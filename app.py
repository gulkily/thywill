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

from models import engine, User, Prayer, InviteToken, Session as SessionModel, PrayerMark

# Load environment variables
load_dotenv()

# ───────── Config ─────────
SESSION_DAYS = 14
TOKEN_EXP_H = 12          # invite links valid 12 h
templates = Jinja2Templates(directory="templates")

app = FastAPI()

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ───────── Session helpers ─────────
def create_session(user_id: str) -> str:
    sid = uuid.uuid4().hex
    with Session(engine) as db:
        db.add(SessionModel(
            id=sid,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS)
        ))
        db.commit()
    return sid

def current_user(req: Request) -> User:
    sid = req.cookies.get("sid")
    if not sid:
        raise HTTPException(401)
    with Session(engine) as db:
        sess = db.get(SessionModel, sid)
        if not sess or sess.expires_at < datetime.utcnow():
            raise HTTPException(401)
        return db.get(User, sess.user_id)

def is_admin(user: User) -> bool:
    return user.id == "admin"   # first user gets id 'admin' (see startup)

def get_feed_counts(user_id: str) -> dict:
    """Get counts for different feed types"""
    with Session(engine) as s:
        counts = {}
        
        # All prayers
        counts['all'] = s.exec(select(func.count(Prayer.id)).where(Prayer.flagged == False)).first()
        
        # New & unprayed
        stmt = (
            select(func.count(Prayer.id))
            .select_from(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .having(func.count(PrayerMark.id) == 0)
        )
        unprayed_prayers = s.exec(stmt).all()
        counts['new_unprayed'] = len(unprayed_prayers)
        
        # Most prayed (prayers with at least 1 mark)
        counts['most_prayed'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
        ).first()
        
        # My prayers (prayers user has marked)
        counts['my_prayers'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.user_id == user_id)
        ).first()
        
        # My requests
        counts['my_requests'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(Prayer.author_id == user_id)
        ).first()
        
        # Recent activity (prayers with marks in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        counts['recent_activity'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.created_at >= week_ago)
        ).first()
        
        return counts

# ───────── Prompt of the day ─────────
def todays_prompt() -> str:
    try:
        data = yaml.safe_load(open("prompts.yaml"))
        return data.get(str(date.today()), "Let us pray 🙏")
    except FileNotFoundError:
        return "Let us pray 🙏"

# ───────── LLM Prayer Generation ─────────
def generate_prayer(prompt: str) -> str:
    """Generate a proper prayer from a user prompt using Anthropic API"""
    try:
        system_prompt = """You are a wise and compassionate spiritual guide. Your task is to transform user requests into beautiful, proper prayers that a COMMUNITY can pray FOR the person making the request.

Create prayers that are:
- Written for others to pray FOR the requester (use "them", "they", "this person", or "our friend/brother/sister")
- Properly formed with appropriate address to the Divine
- Concise yet meaningful (2-4 sentences)
- Godly and reverent in tone
- Well-intentioned and positive
- Easy for a community to pray together
- Agreeable to people of various faith backgrounds

IMPORTANT: Do NOT use first person ("me", "my", "I"). Instead, write the prayer so that community members can pray it FOR the person who made the request. Use third person references like "them", "they", "this person", or terms like "our friend" or "our brother/sister"."""

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Please transform this prayer request into a community prayer that others can pray for the person: {prompt}"}
            ]
        )
        
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error generating prayer: {e}")
        return f"Divine Creator, we lift up our friend who asks for help with: {prompt}. May your will be done in their life. Amen."

# ───────── Routes ─────────
@app.get("/", response_class=HTMLResponse)
def feed(request: Request, feed_type: str = "all", user: User = Depends(current_user)):
    # Ensure feed_type has a valid default
    if not feed_type:
        feed_type = "all"
        
    with Session(engine) as s:
        prayers_with_authors = []
        
        if feed_type == "new_unprayed":
            # New prayers and prayers that have never been prayed
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .group_by(Prayer.id)
                .having(func.count(PrayerMark.id) == 0)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "most_prayed":
            # Most prayed prayers (by total prayer count)
            stmt = (
                select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .group_by(Prayer.id)
                .order_by(func.count(PrayerMark.id).desc())
                .limit(50)
            )
        elif feed_type == "my_prayers":
            # Prayers the current user has marked as prayed
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
            # Prayer requests submitted by the current user
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_id == user.id)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "recent_activity":
            # Prayers with recent prayer marks (most recently prayed)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
                .limit(50)
            )
        else:  # "all" or default
            # All prayers (existing behavior)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
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
                'author_name': author_name,
                'marked_by_user': user_mark_counts.get(prayer.id, 0),
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0)
            }
            prayers_with_authors.append(prayer_dict)
    
    # Get feed counts
    feed_counts = get_feed_counts(user.id)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), 
         "me": user, "current_feed": feed_type, "feed_counts": feed_counts}
    )

