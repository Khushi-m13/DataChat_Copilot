"""Loads user files (CSV / Excel / SQLite) into one SQLite workspace and profiles the data."""
import os
import re
import sqlite3

import pandas as pd

WORKSPACE_DB = "workspace.db"


def _clean(name: str) -> str:
    n = re.sub(r"[^0-9a-zA-Z_]+", "_", str(name).strip()).strip("_").lower() or "col"
    return "_" + n if n[0].isdigit() else n


def _clean_columns(cols) -> list:
    seen, out = {}, []
    for c in cols:
        base = _clean(c)
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return out


def load_to_sqlite(files, db_path: str = WORKSPACE_DB) -> list:
    """files: list of (filename, file-like object). Returns the list of table names created."""
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    tables = []
    try:
        for filename, f in files:
            base, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext == ".csv":
                frames = {base: pd.read_csv(f)}
            elif ext in (".xlsx", ".xls"):
                sheets = pd.read_excel(f, sheet_name=None)
                frames = {(f"{base}_{s}" if len(sheets) > 1 else base): df for s, df in sheets.items()}
            else:
                raise ValueError(f"Unsupported file type: {filename}")
            for tname, df in frames.items():
                df = df.copy()
                df.columns = _clean_columns(df.columns)
                for c in df.columns:  # store dates as ISO text so SQLite date functions work
                    if pd.api.types.is_datetime64_any_dtype(df[c]):
                        df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M:%S")
                name = _clean(tname)
                df.to_sql(name, conn, index=False, if_exists="replace")
                tables.append(name)
        conn.commit()
    finally:
        conn.close()
    return tables


def profile_database(db_path: str = WORKSPACE_DB, max_cats: int = 8) -> str:
    """Automatic data exploration: row counts, nulls, distinct counts, ranges, common values."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    lines = []
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for t in tables:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            lines.append(f"TABLE {t} ({n} rows)")
            for _, col, ctype, *_ in conn.execute(f'PRAGMA table_info("{t}")').fetchall():
                nulls, distinct, mn, mx = conn.execute(
                    f'SELECT SUM("{col}" IS NULL), COUNT(DISTINCT "{col}"), MIN("{col}"), MAX("{col}") FROM "{t}"'
                ).fetchone()
                desc = f"  - {col} ({ctype or 'ANY'}): {distinct} distinct, {nulls or 0} null"
                if (ctype or "").upper() in ("INTEGER", "REAL", "FLOAT", "NUMERIC", "BIGINT", "DOUBLE"):
                    desc += f", range {mn} to {mx}"
                elif distinct and distinct <= max_cats:
                    vals = [
                        str(v[0])
                        for v in conn.execute(
                            f'SELECT "{col}" FROM "{t}" WHERE "{col}" IS NOT NULL GROUP BY "{col}" '
                            f"ORDER BY COUNT(*) DESC LIMIT {max_cats}"
                        )
                    ]
                    desc += f", values: {', '.join(vals)}"
                elif mn is not None:
                    desc += f", from '{str(mn)[:30]}' to '{str(mx)[:30]}'"
                lines.append(desc)
            lines.append("")
    finally:
        conn.close()
    return "\n".join(lines).strip()
