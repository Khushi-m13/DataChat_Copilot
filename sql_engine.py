"""Core data-chat logic using Gemini instead of Claude."""
import re
import sqlite3

import pandas as pd

from data_loader import WORKSPACE_DB, profile_database
from gemini_client import DEFAULT_MODEL, generate_text

DB_PATH = WORKSPACE_DB
MODEL = DEFAULT_MODEL
MAX_ROWS = 500

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum|reindex|grant|revoke)\b",
    re.IGNORECASE,
)

SQL_SYSTEM_PROMPT = """
You are an expert SQLite data analyst.

Convert the user's natural-language question into ONE safe, read-only SQLite query.
Use ONLY the tables and columns provided below.

SCHEMA:
{schema}

DATA PROFILE:
{profile}

RULES:
- Return ONLY SQL. No explanation and no markdown fences.
- Use exactly one SQL statement.
- Only SELECT or WITH ... SELECT is allowed.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, TRUNCATE,
  ATTACH, DETACH, PRAGMA, VACUUM, REINDEX, GRANT or REVOKE.
- Use SQLite syntax.
- Use real table and column names from the schema.
- Use readable column aliases.
- Round money, percentages and ratios to 2 decimals.
- Dates are normally stored as ISO text. Use SQLite date/strftime functions when needed.
- Use the data profile to match real values and date formats.
- For follow-up questions, use the previous conversation supplied by the user.
- If the question cannot be answered from this database, return exactly CANNOT_ANSWER.
"""


def get_schema(db_path: str = DB_PATH) -> str:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return "\n\n".join(r[0] for r in rows)
    finally:
        conn.close()


def clean_sql(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip().rstrip(";").strip()


def validate_sql(sql: str) -> None:
    """Raise ValueError if the query is not a single, read-only SELECT."""
    if sql.strip().upper() == "CANNOT_ANSWER":
        raise ValueError(
            "I can't answer that from the loaded data. Try rephrasing the question "
            "or check the available columns."
        )
    if ";" in sql:
        raise ValueError("Only a single SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a forbidden SQL operation.")


def run_query(sql: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Execute SQL on a read-only SQLite connection and cap returned rows."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return pd.read_sql_query(f"SELECT * FROM ({sql}) LIMIT {MAX_ROWS}", conn)
    finally:
        conn.close()


def _format_history(history) -> str:
    if not history:
        return ""
    lines = [f"Q: {h['question']}\nSQL: {h['sql']}" for h in history[-3:]]
    return "Previous questions in this conversation:\n" + "\n\n".join(lines) + "\n\n"


def generate_sql(question: str, history=None, feedback: str = "", db_path: str = DB_PATH) -> str:
    system = SQL_SYSTEM_PROMPT.format(
        schema=get_schema(db_path),
        profile=profile_database(db_path),
    )
    prompt = (
        _format_history(history)
        + f"Question: {question}\n"
        + feedback
        + "\nReturn only the SQL query."
    )
    return clean_sql(
        generate_text(
            prompt,
            system_instruction=system,
            model=MODEL,
            temperature=0,
            max_output_tokens=800,
        )
    )


def summarize(question: str, sql: str, df: pd.DataFrame) -> str:
    """Create a short business-friendly explanation of the query result."""
    if df.empty:
        return "The query ran successfully but returned no rows."

    result = df.head(25).to_csv(index=False)
    prompt = (
        "Answer the user's question in 1-3 short sentences for a business user. "
        "Use ONLY the result below. Mention the most important numbers. "
        "Do not discuss SQL. If the displayed rows are only a subset, say so.\n\n"
        f"Question: {question}\n"
        f"Result ({len(df)} rows returned; first 25 shown):\n{result}"
    )
    try:
        return generate_text(prompt, model=MODEL, temperature=0.1, max_output_tokens=250)
    except Exception:
        # The SQL result is still useful if a second Gemini call is unavailable.
        return ""


def suggest_questions(db_path: str = DB_PATH) -> list:
    """Suggest useful questions from the database profile."""
    prompt = (
        "You are a data analyst. Based on the database profile below, suggest 6 useful questions "
        "a business user can ask. Include trends, top/bottom performers, comparisons, totals/averages, "
        "anomalies or data-quality questions where appropriate. Every question must be answerable "
        "from the database. Output exactly one question per line, without numbering or bullets.\n\n"
        f"DATABASE PROFILE:\n{profile_database(db_path)}"
    )
    text = generate_text(prompt, model=MODEL, temperature=0.2, max_output_tokens=400)
    return [re.sub(r"^[-*\d.)\s]+", "", line).strip() for line in text.splitlines() if line.strip()][:6]


def answer_question(question: str, history=None, max_retries: int = 2, db_path: str = DB_PATH) -> dict:
    """Generate SQL, safely execute it, retry SQL errors, then summarize the result."""
    feedback, last_error = "", None

    for _ in range(max_retries + 1):
        sql = generate_sql(question, history, feedback, db_path)
        try:
            validate_sql(sql)
            df = run_query(sql, db_path)
        except ValueError:
            raise
        except Exception as exc:
            last_error = str(exc)
            feedback = (
                "\n\nYour previous query failed.\n"
                f"Query: {sql}\n"
                f"SQLite error: {last_error}\n"
                "Fix the query and return ONLY the corrected SQL."
            )
            continue

        return {"sql": sql, "df": df, "summary": summarize(question, sql, df)}

    raise RuntimeError(f"Could not produce a working query. Last error: {last_error}")
