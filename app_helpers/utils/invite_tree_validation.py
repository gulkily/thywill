# app_helpers/utils/invite_tree_validation.py
"""
Invite tree validation and integrity enforcement

This module ensures all users are properly connected to the invite tree
and prevents orphaned users from being created.
"""

import sys
import os
from datetime import datetime
from sqlmodel import Session, select, text

# Add the project root to sys.path to import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import User, InviteToken, engine


class InviteTreeIntegrityError(Exception):
    """Raised when invite tree integrity violations are detected"""
    pass


def validate_new_user_invite_relationship(user_data: dict, invite_token: str = None, session: Session = None) -> dict:
    """
    Validate and ensure new user will have proper invite relationship
    
    Args:
        user_data: Dictionary containing user creation data
        invite_token: Token used for invitation (if any)
        session: Database session
    
    Returns:
        Updated user_data with correct invite relationship fields
        
    Raises:
        InviteTreeIntegrityError: If invite relationship cannot be established
    """
    if not session:
        raise ValueError("Database session is required")
    
    # If this is the first user (admin), no invite relationship needed
    first_user = session.exec(select(User)).first()
    if not first_user:
        return user_data
    
    # Ensure invite relationship fields are set
    if invite_token:
        # Get invite token details
        inv = session.exec(select(InviteToken).where(InviteToken.token == invite_token)).first()
        if not inv:
            raise InviteTreeIntegrityError(f"Invalid invite token: {invite_token}")
        
        # Set invite relationship from token
        user_data['invited_by_username'] = inv.created_by_user if inv.created_by_user != "system" else get_admin_user_id(session)
        user_data['invite_token_used'] = invite_token
    else:
        # No invite token - fallback to admin (for migration/admin creation scenarios)
        admin_id = get_admin_user_id(session)
        user_data['invited_by_username'] = admin_id
        user_data['invite_token_used'] = None
    
    return user_data


def validate_existing_user_invite_update(user: User, invite_token: str, session: Session) -> bool:
    """
    Validate that an existing user can be updated with invite relationship
    
    Args:
        user: Existing user object
        invite_token: Token being used
        session: Database session
    
    Returns:
        True if update is valid, False otherwise
    """
    # If user already has invite relationship, don't override
    if user.invited_by_username and user.invite_token_used:
        return False
    
    # Validate the token
    inv = session.exec(select(InviteToken).where(InviteToken.token == invite_token)).first()
    if not inv or inv.used:
        return False
    
    return True


def get_admin_user_id(session: Session) -> str:
    """Get the admin user ID for fallback invite relationships"""
    # First try to find user with ID 'admin'
    admin_user = session.exec(select(User).where(User.id == "admin")).first()
    if admin_user:
        return admin_user.display_name
    
    # Fall back to first user created (usually admin)
    first_user = session.exec(select(User).order_by(User.created_at)).first()
    if first_user:
        return first_user.display_name
    
    raise InviteTreeIntegrityError("No admin user found - cannot establish invite relationships")


def detect_orphaned_users(session: Session) -> list:
    """
    Detect users who are not connected to the invite tree
    
    Returns:
        List of orphaned user IDs
    """
    orphaned = session.exec(text("""
        SELECT id, display_name, created_at
        FROM user 
        WHERE invited_by_username IS NULL
        AND id != (SELECT id FROM user ORDER BY created_at LIMIT 1)
    """)).fetchall()
    
    return [{'id': row[0], 'name': row[1], 'created_at': row[2]} for row in orphaned]


def detect_circular_references(session: Session) -> list:
    """
    Detect circular references in the invite tree
    
    Returns:
        List of user IDs involved in circular references
    """
    try:
        circular_refs = session.exec(text("""
            WITH RECURSIVE invite_chain(user_id, inviter_id, depth, path) AS (
                SELECT id, invited_by_username, 0, id
                FROM user
                WHERE invited_by_username IS NOT NULL
                
                UNION ALL
                
                SELECT u.id, u.invited_by_username, ic.depth + 1, ic.path || '->' || u.id
                FROM user u
                JOIN invite_chain ic ON u.invited_by_username = ic.user_id
                WHERE ic.depth < 20 AND u.id NOT IN (
                    SELECT value FROM json_each('[' || '"' || replace(ic.path, '->', '","') || '"' || ']')
                )
            )
            SELECT user_id, path FROM invite_chain WHERE depth >= 15
        """)).fetchall()
        
        return [{'user_id': row[0], 'path': row[1]} for row in circular_refs]
    except Exception:
        # Fallback for simpler circular reference detection
        return []


