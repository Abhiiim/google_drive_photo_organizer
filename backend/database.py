from sqlalchemy import Column, Integer, String, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import get_settings


settings = get_settings()

engine_kwargs = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):  # pragma: no cover - sqlite dev convenience
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        **engine_kwargs,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        **engine_kwargs,
    )

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