#!/usr/bin/env python3
"""Build a self-contained, searchable HTML viewer from a WhatsApp export."""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BIDI_CONTROLS = dict.fromkeys(
    map(ord, "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"),
    None,
)
MESSAGE_RE = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+):(?:\s?(.*))?$"
)
ATTACHMENT_RE = re.compile(r"<attached:\s*([^>]+)>", re.IGNORECASE)
PASSWORD_RE = re.compile(r"(?:password|passwd|pass\s*word|پسورد|رمز(?:\s*عبور)?)", re.IGNORECASE)
URL_RE = re.compile(r"(?P<url>https?://[^\s<>]+|www\.[^\s<>]+)|(?P<email>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})")
REDACTION_TEXT = "🔒 اطلاعات ورود هاست برای حفظ امنیت در این نسخه پنهان شده است."


@dataclass
class Message:
    date_raw: str
    time_raw: str
    sender: str
    text: str
    timestamp: datetime
    attachments: list[str]
    redacted: bool = False


def clean_controls(value: str) -> str:
    return value.translate(BIDI_CONTROLS).replace("\ufeff", "")


def parse_timestamp(date_raw: str, time_raw: str) -> datetime:
    year_digits = len(date_raw.rsplit("/", 1)[-1])
    date_format = "%m/%d/%Y" if year_digits == 4 else "%m/%d/%y"
    return datetime.strptime(f"{date_raw} {time_raw}", f"{date_format} %H:%M:%S")


def parse_chat(chat_path: Path) -> list[Message]:
    messages: list[Message] = []
    current: dict[str, str] | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = clean_controls(current["text"]).strip()
        attachments = [name.strip() for name in ATTACHMENT_RE.findall(text)]
        text = ATTACHMENT_RE.sub("", text).strip()
        if text or attachments:
            messages.append(
                Message(
                    date_raw=current["date"],
                    time_raw=current["time"],
                    sender=clean_controls(current["sender"]).strip(),
                    text=text,
                    timestamp=parse_timestamp(current["date"], current["time"]),
                    attachments=attachments,
                )
            )
        current = None

    raw_text = chat_path.read_text(encoding="utf-8-sig")
    for raw_line in raw_text.splitlines():
        line = clean_controls(raw_line)
        match = MESSAGE_RE.match(line)
        if match:
            flush()
            current = {
                "date": match.group(1),
                "time": match.group(2),
                "sender": match.group(3),
                "text": match.group(4) or "",
            }
        elif current is not None:
            current["text"] += "\n" + line
    flush()
    return messages


def redact_credentials(messages: list[Message]) -> int:
    redact_next = False
    redacted_count = 0
    for message in messages:
        original_text = message.text
        password_match = PASSWORD_RE.search(original_text)
        password_reference = bool(password_match)
        if redact_next or password_reference:
            message.text = REDACTION_TEXT
            message.redacted = True
            redacted_count += 1
        if password_match:
            original_tail = original_text[password_match.end() :].strip(" :=-—\n\t")
            redact_next = not original_tail
        else:
            redact_next = False
    return redacted_count


def linkify(value: str) -> str:
    chunks: list[str] = []
    cursor = 0
    for match in URL_RE.finditer(value):
        chunks.append(html.escape(value[cursor : match.start()]))
        token = match.group(0)
        if match.group("email"):
            href = f"mailto:{token}"
        elif token.startswith("www."):
            href = f"https://{token}"
        else:
            href = token
        chunks.append(
            f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(token)}</a>"
        )
        cursor = match.end()
    chunks.append(html.escape(value[cursor:]))
    return "".join(chunks).replace("\n", "<br>")


