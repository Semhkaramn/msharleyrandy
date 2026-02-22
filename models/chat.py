from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base, SessionLocal
from enum import Enum

class MessagePeriodType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL = "all"

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    number = Column(Integer, default=1, nullable=False)
    subscribe = Column(String, nullable=True)
    nodelete = Column(Boolean, default=False, nullable=False)
    raffle_message = Column(JSONB, nullable=True)
    winner_message = Column(JSONB, nullable=True)
    min_message_count = Column(Integer, default=0, nullable=False)
    message_period = Column(String, default="daily", nullable=False)

def find_chat(chat_id: int) -> Chat:
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(chat_id=chat_id)
            db.add(chat)
            db.commit()
            db.refresh(chat)
        return chat
    finally:
        db.close()

def update_chat(chat_id: int, **kwargs) -> Chat:
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(chat_id=chat_id, **kwargs)
            db.add(chat)
        else:
            for key, value in kwargs.items():
                setattr(chat, key, value)
        db.commit()
        db.refresh(chat)
        return chat
    finally:
        db.close()
