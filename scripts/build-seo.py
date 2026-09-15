"""Generate static bilingual HTML and SEO metadata. Python 3 + Node, no packages.
Edit the Persian HTML/data-en attributes, products-data.js and seo-config.json.
Run: python scripts/build-seo.py
"""
from html.parser import HTMLParser
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import json, subprocess, copy, datetime

ROOT = Path(__file__).resolve().parent.parent
VOID = set("area base br col embed hr img input link meta param source track wbr".split())

class Node:
    def __init__(self, tag="", attrs=(), raw=None):
        self.tag, self.attrs, self.children, self.raw = tag, dict(attrs), [], raw
    def html(self):
        if self.raw is not None: return self.raw
        attrs = "".join(" "+k+('="'+escape(str(v), quote=True)+'"' if v is not None else "") for k,v in self.attrs.items())
        start = "<"+self.tag+attrs+">" if self.tag else ""
        return start + "".join(c.html() for c in self.children) + ("</"+self.tag+">" if self.tag and self.tag not in VOID else "")
    def all(self):
        yield self
        for child in self.children: yield from child.all()
    def set_html(self, value): self.children = parse(value).children

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root=Node(); self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs); self.stack[-1].children.append(n)
        if tag not in VOID: self.stack.append(n)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID: self.handle_endtag(tag)
    def handle_endtag(self,tag):
        if len(self.stack)>1 and self.stack[-1].tag==tag: self.stack.pop()
    def raw(self,text): self.stack[-1].children.append(Node(raw=text))
    def handle_data(self,data): self.raw(data)
    def handle_entityref(self,name): self.raw("&"+name+";")
    def handle_charref(self,name): self.raw("&#"+name+";")
    def handle_decl(self,data): self.raw("<!"+data+">")
    def handle_comment(self,data): self.raw("<!--"+data+"-->")
def parse(text):
    p=Parser(); p.feed(text); return p.root
def find(root, predicate): return next(n for n in root.all() if predicate(n))
def esc(text): return escape(str(text),quote=True)
def file_for(page,lang): return page+(".en" if lang=="en" else "")+".html"

config=json.loads((ROOT/"seo-config.json").read_text(encoding="utf-8-sig"))
base=config["siteUrl"].strip().rstrip("/")
if base:
    u=urlsplit(base)
    if u.scheme!="https" or not u.netloc or u.query or u.fragment or u.username or u.password:
        raise ValueError("siteUrl must be the final HTTPS base URL, without query/fragment/credentials")
def absolute(path): return base+"/"+path
products=json.loads(subprocess.check_output(["node","-e",
    "global.window={};require('./products-data.js');process.stdout.write(JSON.stringify(window.FARAZI_PRODUCTS));"],
    cwd=ROOT,encoding="utf-8"))
for p in products:
    for lang in ("fa","en"):
        assert p["name"][lang] and p["description"][lang], "Missing product translation"
    assert p.get("images"), "Each product needs at least one image"
    for image in p["images"]:
        assert (ROOT/image).is_file(), "Missing product image: "+image
    p["image"]=p["images"][0]
    assert isinstance(p.get("featured",False),bool)
    assert isinstance(p["showOnHome"],bool)

