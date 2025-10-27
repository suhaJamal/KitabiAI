# tests/test_english_toc_extractor.py
"""
Unit tests for EnglishTocExtractor.

Tests pattern matching for various English TOC formats.
"""

import pytest
from app.services.english_toc_extractor import EnglishTocExtractor

@pytest.mark.skip(reason="English extractor tests - Phase 2 WIP")
class TestEnglishTocExtractor:
    """Test suite for English TOC extraction."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.extractor = EnglishTocExtractor(min_sections=2)
    
    def test_chapter_format_basic(self):
        """Test basic 'Chapter N: Title' format."""
        text = """
        Chapter 1: Introduction
        This is the introduction text.
        
        Chapter 2: Background
        Some background information here.
        
        Chapter 3: Methodology
        The methodology section.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        assert len(report.sections) == 3
        assert report.sections[0].title == "Introduction"
        assert report.sections[1].title == "Background"
        assert report.sections[2].title == "Methodology"
        assert not report.bookmarks_found
    
    def test_chapter_format_uppercase(self):
        """Test uppercase 'CHAPTER N: TITLE' format."""
        text = """
        CHAPTER 1: INTRODUCTION
        Content here.
        
        CHAPTER 2: LITERATURE REVIEW
        More content.
        """
        
        report = self.extractor.extract(text, num_pages=50)
        
        assert len(report.sections) == 2
        assert report.sections[0].title == "INTRODUCTION"
        assert report.sections[1].title == "LITERATURE REVIEW"
    
    def test_numbered_format(self):
        """Test numbered format '1. Title'."""
        text = """
        1. Introduction
        Some text here.
        
        2. Related Work
        More text.
        
        3. Methods
        Even more text.
        
        4. Results
        Results text.
        """
        
        report = self.extractor.extract(text, num_pages=80)
        
        assert len(report.sections) == 4
        assert report.sections[0].section_id == "1"
        assert report.sections[0].level == 1
    
    def test_hierarchical_numbering(self):
        """Test hierarchical numbering (1, 1.1, 1.2, 2, 2.1)."""
        text = """
        1. Introduction
        Main introduction.
        
        1.1 Background
        Background subsection.
        
        1.2 Objectives
        Objectives subsection.
        
        2. Methods
        Methods section.
        
        2.1 Data Collection
        Data collection subsection.
        
        2.2 Analysis
        Analysis subsection.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        assert len(report.sections) >= 4  # At least top-level sections
        
        # Check hierarchical structure
        intro_sections = [s for s in report.sections if s.section_id.startswith("1")]
        assert len(intro_sections) >= 2  # 1, 1.1, 1.2
        
        # Check levels
        level_1_sections = [s for s in report.sections if s.level == 1]
        level_2_sections = [s for s in report.sections if s.level == 2]
        assert len(level_1_sections) >= 2
        assert len(level_2_sections) >= 2
    
    def test_section_format(self):
        """Test 'Section N: Title' format."""
        text = """
        Section 1: Overview
        Overview text.
        
        Section 2: Implementation
        Implementation text.
        
        Section 2.1: Architecture
        Architecture details.
        """
        
        report = self.extractor.extract(text, num_pages=60)
        
        assert len(report.sections) >= 2
        section_titles = [s.title for s in report.sections]
        assert "Overview" in section_titles or "Implementation" in section_titles
    
    def test_part_format(self):
        """Test 'Part N: Title' format."""
        text = """
        Part I: Foundations
        Foundation text.
        
        Part II: Applications
        Applications text.
        
        Part 1: Introduction
        Another format.
        """
        
        report = self.extractor.extract(text, num_pages=120)
        
        # Should find at least some sections
        assert len(report.sections) >= 1
    
    def test_appendix_format(self):
        """Test 'Appendix X: Title' format."""
        text = """
        Chapter 1: Main Content
        Main text.
        
        Appendix A: Supplementary Data
        Appendix content.
        
        Appendix B: Additional Information
        More appendix.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        assert len(report.sections) >= 2
        titles = [s.title for s in report.sections]
        assert "Supplementary Data" in titles or "Main Content" in titles
    
    def test_mixed_formats(self):
        """Test document with mixed heading formats."""
        text = """
        CHAPTER 1: INTRODUCTION
        Introduction text.
        
        1.1 Background
        Background.
        
        Section 2: Methods
        Methods text.
        
        2.1 Data Analysis
        Analysis.
        
        Part II: Results
        Results text.
        
        Appendix A: Extra Data
        Appendix.
        """
        
        report = self.extractor.extract(text, num_pages=150)
        
        # Should extract multiple sections despite mixed formats
        assert len(report.sections) >= 3
    
    def test_page_range_calculation(self):
        """Test that page ranges are calculated correctly."""
        text = """
        Chapter 1: First
        """ + ("x" * 1000) + """
        
        Chapter 2: Second
        """ + ("y" * 1000) + """
        
        Chapter 3: Third
        """ + ("z" * 1000)
        
        report = self.extractor.extract(text, num_pages=100)
        
        assert len(report.sections) == 3
        
        # First section should start at page 1
        assert report.sections[0].page_start == 1
        
        # Each section should have valid page range
        for section in report.sections:
            assert section.page_start <= section.page_end
            assert section.page_start >= 1
            assert section.page_end <= 100
        
        # Last section should end at last page
        assert report.sections[-1].page_end == 100
    
    def test_insufficient_sections_fallback(self):
        """Test fallback when insufficient sections found."""
        text = """
        Chapter 1: Only One Chapter
        This document only has one chapter.
        """
        
        # With min_sections=2, this should trigger fallback
        report = self.extractor.extract(text, num_pages=50)
        
        assert len(report.sections) == 1
        assert report.sections[0].title == "Document"
        assert report.sections[0].page_start == 1
        assert report.sections[0].page_end == 50
    
    def test_duplicate_removal(self):
        """Test that duplicate sections are removed."""
        text = """
        Chapter 1: Introduction
        First occurrence.
        
        Chapter 1: Introduction
        Duplicate occurrence.
        
        Chapter 2: Methods
        Different section.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        # Should only have 2 unique sections
        assert len(report.sections) == 2
        
        # Check no duplicates
        titles = [s.title for s in report.sections]
        assert len(titles) == len(set(titles))
    
    def test_short_title_filtering(self):
        """Test that very short titles are filtered out."""
        text = """
        Chapter 1: A
        Too short.
        
        Chapter 2: This is a proper title
        Good title.
        
        Chapter 3: XY
        Also too short.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        # Should only extract the section with proper title
        titles = [s.title for s in report.sections]
        assert "This is a proper title" in titles
        assert "A" not in titles
        assert "XY" not in titles
    
    def test_very_long_title_filtering(self):
        """Test that unreasonably long titles are filtered out."""
        text = """
        Chapter 1: This is a normal title
        Normal content.
        
        Chapter 2: """ + ("A" * 250) + """
        This title is way too long and is probably not a real chapter title.
        
        Chapter 3: Another normal title
        More content.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        # Should only extract sections with reasonable title lengths
        for section in report.sections:
            assert len(section.title) <= 200
    
    def test_level_determination(self):
        """Test that hierarchical levels are correctly determined."""
        # Test various number formats
        assert self.extractor._determine_level("1") == 1
        assert self.extractor._determine_level("1.1") == 2
        assert self.extractor._determine_level("1.1.1") == 3
        assert self.extractor._determine_level("2.3.4.5") == 4
    
    def test_section_number_parsing(self):
        """Test section number parsing for sorting."""
        # Test numeric parsing
        assert self.extractor._parse_section_number("1") == (1,)
        assert self.extractor._parse_section_number("1.2") == (1, 2)
        assert self.extractor._parse_section_number("1.10.3") == (1, 10, 3)
        
        # Test that 1.10 comes after 1.2 (not lexicographic)
        num_1_2 = self.extractor._parse_section_number("1.2")
        num_1_10 = self.extractor._parse_section_number("1.10")
        assert num_1_10 > num_1_2
    
    def test_empty_text(self):
        """Test behavior with empty text."""
        report = self.extractor.extract("", num_pages=10)
        
        # Should return fallback
        assert len(report.sections) == 1
        assert report.sections[0].title == "Document"
    
    def test_no_matching_patterns(self):
        """Test document with no matching patterns."""
        text = """
        This is just regular text without any chapter headings
        or section markers. It's just a plain document with
        paragraphs of text and no clear structure.
        
        More text here without any special formatting or
        numbering that would indicate sections or chapters.
        """
        
        report = self.extractor.extract(text, num_pages=50)
        
        # Should return fallback
        assert len(report.sections) == 1
        assert report.sections[0].title == "Document"
    
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        text = """
        chapter 1: lowercase chapter
        Content.
        
        CHAPTER 2: UPPERCASE CHAPTER
        More content.
        
        ChApTeR 3: MiXeD cAsE cHaPtEr
        Even more content.
        """
        
        report = self.extractor.extract(text, num_pages=100)
        
        # All three should be detected
        assert len(report.sections) == 3


class TestRealWorldScenarios:
    """Test realistic document structures."""
    
    def test_academic_paper_structure(self):
        """Test typical academic paper structure."""
        text = """
        1. Introduction
        This paper presents...
        
        2. Related Work
        Previous research has shown...
        
        3. Methodology
        Our approach consists of...
        
        3.1 Data Collection
        We collected data from...
        
        3.2 Data Analysis
        The data was analyzed using...
        
        4. Results
        Our experiments showed...
        
        5. Discussion
        These results indicate...
        
        6. Conclusion
        In conclusion...
        
        Appendix A: Survey Questions
        The survey included...
        """
        
        extractor = EnglishTocExtractor(min_sections=3)
        report = extractor.extract(text, num_pages=25)
        
        assert len(report.sections) >= 6
        
        # Check that hierarchical structure is preserved
        level_2_sections = [s for s in report.sections if s.level == 2]
        assert len(level_2_sections) >= 2  # 3.1, 3.2
    
    def test_technical_manual_structure(self):
        """Test typical technical manual structure."""
        text = """
        Chapter 1: Getting Started
        Welcome to the user manual...
        
        Chapter 2: Installation
        Follow these steps to install...
        
        Chapter 3: Configuration
        Configure the system by...
        
        Section 3.1: Basic Settings
        Set the basic parameters...
        
        Section 3.2: Advanced Settings
        For advanced users...
        
        Chapter 4: Troubleshooting
        If you encounter problems...
        
        Appendix A: Specifications
        Technical specifications...
        
        Appendix B: FAQ
        Frequently asked questions...
        """
        
        extractor = EnglishTocExtractor(min_sections=3)
        report = extractor.extract(text, num_pages=120)
        
        assert len(report.sections) >= 5
        
        # Check that appendices are included
        titles = [s.title for s in report.sections]
        assert any("Appendix" in t or "Specifications" in t or "FAQ" in t for t in titles)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])