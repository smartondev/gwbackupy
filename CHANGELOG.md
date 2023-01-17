# CHANGELOG

## DEV



## 0.7.2

- Bug #47: fix python3.7 run failures

## 0.7.1

- Bug #42: fix cli with --help or no argv exception

## 0.7.0

- Enh #38: kill signals handling

## 0.6.0

- Enh: namespace refactoring `gwb` -> `gwbackupy`
- Enh #22: restore missing Gmail messages (`--restore-missing`)
- Bug: fixed date filters parsing

## 0.5.0

**Local file Storage BC break**

- Enh: temporary file based creation for minimize invalid files states
- Enh: Separation of service parameters for easy reusability in another python library or package
- Enh #13: Self managed versioned file storage with extendable custom storage interface (eg. for database)
- Enh #9: Dry mode
- Enh: Cleaner log messages
- Enh #12: OAUTH supports for free plans
- Enh #18: Quick syncing gmail backup mode

## 0.4.0

- Enh #8: service account json key file support
- Enh #6: Gmail restore by message ID

## 0.3.0

- Enh #1: write message.json only if it changes - gmail backup. (kamarton)
- Enh #2: --log-level parameter
- Enh #3: more logs, remove print() usage
- Fix: gmail restore CHAT labels (fix with skipping)
- Enh #4: memory optimization
- Enh: local files scanning speed optimization

## 0.2.1 - 2022-12-20

Software version fix and automatism

## 0.2.0 - 2012-12-20

`setup.py` fixes and additions

## 0.1.0 - 2022-12-20

Initial public release

