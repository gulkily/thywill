# app_helpers/utils/user_management.py
"""
User management utilities including soft deletion via role system

This module provides functions for deactivating and reactivating users
using the role-based system, avoiding the need for schema changes.
"""

import json
from datetime import datetime
from sqlmodel import Session, select
from models import User, Role, UserRole


class UserManagementError(Exception):
    """Raised when user management operations fail"""
    pass


def get_deactivated_role_id(session: Session) -> str:
    """Get the ID of the deactivated role"""
    stmt = select(Role).where(Role.name == "deactivated")
    role = session.exec(stmt).first()
    if not role:
        raise UserManagementError("Deactivated role not found. Run add_deactivated_role.py first.")
    return role.id


def is_user_deactivated(user_id: str, session: Session) -> bool:
    """Check if a user is deactivated (has deactivated role)"""
    try:
        user = session.exec(select(User).where(User.display_name == user_id)).first()
        if not user:
            return False
        return user.has_role("deactivated", session)
    except Exception:
        return False


def get_user_deactivation_info(user_id: str, session: Session) -> dict | None:
    """Get deactivation information for a user"""
    if not is_user_deactivated(user_id, session):
        return None
    
    # Find the deactivated role assignment
    deactivated_role_id = get_deactivated_role_id(session)
    stmt = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == deactivated_role_id
    )
    user_role = session.exec(stmt).first()
    
    if not user_role:
        return None
    
    return {
        'deactivated_at': user_role.granted_at,
        'deactivated_by': user_role.granted_by,
        'expires_at': user_role.expires_at
    }


def deactivate_user(user_id: str, admin_id: str, reason: str = None, session: Session = None) -> bool:
    """
    Deactivate a user by removing all roles and assigning deactivated role
    
    Args:
        user_id: ID of user to deactivate
        admin_id: ID of admin performing the action
        reason: Optional reason for deactivation
        session: Database session
    
    Returns:
        True if successful, False otherwise
    """
    if not session:
        raise ValueError("Database session is required")
    
    try:
        # Check if user exists
        user = session.exec(select(User).where(User.display_name == user_id)).first()
        if not user:
            raise UserManagementError(f"User not found: {user_id}")
        
        # Check if user is already deactivated
        if is_user_deactivated(user_id, session):
            return True  # Already deactivated
        
        # Prevent deactivating admin users (safety check)
        if user.has_role("admin", session):
            raise UserManagementError("Cannot deactivate admin users")
        
        # Get deactivated role
        deactivated_role_id = get_deactivated_role_id(session)
        
        # Remove all existing roles (keep history by setting expiration)
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        active_roles = session.exec(stmt).all()
        
        for user_role in active_roles:
            user_role.expires_at = datetime.utcnow()
            session.add(user_role)
        
        # Add deactivated role with reason in a custom field (using expires_at = None for permanent)
        deactivated_role = UserRole(
            user_id=user_id,
            role_id=deactivated_role_id,
            granted_by=admin_id,
            granted_at=datetime.utcnow(),
            expires_at=None  # Permanent until manually reactivated
        )
        
        session.add(deactivated_role)
        session.commit()
        
        # Archive the role change
        try:
            from ..services.archive_writers import role_archive_writer
            role_assignment = {
                'user_id': user_id,
                'role_name': 'deactivated',
                'action': 'assigned',
                'granted_by': admin_id,
                'granted_at': datetime.utcnow(),
                'expires_at': None,
                'details': reason or 'User deactivated by admin'
            }
            role_archive_writer.log_role_assignment(role_assignment)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to archive role assignment: {e}")
        
        return True
        
    except Exception as e:
        session.rollback()
        raise UserManagementError(f"Failed to deactivate user: {str(e)}")


