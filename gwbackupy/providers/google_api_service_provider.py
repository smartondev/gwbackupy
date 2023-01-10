from __future__ import annotations

import hashlib
import logging
import tempfile
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from gwbackupy.providers.service_provider_interface import ServiceProviderInterface
from gwbackupy.storage.storage_interface import LinkInterface, StorageInterface


class ServiceItem:
    object_id_token = LinkInterface.id_special_prefix + "token--"

    def __init__(self, provider: GoogleApiServiceProvider, email: str):
        self.__provider = provider
        self.__email: str = email
        self.__created_service = None

    def __enter__(self):
        service = None
        with self.__provider.tlock:
            if self.__email not in self.__provider.services.keys():
                self.__provider.services[self.__email] = []
            if len(self.__provider.services[self.__email]) > 0:
                logging.debug("Reuse service")
                service = self.__provider.services[self.__email].pop()
            if service is None:
                logging.debug("Create new service")
                credentials = None
                if self.__provider.credentials_file_path is not None:
                    fd, temp = tempfile.mkstemp()
                    email_md5 = (
                        hashlib.md5(self.__email.encode("utf-8")).hexdigest().lower()
                    )
                    if email_md5 in self.__provider.credentials_token_links:
                        logging.debug("Try to load previously saved token")
                        token_link = self.__provider.credentials_token_links.get(
                            email_md5
                        )
                        with self.__provider.storage.get(token_link) as tf:
                            with open(temp, "wb") as tfo:
                                tfo.write(tf.read())
                        credentials = Credentials.from_authorized_user_file(temp)
                    if not credentials or not credentials.valid:
                        if (
                            credentials
                            and credentials.expired
                            and credentials.refresh_token
                        ):
                            credentials.refresh(Request())
                        else:
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.__provider.credentials_file_path,
                                self.__provider.scopes,
                            )
                            credentials = flow.run_local_server(port=0)

                        token_link_new = self.__provider.storage.new_link(
                            ServiceItem.object_id_token, "json"
                        )
                        token_link_new.set_properties({"email": email_md5})
                        result = self.__provider.storage.put(
                            token_link_new, credentials.to_json()
                        )
                        if not result:
                            raise Exception(
                                f"{self.__email} Failed to store token ({token_link_new})"
                            )
                        else:
                            logging.info("token stored successfully")
                            token_link_old = (
                                self.__provider.credentials_token_links.get(email_md5)
                            )
                            self.__provider.credentials_token_links[
                                email_md5
                            ] = token_link_new
                            if token_link_old:
                                result = self.__provider.storage.remove(
                                    token_link_old, False
                                )
                                if result:
                                    logging.debug(
                                        f"{self.__email} Old token removed successfully"
                                    )
                                else:
                                    logging.warning(
                                        f"{self.__email} Old token removed fail"
                                    )
                elif self.__provider.service_account_file_path is not None:
                    extension = self.__provider.service_account_file_path.split(".")[
                        -1
                    ].lower()
                    if extension == "p12":
                        if (
                            self.__provider.service_account_email is None
                            or self.__provider.service_account_email.strip() == ""
                        ):
                            raise Exception(
                                "Service account email is required for p12 keyfile"
                            )
                        credentials = ServiceAccountCredentials.from_p12_keyfile(
                            self.__provider.service_account_email,
                            self.__provider.service_account_file_path,
                            "notasecret",
                            scopes=self.__provider.scopes,
                        )
                    elif extension == "json":
                        credentials = ServiceAccountCredentials.from_json_keyfile_name(
                            self.__provider.service_account_file_path,
                            self.__provider.scopes,
                        )
                        pass
                    else:
                        raise Exception(f"Not supported service account file extension")

                    credentials = credentials.create_delegated(self.__email)
                else:
                    raise Exception(f"Not supported credentials")
                service = build(
                    self.__provider.service_name,
                    self.__provider.version,
                    credentials=credentials,
                )
        self.__created_service = service
        return service

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def release(self):
        logging.debug("Release service (email: " + str(self.__email) + ")")
        if self.__created_service is None:
            return
        with self.__provider.tlock:
            if self.__email not in self.__provider.services:
                return
            self.__provider.services[self.__email].append(self.__created_service)


class GoogleApiServiceProvider(ServiceProviderInterface):
    def __init__(
        self,
        service_name: str,
        version: str,
        scopes: [str],
        credentials_file_path: str | None = None,
        service_account_file_path: str | None = None,
        service_account_email: str | None = None,
        storage: StorageInterface | None = None,
    ):
        super().__init__(
            service_name,
            version,
            scopes,
            credentials_file_path=credentials_file_path,
            service_account_file_path=service_account_file_path,
            service_account_email=service_account_email,
            storage=storage,
        )
        self.tlock = threading.RLock()
        self.services: dict[str, list[any]] = dict()
        self.credentials_token_links: dict[str, LinkInterface] = dict()

    def get_service(self, email: str):
        return ServiceItem(self, email)
