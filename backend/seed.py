from app.database.connection import SessionLocal
from sqlalchemy import Table, MetaData
import datetime
import uuid

def force_seed_db():
    db = SessionLocal()
    engine = db.get_bind()
    
    try:
        # 1. Scan the database to see exactly what columns exist
        metadata = MetaData()
        properties_table = Table('properties', metadata, autoload_with=engine)
        
        # 2. The core Indore data we care about
        record = {
            'property_name': 'Skyline Heights',
            'city': 'Indore',
            'location': 'Vijay Nagar',
            'price_in_inr': 15000000,
            'bhk': 3,
            'area_sqft': 1800,
            'property_type': 'Apartment'
        }
        
        # 3. Automatically fill in EVERY other required column to bypass constraints!
        for col in properties_table.columns:
            if col.name not in record and not col.nullable and not col.primary_key:
                col_type = str(col.type).lower()
                if 'int' in col_type or 'numeric' in col_type or 'float' in col_type:
                    record[col.name] = 1
                elif 'char' in col_type or 'text' in col_type:
                    record[col.name] = 'Available'
                elif 'bool' in col_type:
                    record[col.name] = True
                elif 'date' in col_type or 'time' in col_type:
                    record[col.name] = datetime.datetime.now()
                elif 'uuid' in col_type:
                    record[col.name] = str(uuid.uuid4())
                    
        # 4. Force the insert safely
        db.execute(properties_table.insert().values(record))
        db.commit()
        print("✅ BOOM! Ek hi baar mein sab thik ho gaya! Test property added.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    force_seed_db()