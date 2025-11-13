from aiogram import Router, types
from aiogram.filters import Command
from backend.ai_module.pipeline import (
    process_news_pipeline,
    process_smart_pipeline,
    process_multilang_pipeline,
    list_categories,
    get_news_by_category
)
from backend.db.database import SessionLocal
from backend.db.models import Subscriber

router = Router()


# --- /start ---
@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет, я 🤖 *AI News Bot* 🇩🇪\n"
        "Я собираю свежие новости с немецких СМИ и создаю краткие выжимки.\n\n"
        "📌 Команды:\n"
        "👉 /news — короткая сводка\n"
        "👉 /smartnews — подробный анализ\n"
        "👉 /multilangnews — новости на 3 языках (DE/EN/RU)\n"
        "👉 /subscribe — получать автообновления каждые 2 часа\n"
        "👉 /unsubscribe — отменить подписку",
        parse_mode="Markdown"
    )


# --- /news ---
@router.message(Command("news"))
async def news_cmd(message: types.Message):
    await message.answer("🦀 Собираю новости...")
    try:
        result = process_news_pipeline()
        if not result or not result.strip():
            await message.answer(
                "⚠️ Не удалось сформировать новости — возможно, источники временно недоступны."
            )
        else:
            await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обработке: {e}")


# --- /smartnews ---
@router.message(Command("smartnews"))
async def smartnews_cmd(message: types.Message):
    await message.answer("🧠 Секунду, я собираю и анализирую новости...")
    try:
        result = process_smart_pipeline()
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обработке: {e}")


# --- /multilangnews ---
@router.message(Command("multilangnews"))
async def multilang_cmd(message: types.Message):
    await message.answer("🌍 Собираю и перевожу новости...")
    try:
        result = process_multilang_pipeline()
        await message.answer(result, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при обработке: {e}")


# --- /subscribe ---
@router.message(Command("subscribe"))
async def subscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        exists = session.query(Subscriber).filter(
            Subscriber.chat_id == str(message.chat.id)
        ).first()
        if exists:
            await message.answer("✅ Ты уже подписан.")
        else:
            session.add(Subscriber(chat_id=str(message.chat.id)))
            session.commit()
            await message.answer("✅ Подписка активна! Новости будут приходить каждые 2 часа.")
    finally:
        session.close()


# --- /unsubscribe ---
@router.message(Command("unsubscribe"))
async def unsubscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        sub = session.query(Subscriber).filter(
            Subscriber.chat_id == str(message.chat.id)
        ).first()
        if sub:
            session.delete(sub)
            session.commit()
            await message.answer("❌ Подписка отменена.")
        else:
            await message.answer("Ты не был подписан.")
    finally:
        session.close()

async def send_category_news(message, category):
    session = SessionLocal()
    try:
        rows = session.execute(
            f"""
            SELECT title, url FROM articles
            WHERE category = :cat
            ORDER BY created_at DESC
            LIMIT 5
            """
        , {"cat": category}).fetchall()
    finally:
        session.close()

    if not rows:
        await message.answer(f"⚠️ Нет новостей категории '{category}'.")
        return

    text = "\n\n".join([f"🗞️ {r[0]}\n🔗 {r[1]}" for r in rows])
    await message.answer(text)

@router.message(Command("categories"))
async def categories_cmd(message: types.Message):
    cats = list_categories()

    if not cats:
        await message.answer("⚠️ Категории пусты. Пока нет новостей.")
        return

    text = "📊 *Новости по категориям (3 дня):*\n\n"
    for cat, count in cats.items():
        text += f"• *{cat}* — {count}\n"

    await message.answer(text, parse_mode="Markdown")

@router.message(Command("news_politics"))
async def news_politics(message: types.Message):
    await send_category_news(message, "politics")

@router.message(Command("news_economy"))
async def news_economy(message: types.Message):
    await send_category_news(message, "economy")

@router.message(Command("news_tech"))
async def news_tech(message: types.Message):
    await send_category_news(message, "tech")

@router.message(Command("news_world"))
async def news_world(message: types.Message):
    await send_category_news(message, "world")

@router.message(Command("news_society"))
async def news_society(message: types.Message):
    await send_category_news(message, "society")

@router.message(Command("category"))
async def category_cmd(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Использование: `/category politics`", parse_mode="Markdown")
        return

    cat = parts[1].lower()

    news = get_news_by_category(cat)

    if not news:
        await message.answer(f"⚠️ Нет новостей в категории: *{cat}*", parse_mode="Markdown")
        return

    text = f"🗞️ *Топ новости категории: {cat}*\n\n"
    for t, url in news:
        text += f"• {t}\n🔗 {url}\n\n"

    await message.answer(text, parse_mode="Markdown")
