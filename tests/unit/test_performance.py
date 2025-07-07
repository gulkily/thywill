"""Performance tests for prayer attributes system"""
import pytest
import time
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

from models import Prayer, PrayerAttribute, PrayerMark, User
from tests.factories import UserFactory, PrayerFactory, PrayerAttributeFactory, PrayerMarkFactory


@pytest.mark.performance
class TestAttributeQueryPerformance:
    """Test performance of attribute-based queries"""
    
    @pytest.fixture
    def large_dataset(self, test_session):
        """Create a large dataset for performance testing"""
        users = [UserFactory.create() for _ in range(10)]
        test_session.add_all(users)
        test_session.commit()
        
        # Create 1000 prayers with various statuses
        prayers = []
        for i in range(1000):
            prayer = PrayerFactory.create(author_username=users[i % 10].display_name)
            prayers.append(prayer)
        
        test_session.add_all(prayers)
        test_session.commit()
        
        # Add attributes to some prayers
        attributes = []
        for i, prayer in enumerate(prayers):
            if i % 10 == 0:  # 10% archived
                attributes.append(PrayerAttributeFactory.create(
                    prayer_id=prayer.id, 
                    attribute_name='archived',
                    created_by=prayer.author_username
                ))
            if i % 15 == 0:  # ~6.7% answered
                attributes.append(PrayerAttributeFactory.create(
                    prayer_id=prayer.id,
                    attribute_name='answered', 
                    created_by=prayer.author_username
                ))
            if i % 50 == 0:  # 2% flagged
                attributes.append(PrayerAttributeFactory.create(
                    prayer_id=prayer.id,
                    attribute_name='flagged',
                    created_by=prayer.author_username
                ))
        
        test_session.add_all(attributes)
        test_session.commit()
        
        return users, prayers
    
    def test_feed_query_performance(self, test_session, large_dataset):
        """Test performance of main feed query with large dataset"""
        users, prayers = large_dataset
        
        start_time = time.time()
        
        # Main feed query (exclude archived)
        active_prayers = test_session.exec(
            select(Prayer)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .order_by(Prayer.created_at.desc())
            .limit(50)  # Typical page size
        ).all()
        
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert query_time < 0.5  # 500ms threshold
        assert len(active_prayers) == 50
        
        # Verify no archived prayers in results
        for prayer in active_prayers:
            assert not prayer.is_archived(test_session)
    
    def test_answered_feed_query_performance(self, test_session, large_dataset):
        """Test performance of answered feed query"""
        users, prayers = large_dataset
        
        start_time = time.time()
        
        # Answered feed query
        answered_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
            .limit(50)
        ).all()
        
        query_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert query_time < 0.5  # 500ms threshold
        
        # Verify all returned prayers are answered
        for prayer in answered_prayers:
            assert prayer.is_answered(test_session)
    
    def test_attribute_count_performance(self, test_session, large_dataset):
        """Test performance of feed count calculations"""
        users, prayers = large_dataset
        
        start_time = time.time()
        
        # Calculate all feed counts (similar to get_feed_counts function)
        total_count = test_session.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
        ).first()
        
        answered_count = test_session.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).first()
        
        query_time = time.time() - start_time
        
        # Count calculations should be fast
        assert query_time < 0.3  # 300ms threshold
        assert total_count > 0
        assert answered_count >= 0
    
    def test_user_archived_query_performance(self, test_session, large_dataset):
        """Test performance of user-specific archived feed"""
        users, prayers = large_dataset
        user = users[0]
        
        start_time = time.time()
        
        # User's archived prayers
        archived_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user.display_name)
            .where(PrayerAttribute.attribute_name == 'archived')
            .order_by(Prayer.created_at.desc())
        ).all()
        
        query_time = time.time() - start_time
        
        # Should be very fast for user-specific queries
        assert query_time < 0.2  # 200ms threshold
        
        # Verify all belong to user and are archived
        for prayer in archived_prayers:
            assert prayer.author_username == user.display_name
            assert prayer.is_archived(test_session)


