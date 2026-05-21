from app.date_extract import extract_period


def test_numeric_full_date():
    assert extract_period("emitida em 12/03/2025 na sede") == (3, 2025)


def test_month_year_slash():
    assert extract_period("competência 03/2025") == (3, 2025)


def test_month_name():
    assert extract_period("referente a março de 2025") == (3, 2025)


def test_month_abbrev():
    assert extract_period("período mar/2025 fechado") == (3, 2025)


def test_most_frequent_pair_wins():
    text = "01/2024 vence 05/03/2025 e tambem 05/03/2025"
    assert extract_period(text) == (3, 2025)


def test_tie_returns_first():
    assert extract_period("janeiro de 2024 e fevereiro de 2025") == (1, 2024)


def test_no_date_returns_zero():
    assert extract_period("documento sem qualquer data") == (0, 0)


def test_empty_text():
    assert extract_period("") == (0, 0)
    assert extract_period(None) == (0, 0)


def test_invalid_month_ignored():
    assert extract_period("codigo 99/2025 sozinho") == (0, 0)
