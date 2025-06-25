# Test User Cleanup Implementation Plan

## Problem Analysis

Based on the invite tree screenshot and database schema examination, the production database has several issues that need to be addressed:

### Identified Issues

1. **Root Test User Problem**: The invite tree root is occupied by "Test User", which creates a fundamental data integrity issue since all legitimate users trace back to a test account.

2. **Multiple Test Users**: Several test accounts exist throughout the tree:
   - "Test User" (appears multiple times)
   - "Prayer Test User" 
   - These accounts pollute the legitimate user base

3. **Duplicate Users**: The user "ilyag" appears twice:
   - Once at the top level 
   - Once lower in the tree marked as "(You)"
   - This suggests either database corruption or testing artifacts

4. **Data Integrity Concerns**: 
   - Invite relationships may be corrupted
   - User authentication may be affected
   - Archive/audit trail may reference invalid accounts

## Root Cause Analysis

### Why These Issues Occurred

1. **Development/Testing Data in Production**: Test accounts were created during development and not properly cleaned up before production deployment.

2. **Lack of User Deactivation System**: The current User model lacks fields for:
   - `is_active` boolean flag
   - `deactivated_at` timestamp
   - `deactivation_reason` field

3. **Invite Tree Constraints**: The current schema doesn't handle:
   - Root user changes
   - User deactivation cascading effects
   - Orphaned user cleanup

4. **Missing Administrative Tools**: No built-in CLI commands or admin interfaces for:
   - User deactivation
   - Invite tree restructuring
   - Data cleanup operations

## Proposed Solutions

### Phase 1: Database Schema Enhancement

1. **Add User Deactivation Fields**:
   ```python
   # Add to User model
   is_active: bool = Field(default=True)
   deactivated_at: datetime | None = Field(default=None)
   deactivation_reason: str | None = Field(default=None, max_length=255)
   deactivated_by: str | None = Field(default=None, foreign_key="user.id")
   ```

2. **Create Migration Script**:
   - Add new columns to existing users table
   - Set all existing users as `is_active=True`
   - Ensure backward compatibility

### Phase 2: Administrative Tooling

1. **CLI Commands**:
   ```bash
   ./thywill users list --include-inactive
   ./thywill users deactivate <user_id> --reason "test account cleanup"
   ./thywill users reactivate <user_id>
   ./thywill invite-tree rebuild --new-root <user_id>
   ```

2. **Admin Web Interface**:
   - User management panel
   - Bulk deactivation capabilities
   - Invite tree visualization and editing

### Phase 3: Specific Cleanup Actions

1. **Identify Legitimate Root User**:
   - Review user creation timestamps
   - Identify the earliest legitimate (non-test) user
   - Verify their prayer history and community engagement

2. **Test User Deactivation Strategy**:
   ```
   Users to deactivate:
   - All users with display_name containing "Test User"
   - "Prayer Test User"
   - Duplicate "ilyag" entry (keep the one marked as "(You)")
   ```

3. **Invite Tree Restructuring**:
   - Move legitimate users to new root
   - Update `invited_by_user_id` relationships
   - Preserve legitimate invite chains

### Phase 4: Data Integrity Protection

1. **Application Logic Updates**:
   - Filter inactive users from invite trees
   - Exclude inactive users from community feeds
   - Maintain audit trail of deactivated accounts

2. **Archive System Updates**:
   - Handle deactivated user data in text archives
   - Maintain historical accuracy while hiding from active views

3. **Authentication System Updates**:
   - Prevent login for deactivated users
   - Clear active sessions for deactivated accounts

## Implementation Strategy

### Step 1: Schema Migration
```python
# Migration: add_user_deactivation_fields.py
def upgrade():
    # Add new columns
    op.add_column('user', sa.Column('is_active', sa.Boolean(), default=True))
    op.add_column('user', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('deactivation_reason', sa.String(255), nullable=True))
    op.add_column('user', sa.Column('deactivated_by', sa.String(), nullable=True))
    
    # Set all existing users as active
    op.execute("UPDATE user SET is_active = true WHERE is_active IS NULL")
```

### Step 2: Service Layer Implementation
```python
# app_helpers/services/user_management_service.py
class UserManagementService:
    def deactivate_user(self, user_id: str, reason: str, deactivated_by: str, session: Session):
        # Deactivate user
        # Clear active sessions
        # Log security event
        # Update invite tree relationships if needed
        
    def reactivate_user(self, user_id: str, reactivated_by: str, session: Session):
        # Reactivate user
        # Log security event
        
    def rebuild_invite_tree(self, new_root_user_id: str, session: Session):
        # Complex operation to restructure invite relationships
        # Create backup before operation
        # Update all invited_by_user_id references
```

### Step 3: CLI Implementation
```python
# CLI commands in thywill script
def cmd_users_deactivate(user_id, reason):
    # Implement user deactivation via CLI
    
def cmd_invite_tree_rebuild(new_root_id):
    # Implement invite tree restructuring
```

### Step 4: Production Cleanup Execution

1. **Create Database Backup**:
   ```bash
   ./thywill backup --name "before_test_user_cleanup"
   ```

2. **Identify Legitimate Root User**:
   - Query users by creation date
   - Review user activity and prayer history
   - Confirm with community if needed

3. **Execute Cleanup**:
   ```bash
   # Deactivate test users
   ./thywill users deactivate <test_user_id_1> --reason "test account cleanup"
   ./thywill users deactivate <test_user_id_2> --reason "test account cleanup"
   
   # Remove duplicate ilyag (keep the "(You)" version)
   ./thywill users deactivate <duplicate_ilyag_id> --reason "duplicate account cleanup"
   
   # Rebuild invite tree with legitimate root
   ./thywill invite-tree rebuild --new-root <legitimate_user_id>
   ```

4. **Verify Results**:
   - Check invite tree display
   - Verify user counts
   - Test authentication flows
   - Confirm archive integrity

## Risk Mitigation

### Data Safety Measures

1. **Comprehensive Backups**: Full database backup before any operations
2. **Dry Run Mode**: Test all operations with `--dry-run` flag first
3. **Rollback Plan**: Ability to restore from backup if issues occur
4. **Gradual Deployment**: Test on staging environment first

### User Impact Minimization

1. **Preserve User Data**: Deactivated users retain their prayers and marks
2. **Maintain Privacy**: Archive system continues to work for legitimate users
3. **Communication**: Inform community of cleanup if visible changes occur

### System Stability

1. **Authentication Continuity**: Ensure legitimate users remain unaffected
2. **Invite System Integrity**: Preserve valid invite relationships
3. **Admin Access**: Maintain admin privileges throughout process

## Success Criteria

1. **Clean Invite Tree**: No test users visible in community tree
2. **Single User Instances**: No duplicate users (e.g., single "ilyag")
3. **Legitimate Root**: Root user is a real community member
4. **Preserved Functionality**: All system features work normally
5. **Data Integrity**: All legitimate user data and relationships intact

## Timeline Estimate

- **Phase 1 (Schema)**: 2-3 days
- **Phase 2 (Tooling)**: 5-7 days  
- **Phase 3 (Cleanup)**: 1-2 days
- **Phase 4 (Verification)**: 1-2 days

**Total**: 9-14 days for complete implementation and cleanup

## Post-Cleanup Maintenance

1. **Monitoring**: Regular checks for test data in production
2. **Development Guidelines**: Strict separation of test and production data
3. **Automated Cleanup**: Scripts to prevent future test data pollution
4. **User Management**: Ongoing tools for community administration

This plan addresses the immediate cleanup needs while establishing long-term systems to prevent similar issues in the future.