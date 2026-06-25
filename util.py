import re

import arabic_reshaper


def calculate_indices(text: str, page_count: int) -> list[int] | None:
    gps = text.split(",")
    results = set()
    try:
        for g in gps:
            if "-" in g:
                parts = g.split("-")
                if len(parts) == 2:
                    start, end = int(parts[0]) - 1, int(parts[1]) - 1
                    start = max(0, min(start, page_count))
                    end = max(0, min(end, page_count))
                    for i in range(start, end + 1):
                        results.add(i)
            else:
                g_int = max(0, min(int(g) - 1, page_count))
                results.add(g_int)
        return list(results) if len(results) > 0 else None
    except ValueError:
        pass


def needs_arabic_fix(text: str) -> bool:
    if len(text) < 1:
        return False
    return any("\u0600" <= c <= "\u06ff" for c in text)


def normalize_numbers(text: str) -> str:
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return text.translate(table)


def fix_rtl(text: str, collapse_white_space: bool = False) -> str:
    if len(text) < 1:
        return text

    text = normalize_numbers(text)
    if collapse_white_space:
        text = " ".join(text.split())
    tokens = re.split(r"(\d+\.?\d*)", text)
    fixed = []
    for token in tokens:
        token = token.strip()
        if re.match(r"\d+\.?\d*", token):
            fixed.append(token[::-1])
        elif needs_arabic_fix(token):
            reshaped = arabic_reshaper.reshape(token)
            fixed.append(reshaped)
        else:
            fixed.append(token)

    return " ".join([t for t in fixed if t.strip()])
