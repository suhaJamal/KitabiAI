#!/usr/bin/env python3
"""Download FastText language identification model."""

import requests
import os

def download_model():
    """Download FastText lid.176.ftz model."""

    # Direct download link (compressed model, ~900KB)
    url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
    output_path = "/outputs/"

    # Remove failed download if exists
    if os.path.exists(output_path) and os.path.getsize(output_path) < 100000:
        os.remove(output_path)
        print("Removed incomplete download")

    if os.path.exists(output_path):
        print(f"✅ Model already exists: {output_path}")
        print(f"   Size: {os.path.getsize(output_path):,} bytes")
        return True

    try:
        print(f"Downloading from: {url}")

        # Use requests with proper headers and follow redirects
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        response.raise_for_status()

        data = response.content

        # Check if we got actual data (model should be ~900KB)
        if len(data) > 100000:  # At least 100KB
            with open(output_path, 'wb') as f:
                f.write(data)
            print(f"✅ Downloaded successfully!")
            print(f"   Size: {len(data):,} bytes ({len(data)/1024/1024:.2f} MB)")
            print(f"   Saved to: {output_path}")
            return True
        else:
            print(f"❌ Downloaded file too small: {len(data)} bytes")
            print(f"   Content preview: {data[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")
        print("\n💡 Alternative solutions:")
        print("1. Manual download: https://fasttext.cc/docs/en/language-identification.html")
        print("2. Use alternative library: langdetect (no model download needed)")
        print("3. Try again later (CDN might be temporarily unavailable)")
        return False

if __name__ == "__main__":
    success = download_model()
    exit(0 if success else 1)
