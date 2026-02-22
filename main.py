from fastapi import FastAPI, Header, Depends, Query 
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from database import engine, Base, SessionLocal
from models import Place, User, Vote, Favorite, Banner
from sqlalchemy import text

app = FastAPI()

# ✅ ДОБАВЛЕН CORS (БОЛЬШЕ НИЧЕГО НЕ МЕНЯЛОСЬ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

ADMIN_ID = 315901039  # твой ID


# =============================
# DB DEPENDENCY (ВАЖНО)
# =============================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================
# FRONT
# =============================

@app.get("/")
def serve_frontend():
    response = FileResponse("index.html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.middleware("http")
async def disable_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html")


# =============================
# SCHEMAS
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

@app.get("/debug-encoding")
def debug_encoding(db: Session = Depends(get_db)):
    result = db.execute("SHOW client_encoding;").fetchone()
    return {"client_encoding": result[0]}


@app.get("/places")
def get_places(db: Session = Depends(get_db)):
    return db.query(Place).all()


@app.get("/places_with_vote")
def get_places_with_vote(
    telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
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
            "user_vote": user_vote,
            "created_at": place.created_at
        })

    return result


@app.post("/places")
def create_place(place: PlaceSchema, db: Session = Depends(get_db)):

    if place.type:
        try:
            place.type = place.type.encode('latin1').decode('utf-8')
        except:
            pass

    if place.name:
        try:
            place.name = place.name.encode('latin1').decode('utf-8')
        except:
            pass

    if place.street:
        try:
            place.street = place.street.encode('latin1').decode('utf-8')
        except:
            pass

    new_place = Place(**place.dict(), rating=0)
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place


# =============================
# DELETE PLACE
# =============================

@app.delete("/admin/places/{place_id}")
def delete_place(
    place_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    db.query(Vote).filter(Vote.place_id == place_id).delete()
    db.query(Favorite).filter(Favorite.place_id == place_id).delete()

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return {"error": "Не найдено"}

    db.delete(place)
    db.commit()

    return {"message": "Удалено"}


# =============================
# VOTING
# =============================

@app.post("/places/{place_id}/vote")
def vote(
    place_id: int,
    value: int,
    telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    existing_vote = db.query(Vote).filter(
        Vote.place_id == place_id,
        Vote.telegram_id == telegram_id
    ).first()

    if existing_vote:
        if existing_vote.value == value:
            db.delete(existing_vote)
        else:
            existing_vote.value = value
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
# FAVORITES
# =============================

@app.post("/places/{place_id}/favorite")
def toggle_favorite(
    print("TELEGRAM ID:", telegram_id)
    place_id: int,
    telegram_id: int = Query(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

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
def get_favorites(
    telegram_id: Optional[int] = Header(None),
    q_telegram_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    tg = telegram_id or q_telegram_id
    if tg is None:
        return []

    user = get_or_create_user(db, tg)

    favs = db.query(Favorite).filter(Favorite.user_id == user.id).all()
    place_ids = [f.place_id for f in favs]

    if not place_ids:
        return []

    places = db.query(Place).filter(Place.id.in_(place_ids)).all()

    result = []
    for place in places:
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
            "created_at": place.created_at.isoformat() if place.created_at else None
        })

    return result
# =============================
# BANNERS
# =============================

@app.get("/banners")
def get_banners(db: Session = Depends(get_db)):
    return db.query(Banner).all()


@app.post("/admin/banners")
def create_banner(
    banner: BannerSchema,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    new_banner = Banner(**banner.dict())
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)
    return new_banner


@app.put("/admin/banners/{banner_id}")
def update_banner(
    banner_id: int,
    banner: BannerSchema,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    existing = db.query(Banner).filter(Banner.id == banner_id).first()
    if not existing:
        return {"error": "Не найден"}

    existing.image = banner.image
    existing.link = banner.link
    db.commit()

    return {"message": "Обновлено"}


@app.delete("/admin/banners/{banner_id}")
def delete_banner(
    banner_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        return {"error": "Не найден"}

    db.delete(banner)
    db.commit()

    return {"message": "Удалено"}
