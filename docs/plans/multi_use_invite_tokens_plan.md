# Multi-Use Invite Token Development Plan

**Current State**: Single-use tokens with `used: bool` field that blocks reuse after first claim.

**Proposed Changes**:

## 1. Database Schema Updates

### InviteToken Model (models.py)
- Replace `used: bool` with `usage_count: int = 0` 
- Add `max_uses: int | None = None` (null = unlimited)
- Keep `used_by_user_id` for backward compatibility, populate from latest usage

### New InviteTokenUsage Model
```python
class InviteTokenUsage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    invite_token_id: int = Field(foreign_key="invitetoken.id")
    user_id: int = Field(foreign_key="user.id")
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str | None = None  # Security tracking
```

## 2. Environment Configuration
- Add `DEFAULT_INVITE_MAX_USES` environment variable
- Default to 1 for backward compatibility if not set
- Use in token creation when max_uses not explicitly specified

## 3. Token Creation (app_helpers/services/token_service.py)
- Add `max_uses` parameter to `create_invite_token()`
- Use `DEFAULT_INVITE_MAX_USES` when max_uses not provided
- Admin interface to create multi-use tokens

## 4. Claim Logic (app_helpers/routes/auth/login_routes.py)
- Replace `if inv.used:` check with usage count validation
- Create InviteTokenUsage record on successful claim
- Increment `usage_count` and update `used_by_user_id` to latest user
- Block when `usage_count >= max_uses` (if max_uses set)
- Capture IP address for security tracking

## 5. Database Migration
- Create migration script to convert existing `used` boolean to `usage_count`
- Set `max_uses` based on `DEFAULT_INVITE_MAX_USES` for existing tokens
- Create InviteTokenUsage records for existing used tokens
- Preserve existing `used_by_user_id` values

## 6. Edge Cases
- Handle `max_uses = 0` (block all usage)
- Validate `max_uses` is not negative
- Ensure atomic operations to prevent race conditions

**Files to Modify**:
- `models.py` - Update InviteToken schema, add InviteTokenUsage model
- `app_helpers/routes/auth/login_routes.py` - Update claim validation and usage tracking
- `app_helpers/services/token_service.py` - Add max_uses support
- Migration script for schema update and data preservation