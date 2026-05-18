# app/ui/book_template.py
"""
Renders the public book page with a chat widget and book reader.

UI defaults to English regardless of book language; a toggle lets visitors
switch to Arabic. Book content (title, description, section text) always
renders in the book's own language/direction.
"""
import html as _html_mod
import re as _re

_BULLET_RE  = _re.compile(r'^[-*]\s+(.+)$')
_ORDERED_RE = _re.compile(r'^\d+\.\s+(.+)$')


def render_book_page(book, sections: list, has_embeddings: bool) -> str:
    # Strip TOC method suffix from display title
    display_title = book.title or ""
    for suffix in ('-extract', '-generate', '-auto'):
        if display_title.endswith(suffix):
            display_title = display_title[:-len(suffix)].strip()
            break

    lang = book.language or 'ar'
    book_is_ar = lang == 'ar'
    content_dir = 'rtl' if book_is_ar else 'ltr'   # direction of book content

    author_name   = book.author.name       if book.author       else ''
    category_name = book.category_rel.name if book.category_rel else ''
    description   = book.description or ''
    keywords      = book.keywords or ''

    # ── TOC list ──────────────────────────────────────────────────────────────
    toc_items = ""
    for i, sec in enumerate(sections):
        title = sec.title or ''
        pages_en = pages_ar = ""
        if sec.page_start and sec.page_end:
            pages_en = f'pp. {sec.page_start}–{sec.page_end}'
            pages_ar = f'ص {sec.page_start}–{sec.page_end}'
        elif sec.page_start:
            pages_en = f'p. {sec.page_start}'
            pages_ar = f'ص {sec.page_start}'

        pages_html = (
            f'<span class="sec-pages" data-en="{pages_en}" data-ar="{pages_ar}">{pages_en}</span>'
            if pages_en else ''
        )
        summary_btn = (
            f'<button class="summary-btn" onclick="showSummary({i},event)"'
            f' data-en="Summary" data-ar="ملخص">Summary</button>'
            if sec.summary else ''
        )
        toc_items += (
            f'<li class="toc-item" onclick="openReader({i})" title="{_esc(title)}">'
            f'<span class="sec-title" dir="{content_dir}">{_esc(title)}</span>'
            f'<div class="toc-right">{pages_html}{summary_btn}</div>'
            f'</li>\n'
        )

    # ── Reader sections ───────────────────────────────────────────────────────
    reader_sections_js = []
    for sec in sections:
        title   = _esc(sec.title or '')
        content = sec.content or ''
        if content:
            paragraphs = content.strip().split('\n\n')
            paras_html = ''.join(
                _render_para(p.strip(), content_dir)
                for p in paragraphs if p.strip()
            )
        else:
            paras_html = '<p class="no-content">No content available for this section.</p>'

        js_title   = title.replace('\\', '\\\\').replace('`', '\\`')
        js_content = paras_html.replace('\\', '\\\\').replace('`', '\\`')
        reader_sections_js.append(f'{{title:`{js_title}`,content:`{js_content}`}}')

    reader_sections_json = '[' + ',\n'.join(reader_sections_js) + ']'
    has_reader = len(sections) > 0

    # ── Summaries JS array ────────────────────────────────────────────────────
    summaries_js = []
    for sec in sections:
        if sec.summary:
            s = sec.summary.replace('\\', '\\\\').replace('`', '\\`')
            summaries_js.append(f'`{s}`')
        else:
            summaries_js.append('null')
    summaries_json = '[' + ','.join(summaries_js) + ']'

    # ── Chat widget ───────────────────────────────────────────────────────────
    if has_embeddings:
        chat_widget = """
<div class="chat-container" id="chatContainer">
  <div class="chat-messages" id="chatMessages"></div>
  <div class="chat-input-row">
    <input type="text" id="chatInput" dir="auto"
      placeholder="Type your question here..."
      data-en-placeholder="Type your question here..."
      data-ar-placeholder="اكتب سؤالك هنا..." />
    <button id="askBtn" onclick="askQuestion()" data-en="Ask" data-ar="إرسال">Ask</button>
  </div>
</div>
"""
        chat_script = f"""
const BOOK_ID = {book.id};

function askQuestion() {{
  const input = document.getElementById('chatInput');
  const q = input.value.trim();
  if (!q) return;
  input.value = '';
  appendMessage(q, 'user');
  document.getElementById('askBtn').disabled = true;
  fetch('/api/ask', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{book_id: BOOK_ID, question: q}})
  }})
  .then(r => r.json())
  .then(data => {{ appendMessage(data.answer, 'bot', data.sources || []); }})
  .catch(() => {{
    appendMessage(currentLang === 'ar' ? 'حدث خطأ، حاول مجددًا.' : 'An error occurred, please try again.', 'bot');
  }})
  .finally(() => {{ document.getElementById('askBtn').disabled = false; }});
}}

function appendMessage(text, role, sources) {{
  const box = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = 'msg msg-' + role;
  var isArabicMsg = /[؀-ۿ]/.test(text);
  msg.dir = isArabicMsg ? 'rtl' : 'ltr';
  msg.style.textAlign = isArabicMsg ? 'right' : 'left';
  msg.textContent = text;
  if (sources && sources.length) {{
    const srcDiv = document.createElement('div');
    srcDiv.className = 'msg-sources';
    srcDiv.dir = 'rtl';
    srcDiv.style.textAlign = 'right';
    srcDiv.textContent = (currentLang === 'ar' ? 'المصادر: ' : 'Sources: ') +
      sources.map(s => s.section + ' (' + s.pages + ')').join(' • ');
    msg.appendChild(srcDiv);
  }}
  box.appendChild(msg);
  box.scrollTop = box.scrollHeight;
}}

document.getElementById('chatInput').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter') askQuestion();
}});
"""
    else:
        chat_widget = (
            '<div class="chat-unavailable"'
            ' data-en="AI chat is not yet available for this book."'
            ' data-ar="المساعد الذكي غير متاح لهذا الكتاب بعد.">'
            'AI chat is not yet available for this book.</div>'
        )
        chat_script = ""

    # ── Meta / HTML fragments ─────────────────────────────────────────────────
    meta_description = _esc(description[:200]) if description else _esc(display_title)
    meta_keywords    = _esc(keywords) if keywords else ''

    author_html = (
        f'<div class="meta-row">'
        f'<span class="meta-label" data-en="Author" data-ar="المؤلف">Author</span>: '
        f'<span dir="{content_dir}">{_esc(author_name)}</span></div>'
        if author_name else ''
    )
    category_html = (
        f'<div class="meta-row">'
        f'<span class="meta-label" data-en="Category" data-ar="التصنيف">Category</span>: '
        f'<span dir="{content_dir}">{_esc(category_name)}</span></div>'
        if category_name else ''
    )
    keywords_html = (
        f'<div class="meta-row">'
        f'<span class="meta-label" data-en="Keywords" data-ar="الكلمات المفتاحية">Keywords</span>: '
        f'<span class="keywords" dir="{content_dir}">{_esc(keywords)}</span></div>'
        if keywords else ''
    )
    description_html = (
        f'<p class="book-description" dir="{content_dir}">{_esc(description)}</p>'
        if description else ''
    )

    browse_btn = (
        '<button class="browse-btn" onclick="openReader(0)"'
        ' data-en="Browse Book" data-ar="تصفح الكتاب">Browse Book</button>'
        if has_reader else ''
    )

    toc_block = (
        f'<div class="section-card">'
        f'<div class="section-heading" data-en="Table of Contents" data-ar="فهرس المحتويات">Table of Contents</div>'
        f'<ul class="toc-list">{toc_items}</ul></div>'
        if toc_items else ''
    )

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="description" content="{meta_description}"/>
{'<meta name="keywords" content="' + meta_keywords + '"/>' if meta_keywords else ''}
<title>{_esc(display_title)}</title>
<style>
:root {{
  --bg: #f9f7f4;
  --card: #ffffff;
  --ink: #2c2415;
  --muted: #6b5d4d;
  --accent: #c76a2d;
  --accent-light: #e88d51;
  --border: #e5ddd4;
  --chat-user: #fff3e8;
  --chat-bot: #f0f4ff;
  --reader-bg: #fffdf9;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto,
    'Helvetica Neue', Arial, 'Noto Sans Arabic', sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
}}
.container {{ max-width: 860px; margin: 0 auto; padding: 32px 16px 64px; }}

