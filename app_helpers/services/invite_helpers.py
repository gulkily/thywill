"""
Invite system helper functions extracted from app.py
This module contains invite tree management and statistics functions.
"""

from datetime import datetime, timedelta
from collections import defaultdict

from sqlmodel import Session, select, func
from models import User, InviteToken, engine

# Use centralized token configuration
from .token_service import TOKEN_EXP_H


def get_invite_tree() -> dict:
    """Build the complete invite tree starting from the root user (earliest created or admin), with orphaned users attached"""
    with Session(engine) as s:
        # Look for admin user first
        admin_user = s.get(User, "admin")
        
        if not admin_user:
            # If no admin user, use the earliest created user as root
            earliest_user_stmt = select(User).order_by(User.created_at.asc()).limit(1)
            earliest_user = s.exec(earliest_user_stmt).first()
            if not earliest_user:
                return {"tree": None, "stats": {"total_users": 0, "total_invites_sent": 0, "max_depth": 0}}
            admin_user = earliest_user
        
        # Build the tree with admin/root user, treating orphaned users as children
        tree = _build_user_tree_node_with_orphans(admin_user, s, depth=0)
        
        # Calculate statistics
        stats = get_invite_stats()
        
        return {"tree": tree, "stats": stats}


def _get_all_descendants(user_id: str, db: Session) -> list[User]:
    """Get all descendants of a user (for counting purposes)"""
    descendants = []
    _collect_descendants(user_id, db, descendants)
    return descendants


def _build_user_tree_node_with_orphans(user: User, db: Session, depth: int = 0) -> dict:
    """Build a tree node for a user, with special handling for root user to include orphaned users"""
    # Get all users directly invited by this user
    descendants_stmt = (
        select(User)
        .where(User.invited_by_username == user.display_name)
        .order_by(User.created_at.asc(), User.display_name.asc())
    )
    direct_descendants = list(db.exec(descendants_stmt).all())
    
    # If this is the root user (depth 0), also include orphaned users (users with no invited_by_username except root itself)
    if depth == 0:
        orphaned_users_stmt = (
            select(User)
            .where(User.invited_by_username.is_(None))
            .where(User.display_name != user.display_name)  # Don't include root user itself
            .order_by(User.created_at.asc(), User.display_name.asc())
        )
        orphaned_users = list(db.exec(orphaned_users_stmt).all())
        direct_descendants.extend(orphaned_users)

    # Ensure deterministic ordering when orphaned users are merged in
    direct_descendants = sorted(
        direct_descendants,
        key=lambda descendant: (descendant.created_at, descendant.display_name)
    )
    
    # Count total invites sent by this user
    invites_sent = db.exec(
        select(func.count(InviteToken.token))
        .where(InviteToken.created_by_user == user.display_name)
    ).first() or 0
    
    # Count successful invites (users that were actually invited vs orphaned)
    actual_invites = len([d for d in direct_descendants if d.invited_by_username == user.display_name])
    
    # Build children nodes recursively
    children = []
    for descendant in direct_descendants:
        child_node = _build_user_tree_node(descendant, db, depth + 1)
        children.append(child_node)
    
    # Count total descendants (recursive)
    total_descendants = len(direct_descendants)
    for child in children:
        total_descendants += child.get('total_descendants', 0)
    
    return {
        "user": {
            "id": user.display_name,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat(),
            "invited_by_username": user.invited_by_username,
            "invite_token_used": user.invite_token_used
        },
        "invites_sent": invites_sent,
        "successful_invites": actual_invites,
        "total_descendants": total_descendants,
        "depth": depth,
        "children": children
    }


def _build_user_tree_node(user: User, db: Session, depth: int = 0) -> dict:
    """Recursively build a tree node for a user and their descendants"""
    # Get all users directly invited by this user
    descendants_stmt = (
        select(User)
        .where(User.invited_by_username == user.display_name)
        .order_by(User.created_at.asc(), User.display_name.asc())
    )
    direct_descendants = list(db.exec(descendants_stmt).all())
    
    # Count total invites sent by this user
    invites_sent = db.exec(
        select(func.count(InviteToken.token))
        .where(InviteToken.created_by_user == user.display_name)
    ).first() or 0
    
    # Count successful invites (used tokens that created users)
    successful_invites = len(direct_descendants)
    
    # Build children nodes recursively
    children = []
    for descendant in direct_descendants:
        child_node = _build_user_tree_node(descendant, db, depth + 1)
        children.append(child_node)
    
    # Count total descendants (recursive)
    total_descendants = len(direct_descendants)
    for child in children:
        total_descendants += child.get('total_descendants', 0)
    
    return {
        "user": {
            "id": user.display_name,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat(),
            "invited_by_username": user.invited_by_username,
            "invite_token_used": user.invite_token_used
        },
        "invites_sent": invites_sent,
        "successful_invites": successful_invites,
        "total_descendants": total_descendants,
        "depth": depth,
        "children": children
    }


