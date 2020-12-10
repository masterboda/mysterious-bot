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

GET_RECEIVER, GET_MESSAGE, READY_TO_SEND = range(3)


@with_db
def start(cursor, update: Update, context: CallbackContext):
    text_lines = [
        'Hi! I\'m bot for private messaging.',
        'Enter a receiver nickname or share contact to proceed:'
    ]
    text = '\n'.join(text_lines)
    
    context.user_data.pop('receiver_id', None)
    context.user_data.pop('message', None)

    update.message.reply_text(text)

    user = update.effective_user
    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name
    }

    cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()

    if not result:
        cursor.execute('INSERT INTO user_data (username, user_id, data) VALUES (?, ?, ?)', (user.username, user.id, json.dumps(user_data)))
    else:
        cursor.execute('UPDATE user_data SET username = ?, data = ? WHERE user_id = ?', (user.username, json.dumps(user_data), user.id))

    return GET_RECEIVER


@with_db
def get_receiver(cursor, update: Update, context: CallbackContext):
    if update.message.contact:
        context.user_data['receiver_id'] = update.message.contact.user_id
    else:
        cursor.execute('SELECT * FROM user_data WHERE username = ?', (update.message.text.replace('@', ''),))
        result = cursor.fetchone()

        if not result:
            lines = [
                'Sorry, can\'t find specified user :(',
                'Try share contact'
            ]

            update.message.reply_text('\n'.join(lines))

            return GET_RECEIVER

        context.user_data['receiver_id'] = result['user_id']

    text = 'Compose message:'

    update.message.reply_text(
        text,
        # reply_markup=with_receiver_markup
    )

    return GET_MESSAGE


def get_message(update: Update, context: CallbackContext):
    context.user_data['message'] = update.message.text

    text = 'Good! Now you can send it by clicking button below'
    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(markup.SEND, callback_data=1)]
        ])
    )

    return READY_TO_SEND


def send(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    try:
        context.bot.send_message(context.user_data['receiver_id'], 'Hey! You have new message:')
        context.bot.send_message(context.user_data['receiver_id'], context.user_data['message'])

        query.edit_message_text(text='Congrats! Message successfully sent!')
    except Exception:
        query.edit_message_text(text='Sorry, this user is not accessible yet!')

    del context.user_data['message']
    del context.user_data['receiver_id']

    return GET_RECEIVER


def other_reply(update: Update, context: CallbackContext):
    text = "Виберіть один із варіантів на клавіатурі"
    update.message.reply_text(text)


conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        GET_RECEIVER: [
            MessageHandler(Filters.all, get_receiver)
        ],
        GET_MESSAGE: [
            MessageHandler(Filters.all, get_message)
        ],
        READY_TO_SEND: [
            CallbackQueryHandler(send)
        ]
    },
    fallbacks=[
        CommandHandler('start', start),
        MessageHandler(Filters.all, other_reply)
    ]
)
