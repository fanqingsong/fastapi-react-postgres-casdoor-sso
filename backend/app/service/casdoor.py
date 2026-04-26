"""Casdoor service module."""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from simber import Logger
from casdoor import CasdoorSDK

LOG_FORMAT = "{levelname} [{filename}:{lineno}]:"
logger = Logger(__name__, log_path="/logs/api.log")
logger.update_format(LOG_FORMAT)

security = HTTPBearer()

# Global Casdoor SDK instance
_casdoor_sdk = None

def get_casdoor_sdk():
    """Get or initialize Casdoor SDK using the correct CasdoorSDK class."""
    global _casdoor_sdk
    if _casdoor_sdk is None:
        endpoint = os.environ.get("CASDOOR_ENDPOINT", "http://casdoor:8000")
        client_id = os.environ.get("CASDOOR_CLIENT_ID", "")
        client_secret = os.environ.get("CASDOOR_CLIENT_SECRET", "")
        organization = os.environ.get("CASDOOR_ORGANIZATION", "admin")
        application = os.environ.get("CASDOOR_APPLICATION", "app-example")
        certificate = os.environ.get("CASDOOR_CERTIFICATE", "")

        if not client_id or not client_secret:
            logger.error("CASDOOR_CLIENT_ID and CASDOOR_CLIENT_SECRET must be set")
            raise HTTPException(status_code=500, detail="Casdoor configuration missing")

        _casdoor_sdk = CasdoorSDK(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            certificate=certificate,
            org_name=organization,
            application_name=application
        )

    return _casdoor_sdk


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token using Casdoor SDK.

    Args:
        token: The JWT token to verify

    Returns:
        The parsed token payload if valid, None otherwise
    """
    try:
        sdk = get_casdoor_sdk()
        payload = sdk.parse_jwt_token(token)
        logger.info(f"Token verified successfully for user")
        return payload
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate a user with username and password.

    Args:
        username: The username
        password: The password

    Returns:
        Token response with access_token and refresh_token if successful, None otherwise
    """
    try:
        sdk = get_casdoor_sdk()
        token_response = sdk.get_oauth_token(
            code="",
            username=username,
            password=password,
            grant_type="password"
        )
        logger.info(f"User authenticated successfully: {username}")
        return token_response
    except Exception as e:
        logger.error(f"Authentication failed for user {username}: {str(e)}")
        return None


def get_user_info(user_id: str) -> Optional[dict]:
    """Get user information from Casdoor.

    Args:
        user_id: The user ID to fetch

    Returns:
        User information dictionary if found, None otherwise
    """
    try:
        sdk = get_casdoor_sdk()
        user_info = sdk.get_user(user_id)
        logger.info(f"User info retrieved for user_id: {user_id}")
        return user_info
    except Exception as e:
        logger.error(f"Failed to get user info for {user_id}: {str(e)}")
        return None


def refresh_token(refresh_token: str) -> Optional[dict]:
    """Refresh an access token using a refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        New token response with access_token and refresh_token if successful, None otherwise
    """
    try:
        sdk = get_casdoor_sdk()
        new_tokens = sdk.refresh_token_request(
            refresh_token=refresh_token,
            scope=""
        )
        logger.info("Token refreshed successfully")
        return new_tokens
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        return None


def logout() -> bool:
    """Logout user (Casdoor doesn't have explicit logout, tokens are stateless).

    Returns:
        True (logout is handled client-side by discarding tokens)
    """
    logger.info("User logout requested")
    # Casdoor uses stateless JWT tokens, so logout is handled client-side
    # by simply discarding the tokens
    return True
