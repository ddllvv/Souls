import os
import logging
import random
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from psycopg2 import OperationalError

# --- Настройки ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SOULS_BOT')

BOT_TOKEN = os.getenv('BOT_TOKEN')
POSTGRES_URL = "postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

# --- База данных ---
def get_db():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        return conn
    except OperationalError as e:
        logger.error(f"DB ERROR: {e}")
        return None

def init_db():
    conn = get_db()
    if not conn: return
    
    with conn.cursor() as cur:
        # Удаляем старые блокировки
        cur.execute("DROP TABLE IF EXISTS bot_lock")
        cur.execute("""
            CREATE TABLE bot_lock (
                pid INT PRIMARY KEY
            )
        """)
        cur.execute("INSERT INTO bot_lock (pid) VALUES (%s)", (os.getpid(),))
        
        # Таблица игроков
        cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                hp INT DEFAULT 100,
                gold INT DEFAULT 50,
                weapon TEXT DEFAULT 'Кинжал',
                location TEXT DEFAULT 'Хаб'
            )
        """)
    logger.info("База инициализирована")

# --- Игровые данные ---
ENEMIES = {
    "Скелет": {"hp": 80, "attack": 15},
    "Волк": {"hp": 120, "attack": 20}
}

WEAPONS = {
    "Кинжал": 10,
    "Меч": 15,
    "Топор": 20
}

# --- Команды ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    conn = get_db()
    if not conn: return
    
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM players WHERE user_id = %s", (message.from_user.id,))
        if cur.fetchone():
            await message.answer("🗡 Вы уже в игре! Используйте /status")
            return
        
        cur.execute("""
            INSERT INTO players (user_id, username)
            VALUES (%s, %s)
        """, (message.from_user.id, message.from_user.username))
        
        await message.answer(
            "🔥 Добро пожаловать в Dark Souls бот!\n"
            "❤️ HP: 100 | 💰 Золото: 50\n"
            "Команды:\n"
            "/status - ваш профиль\n"
            "/explore - исследовать локацию\n"
            "/shop - магазин"
        )

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    conn = get_db()
    if not conn: return
    
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM players WHERE user_id = %s", (message.from_user.id,))
        player = cur.fetchone()
        
        if not player:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return
        
        await message.answer(
            f"📊 Статус:\n"
            f"❤️ HP: {player[2]}/100\n"
            f"💰 Золото: {player[3]}\n"
            f"⚔️ Оружие: {player[4]}\n"
            f"📍 Локация: {player[5]}"
        )

@dp.message_handler(commands=['explore'])
async def cmd_explore(message: types.Message):
    conn = get_db()
    if not conn: return
    
    with conn.cursor() as cur:
        cur.execute("SELECT location FROM players WHERE user_id = %s", (message.from_user.id,))
        location = cur.fetchone()[0]
        
        enemy = random.choice(list(ENEMIES.keys()))
        enemy_hp = ENEMIES[enemy]["hp"]
        enemy_attack = ENEMIES[enemy]["attack"]
        
        await message.answer(
            f"🌑 Вы встретили {enemy}!\n"
            f"❤️ HP врага: {enemy_hp}\n"
            f"⚔️ Атака: {enemy_attack}\n\n"
            "Выберите действие:",
            reply_markup=types.InlineKeyboardMarkup().row(
                types.InlineKeyboardButton("Атаковать", callback_data=f"fight_{enemy}"),
                types.InlineKeyboardButton("Убежать", callback_data="run_away")
            )
        )

@dp.callback_query_handler(lambda c: c.data.startswith('fight_'))
async def process_fight(callback: types.CallbackQuery):
    enemy = callback.data.split('_')[1]
    enemy_stats = ENEMIES[enemy]
    
    conn = get_db()
    if not conn: return
    
    with conn.cursor() as cur:
        # Получаем данные игрока
        cur.execute("SELECT hp, weapon FROM players WHERE user_id = %s", (callback.from_user.id,))
        player_hp, weapon = cur.fetchone()
        
        # Расчет урона
        damage = WEAPONS.get(weapon, 10)
        new_enemy_hp = enemy_stats["hp"] - damage
        new_player_hp = player_hp - enemy_stats["attack"]
        
        if new_enemy_hp <= 0:
            cur.execute("""
                UPDATE players 
                SET gold = gold + %s 
                WHERE user_id = %s
            """, (enemy_stats["hp"], callback.from_user.id))
            await callback.message.edit_text(f"🎉 Вы победили {enemy}! +{enemy_stats['hp']} золота")
        elif new_player_hp <= 0:
            cur.execute("""
                UPDATE players 
                SET hp = 100, location = 'Хаб' 
                WHERE user_id = %s
            """, (callback.from_user.id,))
            await callback.message.edit_text("☠️ Вы погибли! Возрождение в Хабе.")
        else:
            cur.execute("""
                UPDATE players 
                SET hp = %s 
                WHERE user_id = %s
            """, (new_player_hp, callback.from_user.id))
            await callback.message.edit_text(
                f"⚔️ Вы нанесли {damage} урона!\n"
                f"💢 Вас атаковали! Осталось HP: {new_player_hp}"
            )

# --- Запуск ---
if __name__ == '__main__':
    init_db()  # Инициализация БД
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=lambda _: logger.info("Бот запущен!"),
        timeout=300
                    )
