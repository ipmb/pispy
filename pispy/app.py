#!/usr/bin/env python
from copy import copy
import json
import os
import queue
import logging
from urllib.parse import urlencode

import tornado.web
import tornado.ioloop
import tornado.httpclient
import tornado.options
from tornado import gen
import sockjs.tornado

from pispy import utils

QUEUE = queue.Queue()
CLIENTS = set()
logger = logging.getLogger(__file__)


class MainHandler(tornado.web.RequestHandler):
    """Serve the dashboard"""
    def get(self):
        self.render("index.html", db=settings['influxdb_readonly'])


class InfluxProxyHandler(tornado.web.RequestHandler):
    """Proxies data to InfluxDB and pushes it out to SockJS clients"""
    def check_auth(self):
        """Check that auth matches InfluxDB"""
        user = self.get_query_argument('u')
        password = self.get_query_argument('p')
        valid_user = user == settings['influxdb']['user']
        valid_password = password == settings['influxdb']['password']
        if not (valid_user and valid_password):
            self.set_status(401)
            self.finish()

    @gen.coroutine
    def post(self):
        """
        1. Checks username/password
        2. Adds timestamps to payload
        3. Pushes into realtime queue
        4. Proxies to InfluxDB
        """
        self.check_auth()
        body = self.request.body.decode('utf8')
        try:
            payload = json.loads(body)
            payload = utils.timestamp_data(payload)
        except (ValueError, KeyError):
            self.set_status(400, "Invalid payload format.")
            self.finish()
        QUEUE.put(payload)
        try:
            influx_resp = yield post_to_influx(payload)
        except tornado.httpclient.HTTPError as exp:
            influx_resp = exp
        self.set_status(influx_resp.code)
        self.finish()


class LiveFeedConnection(sockjs.tornado.SockJSConnection):
    """SockJS Realtime Feed. Also tracks connected clients"""
    def on_open(self, info):
        CLIENTS.add(self)
        update_connected_clients()

    def on_message(self, msg):
        # Messages sent from client are ignored
        pass

    def on_close(self):
        CLIENTS.remove(self)
        update_connected_clients()


def update_connected_clients():
    """Push to realtime queue and send to influx"""
    payload = utils.timestamp_data([{
        'name': 'connected_clients',
        'columns': ['count'],
        'points': [[len(CLIENTS)]],
    }])
    QUEUE.put(payload)
    post_to_influx(payload)


def check_queue():
    """
    Slurp new items out of the queue
    and send them to connected clients
    """
    while True:
        try:
            msg = QUEUE.get(block=False)
            LiveFeedRouter.broadcast(CLIENTS, msg)
        except queue.Empty:
            break




def post_to_influx(payload):
    params = {
        'u': settings['influxdb']['user'],
        'p': settings['influxdb']['password'],
        'time_precision': 'm', # milliseconds
    }
    url = '{url}/db/{name}/series?{params}'.format(
        params=urlencode(params), **settings['influxdb'])
    logger.debug('POST: %s', url)
    logger.debug('payload: %s', payload)
    request = tornado.httpclient.HTTPRequest(url, method='POST',
        body=json.dumps(payload), validate_cert=True)
    client = tornado.httpclient.AsyncHTTPClient()
    return client.fetch(request)

settings = {
    'debug': True,
    'static_path': utils.local_path('static'),
    'template_path': utils.local_path('templates'),
    'influxdb': utils.parse_db_conn(os.environ.get('INFLUXDB_URL')),
    'app_url': os.environ.get('APP_URL', 'http://localhost:8888')
}
influxdb_readonly_user, influxdb_readonly_password = os.environ.get(
    'INFLUXDB_READ_USER').split(':')
settings['influxdb_readonly'] = copy(settings['influxdb'])
settings['influxdb_readonly']['user'] = influxdb_readonly_user
settings['influxdb_readonly']['password'] = influxdb_readonly_password

LiveFeedRouter = sockjs.tornado.SockJSRouter(LiveFeedConnection, '/live-feed')
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/incoming", InfluxProxyHandler),
] +  LiveFeedRouter.urls, **settings)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(8888)
    tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOLoop')
    tornado.ioloop.PeriodicCallback(check_queue, 500).start()
    tornado.ioloop.IOLoop.instance().start()
