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
            "Hi! I'm a bot for private messaging.",
            "To start, you need to send me a receiver nickname (in a separate message) or share contact.",
            "Then you should compose message which may contain photo/video/voice/sticker etc. But for now I accept only one message per time, so you cannot send media galleries.",
            "\nHave a good conversation!"
        ]

        cursor.execute('INSERT INTO user_data (username, user_id, data) VALUES (?, ?, ?)', (user.username, user.id, json.dumps(user_data)))
    else:
        text_lines = [
            'Enter a receiver nickname or share contact to proceed:'
        ]

        cursor.execute('UPDATE user_data SET username = ?, data = ? WHERE user_id = ?', (user.username, json.dumps(user_data), user.id))

    text = '\n'.join(text_lines)
    update.message.reply_text(text)

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
    context.user_data['message'] = update.message

    text = 'Good! Now you can send it by clicking button below'
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


def forward_message(receiver_id, message, context):
    context.bot.send_message(receiver_id, 'Hey! You have new message:')

    if message.photo:
        context.bot.send_photo(chat_id=receiver_id, photo=message.photo, caption=message.caption)
    if message.video:
        context.bot.send_video(chat_id=receiver_id, video=message.video, caption=message.caption)
    if message.audio:
        context.bot.send_audio(chat_id=receiver_id, audio=message.audio, caption=message.caption)
    if message.document:
        context.bot.send_document(chat_id=receiver_id, document=message.document, caption=message.caption)
    if message.sticker:
        context.bot.send_sticker(chat_id=receiver_id, sticker=message.sticker)
    if message.voice:
        context.bot.send_voice(chat_id=receiver_id, voice=message.voice)
    if message.video_note:
        context.bot.send_video_note(chat_id=receiver_id, video_note=message.video_note)
    if message.text:
        context.bot.send_message(receiver_id, message.text)

@with_db
def send(cursor, update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == markup.SEND:

        user = {
            'id': update.effective_user.id,
            'username': update.effective_user.username,
            'name': f'{update.effective_user.first_name} {update.effective_user.last_name}'
        }
        cursor.execute('INSERT INTO messages (receiver_id, sender, message) VALUES (?, ?, ?)', (context.user_data['receiver_id'], json.dumps(user), json.dumps(context.user_data['message'].to_dict())))

        try:
            forward_message(context.user_data['receiver_id'], context.user_data['message'], context)
            query.edit_message_text(text='Congrats! Message successfully sent!')
        except Exception:
            print(Exception)
            query.edit_message_text(text='Sorry, this user is not accessible yet!')

    elif query.data == markup.CANCEL:
        query.edit_message_text(text='Canceled!')

    context.user_data.pop('receiver_id', None)
    context.user_data.pop('message', None)

    return GET_RECEIVER


def other_reply(update: Update, context: CallbackContext):
    text = "Choose one of the options on the keyboard"
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
