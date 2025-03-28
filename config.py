import os
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import psycopg2
from psycopg2 import OperationalError

# Инициализация бота
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение к PostgreSQL
def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"))
        conn.autocommit = True
        return conn
    except OperationalError as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        return None

# Инициализация таблиц
def init_db():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS players (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            stamina INTEGER DEFAULT 50,
            gold INTEGER DEFAULT 0,
            weapon TEXT DEFAULT 'Кинжал',
            armor TEXT DEFAULT 'Тряпье',
            current_location TEXT DEFAULT 'Хаб',
            inventory JSONB DEFAULT '{"items": [], "weight": 0}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            required_key TEXT,
            enemies JSONB DEFAULT '{"normal": [], "boss": null}',
            effects JSONB DEFAULT '{}'
        )
        """
    )
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for command in commands:
            cursor.execute(command)
        cursor.close()
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
    finally:
        if conn is not None:
            conn.close()

# Автоматически создаем таблицы при импорте
init_db()
