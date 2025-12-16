import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path("data/app.sqlite")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER,
            provider TEXT,
            model TEXT,
            prompt_style TEXT,
            planning_mode TEXT,
            plan_ms INTEGER,
            summarize_ms INTEGER,
            verify_ms INTEGER,
            answer_len INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            session_id INTEGER,
            tool TEXT,
            duration_ms INTEGER,
            args TEXT,
            stats_json TEXT
        )
    """)
    conn.commit()
    try:
        cols = {r[1] for r in cur.execute("PRAGMA table_info(sessions)")}
        for col in ["summ_cache_hit", "verify_cache_hit", "plan_cache_hit"]:
            if col not in cols:
                cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompt_cache (
            key TEXT PRIMARY KEY,
            ts INTEGER,
            provider TEXT,
            model TEXT,
            style TEXT,
            prompt TEXT,
            response TEXT,
            duration_ms INTEGER
        )
    """)
    conn.commit()
    conn.close()

def record_session(meta: dict, plan: list, results: list, answer_text: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = int(time.time())
    provider = meta.get("provider")
    model = meta.get("model")
    if isinstance(model, dict):
        model = model.get("model")
    prompt_style = meta.get("prompt_style")
    planning_mode = meta.get("planning_mode")
    plan_ms = (meta.get("llm") or {}).get("plan_ms", 0)
    summarize_ms = (meta.get("llm") or {}).get("summarize_ms", 0)
    verify_ms = meta.get("verify_ms", 0)
    answer_len = len(answer_text or "")
    cur.execute("""
        INSERT INTO sessions (ts, provider, model, prompt_style, planning_mode, plan_ms, summarize_ms, verify_ms, answer_len, summ_cache_hit, verify_cache_hit, plan_cache_hit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, provider, model, prompt_style, planning_mode, plan_ms, summarize_ms, verify_ms, answer_len, int(bool(meta.get("summ_cache_hit"))), int(bool(meta.get("verify_cache_hit"))), int(bool(meta.get("plan_cache_hit")))))
    session_id = cur.lastrowid
    for c in meta.get("tool_calls") or []:
        args_text = json.dumps(c.get("args"), ensure_ascii=False)
        stats_text = json.dumps({k: c.get(k) for k in ["stats", "fixed", "packages_count", "releases_count"]}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO tool_calls (session_id, tool, duration_ms, args, stats_json)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, c.get("tool"), c.get("duration_ms", 0), args_text, stats_text))
    conn.commit()
    conn.close()

def fetch_recent_sessions(limit: int = 50) -> list:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, ts, provider, model, prompt_style, planning_mode, plan_ms, summarize_ms, verify_ms, answer_len, summ_cache_hit, verify_cache_hit, plan_cache_hit FROM sessions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    cols = ["id", "ts", "provider", "model", "prompt_style", "planning_mode", "plan_ms", "summarize_ms", "verify_ms", "answer_len", "summ_cache_hit", "verify_cache_hit", "plan_cache_hit"]
    return [dict(zip(cols, r)) for r in rows]

def fetch_tool_calls(session_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tool, duration_ms, args, stats_json FROM tool_calls WHERE session_id=?", (session_id,))
    rows = cur.fetchall()
    conn.close()
    cols = ["tool", "duration_ms", "args", "stats_json"]
    return [dict(zip(cols, r)) for r in rows]

def cache_get_response(key: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT response, duration_ms, ts, provider, model, style FROM prompt_cache WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"response": row[0], "duration_ms": row[1], "ts": row[2], "provider": row[3], "model": row[4], "style": row[5]}

def cache_set_response(key: str, provider: str, model: str, style: str, prompt: str, response: str, duration_ms: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = int(time.time())
    cur.execute("REPLACE INTO prompt_cache (key, ts, provider, model, style, prompt, response, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (key, ts, provider, model, style, prompt, response, duration_ms))
    conn.commit()
    conn.close()
