import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session as DBSession

from backend.models.user import User
from backend.models.session import Session
from backend.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class AuthService:
    def __init__(self, db: DBSession):
        self.db = db
        self.settings = Settings()

    def create_user(self, email: str, password: str, display_name: str, role: str = "user") -> User:
        password_hash = hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            role=role
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        # Use naive UTC datetime for SQLite compatibility
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=self.settings.session_expire_hours)
        session = Session(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(session)
        self.db.commit()
        return token

    def validate_session(self, token: str) -> User | None:
        session = self.db.query(Session).filter(Session.token == token).first()
        if not session:
            return None
        if session.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            self.db.delete(session)
            self.db.commit()
            return None
        return session.user

    def delete_session(self, token: str) -> bool:
        session = self.db.query(Session).filter(Session.token == token).first()
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
