import imaplib
import email
import getpass
from datetime import date
from email.header import decode_header

# Assign variables for IMAP values
imap_host = 'mail-server.pawsey.org.au'
imap_user = 'kookaburramon'
imap_pass =  getpass.getpass()
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
for num in messages[0].split():
    tmp, data = imap.fetch(num, '(RFC822)')
    for response in data:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            dates = decode_header(msg["Date"])[0][0]
            if today_as_str in dates:
                print("True")
