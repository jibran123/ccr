"""
Unit tests for Database Service helper functions.

Tests query parsing and detection functions that don't require MongoDB connection.

Week 13-14: Testing & Quality Assurance - Phase 1 Quick Wins (Pure Functions)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.database import DatabaseService


class TestQueryDetectionMethods:
    """Test query type detection methods."""

    def setup_method(self):
        """Create a mock DatabaseService instance without connecting to MongoDB."""
        # Mock the _connect method to avoid MongoDB connection
        with patch.object(DatabaseService, '_connect', return_value=None):
            self.db_service = DatabaseService('mongodb://fake:27017', 'test_db')

    def test_is_properties_search_with_properties_colon_space(self):
        """Test _is_properties_search with 'Properties :' format."""
        assert self.db_service._is_properties_search('Properties : owner = team') is True

    def test_is_properties_search_with_properties_colon_no_space(self):
        """Test _is_properties_search with 'Properties:' format."""
        assert self.db_service._is_properties_search('Properties: owner = team') is True

    def test_is_properties_search_with_non_properties_query(self):
        """Test _is_properties_search returns False for non-properties queries."""
        assert self.db_service._is_properties_search('Platform = IP4') is False
        assert self.db_service._is_properties_search('simple text search') is False
        assert self.db_service._is_properties_search('') is False

    def test_is_properties_search_case_sensitive(self):
        """Test _is_properties_search is case-sensitive."""
        assert self.db_service._is_properties_search('Properties : key = value') is True
        assert self.db_service._is_properties_search('properties : key = value') is False
        assert self.db_service._is_properties_search('PROPERTIES : key = value') is False

    def test_is_attribute_search_with_equals(self):
        """Test _is_attribute_search with equals operator."""
        assert self.db_service._is_attribute_search('Platform = IP4') is True
        assert self.db_service._is_attribute_search('Status = RUNNING') is True

    def test_is_attribute_search_with_not_equals(self):
        """Test _is_attribute_search with not equals operator."""
        assert self.db_service._is_attribute_search('Platform != IP4') is True

    def test_is_attribute_search_with_comparison_operators(self):
        """Test _is_attribute_search with comparison operators that contain =."""
        # Only >= and <= contain =, so they are detected as attribute search
        assert self.db_service._is_attribute_search('Version >= 2.0') is True
        assert self.db_service._is_attribute_search('Version <= 1.0') is True
        # > and < alone don't contain =, so they're not detected
        # (They're handled later in _parse_single_condition)
        assert self.db_service._is_attribute_search('Version > 1.5') is False
        assert self.db_service._is_attribute_search('Version < 3.0') is False

    def test_is_attribute_search_excludes_properties_search(self):
        """Test _is_attribute_search returns False for Properties search."""
        assert self.db_service._is_attribute_search('Properties : key = value') is False
        assert self.db_service._is_attribute_search('Properties: key = value') is False

    def test_is_attribute_search_with_simple_text(self):
        """Test _is_attribute_search returns False for simple text."""
        assert self.db_service._is_attribute_search('simple search') is False
        assert self.db_service._is_attribute_search('my api name') is False
        assert self.db_service._is_attribute_search('') is False


class TestLogicalQueryParsing:
    """Test logical query parsing (_parse_logical_query)."""

    def setup_method(self):
        """Create a mock DatabaseService instance."""
        with patch.object(DatabaseService, '_connect', return_value=None):
            self.db_service = DatabaseService('mongodb://fake:27017', 'test_db')

    def test_parse_logical_query_single_condition(self):
        """Test parsing single condition without logical operators."""
        result = self.db_service._parse_logical_query('Platform = IP4')

        assert result['operator'] == 'NONE'
        assert len(result['conditions']) == 1
        assert result['conditions'][0] == 'Platform = IP4'

    def test_parse_logical_query_and_operator(self):
        """Test parsing query with AND operator."""
        result = self.db_service._parse_logical_query('Platform = IP4 AND Environment = prd')

        assert result['operator'] == 'AND'
        assert len(result['conditions']) == 2
        assert 'Platform = IP4' in result['conditions']
        assert 'Environment = prd' in result['conditions']

    def test_parse_logical_query_or_operator(self):
        """Test parsing query with OR operator."""
        result = self.db_service._parse_logical_query('Status = RUNNING OR Status = DEPLOYING')

        assert result['operator'] == 'OR'
        assert len(result['conditions']) == 2
        assert 'Status = RUNNING' in result['conditions']
        assert 'Status = DEPLOYING' in result['conditions']

    def test_parse_logical_query_multiple_and_conditions(self):
        """Test parsing query with multiple AND conditions."""
        result = self.db_service._parse_logical_query('Platform = IP4 AND Environment = prd AND Status = RUNNING')

        assert result['operator'] == 'AND'
        assert len(result['conditions']) == 3
        assert 'Platform = IP4' in result['conditions']
        assert 'Environment = prd' in result['conditions']
        assert 'Status = RUNNING' in result['conditions']

    def test_parse_logical_query_multiple_or_conditions(self):
        """Test parsing query with multiple OR conditions."""
        result = self.db_service._parse_logical_query('Status = RUNNING OR Status = STOPPED OR Status = FAILED')

        assert result['operator'] == 'OR'
        assert len(result['conditions']) == 3

    def test_parse_logical_query_and_takes_precedence(self):
        """Test that AND takes precedence over OR."""
        result = self.db_service._parse_logical_query('Platform = IP4 OR Platform = IP5 AND Environment = prd')

        # AND takes precedence, so it splits by AND first
        assert result['operator'] == 'AND'
        assert len(result['conditions']) == 2

    def test_parse_logical_query_strips_whitespace(self):
        """Test that conditions are stripped of whitespace."""
        result = self.db_service._parse_logical_query('  Platform = IP4   AND   Environment = prd  ')

        assert result['operator'] == 'AND'
        assert 'Platform = IP4' in result['conditions']
        assert 'Environment = prd' in result['conditions']

    def test_parse_logical_query_empty_string(self):
        """Test parsing empty string."""
        result = self.db_service._parse_logical_query('')

        assert result['operator'] == 'NONE'
        assert len(result['conditions']) == 1
        assert result['conditions'][0] == ''


class TestSingleConditionParsing:
    """Test single condition parsing (_parse_single_condition)."""

    def setup_method(self):
        """Create a mock DatabaseService instance."""
        with patch.object(DatabaseService, '_connect', return_value=None):
            self.db_service = DatabaseService('mongodb://fake:27017', 'test_db')

    def test_parse_single_condition_equals_case_sensitive(self):
        """Test parsing equals condition with case sensitivity."""
        result = self.db_service._parse_single_condition('Platform = IP4', case_sensitive=True)

        assert 'Platform.PlatformID' in result
        assert result['Platform.PlatformID'] == {'$eq': 'IP4'}

    def test_parse_single_condition_equals_case_insensitive(self):
        """Test parsing equals condition without case sensitivity."""
        result = self.db_service._parse_single_condition('Platform = ip4', case_sensitive=False)

        assert 'Platform.PlatformID' in result
        # Should use regex for case insensitive
        assert '$regex' in result['Platform.PlatformID']

    def test_parse_single_condition_not_equals(self):
        """Test parsing not equals condition."""
        result = self.db_service._parse_single_condition('Status != FAILED', case_sensitive=True)

        assert 'Platform.Environment.status' in result
        assert result['Platform.Environment.status'] == {'$ne': 'FAILED'}

    def test_parse_single_condition_greater_than_or_equal(self):
        """Test parsing >= condition."""
        result = self.db_service._parse_single_condition('Version >= 2.0', case_sensitive=True)

        assert 'Platform.Environment.version' in result
        assert result['Platform.Environment.version'] == {'$gte': 2.0}

    def test_parse_single_condition_less_than_or_equal(self):
        """Test parsing <= condition."""
        result = self.db_service._parse_single_condition('Version <= 1.5', case_sensitive=True)

        assert 'Platform.Environment.version' in result
        assert result['Platform.Environment.version'] == {'$lte': 1.5}

    def test_parse_single_condition_greater_than(self):
        """Test parsing > condition."""
        result = self.db_service._parse_single_condition('Version > 1.0', case_sensitive=True)

        assert 'Platform.Environment.version' in result
        assert result['Platform.Environment.version'] == {'$gt': 1.0}

    def test_parse_single_condition_less_than(self):
        """Test parsing < condition."""
        result = self.db_service._parse_single_condition('Version < 3.0', case_sensitive=True)

        assert 'Platform.Environment.version' in result
        assert result['Platform.Environment.version'] == {'$lt': 3.0}

    def test_parse_single_condition_contains(self):
        """Test parsing contains condition."""
        result = self.db_service._parse_single_condition('API Name contains user', case_sensitive=False)

        assert 'API Name' in result
        assert '$regex' in result['API Name']
        assert 'user' in result['API Name']['$regex']

    def test_parse_single_condition_startswith(self):
        """Test parsing startswith condition."""
        result = self.db_service._parse_single_condition('API Name startswith api', case_sensitive=False)

        assert 'API Name' in result
        assert '$regex' in result['API Name']
        assert '^' in result['API Name']['$regex']

    def test_parse_single_condition_endswith(self):
        """Test parsing endswith condition."""
        result = self.db_service._parse_single_condition('API Name endswith service', case_sensitive=False)

        assert 'API Name' in result
        assert '$regex' in result['API Name']
        assert '$' in result['API Name']['$regex']

    def test_parse_single_condition_with_quotes(self):
        """Test parsing condition with quoted values."""
        result = self.db_service._parse_single_condition('Platform = "IP4"', case_sensitive=True)

        # Should strip quotes
        assert 'Platform.PlatformID' in result
        assert result['Platform.PlatformID'] == {'$eq': 'IP4'}

    def test_parse_single_condition_with_single_quotes(self):
        """Test parsing condition with single quoted values."""
        result = self.db_service._parse_single_condition("Environment = 'prd'", case_sensitive=True)

        assert 'Platform.Environment.environmentID' in result
        assert result['Platform.Environment.environmentID'] == {'$eq': 'prd'}

    def test_parse_single_condition_attribute_mapping(self):
        """Test attribute name mapping."""
        # Test all mapped attributes
        test_cases = [
            ('API Name = test', 'API Name'),
            ('Platform = IP4', 'Platform.PlatformID'),
            ('PlatformID = IP4', 'Platform.PlatformID'),
            ('Environment = prd', 'Platform.Environment.environmentID'),
            ('Status = RUNNING', 'Platform.Environment.status'),
            ('Version = 1.0', 'Platform.Environment.version'),
            ('UpdatedBy = John', 'Platform.Environment.updatedBy'),
        ]

        for condition, expected_field in test_cases:
            result = self.db_service._parse_single_condition(condition, case_sensitive=True)
            assert expected_field in result

    def test_parse_single_condition_numeric_comparison(self):
        """Test parsing numeric comparison."""
        result = self.db_service._parse_single_condition('Version >= 2.5', case_sensitive=True)

        assert 'Platform.Environment.version' in result
        assert result['Platform.Environment.version'] == {'$gte': 2.5}

    def test_parse_single_condition_non_numeric_comparison(self):
        """Test parsing non-numeric comparison."""
        result = self.db_service._parse_single_condition('Status > RUNNING', case_sensitive=True)

        # Should treat as string since it's not numeric
        assert 'Platform.Environment.status' in result
        assert result['Platform.Environment.status'] == {'$gt': 'RUNNING'}

    def test_parse_single_condition_empty_string(self):
        """Test parsing empty condition."""
        result = self.db_service._parse_single_condition('', case_sensitive=True)

        assert result == {}

    def test_parse_single_condition_invalid_format(self):
        """Test parsing invalid condition format."""
        result = self.db_service._parse_single_condition('invalid condition', case_sensitive=True)

        assert result == {}


class TestEdgeCases:
    """Test edge cases in query parsing."""

    def setup_method(self):
        """Create a mock DatabaseService instance."""
        with patch.object(DatabaseService, '_connect', return_value=None):
            self.db_service = DatabaseService('mongodb://fake:27017', 'test_db')

    def test_parse_condition_with_equals_in_value(self):
        """Test parsing condition where value contains equals sign."""
        # This is an edge case that might not work perfectly
        result = self.db_service._parse_single_condition('API Name = test=value', case_sensitive=True)

        # Should split on first =
        assert 'API Name' in result

    def test_parse_condition_with_spaces_in_value(self):
        """Test parsing condition with spaces in value."""
        result = self.db_service._parse_single_condition('UpdatedBy = John Doe', case_sensitive=True)

        assert 'Platform.Environment.updatedBy' in result
        # Value should preserve spaces
        assert 'John Doe' in str(result)

    def test_parse_logical_query_with_empty_conditions(self):
        """Test parsing logical query that results in empty conditions."""
        result = self.db_service._parse_logical_query('Platform = IP4 AND  AND Environment = prd')

        # Should handle empty parts gracefully
        assert result['operator'] == 'AND'
        # Empty strings should be filtered out
        assert all(cond.strip() for cond in result['conditions'])

    def test_is_properties_search_with_properties_in_middle(self):
        """Test properties detection when Properties appears in middle."""
        # Should still detect it
        assert self.db_service._is_properties_search('search Properties : key = value') is True

    def test_parse_condition_case_insensitive_options(self):
        """Test that case insensitive uses regex options correctly."""
        result = self.db_service._parse_single_condition('Platform = IP4', case_sensitive=False)

        assert 'Platform.PlatformID' in result
        assert '$regex' in result['Platform.PlatformID']
        assert '$options' in result['Platform.PlatformID']
        assert 'i' in result['Platform.PlatformID']['$options']

    def test_parse_condition_with_leading_trailing_whitespace(self):
        """Test parsing condition with whitespace."""
        result = self.db_service._parse_single_condition('  Platform   =   IP4  ', case_sensitive=True)

        assert 'Platform.PlatformID' in result
        assert result['Platform.PlatformID'] == {'$eq': 'IP4'}
