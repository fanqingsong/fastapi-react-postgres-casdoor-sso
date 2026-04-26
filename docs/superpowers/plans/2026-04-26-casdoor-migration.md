# Keycloak to Casdoor Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Keycloak SSO with Casdoor SSO while maintaining all current authentication functionality and migrating existing users.

**Architecture:** Replace Keycloak container and python-keycloak library with Casdoor container and casdoor-python-sdk. Maintain same OIDC flow, keep frontend changes minimal, implement user migration script.

**Tech Stack:** Casbin Casdoor, casdoor-python-sdk, FastAPI, React TypeScript, Docker Compose, PostgreSQL

---

## Task 1: Setup Casdoor Infrastructure

**Files:**
- Create: `casdoor/conf/app.conf`
- Modify: `docker-compose.yaml`

- [ ] **Step 1: Create Casdoor configuration directory**

```bash
mkdir -p casdoor/conf
```

- [ ] **Step 2: Create Casdoor app.conf file**

Create file: `casdoor/conf/app.conf`

```ini
appname = Casdoor-OAuth2-Server
httpport = 8000
driver = postgres
dataSource = postgres://casdoor:casdoor_password@casdoor_postgres:5432/casdoor?sslmode=disable
dbName = casdoor
```

- [ ] **Step 3: Update docker-compose.yaml - Add Casdoor services**

Modify: `docker-compose.yaml`

Add these services after the `postgres` service:

```yaml
  casdoor:
    container_name: fastapi_sso_casdoor
    image: casbin/casdoor:latest
    environment:
      RUNNING_IN_DOCKER: "true"
    ports:
      - 8000:8000
    depends_on:
      casdoor_postgres:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./casdoor/conf:/conf
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  casdoor_postgres:
    container_name: fastapi_sso_casdoor_postgres
    image: postgres:latest
    environment:
      POSTGRES_DB: casdoor
      POSTGRES_USER: casdoor
      POSTGRES_PASSWORD: casdoor_password
    volumes:
      - casdoor_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U casdoor"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
```

Add to volumes section:

```yaml
  casdoor_postgres_data:
```

- [ ] **Step 4: Update docker-compose.yaml - Modify backend dependencies**

Modify: `docker-compose.yaml`

Update the `backend` service dependencies:

```yaml
  backend:
    depends_on:
      postgres:
        condition: service_healthy
      casdoor:
        condition: service_healthy
```

Update the `backend2` service dependencies:

```yaml
  backend2:
    depends_on:
      postgres:
        condition: service_healthy
      casdoor:
        condition: service_healthy
```

- [ ] **Step 5: Update docker-compose.yaml - Update nginx dependencies**

Modify: `docker-compose.yaml`

Update the `nginx` service dependencies:

```yaml
  nginx:
    depends_on:
      frontend:
        condition: service_healthy
      frontend2:
        condition: service_healthy
      backend:
        condition: service_healthy
      backend2:
        condition: service_healthy
      casdoor:
        condition: service_started
```

- [ ] **Step 6: Update docker-compose.yaml - Remove Keycloak services**

Modify: `docker-compose.yaml`

Remove the entire `keycloak` service definition and the entire `keycloak_postgres` service definition.

Remove `keycloak_postgres_data` from the volumes section.

- [ ] **Step 7: Verify docker-compose.yaml syntax**

```bash
docker-compose config
```

Expected: No syntax errors, configuration outputs successfully

- [ ] **Step 8: Commit infrastructure changes**

```bash
git add docker-compose.yaml casdoor/conf/app.conf
git commit -m "feat: add Casdoor infrastructure, remove Keycloak

- Add Casdoor container and PostgreSQL database
- Remove Keycloak and Keycloak PostgreSQL services
- Update service dependencies to use Casdoor
- Create Casdoor configuration file

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Update Backend Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend2/requirements.txt`

- [ ] **Step 1: Update backend requirements.txt**

Modify: `backend/requirements.txt`

Remove line:
```
python-keycloak==3.9.0
```

Add line:
```
casdoor==0.2.0
```

- [ ] **Step 2: Update backend2 requirements.txt**

Modify: `backend2/requirements.txt`

Remove line:
```
python-keycloak==3.9.0
```

Add line:
```
casdoor==0.2.0
```

- [ ] **Step 3: Commit dependency changes**

