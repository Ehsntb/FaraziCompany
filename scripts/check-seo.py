"""Check static or PHP-rendered SEO output. Usage: python scripts/check-seo.py [--base-url http://127.0.0.1:8082/]"""
import argparse
import json
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(); self.nodes=[]; self.schemas=[]; self.schema=None; self.feed(source)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs); self.nodes.append((tag,attrs))
        if tag=='script' and attrs.get('type')=='application/ld+json': self.schema=''
    def handle_data(self, data):
        if self.schema is not None: self.schema+=data
    def handle_endtag(self, tag):
        if tag=='script' and self.schema is not None:
            self.schemas.append(json.loads(self.schema)); self.schema=None

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url');args=parser.parse_args()
    config=json.loads((ROOT/'seo-config.json').read_text(encoding='utf-8'));domain=config['siteUrl'].rstrip('/')
    def read(name):
        if args.base_url:
            with urlopen(urljoin(args.base_url.rstrip('/')+'/',name),timeout=15) as response:
                assert response.status==200, (name,response.status)
                return response.read().decode('utf-8')
        return (ROOT/name).read_text(encoding='utf-8')
    urls=[]; titles=set()
    for page,translations in config['pages'].items():
        for lang in ('fa','en'):
            name=page+('.en' if lang=='en' else '')+'.html';source=read(name);doc=Page(source)
            assert sum(tag=='h1' for tag,a in doc.nodes)==1, (name,'h1 count')
            html=next(a for t,a in doc.nodes if t=='html');assert html['lang']==lang
            title=translations[lang]['title'];assert title in unescape(source) and title not in titles; titles.add(title)
            canonical=[a['href'] for t,a in doc.nodes if t=='link' and a.get('rel')=='canonical'];assert canonical==[domain+'/'+name],(name,canonical)
            alternates={a['hreflang']:a['href'] for t,a in doc.nodes if t=='link' and a.get('rel')=='alternate' and 'hreflang' in a}
            assert alternates=={l:domain+'/'+page+('.en' if l=='en' else '')+'.html' for l in ('fa','en','x-default')},name
            assert any(t=='meta' and a.get('name')=='robots' and 'index, follow' in a.get('content','') for t,a in doc.nodes),name
            assert len(doc.schemas)==1 and doc.schemas[0]['url']==domain+'/'+name,name
            assert 'aggregateRating' not in json.dumps(doc.schemas),name
            for tag,attrs in doc.nodes:
                value=attrs.get('src') if tag in ('img','script') else attrs.get('href') if tag in ('a','link') else None
                if not value or value.startswith(('#','data:','mailto:','tel:')):continue
                link=urlsplit(value)
                if link.scheme or link.netloc:continue
                assert (ROOT/unquote(link.path)).is_file(),(name,value)
            if page in ('index','products'):
                for guide in ('lame-yarn','fancy-yarn'):
                    assert any(t=='a' and a.get('href')==guide+('.en' if lang=='en' else '')+'.html' for t,a in doc.nodes),(name,guide)
            urls.append(domain+'/'+name)
    sitemap=ET.fromstring(read('sitemap.xml')); listed=[x.text for x in sitemap.findall('.//{*}loc')]
    assert sorted(listed)==sorted(urls),'sitemap mismatch'
    assert domain+'/sitemap.xml' in read('robots.txt'),'robots sitemap missing'
    print(f'PASS: {len(urls)} pages, headings, metadata, canonical, languages, schema, assets, guide links and sitemap.')
if __name__=='__main__':main()
