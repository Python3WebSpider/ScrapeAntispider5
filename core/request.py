from core.config import *
from requests import Request


class MovieRequest(Request):
    def __init__(self, url, callback, method='GET', headers=None, fail_time=0, timeout=TIMEOUT):
        Request.__init__(self, method, url, headers)
        self.callback = callback
        self.fail_time = fail_time
        self.timeout = timeout
