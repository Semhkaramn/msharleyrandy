from sqlalchemy import Column, Integer, String, BigInteger
from .database import Base, SessionLocal
from datetime import datetime, timedelta

class MessageCount(Base):
    __tablename__ = "message_counts"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)
    count = Column(Integer, default=0, nullable=False)

def get_today_date_tr() -> str:
    now = datetime.utcnow() + timedelta(hours=3)
    return now.strftime("%Y-%m-%d")

def get_week_start_date_tr() -> str:
    now = datetime.utcnow() + timedelta(hours=3)
    day = now.weekday()
    monday = now - timedelta(days=day)
    return monday.strftime("%Y-%m-%d")

def get_month_start_date_tr() -> str:
    now = datetime.utcnow() + timedelta(hours=3)
    return f"{now.year}-{str(now.month).zfill(2)}-01"

def increment_message_count(chat_id: int, user_id: int) -> int:
    db = SessionLocal()
    try:
        date = get_today_date_tr()
        record = db.query(MessageCount).filter(
            MessageCount.chat_id == chat_id,
            MessageCount.user_id == user_id,
            MessageCount.date == date
        ).first()

        if record:
            record.count += 1
        else:
            record = MessageCount(chat_id=chat_id, user_id=user_id, date=date, count=1)
            db.add(record)

        db.commit()
        db.refresh(record)
        return record.count
    finally:
        db.close()

def get_user_message_count(chat_id: int, user_id: int) -> int:
    db = SessionLocal()
    try:
        date = get_today_date_tr()
        record = db.query(MessageCount).filter(
            MessageCount.chat_id == chat_id,
            MessageCount.user_id == user_id,
            MessageCount.date == date
        ).first()
        return record.count if record else 0
    finally:
        db.close()

def get_user_message_count_in_range(chat_id: int, user_id: int, start_date: str, end_date: str = None) -> int:
    db = SessionLocal()
    try:
        query = db.query(MessageCount).filter(
            MessageCount.chat_id == chat_id,
            MessageCount.user_id == user_id,
            MessageCount.date >= start_date
        )
        if end_date:
            query = query.filter(MessageCount.date <= end_date)

        records = query.all()
        return sum(r.count for r in records)
    finally:
        db.close()

def get_user_message_count_by_period(chat_id: int, user_id: int, period: str) -> int:
    if period == "daily":
        return get_user_message_count(chat_id, user_id)
    elif period == "weekly":
        week_start = get_week_start_date_tr()
        return get_user_message_count_in_range(chat_id, user_id, week_start)
    elif period == "monthly":
        month_start = get_month_start_date_tr()
        return get_user_message_count_in_range(chat_id, user_id, month_start)
    elif period == "all":
        db = SessionLocal()
        try:
            records = db.query(MessageCount).filter(
                MessageCount.chat_id == chat_id,
                MessageCount.user_id == user_id
            ).all()
            return sum(r.count for r in records)
        finally:
            db.close()
    return get_user_message_count(chat_id, user_id)

def get_period_name_tr(period: str) -> str:
    periods = {
        "daily": "bugun",
        "weekly": "bu hafta",
        "monthly": "bu ay",
        "all": "toplam"
    }
    return periods.get(period, "bugun")
