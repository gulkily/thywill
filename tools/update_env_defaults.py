#!/usr/bin/env python3
"""
Generic script to update .env file with missing defaults from .env.example
Works on any ThyWill installation by parsing .env.example dynamically.

Usage:
    python tools/update_env_defaults.py                    # Update current directory
    python tools/update_env_defaults.py --env-path /path/to/.env
    python tools/update_env_defaults.py --dry-run          # Show what would be added
    python tools/update_env_defaults.py --backup-only      # Just create backup
"""

import re
import os
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

def parse_env_example_vars(env_example_path: str) -> Dict[str, Tuple[str, str]]:
    """Parse .env.example to extract environment variables and their defaults.
    
    Returns:
        Dict mapping var_name -> (default_value, description)
    """
    env_vars = {}
    
    try:
        with open(env_example_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_comments = []
        
        for line_num, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()
            
            # Collect comments that precede variable assignments
            if line.startswith('#'):
                comment = line.lstrip('# ').strip()
                if comment and not comment.startswith('='):  # Skip section dividers
                    current_comments.append(comment)
                continue
            
            # Skip empty lines but reset comments after a gap
            if not line:
                if current_comments and len(current_comments) > 3:  # Keep only recent comments
                    current_comments = current_comments[-2:]
                continue
            
            # Match variable assignments like VAR_NAME=value
            var_match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line)
            if var_match:
                var_name = var_match.group(1)
                var_value = var_match.group(2)
                
                # Use accumulated comments as description
                if current_comments:
                    # Take the most descriptive comment (usually the last one)
                    description = current_comments[-1]
                    # If it's too generic, try to find a better one
                    for comment in reversed(current_comments):
                        if len(comment) > 20 and not comment.startswith('When') and not comment.startswith('Example:'):
                            description = comment
                            break
                else:
                    description = f"Configuration for {var_name}"
                
                env_vars[var_name] = (var_value, description)
                current_comments = []  # Reset after processing
        
        print(f"Parsed {len(env_vars)} environment variables from .env.example")
        return env_vars
        
    except FileNotFoundError:
        print(f"Error: .env.example not found at {env_example_path}")
        return {}
    except Exception as e:
        print(f"Error parsing .env.example: {e}")
        return {}

def parse_existing_env(env_path: str) -> Dict[str, str]:
    """Parse existing .env file to see what's already configured.
    
    Returns:
        Dict mapping var_name -> current_value
    """
    existing_vars = {}
    
    if not os.path.exists(env_path):
        print(f"No existing .env file found at {env_path}")
        return existing_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Match variable assignments
            var_match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line)
            if var_match:
                var_name = var_match.group(1)
                var_value = var_match.group(2)
                existing_vars[var_name] = var_value
        
        print(f"Found {len(existing_vars)} existing environment variables")
        return existing_vars
        
    except Exception as e:
        print(f"Error parsing existing .env file: {e}")
        return {}

def categorize_env_vars(documented_vars: Dict[str, Tuple[str, str]]) -> Dict[str, List[Tuple[str, str, str]]]:
    """Categorize environment variables by type for organized output.
    
    Returns:
        Dict mapping category -> [(var_name, default_value, description), ...]
    """
    categories = {
        "Required Configuration": [],
        "Server Configuration": [],
        "Authentication & Security": [],
        "Migration Settings": [],
        "Prayer Categorization Feature Flags": [],
        "Optional Configuration": [],
        "Development & Testing": []
    }
    
    # Categorization rules
    required_vars = {"ANTHROPIC_API_KEY", "PRODUCTION_MODE"}
    server_vars = {"PORT", "BASE_URL", "ENVIRONMENT"}
    auth_vars = {"JWT_SECRET", "MULTI_DEVICE_AUTH_ENABLED", "REQUIRE_APPROVAL_FOR_EXISTING_USERS", 
                 "PEER_APPROVAL_COUNT", "REQUIRE_VERIFICATION_CODE", "INVITE_TOKEN_EXPIRATION_HOURS",
                 "REQUIRE_INVITE_LOGIN_VERIFICATION", "SESSION_DAYS"}
    migration_vars = {"AUTO_MIGRATE_ON_STARTUP", "DEFAULT_INVITE_MAX_USES"}
    categorization_vars = {var for var in documented_vars.keys() if "PRAYER_CATEGORIZATION" in var or "CATEGORIZATION" in var or "SAFETY" in var or "SPECIFICITY" in var}
    optional_vars = {"PAYPAL_USERNAME", "VENMO_HANDLE", "TEXT_ARCHIVE_ENABLED", "TEXT_ARCHIVE_BASE_DIR", 
                     "TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS", "EXPORT_RATE_LIMIT_MINUTES", "EXPORT_CACHE_TTL_MINUTES"}
    
    for var_name, (default_val, description) in documented_vars.items():
        if var_name in required_vars:
            categories["Required Configuration"].append((var_name, default_val, description))
        elif var_name in server_vars:
            categories["Server Configuration"].append((var_name, default_val, description))
        elif var_name in auth_vars:
            categories["Authentication & Security"].append((var_name, default_val, description))
        elif var_name in migration_vars:
            categories["Migration Settings"].append((var_name, default_val, description))
        elif var_name in categorization_vars:
            categories["Prayer Categorization Feature Flags"].append((var_name, default_val, description))
        elif var_name in optional_vars:
            categories["Optional Configuration"].append((var_name, default_val, description))
        else:
            categories["Development & Testing"].append((var_name, default_val, description))
    
    # Remove empty categories
    return {category: vars_list for category, vars_list in categories.items() if vars_list}

