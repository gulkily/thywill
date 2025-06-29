#!/usr/bin/env python3
"""
Backup Verification CLI Module

Verifies backup file integrity using checksums and database integrity checks.
Can be run independently or called from the CLI script.
"""

import sys
import os
import subprocess
import hashlib
from typing import Dict, Any


def verify_backup(backup_file: str) -> Dict[str, Any]:
    """
    Verify backup file integrity.
    
    Args:
        backup_file: Path to the backup file to verify
        
    Returns:
        Dict containing verification results
    """
    results = {
        'file_exists': False,
        'checksum_verified': False,
        'checksum_file_found': False,
        'database_integrity_ok': False,
        'errors': []
    }
    
    # Check if backup file exists
    if not os.path.exists(backup_file):
        results['errors'].append(f"Backup file not found: {backup_file}")
        return results
    
    results['file_exists'] = True
    
    # Check checksum if available
    checksum_file = f"{backup_file}.sha256"
    if os.path.exists(checksum_file):
        results['checksum_file_found'] = True
        
        try:
            # Read expected checksum
            with open(checksum_file, 'r') as f:
                expected_checksum = f.read().strip().split()[0]
            
            # Calculate actual checksum
            sha256_hash = hashlib.sha256()
            with open(backup_file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            actual_checksum = sha256_hash.hexdigest()
            
            if actual_checksum == expected_checksum:
                results['checksum_verified'] = True
            else:
                results['errors'].append("Checksum verification failed")
                
        except Exception as e:
            results['errors'].append(f"Checksum verification error: {e}")
    
    # Check database integrity
    try:
        result = subprocess.run([
            'sqlite3', backup_file, 'PRAGMA integrity_check;'
        ], capture_output=True, text=True, check=True)
        
        if 'ok' in result.stdout.lower():
            results['database_integrity_ok'] = True
        else:
            results['errors'].append("Database integrity check failed")
            
    except subprocess.CalledProcessError as e:
        results['errors'].append(f"Database integrity check error: {e}")
    except FileNotFoundError:
        results['errors'].append("sqlite3 command not found - cannot verify database integrity")
    
    return results


def print_verification_report(backup_file: str, results: Dict[str, Any]) -> None:
    """Print a formatted verification report to stdout."""
    print(f"🔍 Verifying Backup Integrity: {backup_file}")
    print("=" * 50)
    print()
    
    if not results['file_exists']:
        print("❌ Backup file not found")
        for error in results['errors']:
            print(f"   {error}")
        return
    
    print("📁 File integrity:")
    if results['checksum_file_found']:
        if results['checksum_verified']:
            print("   ✅ Checksum verification passed")
        else:
            print("   ❌ Checksum verification failed")
    else:
        print("   ⚠️  No checksum file found, skipping checksum verification")
    
    print()
    print("🗄️  Database integrity:")
    if results['database_integrity_ok']:
        print("   ✅ Database integrity check passed")
    else:
        print("   ❌ Database integrity check failed")
    
    if results['errors']:
        print()
        print("❌ Errors encountered:")
        for error in results['errors']:
            print(f"   • {error}")
    
    print()
    if not results['errors']:
        print("✅ Backup verification completed successfully")
    else:
        print("❌ Backup verification failed")


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python backup_verification.py <backup_file>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    
    try:
        results = verify_backup(backup_file)
        print_verification_report(backup_file, results)
        
        # Exit with error code if verification failed
        if results['errors']:
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()