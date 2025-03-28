from aiogram import executor
from config import dp, bot
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def on_startup(_):
    await bot.send_message(os.getenv("ADMIN_ID"), "Бот запущен")

# Регистрируем хэндлеры здесь, а не в отдельных файлах
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в Dark Souls бот! Используй /help")

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer("Доступные команды:\n/start - начать\n/status - статус")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
