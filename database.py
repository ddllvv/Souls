import psycopg2
from psycopg2 import sql, OperationalError
import os

def get_db():
    try:
        conn = psycopg2.connect(os.getenv("postgresql://soulsbase_user:7mUrpaI5iLfNRmGlK2QMiMhf8swRgZob@dpg-cvjdpqhr0fns73fvebvg-a/soulsbase"))  # Используем переменную окружения
        return conn
    except OperationalError as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        return None

def init_db():
    conn = get_db()
    if not conn:
        return

    cursor = conn.cursor()
    
    # Создание таблицы игроков
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id BIGINT PRIMARY KEY,
            username TEXT,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            gold INTEGER DEFAULT 50,
            weapon TEXT DEFAULT 'Кинжал',
            current_location TEXT DEFAULT 'Хаб'
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
