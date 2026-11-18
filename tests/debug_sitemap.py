import sys, os
sys.path.insert(0, os.path.abspath('.'))

# Force reload
import importlib
import src.scraper.sitemap
importlib.reload(src.scraper.sitemap)
from src.scraper.sitemap import parse_sitemap

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
data = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://darglobal.co.uk/the-astera/</loc></url>'
    b'</urlset>'
)
entries, children = parse_sitemap(data, 'test')
print('entries:', entries)
print('children:', children)
print('sitemap.py location:', src.scraper.sitemap.__file__)
