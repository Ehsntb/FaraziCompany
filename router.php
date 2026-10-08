<?php
// Router for local testing: php -S 127.0.0.1:8082 router.php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$route = ltrim($path, '/');
if (preg_match('~^(?:private|scripts)(?:/|$)|(?:^|/)\.(?!well-known(?:/|$))|^admin/lib\.php$|^(?:seo-config\.json|README\.md|SEO-NOTES\.md|ADMIN-GUIDE\.md|AGENTS\.md|router\.php)$~i', $route)) {
    http_response_code(403); return true;
}
if ($route === '') $route = 'index.html';
if (preg_match('/^(?:(?:index|about|products|contact|lame-yarn|fancy-yarn)(?:\.en)?\.html|sitemap\.xml|robots\.txt)$/D', $route)) {
    require __DIR__ . '/site.php';
    return true;
}
return false;
