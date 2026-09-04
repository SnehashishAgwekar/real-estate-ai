import requests
from bs4 import BeautifulSoup
from app.database.connection import SessionLocal
from app.database.models import Property

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
url = "https://quotes.toscrape.com/"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Find ALL parent cards (jaise real estate mein 'property-card' hota hai)
    # Is test site par har quote ek 'div' mein hai jiski class 'quote' hai
    all_cards = soup.find_all("div", class_="quote")
    
    structured_data = []
    
    # 2. Loop through each card to extract specific inner details
    for card in all_cards:
        # Extract first detail (Text)
        text_node = card.find("span", class_="text")
        clean_text = text_node.text.strip() if text_node else "N/A"
        
        # Extract second detail (Author)
        author_node = card.find("small", class_="author")
        author_name = author_node.text.strip() if author_node else "N/A"
        
        # 3. Pack them into a dictionary
        structured_data.append({
            "quote": clean_text,
            "author": author_name
        })
        
    print(f"Total items extracted: {len(structured_data)}\n")
    
    # Print only the first 3 items to verify
    for item in structured_data[:3]:
        print(item)
else:
    print("Failed to fetch the page.")

def save_to_database(scraped_data):
    # 1. Open a secure connection (Session) to PostgreSQL
    db = SessionLocal()

    try:
        for item in scraped_data:
            # 2. Check for Duplicates
            # Hum 'url' ko check karte hain. Agar yeh URL pehle se DB mein hai, toh skip karo.
            existing_record = db.query(Property).filter(Property.source_url == item['url']).first()

            if not existing_record:
                # 3. Create a Database Object
                # Dictionary ki values ko SQL columns se map kar rahe hain
                new_property = Property(
                    title=item['title'],
                    price=item['price'],
                    city=item['city'],
                    source_url=item['url']
                )
                
                # 4. Add to Session Queue
                db.add(new_property)
                
        # 5. Commit
        # Queue mein rakhe saare naye properties ko ek saath DB mein permanently save kar do
        db.commit()
        print("Scraped data successfully saved to PostgreSQL!")
        
    except Exception as e:
        # Agar koi error aaye, toh aadha-adhura data save hone se roko (Rollback)
        db.rollback() 
        print(f"Database Error: {e}")
    finally:
        # 6. Close the connection to free up memory
        db.close()