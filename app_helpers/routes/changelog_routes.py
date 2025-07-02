from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
from app_helpers.services.changelog_helpers import (
    refresh_changelog_if_needed, 
    get_changelog_entries, 
    group_entries_by_date,
    get_change_type_icon,
    get_git_head_commit,
    get_last_cached_commit
)

router = APIRouter()
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

@router.get("/changelog", response_class=HTMLResponse)
async def changelog(request: Request):
    """Display the user-friendly changelog page"""
    # Check if debug mode is enabled
    debug_mode = os.getenv('CHANGELOG_DEBUG', 'false').lower() == 'true'
    debug_info = None
    
    if debug_mode:
        # Debug info for troubleshooting
        debug_info = {
            "git_head": get_git_head_commit(),
            "last_cached": get_last_cached_commit(),
            "anthropic_key_exists": bool(os.getenv('ANTHROPIC_API_KEY')),
            "git_available": True,
            "entry_count": 0
        }
        
        try:
            # Test git availability with common paths
            git_paths = ['/usr/bin/git', '/usr/local/bin/git', 'git']
            git_found = False
            for git_path in git_paths:
                try:
                    subprocess.run([git_path, '--version'], capture_output=True, check=True)
                    git_found = True
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            debug_info["git_available"] = git_found
        except:
            debug_info["git_available"] = False
    
    # Refresh changelog if there are new commits
    refresh_result = refresh_changelog_if_needed()
    if debug_info:
        debug_info["refresh_attempted"] = refresh_result
    
    # Get recent changelog entries
    entries = get_changelog_entries(limit=20)
    if debug_info:
        debug_info["entry_count"] = len(entries)
    
    # Group by date for better display
    grouped_entries = group_entries_by_date(entries)
    
    return templates.TemplateResponse("changelog.html", {
        "request": request,
        "grouped_entries": grouped_entries,
        "get_change_type_icon": get_change_type_icon,
        "debug_info": debug_info
    })

@router.get("/api/changelog")
async def api_changelog():
    """JSON API endpoint for changelog data"""
    # Refresh changelog if there are new commits
    refresh_changelog_if_needed()
    
    # Get recent changelog entries
    entries = get_changelog_entries(limit=20)
    
    # Convert to JSON-serializable format
    changelog_data = []
    for entry in entries:
        changelog_data.append({
            'id': entry.commit_id,
            'friendly_description': entry.friendly_description,
            'change_type': entry.change_type,
            'date': entry.commit_date.isoformat(),
            'icon': get_change_type_icon(entry.change_type)
        })
    
    return JSONResponse(changelog_data)

@router.get("/admin/changelog/refresh")
async def admin_refresh_changelog():
    """Admin endpoint to manually refresh changelog (requires admin auth)"""
    # Note: This should include admin authentication check
    # For now, just refresh and return status
    updated = refresh_changelog_if_needed()
    
    if updated:
        return JSONResponse({'status': 'success', 'message': 'Changelog updated with new commits'})
    else:
        return JSONResponse({'status': 'no_change', 'message': 'No new commits found'})