# app/ui/template.py
"""
Minimal HTML view helpers for the UI.

- html_shell() provides the page chrome (CSS/layout).
- render_home() and render_report() build the body content for routes.
- Keeps HTML/CSS out of the router so it stays clean.
"""

from ..models.schemas import AnalysisReport, BookMetadata


CSS = """
<style>
:root {
    --bg:#0b1020;
    --card:#111935;
    --ink:#e9ecf1;
    --muted:#a8b0c5;
    --accent:#64b5f6;
    --success:#4caf50;
    --warning:#ff9800;
}
* { box-sizing: border-box; }
html, body {
    margin:0;
    padding:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial;
    background: var(--bg);
    color: var(--ink);
}
.container {
    max-width: 900px;
    margin: 40px auto;
    padding: 0 16px;
}
.card {
    background: var(--card);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,.25);
}
h1 { margin: 0 0 8px; font-size: 28px;}
.subtitle {
    color: var(--muted);
    margin-bottom: 20px;
}
form {
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.form-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.form-section h3 {
    margin: 0 0 8px;
    font-size: 16px;
    color: var(--accent);
}
.form-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}
label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 6px;
}
label .required {
    color: #f44336;
}
input[type="file"],
input[type="text"] {
    padding: 10px;
    border: 1px solid #3a4470;
    border-radius: 8px;
    background: #0e1630;
    color: var(--ink);
    font-size: 14px;
    width: 100%;
}
input[type="file"] {
    border-style: dashed;
}
input[type="text"]:focus {
    outline: none;
    border-color: var(--accent);
}
input[type="text"]::placeholder {
    color: #5a6486;
}
.help-text {
    font-size: 12px;
    color: #6a7599;
    margin-top: 4px;
}
button {
    background: var(--accent);
    border: 0;
    color: #07233b;
    padding: 12px 16px;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
    font-size: 15px;
    transition: all 0.2s;
}
button:hover {
    background: #82c9ff;
    transform: translateY(-1px);
}
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}
.badge.ok { background: #2e7d32; color: #c8f7c5; }
.badge.err { background: #b71c1c; color: #ffd6d6; }
.badge.mix { background: #7b1fa2; color: #f4d9ff; }
.badge.arabic { background: #1976d2; color: #bbdefb; }
.badge.english { background: #388e3c; color: #c8e6c9; }
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
}
th, td {
    text-align: left;
    padding: 10px;
    border-bottom: 1px solid #2a335c;
    font-size: 14px;
}
th {
    color: var(--muted);
    font-weight: 600;
}
.kv {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 8px;
    margin-top: 16px;
}
.kv div {
    padding: 6px 0;
    border-bottom: 1px solid #25305a;
}
.footer {
    margin-top: 18px;
    color: var(--muted);
    font-size: 13px;
}
.info-box {
    background: #1a2332;
    border-left: 4px solid var(--accent);
    padding: 12px;
    margin-top: 16px;
    border-radius: 4px;
}
.metadata-section {
    background: #141b2e;
    border: 1px solid #2a335c;
    border-radius: 8px;
    padding: 16px;
}
</style>
"""


def html_shell(body: str) -> str:
    return f"""
    <html>
      <head>
        <title>Book Converter – Unified</title>
        <meta charset="utf-8">
        {CSS}
      </head>
      <body>
        <div class="container">
          <div class="card">
            <h1>📚 Book Converter – Unified (English & Arabic)</h1>
            <div class="subtitle">Upload a PDF → we'll detect the language, verify content, and extract TOC automatically.</div>
            {body}
            <div class="footer">
              💡 Tip: add <code>?json=1</code> to <code>/upload</code> for JSON response. <br>
              📥 Use <code>/export/jsonl</code> for page data, <code>/export/sections.jsonl</code> for TOC.
            </div>
          </div>
        </div>
      </body>
    </html>
    """


