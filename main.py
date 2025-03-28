import os
import logging
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from psycopg2 import OperationalError

# --- Жесткие настройки для Render ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot)

# --- Ваша PostgreSQL ---
POSTGRES_URL = "postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"

def get_db():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        return conn
    except OperationalError as e:
        logger.error(f"DB DEAD: {e}")
        return None

# --- Жесткий лок для бота ---
def bot_lock():
    conn = get_db()
    if not conn: return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_lock (
                    id SERIAL PRIMARY KEY,
                    pid INT UNIQUE
                )
            """)
            
            # Удаляем старые блокировки
            cur.execute("DELETE FROM bot_lock")
            
            # Добавляем текущий процесс
            cur.execute("INSERT INTO bot_lock (pid) VALUES (%s)", (os.getpid(),))
            return True
    except:
        return False

# --- Проверка дублей ---
def is_another_bot_running():
    conn = get_db()
    if not conn: return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pid FROM bot_lock")
            return cur.fetchone() is not None
    except:
        return False

# --- Команды ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("🛡️ Бот работает! /help")

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer("Команды:\n/start\n/help")

# --- Запуск ---
async def on_startup(_):
    if is_another_bot_running():
        logger.error("УБЕЙТЕ ДРУГОЙ ПРОЦЕСС!")
        exit(1)
        
    if not bot_lock():
        logger.error("Не удалось установить блокировку")
        exit(1)
    
    await bot.delete_webhook()
    logger.info("Бот запущен монопольно")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        timeout=300  # Увеличил таймаут для Render
        )
