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
import os
from os.path import dirname, abspath, join
import uuid
import random
import shutil
import asyncio

import crtauth
from drserv.async_server import AsyncServer

import pytest
import mock


ROOT = dirname(abspath(__file__))  # $PROJECT/test/
WORKSPACE = join(ROOT, 'output')
KEYS = join(ROOT, 'pubkeys')
PORT = random.randrange(40000, 42000)
INDEX_CMD = 'true'  # Equivalent to disabling


@pytest.fixture
def server(request):
    """
    Sets up a server in a temporary directory.

    """

    # Make a secret used for crtauth seed and for test directory creation
    secret = uuid.uuid4()

    # Set up a new directory we can use for storage and etc!
    dir = join(WORKSPACE, '{0}-{1}'.format(request.function.__name__, secret))
    os.makedirs(dir)

    auth_server = crtauth.server.AuthServer(
        secret,
        crtauth.key_provider.FileKeyProvider(KEYS),
        'localhost',
        lowest_supported_version=1
    )

    server = AsyncServer(PORT, dir, INDEX_CMD, auth_server)

    def fin():
        # Cleanup tasks that are run once the test finishes.
        shutil.rmtree(dir)

    request.addfinalizer(fin)
    return server


@pytest.fixture
def upload():
    request = mock.MagicMock()
    request.match_info = {
        'major': 'major',
        'minor': 'minor',
        'component': 'component',
        'package': 'package',
        'version': '3.1.14',
    }

    fake_file = mock.MagicMock()
    fake_file.file.read.return_value = b'file_contents'

    request.file_data = {
        'file': fake_file
    }

    @asyncio.coroutine
    def fake_post(*args, **kwargs):
        return request.file_data

    request.post = fake_post

    return request


def get_file_name(server, request):
    deb_target = join(
        server.base_dir,
        '{major}/pool/{minor}/{component}/'
        '{package}/{package}_{version}.deb'.format(
            **request.match_info
        )
    )

    return deb_target


def test_package_upload(server, upload, event_loop):
    routine = server.publish(upload)
    ret, code = event_loop.run_until_complete(routine)

    assert ret == 'OK'
    assert code == 202

    deb = get_file_name(server, upload)
    with open(deb, 'rb') as f:
        assert f.read() == b'file_contents'


def test_already_uploaded(server, upload, event_loop):
    """
    Test that an upload of an already existing file is
    refused and that the contents do not change.

    """

    deb_target = get_file_name(server, upload)
    os.makedirs(dirname(deb_target))

    content = b'something_else'
    with open(deb_target, 'wb') as f:
        f.write(content)

    routine = server.publish(upload)
    ret, code = event_loop.run_until_complete(routine)

    assert code == 400
    with open(deb_target, 'rb') as f:
        assert f.read() == content


@mock.patch('subprocess.check_call')
def test_index_command_called(check_call, server, upload, event_loop):
    routine = server.publish(upload)
    ret, code = event_loop.run_until_complete(routine)

    check_call.assert_called_once_with(INDEX_CMD)
