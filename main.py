from fastapi import FastAPI
from fastapi.responses import FileResponse
from database import engine, Base, SessionLocal
from models import Place
from sqlalchemy.orm import Session
from pydantic import BaseModel

app = FastAPI()

Base.metadata.create_all(bind=engine)


# ---------- FRONTEND ----------

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html")


# ---------- API ----------

@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    return db.query(Place).all()


class PlaceCreate(BaseModel):
    name: str
    average_price: int
    street: str
    type: str
    work_time: str
    rating: int


@app.post("/places")
def create_place(place: PlaceCreate):
    db = SessionLocal()
    new_place = Place(**place.dict())
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place


@app.delete("/places/{place_id}")
def delete_place(place_id: int):
    db = SessionLocal()
    place = db.query(Place).filter(Place.id == place_id).first()
    if place:
        db.delete(place)
        db.commit()
    return {"message": "deleted"}


@app.put("/places/{place_id}")
def update_place(place_id: int, place_data: PlaceCreate):
    db = SessionLocal()
    place = db.query(Place).filter(Place.id == place_id).first()

    if place:
        for key, value in place_data.dict().items():
            setattr(place, key, value)

        db.commit()
        db.refresh(place)

    return place
