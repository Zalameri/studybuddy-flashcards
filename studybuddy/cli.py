"""Command-line interface:  python -m studybuddy <command> ..."""
from __future__ import annotations

import argparse
import sys
from datetime import date

from . import db


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studybuddy", description="Flashcards with SM-2 spaced repetition")
    p.add_argument("--db", default="studybuddy.db", help="SQLite file (default: studybuddy.db)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("decks", help="list decks with card and due counts")
    a = sub.add_parser("add-deck", help="create a deck")
    a.add_argument("name")
    a = sub.add_parser("add-card", help="add a card to a deck")
    a.add_argument("deck")
    a.add_argument("front")
    a.add_argument("back")
    a = sub.add_parser("cards", help="list the cards of a deck")
    a.add_argument("deck")
    a = sub.add_parser("delete-card", help="delete a card by id")
    a.add_argument("card_id", type=int)
    a = sub.add_parser("review", help="review the cards that are due today")
    a.add_argument("deck")
    a.add_argument("--limit", type=int, default=20)
    sub.add_parser("stats", help="show overall statistics")
    return p


def run_review(conn, deck: str, limit: int, today: date, ask=input, out=print) -> int:
    cards = db.due_cards(conn, deck, today, limit)
    if not cards:
        out("Nothing due. Come back later!")
        return 0
    out(f"{len(cards)} card(s) to review. Grade 0-5 (0 = forgot, 5 = perfect), 'q' to stop.")
    done = 0
    for card in cards:
        out(f"\nQ: {card['front']}")
        ask("   (press Enter to show the answer) ")
        out(f"A: {card['back']}")
        while True:
            raw = ask("   Your grade (0-5): ").strip().lower()
            if raw == "q":
                out(f"Stopped after {done} card(s).")
                return done
            if raw.isdigit() and 0 <= int(raw) <= 5:
                break
            out("   Please type a number from 0 to 5, or q.")
        state = db.record_review(conn, card["id"], int(raw), today)
        out(f"   Next review in {state.interval} day(s).")
        done += 1
    out(f"\nDone! Reviewed {done} card(s).")
    return done


def main(argv=None, today: date | None = None) -> int:
    args = build_parser().parse_args(argv)
    today = today or date.today()
    conn = db.connect(args.db)
    try:
        if args.command == "add-deck":
            db.add_deck(conn, args.name)
            print(f"Created deck '{args.name}'.")
        elif args.command == "decks":
            rows = db.list_decks(conn, today)
            if not rows:
                print("No decks yet. Create one with: add-deck <name>")
            for r in rows:
                print(f"{r['name']}: {r['cards']} card(s), {r['due']} due")
        elif args.command == "add-card":
            cid = db.add_card(conn, args.deck, args.front, args.back, today)
            print(f"Added card #{cid} to '{args.deck}'.")
        elif args.command == "cards":
            for r in db.list_cards(conn, args.deck):
                print(f"#{r['id']}  {r['front']}  ->  {r['back']}  (due {r['due']})")
        elif args.command == "delete-card":
            print("Deleted." if db.delete_card(conn, args.card_id) else "No such card.")
        elif args.command == "review":
            run_review(conn, args.deck, args.limit, today)
        elif args.command == "stats":
            s = db.stats(conn, today)
            acc = "n/a" if s["accuracy"] is None else f"{s['accuracy']}%"
            print(f"Cards: {s['cards']}  Due today: {s['due_today']}  Reviews: {s['reviews']}  Accuracy: {acc}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0
