# app.py ─ complete micro-MVP
import os, uuid, yaml
from datetime import datetime, timedelta, date
from typing import Optional
from dotenv import load_dotenv
import anthropic

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import engine, User, Prayer, InviteToken, Session as SessionModel, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
from sqlmodel import text

# Load environment variables
load_dotenv()

# ───────── Config ─────────
SESSION_DAYS = 14
TOKEN_EXP_H = 12          # invite links valid 12 h
MAX_AUTH_REQUESTS_PER_HOUR = 3  # Rate limit for auth requests
MAX_FAILED_ATTEMPTS = 5   # Max failed login attempts before temporary block
BLOCK_DURATION_MINUTES = 15  # How long to block after max failed attempts

# Multi-device authentication settings
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"
REQUIRE_APPROVAL_FOR_EXISTING_USERS = os.getenv("REQUIRE_APPROVAL_FOR_EXISTING_USERS", "true").lower() == "true"
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", "2"))

templates = Jinja2Templates(directory="templates")

app = FastAPI()

# Custom exception handler for 401 unauthorized errors
@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for 401 unauthorized errors to show user-friendly page"""
    reason = exc.detail if exc.detail else "no_session"
    return templates.TemplateResponse("unauthorized.html", {
        "request": request,
        "reason": reason,
        "return_url": request.url.path
    }, status_code=401)

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ───────── Import extracted helper functions for backward compatibility ─────────
# These imports maintain all existing function entry points in app.py namespace
from app_helpers.services.auth_helpers import (
    create_session, current_user, require_full_auth, is_admin,
    create_auth_request, approve_auth_request, get_pending_requests_for_approval,
    log_auth_action, log_security_event, check_rate_limit, 
    validate_session_security, cleanup_expired_requests
)
from app_helpers.services.prayer_helpers import (
    get_feed_counts, get_filtered_prayers_for_user, find_compatible_prayer_partner,
    get_religious_preference_stats, todays_prompt, generate_prayer
)
from app_helpers.services.invite_helpers import (
    get_invite_tree, get_user_descendants, get_user_invite_path,
    get_invite_stats, _build_user_tree_node, _collect_descendants, _calculate_max_depth
)
from app_helpers.utils.database_helpers import migrate_database

# ───────── Extracted functions now imported from helper modules ─────────
# Auth functions: create_session, current_user, require_full_auth, is_admin, etc.
# Prayer functions: get_feed_counts, get_filtered_prayers_for_user, etc.
# Invite functions: get_invite_tree, get_user_descendants, etc.
# Database functions: migrate_database


# ───────── Routes ─────────
@app.get("/", response_class=HTMLResponse)
def feed(request: Request, feed_type: str = "all", user_session: tuple = Depends(current_user)):
    user, session = user_session
    # Ensure feed_type has a valid default
    if not feed_type:
        feed_type = "all"
        
    with Session(engine) as s:
        prayers_with_authors = []
        
        # Base filter to exclude archived prayers for public feeds
        def exclude_archived():
            return ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'archived')
            )
        
        # Religious preference filtering
        def apply_religious_filter():
            if user.religious_preference == "christian":
                # Christians see: all prayers + christian-only prayers
                return Prayer.target_audience.in_(["all", "christians_only"])
            else:
                # All faiths (unspecified) users see only "all" prayers
                return Prayer.target_audience == "all"
        
        if feed_type == "new_unprayed":
            # New prayers and prayers that have never been prayed (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .having(func.count(PrayerMark.id) == 0)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "most_prayed":
            # Most prayed prayers (by total prayer count, exclude archived)
            stmt = (
                select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .order_by(func.count(PrayerMark.id).desc())
                .limit(50)
            )
        elif feed_type == "my_prayers":
            # Prayers the current user has marked as prayed (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerMark.user_id == user.id)
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
            )
        elif feed_type == "my_requests":
            # Prayer requests submitted by the current user (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_id == user.id)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "recent_activity":
            # Prayers with recent prayer marks (most recently prayed, exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
                .limit(50)
            )
        elif feed_type == "answered":
            # Answered prayers (public celebration feed)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerAttribute.attribute_name == 'answered')
                .where(apply_religious_filter())
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "archived":
            # Archived prayers (personal feed for prayer authors only)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_id == user.id)  # Only user's own prayers
                .where(PrayerAttribute.attribute_name == 'archived')
                .order_by(Prayer.created_at.desc())
            )
        else:  # "all" or default
            # All prayers (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .order_by(Prayer.created_at.desc())
            )
            
        results = s.exec(stmt).all()
        
        # Get all prayer marks for the current user
        user_marks_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).where(PrayerMark.user_id == user.id).group_by(PrayerMark.prayer_id)
        user_marks_results = s.exec(user_marks_stmt).all()
        user_mark_counts = {prayer_id: count for prayer_id, count in user_marks_results}
        
        # Get mark counts for all prayers (total times prayed)
        mark_counts_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).group_by(PrayerMark.prayer_id)
        mark_counts_results = s.exec(mark_counts_stmt).all()
        mark_counts = {prayer_id: count for prayer_id, count in mark_counts_results}
        
        # Get distinct user counts for all prayers (how many people prayed)
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.user_id))).group_by(PrayerMark.prayer_id)
        distinct_user_counts_results = s.exec(distinct_user_counts_stmt).all()
        distinct_user_counts = {prayer_id: count for prayer_id, count in distinct_user_counts_results}
        
        # Create a list of prayers with author names and mark data
        for result in results:
            if len(result) == 3:  # most_prayed query includes mark_count
                prayer, author_name, _ = result
            else:
                prayer, author_name = result
                
            prayer_dict = {
                'id': prayer.id,
                'author_id': prayer.author_id,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at,
                'flagged': prayer.flagged,
                'target_audience': prayer.target_audience,
                'author_name': author_name,
                'marked_by_user': user_mark_counts.get(prayer.id, 0),
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0),
                'is_archived': prayer.is_archived(s),
                'is_answered': prayer.is_answered(s),
                'answer_date': prayer.answer_date(s),
                'answer_testimony': prayer.answer_testimony(s)
            }
            prayers_with_authors.append(prayer_dict)
    
    # Get feed counts
    feed_counts = get_feed_counts(user.id)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), 
         "me": user, "session": session, "current_feed": feed_type, "feed_counts": feed_counts}
    )

@app.post("/prayers")
def submit_prayer(text: str = Form(...),
                  tag: Optional[str] = Form(None),
                  target_audience: str = Form("all"),
                  user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to submit prayers")
    
    # Validate target audience
    valid_audiences = ["all", "christians_only"]
    if target_audience not in valid_audiences:
        target_audience = "all"
    
    # Generate a proper prayer from the user's prompt
    generated_prayer = generate_prayer(text)
    
    with Session(engine) as s:
        prayer = Prayer(
            author_id=user.id, 
            text=text[:500], 
            generated_prayer=generated_prayer,
            project_tag=tag,
            target_audience=target_audience,
        )
        s.add(prayer)
        s.commit()
        
        # Try to find a compatible prayer partner immediately
        compatible_user = find_compatible_prayer_partner(prayer, s)
        if compatible_user:
            # Assign prayer to compatible user
            mark = PrayerMark(user_id=compatible_user.id, prayer_id=prayer.id)
            s.add(mark)
            s.commit()
            print(f"Prayer {prayer.id} assigned to compatible user {compatible_user.id}")
    
    return RedirectResponse("/", 303)

@app.post("/flag/{pid}")
def flag_prayer(pid: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        p = s.get(Prayer, pid)
        if not p:
            raise HTTPException(404)
        
        # Only allow unflagging if user is admin
        if p.flagged and not is_admin(user):
            raise HTTPException(403, "Only admins can unflag content")
            
        p.flagged = not p.flagged
        s.add(p); s.commit()
        
        # If this is an HTMX request, return appropriate content
        if request.headers.get("HX-Request"):
            # Check if this is coming from admin panel by looking at the referer
            referer = request.headers.get("referer", "")
            is_admin_panel = "/admin" in referer
            
            if p.flagged:
                # Return shielded version when flagging
                return HTMLResponse(templates.get_template("flagged_prayer.html").render(
                    prayer=p, is_admin=is_admin(user)
                ))
            else:
                # When unflagging (admin only)
                if is_admin_panel:
                    # If unflagging from admin panel, just remove the item
                    return HTMLResponse("")
                else:
                    # If unflagging from main feed, restore the full prayer view
                    # Get author name and prayer marks
                    author = s.get(User, p.author_id)
                    author_name = author.display_name if author else "Unknown"
                    
                    # Get mark counts
                    mark_count_stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == p.id)
                    total_mark_count = s.exec(mark_count_stmt).first() or 0
                    
                    distinct_user_count_stmt = select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == p.id)
                    distinct_user_count = s.exec(distinct_user_count_stmt).first() or 0
                    
                    user_mark_count_stmt = select(func.count(PrayerMark.id)).where(
                        PrayerMark.prayer_id == p.id,
                        PrayerMark.user_id == user.id
                    )
                    user_mark_count = s.exec(user_mark_count_stmt).first() or 0
                    
                    # Build prayer stats display
                    prayer_stats = ""
                    if total_mark_count > 0:
                        if distinct_user_count == 1:
                            if total_mark_count == 1:
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this once</a>'
                            else:
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                        else:
                            prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
                    
                    user_mark_text = ""
                    if user_mark_count > 0:
                        if user_mark_count == 1:
                            user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this</span>'
                        else:
                            user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this {user_mark_count} times</span>'
                    
                    return HTMLResponse(templates.get_template("unflagged_prayer.html").render(
                        prayer=p, user=user, author_name=author_name, 
                        prayer_stats=prayer_stats, user_mark_text=user_mark_text
                    ))
            
    # For non-HTMX requests, redirect appropriately
    if p.flagged:
        return RedirectResponse("/", 303)  # Back to main feed when flagging
    else:
        return RedirectResponse("/admin", 303)  # Back to admin when unflagging

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    cleanup_expired_requests()  # Clean up old requests
    
    with Session(engine) as s:
        # Join Prayer and User tables to get author display names for flagged prayers
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .where(Prayer.flagged == True)
        )
        results = s.exec(stmt).all()
        
        # Create a list of flagged prayers with author names
        flagged_with_authors = []
        for prayer, author_name in results:
            prayer_dict = {
                'id': prayer.id,
                'author_id': prayer.author_id,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at,
                'flagged': prayer.flagged,
                'author_name': author_name
            }
            flagged_with_authors.append(prayer_dict)
        
        # Get authentication requests for admin review
        auth_requests_stmt = (
            select(AuthenticationRequest, User.display_name)
            .join(User, AuthenticationRequest.user_id == User.id)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        auth_results = s.exec(auth_requests_stmt).all()
        auth_requests_with_info = []
        
        for auth_req, requester_name in auth_results:
            # Get current approval count
            approval_count = s.exec(
                select(func.count(AuthApproval.id))
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).first() or 0
            
            # Get approvers
            approvers = s.exec(
                select(AuthApproval, User.display_name)
                .join(User, AuthApproval.approver_user_id == User.id)
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).all()
            
            approver_info = []
            for approval, approver_name in approvers:
                approver_info.append({
                    'name': approver_name,
                    'is_admin': approval.approver_user_id == "admin",
                    'approved_at': approval.created_at
                })
            
            auth_requests_with_info.append({
                'request': auth_req,
                'requester_name': requester_name,
                'approval_count': approval_count,
                'approvers': approver_info
            })
    
    return templates.TemplateResponse(
        "admin.html", {
            "request": request, 
            "flagged": flagged_with_authors, 
            "auth_requests": auth_requests_with_info,
            "me": user,
            "session": session
        }
    )

# ───────── Invite-claim flow ─────────
@app.get("/claim/{token}", response_class=HTMLResponse)
def claim_get(token: str, request: Request):
    return templates.TemplateResponse("claim.html", {"request": request, "token": token})

@app.post("/claim/{token}")
def claim_post(token: str, display_name: str = Form(...), request: Request = None):
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        if not inv or inv.used or inv.expires_at < datetime.utcnow():
            raise HTTPException(400, "Invite expired")

        # Check if username already exists
        existing_user = s.exec(
            select(User).where(User.display_name == display_name)
        ).first()
        
        if existing_user:
            # Username exists - check if multi-device auth is enabled and required
            if not MULTI_DEVICE_AUTH_ENABLED or not REQUIRE_APPROVAL_FOR_EXISTING_USERS:
                # Allow direct login without approval
                sid = create_session(existing_user.id)
                resp = RedirectResponse("/", 303)
                resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
                return resp
            
            # Multi-device auth required - create authentication request
            device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
            ip_address = request.client.host if request else "Unknown"
            
            # Check for recent requests
            recent_request = s.exec(
                select(AuthenticationRequest)
                .where(AuthenticationRequest.user_id == existing_user.id)
                .where(AuthenticationRequest.ip_address == ip_address)
                .where(AuthenticationRequest.status == "pending")
                .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
            ).first()
            
            if recent_request:
                raise HTTPException(429, "Authentication request already pending. Please wait.")
            
            # Create auth request
            request_id = create_auth_request(existing_user.id, device_info, ip_address)
            
            # Create half-authenticated session
            sid = create_session(
                user_id=existing_user.id,
                auth_request_id=request_id,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=False
            )
            
            # Don't mark invite as used for existing users
            resp = RedirectResponse("/auth/status", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp
        
        else:
            # New user - create account normally
            uid = "admin" if s.exec(select(User)).first() is None else uuid.uuid4().hex
            user = User(
                id=uid, 
                display_name=display_name[:40],
                invited_by_user_id=inv.created_by_user if inv.created_by_user != "system" else None,
                invite_token_used=token
            )
            inv.used = True
            inv.used_by_user_id = uid
            s.add_all([user, inv]); s.commit()

            sid = create_session(uid)
            resp = RedirectResponse("/", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp


# ───────── Startup: seed first invite ─────────
@app.on_event("startup")
def startup():
    # Run database migration first
    migrate_database()
    
    # Then seed invite
    with Session(engine) as s:
        if not s.exec(select(InviteToken)).first():
            token = uuid.uuid4().hex
            s.add(InviteToken(
                token=token,
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)))
            s.commit()
            print("\n==== First-run invite token (admin):", token, "====\n")


@app.post("/invites", response_class=HTMLResponse)
def new_invite(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to create invites")
    token = uuid.uuid4().hex
    with Session(engine) as db:
        db.add(InviteToken(
            token=token,
            created_by_user=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)
        ))
        db.commit()

    url = request.url_for("claim_get", token=token)  # absolute link
    # Return a modal-style overlay that doesn't shift layout
    return HTMLResponse(templates.get_template("invite_modal.html").render(url=url))

@app.post("/mark/{prayer_id}")
def mark_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to mark prayers")
    with Session(engine) as s:
        # Check if prayer exists
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Add a new prayer mark
        mark = PrayerMark(user_id=user.id, prayer_id=prayer_id)
        s.add(mark)
        s.commit()
        
        # If this is an HTMX request, return just the updated prayer mark section
        if request.headers.get("HX-Request"):
            # Get updated mark count for all users (total times)
            mark_count_stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer_id)
            total_mark_count = s.exec(mark_count_stmt).first()
            
            # Get updated distinct user count (how many people)
            distinct_user_count_stmt = select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == prayer_id)
            distinct_user_count = s.exec(distinct_user_count_stmt).first()
            
            # Get updated mark count for current user
            user_mark_count_stmt = select(func.count(PrayerMark.id)).where(
                PrayerMark.prayer_id == prayer_id,
                PrayerMark.user_id == user.id
            )
            user_mark_count = s.exec(user_mark_count_stmt).first()
            
            # Build the prayer stats display
            prayer_stats = ""
            if total_mark_count > 0:
                if distinct_user_count == 1:
                    if total_mark_count == 1:
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this once</a>'
                    else:
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                else:
                    prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
            
            # Return the updated prayer mark section HTML
            user_mark_text = ""
            if user_mark_count > 0:
                if user_mark_count == 1:
                    user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this</span>'
                else:
                    user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this {user_mark_count} times</span>'
            
            return HTMLResponse(templates.get_template("prayer_marks_section.html").render(
                prayer_id=prayer_id, prayer_stats=prayer_stats, user_mark_text=user_mark_text
            ))
    
    # For non-HTMX requests, redirect back to the specific prayer
    return RedirectResponse(f"/#prayer-{prayer_id}", 303)

@app.post("/prayer/{prayer_id}/archive")
def archive_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can archive prayers
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can archive this prayer")
        
        # Set archived attribute
        prayer.set_attribute('archived', 'true', user.id, s)
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return success message with gentle transition
            return HTMLResponse(f'''
                <div class="prayer-archived bg-amber-50 dark:bg-amber-900/20 p-3 rounded border border-amber-200 dark:border-amber-700 text-center">
                    <span class="text-amber-700 dark:text-amber-300 text-sm font-medium">
                        📁 Prayer archived successfully
                    </span>
                </div>
            ''')
    
    return RedirectResponse("/", 303)

@app.post("/prayer/{prayer_id}/restore")
def restore_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can restore prayers
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can restore this prayer")
        
        # Remove archived attribute
        prayer.remove_attribute('archived', s, user.id)
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return success message
            return HTMLResponse(f'''
                <div class="prayer-restored bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-700 text-center">
                    <span class="text-green-700 dark:text-green-300 text-sm font-medium">
                        ✅ Prayer restored successfully
                    </span>
                </div>
            ''')
    
    return RedirectResponse("/", 303)

@app.post("/prayer/{prayer_id}/answered")
def mark_prayer_answered(prayer_id: str, request: Request, 
                        testimony: Optional[str] = Form(None),
                        user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can mark prayers as answered
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can mark this prayer as answered")
        
        # Set answered attribute with current date
        from datetime import datetime
        answer_date = datetime.utcnow().isoformat()
        prayer.set_attribute('answered', 'true', user.id, s)
        prayer.set_attribute('answer_date', answer_date, user.id, s)
        
        # Add testimony if provided
        if testimony and testimony.strip():
            prayer.set_attribute('answer_testimony', testimony.strip(), user.id, s)
        
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return celebration message
            return HTMLResponse(f'''
                <div class="prayer-answered bg-green-100 dark:bg-green-900/30 p-4 rounded-lg border border-green-300 dark:border-green-600 text-center">
                    <div class="flex items-center justify-center gap-2 mb-2">
                        <span class="text-2xl">🎉</span>
                        <span class="text-green-800 dark:text-green-200 font-semibold">Prayer Answered!</span>
                    </div>
                    <p class="text-green-700 dark:text-green-300 text-sm">
                        Praise the Lord! This prayer has been moved to the celebration feed.
                    </p>
                </div>
            ''')
    
    return RedirectResponse("/", 303)

@app.get("/answered", response_class=HTMLResponse)
def answered_celebration(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    
    with Session(engine) as s:
        # Get recent answered prayers (last 10)
        recent_stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
            .limit(10)
        )
        recent_results = s.exec(recent_stmt).all()
        
        # Get prayer marks for answered prayers
        answered_prayer_ids = [prayer.id for prayer, _ in recent_results]
        mark_counts_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).where(
            PrayerMark.prayer_id.in_(answered_prayer_ids)
        ).group_by(PrayerMark.prayer_id)
        mark_counts_results = s.exec(mark_counts_stmt).all()
        mark_counts = {prayer_id: count for prayer_id, count in mark_counts_results}
        
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.user_id))).where(
            PrayerMark.prayer_id.in_(answered_prayer_ids)
        ).group_by(PrayerMark.prayer_id)
        distinct_user_counts_results = s.exec(distinct_user_counts_stmt).all()
        distinct_user_counts = {prayer_id: count for prayer_id, count in distinct_user_counts_results}
        
        # Build recent answered prayers list
        recent_answered = []
        for prayer, author_name in recent_results:
            prayer_dict = {
                'id': prayer.id,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'created_at': prayer.created_at,
                'author_name': author_name,
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0),
                'answer_date': prayer.answer_date(s),
                'answer_testimony': prayer.answer_testimony(s)
            }
            recent_answered.append(prayer_dict)
        
        # Calculate statistics
        total_answered = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).first()
        
        total_testimonies = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answer_testimony')
        ).first()
        
        # Recent answered this month
        from datetime import datetime, timedelta
        month_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .where(PrayerAttribute.created_at >= month_ago)
        ).first()
        
        # Community prayer statistics
        community_prayers = s.exec(select(func.count(PrayerMark.id))).first()
        total_prayers = s.exec(select(func.count(Prayer.id)).where(Prayer.flagged == False)).first()
        answered_percentage = round((total_answered / total_prayers * 100)) if total_prayers > 0 else 0
        
        avg_prayer_marks = round(community_prayers / total_prayers) if total_prayers > 0 else 0
    
    return templates.TemplateResponse(
        "answered_celebration.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "recent_answered": recent_answered,
            "total_answered": total_answered,
            "total_testimonies": total_testimonies,
            "recent_count": recent_count,
            "community_prayers": community_prayers,
            "answered_percentage": answered_percentage,
            "avg_prayer_marks": avg_prayer_marks
        }
    )

@app.get("/prayer/{prayer_id}/marks", response_class=HTMLResponse)
def prayer_marks(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get the prayer
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Get all marks for this prayer with user info
        stmt = (
            select(PrayerMark, User.display_name)
            .join(User, PrayerMark.user_id == User.id)
            .where(PrayerMark.prayer_id == prayer_id)
            .order_by(PrayerMark.created_at.desc())
        )
        marks_results = s.exec(stmt).all()
        
        marks_with_users = []
        for mark, user_name in marks_results:
            marks_with_users.append({
                'user_name': user_name,
                'user_id': mark.user_id,
                'created_at': mark.created_at,
                'is_me': mark.user_id == user.id
            })
        
        # Calculate statistics
        total_marks = len(marks_with_users)
        distinct_users = len(set(mark['user_name'] for mark in marks_with_users))
    
    return templates.TemplateResponse(
        "prayer_marks.html",
        {"request": request, "prayer": prayer, "marks": marks_with_users, "me": user, 
         "session": session, "total_marks": total_marks, "distinct_users": distinct_users}
    )

@app.get("/activity", response_class=HTMLResponse)
def recent_activity(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get recent prayer marks with prayer and user info
        stmt = (
            select(PrayerMark, Prayer, User.display_name.label('marker_name'), User.display_name.label('author_name'))
            .join(Prayer, PrayerMark.prayer_id == Prayer.id)
            .join(User, PrayerMark.user_id == User.id)
            .join(User, Prayer.author_id == User.id)
            .where(Prayer.flagged == False)
            .order_by(PrayerMark.created_at.desc())
            .limit(100)
        )
        
        # This query is complex, let's do it in steps
        recent_marks_stmt = (
            select(PrayerMark)
            .join(Prayer, PrayerMark.prayer_id == Prayer.id)
            .where(Prayer.flagged == False)
            .order_by(PrayerMark.created_at.desc())
            .limit(100)
        )
        recent_marks = s.exec(recent_marks_stmt).all()
        
        activity_items = []
        for mark in recent_marks:
            # Get prayer info
            prayer = s.get(Prayer, mark.prayer_id)
            # Get marker name
            marker = s.get(User, mark.user_id)
            # Get author name
            author = s.get(User, prayer.author_id)
            
            activity_items.append({
                'mark': mark,
                'prayer': prayer,
                'marker_name': marker.display_name,
                'author_name': author.display_name,
                'is_my_mark': mark.user_id == user.id,
                'is_my_prayer': prayer.author_id == user.id
            })
    
    return templates.TemplateResponse(
        "activity.html",
        {"request": request, "activity_items": activity_items, "me": user, "session": session}
    )

@app.get("/profile", response_class=HTMLResponse)
def my_profile(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    return user_profile(request, user.id, user_session)

@app.get("/user/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: str, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.id
        
        # Get prayer statistics
        stats = {}
        
        # Total prayers authored
        stats['prayers_authored'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.author_id == user_id)
            .where(Prayer.flagged == False)
        ).first() or 0
        
        # Total prayers marked (how many times they've prayed)
        stats['prayers_marked'] = s.exec(
            select(func.count(PrayerMark.id))
            .where(PrayerMark.user_id == user_id)
        ).first() or 0
        
        # Distinct prayers marked (unique prayers they've prayed)
        stats['distinct_prayers_marked'] = s.exec(
            select(func.count(func.distinct(PrayerMark.prayer_id)))
            .where(PrayerMark.user_id == user_id)
        ).first() or 0
        
        # Recent prayer requests (last 5)
        recent_requests_stmt = (
            select(Prayer)
            .where(Prayer.author_id == user_id)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
            .limit(5)
        )
        recent_requests = s.exec(recent_requests_stmt).all()
        
        # Recent prayers marked (last 5 unique prayers)
        recent_marks_stmt = (
            select(Prayer, func.max(PrayerMark.created_at).label('last_marked'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .join(User, Prayer.author_id == User.id)
            .where(PrayerMark.user_id == user_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .limit(5)
        )
        recent_marks_results = s.exec(recent_marks_stmt).all()
        recent_marked_prayers = []
        for prayer, last_marked in recent_marks_results:
            # Get author name
            author = s.get(User, prayer.author_id)
            recent_marked_prayers.append({
                'prayer': prayer,
                'author_name': author.display_name if author else "Unknown",
                'last_marked': last_marked
            })
        
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request, 
                "profile_user": profile_user, 
                "me": user,
                "session": session, 
                "is_own_profile": is_own_profile,
                "stats": stats,
                "recent_requests": recent_requests,
                "recent_marked_prayers": recent_marked_prayers
            }
        )

@app.get("/users", response_class=HTMLResponse)
def users_list(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get all users with their statistics
        users_stmt = select(User).order_by(User.created_at.desc())
        all_users = s.exec(users_stmt).all()
        
        users_with_stats = []
        for profile_user in all_users:
            # Get statistics for each user
            prayers_authored = s.exec(
                select(func.count(Prayer.id))
                .where(Prayer.author_id == profile_user.id)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.user_id == profile_user.id)
            ).first() or 0
            
            distinct_prayers_marked = s.exec(
                select(func.count(func.distinct(PrayerMark.prayer_id)))
                .where(PrayerMark.user_id == profile_user.id)
            ).first() or 0
            
            # Get last activity
            last_activity = None
            last_prayer_mark = s.exec(
                select(PrayerMark.created_at)
                .where(PrayerMark.user_id == profile_user.id)
                .order_by(PrayerMark.created_at.desc())
                .limit(1)
            ).first()
            
            last_prayer_request = s.exec(
                select(Prayer.created_at)
                .where(Prayer.author_id == profile_user.id)
                .where(Prayer.flagged == False)
                .order_by(Prayer.created_at.desc())
                .limit(1)
            ).first()
            
            if last_prayer_mark and last_prayer_request:
                last_activity = max(last_prayer_mark, last_prayer_request)
            elif last_prayer_mark:
                last_activity = last_prayer_mark
            elif last_prayer_request:
                last_activity = last_prayer_request
            
            users_with_stats.append({
                'user': profile_user,
                'prayers_authored': prayers_authored,
                'prayers_marked': prayers_marked,
                'distinct_prayers_marked': distinct_prayers_marked,
                'last_activity': last_activity,
                'is_me': profile_user.id == user.id
            })
        
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users_with_stats, "me": user, "session": session}
        )

@app.get("/menu", response_class=HTMLResponse)
def menu(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "me": user, "session": session}
    )

@app.get("/invite-tree", response_class=HTMLResponse)
def invite_tree(request: Request, user_session: tuple = Depends(current_user)):
    """Display the complete invite tree for all users to see"""
    user, session = user_session
    
    # Get the complete tree data
    tree_data = get_invite_tree()
    
    # Get invite statistics
    stats = get_invite_stats()
    
    # Get current user's invite path
    user_path = get_user_invite_path(user.id)
    
    return templates.TemplateResponse(
        "invite_tree.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "tree_data": tree_data,
            "stats": stats,
            "user_path": user_path
        }
    )

# ───────── Authentication request routes ─────────
@app.post("/auth/request")
def create_authentication_request(display_name: str = Form(...), request: Request = None):
    """Create an authentication request for an existing username"""
    if not MULTI_DEVICE_AUTH_ENABLED:
        raise HTTPException(404, "Multi-device authentication is disabled")
    
    cleanup_expired_requests()  # Clean up old requests
    
    device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
    ip_address = request.client.host if request else "Unknown"
    
    with Session(engine) as db:
        # Check if user exists
        existing_user = db.exec(
            select(User).where(User.display_name == display_name)
        ).first()
        
        if not existing_user:
            raise HTTPException(400, "Username not found. Please use an invite link to create a new account.")
        
        # Security: Check rate limits
        if not check_rate_limit(existing_user.id, ip_address):
            raise HTTPException(429, "Too many authentication requests. Please try again later.")
        
        # Check for existing pending request from same IP/device in last hour
        recent_request = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == existing_user.id)
            .where(AuthenticationRequest.ip_address == ip_address)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
        ).first()
        
        if recent_request:
            raise HTTPException(429, "Authentication request already pending for this device.")
        
        # Create the authentication request
        request_id = create_auth_request(existing_user.id, device_info, ip_address)
        
        # Create a half-authenticated session
        sid = create_session(
            user_id=existing_user.id,
            auth_request_id=request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=False
        )
        
        resp = RedirectResponse("/auth/status", 303)
        resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
        return resp

@app.get("/auth/status", response_class=HTMLResponse)
def auth_status(request: Request, user_session: tuple = Depends(current_user)):
    """Show authentication status for half-authenticated users"""
    user, session = user_session
    
    if session.is_fully_authenticated:
        return RedirectResponse("/", 303)
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, session.auth_request_id)
        if not auth_req:
            raise HTTPException(404, "Authentication request not found")
        
        # Get approval count and approvers
        approvals = db.exec(
            select(AuthApproval, User.display_name)
            .join(User, AuthApproval.approver_user_id == User.id)
            .where(AuthApproval.auth_request_id == auth_req.id)
        ).all()
        
        approval_info = []
        for approval, approver_name in approvals:
            approval_info.append({
                'approver_name': approver_name,
                'approved_at': approval.created_at,
                'is_admin': approval.approver_user_id == "admin",
                'is_self': approval.approver_user_id == user.id
            })
        
        # Check if approved
        if auth_req.status == "approved":
            # Upgrade session to full authentication
            session.is_fully_authenticated = True
            db.add(session)
            db.commit()
            return RedirectResponse("/", 303)
        
        context = {
            "request": request,
            "user": user,
            "auth_request": auth_req,
            "approvals": approval_info,
            "approval_count": len(approval_info),
            "needs_approvals": PEER_APPROVAL_COUNT - len(approval_info) if len(approval_info) < PEER_APPROVAL_COUNT else 0,
            "peer_approval_count": PEER_APPROVAL_COUNT
        }
        
        return templates.TemplateResponse("auth_pending.html", context)

@app.get("/auth/pending", response_class=HTMLResponse)
def pending_requests(request: Request, user_session: tuple = Depends(current_user)):
    """Show pending authentication requests for approval"""
    user, session = user_session
    cleanup_expired_requests()
    
    # Only fully authenticated users can approve
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    pending_requests = get_pending_requests_for_approval(user.id)
    
    return templates.TemplateResponse(
        "auth_requests.html",
        {
            "request": request, 
            "pending_requests": pending_requests, 
            "me": user, 
            "session": session,
            "peer_approval_count": PEER_APPROVAL_COUNT
        }
    )

@app.post("/auth/approve/{request_id}")
def approve_request(request_id: str, user_session: tuple = Depends(current_user)):
    """Approve an authentication request"""
    user, session = user_session
    
    # Only fully authenticated users can approve
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    success = approve_auth_request(request_id, user.id)
    if not success:
        raise HTTPException(400, "Unable to approve request")
    
    return RedirectResponse("/auth/pending", 303)

@app.post("/auth/reject/{request_id}")
def reject_request(request_id: str, user_session: tuple = Depends(current_user)):
    """Reject an authentication request"""
    user, session = user_session
    
    # Only fully authenticated users can reject, and only admins for now
    if not session.is_fully_authenticated or not is_admin(user):
        raise HTTPException(403, "Admin authentication required")
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, request_id)
        if not auth_req or auth_req.status != "pending":
            raise HTTPException(400, "Request not found or already processed")
        
        auth_req.status = "rejected"
        auth_req.approved_by_user_id = user.id
        auth_req.approved_at = datetime.utcnow()
        
        # Log the rejection
        log_auth_action(
            auth_request_id=request_id,
            action="rejected",
            actor_user_id=user.id,
            actor_type="admin",
            details="Request rejected by admin"
        )
        
        db.commit()
    
    return RedirectResponse("/auth/pending", 303)

@app.get("/auth/my-requests", response_class=HTMLResponse)
def my_auth_requests(request: Request, user_session: tuple = Depends(current_user)):
    """Show user's own authentication requests for self-approval"""
    user, session = user_session
    cleanup_expired_requests()
    
    with Session(engine) as db:
        # Get all authentication requests for this user
        my_requests_stmt = (
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == user.id)
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        my_requests = db.exec(my_requests_stmt).all()
        requests_with_info = []
        
        for auth_req in my_requests:
            # Get approvals for this request
            approvals = db.exec(
                select(AuthApproval, User.display_name)
                .join(User, AuthApproval.approver_user_id == User.id)
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).all()
            
            approval_info = []
            for approval, approver_name in approvals:
                approval_info.append({
                    'approver_name': approver_name,
                    'approved_at': approval.created_at,
                    'is_admin': approval.approver_user_id == "admin",
                    'is_self': approval.approver_user_id == user.id
                })
            
            can_self_approve = (
                auth_req.status == "pending" and 
                session.is_fully_authenticated and
                not any(a['is_self'] for a in approval_info)
            )
            
            requests_with_info.append({
                'request': auth_req,
                'approvals': approval_info,
                'approval_count': len(approval_info),
                'can_self_approve': can_self_approve,
                'is_current_session': auth_req.id == session.auth_request_id
            })
    
    return templates.TemplateResponse(
        "my_auth_requests.html",
        {"request": request, "my_requests": requests_with_info, "me": user, "session": session, "peer_approval_count": PEER_APPROVAL_COUNT}
    )

