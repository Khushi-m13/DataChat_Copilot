# 🗄️ DataChat Copilot — Gemini Edition

Chat with CSV, Excel and SQLite data using natural language.

DataChat Copilot uses Gemini to translate a question into a safe, read-only SQLite query, executes it locally, and displays the result as a table, chart and plain-English explanation.

## What changed from the Claude version?

- Removed `langchain-anthropic` and all Claude API code.
- Added Google's `google-genai` SDK.
- Uses `gemini-2.5-flash-lite` by default.
- Supports a Gemini API key from `.env` or the Streamlit sidebar.
- Keeps the existing CSV/Excel/SQLite → SQLite → SQL → Pandas workflow.
- Keeps read-only SQL validation and automatic SQL retry/correction.

## Free usage

The app is designed for Gemini's free tier. Free-tier availability and quotas are controlled by Google and can change. Check Google's Gemini API pricing/quota documentation if a quota error appears.

## Requirements

- Windows 10/11
- Python 3.10+
- A Gemini API key from Google AI Studio
- Internet connection while calling Gemini

## Setup — Windows

### 1. Install Python

Download Python from:
https://www.python.org/downloads/

Enable **Add Python to PATH** during installation.

### 2. Configure Gemini

Copy:

`.env.example` → `.env`

Then put your key in `.env`:

`GEMINI_API_KEY=YOUR_REAL_KEY`

Do not upload `.env` to GitHub.

Alternatively, start the app and paste the key into the sidebar.

### 3. Install dependencies

Double-click:

`install.bat`

### 4. Run

Double-click:

`run.bat`

The browser should open at:

`http://localhost:8501`

## First test

1. Open DataChat Copilot.
2. Confirm **Gemini is configured** in the sidebar.
3. Click **Use demo data**.
4. Ask:
   - `How many orders are there?`
   - `Which product generated the highest revenue?`
   - `Show sales by product category.`
   - `Which city has the most customers?`

## Supported files

- CSV
- XLSX
- XLS
- SQLite `.db`
- SQLite `.sqlite`

## Security

Generated SQL is checked before execution. Only one read-only `SELECT` or `WITH ... SELECT` statement is allowed. Destructive SQL operations such as INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH and PRAGMA are rejected.

Uploaded CSV/Excel data is converted to a local SQLite workspace. Gemini receives the database schema/profile and the user's question to generate SQL. Result text may also be sent to Gemini for a short explanation.

## Project structure

```text
DataChat_Copilot/
├── app.py
├── sql_engine.py
├── gemini_client.py
├── data_loader.py
├── setup_db.py
├── requirements.txt
├── install.bat
├── run.bat
├── .env.example
├── .gitignore
└── README.md
```

## Power BI

Power BI is normally queried with DAX rather than SQL. Export the relevant Power BI tables as CSV/Excel and upload them to DataChat Copilot.