urls=[]
for page,translations in config["pages"].items():
    source=parse((ROOT/(page+".html")).read_text(encoding="utf-8-sig"))
    for lang in ("fa","en"):
        root=copy.deepcopy(source)
        for n in list(root.all()):
            if "data-en" in n.attrs:
                fa=n.attrs.get("data-fa","".join(c.html() for c in n.children))
                # Keep Persian source text editable; only English needs a Persian fallback.
                if lang=="en":
                    n.attrs["data-fa"]=fa; n.set_html(n.attrs["data-en"])
                else:
                    n.attrs.pop("data-fa",None)
            if lang=="en":
                labels={"فرازی کمپانی، صفحه اصلی":"Farazi Company, home","منوی اصلی":"Main navigation","زبان سایت":"Site language","باز کردن منو":"Open menu","بستن پنجره":"Close dialog","مسیر صفحه":"Breadcrumb","راه‌های ارتباطی":"Contact methods","مزیت‌های فرازی کمپانی":"Why Farazi Company","تصویرسازی الهام‌گرفته از معماری بازار تهران":"Illustration inspired by Tehran Bazaar architecture","تصویرسازی معماری بازار تهران":"Illustration of Tehran Bazaar architecture","نخ‌های پنبه‌ای، مشکی و مسی در کنار یکدیگر":"Ivory, black and copper yarn spools","نقشه ارتباطات تجاری در سراسر جهان":"Illustration of global trade connections","تجربه و همکاری":"Experience and cooperation"}
                for attr in ("aria-label","alt"):
                    if n.attrs.get(attr) in labels: n.attrs[attr]=labels[n.attrs[attr]]
            if n.tag=="html": n.attrs.update(lang=lang,dir="rtl" if lang=="fa" else "ltr")
            if "data-copyright-year" in n.attrs: n.set_html(str(datetime.date.today().year))
            if "data-language" in n.attrs:
                n.tag="a"; n.attrs.pop("type",None); n.attrs.pop("aria-pressed",None)
                target=n.attrs["data-language"]
                n.attrs.update(href=file_for(page,target),hreflang=target)
                n.attrs["aria-current"]="page" if target==lang else "false"
            elif n.tag=="a" and n.attrs.get("href","").split("?")[0].split("#")[0].endswith(".html"):
                u=urlsplit(n.attrs["href"])
                stem=Path(u.path).name.replace(".en.html","").replace(".html","")
                if not u.netloc and stem in config["pages"]:
                    n.attrs["href"]=file_for(stem,lang)+("#"+u.fragment if u.fragment else "")
            if n.attrs.get("id") in ("catalog-list","product-grid"):
                catalog=n.attrs["id"]=="catalog-list"
                items=products if catalog else [p for p in products if p["showOnHome"]]
                cards=[]
                for i,p in enumerate(products):
                    if p not in items: continue
                    name,desc=esc(p["name"][lang]),esc(p["description"][lang])
                    loading="eager" if catalog and p.get("featured") else "lazy"
                    img='<img src="'+esc(p["image"])+'" alt="'+name+'" loading="'+loading+'" decoding="async">'
                    if catalog:
                        featured=p.get("featured",False)
                        count=(('<span class="photo-count">'+str(len(p["images"]))+" "+("تصویر" if lang=="fa" else "photos")+'</span>') if len(p["images"])>1 else "")
                        specialty=(('<p class="product-specialty">'+("۱۵ سال تخصص در واردات و تجارت نخ لمه" if lang=="fa" else "15 years of specialized Lurex trading")+'</p>') if featured else "")
                        action=("مشاهده گالری" if len(p["images"])>1 else "مشاهده جزئیات") if lang=="fa" else ("View gallery" if len(p["images"])>1 else "View details")
                        cards.append('<article class="catalog-product'+(" catalog-product-featured" if featured else "")+'"><button class="catalog-product-trigger" type="button" data-product="'+str(i)+'"><div class="catalog-photo">'+img+count+'</div><div class="catalog-copy">'+specialty+'<h2>'+name+'</h2><div class="catalog-rule"></div><p>'+desc+'</p><span class="catalog-action">'+action+' <span aria-hidden="true">←</span></span></div></button></article>')
                    else:
                        cards.append('<button class="product-card" type="button" data-product="'+str(i)+'"><div class="asset-frame product-art">'+img+'</div><div class="product-info"><h3>'+name+'</h3><span class="view-label">'+("مشاهده" if lang=="fa" else "View")+'</span></div></button>')
                n.set_html("".join(cards))
                if not catalog: n.attrs["style"]="--home-columns: "+str(min(len(items),7))
            if n.attrs.get("id")=="catalog-empty":
                if products: n.attrs["hidden"]=None
                else: n.attrs.pop("hidden",None)
            if "products-section" in n.attrs.get("class","").split():
                if any(p["showOnHome"] for p in products): n.attrs.pop("hidden",None)
                else: n.attrs["hidden"]=None
        head=find(root,lambda n:n.tag=="head")
        head.children=[n for n in head.children if not (
            n.tag=="title" or n.attrs.get("name") in ("description","robots") or
            n.attrs.get("data-seo") is not None)]
        info=translations[lang]
        metadata='<title>'+esc(info["title"])+'</title>\n<meta name="description" content="'+esc(info["description"])+'">\n'
        def meta(key,value,property=False):
            return '<meta data-seo="true" '+("property" if property else "name")+'="'+key+'" content="'+esc(value)+'">\n'
        metadata+=meta("robots","index, follow, max-image-preview:large")
        for key,value in {"og:type":"website","og:site_name":config["siteName"],"og:title":info["title"],"og:description":info["description"],"og:locale":"fa_IR" if lang=="fa" else "en_US","og:locale:alternate":"en_US" if lang=="fa" else "fa_IR"}.items():
            metadata+=meta(key,value,True)
        metadata+=meta("twitter:card","summary_large_image")+meta("twitter:title",info["title"])+meta("twitter:description",info["description"])
        schema={"@context":"https://schema.org","@type":{"about":"AboutPage","contact":"ContactPage","products":"CollectionPage"}.get(page,"WebPage"),"name":info["title"],"description":info["description"],"inLanguage":lang,"publisher":{"@type":"Organization","name":config["siteName"],"alternateName":"فرازی کمپانی"}}
        if base:
            url=absolute(file_for(page,lang)); urls.append(url)
            metadata+='<link data-seo="true" rel="canonical" href="'+esc(url)+'">\n'
            for target in ("fa","en","x-default"):
                metadata+='<link data-seo="true" rel="alternate" hreflang="'+target+'" href="'+esc(absolute(file_for(page,"fa" if target=="x-default" else target)))+'">\n'
            metadata+=meta("og:url",url,True)+meta("og:image",absolute(config["socialImage"]),True)+meta("og:image:alt","Farazi Company textile yarns",True)+meta("twitter:image",absolute(config["socialImage"]))
            schema.update(url=url)
            schema["publisher"].update({"@id":absolute("index.html")+"#organization","url":absolute("index.html"),"logo":absolute("logo/farazi-logo-transparent.png")})
            if page!="index":
                schema["breadcrumb"]={"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"خانه" if lang=="fa" else "Home","item":absolute(file_for("index",lang))},{"@type":"ListItem","position":2,"name":info["title"],"item":url}]}
        if page=="products":
            schema["mainEntity"]={"@type":"ItemList","numberOfItems":len(products),"itemListElement":[{"@type":"ListItem","position":i+1,"item":{"@type":"Thing","name":p["name"][lang],"description":p["description"][lang],**({"image":absolute(p["images"][0])} if base else {})}} for i,p in enumerate(products)]}
        metadata+='<script data-seo="true" type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace("<","\\u003c")+'</script>\n'
        head.children.extend(parse(metadata).children)
        (ROOT/file_for(page,lang)).write_text(root.html(),encoding="utf-8")
robots="User-agent: *\nAllow: /\n"
if base:
    robots+="\nSitemap: "+absolute("sitemap.xml")+"\n"
    (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join("<url><loc>"+esc(u)+"</loc></url>" for u in urls)+"\n</urlset>\n",encoding="utf-8")
elif (ROOT/"sitemap.xml").exists():
    raise ValueError("Existing sitemap found but siteUrl is empty. Set the production URL before regenerating.")
(ROOT/"robots.txt").write_text(robots,encoding="utf-8")
print("Generated 8 static pages, product HTML, social metadata, schema and robots.txt.")
print("Canonical/hreflang/sitemap ready." if base else "Production domain pending: set siteUrl in seo-config.json and rerun.")

