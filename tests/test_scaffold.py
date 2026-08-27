import hplcsim


def test_package_importable_with_version() -> None:
    assert hplcsim.__version__ == "0.1.0"
