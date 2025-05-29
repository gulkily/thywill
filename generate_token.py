import jwt
import uuid, sys, os, datetime as dt
SECRET = os.getenv("JWT_SECRET", "changeme")
tid = uuid.uuid4().hex
payload = {"tid": tid, "exp": dt.datetime.utcnow()+dt.timedelta(days=3)}
print(jwt.encode(payload, SECRET, algorithm="HS256"))

