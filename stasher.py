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

_example = """examples:
    $ export STASH_URL=https://my-secret-stash.herokuapp.com
    $ export STASH_TOKEN=secret
    """
_example_args = """
    Provide URL and token via arg list:
    $ stash -u https://my-stash.herokuapp.com -t secret pull my-box
    """
_example_push = """
    Push files to the server (normally done from different machines):
    $ stash push my-stash-box-name ./my-file-1.txt
    $ stash push my-stash-box-name ./my-file-2.txt

    Rename file on server as "my-file-2"
    $ stash push my-stash-box-name ./my-file-2.txt my-file-2
    """
_example_pull = """
    Pull your files from the server:
    $ stash pull my-stash-box-name

    Note: files are normally kept for 60 minutes and then removed from server.

    Validate that stash has 2 files before pulling:
    $ stash pull my-stash-box-name -c 2

    Wait until stash has 2 files (max 10 minutes):
    $ stash pull my-stash-box-name -wc 2
    """

parser = argparse.ArgumentParser(
    description="Utility for stashing files temporarily on remote server.",
    formatter_class=argparse.RawTextHelpFormatter,
    epilog=_example + _example_push + _example_pull + _example_args)
parser.add_argument('-v', '--version', action='version',
                    version='%(prog)s ' + __version__)
parser.add_argument(
    '-d', '--debug', action='store_true', help="debug logging")
parser.add_argument(
    '-u', '--url', metavar="URL", default=os.environ.get('STASH_URL'),
    help="URL of remote server, default: env STASH_URL")
parser.add_argument(
    '-t', '--token', metavar="TOKEN", default=os.environ.get('STASH_TOKEN'),
    help="authorization token, default: env STASH_TOKEN")
subparsers = parser.add_subparsers(title='command')
subparser = subparsers.add_parser(
    'push', formatter_class=argparse.RawTextHelpFormatter,
    epilog=_example + _example_push)
subparser.set_defaults(command='push')
subparser.add_argument('box', metavar="BOX", help="name of stash box")
subparser.add_argument(
    'file_path', metavar="PATH",
    help="path to file to be stashed, required for stashing")
subparser.add_argument(
    'name', metavar="NAME", nargs='?',
    help="name of the file, default: file path's basename")
subparser = subparsers.add_parser(
    'pull', formatter_class=argparse.RawTextHelpFormatter,
    epilog=_example + _example_pull)
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
