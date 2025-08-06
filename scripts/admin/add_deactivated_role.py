#!/usr/bin/env python3
"""
Add 'deactivated' role for user soft deletion functionality
Run this script to add the deactivated role to the role system
"""

import sys
import os
import json
from sqlmodel import Session, select

# Add the project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))  # Go up two levels from scripts/admin/
sys.path.insert(0, project_root)

from models import engine, Role

def add_deactivated_role():
    """Add the deactivated role to the system"""
    print("Adding 'deactivated' role for user soft deletion...")
    
    with Session(engine) as session:
        try:
            # Check if deactivated role already exists
            stmt = select(Role).where(Role.name == "deactivated")
            existing_role = session.exec(stmt).first()
            
            if existing_role:
                print("✓ 'deactivated' role already exists")
                print(f"  ID: {existing_role.id}")
                print(f"  Description: {existing_role.description}")
                return existing_role.id
            
            # Create deactivated role
            deactivated_role = Role(
                name="deactivated",
                description="Deactivated user - no permissions, cannot login",
                permissions=json.dumps([]),  # No permissions
                is_system_role=True,
                created_by=None  # System role
            )
            
            session.add(deactivated_role)
            session.commit()
            
            print("✓ Successfully created 'deactivated' role")
            print(f"  ID: {deactivated_role.id}")
            print(f"  Description: {deactivated_role.description}")
            print(f"  Permissions: [] (no permissions)")
            
            return deactivated_role.id
            
        except Exception as e:
            session.rollback()
            print(f"✗ Failed to add deactivated role: {e}")
            raise

if __name__ == "__main__":
    add_deactivated_role()