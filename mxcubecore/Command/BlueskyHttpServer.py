# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import json
import os
import time

import gevent
import requests

from mxcubecore.CommandContainer import CommandObject

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class BlueskyHttpServerCommand(CommandObject):
    """Interface for communicating with the Bluesky Http Server API."""

    _default_timeout = 5
    _status_path = "api/status"
    _execute_path = "api/queue/item/execute"

    def __init__(self, name, url, timeout=5, **kwargs):
        CommandObject.__init__(self, name, **kwargs)
        self.username = ""
        self._default_timeout = timeout
        self._url = f"{url}/" if url[-1] != "/" else url
        self._headers = {"Authorization": f"ApiKey {os.environ['AUTH_KEY']}"}

    def format_response(self, response):
        if response:
            response.raise_for_status()
            return json.loads(response.text)
        return response

    def status(self):
        response = requests.get(
            self._url + self._status_path,
            headers=self._headers,
            timeout=self._default_timeout,
        )
        return self.format_response(response)

    def monitor_manager_state(self, stop_state, timeout=86400):
        with gevent.Timeout(timeout, exception=TimeoutError):
            while self.status()["manager_state"] != stop_state:
                time.sleep(0.1)

    def execute_plan(self, plan_name, kwargs=None):
        if not kwargs:
            kwargs = {}
        return requests.post(
            self._url + self._execute_path,
            headers=self._headers,
            json={
                "user": self.username,
                "item": {"name": plan_name, "item_type": "plan", "kwargs": kwargs},
            },
            timeout=self._default_timeout,
        )

    def is_connected(self):
        http_server_status = self.status()
        re_environment_open = http_server_status["worker_environment_exists"]
        re_running = http_server_status["re_state"] is not None
        return re_environment_open and re_running
