from sdlc.utils.text import normalize, slugify, trim


def test_trim_short_string_unchanged():
    assert trim("hello", max_len=10) == "hello"


def test_trim_long_string_truncates():
    result = trim("a" * 300, max_len=200)
    assert len(result) == 200
    assert result.endswith("...")
    assert result == "a" * 197 + "..."


def test_normalize_collapses_whitespace():
    assert normalize("  hello   world  ") == "hello world"


def test_normalize_strips():
    assert normalize("\t\nhello\n\t") == "hello"


def test_slugify_url_safe():
    assert slugify("Hello World!") == "hello-world"


def test_slugify_collapses_hyphens():
    assert slugify("foo   bar---baz") == "foo-bar-baz"


def test_slugify_chinese_input():
    result = slugify("你好 世界")
    assert isinstance(result, str)
    assert " " not in result
