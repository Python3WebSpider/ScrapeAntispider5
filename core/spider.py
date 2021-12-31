import re
import requests
from urllib.parse import urljoin
from requests import Session
from requests.exceptions import RequestException
from core.config import *
from core.db import RedisQueue
from core.request import MovieRequest
from pyquery import PyQuery as pq
from loguru import logger

BASE_URL = 'https://antispider5.scrape.center/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
}


class Spider():
    session = Session()
    queue = RedisQueue()

    @logger.catch
    def get_proxy(self):
        """
        get proxy from proxypool
        :return: proxy
        """
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            logger.debug(f'get proxy {response.text}')
            return response.text

    def start(self):
        """
        start request
        """
        self.session.headers.update(HEADERS)
        start_url = BASE_URL
        request = MovieRequest(
            url=start_url, callback=self.parse_index)
        # schedule first request
        self.queue.add(request)

    def parse_index(self, response):
        """
        parse index page
        :param response: response
        :return: new request
        """
        doc = pq(response.text)

        # request for detail
        items = doc('.item .name').items()
        for item in items:
            detail_url = urljoin(BASE_URL, item.attr('href'))
            request = MovieRequest(
                url=detail_url, callback=self.parse_detail)
            yield request

        # request for next page
        next_href = doc('.next').attr('href')
        if next_href:
            next_url = urljoin(BASE_URL, next_href)
            request = MovieRequest(
                url=next_url, callback=self.parse_index)
            yield request

    def parse_detail(self, response):
        """
        parse detail
        :param response: response of detail
        :return: data
        """
        doc = pq(response.text)
        cover = doc('img.cover').attr('src')
        name = doc('a > h2').text()
        categories = [item.text()
                      for item in doc('.categories button span').items()]
        published_at = doc('.info:contains(上映)').text()
        published_at = re.search('(\d{4}-\d{2}-\d{2})', published_at).group(1) \
            if published_at and re.search('\d{4}-\d{2}-\d{2}', published_at) else None
        drama = doc('.drama p').text()
        score = doc('p.score').text()
        score = float(score) if score else None
        yield {
            'cover': cover,
            'name': name,
            'categories': categories,
            'published_at': published_at,
            'drama': drama,
            'score': score
        }

    def request(self, request):
        """
        execute request
        :param request: weixin request
        :return: response
        """
        try:
            proxy = self.get_proxy()
            logger.debug(f'get proxy {proxy}')
            proxies = {
                'http': 'http://' + proxy,
                'https': 'https://' + proxy
            } if proxy else None
            return self.session.send(request.prepare(),
                                     timeout=request.timeout,
                                     proxies=proxies)
        except RequestException:
            logger.exception(f'requesting {request.url} failed')

    def error(self, request):
        """
        error handling
        :param request: request
        :return:
        """
        request.fail_time = request.fail_time + 1
        logger.debug(
            f'request of {request.url} failed {request.fail_time} times')
        if request.fail_time < MAX_FAILED_TIME:
            self.queue.add(request)

    def schedule(self):
        """
        schedule request
        :return:
        """
        while not self.queue.empty():
            request = self.queue.pop()
            callback = request.callback
            logger.debug(f'executing request {request.url}')
            response = self.request(request)
            logger.debug(f'response status {response} of {request.url}')
            if not response or not response.status_code in VALID_STATUSES:
                self.error(request)
                continue
            results = list(callback(response))
            if not results:
                self.error(request)
                continue
            for result in results:
                if isinstance(result, MovieRequest):
                    logger.debug(f'generated new request {result.url}')
                    self.queue.add(result)
                if isinstance(result, dict):
                    logger.debug(f'scraped new data {result}')

    def run(self):
        """
        run
        :return:
        """
        self.start()
        self.schedule()


if __name__ == '__main__':
    spider = Spider()
    spider.run()
