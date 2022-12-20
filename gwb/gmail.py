import concurrent.futures
import glob
import gzip
import json
import logging
import os
import threading
import time
import hashlib
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from gwb.helpers import get_path, decode_base64url, encode_base64url


class Gmail:
    """Gmail service"""

    def __init__(self, email, service_account_email, service_account_pkcs12_file_path, batch_size=10, labels=None,
                 from_date=None, to_date=None, add_labels=None):
        self.email = email
        self.service_account_email = service_account_email
        self.service_account_pkcs12_file_path = service_account_pkcs12_file_path
        if batch_size is None or batch_size < 1:
            batch_size = 10
        self.batch_size = batch_size
        self.__lock = threading.RLock()
        self.__services = {}
        self.__emails_locally = self.__get_all_messages_from_local()
        self.__error_count = 0
        if labels is None:
            labels = []
        self.labels = labels
        self.from_date = from_date
        self.to_date = to_date
        self.add_labels = add_labels
        self.__add_label_ids = []

    def __get_service(self, email=None):
        service = None
        if email is None:
            email = self.email
        with self.__lock:
            if email not in self.__services.keys():
                self.__services[email] = []
            if len(self.__services[email]) > 0:
                logging.debug('Reuse service')
                service = self.__services[email].pop()
        if service is None:
            logging.debug('Create new service')
            credentials = ServiceAccountCredentials.from_p12_keyfile(
                self.service_account_email,
                self.service_account_pkcs12_file_path,
                'notasecret',
                scopes=[
                    'https://mail.google.com/',
                ])

            credentials = credentials.create_delegated(email)
            service = build('gmail', 'v1', credentials=credentials)
        return service

    def __release_service(self, service, email=None):
        if service is None:
            return
        if email is None:
            email = self.email
        if email not in self.__services.keys():
            return
        logging.debug('Release service (email: ' + str(email) + ')')
        with self.__lock:
            self.__services[email].append(service)

    def __get_all_messages_from_local(self):
        path = get_path(self.email, type=['gmail', 'messages'])
        data = {}
        for file_path in glob.glob(path + '/**', recursive=True):
            file = os.path.basename(file_path)
            if '.' not in file:
                continue
            name = file.split('.')[0]
            if name not in data.keys():
                data[name] = {}
            # if file_path ends with '.json'
            if file_path.endswith('.json'):
                data[name]['metadata'] = file_path
            if file_path.endswith('.eml.gz') or file_path.endswith('.eml'):
                data[name]['message'] = file_path
            if file_path.endswith('.hash'):
                data[name]['message_hash'] = file_path
        # print(data)
        # exit(-1)
        return data

    def __get_message_from_server(self, message_id, message_format='raw', try_count=5, sleep=10):
        for i in range(try_count):
            service = self.__get_service()
            try:
                # message_id = message_id[:-1] + 'a'
                return service.users().messages().get(userId='me', id=message_id, format=message_format).execute()
            except HttpError as e:
                if e.status_code == 404:
                    # message not found
                    return None
                if i == try_count - 1:
                    # last try
                    raise e
                logging.error(e)
                logging.info("Wait " + str(sleep) + " seconds and retry..")
                time.sleep(sleep)
                continue
            except Exception:
                raise
            finally:
                self.__release_service(service)

    def __remove_from_emails_locally(self, message_id):
        with self.__lock:
            if message_id in self.__emails_locally.keys():
                del self.__emails_locally[message_id]

    def __store_message_file(self, message_id, raw_message, email_dates, path_type):
        md5 = hashlib.md5(raw_message).hexdigest()
        sha1 = hashlib.sha1(raw_message).hexdigest()
        hash_file = get_path(self.email, message_id, 'hash', email_dates, type=path_type)
        message_file = get_path(self.email, message_id, 'eml.gz', email_dates, type=path_type)
        try:
            with open(hash_file, 'w') as f:
                f.write(md5 + '\n' + sha1)
            with gzip.open(message_file, "wb", compresslevel=9) as binary_file:
                binary_file.write(raw_message)
        except Exception:
            if os.path.exists(hash_file):
                os.remove(hash_file)
            if os.path.exists(message_file):
                os.remove(message_file)
            raise

    def __required_message_download_format(self, message):
        message_format = 'raw'
        with self.__lock:
            local_data = self.__emails_locally.get(message['id'], None)
        if local_data is None:
            return message_format
        if local_data.get('message', None) is None:
            return message_format
        if os.path.getsize(local_data['message']) == 0:
            return message_format
        if local_data.get('message_hash', None) is None:
            return message_format
        if os.path.getsize(local_data['message_hash']) == 0:
            return message_format
        return 'minimal'

    def __backup_messages(self, message):
        try:
            path_type = ['gmail', 'messages']
            # TODO: option for force raw mode
            message_id = message['id']
            message_format = self.__required_message_download_format(message)

            data = self.__get_message_from_server(message_id, message_format)
            if data is None:
                # message not found
                return
            self.__remove_from_emails_locally(message_id)

            subject = data.get('snippet', '')
            if len(subject) > 64:
                subject = subject[:64] + '...'
            logging.debug('Subject: ' + subject)
            dates = datetime.fromtimestamp(int(data['internalDate']) / 1000, tz=timezone.utc) \
                .strftime('%Y-%m-%d').split('-', 1)

            path = get_path(self.email, subdir=dates, type=path_type)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            if 'raw' in data.keys():
                raw = decode_base64url(data.get('raw'))
                self.__store_message_file(message_id, raw, dates, path_type)
                data.pop('raw')
            json.dump(data, open(get_path(self.email, message_id, 'json', dates, type=path_type), 'w'))
        except Exception as e:
            with self.__lock:
                self.__error_count += 1
            logging.error(e)

    def __get_all_email_ids_from_server(self, email=None):
        if email is None:
            email = self.email
        service = self.__get_service(email)
        try:
            logging.info('Get all message ids from server...')
            messages = []
            count = 0
            next_page_token = None
            while True:
                # print('.', end='')
                data = service.users().messages() \
                    .list(userId='me', pageToken=next_page_token, maxResults=1000, q='label:all').execute()
                # print(data)
                # exit(-1)
                next_page_token = data.get('nextPageToken', None)
                count = count + len(data.get('messages', []))
                messages.extend(data.get('messages', []))
                if data.get('nextPageToken') is None:
                    break
            logging.info('Message(s) count: ' + str(count))
            # print(count)
            # print(messages)
            return messages
        finally:
            self.__release_service(service, email)

    def __get_labels_from_server(self, email=None):
        if email is None:
            email = self.email
        service = self.__get_service(email)
        try:
            labels = service.users().labels().list(userId='me').execute()
            return labels.get('labels', [])
        finally:
            self.__release_service(service, email)

    def __backup_labels(self):
        logging.info('Backing up labels...')
        labels = self.__get_labels_from_server()
        path_type_labels = ['gmail']
        path = get_path(self.email, type=path_type_labels)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        logging.info('Backing up labels...')
        json.dump(labels, open(get_path(self.email, 'labels.json', type=path_type_labels), 'w'))

    def backup(self):
        logging.info('Starting backup for ' + self.email)
        self.__error_count = 0

        self.__backup_labels()
        messages = self.__get_all_email_ids_from_server()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for index, message in enumerate(messages):
                # self.__backup_messages(message)
                executor.submit(self.__backup_messages, message)
        logging.info('Backup finished for ' + self.email)
        if self.__error_count > 0:
            logging.error('Backup failed with ' + str(self.__error_count) + ' errors')
            return False
        # no error founds
        # print(self.__emails_locally)
        _fileKeys = ['metadata', 'message', 'message_hash']
        for message_id in self.__emails_locally:
            logging.info('Deleting locally stored message ' + message_id)
            data = self.__emails_locally[message_id]
            for _fileKey in _fileKeys:
                if _fileKey in data.keys():
                    logging.info('Deleting locally stored file (' + data[_fileKey] + ')')
                    os.remove(data[_fileKey])
        return True

    @staticmethod
    def __is_user_label_id(label_id):
        return label_id.startswith('Label_')

    def __get_user_labels_only(self, labels):
        output = {}
        for label_id in labels:
            if self.__is_user_label_id(label_id):
                output[label_id] = labels[label_id]
        return output

    def __get_user_labels_from_local(self):
        labels = self.__load_labels_from_local()
        return self.__get_user_labels_only(labels)

    @staticmethod
    def __labels_index_by_key(labels, key='id'):
        output = {}
        for label in labels:
            if isinstance(label, dict):
                label_data = label
            else:
                label_data = labels[label]
            output[label_data[key]] = label_data
        return output

    def __load_labels_from_local(self):
        file = get_path(self.email, 'labels.json', type=['gmail'])
        if not os.path.exists(file):
            return {}
        json_data = json.load(open(file))
        return self.__labels_index_by_key(json_data, 'id')

    def __restore_label(self, label_name, email):
        service = None
        try:
            logging.info('Restoring label ' + label_name)
            service = self.__get_service(email)
            return service.users().labels().create(userId='me', body={'name': label_name}).execute()
        except HttpError as e:
            if e.status_code == 409:
                # already exists
                return None
            raise
        except Exception:
            raise
        finally:
            if service is not None:
                self.__release_service(service, email)

    def __restore_message(self, message_files, to_email, labels_from_server, labels_from_server_to_email, try_count=5,
                          sleep=10):
        for i in range(try_count):
            service = None
            try:
                logging.info('Restoring message ' + message_files['message'])
                meta = json.load(open(message_files['metadata']))
                label_ids = self.__add_label_ids.copy()
                # TODO: ignore CHAT label ID
                for label_id in meta['labelIds']:
                    if self.__is_user_label_id(label_id):
                        label = self.__get_label_from_index_label_id(label_id, labels_from_server,
                                                                     labels_from_server_to_email)
                        label_ids.append(label['id'])
                    else:
                        label_ids.append(label_id)
                with gzip.open(message_files['message'], "rb") as binary_file:
                    message_content = binary_file.read()
                # print(file_content)
                message_data = {
                    'labelIds': label_ids,
                    'raw': encode_base64url(message_content),
                }
                # print(meta['labelIds'])
                # print(message_data)
                service = self.__get_service(to_email)
                try:
                    result = service.users().messages().insert(userId='me', internalDateSource='dateHeader',
                                                               body=message_data).execute()
                    print(result)
                    return result
                except HttpError as e:
                    if i == try_count - 1:
                        # last try
                        raise e
                    logging.error(e)
                    logging.info("Wait " + str(sleep) + " seconds and retry..")
                    time.sleep(sleep)
                    continue
                except Exception:
                    raise

            except Exception as e:
                with self.__lock:
                    self.__error_count += 1
                logging.error(e)
            finally:
                if service is not None:
                    self.__release_service(service, to_email)

    def __get_label_from_index_label_id(self, label_id, labels_from, labels_to):
        labels_from = self.__labels_index_by_key(labels_from, 'id')
        labels_to = self.__labels_index_by_key(labels_to, 'name')
        if label_id not in labels_from.keys():
            raise Exception('Label ' + label_id + ' not found in labels_from')
        if labels_from[label_id]['name'] not in labels_to.keys():
            raise Exception('Label ' + labels_from[label_id]['name'] + ' not found in labels_to')
        return labels_to[labels_from[label_id]['name']]

    def restore(self, to_email=None):
        if to_email is None:
            to_email = self.email
        self.__error_count = 0

        print(to_email)
        labels_user = self.__get_user_labels_from_local()
        labels_from_server = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(), 'id'))
        print(self.__labels_index_by_key(labels_from_server, 'id'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for label_id in labels_user:
                executor.submit(self.__restore_label, labels_user[label_id]['name'], to_email)
                # label = self.__restore_label(labels_user[label_id]['name'], to_email)
                # print(label)
        if self.add_labels is not None and len(self.add_labels) > 0:
            for label_name in self.add_labels:
                print(label_name)
                self.__restore_label(label_name, to_email)

        labels_from_server_to_email = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(to_email), 'id'))
        labels_from_server_to_email_by_name = self.__labels_index_by_key(labels_from_server_to_email, 'name')
        if self.add_labels is not None and len(self.add_labels) > 0:
            self.__add_label_ids = []
            for label_name in self.add_labels:
                self.__add_label_ids.append(labels_from_server_to_email_by_name[label_name]['id'])

        messages = self.__get_all_messages_from_local()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for message_id in messages:
                executor.submit(self.__restore_message, messages[message_id], to_email, labels_from_server,
                                labels_from_server_to_email)
                # self.__restore_message(messages[message_id], to_email, labels_from_server, labels_from_server_to_email)
                # exit(-1)

        print('error_count: ' + str(self.__error_count))

        return False
