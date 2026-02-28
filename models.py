from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Text, Column, Integer, String, Float, ForeignKey, DateTime, BigInteger 
from datetime import datetime

class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    image = Column(String, nullable=False)
    link = Column(String, nullable=True)
    
class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    place_id = Column(Integer, ForeignKey("places.id"))
    value = Column(Integer)  # 1 или -1
    
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    average_price = Column(Integer)
    street = Column(String)
    type = Column(String)
    work_time = Column(String)
    rating = Column(Integer, default=0)
    image = Column(String)
    # 👇 ВСТАВИТЬ ВОТ ЭТИ ДВЕ СТРОКИ
    latitude = Column(Float)
    longitude = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    place_id = Column(Integer, ForeignKey("places.id"))

class Visited(Base):
    __tablename__ = "visited"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger)
    place_id = Column(Integer, ForeignKey("places.id"))
    
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger)
    place_id = Column(Integer, ForeignKey("places.id"))
    text = Column(Text)
    recommendation = Column(String)  # positive / negative / neutral
    created_at = Column(DateTime, default=datetime.utcnow)
    username = Column(String)

class ReviewLike(Base):
    __tablename__ = "review_likes"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    telegram_id = Column(BigInteger)
