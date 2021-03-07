import os
import json
import time
import requests
import http.server
import socketserver
import webbrowser
import multiprocessing
from multiprocessing import Value, Pipe
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from base64 import urlsafe_b64encode
import csv

### GLOBALS ###
# !!! Remember to change this here and in Zoom Marketplace if you restarted ngrok server
REDIRECT_URI = ""
AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
ACCESS_TOKEN_URL = "https://zoom.us/oauth/token"
parent_conn, child_conn = Pipe()
DIRECTORY = "server"
CREDS_PATH = "private/creds.json"


#############################################
############## OAUTH FUNCTIONS ##############
#############################################

# HTTP request handler class
class RedirectHandler(SimpleHTTPRequestHandler):

	def __init__(self, *args, directory=None, **kwargs):
		super().__init__(*args, directory=DIRECTORY, **kwargs)
		self.close_connection = True

	def do_GET(self):
		"""
		Serve a GET request.
		Meant to operate in a separate process. Passes extracted code to the main process
		"""
		query = urlparse(self.path).query
		if query:
			qs = parse_qs(query)
			global child_conn
			auth_code = qs['code'][0]
			print("auth code: " + auth_code)
			child_conn.send(auth_code)
			f = self.send_head()
		if f:
			try:
				self.copyfile(f, self.wfile)
			finally:
				f.close()

# semaphore to check if server up
server_running = Value('i', 0)
Handler = RedirectHandler

# run server method to be called in a separate process
def run_server(conn):
	PORT = 8080
	global Handler

	# start a new TCP server with HTTP request handler
	with socketserver.TCPServer(("", PORT), Handler) as httpd:
		print("serving at port", PORT)
		global server_running
		server_running.value = 1
		httpd.handle_request() 		# server handles one request, then terminates
		conn.close()				# terminate the end of the pipe passed to the process

def write_creds(creds):
	global CREDS_PATH
	with open(CREDS_PATH, 'w', encoding='utf-8') as creds_json:
		json.dump(creds, creds_json, ensure_ascii=False, indent=4)

# REFRESH ACCESS TOKENS
# Refreshes Oauth2 Access Tokens if Refresh Token is valid
def refresh_access_tokens(creds, tokens):

	# Construct the Refresh Token Request Header expected by the api
	val = creds['client_id'] + ':' + creds['client_secret']
	# api expects client id and secret Byte64 encoded
	val = "Basic" + urlsafe_b64encode(val.encode('ascii')).decode('utf-8') 
	headers = {'Authorization': val}

	global ACCESS_TOKEN_URL
	if 'refresh_token' in creds:
		# if the refresh token exists, sent a POST request to the Zoom access token url
		# with the headers and expecter query parameters
		response = requests.post(
			ACCESS_TOKEN_URL,
			headers=headers,
			data={
				'grant_type': 'refresh_token',
				'refresh_token': creds['refresh_token']
			}
		)

		# Error Checking - if the refresh failed, return false so new access tokens can be requested
		if int(response.status_code) != 200:
			print("Unable to Refresh Access Token!")
			creds.pop('refresh_token', None)
			write_creds(creds)
			return False

		# requests can turn the byte response into a dictionary
		jsonresponse = response.json()

		# write the new refresh token to memory for next time
		creds['refresh_token'] = jsonresponse['refresh_token']
		write_creds(creds)

		# overwrite the expired tokens with the new tokens
		for key in jsonresponse.keys():
			tokens[key] = jsonresponse[key]

		return tokens

	else: 
		return False

