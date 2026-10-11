<?php
if (!isset($authenticated) || !$authenticated) { http_response_code(404); exit; }
$gallery = [];
try { $gallery = gallery_files(); }
catch (Throwable $e) { echo '<div class="notice error" role="alert">خواندن گالری ممکن نیست؛ پوشه و دسترسی هاست را بررسی کنید.</div>'; }
?>
<section class="intro"><h1>گالری تصاویر</h1><p>عکس اضافه کنید یا عکس‌های قدیمی را از گالری بردارید.</p></section>
<form method="post" enctype="multipart/form-data" class="panel" id="editor">
<?php token_field(); ?><input type="hidden" name="action" value="gallery_upload">
<h2>افزودن عکس به گالری</h2>
<label class="upload">انتخاب عکس از گوشی یا کامپیوتر<input type="file" name="photos[]" accept="image/jpeg,image/png,image/webp" multiple required id="photos"><small>هر بار حداکثر ۲۰ عکس؛ هر عکس تا ۸ مگابایت، با فرمت JPG، PNG یا WebP.</small><span id="preview" class="preview"></span></label>
<button type="submit">افزودن عکس‌ها</button><small>پس از افزودن، عکس‌ها در گالری سایت نمایش داده می‌شوند.</small>
</form>
<h2>عکس‌های گالری (<?=count($gallery)?>)</h2>
<?php if(!$gallery): ?><p class="empty">هنوز عکسی در گالری نیست. از بخش بالا اولین عکس را اضافه کنید.</p>
<?php else: ?>
<form method="post">
<?php token_field(); ?><input type="hidden" name="action" value="gallery_delete">
<p>برای حذف، عکس‌های موردنظر را انتخاب کنید و تأیید پایین صفحه را بزنید.</p>
<div class="gallery-grid">
<?php foreach($gallery as $i=>$name): ?><label class="gallery-photo"><img src="../assets/gallery/<?=h(rawurlencode($name))?>" loading="lazy" alt="عکس گالری <?= $i+1 ?>"><span><input type="checkbox" name="selected[]" value="<?=h($name)?>"> انتخاب عکس <?= $i+1 ?></span></label><?php endforeach ?>
</div>
<div class="panel"><label><input type="checkbox" name="confirm_delete" required> مطمئنم که عکس‌های انتخاب‌شده از گالری برداشته شوند.</label><button class="danger" type="submit">حذف عکس‌های انتخاب‌شده</button><small>نسخه پشتیبان عکس‌ها برای بازیابی توسط مسئول سایت نگهداری می‌شود.</small></div>
</form>
<?php endif ?>
