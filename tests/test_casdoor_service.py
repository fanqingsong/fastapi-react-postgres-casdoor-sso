"""Tests for Casdoor service module."""
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
        from app.service.casdoor import get_casdoor_sdk
        sdk = get_casdoor_sdk()
        assert sdk is not None
        assert sdk.endpoint == 'http://localhost:8000'


def test_verify_token():
    """Test token verification using parse_jwt_token."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock the parse_jwt_token response
        mock_sdk.parse_jwt_token.return_value = {
            'user': 'testuser',
            'exp': 1234567890
        }

        from app.service.casdoor import verify_token
        result = verify_token('valid_token')

        assert result is not None
        assert result['user'] == 'testuser'
        mock_sdk.parse_jwt_token.assert_called_once_with('valid_token')


def test_verify_token_invalid():
    """Test token verification with invalid token."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock parse_jwt_token to return None for invalid token
        mock_sdk.parse_jwt_token.return_value = None

        from app.service.casdoor import verify_token
        result = verify_token('invalid_token')

        assert result is None
        mock_sdk.parse_jwt_token.assert_called_once_with('invalid_token')


def test_authenticate_user():
    """Test user authentication using get_oauth_token."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock the get_oauth_token response
        mock_sdk.get_oauth_token.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer'
        }

        from app.service.casdoor import authenticate_user
        result = authenticate_user('testuser', 'testpass')

        assert result is not None
        assert result['access_token'] == 'test_access_token'
        mock_sdk.get_oauth_token.assert_called_once_with(
            '', 'testuser', 'testpass', 'password'
        )


def test_authenticate_user_failure():
    """Test user authentication with invalid credentials."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock get_oauth_token to return None for invalid credentials
        mock_sdk.get_oauth_token.return_value = None

        from app.service.casdoor import authenticate_user
        result = authenticate_user('wronguser', 'wrongpass')

        assert result is None
        mock_sdk.get_oauth_token.assert_called_once_with(
            '', 'wronguser', 'wrongpass', 'password'
        )


def test_get_user_info():
    """Test getting user information."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock the get_user response
        mock_sdk.get_user.return_value = {
            'id': 'test_user_id',
            'name': 'Test User',
            'email': 'test@example.com'
        }

        from app.service.casdoor import get_user_info
        result = get_user_info('test_user_id')

        assert result is not None
        assert result['name'] == 'Test User'
        mock_sdk.get_user.assert_called_once_with('test_user_id')


def test_refresh_token():
    """Test token refresh."""
    with patch('app.service.casdoor.get_casdoor_sdk') as mock_get_sdk:
        mock_sdk = MagicMock()
        mock_get_sdk.return_value = mock_sdk

        # Mock the refresh_token_request response
        mock_sdk.refresh_token_request.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }

        from app.service.casdoor import refresh_token
        result = refresh_token('old_refresh_token')

        assert result is not None
        assert result['access_token'] == 'new_access_token'
        mock_sdk.refresh_token_request.assert_called_once_with(
            'old_refresh_token', ''
        )


def test_logout():
    """Test logout functionality."""
    from app.service.casdoor import logout
    result = logout()
    assert result is True
