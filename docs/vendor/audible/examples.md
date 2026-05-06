# Audible Examples

Source URL:

- <https://audible.readthedocs.io/en/latest/misc/examples.html>

## Marketplace Iteration Example

```python
import audible

auth = audible.Authenticator.from_file(filename)
client = audible.Client(auth)
country_codes = ["de", "us", "ca", "uk", "au", "fr", "jp", "it", "in"]

for country in country_codes:
    client.switch_marketplace(country)
    library = client.get("library", num_results=1000)
    asins = [book["asin"] for book in library["items"]]
    print(f"Country: {client.marketplace.upper()} | Number of books: {len(asins)}")
```

## Why This Matters Here

This is useful for the importer because marketplace differences affect:

- ASIN availability
- title variants like `Philosopher's` versus `Sorcerer's`
- narrator and edition differences
- region-unavailable results that may still exist in the local library

## Stats Example

The docs also show that `client.get(...)` can target other endpoints such as `1.0/stats/aggregates`, which confirms the client is a generic API wrapper rather than a library-only helper.
