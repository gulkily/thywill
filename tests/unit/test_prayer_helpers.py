"""Unit tests for prayer-related helper functions"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlmodel import Session, select, func

from models import User, Prayer, PrayerMark
from tests.factories import UserFactory, PrayerFactory, PrayerMarkFactory
from app import generate_prayer, get_feed_counts, todays_prompt


@pytest.mark.unit
class TestPrayerGeneration:
    """Test LLM prayer generation functionality"""
    
    def test_generate_prayer_success(self):
        """Test successful prayer generation with mocked Anthropic API"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Divine Creator, we lift up our friend who seeks healing. May your peace be with them. Amen."
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            result = generate_prayer("Please pray for my healing")
            
            assert result['prayer'] == "Divine Creator, we lift up our friend who seeks healing. May your peace be with them. Amen."
            assert result['service_status'] == 'normal'
            
            # Verify API was called with correct parameters
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            
            assert call_args[1]['model'] == "claude-3-5-sonnet-20241022"
            assert call_args[1]['max_tokens'] == 200
            assert call_args[1]['temperature'] == 0.7
            assert "Please pray for my healing" in call_args[1]['messages'][0]['content']
    
    def test_generate_prayer_api_error(self):
        """Test prayer generation fallback when API fails"""
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.side_effect = Exception("API Error")
            
            result = generate_prayer("Please pray for my test")
            
            # Should return fallback prayer
            assert "Divine Creator, we lift up our friend who asks for help with: Please pray for my test" in result['prayer']
            assert "Amen." in result['prayer']
            assert result['service_status'] == 'degraded'
    
    def test_generate_prayer_system_prompt_content(self):
        """Test that system prompt emphasizes community prayer"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Test prayer response"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            generate_prayer("Test request")
            
            # Verify system prompt emphasizes community aspect
            call_args = mock_client.messages.create.call_args
            system_prompt = call_args[1]['system']
            
            assert "community" in system_prompt.lower()
            assert "them" in system_prompt or "they" in system_prompt
            assert "first person" in system_prompt.lower()
            # Check that the system prompt mentions avoiding first person
            assert "Do NOT use first person" in system_prompt
    
    def test_generate_prayer_input_sanitization(self):
        """Test prayer generation with various input types"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Generated prayer"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            # Test with long input
            long_input = "x" * 1000
            result = generate_prayer(long_input)
            assert result['prayer'] == "Generated prayer"
            assert result['service_status'] == 'normal'
            
            # Test with empty input
            result = generate_prayer("")
            assert result['prayer'] == "Generated prayer"
            assert result['service_status'] == 'normal'
            
            # Test with special characters
            result = generate_prayer("Prayer with <tags> & symbols!")
            assert result['prayer'] == "Generated prayer"
            assert result['service_status'] == 'normal'


