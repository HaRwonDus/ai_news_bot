from aiogram import Router, types
from aiogram.filters import Command
from backend.ai_module.pipeline import (
    process_news_pipeline,
    process_smart_pipeline,
    process_multilang_pipeline,
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
