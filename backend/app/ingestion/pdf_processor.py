import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_and_chunk_pdf(file_path: str, chunk_size: int = 300, chunk_overlap: int = 50):
    """Extracts text from a PDF file and splits it into overlapping chunks."""
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    return splitter.split_text(full_text)