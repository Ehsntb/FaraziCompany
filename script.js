"use strict";

document.querySelectorAll("[data-copyright-year]").forEach(element => {
  element.textContent = String(new Date().getFullYear());
});
const pageId = document.body.dataset.page || "home";
const products = (window.FARAZI_PRODUCTS || []).map((product, index) => {
  const images = Array.isArray(product.images)
    ? product.images.filter(Boolean)
    : [product.image].filter(Boolean);
  return {
    ...product,
    images,
    image: images[0] || "",
    id: String(index),
  };
});
let language = "fa";
const dialog = document.querySelector("#detail-dialog");
const dialogContent = document.querySelector("#dialog-content");
let currentDialog = null;
let activeGalleryIndex = 0;
let companyImageIndex = null;
const translatable = [...document.querySelectorAll("[data-en]")];
translatable.forEach((element) => {
  element.dataset.fa ||= element.innerHTML;
});
function t(fa, en) {
  return language === "fa" ? fa : en;
}
function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char],
  );
}
function renderCatalog() {
  const list = document.querySelector("#catalog-list");
  if (!list) return;
  list.innerHTML = products.map(catalogItem).join("");
  document.querySelector("#catalog-empty").hidden = products.length !== 0;
}
function catalogItem(product) {
  const featured = product.featured === true;
  const photoCount = product.images.length;
  return (
    '<article class="catalog-product' +
    (featured ? " catalog-product-featured" : "") +
    '"><button class="catalog-product-trigger" type="button" data-product="' +
    product.id +
    '" aria-label="' +
    t("مشاهده تصاویر و مشخصات ", "View photos and specifications: ") +
    escapeHtml(product.name[language]) +
    '"><div class="catalog-photo"><img src="' +
    escapeHtml(product.image) +
    '" alt="' +
    escapeHtml(product.name[language]) +
    '" loading="' +
    (featured ? "eager" : "lazy") +
    '" decoding="async">' +
    (photoCount > 1
      ? '<span class="photo-count">' +
        photoCount +
        " " +
        t("تصویر", "photos") +
        "</span>"
      : "") +
    '</div><div class="catalog-copy">' +
    (featured
      ? '<p class="product-specialty">' +
        t("۱۵ سال تخصص در واردات و تجارت نخ لمه", "15 years of specialized Lurex trading") +
        "</p>"
      : "") +
    "<h2>" +
    escapeHtml(product.name[language]) +
    '</h2><div class="catalog-rule"></div><p>' +
    escapeHtml(product.description[language]) +
    '</p><span class="catalog-action">' +
    (photoCount > 1 ? t("مشاهده گالری", "View gallery") : t("مشاهده جزئیات", "View details")) +
    " <span aria-hidden=\"true\">←</span></span></div></button></article>"
  );
}
function art(product) {
  return (
    '<div class="asset-frame product-art"><img src="' +
    escapeHtml(product.image) +
    '" alt="' +
    escapeHtml(product.name[language]) +
    '" width="1254" height="1254" loading="lazy" decoding="async"></div>'
  );
}
function card(product) {
  return (
    '<button class="product-card" type="button" data-product="' +
    product.id +
    '" aria-label="' +
    t("مشاهده جزئیات ", "View details: ") +
    escapeHtml(product.name[language]) +
    '">' +
    art(product) +
    '<div class="product-info"><h3>' +
    escapeHtml(product.name[language]) +
    '</h3><span class="view-label">' +
    t("مشاهده", "View") +
    "</span></div></button>"
  );
}
function renderProducts() {
  const grid = document.querySelector("#product-grid");
  if (!grid) return;
  const featured = products.filter((product) => product.showOnHome === true);
  grid.style.setProperty("--home-columns", Math.min(featured.length, 7));
  grid.innerHTML = featured.map(card).join("");
  grid.closest(".products-section").hidden = featured.length === 0;
}
function contactButton() {
  return (
    '<a class="button" href="contact' +
    (language === 'en' ? '.en.html' : '.html') +
    '" data-close-dialog>' +
    t("تماس با ما", "Contact us") +
    "</a>"
  );
}
function renderImageGallery(images, selected, title, prefix) {
  const controls = images.length > 1;
  const arrow = (step, label, icon) => '<button type="button" class="gallery-arrow gallery-' +
    (step < 0 ? 'prev' : 'next') + '" data-' + prefix + '-step="' + step + '" aria-label="' + label + '">' + icon + '</button>';
  return '<div class="dialog-gallery"><div class="dialog-gallery-stage"><img src="' +
    escapeHtml(images[selected]) + '" alt="' + escapeHtml(title) + ' — ' + (selected + 1) + '">' +
    (controls ? arrow(-1, t("تصویر قبلی", "Previous image"), t('›', '‹')) +
      arrow(1, t("تصویر بعدی", "Next image"), t('‹', '›')) +
      '<span class="gallery-counter" aria-live="polite">' + (selected + 1) + ' / ' + images.length + '</span>' : '') +
    '</div>' + (controls ? '<div class="dialog-thumbnails" role="list" aria-label="' + t("انتخاب تصویر", "Choose an image") + '">' +
      images.map((src, index) => '<button type="button" role="listitem" data-' + prefix + '-index="' + index +
        '" class="' + (index === selected ? 'is-active' : '') + '" aria-label="' + t("تصویر ", "Image ") + (index + 1) +
        '"><img src="' + escapeHtml(src) + '" alt="" loading="lazy" decoding="async"></button>').join('') + '</div>' : '') + '</div>';
}
function renderDialog(kind) {
  const thumbnailScroll = dialogContent.querySelector(".dialog-thumbnails")?.scrollLeft || 0;
  const product = products.find((item) => item.id === kind);
  if (product) {
    dialogContent.innerHTML =
      '<div class="dialog-product">' + renderImageGallery(product.images, activeGalleryIndex, product.name[language], "gallery") +
      '<div class="dialog-product-copy"><h2 id="dialog-title">' +
      escapeHtml(product.name[language]) +
      "</h2><p class=\"dialog-description\">" +
      escapeHtml(product.description[language]) +
      '</p><p class="dialog-note">' +
      t(
        "برای اطلاع از مشخصات، موجودی و قیمت روز با ما در تماس باشید.",
        "Contact us for specifications, availability and current pricing.",
      ) +
      "</p>" +
      contactButton() +
      "</div></div>";
  } else if (kind === "gallery") {
    const images = window.FARAZI_GALLERY || [];
    if (companyImageIndex !== null && images[companyImageIndex]) {
      dialogContent.innerHTML = '<div class="company-viewer"><h2 id="dialog-title" hidden>' +
        t("گالری فرازی کمپانی", "Farazi Company gallery") +
        '</h2>' + renderImageGallery(images, companyImageIndex, t("گالری فرازی کمپانی", "Farazi Company gallery"), "company") + '</div>';
    } else {
      dialogContent.innerHTML = '<h2 id="dialog-title">' + t("گالری فرازی کمپانی", "Farazi Company gallery") +
        '</h2><div class="company-gallery">' + images.map((src, index) =>
          '<button type="button" data-company-image="' + index + '" aria-label="' +
          t("نمایش تصویر ", "Open image ") + (index + 1) + '"><img src="' + escapeHtml(src) +
          '" alt="' + t("گالری فرازی کمپانی، تصویر ", "Farazi Company gallery, image ") +
          (index + 1) + '" loading="lazy" decoding="async"></button>'
        ).join("") + '</div>' + (images.length ? '' : '<p>' + t("هنوز تصویری اضافه نشده است.", "No images yet.") + '</p>');
    }
  } else if (kind === "catalog") {
    dialogContent.innerHTML =
      '<h2 id="dialog-title">' +
      (kind === "catalog"
        ? t("محصولات فرازی کمپانی", "Farazi Company products")
        : t("گالری محصولات", "Product gallery")) +
      '</h2><p class="dialog-intro">' +
      t(
        "برای مشاهده توضیحات، محصول مورد نظر را انتخاب کنید.",
        "Select a product to see its details.",
      ) +
      '</p><div class="dialog-grid">' +
      products.map(card).join("") +
      "</div>";
  } else if (kind === "about") {
    dialogContent.innerHTML =
      '<h2 id="dialog-title">' +
      t("درباره فرازی کمپانی", "About Farazi Company") +
      "</h2><p>" +
      t(
        "فرازی کمپانی با بیش از ۴۰ سال تجربه در بازار نساجی و ۱۵ سال تخصص در نخ لمه و متالیک، در زمینه تأمین، سورسینگ، واردات و صادرات انواع نخ فعالیت می‌کند.",
        "With over 40 years in the textile market and 15 years of Lurex and metallic-yarn expertise, Farazi Company sources, supplies, imports and exports textile yarns.",
      ) +
      '</p><p class="dialog-note">' +
      t(
        "برای آشنایی بیشتر با محصولات و دریافت اطلاعات تأمین، با مجموعه در ارتباط باشید.",
        "Get in touch to learn more about our products and sourcing services.",
      ) +
      "</p>" +
      contactButton();
  } else if (kind === "trade") {
    dialogContent.innerHTML =
      '<h2 id="dialog-title">' +
      t("واردات و صادرات", "Import & export") +
      "</h2><p>" +
      t(
        "تأمین مستقیم مواد اولیه نساجی از تولیدکنندگان بین‌المللی و صادرات انواع نخ به بازارهای مختلف، از خدمات فرازی کمپانی است. برای بررسی نوع نخ، مقدار مورد نیاز و شرایط تأمین، با ما تماس بگیرید.",
        "Farazi Company sources textile raw materials from international manufacturers and exports yarn to different markets. Contact us to discuss yarn types, quantities and sourcing requirements.",
      ) +
      "</p>" +
      contactButton();
  } else {
    dialogContent.innerHTML =
      '<h2 id="dialog-title">' +
      t("اطلاعات بیشتر", "More information") +
      "</h2><p>" +
      t(
        "برای دریافت اطلاعات تکمیلی، موجودی و قیمت روز با فرازی کمپانی در ارتباط باشید.",
        "Contact Farazi Company for further information, availability and current pricing.",
      ) +
      "</p>" +
      contactButton();
  }
  const strip = dialogContent.querySelector(".dialog-thumbnails");
  if (strip) {
    strip.scrollLeft = thumbnailScroll;
    requestAnimationFrame(() => {
      if (!strip.isConnected) return;
      const active = strip.querySelector(".is-active");
      if (!active) return;
      const viewport = strip.getBoundingClientRect();
      const selected = active.getBoundingClientRect();
      strip.scrollBy({
        left: selected.left + selected.width / 2 - viewport.left - viewport.width / 2,
        behavior: "instant",
      });
    });
  }
}
let galleryRequest = 0;
async function refreshGallery() {
  if (location.protocol === "file:") return;
  const request = ++galleryRequest;
  try {
    const response = await fetch("gallery.php", { cache: "no-store" });
    if (!response.ok) throw new Error("Gallery unavailable");
    const images = await response.json();
    if (!Array.isArray(images) || !images.every(src => typeof src === "string" && /^assets\/gallery\/[^/]+$/.test(src))) {
      throw new Error("Invalid gallery response");
    }
    if (request !== galleryRequest) return;
    const selected = (window.FARAZI_GALLERY || [])[companyImageIndex];
    window.FARAZI_GALLERY = images;
    if (companyImageIndex !== null) {
      const index = images.indexOf(selected);
      companyImageIndex = index >= 0 ? index : null;
    }
    if (currentDialog === "gallery" && dialog.open) renderDialog("gallery");
  } catch {
    // Keep the bundled list usable for local previews or temporary server errors.
  }
}
function openDialog(kind) {
  currentDialog = kind;
  if (kind === "gallery") companyImageIndex = null;
  if (products.some((item) => item.id === kind)) activeGalleryIndex = 0;
  renderDialog(kind);
  if (!dialog.open) dialog.showModal();
  dialog.querySelector(".dialog-close").focus();
  if (kind === "gallery") refreshGallery();
}
function moveCompanyImage(step) {
  const count = (window.FARAZI_GALLERY || []).length;
  if (!count || companyImageIndex === null) return;
  companyImageIndex = (companyImageIndex + step + count) % count;
  renderDialog("gallery");
}
function moveGallery(step) {
  const product = products.find((item) => item.id === currentDialog);
  if (!product || product.images.length < 2) return;
  activeGalleryIndex =
    (activeGalleryIndex + step + product.images.length) % product.images.length;
  renderDialog(currentDialog);
}
document.addEventListener("click", (event) => {
  const companyIndex = event.target.closest("[data-company-index]");
  if (companyIndex) {
    companyImageIndex = Number(companyIndex.dataset.companyIndex);
    renderDialog("gallery");
    dialogContent.querySelector('[data-company-index="' + companyImageIndex + '"]').focus();
    return;
  }
  const companyImage = event.target.closest("[data-company-image]");
  const companyStep = event.target.closest("[data-company-step]");
  if (companyImage) {
    companyImageIndex = Number(companyImage.dataset.companyImage);
    renderDialog("gallery");
    dialog.querySelector(".dialog-close").focus();
    return;
  }
  if (companyStep) {
    const step = companyStep.dataset.companyStep;
    moveCompanyImage(Number(step));
    dialogContent.querySelector('[data-company-step="' + step + '"]').focus();
    return;
  }
  const galleryIndex = event.target.closest("[data-gallery-index]");
  const galleryStep = event.target.closest("[data-gallery-step]");
  if (galleryIndex) {
    activeGalleryIndex = Number(galleryIndex.dataset.galleryIndex);
    renderDialog(currentDialog);
    return;
  }
  if (galleryStep) {
    moveGallery(Number(galleryStep.dataset.galleryStep));
    return;
  }
  const product = event.target.closest("[data-product]");
  const opener = event.target.closest("[data-dialog]");
  if (product) openDialog(product.dataset.product);
  else if (opener) openDialog(opener.dataset.dialog);
  if (event.target.closest("[data-close-dialog],.dialog-close")) dialog.close();
});
dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  if (
    event.clientX < bounds.left ||
    event.clientX > bounds.right ||
    event.clientY < bounds.top ||
    event.clientY > bounds.bottom
  )
    dialog.close();
});
dialog.addEventListener("close", () => {
  currentDialog = null;
});
const menuButton = document.querySelector("#menu-toggle");
const nav = document.querySelector("#main-nav");
function closeMenu() {
  nav.classList.remove("is-open");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", t("باز کردن منو", "Open menu"));
}
menuButton.addEventListener("click", () => {
  const opened = nav.classList.toggle("is-open");
  menuButton.setAttribute("aria-expanded", String(opened));
  menuButton.setAttribute(
    "aria-label",
    opened ? t("بستن منو", "Close menu") : t("باز کردن منو", "Open menu"),
  );
});
nav.addEventListener("click", (event) => {
  if (event.target.closest("a,button")) closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
  if (dialog.open && currentDialog === "gallery" && companyImageIndex !== null && ["ArrowLeft", "ArrowRight"].includes(event.key)) {
    event.preventDefault();
    moveCompanyImage(event.key === "ArrowLeft" ? (language === "fa" ? 1 : -1) : (language === "fa" ? -1 : 1));
    dialog.querySelector(".dialog-close").focus();
    return;
  }
  if (dialog.open && event.key === "ArrowLeft") moveGallery(language === "fa" ? 1 : -1);
  if (dialog.open && event.key === "ArrowRight") moveGallery(language === "fa" ? -1 : 1);
});
function setLanguage(value) {
  language = value;
  document.documentElement.lang = value;
  document.documentElement.dir = value === "fa" ? "rtl" : "ltr";
  translatable.forEach((element) => {
    element.innerHTML = element.dataset[value];
  });
  document
    .querySelector(".language-switch")
    .setAttribute("aria-label", t("زبان سایت", "Site language"));
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute(
      "aria-current",
      button.dataset.language === value ? "page" : "false",
    );
  });
  document
    .querySelector(".dialog-close")
    .setAttribute("aria-label", t("بستن پنجره", "Close dialog"));
  nav.setAttribute("aria-label", t("منوی اصلی", "Main navigation"));

  document
    .querySelectorAll(".button .icon use[href='#i-arrow']")
    .forEach((icon) => icon.parentElement.classList.add("direction-arrow"));
  const labels = [
    [".brand", "فرازی کمپانی، صفحه اصلی", "Farazi Company, home"],
    [".breadcrumbs", "مسیر صفحه", "Breadcrumb"],
    [".trust-strip", "مزیت‌های فرازی کمپانی", "Why Farazi Company"],
    [".contact-methods", "راه‌های ارتباطی", "Contact methods"],
    [".social-links", "راه‌های ارتباطی", "Connect with us"],
    [
      ".map-art",
      "نقشه ارتباطات تجاری در سراسر جهان",
      "Illustration of global trade connections",
    ],
    [
      ".bazaar-art",
      "تصویرسازی الهام‌گرفته از معماری بازار تهران",
      "Illustration inspired by Tehran Bazaar architecture",
    ],
  ];
  labels.forEach(([selector, fa, en]) =>
    document.querySelector(selector)?.setAttribute("aria-label", t(fa, en)),
  );
  document.querySelectorAll("img[src*='tehran-bazaar']").forEach((img) => {
    if (img.alt)
      img.alt = t(
        "تصویرسازی معماری بازار تهران",
        "Illustration of Tehran Bazaar architecture",
      );
  });
  const sourcingImage = document.querySelector(".sourcing-image img");
  if (sourcingImage)
    sourcingImage.alt = t(
      "نخ‌های پنبه‌ای، مشکی و مسی در کنار یکدیگر",
      "Ivory, black and copper yarn spools",
    );
  const years = document.querySelector(".heritage-figure strong");
  if (years) years.innerHTML = t("۴۰", "40") + "<span>+</span>";
  menuButton.setAttribute(
    "aria-label",
    nav.classList.contains("is-open")
      ? t("بستن منو", "Close menu")
      : t("باز کردن منو", "Open menu"),
  );
  const preview = document.querySelector("#message-preview");
  if (preview && !preview.hidden) prepareContactDraft();
  renderProducts();
  renderCatalog();
  if (dialog.open && currentDialog) renderDialog(currentDialog);
  try {
    localStorage.setItem("farazi-language", value);
  } catch {}
}
// Interior pages retain their active page; only the home page tracks sections.
if (pageId === "home") {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        nav.querySelectorAll("a").forEach((link) => {
          const active = link.getAttribute("href") === "#" + entry.target.id;
          link.classList.toggle("active", active);
          if (active) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        });
      });
    },
    { rootMargin: "-5% 0px -65% 0px", threshold: 0 },
  );
  ["home", "products", "trade"].forEach((id) => {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  });
}
// Stable language URLs; preserve compatibility with previously shared links.
const requestedLanguage = new URLSearchParams(location.search).get("lang");
const pageLanguage = document.documentElement.lang;
if (["fa", "en"].includes(requestedLanguage) && requestedLanguage !== pageLanguage) {
  const target = document.querySelector('[data-language="' + requestedLanguage + '"]');
  if (target) location.replace(target.href + location.hash);
}
setLanguage(pageLanguage);

