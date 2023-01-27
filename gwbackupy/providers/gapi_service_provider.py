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
)


class AccessNotInitializedError(Exception):
    pass


class GapiServiceProvider(ServiceProviderInterface):
    object_id_token = LinkInterface.id_special_prefix + "token--"
    """object ID for access token save and load"""

    def __init__(
        self,
        service_name: str,
        version: str,
        scopes: [str],
        storage: StorageInterface,
        credentials_file_path: str | None = None,
        service_account_file_path: str | None = None,
        service_account_email: str | None = None,
        oauth_bind_addr: str = "0.0.0.0",
        oauth_port: int = 0,
        oauth_redirect_host: str = "localhost",
        verify_email: bool = True,
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
        self.credentials_token_links: dict[
            str, LinkInterface
        ] = self.storage.find().find(
            f=lambda l: l.id() == GapiServiceProvider.object_id_token,
            g=lambda l: [l.get_properties().get("email", "")],
        )
        self.oauth_bind_addr = oauth_bind_addr
        self.oauth_port = oauth_port
        self.oauth_redirect_host = oauth_redirect_host
        self.verify_email = verify_email

    def release_service(self, email: str, service):
        logging.debug(f"{email} Release service")
        if service is None:
            return
        with self.tlock:
            if email not in self.services:
                return
            self.services[email].append(service)

    def get_service(self, email: str, access_init: bool = True):
        service = None
        with self.tlock:
            if email not in self.services.keys():
                self.services[email] = []
            if len(self.services[email]) > 0:
                logging.debug(f"{email} Reuse service")
                service = self.services[email].pop()
            if service is None:
                logging.debug(f"{email} Create new service")
                if self.credentials_file_path is not None:
                    credentials = self.__get_credentials_by_oauth(
                        email, access_init=access_init
                    )
                elif self.service_account_file_path is not None:
                    credentials = self.__get_credentials_by_service_account(email)
                else:
                    raise Exception(f"{email} Not supported credentials")
                if not credentials:
                    raise Exception(f"{email} Credentials cannot be None")
                service = build(
                    self.service_name,
                    self.version,
                    credentials=credentials,
                )
        return ServiceItem(self, email, service)

    def __get_credentials_by_service_account(self, email: str):
        """get credentials by service account access"""
        extension = self.service_account_file_path.split(".")[-1].lower()
        if extension == "p12":
            if (
                self.service_account_email is None
                or self.service_account_email.strip() == ""
            ):
                raise Exception(
                    f"{email} Service account email is required for p12 keyfile"
                )
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
            raise Exception(f"{email} Not supported service account file extension")

        credentials = credentials.create_delegated(email)
        return credentials

    def __get_credentials_by_oauth(self, email: str, access_init: bool = True):
        """Get credentials object from OAuth access. This method store token and reuse/refresh if required"""
        credentials = None
        fd, temp = tempfile.mkstemp()
        email_md5 = hashlib.md5(email.encode("utf-8")).hexdigest().lower()
        if email_md5 in self.credentials_token_links:
            logging.debug(f"{email} Try to load previously saved token")
            token_link = self.credentials_token_links.get(email_md5)
            with self.storage.get(token_link) as tf:
                with open(temp, "wb") as tfo:
                    tfo.write(tf.read())
            credentials = Credentials.from_authorized_user_file(temp)
        if not credentials or not credentials.valid:
            logging.debug(f"{email} Credentials not found or not valid")
            if credentials and credentials.expired and credentials.refresh_token:
                logging.debug(f"{email} Try to refresh token")
                try:
                    credentials.refresh(Request())
                except RefreshError as e:
                    logging.exception(f"{email} Failed to refresh token: {e}")
                    credentials = None
            if not credentials:
                logging.debug("{email} Credentials not found")
                if not access_init:
                    raise AccessNotInitializedError()
                requests_scope = self.scopes.copy()
                if self.verify_email:
                    requests_scope.append(
                        "https://www.googleapis.com/auth/userinfo.email"
                    )
                    requests_scope.append("openid")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file_path,
                    requests_scope,
                )
                credentials = flow.run_local_server(
                    access_type="offline",
                    include_granted_scopes="true",
                    bind_addr=self.oauth_bind_addr,
                    port=self.oauth_port,
                    host=self.oauth_redirect_host,
                    timeout_seconds=300,
                )
                if self.verify_email:
                    auth_email = self.__oauth_get_email(credentials)
                    if auth_email != email:
                        raise ValueError(f"{email} vs {auth_email} mismatch")

            token_link_new = self.storage.new_link(
                GapiServiceProvider.object_id_token, "json"
            )
            token_link_new.set_properties({"email": email_md5})
            logging.debug(f"{email} Put token to storage ({token_link_new})")
            result = self.storage.put(token_link_new, credentials.to_json())
            if not result:
                raise Exception(f"{email} Failed to store token ({token_link_new})")
            else:
                logging.info(f"{email} token stored successfully")
                token_link_old = self.credentials_token_links.get(email_md5)
                self.credentials_token_links[email_md5] = token_link_new
                if token_link_old:
                    result = self.storage.remove(token_link_old, False)
                    if result:
                        logging.debug(f"{email} Old token removed successfully")
                    else:
                        logging.warning(f"{email} Old token removed fail")
        return credentials

    def __oauth_get_email(self, credentials) -> str:
        try:
            service = build(
                "oauth2",
                "v2",
                credentials=credentials,
            )
            user_info = service.userinfo().get().execute()
            return user_info.get("email")
        except BaseException as e:
            raise Exception(f"Could not retrieve user email") from e
