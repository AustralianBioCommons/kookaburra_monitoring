from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver import *
from selenium.webdriver.firefox.options import Options
from pyvirtualdisplay import Display
from seleniumwire import webdriver
import imaplib
import email
from datetime import date,datetime,timedelta
from urllib.parse import urlparse
from email.header import decode_header
from typing import Optional
import traceback
from time import sleep
import re
import sys
import json
from email import message_from_bytes
from email.policy import default
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def check_email() -> Optional[str]:
    """
    This function checks the email folder and returns the
    most recent link to login (received within the last minute) or
    None if there is no new email

    :return: None or url
    """

    imap_host = 'mail-server.pawsey.org.au'
    imap_user = 'kookaburramon'
    imap_pass = open('/home/ubuntu/kookaburra_monitoring/external/password').readline().strip()
    imap = imaplib.IMAP4_SSL(imap_host)

    # Assign variable for today's date
    today_as_str = date.today().strftime("%-d %b %Y")

    # Log in to server
    imap.login(imap_user, imap_pass)

    # Select email inbox
    imap.select('Inbox')

    # Put into a variable the list of messages with the header subject "Nextflow Tower Sign in"
    tmp, messages = imap.search(None, 'ALL', 'HEADER Subject "Nextflow Tower Sign in"')
    # Fetch the messages by its ID
    # Then get the date and time of all messages with the above header
    # Finally only print True if today's date matches any of the messages with the above header

    # Create an empty list to hold emails
    recent_received_emails = []
    for num in messages[0].split():
        tmp, data = imap.fetch(num, '(RFC822)')
        for response in data:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                dates = decode_header(msg["Date"])[0][0]
                email_received_time = datetime.strptime(dates, '%a, %d %b %Y %H:%M:%S %z (%Z)')
                current_time = datetime.now(email_received_time.tzinfo)
                # Calculate the earliest the email could have been received in order to be "within last 10 minutes"
                min_received_time = current_time - timedelta(minutes=10)
                # If the email received time occurs after that calculated time, it was received in the chosen period.
                if email_received_time > min_received_time:
                    # Email was in our chosen time period, so add it to the list
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            cdispo = str(part.get('Content-Disposition'))

                            # skip any text/plain (txt) attachments
                            if ctype == 'text/plain' and 'attachment' not in cdispo:
                                body = part.get_payload(decode=True)  # decode
                                break
                    else:
                        print("Something weird has happened with the email received")
                        return None
                    recent_received_emails.append(body)

    # Check if list is empty
    if recent_received_emails:
        # Turn the most recently received email into a plain multiline string
        email_to_parse = recent_received_emails[-1].decode('utf-8')
        # Parse the most recent email for a URL and return the URLs found in it
        urls = (re.findall(r'(https?://[^\s]+)', email_to_parse))
        # For each URL that we found...
        for url in urls:
            # Check the domain name...
            domain = urlparse(url).netloc
            # If it's Tower (therefore not likely a malicious link...)
            if domain == "tower.services.biocommons.org.au":
                print("Found login URL: " + url)
                return url
    else:
        return None

def send_slack_message(message, screenshot = None):
    try:
        print("Sending Slack message:")
        print(message)
        response = client.chat_postMessage(channel='#kookaburra-ops', text=message)
        assert response["message"]["text"] == message

        if screenshot:
            response = client.files_upload(channels=['#kookaburra-ops'],filename='screenshot.png',file=screenshot)
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

def test_login():
    """This function tests the login in the following steps:
    1. Open tower.services.biocommons.org.au
    2. Trigger login for email address <kookaburramon@pawsey.org.au>
    3. Check for email using <check_mail()>
    4. Login with the link provided by check_mail()
    """

    try:
        global client
        #Step 0
        # Login to Slack
        slack_token = open('/home/ubuntu/kookaburra_monitoring/external/slacktoken').readline().strip()
        client = WebClient(token=slack_token)
        #Step 1
        print("Opening web browser to main Tower page")
        display = Display(visible=0, size=(800, 600))
        display.start()
        driver = webdriver.Firefox()
        driver.get(f"https://tower.services.biocommons.org.au")
        sleep(3)
        print("Attempting to login")
        email_box = driver.find_element(By.TAG_NAME,"input")
        email_box.send_keys("kookaburramon@pawsey.org.au")
        submit_button = driver.find_element(By.CSS_SELECTOR,"button.btn-signin")
        submit_button.click()
        # Wait for the page to load
        sleep(2)
        success_div = driver.find_element(By.CSS_SELECTOR, "div.alert-success")

        #Step 2
        # Wait before attempting to check email, then check email every 4 seconds until we find our URL.
        sleep(4)
        login_found = False
        # Attempt to find the login URL up to times_to_try times, then send a Slack error message.
        # Create login attempt counter
        login_attempt = 0
        times_to_try = 10
        while not login_found:
            if login_attempt < times_to_try:
                # We haven't exhausted our attempts yet, try logging in
                # Check for the new email and save it as login_url
                login_url = check_email()
                if login_url:
                    # If we have a valid login URL, navigate to it using Selenium
                    login_found = True
                    print("Logging in by visiting the login URL")
                    driver.get(login_url)
                else:
                    print("Login URL not found yet, trying again...")
                    sleep(4)
                    login_attempt += 1
            else:
                print(f"We didn't find a login URL after {times_to_try} times, bailing.")
                sys.exit("ERR_NO_EMAIL")

        # Step 3
        # Check for status code
        driver.get(login_url)
        # Filter for status code for only the login_url page
        login_url_request = list(filter(lambda x: x.url == login_url,driver.requests))[0]
        status_code = login_url_request.response.status_code
        # Post the status code and message to Slack
        if status_code != 200:
            sleep(5)
            screen_png = driver.get_screenshot_as_png()
            send_slack_message(f"""The login returned non 200 status code of "{status_code}" """,screen_png)

        # Close browser and quit Firefox
        driver.close()
        driver.quit()

    except Exception as e:
        # Post stack_trace to Slack
        try:
            screen_png = driver.get_screenshot_as_png()
        except e:
            screen_png = None

        send_slack_message(f"Something's wrong, got stack trace {traceback.format_exc()}",screen_png)

    finally:
        display.stop()

# Trigger a login via a remote controlled Firefox
if __name__ == "__main__":
    test_login()
