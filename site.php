<?php
// Dynamic public pages: fixed templates and data files, no shell commands or writes.
function esc($value) { return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function page_file($page, $lang) { return $page . ($lang === 'en' ? '.en' : '') . '.html'; }
function set_markup($node, $markup) {
    while ($node->firstChild) $node->removeChild($node->firstChild);
    if ($markup === '') return;
    $fragmentDoc = new DOMDocument();
    $fragmentDoc->loadHTML('<?xml encoding="UTF-8"><html><body><div id="fragment-root">' . $markup . '</div></body></html>');
    $wrapper = $fragmentDoc->getElementById('fragment-root');
    foreach (iterator_to_array($wrapper->childNodes) as $child) $node->appendChild($node->ownerDocument->importNode($child, true));
}
function render_site($route) {
    $root = __DIR__;
    $config = json_decode(file_get_contents($root . '/seo-config.json'), true, 512, JSON_THROW_ON_ERROR);
    $base = rtrim($config['siteUrl'], '/');
    $parsed = parse_url($base);
    if (($parsed['scheme'] ?? '') !== 'https' || empty($parsed['host']) || isset($parsed['query']) || isset($parsed['fragment']) || isset($parsed['user']) || isset($parsed['pass'])) throw new RuntimeException('Invalid siteUrl');
    $pages = ['index', 'about', 'products', 'contact', 'lame-yarn', 'fancy-yarn'];
    if ($route === 'robots.txt') {
        header('Content-Type: text/plain; charset=utf-8');
        return "User-agent: *\nAllow: /\n\nSitemap: $base/sitemap.xml\n";
    }
    if ($route === 'sitemap.xml') {
        header('Content-Type: application/xml; charset=utf-8');
        $xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
        foreach ($pages as $page) foreach (['fa','en'] as $lang) $xml .= '<url><loc>' . esc($base . '/' . page_file($page, $lang)) . '</loc></url>';
        return $xml . '</urlset>';
    }
    if (!preg_match('/^(index|about|products|contact|lame-yarn|fancy-yarn)(\.en)?\.html$/D', $route, $match)) {
        http_response_code(404); return 'Not found';
    }
    $page = $match[1]; $lang = empty($match[2]) ? 'fa' : 'en';
    $source = file_get_contents($root . '/products-data.js');
    if (!preg_match('/window\.FARAZI_PRODUCTS\s*=\s*(\[.*\])\s*;/s', $source, $data)) throw new RuntimeException('Invalid products data');
    $products = json_decode($data[1], true, 512, JSON_THROW_ON_ERROR);
    foreach ($products as $product) {
        foreach (['fa','en'] as $locale) if (empty($product['name'][$locale]) || empty($product['description'][$locale])) throw new RuntimeException('Missing product translation');
        if (empty($product['images'])) throw new RuntimeException('Missing product image');
    }
    libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    $dom->loadHTML('<?xml encoding="UTF-8">' . file_get_contents($root . '/' . $page . '.html'));
    foreach (iterator_to_array($dom->childNodes) as $node) if ($node->nodeType === XML_PI_NODE) $dom->removeChild($node);
    $xpath = new DOMXPath($dom);
    foreach (iterator_to_array($xpath->query('//*[@data-en]')) as $node) {
        if ($lang === 'en') {
            $fa = ''; foreach ($node->childNodes as $child) $fa .= $dom->saveHTML($child);
            $node->setAttribute('data-fa', $fa);
            set_markup($node, $node->getAttribute('data-en'));
        } else $node->removeAttribute('data-fa');
    }
    if ($lang === 'en') {
        $labels = json_decode('{"فرازی کمپانی، صفحه اصلی": "Farazi Company, home", "منوی اصلی": "Main navigation", "زبان سایت": "Site language", "باز کردن منو": "Open menu", "بستن پنجره": "Close dialog", "مسیر صفحه": "Breadcrumb", "راه‌های ارتباطی": "Contact methods", "مزیت‌های فرازی کمپانی": "Why Farazi Company", "تصویرسازی الهام‌گرفته از معماری بازار تهران": "Illustration inspired by Tehran Bazaar architecture", "تصویرسازی معماری بازار تهران": "Illustration of Tehran Bazaar architecture", "نخ‌های پنبه‌ای، مشکی و مسی در کنار یکدیگر": "Ivory, black and copper yarn spools", "نقشه ارتباطات تجاری در سراسر جهان": "Illustration of global trade connections", "تجربه و همکاری": "Experience and cooperation"}', true);
        $labels['نمونه نخ لمه و متالیک از تصاویر محصولات فرازی کمپانی'] = 'Metallic yarn sample from Farazi Company product photographs';
        $labels['راهنمای نخ'] = 'Yarn guides';
        foreach ($xpath->query('//*[@aria-label or @alt]') as $node) foreach (['aria-label','alt'] as $attr) {
            $value = $node->getAttribute($attr);
            if (isset($labels[$value])) $node->setAttribute($attr,$labels[$value]);
        }
    }
    $html = $dom->documentElement; $html->setAttribute('lang', $lang); $html->setAttribute('dir', $lang === 'fa' ? 'rtl' : 'ltr');
    foreach ($xpath->query('//*[@data-copyright-year]') as $node) $node->textContent = date('Y');
    foreach ($xpath->query('//a[@href]') as $node) {
        $href = $node->getAttribute('href');
        if ($node->hasAttribute('data-language')) {
            $target = $node->getAttribute('data-language');
            $node->setAttribute('href', page_file($page, $target));
            $node->setAttribute('aria-current', $target === $lang ? 'page' : 'false');
        } elseif (preg_match('/^(index|about|products|contact|lame-yarn|fancy-yarn)(?:\.en)?\.html([?#].*)?$/D', $href, $link)) {
            $node->setAttribute('href', page_file($link[1], $lang) . ($link[2] ?? ''));
        }
    }
    foreach (['catalog-list','product-grid'] as $id) {
        $node = $dom->getElementById($id); if (!$node) continue;
        $catalog = $id === 'catalog-list'; $cards = ''; $count = 0;
        foreach ($products as $i => $product) {
            if (!$catalog && empty($product['showOnHome'])) continue;
            $count++; $name = esc($product['name'][$lang]); $desc = esc($product['description'][$lang]);
            $img = '<img src="' . esc($product['images'][0]) . '" alt="' . $name . '" loading="lazy" decoding="async">';
            if ($catalog) {
                $featured = !empty($product['featured']); $photos = count($product['images']);
                $badge = $photos > 1 ? '<span class="photo-count">' . $photos . ' ' . ($lang === 'fa' ? 'تصویر' : 'photos') . '</span>' : '';
                $specialty = $featured ? '<p class="product-specialty">' . ($lang === 'fa' ? '۱۵ سال تخصص در واردات و تجارت نخ لمه' : '15 years of specialized Lurex trading') . '</p>' : '';
                $action = $photos > 1 ? ($lang === 'fa' ? 'مشاهده گالری' : 'View gallery') : ($lang === 'fa' ? 'مشاهده جزئیات' : 'View details');
                $cards .= '<article class="catalog-product' . ($featured ? ' catalog-product-featured' : '') . '"><button class="catalog-product-trigger" type="button" data-product="' . $i . '"><div class="catalog-photo">' . $img . $badge . '</div><div class="catalog-copy">' . $specialty . '<h2>' . $name . '</h2><div class="catalog-rule"></div><p>' . $desc . '</p><span class="catalog-action">' . $action . ' ←</span></div></button></article>';
            } else $cards .= '<button class="product-card" type="button" data-product="' . $i . '"><div class="asset-frame product-art">' . $img . '</div><div class="product-info"><h3>' . $name . '</h3><span class="view-label">' . ($lang === 'fa' ? 'مشاهده' : 'View') . '</span></div></button>';
        }
        set_markup($node, $cards);
        if (!$catalog) {
            $node->setAttribute('style', '--home-columns: ' . min($count,7));
            $section = $node; while ($section && !str_contains($section->getAttribute('class'), 'products-section')) $section = $section->parentNode instanceof DOMElement ? $section->parentNode : null;
            if ($section) { if ($count) $section->removeAttribute('hidden'); else $section->setAttribute('hidden', ''); }
        }
    }
    $empty = $dom->getElementById('catalog-empty');
    if ($empty) { if ($products) $empty->setAttribute('hidden',''); else $empty->removeAttribute('hidden'); }
    foreach (iterator_to_array($xpath->query('//head/title | //head/meta[@name="description" or @name="robots"] | //head/*[@data-seo]')) as $node) $node->parentNode->removeChild($node);
    foreach ($xpath->query('//script[@src] | //link[@rel="stylesheet"]') as $node) {
        $attr = $node->tagName === 'script' ? 'src' : 'href';
        $asset = explode('?', $node->getAttribute($attr))[0];
        if (preg_match('/^[a-zA-Z0-9_-]+\.(js|css)$/D', $asset) && is_file($root.'/'.$asset)) {
            $node->setAttribute($attr, $asset.'?v='.substr(hash_file('sha256',$root.'/'.$asset),0,12));
        }
    }
    $head = $dom->getElementsByTagName('head')->item(0); $info = $config['pages'][$page][$lang];
    $title = $dom->createElement('title'); $title->textContent = $info['title']; $head->appendChild($title);
    $meta = function($key, $value, $property = false) use ($dom,$head) { $n=$dom->createElement('meta'); $n->setAttribute('data-seo','true'); $n->setAttribute($property ? 'property' : 'name',$key); $n->setAttribute('content',$value); $head->appendChild($n); };
    $meta('description',$info['description']); $meta('robots','index, follow, max-image-preview:large');
    $url = $base . '/' . page_file($page,$lang);
    foreach (['og:type'=>'website','og:site_name'=>$config['siteName'],'og:title'=>$info['title'],'og:description'=>$info['description'],'og:url'=>$url,'og:image'=>$base.'/'.$config['socialImage'],'og:image:alt'=>'Farazi Company textile yarns','og:locale'=>$lang === 'fa' ? 'fa_IR' : 'en_US','og:locale:alternate'=>$lang === 'fa' ? 'en_US' : 'fa_IR'] as $key=>$value) $meta($key,$value,true);
    foreach (['twitter:card'=>'summary_large_image','twitter:title'=>$info['title'],'twitter:description'=>$info['description'],'twitter:image'=>$base.'/'.$config['socialImage']] as $key=>$value) $meta($key,$value);
    foreach (['canonical'=>$lang,'fa'=>'fa','en'=>'en','x-default'=>'fa'] as $rel=>$target) {
        $n=$dom->createElement('link'); $n->setAttribute('data-seo','true'); $n->setAttribute('rel',$rel === 'canonical' ? 'canonical' : 'alternate');
        if ($rel !== 'canonical') $n->setAttribute('hreflang',$rel);
        $n->setAttribute('href',$base.'/'.page_file($page,$target)); $head->appendChild($n);
    }
    $schema=['@context'=>'https://schema.org','@type'=>['about'=>'AboutPage','contact'=>'ContactPage','products'=>'CollectionPage'][$page] ?? 'WebPage','name'=>$info['title'],'description'=>$info['description'],'inLanguage'=>$lang,'url'=>$url,'publisher'=>['@type'=>'Organization','name'=>$config['siteName'],'alternateName'=>'فرازی کمپانی','@id'=>$base.'/index.html#organization','url'=>$base.'/index.html','logo'=>$base.'/logo/farazi-symbol-copper.svg']];
    if ($page !== 'index') $schema['breadcrumb']=['@type'=>'BreadcrumbList','itemListElement'=>[['@type'=>'ListItem','position'=>1,'name'=>$lang === 'fa' ? 'خانه' : 'Home','item'=>$base.'/'.page_file('index',$lang)],['@type'=>'ListItem','position'=>2,'name'=>$info['title'],'item'=>$url]]];
    if (in_array($page, ['lame-yarn','fancy-yarn'], true)) {
        $schema['breadcrumb']['itemListElement'] = [
            ['@type'=>'ListItem','position'=>1,'name'=>$lang === 'fa' ? 'خانه' : 'Home','item'=>$base.'/'.page_file('index',$lang)],
            ['@type'=>'ListItem','position'=>2,'name'=>$lang === 'fa' ? 'انواع نخ' : 'Yarns','item'=>$base.'/'.page_file('products',$lang)],
            ['@type'=>'ListItem','position'=>3,'name'=>$info['title'],'item'=>$url]
        ];
    }
    if ($page === 'products') {
        $items=[]; foreach ($products as $i=>$product) $items[]=['@type'=>'ListItem','position'=>$i+1,'item'=>['@type'=>'Thing','name'=>$product['name'][$lang],'description'=>$product['description'][$lang],'image'=>$base.'/'.$product['images'][0]]];
        $schema['mainEntity']=['@type'=>'ItemList','numberOfItems'=>count($products),'itemListElement'=>$items];
    }
    $n=$dom->createElement('script'); $n->setAttribute('data-seo','true'); $n->setAttribute('type','application/ld+json'); $n->appendChild($dom->createTextNode(json_encode($schema,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_HEX_TAG))); $head->appendChild($n);
    libxml_clear_errors(); header('Content-Type: text/html; charset=utf-8');
    return $dom->saveHTML();
}
header('Cache-Control: no-cache');
try { echo render_site($route ?? ($_GET['page'] ?? 'index.html')); }
catch (Throwable $error) { error_log('Site rendering failed: '.$error->getMessage()); http_response_code(503); echo 'Site temporarily unavailable'; }
