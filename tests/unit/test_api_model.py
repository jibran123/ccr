"""
Unit Tests: APIModel
Tests for API data model
Week 13-14: Testing & Quality Assurance - Phase 1
"""

import pytest
from datetime import datetime
from bson import ObjectId

from app.models.api_model import APIModel


class TestAPIModelInitialization:
    """Test APIModel initialization."""

    def test_init_with_full_data(self):
        """Test initialization with complete data."""
        data = {
            '_id': '507f1f77bcf86cd799439011',
            'API Name': 'test-api',
            'PlatformID': 'IP4',
            'Environment': 'tst',
            'Status': 'RUNNING',
            'LastUpdated': '2024-01-01T10:00:00Z',
            'Properties': {'owner': 'team-alpha'}
        }

        model = APIModel(data)

        assert model._id == '507f1f77bcf86cd799439011'
        assert model.api_name == 'test-api'
        assert model.platform_id == 'IP4'
        assert model.environment == 'tst'
        assert model.status == 'RUNNING'
        assert model.last_updated == '2024-01-01T10:00:00Z'
        assert model.properties == {'owner': 'team-alpha'}
        assert model.data == data

    def test_init_with_minimal_data(self):
        """Test initialization with minimal data."""
        data = {
            'API Name': 'minimal-api'
        }

        model = APIModel(data)

        assert model._id is None
        assert model.api_name == 'minimal-api'
        assert model.platform_id == ''
        assert model.environment == ''
        assert model.status == 'Unknown'
        assert model.last_updated is None
        assert model.properties == {}

    def test_init_with_empty_dict(self):
        """Test initialization with empty dictionary."""
        model = APIModel({})

        assert model._id is None
        assert model.api_name == ''
        assert model.platform_id == ''
        assert model.environment == ''
        assert model.status == 'Unknown'
        assert model.last_updated is None
        assert model.properties == {}

    def test_init_preserves_original_data(self):
        """Test that initialization preserves the original data."""
        data = {
            'API Name': 'test-api',
            'custom_field': 'custom_value',
            'nested': {'key': 'value'}
        }

        model = APIModel(data)

        assert model.data == data
        assert model.data['custom_field'] == 'custom_value'
        assert model.data['nested'] == {'key': 'value'}


class TestAPIModelToDictMethod:
    """Test APIModel to_dict() method."""

    def test_to_dict_returns_original_data(self):
        """Test that to_dict returns the original data dictionary."""
        data = {
            '_id': '507f1f77bcf86cd799439011',
            'API Name': 'test-api',
            'PlatformID': 'IP4',
            'Environment': 'tst',
            'Status': 'RUNNING',
            'Properties': {'owner': 'team-alpha'}
        }

        model = APIModel(data)
        result = model.to_dict()

        assert result == data
        assert result is model.data  # Should return the same object

    def test_to_dict_with_minimal_data(self):
        """Test to_dict with minimal data."""
        data = {'API Name': 'minimal-api'}

        model = APIModel(data)
        result = model.to_dict()

        assert result == data

    def test_to_dict_preserves_custom_fields(self):
        """Test that to_dict preserves custom fields not in model attributes."""
        data = {
            'API Name': 'test-api',
            'custom_field_1': 'value1',
            'custom_field_2': 'value2',
            'nested': {'deep': {'field': 'value'}}
        }

        model = APIModel(data)
        result = model.to_dict()

        assert result['custom_field_1'] == 'value1'
        assert result['custom_field_2'] == 'value2'
        assert result['nested']['deep']['field'] == 'value'


class TestAPIModelFromDbMethod:
    """Test APIModel from_db() class method."""

    def test_from_db_with_objectid(self):
        """Test from_db converts ObjectId to string."""
        doc = {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'API Name': 'test-api',
            'PlatformID': 'IP4'
        }

        model = APIModel.from_db(doc)

        assert isinstance(model._id, str)
        assert model._id == '507f1f77bcf86cd799439011'
        assert model.api_name == 'test-api'
        assert model.platform_id == 'IP4'

    def test_from_db_with_string_id(self):
        """Test from_db with string ID (already converted)."""
        doc = {
            '_id': '507f1f77bcf86cd799439011',
            'API Name': 'test-api'
        }

        model = APIModel.from_db(doc)

        assert model._id == '507f1f77bcf86cd799439011'
        assert isinstance(model._id, str)

    def test_from_db_without_id(self):
        """Test from_db without _id field."""
        doc = {
            'API Name': 'test-api',
            'PlatformID': 'IP4'
        }

        model = APIModel.from_db(doc)

        assert model._id is None
        assert model.api_name == 'test-api'

    def test_from_db_returns_api_model_instance(self):
        """Test that from_db returns an APIModel instance."""
        doc = {'API Name': 'test-api'}

        model = APIModel.from_db(doc)

        assert isinstance(model, APIModel)

    def test_from_db_preserves_all_fields(self):
        """Test that from_db preserves all database fields."""
        doc = {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'API Name': 'test-api',
            'PlatformID': 'IP4',
            'Environment': 'prd',
            'Status': 'RUNNING',
            'LastUpdated': '2024-01-01T10:00:00Z',
            'Properties': {'owner': 'team-alpha'},
            'custom_db_field': 'custom_value'
        }

        model = APIModel.from_db(doc)

        assert model.data['custom_db_field'] == 'custom_value'
        assert model.to_dict()['custom_db_field'] == 'custom_value'


