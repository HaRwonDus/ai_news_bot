from sqlalchemy import Column, Integer, String, Text, DateTime, Index, func
from backend.db.database import Base


# --- Старая таблица новостей (для совместимости) ---
class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512))
    url = Column(String(1024))
    summary = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Подписчики (для автообновлений) ---
class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Новая таблица: полные статьи ---
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    summary_de = Column(Text, default="")
    summary_en = Column(Text, default="")
    summary_ru = Column(Text, default="")
    lang = Column(String(8), default="de")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_articles_created_at", "created_at"),
        Index("idx_articles_title", "title"),
        Index("idx_articles_url", "url"),
    )
