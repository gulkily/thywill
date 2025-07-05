#!/usr/bin/env bats

# Tests for ThyWill CLI admin token command
# Tests the integration between CLI and standalone script

load '../test_helper/common'

setup() {
    setup_test_environment
}

teardown() {
    cleanup_test_environment
}

@test "admin-token command creates valid token" {
    run ./thywill admin-token
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Admin invite token created successfully!"* ]]
    [[ "$output" == *"Token:"* ]]
    [[ "$output" == *"Expires:"* ]]
    [[ "$output" == *"Claim URL:"* ]]
}

@test "admin-token command with custom hours" {
    run ./thywill admin-token --hours 24
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Admin invite token created successfully!"* ]]
    [[ "$output" == *"Valid for: 24 hours"* ]]
}

@test "admin-token command with minimal hours" {
    run ./thywill admin-token --hours 1
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"Valid for: 1 hours"* ]]
}

@test "admin-token command shows proper URL format" {
    run ./thywill admin-token
    
    [ "$status" -eq 0 ]
    
    # Extract token from output
    token=$(echo "$output" | grep "Token:" | cut -d' ' -f2)
    
    # Should be 16 character hex token
    [[ ${#token} -eq 16 ]]
    [[ "$token" =~ ^[0-9a-f]{16}$ ]]
    
    # Should show proper claim URL
    [[ "$output" == *"/claim/$token"* ]]
}

@test "admin-token command uses standalone script" {
    # Test that CLI calls the standalone script instead of embedded code
    
    # Mock the standalone script to verify it's called
    mv scripts/admin/create_admin_token.py scripts/admin/create_admin_token.py.bak
    cat > scripts/admin/create_admin_token.py << 'EOF'
#!/usr/bin/env python3
import sys
print("STANDALONE_SCRIPT_CALLED")
print("Args:", sys.argv)
EOF
    chmod +x scripts/admin/create_admin_token.py
    
    run ./thywill admin-token --hours 6
    
    # Restore original script
    mv scripts/admin/create_admin_token.py.bak scripts/admin/create_admin_token.py
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"STANDALONE_SCRIPT_CALLED"* ]]
    [[ "$output" == *"--hours"* ]]
    [[ "$output" == *"6"* ]]
}

@test "admin-token command passes through all arguments" {
    # Mock script to capture arguments
    mv scripts/admin/create_admin_token.py scripts/admin/create_admin_token.py.bak
    cat > scripts/admin/create_admin_token.py << 'EOF'
#!/usr/bin/env python3
import sys
print("Script called with args:", " ".join(sys.argv[1:]))
EOF
    chmod +x scripts/admin/create_admin_token.py
    
    run ./thywill admin-token --hours 48
    
    # Restore original script
    mv scripts/admin/create_admin_token.py.bak scripts/admin/create_admin_token.py
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"--hours 48"* ]]
}

@test "admin-token command handles script errors" {
    # Mock script that exits with error
    mv scripts/admin/create_admin_token.py scripts/admin/create_admin_token.py.bak
    cat > scripts/admin/create_admin_token.py << 'EOF'
#!/usr/bin/env python3
import sys
print("Error creating admin token", file=sys.stderr)
sys.exit(1)
EOF
    chmod +x scripts/admin/create_admin_token.py
    
    run ./thywill admin-token
    
    # Restore original script
    mv scripts/admin/create_admin_token.py.bak scripts/admin/create_admin_token.py
    
    [ "$status" -eq 1 ]
    [[ "$output" == *"Error creating admin token"* ]]
}

@test "admin-token command without arguments uses defaults" {
    run ./thywill admin-token
    
    [ "$status" -eq 0 ]
    # Should use default 12 hours
    [[ "$output" == *"Valid for: 12 hours"* ]]
}

@test "admin-token help shows usage" {
    run ./thywill admin-token --help
    
    [ "$status" -eq 0 ]
    [[ "$output" == *"usage:"* ]] || [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"hours"* ]]
}

@test "admin-token generates unique tokens on multiple calls" {
    # Run twice and extract tokens
    run ./thywill admin-token
    [ "$status" -eq 0 ]
    token1=$(echo "$output" | grep "Token:" | cut -d' ' -f2)
    
    run ./thywill admin-token
    [ "$status" -eq 0 ]
    token2=$(echo "$output" | grep "Token:" | cut -d' ' -f2)
    
    # Tokens should be different
    [ "$token1" != "$token2" ]
    
    # Both should be valid 16-char hex
    [[ ${#token1} -eq 16 ]]
    [[ ${#token2} -eq 16 ]]
    [[ "$token1" =~ ^[0-9a-f]{16}$ ]]
    [[ "$token2" =~ ^[0-9a-f]{16}$ ]]
}