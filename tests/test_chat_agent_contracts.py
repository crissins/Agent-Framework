import pytest

from agents.chat_agent import (
    build_book_request,
    parse_book_request_from_response,
)


def test_parse_book_request_from_response_valid_payload():
    text = '''
Some response text.
```book_request_json
{
  "topic": "IA para niños",
  "target_audience_age": 10,
  "language": "Spanish",
  "country": "Mexico",
  "learning_method": "Scandinavian",
  "num_chapters": 4,
  "pages_per_chapter": 3
}
```
'''

    parsed = parse_book_request_from_response(text)

    assert parsed is not None
    assert parsed["topic"] == "IA para niños"
    assert parsed["target_audience_age"] == 10


def test_parse_book_request_from_response_missing_required_fields_returns_none():
    text = '''
```book_request_json
{
  "topic": "IA para niños",
  "language": "Spanish"
}
```
'''

    parsed = parse_book_request_from_response(text)

    assert parsed is None


def test_build_book_request_validates_and_coerces_values():
    payload = {
        "topic": "Astronomía",
        "target_audience_age": "12",
        "language": "Spanish",
        "country": "Chile",
        "learning_method": "Montessori",
        "num_chapters": "5",
        "pages_per_chapter": "4",
    }

    request = build_book_request(payload)

    assert request.topic == "Astronomía"
    assert request.target_audience_age == 12
    assert request.num_chapters == 5
    assert request.pages_per_chapter == 4


def test_build_book_request_invalid_payload_raises_value_error():
    payload = {
        "topic": "Astronomía",
        "language": "Spanish",
    }

    with pytest.raises(ValueError):
        build_book_request(payload)
