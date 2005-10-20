from distutils.core import setup

distobj = setup(
    name="Xapwrap",
    version="0.3",
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/projects/xapwrap",
    license="MIT",
    platforms=["any"],
    description="Improved interfaceto the Xapian text indexing library",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Topic :: Text Processing :: Indexing"],

    packages=['xapwrap'])

