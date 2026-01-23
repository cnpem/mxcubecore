import os
import time
import requests
import json


class BlueskyAPIInterface():

    _default_timeout = 5
    _execute_path = "queue/item/execute"
    _status_path = "status"
    _abort_path = "re/abort"
    _resume_path = "re/resume"
    _pause_path = "re/pause"

    def __init__(self):
        self._url = os.environ["HTTP_SERVER"]
        self._headers = {
            "Authorization": f"ApiKey {os.environ['AUTH_KEY']}"
        }
    
    def format_response(self, response):
        if response:
           response.raise_for_status()
           return json.loads(response.text)
        return {}
    
    def status(self):
        response = requests.get(
            self._url + self._status_path, 
            headers=self._headers, 
            timeout=self._default_timeout
        )
        
        return self.format_response(response)
 
    def monitor_manager_state(self, stop_state):
        while self.status()["manager_state"] != stop_state:
            time.sleep(0.1)
   
    def execute_plan(self, plan_items):
        response = requests.post(
            self._url+self._execute_path, 
            headers=self._headers, 
            json = {
                "user": "mnc-data",
                "item": plan_items
            }, 
            timeout=self._default_timeout
        )
        self.monitor_manager_state("running")
        self.monitor_manager_state("idle")

        return self.format_response(response)

    def pause(self):
        response = requests.post(
            self._url + self._pause_path, 
            headers=self._headers, 
            timeout=self._default_timeout)
        self.monitor_manager_state("paused")

        return self.format_response(response)
    
    def abort(self):
        if self.status()["manager_state"] != "paused":
            self.pause()
            self.monitor_manager_state("paused")

        status = requests.post(
            self._url + self._abort_path, 
            headers=self._headers, 
            timeout=self._default_timeout)
        self.monitor_manager_state("idle")

        return status

    def resume(self):
        if self.status()["manager_state"] == "paused":
            response = requests.post(
                self._url + self._resume_path, 
                headers=self._headers, 
                timeout=self._default_timeout)
            self.monitor_manager_state("running")

            return self.format_response(response)