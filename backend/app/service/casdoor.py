"""Casdoor service module."""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from simber import Logger
import casdoor

LOG_FORMAT = "{levelname} [{filename}:{lineno}]:"
logger = Logger(__name__, log_path="/logs/api.log")
logger.update_format(LOG_FORMAT)

security = HTTPBearer()

# Global Casdoor client instance
_casdoor_client = None

def get_casdoor_client():
    """Get or initialize Casdoor client."""
    global _casdoor_client
    if _casdoor_client is None:
        endpoint = os.environ.get("CASDOOR_ENDPOINT", "http://casdoor:8000")
        client_id = os.environ.get("CASDOOR_CLIENT_ID", "")
        client_secret = os.environ.get("CASDOOR_CLIENT_SECRET", "")
        organization = os.environ.get("CASDOOR_ORGANIZATION", "admin")
        application = os.environ.get("CASDOOR_APPLICATION", "app-example")

        if not client_id or not client_secret:
            logger.error("CASDOOR_CLIENT_ID and CASDOOR_CLIENT_SECRET must be set")
            raise HTTPException(status_code=500, detail="Casdoor configuration missing")

        _casdoor_client = casdoor.Client(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            organization=organization,
            application=application
        )

    return _casdoor_client
