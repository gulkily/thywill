# app_helpers/routes/file_routes.py
"""
File system routes for serving archive files with clean URLs.

Provides URLs that mirror the file system structure:
/files/prayers/{year}/{month}/{filename}.txt
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from app_helpers.services.auth_helpers import require_full_auth
from sqlmodel import Session, select
from models import engine, Prayer
from pathlib import Path
import re
import os

router = APIRouter(prefix="/files", tags=["files"])


def get_text_archive_base_dir():
    """Get text archive base directory"""
    from app import TEXT_ARCHIVE_BASE_DIR
    return Path(TEXT_ARCHIVE_BASE_DIR)


def find_prayer_by_file_path(year: str, month: str, filename: str) -> Prayer:
    """
    Find prayer by matching file system path components.
    
    Args:
        year: Year string (e.g., "2025")
        month: Month string (e.g., "08")
        filename: Filename with .txt extension
        
    Returns:
        Prayer object if found
        
    Raises:
        HTTPException: If prayer not found
    """
    with Session(engine) as db:
        # Search for prayers with text_file_path containing the year/month/filename pattern
        pattern = f"/{year}/{month}/{filename}"
        
        stmt = select(Prayer).where(
            Prayer.text_file_path.is_not(None),
            Prayer.text_file_path.like(f"%{pattern}")
        )
        prayer = db.exec(stmt).first()
        
        if not prayer:
            raise HTTPException(status_code=404, detail=f"Prayer file not found: {year}/{month}/{filename}")
        
        return prayer


def read_archive_file(file_path: str) -> str:
    """
    Read archive file content, handling both uncompressed and compressed files.
    
    Args:
        file_path: Path to the archive file
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        HTTPException: If file can't be read
    """
    path = Path(file_path)
    
    # First try to read uncompressed file
    if path.exists():
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    
    # TODO: Add compressed file reading when compression is implemented
    raise FileNotFoundError(f"Archive file not found: {file_path}")


@router.get("/prayers/{year}/{month}/{filename}")
async def get_prayer_file(
    year: str,
    month: str, 
    filename: str,
    current_session_user = Depends(require_full_auth)
):
    """
    Serve prayer archive file with file system-like URL.
    
    URL format: /files/prayers/2025/08/2025_08_10_prayer_at_1234.txt
    
    Args:
        year: 4-digit year (e.g., "2025")
        month: 2-digit month (e.g., "08") 
        filename: Filename with .txt extension
        current_session_user: Authenticated user session
        
    Returns:
        Plain text response with prayer archive content
    """
    current_user_obj, current_session = current_session_user
    
    # Validate URL parameters
    if not re.match(r'^\d{4}$', year):
        raise HTTPException(status_code=400, detail="Invalid year format")
    
    if not re.match(r'^\d{2}$', month):
        raise HTTPException(status_code=400, detail="Invalid month format") 
        
    if not filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")
    
    # Find the prayer by file path components
    try:
        prayer = find_prayer_by_file_path(year, month, filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Read and serve the file
    try:
        content = read_archive_file(prayer.text_file_path)
        
        return PlainTextResponse(
            content=content,
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "private, no-cache"
            }
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Archive file not found on disk: {filename}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File access failed: {str(e)}")