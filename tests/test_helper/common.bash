#!/bin/bash

# Common test helper functions for ThyWill CLI testing

# Setup test environment
setup_test_environment() {
    # Create unique test directory
    export TEST_DIR="/tmp/thywill_test_$$_$RANDOM"
    mkdir -p "$TEST_DIR"
    
    # Save original directory
    export ORIG_DIR="$PWD"
    
    # Change to test directory
    cd "$TEST_DIR"
    
    # Copy essential files for testing
    cp "$ORIG_DIR/thywill" ./
    chmod +x ./thywill
    
    # Create minimal files to satisfy directory checks
    touch models.py
    touch thywill.db
    touch import_community_data.py
    chmod +x import_community_data.py
    
    # Create deployment directory structure
    mkdir -p deployment
    touch deployment/deploy.sh
    
    # Create mock backup management script
    cat > deployment/backup_management.sh << 'EOF'
#!/bin/bash
case "$1" in
    list)
        echo "Available Backups:"
        echo "  thywill_backup_123.db"
        ;;
    cleanup)
        echo "Cleaning up old backups..."
        ;;
    *)
        echo "Mock backup management: $*"
        ;;
esac
EOF
    chmod +x deployment/*.sh
}

# Cleanup test environment
cleanup_test_environment() {
    # Return to original directory
    cd "$ORIG_DIR"
    
    # Remove test directory
    rm -rf "$TEST_DIR"
}

# Mock external commands that CLI depends on
setup_mocks() {
    # Mock Python to avoid database operations
    function python3() {
        case "$1" in
            "-c")
                # Mock specific Python operations based on script content
                if [[ "$2" == *"Role-based system"* ]]; then
                    echo "👑 Admin Users (Role-based system):"
                    echo "   • Test Admin"
                    echo "     ID: test123..."
                    echo "     Roles: admin"
                    return 0
                elif [[ "$2" == *"admin token"* ]]; then
                    echo "✅ Admin invite token created successfully!"
                    echo "Token: test-token-123"
                    echo "Expires: 2024-12-07 12:00:00 UTC"
                    echo "🔗 Claim URL:"
                    echo "   http://127.0.0.1:8000/claim/test-token-123"
                    return 0
                elif [[ "$2" == *"role.name"* ]]; then
                    echo "📋 admin 🔒"
                    echo "   Description: Full administrative access"
                    echo "   Users: 1"
                    echo "📋 user 🔒"
                    echo "   Description: Standard user permissions"
                    echo "   Users: 5"
                    return 0
                elif [[ "$2" == *"prayer"* ]]; then
                    echo "✅ Prayer import completed!"
                    echo "   Imported: 10 prayers"
                    return 0
                fi
                ;;
            "import_community_data.py")
                echo "🚀 ThyWill Community Data Import"
                echo "========================================="
                echo "📦 Export Info:"
                echo "   Date: 2024-12-06T10:00:00Z"
                echo "   Version: 1.0"
                echo "   Format: Individual files"
                echo "✅ Import completed successfully"
                return 0
                ;;
        esac
        # Default mock response
        echo "Mocked python3 $*"
        return 0
    }
    export -f python3
    
    # Mock system commands
    function systemctl() {
        case "$1" in
            "is-active")
                echo "active"
                return 0
                ;;
            "status")
                echo "● thywill.service - ThyWill Prayer Application"
                echo "   Loaded: loaded (/etc/systemd/system/thywill.service; enabled)"
                echo "   Active: active (running) since Mon 2024-12-06 10:00:00 UTC"
                return 0
                ;;
            *)
                echo "Mocked systemctl $*"
                return 0
                ;;
        esac
    }
    export -f systemctl
    
    function journalctl() {
        echo "Dec 06 10:00:00 server thywill[1234]: Application started successfully"
        echo "Dec 06 10:00:01 server thywill[1234]: Health check endpoint active"
        return 0
    }
    export -f journalctl
    
    function curl() {
        if [[ "$*" == *"/health"* ]]; then
            echo '{"status": "healthy", "timestamp": "2024-12-06T10:00:00Z"}'
            return 0
        fi
        echo "Mocked curl $*"
        return 0
    }
    export -f curl
    
    function uvicorn() {
        echo "INFO:     Started server process [1234]"
        echo "INFO:     Uvicorn running on http://127.0.0.1:8000"
        return 0
    }
    export -f uvicorn
}

# Create test fixtures
create_test_fixtures() {
    # Create a sample export ZIP file
    cat > sample_export.json << 'EOF'
{
  "export_metadata": {
    "version": "1.0",
    "export_date": "2024-12-06T10:00:00Z",
    "source_instance": "test_community"
  },
  "users": [
    {
      "id": "test_user_1",
      "display_name": "Test User",
      "religious_preference": "christian"
    }
  ],
  "prayers": [
    {
      "id": "test_prayer_1",
      "author_id": "test_user_1",
      "text": "Test prayer request"
    }
  ]
}
EOF
    
    # Create sample prayers JSON
    cat > sample_prayers.json << 'EOF'
[
  {
    "text": "Please pray for healing",
    "generated_prayer": "Lord, we pray for healing...",
    "author_name": "Test User",
    "target_audience": "all"
  }
]
EOF
    
    # Create a mock ZIP file (just rename JSON for testing)
    cp sample_export.json sample_export.zip
}

# Utility function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate CLI output contains expected patterns
assert_output_contains() {
    local expected="$1"
    if [[ "$output" != *"$expected"* ]]; then
        echo "Expected output to contain: $expected"
        echo "Actual output: $output"
        return 1
    fi
}

# Function to validate CLI output does not contain patterns
assert_output_not_contains() {
    local not_expected="$1"
    if [[ "$output" == *"$not_expected"* ]]; then
        echo "Expected output to NOT contain: $not_expected"
        echo "Actual output: $output"
        return 1
    fi
}

# Function to create minimal database-like environment
setup_minimal_db_environment() {
    # Create basic sqlite database file
    touch thywill.db
    
    # Create minimal models.py that satisfies import checks
    cat > models.py << 'EOF'
# Minimal models.py for testing
from sqlalchemy import create_engine
engine = create_engine("sqlite:///thywill.db")
EOF
    
    # Create minimal import script
    cat > import_community_data.py << 'EOF'
#!/usr/bin/env python3
import sys
print("🚀 ThyWill Community Data Import")
print("✅ Mock import completed successfully")
sys.exit(0)
EOF
    chmod +x import_community_data.py
}