```bash
git add backend/requirements.txt backend2/requirements.txt
git commit -m "chore: replace python-keycloak with casdoor SDK

Remove python-keycloak dependency and add casdoor Python SDK
for both backend and backend2 services.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Implement Casdoor Service Layer (Part 1)

**Files:**
- Create: `backend/app/service/casdoor.py`
- Test: `tests/test_casdoor_service.py`

- [ ] **Step 1: Write failing test for Casdoor initialization**

Create file: `tests/test_casdoor_service.py`

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_casdoor_sdk_initialization -v
```

Expected: FAIL with "module 'app.service.casdoor' not found"

- [ ] **Step 3: Create Casdoor service file with basic structure**

Create file: `backend/app/service/casdoor.py`

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_casdoor_sdk_initialization -v
```

Expected: PASS

---

## Task 4: Implement Casdoor Service Layer (Part 2 - Token Verification)

**Files:**
- Modify: `backend/app/service/casdoor.py`
- Test: `tests/test_casdoor_service.py`

- [ ] **Step 1: Write failing test for token verification**

Add to `tests/test_casdoor_service.py`:

```python
def test_verify_token_valid():
    """Test token verification with valid token."""
    from app.service.casdoor import verify_token
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid-token"

    with patch('app.service.casdoor.get_casdoor_client') as mock_client:
        mock_casdoor = MagicMock()
        mock_casdoor.ParseJwtToken.return_value = {"sub": "user123", "exp": 9999999999}
        mock_client.return_value = mock_casdoor

        result = verify_token(mock_credentials)
        assert result["sub"] == "user123"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_verify_token_valid -v
```

Expected: FAIL with "function 'verify_token' not defined"

- [ ] **Step 3: Implement token verification function**

Add to `backend/app/service/casdoor.py`:

```python
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return user info."""
    try:
        client = get_casdoor_client()
        token = credentials.credentials

        # Parse and verify JWT token using Casdoor
        user_info = client.ParseJwtToken(token)

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_info
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_verify_token_valid -v
```

Expected: PASS

---

## Task 5: Implement Casdoor Service Layer (Part 3 - User Authentication)

**Files:**
- Modify: `backend/app/service/casdoor.py`
- Test: `tests/test_casdoor_service.py`

- [ ] **Step 1: Write failing test for user authentication**

Add to `tests/test_casdoor_service.py`:

```python
@pytest.mark.asyncio
async def test_authenticate_user_success():
    """Test user authentication with valid credentials."""
    from app.service.casdoor import authenticate_user

    with patch('app.service.casdoor.get_casdoor_client') as mock_client:
        mock_casdoor = MagicMock()
        mock_casdoor.GetOAuthToken.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_client.return_value = mock_casdoor

        result = await authenticate_user("testuser", "password123")
        assert result["access_token"] == "test-access-token"
        assert "refresh_token" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_authenticate_user_success -v
```

Expected: FAIL with "function 'authenticate_user' not defined"

- [ ] **Step 3: Implement user authentication function**

Add to `backend/app/service/casdoor.py`:

```python
async def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user with Casdoor using password grant."""
    try:
        client = get_casdoor_client()

        # Get OAuth token using resource owner password credentials
        token_data = client.GetOAuthToken(
            username=username,
            password=password,
            grant_type="password"
        )

        if not token_data or "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_authenticate_user_success -v
```

Expected: PASS

---

## Task 6: Implement Casdoor Service Layer (Part 4 - Remaining Functions)

**Files:**
- Modify: `backend/app/service/casdoor.py`
- Test: `tests/test_casdoor_service.py`

- [ ] **Step 1: Write failing test for get_user_info**

Add to `tests/test_casdoor_service.py`:

```python
def test_get_user_info():
    """Test getting user information."""
    from app.service.casdoor import get_user_info

    with patch('app.service.casdoor.get_casdoor_client') as mock_client:
        mock_casdoor = MagicMock()
        mock_casdoor.GetUser.return_value = {
            "id": "user123",
            "name": "Test User",
            "email": "test@example.com"
        }
        mock_client.return_value = mock_casdoor

        result = get_user_info("user123")
        assert result["id"] == "user123"
        assert result["email"] == "test@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_get_user_info -v
