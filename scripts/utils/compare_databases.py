#!/usr/bin/env python3
"""
Database Comparison Script for ThyWill

Compares two SQLite database files and reports differences in:
- Table schemas
- Record counts
- Data content (with sampling for large tables)
- Index structures

Usage:
    python scripts/utils/compare_databases.py db1.db db2.db [--detailed] [--sample-size N]
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
import hashlib

class DatabaseComparator:
    def __init__(self, db1_path: str, db2_path: str, sample_size: int = 100):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.sample_size = sample_size
        self.differences = []
        
    def connect_databases(self):
        """Connect to both databases"""
        try:
            self.conn1 = sqlite3.connect(self.db1_path)
            self.conn1.row_factory = sqlite3.Row
            self.conn2 = sqlite3.connect(self.db2_path)
            self.conn2.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Error connecting to databases: {e}")
            sys.exit(1)
    
    def get_table_names(self, conn: sqlite3.Connection) -> List[str]:
        """Get all table names from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_schema(self, conn: sqlite3.Connection, table_name: str) -> str:
        """Get table schema SQL"""
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_table_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Get record count for table"""
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        return cursor.fetchone()[0]
    
    def get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> List[str]:
        """Get column names for table"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
        return [row[1] for row in cursor.fetchall()]
    
    def sample_table_data(self, conn: sqlite3.Connection, table_name: str, columns: List[str]) -> List[Tuple]:
        """Sample data from table for comparison"""
        cursor = conn.cursor()
        column_list = ', '.join(f'`{col}`' for col in columns)
        
        # Try to order by a common column for consistent sampling
        order_clause = ""
        if 'id' in columns:
            order_clause = " ORDER BY id"
        elif 'created_at' in columns:
            order_clause = " ORDER BY created_at"
        
        query = f"SELECT {column_list} FROM `{table_name}`{order_clause} LIMIT {self.sample_size}"
        cursor.execute(query)
        return cursor.fetchall()
    
    def hash_data_sample(self, data: List[Tuple]) -> str:
        """Create hash of data sample for comparison"""
        # Convert Row objects to tuples for sorting
        data_tuples = [tuple(row) for row in data]
        data_str = str(sorted(data_tuples))
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def compare_tables(self) -> Dict[str, Any]:
        """Compare tables between databases"""
        tables1 = set(self.get_table_names(self.conn1))
        tables2 = set(self.get_table_names(self.conn2))
        
        comparison = {
            'only_in_db1': tables1 - tables2,
            'only_in_db2': tables2 - tables1,
            'common_tables': tables1 & tables2,
            'schema_differences': {},
            'count_differences': {},
            'data_differences': {}
        }
        
        # Compare common tables
        for table in comparison['common_tables']:
            # Schema comparison
            schema1 = self.get_table_schema(self.conn1, table)
            schema2 = self.get_table_schema(self.conn2, table)
            if schema1 != schema2:
                comparison['schema_differences'][table] = {
                    'db1': schema1,
                    'db2': schema2
                }
            
            # Count comparison
            count1 = self.get_table_count(self.conn1, table)
            count2 = self.get_table_count(self.conn2, table)
            if count1 != count2:
                comparison['count_differences'][table] = {
                    'db1': count1,
                    'db2': count2,
                    'difference': count1 - count2
                }
            
            # Data comparison (if schemas match)
            if table not in comparison['schema_differences']:
                columns = self.get_table_columns(self.conn1, table)
                if columns:  # Only if table has columns
                    data1 = self.sample_table_data(self.conn1, table, columns)
                    data2 = self.sample_table_data(self.conn2, table, columns)
                    
                    hash1 = self.hash_data_sample(data1)
                    hash2 = self.hash_data_sample(data2)
                    
                    if hash1 != hash2:
                        comparison['data_differences'][table] = {
                            'sample_size': min(len(data1), len(data2)),
                            'hash1': hash1,
                            'hash2': hash2
                        }
        
        return comparison
    
    def get_index_info(self, conn: sqlite3.Connection) -> Dict[str, List[str]]:
        """Get index information for database"""
        cursor = conn.cursor()
        cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
        indexes = {}
        for row in cursor.fetchall():
            table = row[1]
            if table not in indexes:
                indexes[table] = []
            indexes[table].append(row[2])  # SQL for index
        return indexes
    
    def compare_indexes(self) -> Dict[str, Any]:
        """Compare indexes between databases"""
        indexes1 = self.get_index_info(self.conn1)
        indexes2 = self.get_index_info(self.conn2)
        
        all_tables = set(indexes1.keys()) | set(indexes2.keys())
        differences = {}
        
        for table in all_tables:
            idx1 = set(indexes1.get(table, []))
            idx2 = set(indexes2.get(table, []))
            
            if idx1 != idx2:
                differences[table] = {
                    'only_in_db1': idx1 - idx2,
                    'only_in_db2': idx2 - idx1
                }
        
        return differences
    
    def run_comparison(self, detailed: bool = False) -> Dict[str, Any]:
        """Run complete database comparison"""
        self.connect_databases()
        
        try:
            print(f"Comparing databases:")
            print(f"  DB1: {self.db1_path}")
            print(f"  DB2: {self.db2_path}")
            print()
            
            # Compare tables
            table_comparison = self.compare_tables()
            
            # Compare indexes
            index_comparison = self.compare_indexes()
            
            # Print results
            self.print_comparison_results(table_comparison, index_comparison, detailed)
            
            return {
                'tables': table_comparison,
                'indexes': index_comparison
            }
            
        finally:
            self.conn1.close()
            self.conn2.close()
    
    def print_comparison_results(self, table_comp: Dict, index_comp: Dict, detailed: bool):
        """Print comparison results"""
        # Tables only in one database
        if table_comp['only_in_db1']:
            print(f"❌ Tables only in DB1: {', '.join(table_comp['only_in_db1'])}")
        
        if table_comp['only_in_db2']:
            print(f"❌ Tables only in DB2: {', '.join(table_comp['only_in_db2'])}")
        
        # Schema differences
        if table_comp['schema_differences']:
            print(f"❌ Schema differences in {len(table_comp['schema_differences'])} tables:")
            for table in table_comp['schema_differences']:
                print(f"  - {table}")
                if detailed:
                    print(f"    DB1: {table_comp['schema_differences'][table]['db1']}")
                    print(f"    DB2: {table_comp['schema_differences'][table]['db2']}")
        
        # Count differences
        if table_comp['count_differences']:
            print(f"❌ Record count differences in {len(table_comp['count_differences'])} tables:")
            for table, counts in table_comp['count_differences'].items():
                print(f"  - {table}: DB1({counts['db1']}) vs DB2({counts['db2']}) = {counts['difference']:+d}")
        
        # Data differences with detailed content comparison
        if table_comp['data_differences']:
            print(f"❌ Data differences detected in {len(table_comp['data_differences'])} tables:")
            for table in table_comp['data_differences']:
                sample_size = table_comp['data_differences'][table]['sample_size']
                print(f"  - {table} (sampled {sample_size} records)")
                
                if detailed:
                    # Show actual data differences
                    self._show_data_differences(table)
        
        # Index differences
        if index_comp:
            print(f"❌ Index differences in {len(index_comp)} tables:")
            for table, diffs in index_comp.items():
                if diffs['only_in_db1']:
                    print(f"  - {table}: {len(diffs['only_in_db1'])} indexes only in DB1")
                if diffs['only_in_db2']:
                    print(f"  - {table}: {len(diffs['only_in_db2'])} indexes only in DB2")
        
        # Summary
        total_issues = (
            len(table_comp['only_in_db1']) + 
            len(table_comp['only_in_db2']) +
            len(table_comp['schema_differences']) +
            len(table_comp['count_differences']) +
            len(table_comp['data_differences']) +
            len(index_comp)
        )
        
        print(f"\n{'='*50}")
        if total_issues == 0:
            print("✅ Databases are identical!")
        else:
            print(f"❌ Found {total_issues} difference categories")
            if not detailed:
                print("   Use --detailed flag for more information")
    
    def _show_data_differences(self, table: str):
        """Show actual data differences for a table"""
        try:
            columns = self.get_table_columns(self.conn1, table)
            if not columns:
                return
            
            # Get sample data from both databases
            data1 = self.sample_table_data(self.conn1, table, columns)
            data2 = self.sample_table_data(self.conn2, table, columns)
            
            # Convert to sets for comparison (excluding IDs if present)
            content_columns = [col for col in columns if col != 'id']
            
            def extract_content(data):
                """Extract non-ID content for comparison"""
                content_set = set()
                for row in data:
                    # Create tuple of non-ID values
                    content_tuple = tuple(
                        row[i] for i, col in enumerate(columns) 
                        if col in content_columns
                    )
                    content_set.add(content_tuple)
                return content_set
            
            content1 = extract_content(data1)
            content2 = extract_content(data2)
            
            only_in_db1 = content1 - content2
            only_in_db2 = content2 - content1
            
            if only_in_db1:
                print(f"    Records only in DB1 ({len(only_in_db1)}):")
                for record in list(only_in_db1)[:3]:  # Show first 3
                    print(f"      {dict(zip(content_columns, record))}")
                if len(only_in_db1) > 3:
                    print(f"      ... and {len(only_in_db1) - 3} more")
            
            if only_in_db2:
                print(f"    Records only in DB2 ({len(only_in_db2)}):")
                for record in list(only_in_db2)[:3]:  # Show first 3
                    print(f"      {dict(zip(content_columns, record))}")
                if len(only_in_db2) > 3:
                    print(f"      ... and {len(only_in_db2) - 3} more")
            
            if not only_in_db1 and not only_in_db2:
                print(f"    Content appears identical (differences may be in IDs or ordering)")
                
        except Exception as e:
            print(f"    Error analyzing differences: {e}")

def main():
    parser = argparse.ArgumentParser(description='Compare two SQLite database files')
    parser.add_argument('db1', help='Path to first database file')
    parser.add_argument('db2', help='Path to second database file')
    parser.add_argument('--detailed', action='store_true', help='Show detailed differences')
    parser.add_argument('--sample-size', type=int, default=100, help='Number of records to sample for data comparison')
    
    args = parser.parse_args()
    
    # Validate database files exist
    if not Path(args.db1).exists():
        print(f"Error: Database file '{args.db1}' does not exist")
        sys.exit(1)
    
    if not Path(args.db2).exists():
        print(f"Error: Database file '{args.db2}' does not exist")
        sys.exit(1)
    
    # Run comparison
    comparator = DatabaseComparator(args.db1, args.db2, args.sample_size)
    results = comparator.run_comparison(args.detailed)
    
    # Exit with non-zero if differences found
    total_differences = (
        len(results['tables']['only_in_db1']) +
        len(results['tables']['only_in_db2']) +
        len(results['tables']['schema_differences']) +
        len(results['tables']['count_differences']) +
        len(results['tables']['data_differences']) +
        len(results['indexes'])
    )
    
    sys.exit(0 if total_differences == 0 else 1)

if __name__ == '__main__':
    main()