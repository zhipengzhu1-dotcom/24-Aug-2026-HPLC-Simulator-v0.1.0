import tomllib
from pathlib import Path

import hplcsim


def test_package_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text())["project"]["version"]
    assert hplcsim.__version__ == expected
