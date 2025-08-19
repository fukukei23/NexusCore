
# === NexusCore/openenv\Lib\site-packages\starlette\responses.py ===
from __future__ import annotations

import http.cookies
import json
import os
import stat
import typing
import warnings
from datetime import datetime
from email.utils import format_datetime, formatdate
from functools import partial
from mimetypes import guess_type
from urllib.parse import quote

import anyio
import anyio.to_thread

from starlette._compat import md5_hexdigest
from starlette.background import BackgroundTask
from starlette.concurrency import iterate_in_threadpool
from starlette.datastructures import URL, MutableHeaders
from starlette.types import Receive, Scope, Send


class Response:
    media_type = None
    charset = "utf-8"

    def __init__(
        self,
        content: typing.Any = None,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.body = self.render(content)
        self.init_headers(headers)

    def render(self, content: typing.Any) -> bytes:
        if content is None:
            return b""
        if isinstance(content, bytes):
            return content
        return content.encode(self.charset)  # type: ignore

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        if headers is None:
            raw_headers: list[tuple[bytes, bytes]] = []
            populate_content_length = True
            populate_content_type = True
        else:
            raw_headers = [
                (k.lower().encode("latin-1"), v.encode("latin-1"))
                for k, v in headers.items()
            ]
            keys = [h[0] for h in raw_headers]
            populate_content_length = b"content-length" not in keys
            populate_content_type = b"content-type" not in keys

        body = getattr(self, "body", None)
        if (
            body is not None
            and populate_content_length
            and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(body))
            raw_headers.append((b"content-length", content_length.encode("latin-1")))

        content_type = self.media_type
        if content_type is not None and populate_content_type:
            if (
                content_type.startswith("text/")
                and "charset=" not in content_type.lower()
            ):
                content_type += "; charset=" + self.charset
            raw_headers.append((b"content-type", content_type.encode("latin-1")))

        self.raw_headers = raw_headers

    @property
    def headers(self) -> MutableHeaders:
        if not hasattr(self, "_headers"):
            self._headers = MutableHeaders(raw=self.raw_headers)
        return self._headers

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal["lax", "strict", "none"] | None = "lax",
    ) -> None:
        cookie: http.cookies.BaseCookie[str] = http.cookies.SimpleCookie()
        cookie[key] = value
        if max_age is not None:
            cookie[key]["max-age"] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                cookie[key]["expires"] = format_datetime(expires, usegmt=True)
            else:
                cookie[key]["expires"] = expires
        if path is not None:
            cookie[key]["path"] = path
        if domain is not None:
            cookie[key]["domain"] = domain
        if secure:
            cookie[key]["secure"] = True
        if httponly:
            cookie[key]["httponly"] = True
        if samesite is not None:
            assert samesite.lower() in [
                "strict",
                "lax",
                "none",
            ], "samesite must be either 'strict', 'lax' or 'none'"
            cookie[key]["samesite"] = samesite
        cookie_val = cookie.output(header="").strip()
        self.raw_headers.append((b"set-cookie", cookie_val.encode("latin-1")))

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal["lax", "strict", "none"] | None = "lax",
    ) -> None:
        self.set_cookie(
            key,
            max_age=0,
            expires=0,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        prefix = "websocket." if scope["type"] == "websocket" else ""
        await send(
            {
                "type": prefix + "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        await send({"type": prefix + "http.response.body", "body": self.body})

        if self.background is not None:
            await self.background()


class HTMLResponse(Response):
    media_type = "text/html"


class PlainTextResponse(Response):
    media_type = "text/plain"


class JSONResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class RedirectResponse(Response):
    def __init__(
        self,
        url: str | URL,
        status_code: int = 307,
        headers: typing.Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(
            content=b"", status_code=status_code, headers=headers, background=background
        )
        self.headers["location"] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")


Content = typing.Union[str, bytes]
SyncContentStream = typing.Iterable[Content]
AsyncContentStream = typing.AsyncIterable[Content]
ContentStream = typing.Union[AsyncContentStream, SyncContentStream]


class StreamingResponse(Response):
    body_iterator: AsyncContentStream

    def __init__(
        self,
        content: ContentStream,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        if isinstance(content, typing.AsyncIterable):
            self.body_iterator = content
        else:
            self.body_iterator = iterate_in_threadpool(content)
        self.status_code = status_code
        self.media_type = self.media_type if media_type is None else media_type
        self.background = background
        self.init_headers(headers)

    async def listen_for_disconnect(self, receive: Receive) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break

    async def stream_response(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
            await send({"type": "http.response.body", "body": chunk, "more_body": True})

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with anyio.create_task_group() as task_group:

            async def wrap(func: typing.Callable[[], typing.Awaitable[None]]) -> None:
                await func()
                task_group.cancel_scope.cancel()

            task_group.start_soon(wrap, partial(self.stream_response, send))
            await wrap(partial(self.listen_for_disconnect, receive))

        if self.background is not None:
            await self.background()


class FileResponse(Response):
    chunk_size = 64 * 1024

    def __init__(
        self,
        path: str | os.PathLike[str],
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        self.path = path
        self.status_code = status_code
        self.filename = filename
        if method is not None:
            warnings.warn(
                "The 'method' parameter is not used, and it will be removed.",
                DeprecationWarning,
            )
        if media_type is None:
            media_type = guess_type(filename or path)[0] or "text/plain"
        self.media_type = media_type
        self.background = background
        self.init_headers(headers)
        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            if content_disposition_filename != self.filename:
                content_disposition = "{}; filename*=utf-8''{}".format(
                    content_disposition_type, content_disposition_filename
                )
            else:
                content_disposition = '{}; filename="{}"'.format(
                    content_disposition_type, self.filename
                )
            self.headers.setdefault("content-disposition", content_disposition)
        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)

    def set_stat_headers(self, stat_result: os.stat_result) -> None:
        content_length = str(stat_result.st_size)
        last_modified = formatdate(stat_result.st_mtime, usegmt=True)
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = f'"{md5_hexdigest(etag_base.encode(), usedforsecurity=False)}"'

        self.headers.setdefault("content-length", content_length)
        self.headers.setdefault("last-modified", last_modified)
        self.headers.setdefault("etag", etag)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.stat_result is None:
            try:
                stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
                self.set_stat_headers(stat_result)
            except FileNotFoundError:
                raise RuntimeError(f"File at path {self.path} does not exist.")
            else:
                mode = stat_result.st_mode
                if not stat.S_ISREG(mode):
                    raise RuntimeError(f"File at path {self.path} is not a file.")
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        if scope["method"].upper() == "HEAD":
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        elif "extensions" in scope and "http.response.pathsend" in scope["extensions"]:
            await send({"type": "http.response.pathsend", "path": str(self.path)})
        else:
            async with await anyio.open_file(self.path, mode="rb") as file:
                more_body = True
                while more_body:
                    chunk = await file.read(self.chunk_size)
                    more_body = len(chunk) == self.chunk_size
                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": more_body,
                        }
                    )
        if self.background is not None:
            await self.background()

# === NexusCore/openenv\Lib\site-packages\litellm\secret_managers\aws_secret_manager_v2.py ===
"""
This is a file for the AWS Secret Manager Integration

Handles Async Operations for:
- Read Secret
- Write Secret
- Delete Secret

Relevant issue: https://github.com/BerriAI/litellm/issues/1883

Requires:
* `os.environ["AWS_REGION_NAME"], 
* `pip install boto3>=1.28.57`
"""

import json
import os
from typing import Any, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.proxy._types import KeyManagementSystem
from litellm.types.llms.custom_http import httpxSpecialProvider

from .base_secret_manager import BaseSecretManager


class AWSSecretsManagerV2(BaseAWSLLM, BaseSecretManager):
    def __init__(self, **kwargs):
        BaseSecretManager.__init__(self, **kwargs)
        BaseAWSLLM.__init__(self, **kwargs)

    @classmethod
    def validate_environment(cls):
        if "AWS_REGION_NAME" not in os.environ:
            raise ValueError("Missing required environment variable - AWS_REGION_NAME")

    @classmethod
    def load_aws_secret_manager(cls, use_aws_secret_manager: Optional[bool]):
        """
        Initialize AWSSecretsManagerV2 and sets litellm.secret_manager_client = AWSSecretsManagerV2() and litellm._key_management_system = KeyManagementSystem.AWS_SECRET_MANAGER
        """
        if use_aws_secret_manager is None or use_aws_secret_manager is False:
            return
        try:
            cls.validate_environment()
            litellm.secret_manager_client = cls()
            litellm._key_management_system = KeyManagementSystem.AWS_SECRET_MANAGER

        except Exception as e:
            raise e

    async def async_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        primary_secret_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Async function to read a secret from AWS Secrets Manager

        Returns:
            str: Secret value
        Raises:
            ValueError: If the secret is not found or an HTTP error occurs
        """
        if primary_secret_name:
            return await self.async_read_secret_from_primary_secret(
                secret_name=secret_name, primary_secret_name=primary_secret_name
            )

        endpoint_url, headers, body = self._prepare_request(
            action="GetSecretValue",
            secret_name=secret_name,
            optional_params=optional_params,
        )

        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
            params={"timeout": timeout},
        )

        try:
            response = await async_client.post(
                url=endpoint_url, headers=headers, data=body.decode("utf-8")
            )
            response.raise_for_status()
            return response.json()["SecretString"]
        except httpx.TimeoutException:
            raise ValueError("Timeout error occurred")
        except Exception as e:
            verbose_logger.exception(
                "Error reading secret='%s' from AWS Secrets Manager: %s",
                secret_name,
                str(e),
            )
        return None

    def sync_read_secret(
        self,
        secret_name: str,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        primary_secret_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Sync function to read a secret from AWS Secrets Manager

        Done for backwards compatibility with existing codebase, since get_secret is a sync function
        """
        # self._prepare_request uses these env vars, we cannot read them from AWS Secrets Manager. If we do we'd get stuck in an infinite loop
        if secret_name in [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME",
            "AWS_REGION",
            "AWS_BEDROCK_RUNTIME_ENDPOINT",
        ]:
            return os.getenv(secret_name)

        if primary_secret_name:
            return self.sync_read_secret_from_primary_secret(
                secret_name=secret_name, primary_secret_name=primary_secret_name
            )

        endpoint_url, headers, body = self._prepare_request(
            action="GetSecretValue",
            secret_name=secret_name,
            optional_params=optional_params,
        )

        sync_client = _get_httpx_client(
            params={"timeout": timeout},
        )

        try:
            response = sync_client.post(
                url=endpoint_url, headers=headers, data=body.decode("utf-8")
            )
            return response.json()["SecretString"]
        except httpx.TimeoutException:
            raise ValueError("Timeout error occurred")
        except httpx.HTTPStatusError as e:
            verbose_logger.exception(
                "Error reading secret='%s' from AWS Secrets Manager: %s, %s",
                secret_name,
                str(e.response.text),
                str(e.response.status_code),
            )
        except Exception as e:
            verbose_logger.exception(
                "Error reading secret='%s' from AWS Secrets Manager: %s",
                secret_name,
                str(e),
            )
        return None

    def _parse_primary_secret(self, primary_secret_json_str: Optional[str]) -> dict:
        """
        Parse the primary secret JSON string into a dictionary

        Args:
            primary_secret_json_str: JSON string containing key-value pairs

        Returns:
            Dictionary of key-value pairs from the primary secret
        """
        return json.loads(primary_secret_json_str or "{}")

    def sync_read_secret_from_primary_secret(
        self, secret_name: str, primary_secret_name: str
    ) -> Optional[str]:
        """
        Read a secret from the primary secret
        """
        primary_secret_json_str = self.sync_read_secret(secret_name=primary_secret_name)
        primary_secret_kv_pairs = self._parse_primary_secret(primary_secret_json_str)
        return primary_secret_kv_pairs.get(secret_name)

    async def async_read_secret_from_primary_secret(
        self, secret_name: str, primary_secret_name: str
    ) -> Optional[str]:
        """
        Read a secret from the primary secret
        """
        primary_secret_json_str = await self.async_read_secret(
            secret_name=primary_secret_name
        )
        primary_secret_kv_pairs = self._parse_primary_secret(primary_secret_json_str)
        return primary_secret_kv_pairs.get(secret_name)

    async def async_write_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> dict:
        """
        Async function to write a secret to AWS Secrets Manager

        Args:
            secret_name: Name of the secret
            secret_value: Value to store (can be a JSON string)
            description: Optional description for the secret
            optional_params: Additional AWS parameters
            timeout: Request timeout
        """
        import uuid

        # Prepare the request data
        data = {"Name": secret_name, "SecretString": secret_value}
        if description:
            data["Description"] = description

        data["ClientRequestToken"] = str(uuid.uuid4())

        endpoint_url, headers, body = self._prepare_request(
            action="CreateSecret",
            secret_name=secret_name,
            secret_value=secret_value,
            optional_params=optional_params,
            request_data=data,  # Pass the complete request data
        )

        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
            params={"timeout": timeout},
        )

        try:
            response = await async_client.post(
                url=endpoint_url, headers=headers, data=body.decode("utf-8")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            raise ValueError(f"HTTP error occurred: {err.response.text}")
        except httpx.TimeoutException:
            raise ValueError("Timeout error occurred")

    async def async_delete_secret(
        self,
        secret_name: str,
        recovery_window_in_days: Optional[int] = 7,
        optional_params: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> dict:
        """
        Async function to delete a secret from AWS Secrets Manager

        Args:
            secret_name: Name of the secret to delete
            recovery_window_in_days: Number of days before permanent deletion (default: 7)
            optional_params: Additional AWS parameters
            timeout: Request timeout

        Returns:
            dict: Response from AWS Secrets Manager containing deletion details
        """
        # Prepare the request data
        data = {
            "SecretId": secret_name,
            "RecoveryWindowInDays": recovery_window_in_days,
        }

        endpoint_url, headers, body = self._prepare_request(
            action="DeleteSecret",
            secret_name=secret_name,
            optional_params=optional_params,
            request_data=data,
        )

        async_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.SecretManager,
            params={"timeout": timeout},
        )

        try:
            response = await async_client.post(
                url=endpoint_url, headers=headers, data=body.decode("utf-8")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            raise ValueError(f"HTTP error occurred: {err.response.text}")
        except httpx.TimeoutException:
            raise ValueError("Timeout error occurred")

    def _prepare_request(
        self,
        action: str,  # "GetSecretValue" or "PutSecretValue"
        secret_name: str,
        secret_value: Optional[str] = None,
        optional_params: Optional[dict] = None,
        request_data: Optional[dict] = None,
    ) -> tuple[str, Any, bytes]:
        """Prepare the AWS Secrets Manager request"""
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        optional_params = optional_params or {}
        boto3_credentials_info = self._get_boto_credentials_from_optional_params(
            optional_params
        )

        # Get endpoint
        _, endpoint_url = self.get_runtime_endpoint(
            api_base=None,
            aws_bedrock_runtime_endpoint=boto3_credentials_info.aws_bedrock_runtime_endpoint,
            aws_region_name=boto3_credentials_info.aws_region_name,
        )
        endpoint_url = endpoint_url.replace("bedrock-runtime", "secretsmanager")

        # Use provided request_data if available, otherwise build default data
        if request_data:
            data = request_data
        else:
            data = {"SecretId": secret_name}
            if secret_value and action == "PutSecretValue":
                data["SecretString"] = secret_value

        body = json.dumps(data).encode("utf-8")
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": f"secretsmanager.{action}",
        }

        # Sign request
        request = AWSRequest(
            method="POST", url=endpoint_url, data=body, headers=headers
        )
        SigV4Auth(
            boto3_credentials_info.credentials,
            "secretsmanager",
            boto3_credentials_info.aws_region_name,
        ).add_auth(request)
        prepped = request.prepare()

        return endpoint_url, prepped.headers, body


# if __name__ == "__main__":
#     print("loading aws secret manager v2")
#     aws_secret_manager_v2 = AWSSecretsManagerV2()

#     print("writing secret to aws secret manager v2")
#     asyncio.run(aws_secret_manager_v2.async_write_secret(secret_name="test_secret_3", secret_value="test_value_2"))
#     print("reading secret from aws secret manager v2")

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\tracing.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Tracing
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io


class MemoryDumpConfig(dict):
    '''
    Configuration for memory dump. Used only when "memory-infra" category is enabled.
    '''
    def to_json(self) -> dict:
        return self

    @classmethod
    def from_json(cls, json: dict) -> MemoryDumpConfig:
        return cls(json)

    def __repr__(self):
        return 'MemoryDumpConfig({})'.format(super().__repr__())


@dataclass
class TraceConfig:
    #: Controls how the trace buffer stores data.
    record_mode: typing.Optional[str] = None

    #: Size of the trace buffer in kilobytes. If not specified or zero is passed, a default value
    #: of 200 MB would be used.
    trace_buffer_size_in_kb: typing.Optional[float] = None

    #: Turns on JavaScript stack sampling.
    enable_sampling: typing.Optional[bool] = None

    #: Turns on system tracing.
    enable_systrace: typing.Optional[bool] = None

    #: Turns on argument filter.
    enable_argument_filter: typing.Optional[bool] = None

    #: Included category filters.
    included_categories: typing.Optional[typing.List[str]] = None

    #: Excluded category filters.
    excluded_categories: typing.Optional[typing.List[str]] = None

    #: Configuration to synthesize the delays in tracing.
    synthetic_delays: typing.Optional[typing.List[str]] = None

    #: Configuration for memory dump triggers. Used only when "memory-infra" category is enabled.
    memory_dump_config: typing.Optional[MemoryDumpConfig] = None

    def to_json(self):
        json = dict()
        if self.record_mode is not None:
            json['recordMode'] = self.record_mode
        if self.trace_buffer_size_in_kb is not None:
            json['traceBufferSizeInKb'] = self.trace_buffer_size_in_kb
        if self.enable_sampling is not None:
            json['enableSampling'] = self.enable_sampling
        if self.enable_systrace is not None:
            json['enableSystrace'] = self.enable_systrace
        if self.enable_argument_filter is not None:
            json['enableArgumentFilter'] = self.enable_argument_filter
        if self.included_categories is not None:
            json['includedCategories'] = [i for i in self.included_categories]
        if self.excluded_categories is not None:
            json['excludedCategories'] = [i for i in self.excluded_categories]
        if self.synthetic_delays is not None:
            json['syntheticDelays'] = [i for i in self.synthetic_delays]
        if self.memory_dump_config is not None:
            json['memoryDumpConfig'] = self.memory_dump_config.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            record_mode=str(json['recordMode']) if 'recordMode' in json else None,
            trace_buffer_size_in_kb=float(json['traceBufferSizeInKb']) if 'traceBufferSizeInKb' in json else None,
            enable_sampling=bool(json['enableSampling']) if 'enableSampling' in json else None,
            enable_systrace=bool(json['enableSystrace']) if 'enableSystrace' in json else None,
            enable_argument_filter=bool(json['enableArgumentFilter']) if 'enableArgumentFilter' in json else None,
            included_categories=[str(i) for i in json['includedCategories']] if 'includedCategories' in json else None,
            excluded_categories=[str(i) for i in json['excludedCategories']] if 'excludedCategories' in json else None,
            synthetic_delays=[str(i) for i in json['syntheticDelays']] if 'syntheticDelays' in json else None,
            memory_dump_config=MemoryDumpConfig.from_json(json['memoryDumpConfig']) if 'memoryDumpConfig' in json else None,
        )


class StreamFormat(enum.Enum):
    '''
    Data format of a trace. Can be either the legacy JSON format or the
    protocol buffer format. Note that the JSON format will be deprecated soon.
    '''
    JSON = "json"
    PROTO = "proto"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class StreamCompression(enum.Enum):
    '''
    Compression type to use for traces returned via streams.
    '''
    NONE = "none"
    GZIP = "gzip"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MemoryDumpLevelOfDetail(enum.Enum):
    '''
    Details exposed when memory request explicitly declared.
    Keep consistent with memory_dump_request_args.h and
    memory_instrumentation.mojom
    '''
    BACKGROUND = "background"
    LIGHT = "light"
    DETAILED = "detailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class TracingBackend(enum.Enum):
    '''
    Backend type to use for tracing. ``chrome`` uses the Chrome-integrated
    tracing service and is supported on all platforms. ``system`` is only
    supported on Chrome OS and uses the Perfetto system tracing service.
    ``auto`` chooses ``system`` when the perfettoConfig provided to Tracing.start
    specifies at least one non-Chrome data source; otherwise uses ``chrome``.
    '''
    AUTO = "auto"
    CHROME = "chrome"
    SYSTEM = "system"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def end() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop trace events collection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.end',
    }
    json = yield cmd_dict


def get_categories() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Gets supported tracing categories.

    **EXPERIMENTAL**

    :returns: A list of supported tracing categories.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.getCategories',
    }
    json = yield cmd_dict
    return [str(i) for i in json['categories']]


def record_clock_sync_marker(
        sync_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Record a clock sync marker in the trace.

    **EXPERIMENTAL**

    :param sync_id: The ID of this clock sync marker
    '''
    params: T_JSON_DICT = dict()
    params['syncId'] = sync_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.recordClockSyncMarker',
        'params': params,
    }
    json = yield cmd_dict


def request_memory_dump(
        deterministic: typing.Optional[bool] = None,
        level_of_detail: typing.Optional[MemoryDumpLevelOfDetail] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Request a global memory dump.

    **EXPERIMENTAL**

    :param deterministic: *(Optional)* Enables more deterministic results by forcing garbage collection
    :param level_of_detail: *(Optional)* Specifies level of details in memory dump. Defaults to "detailed".
    :returns: A tuple with the following items:

        0. **dumpGuid** - GUID of the resulting global memory dump.
        1. **success** - True iff the global memory dump succeeded.
    '''
    params: T_JSON_DICT = dict()
    if deterministic is not None:
        params['deterministic'] = deterministic
    if level_of_detail is not None:
        params['levelOfDetail'] = level_of_detail.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.requestMemoryDump',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['dumpGuid']),
        bool(json['success'])
    )


def start(
        categories: typing.Optional[str] = None,
        options: typing.Optional[str] = None,
        buffer_usage_reporting_interval: typing.Optional[float] = None,
        transfer_mode: typing.Optional[str] = None,
        stream_format: typing.Optional[StreamFormat] = None,
        stream_compression: typing.Optional[StreamCompression] = None,
        trace_config: typing.Optional[TraceConfig] = None,
        perfetto_config: typing.Optional[str] = None,
        tracing_backend: typing.Optional[TracingBackend] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start trace events collection.

    :param categories: **(EXPERIMENTAL)** *(Optional)* Category/tag filter
    :param options: **(EXPERIMENTAL)** *(Optional)* Tracing options
    :param buffer_usage_reporting_interval: **(EXPERIMENTAL)** *(Optional)* If set, the agent will issue bufferUsage events at this interval, specified in milliseconds
    :param transfer_mode: *(Optional)* Whether to report trace events as series of dataCollected events or to save trace to a stream (defaults to ```ReportEvents````).
    :param stream_format: *(Optional)* Trace data format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````json````).
    :param stream_compression: **(EXPERIMENTAL)** *(Optional)* Compression format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````none````)
    :param trace_config: *(Optional)*
    :param perfetto_config: **(EXPERIMENTAL)** *(Optional)* Base64-encoded serialized perfetto.protos.TraceConfig protobuf message When specified, the parameters ````categories````, ````options````, ````traceConfig```` are ignored.
    :param tracing_backend: **(EXPERIMENTAL)** *(Optional)* Backend type (defaults to ````auto```)
    '''
    params: T_JSON_DICT = dict()
    if categories is not None:
        params['categories'] = categories
    if options is not None:
        params['options'] = options
    if buffer_usage_reporting_interval is not None:
        params['bufferUsageReportingInterval'] = buffer_usage_reporting_interval
    if transfer_mode is not None:
        params['transferMode'] = transfer_mode
    if stream_format is not None:
        params['streamFormat'] = stream_format.to_json()
    if stream_compression is not None:
        params['streamCompression'] = stream_compression.to_json()
    if trace_config is not None:
        params['traceConfig'] = trace_config.to_json()
    if perfetto_config is not None:
        params['perfettoConfig'] = perfetto_config
    if tracing_backend is not None:
        params['tracingBackend'] = tracing_backend.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.start',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Tracing.bufferUsage')
@dataclass
class BufferUsage:
    '''
    **EXPERIMENTAL**


    '''
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    percent_full: typing.Optional[float]
    #: An approximate number of events in the trace log.
    event_count: typing.Optional[float]
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    value: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BufferUsage:
        return cls(
            percent_full=float(json['percentFull']) if 'percentFull' in json else None,
            event_count=float(json['eventCount']) if 'eventCount' in json else None,
            value=float(json['value']) if 'value' in json else None
        )


@event_class('Tracing.dataCollected')
@dataclass
class DataCollected:
    '''
    **EXPERIMENTAL**

    Contains a bucket of collected trace events. When tracing is stopped collected events will be
    sent as a sequence of dataCollected events followed by tracingComplete event.
    '''
    value: typing.List[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DataCollected:
        return cls(
            value=[dict(i) for i in json['value']]
        )


@event_class('Tracing.tracingComplete')
@dataclass
class TracingComplete:
    '''
    Signals that tracing is stopped and there is no trace buffers pending flush, all data were
    delivered via dataCollected events.
    '''
    #: Indicates whether some trace data is known to have been lost, e.g. because the trace ring
    #: buffer wrapped around.
    data_loss_occurred: bool
    #: A handle of the stream that holds resulting trace data.
    stream: typing.Optional[io.StreamHandle]
    #: Trace data format of returned stream.
    trace_format: typing.Optional[StreamFormat]
    #: Compression format of returned stream.
    stream_compression: typing.Optional[StreamCompression]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TracingComplete:
        return cls(
            data_loss_occurred=bool(json['dataLossOccurred']),
            stream=io.StreamHandle.from_json(json['stream']) if 'stream' in json else None,
            trace_format=StreamFormat.from_json(json['traceFormat']) if 'traceFormat' in json else None,
            stream_compression=StreamCompression.from_json(json['streamCompression']) if 'streamCompression' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\tracing.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Tracing
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io


class MemoryDumpConfig(dict):
    '''
    Configuration for memory dump. Used only when "memory-infra" category is enabled.
    '''
    def to_json(self) -> dict:
        return self

    @classmethod
    def from_json(cls, json: dict) -> MemoryDumpConfig:
        return cls(json)

    def __repr__(self):
        return 'MemoryDumpConfig({})'.format(super().__repr__())


@dataclass
class TraceConfig:
    #: Controls how the trace buffer stores data.
    record_mode: typing.Optional[str] = None

    #: Size of the trace buffer in kilobytes. If not specified or zero is passed, a default value
    #: of 200 MB would be used.
    trace_buffer_size_in_kb: typing.Optional[float] = None

    #: Turns on JavaScript stack sampling.
    enable_sampling: typing.Optional[bool] = None

    #: Turns on system tracing.
    enable_systrace: typing.Optional[bool] = None

    #: Turns on argument filter.
    enable_argument_filter: typing.Optional[bool] = None

    #: Included category filters.
    included_categories: typing.Optional[typing.List[str]] = None

    #: Excluded category filters.
    excluded_categories: typing.Optional[typing.List[str]] = None

    #: Configuration to synthesize the delays in tracing.
    synthetic_delays: typing.Optional[typing.List[str]] = None

    #: Configuration for memory dump triggers. Used only when "memory-infra" category is enabled.
    memory_dump_config: typing.Optional[MemoryDumpConfig] = None

    def to_json(self):
        json = dict()
        if self.record_mode is not None:
            json['recordMode'] = self.record_mode
        if self.trace_buffer_size_in_kb is not None:
            json['traceBufferSizeInKb'] = self.trace_buffer_size_in_kb
        if self.enable_sampling is not None:
            json['enableSampling'] = self.enable_sampling
        if self.enable_systrace is not None:
            json['enableSystrace'] = self.enable_systrace
        if self.enable_argument_filter is not None:
            json['enableArgumentFilter'] = self.enable_argument_filter
        if self.included_categories is not None:
            json['includedCategories'] = [i for i in self.included_categories]
        if self.excluded_categories is not None:
            json['excludedCategories'] = [i for i in self.excluded_categories]
        if self.synthetic_delays is not None:
            json['syntheticDelays'] = [i for i in self.synthetic_delays]
        if self.memory_dump_config is not None:
            json['memoryDumpConfig'] = self.memory_dump_config.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            record_mode=str(json['recordMode']) if 'recordMode' in json else None,
            trace_buffer_size_in_kb=float(json['traceBufferSizeInKb']) if 'traceBufferSizeInKb' in json else None,
            enable_sampling=bool(json['enableSampling']) if 'enableSampling' in json else None,
            enable_systrace=bool(json['enableSystrace']) if 'enableSystrace' in json else None,
            enable_argument_filter=bool(json['enableArgumentFilter']) if 'enableArgumentFilter' in json else None,
            included_categories=[str(i) for i in json['includedCategories']] if 'includedCategories' in json else None,
            excluded_categories=[str(i) for i in json['excludedCategories']] if 'excludedCategories' in json else None,
            synthetic_delays=[str(i) for i in json['syntheticDelays']] if 'syntheticDelays' in json else None,
            memory_dump_config=MemoryDumpConfig.from_json(json['memoryDumpConfig']) if 'memoryDumpConfig' in json else None,
        )


class StreamFormat(enum.Enum):
    '''
    Data format of a trace. Can be either the legacy JSON format or the
    protocol buffer format. Note that the JSON format will be deprecated soon.
    '''
    JSON = "json"
    PROTO = "proto"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class StreamCompression(enum.Enum):
    '''
    Compression type to use for traces returned via streams.
    '''
    NONE = "none"
    GZIP = "gzip"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MemoryDumpLevelOfDetail(enum.Enum):
    '''
    Details exposed when memory request explicitly declared.
    Keep consistent with memory_dump_request_args.h and
    memory_instrumentation.mojom
    '''
    BACKGROUND = "background"
    LIGHT = "light"
    DETAILED = "detailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class TracingBackend(enum.Enum):
    '''
    Backend type to use for tracing. ``chrome`` uses the Chrome-integrated
    tracing service and is supported on all platforms. ``system`` is only
    supported on Chrome OS and uses the Perfetto system tracing service.
    ``auto`` chooses ``system`` when the perfettoConfig provided to Tracing.start
    specifies at least one non-Chrome data source; otherwise uses ``chrome``.
    '''
    AUTO = "auto"
    CHROME = "chrome"
    SYSTEM = "system"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def end() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop trace events collection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.end',
    }
    json = yield cmd_dict


def get_categories() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Gets supported tracing categories.

    **EXPERIMENTAL**

    :returns: A list of supported tracing categories.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.getCategories',
    }
    json = yield cmd_dict
    return [str(i) for i in json['categories']]


def record_clock_sync_marker(
        sync_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Record a clock sync marker in the trace.

    **EXPERIMENTAL**

    :param sync_id: The ID of this clock sync marker
    '''
    params: T_JSON_DICT = dict()
    params['syncId'] = sync_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.recordClockSyncMarker',
        'params': params,
    }
    json = yield cmd_dict


def request_memory_dump(
        deterministic: typing.Optional[bool] = None,
        level_of_detail: typing.Optional[MemoryDumpLevelOfDetail] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Request a global memory dump.

    **EXPERIMENTAL**

    :param deterministic: *(Optional)* Enables more deterministic results by forcing garbage collection
    :param level_of_detail: *(Optional)* Specifies level of details in memory dump. Defaults to "detailed".
    :returns: A tuple with the following items:

        0. **dumpGuid** - GUID of the resulting global memory dump.
        1. **success** - True iff the global memory dump succeeded.
    '''
    params: T_JSON_DICT = dict()
    if deterministic is not None:
        params['deterministic'] = deterministic
    if level_of_detail is not None:
        params['levelOfDetail'] = level_of_detail.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.requestMemoryDump',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['dumpGuid']),
        bool(json['success'])
    )


def start(
        categories: typing.Optional[str] = None,
        options: typing.Optional[str] = None,
        buffer_usage_reporting_interval: typing.Optional[float] = None,
        transfer_mode: typing.Optional[str] = None,
        stream_format: typing.Optional[StreamFormat] = None,
        stream_compression: typing.Optional[StreamCompression] = None,
        trace_config: typing.Optional[TraceConfig] = None,
        perfetto_config: typing.Optional[str] = None,
        tracing_backend: typing.Optional[TracingBackend] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start trace events collection.

    :param categories: **(EXPERIMENTAL)** *(Optional)* Category/tag filter
    :param options: **(EXPERIMENTAL)** *(Optional)* Tracing options
    :param buffer_usage_reporting_interval: **(EXPERIMENTAL)** *(Optional)* If set, the agent will issue bufferUsage events at this interval, specified in milliseconds
    :param transfer_mode: *(Optional)* Whether to report trace events as series of dataCollected events or to save trace to a stream (defaults to ```ReportEvents````).
    :param stream_format: *(Optional)* Trace data format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````json````).
    :param stream_compression: **(EXPERIMENTAL)** *(Optional)* Compression format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````none````)
    :param trace_config: *(Optional)*
    :param perfetto_config: **(EXPERIMENTAL)** *(Optional)* Base64-encoded serialized perfetto.protos.TraceConfig protobuf message When specified, the parameters ````categories````, ````options````, ````traceConfig```` are ignored.
    :param tracing_backend: **(EXPERIMENTAL)** *(Optional)* Backend type (defaults to ````auto```)
    '''
    params: T_JSON_DICT = dict()
    if categories is not None:
        params['categories'] = categories
    if options is not None:
        params['options'] = options
    if buffer_usage_reporting_interval is not None:
        params['bufferUsageReportingInterval'] = buffer_usage_reporting_interval
    if transfer_mode is not None:
        params['transferMode'] = transfer_mode
    if stream_format is not None:
        params['streamFormat'] = stream_format.to_json()
    if stream_compression is not None:
        params['streamCompression'] = stream_compression.to_json()
    if trace_config is not None:
        params['traceConfig'] = trace_config.to_json()
    if perfetto_config is not None:
        params['perfettoConfig'] = perfetto_config
    if tracing_backend is not None:
        params['tracingBackend'] = tracing_backend.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.start',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Tracing.bufferUsage')
@dataclass
class BufferUsage:
    '''
    **EXPERIMENTAL**


    '''
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    percent_full: typing.Optional[float]
    #: An approximate number of events in the trace log.
    event_count: typing.Optional[float]
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    value: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BufferUsage:
        return cls(
            percent_full=float(json['percentFull']) if 'percentFull' in json else None,
            event_count=float(json['eventCount']) if 'eventCount' in json else None,
            value=float(json['value']) if 'value' in json else None
        )


@event_class('Tracing.dataCollected')
@dataclass
class DataCollected:
    '''
    **EXPERIMENTAL**

    Contains a bucket of collected trace events. When tracing is stopped collected events will be
    sent as a sequence of dataCollected events followed by tracingComplete event.
    '''
    value: typing.List[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DataCollected:
        return cls(
            value=[dict(i) for i in json['value']]
        )


@event_class('Tracing.tracingComplete')
@dataclass
class TracingComplete:
    '''
    Signals that tracing is stopped and there is no trace buffers pending flush, all data were
    delivered via dataCollected events.
    '''
    #: Indicates whether some trace data is known to have been lost, e.g. because the trace ring
    #: buffer wrapped around.
    data_loss_occurred: bool
    #: A handle of the stream that holds resulting trace data.
    stream: typing.Optional[io.StreamHandle]
    #: Trace data format of returned stream.
    trace_format: typing.Optional[StreamFormat]
    #: Compression format of returned stream.
    stream_compression: typing.Optional[StreamCompression]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TracingComplete:
        return cls(
            data_loss_occurred=bool(json['dataLossOccurred']),
            stream=io.StreamHandle.from_json(json['stream']) if 'stream' in json else None,
            trace_format=StreamFormat.from_json(json['traceFormat']) if 'traceFormat' in json else None,
            stream_compression=StreamCompression.from_json(json['streamCompression']) if 'streamCompression' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\tracing.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Tracing
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io


class MemoryDumpConfig(dict):
    '''
    Configuration for memory dump. Used only when "memory-infra" category is enabled.
    '''
    def to_json(self) -> dict:
        return self

    @classmethod
    def from_json(cls, json: dict) -> MemoryDumpConfig:
        return cls(json)

    def __repr__(self):
        return 'MemoryDumpConfig({})'.format(super().__repr__())


@dataclass
class TraceConfig:
    #: Controls how the trace buffer stores data.
    record_mode: typing.Optional[str] = None

    #: Size of the trace buffer in kilobytes. If not specified or zero is passed, a default value
    #: of 200 MB would be used.
    trace_buffer_size_in_kb: typing.Optional[float] = None

    #: Turns on JavaScript stack sampling.
    enable_sampling: typing.Optional[bool] = None

    #: Turns on system tracing.
    enable_systrace: typing.Optional[bool] = None

    #: Turns on argument filter.
    enable_argument_filter: typing.Optional[bool] = None

    #: Included category filters.
    included_categories: typing.Optional[typing.List[str]] = None

    #: Excluded category filters.
    excluded_categories: typing.Optional[typing.List[str]] = None

    #: Configuration to synthesize the delays in tracing.
    synthetic_delays: typing.Optional[typing.List[str]] = None

    #: Configuration for memory dump triggers. Used only when "memory-infra" category is enabled.
    memory_dump_config: typing.Optional[MemoryDumpConfig] = None

    def to_json(self):
        json = dict()
        if self.record_mode is not None:
            json['recordMode'] = self.record_mode
        if self.trace_buffer_size_in_kb is not None:
            json['traceBufferSizeInKb'] = self.trace_buffer_size_in_kb
        if self.enable_sampling is not None:
            json['enableSampling'] = self.enable_sampling
        if self.enable_systrace is not None:
            json['enableSystrace'] = self.enable_systrace
        if self.enable_argument_filter is not None:
            json['enableArgumentFilter'] = self.enable_argument_filter
        if self.included_categories is not None:
            json['includedCategories'] = [i for i in self.included_categories]
        if self.excluded_categories is not None:
            json['excludedCategories'] = [i for i in self.excluded_categories]
        if self.synthetic_delays is not None:
            json['syntheticDelays'] = [i for i in self.synthetic_delays]
        if self.memory_dump_config is not None:
            json['memoryDumpConfig'] = self.memory_dump_config.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            record_mode=str(json['recordMode']) if 'recordMode' in json else None,
            trace_buffer_size_in_kb=float(json['traceBufferSizeInKb']) if 'traceBufferSizeInKb' in json else None,
            enable_sampling=bool(json['enableSampling']) if 'enableSampling' in json else None,
            enable_systrace=bool(json['enableSystrace']) if 'enableSystrace' in json else None,
            enable_argument_filter=bool(json['enableArgumentFilter']) if 'enableArgumentFilter' in json else None,
            included_categories=[str(i) for i in json['includedCategories']] if 'includedCategories' in json else None,
            excluded_categories=[str(i) for i in json['excludedCategories']] if 'excludedCategories' in json else None,
            synthetic_delays=[str(i) for i in json['syntheticDelays']] if 'syntheticDelays' in json else None,
            memory_dump_config=MemoryDumpConfig.from_json(json['memoryDumpConfig']) if 'memoryDumpConfig' in json else None,
        )


class StreamFormat(enum.Enum):
    '''
    Data format of a trace. Can be either the legacy JSON format or the
    protocol buffer format. Note that the JSON format will be deprecated soon.
    '''
    JSON = "json"
    PROTO = "proto"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class StreamCompression(enum.Enum):
    '''
    Compression type to use for traces returned via streams.
    '''
    NONE = "none"
    GZIP = "gzip"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MemoryDumpLevelOfDetail(enum.Enum):
    '''
    Details exposed when memory request explicitly declared.
    Keep consistent with memory_dump_request_args.h and
    memory_instrumentation.mojom
    '''
    BACKGROUND = "background"
    LIGHT = "light"
    DETAILED = "detailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class TracingBackend(enum.Enum):
    '''
    Backend type to use for tracing. ``chrome`` uses the Chrome-integrated
    tracing service and is supported on all platforms. ``system`` is only
    supported on Chrome OS and uses the Perfetto system tracing service.
    ``auto`` chooses ``system`` when the perfettoConfig provided to Tracing.start
    specifies at least one non-Chrome data source; otherwise uses ``chrome``.
    '''
    AUTO = "auto"
    CHROME = "chrome"
    SYSTEM = "system"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def end() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop trace events collection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.end',
    }
    json = yield cmd_dict


def get_categories() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Gets supported tracing categories.

    **EXPERIMENTAL**

    :returns: A list of supported tracing categories.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.getCategories',
    }
    json = yield cmd_dict
    return [str(i) for i in json['categories']]


