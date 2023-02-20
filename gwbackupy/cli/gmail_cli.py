def add_cli_args_gmail(service_parser):
    gmail_parser = service_parser.add_parser("gmail", help="GMail service commands")
    gmail_command_parser = gmail_parser.add_subparsers(dest="command")

    gmail_oauth_init_parser = gmail_command_parser.add_parser(
        "access-init", help="Access initialization e.g. OAuth authentication"
    )
    gmail_oauth_init_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    gmail_oauth_check_parser = gmail_command_parser.add_parser(
        "access-check", help="Check access e.g. OAuth tokens"
    )
    gmail_oauth_check_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    gmail_backup_parser = gmail_command_parser.add_parser("backup", help="Backup gmail")
    gmail_backup_parser.add_argument(
        "--email", type=str, help="Email of the account", required=True
    )
    gmail_backup_parser.add_argument(
        "--quick-sync-days",
        type=int,
        default=None,
        help="Quick sync number of days back. (It does not delete messages from local "
        "storage.)",
    )

    gmail_restore_parser = gmail_command_parser.add_parser(
        "restore", help="Restore gmail"
    )
    gmail_restore_parser.add_argument(
        "--email", type=str, help="Email from which restore", required=True
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
