"""Unicode-aware canonicalization that preserves offsets into original text."""
from __future__ import annotations
import re
import unicodedata


def normalize_with_offsets(value: object) -> tuple[str, list[int]]:
    raw = '' if value is None else str(value)
    chars: list[str] = []
    offsets: list[int] = []
    in_space = True
    for pos, ch in enumerate(raw):
        decomposed = unicodedata.normalize('NFKD', ch)
        for decomposed_ch in decomposed:
            if unicodedata.combining(decomposed_ch):
                continue
            folded = decomposed_ch.lower()
            for letter in folded:
                if letter.isalnum():
                    chars.append(letter)
                    offsets.append(pos)
                    in_space = False
                elif not in_space:
                    chars.append(' ')
                    offsets.append(pos)
                    in_space = True
    if chars and chars[-1] == ' ':
        chars.pop(); offsets.pop()
    return ''.join(chars), offsets


def normalize(value: object) -> str:
    return normalize_with_offsets(value)[0]


def contains_phrase(normalized_text: str, phrase: str) -> bool:
    phrase = normalize(phrase)
    return bool(phrase and re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', normalized_text))


def words(value: object) -> list[str]:
    return normalize(value).split()