```

Expected: FAIL with "function 'get_user_info' not defined"

- [ ] **Step 3: Implement get_user_info function**

Add to `backend/app/service/casdoor.py`:

```python
def get_user_info(user_id: str) -> dict:
    """Get user information from Casdoor."""
    try:
        client = get_casdoor_client()
        user_info = client.GetUser(user_id)
        return user_info
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=400, detail="Failed to get user info")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_get_user_info -v
```

Expected: PASS

- [ ] **Step 5: Write failing test for refresh_token**

Add to `tests/test_casdoor_service.py`:

```python
def test_refresh_token():
    """Test token refresh."""
    from app.service.casdoor import refresh_token

    with patch('app.service.casdoor.get_casdoor_client') as mock_client:
        mock_casdoor = MagicMock()
        mock_casdoor.RefreshToken.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        }
        mock_client.return_value = mock_casdoor

        result = refresh_token("old-refresh-token")
        assert result["access_token"] == "new-access-token"
```

- [ ] **Step 6: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_refresh_token -v
```

Expected: FAIL with "function 'refresh_token' not defined"

- [ ] **Step 7: Implement refresh_token function**

Add to `backend/app/service/casdoor.py`:

```python
def refresh_token(refresh_token: str) -> dict:
    """Refresh access token."""
    try:
        client = get_casdoor_client()
        new_token = client.RefreshToken(refresh_token)

        if not new_token or "access_token" not in new_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token refresh failed"
            )

        return new_token
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        raise HTTPException(status_code=400, detail="Failed to refresh token")
```

- [ ] **Step 8: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_refresh_token -v
```

Expected: PASS

- [ ] **Step 9: Write failing test for logout**

Add to `tests/test_casdoor_service.py`:

```python
def test_logout():
    """Test user logout."""
    from app.service.casdoor import logout

    with patch('app.service.casdoor.get_casdoor_client') as mock_client:
        mock_casdoor = MagicMock()
        mock_casdoor.DeleteUserTokens.return_value = True
        mock_client.return_value = mock_casdoor

        result = logout("user123", "refresh-token")
        assert result is True
```

- [ ] **Step 10: Run test to verify it fails**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_logout -v
```

Expected: FAIL with "function 'logout' not defined"

- [ ] **Step 11: Implement logout function**

Add to `backend/app/service/casdoor.py`:

```python
def logout(user_id: str, refresh_token: str) -> bool:
    """Logout user and delete tokens."""
    try:
        client = get_casdoor_client()
        client.DeleteUserTokens(user_id, refresh_token)
        return True
    except Exception as e:
        logger.error(f"Failed to logout: {e}")
        raise HTTPException(status_code=400, detail="Failed to logout")
```

- [ ] **Step 12: Run test to verify it passes**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py::test_logout -v
```

Expected: PASS

- [ ] **Step 13: Run all tests and ensure they pass**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py -v
```

Expected: All tests PASS

- [ ] **Step 14: Commit Casdoor service implementation**

```bash
git add backend/app/service/casdoor.py tests/test_casdoor_service.py
git commit -m "feat: implement Casdoor service layer

- Create casdoor.py with all authentication functions
- Implement get_casdoor_client, verify_token, authenticate_user
- Implement get_user_info, refresh_token, logout
- Add comprehensive unit tests with TDD approach

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Replicate Casdoor Service to backend2

**Files:**
- Create: `backend2/app/service/casdoor.py`

- [ ] **Step 1: Copy Casdoor service to backend2**

```bash
cp backend/app/service/casdoor.py backend2/app/service/casdoor.py
```

- [ ] **Step 2: Verify the file was copied correctly**

```bash
diff backend/app/service/casdoor.py backend2/app/service/casdoor.py
```

Expected: No differences

- [ ] **Step 3: Commit backend2 service copy**

```bash
git add backend2/app/service/casdoor.py
git commit -m "feat: add Casdoor service to backend2

Copy casdoor.py from backend to backend2 to maintain
parity between both backend services.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Update Backend Authentication Routes

**Files:**
- Modify: `backend/app/router/auth.py`
- Modify: `backend2/app/router/auth.py`

- [ ] **Step 1: Update backend auth router imports**

Modify: `backend/app/router/auth.py`

Change line 8 from:
```python
from app.service.keycloak import authenticate_user, logout, refresh_token
```

To:
```python
from app.service.casdoor import authenticate_user, logout, refresh_token
```

- [ ] **Step 2: Update backend2 auth router imports**

Modify: `backend2/app/router/auth.py`

Change line 8 from:
```python
from app.service.keycloak import authenticate_user, logout, refresh_token
```

To:
```python
from app.service.casdoor import authenticate_user, logout, refresh_token
```

