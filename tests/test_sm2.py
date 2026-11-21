from datetime import date

import pytest

from studybuddy.sm2 import CardState, next_due, review


def test_first_correct_answer_is_one_day():
    s = review(CardState(), 4)
    assert (s.repetitions, s.interval) == (1, 1)


def test_second_correct_answer_is_six_days():
    s = review(review(CardState(), 4), 4)
    assert (s.repetitions, s.interval) == (2, 6)


def test_third_answer_multiplies_by_ease():
    s = CardState()
    for _ in range(3):
        s = review(s, 4)
    assert s.repetitions == 3
    assert s.interval == round(6 * s.ease)  # ease stays 2.5 for grade 4


def test_failing_resets_repetitions_and_schedules_tomorrow():
    s = review(review(CardState(), 5), 5)
    s = review(s, 2)
    assert (s.repetitions, s.interval) == (0, 1)


def test_ease_never_below_minimum():
    s = CardState()
    for _ in range(20):
        s = review(s, 0)
    assert s.ease == pytest.approx(1.3)


def test_perfect_grade_raises_ease_by_point_one():
    assert review(CardState(), 5).ease == pytest.approx(2.6)


def test_grade_four_keeps_ease():
    assert review(CardState(), 4).ease == pytest.approx(2.5)


@pytest.mark.parametrize("bad", [-1, 6, 10])
def test_invalid_grade_rejected(bad):
    with pytest.raises(ValueError):
        review(CardState(), bad)


def test_next_due_adds_interval_days():
    assert next_due(date(2026, 1, 30), CardState(interval=6)) == date(2026, 2, 5)