def get_user_descendants(user_id: str) -> list[dict]:
    """Get all users descended from a specific user (recursive)"""
    with Session(engine) as s:
        user = s.get(User, user_id)
        if not user:
            return []
        
        descendants = []
        _collect_descendants(user_id, s, descendants)
        
        # Add metadata to each descendant
        enriched_descendants = []
        for desc in descendants:
            # Get invite stats for this descendant
            invites_sent = s.exec(
                select(func.count(InviteToken.token))
                .where(InviteToken.created_by_user == desc.display_name)
            ).first() or 0

            # Count their direct descendants
            direct_children = s.exec(
                select(func.count(User.display_name))
                .where(User.invited_by_username == desc.display_name)
            ).first() or 0

            enriched_descendants.append({
                "user": {
                    "id": desc.display_name,
                    "display_name": desc.display_name,
                    "created_at": desc.created_at.isoformat(),
                    "invited_by_username": desc.invited_by_username,
                    "invite_token_used": desc.invite_token_used
                },
                "invites_sent": invites_sent,
                "direct_children": direct_children,
                "days_since_joined": (datetime.utcnow() - desc.created_at).days
            })
        
        return enriched_descendants


def _collect_descendants(user_id: str, db: Session, descendants: list, visited: set = None):
    """Recursively collect all descendants of a user"""
    if visited is None:
        visited = set()
    
    if user_id in visited:
        return  # Prevent infinite loops from data inconsistencies
    
    visited.add(user_id)
    
    # Get direct children
    direct_children = db.exec(
        select(User)
        .where(User.invited_by_username == user_id)
        .order_by(User.created_at.asc(), User.display_name.asc())
    ).all()

    for child in direct_children:
        descendants.append(child)
        # Recursively get their descendants
        _collect_descendants(child.display_name, db, descendants, visited)


def get_user_invite_path(user_id: str) -> list[dict]:
    """Get the invitation path from a user back to the root (admin)"""
    with Session(engine) as s:
        user = s.get(User, user_id)
        if not user:
            return []
        
        path = []
        current_user = user
        visited = set()  # Prevent infinite loops
        
        while current_user and current_user.display_name not in visited:
            visited.add(current_user.display_name)
            
            # Get invite token details if available
            token_info = None
            if current_user.invite_token_used:
                token = s.get(InviteToken, current_user.invite_token_used)
                if token:
                    token_info = {
                        "token": token.token[:8] + "...",  # Partially obscure token
                        "created_at": token.expires_at - timedelta(hours=TOKEN_EXP_H),
                        "expires_at": token.expires_at.isoformat()
                    }
            
            path.append({
                "user": {
                    "id": current_user.display_name,
                    "display_name": current_user.display_name,
                    "created_at": current_user.created_at.isoformat(),
                    "is_admin": current_user.display_name == "admin"
                },
                "invited_by_username": current_user.invited_by_username,
                "token_info": token_info
            })
            
            # Move up the chain
            if current_user.invited_by_username:
                current_user = s.get(User, current_user.invited_by_username)
            else:
                break
        
        # Reverse to show path from root to user
        return list(reversed(path))


def get_invite_stats() -> dict:
    """Calculate invite tree statistics"""
    with Session(engine) as s:
        # Total users
        total_users = s.exec(select(func.count(User.display_name))).first() or 0
        
        # Total invite tokens created
        total_invites_sent = s.exec(select(func.count(InviteToken.token))).first() or 0
        
        # Used invite tokens (tokens that have reached their usage limit)
        used_invites = s.exec(
            select(func.count(InviteToken.token)).where(
                (InviteToken.max_uses.isnot(None)) & (InviteToken.usage_count >= InviteToken.max_uses)
            )
        ).first() or 0
        
        # Users with invite relationships (exclude admin/system users)
        users_with_inviters = s.exec(
            select(func.count(User.display_name)).where(User.invited_by_username.isnot(None))
        ).first() or 0
        
        # Calculate max depth by finding the longest invite chain
        max_depth = _calculate_max_depth(s)
        
        # Top inviters with deterministic ordering for ties
        inviters_stmt = (
            select(User.invited_by_username, func.count(User.display_name).label('invite_count'))
            .where(User.invited_by_username.isnot(None))
            .group_by(User.invited_by_username)
            .order_by(func.count(User.display_name).desc(), User.invited_by_username.asc())
        )
        inviters = list(s.exec(inviters_stmt).all())

        top_inviters = []
        for inviter_id, count in inviters[:5]:
            inviter = s.get(User, inviter_id)
            if inviter:
                top_inviters.append({
                    "user_id": inviter.display_name,
                    "display_name": inviter.display_name,
                    "invite_count": count
                })
        
        # Recent growth (users joined in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_users = s.exec(
            select(func.count(User.display_name))
            .where(User.created_at >= thirty_days_ago)
        ).first() or 0
        
        return {
            "total_users": total_users,
            "total_invites_sent": total_invites_sent,
            "used_invites": used_invites,
            "unused_invites": total_invites_sent - used_invites,
            "users_with_inviters": users_with_inviters,
            "max_depth": max_depth,
            "top_inviters": top_inviters,
            "recent_growth": recent_users,
            "invite_success_rate": round((used_invites / total_invites_sent * 100)) if total_invites_sent > 0 else 0
        }

