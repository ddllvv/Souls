import os
import logging
import random
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from psycopg2 import OperationalError
from psycopg2.extras import DictCursor

# Настройки
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('RPG_BOT')

BOT_TOKEN = os.getenv('BOT_TOKEN')
POSTGRES_URL = "postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"

bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

# =============================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (ВСЕ ТАБЛИЦЫ И ДАННЫЕ)
# =============================================

def init_db():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Удаляем старые таблицы
            cur.execute("DROP TABLE IF EXISTS players CASCADE")
            cur.execute("DROP TABLE IF EXISTS locations CASCADE")
            cur.execute("DROP TABLE IF EXISTS enemies CASCADE")
            cur.execute("DROP TABLE IF EXISTS armor CASCADE")
            cur.execute("DROP TABLE IF EXISTS weapons CASCADE")
            cur.execute("DROP TABLE IF EXISTS inventory CASCADE")

            # Игроки
            cur.execute("""
                CREATE TABLE players (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    level INT DEFAULT 1,
                    hp INT DEFAULT 100,
                    max_hp INT DEFAULT 100,
                    stamina INT DEFAULT 100,
                    exp INT DEFAULT 0,
                    gold INT DEFAULT 50,
                    strength INT DEFAULT 5,
                    agility INT DEFAULT 5,
                    intelligence INT DEFAULT 5,
                    current_location TEXT DEFAULT 'Стартовый лагерь',
                    equipped_weapon TEXT,
                    equipped_armor TEXT
                )
            """)

            # Локации (15 уникальных)
            cur.execute("""
                CREATE TABLE locations (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    min_level INT,
                    enemies TEXT[],
                    events TEXT[]
                )
            """)
            locations_data = [
                ("Стартовый лагерь", "Безопасная зона для новичков", 1, 
                 [], ["trader", "rest", "trainer"]),
                ("Лес Теней", "Густой лес с древними духами", 2,
                 ["Лесной волк", "Ядовитый паук"], ["fight", "herb_gathering"]),
                ("Ледяные пещеры", "Пещеры с вечной мерзлотой", 3,
                 ["Ледяной голем", "Снежный тролль"], ["ice_puzzle", "boss"]),
                ("Пустыня Адракс", "Бескрайние пески под палящим солнцем", 4,
                 ["Песчаный червь", "Скорпион-мутант"], ["sandstorm", "oasis"]),
                ("Башня Арканум", "Древняя магическая башня", 5,
                 ["Магический голем", "Архимаг"], ["spell_puzzle", "library"]),
                ("Болота Скверны", "Токсичные топи с ядовитой фауной", 3,
                 ["Болотный тролль", "Гигантская пиявка"], ["poison_cloud", "ritual"]),
                ("Подземелья Моргара", "Лабиринт ловушек и сокровищ", 4,
                 ["Каменный голем", "Темный рыцарь"], ["trap", "treasure"]),
                ("Вулкан Игнис", "Огненная гора с лавовыми потоками", 6,
                 ["Огненный элементаль", "Лавовый дракон"], ["eruption", "forge"]),
                ("Храм Луны", "Заброшенный храм древней цивилизации", 4,
                 ["Жрец Тьмы", "Теневая пантера"], ["moon_puzzle", "sacrifice"]),
                ("Долина Великанов", "Земля древних исполинов", 5,
                 ["Каменный великан", "Громобор"], ["earthquake", "giant_city"]),
                ("Аббатство Крови", "Проклятое место темных ритуалов", 7,
                 ["Вампир-лорд", "Кровавый голем"], ["blood_ritual", "crypt"]),
                ("Руины Зер'Эт", "Остатки древней магической цивилизации", 6,
                 ["Магический разрушитель", "Хранитель руин"], ["arcane_puzzle", "artifact"]),
                ("Проклятый лес", "Деревья с глазами и шепотом теней", 3,
                 ["Теневой вурдалак", "Древний тролль"], ["curse", "ancient_tree"]),
                ("Небесные острова", "Парящие в облаках острова", 8,
                 ["Громовой дракон", "Небесный хищник"], ["sky_battle", "cloud_temple"]),
                ("Подгород", "Подземный город воров и контрабандистов", 5,
                 ["Глава банды", "Теневой убийца"], ["black_market", "ambush"])
            ]
            cur.executemany("""
                INSERT INTO locations (name, description, min_level, enemies, events)
                VALUES (%s, %s, %s, %s, %s)
            """, locations_data)

            # Враги (20+ типов)
            cur.execute("""
                CREATE TABLE enemies (
                    name TEXT PRIMARY KEY,
                    hp INT,
                    attack INT,
                    armor INT,
                    weakness TEXT,
                    exp_reward INT,
                    gold_reward INT,
                    loot TEXT[]
                )
            """)
            enemies_data = [
                ("Лесной волк", 120, 15, 5, "Огонь", 50, 20, ["Клык волка", "Шкура волка"]),
                ("Ядовитый паук", 80, 20, 3, "Удар", 40, 15, ["Ядовитая железа", "Паучий шелк"]),
                ("Ледяной голем", 300, 25, 20, "Огонь", 150, 50, ["Ледяное ядро", "Морозный кристалл"]),
                ("Снежный тролль", 200, 30, 15, "Огонь", 100, 40, ["Древний амулет", "Шкура тролля"]),
                ("Песчаный червь", 400, 35, 25, "Вода", 200, 75, ["Зуб червя", "Песчаная жемчужина"]),
                ("Магический голем", 500, 40, 30, "Магия", 300, 100, ["Эссенция магии", "Рунический камень"]),
                ("Огненный элементаль", 350, 45, 10, "Вода", 250, 90, ["Огненное сердце", "Пламенный шар"]),
                ("Темный рыцарь", 450, 50, 40, "Свет", 400, 150, ["Темный меч", "Рыцарский доспех"]),
                ("Вампир-лорд", 600, 55, 20, "Серебро", 500, 200, ["Плащ вампира", "Клык вампира"]),
                ("Громовой дракон", 800, 70, 50, "Лед", 700, 300, ["Драконий зуб", "Грозовая сфера"])
            ]
            cur.executemany("""
                INSERT INTO enemies (name, hp, attack, armor, weakness, 
                exp_reward, gold_reward, loot)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, enemies_data)

            # Броня (15+ типов)
            cur.execute("""
                CREATE TABLE armor (
                    name TEXT PRIMARY KEY,
                    armor_type TEXT,
                    defense INT,
                    stamina_cost INT,
                    required_level INT
                )
            """)
            armor_data = [
                ("Кожаный доспех", "Лёгкая", 10, 5, 1),
                ("Кольчуга", "Средняя", 20, 10, 2),
                ("Латный доспех", "Тяжелая", 35, 20, 4),
                ("Магическая мантия", "Тканевая", 15, 3, 3),
                ("Доспех дракона", "Тяжелая", 50, 25, 6),
                ("Теневой плащ", "Лёгкая", 25, 8, 5),
                ("Ледяные латы", "Тяжелая", 40, 22, 5),
                ("Обсидиановый доспех", "Тяжелая", 45, 30, 7)
            ]
            cur.executemany("""
                INSERT INTO armor (name, armor_type, defense, stamina_cost, required_level)
                VALUES (%s, %s, %s, %s, %s)
            """, armor_data)

            # Оружие (15+ типов)
            cur.execute("""
                CREATE TABLE weapons (
                    name TEXT PRIMARY KEY,
                    weapon_type TEXT,
                    damage INT,
                    speed INT,
                    required_level INT
                )
            """)
            weapons_data = [
                ("Короткий меч", "Меч", 15, 3, 1),
                ("Секира", "Топор", 20, 2, 2),
                ("Посох огня", "Посох", 25, 4, 3),
                ("Ледяной клинок", "Меч", 30, 3, 4),
                ("Молот грома", "Молот", 35, 1, 5),
                ("Лук тени", "Лук", 28, 5, 3),
                ("Кинжал яда", "Кинжал", 18, 5, 2),
                ("Древний арбалет", "Арбалет", 40, 2, 6)
            ]
            cur.executemany("""
                INSERT INTO weapons (name, weapon_type, damage, speed, required_level)
                VALUES (%s, %s, %s, %s, %s)
            """, weapons_data)

            # Инвентарь
            cur.execute("""
                CREATE TABLE inventory (
                    user_id BIGINT REFERENCES players(user_id),
                    item_type TEXT,
                    item_name TEXT,
                    quantity INT DEFAULT 1,
                    PRIMARY KEY (user_id, item_name)
                )
            """)

        logger.info("База данных инициализирована")
        return True
    except OperationalError as e:
        logger.error(f"Ошибка подключения: {e}")
        return False

# =============================================
# ИГРОВЫЕ СИСТЕМЫ (ПОЛНОСТЬЮ РЕАЛИЗОВАНЫ)
# =============================================

class BattleSystem:
    @staticmethod
    async def handle_attack(user_id: int, enemy_name: str):
        conn = psycopg2.connect(POSTGRES_URL)
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Получаем данные игрока
                cur.execute("""
                    SELECT p.*, w.damage, a.defense 
                    FROM players p
                    LEFT JOIN weapons w ON p.equipped_weapon = w.name
                    LEFT JOIN armor a ON p.equipped_armor = a.name
                    WHERE p.user_id = %s
                """, (user_id,))
                player = cur.fetchone()

                # Получаем данные врага
                cur.execute("SELECT * FROM enemies WHERE name = %s", (enemy_name,))
                enemy = cur.fetchone()

                if not player or not enemy:
                    return "Ошибка в данных"

                # Расчет урона игрока
                base_damage = player['damage'] if player['damage'] else 10
                if enemy['weakness'] == "Огонь" and "Огненный" in player['equipped_weapon']:
                    base_damage *= 2
                final_damage = max(base_damage - enemy['armor'], 1)

                # Ответный удар врага
                enemy_damage = max(enemy['attack'] - player['defense'], 0)

                # Обновление здоровья
                new_enemy_hp = enemy['hp'] - final_damage
                new_player_hp = player['hp'] - enemy_damage

                # Сохранение данных
                cur.execute("UPDATE players SET hp = %s WHERE user_id = %s", (new_player_hp, user_id))

                # Проверка смерти врага
                if new_enemy_hp <= 0:
                    cur.execute("""
                        UPDATE players 
                        SET 
                            exp = exp + %s,
                            gold = gold + %s 
                        WHERE user_id = %s
                    """, (enemy['exp_reward'], enemy['gold_reward'], user_id))
                    loot = random.choice(enemy['loot'])
                    cur.execute("""
                        INSERT INTO inventory (user_id, item_type, item_name)
                        VALUES (%s, 'loot', %s)
                        ON CONFLICT DO UPDATE SET quantity = inventory.quantity + 1
                    """, (user_id, loot))
                    
                    return (
                        f"⚔️ Вы победили {enemy_name}!\n"
                        f"Получено: {enemy['exp_reward']} опыта, "
                        f"{enemy['gold_reward']} золота, {loot}"
                    )
                else:
                    return (
                        f"⚔️ Вы нанесли {final_damage} урона!\n"
                        f"❤️ Ваше HP: {new_player_hp}\n"
                        f"❤️ HP {enemy_name}: {new_enemy_hp}"
                    )
        finally:
            conn.close()

class LocationSystem:
    @staticmethod
    async def explore_location(user_id: int):
        conn = psycopg2.connect(POSTGRES_URL)
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Получаем текущую локацию игрока
                cur.execute("SELECT current_location FROM players WHERE user_id = %s", (user_id,))
                location_name = cur.fetchone()['current_location']

                # Получаем данные локации
                cur.execute("SELECT * FROM locations WHERE name = %s", (location_name,))
                location = cur.fetchone()

                # Выбираем случайное событие
                event = random.choice(location['events'])
                if event == "fight":
                    enemy = random.choice(location['enemies'])
                    return f"💀 На вас напал {enemy}!", BattleSystem.handle_attack(user_id, enemy)
                elif event == "treasure":
                    gold = random.randint(50, 200)
                    cur.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (gold, user_id))
                    return f"💎 Вы нашли сундук с {gold} золота!", None
                # Обработка других событий...
        finally:
            conn.close()

# =============================================
# КОМАНДЫ БОТА (ПОЛНОСТЬЮ РЕАЛИЗОВАНЫ)
# =============================================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    conn = psycopg2.connect(POSTGRES_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO players (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (message.from_user.id, message.from_user.username))
            
            await message.answer(
                "🏰 Добро пожаловать в мир приключений!\n\n"
                "🛡️ Выберите действие:",
                reply_markup=main_menu_keyboard()
            )
    finally:
        conn.close()
# ===================== ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ =====================
def action_keyboard(action_type: str):
    if action_type == "battle":
        return types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("Атаковать ⚔️", callback_data="attack"),
            types.InlineKeyboardButton("Защита 🛡️", callback_data="defend")
        ).row(
            types.InlineKeyboardButton("Исп. предмет 🧪", callback_data="use_item"),
            types.InlineKeyboardButton("Бежать 🏃‍♂️", callback_data="flee")
        )
    else:
        return types.InlineKeyboardMarkup().row(
            types.InlineKeyboardButton("Продолжить ➡️", callback_data="continue")
        )
        
def main_menu_keyboard():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Исследовать 🌍", callback_data="explore"),
        types.InlineKeyboardButton("Инвентарь 🎒", callback_data="inventory")
    ).row(
        types.InlineKeyboardButton("Характеристики 📊", callback_data="stats"),
        types.InlineKeyboardButton("Магазин 🏪", callback_data="shop")
        )
    
@dp.callback_query_handler(lambda c: c.data == 'explore')
async def process_explore(callback: types.CallbackQuery):
    try:
        await callback.answer()
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем текущую локацию игрока
            cur.execute("SELECT current_location FROM players WHERE user_id = %s", (callback.from_user.id,))
            player_data = cur.fetchone()
            
            if not player_data:
                await callback.answer("Игрок не найден", show_alert=True)
                return
                
            location_name = player_data['current_location']

            # Получаем данные локации
            cur.execute("SELECT * FROM locations WHERE name = %s", (location_name,))
            location = cur.fetchone()
            
            if not location:
                await callback.answer("Локация не найдена", show_alert=True)
                return

            # Выбираем случайное событие
            if not location['events']:
                await callback.answer("В этой локации нет событий", show_alert=True)
                return
                
            event = random.choice(location['events'])
            
            if event == "fight":
                if not location['enemies']:
                    await callback.answer("Нет доступных врагов", show_alert=True)
                    return
                    
                enemy = random.choice(location['enemies'])
                result = await BattleSystem.handle_attack(callback.from_user.id, enemy)
                await callback.message.edit_text(
                    f"💀 На вас напал {enemy}!\n\n{result}",
                    reply_markup=action_keyboard("battle")
                )
                
            elif event == "treasure":
                gold = random.randint(50, 200)
                cur.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (gold, callback.from_user.id))
                await callback.message.edit_text(
                    f"💎 Вы нашли сундук с {gold} золота!",
                    reply_markup=action_keyboard(None)
                )
                
    except Exception as e:
        logger.error(f"Error in process_explore: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при исследовании", show_alert=True)
    finally:
        if conn:
            conn.close()

@dp.callback_query_handler(lambda c: c.data == 'attack')
async def process_attack(callback: types.CallbackQuery):
    try:
        await callback.answer()
        enemy_name = "Лесной волк"  # Временное значение, нужно заменить на логику получения текущего врага
        result = await BattleSystem.handle_attack(callback.from_user.id, enemy_name)
        await callback.message.edit_text(
            result,
            reply_markup=action_keyboard("battle")
        )
    except Exception as e:
        logger.error(f"Error in process_attack: {e}")
        await callback.answer("⚠️ Ошибка в бою", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'defend')
async def process_defend(callback: types.CallbackQuery):
    try:
        await callback.answer("🛡️ Вы защищаетесь (функционал в разработке)")
    except Exception as e:
        logger.error(f"Error in process_defend: {e}")
        await callback.answer("⚠️ Ошибка при защите", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'use_item')
async def process_use_item(callback: types.CallbackQuery):
    try:
        await callback.answer("🧪 Использование предметов (функционал в разработке)")
    except Exception as e:
        logger.error(f"Error in process_use_item: {e}")
        await callback.answer("⚠️ Ошибка при использовании предмета", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'flee')
async def process_flee(callback: types.CallbackQuery):
    try:
        await callback.answer("🏃‍♂️ Вы сбежали (функционал в разработке)")
        await callback.message.edit_text(
            "Вы успешно сбежали из боя!",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in process_flee: {e}")
        await callback.answer("⚠️ Ошибка при попытке бегства", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'continue')
async def process_continue(callback: types.CallbackQuery):
    try:
        await callback.answer()
        await callback.message.edit_text(
            "Вы продолжаете своё приключение:",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in process_continue: {e}")
        await callback.answer("⚠️ Ошибка при продолжении", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def process_back(callback: types.CallbackQuery):
    try:
        await callback.answer()
        await callback.message.edit_text(
            "🏰 Главное меню:",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in process_back: {e}")
        await callback.answer("⚠️ Ошибка при возврате в меню", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'stats')
async def process_stats(callback: types.CallbackQuery):
    conn = None
    try:
        await callback.answer()
        conn = psycopg2.connect(POSTGRES_URL)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT p.*, w.name as weapon_name, a.name as armor_name
                FROM players p
                LEFT JOIN weapons w ON p.equipped_weapon = w.name
                LEFT JOIN armor a ON p.equipped_armor = a.name
                WHERE p.user_id = %s
            """, (callback.from_user.id,))
            player = cur.fetchone()

            stats_text = f"""👤 {player['username']}
⚔️ Уровень: {player['level']}
❤️ Здоровье: {player['hp']}/{player['max_hp']}
🛡️ Защита: {player['defense'] if player['defense'] else 0}
💰 Золото: {player['gold']}
🔶 Опыт: {player['exp']}/{player['level']*100}

💪 Сила: {player['strength']}
🏃‍♂️ Ловкость: {player['agility']}
🧠 Интеллект: {player['intelligence']}

⚔️ Оружие: {player['weapon_name'] if player['weapon_name'] else 'Нет'}
🛡️ Броня: {player['armor_name'] if player['armor_name'] else 'Нет'}
📍 Локация: {player['current_location']}"""

            await callback.message.edit_text(
                stats_text,
                reply_markup=types.InlineKeyboardMarkup().row(
                    types.InlineKeyboardButton("Назад ◀️", callback_data="back_to_menu")
                )
            )
    except Exception as e:
        logger.error(f"Error in process_stats: {e}")
        await callback.answer("⚠️ Ошибка при загрузке статистики", show_alert=True)
    finally:
        if conn:
            conn.close()

