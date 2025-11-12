from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from rust_core import fetch_news
from backend.ai_module.model import summarize_news
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(msg: Message):
    await msg.answer("Привет! Я собираю новости по Германии 🇩🇪.\nНапиши /news чтобы получить сводку.")

@dp.message(Command("news"))
async def send_news(msg: Message):
    await msg.answer("🦀 Собираю новости...")
    data = fetch_news()
    summary = summarize_news(data)
    await msg.answer(f"🇩🇪 Новости Германии:\n\n{summary}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
