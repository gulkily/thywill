#!/usr/bin/env bats

# Load common test helpers
load '../test_helper/common'

# Setup function runs before each test
setup() {
    setup_test_environment
    setup_mocks
}

# Cleanup after each test
teardown() {
    cleanup_test_environment
}

@test "thywill help shows usage information" {
    run ./thywill help
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI - Deployment and Backup Management"* ]]
    [[ "$output" == *"USAGE:"* ]]
    [[ "$output" == *"COMMANDS:"* ]]
    [[ "$output" == *"Development Commands:"* ]]
    [[ "$output" == *"Admin Commands:"* ]]
}

@test "thywill --help shows usage information" {
    run ./thywill --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI"* ]]
    [[ "$output" == *"USAGE:"* ]]
}

@test "thywill -h shows usage information" {
    run ./thywill -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI"* ]]
    [[ "$output" == *"USAGE:"* ]]
}

@test "thywill version shows version info" {
    run ./thywill version
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI v1.0.0"* ]]
    [[ "$output" == *"Deployment and Backup Management Utility"* ]]
    [[ "$output" == *"Built for ThyWill Prayer Application"* ]]
}

@test "thywill --version shows version info" {
    run ./thywill --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI v1.0.0"* ]]
}

@test "thywill -v shows version info" {
    run ./thywill -v
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI v1.0.0"* ]]
}

@test "thywill with no arguments shows help" {
    run ./thywill
    [ "$status" -eq 0 ]
    [[ "$output" == *"ThyWill CLI"* ]]
    [[ "$output" == *"USAGE:"* ]]
}

@test "thywill invalid command shows error" {
    run ./thywill nonexistent_command
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown command: nonexistent_command"* ]]
    [[ "$output" == *"Use 'thywill help' to see available commands"* ]]
}

@test "thywill shows available commands in help" {
    run ./thywill help
    [ "$status" -eq 0 ]
    # Check for main command categories
    [[ "$output" == *"start"* ]]
    [[ "$output" == *"admin"* ]]
    [[ "$output" == *"import"* ]]
    [[ "$output" == *"backup"* ]]
    [[ "$output" == *"help"* ]]
}

@test "thywill help includes examples" {
    run ./thywill help
    [ "$status" -eq 0 ]
    [[ "$output" == *"EXAMPLES:"* ]]
    [[ "$output" == *"thywill setup"* ]]
    [[ "$output" == *"thywill admin grant"* ]]
    [[ "$output" == *"thywill import community"* ]]
}