"""Unit tests for XML extraction utilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from lxml import etree

from labapi.exceptions import ExtractionError
from labapi.util.extract import (
    EtreeExtractorDict,
    _flatten_dict,
    extract_etree,
    to_bool,
)


# Tests for _flatten_dict
@pytest.mark.parametrize(
    ("val", "prefix", "expected"),
    [
        # Single-level, no prefix
        (
            {"a": str, "b": int},
            "",
            {"/a": str, "/b": int},
        ),
        # Nested, no prefix
        (
            {"a": {"b": int, "c": str}},
            "",
            {"/a/b": int, "/a/c": str},
        ),
        # Nested with prefix
        (
            {"a": {"b": int}, "c": str},
            "root",
            {"root/a/b": int, "root/c": str},
        ),
        # Deeper nesting
        (
            {"a": {"b": {"c": str}}},
            "",
            {"/a/b/c": str},
        ),
        # Empty dict at leaf
        ({"a": {"b": {"c": {}}}}, "", {}),
        # Multiple nested levels
        (
            {"x": {"y": {"z": int}}, "a": str},
            "",
            {"/x/y/z": int, "/a": str},
        ),
    ],
)
def test_flatten_dict_success(
    val: EtreeExtractorDict,
    prefix: str,
    expected: dict[str, Callable[[Any], Any]],
):
    """Test _flatten_dict with valid inputs."""
    assert _flatten_dict(val, prefix) == expected


@pytest.mark.parametrize(
    ("val", "prefix"),
    [
        ({"": {"b": int}}, ""),  # Empty key
        ({"a": {"": str}}, ""),  # Empty key nested
    ],
)
def test_flatten_dict_value_error(val: EtreeExtractorDict, prefix: str):
    """Test _flatten_dict raises ValueError for empty keys."""
    with pytest.raises(ValueError, match="Key cannot be empty string"):
        _flatten_dict(val, prefix)


# Tests for to_bool
@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("false", False),
        ("FALSE", False),
        ("False", False),
        ("tRuE", True),
        ("fAlSe", False),
        ("TrUe", True),
        ("FaLsE", False),
    ],
)
def test_to_bool_success(s: str, expected: bool):
    """Test to_bool with valid boolean strings."""
    assert to_bool(s) is expected


@pytest.mark.parametrize(
    "s",
    [
        "",
        "0",
        "1",
        "yes",
        "no",
        "truthy",
        "falsey",
        " false ",  # whitespace not stripped
        " true ",  # whitespace not stripped
        "none",
        "True ",  # trailing space
        " False",  # leading space
    ],
)
def test_to_bool_invalid_raises(s: str):
    """Test to_bool raises ValueError for invalid strings."""
    with pytest.raises(ValueError, match=r"Cannot convert '.*' to bool"):
        to_bool(s)


# Tests for extract_etree
def test_extract_etree_single_level():
    """Test extract_etree with single-level XML."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <name>Test Name</name>
        <age>25</age>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "name": str,
        "age": int,
    }

    result = extract_etree(element, format_dict)

    assert result == {"name": "Test Name", "age": 25}


def test_extract_etree_nested():
    """Test extract_etree with nested XML structure."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <user>
            <name>John Doe</name>
            <age>30</age>
        </user>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "user": {
            "name": str,
            "age": int,
        }
    }

    result = extract_etree(element, format_dict)

    assert result == {"name": "John Doe", "age": 30}


def test_extract_etree_with_to_bool():
    """Test extract_etree with to_bool converter."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <active>true</active>
        <enabled>false</enabled>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "active": to_bool,
        "enabled": to_bool,
    }

    result = extract_etree(element, format_dict)

    assert result == {"active": True, "enabled": False}


def test_extract_etree_missing_element_raises():
    """Test extract_etree raises ValueError when element is missing."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <name>Test</name>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "name": str,
        "missing": str,
    }

    with pytest.raises(
        ExtractionError,
        match=(r"Could not find value for '.+/missing' while parsing element at /root"),
    ):
        extract_etree(element, format_dict)


def test_extract_etree_mapper_fails_raises():
    """Test extract_etree raises ValueError when mapper fails."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <value>not_a_bool</value>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "value": to_bool,
    }

    with pytest.raises(
        ExtractionError,
        match=(
            r"Could not map value 'not_a_bool' with to_bool for '.+/value' while "
            r"parsing element at /root"
        ),
    ):
        extract_etree(element, format_dict)


def test_extract_etree_mapper_without_name_raises():
    """Test extract_etree raises ExtractionError properly when mapper has no __name__."""
    from functools import partial

    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <value>not_an_int</value>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    mapper = partial(int, base=16)
    format_dict: EtreeExtractorDict = {
        "value": mapper,
    }

    with pytest.raises(
        ExtractionError,
        match=(
            r"Could not map value 'not_an_int' with .*partial.* for '.+/value' while "
            r"parsing element at /root"
        ),
    ):
        extract_etree(element, format_dict)


def test_extract_etree_warns_on_duplicate_leaf_names():
    """Test duplicate leaf extraction warns and last assignment wins."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <a>
            <id>first</id>
        </a>
        <b>
            <id>second</id>
        </b>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "a": {"id": str},
        "b": {"id": str},
    }

    with pytest.warns(
        UserWarning,
        match=r"Duplicate extractor leaf 'id' encountered at '\.//b/id'; overwriting previous value",
    ):
        result = extract_etree(element, format_dict)

    assert result == {"id": "second"}


def test_extract_etree_deeply_nested():
    """Test extract_etree with deeply nested structure."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <level1>
            <level2>
                <level3>deep_value</level3>
            </level2>
        </level1>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "level1": {
            "level2": {
                "level3": str,
            }
        }
    }

    result = extract_etree(element, format_dict)

    assert result == {"level3": "deep_value"}


def test_extract_etree_multiple_extractors():
    """Test extract_etree with multiple different extractors."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <root>
        <count>42</count>
        <flag>true</flag>
        <message>Hello</message>
    </root>
    """
    element = etree.fromstring(bytes(xml, encoding="utf-8"))
    format_dict: EtreeExtractorDict = {
        "count": int,
        "flag": to_bool,
        "message": str,
    }

    result = extract_etree(element, format_dict)

    assert result == {"count": 42, "flag": True, "message": "Hello"}
