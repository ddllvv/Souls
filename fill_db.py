from utils.database import create_connection

def add_locations():
    conn = create_connection()
    cursor = conn.cursor()
    
    locations = [
        ("Хаб", "Место отдыха. Здесь безопасно.", None, '{"enemies": [], "boss": null}'),
        ("Заброшенная крепость", "Темные коридоры, полные скелетов.", None, '{"enemies": ["Скелет"], "boss": "Каменный страж"}')
    ]
    
    cursor.executemany(
        "INSERT INTO locations (name, description, required_key, enemies) VALUES (?, ?, ?, ?)",
        locations
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_locations()
