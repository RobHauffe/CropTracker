import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os

# Load DATABASE_URL from Streamlit secrets or environment variable
try:
    # Prefer secret for deployment
    DATABASE_URL = st.secrets.get("DATABASE_URL")
    if not DATABASE_URL:
        # Fallback to individual components if URL isn't directly provided
        db_username = st.secrets["DB_USERNAME"]
        db_password = st.secrets["DB_PASSWORD"]
        db_host = st.secrets["DB_HOST"]
        db_port = st.secrets.get("DB_PORT", "6543") # Default to Transaction Pooler port
        db_name = st.secrets["DB_NAME"]
        
        # Determine the driver - pg8000 is more resilient in serverless IPv6 environments
        db_driver = st.secrets.get("DB_DRIVER", "postgresql+psycopg2")
        
        # Construct the URL with pooler settings
        # Note: Supabase pooler hostname is often different (e.g. aws-0-region.pooler.supabase.com)
        DATABASE_URL = f"{db_driver}://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # SSL settings are handled via connect_args for pg8000 compatibility
        if "psycopg2" in db_driver:
            DATABASE_URL += "?sslmode=require"
    
    print(f"✅ Using Streamlit secret for database connection")
except (KeyError, FileNotFoundError):
    # Fallback to environment variable for local development or initial deployment
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crop_tracker.db")
    print(f"⚠️ SECRET NOT FOUND - Using fallback: {DATABASE_URL[:50]}..." if "postgresql" in DATABASE_URL else f"⚠️ Using SQLite fallback")

# engine = create_engine(DATABASE_URL)
# For PostgreSQL/Supabase, we add pooling and statement timeout settings
if "postgresql" in DATABASE_URL:
    connect_args = {}
    
    # Check for both driver name in URL and driver string in secret
    is_pg8000 = "pg8000" in DATABASE_URL
    
    # pg8000 needs ssl_context=True and doesn't support connect_timeout in connect_args
    if is_pg8000:
        connect_args["ssl_context"] = True
    else:
        # psycopg2 supports connect_timeout
        connect_args["connect_timeout"] = 10
         
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args=connect_args
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class CropTemplate(Base):
    __tablename__ = 'crop_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    variety = Column(String)
    sow_location = Column(String, nullable=False) # 'indoor', 'direct outdoor', 'grow bag'
    expected_days_to_germination = Column(Integer)
    expected_days_to_transplant = Column(Integer)
    expected_days_to_first_harvest = Column(Integer)
    expected_days_to_last_harvest = Column(Integer)
    notes = Column(Text)

    cultivations = relationship("Cultivation", back_populates="template")

    def __repr__(self):
        return f"<CropTemplate(name='{self.name}', variety='{self.variety}')>"

