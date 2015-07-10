# Copyright (c) 2015 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging
import time
import collections
import subprocess
import yaml
import sys
import os

import asyncio
import blessings
import types
from aiohttp import web

from crtauth import server
from crtauth import key_provider


log = logging.getLogger(__name__)

PackageInfo = collections.namedtuple(
    'PackageInfo', 'major_dist minor_dist component file')

# size of the chunks to read from the socket to the HTTP client
BUFFER_SIZE = 8192


class AsyncServer:
    t = blessings.Terminal()

    def __init__(self, port, base_dir, index_command, auth_server):
        self.port = port
        self.base_dir = base_dir
        self.index_command = index_command
        self.auth_server = auth_server

        self.address = '127.0.0.1'

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # The regexp parsing takes care of input validation for the URIs
        uri = (
            '/v1/publish/'
            '{major:[a-z]+}/'
            '{minor:[a-z]+}/'
            '{component:[a-z-]+}/'
            r'{package:[^/_]+}_{version}.deb'
        )
        self.routes = (
            ('POST', uri, self.publish),
        )

    @asyncio.coroutine
    def setup_loop(self, loop):
        app = web.Application(loop=loop)

        for method, route, function in self.routes:
            app.router.add_route(
                method,
                route,
                self.endpoint(function, method, route),
            )

        log.info(
            "Server starting at {0}:{1}".format(self.address, self.port)
        )
        srv = yield from loop.create_server(
            app.make_handler(),
            self.address,
            self.port,
        )

        return srv

    def serve_forever(self):
        loop = asyncio.get_event_loop()
        setup_future = self.setup_loop(loop)
        loop.run_until_complete(setup_future)

        loop.run_forever()

    def endpoint(self, func, method, route):
        """
        Decorator method that takes care of calling and post processing
        responses.

        """

        def wrap(*args, **kwargs):
            uri = args[0].path
            log.debug(
                '{t.bold_black}>>{t.white} {method} {t.normal}{uri}'.format(
                    method=method,
                    uri=uri,
                    t=self.t
                )
            )

            body = func(*args, **kwargs)
            code = 200

            # POST requests will need to read from asyncio interfaces, and thus
            # their handler functions will need to `yield from` and return
            # generator objects. If this is the case, we need to yield from
            # them to get the actual body out of there.
            if isinstance(body, types.GeneratorType):  # pragma: nocover
                body = yield from body

            if isinstance(body, tuple):
                # If the result was a 2-tuple, use the second item as the
                # status code.
                body, code = body

            s = '{t.bold_black}<<{t.white} {method} {t.blue}{uri}{t.normal}: '
            if code >= 400:
                s += '{t.bold_red}'
            else:
                s += '{t.bold_green}'

            s += '{code}{t.normal}'
            log.info(
                s.format(
                    method=method,
                    uri=uri,
                    code=code,
                    t=self.t
                )
            )
            response = web.Response(
                body=body.encode(),
                status=code,
                headers={'content-type': 'text/plain'}
            )

            return response

        return asyncio.coroutine(wrap)

    def publish(self, request):
        match = request.match_info
        filename = '{package}_{version}.deb'.format(**match)

        log.debug(
            "Publishing {0} to {major}/{minor}/{component}".format(
                filename,
                **match
            )
        )

        # Construct the target directory
        target_dir = '{0}/{major}/pool/{minor}/{component}/{package}/'.format(
            self.base_dir,
            **match
        )
        os.makedirs(target_dir, exist_ok=True)

        # Grab the file data from the request. We do this before checking if
        # the path already exists since by nature of the HTTP protocol we need
        # to receive the entirety of the POST before we can send anything back.
        file_data = yield from request.post()

        target = os.path.join(target_dir, filename)
        if os.path.exists(target):
            return 'Target already exists: {0}'.format(target), 400

        with open(target, 'wb') as f:
            f.write(file_data['file'].file.read())

        # Run the indexer
        log.debug("Calling index command: %s" % self.index_command)
        subprocess.check_call(self.index_command)

        return "OK", 202


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s+0000 - %(name)s - %(levelname)s - %(message)s')
    logging.Formatter.converter = time.gmtime


def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        'drserv-server',
        description='The drserv service'
    )
    parser.add_argument(
        '--config', action='store',
        default='/etc/drserv.yml',
        help='the config file'
    )

    config = read_config(parser.parse_args().config)

    auth_server = server.AuthServer(
        config['crtauth_secret'],
        key_provider.FileKeyProvider(config['keys_dir']),
        config['service_name'],
        lowest_supported_version=1
    )

    serv = AsyncServer(
        config['listen_port'],
        config['target_basedir'],
        config['index_command'],
        auth_server
    )

    serv.serve_forever()


def read_config(file_name):
    try:
        with open(file_name) as f:
            return yaml.load(f)
    except IOError as e:
        fail('Failed to open config {}: {}'.format(file_name, e.strerror))


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(-1)


if __name__ == '__main__':
    main()
