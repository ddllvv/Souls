import os
import logging
import random
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from psycopg2 import OperationalError

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SOULS_BOT')

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
POSTGRES_URL = "postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"

# ================== ИНИЦИАЛИЗАЦИЯ ==================
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

# ================== БАЗА ДАННЫХ ====================
def init_db():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Удаляем старые блокировки
            cur.execute("DROP TABLE IF EXISTS bot_lock")
            cur.execute("""
                CREATE TABLE bot_lock (
                    pid INT PRIMARY KEY
                )
            """)
            cur.execute("INSERT INTO bot_lock (pid) VALUES (%s)", (os.getpid(),))
            
            # Игроки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    level INT DEFAULT 1,
                    hp INT DEFAULT 100,
                    max_hp INT DEFAULT 100,
                    exp INT DEFAULT 0,
                    gold INT DEFAULT 50,
                    score INT DEFAULT 0,
                    weapon TEXT DEFAULT 'Кинжал',
                    location TEXT DEFAULT 'Хаб',
                    inventory JSONB DEFAULT '[]'
                )
            """)
            
            # Локации
            cur.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    events JSONB DEFAULT '[]',
                    required_level INT DEFAULT 1
                )
            """)
            
            # Заполняем локации
            locations_data = [
                ("Хаб", "Стартовая зона", ["trader", "rest", "trainer"], 1),
                ("Темный лес", "Густой лес с древними духами", ["fight", "treasure", "trap"], 2),
                ("Лабиринт Минотавра", "Каменные стены с кровавыми надписями", ["boss", "puzzle", "trap"], 5),
                ("Вулкан Ашгард", "Раскаленная лава и дым", ["fight", "event", "boss"], 7),
                ("Храм Забытых", "Заброшенный алтарь с артефактами", ["puzzle", "treasure", "curse"], 3),
                ("Ледяные пещеры", "Вечная мерзлота и хрустальные образования", ["fight", "treasure", "trap"], 4),
                ("Кладбище Драконов", "Кости древних существ", ["boss", "event", "curse"], 6),
                ("Башня Магов", "Парящие кристаллы и магические ловушки", ["puzzle", "fight", "treasure"], 8),
                ("Джунгли Шиваны", "Ядовитые растения и скрытые опасности", ["trap", "fight", "event"], 3),
                ("Подземелья Гномов", "Заброшенные шахты с механизмами", ["puzzle", "treasure", "trap"], 4),
                ("Озеро Проклятых", "Туманная вода с призраками", ["curse", "boss", "event"], 5),
                ("Пустыня Безумия", "Палящее солнце и миражы", ["trap", "fight", "treasure"], 6),
                ("Чертоги Хаоса", "Искаженное пространство и демоны", ["boss", "fight", "event"], 9),
                ("Сады Элизиума", "Цветущие растения и скрытые ловушки", ["treasure", "puzzle", "trap"], 2),
                ("Цитадель Тьмы", "Крепость повелителя демонов", ["boss", "fight", "curse"], 10),
                ("Остров Руин", "Развалины древней цивилизации", ["puzzle", "treasure", "trap"], 4),
                ("Абиссальские Глубины", "Подводный мир с чудовищами", ["boss", "fight", "event"], 8),
                ("Небесный Архипелаг", "Парящие острова с хранителями", ["puzzle", "treasure", "boss"], 7)
            ]
            
            cur.executemany("""
                INSERT INTO locations (name, description, events, required_level)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, [(name, desc, events, lvl) for name, desc, events, lvl in locations_data])
            
        logger.info("База инициализирована")
        return True
    except OperationalError as e:
        logger.error(f"Ошибка БД: {e}")
        return False

# ================== ИГРОВЫЕ ДАННЫЕ ====================
WEAPONS = {
    "Кинжал": {"damage": 10, "type": "Обычный"},
    "Меч Пламени": {"damage": 20, "type": "Огонь"},
    "Ледяной Посох": {"damage": 18, "type": "Лед"},
    "Молот Грома": {"damage": 25, "type": "Электричество"}
}

ENEMIES = {
    # Обычные враги
    "Скелет": {"hp": 80, "attack": 15, "gold": 20, "exp": 30, "weakness": "Дробящий"},
    "Лесной Волк": {"hp": 120, "attack": 20, "gold": 30, "exp": 40, "weakness": "Острые"},
    "Гоблин": {"hp": 100, "attack": 18, "gold": 25, "exp": 35, "weakness": "Огонь"},
    
    # Элитные враги
    "Ледяной Голем": {"hp": 200, "attack": 30, "gold": 100, "exp": 80, "weakness": "Огонь"},
    "Огненный Драконид": {"hp": 250, "attack": 35, "gold": 120, "exp": 100, "weakness": "Лед"},
    
    # Боссы
    "Минотавр": {"hp": 500, "attack": 50, "gold": 300, "exp": 200, "weakness": "Электричество"},
    "Лич": {"hp": 400, "attack": 45, "gold": 250, "exp": 180, "weakness": "Свет"},
    "Кракен": {"hp": 600, "attack": 55, "gold": 400, "exp": 250, "weakness": "Огонь"}
}

EVENTS = {
    "fight": "💀 Враг атакует!",
    "treasure": "💎 Вы нашли сундук!",
    "trader": "🏪 Странствующий торговец:",
    "trap": "⚠️ Ловушка!",
    "puzzle": "🔍 Древний механизм...",
    "curse": "☠️ Проклятие!",
    "event": "🌌 Пространство искажается...",
    "rest": "🛌 Вы восстановили силы",
    "boss": "👹 БОСС ЛОКАЦИИ!",
    "trainer": "🧙 Мастер-наставник предлагает:"
}

# ================== СИСТЕМА СОБЫТИЙ ====================
async def handle_event(user_id: int):
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Получаем данные игрока
            cur.execute("SELECT location, level FROM players WHERE user_id = %s", (user_id,))
            location, player_level = cur.fetchone()
            
            # Получаем информацию о локации
            cur.execute("SELECT events, required_level FROM locations WHERE name = %s", (location,))
            location_events, required_level = cur.fetchone()
            
            if player_level < required_level:
                return "🚫 Уровень слишком низок для этой локации!", None
            
            event_type = random.choice(location_events)
            
            # Обработка событий
            if event_type == "fight":
                enemies = [e for e in ENEMIES if ENEMIES[e].get("hp", 0) < 300]
                enemy = random.choice(enemies)
                return (
                    f"{EVENTS[event_type]}\n{enemy} ({ENEMIES[enemy]['hp']}❤)",
                    battle_keyboard(enemy)
                )
                
            elif event_type == "boss":
                bosses = [b for b in ENEMIES if ENEMIES[b].get("hp", 0) >= 300]
                boss = random.choice(bosses)
                return (
                    f"{EVENTS[event_type]}\n{boss} ({ENEMIES[boss]['hp']}❤)",
                    battle_keyboard(boss, is_boss=True)
                )
                
            elif event_type == "treasure":
                gold = random.randint(50, 200)
                cur.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (gold, user_id))
                return f"{EVENTS[event_type]}\n💰 +{gold} золота", menu_keyboard()
            
            elif event_type == "trader":
                return (
                    f"{EVENTS[event_type]}\n"
                    "1. Зелье лечения (100g)\n"
                    "2. Ключ от тайника (200g)",
                    trader_keyboard()
                )
                
            elif event_type == "puzzle":
                return (
                    f"{EVENTS[event_type]}\n"
                    "Нажмите правильную последовательность:",
                    puzzle_keyboard()
                )
                
            elif event_type == "curse":
                damage = random.randint(20, 50)
                cur.execute("UPDATE players SET hp = GREATEST(hp - %s, 0) WHERE user_id = %s", (damage, user_id))
                return f"{EVENTS[event_type]}\n💔 Потеряно {damage} HP!", menu_keyboard()
            
            elif event_type == "rest":
                cur.execute("UPDATE players SET hp = max_hp WHERE user_id = %s", (user_id,))
                return "🛌 Вы полностью исцелились!", menu_keyboard()
                
            return "Ничего не произошло...", menu_keyboard()
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return "⚠️ Ошибка", None

# ================== КЛАВИАТУРЫ ====================
def menu_keyboard():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Исследовать", callback_data="explore"),
        types.InlineKeyboardButton("Профиль", callback_data="status")
    )

def battle_keyboard(enemy: str, is_boss: bool = False):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("Атаковать", callback_data=f"fight_{enemy}"),
        types.InlineKeyboardButton("Сбежать", callback_data="menu")
    )
    if is_boss:
        kb.add(types.InlineKeyboardButton("Исп. артефакт", callback_data="use_artifact"))
    return kb

def trader_keyboard():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Купить зелье", callback_data="buy_potion"),
        types.InlineKeyboardButton("Купить ключ", callback_data="buy_key")
    )

def puzzle_keyboard():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("1", callback_data="puzzle_1"),
        types.InlineKeyboardButton("2", callback_data="puzzle_2"),
        types.InlineKeyboardButton("3", callback_data="puzzle_3")
    )

# ================== ОСНОВНЫЕ КОМАНДЫ ====================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO players (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (message.from_user.id, message.from_user.username))
            
            await message.answer(
                "🔥 Добро пожаловать в Dark Souls бот!",
                reply_markup=menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data == 'explore')
async def process_explore(callback: types.CallbackQuery):
    text, markup = await handle_event(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('fight_'))
async def process_fight(callback: types.CallbackQuery):
    enemy_name = callback.data.split('_')[1]
    enemy = ENEMIES[enemy_name]
    
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Получаем данные игрока
            cur.execute("""
                SELECT hp, weapon, gold, exp 
                FROM players 
                WHERE user_id = %s
            """, (callback.from_user.id,))
            hp, weapon, gold, exp = cur.fetchone()
            
            # Расчет урона
            damage = WEAPONS.get(weapon, {"damage": 10})["damage"]
            if WEAPONS[weapon]["type"] == enemy["weakness"]:
                damage *= 2
                
            new_enemy_hp = enemy["hp"] - damage
            new_hp = hp - enemy["attack"]
            
            # Обновление данных
            if new_enemy_hp <= 0:
                cur.execute("""
                    UPDATE players 
                    SET 
                        gold = gold + %s,
                        exp = exp + %s,
                        score = score + %s
                    WHERE user_id = %s
                """, (enemy["gold"], enemy["exp"], damage, callback.from_user.id))
                text = (
                    f"🎉 {enemy_name} повержен!\n"
                    f"+{enemy['gold']}💰 +{enemy['exp']}✨"
                )
                markup = menu_keyboard()
            else:
                cur.execute("UPDATE players SET hp = %s WHERE user_id = %s", (new_hp, callback.from_user.id))
                text = (
                    f"⚔️ Вы нанесли {damage} урона!\n"
                    f"❤ Ваше HP: {new_hp}\n"
                    f"❤ {enemy_name} HP: {new_enemy_hp}"
                )
                markup = battle_keyboard(enemy_name, "boss" in enemy_name.lower())
                
            await callback.message.edit_text(text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ================== ЗАПУСК ====================
async def on_startup(dp):
    if not init_db():
        exit(1)
        
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "✅ Бот запущен!")
        except:
            pass
    
    logger.info("Бот стартовал")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        timeout=300
            )
