#!/usr/bin/env python3
"""
User Migration Script: Keycloak to Casdoor

This script exports users from Keycloak and imports them into Casdoor.
Supports dry-run mode and generates migration reports.

Requirements:
    pip install python-keycloak casdoor

Usage:
    python migrate_users_keycloak_to_casdoor.py --dry-run
    python migrate_users_keycloak_to_casdoor.py --execute
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Optional
from datetime import datetime
from python_keycloak import KeycloakAdmin
from casdoor import CasdoorSDK

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('user_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def export_keycloak_users(server_url: str, realm: str, admin_user: str, admin_pass: str) -> List[Dict]:
    """
    Export users from Keycloak admin API.

    Args:
        server_url: Keycloak server URL (e.g., http://localhost:8080)
        realm: Keycloak realm name
        admin_user: Keycloak admin username
        admin_pass: Keycloak admin password

    Returns:
        List of Keycloak user dictionaries

    Raises:
        Exception: If export fails
    """
    logger.info(f"Connecting to Keycloak at {server_url}")

    try:
        # Initialize Keycloak admin
        keycloak_admin = KeycloakAdmin(
            server_url=f"{server_url}/auth",
            username=admin_user,
            password=admin_pass,
            realm_name=realm,
            verify=True
        )

        # Get all users
        users = keycloak_admin.get_users({})
        logger.info(f"Exported {len(users)} users from Keycloak realm '{realm}'")

        # Enrich user data with roles and groups
        for user in users:
            user_id = user.get('id')
            # Get user roles
            try:
                user_roles = keycloak_admin.get_user_roles(user_id)
                user['keycloak_roles'] = [role.get('name') for role in user_roles]
            except Exception as e:
                logger.warning(f"Failed to get roles for user {user.get('username')}: {e}")
                user['keycloak_roles'] = []

            # Get user groups
            try:
                user_groups = keycloak_admin.get_user_groups(user_id)
                user['keycloak_groups'] = [group.get('name') for group in user_groups]
            except Exception as e:
                logger.warning(f"Failed to get groups for user {user.get('username')}: {e}")
                user['keycloak_groups'] = []

        return users

    except Exception as e:
        logger.error(f"Failed to export users from Keycloak: {e}")
        raise


def transform_for_casdoor(keycloak_users: List[Dict]) -> List[Dict]:
    """
    Transform Keycloak users to Casdoor format.

    Args:
        keycloak_users: List of Keycloak user dictionaries

    Returns:
        List of Casdoor-formatted user dictionaries
    """
    logger.info("Transforming users to Casdoor format")

    casdoor_users = []
    skipped_users = []

    for kc_user in keycloak_users:
        try:
            # Map Keycloak attributes to Casdoor format
            casdoor_user = {
                'owner': os.environ.get('CASDOOR_ORGANIZATION', 'admin'),
                'name': kc_user.get('username', ''),
                'displayName': kc_user.get('firstName', '') + ' ' + kc_user.get('lastName', ''),
                'email': kc_user.get('email', ''),
                'phone': kc_user.get('attributes', {}).get('phone', [''])[0] if kc_user.get('attributes', {}).get('phone') else '',
                'avatar': kc_user.get('attributes', {}).get('avatar', [''])[0] if kc_user.get('attributes', {}).get('avatar') else '',
                'address': [],
                'affiliation': '',
                'tag': '',
                'homepage': '',
                'bio': '',
                'score': 0,
                'ranking': 0,
                'is_admin': False,
                'is_global_admin': False,
                'is_deleted': False,
                'is forbidden': False,
                'signup_application': os.environ.get('CASDOOR_APPLICATION', 'app-example'),
                'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # Handle enabled/disabled status
            if not kc_user.get('enabled', True):
                casdoor_user['is_deleted'] = True
                logger.info(f"User {kc_user.get('username')} is disabled in Keycloak, marking as deleted")

            # Map roles to Casdoor permissions
            roles = kc_user.get('keycloak_roles', [])
            if 'admin' in roles or 'ADMIN' in roles:
                casdoor_user['is_admin'] = True
                logger.info(f"User {kc_user.get('username')} has admin role")

            # Add metadata for migration tracking
            casdoor_user['keycloak_id'] = kc_user.get('id', '')
            casdoor_user['migration_source'] = 'keycloak'
            casdoor_user['migration_date'] = datetime.now().isoformat()

            # Skip service accounts
            if kc_user.get('serviceAccountClientId'):
                skipped_users.append({
                    'username': kc_user.get('username'),
                    'reason': 'Service account'
                })
                logger.info(f"Skipping service account: {kc_user.get('username')}")
                continue

            # Validate required fields
            if not casdoor_user['name']:
                skipped_users.append({
                    'username': kc_user.get('username'),
                    'reason': 'Missing username'
                })
                logger.warning(f"Skipping user without username: {kc_user.get('email')}")
                continue

            casdoor_users.append(casdoor_user)

        except Exception as e:
            logger.error(f"Failed to transform user {kc_user.get('username')}: {e}")
            skipped_users.append({
                'username': kc_user.get('username', 'unknown'),
                'reason': f'Transformation error: {str(e)}'
            })

    logger.info(f"Successfully transformed {len(casdoor_users)} users")
    logger.info(f"Skipped {len(skipped_users)} users")

    return casdoor_users


def import_to_casdoor(
    users: List[Dict],
    endpoint: str,
    client_id: str,
    client_secret: str,
    org: str,
    dry_run: bool = True
) -> Dict:
    """
    Import users to Casdoor via SDK.

    Args:
        users: List of Casdoor-formatted user dictionaries
        endpoint: Casdoor endpoint URL
        client_id: Casdoor client ID
        client_secret: Casdoor client secret
        org: Casdoor organization name
        dry_run: If True, simulate import without actual changes

    Returns:
        Dictionary with import results
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Importing {len(users)} users to Casdoor")

    results = {
        'total': len(users),
        'success': 0,
        'failed': 0,
        'errors': []
    }

    if dry_run:
        logger.info("DRY RUN MODE - No actual changes will be made")
        for user in users:
            logger.info(f"Would import user: {user['name']} ({user['email']})")
        results['success'] = len(users)
        return results

    try:
        # Initialize Casdoor SDK
        sdk = CasdoorSDK(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            certificate="",
            org_name=org,
            application_name=os.environ.get('CASDOOR_APPLICATION', 'app-example')
        )

        # Import each user
        for user in users:
            try:
                # Check if user already exists
                existing_user = sdk.get_user(user['name'])
                if existing_user:
                    logger.warning(f"User {user['name']} already exists, skipping")
                    results['failed'] += 1
                    results['errors'].append({
                        'username': user['name'],
                        'error': 'User already exists'
                    })
                    continue

                # Add user
                sdk.add_user(user)
                logger.info(f"Successfully imported user: {user['name']}")
                results['success'] += 1

            except Exception as e:
                logger.error(f"Failed to import user {user['name']}: {e}")
                results['failed'] += 1
                results['errors'].append({
                    'username': user['name'],
                    'error': str(e)
                })

    except Exception as e:
        logger.error(f"Failed to initialize Casdoor SDK: {e}")
        raise

    logger.info(f"Import completed: {results['success']} succeeded, {results['failed']} failed")
    return results


def generate_migration_report(
    keycloak_users: List[Dict],
    casdoor_users: List[Dict],
    import_results: Dict,
    dry_run: bool = True
) -> str:
    """
    Generate migration report.

    Args:
        keycloak_users: Original Keycloak users
        casdoor_users: Transformed Casdoor users
        import_results: Import results dictionary
        dry_run: Whether this was a dry run

    Returns:
        Report file path
    """
    report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        'migration_date': datetime.now().isoformat(),
        'dry_run': dry_run,
        'keycloak_users_count': len(keycloak_users),
        'casdoor_users_count': len(casdoor_users),
        'import_results': import_results,
        'users': casdoor_users,
        'summary': {
            'total_users': len(keycloak_users),
            'transformed_users': len(casdoor_users),
            'skipped_users': len(keycloak_users) - len(casdoor_users),
            'imported_users': import_results.get('success', 0),
            'failed_imports': import_results.get('failed', 0)
        }
    }

    report_path = os.path.join(os.path.dirname(__file__), report_filename)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Migration report generated: {report_path}")

    # Print summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Total Keycloak users: {report['summary']['total_users']}")
    print(f"Successfully transformed: {report['summary']['transformed_users']}")
    print(f"Skipped: {report['summary']['skipped_users']}")
    print(f"Imported: {report['summary']['imported_users']}")
    print(f"Failed: {report['summary']['failed_imports']}")
    print("="*60 + "\n")

    return report_path


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate users from Keycloak to Casdoor')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without actual changes')
    parser.add_argument('--execute', action='store_true', help='Execute actual migration')
    parser.add_argument('--keycloak-url', default=os.environ.get('KEYCLOAK_SERVER_URL', 'http://localhost:8080'),
                       help='Keycloak server URL')
    parser.add_argument('--keycloak-realm', default=os.environ.get('KEYCLOAK_REALM_NAME', 'master'),
                       help='Keycloak realm name')
    parser.add_argument('--keycloak-admin', default=os.environ.get('KEYCLOAK_ADMIN_USER', 'admin'),
                       help='Keycloak admin username')
    parser.add_argument('--keycloak-password', default=os.environ.get('KEYCLOAK_ADMIN_PASSWORD', 'admin'),
                       help='Keycloak admin password')
    parser.add_argument('--casdoor-endpoint', default=os.environ.get('CASDOOR_ENDPOINT', 'http://localhost:8000'),
                       help='Casdoor endpoint URL')
    parser.add_argument('--casdoor-client-id', default=os.environ.get('CASDOOR_CLIENT_ID', ''),
                       help='Casdoor client ID')
    parser.add_argument('--casdoor-client-secret', default=os.environ.get('CASDOOR_CLIENT_SECRET', ''),
                       help='Casdoor client secret')
    parser.add_argument('--casdoor-org', default=os.environ.get('CASDOOR_ORGANIZATION', 'admin'),
                       help='Casdoor organization name')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error('Please specify --dry-run or --execute')

    logger.info("Starting user migration from Keycloak to Casdoor")

    try:
        # Step 1: Export users from Keycloak
        logger.info("Step 1: Exporting users from Keycloak...")
        keycloak_users = export_keycloak_users(
            server_url=args.keycloak_url,
            realm=args.keycloak_realm,
            admin_user=args.keycloak_admin,
            admin_pass=args.keycloak_password
        )

        # Step 2: Transform to Casdoor format
        logger.info("Step 2: Transforming users to Casdoor format...")
        casdoor_users = transform_for_casdoor(keycloak_users)

        # Step 3: Import to Casdoor
        logger.info("Step 3: Importing users to Casdoor...")
        import_results = import_to_casdoor(
            users=casdoor_users,
            endpoint=args.casdoor_endpoint,
            client_id=args.casdoor_client_id,
            client_secret=args.casdoor_client_secret,
            org=args.casdoor_org,
            dry_run=args.dry_run
        )

        # Step 4: Generate report
        logger.info("Step 4: Generating migration report...")
        report_path = generate_migration_report(
            keycloak_users=keycloak_users,
            casdoor_users=casdoor_users,
            import_results=import_results,
            dry_run=args.dry_run
        )

        logger.info(f"Migration completed successfully! Report: {report_path}")

        if import_results.get('failed', 0) > 0:
            logger.warning(f"Some users failed to import. Check the report for details.")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
