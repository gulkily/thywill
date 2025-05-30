"""Unit tests for advanced features and admin functionality"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlmodel import Session, select, func

from models import User, Prayer, PrayerMark, AuthenticationRequest, AuthApproval, Session as SessionModel
from tests.factories import UserFactory, PrayerFactory, PrayerMarkFactory, AuthenticationRequestFactory, AuthApprovalFactory, SessionFactory
from app import is_admin


@pytest.mark.unit
class TestAdvancedFeedFiltering:
    """Test advanced feed filtering functionality that wasn't covered in Stage 3"""
    
    def test_recent_activity_feed_time_filtering(self, test_session):
        """Test recent activity feed respects 7-day time window"""
        user1 = UserFactory.create(id="user1")
        user2 = UserFactory.create(id="user2")
        
        prayer1 = PrayerFactory.create(id="prayer1", author_id="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_id="user1", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_id="user1", flagged=False)
        
        # Recent marks (within 7 days)
        recent_mark1 = PrayerMarkFactory.create(
            user_id="user2", 
            prayer_id="prayer1",
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        recent_mark2 = PrayerMarkFactory.create(
            user_id="user2", 
            prayer_id="prayer2",
            created_at=datetime.utcnow() - timedelta(days=6)
        )
        
        # Old mark (more than 7 days)
        old_mark = PrayerMarkFactory.create(
            user_id="user2", 
            prayer_id="prayer3",
            created_at=datetime.utcnow() - timedelta(days=8)
        )
        
        test_session.add_all([
            user1, user2, prayer1, prayer2, prayer3,
            recent_mark1, recent_mark2, old_mark
        ])
        test_session.commit()
        
        # Simulate recent_activity query from app.py
        week_ago = datetime.utcnow() - timedelta(days=7)
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.created_at >= week_ago)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .limit(50)
        )
        results = test_session.exec(stmt).all()
        
        # Should only return prayers with recent marks
        assert len(results) == 2
        prayer_ids = [result[0].id for result in results]
        assert "prayer1" in prayer_ids
        assert "prayer2" in prayer_ids
        assert "prayer3" not in prayer_ids  # Too old
        
        # Verify ordering (most recent first)
        assert results[0][0].id == "prayer1"  # More recent mark
        assert results[1][0].id == "prayer2"  # Less recent mark
    
    def test_feed_filtering_with_complex_scenarios(self, test_session):
        """Test feed filtering with complex user interactions"""
        user1 = UserFactory.create(id="user1")
        user2 = UserFactory.create(id="user2")
        user3 = UserFactory.create(id="user3")
        
        # Prayer with marks from multiple users
        popular_prayer = PrayerFactory.create(
            id="popular", 
            author_id="user1", 
            flagged=False,
            text="Popular prayer"
        )
        
        # Prayer with single mark
        simple_prayer = PrayerFactory.create(
            id="simple", 
            author_id="user2", 
            flagged=False,
            text="Simple prayer"
        )
        
        # Prayer with no marks
        unprayed_prayer = PrayerFactory.create(
            id="unprayed", 
            author_id="user3", 
            flagged=False,
            text="Unprayed prayer"
        )
        
        # Multiple marks on popular prayer
        marks = [
            PrayerMarkFactory.create(user_id="user1", prayer_id="popular"),
            PrayerMarkFactory.create(user_id="user2", prayer_id="popular"),
            PrayerMarkFactory.create(user_id="user3", prayer_id="popular"),
            PrayerMarkFactory.create(user_id="user1", prayer_id="popular"),  # User1 marks twice
            PrayerMarkFactory.create(user_id="user2", prayer_id="simple")
        ]
        
        test_session.add_all([
            user1, user2, user3, popular_prayer, simple_prayer, unprayed_prayer
        ] + marks)
        test_session.commit()
        
        # Test "most_prayed" feed with mark counts
        most_prayed_stmt = (
            select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
            .join(User, Prayer.author_id == User.id)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.count(PrayerMark.id).desc())
        )
        most_prayed_results = test_session.exec(most_prayed_stmt).all()
        
        assert len(most_prayed_results) == 2  # Only prayers with marks
        assert most_prayed_results[0][0].id == "popular"  # 4 marks
        assert most_prayed_results[0][2] == 4  # Mark count
        assert most_prayed_results[1][0].id == "simple"  # 1 mark
        assert most_prayed_results[1][2] == 1  # Mark count
        
        # Test distinct user count
        distinct_users_stmt = (
            select(Prayer.id, func.count(func.distinct(PrayerMark.user_id)).label('user_count'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.id == "popular")
            .group_by(Prayer.id)
        )
        distinct_result = test_session.exec(distinct_users_stmt).first()
        assert distinct_result[1] == 3  # 3 distinct users marked popular prayer
    
    def test_my_prayers_feed_ordering(self, test_session):
        """Test my_prayers feed ordering by most recent mark"""
        user = UserFactory.create()
        user2 = UserFactory.create(id="user2")
        user3 = UserFactory.create(id="user3")
        user4 = UserFactory.create(id="user4")
        
        prayer1 = PrayerFactory.create(id="prayer1", author_id="user2", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_id="user3", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_id="user4", flagged=False)
        
        # User marks prayers at different times
        mark1 = PrayerMarkFactory.create(
            user_id=user.id, 
            prayer_id="prayer1",
            created_at=datetime.utcnow() - timedelta(hours=3)
        )
        mark2 = PrayerMarkFactory.create(
            user_id=user.id, 
            prayer_id="prayer2",
            created_at=datetime.utcnow() - timedelta(hours=1)  # Most recent
        )
        mark3 = PrayerMarkFactory.create(
            user_id=user.id, 
            prayer_id="prayer3",
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        
        test_session.add_all([user, user2, user3, user4, prayer1, prayer2, prayer3, mark1, mark2, mark3])
        test_session.commit()
        
        # Test my_prayers query with ordering
        my_prayers_stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.user_id == user.id)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
        )
        results = test_session.exec(my_prayers_stmt).all()
        
        # Should be ordered by most recent mark first
        assert len(results) == 3
        assert results[0][0].id == "prayer2"  # Most recent mark
        assert results[1][0].id == "prayer3"  # Middle
        assert results[2][0].id == "prayer1"  # Oldest mark


