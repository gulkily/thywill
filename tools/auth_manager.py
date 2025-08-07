#!/usr/bin/env python3
"""
Authentication Request Manager - Command Line Tool
Manage pending authentication requests from the command line.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, List
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, select
from models import engine, AuthenticationRequest, AuthApproval, User

def format_relative_time(dt: datetime, future: bool = False) -> str:
    """Simple relative time formatting"""
    now = datetime.utcnow()
    if future:
        diff = dt - now
        if diff.total_seconds() < 0:
            return "expired"
        prefix = "in "
    else:
        diff = now - dt
        prefix = ""
    
    seconds = abs(diff.total_seconds())
    
    if seconds < 60:
        return f"{prefix}{int(seconds)}s ago" if not future else f"{prefix}{int(seconds)}s"
    elif seconds < 3600:
        return f"{prefix}{int(seconds/60)}m ago" if not future else f"{prefix}{int(seconds/60)}m"
    elif seconds < 86400:
        return f"{prefix}{int(seconds/3600)}h ago" if not future else f"{prefix}{int(seconds/3600)}h"
    else:
        return f"{prefix}{int(seconds/86400)}d ago" if not future else f"{prefix}{int(seconds/86400)}d"

def get_pending_requests() -> List[dict]:
    """Get all pending authentication requests with user info"""
    with Session(engine) as session:
        # Get pending requests with user details
        stmt = select(AuthenticationRequest, User).where(
            AuthenticationRequest.status == "pending",
            AuthenticationRequest.user_id == User.display_name,
            AuthenticationRequest.expires_at > datetime.utcnow()
        )
        
        results = session.exec(stmt).all()
        
        requests = []
        for auth_req, user in results:
            # Get existing approvals
            approval_stmt = select(AuthApproval).where(
                AuthApproval.auth_request_id == auth_req.id
            )
            approvals = session.exec(approval_stmt).all()
            
            # Get approver names
            approver_names = []
            for approval in approvals:
                if approval.approver_user_id == "admin":
                    approver_names.append("admin")
                else:
                    approver = session.get(User, approval.approver_user_id)
                    approver_names.append(approver.display_name if approver else "unknown")
            
            requests.append({
                'request': auth_req,
                'user': user,
                'approvals': len(approvals),
                'approvers': approver_names,
                'needs_approvals': max(0, int(os.getenv('PEER_APPROVAL_COUNT', '2')) - len(approvals))
            })
        
        return requests

def list_pending_requests(show_details: bool = False) -> None:
    """List all pending authentication requests"""
    requests = get_pending_requests()
    
    if not requests:
        print("No pending authentication requests.")
        return
    
    print(f"\n📋 Pending Authentication Requests ({len(requests)})")
    print("=" * 60)
    
    for i, req_info in enumerate(requests, 1):
        auth_req = req_info['request']
        user = req_info['user']
        
        # Basic info
        created_ago = format_relative_time(auth_req.created_at)
        expires_in = format_relative_time(auth_req.expires_at, future=True)
        
        print(f"\n{i}. {user.display_name}")
        print(f"   ID: {auth_req.id[:8]}...")
        print(f"   Created: {created_ago}")
        print(f"   Expires: {expires_in}")
        print(f"   Approvals: {req_info['approvals']}/{os.getenv('PEER_APPROVAL_COUNT', '2')}")
        
        if req_info['approvers']:
            print(f"   Approved by: {', '.join(req_info['approvers'])}")
        
        if show_details:
            print(f"   Device: {auth_req.device_info or 'Unknown'}")
            print(f"   IP: {auth_req.ip_address or 'Unknown'}")
            if auth_req.verification_code:
                print(f"   Verification Code: {auth_req.verification_code}")

def approve_request(request_id: str, approver: str = "admin") -> bool:
    """Approve an authentication request"""
    with Session(engine) as session:
        # Find the request (always try prefix match for convenience)
        stmt = select(AuthenticationRequest).where(
            AuthenticationRequest.id.startswith(request_id),
            AuthenticationRequest.status == "pending"
        )
        auth_req = session.exec(stmt).first()
        
        # If not found and it looks like a full ID, try exact match
        if not auth_req and len(request_id) >= 32:
            auth_req = session.get(AuthenticationRequest, request_id)
        
        if not auth_req:
            print(f"❌ Authentication request not found: {request_id}")
            return False
        
        if auth_req.status != "pending":
            print(f"❌ Request is not pending (status: {auth_req.status})")
            return False
        
        # Check if already approved by this approver
        existing_approval = session.exec(
            select(AuthApproval).where(
                AuthApproval.auth_request_id == auth_req.id,
                AuthApproval.approver_user_id == approver
            )
        ).first()
        
        if existing_approval:
            print(f"❌ Request already approved by {approver}")
            return False
        
        # Add approval
        approval = AuthApproval(
            auth_request_id=auth_req.id,
            approver_user_id=approver,
            approved_at=datetime.utcnow()
        )
        session.add(approval)
        
        # Check if we have enough approvals now
        approval_count = session.exec(
            select(AuthApproval).where(AuthApproval.auth_request_id == auth_req.id)
        ).all()
        
        required_approvals = int(os.getenv('PEER_APPROVAL_COUNT', '2'))
        
        if len(approval_count) + 1 >= required_approvals:  # +1 for the one we're adding
            auth_req.status = "approved"
            auth_req.approved_at = datetime.utcnow()
            auth_req.approved_by_user_id = approver
            print(f"✅ Request FULLY APPROVED and ready for login")
        else:
            print(f"✅ Approval added ({len(approval_count) + 1}/{required_approvals})")
        
        session.commit()
        
        # Show user info
        user = session.get(User, auth_req.user_id)
        if user:
            print(f"   User: {user.display_name}")
            print(f"   Request ID: {auth_req.id[:8]}...")
        
        return True

def reject_request(request_id: str, reason: str = None) -> bool:
    """Reject an authentication request"""
    with Session(engine) as session:
        # Find the request (always try prefix match for convenience)
        stmt = select(AuthenticationRequest).where(
            AuthenticationRequest.id.startswith(request_id),
            AuthenticationRequest.status == "pending"
        )
        auth_req = session.exec(stmt).first()
        
        # If not found and it looks like a full ID, try exact match
        if not auth_req and len(request_id) >= 32:
            auth_req = session.get(AuthenticationRequest, request_id)
        
        if not auth_req:
            print(f"❌ Authentication request not found: {request_id}")
            return False
        
        if auth_req.status != "pending":
            print(f"❌ Request is not pending (status: {auth_req.status})")
            return False
        
        auth_req.status = "rejected"
        session.commit()
        
        # Show user info
        user = session.get(User, auth_req.user_id)
        print(f"❌ Request REJECTED")
        if user:
            print(f"   User: {user.display_name}")
        print(f"   Request ID: {auth_req.id[:8]}...")
        if reason:
            print(f"   Reason: {reason}")
        
        return True

def cleanup_expired_requests() -> int:
    """Clean up expired authentication requests"""
    with Session(engine) as session:
        expired_requests = session.exec(
            select(AuthenticationRequest).where(
                AuthenticationRequest.status == "pending",
                AuthenticationRequest.expires_at < datetime.utcnow()
            )
        ).all()
        
        count = 0
        for req in expired_requests:
            req.status = "expired"
            count += 1
        
        session.commit()
        
        if count > 0:
            print(f"🧹 Cleaned up {count} expired requests")
        else:
            print("🧹 No expired requests to clean up")
        
        return count

def show_stats() -> None:
    """Show authentication request statistics"""
    with Session(engine) as session:
        # Get counts by status
        pending_count = session.exec(
            select(AuthenticationRequest).where(
                AuthenticationRequest.status == "pending",
                AuthenticationRequest.expires_at > datetime.utcnow()
            )
        ).all()
        
        approved_today = session.exec(
            select(AuthenticationRequest).where(
                AuthenticationRequest.status == "approved",
                AuthenticationRequest.approved_at > datetime.utcnow() - timedelta(days=1)
            )
        ).all()
        
        rejected_today = session.exec(
            select(AuthenticationRequest).where(
                AuthenticationRequest.status == "rejected",
                AuthenticationRequest.approved_at > datetime.utcnow() - timedelta(days=1)
            )
        ).all()
        
        print("\n📊 Authentication Request Statistics")
        print("=" * 40)
        print(f"Pending: {len(pending_count)}")
        print(f"Approved today: {len(approved_today)}")
        print(f"Rejected today: {len(rejected_today)}")

def main():
    parser = argparse.ArgumentParser(
        description="Manage ThyWill authentication requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                     # List pending requests
  %(prog)s list --details          # List with full details
  %(prog)s approve abc123          # Approve request by ID
  %(prog)s approve abc123 --by john # Approve as specific user
  %(prog)s reject abc123           # Reject request
  %(prog)s cleanup                 # Clean expired requests
  %(prog)s stats                   # Show statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List pending requests')
    list_parser.add_argument('--details', '-d', action='store_true', 
                           help='Show detailed information')
    
    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve a request')
    approve_parser.add_argument('request_id', help='Request ID (full or partial)')
    approve_parser.add_argument('--by', dest='approver', default='admin',
                               help='Approver username (default: admin)')
    
    # Reject command  
    reject_parser = subparsers.add_parser('reject', help='Reject a request')
    reject_parser.add_argument('request_id', help='Request ID (full or partial)')
    reject_parser.add_argument('--reason', help='Reason for rejection')
    
    # Cleanup command
    subparsers.add_parser('cleanup', help='Clean up expired requests')
    
    # Stats command
    subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list':
            list_pending_requests(args.details)
        elif args.command == 'approve':
            approve_request(args.request_id, args.approver)
        elif args.command == 'reject':
            reject_request(args.request_id, getattr(args, 'reason', None))
        elif args.command == 'cleanup':
            cleanup_expired_requests()
        elif args.command == 'stats':
            show_stats()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()