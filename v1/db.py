"""SQLite连接、处理
"""
from sqlalchemy import create_engine, Column, String, VARCHAR, TIMESTAMP
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy import text

engine = create_engine(
    "sqlite:///blacklist.db?check_same_thread=False",
    echo=False,
    future=True,
    connect_args={"timeout": 20}  # 等待锁超时时间，防止高并发写入冲突
)

# 启用 WAL 模式（必须在 engine 创建后立即执行）
with engine.connect() as conn:
    # WAL模式：读写不互斥，写操作不阻塞读操作
    conn.execute(text("PRAGMA journal_mode=WAL"))
    # NORMAL同步：性能与安全性的平衡，即使断电也只会丢失最近一次提交
    conn.execute(text("PRAGMA synchronous=NORMAL"))
    # 设置缓存大小，提高查询性能（默认2000页，建议调大）
    conn.execute(text("PRAGMA cache_size=10000"))
    # 设置内存映射，加快大文件访问
    conn.execute(text("PRAGMA mmap_size=30000000000"))
    conn.commit()

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
