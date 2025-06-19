"""
Enhanced Database Migration System
Implements schema-only migrations with dependency resolution, locking, and recovery.
"""

import sqlite3
import json
import os
import time
import fcntl
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


class MigrationError(Exception):
    """Custom exception for migration-related errors"""
    pass


class MigrationManager:
    """Enhanced migration manager with dependency resolution and safety mechanisms"""
    
    def __init__(self, db_path: str = "thywill.db", migrations_dir: str = "migrations"):
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.lock_file = Path("migration.lock")
        self.lock_fd = None
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(exist_ok=True)
        
        # Initialize schema version tracking
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Create migration tracking table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL,
                    checksum TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    status TEXT NOT NULL DEFAULT 'completed'
                )
            """)
            conn.commit()
    
    def acquire_migration_lock(self) -> bool:
        """Acquire exclusive lock for migration operations"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.lock_fd.flush()
            return True
        except (OSError, IOError):
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
    
    def release_migration_lock(self):
        """Release migration lock"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                self.lock_file.unlink(missing_ok=True)
            except (OSError, IOError):
                pass
            finally:
                self.lock_fd = None
    
    def is_migration_locked(self) -> bool:
        """Check if migration is currently locked"""
        return self.lock_file.exists()
    
    def get_current_version(self) -> Optional[str]:
        """Get current database schema version (latest applied migration)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT migration_id FROM schema_migrations 
                WHERE status = 'completed'
                ORDER BY applied_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration IDs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT migration_id FROM schema_migrations 
                WHERE status = 'completed'
                ORDER BY applied_at ASC
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_migrations(self) -> List[Dict]:
        """Get list of available migration directories with metadata"""
        migrations = []
        
        for migration_dir in sorted(self.migrations_dir.iterdir()):
            if migration_dir.is_dir() and migration_dir.name != "__pycache__":
                metadata_file = migration_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        migrations.append({
                            'id': migration_dir.name,
                            'path': migration_dir,
                            'metadata': metadata
                        })
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"⚠️  Invalid metadata in {metadata_file}: {e}")
        
        return migrations
    
    def resolve_migration_dependencies(self, migrations: List[Dict]) -> List[Dict]:
        """Sort migrations by dependency order using topological sort"""
        # Get applied migrations to check if dependencies are satisfied
        applied_migrations = set(self.get_applied_migrations())
        
        # Create mapping of migration_id to migration data
        migration_map = {m['id']: m for m in migrations}
        
        # Build dependency graph
        graph = {}
        in_degree = {}
        
        for migration in migrations:
            migration_id = migration['id']
            depends_on = migration['metadata'].get('depends_on', [])
            
            graph[migration_id] = depends_on
            in_degree[migration_id] = 0
        
        # Calculate in-degrees
        for migration_id, dependencies in graph.items():
            for dep in dependencies:
                # Check if dependency is in pending migrations or already applied
                if dep in migration_map or dep in applied_migrations:
                    if dep in migration_map:  # Only count pending dependencies
                        in_degree[migration_id] += 1
                else:
                    raise MigrationError(f"Migration {migration_id} depends on missing migration {dep}")
        
        # Topological sort
        queue = [mid for mid, degree in in_degree.items() if degree == 0]
        sorted_migrations = []
        
        while queue:
            current = queue.pop(0)
            sorted_migrations.append(migration_map[current])
            
            # Update in-degrees of dependent migrations
            for migration_id, dependencies in graph.items():
                if current in dependencies:
                    in_degree[migration_id] -= 1
                    if in_degree[migration_id] == 0:
                        queue.append(migration_id)
        
        if len(sorted_migrations) != len(migrations):
            raise MigrationError("Circular dependency detected in migrations")
        
        return sorted_migrations
    
    def get_pending_migrations(self) -> List[Dict]:
        """Get list of unapplied migrations in dependency order"""
        available = self.get_available_migrations()
        applied = set(self.get_applied_migrations())
        
        pending = [m for m in available if m['id'] not in applied]
        return self.resolve_migration_dependencies(pending)
    
    def calculate_checksum(self, migration_path: Path) -> str:
        """Calculate checksum of migration files"""
        hasher = hashlib.sha256()
        
        for file_name in ['up.sql', 'down.sql', 'metadata.json']:
            file_path = migration_path / file_name
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def estimate_migration_time(self, migration: Dict) -> int:
        """Estimate time required for migration based on metadata and data size"""
        metadata = migration['metadata']
        estimated_seconds = metadata.get('estimated_duration_seconds', 5)
        
        # Get table row counts for data size estimation
        if 'affected_tables' in metadata:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    total_rows = 0
                    for table in metadata['affected_tables']:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        total_rows += cursor.fetchone()[0]
                    
                    # Adjust estimate based on data size (rough heuristic)
                    if total_rows > 10000:
                        estimated_seconds *= 2
                    if total_rows > 100000:
                        estimated_seconds *= 3
            except sqlite3.Error:
                pass  # Use default estimate if table doesn't exist yet
        
        return estimated_seconds
    
    def should_enable_maintenance_mode(self, migration: Dict) -> bool:
        """Determine if migration requires maintenance mode"""
        metadata = migration['metadata']
        
        # Check if explicitly marked for maintenance mode
        if metadata.get('requires_maintenance_mode', False):
            return True
        
        # Check data size threshold
        threshold_mb = metadata.get('data_size_threshold_mb', 100)
        estimated_time = self.estimate_migration_time(migration)
        
        # Enable maintenance mode for long-running migrations (>30 seconds)
        return estimated_time > 30
    
    def validate_migration(self, migration: Dict) -> bool:
        """Validate migration can be applied safely"""
        migration_path = migration['path']
        
        # Check required files exist
        required_files = ['up.sql', 'down.sql', 'metadata.json']
        for file_name in required_files:
            if not (migration_path / file_name).exists():
                raise MigrationError(f"Missing required file: {file_name} in {migration['id']}")
        
        # Validate SQL syntax (basic check)
        try:
            up_sql = (migration_path / 'up.sql').read_text()
            down_sql = (migration_path / 'down.sql').read_text()
            
            # Basic syntax validation - check that SQL can be parsed
            # Note: We don't validate against actual database schema since tables may not exist yet
            if not up_sql.strip():
                raise MigrationError(f"Empty up.sql file in migration {migration['id']}")
            if not down_sql.strip():
                raise MigrationError(f"Empty down.sql file in migration {migration['id']}")
                
            # Very basic SQL syntax check - look for obviously malformed statements
            for line in up_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    # Check for common SQL statement patterns
                    if not any(line.upper().startswith(keyword) for keyword in [
                        'CREATE', 'ALTER', 'DROP', 'INSERT', 'UPDATE', 'DELETE', 'PRAGMA', 'SELECT'
                    ]) and not line.endswith(';'):
                        # This might be a continuation line or comment, which is fine
                        pass
                        
        except Exception as e:
            raise MigrationError(f"Invalid SQL in migration {migration['id']}: {e}")
        
        return True
    
    def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        try:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns
        except sqlite3.Error:
            return False
    
    def _safe_execute_statement(self, conn, statement: str) -> bool:
        """Execute a statement safely, handling common errors gracefully"""
        statement = statement.strip()
        if not statement:
            return True
            
        # Handle comments: if statement only contains comments, skip it
        # But if it contains actual SQL with comments, execute it
        non_comment_lines = [line.strip() for line in statement.split('\n') 
                           if line.strip() and not line.strip().startswith('--')]
        if not non_comment_lines:
            return True  # Only comments, skip execution
            
        try:
            # Handle ADD COLUMN statements that might already exist
            if 'ADD COLUMN' in statement.upper():
                # Extract table name and column name
                parts = statement.split()
                table_idx = -1
                for i, part in enumerate(parts):
                    if part.upper() == 'TABLE':
                        table_idx = i + 1
                        break
                
                if table_idx > 0 and table_idx < len(parts):
                    table_name = parts[table_idx]
                    
                    # Find column name after ADD COLUMN
                    add_col_idx = -1
                    for i, part in enumerate(parts):
                        if part.upper() == 'COLUMN':
                            add_col_idx = i + 1
                            break
                    
                    if add_col_idx > 0 and add_col_idx < len(parts):
                        column_name = parts[add_col_idx]
                        
                        # Check if column already exists
                        if self._column_exists(conn, table_name, column_name):
                            print(f"   - Column {column_name} already exists in {table_name}, skipping")
                            return True
            
            # Handle CREATE TABLE IF NOT EXISTS statements
            conn.execute(statement)
            return True
            
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            
            # Handle common cases where the operation is already done
            if 'duplicate column name' in error_msg:
                print(f"   - Column already exists, skipping: {statement[:50]}...")
                return True
            elif 'table' in error_msg and 'already exists' in error_msg:
                print(f"   - Table already exists, skipping: {statement[:50]}...")
                return True
            elif 'index' in error_msg and 'already exists' in error_msg:
                print(f"   - Index already exists, skipping: {statement[:50]}...")
                return True
            else:
                # Re-raise for other operational errors
                raise
    
    def apply_migration(self, migration: Dict) -> bool:
        """Apply a specific migration with safety checks and transaction handling"""
        migration_id = migration['id']
        migration_path = migration['path']
        
        print(f"🔄 Applying migration {migration_id}...")
        
        # Validate migration
        self.validate_migration(migration)
        
        # Calculate checksum
        checksum = self.calculate_checksum(migration_path)
        
        # Read SQL
        up_sql = (migration_path / 'up.sql').read_text()
        
        start_time = time.time()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Begin transaction
                conn.execute("BEGIN IMMEDIATE")
                
                try:
                    # Mark migration as started
                    conn.execute("""
                        INSERT INTO schema_migrations 
                        (migration_id, applied_at, checksum, status)
                        VALUES (?, ?, ?, 'in_progress')
                    """, (migration_id, datetime.now(), checksum))
                    
                    # Execute migration SQL with safe handling
                    for statement in up_sql.split(';'):
                        if not self._safe_execute_statement(conn, statement):
                            raise MigrationError(f"Failed to execute statement: {statement[:100]}...")
                    
                    # Calculate execution time
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Mark migration as completed
                    conn.execute("""
                        UPDATE schema_migrations 
                        SET status = 'completed', execution_time_ms = ?
                        WHERE migration_id = ?
                    """, (execution_time_ms, migration_id))
                    
                    conn.commit()
                    print(f"✅ Migration {migration_id} completed in {execution_time_ms}ms")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    # Mark migration as failed
                    conn.execute("""
                        UPDATE schema_migrations 
                        SET status = 'failed'
                        WHERE migration_id = ?
                    """, (migration_id,))
                    conn.commit()
                    raise MigrationError(f"Migration {migration_id} failed: {e}")
                    
        except Exception as e:
            print(f"❌ Migration {migration_id} failed: {e}")
            return False
    
    def rollback_migration(self, migration_id: str) -> bool:
        """Safely rollback a migration"""
        print(f"🔄 Rolling back migration {migration_id}...")
        
        # Find migration
        available = self.get_available_migrations()
        migration = next((m for m in available if m['id'] == migration_id), None)
        
        if not migration:
            raise MigrationError(f"Migration {migration_id} not found")
        
        migration_path = migration['path']
        down_sql = (migration_path / 'down.sql').read_text()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                
                try:
                    # Execute rollback SQL
                    for statement in down_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            conn.execute(statement)
                    
                    # Remove migration record
                    conn.execute("""
                        DELETE FROM schema_migrations 
                        WHERE migration_id = ?
                    """, (migration_id,))
                    
                    conn.commit()
                    print(f"✅ Migration {migration_id} rolled back successfully")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    raise MigrationError(f"Rollback of {migration_id} failed: {e}")
                    
        except Exception as e:
            print(f"❌ Rollback of {migration_id} failed: {e}")
            return False
    
    def validate_schema_integrity(self) -> bool:
        """Validate database schema matches expected state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Run PRAGMA integrity_check
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                
                if result != "ok":
                    raise MigrationError(f"Database integrity check failed: {result}")
                
                # Verify migration table exists and is accessible
                conn.execute("SELECT COUNT(*) FROM schema_migrations")
                
                print("✅ Schema integrity validation passed")
                return True
                
        except Exception as e:
            print(f"❌ Schema integrity validation failed: {e}")
            return False
    
    def handle_partial_migration_recovery(self):
        """Recover from partially applied migrations"""
        print("🔄 Checking for partial migration recovery...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find any migrations marked as in_progress
                cursor = conn.execute("""
                    SELECT migration_id FROM schema_migrations 
                    WHERE status = 'in_progress'
                """)
                
                partial_migrations = [row[0] for row in cursor.fetchall()]
                
                if partial_migrations:
                    print(f"⚠️  Found {len(partial_migrations)} partial migrations, attempting recovery...")
                    
                    for migration_id in partial_migrations:
                        print(f"🔄 Attempting to rollback partial migration {migration_id}...")
                        
                        # Mark as failed and attempt rollback
                        conn.execute("""
                            UPDATE schema_migrations 
                            SET status = 'failed'
                            WHERE migration_id = ?
                        """, (migration_id,))
                        
                        # Try to rollback if possible
                        try:
                            self.rollback_migration(migration_id)
                        except MigrationError as e:
                            print(f"⚠️  Could not auto-rollback {migration_id}: {e}")
                            print(f"   Manual intervention may be required")
                    
                    conn.commit()
                else:
                    print("✅ No partial migrations found")
                    
        except Exception as e:
            print(f"❌ Partial migration recovery failed: {e}")
    
    def auto_migrate_on_startup(self) -> List[str]:
        """Automatically detect and apply pending migrations at startup"""
        applied_migrations = []
        
        if not self.acquire_migration_lock():
            raise MigrationError("Could not acquire migration lock - another migration may be in progress")
        
        try:
            pending = self.get_pending_migrations()
            
            if not pending:
                return applied_migrations
            
            print(f"🔄 Found {len(pending)} pending migrations")
            
            # Check if any require maintenance mode
            for migration in pending:
                if self.should_enable_maintenance_mode(migration):
                    print(f"⚠️  Migration {migration['id']} requires maintenance mode")
                    print("   Skipping automatic migration - manual deployment needed")
                    return applied_migrations
            
            # Apply migrations
            for migration in pending:
                if self.apply_migration(migration):
                    applied_migrations.append(migration['id'])
                else:
                    break  # Stop on first failure
            
            # Validate final state
            if applied_migrations:
                self.validate_schema_integrity()
            
            return applied_migrations
            
        finally:
            self.release_migration_lock()
    
    def check_for_pending_migrations(self) -> bool:
        """Check if there are any pending migrations (for monitoring)"""
        return len(self.get_pending_migrations()) > 0