from distutils.core import setup

from xapwrap import version

distobj = setup(
    name="Xapwrap",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/DivmodXapwrap",
    license="MIT",
    platforms=["any"],
    description="Improved interface to the Xapian text indexing library",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Topic :: Text Processing :: Indexing"],

    packages=['xapwrap'])

