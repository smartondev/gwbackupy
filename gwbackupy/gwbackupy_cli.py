import argparse
import logging
import multiprocessing
import sys
import threading

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tzlocal import get_localzone

import gwbackupy.global_properties as global_properties
from gwbackupy.filters.gmail_filter import GmailFilter
from gwbackupy.gmail import Gmail
from gwbackupy.helpers import parse_date
from gwbackupy.providers.gapi_gmail_service_wrapper import GapiGmailServiceWrapper
from gwbackupy.providers.gapi_service_provider import AccessNotInitializedError
from gwbackupy.providers.gmail_service_provider import GmailServiceProvider
from gwbackupy.storage.file_storage import FileStorage

lock = threading.Lock()


def _parse_timezone(s: str) -> ZoneInfo:
    try:
        return ZoneInfo(s)
    except (ZoneInfoNotFoundError, KeyError):
        raise argparse.ArgumentTypeError(f"unknown timezone: '{s}'")


def parse_arguments() -> argparse.Namespace:
    log_levels = {
        "finest": global_properties.log_finest,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    parser = argparse.ArgumentParser(
        description="Google Workspace Backup Tool " + global_properties.version,
        add_help=False,
    )
    parser.set_defaults(feature=True)
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "--dry", default=False, help="Run in dry mode", action="store_true"
    )
    parser.add_argument(
        "--timezone",
        type=_parse_timezone,
        help="time zone",
        default=get_localzone(),
    )
    parser.add_argument(
        "--log-level",
        type=str.lower,
        help="Logging level: {keys}".format(keys=", ".join(log_levels.keys())),
        default="info",
        choices=log_levels,
    )
    parser.add_argument("--batch-size", type=int, help="Concurrent threads", default=5)
    parser.add_argument(
        "--auto-batch",
        default=False,
        help="Automatically adjust batch size to maximize throughput without hitting rate limits",
        action="store_true",
    )
    parser.add_argument(
        "--service-account-email",
        type=str,
        default=None,
        help="Email of the service account",
    )
    parser.add_argument(
        "--service-account-key-filepath",
        type=str,
        help="Path to the service account key file",
        required=False,
    )
    parser.add_argument(
        "--credentials-filepath",
        type=str,
        help="Path to the credentials file",
        required=False,
    )
    parser.add_argument(
        "--workdir",
        type=str,
        help="Path to the workdir",
        required=False,
        default="./data",
    )
    parser.add_argument(
        "--oauth-bind-address",
        type=str,
        required=False,
        default="0.0.0.0",
        help="OAuth binding address, default is 0.0.0.0",
    )
    parser.add_argument(
        "--oauth-port",
        type=int,
        required=False,
        default=0,
        help="OAuth port, default is 0 (random)",
    )
    parser.add_argument(
        "--oauth-redirect-host",
        type=str,
        required=False,
        default="localhost",
        help="OAuth redirect host, default is localhost",
    )
    service_parser = parser.add_subparsers(dest="service")
    gmail_parser = service_parser.add_parser("gmail", help="GMail service commands")
    gmail_command_parser = gmail_parser.add_subparsers(dest="command")

    gmail_oauth_init_parser = gmail_command_parser.add_parser(
        "access-init", help="Access initialization e.g. OAuth authentication"
    )
    gmail_oauth_init_parser.add_argument(
        "--email", type=str, help="Email account", required=True, action="append"
    )
    gmail_oauth_check_parser = gmail_command_parser.add_parser(
        "access-check", help="Check access e.g. OAuth tokens"
    )
    gmail_oauth_check_parser.add_argument(
        "--email", type=str, help="Email account", required=True, action="append"
    )

    gmail_backup_parser = gmail_command_parser.add_parser("backup", help="Backup gmail")
    gmail_backup_parser.add_argument(
        "--email", type=str, help="Email of the account", required=True, action="append"
    )
    gmail_backup_parser.add_argument(
        "--quick-sync",
        default=False,
        help="Quick sync mode: fetches all message IDs but only downloads new messages "
        "and marks deleted ones. Skips re-downloading existing messages.",
        action="store_true",
    )
    gmail_backup_parser.add_argument(
        "--quick-sync-days",
        type=int,
        default=None,
        help="Quick sync number of days back. Without --quick-sync, it does not delete "
        "messages from local storage. When combined with --quick-sync, checks "
        "label/metadata changes for messages within this period (deletions are "
        "still marked).",
    )

    gmail_restore_parser = gmail_command_parser.add_parser(
        "restore", help="Restore gmail"
    )
    gmail_restore_parser.add_argument(
        "--email",
        type=str,
        help="Email from which restore",
        required=True,
        action="append",
    )
    gmail_restore_parser.add_argument(
        "--to-email",
        type=str,
        help="Destination email account, if not specified, then --email is used",
    )
    gmail_restore_parser.add_argument(
        "--add-label",
        type=str,
        action="append",
        help="Add label to restored emails",
        default=None,
        dest="add_labels",
    )
    gmail_restore_parser.add_argument(
        "--restore-deleted",
        help="Restore deleted emails",
        default=False,
        action="store_true",
    )
    gmail_restore_parser.add_argument(
        "--restore-missing",
        help="Restore missing emails",
        default=False,
        action="store_true",
    )
    gmail_restore_parser.add_argument(
        "--filter-date-from",
        type=str,
        help="Filter date from (inclusive, format: yyyy-mm-dd or yyyy-mm-dd hh:mm:ss)",
        default=None,
    )
    gmail_restore_parser.add_argument(
        "--filter-date-to",
        type=str,
        help="Filter date to (exclusive, format: yyyy-mm-dd or yyyy-mm-dd hh:mm:ss)",
        default=None,
    )
    if len(sys.argv) == 1 or "--help" in sys.argv:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args(args=sys.argv[1:])
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.addLevelName(global_properties.log_finest, "FINEST")
    logging.basicConfig(
        # filename="logfile.log",
        stream=sys.stdout,
        filemode="w",
        format=Log_Format,
        level=log_levels[args.log_level],
    )
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    logging.debug(f"CLI parameters: {sys.argv}")
    if (
        args.credentials_filepath is None and args.service_account_key_filepath is None
    ) or (
        args.credentials_filepath is not None
        and args.service_account_key_filepath is not None
    ):
        parser.error(
            "at least one of --credentials-filepath and --service-account-key-filepath required"
        )
    return args


