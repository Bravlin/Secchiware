from setuptools import setup

setup(
    name="secchiware_common",
    version="0.5",
    description="Common libraries for Secchiware products.",
    author="Braulio Pablos",
    author_email="brauliopablos@outlook.com",
    url="https://github.com/Bravlin/Secchiware",
    py_modules=['signatures', 'test_utils', 'redis_custom_locking']
)