from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.staticfiles import StaticFiles
from . import auth, crud, schemas, models
from .deps import get_db
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/users/")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/products/")
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

from datetime import datetime
from fastapi import HTTPException

@app.post("/rent/{product_id}")
def rent_product(product_id: int, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    product = db.query(models.Product).filter_by(id=product_id).first()
    if not product or product.quantity < 1:
        raise HTTPException(status_code=400, detail="Товар недоступен для аренды")
    product.quantity -= 1
    db.add(models.Rental(user_id=user.id, product_id=product.id))
    db.commit()
    return {"message": "Товар арендован"}

@app.post("/buy/{product_id}")
def buy_product(product_id: int, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    product = db.query(models.Product).filter_by(id=product_id).first()
    if not product or product.quantity < 1:
        raise HTTPException(status_code=400, detail="Товар недоступен для покупки")
    product.quantity -= 1
    db.add(models.Purchase(user_id=user.id, product_id=product.id))
    db.commit()
    return {"message": "Товар куплен"}

from fastapi import Body

@app.post("/products/")
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.post("/products/")
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user)
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

app.mount("/", StaticFiles(directory="static", html=True), name="static")
