#!/usr/bin/env python3
"""
Template Field Validation Script

This script validates that template field references match actual model definitions,
helping prevent issues like using non-existent fields (e.g., user.id instead of user.display_name).
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Model field definitions based on actual ThyWill models
MODEL_FIELDS = {
    'User': {
        'display_name',  # Primary key
        'created_at',
        'invited_by_username',
        'invite_token_used',
        'welcome_message_dismissed',
        'text_file_path',
        'is_admin'  # Method, not field
    },
    'Prayer': {
        'id',
        'author_username',  # NOT author_id
        'text',
        'generated_prayer',
        'project_tag',
        'created_at',
        'flagged',
        'text_file_path'
    },
    'PrayerMark': {
        'id',
        'prayer_id',
        'username',  # NOT user_id
        'created_at'
    },
    'Session': {
        'id',
        'username',
        'device_fingerprint',
        'created_at',
        'expires_at',
        'is_active'
    }
}

# Common field name errors
FIELD_CORRECTIONS = {
    'user.id': 'user.display_name',
    'author_id': 'author_username (in Prayer model)',
    'user_id': 'username (in PrayerMark model)',
    'me.id': 'me.display_name'
}

def find_template_files(directory: str = "templates") -> List[Path]:
    """Find all HTML template files."""
    template_dir = Path(directory)
    if not template_dir.exists():
        print(f"Template directory '{directory}' not found")
        return []
    
    return list(template_dir.rglob("*.html"))

def extract_field_references(content: str) -> Set[str]:
    """Extract field references from template content."""
    # Pattern to match template variable field access: {{ var.field }}, {% if var.field %}
    patterns = [
        r'\{\{\s*(\w+(?:\.\w+)+)',  # {{ var.field }}
        r'\{\%\s*if\s+(\w+(?:\.\w+)+)',  # {% if var.field %}
        r'\{\%\s*elif\s+(\w+(?:\.\w+)+)',  # {% elif var.field %}
        r'href="[^"]*\{\{\s*(\w+(?:\.\w+)+)',  # href="/user/{{ var.field }}"
        r'onclick="[^"]*\{\{\s*(\w+(?:\.\w+)+)',  # onclick="func('{{ var.field }}')"
    ]
    
    references = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        references.update(matches)
    
    return references

def validate_field_reference(ref: str) -> Tuple[bool, str]:
    """Validate a single field reference against model definitions."""
    parts = ref.split('.')
    if len(parts) < 2:
        return True, ""  # Not a field reference
    
    var_name = parts[0]
    field_chain = parts[1:]
    
    # Check for common problematic patterns
    if ref in FIELD_CORRECTIONS:
        return False, f"Use '{FIELD_CORRECTIONS[ref]}' instead of '{ref}'"
    
    # Check user field references
    if var_name in ['user', 'me', 'profile_user'] and field_chain[0] == 'id':
        return False, f"User model has no 'id' field. Use 'display_name' instead: {var_name}.display_name"
    
    # Check prayer field references
    if var_name in ['prayer', 'p'] and field_chain[0] == 'author_id':
        return False, f"Prayer model uses 'author_username', not 'author_id': {var_name}.author_username"
    
    # Check nested user references
    if len(field_chain) >= 2 and field_chain[0] == 'user' and field_chain[1] == 'id':
        return False, f"User model has no 'id' field. Use 'display_name' instead: {var_name}.user.display_name"
    
    return True, ""

def validate_template_file(file_path: Path) -> List[Dict]:
    """Validate a single template file."""
    issues = []
    
    try:
        content = file_path.read_text()
        references = extract_field_references(content)
        
        for ref in references:
            is_valid, error_msg = validate_field_reference(ref)
            if not is_valid:
                # Find line number
                lines = content.split('\n')
                line_num = 1
                for i, line in enumerate(lines, 1):
                    if ref in line:
                        line_num = i
                        break
                
                issues.append({
                    'file': str(file_path),
                    'line': line_num,
                    'reference': ref,
                    'error': error_msg
                })
    
    except Exception as e:
        issues.append({
            'file': str(file_path),
            'line': 0,
            'reference': '',
            'error': f"Error reading file: {e}"
        })
    
    return issues

def main():
    """Main validation function."""
    print("🔍 ThyWill Template Field Validation")
    print("=" * 50)
    
    # Find template files
    template_files = find_template_files()
    if not template_files:
        print("No template files found")
        return
    
    print(f"Found {len(template_files)} template files")
    
    # Validate each file
    all_issues = []
    for template_file in template_files:
        issues = validate_template_file(template_file)
        all_issues.extend(issues)
    
    # Report results
    if not all_issues:
        print("\n✅ All templates validated successfully!")
        print("No field reference issues found.")
        return
    
    print(f"\n❌ Found {len(all_issues)} issues:")
    print()
    
    for issue in sorted(all_issues, key=lambda x: (x['file'], x['line'])):
        print(f"📄 {issue['file']}:{issue['line']}")
        print(f"   Reference: {issue['reference']}")
        print(f"   Issue: {issue['error']}")
        print()
    
    # Summary by issue type
    error_types = {}
    for issue in all_issues:
        error_key = issue['error'].split(':')[0] if ':' in issue['error'] else issue['error']
        error_types[error_key] = error_types.get(error_key, 0) + 1
    
    print("📊 Issue Summary:")
    for error_type, count in sorted(error_types.items()):
        print(f"   {error_type}: {count} occurrences")
    
    sys.exit(1)

if __name__ == "__main__":
    main()