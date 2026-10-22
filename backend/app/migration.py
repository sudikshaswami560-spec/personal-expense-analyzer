import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .database import engine, SessionLocal, Base
from . import models
from .auth import get_password_hash

logger = logging.getLogger("expense_migration")
logger.setLevel(logging.INFO)


DEFAULT_USER_EMAIL = "demo@expenseanalyzer.com"
DEFAULT_USER_PASSWORD = "Password123!"
DEFAULT_USER_NAME = "Demo Account"


def get_or_create_default_user(db: Session) -> models.User:
    """Finds the first existing user or creates a secure default demo account."""
    user = db.query(models.User).order_by(models.User.id.asc()).first()
    if not user:
        user = models.User(
            email=DEFAULT_USER_EMAIL,
            hashed_password=get_password_hash(DEFAULT_USER_PASSWORD),
            full_name=DEFAULT_USER_NAME,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created default user: {user.email} (id: {user.id})")
    return user


def run_database_migrations():
    """
    Safe, idempotent database migration.
    1. Ensures all tables (including 'users') are created.
    2. Inspects existing tables (expenses, monthly_summaries, budgets, incomes, recurring_expenses, savings_goals).
    3. Adds 'user_id' column to tables that were created prior to multi-tenant authentication.
    4. Automatically associates any existing unassigned records with the default user.
    Preserves all existing data with zero data loss.
    """
    logger.info("Checking database schema and running necessary migrations...")

    # Step 1: Ensure tables defined in models exist
    Base.metadata.create_all(bind=engine)

    # Step 2: Ensure a default user exists for assigning legacy unassigned records
    with SessionLocal() as db:
        default_user = get_or_create_default_user(db)
        default_user_id = default_user.id

    # Step 3: Check and add user_id column to existing tables if missing
    tables_to_migrate = [
        "expenses",
        "monthly_summaries",
        "budgets",
        "incomes",
        "recurring_expenses",
        "savings_goals",
    ]

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        for table_name in tables_to_migrate:
            if table_name in existing_tables:
                columns = [c["name"] for c in inspector.get_columns(table_name)]
                if "user_id" not in columns:
                    logger.info(f"Adding 'user_id' column to table '{table_name}'...")
                    # ALTER TABLE ADD COLUMN works uniformly in SQLite and PostgreSQL
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER;"))
                    conn.commit()

                # Associate any NULL user_id rows with the default user
                res = conn.execute(
                    text(f"UPDATE {table_name} SET user_id = :uid WHERE user_id IS NULL;"),
                    {"uid": default_user_id},
                )
                conn.commit()
                if res.rowcount and res.rowcount > 0:
                    logger.info(f"Assigned {res.rowcount} legacy records in '{table_name}' to user id {default_user_id}")

                # Create index on user_id if not exists
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_user_id ON {table_name}(user_id);"))
                    conn.commit()
                except Exception as e:
                    # Index might already exist or not supported by some engines
                    logger.debug(f"Index creation note for {table_name}: {e}")

    logger.info("Database migration completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_database_migrations()
