from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
    if existing:
        return
    admin = User(
        name=settings.FIRST_ADMIN_NAME,
        email=settings.FIRST_ADMIN_EMAIL,
        role=UserRole.ADMIN,
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
    )
    db.add(admin)
    db.commit()


def init() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    init()
    print("Database initialized and admin seeded.")
