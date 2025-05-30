"""Test data factories for creating consistent test objects"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, AuthenticationRequest, AuthApproval


class UserFactory:
    """Factory for creating test users"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        display_name: str = "Test User",
        created_at: Optional[datetime] = None
    ) -> User:
        return User(
            id=id or uuid.uuid4().hex,
            display_name=display_name,
            created_at=created_at or datetime.utcnow()
        )
    
    @staticmethod
    def create_admin() -> User:
        return User(
            id="admin",
            display_name="Admin User",
            created_at=datetime.utcnow()
        )


class PrayerFactory:
    """Factory for creating test prayers"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        author_id: str = "test_user_id", 
        text: str = "Please pray for my test",
        generated_prayer: Optional[str] = "DEFAULT_PRAYER",
        project_tag: Optional[str] = None,
        created_at: Optional[datetime] = None,
        flagged: bool = False
    ) -> Prayer:
        # Use a special value to distinguish between None and default
        prayer_text = None if generated_prayer is None else (
            "Divine Creator, we lift up our friend. Amen." if generated_prayer == "DEFAULT_PRAYER" else generated_prayer
        )
        
        return Prayer(
            id=id or uuid.uuid4().hex,
            author_id=author_id,
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
        user_id: str = "test_user_id",
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
            user_id=user_id,
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
        expires_at: Optional[datetime] = None
    ) -> InviteToken:
        return InviteToken(
            token=token or uuid.uuid4().hex,
            created_by_user=created_by_user,
            used=used,
            expires_at=expires_at or (datetime.utcnow() + timedelta(hours=12))
        )


class PrayerMarkFactory:
    """Factory for creating test prayer marks"""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        user_id: str = "test_user_id",
        prayer_id: str = "test_prayer_id",
        created_at: Optional[datetime] = None
    ) -> PrayerMark:
        return PrayerMark(
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
        user_id: str = "test_user_id",
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
        approver_user_id: str = "test_approver_id",
        created_at: Optional[datetime] = None
    ) -> AuthApproval:
        return AuthApproval(
            id=id or uuid.uuid4().hex,
            auth_request_id=auth_request_id,
            approver_user_id=approver_user_id,
            created_at=created_at or datetime.utcnow()
        )