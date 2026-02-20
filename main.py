from fastapi import FastAPI
from fastapi.responses import FileResponse
from database import engine, Base, SessionLocal
from models import Place
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

Base.metadata.drop_all(bind=engine)
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


# ---------- API ----------

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


@app.put("/places/{place_id}")
def update_place(place_id: int, place: PlaceSchema):
    db = SessionLocal()
    db_place = db.query(Place).filter(Place.id == place_id).first()

    if db_place:
        for key, value in place.dict().items():
            setattr(db_place, key, value)

        db.commit()
        db.refresh(db_place)

    return db_place


@app.delete("/places/{place_id}")
def delete_place(place_id: int):
    db = SessionLocal()
    db_place = db.query(Place).filter(Place.id == place_id).first()

    if db_place:
        db.delete(db_place)
        db.commit()

    return {"message": "deleted"}


@app.post("/places/{place_id}/vote")
def vote(place_id: int, value: int):
    db = SessionLocal()
    place = db.query(Place).filter(Place.id == place_id).first()

    if place:
        place.rating += value
        db.commit()
        db.refresh(place)

    return place
