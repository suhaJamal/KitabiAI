"""
Debug script to see the actual TOC format from your PDF.
Run this to see what the TOC lines look like.
"""

import re
from pathlib import Path
from dotenv import load_dotenv
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# Load Azure credentials
load_dotenv()
endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

# Load your PDF
pdf_path = "ar_1.pdf"  # Change this to your PDF path

with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=f.read()
    )

result = poller.result()

# Extract all text
all_text = ""
for page in result.pages:
    for line in page.lines:
        all_text += line.content + "\n"

print(f"Total extracted text length: {len(all_text)} characters")
print(f"\n{'='*80}\n")

# Find TOC header
TOC_PATTERNS = [
    r"المحتويات",
    r"فهرس",
    r"فهرس\s+المحتويات",
    r"جدول\s+المحتويات",
]
toc_regex = re.compile("|".join(TOC_PATTERNS))

# Search in beginning
beginning_text = all_text[:len(all_text)//3]
toc_match = toc_regex.search(beginning_text)

if toc_match:
    print(f"✅ Found TOC header: '{toc_match.group()}'")
    print(f"\n{'='*80}\n")
    
    # Get text after header
    toc_start = toc_match.start()
    sample_after = beginning_text[toc_start:]
    
    # Get first 50 lines after the header
    lines = sample_after.split("\n")
    
    print("First 50 lines after TOC header:")
    print(f"\n{'='*80}\n")
    
    for i, line in enumerate(lines[:50], 1):
        line = line.strip()
        if line:
            print(f"{i:3d}. [{len(line):3d} chars] {line}")
            
    print(f"\n{'='*80}\n")
    print("\nNow let's see which pattern matches:")
    print(f"\n{'='*80}\n")
    
    # Test different patterns
    patterns = {
        "Original (2+ spaces/dots + digits)": r".+[\s\.]{2,}[\u0660-\u0669\d]+$",
        "Any whitespace + digits at end": r".+\s+[\u0660-\u0669\d]+$",
        "Just ends with digits": r".+[\u0660-\u0669\d]+$",
        "Line with digits anywhere": r".*[\u0660-\u0669\d]+.*",
    }
    
    for pattern_name, pattern in patterns.items():
        regex = re.compile(pattern)
        matches = [line.strip() for line in lines[1:30] if line.strip() and regex.match(line.strip())]
        print(f"\n{pattern_name}:")
        print(f"  Matched {len(matches)} lines")
        if matches:
            print(f"  Examples:")
            for match in matches[:3]:
                print(f"    - {match}")
else:
    print("❌ No TOC header found in beginning")
    print("\nSearching in end of book...")
    
    end_text = all_text[int(len(all_text)*0.8):]
    toc_match = toc_regex.search(end_text)
    
    if toc_match:
        print(f"✅ Found TOC header at end: '{toc_match.group()}'")
    else:
        print("❌ No TOC header found anywhere")