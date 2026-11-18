import xml.etree.ElementTree as ET
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
xml = b'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://darglobal.co.uk/the-astera/</loc></url></urlset>'
root = ET.fromstring(xml)
print('tag:', root.tag)
print('ns match:', root.tag == f'{{{NS}}}urlset')
urls = list(root.iterfind(f'{{{NS}}}url'))
print('url elements:', len(urls))
for u in urls:
    loc = u.find(f'{{{NS}}}loc')
    print('  loc:', loc.text if loc is not None else 'NONE')
