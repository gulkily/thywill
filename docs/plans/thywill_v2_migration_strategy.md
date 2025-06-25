# ThyWill v2: Migration Strategy

## Migration Overview

This document outlines the strategy for migrating from the current ThyWill implementation (v1) to the new architecture (v2) while preserving community data and minimizing disruption.

## Migration Goals

### Primary Objectives
1. **Preserve Community Data**: All legitimate users, prayers, and prayer marks
2. **Zero Data Loss**: Complete migration of valid, non-corrupted data
3. **Minimal Downtime**: Keep service disruption under 1 hour
4. **Data Integrity**: Clean up corruption during migration
5. **Rollback Capability**: Ability to revert if issues arise

### Success Criteria
- All legitimate users can log in to v2
- All prayers and prayer marks preserved
- All admin functionality works
- Performance is equal or better than v1
- Zero corruption issues in v2

## Migration Phases

### Phase 1: Preparation (Week 1)

#### 1.1 Data Analysis
```bash
# Analyze current v1 database
./thywill-v1 analyze-data
```

**Tasks:**
- Catalog all tables and relationships
- Identify corrupted records
- Count legitimate vs corrupted data
- Document data quality issues
- Create corruption detection scripts

**Deliverables:**
- Data quality report
- Corruption identification scripts
- Migration feasibility assessment

#### 1.2 V2 Development Environment
```bash
# Set up v2 development
git clone thywill-v2
cd thywill-v2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

**Tasks:**
- Complete v2 core implementation
- Set up development database
- Create migration scripts
- Implement data validation tools

#### 1.3 Migration Scripts Development

```python
# scripts/migrate_data.py
from typing import Dict, List, Optional
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

