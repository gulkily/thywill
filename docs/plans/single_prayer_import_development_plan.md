# Single Prayer Import Development Plan

## Stage 1: Core Import Function (90 minutes)
**Goal**: Create prayer import function that can parse and import a single text file
**Dependencies**: None
**Changes**:
- Add `import_single_prayer_file(file_path)` function to existing import system
- Reuse existing text archive parsing logic from `TextArchiveImportService`
- Add file validation and error handling
- Implement duplicate detection using existing prayer matching logic
**Testing**: Unit tests for file parsing, validation, and duplicate detection
**Risks**: Text archive format inconsistencies, parsing edge cases

## Stage 2: CLI Command Integration (45 minutes)
**Goal**: Add `import-prayer` command to CLI interface
**Dependencies**: Stage 1 complete
**Changes**:
- Add `import-prayer` command to `thywill` CLI script
- Add command parsing and argument validation
- Wire up CLI command to core import function
- Add help text and usage examples
**Testing**: CLI integration tests, help text verification
**Risks**: CLI argument parsing conflicts, command naming issues

## Stage 3: Error Handling and User Feedback (60 minutes)
**Goal**: Provide clear feedback and robust error handling
**Dependencies**: Stages 1-2 complete
**Changes**:
- Add comprehensive error messages for common failure modes
- Implement progress feedback for import operations
- Add validation for user existence and file format
- Handle edge cases (empty files, corrupted data, missing metadata)
**Testing**: Error scenario testing, user feedback verification
**Risks**: Unclear error messages, missing edge cases

## Stage 4: Integration Testing and Documentation (45 minutes)
**Goal**: Ensure feature works end-to-end and update documentation
**Dependencies**: Stages 1-3 complete
**Changes**:
- Add integration tests with real prayer text files
- Update CLAUDE.md with new command documentation
- Test with various text archive formats and edge cases
- Verify no impact on existing import functionality
**Testing**: End-to-end testing, documentation verification
**Risks**: Integration conflicts, documentation gaps

## Database Changes
- No new tables or schema changes required
- Uses existing Prayer, PrayerMark, and PrayerAttribute models
- Leverages current duplicate detection and import logic

## Function Signatures
```python
# app_helpers/import_service.py
def import_single_prayer_file(file_path: str) -> ImportResult
def validate_prayer_text_file(file_path: str) -> bool
def parse_single_prayer_file(file_path: str) -> PrayerData

# CLI integration
def cli_import_prayer(args) -> None
```

## Testing Strategy
- Unit tests for core parsing and import logic
- CLI integration tests for command interface
- Error handling tests for various failure scenarios
- End-to-end tests with sample prayer text files
- Regression tests to ensure existing import functionality unchanged

## Risk Assessment
- **Low**: Reuses existing text archive parsing logic
- **Medium**: CLI integration complexity and error handling edge cases
- **Mitigation**: Comprehensive testing and validation at each stage