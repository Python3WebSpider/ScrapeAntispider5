from redis import StrictRedis
from core.config import *
from pickle import dumps, loads
from core.request import MovieRequest


class RedisQueue():
    def __init__(self):
        """
        init redis connection
        """
        self.db = StrictRedis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

    def add(self, request):
        """
        add request to queue
        :param request: request
        :param fail_time: fail times
        :return: result
        """
        if isinstance(request, MovieRequest):
            return self.db.rpush(REDIS_KEY, dumps(request))
        return False

    def pop(self):
        """
        get next request
        :return: Request or None
        """
        if self.db.llen(REDIS_KEY):
            return loads(self.db.lpop(REDIS_KEY))
        return False

    def clear(self):
        self.db.delete(REDIS_KEY)

    def empty(self):
        return self.db.llen(REDIS_KEY) == 0