@pytest.mark.unit
class TestAdminPanelFunctionality:
    """Test admin panel specific functionality"""
    
    def test_admin_panel_flagged_prayers_retrieval(self, test_session):
        """Test admin panel retrieval of flagged prayers with author info"""
        user1 = UserFactory.create(display_name="User One")
        user2 = UserFactory.create(display_name="User Two")
        
        # Normal prayers (should not appear in admin panel)
        normal_prayer = PrayerFactory.create(
            author_id=user1.id, 
            flagged=False,
            text="Normal prayer"
        )
        
        # Flagged prayers (should appear in admin panel)
        flagged1 = PrayerFactory.create(
            author_id=user1.id, 
            flagged=True,
            text="Flagged prayer 1"
        )
        flagged2 = PrayerFactory.create(
            author_id=user2.id, 
            flagged=True,
            text="Flagged prayer 2"
        )
        
        test_session.add_all([user1, user2, normal_prayer, flagged1, flagged2])
        test_session.commit()
        
        # Simulate admin panel query from app.py
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .where(Prayer.flagged == True)
        )
        flagged_results = test_session.exec(stmt).all()
        
        assert len(flagged_results) == 2
        
        # Check author names are included
        prayer_authors = [(result[0].text, result[1]) for result in flagged_results]
        assert ("Flagged prayer 1", "User One") in prayer_authors
        assert ("Flagged prayer 2", "User Two") in prayer_authors
    
    def test_admin_authentication_requests_with_approvals(self, test_session):
        """Test admin panel auth requests with approval information"""
        user1 = UserFactory.create(display_name="Requester One")
        user2 = UserFactory.create(display_name="Requester Two")
        approver1 = UserFactory.create(display_name="Approver One")
        approver2 = UserFactory.create(display_name="Approver Two")
        admin = UserFactory.create(id="admin", display_name="Admin User")
        
        # Auth request with multiple approvals
        auth_req1 = AuthenticationRequestFactory.create(
            user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        # Auth request with admin approval
        auth_req2 = AuthenticationRequestFactory.create(
            user_id=user2.id,
            status="approved",
            approved_by_user_id=admin.id,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        # Approvals for first request
        approval1 = AuthApprovalFactory.create(
            auth_request_id=auth_req1.id,
            approver_user_id=approver1.id
        )
        approval2 = AuthApprovalFactory.create(
            auth_request_id=auth_req1.id,
            approver_user_id=approver2.id
        )
        
        test_session.add_all([
            user1, user2, approver1, approver2, admin,
            auth_req1, auth_req2, approval1, approval2
        ])
        test_session.commit()
        
        # Simulate admin panel auth requests query
        auth_requests_stmt = (
            select(AuthenticationRequest, User.display_name)
            .join(User, AuthenticationRequest.user_id == User.id)
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(AuthenticationRequest.created_at.desc())
        )
        auth_results = test_session.exec(auth_requests_stmt).all()
        
        assert len(auth_results) == 2
        
        # Get approval information for first request
        approvals_stmt = (
            select(AuthApproval, User.display_name)
            .join(User, AuthApproval.approver_user_id == User.id)
            .where(AuthApproval.auth_request_id == auth_req1.id)
        )
        approval_results = test_session.exec(approvals_stmt).all()
        
        assert len(approval_results) == 2
        approver_names = [result[1] for result in approval_results]
        assert "Approver One" in approver_names
        assert "Approver Two" in approver_names
    
    def test_admin_permissions_checking(self, test_session):
        """Test admin permission checking functionality"""
        admin_user = UserFactory.create(id="admin")
        regular_user = UserFactory.create(id="regular_123")
        fake_admin = UserFactory.create(id="not_admin", display_name="admin")
        
        test_session.add_all([admin_user, regular_user, fake_admin])
        test_session.commit()
        
        # Test admin permissions
        assert is_admin(admin_user) is True
        assert is_admin(regular_user) is False
        assert is_admin(fake_admin) is False  # Name doesn't matter, only ID
        
        # Test admin-only operations simulation
        def admin_only_operation(user):
            if not is_admin(user):
                raise PermissionError("Admin required")
            return "Success"
        
        # Admin can perform operation
        result = admin_only_operation(admin_user)
        assert result == "Success"
        
        # Regular user cannot
        with pytest.raises(PermissionError):
            admin_only_operation(regular_user)
        
        # Fake admin cannot
        with pytest.raises(PermissionError):
            admin_only_operation(fake_admin)


@pytest.mark.unit
class TestBulkOperations:
    """Test bulk administrative operations"""
    
    def test_bulk_approve_authentication_requests(self, test_session):
        """Test bulk approval of multiple authentication requests"""
        admin = UserFactory.create(id="admin")
        
        # Create multiple pending requests
        user1 = UserFactory.create(id="user1")
        user2 = UserFactory.create(id="user2")
        user3 = UserFactory.create(id="user3")
        
        pending_req1 = AuthenticationRequestFactory.create(
            user_id="user1",
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        pending_req2 = AuthenticationRequestFactory.create(
            user_id="user2",
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        pending_req3 = AuthenticationRequestFactory.create(
            user_id="user3",
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        # Expired request (should not be approved)
        expired_req = AuthenticationRequestFactory.create(
            user_id="user1",
            status="pending",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Already approved request (should not be changed)
        approved_req = AuthenticationRequestFactory.create(
            user_id="user2",
            status="approved",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        test_session.add_all([
            admin, user1, user2, user3,
            pending_req1, pending_req2, pending_req3, expired_req, approved_req
        ])
        test_session.commit()
        
        # Simulate bulk approval logic from app.py
        pending_requests = test_session.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
        ).all()
        
        approved_count = 0
        for auth_req in pending_requests:
            auth_req.status = "approved"
            auth_req.approved_by_user_id = admin.id
            auth_req.approved_at = datetime.utcnow()
            approved_count += 1
        
        test_session.commit()
        
        # Verify bulk approval results
        assert approved_count == 3  # Only pending, non-expired requests
        
        # Check individual statuses
        assert test_session.get(AuthenticationRequest, pending_req1.id).status == "approved"
        assert test_session.get(AuthenticationRequest, pending_req2.id).status == "approved"
        assert test_session.get(AuthenticationRequest, pending_req3.id).status == "approved"
        assert test_session.get(AuthenticationRequest, expired_req.id).status == "pending"  # Not touched
        assert test_session.get(AuthenticationRequest, approved_req.id).status == "approved"  # Already approved
    
    def test_bulk_cleanup_expired_requests(self, test_session):
        """Test bulk cleanup of expired authentication requests"""
        # Create requests with various statuses and expiration times
        user = UserFactory.create()
        
        # Expired pending request (should be marked expired)
        expired_pending = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Expired approved request (should not be touched)
        expired_approved = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="approved",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Valid pending request (should not be touched)
        valid_pending = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        test_session.add_all([user, expired_pending, expired_approved, valid_pending])
        test_session.commit()
        
        # Simulate cleanup logic from app.py
        expired_requests = test_session.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at < datetime.utcnow())
        ).all()
        
        for req in expired_requests:
            req.status = "expired"
        
        test_session.commit()
        
        # Verify cleanup results
        assert test_session.get(AuthenticationRequest, expired_pending.id).status == "expired"
        assert test_session.get(AuthenticationRequest, expired_approved.id).status == "approved"  # Unchanged
        assert test_session.get(AuthenticationRequest, valid_pending.id).status == "pending"  # Unchanged
    
    def test_bulk_prayer_moderation(self, test_session):
        """Test bulk prayer moderation operations"""
        admin = UserFactory.create(id="admin")
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        # Create various prayers
        normal_prayer1 = PrayerFactory.create(author_id=user1.id, flagged=False)
        normal_prayer2 = PrayerFactory.create(author_id=user2.id, flagged=False)
        flagged_prayer1 = PrayerFactory.create(author_id=user1.id, flagged=True)
        flagged_prayer2 = PrayerFactory.create(author_id=user2.id, flagged=True)
        
        test_session.add_all([admin, user1, user2, normal_prayer1, normal_prayer2, flagged_prayer1, flagged_prayer2])
        test_session.commit()
        
        # Simulate bulk unflagging operation (admin only)
        if is_admin(admin):
            flagged_prayers = test_session.exec(
                select(Prayer).where(Prayer.flagged == True)
            ).all()
            
            unflagged_count = 0
            for prayer in flagged_prayers:
                prayer.flagged = False
                unflagged_count += 1
        
        test_session.commit()
        
        # Verify bulk unflagging
        assert unflagged_count == 2
        assert test_session.get(Prayer, flagged_prayer1.id).flagged is False
        assert test_session.get(Prayer, flagged_prayer2.id).flagged is False
        
        # Normal prayers should be unchanged
        assert test_session.get(Prayer, normal_prayer1.id).flagged is False
        assert test_session.get(Prayer, normal_prayer2.id).flagged is False
    
    def test_bulk_session_cleanup(self, test_session):
        """Test bulk cleanup of expired sessions"""
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        # Expired sessions
        expired_session1 = SessionFactory.create(
            user_id=user1.id,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        expired_session2 = SessionFactory.create(
            user_id=user2.id,
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        
        # Valid sessions
        valid_session1 = SessionFactory.create(
            user_id=user1.id,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        valid_session2 = SessionFactory.create(
            user_id=user2.id,
            expires_at=datetime.utcnow() + timedelta(days=14)
        )
        
        test_session.add_all([
            user1, user2, expired_session1, expired_session2, valid_session1, valid_session2
        ])
        test_session.commit()
        
        # Simulate bulk session cleanup
        expired_sessions = test_session.exec(
            select(SessionModel)
            .where(SessionModel.expires_at < datetime.utcnow())
        ).all()
        
        # Delete expired sessions
        for session in expired_sessions:
            test_session.delete(session)
        
        test_session.commit()
        
        # Verify cleanup
        assert test_session.get(SessionModel, expired_session1.id) is None
        assert test_session.get(SessionModel, expired_session2.id) is None
        assert test_session.get(SessionModel, valid_session1.id) is not None
        assert test_session.get(SessionModel, valid_session2.id) is not None