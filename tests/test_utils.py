import sys
from pathlib import Path

"""
Unit tests for utility functions.

Focus: calculate_stats
These tests verify that the function correctly computes totals
from a list of entry-like rows.
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import calculate_stats


def test_calculate_stats_empty_list():
    """Empty input should return zeroed formatted totals."""
    stats = calculate_stats([])

    assert stats["total_miles"] == "0.00"
    assert stats["total_made"] == "0.00"
    assert stats["total_set_aside"] == "0.00"
    assert stats["total_deductions"] == "0.00"


def test_calculate_stats_basic_values():
    """Basic summation of miles and earnings with valid entry structure."""
    rows = [
        {"date": "2025-01-06", "miles": 10, "earnings": 20, "notes": ""},
        {"date": "2025-01-13", "miles": 5, "earnings": 15, "notes": ""},
    ]

    stats = calculate_stats(rows)

    assert stats["total_miles"] == "15.00"
    assert stats["total_made"] == "35.00"
    assert stats["total_set_aside"] == "8.75"
    assert stats["total_deductions"] == "10.50"


def test_calculate_stats_with_zero_values():
    """Zero values should still be handled correctly."""
    rows = [
        {"date": "2025-01-06", "miles": 0, "earnings": 0, "notes": ""},
        {"date": "2025-01-13", "miles": 5, "earnings": 10, "notes": ""},
    ]

    stats = calculate_stats(rows)

    assert stats["total_miles"] == "5.00"
    assert stats["total_made"] == "10.00"
    assert stats["total_set_aside"] == "2.50"
    assert stats["total_deductions"] == "3.50"