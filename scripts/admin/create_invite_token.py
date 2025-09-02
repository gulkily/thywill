#!/usr/bin/env python3
"""
ThyWill Invite Token Generator

Creates a new invite token for ThyWill.
Usage: python create_invite_token.py [--hours HOURS] [--max-uses MAX_USES]
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlmodel import Session

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from models import engine
from app_helpers.services.token_service import create_invite_token
from app_helpers.utils.time_formatting import format_hours_intelligently

# Load environment variables
load_dotenv()


def create_regular_token(hours=12, max_uses=1):
    """Create a new regular invite token."""
    try:
        with Session(engine) as session:
            # Create token using the service
            token_info = create_invite_token(
                created_by_user="system_cli",
                custom_expiration_hours=hours,
                max_uses=max_uses,
                token_type="new_user",
                db_session=session
            )
            session.commit()
            
        # Format the expiration time
        expires_at = token_info['expires_at']
        formatted_expiration = format_hours_intelligently(hours)
        
        print("✅ Invite token created successfully!")
        print(f"Token: {token_info['token']}")
        print(f"Max uses: {token_info['max_uses']}")
        print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC ({formatted_expiration})")
        print(f"Invite URL: https://your-domain.com/claim/{token_info['token']}")
        print("\nShare this token with new users to allow them to register.")
        
        return token_info['token']
        
    except Exception as e:
        print(f"❌ Error creating invite token: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create invite token for ThyWill")
    parser.add_argument(
        "--hours", 
        type=int, 
        default=12,
        help="Token expiration time in hours (default: 12)"
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=1,
        help="Maximum number of uses for this token (default: 1)"
    )
    
    args = parser.parse_args()
    
    if args.hours <= 0:
        print("❌ Hours must be positive")
        sys.exit(1)
        
    if args.max_uses <= 0:
        print("❌ Max uses must be positive")
        sys.exit(1)
    
    create_regular_token(args.hours, args.max_uses)


if __name__ == "__main__":
    main()