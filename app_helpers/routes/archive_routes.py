from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer
from app_helpers.services.archive_download_service import ArchiveDownloadService
from app_helpers.services.auth_helpers import current_user, require_full_auth
from sqlmodel import Session
from models import engine, Prayer
import os
from pathlib import Path

router = APIRouter(prefix="/api/archive", tags=["archives"])

def get_archive_service():
    """Get archive download service instance"""
    from app import TEXT_ARCHIVE_BASE_DIR
    return ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)

@router.get("/user/{user_id}/download")
async def download_user_archive(
    user_id: str, 
    include_community: bool = True,
    current_session_user = Depends(require_full_auth)
):
    """Download user's complete text archive as ZIP file"""
    
    current_user_obj, current_session = current_session_user
    
    # Verify user can access this archive (own archive or admin)
    if current_user_obj.id != user_id and current_user_obj.display_name != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        download_service = get_archive_service()
        zip_path = download_service.create_user_archive_zip(user_id, include_community)
        
        # Return file for download
        filename = os.path.basename(zip_path)
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive creation failed: {str(e)}")

@router.get("/user/{user_id}/metadata")
async def get_user_archive_metadata(
    user_id: str,
    current_session_user = Depends(require_full_auth)
):
    """Get metadata about user's available archives"""
    
    current_user_obj, current_session = current_session_user
    
    # Verify user can access this metadata (own metadata or admin)
    if current_user_obj.id != user_id and current_user_obj.display_name != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        download_service = get_archive_service()
        metadata = download_service.get_user_archive_metadata(user_id)
        return metadata
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")

@router.get("/community/list")
async def list_community_archives(
    current_session_user = Depends(require_full_auth)
):
    """List all community archive files (available to all users)"""
    
    try:
        download_service = get_archive_service()
        archives = download_service.list_community_archives()
        return {"archives": archives}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive listing failed: {str(e)}")

@router.get("/community/download")
async def download_community_archive(
    current_session_user = Depends(require_full_auth)
):
    """Download complete community text archive (available to all users)"""
    
    try:
        download_service = get_archive_service()
        zip_path = download_service.create_full_community_zip()
        
        filename = os.path.basename(zip_path)
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Community archive creation failed: {str(e)}")

@router.get("/prayer/{prayer_id}/file")
async def get_prayer_archive_file(
    prayer_id: str,
    current_session_user = Depends(require_full_auth)
):
    """Get direct link to prayer's text archive file"""
    
    try:
        with Session(engine) as db:
            prayer = db.query(Prayer).filter_by(id=prayer_id).first()
            
            if not prayer:
                raise HTTPException(status_code=404, detail="Prayer not found")
            
            if not prayer.text_file_path:
                raise HTTPException(status_code=404, detail="No archive file for this prayer")
            
            # Read the archive file content
            download_service = get_archive_service()
            content = download_service._read_archive_file(prayer.text_file_path)
            
            # Return as plain text file
            filename = f"prayer_{prayer_id}_{prayer.created_at.strftime('%Y_%m_%d')}.txt"
            return Response(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 404s) without modification
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archive file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive file access failed: {str(e)}")

@router.delete("/downloads/cleanup")
async def cleanup_old_downloads(
    background_tasks: BackgroundTasks,
    current_session_user = Depends(require_full_auth)
):
    """Clean up old download files (admin only)"""
    
    current_user_obj, current_session = current_session_user
    
    if current_user_obj.display_name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    def cleanup_downloads():
        download_service = get_archive_service()
        download_service.cleanup_old_downloads(max_age_hours=24)
    
    background_tasks.add_task(cleanup_downloads)
    return {"message": "Download cleanup scheduled"}