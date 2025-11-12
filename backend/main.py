import asyncio
import os
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.telegram.handlers import router
from backend.ai_module.pipeline import auto_collect_news
from backend.db.database import Base, engine, SessionLocal
from backend.db.models import Subscriber
from rust_core import fetch_news
from backend.ai_module.model import summarize_news
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def send_auto_news(bot: Bot):
    session = SessionLocal()
    subs = session.query(Subscriber).all()
    session.close()

    if not subs:
        return

    print(f"📡 Отправляем автообновление для {len(subs)} пользователей...")
    summarized = auto_collect_news(fetch_news, summarize_news, SessionLocal)
    for s in subs:
        try:
            await bot.send_message(int(s.chat_id), f"🕓 Автоматическая сводка новостей:\n\n{summarized}")
        except Exception as e:
            print(f"Ошибка при отправке {s.chat_id}: {e}")

async def main():
    Base.metadata.create_all(bind=engine)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_auto_news, "interval", hours=2, args=[bot])
    scheduler.start()

    print("🤖 Бот запущен! Автоновости каждые 2 часа.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