- [ ] **Step 3: Commit auth router updates**

```bash
git add backend/app/router/auth.py backend2/app/router/auth.py
git commit -m "refactor: update auth routers to use Casdoor service

Replace Keycloak service imports with Casdoor service imports
in both backend and backend2 authentication routers.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Update Backend Main Application Configuration

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend2/app/main.py`

- [ ] **Step 1: Read backend main.py to understand current OIDC configuration**

```bash
cat backend/app/main.py | grep -A 20 -i "oidc\|keycloak"
```

- [ ] **Step 2: Update backend main.py OIDC configuration**

Modify: `backend/app/main.py`

Find the OIDC configuration section and update environment variable names:
- `KEYCLOAK_CLIENT_ID` → `CASDOOR_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET_KEY` → `CASDOOR_CLIENT_SECRET`
- `KEYCLOAK_SERVER_URL` → `CASDOOR_ENDPOINT`
- `KEYCLOAK_REALM_NAME` → `CASDOOR_ORGANIZATION`

- [ ] **Step 3: Update backend2 main.py OIDC configuration**

Modify: `backend2/app/main.py`

Apply the same OIDC configuration updates as backend.

- [ ] **Step 4: Commit main.py updates**

```bash
git add backend/app/main.py backend2/app/main.py
git commit -m "refactor: update OIDC configuration for Casdoor

Replace Keycloak environment variables with Casdoor equivalents
in both backend and backend2 main application files.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Update Environment Variables

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Update .env.example - Remove Keycloak variables**

Modify: `.env.example`

Remove these lines:
```bash
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=
KEYCLOAK_DB_DATABASE=keycloak
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=
KEYCLOAK_SERVER_URL=http://keycloak:8080/
KEYCLOAK_SERVER_URL_CLIENT=http://localhost:8081/
KEYCLOAK_REALM_NAME=master
KEYCLOAK_CLIENT_ID=app
KEYCLOAK_CLIENT_SECRET_KEY=
KEYCLOAK_ADMIN_CLIENT_SECRET=
```

- [ ] **Step 2: Update .env.example - Add Casdoor variables**

Modify: `.env.example`

Add these lines:
```bash
# Casdoor Configuration
CASDOOR_ENDPOINT=http://casdoor:8000
CASDOOR_CLIENT_ID=<your-client-id>
CASDOOR_CLIENT_SECRET=<your-client-secret>
CASDOOR_ORGANIZATION=<your-organization-name>
CASDOOR_APPLICATION=<your-application-name>

# Casdoor Database
CASDOOR_DB_USER=casdoor
CASDOOR_DB_PASSWORD=<your-casdoor-db-password>
CASDOOR_DB_DATABASE=casdoor
```

- [ ] **Step 3: Commit environment variable updates**

```bash
git add .env.example
git commit -m "chore: update environment variables for Casdoor

Remove Keycloak environment variables and add Casdoor-specific
variables to .env.example for configuration reference.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 11: Update Frontend Login Components

**Files:**
- Modify: `frontend/app/src/components/public/OIDCLogin.tsx`
- Modify: `frontend2/app/src/components/public/OIDCLogin.tsx`

- [ ] **Step 1: Update frontend button text**

Modify: `frontend/app/src/components/public/OIDCLogin.tsx`

Find the button text "Login with SSO (OIDC)" and change it to:
```typescript
Login with SSO (Casdoor)
```

- [ ] **Step 2: Update frontend2 button text**

Modify: `frontend2/app/src/components/public/OIDCLogin.tsx`

Find the button text "Login with SSO (OIDC)" and change it to:
```typescript
Login with SSO (Casdoor)
```

- [ ] **Step 3: Commit frontend updates**

```bash
git add frontend/app/src/components/public/OIDCLogin.tsx frontend2/app/src/components/public/OIDCLogin.tsx
git commit -m "refactor: update login button text for Casdoor

Change 'Login with SSO (OIDC)' to 'Login with SSO (Casdoor)'
in both frontend and frontend2 login components.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 12: Create User Migration Script

**Files:**
- Create: `scripts/migrate_users_keycloak_to_casdoor.py`
- Test: `tests/test_migration_script.py`

- [ ] **Step 1: Create scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 2: Create migration script**

Create file: `scripts/migrate_users_keycloak_to_casdoor.py`

```python
#!/usr/bin/env python3
"""User migration script from Keycloak to Casdoor."""
import json
import sys
import argparse
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_keycloak_users(server_url: str, realm_name: str, admin_username: str, admin_password: str) -> List[Dict]:
    """Export users from Keycloak."""
    try:
        from keycloak import KeycloakAdmin
        keycloak_admin = KeycloakAdmin(server_url=server_url, username=admin_username,
                                       password=admin_password, realm_name=realm_name, verify=False)
        users = keycloak_admin.get_users({})
        logger.info(f"Exported {len(users)} users from Keycloak")
        return users
    except Exception as e:
        logger.error(f"Failed to export users from Keycloak: {e}")
        raise

