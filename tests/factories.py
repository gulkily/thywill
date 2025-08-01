"""Test data factories for creating consistent test objects"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, PrayerSkip, AuthenticationRequest, AuthApproval, PrayerAttribute, PrayerActivityLog, ChangelogEntry


class UserFactory:
    """Factory for creating test users"""
    
    @staticmethod
    def create(
        display_name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        invited_by_username: Optional[str] = None,
        invite_token_used: Optional[str] = None
    ) -> User:
        return User(
            display_name=display_name or f"TestUser{uuid.uuid4().hex[:8]}",
            created_at=created_at or datetime.utcnow(),
            invited_by_username=invited_by_username,
            invite_token_used=invite_token_used
        )
    
    @staticmethod
    def create_admin() -> User:
        return User(
            display_name="admin",
            created_at=datetime.utcnow(),
            invited_by_username=None,
            invite_token_used=None
        )


class PrayerFactory:
    """Factory for creating test prayers"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        author_username: str = "testuser", 
        text: str = "Please pray for my test",
        generated_prayer: Optional[str] = "DEFAULT_PRAYER",
        project_tag: Optional[str] = None,
        created_at: Optional[datetime] = None,
        flagged: bool = False,
    ) -> Prayer:
        # Use a special value to distinguish between None and default
        prayer_text = None if generated_prayer is None else (
            "Divine Creator, we lift up our friend. Amen." if generated_prayer == "DEFAULT_PRAYER" else generated_prayer
        )
        
        return Prayer(
            id=id or uuid.uuid4().hex,
            author_username=author_username,
            text=text,
            generated_prayer=prayer_text,
            project_tag=project_tag,
            created_at=created_at or datetime.utcnow(),
            flagged=flagged
        )


class SessionFactory:
    """Factory for creating test sessions"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        username: str = "testuser",
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        auth_request_id: Optional[str] = None,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        is_fully_authenticated: bool = True
    ) -> SessionModel:
        now = created_at or datetime.utcnow()
        return SessionModel(
            id=id or uuid.uuid4().hex,
            username=username,
            created_at=now,
            expires_at=expires_at or (now + timedelta(days=14)),
            auth_request_id=auth_request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=is_fully_authenticated
        )


class InviteTokenFactory:
    """Factory for creating test invite tokens"""
    
    @staticmethod
    def create(
        token: Optional[str] = None,
        created_by_user: str = "admin",
        used: bool = False,
        expires_at: Optional[datetime] = None,
        used_by_user_id: Optional[str] = None,
        usage_count: Optional[int] = None,
        max_uses: Optional[int] = None
    ) -> InviteToken:
        # Use centralized token configuration
        from app_helpers.services.token_service import TOKEN_EXP_H, DEFAULT_INVITE_MAX_USES
        
        # Handle backward compatibility for 'used' parameter
        if used and usage_count is None and max_uses is None:
            # If used=True, set token to be "used" by making usage_count >= max_uses
            calculated_max_uses = DEFAULT_INVITE_MAX_USES
            calculated_usage_count = calculated_max_uses
        else:
            calculated_max_uses = max_uses if max_uses is not None else DEFAULT_INVITE_MAX_USES
            calculated_usage_count = usage_count if usage_count is not None else 0
        
        return InviteToken(
            token=token or uuid.uuid4().hex,
            created_by_user=created_by_user,
            usage_count=calculated_usage_count,
            max_uses=calculated_max_uses,
            expires_at=expires_at or (datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)),
            used_by_user_id=used_by_user_id
        )


class PrayerMarkFactory:
    """Factory for creating test prayer marks"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        username: str = "testuser",
        prayer_id: str = "test_prayer_id",
        created_at: Optional[datetime] = None
    ) -> PrayerMark:
        return PrayerMark(
            id=id or uuid.uuid4().hex,
            username=username,
            prayer_id=prayer_id,
            created_at=created_at or datetime.utcnow()
        )


