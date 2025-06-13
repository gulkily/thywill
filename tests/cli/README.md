# ThyWill CLI Tests

This directory contains comprehensive tests for the ThyWill CLI utility using bats-core.

## Overview

**92 tests** covering all CLI functionality with **100% pass rate**.

## Test Files

- **`test_thywill_help.bats`** - Basic commands (help, version, invalid commands)
- **`test_thywill_admin.bats`** - Admin functionality (user management, tokens)
- **`test_thywill_import.bats`** - Import commands (prayers, community data)
- **`test_thywill_roles.bats`** - Role management (list, grant, revoke)
- **`test_thywill_files.bats`** - File system and service integration
- **`test_thywill_errors.bats`** - Error handling and edge cases

## Test Helpers

- **`../test_helper/common.bash`** - Shared utilities and mocking functions

## Running Tests

```bash
# Run all CLI tests
bats tests/cli/

# Run specific test file
bats tests/cli/test_thywill_admin.bats

# Run specific test
bats --filter "thywill help shows usage" tests/cli/test_thywill_help.bats

# Run with timing information
bats --timing tests/cli/
```

## Test Coverage

### Commands Tested
- ✅ Help and version commands
- ✅ Admin commands (list, grant, revoke, token)
- ✅ Role management (list, grant, revoke)
- ✅ Import commands (prayers, community)
- ✅ Backup commands (backup, list, restore, verify, cleanup)
- ✅ Service commands (start, health, status, logs, config)
- ✅ Deployment commands (deploy)

### Validation Tested
- ✅ Argument validation and error messages
- ✅ File existence checks
- ✅ Directory validation
- ✅ Numeric parameter validation
- ✅ Project environment requirements

### Edge Cases Tested
- ✅ File paths with spaces
- ✅ Special characters in arguments
- ✅ Permission denied scenarios
- ✅ Missing dependencies
- ✅ Network connectivity issues
- ✅ Binary file handling
- ✅ Concurrent execution safety

## Test Strategy

### Mocking
Tests use extensive mocking to avoid database dependencies:
- **Python commands** - Mocked to return expected outputs
- **System commands** - Mocked (systemctl, journalctl, curl)
- **File operations** - Isolated test environments

### Test Environment
Each test runs in isolation:
- Unique temporary directories
- Mock deployment scripts
- Minimal file structure
- Clean setup/teardown

### Error Handling
Tests verify graceful error handling:
- Clear error messages
- Appropriate exit codes
- No crashes or hangs
- Proper cleanup

## Adding New Tests

1. **Choose appropriate test file** based on command category
2. **Use common test helpers** for setup/teardown
3. **Mock external dependencies** to avoid side effects
4. **Test both success and failure paths**
5. **Verify error messages are user-friendly**

### Example Test
```bash
@test "thywill command validates arguments" {
    run ./thywill command invalid_arg
    [ "$status" -eq 1 ]
    [[ "$output" == *"Expected error message"* ]]
}
```

## Mock Functions Available

- `setup_test_environment()` - Creates isolated test directory
- `setup_mocks()` - Mocks external commands (python3, systemctl, etc.)
- `setup_minimal_db_environment()` - Creates minimal project files
- `create_test_fixtures()` - Creates sample data files
- `cleanup_test_environment()` - Cleans up test files

## Performance

Tests run efficiently:
- **Average execution time**: <30 seconds for all 92 tests
- **No external dependencies** required during testing
- **Parallel safe** - tests don't interfere with each other

## Maintenance

To maintain test quality:
1. **Run tests before commits** to catch regressions
2. **Update mocks** when CLI behavior changes
3. **Add tests** for new CLI features
4. **Keep test documentation** current
5. **Monitor test execution time** for performance

## Success Metrics

- ✅ **92/92 tests passing** (100% success rate)
- ✅ **Full command coverage** - All CLI commands tested
- ✅ **Comprehensive validation** - Arguments, files, permissions
- ✅ **Robust error handling** - Graceful failure scenarios
- ✅ **Fast execution** - Complete test suite in <30 seconds