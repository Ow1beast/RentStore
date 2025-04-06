from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash

def create_user(db: Session, user: schemas.UserCreate):
    from .auth import get_password_hash
    hashed = get_password_hash(user.password)
    db_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hashed,
        is_admin=user.is_admin 
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()
