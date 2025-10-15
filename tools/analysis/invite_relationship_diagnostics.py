#!/usr/bin/env python3
"""Quick invite tree health report using current schema."""

import os
import sys
from collections import Counter, defaultdict

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select, func

# Ensure project root is on sys.path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import engine, User, InviteToken
from app_helpers.services.invite_helpers import get_invite_stats, _calculate_max_depth  # type: ignore

def summarize_roots(session: Session) -> tuple[int, list[str]]:
    """Return count and sample of users with no inviter."""
    roots = session.exec(
        select(User.display_name).where(User.invited_by_username.is_(None)).order_by(User.created_at.asc())
    ).all()
    return len(roots), roots[:10]

def find_token_mismatches(session: Session) -> list[tuple[str, str]]:
    """Users who consumed a token but have no inviter recorded."""
    mismatches = session.exec(
        select(User.display_name, InviteToken.created_by_user)
        .join(InviteToken, InviteToken.used_by_user_id == User.display_name)
        .where(User.invited_by_username.is_(None))
    ).all()
    return mismatches

def compute_depth_distribution(session: Session) -> Counter:
    """Count users by depth while handling forests, orphans, and cycles."""
    user_rows = list(
        session.exec(
            select(User.display_name, User.invited_by_username)
            .order_by(User.created_at.asc(), User.display_name.asc())
        ).all()
    )

    depth_counts: Counter = Counter()

    if not user_rows:
        return depth_counts

    children: dict[str, list[str]] = defaultdict(list)
    known_users = {display_name for display_name, _ in user_rows}

    for display_name, invited_by in user_rows:
        if invited_by:
            children[invited_by].append(display_name)

    for inviter in children:
        children[inviter].sort()

    roots = [
        display_name
        for display_name, invited_by in user_rows
        if not invited_by or invited_by not in known_users
    ]

    if not roots:
        roots = [user_rows[0][0]]

    visited_nodes: set[str] = set()

    def dfs(name: str, depth: int, stack: set[str]) -> None:
        if name in stack:
            return

        stack.add(name)
        visited_nodes.add(name)
        depth_counts[depth] += 1

        for child in children.get(name, []):
            dfs(child, depth + 1, stack)

        stack.remove(name)

    for root in roots:
        dfs(root, 0, set())

    for display_name, _ in user_rows:
        if display_name not in visited_nodes:
            dfs(display_name, 0, set())

    return depth_counts

def main() -> None:
    with Session(engine) as session:
        try:
            stats = get_invite_stats()
        except OperationalError as exc:
            print("Invite diagnostics requires a populated database (missing tables detected).")
            print(f"Underlying error: {exc}")
            return

        roots_count, root_sample = summarize_roots(session)
        mismatches = find_token_mismatches(session)
        depth_counts = compute_depth_distribution(session)
        max_depth = _calculate_max_depth(session)

    print("Invite Tree Diagnostics")
    print("========================\n")
    print("Stats summary:")
    for key in ["total_users", "users_with_inviters", "total_invites_sent", "used_invites", "max_depth"]:
        value = stats.get(key)
        print(f"  {key}: {value}")

    print(f"\nComputed max depth (sanity check): {max_depth}")
    print(f"Root users (no inviter recorded): {roots_count}")
    if root_sample:
        print("  sample:")
        for name in root_sample:
            print(f"    - {name}")

    print("\nDepth distribution:")
    for depth in sorted(depth_counts.keys()):
        print(f"  depth {depth}: {depth_counts[depth]} users")

    print("\nInvite token mismatches (token owner but no inviter):")
    if not mismatches:
        print("  none detected")
    else:
        for user_name, inviter in mismatches[:10]:
            print(f"  - {user_name} (token created by {inviter})")
        if len(mismatches) > 10:
            print(f"  ... {len(mismatches) - 10} more")

if __name__ == "__main__":
    main()
