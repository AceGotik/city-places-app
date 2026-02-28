from fastapi import FastAPI, Header, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Column, Integer, BigInteger, ForeignKey
from pydantic import BaseModel
from typing import Optional
from database import engine, Base, SessionLocal
from models import (
    Place, User, Vote, Favorite, Banner, Visited,
    Review, ReviewLike, MenuPhoto, PlacePhoto
)
import shutil
import os
import uuid

# ensure uploads dir exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create tables if not exist
Base.metadata.create_all(bind=engine)

ADMIN_ID = 315901039  # замените на свой ID если нужно


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

    places = db.query(Place).all()
    result = []

    for place in places:

        place_photos = db.query(PlacePhoto).filter(
            PlacePhoto.place_id == place.id
        ).all()

        menu_photos = db.query(MenuPhoto).filter(
            MenuPhoto.place_id == place.id
        ).all()

        result.append({
            "id": place.id,
            "name": place.name,
            "average_price": place.average_price,
            "street": place.street,
            "type": place.type,
            "work_time": place.work_time,
            "rating": place.rating,
            "image": place.image,  # обложка
            "latitude": place.latitude,
            "longitude": place.longitude,
            "created_at": place.created_at,
            "photos": [
                {"id": p.id, "image": p.image}
                for p in place_photos
            ],
            "menu": [
                {"id": m.id, "image": m.image}
                for m in menu_photos
            ]
        })

    return result


