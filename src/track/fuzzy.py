from rapidfuzz import fuzz, process


def candidate_matches(
    query: str, candidates: list[dict[str, str | int]], threshold: int = 85
) -> list[dict[str, int | str | float]]:
    if not candidates:
        return []

    lookup = {str(candidate["role_text"]): candidate for candidate in candidates}
    results = process.extract(
        query,
        list(lookup.keys()),
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=None,
    )
    matches = []
    for role_text, score, _ in results:
        candidate = lookup[role_text]
        matches.append(
            {"id": int(candidate["id"]), "role_text": role_text, "score": float(score)}
        )
    return matches
