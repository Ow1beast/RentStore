from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
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
    return db.query(models.Product).filter(models.Product.quantity > 0).all()

@app.post("/rent/{product_id}")
def rent_product(
    product_id: int,
    data: schemas.RentRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user)
):
    product = db.query(models.Product).filter_by(id=product_id).first()
    if not product or product.quantity < 1:
        raise HTTPException(status_code=400, detail="Товар недоступен для аренды")

    product.quantity -= 1
    db.add(models.Rental(
        user_id=user.id,
        product_id=product.id,
        rented_at=datetime.utcnow(),
        days=data.days
    ))

    user.card_number = data.card_number
    user.card_holder = data.card_holder
    user.expiry = data.expiry
    user.cvc = data.cvc

    db.commit()
    return {"message": "Товар арендован"}

@app.post("/buy/{product_id}")
def buy_product(
    product_id: int,
    data: schemas.PaymentData,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user)
):
    product = db.query(models.Product).filter_by(id=product_id).first()
    if not product or product.quantity < 1:
        raise HTTPException(status_code=400, detail="Товар недоступен для покупки")
    product.quantity -= 1
    db.add(models.Purchase(user_id=user.id, product_id=product.id))

    user.card_number = data.card_number
    user.card_holder = data.card_holder
    user.expiry = data.expiry
    user.cvc = data.cvc

    db.commit()
    return {"message": "Товар куплен"}

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

@app.get("/users/history")
def get_user_history(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user)
):
    rentals = db.query(models.Rental).filter_by(user_id=user.id).all()
    purchases = db.query(models.Purchase).filter_by(user_id=user.id).all()

    def serialize(obj):
        return {
            "product_name": db.query(models.Product).filter_by(id=obj.product_id).first().name,
            "rented_at": getattr(obj, "rented_at", None),
            "returned_at": getattr(obj, "returned_at", None),
            "days": getattr(obj, "days", None),
            "purchased_at": getattr(obj, "purchased_at", None)
        }

    return {
        "rentals": [serialize(r) for r in rentals],
        "purchases": [serialize(p) for p in purchases]
    }

@app.get("/users/")
def list_users(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    users = db.query(models.User).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "is_admin": u.is_admin} for u in users]

@app.post("/users/{user_id}/make_admin")
def make_user_admin(user_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    target.is_admin = True
    db.commit()
    return {"message": "Пользователь теперь администратор"}

@app.post("/users/{user_id}/revoke_admin")
def revoke_admin(user_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    target_user.is_admin = False
    db.commit()
    return {"detail": "Права администратора сняты"}

@app.get("/admin/rentals")
def admin_rental_overview(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    rentals = db.query(models.Rental).all()
    result = []
    for rental in rentals:
        u = db.query(models.User).filter(models.User.id == rental.user_id).first()
        p = db.query(models.Product).filter(models.Product.id == rental.product_id).first()
        result.append({
            "user_name": u.name,
            "user_email": u.email,
            "product_name": p.name,
            "rented_at": rental.rented_at,
            "days": rental.days,
            "returned_at": rental.returned_at
        })
    return result

app.mount("/", StaticFiles(directory="static", html=True), name="static")
