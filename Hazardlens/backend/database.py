"""
HazardLens - Database Models
"""
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./hazardlens.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_name = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)  # "No Helmet", "No Safety Vest", "Restricted Zone Intrusion"
    location_zone = Column(String, default="Zone A")
    confidence = Column(Float, nullable=False)
    severity = Column(String, default="Medium")  # "Low", "Medium", "High", "Critical"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    image_path = Column(String, nullable=True)
    annotated_image_path = Column(String, nullable=True)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    zone_type = Column(String, default="Restricted")  # "Restricted", "Hazardous", "Safe"
    color = Column(String, default="#FF0000")
    coordinates = Column(Text, nullable=True)  # JSON string of polygon points
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DatasetImage(Base):
    __tablename__ = "dataset_images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    analyzed = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
