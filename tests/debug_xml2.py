import xml.etree.ElementTree as ET

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'

data = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b'<url><loc>https://darglobal.co.uk/the-astera/</loc></url>'
    b'</urlset>'
)

root = ET.fromstring(data)
print('root tag:', root.tag)
print('root tag == ns urlset:', root.tag == f'{{{NS}}}urlset')

# Try different find approaches
print('iterfind with ns:', list(root.iterfind(f'{{{NS}}}url')))
print('iterfind without ns:', list(root.iterfind('url')))
print('direct children:', list(root))
for child in root:
    print('  child tag:', child.tag)
