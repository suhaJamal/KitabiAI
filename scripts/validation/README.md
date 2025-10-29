# Validation Scripts

This folder contains scripts used to validate the FastText language detection optimization during Phase 1 testing.

## Scripts

### `validate_language_detection.py`
Tests language detection using **character-ratio method** (PyMuPDF + Arabic character counting).

**Usage:**
```bash
python scripts/validation/validate_language_detection.py outputs/test.pdf
```

### `validate_language_detection_fasttext.py`
Tests language detection using **FastText method** (PyMuPDF + FastText model).

**Usage:**
```bash
python scripts/validation/validate_language_detection_fasttext.py outputs/test.pdf
```

**In Docker:**
```bash
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  kitabiai:latest \
  python scripts/validation/validate_language_detection_fasttext.py outputs/test.pdf
```

### `debug_pdf_extraction.py`
Analyzes what PyMuPDF extracts from a PDF:
- Detects if PDF is image-based or text-based
- Shows extracted text samples
- Calculates Arabic character ratio
- Explains why detection succeeded or failed

**Usage:**
```bash
python scripts/validation/debug_pdf_extraction.py outputs/test.pdf
```

**In Docker:**
```bash
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  kitabiai:latest \
  python scripts/validation/debug_pdf_extraction.py outputs/test.pdf
```

### `download_fasttext_model.py`
Helper script to download the FastText language identification model.

**Usage:**
```bash
python scripts/validation/download_fasttext_model.py
```

**Note:** In Docker, the model is automatically downloaded during the build process.

---

## Validation Results

These scripts were used to validate that:
- ✅ FastText works in Docker
- ✅ FastText correctly detects Arabic (even with low character ratio)
- ✅ FastText is more accurate than character-ratio method
- ✅ NumPy 1.x compatibility works
- ✅ Ready for production implementation

**Test PDF:** `ar_ai_ethics_2023.pdf` (160 pages, Arabic)
- Azure detection: Arabic (73.53% ratio)
- FastText detection: Arabic (63.20% confidence, 24.75% ratio)
- **Result: ✅ MATCH**

---

## Production Implementation

Based on validation results, FastText has been integrated into:
- `app/services/language_detector.py` - Production language detection

These validation scripts are kept for:
- Future testing and debugging
- Regression testing
- Validating new PDFs
- Reference implementation
