import sys, os, gzip, io, unittest.mock as mock
sys.path.insert(0, os.path.abspath('.'))
from src.scraper.sitemap import parse_sitemap, normalise_url, SitemapDiscovery

passed = 0; failed = 0
def check(name, got, expected):
    global passed, failed
    if got == expected:
        print(f'  PASS  {name}')
        passed += 1
    else:
        print(f'  FAIL  {name}: expected {expected!r}, got {got!r}')
        failed += 1

def _gz(data):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as f:
        f.write(data)
    return buf.getvalue()

# Build XML without using &apos; in the bytes literal
# (use a separate <url> for the apostrophe case)
URLSET = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://darglobal.co.uk/the-astera/</loc><lastmod>2026-11-10</lastmod><priority>0.8</priority></url>'
    b"<url><loc>https://darglobal.co.uk/trump&apos;s-corner/</loc></url>"
    b'<url><loc>https://darglobal.co.uk/the astera luxury/</loc></url>'
    b'</urlset>'
)

SITEMAPIDX = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<sitemap><loc>https://cdn.wasalt.sa/en.xml.gz</loc></sitemap>'
    b'<sitemap><loc>https://cdn.wasalt.sa/ar.xml.gz</loc></sitemap>'
    b'</sitemapindex>'
)

CHILD = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://wasalt.sa/en/villas-riyadh</loc></url>'
    b'</urlset>'
)

print('=== normalise_url ===')
check('apos decoded', '&apos;' not in normalise_url("https://x.com/trump&apos;s/"), True)
check('amp decoded', '&amp;' not in normalise_url("https://x.com/p&amp;q=1"), True)
check('space encoded', ' ' not in normalise_url("https://x.com/the astera luxury/"), True)
check('normal unchanged', normalise_url("https://darglobal.co.uk/the-astera/"), "https://darglobal.co.uk/the-astera/")
check('whitespace stripped', normalise_url("  https://x.com/p  "), "https://x.com/p")

print('=== parse urlset ===')
entries, children = parse_sitemap(URLSET, 'test')
print(f'  DEBUG: entries={len(entries)}, children={len(children)}')
if entries:
    print(f'  DEBUG: entry[0].loc={entries[0].loc!r}')
check('urlset entry count', len(entries), 3)
check('no children', children, [])
if len(entries) >= 3:
    check('first loc', entries[0].loc, 'https://darglobal.co.uk/the-astera/')
    check('lastmod', entries[0].lastmod, '2026-11-10')
    check('priority', entries[0].priority, 0.8)
    check('apos decoded in loc', '&apos;' not in entries[1].loc, True)
    check('space encoded', ' ' not in entries[2].loc, True)

gz_entries, gz_ch = parse_sitemap(_gz(URLSET), 'test.gz')
check('gzip urlset count', len(gz_entries), 3)
check('gzip no children', gz_ch, [])

print('=== parse sitemapindex ===')
e2, c2 = parse_sitemap(SITEMAPIDX, 'idx')
check('index no entries', e2, [])
check('index 2 children', len(c2), 2)
check('child url in list', 'https://cdn.wasalt.sa/en.xml.gz' in c2, True)

print('=== gzip sitemapindex ===')
e3, c3 = parse_sitemap(_gz(SITEMAPIDX), 'idx.gz')
check('gz index no entries', e3, [])
check('gz index 2 children', len(c3), 2)

print('=== SitemapDiscovery recursive ===')
url_map = {
    'https://wasalt.sa/sitemap_index.xml': SITEMAPIDX,
    'https://cdn.wasalt.sa/en.xml.gz': _gz(CHILD),
    'https://cdn.wasalt.sa/ar.xml.gz': _gz(CHILD),
}
def fake_open(req, timeout):
    body = url_map.get(req.full_url, b'<urlset></urlset>')
    class R:
        def read(self): return body
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return R()
disco = SitemapDiscovery()
with mock.patch('urllib.request.urlopen', side_effect=fake_open):
    result = disco.discover('https://wasalt.sa/sitemap_index.xml')
check('recursive discovery 2 entries', len(result), 2)

result2 = disco.discover('http://localhost:1/sitemap.xml')
check('unreachable returns []', result2, [])

class BadResp:
    def read(self): return b'<not valid xml ><'
    def __enter__(self): return self
    def __exit__(self, *a): pass
with mock.patch('urllib.request.urlopen', return_value=BadResp()):
    r = disco.discover('https://example.com/broken.xml')
check('malformed xml returns []', r, [])

class GoodResp:
    def read(self): return URLSET
    def __enter__(self): return self
    def __exit__(self, *a): pass
with mock.patch('urllib.request.urlopen', return_value=GoodResp()):
    r2 = disco.discover('https://darglobal.co.uk/sitemap.xml')
check('plain urlset discovery', len(r2), 3)

print(f'\n=== RESULT: {passed} passed, {failed} failed ===')
