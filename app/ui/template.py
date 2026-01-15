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
input[type="text"],
textarea {
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg);
    color: var(--ink);
    font-size: 14px;
    width: 100%;
    font-family: inherit;
}
input[type="file"] {
    border-style: dashed;
}
input[type="text"]:focus,
textarea:focus {
    outline: none;
    border-color: var(--accent);
}
input[type="text"]::placeholder,
textarea::placeholder {
    color: #9ca3af;
}
textarea {
    resize: vertical;
    min-height: 80px;
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
/* Loading Spinner */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
}
button.loading {
    opacity: 0.7;
    cursor: not-allowed;
    pointer-events: none;
}
button.loading:hover {
    transform: none;
}
.loading-message {
    font-size: 13px;
    color: var(--muted);
    margin-top: 12px;
    text-align: center;
    font-style: italic;
}
</style>
<script>
// Loading state handlers for forms
document.addEventListener('DOMContentLoaded', function() {
    // Handle SEO checkbox toggle
    const seoCheckbox = document.getElementById('enable_seo');
    const seoFields = document.getElementById('seo-fields');

    if (seoCheckbox && seoFields) {
        seoCheckbox.addEventListener('change', function() {
            if (this.checked) {
                seoFields.style.display = 'block';
                // Smooth slide animation
                seoFields.style.opacity = '0';
                seoFields.style.transform = 'translateY(-10px)';
                setTimeout(function() {
                    seoFields.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    seoFields.style.opacity = '1';
                    seoFields.style.transform = 'translateY(0)';
                }, 10);
            } else {
                seoFields.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                seoFields.style.opacity = '0';
                seoFields.style.transform = 'translateY(-10px)';
                setTimeout(function() {
                    seoFields.style.display = 'none';
                }, 200);
            }
        });
    }

    // Handle TOC method radio buttons toggle
    const tocMethodRadios = document.querySelectorAll('input[name="toc_method"]');
    const extractOptions = document.getElementById('extract-options');
    const extractLabel = document.getElementById('toc-extract-label');
    const generateLabel = document.getElementById('toc-generate-label');

    if (tocMethodRadios.length > 0 && extractOptions) {
        tocMethodRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (this.value === 'extract') {
                    // Show extraction options
                    extractOptions.style.display = 'block';
                    extractOptions.style.opacity = '0';
                    extractOptions.style.transform = 'translateY(-10px)';
                    setTimeout(function() {
                        extractOptions.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        extractOptions.style.opacity = '1';
                        extractOptions.style.transform = 'translateY(0)';
                    }, 10);
                    // Update border colors
                    if (extractLabel) extractLabel.style.borderColor = 'var(--accent)';
                    if (generateLabel) generateLabel.style.borderColor = 'var(--border)';
                } else {
                    // Hide extraction options
                    extractOptions.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                    extractOptions.style.opacity = '0';
                    extractOptions.style.transform = 'translateY(-10px)';
                    setTimeout(function() {
                        extractOptions.style.display = 'none';
                    }, 200);
                    // Update border colors
                    if (extractLabel) extractLabel.style.borderColor = 'var(--border)';
                    if (generateLabel) generateLabel.style.borderColor = 'var(--accent)';
                }
            });
        });

        // Set initial state (extract is checked by default)
        if (extractLabel) extractLabel.style.borderColor = 'var(--accent)';
    }

    // Handle upload form
    const uploadForm = document.querySelector('form[action="/upload"]');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('loading')) {
                submitBtn.classList.add('loading');
                submitBtn.innerHTML = '<span class="spinner"></span>Analyzing PDF...';

                // Add loading message
                let loadingMsg = uploadForm.querySelector('.loading-message');
                if (!loadingMsg) {
                    loadingMsg = document.createElement('div');
                    loadingMsg.className = 'loading-message';
                    loadingMsg.textContent = 'Please wait, this may take 10-30 seconds for large files';
                    submitBtn.parentNode.appendChild(loadingMsg);
                }
            }
        });
    }

    // Handle HTML generation form - Open tab immediately to avoid pop-up blocker
    const htmlForm = document.querySelector('form[action="/generate/html"]');
    if (htmlForm) {
        htmlForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Stop default form submission

            const submitBtn = htmlForm.querySelector('button[type="submit"]');
            if (submitBtn.classList.contains('loading')) {
                return; // Prevent double-clicks
            }

            // Show loading state
            const originalHTML = submitBtn.innerHTML;
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<span class="spinner"></span>Generating Web Page...';

            let loadingMsg = htmlForm.querySelector('.loading-message');
            if (!loadingMsg) {
                loadingMsg = document.createElement('div');
                loadingMsg.className = 'loading-message';
                loadingMsg.textContent = 'Please wait while we generate your web page...';
                submitBtn.parentNode.appendChild(loadingMsg);
            }

            // Open new tab IMMEDIATELY (before fetch) to avoid pop-up blocker
            const newTab = window.open('about:blank', '_blank');
            if (newTab) {
                newTab.document.write('<html><body><h2>Generating your web page...</h2><p>Please wait...</p></body></html>');
            }

            // Submit via AJAX
            fetch('/generate/html', {
                method: 'POST',
                headers: {
                    'Accept': 'text/html'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Generation failed');
                }
                return response.text();
            })
            .then(html => {
                // Write content to the already-open tab
                if (newTab && !newTab.closed) {
                    newTab.document.open();
                    newTab.document.write(html);
                    newTab.document.close();
                }

                // Reset button
                submitBtn.classList.remove('loading');
                submitBtn.innerHTML = originalHTML;
                if (loadingMsg) {
                    loadingMsg.remove();
                }
            })
            .catch(error => {
                console.error('Error:', error);

                // Close the blank tab on error
                if (newTab && !newTab.closed) {
                    newTab.close();
                }

                alert('Failed to generate web page. Please try again.');

                // Reset button
                submitBtn.classList.remove('loading');
                submitBtn.innerHTML = originalHTML;
                if (loadingMsg) {
                    loadingMsg.remove();
                }
            });
        });
    }

    // Handle Markdown generation form - Show spinner then allow download
    const markdownForm = document.querySelector('form[action="/generate/markdown"]');
    if (markdownForm) {
        markdownForm.addEventListener('submit', function(e) {
            const submitBtn = markdownForm.querySelector('button[type="submit"]');
            if (submitBtn.classList.contains('loading')) {
                e.preventDefault();
                return; // Prevent double-clicks
            }

            // Prevent default briefly to show spinner
            e.preventDefault();

            // Show loading state
            const originalHTML = submitBtn.innerHTML;
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<span class="spinner"></span>Generating Markdown...';

            let loadingMsg = markdownForm.querySelector('.loading-message');
            if (!loadingMsg) {
                loadingMsg = document.createElement('div');
                loadingMsg.className = 'loading-message';
                loadingMsg.textContent = 'Your download will start shortly...';
                submitBtn.parentNode.appendChild(loadingMsg);
            }

            // Let spinner show, then submit form after brief delay
            setTimeout(function() {
                // Create and submit a temporary form to trigger download
                const tempForm = document.createElement('form');
                tempForm.method = 'POST';
                tempForm.action = '/generate/markdown';
                tempForm.style.display = 'none';
                document.body.appendChild(tempForm);
                tempForm.submit();
                document.body.removeChild(tempForm);
            }, 100);

            // Auto-reset after 4 seconds
            setTimeout(function() {
                submitBtn.classList.remove('loading');
                submitBtn.innerHTML = originalHTML;
                if (loadingMsg) {
                    loadingMsg.remove();
                }
            }, 4000);
        });
    }
});

