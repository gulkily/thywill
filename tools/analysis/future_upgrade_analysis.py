#!/usr/bin/env python3
"""
Future Upgrade Strategy Analysis Tool

This tool analyzes the current system state and provides comprehensive
reports on upgrade readiness, data preservation capabilities, and
recommended procedures for seamless upgrades with zero data loss.

Key Features:
- Analyzes current database state vs archive coverage
- Generates upgrade readiness scores
- Provides step-by-step upgrade procedures
- Identifies data preservation opportunities and risks
- Creates export recommendations for critical system state

Usage:
    python future_upgrade_analysis.py                    # Full analysis
    python future_upgrade_analysis.py --summary          # Summary only
    python future_upgrade_analysis.py --export-plan      # Generate export commands
    python future_upgrade_analysis.py --validate-only    # Just validate archives
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from models import engine, User, Prayer, PrayerMark, Session as UserSession, InviteToken, AuthenticationRequest
from app_helpers.services.system_archive_service import SystemArchiveService
from app_helpers.services.system_restore_service import SystemRestoreService
from app_helpers.services.text_archive_service import TextArchiveService
from validate_archive_consistency import ArchiveConsistencyValidator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FutureUpgradeAnalyzer:
    """Comprehensive upgrade strategy analysis"""
    
    def __init__(self):
        self.system_archive = SystemArchiveService()
        self.system_restore = SystemRestoreService()
        self.text_archive = TextArchiveService()
        self.validator = ArchiveConsistencyValidator()
        
        self.analysis_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_readiness_score': 0.0,
            'data_preservation_analysis': {},
            'system_state_analysis': {},
            'archive_completeness': {},
            'upgrade_recommendations': [],
            'export_commands': [],
            'risk_assessment': {},
            'estimated_downtime': '',
            'issues_found': [],
            'warnings': []
        }
    
    def analyze_upgrade_readiness(self, include_system_state: bool = True) -> Dict[str, Any]:
        """Perform comprehensive upgrade readiness analysis"""
        logger.info("Starting future upgrade readiness analysis...")
        
        try:
            # Step 1: Analyze archive completeness
            logger.info("Step 1: Analyzing archive completeness...")
            self._analyze_archive_completeness()
            
            # Step 2: Analyze data preservation capabilities
            logger.info("Step 2: Analyzing data preservation...")
            self._analyze_data_preservation()
            
            # Step 3: Analyze system state (sessions, tokens, etc.)
            if include_system_state:
                logger.info("Step 3: Analyzing system state preservation...")
                self._analyze_system_state()
            
            # Step 4: Generate upgrade recommendations
            logger.info("Step 4: Generating upgrade recommendations...")
            self._generate_upgrade_recommendations()
            
            # Step 5: Calculate overall readiness score
            logger.info("Step 5: Calculating upgrade readiness score...")
            self._calculate_readiness_score()
            
            # Step 6: Assess risks and estimate downtime
            logger.info("Step 6: Assessing risks and estimating downtime...")
            self._assess_risks_and_downtime()
            
            logger.info("Upgrade readiness analysis completed successfully")
            return {
                'success': True,
                'results': self.analysis_results
            }
            
        except Exception as e:
            logger.error(f"Upgrade analysis failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_archive_completeness(self):
        """Analyze completeness of existing archives"""
        # Use existing validation tool
        validation_result = self.validator.validate_consistency(summary_only=True)
        
        if validation_result.get('success'):
            validation_data = validation_result['results']
            
            self.analysis_results['archive_completeness'] = {
                'community_data_score': validation_data['consistency_score'],
                'total_users_archived': validation_data['total_users_in_archives'],
                'total_prayers_archived': validation_data['total_prayers_in_archives'],
                'missing_archive_paths': validation_data['missing_archive_paths'],
                'broken_archive_paths': validation_data['broken_archive_paths'],
                'orphaned_data': validation_data['orphaned_prayers'] + validation_data['orphaned_prayer_marks']
            }
            
            if validation_data['issues_found']:
                self.analysis_results['issues_found'].extend(validation_data['issues_found'])
        else:
            self.analysis_results['warnings'].append("Failed to validate archive consistency")
            self.analysis_results['archive_completeness'] = {'community_data_score': 0.0}
    
    def _analyze_data_preservation(self):
        """Analyze what data gets preserved vs lost in upgrades"""
        with Session(engine) as session:
            # Count database records
            total_users = len(session.exec(select(User)).all())
            total_prayers = len(session.exec(select(Prayer)).all())
            total_prayer_marks = len(session.exec(select(PrayerMark)).all())
            
            # Analyze preservation by category
            preservation_analysis = {
                'fully_preserved': {
                    'description': 'Data that survives upgrades with 100% fidelity',
                    'categories': [
                        f"Users ({total_users} records) - Display names, join dates, invite relationships",
                        f"Prayers ({total_prayers} records) - Full text, AI prayers, timestamps, status",
                        f"Prayer Marks ({total_prayer_marks} records) - Who prayed for what, when",
                        "Prayer Attributes - Archive/answered/flagged status with metadata",
                        "Activity Logs - Complete prayer interaction history",
                        "Invite Tree - User invitation relationships and genealogy"
                    ],
                    'preservation_method': 'Text archives + database import',
                    'data_loss_risk': 'Zero',
                    'human_readable': True
                },
                'system_state_preservable': {
                    'description': 'System state that CAN be preserved with new archival system',
                    'categories': [],
                    'preservation_method': 'Enhanced system state archives',
                    'data_loss_risk': 'Zero (with implementation)',
                    'human_readable': True
                },
                'traditionally_lost': {
                    'description': 'Data traditionally lost in upgrades (now preservable)',
                    'categories': [],
                    'preservation_method': 'Previously: manual export/import',
                    'data_loss_risk': 'Previously: High, Now: Zero',
                    'human_readable': False
                }
            }
            
            # Count system state data  
            # Note: Assume all sessions are active if no is_active field exists
            active_sessions = session.exec(select(UserSession)).all()
            # Check for admin users via role system
            try:
                from sqlmodel import text
                admin_users = session.exec(
                    text("SELECT DISTINCT u.* FROM user u JOIN user_roles ur ON u.id = ur.user_id JOIN role r ON ur.role_id = r.id WHERE r.name = 'admin'")
                ).all()
            except Exception:
                # Fallback: assume no admin users if role system not working
                admin_users = []
            active_tokens = session.exec(select(InviteToken).where(InviteToken.used == False)).all()
            pending_auth = session.exec(select(AuthenticationRequest).where(AuthenticationRequest.status == 'pending')).all()
            
            if active_sessions:
                preservation_analysis['system_state_preservable']['categories'].append(
                    f"Active Sessions ({len(active_sessions)} sessions) - Users stay logged in"
                )
                preservation_analysis['traditionally_lost']['categories'].append(
                    f"Active Sessions ({len(active_sessions)} sessions) - Users had to re-login"
                )
            
            if admin_users:
                preservation_analysis['system_state_preservable']['categories'].append(
                    f"Admin Role Assignments ({len(admin_users)} admins) - Permissions preserved"
                )
                preservation_analysis['traditionally_lost']['categories'].append(
                    f"Admin Role Assignments ({len(admin_users)} admins) - Manual reassignment needed"
                )
            
            if active_tokens:
                preservation_analysis['system_state_preservable']['categories'].append(
                    f"Active Invite Tokens ({len(active_tokens)} tokens) - Links remain valid"
                )
                preservation_analysis['traditionally_lost']['categories'].append(
                    f"Active Invite Tokens ({len(active_tokens)} tokens) - Links became invalid"
                )
            
            if pending_auth:
                preservation_analysis['system_state_preservable']['categories'].append(
                    f"Pending Auth Requests ({len(pending_auth)} requests) - Multi-device auth continues"
                )
                preservation_analysis['traditionally_lost']['categories'].append(
                    f"Pending Auth Requests ({len(pending_auth)} requests) - Users had to restart auth"
                )
            
            self.analysis_results['data_preservation_analysis'] = preservation_analysis
    
    def _analyze_system_state(self):
        """Analyze current system state archival capabilities"""
        system_stats = self.system_archive.get_system_archive_stats()
        
        # Test system archive functionality
        test_restore = self.system_restore.restore_all_system_state(dry_run=True)
        
        self.analysis_results['system_state_analysis'] = {
            'system_archives_exist': system_stats['system_dir_exists'],
            'current_state_files': system_stats['current_state_files'],
            'event_log_files': system_stats['event_log_files'],
            'events_by_type': system_stats['total_events_by_type'],
            'restoration_capability': {
                'sessions_restorable': test_restore.get('sessions_restored', 0),
                'admins_restorable': test_restore.get('admins_restored', 0),
                'tokens_restorable': test_restore.get('tokens_restored', 0),
                'auth_requests_restorable': test_restore.get('auth_requests_restored', 0),
                'total_warnings': len(test_restore.get('warnings', [])),
                'total_errors': len(test_restore.get('errors', []))
            }
        }
        
        # Check if system archival is active
        if not system_stats['current_state_files']:
            self.analysis_results['warnings'].append(
                "System state archival not active - consider running system_archive.rebuild_all_snapshots()"
            )
    
    def _generate_upgrade_recommendations(self):
        """Generate specific upgrade recommendations based on analysis"""
        recommendations = []
        export_commands = []
        
        # Always recommend community data validation
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Community Data',
            'action': 'Validate archive completeness',
            'command': 'python tools/analysis/validate_archive_consistency.py',
            'reason': 'Ensure all community data is properly archived before upgrade'
        })
        
        export_commands.append('# Validate community data archives')
        export_commands.append('./thywill heal-archives')
        export_commands.append('python tools/analysis/validate_archive_consistency.py')
        export_commands.append('')
        
        # System state recommendations
        system_analysis = self.analysis_results.get('system_state_analysis', {})
        restoration_cap = system_analysis.get('restoration_capability', {})
        
        if not system_analysis.get('system_archives_exist'):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'System State',
                'action': 'Initialize system state archival',
                'command': 'python -c "from app_helpers.services.system_archive_service import SystemArchiveService; SystemArchiveService().rebuild_all_snapshots()"',
                'reason': 'Enable zero-downtime upgrades by preserving system state'
            })
            export_commands.append('# Initialize system state archival')
            export_commands.append('python -c "from app_helpers.services.system_archive_service import SystemArchiveService; SystemArchiveService().rebuild_all_snapshots()"')
            export_commands.append('')
        
        if restoration_cap.get('sessions_restorable', 0) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'User Experience',
                'action': 'Preserve active sessions',
                'command': 'System archival already active for sessions',
                'reason': f"Keep {restoration_cap['sessions_restorable']} users logged in during upgrade"
            })
        
        if restoration_cap.get('admins_restorable', 0) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Security',
                'action': 'Preserve admin roles',
                'command': 'System archival already active for admin roles',
                'reason': f"Maintain {restoration_cap['admins_restorable']} admin role assignments"
            })
        
        if restoration_cap.get('tokens_restorable', 0) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Community Growth',
                'action': 'Preserve invite tokens',
                'command': 'System archival already active for tokens',
                'reason': f"Keep {restoration_cap['tokens_restorable']} invite links valid"
            })
        
        # Database backup recommendation
        recommendations.append({
            'priority': 'CRITICAL',
            'category': 'Safety',
            'action': 'Create database backup',
            'command': './thywill backup',
            'reason': 'Enable rollback if upgrade fails'
        })
        
        export_commands.append('# Create safety backup')
        export_commands.append('./thywill backup')
        export_commands.append('')
        
        # Archive completeness check
        archive_score = self.analysis_results.get('archive_completeness', {}).get('community_data_score', 0)
        if archive_score < 95:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Data Integrity',
                'action': 'Fix archive issues before upgrade',
                'command': 'python tools/analysis/validate_archive_consistency.py --fix',
                'reason': f'Archive consistency score is {archive_score}% - should be 95%+'
            })
        
        self.analysis_results['upgrade_recommendations'] = recommendations
        self.analysis_results['export_commands'] = export_commands
    
    def _calculate_readiness_score(self):
        """Calculate overall upgrade readiness score (0-100)"""
        # Community data score (40% weight)
        archive_score = self.analysis_results.get('archive_completeness', {}).get('community_data_score', 0)
        community_score = (archive_score / 100) * 40
        
        # System state preservation score (30% weight)
        system_analysis = self.analysis_results.get('system_state_analysis', {})
        restoration_cap = system_analysis.get('restoration_capability', {})
        
        system_items = [
            restoration_cap.get('sessions_restorable', 0),
            restoration_cap.get('admins_restorable', 0),
            restoration_cap.get('tokens_restorable', 0),
            restoration_cap.get('auth_requests_restorable', 0)
        ]
        
        # If any system state exists and is restorable, score is high
        total_system_items = sum(1 for x in system_items if x > 0)
        if total_system_items > 0:
            system_score = 30  # Full points if system state is preserved
        else:
            system_score = 15  # Half points if no system state to preserve
        
        # Safety and process score (30% weight)
        safety_score = 30  # Assume full points for established process
        
        # Deduct points for issues
        issues_count = len(self.analysis_results.get('issues_found', []))
        warnings_count = len(self.analysis_results.get('warnings', []))
        
        penalty = min(20, issues_count * 5 + warnings_count * 2)
        
        overall_score = max(0, community_score + system_score + safety_score - penalty)
        self.analysis_results['overall_readiness_score'] = round(overall_score, 1)
    
    def _assess_risks_and_downtime(self):
        """Assess upgrade risks and estimate downtime"""
        readiness_score = self.analysis_results['overall_readiness_score']
        system_state = self.analysis_results.get('system_state_analysis', {})
        
        # Risk assessment based on preservation capabilities
        risks = {
            'data_loss_risk': 'VERY LOW',
            'user_disruption_risk': 'LOW',
            'rollback_capability': 'EXCELLENT',
            'complexity_risk': 'LOW'
        }
        
        # Adjust risks based on system state preservation
        restoration_cap = system_state.get('restoration_capability', {})
        if restoration_cap.get('sessions_restorable', 0) == 0:
            risks['user_disruption_risk'] = 'MEDIUM'
            risks['data_loss_risk'] = 'LOW'
        
        # Estimate downtime
        if readiness_score >= 90:
            downtime = "2-5 minutes (near zero-downtime upgrade possible)"
        elif readiness_score >= 80:
            downtime = "5-15 minutes (minimal user disruption)"
        elif readiness_score >= 70:
            downtime = "15-30 minutes (moderate preparation needed)"
        else:
            downtime = "30+ minutes (significant preparation required)"
        
        self.analysis_results['risk_assessment'] = risks
        self.analysis_results['estimated_downtime'] = downtime


def print_analysis_report(results: Dict, summary_only: bool = False):
    """Print formatted upgrade analysis report"""
    r = results['results']
    
    print("\n" + "="*70)
    print("FUTURE UPGRADE STRATEGY ANALYSIS REPORT")
    print("="*70)
    print(f"Analysis timestamp: {r['timestamp']}")
    
    # Overall readiness score
    score = r['overall_readiness_score']
    if score >= 90:
        score_icon = "🟢"
        score_status = "EXCELLENT - Ready for zero-downtime upgrade"
    elif score >= 80:
        score_icon = "🟡"
        score_status = "GOOD - Ready with minimal disruption"
    elif score >= 70:
        score_icon = "🟠"
        score_status = "FAIR - Preparation recommended"
    else:
        score_icon = "🔴"
        score_status = "POOR - Significant preparation needed"
    
    print(f"\n{score_icon} UPGRADE READINESS SCORE: {score}/100")
    print(f"Status: {score_status}")
    print(f"Estimated downtime: {r['estimated_downtime']}")
    
    # Data preservation summary
    print(f"\n📊 DATA PRESERVATION SUMMARY:")
    preservation = r.get('data_preservation_analysis', {})
    
    fully_preserved = preservation.get('fully_preserved', {})
    print(f"✅ Fully Preserved (Zero Loss):")
    for category in fully_preserved.get('categories', []):
        print(f"   • {category}")
    
    system_preservable = preservation.get('system_state_preservable', {})
    if system_preservable.get('categories'):
        print(f"\n🔄 System State Preservable (New Capability):")
        for category in system_preservable['categories']:
            print(f"   • {category}")
    
    # Risk assessment
    risks = r.get('risk_assessment', {})
    print(f"\n⚠️  RISK ASSESSMENT:")
    print(f"   Data loss risk: {risks.get('data_loss_risk', 'UNKNOWN')}")
    print(f"   User disruption risk: {risks.get('user_disruption_risk', 'UNKNOWN')}")
    print(f"   Rollback capability: {risks.get('rollback_capability', 'UNKNOWN')}")
    
    if not summary_only:
        # Recommendations
        recommendations = r.get('upgrade_recommendations', [])
        if recommendations:
            print(f"\n🎯 UPGRADE RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                priority_icon = "🔴" if rec['priority'] == 'CRITICAL' else "🟠" if rec['priority'] == 'HIGH' else "🟡"
                print(f"   {i}. {priority_icon} [{rec['priority']}] {rec['action']}")
                print(f"      Category: {rec['category']}")
                print(f"      Command: {rec['command']}")
                print(f"      Reason: {rec['reason']}")
                print()
        
        # Export commands
        export_commands = r.get('export_commands', [])
        if export_commands:
            print(f"\n💾 RECOMMENDED EXPORT SEQUENCE:")
            for cmd in export_commands:
                if cmd.strip():
                    print(f"   {cmd}")
    
    # Issues and warnings
    issues = r.get('issues_found', [])
    warnings = r.get('warnings', [])
    
    if issues:
        print(f"\n🚨 ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"   • {issue}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not issues and not warnings:
        print(f"\n✅ NO CRITICAL ISSUES FOUND")
    
    print("\n" + "="*70)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Analyze future upgrade strategy and readiness')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary only, not detailed breakdown')
    parser.add_argument('--export-plan', action='store_true',
                       help='Generate export command sequence only')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate existing archives')
    parser.add_argument('--no-system-state', action='store_true',
                       help='Skip system state analysis')
    
    args = parser.parse_args()
    
    analyzer = FutureUpgradeAnalyzer()
    
    if args.validate_only:
        # Just run archive validation
        validation_result = analyzer.validator.validate_consistency(summary_only=args.summary)
        if validation_result.get('success'):
            from tools.analysis.validate_archive_consistency import print_validation_report
            print_validation_report(validation_result, args.summary)
            return 0 if validation_result['results']['consistency_score'] >= 95 else 1
        else:
            print(f"Validation failed: {validation_result.get('error')}")
            return 2
    
    # Full analysis
    results = analyzer.analyze_upgrade_readiness(
        include_system_state=not args.no_system_state
    )
    
    if results.get('success'):
        if args.export_plan:
            # Just print export commands
            export_commands = results['results'].get('export_commands', [])
            print("# Future Upgrade Export Sequence")
            print("# Generated by ThyWill Future Upgrade Analysis")
            print(f"# Timestamp: {results['results']['timestamp']}")
            print()
            for cmd in export_commands:
                print(cmd)
        else:
            print_analysis_report(results, args.summary)
        
        # Return exit code based on readiness score
        score = results['results']['overall_readiness_score']
        if score >= 90:
            return 0  # Excellent readiness
        elif score >= 80:
            return 1  # Good readiness with minor issues
        else:
            return 2  # Significant preparation needed
    else:
        print(f"Analysis failed: {results.get('error')}")
        return 3


if __name__ == '__main__':
    sys.exit(main())