@app.post("/prayers")
def submit_prayer(text: str = Form(...),
                  tag: Optional[str] = Form(None),
                  user: User = Depends(current_user)):
    # Generate a proper prayer from the user's prompt
    generated_prayer = generate_prayer(text)
    
    with Session(engine) as s:
        s.add(Prayer(
            author_id=user.id, 
            text=text[:500], 
            generated_prayer=generated_prayer,
            project_tag=tag
        ))
        s.commit()
    return RedirectResponse("/", 303)

@app.post("/flag/{pid}")
def flag_prayer(pid: str, request: Request, user: User = Depends(current_user)):
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
                unflag_button = ""
                if is_admin(user):
                    unflag_button = f'''
                          <form method="post" action="/flag/{p.id}" class="inline">
                            <button type="submit" 
                                    hx-post="/flag/{p.id}"
                                    hx-target="#prayer-{p.id}"
                                    hx-swap="outerHTML"
                                    class="text-xs text-red-600 hover:text-red-800 underline">
                              Unflag
                            </button>
                          </form>
                    '''
                
                return HTMLResponse(f'''
                    <li id="prayer-{p.id}" class="bg-red-50 p-6 rounded-lg shadow border-l-4 border-red-400">
                      <div class="mb-4">
                        <div class="flex items-center gap-2 mb-3">
                          <span class="text-red-600 text-sm font-medium">⚠️ Content Flagged</span>
                          {unflag_button}
                        </div>
                        <p class="text-gray-600 italic">This content has been flagged by a community member and is hidden from public view.</p>
                        <div class="mt-3 p-3 bg-gray-100 rounded border">
                          <p class="text-xs text-gray-500 mb-1">Preview (admin only):</p>
                          <p class="text-sm text-gray-700 line-clamp-2">{p.text[:100]}{"..." if len(p.text) > 100 else ""}</p>
                        </div>
                      </div>
                      <footer class="text-xs text-gray-500">
                        Flagged content • Originally by user ID {p.author_id}
                      </footer>
                    </li>
                ''')
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
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 1 person prayed this once</a>'
                            else:
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                        else:
                            prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
                    
                    user_mark_text = ""
                    if user_mark_count > 0:
                        if user_mark_count == 1:
                            user_mark_text = f'<span class="text-green-600 text-xs bg-green-100 px-2 py-1 rounded border border-green-300">✓ You prayed this</span>'
                        else:
                            user_mark_text = f'<span class="text-green-600 text-xs bg-green-100 px-2 py-1 rounded border border-green-300">✓ You prayed this {user_mark_count} times</span>'
                    
                    return HTMLResponse(f'''
                        <li id="prayer-{p.id}" class="bg-white p-6 rounded-lg shadow border-l-4 border-purple-300">
                          {"<div class='mb-4'><h3 class='text-sm font-medium text-purple-600 mb-2'>🙏 Prayer</h3><p class='text-lg leading-relaxed text-gray-800 whitespace-pre-wrap italic'>" + (p.generated_prayer or "") + "</p></div>" if p.generated_prayer else ""}
                          
                          <div class="bg-gray-50 p-3 rounded border-l-2 border-gray-300">
                            <h4 class="text-xs font-medium text-gray-500 mb-1">Original Request</h4>
                            <p class="text-sm text-gray-700 whitespace-pre-wrap">{p.text}</p>
                          </div>
                          
                          <footer class="mt-4 text-xs text-gray-500 flex justify-between items-center">
                            <span>by {"you" if p.author_id == user.id else author_name} · {p.created_at.strftime('%Y-%m-%d %H:%M')}</span>
                            <div class="flex items-center gap-4">
                              <div id="prayer-marks-{p.id}" class="flex items-center gap-2">
                                {prayer_stats}
                                <form method="post" action="/mark/{p.id}" class="inline">
                                  <button hx-post="/mark/{p.id}" 
                                          hx-target="#prayer-marks-{p.id}"
                                          hx-swap="innerHTML"
                                          type="submit" 
                                          class="bg-purple-100 hover:bg-purple-200 text-purple-700 text-xs px-2 py-1 rounded border border-purple-300 focus:outline-none focus:ring-1 focus:ring-purple-500">
                                    Mark as Prayed
                                  </button>
                                </form>
                                {user_mark_text}
                              </div>
                              <form method="post" action="/flag/{p.id}" class="inline">
                                <button type="submit" 
                                        hx-post="/flag/{p.id}"
                                        hx-target="#prayer-{p.id}"
                                        hx-swap="outerHTML"
                                        hx-indicator="#loading-{p.id}"
                                        class="text-red-600 hover:text-red-800 hover:underline text-xs px-1 py-0.5 rounded transition-colors duration-200">
                                  <span class="htmx-indicator" id="loading-{p.id}">🔄</span>
                                  <span>Flag</span>
                                </button>
                              </form>
                            </div>
                          </footer>
                        </li>
                    ''')
            
    # For non-HTMX requests, redirect appropriately
    if p.flagged:
        return RedirectResponse("/", 303)  # Back to main feed when flagging
    else:
        return RedirectResponse("/admin", 303)  # Back to admin when unflagging

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user: User = Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403)
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
    
    return templates.TemplateResponse(
        "admin.html", {"request": request, "flagged": flagged_with_authors, "me": user}
    )

