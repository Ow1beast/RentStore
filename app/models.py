from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    card_number = Column(String, nullable=True)
    card_holder = Column(String, nullable=True)
    expiry = Column(String, nullable=True)
    cvc = Column(String, nullable=True)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    price_per_day = Column(Integer)
    purchase_price = Column(Integer)
    quantity = Column(Integer)

class Rental(Base):
    __tablename__ = "rentals"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    rented_at = Column(DateTime, default=datetime.utcnow)

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    purchased_at = Column(DateTime, default=datetime.utcnow)
