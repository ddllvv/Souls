class Player:
    def __init__(self, user_id):
        self.user_id = user_id
        self.level = 1
        self.hp = 100
        self.max_hp = 100
        self.stamina = 10
        self.gold = 50
        self.weapon = "Кинжал"
        self.armor = "Тряпье"
        self.current_location = "Хаб"
        self.inventory = {"items": [], "weight": 0}

class Enemy:
    def __init__(self, name, hp, attack, weakness):
        self.name = name
        self.hp = hp
        self.attack = attack
        self.weakness = weakness  # "fire", "blunt", etc.

# Пример врага
enemies_db = {
    "Скелет": Enemy("Скелет", hp=50, attack=15, weakness="blunt"),
    "Каменный страж": Enemy("Каменный страж", hp=200, attack=30, weakness="lightning")
}
