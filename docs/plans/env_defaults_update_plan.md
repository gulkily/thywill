# Generic .env Defaults Update Plan

## Overview
Create a generic process to update any ThyWill installation's `.env` file with missing default environment variables documented in CLAUDE.md.

## Approach
Rather than hardcoding specific variables, create a script that:
1. Parses CLAUDE.md to extract all documented environment variables and their defaults
2. Reads the existing .env file (if any) to see what's already configured
3. Identifies missing variables and adds them with documented defaults
4. Preserves existing configuration and comments

## Implementation Strategy

### Step 1: Create Environment Variable Parser Script
Create `tools/update_env_defaults.py` that:

```python
#!/usr/bin/env python3
"""
Generic script to update .env file with missing defaults from CLAUDE.md
Works on any ThyWill installation by parsing documentation dynamically.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

def parse_claude_md_env_vars(claude_md_path: str) -> Dict[str, Tuple[str, str]]:
    """Parse CLAUDE.md to extract environment variables and their defaults.
    
    Returns:
        Dict mapping var_name -> (default_value, description)
    """
    # Implementation to parse CLAUDE.md Environment Variables section
    # Extract variables like: VARIABLE_NAME=default_value  # description
    pass

def parse_existing_env(env_path: str) -> Dict[str, str]:
    """Parse existing .env file to see what's already configured.
    
    Returns:
        Dict mapping var_name -> current_value
    """
    # Implementation to parse existing .env file
    pass

def generate_missing_env_section(documented_vars: Dict, existing_vars: Dict) -> str:
    """Generate .env section for missing variables with proper formatting.
    
    Returns:
        Formatted .env content to append
    """
    # Implementation to generate missing sections with comments
    pass

def backup_env_file(env_path: str) -> str:
    """Create backup of existing .env file."""
    # Implementation to create timestamped backup
    pass

def update_env_file(env_path: str, missing_content: str):
    """Append missing environment variables to .env file."""
    # Implementation to safely append content
    pass

if __name__ == "__main__":
    # Main execution logic
    pass
```

### Step 2: Environment Variable Detection Logic
The script should identify these categories of variables from CLAUDE.md:

1. **Required Variables** (ANTHROPIC_API_KEY, PRODUCTION_MODE, etc.)
2. **Server Configuration** (PORT, BASE_URL, etc.)  
3. **Authentication Settings** (JWT_SECRET, MULTI_DEVICE_AUTH_ENABLED, etc.)
4. **Feature Flags** (PRAYER_CATEGORIZATION_*, etc.)
5. **Optional Configuration** (PAYPAL_USERNAME, VENMO_HANDLE, etc.)

### Step 3: Smart Default Application
- Skip variables that are already set in .env
- Use documented defaults from CLAUDE.md
- Group related variables into logical sections
- Preserve existing formatting and comments
- Add descriptive comments for each variable

### Step 4: Safe Update Process
```bash
# Usage examples:
python tools/update_env_defaults.py                    # Update current directory
python tools/update_env_defaults.py --env-path /path/to/.env
python tools/update_env_defaults.py --dry-run          # Show what would be added
python tools/update_env_defaults.py --backup-only      # Just create backup
```

## Generic Validation Process

### Automated Validation
1. **Backup Creation**: Always create timestamped backup before changes
2. **Syntax Validation**: Ensure generated .env is valid
3. **Duplicate Detection**: Prevent duplicate variable definitions
4. **Documentation Sync**: Verify all CLAUDE.md variables are handled

### Manual Validation Steps
1. Review generated backup file
2. Check that existing configuration is preserved
3. Verify new defaults match CLAUDE.md documentation
4. Test application startup with updated .env
5. Run `./thywill test` if available

## Benefits of Generic Approach

### Maintainability
- Single source of truth (CLAUDE.md) for environment variable documentation
- No hardcoded variable lists to maintain
- Automatically stays in sync with documentation updates

### Portability
- Works on any ThyWill installation
- Handles different .env file states (missing, partial, complete)
- Preserves local customizations

### Safety
- Always creates backups before changes
- Dry-run mode to preview changes
- Validates syntax before writing

## Usage Scenarios

### New Installation
```bash
# Fresh install with no .env file
python tools/update_env_defaults.py
# Creates complete .env with all documented defaults
```

### Existing Installation  
```bash
# Update existing .env with missing variables
python tools/update_env_defaults.py
# Adds only missing variables, preserves existing config
```

### Documentation Updates
```bash
# After CLAUDE.md environment variable updates
python tools/update_env_defaults.py
# Automatically picks up new documented variables
```

## Files to Create

- `tools/update_env_defaults.py` - Main update script
- `tools/env_validator.py` - Optional validation helper  
- Add usage instructions to CLAUDE.md Key Commands section