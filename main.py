from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from database import engine, Base, SessionLocal
from models import Place, User, Vote, Favorite
from fastapi import Request

app = FastAPI()

# создаём таблицы
Base.metadata.create_all(bind=engine)

# =============================
# FRONT
# =============================

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html")

# =============================
# SCHEMA
# =============================

class PlaceSchema(BaseModel):
    name: str
    average_price: Optional[int] = None
    street: Optional[str] = None
    type: Optional[str] = None
    work_time: Optional[str] = None
    image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# =============================
# USER HELPER
# =============================

def get_or_create_user(db: Session, telegram_id: int):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# =============================
# PLACES
# =============================

@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    return db.query(Place).all()

@app.post("/places")
def create_place(place: PlaceSchema):
    db = SessionLocal()
    new_place = Place(**place.dict())
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place

# =============================
# DELETE PLACE (ADMIN ONLY)
# =============================

ADMIN_ID = 315901039  # ← ВСТАВЬ СВОЙ TELEGRAM ID

@app.delete("/admin/places/{place_id}")
def delete_place(place_id: int, telegram_id: int = Header(None)):
    db = SessionLocal()

    if telegram_id is None or int(telegram_id) != ADMIN_ID:
        return {"error": "Нет доступа"}

    # удаляем связанные голоса
    db.query(Vote).filter(Vote.place_id == place_id).delete()

    # удаляем избранное
    db.query(Favorite).filter(Favorite.place_id == place_id).delete()

    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        return {"error": "Заведение не найдено"}

    db.delete(place)
    db.commit()

    return {"message": "Удалено"}

# =============================
# VOTING (как в Pepper)
# =============================

@app.post("/places/{place_id}/vote")
def vote(place_id: int, value: int, telegram_id: int = Header(None)):
    print("TELEGRAM:", telegram_id)
    print("PLACE:", place_id)
    print("VALUE:", value)
    db = SessionLocal()

    if telegram_id is None:
        return {"error": "No telegram_id"}

    existing_vote = db.query(Vote).filter(
        Vote.place_id == place_id,
        Vote.telegram_id == telegram_id
    ).first()

    if existing_vote:
        if existing_vote.value == value:
            # повторное нажатие — удалить голос
            db.delete(existing_vote)
        else:
            # смена решения
            existing_vote.value = value
    else:
        new_vote = Vote(
            place_id=place_id,
            telegram_id=telegram_id,
            value=value
        )
        db.add(new_vote)

    db.commit()

    # пересчёт рейтинга
    total = db.query(func.coalesce(func.sum(Vote.value), 0))\
        .filter(Vote.place_id == place_id)\
        .scalar()

    place = db.query(Place).filter(Place.id == place_id).first()
    place.rating = total
    db.commit()

    return {"rating": total}

# =============================
# FAVORITES (toggle)
# =============================

@app.post("/places/{place_id}/favorite")
def add_favorite(place_id: int, telegram_id: int = Header()):
    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    existing = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.place_id == place_id
    ).first()

    if existing:
        return {"message": "Already in favorites"}

    fav = Favorite(user_id=user.id, place_id=place_id)
    db.add(fav)
    db.commit()

    return {"message": "Added"}

@app.delete("/places/{place_id}/favorite")
def remove_favorite(place_id: int, telegram_id: int = Header()):
    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    fav = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.place_id == place_id
    ).first()

    if fav:
        db.delete(fav)
        db.commit()

    return {"message": "Removed"}

@app.get("/favorites")
def get_favorites(telegram_id: int = Header()):
    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    place_ids = [f.place_id for f in favs]

    if not place_ids:
        return []

    return db.query(Place).filter(Place.id.in_(place_ids)).all()