@app.get("/admin/auth-audit", response_class=HTMLResponse)
def auth_audit_log(request: Request, user_session: tuple = Depends(current_user)):
    """View authentication audit log (admin only)"""
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as db:
        # Get audit log entries with user info
        audit_stmt = (
            select(AuthAuditLog, User.display_name.label('actor_name'), User.display_name.label('requester_name'))
            .outerjoin(User, AuthAuditLog.actor_user_id == User.id)
            .join(AuthenticationRequest, AuthAuditLog.auth_request_id == AuthenticationRequest.id)
            .join(User, AuthenticationRequest.user_id == User.id)
            .order_by(AuthAuditLog.created_at.desc())
            .limit(100)
        )
        
        # This is complex, let's do it step by step
        audit_entries = db.exec(
            select(AuthAuditLog)
            .order_by(AuthAuditLog.created_at.desc())
            .limit(100)
        ).all()
        
        audit_with_info = []
        for entry in audit_entries:
            # Get actor info
            actor_name = "System"
            if entry.actor_user_id:
                actor = db.get(User, entry.actor_user_id)
                actor_name = actor.display_name if actor else "Unknown"
            
            # Get requester info
            auth_req = db.get(AuthenticationRequest, entry.auth_request_id)
            requester_name = "Unknown"
            if auth_req:
                requester = db.get(User, auth_req.user_id)
                requester_name = requester.display_name if requester else "Unknown"
            
            audit_with_info.append({
                'entry': entry,
                'actor_name': actor_name,
                'requester_name': requester_name,
                'auth_request': auth_req
            })
    
    return templates.TemplateResponse(
        "auth_audit.html",
        {"request": request, "audit_entries": audit_with_info, "me": user, "session": session}
    )

