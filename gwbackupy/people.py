from __future__ import annotations

import concurrent
import json
import logging
import threading

import requests

from gwbackupy import global_properties
from gwbackupy.process_helpers import await_all_futures
from gwbackupy.providers.people_service_wrapper_interface import (
    PeopleServiceWrapperInterface,
)
from gwbackupy.storage.storage_interface import StorageInterface, LinkInterface, Data


class People:
    """People (contacts) service"""

    def __init__(
        self,
        email: str,
        storage: StorageInterface,
        service_wrapper: PeopleServiceWrapperInterface,
        batch_size: int = 10,
        dry_mode: bool = False,
    ):
        self.dry_mode = dry_mode
        self.email = email
        self.storage = storage
        if batch_size is None or batch_size < 1:
            batch_size = 5
        self.batch_size = batch_size
        self.__lock = threading.RLock()
        self.__error_count = 0
        self.__service_wrapper = service_wrapper

    def backup(self):
        logging.info(f"Starting backup for {self.email}")
        self.__error_count = 0

        logging.info("Scanning backup storage...")
        stored_data_all = self.storage.find()
        logging.info(f"Stored items: {len(stored_data_all)}")

        stored_items: dict[str, dict[int, LinkInterface]] = stored_data_all.find(
            f=lambda l: not l.is_special_id() and (l.is_metadata() or l.is_object()),
            g=lambda l: [l.id(), 0 if l.is_metadata() else 1],
        )

        del stored_data_all
        for item_id in list(stored_items.keys()):
            link_metadata = stored_items[item_id].get(0)
            if link_metadata is None:
                logging.error(f"{item_id} metadata is not found in locally")
                del stored_items[item_id]
            elif link_metadata.is_deleted():
                logging.debug(f"{item_id} metadata is already deleted")
                del stored_items[item_id]
            else:
                logging.log(
                    global_properties.log_finest,
                    f"{item_id} is usable from backup storage",
                )
        logging.info(f"Stored peoples: {len(stored_items)}")

        items_from_server = self.__service_wrapper.get_peoples(self.email)

        logging.info("Processing...")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.batch_size)
        futures = []
        # submit message download jobs
        for message_id in items_from_server:
            futures.append(
                executor.submit(
                    self.__backup_item,
                    items_from_server[message_id],
                    stored_items,
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

        return False

    def __backup_item(
        self, people: dict[str, any], stored_items: dict[str, dict[int, LinkInterface]]
    ):
        people_id = people.get("resourceName", "UNKNOWN")  # for logging
        try:
            people_id = people["resourceName"]
            latest_meta_link = None
            if people_id in stored_items:
                latest_meta_link = stored_items[people_id][0]
            is_new = latest_meta_link is None
            if is_new:
                logging.debug(f"{people_id} is new")

            write_meta = True  # if any failure then write it force

            # ...
            etag = people.get("etag", None)
            if not is_new:
                etag_currently = latest_meta_link.get_property(
                    LinkInterface.property_etag
                )
                if etag_currently is not None and etag_currently == etag:
                    write_meta = False
                    logging.debug(f"{people_id} is not changed, skip put")

            if write_meta:
                photos = people.get("photos", [])
                for photo in photos:
                    photo_url = photo.get("url", None)
                    if photo_url is None or photo.get("default", True) is True:
                        # not found url or default photo
                        continue
                    logging.debug(f"{people_id} downloading photo: {photo_url}")
                    r = requests.get(photo_url, stream=True)
                    if r.status_code != 200:
                        logging.error(
                            f"{people_id} photo download failed ({photo_url})"
                        )
                        continue
                    logging.debug(
                        f"{people_id} photo download success ({len(r.raw)} bytes)"
                    )
                link = (
                    self.storage.new_link(
                        object_id=people_id,
                        extension="json",
                        created_timestamp=0.0,
                    )
                    .set_properties({LinkInterface.property_metadata: True})
                    .set_properties({LinkInterface.property_etag: etag})
                )
                success = self.__storage_put(link, data=json.dumps(people))
                if success:
                    logging.info(f"{people_id} meta data is saved")
                else:
                    raise Exception("Meta data put failed")
            else:
                logging.debug(f"{people_id} meta data is not changed, skip put")

        except Exception as e:
            with self.__lock:
                self.__error_count += 1
            if str(e) == "SKIP":
                return
            logging.exception(f"{people_id} {e}")

    def __storage_put(self, link: LinkInterface, data: Data) -> bool:
        if self.dry_mode:
            logging.info(f"DRY MODE storage put: {link}")
            return True
        return self.storage.put(link, data)

    def restore(self):
        pass
