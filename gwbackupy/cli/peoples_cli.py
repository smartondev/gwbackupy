from gwbackupy.helpers import parse_date


def add_cli_args_peoples(service_parser):
    people_parser = service_parser.add_parser(
        "peoples", help="Peoples (contacts) service commands"
    )
    people_command_parser = people_parser.add_subparsers(dest="command")
    people_oauth_init_parser = people_command_parser.add_parser(
        "access-init", help="Access initialization e.g. OAuth authentication"
    )
    people_oauth_init_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    people_oauth_check_parser = people_command_parser.add_parser(
        "access-check", help="Check access e.g. OAuth tokens"
    )
    people_oauth_check_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    people_backup_parser = people_command_parser.add_parser(
        "backup", help="Backup people"
    )
    people_backup_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    people_backup_parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date (inclusive)",
        required=False,
    )
    people_backup_parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date (exclusive)",
        required=False,
    )
    people_restore_parser = people_command_parser.add_parser(
        "restore", help="Restore people"
    )
    people_restore_parser.add_argument(
        "--email", type=str, help="Email account", required=True
    )
    people_restore_parser.add_argument(
        "--restore-deleted",
        help="Restore deleted emails",
        default=False,
        action="store_true",
    )
    people_restore_parser.add_argument(
        "--restore-missing",
        help="Restore missing emails",
        default=False,
        action="store_true",
    )
