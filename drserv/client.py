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


def main():
    parser = argparse.ArgumentParser(
        'drserv-client',
        description='Deploy a package onto a drserv service'
    )
    parser.add_argument('--url', action='store', required=True,
                        help='the base url of the drserv service')

    parser.add_argument('--key-file', action='store',
                        help='the rsa private key used to authenticate')
    parser.add_argument('--auth-user', action='store',
                        help='the username to authenticate as')

    parser.add_argument('--major-dist', action='store', required=True)
    parser.add_argument('--minor-dist', action='store', required=True)
    parser.add_argument('--component', action='store', required=True)

    parser.add_argument('package_filename')

    args = parser.parse_args()
    print(args)

if __name__ == '__main__':
    main()
