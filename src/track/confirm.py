"""Interactive confirmation and fuzzy-match disambiguation."""

from track.errors import CancelledError
from track.picker import Option, pick_one


def choose_candidate(
    candidates: list[dict[str, int | str | float]],
    input_fn=input,
    output_fn=print,
) -> int:
    options = [
        Option(
            value=int(candidate["id"]),
            label=(
                f"ID#{candidate['id']} - {candidate['role_text']} "
                f"(score={candidate['score']:.1f})"
            ),
        )
        for candidate in candidates
    ]
    return int(
        pick_one(
            options,
            title="Multiple applications matched. Pick one (option number, not ID):",
            input_fn=input_fn,
            output_fn=output_fn,
        )
    )


def confirm_status_change(
    application_id: int,
    role_text: str,
    old_status: str,
    new_status: str,
    input_fn=input,
    output_fn=print,
) -> None:
    output_fn(
        f"Update application #{application_id} ({role_text}) "
        f"from '{old_status}' to '{new_status}'?"
    )
    if input_fn("Confirm [y/N]: ").strip().lower() not in {"y", "yes"}:
        raise CancelledError("Update cancelled. No changes were made.")
