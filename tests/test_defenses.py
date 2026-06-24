"""核心注入防禦邏輯的單元測試（不需 API、不需網路）。"""

import json

import pytest

from main import (
    MAX_INPUT_CHARS,
    SAFE_REJECT_MESSAGE,
    extract_translation,
    looks_like_code,
)


@pytest.mark.parametrize(
    "text",
    [
        "#include <stdio.h>",
        "int main() { return 0; }",
        "def hello(): pass",
        "console.log('hi')",
        "```python\nprint(1)\n```",
        "typedef struct Node Node;",
        "a; b; c; d",  # 多個分號
    ],
)
def test_looks_like_code_detects_code(text):
    assert looks_like_code(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "你好嗎？",
        "Apa kabar?",
        "今天天氣很好，記得帶傘。",
        "Tolong bantu saya membersihkan kamar.",
        "媽媽說晚餐七點吃飯",
    ],
)
def test_looks_like_code_allows_normal_text(text):
    assert looks_like_code(text) is False


def test_extract_translation_valid_json():
    raw = json.dumps({"source_lang": "zh", "translation": "Apa kabar?"})
    assert extract_translation(raw) == "Apa kabar?"


def test_extract_translation_invalid_json_returns_safe_message():
    assert extract_translation("這不是 JSON") == SAFE_REJECT_MESSAGE


def test_extract_translation_empty_translation_returns_safe_message():
    raw = json.dumps({"source_lang": "zh", "translation": ""})
    assert extract_translation(raw) == SAFE_REJECT_MESSAGE


def test_extract_translation_missing_field_returns_safe_message():
    raw = json.dumps({"source_lang": "zh"})
    assert extract_translation(raw) == SAFE_REJECT_MESSAGE


def test_extract_translation_code_payload_is_blocked():
    raw = json.dumps({"source_lang": "zh", "translation": "#include <stdio.h>\nint main(){}"})
    assert extract_translation(raw) == SAFE_REJECT_MESSAGE


def test_extract_translation_json_array_returns_safe_message():
    # 合法 JSON 但不是物件，.get 會觸發 AttributeError
    assert extract_translation("[1, 2, 3]") == SAFE_REJECT_MESSAGE


def test_input_truncation_limit_is_reasonable():
    assert 0 < MAX_INPUT_CHARS <= 1000


def test_input_truncation_slicing():
    long_text = "字" * 2000
    assert len(long_text[:MAX_INPUT_CHARS]) == MAX_INPUT_CHARS
