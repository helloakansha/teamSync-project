import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Locate the .env file in the same folder as database.py, or in parent project folder
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    parent_env = Path(__file__).resolve().parent.parent / ".env"
    if parent_env.exists():
        env_path = parent_env
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Check your .env file.")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


with engine.connect() as connection:
    print("Successfully connected to PostgreSQL!")