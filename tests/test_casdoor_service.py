import os
import pytest
from unittest.mock import patch, MagicMock

def test_casdoor_sdk_initialization():
    """Test that Casdoor SDK initializes correctly with environment variables."""
    with patch.dict(os.environ, {
        'CASDOOR_ENDPOINT': 'http://localhost:8000',
        'CASDOOR_CLIENT_ID': 'test-client',
        'CASDOOR_CLIENT_SECRET': 'test-secret',
        'CASDOOR_ORGANIZATION': 'test-org',
        'CASDOOR_APPLICATION': 'test-app'
    }):
        from app.service.casdoor import get_casdoor_client
        client = get_casdoor_client()
        assert client is not None
        assert client.endpoint == 'http://localhost:8000'
