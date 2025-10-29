#!/usr/bin/env python3
"""Download FastText language identification model."""

import os
import sys
from pathlib import Path

def download_model():
    """Download FastText lid.176.ftz model."""

    # Use current directory for output
    output_path = Path("lid.176.ftz")

    # Remove failed download if exists
    if output_path.exists() and output_path.stat().st_size < 100000:
        output_path.unlink()
        print("Removed incomplete download")

    if output_path.exists():
        print(f"✅ Model already exists: {output_path.absolute()}")
        print(f"   Size: {output_path.stat().st_size:,} bytes")
        return True

    # Direct download link (compressed model, ~900KB)
    url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"

    print(f"Downloading FastText model...")
    print(f"URL: {url}")
    print(f"Output: {output_path.absolute()}")
    print()

    # Try multiple methods
    methods = [
        ("requests library", download_with_requests),
        ("urllib", download_with_urllib),
    ]

    for method_name, method_func in methods:
        print(f"Trying: {method_name}...")
        try:
            success = method_func(url, output_path)
            if success:
                print(f"\n✅ Download successful!")
                print(f"   Method: {method_name}")
                print(f"   Size: {output_path.stat().st_size:,} bytes ({output_path.stat().st_size/1024/1024:.2f} MB)")
                print(f"   Location: {output_path.absolute()}")
                return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue

    # All methods failed
    print("\n❌ All download methods failed")
    print("\n💡 Manual download instructions:")
    print("1. Open in browser: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz")
    print("2. Or visit: https://fasttext.cc/docs/en/language-identification.html")
    print(f"3. Save as: {output_path.absolute()}")
    print()
    print("Alternative (PowerShell):")
    print(f"   Invoke-WebRequest -Uri '{url}' -OutFile '{output_path}'")
    return False


def download_with_requests(url: str, output_path: Path) -> bool:
    """Download using requests library."""
    import requests

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, timeout=60, allow_redirects=True, stream=True)
    response.raise_for_status()

    # Download with progress
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"   Progress: {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)", end='\r')

    print()  # New line after progress

    # Verify size
    if output_path.stat().st_size < 100000:
        output_path.unlink()
        raise Exception(f"File too small: {output_path.stat().st_size} bytes")

    return True


def download_with_urllib(url: str, output_path: Path) -> bool:
    """Download using urllib (no dependencies)."""
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()

        if len(data) < 100000:
            raise Exception(f"File too small: {len(data)} bytes")

        with open(output_path, 'wb') as f:
            f.write(data)

    return True


if __name__ == "__main__":
    print("="*80)
    print("FastText Model Downloader")
    print("="*80)
    print()

    try:
        success = download_model()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user")
        sys.exit(1)
