# Zoom Attendance Logger

This is a python app built to check zoom meeting attendees against a given roster of names. It is not public as of now and can only be installed in developer mode. You will need to set up several things to get started.

As of now, `main.py` implements OAuth with Zoom.
The functionality is untested, as my personal account is not a business or higher level plan, so no guarantees about bugs.

**NOTE: This requires a business or higher level plan to work with live meetings**

## Getting Started

You'll need some additional software to make this application work as well as familiarity with command line.

### Setting Up Project Directory and Environment

If you cloned this from git, you should be all set in terms of directory structure, but you will still need to do a few things.

**Reference**
```
root/
  +- private/
      +- creds.json
  +- requirements.txt
  +- main.py
```

1. Create a file in the `private/` directory named `creds.json` if not there. Leave it empty for now, you will add to it later.

1. Install Python 3.7.7 or higher.

1. Install Virtualenv with `$ pip install virtualenv`.

1. Create a virtual environment using `$ virtualenv venv` (where `venv` is the name of the virtual environment). A folder named `venv` will appear in your project directory

1. Activate the virtual environment using `$ source venv/bin/activate`.

1. Install dependencies from _requirements.txt_ using `$ pip install -r requirements.txt`

### Download ngrok

1. Download ngrok [here](https://ngrok.com/download) and follow installation instructions

1. (later) To open a tunnel to `localhost:8080`, which is the port used for the application, run: `$ ngrok http 8080` in the folder that you want to open. (this will be done when you run the app)

**NOTE: Every time you restart ngrok, you will need to update the redirect url on the app control panel in the zoom marketplace**

### Registering an App on Zoom Marketplace

1. Log in to Zoom Marketplace and navigate to _My Apps_ [here](https://marketplace.zoom.us/user/build).

1. In the upper right corner, go to _Develop -> Build App_

1. Choose _Create OAuth App_ and give the app a name.

1. When the app page opens, Under _App Credentials_ section, add the generated ngrok link to the _Redirect URL_ field. You will need to redo this every time you restart ngrok for this app. (link is generated when you run `$ ngrok http 8080`)

1. Add the credentials to the `private/creds.json`, replacing the values with your own. The json format is as follows:
```
{
	"client_id": "your id here",
	"client_secret": "your secret secret"
}
```

1. Fill out the mandatory fields in the _Information_ section: _short description_, _long description_, _Name_, _Email Address_

1. You can ignore the _Feature_ section.

1. Under _Scopes_, click _Add Scopes_ and select _View your meetings_ and _View and manage your meetings_. You will also need _dashboard_meetings:read:admin_ which only appears for business or higher level plans.

1. Skip the _Activation_ section. (this is handled in the python script)

### Running the Python Script

You must download ngrok and have the app registered before this section.
**Note:** Every time you restart ngrok, repeat step 4 from _Registering an App with Zoom Marketplace_

1. Open an new terminal window (you need 2) in the project directory and start ngrok using `ngrok http 8080` if you haven't already. Copy and paste the `https://xxxxxxxxxxxx.ngrok.io` for step 4 from above.

1. In the other terminal, in the project folder with `main.py`, run `$ python3 main.py`. This will start the script. 

1. Copy and paste the ngrok url when prompted by the script.

1. The script will start a server and open up your browser and ask you to log in to your zoom account. Log in using the same account under which you registered your Zoom App. 

1. Once the server redirects properly, you can close the tab and continue with the program.

## Subsequent Runs

Assuming you have restarted ngrok, (if not skip step 1)

1. Open an new terminal window (you need 2) in the project directory and start ngrok using `ngrok http 8080`. Copy and paste the url from ngrok `https://xxxxxxxxxxxx.ngrok.io` and follow step 4 from _Registering an App with Zoom Marketplace_.

1. In the other terminal, in the project folder with `main.py`, run `$ python3 main.py`. This will start the script. 

1. Copy and paste the ngrok url when prompted by the script.

1. If you've already registered the app, it should just connect. Continue with the program. when prompted, you may type `h` for options.

## Helpful Links

- [Zoom API](https://marketplace.zoom.us/docs/api-reference/zoom-api)
- [Zoom API: Rate Limits](https://marketplace.zoom.us/docs/api-reference/rate-limits)
- [Zoom API: Get a Meeting](https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meeting)
- [Zoom API: List Meeting Registrants](https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meetingregistrants)
- [Zoom API: Update Meeting Registrant Status](https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meetingregistrantstatus)




