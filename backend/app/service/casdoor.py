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
