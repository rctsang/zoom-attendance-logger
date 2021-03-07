from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Much of this code adapted/copied from the SimpleHTTPRequestHandler source code found here:
# https://github.com/python/cpython/blob/3.8/Lib/http/server.py

class RedirectHandler(SimpleHTTPRequestHandler):

	def __init__(self, *args, directory=None, **kwargs):
		super().__init__(*args, directory=None, **kwargs)
		self.close_connection = True

	def do_GET(self):
		"""Serve a GET request."""
		query = urlparse(self.path).query
		if query:
			qs = parse_qs(query)

			code = qs['code'][0]
			print(code)
			f = self.send_head()
		if f:
			try:
				self.copyfile(f, self.wfile)
			finally:
				f.close()