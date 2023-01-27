# gwbackupy: Google Workspace™ backup and restore solution.

[![0.2.0](https://img.shields.io/github/v/release/smartondev/gwbackupy)](https://github.com/smartondev/gwbackupy/releases)
[![0.2.0](https://img.shields.io/pypi/v/gwbackupy)](https://pypi.org/project/gwbackupy/)
[![BSD-3-Clause](https://img.shields.io/github/license/smartondev/gwbackupy)](LICENSE)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage Status](https://img.shields.io/coverallsCoverage/github/smartondev/gwbackupy)](https://coveralls.io/github/smartondev/gwbackupy?branch=main)
[![](https://img.shields.io/circleci/build/github/smartondev/gwbackupy?label=circleci)](https://app.circleci.com/pipelines/github/smartondev/gwbackupy?branch=main)
[![](https://img.shields.io/github/actions/workflow/status/smartondev/gwbackupy/publish-pypi.yml?label=publish-pypi)](https://github.com/smartondev/gwbackupy/actions/workflows/publish-pypi.yml)

## What is it?

Gwbackupy is an open source [Google Workspace™](https://workspace.google.com/) backup and restore solution, written in
python.

*Currently supported Gmail messages and labels only.*

## Why?

Due to [gmvault](https://github.com/gaubert/gmvault) limitations:

- is still abandoned (??)
- authentication method is not usable in Google Workspace wide
- designed only for gmail messages
- only supports IMAP protocol (slow and less security)

## Details

- Run from CLI or run directly from python code
- Authentication
    - OAUTH for free or paid plans (not recommended for paid plans)
    - Service account file (JSON or P12) for paid plans (can be configured to access all accounts in workspace.)
- Version controlled storage interface

  Allows to restore specific moments without using an external snapshot system (eg. zips, file system with snapshot).
  Not limited to file storage and is not limited to the use of a database server.
  *Currently, file system based storage is only available.*
- Dry mode (not write to local storage and not modify on server)
- API communication (no need for special IMAP and other settings): secure and fast
- Gmail backup
    - full backup (download all messages, labels)
    - full backup continuously (periodically rerunning)

      Scanning the full mailbox, but download only the new messages and mark the deleted messages.
    - Quick backup (sync the last N days)
- Gmail restore
    - restore deleted message in specified interval
    - full restore messages and labels to an empty mailbox (e.g. to other gmail account)

*Paid plans are the following: [here](https://workspace.google.com/intl/en/pricing.html). Google One or additional
storages are not considered as paid plans*

## Requirements

- `python3` and `pip`
- [Google Cloud](https://cloud.google.com/) account and own created access files.
  **This software does not contain access files, this is for security reasons.**

  A credit card is required during registration, but the use of Workspace APIs is free.

## Install

The easiest way for installing:

```bash
pip install gwbackupy
# and run...
gwbackupy ...
```

or

```bash
# clone this repository
# install requirements
pip install -r requirements.txt
# and run...
python3 -m gwbackupy ...
```

The project also has an official [Docker](https://www.docker.com/) image: 
[gwbackupy-docker](https://github.com/smartondev/gwbackupy-docker) - **under development**.
The docker image has scheduled backup runs and also supports managing multiple email accounts.

## Instructions

- [GCP OAUTH access setup](docs/oauth-setup.md)

  *For free Gmail plan or paid Google Workspace™ plans*
- [GCP Service Account Setup](docs/service-account-setup.md)

  *Only for paid Google Workspace™ plans*

## Usage

- [Parameters](docs/cli-parameters.md)

### Example usage Gmail

Backup run in CLI:

```bash
gwbackupy \
  --service-account-key-filepath <service-acount-json-key-file> \
  --batch-size 5 \
  gmail backup \
  --email <mailbox email address>
```

Restore run in CLI:

```bash
gwbackupy \
  --service-account-key-filepath <service-acount-json-key-file> \
  --batch-size 5 \
  gmail restore \
  --add-label "backup-restore-1231" \
  --add-label "more-restore-label" \
  --filter-date-from <date or datetime eg. "2023-01-01"> \
  --filter-date-to <date or datetime eg. "2023-02-02 03:00:00"> \
  --restore-deleted \
  --email <source backup mailbox email address> \
  --to-email <destination mailbox email address> # If you want to a different destination account
```

Backup run from python code:

```python
# WARNING: Calling directly from python code actively change in the current state of development.

from gwbackupy.gmail import Gmail
from gwbackupy.storage.file_storage import FileStorage
from gwbackupy.providers.gmail_service_provider import GmailServiceProvider
from gwbackupy.providers.gapi_gmail_service_wrapper import GapiGmailServiceWrapper

storage = FileStorage('./data/email@example.co')
service_provider = GmailServiceProvider(
    service_account_file_path='serviceacc.json',
    storage=storage,
)
service_wrapper = GapiGmailServiceWrapper()
gmail = Gmail(email='email@example.com',
              service_provider=service_provider,
              service_wrapper=service_wrapper,
              batch_size=3,
              storage=storage)
if gmail.backup():
    print('Yeah!')
else:
    print(':(')
```

## Security

See [SECURITY.md](SECURITY.md)

## Contributing

Welcome! I am happy that you want to make the project better.

Currently, there is no developed documentation for the process, in the meantime, please use issues and pull requests.

## Changelog

The changes are contained in [CHANGELOG.md](CHANGELOG.md).

## About

[Márton Somogyi](https://github.com/Kamarton)
