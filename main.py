from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import Place
from pydantic import BaseModel
from fastapi import Header, HTTPException

app = FastAPI()

Base.metadata.create_all(bind=engine)

# ---------- FRONTEND ----------
@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


# ---------- SCHEMA ----------
class PlaceSchema(BaseModel):
    name: str
    rating: int | None = 0
    average_price: int | None = None
    street: str | None = None
    type: str | None = None
    work_time: str | None = None


# ---------- GET ALL ----------
@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    return db.query(Place).all()


# ---------- CREATE ----------
@app.post("/places")
def create_place(place: PlaceSchema):
    db = SessionLocal()
    new_place = Place(**place.dict())
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place


# ---------- UPDATE ----------
@app.put("/places/{place_id}")
def update_place(place_id: int, place: PlaceSchema):
    db = SessionLocal()
    db_place = db.query(Place).filter(Place.id == place_id).first()

    if not db_place:
        raise HTTPException(status_code=404, detail="Not found")

    for key, value in place.dict().items():
        setattr(db_place, key, value)

    db.commit()
    db.refresh(db_place)
    return db_place


# ---------- DELETE ----------
@app.delete("/places/{place_id}")
def delete_place(place_id: int):
    db = SessionLocal()
    db_place = db.query(Place).filter(Place.id == place_id).first()

    if not db_place:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(db_place)
    db.commit()
    return {"message": "Deleted"}

ADMIN_ID = 315901039  # ← ВСТАВЬ СВОЙ TELEGRAM ID


@app.get("/admin")
def serve_admin(x_telegram_id: int = Header(None)):
    if x_telegram_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse("admin.html")