def data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if path.suffix.lower() == ".opus":
        mime = "audio/ogg"
    mime = mime or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def persian_digits(value: str) -> str:
    return value.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def render_attachment(path: Path, message: Message, media_number: int) -> tuple[str, str]:
    source = data_url(path)
    suffix = path.suffix.lower()
    safe_name = html.escape(path.name)
    context = html.escape(f"{message.sender}، {message.date_raw}، {message.time_raw}", quote=True)
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return (
            f'<figure class="media media-image">'
            f'<button type="button" class="image-open" aria-label="باز کردن تصویر {media_number}" '
            f'data-caption="{context}">'
            f'<img loading="lazy" decoding="async" src="{source}" alt="تصویر پیوست‌شده شماره {media_number}">'
            f'</button><figcaption>{safe_name}</figcaption></figure>',
            "image",
        )
    if suffix in {".opus", ".ogg", ".mp3", ".m4a", ".wav", ".aac"}:
        return (
            f'<div class="media media-audio"><div class="audio-label">'
            f'<span aria-hidden="true">◉</span><span>پیام صوتی</span></div>'
            f'<audio controls preload="metadata" src="{source}">مرورگر شما پخش صدا را پشتیبانی نمی‌کند.</audio>'
            f'<span class="media-name">{safe_name}</span></div>',
            "audio",
        )
    return (
        f'<a class="media media-file" href="{source}" download="{safe_name}">دریافت {safe_name}</a>',
        "file",
    )


