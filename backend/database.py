"""SQLAlchemy persistence for the Eko Sahayak API.

The application uses PostgreSQL when DATABASE_URL is provided and a local
SQLite file otherwise, so the demo works without external infrastructure.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
from pathlib import Path
import secrets
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON


PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("eko_sahayak.database")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    logger.warning("python-dotenv is not installed; using process environment only")

default_db = PROJECT_ROOT / "data" / "eko_sahayak.db"
default_db.parent.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

database_type = "postgresql" if DATABASE_URL.startswith("postgresql+psycopg://") else "sqlite"
logger.info("Database configuration loaded: type=%s", database_type)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100), default="Field operations")
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120))
    root_cause: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(JSON_TYPE)
    next_action: Mapped[str] = mapped_column(Text)
    escalation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    consent_to_share: Mapped[bool] = mapped_column(default=False)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def password_matches(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return secrets.compare_digest(actual, expected)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def check_database_connection() -> dict[str, str | bool]:
    """Run a lightweight database query and report connectivity safely."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_type = "postgresql" if engine.url.drivername == "postgresql+psycopg" else "sqlite"
        logger.info("Database connection check succeeded: type=%s", database_type)
        return {"connected": True, "type": database_type, "detail": "Database query succeeded"}
    except Exception as error:
        logger.exception("Database connection check failed: type=%s", engine.url.drivername)
        return {
            "connected": False,
            "type": engine.url.drivername,
            "detail": f"Database query failed: {type(error).__name__}",
        }


def init_db(seed_cases: list[dict[str, Any]], demo_username: str, demo_password: str) -> None:
    try:
        Base.metadata.create_all(engine)
        with SessionLocal.begin() as db:
            user = db.scalar(select(User).where(User.username == demo_username))
            if user is None:
                user = User(username=demo_username, name="Prabal Goswami", role="Field operations",
                            password_hash=password_hash(demo_password))
                db.add(user)
                db.flush()
            if db.scalar(select(Case.id).where(Case.user_id == user.id)) is None:
                for item in seed_cases:
                    case = Case(user_id=user.id, id=item["id"], status=item["status"], category=item["category"],
                                priority=item["priority"], owner=item["owner"], root_cause=item["root_cause"],
                                evidence=item["evidence"], next_action=item["next_action"], escalation=item["escalation"],
                                confidence=item["confidence"], consent_to_share=item["consent_to_share"],
                                created_at=datetime.fromisoformat(item["created_at"]))
                    db.add(case)
                    db.flush()
                    for event in item.get("audit", []):
                        db.add(AuditEvent(case_id=item["id"], user_id=user.id, event=event["event"],
                                          detail=event["detail"], at=datetime.fromisoformat(event["at"])))
        logger.info("Database initialization succeeded: type=%s", database_type)
    except Exception:
        logger.exception("Database initialization failed: type=%s", database_type)
        raise


@contextmanager
def db_session() -> Iterator[Any]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


SESSION_TTL = timedelta(hours=12)
