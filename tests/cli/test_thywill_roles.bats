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

@test "thywill role list shows available roles" {
    run ./thywill role list
    [ "$status" -eq 0 ]
    [[ "$output" == *"Available Roles"* ]]
    [[ "$output" == *"admin"* ]]
    [[ "$output" == *"user"* ]]
}

@test "thywill role list requires project directory" {
    rm -f models.py thywill.db
    run ./thywill role list
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}

@test "thywill role grant requires user and role" {
    run ./thywill role grant
    [ "$status" -eq 1 ]
    [[ "$output" == *"User and role required"* ]]
    [[ "$output" == *"Usage: thywill role grant <user> <role>"* ]]
}

@test "thywill role grant shows examples" {
    run ./thywill role grant
    [ "$status" -eq 1 ]
    [[ "$output" == *"Examples:"* ]]
    [[ "$output" == *"thywill role grant"* ]]
    [[ "$output" == *"moderator"* ]]
}

@test "thywill role grant with one argument fails" {
    run ./thywill role grant "Test User"
    [ "$status" -eq 1 ]
    [[ "$output" == *"User and role required"* ]]
}

@test "thywill role grant with user and role works" {
    run ./thywill role grant "Test User" moderator
    # Should either succeed or fail with database error, not argument error
    if [ "$status" -ne 0 ]; then
        # Should not fail on argument validation
        [[ "$output" != *"User and role required"* ]]
    fi
}

@test "thywill role revoke requires user and role" {
    run ./thywill role revoke
    [ "$status" -eq 1 ]
    [[ "$output" == *"User and role required"* ]]
    [[ "$output" == *"Usage: thywill role revoke <user> <role>"* ]]
}

@test "thywill role revoke shows examples" {
    run ./thywill role revoke
    [ "$status" -eq 1 ]
    [[ "$output" == *"Examples:"* ]]
    [[ "$output" == *"thywill role revoke"* ]]
    [[ "$output" == *"moderator"* ]]
}

@test "thywill role revoke with one argument fails" {
    run ./thywill role revoke "Test User"
    [ "$status" -eq 1 ]
    [[ "$output" == *"User and role required"* ]]
}

@test "thywill role revoke with user and role works" {
    run ./thywill role revoke "Test User" moderator
    # Should either succeed or fail with database error, not argument error
    if [ "$status" -ne 0 ]; then
        # Should not fail on argument validation
        [[ "$output" != *"User and role required"* ]]
    fi
}

@test "thywill role without subcommand shows error" {
    run ./thywill role
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown role subcommand:"* ]]
    [[ "$output" == *"Available subcommands: list, grant, revoke"* ]]
}

@test "thywill role invalid subcommand shows error" {
    run ./thywill role invalidcmd
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown role subcommand: invalidcmd"* ]]
    [[ "$output" == *"Available subcommands:"* ]]
}

@test "thywill role shows usage examples" {
    run ./thywill role invalid
    [ "$status" -eq 1 ]
    [[ "$output" == *"Examples:"* ]]
    [[ "$output" == *"thywill role list"* ]]
    [[ "$output" == *"thywill role grant"* ]]
    [[ "$output" == *"thywill role revoke"* ]]
}

@test "thywill role grant requires project directory" {
    rm -f models.py thywill.db
    run ./thywill role grant "Test User" moderator
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}

@test "thywill role revoke requires project directory" {
    rm -f models.py thywill.db
    run ./thywill role revoke "Test User" moderator
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}