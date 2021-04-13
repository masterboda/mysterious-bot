import os

from telegram import Bot

TOKEN = os.getenv('TOKEN')
PROJECT_HOME = os.getenv('PROJECT_HOME')
BOT = Bot(TOKEN)
DB_FILE = f'{PROJECT_HOME}/data.db'
