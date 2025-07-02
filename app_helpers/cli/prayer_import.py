#!/usr/bin/env python3
"""
Prayer Import CLI Module

Handles importing prayers from JSON files with user creation.
Can be run independently or called from the CLI script.
"""

import sys
import json
import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select
from models import engine, User, Prayer


def find_or_create_user(session: Session, prayer_data: Dict[str, Any]) -> User:
    """
    Find existing user or create new one based on prayer data.
    
    Args:
        session: Database session
        prayer_data: Prayer data containing author information
        
    Returns:
        User object (existing or newly created)
    """
    author_id = prayer_data.get('author_id')
    author_name = prayer_data.get('author_name', 'Imported User')
    
    author = None
    
    # First try to find by existing ID
    if author_id:
        stmt = select(User).where(User.id == author_id)
        author = session.exec(stmt).first()
    
    # Then try to find by display name
    if not author:
        stmt = select(User).where(User.display_name == author_name)
        author = session.exec(stmt).first()
    
    # Create new user if not found
    if not author:
        author = User(
            id=uuid.uuid4().hex,
            display_name=author_name,
            religious_preference=prayer_data.get('religious_preference', 'unspecified')
        )
        session.add(author)
        session.flush()  # Get the ID
    
    return author


def parse_created_at(created_at_str: Optional[str]) -> datetime:
    """
    Parse created_at string to datetime, falling back to current time.
    
    Args:
        created_at_str: ISO format datetime string
        
    Returns:
        Parsed datetime or current time if parsing fails
    """
    if not created_at_str:
        return datetime.utcnow()
    
    try:
        return datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
    except:
        return datetime.utcnow()


def import_prayers_from_json(file_path: str) -> Dict[str, int]:
    """
    Import prayers from a JSON file.
    
    Args:
        file_path: Path to JSON file containing prayer data
        
    Returns:
        Dict containing import statistics
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Validate JSON first
    try:
        with open(file_path, 'r') as f:
            prayers_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {e}")
    
    if not isinstance(prayers_data, list):
        raise ValueError("JSON file must contain an array of prayer objects")
    
    stats = {
        'imported': 0,
        'skipped': 0,
        'errors': 0,
        'total': len(prayers_data)
    }
    
    with Session(engine) as session:
        for i, prayer_data in enumerate(prayers_data):
            try:
                # Validate required fields
                if 'text' not in prayer_data:
                    print(f'⚠️  Skipping prayer {i+1}: missing "text" field')
                    stats['skipped'] += 1
                    continue
                
                # Find or create user
                author = find_or_create_user(session, prayer_data)
                
                # Parse created_at
                created_at = parse_created_at(prayer_data.get('created_at'))
                
                # Create prayer
                prayer = Prayer(
                    id=uuid.uuid4().hex,
                    author_id=author.id,
                    text=prayer_data['text'],
                    generated_prayer=prayer_data.get('generated_prayer'),
                    project_tag=prayer_data.get('project_tag'),
                    target_audience='all',  # All prayers use target_audience='all'
                    created_at=created_at
                )
                
                session.add(prayer)
                stats['imported'] += 1
                
                if stats['imported'] % 100 == 0:
                    print(f'   Imported {stats["imported"]} prayers...')
                
            except Exception as e:
                print(f'❌ Error importing prayer {i+1}: {e}')
                stats['errors'] += 1
                continue
        
        # Commit all changes
        session.commit()
    
    return stats


def print_import_results(stats: Dict[str, int]) -> None:
    """Print formatted import results."""
    print()
    print('✅ Prayer import completed!')
    print(f'   Imported: {stats["imported"]} prayers')
    if stats['skipped'] > 0:
        print(f'   Skipped: {stats["skipped"]} prayers (missing data)')
    if stats['errors'] > 0:
        print(f'   Errors: {stats["errors"]} prayers (failed to import)')


def print_usage():
    """Print usage information."""
    print("Usage: python prayer_import.py <json_file>")
    print("")
    print("Expected JSON format:")
    print('[')
    print('  {')
    print('    "text": "Prayer request text",')
    print('    "generated_prayer": "Generated prayer response",')
    print('    "author_name": "User Display Name",')
    print('    "author_id": "existing_user_id (optional)",')
    print('    "project_tag": "optional tag",')
    print('    "target_audience": "all",')
    print('    "created_at": "2023-12-01T10:00:00"')
    print('  }')
    print(']')


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"📥 Importing Prayers from {file_path}")
    print("=" * 50)
    
    try:
        print("🔍 Validating JSON file...")
        
        print("📥 Importing prayers...")
        stats = import_prayers_from_json(file_path)
        
        print_import_results(stats)
        
        # Exit with error code if there were any errors
        if stats['errors'] > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Error importing prayers: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()