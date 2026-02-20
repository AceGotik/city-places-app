from sqlalchemy import Column, Integer, String
from database import Base

class Place(Base):
    __tablename__ = "places_new"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    average_price = Column(Integer)
    street = Column(String)
    type = Column(String)
    work_time = Column(String)
    rating = Column(Integer, default=0)
    image = Column(String)
