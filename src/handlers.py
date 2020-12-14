import re
import json

from telegram import (
    Update,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    Filters
)

from .db import (
    with_db
)

from . import markup

GET_RECEIVER, GET_MESSAGE, GET_REPLY, READY_TO_SEND = range(4)


@with_db
def start(cursor, update: Update, context: CallbackContext):
    text_lines = []
    
    context.user_data.pop('receiver_id', None)
    context.user_data.pop('message', None)

    user = update.effective_user
    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name
    }

    cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()

    if not result:
        text_lines = [
            "Привіт! Я бот для таємного листування!",
            "Щоб розпочати, тобі потрібно відправити нікнейм отримувача (окремим повідомленням) або поділитися контактом.",
            "Далі набираєш повідомлення, яке хочеш відправити (текст, смайли, стікери, фото, відео, GIF...)",
            "Поки що можна відправити лише одне повідомлення за раз, тому не вдасться надіслати галерею з кількох фото/відео одночасно",
            "Гарного листування!"
        ]

        cursor.execute('INSERT INTO user_data (username, user_id, data) VALUES (?, ?, ?)', (user.username, user.id, json.dumps(user_data)))
    else:
        text_lines = [
            'Відправ нікнейм отримувача або поділися контакатом, щоб продовжити:'
        ]

        cursor.execute('UPDATE user_data SET username = ?, data = ? WHERE user_id = ?', (user.username, json.dumps(user_data), user.id))

    text = '\n\n'.join(text_lines)
    update.message.reply_text(text)

    return GET_RECEIVER


@with_db
def get_receiver(cursor, update: Update, context: CallbackContext):
    if update.message.contact:
        user_id = update.message.contact.user_id
        if not user_id:
            lines = [
                'Вибач, не вдається відправити за цим контактом :(',
                'Спробуй використати нікнейм'
            ]

            update.message.reply_text('\n'.join(lines))            

            return GET_RECEIVER

        context.user_data['receiver_id'] = user_id
    else:
        cursor.execute('SELECT * FROM user_data WHERE username = ?', (update.message.text.replace('@', ''),))
        result = cursor.fetchone()

        if not result:
            lines = [
                'Вибач, не можу знайти цього користувача :(',
                'Спробуй поділитися контактом'
            ]

            update.message.reply_text('\n'.join(lines))

            return GET_RECEIVER

        context.user_data['receiver_id'] = result['user_id']

    text = 'Створи повідомлення:'

    update.message.reply_text(
        text,
        # reply_markup=with_receiver_markup
    )

    return GET_MESSAGE


def get_message(update: Update, context: CallbackContext):
    context.user_data['message'] = update.message
    context.user_data['message_id'] = update.message.message_id

    text = 'Чудово! Тепер можеш відправити його або скасувати:'
    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(markup.SEND, callback_data=markup.SEND),
                InlineKeyboardButton(markup.CANCEL, callback_data=markup.CANCEL)
            ]
        ])
    )

    return READY_TO_SEND


@with_db
def anonymous_reply(cursor, update: Update, context: CallbackContext):
    reply_to = update.message.reply_to_message
    user = update.effective_user

    cursor.execute('SELECT * FROM messages WHERE message_id = ?', (reply_to.message_id,))
    message_data = cursor.fetchone()

    if not message_data:
        update.message.reply_text('Вибач, не можу надіслати відповідь для цього повідомлення')

        return GET_RECEIVER

    sender = json.loads(message_data['sender'])
    user_data = {
        'id': update.effective_user.id,
        'username': update.effective_user.username,
        'name': update.effective_user.full_name
    }

    if not message_data['is_reply']:
        context.bot.send_message(sender['id'], f'Відповідь від { "@" + user.username if user.username else user.full_name }:')
    else:
        context.bot.send_message(sender['id'], f'Відповідь:')

    sent = context.bot.copy_message(chat_id=sender['id'], from_chat_id=update.effective_chat.id, message_id=update.message.message_id, reply_to_message_id=message_data['original_message_id'])
    
    cursor.execute('INSERT INTO messages (receiver_id, sender, message_id, original_message_id, is_reply) VALUES (?, ?, ?, ?, ?)', (sender['id'], json.dumps(user_data), sent.message_id, update.message.message_id, True))

    update.message.reply_text('Відповідь надіслана!')

    return GET_RECEIVER


@with_db
def query_buttons(cursor, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    receiver_id, user_message, user_message_id = context.user_data['receiver_id'], context.user_data['message'], context.user_data['message_id']

    if query.data == markup.SEND:

        user = {
            'id': update.effective_user.id,
            'username': update.effective_user.username,
            'name': update.effective_user.full_name
        }

        try:
            context.bot.send_message(receiver_id, 'Привіт, маю нове повідомлення для тебе!')
            sent = context.bot.copy_message(chat_id=receiver_id, from_chat_id=update.effective_user.id, message_id=user_message_id)

            cursor.execute('INSERT INTO messages (receiver_id, sender, message_id, original_message_id) VALUES (?, ?, ?, ?)', (context.user_data['receiver_id'], json.dumps(user), sent.message_id, user_message_id))
            
            query.edit_message_text(text='Вітаю! Повідомлення успішно доставлено!')
        except Exception:
            print(Exception)
            query.edit_message_text(text='Вибач, цей користувач поки не доступний')

    elif query.data == markup.CANCEL:
        query.edit_message_text(text='Скасовано!')

    context.user_data.pop('receiver_id', None)
    context.user_data.pop('message', None)

    return GET_RECEIVER


def other_reply(update: Update, context: CallbackContext):
    text = "Невалідна відповідь!"
    update.message.reply_text(text)


conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        GET_RECEIVER: [
            MessageHandler(Filters.reply, anonymous_reply),
            MessageHandler(Filters.all ^ Filters.command, get_receiver)
        ],
        GET_MESSAGE: [
            MessageHandler(Filters.all ^ Filters.command, get_message)
        ],
        READY_TO_SEND: [
            CallbackQueryHandler(query_buttons)
        ]
    },
    fallbacks=[
        CommandHandler('start', start),
        MessageHandler(Filters.all, other_reply)
    ]
)
