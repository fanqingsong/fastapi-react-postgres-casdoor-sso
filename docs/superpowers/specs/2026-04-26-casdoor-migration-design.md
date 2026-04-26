# Keycloak to Casdoor Migration Design

**Date:** 2026-04-26
**Author:** Claude Sonnet
**Status:** Approved

## Overview

Migrate the FastAPI + React + PostgreSQL application from Keycloak SSO to Casdoor SSO while maintaining all current functionality. This is a complete replacement migration that includes user data migration.

## Architecture

### Current Architecture
```
User → Frontend → Backend (Keycloak) → Keycloak Server → User authenticated
```

### New Architecture
```
User → Frontend → Backend (Casdoor) → Casdoor Server → User authenticated
```

### Key Components
- **Casdoor Server** (Docker container): Replaces Keycloak, provides OIDC endpoints
- **Backend Service**: Modified to use Casdoor Python SDK instead of python-keycloak
- **Frontend**: Minimal changes (auth URLs and callback handling)
- **Database**: PostgreSQL for app data, separate database for Casdoor
- **User Migration**: Script to export Keycloak users and import to Casdoor

## Backend Changes

### Dependencies
- **Remove:** `python-keycloak`
- **Add:** `casdoor-python-sdk`

### File Modifications

#### 1. `backend/app/service/keycloak.py` → `backend/app/service/casdoor.py`

Replace KeycloakOpenID with Casdoor SDK while maintaining same function signatures:

- `verify_token()` - Verify JWT tokens using Casdoor's public key
- `authenticate_user()` - Password grant authentication via Casdoor API
- `get_user_info()` - Retrieve user information from Casdoor
- `refresh_token()` - Refresh access tokens
- `logout()` - User logout and session termination

JWT verification logic will be adapted for Casdoor's token format (similar structure to Keycloak).

#### 2. `backend/app/router/auth.py`

- Import `casdoor` instead of `keycloak`
- Maintain all existing OIDC endpoints:
  - `GET /api/auth/oidc/login` - Get OIDC authorization URL
  - `GET /api/auth/oidc/callback` - Handle OIDC callback
  - `GET /api/auth/oidc/user` - Get current user info
  - `POST /api/auth/token` - Password grant login
  - `POST /api/auth/refresh` - Refresh tokens
  - `POST /api/auth/logout` - Logout

#### 3. `backend/app/main.py`

- Update OIDC configuration (client_id, redirect_uri, endpoint URLs)
- Initialize Casdoor SDK with environment variables
- Configure Casdoor callback URL

### Environment Variables

**Remove:**
```bash
KEYCLOAK_SERVER_URL
KEYCLOAK_REALM_NAME
KEYCLOAK_CLIENT_ID
KEYCLOAK_CLIENT_SECRET_KEY
KEYCLOAK_ADMIN_CLIENT_SECRET
```

**Add:**
```bash
CASDOOR_ENDPOINT=http://casdoor:8000
CASDOOR_CLIENT_ID=<your-client-id>
CASDOOR_CLIENT_SECRET=<your-client-secret>
CASDOOR_ORGANIZATION=<your-org-name>
CASDOOR_APPLICATION=<your-app-name>
```

Apply same changes to `backend2/`.

## Frontend Changes

### Minimal Changes Required

#### 1. `frontend/app/src/utils/Auth.ts` (and `frontend2/app/src/utils/Auth.ts`)

- No structural changes needed
- OIDC flow remains identical
- Backend API endpoints unchanged
- Token storage and validation logic stays the same

#### 2. `frontend/app/src/components/public/OIDCCallback.tsx` (and `frontend2/`)

- No changes needed
- Callback handling is provider-agnostic
- Same code/state/parameter parsing
- Same error handling flow

#### 3. `frontend/app/src/components/public/OIDCLogin.tsx` (and `frontend2/`)

- Button text: "Login with SSO (Casdoor)" instead of "Login with SSO (OIDC)"
- Optional: Add Casdoor logo

### User Experience

- Same login flow: click button → redirect to Casdoor → callback → authenticated
- Same token management (access token, refresh token)
- Same session handling
- Casdoor login page instead of Keycloak login page