@pytest.mark.performance
class TestAttributeOperationPerformance:
    """Test performance of attribute CRUD operations"""
    
    def test_bulk_attribute_setting_performance(self, test_session):
        """Test performance of setting attributes on many prayers"""
        user = UserFactory.create()
        prayers = [PrayerFactory.create(author_username=user.display_name) for _ in range(100)]
        test_session.add_all([user] + prayers)
        test_session.commit()
        
        start_time = time.time()
        
        # Set archived status on all prayers
        for prayer in prayers:
            prayer.set_attribute('archived', 'true', user.display_name, test_session)
        
        test_session.commit()
        
        operation_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert operation_time < 2.0  # 2 second threshold for 100 operations
        
        # Verify all prayers are archived
        for prayer in prayers:
            assert prayer.is_archived(test_session)
    
    def test_attribute_lookup_performance(self, test_session):
        """Test performance of attribute lookups"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set multiple attributes
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        prayer.set_attribute('answered', 'true', user.display_name, test_session)
        prayer.set_attribute('answer_testimony', 'Long testimony text here...', user.display_name, test_session)
        test_session.commit()
        
        start_time = time.time()
        
        # Perform many attribute lookups
        for _ in range(1000):
            prayer.is_archived(test_session)
            prayer.is_answered(test_session)
            prayer.answer_testimony(test_session)
        
        lookup_time = time.time() - start_time
        
        # Lookups should be fast
        assert lookup_time < 1.0  # 1 second for 1000 lookups


@pytest.mark.performance
class TestDatabaseIndexEfficiency:
    """Test that database indexes are working effectively"""
    
    def test_prayer_attribute_index_usage(self, test_session):
        """Test that queries use indexes efficiently"""
        # Create test data
        user = UserFactory.create()
        prayers = [PrayerFactory.create(author_username=user.display_name) for _ in range(100)]
        test_session.add_all([user] + prayers)
        test_session.commit()
        
        # Add attributes to half the prayers
        for i, prayer in enumerate(prayers[:50]):
            prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # This query should use the composite index on (prayer_id, attribute_name)
        start_time = time.time()
        
        archived_ids = test_session.exec(
            select(PrayerAttribute.prayer_id)
            .where(PrayerAttribute.attribute_name == 'archived')
        ).all()
        
        query_time = time.time() - start_time
        
        # Should be very fast with proper indexing
        assert query_time < 0.1  # 100ms threshold
        assert len(archived_ids) == 50
    
    def test_prayer_filtering_index_usage(self, test_session):
        """Test that prayer filtering queries use indexes"""
        user = UserFactory.create()
        prayers = [PrayerFactory.create(author_username=user.display_name) for _ in range(200)]
        test_session.add_all([user] + prayers)
        test_session.commit()
        
        # Archive some prayers
        for prayer in prayers[::5]:  # Every 5th prayer
            prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        start_time = time.time()
        
        # Complex query that should benefit from indexing
        active_prayers = test_session.exec(
            select(Prayer)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user.display_name)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .order_by(Prayer.created_at.desc())
        ).all()
        
        query_time = time.time() - start_time
        
        # Should complete quickly with proper indexes
        assert query_time < 0.2  # 200ms threshold
        assert len(active_prayers) == 160  # 200 - 40 archived
    
    def test_join_performance(self, test_session):
        """Test performance of prayer-attribute joins"""
        user = UserFactory.create()
        prayers = [PrayerFactory.create(author_username=user.display_name) for _ in range(100)]
        test_session.add_all([user] + prayers)
        test_session.commit()
        
        # Add answered status to prayers
        for prayer in prayers[::3]:  # Every 3rd prayer
            prayer.set_attribute('answered', 'true', user.display_name, test_session)
            prayer.set_attribute('answer_testimony', f'Testimony for prayer {prayer.id}', user.display_name, test_session)
        test_session.commit()
        
        start_time = time.time()
        
        # Join query that loads prayers with their answered attributes
        answered_prayers = test_session.exec(
            select(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).all()
        
        query_time = time.time() - start_time
        
        # Join should be efficient
        assert query_time < 0.15  # 150ms threshold
        assert len(answered_prayers) > 0
        
        # Verify testimonies can be loaded efficiently
        for prayer in answered_prayers:
            testimony = prayer.answer_testimony(test_session)
            assert testimony is not None


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory efficiency of attribute operations"""
    
    def test_large_dataset_memory_usage(self, test_session):
        """Test that large datasets don't cause memory issues"""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large dataset
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        prayers = []
        for i in range(1000):
            prayer = PrayerFactory.create(author_username=user.display_name)
            prayers.append(prayer)
            
            # Add attributes to some prayers
            if i % 5 == 0:
                prayer.set_attribute('archived', 'true', user.display_name, test_session)
            if i % 7 == 0:
                prayer.set_attribute('answered', 'true', user.display_name, test_session)
        
        test_session.add_all(prayers)
        test_session.commit()
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for 1000 prayers)
        assert memory_increase < 50 * 1024 * 1024  # 50MB threshold
    
    def test_attribute_query_memory_efficiency(self, test_session):
        """Test that attribute queries don't load excessive data"""
        user = UserFactory.create()
        prayers = [PrayerFactory.create(author_username=user.display_name) for _ in range(500)]
        test_session.add_all([user] + prayers)
        test_session.commit()
        
        # Add many attributes
        for prayer in prayers:
            prayer.set_attribute('archived', 'true', user.display_name, test_session)
            prayer.set_attribute('answer_testimony', 'Long testimony text ' * 50, user.display_name, test_session)
        test_session.commit()
        
        # Query that should only load prayer IDs, not full objects
        start_time = time.time()
        
        archived_ids = test_session.exec(
            select(PrayerAttribute.prayer_id)
            .where(PrayerAttribute.attribute_name == 'archived')
        ).all()
        
        query_time = time.time() - start_time
        
        # Should be fast and memory-efficient
        assert query_time < 0.2
        assert len(archived_ids) == 500
        
        # Should not have loaded full prayer objects or testimonies
        # This is ensured by only selecting prayer_id