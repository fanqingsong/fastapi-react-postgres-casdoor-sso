# Casdoor Setup Guide

This guide provides quick setup instructions for Casdoor SSO integration with FastAPI, React, and PostgreSQL.

## Prerequisites

- Docker and Docker Compose installed
- Basic knowledge of OIDC/OAuth2 concepts

## Quick Start

### 1. Environment Configuration

Create a `.env` file in the project root based on `.env.example`:

```bash
# Casdoor Configuration
CASDOOR_ENDPOINT=http://casdoor:8000
CASDOOR_CLIENT_ID=fastapi-client
CASDOOR_CLIENT_SECRET=your-client-secret-here
CASDOOR_ORGANIZATION=admin
CASDOOR_APPLICATION=app-example
CASDOOR_CERTIFICATE=

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fastapi_db

# Backend Configuration
BACKEND_HOST=backend
BACKEND_PORT=8000

# Frontend Configuration
FRONTEND_HOST=frontend
FRONTEND_PORT=3000
```

### 2. Start Casdoor Service

```bash
docker-compose up -d casdoor
```

Wait for Casdoor to initialize (approximately 30 seconds).

### 3. Initialize Casdoor

Run the initialization script to create the organization and application:

```bash
bash casdoor/init.sh
```

This script will:
- Create an admin organization
- Create an application with OIDC enabled
- Display the client secret (copy this to your `.env` file)

### 4. Access Casdoor Console

Open your browser and navigate to: http://localhost:8000

**Default credentials:**
- Username: `admin`
- Password: `123` (change this immediately after first login)

### 5. Configure Application

In the Casdoor console:

1. Go to **Applications** → Select your application
2. Edit the application settings:
   - **Redirect URIs**: Add `http://localhost/oidc/callback`
   - **Grant Types**: Enable `Authorization Code` and `Password`
   - **Scopes**: Add `openid`, `email`, `profile`
3. Save the configuration
4. Copy the **Client Secret** from the application details
5. Update `CASDOOR_CLIENT_SECRET` in your `.env` file

### 6. Start All Services

```bash
docker-compose up -d
```

This starts:
- **Casdoor**: SSO authentication service (port 8000)
- **Backend**: FastAPI server (port 8000 internally)
- **Frontend**: React application (port 3000)
- **PostgreSQL**: Database (port 5432)

### 7. Test the Integration

1. Open http://localhost in your browser
2. You should see the login page with two options:
   - **Login with Password**: Direct username/password authentication
   - **Login with SSO (OIDC)**: Redirect to Casdoor login page

## User Migration from Keycloak

If you're migrating from Keycloak to Casdoor, use the provided migration script:

```bash
# Dry run (test without making changes)
python scripts/migrate_users_keycloak_to_casdoor.py --dry-run

# Execute migration
python scripts/migrate_users_keycloak_to_casdoor.py --execute
```

The script will:
- Export users from Keycloak
- Transform user data to Casdoor format
- Import users to Casdoor
- Generate a detailed migration report

## Configuration Options

### Organization Structure

Casdoor uses a hierarchical structure:
- **Organization**: Top-level container (e.g., `admin`, `company-name`)
- **Application**: OIDC application within an organization
- **Users**: User accounts belong to organizations

### User Attributes

Casdoor supports the following user attributes:
- `name`: Username (unique)
- `displayName`: Full name
- `email`: Email address
- `phone`: Phone number
- `avatar`: Profile picture URL
- `address`: Address information
- `affiliation`: Organization affiliation
- `tag`: User tags
- `homepage`: Personal website
- `bio`: Biography
- `is_admin`: Admin privileges

### Token Management

Casdoor provides JWT tokens with the following grants:
- **Authorization Code**: For SSO flow
- **Password**: For direct authentication
- **Refresh Token**: For token renewal
- **Client Credentials**: For service-to-service communication

## Security Best Practices

1. **Change Default Password**: Immediately change the default admin password
2. **Use HTTPS**: Enable HTTPS in production
3. **Secure Client Secret**: Use strong, randomly generated client secrets
4. **Limit Redirect URIs**: Only whitelist necessary redirect URLs
5. **Enable 2FA**: Enable two-factor authentication for admin accounts
6. **Regular Updates**: Keep Casdoor updated to the latest version
7. **Backup Data**: Regular backup of Casdoor database

## Troubleshooting

### Casdoor Service Not Starting

```bash
# Check Casdoor logs
docker-compose logs casdoor

# Restart Casdoor
docker-compose restart casdoor
```

### Authentication Failures

1. Verify environment variables are set correctly
2. Check Casdoor application configuration
3. Ensure redirect URIs match exactly
4. Verify client secret is correct

### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Frontend Not Connecting to Backend

1. Check CORS configuration in `backend/app/main.py`
2. Verify backend is running: `docker-compose ps backend`
3. Check network connectivity: `docker-compose logs backend`

## Advanced Configuration

### Custom Authentication Flow

For custom authentication requirements, modify the Casdoor service in `backend/app/service/casdoor.py`:

```python
from app.service.casdoor import authenticate_user, get_user_info

# Custom authentication
def custom_auth(username: str, password: str):
    result = authenticate_user(username, password)
    if result:
        user_info = get_user_info(result['access_token'])
        # Add custom logic here
    return result
```

### Multi-Organization Setup

To support multiple organizations:

1. Create organizations in Casdoor console
2. Update environment variables for each organization
3. Modify the authentication flow to handle organization selection

### Custom User Attributes

Add custom user attributes by extending the user model:

```python
# In migration script or user creation
casdoor_user = {
    'name': 'john.doe',
    'displayName': 'John Doe',
    'email': 'john@example.com',
    'custom_attribute': 'custom_value'  # Add custom fields
}
```

## Production Deployment

For production deployment:

1. **Use HTTPS**: Configure SSL certificates
2. **External Database**: Use managed PostgreSQL service
3. **Load Balancing**: Deploy multiple Casdoor instances behind a load balancer
4. **Monitoring**: Set up logging and monitoring
5. **Backup Strategy**: Implement automated backups
6. **Disaster Recovery**: Plan for failover scenarios

## Resources

- [Casdoor Documentation](https://casdoor.org/docs/intro)
- [Casdoor GitHub](https://github.com/casdoor/casdoor)
- [OIDC Specifications](https://openid.net/connect/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

## Support

For issues and questions:
- Check the [Casdoor FAQ](https://casdoor.org/docs/faqs)
- Review [Casdoor GitHub Issues](https://github.com/casdoor/casdoor/issues)
- Consult the [OIDC Integration Guide](./OIDC_INTEGRATION.md)
