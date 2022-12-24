import concurrent.futures
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
import gwb.global_properties as global_properties

from gwb.helpers import get_path, decode_base64url, encode_base64url, str_trim


class StorageDescriptor:
    """Local files descriptor"""

    def __init__(self):
        self.metadata = None
        self.message = None
        self.message_hash = None


class Gmail:
    """Gmail service"""

    def __init__(self, email, service_account_email, service_account_file_path, batch_size=10, labels=None,
                 from_date=None, to_date=None, add_labels=None):
        self.email = email
        self.service_account_email = service_account_email
        self.service_account_file_path = service_account_file_path
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
            extension = self.service_account_file_path.split('.')[-1].lower()
            credentials = None
            scopes = [
                'https://mail.google.com/',
            ]
            if extension == 'p12':
                if self.service_account_email is None or self.service_account_email.strip() == '':
                    raise Exception("Service account email is required for p12 keyfile")
                credentials = ServiceAccountCredentials.from_p12_keyfile(
                    self.service_account_email,
                    self.service_account_file_path,
                    'notasecret',
                    scopes=scopes)
            elif extension == 'json':
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    self.service_account_file_path,
                    scopes
                )
                pass

            if credentials is None:
                raise Exception(f'Not supported service account file extension')

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
        logging.info("Scanning messages from local")
        path = get_path(self.email, type=['gmail', 'messages'])
        data = {}
        for path, _, filenames in os.walk(path):
            for file in filenames:
                file_path = os.path.join(path, file)
                if '.' not in file:
                    continue
                name = file.split('.')[0]
                if name not in data.keys():
                    logging.log(global_properties.log_finest, f"{name} message found")
                    data[name] = StorageDescriptor()
                if file_path.endswith('.json'):
                    data[name].metadata = file_path
                if file_path.endswith('.eml.gz') or file_path.endswith('.eml'):
                    data[name].message = file_path
                if file_path.endswith('.hash'):
                    data[name].message_hash = file_path
        # print(data)
        # exit(-1)
        logging.info(f'Local messages scanned: {len(data)}')
        return data

    def __get_message_from_server(self, message_id, message_format='raw', try_count=5, sleep=10):
        logging.debug(f'{message_id} download from server with format: {message_format}')
        for i in range(try_count):
            service = self.__get_service()
            try:
                # message_id = message_id[:-1] + 'a'
                result = service.users().messages().get(userId='me', id=message_id, format=message_format).execute()
                logging.debug(f"{message_id} successfully downloaded")
                return result
            except HttpError as e:
                if e.status_code == 404:
                    logging.warning(f"{message_id} message not found")
                    # message not found
                    return None
                if i == try_count - 1:
                    # last try
                    logging.error(f"{message_id} message download failed")
                    raise e
                logging.error(e)
                logging.info(f"{message_id} Wait {sleep} seconds and retry..")
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
        logging.debug("Store message {id}".format(id=message_id))
        md5 = hashlib.md5(raw_message).hexdigest()
        sha1 = hashlib.sha1(raw_message).hexdigest()
        hash_file = get_path(self.email, message_id, 'hash', email_dates, type=path_type)
        message_file = get_path(self.email, message_id, 'eml.gz', email_dates, type=path_type)
        try:
            with gzip.open(message_file, "wb", compresslevel=9) as binary_file:
                binary_file.write(raw_message)
            with open(hash_file, 'w') as f:
                f.write(md5 + '\n' + sha1)
        except Exception as e:
            logging.error(e)
            if os.path.exists(hash_file):
                os.remove(hash_file)
            if os.path.exists(message_file):
                os.remove(message_file)
            raise

    def __required_message_download_format(self, message):
        raw_format = 'raw'
        with self.__lock:
            local_data = self.__emails_locally.get(message['id'], None)
        if local_data is None:
            return raw_format
        if local_data.message is None:
            return raw_format
        if os.path.getsize(local_data.message) == 0:
            return raw_format
        if local_data.message_hash is None:
            return raw_format
        if os.path.getsize(local_data.message_hash) == 0:
            return raw_format
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

            subject = str_trim(data.get('snippet', ''), 64)
            logging.debug(f'{message_id} Subject: {subject}')
            dates = datetime.fromtimestamp(int(data['internalDate']) / 1000, tz=timezone.utc) \
                .strftime('%Y-%m-%d').split('-', 1)

            path = get_path(self.email, subdir=dates, type=path_type)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            if 'raw' in data.keys():
                raw = decode_base64url(data.get('raw'))
                self.__store_message_file(message_id, raw, dates, path_type)
                data.pop('raw')
            metafile = get_path(self.email, message_id, 'json', dates, type=path_type)
            write_meta = True
            if os.path.exists(metafile):
                d = json.load(open(metafile))
                if d == data:
                    write_meta = False
            if write_meta:
                logging.debug(f'{message_id} Meta data is changed, writing to file')
                json.dump(data, open(metafile, 'w'))
            else:
                logging.debug(f'{message_id} Meta data is not changed, skip file writing')
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
            page = 1
            while True:
                logging.debug(f'Loading {page}. from server...')
                # print('.', end='')
                data = service.users().messages() \
                    .list(userId='me', pageToken=next_page_token, maxResults=1000, q='label:all').execute()
                logging.debug(f'{page} successfully loaded')
                # print(data)
                # exit(-1)
                next_page_token = data.get('nextPageToken', None)
                count = count + len(data.get('messages', []))
                messages.extend(data.get('messages', []))
                page += 1
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
        for message_id in self.__emails_locally:
            logging.info('Deleting locally stored message ' + message_id)
            data = self.__emails_locally[message_id]
            self.__remove_file(data.metadata)
            self.__remove_file(data.message)
            self.__remove_file(data.message_hash)
        return True

    @staticmethod
    def __remove_file(filepath):
        if filepath is not None and os.path.exists(filepath):
            logging.info('Deleting locally stored file (' + filepath + ')')
            os.remove(filepath)

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

    def __restore_message(self, storage_descriptor, to_email, labels_from_server, labels_from_server_to_email,
                          try_count=5,
                          sleep=10):
        logging.debug('Restoring message ' + storage_descriptor.message)
        meta = json.load(open(storage_descriptor.metadata))
        restore_message_id = meta.get('id')
        logging.debug(f"{restore_message_id} {meta}")
        label_ids = self.__add_label_ids.copy()
        for label_id in meta.get('labelIds', []):
            if self.__is_user_label_id(label_id):
                label = self.__get_label_from_index_label_id(label_id, labels_from_server,
                                                             labels_from_server_to_email)
                label_ids.append(label['id'])
            elif label_id == 'CHAT':
                logging.info(f'{meta.id} Message with CHAT label is not supported')
                return None
            else:
                label_ids.append(label_id)
        if storage_descriptor.message is None:
            logging.error(f"{restore_message_id} message file not found")
            self.__error_count += 1
            return None
        with gzip.open(storage_descriptor.message, "rb") as binary_file:
            # TODO check hash!
            message_content = binary_file.read()
        # print(file_content)
        message_data = {
            'labelIds': label_ids,
            'raw': encode_base64url(message_content),
        }
        # print(meta['labelIds'])
        # print(message_data)
        subject = str_trim(meta.get('snippet', ''), 64)
        for i in range(try_count):
            service = self.__get_service(to_email)
            try:
                try:
                    logging.info(f'{restore_message_id} Trying to upload message {i + 1}/{try_count} ({subject})')
                    result = service.users().messages().insert(userId='me', internalDateSource='dateHeader',
                                                               body=message_data).execute()
                    logging.debug(f"Message uploaded {result}")
                    logging.info(f'{restore_message_id}->{result.get("id")} Message uploaded ({subject})')
                    return result
                except HttpError as e:
                    if i == try_count - 1:
                        # last trys
                        raise e
                    logging.error(f"{restore_message_id} Exception: {e}")
                    logging.info(f"{restore_message_id} Wait {sleep} seconds and retry..")
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

        # TODO restore only used labels ??
        logging.info("Restoring labels...")
        labels_user = self.__get_user_labels_from_local()
        labels_from_server = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(), 'id'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for label_id in labels_user:
                executor.submit(self.__restore_label, labels_user[label_id]['name'], to_email)
        if self.add_labels is not None and len(self.add_labels) > 0:
            for label_name in self.add_labels:
                self.__restore_label(label_name, to_email)
        logging.info("Labels restored")

        logging.info("Getting labels from server...")
        labels_from_server_to_email = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(to_email), 'id'))
        labels_from_server_to_email_by_name = self.__labels_index_by_key(labels_from_server_to_email, 'name')
        if self.add_labels is not None and len(self.add_labels) > 0:
            self.__add_label_ids = []
            for label_name in self.add_labels:
                self.__add_label_ids.append(labels_from_server_to_email_by_name[label_name]['id'])
        logging.info("Labels downloaded")

        logging.info("Upload messages...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for message_id in self.__emails_locally:
                executor.submit(self.__restore_message, self.__emails_locally[message_id], to_email, labels_from_server,
                                labels_from_server_to_email)

        if self.__error_count > 0:
            logging.error('Messages uploaded with ' + str(self.__error_count) + ' errors')
            return False
        logging.info("Messages uploaded successfully")

        return True
