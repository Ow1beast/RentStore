from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    sub: Optional[str] = None

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class ProductCreate(BaseModel):
    name: str
    description: str
    price_per_day: int
    purchase_price: int
    quantity: int
