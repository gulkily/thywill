#!/usr/bin/env python3
"""
Comprehensive test suite for the Enhanced Migration System
Tests all key functionality including dependency resolution, rollbacks, and safety mechanisms
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import json
from pathlib import Path

# Add project root to path
sys.path.append('.')

from app_helpers.utils.enhanced_migration import MigrationManager, MigrationError


class MigrationSystemTester:
    """Test suite for the enhanced migration system"""
    
    def __init__(self):
        self.test_dir = None
        self.test_db_path = None
        self.manager = None
        self.tests_passed = 0
        self.tests_failed = 0
        
    def setup_test_environment(self):
        """Create a temporary test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="migration_test_"))
        self.test_db_path = self.test_dir / "test.db"
        migrations_dir = self.test_dir / "migrations"
        migrations_dir.mkdir()
        
        # Initialize migration manager with test environment
        self.manager = MigrationManager(
            db_path=str(self.test_db_path),
            migrations_dir=str(migrations_dir)
        )
        
        print(f"✅ Test environment created at: {self.test_dir}")
        
    def cleanup_test_environment(self):
        """Clean up the test environment"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print("✅ Test environment cleaned up")
    
    def create_test_migration(self, migration_id, depends_on=None, requires_maintenance=False):
        """Create a test migration"""
        migration_dir = self.test_dir / "migrations" / migration_id
        migration_dir.mkdir()
        
        # Create metadata
        metadata = {
            "migration_id": migration_id,
            "description": f"Test migration {migration_id}",
            "depends_on": depends_on or [],
            "estimated_duration_seconds": 1,
            "requires_maintenance_mode": requires_maintenance,
            "data_size_threshold_mb": 10
        }
        
        with open(migration_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create simple SQL files
        table_name = f"test_{migration_id.replace('-', '_')}"
        up_sql = f"""-- Test migration {migration_id}

CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""
        
        down_sql = f"""
-- Rollback for {migration_id}
DROP TABLE IF EXISTS test_{migration_id.replace('-', '_')};
"""
        
        with open(migration_dir / "up.sql", 'w') as f:
            f.write(up_sql)
        
        with open(migration_dir / "down.sql", 'w') as f:
            f.write(down_sql)
    
    def assert_test(self, condition, test_name):
        """Assert a test condition"""
        if condition:
            print(f"✅ {test_name}")
            self.tests_passed += 1
        else:
            print(f"❌ {test_name}")
            self.tests_failed += 1
            
    def test_basic_functionality(self):
        """Test basic migration functionality"""
        print("\n🔄 Testing basic functionality...")
        
        # Test 1: Migration manager initialization
        self.assert_test(
            self.manager is not None,
            "Migration manager initialization"
        )
        
        # Test 2: Schema migration table creation
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_migrations'
            """)
            table_exists = cursor.fetchone() is not None
        
        self.assert_test(table_exists, "Schema migrations table creation")
        
        # Test 3: No pending migrations initially
        pending = self.manager.get_pending_migrations()
        self.assert_test(len(pending) == 0, "No pending migrations initially")
        
    def test_migration_creation_and_detection(self):
        """Test migration creation and detection"""
        print("\n🔄 Testing migration creation and detection...")
        
        # Create test migrations
        self.create_test_migration("001-create-users")
        self.create_test_migration("002-create-posts", depends_on=["001-create-users"])
        
        # Test 1: Available migrations detection
        available = self.manager.get_available_migrations()
        self.assert_test(
            len(available) == 2,
            f"Available migrations detection (found {len(available)})"
        )
        
        # Test 2: Pending migrations detection
        pending = self.manager.get_pending_migrations()
        self.assert_test(
            len(pending) == 2,
            f"Pending migrations detection (found {len(pending)})"
        )
        
        # Test 3: Dependency resolution
        migration_ids = [m['id'] for m in pending]
        self.assert_test(
            migration_ids[0] == "001-create-users" and migration_ids[1] == "002-create-posts",
            f"Dependency resolution order (got: {migration_ids})"
        )
    
    def test_migration_application(self):
        """Test migration application"""
        print("\n🔄 Testing migration application...")
        
        # Test 1: Apply migrations
        applied = self.manager.auto_migrate_on_startup()
        self.assert_test(
            len(applied) == 2,
            f"Migration application (applied {len(applied)} migrations)"
        )
        
        # Test 2: Check tables were created
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'test_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['test_001_create_users', 'test_002_create_posts']
        self.assert_test(
            all(table in tables for table in expected_tables),
            f"Tables created correctly (found: {tables})"
        )
        
        # Test 3: Applied migrations tracking
        applied_migrations = self.manager.get_applied_migrations()
        self.assert_test(
            len(applied_migrations) == 2,
            f"Applied migrations tracking (tracked {len(applied_migrations)})"
        )
        
        # Test 4: No more pending migrations
        pending = self.manager.get_pending_migrations()
        self.assert_test(
            len(pending) == 0,
            "No pending migrations after application"
        )
    
    def test_rollback_functionality(self):
        """Test migration rollback functionality"""
        print("\n🔄 Testing rollback functionality...")
        
        # Test 1: Rollback last migration
        success = self.manager.rollback_migration("002-create-posts")
        self.assert_test(success, "Migration rollback execution")
        
        # Test 2: Check table was removed
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='test_002_create_posts'
            """)
            table_exists = cursor.fetchone() is not None
        
        self.assert_test(not table_exists, "Table removed after rollback")
        
        # Test 3: Applied migrations updated
        applied_migrations = self.manager.get_applied_migrations()
        self.assert_test(
            len(applied_migrations) == 1 and applied_migrations[0] == "001-create-users",
            f"Applied migrations updated after rollback (have: {applied_migrations})"
        )
    
    def test_error_handling(self):
        """Test error handling and safety mechanisms"""
        print("\n🔄 Testing error handling and safety mechanisms...")
        
        # Test 1: Invalid migration detection
        invalid_migration_dir = self.test_dir / "migrations" / "003-invalid"
        invalid_migration_dir.mkdir()
        
        # Create invalid migration (missing files)
        with open(invalid_migration_dir / "metadata.json", 'w') as f:
            json.dump({
                "migration_id": "003-invalid",
                "description": "Invalid migration",
                "depends_on": [],
                "estimated_duration_seconds": 1,
                "requires_maintenance_mode": False
            }, f)
        
        # Missing up.sql and down.sql files should cause validation to fail
        try:
            available = self.manager.get_available_migrations()
            # The invalid migration should be detected but validation should fail
            invalid_migration = next((m for m in available if m['id'] == '003-invalid'), None)
            if invalid_migration:
                self.manager.validate_migration(invalid_migration)
                self.assert_test(False, "Invalid migration validation (should have failed)")
            else:
                self.assert_test(True, "Invalid migration not detected (acceptable)")
        except MigrationError:
            self.assert_test(True, "Invalid migration validation error handling")
        except Exception as e:
            print(f"   Unexpected error: {e}")
            self.assert_test(False, f"Unexpected error in validation: {e}")
        
        # Clean up invalid migration
        shutil.rmtree(invalid_migration_dir)
    
    def test_schema_integrity(self):
        """Test schema integrity validation"""
        print("\n🔄 Testing schema integrity validation...")
        
        # Test 1: Schema integrity check
        integrity_check = self.manager.validate_schema_integrity()
        self.assert_test(integrity_check, "Schema integrity validation")
        
        # Test 2: Current version detection
        current_version = self.manager.get_current_version()
        self.assert_test(
            current_version == "001-create-users",
            f"Current version detection (got: {current_version})"
        )
    
    def test_dependency_error_handling(self):
        """Test dependency error handling"""
        print("\n🔄 Testing dependency error handling...")
        
        # Create migration with missing dependency
        self.create_test_migration("004-depends-on-missing", depends_on=["999-missing"])
        
        try:
            pending = self.manager.get_pending_migrations()
            self.assert_test(False, "Missing dependency detection (should have failed)")
        except MigrationError as e:
            self.assert_test(
                "missing migration" in str(e).lower(),
                "Missing dependency error handling"
            )
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Enhanced Migration System Tests")
        print("=" * 50)
        
        try:
            self.setup_test_environment()
            
            # Run all test suites
            self.test_basic_functionality()
            self.test_migration_creation_and_detection()
            self.test_migration_application()
            self.test_rollback_functionality()
            self.test_error_handling()
            self.test_schema_integrity()
            self.test_dependency_error_handling()
            
        finally:
            self.cleanup_test_environment()
        
        # Print test results
        print("\n" + "=" * 50)
        print("🧪 Test Results Summary")
        print(f"✅ Tests passed: {self.tests_passed}")
        print(f"❌ Tests failed: {self.tests_failed}")
        print(f"📊 Success rate: {(self.tests_passed / (self.tests_passed + self.tests_failed) * 100):.1f}%")
        
        if self.tests_failed == 0:
            print("🎉 All tests passed! Migration system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please review the output above.")
            return False


def main():
    """Main test runner"""
    tester = MigrationSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()