# Audible Authentication

Source URLs:

- <https://audible.readthedocs.io/en/latest/auth/authentication.html>
- <https://audible.readthedocs.io/en/latest/auth/authorization.html>

## Supported Modes

The docs describe two API authentication modes:

- sign request
- bearer token

## Sign Request

This is the preferred mode because it provides unrestricted API access.

It relies on device registration data such as:

- RSA private key
- `adp_token`

The package applies this automatically when the `Authenticator` has the required data.

## Bearer Mode

Bearer mode is more limited.

The docs specifically note that some calls, including content license requests, do not work with bearer-only auth.

Headers look like:

```text
Authorization: Bearer Atna|...
client-id: 0
```

## Website Cookies

The `Authenticator` also exposes website cookies that can be used with `httpx.Client` for web endpoints that are not part of the external Audible API.

## Practical Guidance For This Repo

- do not store Audible usernames or passwords in repo files
- prefer an external auth file loaded with `Authenticator.from_file(...)`
- keep auth material outside committed files
- treat Audible auth as optional and secondary to ABS plus Audnex during early development