# GET ACCESS TOKENS
# Gets Oauth2 Access and Refresh Tokens if Authorized
# overwrites the token parameter dictionary with the new tokens
def get_access_tokens(creds, tokens):

	# if there is an available refresh token, attempt to refresh
	# if the refresh succeeds, return, otherwise continue to request new tokens
	if 'refresh_token' in creds:
		oauth_tokens = refresh_access_tokens(creds, tokens)
		if oauth_tokens:
			return oauth_tokens

	global ACCESS_TOKEN_URL
	global REDIRECT_URI
	# POST request for new access and refresh tokens using OAuth Code
	response = requests.post(
		ACCESS_TOKEN_URL,
		data={
			'grant_type': 'authorization_code',
			'code': creds['auth_code'],
			'client_id': creds['client_id'],
			'client_secret': creds['client_secret'],
			'redirect_uri': REDIRECT_URI
		}
	)
	
	# get dictionary of response
	oauth_tokens = response.json()

	# error checking, if there was a fail, remove the refresh token from memory if present and exit
	if int(response.status_code) != 200:
		print(oauth_tokens)
		print("Authentication failed. Exiting...")
		creds.pop('auth_code', None)
		write_creds(creds)
		exit()

	# write new refresh token to memory
	creds['refresh_token'] = oauth_tokens['refresh_token']
	write_creds(creds)

	# write or overwrite the deprecated tokens dictionary
	for key in oauth_tokens.keys():
		tokens[key] = oauth_tokens[key]

		return tokens

	return tokens

# GET AUTHORIZATION CODE
# Get authorization code (should only need to run this once)
# Writes authorization code to creds.json
def get_auth_code(creds):
	global REDIRECT_URI
	global AUTHORIZE_URL
	global ACCESS_TOKEN_URL

	CLIENT_ID = creds['client_id']
	CLIENT_SECRET = creds['client_secret']

	# construct query dictionary for the authorization url
	qdict = {'response_type': 'code', 
			 'client_id': CLIENT_ID,
			 'client_secret': CLIENT_SECRET,
			 'redirect_uri': REDIRECT_URI}
	# append url query to base authorization url
	install_url = AUTHORIZE_URL + '?' + urlencode(qdict)

	# start a separate process to run http server that will wait for authentication
	p = multiprocessing.Process(target=run_server, args=(child_conn,))
	p.start()

	# make sure not to make server requests before it's ready
	while not server_running.value:
		print("waiting for server to start...")
		time.sleep(0.01)

	# open the authentication page in a browser window
	# user will allow app access to his/her chat channels and messages
	webbrowser.open(install_url)

	# wait for the server's handler to send the authentication code to the main process via pipe
	auth_code = parent_conn.recv()

	# once server process is completed, join it with the main process
	p.join()

	# make sure the authorization code was received
	if not auth_code:
		print("Error: No Authorization Code Received!")
		return

	# write authoriation code to file
	creds['auth_code'] = auth_code
	write_creds(creds)

#############################################
############### API WRAPPERS ################
#############################################

def get_meeting(creds, tokens, meeting_id, occurance_id="", show_prev=True):
	GET_MEETING_URL = "https://api.zoom.us/v2/meetings/{meetingId}"

	# construct url query dictionary
	params = {}
	if occurance_id:
		params['occurance_id'] = occurance_id
	if show_prev:
		params['show_previous_occurances'] = "true"
	

	# HTTP Request header with valid access token 
	headers = {'authorization': "Bearer " + tokens['access_token']}

	# GET request for meeting id
	response = requests.get(
		GET_MEETING_URL.format(meetingId=meeting_id),
		headers=headers,
		params=params
	)

	# rate limit considerations
	time.sleep(1)
	if (response.status_code != 200):
		print("Get Meeting Failed! Response:")
		print(response.content, '\n')
		return {}
	return response.json()



def list_meeting_participants(creds, tokens, meeting_id, mtype="live", page_size=100, next_page_token="", include_fields=""):
	LIST_MEETING_PARTICIPANTS_URL = "https://api.zoom.us/v2/metrics/meetings/{meetingId}/participants"

	# construct url query dictionary
	params = {}
	if mtype:
		params['type'] = mtype
	if page_size > 30:
		params['page_size'] = page_size
	if next_page_token:
		params['next_page_token'] = next_page_token
	if include_fields:
		params['include_fields'] = include_fields

	# HTTP Request header with valid access token 
	headers = {'authorization': "Bearer " + tokens['access_token']}

	# GET request for meeting participants
	response = requests.get(
		LIST_MEETING_PARTICIPANTS_URL.format(meetingId=meeting_id),
		headers=headers,
		params=params
	)

	# rate limit considerations
	time.sleep(1)
	if (response.status_code != 200):
		print("Get Participants Failed! Response:")
		print(response.content, '\n')
		return {}
	return response.json()


