# CLI parameters

| parameter                        | type     | description                                                                                       |
|----------------------------------|----------|---------------------------------------------------------------------------------------------------|
| `--log-level`                    | string   | Set logging level: `finest`, `debug`, `info` (default), `error`, `critical`                       |
| `--batch-size`                   | integer  | Concurrent threads count, default: 5                                                              |
| `--service-account-key-filepath` | filepath | JSON or P12 service account file path, see more [Service Account Setup](service-account-setup.md) |
| `--service-account-email`        | string   | Service account email address, required only for P12 type                                         |
| `--credentials-filepath`         | string   | OAUTH credentials json, see more [OAuth setup](oauth-setup.md)                                    |
| `--timzone`                      | string   | Timezone                                                                                          |
| `--workdir`                      | string   | Storage directory path, default: `./data`                                                         |
| `--dry`                          |          | Dry mode (not modify on server, not modify in local storage)                                      |
| `<service>`                      | service  | Service ID, eg. gmail                                                                             |

## `service` types

Currently only `gmail` is supported.

### `gmail` service

`... gmail <command> ...`

#### `backup` command

| parameter           | type   | description                                                                                                    |
|---------------------|--------|----------------------------------------------------------------------------------------------------------------|
| `--email`           | string | email account for backup (REQUIRED)                                                                            |
| `--quick-sync-days` | int    | Quick syncing mode. The value is number of retroactive days. (It does not delete messages from local storage.) |

#### `restore` command

| parameter            | type             | description                                                                                                   |
|----------------------|------------------|---------------------------------------------------------------------------------------------------------------|
| `--email`            | string           | email account for restore (REQUIRED)                                                                          |
| `--to-email`         | string           | email account to restore                                                                                      |
| `--restore-deleted`  |                  | Restore deleted message (The message has been marked as deleted in the local storage.)                        |
| `--restore-missing`  |                  | Restore missing message (The backup has not been run before, but the message no longer exists on the server.) |
| `--filter-date-from` | date or datetime | Filter message from date, e.g. "2023-01-01" or "2023-01-01 05:33:00"                                          |
| `--filter-date-to`   | date or datetime | Filter message from to, e.g. "2023-01-01" or "2023-01-01 05:33:00"                                            |

*deleted vs missing: The missing message meanłs that the message exists in the local storage,
but no longer on the server, but the backup has not been run yet, so its status has not been deleted.
The deleted message when the backup detected the deletion of the message
on the server and marked it in the local storage.*

#### `access-init` and `access-check` commands

| parameter            | type             | description                            |
|----------------------|------------------|----------------------------------------|
| `--email`            | string           | email account for check or init access |
