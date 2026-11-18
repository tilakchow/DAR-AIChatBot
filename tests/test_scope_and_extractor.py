import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

from src.scraper.scope import DARGLOBAL_SCOPE, WASALT_SCOPE, CrawlScope, DARGLOBAL_CONFIG, WASALT_CONFIG
from src.scraper.extractor import (
    extract_darglobal,
    extract_wasalt,
    ProjectFact,
    ListingOffer,
    FAQPair
)

# ---------------------------------------------------------------------------
# DAR-11 Tests: Scope and caps
# ---------------------------------------------------------------------------

class TestCrawlScope:
    def test_darglobal_allowed_urls(self):
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/the-astera/") is True
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/blog/news-update") is True
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/press/release-1") is True
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/insights/market-report") is True

    def test_darglobal_disallowed_urls(self):
        # Query params (tracking, etc.)
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/the-astera/?utm_source=google") is False
        # Forms / cart / contact / admin
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/contact-us") is False
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/thank-you") is False
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/checkout") is False
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/wp-admin/") is False
        assert DARGLOBAL_SCOPE.is_in_scope("https://darglobal.co.uk/brochure.pdf") is False

    def test_wasalt_allowed_category_urls(self):
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/en/villas-for-sale-in-riyadh") is True
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/en/apartments-for-rent") is True
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/ar/villas-for-sale") is True

    def test_wasalt_disallowed_urls(self):
        # Search and CDN
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/search?q=riyadh") is False
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/cdn-cgi/rum") is False
        # Individual listing pages or agent pages
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/en/property/villa-12345") is False
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/en/agent/john-doe") is False
        assert WASALT_SCOPE.is_in_scope("https://wasalt.sa/en/login") is False


# ---------------------------------------------------------------------------
# DAR-12 Tests: Fixtures and JSON-LD Extraction
# ---------------------------------------------------------------------------

DARGLOBAL_FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "RealEstateListing",
      "name": "The Astera, Interiors by Aston Martin",
      "description": "Exclusive beachfront residences on Al Marjan Island.",
      "additionalProperty": [
        {"@type": "PropertyValue", "name": "status", "value": "Under Construction"},
        {"@type": "PropertyValue", "name": "units", "value": "1, 2, 3 Bedroom Apartments & Villas"},
        {"@type": "PropertyValue", "name": "area", "value": "Ras Al Khaimah"},
        {"@type": "PropertyValue", "name": "location", "value": "Al Marjan Island"}
      ],
      "amenityFeature": [
        {"@type": "LocationFeatureSpecification", "name": "Infinity Pool"},
        {"@type": "LocationFeatureSpecification", "name": "Private Beach"}
      ]
    },
    {
      "@type": "Place",
      "name": "Al Marjan Island",
      "address": {
        "@type": "PostalAddress",
        "addressLocality": "Ras Al Khaimah",
        "addressCountry": "United Arab Emirates"
      }
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is the expected completion date?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The completion is scheduled for December 2028."
          }
        },
        {
          "@type": "Question",
          "name": "What are the starting prices?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Starting prices begin from AED 2,150,000."
          }
        }
      ]
    }
  ]
}
</script>
</head>
<body><h1>The Astera</h1></body>
</html>
"""

WASALT_FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "itemListElement": [
    {
      "@type": "Offer",
      "url": "https://wasalt.sa/en/property/luxury-villa-al-narjis-101",
      "price": "3,200,000",
      "priceCurrency": "SAR",
      "availabilityStarts": "2026-11-01",
      "seller": {
        "@type": "RealEstateAgent",
        "name": "Mohammed Al-Otaibi",
        "telephone": "+966501234567"
      },
      "itemOffered": {
        "@type": "SingleFamilyResidence",
        "name": "Modern Villa in Al Narjis",
        "numberOfRooms": 5,
        "numberOfBathroomsTotal": 6,
        "floorSize": {
          "@type": "QuantitativeValue",
          "value": 420.5
        },
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "Al Narjis District",
          "addressLocality": "Riyadh",
          "postalCode": "13324"
        },
        "amenityFeature": [
          {"@type": "LocationFeatureSpecification", "name": "Driver Room"},
          {"@type": "LocationFeatureSpecification", "name": "Elevator"}
        ]
      }
    }
  ]
}
</script>
</head>
<body><h1>Villas for sale in Riyadh</h1></body>
</html>
"""

class TestExtraction:
    def test_darglobal_extraction(self):
        fact = extract_darglobal(DARGLOBAL_FIXTURE_HTML, "https://darglobal.co.uk/the-astera/")
        assert fact.name == "The Astera, Interiors by Aston Martin"
        assert fact.status == "Under Construction"
        assert fact.units == "1, 2, 3 Bedroom Apartments & Villas"
        assert fact.area == "Ras Al Khaimah"
        assert "Infinity Pool" in fact.amenities
        assert len(fact.faq_pairs) == 2
        assert fact.faq_pairs[0].question == "What is the expected completion date?"
        assert fact.faq_pairs[0].answer == "The completion is scheduled for December 2028."

    def test_wasalt_extraction_and_pii_removal(self):
        offers = extract_wasalt(WASALT_FIXTURE_HTML, "https://wasalt.sa/en/villas-for-sale-in-riyadh", "2026-11-18")
        assert len(offers) == 1
        offer = offers[0]
        assert offer.price == 3200000.0
        assert offer.price_currency == "SAR"
        assert offer.num_rooms == 5
        assert offer.num_bathrooms == 6
        assert offer.floor_size_sqm == 420.5
        assert offer.district == "Al Narjis District"
        assert offer.city == "Riyadh"
        assert offer.postal_code == "13324"
        assert "Driver Room" in offer.amenities

        # Acceptance Criterion: No seller or agent name appears in any extracted record
        record_dump = str(offer.__dict__)
        assert "Mohammed" not in record_dump
        assert "Al-Otaibi" not in record_dump
        assert "966501234567" not in record_dump
        assert "seller" not in offer.__dict__
