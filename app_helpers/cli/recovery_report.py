#!/usr/bin/env python3
"""
Recovery Report CLI Module

Generates comprehensive recovery capability reports for the archive system.
Can be run independently or called from the CLI script.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from app_helpers.services.database_recovery import CompleteSystemRecovery


def analyze_archive_structure(archive_dir: Path) -> Dict[str, Any]:
    """
    Analyze archive directory structure and file counts.
    
    Args:
        archive_dir: Path to the archive directory
        
    Returns:
        Dict containing analysis results
    """
    analysis = {
        'core_data': {},
        'enhanced_data': {},
        'prayer_metadata': {},
        'recommendations': []
    }
    
    # Core data recovery capability
    prayers_dir = archive_dir / 'prayers'
    users_dir = archive_dir / 'users'
    activity_dir = archive_dir / 'activity'
    
    if prayers_dir.exists():
        prayer_files = list(prayers_dir.rglob('*.txt'))
        analysis['core_data']['prayers'] = {
            'exists': True,
            'file_count': len(prayer_files)
        }
    else:
        analysis['core_data']['prayers'] = {
            'exists': False,
            'file_count': 0
        }
    
    if users_dir.exists():
        user_files = list(users_dir.glob('*.txt'))
        analysis['core_data']['users'] = {
            'exists': True,
            'file_count': len(user_files)
        }
    else:
        analysis['core_data']['users'] = {
            'exists': False,
            'file_count': 0
        }
    
    if activity_dir.exists():
        activity_files = list(activity_dir.glob('*.txt'))
        analysis['core_data']['activity'] = {
            'exists': True,
            'file_count': len(activity_files)
        }
    else:
        analysis['core_data']['activity'] = {
            'exists': False,
            'file_count': 0
        }
    
    # Enhanced data recovery capability
    auth_dir = archive_dir / 'auth'
    roles_dir = archive_dir / 'roles'
    system_dir = archive_dir / 'system'
    
    if auth_dir.exists():
        auth_files = list(auth_dir.rglob('*.txt'))
        analysis['enhanced_data']['auth'] = {
            'exists': True,
            'file_count': len(auth_files)
        }
    else:
        analysis['enhanced_data']['auth'] = {
            'exists': False,
            'file_count': 0
        }
    
    if roles_dir.exists():
        role_files = list(roles_dir.glob('*.txt'))
        analysis['enhanced_data']['roles'] = {
            'exists': True,
            'file_count': len(role_files)
        }
    else:
        analysis['enhanced_data']['roles'] = {
            'exists': False,
            'file_count': 0
        }
    
    if system_dir.exists():
        system_files = list(system_dir.glob('*.txt'))
        analysis['enhanced_data']['system'] = {
            'exists': True,
            'file_count': len(system_files)
        }
    else:
        analysis['enhanced_data']['system'] = {
            'exists': False,
            'file_count': 0
        }
    
    # Prayer metadata recovery
    if prayers_dir.exists():
        attrs_dir = prayers_dir / 'attributes'
        marks_dir = prayers_dir / 'marks'
        skips_dir = prayers_dir / 'skips'
        
        if attrs_dir.exists():
            attr_files = list(attrs_dir.glob('*.txt'))
            analysis['prayer_metadata']['attributes'] = {
                'exists': True,
                'file_count': len(attr_files)
            }
        else:
            analysis['prayer_metadata']['attributes'] = {
                'exists': False,
                'file_count': 0
            }
        
        if marks_dir.exists():
            mark_files = list(marks_dir.glob('*.txt'))
            analysis['prayer_metadata']['marks'] = {
                'exists': True,
                'file_count': len(mark_files)
            }
        else:
            analysis['prayer_metadata']['marks'] = {
                'exists': False,
                'file_count': 0
            }
        
        if skips_dir.exists():
            skip_files = list(skips_dir.glob('*.txt'))
            analysis['prayer_metadata']['skips'] = {
                'exists': True,
                'file_count': len(skip_files)
            }
        else:
            analysis['prayer_metadata']['skips'] = {
                'exists': False,
                'file_count': 0
            }
    
    # Generate recommendations
    has_core = (analysis['core_data']['prayers']['exists'] and 
                analysis['core_data']['users']['exists'])
    has_enhanced = (analysis['enhanced_data']['auth']['exists'] and 
                   analysis['enhanced_data']['roles']['exists'])
    
    if has_core and has_enhanced:
        analysis['recommendations'] = [
            "Complete recovery capability available!",
            "All data types can be fully reconstructed.",
            'Recommended: Run "thywill test-recovery" to validate.'
        ]
    elif has_core:
        analysis['recommendations'] = [
            "Core recovery capability available!",
            "Basic prayer and user data can be reconstructed.",
            "Authentication and roles will use defaults.",
            'Recommended: Run "thywill test-recovery" to validate.'
        ]
    else:
        analysis['recommendations'] = [
            "Limited recovery capability.",
            "Missing critical archive files.",
            "Recommended: Check archive generation and run backup."
        ]
    
    return analysis


def generate_recovery_report() -> Dict[str, Any]:
    """
    Generate comprehensive recovery capability report.
    
    Returns:
        Dict containing the complete report data
    """
    try:
        recovery = CompleteSystemRecovery('text_archives')
        archive_dir = recovery.archive_dir
        
        report = {
            'archive_dir': str(archive_dir.absolute()),
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'analysis': analyze_archive_structure(archive_dir)
        }
        
        return report
        
    except Exception as e:
        raise RuntimeError(f"Report generation failed: {e}")


def print_recovery_report(report: Dict[str, Any]) -> None:
    """Print formatted recovery capability report."""
    print('📊 Recovery Capability Report')
    print('=' * 60)
    print(f'Archive Directory: {report["archive_dir"]}')
    print(f'Report Generated: {report["generated_at"]}')
    print()
    
    analysis = report['analysis']
    
    # Core data recovery capability
    print('🔵 CORE DATA RECOVERY')
    print('-' * 30)
    
    core_data = analysis['core_data']
    
    prayers = core_data['prayers']
    if prayers['exists']:
        print(f'✅ Prayer archives: {prayers["file_count"]} files')
    else:
        print('❌ Prayer archives: missing')
    
    users = core_data['users']
    if users['exists']:
        print(f'✅ User archives: {users["file_count"]} files')
    else:
        print('❌ User archives: missing')
    
    activity = core_data['activity']
    if activity['exists']:
        print(f'✅ Activity archives: {activity["file_count"]} files')
    else:
        print('❌ Activity archives: missing')
    
    print()
    
    # Enhanced data recovery capability
    print('🟡 ENHANCED DATA RECOVERY')
    print('-' * 30)
    
    enhanced_data = analysis['enhanced_data']
    
    auth = enhanced_data['auth']
    if auth['exists']:
        print(f'✅ Authentication archives: {auth["file_count"]} files')
    else:
        print('⚠️  Authentication archives: missing (will use defaults)')
    
    roles = enhanced_data['roles']
    if roles['exists']:
        print(f'✅ Role system archives: {roles["file_count"]} files')
    else:
        print('⚠️  Role system archives: missing (will create defaults)')
    
    system = enhanced_data['system']
    if system['exists']:
        print(f'✅ System state archives: {system["file_count"]} files')
    else:
        print('⚠️  System state archives: missing (will use defaults)')
    
    print()
    
    # Prayer metadata recovery
    print('🟢 PRAYER METADATA RECOVERY')
    print('-' * 30)
    
    if core_data['prayers']['exists']:
        metadata = analysis['prayer_metadata']
        
        attributes = metadata.get('attributes', {'exists': False, 'file_count': 0})
        if attributes['exists']:
            print(f'✅ Prayer attributes: {attributes["file_count"]} files')
        else:
            print('⚠️  Prayer attributes: missing')
        
        marks = metadata.get('marks', {'exists': False, 'file_count': 0})
        if marks['exists']:
            print(f'✅ Prayer marks: {marks["file_count"]} files')
        else:
            print('⚠️  Prayer marks: missing')
        
        skips = metadata.get('skips', {'exists': False, 'file_count': 0})
        if skips['exists']:
            print(f'✅ Prayer skips: {skips["file_count"]} files')
        else:
            print('⚠️  Prayer skips: missing')
    
    print()
    
    # Recovery recommendations
    print('💡 RECOVERY RECOMMENDATIONS')
    print('-' * 30)
    
    recommendations = analysis['recommendations']
    for i, rec in enumerate(recommendations):
        if i == 0:
            if "Complete recovery" in rec:
                print(f'🎉 {rec}')
            elif "Core recovery" in rec:
                print(f'✅ {rec}')
            else:
                print(f'⚠️  {rec}')
        else:
            print(f'   {rec}')
    
    print()
    print('📋 Use "thywill test-recovery" to simulate complete recovery')
    print('📋 Use "thywill validate-archives" for detailed validation')


def main():
    """Main entry point when run as a standalone script."""
    try:
        report = generate_recovery_report()
        print_recovery_report(report)
        
    except Exception as e:
        print(f'❌ Report generation failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()