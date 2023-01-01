import argparse
import threading
import logging
import sys
import traceback
from tzlocal import get_localzone
import pytz as pytz

import gwb.global_properties as global_properties

from gwb.gmail import Gmail
from gwb.storage.file_storage import FileStorage

lock = threading.Lock()


def parse_arguments():
    log_levels = {
        "finest": global_properties.log_finest,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    parser = argparse.ArgumentParser(description='Google Workspace Backup Tool ' + global_properties.version)
    parser.set_defaults(feature=True)
    parser.add_argument('--dry', default=False, help='Run in dry mode', action='store_true')
    parser.add_argument('--timezone', type=lambda s: pytz.timezone(s),
                        help='time zone', default=get_localzone())
    parser.add_argument('--log-level', type=str.lower,
                        help="Logging level: {keys}".format(keys=', '.join(log_levels.keys())),
                        default='info', choices=log_levels)
    parser.add_argument('--batch-size', type=int, help='Concurrent threads', default=5)
    parser.add_argument('--service-account-email', type=str, default=None,
                        help='Email of the service account (required for p12 keyfile)')
    parser.add_argument('--service-account-key-filepath', type=str,
                        help='Path to the service account key file', required=True)
    parser.add_argument('--workdir', type=str, help='Path to the workdir', required=False, default='./data')
    service_parser = parser.add_subparsers(dest='service')
    gmail_parser = service_parser.add_parser('gmail', help='GMail service commands')
    gmail_command_parser = gmail_parser.add_subparsers(dest='command')

    gmail_backup_parser = gmail_command_parser.add_parser('backup', help='Backup gmail')
    gmail_backup_parser.add_argument('--email', type=str, help='Email of the account', required=True)

    gmail_restore_parser = gmail_command_parser.add_parser('restore', help='Restore gmail')
    gmail_restore_parser.add_argument('--email', type=str, help='Email from which restore', required=True)
    gmail_restore_parser.add_argument('--to-email', type=str,
                                      help='Destination email account, if not specified, then --email is used')
    gmail_restore_parser.add_argument('--add-label', type=str, action='append',
                                      help='Add label to restored emails', default=None, dest='add_labels')
    gmail_restore_parser.add_argument('--restore-deleted', help='Restore deleted emails',
                                      default=False, action='store_true')
    gmail_restore_parser.add_argument('--filter-date-from', type=str, help='Filter date from', default=None)
    gmail_restore_parser.add_argument('--filter-date-to', type=str, help='Filter date to', default=None)

    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.addLevelName(global_properties.log_finest, 'FINEST')
    logging.basicConfig(
        # filename="logfile.log",
        stream=sys.stdout,
        filemode="w",
        format=Log_Format,
        level=log_levels[args.log_level])
    return args


def cli_startup():
    try:
        args = parse_arguments()
        storage = FileStorage(args.workdir + '/' + args.email)
        if args.service == 'gmail':
            gmail = Gmail(email=args.email,
                          service_account_email=args.service_account_email,
                          service_account_file_path=args.service_account_key_filepath,
                          batch_size=args.batch_size,
                          storage=storage,
                          dry_mode=args.dry)
            if args.command == 'backup':
                if gmail.backup():
                    exit(0)
                else:
                    exit(1)
            if args.command == 'restore':
                if args.add_labels is None:
                    args.add_labels = ['gwbackupy']
                if gmail.restore(to_email=args.to_email,
                                 timezone=args.timezone,
                                 filter_date_from=args.filter_date_from,
                                 filter_date_to=args.filter_date_to,
                                 restore_deleted=args.restore_deleted,
                                 add_labels=args.add_labels,
                                 ):
                    exit(0)
                else:
                    exit(1)
            else:
                raise Exception('Unknown command')
    except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())
        exit(1)


if __name__ == '__main__':
    cli_startup()
