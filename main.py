from fastapi import FastAPI, Header, HTTPException
from database import engine, Base, SessionLocal
from models import Place
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

Base.metadata.create_all(bind=engine)

# 🔐 ТВОЙ Telegram ID
ADMIN_ID = 315901039  # ← ВСТАВЬ СЮДА СВОЙ TELEGRAM ID


@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    return db.query(Place).all()


class PlaceCreate(BaseModel):
    name: str
    rating: int = 0
    average_price: int
    street: str
    type: str
    work_time: str


@app.post("/places")
def create_place(place: PlaceCreate, telegram_id: int = Header(None)):
    if telegram_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Not allowed")

    db = SessionLocal()

    new_place = Place(
        name=place.name,
        rating=place.rating,
        average_price=place.average_price,
        street=place.street,
        type=place.type,
        work_time=place.work_time
    )

    db.add(new_place)
    db.commit()
    db.refresh(new_place)

    return new_place