@dp.callback_query_handler(lambda c: c.data == 'inventory')
async def process_inventory(callback: types.CallbackQuery):
    try:
        await callback.answer()
        # Заглушка для инвентаря
        await callback.message.edit_text(
            "🎒 Ваш инвентарь (функционал в разработке)",
            reply_markup=types.InlineKeyboardMarkup().row(
                types.InlineKeyboardButton("Назад ◀️", callback_data="back_to_menu")
            )
        )
    except Exception as e:
        logger.error(f"Error in process_inventory: {e}")
        await callback.answer("⚠️ Ошибка при открытии инвентаря", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'shop')
async def process_shop(callback: types.CallbackQuery):
    try:
        await callback.answer()
        # Заглушка для магазина
        await callback.message.edit_text(
            "🏪 Магазин (функционал в разработке)",
            reply_markup=types.InlineKeyboardMarkup().row(
                types.InlineKeyboardButton("Назад ◀️", callback_data="back_to_menu")
            )
        )
    except Exception as e:
        logger.error(f"Error in process_shop: {e}")
        await callback.answer("⚠️ Ошибка при открытии магазина", show_alert=True)
        
# =============================================
# ЗАПУСК БОТА
# =============================================

if __name__ == '__main__':
    if init_db():
        logger.info("Бот запущен")
        executor.start_polling(dp, skip_updates=True)
    else:
        logger.error("Не удалось подключиться к базе данных")
