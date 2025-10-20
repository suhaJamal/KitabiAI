"""
Tests for Arabic TOC Extractor

These tests verify that your TOC extraction works correctly
without manually uploading PDFs each time.
"""

import pytest
from app.services.arabic_toc_extractor import ArabicTocExtractor


class TestArabicTocExtractor:
    """Test suite for Arabic TOC extraction functionality"""
    
    def setup_method(self):
        """Run before each test - creates a fresh extractor instance"""
        self.extractor = ArabicTocExtractor()
    
    # TEST 1: Check that the extractor initializes correctly
    def test_extractor_initialization(self):
        """Verify the extractor object is created with correct properties"""
        assert self.extractor is not None
        assert self.extractor.toc_regex is not None
        print("✅ Extractor initialized successfully")
    
    # TEST 2: Check TOC pattern detection
    def test_toc_header_detection(self):
        """Verify Arabic TOC headers are correctly identified"""
        # Sample text with Arabic TOC header
        text_with_toc = """
        المحتويات
        الفصل الأول: مقدمة .......... 1
        الفصل الثاني: النظرية ........ 15
        """
        
        # Check if TOC header is found
        match = self.extractor.toc_regex.search(text_with_toc)
        assert match is not None
        assert "المحتويات" in match.group()
        print("✅ TOC header detected correctly")
    
    # TEST 3: Check fallback behavior when no TOC found
    def test_fallback_section(self):
        """Verify fallback section is created when TOC extraction fails"""
        result = self.extractor._fallback_section()
        
        # Verify the fallback structure
        assert result.bookmarks_found == False
        assert len(result.sections) == 1
        assert result.sections[0].title == "Document"
        assert result.sections[0].page_start == 1
        print("✅ Fallback section created correctly")
    
    # TEST 4: Check header/footer filtering
    def test_header_footer_filtering(self):
        """Verify headers and footers are correctly filtered out"""
        # Test cases: (text, should_be_filtered)
        test_cases = [
            ("صفحة 123", True),  # Page number - should filter
            ("الفصل الأول", False),  # Chapter title - keep
            ("12/10/2024 3:45", True),  # Timestamp - should filter
            ("©2024", True),  # Copyright - should filter
            ("مقدمة", False),  # Introduction - keep
        ]
        
        for text, should_filter in test_cases:
            result = self.extractor._is_header_footer(text, in_toc_context=False)
            assert result == should_filter
            status = "filtered" if should_filter else "kept"
            print(f"✅ '{text}' correctly {status}")
    
    # TEST 5: Check TOC entry parsing
    def test_toc_entry_parsing(self):
        """Verify TOC entries are correctly parsed into sections"""
        # Sample TOC text with proper format
        toc_text = """
        الفصل الأول
        1
        الفصل الثاني
        15
        الفصل الثالث
        30
        """
        
        entries = self.extractor._parse_toc_entries(toc_text)
        
        # Verify correct number of entries
        assert len(entries) >= 3
        
        # Verify first entry structure
        assert entries[0]["title"] == "الفصل الأول"
        assert entries[0]["page"] == 1
        
        print(f"✅ Parsed {len(entries)} TOC entries correctly")
    
    # TEST 6: Check section creation with page ranges
    def test_section_creation(self):
        """Verify sections are created with correct page ranges"""
        entries = [
            {"title": "Chapter 1", "page": 1},
            {"title": "Chapter 2", "page": 15},
            {"title": "Chapter 3", "page": 30}
        ]
        
        sections = self.extractor._create_sections(entries)
        
        # Verify correct number of sections
        assert len(sections) == 3
        
        # Verify first section
        assert sections[0].title == "Chapter 1"
        assert sections[0].page_start == 1
        assert sections[0].page_end == 14  # One before next section
        
        # Verify middle section
        assert sections[1].page_start == 15
        assert sections[1].page_end == 29
        
        print("✅ Sections created with correct page ranges")
    
    # TEST 7: Integration test - full extraction process
    def test_full_extraction_with_valid_toc(self):
        """Test complete extraction process with valid Arabic TOC"""
        # Sample document with TOC at beginning
        sample_text = """
        المحتويات
        
        الفصل الأول: المقدمة
        1
        الفصل الثاني: النظرية
        15
        الفصل الثالث: التطبيق
        30
        الفصل الرابع: النتائج
        45
        الفصل الخامس: الخاتمة
        60
        
        [Rest of document text...]
        """ * 10  # Simulate longer document
        
        result = self.extractor.extract(sample_text)
        
        # Verify extraction was successful
        assert result.bookmarks_found == True
        assert len(result.sections) >= 5
        assert result.sections[0].title == "الفصل الأول: المقدمة"
        
        print(f"✅ Full extraction successful: {len(result.sections)} sections found")
    
    # TEST 8: Edge case - empty text
    def test_extraction_with_empty_text(self):
        """Verify graceful handling of empty input"""
        result = self.extractor.extract("")
        
        assert result.bookmarks_found == False
        assert len(result.sections) == 1
        assert result.sections[0].title == "Document"
        
        print("✅ Empty text handled gracefully")
    
    # TEST 9: Edge case - TOC at end of document
    def test_toc_at_end_of_document(self):
        """Verify TOC can be found at end of book"""
        # Create text with TOC at the end (common in Arabic books)
        beginning = "Main content of the book... " * 100
        toc_at_end = """
        المحتويات
        
        الباب الأول
        5
        الباب الثاني
        20
        الباب الثالث
        35
        الباب الرابع
        50
        الباب الخامس
        65
        """
        
        sample_text = beginning + toc_at_end
        result = self.extractor.extract(sample_text)
        
        assert result.bookmarks_found == True
        assert len(result.sections) >= 5
        
        print("✅ TOC at end of document detected successfully")


# This is what runs when you execute: pytest tests/
if __name__ == "__main__":
    pytest.main([__file__, "-v"])  # -v means verbose (detailed output)