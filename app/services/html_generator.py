# app/services/html_generator.py
"""
Generate styled HTML from PDF content.

Features:
- Responsive design
- RTL support for Arabic
- Navigation sidebar
- Clean typography
- Print-friendly styles
"""

import logging
from typing import List, Optional
from datetime import datetime
from ..models.schemas import (
    BookMetadata,
    SectionInfo,
    PageInfo,
    ChunkInfo
)

logger = logging.getLogger(__name__)


class HtmlGenerator:
    """Generate styled HTML from book content."""
    
    def generate(
        self,
        metadata: BookMetadata,
        sections: List[SectionInfo],
        pages: List[PageInfo],
        language: str,
        include_toc: bool = True
    ) -> str:
        """
        Generate complete HTML document.
        
        Args:
            metadata: Book metadata
            sections: TOC sections
            pages: Page content
            language: Detected language (english/arabic)
            include_toc: Include navigation sidebar
            
        Returns:
            Complete HTML document as string
        """
        # Build HTML parts
        html_head = self._generate_head(metadata, language)
        html_header = self._generate_header(metadata)
        html_nav = self._generate_nav(sections) if include_toc else ""
        html_content = self._generate_content(sections, pages, language)
        html_footer = self._generate_footer()
        
        # Combine into full document
        direction = "rtl" if language == "arabic" else "ltr"
        
        html = f"""<!DOCTYPE html>
<html lang="{language}" dir="{direction}">
{html_head}
<body>
    {html_header}
    <div class="container">
        {html_nav}
        <main class="content">
            {html_content}
        </main>
    </div>
    {html_footer}
</body>
</html>"""
        
        return html
    
    def generate_from_chunks(
        self,
        metadata: BookMetadata,
        chunks: List[ChunkInfo],
        language: str,
        include_toc: bool = True
    ) -> str:
        """
        Generate HTML from pre-chunked content.
        
        Args:
            metadata: Book metadata
            chunks: Chunked content
            language: Detected language
            include_toc: Include navigation sidebar
            
        Returns:
            Complete HTML document
        """
        html_head = self._generate_head(metadata, language)
        html_header = self._generate_header(metadata)
        html_nav = self._generate_nav_from_chunks(chunks) if include_toc else ""
        html_content = self._generate_content_from_chunks(chunks)
        html_footer = self._generate_footer()
        
        direction = "rtl" if language == "arabic" else "ltr"
        
        html = f"""<!DOCTYPE html>
<html lang="{language}" dir="{direction}">
{html_head}
<body>
    {html_header}
    <div class="container">
        {html_nav}
        <main class="content">
            {html_content}
        </main>
    </div>
    {html_footer}
</body>
</html>"""
        
        return html
    
    def _generate_head(self, metadata: BookMetadata, language: str) -> str:
        """Generate HTML head with styles."""
        direction = "rtl" if language == "arabic" else "ltr"
        
        return f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        
        /* RTL Support */
        [dir="rtl"] {{
            text-align: right;
        }}
        
        [dir="rtl"] body {{
            font-family: 'Traditional Arabic', 'Simplified Arabic', Arial, sans-serif;
        }}
        
        /* Header */
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .metadata {{
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        
        /* Container */
        .container {{
            display: flex;
            max-width: 1400px;
            margin: 2rem auto;
            gap: 2rem;
            padding: 0 1rem;
        }}
        
        /* Navigation */
        nav {{
            flex: 0 0 280px;
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            position: sticky;
            top: 2rem;
            height: fit-content;
            max-height: calc(100vh - 4rem);
            overflow-y: auto;
        }}
        
        nav h2 {{
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: #667eea;
        }}
        
        nav ul {{
            list-style: none;
        }}
        
        nav li {{
            margin-bottom: 0.5rem;
        }}
        
        nav a {{
            color: #555;
            text-decoration: none;
            display: block;
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        
        nav a:hover {{
            background: #f0f0f0;
            color: #667eea;
        }}
        
        nav .level-2 {{
            padding-left: 1rem;
            font-size: 0.9rem;
        }}
        
        nav .level-3 {{
            padding-left: 2rem;
            font-size: 0.85rem;
        }}
        
        /* Main Content */
        .content {{
            flex: 1;
            background: white;
            padding: 3rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        /* Sections */
        section {{
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        section:last-child {{
            border-bottom: none;
        }}
        
        section h2 {{
            color: #667eea;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        section h3 {{
            color: #764ba2;
            font-size: 1.5rem;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        
        section h4 {{
            color: #555;
            font-size: 1.2rem;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }}
        
        .page-range {{
            font-size: 0.9rem;
            color: #888;
            font-style: italic;
            margin-bottom: 1rem;
        }}
        
        /* Paragraphs */
        p {{
            margin-bottom: 1rem;
            text-align: justify;
        }}
        
        /* Footer */
        footer {{
            text-align: center;
            padding: 2rem;
            color: #888;
            font-size: 0.9rem;
        }}
        
        /* Print Styles */
        @media print {{
            body {{
                background: white;
            }}
            
            nav {{
                display: none;
            }}
            
            .container {{
                margin: 0;
            }}
            
            section {{
                page-break-inside: avoid;
            }}
        }}
        
        /* Mobile Responsive */
        @media (max-width: 768px) {{
            .container {{
                flex-direction: column;
            }}
            
            nav {{
                position: static;
                max-height: none;
            }}
            
            .content {{
                padding: 1.5rem;
            }}
            
            header h1 {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>"""
    
    def _generate_header(self, metadata: BookMetadata) -> str:
        """Generate page header."""
        meta_parts = []
        if metadata.author:
            meta_parts.append(f"By {metadata.author}")
        if metadata.publication_date:
            meta_parts.append(metadata.publication_date)
        
        meta_html = " • ".join(meta_parts) if meta_parts else ""
        
        return f"""<header>
    <h1>{metadata.title}</h1>
    {f'<div class="metadata">{meta_html}</div>' if meta_html else ''}
</header>"""
    
    def _generate_nav(self, sections: List[SectionInfo]) -> str:
        """Generate navigation sidebar."""
        nav_items = []
        for section in sections:
            level_class = f"level-{section.level}"
            anchor = self._make_anchor(section.section_id)
            nav_items.append(
                f'<li class="{level_class}"><a href="#{anchor}">{section.title}</a></li>'
            )
        
        nav_html = "\n".join(nav_items)
        
        return f"""<nav>
    <h2>Contents</h2>
    <ul>
        {nav_html}
    </ul>
</nav>"""
    
    def _generate_nav_from_chunks(self, chunks: List[ChunkInfo]) -> str:
        """Generate navigation from chunks (unique sections)."""
        nav_items = []
        seen_sections = set()
        
        for chunk in chunks:
            if chunk.section_id not in seen_sections:
                anchor = self._make_anchor(chunk.section_id)
                nav_items.append(
                    f'<li><a href="#{anchor}">{chunk.section_title}</a></li>'
                )
                seen_sections.add(chunk.section_id)
        
        nav_html = "\n".join(nav_items)
        
        return f"""<nav>
    <h2>Contents</h2>
    <ul>
        {nav_html}
    </ul>
</nav>"""
    
    def _generate_content(
        self,
        sections: List[SectionInfo],
        pages: List[PageInfo],
        language: str
    ) -> str:
        """Generate main content sections."""
        section_htmls = []

        for section in sections:
            section_html = self._generate_section(section, pages, language, sections)
            section_htmls.append(section_html)

        return "\n".join(section_htmls)
    
    def _generate_section(
        self,
        section: SectionInfo,
        pages: List[PageInfo],
        language: str,
        all_sections: List[SectionInfo]
    ) -> str:
        """
        Generate HTML for a single section.

        For hierarchical TOCs (English), only leaf sections (sections with no children)
        get content extracted. Parent sections appear in navigation only.
        This prevents duplicate content when a parent and its children have overlapping page ranges.

        For flat TOCs (Arabic), all sections are leaf nodes, so all get content.
        """
        anchor = self._make_anchor(section.section_id)
        header_tag = f"h{min(section.level + 1, 6)}"  # h2-h6

        # Check if this section has children (only for hierarchical TOCs)
        is_leaf = self._is_leaf_section(section, all_sections)

        # Build paragraphs only for leaf sections
        paragraphs = []
        if is_leaf:
            # Get section pages
            section_pages = [
                p for p in pages
                if section.page_start <= p.page <= section.page_end
            ]

            for page in section_pages:
                if page.has_text and page.text:
                    # Split into paragraphs and wrap in <p> tags
                    for para in page.text.split("\n\n"):
                        para = para.strip()
                        if len(para) > 10:  # Skip very short paragraphs
                            # Escape HTML special characters
                            para = self._escape_html(para)
                            paragraphs.append(f"<p>{para}</p>")

        content_html = "\n".join(paragraphs)

        return f"""<section id="{anchor}">
    <{header_tag}>{section.title}</{header_tag}>
    <div class="page-range">Pages {section.page_start}-{section.page_end}</div>
    {content_html}
</section>"""
    
    def _generate_content_from_chunks(self, chunks: List[ChunkInfo]) -> str:
        """Generate content from chunks."""
        section_htmls = []
        current_section = None
        
        for chunk in chunks:
            # Start new section if needed
            if chunk.section_id != current_section:
                if current_section is not None:
                    section_htmls.append("</section>")
                
                anchor = self._make_anchor(chunk.section_id)
                section_htmls.append(f"""<section id="{anchor}">
    <h2>{chunk.section_title}</h2>
    <div class="page-range">Pages {chunk.page_start}-{chunk.page_end}</div>""")
                current_section = chunk.section_id
            
            # Add chunk content
            paragraphs = []
            for para in chunk.content.split("\n\n"):
                para = para.strip()
                if len(para) > 10:
                    para = self._escape_html(para)
                    paragraphs.append(f"<p>{para}</p>")
            
            section_htmls.append("\n".join(paragraphs))
        
        # Close last section
        if current_section is not None:
            section_htmls.append("</section>")
        
        return "\n".join(section_htmls)
    
    def _is_leaf_section(self, section: SectionInfo, all_sections: List[SectionInfo]) -> bool:
        """
        Check if a section is a leaf node (has no children).

        A section has children if any other section's ID starts with this section's ID + "."
        Examples:
        - "1" has children if "1.1", "1.2", etc. exist
        - "2.3" has children if "2.3.1", "2.3.2", etc. exist
        - Arabic sections like "1", "2", "3" have no children (no "1.1" exists)

        Args:
            section: The section to check
            all_sections: All sections in the TOC

        Returns:
            True if section has no children, False otherwise
        """
        section_prefix = section.section_id + "."
        for other in all_sections:
            if other.section_id.startswith(section_prefix):
                return False  # Found a child
        return True  # No children found

    def _generate_footer(self) -> str:
        """Generate page footer."""
        return f"""<footer>
    <p>Generated by KitabiAI • {datetime.utcnow().strftime('%Y-%m-%d')}</p>
</footer>"""
    
    def _make_anchor(self, section_id: str) -> str:
        """Create URL-safe anchor from section ID."""
        return f"section-{section_id.replace('.', '-')}"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))
    
    def save_to_file(self, content: str, output_path: str) -> None:
        """Save HTML content to file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved HTML to {output_path}")