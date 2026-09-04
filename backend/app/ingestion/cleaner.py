import re
import pandas as pd

def parse_price(price_str: str) -> float:
    """Converts price strings like '85 Lakhs', '1.5 Cr', or '8500000' to standard float in INR."""
    if pd.isna(price_str):
        return 0.0
    
    text = str(price_str).strip().lower()
    
    if text.replace('.', '', 1).isdigit():
        return float(text)
    
    num_match = re.search(r"[\d\.]+", text)
    if not num_match:
        return 0.0
    num = float(num_match.group())
    
    if "cr" in text or "crore" in text:
        return num * 10_000_000
    elif "lakh" in text or "lakhs" in text or "lac" in text:
        return num * 100_000
    
    return num

def clean_structured_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans raw property dataframe and removes duplicates."""
    df = df.copy()
    
    df['city'] = df['city'].astype(str).str.strip().str.title()
    df['property_name'] = df['property_name'].astype(str).str.strip()
    df['location'] = df['location'].astype(str).str.strip()
    
    df['price_in_inr'] = df['price_raw'].apply(parse_price)
    
    df_clean = df.drop_duplicates(
        subset=['property_name', 'city', 'bhk', 'area_sqft'], 
        keep='first'
    )
    
    return df_clean