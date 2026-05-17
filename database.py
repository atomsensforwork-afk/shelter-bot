import sqlite3
import json
from pathlib import Path

DB_PATH = Path("shelter.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS games (
            chat_id     INTEGER PRIMARY KEY,
            host_id     INTEGER NOT NULL,
            state       TEXT NOT NULL DEFAULT 'lobby',
            scenario    TEXT,
            round       INTEGER NOT NULL DEFAULT 1,
            survivors   INTEGER NOT NULL DEFAULT 0,
            revote      INTEGER NOT NULL DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            username    TEXT NOT NULL,
            cards       TEXT,
            revealed    TEXT NOT NULL DEFAULT '[]',
            eliminated  INTEGER NOT NULL DEFAULT 0,
            UNIQUE(chat_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS votes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER NOT NULL,
            round       INTEGER NOT NULL,
            revote      INTEGER NOT NULL DEFAULT 0,
            voter_id    INTEGER NOT NULL,
            target_id   INTEGER NOT NULL,
            UNIQUE(chat_id, round, revote, voter_id)
        );
        """)


# ─── Games ────────────────────────────────

def create_game(chat_id: int, host_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO games (chat_id, host_id, state) VALUES (?, ?, 'lobby')",
            (chat_id, host_id)
        )


def get_game(chat_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM games WHERE chat_id = ?", (chat_id,)).fetchone()
        if row:
            d = dict(row)
            if d["scenario"]:
                d["scenario"] = json.loads(d["scenario"])
            return d
    return None


def update_game(chat_id: int, **kwargs):
    if not kwargs:
        return
    if "scenario" in kwargs and isinstance(kwargs["scenario"], dict):
        kwargs["scenario"] = json.dumps(kwargs["scenario"], ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [chat_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE games SET {sets} WHERE chat_id = ?", vals)


def delete_game(chat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM votes WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM players WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM games WHERE chat_id = ?", (chat_id,))


# ─── Players ──────────────────────────────

def add_player(chat_id: int, user_id: int, username: str) -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO players (chat_id, user_id, username) VALUES (?, ?, ?)",
                (chat_id, user_id, username)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_players(chat_id: int, active_only: bool = False) -> list:
    q = "SELECT * FROM players WHERE chat_id = ?"
    if active_only:
        q += " AND eliminated = 0"
    with get_conn() as conn:
        rows = conn.execute(q, (chat_id,)).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["cards"] = json.loads(d["cards"]) if d["cards"] else {}
        d["revealed"] = json.loads(d["revealed"])
        result.append(d)
    return result


def get_player(chat_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
    if row:
        d = dict(row)
        d["cards"] = json.loads(d["cards"]) if d["cards"] else {}
        d["revealed"] = json.loads(d["revealed"])
        return d
    return None


def get_player_game(user_id: int):
    """Находит активную игру игрока."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT chat_id FROM players WHERE user_id = ? AND eliminated = 0",
            (user_id,)
        ).fetchone()
    return row["chat_id"] if row else None


def set_player_cards(chat_id: int, user_id: int, cards: dict):
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET cards = ? WHERE chat_id = ? AND user_id = ?",
            (json.dumps(cards, ensure_ascii=False), chat_id, user_id)
        )


def reveal_card(chat_id: int, user_id: int, card_key: str):
    player = get_player(chat_id, user_id)
    if not player:
        return
    revealed = player["revealed"]
    if card_key not in revealed:
        revealed.append(card_key)
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET revealed = ? WHERE chat_id = ? AND user_id = ?",
            (json.dumps(revealed), chat_id, user_id)
        )


def eliminate_player(chat_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET eliminated = 1 WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )


# ─── Votes ────────────────────────────────

def cast_vote(chat_id: int, round_n: int, revote: int, voter_id: int, target_id: int) -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO votes (chat_id, round, revote, voter_id, target_id)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(chat_id, round, revote, voter_id)
                   DO UPDATE SET target_id = excluded.target_id""",
                (chat_id, round_n, revote, voter_id, target_id)
            )
        return True
    except Exception:
        return False


def get_votes(chat_id: int, round_n: int, revote: int = 0) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM votes WHERE chat_id = ? AND round = ? AND revote = ?",
            (chat_id, round_n, revote)
        ).fetchall()
    return [dict(r) for r in rows]


def count_votes(chat_id: int, round_n: int, revote: int = 0) -> dict:
    votes = get_votes(chat_id, round_n, revote)
    counts = {}
    for v in votes:
        counts[v["target_id"]] = counts.get(v["target_id"], 0) + 1
    return counts
