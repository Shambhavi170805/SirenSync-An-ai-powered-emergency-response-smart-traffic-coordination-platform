from sqlalchemy import inspect, text
from backend.database.session import engine
from backend.database.base import Base
# Import all models to ensure metadata registration
import backend.models


def migrate_db(bind_engine=None):
    """
    Idempotent SQLite schema migration helper.
    Inspects existing database tables and adds missing columns without data loss.
    """
    target_engine = bind_engine or engine

    with target_engine.connect() as conn:
        inspector = inspect(target_engine)
        tables = inspector.get_table_names()

        if "emergencies" in tables:
            columns = [
                col["name"]
                for col in inspector.get_columns("emergencies")
            ]

            if "symptoms" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE emergencies "
                        "ADD COLUMN symptoms VARCHAR(500);"
                    )
                )
                conn.commit()
                print("Database migration: Added 'symptoms' column.")

            if "region" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE emergencies "
                        "ADD COLUMN region VARCHAR(100) "
                        "NOT NULL DEFAULT 'Dehradun';"
                    )
                )
                conn.commit()
                print("Database migration: Added 'region' column.")

        if "hospitals" in tables:
            columns = [
                col["name"]
                for col in inspector.get_columns("hospitals")
            ]

            if "region" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE hospitals "
                        "ADD COLUMN region VARCHAR(100) "
                        "NOT NULL DEFAULT 'Bengaluru';"
                    )
                )
                conn.commit()
                print("Database migration: Added 'region' column.")


def init_db():
    """Initializes all database tables and applies idempotent migrations."""
    Base.metadata.create_all(bind=engine)
    migrate_db()
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
