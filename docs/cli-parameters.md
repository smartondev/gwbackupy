# CLI parameters

| parameter                        | type     | description                                                                 |
|----------------------------------|----------|-----------------------------------------------------------------------------|
| `--log-level`                    | string   | Set logging level: `finest`, `debug`, `info` (default), `error`, `critical` |
| `--batch-size`                   | integer  | Concurrent threads count, default: 5                                        |
| `--service-account-key-filepath` | filepath | JSON or P12 service account file path (REQUIRED)                            |
| `--service-account-email`        | string   | Service account email address, required only for P12 type                   |
| `--timzone`                      | string   | Timezone                                                                    |
| `--workdir`                      | string   | Storage directory path, default: `./data`                                   |
| `<service>`                      | service  | Service ID, eg. gmail                                                       |

## `service` types

Currently only `gmail` is supported.

### `gmail`

...
