# coding=utf-8
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
import unittest
from drserv import server


class TestServer(unittest.TestCase):

    def test_parse_path(self):
        self.assertRaises(ValueError, server.DrservServer.parse_path, 42)
        self.assertRaises(ValueError, server.DrservServer.parse_path, u'€')

        major, minor, component, filename = server.DrservServer.parse_path(
            '/v1/publish/squeeze/stable/non-free/some-package_1.deb')
        self.assertEquals('squeeze', major)
        self.assertEquals('stable', minor)
        self.assertEquals('non-free', component)
        self.assertEquals('some-package_1.deb', filename)

        # control characters not allowed
        self.assertRaises(ValueError, server.DrservServer.parse_path, '\x00')

        # can't have .. parameters
        self.assertRaises(
            ValueError, server.DrservServer.parse_path,
            '/v1/publish/../../../some-package_1.deb',
        )

        # filename part needs to end in ".deb"
        self.assertRaises(
            ValueError, server.DrservServer.parse_path,
            '/v1/publish/squeeze/stable/non-free/foo'
        )

        # wrong number of path elements
        self.assertRaises(
            server.HttpException, server.DrservServer.parse_path,
            '/v1/publish/squeeze/stable/foo.deb'
        )