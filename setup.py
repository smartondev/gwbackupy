from setuptools import setup

setup(
    name='gwbackupy',
    version='0.1.1',
    packages=['gwb'],
    url='https://github.com/smartondev/gwbackupy',
    license='BSD 3-Clause "New" or "Revised" License',
    author='Márton Somogyi',
    author_email='info@smarton.dev',
    description='Open source Google Workspace backup solution.',
    install_requires=['google-api-python-client~=2.70.0', 'oauth2client~=4.1.3', 'pyopenssl~=22.1'],
    scripts=['scripts/gwbackupy'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
