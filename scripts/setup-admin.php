<?php
// Run once locally, then upload private/admin/config.php to the same path on hosting.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__ . '/../admin/lib.php';
if (config()) { fwrite(STDERR, "Admin already configured. Remove private/admin/config.php deliberately to reset.\n"); exit(1); }
if (!is_dir(STORE) && !mkdir(STORE, 0700, true)) throw new RuntimeException('Cannot create private storage');
$token = bin2hex(random_bytes(24));
save_config(['setup' => hash('sha256', $token)]);
echo "Upload private/admin/config.php to hosting (never commit it).\nOpen your site's /admin/?setup=" . $token . "\nChoose a password there. This link works only once.\n";