def reactivate_user(user_id: str, admin_id: str, session: Session = None) -> bool:
    """
    Reactivate a user by removing deactivated role and restoring default user role
    
    Args:
        user_id: ID of user to reactivate
        admin_id: ID of admin performing the action
        session: Database session
    
    Returns:
        True if successful, False otherwise
    """
    if not session:
        raise ValueError("Database session is required")
    
    try:
        # Check if user exists
        user = session.exec(select(User).where(User.display_name == user_id)).first()
        if not user:
            raise UserManagementError(f"User not found: {user_id}")
        
        # Check if user is deactivated
        if not is_user_deactivated(user_id, session):
            return True  # Already active
        
        # Get deactivated role
        deactivated_role_id = get_deactivated_role_id(session)
        
        # Remove deactivated role
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == deactivated_role_id,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        deactivated_user_role = session.exec(stmt).first()
        
        if deactivated_user_role:
            deactivated_user_role.expires_at = datetime.utcnow()
            session.add(deactivated_user_role)
        
        # Restore default user role
        user_role_stmt = select(Role).where(Role.name == "user")
        user_role = session.exec(user_role_stmt).first()
        
        if user_role:
            restored_role = UserRole(
                user_id=user_id,
                role_id=user_role.id,
                granted_by=admin_id,
                granted_at=datetime.utcnow(),
                expires_at=None
            )
            session.add(restored_role)
        
        session.commit()
        
        # Archive the role change
        try:
            from ..services.archive_writers import role_archive_writer
            role_assignment = {
                'user_id': user_id,
                'role_name': 'user',
                'action': 'assigned',
                'granted_by': admin_id,
                'granted_at': datetime.utcnow(),
                'expires_at': None,
                'details': 'User reactivated by admin'
            }
            role_archive_writer.log_role_assignment(role_assignment)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to archive role assignment: {e}")
        
        return True
        
    except Exception as e:
        session.rollback()
        raise UserManagementError(f"Failed to reactivate user: {str(e)}")


def get_deactivated_users(session: Session) -> list:
    """Get list of all deactivated users"""
    try:
        deactivated_role_id = get_deactivated_role_id(session)
        
        stmt = select(User, UserRole).join(
            UserRole, User.display_name == UserRole.user_id
        ).where(
            UserRole.role_id == deactivated_role_id,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        
        results = session.exec(stmt).all()
        
        deactivated_users = []
        for user, user_role in results:
            deactivated_users.append({
                'user': user,
                'deactivated_at': user_role.granted_at,
                'deactivated_by': user_role.granted_by
            })
        
        return deactivated_users
        
    except Exception:
        return []


def get_active_users(session: Session) -> list:
    """Get list of all active (non-deactivated) users"""
    try:
        deactivated_role_id = get_deactivated_role_id(session)
        
        # Get all users who don't have active deactivated role
        stmt = select(User).where(
            ~User.display_name.in_(
                select(UserRole.user_id).where(
                    UserRole.role_id == deactivated_role_id,
                    (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
                )
            )
        )
        
        return list(session.exec(stmt).all())
        
    except Exception:
        # Fallback to all users if role system fails
        return list(session.exec(select(User)).all())


def cleanup_expired_deactivations(session: Session) -> int:
    """
    Clean up any expired deactivations (if expires_at was set)
    Returns number of users reactivated
    """
    try:
        deactivated_role_id = get_deactivated_role_id(session)
        
        # Find expired deactivated roles
        stmt = select(UserRole).where(
            UserRole.role_id == deactivated_role_id,
            UserRole.expires_at <= datetime.utcnow()
        )
        
        expired_roles = session.exec(stmt).all()
        reactivated_count = 0
        
        for user_role in expired_roles:
            # Auto-reactivate by restoring user role
            user_role_stmt = select(Role).where(Role.name == "user")
            user_role_obj = session.exec(user_role_stmt).first()
            
            if user_role_obj:
                restored_role = UserRole(
                    user_id=user_role.user_id,
                    role_id=user_role_obj.id,
                    granted_by=None,  # System reactivation
                    granted_at=datetime.utcnow(),
                    expires_at=None
                )
                session.add(restored_role)
                reactivated_count += 1
        
        session.commit()
        return reactivated_count
        
    except Exception:
        session.rollback()
        return 0


# Helper function for CLI/admin use
def bulk_deactivate_users(user_ids: list, admin_id: str, reason: str = None, session: Session = None) -> dict:
    """
    Bulk deactivate multiple users
    
    Returns:
        dict with 'success', 'failed', and 'errors' lists
    """
    if not session:
        raise ValueError("Database session is required")
    
    results = {
        'success': [],
        'failed': [],
        'errors': []
    }
    
    for user_id in user_ids:
        try:
            if deactivate_user(user_id, admin_id, reason, session):
                results['success'].append(user_id)
            else:
                results['failed'].append(user_id)
        except Exception as e:
            results['failed'].append(user_id)
            results['errors'].append(f"{user_id}: {str(e)}")
    
    return results