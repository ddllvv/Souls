import sqlite3
from sqlite3 import Error

def create_connection():
    """Создает подключение к SQLite-базе."""
    conn = None
    try:
        conn = sqlite3.connect('data/database.db')
        print("Подключение к SQLite успешно!")
        return conn
    except Error as e:
        print(f"Ошибка подключения: {e}")
    return conn

def init_db():
    """Инициализирует таблицы в БД."""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Игроки
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        username TEXT,
        level INTEGER DEFAULT 1,
        hp INTEGER DEFAULT 100,
        max_hp INTEGER DEFAULT 100,
        gold INTEGER DEFAULT 50,
        weapon TEXT DEFAULT "Кинжал",
        armor TEXT DEFAULT "Тряпье",
        current_location TEXT DEFAULT "Хаб",
        inventory TEXT DEFAULT '{"items": []}'
    )''')
    
    # Локации
    cursor.execute('''CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        description TEXT,
        required_key TEXT NULL,
        enemies TEXT  # JSON: {"enemies": ["Скелет"], "boss": "Демон"}
    )''')
    
    conn.commit()
    conn.close()
