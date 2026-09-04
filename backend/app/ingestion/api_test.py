import requests
from app.database.connection import SessionLocal
from app.database.models import PropertyModel

def fetch_housing_data():
    # Housing.com API endpoint
    url = "https://mightyzeus-mum.housing.com/api/gql/stale?apiName=SEARCH_RESULTS&emittedFrom=client_buy_SRP&isBot=false&platform=desktop&source=web&source_name=AudienceWeb"

    # Browser headers to prevent blocking
    headers = {
        "accept": "*/*",
        "app-name": "desktop_web_buyer",
        "content-type": "application/json; charset=UTF-8",
        "origin": "https://housing.com",
        "referer": "https://housing.com/in/buy/indore/rau-gid/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    }

    # GraphQL payload filtering only essential details
    payload = {
        "query": """
          query(
            $pageInfo: PageInfoInput, $city: CityInput, $hash: String!, $service: String!, $category: String!,
            $pageTypeMajor: String, $meta: JSON, $fltcnt: String,
            $isLandmarkSearchActive: Boolean, $interestLedFilter: String,
            $isMapSearch: Boolean, $lat: Float, $lng: Float, $outerRadius: Float, $amenities: [String],
            $amenityPageSearch: Boolean, $showCarouselTags: Boolean
          ) {
            searchResults(
              hash: $hash, service: $service, category: $category, city: $city, pageTypeMajor: $pageTypeMajor,
              pageInfo: $pageInfo, meta: $meta, fltcnt: $fltcnt, isLandmarkSearchActive: $isLandmarkSearchActive,
              interestLedFilter: $interestLedFilter, isMapSearch: $isMapSearch, lat: $lat, lng: $lng,
              outerRadius: $outerRadius, amenities: $amenities, amenityPageSearch: $amenityPageSearch,
              showCarouselTags: $showCarouselTags
            ) {
              properties {
                title
                subtitle
                price
                displayPrice { displayValue }
                address { address }
                builtUpArea { value unit }
                url
              }
            }
          }
        """,
        "variables": '{"hash":"P6n45a0dusm70m6dg","service":"buy","category":"residential","city":{"name":"Indore","id":"03d6e2fba020d921c748","cityId":"7bc37231414ee9d72d2e","url":"indore","isTierTwo":true,"products":["buy","plots","commercial","rent","paying_guest"]},"pageTypeMajor":"SRP","pageInfo":{"page":2,"size":30},"meta":{"filterMeta":{},"url":"/in/buy/indore/rau-gid/","shouldModifySearchResults":true,"pagination_flow":false,"enableExperimentalFlag":false,"isDeveloperSearch":false,"orionExperiment":true,"api":{"cursor":"-1151204108","np_total_count":363,"np_offset":0,"resale_offset":0,"resale_total_count":516}},"bot":false,"getStructured":true,"adReq":false,"hashProp":"P6n45a0dusm70m6dg","fltcnt":"","isLandmarkSearchActive":true,"addSellersData":true,"interestLedFilter":"","isMapSearch":false,"lat":0,"lng":0,"outerRadius":0,"amenities":[],"amenityPageSearch":false}'
    }

    print("Fetching live data from Housing.com API...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        properties = data.get("data", {}).get("searchResults", {}).get("properties", [])
        
        print(f"Success! Found {len(properties)} properties. Parsing and saving to PostgreSQL...")
        
        db = SessionLocal()
        try:
            added_count = 0
            for prop in properties:
                title = prop.get("title", "Unknown Title")
                location = prop.get("address", {}).get("address", "Unknown Location")
                source_url = prop.get("url", "")
                
                if not source_url:
                    continue
                if source_url.startswith("/"):
                    source_url = "https://housing.com" + source_url

                # Convert String Price to Float (INR)
                price_str = prop.get("displayPrice", {}).get("displayValue", "")
                price_val = 0.0
                if "Cr" in price_str:
                    try: price_val = float(price_str.replace("Cr", "").replace("₹", "").replace(",", "").strip()) * 10000000
                    except: pass
                elif "L" in price_str:
                    try: price_val = float(price_str.replace("L", "").replace("₹", "").replace(",", "").strip()) * 100000
                    except: pass
                elif price_str.replace("₹", "").replace(",", "").strip().isdigit():
                    try: price_val = float(price_str.replace("₹", "").replace(",", "").strip())
                    except: pass

                # Extract Area and BHK
                area_val = 0.0
                area_dict = prop.get("builtUpArea", {})
                if area_dict and "value" in area_dict:
                    try: area_val = float(area_dict["value"])
                    except: pass
                
                bhk = 0
                if "BHK" in title:
                    try: bhk = int(title.split("BHK")[0].strip()[-1])
                    except: pass

                # Prevent Duplicate Entries
                existing_record = db.query(PropertyModel).filter(PropertyModel.source_url == source_url).first()

                if not existing_record:
                    new_property = PropertyModel(
                        property_name=title[:255], 
                        city="Indore",
                        location=location[:255],
                        price_in_inr=price_val,
                        bhk=bhk,
                        area_sqft=area_val,
                        property_type="Apartment", 
                        source="Housing.com",
                        source_url=source_url
                    )
                    db.add(new_property)
                    added_count += 1
            
            db.commit()
            print(f"Successfully saved {added_count} new properties to PostgreSQL!")
            
        except Exception as e:
            db.rollback()
            print(f"Database insertion failed: {e}")
        finally:
            db.close()
    else:
        print(f"Failed to fetch data. Status Code: {response.status_code}")
        print("Response:", response.text)

if __name__ == "__main__":
    fetch_housing_data()