def generate_missing_env_section(documented_vars: Dict[str, Tuple[str, str]], existing_vars: Dict[str, str]) -> str:
    """Generate .env section for missing variables with proper formatting.
    
    Returns:
        Formatted .env content to append
    """
    # Find missing variables
    missing_vars = {
        var_name: (default_val, description) 
        for var_name, (default_val, description) in documented_vars.items()
        if var_name not in existing_vars
    }
    
    if not missing_vars:
        return ""
    
    print(f"Found {len(missing_vars)} missing environment variables")
    
    # Categorize missing variables
    categorized_missing = categorize_env_vars(missing_vars)
    
    # Generate formatted output
    output_lines = [
        "",
        "# ========================================",
        "# MISSING ENVIRONMENT VARIABLES",
        "# ========================================",
        "# The following variables were added automatically from .env.example",
        f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    for category, vars_list in categorized_missing.items():
        if not vars_list:
            continue
            
        output_lines.extend([
            f"# ========================================",
            f"# {category.upper()}",
            f"# ========================================",
            ""
        ])
        
        for var_name, default_val, description in vars_list:
            # Add description as comment
            if description:
                output_lines.append(f"# {description}")
            
            # Add the variable assignment
            output_lines.append(f"{var_name}={default_val}")
            output_lines.append("")
    
    return "\n".join(output_lines)

def backup_env_file(env_path: str) -> Optional[str]:
    """Create backup of existing .env file.
    
    Returns:
        Path to backup file or None if no file to backup
    """
    if not os.path.exists(env_path):
        print("No existing .env file to backup")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{env_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(env_path, backup_path)
        print(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None

def update_env_file(env_path: str, missing_content: str, dry_run: bool = False):
    """Append missing environment variables to .env file."""
    if dry_run:
        print("\n=== DRY RUN - Content that would be added ===")
        print(missing_content)
        print("=== END DRY RUN ===\n")
        return
    
    try:
        with open(env_path, 'a', encoding='utf-8') as f:
            f.write(missing_content)
        print(f"Successfully updated {env_path}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

def validate_env_syntax(env_path: str) -> bool:
    """Basic validation of .env file syntax."""
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Check for valid variable assignment
            if '=' not in line:
                print(f"Warning: Line {line_num} doesn't appear to be a valid assignment: {line}")
                continue
            
            var_name = line.split('=')[0]
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', var_name):
                print(f"Warning: Line {line_num} has invalid variable name: {var_name}")
        
        return True
    except Exception as e:
        print(f"Error validating .env syntax: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Update .env file with missing defaults from .env.example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/update_env_defaults.py                    # Update current directory
  python tools/update_env_defaults.py --env-path /path/to/.env
  python tools/update_env_defaults.py --dry-run          # Show what would be added
  python tools/update_env_defaults.py --backup-only      # Just create backup
        """
    )
    
    parser.add_argument(
        '--env-path',
        default='.env',
        help='Path to .env file (default: .env in current directory)'
    )
    
    parser.add_argument(
        '--env-example-path',
        default='.env.example',
        help='Path to .env.example file (default: .env.example in current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be added without making changes'
    )
    
    parser.add_argument(
        '--backup-only',
        action='store_true',
        help='Only create backup, do not update file'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Convert relative paths to absolute
    env_path = os.path.abspath(args.env_path)
    env_example_path = os.path.abspath(args.env_example_path)
    
    print(f"ThyWill Environment Defaults Updater")
    print(f"Environment file: {env_path}")
    print(f"Template file: {env_example_path}")
    print()
    
    # Parse documented environment variables
    documented_vars = parse_env_example_vars(env_example_path)
    if not documented_vars:
        print("No environment variables found in .env.example. Exiting.")
        return 1
    
    # Parse existing environment variables
    existing_vars = parse_existing_env(env_path)
    
    # Create backup if requested and file exists
    if not args.no_backup and os.path.exists(env_path):
        backup_path = backup_env_file(env_path)
        if args.backup_only:
            print("Backup created. Exiting as requested.")
            return 0
    
    # Generate missing content
    missing_content = generate_missing_env_section(documented_vars, existing_vars)
    
    if not missing_content:
        print("No missing environment variables found. Your .env file is up to date!")
        return 0
    
    # Update the file
    update_env_file(env_path, missing_content, args.dry_run)
    
    if not args.dry_run:
        # Validate syntax
        if validate_env_syntax(env_path):
            print("Environment file validation passed.")
        
        print("\nUpdate complete! Please review the changes and test your application.")
        print("Consider running './thywill test' to ensure no breaking changes.")
    
    return 0

if __name__ == "__main__":
    exit(main())