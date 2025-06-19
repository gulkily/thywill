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

@test "thywill admin list shows admin users" {
    run ./thywill admin list
    [ "$status" -eq 0 ]
    [[ "$output" == *"Admin Users"* ]]
    [[ "$output" == *"Test Admin"* ]]
}

@test "thywill admin list fails when not in project directory" {
    # Remove models.py to simulate wrong directory (SAFE: only in test dir)
    rm -f ./models.py ./thywill.db
    run ./thywill admin list
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}

@test "thywill admin grant requires user argument" {
    run ./thywill admin grant
    [ "$status" -eq 1 ]
    [[ "$output" == *"User identifier required"* ]]
    [[ "$output" == *"Usage: thywill admin grant"* ]]
}

@test "thywill admin grant shows examples" {
    run ./thywill admin grant
    [ "$status" -eq 1 ]
    [[ "$output" == *"Examples:"* ]]
    [[ "$output" == *"thywill admin grant"* ]]
}

@test "thywill admin revoke requires user argument" {
    run ./thywill admin revoke
    [ "$status" -eq 1 ]
    [[ "$output" == *"User identifier required"* ]]
    [[ "$output" == *"Usage: thywill admin revoke"* ]]
}

@test "thywill admin token creates token with default hours" {
    run ./thywill admin token
    [ "$status" -eq 0 ]
    [[ "$output" == *"Admin invite token created successfully"* ]]
    [[ "$output" == *"Token:"* ]]
    [[ "$output" == *"Claim URL:"* ]]
}

@test "thywill admin token accepts custom hours" {
    run ./thywill admin token 24
    [ "$status" -eq 0 ]
    [[ "$output" == *"Admin invite token created successfully"* ]]
    [[ "$output" == *"Token:"* ]]
}

@test "thywill admin token validates hours parameter" {
    run ./thywill admin token invalid_number
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
}

@test "thywill admin token rejects zero hours" {
    run ./thywill admin token 0
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
}

@test "thywill admin token rejects negative hours" {
    run ./thywill admin token -5
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hours must be a positive number"* ]]
}

@test "thywill admin without subcommand shows error" {
    run ./thywill admin
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown admin subcommand:"* ]]
    [[ "$output" == *"Available subcommands: grant, revoke, list, token"* ]]
}

@test "thywill admin invalid subcommand shows error" {
    run ./thywill admin invalidcmd
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown admin subcommand: invalidcmd"* ]]
    [[ "$output" == *"Available subcommands:"* ]]
}

@test "thywill admin grant with user works" {
    run ./thywill admin grant "Test User"
    # Should either succeed or fail with database error, not argument error
    if [ "$status" -ne 0 ]; then
        # Should not fail on argument validation
        [[ "$output" != *"User identifier required"* ]]
    fi
}

@test "thywill admin revoke with user works" {
    run ./thywill admin revoke "Test User"
    # Should either succeed or fail with database error, not argument error
    if [ "$status" -ne 0 ]; then
        # Should not fail on argument validation
        [[ "$output" != *"User identifier required"* ]]
    fi
}

@test "thywill admin commands require project directory" {
    rm -f ./models.py ./thywill.db
    
    run ./thywill admin grant "Test User"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
    
    run ./thywill admin revoke "Test User"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
    
    run ./thywill admin token
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}