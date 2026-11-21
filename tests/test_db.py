from datetime import date

import pytest

from studybuddy import db

TODAY = date(2026, 3, 1)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


def test_deck_names_are_unique_and_not_empty(conn):
    db.add_deck(conn, "Biology")
    with pytest.raises(ValueError):
        db.add_deck(conn, "Biology")
    with pytest.raises(ValueError):
        db.add_deck(conn, "   ")


def test_card_requires_existing_deck_and_text(conn):
    with pytest.raises(ValueError):
        db.add_card(conn, "Nope", "q", "a", TODAY)
    db.add_deck(conn, "D")
    with pytest.raises(ValueError):
        db.add_card(conn, "D", "", "a", TODAY)


def test_new_card_is_due_today(conn):
    db.add_deck(conn, "D")
    db.add_card(conn, "D", "2+2", "4", TODAY)
    assert len(db.due_cards(conn, "D", TODAY)) == 1


def test_review_schedules_and_hides_card_until_due(conn):
    db.add_deck(conn, "D")
    cid = db.add_card(conn, "D", "q", "a", TODAY)
    db.record_review(conn, cid, 4, TODAY)
    assert db.due_cards(conn, "D", TODAY) == []
    assert len(db.due_cards(conn, "D", date(2026, 3, 2))) == 1


def test_failed_review_keeps_card_due_tomorrow(conn):
    db.add_deck(conn, "D")
    cid = db.add_card(conn, "D", "q", "a", TODAY)
    state = db.record_review(conn, cid, 1, TODAY)
    assert state.interval == 1


def test_stats_and_accuracy(conn):
    db.add_deck(conn, "D")
    a = db.add_card(conn, "D", "q1", "a", TODAY)
    b = db.add_card(conn, "D", "q2", "a", TODAY)
    db.record_review(conn, a, 5, TODAY)
    db.record_review(conn, b, 1, TODAY)
    s = db.stats(conn, TODAY)
    assert s["cards"] == 2 and s["reviews"] == 2 and s["accuracy"] == 50


def test_delete_card_and_cascade_with_reviews(conn):
    db.add_deck(conn, "D")
    cid = db.add_card(conn, "D", "q", "a", TODAY)
    db.record_review(conn, cid, 4, TODAY)
    assert db.delete_card(conn, cid) is True
    assert db.delete_card(conn, cid) is False
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0


def test_sql_injection_text_is_stored_literally(conn):
    db.add_deck(conn, "D")
    evil = "x'); DROP TABLE cards;--"
    db.add_card(conn, "D", evil, "a", TODAY)
    assert db.list_cards(conn, "D")[0]["front"] == evil
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 1


def test_list_decks_counts_due(conn):
    db.add_deck(conn, "D")
    cid = db.add_card(conn, "D", "q", "a", TODAY)
    db.add_card(conn, "D", "q2", "a", TODAY)
    db.record_review(conn, cid, 5, TODAY)
    row = db.list_decks(conn, TODAY)[0]
    assert (row["cards"], row["due"]) == (2, 1)
