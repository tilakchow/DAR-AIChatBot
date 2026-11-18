import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

from src.processing.cleaner import clean_text, scrub_pii
from src.processing.chunker import (
    chunk_faq,
    chunk_listing,
    chunk_page_text,
    detect_language,
    DocumentChunk
)

# ---------------------------------------------------------------------------
# DAR-15 Tests: Cleaner and PII scrubbing
# ---------------------------------------------------------------------------

class TestCleanerAndPIIScrubbing:
    def test_phone_numbers_removed(self):
        sample = (
            "Contact our agent at +966 50 123 4567 or call 0512345678. "
            "International office: +44 20 7946 0991."
        )
        cleaned = scrub_pii(sample)
        assert "+966" not in cleaned
        assert "0512345678" not in cleaned
        assert "+44 20" not in cleaned
        assert "[PHONE_REMOVED]" in cleaned

    def test_emails_removed(self):
        sample = "For inquiries email sales@darglobal.co.uk or info.support@wasalt.sa."
        cleaned = scrub_pii(sample)
        assert "sales@darglobal.co.uk" not in cleaned
        assert "info.support@wasalt.sa" not in cleaned
        assert "[EMAIL_REMOVED]" in cleaned

    def test_prices_preserved(self):
        sample = "Starting from AED 2,150,000 up to SAR 15,500,000."
        cleaned = clean_text(sample)
        assert "2,150,000" in cleaned
        assert "15,500,000" in cleaned

    def test_area_ranges_and_dates_preserved(self):
        sample = "Units range from 120.5 sqm to 450 sqm. Available from 2026-11-18 until 2028-12-31."
        cleaned = clean_text(sample)
        assert "120.5 sqm" in cleaned
        assert "450 sqm" in cleaned
        assert "2026-11-18" in cleaned
        assert "2028-12-31" in cleaned

    def test_boilerplate_removed(self):
        sample = (
            "The Astera offers beachfront living.\n"
            "Accept all cookies. By continuing to browse this site, you agree to our use of cookies.\n"
            "All rights reserved. Copyright © 2026 DarGlobal."
        )
        cleaned = clean_text(sample)
        assert "The Astera offers beachfront living." in cleaned
        assert "Accept all cookies" not in cleaned
        assert "agree to our use of cookies" not in cleaned
        assert "All rights reserved" not in cleaned


# ---------------------------------------------------------------------------
# DAR-16 Tests: Chunker
# ---------------------------------------------------------------------------

class TestChunker:
    def test_faq_chunk(self):
        faq = {
            "question": "What is the starting price for The Astera?",
            "answer": "Starting price is AED 2,150,000.",
            "source_url": "https://darglobal.co.uk/the-astera"
        }
        chunk = chunk_faq(faq, site="darglobal", collection_date="2026-11-18")
        assert chunk.chunk_type == "faq"
        assert chunk.site == "darglobal"
        assert chunk.url == "https://darglobal.co.uk/the-astera"
        assert chunk.title == "What is the starting price for The Astera?"
        assert chunk.language == "en"
        assert chunk.collection_date == "2026-11-18"
        assert "AED 2,150,000" in chunk.content

    def test_listing_chunk(self):
        offer = {
            "source_url": "https://wasalt.sa/en/villas-for-sale-in-riyadh",
            "listing_url": "https://wasalt.sa/en/property/villa-101",
            "name": "Luxury Villa in Al Narjis",
            "price": 3500000.0,
            "price_currency": "SAR",
            "num_rooms": 5,
            "num_bathrooms": 6,
            "floor_size_sqm": 450.0,
            "district": "Al Narjis",
            "city": "Riyadh",
            "amenities": ["Pool", "Elevator"]
        }
        chunk = chunk_listing(offer, collection_date="2026-11-18")
        assert chunk.chunk_type == "listing"
        assert chunk.site == "wasalt"
        assert chunk.collection_date == "2026-11-18"
        assert "3,500,000 SAR" in chunk.content
        assert "Al Narjis, Riyadh" in chunk.content
        assert "Source: Wasalt.sa" in chunk.content
        assert "Pool, Elevator" in chunk.content

    def test_page_chunking_length_cap(self):
        long_text = "\n".join([f"Paragraph {i}: This is high-end luxury real estate content with great details." for i in range(100)])
        chunks = chunk_page_text(
            text=long_text,
            url="https://darglobal.co.uk/the-astera",
            title="The Astera",
            site="darglobal",
            collection_date="2026-11-18",
            max_chunk_chars=1000
        )
        assert len(chunks) > 1
        for ch in chunks:
            assert len(ch.content) <= 1500
            assert ch.site == "darglobal"
            assert ch.url == "https://darglobal.co.uk/the-astera"
            assert ch.title == "The Astera"
            assert ch.collection_date == "2026-11-18"

    def test_language_detection(self):
        assert detect_language("This is a luxury apartment in Dubai.") == "en"
        assert detect_language("فيلا فاخرة للبيع في حي النرجس بالرياض.") == "ar"
