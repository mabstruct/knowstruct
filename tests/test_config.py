import pytest

from ks.config import ConfigError, Env, load_env


def test_load_env_reads_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# c\nPLANE_BASE_URL="https://p.example/"\nPLANE_API_KEY=abc\n')
    env = load_env(f)
    assert env == Env(base_url="https://p.example", api_key="abc")


def test_load_env_missing_key_names_variable_not_value(tmp_path):
    f = tmp_path / ".env"
    f.write_text("PLANE_BASE_URL=https://p.example\n")
    with pytest.raises(ConfigError, match="PLANE_API_KEY"):
        load_env(f)


def test_load_env_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_env(tmp_path / ".env")
