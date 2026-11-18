import sys, os
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('.'))

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
data = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://darglobal.co.uk/the-astera/</loc></url>'
    b'</urlset>'
)

root = ET.fromstring(data)
print('root.tag:', root.tag)
print('expected urlset tag:', f'{{{NS}}}urlset')
print('match:', root.tag == f'{{{NS}}}urlset')
print()

# Check the parse_sitemap logic
from src.scraper.sitemap import _parse_urlset, _parse_sitemapindex, _ns, _text

tag = root.tag
print('tag is ns urlset:', tag == f'{{{NS}}}urlset' or tag == 'urlset')
print('tag check in code:')
print('  tag == ns(urlset):', tag == f'{{{NS}}}urlset')
print('  tag == urlset:', tag == 'urlset')

# Check _parse_urlset directly
entries, children = _parse_urlset(root)
print('_parse_urlset entries:', entries)

# Check iterfind
print()
print('iterfind _ns(url):', list(root.iterfind(_ns('url'))))
print('_ns("url"):', _ns('url'))
