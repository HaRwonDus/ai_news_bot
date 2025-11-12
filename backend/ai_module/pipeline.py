import json
from sqlalchemy.exc import IntegrityError
from backend.ai_module.model import (
    summarize_news,
    smart_summarize,
    summarize_multilang,
    summarize_text_safe
)
from backend.db.database import SessionLocal
from backend.db.models import News, Article
from rust_core import fetch_full_articles


# --- Вспомогательная функция: получение статей через Rust ---
def _fetch_articles():
    print("🦀 Rust: собираем статьи...")
    return fetch_full_articles()


# --- Вспомогательная: сохранение статей в БД ---
def _upsert_articles(session, raw_json: str, with_summaries: bool = False):
    items = json.loads(raw_json)
    saved = 0
    for n in items[:20]:
        try:
            summary_de = (
                summarize_text_safe(n.get("content", ""))
                if with_summaries else ""
            )
            art = Article(
                title=n.get("title", "")[:512],
                url=n.get("url", "")[:1024],
                content=n.get("content", ""),
                summary_de=summary_de or "",
                lang="de",
            )
            session.add(art)
            session.flush()
            saved += 1
        except IntegrityError:
            session.rollback()  # уже есть по unique(url)
        except Exception:
            session.rollback()
    if saved:
        print(f"💾 Сохранено статей: {saved}")


# --- /news: краткая выжимка ---
def process_news_pipeline():
    session = SessionLocal()
    try:
        raw = _fetch_articles()
        _upsert_articles(session, raw, with_summaries=False)

        # Старая таблица News (для совместимости)
        news_list = json.loads(raw)
        for n in news_list[:5]:
            session.add(
                News(title=n.get("title", ""), url=n.get("url", ""), summary="")
            )
        session.commit()

        print("🤖 AI: создаём краткую выжимку...")
        summarized = summarize_news(raw)

        # Fallback, если модель не дала результат
        if not summarized or summarized.strip().startswith("⚠️"):
            from sqlalchemy import text
            rows = session.execute(text("""
                SELECT title, url FROM articles
                WHERE created_at >= datetime('now','-1 day')
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


# --- /smartnews: глубокая выжимка ---
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


# --- /multilangnews: многоязычный ---
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


# --- автообновление (для планировщика) ---
def auto_collect_news(fetch_fn, summarize_fn, session_maker):
    """
    Rust → AI → сохранение в БД (автоматический сбор)
    """
    print("🦀 Rust: автоматический сбор новостей...")

    raw = None
    try:
        raw = fetch_fn()
        if not raw:
            print("⚠️ fetch_fn() вернул пустой результат.")
            return "⚠️ Не удалось получить новости."

        print(f"📥 Пример данных от fetch_fn: {str(raw)[:500]}")
    except Exception as e:
        print(f"❌ Ошибка при вызове fetch_fn: {e}")
        return "⚠️ Ошибка при получении данных из Rust."

    # Пробуем сделать саммари
    try:
        summarized = summarize_fn(raw)
    except Exception as e:
        print(f"❌ Ошибка при summarize_fn: {e}")
        summarized = "⚠️ Ошибка при суммаризации новостей."

    # Работа с базой
    session = session_maker()
    count = 0
    try:
        news_list = json.loads(raw)
        for n in news_list[:5]:
            title = n.get("title", "").strip()
            url = n.get("url", "").strip()
            if not title or not url:
                continue
            session.add(News(title=title, url=url, summary=""))
            count += 1
        session.commit()
        print(f"💾 Сохранено статей: {count}")
    except Exception as e:
        print(f"❌ Ошибка при работе с БД: {e}")
    finally:
        session.close()

    return summarized