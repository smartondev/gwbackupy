# CLI parameters

| parameter                        | type     | description                                                                 |
|----------------------------------|----------|-----------------------------------------------------------------------------|
| `--log-level`                    | string   | Set logging level: `finest`, `debug`, `info` (default), `error`, `critical` |
| `--batch-size`                   | integer  | Concurrent threads count, default: 5                                        |
| `--service-account-key-filepath` | filepath | JSON or P12 service account file path                                       |
| `--service-account-email`        | string   | Service account email address, required only for P12 type                   |
| `--credentials-filepath`         | string   | OAUTH credentials json                                                      |
| `--timzone`                      | string   | Timezone                                                                    |
| `--workdir`                      | string   | Storage directory path, default: `./data`                                   |
| `--dry`                          |          | Dry mode (not modify on server, not modify in local storage)                |
| `<service>`                      | service  | Service ID, eg. gmail                                                       |

## `service` types

Currently only `gmail` is supported.

### `gmail` service

`backup` parameters

| parameter           | type   | description                                                                                                    |
|---------------------|--------|----------------------------------------------------------------------------------------------------------------|
| `--email`           | string | email account for backup (REQUIRED)                                                                            |
| `--quick-sync-days` | int    | Quick syncing mode. The value is number of retroactive days. (It does not delete messages from local storage.) |

`restore` parameters

...
