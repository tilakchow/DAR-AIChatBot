import sys, os
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('.'))
from src.scraper.sitemap import _ns, _text

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
data = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://darglobal.co.uk/the-astera/</loc></url>'
    b'</urlset>'
)
root = ET.fromstring(data)

print('_ns(url):', _ns('url'))

# Manually replicate _parse_urlset
entries = []
for url_el in root.iterfind(_ns("url")):
    print('  url_el found:', url_el)
    loc_raw = _text(url_el, "loc")
    print('  loc_raw:', loc_raw)

# Is _ns working?
import src.scraper.sitemap as sm
print('sm._SITEMAP_NS:', sm._SITEMAP_NS)
print('sm._ns("url"):', sm._ns("url"))
print('expected:', f'{{{NS}}}url')
print('match:', sm._ns("url") == f'{{{NS}}}url')
