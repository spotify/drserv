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
import yaml
import sys

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
    def __init__(self, port, base_dir, temp_dir):
        log.info('Starting server listening to port %d', port)
        self.base_dir = base_dir
        self.temp_dir = temp_dir
        self.wsgi_server = simple_server.make_server(
            '', port, self.handle_request)

    def serve_forever(self):
        self.wsgi_server.serve_forever()

    def handle_request(self, environ, start_response):
        try:
            path = urllib.unquote(environ['PATH_INFO'])
            if not path.startswith('/v1/publish'):
                raise HttpException('404 Not found')
            pi = self.parse_path(path)
            log.debug("Publishing %s to %s/%s/%s" %
                      (pi.file, pi.major_dist, pi.minor_dist, pi.component))

            temp_filename = self.store_post_data(
                environ['wsgi.input'], environ['CONTENT_LENGTH'], )

            start_response("202 Accepted", [('Content-type', 'text/plain')])
            return "OK\n",

        except HttpException, e:
            start_response(e.message,
                           [('Content-type', 'text/plain'),
                            ('Content-length', str(len(e.message) - 3))])
            return e.message[4:] + "\n",


    @staticmethod
    def store_post_data(length, to_read_from, temp_dir):
        """
        Reads length bytes of POST data from to_read_from and store in a
        unique temporary file in temp_dir
        """
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as f:
            to_read = max(length, BUFFER_SIZE)
            while length:
                buf = to_read_from.read(to_read)
                length -= len(buf)
                to_read = max(length, BUFFER_SIZE)
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



    @staticmethod
    def fail(status_string, start_response):
        start_response(status_string, [('Content-type', 'text/plain')])
        return ""


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
        config['listen_port'], config['target_basedir'], config['temp_dir']
    )
    server.serve_forever()


def read_config(file_name):
    try:
        with open(file_name) as f:
            return yaml.load(f)
    except IOError, e:
        fail("Failed to open config {}: {}".format(args.config, e.strerror))

def fail(message):
    print(message, file=sys.stderr)
    sys.exit(-1)


if __name__ == '__main__':
    main(sys.argv[1:])
