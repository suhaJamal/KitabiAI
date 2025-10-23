#!/bin/bash
# deploy_toc_fix.sh
# Script to deploy English TOC extraction improvements

set -e  # Exit on error

echo "=========================================="
echo "English PDF TOC Extraction Fix Deployment"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "app" ]; then
    echo -e "${RED}Error: 'app' directory not found. Please run this script from the project root.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Backing up existing files...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "app/services/toc_extractor.py" ]; then
    cp app/services/toc_extractor.py "$BACKUP_DIR/"
    echo "  ✓ Backed up toc_extractor.py"
fi

if [ -f "app/routers/upload.py" ]; then
    cp app/routers/upload.py "$BACKUP_DIR/"
    echo "  ✓ Backed up upload.py"
fi

echo -e "${GREEN}  Backup created in: $BACKUP_DIR${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing new files...${NC}"

# Copy new EnglishTocExtractor
if [ -f "english_toc_extractor.py" ]; then
    cp english_toc_extractor.py app/services/
    echo "  ✓ Installed english_toc_extractor.py"
else
    echo -e "${RED}  ✗ english_toc_extractor.py not found in current directory${NC}"
    exit 1
fi

# Update existing files
if [ -f "toc_extractor.py" ]; then
    cp toc_extractor.py app/services/
    echo "  ✓ Updated toc_extractor.py"
else
    echo -e "${RED}  ✗ toc_extractor.py not found in current directory${NC}"
    exit 1
fi

if [ -f "upload.py" ]; then
    cp upload.py app/routers/
    echo "  ✓ Updated upload.py"
else
    echo -e "${RED}  ✗ upload.py not found in current directory${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 3: Validating Python syntax...${NC}"

# Check if Python is available
if command -v python3 &> /dev/null; then
    python3 -m py_compile app/services/english_toc_extractor.py && echo "  ✓ english_toc_extractor.py - OK" || echo "  ✗ Syntax error"
    python3 -m py_compile app/services/toc_extractor.py && echo "  ✓ toc_extractor.py - OK" || echo "  ✗ Syntax error"
    python3 -m py_compile app/routers/upload.py && echo "  ✓ upload.py - OK" || echo "  ✗ Syntax error"
else
    echo -e "${YELLOW}  ⚠ Python3 not found, skipping syntax validation${NC}"
fi

echo ""
echo -e "${YELLOW}Step 4: Checking dependencies...${NC}"

if [ -f "requirements.txt" ]; then
    # Check if required packages are listed
    if grep -q "pymupdf" requirements.txt && \
       grep -q "fastapi" requirements.txt && \
       grep -q "azure-ai-documentintelligence" requirements.txt; then
        echo "  ✓ All required packages found in requirements.txt"
    else
        echo -e "${YELLOW}  ⚠ Some packages might be missing from requirements.txt${NC}"
        echo "    Required: pymupdf, fastapi, azure-ai-documentintelligence"
    fi
else
    echo -e "${YELLOW}  ⚠ requirements.txt not found${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Deployment completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart your application:"
echo "   - Docker: docker-compose restart"
echo "   - Local:  pkill -f uvicorn && uvicorn app.main:app --reload"
echo ""
echo "2. Test with an English PDF that has chapter headings"
echo ""
echo "3. Download the sections.jsonl file and verify multiple sections"
echo ""
echo "4. If issues occur, restore from backup:"
echo "   cp $BACKUP_DIR/* app/services/"
echo "   cp $BACKUP_DIR/upload.py app/routers/"
echo ""
echo -e "${YELLOW}Backup location: $BACKUP_DIR${NC}"
echo ""