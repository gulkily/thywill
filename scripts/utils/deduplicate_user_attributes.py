#!/usr/bin/env python3
"""
Deduplicate User Attributes Script

This script removes duplicate entries from text_archives/users/user_attributes.txt
keeping only the most recent entry for each user.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

def parse_user_attributes(file_path: Path) -> Dict[str, Dict[str, str]]:
    """Parse user attributes file and return dict of username -> attributes."""
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return {}
    
    users = {}
    current_user = None
    current_attrs = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and header
            if not line or line.startswith('User Attributes'):
                continue
            
            # Check if this is a username line
            if line.startswith('username: '):
                # Save previous user if exists
                if current_user:
                    users[current_user] = current_attrs.copy()
                
                # Start new user
                current_user = line.split('username: ', 1)[1]
                current_attrs = {}
                
            elif current_user and ': ' in line:
                # Parse attribute line
                key, value = line.split(': ', 1)
                current_attrs[key] = value
            
            elif current_user:
                # This might be a continuation or malformed line
                print(f"⚠️  Warning: Unexpected line {line_num}: {line}")
    
    # Save last user
    if current_user:
        users[current_user] = current_attrs.copy()
    
    return users

def write_user_attributes(file_path: Path, users: Dict[str, Dict[str, str]]) -> None:
    """Write deduplicated user attributes to file."""
    # Create backup
    backup_path = file_path.with_suffix('.txt.backup')
    if file_path.exists():
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
    
    # Write deduplicated file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("User Attributes\n\n")
        
        # Sort users by username for consistent output
        for username in sorted(users.keys()):
            attrs = users[username]
            f.write(f"username: {username}\n")
            
            # Write attributes in consistent order
            for key in sorted(attrs.keys()):
                f.write(f"{key}: {attrs[key]}\n")
            
            f.write("\n")  # Empty line between users

def deduplicate_user_attributes(file_path: Path, dry_run: bool = False) -> bool:
    """Deduplicate user attributes file."""
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"🔍 Analyzing user attributes file: {file_path}")
    
    # Parse current file
    users = parse_user_attributes(file_path)
    
    if not users:
        print("❌ No users found in file")
        return False
    
    # Count original entries (by counting username lines)
    original_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('username: '):
                original_count += 1
    
    deduplicated_count = len(users)
    
    print(f"📊 Original entries: {original_count}")
    print(f"📊 After deduplication: {deduplicated_count}")
    
    if original_count == deduplicated_count:
        print("✅ No duplicates found - file is already clean")
        return True
    
    print(f"🔧 Removing {original_count - deduplicated_count} duplicate entries")
    
    if dry_run:
        print("🔍 DRY RUN - Would deduplicate but not writing changes")
        return True
    
    # Write deduplicated file
    write_user_attributes(file_path, users)
    print(f"✅ Successfully deduplicated {file_path}")
    print(f"💾 Backup saved as: {file_path.with_suffix('.txt.backup')}")
    
    return True

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deduplicate user attributes file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--file', type=str, help='Path to user attributes file (default: text_archives/users/user_attributes.txt)')
    args = parser.parse_args()
    
    # Determine file path
    if args.file:
        file_path = Path(args.file)
    else:
        file_path = Path('text_archives/users/user_attributes.txt')
    
    print("🧹 User Attributes Deduplication Tool")
    print("=" * 40)
    
    success = deduplicate_user_attributes(file_path, args.dry_run)
    
    if success:
        print("\n✅ Deduplication completed successfully!")
        if not args.dry_run:
            print("💡 You can now run './thywill import-all' to update the database")
    else:
        print("\n❌ Deduplication failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()