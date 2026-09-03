"""Fuzzy role_text matching for application identifiers using RapidFuzz WRatio."""

from rapidfuzz import fuzz, process

# Minimum WRatio score (0–100) for fuzzy application identifier matches.
FUZZY_MATCH_THRESHOLD = 85
# Looser cutoff for `track list <query>` ranked search (not resolve-to-one).
LIST_MATCH_THRESHOLD = 60


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
    """Score every candidate; return those at or above threshold, unsorted."""
    stripped = query.strip().lower()
    if not stripped or not candidates:
        return []

    matches: list[dict] = []
    for candidate in candidates:
        score = float(fuzz.WRatio(stripped, str(candidate["role_text"]).lower()))
        if score >= threshold:
            matches.append({**candidate, "score": score})
    return matches
