"""
Database - MySQL 数据库连接

职责：
- 提供统一的数据库连接管理
- Session 工厂
- 连接池配置

不负责：
- 业务表定义（由 libs/facts 定义）
- 数据迁移（由 alembic 或手动 SQL）
"""

from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from .config import get_config
from .logger import get_logger

logger = get_logger("database")

# 声明式基类
Base = declarative_base()

# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """
    获取数据库连接 URL
    
    优先级：环境变量 IRONBULL_DATABASE_URL > config 中的拼接
    """
    config = get_config()
    
    # 直接 URL（推荐用于生产环境）
    url = config.get_str("database_url", "")
    if url:
        return url
    
    # 拼接方式（开发环境）
    host = config.get_str("db_host", "127.0.0.1")
    port = config.get_int("db_port", 3306)
    user = config.get_str("db_user", "root")
    password = config.get_str("db_password", "")
    database = config.get_str("db_name", "ironbull")
    charset = config.get_str("db_charset", "utf8mb4")
    
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"


def init_database(echo: bool = False) -> None:
    """
    初始化数据库连接
    
    Args:
        echo: 是否打印 SQL（开发调试用）
    """
    global _engine, _SessionLocal
    
    if _engine is not None:
        return
    
    config = get_config()
    url = get_database_url()
    
    # 连接池配置
    pool_size = config.get_int("db_pool_size", 5)
    max_overflow = config.get_int("db_max_overflow", 10)
    pool_timeout = config.get_int("db_pool_timeout", 30)
    pool_recycle = config.get_int("db_pool_recycle", 3600)
    
    _engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
    )
    
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )
    
    logger.info(
        "database initialized",
        host=config.get_str("db_host", "127.0.0.1"),
        database=config.get_str("db_name", "ironbull"),
        pool_size=pool_size,
    )


def get_engine():
    """获取数据库引擎"""
    if _engine is None:
        init_database()
    return _engine


def get_session() -> Session:
    """获取数据库会话"""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    数据库会话上下文管理器
    
    Usage:
        with get_db() as db:
            db.query(...)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """
    创建所有表（开发用，生产建议用迁移）
    """
    if _engine is None:
        init_database()
    Base.metadata.create_all(bind=_engine)
    logger.info("database tables created")


def check_connection() -> bool:
    """
    检查数据库连接是否正常
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("database connection failed", error=str(e))
        return False


def close_database() -> None:
    """
    关闭数据库连接（用于优雅关闭）
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("database connection closed")
