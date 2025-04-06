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

# Фоновая задача рассылки уведомлений за 15 дней до окончания аренды
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_FROM_NAME="Electro Rental",
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

@app.on_event("startup")
async def schedule_rental_notifications():
    from asyncio import create_task, sleep
    async def notify_loop():
        while True:
            await notify_expiring_rentals()
            await sleep(86400)  # раз в сутки
    create_task(notify_loop())

async def notify_expiring_rentals():
    db = SessionLocal()
    try:
        today = datetime.utcnow()
        rentals = db.query(models.Rental).all()
        for r in rentals:
            if not r.rented_at or not r.days:
                continue
            end_date = r.rented_at + timedelta(days=r.days)
            if (end_date - today).days == 15:
                user = db.query(models.User).filter_by(id=r.user_id).first()
                product = db.query(models.Product).filter_by(id=r.product_id).first()
                if user and product:
                    message = MessageSchema(
                        subject="Скоро завершение аренды",
                        recipients=[user.email],
                        body=f"Здравствуйте, {user.name}! \n Аренда товара '{product.name}' заканчивается {end_date.strftime('%d.%m.%Y')}. \n Пожалуйста, подготовьтесь к возврату или продлению. \n С уважением, Electro Rental",
                        subtype="plain"
                    )
                    fm = FastMail(conf)
                    await fm.send_message(message)
    finally:
        db.close()


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

app.mount("/", StaticFiles(directory="static", html=True), name="static")
