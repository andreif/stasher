#!/usr/bin/env python
"""
Run `stash -h` for help.
"""
import argparse
import base64
import logging
import os
import re
import time

_log = logging.getLogger(__name__)

__version__ = '1.0.0'


class ArgParser(argparse.ArgumentParser):
    def format_help(self):
        return "version: {}\n{}".format(
            __version__, super(ArgParser, self).format_help())

parser = ArgParser(
    description="Utility for stashing files on remote server.")
parser.add_argument(
    '-v', '--version', action='store_true', help="show version")
parser.add_argument(
    '-d', '--debug', action='store_true', help="debug logging")
parser.add_argument(
    '-u', '--url', metavar="URL", default=os.environ.get('STASH_URL'),
    help="URL of remote server, default: env STASH_URL")
parser.add_argument(
    '-t', '--token', metavar="TOKEN", default=os.environ.get('STASH_TOKEN'),
    help="authorization token, default: env STASH_TOKEN")
subparsers = parser.add_subparsers(title='command')
subparser = subparsers.add_parser('push')
subparser.set_defaults(command='push')
subparser.add_argument('box', metavar="BOX", help="name of stash box")
subparser.add_argument(
    'file_path', metavar="PATH",
    help="path to file to be stashed, required for stashing")
subparser.add_argument(
    'name', metavar="NAME", nargs='?',
    help="name of the file, default: file path's basename")
subparser = subparsers.add_parser('pull')
subparser.set_defaults(command='pull')
subparser.add_argument('box', metavar="BOX", help="name of stash box")
subparser.add_argument(
    '-c', '--check-count', metavar="CNT",
    help="validate count of stashed files in the box")
subparser.add_argument(
    '-w', '--wait-for-count', action='store_true',
    help="wait until count matches given value")
subparser.add_argument(
    '-b', '--base-dir', metavar="DIR",
    help="base directory to pull stash to, default is current dir.")


class Stasher(object):
    def __init__(self, url, token=None):
        assert url
        self.url = url
        self.token = token

    def headers(self):
        if self.token:
            assert not re.search('[\'"$\s]', self.token), "Invalid token"
            return {'Authorization': 'Token ' + self.token}
        else:
            return {}

    def push(self, box, path, name=None):
        import requests
        assert box
        assert path
        if not name:
            name = os.path.basename(path)
        f = open(path, 'rb')
        try:
            r = requests.post(url=self.url + '/push',
                              data={'box': box, 'name': name},
                              headers=self.headers(),
                              files={'file': f})
        except requests.RequestException as e:
            _log.error(str(e))
        else:
            if r.ok:
                _log.info('OK.')
            else:
                _log.error('%s', r.text)

    def pull(self, box, check_count=None, base_dir=None,
             wait=False):
        import requests
        if wait and check_count:
            start_time = time.time()
            while True:
                if self.pull(box=box, check_count=check_count,
                             base_dir=base_dir):
                    return True
                _log.debug("Waiting 10s...")
                time.sleep(10)
                if time.time() - start_time > 60 * 10:
                    return False
        r = requests.get(url=self.url + '/pull',
                         params={'box': box, 'count': check_count},
                         headers=self.headers())
        if r.ok:
            for k, v in r.json().items():
                path = os.path.basename(k)
                if base_dir:
                    path = os.path.join(base_dir, path)
                path = os.path.abspath(path)
                _log.info(path)
                with open(path, 'wb+') as fp:
                    fp.write(base64.b64decode(v.encode()))
            return True
        else:
            _log.error('%s', r.text)
            return False


def main():
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if args.version:
        print(__version__)
        exit()

    if args.url:
        stasher = Stasher(url=args.url, token=args.token)
    else:
        parser.print_help()
        exit(1)

    if args.command == 'push':
        stasher.push(box=args.box, path=args.file_path, name=args.name)
    elif args.command == 'pull':
        stasher.pull(box=args.box, check_count=args.check_count,
                     base_dir=args.base_dir, wait=args.wait_for_count)
    else:
        parser.print_help()
        exit(1)

if __name__ == '__main__':
    main()
