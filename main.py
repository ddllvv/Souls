from config import dp
import handlers.battle
import handlers.locations
import handlers.inventory

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
