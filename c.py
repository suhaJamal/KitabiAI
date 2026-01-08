from app.services.language_detector import LanguageDetector

# Create an instance of LanguageDetector
detector = LanguageDetector()

# Read an actual PDF file
pdf_path = "./outputs/books/2.pdf"  # Replace with your PDF path

try:
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    language, text, _ = detector.detect(pdf_bytes)
    print(f"Detected: {language}")
    print(f"Extracted text length: {len(text) if text else 0} characters")
    
    # Show first 200 characters
    if text:
        print(f"Preview: {text[:200]}")
        
except FileNotFoundError:
    print(f"Error: PDF file not found at {pdf_path}")
except Exception as e:
    print(f"Error: {e}")