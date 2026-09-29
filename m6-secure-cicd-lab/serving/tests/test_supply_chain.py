"""TestSupplyChain — does tampering actually get detected? A failure means the protection is theatre."""
import os
from model.package_model import PKG, package, verify, tamper


def test_clean_package_verifies():
    package()
    assert verify() is True


def test_modified_file_is_caught():
    package()
    tamper()
    assert verify() is False
    package()  # restore


def test_added_file_is_caught():
    package()
    open(os.path.join(PKG, "sitecustomize.py"), "w").write("# a file nobody approved\n")
    assert verify() is False  # 'these files and no others'
    package()  # restore
