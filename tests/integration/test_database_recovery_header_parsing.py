"""
Integration tests for database recovery header parsing functionality.

Tests the enhanced header parsing logic that skips format lines and 
authentication request headers during archive import.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from sqlmodel import Session

from models import engine
from app_helpers.services.database_recovery import CompleteSystemRecovery


@pytest.mark.integration
class TestDatabaseRecoveryHeaderParsing:
    """Test archive header parsing during database recovery"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.archive_dir = Path(self.temp_dir)
        
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_skip_format_header_lines(self):
        """Test that format header lines are properly skipped during parsing"""
        # Create archive file with format headers
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("Format: Authentication Request Archive\n")
            f.write("Generated: 2025-06-25 19:16:45\n")
            f.write("Authentication Requests\n")
            f.write("=======================\n")
            f.write("\n")
            f.write("2025-06-25 10:30:00 | user123 | device_info | 192.168.1.1 | pending\n")
            f.write("2025-06-25 11:45:30 | user456 | mobile_app | 10.0.0.1 | approved\n")
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        # Should not raise timestamp parsing errors on header lines
        try:
            with Session(engine) as session:
                stats = recovery._recover_authentication_requests(session)
                
            # Should successfully parse the actual data lines
            assert stats['auth_requests_recovered'] == 2
            
        except ValueError as e:
            if "time data" in str(e):
                pytest.fail(f"Header parsing failed - timestamp error on header line: {e}")
            else:
                raise
    
    def test_skip_authentication_requests_header(self):
        """Test that 'Authentication Requests' header is skipped"""
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("Authentication Requests\n")
            f.write("2025-06-25 10:30:00 | user123 | device_info | 192.168.1.1 | pending\n")
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        with Session(engine) as session:
            stats = recovery._recover_authentication_requests(session)
            
        # Should parse the data line but skip the header
        assert stats['auth_requests_recovered'] == 1
    
    def test_skip_multiple_header_types(self):
        """Test skipping various header line formats"""
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("Format: Authentication Request Archive\n")
            f.write("Generated: 2025-06-25 19:16:45\n")
            f.write("Authentication Requests\n")
            f.write("=======================\n")
            f.write("Total Records: 3\n")
            f.write("\n")  # Empty line
            f.write("2025-06-25 10:30:00 | user123 | device_info | 192.168.1.1 | pending\n")
            f.write("2025-06-25 11:45:30 | user456 | mobile_app | 10.0.0.1 | approved\n")
            f.write("2025-06-25 12:15:00 | user789 | web_browser | 172.16.0.1 | rejected\n")
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        with Session(engine) as session:
            stats = recovery._recover_authentication_requests(session)
            
        # Should parse only the actual data lines
        assert stats['auth_requests_recovered'] == 3
    
    def test_lazy_loading_archive_service(self):
        """Test that archive service is not created until needed during validation"""
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        # Archive service should not be initialized yet
        assert recovery._archive_service is None
        assert recovery._text_importer is None
        
        # Accessing the archive service should initialize it lazily
        service = recovery.archive_service
        assert service is not None
        assert recovery._archive_service is not None
    
    def test_empty_file_handling(self):
        """Test handling of empty archive files"""
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("")  # Empty file
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        with Session(engine) as session:
            stats = recovery._recover_authentication_requests(session)
            
        # Should handle empty files gracefully
        assert stats['auth_requests_recovered'] == 0
    
    def test_header_only_file_handling(self):
        """Test handling of files with only headers and no data"""
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("Format: Authentication Request Archive\n")
            f.write("Generated: 2025-06-25 19:16:45\n")
            f.write("Authentication Requests\n")
            f.write("=======================\n")
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        with Session(engine) as session:
            stats = recovery._recover_authentication_requests(session)
            
        # Should handle header-only files gracefully
        assert stats['auth_requests_recovered'] == 0
    
    def test_malformed_data_line_handling(self):
        """Test handling of malformed data lines mixed with headers"""
        auth_requests_file = self.archive_dir / "authentication_requests.txt"
        with open(auth_requests_file, 'w') as f:
            f.write("Format: Authentication Request Archive\n")
            f.write("2025-06-25 10:30:00 | user123 | device_info | 192.168.1.1 | pending\n")
            f.write("malformed line without proper format\n")
            f.write("2025-06-25 11:45:30 | user456 | mobile_app | 10.0.0.1 | approved\n")
        
        recovery = CompleteSystemRecovery(archive_dir=str(self.archive_dir))
        
        with Session(engine) as session:
            # Should skip malformed lines and process valid ones
            stats = recovery._recover_authentication_requests(session)
            
        # Should successfully parse the valid data lines
        assert stats['auth_requests_recovered'] == 2