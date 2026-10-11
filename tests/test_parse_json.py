import pytest

from crossfoot.model import PRICE_PER_MTOK, parse_json, price


def test_plain_and_fenced_answers_still_parse():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('```\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


def test_prose_before_after_or_around_the_object():
    assert parse_json('Here is the reading:\n{"value": 12}') == {"value": 12}
    assert parse_json('{"value": 12}\nLet me know if you want another look.') == {"value": 12}
    assert parse_json('Reading the crop, I get this.\n{"value": 12}\nThe last digit is clear.') == {"value": 12}


def test_a_fence_inside_prose_and_prose_after_a_fence():
    assert parse_json('The answer is:\n```json\n{"action": "done"}\n```\nThat is all.') == {"action": "done"}
    assert parse_json('```json\n{"action": "done"}\n``` Hope this helps') == {"action": "done"}


def test_braces_in_the_prose_do_not_hide_the_object():
    assert parse_json('Targets look like {kind: cell}. Answer: {"value": 3}') == {"value": 3}
    assert parse_json('{"rereads": [{"target": {"kind": "grand"}, "dpi": 400}], "action": "reread"} trailing {') \
        == {"rereads": [{"target": {"kind": "grand"}, "dpi": 400}], "action": "reread"}


def test_no_json_still_raises():
    with pytest.raises(ValueError):
        parse_json("I cannot read this image.")
    with pytest.raises(ValueError):
        parse_json("")


def test_price_table_is_the_gateways_list():
    assert PRICE_PER_MTOK == {"claude-haiku": (1.10, 5.50), "claude-sonnet-4.6": (3.30, 16.50),
                              "claude-opus-4.6": (5.50, 27.50)}
    assert price("claude-sonnet-4.6", 1_000_000, 1_000_000) == pytest.approx(19.80)
