from aiogram import Router, types
from aiogram.filters import Command

from sqlalchemy import text

# Пайплайны обработки новостей
from backend.ai_module.pipeline import (
    process_news_pipeline,
    process_smart_pipeline,
    process_multilang_pipeline,
    list_categories,
    get_news_by_category,
    get_sentiment_stats,
    recommend_personal_news,
)

# База данных
from backend.db.database import SessionLocal
from backend.db.models import Subscriber, UserPreferences, UserCategoryStat

router = Router()


# ---------------------------------------------------------
#  /start
# ---------------------------------------------------------
@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет, я 🤖 *AI News Bot* 🇩🇪\n"
        "Я собираю свежие новости с немецких СМИ и создаю краткие выжимки.\n\n"
        "📌 Команды:\n"
        "👉 /news — короткая сводка\n"
        "👉 /smartnews — подробный анализ\n"
        "👉 /multilangnews — на 3 языках (DE/EN/RU)\n"
        "👉 /categories — список категорий\n"
        "👉 /category <name> — новости по категории\n"
        "👉 /sentiment — тональность новостей\n"
        "👉 /recommend — персональные рекомендации\n"
        "👉 /setfav — выбрать любимые категории\n"
        "👉 /setlang — язык дайджеста\n"
        "👉 /setsentiment — фильтр по тональности\n"
        "👉 /subscribe — автообновления\n"
        "👉 /unsubscribe — отменить подписку",
        parse_mode="Markdown"
    )


# ---------------------------------------------------------
#  /news
# ---------------------------------------------------------
@router.message(Command("news"))
async def news_cmd(message: types.Message):
    await message.answer("🦀 Собираю новости...")
    try:
        result = process_news_pipeline()
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обработке: {e}")


# ---------------------------------------------------------
#  /smartnews
# ---------------------------------------------------------
@router.message(Command("smartnews"))
async def smartnews_cmd(message: types.Message):
    await message.answer("🧠 Анализирую контент...")
    try:
        result = process_smart_pipeline()
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


# ---------------------------------------------------------
#  /multilangnews
# ---------------------------------------------------------
@router.message(Command("multilangnews"))
async def multilang_cmd(message: types.Message):
    await message.answer("🌍 Обрабатываю и перевожу...")
    try:
        result = process_multilang_pipeline()
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


# ---------------------------------------------------------
#  /subscribe
# ---------------------------------------------------------
@router.message(Command("subscribe"))
async def subscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        exists = session.query(Subscriber).filter_by(
            chat_id=str(message.chat.id)
        ).first()

        if exists:
            await message.answer("✅ Ты уже подписан.")
        else:
            session.add(Subscriber(chat_id=str(message.chat.id)))
            session.commit()
            await message.answer("✅ Подписка активирована!")
    finally:
        session.close()


# ---------------------------------------------------------
#  /unsubscribe
# ---------------------------------------------------------
@router.message(Command("unsubscribe"))
async def unsubscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        sub = session.query(Subscriber).filter_by(
            chat_id=str(message.chat.id)
        ).first()

        if sub:
            session.delete(sub)
            session.commit()
            await message.answer("❌ Подписка отменена.")
        else:
            await message.answer("Ты не был подписан.")
    finally:
        session.close()


# ---------------------------------------------------------
#  Вспомогательная: отправить новости выбранной категории
# ---------------------------------------------------------
async def send_category_news(message: types.Message, category: str):
    session = SessionLocal()
    try:
        rows = session.execute(
            text("""
                SELECT title, url FROM articles
                WHERE category = :cat
                ORDER BY created_at DESC
                LIMIT 5
            """),
            {"cat": category}
        ).fetchall()

        # Логируем интерес пользователя
        chat_id = str(message.chat.id)
        stat = session.query(UserCategoryStat).filter_by(
            chat_id=chat_id,
            category=category,
        ).first()

        if not stat:
            stat = UserCategoryStat(chat_id=chat_id, category=category, clicks=1)
            session.add(stat)
        else:
            stat.clicks += 1

        session.commit()

    finally:
        session.close()

    if not rows:
        await message.answer(f"⚠️ Нет новостей категории '{category}'.")
        return

    formatted = "\n\n".join([f"🗞️ {r[0]}\n🔗 {r[1]}" for r in rows])
    await message.answer(formatted)


# ---------------------------------------------------------
#  /categories
# ---------------------------------------------------------
@router.message(Command("categories"))
async def categories_cmd(message: types.Message):
    cats = list_categories()

    if not cats:
        await message.answer("⚠️ Категории пусты.")
        return

    text = "📊 *Категории за 3 дня:*\n\n"
    for cat, count in cats.items():
        text += f"• *{cat}* — {count}\n"

    await message.answer(text, parse_mode="Markdown")


