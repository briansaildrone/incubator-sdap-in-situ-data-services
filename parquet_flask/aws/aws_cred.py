# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from parquet_flask.utils.config import Config


class AwsCred:
    def __init__(self):
        self.__boto3_session = {
            'aws_access_key_id': Config().get_value('aws_access_key_id'),
            'aws_secret_access_key': Config().get_value('aws_secret_access_key'),
            'region_name': 'us-west-2',
        }
        aws_session_token = Config().get_value('aws_session_token')
        if aws_session_token is not None:
            self.__boto3_session['aws_session_token'] = aws_session_token

    @property
    def boto3_session(self):
        return self.__boto3_session

    @boto3_session.setter
    def boto3_session(self, val):
        """
        :param val:
        :return: None
        """
        self.__boto3_session = val
        return