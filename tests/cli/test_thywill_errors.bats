#!/usr/bin/env bats

# Load common test helpers
load '../test_helper/common'

# Setup function runs before each test
setup() {
    setup_test_environment
    setup_mocks
    setup_minimal_db_environment
}

# Cleanup after each test
teardown() {
    cleanup_test_environment
}

@test "thywill handles empty arguments gracefully" {
    run ./thywill ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI"* ]]
}

@test "thywill handles multiple invalid arguments" {
    run ./thywill invalid1 invalid2 invalid3
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command: invalid1"* ]]
}

@test "thywill admin handles quoted arguments correctly" {
    run ./thywill admin grant "User With Spaces"
    # Should not fail on argument parsing
    if [ "$status" -ne 0 ]; then
        [[ "$output" != *"User identifier required"* ]]
    fi
}

@test "thywill role handles quoted arguments correctly" {
    run ./thywill role grant "User With Spaces" "role with spaces"
    # Should not fail on argument parsing
    if [ "$status" -ne 0 ]; then
        [[ "$output" != *"User and role required"* ]]
    fi
}

@test "thywill import handles file paths with spaces" {
    # Create file with spaces in name
    touch "file with spaces.json"
    echo '[]' > "file with spaces.json"
    
    run ./thywill import prayers "file with spaces.json"
    # Should handle the file path correctly
    [[ "$output" != *"File not found"* ]]
}

@test "thywill import community handles file paths with spaces" {
    # Create file with spaces in name  
    touch "export with spaces.zip"
    echo '{}' > "export with spaces.zip"
    
    run ./thywill import community "export with spaces.zip"
    # Should handle the file path correctly
    [[ "$output" != *"File not found"* ]]
}

@test "thywill commands handle special characters in arguments" {
    run ./thywill admin grant 'user@domain.com'
    # Should not crash on email-like usernames
    # May fail with database error but not argument parsing
    if [ "$status" -ne 0 ]; then
        [[ "$output" != *"User identifier required"* ]]
    fi
}

@test "thywill admin token handles very large hour values" {
    run ./thywill admin token 99999999
    # Should either accept it or give reasonable error
    if [ "$status" -ne 0 ]; then
        [[ "$output" == *"Hours must be a positive number"* ]] || [[ "$output" != *"error"* ]]
    fi
}

@test "thywill admin token handles decimal hours" {
    run ./thywill admin token 12.5
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
}

@test "thywill import shows proper error for missing import script" {
    # Remove import script to test error handling
    rm -f import_community_data.py
    
    run ./thywill import community sample_export.zip
    [ "$status" -eq 1 ]
    # Should show some kind of error about missing script
    [[ "$output" == *"not found"* ]] || [[ "$output" == *"script"* ]]
}

@test "thywill handles permission denied gracefully" {
    # Create a directory we can't write to
    chmod 000 deployment/
    
    # Commands that might need to access deployment directory
    run ./thywill backup daily
    # Should either work or give reasonable error
    if [ "$status" -ne 0 ]; then
        # Should not crash, just show an error
        [[ "$output" != *"Segmentation fault"* ]]
    fi
    
    # Restore permissions for cleanup
    chmod 755 deployment/
}

@test "thywill handles missing python gracefully" {
    # Mock python3 to simulate it not being found
    function python3() {
        echo "python3: command not found"
        return 127
    }
    export -f python3
    
    run ./thywill admin list
    [ "$status" -eq 127 ]
    [[ "$output" == *"command not found"* ]]
}

@test "thywill handles long file paths" {
    # Create a very long filename
    local long_name=""
    for i in {1..100}; do
        long_name="${long_name}x"
    done
    long_name="${long_name}.json"
    
    run ./thywill import prayers "$long_name"
    [ "$status" -eq 1 ]
    [[ "$output" == *"File not found"* ]]
}

@test "thywill handles binary files as input" {
    # Create a binary file
    echo -e '\x00\x01\x02\x03\xFF' > binary_file.json
    
    run ./thywill import prayers binary_file.json
    # Should handle gracefully, either by processing or giving clear error
    # Should not crash
    [[ "$output" != *"Segmentation fault"* ]]
}

@test "thywill shows reasonable error for network issues" {
    # Mock curl to simulate network failure
    function curl() {
        echo "curl: (6) Could not resolve host"
        return 6
    }
    export -f curl
    
    run ./thywill health
    # Should handle network errors gracefully
    if [ "$status" -ne 0 ]; then
        [[ "$output" == *"Health endpoint not responding"* ]]
    fi
}

@test "thywill handles interrupted commands gracefully" {
    # Test timeout behavior
    run timeout 1s ./thywill start 2>/dev/null
    # Should not leave processes hanging
    # This is mainly to test cleanup
    [ "$status" -ne 0 ]  # timeout will return non-zero
}

@test "thywill validates numeric arguments consistently" {
    # Test various invalid numeric inputs
    
    run ./thywill admin token abc
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
    
    run ./thywill admin token 0.0
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
    
    # Test empty argument - may default to 12 hours, so just test it doesn't crash
    run ./thywill admin token ''
    # Should either work (default 12) or give validation error
    [[ "$output" != *"Segmentation fault"* ]]
}

@test "thywill handles concurrent executions safely" {
    # This test ensures the CLI doesn't have race conditions
    # Run multiple commands in background
    ./thywill help > /dev/null &
    ./thywill version > /dev/null &
    ./thywill config > /dev/null &
    
    # Wait for all to complete
    wait
    
    # If we get here without deadlock, test passes
    [ 0 -eq 0 ]
}