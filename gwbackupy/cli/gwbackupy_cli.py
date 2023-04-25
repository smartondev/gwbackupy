import argparse
import logging
import os
import sys
import threading

import pytz as pytz
from tzlocal import get_localzone

import gwbackupy.global_properties as global_properties
from gwbackupy.cli.gmail_cli import add_cli_args_gmail
from gwbackupy.cli.peoples_cli import add_cli_args_peoples
from gwbackupy.filters.gmail_filter import GmailFilter
from gwbackupy.gmail import Gmail
from gwbackupy.helpers import parse_date
from gwbackupy.people import People
from gwbackupy.providers.gapi_gmail_service_wrapper import GapiGmailServiceWrapper
from gwbackupy.providers.gapi_people_service_wrapper import GapiPeopleServiceWrapper
from gwbackupy.providers.gapi_service_provider import AccessNotInitializedError
from gwbackupy.providers.gmail_service_provider import GmailServiceProvider
from gwbackupy.providers.people_service_provider import PeopleServiceProvider
from gwbackupy.storage.file_storage import FileStorage

lock = threading.Lock()


def parse_arguments(people_cli=None) -> argparse.Namespace:
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
        type=lambda s: pytz.timezone(s),
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
        "--service-account-email",
        type=str,
        default=None,
        help="Email of the service account (required for p12 keyfile)",
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
    add_cli_args_gmail(service_parser)
    add_cli_args_peoples(service_parser)

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


def cli_startup():
    try:
        args = parse_arguments()

        storage = FileStorage(os.path.join(args.workdir, args.email, args.service))
        storage_oauth_tokens = FileStorage(os.path.join(args.workdir, "oauth-tokens"))
        service_provider_args = {
            "credentials_file_path": args.credentials_filepath,
            "service_account_email": args.service_account_email,
            "service_account_file_path": args.service_account_key_filepath,
            "storage": storage_oauth_tokens,
            "oauth_bind_addr": args.oauth_bind_address,
            "oauth_port": args.oauth_port,
            "oauth_redirect_host": args.oauth_redirect_host,
        }

        if args.service == "peoples":
            service_provider = PeopleServiceProvider(**service_provider_args)
            service_wrapper = GapiPeopleServiceWrapper(
                service_provider=service_provider,
                dry_mode=args.dry,
            )

            service = People(
                email=args.email,
                service_wrapper=service_wrapper,
                # batch_size=args.batch_size,
                batch_size=1,
                storage=storage,
                dry_mode=args.dry,
            )
            if args.command == "access-init":
                service_wrapper.get_peoples(args.email)
            elif args.command == "access-check":
                try:
                    with service_provider.get_service(args.email, False) as s:
                        service_wrapper.get_peoples(args.email)
                except AccessNotInitializedError:
                    exit(1)
            elif args.command == "backup":
                if service.backup():
                    exit(0)
                else:
                    exit(1)
            else:
                exit(1)
        elif args.service == "gmail":
            service_provider = GmailServiceProvider(**service_provider_args)
            service_wrapper = GapiGmailServiceWrapper(
                service_provider=service_provider,
                dry_mode=args.dry,
            )
            service = Gmail(
                email=args.email,
                service_wrapper=service_wrapper,
                batch_size=args.batch_size,
                storage=storage,
                dry_mode=args.dry,
            )
            if args.command == "access-init":
                service_wrapper.get_labels(args.email)
            elif args.command == "access-check":
                try:
                    with service_provider.get_service(args.email, False) as s:
                        service_wrapper.get_labels(args.email)
                except AccessNotInitializedError:
                    exit(1)
            elif args.command == "backup":
                if service.backup(quick_sync_days=args.quick_sync_days):
                    exit(0)
                else:
                    exit(1)
            elif args.command == "restore":
                if args.add_labels is None:
                    args.add_labels = ["gwbackupy"]
                item_filter = GmailFilter()
                if args.restore_deleted:
                    item_filter.is_deleted()
                    logging.info("Filter options: deleted")
                if args.restore_missing:
                    item_filter.is_missing()
                    logging.info("Filter options: missing")
                if args.filter_date_from is not None:
                    dt = parse_date(args.filter_date_from, args.timezone)
                    item_filter.date_from(dt)
                    logging.info(f"Filter options: date from {dt}")
                if args.filter_date_to is not None:
                    dt = parse_date(args.filter_date_to, args.timezone)
                    item_filter.date_to(dt)
                    logging.info(f"Filter options: date to {dt}")
                if service.restore(
                    to_email=args.to_email,
                    item_filter=item_filter,
                    restore_deleted=args.restore_deleted,
                    restore_missing=args.restore_missing,
                    add_labels=args.add_labels,
                ):
                    exit(0)
                else:
                    exit(1)
            else:
                raise Exception("Unknown command")
    except KeyboardInterrupt:
        logging.warning("Process is interrupted")
        exit(1)
    except SystemExit as e:
        exit(e.code)
    except BaseException:
        logging.exception("CLI startup/run failed")
        exit(1)


if __name__ == "__main__":
    cli_startup()