def _calculate_max_depth(db: Session) -> int:
    """Calculate the maximum depth across the entire invite forest."""

    user_rows = list(
        db.exec(
            select(User.display_name, User.invited_by_username)
            .order_by(User.created_at.asc(), User.display_name.asc())
        ).all()
    )

    if not user_rows:
        return 0

    children: dict[str, list[str]] = defaultdict(list)
    known_users = {display_name for display_name, _ in user_rows}

    for display_name, invited_by in user_rows:
        if invited_by:
            children[invited_by].append(display_name)

    for inviter in children:
        children[inviter].sort()

    # Identify roots: users with no inviter or whose inviter is missing
    roots = [
        display_name
        for display_name, invited_by in user_rows
        if not invited_by or invited_by not in known_users
    ]

    if not roots:
        # Fallback to the earliest user if every user references another
        roots = [user_rows[0][0]]

    max_depth = 0
    visited_nodes: set[str] = set()

    def dfs(node: str, depth: int, stack: set[str]) -> None:
        nonlocal max_depth
        if node in stack:
            return  # Cycle detected; stop this path

        stack.add(node)
        visited_nodes.add(node)
        max_depth = max(max_depth, depth)

        for child in children.get(node, []):
            dfs(child, depth + 1, stack)

        stack.remove(node)

    for root in roots:
        dfs(root, 0, set())

    # Catch any disconnected components or cycles without clear roots
    for display_name, _ in user_rows:
        if display_name not in visited_nodes:
            dfs(display_name, 0, set())

    return max_depth


# Intent-Based Authentication Functions

def create_invite_token(created_by_user: str, token_type: str = "new_user", max_uses: int = 1) -> str:
    """
    Create invite token with specified type.
    
    Args:
        created_by_user: User creating the invite
        token_type: 'new_user' for registration, 'multi_device' for device addition
        max_uses: Maximum number of uses (default 1)
        
    Returns:
        str: The created token (16-character format)
        
    Raises:
        ValueError: If token_type is invalid
    """
    import secrets
    
    if token_type not in ["new_user", "multi_device"]:
        raise ValueError("token_type must be 'new_user' or 'multi_device'")
    
    # Use same 16-character format as admin tokens (8 bytes = 16 hex chars)
    token = secrets.token_hex(8)
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)
    
    invite = InviteToken(
        token=token,
        created_by_user=created_by_user,
        token_type=token_type,
        max_uses=max_uses,
        expires_at=expires_at
    )
    
    # Save to database and archive
    with Session(engine) as session:
        session.add(invite)
        session.commit()
        
        # Archive the token creation
        try:
            from app_helpers.services.archive_writers import system_archive_writer
            system_archive_writer.log_invite_creation(
                token=token,
                created_by=created_by_user,
                token_type=token_type,
                max_uses=max_uses
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to archive invite token creation: {e}")
        
    return token


def create_device_token(user_id: str, expiry_hours: int = 24) -> str:
    """
    Create a multi-device token for adding new devices.
    
    Args:
        user_id: ID of the user creating the device token
        expiry_hours: Hours until token expires (default 24, shorter than regular invites)
        
    Returns:
        str: The device token (16-character format, same as admin tokens)
    """
    import secrets
    
    # Use same 16-character format as admin tokens (8 bytes = 16 hex chars)
    token = secrets.token_hex(8)
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    invite = InviteToken(
        token=token,
        created_by_user=user_id,
        token_type="multi_device",
        max_uses=1,  # Device tokens are single-use
        expires_at=expires_at
    )
    
    # Save to database
    with Session(engine) as session:
        session.add(invite)
        session.commit()
        
        # Archive the device token creation
        try:
            from app_helpers.services.archive_writers import system_archive_writer
            system_archive_writer.log_invite_creation(
                token=token,
                created_by=user_id,
                token_type="multi_device",
                max_uses=1
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to archive device token creation: {e}")
    
    return token


def get_user_device_tokens(user_id: str, include_expired: bool = False) -> list[InviteToken]:
    """
    Get all device tokens created by a user.
    
    Args:
        user_id: ID of the user
        include_expired: Whether to include expired tokens
        
    Returns:
        list[InviteToken]: List of device tokens
    """
    with Session(engine) as session:
        stmt = select(InviteToken).where(
            InviteToken.created_by_user == user_id,
            InviteToken.token_type == "multi_device"
        )
        
        if not include_expired:
            stmt = stmt.where(InviteToken.expires_at > datetime.utcnow())
            
        return session.exec(stmt.order_by(InviteToken.expires_at.desc())).all()
