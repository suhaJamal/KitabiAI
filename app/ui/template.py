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
    --bg: #f9f7f4;
    --card: #ffffff;
    --ink: #2c2415;
    --muted: #6b5d4d;
    --accent: #c76a2d;
    --accent-light: #e88d51;
    --success: #4a7c59;
    --warning: #d97706;
    --border: #e5ddd4;
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
    box-shadow: 0 2px 8px rgba(44, 36, 21, 0.08);
    border: 1px solid var(--border);
}
h1 { margin: 0 0 8px; font-size: 28px; color: var(--ink);}
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
    color: #dc2626;
}
input[type="file"],
input[type="text"] {
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg);
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
    color: #9ca3af;
}
.help-text {
    font-size: 12px;
    color: var(--muted);
    margin-top: 4px;
}
button {
    background: var(--accent);
    border: 0;
    color: white;
    padding: 12px 16px;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
    font-size: 15px;
    transition: all 0.2s;
}
button:hover {
    background: var(--accent-light);
    transform: translateY(-1px);
}
button.secondary {
    background: #f3f1ed;
    color: var(--accent);
    border: 1px solid var(--border);
}
button.secondary:hover {
    background: #e8e4dd;
}
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}
.badge.ok { background: #d1fae5; color: #065f46; }
.badge.err { background: #fee2e2; color: #991b1b; }
.badge.mix { background: #e9d5ff; color: #6b21a8; }
.badge.arabic { background: #dbeafe; color: #1e40af; }
.badge.english { background: #d1fae5; color: #065f46; }
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
}
th, td {
    text-align: left;
    padding: 10px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
}
th {
    color: var(--muted);
    font-weight: 600;
    background: var(--bg);
}
.kv {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 8px;
    margin-top: 16px;
}
.kv div {
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
}
.footer {
    margin-top: 18px;
    color: var(--muted);
    font-size: 13px;
}
.info-box {
    background: #fef3e7;
    border-left: 4px solid var(--accent);
    padding: 12px;
    margin-top: 16px;
    border-radius: 4px;
}
.metadata-section {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}
.generation-section {
    background: #fef9f3;
    border: 2px solid var(--accent);
    border-radius: 12px;
    padding: 20px;
    margin-top: 24px;
}
.generation-section h3 {
    margin: 0 0 16px;
    color: var(--accent);
    font-size: 18px;
}
.button-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 12px;
}
.gen-button {
    background: var(--accent);
    color: white;
    padding: 14px 20px;
    border-radius: 10px;
    text-decoration: none;
    font-weight: 700;
    text-align: center;
    transition: all 0.2s;
    display: block;
    border: 0;
    cursor: pointer;
}
.gen-button:hover {
    background: var(--accent-light);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(199, 106, 45, 0.3);
}
.gen-button.secondary {
    background: white;
    color: var(--accent);
    border: 2px solid var(--accent);
}
.gen-button.secondary:hover {
    background: #fef9f3;
}
code {
    background: var(--bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    color: var(--accent);
}
a {
    color: var(--accent);
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
/* Collapsible Details */
details {
    margin-top: 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}
details summary {
    cursor: pointer;
    color: var(--accent);
    font-weight: 600;
    padding: 14px 16px;
    background: var(--bg);
    list-style: none;
    user-select: none;
    transition: background 0.2s;
}
details summary:hover {
    background: #f3f1ed;
}
details summary::-webkit-details-marker {
    display: none;
}
details summary::before {
    content: '▶';
    display: inline-block;
    margin-right: 8px;
    transition: transform 0.2s;
}
details[open] summary::before {
    transform: rotate(90deg);
}
details[open] summary {
    border-bottom: 1px solid var(--border);
}
/* Primary/Secondary Generation Buttons */
.gen-button-primary {
    background: var(--accent);
    color: white;
    padding: 18px 24px;
    font-size: 18px;
    border-radius: 12px;
    font-weight: 700;
    width: 100%;
    border: 0;
    cursor: pointer;
    transition: all 0.2s;
}
.gen-button-primary:hover {
    background: var(--accent-light);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(199, 106, 45, 0.4);
}
.gen-button-secondary {
    background: white;
    color: var(--accent);
    padding: 12px 20px;
    font-size: 14px;
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid var(--border);
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
}
.gen-button-secondary:hover {
    background: var(--bg);
    border-color: var(--accent);
}
.divider-section {
    border-top: 1px solid var(--border);
    padding-top: 20px;
    margin-top: 20px;
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
        <div class="info-box" style="margin-top: 0; margin-bottom: 16px; background: #fef3e7;">
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
    """Render analysis report with language detection, book metadata, and generation options."""
    
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
    
    # Generation section
    generation_html = """
    <div class="generation-section">
      <h3>🎨 Generate Book Formats</h3>
      <p style="color: var(--muted); margin: 0 0 20px;">Transform your PDF into beautiful, readable formats</p>

      <!-- PRIMARY: Web Page Generation -->
      <form action="/generate/html" method="post" target="_blank" style="margin: 0;">
        <button type="submit" class="gen-button-primary">
          🌐 Generate Web Page
        </button>
      </form>
      <p style="font-size: 13px; color: var(--muted); margin: 8px 0 0; text-align: center;">
        Creates an SEO-friendly HTML version for web publishing
      </p>

      <!-- SECONDARY: Markdown (Advanced) -->
      <div class="divider-section">
        <h4 style="font-size: 14px; color: var(--muted); margin: 0 0 12px; font-weight: 600;">
          Advanced: Developer Format
        </h4>
        <form action="/generate/markdown" method="post" style="margin: 0;">
          <button type="submit" class="gen-button-secondary">
            📝 Generate Markdown
          </button>
        </form>
        <p style="font-size: 12px; color: var(--muted); margin: 8px 0 0;">
          For developers and content editors - includes YAML frontmatter & structured TOC
        </p>
      </div>
    </div>
    """
    
    body = f"""
      {metadata_html}
      
      <h2 style="font-size: 18px; margin-bottom: 12px; color: var(--accent);">📊 Analysis Report</h2>
      <div class="kv">
        <div><strong>File name</strong></div><div>{filename}</div>
        <div><strong>Language</strong></div><div>{language_badge}</div>
        <div><strong>Pages</strong></div><div>{report.num_pages}</div>
        <div><strong>Classification</strong></div><div>{classification_badge}</div>
      </div>

      <details>
        <summary>Show Page-by-Page Details ({report.num_pages} pages)</summary>
        <table>
          <thead><tr><th>Page</th><th>Has Text</th><th>Image Count</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </details>

      {generation_html}
      
      <div class="info-box" style="margin-top: 20px;">
        <strong>📥 Raw Data Export Options:</strong><br>
        • <a href="/export/jsonl">Download page-level data (JSONL)</a><br>
        • <a href="/export/sections.jsonl">Download TOC/sections (JSONL)</a><br>
        • <a href="/info">Get metadata (JSON)</a>
      </div>
    """
    return body