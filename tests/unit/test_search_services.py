"""Unit tests for search service."""

import pytest
from unittest.mock import Mock, MagicMock
from app.services.search_service import SearchService


class TestSearchService:
    """Test search service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.search_service = SearchService(self.mock_db)
    
    def test_search_simple_query(self):
        """Test simple text search."""
        # Mock database response
        self.mock_db.find_documents.return_value = [
            {"APIName": "UserAPI", "Platform": "AWS"}
        ]
        self.mock_db.count_documents.return_value = 1
        
        results, count, metadata = self.search_service.search("user")
        
        assert len(results) == 1
        assert count == 1
        assert metadata['total_results'] == 1
        assert metadata['query'] == 'user'
        
        # Verify database was called
        self.mock_db.find_documents.assert_called_once()
        self.mock_db.count_documents.assert_called_once()
    
    def test_search_property_query(self):
        """Test property-based search."""
        self.mock_db.find_documents.return_value = [
            {"APIName": "UserAPI", "Platform": "AWS"}
        ]
        self.mock_db.count_documents.return_value = 1
        
        results, count, metadata = self.search_service.search('Platform=AWS')
        
        assert len(results) == 1
        assert count == 1
        
        # Check that MongoDB query was built correctly
        call_args = self.mock_db.find_documents.call_args[1]
        query = call_args['query']
        assert 'Platform' in str(query) or '$or' in query
    
    def test_search_with_pagination(self):
        """Test search with pagination."""
        self.mock_db.find_documents.return_value = []
        self.mock_db.count_documents.return_value = 100
        
        results, count, metadata = self.search_service.search(
            "test", 
            page=3, 
            page_size=20
        )
        
        assert metadata['page'] == 3
        assert metadata['page_size'] == 20
        assert metadata['total_pages'] == 5
        
        # Check skip calculation
        call_args = self.mock_db.find_documents.call_args[1]
        assert call_args['skip'] == 40  # (3-1) * 20
        assert call_args['limit'] == 20
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        self.mock_db.find_documents.return_value = []
        self.mock_db.count_documents.return_value = 0
        
        results, count, metadata = self.search_service.search("")
        
        # Should return empty query to MongoDB
        call_args = self.mock_db.find_documents.call_args[1]
        assert call_args['query'] == {}
    
    def test_search_error_handling(self):
        """Test search error handling."""
        self.mock_db.find_documents.side_effect = Exception("Database error")
        
        results, count, metadata = self.search_service.search("test")
        
        assert results == []
        assert count == 0
        assert 'error' in metadata
    
    def test_get_suggestions(self):
        """Test autocomplete suggestions."""
        self.mock_db.get_distinct_values.return_value = [
            "AWS", "Azure", "GCP", "Alibaba"
        ]
        
        suggestions = self.search_service.get_suggestions("Platform", "A")
        
        assert len(suggestions) == 3  # AWS, Azure, Alibaba
        assert "AWS" in suggestions
        assert "Azure" in suggestions
        assert "Alibaba" in suggestions
        assert "GCP" not in suggestions