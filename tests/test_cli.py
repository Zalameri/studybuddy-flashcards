from datetime import date

from studybuddy import cli, db

TODAY = date(2026, 3, 1)


def run(tmp_path, *args):
    return cli.main(["--db", str(tmp_path / "c.db"), *args], today=TODAY)


def test_full_flow(tmp_path, capsys):
    assert run(tmp_path, "add-deck", "Math") == 0
    assert run(tmp_path, "add-card", "Math", "2+2", "4") == 0
    assert run(tmp_path, "decks") == 0
    assert "Math: 1 card(s), 1 due" in capsys.readouterr().out
    assert run(tmp_path, "stats") == 0
    assert "Cards: 1" in capsys.readouterr().out


def test_errors_return_exit_code_1(tmp_path, capsys):
    assert run(tmp_path, "add-card", "Missing", "q", "a") == 1
    assert "does not exist" in capsys.readouterr().err


def test_review_session_grades_and_reschedules(tmp_path):
    conn = db.connect(tmp_path / "r.db")
    db.add_deck(conn, "D")
    db.add_card(conn, "D", "q", "a", TODAY)
    answers = iter(["", "x", "9", "5"])  # show answer, two invalid grades, then 5
    out = []
    done = cli.run_review(conn, "D", 10, TODAY, ask=lambda _: next(answers), out=out.append)
    assert done == 1
    assert db.due_cards(conn, "D", TODAY) == []
    assert any("Please type a number" in line for line in out)


def test_review_can_quit(tmp_path):
    conn = db.connect(tmp_path / "q.db")
    db.add_deck(conn, "D")
    db.add_card(conn, "D", "q", "a", TODAY)
    answers = iter(["", "q"])
    done = cli.run_review(conn, "D", 10, TODAY, ask=lambda _: next(answers), out=lambda _: None)
    assert done == 0
    assert len(db.due_cards(conn, "D", TODAY)) == 1


def test_review_with_nothing_due(tmp_path):
    conn = db.connect(tmp_path / "n.db")
    db.add_deck(conn, "D")
    out = []
    assert cli.run_review(conn, "D", 10, TODAY, ask=lambda _: "", out=out.append) == 0
    assert "Nothing due" in out[0]