// Function to generate and save all files
function generateAndSaveAll() {
    const button = event.target;
    const statusDiv = document.getElementById('save-status');

    // Disable button and show loading
    button.disabled = true;
    button.classList.add('loading');
    button.innerHTML = '<span class="spinner"></span>Generating & Saving Files...';
    statusDiv.innerHTML = '<span style="color: var(--muted);">⏳ Please wait, this may take 10-30 seconds...</span>';

    // Call the /generate/both endpoint
    fetch('/generate/both', {
        method: 'POST',
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Generation failed');
        }
        return response.json();
    })
    .then(data => {
        // Success! Show results
        button.classList.remove('loading');
        button.innerHTML = '✅ Success! Files Generated & Saved';
        button.style.background = '#16a34a';

        // Display success message with file details
        const fileList = data.files.map(f => {
            const sizeKB = (f.size_bytes / 1024).toFixed(1);
            return `<li><strong>${f.format}</strong>: ${f.filename} (${sizeKB} KB)</li>`;
        }).join('');

        statusDiv.innerHTML = `
            <div style="padding: 12px; background: #f0fdf4; border: 1px solid #4ade80; border-radius: 8px; text-align: left; margin-top: 12px;">
                <p style="margin: 0 0 8px; color: #166534; font-weight: 600;">✅ Success! All files saved to database</p>
                <p style="margin: 0 0 8px; font-size: 12px; color: #166534;">
                    <strong>Book ID:</strong> ${data.book_id} |
                    <strong>Sections:</strong> ${data.sections_count}
                </p>
                <ul style="margin: 8px 0 0; padding-left: 20px; font-size: 12px; color: #166534;">
                    ${fileList}
                </ul>
                <p style="margin: 8px 0 0; font-size: 11px; color: #166534;">
                    📁 Files saved to: <code>outputs/books/${data.book_id}/</code>
                </p>
            </div>
        `;

        // Re-enable button after 5 seconds
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = '💾 Generate All Files & Save to Database';
            button.style.background = '#16a34a';
        }, 5000);
    })
    .catch(error => {
        // Error handling
        button.classList.remove('loading');
        button.disabled = false;
        button.innerHTML = '❌ Generation Failed - Try Again';
        button.style.background = '#dc2626';

        statusDiv.innerHTML = `
            <div style="padding: 12px; background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; text-align: left;">
                <p style="margin: 0; color: #dc2626; font-weight: 600;">❌ Error: ${error.message}</p>
                <p style="margin: 8px 0 0; font-size: 12px; color: #dc2626;">
                    Make sure you uploaded a PDF first, then try again.
                </p>
            </div>
        `;

        // Reset button after 5 seconds
        setTimeout(() => {
            button.innerHTML = '💾 Generate All Files & Save to Database';
            button.style.background = '#16a34a';
        }, 5000);
    });
}
</script>
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

            <!-- Collapsible: What Books Work Best -->
            <details style="margin: 20px 0;">
              <summary>📖 What Books Work Best?</summary>
              <div style="padding: 16px; background: var(--bg); border-radius: 8px; margin-top: 8px;">
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div style="display: flex; align-items: start; gap: 10px;">
                    <span style="color: #16a34a; font-size: 18px; flex-shrink: 0;">✅</span>
                    <div>
                      <strong style="color: var(--ink);">Modern printed books</strong>
                      <div style="color: var(--muted); font-size: 14px;">Full automatic processing</div>
                    </div>
                  </div>
                  <div style="display: flex; align-items: start; gap: 10px;">
                    <span style="color: #d97706; font-size: 18px; flex-shrink: 0;">⚠️</span>
                    <div>
                      <strong style="color: var(--ink);">Older printed books</strong>
                      <div style="color: var(--muted); font-size: 14px;">Mostly works, may need review</div>
                    </div>
                  </div>
                  <div style="display: flex; align-items: start; gap: 10px;">
                    <span style="color: #667eea; font-size: 18px; flex-shrink: 0;">💡</span>
                    <div>
                      <strong style="color: var(--ink);">Ancient manuscripts</strong>
                      <div style="color: var(--muted); font-size: 14px;">Manual TOC input (coming soon!)</div>
                    </div>
                  </div>
                </div>
              </div>
            </details>

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

      <!-- Cover Image Upload Section (Optional) -->
      <div class="form-section">
        <label>
          🖼️ Book Cover Image (Optional)
        </label>
        <input name="cover_image" type="file" accept="image/*" />
        <p style="font-size: 12px; color: var(--muted); margin: 6px 0 0;">
          Upload a cover image (JPG, PNG, etc.). If not provided, you can add it later.
        </p>
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
          <strong>📝 Metadata Note:</strong> Only the title is required. Additional details help improve discoverability.
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
      </div>

      <!-- SEO Metadata Section -->
      <div class="form-section metadata-section">
        <h3>🔍 SEO & Discoverability (Optional)</h3>

        <!-- Checkbox to enable SEO -->
        <div style="margin-bottom: 16px;">
          <label style="display: flex; align-items: center; cursor: pointer; font-size: 14px;">
            <input type="checkbox" name="enable_seo" id="enable_seo" value="true" style="width: auto; margin-right: 10px; cursor: pointer;" />
            <span style="font-weight: 600; color: var(--ink);">☑ Optimize for search engines (recommended)</span>
          </label>
          <div class="help-text" style="margin-left: 28px; margin-top: 6px;">
            Adds meta tags and structured data to help readers discover this book online through Google, Bing, and other search engines.
          </div>
        </div>

        <!-- Collapsible SEO fields (hidden by default) -->
        <div id="seo-fields" style="display: none; margin-top: 16px;">
          <div class="form-row">
            <div>
              <label>Book Description</label>
              <textarea name="description" placeholder="Brief description of the book content (max 160 characters recommended for SEO)" maxlength="160" rows="3"></textarea>
              <div class="help-text">This appears in search engine results. Keep it concise and compelling.</div>
            </div>
          </div>

          <div class="form-row">
            <div>
              <label>Category / Subject</label>
              <input type="text" name="category" placeholder="e.g., Philosophy, History, Islamic Studies, Science" />
              <div class="help-text">Main subject area or genre</div>
            </div>
          </div>

          <div class="form-row">
            <div>
              <label>Keywords / Tags</label>
              <input type="text" name="keywords" placeholder="e.g., medieval history, Arabic literature, philosophy" />
              <div class="help-text">Comma-separated keywords that describe the book's topics</div>
            </div>
          </div>

          <div class="form-row">
            <div>
              <label>Publication Date</label>
              <input type="text" name="publication_date" placeholder="e.g., 2024 or January 2024 (optional)" />
              <div class="help-text">When the book was published</div>
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
      </div>

      <!-- TOC Method Selection -->
      <div class="form-section metadata-section">
        <h3>📑 Table of Contents Method</h3>

        <div class="info-box" style="margin-top: 0; margin-bottom: 16px; background: #f0f9ff;">
          <strong>💡 Choose how to build the Table of Contents:</strong><br>
          • <strong>Extract from book</strong>: Uses existing TOC page in the book (best for books with clear TOC)<br>
          • <strong>Generate from headings</strong>: Detects chapter titles throughout the book (best for books without TOC or old scans)
        </div>

        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
          <label style="display: flex; align-items: flex-start; cursor: pointer; padding: 12px; border: 2px solid var(--border); border-radius: 8px; transition: all 0.2s;" class="toc-method-option" id="toc-extract-label">
            <input type="radio" name="toc_method" value="extract" checked style="width: auto; margin-right: 12px; margin-top: 2px;" />
            <div>
              <span style="font-weight: 600; color: var(--ink);">Extract TOC from book</span>
              <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                Searches for existing Table of Contents page and extracts chapter titles with page numbers.
                Works best for modern printed books with clear TOC structure.
              </div>
            </div>
          </label>

          <label style="display: flex; align-items: flex-start; cursor: pointer; padding: 12px; border: 2px solid var(--border); border-radius: 8px; transition: all 0.2s;" class="toc-method-option" id="toc-generate-label">
            <input type="radio" name="toc_method" value="generate" style="width: auto; margin-right: 12px; margin-top: 2px;" />
            <div>
              <span style="font-weight: 600; color: var(--ink);">Generate TOC from headings</span>
              <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
                Detects chapter titles and section headings throughout the document using AI.
                Best for books without formal TOC, old scans, or when page numbers don't match.
              </div>
            </div>
          </label>
        </div>

        <!-- Extraction-specific options (shown when "extract" is selected) -->
        <div id="extract-options" style="margin-top: 16px; padding: 16px; background: var(--bg); border-radius: 8px;">
          <h4 style="margin: 0 0 12px; font-size: 14px; color: var(--muted);">Extraction Options</h4>

          <div class="form-row">
            <div>
              <label>TOC Page Number</label>
              <input type="number" name="toc_page" placeholder="e.g., 345 (optional)" min="1" />
              <div class="help-text">Page number where the Table of Contents is located (enables table-based extraction)</div>
            </div>
          </div>

          <div class="form-row" style="margin-top: 12px;">
            <div>
              <label>Page Offset</label>
              <input type="number" name="page_offset" placeholder="e.g., 14 (optional)" min="0" value="0" />
              <div class="help-text">Offset between book page numbers and PDF page numbers (default: 0)</div>
            </div>
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

      <!-- NEW PRIMARY: Generate & Save All Files -->
      <div style="padding: 16px; background: #f0fdf4; border: 2px solid #4ade80; border-radius: 12px; margin-bottom: 20px;">
        <h4 style="font-size: 15px; color: #166534; margin: 0 0 8px; font-weight: 700;">
          ✨ Recommended: Generate & Save All Files
        </h4>
        <p style="font-size: 13px; color: #166534; margin: 0 0 12px;">
          Generates HTML, Markdown, and data exports • Saves to database • Ready for deployment
        </p>
        <button type="button" onclick="generateAndSaveAll()" class="gen-button-primary" style="background: #16a34a; width: 100%;">
          💾 Generate All Files & Save to Database
        </button>
        <div id="save-status" style="margin-top: 12px; font-size: 13px; text-align: center;"></div>
      </div>

      <!-- Quick Preview Options -->
      <div style="padding: 16px; background: #fef9f3; border: 1px solid var(--border); border-radius: 12px;">
        <h4 style="font-size: 14px; color: var(--muted); margin: 0 0 12px; font-weight: 600;">
          Quick Preview (Browser Only - Not Saved)
        </h4>

        <form action="/generate/html" method="post" style="margin: 0 0 12px;">
          <button type="submit" class="gen-button-secondary">
            🌐 Preview Web Page
          </button>
        </form>

        <form action="/generate/markdown" method="post" style="margin: 0;">
          <button type="submit" class="gen-button-secondary">
            📝 Download Markdown
          </button>
        </form>

        <p style="font-size: 12px; color: var(--warning); margin: 12px 0 0; text-align: center;">
          ⚠️ These options do NOT save to database
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