class PrayerSkipFactory:
    """Factory for creating test prayer skips"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        user_id: str = "testuser",
        prayer_id: str = "test_prayer_id",
        created_at: Optional[datetime] = None
    ) -> PrayerSkip:
        return PrayerSkip(
            id=id or uuid.uuid4().hex,
            user_id=user_id,
            prayer_id=prayer_id,
            created_at=created_at or datetime.utcnow()
        )


class AuthenticationRequestFactory:
    """Factory for creating test authentication requests"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        user_id: str = "testuser",
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        status: str = "pending",
        approved_by_user_id: Optional[str] = None,
        approved_at: Optional[datetime] = None
    ) -> AuthenticationRequest:
        now = created_at or datetime.utcnow()
        return AuthenticationRequest(
            id=id or uuid.uuid4().hex,
            user_id=user_id,
            device_info=device_info or "Test Browser",
            ip_address=ip_address or "127.0.0.1",
            created_at=now,
            expires_at=expires_at or (now + timedelta(days=7)),
            status=status,
            approved_by_user_id=approved_by_user_id,
            approved_at=approved_at
        )


class AuthApprovalFactory:
    """Factory for creating test auth approvals"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        auth_request_id: str = "test_auth_request_id",
        approver_user_id: str = "testuser",
        created_at: Optional[datetime] = None
    ) -> AuthApproval:
        return AuthApproval(
            id=id or uuid.uuid4().hex,
            auth_request_id=auth_request_id,
            approver_user_id=approver_user_id,
            created_at=created_at or datetime.utcnow()
        )


class PrayerAttributeFactory:
    """Factory for creating test prayer attributes"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        prayer_id: str = "test_prayer_id",
        attribute_name: str = "test_attribute",
        attribute_value: str = "true",
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> PrayerAttribute:
        return PrayerAttribute(
            id=id or uuid.uuid4().hex[:16],
            prayer_id=prayer_id,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            created_at=created_at or datetime.utcnow(),
            created_by=created_by
        )
    
    @staticmethod
    def create_archived(prayer_id: str, created_by: str) -> PrayerAttribute:
        return PrayerAttributeFactory.create(
            prayer_id=prayer_id,
            attribute_name="archived",
            attribute_value="true",
            created_by=created_by
        )
    
    @staticmethod
    def create_answered(prayer_id: str, created_by: str, testimony: Optional[str] = None) -> list[PrayerAttribute]:
        attributes = [
            PrayerAttributeFactory.create(
                prayer_id=prayer_id,
                attribute_name="answered",
                attribute_value="true",
                created_by=created_by
            ),
            PrayerAttributeFactory.create(
                prayer_id=prayer_id,
                attribute_name="answer_date",
                attribute_value=datetime.utcnow().isoformat(),
                created_by=created_by
            )
        ]
        
        if testimony:
            attributes.append(
                PrayerAttributeFactory.create(
                    prayer_id=prayer_id,
                    attribute_name="answer_testimony",
                    attribute_value=testimony,
                    created_by=created_by
                )
            )
        
        return attributes


class PrayerActivityLogFactory:
    """Factory for creating test prayer activity logs"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        prayer_id: str = "test_prayer_id",
        user_id: str = "testuser",
        action: str = "set_archived",
        old_value: Optional[str] = None,
        new_value: str = "true",
        created_at: Optional[datetime] = None
    ) -> PrayerActivityLog:
        return PrayerActivityLog(
            id=id or uuid.uuid4().hex[:16],
            prayer_id=prayer_id,
            user_id=user_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            created_at=created_at or datetime.utcnow()
        )


class ChangelogEntryFactory:
    """Factory for creating test changelog entries"""
    
    @staticmethod
    def create(
        commit_id: Optional[str] = None,
        original_message: str = "Test commit message",
        friendly_description: str = "Test friendly description",
        change_type: str = "enhanced",
        commit_date: Optional[datetime] = None
    ) -> ChangelogEntry:
        return ChangelogEntry(
            commit_id=commit_id or uuid.uuid4().hex[:8],
            original_message=original_message,
            friendly_description=friendly_description,
            change_type=change_type,
            commit_date=commit_date or datetime.utcnow()
        )
    
    @staticmethod
    def build(
        commit_id: Optional[str] = None,
        original_message: str = "Test commit message",
        friendly_description: str = "Test friendly description", 
        change_type: str = "enhanced",
        commit_date: Optional[datetime] = None
    ) -> ChangelogEntry:
        """Build without persisting to database"""
        return ChangelogEntry(
            commit_id=commit_id or uuid.uuid4().hex[:8],
            original_message=original_message,
            friendly_description=friendly_description,
            change_type=change_type,
            commit_date=commit_date or datetime.utcnow()
        )