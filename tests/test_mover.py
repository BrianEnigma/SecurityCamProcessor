"""Property-based tests for Mover date transformation."""

import os
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

# Add parent directory to path so we can import mover
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mover import Mover


# Strategy for 8-character MMDDYYYY strings
mm = st.integers(min_value=0, max_value=99).map(lambda x: f"{x:02d}")
dd = st.integers(min_value=0, max_value=99).map(lambda x: f"{x:02d}")
yyyy = st.integers(min_value=0, max_value=9999).map(lambda x: f"{x:04d}")

eight_char_dates = st.tuples(mm, dd, yyyy).map(lambda t: t[0] + t[1] + t[2])

# Strategy for strings whose length is NOT 8
non_eight_char_strings = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=0,
    max_size=30,
).filter(lambda s: len(s) != 8)


# Feature: ruby-to-python-rewrite, Property 7: Date string transformation
@settings(max_examples=100)
@given(date_str=eight_char_dates)
def test_date_transform_eight_char_swaps(date_str: str) -> None:
    """Property 7 (8-char case): For any 8-character string in MMDDYYYY format,
    _date_transform produces YYYYMMDD by swapping characters 0-3 with 4-7.

    Validates: Requirements 6.5
    """
    mover = Mover.__new__(Mover)
    result = mover._date_transform(date_str)

    assert len(result) == 8
    assert result == date_str[4:8] + date_str[0:4]


# Feature: ruby-to-python-rewrite, Property 7: Date string transformation
@settings(max_examples=100)
@given(s=non_eight_char_strings)
def test_date_transform_non_eight_char_passthrough(s: str) -> None:
    """Property 7 (non-8-char case): For any string whose length is not 8,
    _date_transform returns the original string unchanged.

    Validates: Requirements 6.9
    """
    mover = Mover.__new__(Mover)
    result = mover._date_transform(s)

    assert result == s
