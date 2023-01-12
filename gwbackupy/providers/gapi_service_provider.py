from __future__ import annotations

import hashlib
import logging
import tempfile
import threading

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from gwbackupy.providers.service_provider_interface import (
    ServiceProviderInterface,
    ServiceItem,
)
from gwbackupy.storage.storage_interface import (
    LinkInterface,
    StorageInterface,
    LinkList,
)


class GapiServiceProvider(ServiceProviderInterface):
    object_id_token = LinkInterface.id_special_prefix + "token--"
    """object ID for access token save and load"""

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
        self.service_name = service_name
        self.version = version
        self.scopes = scopes
        self.credentials_file_path = credentials_file_path
        self.service_account_file_path = service_account_file_path
        self.service_account_email = service_account_email
        self.storage = storage
        self.tlock = threading.RLock()
        self.services: dict[str, list[any]] = dict()
        self.credentials_token_links: dict[str, LinkInterface] = dict()

    def release_service(self, email: str, service):
        logging.debug(f"Release service ({email})")
        if service is None:
            return
        with self.tlock:
            if email not in self.services:
                return
            self.services[email].append(service)

    def get_service(self, email: str):
        service = None
        with self.tlock:
            if email not in self.services.keys():
                self.services[email] = []
            if len(self.services[email]) > 0:
                logging.debug(f"Reuse service ({email})")
                service = self.services[email].pop()
            if service is None:
                logging.debug("Create new service")
                if self.credentials_file_path is not None:
                    credentials = self.__get_credentials_by_oauth(email)
                elif self.service_account_file_path is not None:
                    credentials = self.__get_credentials_by_service_account(email)
                else:
                    raise Exception(f"Not supported credentials")
                if not credentials:
                    raise Exception(f"Credentials cannot be None")
                service = build(
                    self.service_name,
                    self.version,
                    credentials=credentials,
                )
        return ServiceItem(self, email, service)

    def storage_links(self, links: LinkList[LinkInterface]):
        """Filter stored tokens for OAuth authentication"""
        self.credentials_token_links = links.find(
            f=lambda l: l.id() == GapiServiceProvider.object_id_token,
            g=lambda l: [l.get_properties().get("email", "")],
        )

    def __get_credentials_by_service_account(self, email: str):
        """get credentials by service account access"""
        extension = self.service_account_file_path.split(".")[-1].lower()
        if extension == "p12":
            if (
                self.service_account_email is None
                or self.service_account_email.strip() == ""
            ):
                raise Exception("Service account email is required for p12 keyfile")
            credentials = ServiceAccountCredentials.from_p12_keyfile(
                self.service_account_email,
                self.service_account_file_path,
                "notasecret",
                scopes=self.scopes,
            )
        elif extension == "json":
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.service_account_file_path,
                self.scopes,
            )
            pass
        else:
            raise Exception(f"Not supported service account file extension")

        credentials = credentials.create_delegated(email)
        return credentials

    def __get_credentials_by_oauth(self, email: str):
        """Get credentials object from OAuth access. This method store token and reuse/refresh if required"""
        credentials = None
        fd, temp = tempfile.mkstemp()
        email_md5 = hashlib.md5(email.encode("utf-8")).hexdigest().lower()
        if email_md5 in self.credentials_token_links:
            logging.debug("Try to load previously saved token")
            token_link = self.credentials_token_links.get(email_md5)
            with self.storage.get(token_link) as tf:
                with open(temp, "wb") as tfo:
                    tfo.write(tf.read())
            credentials = Credentials.from_authorized_user_file(temp)
        if not credentials or not credentials.valid:
            logging.debug("Credentials not found or not valid")
            if credentials and credentials.expired and credentials.refresh_token:
                logging.debug("Try to refresh token")
                try:
                    credentials.refresh(Request())
                except RefreshError as e:
                    logging.exception(f"Failed to refresh token: {e}")
                    credentials = None
            if not credentials:
                logging.debug("Credentials not found")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file_path,
                    self.scopes,
                )
                credentials = flow.run_local_server(port=0)

            token_link_new = self.storage.new_link(
                GapiServiceProvider.object_id_token, "json"
            )
            token_link_new.set_properties({"email": email_md5})
            logging.debug(f"Put token to storage ({token_link_new})")
            result = self.storage.put(token_link_new, credentials.to_json())
            if not result:
                raise Exception(f"{email} Failed to store token ({token_link_new})")
            else:
                logging.info("token stored successfully")
                token_link_old = self.credentials_token_links.get(email_md5)
                self.credentials_token_links[email_md5] = token_link_new
                if token_link_old:
                    result = self.storage.remove(token_link_old, False)
                    if result:
                        logging.debug(f"{email} Old token removed successfully")
                    else:
                        logging.warning(f"{email} Old token removed fail")
        return credentials
