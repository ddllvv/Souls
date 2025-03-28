from aiogram import types
from aiogram.dispatcher import FSMContext
from config import dp, cursor, conn

@dp.message_handler(commands=['move'])
async def move_location(message: types.Message):
    player = get_player(message.from_user.id)
    cursor.execute("SELECT * FROM locations WHERE name=?", (player.current_location,))
    location = cursor.fetchone()

    # Клавиатура с доступными направлениями
    keyboard = types.InlineKeyboardMarkup()
    if location['required_key'] in player.inventory["items"]:
        keyboard.add(types.InlineKeyboardButton("Вперед", callback_data="move_forward"))
    keyboard.add(types.InlineKeyboardButton("В Хаб", callback_data="move_hub"))

    await message.answer("Выберите направление:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def process_move(callback: types.CallbackQuery):
    direction = callback.data.split('_')[1]
    player = get_player(callback.from_user.id)

    if direction == "hub":
        player.current_location = "Хаб"
        await callback.message.answer("Вы вернулись в Хаб.")
    elif direction == "forward":
        # Логика перехода на новую локацию
        pass
    update_player(player)
