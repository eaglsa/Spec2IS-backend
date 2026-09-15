from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from bis_extractor.config import DATABASE_URL
from bis_extractor.database.models import Base

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionFactory)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return Session()
