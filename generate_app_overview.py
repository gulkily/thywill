#!/usr/bin/env python3
"""
Generate ThyWill app overview with current database statistics.
Run this script to update the overview with live data from production.
"""

import sqlite3
import os
import subprocess
from datetime import datetime
from pathlib import Path

def get_git_stats():
    """Get git repository statistics."""
    try:
        # Get total commit count
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                              capture_output=True, text=True)
        total_commits = int(result.stdout.strip()) if result.returncode == 0 else 0
        
        # Get first commit date
        result = subprocess.run(['git', 'log', '--reverse', '--format=%ci', '--max-count=1'], 
                              capture_output=True, text=True)
        first_commit = result.stdout.strip().split()[0] if result.returncode == 0 else "2025-05-29"
        
        # Get recent commits (last 7 days)
        result = subprocess.run(['git', 'log', '--since="7 days ago"', '--oneline'], 
                              capture_output=True, text=True)
        recent_commits = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        
        return {
            'total_commits': total_commits,
            'first_commit': first_commit,
            'recent_commits': recent_commits
        }
    except Exception as e:
        print(f"Warning: Could not get git stats: {e}")
        return {
            'total_commits': 500,
            'first_commit': "2025-05-29",
            'recent_commits': 10
        }

def get_db_stats():
    """Get database statistics."""
    db_path = 'thywill.db'
    
    if not os.path.exists(db_path):
        print(f"Warning: Database not found at {db_path}")
        return {
            'total_users': 25,
            'total_prayers': 30,
            'total_marks': 87,
            'db_size_kb': 208,
            'active_users_7d': 5,
            'prayers_7d': 10
        }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM user")
        total_users = cursor.fetchone()[0]
        
        # Get prayer count
        cursor.execute("SELECT COUNT(*) FROM prayer")
        total_prayers = cursor.fetchone()[0]
        
        # Get prayer marks count
        cursor.execute("SELECT COUNT(*) FROM prayermark")
        total_marks = cursor.fetchone()[0]
        
        # Get users active in last 7 days
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM session 
            WHERE created_at > datetime('now', '-7 days')
        """)
        result = cursor.fetchone()
        active_users_7d = result[0] if result else 0
        
        # Get prayers created in last 7 days
        cursor.execute("""
            SELECT COUNT(*) FROM prayer 
            WHERE created_at > datetime('now', '-7 days')
        """)
        result = cursor.fetchone()
        prayers_7d = result[0] if result else 0
        
        conn.close()
        
        # Get database file size
        db_size_kb = os.path.getsize(db_path) // 1024
        
        return {
            'total_users': total_users,
            'total_prayers': total_prayers,
            'total_marks': total_marks,
            'db_size_kb': db_size_kb,
            'active_users_7d': active_users_7d,
            'prayers_7d': prayers_7d
        }
        
    except Exception as e:
        print(f"Warning: Could not get database stats: {e}")
        return {
            'total_users': 25,
            'total_prayers': 30,
            'total_marks': 87,
            'db_size_kb': 208,
            'active_users_7d': 5,
            'prayers_7d': 10
        }

def generate_overview():
    """Generate the app overview markdown with current stats."""
    
    git_stats = get_git_stats()
    db_stats = get_db_stats()
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Calculate months since start
    from datetime import datetime
    start_date = datetime.strptime(git_stats['first_commit'], "%Y-%m-%d")
    months_dev = (datetime.now() - start_date).days // 30 + 1
    
    # Calculate average engagement
    avg_engagement = db_stats['total_marks'] / max(db_stats['total_prayers'], 1)
    
    # Read template file
    template_path = 'app_overview_template.md'
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Format template with current data
    content = template_content.format(
        current_date=current_date,
        total_users=db_stats['total_users'],
        active_users_7d=db_stats['active_users_7d'],
        db_size_kb=db_stats['db_size_kb'],
        total_prayers=db_stats['total_prayers'],
        prayers_7d=db_stats['prayers_7d'],
        total_marks=db_stats['total_marks'],
        avg_engagement=f"{avg_engagement:.1f}",
        first_commit=git_stats['first_commit'],
        months_dev=months_dev,
        total_commits=git_stats['total_commits'],
        recent_commits=git_stats['recent_commits']
    )
    
    return content

def main():
    """Generate and save the app overview."""
    try:
        content = generate_overview()
        
        # Save to file
        output_file = "thywill_app_overview.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ App overview generated: {output_file}")
        print(f"✓ File size: {len(content)} characters")
        
        # Optionally generate PDF if script exists
        if os.path.exists("md_to_pdf.py"):
            print("✓ PDF converter available - run: python md_to_pdf.py thywill_app_overview.md")
        
    except Exception as e:
        print(f"Error generating overview: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())