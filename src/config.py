import os

from telegram import Bot

TOKEN = os.getenv('TOKEN')
print(TOKEN)
BOT = Bot(TOKEN)
DB_FILE = '/home/brutia/Code/Projects/anonymous-bot/data.db'
