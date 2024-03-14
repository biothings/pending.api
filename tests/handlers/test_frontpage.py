"""
Tests for mocking the FrontPageHandler front page rendering
"""
import tornado
from tornado.testing import AsyncHTTPTestCase

from biothings.web.launcher import TornadoAPILauncher

from web.handlers import EXTRA_HANDLERS


class TestFrontPageHandler(AsyncHTTPTestCase):

    def get_app(self):
        app_handlers = EXTRA_HANDLERS
        app_settings = {"static_path": "static"}

        configuration = "config_web"
        launcher = TornadoAPILauncher(configuration)
        launcher.handlers = app_handlers
        launcher.settings.update(app_settings)

        return launcher.get_app()

    def test_get_method(self):
        """
        Test the GET HTTP method handler for the front page

        Example Response Header Content
        [
            ('Connection', 'close')
            ('Content-Length', '39180'),
            ('Content-Type', 'text/html; charset=UTF-8'),
            ('Date', 'Tue, 12 Mar 2024 18:10:46 GMT'),
            ('Etag', '"59777fcfe54fb940e50d1c534e02ed8a8c59d52e"'),
            ('Server', 'TornadoServer/6.4'),
        ]
        Example Request Header Content
        [
            ('Accept-Encoding', 'gzip')
            ('Connection', 'close'),
            ('Host', '127.0.0.1:41599'),
            ('User-Agent', 'Tornado/6.4'),
        ]
        """
        frontpage_endpoint = r"/"
        http_method = "GET"

        response = self.fetch(frontpage_endpoint, method=http_method)
        self.assertEqual(response.code, 200)
        self.assertEqual(response._body, None)
        self.assertEqual(response.reason, "OK")
        self.assertFalse(response._error_is_response_code)

        response_headers = response.headers
        response_content_type = response_headers.get("Content-Type", None)
        response_content_length = response_headers.get("Content-Length", "-10")
        response_header_connection = response_headers.get("Connection", None)

        self.assertTrue(isinstance(response_headers, tornado.httputil.HTTPHeaders))
        self.assertEqual(response_content_type, "text/html; charset=UTF-8")
        self.assertTrue(int(response_content_length) > 0)
        self.assertEqual(response_header_connection, "close")

        get_request = response.request
        self.assertEqual(get_request.method, http_method)
        self.assertEqual(get_request.body, None)

        get_request_headers = get_request.headers
        request_connection = get_request_headers.get("Connection", None)
        response_user_agent = get_request_headers.get("User-Agent", None)
        request_user_agent = get_request_headers.get("User-Agent", None)

        self.assertEqual(request_connection, "close")
        self.assertTrue(response_user_agent)
        self.assertTrue(request_user_agent)
        self.assertEqual(response_user_agent, request_user_agent)

        response_time = response.start_time
        request_time = get_request.start_time
        self.assertTrue(response.request_time >= (response_time - request_time))

    def test_head_method(self):
        """
        Test the HEAD HTTP method handler for the front page
        """
        frontpage_endpoint = r"/"
        http_method = "HEAD"
        response = self.fetch(frontpage_endpoint, method=http_method)
        self.assertEqual(response.code, 200)
        self.assertEqual(response._body, None)
        self.assertEqual(response.reason, "OK")
        self.assertFalse(response._error_is_response_code)

        response_headers = response.headers
        response_content_type = response_headers.get("Content-Type", None)
        response_content_length = response_headers.get("Content-Length", "-10")
        response_header_connection = response_headers.get("Connection", None)

        self.assertTrue(isinstance(response_headers, tornado.httputil.HTTPHeaders))
        self.assertEqual(response_content_type, "text/html; charset=UTF-8")
        self.assertTrue(int(response_content_length) > 0)
        self.assertEqual(response_header_connection, "close")

        head_request = response.request
        self.assertEqual(head_request.method, http_method)
        self.assertEqual(head_request.body, None)

        head_request_headers = head_request.headers
        request_connection = head_request_headers.get("Connection", None)
        response_user_agent = head_request_headers.get("User-Agent", None)
        request_user_agent = head_request_headers.get("User-Agent", None)

        self.assertEqual(request_connection, "close")
        self.assertTrue(response_user_agent)
        self.assertTrue(request_user_agent)
        self.assertEqual(response_user_agent, request_user_agent)

        response_time = response.start_time
        request_time = head_request.start_time
        self.assertTrue(response.request_time >= (response_time - request_time))