class TestAPIModelEdgeCases:
    """Test APIModel edge cases and error handling."""

    def test_model_with_none_values(self):
        """Test model with None values in data."""
        data = {
            'API Name': None,
            'PlatformID': None,
            'Status': None,
            'Properties': None
        }

        model = APIModel(data)

        # dict.get() returns None when value is explicitly None (not missing)
        assert model.api_name is None
        assert model.platform_id is None
        assert model.status is None
        assert model.properties is None

    def test_model_with_mixed_types(self):
        """Test model handles mixed data types."""
        data = {
            'API Name': 'test-api',
            'PlatformID': 123,  # Number instead of string
            'Status': True,  # Boolean instead of string
            'Properties': {'count': 42, 'enabled': True}
        }

        model = APIModel(data)

        # Should preserve original types
        assert model.platform_id == 123
        assert model.status is True
        assert model.properties['count'] == 42
        assert model.properties['enabled'] is True

    def test_model_with_special_characters(self):
        """Test model with special characters in strings."""
        data = {
            'API Name': 'test-api-with-特殊字符',
            'PlatformID': 'IP4',
            'Properties': {'owner': 'team-αβγ', 'note': 'Special chars: !@#$%^&*()'}
        }

        model = APIModel(data)

        assert model.api_name == 'test-api-with-特殊字符'
        assert model.properties['owner'] == 'team-αβγ'
        assert model.properties['note'] == 'Special chars: !@#$%^&*()'

    def test_model_immutability_of_data(self):
        """Test that modifying model attributes doesn't affect original data."""
        data = {
            'API Name': 'test-api',
            'PlatformID': 'IP4'
        }

        model = APIModel(data)

        # Modify model attribute
        model.api_name = 'modified-api'

        # Original data should remain unchanged
        assert data['API Name'] == 'test-api'

        # But to_dict should return original data
        assert model.to_dict()['API Name'] == 'test-api'

    def test_from_db_with_various_id_types(self):
        """Test from_db handles various _id types."""
        # Test with integer ID
        doc1 = {'_id': 12345, 'API Name': 'test1'}
        model1 = APIModel.from_db(doc1)
        assert model1._id == '12345'

        # Test with string ID
        doc2 = {'_id': 'string-id', 'API Name': 'test2'}
        model2 = APIModel.from_db(doc2)
        assert model2._id == 'string-id'

        # Test with ObjectId
        doc3 = {'_id': ObjectId('507f1f77bcf86cd799439011'), 'API Name': 'test3'}
        model3 = APIModel.from_db(doc3)
        assert model3._id == '507f1f77bcf86cd799439011'


class TestAPIModelDataConsistency:
    """Test data consistency across model operations."""

    def test_round_trip_consistency(self):
        """Test data consistency through init -> to_dict cycle."""
        original_data = {
            '_id': '507f1f77bcf86cd799439011',
            'API Name': 'test-api',
            'PlatformID': 'IP4',
            'Environment': 'tst',
            'Status': 'RUNNING',
            'LastUpdated': '2024-01-01T10:00:00Z',
            'Properties': {'owner': 'team-alpha'},
            'custom_field': 'custom_value'
        }

        model = APIModel(original_data)
        result_data = model.to_dict()

        assert result_data == original_data
        assert result_data is original_data  # Same object reference

    def test_from_db_round_trip(self):
        """Test data consistency through from_db -> to_dict cycle."""
        original_doc = {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'API Name': 'test-api',
            'PlatformID': 'IP4',
            'Properties': {'owner': 'team-alpha'}
        }

        model = APIModel.from_db(original_doc)
        result_data = model.to_dict()

        # _id should be converted to string
        assert result_data['_id'] == '507f1f77bcf86cd799439011'
        assert result_data['API Name'] == 'test-api'
        assert result_data['PlatformID'] == 'IP4'
        assert result_data['Properties'] == {'owner': 'team-alpha'}

    def test_multiple_models_independence(self):
        """Test that multiple model instances are independent."""
        data1 = {'API Name': 'api-1', 'Properties': {'key': 'value1'}}
        data2 = {'API Name': 'api-2', 'Properties': {'key': 'value2'}}

        model1 = APIModel(data1)
        model2 = APIModel(data2)

        assert model1.api_name != model2.api_name
        assert model1.properties != model2.properties
        assert model1.data is not model2.data
