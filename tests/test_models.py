import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_user(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.role == "user"


def test_create_conversation(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="Test Chat")
    db_session.add(conv)
    db_session.commit()
    assert conv.id is not None


def test_create_message(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="Test Chat")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, role="user", content="Hello")
    db_session.add(msg)
    db_session.commit()
    assert msg.id is not None
