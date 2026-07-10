import pytest

from track.errors import CancelledError, ValidationError
from track.picker import Option, pick_one


def test_pick_one_returns_selected_value():
    value = pick_one(
        [Option(value=10, label="ten"), Option(value=20, label="twenty")],
        input_fn=lambda _: "2",
        output_fn=lambda _: None,
    )
    assert value == 20


def test_pick_one_rejects_non_numeric_selection():
    with pytest.raises(ValidationError, match="Selection must be a number"):
        pick_one(
            [Option(value=10, label="ten")],
            input_fn=lambda _: "abc",
            output_fn=lambda _: None,
        )


def test_pick_one_rejects_out_of_range_selection():
    with pytest.raises(ValidationError, match="Selection is out of range"):
        pick_one(
            [Option(value=10, label="ten")],
            input_fn=lambda _: "2",
            output_fn=lambda _: None,
        )


def test_pick_one_allows_cancel_shortcuts():
    with pytest.raises(CancelledError, match="Selection cancelled"):
        pick_one(
            [Option(value=10, label="ten")],
            input_fn=lambda _: "q",
            output_fn=lambda _: None,
        )
