from backend.database.session import engine
from backend.database.base import Base
# Import all models to ensure metadata registration
import backend.models

def init_db():
    """Initializes all database tables defined in SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
