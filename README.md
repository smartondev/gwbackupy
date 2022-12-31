# gwbackupy: Google Workspace™ backup and restore solution.

![0.2.0](https://img.shields.io/github/v/release/smartondev/gwbackupy)
![0.2.0](https://img.shields.io/pypi/v/gwbackupy)
![](https://img.shields.io/github/license/smartondev/gwbackupy)

## What is it?

[Google Workspace™](https://workspace.google.com/) backup and restore solution. Gwbackupy is open source and written in
python.

Currently supported only the gmail messages.

## Why?

Due to [gmvault](https://github.com/gaubert/gmvault) limitations:

- authentication method is not usable in Google Workspace wide
- is still abandoned (?)
- only supports gmail messages

## Currently implemented functionality

- Run from CLI or run directly from python code
- Dry mode (not write to local storage and not modify on server)
- Google Workspace
    - authentication with p12/json service account file.

      *It can be applied to the entire workspace.*
- Gmail
    - full backup
      Download all messages
    - full backup continuously
      Scanning the full mailbox, but download only the new messages.
    - full restore to an empty mailbox to same or other mailbox
    - restore deleted message
    - *partially restore with pre-filtered files at the file system level*

Additional functionality under development.

## Functionality planned in the near future

- Google Workspace
    - list all workspace accounts email addresses
- Gmail
    - Support for standard gmail account authentication
    - Filtered restore

## Install

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
  --email <source backup mailbox email address> \
  --to-email <destination mailbox email address> # If you want to a different destination account
```

Backup run from python code:

```python
from gwb.gmail import Gmail
from gwb.storage.file_storage import FileStorage

gmail = Gmail(email='email@example.com',
              service_account_file_path='xx.json',
              batch_size=3,
              storage=FileStorage('data/email@example.co')
              )
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
