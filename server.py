import base64
import cgi
import http
import json
import logging
import os
import re
import traceback
import urllib.parse
import psycopg2

DEBUG = bool(os.environ.get('DEBUG'))
LIFETIME = int(os.environ.get('STASH_LIFETIME', 60))

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
_log = logging.getLogger(__name__)


class DB(object):
    def __init__(self, dsn):
        self.dsn = dsn
        self.connect()
        self.create()

    def connect(self):
        self.connection = psycopg2.connect(self.dsn)
        self.connection.set_session(autocommit=True)
        self.cursor = self.connection.cursor()

    def execute(self, query, *args):
        _log.debug("%s, %r", re.sub('\s+', ' ', query.strip()), args)
        if self.connection.closed:
            self.connect()
        self.cursor.execute(query, args)
        return self.cursor

    def create(self):
        self.execute('''
            CREATE TABLE IF NOT EXISTS stash (
                id SERIAL PRIMARY KEY,
                "box" VARCHAR(255) NOT NULL,
                "name" VARCHAR(255) NOT NULL,
                "file" BYTEA NOT NULL,
                "timestamp" TIMESTAMP NOT NULL,
                CONSTRAINT stash_u UNIQUE ("box", "name")
            );
        ''')

    def push(self, box, name, data):
        self.execute('''
            INSERT INTO stash
                ("box", "name", "file", "timestamp")
            VALUES
                (%s, %s, %s, current_timestamp)
        ''', box, name, psycopg2.Binary(data))

    def cleanup(self):
        self.execute('''
            DELETE FROM stash
            WHERE "timestamp" < current_timestamp - INTERVAL '%s' MINUTE
        ''', LIFETIME)

    def count(self, box):
        return list(self.execute(
            'SELECT COUNT(*) FROM stash WHERE "box"=%s', box))[0][0]

    def count_all(self):
        return list(self.execute(
            'SELECT COUNT(*) FROM stash'))[0][0]

    def pull(self, box):
        return self.execute(
            'SELECT "name", "file" FROM stash WHERE "box"=%s', box)


db = DB(dsn=os.environ['DATABASE_URL'])
_log.info("Stash count: %d", db.count_all())


def default(obj):
    if isinstance(obj, memoryview):
        return base64.b64encode(obj.tobytes()).decode()
    raise NotImplementedError((type(obj), repr(obj)))


def app(env, resp):
    def response(code, content=None, headers=None):
        headers = dict({'Server': 'nginx'}, **(headers or {}))
        if isinstance(content, str):
            content = [content.encode()]
        resp('%d %s' % (code, http.HTTPStatus(code).phrase),
             list(headers.items()))
        return content or []

    path = env.get('SCRIPT_NAME', '') + env.get('PATH_INFO', '')
    qs = urllib.parse.parse_qs(env.get('QUERY_STRING', ''))
    box = name = None
    try:
        if not DEBUG and env['wsgi.url_scheme'] != 'https':
            _log.error("Invalid scheme: %r", env['wsgi.url_scheme'])
            return response(405)

        token = os.environ.get('STASH_TOKEN')
        auth = env.get('HTTP_AUTHORIZATION')
        if token and auth != 'Token ' + token:
            _log.error("Invalid auth: %r", auth)
            return response(401, "Unauthorized")

        db.cleanup()

        if env['REQUEST_METHOD'] == 'POST':
            assert path == '/push' and env['wsgi.input']
            fs = cgi.FieldStorage(fp=env['wsgi.input'], environ=env,
                                  keep_blank_values=True)
            box = fs.getvalue('box')
            assert box
            name = (os.path.basename(fs.getvalue('name') or '') or
                    os.path.basename(fs['file'].filename or ''))
            data = fs['file'].file.read()
            assert name and data
            db.push(box=box, name=name, data=data)
            _log.info("Pushed %r %r", box, name)
            return response(200)
        else:
            count = qs.get('count')
            if count:
                count = int(count[0])
            assert path == '/pull'
            box = qs['box'][0]
            db_count = db.count(box=box)
            if count and db_count != count:
                _log.warning("Count %r != db count %r", count, db_count)
                return response(404, "Count mismatch: %s" % db_count)
            body = dict(db.pull(box=box))
            if body:
                _log.info("Pull stash %r %r", box, len(body))
                return response(200, json.dumps(body, default=default))
            else:
                _log.info("No stash found for %r", box)
                return response(404)

    except psycopg2.IntegrityError:
        _log.warning("Already stashed: %r", (box, name))
        return response(400, "Already stashed.")

    except (AssertionError, KeyError, IndexError) as e:
        _log.error(traceback.format_exc(), exc_info=1)
        return response(400, "Bad request.")


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from wsgiref.handlers import BaseHandler
    BaseHandler.error_body = b''
    try:
        host = os.environ.get('HOST') or '127.0.0.1'
        host, _, port = host.partition(':')
        port = int(port or os.environ.get('PORT') or 8000)
        _log.info('Starting server %s:%s...' % (host, port))
        make_server(host=host, port=port, app=app).serve_forever()
    except KeyboardInterrupt:
        _log.info('\nStopped.')
