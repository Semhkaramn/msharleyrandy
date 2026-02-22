from sqlalchemy import Column, Integer, String, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from .database import Base, SessionLocal

class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    message_id = Column(BigInteger, index=True, nullable=True)
    participants_ids = Column(ARRAY(BigInteger), default=[], nullable=False)
    winners = Column(Text, nullable=True)
    raffle_message = Column(JSONB, nullable=True)
    winner_message = Column(JSONB, nullable=True)

def add_raffle(chat_id: int) -> Raffle:
    db = SessionLocal()
    try:
        raffle = Raffle(chat_id=chat_id, participants_ids=[])
        db.add(raffle)
        db.commit()
        db.refresh(raffle)
        return raffle
    finally:
        db.close()

def get_raffle(chat_id: int, raffle_id) -> Raffle:
    db = SessionLocal()
    try:
        try:
            rid = int(raffle_id)
            raffle = db.query(Raffle).filter(Raffle.id == rid).first()
            if raffle:
                return raffle
        except (ValueError, TypeError):
            pass
        return db.query(Raffle).filter(
            Raffle.chat_id == chat_id,
            Raffle.message_id == int(raffle_id)
        ).first()
    finally:
        db.close()

def get_raffle_by_message(chat_id: int, message_id: int) -> Raffle:
    db = SessionLocal()
    try:
        return db.query(Raffle).filter(
            Raffle.chat_id == chat_id,
            Raffle.message_id == message_id
        ).first()
    finally:
        db.close()

def update_raffle(raffle_id: int, **kwargs) -> Raffle:
    db = SessionLocal()
    try:
        raffle = db.query(Raffle).filter(Raffle.id == raffle_id).first()
        if raffle:
            for key, value in kwargs.items():
                setattr(raffle, key, value)
            db.commit()
            db.refresh(raffle)
        return raffle
    finally:
        db.close()

def add_participant(raffle_id: int, user_id: int) -> bool:
    db = SessionLocal()
    try:
        raffle = db.query(Raffle).filter(Raffle.id == raffle_id).first()
        if raffle:
            if user_id not in raffle.participants_ids:
                new_list = list(raffle.participants_ids) + [user_id]
                raffle.participants_ids = new_list
                db.commit()
                return True
        return False
    finally:
        db.close()
