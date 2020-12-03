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

from src.config import TOKEN
from src.handlers import conversation_handler

from src.db import (
    init_db
)

""" Logging setup
========================================="""
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

updater = Updater(token=TOKEN, use_context=True)

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


def main():
    # Conversation Handlers
    updater.dispatcher.add_handler(conversation_handler)

    # Command Handlers
    updater.dispatcher.add_handler(CommandHandler('stop', stop))

    # Message Handlers
    # ...

    init_db()

    updater.start_polling()


if __name__ == '__main__':
    main()
