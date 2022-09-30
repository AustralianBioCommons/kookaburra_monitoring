from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver import *
import imaplib
import email
from datetime import date
from email.header import decode_header
from typing import Optional
import traceback
from time import sleep
import sys
from datetime import datetime

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
    today_as_str = date.today().strftime("%d %b %Y")

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
                current_time = datetime.now()
                # TODO - check if we need %d or %-d - see https://www.programiz.com/python-programming/datetime/strptime
                a = datetime.strptime(dates, '%a, %d %b %Y %H:%M:%S %z (%Z)')
                # TODO - compare a to current_time

                if today_as_str in dates:
                    recent_received_emails.append(data)

    print(recent_received_emails[-1])


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


    except Exception as e:
        #Todo: alert!
        # post this to slack

        stack_trace = traceback.format_exc()

        pass

#test_login()
check_email()