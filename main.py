from fastapi import FastAPI
from database import engine, Base
from models import Place
from sqlalchemy.orm import Session
from database import SessionLocal

app = FastAPI()

Base.metadata.create_all(bind=engine)

from fastapi.responses import FileResponse

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    places = db.query(Place).all()
    return places

from pydantic import BaseModel

class PlaceCreate(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None


@app.post("/places")
def create_place(place: PlaceCreate):
    db = SessionLocal()
    new_place = Place(
        name=place.name,
        category=place.category,
        description=place.description
    )
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place

@app.get("/places")
def get_places():
    db = SessionLocal()
    return db.query(Place).all()
