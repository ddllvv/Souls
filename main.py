from aiogram import executor, types
from config import dp, bot, get_db_connection
import logging
import os

logging.basicConfig(level=logging.INFO)

async def on_startup(_):
    await bot.send_message(os.getenv("ADMIN_ID"), "🔥 Бот запущен!")

# Проверяем, зарегистрирован ли игрок в БД
async def is_user_registered(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = %s", (user_id,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

# Регистрируем нового игрока
async def register_user(user_id: int, username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO players (user_id, username) VALUES (%s, %s)",
        (user_id, username)
    )
    conn.commit()
    cursor.close()
    conn.close()

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    if await is_user_registered(user_id):
        await message.answer("🗡 Вы уже в игре! Используй /explore")
    else:
        await register_user(user_id, username)
        await message.answer(
            "🔥 Добро пожаловать в Dark Souls бот!\n\n"
            "🛡️ Доступные команды:\n"
            "/explore - начать исследование\n"
            "/status - ваш статус"
        )

# Команда /explore
@dp.message_handler(commands=['explore'])
async def cmd_explore(message: types.Message):
    await message.answer(
        "🌑 Вы в мрачном подземелье...\n"
        "Выберите действие:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Идти вперед", callback_data="dungeon_forward"),
            types.InlineKeyboardButton("Осмотреться", callback_data="dungeon_look")
        )
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
