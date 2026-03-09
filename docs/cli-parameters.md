# CLI parameters

| parameter                        | type     | description                                                                                                                                                                                  |
|----------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--log-level`                    | string   | Set logging level: `finest`, `debug`, `info` (default), `error`, `critical`                                                                                                                  |
| `--batch-size`                   | integer  | Concurrent threads count, default: 5                                                                                                                                                         |
| `--auto-batch`                   |          | Automatically adjust batch size to maximize throughput without hitting rate limits (starts from `--batch-size`, increases slowly, reduces on rate limit)                |
| `--service-account-key-filepath` | filepath | JSON service account file path, see more [Service Account Setup](service-account-setup.md)                                                                                                    |
| `--service-account-email`        | string   | Service account email address                                                                                                                                    |
| `--credentials-filepath`         | string   | OAUTH credentials json, see more [OAuth setup](oauth-setup.md)                                                                                                                               |
| `--timezone`                     | string   | Timezone                                                                                                                                                                                     |
| `--workdir`                      | string   | Storage directory path, default: `./data`                                                                                                                                                    |
| `--dry`                          |          | Dry mode (not modify on server, not modify in local storage)                                                                                                                                 |
| `--oauth-bind-address`           | string   | OAuth bind address, default is `0.0.0.0`. See more [google_auth_oauthlib.flow](https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html)               |
| `--oauth-port`                   | int      | OAuth port, default is `0` (random). See more [google_auth_oauthlib.flow](https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html)                    |
| `--oauth-redirect-host`          | string   | OAuth redirect host, default is `localhost`. See more [google_auth_oauthlib.flow](https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html) |
| `<service>`                      | service  | Service ID, eg. gmail                                                                                                                                                                        |

## `service` types

Currently only `gmail` is supported.

### `gmail` service

`... gmail <command> ...`

#### `backup` command

| parameter           | type   | description                                                                                                    |
|---------------------|--------|----------------------------------------------------------------------------------------------------------------|
| `--email`           | string | email account for backup (REQUIRED, can be specified multiple times for parallel multi-account backup)          |
| `--quick-sync`      |        | Quick sync mode: fetches all message IDs but only downloads new messages and marks deleted ones. Skips re-downloading existing messages. Can be combined with `--quick-sync-days`. |
| `--quick-sync-days` | int    | Quick syncing mode. The value is number of retroactive days. (It does not delete messages from local storage.) When combined with `--quick-sync`, checks label/metadata changes for messages within the specified period. |

**`--quick-sync` combined with `--quick-sync-days`**: When both flags are used together, the backup fetches the full message list from the server, downloads only new messages (raw format), marks deleted messages, and additionally checks label/metadata changes for existing messages within the last N days (minimal format). Messages older than N days are skipped entirely. This provides a good balance between speed and completeness.

| Flags | Server query | Download | Marks deleted |
|-------|-------------|----------|---------------|
| *(none)* | All messages | New (raw) + existing (minimal) | Yes |
| `--quick-sync-days N` | Last N days | New (raw) + existing (minimal) | No |
| `--quick-sync` | All messages | Only new (raw) | Yes |
| `--quick-sync --quick-sync-days N` | All messages | New (raw) + existing within N days (minimal) | Yes |

#### `restore` command

| parameter            | type             | description                                                                                                   |
|----------------------|------------------|---------------------------------------------------------------------------------------------------------------|
| `--email`            | string           | email account for restore (REQUIRED, can be specified multiple times for parallel multi-account restore)       |
| `--to-email`         | string           | destination email account; if not specified, `--email` is used as the destination (cannot be used with multiple `--email` accounts) |
| `--restore-deleted`  |                  | Restore deleted message (The message has been marked as deleted in the local storage.)                        |
| `--restore-missing`  |                  | Restore missing message (The backup has not been run before, but the message no longer exists on the server.) |
| `--filter-date-from` | date or datetime | Filter message from date, e.g. "2023-01-01" or "2023-01-01 05:33:00"                                          |
| `--filter-date-to`   | date or datetime | Filter message to date, e.g. "2023-01-01" or "2023-01-01 05:33:00"                                            |

*deleted vs missing: The missing message means that the message exists in the local storage,
but no longer on the server, but the backup has not been run yet, so its status has not been deleted.
The deleted message is when the backup detected the deletion of the message
on the server and marked it in the local storage.*

#### `access-init` and `access-check` commands

| parameter | type   | description                            |
|-----------|--------|----------------------------------------|
| `--email` | string | email account for check or init access (can be specified multiple times) |
