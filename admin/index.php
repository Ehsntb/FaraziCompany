<?php
declare(strict_types=1);
require __DIR__ . '/lib.php';
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
session_name('farazi_admin');
session_set_cookie_params(['httponly'=>true,'secure'=>!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off','samesite'=>'Strict','path'=>rtrim(dirname($_SERVER['SCRIPT_NAME']), '/') . '/']);
ini_set('session.use_strict_mode', '1');
session_start();
$_SESSION['csrf'] ??= bin2hex(random_bytes(32));
$error = ''; $notice = $_SESSION['notice'] ?? ''; unset($_SESSION['notice']);
$c = config();
if (!empty($_SESSION['auth']) && (($_SESSION['last'] ?? 0) < time()-3600 || ($_SESSION['version'] ?? '') !== ($c['password'] ?? ''))) unset($_SESSION['auth']);
if (!empty($_SESSION['auth'])) $_SESSION['last'] = time();
$setup = (string)($_POST['setup'] ?? $_GET['setup'] ?? '');
$isSetup = isset($c['setup']) && hash_equals($c['setup'], hash('sha256', $setup));
$edit = (string)($_POST['id'] ?? $_GET['edit'] ?? '');
$products = []; $revision = ''; $lock = null;
try {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        if (!hash_equals($_SESSION['csrf'], (string)($_POST['csrf'] ?? ''))) throw new RuntimeException('صفحه منقضی شده است؛ صفحه را تازه کنید و دوباره تلاش کنید.');
        $action = (string)($_POST['action'] ?? '');
        if ($action === 'logout') { $_SESSION=[]; session_regenerate_id(true); header('Location: ./'); exit; }
        if (!is_dir(STORE)) throw new RuntimeException('پنل هنوز راه‌اندازی نشده است.');
        $lock = fopen(STORE . '/write.lock', 'c');
        if (!$lock || !flock($lock, LOCK_EX)) throw new RuntimeException('ذخیره‌سازی موقتاً در دسترس نیست.');
        $c = config();
        if ($action === 'setup' && isset($c['setup']) && hash_equals($c['setup'], hash('sha256', $setup))) {
            $password = (string)($_POST['password'] ?? '');
            if (strlen($password)<12 || strlen($password)>72) throw new RuntimeException('رمز باید بین ۱۲ تا ۷۲ بایت باشد؛ یک عبارت طولانی انتخاب کنید.');
            if ($password !== ($_POST['confirm'] ?? '')) throw new RuntimeException('تکرار رمز یکسان نیست.');
            save_config(['password'=>password_hash($password, PASSWORD_DEFAULT)]);
            $_SESSION['notice']='رمز ساخته شد. اکنون وارد شوید.'; header('Location: ./'); exit;
        } elseif ($action === 'login') {
            $ratePath = STORE . '/attempts.json';
            $rates = is_file($ratePath) ? json_decode(file_get_contents($ratePath), true, 512, JSON_THROW_ON_ERROR) : [];
            $rates = array_filter($rates, fn($v)=>$v['until']>time());
            $key = hash('sha256', $_SERVER['REMOTE_ADDR'] ?? 'unknown');
            $rate = $rates[$key] ?? ['count'=>0,'until'=>time()+900];
            if ($rate['count'] >= 5) throw new RuntimeException('تلاش‌های ورود زیاد بوده است. ۱۵ دقیقه بعد دوباره تلاش کنید.');
            $rate['count']++; $rates[$key]=$rate; atomic_write($ratePath,json_encode($rates));
            if (empty($c['password']) || !password_verify((string)($_POST['password'] ?? ''), $c['password'])) throw new RuntimeException('رمز ورود درست نیست.');
            unset($rates[$key]); atomic_write($ratePath,json_encode($rates));
            session_regenerate_id(true); $_SESSION['auth']=true; $_SESSION['last']=time(); $_SESSION['version']=$c['password']; $_SESSION['csrf']=bin2hex(random_bytes(32));
            header('Location: ./'); exit;
        } else {
            if (empty($_SESSION['auth']) || ($_SESSION['version'] ?? '') !== ($c['password'] ?? '')) throw new RuntimeException('ابتدا وارد پنل شوید.');
            $products = read_products();
            if (!hash_equals(revision(), (string)($_POST['revision'] ?? ''))) throw new RuntimeException('محصولات در صفحه دیگری تغییر کرده‌اند. صفحه را تازه کنید تا تغییرات قبلی از بین نروند.');
            if ($edit !== 'new' && (!ctype_digit($edit) || !isset($products[(int)$edit]))) throw new RuntimeException('محصول پیدا نشد.');
            if ($action === 'delete') {
                if (empty($_POST['confirm_delete']) || $edit === 'new') throw new RuntimeException('برای حذف، کادر تأیید را علامت بزنید.');
                array_splice($products, (int)$edit, 1);
            } elseif ($action === 'save') {
                $old = $edit === 'new' ? [] : $products[(int)$edit];
                $name = trim((string)($_POST['name'] ?? '')); $description=trim((string)($_POST['description'] ?? ''));
                if ($name === '' || $description === '' || strlen($name)>600 || strlen($description)>30000) throw new RuntimeException('نام و توضیحات محصول را کامل کنید؛ متن بیش از حد طولانی نباشد.');
                $images=[];
                foreach (($old['images'] ?? []) as $i=>$path) if (!in_array((string)$i, (array)($_POST['remove'] ?? []), true)) $images[]=$path;
                $cover = $old['images'][(int)($_POST['cover'] ?? -1)] ?? null;
                if ($cover && in_array($cover,$images,true)) { $images=array_values(array_diff($images,[$cover])); array_unshift($images,$cover); }
                $uploads=upload_photos(); $images=array_merge($images,$uploads);
                if (!$images) throw new RuntimeException('حداقل یک عکس برای محصول انتخاب کنید.');
                $product=array_merge($old,['name'=>['fa'=>$name,'en'=>trim((string)($_POST['name_en'] ?? '')) ?: $name], 'description'=>['fa'=>$description,'en'=>trim((string)($_POST['description_en'] ?? '')) ?: $description], 'images'=>$images,'showOnHome'=>isset($_POST['showOnHome']),'visible'=>isset($_POST['visible'])]);
                $product['featured'] ??= false;
                if ($edit === 'new') $products[]=$product; else $products[(int)$edit]=$product;
            } else throw new RuntimeException('درخواست معتبر نیست.');
            // Keep a protected copy before replacing the canonical public data file.
            $source=file_get_contents(ROOT . '/products-data.js');
            $backup=STORE . '/products-' . date('Ymd-His') . '-' . bin2hex(random_bytes(4)) . '.js';
            atomic_write($backup,$source);
            atomic_write(ROOT . '/products-data.js', "// Managed by the product panel. Keep the array valid JSON.\nwindow.FARAZI_PRODUCTS = " . json_encode(array_values($products), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_THROW_ON_ERROR) . ";\n");
            $_SESSION['notice']=$action === 'delete' ? 'محصول حذف شد.' : 'محصول ذخیره شد و تغییرات روی سایت اعمال شد.';
            header('Location: ./'); exit;
        }
    }
} catch (Throwable $e) { error_log('Admin: ' . $e->getMessage()); $error=$e instanceof RuntimeException ? $e->getMessage() : 'ذخیره انجام نشد. تنظیمات و دسترسی نوشتن هاست را بررسی کنید.'; }
finally { if (is_resource($lock)) { flock($lock,LOCK_UN); fclose($lock); } }
$authenticated = !empty($_SESSION['auth']);
if ($authenticated) {
    try {
        $readLock=fopen(STORE . '/write.lock','c');
        if (!$readLock || !flock($readLock,LOCK_SH)) throw new RuntimeException('Storage unavailable');
        try { $products=read_products(); $revision=(string)($_POST['revision'] ?? revision()); }
        finally { flock($readLock,LOCK_UN); fclose($readLock); }
    } catch(Throwable $e) { $error='فایل محصولات معتبر نیست. پیش از ویرایش، نسخه پشتیبان را بازیابی کنید.'; $edit=''; }
}
?><!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>مدیریت محصولات | فرازی کمپانی</title><link rel="stylesheet" href="admin.css"><script src="admin.js" defer></script></head><body>
<header><div class="brand"><img src="../logo/farazi-symbol-copper.svg" alt=""><strong>فرازی کمپانی</strong></div><nav><a href="../index.html" target="_blank" rel="noopener">مشاهده سایت</a><?php if($authenticated): ?><form method="post"><?php token_field(); ?><button class="secondary" name="action" value="logout">خروج</button></form><?php endif ?></nav></header>
<main><?php if($error): ?><div class="notice error" role="alert"><?=h($error)?></div><?php endif ?><?php if($notice): ?><div class="notice" role="status"><?=h($notice)?></div><?php endif ?>
<?php if(!$authenticated): ?>
<section class="panel login"><h1><?=$isSetup?'ساخت رمز ورود':'ورود به پنل'?></h1>
<?php if(!$c || (isset($c['setup']) && !$isSetup)): ?><p>پنل هنوز فعال نشده است. برای راه‌اندازی، راهنمای مدیریت محصولات را در اختیار مسئول سایت بگذارید.</p>
<?php else: ?><p><?=$isSetup?'یک رمز طولانی انتخاب کنید و آن را در جای امن نگه دارید.':'برای مدیریت محصولات، رمز خود را وارد کنید.'?></p><form method="post"><?php token_field(); ?><input type="hidden" name="setup" value="<?=h($setup)?>"><label>رمز ورود<input type="password" name="password" autocomplete="<?=$isSetup?'new-password':'current-password'?>" required <?=$isSetup?'minlength="12"':''?>></label><?php if($isSetup): ?><label>تکرار رمز<input type="password" name="confirm" autocomplete="new-password" required></label><?php endif ?><button name="action" value="<?=$isSetup?'setup':'login'?>"><?=$isSetup?'ثبت رمز':'ورود'?></button></form><?php endif ?></section>
<?php elseif($edit !== '' && ($edit === 'new' || (ctype_digit($edit) && isset($products[(int)$edit])))): $p=$edit === 'new' ? [] : $products[(int)$edit]; ?>
<a href="./">← بازگشت به محصولات</a><h1><?=$edit==='new'?'افزودن محصول':'ویرایش محصول'?></h1><p>نام، توضیحات و عکس‌ها را وارد کنید؛ سپس «ذخیره محصول» را بزنید.</p>
<form method="post" enctype="multipart/form-data" class="panel" id="editor"><?php token_field(); ?><input type="hidden" name="id" value="<?=h($edit)?>"><input type="hidden" name="revision" value="<?=h($revision)?>"><input type="hidden" name="action" value="save">
<label>نام محصول<input name="name" required maxlength="200" value="<?=h($_POST['name'] ?? $p['name']['fa'] ?? '')?>"></label><label>توضیحات<textarea name="description" required maxlength="10000"><?=h($_POST['description'] ?? $p['description']['fa'] ?? '')?></textarea></label>
<h2>عکس‌های محصول</h2><p>عکس اصلی در فهرست محصولات نمایش داده می‌شود. برای کنار گذاشتن عکس، «حذف این عکس» را علامت بزنید.</p><div class="photos">
<?php foreach(($p['images'] ?? []) as $i=>$path): ?><div class="photo"><img src="../<?=h($path)?>" alt="عکس <?= $i+1 ?>"><label><input type="radio" name="cover" value="<?=$i?>" <?=$i===0?'checked':''?>> عکس اصلی</label><label><input type="checkbox" name="remove[]" value="<?=$i?>"> حذف این عکس</label></div><?php endforeach ?></div>
<label class="upload">افزودن عکس از گوشی یا کامپیوتر<input type="file" name="photos[]" accept="image/jpeg,image/png,image/webp" multiple id="photos"><small>JPG، PNG یا WebP؛ هر عکس حداکثر ۸ مگابایت. می‌توانید چند عکس انتخاب کنید.</small><span id="preview" class="preview"></span></label>
<label><input type="checkbox" name="visible" <?=($p['visible'] ?? true)?'checked':''?>> نمایش محصول در سایت</label><label><input type="checkbox" name="showOnHome" <?=($p['showOnHome'] ?? true)?'checked':''?>> نمایش در صفحه اصلی هم باشد</label>
<details><summary>متن انگلیسی (اختیاری)</summary><p>اگر خالی بماند، متن فارسی در نسخه انگلیسی هم نمایش داده می‌شود.</p><label>نام انگلیسی<input dir="ltr" name="name_en" maxlength="200" value="<?=h($_POST['name_en'] ?? $p['name']['en'] ?? '')?>"></label><label>توضیحات انگلیسی<textarea dir="ltr" name="description_en" maxlength="10000"><?=h($_POST['description_en'] ?? $p['description']['en'] ?? '')?></textarea></label></details>
<div class="actions"><button type="submit">ذخیره محصول</button><a class="button secondary" href="./">انصراف</a></div><small>پس از ذخیره، تغییرات مستقیماً روی سایت اعمال می‌شود.</small></form>
<?php if($edit!=='new'): ?><details class="panel"><summary>حذف کامل محصول</summary><p>برای توقف موقت نمایش، گزینه «نمایش محصول در سایت» را خاموش کنید.</p><form method="post"><?php token_field(); ?><input type="hidden" name="id" value="<?=h($edit)?>"><input type="hidden" name="revision" value="<?=h($revision)?>"><label><input type="checkbox" name="confirm_delete" required> مطمئنم که این محصول حذف شود.</label><button class="danger" name="action" value="delete">حذف محصول</button></form></details><?php endif ?>
<?php else: ?><section class="intro"><h1>محصولات</h1><p>برای تغییر هر محصول، دکمه ویرایش را بزنید.</p><a class="button" href="?edit=new">+ افزودن محصول</a></section>
<?php if(!$products): ?><p class="empty">هنوز محصولی ثبت نشده است. اولین محصول را اضافه کنید.</p><?php endif ?>
<?php foreach($products as $i=>$p): ?><article class="row"><img src="../<?=h($p['images'][0])?>" alt=""><div class="copy"><h2><?=h($p['name']['fa'])?></h2><p><?=($p['visible'] ?? true)?'در سایت نمایش داده می‌شود':'نمایش در سایت خاموش است'?> · <?=count($p['images'])?> عکس</p></div><a class="button secondary" href="?edit=<?=$i?>">ویرایش<span class="sr-only"> <?=h($p['name']['fa'])?></span></a></article><?php endforeach ?>
<?php endif ?></main></body></html>
