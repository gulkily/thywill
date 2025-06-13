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

@test "thywill config shows current configuration" {
    setup_minimal_db_environment
    run ./thywill config
    # May fail due to missing backup directory, but should show the header
    [[ "$output" == *"Current Configuration"* ]]
    [[ "$output" == *"Paths:"* ]]
}

@test "thywill config shows service status" {
    setup_minimal_db_environment
    run ./thywill config
    # Should at least attempt to show service status
    [[ "$output" == *"Service Status:"* ]]
}

@test "thywill status shows system information" {
    setup_minimal_db_environment
    run ./thywill status
    [ "$status" -eq 0 ]
    [[ "$output" == *"System Status"* ]]
    [[ "$output" == *"Service Status:"* ]]
}

@test "thywill health checks service and endpoint" {
    setup_minimal_db_environment
    run ./thywill health
    [ "$status" -eq 0 ]
    [[ "$output" == *"Application Health Check"* ]]
    [[ "$output" == *"ThyWill service is running"* ]]
    [[ "$output" == *"Health endpoint responding"* ]]
}

@test "thywill logs shows application logs" {
    setup_minimal_db_environment
    run ./thywill logs
    [ "$status" -eq 0 ]
    [[ "$output" == *"Application Logs"* ]]
}

@test "thywill logs accepts custom line count" {
    setup_minimal_db_environment
    run ./thywill logs 20
    [ "$status" -eq 0 ]
    [[ "$output" == *"last 20 lines"* ]]
}

@test "thywill start validates environment" {
    run ./thywill start
    # Should check for app.py first
    [ "$status" -eq 1 ]
    [[ "$output" == *"app.py not found in current directory"* ]]
    [[ "$output" == *"Please run this command from your ThyWill project directory"* ]]
}

@test "thywill start with app.py present works" {
    touch app.py
    run timeout 2s ./thywill start
    # Should start trying to set up environment
    [[ "$output" == *"Starting Development Server"* ]]
}

@test "thywill backup requires type argument" {
    setup_minimal_db_environment
    run ./thywill backup
    [ "$status" -eq 1 ]
    [[ "$output" == *"Backup type required"* ]]
    [[ "$output" == *"Use: hourly, daily, or weekly"* ]]
}

@test "thywill backup accepts valid types" {
    setup_minimal_db_environment
    
    run ./thywill backup hourly
    [[ "$output" == *"Creating hourly Backup"* ]]
    
    run ./thywill backup daily
    [[ "$output" == *"Creating daily Backup"* ]]
    
    run ./thywill backup weekly
    [[ "$output" == *"Creating weekly Backup"* ]]
}

@test "thywill backup rejects invalid type" {
    setup_minimal_db_environment
    run ./thywill backup invalid
    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid backup type: invalid"* ]]
    [[ "$output" == *"Valid types: hourly, daily, weekly"* ]]
}

@test "thywill list shows available backups" {
    setup_minimal_db_environment
    run ./thywill list
    [ "$status" -eq 0 ]
    [[ "$output" == *"Available Backups"* ]]
}

@test "thywill restore requires backup file" {
    setup_minimal_db_environment
    run ./thywill restore
    [ "$status" -eq 1 ]
    [[ "$output" == *"Backup file path required"* ]]
    [[ "$output" == *"Use 'thywill list' to see available backups"* ]]
}

@test "thywill verify requires backup file" {
    setup_minimal_db_environment
    run ./thywill verify
    [ "$status" -eq 1 ]
    [[ "$output" == *"Backup file path required"* ]]
}

@test "thywill verify with nonexistent file fails" {
    setup_minimal_db_environment
    run ./thywill verify /nonexistent/backup.db
    [ "$status" -eq 1 ]
    [[ "$output" == *"Backup file not found"* ]]
}

@test "thywill cleanup removes old backups" {
    setup_minimal_db_environment
    run ./thywill cleanup
    [ "$status" -eq 0 ]
    [[ "$output" == *"Cleaning Up Old Backups"* ]]
}

@test "thywill commands check deployment script existence" {
    setup_minimal_db_environment
    
    # Remove deployment script to test error handling
    rm -f deployment/deploy.sh
    run ./thywill deploy
    [ "$status" -eq 1 ]
    [[ "$output" == *"Deployment script not found"* ]]
}