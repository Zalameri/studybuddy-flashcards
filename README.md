# StudyBuddy Flashcards

A small command-line flashcard app that schedules reviews with the **SM-2 spaced-repetition algorithm**
(the one behind SuperMemo and Anki's classic scheduler). Cards you know well come back after longer
and longer gaps; cards you forget come back tomorrow.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-built--in-003B57?style=flat-square&logo=sqlite&logoColor=white)

## Features
- Decks and cards stored in a local SQLite file (`studybuddy.db`)
- `review` shows today's due cards, asks for a grade 0-5 and reschedules with SM-2
- Per-deck counts of cards and cards due today, plus overall accuracy
- Parameterised SQL only; the standard library only (pytest is needed just for the tests)

## Usage
```bash
git clone https://github.com/Zalameri/studybuddy-flashcards.git
cd studybuddy-flashcards

python -m studybuddy add-deck Biology
python -m studybuddy add-card Biology "Powerhouse of the cell?" "Mitochondria"
python -m studybuddy decks
python -m studybuddy review Biology
python -m studybuddy stats
```
Other commands: `cards <deck>`, `delete-card <id>`. Use `--db other.db` to pick a different database file.

## How SM-2 works here
Grade each answer from 0 (forgot) to 5 (perfect):
- grade below 3: repetitions restart and the card returns the next day
- otherwise the interval is 1 day, then 6 days, then `previous interval x ease`
- the ease factor moves with your grade and never drops below 1.3

The algorithm is the pure function `studybuddy/sm2.py::review`, so it is easy to test and read.

## Tests
```bash
pip install -r requirements-dev.txt
python -m pytest
```
25 tests cover the scheduler, the database layer (including SQL-injection text) and the CLI review loop.
They also run on every push through GitHub Actions.

## Project layout
```text
studybuddy/
  sm2.py    # SM-2 algorithm (pure function)
  db.py     # SQLite storage
  cli.py    # command-line interface
tests/      # pytest tests
```

## Ideas for later
- Import/export decks as CSV
- A small web page on top of the same database layer