@app.get("/places_with_vote")
def get_places_with_vote(
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    places = db.query(Place).all()
    result = []

    for place in places:

        user_vote = 0
        is_favorite = False
        is_visited = False

        if telegram_id:

            vote = db.query(Vote).filter(
                Vote.place_id == place.id,
                Vote.telegram_id == telegram_id
            ).first()

            if vote:
                user_vote = vote.value

            fav = db.query(Favorite).join(User).filter(
                User.telegram_id == telegram_id,
                Favorite.place_id == place.id
            ).first()

            if fav:
                is_favorite = True

            visited = db.query(Visited).filter(
                Visited.place_id == place.id,
                Visited.telegram_id == telegram_id
            ).first()

            if visited:
                is_visited = True


        # 🔥 ДОБАВЛЯЕМ ФОТО
        place_photos = db.query(PlacePhoto).filter(
            PlacePhoto.place_id == place.id
        ).all()

        menu_photos = db.query(MenuPhoto).filter(
            MenuPhoto.place_id == place.id
        ).all()


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
            "is_favorite": is_favorite,
            "is_visited": is_visited,
            "created_at": place.created_at,

            # 🔥 ВОТ ЭТО ГЛАВНОЕ
            "photos": [
                {"id": p.id, "image": p.image}
                for p in place_photos
            ],
            "menu": [
                {"id": m.id, "image": m.image}
                for m in menu_photos
            ]
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
    db.query(MenuPhoto).filter(MenuPhoto.place_id == place_id).delete()

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return {"error": "Не найдено"}

    db.delete(place)
    db.commit()

    return {"message": "Удалено"}


@app.put("/admin/places/{place_id}")
def update_place(
    place_id: int,
    place_data: PlaceSchema,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return {"error": "Не найдено"}

    place.name = place_data.name
    place.average_price = place_data.average_price
    place.street = place_data.street
    place.type = place_data.type
    place.work_time = place_data.work_time
    place.image = place_data.image
    place.latitude = place_data.latitude
    place.longitude = place_data.longitude

    db.commit()

    return {"message": "Обновлено"}


# =============================
@app.post("/places/{place_id}/vote")
def vote(
    place_id: int,
    value: int,
    telegram_id: int = Header(None),
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
    place_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    print("TELEGRAM ID:", telegram_id)
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
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return []

    user = get_or_create_user(db, telegram_id)

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


@app.post("/places/{place_id}/visit")
def mark_visited(
    place_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    existing = db.query(Visited).filter(
        Visited.place_id == place_id,
        Visited.telegram_id == telegram_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed"}

    new_visit = Visited(
        place_id=place_id,
        telegram_id=telegram_id
    )
    db.add(new_visit)
    db.commit()

    return {"message": "Added"}


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


# =============================
# REVIEWS
# =============================
@app.post("/places/{place_id}/review")
def add_review(
    place_id: int,
    recommendation: str,
    text: str,
    username: str = Query(None),
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    # Один отзыв на пользователя
    existing = db.query(Review).filter(
        Review.place_id == place_id,
        Review.telegram_id == telegram_id
    ).first()

    if existing:
        existing.text = text
        existing.recommendation = recommendation
        db.commit()
        return {"message": "Updated"}

    new_review = Review(
        place_id=place_id,
        telegram_id=telegram_id,
        username=username,
        text=text,
        recommendation=recommendation
    )

    db.add(new_review)
    db.commit()

    return {"message": "Added"}


@app.get("/places/{place_id}/reviews")
def get_reviews(
    place_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(
        Review.place_id == place_id
    ).order_by(Review.created_at.desc()).all()

    result = []

    for r in reviews:

        # 🔹 считаем лайки
        likes_count = db.query(ReviewLike).filter(
            ReviewLike.review_id == r.id
        ).count()

        # 🔹 проверяем лайкнул ли пользователь
        user_liked = False
        if telegram_id:
            user_liked = db.query(ReviewLike).filter(
                ReviewLike.review_id == r.id,
                ReviewLike.telegram_id == telegram_id
            ).first() is not None

        result.append({
            "id": r.id,
            "text": r.text,
            "recommendation": r.recommendation,
            "username": getattr(r, "username", None),
            "telegram_id": r.telegram_id,
            "created_at": r.created_at,
            "is_mine": r.telegram_id == telegram_id,
            "likes": likes_count,
            "user_liked": user_liked
        })

    return result


@app.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.telegram_id == telegram_id
    ).first()

    if not review:
        return {"error": "Not allowed"}

    db.delete(review)
    db.commit()

    return {"message": "Deleted"}


@app.post("/reviews/{review_id}/like")
def toggle_review_like(
    review_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    existing = db.query(ReviewLike).filter(
        ReviewLike.review_id == review_id,
        ReviewLike.telegram_id == telegram_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed"}

    new_like = ReviewLike(
        review_id=review_id,
        telegram_id=telegram_id
    )
    db.add(new_like)
    db.commit()

    return {"message": "Added"}


# =============================
# MENU PHOTOS (simple add via URL) - оставляем для совместимости
# =============================
@app.post("/places/{place_id}/menu_photo")
def add_menu_photo(
    place_id: int,
    image: str,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id is None:
        return {"error": "No telegram_id"}

    photo = MenuPhoto(
        place_id=place_id,
        image=image
    )

    db.add(photo)
    db.commit()

    return {"message": "Added"}


@app.get("/places/{place_id}/menu_photos")
def get_menu_photos(
    place_id: int,
    db: Session = Depends(get_db)
):
    photos = db.query(MenuPhoto).filter(
        MenuPhoto.place_id == place_id
    ).all()

    return photos


# =============================
# ADMIN: upload place photos (multiple) and menu images (multiple)
# =============================
@app.post("/admin/places/{place_id}/photos")
def upload_place_photos(
    place_id: int,
    files: list[UploadFile] = File(...),
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    place = db.query(Place).filter(Place.id == place_id).first()
    if not place:
        return {"error": "Не найдено"}

    import uuid
    urls = []

    for file in files:
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = f"uploads/{unique_name}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        photo = PlacePhoto(
            place_id=place_id,
            image=f"/{file_path}"
        )

        db.add(photo)
        urls.append(f"/{file_path}")

    db.commit()

    # первое фото — обложка если её нет
    if not place.image and urls:
        place.image = urls[0]
        db.commit()

    return {"urls": urls}

@app.get("/places/{place_id}/photos")
def get_place_photos(place_id: int, db: Session = Depends(get_db)):
    photos = db.query(PlacePhoto).filter(
        PlacePhoto.place_id == place_id
    ).all()

    return photos


@app.post("/admin/places/{place_id}/menu")
def upload_menu_photos(
    place_id: int,
    files: list[UploadFile] = File(...),
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    """
    Загружает несколько фото меню, добавляет записи MenuPhoto.
    """
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    urls = []

    for file in files:
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join("uploads", unique_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url = f"/uploads/{unique_name}"
        photo = MenuPhoto(
            place_id=place_id,
            image=url
        )
        db.add(photo)
        urls.append(url)

    db.commit()

    return {"urls": urls}


# static uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# =============================
# Admin helpers to list/delete uploaded photos
# =============================
@app.get("/admin/places/{place_id}/photos")
def get_admin_place_photos(place_id: int, db: Session = Depends(get_db)):

    result = []

    place_photos = db.query(PlacePhoto).filter(
        PlacePhoto.place_id == place_id
    ).all()

    for p in place_photos:
        result.append({
            "id": p.id,
            "image": p.image,
            "type": "place"
        })

    menu_photos = db.query(MenuPhoto).filter(
        MenuPhoto.place_id == place_id
    ).all()

    for m in menu_photos:
        result.append({
            "id": m.id,
            "image": m.image,
            "type": "menu"
        })

    return result



@app.delete("/admin/menu/{photo_id}")
def delete_menu_photo(
    photo_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    photo = db.query(MenuPhoto).filter(MenuPhoto.id == photo_id).first()
    if not photo:
        return {"error": "Не найдено"}

    # удаляем файл с диска если есть
    try:
        path = photo.image
        if path and path.startswith("/uploads/"):
            fs_path = path.lstrip("/")
            if os.path.exists(fs_path):
                os.remove(fs_path)
    except Exception:
        pass

    db.delete(photo)
    db.commit()

    return {"message": "Удалено"}

@app.delete("/admin/place_photo/{photo_id}")
def delete_place_photo(
    photo_id: int,
    telegram_id: int = Header(None),
    db: Session = Depends(get_db)
):
    if telegram_id != ADMIN_ID:
        return {"error": "Нет доступа"}

    photo = db.query(PlacePhoto).filter(
        PlacePhoto.id == photo_id
    ).first()

    if not photo:
        return {"error": "Не найдено"}

    # удаляем файл
    try:
        path = photo.image
        if path and path.startswith("/uploads/"):
            fs_path = path.lstrip("/")
            if os.path.exists(fs_path):
                os.remove(fs_path)
    except:
        pass

    db.delete(photo)
    db.commit()

    return {"message": "Удалено"}
