import sys


def test_python_runtime_is_3_14_or_newer() -> None:
    assert sys.version_info >= (3, 14)
    assert sys.version_info < (3, 15)