def render_archive(messages: list[Message], export_dir: Path, redacted_count: int) -> str:
    participants = list(dict.fromkeys(message.sender for message in messages))
    self_sender = next((name for name in participants if "Ehsan" in name), participants[-1])
    message_parts: list[str] = []
    seen_dates: list[str] = []
    media_total = image_total = audio_total = 0
    current_date = ""

    for index, message in enumerate(messages, start=1):
        date_key = message.timestamp.strftime("%Y-%m-%d")
        if date_key != current_date:
            current_date = date_key
            seen_dates.append(date_key)
            date_label = persian_digits(message.timestamp.strftime("%Y/%m/%d"))
            message_parts.append(
                f'<section class="day-group" data-day="{date_key}"><div class="date-divider" id="day-{date_key}">'
                f'<span>{date_label}</span></div>'
            )
        media_markup: list[str] = []
        media_kinds: set[str] = set()
        for attachment in message.attachments:
            media_path = export_dir / attachment
            if not media_path.is_file():
                media_markup.append(
                    f'<div class="missing-media">فایل پیدا نشد: {html.escape(attachment)}</div>'
                )
                media_kinds.add("missing")
                continue
            media_total += 1
            markup, kind = render_attachment(media_path, message, media_total)
            media_markup.append(markup)
            media_kinds.add(kind)
            image_total += int(kind == "image")
            audio_total += int(kind == "audio")

        sender_class = "mine" if message.sender == self_sender else "theirs"
        sender_label = "احسان طباطبایی" if sender_class == "mine" else message.sender.lstrip("~")
        text_markup = f'<div class="message-text" dir="auto">{linkify(message.text)}</div>' if message.text else ""
        type_tokens = " ".join(sorted(media_kinds)) if media_kinds else "text"
        search_text = clean_controls(f"{sender_label} {message.text} {' '.join(message.attachments)}").lower()
        redacted_badge = '<span class="redacted-label">محرمانه</span>' if message.redacted else ""
        message_parts.append(
            f'<article class="message {sender_class}" id="message-{index}" '
            f'data-sender="{sender_class}" data-types="{html.escape(type_tokens, quote=True)}" '
            f'data-search="{html.escape(search_text, quote=True)}">'
            f'<div class="bubble"><header><strong>{html.escape(sender_label)}</strong>{redacted_badge}</header>'
            f'{text_markup}{"".join(media_markup)}'
            f'<footer><time datetime="{message.timestamp.isoformat()}">{persian_digits(message.time_raw[:5])}</time>'
            f'<a href="#message-{index}" aria-label="پیوند به پیام {index}">#{persian_digits(str(index))}</a></footer>'
            f'</div></article>'
        )
        next_message = messages[index] if index < len(messages) else None
        if next_message is None or next_message.timestamp.strftime("%Y-%m-%d") != current_date:
            message_parts.append("</section>")

    start_date = persian_digits(messages[0].timestamp.strftime("%Y/%m/%d"))
    end_date = persian_digits(messages[-1].timestamp.strftime("%Y/%m/%d"))
    options = "".join(
        f'<option value="day-{date}">{persian_digits(datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d"))}</option>'
        for date in seen_dates
    )
    participant_text = " و ".join(html.escape(name.lstrip("~")) for name in participants)

    template = r'''<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>آرشیو گفت‌وگوی فرازی کمپانی</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%23111c19'/%3E%3Cpath d='M18 18h28v21H31l-9 7v-7h-4z' fill='%23bd7044'/%3E%3C/svg%3E">
  <style>
    :root {
      color-scheme: light;
      --ink: #17201d;
      --muted: #66736e;
      --dark: #111c19;
      --dark-soft: #1b2925;
      --copper: #bd7044;
      --copper-deep: #945233;
      --paper: #f4efe8;
      --surface: #fffdf9;
      --mine: #dcefe7;
      --theirs: #ffffff;
      --line: rgba(23, 32, 29, .11);
      --shadow: 0 16px 40px rgba(24, 32, 29, .09);
      font-family: Tahoma, "Segoe UI", Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { margin: 0; color: var(--ink); background: var(--paper); min-height: 100vh; }
    button, input, select { font: inherit; }
    a { color: var(--copper-deep); text-underline-offset: 3px; }
    .app-header {
      position: sticky; top: 0; z-index: 30; color: #fff;
      background: linear-gradient(135deg, var(--dark), var(--dark-soft));
      border-bottom: 1px solid rgba(255,255,255,.09);
      box-shadow: 0 10px 30px rgba(6, 12, 10, .22);
    }
    .header-inner { width: min(1120px, calc(100% - 32px)); margin: auto; padding: 18px 0 14px; }
    .title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
    h1 { margin: 0 0 7px; font-size: clamp(1.2rem, 2.7vw, 1.85rem); line-height: 1.35; }
    .subtitle { margin: 0; color: rgba(255,255,255,.66); font-size: .82rem; line-height: 1.8; }
    .top-button {
      flex: 0 0 auto; border: 1px solid rgba(255,255,255,.2); color: #fff; background: rgba(255,255,255,.08);
      border-radius: 10px; padding: 9px 13px; cursor: pointer;
    }
    .toolbar { display: grid; grid-template-columns: minmax(190px, 1fr) auto auto; gap: 10px; margin-top: 16px; }
    .search-wrap { position: relative; }
    .search-wrap svg { position: absolute; right: 13px; top: 50%; transform: translateY(-50%); color: #94a29d; }
    .search-wrap input, .toolbar select {
      width: 100%; min-height: 42px; border: 1px solid rgba(255,255,255,.15); border-radius: 11px;
      color: #fff; background: rgba(255,255,255,.08); outline: none;
    }
    .search-wrap input { padding: 9px 42px 9px 13px; }
    .search-wrap input::placeholder { color: #aeb9b5; }
    .search-wrap input:focus, .toolbar select:focus { border-color: var(--copper); box-shadow: 0 0 0 3px rgba(189,112,68,.2); }
    .toolbar select { padding: 7px 10px; min-width: 142px; }
    .toolbar select option { color: var(--ink); }
    .filter-row { display: flex; gap: 7px; margin-top: 10px; overflow-x: auto; scrollbar-width: thin; padding-bottom: 2px; }
    .filter {
      white-space: nowrap; color: rgba(255,255,255,.75); border: 1px solid rgba(255,255,255,.13);
      background: transparent; padding: 7px 12px; border-radius: 999px; cursor: pointer; font-size: .78rem;
    }
    .filter[aria-pressed="true"] { color: #fff; border-color: var(--copper); background: var(--copper); }
    main {
      background-color: var(--paper);
      background-image: radial-gradient(rgba(148,82,51,.08) .8px, transparent .8px);
      background-size: 19px 19px;
      min-height: calc(100vh - 160px);
    }
    .archive { width: min(920px, calc(100% - 28px)); margin: auto; padding: 28px 0 90px; }
    .summary {
      display: flex; align-items: center; justify-content: space-between; gap: 18px; margin: 0 auto 26px;
      padding: 16px 18px; color: #f9f6f1; background: var(--dark-soft); border-radius: 16px; box-shadow: var(--shadow);
    }
    .summary strong { display: block; margin-bottom: 5px; }
    .summary p { margin: 0; color: rgba(255,255,255,.65); font-size: .78rem; line-height: 1.8; }
    .summary-count { flex: 0 0 auto; color: #fff; background: rgba(189,112,68,.18); border: 1px solid rgba(189,112,68,.36); border-radius: 12px; padding: 10px 13px; font-size: .82rem; }
    .date-divider { display: flex; align-items: center; justify-content: center; margin: 30px 0 20px; scroll-margin-top: 190px; }
    .date-divider span { color: #5f6d68; background: rgba(255,255,255,.88); border: 1px solid var(--line); border-radius: 999px; padding: 7px 13px; font-size: .74rem; box-shadow: 0 5px 16px rgba(24,32,29,.06); }
    .message { display: flex; margin: 8px 0; scroll-margin-top: 190px; }
    .message.mine { justify-content: flex-start; }
    .message.theirs { justify-content: flex-end; }
    .bubble { position: relative; width: fit-content; max-width: min(76%, 650px); padding: 10px 12px 7px; border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 4px 14px rgba(24,32,29,.055); }
    .mine .bubble { background: var(--mine); border-top-right-radius: 4px; }
    .theirs .bubble { background: var(--theirs); border-top-left-radius: 4px; }
    .bubble header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; color: var(--copper-deep); font-size: .73rem; }
    .redacted-label { color: #fff; background: #7e3f37; border-radius: 999px; padding: 2px 7px; font-size: .63rem; }
    .message-text { font-size: .9rem; line-height: 1.9; overflow-wrap: anywhere; white-space: normal; }
    .bubble footer { display: flex; direction: ltr; justify-content: flex-start; gap: 7px; align-items: center; margin-top: 5px; color: var(--muted); font-size: .66rem; }
    .bubble footer a { color: inherit; text-decoration: none; opacity: .7; }
    .media { margin-top: 9px; }
    figure { margin-inline: 0; margin-bottom: 0; }
    .image-open { display: block; width: 100%; padding: 0; border: 0; border-radius: 10px; overflow: hidden; cursor: zoom-in; background: #d8ddd9; }
    .media-image img { display: block; width: 100%; max-width: 520px; max-height: 520px; object-fit: contain; }
    figcaption, .media-name { display: block; margin-top: 5px; color: var(--muted); font-size: .62rem; direction: ltr; text-align: left; overflow-wrap: anywhere; }
    .media-audio { min-width: min(380px, 60vw); }
    .audio-label { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; color: var(--copper-deep); font-size: .78rem; }
    .audio-label span:first-child { display: grid; place-items: center; width: 26px; height: 26px; color: #fff; background: var(--copper); border-radius: 50%; }
    audio { display: block; width: 100%; height: 38px; }
    .missing-media { padding: 12px; color: #7e3f37; background: #fff0ed; border: 1px dashed #c98980; border-radius: 10px; }
    .empty { display: none; text-align: center; padding: 60px 18px; color: var(--muted); }
    .empty.visible { display: block; }
    .day-group.hidden, .message.hidden { display: none; }
    .jump-bottom {
      position: fixed; left: 22px; bottom: 22px; z-index: 20; width: 46px; height: 46px; border: 0; border-radius: 50%;
      color: #fff; background: var(--copper); box-shadow: 0 12px 30px rgba(148,82,51,.32); cursor: pointer; font-size: 1.2rem;
    }
    dialog { width: min(94vw, 980px); max-height: 92vh; padding: 0; border: 0; border-radius: 18px; overflow: hidden; background: #0d1513; box-shadow: 0 28px 80px rgba(0,0,0,.45); }
    dialog::backdrop { background: rgba(5,9,8,.83); backdrop-filter: blur(4px); }
    .lightbox-inner { position: relative; display: grid; place-items: center; min-height: 70vh; padding: 54px 20px 46px; }
    .lightbox-inner img { display: block; max-width: 100%; max-height: 75vh; object-fit: contain; border-radius: 8px; }
    .lightbox-close { position: absolute; top: 12px; left: 12px; width: 36px; height: 36px; border: 1px solid rgba(255,255,255,.2); border-radius: 50%; color: #fff; background: rgba(255,255,255,.08); cursor: pointer; font-size: 1.25rem; }
    .lightbox-caption { position: absolute; right: 18px; bottom: 14px; left: 18px; color: rgba(255,255,255,.7); text-align: center; font-size: .75rem; }
    @media (max-width: 680px) {
      .header-inner { width: min(100% - 22px, 1120px); padding-top: 13px; }
      .title-row { gap: 10px; }
      .subtitle { max-width: 250px; }
      .toolbar { grid-template-columns: 1fr auto; }
      .search-wrap { grid-column: 1 / -1; }
      .toolbar select { min-width: 0; }
      .archive { width: min(100% - 16px, 920px); padding-top: 18px; }
      .summary { align-items: flex-start; padding: 14px; }
      .summary-count { font-size: .72rem; }
      .bubble { max-width: 91%; }
      .message-text { font-size: .86rem; }
      .media-audio { min-width: min(300px, 76vw); }
      .jump-bottom { left: 14px; bottom: 14px; }
    }
    @media print {
      .app-header, .jump-bottom, dialog { display: none !important; }
      body, main { background: #fff; }
      .archive { width: 100%; padding: 0; }
      .summary { color: #111; background: #eee; box-shadow: none; }
      .summary p { color: #444; }
      .message { break-inside: avoid; }
      .bubble { max-width: 82%; box-shadow: none; }
      audio { display: none; }
    }
  </style>
</head>
<body>
  <header class="app-header">
    <div class="header-inner">
      <div class="title-row">
        <div>
          <h1>آرشیو گفت‌وگوی فرازی کمپانی</h1>
          <p class="subtitle">__PARTICIPANTS__ · از __START_DATE__ تا __END_DATE__</p>
        </div>
        <button class="top-button" type="button" id="print-chat">چاپ / PDF</button>
      </div>
      <div class="toolbar">
        <label class="search-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.8-3.8"></path></svg>
          <input id="search" type="search" placeholder="جست‌وجو در متن، نام یا فایل…" autocomplete="off">
        </label>
        <select id="day-picker" aria-label="رفتن به تاریخ"><option value="">رفتن به تاریخ…</option>__DATE_OPTIONS__</select>
        <select id="sort-order" aria-label="ترتیب پیام‌ها"><option value="oldest">قدیمی به جدید</option><option value="newest">جدید به قدیم</option></select>
      </div>
      <div class="filter-row" aria-label="فیلتر پیام‌ها">
        <button class="filter" type="button" data-filter="all" aria-pressed="true">همه</button>
        <button class="filter" type="button" data-filter="theirs" aria-pressed="false">کارفرما</button>
        <button class="filter" type="button" data-filter="mine" aria-pressed="false">احسان</button>
        <button class="filter" type="button" data-filter="image" aria-pressed="false">تصاویر</button>
        <button class="filter" type="button" data-filter="audio" aria-pressed="false">ویس‌ها</button>
      </div>
    </div>
  </header>
  <main>
    <div class="archive" id="archive">
      <section class="summary">
        <div><strong>نسخهٔ خوانا و خودکفا</strong><p>همهٔ مدیا داخل همین فایل HTML قرار دارد. اطلاعات ورود هاست عمداً پنهان شده و صفحه برای موتورهای جست‌وجو noindex است.</p></div>
        <div class="summary-count"><span id="visible-count">__MESSAGE_COUNT__</span> پیام · __IMAGE_COUNT__ تصویر · __AUDIO_COUNT__ ویس</div>
      </section>
      <div id="messages">__MESSAGES__</div>
      <div class="empty" id="empty-state">پیامی با این جست‌وجو یا فیلتر پیدا نشد.</div>
    </div>
  </main>
  <button class="jump-bottom" type="button" id="jump-bottom" aria-label="رفتن به انتهای گفت‌وگو">↓</button>
  <dialog id="lightbox" aria-label="نمایش تصویر">
    <div class="lightbox-inner">
      <button class="lightbox-close" type="button" aria-label="بستن">×</button>
      <img alt="تصویر پیوست‌شده در اندازه بزرگ">
      <div class="lightbox-caption"></div>
    </div>
  </dialog>
  <noscript><p>برای جست‌وجو و بازکردن تصاویر، JavaScript مرورگر را فعال کنید.</p></noscript>
  <script>
    (() => {
      const search = document.querySelector('#search');
      const filters = [...document.querySelectorAll('.filter')];
      const groups = [...document.querySelectorAll('.day-group')];
      const messages = [...document.querySelectorAll('.message')];
      const visibleCount = document.querySelector('#visible-count');
      const empty = document.querySelector('#empty-state');
      const messagesRoot = document.querySelector('#messages');
      let activeFilter = 'all';

      const applyFilters = () => {
        const query = search.value.trim().toLocaleLowerCase('fa');
        let count = 0;
        messages.forEach(message => {
          const sender = message.dataset.sender;
          const types = message.dataset.types.split(' ');
          const filterMatch = activeFilter === 'all' || sender === activeFilter || types.includes(activeFilter);
          const searchMatch = !query || message.dataset.search.includes(query);
          const visible = filterMatch && searchMatch;
          message.classList.toggle('hidden', !visible);
          if (visible) count += 1;
        });
        groups.forEach(group => {
          group.classList.toggle('hidden', !group.querySelector('.message:not(.hidden)'));
        });
        visibleCount.textContent = new Intl.NumberFormat('fa-IR').format(count);
        empty.classList.toggle('visible', count === 0);
      };

      filters.forEach(button => button.addEventListener('click', () => {
        activeFilter = button.dataset.filter;
        filters.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        applyFilters();
      }));
      search.addEventListener('input', applyFilters);
      document.querySelector('#day-picker').addEventListener('change', event => {
        if (!event.target.value) return;
        document.getElementById(event.target.value)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      document.querySelector('#sort-order').addEventListener('change', event => {
        const ordered = [...groups].sort((a, b) => event.target.value === 'newest'
          ? b.dataset.day.localeCompare(a.dataset.day)
          : a.dataset.day.localeCompare(b.dataset.day));
        ordered.forEach(group => messagesRoot.appendChild(group));
      });
      document.querySelector('#print-chat').addEventListener('click', () => window.print());
      document.querySelector('#jump-bottom').addEventListener('click', () => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));

      const lightbox = document.querySelector('#lightbox');
      const lightboxImage = lightbox.querySelector('img');
      const lightboxCaption = lightbox.querySelector('.lightbox-caption');
      document.addEventListener('click', event => {
        const trigger = event.target.closest('.image-open');
        if (!trigger) return;
        lightboxImage.src = trigger.querySelector('img').src;
        lightboxCaption.textContent = trigger.dataset.caption;
        lightbox.showModal();
      });
      lightbox.querySelector('.lightbox-close').addEventListener('click', () => lightbox.close());
      lightbox.addEventListener('click', event => { if (event.target === lightbox) lightbox.close(); });
      document.addEventListener('keydown', event => {
        if (event.key === '/' && document.activeElement !== search) { event.preventDefault(); search.focus(); }
      });
    })();
  </script>
</body>
</html>
'''
    return (
        template.replace("__PARTICIPANTS__", participant_text)
        .replace("__START_DATE__", start_date)
        .replace("__END_DATE__", end_date)
        .replace("__DATE_OPTIONS__", options)
        .replace("__MESSAGE_COUNT__", persian_digits(str(len(messages))))
        .replace("__IMAGE_COUNT__", persian_digits(str(image_total)))
        .replace("__AUDIO_COUNT__", persian_digits(str(audio_total)))
        .replace("__MESSAGES__", "".join(message_parts))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_dir", type=Path, help="Directory containing _chat.txt and attachments")
    parser.add_argument("output", type=Path, help="Destination HTML file")
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    chat_path = export_dir / "_chat.txt"
    if not chat_path.is_file():
        raise SystemExit(f"Chat export not found: {chat_path}")

    messages = parse_chat(chat_path)
    if not messages:
        raise SystemExit("No messages were parsed from the export.")

    referenced = [name for message in messages for name in message.attachments]
    missing = [name for name in referenced if not (export_dir / name).is_file()]
    if missing:
        raise SystemExit("Missing attachments: " + ", ".join(missing))

    redacted_count = redact_credentials(messages)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_archive(messages, export_dir, redacted_count), encoding="utf-8")
    print(
        f"Built {output}\n"
        f"messages={len(messages)} attachments={len(referenced)} redacted_messages={redacted_count} "
        f"size_bytes={output.stat().st_size}"
    )


if __name__ == "__main__":
    main()