@app.post("/admin/bulk-approve")
def bulk_approve_requests(request: Request, user_session: tuple = Depends(current_user)):
    """Bulk approve multiple authentication requests (admin only)"""
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    # This would need form data with request IDs
    # For now, let's approve all pending requests
    approved_count = 0
    with Session(engine) as db:
        pending_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
        ).all()
        
        for auth_req in pending_requests:
            # Approve each request
            auth_req.status = "approved"
            auth_req.approved_by_user_id = user.id
            auth_req.approved_at = datetime.utcnow()
            approved_count += 1
            
            # Log the bulk approval
            log_auth_action(
                auth_request_id=auth_req.id,
                action="approved",
                actor_user_id=user.id,
                actor_type="admin",
                details="Request approved via bulk admin action"
            )
        
        db.commit()
    
    return RedirectResponse(f"/admin?message=Approved {approved_count} requests", 303)

# ───────── Religious Preference Management API ─────────
@app.get("/profile/preferences")
async def get_user_preferences(request: Request, user_session: tuple = Depends(current_user)):
    """Display user religious preference settings"""
    user, session = user_session
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        return templates.TemplateResponse("preferences.html", {
            "request": request,
            "user": db_user,
            "me": user,
            "session": session
        })

@app.post("/profile/preferences")
async def update_religious_preferences(
    request: Request,
    religious_preference: str = Form(...),
    prayer_style: str = Form(None),
    user_session: tuple = Depends(current_user)
):
    """Update user's religious preferences"""
    user, session = user_session
    
    # Validate religious preference
    valid_preferences = ["christian", "unspecified"]
    if religious_preference not in valid_preferences:
        raise HTTPException(400, "Invalid religious preference")
    
    # Validate prayer style for Christians
    valid_prayer_styles = ["in_jesus_name", "interfaith", None, ""]
    if prayer_style and prayer_style not in valid_prayer_styles:
        raise HTTPException(400, "Invalid prayer style")
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        old_preference = db_user.religious_preference
        old_style = db_user.prayer_style
        
        db_user.religious_preference = religious_preference
        
        # Only set prayer style for Christian users
        if religious_preference == "christian":
            db_user.prayer_style = prayer_style if prayer_style else None
        else:
            db_user.prayer_style = None
        
        db.add(db_user)
        db.commit()
        
        # Log the preference change for analytics
        print(f"User {user.id} changed preference: {old_preference} -> {religious_preference}, style: {old_style} -> {db_user.prayer_style}")
    
    return RedirectResponse("/profile", status_code=303)

@app.post("/logout")
async def logout(request: Request, user_session: tuple = Depends(current_user)):
    """Log out the current user by clearing their session"""
    user, session = user_session
    
    # Get client info for logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Delete the session from database
    with Session(engine) as db:
        db.delete(session)
        db.commit()
    
    # Log the logout event
    log_security_event(
        event_type="logout",
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details=f"User {user.display_name} logged out"
    )
    
    # Clear the session cookie and redirect to logged-out confirmation page
    response = RedirectResponse("/logged-out", status_code=303)
    response.delete_cookie("sid", path="/", domain=None)
    return response

@app.get("/logged-out", response_class=HTMLResponse)
async def logged_out_page(request: Request):
    """Show logged-out confirmation page - no authentication required"""
    # Explicitly ensure no user data is passed to template
    return templates.TemplateResponse("logged_out.html", {
        "request": request,
        "me": None  # Explicitly set user to None
    })

@app.get("/api/religious-stats")
async def get_religious_stats(request: Request, user_session: tuple = Depends(current_user)):
    """Get religious preference statistics (admin only)"""
    user, session = user_session
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats
