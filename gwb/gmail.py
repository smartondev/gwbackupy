from __future__ import annotations

import concurrent.futures
import gzip
import json
import logging
import os
import threading
import time
import traceback

import tzlocal
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from gwb import global_properties
from gwb.helpers import get_path, decode_base64url, encode_base64url, str_trim
from gwb.storage.storage_interface import StorageInterface, LinkList, LinkInterface


class Gmail:
    """Gmail service"""
    object_id_labels = '--gwbackupy-labels--'
    """Gmail's special object ID for storing labels"""

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

    def __store_message_file(self, message_id: str, raw_message: bytes, create_timestamp: float):
        logging.debug("Store message {id}".format(id=message_id))
        link = self.storage.new_link(object_id=message_id, extension='eml.gz',
                                     created_timestamp=create_timestamp) \
            .set_properties({LinkInterface.property_object: True})
        result = self.storage.put(link, data=gzip.compress(raw_message, compresslevel=9))
        if result:
            logging.debug(f'{message_id} message is saves successfully')
        else:
            raise Exception('Mail message save failed')

    def __backup_messages(self, message, stored_messages: dict[int, LinkInterface]):
        message_id = message.get('id', 'UNKNOWN')  # for logging
        try:
            # if message_id != '18548c887279e2e5':
            #     raise Exception('SKIP')
            message_id = message['id']  # throw error if not exists
            latest_meta_link = None
            if message_id in stored_messages:
                latest_meta_link = stored_messages[message_id][0]
            is_new = latest_meta_link is None
            if is_new:
                logging.debug(f'{message_id} is new')
            # TODO: option for force raw mode
            message_format = 'raw'
            if not is_new and stored_messages[message_id][1] is not None:
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

            create_timestamp = int(data['internalDate']) / 1000.0
            if 'raw' in data.keys():
                raw = decode_base64url(data.get('raw'))
                self.__store_message_file(message_id, raw, create_timestamp)
                data.pop('raw')
            write_meta = True  # if any failure then write it force
            if not is_new:
                logging.log(global_properties.log_finest, f'{message_id} load local version of meta data')
                try:
                    with self.storage.get(latest_meta_link) as mf:
                        if mf is not None:
                            d = json.load(mf)
                            logging.log(global_properties.log_finest, f'{message_id} metadata is loaded from local')
                            if d == data:
                                write_meta = False
                        else:
                            logging.warning(f'{message_id} local version of meta data is not exists')
                except BaseException as e:
                    logging.error(f'{message_id} metadata load as json failed: {e}')
                    logging.error(traceback.format_exc())

            if write_meta:
                link = self.storage.new_link(object_id=message_id, extension='json',
                                             created_timestamp=create_timestamp) \
                    .set_properties({LinkInterface.property_metadata: True})
                success = self.storage.put(link, data=json.dumps(data))
                if success:
                    logging.info(f'{message_id} Meta data is saved')
                else:
                    raise Exception('Meta data put failed')
            else:
                logging.debug(f'{message_id} Meta data is not changed, skip put')
            if message_id in stored_messages:
                del stored_messages[message_id]
        except Exception as e:
            with self.__lock:
                self.__error_count += 1
            # if str(e) == 'SKIP':
            #     return
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

    def __backup_labels(self, link: LinkInterface | None):
        logging.info('Backing up labels...')
        labels = self.__get_labels_from_server()
        if link is not None:
            logging.debug('labels is exists, checking for changes')
            try:
                with self.storage.get(link) as f:
                    if f is None:
                        logging.error('labels loading failed.')
                    else:
                        d = json.load(f)
                        if d == labels:
                            logging.info('Labels is not changed, not saving it')
                            return
                        else:
                            logging.debug('labels is changed')
            except BaseException as e:
                logging.error(f'labels loading or parsing failed: {e}')
                logging.error(traceback.format_exc())
        link = self.storage.new_link(object_id=Gmail.object_id_labels, extension='json',
                                     created_timestamp=None) \
            .set_properties({LinkInterface.property_metadata: True})
        self.storage.put(link, data=json.dumps(labels))
        logging.info('Backing up labels successfully')

    def backup(self):
        logging.info(f'Starting backup for {self.email}')
        self.__error_count = 0

        logging.info("Scanning backup storage...")
        stored_data_all = self.storage.find()
        logging.info(f'Stored items: {len(stored_data_all)}')
        labels_link = stored_data_all.latest_mutation(f=lambda l: l.id() == Gmail.object_id_labels and l.is_metadata)
        self.__backup_labels(labels_link)

        stored_messages: dict[str, dict[int, LinkInterface]] = stored_data_all.latest_mutation(
            f=lambda l: l.id() != Gmail.object_id_labels and (l.is_metadata() or l.is_object()),
            g=lambda l: [l.id(), 0 if l.is_metadata() else 1])
        del stored_data_all
        for message_id in list(stored_messages.keys()):
            link_metadata = stored_messages[message_id].get(0)
            if link_metadata is None:
                logging.error(f'{message_id} metadata is not found in locally')
                del stored_messages[message_id]
            elif link_metadata.is_deleted():
                logging.debug(f'{message_id} metadata is already deleted')
                del stored_messages[message_id]
            else:
                logging.log(global_properties.log_finest, f'{message_id} is usable from backup storage')
        logging.info(f'Stored messages: {len(stored_messages)}')

        messages_from_server = self.__get_all_email_ids_from_server()
        logging.info('Processing...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            for message_id in messages_from_server:
                executor.submit(self.__backup_messages, messages_from_server[message_id], stored_messages)
        logging.info('Processed')

        if self.__error_count > 0:
            # if error then never delete!
            logging.error('Backup failed with ' + str(self.__error_count) + ' errors')
            return False

        logging.info('Mark as deletes...')
        for message_id in stored_messages:
            links = stored_messages[message_id]
            logging.debug(f'{message_id} mark as deleted in local storage...')
            meta_link = links.get(0)
            if meta_link is None:
                continue
            logging.debug(f'{message_id} - {meta_link}')
            if self.storage.remove(meta_link):
                logging.debug(f'{message_id} metadata mark as deleted successfully')
                message_link = links.get(1)
                if message_link is None:
                    logging.info(f'{message_id} marked as deleted')
                else:
                    if self.storage.remove(message_link):
                        logging.debug(f'{message_id} object mark as deleted successfully')
                        logging.info(f'{message_id} marked as deleted')
                    else:
                        logging.error(f'{message_id} object mark as deleted fail')
            else:
                logging.error(f'{message_id} mark as deleted failed')

        logging.info('Mark as deleted: complete')
        logging.info(f'Backup finished for {self.email}')
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

    def restore(self, to_email=None, timezone=None, filter_date_from=None, filter_date_to=None,
                restore_deleted=False, add_labels=None):
        if timezone is None:
            timezone = tzlocal.get_localzone()
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
