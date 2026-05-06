# Audible Getting Started

Source URL:

- <https://audible.readthedocs.io/en/latest/intro/getting_started.html>

## Device Registration

Before using the Audible API, you authorize against Amazon or Audible and register a virtual device.

Reference pattern:

```python
import audible

auth = audible.Authenticator.from_login(
    USERNAME,
    PASSWORD,
    locale=COUNTRY_CODE,
    with_username=False,
)
auth.to_file(FILENAME)
```

Notes:

- every device registration appears in the Amazon devices list
- the docs recommend registering once and reusing the saved auth file
- two-factor auth can be handled by appending the current OTP to the password in some cases

## First Library Call

Reference pattern:

```python
with audible.Client(auth=auth) as client:
    library = client.get(
        "1.0/library",
        num_results=1000,
        response_groups="product_desc, product_attrs",
        sort_by="-PurchaseDate",
    )
```

## Reusing Credentials

Reference pattern:

```python
auth = audible.Authenticator.from_file(FILENAME)
```

For this importer, file-based auth reuse is the right default. Interactive login should stay outside the normal import path.
