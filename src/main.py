#!/usr/bin/env python3

import argparse
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_server(args):
    from server import server
    server.run_server()


def run_frontend(args):
    os.execvp('gunicorn', ['gunicorn', '--bind', f'0.0.0.0:{args.port}', 'src.frontend.frontend:app'])


def main():
    parser = argparse.ArgumentParser(description='TeleGPT')
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

    server_parser = subparsers.add_parser('server', help='Start server')
    server_parser.set_defaults(func=run_server)

    frontend_parser = subparsers.add_parser('frontend', help='Start frontend')
    frontend_parser.add_argument('port', type=int, help='Port number')
    frontend_parser.set_defaults(func=run_frontend)

    args = parser.parse_args()

    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
