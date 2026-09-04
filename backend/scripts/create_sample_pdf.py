import fitz  # PyMuPDF

def create_pdf():
    doc = fitz.open()
    page = doc.new_page()
    text = """
    ABC Residency - Luxury Living in Vijay Nagar, Indore
    
    Project Overview:
    ABC Residency offers premium 3 BHK apartments designed for modern living. Located in the heart of Vijay Nagar, Indore, this project spans 5 acres of greenery with 70% open spaces.
    
    Key Features & Amenities:
    - Temperature-controlled swimming pool
    - State-of-the-art fitness center and clubhouse
    - 24/7 multi-tier security with CCTV surveillance
    - Close proximity to major IT parks and top schools
    
    Pricing & Possession:
    Starting price: ₹85 Lakhs onwards. Possession begins Q4 2026. Approved by major national banks for home loans.
    """
    page.insert_text((50, 50), text, fontsize=11)
    doc.save("../data/sample/sample_brochure.pdf")
    print("Sample PDF brochure created at data/sample/sample_brochure.pdf")

if __name__ == "__main__":
    create_pdf()