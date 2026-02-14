# evaluation/compare.py
"""
Compare TOC extraction/generation results against manual ground truth.

Compares by page number matching (±1 page tolerance) since Arabic titles
may differ slightly between OCR output and manual transcription.

Usage:
    python -m evaluation.compare
    python -m evaluation.compare --book "اللابس المتلبس"
"""

import json
import os
import sys
import re
import argparse
from pathlib import Path

# Fix Windows console encoding for Arabic text
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

EVAL_DIR = Path(__file__).parent
MANUAL_INDEX = EVAL_DIR / "manual_index.json"

# Method suffixes used in book titles
METHOD_SUFFIXES = ["-auto", "-extract", "-generate"]


def load_manual_index():
    """Load manual ground truth from manual_index.json."""
    with open(MANUAL_INDEX, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Index by book title
    return {book["book_title"]: book["chapters"] for book in data["books"]}


def strip_method_suffix(title):
    """Strip -auto/-extract/-generate suffix from book title."""
    for suffix in METHOD_SUFFIXES:
        if title.endswith(suffix):
            return title[:-len(suffix)].strip(), suffix[1:]
    return title, None


def find_eval_files(book_filter=None):
    """
    Find all eval JSON files and group by base book title.

    Returns:
        dict: {base_title: {method: filepath, ...}, ...}
    """
    results = {}

    for f in EVAL_DIR.glob("toc_eval_*.json"):
        with open(f, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError:
                continue

        raw_title = data.get("book_title", "")
        base_title, suffix_method = strip_method_suffix(raw_title)

        # Determine actual method from file content
        method_field = data.get("method", "")
        if suffix_method:
            method = suffix_method
        elif "generate" in method_field:
            method = "generate"
        elif "auto" in method_field:
            method = "auto"
        else:
            method = "extract"

        if book_filter and base_title != book_filter:
            continue

        if base_title not in results:
            results[base_title] = {}
        results[base_title][method] = {
            "filepath": str(f),
            "data": data
        }

    return results


def compare_sections(system_sections, ground_truth, page_tolerance=1):
    """
    Compare system-extracted sections against ground truth.

    Matching criteria: page numbers within ±tolerance.
    Only compares level 1 sections (or all if ground truth has no levels).

    Returns:
        dict with precision, recall, f1, matched, missed, extra
    """
    # Ground truth pages
    gt_pages = []
    for ch in ground_truth:
        page = ch.get("page")
        if page is not None:
            gt_pages.append(page)

    # System pages
    sys_pages = []
    for sec in system_sections:
        page = sec.get("page_start")
        if page is not None:
            sys_pages.append(page)

    # Match: for each ground truth page, check if any system page is within tolerance
    matched_gt = set()
    matched_sys = set()

    for i, gt_p in enumerate(gt_pages):
        for j, sys_p in enumerate(sys_pages):
            if j in matched_sys:
                continue
            if abs(gt_p - sys_p) <= page_tolerance:
                matched_gt.add(i)
                matched_sys.add(j)
                break

    true_positives = len(matched_gt)
    false_negatives = len(gt_pages) - true_positives  # missed ground truth
    false_positives = len(sys_pages) - len(matched_sys)  # extra system sections

    precision = true_positives / len(sys_pages) if sys_pages else 0
    recall = true_positives / len(gt_pages) if gt_pages else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Details: which ground truth chapters were missed
    missed = []
    for i, ch in enumerate(ground_truth):
        if ch.get("page") is not None and i not in matched_gt:
            missed.append(ch)

    # Details: which system sections are extra
    extra = []
    for j, sec in enumerate(system_sections):
        if sec.get("page_start") is not None and j not in matched_sys:
            extra.append(sec)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": true_positives,
        "ground_truth_count": len(gt_pages),
        "system_count": len(sys_pages),
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "missed": missed,
        "extra": extra,
    }


def print_comparison(base_title, methods_data, ground_truth):
    """Print comparison results for one book across all methods."""
    print(f"\n{'='*70}")
    print(f"Book: {base_title}")
    print(f"Ground truth chapters: {len(ground_truth)}")
    print(f"{'='*70}")

    for method in ["auto", "extract", "generate"]:
        if method not in methods_data:
            print(f"\n  [{method.upper()}] — No eval file found")
            continue

        data = methods_data[method]["data"]
        sections = data.get("final_sections", [])

        print(f"\n  [{method.upper()}]")
        print(f"  Strategy: {data.get('strategy_used', data.get('method', '?'))}")
        print(f"  Sections found: {len(sections)}")

        if not sections:
            print(f"  Result: No sections extracted — skipping comparison")
            continue

        result = compare_sections(sections, ground_truth)

        print(f"  Precision: {result['precision']:.2%}  ({result['true_positives']}/{result['system_count']} system sections matched)")
        print(f"  Recall:    {result['recall']:.2%}  ({result['true_positives']}/{result['ground_truth_count']} ground truth matched)")
        print(f"  F1 Score:  {result['f1']:.2%}")

        if result["missed"]:
            print(f"  Missed ({result['false_negatives']}):")
            for ch in result["missed"][:5]:
                print(f"    - p.{ch['page']}: {ch['title'][:50]}")
            if len(result["missed"]) > 5:
                print(f"    ... and {len(result['missed']) - 5} more")

        if result["extra"]:
            print(f"  Extra ({result['false_positives']}):")
            for sec in result["extra"][:5]:
                print(f"    - p.{sec['page_start']}: {sec['title'][:50]}")
            if len(result["extra"]) > 5:
                print(f"    ... and {len(result['extra']) - 5} more")


def main():
    parser = argparse.ArgumentParser(description="Compare TOC results against ground truth")
    parser.add_argument("--book", type=str, help="Filter to a specific book title")
    parser.add_argument("--tolerance", type=int, default=1, help="Page matching tolerance (default: ±1)")
    args = parser.parse_args()

    # Load ground truth
    if not MANUAL_INDEX.exists():
        print(f"Error: {MANUAL_INDEX} not found")
        return

    gt_index = load_manual_index()
    print(f"Loaded ground truth for {len(gt_index)} books")

    # Find eval files
    eval_files = find_eval_files(book_filter=args.book)

    if not eval_files:
        print("No evaluation files found in", EVAL_DIR)
        if args.book:
            print(f"(filtered for: {args.book})")
        return

    print(f"Found eval files for {len(eval_files)} book(s)")

    # Compare each book
    summary = []
    for base_title, methods_data in sorted(eval_files.items()):
        if base_title not in gt_index:
            print(f"\n  Warning: No ground truth for '{base_title}' — skipping")
            continue

        ground_truth = gt_index[base_title]
        print_comparison(base_title, methods_data, ground_truth)

        # Collect summary
        for method in ["auto", "extract", "generate"]:
            if method in methods_data:
                sections = methods_data[method]["data"].get("final_sections", [])
                if sections:
                    result = compare_sections(sections, ground_truth, args.tolerance)
                    summary.append({
                        "book": base_title,
                        "method": method,
                        **result
                    })

    # Print summary table
    if summary:
        print(f"\n\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"{'Book':<30} {'Method':<10} {'P':>8} {'R':>8} {'F1':>8} {'Sys':>5} {'GT':>5}")
        print("-" * 70)
        for row in summary:
            book_short = row["book"][:28]
            print(f"{book_short:<30} {row['method']:<10} {row['precision']:>7.1%} {row['recall']:>7.1%} {row['f1']:>7.1%} {row['system_count']:>5} {row['ground_truth_count']:>5}")


if __name__ == "__main__":
    main()