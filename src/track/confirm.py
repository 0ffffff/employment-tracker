"""Interactive confirmation and fuzzy-match disambiguation."""

from track.errors import CancelledError, ValidationError


def choose_candidate(
    candidates: list[dict[str, int | str | float]],
    input_fn=input,
    output_fn=print,
) -> int:
    output_fn("Multiple applications matched. Pick one (option number, not ID):")
    for index, candidate in enumerate(candidates, start=1):
        output_fn(
            f"{index}) ID#{candidate['id']} - {candidate['role_text']} "
            f"(score={candidate['score']:.1f})"
        )
    response = input_fn("Enter selection number: ").strip()
    if not response.isdigit():
        raise ValidationError("Selection must be a number.")
    selected_index = int(response)
    if selected_index < 1 or selected_index > len(candidates):
        raise ValidationError("Selection is out of range.")
    return int(candidates[selected_index - 1]["id"])


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
