import argparse
import threading
import logging
import sys
import traceback

import gwb.global_properties as global_properties

from gwb.gmail import Gmail

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
    parser.add_argument('--log-level', type=str.lower,
                        help="Logging level: {keys}".format(keys=', '.join(log_levels.keys())),
                        default='info', choices=log_levels)
    parser.add_argument('--batch-size', type=int, help='Email of the account', default=5)
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

    args = parser.parse_args()
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        # filename="logfile.log",
        stream=sys.stdout,
        filemode="w",
        format=Log_Format,
        level=log_levels[args.log_level])
    return args


def startup():
    try:
        args = parse_arguments()
        global_properties.working_directory = args.workdir
        if args.service == 'gmail':
            if args.command == 'backup':
                gmail = Gmail(email=args.email,
                              service_account_email=args.service_account_email,
                              service_account_file_path=args.service_account_key_filepath,
                              batch_size=args.batch_size)
                if gmail.backup():
                    exit(0)
                else:
                    exit(1)
            if args.command == 'restore':
                if args.add_labels is None:
                    args.add_labels = ['gwb']
                gmail = Gmail(email=args.email,
                              service_account_email=args.service_account_email,
                              service_account_file_path=args.service_account_key_filepath,
                              batch_size=args.batch_size,
                              add_labels=args.add_labels)
                if gmail.restore(to_email=args.to_email):
                    exit(0)
                else:
                    exit(1)
            else:
                raise Exception('Unknown command')
    except Exception as e:
        logging.error(e)
        logging.debug(traceback.format_exc())
        exit(1)


if __name__ == '__main__':
    startup()
