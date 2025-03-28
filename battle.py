from aiogram import types
from aiogram.dispatcher import FSMContext
from config import dp, cursor, conn
from models import Enemy, enemies_db

class BattleState:
    ENEMY_HP = 'enemy_hp'
    PLAYER_HP = 'player_hp'

@dp.message_handler(commands=['attack'], state="*")
async def attack_enemy(message: types.Message, state: FSMContext):
    data = await state.get_data()
    enemy = enemies_db[data['enemy_name']]
    player = get_player(message.from_user.id)  # Функция загрузки из БД

    # Урон игрока
    damage = 10 + (player.level * 2)
    if player.weapon == enemy.weakness:
        damage *= 2

    # Обновляем HP врага
    new_enemy_hp = data[BattleState.ENEMY_HP] - damage
    await state.update_data({BattleState.ENEMY_HP: new_enemy_hp})

    # Ответный удар врага
    player_hp = data[BattleState.PLAYER_HP] - enemy.attack
    await state.update_data({BattleState.PLAYER_HP: player_hp})

    # Проверка на смерть
    if new_enemy_hp <= 0:
        await message.answer(f"⚔️ Вы победили {enemy.name}! +{enemy.hp // 2} золота")
        update_gold(player.user_id, enemy.hp // 2)
        await state.finish()
    elif player_hp <= 0:
        await message.answer("☠️ Вы погибли! Возрождение в Хабе.")
        respawn_player(player.user_id)
        await state.finish()
    else:
        await message.answer(
            f"🗡 Вы нанесли {damage} урона. У врага осталось {new_enemy_hp} HP.\n"
            f"💢 Враг атакует в ответ! Ваше HP: {player_hp}"
  )
