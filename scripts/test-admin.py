"""Integration checks against an isolated copy, never against the real catalog.
Run: python scripts/test-admin.py. --preview keeps a fixture on port 8093 for UI QA.
"""
import argparse, hashlib, http.cookiejar, json, re, shutil, subprocess, tempfile, time
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parent.parent
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--preview',action='store_true'); args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='farazi-admin-test-') as directory:
        root=Path(directory)
        for name in ['admin','scripts','logo']:
            shutil.copytree(ROOT/name,root/name)
        for name in ['products-data.js','router.php','site.php','seo-config.json']:
            shutil.copy2(ROOT/name,root/name)
        for path in ROOT.glob('*.html'): shutil.copy2(path,root/path.name)
        for name in ['styles.css','pages.css','script.js','gallery-data.js']:
            if (ROOT/name).exists(): shutil.copy2(ROOT/name,root/name)
        shutil.copytree(ROOT/'assets/fonts',root/'assets/fonts')
        source=(root/'products-data.js').read_text(encoding='utf-8')
        products=json.loads(re.search(r'=\s*(\[.*\])\s*;',source,re.S)[1])
        for product in products:
            for name in product['images']:
                target=root/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,target)
        setup=subprocess.check_output(['php','scripts/setup-admin.php'],cwd=root,text=True)
        token=re.search(r'setup=([a-f0-9]+)',setup)[1]
        proc=subprocess.Popen(['php','-S','127.0.0.1:8093','router.php'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            base='http://127.0.0.1:8093/'
            client=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
            def get(path): return client.open(base+path).read().decode()
            for _ in range(50):
                try: get('admin/'); break
                except OSError: time.sleep(.1)
            def fields(html): return dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"',html))
            def post(data, files=None):
                if files:
                    boundary='FaraziTestBoundary'; body=b''
                    for k,v in data.items(): body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for name,content in files:
                        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="photos[]"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+content+b'\r\n'
                    body+=f'--{boundary}--\r\n'.encode(); mime='multipart/form-data; boundary='+boundary
                else: body=urlencode(data).encode(); mime='application/x-www-form-urlencoded'
                return client.open(Request(base+'admin/',body,{'Content-Type':mime})).read().decode()
            def catalog(): return json.loads(re.search(r'=\s*(\[.*\])\s*;', (root/'products-data.js').read_text(encoding='utf-8'),re.S)[1])
            assert 'name="password"' not in get('admin/')
            html=get('admin/?setup='+token)
            post({**fields(html),'action':'setup','password':'local-test-only-2026','confirm':'local-test-only-2026'})
            assert 'name="confirm"' not in get('admin/?setup='+token), 'setup token replay'
            html=get('admin/'); html=post({**fields(html),'action':'login','password':'local-test-only-2026'})
            assert '?edit=new' in html
            for path in ['private/admin/config.php','private/admin/','scripts/setup-admin.php','admin/lib.php']:
                try: urlopen(base+path); raise AssertionError(path+' exposed')
                except HTTPError as e: assert e.code==403
            html=get('admin/?edit=new'); form={**fields(html),'name':'محصول آزمایشی','description':'توضیح آزمایشی','visible':'on','showOnHome':'on'}
            before=(root/'products-data.js').read_bytes()
            post({**form,'csrf':'wrong'}); assert (root/'products-data.js').read_bytes()==before
            post(form,[('bad.jpg',b'<?php echo "bad";')]); assert (root/'products-data.js').read_bytes()==before
            from PIL import Image
            import io
            image=io.BytesIO(); Image.new('RGB',(30,40),'green').save(image,format='PNG')
            post(form,[('photo.php.png',image.getvalue())]); assert len(catalog())==len(products)+1
            assert catalog()[-1]['name']['fa']=='محصول آزمایشی'; assert catalog()[-1]['images'][0].endswith('.png')
            assert len(list((root/'private/admin').glob('products-*.js')))==1
            idx=len(products); html=get(f'admin/?edit={idx}'); stale=fields(html)
            post({**stale,'name':'پنهان آزمایشی','description':'توضیح تازه','showOnHome':'on'})
            assert catalog()[-1]['visible'] is False
            public=get('products.html'); assert 'پنهان آزمایشی' not in public
            post({**stale,'name':'stale overwrite','description':'stale'}); assert catalog()[-1]['name']['fa']=='پنهان آزمایشی'
            html=get(f'admin/?edit={idx}'); fresh=fields(html)
            post({**fresh,'action':'delete'}); assert len(catalog())==len(products)+1
            post({**fresh,'action':'delete','confirm_delete':'on'}); assert len(catalog())==len(products)
            for page in ['index','about','products','contact','lame-yarn','fancy-yarn']:
                for suffix in ['','.en']: assert '<html' in get(page+suffix+'.html')
            html=get('admin/'); post({**fields(html),'action':'logout'}); assert '?edit=new' not in get('admin/')
            for _ in range(5): post({**fields(get('admin/')),'action':'login','password':'incorrect'})
            html=post({**fields(get('admin/')),'action':'login','password':'local-test-only-2026'}); assert '?edit=new' not in html
            (root/'private/admin/attempts.json').write_text('{}')
            print('PASS: setup, token replay, login/logout, CSRF, upload validation, create, hide, conflicts, delete confirmation, backups, throttling, protected paths and 12 public pages.',flush=True)
            if args.preview:
                print('Preview: http://127.0.0.1:8093/admin/ | disposable password: local-test-only-2026',flush=True)
                while True: time.sleep(1)
        finally: proc.terminate(); proc.wait(timeout=10)
if __name__=='__main__': main()
