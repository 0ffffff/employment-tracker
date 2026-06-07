"""Fuzzy role_text matching for application identifiers using RapidFuzz WRatio."""

from rapidfuzz import fuzz, process


def candidate_matches(
    query: str, candidates: list[dict[str, str | int]], threshold: int = 85
) -> list[dict[str, int | str | float]]:
    if not candidates:
        return []

    stripped = query.strip()
    exact = [
        c
        for c in candidates
        if str(c["role_text"]).strip().casefold() == stripped.casefold()
    ]
    if len(exact) == 1:
        c = exact[0]
        return [{"id": int(c["id"]), "role_text": str(c["role_text"]), "score": 100.0}]

    lookup = {str(c["role_text"]): c for c in candidates}
    results = process.extract(
        query,
        list(lookup.keys()),
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=None,
    )
    return [
        {
            "id": int(lookup[role_text]["id"]),
            "role_text": role_text,
            "score": float(score),
        }
        for role_text, score, _ in results
    ]
