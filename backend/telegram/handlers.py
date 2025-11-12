from aiogram import Router, types
from aiogram.filters import Command
from rust_core import fetch_news
from backend.ai_module.pipeline import process_news_pipeline
from backend.db.database import SessionLocal
from backend.db.models import Subscriber

router = Router()

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет, я AI News Bot 🇩🇪\n"
        "Я собираю статьи с немецких СМИ и кратко излагаю их.\n\n"
        "👉 /news — получить свежие новости\n"
        "👉 /subscribe — подписаться на автообновления\n"
        "👉 /unsubscribe — отписаться"
    )

@router.message(Command("news"))
async def news_cmd(message: types.Message):
    await message.answer("🦀 Собираю новости...")
    from rust_core import fetch_news
    from backend.ai_module.pipeline import process_news_pipeline

    data = fetch_news()
    result = process_news_pipeline()

    if not result or not result.strip():
        await message.answer("⚠️ Не удалось сформировать новости — возможно, источники не вернули актуальных данных.")
        return

    # Отправляем итог
    await message.answer(result)


@router.message(Command("subscribe"))
async def subscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        exists = session.query(Subscriber).filter(Subscriber.chat_id == str(message.chat.id)).first()
        if exists:
            await message.answer("✅ Ты уже подписан.")
        else:
            session.add(Subscriber(chat_id=str(message.chat.id)))
            session.commit()
            await message.answer("✅ Подписка активна! Новости будут приходить каждые 2 часа.")
    finally:
        session.close()

@router.message(Command("unsubscribe"))
async def unsubscribe_cmd(message: types.Message):
    session = SessionLocal()
    try:
        sub = session.query(Subscriber).filter(Subscriber.chat_id == str(message.chat.id)).first()
        if sub:
            session.delete(sub)
            session.commit()
            await message.answer("❌ Подписка отменена.")
        else:
            await message.answer("Ты не был подписан.")
    finally:
        session.close()

@router.message(Command("smartnews"))
async def smartnews_cmd(message: types.Message):
    await message.answer("🧠 Секунду, я собираю и анализирую новости...")
    from backend.ai_module.pipeline import process_smart_pipeline
    result = process_smart_pipeline()
    await message.answer(result, parse_mode="Markdown")

    @router.message(Command("multilangnews"))
    async def multilang_cmd(message: types.Message):
        await message.answer("🌍 Собираю и перевожу новости...")
        from backend.ai_module.pipeline import process_multilang_pipeline
        result = process_multilang_pipeline()
        await message.answer(result, parse_mode="Markdown")
