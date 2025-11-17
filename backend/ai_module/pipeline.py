import json
from sqlalchemy.exc import IntegrityError

from backend.ai_module.model import (
    summarize_news,
    smart_summarize,
    summarize_multilang,
    summarize_text_safe,
)

from backend.ai_module.category import categorize
from backend.ai_module.cleaner import clean_article
from backend.ai_module.sentiment import detect_sentiment

from backend.db.database import SessionLocal
from backend.db.models import News, Article

from rust_core import fetch_full_articles


# ---------------------------------------------------------
#  Функция получения статей через Rust
# ---------------------------------------------------------
def _fetch_articles():
    print("🦀 Rust: собираем статьи...")
    return fetch_full_articles()


# ---------------------------------------------------------
#  Сохранение статей в Article (+ очистка, категории)
# ---------------------------------------------------------
def _upsert_articles(session, raw_json: str, with_summaries: bool = False):
    items = json.loads(raw_json)
    saved = 0

    for n in items[:20]:
        try:
            # --- Чистим текст ---
            raw_content = n.get("content", "") or ""
            content = clean_article(raw_content)

            # --- Пропуск маленьких статей ---
            if len(content) < 200:
                continue

            # --- Опциональная суммаризация ---
            summary_de = summarize_text_safe(content) if with_summaries else ""

            # --- Категоризация ---
            full_text_for_cat = (n.get("title", "") or "") + " " + content
            cat = categorize(full_text_for_cat)

            # --- Анализ настроения ---
            sentiment = detect_sentiment(full_text_for_cat)

            # --- Создание записи ---
            art = Article(
                title=n.get("title", "")[:512],
                url=n.get("url", "")[:1024],
                content=content,
                summary_de=summary_de or "",
                lang="de",
                category=cat,
                sentiment=sentiment,   # ⭐ добавлено
            )

            session.add(art)
            session.flush()
            saved += 1

        except IntegrityError:
            session.rollback()
        except Exception:
            session.rollback()

    if saved:
        print(f"💾 Сохранено статей: {saved}")


# ---------------------------------------------------------
#  /news — короткая выжимка
# ---------------------------------------------------------
def process_news_pipeline():
    session = SessionLocal()
    try:
        raw = _fetch_articles()
        _upsert_articles(session, raw, with_summaries=False)

        # Сохраняем в старую таблицу News (совместимость)
        news_list = json.loads(raw)
        for n in news_list[:5]:
            session.add(News(title=n.get("title", ""), url=n.get("url", ""), summary=""))
        session.commit()

        print("🤖 AI: создаём краткую выжимку...")
        summarized = summarize_news(raw)

        # Fallback, если модель вернула пустоту
        if not summarized or summarized.strip().startswith("⚠️"):
            from sqlalchemy import text
            rows = session.execute(text("""
                SELECT title, url
                FROM articles
                WHERE created_at >= datetime('now', '-1 day')
                ORDER BY created_at DESC
                LIMIT 5
            """)).fetchall()

            if rows:
                summarized = "\n\n".join(
                    [f"🗞️ {r[0]}\n🔗 {r[1]}" for r in rows]
                )
            else:
                summarized = "⚠️ Пока нет свежих новостей в истории."

        return summarized

    finally:
        session.close()


# ---------------------------------------------------------
#  /smartnews — глубокая выжимка
# ---------------------------------------------------------
def process_smart_pipeline():
    raw = _fetch_articles()
    print("🤖 AI: обрабатываем контент...")

    session = SessionLocal()
    try:
        _upsert_articles(session, raw, with_summaries=True)
        session.commit()
    finally:
        session.close()

    return smart_summarize(raw)


# ---------------------------------------------------------
#  /multilangnews — выжимка на DE/EN/RU
# ---------------------------------------------------------
def process_multilang_pipeline():
    raw = _fetch_articles()
    print("🤖 AI: создаём выжимку и переводы...")

    session = SessionLocal()
    try:
        _upsert_articles(session, raw, with_summaries=True)
        session.commit()
    finally:
        session.close()

    return summarize_multilang(raw)