## Infrastructure Changes

### Docker Compose Modifications

#### Remove Services
- `keycloak` container
- `keycloak_postgres` container
- Keycloak volumes and dependencies

#### Add Services

**Casdoor Container:**
```yaml
casdoor:
  container_name: fastapi_sso_casdoor
  image: casbin/casdoor:latest
  environment:
    RUNNING_IN_DOCKER: "true"
    DRIVER: postgres
    SQL_CONNECTION_STRING: "postgres://casdoor:casdoor_password@casdoor_postgres:5432/casdoor"
  ports:
    - 8000:8000
  depends_on:
    casdoor_postgres:
      condition: service_healthy
  restart: unless-stopped
  volumes:
    - ./casdoor/conf:/conf
```

**Casdoor PostgreSQL:**
```yaml
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
  restart: unless-stopped
```

#### Update Existing Services
- `nginx`: Remove Keycloak proxy, add Casdoor proxy if needed
- `backend` and `backend2`: Depend on `casdoor` instead of `keycloak`

## User Migration Strategy

### Migration Script: `scripts/migrate_users_keycloak_to_casdoor.py`

#### Migration Steps

1. **Export from Keycloak:**
   - Connect to Keycloak admin API
   - Export users: username, email, created_at, attributes
   - Export realm roles and client roles
   - Save to temporary JSON file

2. **Transform Data:**
   - Map Keycloak user structure to Casdoor format
   - Convert roles to Casdoor permissions
   - Generate random passwords (users reset on first login)

3. **Import to Casdoor:**
   - Use Casdoor Python SDK admin API
   - Create users in Casdoor organization
   - Assign roles/permissions
   - Generate migration report

#### Script Features
- Dry-run mode (preview changes without executing)
- Batch processing (handle large user counts)
- Error handling and rollback capability
- Detailed logging and reporting
- Validation after import

#### First Login Experience
- Users receive "password reset required" notification
- Or implement "forgot password" flow on first login
- Maintains security while providing smooth transition

#### Rollback Plan
- Keep Keycloak running in parallel initially (separate port)
- If issues occur, switch back via environment variable
- Full backup of both databases before migration

## Testing Strategy

### Phase 1: Unit Tests
- Test Casdoor service layer functions
- Mock Casdoor SDK responses
- Verify token parsing and validation
- Test error handling

### Phase 2: Integration Tests
- Test backend against real Casdoor container
- Verify OIDC flow: login → callback → token
- Test password grant flow
- Test token refresh and logout
- Verify permission checking

### Phase 3: Frontend Tests
- Test login component with Casdoor
- Test callback handling
- Test token storage and retrieval
- Test authenticated API calls

### Phase 4: End-to-End Tests
- Full user journey: login → access protected resource → logout
- Test both password and OIDC flows
- Test session management
- Test error scenarios (invalid credentials, expired tokens)

### Phase 5: Migration Testing
- Test user migration script with sample data
- Verify imported users can login
- Test permissions and roles transfer correctly
- Performance test with large user counts

### Phase 6: Production Readiness
- Load testing (concurrent users)
- Security testing (token validation, CSRF protection)
- Failover testing (Casdoor restart, network issues)
- Monitoring and logging validation

## Implementation Order

1. Setup Casdoor infrastructure (Docker containers)
2. Implement backend Casdoor service layer
3. Update backend authentication routes
4. Update frontend (minimal changes)
5. Create and test user migration script
6. Execute migration in test environment
7. Execute full testing suite
8. Production deployment

## Success Criteria

- All existing authentication flows work with Casdoor
- All existing users can login after migration
- Token validation and refresh work correctly
- Frontend user experience remains the same
- Performance comparable to Keycloak setup
- No security vulnerabilities introduced

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Token format differences | Thorough testing of JWT validation |
| User migration failures | Dry-run mode, rollback plan |
| Performance degradation | Load testing before production |
| Frontend compatibility | Minimal changes, same OIDC flow |
| Configuration errors | Detailed documentation, validation scripts |
