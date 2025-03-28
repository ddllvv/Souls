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
ADMIN_ID = os.getenv('ADMIN_ID')  # Получить через @userinfobot
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
                    required_level INT DEFAULT 1,
                    enemies JSONB DEFAULT '[]'
                )
            """)
            
            # Заполняем локации
            cur.execute("""
                INSERT INTO locations (name, description, enemies)
                VALUES 
                    ('Хаб', 'Место отдыха', '[]'),
                    ('Темный лес', 'Густой лес с опасными тварями', '["Скелет", "Лесной волк"]')
                ON CONFLICT DO NOTHING
            """)
            
        logger.info("База инициализирована")
        return True
    except OperationalError as e:
        logger.error(f"Ошибка БД: {e}")
        return False

# ================== ИГРОВЫЕ ДАННЫЕ ====================
WEAPONS = {
    "Кинжал": {"damage": 10, "type": "Острые"},
    "Топор": {"damage": 15, "type": "Дробящие"}
}

ENEMIES = {
    "Скелет": {"hp": 80, "attack": 15, "weakness": "Дробящие", "exp": 20},
    "Лесной волк": {"hp": 120, "attack": 20, "weakness": "Острые", "exp": 30}
}

# ================== СИСТЕМА БОЯ ====================
async def handle_battle(user_id: int, enemy_name: str):
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Получаем данные игрока
            cur.execute("""
                SELECT hp, weapon, level, exp 
                FROM players 
                WHERE user_id = %s
            """, (user_id,))
            player = cur.fetchone()
            
            if not player:
                return "❌ Сначала зарегистрируйтесь через /start"
            
            player_hp, weapon, level, exp = player
            enemy = ENEMIES[enemy_name]
            weapon_damage = WEAPONS.get(weapon, {"damage": 10})["damage"]
            
            # Расчет урона с учетом слабостей
            if WEAPONS[weapon]["type"] == enemy["weakness"]:
                damage = weapon_damage * 2
            else:
                damage = weapon_damage
                
            enemy_hp = enemy["hp"] - damage
            player_new_hp = player_hp - enemy["attack"]
            
            # Обновляем данные
            if enemy_hp <= 0:
                new_exp = exp + enemy["exp"]
                new_gold = enemy["hp"] // 2
                cur.execute("""
                    UPDATE players 
                    SET 
                        hp = CASE WHEN hp > 0 THEN hp ELSE 100 END,
                        exp = %s,
                        gold = gold + %s,
                        score = score + %s
                    WHERE user_id = %s
                """, (new_exp, new_gold, damage, user_id))
                return f"🎉 Победа! +{enemy['exp']} опыта, +{new_gold} золота"
                
            elif player_new_hp <= 0:
                cur.execute("""
                    UPDATE players 
                    SET hp = 100, location = 'Хаб' 
                    WHERE user_id = %s
                """, (user_id,))
                return "☠️ Вы погибли! Возрождение в Хабе."
                
            else:
                cur.execute("""
                    UPDATE players 
                    SET hp = %s 
                    WHERE user_id = %s
                """, (player_new_hp, user_id))
                return f"⚔️ Вы нанесли {damage} урона! Ваше HP: {player_new_hp}"
                
    except Exception as e:
        logger.error(f"Ошибка боя: {e}")
        return "⚠️ Произошла ошибка"

# ================== КОМАНДЫ ====================
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
                "🔥 Добро пожаловать в Dark Souls бот!\n"
                "Основные команды:\n"
                "/status - ваш профиль\n"
                "/explore - исследовать локацию\n"
                "/upgrade - прокачка\n"
                "/top - таблица лидеров"
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT level, hp, exp, gold, score, weapon, location 
                FROM players 
                WHERE user_id = %s
            """, (message.from_user.id,))
            data = cur.fetchone()
            
            if not data:
                await message.answer("Сначала /start")
                return
                
            level, hp, exp, gold, score, weapon, location = data
            await message.answer(
                f"📊 Уровень: {level}\n"
                f"❤️ HP: {hp}/100\n"
                f"✨ Опыт: {exp}/100\n"
                f"💰 Золото: {gold}\n"
                f"🏆 Очки: {score}\n"
                f"⚔️ Оружие: {weapon}\n"
                f"📍 Локация: {location}"
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")

@dp.message_handler(commands=['explore'])
async def cmd_explore(message: types.Message):
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT location, level 
                FROM players 
                WHERE user_id = %s
            """, (message.from_user.id,))
            location, level = cur.fetchone()
            
            cur.execute("""
                SELECT enemies 
                FROM locations 
                WHERE name = %s AND required_level <= %s
            """, (location, level))
            
            if enemies := cur.fetchone()[0]:
                enemy = random.choice(enemies)
                await message.answer(
                    f"🌑 Вы встретили {enemy}!\n"
                    "Выберите действие:",
                    reply_markup=types.InlineKeyboardMarkup().row(
                        types.InlineKeyboardButton("Атаковать", callback_data=f"fight_{enemy}"),
                        types.InlineKeyboardButton("Убежать", callback_data="run_away")
                    )
                )
            else:
                await message.answer("Здесь нечего исследовать")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('fight_'))
async def process_fight(callback: types.CallbackQuery):
    enemy = callback.data.split('_')[1]
    result = await handle_battle(callback.from_user.id, enemy)
    await callback.message.edit_text(result)

# ================== ЗАПУСК ====================
async def on_startup(dp):
    if not init_db():
        exit(1)
        
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, "✅ Бот запущен!")
    
    logger.info("Бот стартовал")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        timeout=300
)
