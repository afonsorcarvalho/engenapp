import re
from collections import Counter

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

_RE_FULL = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
_RE_MY = re.compile(r"\b(\d{1,2})[/\-.](\d{4})\b")
_RE_NAME = re.compile(
    r"\b(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) +
    r")\.?\s*(?:de\s+|/|-)?\s*(\d{4})\b",
    re.IGNORECASE,
)


def _valid(mes, ano):
    return 1 <= mes <= 12 and 1990 <= ano <= 2100


def extract_period(text):
    """Return (mes, ano) most frequent in text; (0, 0) if none found."""
    if not text:
        return (0, 0)
    pairs = []
    for _d, m, a in _RE_FULL.findall(text):
        m, a = int(m), int(a)
        if _valid(m, a):
            pairs.append((m, a))
    text_wo_full = _RE_FULL.sub(" ", text)
    for m, a in _RE_MY.findall(text_wo_full):
        m, a = int(m), int(a)
        if _valid(m, a):
            pairs.append((m, a))
    for name, a in _RE_NAME.findall(text):
        m = _MONTHS[name.lower()]
        a = int(a)
        if _valid(m, a):
            pairs.append((m, a))
    if not pairs:
        return (0, 0)
    counter = Counter(pairs)
    top = counter.most_common(1)[0][1]
    for pair in pairs:
        if counter[pair] == top:
            return pair
    return pairs[0]
