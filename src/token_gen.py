def generate_token():
    import secrets
    return secrets.token_urlsafe(16)

def verify_token(token, valid_tokens):
    return token in valid_tokens