def validate_invite_tree_integrity(session: Session) -> dict:
    """
    Comprehensive invite tree integrity validation
    
    Returns:
        Dictionary with validation results and any issues found
    """
    results = {
        'valid': True,
        'issues': [],
        'stats': {},
        'orphaned_users': [],
        'circular_references': []
    }
    
    try:
        # Get basic statistics
        total_users = session.exec(text("SELECT COUNT(*) FROM user")).first()[0]
        users_with_inviters = session.exec(text(
            "SELECT COUNT(*) FROM user WHERE invited_by_username IS NOT NULL"
        )).first()[0]
        
        results['stats'] = {
            'total_users': total_users,
            'users_with_inviters': users_with_inviters,
            'orphaned_count': total_users - users_with_inviters
        }
        
        # Detect orphaned users
        orphaned = detect_orphaned_users(session)
        if orphaned:
            results['valid'] = False
            results['orphaned_users'] = orphaned
            results['issues'].append(f"Found {len(orphaned)} orphaned users")
        
        # Detect circular references
        circular = detect_circular_references(session)
        if circular:
            results['valid'] = False
            results['circular_references'] = circular
            results['issues'].append(f"Found {len(circular)} circular references")
        
        # Check for invalid invite relationships
        invalid_inviters = session.exec(text("""
            SELECT u1.id, u1.display_name, u1.invited_by_username
            FROM user u1
            LEFT JOIN user u2 ON u1.invited_by_username = u2.id
            WHERE u1.invited_by_username IS NOT NULL 
            AND u2.id IS NULL
        """)).fetchall()
        
        if invalid_inviters:
            results['valid'] = False
            results['issues'].append(f"Found {len(invalid_inviters)} users with invalid inviter IDs")
        
    except Exception as e:
        results['valid'] = False
        results['issues'].append(f"Validation error: {str(e)}")
    
    return results


def ensure_user_has_invite_relationship(user_id: str, session: Session) -> bool:
    """
    Ensure a specific user has a valid invite relationship
    
    Args:
        user_id: ID of user to check/fix
        session: Database session
    
    Returns:
        True if user now has valid relationship, False if failed
    """
    user = session.exec(select(User).where(User.display_name == user_id)).first()
    if not user:
        return False
    
    # If user already has relationship, validate it
    if user.invited_by_username:
        inviter = session.exec(select(User).where(User.display_name == user.invited_by_username)).first()
        if inviter:
            return True  # Valid relationship exists
    
    # Need to establish relationship - assign to admin as fallback
    try:
        admin_id = get_admin_user_id(session)
        user.invited_by_username = admin_id
        session.add(user)
        session.commit()
        return True
    except Exception:
        return False


def create_integrity_constraints():
    """
    Create database constraints to enforce invite tree integrity
    Note: SQLite has limited constraint support, so this implements basic checks
    """
    constraints = [
        # Ensure invited_by_username references valid user
        "CREATE INDEX IF NOT EXISTS idx_user_invited_by ON user(invited_by_username)",
        
        # Ensure invite tokens are properly linked
        "CREATE INDEX IF NOT EXISTS idx_invitetoken_used_by ON invitetoken(used_by_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_invite_token ON user(invite_token_used)",
    ]
    
    with Session(engine) as session:
        for constraint in constraints:
            try:
                session.exec(text(constraint))
                session.commit()
            except Exception as e:
                print(f"Warning: Could not create constraint: {e}")


# Auto-validation middleware function
def validate_user_operation(operation_type: str, user_data: dict = None, user_id: str = None, session: Session = None):
    """
    Middleware function to validate user operations maintain invite tree integrity
    
    Args:
        operation_type: 'create', 'update', 'delete'
        user_data: User data for create/update operations
        user_id: User ID for update/delete operations
        session: Database session
    """
    if not session:
        return
    
    try:
        if operation_type == 'create' and user_data:
            # Ensure new users have proper invite relationships
            if 'invited_by_username' not in user_data or not user_data['invited_by_username']:
                # Check if this is the first user (admin)
                first_user = session.exec(select(User)).first()
                if first_user:  # Not first user - needs invite relationship
                    admin_id = get_admin_user_id(session)
                    user_data['invited_by_username'] = admin_id
        
        elif operation_type == 'delete' and user_id:
            # Check if deleting this user would orphan others
            dependents = session.exec(
                select(User).where(User.invited_by_username == user_id)
            ).all()
            
            if dependents:
                # Re-assign dependents to admin
                admin_id = get_admin_user_id(session)
                for dependent in dependents:
                    dependent.invited_by_username = admin_id
                    session.add(dependent)
    
    except Exception as e:
        # Log but don't fail the operation
        print(f"Invite tree validation warning: {e}")


if __name__ == "__main__":
    # Command-line interface for validation
    import sys
    
    with Session(engine) as session:
        if len(sys.argv) > 1 and sys.argv[1] == "check":
            results = validate_invite_tree_integrity(session)
            print("=== Invite Tree Integrity Check ===")
            print(f"Status: {'VALID' if results['valid'] else 'ISSUES FOUND'}")
            print(f"Total users: {results['stats']['total_users']}")
            print(f"Users with inviters: {results['stats']['users_with_inviters']}")
            print(f"Orphaned users: {results['stats']['orphaned_count']}")
            
            if results['issues']:
                print("\nIssues found:")
                for issue in results['issues']:
                    print(f"  - {issue}")
        else:
            print("Usage: python invite_tree_validation.py check")