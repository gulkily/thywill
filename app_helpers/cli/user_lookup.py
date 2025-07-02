#!/usr/bin/env python3
"""
User Lookup CLI Module

Provides user lookup functionality for CLI commands.
Can be run independently or called from other modules.
"""

import sys
from typing import Optional
from sqlmodel import Session, select
from models import engine, User


def find_user_by_identifier(session: Session, identifier: str) -> Optional[User]:
    """
    Find a user by ID or display name with flexible matching.
    
    Args:
        session: Database session
        identifier: User ID or display name (supports partial matching)
        
    Returns:
        User object if found, None otherwise
    """
    # First try exact display_name match
    stmt = select(User).where(User.display_name == identifier)
    user = session.exec(stmt).first()
    
    if not user:
        # Try partial display_name match for convenience
        stmt = select(User).where(User.display_name.contains(identifier))
        partial_users = list(session.exec(stmt))
        if len(partial_users) == 1:
            user = partial_users[0]
    
    if not user:
        print(f'❌ No user found matching: {identifier}')
        print('   Available users:')
        # Show first 10 users as examples
        all_users = list(session.exec(select(User).limit(10)))
        for u in all_users:
            print(f'   - "{u.display_name}"')
        if len(all_users) == 10:
            print('   ... (showing first 10 users)')
        return None
    
    return user


def find_user_interactive(identifier: str) -> Optional[User]:
    """
    Find a user with interactive session management.
    
    Args:
        identifier: User ID or display name
        
    Returns:
        User object if found, None otherwise
    """
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, identifier)
            return user
    except Exception as e:
        print(f'❌ Error finding user: {e}')
        return None


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python user_lookup.py <user_identifier>")
        sys.exit(1)
    
    identifier = sys.argv[1]
    
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, identifier)
            
            if user:
                print(f'✅ Found user: "{user.display_name}"')
                print(f'   Username: {user.display_name}')
                print(f'   Admin: {"Yes" if user.is_admin else "No"}')
                print(f'   Created: {user.created_at}')
            else:
                sys.exit(1)
                
    except Exception as e:
        print(f'❌ Lookup failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()