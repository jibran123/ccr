"""Unit tests for validators."""

import pytest
from datetime import datetime
from app.utils.validators import ValueComparator


class TestValueComparator:
    """Test value comparison functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.comparator = ValueComparator()
    
    def test_parse_integer_value(self):
        """Test parsing integer values."""
        result = self.comparator.parse_value("42")
        assert result == 42
        assert isinstance(result, int)
    
    def test_parse_float_value(self):
        """Test parsing float values."""
        result = self.comparator.parse_value("3.14")
        assert result == 3.14
        assert isinstance(result, float)
    
    def test_parse_date_value(self):
        """Test parsing date values."""
        result = self.comparator.parse_value("2024-01-15T10:30:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_string_value(self):
        """Test parsing string values."""
        result = self.comparator.parse_value("hello world")
        assert result == "hello world"
        assert isinstance(result, str)
    
    def test_compare_equal(self):
        """Test equality comparison."""
        assert self.comparator.compare_values("test", "test", "=")
        assert not self.comparator.compare_values("test", "other", "=")
    
    def test_compare_not_equal(self):
        """Test inequality comparison."""
        assert self.comparator.compare_values("test", "other", "!=")
        assert not self.comparator.compare_values("test", "test", "!=")
    
    def test_compare_greater_than(self):
        """Test greater than comparison."""
        assert self.comparator.compare_values(10, 5, ">")
        assert not self.comparator.compare_values(5, 10, ">")
    
    def test_compare_contains(self):
        """Test contains comparison."""
        assert self.comparator.compare_values("hello world", "world", "contains")
        assert not self.comparator.compare_values("hello world", "test", "contains")
    
    def test_compare_startswith(self):
        """Test startswith comparison."""
        assert self.comparator.compare_values("hello world", "hello", "startswith")
        assert not self.comparator.compare_values("hello world", "world", "startswith")
    
    def test_compare_endswith(self):
        """Test endswith comparison."""
        assert self.comparator.compare_values("hello world", "world", "endswith")
        assert not self.comparator.compare_values("hello world", "hello", "endswith")
    
    def test_compare_with_none(self):
        """Test comparison with None values."""
        assert self.comparator.compare_values(None, "test", "!=")
        assert not self.comparator.compare_values(None, "test", "=")
    
    def test_validate_operator(self):
        """Test operator validation."""
        assert self.comparator.validate_operator("=")
        assert self.comparator.validate_operator("contains")
        assert not self.comparator.validate_operator("invalid")
    
    def test_normalize_value(self):
        """Test value normalization."""
        assert self.comparator.normalize_value("  test  ") == "test"
        assert self.comparator.normalize_value(42) == 42
        assert self.comparator.normalize_value(None) is None