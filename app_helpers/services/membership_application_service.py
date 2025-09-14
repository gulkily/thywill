"""
Membership Application Service

Handles membership applications following the archive-first pattern:
1. Write application to text archive file FIRST
2. Store database record with reference to text file
3. Provide admin review and processing functionality
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select
from pathlib import Path

from models import MembershipApplication, InviteToken, engine
from app_helpers.services.text_archive_service import TextArchiveService


class MembershipApplicationService:
    """Service for managing membership applications with archive-first approach"""

    @staticmethod
    def create_application(username: str, essay: str, contact_info: str = None, ip_address: str = None) -> MembershipApplication:
        """
        Create a new membership application following archive-first pattern:
        1. Write to text archive file first
        2. Create database record with text file reference
        """
        app_id = uuid.uuid4().hex
        timestamp = datetime.utcnow()

        # Archive-first: Write text file before database
        text_file_path = MembershipApplicationService._write_to_archive(
            app_id, username, essay, contact_info, ip_address, timestamp
        )

        # Create database record
        with Session(engine) as db:
            application = MembershipApplication(
                id=app_id,
                username=username,
                essay=essay,
                contact_info=contact_info,
                ip_address=ip_address,
                status="pending",
                created_at=timestamp,
                text_file_path=text_file_path
            )

            db.add(application)
            db.commit()
            db.refresh(application)

        return application

    @staticmethod
    def get_pending_applications() -> List[MembershipApplication]:
        """Get all pending membership applications"""
        with Session(engine) as db:
            stmt = select(MembershipApplication).where(
                MembershipApplication.status == "pending"
            ).order_by(MembershipApplication.created_at.asc())
            return list(db.exec(stmt).all())

    @staticmethod
    def approve_application(app_id: str, admin_user_id: str) -> Optional[InviteToken]:
        """
        Approve a membership application and generate invite token
        Updates both text archive and database
        """
        with Session(engine) as db:
            # Get application
            stmt = select(MembershipApplication).where(MembershipApplication.id == app_id)
            application = db.exec(stmt).first()

            if not application or application.status != "pending":
                return None

            # Generate invite token
            from app_helpers.services.invite_helpers import create_invite_token
            invite_token_str = create_invite_token(
                created_by_user=admin_user_id,
                token_type="new_user",
                max_uses=1
            )

            # Update application status
            application.status = "approved"
            application.processed_at = datetime.utcnow()
            application.processed_by_user_id = admin_user_id
            application.invite_token = invite_token_str

            db.add(application)
            db.commit()

            # Get the InviteToken object for return (fresh query after commit)
            from models import InviteToken
            stmt_token = select(InviteToken).where(InviteToken.token == invite_token_str)
            invite_token_obj = db.exec(stmt_token).first()

            # Archive the approval decision
            MembershipApplicationService._append_to_archive(
                application.text_file_path,
                f"APPROVED by {admin_user_id} at {application.processed_at.isoformat()}\n"
                f"Invite token: {invite_token_str}\n"
            )

            return invite_token_obj

    @staticmethod
    def reject_application(app_id: str, admin_user_id: str, reason: str = None) -> bool:
        """
        Reject a membership application
        Updates both text archive and database
        """
        with Session(engine) as db:
            # Get application
            stmt = select(MembershipApplication).where(MembershipApplication.id == app_id)
            application = db.exec(stmt).first()

            if not application or application.status != "pending":
                return False

            # Update application status
            application.status = "rejected"
            application.processed_at = datetime.utcnow()
            application.processed_by_user_id = admin_user_id

            db.add(application)
            db.commit()

            # Archive the rejection decision
            rejection_note = f"REJECTED by {admin_user_id} at {application.processed_at.isoformat()}\n"
            if reason:
                rejection_note += f"Reason: {reason}\n"

            MembershipApplicationService._append_to_archive(
                application.text_file_path,
                rejection_note
            )

            return True

    @staticmethod
    def _write_to_archive(app_id: str, username: str, essay: str, contact_info: str, ip_address: str, timestamp: datetime) -> str:
        """Write application to text archive file following established format"""
        # Create archive directory if it doesn't exist
        archive_dir = Path("text_archives/membership_applications")
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{app_id}.txt"
        file_path = archive_dir / filename

        # Write application data
        content = f"""MEMBERSHIP APPLICATION
=====================

Application ID: {app_id}
Submitted: {timestamp.isoformat()}
IP Address: {ip_address or 'Unknown'}

USERNAME: {username}

ESSAY/MOTIVATION:
{essay}

CONTACT INFO: {contact_info or 'None provided'}

STATUS: pending
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(file_path)

    @staticmethod
    def _append_to_archive(file_path: str, content: str):
        """Append content to existing archive file"""
        if not file_path or not Path(file_path).exists():
            return

        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{content}")