# gwbackupy: Google Workspace™ backup and restore solution.

![0.2.0](https://img.shields.io/github/v/release/smartondev/gwbackupy)
![0.2.0](https://img.shields.io/pypi/v/gwbackupy)
![BSD-3-Clause](https://img.shields.io/github/license/smartondev/gwbackupy)

## What is it?

[Google Workspace™](https://workspace.google.com/) backup and restore solution.
Gwbackupy is open source and written in python.

*Currently supported Gmail messages and labels only.*

## Why?

Due to [gmvault](https://github.com/gaubert/gmvault) limitations:

- is still abandoned (??)
- authentication method is not usable in Google Workspace wide
- designed only for gmail messages
- only supports IMAP protocol (slow and limited speed)

## Functionality

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

- `pip` or `python3`
- [Google Cloud](https://cloud.google.com/) account and own created access files.
  **This software does not contain access files, this is for security reasons.**

## Install

The easiest way for installing:

`pip install gwbackupy`

## Instructions

- [GCP Service Account Setup](docs/service-account-setup.md)

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
from gwb.gmail import Gmail
from gwb.storage.file_storage import FileStorage

storage = FileStorage('./data/email@example.co')
gmail = Gmail(email='email@example.com',
              service_account_file_path='xx.json',
              batch_size=3,
              storage=storage)
if gmail.backup():
    print('Yeah!')
else:
    print(':(')
```

## Contributing

...

## Changelog

The changes are contained in [CHANGELOG.md](CHANGELOG.md).

## About

[Márton Somogyi](https://github.com/Kamarton)
