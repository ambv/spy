import pytest
import os
import pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent

def test_mypy():
    mypy_ini = ROOT.joinpath('mypy.ini')
    assert mypy_ini.exists()
    os.environ['MYPY_FORCE_COLOR'] = '1'
    print()
    ret = os.system('mypy')
    print()
    if ret != 0:
        pytest.fail('mypy failed')
