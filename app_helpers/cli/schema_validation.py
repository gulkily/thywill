#!/usr/bin/env python3
"""
Schema Validation CLI Module

Provides CLI interface for validating database schema compatibility
and identifying missing columns or tables.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import engine
from app import column_exists, validate_schema_compatibility


def validate_schema():
    """Run comprehensive schema validation"""
    print("🔍 ThyWill Database Schema Validation")
    print("=" * 50)
    
    try:
        # Check if database exists
        db_path = os.environ.get('DATABASE_PATH', 'thywill.db')
        if db_path != ':memory:' and not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False
        
        # Run schema validation
        print("📋 Checking required columns...")
        is_valid, missing_columns = validate_schema_compatibility()
        
        if is_valid:
            print("✅ Schema validation PASSED")
            print("   All required columns are present")
            return True
        else:
            print(f"❌ Schema validation FAILED")
            print(f"   Found {len(missing_columns)} missing columns:")
            
            # Group by table for better readability
            tables = {}
            for col in missing_columns:
                table, column = col.split('.', 1)
                if table not in tables:
                    tables[table] = []
                tables[table].append(column)
            
            for table, columns in tables.items():
                print(f"   📑 Table '{table}':")
                for column in columns:
                    print(f"      - {column}")
            
            print("\n💡 Recommendations:")
            print("   • Run schema repairs: ./thywill start (will auto-repair)")
            print("   • Or manually fix with: ALTER TABLE statements")
            print("   • Check migration status: ./thywill status")
            
            return False
            
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=?"), (table_name,))
            return result.fetchone() is not None
    except Exception:
        return False


def show_table_info(table_name: str):
    """Show detailed information about a table"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = result.fetchall()
            
            if not columns:
                print(f"❌ Table '{table_name}' not found")
                return
            
            print(f"📑 Table '{table_name}' structure:")
            print("   Col | Name                 | Type      | NotNull | Default")
            print("   ----|----------------------|-----------|---------|--------")
            for col in columns:
                cid, name, col_type, not_null, default_val, pk = col
                not_null_str = "YES" if not_null else "NO"
                default_str = str(default_val) if default_val is not None else "NULL"
                print(f"   {cid:3} | {name:20} | {col_type:9} | {not_null_str:7} | {default_str}")
    except Exception as e:
        print(f"❌ Error reading table info: {e}")


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m app_helpers.cli.schema_validation <command>")
        print("Commands:")
        print("  validate     - Run schema validation")
        print("  table <name> - Show table structure")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        success = validate_schema()
        sys.exit(0 if success else 1)
    elif command == "table":
        if len(sys.argv) < 3:
            print("Usage: python -m app_helpers.cli.schema_validation table <table_name>")
            sys.exit(1)
        table_name = sys.argv[2]
        show_table_info(table_name)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()