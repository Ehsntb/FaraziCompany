"use strict";
const picker = document.querySelector('#photos');
let urls = [];
picker?.addEventListener('change', () => {
  let count=document.querySelector('[name=photo_count]');
  if (!count) { count=document.createElement('input'); count.type='hidden'; count.name='photo_count'; picker.form.append(count); }
  count.value=String(picker.files.length);
  picker.setCustomValidity(picker.files.length>20 ? 'هر بار حداکثر ۲۰ عکس انتخاب کنید.' : '');
  urls.forEach(URL.revokeObjectURL); urls=[];
  const preview=document.querySelector('#preview'); preview.replaceChildren();
  for (const file of picker.files) {
    if (!file.type.startsWith('image/')) continue;
    const image=document.createElement('img');
    image.alt=file.name; image.src=URL.createObjectURL(file); urls.push(image.src); preview.append(image);
  }
});
document.querySelector('#editor')?.addEventListener('submit', event => {
  if (!event.target.checkValidity()) return;
  const button=event.target.querySelector('button[type=submit]');
  button.disabled=true; button.textContent='در حال ذخیره…';
});
