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

from __future__ import print_function
import argparse
import logging
import tempfile
import urllib
from wsgiref import simple_server
import time
import collections
import subprocess
import yaml
import sys
import os

log = logging.getLogger(__name__)

PackageInfo = collections.namedtuple(
    'PackageInfo', 'major_dist minor_dist component file')

# size of the chunks to read from the socket to the HTTP client
BUFFER_SIZE = 8192


class HttpException(Exception):
    """
    Used to fail an incoming http request with a non-200 code and message
    """
    pass


class DrservServer(object):
    """
    DrservServer instances listens to a port, responds to API calls
    and
    """
    def __init__(self, port, base_dir, temp_dir, index_command):
        log.info('Starting server listening to port %d', port)
        self.base_dir = base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        self.temp_dir = temp_dir
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        self.index_command = index_command

        self.wsgi_server = simple_server.make_server(
            '', port, self.handle_request)

    def serve_forever(self):
        self.wsgi_server.serve_forever()

    def handle_request(self, environ, start_response):
        try:
            path = urllib.unquote(environ['PATH_INFO'])
            if not path.startswith('/v1/publish'):
                raise HttpException('404 Not found')
            if environ['REQUEST_METHOD'] != 'POST':
                raise HttpException('405 Only POST allowed')
            pi = self.parse_path(path)
            log.debug("Publishing %s to %s/%s/%s" %
                      (pi.file, pi.major_dist, pi.minor_dist, pi.component))

            temp_filename = self.store_post_data(
                int(environ['CONTENT_LENGTH']), environ['wsgi.input'],
                self.temp_dir)
            log.debug("Received data in file %s" % temp_filename)

            # PyTypeChecker is buggy in 14.1.1
            # noinspection PyTypeChecker
            target_dir = self.build_target_dir(self.base_dir, pi)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            target = os.path.join(target_dir, pi.file)
            if os.path.exists(target):
                raise HttpException(
                    "400 refusing to overwrite existing file %s " % target)
            os.rename(temp_filename, target)
            log.debug("renamed %s into %s " % (temp_filename, target))
            log.debug("calling %s" % self.index_command)
            subprocess.check_call(self.index_command)
            log.debug("called %s" % self.index_command)

            start_response("202 Accepted", [('Content-type', 'text/plain')])
            return "OK\n",

        except HttpException, e:
            log.warning("Failed request: " + e.message)
            start_response(e.message,
                           [('Content-type', 'text/plain'),
                            ('Content-length', str(len(e.message) - 3))])
            return e.message[4:] + "\n",

    @staticmethod
    def build_target_dir(base_dir, package_info):
        file_parts = package_info.file.split("_")
        if len(file_parts) < 2 or not file_parts[0]:
            raise HttpException("400 Filename %s invalid, should be of format "
                                "NAME_VERSION.deb" % package_info.file)
        return os.path.join(
            base_dir, package_info.major_dist, 'pool', package_info.minor_dist,
            package_info.component, file_parts[0]
        )

    @staticmethod
    def store_post_data(length, to_read_from, temp_dir):
        """
        Reads length bytes of POST data from to_read_from and store in a
        unique temporary file in temp_dir
        """
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as f:
            to_read = min(length, BUFFER_SIZE)
            while length:
                buf = to_read_from.read(to_read)
                length -= len(buf)
                to_read = min(length, BUFFER_SIZE)
                f.write(buf)
        return f.name

    @staticmethod
    def parse_path(path):
        """
        Sanity checking and parsing of the path provided with the API call
        """
        if not isinstance(path, basestring):
            raise ValueError("wrong type %s of parameter path" % type(path))
        for i, c in enumerate(path):
            if ord(c) > 0x7f:
                raise ValueError("Char on pos %d is not ascii: '%s'" % (i, c))

        elements = [x for x in path.split("/") if x]
        if len(elements) != 6:
            raise HttpException(
                "400 path needs to be of form /v1/publish/{major.dist}"
                "/{minor.dist}/{component}/{filename.deb}")
        return PackageInfo(elements[2], elements[3], elements[4], elements[5])


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s+0000 - %(name)s - %(levelname)s - %(message)s')
    logging.Formatter.converter = time.gmtime


def main(arguments):
    setup_logging()
    parser = argparse.ArgumentParser(
        'drserv-server',
        description='The drserv service'
    )
    parser.add_argument('--config', action='store',
                        default='/etc/drserv/drserv.conf',
                        help='the config file')

    config = read_config(parser.parse_args(arguments).config)

    server = DrservServer(
        config['listen_port'], config['target_basedir'], config['temp_dir'],
        config['index_command']
    )
    server.serve_forever()


def read_config(file_name):
    try:
        with open(file_name) as f:
            return yaml.load(f)
    except IOError, e:
        fail("Failed to open config {}: {}".format(file_name, e.strerror))


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(-1)


if __name__ == '__main__':
    main(sys.argv[1:])