class Cultivation(Base):
    __tablename__ = 'cultivations'

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('crop_templates.id'), nullable=False)
    sow_date = Column(Date, nullable=False)
    
    # Predicted milestone dates
    predicted_germination_date = Column(Date)
    predicted_transplant_date = Column(Date)
    predicted_first_harvest_date = Column(Date)
    predicted_last_harvest_date = Column(Date)

    # Actual milestone dates (for manual override)
    actual_germination_date = Column(Date)
    actual_transplant_date = Column(Date)
    actual_first_harvest_date = Column(Date)
    actual_last_harvest_date = Column(Date)

    notes = Column(Text)
    is_archived = Column(Integer, default=0) # 0 = Active, 1 = Archived

    template = relationship("CropTemplate", back_populates="cultivations")
    yields = relationship("Yield", back_populates="cultivation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cultivation(crop='{self.template.name}', sow_date='{self.sow_date}')>"

class Yield(Base):
    __tablename__ = 'yields'

    id = Column(Integer, primary_key=True)
    cultivation_id = Column(Integer, ForeignKey('cultivations.id'), nullable=False)
    weight_kg = Column(Float, nullable=False)
    harvest_date = Column(Date, nullable=False)
    notes = Column(Text)

    cultivation = relationship("Cultivation", back_populates="yields")

    def __repr__(self):
        return f"<Yield(weight={self.weight_kg}kg, date={self.harvest_date})>"

class FruitPlant(Base): 
    __tablename__ = 'fruit_plants' 

    id = Column(Integer, primary_key=True) 
    species = Column(String, nullable=False)   # e.g. "Apple" 
    label = Column(String)                     # user's own name, e.g. "Old apple, back garden" 
    planted_year = Column(Integer)             # optional, for context 
    notes = Column(Text)                       # general notes about this plant 

    pruning_logs = relationship("PruningLog", back_populates="plant", 
                                cascade="all, delete-orphan") 

class PruningLog(Base): 
    __tablename__ = 'pruning_logs' 

    id = Column(Integer, primary_key=True) 
    plant_id = Column(Integer, ForeignKey('fruit_plants.id'), nullable=False) 
    task_key = Column(String, nullable=False)  # matches key in FRUIT_SPECIES dict 
    done_date = Column(Date, nullable=False) 
    notes = Column(Text) 

    plant = relationship("FruitPlant", back_populates="pruning_logs")

def create_db_and_tables():
    """Initialize database - Alembic handles migrations"""
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_data(db):
    crops_data = [
        {"name": "Spinach", "sow_location": "Direct outside", "notes": "Frost hardy, cool soil fine", "expected_days_to_germination": 7, "expected_days_to_first_harvest": 30, "expected_days_to_last_harvest": 60},
        {"name": "Lamb's lettuce", "sow_location": "Direct outside", "notes": "Very frost hardy", "expected_days_to_germination": 10, "expected_days_to_first_harvest": 40, "expected_days_to_last_harvest": 70},
        {"name": "Radishes", "sow_location": "Direct outside", "notes": "Fast crop, succession sow", "expected_days_to_germination": 5, "expected_days_to_first_harvest": 25, "expected_days_to_last_harvest": 40},
        {"name": "Peas", "sow_location": "Direct outside", "notes": "Frost hardy", "expected_days_to_germination": 10, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 90},
        {"name": "Broad beans", "sow_location": "Direct outside", "notes": "Frost hardy", "expected_days_to_germination": 10, "expected_days_to_first_harvest": 70, "expected_days_to_last_harvest": 100},
        {"name": "Pak choi / Asian greens", "sow_location": "Direct outside", "notes": "Frost hardy", "expected_days_to_germination": 7, "expected_days_to_first_harvest": 30, "expected_days_to_last_harvest": 60},
        {"name": "Carrots", "sow_location": "Direct outside", "notes": "Needs soil >8°C", "expected_days_to_germination": 14, "expected_days_to_first_harvest": 70, "expected_days_to_last_harvest": 100},
        {"name": "Parsnips", "sow_location": "Direct outside", "notes": "Slow germinator, be patient", "expected_days_to_germination": 21, "expected_days_to_first_harvest": 100, "expected_days_to_last_harvest": 130},
        {"name": "Beetroot", "sow_location": "Direct outside", "notes": "Wait for soil to warm slightly", "expected_days_to_germination": 10, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 90},
        {"name": "Chard", "sow_location": "Direct outside", "notes": "Can also start indoors", "expected_days_to_germination": 10, "expected_days_to_first_harvest": 50, "expected_days_to_last_harvest": 80},
        {"name": "Kale", "sow_location": "Direct outside", "notes": "Very hardy once established", "expected_days_to_germination": 7, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 90},
        {"name": "Kohlrabi", "sow_location": "Direct outside", "notes": "", "expected_days_to_germination": 7, "expected_days_to_first_harvest": 50, "expected_days_to_last_harvest": 80},
        {"name": "Lettuce", "sow_location": "Direct outside", "notes": "Bolt-risk rises with heat later", "expected_days_to_germination": 7, "expected_days_to_first_harvest": 40, "expected_days_to_last_harvest": 70},
        {"name": "Peppers / Chillies", "sow_location": "Indoor", "notes": "Transplant mid-May; 10–12 weeks lead time", "expected_days_to_germination": 14, "expected_days_to_transplant": 70, "expected_days_to_first_harvest": 120, "expected_days_to_last_harvest": 180},
        {"name": "Aubergine", "sow_location": "Indoor", "notes": "Transplant mid-May; needs warmth", "expected_days_to_germination": 14, "expected_days_to_transplant": 70, "expected_days_to_first_harvest": 120, "expected_days_to_last_harvest": 180},
        {"name": "Tomatoes", "sow_location": "Indoor", "notes": "Transplant mid-May; 8–10 weeks", "expected_days_to_germination": 10, "expected_days_to_transplant": 60, "expected_days_to_first_harvest": 100, "expected_days_to_last_harvest": 160},
        {"name": "Celeriac", "sow_location": "Indoor", "notes": "Very slow, long lead time", "expected_days_to_germination": 21, "expected_days_to_transplant": 90, "expected_days_to_first_harvest": 150, "expected_days_to_last_harvest": 210},
        {"name": "Leeks", "sow_location": "Indoor", "notes": "Transplant late April–May", "expected_days_to_germination": 14, "expected_days_to_transplant": 70, "expected_days_to_first_harvest": 120, "expected_days_to_last_harvest": 180},
        {"name": "Courgette / Zucchini", "sow_location": "Indoor", "notes": "Fast grower; 6 weeks enough", "expected_days_to_germination": 7, "expected_days_to_transplant": 30, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 120},
        {"name": "Cucumber", "sow_location": "Indoor", "notes": "Fast grower; 6 weeks enough", "expected_days_to_germination": 7, "expected_days_to_transplant": 30, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 120},
        {"name": "Pumpkin / Squash", "sow_location": "Indoor", "notes": "Fast grower; 6 weeks enough", "expected_days_to_germination": 7, "expected_days_to_transplant": 30, "expected_days_to_first_harvest": 60, "expected_days_to_last_harvest": 120},
        {"name": "Basil", "sow_location": "Indoor", "notes": "Needs warmth; very frost sensitive", "expected_days_to_germination": 7, "expected_days_to_transplant": 30, "expected_days_to_first_harvest": 50, "expected_days_to_last_harvest": 90},
        {"name": "French beans", "sow_location": "Indoor", "notes": "Fast grower; too early = leggy", "expected_days_to_germination": 7, "expected_days_to_transplant": 20, "expected_days_to_first_harvest": 50, "expected_days_to_last_harvest": 80},
        {"name": "Sweetcorn", "sow_location": "Indoor", "notes": "Fast grower; too early = leggy", "expected_days_to_germination": 10, "expected_days_to_transplant": 30, "expected_days_to_first_harvest": 80, "expected_days_to_last_harvest": 110},
        {"name": "Potatoes (Laura)", "sow_location": "Grow bag", "notes": "Waxy/salad type; harvest ~late June–July", "expected_days_to_germination": 20, "expected_days_to_first_harvest": 100, "expected_days_to_last_harvest": 130},
        {"name": "Potatoes (Agria)", "sow_location": "Grow bag", "notes": "Floury/all-rounder; slightly later harvest", "expected_days_to_germination": 20, "expected_days_to_first_harvest": 110, "expected_days_to_last_harvest": 140},
    ]

    for template_data in crops_data:
        template = CropTemplate(**template_data)
        db.add(template)
    db.commit()
