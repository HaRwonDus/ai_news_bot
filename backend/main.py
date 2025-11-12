import asyncio
import os
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Важно: Windows async event loop fix
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- Локальные импорты ---
from backend.telegram.handlers import router
from backend.ai_module.pipeline import auto_collect_news
from backend.db.database import Base, engine, SessionLocal
from backend.db.models import Subscriber
from rust_core import fetch_news
from backend.ai_module.model import summarize_news


# --- Загружаем токен ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в .env")


# --- Автоматическая рассылка ---
async def send_auto_news(bot: Bot):
    session = SessionLocal()
    try:
        subs = session.query(Subscriber).all()
    finally:
        session.close()

    if not subs:
        print("⚠️ Нет подписчиков для автообновления.")
        return

    print(f"📡 Отправляем автообновление для {len(subs)} пользователей...")
    summarized = auto_collect_news(fetch_news, summarize_news, SessionLocal)

    for s in subs:
        try:
            await bot.send_message(
                int(s.chat_id),
                f"🕓 Автоматическая сводка новостей:\n\n{summarized}",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            print(f"Ошибка при отправке {s.chat_id}: {e}")


# --- Главная асинхронная функция ---
async def main():
    # Создание таблиц, если их нет
    Base.metadata.create_all(bind=engine)

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Планировщик автообновлений
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(send_auto_news, "interval", hours=2, args=[bot])
    scheduler.start()

    print("🤖 Бот запущен! Автоновости каждые 2 часа.")
    await dp.start_polling(bot)


# --- Точка входа ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот остановлен вручную.")

