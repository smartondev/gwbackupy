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
    - Retention of deleted mails

      *Purpose: to be easy to use even without additional snapshot storage.*
    - Filtered restore
    - Live restore without duplicate mails.

      *Currently not check email exists or not, and restoring forcely.*

## Install

`pip install gwbackupy`

## Instructions

- [GCP Service Account Setup](docs/service-account-setup.md)

## Usage

### Gmail

Backup

```bash
gwbackupy \
  --service-account-key-filepath <service-acount-json-key-file> \
  --batch-size 5 \
  gmail backup \
  --email <mailbox email address>
```

Restore

```bash
gwbackupy \
  --service-account-key-filepath <service-acount-json-key-file> \
  --batch-size 5 \
  gmail restore \
  --add-label "backup-restore-1231" \
  --add-label "more-restore-label" \
  --email <source backup mailbox email address> \
  --to-email <destination mailbox email address>
```

## Contributing

...

## Changelog

The changes are contained in [CHANGELOG.md](CHANGELOG.md).

## About

[Márton Somogyi](https://github.com/Kamarton)
