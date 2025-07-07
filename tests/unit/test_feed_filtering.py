"""Unit tests for enhanced feed system with attribute filtering"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

from models import Prayer, PrayerAttribute, PrayerMark, User
from tests.factories import UserFactory, PrayerFactory, PrayerAttributeFactory, PrayerMarkFactory


@pytest.mark.unit
class TestFeedCounts:
    """Test feed count calculations with attributes"""
    
    def test_feed_counts_exclude_archived_prayers(self, test_session):
        """Test that feed counts exclude archived prayers"""
        user = UserFactory.create()
        
        # Create active and archived prayers
        active_prayer = PrayerFactory.create(author_username=user.display_name)
        archived_prayer = PrayerFactory.create(author_username=user.display_name)
        
        test_session.add_all([user, active_prayer, archived_prayer])
        test_session.commit()
        
        # Archive one prayer
        archived_prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Count active prayers (should exclude archived)
        active_count = test_session.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
        ).first()
        
        assert active_count == 1
    
    def test_answered_prayers_count(self, test_session):
        """Test counting answered prayers"""
        user = UserFactory.create()
        
        # Create regular and answered prayers
        regular_prayer = PrayerFactory.create(author_username=user.display_name)
        answered_prayer = PrayerFactory.create(author_username=user.display_name)
        
        test_session.add_all([user, regular_prayer, answered_prayer])
        test_session.commit()
        
        # Mark one as answered
        answered_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Count answered prayers
        answered_count = test_session.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).first()
        
        assert answered_count == 1
    
    def test_user_specific_archived_count(self, test_session):
        """Test counting archived prayers for specific user"""
        user1 = UserFactory.create(display_name="User 1")
        user2 = UserFactory.create(display_name="User 2")
        
        # Create prayers for both users
        user1_prayer = PrayerFactory.create(author_username=user1.display_name)
        user2_prayer = PrayerFactory.create(author_username=user2.display_name)
        
        test_session.add_all([user1, user2, user1_prayer, user2_prayer])
        test_session.commit()
        
        # Archive both prayers
        user1_prayer.set_attribute('archived', 'true', user1.display_name, test_session)
        user2_prayer.set_attribute('archived', 'true', user2.display_name, test_session)
        test_session.commit()
        
        # Count archived prayers for user1 only
        user1_archived_count = test_session.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user1.display_name)
            .where(PrayerAttribute.attribute_name == 'archived')
        ).first()
        
        assert user1_archived_count == 1


@pytest.mark.unit
class TestFeedQueries:
    """Test feed query filtering with attributes"""
    
    def test_all_feed_excludes_archived(self, test_session):
        """Test that 'all' feed excludes archived prayers"""
        user = UserFactory.create()
        
        # Create mix of prayers
        active_prayer = PrayerFactory.create(author_username=user.display_name, text="Active prayer")
        archived_prayer = PrayerFactory.create(author_username=user.display_name, text="Archived prayer")
        answered_prayer = PrayerFactory.create(author_username=user.display_name, text="Answered prayer")
        
        test_session.add_all([user, active_prayer, archived_prayer, answered_prayer])
        test_session.commit()
        
        # Set statuses
        archived_prayer.set_attribute('archived', 'true', user.display_name, test_session)
        answered_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query 'all' feed (exclude archived)
        all_prayers = test_session.exec(
            select(Prayer)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # Should include active and answered, but not archived
        prayer_texts = [p.text for p in all_prayers]
        assert "Active prayer" in prayer_texts
        assert "Answered prayer" in prayer_texts
        assert "Archived prayer" not in prayer_texts
    
    def test_answered_feed_includes_only_answered(self, test_session):
        """Test that answered feed includes only answered prayers"""
        user = UserFactory.create()
        
        # Create mix of prayers
        active_prayer = PrayerFactory.create(author_username=user.display_name, text="Active prayer")
        answered_prayer = PrayerFactory.create(author_username=user.display_name, text="Answered prayer")
        answered_archived_prayer = PrayerFactory.create(author_username=user.display_name, text="Answered and archived")
        
        test_session.add_all([user, active_prayer, answered_prayer, answered_archived_prayer])
        test_session.commit()
        
        # Set statuses
        answered_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        answered_archived_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        answered_archived_prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query answered feed
        answered_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # Should include both answered prayers (archived status doesn't matter for answered feed)
        prayer_texts = [p.text for p in answered_prayers]
        assert "Answered prayer" in prayer_texts
        assert "Answered and archived" in prayer_texts
        assert "Active prayer" not in prayer_texts
    
    def test_archived_feed_user_specific(self, test_session):
        """Test that archived feed is user-specific"""
        user1 = UserFactory.create(display_name="User 1")
        user2 = UserFactory.create(display_name="User 2")
        
        # Create prayers for both users
        user1_archived = PrayerFactory.create(author_username=user1.display_name, text="User 1 archived")
        user2_archived = PrayerFactory.create(author_username=user2.display_name, text="User 2 archived")
        
        test_session.add_all([user1, user2, user1_archived, user2_archived])
        test_session.commit()
        
        # Archive both prayers
        user1_archived.set_attribute('archived', 'true', user1.display_name, test_session)
        user2_archived.set_attribute('archived', 'true', user2.display_name, test_session)
        test_session.commit()
        
        # Query archived feed for user1
        user1_archived_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user1.display_name)
            .where(PrayerAttribute.attribute_name == 'archived')
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # Should only include user1's archived prayers
        prayer_texts = [p.text for p in user1_archived_prayers]
        assert "User 1 archived" in prayer_texts
        assert "User 2 archived" not in prayer_texts
    
    def test_new_unprayed_excludes_archived(self, test_session):
        """Test that new/unprayed feed excludes archived prayers"""
        user = UserFactory.create()
        
        # Create prayers without prayer marks
        new_prayer = PrayerFactory.create(author_username=user.display_name, text="New prayer")
        archived_unprayed = PrayerFactory.create(author_username=user.display_name, text="Archived unprayed")
        
        test_session.add_all([user, new_prayer, archived_unprayed])
        test_session.commit()
        
        # Archive one prayer
        archived_unprayed.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query new/unprayed feed
        new_prayers = test_session.exec(
            select(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .group_by(Prayer.id)
            .having(func.count(PrayerMark.id) == 0)
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # Should only include new (non-archived) prayer
        prayer_texts = [p.text for p in new_prayers]
        assert "New prayer" in prayer_texts
        assert "Archived unprayed" not in prayer_texts


@pytest.mark.unit
class TestFeedPermissions:
    """Test feed access permissions"""
    
    def test_my_requests_includes_all_statuses(self, test_session):
        """Test that 'my requests' feed includes all user's prayers regardless of status"""
        user = UserFactory.create()
        
        # Create prayers with different statuses
        active_prayer = PrayerFactory.create(author_username=user.display_name, text="Active")
        archived_prayer = PrayerFactory.create(author_username=user.display_name, text="Archived") 
        answered_prayer = PrayerFactory.create(author_username=user.display_name, text="Answered")
        
        test_session.add_all([user, active_prayer, archived_prayer, answered_prayer])
        test_session.commit()
        
        # Set statuses
        archived_prayer.set_attribute('archived', 'true', user.display_name, test_session)
        answered_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query user's requests (should include all)
        user_prayers = test_session.exec(
            select(Prayer)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user.display_name)
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # Should include all prayers regardless of status
        prayer_texts = [p.text for p in user_prayers]
        assert "Active" in prayer_texts
        assert "Archived" in prayer_texts
        assert "Answered" in prayer_texts
        assert len(user_prayers) == 3
    
    def test_my_prayers_includes_all_statuses(self, test_session):
        """Test that 'my prayers' feed includes prayers user marked regardless of status"""
        user = UserFactory.create()
        author = UserFactory.create(display_name="Author")
        
        # Create prayers by author
        active_prayer = PrayerFactory.create(author_username=author.display_name, text="Active")
        archived_prayer = PrayerFactory.create(author_username=author.display_name, text="Archived")
        
        test_session.add_all([user, author, active_prayer, archived_prayer])
        test_session.commit()
        
        # User marks both prayers
        mark1 = PrayerMarkFactory.create(username=user.display_name, prayer_id=active_prayer.id)
        mark2 = PrayerMarkFactory.create(username=user.display_name, prayer_id=archived_prayer.id)
        test_session.add_all([mark1, mark2])
        test_session.commit()
        
        # Archive one prayer
        archived_prayer.set_attribute('archived', 'true', author.display_name, test_session)
        test_session.commit()
        
        # Query prayers user has marked (should include archived ones too)
        marked_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.username == user.display_name)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
        ).all()
        
        # Should include both prayers even though one is archived
        prayer_texts = [p.text for p in marked_prayers]
        assert "Active" in prayer_texts
        assert "Archived" in prayer_texts
        assert len(marked_prayers) == 2