#############################################
############### FUNCTIONALITY ###############
#############################################

# Returns a dictionary of the new attendees in participants
def compare_against_file(path, participants):
	with open(path, 'r') as file:
		reader = csv.DictReader(file)
		roster = {row['id'] : row for row in reader}

	curr_attendees = set(participants.keys())
	past_attendees = set(roster.keys())
	new_attendees = curr_attendees.difference(past_attendees)
	non_returnees = past_attendees.difference(curr_attendees)
	returnees = curr_attendees.intersection(past_attendees)

	print("Returnees:")
	for a in returnees:
		print('\t', roster[a]['user_name'])
	print("Non-Returnees:")
	for a in non_returnees:
		print('\t', roster[a]['user_name'])
	print("New Attendees:")
	for a in new_attendees:
		print('\t', participants[a]['user_name'])

	return {pid : participants[a] for pid in new_attendees}

def add_new_participants_to_file(path, new_participants):
	if os.path.exists(path):
		with open(path, 'r') as file:
			reader = csv.DictReader(file)
			roster = {row['id'] : row for row in reader}
	else:
		roster = {}

	roster.update(new_participants)

	print("Writing new participants to file...")
	fieldnames = roster.values()[0].keys()
	with open(path, 'w') as file:
		writer = csv.DictWriter(file, fieldnames=fieldnames)
		writer.writeheader()
		for p in roster.values():
			writer.writerow(p)

	print("New participants added:")
	for p in new_participants.values():
		print('\t', p['user_name'])



def main():
	global CREDS_PATH
	global REDIRECT_URI

	if not REDIRECT_URI:
		REDIRECT_URI = input("redirect uri: ")
	
	# load client credentials from file
	with open(CREDS_PATH, 'r') as creds_json:
		creds = json.load(creds_json)

	# check if we have an authorization code
	if 'auth_code' not in creds.keys():
		get_auth_code(creds);

	print("Authorized! Code:", creds['auth_code'])

	# initialize an empty access tokens dictionary
	oauth_tokens = {}

	print("Aquiring Access Tokens...")
	get_access_tokens(creds, oauth_tokens)
	print("Aquired Access Tokens!")
	print("Access Token:", oauth_tokens['access_token'])

	details = {}
	participants = {}
	new_participants = {}

	while (1):
		print("What Would you like to do? (type \'h\' for options)")
		cmd = input(": ")

		if cmd == 'h':
			print("details <meeting id>			- gets details for the meeting id")
			print("participants <meeting id>	- gets participants for the meeting id")
			print("allparticipants <meeting id>	- (not implemented")
			print("compare <file path>			- compares participants against roster .csv file (requires participants first)")
			print("save <file path> 			- saves new participants to .csv file (requires compare). creates a new file if it doesn't exist")


		if "details" in cmd:
			mid = int(cmd.lstrip("details "))
			details = get_meeting(creds, oauth_tokens, mid)
			print(json.dumps(details, indent=2), '\n')

		if "participants" in cmd:
			mid = int(cmd.lstrip("details "))
			participants = list_meeting_participants(creds, oauth_tokens, mid)
			if participants['page_count'] > 1:
				print("Note: More than 100 participants, please use \'allparticipants\' to list all.")
			for p in participants:
				print('\t', participants[p]['user_name'], ': ID', p)

		if "compare" in cmd:
			path = cmd.lstrip("compare ")
			new_participants = compare_against_file(path, participants)

		if "save" in cmd:
			path = cmd.lstrip("save ")
			add_new_participants_to_file(path, new_participants)


main()