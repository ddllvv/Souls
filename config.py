from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение БД
conn = sqlite3.connect('data/database.db')
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    username TEXT,
    level INTEGER DEFAULT 1,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    stamina INTEGER DEFAULT 10,
    gold INTEGER DEFAULT 50,
    weapon TEXT DEFAULT "Кинжал",
    armor TEXT DEFAULT "Тряпье",
    current_location TEXT DEFAULT "Хаб",
    inventory TEXT DEFAULT '{"items": [], "weight": 0}'
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY,
    name TEXT,
    required_key TEXT,
    enemies TEXT  # JSON: {"enemies": ["Скелет", "Зомби"], "boss": "Каменный страж"}
)''')

conn.commit()
