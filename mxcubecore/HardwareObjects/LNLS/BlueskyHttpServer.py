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
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
from mxcubecore.BaseHardwareObjects import HardwareObject


class BlueskyHttpServer(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        super().init()
        self.api = self.get_command_object("bluesky_http_server")
        self.api.username = "mnc-data"
    
    def execute_plan(self, plan_name, kwargs = {}):
        response = self.api.execute_plan(plan_name=plan_name, kwargs=kwargs)
        response_content = response.json()
        if response_content["success"]:
            try:
                self.api.monitor_manager_state("running")
                self.api.monitor_manager_state("idle")
            except TimeoutError:
                self.log.error("The Bluesky plan has timed out!")
        else:
            self.log.error(response_content["msg"])