# ---------------------------------------------------------
#  /category <name>
# ---------------------------------------------------------
@router.message(Command("category"))
async def category_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: `/category politics`", parse_mode="Markdown")
        return

    cat = parts[1].lower()
    news = get_news_by_category(cat)

    if not news:
        await message.answer(f"⚠️ В категории *{cat}* нет новостей.", parse_mode="Markdown")
        return

    text = f"📰 *Новости категории {cat}:*\n\n"
    for title, url in news:
        text += f"• {title}\n🔗 {url}\n\n"

    await message.answer(text, parse_mode="Markdown")


# ---------------------------------------------------------
#  /sentiment
# ---------------------------------------------------------
@router.message(Command("sentiment"))
async def sentiment_cmd(message: types.Message):
    stats = get_sentiment_stats()
    total = sum(stats.values())

    if total == 0:
        await message.answer("⚠️ Нет данных для анализа.")
        return

    msg = (
        "🧠 *Тональность новостей (3 дня)*\n\n"
        f"🟢 Позитивные: {stats.get('positive', 0)}\n"
        f"⚪ Нейтральные: {stats.get('neutral', 0)}\n"
        f"🔴 Негативные: {stats.get('negative', 0)}\n\n"
        f"Всего статей: {total}"
    )

    await message.answer(msg, parse_mode="Markdown")


# ---------------------------------------------------------
#  /recommend
# ---------------------------------------------------------
@router.message(Command("recommend"))
async def recommend_cmd(message: types.Message):
    news = recommend_personal_news(str(message.chat.id))

    if not news:
        await message.answer("⚠️ Пока нет рекомендаций.")
        return

    msg = "🎯 *Персональная подборка:*\n\n" + "\n\n".join(news)
    await message.answer(msg, parse_mode="Markdown")


# ---------------------------------------------------------
#  /setfav (любимые категории)
# ---------------------------------------------------------
@router.message(Command("setfav"))
async def setfav_cmd(message: types.Message):
    args = message.text.split()[1:]

    valid = {"politics", "economy", "tech", "world", "society"}

    chosen = [a.lower() for a in args if a.lower() in valid]

    if not chosen:
        await message.answer(
            "Использование: `/setfav politics tech`\n"
            "Доступные: politics, economy, tech, world, society",
            parse_mode="Markdown"
        )
        return

    session = SessionLocal()
    try:
        prefs = session.query(UserPreferences).filter_by(
            chat_id=str(message.chat.id)
        ).first()

        if not prefs:
            prefs = UserPreferences(chat_id=str(message.chat.id))

        prefs.favorite_categories = ",".join(chosen)
        session.add(prefs)
        session.commit()

    finally:
        session.close()

    await message.answer(
        f"⭐ Любимые категории обновлены:\n*{', '.join(chosen)}*",
        parse_mode="Markdown"
    )


# ---------------------------------------------------------
#  /setlang
# ---------------------------------------------------------
@router.message(Command("setlang"))
async def setlang_cmd(message: types.Message):
    args = message.text.split()[1:]
    if not args or args[0].lower() not in {"de", "en", "ru"}:
        await message.answer("Использование: `/setlang de|en|ru`")
        return

    lang = args[0].lower()

    session = SessionLocal()
    try:
        prefs = session.query(UserPreferences).filter_by(
            chat_id=str(message.chat.id)
        ).first()

        if not prefs:
            prefs = UserPreferences(chat_id=str(message.chat.id))

        prefs.preferred_lang = lang
        session.add(prefs)
        session.commit()

    finally:
        session.close()

    await message.answer(f"🌍 Язык установлен: *{lang}*", parse_mode="Markdown")


# ---------------------------------------------------------
#  /setsentiment
# ---------------------------------------------------------
@router.message(Command("setsentiment"))
async def setsentiment_cmd(message: types.Message):
    args = message.text.split()[1:]
    if not args or args[0].lower() not in {"positive", "neutral", "negative"}:
        await message.answer("Использование: `/setsentiment positive|neutral|negative`")
        return

    sent = args[0].lower()

    session = SessionLocal()
    try:
        prefs = session.query(UserPreferences).filter_by(
            chat_id=str(message.chat.id)
        ).first()

        if not prefs:
            prefs = UserPreferences(chat_id=str(message.chat.id))

        prefs.preferred_sentiment = sent
        session.add(prefs)
        session.commit()

    finally:
        session.close()

    await message.answer(
        f"🧠 Предпочтительная тональность: *{sent}*",
        parse_mode="Markdown"
    )
