import sys, os
# allow tests to import from the 'src' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

@pytest.fixture
def sample_html():
    return "<p>First paragraph.</p><p>Second<br>Line</p>"

@pytest.fixture
def sample_authors():
    return [
        {"name": "John Doe"},
        {"name": "Jane Translator"},
        {"name": "Alice Illustrator"}
    ]

@pytest.fixture
def sample_item():
    return {
        "title": "Test Title",
        "subtitle": "SubTitle",
        "authors": [{"name": "Author One"}, {"name": "Translator Two"}],
        "narrators": [{"name": "Narrator A"}],
        "publisherName": "Pub House",
        "releaseDate": "2020-01-01T00:00:00Z",
        "summary": "<p>Summary paragraph.</p>",
        "description": "<p>Description paragraph.</p>",
        "image": "http://example.com/cover.jpg",
        "asin": "B000123456",
        "isbn": "1234567890",
        "genres": [
            {"type": "genre", "name": "Fantasy"},
            {"type": "tag", "name": "Epic"}
        ],
        "seriesPrimary": {"name": "Series Name", "position": "1"},
        "seriesSecondary": {"name": "Other Series", "position": ""},
        "language": "en",
        "runtimeLengthMin": 600,
        "region": "us",
        "rating": 4.5,
        "formatType": "abridged"
    }

@pytest.fixture
def sample_payload():
    return {"name": "Test Name", "url": "http://example.com", "download_url": "http://example.com/file"}
