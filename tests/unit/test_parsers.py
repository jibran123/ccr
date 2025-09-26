"""Unit tests for query parsers."""

import pytest
from app.utils.parsers import QueryParser


class TestQueryParser:
    """Test query parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = QueryParser()
    
    def test_parse_simple_query(self):
        """Test parsing simple text query."""
        result = self.parser.parse_query("user api")
        assert result['type'] == 'simple'
        assert result['value'] == 'user api'
    
    def test_parse_property_query(self):
        """Test parsing property-based query."""
        result = self.parser.parse_query('APIName="UserService"')
        assert result['type'] == 'property'
        assert result['property'] == 'APIName'
        assert result['operator'] == '='
        assert result['value'] == 'UserService'
    
    def test_parse_comparison_query(self):
        """Test parsing comparison query."""
        result = self.parser.parse_query('APIVersion > 2.0')
        assert result['type'] == 'property'
        assert result['property'] == 'APIVersion'
        assert result['operator'] == '>'
        assert result['value'] == '2.0'
    
    def test_parse_logical_and_query(self):
        """Test parsing logical AND query."""
        result = self.parser.parse_query('Platform=AWS AND Environment=prod')
        assert result['type'] == 'logical'
        assert result['operator'] == 'AND'
        assert len(result['conditions']) == 2
        assert result['conditions'][0]['property'] == 'Platform'
        assert result['conditions'][1]['property'] == 'Environment'
    
    def test_parse_logical_or_query(self):
        """Test parsing logical OR query."""
        result = self.parser.parse_query('APIName contains user OR APIName contains customer')
        assert result['type'] == 'logical'
        assert result['operator'] == 'OR'
        assert len(result['conditions']) == 2
    
    def test_parse_empty_query(self):
        """Test parsing empty query."""
        result = self.parser.parse_query("")
        assert result == {}
    
    def test_parse_whitespace_query(self):
        """Test parsing whitespace-only query."""
        result = self.parser.parse_query("   ")
        assert result == {}
    
    def test_extract_tokens(self):
        """Test token extraction."""
        tokens = self.parser.extract_tokens('APIName=user AND Platform!=AWS')
        assert 'APIName' in tokens
        assert 'user' in tokens
        assert 'Platform' in tokens
        assert 'AWS' in tokens
        assert 'AND' not in tokens
        assert '=' not in tokens