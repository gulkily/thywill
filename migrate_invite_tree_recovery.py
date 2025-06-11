#!/usr/bin/env python3
"""
Migration script for invite tree orphaned user recovery
Run this script to reconstruct missing invite relationships for existing users

This script addresses the critical issue where 90% of users are orphaned
(not connected to the invite tree) due to historical data gaps.

Recovery Strategy:
1. Analyze historical invite tokens and correlate with user creation timestamps
2. Match users to their likely inviters based on token usage patterns
3. Set admin as fallback inviter for users with no clear invitation path
4. Update User.invited_by_user_id for all orphaned users
"""

import sys
import os
from sqlmodel import Session, select, text
from datetime import datetime, timedelta

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, InviteToken

def get_admin_user_id(session: Session) -> str:
    """Find the admin user ID"""
    # First try to find user with ID 'admin'
    admin_user = session.exec(select(User).where(User.id == "admin")).first()
    if admin_user:
        return admin_user.id
    
    # Fall back to first user created (usually admin)
    first_user = session.exec(select(User).order_by(User.created_at)).first()
    if first_user:
        return first_user.id
    
    raise Exception("No admin user found - database may be empty")

def analyze_current_state(session: Session):
    """Analyze current invite tree state"""
    print("=== Current Invite Tree State Analysis ===")
    
    # Count total users
    total_users = session.exec(text("SELECT COUNT(*) FROM user")).first()[0]
    print(f"Total users: {total_users}")
    
    # Count users with invite relationships
    users_with_inviters = session.exec(text(
        "SELECT COUNT(*) FROM user WHERE invited_by_user_id IS NOT NULL"
    )).first()[0]
    print(f"Users with invite relationships: {users_with_inviters}")
    
    # Count orphaned users
    orphaned_users = total_users - users_with_inviters
    print(f"Orphaned users (no invite relationship): {orphaned_users}")
    
    # Count invite tokens
    total_tokens = session.exec(text("SELECT COUNT(*) FROM invitetoken")).first()[0]
    used_tokens = session.exec(text("SELECT COUNT(*) FROM invitetoken WHERE used = 1")).first()[0]
    print(f"Total invite tokens: {total_tokens}")
    print(f"Used tokens: {used_tokens}")
    
    # Check for tokens with used_by_user_id but users without invited_by_user_id
    mismatched = session.exec(text("""
        SELECT COUNT(*) FROM invitetoken t
        JOIN user u ON t.used_by_user_id = u.id
        WHERE t.used = 1 AND u.invited_by_user_id IS NULL
    """)).first()[0]
    print(f"Users with tokens but no invite relationship: {mismatched}")
    
    return {
        'total_users': total_users,
        'users_with_inviters': users_with_inviters,
        'orphaned_users': orphaned_users,
        'total_tokens': total_tokens,
        'used_tokens': used_tokens,
        'mismatched': mismatched
    }

def recover_token_relationships(session: Session) -> int:
    """Recover invite relationships from existing token data"""
    print("\n=== Recovering Token-Based Relationships ===")
    
    # Find users who used tokens but don't have invite relationships
    mismatched_users = session.exec(text("""
        SELECT u.id, u.display_name, t.token, t.created_by_user
        FROM invitetoken t
        JOIN user u ON t.used_by_user_id = u.id
        WHERE t.used = 1 AND u.invited_by_user_id IS NULL
    """)).fetchall()
    
    recovered_count = 0
    
    for user_id, display_name, token, created_by_user in mismatched_users:
        inviter_id = created_by_user if created_by_user != "system" else None
        
        # Get and update the user directly using SQLModel
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user:
            user.invited_by_user_id = inviter_id
            user.invite_token_used = token
            session.add(user)
        
        recovered_count += 1
        print(f"✓ Recovered: {display_name} -> invited by {inviter_id or 'system'} (token: {token[:8]}...)")
    
    return recovered_count

