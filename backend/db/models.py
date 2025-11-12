from sqlalchemy import Column, Integer, String, DateTime, func
from backend.db.database import Base

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String)
    summary = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscriber(Base):
    __tablename__ = "subscribers"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
