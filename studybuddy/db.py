"""SQLite storage. Every query is parameterised (no string-built SQL)."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .sm2 import CardState, next_due, review

SCHEMA = """
CREATE TABLE IF NOT EXISTS decks (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id     INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    front       TEXT NOT NULL,
    back        TEXT NOT NULL,
    repetitions INTEGER NOT NULL DEFAULT 0,
    interval    INTEGER NOT NULL DEFAULT 0,
    ease        REAL NOT NULL DEFAULT 2.5,
    due         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id   INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed  TEXT NOT NULL,
    grade     INTEGER NOT NULL
);
"""


def connect(path: str | Path = "studybuddy.db") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def add_deck(conn, name: str) -> int:
    name = name.strip()
    if not name:
        raise ValueError("deck name cannot be empty")
    try:
        cur = conn.execute("INSERT INTO decks (name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        raise ValueError(f"deck '{name}' already exists") from None
    conn.commit()
    return cur.lastrowid


def _deck_id(conn, name: str) -> int:
    row = conn.execute("SELECT id FROM decks WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise ValueError(f"deck '{name}' does not exist")
    return row["id"]


def list_decks(conn, today: date):
    return conn.execute(
        """SELECT d.name,
                  COUNT(c.id) AS cards,
                  COALESCE(SUM(c.due <= ?), 0) AS due
           FROM decks d LEFT JOIN cards c ON c.deck_id = d.id
           GROUP BY d.id ORDER BY d.name""",
        (today.isoformat(),),
    ).fetchall()


def add_card(conn, deck: str, front: str, back: str, today: date) -> int:
    if not front.strip() or not back.strip():
        raise ValueError("front and back cannot be empty")
    cur = conn.execute(
        "INSERT INTO cards (deck_id, front, back, due) VALUES (?, ?, ?, ?)",
        (_deck_id(conn, deck), front.strip(), back.strip(), today.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def list_cards(conn, deck: str):
    return conn.execute(
        "SELECT id, front, back, due FROM cards WHERE deck_id = ? ORDER BY id",
        (_deck_id(conn, deck),),
    ).fetchall()


def delete_card(conn, card_id: int) -> bool:
    cur = conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    return cur.rowcount == 1


def due_cards(conn, deck: str, today: date, limit: int = 20):
    return conn.execute(
        """SELECT * FROM cards WHERE deck_id = ? AND due <= ?
           ORDER BY due, id LIMIT ?""",
        (_deck_id(conn, deck), today.isoformat(), limit),
    ).fetchall()


def record_review(conn, card_id: int, grade: int, today: date) -> CardState:
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        raise ValueError(f"card {card_id} does not exist")
    state = review(CardState(row["repetitions"], row["interval"], row["ease"]), grade)
    conn.execute(
        "UPDATE cards SET repetitions = ?, interval = ?, ease = ?, due = ? WHERE id = ?",
        (state.repetitions, state.interval, state.ease, next_due(today, state).isoformat(), card_id),
    )
    conn.execute(
        "INSERT INTO reviews (card_id, reviewed, grade) VALUES (?, ?, ?)",
        (card_id, today.isoformat(), grade),
    )
    conn.commit()
    return state


def stats(conn, today: date) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    due = conn.execute("SELECT COUNT(*) FROM cards WHERE due <= ?", (today.isoformat(),)).fetchone()[0]
    reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM reviews WHERE grade >= 3").fetchone()[0]
    return {
        "cards": total,
        "due_today": due,
        "reviews": reviews,
        "accuracy": round(100 * correct / reviews) if reviews else None,
    }
