from setuptools import setup
import gwb.global_properties as global_properties

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='gwbackupy',
    version=global_properties.version,
    packages=['gwb', 'gwb.storage'],
    url='https://github.com/smartondev/gwbackupy',
    license='BSD 3-Clause "New" or "Revised" License',
    author='Márton Somogyi',
    author_email='info@smarton.dev',
    description='Open source Google Workspace backup solution.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['google-api-python-client~=2.70.0', 'oauth2client~=4.1.3', 'pyopenssl~=22.1', 'tzlocal', 'pytz'],
    scripts=['scripts/gwbackupy'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
