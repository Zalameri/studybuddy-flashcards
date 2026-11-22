"""Tests for the order of due cards and the --limit cap in a review session."""
from datetime import date, timedelta

import pytest

from studybuddy import cli, db

TODAY = date(2026, 3, 1)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "o.db")
    db.add_deck(c, "D")
    yield c
    c.close()


def add_card_due(conn, front, due):
    """Add a card, then set its due date (temporary test database only)."""
    card_id = db.add_card(conn, "D", front, "answer", TODAY)
    conn.execute("UPDATE cards SET due = ? WHERE id = ?", (due.isoformat(), card_id))
    conn.commit()
    return card_id


def test_most_overdue_cards_come_first(conn):
    add_card_due(conn, "yesterday", TODAY - timedelta(days=1))
    add_card_due(conn, "last week", TODAY - timedelta(days=7))
    add_card_due(conn, "today", TODAY)
    fronts = [c["front"] for c in db.due_cards(conn, "D", TODAY)]
    assert fronts == ["last week", "yesterday", "today"]


def test_same_due_date_is_ordered_by_card_id(conn):
    first = add_card_due(conn, "a", TODAY)
    second = add_card_due(conn, "b", TODAY)
    third = add_card_due(conn, "c", TODAY)
    assert [c["id"] for c in db.due_cards(conn, "D", TODAY)] == [first, second, third]


def test_cards_due_in_the_future_are_not_returned(conn):
    add_card_due(conn, "later", TODAY + timedelta(days=1))
    add_card_due(conn, "now", TODAY)
    assert [c["front"] for c in db.due_cards(conn, "D", TODAY)] == ["now"]


def test_limit_caps_the_number_of_cards(conn):
    for i in range(5):
        add_card_due(conn, f"card {i}", TODAY)
    assert len(db.due_cards(conn, "D", TODAY, limit=3)) == 3
    assert len(db.due_cards(conn, "D", TODAY, limit=10)) == 5


def test_limit_keeps_the_most_overdue_cards(conn):
    add_card_due(conn, "today", TODAY)
    add_card_due(conn, "oldest", TODAY - timedelta(days=10))
    add_card_due(conn, "older", TODAY - timedelta(days=5))
    fronts = [c["front"] for c in db.due_cards(conn, "D", TODAY, limit=2)]
    assert fronts == ["oldest", "older"]


def test_review_session_respects_limit(conn):
    for i in range(4):
        add_card_due(conn, f"card {i}", TODAY)
    out = []
    done = cli.run_review(conn, "D", 2, TODAY, ask=lambda _: "5", out=out.append)
    assert done == 2
    assert "2 card(s) to review" in out[0]
    # the two cards that were not reviewed are still due
    assert len(db.due_cards(conn, "D", TODAY)) == 2


def test_review_session_shows_overdue_card_first(conn):
    add_card_due(conn, "today", TODAY)
    add_card_due(conn, "overdue", TODAY - timedelta(days=3))
    out = []
    cli.run_review(conn, "D", 10, TODAY, ask=lambda _: "q", out=out.append)
    questions = [line.strip() for line in out if line.strip().startswith("Q:")]
    assert questions == ["Q: overdue"]


def test_review_limit_option_is_parsed():
    args = cli.build_parser().parse_args(["review", "D", "--limit", "3"])
    assert args.limit == 3
    assert cli.build_parser().parse_args(["review", "D"]).limit == 20
