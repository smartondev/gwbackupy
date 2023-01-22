from setuptools import setup
import gwbackupy.global_properties as global_properties

with open("README.md", "r") as fh:
    long_description = fh.read()

requires = []
with open("requirements.txt", "r") as fh:
    for line in fh.readlines():
        requires.append(line.strip())

setup(
    name="gwbackupy",
    version=global_properties.version,
    packages=[
        "gwbackupy",
        "gwbackupy.storage",
        "gwbackupy.filters",
        "gwbackupy.providers",
    ],
    url="https://github.com/smartondev/gwbackupy",
    license='BSD 3-Clause "New" or "Revised" License',
    author="Márton Somogyi",
    author_email="info@smarton.dev",
    description="Open source Google Workspace backup solution.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requires,
    scripts=["scripts/gwbackupy"],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Environment :: Console",
        "Programming Language :: Python",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
