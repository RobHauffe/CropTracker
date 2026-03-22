from sqlalchemy.orm import Session
from database import CropTemplate, Cultivation, Yield
from calculations import calculate_predicted_dates
import datetime

# --- Crop Template CRUD ---
def create_template(db: Session, template_data: dict):
    template = CropTemplate(**template_data)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

def get_templates(db: Session):
    return db.query(CropTemplate).all()

def get_template_by_id(db: Session, template_id: int):
    return db.query(CropTemplate).filter(CropTemplate.id == template_id).first()

def update_template(db: Session, template_id: int, template_data: dict):
    db_template = get_template_by_id(db, template_id)
    if db_template:
        for key, value in template_data.items():
            setattr(db_template, key, value)
        db.commit()
        db.refresh(db_template)
        
        # Also update all active cultivations linked to this template
        cultivations = db.query(Cultivation).filter(Cultivation.template_id == template_id).all()
        for cultivation in cultivations:
            calculate_predicted_dates(cultivation)
        db.commit()
        
    return db_template

def delete_template(db: Session, template_id: int):
    db_template = get_template_by_id(db, template_id)
    if db_template:
        db.delete(db_template)
        db.commit()
    return db_template

# --- Cultivation CRUD ---
def start_cultivation(db: Session, template_id: int, sow_date: datetime.date, notes: str = None):
    cultivation = Cultivation(template_id=template_id, sow_date=sow_date, notes=notes)
    # Predicted dates are calculated based on the template
    db.add(cultivation)
    db.commit()
    db.refresh(cultivation)
    # Now calculate predicted dates
    cultivation = calculate_predicted_dates(cultivation)
    db.commit()
    db.refresh(cultivation)
    return cultivation

def get_cultivations(db: Session):
    return db.query(Cultivation).all()

def get_cultivation_by_id(db: Session, cultivation_id: int):
    return db.query(Cultivation).filter(Cultivation.id == cultivation_id).first()

def update_cultivation(db: Session, cultivation_id: int, cultivation_data: dict):
    db_cultivation = get_cultivation_by_id(db, cultivation_id)
    if db_cultivation:
        for key, value in cultivation_data.items():
            setattr(db_cultivation, key, value)
        db_cultivation = calculate_predicted_dates(db_cultivation)
        db.commit()
        db.refresh(db_cultivation)
    return db_cultivation

def delete_cultivation(db: Session, cultivation_id: int):
    db_cultivation = get_cultivation_by_id(db, cultivation_id)
    if db_cultivation:
        db.delete(db_cultivation)
        db.commit()
    return db_cultivation

def update_cultivation_plot(db: Session, cultivation_id: int, plot_address: str):
    db_cultivation = get_cultivation_by_id(db, cultivation_id)
    if db_cultivation:
        db_cultivation.plot_address = plot_address
        db.commit()
        db.refresh(db_cultivation)
    return db_cultivation

# --- Yield CRUD ---
def create_yield(db: Session, cultivation_id: int, weight_kg: float, harvest_date: datetime.date, notes: str = None):
    yield_record = Yield(cultivation_id=cultivation_id, weight_kg=weight_kg, harvest_date=harvest_date, notes=notes)
    db.add(yield_record)
    db.commit()
    db.refresh(yield_record)
    return yield_record

def get_yields(db: Session):
    return db.query(Yield).all()

def get_yield_by_id(db: Session, yield_id: int):
    return db.query(Yield).filter(Yield.id == yield_id).first()

def get_yields_by_cultivation(db: Session, cultivation_id: int):
    return db.query(Yield).filter(Yield.cultivation_id == cultivation_id).all()

def get_yields_by_crop(db: Session, template_id: int):
    """Get all yields for a specific crop template across all cultivations"""
    return db.query(Yield).join(Cultivation).filter(Cultivation.template_id == template_id).all()

def update_yield(db: Session, yield_id: int, yield_data: dict):
    db_yield = get_yield_by_id(db, yield_id)
    if db_yield:
        for key, value in yield_data.items():
            setattr(db_yield, key, value)
        db.commit()
        db.refresh(db_yield)
    return db_yield

def delete_yield(db: Session, yield_id: int):
    db_yield = get_yield_by_id(db, yield_id)
    if db_yield:
        db.delete(db_yield)
        db.commit()
    return db_yield
