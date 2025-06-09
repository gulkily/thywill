from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app_helpers.services.changelog_helpers import (
    refresh_changelog_if_needed, 
    get_changelog_entries, 
    group_entries_by_date,
    get_change_type_icon
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/changelog", response_class=HTMLResponse)
async def changelog(request: Request):
    """Display the user-friendly changelog page"""
    # Refresh changelog if there are new commits
    refresh_changelog_if_needed()
    
    # Get recent changelog entries
    entries = get_changelog_entries(limit=20)
    
    # Group by date for better display
    grouped_entries = group_entries_by_date(entries)
    
    return templates.TemplateResponse("changelog.html", {
        "request": request,
        "grouped_entries": grouped_entries,
        "get_change_type_icon": get_change_type_icon
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