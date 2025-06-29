#!/usr/bin/env bats

# Load common test helpers
load '../test_helper/common'

# Setup function runs before each test
setup() {
    setup_test_environment
    setup_mocks
    setup_minimal_db_environment
    create_test_fixtures
}

# Cleanup after each test
teardown() {
    cleanup_test_environment
}

@test "thywill import without arguments shows usage" {
    run ./thywill import
    [ "$status" -eq 1 ]
    [[ "$output" == *"Available import types: prayers, text-archives"* ]]
    [[ "$output" == *"Usage: thywill import <type> <file>"* ]]
    [[ "$output" == *"Examples:"* ]]
}

@test "thywill import shows examples" {
    run ./thywill import
    [ "$status" -eq 1 ]
    [[ "$output" == *"thywill import prayers backup.json"* ]]
}


@test "thywill import prayers without file shows usage" {
    run ./thywill import prayers
    [ "$status" -eq 1 ]
    [[ "$output" == *"File path required"* ]]
    [[ "$output" == *"Usage: thywill import prayers <json_file>"* ]]
}

@test "thywill import prayers shows expected format" {
    run ./thywill import prayers
    [ "$status" -eq 1 ]
    [[ "$output" == *"Expected JSON format:"* ]]
    [[ "$output" == *"text"* ]]
    [[ "$output" == *"generated_prayer"* ]]
    [[ "$output" == *"author_name"* ]]
}

@test "thywill import prayers with nonexistent file fails" {
    run ./thywill import prayers /nonexistent/file.json
    [ "$status" -eq 1 ]
    [[ "$output" == *"File not found"* ]]
}

@test "thywill import prayers with existing file works" {
    run ./thywill import prayers sample_prayers.json
    [ "$status" -eq 0 ]
    [[ "$output" == *"Prayer import completed"* ]]
}

@test "thywill import prayers requires project directory" {
    rm -f ./models.py ./thywill.db
    run ./thywill import prayers sample_prayers.json
    [ "$status" -eq 1 ]
    [[ "$output" == *"Must run from ThyWill project directory"* ]]
}

@test "thywill import invalid type shows error" {
    run ./thywill import invalidtype file.json
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown import type: invalidtype"* ]]
    [[ "$output" == *"Available import types: prayers, text-archives"* ]]
}

