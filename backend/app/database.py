import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Allow direct DATABASE_URL (e.g. PostgreSQL, Render external DB) or fallback to SQLite
raw_database_url = os.getenv("DATABASE_URL")

if raw_database_url:
    # Render and Heroku PostgreSQL URLs start with 'postgres://', which SQLAlchemy 1.4+ requires as 'postgresql://'
    if raw_database_url.startswith("postgres://"):
        DATABASE_URL = raw_database_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = raw_database_url
else:
    # 2. Default to SQLite with configurable file path (e.g. /var/data/expenses.db on a Render Persistent Disk)
    database_file = os.getenv("DATABASE_FILE", "expenses.db")
    # Ensure parent directory exists if a persistent disk mount path was specified
    dir_name = os.path.dirname(database_file)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    DATABASE_URL = f"sqlite:///{database_file}"

# SQLite requires check_same_thread: False when handling multi-threaded FastAPI requests
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session for each request and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
