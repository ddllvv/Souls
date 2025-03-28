import os
import logging
import psycopg2
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from psycopg2 import OperationalError
from psycopg2.extras import DictCursor

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DARK_SOULS_BOT')

BOT_TOKEN = os.getenv('BOT_TOKEN')
POSTGRES_URL = "postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"

# ================== ИНИЦИАЛИЗАЦИЯ ==================
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())

# ================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_db()

    def connect(self):
        try:
            self.conn = psycopg2.connect(POSTGRES_URL)
            self.conn.autocommit = True
        except OperationalError as e:
            logger.error(f"Ошибка подключения к БД: {e}")

    def init_db(self):
        with self.conn.cursor() as cur:
            # Игроки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    level INT DEFAULT 1,
                    hp INT DEFAULT 100,
                    max_hp INT DEFAULT 100,
                    stamina INT DEFAULT 50,
                    gold INT DEFAULT 50,
                    weapon TEXT DEFAULT 'Кинжал',
                    armor TEXT DEFAULT 'Тряпье',
                    location TEXT DEFAULT 'Хаб',
                    inventory JSONB DEFAULT '[]'
                )
            """)
            
            # Локации
            cur.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    required_level INT DEFAULT 1,
                    enemies JSONB DEFAULT '[]',
                    shop JSONB DEFAULT '[]'
                )
            """)
            
            # Блокировка процессов
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_lock (
                    lock_id INT PRIMARY KEY DEFAULT 1,
                    pid INT NOT NULL
                )
            """)

    def execute(self, query, params=None):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params or ())
                return cur
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            self.connect()
            return None

db = Database()

# ================ ИГРОВЫЕ МЕХАНИКИ ================
class Game:
    # Локации
    LOCATIONS = {
        "Хаб": {
            "description": "Место отдыха. Здесь безопасно.",
            "enemies": [],
            "shop": ["Зелье здоровья:50", "Рем. набор:30"]
        },
        "Темный лес": {
            "description": "Густой лес, полный опасностей.",
            "required_level": 2,
            "enemies": ["Скелет", "Лесной волк"],
            "shop": ["Яд:20", "Факел:40"]
        }
    }

    # Враги
    ENEMIES = {
        "Скелет": {"hp": 80, "attack": 15, "weakness": "Дробящее"},
        "Лесной волк": {"hp": 120, "attack": 20, "weakness": "Острые"}
    }

    # Оружие
    WEAPONS = {
        "Кинжал": {"type": "Острые", "damage": 10},
        "Дубина": {"type": "Дробящее", "damage": 15}
    }

# ==================== КОМАНДЫ =====================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = db.execute("SELECT * FROM players WHERE user_id = %s", (message.from_user.id,))
    if user.fetchone():
        await message.answer("🔮 Вы уже в игре! Используйте /status")
        return
    
    db.execute(
        "INSERT INTO players (user_id, username) VALUES (%s, %s)",
        (message.from_user.id, message.from_user.username)
    )
    
    await message.answer(
        "🔥 Добро пожаловать в Dark Souls бот!\n\n"
        "🛡️ Ваши характеристики:\n"
        "❤️ Здоровье: 100/100\n"
        "💪 Уровень: 1\n"
        "💰 Золото: 50\n\n"
        "Основные команды:\n"
        "/status - ваш профиль\n"
        "/explore - исследовать локацию\n"
        "/inventory - инвентарь\n"
        "/shop - магазин"
    )

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    player = db.execute(
        "SELECT * FROM players WHERE user_id = %s", 
        (message.from_user.id,)
    ).fetchone()
    
    if not player:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    await message.answer(
        f"📊 [Уровень {player['level']}]\n"
        f"❤️ Здоровье: {player['hp']}/{player['max_hp']}\n"
        f"💰 Золото: {player['gold']}\n"
        f"⚔️ Оружие: {player['weapon']}\n"
        f"📍 Локация: {player['location']}"
    )

@dp.message_handler(commands=['explore'])
async def cmd_explore(message: types.Message):
    player = db.execute(
        "SELECT * FROM players WHERE user_id = %s", 
        (message.from_user.id,)
    ).fetchone()
    
    if not player:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    location = Game.LOCATIONS.get(player['location'], {})
    enemies = location.get('enemies', [])
    
    if not enemies:
        await message.answer("Здесь нечего исследовать.")
        return
    
    enemy = random.choice(enemies)
    enemy_stats = Game.ENEMIES[enemy]
    
    await message.answer(
        f"💀 Вы встретили {enemy}!\n"
        f"❤️ HP: {enemy_stats['hp']}\n"
        f"⚔️ Атака: {enemy_stats['attack']}\n\n"
        "Выберите действие:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Атаковать", callback_data=f"fight_{enemy}"),
            types.InlineKeyboardButton("Убежать", callback_data="run_away")
        )
    )

@dp.callback_query_handler(lambda c: c.data.startswith('fight_'))
async def process_fight(callback: types.CallbackQuery):
    enemy = callback.data.split('_')[1]
    enemy_stats = Game.ENEMIES[enemy]
    
    player = db.execute(
        "SELECT * FROM players WHERE user_id = %s", 
        (callback.from_user.id,)
    ).fetchone()
    
    weapon = Game.WEAPONS[player['weapon']]
    damage = weapon['damage']
    
    if weapon['type'] == enemy_stats['weakness']:
        damage *= 2
    
    new_enemy_hp = enemy_stats['hp'] - damage
    new_player_hp = player['hp'] - enemy_stats['attack']
    
    if new_enemy_hp <= 0:
        db.execute(
            "UPDATE players SET gold = gold + %s WHERE user_id = %s",
            (enemy_stats['hp'] // 2, callback.from_user.id)
        )
        await callback.message.edit_text(
            f"🎉 Вы победили {enemy}!\n"
            f"💰 Получено золота: {enemy_stats['hp'] // 2}"
        )
    elif new_player_hp <= 0:
        db.execute(
            "UPDATE players SET hp = max_hp, location = 'Хаб' WHERE user_id = %s",
            (callback.from_user.id,)
        )
        await callback.message.edit_text("☠️ Вы погибли! Возрождение в Хабе.")
    else:
        db.execute(
            "UPDATE players SET hp = %s WHERE user_id = %s",
            (new_player_hp, callback.from_user.id)
        )
        await callback.message.edit_text(
            f"⚔️ Вы нанесли {damage} урона!\n"
            f"💢 Враг атакует! Ваше HP: {new_player_hp}"
        )

# ==================== ЗАПУСК ======================
def kill_other_instances():
    db.execute("DELETE FROM bot_lock")
    db.execute("INSERT INTO bot_lock (lock_id, pid) VALUES (1, %s)", (os.getpid(),))

if __name__ == '__main__':
    kill_other_instances()
    executor.start_polling(
        dp,
        skip_updates=True,
        timeout=300,
        on_startup=lambda _: logger.info("Бот запущен!")
        )
