from backend.ai_module.model import summarize_news, smart_summarize, summarize_multilang
from backend.db.database import SessionLocal
from backend.db.models import News
from rust_core import fetch_full_articles
import json


# --- Основной сбор данных (только через Rust full fetch) ---
def _fetch_articles():
    """Единый источник данных из Rust"""
    print("🦀 Rust: собираем статьи...")
    raw = fetch_full_articles()
    return raw


# --- /news (краткий дайджест) ---
def process_news_pipeline():
    """Rust → краткая выжимка"""
    session = SessionLocal()
    try:
        raw = _fetch_articles()
        news_list = json.loads(raw)

        # Сохраняем в БД
        for n in news_list[:5]:
            session.add(News(title=n.get("title", ""), url=n.get("url", ""), summary=""))
        session.commit()

        print("🤖 AI: создаём краткую выжимку...")
        summarized = summarize_news(raw)
        return summarized
    finally:
        session.close()


# --- /smartnews ---
def process_smart_pipeline():
    """Полный AI-анализ"""
    raw = _fetch_articles()
    print("🤖 AI: обрабатываем контент...")
    return smart_summarize(raw)


# --- /multilangnews ---
def process_multilang_pipeline():
    """Многоязычный вариант"""
    raw = _fetch_articles()
    print("🤖 AI: создаём выжимку и переводы...")
    return summarize_multilang(raw)


# --- Автообновление каждые 2 часа ---
def auto_collect_news(session_maker=SessionLocal):
    """Для автосбора — использует тот же Rust full fetch"""
    raw = _fetch_articles()
    summarized = summarize_news(raw)
    session = session_maker()
    try:
        news_list = json.loads(raw)
        for n in news_list[:5]:
            session.add(News(title=n["title"], url=n["url"], summary=""))
        session.commit()
        return summarized
    finally:
        session.close()
