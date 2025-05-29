# app.py ─ complete micro-MVP
import os, uuid, yaml
from datetime import datetime, timedelta, date
from typing import Optional
from dotenv import load_dotenv
import anthropic

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from models import engine, User, Prayer, InviteToken, Session as SessionModel

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
def feed(request: Request, user: User = Depends(current_user)):
    with Session(engine) as s:
        # Join Prayer and User tables to get author display names
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
        )
        results = s.exec(stmt).all()
        
        # Create a list of prayers with author names
        prayers_with_authors = []
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
            prayers_with_authors.append(prayer_dict)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), "me": user}
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
def flag_prayer(pid: str, user: User = Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403)
    with Session(engine) as s:
        p = s.get(Prayer, pid)
        if not p:
            raise HTTPException(404)
        p.flagged = not p.flagged
        s.add(p); s.commit()
    return RedirectResponse("/admin", 303)

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
    # Return a small fragment HTMX will swap in for the button
    return (
        f'<div class="bg-green-100 border border-green-300 p-4 rounded">'
        f'<p class="text-sm">Share this invite:</p>'
        f'<a href="{url}" class="text-blue-600 break-all hover:underline">{url}</a>'
        f'</div>'
    )
