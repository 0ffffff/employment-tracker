"""Fuzzy role_text matching for application identifiers using RapidFuzz WRatio."""

import re

from rapidfuzz import fuzz, process

# Minimum WRatio score (0–100) for fuzzy application identifier matches.
FUZZY_MATCH_THRESHOLD = 85
# Token-level ratio cutoff for `track list <query>`.
LIST_MATCH_THRESHOLD = 80


def candidate_matches(
    query: str,
    candidates: list[dict[str, str | int]],
    threshold: int = FUZZY_MATCH_THRESHOLD,
) -> list[dict[str, int | str | float]]:
    if not candidates:
        return []

    stripped = query.strip().lower()
    exact = [
        c
        for c in candidates
        if str(c["role_text"]).strip().casefold() == stripped.casefold()
    ]
    if len(exact) == 1:
        c = exact[0]
        return [{"id": int(c["id"]), "role_text": str(c["role_text"]), "score": 100.0}]

    choices = [str(c["role_text"]) for c in candidates]
    results = process.extract(
        stripped,
        choices,
        scorer=fuzz.WRatio,
        processor=str.lower,
        score_cutoff=threshold,
        limit=None,
    )
    return [
        {
            "id": int(candidates[idx]["id"]),
            "role_text": str(candidates[idx]["role_text"]),
            "score": float(score),
        }
        for _, score, idx in results
    ]


def ranked_role_matches(
    query: str,
    candidates: list[dict],
    threshold: int = LIST_MATCH_THRESHOLD,
) -> list[dict]:
    q_tokens = re.findall(r"[a-z0-9]+", query.lower())
    if not q_tokens:
        return []

    matches: list[dict] = []
    for candidate in candidates:
        r_tokens = re.findall(r"[a-z0-9]+", str(candidate["role_text"]).lower())
        if not r_tokens:
            continue
        scores = [
            max(100 if len(q) >= 3 and t.startswith(q) else fuzz.ratio(q, t) for t in r_tokens)
            for q in q_tokens
        ]
        if min(scores) >= threshold:
            matches.append({**candidate, "score": sum(scores) / len(scores)})
    return matches
