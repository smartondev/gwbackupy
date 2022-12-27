import concurrent.futures
import copy
import gzip
import json
import logging
import os
import shutil
import threading
import time
import hashlib
import traceback
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from gwb import global_properties
from gwb.helpers import get_path, decode_base64url, encode_base64url, str_trim
from gwb.storage.storage_interface import StorageInterface, ObjectList, ObjectDescriptor


class Gmail:
    """Gmail service"""
    path_root = '/gmail'
    path_messages = f'{path_root}/messages'

    def __init__(self, email: str, service_account_email: str, service_account_file_path: str,
                 storage: StorageInterface, batch_size: int = 10, labels=None):
        self.email = email
        self.storage = storage
        self.service_account_email = service_account_email
        self.service_account_file_path = service_account_file_path
        if batch_size is None or batch_size < 1:
            batch_size = 5
        self.batch_size = batch_size
        self.__lock = threading.RLock()
        self.__services = {}
        self.__error_count = 0
        if labels is None:
            labels = []
        self.labels = labels

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

    def __get_local_messages_latest_mutations_only(self):
        pass

    def __get_message_from_server(self, message_id, message_format='raw', try_count=5, sleep=10, email=None):
        logging.debug(f'{message_id} download from server with format: {message_format}')
        for i in range(try_count):
            service = self.__get_service(email)
            try:
                # message_id = message_id[:-1] + 'a'
                result = service.users().messages().get(userId='me', id=message_id, format=message_format).execute()
                logging.debug(f"{message_id} successfully downloaded")
                return result
            except HttpError as e:
                if e.status_code == 404:
                    logging.debug(f"{message_id} message not found")
                    # message not found
                    return None
                if i == try_count - 1:
                    # last try
                    logging.error(f"{message_id} message download failed")
                    raise e
                logging.error(e)
                logging.error(traceback.format_exc())
                logging.info(f"{message_id} Wait {sleep} seconds and retry..")
                time.sleep(sleep)
                continue
            except Exception:
                raise
            finally:
                self.__release_service(service)

    def __store_message_file(self, message_id, raw_message, path):
        logging.debug("Store message {id}".format(id=message_id))
        mutation = self.storage.new_mutation()
        result = self.storage.put(path=path, oid=message_id,
                                  mime=StorageInterface.mime_eml_gz,
                                  data=gzip.compress(raw_message, compresslevel=9), mutation=mutation)
        if not result:
            raise Exception('Mail message save failed')

    def __backup_messages(self, message, local_messages: dict[str, ObjectList[ObjectDescriptor]]):
        message_id = message.get('id', 'UNKNOWN')  # for logging
        try:
            message_id = message['id']  # throw error if not exists
            latest_meta = None
            if message_id in local_messages:
                latest_meta = local_messages[message_id].get_latest_mutation(message_id, StorageInterface.mime_json)
            is_new = latest_meta is None
            if not is_new and latest_meta.deleted:
                raise RuntimeError('Message is already deleted')
            # TODO: option for force raw mode
            message_format = 'raw'
            if not is_new and (
                    local_messages[message_id].get_latest_mutation(message_id, StorageInterface.mime_eml_gz) or
                    local_messages[message_id].get_latest_mutation(message_id, StorageInterface.mime_eml)):
                message_format = 'minimal'
            data = self.__get_message_from_server(message_id, message_format)
            if data is None:
                # (deleted)
                logging.info(f'{message_id} is not found')
                return

            subject = str_trim(data.get('snippet', ''), 64)
            if is_new:
                logging.info(f'{message_id} New message, snippet: {subject}')
            else:
                logging.debug(f'{message_id} Snippet: {subject}')
            sub_paths = datetime.fromtimestamp(int(data['internalDate']) / 1000, tz=timezone.utc) \
                .strftime('%Y-%m-%d').split('-', 1)

            path = f'{Gmail.path_messages}/{sub_paths[0]}/{sub_paths[1]}'
            if 'raw' in data.keys():
                raw = decode_base64url(data.get('raw'))
                self.__store_message_file(message_id, raw, path)
                data.pop('raw')
            write_meta = True
            if not is_new:
                logging.log(global_properties.log_finest, f'{message_id} load local version of meta data')
                with self.storage.getd(latest_meta) as mf:
                    if mf is not None:
                        d = json.load(mf)
                        if d == data:
                            write_meta = False
                    else:
                        logging.warning(f'{message_id} local version of meta data is not exists')

            if write_meta:
                mutation = StorageInterface.new_mutation()
                logging.debug(f'{message_id} Meta data is changed')
                success = self.storage.put(path=path, oid=message_id, mime=StorageInterface.mime_json,
                                           data=json.dumps(data), mutation=mutation)
                if not success:
                    raise Exception('Meta data put failed')
            else:
                logging.debug(f'{message_id} Meta data is not changed, skip put')
            if message_id in local_messages:
                del local_messages[message_id]
        except Exception as e:
            with self.__lock:
                self.__error_count += 1
            logging.error(f'{message_id} {e}')
            logging.error(traceback.format_exc())

    def __get_all_email_ids_from_server(self, email=None):
        if email is None:
            email = self.email
        service = self.__get_service(email)
        try:
            logging.info('Get all message ids from server...')
            messages = {}
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
                for message in data.get('messages', []):
                    messages[message.get('id')] = message
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
        self.storage.put(path=Gmail.path_root, oid='labels', mime=StorageInterface.mime_json,
                         mutation=StorageInterface.new_mutation(),
                         data=json.dumps(labels))
        logging.info('Backing up labels successfully')

    def backup(self):
        logging.info('Starting backup for ' + self.email)
        self.__error_count = 0

        self.__backup_labels()
        logging.info("Scanning local messages...")
        local_messages: dict[str, ObjectList[ObjectDescriptor]] = {}
        local_messages_all = self.storage.find(Gmail.path_messages)
        logging.info(f'Local items: {len(local_messages_all)}')
        for desc in local_messages_all:
            if desc.object_id in local_messages:
                continue
            local_messages[desc.object_id] = local_messages_all.get_latest_mutations(desc.object_id)
        del local_messages_all
        logging.info(f'Local messages: {len(local_messages)}')

        messages = self.__get_all_email_ids_from_server()
        logging.info('Processing...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for message_id in messages:
                # self.__backup_messages(message)
                executor.submit(self.__backup_messages, messages[message_id], local_messages)
        logging.info('Processed')
        if self.__error_count > 0:
            logging.error('Backup failed with ' + str(self.__error_count) + ' errors')
            return False
        logging.info('Mark as deletes...')
        for message_id in local_messages:
            olist = local_messages[message_id]
            desc = olist.get_latest_mutation(message_id, StorageInterface.mime_json)
            if desc.deleted:
                # already deleted, skip it
                continue
            logging.debug(f'{message_id} mark as deleted in local storage...')
            mutation = self.storage.new_mutation()
            new_desc = copy.copy(desc)
            new_desc.deleted = True
            new_desc.mutation = mutation
            logging.debug(f'{message_id} {desc} -> {new_desc}')
            with self.storage.getd(desc) as f:
                self.storage.putd(new_desc, f)
            logging.info(f'{message_id} marked as deleted')
        logging.info('Mark as deleted: complete')
        logging.info('Backup finished for ' + self.email)
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
        file = get_path(self.email, self.work_directory, 'labels.json', group=['gmail'])
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

    def __restore_message(self, storage_descriptor, to_email, labels_from_server, labels_from_server_to_email
                          , add_label_ids, try_count=5, sleep=10):
        logging.debug('Restoring message ' + storage_descriptor.object)
        meta = json.load(open(storage_descriptor.get_latest_mutation_metadata_file_path()))
        restore_message_id = meta.get('id')
        logging.debug(f"{restore_message_id} {meta}")
        label_ids = add_label_ids.copy()
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
        if storage_descriptor.object is None:
            logging.error(f"{restore_message_id} message file not found")
            self.__error_count += 1
            return None
        with gzip.open(storage_descriptor.object, "rb") as binary_file:
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
            except Exception as e:
                with self.__lock:
                    self.__error_count += 1
                logging.error(f"{restore_message_id} Exception: {e}")
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

    def restore(self, to_email=None, filter_timezone=None, filter_date_from=None, filter_date_to=None,
                restore_deleted=False, add_labels=None):
        if to_email is None:
            to_email = self.email
        self.__error_count = 0

        # TODO restore only used labels ??
        logging.info("Restoring labels...")
        labels_user = self.__get_user_labels_from_local()
        labels_from_server_src_email = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(), 'id'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for label_id in labels_user:
                executor.submit(self.__restore_label, labels_user[label_id]['name'], to_email)
        if add_labels is not None and len(add_labels) > 0:
            for label_name in add_labels:
                self.__restore_label(label_name, to_email)
        logging.info("Labels restored")

        logging.info("Getting labels from server...")
        labels_from_server_dest_email = self.__get_user_labels_only(
            self.__labels_index_by_key(self.__get_labels_from_server(to_email), 'id'))
        labels_from_server_to_email_by_name = self.__labels_index_by_key(labels_from_server_dest_email, 'name')
        add_label_ids = []
        if add_labels is not None and len(add_labels) > 0:
            add_label_ids = []
            for label_name in add_labels:
                add_label_ids.append(labels_from_server_to_email_by_name[label_name]['id'])
        logging.info("Labels downloaded")

        messages_from_server_dest_email = {}
        if self.email == to_email:
            messages_from_server_dest_email = self.__get_all_email_ids_from_server(email=to_email)

        logging.info("Upload messages...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for message_id in self.__emails_locally:
                if message_id in messages_from_server_dest_email:
                    logging.debug(f'{message_id} exists, skip it')
                else:
                    executor.submit(self.__restore_message, self.__emails_locally[message_id], to_email,
                                    labels_from_server_src_email,
                                    labels_from_server_dest_email,
                                    add_label_ids)

        if self.__error_count > 0:
            logging.error('Messages uploaded with ' + str(self.__error_count) + ' errors')
            return False
        logging.info("Messages uploaded successfully")

        return True
