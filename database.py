import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL should be provided via environment variable. Example:
# postgresql://user:password@localhost:5432/myntra_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./excel_matcher.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Create tables if they don't exist
def init_db():
    Base.metadata.create_all(bind=engine)
