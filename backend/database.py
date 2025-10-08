from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://akeshibh:password@localhost/face_organizer")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Person(Base):
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="Person_")
    folder_id = Column(String(100))
    sample_face_path = Column(String(255))

class PhotoFace(Base):
    __tablename__ = "photo_faces"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_name = Column(String(255))
    photo_drive_id = Column(String(100))
    person_ids = Column(Text)  # JSON array of person IDs
    is_original = Column(Boolean, default=True)
    original_folder_id = Column(String(100))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()