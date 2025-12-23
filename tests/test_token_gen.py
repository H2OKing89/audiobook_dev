from src.token_gen import generate_token, verify_token


class TestTokenGeneration:
    def test_generate_token_length(self):
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 10  # URL-safe base64 tokens are typically longer

    def test_generate_token_uniqueness(self):
        tokens = [generate_token() for _ in range(100)]
        # All tokens should be unique
        assert len(set(tokens)) == 100

    def test_generate_token_format(self):
        token = generate_token()
        # Should be URL-safe (no special characters that need encoding)
        import string

        allowed_chars = string.ascii_letters + string.digits + "-_"
        assert all(c in allowed_chars for c in token)

    def test_verify_token_valid(self):
        valid_tokens = ["token1", "token2", "token3"]
        assert verify_token("token1", valid_tokens) is True
        assert verify_token("token2", valid_tokens) is True
        assert verify_token("token3", valid_tokens) is True

    def test_verify_token_invalid(self):
        valid_tokens = ["token1", "token2", "token3"]
        assert verify_token("invalid", valid_tokens) is False
        assert verify_token("", valid_tokens) is False
        assert verify_token("TOKEN1", valid_tokens) is False  # Case sensitive

    def test_verify_token_empty_list(self):
        assert verify_token("any_token", []) is False

    def test_verify_token_edge_cases(self):
        valid_tokens = ["token1", "token2"]
        # The function actually just returns False for None (Python's `in` operator handles it)
        # This might not be ideal but it's the current behavior
        assert verify_token("", valid_tokens) is False

    def test_generated_token_verification(self):
        # Test that a generated token can be verified
        token = generate_token()
        valid_tokens = [token, "other_token"]
        assert verify_token(token, valid_tokens) is True
