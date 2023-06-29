from flask import Flask, jsonify, request, render_template
import pickle
import os.path
from apiclient import errors
import email
from datetime import datetime
from googleapiclient.errors import HttpError
import pytz
import PySimpleGUI as sg
import quopri
import time
from bs4 import BeautifulSoup
import webbrowser
from email.header import decode_header
import os
import subprocess
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

SCOPES = ['https://mail.google.com/', 'https://www.googleapis.com/auth/drive']
app = Flask(__name__, template_folder='templates')

def shutdown_server():
    command = 'ps aux | grep "python3 today.py"'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0].decode()
    
    lines = output.split('\n')
    for line in lines:
        if "python3 today.py" in line:
            fields = line.split()
            if len(fields) >= 2:
                pid = fields[1]
                # Close the server by killing the process with the obtained PID
                subprocess.call(['kill', '-9', pid])
                print(f"Closed server process with PID: {pid}")

    
def check_browser_status():
    while True:
        command = 'ps aux | grep -E "chrome.*http://127.0.0.1:5000" | grep -v "grep" | wc -l'
        
        num_processes = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = num_processes.stdout.strip()  # Remove leading/trailing whitespace
        num_processes = int(output)  # Convert to integer
        
        #print(num_processes)
        
        if num_processes < 1:
            shutdown_server()
            break
        time.sleep(1)

@app.route('/close-server', methods=['POST'])
def close_server():
    shutdown_server()
    return jsonify

@app.route('/backup-message', methods=['POST'])
def backup_message():
    message_id = request.json['messageId']
    # Realizați operațiunile de backup aici
    # Puteți folosi message_id pentru a identifica și salva emailul în Google Drive
    service = get_service()
    backup_link = save_email_to_drive(service, message_id)
    print(f"Email backup requested for message ID: {message_id}")

    # Răspundeți cu un mesaj de confirmare
    webbrowser.open(backup_link)
    return jsonify({'message': 'Backup request received'})

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
    threading.Thread(target=check_browser_status).start()
    return render_template('today.html', inbox_messages=inbox_message_content, spam_messages=spam_message_content)

@app.route('/send-message', methods=['POST'])
def send_message():
    subject = request.json.get('subject')
    message = request.json.get('message')
    to = request.json.get('senderEmail')
    service = get_service()
    email_message = create_message(subject, message, to)

    try:
        # Send the message
        sent_message = service.users().messages().send(userId='me', body=email_message).execute()
        display_error_message('Message sent successfully.')
        return sent_message
    except Exception as e:
        display_error_message('An error occurred while sending the message:' + str(e))
        return None
    
def create_message(subject, message, to):
    sender = 'me'
    recipient = to

    # Create the message body
    message_body = f"Subject: {subject}\nTo: {recipient}\n\n{message}"

    # Encode the message body
    encoded_message = base64.urlsafe_b64encode(message_body.encode('utf-8')).decode('utf-8')

    # Create the email message
    email_message = {
        'raw': encoded_message
    }

    return email_message

def display_error_message(message):
    # Funcție pentru afișarea ferestrei de eroare
    layout = [
        [sg.Text(message, font='Any 12')],
        [sg.Button('Închide', key='-CLOSE-')]
    ]

    window = sg.Window('Atentionare', layout)
    window.finalize() 
    window.bring_to_front() 
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == '-CLOSE-':
            break

    window.close()

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
        message = service.users().messages().get(userId="me", id=msg_id, format='raw').execute()
        raw_data = message['raw']
        msg_str = base64.urlsafe_b64decode(raw_data).decode('utf-8')
        mime_msg = email.message_from_string(msg_str)

        sender = mime_msg['From']
        recipient = mime_msg['To']
        subject = mime_msg['Subject']
        from_address, sender_name = email.utils.parseaddr(sender)
        to_address, receiver_name = email.utils.parseaddr(recipient)
        if subject is not None:
            subject = decode_header(subject)[0][0]
            subject = quopri.decodestring(subject).decode('utf-8', errors='replace')
        
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
                formatted_date = datetime_obj.strftime("%d-%m-%Y %H:%M:%S")

                message_data = {
                    'sender': sender_name,
                    'recipient': receiver_name,
                    'subject': subject,
                    'date': formatted_date,
                    'content': html_content
                }

                return message_data

        # Dacă mesajul nu este de tip "multipart" sau nu conține o parte HTML, returnăm None
        return None
    except errors.HttpError as error:
        print('An error occured: %s') % error


def save_email_to_drive(service, message_id):
    message_content = get_message_content(service, message_id)
    html_content = message_content['content']
    sender = message_content['sender']
    subject = message_content['subject']
    date = message_content['date']
    recipient = message_content['recipient']
    #soup = BeautifulSoup(html_content, 'html.parser')
    #text = soup.get_text()
    content = f"Sender : {sender}<br>Receiver: {recipient}<br>Time&Date: {date}<br><br><br>{html_content}"
    content = content.encode('utf-8')
    backupService = get_backup()
    
    response = backupService.files().list(
            q="name='BackUpFolder2023' and mimeType='application/vnd.google-apps.folder'",
            spaces='drive'
        ).execute()

    if not response['files']:
        file_metadata = {
            "name": "BackupFolder2023",
            "mimeType": "application/vnd.google-apps.folder"
        }

        file = backupService.files().create(body=file_metadata, fields="id").execute()
        folder_id = file.get("id")
    else:
        folder_id = response['files'][0]['id']

    file_name = f"{subject}.html"
    file_metadata = {'name': file_name, 'mimeType': 'message/rfc822', 'parents': [folder_id]}
    media_body = MediaInMemoryUpload(content, mimetype='text/html', chunksize=-1, resumable=True)
    uploaded = backupService.files().create(body=file_metadata, media_body=media_body, fields="id").execute()

    file_id = uploaded.get('id')
    file = backupService.files().get(fileId=file_id, fields='webViewLink').execute()
    backup_link = file.get('webViewLink')
    return backup_link

def get_backup():
    creds = None
    with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
        
    except HttpError as e:
        print("Error: " + str(e))

if __name__ == '__main__':
    browser_thread = threading.Thread(target=check_browser_status)
    browser_thread.start()
    app.run(debug=True)
