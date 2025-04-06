from app.database import SessionLocal
from app import models

products = [
    {
        "name": "MacBook Pro 14 M1",
        "description": "Apple, 14 дюймов, 16 ГБ RAM, SSD 512 ГБ",
        "price_per_day": 5500,
        "purchase_price": 790000,
        "quantity": 3
    },
    {
        "name": "Lenovo IdeaPad 3",
        "description": "15.6\", AMD Ryzen 5, 8 ГБ, SSD 256 ГБ",
        "price_per_day": 2500,
        "purchase_price": 320000,
        "quantity": 5
    },
    {
        "name": "iPhone 13",
        "description": "Apple, 128 ГБ, с Face ID",
        "price_per_day": 4200,
        "purchase_price": 500000,
        "quantity": 4
    },
    {
        "name": "Canon EOS M50",
        "description": "Беззеркальный фотоаппарат + объектив",
        "price_per_day": 4000,
        "purchase_price": 360000,
        "quantity": 2
    },
    {
        "name": "Sony WH-1000XM4",
        "description": "Беспроводные наушники с шумоподавлением",
        "price_per_day": 1200,
        "purchase_price": 145000,
        "quantity": 6
    }
]

db = SessionLocal()

for p in products:
    exists = db.query(models.Product).filter_by(name=p["name"]).first()
    if not exists:
        db.add(models.Product(**p))

db.commit()
db.close()

print("✅ Товары добавлены")
