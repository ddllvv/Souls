from aiogram import executor, types
from config import dp, bot
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def on_startup(_):
    await bot.send_message(os.getenv("ADMIN_ID"), "Бот запущен")

# Основные команды
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("🔥 Добро пожаловать в Dark Souls бот! 🔥\n\n"
                        "🛡️ Доступные команды:\n"
                        "/start - начать игру\n"
                        "/status - ваш статус\n"
                        "/explore - исследовать локацию")

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    await message.answer("Ваш статус:\n"
                        "Уровень: 1\n"
                        "HP: 100/100\n"
                        "Оружие: Кинжал")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
