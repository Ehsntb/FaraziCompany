<?php
// Read only the public gallery directory; never accept a path from the request.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, max-age=0');
header('X-Content-Type-Options: nosniff');
$directory = __DIR__ . '/assets/gallery';
$files = @scandir($directory);
if ($files === false) {
    http_response_code(503);
    echo json_encode(['error' => 'Gallery unavailable']);
    exit;
}
$images = [];
$extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'avif'];
foreach ($files as $file) {
    $path = $directory . '/' . $file;
    if (!is_link($path) && is_file($path) && in_array(strtolower(pathinfo($file, PATHINFO_EXTENSION)), $extensions, true)) {
        $images[] = $file;
    }
}
natcasesort($images);
$urls = array_map(function ($name) {
    return 'assets/gallery/' . rawurlencode($name);
}, array_values($images));
echo json_encode($urls, JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
