# Fix FastText NumPy Compatibility Issue

## The Problem

You're seeing this error:
```
ERROR: Unable to avoid copy while creating an array as requested.
If using `np.array(obj, copy=False)` replace it with `np.asarray(obj)`
```

**Cause:** FastText library hasn't been updated for NumPy 2.0 compatibility yet.

---

## The Solution: Downgrade NumPy

### Step 1: Check Current NumPy Version

```powershell
python -c "import numpy; print(numpy.__version__)"
```

If it shows `2.x.x`, you need to downgrade.

### Step 2: Downgrade to NumPy 1.x

```powershell
# Uninstall current NumPy
pip uninstall numpy -y

# Install compatible version
pip install "numpy<2.0"

# Verify
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
# Should show 1.26.x or 1.25.x
```

### Step 3: Test FastText

```powershell
# Quick test
python -c "import fasttext; model = fasttext.load_model('lid.176.ftz'); print('FastText OK')"

# Full test
python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

---

## Alternative: Use fasttext-wheel

If downgrading NumPy causes other issues, try the wheel version:

```powershell
pip uninstall fasttext -y
pip install fasttext-wheel
```

---

## What If This Breaks Other Packages?

If other packages require NumPy 2.0, you have two options:

### Option 1: Use Virtual Environment (Recommended)

Create a separate environment just for testing:

```powershell
# Create new test environment
python -m venv .venv_fasttext_test

# Activate it
.venv_fasttext_test\Scripts\Activate.ps1

# Install dependencies with NumPy 1.x
pip install "numpy<2.0" fasttext PyMuPDF

# Run tests
python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf

# When done, deactivate
deactivate
```

### Option 2: Skip FastText

Use the character-ratio method instead (no NumPy issues):

```powershell
python validate_language_detection.py outputs/ar_ai_ethics_2023.pdf
```

**BUT:** You mentioned character-ratio failed to detect Arabic. Let's debug why first:

```powershell
python debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf
```

---

## Quick Decision Tree

```
Is your PDF image-based (scanned)?
├─ YES → Must use Azure OCR (no cost savings possible)
└─ NO → Text-based PDF
    │
    Does PyMuPDF extract Arabic characters?
    ├─ YES, enough → Use character-ratio method
    ├─ YES, but too few → Try FastText OR lower threshold
    └─ NO → Must use Azure (or try different PDF library)
```

---

## Next Steps

1. **First, debug your PDF:**
   ```powershell
   python debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf
   ```

2. **If PDF is text-based and has Arabic:**
   - Fix NumPy: `pip install "numpy<2.0"`
   - Test FastText: `python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf`

3. **If PDF is image-based:**
   - Cost optimization not possible for this PDF
   - Must use Azure for OCR

4. **If PyMuPDF extracts no Arabic:**
   - PDF might need Azure anyway
   - Cost savings may be limited

---

## Commands Summary

```powershell
# Debug what's wrong
python debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf

# Fix NumPy
pip install "numpy<2.0"

# Test FastText
python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf

# Or test character-ratio (if debug shows it should work)
python validate_language_detection.py outputs/ar_ai_ethics_2023.pdf
```
