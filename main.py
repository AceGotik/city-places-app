from fastapi import FastAPI
from database import engine, Base
from models import Place
from sqlalchemy.orm import Session
from database import SessionLocal

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "City Places Backend Running"}

@app.get("/places")
def get_places():
    db: Session = SessionLocal()
    places = db.query(Place).all()
    return places
