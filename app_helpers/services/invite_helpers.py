"""
Invite system helper functions extracted from app.py
This module contains invite tree management and statistics functions.
"""

import os
from datetime import datetime, timedelta
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
        .order_by(User.created_at.asc())
    )
    direct_descendants = db.exec(descendants_stmt).all()
    
    # If this is the root user (depth 0), also include orphaned users (users with no invited_by_username except root itself)
    if depth == 0:
        orphaned_users_stmt = (
            select(User)
            .where(User.invited_by_username.is_(None))
            .where(User.display_name != user.display_name)  # Don't include root user itself
            .order_by(User.created_at.asc())
        )
        orphaned_users = db.exec(orphaned_users_stmt).all()
        direct_descendants.extend(orphaned_users)
    
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
        .order_by(User.created_at.asc())
    )
    direct_descendants = db.exec(descendants_stmt).all()
    
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
                .where(InviteToken.created_by_user == desc.id)
            ).first() or 0
            
            # Count their direct descendants
            direct_children = s.exec(
                select(func.count(User.display_name))
                .where(User.invited_by_username == desc.id)
            ).first() or 0
            
            enriched_descendants.append({
                "user": {
                    "id": desc.id,
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
        select(User).where(User.invited_by_username == user_id)
    ).all()
    
    for child in direct_children:
        descendants.append(child)
        # Recursively get their descendants
        _collect_descendants(child.id, db, descendants, visited)


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
        
        # Top inviters (users who have successfully invited the most people)
        # Get all users who have invited someone
        inviters = s.exec(
            select(User.invited_by_username, func.count(User.display_name).label('count'))
            .where(User.invited_by_username.isnot(None))
            .group_by(User.invited_by_username)
            .order_by(func.count(User.display_name).desc())
        ).all()
        
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
    """Calculate the maximum depth of the invite tree"""
    # Find the root user (admin or earliest created)
    admin_user = db.get(User, "admin")
    if not admin_user:
        earliest_user_stmt = select(User).order_by(User.created_at.asc()).limit(1)
        admin_user = db.exec(earliest_user_stmt).first()
    
    if not admin_user:
        return 0
    
    def get_depth(user_id: str, visited: set = None, current_depth: int = 0) -> int:
        if visited is None:
            visited = set()
        
        if user_id in visited:
            return current_depth
        
        visited.add(user_id)
        
        # Get all users invited by this user
        descendants = db.exec(
            select(User.display_name).where(User.invited_by_username == user_id)
        ).all()
        
        if not descendants:
            return current_depth
        
        max_child_depth = current_depth
        for descendant_id in descendants:
            child_depth = get_depth(descendant_id, visited.copy(), current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    # Since orphaned users are treated as depth 1 under root, the minimum depth is 1 if there are orphaned users
    depth = get_depth(admin_user.display_name)
    
    # Check if there are orphaned users (if so, min depth is 1)
    orphaned_count = db.exec(
        select(func.count(User.display_name))
        .where(User.invited_by_username.is_(None))
        .where(User.display_name != admin_user.display_name)
    ).first() or 0
    
    return max(depth, 1 if orphaned_count > 0 else 0)