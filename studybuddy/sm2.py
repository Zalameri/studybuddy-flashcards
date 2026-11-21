"""The SM-2 spaced-repetition algorithm (SuperMemo 2), as a pure function.

After each review the learner gives a quality grade from 0 (total blackout) to 5 (perfect).
- grade < 3: the card is "forgotten": repetitions restart and it is shown again tomorrow.
- grade >= 3: repetitions grow; the interval is 1 day, then 6 days, then interval * ease.
The ease factor never drops below 1.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

MIN_EASE = 1.3
DEFAULT_EASE = 2.5


@dataclass(frozen=True)
class CardState:
    repetitions: int = 0
    interval: int = 0      # days until the next review
    ease: float = DEFAULT_EASE


def review(state: CardState, grade: int) -> CardState:
    """Return the new state after answering with `grade` (0-5)."""
    if not 0 <= grade <= 5:
        raise ValueError("grade must be between 0 and 5")

    ease = state.ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    ease = max(MIN_EASE, ease)

    if grade < 3:
        return CardState(repetitions=0, interval=1, ease=ease)

    repetitions = state.repetitions + 1
    if repetitions == 1:
        interval = 1
    elif repetitions == 2:
        interval = 6
    else:
        interval = round(state.interval * ease)
    return CardState(repetitions=repetitions, interval=interval, ease=ease)


def next_due(today: date, state: CardState) -> date:
    return today + timedelta(days=state.interval)
