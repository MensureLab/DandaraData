"""Dictionary-driven mention detection: no NER, no machine learning.

Offsets reference the ORIGINAL article field (preserving evidence), not normalized text.
"""
from __future__ import annotations
from collections import defaultdict
import re
import pandas as pd
from .models import Candidate, Mention
from .normalization import normalize_with_offsets
from .ingestion import ARTICLE_FIELDS


def detect_mentions(articles: pd.DataFrame, alias_index: dict[str, list[Candidate]],
                    minimum_name_length: int = 3) -> list[Mention]:
    by_length = defaultdict(dict)
    for alias, candidates in alias_index.items():
        if len(alias) < minimum_name_length:
            continue
        by_length[len(alias.split())][alias] = candidates
    phrase_lengths = sorted(by_length)
    mentions: list[Mention] = []
    for row_idx, article in articles.iterrows():
        ut = str(article['UT'])
        # The original program's row-based article ID: zero-index + 2
        article_id = int(row_idx) + 2
        for field in ARTICLE_FIELDS:
            original = str(article.get(field, ''))
            if not original.strip():
                continue
            norm, offsets = normalize_with_offsets(original)
            tokens = list(re.finditer(r'\b\w+\b', norm))
            n = len(tokens)
            for start_i in range(n):
                for size in phrase_lengths:
                    if start_i + size > n:
                        break
                    phrase = norm[tokens[start_i].start():tokens[start_i+size-1].end()]
                    related = by_length[size].get(phrase)
                    if not related:
                        continue
                    norm_start, norm_end = tokens[start_i].start(), tokens[start_i+size-1].end()
                    orig_start, orig_end = offsets[norm_start], offsets[norm_end-1] + 1
                    context = original[max(0, orig_start-90):min(len(original), orig_end+90)]
                    for candidate in related:
                        mentions.append(Mention(
                            ut=ut, article_id=article_id, field=field,
                            candidate_id=candidate.candidate_id, name=candidate.name,
                            matched_text=original[orig_start:orig_end],
                            start=orig_start, end=orig_end, context=context,
                        ))
    return mentions
