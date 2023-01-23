from __future__ import annotations

import collections
import concurrent.futures
import copy
import gzip
import json
import logging
import threading
from datetime import datetime, timedelta

from gwbackupy import global_properties
from gwbackupy.filters.filter_interface import FilterInterface
from gwbackupy.helpers import (
    decode_base64url,
    encode_base64url,
    str_trim,
    json_load,
)
from gwbackupy.process_helpers import is_killed, sleep_kc, await_all_futures
from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)
from gwbackupy.storage.storage_interface import (
    StorageInterface,
    LinkList,
    LinkInterface,
    Data,
)


class Gmail:
    """Gmail service"""

    object_id_labels = "--gwbackupy-labels--"
    """Gmail's special object ID for storing labels"""

    def __init__(
        self,
        email: str,
        storage: StorageInterface,
        service_wrapper: GmailServiceWrapperInterface,
        batch_size: int = 10,
        labels: list[str] | None = None,
        dry_mode: bool = False,
    ):
        self.dry_mode = dry_mode
        self.email = email
        self.storage = storage
        if batch_size is None or batch_size < 1:
            batch_size = 5
        self.batch_size = batch_size
        self.__lock = threading.RLock()
        self.__services = {}
        self.__error_count = 0
        self.__service_wrapper = service_wrapper
        if labels is None:
            labels = []
        self.labels = labels

    def __get_local_messages_latest_mutations_only(self):
        pass

    def __get_message_from_server(self, message_id, message_format="raw", email=None):
        if email is None:
            email = self.email
        logging.debug(
            f"{message_id} download from server with format: {message_format}"
        )
        result = self.__service_wrapper.get_message(email, message_id, message_format)
        logging.debug(f"{message_id} successfully downloaded")
        return result

    def __store_message_file(
        self, message_id: str, raw_message: bytes, create_timestamp: float
    ):
        logging.debug("Store message {id}".format(id=message_id))
        link = self.storage.new_link(
            object_id=message_id, extension="eml.gz", created_timestamp=create_timestamp
        ).set_properties(
            {
                LinkInterface.property_object: True,
                LinkInterface.property_content_hash: self.storage.content_hash_generate(
                    raw_message
                ),
            }
        )
        result = self.__storage_put(
            link, data=gzip.compress(raw_message, compresslevel=9)
        )
        if result:
            logging.info(f"{message_id} message is saved")
        else:
            raise Exception("Mail message save failed")

    def __fix_content_hash_to_message_object(
        self, message_id: str, link: LinkInterface
    ) -> LinkInterface:
        if link.get_property(LinkInterface.property_content_hash) is not None:
            return link
        logging.debug(f"{message_id} message object not has content hash, add it")
        with self.storage.get(link) as mf:
            message_content = gzip.decompress(mf.read())
            content_hash = self.storage.content_hash_generate(message_content)
        new_object_link = copy.deepcopy(link)
        new_object_link.set_properties(
            {LinkInterface.property_content_hash: content_hash}
        )
        self.storage.modify(link, new_object_link)
        logging.debug(f"{message_id} message object is signed by content hash")
        return new_object_link

    def __backup_messages(
        self, message, stored_messages: dict[str, dict[int, LinkInterface]]
    ):
        message_id = message.get("id", "UNKNOWN")  # for logging
        try:
            # if message_id != '1853ee437c8ff302':
            #     raise Exception('SKIP')
            message_id = message["id"]
            latest_meta_link = None
            if message_id in stored_messages:
                latest_meta_link = stored_messages[message_id][0]
            is_new = latest_meta_link is None
            if is_new:
                logging.debug(f"{message_id} is new")
            # TODO: option for force raw mode
            message_format = "raw"
            if not is_new and stored_messages[message_id][1] is not None:
                stored_messages[message_id][
                    1
                ] = self.__fix_content_hash_to_message_object(
                    message_id, stored_messages[message_id][1]
                )
                message_format = "minimal"
            data = self.__get_message_from_server(message_id, message_format)
            if data is None:
                # (deleted)
                logging.info(f"{message_id} is not found on server")
                return

            subject = str_trim(data.get("snippet", ""), 64)
            if is_new:
                logging.info(f"{message_id} new message, snippet: {subject}")
            else:
                logging.debug(f"{message_id} Snippet: {subject}")

            create_timestamp = int(data["internalDate"]) / 1000.0
            if "raw" in data.keys():
                raw = decode_base64url(data.get("raw"))
                self.__store_message_file(message_id, raw, create_timestamp)
                data.pop("raw")

            write_meta = True  # if any failure then write it force
            if not is_new:
                logging.log(
                    global_properties.log_finest,
                    f"{message_id} load local version of meta data",
                )
                try:
                    with self.storage.get(latest_meta_link) as mf:
                        d = json.load(mf)
                        logging.log(
                            global_properties.log_finest,
                            f"{message_id} metadata is loaded from local",
                        )
                        if d == data:
                            write_meta = False
                except BaseException as e:
                    logging.exception(f"{message_id} metadata load as json failed: {e}")

            if write_meta:
                link = self.storage.new_link(
                    object_id=message_id,
                    extension="json",
                    created_timestamp=create_timestamp,
                ).set_properties({LinkInterface.property_metadata: True})
                success = self.__storage_put(link, data=json.dumps(data))
                if success:
                    logging.info(f"{message_id} meta data is saved")
                else:
                    raise Exception("Meta data put failed")
            else:
                logging.debug(f"{message_id} meta data is not changed, skip put")
            if message_id in stored_messages:
                del stored_messages[message_id]
        except Exception as e:
            with self.__lock:
                self.__error_count += 1
            if str(e) == "SKIP":
                return
            logging.exception(f"{message_id} {e}")

    def __get_all_messages_from_server(
        self, email: str | None = None, q: str | None = "label:all"
    ):
        if email is None:
            email = self.email
        logging.info("Get all message ids from server...")
        messages = self.__service_wrapper.get_messages(email, q)
        logging.info(f"Message(s) count: {len(messages)}")
        # print(count)
        # print(messages)
        return messages

    def __get_labels_from_server(self, email=None) -> list[dict[str, any]]:
        if email is None:
            email = self.email
        logging.info(f"Getting labels from server ({email})")
        return self.__service_wrapper.get_labels(email)

    def __backup_labels(self, link: LinkInterface | None) -> bool:
        logging.info("Backing up labels...")
        labels = self.__get_labels_from_server()
        if link is not None:
            logging.debug("labels is exists, checking for changes")
            try:
                with self.storage.get(link) as f:
                    d = json.load(f)
                    if d == labels:
                        logging.info("Labels is not changed, not saving it")
                        return True
                    else:
                        logging.debug("labels is changed")
            except BaseException as e:
                logging.exception(f"labels loading or parsing failed: {e}")
        link = self.storage.new_link(
            object_id=Gmail.object_id_labels, extension="json", created_timestamp=None
        ).set_properties({LinkInterface.property_metadata: True})
        result = self.__storage_put(link, data=json.dumps(labels))
        if not result:
            logging.error("Error while storing labels")
            return False
        logging.info("Backing up labels successfully")
        return True

    def __storage_remove(self, link: LinkInterface) -> bool:
        if self.dry_mode:
            logging.info(f"DRY MODE storage remove: {link}")
            return True
        return self.storage.remove(link)

    def __storage_put(self, link: LinkInterface, data: Data) -> bool:
        if self.dry_mode:
            logging.info(f"DRY MODE storage put: {link}")
            return True
        return self.storage.put(link, data)

    def backup(self, quick_sync_days: int | None = None) -> bool:
        logging.info(f"Starting backup for {self.email}")
        self.__error_count = 0

        logging.info("Scanning backup storage...")
        stored_data_all = self.storage.find()
        logging.info(f"Stored items: {len(stored_data_all)}")

        labels_link = stored_data_all.find(
            f=lambda l: l.id() == Gmail.object_id_labels and l.is_metadata
        )
        if not self.__backup_labels(labels_link):
            logging.error("Backup finished with storing labels failed")
            return False
        if quick_sync_days is not None and quick_sync_days < 1:
            quick_sync_days = None
        if quick_sync_days is not None:
            logging.info(f"Quick syncing, going back {quick_sync_days} days")

        stored_messages: dict[str, dict[int, LinkInterface]] = stored_data_all.find(
            f=lambda l: not l.is_special_id() and (l.is_metadata() or l.is_object()),
            g=lambda l: [l.id(), 0 if l.is_metadata() else 1],
        )
        del stored_data_all
        for message_id in list(stored_messages.keys()):
            link_metadata = stored_messages[message_id].get(0)
            if link_metadata is None:
                logging.error(f"{message_id} metadata is not found in locally")
                del stored_messages[message_id]
            elif link_metadata.is_deleted():
                logging.debug(f"{message_id} metadata is already deleted")
                del stored_messages[message_id]
            else:
                logging.log(
                    global_properties.log_finest,
                    f"{message_id} is usable from backup storage",
                )
        logging.info(f"Stored messages: {len(stored_messages)}")

        q = "label:all"
        if quick_sync_days is not None:
            date = datetime.now() - timedelta(days=quick_sync_days)
            q = f"label:all after:{date.strftime('%Y/%m/%d')}"
        messages_from_server = self.__get_all_messages_from_server(q=q)
        logging.info("Processing...")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size)
        futures = []
        # submit message download jobs
        for message_id in messages_from_server:
            futures.append(
                executor.submit(
                    self.__backup_messages,
                    messages_from_server[message_id],
                    stored_messages,
                )
            )
        # wait for jobs
        if not await_all_futures(futures):
            # cancel jobs
            executor.shutdown(cancel_futures=True)
            logging.warning("Process is killed")
            return False
        logging.info("Processed")

        if self.__error_count > 0:
            # if error then never delete!
            logging.error("Backup failed with " + str(self.__error_count) + " errors")
            return False

        if quick_sync_days is None:
            logging.info("Mark as deletes...")
            for message_id in stored_messages:
                if is_killed():
                    logging.warning("Process is killed")
                    return False

                links = stored_messages[message_id]
                logging.debug(f"{message_id} mark as deleted in local storage...")
                meta_link = links.get(0)
                if meta_link is None:
                    continue
                logging.debug(f"{message_id} - {meta_link}")
                if self.__storage_remove(meta_link):
                    logging.debug(f"{message_id} metadata mark as deleted successfully")
                    message_link = links.get(1)
                    if message_link is None:
                        logging.info(f"{message_id} marked as deleted")
                    else:
                        if self.__storage_remove(message_link):
                            logging.debug(
                                f"{message_id} object mark as deleted successfully"
                            )
                            logging.info(f"{message_id} marked as deleted")
                        else:
                            logging.error(f"{message_id} object mark as deleted fail")
                else:
                    logging.error(f"{message_id} mark as deleted failed")
            logging.info("Mark as deleted: complete")
        else:
            logging.info("Quick syncing mode, skip deletion for locale storage")
        logging.info(f"Backup finished for {self.email}")
        return True

    def __create_label_server(self, label_name, email) -> dict:
        if email is None:
            email = self.email
        logging.info(f"Restoring label if not exists: {label_name}")
        if self.dry_mode:
            logging.info("DRY MODE: create label if not exists")
            return {
                "id": f"Label_DRY{datetime.utcnow().timestamp():1.3f}",
                "type": "user",
                "name": label_name,
            }
        return self.__service_wrapper.create_label(email=email, name=label_name)

    def __get_restore_label_ids(
        self,
        to_email: str,
        labels_from_storage: dict[str, dict[str, any]],
        labels_form_server: dict[str, dict[str, any]],
        add_labels: [str],
        label_ids_from_message: [str],
    ) -> [str]:
        if self.email != to_email:
            raise NotImplementedError("Not implemented for different emails")
        with self.__lock:
            result = []
            for message_label_id in label_ids_from_message:
                if message_label_id == "CHAT":
                    # CHAT tag cannot be restoring
                    continue
                if message_label_id in labels_form_server:
                    server_data = labels_form_server[message_label_id]
                    if server_data["type"] == "system" or server_data["type"] == "user":
                        # user and system tag allow directly if exists on server
                        result.append(server_data["id"])
                        continue
                    raise NotImplementedError(
                        f'Not implemented tag type: {server_data["type"]}'
                    )
                # not exists on server
                if message_label_id not in labels_from_storage:
                    logging.warning(
                        f"Label with {message_label_id} ID is cannot be restored because no data can be found."
                    )
                    continue
                label_data = labels_from_storage[message_label_id]
                created_label_data = self.__create_label_server(
                    label_data["name"], to_email
                )
                if created_label_data is None:
                    raise Exception(f"Label is created already? A ({label_data})")
                # label data stored on original label ID!
                labels_form_server[message_label_id] = created_label_data
                result.append(created_label_data["id"])
            for add_label in add_labels:
                found = False
                for key in labels_form_server:
                    server_data = labels_form_server[key]
                    if server_data["name"] == add_label:
                        result.append(server_data["id"])
                        found = True
                        break
                if found:
                    continue
                # create label...
                created_label_data = self.__create_label_server(add_label, to_email)
                if created_label_data is None:
                    raise Exception(f"Label is created already? B ({label_data})")
                # label data stored on original label ID!
                labels_form_server[created_label_data["id"]] = created_label_data
                result.append(created_label_data["id"])

            return result

    def __restore_message(
        self,
        restore_message_id: str,
        link: dict[int, LinkInterface],
        to_email: str,
        labels_from_storage: dict[str, dict[str, any]],
        labels_form_server: dict[str, dict[str, any]],
        add_labels: [str],
    ):
        try:
            logging.info(f"{restore_message_id} Restoring message...")
            if 0 not in link or 1 not in link:
                raise Exception("Metadata and/or message link not found in storage")
            with self.storage.get(link[0]) as mf:
                meta = json.load(mf)
            logging.debug(f"{restore_message_id} {meta}")
            with self.storage.get(link[1]) as mf:
                message_content = gzip.decompress(mf.read())
            label_ids_from_message: [str] = meta["labelIds"]
            try:
                label_ids_from_message.index("CHAT")
                # not restorable as message
                logging.info(
                    f"{restore_message_id} message with CHAT label is not supported."
                )
                return
            except ValueError:
                pass
            label_ids = self.__get_restore_label_ids(
                to_email=to_email,
                labels_from_storage=labels_from_storage,
                labels_form_server=labels_form_server,
                add_labels=add_labels,
                label_ids_from_message=label_ids_from_message,
            )
            label_names = []
            for label_id in meta["labelIds"]:
                label_names.append(labels_form_server[label_id]["name"])

            logging.info(
                f"{restore_message_id} snippet: {str_trim(meta['snippet'], 80)} / labels: {', '.join(label_names)}"
            )

            message_data = {
                "labelIds": label_ids,
                "raw": encode_base64url(message_content),
            }
            subject = str_trim(meta.get("snippet", ""), 64)
            if self.dry_mode:
                logging.info(f"DRY MODE {restore_message_id} message insert")
            result = self.__service_wrapper.insert_message(to_email, message_data)
            logging.debug(f"Message uploaded {result}")
            logging.info(
                f'{restore_message_id}->{result.get("id")} Message uploaded ({subject})'
            )
            return result
        except BaseException as e:
            with self.__lock:
                self.__error_count += 1
            logging.exception(f"{restore_message_id} Exception: {e}")

    def __load_labels_from_storage(
        self, links: LinkList[LinkInterface]
    ) -> dict[str, dict[str, any]] | None:
        logging.info(f"Loading labels...")
        labels_links: dict[str, LinkInterface] = links.find(
            f=lambda l: l.id() == Gmail.object_id_labels and l.is_metadata,
            g=lambda l: [l.mutation()],
        )
        labels_links = collections.OrderedDict(sorted(labels_links.items()))
        result = {}
        for key in labels_links:
            labels_link = labels_links[key]
            with self.storage.get(labels_link) as lf:
                json_data: list[dict[str, any]] = json_load(lf)
                if json_data is None:
                    logging.error(f"Stored labels read from JSON failed")
                    return None
                for item in json_data:
                    if item.get("id") is None:
                        logging.error(f"Invalid structure of stored labels")
                        return None
                    result[item.get("id")] = item
        logging.info(f"Labels loaded successfully ({len(result)})")
        return result

    def restore(
        self,
        item_filter: FilterInterface,
        to_email: str | None = None,
        restore_deleted: bool = False,
        add_labels: list[str] | None = None,
        restore_missing: bool = False,
    ):
        self.__error_count = 0
        if to_email is None:
            to_email = self.email

        if not restore_deleted and not restore_missing:
            logging.warning("Tasks not found, see more e.g. --restore-deleted")
            return True

        logging.info("Scanning backup storage...")
        stored_data_all = self.storage.find()
        logging.info(f"Stored items: {len(stored_data_all)}")

        latest_labels_from_storage = self.__load_labels_from_storage(stored_data_all)
        if latest_labels_from_storage is None:
            logging.error("Stored labels loading failed")
            return False
        _labels_from_server = self.__get_labels_from_server()
        if _labels_from_server is None:
            logging.error("Loading labels from server failed")
            return False
        labels_from_server = {}
        for label in _labels_from_server:
            if "id" not in label:
                raise Exception("Not supported label structure")
            labels_from_server[label.get("id")] = label
        del _labels_from_server
        messages_from_server_dest_email = {}
        if self.email == to_email:
            messages_from_server_dest_email = self.__get_all_messages_from_server()

        logging.info("Filtering messages...")
        stored_messages: dict[str, dict[int, LinkInterface]] = stored_data_all.find(
            f=lambda l: not l.is_special_id()
            and (l.is_metadata() or l.is_object())
            and item_filter.match(
                {
                    "message-id": l.id(),
                    "link": l,
                    "server-data": messages_from_server_dest_email,
                }
            ),
            g=lambda l: [l.id(), 0 if l.is_metadata() else 1],
        )
        del stored_data_all
        for message_id in list(stored_messages.keys()):
            if (
                stored_messages[message_id].get(0) is None
                or stored_messages[message_id].get(1) is None
            ):
                # no metadata or no object
                del stored_messages[message_id]

        logging.info(f"Number of potentially affected messages: {len(stored_messages)}")
        logging.info("Upload messages...")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size)
        futures = []
        for message_id in stored_messages:
            futures.append(
                executor.submit(
                    self.__restore_message,
                    message_id,
                    stored_messages[message_id],
                    to_email,
                    latest_labels_from_storage,
                    labels_from_server,
                    add_labels,
                )
            )
        if not await_all_futures(futures):
            logging.warning("Process killed")
            return False

        if self.__error_count > 0:
            logging.error(f"Messages uploaded with {self.__error_count} errors")
            return False
        logging.info("Messages uploaded successfully")

        return True
