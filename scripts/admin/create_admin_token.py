#!/usr/bin/env python3
"""
ThyWill Admin Token Generator

Creates a new admin invite token for ThyWill.
Usage: python create_admin_token.py [--hours HOURS]
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlmodel import Session

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from models import engine, InviteToken
from app_helpers.services.token_service import create_system_token
from app_helpers.utils.time_formatting import format_hours_intelligently

# Load environment variables
load_dotenv()


def create_admin_token(hours=12):
    """Create a new admin invite token."""
    try:
        # Use centralized token service
        invite_token = create_system_token(custom_expiration_hours=hours)
        
        # Success output
        print("✅ Admin invite token created successfully!")
        print(f"Token: {invite_token['token']}")
        print(f"Expires: {invite_token['expires_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Valid for: {format_hours_intelligently(hours)}")
        print()
        print("🔗 Claim URL:")
        base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        print(f"   {base_url}/claim/{invite_token['token']}")
        print()
        print("💡 Next steps:")
        print("   1. Visit the claim URL above")
        print("   2. Create your admin account")
        print("   3. Use the admin panel to generate invite links for other users")
        
        return invite_token['token']
        
    except Exception as e:
        print(f"❌ Error creating admin token: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Create a new admin invite token for ThyWill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_admin_token.py              # 12-hour token (default)
  python create_admin_token.py --hours 24   # 24-hour token
  python create_admin_token.py --hours 1    # 1-hour token
        """
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=12,
        help='Token expiration time in hours (default: 12)'
    )
    
    args = parser.parse_args()
    
    # Validate hours
    if args.hours <= 0:
        print("❌ Error: Hours must be greater than 0", file=sys.stderr)
        sys.exit(1)
    
    if args.hours > 168:  # 1 week
        print("⚠️  Warning: Token will expire in more than 1 week")
        confirm = input("Continue? (y/N): ")
        if confirm.lower() not in ['y', 'yes']:
            print("Cancelled.")
            sys.exit(0)
    
    print(f"🔑 Creating admin invite token (expires in {args.hours} hours)...")
    create_admin_token(args.hours)


if __name__ == "__main__":
    main()