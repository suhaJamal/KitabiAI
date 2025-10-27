# FastText Installation Guide for Language Detection

This guide shows you how to install FastText and download the language detection model.

---

## Step 1: Install FastText Library

### Option A: Using pip (Recommended)

```powershell
# Activate your virtual environment first
# (.venv) should be visible in your prompt

pip install fasttext-wheel
```

**Note:** Use `fasttext-wheel` instead of `fasttext` on Windows - it includes pre-built binaries.

### Option B: If Option A fails

```powershell
pip install fasttext
```

If this gives build errors, try:
```powershell
# Install Microsoft C++ Build Tools first
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Then try again
pip install fasttext
```

---

## Step 2: Download FastText Language Detection Model

### Option A: Manual Download (Most Reliable)

1. **Download the model file:**
   - Go to: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz
   - Or use this alternative: https://fasttext.cc/docs/en/language-identification.html
   - File size: ~900 KB (compressed model for 176 languages)

2. **Save to your project:**
   - Save as: `lid.176.ftz`
   - Location: `C:\Users\Suha\Desktop\2025\bookAutomation-v3\lid.176.ftz`
   - (Same directory as your validate script)

### Option B: Download with PowerShell

```powershell
# Download using PowerShell
Invoke-WebRequest -Uri "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz" -OutFile "lid.176.ftz"

# Verify download
ls lid.176.ftz
# Should show ~900 KB file
```

### Option C: Download with Python script

```powershell
python download_fasttext_model.py
```

(Script is included in the repository)

---

## Step 3: Verify Installation

Test that FastText is working:

```powershell
python -c "import fasttext; print('FastText installed:', fasttext.__version__)"
```

Test that model loads:

```powershell
python -c "import fasttext; model = fasttext.load_model('lid.176.ftz'); print('Model loaded successfully')"
```

---

## Expected File Structure

After setup, you should have:

```
bookAutomation-v3/
├── .venv/                          # Your virtual environment
├── lid.176.ftz                     # FastText model (900 KB)
├── validate_language_detection_fasttext.py
├── download_fasttext_model.py
├── .env                            # Azure credentials
└── outputs/
    └── ar_ai_ethics_2023.pdf       # Test PDFs
```

---

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'fasttext'"

**Solution:**
```powershell
pip install fasttext-wheel
```

### Problem: "Model file not found"

**Solution:**
- Make sure `lid.176.ftz` is in the same directory as your script
- Or provide full path in the code

### Problem: FastText installation fails on Windows

**Solution:**
```powershell
# Try the wheel version (pre-built)
pip install fasttext-wheel

# Or install build tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### Problem: Download blocked or 403 Forbidden

**Solution:**
- Try manual download from browser
- Use alternative source: https://fasttext.cc/docs/en/language-identification.html
- Try the Python script with different headers

---

## Quick Start Command Sequence

```powershell
# 1. Activate environment
cd C:\Users\Suha\Desktop\2025\bookAutomation-v3

# 2. Install FastText
pip install fasttext-wheel

# 3. Download model
Invoke-WebRequest -Uri "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz" -OutFile "lid.176.ftz"

# 4. Verify
python -c "import fasttext; model = fasttext.load_model('lid.176.ftz'); print('Ready!')"

# 5. Run validation
python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

---

## Model Information

**File:** lid.176.ftz
**Size:** ~900 KB (compressed)
**Languages:** 176 languages supported
**Accuracy:** >99% for Arabic/English
**Speed:** Very fast (microseconds per detection)

**Output format:**
- Language code: `__label__ar` (Arabic), `__label__en` (English)
- Confidence score: 0.0 to 1.0

---

## Alternative: Use Character-Ratio Instead

If FastText is too complex, you can use the character-ratio method (no dependencies):

```powershell
python validate_language_detection.py outputs/ar_ai_ethics_2023.pdf
```

This uses Arabic Unicode range detection (U+0600-U+06FF) which works well for Arabic/English.

---

**Ready to test?** Once you have FastText installed and the model downloaded, run:

```powershell
python validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```
