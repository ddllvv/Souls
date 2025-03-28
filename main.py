import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import psycopg2
from psycopg2 import OperationalError

# --- Настройка логов ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Инициализация бота ---
bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- Подключение к PostgreSQL ---
def get_db():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    except OperationalError as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None

# --- Проверка регистрации игрока ---
async def is_player_exists(user_id: int) -> bool:
    conn = get_db()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM players WHERE user_id = %s", (user_id,))
            return cur.fetchone() is not None
    finally:
        conn.close()

# --- Регистрация нового игрока ---
async def register_player(user_id: int, username: str):
    conn = get_db()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO players (user_id, username, current_location) "
                "VALUES (%s, %s, 'Хаб')",
                (user_id, username)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        return False
    finally:
        conn.close()

# --- Команда /start ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Безымянный"
    
    if await is_player_exists(user_id):
        await message.answer("🔮 Вы уже в игре! Используйте /explore")
    else:
        if await register_player(user_id, username):
            await message.answer(
                "🔥 Добро пожаловать в Dark Souls бот!\n\n"
                "🛡️ Доступные команды:\n"
                "/explore - исследовать локацию\n"
                "/status - ваш статус\n"
                "/inventory - инвентарь"
            )
        else:
            await message.answer("⚠️ Ошибка регистрации. Попробуйте позже.")

# --- Команда /explore ---
@dp.message_handler(commands=['explore'])
async def cmd_explore(message: types.Message):
    if not await is_player_exists(message.from_user.id):
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
        
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Идти вперед", callback_data="move_forward"),
        types.InlineKeyboardButton("Осмотреться", callback_data="look_around")
    )
    
    await message.answer(
        "🌑 Вы стоите в мрачном коридоре. Что будете делать?",
        reply_markup=keyboard
    )

# --- Обработка кнопок ---
@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def process_move(callback: types.CallbackQuery):
    action = callback.data.split('_')[1]
    
    if action == "forward":
        await callback.message.edit_text(
            "Вы осторожно продвигаетесь вперед...\n"
            "Внезапно перед вами появляется Скелет!",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("Атаковать", callback_data="fight_skeleton"),
                types.InlineKeyboardButton("Бежать", callback_data="run_away")
            )
        )
    await callback.answer()

# --- Запуск бота ---
async def on_startup(dp):
    await bot.send_message(os.getenv("ADMIN_ID"), "🤖 Бот успешно запущен!")
    logger.info("Bot started")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        timeout=60,
        relax=0.1
)