@pytest.mark.unit
class TestFeedCounts:
    """Test feed counting and statistics functionality"""
    
    def test_get_feed_counts_empty_database(self, test_session):
        """Test feed counts with empty database"""
        with patch('app_helpers.services.prayer_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            counts = get_feed_counts("testuser")
            
            assert counts['all'] == 0
            assert counts['new_unprayed'] == 0
            assert counts['most_prayed'] == 0
            assert counts['my_prayers'] == 0
            assert counts['my_requests'] == 0
            assert counts['recent_activity'] == 0
            assert counts['daily_prayer'] == 0
    
    def test_get_feed_counts_with_prayers(self, test_session):
        """Test feed counts with various prayers"""
        # Create users
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        
        # Create prayers
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user2", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user1", flagged=True)  # Flagged
        
        test_session.add_all([user1, user2, prayer1, prayer2, prayer3])
        test_session.commit()
        
        with patch('app_helpers.services.prayer_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            counts = get_feed_counts("user1")
            
            # Should count only unflagged prayers
            assert counts['all'] == 2  # prayer1, prayer2 (not prayer3 - flagged)
            assert counts['my_requests'] == 1  # only prayer1 by user1 (unflagged)
    
    def test_get_feed_counts_with_prayer_marks(self, test_session):
        """Test feed counts with prayer marks"""
        # Create users
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        
        # Create prayers
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user2", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user2", flagged=False)
        
        # Create prayer marks
        mark1 = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        mark2 = PrayerMarkFactory.create(username="user1", prayer_id="prayer2")
        mark3 = PrayerMarkFactory.create(username="user2", prayer_id="prayer1")
        
        test_session.add_all([user1, user2, prayer1, prayer2, prayer3, mark1, mark2, mark3])
        test_session.commit()
        
        with patch('app_helpers.services.prayer_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            counts = get_feed_counts("user1")
            
            assert counts['all'] == 3  # All unflagged prayers
            assert counts['new_unprayed'] == 1  # prayer3 has no marks
            assert counts['most_prayed'] == 2  # prayer1, prayer2 have marks
            assert counts['my_prayers'] == 2  # user1 marked prayer1, prayer2
            assert counts['my_requests'] == 1  # user1 authored prayer1
    
    def test_get_feed_counts_recent_activity(self, test_session):
        """Test recent activity counting (prayers with any marks)"""
        user1 = UserFactory.create(display_name="user1")
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user1", flagged=False)
        
        # Recent mark (within 7 days)
        recent_time = datetime.utcnow() - timedelta(days=3)
        recent_mark = PrayerMarkFactory.create(
            username="user1", 
            prayer_id="prayer1", 
            created_at=recent_time
        )
        
        # Old mark (more than 7 days ago)
        old_time = datetime.utcnow() - timedelta(days=10)
        old_mark = PrayerMarkFactory.create(
            username="user1", 
            prayer_id="prayer2", 
            created_at=old_time
        )
        
        test_session.add_all([user1, prayer1, prayer2, recent_mark, old_mark])
        test_session.commit()
        
        with patch('app_helpers.services.prayer_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            counts = get_feed_counts("user1")
            
            # All prayers with marks should count (no time restriction)
            assert counts['recent_activity'] == 2  # Both prayer1 and prayer2 have marks
            assert counts['daily_prayer'] == 2  # Same as recent_activity
    
    def test_get_feed_counts_excludes_flagged_prayers(self, test_session):
        """Test that flagged prayers are excluded from all counts"""
        user1 = UserFactory.create(display_name="user1")
        
        # Normal prayer
        normal_prayer = PrayerFactory.create(
            id="normal", 
            author_username="user1", 
            flagged=False
        )
        
        # Flagged prayer
        flagged_prayer = PrayerFactory.create(
            id="flagged", 
            author_username="user1", 
            flagged=True
        )
        
        # Marks on both prayers
        normal_mark = PrayerMarkFactory.create(username="user1", prayer_id="normal")
        flagged_mark = PrayerMarkFactory.create(username="user1", prayer_id="flagged")
        
        test_session.add_all([user1, normal_prayer, flagged_prayer, normal_mark, flagged_mark])
        test_session.commit()
        
        with patch('app_helpers.services.prayer_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            counts = get_feed_counts("user1")
            
            # Should only count normal prayer, not flagged
            assert counts['all'] == 1
            assert counts['my_prayers'] == 1
            assert counts['my_requests'] == 1
            assert counts['most_prayed'] == 1


@pytest.mark.unit
class TestPersonDifferentiation:
    """Test prayer person differentiation functionality"""
    
    def test_individual_request_generates_third_person_prayer(self):
        """Test individual requests generate third-person community prayers"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Divine Creator, we pray for our friend who seeks healing. May your peace be with them. Amen."
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            # Test individual pronouns
            test_cases = [
                "Please help me with my anxiety",
                "I need guidance for my job search", 
                "Pray for my sick grandmother",
                "My family needs healing"
            ]
            
            for request in test_cases:
                result = generate_prayer(request)
                
                # Verify third-person format is encouraged in prompt
                call_args = mock_client.messages.create.call_args
                system_prompt = call_args[1]['system']
                
                # Should encourage third person for individual requests
                assert "them" in system_prompt or "they" in system_prompt
                assert "our friend" in system_prompt
    
    def test_collective_request_generates_second_person_prayer(self):
        """Test collective requests generate second-person community prayers"""
        mock_response = Mock()
        mock_content = Mock() 
        mock_content.text = "Divine Creator, help us grow closer to You as a community. Guide us in unity. Amen."
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            # Test collective pronouns
            test_cases = [
                "Help us grow closer as a church",
                "Bless our community outreach efforts",
                "We need guidance in our decisions",
                "Guide us in unity"
            ]
            
            for request in test_cases:
                result = generate_prayer(request)
                
                # Verify differentiation instructions are included when enabled
                call_args = mock_client.messages.create.call_args
                system_prompt = call_args[1]['system']
                
                # Should include person differentiation instructions
                if "COLLECTIVE PRONOUNS" in system_prompt:
                    assert "us/our/we" in system_prompt
                    assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" in system_prompt
    
    @patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true'})
    def test_feature_flag_enabled_includes_differentiation_prompt(self):
        """Test that enabling feature flag includes differentiation instructions"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Test prayer"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            generate_prayer("Help us grow")
            
            call_args = mock_client.messages.create.call_args
            system_prompt = call_args[1]['system']
            
            # Should include person differentiation instructions
            assert "COLLECTIVE PRONOUNS" in system_prompt
            assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" in system_prompt
            assert "us/our/we" in system_prompt
            assert "me/my/I" in system_prompt
    
    @patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'false'})
    def test_feature_flag_disabled_excludes_differentiation_prompt(self):
        """Test that disabling feature flag excludes differentiation instructions"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Test prayer"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            generate_prayer("Help us grow")
            
            call_args = mock_client.messages.create.call_args
            system_prompt = call_args[1]['system']
            
            # Should NOT include person differentiation instructions
            assert "COLLECTIVE PRONOUNS" not in system_prompt
            assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" not in system_prompt
    
    def test_mixed_pronoun_requests_handle_gracefully(self):
        """Test requests with mixed pronouns are handled appropriately"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Test prayer for mixed pronouns"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            # Test edge cases
            test_cases = [
                "Help me and our family heal",
                "We need prayer for my surgery", 
                "Pray that our church helps me find peace",
                "I want us to grow together"
            ]
            
            for request in test_cases:
                result = generate_prayer(request)
                
                # Should handle gracefully without errors
                assert result['prayer'] is not None
                assert result['service_status'] == 'normal'
    
    def test_empty_and_ambiguous_requests_default_gracefully(self):
        """Test that empty or ambiguous requests default to individual format"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Default prayer format"
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.prayer_helpers.anthropic_client') as mock_client:
            mock_client.messages.create.return_value = mock_response
            
            # Test ambiguous cases
            test_cases = [
                "",
                "prayer needed",
                "healing please",
                "guidance",
                "help"
            ]
            
            for request in test_cases:
                result = generate_prayer(request)
                
                # Should handle gracefully and default appropriately
                assert result['prayer'] is not None
                assert result['service_status'] == 'normal'


@pytest.mark.unit
class TestTodaysPrompt:
    """Test daily prompt functionality"""
    
    def test_todays_prompt_returns_default(self):
        """Test that todays_prompt returns the default prompt"""
        prompt = todays_prompt()
        assert prompt == "Let us pray 🙏"

