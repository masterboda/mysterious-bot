import re
import json
import datetime
import threading
import telegram

from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters
)

from src import config
from src.handlers import conversation_handler

from src.db import (
    init_db, with_db
)

""" Logging setup
========================================="""
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

updater = Updater(token=config.TOKEN, use_context=True)

""" Stop the Bot
========================================="""


def shutdown():
    updater.stop()
    updater.is_idle = False


def stop(update: telegram.Update, context: CallbackContext):
    if update.effective_user.username == 'masterboda':
        update.message.reply_text("Bot is going to stop. Bye!")
        threading.Thread(target=shutdown).start()
    else:
        update.message.reply_text("You don't have a permission to do this operation!")


def restart_fallback(update: telegram.Update, context: CallbackContext):
    update.message.reply_text("Бот оновився, щоб відновити роботу - натисни /start")


@with_db
def broadcast(cursor, update: telegram.Update, context: CallbackContext):
    cursor.execute('SELECT user_id FROM user_data WHERE NOT user_id = ?', (update.effective_user.id,))
    users = cursor.fetchall()

    message = re.sub(r'^(\s+)?\/broadcast(\s+)?', '', update.message.text)

    for user in users:
        try:
            context.bot.send_message(user['user_id'], message)
            print(f"Sent! user_id: { user['user_id'] }")
        except Exception:
            print(f"Send message error!, user_id: { user['user_id'] }")


def main():
    # Command Handlers
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('broadcast', broadcast))

    # Conversation Handlers
    updater.dispatcher.add_handler(conversation_handler)

    # Message Handlers
    updater.dispatcher.add_handler(MessageHandler(Filters.all, restart_fallback))

    init_db()

    updater.start_polling()


if __name__ == '__main__':
    main()
