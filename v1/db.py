"""SQLite连接、处理
"""
from sqlalchemy import create_engine, Column, String, VARCHAR, TIMESTAMP
from sqlalchemy.orm import sessionmaker, declarative_base, Session

engine = create_engine(
    "sqlite:///blacklist.db?check_same_thread=False", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Blacklist(Base):
    __tablename__ = 'blacklist'
    userid = Column(VARCHAR(10), primary_key=True)
    username = Column(String)
    reason = Column(String)
    operator = Column(VARCHAR(10))
    created_at = Column(TIMESTAMP)


class Token(Base):
    __tablename__ = 'token'
    botid = Column(VARCHAR(10), primary_key=True)
    token = Column(VARCHAR(36))


Base.metadata.create_all(engine)
