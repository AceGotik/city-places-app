from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from database import engine, Base, SessionLocal
from models import Place, User, Vote, Favorite, Banner

app = FastAPI()

# создаём таблицы
Base.metadata.create_all(bind=engine)

# =============================
# CONFIG
# =============================

ADMIN_ID = 315901039  # ← ВСТАВЬ СВОЙ TELEGRAM ID

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

class BannerSchema(BaseModel):
    image: str
    link: Optional[str] = None

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
    db = SessionLocal()
    return db.query(Place).all()

@app.get("/places_with_vote")
def get_places_with_vote(telegram_id: int = Header(None)):
    db = SessionLocal()
    places = db.query(Place).all()

    result = []
    for place in places:
        user_vote = 0
        if telegram_id:
            vote = db.query(Vote).filter(
                Vote.place_id == place.id,
                Vote.telegram_id == telegram_id
            ).first()
            if vote:
                user_vote = vote.value

        result.append({
            "id": place.id,
            "name": place.name,
            "average_price": place.average_price,
            "street": place.street,
            "type": place.type,
            "work_time": place.work_time,
            "rating": place.rating,
            "image": place.image,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "user_vote": user_vote
        })

    return result

@app.post("/places")
def create_place(place: PlaceSchema):
    db = SessionLocal()
    new_place = Place(**place.dict(), rating=0)
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place

# =============================
# DELETE PLACE (ADMIN)
# =============================

@app.delete("/admin/places/{place_id}")
def delete_place(place_id: int, telegram_id: int = Header(None)):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    db = SessionLocal()

    db.query(Vote).filter(Vote.place_id == place_id).delete()
    db.query(Favorite).filter(Favorite.place_id == place_id).delete()

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return {"error": "Не найдено"}

    db.delete(place)
    db.commit()

    return {"message": "Удалено"}

# =============================
# VOTING (Pepper logic)
# =============================

@app.post("/places/{place_id}/vote")
def vote(place_id: int, value: int, telegram_id: int = Header(None)):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    db = SessionLocal()

    existing_vote = db.query(Vote).filter(
        Vote.place_id == place_id,
        Vote.telegram_id == telegram_id
    ).first()

    if existing_vote:
        if existing_vote.value == value:
            db.delete(existing_vote)  # убрать голос
        else:
            existing_vote.value = value  # сменить
    else:
        new_vote = Vote(
            place_id=place_id,
            telegram_id=telegram_id,
            value=value
        )
        db.add(new_vote)

    db.commit()

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
def toggle_favorite(place_id: int, telegram_id: int = Header(None)):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    existing = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.place_id == place_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed"}

    fav = Favorite(user_id=user.id, place_id=place_id)
    db.add(fav)
    db.commit()

    return {"message": "Added"}

@app.get("/favorites")
def get_favorites(telegram_id: int = Header(None)):
    if telegram_id is None:
        return []

    db = SessionLocal()
    user = get_or_create_user(db, telegram_id)

    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    place_ids = [f.place_id for f in favs]

    if not place_ids:
        return []

    return db.query(Place).filter(Place.id.in_(place_ids)).all()

# =============================
# BANNERS
# =============================

@app.get("/banners")
def get_banners():
    db = SessionLocal()
    return db.query(Banner).all()

@app.post("/admin/banners")
def create_banner(banner: BannerSchema, telegram_id: int = Header(None)):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    db = SessionLocal()
    new_banner = Banner(**banner.dict())
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)
    return new_banner

@app.put("/admin/banners/{banner_id}")
def update_banner(banner_id: int, banner: BannerSchema, telegram_id: int = Header(None)):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    db = SessionLocal()
    existing = db.query(Banner).filter(Banner.id == banner_id).first()

    if not existing:
        return {"error": "Не найден"}

    existing.image = banner.image
    existing.link = banner.link
    db.commit()

    return {"message": "Обновлено"}

@app.delete("/admin/banners/{banner_id}")
def delete_banner(banner_id: int, telegram_id: int = Header(None)):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    db = SessionLocal()
    banner = db.query(Banner).filter(Banner.id == banner_id).first()

    if not banner:
        return {"error": "Не найден"}

    db.delete(banner)
    db.commit()

    return {"message": "Удалено"}
