"""
Email Management Service - Handles email encryption, verification, and recovery operations
"""
import os
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
import base64
from sqlmodel import Session, select
from models import User, InviteToken, SecurityLog, engine
from models_email import UserEmail, email_engine
import logging

logger = logging.getLogger(__name__)

class EmailManagementService:
    """Service for managing user email associations with encryption and verification"""
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for email storage"""
        key_env = os.getenv('EMAIL_ENCRYPTION_KEY')
        if key_env and key_env.strip():  # Check for non-empty key
            try:
                # Fernet keys are base64 encoded, return as bytes
                logger.debug("Using EMAIL_ENCRYPTION_KEY from environment")
                return key_env.strip().encode('utf-8')
            except Exception as e:
                logger.error(f"Invalid EMAIL_ENCRYPTION_KEY format: {e}")
                logger.error("Generate a new key with: python -c \"from cryptography.fernet import Fernet; print('EMAIL_ENCRYPTION_KEY=' + Fernet.generate_key().decode())\"")
                raise Exception("Invalid EMAIL_ENCRYPTION_KEY format. Please generate a new key.")
        
        # Generate new key if not configured - this should only happen in development
        logger.error("❌ CRITICAL: No EMAIL_ENCRYPTION_KEY found in environment!")
        logger.error("❌ This will cause data loss - emails encrypted with different keys cannot be decrypted!")
        logger.error("❌ Set EMAIL_ENCRYPTION_KEY in your .env file immediately!")
        
        key = Fernet.generate_key()
        logger.warning(f"🚨 TEMPORARY key generated: EMAIL_ENCRYPTION_KEY={key.decode()}")
        logger.warning("🚨 Add this to your .env file to prevent data loss!")
        return key
    
    def encrypt_email(self, email: str) -> str:
        """Encrypt email address for storage"""
        return self.fernet.encrypt(email.encode()).decode()
    
    def decrypt_email(self, encrypted_email: str) -> str:
        """Decrypt email address from storage"""
        return self.fernet.decrypt(encrypted_email.encode()).decode()
    
    def validate_email_format(self, email: str) -> bool:
        """Basic email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def generate_verification_token(self) -> str:
        """Generate unique verification token"""
        return uuid.uuid4().hex
    
    def add_user_email(self, user_id: str, email: str, ip_address: str = None, allow_pending: bool = False) -> tuple[bool, str]:
        """
        Add email to user account and send verification
        Args:
            user_id: User ID
            email: Email address to add
            ip_address: Client IP for logging
            allow_pending: Allow adding email when user already has one (for email changes)
        Returns: (success, message/error)
        """
        if not self.validate_email_format(email):
            self._log_security_event("email_add_invalid_format", user_id, ip_address, email)
            return False, "Invalid email format"
        
        # Check if user exists in main database
        with Session(engine) as main_session:
            user = main_session.get(User, user_id)
            if not user:
                return False, "User not found"
        
        with Session(email_engine) as email_session:
            # Check existing emails for this user
            existing_emails = email_session.exec(
                select(UserEmail).where(UserEmail.user_id == user_id)
            ).all()
            
            has_verified = any(email.email_verified for email in existing_emails)
            has_unverified = any(not email.email_verified for email in existing_emails)
            
            # Logic for first email (user has no emails)
            if not existing_emails:
                pass  # Continue to add first email
            
            # Logic for users with verified email wanting to change
            elif has_verified and not allow_pending:
                self._log_security_event("email_add_already_exists", user_id, ip_address, email)
                return False, "User already has a verified email address. Use 'Change Email' instead."
            
            # Logic for email changes - remove any existing unverified emails (keep verified ones)
            elif allow_pending and has_unverified:
                self._log_security_event("email_replace_unverified", user_id, ip_address, email)
                # Remove only unverified emails, keep verified ones
                for existing in existing_emails:
                    if not existing.email_verified:
                        email_session.delete(existing)
                email_session.commit()
            
            # For users with only unverified email, replace it
            elif has_unverified and not has_verified:
                self._log_security_event("email_replace_unverified", user_id, ip_address, email)
                # Remove the unverified email record
                for existing in existing_emails:
                    email_session.delete(existing)
                email_session.commit()
            
            # Check if email is already used by another user
            encrypted_email = self.encrypt_email(email.lower().strip())
            email_exists = email_session.exec(
                select(UserEmail).where(UserEmail.email_encrypted == encrypted_email)
            ).first()
            
            if email_exists:
                self._log_security_event("email_add_duplicate", user_id, ip_address, email)
                return False, "This email address is already associated with another account"
            
            # Create new email record
            verification_token = self.generate_verification_token()
            user_email = UserEmail(
                user_id=user_id,
                email_encrypted=encrypted_email,
                verification_token=verification_token
            )
            
            email_session.add(user_email)
            email_session.commit()
            
            # Log successful email addition
            self._log_security_event("email_added", user_id, ip_address, email)
            
            # Send verification email
            try:
                self.send_verification_email(email, user_id, verification_token)
                return True, "Verification email sent. Please check your inbox."
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
                return False, "Failed to send verification email. Please try again."
    
    def send_verification_email(self, email: str, user_id: str, verification_token: str):
        """Send email verification email"""
        if not self._is_email_enabled():
            raise Exception("Email authentication is disabled")
        
        # Create verification token in main database
        with Session(engine) as main_session:
            # Create invite token for email verification
            expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiration
            invite_token = InviteToken(
                token=verification_token,
                created_by_user="system",
                expires_at=expires_at,
                token_type="email_verification",
                used_by_user_id=user_id,  # Pre-associate with user
                max_uses=1
            )
            main_session.add(invite_token)
            main_session.commit()
        
        # Send email
        subject = "Verify Your Email - ThyWill"
        verification_url = f"{self._get_base_url()}/claim/{verification_token}"
        
        body = f"""
Hello,

Please verify your email address for your ThyWill account by clicking the link below:

{verification_url}

This link will expire in 1 hour for security.

If you didn't request this verification, you can safely ignore this email.

Blessings,
The ThyWill Team
        """.strip()
        
        self._send_email(email, subject, body)
    
    def verify_email_token(self, token: str) -> tuple[bool, str]:
        """
        Verify email token and mark email as verified
        The token parameter is the invite token, we need to find the corresponding email record
        Returns: (success, message)
        """
        # First get the invite token to find the user_id
        with Session(engine) as main_session:
            invite_token = main_session.get(InviteToken, token)
            if not invite_token or invite_token.token_type != "email_verification":
                return False, "Invalid verification token"
            
            user_id = invite_token.used_by_user_id
            if not user_id:
                return False, "Invalid verification token"
        
        # Now find and verify the email record for this user
        with Session(email_engine) as email_session:
            user_email = email_session.exec(
                select(UserEmail).where(
                    UserEmail.user_id == user_id,
                    UserEmail.email_verified == False
                )
            ).first()
            
            if not user_email:
                return False, "No unverified email found for this user"
            
            # Mark as verified
            user_email.email_verified = True
            user_email.verified_at = datetime.utcnow()
            user_email.verification_token = None  # Clear token
            
            # When verifying a new email, remove any old verified emails (for email changes)
            # This ensures only one verified email per user
            other_verified_emails = email_session.exec(
                select(UserEmail).where(
                    UserEmail.user_id == user_id,
                    UserEmail.email_verified == True,
                    UserEmail.id != user_email.id  # Don't delete the one we just verified
                )
            ).all()
            
            for old_email in other_verified_emails:
                self._log_security_event("email_replaced_on_verify", user_id, None, self.decrypt_email(old_email.email_encrypted))
                email_session.delete(old_email)
            
            email_session.commit()
            
            # Log email verification
            self._log_security_event("email_verified", user_email.user_id)
            
            return True, "Email verified successfully"
    
    def send_recovery_email(self, email: str, ip_address: str = None) -> bool:
        """
        Send recovery email if email exists and is verified
        Returns success status (always True to prevent email enumeration)
        """
        if not self._is_email_enabled():
            return True  # Don't reveal that email is disabled
        
        try:
            with Session(email_engine) as email_session:
                encrypted_email = self.encrypt_email(email.lower().strip())
                user_email = email_session.exec(
                    select(UserEmail).where(
                        UserEmail.email_encrypted == encrypted_email,
                        UserEmail.email_verified == True
                    )
                ).first()
                
                if user_email:
                    # Log recovery request
                    self._log_security_event("email_recovery_requested", user_email.user_id, ip_address, email)
                    
                    # Create recovery token in main database
                    recovery_token = self.generate_verification_token()
                    expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiration
                    
                    with Session(engine) as main_session:
                        invite_token = InviteToken(
                            token=recovery_token,
                            created_by_user="system",
                            expires_at=expires_at,
                            token_type="user_login",  # Use existing user_login type
                            used_by_user_id=user_email.user_id,  # Pre-associate with user
                            max_uses=1
                        )
                        main_session.add(invite_token)
                        main_session.commit()
                    
                    # Send recovery email
                    subject = "Account Recovery - ThyWill"
                    recovery_url = f"{self._get_base_url()}/claim/{recovery_token}"
                    
                    body = f"""
Hello,

You requested to recover access to your ThyWill account.

Click the link below to log in immediately:

{recovery_url}

This link will expire in 1 hour for security.

If you didn't request account recovery, you can safely ignore this email.

Blessings,
The ThyWill Team
                    """.strip()
                    
                    self._send_email(email, subject, body)
                else:
                    # Log attempted recovery for non-existent email (but don't indicate this to user)
                    self._log_security_event("email_recovery_nonexistent", "unknown", ip_address, email)
        
        except Exception as e:
            logger.error(f"Error in recovery email process: {e}")
        
        return True  # Always return True to prevent email enumeration
    
    def _is_email_enabled(self) -> bool:
        """Check if email authentication is enabled via feature flag"""
        return os.getenv('EMAIL_AUTH_ENABLED', 'false').lower() == 'true'
    
    def _get_base_url(self) -> str:
        """Get base URL for email links"""
        return os.getenv('BASE_URL', 'http://localhost:8000')
    
    def _send_email(self, to_email: str, subject: str, body: str):
        """Send email using configured SMTP settings"""
        smtp_host = os.getenv('SMTP_HOST', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '25'))
        smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('SMTP_FROM_EMAIL', 'admin@thywill.live')
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if smtp_use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls(context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
        
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
    
    def get_user_email(self, user_id: str) -> str | None:
        """Get decrypted email for user if exists and verified"""
        with Session(email_engine) as email_session:
            user_email = email_session.exec(
                select(UserEmail).where(
                    UserEmail.user_id == user_id,
                    UserEmail.email_verified == True
                )
            ).first()
            
            if user_email:
                return self.decrypt_email(user_email.email_encrypted)
            return None
    
    def get_user_email_status(self, user_id: str) -> dict:
        """Get user email information including verification status"""
        with Session(email_engine) as email_session:
            user_email = email_session.exec(
                select(UserEmail).where(UserEmail.user_id == user_id)
            ).first()
            
            if user_email:
                return {
                    'email': self.decrypt_email(user_email.email_encrypted),
                    'verified': user_email.email_verified,
                    'added_at': user_email.added_at,
                    'verified_at': user_email.verified_at
                }
            return None
    
    def remove_user_email(self, user_id: str, ip_address: str = None) -> bool:
        """Remove email association for user"""
        with Session(email_engine) as email_session:
            user_email = email_session.exec(
                select(UserEmail).where(UserEmail.user_id == user_id)
            ).first()
            
            if user_email:
                # Log email removal before deleting
                decrypted_email = self.decrypt_email(user_email.email_encrypted)
                self._log_security_event("email_removed", user_id, ip_address, decrypted_email)
                
                email_session.delete(user_email)
                email_session.commit()
                return True
            return False
    
    def _log_security_event(self, event_type: str, user_id: str, ip_address: str = None, email: str = None):
        """Log security events related to email operations"""
        try:
            with Session(engine) as main_session:
                # Create details string with relevant information
                details = f"event_type:{event_type}"
                if email:
                    # Only log the domain part of email to protect privacy
                    domain = email.split('@')[-1] if '@' in email else 'unknown'
                    details += f",email_domain:{domain}"
                
                security_log = SecurityLog(
                    user_id=user_id,
                    event_type=event_type,
                    ip_address=ip_address,
                    details=details
                )
                main_session.add(security_log)
                main_session.commit()
        except Exception as e:
            logger.error(f"Failed to log security event {event_type}: {e}")