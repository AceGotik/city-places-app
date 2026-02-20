from sqlalchemy import Column, Integer, String, Text
from database import Base

class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)
    rating = Column(Integer, default=0)
    average_price = Column(Integer)
    street = Column(String)
    type = Column(String)
    work_time = Column(String)
