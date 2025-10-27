# Running Language Detection Validation in Docker

This guide shows you how to run the language detection validation using Docker, with all dependencies (including FastText) pre-installed.

---

## Prerequisites

1. **Docker installed** on your machine
2. **Azure credentials** in `.env` file
3. **Sample PDFs** in `outputs/` folder

---

## Quick Start

### Step 1: Build the Docker Image

```bash
# Build the image (this will download FastText model automatically)
docker build -t kitabiai:latest .

# This will:
# - Install all Python dependencies (including fasttext-wheel, numpy<2.0)
# - Download the FastText model (~900KB)
# - Copy all validation scripts
```

### Step 2: Verify FastText Model is Downloaded

```bash
# Check if model was downloaded successfully
docker run --rm kitabiai:latest ls -lh /app/lid.176.ftz

# Should show: -rw-r--r-- 1 root root 917K ... /app/lid.176.ftz
```

### Step 3: Run Validation Scripts

#### Option A: Debug Your PDF (Recommended First)

```bash
# Analyze what PyMuPDF extracts from your PDF
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  kitabiai:latest \
  python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf
```

**Windows PowerShell:**
```powershell
docker run --rm `
  -v ${PWD}/outputs:/app/outputs `
  kitabiai:latest `
  python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf
```

#### Option B: Test FastText Detection

```bash
# Run FastText-based validation
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  kitabiai:latest \
  python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

**Windows PowerShell:**
```powershell
docker run --rm `
  -v ${PWD}/outputs:/app/outputs `
  -v ${PWD}/.env:/app/.env `
  kitabiai:latest `
  python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

#### Option C: Test Character-Ratio Detection

```bash
# Run character-ratio validation (no FastText)
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  kitabiai:latest \
  python scripts/validation/validate_language_detection.py outputs/ar_ai_ethics_2023.pdf
```

---

## Using Docker Compose (Easier)

### Step 1: Update docker-compose.yml (Already Done)

The `docker-compose.yml` already has the necessary volume mappings.

### Step 2: Build and Run

```bash
# Build the image
docker-compose build

# Run validation scripts
docker-compose run --rm kitabiai python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf

docker-compose run --rm kitabiai python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

**Windows PowerShell:**
```powershell
docker-compose build

docker-compose run --rm kitabiai python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf

docker-compose run --rm kitabiai python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

---

## Troubleshooting

### Issue: FastText model download fails during build

**Solution 1: Build with internet access**
```bash
docker build --network=host -t kitabiai:latest .
```

**Solution 2: Download model manually and copy during build**

1. Download model manually:
   ```bash
   curl -L -o lid.176.ftz https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz
   ```

2. Update Dockerfile to copy instead of download:
   ```dockerfile
   # Replace the wget/curl RUN command with:
   COPY lid.176.ftz /app/lid.176.ftz
   ```

3. Rebuild:
   ```bash
   docker build -t kitabiai:latest .
   ```

### Issue: NumPy compatibility error

**Already fixed!** The requirements.txt now specifies `numpy>=1.24.0,<2.0.0`

If you still see issues, rebuild the image:
```bash
docker build --no-cache -t kitabiai:latest .
```

### Issue: "document closed" error

This is already fixed in the latest `debug_pdf_extraction.py`. Pull the latest code:
```bash
git pull
docker build -t kitabiai:latest .
```

### Issue: .env file not found

Make sure you have a `.env` file in your project root with Azure credentials:
```bash
# Create from example
cp .env.example .env

# Edit with your credentials
# AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
# AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key-here
```

---

## Running in Office Environment

Since you're in your office without a local Python environment, Docker is perfect!

### Complete Workflow:

```bash
# 1. Pull latest code
git pull

# 2. Make sure you have test PDFs in outputs/
ls outputs/

# 3. Make sure .env has Azure credentials
cat .env

# 4. Build Docker image (downloads everything)
docker build -t kitabiai:latest .