def recover_temporal_relationships(session: Session) -> int:
    """Recover relationships by analyzing user creation timing"""
    print("\n=== Recovering Temporal-Based Relationships ===")
    
    # Get all orphaned users (still without relationships after token recovery)
    orphaned_users = session.exec(text("""
        SELECT id, display_name, created_at
        FROM user 
        WHERE invited_by_user_id IS NULL
        ORDER BY created_at
    """)).fetchall()
    
    if not orphaned_users:
        print("No orphaned users found after token recovery")
        return 0
    
    admin_id = get_admin_user_id(session)
    recovered_count = 0
    
    # Get all used tokens ordered by creation time
    used_tokens = session.exec(text("""
        SELECT token, created_by_user, expires_at, used_by_user_id
        FROM invitetoken 
        WHERE used = 1
        ORDER BY expires_at
    """)).fetchall()
    
    for user_id, display_name, created_at in orphaned_users:
        inviter_id = None
        matched_token = None
        
        # Skip admin user - they should be root of tree
        if user_id == admin_id:
            print(f"✓ Skipping admin user: {display_name} (root of tree)")
            continue
        
        # Try to find a token that could have been used for this user
        # Look for tokens created before this user and not yet assigned
        for token, created_by_user, expires_at, used_by_user_id in used_tokens:
            # If this token was used by this specific user, use it
            if used_by_user_id == user_id:
                inviter_id = created_by_user if created_by_user != "system" else admin_id
                matched_token = token
                break
            
            # If no specific match, find tokens created before this user
            # and within a reasonable time window (24 hours)
            if expires_at and created_at:
                try:
                    # Parse expires_at if it's a string
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    
                    token_creation = expires_at - timedelta(days=7)  # Tokens expire after 7 days
                    time_diff = abs((created_at - token_creation).total_seconds())
                    
                    # If user was created within 24 hours of token creation, it's likely a match
                    if time_diff <= 86400 and not used_by_user_id:  # 24 hours
                        inviter_id = created_by_user if created_by_user != "system" else admin_id
                        matched_token = token
                        break
                except (ValueError, TypeError):
                    # Skip if datetime parsing fails
                    continue
        
        # If no token match found, assign to admin as fallback
        if not inviter_id:
            inviter_id = admin_id
            print(f"  Fallback to admin for: {display_name}")
        
        # Get and update the user directly using SQLModel
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user:
            user.invited_by_user_id = inviter_id
            user.invite_token_used = matched_token
            session.add(user)
        
        recovered_count += 1
        inviter_name = "admin" if inviter_id == admin_id else inviter_id
        token_info = f" (token: {matched_token[:8]}...)" if matched_token else " (no token - fallback)"
        print(f"✓ Recovered: {display_name} -> invited by {inviter_name}{token_info}")
    
    return recovered_count

def validate_recovery(session: Session):
    """Validate the recovery results"""
    print("\n=== Validation Results ===")
    
    # Re-analyze state
    final_state = analyze_current_state(session)
    
    # Check for circular references
    circular_refs = session.exec(text("""
        WITH RECURSIVE invite_chain(user_id, inviter_id, depth) AS (
            SELECT id, invited_by_user_id, 0
            FROM user
            WHERE invited_by_user_id IS NOT NULL
            
            UNION ALL
            
            SELECT u.id, u.invited_by_user_id, ic.depth + 1
            FROM user u
            JOIN invite_chain ic ON u.invited_by_user_id = ic.user_id
            WHERE ic.depth < 10
        )
        SELECT COUNT(*) FROM invite_chain WHERE depth >= 10
    """)).first()[0]
    
    if circular_refs > 0:
        print(f"⚠️  Warning: Possible circular references detected: {circular_refs}")
    else:
        print("✓ No circular references detected")
    
    # Check tree connectivity
    root_users = session.exec(text("""
        SELECT COUNT(*) FROM user WHERE invited_by_user_id IS NULL
    """)).first()[0]
    
    print(f"✓ Root users (tree roots): {root_users}")
    
    if final_state['orphaned_users'] == 0:
        print("🎉 SUCCESS: All users are now connected to the invite tree!")
    else:
        print(f"⚠️  {final_state['orphaned_users']} users still orphaned")
    
    return final_state['orphaned_users'] == 0

def migrate_invite_tree_recovery():
    """Main migration function"""
    print("Starting invite tree orphaned user recovery...")
    print("This will reconstruct missing invite relationships for existing users.\n")
    
    with Session(engine) as session:
        try:
            # Analyze current state
            initial_state = analyze_current_state(session)
            
            if initial_state['orphaned_users'] == 0:
                print("✓ No orphaned users found - invite tree is already complete!")
                return
            
            # Step 1: Recover relationships from existing token data
            token_recovered = recover_token_relationships(session)
            
            # Step 2: Recover remaining relationships using temporal analysis
            temporal_recovered = recover_temporal_relationships(session)
            
            # Commit all changes
            session.commit()
            
            print(f"\n=== Recovery Summary ===")
            print(f"Users recovered via token matching: {token_recovered}")
            print(f"Users recovered via temporal analysis: {temporal_recovered}")
            print(f"Total users recovered: {token_recovered + temporal_recovered}")
            
            # Validate results
            success = validate_recovery(session)
            
            if success:
                print("\n🎉 Migration completed successfully!")
                print("All users are now properly connected to the invite tree.")
            else:
                print("\n⚠️  Migration completed with warnings.")
                print("Some users may still need manual intervention.")
            
        except Exception as e:
            session.rollback()
            print(f"\n✗ Migration failed: {e}")
            raise

def rollback_migration():
    """Remove invite relationships (for testing purposes)"""
    print("Rolling back invite tree recovery...")
    print("This will remove all invite relationships, creating orphaned users again.")
    
    response = input("Are you sure you want to rollback? This cannot be undone easily. (y/N): ")
    if response.lower() != 'y':
        print("Rollback cancelled.")
        return
    
    with Session(engine) as session:
        try:
            # Clear all invite relationships except for admin
            session.exec(text("""
                UPDATE user 
                SET invited_by_user_id = NULL, invite_token_used = NULL
                WHERE id != 'admin'
            """))
            
            session.commit()
            print("✓ Rollback completed - all users (except admin) are now orphaned")
            
        except Exception as e:
            session.rollback()
            print(f"✗ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    elif len(sys.argv) > 1 and sys.argv[1] == "analyze":
        with Session(engine) as session:
            analyze_current_state(session)
    else:
        migrate_invite_tree_recovery()