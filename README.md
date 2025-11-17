#  AI News Bot 🇩🇪  
### Rust-powered German news aggregator with ML summarization, multilingual output, sentiment analysis & personal recommendations

---

##  Overview

**AI News Bot** is an intelligent Telegram system that automatically collects news from German media and turns them into structured, multilingual, personalized digests.

It uses:

-  **Rust** for ultra-fast scraping  
-  **Python ML pipelines** (summaries, translations, sentiment)  
-  **Smart text cleaning**  
-  **Automatic category detection**  
-  **Personal recommendations**  
-  **Scheduled Telegram updates**  
-  **SQLite + SQLAlchemy** persistence  

This project demonstrates a fully integrated AI/ML + Rust + Telegram architecture.

---

##  Features

###  Rust fast-scraper (`rust_core`)
- Fetches full articles (title, URL, content)
- Cleans and normalizes data before sending to Python

###  AI processing pipeline (Python)
- Summarization (short & long)
- Translation to EN / RU
- Safe summarization wrapper
- Automatic categorization (politics, tech, world, etc.)
- Sentiment detection (positive / neutral / negative)
- Multilingual news digests

###  Telegram bot (Aiogram)
Commands:

| Command | Description |
|--------|-------------|
| `/news` | Quick summary digest |
| `/smartnews` | Deep multi-article analysis |
| `/multilangnews` | Output in DE/EN/RU |
| `/categories` | Category list |
| `/category <name>` | Articles from a category |
| `/sentiment` | Sentiment stats |
| `/subscribe` | Auto news every 2 hours |
| `/unsubscribe` | Disable auto news |
| `/setfav <cats>` | Set favorite categories |
| `/setlang de|en|ru` | Preferred digest language |
| `/setsentiment positive|neutral|negative` | Tone preference |
| `/recommend` | Personalized recommendations |

---

##  System Architecture

```
              ┌─────────────────────────┐
              │       Telegram Bot       │
              │    (Aiogram router)      │
              └───────────┬─────────────┘
                          │
                          ▼
          ┌────────────────────────────────────┐
          │        Python AI Pipeline          │
          │  Summaries | Categories | Sentiment│
          └───────────────┬────────────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │     Rust Core     │
                │ (HTML Scraper)    │
                └───────────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │     Database      │
                │  (SQLite + ORM)   │
                └───────────────────┘
```

---

##  Installation

### 1️⃣ Clone repo  
```bash
git clone https://github.com/YOUR_USERNAME/ai_news_bot
cd ai_news_bot
```

### 2️⃣ Install Python env  
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Install Rust  
```
https://rustup.rs
```

### 4️⃣ Build Rust module  
from `rust_core` directory:

```bash
cargo build --release
```

Make sure the Python extension is compiled (via pyo3/maturin if used).

### 5️⃣ Database  
First run will auto-create SQLite tables.

---

## ▶ Running the bot

```bash
python -m backend.main
```

---

##  Project Structure

```
backend/
  ai_module/
    model.py
    pipeline.py
    category.py
    sentiment.py
    cleaner.py
  telegram/
    handlers.py
  db/
    database.py
    models.py
rust_core/
  src/
    lib.rs
README.md
```

---

##  Personalization Engine

Your preferences are stored in `UserPreferences`:

- Favorite categories  
- Preferred language  
- Preferred sentiment  

Bot also tracks your clicks (`UserCategoryStat`)  
→ Recommends relevant articles via `/recommend`.

---

##  Auto-updates

A background scheduler sends news every **2 hours** to all subscribers.

---

##  ML Models Used

- **Summarization:** DistilBART  
- **Translation:** MarianMT + NLLB  
- **Sentiment:** Rule-based + scoring  
- **Text cleaning:** BS4 + regex normalization  

---

##  Error Handling

The pipeline includes:

- Fail-safe summarization  
- Rust fetch fallback  
- Database rollback checks  
- Automatic skip of malformed articles  

---

##  License

MIT License.

---

##  Contribute

Pull requests are welcome!  
The system is modular — you can add new ML models, sources, or commands easily.

---

##  Author

Dmitriy (HaRwonDus)  
AI Developer  
GitHub: https://github.com/HaRwonDus

