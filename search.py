from flask import Flask, request, jsonify, render_template
import pickle
import os.path
from apiclient import errors
import email
import pytz
import sys
import io
import requests
import quopri
import zipfile
from bs4 import BeautifulSoup
from email.header import decode_header
import signal
import os
import webbrowser
import PySimpleGUI as sg
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import threading
import subprocess
import time
from googleapiclient.http import MediaInMemoryUpload
import base64

# autorizatie fara restrictii
SCOPES = ['https://mail.google.com/', 'https://www.googleapis.com/auth/drive']
app = Flask(__name__, template_folder='templates')


def shutdown_server():
    command = 'ps aux | grep "python3 search.py"'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0].decode()
    
    lines = output.split('\n')
    for line in lines:
        if "python3 search.py" in line:
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
   
search_string = sys.argv[1]

@app.route('/close-server', methods=['POST'])
def close_server():
    shutdown_server()
    return jsonify({'message': 'Server closed successfully'})

@app.route('/backup-message', methods=['POST'])
def backup_message():
    message_id = request.json['messageId']
    # Puteți folosi message_id pentru a identifica și salva emailul în Google Drive
    service = get_service()
    backup_link = save_email_to_drive(service, message_id)
    #print(f"Email backup requested for message ID: {message_id}")
    print(f"Email backup requested for message ID: {message_id}")

    # Răspundeți cu un mesaj de confirmare
    webbrowser.open(backup_link)
    return jsonify({'message': 'Backup request received'})

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
        print('Message sent successfully.')
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

@app.route('/')
def display_message():
    service = get_service()
    
    # Definiți ID-ul utilizatorului (adresa de e-mail)
    user_id = 'me'
    # Definiți șirul de căutare pentru mesaje
    #search_string = 'simplu'  # înlocuiți cu căutarea dorită

    # Apelați funcția search_message pentru a obține lista de ID-uri ale mesajelor căutate
    message_ids = search_message(service, user_id, search_string)
    if not message_ids:
        error_message = 'Nu există mesaje cu acest subiect. Încercați o altă opțiune!'
        display_error_message(error_message)
        os.kill(os.getpid(), signal.SIGINT)
        close_server()
        return

    message_content_list = []
    # Iterați prin fiecare ID de mesaj și obțineți conținutul mesajelor
    for msg_id in message_ids :
        message_content = get_message(service, user_id, msg_id)
        message_content['id'] = msg_id
        #print(message_content)
        message_content_list.append(message_content)

    #print(message_content_list)
    return render_template('messages.html', messages=message_content_list)

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

def search_message(service, user_id, search_string):
    try:
        list_ids = []  # lista cu id-uri
        search_ids = service.users().messages().list(userId=user_id, q=search_string).execute()
        try:
            ids = search_ids['messages']
        except KeyError:
            return []

        for msg_id in ids:  # iterez prin toate
            message = service.users().messages().get(userId=user_id, id=msg_id['id']).execute()
            subject = None
            headers = message['payload'].get('headers')
            if headers:
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                        break
            if subject is not None and search_string.lower() in subject.lower():
                list_ids.append(msg_id['id'])  # adaug în lista de ID-uri toate ID-urile

        return list_ids

    except errors.HttpError as error:
        print("Eroare: %s" % error)

def upload_attachment_to_anonfiles(attachment):
    filename = attachment['filename']
    data = attachment['data']
    
    # Create a file-like object from the attachment data
    file_data = io.BytesIO(data)
    
    # Make a POST request to anonfiles.com API for file upload
    response = requests.post('https://api.anonfiles.com/upload', files={'file': (filename, file_data)})
    
    if response.status_code == 200:
        # Parse the JSON response
        json_response = response.json()
        if json_response['status']:
            file_url = json_response['data']['file']['url']['short']
            return file_url
    
    return None

def get_message(service, user_id, msg_id):
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()
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

        html_content = None
        attachments = []
        attach_drive =  []

        for part in mime_msg.walk():
            if part.get_content_type() == 'text/html':
                html_content = part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif part.get_content_type().startswith('application/') or part.get_content_type().startswith('image/') or part.get_content_type().startswith('audio/') or part.get_content_type().startswith('video/'):
                attachment = {
                    'filename': part.get_filename(),
                    'content_type': part.get_content_type(),
                    'data': part.get_payload(decode=True)
                }
                saved_attach = upload_attachment_to_anonfiles(attachment)
                attach_drive.append(attachment)
                if saved_attach:
                    attachments.append({'filename': attachment['filename'], 'url': saved_attach})
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
            'content': html_content,
            'attachments': attachments,
            'attach_drive': attach_drive
        }

        return message_data

    except errors.HttpError as error:
        print('A apărut o eroare: %s') % error


#return va fi <googleapiclient.discovery.Resource at 0x284631d0790>
def get_service():
    creds = None
    # token.pickle salveaza accesul user-ului the user access, refresh_token si este generat automat 
    # cand e autorizata aplicatia de user
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Daca credentialele nu sunt valide
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

def save_email_to_drive(service, message_id):
    message_content = get_message(service, "me" ,message_id)
    html_content = message_content['content']
    sender = message_content['sender']
    subject = message_content['subject']
    date = message_content['date']
    recipient = message_content['recipient']
    attachments = message_content['attach_drive']
    #soup = BeautifulSoup(html_content, 'html.parser')
    #text = soup.get_text()
    content = f"Sender : {sender}<br>Receiver: {recipient}<br>Time&Date: {date}<br><br><br>{html_content}<br>"

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

    # file_name = f"{subject}.html"
    # file_metadata = {'name': file_name, 'mimeType': 'message/rfc822', 'parents': [folder_id]}
    # media_body = MediaInMemoryUpload(content, mimetype='text/html', chunksize=-1, resumable=True)
    # uploaded = backupService.files().create(body=file_metadata, media_body=media_body, fields="id").execute()

    zip_buffer = io.BytesIO()
    
    # Create a ZIP file object
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the HTML file to the ZIP
        zip_file.writestr(f"{subject}.html", content)
        
        # Add attachments to the ZIP
        for attachment in attachments:
            filename = attachment['filename']
            data = attachment['data']
            zip_file.writestr(filename, data)

    media_body = MediaInMemoryUpload(zip_buffer.getvalue(), mimetype='application/zip', chunksize=-1, resumable=True)
    file_metadata = {'name': f"{subject}.zip", 'parents': [folder_id]}
    uploaded = backupService.files().create(body=file_metadata, media_body=media_body, fields='id').execute()

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