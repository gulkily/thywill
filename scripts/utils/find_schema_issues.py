#!/usr/bin/env python3
"""
Find all remaining schema migration issues in the codebase.
This will identify code that still references old field names.
"""

import os
import re
from pathlib import Path

def find_issues_in_file(file_path):
    """Find schema issues in a single file"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
            
        # Patterns to look for
        patterns = [
            (r'\.author_id\b', 'should be .author_username'),
            (r'author_id\s*=', 'should be author_username='),
            (r'\.user_id\b(?!.*PrayerActivityLog|NotificationState|AuthenticationRequest)', 'should be .username (except for some tables)'),
            (r'user_id\s*=.*PrayerMark', 'should be username= for PrayerMark'),
            (r'\.id\b.*User\(', 'User.id should be User.display_name'),
            (r'user\.id\b', 'should be user.display_name'),
            (r'existing_user\.id\b', 'should be existing_user.display_name'),
            (r'current_user\.id\b', 'should be current_user.display_name'),
            (r'invited_by_user_id', 'should be invited_by_username'),
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern, suggestion in patterns:
                if re.search(pattern, line):
                    issues.append({
                        'line': line_num,
                        'content': line.strip(),
                        'issue': suggestion,
                        'pattern': pattern
                    })
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return issues

def main():
    """Scan the codebase for schema issues"""
    root_dir = Path('/home/wsl/thywill')
    
    # Priority order for fixing
    priority_dirs = [
        'app_helpers/routes/',
        'app_helpers/services/',
        'app.py',
        'models.py'
    ]
    
    # Skip these directories
    skip_dirs = {'venv', '.git', '__pycache__', 'node_modules', 'tests'}
    
    all_issues = {}
    
    print("🔍 Scanning for Schema Migration Issues")
    print("=" * 50)
    
    # First scan priority files
    for priority_path in priority_dirs:
        full_path = root_dir / priority_path
        if full_path.is_file():
            # Single file
            issues = find_issues_in_file(full_path)
            if issues:
                all_issues[str(full_path)] = issues
        elif full_path.is_dir():
            # Directory
            for py_file in full_path.rglob('*.py'):
                issues = find_issues_in_file(py_file)
                if issues:
                    all_issues[str(py_file)] = issues
    
    # Display results by priority
    total_issues = 0
    for file_path, issues in sorted(all_issues.items()):
        print(f"\n📁 {file_path}")
        print("-" * 40)
        
        for issue in issues[:5]:  # Limit to first 5 issues per file
            print(f"  Line {issue['line']}: {issue['issue']}")
            print(f"    {issue['content']}")
            total_issues += 1
            
        if len(issues) > 5:
            print(f"    ... and {len(issues) - 5} more issues")
            
    print(f"\n📊 Summary: Found {total_issues} schema migration issues")
    
    if total_issues > 0:
        print("\n💡 Recommendations:")
        print("1. Start with files in app_helpers/routes/ and app_helpers/services/")
        print("2. Focus on .author_id and .user_id references first")
        print("3. Test each fix with: python debug_helper.py")
        print("4. Use find-and-replace in your editor for bulk changes")
    else:
        print("✅ No major schema issues found!")

if __name__ == "__main__":
    main()