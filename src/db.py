import sqlite3
import sys
import json
import time

from . import config


class SQLite:
    def __init__(self):
        self.db_file = config.DB_FILE

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row

        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()


def with_db(func):
    def wrapper(*args, **kwargs):
        with SQLite() as cursor:
            # try:
            return func(cursor, *args, **kwargs)
            # except Exception as e:
            #     print('DATABASE ERROR', e)

    return wrapper


@with_db
def init_db(cursor, reset=False):
    if reset:
        cursor.execute('DROP TABLE IF EXISTS user_data')
        cursor.execute('DROP TABLE IF EXISTS messages')
        cursor.execute('DROP TABLE IF EXISTS permissions')

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64) NULL,
            user_id INTEGER NOT NULL,
            data TEXT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            date DATE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(64) NOT NULL,
            label TEXT NOT NULL
        )
        """
    )
