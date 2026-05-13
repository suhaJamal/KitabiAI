# app/ui/book_template.py
"""
Renders the public book page with a chat widget and book reader.
"""
import html as _html_mod


def render_book_page(book, sections: list, has_embeddings: bool) -> str:
    # Strip TOC method suffix from display title
    display_title = book.title or ""
    for suffix in ('-extract', '-generate', '-auto'):
        if display_title.endswith(suffix):
            display_title = display_title[:-len(suffix)].strip()
            break

    lang = book.language or 'ar'
    is_rtl = lang == 'ar'
    dir_attr = 'rtl' if is_rtl else 'ltr'
    text_align = 'right' if is_rtl else 'left'

    author_name = book.author.name if book.author else ''
    category_name = book.category_rel.name if book.category_rel else ''
    description = book.description or ''
    keywords = book.keywords or ''

    # ── Labels ────────────────────────────────────────────────────────────────
    chat_heading    = "اسأل عن هذا الكتاب"  if is_rtl else "Ask About This Book"
    toc_heading     = "فهرس المحتويات"       if is_rtl else "Table of Contents"
    reader_heading  = "تصفح الكتاب"          if is_rtl else "Browse Book"
    browse_btn_lbl  = "تصفح الكتاب"          if is_rtl else "Browse Book"
    author_label    = "المؤلف"               if is_rtl else "Author"
    category_label  = "التصنيف"              if is_rtl else "Category"
    keywords_label  = "الكلمات المفتاحية"    if is_rtl else "Keywords"
    no_content_msg  = "لا يوجد محتوى متاح لهذا القسم." if is_rtl else "No content available for this section."
    prev_lbl        = "السابق"               if is_rtl else "Previous"
    next_lbl        = "التالي"               if is_rtl else "Next"
    close_lbl       = "إغلاق القارئ"         if is_rtl else "Close Reader"
    section_of_lbl  = "من"                   if is_rtl else "of"

    # ── TOC list ──────────────────────────────────────────────────────────────
    toc_items = ""
    for i, sec in enumerate(sections):
        title = sec.title or ''
        pages = ""
        if sec.page_start and sec.page_end:
            pages = f'<span class="sec-pages">ص {sec.page_start}–{sec.page_end}</span>' if is_rtl else f'<span class="sec-pages">pp. {sec.page_start}–{sec.page_end}</span>'
        elif sec.page_start:
            pages = f'<span class="sec-pages">ص {sec.page_start}</span>' if is_rtl else f'<span class="sec-pages">p. {sec.page_start}</span>'
        toc_items += (
            f'<li class="toc-item" onclick="openReader({i})" title="{_esc(title)}">'
            f'<span class="sec-title">{_esc(title)}</span>{pages}'
            f'</li>\n'
        )

    # ── Reader sections ───────────────────────────────────────────────────────
    reader_sections_js = []   # list of JS objects {title, content}
    for sec in sections:
        title   = _esc(sec.title or '')
        content = sec.content or sec.summary or ''
        if content:
            # Convert double newlines to paragraph breaks; single newlines to <br>
            paragraphs = content.strip().split('\n\n')
            paras_html = ''.join(
                f'<p>{_esc(p.strip()).replace(chr(10), "<br/>")}</p>'
                for p in paragraphs if p.strip()
            )
        else:
            paras_html = f'<p class="no-content">{no_content_msg}</p>'

        # Encode for JS string (escape backticks and backslashes)
        js_title   = title.replace('\\', '\\\\').replace('`', '\\`')
        js_content = paras_html.replace('\\', '\\\\').replace('`', '\\`')
        reader_sections_js.append(f'{{title:`{js_title}`,content:`{js_content}`}}')

    reader_sections_json = '[' + ',\n'.join(reader_sections_js) + ']'
    has_reader = len(sections) > 0

    # ── Chat widget ───────────────────────────────────────────────────────────
    if has_embeddings:
        chat_placeholder = "اكتب سؤالك هنا..." if is_rtl else "Type your question here..."
        ask_label = "إرسال" if is_rtl else "Ask"
        chat_widget = f"""
<div class="chat-container" id="chatContainer">
  <div class="chat-messages" id="chatMessages"></div>
  <div class="chat-input-row">
    <input type="text" id="chatInput" placeholder="{chat_placeholder}" dir="{dir_attr}" />
    <button id="askBtn" onclick="askQuestion()">{ask_label}</button>
  </div>
</div>
"""
        chat_script = f"""
const BOOK_ID = {book.id};
const IS_RTL  = {'true' if is_rtl else 'false'};

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
  .catch(() => {{ appendMessage(IS_RTL ? 'حدث خطأ، حاول مجددًا.' : 'An error occurred, please try again.', 'bot'); }})
  .finally(() => {{ document.getElementById('askBtn').disabled = false; }});
}}

function appendMessage(text, role, sources) {{
  const box = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = 'msg msg-' + role;
  msg.dir = IS_RTL ? 'rtl' : 'ltr';
  msg.textContent = text;
  if (sources && sources.length) {{
    const srcDiv = document.createElement('div');
    srcDiv.className = 'msg-sources';
    srcDiv.textContent = (IS_RTL ? 'المصادر: ' : 'Sources: ') +
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
        notice = "الفهرس الذكي لهذا الكتاب لم يُنشأ بعد. يرجى التواصل مع المسؤول." if is_rtl else "Smart index not yet generated for this book. Please contact the administrator."
        chat_widget = f'<div class="chat-unavailable">{notice}</div>'
        chat_script = "const IS_RTL = " + ('true' if is_rtl else 'false') + ";"

    # ── Meta ──────────────────────────────────────────────────────────────────
    meta_description = _esc(description[:200]) if description else _esc(display_title)
    meta_keywords    = _esc(keywords) if keywords else ''

    author_html      = f'<div class="meta-row"><span class="meta-label">{author_label}:</span> <span>{_esc(author_name)}</span></div>' if author_name else ''
    category_html    = f'<div class="meta-row"><span class="meta-label">{category_label}:</span> <span>{_esc(category_name)}</span></div>' if category_name else ''
    keywords_html    = f'<div class="meta-row"><span class="meta-label">{keywords_label}:</span> <span class="keywords">{_esc(keywords)}</span></div>' if keywords else ''
    description_html = f'<p class="book-description">{_esc(description)}</p>' if description else ''

    browse_btn = (
        f'<button class="browse-btn" onclick="openReader(0)">{browse_btn_lbl}</button>'
        if has_reader else ''
    )

    toc_block = (
        f'<div class="section-card"><div class="section-heading">{toc_heading}</div>'
        f'<ul class="toc-list">{toc_items}</ul></div>'
        if toc_items else ''
    )

    total_sections = len(sections)

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{dir_attr}">
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

/* ── Book header ── */
.book-header {{
  background: var(--card);
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 2px 8px rgba(44,36,21,.08);
  border: 1px solid var(--border);
  margin-bottom: 24px;
}}
.book-title {{
  font-size: 26px; font-weight: 700; color: var(--ink);
  margin-bottom: 12px; text-align: {text_align};
}}
.meta-row {{ font-size: 14px; color: var(--muted); margin-bottom: 6px; text-align: {text_align}; }}
.meta-label {{ font-weight: 600; color: var(--accent); }}
.book-description {{ margin-top: 14px; font-size: 15px; color: var(--ink); text-align: {text_align}; line-height: 1.8; }}
.keywords {{ font-size: 13px; color: var(--muted); }}

/* Browse button */
.browse-btn {{
  display: inline-block;
  margin-top: 18px;
  padding: 10px 22px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
  transition: background .15s;
}}
.browse-btn:hover {{ background: var(--accent-light); }}

/* ── Section card ── */
.section-card {{
  background: var(--card);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(44,36,21,.08);
  border: 1px solid var(--border);
  margin-bottom: 24px;
}}
.section-heading {{
  font-size: 16px; font-weight: 700; color: var(--accent);
  margin-bottom: 16px; text-align: {text_align};
}}

/* ── TOC ── */
.toc-list {{ list-style: none; padding: 0; }}
.toc-item {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 9px 0;
  border-bottom: 1px solid var(--border);
  gap: 8px;
  cursor: pointer;
  {'flex-direction: row-reverse;' if is_rtl else ''}
}}
.toc-item:last-child {{ border-bottom: none; }}
.toc-item:hover .sec-title {{ color: var(--accent); }}
.sec-title {{ font-size: 14px; color: var(--ink); transition: color .15s; }}
.sec-pages {{ font-size: 12px; color: var(--muted); white-space: nowrap; }}

/* ── Reader overlay ── */
.reader-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(44,36,21,.45);
  z-index: 100;
  align-items: flex-start;
  justify-content: center;
  padding: 24px 12px;
  overflow-y: auto;
}}
.reader-overlay.open {{ display: flex; }}
.reader-modal {{
  background: var(--reader-bg);
  border-radius: 18px;
  width: 100%;
  max-width: 720px;
  box-shadow: 0 8px 32px rgba(44,36,21,.22);
  overflow: hidden;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  margin: auto;
}}
.reader-topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--card);
  gap: 12px;
  flex-wrap: wrap;
}}
.reader-counter {{
  font-size: 13px;
  color: var(--muted);
  white-space: nowrap;
}}
.reader-nav {{
  display: flex;
  gap: 8px;
  {'flex-direction: row-reverse;' if is_rtl else ''}
}}
.reader-nav button, .reader-close {{
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  color: var(--ink);
  transition: background .15s;
}}
.reader-nav button:hover, .reader-close:hover {{ background: var(--border); }}
.reader-nav button:disabled {{ opacity: .4; cursor: default; }}
.reader-close {{ color: #dc2626; border-color: #fca5a5; background: #fff5f5; }}
.reader-close:hover {{ background: #fee2e2; }}
.reader-body {{
  padding: 28px 32px 36px;
  flex: 1;
  overflow-y: auto;
  direction: {dir_attr};
}}
.reader-section-title {{
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 20px;
  text-align: {text_align};
  line-height: 1.5;
}}
.reader-body p {{
  font-size: 16px;
  line-height: 2;
  color: var(--ink);
  text-align: {text_align};
  margin-bottom: 14px;
}}
.reader-body p.no-content {{
  color: var(--muted);
  font-style: italic;
}}

/* ── Chat ── */
.chat-container {{ display: flex; flex-direction: column; gap: 12px; }}
.chat-messages {{
  min-height: 200px; max-height: 400px;
  overflow-y: auto; display: flex; flex-direction: column;
  gap: 10px; padding: 8px 0;
}}
.msg {{
  padding: 10px 14px; border-radius: 12px;
  font-size: 14px; max-width: 85%; line-height: 1.7;
}}
.msg-user {{ background: var(--chat-user); align-self: {'flex-start' if is_rtl else 'flex-end'}; border: 1px solid #f0c898; }}
.msg-bot  {{ background: var(--chat-bot);  align-self: {'flex-end' if is_rtl else 'flex-start'}; border: 1px solid #d0d8f0; }}
.msg-sources {{ margin-top: 6px; font-size: 11px; color: var(--muted); border-top: 1px solid rgba(0,0,0,.08); padding-top: 4px; }}
.chat-input-row {{ display: flex; gap: 8px; {'flex-direction: row-reverse;' if is_rtl else ''} }}
.chat-input-row input {{
  flex: 1; padding: 10px 14px;
  border: 1px solid var(--border); border-radius: 10px;
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
  background: #fafafa; border-radius: 10px;
  border: 1px dashed var(--border); text-align: {text_align};
}}
</style>
</head>
<body>

<!-- Reader overlay -->
<div class="reader-overlay" id="readerOverlay" onclick="handleOverlayClick(event)">
  <div class="reader-modal" id="readerModal">
    <div class="reader-topbar">
      <div class="reader-nav">
        <button id="prevBtn" onclick="navigateReader(-1)">{prev_lbl}</button>
        <button id="nextBtn" onclick="navigateReader(1)">{next_lbl}</button>
      </div>
      <span class="reader-counter" id="readerCounter"></span>
      <button class="reader-close" onclick="closeReader()">{close_lbl}</button>
    </div>
    <div class="reader-body" id="readerBody"></div>
  </div>
</div>

<div class="container">

  <div class="book-header">
    <div class="book-title">{_esc(display_title)}</div>
    {author_html}
    {category_html}
    {keywords_html}
    {description_html}
    {browse_btn}
  </div>

  {toc_block}

  <div class="section-card">
    <div class="section-heading">{chat_heading}</div>
    {chat_widget}
  </div>

</div>

<script>
{chat_script}

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

function renderSection() {{
  const sec = SECTIONS[curIdx];
  document.getElementById('readerBody').innerHTML =
    '<div class="reader-section-title">' + sec.title + '</div>' + sec.content;
  document.getElementById('readerCounter').textContent =
    (curIdx + 1) + ' {section_of_lbl} ' + TOTAL;
  document.getElementById('prevBtn').disabled = curIdx === 0;
  document.getElementById('nextBtn').disabled = curIdx === TOTAL - 1;
}}

document.addEventListener('keydown', function(e) {{
  if (!document.getElementById('readerOverlay').classList.contains('open')) return;
  if (e.key === 'ArrowRight') navigateReader(IS_RTL ? 1 : -1);
  if (e.key === 'ArrowLeft')  navigateReader(IS_RTL ? -1 : 1);
  if (e.key === 'Escape') closeReader();
}});
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
