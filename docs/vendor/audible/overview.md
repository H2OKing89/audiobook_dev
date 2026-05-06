# Audible Overview

Source URLs:

- <https://audible.readthedocs.io/en/latest/index.html>
- <https://github.com/mkb79/Audible>

## Workspace Notes

- Installed package version in this workspace: `audible 0.8.2`
- ReadTheDocs pages currently describe `0.10.0`
- The core runtime surface we verified is present in `0.8.2`:
  - `audible.Authenticator.from_file(...)`
  - `audible.Authenticator.from_login(...)`
  - `audible.Client`
  - `audible.AsyncClient`
  - `client.get/post/put/delete/switch_marketplace`

## What The Package Is

`audible` is a Python client for Audible's non-public API. It provides:

- device registration and credential handling
- automatic request authentication
- synchronous and asynchronous clients
- access to library, catalog, content, and account endpoints

## Why It Matters For This Importer

Audible support gives the importer a second strong metadata source next to Audnex.

Use it for:

- direct library enumeration from the user's Audible account
- product metadata lookups by ASIN
- richer response groups than Audnex in some cases
- validating ASINs and edition variants against the user's owned library

Do not use it as the only metadata source. It should complement:

- Audiobookshelf item metadata
- Audnex product and chapter data
- local tags and filenames

## Key Runtime Pattern

```python
import audible

auth = audible.Authenticator.from_file("credentials.json", password="...")
with audible.Client(auth=auth) as client:
    library = client.get("1.0/library", num_results=1000)
```
