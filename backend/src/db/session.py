from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import json
import os

# Load config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "development.json")

try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    print(f"Loaded config from {CONFIG_PATH}")
except FileNotFoundError:
    # Fallback to env or defaults
    print("Warning: Config file not found. Using defaults/env.")
    config = {
        "postgres_url": os.getenv("POSTGRES_URL", "sqlite:///./test.db")
    }

SQLALCHEMY_DATABASE_URL = config.get("postgres_url")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
