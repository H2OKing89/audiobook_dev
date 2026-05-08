# Audible External API Reference

Source URL:

- <https://audible.readthedocs.io/en/latest/misc/external_api.html>

## Important Note

The Audible API is not publicly documented by Audible. The `audible` package docs provide community-maintained endpoint notes.

Responses often return minimal data unless `response_groups` are requested.

## Endpoints Relevant To This Importer

### Library

`GET /1.0/library`

Useful query parameters:

- `num_results` up to `1000`
- `page`
- `title`
- `author`
- `sort_by`
- `response_groups`

Relevant response groups include:

- `contributors`
- `media`
- `product_attrs`
- `product_desc`
- `product_details`
- `product_extended_attrs`
- `series`
- `relationships`
- `origin_asin`
- `pdf_url`

`GET /1.0/library/{asin}`

Use this for richer per-book library data when a title is already known.

### Catalog

`GET /1.0/catalog/products/{asin}`

This is the key product lookup endpoint for the importer.

Useful response groups:

- `contributors`
- `media`
- `product_attrs`
- `product_desc`
- `product_details`
- `product_extended_attrs`
- `series`
- `relationships`
- `rating`
- `customer_rights`

`GET /1.0/catalog/products`

Supports batch lookup using `asins`.

### Content

`GET /1.0/content/{asin}/metadata`

Potentially useful for content reference and chapter-related metadata.

`POST /1.0/content/{asin}/licenserequest`

Not needed for importer naming. This is relevant for download and DRM workflows, which should stay out of scope for now.

## Recommended Usage For Naming

For importer metadata, the best starting sequence is:

1. enumerate owned titles with `GET /1.0/library`
2. enrich a specific ASIN with `GET /1.0/catalog/products/{asin}`
3. compare Audible fields against Audnex, ABS, and local filenames
4. use Audible as a tie-breaker and ownership-aware source, not the only source of truth