@pytest.mark.unit  
class TestNewFeedTypes:
    """Test new feed types (answered, archived)"""
    
    def test_answered_feed_with_testimonies(self, test_session):
        """Test answered feed includes testimonies"""
        user = UserFactory.create()
        
        # Create answered prayers with and without testimonies
        answered_with_testimony = PrayerFactory.create(author_username=user.display_name, text="With testimony")
        answered_without_testimony = PrayerFactory.create(author_username=user.display_name, text="Without testimony")
        
        test_session.add_all([user, answered_with_testimony, answered_without_testimony])
        test_session.commit()
        
        # Mark both as answered
        answered_with_testimony.set_attribute('answered', 'true', user.display_name, test_session)
        answered_with_testimony.set_attribute('answer_testimony', 'God is faithful!', user.display_name, test_session)
        
        answered_without_testimony.set_attribute('answered', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query answered feed
        answered_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
        ).all()
        
        assert len(answered_prayers) == 2
        
        # Verify testimonies are accessible
        prayer_with_testimony = next(p for p in answered_prayers if p.text == "With testimony")
        assert prayer_with_testimony.answer_testimony(test_session) == 'God is faithful!'
        
        prayer_without_testimony = next(p for p in answered_prayers if p.text == "Without testimony")
        assert prayer_without_testimony.answer_testimony(test_session) is None
    
    def test_archived_feed_privacy(self, test_session):
        """Test that archived feed respects privacy (user's own prayers only)"""
        user1 = UserFactory.create(display_name="User 1")
        user2 = UserFactory.create(display_name="User 2")
        
        # Create archived prayers for both users
        user1_prayer = PrayerFactory.create(author_username=user1.display_name, text="User 1 prayer")
        user2_prayer = PrayerFactory.create(author_username=user2.display_name, text="User 2 prayer")
        
        test_session.add_all([user1, user2, user1_prayer, user2_prayer])
        test_session.commit()
        
        # Archive both
        user1_prayer.set_attribute('archived', 'true', user1.display_name, test_session)
        user2_prayer.set_attribute('archived', 'true', user2.display_name, test_session)
        test_session.commit()
        
        # User1's archived feed should only show their prayers
        user1_archived = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user1.display_name)  # This enforces privacy
            .where(PrayerAttribute.attribute_name == 'archived')
        ).all()
        
        assert len(user1_archived) == 1
        assert user1_archived[0].text == "User 1 prayer"
    
    def test_feed_ordering_consistency(self, test_session):
        """Test that feeds maintain consistent ordering"""
        user = UserFactory.create()
        
        # Create prayers with specific timestamps
        now = datetime.utcnow()
        old_prayer = PrayerFactory.create(
            author_username=user.display_name, 
            text="Old prayer",
            created_at=now - timedelta(hours=2)
        )
        new_prayer = PrayerFactory.create(
            author_username=user.display_name,
            text="New prayer", 
            created_at=now
        )
        
        test_session.add_all([user, old_prayer, new_prayer])
        test_session.commit()
        
        # Mark both as answered
        old_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        new_prayer.set_attribute('answered', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Query answered feed (should be ordered by creation date desc)
        answered_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
        ).all()
        
        # New prayer should come first
        assert answered_prayers[0].text == "New prayer"
        assert answered_prayers[1].text == "Old prayer"