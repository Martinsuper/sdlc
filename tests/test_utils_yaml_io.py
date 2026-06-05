from sdlc.utils.yaml_io import load_yaml, load_yaml_str, save_yaml


def test_load_yaml_str_dict():
    data = load_yaml_str("name: alice\nage: 30\n")
    assert data == {"name": "alice", "age": 30}


def test_load_yaml_str_list():
    data = load_yaml_str("- a\n- b\n- c\n")
    assert data == ["a", "b", "c"]


def test_round_trip_dict(tmp_path):
    p = tmp_path / "test.yaml"
    original = {"key": "value", "num": 42, "flag": True}
    save_yaml(p, original)
    loaded = load_yaml(p)
    assert loaded == original


def test_round_trip_list(tmp_path):
    p = tmp_path / "test.yaml"
    original = [1, 2, 3]
    save_yaml(p, original)
    loaded = load_yaml(p)
    assert loaded == original


def test_round_trip_nested(tmp_path):
    p = tmp_path / "test.yaml"
    original = {"items": [{"name": "a"}, {"name": "b"}], "count": 2}
    save_yaml(p, original)
    loaded = load_yaml(p)
    assert loaded == original


def test_preserve_comments(tmp_path):
    p = tmp_path / "test.yaml"
    yaml_text = "# top comment\nkey: value\n"
    p.write_text(yaml_text, encoding="utf-8")
    from ruamel.yaml import YAML

    y = YAML()
    with p.open("r", encoding="utf-8") as f:
        data = y.load(f)
    save_yaml(p, data, preserve=True)
    content = p.read_text(encoding="utf-8")
    assert "# top comment" in content