# ───────── Invite-claim flow ─────────
@app.get("/claim/{token}", response_class=HTMLResponse)
def claim_get(token: str, request: Request):
    return templates.TemplateResponse("claim.html", {"request": request, "token": token})

@app.post("/claim/{token}")
def claim_post(token: str, display_name: str = Form(...)):
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        if not inv or inv.used or inv.expires_at < datetime.utcnow():
            raise HTTPException(400, "Invite expired")

        uid = "admin" if s.exec(select(User)).first() is None else uuid.uuid4().hex
        user = User(id=uid, display_name=display_name[:40])
        inv.used = True
        s.add_all([user, inv]); s.commit()

    sid = create_session(uid)
    resp = RedirectResponse("/", 303)
    resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
    return resp

# ───────── Startup: seed first invite ─────────
@app.on_event("startup")
def seed_invite():
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
def new_invite(request: Request, user: User = Depends(current_user)):
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
    return HTMLResponse(f'''
        <div id="invite-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div class="flex justify-between items-start mb-4">
              <h3 class="text-lg font-semibold text-gray-900">Invite Link Generated</h3>
              <button onclick="closeInviteModal()" class="text-gray-400 hover:text-gray-600 text-xl font-bold">&times;</button>
            </div>
            <div class="mb-4">
              <p class="text-sm text-gray-600 mb-3">Share this link with someone you'd like to invite to join the community:</p>
              <div class="bg-gray-50 p-3 rounded border">
                <a href="{url}" class="text-blue-600 break-all hover:underline text-sm" target="_blank">{url}</a>
              </div>
            </div>
            <div class="flex gap-3">
              <button onclick="copyInviteLink('{url}')" class="flex-1 bg-purple-600 hover:bg-purple-700 text-white text-sm px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-purple-500">
                Copy Link
              </button>
              <button onclick="closeInviteModal()" class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-gray-500">
                Close
              </button>
            </div>
          </div>
        </div>
    ''')

@app.post("/mark/{prayer_id}")
def mark_prayer(prayer_id: str, request: Request, user: User = Depends(current_user)):
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
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 1 person prayed this once</a>'
                    else:
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                else:
                    prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 hover:text-purple-800 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
            
            # Return the updated prayer mark section HTML
            user_mark_text = ""
            if user_mark_count > 0:
                if user_mark_count == 1:
                    user_mark_text = f'<span class="text-green-600 text-xs bg-green-100 px-2 py-1 rounded border border-green-300">✓ You prayed this</span>'
                else:
                    user_mark_text = f'<span class="text-green-600 text-xs bg-green-100 px-2 py-1 rounded border border-green-300">✓ You prayed this {user_mark_count} times</span>'
            
            return HTMLResponse(f'''
                <div class="flex items-center gap-2">
                  {prayer_stats}
                  <form method="post" action="/mark/{prayer_id}" class="inline">
                    <button hx-post="/mark/{prayer_id}" 
                            hx-target="#prayer-marks-{prayer_id}"
                            hx-swap="innerHTML"
                            type="submit" 
                            class="bg-purple-100 hover:bg-purple-200 text-purple-700 text-xs px-2 py-1 rounded border border-purple-300 focus:outline-none focus:ring-1 focus:ring-purple-500">
                      Mark as Prayed
                    </button>
                  </form>
                  {user_mark_text}
                </div>
            ''')
    
    # For non-HTMX requests, redirect back to the specific prayer
    return RedirectResponse(f"/#prayer-{prayer_id}", 303)

@app.get("/prayer/{prayer_id}/marks", response_class=HTMLResponse)
def prayer_marks(prayer_id: str, request: Request, user: User = Depends(current_user)):
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
                'created_at': mark.created_at,
                'is_me': mark.user_id == user.id
            })
        
        # Calculate statistics
        total_marks = len(marks_with_users)
        distinct_users = len(set(mark['user_name'] for mark in marks_with_users))
    
    return templates.TemplateResponse(
        "prayer_marks.html",
        {"request": request, "prayer": prayer, "marks": marks_with_users, "me": user, 
         "total_marks": total_marks, "distinct_users": distinct_users}
    )

@app.get("/activity", response_class=HTMLResponse)
def recent_activity(request: Request, user: User = Depends(current_user)):
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
        {"request": request, "activity_items": activity_items, "me": user}
    )
