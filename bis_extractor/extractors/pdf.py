import fitz  # PyMuPDF
import pdfplumber

def extract_pdf_content(file_path: str):
    """
    Extracts text, headings, and metadata from a PDF.
    """
    result = {
        'text': '',
        'metadata': {},
        'tables': [],
        'status': 'success'
    }
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            result['status'] = 'encrypted'
            return result
            
        result['metadata'] = doc.metadata
        for page in doc:
            result['text'] += page.get_text() + "\n"
            
        doc.close()
        
        # Table extraction using pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    result['tables'].extend(tables)
                    
    except Exception as e:
        result['status'] = f'error: {str(e)}'
        
    return result
