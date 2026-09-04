import time
import random
import requests
from bs4 import BeautifulSoup
from app.database.connection import SessionLocal
from app.database.models import Property

def scrape_real_estate_listings():
    # Using an accessible open listings structure (e.g., a lightweight directory or regional classifieds page)
    url = "https://www.sulekha.com/properties-in-indore"  # Example open public directory
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"Request blocked or failed with status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Target card selector based on standard open listing layouts
    property_cards = soup.find_all("div", class_="list-item") or soup.find_all("div", class_="property-card")
    
    if not property_cards:
        print("No property cards found. HTML layout might have changed or triggered a protection wall.")
        return

    db = SessionLocal()
    inserted_count = 0

    try:
        for card in property_cards:
            # Title extraction
            title_node = card.find("h3") or card.find("a", class_="title")
            title = title_node.text.strip() if title_node else "Apartment in Indore"
            
            # Price extraction
            price_node = card.find("span", class_="price") or card.find("div", class_="price-val")
            price_text = price_node.text.strip() if price_node else "5000000"
            price_val = parse_price_to_float(price_text)
            
            # Link extraction
            link_node = card.find("a", href=True)
            source_url = link_node['href'] if link_node else url
            if not source_url.startswith("http"):
                source_url = "https://www.sulekha.com" + source_url

            # BHK detection
            bhk_val = 3 if "3 bhk" in title.lower() else (2 if "2 bhk" in title.lower() else 1)

            # Duplicate check
            existing = db.query(Property).filter(Property.source_url == source_url).first()
            
            if not existing:
                new_property = Property(
                    title=title,
                    price=price_val,
                    city="Indore",
                    source_url=source_url,
                    min_bhk=bhk_val
                )
                db.add(new_property)
                inserted_count += 1

            time.sleep(random.uniform(1.0, 2.0))

        db.commit()
        print(f"Successfully scraped and seeded {inserted_count} properties into PostgreSQL!")

    except Exception as e:
        db.rollback()
        print(f"Database/Scraper Error: {e}")
    finally:
        db.close()

def parse_price_to_float(price_str):
    clean_str = price_str.lower().replace("₹", "").replace("rs.", "").replace(",", "").strip()
    try:
        if "cr" in clean_str:
            return float(clean_str.replace("cr", "").strip()) * 10000000
        elif "lakh" in clean_str or "lac" in clean_str:
            return float(clean_str.replace("lakh", "").replace("lac", "").strip()) * 100000
        return float(clean_str)
    except ValueError:
        return 6500000.0

if __name__ == "__main__":
    scrape_real_estate_listings()