# 5. Debug your PDF first
docker run --rm -v $(pwd)/outputs:/app/outputs kitabiai:latest \
  python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf

# 6. Run FastText validation
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  kitabiai:latest \
  python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf

# 7. Check results and share with me!
```

**Windows PowerShell:**
```powershell
# 1. Pull latest code
git pull

# 2. Check test PDFs
ls outputs/

# 3. Check .env
cat .env

# 4. Build Docker image
docker build -t kitabiai:latest .

# 5. Debug your PDF
docker run --rm -v ${PWD}/outputs:/app/outputs kitabiai:latest python scripts/validation/debug_pdf_extraction.py outputs/ar_ai_ethics_2023.pdf

# 6. Run FastText validation
docker run --rm `
  -v ${PWD}/outputs:/app/outputs `
  -v ${PWD}/.env:/app/.env `
  kitabiai:latest `
  python scripts/validation/validate_language_detection_fasttext.py outputs/ar_ai_ethics_2023.pdf
```

---

## What Gets Installed

The Docker image includes:

### Python Packages:
- ✅ `fasttext-wheel>=0.9.2` - Language detection
- ✅ `numpy>=1.24.0,<2.0.0` - NumPy 1.x (FastText compatible)
- ✅ `requests>=2.31.0` - For downloading models
- ✅ `PyMuPDF>=1.23.0` - PDF processing
- ✅ `azure-ai-documentintelligence` - Azure OCR
- ✅ All other existing dependencies

### System Packages:
- ✅ `gcc` - For compiling Python packages
- ✅ `wget` - For downloading FastText model
- ✅ `curl` - Fallback for downloading

### FastText Model:
- ✅ `lid.176.ftz` - 176-language detection model (~900KB)
- Location: `/app/lid.176.ftz`

### Validation Scripts:
- ✅ `validate_language_detection.py` - Character-ratio method
- ✅ `validate_language_detection_fasttext.py` - FastText method
- ✅ `debug_pdf_extraction.py` - PDF analysis tool
- ✅ `download_fasttext_model.py` - Model downloader

---

## Expected Output

### From debug script:
```
================================================================================
PDF EXTRACTION ANALYSIS
================================================================================
File: ar_ai_ethics_2023.pdf

📄 PDF Info:
   Total pages: 160
   Text-based pages: 158/160
   Arabic ratio: 24.75%

🟡 TEXT-BASED PDF with poor extraction
   Cost optimization: POSSIBLE with FastText
```

### From FastText validation:
```
[Method 1] Current: Azure Document Intelligence
✅ Result: ARABIC

[Method 2] Proposed: PyMuPDF + FastText
✅ Result: ARABIC

[Comparison]
✅ MATCH! Both detected: ARABIC
   → FastText can replace Azure for language detection!
```

---

## Next Steps After Validation

Once you confirm FastText works in Docker:

1. **Share results with me** - I'll analyze and provide recommendations
2. **Implement in production** - Integrate FastText into main application
3. **Deploy with Docker** - Use the same Docker setup for production

---

## Quick Reference

```bash
# Build
docker build -t kitabiai:latest .

# Debug PDF
docker run --rm -v $(pwd)/outputs:/app/outputs kitabiai:latest \
  python scripts/validation/debug_pdf_extraction.py outputs/YOUR_PDF.pdf

# Test FastText
docker run --rm -v $(pwd)/outputs:/app/outputs -v $(pwd)/.env:/app/.env \
  kitabiai:latest python scripts/validation/validate_language_detection_fasttext.py outputs/YOUR_PDF.pdf

# Test character-ratio
docker run --rm -v $(pwd)/outputs:/app/outputs -v $(pwd)/.env:/app/.env \
  kitabiai:latest python scripts/validation/validate_language_detection.py outputs/YOUR_PDF.pdf
```

---

**Ready to test in your office!** Just build the Docker image and run the validation scripts. Everything is pre-configured.
