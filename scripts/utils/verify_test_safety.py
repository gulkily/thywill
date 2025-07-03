#!/usr/bin/env python3
"""
Test Safety Verification Script

This script verifies that all tests use temporary directories and never touch
the production text_archives directory.
"""

import re
import os
from pathlib import Path

def check_file_safety(file_path):
    """Check if a test file is safe (uses temp directories)"""
    issues = []
    
    try:
        content = Path(file_path).read_text()
        
        # Check for dangerous patterns
        dangerous_patterns = [
            (r'["\']\.?/?text_archives["\']', 'Direct reference to text_archives directory'),
            (r'TEXT_ARCHIVE_BASE_DIR\s*=\s*["\']\.?/?text_archives["\']', 'Sets TEXT_ARCHIVE_BASE_DIR to production'),
            (r'base_dir\s*=\s*["\']\.?/?text_archives["\']', 'Sets base_dir to production'),
            (r'archive_dir\s*=\s*["\']\.?/?text_archives["\']', 'Sets archive_dir to production'),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"DANGER: {description}")
        
        # Check for safety patterns
        safe_patterns = [
            r'tempfile\.mkdtemp\(\)',
            r'TEXT_ARCHIVE_BASE_DIR.*tempfile\.mkdtemp\(\)',
            r'base_dir.*temp',
            r'temp_dir.*=',
        ]
        
        has_safety = any(re.search(pattern, content, re.IGNORECASE) for pattern in safe_patterns)
        
        # Check if it's an archive-related test
        archive_related = any(keyword in content.lower() for keyword in [
            'textarchiveservice', 'archive_first_service', 'text_archive_service', 
            'text_importer_service', 'create_prayer_with_text_archive', 
            'append_prayer_activity_with_archive', 'import_from_archive_directory'
        ])
        
        if archive_related and not has_safety:
            issues.append("WARNING: Archive-related test without clear temp directory usage")
        
        return issues
        
    except Exception as e:
        return [f"ERROR: Could not read file: {e}"]

def main():
    print("🔍 Test Safety Verification")
    print("=" * 50)
    
    # Find all test files
    test_files = []
    
    # Root level test files
    for file in Path('.').glob('test_*.py'):
        test_files.append(file)
    
    # Tests directory
    tests_dir = Path('./tests')
    if tests_dir.exists():
        for file in tests_dir.rglob('test_*.py'):
            test_files.append(file)
    
    print(f"📄 Found {len(test_files)} test files")
    
    total_issues = 0
    files_with_issues = 0
    
    for test_file in test_files:
        issues = check_file_safety(test_file)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"\n⚠️  {test_file}:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"✅ {test_file.name}")
    
    print(f"\n📊 Summary:")
    print(f"  • Total files checked: {len(test_files)}")
    print(f"  • Files with issues: {files_with_issues}")
    print(f"  • Total issues: {total_issues}")
    
    if total_issues == 0:
        print(f"\n🎉 All tests are SAFE! No production archive access detected.")
        return True
    else:
        print(f"\n⚠️  ISSUES FOUND! Please review and fix the problems above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)