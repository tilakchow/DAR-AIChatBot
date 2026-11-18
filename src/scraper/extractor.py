"""
DAR-12 · Extract JSONLD facts, FAQs and listings from pages.

Acceptance criteria (from DAR-12):
  ✓ Fixture tests extract FAQ pairs and project properties from a DarGlobal-style page
  ✓ Fixture tests extract price, rooms, area and district from a Wasalt-style page
  ✓ No seller or agent name appears in any extracted record

Design (section 5 — recon findings):
  DarGlobal page JSONLD @graph contains:
    - Organization
    - Place
    - RealEstateListing (additionalProperty: status, units, area, location)
    - FAQPage with question-and-answer pairs

  Wasalt category page JSONLD contains:
    - Offer items, each with:
      - url, price, priceCurrency (SAR)
      - availabilityStarts
      - itemOffered: name, address (district, city, postalCode),
                     numberOfRooms, numberOfBathroomsTotal, floorSize (sqm)
                     amenityFeature
      - seller (agent name) → MUST be dropped

  Personal data rule (DAR-12, risk R2):
    The seller field holds individuals' names. MUST NOT store it.
    Phone numbers and WhatsApp links are scrubbed in DAR-15.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class FAQPair:
    question: str
    answer: str
    source_url: str


@dataclass
class ProjectFact:
    """A set of structured facts about one DarGlobal project."""
    source_url: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    units: Optional[str] = None
    area: Optional[str] = None
    amenities: list[str] = field(default_factory=list)
    faq_pairs: list[FAQPair] = field(default_factory=list)
    raw_text: Optional[str] = None  # article body text (from HTML, added later)


@dataclass
class ListingOffer:
    """A single property listing from a Wasalt category page."""
    source_url: str           # the category page URL (not the listing URL)
    listing_url: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    price_currency: Optional[str] = None
    availability_starts: Optional[str] = None  # ISO date
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    num_rooms: Optional[int] = None
    num_bathrooms: Optional[int] = None
    floor_size_sqm: Optional[float] = None
    amenities: list[str] = field(default_factory=list)
    collection_date: Optional[str] = None
    # seller / agent fields are intentionally absent


# ---------------------------------------------------------------------------
# JSONLD extraction helpers
# ---------------------------------------------------------------------------

def _extract_jsonld_blocks(html: str) -> list[dict]:
    """Find all <script type="application/ld+json"> blocks and parse them."""
    blocks: list[dict] = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.debug("JSONLD parse error: %s", exc)
            continue
        if isinstance(parsed, list):
            blocks.extend(parsed)
        elif isinstance(parsed, dict):
            blocks.append(parsed)
    return blocks


def _get_type(item: dict) -> str:
    """Return the @type of a JSONLD item (handle list)."""
    t = item.get("@type", "")
    if isinstance(t, list):
        return " ".join(t)
    return str(t)


def _prop_value(props: list[dict], name: str) -> Optional[str]:
    """Find an additionalProperty value by name."""
    for p in props:
        if isinstance(p, dict) and p.get("name") == name:
            v = p.get("value") or p.get("unitText") or ""
            return str(v) if v else None
    return None


# ---------------------------------------------------------------------------
# DarGlobal extractor
# ---------------------------------------------------------------------------

def extract_darglobal(html: str, source_url: str) -> ProjectFact:
    """Extract structured facts from a DarGlobal project page."""
    blocks = _extract_jsonld_blocks(html)

    fact = ProjectFact(source_url=source_url)
    faq_pairs: list[FAQPair] = []

    # Walk the @graph array if present, or treat the whole block as a single item.
    all_items: list[dict] = []
    for block in blocks:
        if "@graph" in block:
            all_items.extend(block["@graph"])
        else:
            all_items.append(block)

    for item in all_items:
        t = _get_type(item)

        if "RealEstateListing" in t:
            fact.name = item.get("name") or fact.name
            fact.description = item.get("description") or fact.description
            props = item.get("additionalProperty", [])
            if isinstance(props, list):
                fact.status = _prop_value(props, "status") or fact.status
                fact.units = _prop_value(props, "units") or fact.units
                fact.area = _prop_value(props, "area") or fact.area
                fact.location = _prop_value(props, "location") or fact.location
            amenities = item.get("amenityFeature", [])
            if isinstance(amenities, list):
                fact.amenities = [
                    a.get("name", "") for a in amenities if isinstance(a, dict)
                ]

        elif "Place" in t:
            if not fact.location:
                addr = item.get("address", {})
                if isinstance(addr, dict):
                    parts = [
                        addr.get("streetAddress"),
                        addr.get("addressLocality"),
                        addr.get("addressCountry"),
                    ]
                    fact.location = ", ".join(p for p in parts if p)
                elif isinstance(addr, str):
                    fact.location = addr

        elif "FAQPage" in t:
            main_entity = item.get("mainEntity", [])
            if isinstance(main_entity, list):
                for qa in main_entity:
                    if not isinstance(qa, dict):
                        continue
                    q = qa.get("name") or qa.get("question", "")
                    a_obj = qa.get("acceptedAnswer", {})
                    a = (
                        a_obj.get("text", "") if isinstance(a_obj, dict)
                        else str(a_obj)
                    )
                    if q and a:
                        faq_pairs.append(FAQPair(
                            question=q.strip(),
                            answer=a.strip(),
                            source_url=source_url,
                        ))

    fact.faq_pairs = faq_pairs
    return fact


# ---------------------------------------------------------------------------
# Wasalt extractor
# ---------------------------------------------------------------------------

_PHONE_RE = re.compile(
    r"""(?:(?:\+|00)966|05)[\s\-]?\d[\s\-]?\d{3}[\s\-]?\d{4}"""
    r"""|(?:\+|00)[1-9]\d{6,14}""",
    re.VERBOSE,
)


def _drop_pii(d: dict) -> dict:
    """Remove known PII fields from a dict (seller, agent, phone, whatsapp)."""
    PII_FIELDS = {"seller", "agent", "phone", "telephone", "whatsapp", "contactPoint"}
    return {k: v for k, v in d.items() if k.lower() not in {f.lower() for f in PII_FIELDS}}


def extract_wasalt(html: str, source_url: str, collection_date: str = "") -> list[ListingOffer]:
    """Extract listing offers from a Wasalt category page."""
    blocks = _extract_jsonld_blocks(html)
    offers: list[ListingOffer] = []

    all_items: list[dict] = []
    for block in blocks:
        if "@graph" in block:
            all_items.extend(block["@graph"])
        else:
            all_items.append(block)

    for item in all_items:
        t = _get_type(item)

        # Offers can appear directly or inside a Product/ItemList
        if "Offer" in t:
            offer = _parse_wasalt_offer(item, source_url, collection_date)
            if offer:
                offers.append(offer)

        elif "ItemList" in t or "ItemPage" in t or "Product" in t:
            # Offers may be nested
            for sub in item.get("offers", []) or item.get("itemListElement", []):
                if isinstance(sub, dict):
                    sub_t = _get_type(sub)
                    if "Offer" in sub_t or True:  # try anyway
                        offer = _parse_wasalt_offer(sub, source_url, collection_date)
                        if offer:
                            offers.append(offer)

    return offers


def _parse_wasalt_offer(item: dict, source_url: str, collection_date: str) -> Optional[ListingOffer]:
    """Parse a single Offer item, dropping all PII fields."""
    # Drop seller and agent before anything else.
    item = _drop_pii(item)

    offered = item.get("itemOffered", {})
    if isinstance(offered, dict):
        offered = _drop_pii(offered)
    else:
        offered = {}

    # Address
    addr = offered.get("address", {}) or {}
    if isinstance(addr, str):
        addr = {}

    # Price
    price_raw = item.get("price") or item.get("lowPrice") or item.get("highPrice")
    price: Optional[float] = None
    if price_raw is not None:
        try:
            price = float(str(price_raw).replace(",", ""))
        except (ValueError, TypeError):
            pass

    # Rooms / bathrooms
    rooms_raw = offered.get("numberOfRooms")
    rooms: Optional[int] = None
    if rooms_raw is not None:
        try:
            rooms = int(rooms_raw)
        except (ValueError, TypeError):
            pass

    baths_raw = offered.get("numberOfBathroomsTotal")
    baths: Optional[int] = None
    if baths_raw is not None:
        try:
            baths = int(baths_raw)
        except (ValueError, TypeError):
            pass

    # Floor size
    fs = offered.get("floorSize", {})
    floor_size: Optional[float] = None
    if isinstance(fs, dict):
        fs_val = fs.get("value")
        if fs_val is not None:
            try:
                floor_size = float(fs_val)
            except (ValueError, TypeError):
                pass
    elif fs:
        try:
            floor_size = float(fs)
        except (ValueError, TypeError):
            pass

    # Amenities
    amenities = []
    for feat in offered.get("amenityFeature", []):
        if isinstance(feat, dict):
            n = feat.get("name")
            if n:
                amenities.append(str(n))

    # Listing URL
    listing_url = item.get("url") or offered.get("url")

    # Sanity check: skip items with no useful data
    if price is None and not offered.get("name") and not listing_url:
        return None

    return ListingOffer(
        source_url=source_url,
        listing_url=listing_url,
        name=offered.get("name"),
        price=price,
        price_currency=item.get("priceCurrency", "SAR"),
        availability_starts=item.get("availabilityStarts"),
        district=addr.get("streetAddress") or addr.get("addressLocality"),
        city=addr.get("addressLocality") or addr.get("addressRegion"),
        postal_code=addr.get("postalCode"),
        num_rooms=rooms,
        num_bathrooms=baths,
        floor_size_sqm=floor_size,
        amenities=amenities,
        collection_date=collection_date,
    )
