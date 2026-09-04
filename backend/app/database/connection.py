import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the SQLAlchemy database engine
engine = create_engine(DATABASE_URL, echo=True)

# Create a session factory to manage transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our database models
Base = declarative_base()

def get_db():
    """
    Dependency that provides a database session per request 
    and closes it when finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()