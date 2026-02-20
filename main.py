from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import Place, User, Vote, Favorite
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE places 
        ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
    """))
    conn.execute(text("""
        ALTER TABLE places 
        ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
    """))
    conn.commit()

Base.metadata.create_all(bind=engine)


# ---------- FRONT ----------

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html")


# ---------- SCHEMA ----------

class PlaceSchema(BaseModel):
    name: str
    average_price: Optional[int] = None
    street: Optional[str] = None
    type: Optional[str] = None
    work_time: Optional[str] = None
    rating: Optional[int] = 0
    image: Optional[str] = None


# ---------- USER HELPER ----------

def get_or_create_user(db: Session, telegram_id: int):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------- PLACES ----------

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


# ---------- VOTING (1 user = 1 vote) ----------

@app.post("/places/{place_id}/vote")
def vote(place_id: int, value: int, telegram_id: int = Header()):
    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    existing_vote = db.query(Vote).filter(
        Vote.user_id == user.id,
        Vote.place_id == place_id
    ).first()

    place = db.query(Place).filter(Place.id == place_id).first()

    if not place:
        return {"error": "Place not found"}

    if existing_vote:
        return {"message": "Already voted"}

    vote = Vote(user_id=user.id, place_id=place_id, value=value)
    db.add(vote)

    place.rating += value

    db.commit()
    return {"message": "Voted"}


# ---------- FAVORITES ----------

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

    return {"message": "Added to favorites"}


@app.get("/favorites")
def get_favorites(telegram_id: int = Header()):
    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    place_ids = [f.place_id for f in favs]

    return db.query(Place).filter(Place.id.in_(place_ids)).all()

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
