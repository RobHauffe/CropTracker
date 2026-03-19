# crud_fruit.py 
import datetime 
from database import FruitPlant, PruningLog 
 
def add_fruit_plant(db, species, label=None, planted_year=None, notes=None): 
    plant = FruitPlant( 
        species=species, 
        label=label, 
        planted_year=planted_year, 
        notes=notes 
    ) 
    db.add(plant) 
    db.commit() 
    db.refresh(plant) 
    return plant 
 
def get_fruit_plants(db): 
    return db.query(FruitPlant).order_by(FruitPlant.species).all() 
 
def delete_fruit_plant(db, plant_id): 
    plant = db.query(FruitPlant).filter(FruitPlant.id == plant_id).first() 
    if plant: 
        db.delete(plant) 
        db.commit() 
 
def log_pruning(db, plant_id, task_key, done_date, notes=None): 
    log = PruningLog( 
        plant_id=plant_id, 
        task_key=task_key, 
        done_date=done_date, 
        notes=notes 
    ) 
    db.add(log) 
    db.commit() 
    db.refresh(log) 
    return log 
 
def get_pruning_logs_for_plant(db, plant_id): 
    return ( 
        db.query(PruningLog) 
        .filter(PruningLog.plant_id == plant_id) 
        .order_by(PruningLog.done_date.desc()) 
        .all() 
    ) 
 
def delete_pruning_log(db, log_id): 
    log = db.query(PruningLog).filter(PruningLog.id == log_id).first() 
    if log: 
        db.delete(log) 
        db.commit()
