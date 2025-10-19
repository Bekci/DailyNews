import os
import email

from datetime import datetime
from dotenv import load_dotenv
from email.header import decode_header
from imaplib import IMAP4_SSL

SMTP_SERVER = "imap.gmail.com"
SMTP_PORT = 993
SENDER = "team@aposto.com"


class Explorer:

    def __init__(self, email_date=None, mail_key:str|None = None):
        
        load_dotenv()

        self._mail: IMAP4_SSL = IMAP4_SSL(SMTP_SERVER)
        self._password = mail_key
    
        if self._password is None:
           self._password: str | None = os.getenv('MAIL_PASS')

        if self._password is None:
            raise Exception("Couldn't find mail password environment variable")
        
        # Expected format for imap is 04-Oct-2025
        self.date = email_date if email_date is not None else datetime.today().strftime("%d-%b-%Y")

        self.email_address = os.environ["EMAIL_ADDRESS"]

    def retrive_email(self):
        self._mail.login(self.email_address, self._password)
        
        ids = self.retrive_mail_ids()
        
        if len(ids) > 1:
            print("There are multiple mails")
    
        email_text = self.fetch_content_by_id(ids[0])    
        self._mail.logout()
        return email_text


    def retrive_mail_ids(self) -> list[str]:

        self._mail.select("INBOX")
        search_criteria = f'(FROM "{SENDER}" ON {self.date})'
        typ, data = self._mail.search(None, search_criteria)

        if typ != "OK":
            self._mail.logout()
            raise RuntimeError(f"IMAP search failed: {typ}")

        ids = data[0].split()
        return ids
    

    def fetch_content_by_id(self, mail_id) -> str | None:
        result = ""
        typ, msg_data = self._mail.fetch(mail_id, "(RFC822)")
        
        if typ != "OK":
            return None
        
        raw = msg_data[0][1]

        msg = email.message_from_bytes(raw)
            
        subject, encoding = decode_header(msg.get("Subject") or "")[0]

        if isinstance(subject, bytes):
            try:
                subject = subject.decode(encoding or "utf-8", errors="replace")
            except Exception:
                subject = subject.decode("utf-8", errors="replace")
        
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))

                if ctype == "text/plain" and "attachment" not in disp:
                    payload = part.get_payload(decode=True)

                    if payload:
                        partial_content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                        result += partial_content
                                
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                result = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        
        return result