function prepareContactDraft() {
  const form = document.querySelector("#contact-form");
  if (!form) return;
  const fields = new FormData(form);
  const subject =
    document.querySelector("#message-subject").selectedOptions[0].textContent.trim();
  const lines = [
    t("نام: ", "Name: ") + fields.get("name").trim(),
    t("مجموعه: ", "Company: ") + (fields.get("company").trim() || "—"),
    t("ایمیل: ", "Email: ") + fields.get("email").trim(),
    t("موضوع: ", "Subject: ") + subject,
    "",
    fields.get("message").trim(),
  ];
  const body = lines.join("\n");
  document.querySelector("#message-body").textContent = body;
  document.querySelector("#email-draft-link").href =
    "mailto:farazicompanyfc@gmail.com?subject=" +
    encodeURIComponent(subject + " | Farazi Company") +
    "&body=" +
    encodeURIComponent(body);
}
const contactForm = document.querySelector("#contact-form");
if (contactForm) {
  contactForm.addEventListener(
    "invalid",
    (event) => {
      const field = event.target;
      if (field.validity.valueMissing)
        field.setCustomValidity(
          t("لطفاً این بخش را تکمیل کنید.", "Please complete this field."),
        );
      else if (field.validity.typeMismatch)
        field.setCustomValidity(
          t(
            "لطفاً یک نشانی ایمیل معتبر وارد کنید.",
            "Please enter a valid email address.",
          ),
        );
      else if (field.validity.tooShort)
        field.setCustomValidity(
          t(
            "پیام باید حداقل ۱۰ نویسه داشته باشد.",
            "Please enter at least 10 characters.",
          ),
        );
    },
    true,
  );

  contactForm.addEventListener("input", () => {
    document.querySelector("#message-preview").hidden = true;
    contactForm
      .querySelectorAll("input, textarea")
      .forEach((field) => field.setCustomValidity(""));
  });
  contactForm.addEventListener("change", () => {
    document.querySelector("#message-preview").hidden = true;
  });
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.querySelector("#sender-name");
    const message = document.querySelector("#sender-message");
    name.setCustomValidity(
      name.value.trim()
        ? ""
        : t("نام خود را وارد کنید.", "Please enter your name."),
    );
    message.setCustomValidity(
      message.value.trim().length >= 10
        ? ""
        : t(
            "پیام باید حداقل ۱۰ نویسه داشته باشد.",
            "Please enter at least 10 characters.",
          ),
    );
    if (!contactForm.reportValidity()) return;
    prepareContactDraft();
    document.querySelector("#message-preview").hidden = false;
    const title = document.querySelector("#preview-title");
    title.tabIndex = -1;
    title.focus();
  });
}