class DataMigrator:
    def __init__(self, v1_db_path: str, v2_db_url: str):
        self.v1_engine = create_engine(f"sqlite:///{v1_db_path}")
        self.v2_engine = create_engine(v2_db_url)
        self.logger = logging.getLogger(__name__)
        
        # Migration statistics
        self.stats = {
            "users_migrated": 0,
            "users_skipped": 0,
            "prayers_migrated": 0,
            "prayers_skipped": 0,
            "marks_migrated": 0,
            "corrupted_records": []
        }
    
    def migrate_all(self):
        """Execute complete migration."""
        self.logger.info("Starting migration from v1 to v2")
        
        try:
            self.validate_v1_database()
            self.migrate_users()
            self.migrate_prayers()
            self.migrate_prayer_marks()
            self.migrate_admin_roles()
            self.migrate_text_archives()  # Essential: preserve text archives
            self.validate_migration()
            
            self.logger.info("Migration completed successfully")
            self.print_migration_report()
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise
    
    def migrate_users(self):
        """Migrate users with corruption detection."""
        self.logger.info("Migrating users...")
        
        with self.v1_engine.connect() as v1_conn, self.v2_engine.connect() as v2_conn:
            # Get all users from v1
            v1_users = v1_conn.execute(text("SELECT * FROM user")).fetchall()
            
            for user in v1_users:
                if self.is_user_corrupted(user, v1_conn):
                    self.logger.warning(f"Skipping corrupted user: {user.display_name}")
                    self.stats["users_skipped"] += 1
                    self.stats["corrupted_records"].append({
                        "type": "user",
                        "id": user.id,
                        "display_name": user.display_name,
                        "reason": "corruption_detected"
                    })
                    continue
                
                # Migrate user to v2
                try:
                    v2_conn.execute(text("""
                        INSERT INTO users (
                            id, display_name, email, religious_preference, 
                            prayer_style, created_at, updated_at, is_active
                        ) VALUES (
                            :id, :display_name, :email, :religious_preference,
                            :prayer_style, :created_at, :updated_at, :is_active
                        )
                    """), {
                        "id": user.id,
                        "display_name": user.display_name,
                        "email": getattr(user, 'email', None),
                        "religious_preference": user.religious_preference or "unspecified",
                        "prayer_style": getattr(user, 'prayer_style', None),
                        "created_at": user.created_at,
                        "updated_at": user.created_at,
                        "is_active": True
                    })
                    
                    self.stats["users_migrated"] += 1
                    self.logger.debug(f"Migrated user: {user.display_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate user {user.display_name}: {e}")
                    self.stats["users_skipped"] += 1
            
            v2_conn.commit()
    
    def is_user_corrupted(self, user, v1_conn) -> bool:
        """Detect corrupted user records based on v1 patterns."""
        try:
            # Test if user can be retrieved by ID (the corruption we encountered)
            lookup_test = v1_conn.execute(
                text("SELECT id FROM user WHERE id = :user_id"), 
                {"user_id": user.id}
            ).fetchone()
            
            if not lookup_test:
                return True  # Can't be retrieved by ID
            
            # Additional corruption checks
            if not user.display_name or len(user.display_name.strip()) == 0:
                return True  # Invalid display name
            
            if user.display_name in ["Test User", "Prayer Test User"] and user.id == "12232388dbed436bbcc061e60e47ed99":
                return True  # Known corrupted record
            
            return False
            
        except Exception:
            return True  # Any error means corruption
    
    def migrate_text_archives(self):
        """Migrate and create text archives for all data."""
        self.logger.info("Migrating text archives...")
        
        from app.services.archives import TextArchiveService
        archive_service = TextArchiveService(Path("./text_archives_v2"))
        
        with self.v1_engine.connect() as v1_conn, self.v2_engine.connect() as v2_conn:
            # Migrate existing v1 text archives if they exist
            v1_archive_dir = Path("./text_archives")
            if v1_archive_dir.exists():
                self.logger.info("Copying existing v1 text archives...")
                import shutil
                shutil.copytree(v1_archive_dir, "./text_archives_v2", dirs_exist_ok=True)
            
            # Create archives for any data that doesn't have them
            self.create_missing_user_archives(v2_conn, archive_service)
            self.create_missing_prayer_archives(v2_conn, archive_service)
            self.rebuild_activity_logs(v2_conn, archive_service)
    
    def create_missing_user_archives(self, v2_conn, archive_service):
        """Create text archives for users that don't have them."""
        users = v2_conn.execute(text("SELECT * FROM users")).fetchall()
        
        for user in users:
            user_file = archive_service.users_dir / f"{user.id}.txt"
            
            if not user_file.exists():
                # Create archive for migrated user
                user_data = {
                    "id": user.id,
                    "display_name": user.display_name,
                    "religious_preference": user.religious_preference,
                    "created_at": user.created_at,
                    "invited_by_display_name": "migrated from v1"
                }
                
                archive_service.archive_user_registration(user_data)
                self.logger.debug(f"Created archive for user: {user.display_name}")
    
    def create_missing_prayer_archives(self, v2_conn, archive_service):
        """Create text archives for prayers that don't have them."""
        prayers_query = text("""
            SELECT p.*, u.display_name as author_name
            FROM prayers p
            JOIN users u ON p.author_id = u.id
        """)
        prayers = v2_conn.execute(prayers_query).fetchall()
        
        for prayer in prayers:
            prayer_file = archive_service.prayers_dir / f"{prayer.id}.txt"
            
            if not prayer_file.exists():
                # Create archive for migrated prayer
                prayer_data = {
                    "id": prayer.id,
                    "author_id": prayer.author_id,
                    "author_display_name": prayer.author_name,
                    "text": prayer.text,
                    "generated_prayer": prayer.generated_prayer,
                    "target_audience": prayer.target_audience,
                    "created_at": prayer.created_at
                }
                
                archive_service.archive_prayer_request(prayer_data)
                self.logger.debug(f"Created archive for prayer: {prayer.id}")
    
    def rebuild_activity_logs(self, v2_conn, archive_service):
        """Rebuild activity logs from prayer marks."""
        marks_query = text("""
            SELECT pm.*, u.display_name as user_name
            FROM prayer_marks pm
            JOIN users u ON pm.user_id = u.id
            ORDER BY pm.marked_at
        """)
        marks = v2_conn.execute(marks_query).fetchall()
        
        for mark in marks:
            mark_data = {
                "prayer_id": mark.prayer_id,
                "user_id": mark.user_id,
                "user_display_name": mark.user_name,
                "marked_at": mark.marked_at
            }
            
            archive_service.archive_prayer_mark(mark_data)