# ---------------------------------------------------------
#  Автосбор для планировщика (каждые 2 часа)
# ---------------------------------------------------------
def auto_collect_news(fetch_fn, summarize_fn, session_maker):
    print("🦀 Rust: автоматический сбор новостей...")

    try:
        raw = fetch_fn()
    except Exception as e:
        print(f"❌ Ошибка fetch_fn: {e}")
        return "⚠️ Ошибка получения данных из Rust."

    if not raw:
        print("⚠️ Rust вернул пустоту")
        return "⚠️ Нет данных."

    print(f"📥 Пример данных: {raw[:300]}")

    # Пытаемся построить суммаризацию
    try:
        summarized = summarize_fn(raw)
    except Exception as e:
        print(f"❌ Ошибка summarize_fn: {e}")
        summarized = "⚠️ Ошибка суммаризации."

    # Сохранение в старую News (для истории)
    session = session_maker()
    count = 0
    try:
        news_list = json.loads(raw)
        for n in news_list[:5]:
            title = n.get("title", "").strip()
            url = n.get("url", "").strip()
            if title and url:
                session.add(News(title=title, url=url, summary=""))
                count += 1

        session.commit()
        print(f"💾 Сохранено статей в News: {count}")

    except Exception as e:
        print(f"❌ Ошибка работы с БД: {e}")
    finally:
        session.close()

    return summarized


# ---------------------------------------------------------
#  Категории — сколько статей в каждой
# ---------------------------------------------------------
def list_categories():
    session = SessionLocal()
    try:
        from sqlalchemy import text
        rows = session.execute(text("""
            SELECT category, COUNT(*)
            FROM articles
            WHERE created_at >= datetime('now', '-3 day')
            GROUP BY category
            ORDER BY COUNT(*) DESC
        """)).fetchall()

        return {row[0]: row[1] for row in rows}
    finally:
        session.close()


# ---------------------------------------------------------
#  Получить новости конкретной категории
# ---------------------------------------------------------
def get_news_by_category(cat: str):
    session = SessionLocal()
    try:
        from sqlalchemy import text
        rows = session.execute(text("""
            SELECT title, url
            FROM articles
            WHERE category = :cat
            ORDER BY created_at DESC
            LIMIT 10
        """), {"cat": cat}).fetchall()

        return [(r[0], r[1]) for r in rows]
    finally:
        session.close()

def get_sentiment_stats():
    session = SessionLocal()
    try:
        from sqlalchemy import text

        rows = session.execute(text("""
            SELECT sentiment, COUNT(*)
            FROM articles
            WHERE created_at >= datetime('now','-3 day')
            GROUP BY sentiment
        """)).fetchall()

        return {row[0]: row[1] for row in rows}

    finally:
        session.close()

def recommend_personal_news(chat_id: str):
    session = SessionLocal()

    try:
        # 1 — preferences
        prefs = session.query(UserPreferences).filter_by(chat_id=chat_id).first()
        if not prefs:
            return ["⚠️ У тебя пока нет профиля. Используй /setfav"]

        fav = prefs.favorite_categories.split(",") if prefs.favorite_categories else []
        target_sent = prefs.preferred_sentiment

        # 2 — получаем свежие статьи
        from sqlalchemy import text
        rows = session.execute(text("""
            SELECT title, url, category, sentiment
            FROM articles
            WHERE created_at >= datetime('now','-2 day')
        """)).fetchall()

        scored = []
        for t, url, cat, sent in rows:
            score = 0
            if cat in fav:
                score += 0.6
            if sent == target_sent:
                score += 0.2

            scored.append((score, t, url))

        # сортировка
        scored.sort(reverse=True, key=lambda x: x[0])

        # выбираем топ 5
        top = scored[:5]
        return [
            f"🗞️ {title}\n🔗 {url}"
            for _, title, url in top
        ]
    finally:
        session.close()
