<?php
declare(strict_types=1);
const ROOT = __DIR__ . '/..';
const STORE = ROOT . '/private/admin';
function h($s): string { return htmlspecialchars((string)$s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function atomic_write(string $path, string $data): void {
    $tmp = tempnam(dirname($path), '.write-');
    if ($tmp === false) throw new RuntimeException('امکان ذخیره روی هاست وجود ندارد.');
    try {
        if (file_put_contents($tmp, $data) !== strlen($data)) throw new RuntimeException('ذخیره انجام نشد؛ دسترسی نوشتن فایل‌ها را بررسی کنید.');
        // tempnam creates mode 0600; preserve the public catalog's readable mode.
        $mode = $path === ROOT . '/products-data.js' ? 0644 : 0600;
        if (!chmod($tmp, $mode) || !rename($tmp, $path)) throw new RuntimeException('ذخیره انجام نشد؛ دسترسی نوشتن فایل‌ها را بررسی کنید.');
    } finally { if (is_file($tmp)) unlink($tmp); }
}
function config(): array { return is_file(STORE . '/config.php') ? require STORE . '/config.php' : []; }
function save_config(array $c): void { atomic_write(STORE . '/config.php', '<?php return ' . var_export($c, true) . ';'); }
function read_products(): array {
    $source = file_get_contents(ROOT . '/products-data.js');
    if (!preg_match('/window\.FARAZI_PRODUCTS\s*=\s*(\[.*\])\s*;/s', $source, $m)) throw new RuntimeException('فایل محصولات قابل خواندن نیست.');
    return json_decode($m[1], true, 512, JSON_THROW_ON_ERROR);
}
function revision(): string { return hash_file('sha256', ROOT . '/products-data.js'); }
function token_field(): void { echo '<input type="hidden" name="csrf" value="' . h($_SESSION['csrf']) . '">'; }
function upload_photos(): array {
    $result = [];
    try {
        $received=count(array_filter($_FILES['photos']['error'] ?? [], fn($e)=>$e!==UPLOAD_ERR_NO_FILE));
        if ($received>20 || (isset($_POST['photo_count']) && (int)$_POST['photo_count'] !== $received)) throw new RuntimeException('همه عکس‌ها دریافت نشدند. تعداد کمتری انتخاب کنید و دوباره ذخیره کنید.');
        foreach (($_FILES['photos']['error'] ?? []) as $i => $error) {
            if ($error === UPLOAD_ERR_NO_FILE) continue;
            if ($error !== UPLOAD_ERR_OK) throw new RuntimeException('آپلود عکس کامل نشد؛ حجم مجاز هاست را بررسی کنید.');
            $tmp = $_FILES['photos']['tmp_name'][$i];
            if (!is_uploaded_file($tmp) || filesize($tmp) > 8 * 1024 * 1024) throw new RuntimeException('هر عکس باید حداکثر ۸ مگابایت باشد.');
            $info = @getimagesize($tmp);
            if (!$info || !in_array($info[2], [IMAGETYPE_JPEG, IMAGETYPE_PNG, IMAGETYPE_WEBP], true) || $info[0] * $info[1] > 24000000) throw new RuntimeException('عکس باید JPG، PNG یا WebP و حداکثر ۲۴ میلیون پیکسل باشد.');
            $image = @imagecreatefromstring(file_get_contents($tmp));
            if (!$image) throw new RuntimeException('عکس قابل خواندن نیست.');
            $path = 'assets/products/admin-' . bin2hex(random_bytes(16)) . '.png';
            $result[] = $path;
            try { if (!imagepng($image, ROOT . '/' . $path)) throw new RuntimeException('ذخیره عکس روی هاست انجام نشد.'); }
            finally { imagedestroy($image); }
        }
        return $result;
    } catch (Throwable $e) { foreach ($result as $path) if (is_file(ROOT . '/' . $path)) unlink(ROOT . '/' . $path); throw $e; }
}