/* ── Language toggle ── */
.lang-toggle {{
  position: fixed;
  top: 16px;
  inset-inline-end: 16px;
  display: flex;
  gap: 4px;
  z-index: 300;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px;
  box-shadow: 0 2px 8px rgba(44,36,21,.1);
}}
.lang-btn {{
  padding: 4px 12px;
  border-radius: 16px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: transparent;
  color: var(--muted);
  transition: all .15s;
  font-family: inherit;
}}
.lang-btn.active {{ background: var(--accent); color: #fff; }}

/* ── Book header ── */
.book-header {{
  background: var(--card);
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 2px 8px rgba(44,36,21,.08);
  border: 1px solid var(--border);
  margin-bottom: 24px;
}}
.book-title {{ font-size: 26px; font-weight: 700; color: var(--ink); margin-bottom: 12px; }}
.meta-row {{ font-size: 14px; color: var(--muted); margin-bottom: 6px; }}
.meta-label {{ font-weight: 600; color: var(--accent); }}
.book-description {{ margin-top: 14px; font-size: 15px; color: var(--ink); line-height: 1.8; }}
.keywords {{ font-size: 13px; color: var(--muted); }}

/* Browse button */
.browse-btn {{
  display: inline-block; margin-top: 18px; padding: 10px 22px;
  background: var(--accent); color: #fff; border: none; border-radius: 10px;
  font-size: 14px; font-family: inherit; cursor: pointer; transition: background .15s;
}}
.browse-btn:hover {{ background: var(--accent-light); }}

/* ── Section card ── */
.section-card {{
  background: var(--card); border-radius: 16px; padding: 24px;
  box-shadow: 0 2px 8px rgba(44,36,21,.08); border: 1px solid var(--border);
  margin-bottom: 24px;
}}
.section-heading {{ font-size: 16px; font-weight: 700; color: var(--accent); margin-bottom: 16px; }}

/* ── TOC ──
   No flex-direction override here — dir="rtl" on <html> (set by JS) naturally
   reverses flex start/end so sec-title lands on the right in Arabic mode. */
.toc-list {{ list-style: none; padding: 0; }}
.toc-item {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 9px 0;
  border-bottom: 1px solid var(--border);
  gap: 8px;
  cursor: pointer;
}}
.toc-item:last-child {{ border-bottom: none; }}
.toc-item:hover .sec-title {{ color: var(--accent); }}
.sec-title {{ font-size: 14px; color: var(--ink); transition: color .15s; }}
.sec-pages {{ font-size: 12px; color: var(--muted); white-space: nowrap; }}

/* ── Reader overlay ── */
.reader-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(44,36,21,.45); z-index: 100;
  align-items: flex-start; justify-content: center;
  padding: 24px 12px; overflow-y: auto;
}}
.reader-overlay.open {{ display: flex; }}
.reader-modal {{
  background: var(--reader-bg); border-radius: 18px;
  width: 100%; max-width: 720px;
  box-shadow: 0 8px 32px rgba(44,36,21,.22);
  overflow: hidden; min-height: 300px;
  display: flex; flex-direction: column; margin: auto;
}}
.reader-topbar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--border);
  background: var(--card); gap: 12px; flex-wrap: wrap;
}}
.reader-counter {{ font-size: 13px; color: var(--muted); white-space: nowrap; }}
.reader-nav {{ display: flex; gap: 8px; }}
.reader-nav button, .reader-close {{
  padding: 6px 16px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--bg); font-size: 13px; font-family: inherit;
  cursor: pointer; color: var(--ink); transition: background .15s;
}}
.reader-nav button:hover, .reader-close:hover {{ background: var(--border); }}
.reader-nav button:disabled {{ opacity: .4; cursor: default; }}
.reader-close {{ color: #dc2626; border-color: #fca5a5; background: #fff5f5; }}
.reader-close:hover {{ background: #fee2e2; }}
.reader-body {{
  padding: 28px 32px 36px; flex: 1; overflow-y: auto;
  direction: {content_dir};
}}
.reader-section-title {{
  font-size: 20px; font-weight: 700; color: var(--ink);
  margin-bottom: 20px; line-height: 1.5;
}}
.reader-body p {{ font-size: 16px; line-height: 2; color: var(--ink); margin-bottom: 14px; }}
.reader-body p.no-content {{ color: var(--muted); font-style: italic; }}
.book-table {{
  width: 100%; border-collapse: collapse; margin: 16px 0;
  font-size: 14px; line-height: 1.6;
}}
.book-table th, .book-table td {{
  border: 1px solid var(--border); padding: 8px 12px;
  color: var(--ink);
}}
.book-table th {{
  background: var(--bg); font-weight: 700; color: var(--accent);
}}
.book-table tr:nth-child(even) td {{ background: #fdfaf7; }}
.book-list {{
  margin: 12px 0 12px 28px; padding: 0;
  font-size: 16px; line-height: 2; color: var(--ink);
}}
.book-list li {{ margin-bottom: 2px; }}

/* ── Chat ── */
.chat-container {{ display: flex; flex-direction: column; gap: 12px; }}
.chat-messages {{
  min-height: 200px; max-height: 400px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 10px; padding: 8px 0;
}}
.msg {{ padding: 10px 14px; border-radius: 12px; font-size: 14px; max-width: 85%; line-height: 1.7; }}
.msg-user {{ background: var(--chat-user); align-self: flex-end;   border: 1px solid #f0c898; }}
.msg-bot  {{ background: var(--chat-bot);  align-self: flex-start; border: 1px solid #d0d8f0; }}
[dir="rtl"] .msg-user {{ align-self: flex-start; }}
[dir="rtl"] .msg-bot  {{ align-self: flex-end; }}
/* Inline dir + textAlign set by JS wins; these are fallback anchors */
.msg[dir="ltr"] {{ text-align: left; }}
.msg[dir="rtl"] {{ text-align: right; }}
.msg-sources {{ margin-top: 6px; font-size: 11px; color: var(--muted); border-top: 1px solid rgba(0,0,0,.08); padding-top: 4px; }}
.chat-input-row {{ display: flex; gap: 8px; }}
.chat-input-row input {{
  flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 10px;
  font-size: 14px; outline: none; font-family: inherit; background: var(--bg);
}}
.chat-input-row input:focus {{ border-color: var(--accent); }}
.chat-input-row button {{
  padding: 10px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 10px; font-size: 14px;
  cursor: pointer; font-family: inherit; white-space: nowrap;
}}
.chat-input-row button:hover {{ background: var(--accent-light); }}
.chat-input-row button:disabled {{ opacity: .6; cursor: default; }}
.chat-unavailable {{
  font-size: 14px; color: var(--muted); padding: 16px;
  background: #fafafa; border-radius: 10px; border: 1px dashed var(--border);
}}

/* ── Summary button & modal ── */
.toc-right {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
.summary-btn {{
  font-size: 11px; padding: 3px 10px; border-radius: 20px;
  border: 1px solid var(--accent); color: var(--accent); background: transparent;
  cursor: pointer; font-family: inherit; white-space: nowrap;
  transition: background .15s, color .15s;
}}
.summary-btn:hover {{ background: var(--accent); color: #fff; }}
.summary-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(44,36,21,.45); z-index: 200;
  align-items: center; justify-content: center; padding: 24px 12px;
}}
.summary-overlay.open {{ display: flex; }}
.summary-modal {{
  background: var(--card); border-radius: 16px; width: 100%; max-width: 640px;
  box-shadow: 0 8px 32px rgba(44,36,21,.22); overflow: hidden;
}}
.summary-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--border); background: var(--bg);
}}
.summary-header h3 {{ font-size: 15px; font-weight: 700; color: var(--ink); }}
.summary-close {{
  padding: 4px 12px; border-radius: 8px;
  border: 1px solid #fca5a5; background: #fff5f5;
  color: #dc2626; font-size: 13px; cursor: pointer; font-family: inherit;
}}
.summary-close:hover {{ background: #fee2e2; }}
.summary-body {{
  padding: 20px 24px 28px; font-size: 15px; line-height: 2;
  color: var(--ink); max-height: 60vh; overflow-y: auto;
}}
</style>
</head>
<body>

<!-- Language toggle -->
<div class="lang-toggle">
  <button onclick="switchLang('en')" id="btn-en" class="lang-btn active">EN</button>
  <button onclick="switchLang('ar')" id="btn-ar" class="lang-btn">AR</button>
</div>

<!-- Summary overlay -->
<div class="summary-overlay" id="summaryOverlay" onclick="handleSummaryClick(event)">
  <div class="summary-modal">
    <div class="summary-header">
      <h3 id="summaryTitle"></h3>
      <button class="summary-close" onclick="closeSummary()"
        data-en="Close" data-ar="إغلاق">Close</button>
    </div>
    <div class="summary-body" id="summaryBody" dir="{content_dir}"></div>
  </div>
</div>

<!-- Reader overlay -->
<div class="reader-overlay" id="readerOverlay" onclick="handleOverlayClick(event)">
  <div class="reader-modal" id="readerModal">
    <div class="reader-topbar">
      <div class="reader-nav">
        <button id="prevBtn" onclick="navigateReader(-1)"
          data-en="Previous" data-ar="السابق">Previous</button>
        <button id="nextBtn" onclick="navigateReader(1)"
          data-en="Next" data-ar="التالي">Next</button>
      </div>
      <span class="reader-counter" id="readerCounter"></span>
      <button class="reader-close" onclick="closeReader()"
        data-en="Close Reader" data-ar="إغلاق القارئ">Close Reader</button>
    </div>
    <div class="reader-body" id="readerBody"></div>
  </div>
</div>

<div class="container">

  <div class="book-header">
    <div class="book-title" dir="{content_dir}">{_esc(display_title)}</div>
    {author_html}
    {category_html}
    {keywords_html}
    {description_html}
    {browse_btn}
  </div>

  {toc_block}

  <div class="section-card">
    <div class="section-heading"
      data-en="Ask About This Book — in English or Arabic"
      data-ar="اسأل عن هذا الكتاب — بالعربية أو الإنجليزية">Ask About This Book — in English or Arabic</div>
    {chat_widget}
  </div>

</div>

<script>
{chat_script}

// ── Language switching ────────────────────────────────────────────────────
let currentLang = localStorage.getItem('bookLang') || 'en';
const SECTION_OF = {{ en: 'of', ar: 'من' }};

function switchLang(lang) {{
  currentLang = lang;
  localStorage.setItem('bookLang', lang);
  document.documentElement.lang = lang;
  document.documentElement.dir  = lang === 'ar' ? 'rtl' : 'ltr';

  document.querySelectorAll('[data-en]').forEach(function(el) {{
    el.textContent = lang === 'ar' ? (el.dataset.ar || el.dataset.en) : el.dataset.en;
  }});

  var chatInput = document.getElementById('chatInput');
  if (chatInput) {{
    chatInput.placeholder = lang === 'ar'
      ? chatInput.dataset.arPlaceholder
      : chatInput.dataset.enPlaceholder;
  }}

  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  document.getElementById('btn-ar').classList.toggle('active', lang === 'ar');

  if (typeof curIdx !== 'undefined' &&
      document.getElementById('readerOverlay').classList.contains('open')) {{
    updateReaderCounter();
  }}
}}

// ── Section summaries ─────────────────────────────────────────────────────
const SUMMARIES = {summaries_json};

function showSummary(idx, e) {{
  e.stopPropagation();
  var text = SUMMARIES[idx];
  if (!text) return;
  document.getElementById('summaryTitle').textContent =
    SECTIONS[idx] ? SECTIONS[idx].title :
    (currentLang === 'ar' ? 'ملخص الفصل' : 'Section Summary');
  document.getElementById('summaryBody').textContent = text;
  document.getElementById('summaryOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeSummary() {{
  document.getElementById('summaryOverlay').classList.remove('open');
  document.body.style.overflow = '';
}}

function handleSummaryClick(e) {{
  if (e.target === document.getElementById('summaryOverlay')) closeSummary();
}}

// ── Reader ────────────────────────────────────────────────────────────────
const SECTIONS = {reader_sections_json};
const TOTAL    = SECTIONS.length;
let   curIdx   = 0;

function openReader(idx) {{
  if (!TOTAL) return;
  curIdx = Math.max(0, Math.min(idx, TOTAL - 1));
  renderSection();
  document.getElementById('readerOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeReader() {{
  document.getElementById('readerOverlay').classList.remove('open');
  document.body.style.overflow = '';
}}

function handleOverlayClick(e) {{
  if (e.target === document.getElementById('readerOverlay')) closeReader();
}}

function navigateReader(delta) {{
  curIdx = Math.max(0, Math.min(curIdx + delta, TOTAL - 1));
  renderSection();
  document.getElementById('readerBody').scrollTop = 0;
}}

function updateReaderCounter() {{
  document.getElementById('readerCounter').textContent =
    (curIdx + 1) + ' ' + (SECTION_OF[currentLang] || 'of') + ' ' + TOTAL;
}}

function renderSection() {{
  var sec = SECTIONS[curIdx];
  document.getElementById('readerBody').innerHTML =
    '<div class="reader-section-title">' + sec.title + '</div>' + sec.content;
  updateReaderCounter();
  document.getElementById('prevBtn').disabled = curIdx === 0;
  document.getElementById('nextBtn').disabled = curIdx === TOTAL - 1;
}}

document.addEventListener('keydown', function(e) {{
  if (!document.getElementById('readerOverlay').classList.contains('open')) return;
  if (e.key === 'ArrowRight') navigateReader(currentLang === 'ar' ? 1 : -1);
  if (e.key === 'ArrowLeft')  navigateReader(currentLang === 'ar' ? -1 : 1);
  if (e.key === 'Escape') closeReader();
}});

// ── Initialise ────────────────────────────────────────────────────────────
switchLang(currentLang);
</script>
</body>
</html>"""


def _esc(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _render_para(para: str, content_dir: str) -> str:
    """Render a paragraph as HTML. Handles tables, bullet lists, numbered lists, and plain text."""
    lines = para.split('\n')
    # Table detection
    if len(lines) >= 2 and lines[0].startswith('|') and lines[1].startswith('|'):
        return _md_table_to_html(lines, content_dir)
    # List / mixed content
    return _render_segments(lines)


def _render_segments(lines: list) -> str:
    """Split lines into list/paragraph segments and render each as HTML."""
    segments: list = []
    current: list  = []
    current_type   = None  # None, 'ul', or 'ol'

    for line in lines:
        stripped = line.strip()
        bullet  = _BULLET_RE.match(stripped)
        ordered = _ORDERED_RE.match(stripped)

        if bullet:
            if current_type != 'ul':
                if current:
                    segments.append((current_type, current))
                current, current_type = [], 'ul'
            current.append(bullet.group(1))
        elif ordered:
            if current_type != 'ol':
                if current:
                    segments.append((current_type, current))
                current, current_type = [], 'ol'
            current.append(ordered.group(1))
        else:
            if current_type in ('ul', 'ol'):
                segments.append((current_type, current))
                current, current_type = [], None
            current.append(line)

    if current:
        segments.append((current_type, current))

    html = ''
    for seg_type, seg_lines in segments:
        if seg_type == 'ul':
            items = ''.join(f'<li>{_esc(l)}</li>' for l in seg_lines)
            html += f'<ul class="book-list">{items}</ul>'
        elif seg_type == 'ol':
            items = ''.join(f'<li>{_esc(l)}</li>' for l in seg_lines)
            html += f'<ol class="book-list">{items}</ol>'
        else:
            text = '\n'.join(seg_lines).strip()
            if text:
                html += f'<p>{_esc(text).replace(chr(10), "<br/>")}</p>'
    return html


def _md_table_to_html(lines: list, content_dir: str) -> str:
    """Convert Markdown table lines to an HTML <table>."""
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        # Skip separator rows (e.g. | --- | --- |)
        inner = stripped.strip('|')
        if all(c in '- |:' for c in inner):
            continue
        cells = [c.strip() for c in stripped.strip('|').split('|')]
        rows.append(cells)

    if not rows:
        return ''

    html = f'<table class="book-table" dir="{content_dir}">'
    html += '<thead><tr>'
    for cell in rows[0]:
        html += f'<th>{_esc(cell)}</th>'
    html += '</tr></thead><tbody>'
    for row in rows[1:]:
        html += '<tr>'
        for cell in row:
            html += f'<td>{_esc(cell)}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html