```

### Phase 2: Testing Migration (Week 2)

#### 2.1 Development Migration Testing
```bash
# Test migration with development data
python scripts/migrate_data.py \
    --v1-db ./thywill_v1_dev.db \
    --v2-db postgresql://localhost/thywill_v2_dev \
    --dry-run
```

#### 2.2 Production Data Copy Testing
```bash
# Copy production database for testing
cp /prod/thywill.db /staging/thywill_v1_test.db

# Test migration with production data copy
python scripts/migrate_data.py \
    --v1-db /staging/thywill_v1_test.db \
    --v2-db postgresql://localhost/thywill_v2_staging \
    --verbose
```

#### 2.3 Validation Scripts

```python
# scripts/validate_migration.py
class MigrationValidator:
    def validate_user_migration(self):
        """Validate user migration completeness."""
        with self.v1_engine.connect() as v1_conn, self.v2_engine.connect() as v2_conn:
            # Count legitimate users in v1
            v1_count = v1_conn.execute(text("""
                SELECT COUNT(*) FROM user 
                WHERE display_name NOT LIKE '%Test%' 
                AND id != '12232388dbed436bbcc061e60e47ed99'
            """)).scalar()
            
            # Count users in v2
            v2_count = v2_conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            
            self.logger.info(f"V1 legitimate users: {v1_count}, V2 users: {v2_count}")
            
            if v1_count != v2_count:
                raise ValidationError(f"User count mismatch: v1={v1_count}, v2={v2_count}")
    
    def validate_prayer_migration(self):
        """Validate prayer migration completeness."""
        # Similar validation for prayers
        pass
    
    def validate_functionality(self):
        """Test key functionality in v2."""
        # Test user login
        # Test prayer creation
        # Test prayer marking
        # Test admin functions
        pass
```

### Phase 3: Staging Deployment (Week 3)

#### 3.1 Staging Environment Setup
```bash
# Deploy v2 to staging
docker-compose -f docker-compose.staging.yml up -d

# Run migration on staging
python scripts/migrate_data.py \
    --v1-db /prod/thywill_backup.db \
    --v2-db $STAGING_DB_URL
