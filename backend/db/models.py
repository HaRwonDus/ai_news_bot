from sqlalchemy import Column, Integer, String, Text, DateTime, func
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

    category = Column(String(32), default="other")

    sentiment = Column(String(16), default="neutral")

    created_at = Column(DateTime, server_default=func.now())



class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    chat_id = Column(String, unique=True)

    favorite_categories = Column(String, default="")   # "politics,tech"
    preferred_lang = Column(String, default="de")      # de|en|ru
    preferred_sentiment = Column(String, default="neutral")  # positive|neutral|negative

    updated_at = Column(DateTime, server_default=func.now())


class UserCategoryStat(Base):
    __tablename__ = "user_category_stats"

    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True)
    category = Column(String(32))
    clicks = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