def transform_for_casdoor(keycloak_users: List[Dict]) -> List[Dict]:
    """Transform Keycloak users to Casdoor format."""
    casdoor_users = []
    for kc_user in keycloak_users:
        casdoor_user = {
            "name": kc_user.get("username", ""),
            "displayName": f"{kc_user.get('firstName', '')} {kc_user.get('lastName', '')}".strip(),
            "email": kc_user.get("email", ""),
            "phone": "",
            "address": [],
            "affiliation": "",
            "tag": "",
            "region": "",
            "language": "en",
            "avatar": "",
            "score": 0,
            "ranking": 0,
            "is_admin": False,
            "is_global_admin": False,
            "is_deleted": False,
            "created_time": kc_user.get("createdTimestamp", 0),
            "properties": {}
        }
        casdoor_users.append(casdoor_user)
    logger.info(f"Transformed {len(casdoor_users)} users for Casdoor")
    return casdoor_users

def import_to_casdoor(users: List[Dict], endpoint: str, client_id: str, client_secret: str,
                      organization: str, dry_run: bool = False) -> None:
    """Import users into Casdoor."""
    import casdoor
    try:
        client = casdoor.Client(endpoint=endpoint, client_id=client_id,
                               client_secret=client_secret, organization=organization,
                               application="app-example")
        if dry_run:
            logger.info(f"DRY RUN: Would import {len(users)} users to Casdoor")
            return
        for user in users:
            import secrets
            password = secrets.token_urlsafe(16)
            user["password"] = password
            client.AddUser(user)
            logger.info(f"Imported user: {user['name']}")
        logger.info(f"Successfully imported users to Casdoor")
    except Exception as e:
        logger.error(f"Failed to connect to Casdoor: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Migrate users from Keycloak to Casdoor')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
    parser.add_argument('--keycloak-url', default='http://keycloak:8080', help='Keycloak server URL')
    parser.add_argument('--keycloak-realm', default='master', help='Keycloak realm name')
    parser.add_argument('--keycloak-admin', required=True, help='Keycloak admin username')
    parser.add_argument('--keycloak-password', required=True, help='Keycloak admin password')
    parser.add_argument('--casdoor-endpoint', default='http://casdoor:8000', help='Casdoor endpoint')
    parser.add_argument('--casdoor-client-id', required=True, help='Casdoor client ID')
    parser.add_argument('--casdoor-client-secret', required=True, help='Casdoor client secret')
    parser.add_argument('--casdoor-org', required=True, help='Casdoor organization name')
    parser.add_argument('--output', default='migration_report.json', help='Output file for migration report')
    args = parser.parse_args()

    try:
        keycloak_users = export_keycloak_users(args.keycloak_url, args.keycloak_realm,
                                                args.keycloak_admin, args.keycloak_password)
        casdoor_users = transform_for_casdoor(keycloak_users)
        import_to_casdoor(casdoor_users, args.casdoor_endpoint, args.casdoor_client_id,
                          args.casdoor_client_secret, args.casdoor_org, dry_run=args.dry_run)
        report = {"total_users": len(casdoor_users), "dry_run": args.dry_run,
                  "timestamp": __import__('datetime').datetime.now().isoformat()}
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Migration complete. Report saved to {args.output}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Make script executable**

```bash
chmod +x scripts/migrate_users_keycloak_to_casdoor.py
```

- [ ] **Step 4: Write tests for migration script**

Create file: `tests/test_migration_script.py`

```python
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, 'scripts')

def test_export_users_from_keycloak():
    """Test exporting users from Keycloak."""
    from migrate_users_keycloak_to_casdoor import export_keycloak_users
    with patch('migrate_users_keycloak_to_casdoor.KeycloakOpenID') as mock_keycloak:
        mock_admin = MagicMock()
        mock_admin.get_users.return_value = [{"id": "user1", "username": "testuser"}]
        mock_keycloak.return_value = mock_admin
        users = export_keycloak_users("http://keycloak:8080", "master", "admin", "password")
        assert len(users) == 1

def test_transform_for_casdoor():
    """Test transforming Keycloak users to Casdoor format."""
    from migrate_users_keycloak_to_casdoor import transform_for_casdoor
    keycloak_users = [{"id": "user1", "username": "testuser", "email": "test@example.com",
                       "firstName": "Test", "lastName": "User", "createdTimestamp": 1234567890000}]
    casdoor_users = transform_for_casdoor(keycloak_users)
    assert len(casdoor_users) == 1
    assert casdoor_users[0]["name"] == "testuser"
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_migration_script.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit migration script**

```bash
git add scripts/migrate_users_keycloak_to_casdoor.py tests/test_migration_script.py
git commit -m "feat: add user migration script from Keycloak to Casdoor

Implement migration script with:
- Export users from Keycloak via admin API
- Transform user data to Casdoor format
- Import users to Casdoor via SDK
- Dry-run mode for testing
- Comprehensive error handling and logging

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 13: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `OIDC_INTEGRATION.md`
- Create: `CASDOOR_SETUP.md`

- [ ] **Step 1: Update README.md**

Modify: `README.md`

Replace Keycloak installation section with:

```markdown
## Casdoor Installation

Create a `.env` file based on the `.env.example` file.

> :warning: Don't forget to put values for the password fields

Next step is to launch Casdoor:

```bash
docker-compose up -d casdoor casdoor_postgres
```

Access the Casdoor console: http://localhost:8000
```

- [ ] **Step 2: Update OIDC_INTEGRATION.md**

Modify: `OIDC_INTEGRATION.md`

Replace all Keycloak references with Casdoor equivalents.

- [ ] **Step 3: Create Casdoor setup guide**

Create file: `CASDOOR_SETUP.md`

```markdown
# Casdoor Setup Guide

## Initial Setup

1. Start Casdoor services:
```bash
docker-compose up -d casdoor casdoor_postgres
```

2. Access Casdoor console at http://localhost:8000

3. Login and configure organization/application

## Configure Application

1. Create an organization
2. Create an application with OAuth settings
3. Copy client credentials to .env file
```

- [ ] **Step 4: Commit documentation updates**

```bash
git add README.md OIDC_INTEGRATION.md CASDOOR_SETUP.md
git commit -m "docs: update documentation for Casdoor

Replace Keycloak references with Casdoor in README and
OIDC integration docs. Add new Casdoor setup guide.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 14: Final Cleanup and Verification

**Files:**
- Delete: `backend/app/service/keycloak.py`
- Delete: `backend2/app/service/keycloak.py`

- [ ] **Step 1: Delete old Keycloak service files**

```bash
rm backend/app/service/keycloak.py
rm backend2/app/service/keycloak.py
```

- [ ] **Step 2: Run complete test suite**

```bash
cd backend && python -m pytest ../tests/test_casdoor_service.py -v
cd ../backend2 && python -m pytest ../tests/test_casdoor_service.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Verify docker-compose configuration**

```bash
docker-compose config
```

Expected: Valid YAML, no errors

- [ ] **Step 4: Check for any remaining Keycloak references**

```bash
grep -r "keycloak" --include="*.py" --include="*.ts" --include="*.tsx" backend/ backend2/ frontend/ frontend2/ | grep -v "Binary" | grep -v ".git"
```

Expected: No results (or only in comments/git history)

- [ ] **Step 5: Commit cleanup**

```bash
git add -u
git commit -m "chore: remove Keycloak service files

Delete backend/app/service/keycloak.py and backend2 version
after verifying Casdoor migration is complete and functional.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Verification

### Testing Checklist

- [ ] All unit tests pass
- [ ] Docker Compose configuration is valid
- [ ] Casdoor container starts successfully
- [ ] Backend services connect to Casdoor
- [ ] Frontend login buttons updated
- [ ] Migration script runs in dry-run mode
- [ ] No Keycloak references in active code

### Success Criteria

- ✅ All unit tests pass
- ✅ All services healthy in docker-compose
- ✅ No Keycloak references in code (except docs/git)
- ✅ Migration script created and tested
- ✅ Documentation updated

**Plan Complete:** This implementation plan covers all aspects of migrating from Keycloak to Casdoor SSO with comprehensive TDD approach and verification steps.
