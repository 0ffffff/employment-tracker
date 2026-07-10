"""Generic interactive picker for selecting one option from a list."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from track.errors import CancelledError, ValidationError

T = TypeVar("T")


@dataclass(frozen=True)
class Option(Generic[T]):
    value: T
    label: str


def pick_one(
    options: list[Option[T]],
    *,
    title: str = "Pick one option (option number):",
    prompt: str = "Enter selection number: ",
    allow_cancel: bool = True,
    input_fn=input,
    output_fn=print,
) -> T:
    if not options:
        raise ValidationError("No options available for selection.")

    output_fn(title)
    for index, option in enumerate(options, start=1):
        output_fn(f"{index}) {option.label}")

    response = input_fn(prompt).strip()
    if allow_cancel and response.lower() in {"", "q", "quit"}:
        raise CancelledError("Selection cancelled.")
    if not response.isdigit():
        raise ValidationError("Selection must be a number.")

    selected_index = int(response)
    if selected_index < 1 or selected_index > len(options):
        raise ValidationError("Selection is out of range.")
    return options[selected_index - 1].value
