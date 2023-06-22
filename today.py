from flask import Flask, jsonify, request, render_template
import pickle
import os.path
from apiclient import errors
import email
from datetime import datetime
from googleapiclient.errors import HttpError
import pytz
import quopri
import signal
from email.header import decode_header
import os
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

SCOPES = ['https://mail.google.com/']
app = Flask(__name__, template_folder='templates')

@app.route('/close-server', methods=['POST'])
def close_server():
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify

@app.route('/')
def display_messages():
    service = get_service()
    
    # Data de azi
    today = datetime.now().strftime('%Y/%m/%d')

    # Obținerea mesajelor necitite din Inbox
    inbox_messages = get_unread_messages(service, 'INBOX', today)

    # Obținerea mesajelor necitite din Spam
    spam_messages = get_unread_messages(service, 'SPAM', today)

    # Transformarea mesajelor în formatul așteptat pentru afișare
    inbox_message_content = transform_messages(inbox_messages, service)
    spam_message_content = transform_messages(spam_messages, service)

    return render_template('today.html', inbox_messages=inbox_message_content, spam_messages=spam_message_content)

def get_service():
    creds = None
    # token.pickle salveaza accesul user-ului the user access, refresh_token si este generat automat 
    # cand e autorizata aplicatia de user
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Daca credentialele nu sunt valide, user-ul se logheaza
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Salvez credentiale pentru data viitoare
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_unread_messages(service, label_id, date):
    try:
        response = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            q=f'is:unread after:{date}'
        ).execute()

        messages = response.get('messages', [])

        return messages

    except HttpError as error:
        print(f'Error getting unread messages: {error}')
        return []

def transform_messages(messages, service):
    message_content_list = []

    for message in messages:
        msg_id = message['id']
        message_content = get_message_content(service, msg_id)

        if message_content is not None:
            message_content['id'] = msg_id
            message_content_list.append(message_content)

    return message_content_list


def get_message_content(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
        raw_data = message['raw']
        msg_str = base64.urlsafe_b64decode(raw_data).decode('utf-8')
        mime_msg = email.message_from_string(msg_str)

        sender = mime_msg['From']
        recipient = mime_msg['To']
        subject = decode_header(mime_msg['Subject'])[0][0]

        # Verificăm dacă mesajul este de tip "multipart"
        if mime_msg.is_multipart():
            parts = mime_msg.get_payload()
            html_content = None

            # Căutăm prima parte de tip HTML
            for part in parts:
                if part.get_content_type() == 'text/html':
                    html_content = part.get_payload(decode=True).decode('utf-8')
                    break

            if html_content:
                # Procesăm conținutul doar dacă există o parte HTML
                date = mime_msg.get('Date')
                timezone = pytz.timezone("Europe/Bucharest")
                parsed_date = email.utils.parsedate_to_datetime(date)
                datetime_obj = parsed_date.astimezone(timezone)
                formatted_date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

                message_data = {
                    'sender': sender,
                    'recipient': recipient,
                    'subject': quopri.decodestring(subject).decode('utf-8'),
                    'date': formatted_date,
                    'content': html_content
                }

                return message_data

        # Dacă mesajul nu este de tip "multipart" sau nu conține o parte HTML, returnăm None
        return None
    except errors.HttpError as error:
        print('An error occured: %s') % error


if __name__ == '__main__':
    app.run(debug=True)
