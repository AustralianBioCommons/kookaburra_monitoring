from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver import *
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
from email import message_from_bytes
from email.policy import default

def check_email() -> Optional[str]:
    """
    This function checks the email folder and returns the
    most recent link to login (received within the last minute) or
    None if there is no new email

    :return: None or url
    """

    imap_host = 'mail-server.pawsey.org.au'
    imap_user = 'kookaburramon'
    imap_pass = open('external/password').readline().strip()
    imap = imaplib.IMAP4_SSL(imap_host)

    # Assign variable for today's date
    today_as_str = date.today().strftime("%-d %b %Y")
    print(today_as_str)

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
                return url

    else:
        return None

def test_login():
    """This function tests the login in the following steps:
    1. Open tower.services.biocommons.org.au
    2. Trigger login for email address <kookaburramon@pawsey.org.au>
    3. Check for email usingn <check_mail()>
    4. Login with the link provided by check_mail()
    """

    try:
        #Step 1
        browser = Firefox()
        browser.get(f"https://tower.services.biocommons.org.au")
        sleep(3)
        email_box = browser.find_element(By.ID,"email")
        email_box.send_keys("kookaburramon@pawsey.org.au")
        submit_button = browser.find_element(By.CSS_SELECTOR,"button.btn-signin")
        submit_button.click()
        success_div = browser.find_element(By.CSS_SELECTOR, "div.alert-success")

        #Step 2
        # Wait for the email to be received (TODO: Smarter wait?)
        sleep(4)
        # Check for the new email and save it as login_url
        login_url = check_email()
        print(login_url)
        # If we have a valid login URL, navigate to it using Selenium
        browser.get(login_url)
        # Step 3

    except Exception as e:
        #Todo: alert!
        # post this to slack

        stack_trace = traceback.format_exc()

        pass

# Trigger a login via a remote controlled Firefox
test_login()