```

#### 3.2 User Acceptance Testing
- Invite key community members to test staging
- Verify all critical functionality
- Collect feedback and fix issues
- Performance testing with real data volumes

#### 3.3 Final Migration Script Refinement

```python
# scripts/production_migration.py
class ProductionMigrator(DataMigrator):
    def __init__(self):
        super().__init__(
            v1_db_path=os.environ["V1_DB_PATH"],
            v2_db_url=os.environ["V2_DB_URL"]
        )
        self.backup_dir = os.environ["BACKUP_DIR"]
    
    def execute_production_migration(self):
        """Execute production migration with all safety measures."""
        
        # Step 1: Create comprehensive backups
        self.create_production_backups()
        
        # Step 2: Put v1 in maintenance mode
        self.enable_maintenance_mode()
        
        try:
            # Step 3: Final data sync
            self.migrate_all()
            
            # Step 4: Validate migration
            self.validate_migration()
            
            # Step 5: Switch DNS to v2
            self.switch_to_v2()
            
            # Step 6: Verify v2 is working
            self.verify_v2_functionality()
            
        except Exception as e:
            # Rollback procedures
            self.rollback_to_v1()
            raise
        
        finally:
            self.disable_maintenance_mode()
    
    def create_production_backups(self):
        """Create multiple backup copies."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Database backup
        shutil.copy2(
            os.environ["V1_DB_PATH"],
            f"{self.backup_dir}/thywill_v1_backup_{timestamp}.db"
        )
        
        # File system backup
        shutil.copytree(
            "/prod/thywill_v1",
            f"{self.backup_dir}/thywill_v1_files_{timestamp}",
            ignore=shutil.ignore_patterns("*.pyc", "venv", "__pycache__")
        )
```

### Phase 4: Production Migration (Week 4)

#### 4.1 Pre-Migration Checklist
- [ ] V2 tested and validated on staging
- [ ] Migration scripts tested with production data copy
- [ ] Backup procedures verified
- [ ] Rollback procedures tested
- [ ] Team coordination and communication plan
- [ ] Monitoring and alerting configured

#### 4.2 Migration Day Procedures

**Timeline: Saturday 2:00 AM - 3:00 AM (Low Traffic)**

```bash
# T-0:60 - Start preparation
echo "Starting migration preparation..."

# T-0:30 - Enable maintenance mode
python scripts/maintenance_mode.py --enable

# T-0:15 - Final backup
python scripts/backup.py --full

# T-0:05 - Last validation
python scripts/validate_v1.py

# T-0:00 - Execute migration
python scripts/production_migration.py

# T+0:30 - Validation and testing
python scripts/validate_v2.py

# T+0:45 - Switch traffic to v2
python scripts/switch_dns.py --to-v2

# T+0:60 - Disable maintenance mode
python scripts/maintenance_mode.py --disable
```

#### 4.3 Post-Migration Validation

```python
# scripts/post_migration_validation.py
def validate_production_migration():
    """Comprehensive post-migration validation."""
    
    checks = [
        check_user_login,
        check_prayer_creation,
        check_prayer_marking,
        check_admin_functions,
        check_performance_metrics,
        check_error_rates,
        check_database_integrity
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append({"check": check.__name__, "status": "PASS", "result": result})
        except Exception as e:
            results.append({"check": check.__name__, "status": "FAIL", "error": str(e)})
    
    # Report results
    passed = len([r for r in results if r["status"] == "PASS"])
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} validation checks passed")
        return True
    else:
        print(f"❌ {total - passed} validation checks failed")
        for result in results:
            if result["status"] == "FAIL":
                print(f"   FAIL: {result['check']} - {result['error']}")
        return False
```

## Rollback Strategy

### Automatic Rollback Triggers
- Migration validation failures
- Critical errors during migration
- V2 functionality failures post-migration

### Rollback Procedures

```python
# scripts/rollback.py
class RollbackManager:
    def execute_rollback(self):
        """Rollback to v1 if v2 migration fails."""
        
        self.logger.info("Executing rollback to v1...")
        
        # Step 1: Switch DNS back to v1
        self.switch_dns_to_v1()
        
        # Step 2: Restore v1 database if needed
        self.restore_v1_database()
        
        # Step 3: Restart v1 services
        self.restart_v1_services()
        
        # Step 4: Validate v1 is working
        self.validate_v1_functionality()
        
        # Step 5: Disable maintenance mode
        self.disable_maintenance_mode()
        
        self.logger.info("Rollback completed successfully")
```

## Communication Plan

### Pre-Migration Communication
**1 Week Before:**
- Email to all users about upcoming maintenance
- Blog post explaining improvements
- Social media announcements

**1 Day Before:**
- Reminder email with exact timing
- In-app notification about maintenance window

### During Migration
- Status page updates every 15 minutes
- Social media updates on progress

### Post-Migration
- Success announcement
- New feature highlights
- Thank you to community for patience

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| Data corruption during migration | Low | High | Multiple backups, validation scripts |
| V2 performance issues | Medium | Medium | Load testing, performance monitoring |
| Authentication failures | Low | High | Extensive auth testing, fallback procedures |
| Database connection issues | Medium | Medium | Connection pooling, retry logic |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| User dissatisfaction | Low | Medium | Clear communication, quick issue resolution |
| Extended downtime | Low | High | Thorough testing, rollback procedures |
| Feature regression | Medium | Medium | Comprehensive testing, user feedback |

## Success Metrics

### Technical Metrics
- Migration completion time: < 1 hour
- Data integrity: 100% of legitimate data migrated
- System availability: > 99.9% post-migration
- Performance: Response times ≤ v1 performance

### User Experience Metrics
- User login success rate: > 99%
- Prayer submission success rate: > 99%
- User-reported issues: < 5 in first week
- User satisfaction: Positive feedback from 90%+ of users

## Post-Migration Cleanup

### Week 1-2 After Migration
- Monitor system performance and error rates
- Address any user-reported issues
- Fine-tune performance optimizations
- Complete documentation updates

### Month 1 After Migration
- Decommission v1 infrastructure
- Archive v1 backups according to retention policy
- Conduct migration retrospective
- Plan v2.1 feature development

This migration strategy prioritizes data safety and minimal user disruption while addressing the corruption and complexity issues that plagued v1.