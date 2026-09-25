# SEO implementation and launch notes

Reviewed against Google Search Central on 2026-09-25.

## Search intent and page ownership

| Query | Primary Persian page | Purpose |
| --- | --- | --- |
| نخ | products.html | Existing yarn collection, specifications and enquiries |
| نخ لمه | lame-yarn.html | Real catalogue specifications, sample photography and buying questions |
| نخ فانتزی | fancy-yarn.html | Selection guide and enquiry requirements; no unconfirmed stock claims |

The English equivalents use `.en.html`. The home page introduces the business and links to the catalogue and both guides. Do not create near-identical pages for spelling variations or cities. Add new pages only when there is distinct, useful content and a real service/product to describe.

## Implemented

- Visible descriptive home H1 and page-specific titles/descriptions.
- Two bilingual guide pages with crawlable HTML links from the home and catalogue pages.
- Real metallic-yarn product image as the first catalogue photo, with descriptive text and dimensions on the guide.
- Source-grounded fancy-yarn explanation with an educational reference. The precise fancy-yarn stock range remains unconfirmed.
- Twelve canonical URLs, reciprocal Persian/English/x-default alternates, sitemap and robots output in both static and PHP modes.
- Breadcrumb markup matching the guide hierarchy. Existing catalogue ItemList retained; no invented prices, ratings, reviews or availability.
- HTML content available before JavaScript executes; metadata generated on the server.
- Optional Apache compression for text assets. This is configuration, not a measured production Core Web Vitals result.
- `scripts/check-seo.py` verifies all configured pages, metadata, headings, language links, schema parsing, asset paths, guide links and sitemap parity.

## Verification commands

```powershell
python scripts/build-seo.py
python scripts/check-seo.py
php -S 127.0.0.1:8082 router.php
# In another terminal:
python scripts/check-seo.py --base-url http://127.0.0.1:8082/
```

Browser checks passed at desktop and mobile widths in Persian and English, including navigation to a guide and switching language. Production Apache rewrite/compression, real network performance and search indexing have not been verified. Opening the configured production URL through the web retrieval tool did not return a usable page; this alone does not establish the site's availability.

## Launch and Search Console

1. Deploy the updated pages, PHP files, `.htaccess`, configuration, scripts and referenced assets. The two new route names must be included in server rewrites. Keep the real production domain in `seo-config.json`.
2. Confirm HTTPS, the preferred host and redirects with the host administrator. Check both normal pages and a nonexistent URL (real 404, not a success page). Check live canonical/hreflang, response codes and rendered content.
3. Verify ownership of the domain property in Google Search Console. No verification token or account access was supplied, so none was fabricated or installed.
4. Submit `https://farazicompanyfc.com/sitemap.xml`. Use URL Inspection for the home, catalogue and two guides, confirm rendered content and request indexing where appropriate. Submission and indexing are not completed by local edits.
5. Run the live pages through Rich Results Test and PageSpeed Insights; review real-user Core Web Vitals when enough data exists. Do not treat local browser tests as a production performance score.
6. Monitor impressions, clicks, CTR and landing pages for the three Persian terms and relevant longer queries. Record the deployment date and compare equivalent periods after Google has had time to recrawl; ranking improvements are not guaranteed.
7. Have the business confirm the exact fancy-yarn range before adding stock or sales claims. Add genuine specifications, original sample images and customer questions as they become available. Keep contact and catalogue information accurate.

## Primary references

- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://developers.google.com/search/docs/appearance/structured-data/product-snippet
- https://cottonworks.com/wp-content/uploads/2017/11/Textile_Yarns.pdf
