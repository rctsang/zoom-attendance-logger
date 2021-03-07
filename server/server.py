# Code Credited to https://www.afternerd.com/blog/python-http-server/

import http.server
import socketserver
from handler import RedirectHandler



PORT = 8080
Handler = RedirectHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.handle_request()