def record_clock_sync_marker(
        sync_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Record a clock sync marker in the trace.

    **EXPERIMENTAL**

    :param sync_id: The ID of this clock sync marker
    '''
    params: T_JSON_DICT = dict()
    params['syncId'] = sync_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.recordClockSyncMarker',
        'params': params,
    }
    json = yield cmd_dict


def request_memory_dump(
        deterministic: typing.Optional[bool] = None,
        level_of_detail: typing.Optional[MemoryDumpLevelOfDetail] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Request a global memory dump.

    **EXPERIMENTAL**

    :param deterministic: *(Optional)* Enables more deterministic results by forcing garbage collection
    :param level_of_detail: *(Optional)* Specifies level of details in memory dump. Defaults to "detailed".
    :returns: A tuple with the following items:

        0. **dumpGuid** - GUID of the resulting global memory dump.
        1. **success** - True iff the global memory dump succeeded.
    '''
    params: T_JSON_DICT = dict()
    if deterministic is not None:
        params['deterministic'] = deterministic
    if level_of_detail is not None:
        params['levelOfDetail'] = level_of_detail.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.requestMemoryDump',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['dumpGuid']),
        bool(json['success'])
    )


def start(
        categories: typing.Optional[str] = None,
        options: typing.Optional[str] = None,
        buffer_usage_reporting_interval: typing.Optional[float] = None,
        transfer_mode: typing.Optional[str] = None,
        stream_format: typing.Optional[StreamFormat] = None,
        stream_compression: typing.Optional[StreamCompression] = None,
        trace_config: typing.Optional[TraceConfig] = None,
        perfetto_config: typing.Optional[str] = None,
        tracing_backend: typing.Optional[TracingBackend] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start trace events collection.

    :param categories: **(EXPERIMENTAL)** *(Optional)* Category/tag filter
    :param options: **(EXPERIMENTAL)** *(Optional)* Tracing options
    :param buffer_usage_reporting_interval: **(EXPERIMENTAL)** *(Optional)* If set, the agent will issue bufferUsage events at this interval, specified in milliseconds
    :param transfer_mode: *(Optional)* Whether to report trace events as series of dataCollected events or to save trace to a stream (defaults to ```ReportEvents````).
    :param stream_format: *(Optional)* Trace data format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````json````).
    :param stream_compression: **(EXPERIMENTAL)** *(Optional)* Compression format to use. This only applies when using ````ReturnAsStream```` transfer mode (defaults to ````none````)
    :param trace_config: *(Optional)*
    :param perfetto_config: **(EXPERIMENTAL)** *(Optional)* Base64-encoded serialized perfetto.protos.TraceConfig protobuf message When specified, the parameters ````categories````, ````options````, ````traceConfig```` are ignored.
    :param tracing_backend: **(EXPERIMENTAL)** *(Optional)* Backend type (defaults to ````auto```)
    '''
    params: T_JSON_DICT = dict()
    if categories is not None:
        params['categories'] = categories
    if options is not None:
        params['options'] = options
    if buffer_usage_reporting_interval is not None:
        params['bufferUsageReportingInterval'] = buffer_usage_reporting_interval
    if transfer_mode is not None:
        params['transferMode'] = transfer_mode
    if stream_format is not None:
        params['streamFormat'] = stream_format.to_json()
    if stream_compression is not None:
        params['streamCompression'] = stream_compression.to_json()
    if trace_config is not None:
        params['traceConfig'] = trace_config.to_json()
    if perfetto_config is not None:
        params['perfettoConfig'] = perfetto_config
    if tracing_backend is not None:
        params['tracingBackend'] = tracing_backend.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Tracing.start',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Tracing.bufferUsage')
@dataclass
class BufferUsage:
    '''
    **EXPERIMENTAL**


    '''
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    percent_full: typing.Optional[float]
    #: An approximate number of events in the trace log.
    event_count: typing.Optional[float]
    #: A number in range [0..1] that indicates the used size of event buffer as a fraction of its
    #: total size.
    value: typing.Optional[float]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BufferUsage:
        return cls(
            percent_full=float(json['percentFull']) if 'percentFull' in json else None,
            event_count=float(json['eventCount']) if 'eventCount' in json else None,
            value=float(json['value']) if 'value' in json else None
        )


@event_class('Tracing.dataCollected')
@dataclass
class DataCollected:
    '''
    **EXPERIMENTAL**

    Contains a bucket of collected trace events. When tracing is stopped collected events will be
    sent as a sequence of dataCollected events followed by tracingComplete event.
    '''
    value: typing.List[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DataCollected:
        return cls(
            value=[dict(i) for i in json['value']]
        )


@event_class('Tracing.tracingComplete')
@dataclass
class TracingComplete:
    '''
    Signals that tracing is stopped and there is no trace buffers pending flush, all data were
    delivered via dataCollected events.
    '''
    #: Indicates whether some trace data is known to have been lost, e.g. because the trace ring
    #: buffer wrapped around.
    data_loss_occurred: bool
    #: A handle of the stream that holds resulting trace data.
    stream: typing.Optional[io.StreamHandle]
    #: Trace data format of returned stream.
    trace_format: typing.Optional[StreamFormat]
    #: Compression format of returned stream.
    stream_compression: typing.Optional[StreamCompression]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TracingComplete:
        return cls(
            data_loss_occurred=bool(json['dataLossOccurred']),
            stream=io.StreamHandle.from_json(json['stream']) if 'stream' in json else None,
            trace_format=StreamFormat.from_json(json['traceFormat']) if 'traceFormat' in json else None,
            stream_compression=StreamCompression.from_json(json['streamCompression']) if 'streamCompression' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\aiohttp\client_proto.py ===
import asyncio
from contextlib import suppress
from typing import Any, Optional, Tuple, Union

from .base_protocol import BaseProtocol
from .client_exceptions import (
    ClientConnectionError,
    ClientOSError,
    ClientPayloadError,
    ServerDisconnectedError,
    SocketTimeoutError,
)
from .helpers import (
    _EXC_SENTINEL,
    EMPTY_BODY_STATUS_CODES,
    BaseTimerContext,
    set_exception,
    set_result,
)
from .http import HttpResponseParser, RawResponseMessage
from .http_exceptions import HttpProcessingError
from .streams import EMPTY_PAYLOAD, DataQueue, StreamReader


class ResponseHandler(BaseProtocol, DataQueue[Tuple[RawResponseMessage, StreamReader]]):
    """Helper class to adapt between Protocol and StreamReader."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        BaseProtocol.__init__(self, loop=loop)
        DataQueue.__init__(self, loop)

        self._should_close = False

        self._payload: Optional[StreamReader] = None
        self._skip_payload = False
        self._payload_parser = None

        self._timer = None

        self._tail = b""
        self._upgraded = False
        self._parser: Optional[HttpResponseParser] = None

        self._read_timeout: Optional[float] = None
        self._read_timeout_handle: Optional[asyncio.TimerHandle] = None

        self._timeout_ceil_threshold: Optional[float] = 5

        self._closed: Union[None, asyncio.Future[None]] = None
        self._connection_lost_called = False

    @property
    def closed(self) -> Union[None, asyncio.Future[None]]:
        """Future that is set when the connection is closed.

        This property returns a Future that will be completed when the connection
        is closed. The Future is created lazily on first access to avoid creating
        futures that will never be awaited.

        Returns:
            - A Future[None] if the connection is still open or was closed after
              this property was accessed
            - None if connection_lost() was already called before this property
              was ever accessed (indicating no one is waiting for the closure)
        """
        if self._closed is None and not self._connection_lost_called:
            self._closed = self._loop.create_future()
        return self._closed

    @property
    def upgraded(self) -> bool:
        return self._upgraded

    @property
    def should_close(self) -> bool:
        return bool(
            self._should_close
            or (self._payload is not None and not self._payload.is_eof())
            or self._upgraded
            or self._exception is not None
            or self._payload_parser is not None
            or self._buffer
            or self._tail
        )

    def force_close(self) -> None:
        self._should_close = True

    def close(self) -> None:
        self._exception = None  # Break cyclic references
        transport = self.transport
        if transport is not None:
            transport.close()
            self.transport = None
            self._payload = None
            self._drop_timeout()

    def abort(self) -> None:
        self._exception = None  # Break cyclic references
        transport = self.transport
        if transport is not None:
            transport.abort()
            self.transport = None
            self._payload = None
            self._drop_timeout()

    def is_connected(self) -> bool:
        return self.transport is not None and not self.transport.is_closing()

    def connection_lost(self, exc: Optional[BaseException]) -> None:
        self._connection_lost_called = True
        self._drop_timeout()

        original_connection_error = exc
        reraised_exc = original_connection_error

        connection_closed_cleanly = original_connection_error is None

        if self._closed is not None:
            # If someone is waiting for the closed future,
            # we should set it to None or an exception. If
            # self._closed is None, it means that
            # connection_lost() was called already
            # or nobody is waiting for it.
            if connection_closed_cleanly:
                set_result(self._closed, None)
            else:
                assert original_connection_error is not None
                set_exception(
                    self._closed,
                    ClientConnectionError(
                        f"Connection lost: {original_connection_error !s}",
                    ),
                    original_connection_error,
                )

        if self._payload_parser is not None:
            with suppress(Exception):  # FIXME: log this somehow?
                self._payload_parser.feed_eof()

        uncompleted = None
        if self._parser is not None:
            try:
                uncompleted = self._parser.feed_eof()
            except Exception as underlying_exc:
                if self._payload is not None:
                    client_payload_exc_msg = (
                        f"Response payload is not completed: {underlying_exc !r}"
                    )
                    if not connection_closed_cleanly:
                        client_payload_exc_msg = (
                            f"{client_payload_exc_msg !s}. "
                            f"{original_connection_error !r}"
                        )
                    set_exception(
                        self._payload,
                        ClientPayloadError(client_payload_exc_msg),
                        underlying_exc,
                    )

        if not self.is_eof():
            if isinstance(original_connection_error, OSError):
                reraised_exc = ClientOSError(*original_connection_error.args)
            if connection_closed_cleanly:
                reraised_exc = ServerDisconnectedError(uncompleted)
            # assigns self._should_close to True as side effect,
            # we do it anyway below
            underlying_non_eof_exc = (
                _EXC_SENTINEL
                if connection_closed_cleanly
                else original_connection_error
            )
            assert underlying_non_eof_exc is not None
            assert reraised_exc is not None
            self.set_exception(reraised_exc, underlying_non_eof_exc)

        self._should_close = True
        self._parser = None
        self._payload = None
        self._payload_parser = None
        self._reading_paused = False

        super().connection_lost(reraised_exc)

    def eof_received(self) -> None:
        # should call parser.feed_eof() most likely
        self._drop_timeout()

    def pause_reading(self) -> None:
        super().pause_reading()
        self._drop_timeout()

    def resume_reading(self) -> None:
        super().resume_reading()
        self._reschedule_timeout()

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = _EXC_SENTINEL,
    ) -> None:
        self._should_close = True
        self._drop_timeout()
        super().set_exception(exc, exc_cause)

    def set_parser(self, parser: Any, payload: Any) -> None:
        # TODO: actual types are:
        #   parser: WebSocketReader
        #   payload: WebSocketDataQueue
        # but they are not generi enough
        # Need an ABC for both types
        self._payload = payload
        self._payload_parser = parser

        self._drop_timeout()

        if self._tail:
            data, self._tail = self._tail, b""
            self.data_received(data)

    def set_response_params(
        self,
        *,
        timer: Optional[BaseTimerContext] = None,
        skip_payload: bool = False,
        read_until_eof: bool = False,
        auto_decompress: bool = True,
        read_timeout: Optional[float] = None,
        read_bufsize: int = 2**16,
        timeout_ceil_threshold: float = 5,
        max_line_size: int = 8190,
        max_field_size: int = 8190,
    ) -> None:
        self._skip_payload = skip_payload

        self._read_timeout = read_timeout

        self._timeout_ceil_threshold = timeout_ceil_threshold

        self._parser = HttpResponseParser(
            self,
            self._loop,
            read_bufsize,
            timer=timer,
            payload_exception=ClientPayloadError,
            response_with_body=not skip_payload,
            read_until_eof=read_until_eof,
            auto_decompress=auto_decompress,
            max_line_size=max_line_size,
            max_field_size=max_field_size,
        )

        if self._tail:
            data, self._tail = self._tail, b""
            self.data_received(data)

    def _drop_timeout(self) -> None:
        if self._read_timeout_handle is not None:
            self._read_timeout_handle.cancel()
            self._read_timeout_handle = None

    def _reschedule_timeout(self) -> None:
        timeout = self._read_timeout
        if self._read_timeout_handle is not None:
            self._read_timeout_handle.cancel()

        if timeout:
            self._read_timeout_handle = self._loop.call_later(
                timeout, self._on_read_timeout
            )
        else:
            self._read_timeout_handle = None

    def start_timeout(self) -> None:
        self._reschedule_timeout()

    @property
    def read_timeout(self) -> Optional[float]:
        return self._read_timeout

    @read_timeout.setter
    def read_timeout(self, read_timeout: Optional[float]) -> None:
        self._read_timeout = read_timeout

    def _on_read_timeout(self) -> None:
        exc = SocketTimeoutError("Timeout on reading data from socket")
        self.set_exception(exc)
        if self._payload is not None:
            set_exception(self._payload, exc)

    def data_received(self, data: bytes) -> None:
        self._reschedule_timeout()

        if not data:
            return

        # custom payload parser - currently always WebSocketReader
        if self._payload_parser is not None:
            eof, tail = self._payload_parser.feed_data(data)
            if eof:
                self._payload = None
                self._payload_parser = None

                if tail:
                    self.data_received(tail)
            return

        if self._upgraded or self._parser is None:
            # i.e. websocket connection, websocket parser is not set yet
            self._tail += data
            return

        # parse http messages
        try:
            messages, upgraded, tail = self._parser.feed_data(data)
        except BaseException as underlying_exc:
            if self.transport is not None:
                # connection.release() could be called BEFORE
                # data_received(), the transport is already
                # closed in this case
                self.transport.close()
            # should_close is True after the call
            if isinstance(underlying_exc, HttpProcessingError):
                exc = HttpProcessingError(
                    code=underlying_exc.code,
                    message=underlying_exc.message,
                    headers=underlying_exc.headers,
                )
            else:
                exc = HttpProcessingError()
            self.set_exception(exc, underlying_exc)
            return

        self._upgraded = upgraded

        payload: Optional[StreamReader] = None
        for message, payload in messages:
            if message.should_close:
                self._should_close = True

            self._payload = payload

            if self._skip_payload or message.code in EMPTY_BODY_STATUS_CODES:
                self.feed_data((message, EMPTY_PAYLOAD), 0)
            else:
                self.feed_data((message, payload), 0)

        if payload is not None:
            # new message(s) was processed
            # register timeout handler unsubscribing
            # either on end-of-stream or immediately for
            # EMPTY_PAYLOAD
            if payload is not EMPTY_PAYLOAD:
                payload.on_eof(self._drop_timeout)
            else:
                self._drop_timeout()

        if upgraded and tail:
            self.data_received(tail)

# === NexusCore/openenv\Lib\site-packages\litellm\rerank_api\main.py ===
import asyncio
import contextvars
from functools import partial
from typing import Any, Coroutine, Dict, List, Literal, Optional, Union

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.rerank.transformation import BaseRerankConfig
from litellm.llms.bedrock.rerank.handler import BedrockRerankHandler
from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from litellm.llms.together_ai.rerank.handler import TogetherAIRerank
from litellm.rerank_api.rerank_utils import get_optional_rerank_params
from litellm.secret_managers.main import get_secret, get_secret_str
from litellm.types.rerank import OptionalRerankParams, RerankResponse
from litellm.types.router import *
from litellm.utils import ProviderConfigManager, client, exception_type

####### ENVIRONMENT VARIABLES ###################
# Initialize any necessary instances or variables here
together_rerank = TogetherAIRerank()
bedrock_rerank = BedrockRerankHandler()
base_llm_http_handler = BaseLLMHTTPHandler()
#################################################


@client
async def arerank(
    model: str,
    query: str,
    documents: List[Union[str, Dict[str, Any]]],
    custom_llm_provider: Optional[Literal["cohere", "together_ai"]] = None,
    top_n: Optional[int] = None,
    rank_fields: Optional[List[str]] = None,
    return_documents: Optional[bool] = None,
    max_chunks_per_doc: Optional[int] = None,
    **kwargs,
) -> Union[RerankResponse, Coroutine[Any, Any, RerankResponse]]:
    """
    Async: Reranks a list of documents based on their relevance to the query
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["arerank"] = True

        func = partial(
            rerank,
            model,
            query,
            documents,
            custom_llm_provider,
            top_n,
            rank_fields,
            return_documents,
            max_chunks_per_doc,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response
    except Exception as e:
        raise e


@client
def rerank(  # noqa: PLR0915
    model: str,
    query: str,
    documents: List[Union[str, Dict[str, Any]]],
    custom_llm_provider: Optional[
        Literal["cohere", "together_ai", "azure_ai", "infinity", "litellm_proxy"]
    ] = None,
    top_n: Optional[int] = None,
    rank_fields: Optional[List[str]] = None,
    return_documents: Optional[bool] = True,
    max_chunks_per_doc: Optional[int] = None,
    max_tokens_per_doc: Optional[int] = None,
    **kwargs,
) -> Union[RerankResponse, Coroutine[Any, Any, RerankResponse]]:
    """
    Reranks a list of documents based on their relevance to the query
    """
    headers: Optional[dict] = kwargs.get("headers")  # type: ignore
    litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
    litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
    proxy_server_request = kwargs.get("proxy_server_request", None)
    model_info = kwargs.get("model_info", None)
    metadata = kwargs.get("metadata", {})
    user = kwargs.get("user", None)
    client = kwargs.get("client", None)
    try:
        _is_async = kwargs.pop("arerank", False) is True
        optional_params = GenericLiteLLMParams(**kwargs)
        # Params that are unique to specific versions of the client for the rerank call
        unique_version_params = {
            "max_chunks_per_doc": max_chunks_per_doc,
            "max_tokens_per_doc": max_tokens_per_doc,
        }
        present_version_params = [
            k for k, v in unique_version_params.items() if v is not None
        ]

        (
            model,
            _custom_llm_provider,
            dynamic_api_key,
            dynamic_api_base,
        ) = litellm.get_llm_provider(
            model=model,
            custom_llm_provider=custom_llm_provider,
            api_base=optional_params.api_base,
            api_key=optional_params.api_key,
        )

        rerank_provider_config: BaseRerankConfig = (
            ProviderConfigManager.get_provider_rerank_config(
                model=model,
                provider=litellm.LlmProviders(_custom_llm_provider),
                api_base=optional_params.api_base,
                present_version_params=present_version_params,
            )
        )

        optional_rerank_params: OptionalRerankParams = get_optional_rerank_params(
            rerank_provider_config=rerank_provider_config,
            model=model,
            drop_params=kwargs.get("drop_params") or litellm.drop_params or False,
            query=query,
            documents=documents,
            custom_llm_provider=_custom_llm_provider,
            top_n=top_n,
            rank_fields=rank_fields,
            return_documents=return_documents,
            max_chunks_per_doc=max_chunks_per_doc,
            max_tokens_per_doc=max_tokens_per_doc,
            non_default_params=kwargs,
        )

        if isinstance(optional_params.timeout, str):
            optional_params.timeout = float(optional_params.timeout)

        model_response = RerankResponse()

        litellm_logging_obj.update_environment_variables(
            model=model,
            user=user,
            optional_params=dict(optional_rerank_params),
            litellm_params={
                "litellm_call_id": litellm_call_id,
                "proxy_server_request": proxy_server_request,
                "model_info": model_info,
                "metadata": metadata,
                "preset_cache_key": None,
                "stream_response": {},
                **optional_params.model_dump(exclude_unset=True),
            },
            custom_llm_provider=_custom_llm_provider,
        )

        # Implement rerank logic here based on the custom_llm_provider
        if _custom_llm_provider == "cohere" or _custom_llm_provider == "litellm_proxy":
            # Implement Cohere rerank logic
            api_key: Optional[str] = (
                dynamic_api_key or optional_params.api_key or litellm.api_key
            )

            api_base: Optional[str] = (
                dynamic_api_base
                or optional_params.api_base
                or litellm.api_base
                or get_secret("COHERE_API_BASE")  # type: ignore
                or "https://api.cohere.com"
            )

            if api_base is None:
                raise Exception(
                    "Invalid api base. api_base=None. Set in call or via `COHERE_API_BASE` env var."
                )
            response = base_llm_http_handler.rerank(
                model=model,
                custom_llm_provider=_custom_llm_provider,
                provider_config=rerank_provider_config,
                optional_rerank_params=optional_rerank_params,
                logging_obj=litellm_logging_obj,
                timeout=optional_params.timeout,
                api_key=api_key,
                api_base=api_base,
                _is_async=_is_async,
                headers=headers or litellm.headers or {},
                client=client,
                model_response=model_response,
            )
        elif _custom_llm_provider == "azure_ai":
            api_base = (
                dynamic_api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or optional_params.api_base
                or litellm.api_base
                or get_secret("AZURE_AI_API_BASE")  # type: ignore
            )
            response = base_llm_http_handler.rerank(
                model=model,
                custom_llm_provider=_custom_llm_provider,
                optional_rerank_params=optional_rerank_params,
                provider_config=rerank_provider_config,
                logging_obj=litellm_logging_obj,
                timeout=optional_params.timeout,
                api_key=dynamic_api_key or optional_params.api_key,
                api_base=api_base,
                _is_async=_is_async,
                headers=headers or litellm.headers or {},
                client=client,
                model_response=model_response,
            )
        elif _custom_llm_provider == "infinity":
            # Implement Infinity rerank logic
            api_key = dynamic_api_key or optional_params.api_key or litellm.api_key

            api_base = (
                dynamic_api_base
                or optional_params.api_base
                or litellm.api_base
                or get_secret_str("INFINITY_API_BASE")
            )

            if api_base is None:
                raise Exception(
                    "Invalid api base. api_base=None. Set in call or via `INFINITY_API_BASE` env var."
                )

            response = base_llm_http_handler.rerank(
                model=model,
                custom_llm_provider=_custom_llm_provider,
                provider_config=rerank_provider_config,
                optional_rerank_params=optional_rerank_params,
                logging_obj=litellm_logging_obj,
                timeout=optional_params.timeout,
                api_key=dynamic_api_key or optional_params.api_key,
                api_base=api_base,
                _is_async=_is_async,
                headers=headers or litellm.headers or {},
                client=client,
                model_response=model_response,
            )
        elif _custom_llm_provider == "together_ai":
            # Implement Together AI rerank logic
            api_key = (
                dynamic_api_key
                or optional_params.api_key
                or litellm.togetherai_api_key
                or get_secret("TOGETHERAI_API_KEY")  # type: ignore
                or litellm.api_key
            )

            if api_key is None:
                raise ValueError(
                    "TogetherAI API key is required, please set 'TOGETHERAI_API_KEY' in your environment"
                )

            response = together_rerank.rerank(
                model=model,
                query=query,
                documents=documents,
                top_n=top_n,
                rank_fields=rank_fields,
                return_documents=return_documents,
                max_chunks_per_doc=max_chunks_per_doc,
                api_key=api_key,
                _is_async=_is_async,
            )
        elif _custom_llm_provider == "jina_ai":
            if dynamic_api_key is None:
                raise ValueError(
                    "Jina AI API key is required, please set 'JINA_AI_API_KEY' in your environment"
                )

            api_base = (
                dynamic_api_base
                or optional_params.api_base
                or litellm.api_base
                or get_secret("BEDROCK_API_BASE")  # type: ignore
            )

            response = base_llm_http_handler.rerank(
                model=model,
                custom_llm_provider=_custom_llm_provider,
                optional_rerank_params=optional_rerank_params,
                logging_obj=litellm_logging_obj,
                provider_config=rerank_provider_config,
                timeout=optional_params.timeout,
                api_key=dynamic_api_key or optional_params.api_key,
                api_base=api_base,
                _is_async=_is_async,
                headers=headers or litellm.headers or {},
                client=client,
                model_response=model_response,
            )
        elif _custom_llm_provider == "bedrock":
            api_base = (
                dynamic_api_base
                or optional_params.api_base
                or litellm.api_base
                or get_secret("BEDROCK_API_BASE")  # type: ignore
            )

            response = bedrock_rerank.rerank(
                model=model,
                query=query,
                documents=documents,
                top_n=top_n,
                rank_fields=rank_fields,
                return_documents=return_documents,
                max_chunks_per_doc=max_chunks_per_doc,
                _is_async=_is_async,
                optional_params=optional_params.model_dump(exclude_unset=True),
                api_base=api_base,
                logging_obj=litellm_logging_obj,
                client=client,
            )
        else:
            # Generic handler for all providers that use base_llm_http_handler
            # Provider-specific logic (API key validation, URL generation, etc.) 
            # is handled in the respective transformation configs
            
            # Check if the provider is actually supported
            # If rerank_provider_config is a default CohereRerankConfig but the provider is not Cohere or litellm_proxy,
            # it means the provider is not supported
            if (isinstance(rerank_provider_config, litellm.CohereRerankConfig) or 
                isinstance(rerank_provider_config, litellm.CohereRerankV2Config)) and _custom_llm_provider != "cohere" and _custom_llm_provider != "litellm_proxy":
                raise ValueError(f"Unsupported provider: {_custom_llm_provider}")
                
            response = base_llm_http_handler.rerank(
                model=model,
                custom_llm_provider=_custom_llm_provider,
                provider_config=rerank_provider_config,
                optional_rerank_params=optional_rerank_params,
                logging_obj=litellm_logging_obj,
                timeout=optional_params.timeout,
                api_key=dynamic_api_key or optional_params.api_key,
                api_base=dynamic_api_base or optional_params.api_base,
                _is_async=_is_async,
                headers=headers or litellm.headers or {},
                client=client,
                model_response=model_response,
            )

        # Placeholder return
        return response
    except Exception as e:
        verbose_logger.error(f"Error in rerank: {str(e)}")
        raise exception_type(
            model=model, custom_llm_provider=custom_llm_provider, original_exception=e
        )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\resources.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2017 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import bisect
import io
import logging
import os
import pkgutil
import sys
import types
import zipimport

from . import DistlibException
from .util import cached_property, get_cache_base, Cache

logger = logging.getLogger(__name__)


cache = None    # created when needed


class ResourceCache(Cache):
    def __init__(self, base=None):
        if base is None:
            # Use native string to avoid issues on 2.x: see Python #20140.
            base = os.path.join(get_cache_base(), str('resource-cache'))
        super(ResourceCache, self).__init__(base)

    def is_stale(self, resource, path):
        """
        Is the cache stale for the given resource?

        :param resource: The :class:`Resource` being cached.
        :param path: The path of the resource in the cache.
        :return: True if the cache is stale.
        """
        # Cache invalidation is a hard problem :-)
        return True

    def get(self, resource):
        """
        Get a resource into the cache,

        :param resource: A :class:`Resource` instance.
        :return: The pathname of the resource in the cache.
        """
        prefix, path = resource.finder.get_cache_info(resource)
        if prefix is None:
            result = path
        else:
            result = os.path.join(self.base, self.prefix_to_dir(prefix), path)
            dirname = os.path.dirname(result)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            if not os.path.exists(result):
                stale = True
            else:
                stale = self.is_stale(resource, path)
            if stale:
                # write the bytes of the resource to the cache location
                with open(result, 'wb') as f:
                    f.write(resource.bytes)
        return result


class ResourceBase(object):
    def __init__(self, finder, name):
        self.finder = finder
        self.name = name


class Resource(ResourceBase):
    """
    A class representing an in-package resource, such as a data file. This is
    not normally instantiated by user code, but rather by a
    :class:`ResourceFinder` which manages the resource.
    """
    is_container = False        # Backwards compatibility

    def as_stream(self):
        """
        Get the resource as a stream.

        This is not a property to make it obvious that it returns a new stream
        each time.
        """
        return self.finder.get_stream(self)

    @cached_property
    def file_path(self):
        global cache
        if cache is None:
            cache = ResourceCache()
        return cache.get(self)

    @cached_property
    def bytes(self):
        return self.finder.get_bytes(self)

    @cached_property
    def size(self):
        return self.finder.get_size(self)


class ResourceContainer(ResourceBase):
    is_container = True     # Backwards compatibility

    @cached_property
    def resources(self):
        return self.finder.get_resources(self)


class ResourceFinder(object):
    """
    Resource finder for file system resources.
    """

    if sys.platform.startswith('java'):
        skipped_extensions = ('.pyc', '.pyo', '.class')
    else:
        skipped_extensions = ('.pyc', '.pyo')

    def __init__(self, module):
        self.module = module
        self.loader = getattr(module, '__loader__', None)
        self.base = os.path.dirname(getattr(module, '__file__', ''))

    def _adjust_path(self, path):
        return os.path.realpath(path)

    def _make_path(self, resource_name):
        # Issue #50: need to preserve type of path on Python 2.x
        # like os.path._get_sep
        if isinstance(resource_name, bytes):    # should only happen on 2.x
            sep = b'/'
        else:
            sep = '/'
        parts = resource_name.split(sep)
        parts.insert(0, self.base)
        result = os.path.join(*parts)
        return self._adjust_path(result)

    def _find(self, path):
        return os.path.exists(path)

    def get_cache_info(self, resource):
        return None, resource.path

    def find(self, resource_name):
        path = self._make_path(resource_name)
        if not self._find(path):
            result = None
        else:
            if self._is_directory(path):
                result = ResourceContainer(self, resource_name)
            else:
                result = Resource(self, resource_name)
            result.path = path
        return result

    def get_stream(self, resource):
        return open(resource.path, 'rb')

    def get_bytes(self, resource):
        with open(resource.path, 'rb') as f:
            return f.read()

    def get_size(self, resource):
        return os.path.getsize(resource.path)

    def get_resources(self, resource):
        def allowed(f):
            return (f != '__pycache__' and not
                    f.endswith(self.skipped_extensions))
        return set([f for f in os.listdir(resource.path) if allowed(f)])

    def is_container(self, resource):
        return self._is_directory(resource.path)

    _is_directory = staticmethod(os.path.isdir)

    def iterator(self, resource_name):
        resource = self.find(resource_name)
        if resource is not None:
            todo = [resource]
            while todo:
                resource = todo.pop(0)
                yield resource
                if resource.is_container:
                    rname = resource.name
                    for name in resource.resources:
                        if not rname:
                            new_name = name
                        else:
                            new_name = '/'.join([rname, name])
                        child = self.find(new_name)
                        if child.is_container:
                            todo.append(child)
                        else:
                            yield child


class ZipResourceFinder(ResourceFinder):
    """
    Resource finder for resources in .zip files.
    """
    def __init__(self, module):
        super(ZipResourceFinder, self).__init__(module)
        archive = self.loader.archive
        self.prefix_len = 1 + len(archive)
        # PyPy doesn't have a _files attr on zipimporter, and you can't set one
        if hasattr(self.loader, '_files'):
            self._files = self.loader._files
        else:
            self._files = zipimport._zip_directory_cache[archive]
        self.index = sorted(self._files)

    def _adjust_path(self, path):
        return path

    def _find(self, path):
        path = path[self.prefix_len:]
        if path in self._files:
            result = True
        else:
            if path and path[-1] != os.sep:
                path = path + os.sep
            i = bisect.bisect(self.index, path)
            try:
                result = self.index[i].startswith(path)
            except IndexError:
                result = False
        if not result:
            logger.debug('_find failed: %r %r', path, self.loader.prefix)
        else:
            logger.debug('_find worked: %r %r', path, self.loader.prefix)
        return result

    def get_cache_info(self, resource):
        prefix = self.loader.archive
        path = resource.path[1 + len(prefix):]
        return prefix, path

    def get_bytes(self, resource):
        return self.loader.get_data(resource.path)

    def get_stream(self, resource):
        return io.BytesIO(self.get_bytes(resource))

    def get_size(self, resource):
        path = resource.path[self.prefix_len:]
        return self._files[path][3]

    def get_resources(self, resource):
        path = resource.path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        plen = len(path)
        result = set()
        i = bisect.bisect(self.index, path)
        while i < len(self.index):
            if not self.index[i].startswith(path):
                break
            s = self.index[i][plen:]
            result.add(s.split(os.sep, 1)[0])   # only immediate children
            i += 1
        return result

    def _is_directory(self, path):
        path = path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        i = bisect.bisect(self.index, path)
        try:
            result = self.index[i].startswith(path)
        except IndexError:
            result = False
        return result


_finder_registry = {
    type(None): ResourceFinder,
    zipimport.zipimporter: ZipResourceFinder
}

try:
    # In Python 3.6, _frozen_importlib -> _frozen_importlib_external
    try:
        import _frozen_importlib_external as _fi
    except ImportError:
        import _frozen_importlib as _fi
    _finder_registry[_fi.SourceFileLoader] = ResourceFinder
    _finder_registry[_fi.FileFinder] = ResourceFinder
    # See issue #146
    _finder_registry[_fi.SourcelessFileLoader] = ResourceFinder
    del _fi
except (ImportError, AttributeError):
    pass


def register_finder(loader, finder_maker):
    _finder_registry[type(loader)] = finder_maker


_finder_cache = {}


def finder(package):
    """
    Return a resource finder for a package.
    :param package: The name of the package.
    :return: A :class:`ResourceFinder` instance for the package.
    """
    if package in _finder_cache:
        result = _finder_cache[package]
    else:
        if package not in sys.modules:
            __import__(package)
        module = sys.modules[package]
        path = getattr(module, '__path__', None)
        if path is None:
            raise DistlibException('You cannot get a finder for a module, '
                                   'only for a package')
        loader = getattr(module, '__loader__', None)
        finder_maker = _finder_registry.get(type(loader))
        if finder_maker is None:
            raise DistlibException('Unable to locate finder for %r' % package)
        result = finder_maker(module)
        _finder_cache[package] = result
    return result


_dummy_module = types.ModuleType(str('__dummy__'))


def finder_for_path(path):
    """
    Return a resource finder for a path, which should represent a container.

    :param path: The path.
    :return: A :class:`ResourceFinder` instance for the path.
    """
    result = None
    # calls any path hooks, gets importer into cache
    pkgutil.get_importer(path)
    loader = sys.path_importer_cache.get(path)
    finder = _finder_registry.get(type(loader))
    if finder:
        module = _dummy_module
        module.__file__ = os.path.join(path, '')
        module.__loader__ = loader
        result = finder(module)
    return result

# === NexusCore/openenv\Lib\site-packages\nltk\ccg\api.py ===
# Natural Language Toolkit: CCG Categories
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from abc import ABCMeta, abstractmethod
from functools import total_ordering

from nltk.internals import raise_unorderable_types


@total_ordering
class AbstractCCGCategory(metaclass=ABCMeta):
    """
    Interface for categories in combinatory grammars.
    """

    @abstractmethod
    def is_primitive(self):
        """
        Returns true if the category is primitive.
        """

    @abstractmethod
    def is_function(self):
        """
        Returns true if the category is a function application.
        """

    @abstractmethod
    def is_var(self):
        """
        Returns true if the category is a variable.
        """

    @abstractmethod
    def substitute(self, substitutions):
        """
        Takes a set of (var, category) substitutions, and replaces every
        occurrence of the variable with the corresponding category.
        """

    @abstractmethod
    def can_unify(self, other):
        """
        Determines whether two categories can be unified.
         - Returns None if they cannot be unified
         - Returns a list of necessary substitutions if they can.
        """

    # Utility functions: comparison, strings and hashing.
    @abstractmethod
    def __str__(self):
        pass

    def __eq__(self, other):
        return (
            self.__class__ is other.__class__
            and self._comparison_key == other._comparison_key
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, AbstractCCGCategory):
            raise_unorderable_types("<", self, other)
        if self.__class__ is other.__class__:
            return self._comparison_key < other._comparison_key
        else:
            return self.__class__.__name__ < other.__class__.__name__

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._comparison_key)
            return self._hash


class CCGVar(AbstractCCGCategory):
    """
    Class representing a variable CCG category.
    Used for conjunctions (and possibly type-raising, if implemented as a
    unary rule).
    """

    _maxID = 0

    def __init__(self, prim_only=False):
        """Initialize a variable (selects a new identifier)

        :param prim_only: a boolean that determines whether the variable is
                          restricted to primitives
        :type prim_only: bool
        """
        self._id = self.new_id()
        self._prim_only = prim_only
        self._comparison_key = self._id

    @classmethod
    def new_id(cls):
        """
        A class method allowing generation of unique variable identifiers.
        """
        cls._maxID = cls._maxID + 1
        return cls._maxID - 1

    @classmethod
    def reset_id(cls):
        cls._maxID = 0

    def is_primitive(self):
        return False

    def is_function(self):
        return False

    def is_var(self):
        return True

    def substitute(self, substitutions):
        """If there is a substitution corresponding to this variable,
        return the substituted category.
        """
        for var, cat in substitutions:
            if var == self:
                return cat
        return self

    def can_unify(self, other):
        """If the variable can be replaced with other
        a substitution is returned.
        """
        if other.is_primitive() or not self._prim_only:
            return [(self, other)]
        return None

    def id(self):
        return self._id

    def __str__(self):
        return "_var" + str(self._id)


@total_ordering
class Direction:
    """
    Class representing the direction of a function application.
    Also contains maintains information as to which combinators
    may be used with the category.
    """

    def __init__(self, dir, restrictions):
        self._dir = dir
        self._restrs = restrictions
        self._comparison_key = (dir, tuple(restrictions))

    # Testing the application direction
    def is_forward(self):
        return self._dir == "/"

    def is_backward(self):
        return self._dir == "\\"

    def dir(self):
        return self._dir

    def restrs(self):
        """A list of restrictions on the combinators.
        '.' denotes that permuting operations are disallowed
        ',' denotes that function composition is disallowed
        '_' denotes that the direction has variable restrictions.
        (This is redundant in the current implementation of type-raising)
        """
        return self._restrs

    def is_variable(self):
        return self._restrs == "_"

    # Unification and substitution of variable directions.
    # Used only if type-raising is implemented as a unary rule, as it
    # must inherit restrictions from the argument category.
    def can_unify(self, other):
        if other.is_variable():
            return [("_", self.restrs())]
        elif self.is_variable():
            return [("_", other.restrs())]
        else:
            if self.restrs() == other.restrs():
                return []
        return None

    def substitute(self, subs):
        if not self.is_variable():
            return self

        for var, restrs in subs:
            if var == "_":
                return Direction(self._dir, restrs)
        return self

    # Testing permitted combinators
    def can_compose(self):
        return "," not in self._restrs

    def can_cross(self):
        return "." not in self._restrs

    def __eq__(self, other):
        return (
            self.__class__ is other.__class__
            and self._comparison_key == other._comparison_key
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Direction):
            raise_unorderable_types("<", self, other)
        if self.__class__ is other.__class__:
            return self._comparison_key < other._comparison_key
        else:
            return self.__class__.__name__ < other.__class__.__name__

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._comparison_key)
            return self._hash

    def __str__(self):
        r_str = ""
        for r in self._restrs:
            r_str = r_str + "%s" % r
        return f"{self._dir}{r_str}"

    # The negation operator reverses the direction of the application
    def __neg__(self):
        if self._dir == "/":
            return Direction("\\", self._restrs)
        else:
            return Direction("/", self._restrs)


class PrimitiveCategory(AbstractCCGCategory):
    """
    Class representing primitive categories.
    Takes a string representation of the category, and a
    list of strings specifying the morphological subcategories.
    """

    def __init__(self, categ, restrictions=[]):
        self._categ = categ
        self._restrs = restrictions
        self._comparison_key = (categ, tuple(restrictions))

    def is_primitive(self):
        return True

    def is_function(self):
        return False

    def is_var(self):
        return False

    def restrs(self):
        return self._restrs

    def categ(self):
        return self._categ

    # Substitution does nothing to a primitive category
    def substitute(self, subs):
        return self

    # A primitive can be unified with a class of the same
    # base category, given that the other category shares all
    # of its subclasses, or with a variable.
    def can_unify(self, other):
        if not other.is_primitive():
            return None
        if other.is_var():
            return [(other, self)]
        if other.categ() == self.categ():
            for restr in self._restrs:
                if restr not in other.restrs():
                    return None
            return []
        return None

    def __str__(self):
        if self._restrs == []:
            return "%s" % self._categ
        restrictions = "[%s]" % ",".join(repr(r) for r in self._restrs)
        return f"{self._categ}{restrictions}"


class FunctionalCategory(AbstractCCGCategory):
    """
    Class that represents a function application category.
    Consists of argument and result categories, together with
    an application direction.
    """

    def __init__(self, res, arg, dir):
        self._res = res
        self._arg = arg
        self._dir = dir
        self._comparison_key = (arg, dir, res)

    def is_primitive(self):
        return False

    def is_function(self):
        return True

    def is_var(self):
        return False

    # Substitution returns the category consisting of the
    # substitution applied to each of its constituents.
    def substitute(self, subs):
        sub_res = self._res.substitute(subs)
        sub_dir = self._dir.substitute(subs)
        sub_arg = self._arg.substitute(subs)
        return FunctionalCategory(sub_res, sub_arg, self._dir)

    # A function can unify with another function, so long as its
    # constituents can unify, or with an unrestricted variable.
    def can_unify(self, other):
        if other.is_var():
            return [(other, self)]
        if other.is_function():
            sa = self._res.can_unify(other.res())
            sd = self._dir.can_unify(other.dir())
            if sa is not None and sd is not None:
                sb = self._arg.substitute(sa).can_unify(other.arg().substitute(sa))
                if sb is not None:
                    return sa + sb
        return None

    # Constituent accessors
    def arg(self):
        return self._arg

    def res(self):
        return self._res

    def dir(self):
        return self._dir

    def __str__(self):
        return f"({self._res}{self._dir}{self._arg})"

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\resources.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2017 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import bisect
import io
import logging
import os
import pkgutil
import sys
import types
import zipimport

from . import DistlibException
from .util import cached_property, get_cache_base, Cache

logger = logging.getLogger(__name__)


cache = None    # created when needed


class ResourceCache(Cache):
    def __init__(self, base=None):
        if base is None:
            # Use native string to avoid issues on 2.x: see Python #20140.
            base = os.path.join(get_cache_base(), str('resource-cache'))
        super(ResourceCache, self).__init__(base)

    def is_stale(self, resource, path):
        """
        Is the cache stale for the given resource?

        :param resource: The :class:`Resource` being cached.
        :param path: The path of the resource in the cache.
        :return: True if the cache is stale.
        """
        # Cache invalidation is a hard problem :-)
        return True

    def get(self, resource):
        """
        Get a resource into the cache,

        :param resource: A :class:`Resource` instance.
        :return: The pathname of the resource in the cache.
        """
        prefix, path = resource.finder.get_cache_info(resource)
        if prefix is None:
            result = path
        else:
            result = os.path.join(self.base, self.prefix_to_dir(prefix), path)
            dirname = os.path.dirname(result)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            if not os.path.exists(result):
                stale = True
            else:
                stale = self.is_stale(resource, path)
            if stale:
                # write the bytes of the resource to the cache location
                with open(result, 'wb') as f:
                    f.write(resource.bytes)
        return result


class ResourceBase(object):
    def __init__(self, finder, name):
        self.finder = finder
        self.name = name


class Resource(ResourceBase):
    """
    A class representing an in-package resource, such as a data file. This is
    not normally instantiated by user code, but rather by a
    :class:`ResourceFinder` which manages the resource.
    """
    is_container = False        # Backwards compatibility

    def as_stream(self):
        """
        Get the resource as a stream.

        This is not a property to make it obvious that it returns a new stream
        each time.
        """
        return self.finder.get_stream(self)

    @cached_property
    def file_path(self):
        global cache
        if cache is None:
            cache = ResourceCache()
        return cache.get(self)

    @cached_property
    def bytes(self):
        return self.finder.get_bytes(self)

    @cached_property
    def size(self):
        return self.finder.get_size(self)


class ResourceContainer(ResourceBase):
    is_container = True     # Backwards compatibility

    @cached_property
    def resources(self):
        return self.finder.get_resources(self)


class ResourceFinder(object):
    """
    Resource finder for file system resources.
    """

    if sys.platform.startswith('java'):
        skipped_extensions = ('.pyc', '.pyo', '.class')
    else:
        skipped_extensions = ('.pyc', '.pyo')

    def __init__(self, module):
        self.module = module
        self.loader = getattr(module, '__loader__', None)
        self.base = os.path.dirname(getattr(module, '__file__', ''))

    def _adjust_path(self, path):
        return os.path.realpath(path)

    def _make_path(self, resource_name):
        # Issue #50: need to preserve type of path on Python 2.x
        # like os.path._get_sep
        if isinstance(resource_name, bytes):    # should only happen on 2.x
            sep = b'/'
        else:
            sep = '/'
        parts = resource_name.split(sep)
        parts.insert(0, self.base)
        result = os.path.join(*parts)
        return self._adjust_path(result)

    def _find(self, path):
        return os.path.exists(path)

    def get_cache_info(self, resource):
        return None, resource.path

    def find(self, resource_name):
        path = self._make_path(resource_name)
        if not self._find(path):
            result = None
        else:
            if self._is_directory(path):
                result = ResourceContainer(self, resource_name)
            else:
                result = Resource(self, resource_name)
            result.path = path
        return result

    def get_stream(self, resource):
        return open(resource.path, 'rb')

    def get_bytes(self, resource):
        with open(resource.path, 'rb') as f:
            return f.read()

    def get_size(self, resource):
        return os.path.getsize(resource.path)

    def get_resources(self, resource):
        def allowed(f):
            return (f != '__pycache__' and not
                    f.endswith(self.skipped_extensions))
        return set([f for f in os.listdir(resource.path) if allowed(f)])

    def is_container(self, resource):
        return self._is_directory(resource.path)

    _is_directory = staticmethod(os.path.isdir)

    def iterator(self, resource_name):
        resource = self.find(resource_name)
        if resource is not None:
            todo = [resource]
            while todo:
                resource = todo.pop(0)
                yield resource
                if resource.is_container:
                    rname = resource.name
                    for name in resource.resources:
                        if not rname:
                            new_name = name
                        else:
                            new_name = '/'.join([rname, name])
                        child = self.find(new_name)
                        if child.is_container:
                            todo.append(child)
                        else:
                            yield child


class ZipResourceFinder(ResourceFinder):
    """
    Resource finder for resources in .zip files.
    """
    def __init__(self, module):
        super(ZipResourceFinder, self).__init__(module)
        archive = self.loader.archive
        self.prefix_len = 1 + len(archive)
        # PyPy doesn't have a _files attr on zipimporter, and you can't set one
        if hasattr(self.loader, '_files'):
            self._files = self.loader._files
        else:
            self._files = zipimport._zip_directory_cache[archive]
        self.index = sorted(self._files)

    def _adjust_path(self, path):
        return path

    def _find(self, path):
        path = path[self.prefix_len:]
        if path in self._files:
            result = True
        else:
            if path and path[-1] != os.sep:
                path = path + os.sep
            i = bisect.bisect(self.index, path)
            try:
                result = self.index[i].startswith(path)
            except IndexError:
                result = False
        if not result:
            logger.debug('_find failed: %r %r', path, self.loader.prefix)
        else:
            logger.debug('_find worked: %r %r', path, self.loader.prefix)
        return result

    def get_cache_info(self, resource):
        prefix = self.loader.archive
        path = resource.path[1 + len(prefix):]
        return prefix, path

    def get_bytes(self, resource):
        return self.loader.get_data(resource.path)

    def get_stream(self, resource):
        return io.BytesIO(self.get_bytes(resource))

    def get_size(self, resource):
        path = resource.path[self.prefix_len:]
        return self._files[path][3]

    def get_resources(self, resource):
        path = resource.path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        plen = len(path)
        result = set()
        i = bisect.bisect(self.index, path)
        while i < len(self.index):
            if not self.index[i].startswith(path):
                break
            s = self.index[i][plen:]
            result.add(s.split(os.sep, 1)[0])   # only immediate children
            i += 1
        return result

    def _is_directory(self, path):
        path = path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        i = bisect.bisect(self.index, path)
        try:
            result = self.index[i].startswith(path)
        except IndexError:
            result = False
        return result


_finder_registry = {
    type(None): ResourceFinder,
    zipimport.zipimporter: ZipResourceFinder
}

try:
    # In Python 3.6, _frozen_importlib -> _frozen_importlib_external
    try:
        import _frozen_importlib_external as _fi
    except ImportError:
        import _frozen_importlib as _fi
    _finder_registry[_fi.SourceFileLoader] = ResourceFinder
    _finder_registry[_fi.FileFinder] = ResourceFinder
    # See issue #146
    _finder_registry[_fi.SourcelessFileLoader] = ResourceFinder
    del _fi
except (ImportError, AttributeError):
    pass


def register_finder(loader, finder_maker):
    _finder_registry[type(loader)] = finder_maker


_finder_cache = {}


def finder(package):
    """
    Return a resource finder for a package.
    :param package: The name of the package.
    :return: A :class:`ResourceFinder` instance for the package.
    """
    if package in _finder_cache:
        result = _finder_cache[package]
    else:
        if package not in sys.modules:
            __import__(package)
        module = sys.modules[package]
        path = getattr(module, '__path__', None)
        if path is None:
            raise DistlibException('You cannot get a finder for a module, '
                                   'only for a package')
        loader = getattr(module, '__loader__', None)
        finder_maker = _finder_registry.get(type(loader))
        if finder_maker is None:
            raise DistlibException('Unable to locate finder for %r' % package)
        result = finder_maker(module)
        _finder_cache[package] = result
    return result


_dummy_module = types.ModuleType(str('__dummy__'))


def finder_for_path(path):
    """
    Return a resource finder for a path, which should represent a container.

    :param path: The path.
    :return: A :class:`ResourceFinder` instance for the path.
    """
    result = None
    # calls any path hooks, gets importer into cache
    pkgutil.get_importer(path)
    loader = sys.path_importer_cache.get(path)
    finder = _finder_registry.get(type(loader))
    if finder:
        module = _dummy_module
        module.__file__ = os.path.join(path, '')
        module.__loader__ = loader
        result = finder(module)
    return result

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\config.py ===
"""distutils.command.config

Implements the Distutils 'config' command, a (mostly) empty command class
that exists mainly to be sub-classed by specific module distributions and
applications.  The idea is that while every "config" command is different,
at least they're all named the same, and users always see "config" in the
list of standard commands.  Also, this is a good place to put common
configure-like tasks: "try to compile this C code", or "figure out where
this header file lives".
"""

from __future__ import annotations

import os
import pathlib
import re
from collections.abc import Sequence
from distutils._log import log

from ..ccompiler import CCompiler, CompileError, LinkError, new_compiler
from ..core import Command
from ..errors import DistutilsExecError
from ..sysconfig import customize_compiler

LANG_EXT = {"c": ".c", "c++": ".cxx"}


class config(Command):
    description = "prepare to build"

    user_options = [
        ('compiler=', None, "specify the compiler type"),
        ('cc=', None, "specify the compiler executable"),
        ('include-dirs=', 'I', "list of directories to search for header files"),
        ('define=', 'D', "C preprocessor macros to define"),
        ('undef=', 'U', "C preprocessor macros to undefine"),
        ('libraries=', 'l', "external C libraries to link with"),
        ('library-dirs=', 'L', "directories to search for external C libraries"),
        ('noisy', None, "show every action (compile, link, run, ...) taken"),
        (
            'dump-source',
            None,
            "dump generated source files before attempting to compile them",
        ),
    ]

    # The three standard command methods: since the "config" command
    # does nothing by default, these are empty.

    def initialize_options(self):
        self.compiler = None
        self.cc = None
        self.include_dirs = None
        self.libraries = None
        self.library_dirs = None

        # maximal output for now
        self.noisy = 1
        self.dump_source = 1

        # list of temporary files generated along-the-way that we have
        # to clean at some point
        self.temp_files = []

    def finalize_options(self):
        if self.include_dirs is None:
            self.include_dirs = self.distribution.include_dirs or []
        elif isinstance(self.include_dirs, str):
            self.include_dirs = self.include_dirs.split(os.pathsep)

        if self.libraries is None:
            self.libraries = []
        elif isinstance(self.libraries, str):
            self.libraries = [self.libraries]

        if self.library_dirs is None:
            self.library_dirs = []
        elif isinstance(self.library_dirs, str):
            self.library_dirs = self.library_dirs.split(os.pathsep)

    def run(self):
        pass

    # Utility methods for actual "config" commands.  The interfaces are
    # loosely based on Autoconf macros of similar names.  Sub-classes
    # may use these freely.

    def _check_compiler(self):
        """Check that 'self.compiler' really is a CCompiler object;
        if not, make it one.
        """
        if not isinstance(self.compiler, CCompiler):
            self.compiler = new_compiler(
                compiler=self.compiler, dry_run=self.dry_run, force=True
            )
            customize_compiler(self.compiler)
            if self.include_dirs:
                self.compiler.set_include_dirs(self.include_dirs)
            if self.libraries:
                self.compiler.set_libraries(self.libraries)
            if self.library_dirs:
                self.compiler.set_library_dirs(self.library_dirs)

    def _gen_temp_sourcefile(self, body, headers, lang):
        filename = "_configtest" + LANG_EXT[lang]
        with open(filename, "w", encoding='utf-8') as file:
            if headers:
                for header in headers:
                    file.write(f"#include <{header}>\n")
                file.write("\n")
            file.write(body)
            if body[-1] != "\n":
                file.write("\n")
        return filename

    def _preprocess(self, body, headers, include_dirs, lang):
        src = self._gen_temp_sourcefile(body, headers, lang)
        out = "_configtest.i"
        self.temp_files.extend([src, out])
        self.compiler.preprocess(src, out, include_dirs=include_dirs)
        return (src, out)

    def _compile(self, body, headers, include_dirs, lang):
        src = self._gen_temp_sourcefile(body, headers, lang)
        if self.dump_source:
            dump_file(src, f"compiling '{src}':")
        (obj,) = self.compiler.object_filenames([src])
        self.temp_files.extend([src, obj])
        self.compiler.compile([src], include_dirs=include_dirs)
        return (src, obj)

    def _link(self, body, headers, include_dirs, libraries, library_dirs, lang):
        (src, obj) = self._compile(body, headers, include_dirs, lang)
        prog = os.path.splitext(os.path.basename(src))[0]
        self.compiler.link_executable(
            [obj],
            prog,
            libraries=libraries,
            library_dirs=library_dirs,
            target_lang=lang,
        )

        if self.compiler.exe_extension is not None:
            prog = prog + self.compiler.exe_extension
        self.temp_files.append(prog)

        return (src, obj, prog)

    def _clean(self, *filenames):
        if not filenames:
            filenames = self.temp_files
            self.temp_files = []
        log.info("removing: %s", ' '.join(filenames))
        for filename in filenames:
            try:
                os.remove(filename)
            except OSError:
                pass

    # XXX these ignore the dry-run flag: what to do, what to do? even if
    # you want a dry-run build, you still need some sort of configuration
    # info.  My inclination is to make it up to the real config command to
    # consult 'dry_run', and assume a default (minimal) configuration if
    # true.  The problem with trying to do it here is that you'd have to
    # return either true or false from all the 'try' methods, neither of
    # which is correct.

    # XXX need access to the header search path and maybe default macros.

    def try_cpp(self, body=None, headers=None, include_dirs=None, lang="c"):
        """Construct a source file from 'body' (a string containing lines
        of C/C++ code) and 'headers' (a list of header files to include)
        and run it through the preprocessor.  Return true if the
        preprocessor succeeded, false if there were any errors.
        ('body' probably isn't of much use, but what the heck.)
        """
        self._check_compiler()
        ok = True
        try:
            self._preprocess(body, headers, include_dirs, lang)
        except CompileError:
            ok = False

        self._clean()
        return ok

    def search_cpp(self, pattern, body=None, headers=None, include_dirs=None, lang="c"):
        """Construct a source file (just like 'try_cpp()'), run it through
        the preprocessor, and return true if any line of the output matches
        'pattern'.  'pattern' should either be a compiled regex object or a
        string containing a regex.  If both 'body' and 'headers' are None,
        preprocesses an empty file -- which can be useful to determine the
        symbols the preprocessor and compiler set by default.
        """
        self._check_compiler()
        src, out = self._preprocess(body, headers, include_dirs, lang)

        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        with open(out, encoding='utf-8') as file:
            match = any(pattern.search(line) for line in file)

        self._clean()
        return match

    def try_compile(self, body, headers=None, include_dirs=None, lang="c"):
        """Try to compile a source file built from 'body' and 'headers'.
        Return true on success, false otherwise.
        """
        self._check_compiler()
        try:
            self._compile(body, headers, include_dirs, lang)
            ok = True
        except CompileError:
            ok = False

        log.info(ok and "success!" or "failure.")
        self._clean()
        return ok

    def try_link(
        self,
        body,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        lang="c",
    ):
        """Try to compile and link a source file, built from 'body' and
        'headers', to executable form.  Return true on success, false
        otherwise.
        """
        self._check_compiler()
        try:
            self._link(body, headers, include_dirs, libraries, library_dirs, lang)
            ok = True
        except (CompileError, LinkError):
            ok = False

        log.info(ok and "success!" or "failure.")
        self._clean()
        return ok

    def try_run(
        self,
        body,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        lang="c",
    ):
        """Try to compile, link to an executable, and run a program
        built from 'body' and 'headers'.  Return true on success, false
        otherwise.
        """
        self._check_compiler()
        try:
            src, obj, exe = self._link(
                body, headers, include_dirs, libraries, library_dirs, lang
            )
            self.spawn([exe])
            ok = True
        except (CompileError, LinkError, DistutilsExecError):
            ok = False

        log.info(ok and "success!" or "failure.")
        self._clean()
        return ok

    # -- High-level methods --------------------------------------------
    # (these are the ones that are actually likely to be useful
    # when implementing a real-world config command!)

    def check_func(
        self,
        func,
        headers=None,
        include_dirs=None,
        libraries=None,
        library_dirs=None,
        decl=False,
        call=False,
    ):
        """Determine if function 'func' is available by constructing a
        source file that refers to 'func', and compiles and links it.
        If everything succeeds, returns true; otherwise returns false.

        The constructed source file starts out by including the header
        files listed in 'headers'.  If 'decl' is true, it then declares
        'func' (as "int func()"); you probably shouldn't supply 'headers'
        and set 'decl' true in the same call, or you might get errors about
        a conflicting declarations for 'func'.  Finally, the constructed
        'main()' function either references 'func' or (if 'call' is true)
        calls it.  'libraries' and 'library_dirs' are used when
        linking.
        """
        self._check_compiler()
        body = []
        if decl:
            body.append(f"int {func} ();")
        body.append("int main () {")
        if call:
            body.append(f"  {func}();")
        else:
            body.append(f"  {func};")
        body.append("}")
        body = "\n".join(body) + "\n"

        return self.try_link(body, headers, include_dirs, libraries, library_dirs)

    def check_lib(
        self,
        library,
        library_dirs=None,
        headers=None,
        include_dirs=None,
        other_libraries: Sequence[str] = [],
    ):
        """Determine if 'library' is available to be linked against,
        without actually checking that any particular symbols are provided
        by it.  'headers' will be used in constructing the source file to
        be compiled, but the only effect of this is to check if all the
        header files listed are available.  Any libraries listed in
        'other_libraries' will be included in the link, in case 'library'
        has symbols that depend on other libraries.
        """
        self._check_compiler()
        return self.try_link(
            "int main (void) { }",
            headers,
            include_dirs,
            [library] + list(other_libraries),
            library_dirs,
        )

    def check_header(self, header, include_dirs=None, library_dirs=None, lang="c"):
        """Determine if the system header file named by 'header_file'
        exists and can be found by the preprocessor; return true if so,
        false otherwise.
        """
        return self.try_cpp(
            body="/* No body */", headers=[header], include_dirs=include_dirs
        )


def dump_file(filename, head=None):
    """Dumps a file content into log.info.

    If head is not None, will be dumped before the file content.
    """
    if head is None:
        log.info('%s', filename)
    else:
        log.info(head)
    log.info(pathlib.Path(filename).read_text(encoding='utf-8'))

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc7292.py ===
# This file is being contributed to pyasn1-modules software.
#
# Created by Russ Housley with assistance from the asn1ate tool.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# PKCS #12: Personal Information Exchange Syntax v1.1
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc7292.txt
# https://www.rfc-editor.org/errata_search.php?rfc=7292

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc2315
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5958


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


# Initialize the maps used in PKCS#12

pkcs12BagTypeMap = { }

pkcs12CertBagMap = { }

pkcs12CRLBagMap = { }

pkcs12SecretBagMap = { }


# Imports from RFC 2315, RFC 5652, and RFC 5958

DigestInfo = rfc2315.DigestInfo


ContentInfo = rfc5652.ContentInfo

PKCS12Attribute = rfc5652.Attribute


EncryptedPrivateKeyInfo = rfc5958.EncryptedPrivateKeyInfo

PrivateKeyInfo = rfc5958.PrivateKeyInfo


# CMSSingleAttribute is the same as Attribute in RFC 5652 except the attrValues
# SET must have one and only one member

class AttributeType(univ.ObjectIdentifier):
    pass


class AttributeValue(univ.Any):
    pass


class AttributeValues(univ.SetOf):
    pass

AttributeValues.componentType = AttributeValue()


class CMSSingleAttribute(univ.Sequence):
    pass

CMSSingleAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', AttributeType()),
    namedtype.NamedType('attrValues',
        AttributeValues().subtype(sizeSpec=constraint.ValueSizeConstraint(1, 1)),
        openType=opentype.OpenType('attrType', rfc5652.cmsAttributesMap)
    )
)


# Object identifier arcs

rsadsi = _OID(1, 2, 840, 113549)

pkcs = _OID(rsadsi, 1)

pkcs_9 = _OID(pkcs, 9)

certTypes = _OID(pkcs_9, 22)

crlTypes = _OID(pkcs_9, 23)

pkcs_12 = _OID(pkcs, 12)


# PBE Algorithm Identifiers and Parameters Structure

pkcs_12PbeIds = _OID(pkcs_12, 1)

pbeWithSHAAnd128BitRC4 = _OID(pkcs_12PbeIds, 1)

pbeWithSHAAnd40BitRC4 = _OID(pkcs_12PbeIds, 2)

pbeWithSHAAnd3_KeyTripleDES_CBC = _OID(pkcs_12PbeIds, 3)

pbeWithSHAAnd2_KeyTripleDES_CBC = _OID(pkcs_12PbeIds, 4)

pbeWithSHAAnd128BitRC2_CBC = _OID(pkcs_12PbeIds, 5)

pbeWithSHAAnd40BitRC2_CBC = _OID(pkcs_12PbeIds, 6)


class Pkcs_12PbeParams(univ.Sequence):
    pass

Pkcs_12PbeParams.componentType = namedtype.NamedTypes(
    namedtype.NamedType('salt', univ.OctetString()),
    namedtype.NamedType('iterations', univ.Integer())
)


# Bag types

bagtypes = _OID(pkcs_12, 10, 1)

class BAG_TYPE(univ.Sequence):
    pass

BAG_TYPE.componentType = namedtype.NamedTypes(
    namedtype.NamedType('id', univ.ObjectIdentifier()),
    namedtype.NamedType('unnamed1', univ.Any(),
        openType=opentype.OpenType('attrType', pkcs12BagTypeMap)
    )
)


id_keyBag = _OID(bagtypes, 1)

class KeyBag(PrivateKeyInfo):
    pass


id_pkcs8ShroudedKeyBag = _OID(bagtypes, 2)

class PKCS8ShroudedKeyBag(EncryptedPrivateKeyInfo):
    pass


id_certBag = _OID(bagtypes, 3)

class CertBag(univ.Sequence):
    pass

CertBag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certId', univ.ObjectIdentifier()),
    namedtype.NamedType('certValue',
        univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
        openType=opentype.OpenType('certId', pkcs12CertBagMap)
    )
)


x509Certificate = CertBag()
x509Certificate['certId'] = _OID(certTypes, 1)
x509Certificate['certValue'] = univ.OctetString()
# DER-encoded X.509 certificate stored in OCTET STRING


sdsiCertificate = CertBag()
sdsiCertificate['certId'] = _OID(certTypes, 2)
sdsiCertificate['certValue'] = char.IA5String()
# Base64-encoded SDSI certificate stored in IA5String


id_CRLBag = _OID(bagtypes, 4)

class CRLBag(univ.Sequence):
    pass

CRLBag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('crlId', univ.ObjectIdentifier()),
    namedtype.NamedType('crlValue',
        univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
                openType=opentype.OpenType('crlId', pkcs12CRLBagMap)
    )
)


x509CRL = CRLBag()
x509CRL['crlId'] = _OID(crlTypes, 1)
x509CRL['crlValue'] = univ.OctetString()
# DER-encoded X.509 CRL stored in OCTET STRING


id_secretBag = _OID(bagtypes, 5)

class SecretBag(univ.Sequence):
    pass

SecretBag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('secretTypeId', univ.ObjectIdentifier()),
    namedtype.NamedType('secretValue',
        univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
        openType=opentype.OpenType('secretTypeId', pkcs12SecretBagMap)
    )
)


id_safeContentsBag = _OID(bagtypes, 6)

class SafeBag(univ.Sequence):
    pass

SafeBag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bagId', univ.ObjectIdentifier()),
    namedtype.NamedType('bagValue',
        univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
        openType=opentype.OpenType('bagId', pkcs12BagTypeMap)
    ),
    namedtype.OptionalNamedType('bagAttributes',
        univ.SetOf(componentType=PKCS12Attribute())
    )
)


class SafeContents(univ.SequenceOf):
    pass

SafeContents.componentType = SafeBag()


# The PFX PDU

class AuthenticatedSafe(univ.SequenceOf):
    pass

AuthenticatedSafe.componentType = ContentInfo()
# Data if unencrypted
# EncryptedData if password-encrypted
# EnvelopedData if public key-encrypted


class MacData(univ.Sequence):
    pass

MacData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('mac', DigestInfo()),
    namedtype.NamedType('macSalt', univ.OctetString()),
    namedtype.DefaultedNamedType('iterations', univ.Integer().subtype(value=1))
    # Note: The default is for historical reasons and its use is deprecated
)


class PFX(univ.Sequence):
    pass

PFX.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version',
        univ.Integer(namedValues=namedval.NamedValues(('v3', 3)))
    ),
    namedtype.NamedType('authSafe', ContentInfo()),
    namedtype.OptionalNamedType('macData', MacData())
)


# Local key identifier (also defined as certificateAttribute in rfc2985.py)

pkcs_9_at_localKeyId = _OID(pkcs_9, 21)

localKeyId = CMSSingleAttribute()
localKeyId['attrType'] = pkcs_9_at_localKeyId
localKeyId['attrValues'][0] = univ.OctetString()


# Friendly name (also defined as certificateAttribute in rfc2985.py)

pkcs_9_ub_pkcs9String = univ.Integer(255)

pkcs_9_ub_friendlyName = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_at_friendlyName = _OID(pkcs_9, 20)

class FriendlyName(char.BMPString):
    pass

FriendlyName.subtypeSpec = constraint.ValueSizeConstraint(1, pkcs_9_ub_friendlyName)


friendlyName = CMSSingleAttribute()
friendlyName['attrType'] = pkcs_9_at_friendlyName
friendlyName['attrValues'][0] = FriendlyName()


# Update the PKCS#12 maps

_pkcs12BagTypeMap = {
    id_keyBag: KeyBag(),
    id_pkcs8ShroudedKeyBag: PKCS8ShroudedKeyBag(),
    id_certBag: CertBag(),
    id_CRLBag: CRLBag(),
    id_secretBag: SecretBag(),
    id_safeContentsBag: SafeBag(),
}

pkcs12BagTypeMap.update(_pkcs12BagTypeMap)


_pkcs12CertBagMap = {
    _OID(certTypes, 1): univ.OctetString(),
    _OID(certTypes, 2): char.IA5String(),
}

pkcs12CertBagMap.update(_pkcs12CertBagMap)


_pkcs12CRLBagMap = {
    _OID(crlTypes, 1): univ.OctetString(),
}

pkcs12CRLBagMap.update(_pkcs12CRLBagMap)


# Update the Algorithm Identifier map

_algorithmIdentifierMapUpdate = {
    pbeWithSHAAnd128BitRC4: Pkcs_12PbeParams(),
    pbeWithSHAAnd40BitRC4: Pkcs_12PbeParams(),
    pbeWithSHAAnd3_KeyTripleDES_CBC: Pkcs_12PbeParams(),
    pbeWithSHAAnd2_KeyTripleDES_CBC: Pkcs_12PbeParams(),
    pbeWithSHAAnd128BitRC2_CBC: Pkcs_12PbeParams(),
    pbeWithSHAAnd40BitRC2_CBC: Pkcs_12PbeParams(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)


# Update the CMS Attribute map

_cmsAttributesMapUpdate = {
    pkcs_9_at_friendlyName: FriendlyName(),
    pkcs_9_at_localKeyId: univ.OctetString(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pyparsing\unicode.py ===
# unicode.py

import sys
from itertools import filterfalse
from typing import Union


class _lazyclassproperty:
    def __init__(self, fn):
        self.fn = fn
        self.__doc__ = fn.__doc__
        self.__name__ = fn.__name__

    def __get__(self, obj, cls):
        if cls is None:
            cls = type(obj)
        if not hasattr(cls, "_intern") or any(
            cls._intern is getattr(superclass, "_intern", [])
            for superclass in cls.__mro__[1:]
        ):
            cls._intern = {}
        attrname = self.fn.__name__
        if attrname not in cls._intern:
            cls._intern[attrname] = self.fn(cls)
        return cls._intern[attrname]


UnicodeRangeList = list[Union[tuple[int, int], tuple[int]]]


class unicode_set:
    """
    A set of Unicode characters, for language-specific strings for
    ``alphas``, ``nums``, ``alphanums``, and ``printables``.
    A unicode_set is defined by a list of ranges in the Unicode character
    set, in a class attribute ``_ranges``. Ranges can be specified using
    2-tuples or a 1-tuple, such as::

        _ranges = [
            (0x0020, 0x007e),
            (0x00a0, 0x00ff),
            (0x0100,),
            ]

    Ranges are left- and right-inclusive. A 1-tuple of (x,) is treated as (x, x).

    A unicode set can also be defined using multiple inheritance of other unicode sets::

        class CJK(Chinese, Japanese, Korean):
            pass
    """

    _ranges: UnicodeRangeList = []

    @_lazyclassproperty
    def _chars_for_ranges(cls) -> list[str]:
        ret: list[int] = []
        for cc in cls.__mro__:  # type: ignore[attr-defined]
            if cc is unicode_set:
                break
            for rr in getattr(cc, "_ranges", ()):
                ret.extend(range(rr[0], rr[-1] + 1))
        return sorted(chr(c) for c in set(ret))

    @_lazyclassproperty
    def printables(cls) -> str:
        """all non-whitespace characters in this range"""
        return "".join(filterfalse(str.isspace, cls._chars_for_ranges))

    @_lazyclassproperty
    def alphas(cls) -> str:
        """all alphabetic characters in this range"""
        return "".join(filter(str.isalpha, cls._chars_for_ranges))

    @_lazyclassproperty
    def nums(cls) -> str:
        """all numeric digit characters in this range"""
        return "".join(filter(str.isdigit, cls._chars_for_ranges))

    @_lazyclassproperty
    def alphanums(cls) -> str:
        """all alphanumeric characters in this range"""
        return cls.alphas + cls.nums

    @_lazyclassproperty
    def identchars(cls) -> str:
        """all characters in this range that are valid identifier characters, plus underscore '_'"""
        return "".join(
            sorted(
                set(filter(str.isidentifier, cls._chars_for_ranges))
                | set(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzªµº"
                    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
                    "_"
                )
            )
        )

    @_lazyclassproperty
    def identbodychars(cls) -> str:
        """
        all characters in this range that are valid identifier body characters,
        plus the digits 0-9, and · (Unicode MIDDLE DOT)
        """
        identifier_chars = set(
            c for c in cls._chars_for_ranges if ("_" + c).isidentifier()
        )
        return "".join(
            sorted(identifier_chars | set(cls.identchars) | set("0123456789·"))
        )

    @_lazyclassproperty
    def identifier(cls):
        """
        a pyparsing Word expression for an identifier using this range's definitions for
        identchars and identbodychars
        """
        from pyparsing import Word

        return Word(cls.identchars, cls.identbodychars)


class pyparsing_unicode(unicode_set):
    """
    A namespace class for defining common language unicode_sets.
    """

    # fmt: off

    # define ranges in language character sets
    _ranges: UnicodeRangeList = [
        (0x0020, sys.maxunicode),
    ]

    class BasicMultilingualPlane(unicode_set):
        """Unicode set for the Basic Multilingual Plane"""
        _ranges: UnicodeRangeList = [
            (0x0020, 0xFFFF),
        ]

    class Latin1(unicode_set):
        """Unicode set for Latin-1 Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0020, 0x007E),
            (0x00A0, 0x00FF),
        ]

    class LatinA(unicode_set):
        """Unicode set for Latin-A Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0100, 0x017F),
        ]

    class LatinB(unicode_set):
        """Unicode set for Latin-B Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0180, 0x024F),
        ]

    class Greek(unicode_set):
        """Unicode set for Greek Unicode Character Ranges"""
        _ranges: UnicodeRangeList = [
            (0x0342, 0x0345),
            (0x0370, 0x0377),
            (0x037A, 0x037F),
            (0x0384, 0x038A),
            (0x038C,),
            (0x038E, 0x03A1),
            (0x03A3, 0x03E1),
            (0x03F0, 0x03FF),
            (0x1D26, 0x1D2A),
            (0x1D5E,),
            (0x1D60,),
            (0x1D66, 0x1D6A),
            (0x1F00, 0x1F15),
            (0x1F18, 0x1F1D),
            (0x1F20, 0x1F45),
            (0x1F48, 0x1F4D),
            (0x1F50, 0x1F57),
            (0x1F59,),
            (0x1F5B,),
            (0x1F5D,),
            (0x1F5F, 0x1F7D),
            (0x1F80, 0x1FB4),
            (0x1FB6, 0x1FC4),
            (0x1FC6, 0x1FD3),
            (0x1FD6, 0x1FDB),
            (0x1FDD, 0x1FEF),
            (0x1FF2, 0x1FF4),
            (0x1FF6, 0x1FFE),
            (0x2129,),
            (0x2719, 0x271A),
            (0xAB65,),
            (0x10140, 0x1018D),
            (0x101A0,),
            (0x1D200, 0x1D245),
            (0x1F7A1, 0x1F7A7),
        ]

    class Cyrillic(unicode_set):
        """Unicode set for Cyrillic Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0400, 0x052F),
            (0x1C80, 0x1C88),
            (0x1D2B,),
            (0x1D78,),
            (0x2DE0, 0x2DFF),
            (0xA640, 0xA672),
            (0xA674, 0xA69F),
            (0xFE2E, 0xFE2F),
        ]

    class Chinese(unicode_set):
        """Unicode set for Chinese Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x2E80, 0x2E99),
            (0x2E9B, 0x2EF3),
            (0x31C0, 0x31E3),
            (0x3400, 0x4DB5),
            (0x4E00, 0x9FEF),
            (0xA700, 0xA707),
            (0xF900, 0xFA6D),
            (0xFA70, 0xFAD9),
            (0x16FE2, 0x16FE3),
            (0x1F210, 0x1F212),
            (0x1F214, 0x1F23B),
            (0x1F240, 0x1F248),
            (0x20000, 0x2A6D6),
            (0x2A700, 0x2B734),
            (0x2B740, 0x2B81D),
            (0x2B820, 0x2CEA1),
            (0x2CEB0, 0x2EBE0),
            (0x2F800, 0x2FA1D),
        ]

    class Japanese(unicode_set):
        """Unicode set for Japanese Unicode Character Range, combining Kanji, Hiragana, and Katakana ranges"""

        class Kanji(unicode_set):
            "Unicode set for Kanji Unicode Character Range"
            _ranges: UnicodeRangeList = [
                (0x4E00, 0x9FBF),
                (0x3000, 0x303F),
            ]

        class Hiragana(unicode_set):
            """Unicode set for Hiragana Unicode Character Range"""
            _ranges: UnicodeRangeList = [
                (0x3041, 0x3096),
                (0x3099, 0x30A0),
                (0x30FC,),
                (0xFF70,),
                (0x1B001,),
                (0x1B150, 0x1B152),
                (0x1F200,),
            ]

        class Katakana(unicode_set):
            """Unicode set for Katakana  Unicode Character Range"""
            _ranges: UnicodeRangeList = [
                (0x3099, 0x309C),
                (0x30A0, 0x30FF),
                (0x31F0, 0x31FF),
                (0x32D0, 0x32FE),
                (0xFF65, 0xFF9F),
                (0x1B000,),
                (0x1B164, 0x1B167),
                (0x1F201, 0x1F202),
                (0x1F213,),
            ]

        漢字 = Kanji
        カタカナ = Katakana
        ひらがな = Hiragana

        _ranges = (
            Kanji._ranges
            + Hiragana._ranges
            + Katakana._ranges
        )

    class Hangul(unicode_set):
        """Unicode set for Hangul (Korean) Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x1100, 0x11FF),
            (0x302E, 0x302F),
            (0x3131, 0x318E),
            (0x3200, 0x321C),
            (0x3260, 0x327B),
            (0x327E,),
            (0xA960, 0xA97C),
            (0xAC00, 0xD7A3),
            (0xD7B0, 0xD7C6),
            (0xD7CB, 0xD7FB),
            (0xFFA0, 0xFFBE),
            (0xFFC2, 0xFFC7),
            (0xFFCA, 0xFFCF),
            (0xFFD2, 0xFFD7),
            (0xFFDA, 0xFFDC),
        ]

    Korean = Hangul

    class CJK(Chinese, Japanese, Hangul):
        """Unicode set for combined Chinese, Japanese, and Korean (CJK) Unicode Character Range"""

    class Thai(unicode_set):
        """Unicode set for Thai Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0E01, 0x0E3A),
            (0x0E3F, 0x0E5B)
        ]

    class Arabic(unicode_set):
        """Unicode set for Arabic Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0600, 0x061B),
            (0x061E, 0x06FF),
            (0x0700, 0x077F),
        ]

    class Hebrew(unicode_set):
        """Unicode set for Hebrew Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0591, 0x05C7),
            (0x05D0, 0x05EA),
            (0x05EF, 0x05F4),
            (0xFB1D, 0xFB36),
            (0xFB38, 0xFB3C),
            (0xFB3E,),
            (0xFB40, 0xFB41),
            (0xFB43, 0xFB44),
            (0xFB46, 0xFB4F),
        ]

    class Devanagari(unicode_set):
        """Unicode set for Devanagari Unicode Character Range"""
        _ranges: UnicodeRangeList = [
            (0x0900, 0x097F),
            (0xA8E0, 0xA8FF)
        ]

    BMP = BasicMultilingualPlane

    # add language identifiers using language Unicode
    العربية = Arabic
    中文 = Chinese
    кириллица = Cyrillic
    Ελληνικά = Greek
    עִברִית = Hebrew
    日本語 = Japanese
    한국어 = Korean
    ไทย = Thai
    देवनागरी = Devanagari

    # fmt: on

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\discuss_service.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "GenerateMessageRequest",
        "GenerateMessageResponse",
        "Message",
        "MessagePrompt",
        "Example",
        "CountMessageTokensRequest",
        "CountMessageTokensResponse",
    },
)


class GenerateMessageRequest(proto.Message):
    r"""Request to generate a message response from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the model to use.

            Format: ``name=models/{model}``.
        prompt (google.ai.generativelanguage_v1beta.types.MessagePrompt):
            Required. The structured textual input given
            to the model as a prompt.
            Given a
            prompt, the model will return what it predicts
            is the next message in the discussion.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Optional. The number of generated response messages to
            return.

            This value must be between ``[1, 8]``, inclusive. If unset,
            this will default to ``1``.

            This field is a member of `oneof`_ ``_candidate_count``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens.

            This field is a member of `oneof`_ ``_top_k``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=6,
        optional=True,
    )


class GenerateMessageResponse(proto.Message):
    r"""The response from the model.

    This includes candidate messages and
    conversation history in the form of chronologically-ordered
    messages.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta.types.Message]):
            Candidate response messages from the model.
        messages (MutableSequence[google.ai.generativelanguage_v1beta.types.Message]):
            The conversation history used by the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category.
    """

    candidates: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Message",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )


class Message(proto.Message):
    r"""The base unit of structured text.

    A ``Message`` includes an ``author`` and the ``content`` of the
    ``Message``.

    The ``author`` is used to tag messages when they are fed to the
    model as text.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        author (str):
            Optional. The author of this Message.

            This serves as a key for tagging
            the content of this Message when it is fed to
            the model as text.

            The author can be any alphanumeric string.
        content (str):
            Required. The text content of the structured ``Message``.
        citation_metadata (google.ai.generativelanguage_v1beta.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``content`` in this ``Message``.

            If this ``Message`` was generated as output from the model,
            this field may be populated with attribution information for
            any text included in the ``content``. This field is used
            only on output.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    author: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: str = proto.Field(
        proto.STRING,
        number=2,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class MessagePrompt(proto.Message):
    r"""All of the structured input text passed to the model as a prompt.

    A ``MessagePrompt`` contains a structured set of fields that provide
    context for the conversation, examples of user input/model output
    message pairs that prime the model to respond in different ways, and
    the conversation history or list of messages representing the
    alternating turns of the conversation between the user and the
    model.

    Attributes:
        context (str):
            Optional. Text that should be provided to the model first to
            ground the response.

            If not empty, this ``context`` will be given to the model
            first before the ``examples`` and ``messages``. When using a
            ``context`` be sure to provide it with every request to
            maintain continuity.

            This field can be a description of your prompt to the model
            to help provide context and guide the responses. Examples:
            "Translate the phrase from English to French." or "Given a
            statement, classify the sentiment as happy, sad or neutral."

            Anything included in this field will take precedence over
            message history if the total input size exceeds the model's
            ``input_token_limit`` and the input request is truncated.
        examples (MutableSequence[google.ai.generativelanguage_v1beta.types.Example]):
            Optional. Examples of what the model should generate.

            This includes both user input and the response that the
            model should emulate.

            These ``examples`` are treated identically to conversation
            messages except that they take precedence over the history
            in ``messages``: If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated. Items
            will be dropped from ``messages`` before ``examples``.
        messages (MutableSequence[google.ai.generativelanguage_v1beta.types.Message]):
            Required. A snapshot of the recent conversation history
            sorted chronologically.

            Turns alternate between two authors.

            If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated: The
            oldest items will be dropped from ``messages``.
    """

    context: str = proto.Field(
        proto.STRING,
        number=1,
    )
    examples: MutableSequence["Example"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Example",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="Message",
    )


class Example(proto.Message):
    r"""An input/output example used to instruct the Model.

    It demonstrates how the model should respond or format its
    response.

    Attributes:
        input (google.ai.generativelanguage_v1beta.types.Message):
            Required. An example of an input ``Message`` from the user.
        output (google.ai.generativelanguage_v1beta.types.Message):
            Required. An example of what the model should
            output given the input.
    """

    input: "Message" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    output: "Message" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="Message",
    )


class CountMessageTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        prompt (google.ai.generativelanguage_v1beta.types.MessagePrompt):
            Required. The prompt, whose token count is to
            be returned.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )


class CountMessageTokensResponse(proto.Message):
    r"""A response from ``CountMessageTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        token_count (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    token_count: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\types\discuss_service.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta2.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta2",
    manifest={
        "GenerateMessageRequest",
        "GenerateMessageResponse",
        "Message",
        "MessagePrompt",
        "Example",
        "CountMessageTokensRequest",
        "CountMessageTokensResponse",
    },
)


class GenerateMessageRequest(proto.Message):
    r"""Request to generate a message response from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the model to use.

            Format: ``name=models/{model}``.
        prompt (google.ai.generativelanguage_v1beta2.types.MessagePrompt):
            Required. The structured textual input given
            to the model as a prompt.
            Given a
            prompt, the model will return what it predicts
            is the next message in the discussion.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Optional. The number of generated response messages to
            return.

            This value must be between ``[1, 8]``, inclusive. If unset,
            this will default to ``1``.

            This field is a member of `oneof`_ ``_candidate_count``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens.

            This field is a member of `oneof`_ ``_top_k``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=6,
        optional=True,
    )


class GenerateMessageResponse(proto.Message):
    r"""The response from the model.

    This includes candidate messages and
    conversation history in the form of chronologically-ordered
    messages.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta2.types.Message]):
            Candidate response messages from the model.
        messages (MutableSequence[google.ai.generativelanguage_v1beta2.types.Message]):
            The conversation history used by the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta2.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category.
    """

    candidates: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Message",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )


class Message(proto.Message):
    r"""The base unit of structured text.

    A ``Message`` includes an ``author`` and the ``content`` of the
    ``Message``.

    The ``author`` is used to tag messages when they are fed to the
    model as text.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        author (str):
            Optional. The author of this Message.

            This serves as a key for tagging
            the content of this Message when it is fed to
            the model as text.

            The author can be any alphanumeric string.
        content (str):
            Required. The text content of the structured ``Message``.
        citation_metadata (google.ai.generativelanguage_v1beta2.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``content`` in this ``Message``.

            If this ``Message`` was generated as output from the model,
            this field may be populated with attribution information for
            any text included in the ``content``. This field is used
            only on output.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    author: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: str = proto.Field(
        proto.STRING,
        number=2,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class MessagePrompt(proto.Message):
    r"""All of the structured input text passed to the model as a prompt.

    A ``MessagePrompt`` contains a structured set of fields that provide
    context for the conversation, examples of user input/model output
    message pairs that prime the model to respond in different ways, and
    the conversation history or list of messages representing the
    alternating turns of the conversation between the user and the
    model.

    Attributes:
        context (str):
            Optional. Text that should be provided to the model first to
            ground the response.

            If not empty, this ``context`` will be given to the model
            first before the ``examples`` and ``messages``. When using a
            ``context`` be sure to provide it with every request to
            maintain continuity.

            This field can be a description of your prompt to the model
            to help provide context and guide the responses. Examples:
            "Translate the phrase from English to French." or "Given a
            statement, classify the sentiment as happy, sad or neutral."

            Anything included in this field will take precedence over
            message history if the total input size exceeds the model's
            ``input_token_limit`` and the input request is truncated.
        examples (MutableSequence[google.ai.generativelanguage_v1beta2.types.Example]):
            Optional. Examples of what the model should generate.

            This includes both user input and the response that the
            model should emulate.

            These ``examples`` are treated identically to conversation
            messages except that they take precedence over the history
            in ``messages``: If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated. Items
            will be dropped from ``messages`` before ``examples``.
        messages (MutableSequence[google.ai.generativelanguage_v1beta2.types.Message]):
            Required. A snapshot of the recent conversation history
            sorted chronologically.

            Turns alternate between two authors.

            If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated: The
            oldest items will be dropped from ``messages``.
    """

    context: str = proto.Field(
        proto.STRING,
        number=1,
    )
    examples: MutableSequence["Example"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Example",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="Message",
    )


class Example(proto.Message):
    r"""An input/output example used to instruct the Model.

    It demonstrates how the model should respond or format its
    response.

    Attributes:
        input (google.ai.generativelanguage_v1beta2.types.Message):
            Required. An example of an input ``Message`` from the user.
        output (google.ai.generativelanguage_v1beta2.types.Message):
            Required. An example of what the model should
            output given the input.
    """

    input: "Message" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    output: "Message" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="Message",
    )


class CountMessageTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        prompt (google.ai.generativelanguage_v1beta2.types.MessagePrompt):
            Required. The prompt, whose token count is to
            be returned.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )


class CountMessageTokensResponse(proto.Message):
    r"""A response from ``CountMessageTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        token_count (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    token_count: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\discuss_service.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta3.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "GenerateMessageRequest",
        "GenerateMessageResponse",
        "Message",
        "MessagePrompt",
        "Example",
        "CountMessageTokensRequest",
        "CountMessageTokensResponse",
    },
)


class GenerateMessageRequest(proto.Message):
    r"""Request to generate a message response from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the model to use.

            Format: ``name=models/{model}``.
        prompt (google.ai.generativelanguage_v1beta3.types.MessagePrompt):
            Required. The structured textual input given
            to the model as a prompt.
            Given a
            prompt, the model will return what it predicts
            is the next message in the discussion.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Optional. The number of generated response messages to
            return.

            This value must be between ``[1, 8]``, inclusive. If unset,
            this will default to ``1``.

            This field is a member of `oneof`_ ``_candidate_count``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens.

            This field is a member of `oneof`_ ``_top_k``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=6,
        optional=True,
    )


class GenerateMessageResponse(proto.Message):
    r"""The response from the model.

    This includes candidate messages and
    conversation history in the form of chronologically-ordered
    messages.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta3.types.Message]):
            Candidate response messages from the model.
        messages (MutableSequence[google.ai.generativelanguage_v1beta3.types.Message]):
            The conversation history used by the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta3.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category.
    """

    candidates: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Message",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )


class Message(proto.Message):
    r"""The base unit of structured text.

    A ``Message`` includes an ``author`` and the ``content`` of the
    ``Message``.

    The ``author`` is used to tag messages when they are fed to the
    model as text.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        author (str):
            Optional. The author of this Message.

            This serves as a key for tagging
            the content of this Message when it is fed to
            the model as text.

            The author can be any alphanumeric string.
        content (str):
            Required. The text content of the structured ``Message``.
        citation_metadata (google.ai.generativelanguage_v1beta3.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``content`` in this ``Message``.

            If this ``Message`` was generated as output from the model,
            this field may be populated with attribution information for
            any text included in the ``content``. This field is used
            only on output.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    author: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: str = proto.Field(
        proto.STRING,
        number=2,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class MessagePrompt(proto.Message):
    r"""All of the structured input text passed to the model as a prompt.

    A ``MessagePrompt`` contains a structured set of fields that provide
    context for the conversation, examples of user input/model output
    message pairs that prime the model to respond in different ways, and
    the conversation history or list of messages representing the
    alternating turns of the conversation between the user and the
    model.

    Attributes:
        context (str):
            Optional. Text that should be provided to the model first to
            ground the response.

            If not empty, this ``context`` will be given to the model
            first before the ``examples`` and ``messages``. When using a
            ``context`` be sure to provide it with every request to
            maintain continuity.

            This field can be a description of your prompt to the model
            to help provide context and guide the responses. Examples:
            "Translate the phrase from English to French." or "Given a
            statement, classify the sentiment as happy, sad or neutral."

            Anything included in this field will take precedence over
            message history if the total input size exceeds the model's
            ``input_token_limit`` and the input request is truncated.
        examples (MutableSequence[google.ai.generativelanguage_v1beta3.types.Example]):
            Optional. Examples of what the model should generate.

            This includes both user input and the response that the
            model should emulate.

            These ``examples`` are treated identically to conversation
            messages except that they take precedence over the history
            in ``messages``: If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated. Items
            will be dropped from ``messages`` before ``examples``.
        messages (MutableSequence[google.ai.generativelanguage_v1beta3.types.Message]):
            Required. A snapshot of the recent conversation history
            sorted chronologically.

            Turns alternate between two authors.

            If the total input size exceeds the model's
            ``input_token_limit`` the input will be truncated: The
            oldest items will be dropped from ``messages``.
    """

    context: str = proto.Field(
        proto.STRING,
        number=1,
    )
    examples: MutableSequence["Example"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Example",
    )
    messages: MutableSequence["Message"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="Message",
    )


class Example(proto.Message):
    r"""An input/output example used to instruct the Model.

    It demonstrates how the model should respond or format its
    response.

    Attributes:
        input (google.ai.generativelanguage_v1beta3.types.Message):
            Required. An example of an input ``Message`` from the user.
        output (google.ai.generativelanguage_v1beta3.types.Message):
            Required. An example of what the model should
            output given the input.
    """

    input: "Message" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="Message",
    )
    output: "Message" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="Message",
    )


class CountMessageTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        prompt (google.ai.generativelanguage_v1beta3.types.MessagePrompt):
            Required. The prompt, whose token count is to
            be returned.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "MessagePrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="MessagePrompt",
    )


class CountMessageTokensResponse(proto.Message):
    r"""A response from ``CountMessageTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        token_count (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    token_count: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\chat\v2_transformation.py ===
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.prompt_templates.factory import cohere_messages_pt_v2
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.cohere import CohereV2ChatResponse
from litellm.types.llms.openai import AllMessageValues, ChatCompletionToolCallChunk
from litellm.types.utils import ModelResponse, Usage

from ..common_utils import CohereError
from ..common_utils import ModelResponseIterator as CohereModelResponseIterator
from ..common_utils import validate_environment as cohere_validate_environment

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class CohereV2ChatConfig(BaseConfig):
    """
    Configuration class for Cohere's API interface.

    Args:
        preamble (str, optional): When specified, the default Cohere preamble will be replaced with the provided one.
        chat_history (List[Dict[str, str]], optional): A list of previous messages between the user and the model.
        generation_id (str, optional): Unique identifier for the generated reply.
        response_id (str, optional): Unique identifier for the response.
        conversation_id (str, optional): An alternative to chat_history, creates or resumes a persisted conversation.
        prompt_truncation (str, optional): Dictates how the prompt will be constructed. Options: 'AUTO', 'AUTO_PRESERVE_ORDER', 'OFF'.
        connectors (List[Dict[str, str]], optional): List of connectors (e.g., web-search) to enrich the model's reply.
        search_queries_only (bool, optional): When true, the response will only contain a list of generated search queries.
        documents (List[Dict[str, str]], optional): A list of relevant documents that the model can cite.
        temperature (float, optional): A non-negative float that tunes the degree of randomness in generation.
        max_tokens (int, optional): The maximum number of tokens the model will generate as part of the response.
        k (int, optional): Ensures only the top k most likely tokens are considered for generation at each step.
        p (float, optional): Ensures that only the most likely tokens, with total probability mass of p, are considered for generation.
        frequency_penalty (float, optional): Used to reduce repetitiveness of generated tokens.
        presence_penalty (float, optional): Used to reduce repetitiveness of generated tokens.
        tools (List[Dict[str, str]], optional): A list of available tools (functions) that the model may suggest invoking.
        tool_results (List[Dict[str, Any]], optional): A list of results from invoking tools.
        seed (int, optional): A seed to assist reproducibility of the model's response.
    """

    preamble: Optional[str] = None
    chat_history: Optional[list] = None
    generation_id: Optional[str] = None
    response_id: Optional[str] = None
    conversation_id: Optional[str] = None
    prompt_truncation: Optional[str] = None
    connectors: Optional[list] = None
    search_queries_only: Optional[bool] = None
    documents: Optional[list] = None
    temperature: Optional[int] = None
    max_tokens: Optional[int] = None
    k: Optional[int] = None
    p: Optional[int] = None
    frequency_penalty: Optional[int] = None
    presence_penalty: Optional[int] = None
    tools: Optional[list] = None
    tool_results: Optional[list] = None
    seed: Optional[int] = None

    def __init__(
        self,
        preamble: Optional[str] = None,
        chat_history: Optional[list] = None,
        generation_id: Optional[str] = None,
        response_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt_truncation: Optional[str] = None,
        connectors: Optional[list] = None,
        search_queries_only: Optional[bool] = None,
        documents: Optional[list] = None,
        temperature: Optional[int] = None,
        max_tokens: Optional[int] = None,
        k: Optional[int] = None,
        p: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        tools: Optional[list] = None,
        tool_results: Optional[list] = None,
        seed: Optional[int] = None,
    ) -> None:
        locals_ = locals()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        return cohere_validate_environment(
            headers=headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            api_key=api_key,
        )

    def get_supported_openai_params(self, model: str) -> List[str]:
        return [
            "stream",
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "n",
            "tools",
            "tool_choice",
            "seed",
            "extra_headers",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "stream":
                optional_params["stream"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "max_tokens":
                optional_params["max_tokens"] = value
            if param == "n":
                optional_params["num_generations"] = value
            if param == "top_p":
                optional_params["p"] = value
            if param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            if param == "presence_penalty":
                optional_params["presence_penalty"] = value
            if param == "stop":
                optional_params["stop_sequences"] = value
            if param == "tools":
                optional_params["tools"] = value
            if param == "seed":
                optional_params["seed"] = value
        return optional_params

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        ## Load Config
        for k, v in litellm.CohereChatConfig.get_config().items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > cohere_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        most_recent_message, chat_history = cohere_messages_pt_v2(
            messages=messages, model=model, llm_provider="cohere_chat"
        )

        ## Handle Tool Calling
        if "tools" in optional_params:
            _is_function_call = True
            cohere_tools = self._construct_cohere_tool(tools=optional_params["tools"])
            optional_params["tools"] = cohere_tools
        if isinstance(most_recent_message, dict):
            optional_params["tool_results"] = [most_recent_message]
        elif isinstance(most_recent_message, str):
            optional_params["message"] = most_recent_message

        ## check if chat history message is 'user' and 'tool_results' is given -> force_single_step=True, else cohere api fails
        if len(chat_history) > 0 and chat_history[-1]["role"] == "USER":
            optional_params["force_single_step"] = True

        return optional_params

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise CohereError(
                message=raw_response.text, status_code=raw_response.status_code
            )

        try:
            cohere_v2_chat_response = CohereV2ChatResponse(**raw_response_json)  # type: ignore
        except Exception:
            raise CohereError(message=raw_response.text, status_code=422)

        cohere_content = cohere_v2_chat_response["message"].get("content", None)
        if cohere_content is not None:
            model_response.choices[0].message.content = "".join(  # type: ignore
                [
                    content.get("text", "")
                    for content in cohere_content
                    if content is not None
                ]
            )

        ## ADD CITATIONS
        if "citations" in cohere_v2_chat_response:
            setattr(model_response, "citations", cohere_v2_chat_response["citations"])

        ## Tool calling response
        cohere_tools_response = cohere_v2_chat_response["message"].get("tool_calls", [])
        if cohere_tools_response is not None and cohere_tools_response != []:
            # convert cohere_tools_response to OpenAI response format
            tool_calls: List[ChatCompletionToolCallChunk] = []
            for index, tool in enumerate(cohere_tools_response):
                tool_call: ChatCompletionToolCallChunk = {
                    **tool,  # type: ignore
                    "index": index,
                }
                tool_calls.append(tool_call)
            _message = litellm.Message(
                tool_calls=tool_calls,
                content=None,
            )
            model_response.choices[0].message = _message  # type: ignore

        ## CALCULATING USAGE - use cohere `billed_units` for returning usage
        token_usage = cohere_v2_chat_response["usage"].get("tokens", {})
        prompt_tokens = token_usage.get("input_tokens", 0)
        completion_tokens = token_usage.get("output_tokens", 0)

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def _construct_cohere_tool(
        self,
        tools: Optional[list] = None,
    ):
        if tools is None:
            tools = []
        cohere_tools = []
        for tool in tools:
            cohere_tool = self._translate_openai_tool_to_cohere(tool)
            cohere_tools.append(cohere_tool)
        return cohere_tools

    def _translate_openai_tool_to_cohere(
        self,
        openai_tool: dict,
    ):
        # cohere tools look like this
        """
        {
        "name": "query_daily_sales_report",
        "description": "Connects to a database to retrieve overall sales volumes and sales information for a given day.",
        "parameter_definitions": {
            "day": {
                "description": "Retrieves sales data for this day, formatted as YYYY-MM-DD.",
                "type": "str",
                "required": True
            }
        }
        }
        """

        # OpenAI tools look like this
        """
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
        """
        cohere_tool = {
            "name": openai_tool["function"]["name"],
            "description": openai_tool["function"]["description"],
            "parameter_definitions": {},
        }

        for param_name, param_def in openai_tool["function"]["parameters"][
            "properties"
        ].items():
            required_params = (
                openai_tool.get("function", {})
                .get("parameters", {})
                .get("required", [])
            )
            cohere_param_def = {
                "description": param_def.get("description", ""),
                "type": param_def.get("type", ""),
                "required": param_name in required_params,
            }
            cohere_tool["parameter_definitions"][param_name] = cohere_param_def

        return cohere_tool

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return CohereModelResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return CohereError(status_code=status_code, message=error_message)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\_parser.py ===
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

import ast
from typing import Any, List, NamedTuple, Optional, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        raise NotImplementedError


class Variable(Node):
    def serialize(self) -> str:
        return str(self)


class Value(Node):
    def serialize(self) -> str:
        return f'"{self}"'


class Op(Node):
    def serialize(self) -> str:
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
# MarkerAtom = Union[MarkerItem, List["MarkerAtom"]]
# MarkerList = List[Union["MarkerList", MarkerAtom, str]]
# mypy does not support recursive type definition
# https://github.com/python/mypy/issues/731
MarkerAtom = Any
MarkerList = List[Any]


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: List[str]
    specifier: str
    marker: Optional[MarkerList]


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> Tuple[str, str, Optional[MarkerList]]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> List[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> List[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: List[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of "
            "<=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )

# === NexusCore/openenv\Lib\site-packages\urllib3\http2\connection.py ===
from __future__ import annotations

import logging
import re
import threading
import types
import typing

import h2.config  # type: ignore[import-untyped]
import h2.connection  # type: ignore[import-untyped]
import h2.events  # type: ignore[import-untyped]

from .._base_connection import _TYPE_BODY
from .._collections import HTTPHeaderDict
from ..connection import HTTPSConnection, _get_default_user_agent
from ..exceptions import ConnectionError
from ..response import BaseHTTPResponse

orig_HTTPSConnection = HTTPSConnection

T = typing.TypeVar("T")

log = logging.getLogger(__name__)

RE_IS_LEGAL_HEADER_NAME = re.compile(rb"^[!#$%&'*+\-.^_`|~0-9a-z]+$")
RE_IS_ILLEGAL_HEADER_VALUE = re.compile(rb"[\0\x00\x0a\x0d\r\n]|^[ \r\n\t]|[ \r\n\t]$")


def _is_legal_header_name(name: bytes) -> bool:
    """
    "An implementation that validates fields according to the definitions in Sections
    5.1 and 5.5 of [HTTP] only needs an additional check that field names do not
    include uppercase characters." (https://httpwg.org/specs/rfc9113.html#n-field-validity)

    `http.client._is_legal_header_name` does not validate the field name according to the
    HTTP 1.1 spec, so we do that here, in addition to checking for uppercase characters.

    This does not allow for the `:` character in the header name, so should not
    be used to validate pseudo-headers.
    """
    return bool(RE_IS_LEGAL_HEADER_NAME.match(name))


def _is_illegal_header_value(value: bytes) -> bool:
    """
    "A field value MUST NOT contain the zero value (ASCII NUL, 0x00), line feed
    (ASCII LF, 0x0a), or carriage return (ASCII CR, 0x0d) at any position. A field
    value MUST NOT start or end with an ASCII whitespace character (ASCII SP or HTAB,
    0x20 or 0x09)." (https://httpwg.org/specs/rfc9113.html#n-field-validity)
    """
    return bool(RE_IS_ILLEGAL_HEADER_VALUE.search(value))


class _LockedObject(typing.Generic[T]):
    """
    A wrapper class that hides a specific object behind a lock.
    The goal here is to provide a simple way to protect access to an object
    that cannot safely be simultaneously accessed from multiple threads. The
    intended use of this class is simple: take hold of it with a context
    manager, which returns the protected object.
    """

    __slots__ = (
        "lock",
        "_obj",
    )

    def __init__(self, obj: T):
        self.lock = threading.RLock()
        self._obj = obj

    def __enter__(self) -> T:
        self.lock.acquire()
        return self._obj

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.lock.release()


class HTTP2Connection(HTTPSConnection):
    def __init__(
        self, host: str, port: int | None = None, **kwargs: typing.Any
    ) -> None:
        self._h2_conn = self._new_h2_conn()
        self._h2_stream: int | None = None
        self._headers: list[tuple[bytes, bytes]] = []

        if "proxy" in kwargs or "proxy_config" in kwargs:  # Defensive:
            raise NotImplementedError("Proxies aren't supported with HTTP/2")

        super().__init__(host, port, **kwargs)

        if self._tunnel_host is not None:
            raise NotImplementedError("Tunneling isn't supported with HTTP/2")

    def _new_h2_conn(self) -> _LockedObject[h2.connection.H2Connection]:
        config = h2.config.H2Configuration(client_side=True)
        return _LockedObject(h2.connection.H2Connection(config=config))

    def connect(self) -> None:
        super().connect()
        with self._h2_conn as conn:
            conn.initiate_connection()
            if data_to_send := conn.data_to_send():
                self.sock.sendall(data_to_send)

    def putrequest(  # type: ignore[override]
        self,
        method: str,
        url: str,
        **kwargs: typing.Any,
    ) -> None:
        """putrequest
        This deviates from the HTTPConnection method signature since we never need to override
        sending accept-encoding headers or the host header.
        """
        if "skip_host" in kwargs:
            raise NotImplementedError("`skip_host` isn't supported")
        if "skip_accept_encoding" in kwargs:
            raise NotImplementedError("`skip_accept_encoding` isn't supported")

        self._request_url = url or "/"
        self._validate_path(url)  # type: ignore[attr-defined]

        if ":" in self.host:
            authority = f"[{self.host}]:{self.port or 443}"
        else:
            authority = f"{self.host}:{self.port or 443}"

        self._headers.append((b":scheme", b"https"))
        self._headers.append((b":method", method.encode()))
        self._headers.append((b":authority", authority.encode()))
        self._headers.append((b":path", url.encode()))

        with self._h2_conn as conn:
            self._h2_stream = conn.get_next_available_stream_id()

    def putheader(self, header: str | bytes, *values: str | bytes) -> None:  # type: ignore[override]
        # TODO SKIPPABLE_HEADERS from urllib3 are ignored.
        header = header.encode() if isinstance(header, str) else header
        header = header.lower()  # A lot of upstream code uses capitalized headers.
        if not _is_legal_header_name(header):
            raise ValueError(f"Illegal header name {str(header)}")

        for value in values:
            value = value.encode() if isinstance(value, str) else value
            if _is_illegal_header_value(value):
                raise ValueError(f"Illegal header value {str(value)}")
            self._headers.append((header, value))

    def endheaders(self, message_body: typing.Any = None) -> None:  # type: ignore[override]
        if self._h2_stream is None:
            raise ConnectionError("Must call `putrequest` first.")

        with self._h2_conn as conn:
            conn.send_headers(
                stream_id=self._h2_stream,
                headers=self._headers,
                end_stream=(message_body is None),
            )
            if data_to_send := conn.data_to_send():
                self.sock.sendall(data_to_send)
        self._headers = []  # Reset headers for the next request.

    def send(self, data: typing.Any) -> None:
        """Send data to the server.
        `data` can be: `str`, `bytes`, an iterable, or file-like objects
        that support a .read() method.
        """
        if self._h2_stream is None:
            raise ConnectionError("Must call `putrequest` first.")

        with self._h2_conn as conn:
            if data_to_send := conn.data_to_send():
                self.sock.sendall(data_to_send)

            if hasattr(data, "read"):  # file-like objects
                while True:
                    chunk = data.read(self.blocksize)
                    if not chunk:
                        break
                    if isinstance(chunk, str):
                        chunk = chunk.encode()  # pragma: no cover
                    conn.send_data(self._h2_stream, chunk, end_stream=False)
                    if data_to_send := conn.data_to_send():
                        self.sock.sendall(data_to_send)
                conn.end_stream(self._h2_stream)
                return

            if isinstance(data, str):  # str -> bytes
                data = data.encode()

            try:
                if isinstance(data, bytes):
                    conn.send_data(self._h2_stream, data, end_stream=True)
                    if data_to_send := conn.data_to_send():
                        self.sock.sendall(data_to_send)
                else:
                    for chunk in data:
                        conn.send_data(self._h2_stream, chunk, end_stream=False)
                        if data_to_send := conn.data_to_send():
                            self.sock.sendall(data_to_send)
                    conn.end_stream(self._h2_stream)
            except TypeError:
                raise TypeError(
                    "`data` should be str, bytes, iterable, or file. got %r"
                    % type(data)
                )

    def set_tunnel(
        self,
        host: str,
        port: int | None = None,
        headers: typing.Mapping[str, str] | None = None,
        scheme: str = "http",
    ) -> None:
        raise NotImplementedError(
            "HTTP/2 does not support setting up a tunnel through a proxy"
        )

    def getresponse(  # type: ignore[override]
        self,
    ) -> HTTP2Response:
        status = None
        data = bytearray()
        with self._h2_conn as conn:
            end_stream = False
            while not end_stream:
                # TODO: Arbitrary read value.
                if received_data := self.sock.recv(65535):
                    events = conn.receive_data(received_data)
                    for event in events:
                        if isinstance(event, h2.events.ResponseReceived):
                            headers = HTTPHeaderDict()
                            for header, value in event.headers:
                                if header == b":status":
                                    status = int(value.decode())
                                else:
                                    headers.add(
                                        header.decode("ascii"), value.decode("ascii")
                                    )

                        elif isinstance(event, h2.events.DataReceived):
                            data += event.data
                            conn.acknowledge_received_data(
                                event.flow_controlled_length, event.stream_id
                            )

                        elif isinstance(event, h2.events.StreamEnded):
                            end_stream = True

                if data_to_send := conn.data_to_send():
                    self.sock.sendall(data_to_send)

        assert status is not None
        return HTTP2Response(
            status=status,
            headers=headers,
            request_url=self._request_url,
            data=bytes(data),
        )

    def request(  # type: ignore[override]
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        *,
        preload_content: bool = True,
        decode_content: bool = True,
        enforce_content_length: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        """Send an HTTP/2 request"""
        if "chunked" in kwargs:
            # TODO this is often present from upstream.
            # raise NotImplementedError("`chunked` isn't supported with HTTP/2")
            pass

        if self.sock is not None:
            self.sock.settimeout(self.timeout)

        self.putrequest(method, url)

        headers = headers or {}
        for k, v in headers.items():
            if k.lower() == "transfer-encoding" and v == "chunked":
                continue
            else:
                self.putheader(k, v)

        if b"user-agent" not in dict(self._headers):
            self.putheader(b"user-agent", _get_default_user_agent())

        if body:
            self.endheaders(message_body=body)
            self.send(body)
        else:
            self.endheaders()

    def close(self) -> None:
        with self._h2_conn as conn:
            try:
                conn.close_connection()
                if data := conn.data_to_send():
                    self.sock.sendall(data)
            except Exception:
                pass

        # Reset all our HTTP/2 connection state.
        self._h2_conn = self._new_h2_conn()
        self._h2_stream = None
        self._headers = []

        super().close()


class HTTP2Response(BaseHTTPResponse):
    # TODO: This is a woefully incomplete response object, but works for non-streaming.
    def __init__(
        self,
        status: int,
        headers: HTTPHeaderDict,
        request_url: str,
        data: bytes,
        decode_content: bool = False,  # TODO: support decoding
    ) -> None:
        super().__init__(
            status=status,
            headers=headers,
            # Following CPython, we map HTTP versions to major * 10 + minor integers
            version=20,
            version_string="HTTP/2",
            # No reason phrase in HTTP/2
            reason=None,
            decode_content=decode_content,
            request_url=request_url,
        )
        self._data = data
        self.length_remaining = 0

    @property
    def data(self) -> bytes:
        return self._data

    def get_redirect_location(self) -> None:
        return None

    def close(self) -> None:
        pass

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\_collections.py ===
from __future__ import absolute_import

try:
    from collections.abc import Mapping, MutableMapping
except ImportError:
    from collections import Mapping, MutableMapping
try:
    from threading import RLock
except ImportError:  # Platform-specific: No threads available

    class RLock:
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            pass


from collections import OrderedDict

from .exceptions import InvalidHeader
from .packages import six
from .packages.six import iterkeys, itervalues

__all__ = ["RecentlyUsedContainer", "HTTPHeaderDict"]


_Null = object()


class RecentlyUsedContainer(MutableMapping):
    """
    Provides a thread-safe dict-like container which maintains up to
    ``maxsize`` keys while throwing away the least-recently-used keys beyond
    ``maxsize``.

    :param maxsize:
        Maximum number of recent elements to retain.

    :param dispose_func:
        Every time an item is evicted from the container,
        ``dispose_func(value)`` is called.  Callback which will get called
    """

    ContainerCls = OrderedDict

    def __init__(self, maxsize=10, dispose_func=None):
        self._maxsize = maxsize
        self.dispose_func = dispose_func

        self._container = self.ContainerCls()
        self.lock = RLock()

    def __getitem__(self, key):
        # Re-insert the item, moving it to the end of the eviction line.
        with self.lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key, value):
        evicted_value = _Null
        with self.lock:
            # Possibly evict the existing value of 'key'
            evicted_value = self._container.get(key, _Null)
            self._container[key] = value

            # If we didn't evict an existing value, we might have to evict the
            # least recently used item from the beginning of the container.
            if len(self._container) > self._maxsize:
                _key, evicted_value = self._container.popitem(last=False)

        if self.dispose_func and evicted_value is not _Null:
            self.dispose_func(evicted_value)

    def __delitem__(self, key):
        with self.lock:
            value = self._container.pop(key)

        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self):
        with self.lock:
            return len(self._container)

    def __iter__(self):
        raise NotImplementedError(
            "Iteration over this class is unlikely to be threadsafe."
        )

    def clear(self):
        with self.lock:
            # Copy pointers to all values, then wipe the mapping
            values = list(itervalues(self._container))
            self._container.clear()

        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self):
        with self.lock:
            return list(iterkeys(self._container))


class HTTPHeaderDict(MutableMapping):
    """
    :param headers:
        An iterable of field-value pairs. Must not contain multiple field names
        when compared case-insensitively.

    :param kwargs:
        Additional field-value pairs to pass in to ``dict.update``.

    A ``dict`` like container for storing HTTP Headers.

    Field names are stored and compared case-insensitively in compliance with
    RFC 7230. Iteration provides the first case-sensitive key seen for each
    case-insensitive pair.

    Using ``__setitem__`` syntax overwrites fields that compare equal
    case-insensitively in order to maintain ``dict``'s api. For fields that
    compare equal, instead create a new ``HTTPHeaderDict`` and use ``.add``
    in a loop.

    If multiple fields that are equal case-insensitively are passed to the
    constructor or ``.update``, the behavior is undefined and some will be
    lost.

    >>> headers = HTTPHeaderDict()
    >>> headers.add('Set-Cookie', 'foo=bar')
    >>> headers.add('set-cookie', 'baz=quxx')
    >>> headers['content-length'] = '7'
    >>> headers['SET-cookie']
    'foo=bar, baz=quxx'
    >>> headers['Content-Length']
    '7'
    """

    def __init__(self, headers=None, **kwargs):
        super(HTTPHeaderDict, self).__init__()
        self._container = OrderedDict()
        if headers is not None:
            if isinstance(headers, HTTPHeaderDict):
                self._copy_from(headers)
            else:
                self.extend(headers)
        if kwargs:
            self.extend(kwargs)

    def __setitem__(self, key, val):
        self._container[key.lower()] = [key, val]
        return self._container[key.lower()]

    def __getitem__(self, key):
        val = self._container[key.lower()]
        return ", ".join(val[1:])

    def __delitem__(self, key):
        del self._container[key.lower()]

    def __contains__(self, key):
        return key.lower() in self._container

    def __eq__(self, other):
        if not isinstance(other, Mapping) and not hasattr(other, "keys"):
            return False
        if not isinstance(other, type(self)):
            other = type(self)(other)
        return dict((k.lower(), v) for k, v in self.itermerged()) == dict(
            (k.lower(), v) for k, v in other.itermerged()
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    if six.PY2:  # Python 2
        iterkeys = MutableMapping.iterkeys
        itervalues = MutableMapping.itervalues

    __marker = object()

    def __len__(self):
        return len(self._container)

    def __iter__(self):
        # Only provide the originally cased names
        for vals in self._container.values():
            yield vals[0]

    def pop(self, key, default=__marker):
        """D.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.
        """
        # Using the MutableMapping function directly fails due to the private marker.
        # Using ordinary dict.pop would expose the internal structures.
        # So let's reinvent the wheel.
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def discard(self, key):
        try:
            del self[key]
        except KeyError:
            pass

    def add(self, key, val):
        """Adds a (name, value) pair, doesn't overwrite the value if it already
        exists.

        >>> headers = HTTPHeaderDict(foo='bar')
        >>> headers.add('Foo', 'baz')
        >>> headers['foo']
        'bar, baz'
        """
        key_lower = key.lower()
        new_vals = [key, val]
        # Keep the common case aka no item present as fast as possible
        vals = self._container.setdefault(key_lower, new_vals)
        if new_vals is not vals:
            vals.append(val)

    def extend(self, *args, **kwargs):
        """Generic import function for any type of header-like object.
        Adapted version of MutableMapping.update in order to insert items
        with self.add instead of self.__setitem__
        """
        if len(args) > 1:
            raise TypeError(
                "extend() takes at most 1 positional "
                "arguments ({0} given)".format(len(args))
            )
        other = args[0] if len(args) >= 1 else ()

        if isinstance(other, HTTPHeaderDict):
            for key, val in other.iteritems():
                self.add(key, val)
        elif isinstance(other, Mapping):
            for key in other:
                self.add(key, other[key])
        elif hasattr(other, "keys"):
            for key in other.keys():
                self.add(key, other[key])
        else:
            for key, value in other:
                self.add(key, value)

        for key, value in kwargs.items():
            self.add(key, value)

    def getlist(self, key, default=__marker):
        """Returns a list of all the values for the named field. Returns an
        empty list if the key doesn't exist."""
        try:
            vals = self._container[key.lower()]
        except KeyError:
            if default is self.__marker:
                return []
            return default
        else:
            return vals[1:]

    def _prepare_for_method_change(self):
        """
        Remove content-specific header fields before changing the request
        method to GET or HEAD according to RFC 9110, Section 15.4.
        """
        content_specific_headers = [
            "Content-Encoding",
            "Content-Language",
            "Content-Location",
            "Content-Type",
            "Content-Length",
            "Digest",
            "Last-Modified",
        ]
        for header in content_specific_headers:
            self.discard(header)
        return self

    # Backwards compatibility for httplib
    getheaders = getlist
    getallmatchingheaders = getlist
    iget = getlist

    # Backwards compatibility for http.cookiejar
    get_all = getlist

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict(self.itermerged()))

    def _copy_from(self, other):
        for key in other:
            val = other.getlist(key)
            if isinstance(val, list):
                # Don't need to convert tuples
                val = list(val)
            self._container[key.lower()] = [key] + val

    def copy(self):
        clone = type(self)()
        clone._copy_from(self)
        return clone

    def iteritems(self):
        """Iterate over all header lines, including duplicate ones."""
        for key in self:
            vals = self._container[key.lower()]
            for val in vals[1:]:
                yield vals[0], val

    def itermerged(self):
        """Iterate over all headers, merging duplicate ones together."""
        for key in self:
            val = self._container[key.lower()]
            yield val[0], ", ".join(val[1:])

    def items(self):
        return list(self.iteritems())

    @classmethod
    def from_httplib(cls, message):  # Python 2
        """Read headers from a Python 2 httplib message object."""
        # python2.7 does not expose a proper API for exporting multiheaders
        # efficiently. This function re-reads raw lines from the message
        # object and extracts the multiheaders properly.
        obs_fold_continued_leaders = (" ", "\t")
        headers = []

        for line in message.headers:
            if line.startswith(obs_fold_continued_leaders):
                if not headers:
                    # We received a header line that starts with OWS as described
                    # in RFC-7230 S3.2.4. This indicates a multiline header, but
                    # there exists no previous header to which we can attach it.
                    raise InvalidHeader(
                        "Header continuation with no previous header: %s" % line
                    )
                else:
                    key, value = headers[-1]
                    headers[-1] = (key, value + " " + line.strip())
                    continue

            key, value = line.split(":", 1)
            headers.append((key, value.strip()))

        return cls(headers)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\community.py ===
"""
Data structures to interact with Discussions and Pull Requests on the Hub.

See [the Discussions and Pull Requests guide](https://huggingface.co/docs/hub/repositories-pull-requests-discussions)
for more information on Pull Requests, Discussions, and the community tab.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal, Optional, Union

from . import constants
from .utils import parse_datetime


DiscussionStatus = Literal["open", "closed", "merged", "draft"]


@dataclass
class Discussion:
    """
    A Discussion or Pull Request on the Hub.

    This dataclass is not intended to be instantiated directly.

    Attributes:
        title (`str`):
            The title of the Discussion / Pull Request
        status (`str`):
            The status of the Discussion / Pull Request.
            It must be one of:
                * `"open"`
                * `"closed"`
                * `"merged"` (only for Pull Requests )
                * `"draft"` (only for Pull Requests )
        num (`int`):
            The number of the Discussion / Pull Request.
        repo_id (`str`):
            The id (`"{namespace}/{repo_name}"`) of the repo on which
            the Discussion / Pull Request was open.
        repo_type (`str`):
            The type of the repo on which the Discussion / Pull Request was open.
            Possible values are: `"model"`, `"dataset"`, `"space"`.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        is_pull_request (`bool`):
            Whether or not this is a Pull Request.
        created_at (`datetime`):
            The `datetime` of creation of the Discussion / Pull Request.
        endpoint (`str`):
            Endpoint of the Hub. Default is https://huggingface.co.
        git_reference (`str`, *optional*):
            (property) Git reference to which changes can be pushed if this is a Pull Request, `None` otherwise.
        url (`str`):
            (property) URL of the discussion on the Hub.
    """

    title: str
    status: DiscussionStatus
    num: int
    repo_id: str
    repo_type: str
    author: str
    is_pull_request: bool
    created_at: datetime
    endpoint: str

    @property
    def git_reference(self) -> Optional[str]:
        """
        If this is a Pull Request , returns the git reference to which changes can be pushed.
        Returns `None` otherwise.
        """
        if self.is_pull_request:
            return f"refs/pr/{self.num}"
        return None

    @property
    def url(self) -> str:
        """Returns the URL of the discussion on the Hub."""
        if self.repo_type is None or self.repo_type == constants.REPO_TYPE_MODEL:
            return f"{self.endpoint}/{self.repo_id}/discussions/{self.num}"
        return f"{self.endpoint}/{self.repo_type}s/{self.repo_id}/discussions/{self.num}"


@dataclass
class DiscussionWithDetails(Discussion):
    """
    Subclass of [`Discussion`].

    Attributes:
        title (`str`):
            The title of the Discussion / Pull Request
        status (`str`):
            The status of the Discussion / Pull Request.
            It can be one of:
                * `"open"`
                * `"closed"`
                * `"merged"` (only for Pull Requests )
                * `"draft"` (only for Pull Requests )
        num (`int`):
            The number of the Discussion / Pull Request.
        repo_id (`str`):
            The id (`"{namespace}/{repo_name}"`) of the repo on which
            the Discussion / Pull Request was open.
        repo_type (`str`):
            The type of the repo on which the Discussion / Pull Request was open.
            Possible values are: `"model"`, `"dataset"`, `"space"`.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        is_pull_request (`bool`):
            Whether or not this is a Pull Request.
        created_at (`datetime`):
            The `datetime` of creation of the Discussion / Pull Request.
        events (`list` of [`DiscussionEvent`])
            The list of [`DiscussionEvents`] in this Discussion or Pull Request.
        conflicting_files (`Union[List[str], bool, None]`, *optional*):
            A list of conflicting files if this is a Pull Request.
            `None` if `self.is_pull_request` is `False`.
            `True` if there are conflicting files but the list can't be retrieved.
        target_branch (`str`, *optional*):
            The branch into which changes are to be merged if this is a
            Pull Request . `None`  if `self.is_pull_request` is `False`.
        merge_commit_oid (`str`, *optional*):
            If this is a merged Pull Request , this is set to the OID / SHA of
            the merge commit, `None` otherwise.
        diff (`str`, *optional*):
            The git diff if this is a Pull Request , `None` otherwise.
        endpoint (`str`):
            Endpoint of the Hub. Default is https://huggingface.co.
        git_reference (`str`, *optional*):
            (property) Git reference to which changes can be pushed if this is a Pull Request, `None` otherwise.
        url (`str`):
            (property) URL of the discussion on the Hub.
    """

    events: List["DiscussionEvent"]
    conflicting_files: Union[List[str], bool, None]
    target_branch: Optional[str]
    merge_commit_oid: Optional[str]
    diff: Optional[str]


@dataclass
class DiscussionEvent:
    """
    An event in a Discussion or Pull Request.

    Use concrete classes:
        * [`DiscussionComment`]
        * [`DiscussionStatusChange`]
        * [`DiscussionCommit`]
        * [`DiscussionTitleChange`]

    Attributes:
        id (`str`):
            The ID of the event. An hexadecimal string.
        type (`str`):
            The type of the event.
        created_at (`datetime`):
            A [`datetime`](https://docs.python.org/3/library/datetime.html?highlight=datetime#datetime.datetime)
            object holding the creation timestamp for the event.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
    """

    id: str
    type: str
    created_at: datetime
    author: str

    _event: dict
    """Stores the original event data, in case we need to access it later."""


@dataclass
class DiscussionComment(DiscussionEvent):
    """A comment in a Discussion / Pull Request.

    Subclass of [`DiscussionEvent`].


    Attributes:
        id (`str`):
            The ID of the event. An hexadecimal string.
        type (`str`):
            The type of the event.
        created_at (`datetime`):
            A [`datetime`](https://docs.python.org/3/library/datetime.html?highlight=datetime#datetime.datetime)
            object holding the creation timestamp for the event.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        content (`str`):
            The raw markdown content of the comment. Mentions, links and images are not rendered.
        edited (`bool`):
            Whether or not this comment has been edited.
        hidden (`bool`):
            Whether or not this comment has been hidden.
    """

    content: str
    edited: bool
    hidden: bool

    @property
    def rendered(self) -> str:
        """The rendered comment, as a HTML string"""
        return self._event["data"]["latest"]["html"]

    @property
    def last_edited_at(self) -> datetime:
        """The last edit time, as a `datetime` object."""
        return parse_datetime(self._event["data"]["latest"]["updatedAt"])

    @property
    def last_edited_by(self) -> str:
        """The last edit time, as a `datetime` object."""
        return self._event["data"]["latest"].get("author", {}).get("name", "deleted")

    @property
    def edit_history(self) -> List[dict]:
        """The edit history of the comment"""
        return self._event["data"]["history"]

    @property
    def number_of_edits(self) -> int:
        return len(self.edit_history)


@dataclass
class DiscussionStatusChange(DiscussionEvent):
    """A change of status in a Discussion / Pull Request.

    Subclass of [`DiscussionEvent`].

    Attributes:
        id (`str`):
            The ID of the event. An hexadecimal string.
        type (`str`):
            The type of the event.
        created_at (`datetime`):
            A [`datetime`](https://docs.python.org/3/library/datetime.html?highlight=datetime#datetime.datetime)
            object holding the creation timestamp for the event.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        new_status (`str`):
            The status of the Discussion / Pull Request after the change.
            It can be one of:
                * `"open"`
                * `"closed"`
                * `"merged"` (only for Pull Requests )
    """

    new_status: str


@dataclass
class DiscussionCommit(DiscussionEvent):
    """A commit in a Pull Request.

    Subclass of [`DiscussionEvent`].

    Attributes:
        id (`str`):
            The ID of the event. An hexadecimal string.
        type (`str`):
            The type of the event.
        created_at (`datetime`):
            A [`datetime`](https://docs.python.org/3/library/datetime.html?highlight=datetime#datetime.datetime)
            object holding the creation timestamp for the event.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        summary (`str`):
            The summary of the commit.
        oid (`str`):
            The OID / SHA of the commit, as a hexadecimal string.
    """

    summary: str
    oid: str


@dataclass
class DiscussionTitleChange(DiscussionEvent):
    """A rename event in a Discussion / Pull Request.

    Subclass of [`DiscussionEvent`].

    Attributes:
        id (`str`):
            The ID of the event. An hexadecimal string.
        type (`str`):
            The type of the event.
        created_at (`datetime`):
            A [`datetime`](https://docs.python.org/3/library/datetime.html?highlight=datetime#datetime.datetime)
            object holding the creation timestamp for the event.
        author (`str`):
            The username of the Discussion / Pull Request author.
            Can be `"deleted"` if the user has been deleted since.
        old_title (`str`):
            The previous title for the Discussion / Pull Request.
        new_title (`str`):
            The new title.
    """

    old_title: str
    new_title: str


def deserialize_event(event: dict) -> DiscussionEvent:
    """Instantiates a [`DiscussionEvent`] from a dict"""
    event_id: str = event["id"]
    event_type: str = event["type"]
    created_at = parse_datetime(event["createdAt"])

    common_args = dict(
        id=event_id,
        type=event_type,
        created_at=created_at,
        author=event.get("author", {}).get("name", "deleted"),
        _event=event,
    )

    if event_type == "comment":
        return DiscussionComment(
            **common_args,
            edited=event["data"]["edited"],
            hidden=event["data"]["hidden"],
            content=event["data"]["latest"]["raw"],
        )
    if event_type == "status-change":
        return DiscussionStatusChange(
            **common_args,
            new_status=event["data"]["status"],
        )
    if event_type == "commit":
        return DiscussionCommit(
            **common_args,
            summary=event["data"]["subject"],
            oid=event["data"]["oid"],
        )
    if event_type == "title-change":
        return DiscussionTitleChange(
            **common_args,
            old_title=event["data"]["from"],
            new_title=event["data"]["to"],
        )

    return DiscussionEvent(**common_args)

# === NexusCore/openenv\Lib\site-packages\jsonschema\_utils.py ===
from collections.abc import Mapping, MutableMapping, Sequence
from urllib.parse import urlsplit
import itertools
import re


class URIDict(MutableMapping):
    """
    Dictionary which uses normalized URIs as keys.
    """

    def normalize(self, uri):
        return urlsplit(uri).geturl()

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.store.update(*args, **kwargs)

    def __getitem__(self, uri):
        return self.store[self.normalize(uri)]

    def __setitem__(self, uri, value):
        self.store[self.normalize(uri)] = value

    def __delitem__(self, uri):
        del self.store[self.normalize(uri)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):  # pragma: no cover -- untested, but to be removed
        return len(self.store)

    def __repr__(self):  # pragma: no cover -- untested, but to be removed
        return repr(self.store)


class Unset:
    """
    An as-of-yet unset attribute or unprovided default parameter.
    """

    def __repr__(self):  # pragma: no cover
        return "<unset>"


def format_as_index(container, indices):
    """
    Construct a single string containing indexing operations for the indices.

    For example for a container ``bar``, [1, 2, "foo"] -> bar[1][2]["foo"]

    Arguments:

        container (str):

            A word to use for the thing being indexed

        indices (sequence):

            The indices to format.

    """
    if not indices:
        return container
    return f"{container}[{']['.join(repr(index) for index in indices)}]"


def find_additional_properties(instance, schema):
    """
    Return the set of additional properties for the given ``instance``.

    Weeds out properties that should have been validated by ``properties`` and
    / or ``patternProperties``.

    Assumes ``instance`` is dict-like already.
    """
    properties = schema.get("properties", {})
    patterns = "|".join(schema.get("patternProperties", {}))
    for property in instance:
        if property not in properties:
            if patterns and re.search(patterns, property):
                continue
            yield property


def extras_msg(extras):
    """
    Create an error message for extra items or properties.
    """
    verb = "was" if len(extras) == 1 else "were"
    return ", ".join(repr(extra) for extra in extras), verb


def ensure_list(thing):
    """
    Wrap ``thing`` in a list if it's a single str.

    Otherwise, return it unchanged.
    """
    if isinstance(thing, str):
        return [thing]
    return thing


def _mapping_equal(one, two):
    """
    Check if two mappings are equal using the semantics of `equal`.
    """
    if len(one) != len(two):
        return False
    return all(
        key in two and equal(value, two[key])
        for key, value in one.items()
    )


def _sequence_equal(one, two):
    """
    Check if two sequences are equal using the semantics of `equal`.
    """
    if len(one) != len(two):
        return False
    return all(equal(i, j) for i, j in zip(one, two))


def equal(one, two):
    """
    Check if two things are equal evading some Python type hierarchy semantics.

    Specifically in JSON Schema, evade `bool` inheriting from `int`,
    recursing into sequences to do the same.
    """
    if one is two:
        return True
    if isinstance(one, str) or isinstance(two, str):
        return one == two
    if isinstance(one, Sequence) and isinstance(two, Sequence):
        return _sequence_equal(one, two)
    if isinstance(one, Mapping) and isinstance(two, Mapping):
        return _mapping_equal(one, two)
    return unbool(one) == unbool(two)


def unbool(element, true=object(), false=object()):
    """
    A hack to make True and 1 and False and 0 unique for ``uniq``.
    """
    if element is True:
        return true
    elif element is False:
        return false
    return element


def uniq(container):
    """
    Check if all of a container's elements are unique.

    Tries to rely on the container being recursively sortable, or otherwise
    falls back on (slow) brute force.
    """
    try:
        sort = sorted(unbool(i) for i in container)
        sliced = itertools.islice(sort, 1, None)

        for i, j in zip(sort, sliced):
            if equal(i, j):
                return False

    except (NotImplementedError, TypeError):
        seen = []
        for e in container:
            e = unbool(e)

            for i in seen:
                if equal(i, e):
                    return False

            seen.append(e)
    return True


def find_evaluated_item_indexes_by_schema(validator, instance, schema):
    """
    Get all indexes of items that get evaluated under the current schema.

    Covers all keywords related to unevaluatedItems: items, prefixItems, if,
    then, else, contains, unevaluatedItems, allOf, oneOf, anyOf
    """
    if validator.is_type(schema, "boolean"):
        return []
    evaluated_indexes = []

    if "items" in schema:
        return list(range(len(instance)))

    ref = schema.get("$ref")
    if ref is not None:
        resolved = validator._resolver.lookup(ref)
        evaluated_indexes.extend(
            find_evaluated_item_indexes_by_schema(
                validator.evolve(
                    schema=resolved.contents,
                    _resolver=resolved.resolver,
                ),
                instance,
                resolved.contents,
            ),
        )

    dynamicRef = schema.get("$dynamicRef")
    if dynamicRef is not None:
        resolved = validator._resolver.lookup(dynamicRef)
        evaluated_indexes.extend(
            find_evaluated_item_indexes_by_schema(
                validator.evolve(
                    schema=resolved.contents,
                    _resolver=resolved.resolver,
                ),
                instance,
                resolved.contents,
            ),
        )

    if "prefixItems" in schema:
        evaluated_indexes += list(range(len(schema["prefixItems"])))

    if "if" in schema:
        if validator.evolve(schema=schema["if"]).is_valid(instance):
            evaluated_indexes += find_evaluated_item_indexes_by_schema(
                validator, instance, schema["if"],
            )
            if "then" in schema:
                evaluated_indexes += find_evaluated_item_indexes_by_schema(
                    validator, instance, schema["then"],
                )
        elif "else" in schema:
            evaluated_indexes += find_evaluated_item_indexes_by_schema(
                validator, instance, schema["else"],
            )

    for keyword in ["contains", "unevaluatedItems"]:
        if keyword in schema:
            for k, v in enumerate(instance):
                if validator.evolve(schema=schema[keyword]).is_valid(v):
                    evaluated_indexes.append(k)

    for keyword in ["allOf", "oneOf", "anyOf"]:
        if keyword in schema:
            for subschema in schema[keyword]:
                errs = next(validator.descend(instance, subschema), None)
                if errs is None:
                    evaluated_indexes += find_evaluated_item_indexes_by_schema(
                        validator, instance, subschema,
                    )

    return evaluated_indexes


def find_evaluated_property_keys_by_schema(validator, instance, schema):
    """
    Get all keys of items that get evaluated under the current schema.

    Covers all keywords related to unevaluatedProperties: properties,
    additionalProperties, unevaluatedProperties, patternProperties,
    dependentSchemas, allOf, oneOf, anyOf, if, then, else
    """
    if validator.is_type(schema, "boolean"):
        return []
    evaluated_keys = []

    ref = schema.get("$ref")
    if ref is not None:
        resolved = validator._resolver.lookup(ref)
        evaluated_keys.extend(
            find_evaluated_property_keys_by_schema(
                validator.evolve(
                    schema=resolved.contents,
                    _resolver=resolved.resolver,
                ),
                instance,
                resolved.contents,
            ),
        )

    dynamicRef = schema.get("$dynamicRef")
    if dynamicRef is not None:
        resolved = validator._resolver.lookup(dynamicRef)
        evaluated_keys.extend(
            find_evaluated_property_keys_by_schema(
                validator.evolve(
                    schema=resolved.contents,
                    _resolver=resolved.resolver,
                ),
                instance,
                resolved.contents,
            ),
        )

    properties = schema.get("properties")
    if validator.is_type(properties, "object"):
        evaluated_keys += properties.keys() & instance.keys()

    for keyword in ["additionalProperties", "unevaluatedProperties"]:
        if (subschema := schema.get(keyword)) is None:
            continue
        evaluated_keys += (
            key
            for key, value in instance.items()
            if is_valid(validator.descend(value, subschema))
        )

    if "patternProperties" in schema:
        for property in instance:
            for pattern in schema["patternProperties"]:
                if re.search(pattern, property):
                    evaluated_keys.append(property)

    if "dependentSchemas" in schema:
        for property, subschema in schema["dependentSchemas"].items():
            if property not in instance:
                continue
            evaluated_keys += find_evaluated_property_keys_by_schema(
                validator, instance, subschema,
            )

    for keyword in ["allOf", "oneOf", "anyOf"]:
        for subschema in schema.get(keyword, []):
            if not is_valid(validator.descend(instance, subschema)):
                continue
            evaluated_keys += find_evaluated_property_keys_by_schema(
                validator, instance, subschema,
            )

    if "if" in schema:
        if validator.evolve(schema=schema["if"]).is_valid(instance):
            evaluated_keys += find_evaluated_property_keys_by_schema(
                validator, instance, schema["if"],
            )
            if "then" in schema:
                evaluated_keys += find_evaluated_property_keys_by_schema(
                    validator, instance, schema["then"],
                )
        elif "else" in schema:
            evaluated_keys += find_evaluated_property_keys_by_schema(
                validator, instance, schema["else"],
            )

    return evaluated_keys


def is_valid(errs_it):
    """Whether there are no errors in the given iterator."""
    return next(errs_it, None) is None

# === NexusCore/openenv\Lib\site-packages\markdown_it\main.py ===
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping
from contextlib import contextmanager
from typing import Any, Literal, overload

from . import helpers, presets
from .common import normalize_url, utils
from .parser_block import ParserBlock
from .parser_core import ParserCore
from .parser_inline import ParserInline
from .renderer import RendererHTML, RendererProtocol
from .rules_core.state_core import StateCore
from .token import Token
from .utils import EnvType, OptionsDict, OptionsType, PresetType

try:
    import linkify_it
except ModuleNotFoundError:
    linkify_it = None


_PRESETS: dict[str, PresetType] = {
    "default": presets.default.make(),
    "js-default": presets.js_default.make(),
    "zero": presets.zero.make(),
    "commonmark": presets.commonmark.make(),
    "gfm-like": presets.gfm_like.make(),
}


class MarkdownIt:
    def __init__(
        self,
        config: str | PresetType = "commonmark",
        options_update: Mapping[str, Any] | None = None,
        *,
        renderer_cls: Callable[[MarkdownIt], RendererProtocol] = RendererHTML,
    ):
        """Main parser class

        :param config: name of configuration to load or a pre-defined dictionary
        :param options_update: dictionary that will be merged into ``config["options"]``
        :param renderer_cls: the class to load as the renderer:
            ``self.renderer = renderer_cls(self)
        """
        # add modules
        self.utils = utils
        self.helpers = helpers

        # initialise classes
        self.inline = ParserInline()
        self.block = ParserBlock()
        self.core = ParserCore()
        self.renderer = renderer_cls(self)
        self.linkify = linkify_it.LinkifyIt() if linkify_it else None

        # set the configuration
        if options_update and not isinstance(options_update, Mapping):
            # catch signature change where renderer_cls was not used as a key-word
            raise TypeError(
                f"options_update should be a mapping: {options_update}"
                "\n(Perhaps you intended this to be the renderer_cls?)"
            )
        self.configure(config, options_update=options_update)

    def __repr__(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}()"

    @overload
    def __getitem__(self, name: Literal["inline"]) -> ParserInline:
        ...

    @overload
    def __getitem__(self, name: Literal["block"]) -> ParserBlock:
        ...

    @overload
    def __getitem__(self, name: Literal["core"]) -> ParserCore:
        ...

    @overload
    def __getitem__(self, name: Literal["renderer"]) -> RendererProtocol:
        ...

    @overload
    def __getitem__(self, name: str) -> Any:
        ...

    def __getitem__(self, name: str) -> Any:
        return {
            "inline": self.inline,
            "block": self.block,
            "core": self.core,
            "renderer": self.renderer,
        }[name]

    def set(self, options: OptionsType) -> None:
        """Set parser options (in the same format as in constructor).
        Probably, you will never need it, but you can change options after constructor call.

        __Note:__ To achieve the best possible performance, don't modify a
        `markdown-it` instance options on the fly. If you need multiple configurations
        it's best to create multiple instances and initialize each with separate config.
        """
        self.options = OptionsDict(options)

    def configure(
        self, presets: str | PresetType, options_update: Mapping[str, Any] | None = None
    ) -> MarkdownIt:
        """Batch load of all options and component settings.
        This is an internal method, and you probably will not need it.
        But if you will - see available presets and data structure
        [here](https://github.com/markdown-it/markdown-it/tree/master/lib/presets)

        We strongly recommend to use presets instead of direct config loads.
        That will give better compatibility with next versions.
        """
        if isinstance(presets, str):
            if presets not in _PRESETS:
                raise KeyError(f"Wrong `markdown-it` preset '{presets}', check name")
            config = _PRESETS[presets]
        else:
            config = presets

        if not config:
            raise ValueError("Wrong `markdown-it` config, can't be empty")

        options = config.get("options", {}) or {}
        if options_update:
            options = {**options, **options_update}  # type: ignore

        self.set(options)  # type: ignore

        if "components" in config:
            for name, component in config["components"].items():
                rules = component.get("rules", None)
                if rules:
                    self[name].ruler.enableOnly(rules)
                rules2 = component.get("rules2", None)
                if rules2:
                    self[name].ruler2.enableOnly(rules2)

        return self

    def get_all_rules(self) -> dict[str, list[str]]:
        """Return the names of all active rules."""
        rules = {
            chain: self[chain].ruler.get_all_rules()
            for chain in ["core", "block", "inline"]
        }
        rules["inline2"] = self.inline.ruler2.get_all_rules()
        return rules

    def get_active_rules(self) -> dict[str, list[str]]:
        """Return the names of all active rules."""
        rules = {
            chain: self[chain].ruler.get_active_rules()
            for chain in ["core", "block", "inline"]
        }
        rules["inline2"] = self.inline.ruler2.get_active_rules()
        return rules

    def enable(
        self, names: str | Iterable[str], ignoreInvalid: bool = False
    ) -> MarkdownIt:
        """Enable list or rules. (chainable)

        :param names: rule name or list of rule names to enable.
        :param ignoreInvalid: set `true` to ignore errors when rule not found.

        It will automatically find appropriate components,
        containing rules with given names. If rule not found, and `ignoreInvalid`
        not set - throws exception.

        Example::

            md = MarkdownIt().enable(['sub', 'sup']).disable('smartquotes')

        """
        result = []

        if isinstance(names, str):
            names = [names]

        for chain in ["core", "block", "inline"]:
            result.extend(self[chain].ruler.enable(names, True))
        result.extend(self.inline.ruler2.enable(names, True))

        missed = [name for name in names if name not in result]
        if missed and not ignoreInvalid:
            raise ValueError(f"MarkdownIt. Failed to enable unknown rule(s): {missed}")

        return self

    def disable(
        self, names: str | Iterable[str], ignoreInvalid: bool = False
    ) -> MarkdownIt:
        """The same as [[MarkdownIt.enable]], but turn specified rules off. (chainable)

        :param names: rule name or list of rule names to disable.
        :param ignoreInvalid: set `true` to ignore errors when rule not found.

        """
        result = []

        if isinstance(names, str):
            names = [names]

        for chain in ["core", "block", "inline"]:
            result.extend(self[chain].ruler.disable(names, True))
        result.extend(self.inline.ruler2.disable(names, True))

        missed = [name for name in names if name not in result]
        if missed and not ignoreInvalid:
            raise ValueError(f"MarkdownIt. Failed to disable unknown rule(s): {missed}")
        return self

    @contextmanager
    def reset_rules(self) -> Generator[None, None, None]:
        """A context manager, that will reset the current enabled rules on exit."""
        chain_rules = self.get_active_rules()
        yield
        for chain, rules in chain_rules.items():
            if chain != "inline2":
                self[chain].ruler.enableOnly(rules)
        self.inline.ruler2.enableOnly(chain_rules["inline2"])

    def add_render_rule(
        self, name: str, function: Callable[..., Any], fmt: str = "html"
    ) -> None:
        """Add a rule for rendering a particular Token type.

        Only applied when ``renderer.__output__ == fmt``
        """
        if self.renderer.__output__ == fmt:
            self.renderer.rules[name] = function.__get__(self.renderer)  # type: ignore

    def use(
        self, plugin: Callable[..., None], *params: Any, **options: Any
    ) -> MarkdownIt:
        """Load specified plugin with given params into current parser instance. (chainable)

        It's just a sugar to call `plugin(md, params)` with curring.

        Example::

            def func(tokens, idx):
                tokens[idx].content = tokens[idx].content.replace('foo', 'bar')
            md = MarkdownIt().use(plugin, 'foo_replace', 'text', func)

        """
        plugin(self, *params, **options)
        return self

    def parse(self, src: str, env: EnvType | None = None) -> list[Token]:
        """Parse the source string to a token stream

        :param src: source string
        :param env: environment sandbox

        Parse input string and return list of block tokens (special token type
        "inline" will contain list of inline tokens).

        `env` is used to pass data between "distributed" rules and return additional
        metadata like reference info, needed for the renderer. It also can be used to
        inject data in specific cases. Usually, you will be ok to pass `{}`,
        and then pass updated object to renderer.
        """
        env = {} if env is None else env
        if not isinstance(env, MutableMapping):
            raise TypeError(f"Input data should be a MutableMapping, not {type(env)}")
        if not isinstance(src, str):
            raise TypeError(f"Input data should be a string, not {type(src)}")
        state = StateCore(src, self, env)
        self.core.process(state)
        return state.tokens

    def render(self, src: str, env: EnvType | None = None) -> Any:
        """Render markdown string into html. It does all magic for you :).

        :param src: source string
        :param env: environment sandbox
        :returns: The output of the loaded renderer

        `env` can be used to inject additional metadata (`{}` by default).
        But you will not need it with high probability. See also comment
        in [[MarkdownIt.parse]].
        """
        env = {} if env is None else env
        return self.renderer.render(self.parse(src, env), self.options, env)

    def parseInline(self, src: str, env: EnvType | None = None) -> list[Token]:
        """The same as [[MarkdownIt.parse]] but skip all block rules.

        :param src: source string
        :param env: environment sandbox

        It returns the
        block tokens list with the single `inline` element, containing parsed inline
        tokens in `children` property. Also updates `env` object.
        """
        env = {} if env is None else env
        if not isinstance(env, MutableMapping):
            raise TypeError(f"Input data should be an MutableMapping, not {type(env)}")
        if not isinstance(src, str):
            raise TypeError(f"Input data should be a string, not {type(src)}")
        state = StateCore(src, self, env)
        state.inlineMode = True
        self.core.process(state)
        return state.tokens

    def renderInline(self, src: str, env: EnvType | None = None) -> Any:
        """Similar to [[MarkdownIt.render]] but for single paragraph content.

        :param src: source string
        :param env: environment sandbox

        Similar to [[MarkdownIt.render]] but for single paragraph content. Result
        will NOT be wrapped into `<p>` tags.
        """
        env = {} if env is None else env
        return self.renderer.render(self.parseInline(src, env), self.options, env)

    # link methods

    def validateLink(self, url: str) -> bool:
        """Validate if the URL link is allowed in output.

        This validator can prohibit more than really needed to prevent XSS.
        It's a tradeoff to keep code simple and to be secure by default.

        Note: the url should be normalized at this point, and existing entities decoded.
        """
        return normalize_url.validateLink(url)

    def normalizeLink(self, url: str) -> str:
        """Normalize destination URLs in links

        ::

            [label]:   destination   'title'
                    ^^^^^^^^^^^
        """
        return normalize_url.normalizeLink(url)

    def normalizeLinkText(self, link: str) -> str:
        """Normalize autolink content

        ::

            <destination>
            ~~~~~~~~~~~
        """
        return normalize_url.normalizeLinkText(link)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\wtsapi32.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Wrapper for wtsapi32.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.advapi32 import *

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- Constants ----------------------------------------------------------------

WTS_CURRENT_SERVER_HANDLE = 0
WTS_CURRENT_SESSION = 1

# --- WTS_PROCESS_INFO structure -----------------------------------------------

# typedef struct _WTS_PROCESS_INFO {
#   DWORD  SessionId;
#   DWORD  ProcessId;
#   LPTSTR pProcessName;
#   PSID   pUserSid;
# } WTS_PROCESS_INFO, *PWTS_PROCESS_INFO;


class WTS_PROCESS_INFOA(Structure):
    _fields_ = [
        ("SessionId", DWORD),
        ("ProcessId", DWORD),
        ("pProcessName", LPSTR),
        ("pUserSid", PSID),
    ]


PWTS_PROCESS_INFOA = POINTER(WTS_PROCESS_INFOA)


class WTS_PROCESS_INFOW(Structure):
    _fields_ = [
        ("SessionId", DWORD),
        ("ProcessId", DWORD),
        ("pProcessName", LPWSTR),
        ("pUserSid", PSID),
    ]


PWTS_PROCESS_INFOW = POINTER(WTS_PROCESS_INFOW)

# --- WTSQuerySessionInformation enums and structures --------------------------

# typedef enum _WTS_INFO_CLASS {
#   WTSInitialProgram          = 0,
#   WTSApplicationName         = 1,
#   WTSWorkingDirectory        = 2,
#   WTSOEMId                   = 3,
#   WTSSessionId               = 4,
#   WTSUserName                = 5,
#   WTSWinStationName          = 6,
#   WTSDomainName              = 7,
#   WTSConnectState            = 8,
#   WTSClientBuildNumber       = 9,
#   WTSClientName              = 10,
#   WTSClientDirectory         = 11,
#   WTSClientProductId         = 12,
#   WTSClientHardwareId        = 13,
#   WTSClientAddress           = 14,
#   WTSClientDisplay           = 15,
#   WTSClientProtocolType      = 16,
#   WTSIdleTime                = 17,
#   WTSLogonTime               = 18,
#   WTSIncomingBytes           = 19,
#   WTSOutgoingBytes           = 20,
#   WTSIncomingFrames          = 21,
#   WTSOutgoingFrames          = 22,
#   WTSClientInfo              = 23,
#   WTSSessionInfo             = 24,
#   WTSSessionInfoEx           = 25,
#   WTSConfigInfo              = 26,
#   WTSValidationInfo          = 27,
#   WTSSessionAddressV4        = 28,
#   WTSIsRemoteSession         = 29
# } WTS_INFO_CLASS;

WTSInitialProgram = 0
WTSApplicationName = 1
WTSWorkingDirectory = 2
WTSOEMId = 3
WTSSessionId = 4
WTSUserName = 5
WTSWinStationName = 6
WTSDomainName = 7
WTSConnectState = 8
WTSClientBuildNumber = 9
WTSClientName = 10
WTSClientDirectory = 11
WTSClientProductId = 12
WTSClientHardwareId = 13
WTSClientAddress = 14
WTSClientDisplay = 15
WTSClientProtocolType = 16
WTSIdleTime = 17
WTSLogonTime = 18
WTSIncomingBytes = 19
WTSOutgoingBytes = 20
WTSIncomingFrames = 21
WTSOutgoingFrames = 22
WTSClientInfo = 23
WTSSessionInfo = 24
WTSSessionInfoEx = 25
WTSConfigInfo = 26
WTSValidationInfo = 27
WTSSessionAddressV4 = 28
WTSIsRemoteSession = 29

WTS_INFO_CLASS = ctypes.c_int

# typedef enum _WTS_CONNECTSTATE_CLASS {
#   WTSActive,
#   WTSConnected,
#   WTSConnectQuery,
#   WTSShadow,
#   WTSDisconnected,
#   WTSIdle,
#   WTSListen,
#   WTSReset,
#   WTSDown,
#   WTSInit
# } WTS_CONNECTSTATE_CLASS;

WTSActive = 0
WTSConnected = 1
WTSConnectQuery = 2
WTSShadow = 3
WTSDisconnected = 4
WTSIdle = 5
WTSListen = 6
WTSReset = 7
WTSDown = 8
WTSInit = 9

WTS_CONNECTSTATE_CLASS = ctypes.c_int


# typedef struct _WTS_CLIENT_DISPLAY {
#   DWORD HorizontalResolution;
#   DWORD VerticalResolution;
#   DWORD ColorDepth;
# } WTS_CLIENT_DISPLAY, *PWTS_CLIENT_DISPLAY;
class WTS_CLIENT_DISPLAY(Structure):
    _fields_ = [
        ("HorizontalResolution", DWORD),
        ("VerticalResolution", DWORD),
        ("ColorDepth", DWORD),
    ]


PWTS_CLIENT_DISPLAY = POINTER(WTS_CLIENT_DISPLAY)

# typedef struct _WTS_CLIENT_ADDRESS {
#   DWORD AddressFamily;
#   BYTE  Address[20];
# } WTS_CLIENT_ADDRESS, *PWTS_CLIENT_ADDRESS;

# XXX TODO

# typedef struct _WTSCLIENT {
#   WCHAR   ClientName[CLIENTNAME_LENGTH + 1];
#   WCHAR   Domain[DOMAIN_LENGTH + 1 ];
#   WCHAR   UserName[USERNAME_LENGTH + 1];
#   WCHAR   WorkDirectory[MAX_PATH + 1];
#   WCHAR   InitialProgram[MAX_PATH + 1];
#   BYTE    EncryptionLevel;
#   ULONG   ClientAddressFamily;
#   USHORT  ClientAddress[CLIENTADDRESS_LENGTH + 1];
#   USHORT  HRes;
#   USHORT  VRes;
#   USHORT  ColorDepth;
#   WCHAR   ClientDirectory[MAX_PATH + 1];
#   ULONG   ClientBuildNumber;
#   ULONG   ClientHardwareId;
#   USHORT  ClientProductId;
#   USHORT  OutBufCountHost;
#   USHORT  OutBufCountClient;
#   USHORT  OutBufLength;
#   WCHAR     DeviceId[MAX_PATH + 1];
# } WTSCLIENT, *PWTSCLIENT;

# XXX TODO

# typedef struct _WTSINFO {
#   WTS_CONNECTSTATE_CLASS State;
#   DWORD                  SessionId;
#   DWORD                  IncomingBytes;
#   DWORD                  OutgoingBytes;
#   DWORD                  IncomingCompressedBytes;
#   DWORD                  OutgoingCompressedBytes;
#   WCHAR                  WinStationName;
#   WCHAR                  Domain;
#   WCHAR                  UserName;
#   LARGE_INTEGER          ConnectTime;
#   LARGE_INTEGER          DisconnectTime;
#   LARGE_INTEGER          LastInputTime;
#   LARGE_INTEGER          LogonTime;
#   LARGE_INTEGER          CurrentTime;
# } WTSINFO, *PWTSINFO;

# XXX TODO

# typedef struct _WTSINFOEX {
#   DWORD           Level;
#   WTSINFOEX_LEVEL Data;
# } WTSINFOEX, *PWTSINFOEX;

# XXX TODO

# --- wtsapi32.dll -------------------------------------------------------------


# void WTSFreeMemory(
#   __in  PVOID pMemory
# );
def WTSFreeMemory(pMemory):
    _WTSFreeMemory = windll.wtsapi32.WTSFreeMemory
    _WTSFreeMemory.argtypes = [PVOID]
    _WTSFreeMemory.restype = None
    _WTSFreeMemory(pMemory)


# BOOL WTSEnumerateProcesses(
#   __in   HANDLE hServer,
#   __in   DWORD Reserved,
#   __in   DWORD Version,
#   __out  PWTS_PROCESS_INFO *ppProcessInfo,
#   __out  DWORD *pCount
# );
def WTSEnumerateProcessesA(hServer=WTS_CURRENT_SERVER_HANDLE):
    _WTSEnumerateProcessesA = windll.wtsapi32.WTSEnumerateProcessesA
    _WTSEnumerateProcessesA.argtypes = [HANDLE, DWORD, DWORD, POINTER(PWTS_PROCESS_INFOA), PDWORD]
    _WTSEnumerateProcessesA.restype = bool
    _WTSEnumerateProcessesA.errcheck = RaiseIfZero

    pProcessInfo = PWTS_PROCESS_INFOA()
    Count = DWORD(0)
    _WTSEnumerateProcessesA(hServer, 0, 1, byref(pProcessInfo), byref(Count))
    return pProcessInfo, Count.value


def WTSEnumerateProcessesW(hServer=WTS_CURRENT_SERVER_HANDLE):
    _WTSEnumerateProcessesW = windll.wtsapi32.WTSEnumerateProcessesW
    _WTSEnumerateProcessesW.argtypes = [HANDLE, DWORD, DWORD, POINTER(PWTS_PROCESS_INFOW), PDWORD]
    _WTSEnumerateProcessesW.restype = bool
    _WTSEnumerateProcessesW.errcheck = RaiseIfZero

    pProcessInfo = PWTS_PROCESS_INFOW()
    Count = DWORD(0)
    _WTSEnumerateProcessesW(hServer, 0, 1, byref(pProcessInfo), byref(Count))
    return pProcessInfo, Count.value


WTSEnumerateProcesses = DefaultStringType(WTSEnumerateProcessesA, WTSEnumerateProcessesW)


# BOOL WTSTerminateProcess(
#   __in  HANDLE hServer,
#   __in  DWORD ProcessId,
#   __in  DWORD ExitCode
# );
def WTSTerminateProcess(hServer, ProcessId, ExitCode):
    _WTSTerminateProcess = windll.wtsapi32.WTSTerminateProcess
    _WTSTerminateProcess.argtypes = [HANDLE, DWORD, DWORD]
    _WTSTerminateProcess.restype = bool
    _WTSTerminateProcess.errcheck = RaiseIfZero
    _WTSTerminateProcess(hServer, ProcessId, ExitCode)


# BOOL WTSQuerySessionInformation(
#   __in   HANDLE hServer,
#   __in   DWORD SessionId,
#   __in   WTS_INFO_CLASS WTSInfoClass,
#   __out  LPTSTR *ppBuffer,
#   __out  DWORD *pBytesReturned
# );

# XXX TODO

# --- kernel32.dll -------------------------------------------------------------

# I've no idea why these functions are in kernel32.dll instead of wtsapi32.dll


# BOOL ProcessIdToSessionId(
#   __in   DWORD dwProcessId,
#   __out  DWORD *pSessionId
# );
def ProcessIdToSessionId(dwProcessId):
    _ProcessIdToSessionId = windll.kernel32.ProcessIdToSessionId
    _ProcessIdToSessionId.argtypes = [DWORD, PDWORD]
    _ProcessIdToSessionId.restype = bool
    _ProcessIdToSessionId.errcheck = RaiseIfZero

    dwSessionId = DWORD(0)
    _ProcessIdToSessionId(dwProcessId, byref(dwSessionId))
    return dwSessionId.value


# DWORD WTSGetActiveConsoleSessionId(void);
def WTSGetActiveConsoleSessionId():
    _WTSGetActiveConsoleSessionId = windll.kernel32.WTSGetActiveConsoleSessionId
    _WTSGetActiveConsoleSessionId.argtypes = []
    _WTSGetActiveConsoleSessionId.restype = DWORD
    _WTSGetActiveConsoleSessionId.errcheck = RaiseIfZero
    return _WTSGetActiveConsoleSessionId()


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_machar.py ===
"""
Machine arithmetic - determine the parameters of the
floating-point arithmetic system

Author: Pearu Peterson, September 2003

"""
__all__ = ['MachAr']

from ._ufunc_config import errstate
from .fromnumeric import any

# Need to speed this up...especially for longdouble

# Deprecated 2021-10-20, NumPy 1.22
class MachAr:
    """
    Diagnosing machine parameters.

    Attributes
    ----------
    ibeta : int
        Radix in which numbers are represented.
    it : int
        Number of base-`ibeta` digits in the floating point mantissa M.
    machep : int
        Exponent of the smallest (most negative) power of `ibeta` that,
        added to 1.0, gives something different from 1.0
    eps : float
        Floating-point number ``beta**machep`` (floating point precision)
    negep : int
        Exponent of the smallest power of `ibeta` that, subtracted
        from 1.0, gives something different from 1.0.
    epsneg : float
        Floating-point number ``beta**negep``.
    iexp : int
        Number of bits in the exponent (including its sign and bias).
    minexp : int
        Smallest (most negative) power of `ibeta` consistent with there
        being no leading zeros in the mantissa.
    xmin : float
        Floating-point number ``beta**minexp`` (the smallest [in
        magnitude] positive floating point number with full precision).
    maxexp : int
        Smallest (positive) power of `ibeta` that causes overflow.
    xmax : float
        ``(1-epsneg) * beta**maxexp`` (the largest [in magnitude]
        usable floating value).
    irnd : int
        In ``range(6)``, information on what kind of rounding is done
        in addition, and on how underflow is handled.
    ngrd : int
        Number of 'guard digits' used when truncating the product
        of two mantissas to fit the representation.
    epsilon : float
        Same as `eps`.
    tiny : float
        An alias for `smallest_normal`, kept for backwards compatibility.
    huge : float
        Same as `xmax`.
    precision : float
        ``- int(-log10(eps))``
    resolution : float
        ``- 10**(-precision)``
    smallest_normal : float
        The smallest positive floating point number with 1 as leading bit in
        the mantissa following IEEE-754. Same as `xmin`.
    smallest_subnormal : float
        The smallest positive floating point number with 0 as leading bit in
        the mantissa following IEEE-754.

    Parameters
    ----------
    float_conv : function, optional
        Function that converts an integer or integer array to a float
        or float array. Default is `float`.
    int_conv : function, optional
        Function that converts a float or float array to an integer or
        integer array. Default is `int`.
    float_to_float : function, optional
        Function that converts a float array to float. Default is `float`.
        Note that this does not seem to do anything useful in the current
        implementation.
    float_to_str : function, optional
        Function that converts a single float to a string. Default is
        ``lambda v:'%24.16e' %v``.
    title : str, optional
        Title that is printed in the string representation of `MachAr`.

    See Also
    --------
    finfo : Machine limits for floating point types.
    iinfo : Machine limits for integer types.

    References
    ----------
    .. [1] Press, Teukolsky, Vetterling and Flannery,
           "Numerical Recipes in C++," 2nd ed,
           Cambridge University Press, 2002, p. 31.

    """

    def __init__(self, float_conv=float, int_conv=int,
                 float_to_float=float,
                 float_to_str=lambda v: f'{v:24.16e}',
                 title='Python floating point number'):
        """

        float_conv - convert integer to float (array)
        int_conv   - convert float (array) to integer
        float_to_float - convert float array to float
        float_to_str - convert array float to str
        title        - description of used floating point numbers

        """
        # We ignore all errors here because we are purposely triggering
        # underflow to detect the properties of the running arch.
        with errstate(under='ignore'):
            self._do_init(float_conv, int_conv, float_to_float, float_to_str, title)

    def _do_init(self, float_conv, int_conv, float_to_float, float_to_str, title):
        max_iterN = 10000
        msg = "Did not converge after %d tries with %s"
        one = float_conv(1)
        two = one + one
        zero = one - one

        # Do we really need to do this?  Aren't they 2 and 2.0?
        # Determine ibeta and beta
        a = one
        for _ in range(max_iterN):
            a = a + a
            temp = a + one
            temp1 = temp - a
            if any(temp1 - one != zero):
                break
        else:
            raise RuntimeError(msg % (_, one.dtype))
        b = one
        for _ in range(max_iterN):
            b = b + b
            temp = a + b
            itemp = int_conv(temp - a)
            if any(itemp != 0):
                break
        else:
            raise RuntimeError(msg % (_, one.dtype))
        ibeta = itemp
        beta = float_conv(ibeta)

        # Determine it and irnd
        it = -1
        b = one
        for _ in range(max_iterN):
            it = it + 1
            b = b * beta
            temp = b + one
            temp1 = temp - b
            if any(temp1 - one != zero):
                break
        else:
            raise RuntimeError(msg % (_, one.dtype))

        betah = beta / two
        a = one
        for _ in range(max_iterN):
            a = a + a
            temp = a + one
            temp1 = temp - a
            if any(temp1 - one != zero):
                break
        else:
            raise RuntimeError(msg % (_, one.dtype))
        temp = a + betah
        irnd = 0
        if any(temp - a != zero):
            irnd = 1
        tempa = a + beta
        temp = tempa + betah
        if irnd == 0 and any(temp - tempa != zero):
            irnd = 2

        # Determine negep and epsneg
        negep = it + 3
        betain = one / beta
        a = one
        for i in range(negep):
            a = a * betain
        b = a
        for _ in range(max_iterN):
            temp = one - a
            if any(temp - one != zero):
                break
            a = a * beta
            negep = negep - 1
            # Prevent infinite loop on PPC with gcc 4.0:
            if negep < 0:
                raise RuntimeError("could not determine machine tolerance "
                                   "for 'negep', locals() -> %s" % (locals()))
        else:
            raise RuntimeError(msg % (_, one.dtype))
        negep = -negep
        epsneg = a

        # Determine machep and eps
        machep = - it - 3
        a = b

        for _ in range(max_iterN):
            temp = one + a
            if any(temp - one != zero):
                break
            a = a * beta
            machep = machep + 1
        else:
            raise RuntimeError(msg % (_, one.dtype))
        eps = a

        # Determine ngrd
        ngrd = 0
        temp = one + eps
        if irnd == 0 and any(temp * one - one != zero):
            ngrd = 1

        # Determine iexp
        i = 0
        k = 1
        z = betain
        t = one + eps
        nxres = 0
        for _ in range(max_iterN):
            y = z
            z = y * y
            a = z * one  # Check here for underflow
            temp = z * t
            if any(a + a == zero) or any(abs(z) >= y):
                break
            temp1 = temp * betain
            if any(temp1 * beta == z):
                break
            i = i + 1
            k = k + k
        else:
            raise RuntimeError(msg % (_, one.dtype))
        if ibeta != 10:
            iexp = i + 1
            mx = k + k
        else:
            iexp = 2
            iz = ibeta
            while k >= iz:
                iz = iz * ibeta
                iexp = iexp + 1
            mx = iz + iz - 1

        # Determine minexp and xmin
        for _ in range(max_iterN):
            xmin = y
            y = y * betain
            a = y * one
            temp = y * t
            if any((a + a) != zero) and any(abs(y) < xmin):
                k = k + 1
                temp1 = temp * betain
                if any(temp1 * beta == y) and any(temp != y):
                    nxres = 3
                    xmin = y
                    break
            else:
                break
        else:
            raise RuntimeError(msg % (_, one.dtype))
        minexp = -k

        # Determine maxexp, xmax
        if mx <= k + k - 3 and ibeta != 10:
            mx = mx + mx
            iexp = iexp + 1
        maxexp = mx + minexp
        irnd = irnd + nxres
        if irnd >= 2:
            maxexp = maxexp - 2
        i = maxexp + minexp
        if ibeta == 2 and not i:
            maxexp = maxexp - 1
        if i > 20:
            maxexp = maxexp - 1
        if any(a != y):
            maxexp = maxexp - 2
        xmax = one - epsneg
        if any(xmax * one != xmax):
            xmax = one - beta * epsneg
        xmax = xmax / (xmin * beta * beta * beta)
        i = maxexp + minexp + 3
        for j in range(i):
            if ibeta == 2:
                xmax = xmax + xmax
            else:
                xmax = xmax * beta

        smallest_subnormal = abs(xmin / beta ** (it))

        self.ibeta = ibeta
        self.it = it
        self.negep = negep
        self.epsneg = float_to_float(epsneg)
        self._str_epsneg = float_to_str(epsneg)
        self.machep = machep
        self.eps = float_to_float(eps)
        self._str_eps = float_to_str(eps)
        self.ngrd = ngrd
        self.iexp = iexp
        self.minexp = minexp
        self.xmin = float_to_float(xmin)
        self._str_xmin = float_to_str(xmin)
        self.maxexp = maxexp
        self.xmax = float_to_float(xmax)
        self._str_xmax = float_to_str(xmax)
        self.irnd = irnd

        self.title = title
        # Commonly used parameters
        self.epsilon = self.eps
        self.tiny = self.xmin
        self.huge = self.xmax
        self.smallest_normal = self.xmin
        self._str_smallest_normal = float_to_str(self.xmin)
        self.smallest_subnormal = float_to_float(smallest_subnormal)
        self._str_smallest_subnormal = float_to_str(smallest_subnormal)

        import math
        self.precision = int(-math.log10(float_to_float(self.eps)))
        ten = two + two + two + two + two
        resolution = ten ** (-self.precision)
        self.resolution = float_to_float(resolution)
        self._str_resolution = float_to_str(resolution)

    def __str__(self):
        fmt = (
           'Machine parameters for %(title)s\n'
           '---------------------------------------------------------------------\n'
           'ibeta=%(ibeta)s it=%(it)s iexp=%(iexp)s ngrd=%(ngrd)s irnd=%(irnd)s\n'
           'machep=%(machep)s     eps=%(_str_eps)s (beta**machep == epsilon)\n'
           'negep =%(negep)s  epsneg=%(_str_epsneg)s (beta**epsneg)\n'
           'minexp=%(minexp)s   xmin=%(_str_xmin)s (beta**minexp == tiny)\n'
           'maxexp=%(maxexp)s    xmax=%(_str_xmax)s ((1-epsneg)*beta**maxexp == huge)\n'
           'smallest_normal=%(smallest_normal)s    '
           'smallest_subnormal=%(smallest_subnormal)s\n'
           '---------------------------------------------------------------------\n'
           )
        return fmt % self.__dict__


if __name__ == '__main__':
    print(MachAr())

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\_collections.py ===
from __future__ import absolute_import

try:
    from collections.abc import Mapping, MutableMapping
except ImportError:
    from collections import Mapping, MutableMapping
try:
    from threading import RLock
except ImportError:  # Platform-specific: No threads available

    class RLock:
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            pass


from collections import OrderedDict

from .exceptions import InvalidHeader
from .packages import six
from .packages.six import iterkeys, itervalues

__all__ = ["RecentlyUsedContainer", "HTTPHeaderDict"]


_Null = object()


class RecentlyUsedContainer(MutableMapping):
    """
    Provides a thread-safe dict-like container which maintains up to
    ``maxsize`` keys while throwing away the least-recently-used keys beyond
    ``maxsize``.

    :param maxsize:
        Maximum number of recent elements to retain.

    :param dispose_func:
        Every time an item is evicted from the container,
        ``dispose_func(value)`` is called.  Callback which will get called
    """

    ContainerCls = OrderedDict

    def __init__(self, maxsize=10, dispose_func=None):
        self._maxsize = maxsize
        self.dispose_func = dispose_func

        self._container = self.ContainerCls()
        self.lock = RLock()

    def __getitem__(self, key):
        # Re-insert the item, moving it to the end of the eviction line.
        with self.lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key, value):
        evicted_value = _Null
        with self.lock:
            # Possibly evict the existing value of 'key'
            evicted_value = self._container.get(key, _Null)
            self._container[key] = value

            # If we didn't evict an existing value, we might have to evict the
            # least recently used item from the beginning of the container.
            if len(self._container) > self._maxsize:
                _key, evicted_value = self._container.popitem(last=False)

        if self.dispose_func and evicted_value is not _Null:
            self.dispose_func(evicted_value)

    def __delitem__(self, key):
        with self.lock:
            value = self._container.pop(key)

        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self):
        with self.lock:
            return len(self._container)

    def __iter__(self):
        raise NotImplementedError(
            "Iteration over this class is unlikely to be threadsafe."
        )

    def clear(self):
        with self.lock:
            # Copy pointers to all values, then wipe the mapping
            values = list(itervalues(self._container))
            self._container.clear()

        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self):
        with self.lock:
            return list(iterkeys(self._container))


class HTTPHeaderDict(MutableMapping):
    """
    :param headers:
        An iterable of field-value pairs. Must not contain multiple field names
        when compared case-insensitively.

    :param kwargs:
        Additional field-value pairs to pass in to ``dict.update``.

    A ``dict`` like container for storing HTTP Headers.

    Field names are stored and compared case-insensitively in compliance with
    RFC 7230. Iteration provides the first case-sensitive key seen for each
    case-insensitive pair.

    Using ``__setitem__`` syntax overwrites fields that compare equal
    case-insensitively in order to maintain ``dict``'s api. For fields that
    compare equal, instead create a new ``HTTPHeaderDict`` and use ``.add``
    in a loop.

    If multiple fields that are equal case-insensitively are passed to the
    constructor or ``.update``, the behavior is undefined and some will be
    lost.

    >>> headers = HTTPHeaderDict()
    >>> headers.add('Set-Cookie', 'foo=bar')
    >>> headers.add('set-cookie', 'baz=quxx')
    >>> headers['content-length'] = '7'
    >>> headers['SET-cookie']
    'foo=bar, baz=quxx'
    >>> headers['Content-Length']
    '7'
    """

    def __init__(self, headers=None, **kwargs):
        super(HTTPHeaderDict, self).__init__()
        self._container = OrderedDict()
        if headers is not None:
            if isinstance(headers, HTTPHeaderDict):
                self._copy_from(headers)
            else:
                self.extend(headers)
        if kwargs:
            self.extend(kwargs)

    def __setitem__(self, key, val):
        self._container[key.lower()] = [key, val]
        return self._container[key.lower()]

    def __getitem__(self, key):
        val = self._container[key.lower()]
        return ", ".join(val[1:])

    def __delitem__(self, key):
        del self._container[key.lower()]

    def __contains__(self, key):
        return key.lower() in self._container

    def __eq__(self, other):
        if not isinstance(other, Mapping) and not hasattr(other, "keys"):
            return False
        if not isinstance(other, type(self)):
            other = type(self)(other)
        return dict((k.lower(), v) for k, v in self.itermerged()) == dict(
            (k.lower(), v) for k, v in other.itermerged()
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    if six.PY2:  # Python 2
        iterkeys = MutableMapping.iterkeys
        itervalues = MutableMapping.itervalues

    __marker = object()

    def __len__(self):
        return len(self._container)

    def __iter__(self):
        # Only provide the originally cased names
        for vals in self._container.values():
            yield vals[0]

    def pop(self, key, default=__marker):
        """D.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.
        """
        # Using the MutableMapping function directly fails due to the private marker.
        # Using ordinary dict.pop would expose the internal structures.
        # So let's reinvent the wheel.
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def discard(self, key):
        try:
            del self[key]
        except KeyError:
            pass

    def add(self, key, val):
        """Adds a (name, value) pair, doesn't overwrite the value if it already
        exists.

        >>> headers = HTTPHeaderDict(foo='bar')
        >>> headers.add('Foo', 'baz')
        >>> headers['foo']
        'bar, baz'
        """
        key_lower = key.lower()
        new_vals = [key, val]
        # Keep the common case aka no item present as fast as possible
        vals = self._container.setdefault(key_lower, new_vals)
        if new_vals is not vals:
            vals.append(val)

    def extend(self, *args, **kwargs):
        """Generic import function for any type of header-like object.
        Adapted version of MutableMapping.update in order to insert items
        with self.add instead of self.__setitem__
        """
        if len(args) > 1:
            raise TypeError(
                "extend() takes at most 1 positional "
                "arguments ({0} given)".format(len(args))
            )
        other = args[0] if len(args) >= 1 else ()

        if isinstance(other, HTTPHeaderDict):
            for key, val in other.iteritems():
                self.add(key, val)
        elif isinstance(other, Mapping):
            for key in other:
                self.add(key, other[key])
        elif hasattr(other, "keys"):
            for key in other.keys():
                self.add(key, other[key])
        else:
            for key, value in other:
                self.add(key, value)

        for key, value in kwargs.items():
            self.add(key, value)

    def getlist(self, key, default=__marker):
        """Returns a list of all the values for the named field. Returns an
        empty list if the key doesn't exist."""
        try:
            vals = self._container[key.lower()]
        except KeyError:
            if default is self.__marker:
                return []
            return default
        else:
            return vals[1:]

    def _prepare_for_method_change(self):
        """
        Remove content-specific header fields before changing the request
        method to GET or HEAD according to RFC 9110, Section 15.4.
        """
        content_specific_headers = [
            "Content-Encoding",
            "Content-Language",
            "Content-Location",
            "Content-Type",
            "Content-Length",
            "Digest",
            "Last-Modified",
        ]
        for header in content_specific_headers:
            self.discard(header)
        return self

    # Backwards compatibility for httplib
    getheaders = getlist
    getallmatchingheaders = getlist
    iget = getlist

    # Backwards compatibility for http.cookiejar
    get_all = getlist

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict(self.itermerged()))

    def _copy_from(self, other):
        for key in other:
            val = other.getlist(key)
            if isinstance(val, list):
                # Don't need to convert tuples
                val = list(val)
            self._container[key.lower()] = [key] + val

    def copy(self):
        clone = type(self)()
        clone._copy_from(self)
        return clone

    def iteritems(self):
        """Iterate over all header lines, including duplicate ones."""
        for key in self:
            vals = self._container[key.lower()]
            for val in vals[1:]:
                yield vals[0], val

    def itermerged(self):
        """Iterate over all headers, merging duplicate ones together."""
        for key in self:
            val = self._container[key.lower()]
            yield val[0], ", ".join(val[1:])

    def items(self):
        return list(self.iteritems())

    @classmethod
    def from_httplib(cls, message):  # Python 2
        """Read headers from a Python 2 httplib message object."""
        # python2.7 does not expose a proper API for exporting multiheaders
        # efficiently. This function re-reads raw lines from the message
        # object and extracts the multiheaders properly.
        obs_fold_continued_leaders = (" ", "\t")
        headers = []

        for line in message.headers:
            if line.startswith(obs_fold_continued_leaders):
                if not headers:
                    # We received a header line that starts with OWS as described
                    # in RFC-7230 S3.2.4. This indicates a multiline header, but
                    # there exists no previous header to which we can attach it.
                    raise InvalidHeader(
                        "Header continuation with no previous header: %s" % line
                    )
                else:
                    key, value = headers[-1]
                    headers[-1] = (key, value + " " + line.strip())
                    continue

            key, value = line.split(":", 1)
            headers.append((key, value.strip()))

        return cls(headers)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_util.py ===
from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine, Generator
import pytest

import trio
from trio.testing import Matcher, RaisesGroup

from .. import _core
from .._core._tests.tutil import (
    create_asyncio_future_in_new_loop,
    ignore_coroutine_never_awaited_warnings,
)
from .._util import (
    ConflictDetector,
    MultipleExceptionError,
    NoPublicConstructor,
    coroutine_or_error,
    final,
    fixup_module_metadata,
    generic_function,
    is_main_thread,
    raise_single_exception_from_group,
)
from ..testing import wait_all_tasks_blocked

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

T = TypeVar("T")


async def test_ConflictDetector() -> None:
    ul1 = ConflictDetector("ul1")
    ul2 = ConflictDetector("ul2")

    with ul1:
        with ul2:
            print("ok")

    with pytest.raises(_core.BusyResourceError, match="ul1"):
        with ul1:
            with ul1:
                pass  # pragma: no cover

    async def wait_with_ul1() -> None:
        with ul1:
            await wait_all_tasks_blocked()

    with RaisesGroup(Matcher(_core.BusyResourceError, "ul1")):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(wait_with_ul1)
            nursery.start_soon(wait_with_ul1)


def test_module_metadata_is_fixed_up() -> None:
    import trio
    import trio.testing

    assert trio.Cancelled.__module__ == "trio"
    assert trio.open_nursery.__module__ == "trio"
    assert trio.abc.Stream.__module__ == "trio.abc"
    assert trio.lowlevel.wait_task_rescheduled.__module__ == "trio.lowlevel"
    assert trio.testing.trio_test.__module__ == "trio.testing"

    # Also check methods
    assert trio.lowlevel.ParkingLot.__init__.__module__ == "trio.lowlevel"
    assert trio.abc.Stream.send_all.__module__ == "trio.abc"

    # And names
    assert trio.Cancelled.__name__ == "Cancelled"
    assert trio.Cancelled.__qualname__ == "Cancelled"
    assert trio.abc.SendStream.send_all.__name__ == "send_all"
    assert trio.abc.SendStream.send_all.__qualname__ == "SendStream.send_all"
    assert trio.to_thread.__name__ == "trio.to_thread"
    assert trio.to_thread.run_sync.__name__ == "run_sync"
    assert trio.to_thread.run_sync.__qualname__ == "run_sync"


async def test_is_main_thread() -> None:
    assert is_main_thread()

    def not_main_thread() -> None:
        assert not is_main_thread()

    await trio.to_thread.run_sync(not_main_thread)


# @coroutine is deprecated since python 3.8, which is fine with us.
@pytest.mark.filterwarnings("ignore:.*@coroutine.*:DeprecationWarning")
def test_coroutine_or_error() -> None:
    class Deferred:
        "Just kidding"

    with ignore_coroutine_never_awaited_warnings():

        async def f() -> None:  # pragma: no cover
            pass

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(f())  # type: ignore[arg-type, unused-coroutine]
        assert "expecting an async function" in str(excinfo.value)

        import asyncio

        if sys.version_info < (3, 11):

            @asyncio.coroutine
            def generator_based_coro() -> (
                Generator[Coroutine[None, None, None], None, None]
            ):  # pragma: no cover
                yield from asyncio.sleep(1)

            with pytest.raises(TypeError) as excinfo:
                coroutine_or_error(generator_based_coro())  # type: ignore[arg-type, unused-coroutine]
            assert "asyncio" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(create_asyncio_future_in_new_loop())  # type: ignore[arg-type, unused-coroutine]
        assert "asyncio" in str(excinfo.value)

        # does not raise arg-type error
        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(create_asyncio_future_in_new_loop)  # type: ignore[unused-coroutine]
        assert "asyncio" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(Deferred())  # type: ignore[arg-type, unused-coroutine]
        assert "twisted" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(lambda: Deferred())  # type: ignore[arg-type, unused-coroutine, return-value]
        assert "twisted" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(len, [[1, 2, 3]])  # type: ignore[arg-type, unused-coroutine]

        assert "appears to be synchronous" in str(excinfo.value)

        async def async_gen(
            _: object,
        ) -> AsyncGenerator[None, None]:  # pragma: no cover
            yield

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(async_gen, [0])  # type: ignore[arg-type,unused-coroutine]
        msg = "expected an async function but got an async generator"
        assert msg in str(excinfo.value)

        # Make sure no references are kept around to keep anything alive
        del excinfo


def test_generic_function() -> None:
    @generic_function  # Decorated function contains "Any".
    def test_func(arg: T) -> T:  # type: ignore[misc]
        """Look, a docstring!"""
        return arg

    assert test_func is test_func[int] is test_func[int, str]
    assert test_func(42) == test_func[int](42) == 42
    assert test_func.__doc__ == "Look, a docstring!"
    assert test_func.__qualname__ == "test_generic_function.<locals>.test_func"  # type: ignore[attr-defined]
    assert test_func.__name__ == "test_func"  # type: ignore[attr-defined]
    assert test_func.__module__ == __name__


def test_final_decorator() -> None:
    """Test that subclassing a @final-annotated class is not allowed.

    This checks both runtime results, and verifies that type checkers detect
    the error statically through the type-ignore comment.
    """

    @final
    class FinalClass:
        pass

    with pytest.raises(TypeError):

        class SubClass(FinalClass):  # type: ignore[misc]
            pass


def test_no_public_constructor_metaclass() -> None:
    """The NoPublicConstructor metaclass prevents calling the constructor directly."""

    class SpecialClass(metaclass=NoPublicConstructor):
        def __init__(self, a: int, b: float) -> None:
            """Check arguments can be passed to __init__."""
            assert a == 8
            assert b == 3.15

    with pytest.raises(TypeError):
        SpecialClass(8, 3.15)

    # Private constructor should not raise, and passes args to __init__.
    assert isinstance(SpecialClass._create(8, b=3.15), SpecialClass)


def test_fixup_module_metadata() -> None:
    # Ignores modules not in the trio.X tree.
    non_trio_module = types.ModuleType("not_trio")
    non_trio_module.some_func = lambda: None  # type: ignore[attr-defined]
    non_trio_module.some_func.__name__ = "some_func"
    non_trio_module.some_func.__qualname__ = "some_func"

    fixup_module_metadata(non_trio_module.__name__, vars(non_trio_module))

    assert non_trio_module.some_func.__name__ == "some_func"
    assert non_trio_module.some_func.__qualname__ == "some_func"

    # Bulild up a fake module to test. Just use lambdas since all we care about is the names.
    mod = types.ModuleType("trio._somemodule_impl")
    mod.some_func = lambda: None  # type: ignore[attr-defined]
    mod.some_func.__name__ = "_something_else"
    mod.some_func.__qualname__ = "_something_else"

    # No __module__ means it's unchanged.
    mod.not_funclike = types.SimpleNamespace()  # type: ignore[attr-defined]
    mod.not_funclike.__name__ = "not_funclike"

    # Check __qualname__ being absent works.
    mod.only_has_name = types.SimpleNamespace()  # type: ignore[attr-defined]
    mod.only_has_name.__module__ = "trio._somemodule_impl"
    mod.only_has_name.__name__ = "only_name"

    # Underscored names are unchanged.
    mod._private = lambda: None  # type: ignore[attr-defined]
    mod._private.__module__ = "trio._somemodule_impl"
    mod._private.__name__ = mod._private.__qualname__ = "_private"

    # We recurse into classes.
    mod.SomeClass = type(  # type: ignore[attr-defined]
        "SomeClass",
        (),
        {
            "__init__": lambda self: None,
            "method": lambda self: None,
        },
    )
    # Reference loop is fine.
    mod.SomeClass.recursion = mod.SomeClass  # type: ignore[attr-defined]

    fixup_module_metadata("trio.somemodule", vars(mod))
    assert mod.some_func.__name__ == "some_func"
    assert mod.some_func.__module__ == "trio.somemodule"
    assert mod.some_func.__qualname__ == "some_func"

    assert mod.not_funclike.__name__ == "not_funclike"
    assert mod._private.__name__ == "_private"
    assert mod._private.__module__ == "trio._somemodule_impl"
    assert mod._private.__qualname__ == "_private"

    assert mod.only_has_name.__name__ == "only_has_name"
    assert mod.only_has_name.__module__ == "trio.somemodule"
    assert not hasattr(mod.only_has_name, "__qualname__")

    assert mod.SomeClass.method.__name__ == "method"  # type: ignore[attr-defined]
    assert mod.SomeClass.method.__module__ == "trio.somemodule"  # type: ignore[attr-defined]
    assert mod.SomeClass.method.__qualname__ == "SomeClass.method"  # type: ignore[attr-defined]
    # Make coverage happy.
    non_trio_module.some_func()
    mod.some_func()
    mod._private()
    mod.SomeClass().method()


async def test_raise_single_exception_from_group() -> None:
    excinfo: pytest.ExceptionInfo[BaseException]

    exc = ValueError("foo")
    cause = SyntaxError("cause")
    context = TypeError("context")
    exc.__cause__ = cause
    exc.__context__ = context
    cancelled = trio.Cancelled._create()

    with pytest.raises(ValueError, match="foo") as excinfo:
        raise_single_exception_from_group(ExceptionGroup("", [exc]))
    assert excinfo.value.__cause__ == cause
    assert excinfo.value.__context__ == context

    # only unwraps one layer of exceptiongroup
    inner_eg = ExceptionGroup("inner eg", [exc])
    inner_cause = SyntaxError("inner eg cause")
    inner_context = TypeError("inner eg context")
    inner_eg.__cause__ = inner_cause
    inner_eg.__context__ = inner_context
    with RaisesGroup(Matcher(ValueError, match="^foo$"), match="^inner eg$") as eginfo:
        raise_single_exception_from_group(ExceptionGroup("", [inner_eg]))
    assert eginfo.value.__cause__ == inner_cause
    assert eginfo.value.__context__ == inner_context

    with pytest.raises(ValueError, match="foo") as excinfo:
        raise_single_exception_from_group(
            BaseExceptionGroup("", [cancelled, cancelled, exc])
        )
    assert excinfo.value.__cause__ == cause
    assert excinfo.value.__context__ == context

    # multiple non-cancelled
    eg = ExceptionGroup("", [ValueError("foo"), ValueError("bar")])
    with pytest.raises(
        MultipleExceptionError,
        match=r"^Attempted to unwrap exceptiongroup with multiple non-cancelled exceptions. This is often caused by a bug in the caller.$",
    ) as excinfo:
        raise_single_exception_from_group(eg)
    assert excinfo.value.__cause__ is eg
    assert excinfo.value.__context__ is None

    # keyboardinterrupt overrides everything
    eg_ki = BaseExceptionGroup(
        "",
        [
            ValueError("foo"),
            ValueError("bar"),
            KeyboardInterrupt("this exc doesn't get reraised"),
        ],
    )
    with pytest.raises(KeyboardInterrupt, match=r"^$") as excinfo:
        raise_single_exception_from_group(eg_ki)
    assert excinfo.value.__cause__ is eg_ki
    assert excinfo.value.__context__ is None

    # and same for SystemExit
    systemexit_ki = BaseExceptionGroup(
        "",
        [
            ValueError("foo"),
            ValueError("bar"),
            SystemExit("this exc doesn't get reraised"),
        ],
    )
    with pytest.raises(SystemExit, match=r"^$") as excinfo:
        raise_single_exception_from_group(systemexit_ki)
    assert excinfo.value.__cause__ is systemexit_ki
    assert excinfo.value.__context__ is None

    # if we only got cancelled, first one is reraised
    with pytest.raises(trio.Cancelled, match=r"^Cancelled$") as excinfo:
        raise_single_exception_from_group(
            BaseExceptionGroup("", [cancelled, trio.Cancelled._create()])
        )
    assert excinfo.value is cancelled
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None

# === NexusCore/myenv\Lib\site-packages\pip\_internal\wheel_builder.py ===
"""Orchestrator for building wheels from InstallRequirements.
"""

import logging
import os.path
import re
import shutil
from typing import Iterable, List, Optional, Tuple

from pip._vendor.packaging.utils import canonicalize_name, canonicalize_version
from pip._vendor.packaging.version import InvalidVersion, Version

from pip._internal.cache import WheelCache
from pip._internal.exceptions import InvalidWheelFilename, UnsupportedWheel
from pip._internal.metadata import FilesystemWheel, get_wheel_distribution
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.build.wheel import build_wheel_pep517
from pip._internal.operations.build.wheel_editable import build_wheel_editable
from pip._internal.operations.build.wheel_legacy import build_wheel_legacy
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import ensure_dir, hash_file
from pip._internal.utils.setuptools_build import make_setuptools_clean_args
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import vcs

logger = logging.getLogger(__name__)

_egg_info_re = re.compile(r"([a-z0-9_.]+)-([a-z0-9_.!+-]+)", re.IGNORECASE)

BuildResult = Tuple[List[InstallRequirement], List[InstallRequirement]]


def _contains_egg_info(s: str) -> bool:
    """Determine whether the string looks like an egg_info.

    :param s: The string to parse. E.g. foo-2.1
    """
    return bool(_egg_info_re.search(s))


def _should_build(
    req: InstallRequirement,
    need_wheel: bool,
) -> bool:
    """Return whether an InstallRequirement should be built into a wheel."""
    if req.constraint:
        # never build requirements that are merely constraints
        return False
    if req.is_wheel:
        if need_wheel:
            logger.info(
                "Skipping %s, due to already being wheel.",
                req.name,
            )
        return False

    if need_wheel:
        # i.e. pip wheel, not pip install
        return True

    # From this point, this concerns the pip install command only
    # (need_wheel=False).

    if not req.source_dir:
        return False

    if req.editable:
        # we only build PEP 660 editable requirements
        return req.supports_pyproject_editable

    return True


def should_build_for_wheel_command(
    req: InstallRequirement,
) -> bool:
    return _should_build(req, need_wheel=True)


def should_build_for_install_command(
    req: InstallRequirement,
) -> bool:
    return _should_build(req, need_wheel=False)


def _should_cache(
    req: InstallRequirement,
) -> Optional[bool]:
    """
    Return whether a built InstallRequirement can be stored in the persistent
    wheel cache, assuming the wheel cache is available, and _should_build()
    has determined a wheel needs to be built.
    """
    if req.editable or not req.source_dir:
        # never cache editable requirements
        return False

    if req.link and req.link.is_vcs:
        # VCS checkout. Do not cache
        # unless it points to an immutable commit hash.
        assert not req.editable
        assert req.source_dir
        vcs_backend = vcs.get_backend_for_scheme(req.link.scheme)
        assert vcs_backend
        if vcs_backend.is_immutable_rev_checkout(req.link.url, req.source_dir):
            return True
        return False

    assert req.link
    base, ext = req.link.splitext()
    if _contains_egg_info(base):
        return True

    # Otherwise, do not cache.
    return False


def _get_cache_dir(
    req: InstallRequirement,
    wheel_cache: WheelCache,
) -> str:
    """Return the persistent or temporary cache directory where the built
    wheel need to be stored.
    """
    cache_available = bool(wheel_cache.cache_dir)
    assert req.link
    if cache_available and _should_cache(req):
        cache_dir = wheel_cache.get_path_for_link(req.link)
    else:
        cache_dir = wheel_cache.get_ephem_path_for_link(req.link)
    return cache_dir


def _verify_one(req: InstallRequirement, wheel_path: str) -> None:
    canonical_name = canonicalize_name(req.name or "")
    w = Wheel(os.path.basename(wheel_path))
    if canonicalize_name(w.name) != canonical_name:
        raise InvalidWheelFilename(
            f"Wheel has unexpected file name: expected {canonical_name!r}, "
            f"got {w.name!r}",
        )
    dist = get_wheel_distribution(FilesystemWheel(wheel_path), canonical_name)
    dist_verstr = str(dist.version)
    if canonicalize_version(dist_verstr) != canonicalize_version(w.version):
        raise InvalidWheelFilename(
            f"Wheel has unexpected file name: expected {dist_verstr!r}, "
            f"got {w.version!r}",
        )
    metadata_version_value = dist.metadata_version
    if metadata_version_value is None:
        raise UnsupportedWheel("Missing Metadata-Version")
    try:
        metadata_version = Version(metadata_version_value)
    except InvalidVersion:
        msg = f"Invalid Metadata-Version: {metadata_version_value}"
        raise UnsupportedWheel(msg)
    if metadata_version >= Version("1.2") and not isinstance(dist.version, Version):
        raise UnsupportedWheel(
            f"Metadata 1.2 mandates PEP 440 version, but {dist_verstr!r} is not"
        )


def _build_one(
    req: InstallRequirement,
    output_dir: str,
    verify: bool,
    build_options: List[str],
    global_options: List[str],
    editable: bool,
) -> Optional[str]:
    """Build one wheel.

    :return: The filename of the built wheel, or None if the build failed.
    """
    artifact = "editable" if editable else "wheel"
    try:
        ensure_dir(output_dir)
    except OSError as e:
        logger.warning(
            "Building %s for %s failed: %s",
            artifact,
            req.name,
            e,
        )
        return None

    # Install build deps into temporary directory (PEP 518)
    with req.build_env:
        wheel_path = _build_one_inside_env(
            req, output_dir, build_options, global_options, editable
        )
    if wheel_path and verify:
        try:
            _verify_one(req, wheel_path)
        except (InvalidWheelFilename, UnsupportedWheel) as e:
            logger.warning("Built %s for %s is invalid: %s", artifact, req.name, e)
            return None
    return wheel_path


def _build_one_inside_env(
    req: InstallRequirement,
    output_dir: str,
    build_options: List[str],
    global_options: List[str],
    editable: bool,
) -> Optional[str]:
    with TempDirectory(kind="wheel") as temp_dir:
        assert req.name
        if req.use_pep517:
            assert req.metadata_directory
            assert req.pep517_backend
            if global_options:
                logger.warning(
                    "Ignoring --global-option when building %s using PEP 517", req.name
                )
            if build_options:
                logger.warning(
                    "Ignoring --build-option when building %s using PEP 517", req.name
                )
            if editable:
                wheel_path = build_wheel_editable(
                    name=req.name,
                    backend=req.pep517_backend,
                    metadata_directory=req.metadata_directory,
                    tempd=temp_dir.path,
                )
            else:
                wheel_path = build_wheel_pep517(
                    name=req.name,
                    backend=req.pep517_backend,
                    metadata_directory=req.metadata_directory,
                    tempd=temp_dir.path,
                )
        else:
            wheel_path = build_wheel_legacy(
                name=req.name,
                setup_py_path=req.setup_py_path,
                source_dir=req.unpacked_source_directory,
                global_options=global_options,
                build_options=build_options,
                tempd=temp_dir.path,
            )

        if wheel_path is not None:
            wheel_name = os.path.basename(wheel_path)
            dest_path = os.path.join(output_dir, wheel_name)
            try:
                wheel_hash, length = hash_file(wheel_path)
                shutil.move(wheel_path, dest_path)
                logger.info(
                    "Created wheel for %s: filename=%s size=%d sha256=%s",
                    req.name,
                    wheel_name,
                    length,
                    wheel_hash.hexdigest(),
                )
                logger.info("Stored in directory: %s", output_dir)
                return dest_path
            except Exception as e:
                logger.warning(
                    "Building wheel for %s failed: %s",
                    req.name,
                    e,
                )
        # Ignore return, we can't do anything else useful.
        if not req.use_pep517:
            _clean_one_legacy(req, global_options)
        return None


def _clean_one_legacy(req: InstallRequirement, global_options: List[str]) -> bool:
    clean_args = make_setuptools_clean_args(
        req.setup_py_path,
        global_options=global_options,
    )

    logger.info("Running setup.py clean for %s", req.name)
    try:
        call_subprocess(
            clean_args, command_desc="python setup.py clean", cwd=req.source_dir
        )
        return True
    except Exception:
        logger.error("Failed cleaning build dir for %s", req.name)
        return False


def build(
    requirements: Iterable[InstallRequirement],
    wheel_cache: WheelCache,
    verify: bool,
    build_options: List[str],
    global_options: List[str],
) -> BuildResult:
    """Build wheels.

    :return: The list of InstallRequirement that succeeded to build and
        the list of InstallRequirement that failed to build.
    """
    if not requirements:
        return [], []

    # Build the wheels.
    logger.info(
        "Building wheels for collected packages: %s",
        ", ".join(req.name for req in requirements),  # type: ignore
    )

    with indent_log():
        build_successes, build_failures = [], []
        for req in requirements:
            assert req.name
            cache_dir = _get_cache_dir(req, wheel_cache)
            wheel_file = _build_one(
                req,
                cache_dir,
                verify,
                build_options,
                global_options,
                req.editable and req.permit_editable_wheels,
            )
            if wheel_file:
                # Record the download origin in the cache
                if req.download_info is not None:
                    # download_info is guaranteed to be set because when we build an
                    # InstallRequirement it has been through the preparer before, but
                    # let's be cautious.
                    wheel_cache.record_download_origin(cache_dir, req.download_info)
                # Update the link for this.
                req.link = Link(path_to_url(wheel_file))
                req.local_file_path = req.link.file_path
                assert req.link.is_wheel
                build_successes.append(req)
            else:
                build_failures.append(req)

    # notify success/failure
    if build_successes:
        logger.info(
            "Successfully built %s",
            " ".join([req.name for req in build_successes]),  # type: ignore
        )
    if build_failures:
        logger.info(
            "Failed to build %s",
            " ".join([req.name for req in build_failures]),  # type: ignore
        )
    # Return a list of requirements that failed to build
    return build_successes, build_failures