def render_home() -> str:
    return """
    <form action="/upload" enctype="multipart/form-data" method="post">
      <!-- PDF File Upload Section -->
      <div class="form-section">
        <label>
          📄 Select PDF File <span class="required">*</span>
        </label>
        <input name="file" type="file" accept=".pdf" required />
      </div>

      <!-- Book Metadata Section -->
      <div class="form-section metadata-section">
        <h3>📋 Book Metadata</h3>
        <div class="info-box" style="margin-top: 0; margin-bottom: 16px; background: #0e1630; border-left-color: #ff9800;">
          <strong>ℹ️ What This Tool Does:</strong><br>
          • Automatically detects language (English/Arabic)<br>
          • Extracts Table of Contents structure<br>
          • Identifies sections and page ranges<br>
          <br>
          <strong>📝 Metadata Note:</strong> To save complete book information, please fill in the fields below. Only the title is required.
        </div>

        <div class="form-row">
          <div>
            <label>
              Book Title <span class="required">*</span>
            </label>
            <input type="text" name="book_title" placeholder="Enter the book title" required />
          </div>
        </div>

        <div class="form-row">
          <div>
            <label>Author Name</label>
            <input type="text" name="author" placeholder="e.g., John Doe (optional)" />
          </div>
        </div>

        <div class="form-row">
          <div>
            <label>Publication Date</label>
            <input type="text" name="publication_date" placeholder="e.g., 2024 or January 2024 (optional)" />
          </div>
        </div>

        <div class="form-row">
          <div>
            <label>ISBN</label>
            <input type="text" name="isbn" placeholder="e.g., 978-3-16-148410-0 (optional)" pattern="[0-9\\-X]{10,17}" />
            <div class="help-text">Format: 10 or 13 digits with optional hyphens</div>
          </div>
        </div>
      </div>

      <!-- Submit Button -->
      <button type="submit">🚀 Upload & Analyze</button>
    </form>

    <div class="info-box">
      <strong>✨ Processing Methods:</strong><br>
      • <strong>English PDFs</strong>: Uses native bookmarks for TOC extraction<br>
      • <strong>Arabic PDFs</strong>: Uses Azure Document Intelligence with pattern-based TOC detection<br>
      • Automatically detects language and routes to appropriate extraction method
    </div>
    """


def render_report(filename: str, report: AnalysisReport, language: str = "unknown", metadata: BookMetadata = None) -> str:
    """Render analysis report with language detection and book metadata."""
    
    # Classification badge
    badge_map = {
        "image_only": "<span class='badge err'>IMAGE-ONLY</span>",
        "text_only": "<span class='badge ok'>TEXT-ONLY</span>",
        "mixed": "<span class='badge mix'>MIXED</span>",
    }
    classification_badge = badge_map.get(report.classification, "")
    
    # Language badge
    language_badge = f"<span class='badge {language}'>{language.upper()}</span>"
    
    # Book metadata section (if provided)
    metadata_html = ""
    if metadata:
        metadata_rows = f"""
            <div><strong>Book Title</strong></div><div>{metadata.title}</div>
        """
        if metadata.author:
            metadata_rows += f"""
            <div><strong>Author</strong></div><div>{metadata.author}</div>
            """
        if metadata.publication_date:
            metadata_rows += f"""
            <div><strong>Publication Date</strong></div><div>{metadata.publication_date}</div>
            """
        if metadata.isbn:
            metadata_rows += f"""
            <div><strong>ISBN</strong></div><div>{metadata.isbn}</div>
            """
        
        metadata_html = f"""
        <div style="margin-bottom: 20px;">
          <h2 style="font-size: 18px; margin-bottom: 12px; color: var(--accent);">📚 Book Information</h2>
          <div class="kv" style="margin-top: 0;">
            {metadata_rows}
          </div>
        </div>
        """
    
    # Table rows
    rows = "\n".join(
        f"<tr><td>{p.page}</td><td>{'Yes' if p.has_text else 'No'}</td><td>{p.image_count}</td></tr>"
        for p in report.pages
    )
    
    body = f"""
      {metadata_html}
      
      <h2 style="font-size: 18px; margin-bottom: 12px; color: var(--accent);">📊 Analysis Report</h2>
      <div class="kv">
        <div><strong>File name</strong></div><div>{filename}</div>
        <div><strong>Language</strong></div><div>{language_badge}</div>
        <div><strong>Pages</strong></div><div>{report.num_pages}</div>
        <div><strong>Classification</strong></div><div>{classification_badge}</div>
      </div>
      <table>
        <thead><tr><th>Page</th><th>Has Text</th><th>Image Count</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <div class="info-box" style="margin-top: 20px;">
        <strong>📥 Export Options:</strong><br>
        • <a href="/export/jsonl" style="color: var(--accent);">Download page-level data (JSONL)</a><br>
        • <a href="/export/sections.jsonl" style="color: var(--accent);">Download TOC/sections (JSONL)</a><br>
        • <a href="/info" style="color: var(--accent);">Get metadata (JSON)</a>
      </div>
    """
    return body