def _run_single_email(args: argparse.Namespace, email: str):
    log_format = f"%(levelname)s %(asctime)s [{email}] - %(message)s"
    for handler in logging.root.handlers:
        handler.setFormatter(logging.Formatter(log_format))

    if args.service == "gmail":
        storage = FileStorage(args.workdir + "/" + email + "/gmail")
        storage_oauth_tokens = FileStorage(args.workdir + "/oauth-tokens")
        service_provider = GmailServiceProvider(
            credentials_file_path=args.credentials_filepath,
            service_account_email=args.service_account_email,
            service_account_file_path=args.service_account_key_filepath,
            storage=storage_oauth_tokens,
            oauth_bind_addr=args.oauth_bind_address,
            oauth_port=args.oauth_port,
            oauth_redirect_host=args.oauth_redirect_host,
        )
        service_wrapper = GapiGmailServiceWrapper(
            service_provider=service_provider,
            dry_mode=args.dry,
        )
        gmail = Gmail(
            email=email,
            service_wrapper=service_wrapper,
            batch_size=args.batch_size,
            storage=storage,
            dry_mode=args.dry,
            auto_batch=args.auto_batch,
        )
        if args.command == "access-init":
            service_wrapper.get_labels(email)
        elif args.command == "access-check":
            try:
                with service_provider.get_service(email, False) as s:
                    service_wrapper.get_labels(email)
            except AccessNotInitializedError:
                sys.exit(1)
        elif args.command == "backup":
            if gmail.backup(
                quick_sync=args.quick_sync, quick_sync_days=args.quick_sync_days
            ):
                sys.exit(0)
            else:
                sys.exit(1)
        elif args.command == "restore":
            add_labels = (
                args.add_labels if args.add_labels is not None else ["gwbackupy"]
            )
            item_filter = GmailFilter()
            if args.restore_deleted:
                item_filter.with_match_deleted()
                logging.info("Filter options: deleted")
            if args.restore_missing:
                item_filter.with_match_missing()
                logging.info("Filter options: missing")
            if args.filter_date_from is not None:
                dt = parse_date(args.filter_date_from, args.timezone)
                item_filter.with_date_from(dt)
                logging.info(f"Filter options: date from {dt}")
            if args.filter_date_to is not None:
                dt = parse_date(args.filter_date_to, args.timezone)
                item_filter.with_date_to(dt)
                logging.info(f"Filter options: date to {dt}")

            if (
                not item_filter.is_match_deleted()
                and not item_filter.is_match_missing()
            ):
                logging.warning("Tasks not found, see more e.g. --restore-deleted")
                sys.exit(0)

            if gmail.restore(
                to_email=args.to_email,
                item_filter=item_filter,
                add_labels=add_labels,
            ):
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            raise Exception("Unknown command")


def _ensure_access(args: argparse.Namespace, emails: list[str]):
    """Sequentially ensure all email accounts have valid OAuth tokens before parallel execution."""
    if args.credentials_filepath is None:
        return
    storage_oauth_tokens = FileStorage(args.workdir + "/oauth-tokens")
    service_provider = GmailServiceProvider(
        credentials_file_path=args.credentials_filepath,
        service_account_email=args.service_account_email,
        service_account_file_path=args.service_account_key_filepath,
        storage=storage_oauth_tokens,
        oauth_bind_addr=args.oauth_bind_address,
        oauth_port=args.oauth_port,
        oauth_redirect_host=args.oauth_redirect_host,
    )
    for email in emails:
        logging.info(f"Checking access for {email}...")
        with service_provider.get_service(email) as s:
            pass
        logging.info(f"Access OK for {email}")


def cli_startup():
    try:
        args = parse_arguments()
        emails = args.email

        if len(emails) != len(set(emails)):
            logging.error("--email contains duplicate accounts")
            sys.exit(1)

        if (
            args.command == "restore"
            and getattr(args, "to_email", None) is not None
            and len(emails) > 1
        ):
            logging.error("--to-email cannot be used with multiple --email accounts")
            sys.exit(1)

        if len(emails) == 1:
            _run_single_email(args, emails[0])
            return

        if args.command == "access-init":
            for email in emails:
                _run_single_email(args, email)
            return

        _ensure_access(args, emails)

        processes = {}
        for email in emails:
            p = multiprocessing.Process(
                target=_run_single_email,
                args=(args, email),
            )
            p.start()
            processes[email] = p

        for email, p in processes.items():
            p.join()

        failed = [email for email, p in processes.items() if p.exitcode != 0]
        if failed:
            logging.error(f"Failed accounts: {', '.join(failed)}")
            sys.exit(1)
        else:
            logging.info("All accounts completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        logging.warning("Process is interrupted")
        if "processes" in locals():
            for email, p in processes.items():
                p.join(timeout=30)
                if p.is_alive():
                    p.terminate()
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except BaseException:
        logging.exception("CLI startup/run failed")
        sys.exit(1)


if __name__ == "__main__":
    cli_startup()
