"""Unit tests for changelog helper functions"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, mock_open
from sqlmodel import Session, select
import subprocess

from models import ChangelogEntry
from app_helpers.services.changelog_helpers import (
    get_git_head_commit,
    get_last_cached_commit,
    parse_git_commits,
    categorize_commit,
    generate_friendly_description,
    refresh_changelog_if_needed,
    get_changelog_entries,
    group_entries_by_date,
    get_change_type_icon
)
from tests.factories import ChangelogEntryFactory


@pytest.mark.unit
class TestGitOperations:
    """Test git-related helper functions"""
    
    def test_get_git_head_commit_success(self):
        """Test successful git head commit retrieval"""
        mock_result = Mock()
        mock_result.stdout = "abc123def456\n"
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            result = get_git_head_commit()
            
            assert result == "abc123def456"
            mock_run.assert_called_once()
    
    def test_get_git_head_commit_failure(self):
        """Test git head commit retrieval failure"""
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git')):
            result = get_git_head_commit()
            
            assert result == ""
    
    def test_get_last_cached_commit_exists(self, test_session, clean_db):
        """Test retrieving last cached commit when entries exist"""
        # Create test changelog entries
        entry1 = ChangelogEntryFactory.create(
            commit_id="old123",
            commit_date=datetime(2024, 1, 1)
        )
        entry2 = ChangelogEntryFactory.create(
            commit_id="new456", 
            commit_date=datetime(2024, 1, 2)
        )
        test_session.add_all([entry1, entry2])
        test_session.commit()
        
        with patch('app_helpers.services.changelog_helpers.Session', return_value=test_session):
            result = get_last_cached_commit()
            
            assert result == "new456"
    
    def test_get_last_cached_commit_empty(self, test_session, clean_db):
        """Test retrieving last cached commit when no entries exist"""
        with patch('app_helpers.services.changelog_helpers.Session', return_value=test_session):
            result = get_last_cached_commit()
            
            assert result == ""


@pytest.mark.unit 
class TestCommitParsing:
    """Test git commit parsing functionality"""
    
    def test_parse_git_commits_success(self):
        """Test successful git commit parsing"""
        mock_result = Mock()
        mock_result.stdout = "abc123|2024-01-15 12:00:00 -0500|Add new feature\ndef456|2024-01-14 10:30:00 -0500|Fix bug in login\n"
        
        with patch('subprocess.run', return_value=mock_result):
            commits = parse_git_commits()
            
            assert len(commits) == 2
            assert commits[0]['id'] == "abc123"
            assert commits[0]['message'] == "Add new feature"
            assert commits[1]['id'] == "def456"
            assert commits[1]['message'] == "Fix bug in login"
    
    def test_parse_git_commits_with_since(self):
        """Test parsing commits since specific commit"""
        mock_result = Mock()
        mock_result.stdout = "abc123|2024-01-15 12:00:00 -0500|Add new feature\n"
        
        with patch('subprocess.run', return_value=mock_result) as mock_run:
            commits = parse_git_commits(since_commit="old123")
            
            # Verify command includes since parameter
            call_args = mock_run.call_args[0][0]
            assert "old123..HEAD" in call_args
    
    def test_parse_git_commits_date_parsing_error(self):
        """Test handling of date parsing errors"""
        mock_result = Mock()
        mock_result.stdout = "abc123|invalid-date|Add new feature\n"
        
        with patch('subprocess.run', return_value=mock_result):
            commits = parse_git_commits()
            
            assert len(commits) == 1
            assert commits[0]['id'] == "abc123"
            # Should use current time as fallback
            assert isinstance(commits[0]['date'], datetime)
    
    def test_parse_git_commits_failure(self):
        """Test handling of git command failure"""
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git')):
            commits = parse_git_commits()
            
            assert commits == []


@pytest.mark.unit
class TestCommitCategorization:
    """Test commit categorization logic"""
    
    def test_categorize_new_features(self):
        """Test categorization of new feature commits"""
        assert categorize_commit("Add user registration feature") == "new"
        assert categorize_commit("Implement prayer sharing") == "new"
        assert categorize_commit("Create admin dashboard") == "new"
        assert categorize_commit("Introduce dark mode") == "new"
    
    def test_categorize_bug_fixes(self):
        """Test categorization of bug fix commits"""
        assert categorize_commit("Fix login authentication issue") == "fixed"
        assert categorize_commit("Bug fix for prayer submission") == "fixed"
        assert categorize_commit("Resolve database connection problem") == "fixed"
        assert categorize_commit("Patch security vulnerability") == "fixed"
    
    def test_categorize_enhancements(self):
        """Test categorization of enhancement commits"""
        assert categorize_commit("Improve user interface design") == "enhanced"
        assert categorize_commit("Update prayer filtering logic") == "enhanced"
        assert categorize_commit("Optimize database queries") == "enhanced"
        assert categorize_commit("Refactor authentication code") == "enhanced"
    
    def test_categorize_meta_changes(self):
        """Test categorization of meta/documentation commits"""
        assert categorize_commit("Add development plan documentation") == "meta"
        assert categorize_commit("Update README with setup guide") == "meta"
        assert categorize_commit("Create API specification") == "meta"
        assert categorize_commit("Write testing strategy guide") == "meta"
    
    def test_categorize_default_case(self):
        """Test default categorization for unclear commits"""
        assert categorize_commit("Random commit message") == "enhanced"
        assert categorize_commit("") == "enhanced"


@pytest.mark.unit
class TestFriendlyDescriptions:
    """Test AI-powered friendly description generation"""
    
    def test_generate_friendly_description_success(self):
        """Test successful AI description generation"""
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Added a new way for users to share their prayers with friends."
        mock_response.content = [mock_content]
        
        with patch('app_helpers.services.changelog_helpers.anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            result = generate_friendly_description("Implement prayer sharing feature")
            
            assert result == "Added a new way for users to share their prayers with friends."
            mock_client.messages.create.assert_called_once()
    
    def test_generate_friendly_description_failure(self):
        """Test fallback when AI generation fails"""
        with patch('app_helpers.services.changelog_helpers.anthropic.Anthropic', side_effect=Exception("API error")):
            result = generate_friendly_description("implement prayer sharing feature")
            
            # Should fallback to capitalized original message
            assert result == "Implement prayer sharing feature"


@pytest.mark.unit
class TestChangelogRefresh:
    """Test changelog refresh functionality"""
    
    def test_refresh_changelog_no_changes(self, test_session, clean_db):
        """Test refresh when no new commits exist"""
        # Mock git operations to return same commit
        with patch('app_helpers.services.changelog_helpers.get_git_head_commit', return_value="abc123"), \
             patch('app_helpers.services.changelog_helpers.get_last_cached_commit', return_value="abc123"), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('fcntl.flock'):
            
            result = refresh_changelog_if_needed()
            
            assert result is False
    
    def test_refresh_changelog_with_new_commits(self, test_session, clean_db):
        """Test refresh when new commits exist"""
        # Mock git operations
        mock_commits = [{
            'id': 'new123',
            'date': datetime(2024, 1, 15),
            'message': 'Add new feature'
        }]
        
        with patch('app_helpers.services.changelog_helpers.get_git_head_commit', return_value="new123"), \
             patch('app_helpers.services.changelog_helpers.get_last_cached_commit', return_value="old123"), \
             patch('app_helpers.services.changelog_helpers.parse_git_commits', return_value=mock_commits), \
             patch('app_helpers.services.changelog_helpers.generate_friendly_description', return_value="Added cool new feature"), \
             patch('app_helpers.services.changelog_helpers.Session', return_value=test_session), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('fcntl.flock'):
            
            result = refresh_changelog_if_needed()
            
            assert result is True
            
            # Verify entry was added to database
            entries = test_session.exec(select(ChangelogEntry)).all()
            assert len(entries) == 1
            assert entries[0].commit_id == "new123"
            assert entries[0].friendly_description == "Added cool new feature"
    
    def test_refresh_changelog_lock_conflict(self):
        """Test handling of file lock conflicts"""
        with patch('builtins.open', mock_open()), \
             patch('fcntl.flock', side_effect=BlockingIOError()):
            
            result = refresh_changelog_if_needed()
            
            assert result is False


@pytest.mark.unit
class TestChangelogRetrieval:
    """Test changelog data retrieval functions"""
    
    def test_get_changelog_entries(self, test_session, clean_db):
        """Test retrieving changelog entries from database"""
        # Create test entries
        entry1 = ChangelogEntryFactory.create(commit_date=datetime(2024, 1, 1))
        entry2 = ChangelogEntryFactory.create(commit_date=datetime(2024, 1, 2))
        test_session.add_all([entry1, entry2])
        test_session.commit()
        
        with patch('app_helpers.services.changelog_helpers.Session', return_value=test_session):
            entries = get_changelog_entries(limit=10)
            
            assert len(entries) == 2
            # Should be ordered by date descending
            assert entries[0].commit_date > entries[1].commit_date
    
    def test_group_entries_by_date(self):
        """Test grouping entries by relative date"""
        from datetime import date, timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=8)
        
        entries = [
            ChangelogEntryFactory.build(commit_date=datetime.combine(today, datetime.min.time())),
            ChangelogEntryFactory.build(commit_date=datetime.combine(yesterday, datetime.min.time())),
            ChangelogEntryFactory.build(commit_date=datetime.combine(last_week, datetime.min.time()))
        ]
        
        grouped = group_entries_by_date(entries)
        
        assert "Today" in grouped
        assert "Yesterday" in grouped
        assert len(grouped["Today"]) == 1
        assert len(grouped["Yesterday"]) == 1
        # Last week entry should be grouped by specific date
        assert any(key not in ["Today", "Yesterday", "This Week"] for key in grouped.keys())


@pytest.mark.unit
class TestChangeTypeIcons:
    """Test change type icon mapping"""
    
    def test_get_change_type_icons(self):
        """Test icon mapping for different change types"""
        assert get_change_type_icon("new") == "🚀"
        assert get_change_type_icon("enhanced") == "✨"
        assert get_change_type_icon("fixed") == "🐛"
        assert get_change_type_icon("meta") == "📋"
        assert get_change_type_icon("unknown") == "📝"  # Default