
# === NexusCore/tools\exports\export_20250803_114325\combined_76.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\ui_sso.py ===
"""
Has all /sso/* routes

/sso/key/generate - handles user signing in with SSO and redirects to /sso/callback
/sso/callback - returns JWT Redirect Response that redirects to LiteLLM UI

/sso/debug/login - handles user signing in with SSO and redirects to /sso/debug/callback
/sso/debug/callback - returns the OpenID object returned by the SSO provider
"""

import asyncio
import os
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache
from litellm.constants import MAX_SPENDLOG_ROWS_TO_QUERY
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import (
    CommonProxyErrors,
    LiteLLM_UserTable,
    LitellmUserRoles,
    Member,
    NewTeamRequest,
    NewUserRequest,
    NewUserResponse,
    ProxyErrorTypes,
    ProxyException,
    SSOUserDefinedValues,
    TeamMemberAddRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.auth_checks import ExperimentalUIJWTToken, get_user_object
from litellm.proxy.auth.auth_utils import _has_user_setup_sso
from litellm.proxy.auth.handle_jwt import JWTHandler
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_utils.admin_ui_utils import (
    admin_ui_disabled,
    show_missing_vars_in_env,
)
from litellm.proxy.common_utils.html_forms.jwt_display_template import (
    jwt_display_template,
)
from litellm.proxy.common_utils.html_forms.ui_login import html_form
from litellm.proxy.management_endpoints.internal_user_endpoints import new_user
from litellm.proxy.management_endpoints.sso_helper_utils import (
    check_is_admin_only_access,
    has_admin_ui_access,
)
from litellm.proxy.management_endpoints.team_endpoints import new_team, team_member_add
from litellm.proxy.management_endpoints.types import CustomOpenID
from litellm.proxy.utils import PrismaClient, ProxyLogging, get_server_root_path
from litellm.secret_managers.main import get_secret_bool, str_to_bool
from litellm.types.proxy.management_endpoints.ui_sso import *

if TYPE_CHECKING:
    from fastapi_sso.sso.base import OpenID
else:
    from typing import Any as OpenID

router = APIRouter()


@router.get("/sso/key/generate", tags=["experimental"], include_in_schema=False)
async def google_login(request: Request):  # noqa: PLR0915
    """
    Create Proxy API Keys using Google Workspace SSO. Requires setting PROXY_BASE_URL in .env
    PROXY_BASE_URL should be the your deployed proxy endpoint, e.g. PROXY_BASE_URL="https://litellm-production-7002.up.railway.app/"
    Example:
    """
    from litellm.proxy.proxy_server import premium_user

    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID", None)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", None)
    generic_client_id = os.getenv("GENERIC_CLIENT_ID", None)

    ####### Check if UI is disabled #######
    _disable_ui_flag = os.getenv("DISABLE_ADMIN_UI")
    if _disable_ui_flag is not None:
        is_disabled = str_to_bool(value=_disable_ui_flag)
        if is_disabled:
            return admin_ui_disabled()

    ####### Check if user is a Enterprise / Premium User #######
    if (
        microsoft_client_id is not None
        or google_client_id is not None
        or generic_client_id is not None
    ):
        if premium_user is not True:
            raise ProxyException(
                message="You must be a LiteLLM Enterprise user to use SSO. If you have a license please set `LITELLM_LICENSE` in your env. If you want to obtain a license meet with us here: https://calendly.com/d/4mp-gd3-k5k/litellm-1-1-onboarding-chat You are seeing this error message because You set one of `MICROSOFT_CLIENT_ID`, `GOOGLE_CLIENT_ID`, or `GENERIC_CLIENT_ID` in your env. Please unset this",
                type=ProxyErrorTypes.auth_error,
                param="premium_user",
                code=status.HTTP_403_FORBIDDEN,
            )

    ####### Detect DB + MASTER KEY in .env #######
    missing_env_vars = show_missing_vars_in_env()
    if missing_env_vars is not None:
        return missing_env_vars
    ui_username = os.getenv("UI_USERNAME")

    # get url from request
    redirect_url = SSOAuthenticationHandler.get_redirect_url_for_sso(
        request=request,
        sso_callback_route="sso/callback",
    )

    # Check if we should use SSO handler
    if (
        SSOAuthenticationHandler.should_use_sso_handler(
            microsoft_client_id=microsoft_client_id,
            google_client_id=google_client_id,
            generic_client_id=generic_client_id,
        )
        is True
    ):
        verbose_proxy_logger.info(f"Redirecting to SSO login for {redirect_url}")
        return await SSOAuthenticationHandler.get_sso_login_redirect(
            redirect_url=redirect_url,
            microsoft_client_id=microsoft_client_id,
            google_client_id=google_client_id,
            generic_client_id=generic_client_id,
        )
    elif ui_username is not None:
        # No Google, Microsoft SSO
        # Use UI Credentials set in .env
        from fastapi.responses import HTMLResponse

        return HTMLResponse(content=html_form, status_code=200)
    else:
        from fastapi.responses import HTMLResponse

        return HTMLResponse(content=html_form, status_code=200)


def generic_response_convertor(response, jwt_handler: JWTHandler):
    generic_user_id_attribute_name = os.getenv(
        "GENERIC_USER_ID_ATTRIBUTE", "preferred_username"
    )
    generic_user_display_name_attribute_name = os.getenv(
        "GENERIC_USER_DISPLAY_NAME_ATTRIBUTE", "sub"
    )
    generic_user_email_attribute_name = os.getenv(
        "GENERIC_USER_EMAIL_ATTRIBUTE", "email"
    )

    generic_user_first_name_attribute_name = os.getenv(
        "GENERIC_USER_FIRST_NAME_ATTRIBUTE", "first_name"
    )
    generic_user_last_name_attribute_name = os.getenv(
        "GENERIC_USER_LAST_NAME_ATTRIBUTE", "last_name"
    )

    generic_provider_attribute_name = os.getenv(
        "GENERIC_USER_PROVIDER_ATTRIBUTE", "provider"
    )

    verbose_proxy_logger.debug(
        f" generic_user_id_attribute_name: {generic_user_id_attribute_name}\n generic_user_email_attribute_name: {generic_user_email_attribute_name}"
    )

    return CustomOpenID(
        id=response.get(generic_user_id_attribute_name),
        display_name=response.get(generic_user_display_name_attribute_name),
        email=response.get(generic_user_email_attribute_name),
        first_name=response.get(generic_user_first_name_attribute_name),
        last_name=response.get(generic_user_last_name_attribute_name),
        provider=response.get(generic_provider_attribute_name),
        team_ids=jwt_handler.get_team_ids_from_jwt(cast(dict, response)),
    )


async def get_generic_sso_response(
    request: Request,
    jwt_handler: JWTHandler,
    generic_client_id: str,
    redirect_url: str,
) -> Union[OpenID, dict]:
    # make generic sso provider
    from fastapi_sso.sso.base import DiscoveryDocument
    from fastapi_sso.sso.generic import create_provider

    generic_client_secret = os.getenv("GENERIC_CLIENT_SECRET", None)
    generic_scope = os.getenv("GENERIC_SCOPE", "openid email profile").split(" ")
    generic_authorization_endpoint = os.getenv("GENERIC_AUTHORIZATION_ENDPOINT", None)
    generic_token_endpoint = os.getenv("GENERIC_TOKEN_ENDPOINT", None)
    generic_userinfo_endpoint = os.getenv("GENERIC_USERINFO_ENDPOINT", None)
    generic_include_client_id = (
        os.getenv("GENERIC_INCLUDE_CLIENT_ID", "false").lower() == "true"
    )
    if generic_client_secret is None:
        raise ProxyException(
            message="GENERIC_CLIENT_SECRET not set. Set it in .env file",
            type=ProxyErrorTypes.auth_error,
            param="GENERIC_CLIENT_SECRET",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if generic_authorization_endpoint is None:
        raise ProxyException(
            message="GENERIC_AUTHORIZATION_ENDPOINT not set. Set it in .env file",
            type=ProxyErrorTypes.auth_error,
            param="GENERIC_AUTHORIZATION_ENDPOINT",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if generic_token_endpoint is None:
        raise ProxyException(
            message="GENERIC_TOKEN_ENDPOINT not set. Set it in .env file",
            type=ProxyErrorTypes.auth_error,
            param="GENERIC_TOKEN_ENDPOINT",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if generic_userinfo_endpoint is None:
        raise ProxyException(
            message="GENERIC_USERINFO_ENDPOINT not set. Set it in .env file",
            type=ProxyErrorTypes.auth_error,
            param="GENERIC_USERINFO_ENDPOINT",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    verbose_proxy_logger.debug(
        f"authorization_endpoint: {generic_authorization_endpoint}\ntoken_endpoint: {generic_token_endpoint}\nuserinfo_endpoint: {generic_userinfo_endpoint}"
    )
    verbose_proxy_logger.debug(
        f"GENERIC_REDIRECT_URI: {redirect_url}\nGENERIC_CLIENT_ID: {generic_client_id}\n"
    )

    discovery = DiscoveryDocument(
        authorization_endpoint=generic_authorization_endpoint,
        token_endpoint=generic_token_endpoint,
        userinfo_endpoint=generic_userinfo_endpoint,
    )

    def response_convertor(response, client):
        return generic_response_convertor(
            response=response,
            jwt_handler=jwt_handler,
        )

    SSOProvider = create_provider(
        name="oidc",
        discovery_document=discovery,
        response_convertor=response_convertor,
    )
    generic_sso = SSOProvider(
        client_id=generic_client_id,
        client_secret=generic_client_secret,
        redirect_uri=redirect_url,
        allow_insecure_http=True,
        scope=generic_scope,
    )
    verbose_proxy_logger.debug("calling generic_sso.verify_and_process")
    additional_generic_sso_headers = os.getenv(
        "GENERIC_SSO_HEADERS", None
    )  # Comma-separated list of headers to add to the request - e.g. Authorization=Bearer <token>, Content-Type=application/json, etc.
    additional_generic_sso_headers_dict = {}
    if additional_generic_sso_headers is not None:
        additional_generic_sso_headers_split = additional_generic_sso_headers.split(",")
        for header in additional_generic_sso_headers_split:
            header = header.strip()
            if header:
                key, value = header.split("=")
                additional_generic_sso_headers_dict[key] = value

    try:
        result = await generic_sso.verify_and_process(
            request,
            params={"include_client_id": generic_include_client_id},
            headers=additional_generic_sso_headers_dict,
        )
    except Exception as e:
        verbose_proxy_logger.exception(
            f"Error verifying and processing generic SSO: {e}. Passed in headers: {additional_generic_sso_headers_dict}"
        )
        raise e
    verbose_proxy_logger.debug("generic result: %s", result)
    return result or {}


async def create_team_member_add_task(team_id, user_info):
    """Create a task for adding a member to a team."""
    try:
        member = Member(user_id=user_info.user_id, role="user")
        team_member_add_request = TeamMemberAddRequest(
            member=member,
            team_id=team_id,
        )
        return await team_member_add(
            data=team_member_add_request,
            user_api_key_dict=UserAPIKeyAuth(user_role=LitellmUserRoles.PROXY_ADMIN),
        )
    except Exception as e:
        verbose_proxy_logger.debug(
            f"[Non-Blocking] Error trying to add sso user to db: {e}"
        )


async def add_missing_team_member(
    user_info: Union[NewUserResponse, LiteLLM_UserTable], sso_teams: List[str]
):
    """
    - Get missing teams (diff b/w user_info.team_ids and sso_teams)
    - Add missing user to missing teams
    """
    if user_info.teams is None:
        return
    missing_teams = set(sso_teams) - set(user_info.teams)
    missing_teams_list = list(missing_teams)
    tasks = []
    tasks = [
        create_team_member_add_task(team_id, user_info)
        for team_id in missing_teams_list
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        verbose_proxy_logger.debug(
            f"[Non-Blocking] Error trying to add sso user to db: {e}"
        )


def get_disabled_non_admin_personal_key_creation():
    key_generation_settings = litellm.key_generation_settings
    if key_generation_settings is None:
        return False
    personal_key_generation = (
        key_generation_settings.get("personal_key_generation") or {}
    )
    allowed_user_roles = personal_key_generation.get("allowed_user_roles") or []
    return bool("proxy_admin" in allowed_user_roles)


async def get_existing_user_info_from_db(
    user_id: Optional[str],
    user_email: Optional[str],
    prisma_client: PrismaClient,
    user_api_key_cache: DualCache,
    proxy_logging_obj: ProxyLogging,
) -> Optional[LiteLLM_UserTable]:
    try:
        user_info = await get_user_object(
            user_id=user_id,
            user_email=user_email,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            user_id_upsert=False,
            parent_otel_span=None,
            proxy_logging_obj=proxy_logging_obj,
            sso_user_id=user_id,
        )
    except Exception as e:
        verbose_proxy_logger.debug(f"Error getting user object: {e}")
        user_info = None

    return user_info


async def get_user_info_from_db(
    result: Union[CustomOpenID, OpenID, dict],
    prisma_client: PrismaClient,
    user_api_key_cache: DualCache,
    proxy_logging_obj: ProxyLogging,
    user_email: Optional[str],
    user_defined_values: Optional[SSOUserDefinedValues],
    alternate_user_id: Optional[str] = None,
) -> Optional[Union[LiteLLM_UserTable, NewUserResponse]]:
    try:
        potential_user_ids = []
        if alternate_user_id is not None:
            potential_user_ids.append(alternate_user_id)
        if not isinstance(result, dict):
            _id = getattr(result, "id", None)
            if _id is not None and isinstance(_id, str):
                potential_user_ids.append(_id)
        else:
            _id = result.get("id", None)
            if _id is not None and isinstance(_id, str):
                potential_user_ids.append(_id)

        user_email = (
            getattr(result, "email", None)
            if not isinstance(result, dict)
            else result.get("email", None)
        )

        user_info: Optional[Union[LiteLLM_UserTable, NewUserResponse]] = None

        for user_id in potential_user_ids:
            user_info = await get_existing_user_info_from_db(
                user_id=user_id,
                user_email=user_email,
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                proxy_logging_obj=proxy_logging_obj,
            )
            if user_info is not None:
                break

        verbose_proxy_logger.debug(
            f"user_info: {user_info}; litellm.default_internal_user_params: {litellm.default_internal_user_params}"
        )

        # Upsert SSO User to LiteLLM DB

        if user_info is None:
            user_info = await SSOAuthenticationHandler.upsert_sso_user(
                result=result,
                user_info=user_info,
                user_email=user_email,
                user_defined_values=user_defined_values,
                prisma_client=prisma_client,
            )

        await SSOAuthenticationHandler.add_user_to_teams_from_sso_response(
            result=result,
            user_info=user_info,
        )

        return user_info
    except Exception as e:
        verbose_proxy_logger.exception(
            f"[Non-Blocking] Error trying to add sso user to db: {e}"
        )

    return None


def apply_user_info_values_to_sso_user_defined_values(
    user_info: Optional[Union[LiteLLM_UserTable, NewUserResponse]],
    user_defined_values: Optional[SSOUserDefinedValues],
) -> Optional[SSOUserDefinedValues]:
    if user_defined_values is None:
        return None
    if user_info is not None and user_info.user_id is not None:
        user_defined_values["user_id"] = user_info.user_id

    if user_info is None or user_info.user_role is None:
        user_defined_values["user_role"] = LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
    else:
        user_defined_values["user_role"] = user_info.user_role

    return user_defined_values


async def check_and_update_if_proxy_admin_id(
    user_role: str, user_id: str, prisma_client: Optional[PrismaClient]
):
    """
    - Check if user role in DB is admin
    - If not, update user role in DB to admin role
    """
    proxy_admin_id = os.getenv("PROXY_ADMIN_ID")
    if proxy_admin_id is not None and proxy_admin_id == user_id:
        if user_role and user_role == LitellmUserRoles.PROXY_ADMIN.value:
            return user_role

        if prisma_client:
            await prisma_client.db.litellm_usertable.update(
                where={"user_id": user_id},
                data={"user_role": LitellmUserRoles.PROXY_ADMIN.value},
            )

        user_role = LitellmUserRoles.PROXY_ADMIN.value

    return user_role


@router.get("/sso/callback", tags=["experimental"], include_in_schema=False)
async def auth_callback(request: Request):  # noqa: PLR0915
    """Verify login"""
    verbose_proxy_logger.info("Starting SSO callback")
    from litellm.proxy.management_endpoints.key_management_endpoints import (
        generate_key_helper_fn,
    )
    from litellm.proxy.proxy_server import (
        general_settings,
        jwt_handler,
        master_key,
        premium_user,
        prisma_client,
        proxy_logging_obj,
        ui_access_mode,
        user_api_key_cache,
        user_custom_sso,
    )
    from litellm.proxy.utils import get_custom_url
    from litellm.types.proxy.ui_sso import ReturnedUITokenObject

    if prisma_client is None:
        raise HTTPException(
            status_code=500, detail=CommonProxyErrors.db_not_connected_error.value
        )

    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID", None)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", None)
    generic_client_id = os.getenv("GENERIC_CLIENT_ID", None)
    # get url from request
    if master_key is None:
        raise ProxyException(
            message="Master Key not set for Proxy. Please set Master Key to use Admin UI. Set `LITELLM_MASTER_KEY` in .env or set general_settings:master_key in config.yaml.  https://docs.litellm.ai/docs/proxy/virtual_keys. If set, use `--detailed_debug` to debug issue.",
            type=ProxyErrorTypes.auth_error,
            param="master_key",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    redirect_url = SSOAuthenticationHandler.get_redirect_url_for_sso(
        request=request, sso_callback_route="sso/callback"
    )

    verbose_proxy_logger.info(f"Redirecting to {redirect_url}")
    result = None
    if google_client_id is not None:
        result = await GoogleSSOHandler.get_google_callback_response(
            request=request,
            google_client_id=google_client_id,
            redirect_url=redirect_url,
        )
    elif microsoft_client_id is not None:
        result = await MicrosoftSSOHandler.get_microsoft_callback_response(
            request=request,
            microsoft_client_id=microsoft_client_id,
            redirect_url=redirect_url,
        )
    elif generic_client_id is not None:
        result = await get_generic_sso_response(
            request=request,
            jwt_handler=jwt_handler,
            generic_client_id=generic_client_id,
            redirect_url=redirect_url,
        )

    if result is None:
        raise HTTPException(
            status_code=401,
            detail="Result not returned by SSO provider.",
        )

    # User is Authe'd in - generate key for the UI to access Proxy
    verbose_proxy_logger.info(f"SSO callback result: {result}")
    user_email: Optional[str] = getattr(result, "email", None)
    user_id: Optional[str] = getattr(result, "id", None) if result is not None else None

    if user_email is not None and os.getenv("ALLOWED_EMAIL_DOMAINS") is not None:
        email_domain = user_email.split("@")[1]
        allowed_domains = os.getenv("ALLOWED_EMAIL_DOMAINS").split(",")  # type: ignore
        if email_domain not in allowed_domains:
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "The email domain={}, is not an allowed email domain={}. Contact your admin to change this.".format(
                        email_domain, allowed_domains
                    )
                },
            )

    # generic client id
    if generic_client_id is not None and result is not None:
        generic_user_role_attribute_name = os.getenv(
            "GENERIC_USER_ROLE_ATTRIBUTE", "role"
        )
        user_id = getattr(result, "id", None)
        user_email = getattr(result, "email", None)
        user_role = getattr(result, generic_user_role_attribute_name, None)  # type: ignore

    if user_id is None and result is not None:
        _first_name = getattr(result, "first_name", "") or ""
        _last_name = getattr(result, "last_name", "") or ""
        user_id = _first_name + _last_name

    if user_email is not None and (user_id is None or len(user_id) == 0):
        user_id = user_email

    user_info = None
    user_id_models: List = []
    max_internal_user_budget = litellm.max_internal_user_budget
    internal_user_budget_duration = litellm.internal_user_budget_duration

    # User might not be already created on first generation of key
    # But if it is, we want their models preferences
    default_ui_key_values: Dict[str, Any] = {
        "duration": "24hr",
        "key_max_budget": litellm.max_ui_session_budget,
        "aliases": {},
        "config": {},
        "spend": 0,
        "team_id": "litellm-dashboard",
    }
    user_defined_values: Optional[SSOUserDefinedValues] = None

    if user_custom_sso is not None:
        if asyncio.iscoroutinefunction(user_custom_sso):
            user_defined_values = await user_custom_sso(result)  # type: ignore
        else:
            raise ValueError("user_custom_sso must be a coroutine function")
    elif user_id is not None:
        user_defined_values = SSOUserDefinedValues(
            models=user_id_models,
            user_id=user_id,
            user_email=user_email,
            max_budget=max_internal_user_budget,
            user_role=None,
            budget_duration=internal_user_budget_duration,
        )

    user_info = await get_user_info_from_db(
        result=result,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
        user_email=user_email,
        user_defined_values=user_defined_values,
        alternate_user_id=user_id,
    )

    user_defined_values = apply_user_info_values_to_sso_user_defined_values(
        user_info=user_info, user_defined_values=user_defined_values
    )

    if user_defined_values is None:
        raise Exception(
            "Unable to map user identity to known values. 'user_defined_values' is None. File an issue - https://github.com/BerriAI/litellm/issues"
        )

    verbose_proxy_logger.info(
        f"user_defined_values for creating ui key: {user_defined_values}"
    )

    default_ui_key_values.update(user_defined_values)
    default_ui_key_values["request_type"] = "key"
    response = await generate_key_helper_fn(
        **default_ui_key_values,  # type: ignore
        table_name="key",
    )

    key = response["token"]  # type: ignore
    user_id = response["user_id"]  # type: ignore

    litellm_dashboard_ui = get_custom_url(
        request_base_url=str(request.base_url), route="ui/"
    )
    user_role = (
        user_defined_values["user_role"]
        or LitellmUserRoles.INTERNAL_USER_VIEW_ONLY.value
    )
    if user_id and isinstance(user_id, str):
        user_role = await check_and_update_if_proxy_admin_id(
            user_role=user_role, user_id=user_id, prisma_client=prisma_client
        )

    verbose_proxy_logger.debug(
        f"user_role: {user_role}; ui_access_mode: {ui_access_mode}"
    )
    ## CHECK IF ROLE ALLOWED TO USE PROXY ##
    is_admin_only_access = check_is_admin_only_access(ui_access_mode)
    if is_admin_only_access:
        has_access = has_admin_ui_access(user_role)
        if not has_access:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": f"User not allowed to access proxy. User role={user_role}, proxy mode={ui_access_mode}"
                },
            )

    disabled_non_admin_personal_key_creation = (
        get_disabled_non_admin_personal_key_creation()
    )

    import jwt

    if get_secret_bool("EXPERIMENTAL_UI_LOGIN"):
        _user_info: Optional[LiteLLM_UserTable] = None
        if (
            user_defined_values is not None
            and user_defined_values["user_id"] is not None
        ):
            _user_info = LiteLLM_UserTable(
                user_id=user_defined_values["user_id"],
                user_role=user_defined_values["user_role"] or user_role,
                models=[],
                max_budget=litellm.max_ui_session_budget,
            )
        if _user_info is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "User Information is required for experimental UI login"
                },
            )

        key = ExperimentalUIJWTToken.get_experimental_ui_login_jwt_auth_token(
            _user_info
        )

    returned_ui_token_object = ReturnedUITokenObject(
        user_id=cast(str, user_id),
        key=key,
        user_email=user_email,
        user_role=user_role,
        login_method="sso",
        premium_user=premium_user,
        auth_header_name=general_settings.get(
            "litellm_key_header_name", "Authorization"
        ),
        disabled_non_admin_personal_key_creation=disabled_non_admin_personal_key_creation,
        server_root_path=get_server_root_path(),
    )

    jwt_token = jwt.encode(  # type: ignore
        cast(dict, returned_ui_token_object),
        master_key,
        algorithm="HS256",
    )
    verbose_proxy_logger.info(f"user_id: {user_id}; jwt_token: {jwt_token}")
    if user_id is not None and isinstance(user_id, str):
        litellm_dashboard_ui += "?login=success"
    verbose_proxy_logger.info(f"Redirecting to {litellm_dashboard_ui}")
    redirect_response = RedirectResponse(url=litellm_dashboard_ui, status_code=303)
    redirect_response.set_cookie(key="token", value=jwt_token)
    return redirect_response


async def insert_sso_user(
    result_openid: Optional[Union[OpenID, dict]],
    user_defined_values: Optional[SSOUserDefinedValues] = None,
) -> NewUserResponse:
    """
    Helper function to create a New User in LiteLLM DB after a successful SSO login

    Args:
        result_openid (OpenID): User information in OpenID format if the login was successful.
        user_defined_values (Optional[SSOUserDefinedValues], optional): LiteLLM SSOValues / fields that were read

    Returns:
        Tuple[str, str]: User ID and User Role
    """
    verbose_proxy_logger.debug(
        f"Inserting SSO user into DB. User values: {user_defined_values}"
    )
    if result_openid is None:
        raise ValueError("result_openid is None")
    if isinstance(result_openid, dict):
        result_openid = OpenID(**result_openid)

    if user_defined_values is None:
        raise ValueError("user_defined_values is None")

    if litellm.default_internal_user_params:
        user_defined_values.update(litellm.default_internal_user_params)  # type: ignore

    # Set budget for internal users
    if user_defined_values.get("user_role") == LitellmUserRoles.INTERNAL_USER.value:
        if user_defined_values.get("max_budget") is None:
            user_defined_values["max_budget"] = litellm.max_internal_user_budget
        if user_defined_values.get("budget_duration") is None:
            user_defined_values["budget_duration"] = (
                litellm.internal_user_budget_duration
            )

    if user_defined_values["user_role"] is None:
        user_defined_values["user_role"] = LitellmUserRoles.INTERNAL_USER_VIEW_ONLY

    new_user_request = NewUserRequest(
        user_id=user_defined_values["user_id"],
        user_email=user_defined_values["user_email"],
        user_role=user_defined_values["user_role"],  # type: ignore
        max_budget=user_defined_values["max_budget"],
        budget_duration=user_defined_values["budget_duration"],
        sso_user_id=user_defined_values["user_id"],
        auto_create_key=False,
    )

    if result_openid:
        new_user_request.metadata = {"auth_provider": result_openid.provider}

    response = await new_user(
        data=new_user_request,
        user_api_key_dict=UserAPIKeyAuth(user_role=LitellmUserRoles.PROXY_ADMIN),
    )

    return response


@router.get(
    "/sso/get/ui_settings",
    tags=["experimental"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def get_ui_settings(request: Request):
    from litellm.proxy.proxy_server import general_settings, proxy_state

    _proxy_base_url = os.getenv("PROXY_BASE_URL", None)
    _logout_url = os.getenv("PROXY_LOGOUT_URL", None)
    _is_sso_enabled = _has_user_setup_sso()
    disable_expensive_db_queries = (
        proxy_state.get_proxy_state_variable("spend_logs_row_count")
        > MAX_SPENDLOG_ROWS_TO_QUERY
    )
    default_team_disabled = general_settings.get("default_team_disabled", False)
    if "PROXY_DEFAULT_TEAM_DISABLED" in os.environ:
        if os.environ["PROXY_DEFAULT_TEAM_DISABLED"].lower() == "true":
            default_team_disabled = True

    return {
        "PROXY_BASE_URL": _proxy_base_url,
        "PROXY_LOGOUT_URL": _logout_url,
        "DEFAULT_TEAM_DISABLED": default_team_disabled,
        "SSO_ENABLED": _is_sso_enabled,
        "NUM_SPEND_LOGS_ROWS": proxy_state.get_proxy_state_variable(
            "spend_logs_row_count"
        ),
        "DISABLE_EXPENSIVE_DB_QUERIES": disable_expensive_db_queries,
    }


class SSOAuthenticationHandler:
    """
    Handler for SSO Authentication across all SSO providers
    """

    @staticmethod
    async def get_sso_login_redirect(
        redirect_url: str,
        google_client_id: Optional[str] = None,
        microsoft_client_id: Optional[str] = None,
        generic_client_id: Optional[str] = None,
    ) -> Optional[RedirectResponse]:
        """
        Step 1. Call Get Login Redirect for the SSO provider. Send the redirect response to `redirect_url`

        Args:
            redirect_url (str): The URL to redirect the user to after login
            google_client_id (Optional[str], optional): The Google Client ID. Defaults to None.
            microsoft_client_id (Optional[str], optional): The Microsoft Client ID. Defaults to None.
            generic_client_id (Optional[str], optional): The Generic Client ID. Defaults to None.

        Returns:
            RedirectResponse: The redirect response from the SSO provider
        """
        # Google SSO Auth
        if google_client_id is not None:
            from fastapi_sso.sso.google import GoogleSSO

            google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", None)
            if google_client_secret is None:
                raise ProxyException(
                    message="GOOGLE_CLIENT_SECRET not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="GOOGLE_CLIENT_SECRET",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            google_sso = GoogleSSO(
                client_id=google_client_id,
                client_secret=google_client_secret,
                redirect_uri=redirect_url,
            )
            verbose_proxy_logger.info(
                f"In /google-login/key/generate, \nGOOGLE_REDIRECT_URI: {redirect_url}\nGOOGLE_CLIENT_ID: {google_client_id}"
            )
            with google_sso:
                return await google_sso.get_login_redirect()
        # Microsoft SSO Auth
        elif microsoft_client_id is not None:
            from fastapi_sso.sso.microsoft import MicrosoftSSO

            microsoft_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", None)
            microsoft_tenant = os.getenv("MICROSOFT_TENANT", None)
            if microsoft_client_secret is None:
                raise ProxyException(
                    message="MICROSOFT_CLIENT_SECRET not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="MICROSOFT_CLIENT_SECRET",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            microsoft_sso = MicrosoftSSO(
                client_id=microsoft_client_id,
                client_secret=microsoft_client_secret,
                tenant=microsoft_tenant,
                redirect_uri=redirect_url,
                allow_insecure_http=True,
            )
            with microsoft_sso:
                return await microsoft_sso.get_login_redirect()
        elif generic_client_id is not None:
            from fastapi_sso.sso.base import DiscoveryDocument
            from fastapi_sso.sso.generic import create_provider

            generic_client_secret = os.getenv("GENERIC_CLIENT_SECRET", None)
            generic_scope = os.getenv("GENERIC_SCOPE", "openid email profile").split(
                " "
            )
            generic_authorization_endpoint = os.getenv(
                "GENERIC_AUTHORIZATION_ENDPOINT", None
            )
            generic_token_endpoint = os.getenv("GENERIC_TOKEN_ENDPOINT", None)
            generic_userinfo_endpoint = os.getenv("GENERIC_USERINFO_ENDPOINT", None)
            if generic_client_secret is None:
                raise ProxyException(
                    message="GENERIC_CLIENT_SECRET not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="GENERIC_CLIENT_SECRET",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if generic_authorization_endpoint is None:
                raise ProxyException(
                    message="GENERIC_AUTHORIZATION_ENDPOINT not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="GENERIC_AUTHORIZATION_ENDPOINT",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if generic_token_endpoint is None:
                raise ProxyException(
                    message="GENERIC_TOKEN_ENDPOINT not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="GENERIC_TOKEN_ENDPOINT",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if generic_userinfo_endpoint is None:
                raise ProxyException(
                    message="GENERIC_USERINFO_ENDPOINT not set. Set it in .env file",
                    type=ProxyErrorTypes.auth_error,
                    param="GENERIC_USERINFO_ENDPOINT",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            verbose_proxy_logger.debug(
                f"authorization_endpoint: {generic_authorization_endpoint}\ntoken_endpoint: {generic_token_endpoint}\nuserinfo_endpoint: {generic_userinfo_endpoint}"
            )
            verbose_proxy_logger.debug(
                f"GENERIC_REDIRECT_URI: {redirect_url}\nGENERIC_CLIENT_ID: {generic_client_id}\n"
            )
            discovery = DiscoveryDocument(
                authorization_endpoint=generic_authorization_endpoint,
                token_endpoint=generic_token_endpoint,
                userinfo_endpoint=generic_userinfo_endpoint,
            )
            SSOProvider = create_provider(name="oidc", discovery_document=discovery)
            generic_sso = SSOProvider(
                client_id=generic_client_id,
                client_secret=generic_client_secret,
                redirect_uri=redirect_url,
                allow_insecure_http=True,
                scope=generic_scope,
            )
            with generic_sso:
                # TODO: state should be a random string and added to the user session with cookie
                # or a cryptographicly signed state that we can verify stateless
                # For simplification we are using a static state, this is not perfect but some
                # SSO providers do not allow stateless verification
                redirect_params = {}
                state = os.getenv("GENERIC_CLIENT_STATE", None)

                if state:
                    redirect_params["state"] = state
                elif "okta" in generic_authorization_endpoint:
                    redirect_params["state"] = (
                        uuid.uuid4().hex
                    )  # set state param for okta - required
                return await generic_sso.get_login_redirect(**redirect_params)  # type: ignore
        raise ValueError(
            "Unknown SSO provider. Please setup SSO with client IDs https://docs.litellm.ai/docs/proxy/admin_ui_sso"
        )

    @staticmethod
    def should_use_sso_handler(
        google_client_id: Optional[str] = None,
        microsoft_client_id: Optional[str] = None,
        generic_client_id: Optional[str] = None,
    ) -> bool:
        if (
            google_client_id is not None
            or microsoft_client_id is not None
            or generic_client_id is not None
        ):
            return True
        return False

    @staticmethod
    def get_redirect_url_for_sso(
        request: Request,
        sso_callback_route: str,
    ) -> str:
        """
        Get the redirect URL for SSO
        """
        from litellm.proxy.utils import get_custom_url

        redirect_url = get_custom_url(request_base_url=str(request.base_url))
        if redirect_url.endswith("/"):
            redirect_url += sso_callback_route
        else:
            redirect_url += "/" + sso_callback_route
        return redirect_url

    @staticmethod
    async def upsert_sso_user(
        result: Optional[Union[CustomOpenID, OpenID, dict]],
        user_info: Optional[Union[NewUserResponse, LiteLLM_UserTable]],
        user_email: Optional[str],
        user_defined_values: Optional[SSOUserDefinedValues],
        prisma_client: PrismaClient,
    ):
        """
        Connects the SSO Users to the User Table in LiteLLM DB

        - If user on LiteLLM DB, update the user_email with the SSO user_email
        - If user not on LiteLLM DB, insert the user into LiteLLM DB
        """
        try:
            if user_info is not None:
                user_id = user_info.user_id
                await prisma_client.db.litellm_usertable.update_many(
                    where={"user_id": user_id}, data={"user_email": user_email}
                )
            else:
                verbose_proxy_logger.info(
                    "user not in DB, inserting user into LiteLLM DB"
                )
                # user not in DB, insert User into LiteLLM DB
                user_info = await insert_sso_user(
                    result_openid=result,
                    user_defined_values=user_defined_values,
                )
            return user_info
        except Exception as e:
            verbose_proxy_logger.error(f"Error upserting SSO user into LiteLLM DB: {e}")
            return user_info

    @staticmethod
    async def add_user_to_teams_from_sso_response(
        result: Optional[Union[CustomOpenID, OpenID, dict]],
        user_info: Optional[Union[NewUserResponse, LiteLLM_UserTable]],
    ):
        """
        Adds the user as a team member to the teams specified in the SSO responses `team_ids` field


        The `team_ids` field is populated by litellm after processing the SSO response
        """
        if user_info is None:
            verbose_proxy_logger.debug(
                "User not found in LiteLLM DB, skipping team member addition"
            )
            return
        sso_teams = getattr(result, "team_ids", [])
        await add_missing_team_member(user_info=user_info, sso_teams=sso_teams)

    @staticmethod
    async def create_litellm_team_from_sso_group(
        litellm_team_id: str,
        litellm_team_name: Optional[str] = None,
    ):
        """
        Creates a Litellm Team from a SSO Group ID

        Your SSO provider might have groups that should be created on LiteLLM

        Use this helper to create a Litellm Team from a SSO Group ID

        Args:
            litellm_team_id (str): The ID of the Litellm Team
            litellm_team_name (Optional[str]): The name of the Litellm Team
        """
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise ProxyException(
                message="Prisma client not found. Set it in the proxy_server.py file",
                type=ProxyErrorTypes.auth_error,
                param="prisma_client",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            team_obj = await prisma_client.db.litellm_teamtable.find_first(
                where={"team_id": litellm_team_id}
            )
            verbose_proxy_logger.debug(f"Team object: {team_obj}")

            # only create a new team if it doesn't exist
            if team_obj:
                verbose_proxy_logger.debug(
                    f"Team already exists: {litellm_team_id} - {litellm_team_name}"
                )
                return

            team_request: NewTeamRequest = NewTeamRequest(
                team_id=litellm_team_id,
                team_alias=litellm_team_name,
            )
            if litellm.default_team_params:
                team_request = SSOAuthenticationHandler._cast_and_deepcopy_litellm_default_team_params(
                    default_team_params=litellm.default_team_params,
                    litellm_team_id=litellm_team_id,
                    litellm_team_name=litellm_team_name,
                    team_request=team_request,
                )

            await new_team(
                data=team_request,
                # params used for Audit Logging
                http_request=Request(scope={"type": "http", "method": "POST"}),
                user_api_key_dict=UserAPIKeyAuth(
                    token="",
                    key_alias=f"litellm.{MicrosoftSSOHandler.__name__}",
                ),
            )
        except Exception as e:
            verbose_proxy_logger.exception(f"Error creating Litellm Team: {e}")

    @staticmethod
    def _cast_and_deepcopy_litellm_default_team_params(
        default_team_params: Union[DefaultTeamSSOParams, Dict],
        team_request: NewTeamRequest,
        litellm_team_id: str,
        litellm_team_name: Optional[str] = None,
    ) -> NewTeamRequest:
        """
        Casts and deepcopies the litellm.default_team_params to a NewTeamRequest object

        - Ensures we create a new DefaultTeamSSOParams object
        - Handle the case where litellm.default_team_params is a dict or a DefaultTeamSSOParams object
        - Adds the litellm_team_id and litellm_team_name to the DefaultTeamSSOParams object
        """
        if isinstance(default_team_params, dict):
            _team_request = deepcopy(default_team_params)
            _team_request["team_id"] = litellm_team_id
            _team_request["team_alias"] = litellm_team_name
            team_request = NewTeamRequest(**_team_request)
        elif isinstance(litellm.default_team_params, DefaultTeamSSOParams):
            _default_team_params = deepcopy(litellm.default_team_params)
            _new_team_request = team_request.model_dump()
            _new_team_request.update(_default_team_params)
            team_request = NewTeamRequest(**_new_team_request)
        return team_request


class MicrosoftSSOHandler:
    """
    Handles Microsoft SSO callback response and returns a CustomOpenID object
    """

    graph_api_base_url = "https://graph.microsoft.com/v1.0"
    graph_api_user_groups_endpoint = f"{graph_api_base_url}/me/memberOf"

    """
    Constants
    """
    MAX_GRAPH_API_PAGES = 200

    # used for debugging to show the user groups litellm found from Graph API
    GRAPH_API_RESPONSE_KEY = "graph_api_user_groups"

    @staticmethod
    async def get_microsoft_callback_response(
        request: Request,
        microsoft_client_id: str,
        redirect_url: str,
        return_raw_sso_response: bool = False,
    ) -> Union[CustomOpenID, OpenID, dict]:
        """
        Get the Microsoft SSO callback response

        Args:
            return_raw_sso_response: If True, return the raw SSO response
        """
        from fastapi_sso.sso.microsoft import MicrosoftSSO

        microsoft_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", None)
        microsoft_tenant = os.getenv("MICROSOFT_TENANT", None)
        if microsoft_client_secret is None:
            raise ProxyException(
                message="MICROSOFT_CLIENT_SECRET not set. Set it in .env file",
                type=ProxyErrorTypes.auth_error,
                param="MICROSOFT_CLIENT_SECRET",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if microsoft_tenant is None:
            raise ProxyException(
                message="MICROSOFT_TENANT not set. Set it in .env file",
                type=ProxyErrorTypes.auth_error,
                param="MICROSOFT_TENANT",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        microsoft_sso = MicrosoftSSO(
            client_id=microsoft_client_id,
            client_secret=microsoft_client_secret,
            tenant=microsoft_tenant,
            redirect_uri=redirect_url,
            allow_insecure_http=True,
        )
        original_msft_result = (
            await microsoft_sso.verify_and_process(
                request=request,
                convert_response=False,  # type: ignore
            )
            or {}
        )

        user_team_ids = await MicrosoftSSOHandler.get_user_groups_from_graph_api(
            access_token=microsoft_sso.access_token
        )

        # if user is trying to get the raw sso response for debugging, return the raw sso response
        if return_raw_sso_response:
            original_msft_result[MicrosoftSSOHandler.GRAPH_API_RESPONSE_KEY] = (
                user_team_ids
            )
            return original_msft_result or {}

        result = MicrosoftSSOHandler.openid_from_response(
            response=original_msft_result,
            team_ids=user_team_ids,
        )
        return result

    @staticmethod
    def openid_from_response(
        response: Optional[dict], team_ids: List[str]
    ) -> CustomOpenID:
        response = response or {}
        verbose_proxy_logger.debug(f"Microsoft SSO Callback Response: {response}")
        openid_response = CustomOpenID(
            email=response.get("userPrincipalName") or response.get("mail"),
            display_name=response.get("displayName"),
            provider="microsoft",
            id=response.get("id"),
            first_name=response.get("givenName"),
            last_name=response.get("surname"),
            team_ids=team_ids,
        )
        verbose_proxy_logger.debug(f"Microsoft SSO OpenID Response: {openid_response}")
        return openid_response

    @staticmethod
    async def get_user_groups_from_graph_api(
        access_token: Optional[str] = None,
    ) -> List[str]:
        """
        Returns a list of `team_ids` the user belongs to from the Microsoft Graph API

        Args:
            access_token (Optional[str]): Microsoft Graph API access token

        Returns:
            List[str]: List of group IDs the user belongs to
        """
        try:
            async_client = get_async_httpx_client(
                llm_provider=httpxSpecialProvider.SSO_HANDLER
            )

            # Handle MSFT Enterprise Application Groups
            service_principal_id = os.getenv("MICROSOFT_SERVICE_PRINCIPAL_ID", None)
            service_principal_group_ids: Optional[List[str]] = []
            service_principal_teams: Optional[List[MicrosoftServicePrincipalTeam]] = []
            if service_principal_id:
                (
                    service_principal_group_ids,
                    service_principal_teams,
                ) = await MicrosoftSSOHandler.get_group_ids_from_service_principal(
                    service_principal_id=service_principal_id,
                    async_client=async_client,
                    access_token=access_token,
                )
                verbose_proxy_logger.debug(
                    f"Service principal group IDs: {service_principal_group_ids}"
                )
                if len(service_principal_group_ids) > 0:
                    await MicrosoftSSOHandler.create_litellm_teams_from_service_principal_team_ids(
                        service_principal_teams=service_principal_teams,
                    )

            # Fetch user membership from Microsoft Graph API
            all_group_ids = []
            next_link: Optional[str] = (
                MicrosoftSSOHandler.graph_api_user_groups_endpoint
            )
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            page_count = 0

            while (
                next_link is not None
                and page_count < MicrosoftSSOHandler.MAX_GRAPH_API_PAGES
            ):
                group_ids, next_link = await MicrosoftSSOHandler.fetch_and_parse_groups(
                    url=next_link, headers=auth_headers, async_client=async_client
                )
                all_group_ids.extend(group_ids)
                page_count += 1

            if (
                next_link is not None
                and page_count >= MicrosoftSSOHandler.MAX_GRAPH_API_PAGES
            ):
                verbose_proxy_logger.warning(
                    f"Reached maximum page limit of {MicrosoftSSOHandler.MAX_GRAPH_API_PAGES}. Some groups may not be included."
                )

            # If service_principal_group_ids is not empty, only return group_ids that are in both all_group_ids and service_principal_group_ids
            if service_principal_group_ids and len(service_principal_group_ids) > 0:
                all_group_ids = [
                    group_id
                    for group_id in all_group_ids
                    if group_id in service_principal_group_ids
                ]

            return all_group_ids

        except Exception as e:
            verbose_proxy_logger.error(
                f"Error getting user groups from Microsoft Graph API: {e}"
            )
            return []

    @staticmethod
    async def fetch_and_parse_groups(
        url: str, headers: dict, async_client: AsyncHTTPHandler
    ) -> Tuple[List[str], Optional[str]]:
        """Helper function to fetch and parse group data from a URL"""
        response = await async_client.get(url, headers=headers)
        response_json = response.json()
        response_typed = await MicrosoftSSOHandler._cast_graph_api_response_dict(
            response=response_json
        )
        group_ids = MicrosoftSSOHandler._get_group_ids_from_graph_api_response(
            response=response_typed
        )
        return group_ids, response_typed.get("odata_nextLink")

    @staticmethod
    def _get_group_ids_from_graph_api_response(
        response: MicrosoftGraphAPIUserGroupResponse,
    ) -> List[str]:
        group_ids = []
        for _object in response.get("value", []) or []:
            _group_id = _object.get("id")
            if _group_id is not None:
                group_ids.append(_group_id)
        return group_ids

    @staticmethod
    async def _cast_graph_api_response_dict(
        response: dict,
    ) -> MicrosoftGraphAPIUserGroupResponse:
        directory_objects: List[MicrosoftGraphAPIUserGroupDirectoryObject] = []
        for _object in response.get("value", []):
            directory_objects.append(
                MicrosoftGraphAPIUserGroupDirectoryObject(
                    odata_type=_object.get("@odata.type"),
                    id=_object.get("id"),
                    deletedDateTime=_object.get("deletedDateTime"),
                    description=_object.get("description"),
                    displayName=_object.get("displayName"),
                    roleTemplateId=_object.get("roleTemplateId"),
                )
            )
        return MicrosoftGraphAPIUserGroupResponse(
            odata_context=response.get("@odata.context"),
            odata_nextLink=response.get("@odata.nextLink"),
            value=directory_objects,
        )

    @staticmethod
    async def get_group_ids_from_service_principal(
        service_principal_id: str,
        async_client: AsyncHTTPHandler,
        access_token: Optional[str] = None,
    ) -> Tuple[List[str], List[MicrosoftServicePrincipalTeam]]:
        """
        Gets the groups belonging to the Service Principal Application

        Service Principal Id is an `Enterprise Application` in Azure AD

        Users use Enterprise Applications to manage Groups and Users on Microsoft Entra ID
        """
        base_url = "https://graph.microsoft.com/v1.0"
        # Endpoint to get app role assignments for the given service principal
        endpoint = f"/servicePrincipals/{service_principal_id}/appRoleAssignedTo"
        url = base_url + endpoint

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = await async_client.get(url, headers=headers)
        response_json = response.json()
        verbose_proxy_logger.debug(
            f"Response from service principal app role assigned to: {response_json}"
        )
        group_ids: List[str] = []
        service_principal_teams: List[MicrosoftServicePrincipalTeam] = []

        for _object in response_json.get("value", []):
            if _object.get("principalType") == "Group":
                # Append the group ID to the list
                group_ids.append(_object.get("principalId"))
                # Append the service principal team to the list
                service_principal_teams.append(
                    MicrosoftServicePrincipalTeam(
                        principalDisplayName=_object.get("principalDisplayName"),
                        principalId=_object.get("principalId"),
                    )
                )

        return group_ids, service_principal_teams

    @staticmethod
    async def create_litellm_teams_from_service_principal_team_ids(
        service_principal_teams: List[MicrosoftServicePrincipalTeam],
    ):
        """
        Creates Litellm Teams from the Service Principal Group IDs

        When a user sets a `SERVICE_PRINCIPAL_ID` in the env, litellm will fetch groups under that service principal and create Litellm Teams from them
        """
        verbose_proxy_logger.debug(
            f"Creating Litellm Teams from Service Principal Teams: {service_principal_teams}"
        )
        for service_principal_team in service_principal_teams:
            litellm_team_id: Optional[str] = service_principal_team.get("principalId")
            litellm_team_name: Optional[str] = service_principal_team.get(
                "principalDisplayName"
            )
            if not litellm_team_id:
                verbose_proxy_logger.debug(
                    f"Skipping team creation for {litellm_team_name} because it has no principalId"
                )
                continue

            await SSOAuthenticationHandler.create_litellm_team_from_sso_group(
                litellm_team_id=litellm_team_id,
                litellm_team_name=litellm_team_name,
            )


class GoogleSSOHandler:
    """
    Handles Google SSO callback response and returns a CustomOpenID object
    """

    @staticmethod
    async def get_google_callback_response(
        request: Request,
        google_client_id: str,
        redirect_url: str,
        return_raw_sso_response: bool = False,
    ) -> Union[OpenID, dict]:
        """
        Get the Google SSO callback response

        Args:
            return_raw_sso_response: If True, return the raw SSO response
        """
        from fastapi_sso.sso.google import GoogleSSO

        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", None)
        if google_client_secret is None:
            raise ProxyException(
                message="GOOGLE_CLIENT_SECRET not set. Set it in .env file",
                type=ProxyErrorTypes.auth_error,
                param="GOOGLE_CLIENT_SECRET",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        google_sso = GoogleSSO(
            client_id=google_client_id,
            redirect_uri=redirect_url,
            client_secret=google_client_secret,
        )

        # if user is trying to get the raw sso response for debugging, return the raw sso response
        if return_raw_sso_response:
            return (
                await google_sso.verify_and_process(
                    request=request,
                    convert_response=False,  # type: ignore
                )
                or {}
            )

        result = await google_sso.verify_and_process(request)
        return result or {}


@router.get("/sso/debug/login", tags=["experimental"], include_in_schema=False)
async def debug_sso_login(request: Request):
    """
    Create Proxy API Keys using Google Workspace SSO. Requires setting PROXY_BASE_URL in .env
    PROXY_BASE_URL should be the your deployed proxy endpoint, e.g. PROXY_BASE_URL="https://litellm-production-7002.up.railway.app/"
    Example:
    """
    from litellm.proxy.proxy_server import premium_user

    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID", None)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", None)
    generic_client_id = os.getenv("GENERIC_CLIENT_ID", None)

    ####### Check if user is a Enterprise / Premium User #######
    if (
        microsoft_client_id is not None
        or google_client_id is not None
        or generic_client_id is not None
    ):
        if premium_user is not True:
            raise ProxyException(
                message="You must be a LiteLLM Enterprise user to use SSO. If you have a license please set `LITELLM_LICENSE` in your env. If you want to obtain a license meet with us here: https://calendly.com/d/4mp-gd3-k5k/litellm-1-1-onboarding-chat You are seeing this error message because You set one of `MICROSOFT_CLIENT_ID`, `GOOGLE_CLIENT_ID`, or `GENERIC_CLIENT_ID` in your env. Please unset this",
                type=ProxyErrorTypes.auth_error,
                param="premium_user",
                code=status.HTTP_403_FORBIDDEN,
            )

    # get url from request
    redirect_url = SSOAuthenticationHandler.get_redirect_url_for_sso(
        request=request,
        sso_callback_route="sso/debug/callback",
    )

    # Check if we should use SSO handler
    if (
        SSOAuthenticationHandler.should_use_sso_handler(
            microsoft_client_id=microsoft_client_id,
            google_client_id=google_client_id,
            generic_client_id=generic_client_id,
        )
        is True
    ):
        return await SSOAuthenticationHandler.get_sso_login_redirect(
            redirect_url=redirect_url,
            microsoft_client_id=microsoft_client_id,
            google_client_id=google_client_id,
            generic_client_id=generic_client_id,
        )


@router.get("/sso/debug/callback", tags=["experimental"], include_in_schema=False)
async def debug_sso_callback(request: Request):
    """
    Returns the OpenID object returned by the SSO provider
    """
    import json

    from fastapi.responses import HTMLResponse

    from litellm.proxy.proxy_server import jwt_handler

    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID", None)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", None)
    generic_client_id = os.getenv("GENERIC_CLIENT_ID", None)

    redirect_url = os.getenv("PROXY_BASE_URL", str(request.base_url))
    if redirect_url.endswith("/"):
        redirect_url += "sso/debug/callback"
    else:
        redirect_url += "/sso/debug/callback"

    result = None
    if google_client_id is not None:
        result = await GoogleSSOHandler.get_google_callback_response(
            request=request,
            google_client_id=google_client_id,
            redirect_url=redirect_url,
            return_raw_sso_response=True,
        )
    elif microsoft_client_id is not None:
        result = await MicrosoftSSOHandler.get_microsoft_callback_response(
            request=request,
            microsoft_client_id=microsoft_client_id,
            redirect_url=redirect_url,
            return_raw_sso_response=True,
        )

    elif generic_client_id is not None:
        result = await get_generic_sso_response(
            request=request,
            jwt_handler=jwt_handler,
            generic_client_id=generic_client_id,
            redirect_url=redirect_url,
        )

    # If result is None, return a basic error message
    if result is None:
        return HTMLResponse(
            content="<h1>SSO Authentication Failed</h1><p>No data was returned from the SSO provider.</p>",
            status_code=400,
        )

    # Convert the OpenID object to a dictionary
    if hasattr(result, "__dict__"):
        result_dict = result.__dict__
    else:
        result_dict = dict(result)

    # Filter out any None values and convert to JSON serializable format
    filtered_result = {}
    for key, value in result_dict.items():
        if value is not None and not key.startswith("_"):
            if isinstance(value, (str, int, float, bool)) or value is None:
                filtered_result[key] = value
            else:
                try:
                    # Try to convert to string or another JSON serializable format
                    filtered_result[key] = str(value)
                except Exception as e:
                    filtered_result[key] = f"Complex value (not displayable): {str(e)}"

    # Replace the placeholder in the template with the actual data
    html_content = jwt_display_template.replace(
        "const userData = SSO_DATA;",
        f"const userData = {json.dumps(filtered_result, indent=2)};",
    )

    return HTMLResponse(content=html_content)

# === NexusCore/openenv\Lib\site-packages\tornado\iostream.py ===
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Utility classes to write to and read from non-blocking files and sockets.

Contents:

* `BaseIOStream`: Generic interface for reading and writing.
* `IOStream`: Implementation of BaseIOStream using non-blocking sockets.
* `SSLIOStream`: SSL-aware version of IOStream.
* `PipeIOStream`: Pipe-based IOStream implementation.
"""

import asyncio
import collections
import errno
import io
import numbers
import os
import socket
import ssl
import sys
import re

from tornado.concurrent import Future, future_set_result_unless_cancelled
from tornado import ioloop
from tornado.log import gen_log
from tornado.netutil import ssl_wrap_socket, _client_ssl_defaults, _server_ssl_defaults
from tornado.util import errno_from_exception

import typing
from typing import (
    Union,
    Optional,
    Awaitable,
    Callable,
    Pattern,
    Any,
    Dict,
    TypeVar,
    Tuple,
)
from types import TracebackType

if typing.TYPE_CHECKING:
    from typing import Deque, List, Type  # noqa: F401

_IOStreamType = TypeVar("_IOStreamType", bound="IOStream")

# These errnos indicate that a connection has been abruptly terminated.
# They should be caught and handled less noisily than other errors.
_ERRNO_CONNRESET = (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE, errno.ETIMEDOUT)

if hasattr(errno, "WSAECONNRESET"):
    _ERRNO_CONNRESET += (  # type: ignore
        errno.WSAECONNRESET,  # type: ignore
        errno.WSAECONNABORTED,  # type: ignore
        errno.WSAETIMEDOUT,  # type: ignore
    )

if sys.platform == "darwin":
    # OSX appears to have a race condition that causes send(2) to return
    # EPROTOTYPE if called while a socket is being torn down:
    # http://erickt.github.io/blog/2014/11/19/adventures-in-debugging-a-potential-osx-kernel-bug/
    # Since the socket is being closed anyway, treat this as an ECONNRESET
    # instead of an unexpected error.
    _ERRNO_CONNRESET += (errno.EPROTOTYPE,)  # type: ignore

_WINDOWS = sys.platform.startswith("win")


class StreamClosedError(IOError):
    """Exception raised by `IOStream` methods when the stream is closed.

    Note that the close callback is scheduled to run *after* other
    callbacks on the stream (to allow for buffered data to be processed),
    so you may see this error before you see the close callback.

    The ``real_error`` attribute contains the underlying error that caused
    the stream to close (if any).

    .. versionchanged:: 4.3
       Added the ``real_error`` attribute.
    """

    def __init__(self, real_error: Optional[BaseException] = None) -> None:
        super().__init__("Stream is closed")
        self.real_error = real_error


class UnsatisfiableReadError(Exception):
    """Exception raised when a read cannot be satisfied.

    Raised by ``read_until`` and ``read_until_regex`` with a ``max_bytes``
    argument.
    """

    pass


class StreamBufferFullError(Exception):
    """Exception raised by `IOStream` methods when the buffer is full."""


class _StreamBuffer:
    """
    A specialized buffer that tries to avoid copies when large pieces
    of data are encountered.
    """

    def __init__(self) -> None:
        # A sequence of (False, bytearray) and (True, memoryview) objects
        self._buffers = (
            collections.deque()
        )  # type: Deque[Tuple[bool, Union[bytearray, memoryview]]]
        # Position in the first buffer
        self._first_pos = 0
        self._size = 0

    def __len__(self) -> int:
        return self._size

    # Data above this size will be appended separately instead
    # of extending an existing bytearray
    _large_buf_threshold = 2048

    def append(self, data: Union[bytes, bytearray, memoryview]) -> None:
        """
        Append the given piece of data (should be a buffer-compatible object).
        """
        size = len(data)
        if size > self._large_buf_threshold:
            if not isinstance(data, memoryview):
                data = memoryview(data)
            self._buffers.append((True, data))
        elif size > 0:
            if self._buffers:
                is_memview, b = self._buffers[-1]
                new_buf = is_memview or len(b) >= self._large_buf_threshold
            else:
                new_buf = True
            if new_buf:
                self._buffers.append((False, bytearray(data)))
            else:
                b += data  # type: ignore

        self._size += size

    def peek(self, size: int) -> memoryview:
        """
        Get a view over at most ``size`` bytes (possibly fewer) at the
        current buffer position.
        """
        assert size > 0
        try:
            is_memview, b = self._buffers[0]
        except IndexError:
            return memoryview(b"")

        pos = self._first_pos
        if is_memview:
            return typing.cast(memoryview, b[pos : pos + size])
        else:
            return memoryview(b)[pos : pos + size]

    def advance(self, size: int) -> None:
        """
        Advance the current buffer position by ``size`` bytes.
        """
        assert 0 < size <= self._size
        self._size -= size
        pos = self._first_pos

        buffers = self._buffers
        while buffers and size > 0:
            is_large, b = buffers[0]
            b_remain = len(b) - size - pos
            if b_remain <= 0:
                buffers.popleft()
                size -= len(b) - pos
                pos = 0
            elif is_large:
                pos += size
                size = 0
            else:
                pos += size
                del typing.cast(bytearray, b)[:pos]
                pos = 0
                size = 0

        assert size == 0
        self._first_pos = pos


class BaseIOStream:
    """A utility class to write to and read from a non-blocking file or socket.

    We support a non-blocking ``write()`` and a family of ``read_*()``
    methods. When the operation completes, the ``Awaitable`` will resolve
    with the data read (or ``None`` for ``write()``). All outstanding
    ``Awaitables`` will resolve with a `StreamClosedError` when the
    stream is closed; `.BaseIOStream.set_close_callback` can also be used
    to be notified of a closed stream.

    When a stream is closed due to an error, the IOStream's ``error``
    attribute contains the exception object.

    Subclasses must implement `fileno`, `close_fd`, `write_to_fd`,
    `read_from_fd`, and optionally `get_fd_error`.

    """

    def __init__(
        self,
        max_buffer_size: Optional[int] = None,
        read_chunk_size: Optional[int] = None,
        max_write_buffer_size: Optional[int] = None,
    ) -> None:
        """`BaseIOStream` constructor.

        :arg max_buffer_size: Maximum amount of incoming data to buffer;
            defaults to 100MB.
        :arg read_chunk_size: Amount of data to read at one time from the
            underlying transport; defaults to 64KB.
        :arg max_write_buffer_size: Amount of outgoing data to buffer;
            defaults to unlimited.

        .. versionchanged:: 4.0
           Add the ``max_write_buffer_size`` parameter.  Changed default
           ``read_chunk_size`` to 64KB.
        .. versionchanged:: 5.0
           The ``io_loop`` argument (deprecated since version 4.1) has been
           removed.
        """
        self.io_loop = ioloop.IOLoop.current()
        self.max_buffer_size = max_buffer_size or 104857600
        # A chunk size that is too close to max_buffer_size can cause
        # spurious failures.
        self.read_chunk_size = min(read_chunk_size or 65536, self.max_buffer_size // 2)
        self.max_write_buffer_size = max_write_buffer_size
        self.error = None  # type: Optional[BaseException]
        self._read_buffer = bytearray()
        self._read_buffer_size = 0
        self._user_read_buffer = False
        self._after_user_read_buffer = None  # type: Optional[bytearray]
        self._write_buffer = _StreamBuffer()
        self._total_write_index = 0
        self._total_write_done_index = 0
        self._read_delimiter = None  # type: Optional[bytes]
        self._read_regex = None  # type: Optional[Pattern]
        self._read_max_bytes = None  # type: Optional[int]
        self._read_bytes = None  # type: Optional[int]
        self._read_partial = False
        self._read_until_close = False
        self._read_future = None  # type: Optional[Future]
        self._write_futures = (
            collections.deque()
        )  # type: Deque[Tuple[int, Future[None]]]
        self._close_callback = None  # type: Optional[Callable[[], None]]
        self._connect_future = None  # type: Optional[Future[IOStream]]
        # _ssl_connect_future should be defined in SSLIOStream
        # but it's here so we can clean it up in _signal_closed
        # TODO: refactor that so subclasses can add additional futures
        # to be cancelled.
        self._ssl_connect_future = None  # type: Optional[Future[SSLIOStream]]
        self._connecting = False
        self._state = None  # type: Optional[int]
        self._closed = False

    def fileno(self) -> Union[int, ioloop._Selectable]:
        """Returns the file descriptor for this stream."""
        raise NotImplementedError()

    def close_fd(self) -> None:
        """Closes the file underlying this stream.

        ``close_fd`` is called by `BaseIOStream` and should not be called
        elsewhere; other users should call `close` instead.
        """
        raise NotImplementedError()

    def write_to_fd(self, data: memoryview) -> int:
        """Attempts to write ``data`` to the underlying file.

        Returns the number of bytes written.
        """
        raise NotImplementedError()

    def read_from_fd(self, buf: Union[bytearray, memoryview]) -> Optional[int]:
        """Attempts to read from the underlying file.

        Reads up to ``len(buf)`` bytes, storing them in the buffer.
        Returns the number of bytes read. Returns None if there was
        nothing to read (the socket returned `~errno.EWOULDBLOCK` or
        equivalent), and zero on EOF.

        .. versionchanged:: 5.0

           Interface redesigned to take a buffer and return a number
           of bytes instead of a freshly-allocated object.
        """
        raise NotImplementedError()

    def get_fd_error(self) -> Optional[Exception]:
        """Returns information about any error on the underlying file.

        This method is called after the `.IOLoop` has signaled an error on the
        file descriptor, and should return an Exception (such as `socket.error`
        with additional information, or None if no such information is
        available.
        """
        return None

    def read_until_regex(
        self, regex: bytes, max_bytes: Optional[int] = None
    ) -> Awaitable[bytes]:
        """Asynchronously read until we have matched the given regex.

        The result includes the data that matches the regex and anything
        that came before it.

        If ``max_bytes`` is not None, the connection will be closed
        if more than ``max_bytes`` bytes have been read and the regex is
        not satisfied.

        .. versionchanged:: 4.0
            Added the ``max_bytes`` argument.  The ``callback`` argument is
            now optional and a `.Future` will be returned if it is omitted.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.

        """
        future = self._start_read()
        self._read_regex = re.compile(regex)
        self._read_max_bytes = max_bytes
        try:
            self._try_inline_read()
        except UnsatisfiableReadError as e:
            # Handle this the same way as in _handle_events.
            gen_log.info("Unsatisfiable read, closing connection: %s" % e)
            self.close(exc_info=e)
            return future
        except:
            # Ensure that the future doesn't log an error because its
            # failure was never examined.
            future.add_done_callback(lambda f: f.exception())
            raise
        return future

    def read_until(
        self, delimiter: bytes, max_bytes: Optional[int] = None
    ) -> Awaitable[bytes]:
        """Asynchronously read until we have found the given delimiter.

        The result includes all the data read including the delimiter.

        If ``max_bytes`` is not None, the connection will be closed
        if more than ``max_bytes`` bytes have been read and the delimiter
        is not found.

        .. versionchanged:: 4.0
            Added the ``max_bytes`` argument.  The ``callback`` argument is
            now optional and a `.Future` will be returned if it is omitted.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.
        """
        future = self._start_read()
        self._read_delimiter = delimiter
        self._read_max_bytes = max_bytes
        try:
            self._try_inline_read()
        except UnsatisfiableReadError as e:
            # Handle this the same way as in _handle_events.
            gen_log.info("Unsatisfiable read, closing connection: %s" % e)
            self.close(exc_info=e)
            return future
        except:
            future.add_done_callback(lambda f: f.exception())
            raise
        return future

    def read_bytes(self, num_bytes: int, partial: bool = False) -> Awaitable[bytes]:
        """Asynchronously read a number of bytes.

        If ``partial`` is true, data is returned as soon as we have
        any bytes to return (but never more than ``num_bytes``)

        .. versionchanged:: 4.0
            Added the ``partial`` argument.  The callback argument is now
            optional and a `.Future` will be returned if it is omitted.

        .. versionchanged:: 6.0

           The ``callback`` and ``streaming_callback`` arguments have
           been removed. Use the returned `.Future` (and
           ``partial=True`` for ``streaming_callback``) instead.

        """
        future = self._start_read()
        assert isinstance(num_bytes, numbers.Integral)
        self._read_bytes = num_bytes
        self._read_partial = partial
        try:
            self._try_inline_read()
        except:
            future.add_done_callback(lambda f: f.exception())
            raise
        return future

    def read_into(self, buf: bytearray, partial: bool = False) -> Awaitable[int]:
        """Asynchronously read a number of bytes.

        ``buf`` must be a writable buffer into which data will be read.

        If ``partial`` is true, the callback is run as soon as any bytes
        have been read.  Otherwise, it is run when the ``buf`` has been
        entirely filled with read data.

        .. versionadded:: 5.0

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.

        """
        future = self._start_read()

        # First copy data already in read buffer
        available_bytes = self._read_buffer_size
        n = len(buf)
        if available_bytes >= n:
            buf[:] = memoryview(self._read_buffer)[:n]
            del self._read_buffer[:n]
            self._after_user_read_buffer = self._read_buffer
        elif available_bytes > 0:
            buf[:available_bytes] = memoryview(self._read_buffer)[:]

        # Set up the supplied buffer as our temporary read buffer.
        # The original (if it had any data remaining) has been
        # saved for later.
        self._user_read_buffer = True
        self._read_buffer = buf
        self._read_buffer_size = available_bytes
        self._read_bytes = n
        self._read_partial = partial

        try:
            self._try_inline_read()
        except:
            future.add_done_callback(lambda f: f.exception())
            raise
        return future

    def read_until_close(self) -> Awaitable[bytes]:
        """Asynchronously reads all data from the socket until it is closed.

        This will buffer all available data until ``max_buffer_size``
        is reached. If flow control or cancellation are desired, use a
        loop with `read_bytes(partial=True) <.read_bytes>` instead.

        .. versionchanged:: 4.0
            The callback argument is now optional and a `.Future` will
            be returned if it is omitted.

        .. versionchanged:: 6.0

           The ``callback`` and ``streaming_callback`` arguments have
           been removed. Use the returned `.Future` (and `read_bytes`
           with ``partial=True`` for ``streaming_callback``) instead.

        """
        future = self._start_read()
        if self.closed():
            self._finish_read(self._read_buffer_size)
            return future
        self._read_until_close = True
        try:
            self._try_inline_read()
        except:
            future.add_done_callback(lambda f: f.exception())
            raise
        return future

    def write(self, data: Union[bytes, memoryview]) -> "Future[None]":
        """Asynchronously write the given data to this stream.

        This method returns a `.Future` that resolves (with a result
        of ``None``) when the write has been completed.

        The ``data`` argument may be of type `bytes` or `memoryview`.

        .. versionchanged:: 4.0
            Now returns a `.Future` if no callback is given.

        .. versionchanged:: 4.5
            Added support for `memoryview` arguments.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.

        """
        self._check_closed()
        if data:
            if isinstance(data, memoryview):
                # Make sure that ``len(data) == data.nbytes``
                data = memoryview(data).cast("B")
            if (
                self.max_write_buffer_size is not None
                and len(self._write_buffer) + len(data) > self.max_write_buffer_size
            ):
                raise StreamBufferFullError("Reached maximum write buffer size")
            self._write_buffer.append(data)
            self._total_write_index += len(data)
        future = Future()  # type: Future[None]
        future.add_done_callback(lambda f: f.exception())
        self._write_futures.append((self._total_write_index, future))
        if not self._connecting:
            self._handle_write()
            if self._write_buffer:
                self._add_io_state(self.io_loop.WRITE)
            self._maybe_add_error_listener()
        return future

    def set_close_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Call the given callback when the stream is closed.

        This mostly is not necessary for applications that use the
        `.Future` interface; all outstanding ``Futures`` will resolve
        with a `StreamClosedError` when the stream is closed. However,
        it is still useful as a way to signal that the stream has been
        closed while no other read or write is in progress.

        Unlike other callback-based interfaces, ``set_close_callback``
        was not removed in Tornado 6.0.
        """
        self._close_callback = callback
        self._maybe_add_error_listener()

    def close(
        self,
        exc_info: Union[
            None,
            bool,
            BaseException,
            Tuple[
                "Optional[Type[BaseException]]",
                Optional[BaseException],
                Optional[TracebackType],
            ],
        ] = False,
    ) -> None:
        """Close this stream.

        If ``exc_info`` is true, set the ``error`` attribute to the current
        exception from `sys.exc_info` (or if ``exc_info`` is a tuple,
        use that instead of `sys.exc_info`).
        """
        if not self.closed():
            if exc_info:
                if isinstance(exc_info, tuple):
                    self.error = exc_info[1]
                elif isinstance(exc_info, BaseException):
                    self.error = exc_info
                else:
                    exc_info = sys.exc_info()
                    if any(exc_info):
                        self.error = exc_info[1]
            if self._read_until_close:
                self._read_until_close = False
                self._finish_read(self._read_buffer_size)
            elif self._read_future is not None:
                # resolve reads that are pending and ready to complete
                try:
                    pos = self._find_read_pos()
                except UnsatisfiableReadError:
                    pass
                else:
                    if pos is not None:
                        self._read_from_buffer(pos)
            if self._state is not None:
                self.io_loop.remove_handler(self.fileno())
                self._state = None
            self.close_fd()
            self._closed = True
        self._signal_closed()

    def _signal_closed(self) -> None:
        futures = []  # type: List[Future]
        if self._read_future is not None:
            futures.append(self._read_future)
            self._read_future = None
        futures += [future for _, future in self._write_futures]
        self._write_futures.clear()
        if self._connect_future is not None:
            futures.append(self._connect_future)
            self._connect_future = None
        for future in futures:
            if not future.done():
                future.set_exception(StreamClosedError(real_error=self.error))
            # Reference the exception to silence warnings. Annoyingly,
            # this raises if the future was cancelled, but just
            # returns any other error.
            try:
                future.exception()
            except asyncio.CancelledError:
                pass
        if self._ssl_connect_future is not None:
            # _ssl_connect_future expects to see the real exception (typically
            # an ssl.SSLError), not just StreamClosedError.
            if not self._ssl_connect_future.done():
                if self.error is not None:
                    self._ssl_connect_future.set_exception(self.error)
                else:
                    self._ssl_connect_future.set_exception(StreamClosedError())
            self._ssl_connect_future.exception()
            self._ssl_connect_future = None
        if self._close_callback is not None:
            cb = self._close_callback
            self._close_callback = None
            self.io_loop.add_callback(cb)
        # Clear the buffers so they can be cleared immediately even
        # if the IOStream object is kept alive by a reference cycle.
        # TODO: Clear the read buffer too; it currently breaks some tests.
        self._write_buffer = None  # type: ignore

    def reading(self) -> bool:
        """Returns ``True`` if we are currently reading from the stream."""
        return self._read_future is not None

    def writing(self) -> bool:
        """Returns ``True`` if we are currently writing to the stream."""
        return bool(self._write_buffer)

    def closed(self) -> bool:
        """Returns ``True`` if the stream has been closed."""
        return self._closed

    def set_nodelay(self, value: bool) -> None:
        """Sets the no-delay flag for this stream.

        By default, data written to TCP streams may be held for a time
        to make the most efficient use of bandwidth (according to
        Nagle's algorithm).  The no-delay flag requests that data be
        written as soon as possible, even if doing so would consume
        additional bandwidth.

        This flag is currently defined only for TCP-based ``IOStreams``.

        .. versionadded:: 3.1
        """
        pass

    def _handle_connect(self) -> None:
        raise NotImplementedError()

    def _handle_events(self, fd: Union[int, ioloop._Selectable], events: int) -> None:
        if self.closed():
            gen_log.warning("Got events for closed stream %s", fd)
            return
        try:
            if self._connecting:
                # Most IOLoops will report a write failed connect
                # with the WRITE event, but SelectIOLoop reports a
                # READ as well so we must check for connecting before
                # either.
                self._handle_connect()
            if self.closed():
                return
            if events & self.io_loop.READ:
                self._handle_read()
            if self.closed():
                return
            if events & self.io_loop.WRITE:
                self._handle_write()
            if self.closed():
                return
            if events & self.io_loop.ERROR:
                self.error = self.get_fd_error()
                # We may have queued up a user callback in _handle_read or
                # _handle_write, so don't close the IOStream until those
                # callbacks have had a chance to run.
                self.io_loop.add_callback(self.close)
                return
            state = self.io_loop.ERROR
            if self.reading():
                state |= self.io_loop.READ
            if self.writing():
                state |= self.io_loop.WRITE
            if state == self.io_loop.ERROR and self._read_buffer_size == 0:
                # If the connection is idle, listen for reads too so
                # we can tell if the connection is closed.  If there is
                # data in the read buffer we won't run the close callback
                # yet anyway, so we don't need to listen in this case.
                state |= self.io_loop.READ
            if state != self._state:
                assert (
                    self._state is not None
                ), "shouldn't happen: _handle_events without self._state"
                self._state = state
                self.io_loop.update_handler(self.fileno(), self._state)
        except UnsatisfiableReadError as e:
            gen_log.info("Unsatisfiable read, closing connection: %s" % e)
            self.close(exc_info=e)
        except Exception as e:
            gen_log.error("Uncaught exception, closing connection.", exc_info=True)
            self.close(exc_info=e)
            raise

    def _read_to_buffer_loop(self) -> Optional[int]:
        # This method is called from _handle_read and _try_inline_read.
        if self._read_bytes is not None:
            target_bytes = self._read_bytes  # type: Optional[int]
        elif self._read_max_bytes is not None:
            target_bytes = self._read_max_bytes
        elif self.reading():
            # For read_until without max_bytes, or
            # read_until_close, read as much as we can before
            # scanning for the delimiter.
            target_bytes = None
        else:
            target_bytes = 0
        next_find_pos = 0
        while not self.closed():
            # Read from the socket until we get EWOULDBLOCK or equivalent.
            # SSL sockets do some internal buffering, and if the data is
            # sitting in the SSL object's buffer select() and friends
            # can't see it; the only way to find out if it's there is to
            # try to read it.
            if self._read_to_buffer() == 0:
                break

            # If we've read all the bytes we can use, break out of
            # this loop.

            # If we've reached target_bytes, we know we're done.
            if target_bytes is not None and self._read_buffer_size >= target_bytes:
                break

            # Otherwise, we need to call the more expensive find_read_pos.
            # It's inefficient to do this on every read, so instead
            # do it on the first read and whenever the read buffer
            # size has doubled.
            if self._read_buffer_size >= next_find_pos:
                pos = self._find_read_pos()
                if pos is not None:
                    return pos
                next_find_pos = self._read_buffer_size * 2
        return self._find_read_pos()

    def _handle_read(self) -> None:
        try:
            pos = self._read_to_buffer_loop()
        except UnsatisfiableReadError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            gen_log.warning("error on read: %s" % e)
            self.close(exc_info=e)
            return
        if pos is not None:
            self._read_from_buffer(pos)

    def _start_read(self) -> Future:
        if self._read_future is not None:
            # It is an error to start a read while a prior read is unresolved.
            # However, if the prior read is unresolved because the stream was
            # closed without satisfying it, it's better to raise
            # StreamClosedError instead of AssertionError. In particular, this
            # situation occurs in harmless situations in http1connection.py and
            # an AssertionError would be logged noisily.
            #
            # On the other hand, it is legal to start a new read while the
            # stream is closed, in case the read can be satisfied from the
            # read buffer. So we only want to check the closed status of the
            # stream if we need to decide what kind of error to raise for
            # "already reading".
            #
            # These conditions have proven difficult to test; we have no
            # unittests that reliably verify this behavior so be careful
            # when making changes here. See #2651 and #2719.
            self._check_closed()
            assert self._read_future is None, "Already reading"
        self._read_future = Future()
        return self._read_future

    def _finish_read(self, size: int) -> None:
        if self._user_read_buffer:
            self._read_buffer = self._after_user_read_buffer or bytearray()
            self._after_user_read_buffer = None
            self._read_buffer_size = len(self._read_buffer)
            self._user_read_buffer = False
            result = size  # type: Union[int, bytes]
        else:
            result = self._consume(size)
        if self._read_future is not None:
            future = self._read_future
            self._read_future = None
            future_set_result_unless_cancelled(future, result)
        self._maybe_add_error_listener()

    def _try_inline_read(self) -> None:
        """Attempt to complete the current read operation from buffered data.

        If the read can be completed without blocking, schedules the
        read callback on the next IOLoop iteration; otherwise starts
        listening for reads on the socket.
        """
        # See if we've already got the data from a previous read
        pos = self._find_read_pos()
        if pos is not None:
            self._read_from_buffer(pos)
            return
        self._check_closed()
        pos = self._read_to_buffer_loop()
        if pos is not None:
            self._read_from_buffer(pos)
            return
        # We couldn't satisfy the read inline, so make sure we're
        # listening for new data unless the stream is closed.
        if not self.closed():
            self._add_io_state(ioloop.IOLoop.READ)

    def _read_to_buffer(self) -> Optional[int]:
        """Reads from the socket and appends the result to the read buffer.

        Returns the number of bytes read.  Returns 0 if there is nothing
        to read (i.e. the read returns EWOULDBLOCK or equivalent).  On
        error closes the socket and raises an exception.
        """
        try:
            while True:
                try:
                    if self._user_read_buffer:
                        buf = memoryview(self._read_buffer)[
                            self._read_buffer_size :
                        ]  # type: Union[memoryview, bytearray]
                    else:
                        buf = bytearray(self.read_chunk_size)
                    bytes_read = self.read_from_fd(buf)
                except OSError as e:
                    # ssl.SSLError is a subclass of socket.error
                    if self._is_connreset(e):
                        # Treat ECONNRESET as a connection close rather than
                        # an error to minimize log spam  (the exception will
                        # be available on self.error for apps that care).
                        self.close(exc_info=e)
                        return None
                    self.close(exc_info=e)
                    raise
                break
            if bytes_read is None:
                return 0
            elif bytes_read == 0:
                self.close()
                return 0
            if not self._user_read_buffer:
                self._read_buffer += memoryview(buf)[:bytes_read]
            self._read_buffer_size += bytes_read
        finally:
            # Break the reference to buf so we don't waste a chunk's worth of
            # memory in case an exception hangs on to our stack frame.
            del buf
        if self._read_buffer_size > self.max_buffer_size:
            gen_log.error("Reached maximum read buffer size")
            self.close()
            raise StreamBufferFullError("Reached maximum read buffer size")
        return bytes_read

    def _read_from_buffer(self, pos: int) -> None:
        """Attempts to complete the currently-pending read from the buffer.

        The argument is either a position in the read buffer or None,
        as returned by _find_read_pos.
        """
        self._read_bytes = self._read_delimiter = self._read_regex = None
        self._read_partial = False
        self._finish_read(pos)

    def _find_read_pos(self) -> Optional[int]:
        """Attempts to find a position in the read buffer that satisfies
        the currently-pending read.

        Returns a position in the buffer if the current read can be satisfied,
        or None if it cannot.
        """
        if self._read_bytes is not None and (
            self._read_buffer_size >= self._read_bytes
            or (self._read_partial and self._read_buffer_size > 0)
        ):
            num_bytes = min(self._read_bytes, self._read_buffer_size)
            return num_bytes
        elif self._read_delimiter is not None:
            # Multi-byte delimiters (e.g. '\r\n') may straddle two
            # chunks in the read buffer, so we can't easily find them
            # without collapsing the buffer.  However, since protocols
            # using delimited reads (as opposed to reads of a known
            # length) tend to be "line" oriented, the delimiter is likely
            # to be in the first few chunks.  Merge the buffer gradually
            # since large merges are relatively expensive and get undone in
            # _consume().
            if self._read_buffer:
                loc = self._read_buffer.find(self._read_delimiter)
                if loc != -1:
                    delimiter_len = len(self._read_delimiter)
                    self._check_max_bytes(self._read_delimiter, loc + delimiter_len)
                    return loc + delimiter_len
                self._check_max_bytes(self._read_delimiter, self._read_buffer_size)
        elif self._read_regex is not None:
            if self._read_buffer:
                m = self._read_regex.search(self._read_buffer)
                if m is not None:
                    loc = m.end()
                    self._check_max_bytes(self._read_regex, loc)
                    return loc
                self._check_max_bytes(self._read_regex, self._read_buffer_size)
        return None

    def _check_max_bytes(self, delimiter: Union[bytes, Pattern], size: int) -> None:
        if self._read_max_bytes is not None and size > self._read_max_bytes:
            raise UnsatisfiableReadError(
                "delimiter %r not found within %d bytes"
                % (delimiter, self._read_max_bytes)
            )

    def _handle_write(self) -> None:
        while True:
            size = len(self._write_buffer)
            if not size:
                break
            assert size > 0
            try:
                if _WINDOWS:
                    # On windows, socket.send blows up if given a
                    # write buffer that's too large, instead of just
                    # returning the number of bytes it was able to
                    # process.  Therefore we must not call socket.send
                    # with more than 128KB at a time.
                    size = 128 * 1024

                num_bytes = self.write_to_fd(self._write_buffer.peek(size))
                if num_bytes == 0:
                    break
                self._write_buffer.advance(num_bytes)
                self._total_write_done_index += num_bytes
            except BlockingIOError:
                break
            except OSError as e:
                if not self._is_connreset(e):
                    # Broken pipe errors are usually caused by connection
                    # reset, and its better to not log EPIPE errors to
                    # minimize log spam
                    gen_log.warning("Write error on %s: %s", self.fileno(), e)
                self.close(exc_info=e)
                return

        while self._write_futures:
            index, future = self._write_futures[0]
            if index > self._total_write_done_index:
                break
            self._write_futures.popleft()
            future_set_result_unless_cancelled(future, None)

    def _consume(self, loc: int) -> bytes:
        # Consume loc bytes from the read buffer and return them
        if loc == 0:
            return b""
        assert loc <= self._read_buffer_size
        # Slice the bytearray buffer into bytes, without intermediate copying
        b = (memoryview(self._read_buffer)[:loc]).tobytes()
        self._read_buffer_size -= loc
        del self._read_buffer[:loc]
        return b

    def _check_closed(self) -> None:
        if self.closed():
            raise StreamClosedError(real_error=self.error)

    def _maybe_add_error_listener(self) -> None:
        # This method is part of an optimization: to detect a connection that
        # is closed when we're not actively reading or writing, we must listen
        # for read events.  However, it is inefficient to do this when the
        # connection is first established because we are going to read or write
        # immediately anyway.  Instead, we insert checks at various times to
        # see if the connection is idle and add the read listener then.
        if self._state is None or self._state == ioloop.IOLoop.ERROR:
            if (
                not self.closed()
                and self._read_buffer_size == 0
                and self._close_callback is not None
            ):
                self._add_io_state(ioloop.IOLoop.READ)

    def _add_io_state(self, state: int) -> None:
        """Adds `state` (IOLoop.{READ,WRITE} flags) to our event handler.

        Implementation notes: Reads and writes have a fast path and a
        slow path.  The fast path reads synchronously from socket
        buffers, while the slow path uses `_add_io_state` to schedule
        an IOLoop callback.

        To detect closed connections, we must have called
        `_add_io_state` at some point, but we want to delay this as
        much as possible so we don't have to set an `IOLoop.ERROR`
        listener that will be overwritten by the next slow-path
        operation. If a sequence of fast-path ops do not end in a
        slow-path op, (e.g. for an @asynchronous long-poll request),
        we must add the error handler.

        TODO: reevaluate this now that callbacks are gone.

        """
        if self.closed():
            # connection has been closed, so there can be no future events
            return
        if self._state is None:
            self._state = ioloop.IOLoop.ERROR | state
            self.io_loop.add_handler(self.fileno(), self._handle_events, self._state)
        elif not self._state & state:
            self._state = self._state | state
            self.io_loop.update_handler(self.fileno(), self._state)

    def _is_connreset(self, exc: BaseException) -> bool:
        """Return ``True`` if exc is ECONNRESET or equivalent.

        May be overridden in subclasses.
        """
        return (
            isinstance(exc, (socket.error, IOError))
            and errno_from_exception(exc) in _ERRNO_CONNRESET
        )


class IOStream(BaseIOStream):
    r"""Socket-based `IOStream` implementation.

    This class supports the read and write methods from `BaseIOStream`
    plus a `connect` method.

    The ``socket`` parameter may either be connected or unconnected.
    For server operations the socket is the result of calling
    `socket.accept <socket.socket.accept>`.  For client operations the
    socket is created with `socket.socket`, and may either be
    connected before passing it to the `IOStream` or connected with
    `IOStream.connect`.

    A very simple (and broken) HTTP client using this class:

    .. testcode::

        import socket
        import tornado

        async def main():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            stream = tornado.iostream.IOStream(s)
            await stream.connect(("friendfeed.com", 80))
            await stream.write(b"GET / HTTP/1.0\r\nHost: friendfeed.com\r\n\r\n")
            header_data = await stream.read_until(b"\r\n\r\n")
            headers = {}
            for line in header_data.split(b"\r\n"):
                parts = line.split(b":")
                if len(parts) == 2:
                    headers[parts[0].strip()] = parts[1].strip()
            body_data = await stream.read_bytes(int(headers[b"Content-Length"]))
            print(body_data)
            stream.close()

        if __name__ == '__main__':
            asyncio.run(main())

    """

    def __init__(self, socket: socket.socket, *args: Any, **kwargs: Any) -> None:
        self.socket = socket
        self.socket.setblocking(False)
        super().__init__(*args, **kwargs)

    def fileno(self) -> Union[int, ioloop._Selectable]:
        return self.socket

    def close_fd(self) -> None:
        self.socket.close()
        self.socket = None  # type: ignore

    def get_fd_error(self) -> Optional[Exception]:
        errno = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        return socket.error(errno, os.strerror(errno))

    def read_from_fd(self, buf: Union[bytearray, memoryview]) -> Optional[int]:
        try:
            return self.socket.recv_into(buf, len(buf))
        except BlockingIOError:
            return None
        finally:
            del buf

    def write_to_fd(self, data: memoryview) -> int:
        try:
            return self.socket.send(data)  # type: ignore
        finally:
            # Avoid keeping to data, which can be a memoryview.
            # See https://github.com/tornadoweb/tornado/pull/2008
            del data

    def connect(
        self: _IOStreamType, address: Any, server_hostname: Optional[str] = None
    ) -> "Future[_IOStreamType]":
        """Connects the socket to a remote address without blocking.

        May only be called if the socket passed to the constructor was
        not previously connected.  The address parameter is in the
        same format as for `socket.connect <socket.socket.connect>` for
        the type of socket passed to the IOStream constructor,
        e.g. an ``(ip, port)`` tuple.  Hostnames are accepted here,
        but will be resolved synchronously and block the IOLoop.
        If you have a hostname instead of an IP address, the `.TCPClient`
        class is recommended instead of calling this method directly.
        `.TCPClient` will do asynchronous DNS resolution and handle
        both IPv4 and IPv6.

        If ``callback`` is specified, it will be called with no
        arguments when the connection is completed; if not this method
        returns a `.Future` (whose result after a successful
        connection will be the stream itself).

        In SSL mode, the ``server_hostname`` parameter will be used
        for certificate validation (unless disabled in the
        ``ssl_options``) and SNI.

        Note that it is safe to call `IOStream.write
        <BaseIOStream.write>` while the connection is pending, in
        which case the data will be written as soon as the connection
        is ready.  Calling `IOStream` read methods before the socket is
        connected works on some platforms but is non-portable.

        .. versionchanged:: 4.0
            If no callback is given, returns a `.Future`.

        .. versionchanged:: 4.2
           SSL certificates are validated by default; pass
           ``ssl_options=dict(cert_reqs=ssl.CERT_NONE)`` or a
           suitably-configured `ssl.SSLContext` to the
           `SSLIOStream` constructor to disable.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.

        """
        self._connecting = True
        future = Future()  # type: Future[_IOStreamType]
        self._connect_future = typing.cast("Future[IOStream]", future)
        try:
            self.socket.connect(address)
        except BlockingIOError:
            # In non-blocking mode we expect connect() to raise an
            # exception with EINPROGRESS or EWOULDBLOCK.
            pass
        except OSError as e:
            # On freebsd, other errors such as ECONNREFUSED may be
            # returned immediately when attempting to connect to
            # localhost, so handle them the same way as an error
            # reported later in _handle_connect.
            if future is None:
                gen_log.warning("Connect error on fd %s: %s", self.socket.fileno(), e)
            self.close(exc_info=e)
            return future
        self._add_io_state(self.io_loop.WRITE)
        return future

    def start_tls(
        self,
        server_side: bool,
        ssl_options: Optional[Union[Dict[str, Any], ssl.SSLContext]] = None,
        server_hostname: Optional[str] = None,
    ) -> Awaitable["SSLIOStream"]:
        """Convert this `IOStream` to an `SSLIOStream`.

        This enables protocols that begin in clear-text mode and
        switch to SSL after some initial negotiation (such as the
        ``STARTTLS`` extension to SMTP and IMAP).

        This method cannot be used if there are outstanding reads
        or writes on the stream, or if there is any data in the
        IOStream's buffer (data in the operating system's socket
        buffer is allowed).  This means it must generally be used
        immediately after reading or writing the last clear-text
        data.  It can also be used immediately after connecting,
        before any reads or writes.

        The ``ssl_options`` argument may be either an `ssl.SSLContext`
        object or a dictionary of keyword arguments for the
        `ssl.SSLContext.wrap_socket` function.  The ``server_hostname`` argument
        will be used for certificate validation unless disabled
        in the ``ssl_options``.

        This method returns a `.Future` whose result is the new
        `SSLIOStream`.  After this method has been called,
        any other operation on the original stream is undefined.

        If a close callback is defined on this stream, it will be
        transferred to the new stream.

        .. versionadded:: 4.0

        .. versionchanged:: 4.2
           SSL certificates are validated by default; pass
           ``ssl_options=dict(cert_reqs=ssl.CERT_NONE)`` or a
           suitably-configured `ssl.SSLContext` to disable.
        """
        if (
            self._read_future
            or self._write_futures
            or self._connect_future
            or self._closed
            or self._read_buffer
            or self._write_buffer
        ):
            raise ValueError("IOStream is not idle; cannot convert to SSL")
        if ssl_options is None:
            if server_side:
                ssl_options = _server_ssl_defaults
            else:
                ssl_options = _client_ssl_defaults

        socket = self.socket
        self.io_loop.remove_handler(socket)
        self.socket = None  # type: ignore
        socket = ssl_wrap_socket(
            socket,
            ssl_options,
            server_hostname=server_hostname,
            server_side=server_side,
            do_handshake_on_connect=False,
        )
        orig_close_callback = self._close_callback
        self._close_callback = None

        future = Future()  # type: Future[SSLIOStream]
        ssl_stream = SSLIOStream(socket, ssl_options=ssl_options)
        ssl_stream.set_close_callback(orig_close_callback)
        ssl_stream._ssl_connect_future = future
        ssl_stream.max_buffer_size = self.max_buffer_size
        ssl_stream.read_chunk_size = self.read_chunk_size
        return future

    def _handle_connect(self) -> None:
        try:
            err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        except OSError as e:
            # Hurd doesn't allow SO_ERROR for loopback sockets because all
            # errors for such sockets are reported synchronously.
            if errno_from_exception(e) == errno.ENOPROTOOPT:
                err = 0
        if err != 0:
            self.error = socket.error(err, os.strerror(err))
            # IOLoop implementations may vary: some of them return
            # an error state before the socket becomes writable, so
            # in that case a connection failure would be handled by the
            # error path in _handle_events instead of here.
            if self._connect_future is None:
                gen_log.warning(
                    "Connect error on fd %s: %s",
                    self.socket.fileno(),
                    errno.errorcode[err],
                )
            self.close()
            return
        if self._connect_future is not None:
            future = self._connect_future
            self._connect_future = None
            future_set_result_unless_cancelled(future, self)
        self._connecting = False

    def set_nodelay(self, value: bool) -> None:
        if self.socket is not None and self.socket.family in (
            socket.AF_INET,
            socket.AF_INET6,
        ):
            try:
                self.socket.setsockopt(
                    socket.IPPROTO_TCP, socket.TCP_NODELAY, 1 if value else 0
                )
            except OSError as e:
                # Sometimes setsockopt will fail if the socket is closed
                # at the wrong time.  This can happen with HTTPServer
                # resetting the value to ``False`` between requests.
                if e.errno != errno.EINVAL and not self._is_connreset(e):
                    raise


class SSLIOStream(IOStream):
    """A utility class to write to and read from a non-blocking SSL socket.

    If the socket passed to the constructor is already connected,
    it should be wrapped with::

        ssl.SSLContext(...).wrap_socket(sock, do_handshake_on_connect=False, **kwargs)

    before constructing the `SSLIOStream`.  Unconnected sockets will be
    wrapped when `IOStream.connect` is finished.
    """

    socket = None  # type: ssl.SSLSocket

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """The ``ssl_options`` keyword argument may either be an
        `ssl.SSLContext` object or a dictionary of keywords arguments
        for `ssl.SSLContext.wrap_socket`
        """
        self._ssl_options = kwargs.pop("ssl_options", _client_ssl_defaults)
        super().__init__(*args, **kwargs)
        self._ssl_accepting = True
        self._handshake_reading = False
        self._handshake_writing = False
        self._server_hostname = None  # type: Optional[str]

        # If the socket is already connected, attempt to start the handshake.
        try:
            self.socket.getpeername()
        except OSError:
            pass
        else:
            # Indirectly start the handshake, which will run on the next
            # IOLoop iteration and then the real IO state will be set in
            # _handle_events.
            self._add_io_state(self.io_loop.WRITE)

    def reading(self) -> bool:
        return self._handshake_reading or super().reading()

    def writing(self) -> bool:
        return self._handshake_writing or super().writing()

    def _do_ssl_handshake(self) -> None:
        # Based on code from test_ssl.py in the python stdlib
        try:
            self._handshake_reading = False
            self._handshake_writing = False
            self.socket.do_handshake()
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._handshake_reading = True
                return
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._handshake_writing = True
                return
            elif err.args[0] in (ssl.SSL_ERROR_EOF, ssl.SSL_ERROR_ZERO_RETURN):
                return self.close(exc_info=err)
            elif err.args[0] in (ssl.SSL_ERROR_SSL, ssl.SSL_ERROR_SYSCALL):
                try:
                    peer = self.socket.getpeername()
                except Exception:
                    peer = "(not connected)"
                gen_log.warning(
                    "SSL Error on %s %s: %s", self.socket.fileno(), peer, err
                )
                return self.close(exc_info=err)
            raise
        except OSError as err:
            # Some port scans (e.g. nmap in -sT mode) have been known
            # to cause do_handshake to raise EBADF and ENOTCONN, so make
            # those errors quiet as well.
            # https://groups.google.com/forum/?fromgroups#!topic/python-tornado/ApucKJat1_0
            # Errno 0 is also possible in some cases (nc -z).
            # https://github.com/tornadoweb/tornado/issues/2504
            if self._is_connreset(err) or err.args[0] in (
                0,
                errno.EBADF,
                errno.ENOTCONN,
            ):
                return self.close(exc_info=err)
            raise
        except AttributeError as err:
            # On Linux, if the connection was reset before the call to
            # wrap_socket, do_handshake will fail with an
            # AttributeError.
            return self.close(exc_info=err)
        else:
            self._ssl_accepting = False
            # Prior to the introduction of SNI, this is where we would check
            # the server's claimed hostname.
            assert ssl.HAS_SNI
            self._finish_ssl_connect()

    def _finish_ssl_connect(self) -> None:
        if self._ssl_connect_future is not None:
            future = self._ssl_connect_future
            self._ssl_connect_future = None
            future_set_result_unless_cancelled(future, self)

    def _handle_read(self) -> None:
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super()._handle_read()

    def _handle_write(self) -> None:
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super()._handle_write()

    def connect(
        self, address: Tuple, server_hostname: Optional[str] = None
    ) -> "Future[SSLIOStream]":
        self._server_hostname = server_hostname
        # Ignore the result of connect(). If it fails,
        # wait_for_handshake will raise an error too. This is
        # necessary for the old semantics of the connect callback
        # (which takes no arguments). In 6.0 this can be refactored to
        # be a regular coroutine.
        # TODO: This is trickier than it looks, since if write()
        # is called with a connect() pending, we want the connect
        # to resolve before the write. Or do we care about this?
        # (There's a test for it, but I think in practice users
        # either wait for the connect before performing a write or
        # they don't care about the connect Future at all)
        fut = super().connect(address)
        fut.add_done_callback(lambda f: f.exception())
        return self.wait_for_handshake()

    def _handle_connect(self) -> None:
        # Call the superclass method to check for errors.
        super()._handle_connect()
        if self.closed():
            return
        # When the connection is complete, wrap the socket for SSL
        # traffic.  Note that we do this by overriding _handle_connect
        # instead of by passing a callback to super().connect because
        # user callbacks are enqueued asynchronously on the IOLoop,
        # but since _handle_events calls _handle_connect immediately
        # followed by _handle_write we need this to be synchronous.
        #
        # The IOLoop will get confused if we swap out self.socket while the
        # fd is registered, so remove it now and re-register after
        # wrap_socket().
        self.io_loop.remove_handler(self.socket)
        old_state = self._state
        assert old_state is not None
        self._state = None
        self.socket = ssl_wrap_socket(
            self.socket,
            self._ssl_options,
            server_hostname=self._server_hostname,
            do_handshake_on_connect=False,
            server_side=False,
        )
        self._add_io_state(old_state)

    def wait_for_handshake(self) -> "Future[SSLIOStream]":
        """Wait for the initial SSL handshake to complete.

        If a ``callback`` is given, it will be called with no
        arguments once the handshake is complete; otherwise this
        method returns a `.Future` which will resolve to the
        stream itself after the handshake is complete.

        Once the handshake is complete, information such as
        the peer's certificate and NPN/ALPN selections may be
        accessed on ``self.socket``.

        This method is intended for use on server-side streams
        or after using `IOStream.start_tls`; it should not be used
        with `IOStream.connect` (which already waits for the
        handshake to complete). It may only be called once per stream.

        .. versionadded:: 4.2

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           `.Future` instead.

        """
        if self._ssl_connect_future is not None:
            raise RuntimeError("Already waiting")
        future = self._ssl_connect_future = Future()
        if not self._ssl_accepting:
            self._finish_ssl_connect()
        return future

    def write_to_fd(self, data: memoryview) -> int:
        # clip buffer size at 1GB since SSL sockets only support upto 2GB
        # this change in behaviour is transparent, since the function is
        # already expected to (possibly) write less than the provided buffer
        if len(data) >> 30:
            data = memoryview(data)[: 1 << 30]
        try:
            return self.socket.send(data)  # type: ignore
        except ssl.SSLError as e:
            if e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                # In Python 3.5+, SSLSocket.send raises a WANT_WRITE error if
                # the socket is not writeable; we need to transform this into
                # an EWOULDBLOCK socket.error or a zero return value,
                # either of which will be recognized by the caller of this
                # method. Prior to Python 3.5, an unwriteable socket would
                # simply return 0 bytes written.
                return 0
            raise
        finally:
            # Avoid keeping to data, which can be a memoryview.
            # See https://github.com/tornadoweb/tornado/pull/2008
            del data

    def read_from_fd(self, buf: Union[bytearray, memoryview]) -> Optional[int]:
        try:
            if self._ssl_accepting:
                # If the handshake hasn't finished yet, there can't be anything
                # to read (attempting to read may or may not raise an exception
                # depending on the SSL version)
                return None
            # clip buffer size at 1GB since SSL sockets only support upto 2GB
            # this change in behaviour is transparent, since the function is
            # already expected to (possibly) read less than the provided buffer
            if len(buf) >> 30:
                buf = memoryview(buf)[: 1 << 30]
            try:
                return self.socket.recv_into(buf, len(buf))
            except ssl.SSLError as e:
                # SSLError is a subclass of socket.error, so this except
                # block must come first.
                if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                    return None
                else:
                    raise
            except BlockingIOError:
                return None
        finally:
            del buf

    def _is_connreset(self, e: BaseException) -> bool:
        if isinstance(e, ssl.SSLError) and e.args[0] == ssl.SSL_ERROR_EOF:
            return True
        return super()._is_connreset(e)


class PipeIOStream(BaseIOStream):
    """Pipe-based `IOStream` implementation.

    The constructor takes an integer file descriptor (such as one returned
    by `os.pipe`) rather than an open file object.  Pipes are generally
    one-way, so a `PipeIOStream` can be used for reading or writing but not
    both.

    ``PipeIOStream`` is only available on Unix-based platforms.
    """

    def __init__(self, fd: int, *args: Any, **kwargs: Any) -> None:
        self.fd = fd
        self._fio = io.FileIO(self.fd, "r+")
        if sys.platform == "win32":
            # The form and placement of this assertion is important to mypy.
            # A plain assert statement isn't recognized here. If the assertion
            # were earlier it would worry that the attributes of self aren't
            # set on windows. If it were missing it would complain about
            # the absence of the set_blocking function.
            raise AssertionError("PipeIOStream is not supported on Windows")
        os.set_blocking(fd, False)
        super().__init__(*args, **kwargs)

    def fileno(self) -> int:
        return self.fd

    def close_fd(self) -> None:
        self._fio.close()

    def write_to_fd(self, data: memoryview) -> int:
        try:
            return os.write(self.fd, data)  # type: ignore
        finally:
            # Avoid keeping to data, which can be a memoryview.
            # See https://github.com/tornadoweb/tornado/pull/2008
            del data

    def read_from_fd(self, buf: Union[bytearray, memoryview]) -> Optional[int]:
        try:
            return self._fio.readinto(buf)  # type: ignore
        except OSError as e:
            if errno_from_exception(e) == errno.EBADF:
                # If the writing half of a pipe is closed, select will
                # report it as readable but reads will fail with EBADF.
                self.close(exc_info=e)
                return None
            else:
                raise
        finally:
            del buf


def doctests() -> Any:
    import doctest

    return doctest.DocTestSuite()

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\polynomial.py ===
"""
=================================================
Power Series (:mod:`numpy.polynomial.polynomial`)
=================================================

This module provides a number of objects (mostly functions) useful for
dealing with polynomials, including a `Polynomial` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with polynomial objects is in
the docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------
.. autosummary::
   :toctree: generated/

   Polynomial

Constants
---------
.. autosummary::
   :toctree: generated/

   polydomain
   polyzero
   polyone
   polyx

Arithmetic
----------
.. autosummary::
   :toctree: generated/

   polyadd
   polysub
   polymulx
   polymul
   polydiv
   polypow
   polyval
   polyval2d
   polyval3d
   polygrid2d
   polygrid3d

Calculus
--------
.. autosummary::
   :toctree: generated/

   polyder
   polyint

Misc Functions
--------------
.. autosummary::
   :toctree: generated/

   polyfromroots
   polyroots
   polyvalfromroots
   polyvander
   polyvander2d
   polyvander3d
   polycompanion
   polyfit
   polytrim
   polyline

See Also
--------
`numpy.polynomial`

"""
__all__ = [
    'polyzero', 'polyone', 'polyx', 'polydomain', 'polyline', 'polyadd',
    'polysub', 'polymulx', 'polymul', 'polydiv', 'polypow', 'polyval',
    'polyvalfromroots', 'polyder', 'polyint', 'polyfromroots', 'polyvander',
    'polyfit', 'polytrim', 'polyroots', 'Polynomial', 'polyval2d', 'polyval3d',
    'polygrid2d', 'polygrid3d', 'polyvander2d', 'polyvander3d',
    'polycompanion']

import numpy as np
import numpy.linalg as la
from numpy.lib.array_utils import normalize_axis_index

from . import polyutils as pu
from ._polybase import ABCPolyBase

polytrim = pu.trimcoef

#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Polynomial default domain.
polydomain = np.array([-1., 1.])

# Polynomial coefficients representing zero.
polyzero = np.array([0])

# Polynomial coefficients representing one.
polyone = np.array([1])

# Polynomial coefficients representing the identity x.
polyx = np.array([0, 1])

#
# Polynomial series functions
#


def polyline(off, scl):
    """
    Returns an array representing a linear polynomial.

    Parameters
    ----------
    off, scl : scalars
        The "y-intercept" and "slope" of the line, respectively.

    Returns
    -------
    y : ndarray
        This module's representation of the linear polynomial ``off +
        scl*x``.

    See Also
    --------
    numpy.polynomial.chebyshev.chebline
    numpy.polynomial.legendre.legline
    numpy.polynomial.laguerre.lagline
    numpy.polynomial.hermite.hermline
    numpy.polynomial.hermite_e.hermeline

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> P.polyline(1, -1)
    array([ 1, -1])
    >>> P.polyval(1, P.polyline(1, -1))  # should be 0
    0.0

    """
    if scl != 0:
        return np.array([off, scl])
    else:
        return np.array([off])


def polyfromroots(roots):
    """
    Generate a monic polynomial with given roots.

    Return the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    where the :math:`r_n` are the roots specified in `roots`.  If a zero has
    multiplicity n, then it must appear in `roots` n times. For instance,
    if 2 is a root of multiplicity three and 3 is a root of multiplicity 2,
    then `roots` looks something like [2, 2, 2, 3, 3]. The roots can appear
    in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * x + ... +  x^n

    The coefficient of the last term is 1 for monic polynomials in this
    form.

    Parameters
    ----------
    roots : array_like
        Sequence containing the roots.

    Returns
    -------
    out : ndarray
        1-D array of the polynomial's coefficients If all the roots are
        real, then `out` is also real, otherwise it is complex.  (see
        Examples below).

    See Also
    --------
    numpy.polynomial.chebyshev.chebfromroots
    numpy.polynomial.legendre.legfromroots
    numpy.polynomial.laguerre.lagfromroots
    numpy.polynomial.hermite.hermfromroots
    numpy.polynomial.hermite_e.hermefromroots

    Notes
    -----
    The coefficients are determined by multiplying together linear factors
    of the form ``(x - r_i)``, i.e.

    .. math:: p(x) = (x - r_0) (x - r_1) ... (x - r_n)

    where ``n == len(roots) - 1``; note that this implies that ``1`` is always
    returned for :math:`a_n`.

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> P.polyfromroots((-1,0,1))  # x(x - 1)(x + 1) = x^3 - x
    array([ 0., -1.,  0.,  1.])
    >>> j = complex(0,1)
    >>> P.polyfromroots((-j,j))  # complex returned, though values are real
    array([1.+0.j,  0.+0.j,  1.+0.j])

    """
    return pu._fromroots(polyline, polymul, roots)


def polyadd(c1, c2):
    """
    Add one polynomial to another.

    Returns the sum of two polynomials `c1` + `c2`.  The arguments are
    sequences of coefficients from lowest order term to highest, i.e.,
    [1,2,3] represents the polynomial ``1 + 2*x + 3*x**2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of polynomial coefficients ordered from low to high.

    Returns
    -------
    out : ndarray
        The coefficient array representing their sum.

    See Also
    --------
    polysub, polymulx, polymul, polydiv, polypow

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c1 = (1, 2, 3)
    >>> c2 = (3, 2, 1)
    >>> sum = P.polyadd(c1,c2); sum
    array([4.,  4.,  4.])
    >>> P.polyval(2, sum)  # 4 + 4(2) + 4(2**2)
    28.0

    """
    return pu._add(c1, c2)


def polysub(c1, c2):
    """
    Subtract one polynomial from another.

    Returns the difference of two polynomials `c1` - `c2`.  The arguments
    are sequences of coefficients from lowest order term to highest, i.e.,
    [1,2,3] represents the polynomial ``1 + 2*x + 3*x**2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of polynomial coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of coefficients representing their difference.

    See Also
    --------
    polyadd, polymulx, polymul, polydiv, polypow

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c1 = (1, 2, 3)
    >>> c2 = (3, 2, 1)
    >>> P.polysub(c1,c2)
    array([-2.,  0.,  2.])
    >>> P.polysub(c2, c1)  # -P.polysub(c1,c2)
    array([ 2.,  0., -2.])

    """
    return pu._sub(c1, c2)


def polymulx(c):
    """Multiply a polynomial by x.

    Multiply the polynomial `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of polynomial coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    polyadd, polysub, polymul, polydiv, polypow

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = (1, 2, 3)
    >>> P.polymulx(c)
    array([0., 1., 2., 3.])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0] * 0
    prd[1:] = c
    return prd


def polymul(c1, c2):
    """
    Multiply one polynomial by another.

    Returns the product of two polynomials `c1` * `c2`.  The arguments are
    sequences of coefficients, from lowest order term to highest, e.g.,
    [1,2,3] represents the polynomial ``1 + 2*x + 3*x**2.``

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of coefficients representing a polynomial, relative to the
        "standard" basis, and ordered from lowest order term to highest.

    Returns
    -------
    out : ndarray
        Of the coefficients of their product.

    See Also
    --------
    polyadd, polysub, polymulx, polydiv, polypow

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c1 = (1, 2, 3)
    >>> c2 = (3, 2, 1)
    >>> P.polymul(c1, c2)
    array([  3.,   8.,  14.,   8.,   3.])

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    ret = np.convolve(c1, c2)
    return pu.trimseq(ret)


def polydiv(c1, c2):
    """
    Divide one polynomial by another.

    Returns the quotient-with-remainder of two polynomials `c1` / `c2`.
    The arguments are sequences of coefficients, from lowest order term
    to highest, e.g., [1,2,3] represents ``1 + 2*x + 3*x**2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of polynomial coefficients ordered from low to high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of coefficient series representing the quotient and remainder.

    See Also
    --------
    polyadd, polysub, polymulx, polymul, polypow

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c1 = (1, 2, 3)
    >>> c2 = (3, 2, 1)
    >>> P.polydiv(c1, c2)
    (array([3.]), array([-8., -4.]))
    >>> P.polydiv(c2, c1)
    (array([ 0.33333333]), array([ 2.66666667,  1.33333333]))  # may vary

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    if c2[-1] == 0:
        raise ZeroDivisionError  # FIXME: add message with details to exception

    # note: this is more efficient than `pu._div(polymul, c1, c2)`
    lc1 = len(c1)
    lc2 = len(c2)
    if lc1 < lc2:
        return c1[:1] * 0, c1
    elif lc2 == 1:
        return c1 / c2[-1], c1[:1] * 0
    else:
        dlen = lc1 - lc2
        scl = c2[-1]
        c2 = c2[:-1] / scl
        i = dlen
        j = lc1 - 1
        while i >= 0:
            c1[i:j] -= c2 * c1[j]
            i -= 1
            j -= 1
        return c1[j + 1:] / scl, pu.trimseq(c1[:j + 1])


def polypow(c, pow, maxpower=None):
    """Raise a polynomial to a power.

    Returns the polynomial `c` raised to the power `pow`. The argument
    `c` is a sequence of coefficients ordered from low to high. i.e.,
    [1,2,3] is the series  ``1 + 2*x + 3*x**2.``

    Parameters
    ----------
    c : array_like
        1-D array of array of series coefficients ordered from low to
        high degree.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Power series of power.

    See Also
    --------
    polyadd, polysub, polymulx, polymul, polydiv

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> P.polypow([1, 2, 3], 2)
    array([ 1., 4., 10., 12., 9.])

    """
    # note: this is more efficient than `pu._pow(polymul, c1, c2)`, as it
    # avoids calling `as_series` repeatedly
    return pu._pow(np.convolve, c, pow, maxpower)


def polyder(c, m=1, scl=1, axis=0):
    """
    Differentiate a polynomial.

    Returns the polynomial coefficients `c` differentiated `m` times along
    `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable).  The
    argument `c` is an array of coefficients from low to high degree along
    each axis, e.g., [1,2,3] represents the polynomial ``1 + 2*x + 3*x**2``
    while [[1,2],[1,2]] represents ``1 + 1*x + 2*y + 2*x*y`` if axis=0 is
    ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of polynomial coefficients. If c is multidimensional the
        different axis correspond to different variables with the degree
        in each axis given by the corresponding index.
    m : int, optional
        Number of derivatives taken, must be non-negative. (Default: 1)
    scl : scalar, optional
        Each differentiation is multiplied by `scl`.  The end result is
        multiplication by ``scl**m``.  This is for use in a linear change
        of variable. (Default: 1)
    axis : int, optional
        Axis over which the derivative is taken. (Default: 0).

    Returns
    -------
    der : ndarray
        Polynomial coefficients of the derivative.

    See Also
    --------
    polyint

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = (1, 2, 3, 4)
    >>> P.polyder(c)  # (d/dx)(c)
    array([  2.,   6.,  12.])
    >>> P.polyder(c, 3)  # (d**3/dx**3)(c)
    array([24.])
    >>> P.polyder(c, scl=-1)  # (d/d(-x))(c)
    array([ -2.,  -6., -12.])
    >>> P.polyder(c, 2, -1)  # (d**2/d(-x)**2)(c)
    array([  6.,  24.])

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        # astype fails with NA
        c = c + 0.0
    cdt = c.dtype
    cnt = pu._as_int(m, "the order of derivation")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of derivation must be non-negative")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    n = len(c)
    if cnt >= n:
        c = c[:1] * 0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=cdt)
            for j in range(n, 0, -1):
                der[j - 1] = j * c[j]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def polyint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a polynomial.

    Returns the polynomial coefficients `c` integrated `m` times from
    `lbnd` along `axis`.  At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.) The argument `c` is an array of
    coefficients, from low to high degree along each axis, e.g., [1,2,3]
    represents the polynomial ``1 + 2*x + 3*x**2`` while [[1,2],[1,2]]
    represents ``1 + 1*x + 2*y + 2*x*y`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        1-D array of polynomial coefficients, ordered from low to high.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at zero
        is the first value in the list, the value of the second integral
        at zero is the second value, etc.  If ``k == []`` (the default),
        all constants are set to zero.  If ``m == 1``, a single scalar can
        be given instead of a list.
    lbnd : scalar, optional
        The lower bound of the integral. (Default: 0)
    scl : scalar, optional
        Following each integration the result is *multiplied* by `scl`
        before the integration constant is added. (Default: 1)
    axis : int, optional
        Axis over which the integral is taken. (Default: 0).

    Returns
    -------
    S : ndarray
        Coefficient array of the integral.

    Raises
    ------
    ValueError
        If ``m < 1``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    polyder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.  Why
    is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`. Then
    :math:`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a` - perhaps not what one would have first thought.

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = (1, 2, 3)
    >>> P.polyint(c)  # should return array([0, 1, 1, 1])
    array([0.,  1.,  1.,  1.])
    >>> P.polyint(c, 3)  # should return array([0, 0, 0, 1/6, 1/12, 1/20])
     array([ 0.        ,  0.        ,  0.        ,  0.16666667,  0.08333333, # may vary
             0.05      ])
    >>> P.polyint(c, k=3)  # should return array([3, 1, 1, 1])
    array([3.,  1.,  1.,  1.])
    >>> P.polyint(c,lbnd=-2)  # should return array([6, 1, 1, 1])
    array([6.,  1.,  1.,  1.])
    >>> P.polyint(c,scl=-2)  # should return array([0, -2, -2, -2])
    array([ 0., -2., -2., -2.])

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        # astype doesn't preserve mask attribute.
        c = c + 0.0
    cdt = c.dtype
    if not np.iterable(k):
        k = [k]
    cnt = pu._as_int(m, "the order of integration")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of integration must be non-negative")
    if len(k) > cnt:
        raise ValueError("Too many integration constants")
    if np.ndim(lbnd) != 0:
        raise ValueError("lbnd must be a scalar.")
    if np.ndim(scl) != 0:
        raise ValueError("scl must be a scalar.")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    k = list(k) + [0] * (cnt - len(k))
    c = np.moveaxis(c, iaxis, 0)
    for i in range(cnt):
        n = len(c)
        c *= scl
        if n == 1 and np.all(c[0] == 0):
            c[0] += k[i]
        else:
            tmp = np.empty((n + 1,) + c.shape[1:], dtype=cdt)
            tmp[0] = c[0] * 0
            tmp[1] = c[0]
            for j in range(1, n):
                tmp[j + 1] = c[j] / (j + 1)
            tmp[0] += k[i] - polyval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def polyval(x, c, tensor=True):
    """
    Evaluate a polynomial at points x.

    If `c` is of length ``n + 1``, this function returns the value

    .. math:: p(x) = c_0 + c_1 * x + ... + c_n * x^n

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `c`.

    If `c` is a 1-D array, then ``p(x)`` will have the same shape as `x`.  If
    `c` is multidimensional, then the shape of the result depends on the
    value of `tensor`. If `tensor` is true the shape will be c.shape[1:] +
    x.shape. If `tensor` is false the shape will be c.shape[1:]. Note that
    scalars have shape (,).

    Trailing zeros in the coefficients will be used in the evaluation, so
    they should be avoided if efficiency is a concern.

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        with themselves and with the elements of `c`.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree n are contained in c[n]. If `c` is multidimensional the
        remaining indices enumerate multiple polynomials. In the two
        dimensional case the coefficients may be thought of as stored in
        the columns of `c`.
    tensor : boolean, optional
        If True, the shape of the coefficient array is extended with ones
        on the right, one for each dimension of `x`. Scalars have dimension 0
        for this action. The result is that every column of coefficients in
        `c` is evaluated for every element of `x`. If False, `x` is broadcast
        over the columns of `c` for the evaluation.  This keyword is useful
        when `c` is multidimensional. The default value is True.

    Returns
    -------
    values : ndarray, compatible object
        The shape of the returned array is described above.

    See Also
    --------
    polyval2d, polygrid2d, polyval3d, polygrid3d

    Notes
    -----
    The evaluation uses Horner's method.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.polynomial import polyval
    >>> polyval(1, [1,2,3])
    6.0
    >>> a = np.arange(4).reshape(2,2)
    >>> a
    array([[0, 1],
           [2, 3]])
    >>> polyval(a, [1, 2, 3])
    array([[ 1.,   6.],
           [17.,  34.]])
    >>> coef = np.arange(4).reshape(2, 2)  # multidimensional coefficients
    >>> coef
    array([[0, 1],
           [2, 3]])
    >>> polyval([1, 2], coef, tensor=True)
    array([[2.,  4.],
           [4.,  7.]])
    >>> polyval([1, 2], coef, tensor=False)
    array([2.,  7.])

    """
    c = np.array(c, ndmin=1, copy=None)
    if c.dtype.char in '?bBhHiIlLqQpP':
        # astype fails with NA
        c = c + 0.0
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray) and tensor:
        c = c.reshape(c.shape + (1,) * x.ndim)

    c0 = c[-1] + x * 0
    for i in range(2, len(c) + 1):
        c0 = c[-i] + c0 * x
    return c0


def polyvalfromroots(x, r, tensor=True):
    """
    Evaluate a polynomial specified by its roots at points x.

    If `r` is of length ``N``, this function returns the value

    .. math:: p(x) = \\prod_{n=1}^{N} (x - r_n)

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `r`.

    If `r` is a 1-D array, then ``p(x)`` will have the same shape as `x`.  If `r`
    is multidimensional, then the shape of the result depends on the value of
    `tensor`. If `tensor` is ``True`` the shape will be r.shape[1:] + x.shape;
    that is, each polynomial is evaluated at every value of `x`. If `tensor` is
    ``False``, the shape will be r.shape[1:]; that is, each polynomial is
    evaluated only for the corresponding broadcast value of `x`. Note that
    scalars have shape (,).

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        with themselves and with the elements of `r`.
    r : array_like
        Array of roots. If `r` is multidimensional the first index is the
        root index, while the remaining indices enumerate multiple
        polynomials. For instance, in the two dimensional case the roots
        of each polynomial may be thought of as stored in the columns of `r`.
    tensor : boolean, optional
        If True, the shape of the roots array is extended with ones on the
        right, one for each dimension of `x`. Scalars have dimension 0 for this
        action. The result is that every column of coefficients in `r` is
        evaluated for every element of `x`. If False, `x` is broadcast over the
        columns of `r` for the evaluation.  This keyword is useful when `r` is
        multidimensional. The default value is True.

    Returns
    -------
    values : ndarray, compatible object
        The shape of the returned array is described above.

    See Also
    --------
    polyroots, polyfromroots, polyval

    Examples
    --------
    >>> from numpy.polynomial.polynomial import polyvalfromroots
    >>> polyvalfromroots(1, [1, 2, 3])
    0.0
    >>> a = np.arange(4).reshape(2, 2)
    >>> a
    array([[0, 1],
           [2, 3]])
    >>> polyvalfromroots(a, [-1, 0, 1])
    array([[-0.,   0.],
           [ 6.,  24.]])
    >>> r = np.arange(-2, 2).reshape(2,2)  # multidimensional coefficients
    >>> r # each column of r defines one polynomial
    array([[-2, -1],
           [ 0,  1]])
    >>> b = [-2, 1]
    >>> polyvalfromroots(b, r, tensor=True)
    array([[-0.,  3.],
           [ 3., 0.]])
    >>> polyvalfromroots(b, r, tensor=False)
    array([-0.,  0.])

    """
    r = np.array(r, ndmin=1, copy=None)
    if r.dtype.char in '?bBhHiIlLqQpP':
        r = r.astype(np.double)
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray):
        if tensor:
            r = r.reshape(r.shape + (1,) * x.ndim)
        elif x.ndim >= r.ndim:
            raise ValueError("x.ndim must be < r.ndim when tensor == False")
    return np.prod(x - r, axis=0)


def polyval2d(x, y, c):
    """
    Evaluate a 2-D polynomial at points (x, y).

    This function returns the value

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * x^i * y^j

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars and they
    must have the same shape after conversion. In either case, either `x`
    and `y` or their elements must support multiplication and addition both
    with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points ``(x, y)``,
        where `x` and `y` must have the same shape. If `x` or `y` is a list
        or tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term
        of multi-degree i,j is contained in ``c[i,j]``. If `c` has
        dimension greater than two the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points formed with
        pairs of corresponding values from `x` and `y`.

    See Also
    --------
    polyval, polygrid2d, polyval3d, polygrid3d

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = ((1, 2, 3), (4, 5, 6))
    >>> P.polyval2d(1, 1, c)
    21.0

    """
    return pu._valnd(polyval, c, x, y)


def polygrid2d(x, y, c):
    """
    Evaluate a 2-D polynomial on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * a^i * b^j

    where the points ``(a, b)`` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape + y.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    polyval, polyval2d, polyval3d, polygrid3d

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = ((1, 2, 3), (4, 5, 6))
    >>> P.polygrid2d([0, 1], [0, 1], c)
    array([[ 1.,  6.],
           [ 5., 21.]])

    """
    return pu._gridnd(polyval, c, x, y)


def polyval3d(x, y, z, c):
    """
    Evaluate a 3-D polynomial at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * x^i * y^j * z^k

    The parameters `x`, `y`, and `z` are converted to arrays only if
    they are tuples or a lists, otherwise they are treated as a scalars and
    they must have the same shape after conversion. In either case, either
    `x`, `y`, and `z` or their elements must support multiplication and
    addition both with themselves and with the elements of `c`.

    If `c` has fewer than 3 dimensions, ones are implicitly appended to its
    shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible object
        The three dimensional series is evaluated at the points
        ``(x, y, z)``, where `x`, `y`, and `z` must have the same shape.  If
        any of `x`, `y`, or `z` is a list or tuple, it is first converted
        to an ndarray, otherwise it is left unchanged and if it isn't an
        ndarray it is  treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j,k is contained in ``c[i,j,k]``. If `c` has dimension
        greater than 3 the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the multidimensional polynomial on points formed with
        triples of corresponding values from `x`, `y`, and `z`.

    See Also
    --------
    polyval, polyval2d, polygrid2d, polygrid3d

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = ((1, 2, 3), (4, 5, 6), (7, 8, 9))
    >>> P.polyval3d(1, 1, 1, c)
    45.0

    """
    return pu._valnd(polyval, c, x, y, z)


def polygrid3d(x, y, z, c):
    """
    Evaluate a 3-D polynomial on the Cartesian product of x, y and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * a^i * b^j * c^k

    where the points ``(a, b, c)`` consist of all triples formed by taking
    `a` from `x`, `b` from `y`, and `c` from `z`. The resulting points form
    a grid with `x` in the first dimension, `y` in the second, and `z` in
    the third.

    The parameters `x`, `y`, and `z` are converted to arrays only if they
    are tuples or a lists, otherwise they are treated as a scalars. In
    either case, either `x`, `y`, and `z` or their elements must support
    multiplication and addition both with themselves and with the elements
    of `c`.

    If `c` has fewer than three dimensions, ones are implicitly appended to
    its shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape + y.shape + z.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible objects
        The three dimensional series is evaluated at the points in the
        Cartesian product of `x`, `y`, and `z`.  If `x`, `y`, or `z` is a
        list or tuple, it is first converted to an ndarray, otherwise it is
        left unchanged and, if it isn't an ndarray, it is treated as a
        scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    polyval, polyval2d, polygrid2d, polyval3d

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = ((1, 2, 3), (4, 5, 6), (7, 8, 9))
    >>> P.polygrid3d([0, 1], [0, 1], [0, 1], c)
    array([[ 1., 13.],
           [ 6., 51.]])

    """
    return pu._gridnd(polyval, c, x, y, z)


def polyvander(x, deg):
    """Vandermonde matrix of given degree.

    Returns the Vandermonde matrix of degree `deg` and sample points
    `x`. The Vandermonde matrix is defined by

    .. math:: V[..., i] = x^i,

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the power of `x`.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    matrix ``V = polyvander(x, n)``, then ``np.dot(V, c)`` and
    ``polyval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of polynomials of the same degree and sample points.

    Parameters
    ----------
    x : array_like
        Array of points. The dtype is converted to float64 or complex128
        depending on whether any of the elements are complex. If `x` is
        scalar it is converted to a 1-D array.
    deg : int
        Degree of the resulting matrix.

    Returns
    -------
    vander : ndarray.
        The Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where the last index is the power of `x`.
        The dtype will be the same as the converted `x`.

    See Also
    --------
    polyvander2d, polyvander3d

    Examples
    --------
    The Vandermonde matrix of degree ``deg = 5`` and sample points
    ``x = [-1, 2, 3]`` contains the element-wise powers of `x`
    from 0 to 5 as its columns.

    >>> from numpy.polynomial import polynomial as P
    >>> x, deg = [-1, 2, 3], 5
    >>> P.polyvander(x=x, deg=deg)
    array([[  1.,  -1.,   1.,  -1.,   1.,  -1.],
           [  1.,   2.,   4.,   8.,  16.,  32.],
           [  1.,   3.,   9.,  27.,  81., 243.]])

    """
    ideg = pu._as_int(deg, "deg")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=None, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    v[0] = x * 0 + 1
    if ideg > 0:
        v[1] = x
        for i in range(2, ideg + 1):
            v[i] = v[i - 1] * x
    return np.moveaxis(v, 0, -1)


def polyvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = x^i * y^j,

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the powers of
    `x` and `y`.

    If ``V = polyvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``polyval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D polynomials
    of the same degrees and sample points.

    Parameters
    ----------
    x, y : array_like
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to
        1-D arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg].

    Returns
    -------
    vander2d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg([1]+1)`.  The dtype will be the same
        as the converted `x` and `y`.

    See Also
    --------
    polyvander, polyvander3d, polyval2d, polyval3d

    Examples
    --------
    >>> import numpy as np

    The 2-D pseudo-Vandermonde matrix of degree ``[1, 2]`` and sample
    points ``x = [-1, 2]`` and ``y = [1, 3]`` is as follows:

    >>> from numpy.polynomial import polynomial as P
    >>> x = np.array([-1, 2])
    >>> y = np.array([1, 3])
    >>> m, n = 1, 2
    >>> deg = np.array([m, n])
    >>> V = P.polyvander2d(x=x, y=y, deg=deg)
    >>> V
    array([[ 1.,  1.,  1., -1., -1., -1.],
           [ 1.,  3.,  9.,  2.,  6., 18.]])

    We can verify the columns for any ``0 <= i <= m`` and ``0 <= j <= n``:

    >>> i, j = 0, 1
    >>> V[:, (deg[1]+1)*i + j] == x**i * y**j
    array([ True,  True])

    The (1D) Vandermonde matrix of sample points ``x`` and degree ``m`` is a
    special case of the (2D) pseudo-Vandermonde matrix with ``y`` points all
    zero and degree ``[m, 0]``.

    >>> P.polyvander2d(x=x, y=0*x, deg=(m, 0)) == P.polyvander(x=x, deg=m)
    array([[ True,  True],
           [ True,  True]])

    """
    return pu._vander_nd_flat((polyvander, polyvander), (x, y), deg)


def polyvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = x^i * y^j * z^k,

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the powers of `x`, `y`, and `z`.

    If ``V = polyvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and  ``np.dot(V, c.flat)`` and ``polyval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D polynomials
    of the same degrees and sample points.

    Parameters
    ----------
    x, y, z : array_like
        Arrays of point coordinates, all of the same shape. The dtypes will
        be converted to either float64 or complex128 depending on whether
        any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg, z_deg].

    Returns
    -------
    vander3d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg([1]+1)*(deg[2]+1)`.  The dtype will
        be the same as the converted `x`, `y`, and `z`.

    See Also
    --------
    polyvander, polyvander3d, polyval2d, polyval3d

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial import polynomial as P
    >>> x = np.asarray([-1, 2, 1])
    >>> y = np.asarray([1, -2, -3])
    >>> z = np.asarray([2, 2, 5])
    >>> l, m, n = [2, 2, 1]
    >>> deg = [l, m, n]
    >>> V = P.polyvander3d(x=x, y=y, z=z, deg=deg)
    >>> V
    array([[  1.,   2.,   1.,   2.,   1.,   2.,  -1.,  -2.,  -1.,
             -2.,  -1.,  -2.,   1.,   2.,   1.,   2.,   1.,   2.],
           [  1.,   2.,  -2.,  -4.,   4.,   8.,   2.,   4.,  -4.,
             -8.,   8.,  16.,   4.,   8.,  -8., -16.,  16.,  32.],
           [  1.,   5.,  -3., -15.,   9.,  45.,   1.,   5.,  -3.,
            -15.,   9.,  45.,   1.,   5.,  -3., -15.,   9.,  45.]])

    We can verify the columns for any ``0 <= i <= l``, ``0 <= j <= m``,
    and ``0 <= k <= n``

    >>> i, j, k = 2, 1, 0
    >>> V[:, (m+1)*(n+1)*i + (n+1)*j + k] == x**i * y**j * z**k
    array([ True,  True,  True])

    """
    return pu._vander_nd_flat((polyvander, polyvander, polyvander), (x, y, z), deg)


def polyfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least-squares fit of a polynomial to data.

    Return the coefficients of a polynomial of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * x + ... + c_n * x^n,

    where `n` is `deg`.

    Parameters
    ----------
    x : array_like, shape (`M`,)
        x-coordinates of the `M` sample (data) points ``(x[i], y[i])``.
    y : array_like, shape (`M`,) or (`M`, `K`)
        y-coordinates of the sample points.  Several sets of sample points
        sharing the same x-coordinates can be (independently) fit with one
        call to `polyfit` by passing in for `y` a 2-D array that contains
        one data set per column.
    deg : int or 1-D array_like
        Degree(s) of the fitting polynomials. If `deg` is a single integer
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit.  Singular values smaller
        than `rcond`, relative to the largest singular value, will be
        ignored.  The default value is ``len(x)*eps``, where `eps` is the
        relative precision of the platform's float type, about 2e-16 in
        most cases.
    full : bool, optional
        Switch determining the nature of the return value.  When ``False``
        (the default) just the coefficients are returned; when ``True``,
        diagnostic information from the singular value decomposition (used
        to solve the fit's matrix equation) is also returned.
    w : array_like, shape (`M`,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.

    Returns
    -------
    coef : ndarray, shape (`deg` + 1,) or (`deg` + 1, `K`)
        Polynomial coefficients ordered from low to high.  If `y` was 2-D,
        the coefficients in column `k` of `coef` represent the polynomial
        fit to the data in `y`'s `k`-th column.

    [residuals, rank, singular_values, rcond] : list
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the numerical rank of the scaled Vandermonde matrix
        - singular_values -- singular values of the scaled Vandermonde matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    Raises
    ------
    RankWarning
        Raised if the matrix in the least-squares fit is rank deficient.
        The warning is only raised if ``full == False``.  The warnings can
        be turned off by:

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    numpy.polynomial.chebyshev.chebfit
    numpy.polynomial.legendre.legfit
    numpy.polynomial.laguerre.lagfit
    numpy.polynomial.hermite.hermfit
    numpy.polynomial.hermite_e.hermefit
    polyval : Evaluates a polynomial.
    polyvander : Vandermonde matrix for powers.
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the polynomial `p` that minimizes
    the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where the :math:`w_j` are the weights. This problem is solved by
    setting up the (typically) over-determined matrix equation:

    .. math:: V(x) * c = w * y,

    where `V` is the weighted pseudo Vandermonde matrix of `x`, `c` are the
    coefficients to be solved for, `w` are the weights, and `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of `V`.

    If some of the singular values of `V` are so small that they are
    neglected (and `full` == ``False``), a `~exceptions.RankWarning` will be
    raised.  This means that the coefficient values may be poorly determined.
    Fitting to a lower order polynomial will usually get rid of the warning
    (but may not be what you want, of course; if you have independent
    reason(s) for choosing the degree which isn't working, you may have to:
    a) reconsider those reasons, and/or b) reconsider the quality of your
    data).  The `rcond` parameter can also be set to a value smaller than
    its default, but the resulting fit may be spurious and have large
    contributions from roundoff error.

    Polynomial fits using double precision tend to "fail" at about
    (polynomial) degree 20. Fits using Chebyshev or Legendre series are
    generally better conditioned, but much can still depend on the
    distribution of the sample points and the smoothness of the data.  If
    the quality of the fit is inadequate, splines may be a good
    alternative.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial import polynomial as P
    >>> x = np.linspace(-1,1,51)  # x "data": [-1, -0.96, ..., 0.96, 1]
    >>> rng = np.random.default_rng()
    >>> err = rng.normal(size=len(x))
    >>> y = x**3 - x + err  # x^3 - x + Gaussian noise
    >>> c, stats = P.polyfit(x,y,3,full=True)
    >>> c # c[0], c[1] approx. -1, c[2] should be approx. 0, c[3] approx. 1
    array([ 0.23111996, -1.02785049, -0.2241444 ,  1.08405657]) # may vary
    >>> stats # note the large SSR, explaining the rather poor results
    [array([48.312088]),                                        # may vary
     4,
     array([1.38446749, 1.32119158, 0.50443316, 0.28853036]),
     1.1324274851176597e-14]

    Same thing without the added noise

    >>> y = x**3 - x
    >>> c, stats = P.polyfit(x,y,3,full=True)
    >>> c # c[0], c[1] ~= -1, c[2] should be "very close to 0", c[3] ~= 1
    array([-6.73496154e-17, -1.00000000e+00,  0.00000000e+00,  1.00000000e+00])
    >>> stats # note the minuscule SSR
    [array([8.79579319e-31]),
     np.int32(4),
     array([1.38446749, 1.32119158, 0.50443316, 0.28853036]),
     1.1324274851176597e-14]

    """
    return pu._fit(polyvander, x, y, deg, rcond, full, w)


def polycompanion(c):
    """
    Return the companion matrix of c.

    The companion matrix for power series cannot be made symmetric by
    scaling the basis, so this function differs from those for the
    orthogonal polynomials.

    Parameters
    ----------
    c : array_like
        1-D array of polynomial coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Companion matrix of dimensions (deg, deg).

    Examples
    --------
    >>> from numpy.polynomial import polynomial as P
    >>> c = (1, 2, 3)
    >>> P.polycompanion(c)
    array([[ 0.        , -0.33333333],
           [ 1.        , -0.66666667]])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[-c[0] / c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    bot = mat.reshape(-1)[n::n + 1]
    bot[...] = 1
    mat[:, -1] -= c[:-1] / c[-1]
    return mat


def polyroots(c):
    """
    Compute the roots of a polynomial.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * x^i.

    Parameters
    ----------
    c : 1-D array_like
        1-D array of polynomial coefficients.

    Returns
    -------
    out : ndarray
        Array of the roots of the polynomial. If all the roots are real,
        then `out` is also real, otherwise it is complex.

    See Also
    --------
    numpy.polynomial.chebyshev.chebroots
    numpy.polynomial.legendre.legroots
    numpy.polynomial.laguerre.lagroots
    numpy.polynomial.hermite.hermroots
    numpy.polynomial.hermite_e.hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the power series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    Examples
    --------
    >>> import numpy.polynomial.polynomial as poly
    >>> poly.polyroots(poly.polyfromroots((-1,0,1)))
    array([-1.,  0.,  1.])
    >>> poly.polyroots(poly.polyfromroots((-1,0,1))).dtype
    dtype('float64')
    >>> j = complex(0,1)
    >>> poly.polyroots(poly.polyfromroots((-j,0,j)))
    array([  0.00000000e+00+0.j,   0.00000000e+00+1.j,   2.77555756e-17-1.j])  # may vary

    """  # noqa: E501
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-c[0] / c[1]])

    m = polycompanion(c)
    r = la.eigvals(m)
    r.sort()
    return r


#
# polynomial class
#

class Polynomial(ABCPolyBase):
    """A power series class.

    The Polynomial class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        Polynomial coefficients in order of increasing degree, i.e.,
        ``(1, 2, 3)`` give ``1 + 2*x + 3*x**2``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [-1., 1.].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [-1., 1.].
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    """
    # Virtual Functions
    _add = staticmethod(polyadd)
    _sub = staticmethod(polysub)
    _mul = staticmethod(polymul)
    _div = staticmethod(polydiv)
    _pow = staticmethod(polypow)
    _val = staticmethod(polyval)
    _int = staticmethod(polyint)
    _der = staticmethod(polyder)
    _fit = staticmethod(polyfit)
    _line = staticmethod(polyline)
    _roots = staticmethod(polyroots)
    _fromroots = staticmethod(polyfromroots)

    # Virtual properties
    domain = np.array(polydomain)
    window = np.array(polydomain)
    basis_name = None

    @classmethod
    def _str_term_unicode(cls, i, arg_str):
        if i == '1':
            return f"·{arg_str}"
        else:
            return f"·{arg_str}{i.translate(cls._superscript_mapping)}"

    @staticmethod
    def _str_term_ascii(i, arg_str):
        if i == '1':
            return f" {arg_str}"
        else:
            return f" {arg_str}**{i}"

    @staticmethod
    def _repr_latex_term(i, arg_str, needs_parens):
        if needs_parens:
            arg_str = rf"\left({arg_str}\right)"
        if i == 0:
            return '1'
        elif i == 1:
            return arg_str
        else:
            return f"{arg_str}^{{{i}}}"

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\scripting.py ===
"""
    pygments.lexers.scripting
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for scripting and embedded languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, default, combined, \
    words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error, Whitespace, Other
from pygments.util import get_bool_opt, get_list_opt

__all__ = ['LuaLexer', 'LuauLexer', 'MoonScriptLexer', 'ChaiscriptLexer', 'LSLLexer',
           'AppleScriptLexer', 'RexxLexer', 'MOOCodeLexer', 'HybrisLexer',
           'EasytrieveLexer', 'JclLexer', 'MiniScriptLexer']


def all_lua_builtins():
    from pygments.lexers._lua_builtins import MODULES
    return [w for values in MODULES.values() for w in values]

class LuaLexer(RegexLexer):
    """
    For Lua source code.

    Additional options accepted:

    `func_name_highlighting`
        If given and ``True``, highlight builtin function names
        (default: ``True``).
    `disabled_modules`
        If given, must be a list of module names whose function names
        should not be highlighted. By default all modules are highlighted.

        To get a list of allowed modules have a look into the
        `_lua_builtins` module:

        .. sourcecode:: pycon

            >>> from pygments.lexers._lua_builtins import MODULES
            >>> MODULES.keys()
            ['string', 'coroutine', 'modules', 'io', 'basic', ...]
    """

    name = 'Lua'
    url = 'https://www.lua.org/'
    aliases = ['lua']
    filenames = ['*.lua', '*.wlua']
    mimetypes = ['text/x-lua', 'application/x-lua']
    version_added = ''

    _comment_multiline = r'(?:--\[(?P<level>=*)\[[\w\W]*?\](?P=level)\])'
    _comment_single = r'(?:--.*$)'
    _space = r'(?:\s+(?!\s))'
    _s = rf'(?:{_comment_multiline}|{_comment_single}|{_space})'
    _name = r'(?:[^\W\d]\w*)'

    tokens = {
        'root': [
            # Lua allows a file to start with a shebang.
            (r'#!.*', Comment.Preproc),
            default('base'),
        ],
        'ws': [
            (_comment_multiline, Comment.Multiline),
            (_comment_single, Comment.Single),
            (_space, Whitespace),
        ],
        'base': [
            include('ws'),

            (r'(?i)0x[\da-f]*(\.[\da-f]*)?(p[+-]?\d+)?', Number.Hex),
            (r'(?i)(\d*\.\d+|\d+\.\d*)(e[+-]?\d+)?', Number.Float),
            (r'(?i)\d+e[+-]?\d+', Number.Float),
            (r'\d+', Number.Integer),

            # multiline strings
            (r'(?s)\[(=*)\[.*?\]\1\]', String),

            (r'::', Punctuation, 'label'),
            (r'\.{3}', Punctuation),
            (r'[=<>|~&+\-*/%#^]+|\.\.', Operator),
            (r'[\[\]{}().,:;]+', Punctuation),
            (r'(and|or|not)\b', Operator.Word),

            (words([
                'break', 'do', 'else', 'elseif', 'end', 'for', 'if', 'in',
                'repeat', 'return', 'then', 'until', 'while'
            ], suffix=r'\b'), Keyword.Reserved),
            (r'goto\b', Keyword.Reserved, 'goto'),
            (r'(local)\b', Keyword.Declaration),
            (r'(true|false|nil)\b', Keyword.Constant),

            (r'(function)\b', Keyword.Reserved, 'funcname'),

            (words(all_lua_builtins(), suffix=r"\b"), Name.Builtin),
            (fr'[A-Za-z_]\w*(?={_s}*[.:])', Name.Variable, 'varname'),
            (fr'[A-Za-z_]\w*(?={_s}*\()', Name.Function),
            (r'[A-Za-z_]\w*', Name.Variable),

            ("'", String.Single, combined('stringescape', 'sqs')),
            ('"', String.Double, combined('stringescape', 'dqs'))
        ],

        'varname': [
            include('ws'),
            (r'\.\.', Operator, '#pop'),
            (r'[.:]', Punctuation),
            (rf'{_name}(?={_s}*[.:])', Name.Property),
            (rf'{_name}(?={_s}*\()', Name.Function, '#pop'),
            (_name, Name.Property, '#pop'),
        ],

        'funcname': [
            include('ws'),
            (r'[.:]', Punctuation),
            (rf'{_name}(?={_s}*[.:])', Name.Class),
            (_name, Name.Function, '#pop'),
            # inline function
            (r'\(', Punctuation, '#pop'),
        ],

        'goto': [
            include('ws'),
            (_name, Name.Label, '#pop'),
        ],

        'label': [
            include('ws'),
            (r'::', Punctuation, '#pop'),
            (_name, Name.Label),
        ],

        'stringescape': [
            (r'\\([abfnrtv\\"\']|[\r\n]{1,2}|z\s*|x[0-9a-fA-F]{2}|\d{1,3}|'
             r'u\{[0-9a-fA-F]+\})', String.Escape),
        ],

        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"[^\\']+", String.Single),
        ],

        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'[^\\"]+', String.Double),
        ]
    }

    def __init__(self, **options):
        self.func_name_highlighting = get_bool_opt(
            options, 'func_name_highlighting', True)
        self.disabled_modules = get_list_opt(options, 'disabled_modules', [])

        self._functions = set()
        if self.func_name_highlighting:
            from pygments.lexers._lua_builtins import MODULES
            for mod, func in MODULES.items():
                if mod not in self.disabled_modules:
                    self._functions.update(func)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name.Builtin and value not in self._functions:
                if '.' in value:
                    a, b = value.split('.')
                    yield index, Name, a
                    yield index + len(a), Punctuation, '.'
                    yield index + len(a) + 1, Name, b
                else:
                    yield index, Name, value
                continue
            yield index, token, value

def _luau_make_expression(should_pop, _s):
    temp_list = [
        (r'0[xX][\da-fA-F_]*', Number.Hex, '#pop'),
        (r'0[bB][\d_]*', Number.Bin, '#pop'),
        (r'\.?\d[\d_]*(?:\.[\d_]*)?(?:[eE][+-]?[\d_]+)?', Number.Float, '#pop'),

        (words((
            'true', 'false', 'nil'
        ), suffix=r'\b'), Keyword.Constant, '#pop'),

        (r'\[(=*)\[[.\n]*?\]\1\]', String, '#pop'),

        (r'(\.)([a-zA-Z_]\w*)(?=%s*[({"\'])', bygroups(Punctuation, Name.Function), '#pop'),
        (r'(\.)([a-zA-Z_]\w*)', bygroups(Punctuation, Name.Variable), '#pop'),

        (rf'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*(?={_s}*[({{"\'])', Name.Other, '#pop'),
        (r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*', Name, '#pop'),
    ]
    if should_pop:
        return temp_list
    return [entry[:2] for entry in temp_list]

def _luau_make_expression_special(should_pop):
    temp_list = [
        (r'\{', Punctuation, ('#pop', 'closing_brace_base', 'expression')),
        (r'\(', Punctuation, ('#pop', 'closing_parenthesis_base', 'expression')),

        (r'::?', Punctuation, ('#pop', 'type_end', 'type_start')),

        (r"'", String.Single, ('#pop', 'string_single')),
        (r'"', String.Double, ('#pop', 'string_double')),
        (r'`', String.Backtick, ('#pop', 'string_interpolated')),
    ]
    if should_pop:
        return temp_list
    return [(entry[0], entry[1], entry[2][1:]) for entry in temp_list]

class LuauLexer(RegexLexer):
    """
    For Luau source code.

    Additional options accepted:

    `include_luau_builtins`
        If given and ``True``, automatically highlight Luau builtins
        (default: ``True``).
    `include_roblox_builtins`
        If given and ``True``, automatically highlight Roblox-specific builtins
        (default: ``False``).
    `additional_builtins`
        If given, must be a list of additional builtins to highlight.
    `disabled_builtins`
        If given, must be a list of builtins that will not be highlighted.
    """

    name = 'Luau'
    url = 'https://luau-lang.org/'
    aliases = ['luau']
    filenames = ['*.luau']
    version_added = '2.18'

    _comment_multiline = r'(?:--\[(?P<level>=*)\[[\w\W]*?\](?P=level)\])'
    _comment_single = r'(?:--.*$)'
    _s = r'(?:{}|{}|{})'.format(_comment_multiline, _comment_single, r'\s+')

    tokens = {
        'root': [
            (r'#!.*', Comment.Hashbang, 'base'),
            default('base'),
        ],

        'ws': [
            (_comment_multiline, Comment.Multiline),
            (_comment_single, Comment.Single),
            (r'\s+', Whitespace),
        ],

        'base': [
            include('ws'),

            *_luau_make_expression_special(False),
            (r'\.\.\.', Punctuation),

            (rf'type\b(?={_s}+[a-zA-Z_])', Keyword.Reserved, 'type_declaration'),
            (rf'export\b(?={_s}+[a-zA-Z_])', Keyword.Reserved),

            (r'(?:\.\.|//|[+\-*\/%^<>=])=?', Operator, 'expression'),
            (r'~=', Operator, 'expression'),

            (words((
                'and', 'or', 'not'
            ), suffix=r'\b'), Operator.Word, 'expression'),

            (words((
                'elseif', 'for', 'if', 'in', 'repeat', 'return', 'until',
                'while'), suffix=r'\b'), Keyword.Reserved, 'expression'),
            (r'local\b', Keyword.Declaration, 'expression'),

            (r'function\b', Keyword.Reserved, ('expression', 'func_name')),

            (r'[\])};]+', Punctuation),

            include('expression_static'),
            *_luau_make_expression(False, _s),

            (r'[\[.,]', Punctuation, 'expression'),
        ],
        'expression_static': [
            (words((
                'break', 'continue', 'do', 'else', 'elseif', 'end', 'for',
                'if', 'in', 'repeat', 'return', 'then', 'until', 'while'),
                suffix=r'\b'), Keyword.Reserved),
        ],
        'expression': [
            include('ws'),

            (r'if\b', Keyword.Reserved, ('ternary', 'expression')),

            (r'local\b', Keyword.Declaration),
            *_luau_make_expression_special(True),
            (r'\.\.\.', Punctuation, '#pop'),

            (r'function\b', Keyword.Reserved, 'func_name'),

            include('expression_static'),
            *_luau_make_expression(True, _s),

            default('#pop'),
        ],
        'ternary': [
            include('ws'),

            (r'else\b', Keyword.Reserved, '#pop'),
            (words((
                'then', 'elseif',
            ), suffix=r'\b'), Operator.Reserved, 'expression'),

            default('#pop'),
        ],

        'closing_brace_pop': [
            (r'\}', Punctuation, '#pop'),
        ],
        'closing_parenthesis_pop': [
            (r'\)', Punctuation, '#pop'),
        ],
        'closing_gt_pop': [
            (r'>', Punctuation, '#pop'),
        ],

        'closing_parenthesis_base': [
            include('closing_parenthesis_pop'),
            include('base'),
        ],
        'closing_parenthesis_type': [
            include('closing_parenthesis_pop'),
            include('type'),
        ],
        'closing_brace_base': [
            include('closing_brace_pop'),
            include('base'),
        ],
        'closing_brace_type': [
            include('closing_brace_pop'),
            include('type'),
        ],
        'closing_gt_type': [
            include('closing_gt_pop'),
            include('type'),
        ],

        'string_escape': [
            (r'\\z\s*', String.Escape),
            (r'\\(?:[abfnrtvz\\"\'`\{\n])|[\r\n]{1,2}|x[\da-fA-F]{2}|\d{1,3}|'
             r'u\{\}[\da-fA-F]*\}', String.Escape),
        ],
        'string_single': [
            include('string_escape'),

            (r"'", String.Single, "#pop"),
            (r"[^\\']+", String.Single),
        ],
        'string_double': [
            include('string_escape'),

            (r'"', String.Double, "#pop"),
            (r'[^\\"]+', String.Double),
        ],
        'string_interpolated': [
            include('string_escape'),

            (r'\{', Punctuation, ('closing_brace_base', 'expression')),

            (r'`', String.Backtick, "#pop"),
            (r'[^\\`\{]+', String.Backtick),
        ],

        'func_name': [
            include('ws'),

            (r'[.:]', Punctuation),
            (rf'[a-zA-Z_]\w*(?={_s}*[.:])', Name.Class),
            (r'[a-zA-Z_]\w*', Name.Function),

            (r'<', Punctuation, 'closing_gt_type'),

            (r'\(', Punctuation, '#pop'),
        ],

        'type': [
            include('ws'),

            (r'\(', Punctuation, 'closing_parenthesis_type'),
            (r'\{', Punctuation, 'closing_brace_type'),
            (r'<', Punctuation, 'closing_gt_type'),

            (r"'", String.Single, 'string_single'),
            (r'"', String.Double, 'string_double'),

            (r'[|&\.,\[\]:=]+', Punctuation),
            (r'->', Punctuation),

            (r'typeof\(', Name.Builtin, ('closing_parenthesis_base',
                                         'expression')),
            (r'[a-zA-Z_]\w*', Name.Class),
        ],
        'type_start': [
            include('ws'),

            (r'\(', Punctuation, ('#pop', 'closing_parenthesis_type')),
            (r'\{', Punctuation, ('#pop', 'closing_brace_type')),
            (r'<', Punctuation, ('#pop', 'closing_gt_type')),

            (r"'", String.Single, ('#pop', 'string_single')),
            (r'"', String.Double, ('#pop', 'string_double')),

            (r'typeof\(', Name.Builtin, ('#pop', 'closing_parenthesis_base',
                                         'expression')),
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
        ],
        'type_end': [
            include('ws'),

            (r'[|&\.]', Punctuation, 'type_start'),
            (r'->', Punctuation, 'type_start'),

            (r'<', Punctuation, 'closing_gt_type'),

            default('#pop'),
        ],
        'type_declaration': [
            include('ws'),

            (r'[a-zA-Z_]\w*', Name.Class),
            (r'<', Punctuation, 'closing_gt_type'),

            (r'=', Punctuation, ('#pop', 'type_end', 'type_start')),
        ],
    }

    def __init__(self, **options):
        self.include_luau_builtins = get_bool_opt(
            options, 'include_luau_builtins', True)
        self.include_roblox_builtins = get_bool_opt(
            options, 'include_roblox_builtins', False)
        self.additional_builtins = get_list_opt(options, 'additional_builtins', [])
        self.disabled_builtins = get_list_opt(options, 'disabled_builtins', [])

        self._builtins = set(self.additional_builtins)
        if self.include_luau_builtins:
            from pygments.lexers._luau_builtins import LUAU_BUILTINS
            self._builtins.update(LUAU_BUILTINS)
        if self.include_roblox_builtins:
            from pygments.lexers._luau_builtins import ROBLOX_BUILTINS
            self._builtins.update(ROBLOX_BUILTINS)
        if self.additional_builtins:
            self._builtins.update(self.additional_builtins)
        self._builtins.difference_update(self.disabled_builtins)

        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name or token is Name.Other:
                split_value = value.split('.')
                complete_value = []
                new_index = index
                for position in range(len(split_value), 0, -1):
                    potential_string = '.'.join(split_value[:position])
                    if potential_string in self._builtins:
                        yield index, Name.Builtin, potential_string
                        new_index += len(potential_string)

                        if complete_value:
                            yield new_index, Punctuation, '.'
                            new_index += 1
                        break
                    complete_value.insert(0, split_value[position - 1])

                for position, substring in enumerate(complete_value):
                    if position + 1 == len(complete_value):
                        if token is Name:
                            yield new_index, Name.Variable, substring
                            continue
                        yield new_index, Name.Function, substring
                        continue
                    yield new_index, Name.Variable, substring
                    new_index += len(substring)
                    yield new_index, Punctuation, '.'
                    new_index += 1

                continue
            yield index, token, value

class MoonScriptLexer(LuaLexer):
    """
    For MoonScript source code.
    """

    name = 'MoonScript'
    url = 'http://moonscript.org'
    aliases = ['moonscript', 'moon']
    filenames = ['*.moon']
    mimetypes = ['text/x-moonscript', 'application/x-moonscript']
    version_added = '1.5'

    tokens = {
        'root': [
            (r'#!(.*?)$', Comment.Preproc),
            default('base'),
        ],
        'base': [
            ('--.*$', Comment.Single),
            (r'(?i)(\d*\.\d+|\d+\.\d*)(e[+-]?\d+)?', Number.Float),
            (r'(?i)\d+e[+-]?\d+', Number.Float),
            (r'(?i)0x[0-9a-f]*', Number.Hex),
            (r'\d+', Number.Integer),
            (r'\n', Whitespace),
            (r'[^\S\n]+', Text),
            (r'(?s)\[(=*)\[.*?\]\1\]', String),
            (r'(->|=>)', Name.Function),
            (r':[a-zA-Z_]\w*', Name.Variable),
            (r'(==|!=|~=|<=|>=|\.\.\.|\.\.|[=+\-*/%^<>#!.\\:])', Operator),
            (r'[;,]', Punctuation),
            (r'[\[\]{}()]', Keyword.Type),
            (r'[a-zA-Z_]\w*:', Name.Variable),
            (words((
                'class', 'extends', 'if', 'then', 'super', 'do', 'with',
                'import', 'export', 'while', 'elseif', 'return', 'for', 'in',
                'from', 'when', 'using', 'else', 'and', 'or', 'not', 'switch',
                'break'), suffix=r'\b'),
             Keyword),
            (r'(true|false|nil)\b', Keyword.Constant),
            (r'(and|or|not)\b', Operator.Word),
            (r'(self)\b', Name.Builtin.Pseudo),
            (r'@@?([a-zA-Z_]\w*)?', Name.Variable.Class),
            (r'[A-Z]\w*', Name.Class),  # proper name
            (words(all_lua_builtins(), suffix=r"\b"), Name.Builtin),
            (r'[A-Za-z_]\w*', Name),
            ("'", String.Single, combined('stringescape', 'sqs')),
            ('"', String.Double, combined('stringescape', 'dqs'))
        ],
        'stringescape': [
            (r'''\\([abfnrtv\\"']|\d{1,3})''', String.Escape)
        ],
        'sqs': [
            ("'", String.Single, '#pop'),
            ("[^']+", String)
        ],
        'dqs': [
            ('"', String.Double, '#pop'),
            ('[^"]+', String)
        ]
    }

    def get_tokens_unprocessed(self, text):
        # set . as Operator instead of Punctuation
        for index, token, value in LuaLexer.get_tokens_unprocessed(self, text):
            if token == Punctuation and value == ".":
                token = Operator
            yield index, token, value


class ChaiscriptLexer(RegexLexer):
    """
    For ChaiScript source code.
    """

    name = 'ChaiScript'
    url = 'http://chaiscript.com/'
    aliases = ['chaiscript', 'chai']
    filenames = ['*.chai']
    mimetypes = ['text/x-chaiscript', 'application/x-chaiscript']
    version_added = '2.0'

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'^\#.*?\n', Comment.Single)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            include('commentsandwhitespace'),
            (r'\n', Text),
            (r'[^\S\n]+', Text),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|\.\.'
             r'(<<|>>>?|==?|!=?|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'[=+\-*/]', Operator),
            (r'(for|in|while|do|break|return|continue|if|else|'
             r'throw|try|catch'
             r')\b', Keyword, 'slashstartsregex'),
            (r'(var)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(attr|def|fun)\b', Keyword.Reserved),
            (r'(true|false)\b', Keyword.Constant),
            (r'(eval|throw)\b', Name.Builtin),
            (r'`\S+`', Name.Builtin),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"', String.Double, 'dqstring'),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ],
        'dqstring': [
            (r'\$\{[^"}]+?\}', String.Interpol),
            (r'\$', String.Double),
            (r'\\\\', String.Double),
            (r'\\"', String.Double),
            (r'[^\\"$]+', String.Double),
            (r'"', String.Double, '#pop'),
        ],
    }


class LSLLexer(RegexLexer):
    """
    For Second Life's Linden Scripting Language source code.
    """

    name = 'LSL'
    aliases = ['lsl']
    filenames = ['*.lsl']
    mimetypes = ['text/x-lsl']
    url = 'https://wiki.secondlife.com/wiki/Linden_Scripting_Language'
    version_added = '2.0'

    flags = re.MULTILINE

    lsl_keywords = r'\b(?:do|else|for|if|jump|return|while)\b'
    lsl_types = r'\b(?:float|integer|key|list|quaternion|rotation|string|vector)\b'
    lsl_states = r'\b(?:(?:state)\s+\w+|default)\b'
    lsl_events = r'\b(?:state_(?:entry|exit)|touch(?:_(?:start|end))?|(?:land_)?collision(?:_(?:start|end))?|timer|listen|(?:no_)?sensor|control|(?:not_)?at_(?:rot_)?target|money|email|run_time_permissions|changed|attach|dataserver|moving_(?:start|end)|link_message|(?:on|object)_rez|remote_data|http_re(?:sponse|quest)|path_update|transaction_result)\b'
    lsl_functions_builtin = r'\b(?:ll(?:ReturnObjectsBy(?:ID|Owner)|Json(?:2List|[GS]etValue|ValueType)|Sin|Cos|Tan|Atan2|Sqrt|Pow|Abs|Fabs|Frand|Floor|Ceil|Round|Vec(?:Mag|Norm|Dist)|Rot(?:Between|2(?:Euler|Fwd|Left|Up))|(?:Euler|Axes)2Rot|Whisper|(?:Region|Owner)?Say|Shout|Listen(?:Control|Remove)?|Sensor(?:Repeat|Remove)?|Detected(?:Name|Key|Owner|Type|Pos|Vel|Grab|Rot|Group|LinkNumber)|Die|Ground|Wind|(?:[GS]et)(?:AnimationOverride|MemoryLimit|PrimMediaParams|ParcelMusicURL|Object(?:Desc|Name)|PhysicsMaterial|Status|Scale|Color|Alpha|Texture|Pos|Rot|Force|Torque)|ResetAnimationOverride|(?:Scale|Offset|Rotate)Texture|(?:Rot)?Target(?:Remove)?|(?:Stop)?MoveToTarget|Apply(?:Rotational)?Impulse|Set(?:KeyframedMotion|ContentType|RegionPos|(?:Angular)?Velocity|Buoyancy|HoverHeight|ForceAndTorque|TimerEvent|ScriptState|Damage|TextureAnim|Sound(?:Queueing|Radius)|Vehicle(?:Type|(?:Float|Vector|Rotation)Param)|(?:Touch|Sit)?Text|Camera(?:Eye|At)Offset|PrimitiveParams|ClickAction|Link(?:Alpha|Color|PrimitiveParams(?:Fast)?|Texture(?:Anim)?|Camera|Media)|RemoteScriptAccessPin|PayPrice|LocalRot)|ScaleByFactor|Get(?:(?:Max|Min)ScaleFactor|ClosestNavPoint|StaticPath|SimStats|Env|PrimitiveParams|Link(?:PrimitiveParams|Number(?:OfSides)?|Key|Name|Media)|HTTPHeader|FreeURLs|Object(?:Details|PermMask|PrimCount)|Parcel(?:MaxPrims|Details|Prim(?:Count|Owners))|Attached|(?:SPMax|Free|Used)Memory|Region(?:Name|TimeDilation|FPS|Corner|AgentCount)|Root(?:Position|Rotation)|UnixTime|(?:Parcel|Region)Flags|(?:Wall|GMT)clock|SimulatorHostname|BoundingBox|GeometricCenter|Creator|NumberOf(?:Prims|NotecardLines|Sides)|Animation(?:List)?|(?:Camera|Local)(?:Pos|Rot)|Vel|Accel|Omega|Time(?:stamp|OfDay)|(?:Object|CenterOf)?Mass|MassMKS|Energy|Owner|(?:Owner)?Key|SunDirection|Texture(?:Offset|Scale|Rot)|Inventory(?:Number|Name|Key|Type|Creator|PermMask)|Permissions(?:Key)?|StartParameter|List(?:Length|EntryType)|Date|Agent(?:Size|Info|Language|List)|LandOwnerAt|NotecardLine|Script(?:Name|State))|(?:Get|Reset|GetAndReset)Time|PlaySound(?:Slave)?|LoopSound(?:Master|Slave)?|(?:Trigger|Stop|Preload)Sound|(?:(?:Get|Delete)Sub|Insert)String|To(?:Upper|Lower)|Give(?:InventoryList|Money)|RezObject|(?:Stop)?LookAt|Sleep|CollisionFilter|(?:Take|Release)Controls|DetachFromAvatar|AttachToAvatar(?:Temp)?|InstantMessage|(?:GetNext)?Email|StopHover|MinEventDelay|RotLookAt|String(?:Length|Trim)|(?:Start|Stop)Animation|TargetOmega|RequestPermissions|(?:Create|Break)Link|BreakAllLinks|(?:Give|Remove)Inventory|Water|PassTouches|Request(?:Agent|Inventory)Data|TeleportAgent(?:Home|GlobalCoords)?|ModifyLand|CollisionSound|ResetScript|MessageLinked|PushObject|PassCollisions|AxisAngle2Rot|Rot2(?:Axis|Angle)|A(?:cos|sin)|AngleBetween|AllowInventoryDrop|SubStringIndex|List2(?:CSV|Integer|Json|Float|String|Key|Vector|Rot|List(?:Strided)?)|DeleteSubList|List(?:Statistics|Sort|Randomize|(?:Insert|Find|Replace)List)|EdgeOfWorld|AdjustSoundVolume|Key2Name|TriggerSoundLimited|EjectFromLand|(?:CSV|ParseString)2List|OverMyLand|SameGroup|UnSit|Ground(?:Slope|Normal|Contour)|GroundRepel|(?:Set|Remove)VehicleFlags|(?:AvatarOn)?(?:Link)?SitTarget|Script(?:Danger|Profiler)|Dialog|VolumeDetect|ResetOtherScript|RemoteLoadScriptPin|(?:Open|Close)RemoteDataChannel|SendRemoteData|RemoteDataReply|(?:Integer|String)ToBase64|XorBase64|Log(?:10)?|Base64To(?:String|Integer)|ParseStringKeepNulls|RezAtRoot|RequestSimulatorData|ForceMouselook|(?:Load|Release|(?:E|Une)scape)URL|ParcelMedia(?:CommandList|Query)|ModPow|MapDestination|(?:RemoveFrom|AddTo|Reset)Land(?:Pass|Ban)List|(?:Set|Clear)CameraParams|HTTP(?:Request|Response)|TextBox|DetectedTouch(?:UV|Face|Pos|(?:N|Bin)ormal|ST)|(?:MD5|SHA1|DumpList2)String|Request(?:Secure)?URL|Clear(?:Prim|Link)Media|(?:Link)?ParticleSystem|(?:Get|Request)(?:Username|DisplayName)|RegionSayTo|CastRay|GenerateKey|TransferLindenDollars|ManageEstateAccess|(?:Create|Delete)Character|ExecCharacterCmd|Evade|FleeFrom|NavigateTo|PatrolPoints|Pursue|UpdateCharacter|WanderWithin))\b'
    lsl_constants_float = r'\b(?:DEG_TO_RAD|PI(?:_BY_TWO)?|RAD_TO_DEG|SQRT2|TWO_PI)\b'
    lsl_constants_integer = r'\b(?:JSON_APPEND|STATUS_(?:PHYSICS|ROTATE_[XYZ]|PHANTOM|SANDBOX|BLOCK_GRAB(?:_OBJECT)?|(?:DIE|RETURN)_AT_EDGE|CAST_SHADOWS|OK|MALFORMED_PARAMS|TYPE_MISMATCH|BOUNDS_ERROR|NOT_(?:FOUND|SUPPORTED)|INTERNAL_ERROR|WHITELIST_FAILED)|AGENT(?:_(?:BY_(?:LEGACY_|USER)NAME|FLYING|ATTACHMENTS|SCRIPTED|MOUSELOOK|SITTING|ON_OBJECT|AWAY|WALKING|IN_AIR|TYPING|CROUCHING|BUSY|ALWAYS_RUN|AUTOPILOT|LIST_(?:PARCEL(?:_OWNER)?|REGION)))?|CAMERA_(?:PITCH|DISTANCE|BEHINDNESS_(?:ANGLE|LAG)|(?:FOCUS|POSITION)(?:_(?:THRESHOLD|LOCKED|LAG))?|FOCUS_OFFSET|ACTIVE)|ANIM_ON|LOOP|REVERSE|PING_PONG|SMOOTH|ROTATE|SCALE|ALL_SIDES|LINK_(?:ROOT|SET|ALL_(?:OTHERS|CHILDREN)|THIS)|ACTIVE|PASSIVE|SCRIPTED|CONTROL_(?:FWD|BACK|(?:ROT_)?(?:LEFT|RIGHT)|UP|DOWN|(?:ML_)?LBUTTON)|PERMISSION_(?:RETURN_OBJECTS|DEBIT|OVERRIDE_ANIMATIONS|SILENT_ESTATE_MANAGEMENT|TAKE_CONTROLS|TRIGGER_ANIMATION|ATTACH|CHANGE_LINKS|(?:CONTROL|TRACK)_CAMERA|TELEPORT)|INVENTORY_(?:TEXTURE|SOUND|OBJECT|SCRIPT|LANDMARK|CLOTHING|NOTECARD|BODYPART|ANIMATION|GESTURE|ALL|NONE)|CHANGED_(?:INVENTORY|COLOR|SHAPE|SCALE|TEXTURE|LINK|ALLOWED_DROP|OWNER|REGION(?:_START)?|TELEPORT|MEDIA)|OBJECT_(?:(?:PHYSICS|SERVER|STREAMING)_COST|UNKNOWN_DETAIL|CHARACTER_TIME|PHANTOM|PHYSICS|TEMP_ON_REZ|NAME|DESC|POS|PRIM_EQUIVALENCE|RETURN_(?:PARCEL(?:_OWNER)?|REGION)|ROO?T|VELOCITY|OWNER|GROUP|CREATOR|ATTACHED_POINT|RENDER_WEIGHT|PATHFINDING_TYPE|(?:RUNNING|TOTAL)_SCRIPT_COUNT|SCRIPT_(?:MEMORY|TIME))|TYPE_(?:INTEGER|FLOAT|STRING|KEY|VECTOR|ROTATION|INVALID)|(?:DEBUG|PUBLIC)_CHANNEL|ATTACH_(?:AVATAR_CENTER|CHEST|HEAD|BACK|PELVIS|MOUTH|CHIN|NECK|NOSE|BELLY|[LR](?:SHOULDER|HAND|FOOT|EAR|EYE|[UL](?:ARM|LEG)|HIP)|(?:LEFT|RIGHT)_PEC|HUD_(?:CENTER_[12]|TOP_(?:RIGHT|CENTER|LEFT)|BOTTOM(?:_(?:RIGHT|LEFT))?))|LAND_(?:LEVEL|RAISE|LOWER|SMOOTH|NOISE|REVERT)|DATA_(?:ONLINE|NAME|BORN|SIM_(?:POS|STATUS|RATING)|PAYINFO)|PAYMENT_INFO_(?:ON_FILE|USED)|REMOTE_DATA_(?:CHANNEL|REQUEST|REPLY)|PSYS_(?:PART_(?:BF_(?:ZERO|ONE(?:_MINUS_(?:DEST_COLOR|SOURCE_(ALPHA|COLOR)))?|DEST_COLOR|SOURCE_(ALPHA|COLOR))|BLEND_FUNC_(DEST|SOURCE)|FLAGS|(?:START|END)_(?:COLOR|ALPHA|SCALE|GLOW)|MAX_AGE|(?:RIBBON|WIND|INTERP_(?:COLOR|SCALE)|BOUNCE|FOLLOW_(?:SRC|VELOCITY)|TARGET_(?:POS|LINEAR)|EMISSIVE)_MASK)|SRC_(?:MAX_AGE|PATTERN|ANGLE_(?:BEGIN|END)|BURST_(?:RATE|PART_COUNT|RADIUS|SPEED_(?:MIN|MAX))|ACCEL|TEXTURE|TARGET_KEY|OMEGA|PATTERN_(?:DROP|EXPLODE|ANGLE(?:_CONE(?:_EMPTY)?)?)))|VEHICLE_(?:REFERENCE_FRAME|TYPE_(?:NONE|SLED|CAR|BOAT|AIRPLANE|BALLOON)|(?:LINEAR|ANGULAR)_(?:FRICTION_TIMESCALE|MOTOR_DIRECTION)|LINEAR_MOTOR_OFFSET|HOVER_(?:HEIGHT|EFFICIENCY|TIMESCALE)|BUOYANCY|(?:LINEAR|ANGULAR)_(?:DEFLECTION_(?:EFFICIENCY|TIMESCALE)|MOTOR_(?:DECAY_)?TIMESCALE)|VERTICAL_ATTRACTION_(?:EFFICIENCY|TIMESCALE)|BANKING_(?:EFFICIENCY|MIX|TIMESCALE)|FLAG_(?:NO_DEFLECTION_UP|LIMIT_(?:ROLL_ONLY|MOTOR_UP)|HOVER_(?:(?:WATER|TERRAIN|UP)_ONLY|GLOBAL_HEIGHT)|MOUSELOOK_(?:STEER|BANK)|CAMERA_DECOUPLED))|PRIM_(?:TYPE(?:_(?:BOX|CYLINDER|PRISM|SPHERE|TORUS|TUBE|RING|SCULPT))?|HOLE_(?:DEFAULT|CIRCLE|SQUARE|TRIANGLE)|MATERIAL(?:_(?:STONE|METAL|GLASS|WOOD|FLESH|PLASTIC|RUBBER))?|SHINY_(?:NONE|LOW|MEDIUM|HIGH)|BUMP_(?:NONE|BRIGHT|DARK|WOOD|BARK|BRICKS|CHECKER|CONCRETE|TILE|STONE|DISKS|GRAVEL|BLOBS|SIDING|LARGETILE|STUCCO|SUCTION|WEAVE)|TEXGEN_(?:DEFAULT|PLANAR)|SCULPT_(?:TYPE_(?:SPHERE|TORUS|PLANE|CYLINDER|MASK)|FLAG_(?:MIRROR|INVERT))|PHYSICS(?:_(?:SHAPE_(?:CONVEX|NONE|PRIM|TYPE)))?|(?:POS|ROT)_LOCAL|SLICE|TEXT|FLEXIBLE|POINT_LIGHT|TEMP_ON_REZ|PHANTOM|POSITION|SIZE|ROTATION|TEXTURE|NAME|OMEGA|DESC|LINK_TARGET|COLOR|BUMP_SHINY|FULLBRIGHT|TEXGEN|GLOW|MEDIA_(?:ALT_IMAGE_ENABLE|CONTROLS|(?:CURRENT|HOME)_URL|AUTO_(?:LOOP|PLAY|SCALE|ZOOM)|FIRST_CLICK_INTERACT|(?:WIDTH|HEIGHT)_PIXELS|WHITELIST(?:_ENABLE)?|PERMS_(?:INTERACT|CONTROL)|PARAM_MAX|CONTROLS_(?:STANDARD|MINI)|PERM_(?:NONE|OWNER|GROUP|ANYONE)|MAX_(?:URL_LENGTH|WHITELIST_(?:SIZE|COUNT)|(?:WIDTH|HEIGHT)_PIXELS)))|MASK_(?:BASE|OWNER|GROUP|EVERYONE|NEXT)|PERM_(?:TRANSFER|MODIFY|COPY|MOVE|ALL)|PARCEL_(?:MEDIA_COMMAND_(?:STOP|PAUSE|PLAY|LOOP|TEXTURE|URL|TIME|AGENT|UNLOAD|AUTO_ALIGN|TYPE|SIZE|DESC|LOOP_SET)|FLAG_(?:ALLOW_(?:FLY|(?:GROUP_)?SCRIPTS|LANDMARK|TERRAFORM|DAMAGE|CREATE_(?:GROUP_)?OBJECTS)|USE_(?:ACCESS_(?:GROUP|LIST)|BAN_LIST|LAND_PASS_LIST)|LOCAL_SOUND_ONLY|RESTRICT_PUSHOBJECT|ALLOW_(?:GROUP|ALL)_OBJECT_ENTRY)|COUNT_(?:TOTAL|OWNER|GROUP|OTHER|SELECTED|TEMP)|DETAILS_(?:NAME|DESC|OWNER|GROUP|AREA|ID|SEE_AVATARS))|LIST_STAT_(?:MAX|MIN|MEAN|MEDIAN|STD_DEV|SUM(?:_SQUARES)?|NUM_COUNT|GEOMETRIC_MEAN|RANGE)|PAY_(?:HIDE|DEFAULT)|REGION_FLAG_(?:ALLOW_DAMAGE|FIXED_SUN|BLOCK_TERRAFORM|SANDBOX|DISABLE_(?:COLLISIONS|PHYSICS)|BLOCK_FLY|ALLOW_DIRECT_TELEPORT|RESTRICT_PUSHOBJECT)|HTTP_(?:METHOD|MIMETYPE|BODY_(?:MAXLENGTH|TRUNCATED)|CUSTOM_HEADER|PRAGMA_NO_CACHE|VERBOSE_THROTTLE|VERIFY_CERT)|STRING_(?:TRIM(?:_(?:HEAD|TAIL))?)|CLICK_ACTION_(?:NONE|TOUCH|SIT|BUY|PAY|OPEN(?:_MEDIA)?|PLAY|ZOOM)|TOUCH_INVALID_FACE|PROFILE_(?:NONE|SCRIPT_MEMORY)|RC_(?:DATA_FLAGS|DETECT_PHANTOM|GET_(?:LINK_NUM|NORMAL|ROOT_KEY)|MAX_HITS|REJECT_(?:TYPES|AGENTS|(?:NON)?PHYSICAL|LAND))|RCERR_(?:CAST_TIME_EXCEEDED|SIM_PERF_LOW|UNKNOWN)|ESTATE_ACCESS_(?:ALLOWED_(?:AGENT|GROUP)_(?:ADD|REMOVE)|BANNED_AGENT_(?:ADD|REMOVE))|DENSITY|FRICTION|RESTITUTION|GRAVITY_MULTIPLIER|KFM_(?:COMMAND|CMD_(?:PLAY|STOP|PAUSE|SET_MODE)|MODE|FORWARD|LOOP|PING_PONG|REVERSE|DATA|ROTATION|TRANSLATION)|ERR_(?:GENERIC|PARCEL_PERMISSIONS|MALFORMED_PARAMS|RUNTIME_PERMISSIONS|THROTTLED)|CHARACTER_(?:CMD_(?:(?:SMOOTH_)?STOP|JUMP)|DESIRED_(?:TURN_)?SPEED|RADIUS|STAY_WITHIN_PARCEL|LENGTH|ORIENTATION|ACCOUNT_FOR_SKIPPED_FRAMES|AVOIDANCE_MODE|TYPE(?:_(?:[A-D]|NONE))?|MAX_(?:DECEL|TURN_RADIUS|(?:ACCEL|SPEED)))|PURSUIT_(?:OFFSET|FUZZ_FACTOR|GOAL_TOLERANCE|INTERCEPT)|REQUIRE_LINE_OF_SIGHT|FORCE_DIRECT_PATH|VERTICAL|HORIZONTAL|AVOID_(?:CHARACTERS|DYNAMIC_OBSTACLES|NONE)|PU_(?:EVADE_(?:HIDDEN|SPOTTED)|FAILURE_(?:DYNAMIC_PATHFINDING_DISABLED|INVALID_(?:GOAL|START)|NO_(?:NAVMESH|VALID_DESTINATION)|OTHER|TARGET_GONE|(?:PARCEL_)?UNREACHABLE)|(?:GOAL|SLOWDOWN_DISTANCE)_REACHED)|TRAVERSAL_TYPE(?:_(?:FAST|NONE|SLOW))?|CONTENT_TYPE_(?:ATOM|FORM|HTML|JSON|LLSD|RSS|TEXT|XHTML|XML)|GCNP_(?:RADIUS|STATIC)|(?:PATROL|WANDER)_PAUSE_AT_WAYPOINTS|OPT_(?:AVATAR|CHARACTER|EXCLUSION_VOLUME|LEGACY_LINKSET|MATERIAL_VOLUME|OTHER|STATIC_OBSTACLE|WALKABLE)|SIM_STAT_PCT_CHARS_STEPPED)\b'
    lsl_constants_integer_boolean = r'\b(?:FALSE|TRUE)\b'
    lsl_constants_rotation = r'\b(?:ZERO_ROTATION)\b'
    lsl_constants_string = r'\b(?:EOF|JSON_(?:ARRAY|DELETE|FALSE|INVALID|NULL|NUMBER|OBJECT|STRING|TRUE)|NULL_KEY|TEXTURE_(?:BLANK|DEFAULT|MEDIA|PLYWOOD|TRANSPARENT)|URL_REQUEST_(?:GRANTED|DENIED))\b'
    lsl_constants_vector = r'\b(?:TOUCH_INVALID_(?:TEXCOORD|VECTOR)|ZERO_VECTOR)\b'
    lsl_invalid_broken = r'\b(?:LAND_(?:LARGE|MEDIUM|SMALL)_BRUSH)\b'
    lsl_invalid_deprecated = r'\b(?:ATTACH_[LR]PEC|DATA_RATING|OBJECT_ATTACHMENT_(?:GEOMETRY_BYTES|SURFACE_AREA)|PRIM_(?:CAST_SHADOWS|MATERIAL_LIGHT|TYPE_LEGACY)|PSYS_SRC_(?:INNER|OUTER)ANGLE|VEHICLE_FLAG_NO_FLY_UP|ll(?:Cloud|Make(?:Explosion|Fountain|Smoke|Fire)|RemoteDataSetRegion|Sound(?:Preload)?|XorBase64Strings(?:Correct)?))\b'
    lsl_invalid_illegal = r'\b(?:event)\b'
    lsl_invalid_unimplemented = r'\b(?:CHARACTER_(?:MAX_ANGULAR_(?:ACCEL|SPEED)|TURN_SPEED_MULTIPLIER)|PERMISSION_(?:CHANGE_(?:JOINTS|PERMISSIONS)|RELEASE_OWNERSHIP|REMAP_CONTROLS)|PRIM_PHYSICS_MATERIAL|PSYS_SRC_OBJ_REL_MASK|ll(?:CollisionSprite|(?:Stop)?PointAt|(?:(?:Refresh|Set)Prim)URL|(?:Take|Release)Camera|RemoteLoadScript))\b'
    lsl_reserved_godmode = r'\b(?:ll(?:GodLikeRezObject|Set(?:Inventory|Object)PermMask))\b'
    lsl_reserved_log = r'\b(?:print)\b'
    lsl_operators = r'\+\+|\-\-|<<|>>|&&?|\|\|?|\^|~|[!%<>=*+\-/]=?'

    tokens = {
        'root':
        [
            (r'//.*?\n',                          Comment.Single),
            (r'/\*',                              Comment.Multiline, 'comment'),
            (r'"',                                String.Double, 'string'),
            (lsl_keywords,                        Keyword),
            (lsl_types,                           Keyword.Type),
            (lsl_states,                          Name.Class),
            (lsl_events,                          Name.Builtin),
            (lsl_functions_builtin,               Name.Function),
            (lsl_constants_float,                 Keyword.Constant),
            (lsl_constants_integer,               Keyword.Constant),
            (lsl_constants_integer_boolean,       Keyword.Constant),
            (lsl_constants_rotation,              Keyword.Constant),
            (lsl_constants_string,                Keyword.Constant),
            (lsl_constants_vector,                Keyword.Constant),
            (lsl_invalid_broken,                  Error),
            (lsl_invalid_deprecated,              Error),
            (lsl_invalid_illegal,                 Error),
            (lsl_invalid_unimplemented,           Error),
            (lsl_reserved_godmode,                Keyword.Reserved),
            (lsl_reserved_log,                    Keyword.Reserved),
            (r'\b([a-zA-Z_]\w*)\b',     Name.Variable),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d*', Number.Float),
            (r'(\d+\.\d*|\.\d+)',                 Number.Float),
            (r'0[xX][0-9a-fA-F]+',                Number.Hex),
            (r'\d+',                              Number.Integer),
            (lsl_operators,                       Operator),
            (r':=?',                              Error),
            (r'[,;{}()\[\]]',                     Punctuation),
            (r'\n+',                              Whitespace),
            (r'\s+',                              Whitespace)
        ],
        'comment':
        [
            (r'[^*/]+',                           Comment.Multiline),
            (r'/\*',                              Comment.Multiline, '#push'),
            (r'\*/',                              Comment.Multiline, '#pop'),
            (r'[*/]',                             Comment.Multiline)
        ],
        'string':
        [
            (r'\\([nt"\\])',                      String.Escape),
            (r'"',                                String.Double, '#pop'),
            (r'\\.',                              Error),
            (r'[^"\\]+',                          String.Double),
        ]
    }


class AppleScriptLexer(RegexLexer):
    """
    For AppleScript source code,
    including `AppleScript Studio
    <http://developer.apple.com/documentation/AppleScript/
    Reference/StudioReference>`_.
    Contributed by Andreas Amann <aamann@mac.com>.
    """

    name = 'AppleScript'
    url = 'https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/introduction/ASLR_intro.html'
    aliases = ['applescript']
    filenames = ['*.applescript']
    version_added = '1.0'

    flags = re.MULTILINE | re.DOTALL

    Identifiers = r'[a-zA-Z]\w*'

    # XXX: use words() for all of these
    Literals = ('AppleScript', 'current application', 'false', 'linefeed',
                'missing value', 'pi', 'quote', 'result', 'return', 'space',
                'tab', 'text item delimiters', 'true', 'version')
    Classes = ('alias ', 'application ', 'boolean ', 'class ', 'constant ',
               'date ', 'file ', 'integer ', 'list ', 'number ', 'POSIX file ',
               'real ', 'record ', 'reference ', 'RGB color ', 'script ',
               'text ', 'unit types', '(?:Unicode )?text', 'string')
    BuiltIn = ('attachment', 'attribute run', 'character', 'day', 'month',
               'paragraph', 'word', 'year')
    HandlerParams = ('about', 'above', 'against', 'apart from', 'around',
                     'aside from', 'at', 'below', 'beneath', 'beside',
                     'between', 'for', 'given', 'instead of', 'on', 'onto',
                     'out of', 'over', 'since')
    Commands = ('ASCII (character|number)', 'activate', 'beep', 'choose URL',
                'choose application', 'choose color', 'choose file( name)?',
                'choose folder', 'choose from list',
                'choose remote application', 'clipboard info',
                'close( access)?', 'copy', 'count', 'current date', 'delay',
                'delete', 'display (alert|dialog)', 'do shell script',
                'duplicate', 'exists', 'get eof', 'get volume settings',
                'info for', 'launch', 'list (disks|folder)', 'load script',
                'log', 'make', 'mount volume', 'new', 'offset',
                'open( (for access|location))?', 'path to', 'print', 'quit',
                'random number', 'read', 'round', 'run( script)?',
                'say', 'scripting components',
                'set (eof|the clipboard to|volume)', 'store script',
                'summarize', 'system attribute', 'system info',
                'the clipboard', 'time to GMT', 'write', 'quoted form')
    References = ('(in )?back of', '(in )?front of', '[0-9]+(st|nd|rd|th)',
                  'first', 'second', 'third', 'fourth', 'fifth', 'sixth',
                  'seventh', 'eighth', 'ninth', 'tenth', 'after', 'back',
                  'before', 'behind', 'every', 'front', 'index', 'last',
                  'middle', 'some', 'that', 'through', 'thru', 'where', 'whose')
    Operators = ("and", "or", "is equal", "equals", "(is )?equal to", "is not",
                 "isn't", "isn't equal( to)?", "is not equal( to)?",
                 "doesn't equal", "does not equal", "(is )?greater than",
                 "comes after", "is not less than or equal( to)?",
                 "isn't less than or equal( to)?", "(is )?less than",
                 "comes before", "is not greater than or equal( to)?",
                 "isn't greater than or equal( to)?",
                 "(is  )?greater than or equal( to)?", "is not less than",
                 "isn't less than", "does not come before",
                 "doesn't come before", "(is )?less than or equal( to)?",
                 "is not greater than", "isn't greater than",
                 "does not come after", "doesn't come after", "starts? with",
                 "begins? with", "ends? with", "contains?", "does not contain",
                 "doesn't contain", "is in", "is contained by", "is not in",
                 "is not contained by", "isn't contained by", "div", "mod",
                 "not", "(a  )?(ref( to)?|reference to)", "is", "does")
    Control = ('considering', 'else', 'error', 'exit', 'from', 'if',
               'ignoring', 'in', 'repeat', 'tell', 'then', 'times', 'to',
               'try', 'until', 'using terms from', 'while', 'whith',
               'with timeout( of)?', 'with transaction', 'by', 'continue',
               'end', 'its?', 'me', 'my', 'return', 'of', 'as')
    Declarations = ('global', 'local', 'prop(erty)?', 'set', 'get')
    Reserved = ('but', 'put', 'returning', 'the')
    StudioClasses = ('action cell', 'alert reply', 'application', 'box',
                     'browser( cell)?', 'bundle', 'button( cell)?', 'cell',
                     'clip view', 'color well', 'color-panel',
                     'combo box( item)?', 'control',
                     'data( (cell|column|item|row|source))?', 'default entry',
                     'dialog reply', 'document', 'drag info', 'drawer',
                     'event', 'font(-panel)?', 'formatter',
                     'image( (cell|view))?', 'matrix', 'menu( item)?', 'item',
                     'movie( view)?', 'open-panel', 'outline view', 'panel',
                     'pasteboard', 'plugin', 'popup button',
                     'progress indicator', 'responder', 'save-panel',
                     'scroll view', 'secure text field( cell)?', 'slider',
                     'sound', 'split view', 'stepper', 'tab view( item)?',
                     'table( (column|header cell|header view|view))',
                     'text( (field( cell)?|view))?', 'toolbar( item)?',
                     'user-defaults', 'view', 'window')
    StudioEvents = ('accept outline drop', 'accept table drop', 'action',
                    'activated', 'alert ended', 'awake from nib', 'became key',
                    'became main', 'begin editing', 'bounds changed',
                    'cell value', 'cell value changed', 'change cell value',
                    'change item value', 'changed', 'child of item',
                    'choose menu item', 'clicked', 'clicked toolbar item',
                    'closed', 'column clicked', 'column moved',
                    'column resized', 'conclude drop', 'data representation',
                    'deminiaturized', 'dialog ended', 'document nib name',
                    'double clicked', 'drag( (entered|exited|updated))?',
                    'drop', 'end editing', 'exposed', 'idle', 'item expandable',
                    'item value', 'item value changed', 'items changed',
                    'keyboard down', 'keyboard up', 'launched',
                    'load data representation', 'miniaturized', 'mouse down',
                    'mouse dragged', 'mouse entered', 'mouse exited',
                    'mouse moved', 'mouse up', 'moved',
                    'number of browser rows', 'number of items',
                    'number of rows', 'open untitled', 'opened', 'panel ended',
                    'parameters updated', 'plugin loaded', 'prepare drop',
                    'prepare outline drag', 'prepare outline drop',
                    'prepare table drag', 'prepare table drop',
                    'read from file', 'resigned active', 'resigned key',
                    'resigned main', 'resized( sub views)?',
                    'right mouse down', 'right mouse dragged',
                    'right mouse up', 'rows changed', 'scroll wheel',
                    'selected tab view item', 'selection changed',
                    'selection changing', 'should begin editing',
                    'should close', 'should collapse item',
                    'should end editing', 'should expand item',
                    'should open( untitled)?',
                    'should quit( after last window closed)?',
                    'should select column', 'should select item',
                    'should select row', 'should select tab view item',
                    'should selection change', 'should zoom', 'shown',
                    'update menu item', 'update parameters',
                    'update toolbar item', 'was hidden', 'was miniaturized',
                    'will become active', 'will close', 'will dismiss',
                    'will display browser cell', 'will display cell',
                    'will display item cell', 'will display outline cell',
                    'will finish launching', 'will hide', 'will miniaturize',
                    'will move', 'will open', 'will pop up', 'will quit',
                    'will resign active', 'will resize( sub views)?',
                    'will select tab view item', 'will show', 'will zoom',
                    'write to file', 'zoomed')
    StudioCommands = ('animate', 'append', 'call method', 'center',
                      'close drawer', 'close panel', 'display',
                      'display alert', 'display dialog', 'display panel', 'go',
                      'hide', 'highlight', 'increment', 'item for',
                      'load image', 'load movie', 'load nib', 'load panel',
                      'load sound', 'localized string', 'lock focus', 'log',
                      'open drawer', 'path for', 'pause', 'perform action',
                      'play', 'register', 'resume', 'scroll', 'select( all)?',
                      'show', 'size to fit', 'start', 'step back',
                      'step forward', 'stop', 'synchronize', 'unlock focus',
                      'update')
    StudioProperties = ('accepts arrow key', 'action method', 'active',
                        'alignment', 'allowed identifiers',
                        'allows branch selection', 'allows column reordering',
                        'allows column resizing', 'allows column selection',
                        'allows customization',
                        'allows editing text attributes',
                        'allows empty selection', 'allows mixed state',
                        'allows multiple selection', 'allows reordering',
                        'allows undo', 'alpha( value)?', 'alternate image',
                        'alternate increment value', 'alternate title',
                        'animation delay', 'associated file name',
                        'associated object', 'auto completes', 'auto display',
                        'auto enables items', 'auto repeat',
                        'auto resizes( outline column)?',
                        'auto save expanded items', 'auto save name',
                        'auto save table columns', 'auto saves configuration',
                        'auto scroll', 'auto sizes all columns to fit',
                        'auto sizes cells', 'background color', 'bezel state',
                        'bezel style', 'bezeled', 'border rect', 'border type',
                        'bordered', 'bounds( rotation)?', 'box type',
                        'button returned', 'button type',
                        'can choose directories', 'can choose files',
                        'can draw', 'can hide',
                        'cell( (background color|size|type))?', 'characters',
                        'class', 'click count', 'clicked( data)? column',
                        'clicked data item', 'clicked( data)? row',
                        'closeable', 'collating', 'color( (mode|panel))',
                        'command key down', 'configuration',
                        'content(s| (size|view( margins)?))?', 'context',
                        'continuous', 'control key down', 'control size',
                        'control tint', 'control view',
                        'controller visible', 'coordinate system',
                        'copies( on scroll)?', 'corner view', 'current cell',
                        'current column', 'current( field)?  editor',
                        'current( menu)? item', 'current row',
                        'current tab view item', 'data source',
                        'default identifiers', 'delta (x|y|z)',
                        'destination window', 'directory', 'display mode',
                        'displayed cell', 'document( (edited|rect|view))?',
                        'double value', 'dragged column', 'dragged distance',
                        'dragged items', 'draws( cell)? background',
                        'draws grid', 'dynamically scrolls', 'echos bullets',
                        'edge', 'editable', 'edited( data)? column',
                        'edited data item', 'edited( data)? row', 'enabled',
                        'enclosing scroll view', 'ending page',
                        'error handling', 'event number', 'event type',
                        'excluded from windows menu', 'executable path',
                        'expanded', 'fax number', 'field editor', 'file kind',
                        'file name', 'file type', 'first responder',
                        'first visible column', 'flipped', 'floating',
                        'font( panel)?', 'formatter', 'frameworks path',
                        'frontmost', 'gave up', 'grid color', 'has data items',
                        'has horizontal ruler', 'has horizontal scroller',
                        'has parent data item', 'has resize indicator',
                        'has shadow', 'has sub menu', 'has vertical ruler',
                        'has vertical scroller', 'header cell', 'header view',
                        'hidden', 'hides when deactivated', 'highlights by',
                        'horizontal line scroll', 'horizontal page scroll',
                        'horizontal ruler view', 'horizontally resizable',
                        'icon image', 'id', 'identifier',
                        'ignores multiple clicks',
                        'image( (alignment|dims when disabled|frame style|scaling))?',
                        'imports graphics', 'increment value',
                        'indentation per level', 'indeterminate', 'index',
                        'integer value', 'intercell spacing', 'item height',
                        'key( (code|equivalent( modifier)?|window))?',
                        'knob thickness', 'label', 'last( visible)? column',
                        'leading offset', 'leaf', 'level', 'line scroll',
                        'loaded', 'localized sort', 'location', 'loop mode',
                        'main( (bunde|menu|window))?', 'marker follows cell',
                        'matrix mode', 'maximum( content)? size',
                        'maximum visible columns',
                        'menu( form representation)?', 'miniaturizable',
                        'miniaturized', 'minimized image', 'minimized title',
                        'minimum column width', 'minimum( content)? size',
                        'modal', 'modified', 'mouse down state',
                        'movie( (controller|file|rect))?', 'muted', 'name',
                        'needs display', 'next state', 'next text',
                        'number of tick marks', 'only tick mark values',
                        'opaque', 'open panel', 'option key down',
                        'outline table column', 'page scroll', 'pages across',
                        'pages down', 'palette label', 'pane splitter',
                        'parent data item', 'parent window', 'pasteboard',
                        'path( (names|separator))?', 'playing',
                        'plays every frame', 'plays selection only', 'position',
                        'preferred edge', 'preferred type', 'pressure',
                        'previous text', 'prompt', 'properties',
                        'prototype cell', 'pulls down', 'rate',
                        'released when closed', 'repeated',
                        'requested print time', 'required file type',
                        'resizable', 'resized column', 'resource path',
                        'returns records', 'reuses columns', 'rich text',
                        'roll over', 'row height', 'rulers visible',
                        'save panel', 'scripts path', 'scrollable',
                        'selectable( identifiers)?', 'selected cell',
                        'selected( data)? columns?', 'selected data items?',
                        'selected( data)? rows?', 'selected item identifier',
                        'selection by rect', 'send action on arrow key',
                        'sends action when done editing', 'separates columns',
                        'separator item', 'sequence number', 'services menu',
                        'shared frameworks path', 'shared support path',
                        'sheet', 'shift key down', 'shows alpha',
                        'shows state by', 'size( mode)?',
                        'smart insert delete enabled', 'sort case sensitivity',
                        'sort column', 'sort order', 'sort type',
                        'sorted( data rows)?', 'sound', 'source( mask)?',
                        'spell checking enabled', 'starting page', 'state',
                        'string value', 'sub menu', 'super menu', 'super view',
                        'tab key traverses cells', 'tab state', 'tab type',
                        'tab view', 'table view', 'tag', 'target( printer)?',
                        'text color', 'text container insert',
                        'text container origin', 'text returned',
                        'tick mark position', 'time stamp',
                        'title(d| (cell|font|height|position|rect))?',
                        'tool tip', 'toolbar', 'trailing offset', 'transparent',
                        'treat packages as directories', 'truncated labels',
                        'types', 'unmodified characters', 'update views',
                        'use sort indicator', 'user defaults',
                        'uses data source', 'uses ruler',
                        'uses threaded animation',
                        'uses title from previous column', 'value wraps',
                        'version',
                        'vertical( (line scroll|page scroll|ruler view))?',
                        'vertically resizable', 'view',
                        'visible( document rect)?', 'volume', 'width', 'window',
                        'windows menu', 'wraps', 'zoomable', 'zoomed')

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'¬\n', String.Escape),
            (r"'s\s+", Text),  # This is a possessive, consider moving
            (r'(--|#).*?$', Comment),
            (r'\(\*', Comment.Multiline, 'comment'),
            (r'[(){}!,.:]', Punctuation),
            (r'(«)([^»]+)(»)',
             bygroups(Text, Name.Builtin, Text)),
            (r'\b((?:considering|ignoring)\s*)'
             r'(application responses|case|diacriticals|hyphens|'
             r'numeric strings|punctuation|white space)',
             bygroups(Keyword, Name.Builtin)),
            (r'(-|\*|\+|&|≠|>=?|<=?|=|≥|≤|/|÷|\^)', Operator),
            (r"\b({})\b".format('|'.join(Operators)), Operator.Word),
            (r'^(\s*(?:on|end)\s+)'
             r'({})'.format('|'.join(StudioEvents[::-1])),
             bygroups(Keyword, Name.Function)),
            (r'^(\s*)(in|on|script|to)(\s+)', bygroups(Text, Keyword, Text)),
            (r'\b(as )({})\b'.format('|'.join(Classes)),
             bygroups(Keyword, Name.Class)),
            (r'\b({})\b'.format('|'.join(Literals)), Name.Constant),
            (r'\b({})\b'.format('|'.join(Commands)), Name.Builtin),
            (r'\b({})\b'.format('|'.join(Control)), Keyword),
            (r'\b({})\b'.format('|'.join(Declarations)), Keyword),
            (r'\b({})\b'.format('|'.join(Reserved)), Name.Builtin),
            (r'\b({})s?\b'.format('|'.join(BuiltIn)), Name.Builtin),
            (r'\b({})\b'.format('|'.join(HandlerParams)), Name.Builtin),
            (r'\b({})\b'.format('|'.join(StudioProperties)), Name.Attribute),
            (r'\b({})s?\b'.format('|'.join(StudioClasses)), Name.Builtin),
            (r'\b({})\b'.format('|'.join(StudioCommands)), Name.Builtin),
            (r'\b({})\b'.format('|'.join(References)), Name.Builtin),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (rf'\b({Identifiers})\b', Name.Variable),
            (r'[-+]?(\d+\.\d*|\d*\.\d+)(E[-+][0-9]+)?', Number.Float),
            (r'[-+]?\d+', Number.Integer),
        ],
        'comment': [
            (r'\(\*', Comment.Multiline, '#push'),
            (r'\*\)', Comment.Multiline, '#pop'),
            ('[^*(]+', Comment.Multiline),
            ('[*(]', Comment.Multiline),
        ],
    }


class RexxLexer(RegexLexer):
    """
    Rexx is a scripting language available for
    a wide range of different platforms with its roots found on mainframe
    systems. It is popular for I/O- and data based tasks and can act as glue
    language to bind different applications together.
    """
    name = 'Rexx'
    url = 'http://www.rexxinfo.org/'
    aliases = ['rexx', 'arexx']
    filenames = ['*.rexx', '*.rex', '*.rx', '*.arexx']
    mimetypes = ['text/x-rexx']
    version_added = '2.0'
    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'"', String, 'string_double'),
            (r"'", String, 'string_single'),
            (r'[0-9]+(\.[0-9]+)?(e[+-]?[0-9])?', Number),
            (r'([a-z_]\w*)(\s*)(:)(\s*)(procedure)\b',
             bygroups(Name.Function, Whitespace, Operator, Whitespace,
                      Keyword.Declaration)),
            (r'([a-z_]\w*)(\s*)(:)',
             bygroups(Name.Label, Whitespace, Operator)),
            include('function'),
            include('keyword'),
            include('operator'),
            (r'[a-z_]\w*', Text),
        ],
        'function': [
            (words((
                'abbrev', 'abs', 'address', 'arg', 'b2x', 'bitand', 'bitor', 'bitxor',
                'c2d', 'c2x', 'center', 'charin', 'charout', 'chars', 'compare',
                'condition', 'copies', 'd2c', 'd2x', 'datatype', 'date', 'delstr',
                'delword', 'digits', 'errortext', 'form', 'format', 'fuzz', 'insert',
                'lastpos', 'left', 'length', 'linein', 'lineout', 'lines', 'max',
                'min', 'overlay', 'pos', 'queued', 'random', 'reverse', 'right', 'sign',
                'sourceline', 'space', 'stream', 'strip', 'substr', 'subword', 'symbol',
                'time', 'trace', 'translate', 'trunc', 'value', 'verify', 'word',
                'wordindex', 'wordlength', 'wordpos', 'words', 'x2b', 'x2c', 'x2d',
                'xrange'), suffix=r'(\s*)(\()'),
             bygroups(Name.Builtin, Whitespace, Operator)),
        ],
        'keyword': [
            (r'(address|arg|by|call|do|drop|else|end|exit|for|forever|if|'
             r'interpret|iterate|leave|nop|numeric|off|on|options|parse|'
             r'pull|push|queue|return|say|select|signal|to|then|trace|until|'
             r'while)\b', Keyword.Reserved),
        ],
        'operator': [
            (r'(-|//|/|\(|\)|\*\*|\*|\\<<|\\<|\\==|\\=|\\>>|\\>|\\|\|\||\||'
             r'&&|&|%|\+|<<=|<<|<=|<>|<|==|=|><|>=|>>=|>>|>|¬<<|¬<|¬==|¬=|'
             r'¬>>|¬>|¬|\.|,)', Operator),
        ],
        'string_double': [
            (r'[^"\n]+', String),
            (r'""', String),
            (r'"', String, '#pop'),
            (r'\n', Text, '#pop'),  # Stray linefeed also terminates strings.
        ],
        'string_single': [
            (r'[^\'\n]+', String),
            (r'\'\'', String),
            (r'\'', String, '#pop'),
            (r'\n', Text, '#pop'),  # Stray linefeed also terminates strings.
        ],
        'comment': [
            (r'[^*]+', Comment.Multiline),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'\*', Comment.Multiline),
        ]
    }

    def _c(s):
        return re.compile(s, re.MULTILINE)
    _ADDRESS_COMMAND_PATTERN = _c(r'^\s*address\s+command\b')
    _ADDRESS_PATTERN = _c(r'^\s*address\s+')
    _DO_WHILE_PATTERN = _c(r'^\s*do\s+while\b')
    _IF_THEN_DO_PATTERN = _c(r'^\s*if\b.+\bthen\s+do\s*$')
    _PROCEDURE_PATTERN = _c(r'^\s*([a-z_]\w*)(\s*)(:)(\s*)(procedure)\b')
    _ELSE_DO_PATTERN = _c(r'\belse\s+do\s*$')
    _PARSE_ARG_PATTERN = _c(r'^\s*parse\s+(upper\s+)?(arg|value)\b')
    PATTERNS_AND_WEIGHTS = (
        (_ADDRESS_COMMAND_PATTERN, 0.2),
        (_ADDRESS_PATTERN, 0.05),
        (_DO_WHILE_PATTERN, 0.1),
        (_ELSE_DO_PATTERN, 0.1),
        (_IF_THEN_DO_PATTERN, 0.1),
        (_PROCEDURE_PATTERN, 0.5),
        (_PARSE_ARG_PATTERN, 0.2),
    )

    def analyse_text(text):
        """
        Check for initial comment and patterns that distinguish Rexx from other
        C-like languages.
        """
        if re.search(r'/\*\**\s*rexx', text, re.IGNORECASE):
            # Header matches MVS Rexx requirements, this is certainly a Rexx
            # script.
            return 1.0
        elif text.startswith('/*'):
            # Header matches general Rexx requirements; the source code might
            # still be any language using C comments such as C++, C# or Java.
            lowerText = text.lower()
            result = sum(weight
                         for (pattern, weight) in RexxLexer.PATTERNS_AND_WEIGHTS
                         if pattern.search(lowerText)) + 0.01
            return min(result, 1.0)


class MOOCodeLexer(RegexLexer):
    """
    For MOOCode (the MOO scripting language).
    """
    name = 'MOOCode'
    url = 'http://www.moo.mud.org/'
    filenames = ['*.moo']
    aliases = ['moocode', 'moo']
    mimetypes = ['text/x-moocode']
    version_added = '0.9'

    tokens = {
        'root': [
            # Numbers
            (r'(0|[1-9][0-9_]*)', Number.Integer),
            # Strings
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            # exceptions
            (r'(E_PERM|E_DIV)', Name.Exception),
            # db-refs
            (r'((#[-0-9]+)|(\$\w+))', Name.Entity),
            # Keywords
            (r'\b(if|else|elseif|endif|for|endfor|fork|endfork|while'
             r'|endwhile|break|continue|return|try'
             r'|except|endtry|finally|in)\b', Keyword),
            # builtins
            (r'(random|length)', Name.Builtin),
            # special variables
            (r'(player|caller|this|args)', Name.Variable.Instance),
            # skip whitespace
            (r'\s+', Text),
            (r'\n', Text),
            # other operators
            (r'([!;=,{}&|:.\[\]@()<>?]+)', Operator),
            # function call
            (r'(\w+)(\()', bygroups(Name.Function, Operator)),
            # variables
            (r'(\w+)', Text),
        ]
    }


class HybrisLexer(RegexLexer):
    """
    For Hybris source code.
    """

    name = 'Hybris'
    aliases = ['hybris']
    filenames = ['*.hyb']
    mimetypes = ['text/x-hybris', 'application/x-hybris']
    url = 'https://github.com/evilsocket/hybris'
    version_added = '1.4'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:function|method|operator\s+)+?)'
             r'([a-zA-Z_]\w*)'
             r'(\s*)(\()', bygroups(Keyword, Name.Function, Text, Operator)),
            (r'[^\S\n]+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'@[a-zA-Z_][\w.]*', Name.Decorator),
            (r'(break|case|catch|next|default|do|else|finally|for|foreach|of|'
             r'unless|if|new|return|switch|me|throw|try|while)\b', Keyword),
            (r'(extends|private|protected|public|static|throws|function|method|'
             r'operator)\b', Keyword.Declaration),
            (r'(true|false|null|__FILE__|__LINE__|__VERSION__|__LIB_PATH__|'
             r'__INC_PATH__)\b', Keyword.Constant),
            (r'(class|struct)(\s+)',
             bygroups(Keyword.Declaration, Text), 'class'),
            (r'(import|include)(\s+)',
             bygroups(Keyword.Namespace, Text), 'import'),
            (words((
                'gc_collect', 'gc_mm_items', 'gc_mm_usage', 'gc_collect_threshold',
                'urlencode', 'urldecode', 'base64encode', 'base64decode', 'sha1', 'crc32',
                'sha2', 'md5', 'md5_file', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos',
                'cosh', 'exp', 'fabs', 'floor', 'fmod', 'log', 'log10', 'pow', 'sin',
                'sinh', 'sqrt', 'tan', 'tanh', 'isint', 'isfloat', 'ischar', 'isstring',
                'isarray', 'ismap', 'isalias', 'typeof', 'sizeof', 'toint', 'tostring',
                'fromxml', 'toxml', 'binary', 'pack', 'load', 'eval', 'var_names',
                'var_values', 'user_functions', 'dyn_functions', 'methods', 'call',
                'call_method', 'mknod', 'mkfifo', 'mount', 'umount2', 'umount', 'ticks',
                'usleep', 'sleep', 'time', 'strtime', 'strdate', 'dllopen', 'dlllink',
                'dllcall', 'dllcall_argv', 'dllclose', 'env', 'exec', 'fork', 'getpid',
                'wait', 'popen', 'pclose', 'exit', 'kill', 'pthread_create',
                'pthread_create_argv', 'pthread_exit', 'pthread_join', 'pthread_kill',
                'smtp_send', 'http_get', 'http_post', 'http_download', 'socket', 'bind',
                'listen', 'accept', 'getsockname', 'getpeername', 'settimeout', 'connect',
                'server', 'recv', 'send', 'close', 'print', 'println', 'printf', 'input',
                'readline', 'serial_open', 'serial_fcntl', 'serial_get_attr',
                'serial_get_ispeed', 'serial_get_ospeed', 'serial_set_attr',
                'serial_set_ispeed', 'serial_set_ospeed', 'serial_write', 'serial_read',
                'serial_close', 'xml_load', 'xml_parse', 'fopen', 'fseek', 'ftell',
                'fsize', 'fread', 'fwrite', 'fgets', 'fclose', 'file', 'readdir',
                'pcre_replace', 'size', 'pop', 'unmap', 'has', 'keys', 'values',
                'length', 'find', 'substr', 'replace', 'split', 'trim', 'remove',
                'contains', 'join'), suffix=r'\b'),
             Name.Builtin),
            (words((
                'MethodReference', 'Runner', 'Dll', 'Thread', 'Pipe', 'Process',
                'Runnable', 'CGI', 'ClientSocket', 'Socket', 'ServerSocket',
                'File', 'Console', 'Directory', 'Exception'), suffix=r'\b'),
             Keyword.Type),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"'\\.'|'[^\\]'|'\\u[0-9a-f]{4}'", String.Char),
            (r'(\.)([a-zA-Z_]\w*)',
             bygroups(Operator, Name.Attribute)),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[~^*!%&\[\](){}<>|+=:;,./?\-@]+', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Text),
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
    }

    def analyse_text(text):
        """public method and private method don't seem to be quite common
        elsewhere."""
        result = 0
        if re.search(r'\b(?:public|private)\s+method\b', text):
            result += 0.01
        return result



class EasytrieveLexer(RegexLexer):
    """
    Easytrieve Plus is a programming language for extracting, filtering and
    converting sequential data. Furthermore it can layout data for reports.
    It is mainly used on mainframe platforms and can access several of the
    mainframe's native file formats. It is somewhat comparable to awk.
    """
    name = 'Easytrieve'
    aliases = ['easytrieve']
    filenames = ['*.ezt', '*.mac']
    mimetypes = ['text/x-easytrieve']
    url = 'https://www.broadcom.com/products/mainframe/application-development/easytrieve-report-generator'
    version_added = '2.1'
    flags = 0

    # Note: We cannot use r'\b' at the start and end of keywords because
    # Easytrieve Plus delimiter characters are:
    #
    #   * space ( )
    #   * apostrophe (')
    #   * period (.)
    #   * comma (,)
    #   * parenthesis ( and )
    #   * colon (:)
    #
    # Additionally words end once a '*' appears, indicatins a comment.
    _DELIMITERS = r' \'.,():\n'
    _DELIMITERS_OR_COMENT = _DELIMITERS + '*'
    _DELIMITER_PATTERN = '[' + _DELIMITERS + ']'
    _DELIMITER_PATTERN_CAPTURE = '(' + _DELIMITER_PATTERN + ')'
    _NON_DELIMITER_OR_COMMENT_PATTERN = '[^' + _DELIMITERS_OR_COMENT + ']'
    _OPERATORS_PATTERN = '[.+\\-/=\\[\\](){}<>;,&%¬]'
    _KEYWORDS = [
        'AFTER-BREAK', 'AFTER-LINE', 'AFTER-SCREEN', 'AIM', 'AND', 'ATTR',
        'BEFORE', 'BEFORE-BREAK', 'BEFORE-LINE', 'BEFORE-SCREEN', 'BUSHU',
        'BY', 'CALL', 'CASE', 'CHECKPOINT', 'CHKP', 'CHKP-STATUS', 'CLEAR',
        'CLOSE', 'COL', 'COLOR', 'COMMIT', 'CONTROL', 'COPY', 'CURSOR', 'D',
        'DECLARE', 'DEFAULT', 'DEFINE', 'DELETE', 'DENWA', 'DISPLAY', 'DLI',
        'DO', 'DUPLICATE', 'E', 'ELSE', 'ELSE-IF', 'END', 'END-CASE',
        'END-DO', 'END-IF', 'END-PROC', 'ENDPAGE', 'ENDTABLE', 'ENTER', 'EOF',
        'EQ', 'ERROR', 'EXIT', 'EXTERNAL', 'EZLIB', 'F1', 'F10', 'F11', 'F12',
        'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F2', 'F20', 'F21',
        'F22', 'F23', 'F24', 'F25', 'F26', 'F27', 'F28', 'F29', 'F3', 'F30',
        'F31', 'F32', 'F33', 'F34', 'F35', 'F36', 'F4', 'F5', 'F6', 'F7',
        'F8', 'F9', 'FETCH', 'FILE-STATUS', 'FILL', 'FINAL', 'FIRST',
        'FIRST-DUP', 'FOR', 'GE', 'GET', 'GO', 'GOTO', 'GQ', 'GR', 'GT',
        'HEADING', 'HEX', 'HIGH-VALUES', 'IDD', 'IDMS', 'IF', 'IN', 'INSERT',
        'JUSTIFY', 'KANJI-DATE', 'KANJI-DATE-LONG', 'KANJI-TIME', 'KEY',
        'KEY-PRESSED', 'KOKUGO', 'KUN', 'LAST-DUP', 'LE', 'LEVEL', 'LIKE',
        'LINE', 'LINE-COUNT', 'LINE-NUMBER', 'LINK', 'LIST', 'LOW-VALUES',
        'LQ', 'LS', 'LT', 'MACRO', 'MASK', 'MATCHED', 'MEND', 'MESSAGE',
        'MOVE', 'MSTART', 'NE', 'NEWPAGE', 'NOMASK', 'NOPRINT', 'NOT',
        'NOTE', 'NOVERIFY', 'NQ', 'NULL', 'OF', 'OR', 'OTHERWISE', 'PA1',
        'PA2', 'PA3', 'PAGE-COUNT', 'PAGE-NUMBER', 'PARM-REGISTER',
        'PATH-ID', 'PATTERN', 'PERFORM', 'POINT', 'POS', 'PRIMARY', 'PRINT',
        'PROCEDURE', 'PROGRAM', 'PUT', 'READ', 'RECORD', 'RECORD-COUNT',
        'RECORD-LENGTH', 'REFRESH', 'RELEASE', 'RENUM', 'REPEAT', 'REPORT',
        'REPORT-INPUT', 'RESHOW', 'RESTART', 'RETRIEVE', 'RETURN-CODE',
        'ROLLBACK', 'ROW', 'S', 'SCREEN', 'SEARCH', 'SECONDARY', 'SELECT',
        'SEQUENCE', 'SIZE', 'SKIP', 'SOKAKU', 'SORT', 'SQL', 'STOP', 'SUM',
        'SYSDATE', 'SYSDATE-LONG', 'SYSIN', 'SYSIPT', 'SYSLST', 'SYSPRINT',
        'SYSSNAP', 'SYSTIME', 'TALLY', 'TERM-COLUMNS', 'TERM-NAME',
        'TERM-ROWS', 'TERMINATION', 'TITLE', 'TO', 'TRANSFER', 'TRC',
        'UNIQUE', 'UNTIL', 'UPDATE', 'UPPERCASE', 'USER', 'USERID', 'VALUE',
        'VERIFY', 'W', 'WHEN', 'WHILE', 'WORK', 'WRITE', 'X', 'XDM', 'XRST'
    ]

    tokens = {
        'root': [
            (r'\*.*\n', Comment.Single),
            (r'\n+', Whitespace),
            # Macro argument
            (r'&' + _NON_DELIMITER_OR_COMMENT_PATTERN + r'+\.', Name.Variable,
             'after_macro_argument'),
            # Macro call
            (r'%' + _NON_DELIMITER_OR_COMMENT_PATTERN + r'+', Name.Variable),
            (r'(FILE|MACRO|REPORT)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'after_declaration'),
            (r'(JOB|PARM)' + r'(' + _DELIMITER_PATTERN + r')',
             bygroups(Keyword.Declaration, Operator)),
            (words(_KEYWORDS, suffix=_DELIMITER_PATTERN_CAPTURE),
             bygroups(Keyword.Reserved, Operator)),
            (_OPERATORS_PATTERN, Operator),
            # Procedure declaration
            (r'(' + _NON_DELIMITER_OR_COMMENT_PATTERN + r'+)(\s*)(\.?)(\s*)(PROC)(\s*\n)',
             bygroups(Name.Function, Whitespace, Operator, Whitespace,
                      Keyword.Declaration, Whitespace)),
            (r'[0-9]+\.[0-9]*', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r"'(''|[^'])*'", String),
            (r'\s+', Whitespace),
            # Everything else just belongs to a name
            (_NON_DELIMITER_OR_COMMENT_PATTERN + r'+', Name),
         ],
        'after_declaration': [
            (_NON_DELIMITER_OR_COMMENT_PATTERN + r'+', Name.Function),
            default('#pop'),
        ],
        'after_macro_argument': [
            (r'\*.*\n', Comment.Single, '#pop'),
            (r'\s+', Whitespace, '#pop'),
            (_OPERATORS_PATTERN, Operator, '#pop'),
            (r"'(''|[^'])*'", String, '#pop'),
            # Everything else just belongs to a name
            (_NON_DELIMITER_OR_COMMENT_PATTERN + r'+', Name),
        ],
    }
    _COMMENT_LINE_REGEX = re.compile(r'^\s*\*')
    _MACRO_HEADER_REGEX = re.compile(r'^\s*MACRO')

    def analyse_text(text):
        """
        Perform a structural analysis for basic Easytrieve constructs.
        """
        result = 0.0
        lines = text.split('\n')
        hasEndProc = False
        hasHeaderComment = False
        hasFile = False
        hasJob = False
        hasProc = False
        hasParm = False
        hasReport = False

        def isCommentLine(line):
            return EasytrieveLexer._COMMENT_LINE_REGEX.match(lines[0]) is not None

        def isEmptyLine(line):
            return not bool(line.strip())

        # Remove possible empty lines and header comments.
        while lines and (isEmptyLine(lines[0]) or isCommentLine(lines[0])):
            if not isEmptyLine(lines[0]):
                hasHeaderComment = True
            del lines[0]

        if EasytrieveLexer._MACRO_HEADER_REGEX.match(lines[0]):
            # Looks like an Easytrieve macro.
            result = 0.4
            if hasHeaderComment:
                result += 0.4
        else:
            # Scan the source for lines starting with indicators.
            for line in lines:
                words = line.split()
                if (len(words) >= 2):
                    firstWord = words[0]
                    if not hasReport:
                        if not hasJob:
                            if not hasFile:
                                if not hasParm:
                                    if firstWord == 'PARM':
                                        hasParm = True
                                if firstWord == 'FILE':
                                    hasFile = True
                            if firstWord == 'JOB':
                                hasJob = True
                        elif firstWord == 'PROC':
                            hasProc = True
                        elif firstWord == 'END-PROC':
                            hasEndProc = True
                        elif firstWord == 'REPORT':
                            hasReport = True

            # Weight the findings.
            if hasJob and (hasProc == hasEndProc):
                if hasHeaderComment:
                    result += 0.1
                if hasParm:
                    if hasProc:
                        # Found PARM, JOB and PROC/END-PROC:
                        # pretty sure this is Easytrieve.
                        result += 0.8
                    else:
                        # Found PARAM and  JOB: probably this is Easytrieve
                        result += 0.5
                else:
                    # Found JOB and possibly other keywords: might be Easytrieve
                    result += 0.11
                    if hasParm:
                        # Note: PARAM is not a proper English word, so this is
                        # regarded a much better indicator for Easytrieve than
                        # the other words.
                        result += 0.2
                    if hasFile:
                        result += 0.01
                    if hasReport:
                        result += 0.01
        assert 0.0 <= result <= 1.0
        return result


class JclLexer(RegexLexer):
    """
    Job Control Language (JCL)
    is a scripting language used on mainframe platforms to instruct the system
    on how to run a batch job or start a subsystem. It is somewhat
    comparable to MS DOS batch and Unix shell scripts.
    """
    name = 'JCL'
    aliases = ['jcl']
    filenames = ['*.jcl']
    mimetypes = ['text/x-jcl']
    url = 'https://en.wikipedia.org/wiki/Job_Control_Language'
    version_added = '2.1'

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'//\*.*\n', Comment.Single),
            (r'//', Keyword.Pseudo, 'statement'),
            (r'/\*', Keyword.Pseudo, 'jes2_statement'),
            # TODO: JES3 statement
            (r'.*\n', Other)  # Input text or inline code in any language.
        ],
        'statement': [
            (r'\s*\n', Whitespace, '#pop'),
            (r'([a-z]\w*)(\s+)(exec|job)(\s*)',
             bygroups(Name.Label, Whitespace, Keyword.Reserved, Whitespace),
             'option'),
            (r'[a-z]\w*', Name.Variable, 'statement_command'),
            (r'\s+', Whitespace, 'statement_command'),
        ],
        'statement_command': [
            (r'\s+(command|cntl|dd|endctl|endif|else|include|jcllib|'
             r'output|pend|proc|set|then|xmit)\s+', Keyword.Reserved, 'option'),
            include('option')
        ],
        'jes2_statement': [
            (r'\s*\n', Whitespace, '#pop'),
            (r'\$', Keyword, 'option'),
            (r'\b(jobparam|message|netacct|notify|output|priority|route|'
             r'setup|signoff|xeq|xmit)\b', Keyword, 'option'),
        ],
        'option': [
            # (r'\n', Text, 'root'),
            (r'\*', Name.Builtin),
            (r'[\[\](){}<>;,]', Punctuation),
            (r'[-+*/=&%]', Operator),
            (r'[a-z_]\w*', Name),
            (r'\d+\.\d*', Number.Float),
            (r'\.\d+', Number.Float),
            (r'\d+', Number.Integer),
            (r"'", String, 'option_string'),
            (r'[ \t]+', Whitespace, 'option_comment'),
            (r'\.', Punctuation),
        ],
        'option_string': [
            (r"(\n)(//)", bygroups(Text, Keyword.Pseudo)),
            (r"''", String),
            (r"[^']", String),
            (r"'", String, '#pop'),
        ],
        'option_comment': [
            # (r'\n', Text, 'root'),
            (r'.+', Comment.Single),
        ]
    }

    _JOB_HEADER_PATTERN = re.compile(r'^//[a-z#$@][a-z0-9#$@]{0,7}\s+job(\s+.*)?$',
                                     re.IGNORECASE)

    def analyse_text(text):
        """
        Recognize JCL job by header.
        """
        result = 0.0
        lines = text.split('\n')
        if len(lines) > 0:
            if JclLexer._JOB_HEADER_PATTERN.match(lines[0]):
                result = 1.0
        assert 0.0 <= result <= 1.0
        return result


class MiniScriptLexer(RegexLexer):
    """
    For MiniScript source code.
    """

    name = 'MiniScript'
    url = 'https://miniscript.org'
    aliases = ['miniscript', 'ms']
    filenames = ['*.ms']
    mimetypes = ['text/x-minicript', 'application/x-miniscript']
    version_added = '2.6'

    tokens = {
        'root': [
            (r'#!(.*?)$', Comment.Preproc),
            default('base'),
        ],
        'base': [
            ('//.*$', Comment.Single),
            (r'(?i)(\d*\.\d+|\d+\.\d*)(e[+-]?\d+)?', Number),
            (r'(?i)\d+e[+-]?\d+', Number),
            (r'\d+', Number),
            (r'\n', Text),
            (r'[^\S\n]+', Text),
            (r'"', String, 'string_double'),
            (r'(==|!=|<=|>=|[=+\-*/%^<>.:])', Operator),
            (r'[;,\[\]{}()]', Punctuation),
            (words((
                'break', 'continue', 'else', 'end', 'for', 'function', 'if',
                'in', 'isa', 'then', 'repeat', 'return', 'while'), suffix=r'\b'),
             Keyword),
            (words((
                'abs', 'acos', 'asin', 'atan', 'ceil', 'char', 'cos', 'floor',
                'log', 'round', 'rnd', 'pi', 'sign', 'sin', 'sqrt', 'str', 'tan',
                'hasIndex', 'indexOf', 'len', 'val', 'code', 'remove', 'lower',
                'upper', 'replace', 'split', 'indexes', 'values', 'join', 'sum',
                'sort', 'shuffle', 'push', 'pop', 'pull', 'range',
                'print', 'input', 'time', 'wait', 'locals', 'globals', 'outer',
                'yield'), suffix=r'\b'),
             Name.Builtin),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(and|or|not|new)\b', Operator.Word),
            (r'(self|super|__isa)\b', Name.Builtin.Pseudo),
            (r'[a-zA-Z_]\w*', Name.Variable)
        ],
        'string_double': [
            (r'[^"\n]+', String),
            (r'""', String),
            (r'"', String, '#pop'),
            (r'\n', Text, '#pop'),  # Stray linefeed also terminates strings.
        ]
    }

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\shellcon.py ===
# Generated by h2py from \mssdk\include\shlobj.h and shellapi.h
WM_USER = 1024
DROPEFFECT_NONE = 0
DROPEFFECT_COPY = 1
DROPEFFECT_MOVE = 2
DROPEFFECT_LINK = 4
DROPEFFECT_SCROLL = -2147483648

FO_MOVE = 1
FO_COPY = 2
FO_DELETE = 3
FO_RENAME = 4

## File operation flags used with shell.SHFileOperation
FOF_MULTIDESTFILES = 1
FOF_CONFIRMMOUSE = 2
FOF_SILENT = 4
FOF_RENAMEONCOLLISION = 8
FOF_NOCONFIRMATION = 16
FOF_WANTMAPPINGHANDLE = 32
FOF_ALLOWUNDO = 64
FOF_FILESONLY = 128
FOF_SIMPLEPROGRESS = 256
FOF_NOCONFIRMMKDIR = 512
FOF_NOERRORUI = 1024
FOF_NOCOPYSECURITYATTRIBS = 2048
FOF_NORECURSION = 4096
FOF_NO_CONNECTED_ELEMENTS = 8192
FOF_WANTNUKEWARNING = 16384
FOF_NORECURSEREPARSE = 32768
FOF_NO_UI = FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_NOCONFIRMMKDIR

## Extended file operation flags, used with IFileOperation
FOFX_NOSKIPJUNCTIONS = 0x00010000
FOFX_PREFERHARDLINK = 0x00020000
FOFX_SHOWELEVATIONPROMPT = 0x00040000
FOFX_EARLYFAILURE = 0x00100000
FOFX_PRESERVEFILEEXTENSIONS = 0x00200000
FOFX_KEEPNEWERFILE = 0x00400000
FOFX_NOCOPYHOOKS = 0x00800000
FOFX_NOMINIMIZEBOX = 0x01000000
FOFX_MOVEACLSACROSSVOLUMES = 0x02000000
FOFX_DONTDISPLAYSOURCEPATH = 0x04000000
FOFX_DONTDISPLAYDESTPATH = 0x08000000
FOFX_REQUIREELEVATION = 0x10000000
FOFX_COPYASDOWNLOAD = 0x40000000
FOFX_DONTDISPLAYLOCATIONS = 0x80000000

PO_DELETE = 19
PO_RENAME = 20
PO_PORTCHANGE = 32
PO_REN_PORT = 52
SE_ERR_FNF = 2
SE_ERR_PNF = 3
SE_ERR_ACCESSDENIED = 5
SE_ERR_OOM = 8
SE_ERR_DLLNOTFOUND = 32
SE_ERR_SHARE = 26
SE_ERR_ASSOCINCOMPLETE = 27
SE_ERR_DDETIMEOUT = 28
SE_ERR_DDEFAIL = 29
SE_ERR_DDEBUSY = 30
SE_ERR_NOASSOC = 31
SEE_MASK_CLASSNAME = 1
SEE_MASK_CLASSKEY = 3
SEE_MASK_IDLIST = 4
SEE_MASK_INVOKEIDLIST = 12
SEE_MASK_ICON = 16
SEE_MASK_HOTKEY = 32
SEE_MASK_NOCLOSEPROCESS = 64
SEE_MASK_CONNECTNETDRV = 128
SEE_MASK_FLAG_DDEWAIT = 256
SEE_MASK_DOENVSUBST = 512
SEE_MASK_FLAG_NO_UI = 1024
SEE_MASK_UNICODE = 16384
SEE_MASK_NO_CONSOLE = 32768
SEE_MASK_ASYNCOK = 1048576
SEE_MASK_HMONITOR = 2097152
SHERB_NOCONFIRMATION = 1
SHERB_NOPROGRESSUI = 2
SHERB_NOSOUND = 4
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
SHGFI_ICON = 256
SHGFI_DISPLAYNAME = 512
SHGFI_TYPENAME = 1024
SHGFI_ATTRIBUTES = 2048
SHGFI_ICONLOCATION = 4096
SHGFI_EXETYPE = 8192
SHGFI_SYSICONINDEX = 16384
SHGFI_LINKOVERLAY = 32768
SHGFI_SELECTED = 65536
SHGFI_ATTR_SPECIFIED = 131072
SHGFI_LARGEICON = 0
SHGFI_SMALLICON = 1
SHGFI_OPENICON = 2
SHGFI_SHELLICONSIZE = 4
SHGFI_PIDL = 8
SHGFI_USEFILEATTRIBUTES = 16
SHGNLI_PIDL = 1
SHGNLI_PREFIXNAME = 2
SHGNLI_NOUNIQUE = 4
PRINTACTION_OPEN = 0
PRINTACTION_PROPERTIES = 1
PRINTACTION_NETINSTALL = 2
PRINTACTION_NETINSTALLLINK = 3
PRINTACTION_TESTPAGE = 4
PRINTACTION_OPENNETPRN = 5
PRINTACTION_DOCUMENTDEFAULTS = 6
PRINTACTION_SERVERPROPERTIES = 7

# Flags used with IContextMenu.QueryContextMenu
CMF_NORMAL = 0
CMF_DEFAULTONLY = 1
CMF_VERBSONLY = 2
CMF_EXPLORE = 4
CMF_NOVERBS = 8
CMF_CANRENAME = 16
CMF_NODEFAULT = 32
CMF_INCLUDESTATIC = 64
CMF_ITEMMENU = 128
CMF_EXTENDEDVERBS = 256
CMF_DISABLEDVERBS = 512
CMF_ASYNCVERBSTATE = 1024
CMF_OPTIMIZEFORINVOKE = 2048
CMF_SYNCCASCADEMENU = 4096
CMF_DONOTPICKDEFAULT = 8192
CMF_RESERVED = 0xFFFF0000

GCS_VERBA = 0
GCS_HELPTEXTA = 1
GCS_VALIDATEA = 2
GCS_VERBW = 4
GCS_HELPTEXTW = 5
GCS_VALIDATEW = 6
GCS_UNICODE = 4
GCS_VERB = GCS_VERBA
GCS_HELPTEXT = GCS_HELPTEXTA
GCS_VALIDATE = GCS_VALIDATEA
CMDSTR_NEWFOLDERA = "NewFolder"
CMDSTR_VIEWLISTA = "ViewList"
CMDSTR_VIEWDETAILSA = "ViewDetails"
CMDSTR_NEWFOLDER = CMDSTR_NEWFOLDERA
CMDSTR_VIEWLIST = CMDSTR_VIEWLISTA
CMDSTR_VIEWDETAILS = CMDSTR_VIEWDETAILSA
CMIC_MASK_HOTKEY = SEE_MASK_HOTKEY
CMIC_MASK_ICON = SEE_MASK_ICON
CMIC_MASK_FLAG_NO_UI = SEE_MASK_FLAG_NO_UI
CMIC_MASK_UNICODE = SEE_MASK_UNICODE
CMIC_MASK_NO_CONSOLE = SEE_MASK_NO_CONSOLE
CMIC_MASK_ASYNCOK = SEE_MASK_ASYNCOK
CMIC_MASK_PTINVOKE = 536870912
GIL_OPENICON = 1
GIL_FORSHELL = 2
GIL_ASYNC = 32
GIL_DEFAULTICON = 64
GIL_FORSHORTCUT = 128
GIL_CHECKSHIELD = 512
GIL_SIMULATEDOC = 1
GIL_PERINSTANCE = 2
GIL_PERCLASS = 4
GIL_NOTFILENAME = 8
GIL_DONTCACHE = 16
GIL_SHIELD = 512
GIL_FORCENOSHIELD = 1024
ISIOI_ICONFILE = 1
ISIOI_ICONINDEX = 2
ISIOI_SYSIMAGELISTINDEX = 4
FVSIF_RECT = 1
FVSIF_PINNED = 2
FVSIF_NEWFAILED = 134217728
FVSIF_NEWFILE = -2147483648
FVSIF_CANVIEWIT = 1073741824
FCIDM_SHVIEWFIRST = 0
FCIDM_SHVIEWLAST = 32767
FCIDM_BROWSERFIRST = 40960
FCIDM_BROWSERLAST = 48896
FCIDM_GLOBALFIRST = 32768
FCIDM_GLOBALLAST = 40959
FCIDM_MENU_FILE = FCIDM_GLOBALFIRST + 0
FCIDM_MENU_EDIT = FCIDM_GLOBALFIRST + 64
FCIDM_MENU_VIEW = FCIDM_GLOBALFIRST + 128
FCIDM_MENU_VIEW_SEP_OPTIONS = FCIDM_GLOBALFIRST + 129
FCIDM_MENU_TOOLS = FCIDM_GLOBALFIRST + 192
FCIDM_MENU_TOOLS_SEP_GOTO = FCIDM_GLOBALFIRST + 193
FCIDM_MENU_HELP = FCIDM_GLOBALFIRST + 256
FCIDM_MENU_FIND = FCIDM_GLOBALFIRST + 320
FCIDM_MENU_EXPLORE = FCIDM_GLOBALFIRST + 336
FCIDM_MENU_FAVORITES = FCIDM_GLOBALFIRST + 368
FCIDM_TOOLBAR = FCIDM_BROWSERFIRST + 0
FCIDM_STATUS = FCIDM_BROWSERFIRST + 1
IDC_OFFLINE_HAND = 103
SBSP_DEFBROWSER = 0
SBSP_SAMEBROWSER = 1
SBSP_NEWBROWSER = 2
SBSP_DEFMODE = 0
SBSP_OPENMODE = 16
SBSP_EXPLOREMODE = 32
SBSP_ABSOLUTE = 0
SBSP_RELATIVE = 4096
SBSP_PARENT = 8192
SBSP_NAVIGATEBACK = 16384
SBSP_NAVIGATEFORWARD = 32768
SBSP_ALLOW_AUTONAVIGATE = 65536
SBSP_INITIATEDBYHLINKFRAME = -2147483648
SBSP_REDIRECT = 1073741824
SBSP_WRITENOHISTORY = 134217728
SBSP_NOAUTOSELECT = 67108864
FCW_STATUS = 1
FCW_TOOLBAR = 2
FCW_TREE = 3
FCW_INTERNETBAR = 6
FCW_PROGRESS = 8
FCT_MERGE = 1
FCT_CONFIGABLE = 2
FCT_ADDTOEND = 4
CDBOSC_SETFOCUS = 0
CDBOSC_KILLFOCUS = 1
CDBOSC_SELCHANGE = 2
CDBOSC_RENAME = 3
SVSI_DESELECT = 0
SVSI_SELECT = 1
SVSI_EDIT = 3
SVSI_DESELECTOTHERS = 4
SVSI_ENSUREVISIBLE = 8
SVSI_FOCUSED = 16
SVSI_TRANSLATEPT = 32
SVSI_SELECTIONMARK = 64
SVSI_POSITIONITEM = 128
SVSI_CHECK = 256
SVSI_CHECK2 = 512
SVSI_KEYBOARDSELECT = 1025
SVSI_NOTAKEFOCUS = 1073741824
SVGIO_BACKGROUND = 0
SVGIO_SELECTION = 1
SVGIO_ALLVIEW = 2
SVGIO_CHECKED = (0x3,)
SVGIO_TYPE_MASK = (0xF,)
SVGIO_FLAG_VIEWORDER = -2147483648  # 0x80000000
STRRET_WSTR = 0
STRRET_OFFSET = 1
STRRET_CSTR = 2
CSIDL_DESKTOP = 0
CSIDL_INTERNET = 1
CSIDL_PROGRAMS = 2
CSIDL_CONTROLS = 3
CSIDL_PRINTERS = 4
CSIDL_PERSONAL = 5
CSIDL_FAVORITES = 6
CSIDL_STARTUP = 7
CSIDL_RECENT = 8
CSIDL_SENDTO = 9
CSIDL_BITBUCKET = 10
CSIDL_STARTMENU = 11
CSIDL_MYDOCUMENTS = 12
CSIDL_MYMUSIC = 13
CSIDL_MYVIDEO = 14
CSIDL_DESKTOPDIRECTORY = 16
CSIDL_DRIVES = 17
CSIDL_NETWORK = 18
CSIDL_NETHOOD = 19
CSIDL_FONTS = 20
CSIDL_TEMPLATES = 21
CSIDL_COMMON_STARTMENU = 22
CSIDL_COMMON_PROGRAMS = 23
CSIDL_COMMON_STARTUP = 24
CSIDL_COMMON_DESKTOPDIRECTORY = 25
CSIDL_APPDATA = 26
CSIDL_PRINTHOOD = 27
CSIDL_LOCAL_APPDATA = 28
CSIDL_ALTSTARTUP = 29
CSIDL_COMMON_ALTSTARTUP = 30
CSIDL_COMMON_FAVORITES = 31
CSIDL_INTERNET_CACHE = 32
CSIDL_COOKIES = 33
CSIDL_HISTORY = 34
CSIDL_COMMON_APPDATA = 35
CSIDL_WINDOWS = 36
CSIDL_SYSTEM = 37
CSIDL_PROGRAM_FILES = 38
CSIDL_MYPICTURES = 39
CSIDL_PROFILE = 40
CSIDL_SYSTEMX86 = 41
CSIDL_PROGRAM_FILESX86 = 42
CSIDL_PROGRAM_FILES_COMMON = 43
CSIDL_PROGRAM_FILES_COMMONX86 = 44
CSIDL_COMMON_TEMPLATES = 45
CSIDL_COMMON_DOCUMENTS = 46
CSIDL_COMMON_ADMINTOOLS = 47
CSIDL_ADMINTOOLS = 48
CSIDL_CONNECTIONS = 49
CSIDL_COMMON_MUSIC = 53
CSIDL_COMMON_PICTURES = 54
CSIDL_COMMON_VIDEO = 55
CSIDL_RESOURCES = 56
CSIDL_RESOURCES_LOCALIZED = 57
CSIDL_COMMON_OEM_LINKS = 58
CSIDL_CDBURN_AREA = 59
# 60 unused
CSIDL_COMPUTERSNEARME = 61

BIF_RETURNONLYFSDIRS = 1
BIF_DONTGOBELOWDOMAIN = 2
BIF_STATUSTEXT = 4
BIF_RETURNFSANCESTORS = 8
BIF_EDITBOX = 16
BIF_VALIDATE = 32
BIF_BROWSEFORCOMPUTER = 4096
BIF_BROWSEFORPRINTER = 8192
BIF_BROWSEINCLUDEFILES = 16384
BFFM_INITIALIZED = 1
BFFM_SELCHANGED = 2
BFFM_VALIDATEFAILEDA = 3
BFFM_VALIDATEFAILEDW = 4
BFFM_SETSTATUSTEXTA = WM_USER + 100
BFFM_ENABLEOK = WM_USER + 101
BFFM_SETSELECTIONA = WM_USER + 102
BFFM_SETSELECTIONW = WM_USER + 103
BFFM_SETSTATUSTEXTW = WM_USER + 104
BFFM_SETSTATUSTEXT = BFFM_SETSTATUSTEXTA
BFFM_SETSELECTION = BFFM_SETSELECTIONA
BFFM_VALIDATEFAILED = BFFM_VALIDATEFAILEDA
SFGAO_CANCOPY = DROPEFFECT_COPY
SFGAO_CANMOVE = DROPEFFECT_MOVE
SFGAO_CANLINK = DROPEFFECT_LINK
SFGAO_CANRENAME = 16
SFGAO_CANDELETE = 32
SFGAO_HASPROPSHEET = 64
SFGAO_DROPTARGET = 256
SFGAO_CAPABILITYMASK = 375
SFGAO_LINK = 65536
SFGAO_SHARE = 131072
SFGAO_READONLY = 262144
SFGAO_GHOSTED = 524288
SFGAO_HIDDEN = 524288
SFGAO_DISPLAYATTRMASK = 983040
SFGAO_FILESYSANCESTOR = 268435456
SFGAO_FOLDER = 536870912
SFGAO_FILESYSTEM = 1073741824
SFGAO_HASSUBFOLDER = -2147483648
SFGAO_CONTENTSMASK = -2147483648
SFGAO_VALIDATE = 16777216
SFGAO_REMOVABLE = 33554432
SFGAO_COMPRESSED = 67108864
SFGAO_BROWSABLE = 134217728
SFGAO_NONENUMERATED = 1048576
SFGAO_NEWCONTENT = 2097152
SFGAO_STORAGE = 8
DWFRF_NORMAL = 0
DWFRF_DELETECONFIGDATA = 1
DWFAF_HIDDEN = 1
CFSTR_SHELLIDLIST = "Shell IDList Array"
CFSTR_SHELLIDLISTOFFSET = "Shell Object Offsets"
CFSTR_NETRESOURCES = "Net Resource"
CFSTR_FILEDESCRIPTORA = "FileGroupDescriptor"
CFSTR_FILEDESCRIPTORW = "FileGroupDescriptorW"
CFSTR_FILECONTENTS = "FileContents"
CFSTR_FILENAMEA = "FileName"
CFSTR_FILENAMEW = "FileNameW"
CFSTR_PRINTERGROUP = "PrinterFriendlyName"
CFSTR_FILENAMEMAPA = "FileNameMap"
CFSTR_FILENAMEMAPW = "FileNameMapW"
CFSTR_SHELLURL = "UniformResourceLocator"
CFSTR_INETURLA = CFSTR_SHELLURL
CFSTR_INETURLW = "UniformResourceLocatorW"
CFSTR_PREFERREDDROPEFFECT = "Preferred DropEffect"
CFSTR_PERFORMEDDROPEFFECT = "Performed DropEffect"
CFSTR_PASTESUCCEEDED = "Paste Succeeded"
CFSTR_INDRAGLOOP = "InShellDragLoop"
CFSTR_DRAGCONTEXT = "DragContext"
CFSTR_MOUNTEDVOLUME = "MountedVolume"
CFSTR_PERSISTEDDATAOBJECT = "PersistedDataObject"
CFSTR_TARGETCLSID = "TargetCLSID"
CFSTR_LOGICALPERFORMEDDROPEFFECT = "Logical Performed DropEffect"
CFSTR_AUTOPLAY_SHELLIDLISTS = "Autoplay Enumerated IDList Array"
CFSTR_FILEDESCRIPTOR = CFSTR_FILEDESCRIPTORA
CFSTR_FILENAME = CFSTR_FILENAMEA
CFSTR_FILENAMEMAP = CFSTR_FILENAMEMAPA
DVASPECT_SHORTNAME = 2
SHCNE_RENAMEITEM = 1
SHCNE_CREATE = 2
SHCNE_DELETE = 4
SHCNE_MKDIR = 8
SHCNE_RMDIR = 16
SHCNE_MEDIAINSERTED = 32
SHCNE_MEDIAREMOVED = 64
SHCNE_DRIVEREMOVED = 128
SHCNE_DRIVEADD = 256
SHCNE_NETSHARE = 512
SHCNE_NETUNSHARE = 1024
SHCNE_ATTRIBUTES = 2048
SHCNE_UPDATEDIR = 4096
SHCNE_UPDATEITEM = 8192
SHCNE_SERVERDISCONNECT = 16384
SHCNE_UPDATEIMAGE = 32768
SHCNE_DRIVEADDGUI = 65536
SHCNE_RENAMEFOLDER = 131072
SHCNE_FREESPACE = 262144
SHCNE_EXTENDED_EVENT = 67108864
SHCNE_ASSOCCHANGED = 134217728
SHCNE_DISKEVENTS = 145439
SHCNE_GLOBALEVENTS = 201687520
SHCNE_ALLEVENTS = 2147483647
SHCNE_INTERRUPT = -2147483648
SHCNEE_ORDERCHANGED = 2
SHCNF_IDLIST = 0
SHCNF_PATHA = 1
SHCNF_PRINTERA = 2
SHCNF_DWORD = 3
SHCNF_PATHW = 5
SHCNF_PRINTERW = 6
SHCNF_TYPE = 255
SHCNF_FLUSH = 4096
SHCNF_FLUSHNOWAIT = 8192
SHCNF_PATH = SHCNF_PATHA
SHCNF_PRINTER = SHCNF_PRINTERA
QIF_CACHED = 1
QIF_DONTEXPANDFOLDER = 2

# ShellWindowFindWindowOptions
SWFO_NEEDDISPATCH = 1
SWFO_INCLUDEPENDING = 2
SWFO_COOKIEPASSED = 4

# ShellWindowTypeConstants
SWC_EXPLORER = 0
SWC_BROWSER = 1
SWC_3RDPARTY = 2
SWC_CALLBACK = 4
SWC_DESKTOP = 8

# SHARD enum for SHAddToRecentDocs
SHARD_PIDL = 1
SHARD_PATHA = 2
SHARD_PATHW = 3
SHARD_APPIDINFO = 4
SHARD_APPIDINFOIDLIST = 5
SHARD_LINK = 6
SHARD_APPIDINFOLINK = 7
SHARD_SHELLITEM = 8
## SHARD_PATH = SHARD_PATHW
SHARD_PATH = SHARD_PATHA

SHGDFIL_FINDDATA = 1
SHGDFIL_NETRESOURCE = 2
SHGDFIL_DESCRIPTIONID = 3
SHDID_ROOT_REGITEM = 1
SHDID_FS_FILE = 2
SHDID_FS_DIRECTORY = 3
SHDID_FS_OTHER = 4
SHDID_COMPUTER_DRIVE35 = 5
SHDID_COMPUTER_DRIVE525 = 6
SHDID_COMPUTER_REMOVABLE = 7
SHDID_COMPUTER_FIXED = 8
SHDID_COMPUTER_NETDRIVE = 9
SHDID_COMPUTER_CDROM = 10
SHDID_COMPUTER_RAMDISK = 11
SHDID_COMPUTER_OTHER = 12
SHDID_NET_DOMAIN = 13
SHDID_NET_SERVER = 14
SHDID_NET_SHARE = 15
SHDID_NET_RESTOFNET = 16
SHDID_NET_OTHER = 17
PID_IS_URL = 2
PID_IS_NAME = 4
PID_IS_WORKINGDIR = 5
PID_IS_HOTKEY = 6
PID_IS_SHOWCMD = 7
PID_IS_ICONINDEX = 8
PID_IS_ICONFILE = 9
PID_IS_WHATSNEW = 10
PID_IS_AUTHOR = 11
PID_IS_DESCRIPTION = 12
PID_IS_COMMENT = 13
PID_INTSITE_WHATSNEW = 2
PID_INTSITE_AUTHOR = 3
PID_INTSITE_LASTVISIT = 4
PID_INTSITE_LASTMOD = 5
PID_INTSITE_VISITCOUNT = 6
PID_INTSITE_DESCRIPTION = 7
PID_INTSITE_COMMENT = 8
PID_INTSITE_FLAGS = 9
PID_INTSITE_CONTENTLEN = 10
PID_INTSITE_CONTENTCODE = 11
PID_INTSITE_RECURSE = 12
PID_INTSITE_WATCH = 13
PID_INTSITE_SUBSCRIPTION = 14
PID_INTSITE_URL = 15
PID_INTSITE_TITLE = 16
PID_INTSITE_CODEPAGE = 18
PID_INTSITE_TRACKING = 19
PIDISF_RECENTLYCHANGED = 1
PIDISF_CACHEDSTICKY = 2
PIDISF_CACHEIMAGES = 16
PIDISF_FOLLOWALLLINKS = 32
PIDISM_GLOBAL = 0
PIDISM_WATCH = 1
PIDISM_DONTWATCH = 2
SSF_SHOWALLOBJECTS = 1
SSF_SHOWEXTENSIONS = 2
SSF_SHOWCOMPCOLOR = 8
SSF_SHOWSYSFILES = 32
SSF_DOUBLECLICKINWEBVIEW = 128
SSF_SHOWATTRIBCOL = 256
SSF_DESKTOPHTML = 512
SSF_WIN95CLASSIC = 1024
SSF_DONTPRETTYPATH = 2048
SSF_SHOWINFOTIP = 8192
SSF_MAPNETDRVBUTTON = 4096
SSF_NOCONFIRMRECYCLE = 32768
SSF_HIDEICONS = 16384

ABM_NEW = 0
ABM_REMOVE = 1
ABM_QUERYPOS = 2
ABM_SETPOS = 3
ABM_GETSTATE = 4
ABM_GETTASKBARPOS = 5
ABM_ACTIVATE = 6
ABM_GETAUTOHIDEBAR = 7
ABM_SETAUTOHIDEBAR = 8
ABM_WINDOWPOSCHANGED = 9
ABN_STATECHANGE = 0
ABN_POSCHANGED = 1
ABN_FULLSCREENAPP = 2
ABN_WINDOWARRANGE = 3
ABS_AUTOHIDE = 1
ABS_ALWAYSONTOP = 2
ABE_LEFT = 0
ABE_TOP = 1
ABE_RIGHT = 2
ABE_BOTTOM = 3


def EIRESID(x):
    return -1 * (int)(x)


# Some manually added ones

SHCONTF_FOLDERS = 32  # for shell browser
SHCONTF_NONFOLDERS = 64  # for default view
SHCONTF_INCLUDEHIDDEN = 128  # for hidden/system objects
SHCONTF_INIT_ON_FIRST_NEXT = 256
SHCONTF_NETPRINTERSRCH = 512
SHCONTF_SHAREABLE = 1024
SHCONTF_STORAGE = 2048

SHGDN_NORMAL = 0  # default (display purpose)
SHGDN_INFOLDER = 1  # displayed under a folder (relative)
SHGDN_FOREDITING = 4096  # for in-place editing
SHGDN_INCLUDE_NONFILESYS = 8192  # if not set, display names for shell name space items that are not in the file system will fail.
SHGDN_FORADDRESSBAR = 16384  # for displaying in the address (drives dropdown) bar
SHGDN_FORPARSING = 32768  # for ParseDisplayName or path

BFO_NONE = 0
BFO_BROWSER_PERSIST_SETTINGS = 1
BFO_RENAME_FOLDER_OPTIONS_TOINTERNET = 2
BFO_BOTH_OPTIONS = 4
BIF_PREFER_INTERNET_SHORTCUT = 8
BFO_BROWSE_NO_IN_NEW_PROCESS = 16
BFO_ENABLE_HYPERLINK_TRACKING = 32
BFO_USE_IE_OFFLINE_SUPPORT = 64
BFO_SUBSTITUE_INTERNET_START_PAGE = 128
BFO_USE_IE_LOGOBANDING = 256
BFO_ADD_IE_TOCAPTIONBAR = 512
BFO_USE_DIALUP_REF = 1024
BFO_USE_IE_TOOLBAR = 2048
BFO_NO_PARENT_FOLDER_SUPPORT = 4096
BFO_NO_REOPEN_NEXT_RESTART = 8192
BFO_GO_HOME_PAGE = 16384
BFO_PREFER_IEPROCESS = 32768
BFO_SHOW_NAVIGATION_CANCELLED = 65536
BFO_QUERY_ALL = -1
# From ShlGuid.h
PID_FINDDATA = 0
PID_NETRESOURCE = 1
PID_DESCRIPTIONID = 2
PID_WHICHFOLDER = 3
PID_NETWORKLOCATION = 4
PID_COMPUTERNAME = 5
PID_DISPLACED_FROM = 2
PID_DISPLACED_DATE = 3
PID_SYNC_COPY_IN = 2
PID_MISC_STATUS = 2
PID_MISC_ACCESSCOUNT = 3
PID_MISC_OWNER = 4
PID_HTMLINFOTIPFILE = 5
PID_MISC_PICS = 6
PID_DISPLAY_PROPERTIES = 0
PID_INTROTEXT = 1
PIDSI_ARTIST = 2
PIDSI_SONGTITLE = 3
PIDSI_ALBUM = 4
PIDSI_YEAR = 5
PIDSI_COMMENT = 6
PIDSI_TRACK = 7
PIDSI_GENRE = 11
PIDSI_LYRICS = 12
PIDDRSI_PROTECTED = 2
PIDDRSI_DESCRIPTION = 3
PIDDRSI_PLAYCOUNT = 4
PIDDRSI_PLAYSTARTS = 5
PIDDRSI_PLAYEXPIRES = 6
PIDVSI_STREAM_NAME = 2
PIDVSI_FRAME_WIDTH = 3
PIDVSI_FRAME_HEIGHT = 4
PIDVSI_TIMELENGTH = 7
PIDVSI_FRAME_COUNT = 5
PIDVSI_FRAME_RATE = 6
PIDVSI_DATA_RATE = 8
PIDVSI_SAMPLE_SIZE = 9
PIDVSI_COMPRESSION = 10
PIDVSI_STREAM_NUMBER = 11
PIDASI_FORMAT = 2
PIDASI_TIMELENGTH = 3
PIDASI_AVG_DATA_RATE = 4
PIDASI_SAMPLE_RATE = 5
PIDASI_SAMPLE_SIZE = 6
PIDASI_CHANNEL_COUNT = 7
PIDASI_STREAM_NUMBER = 8
PIDASI_STREAM_NAME = 9
PIDASI_COMPRESSION = 10
PID_CONTROLPANEL_CATEGORY = 2
PID_VOLUME_FREE = 2
PID_VOLUME_CAPACITY = 3
PID_VOLUME_FILESYSTEM = 4
PID_SHARE_CSC_STATUS = 2
PID_LINK_TARGET = 2
PID_QUERY_RANK = 2
# From PropIdl.h
PROPSETFLAG_DEFAULT = 0
PROPSETFLAG_NONSIMPLE = 1
PROPSETFLAG_ANSI = 2
PROPSETFLAG_UNBUFFERED = 4
PROPSETFLAG_CASE_SENSITIVE = 8
PROPSET_BEHAVIOR_CASE_SENSITIVE = 1
PID_DICTIONARY = 0
PID_CODEPAGE = 1
PID_FIRST_USABLE = 2
PID_FIRST_NAME_DEFAULT = 4095
PID_LOCALE = -2147483648
PID_MODIFY_TIME = -2147483647
PID_SECURITY = -2147483646
PID_BEHAVIOR = -2147483645
PID_ILLEGAL = -1
PID_MIN_READONLY = -2147483648
PID_MAX_READONLY = -1073741825
PIDDI_THUMBNAIL = 2
PIDSI_TITLE = 2
PIDSI_SUBJECT = 3
PIDSI_AUTHOR = 4
PIDSI_KEYWORDS = 5
PIDSI_COMMENTS = 6
PIDSI_TEMPLATE = 7
PIDSI_LASTAUTHOR = 8
PIDSI_REVNUMBER = 9
PIDSI_EDITTIME = 10
PIDSI_LASTPRINTED = 11
PIDSI_CREATE_DTM = 12
PIDSI_LASTSAVE_DTM = 13
PIDSI_PAGECOUNT = 14
PIDSI_WORDCOUNT = 15
PIDSI_CHARCOUNT = 16
PIDSI_THUMBNAIL = 17
PIDSI_APPNAME = 18
PIDSI_DOC_SECURITY = 19
PIDDSI_CATEGORY = 2
PIDDSI_PRESFORMAT = 3
PIDDSI_BYTECOUNT = 4
PIDDSI_LINECOUNT = 5
PIDDSI_PARCOUNT = 6
PIDDSI_SLIDECOUNT = 7
PIDDSI_NOTECOUNT = 8
PIDDSI_HIDDENCOUNT = 9
PIDDSI_MMCLIPCOUNT = 10
PIDDSI_SCALE = 11
PIDDSI_HEADINGPAIR = 12
PIDDSI_DOCPARTS = 13
PIDDSI_MANAGER = 14
PIDDSI_COMPANY = 15
PIDDSI_LINKSDIRTY = 16
PIDMSI_EDITOR = 2
PIDMSI_SUPPLIER = 3
PIDMSI_SOURCE = 4
PIDMSI_SEQUENCE_NO = 5
PIDMSI_PROJECT = 6
PIDMSI_STATUS = 7
PIDMSI_OWNER = 8
PIDMSI_RATING = 9
PIDMSI_PRODUCTION = 10
PIDMSI_COPYRIGHT = 11
PRSPEC_INVALID = -1
PRSPEC_LPWSTR = 0
PRSPEC_PROPID = 1
# From ShObjIdl.h
SHCIDS_ALLFIELDS = -2147483648
SHCIDS_CANONICALONLY = 268435456
SHCIDS_BITMASK = -65536
SHCIDS_COLUMNMASK = 65535
SFGAO_CANMONIKER = 4194304
SFGAO_HASSTORAGE = 4194304
SFGAO_STREAM = 4194304
SFGAO_STORAGEANCESTOR = 8388608
SFGAO_STORAGECAPMASK = 1891958792

MAXPROPPAGES = 100
PSP_DEFAULT = 0
PSP_DLGINDIRECT = 1
PSP_USEHICON = 2
PSP_USEICONID = 4
PSP_USETITLE = 8
PSP_RTLREADING = 16
PSP_HASHELP = 32
PSP_USEREFPARENT = 64
PSP_USECALLBACK = 128
PSP_PREMATURE = 1024
PSP_HIDEHEADER = 2048
PSP_USEHEADERTITLE = 4096
PSP_USEHEADERSUBTITLE = 8192
PSP_USEFUSIONCONTEXT = 16384
PSPCB_ADDREF = 0
PSPCB_RELEASE = 1
PSPCB_CREATE = 2

PSH_DEFAULT = 0
PSH_PROPTITLE = 1
PSH_USEHICON = 2
PSH_USEICONID = 4
PSH_PROPSHEETPAGE = 8
PSH_WIZARDHASFINISH = 16
PSH_WIZARD = 32
PSH_USEPSTARTPAGE = 64
PSH_NOAPPLYNOW = 128
PSH_USECALLBACK = 256
PSH_HASHELP = 512
PSH_MODELESS = 1024
PSH_RTLREADING = 2048
PSH_WIZARDCONTEXTHELP = 4096
PSH_WIZARD97 = 16777216
PSH_WATERMARK = 32768
PSH_USEHBMWATERMARK = 65536
PSH_USEHPLWATERMARK = 131072
PSH_STRETCHWATERMARK = 262144
PSH_HEADER = 524288
PSH_USEHBMHEADER = 1048576
PSH_USEPAGELANG = 2097152
PSH_WIZARD_LITE = 4194304
PSH_NOCONTEXTHELP = 33554432

PSCB_INITIALIZED = 1
PSCB_PRECREATE = 2
PSCB_BUTTONPRESSED = 3
PSNRET_NOERROR = 0
PSNRET_INVALID = 1
PSNRET_INVALID_NOCHANGEPAGE = 2
PSNRET_MESSAGEHANDLED = 3

PSWIZB_BACK = 1
PSWIZB_NEXT = 2
PSWIZB_FINISH = 4
PSWIZB_DISABLEDFINISH = 8
PSBTN_BACK = 0
PSBTN_NEXT = 1
PSBTN_FINISH = 2
PSBTN_OK = 3
PSBTN_APPLYNOW = 4
PSBTN_CANCEL = 5
PSBTN_HELP = 6
PSBTN_MAX = 6

ID_PSRESTARTWINDOWS = 2
ID_PSREBOOTSYSTEM = ID_PSRESTARTWINDOWS | 1
WIZ_CXDLG = 276
WIZ_CYDLG = 140
WIZ_CXBMP = 80
WIZ_BODYX = 92
WIZ_BODYCX = 184
PROP_SM_CXDLG = 212
PROP_SM_CYDLG = 188
PROP_MED_CXDLG = 227
PROP_MED_CYDLG = 215
PROP_LG_CXDLG = 252
PROP_LG_CYDLG = 218
ISOLATION_AWARE_USE_STATIC_LIBRARY = 0
ISOLATION_AWARE_BUILD_STATIC_LIBRARY = 0

SHCOLSTATE_TYPE_STR = 1
SHCOLSTATE_TYPE_INT = 2
SHCOLSTATE_TYPE_DATE = 3
SHCOLSTATE_TYPEMASK = 15
SHCOLSTATE_ONBYDEFAULT = 16
SHCOLSTATE_SLOW = 32
SHCOLSTATE_EXTENDED = 64
SHCOLSTATE_SECONDARYUI = 128
SHCOLSTATE_HIDDEN = 256
SHCOLSTATE_PREFER_VARCMP = 512

FWF_AUTOARRANGE = 1
FWF_ABBREVIATEDNAMES = 2
FWF_SNAPTOGRID = 4
FWF_OWNERDATA = 8
FWF_BESTFITWINDOW = 16
FWF_DESKTOP = 32
FWF_SINGLESEL = 64
FWF_NOSUBFOLDERS = 128
FWF_TRANSPARENT = 256
FWF_NOCLIENTEDGE = 512
FWF_NOSCROLL = 1024
FWF_ALIGNLEFT = 2048
FWF_NOICONS = 4096
FWF_SHOWSELALWAYS = 8192
FWF_NOVISIBLE = 16384
FWF_SINGLECLICKACTIVATE = 32768
FWF_NOWEBVIEW = 65536
FWF_HIDEFILENAMES = 131072
FWF_CHECKSELECT = 262144

FVM_FIRST = 1
FVM_ICON = 1
FVM_SMALLICON = 2
FVM_LIST = 3
FVM_DETAILS = 4
FVM_THUMBNAIL = 5
FVM_TILE = 6
FVM_THUMBSTRIP = 7

SVUIA_DEACTIVATE = 0
SVUIA_ACTIVATE_NOFOCUS = 1
SVUIA_ACTIVATE_FOCUS = 2
SVUIA_INPLACEACTIVATE = 3

# SHChangeNotifyRegister flags
SHCNRF_InterruptLevel = 1
SHCNRF_ShellLevel = 2
SHCNRF_RecursiveInterrupt = 4096
SHCNRF_NewDelivery = 32768

FD_CLSID = 0x0001
FD_SIZEPOINT = 0x0002
FD_ATTRIBUTES = 0x0004
FD_CREATETIME = 0x0008
FD_ACCESSTIME = 0x0010
FD_WRITESTIME = 0x0020
FD_FILESIZE = 0x0040
FD_PROGRESSUI = 0x4000
FD_LINKUI = 0x8000

# shlwapi stuff
ASSOCF_INIT_NOREMAPCLSID = 0x00000001  #  do not remap clsids to progids
ASSOCF_INIT_BYEXENAME = 0x00000002  # executable is being passed in
ASSOCF_OPEN_BYEXENAME = 0x00000002  # executable is being passed in
ASSOCF_INIT_DEFAULTTOSTAR = 0x00000004  # treat "*" as the BaseClass
ASSOCF_INIT_DEFAULTTOFOLDER = 0x00000008  # treat "Folder" as the BaseClass
ASSOCF_NOUSERSETTINGS = 0x00000010  #  don't use HKCU
ASSOCF_NOTRUNCATE = 0x00000020  # don't truncate the return string
ASSOCF_VERIFY = 0x00000040  #  verify data is accurate (DISK HITS)
ASSOCF_REMAPRUNDLL = 0x00000080  # actually gets info about rundlls target if applicable
ASSOCF_NOFIXUPS = 0x00000100  # attempt to fix errors if found
ASSOCF_IGNOREBASECLASS = 0x00000200  # don't recurse into the baseclass

ASSOCSTR_COMMAND = 1  # shell\verb\command string
ASSOCSTR_EXECUTABLE = 2  # the executable part of command string
ASSOCSTR_FRIENDLYDOCNAME = 3  # friendly name of the document type
ASSOCSTR_FRIENDLYAPPNAME = 4  # friendly name of executable
ASSOCSTR_NOOPEN = 5  # noopen value
ASSOCSTR_SHELLNEWVALUE = 6  # query values under the shellnew key
ASSOCSTR_DDECOMMAND = 7  # template for DDE commands
ASSOCSTR_DDEIFEXEC = 8  # DDECOMMAND to use if just create a process
ASSOCSTR_DDEAPPLICATION = 9  # Application name in DDE broadcast
ASSOCSTR_DDETOPIC = 10  # Topic Name in DDE broadcast
ASSOCSTR_INFOTIP = (
    11  # info tip for an item, or list of properties to create info tip from
)
ASSOCSTR_QUICKTIP = 12  # same as ASSOCSTR_INFOTIP, except, this list contains only quickly retrievable properties
ASSOCSTR_TILEINFO = (
    13  # similar to ASSOCSTR_INFOTIP - lists important properties for tileview
)
ASSOCSTR_CONTENTTYPE = 14  # MIME Content type
ASSOCSTR_DEFAULTICON = 15  # Default icon source
ASSOCSTR_SHELLEXTENSION = (
    16  # Guid string pointing to the Shellex\Shellextensionhandler value.
)

ASSOCKEY_SHELLEXECCLASS = 1  # the key that should be passed to ShellExec(hkeyClass)
ASSOCKEY_APP = 2  # the "Application" key for the association
ASSOCKEY_CLASS = 3  # the progid or class key
ASSOCKEY_BASECLASS = 4  # the BaseClass key

ASSOCDATA_MSIDESCRIPTOR = 1  # Component Descriptor to pass to MSI APIs
ASSOCDATA_NOACTIVATEHANDLER = 2  # restrict attempts to activate window
ASSOCDATA_QUERYCLASSSTORE = 3  # should check with the NT Class Store
ASSOCDATA_HASPERUSERASSOC = 4  # defaults to user specified association
ASSOCDATA_EDITFLAGS = 5  # Edit flags.
ASSOCDATA_VALUE = 6  # use pszExtra as the Value name

# flags used with SHGetViewStatePropertyBag
SHGVSPB_PERUSER = 1
SHGVSPB_ALLUSERS = 2
SHGVSPB_PERFOLDER = 4
SHGVSPB_ALLFOLDERS = 8
SHGVSPB_INHERIT = 16
SHGVSPB_ROAM = 32
SHGVSPB_NOAUTODEFAULTS = 0x80000000
SHGVSPB_FOLDER = SHGVSPB_PERUSER | SHGVSPB_PERFOLDER
SHGVSPB_FOLDERNODEFAULTS = SHGVSPB_PERUSER | SHGVSPB_PERFOLDER | SHGVSPB_NOAUTODEFAULTS
SHGVSPB_USERDEFAULTS = SHGVSPB_PERUSER | SHGVSPB_ALLFOLDERS
SHGVSPB_GLOBALDEAFAULTS = SHGVSPB_ALLUSERS | SHGVSPB_ALLFOLDERS

# IDeskband and related
DBIM_MINSIZE = 0x0001
DBIM_MAXSIZE = 0x0002
DBIM_INTEGRAL = 0x0004
DBIM_ACTUAL = 0x0008
DBIM_TITLE = 0x0010
DBIM_MODEFLAGS = 0x0020
DBIM_BKCOLOR = 0x0040

DBIMF_NORMAL = 0x0000
DBIMF_VARIABLEHEIGHT = 0x0008
DBIMF_DEBOSSED = 0x0020
DBIMF_BKCOLOR = 0x0040

DBIF_VIEWMODE_NORMAL = 0x0000
DBIF_VIEWMODE_VERTICAL = 0x0001
DBIF_VIEWMODE_FLOATING = 0x0002
DBIF_VIEWMODE_TRANSPARENT = 0x0004

# Message types used with SHShellFolderView_Message
SFVM_REARRANGE = 1
SFVM_ADDOBJECT = 3
SFVM_REMOVEOBJECT = 6
SFVM_UPDATEOBJECT = 7
SFVM_GETSELECTEDOBJECTS = 9
SFVM_SETITEMPOS = 14
SFVM_SETCLIPBOARD = 16
SFVM_SETPOINTS = 23

# SHELL_LINK_DATA_FLAGS enum, used with IShellLinkDatalist
SLDF_HAS_ID_LIST = 1
SLDF_HAS_LINK_INFO = 2
SLDF_HAS_NAME = 4
SLDF_HAS_RELPATH = 8
SLDF_HAS_WORKINGDIR = 16
SLDF_HAS_ARGS = 32
SLDF_HAS_ICONLOCATION = 64
SLDF_UNICODE = 128
SLDF_FORCE_NO_LINKINFO = 256
SLDF_HAS_EXP_SZ = 512
SLDF_RUN_IN_SEPARATE = 1024
SLDF_HAS_LOGO3ID = 2048
SLDF_HAS_DARWINID = 4096
SLDF_RUNAS_USER = 8192
SLDF_NO_PIDL_ALIAS = 32768
SLDF_FORCE_UNCNAME = 65536
SLDF_HAS_EXP_ICON_SZ = 16384
SLDF_RUN_WITH_SHIMLAYER = 131072
SLDF_RESERVED = 2147483648

# IShellLinkDataList data block signatures
EXP_SPECIAL_FOLDER_SIG = 2684354565
NT_CONSOLE_PROPS_SIG = 2684354562
NT_FE_CONSOLE_PROPS_SIG = 2684354564
EXP_DARWIN_ID_SIG = 2684354566
EXP_LOGO3_ID_SIG = 2684354567
EXP_SZ_ICON_SIG = 2684354567
EXP_SZ_LINK_SIG = 2684354561

# IURL_SETURL_FLAGS enum, used with PyIUniformResourceLocator.SetURL
IURL_SETURL_FL_GUESS_PROTOCOL = 1
IURL_SETURL_FL_USE_DEFAULT_PROTOCOL = 2

# IURL_INVOKECOMMAND_FLAGS enum, used with PyIUniformResourceLocator.InvokeCommand
IURL_INVOKECOMMAND_FL_ALLOW_UI = 1
IURL_INVOKECOMMAND_FL_USE_DEFAULT_VERB = 2
IURL_INVOKECOMMAND_FL_DDEWAIT = 4

## constants used with IActiveDesktop
# COMPONENT.ComponentType
COMP_TYPE_HTMLDOC = 0
COMP_TYPE_PICTURE = 1
COMP_TYPE_WEBSITE = 2
COMP_TYPE_CONTROL = 3
COMP_TYPE_CFHTML = 4
COMP_TYPE_MAX = 4
# COMPONENT.CurItemState
IS_NORMAL = 1
IS_FULLSCREEN = 2
IS_SPLIT = 4
IS_VALIDSIZESTATEBITS = IS_NORMAL | IS_SPLIT | IS_FULLSCREEN
IS_VALIDSTATEBITS = IS_NORMAL | IS_SPLIT | IS_FULLSCREEN | 0x80000000 | 0x40000000
# IActiveDesktop.ApplyChanges Flags
AD_APPLY_SAVE = 1
AD_APPLY_HTMLGEN = 2
AD_APPLY_REFRESH = 4
AD_APPLY_ALL = AD_APPLY_SAVE | AD_APPLY_HTMLGEN | AD_APPLY_REFRESH
AD_APPLY_FORCE = 8
AD_APPLY_BUFFERED_REFRESH = 16
AD_APPLY_DYNAMICREFRESH = 32
# Wallpaper styles used with GetWallpaper and SetWallpaper
WPSTYLE_CENTER = 0
WPSTYLE_TILE = 1
WPSTYLE_STRETCH = 2
WPSTYLE_MAX = 3
# ModifyDesktopItem flags
COMP_ELEM_TYPE = 0x00000001
COMP_ELEM_CHECKED = 0x00000002
COMP_ELEM_DIRTY = 0x00000004
COMP_ELEM_NOSCROLL = 0x00000008
COMP_ELEM_POS_LEFT = 0x00000010
COMP_ELEM_POS_TOP = 0x00000020
COMP_ELEM_SIZE_WIDTH = 0x00000040
COMP_ELEM_SIZE_HEIGHT = 0x00000080
COMP_ELEM_POS_ZINDEX = 0x00000100
COMP_ELEM_SOURCE = 0x00000200
COMP_ELEM_FRIENDLYNAME = 0x00000400
COMP_ELEM_SUBSCRIBEDURL = 0x00000800
COMP_ELEM_ORIGINAL_CSI = 0x00001000
COMP_ELEM_RESTORED_CSI = 0x00002000
COMP_ELEM_CURITEMSTATE = 0x00004000
COMP_ELEM_ALL = (
    COMP_ELEM_TYPE
    | COMP_ELEM_CHECKED
    | COMP_ELEM_DIRTY
    | COMP_ELEM_NOSCROLL
    | COMP_ELEM_POS_LEFT
    | COMP_ELEM_SIZE_WIDTH
    | COMP_ELEM_SIZE_HEIGHT
    | COMP_ELEM_POS_ZINDEX
    | COMP_ELEM_SOURCE
    | COMP_ELEM_FRIENDLYNAME
    | COMP_ELEM_POS_TOP
    | COMP_ELEM_SUBSCRIBEDURL
    | COMP_ELEM_ORIGINAL_CSI
    | COMP_ELEM_RESTORED_CSI
    | COMP_ELEM_CURITEMSTATE
)

DTI_ADDUI_DEFAULT = 0
DTI_ADDUI_DISPSUBWIZARD = 1
DTI_ADDUI_POSITIONITEM = 2
ADDURL_SILENT = 0x0001
COMPONENT_TOP = 0x3FFFFFFF
COMPONENT_DEFAULT_LEFT = 0xFFFF
COMPONENT_DEFAULT_TOP = 0xFFFF

SSM_CLEAR = 0
SSM_SET = 1
SSM_REFRESH = 2
SSM_UPDATE = 4

SCHEME_DISPLAY = 0x0001
SCHEME_EDIT = 0x0002
SCHEME_LOCAL = 0x0004
SCHEME_GLOBAL = 0x0008
SCHEME_REFRESH = 0x0010
SCHEME_UPDATE = 0x0020
SCHEME_DONOTUSE = 0x0040
SCHEME_CREATE = 0x0080

GADOF_DIRTY = 1

# From EmptyVC.h
EVCF_HASSETTINGS = 0x0001
EVCF_ENABLEBYDEFAULT = 0x0002
EVCF_REMOVEFROMLIST = 0x0004
EVCF_ENABLEBYDEFAULT_AUTO = 0x0008
EVCF_DONTSHOWIFZERO = 0x0010
EVCF_SETTINGSMODE = 0x0020
EVCF_OUTOFDISKSPACE = 0x0040
EVCCBF_LASTNOTIFICATION = 0x0001

# ShObjIdl.h IExplorer* related
EBO_NONE = 0
EBO_NAVIGATEONCE = 0x1
EBO_SHOWFRAMES = 0x2
EBO_ALWAYSNAVIGATE = 0x4
EBO_NOTRAVELLOG = 0x8
EBO_NOWRAPPERWINDOW = 0x10
EBF_NONE = 0
EBF_SELECTFROMDATAOBJECT = 0x100
EBF_NODROPTARGET = 0x200
ECS_ENABLED = 0
ECS_DISABLED = 0x1
ECS_HIDDEN = 0x2
ECS_CHECKBOX = 0x4
ECS_CHECKED = 0x8

ECF_HASSUBCOMMANDS = 0x1
ECF_HASSPLITBUTTON = 0x2
ECF_HIDELABEL = 0x4
ECF_ISSEPARATOR = 0x8
ECF_HASLUASHIELD = 0x10

SIATTRIBFLAGS_AND = 0x1
SIATTRIBFLAGS_OR = 0x2
SIATTRIBFLAGS_APPCOMPAT = 0x3
SIATTRIBFLAGS_MASK = 0x3

SIGDN_NORMALDISPLAY = 0
SIGDN_PARENTRELATIVEPARSING = -2147385343  ## 0x80018001
SIGDN_DESKTOPABSOLUTEPARSING = -2147319808  ## 0x80028000
SIGDN_PARENTRELATIVEEDITING = -2147282943  ## 0x80031001
SIGDN_DESKTOPABSOLUTEEDITING = -2147172352  ## 0x8004c000
SIGDN_FILESYSPATH = -2147123200  ## 0x80058000
SIGDN_URL = -2147057664  ## 0x80068000
SIGDN_PARENTRELATIVEFORADDRESSBAR = -2146975743  ## 0x8007c001,
SIGDN_PARENTRELATIVE = -2146959359  ## 0x80080001

SICHINT_DISPLAY = (0,)
SICHINT_ALLFIELDS = -2147483648  ## 0x80000000
SICHINT_CANONICAL = 0x10000000

ASSOCCLASS_SHELL_KEY = 0
ASSOCCLASS_PROGID_KEY = 1  # hkeyClass
ASSOCCLASS_PROGID_STR = 2  # pszClass (HKCR\pszClass)
ASSOCCLASS_CLSID_KEY = 3  # hkeyClass
ASSOCCLASS_CLSID_STR = 4  #  pszClass (HKCR\CLSID\pszClass)
ASSOCCLASS_APP_KEY = 5  # hkeyClass
ASSOCCLASS_APP_STR = 6  # pszClass (HKCR\Applications\PathFindFileName(pszClass))
ASSOCCLASS_SYSTEM_STR = 7  # pszClass
ASSOCCLASS_FOLDER = 8  # none
ASSOCCLASS_STAR = 9  # none

NSTCS_HASEXPANDOS = 0x1
NSTCS_HASLINES = 0x2
NSTCS_SINGLECLICKEXPAND = 0x4
NSTCS_FULLROWSELECT = 0x8
NSTCS_SPRINGEXPAND = 0x10
NSTCS_HORIZONTALSCROLL = 0x20
NSTCS_ROOTHASEXPANDO = 0x40
NSTCS_SHOWSELECTIONALWAYS = 0x80
NSTCS_NOINFOTIP = 0x200
NSTCS_EVENHEIGHT = 0x400
NSTCS_NOREPLACEOPEN = 0x800
NSTCS_DISABLEDRAGDROP = 0x1000
NSTCS_NOORDERSTREAM = 0x2000
NSTCS_RICHTOOLTIP = 0x4000
NSTCS_BORDER = 0x8000
NSTCS_NOEDITLABELS = 0x10000
NSTCS_TABSTOP = 0x20000
NSTCS_FAVORITESMODE = 0x80000
NSTCS_AUTOHSCROLL = 0x100000
NSTCS_FADEINOUTEXPANDOS = 0x200000
NSTCS_EMPTYTEXT = 0x400000
NSTCS_CHECKBOXES = 0x800000
NSTCS_PARTIALCHECKBOXES = 0x1000000
NSTCS_EXCLUSIONCHECKBOXES = 0x2000000
NSTCS_DIMMEDCHECKBOXES = 0x4000000
NSTCS_NOINDENTCHECKS = 0x8000000
NSTCS_ALLOWJUNCTIONS = 0x10000000
NSTCS_SHOWTABSBUTTON = 0x20000000
NSTCS_SHOWDELETEBUTTON = 0x40000000
NSTCS_SHOWREFRESHBUTTON = -2147483648  # 0x80000000

NSTCRS_VISIBLE = 0
NSTCRS_HIDDEN = 0x1
NSTCRS_EXPANDED = 0x2
NSTCIS_NONE = 0
NSTCIS_SELECTED = 0x1
NSTCIS_EXPANDED = 0x2
NSTCIS_BOLD = 0x4
NSTCIS_DISABLED = 0x8
NSTCGNI_NEXT = 0
NSTCGNI_NEXTVISIBLE = 0x1
NSTCGNI_PREV = 0x2
NSTCGNI_PREVVISIBLE = 0x3
NSTCGNI_PARENT = 0x4
NSTCGNI_CHILD = 0x5
NSTCGNI_FIRSTVISIBLE = 0x6
NSTCGNI_LASTVISIBLE = 0x7

CLSID_ExplorerBrowser = "{71f96385-ddd6-48d3-a0c1-ae06e8b055fb}"

# Names of the methods of many shell interfaces; used by implementation of
# the interfaces.
IBrowserFrame_Methods = ["GetFrameOptions"]
ICategorizer_Methods = [
    "GetDescription",
    "GetCategory",
    "GetCategoryInfo",
    "CompareCategory",
]
ICategoryProvider_Methods = [
    "CanCategorizeOnSCID",
    "GetDefaultCategory",
    "GetCategoryForSCID",
    "EnumCategories",
    "GetCategoryName",
    "CreateCategory",
]
IContextMenu_Methods = ["QueryContextMenu", "InvokeCommand", "GetCommandString"]
IExplorerCommand_Methods = [
    "GetTitle",
    "GetIcon",
    "GetToolTip",
    "GetCanonicalName",
    "GetState",
    "Invoke",
    "GetFlags",
    "EnumSubCommands",
]
IExplorerCommandProvider_Methods = ["GetCommand", "GetCommands"]
IOleWindow_Methods = [
    "GetWindow",
    "ContextSensitiveHelp",
]  # XXX - this should be somewhere in win32com
IPersist_Methods = ["GetClassID"]
IPersistFolder_Methods = IPersist_Methods + ["Initialize"]
IPersistFolder2_Methods = IPersistFolder_Methods + ["GetCurFolder"]
IShellExtInit_Methods = ["Initialize"]
IShellView_Methods = IOleWindow_Methods + [
    "TranslateAccelerator",
    "EnableModeless",
    "UIActivate",
    "Refresh",
    "CreateViewWindow",
    "DestroyViewWindow",
    "GetCurrentInfo",
    "AddPropertySheetPages",
    "SaveViewState",
    "SelectItem",
    "GetItemObject",
]

IShellFolder_Methods = [
    "ParseDisplayName",
    "EnumObjects",
    "BindToObject",
    "BindToStorage",
    "CompareIDs",
    "CreateViewObject",
    "GetAttributesOf",
    "GetUIObjectOf",
    "GetDisplayNameOf",
    "SetNameOf",
]
IShellFolder2_Methods = IShellFolder_Methods + [
    "GetDefaultSearchGUID",
    "EnumSearches",
    "GetDefaultColumn",
    "GetDefaultColumnState",
    "GetDetailsEx",
    "GetDetailsOf",
    "MapColumnToSCID",
]

## enum GETPROPERTYSTOREFLAGS, used with IShellItem2 methods
GPS_DEFAULT = 0
GPS_HANDLERPROPERTIESONLY = 0x1
GPS_READWRITE = 0x2
GPS_TEMPORARY = 0x4
GPS_FASTPROPERTIESONLY = 0x8
GPS_OPENSLOWITEM = 0x10
GPS_DELAYCREATION = 0x20
GPS_BESTEFFORT = 0x40
GPS_MASK_VALID = 0x7F

## Bind context parameter names, used with IBindCtx::RegisterObjectParam
STR_AVOID_DRIVE_RESTRICTION_POLICY = "Avoid Drive Restriction Policy"
STR_BIND_DELEGATE_CREATE_OBJECT = "Delegate Object Creation"
STR_BIND_FOLDERS_READ_ONLY = "Folders As Read Only"
STR_BIND_FOLDER_ENUM_MODE = "Folder Enum Mode"
STR_BIND_FORCE_FOLDER_SHORTCUT_RESOLVE = "Force Folder Shortcut Resolve"
STR_DONT_PARSE_RELATIVE = "Don't Parse Relative"
STR_DONT_RESOLVE_LINK = "Don't Resolve Link"
## STR_ENUM_ITEMS_FLAGS
STR_FILE_SYS_BIND_DATA = "File System Bind Data"
STR_GET_ASYNC_HANDLER = "GetAsyncHandler"
STR_GPS_BESTEFFORT = "GPS_BESTEFFORT"
STR_GPS_DELAYCREATION = "GPS_DELAYCREATION"
STR_GPS_FASTPROPERTIESONLY = "GPS_FASTPROPERTIESONLY"
STR_GPS_HANDLERPROPERTIESONLY = "GPS_HANDLERPROPERTIESONLY"
STR_GPS_NO_OPLOCK = "GPS_NO_OPLOCK"
STR_GPS_OPENSLOWITEM = "GPS_OPENSLOWITEM"
STR_IFILTER_FORCE_TEXT_FILTER_FALLBACK = "Always bind persistent handlers"
STR_IFILTER_LOAD_DEFINED_FILTER = "Only bind registered persistent handlers"
STR_INTERNAL_NAVIGATE = "Internal Navigation"
STR_INTERNETFOLDER_PARSE_ONLY_URLMON_BINDABLE = "Validate URL"
STR_ITEM_CACHE_CONTEXT = "ItemCacheContext"
STR_NO_VALIDATE_FILENAME_CHARS = "NoValidateFilenameChars"
STR_PARSE_ALLOW_INTERNET_SHELL_FOLDERS = "Allow binding to Internet shell folder handlers and negate STR_PARSE_PREFER_WEB_BROWSING"
STR_PARSE_AND_CREATE_ITEM = "ParseAndCreateItem"
STR_PARSE_DONT_REQUIRE_VALIDATED_URLS = "Do not require validated URLs"
STR_PARSE_EXPLICIT_ASSOCIATION_SUCCESSFUL = "ExplicitAssociationSuccessful"
STR_PARSE_PARTIAL_IDLIST = "ParseOriginalItem"
STR_PARSE_PREFER_FOLDER_BROWSING = "Parse Prefer Folder Browsing"
STR_PARSE_PREFER_WEB_BROWSING = "Do not bind to Internet shell folder handlers"
STR_PARSE_PROPERTYSTORE = "DelegateNamedProperties"
STR_PARSE_SHELL_PROTOCOL_TO_FILE_OBJECTS = "Parse Shell Protocol To File Objects"
STR_PARSE_SHOW_NET_DIAGNOSTICS_UI = "Show network diagnostics UI"
STR_PARSE_SKIP_NET_CACHE = "Skip Net Resource Cache"
STR_PARSE_TRANSLATE_ALIASES = "Parse Translate Aliases"
STR_PARSE_WITH_EXPLICIT_ASSOCAPP = "ExplicitAssociationApp"
STR_PARSE_WITH_EXPLICIT_PROGID = "ExplicitProgid"
STR_PARSE_WITH_PROPERTIES = "ParseWithProperties"
## STR_PROPERTYBAG_PARAM
STR_SKIP_BINDING_CLSID = "Skip Binding CLSID"
STR_TRACK_CLSID = "Track the CLSID"

## KF_REDIRECTION_CAPABILITIES enum
KF_REDIRECTION_CAPABILITIES_ALLOW_ALL = 0x000000FF
KF_REDIRECTION_CAPABILITIES_REDIRECTABLE = 0x00000001
KF_REDIRECTION_CAPABILITIES_DENY_ALL = 0x000FFF00
KF_REDIRECTION_CAPABILITIES_DENY_POLICY_REDIRECTED = 0x00000100
KF_REDIRECTION_CAPABILITIES_DENY_POLICY = 0x00000200
KF_REDIRECTION_CAPABILITIES_DENY_PERMISSIONS = 0x00000400

## KF_REDIRECT_FLAGS enum
KF_REDIRECT_USER_EXCLUSIVE = 0x00000001
KF_REDIRECT_COPY_SOURCE_DACL = 0x00000002
KF_REDIRECT_OWNER_USER = 0x00000004
KF_REDIRECT_SET_OWNER_EXPLICIT = 0x00000008
KF_REDIRECT_CHECK_ONLY = 0x00000010
KF_REDIRECT_WITH_UI = 0x00000020
KF_REDIRECT_UNPIN = 0x00000040
KF_REDIRECT_PIN = 0x00000080
KF_REDIRECT_COPY_CONTENTS = 0x00000200
KF_REDIRECT_DEL_SOURCE_CONTENTS = 0x00000400
KF_REDIRECT_EXCLUDE_ALL_KNOWN_SUBFOLDERS = 0x00000800

## KF_CATEGORY enum
KF_CATEGORY_VIRTUAL = 0x00000001
KF_CATEGORY_FIXED = 0x00000002
KF_CATEGORY_COMMON = 0x00000003
KF_CATEGORY_PERUSER = 0x00000004

## FFFP_MODE enum
FFFP_EXACTMATCH = 0
FFFP_NEARESTPARENTMATCH = 1

## APPDOCLISTTYPE, used with IApplicationDocumentLists.GetList
ADLT_RECENT = 0
ADLT_FREQUENT = 1

## KNOWNDESTCATEGORY used with ICustomDestinationList.AppendKnownCategory
KDC_FREQUENT = 1
KDC_RECENT = 2

## LIBRARYFOLDERFILTER used with IShellLibrary.GetFolders
LFF_FORCEFILESYSTEM = 1
LFF_STORAGEITEMS = 2
LFF_ALLITEMS = 3

## DEFAULTSAVEFOLDERTYPE used with IShellLibrary.Get/SetDefaultSaveFolder
DSFT_DETECT = 1
DSFT_PRIVATE = 2
DSFT_PUBLIC = 3

## LIBRARYOPTIONFLAGS used with IShellLibrary.Get/SetOptions
LOF_DEFAULT = 0
LOF_PINNEDTONAVPANE = 1
LOF_MASK_ALL = 1

## LIBRARYSAVEFLAGS Used with PyIShellLibrary.Save
LSF_FAILIFTHERE = 0
LSF_OVERRIDEEXISTING = 1
LSF_MAKEUNIQUENAME = 2

## TRANSFER_SOURCE_FLAGS, used with IFileOperationProgressSink
TSF_NORMAL = 0
TSF_FAIL_EXIST = 0
TSF_RENAME_EXIST = 0x1
TSF_OVERWRITE_EXIST = 0x2
TSF_ALLOW_DECRYPTION = 0x4
TSF_NO_SECURITY = 0x8
TSF_COPY_CREATION_TIME = 0x10
TSF_COPY_WRITE_TIME = 0x20
TSF_USE_FULL_ACCESS = 0x40
TSF_DELETE_RECYCLE_IF_POSSIBLE = 0x80
TSF_COPY_HARD_LINK = 0x100
TSF_COPY_LOCALIZED_NAME = 0x200
TSF_MOVE_AS_COPY_DELETE = 0x400
TSF_SUSPEND_SHELLEVENTS = 0x800

## TRANSFER_ADVISE_STATE, used with ITransferAdviseSink
TS_NONE = 0
TS_PERFORMING = 1
TS_PREPARING = 2
TS_INDETERMINATE = 4

## Success HRESULTs returned by ITransfer* interface operations
COPYENGINE_S_YES = 0x00270001
COPYENGINE_S_NOT_HANDLED = 0x00270003
COPYENGINE_S_USER_RETRY = 0x00270004
COPYENGINE_S_USER_IGNORED = 0x00270005
COPYENGINE_S_MERGE = 0x00270006
COPYENGINE_S_DONT_PROCESS_CHILDREN = 0x00270008
COPYENGINE_S_ALREADY_DONE = 0x0027000A
COPYENGINE_S_PENDING = 0x0027000B
COPYENGINE_S_KEEP_BOTH = 0x0027000C
COPYENGINE_S_CLOSE_PROGRAM = 0x0027000D
COPYENGINE_S_COLLISIONRESOLVED = 0x0027000E

## Error HRESULTS
COPYENGINE_E_USER_CANCELLED = 0x80270000
COPYENGINE_E_CANCELLED = 0x80270001
COPYENGINE_E_REQUIRES_ELEVATION = 0x80270002
COPYENGINE_E_SAME_FILE = 0x80270003
COPYENGINE_E_DIFF_DIR = 0x80270004
COPYENGINE_E_MANY_SRC_1_DEST = 0x80270005
COPYENGINE_E_DEST_SUBTREE = 0x80270009
COPYENGINE_E_DEST_SAME_TREE = 0x8027000A
COPYENGINE_E_FLD_IS_FILE_DEST = 0x8027000B
COPYENGINE_E_FILE_IS_FLD_DEST = 0x8027000C
COPYENGINE_E_FILE_TOO_LARGE = 0x8027000D
COPYENGINE_E_REMOVABLE_FULL = 0x8027000E
COPYENGINE_E_DEST_IS_RO_CD = 0x8027000F
COPYENGINE_E_DEST_IS_RW_CD = 0x80270010
COPYENGINE_E_DEST_IS_R_CD = 0x80270011
COPYENGINE_E_DEST_IS_RO_DVD = 0x80270012
COPYENGINE_E_DEST_IS_RW_DVD = 0x80270013
COPYENGINE_E_DEST_IS_R_DVD = 0x80270014
COPYENGINE_E_SRC_IS_RO_CD = 0x80270015
COPYENGINE_E_SRC_IS_RW_CD = 0x80270016
COPYENGINE_E_SRC_IS_R_CD = 0x80270017
COPYENGINE_E_SRC_IS_RO_DVD = 0x80270018
COPYENGINE_E_SRC_IS_RW_DVD = 0x80270019
COPYENGINE_E_SRC_IS_R_DVD = 0x8027001A
COPYENGINE_E_INVALID_FILES_SRC = 0x8027001B
COPYENGINE_E_INVALID_FILES_DEST = 0x8027001C
COPYENGINE_E_PATH_TOO_DEEP_SRC = 0x8027001D
COPYENGINE_E_PATH_TOO_DEEP_DEST = 0x8027001E
COPYENGINE_E_ROOT_DIR_SRC = 0x8027001F
COPYENGINE_E_ROOT_DIR_DEST = 0x80270020
COPYENGINE_E_ACCESS_DENIED_SRC = 0x80270021
COPYENGINE_E_ACCESS_DENIED_DEST = 0x80270022
COPYENGINE_E_PATH_NOT_FOUND_SRC = 0x80270023
COPYENGINE_E_PATH_NOT_FOUND_DEST = 0x80270024
COPYENGINE_E_NET_DISCONNECT_SRC = 0x80270025
COPYENGINE_E_NET_DISCONNECT_DEST = 0x80270026
COPYENGINE_E_SHARING_VIOLATION_SRC = 0x80270027
COPYENGINE_E_SHARING_VIOLATION_DEST = 0x80270028
COPYENGINE_E_ALREADY_EXISTS_NORMAL = 0x80270029
COPYENGINE_E_ALREADY_EXISTS_READONLY = 0x8027002A
COPYENGINE_E_ALREADY_EXISTS_SYSTEM = 0x8027002B
COPYENGINE_E_ALREADY_EXISTS_FOLDER = 0x8027002C
COPYENGINE_E_STREAM_LOSS = 0x8027002D
COPYENGINE_E_EA_LOSS = 0x8027002E
COPYENGINE_E_PROPERTY_LOSS = 0x8027002F
COPYENGINE_E_PROPERTIES_LOSS = 0x80270030
COPYENGINE_E_ENCRYPTION_LOSS = 0x80270031
COPYENGINE_E_DISK_FULL = 0x80270032
COPYENGINE_E_DISK_FULL_CLEAN = 0x80270033
COPYENGINE_E_EA_NOT_SUPPORTED = 0x80270034
COPYENGINE_E_CANT_REACH_SOURCE = 0x80270035
COPYENGINE_E_RECYCLE_UNKNOWN_ERROR = 0x80270035
COPYENGINE_E_RECYCLE_FORCE_NUKE = 0x80270036
COPYENGINE_E_RECYCLE_SIZE_TOO_BIG = 0x80270037
COPYENGINE_E_RECYCLE_PATH_TOO_LONG = 0x80270038
COPYENGINE_E_RECYCLE_BIN_NOT_FOUND = 0x8027003A
COPYENGINE_E_NEWFILE_NAME_TOO_LONG = 0x8027003B
COPYENGINE_E_NEWFOLDER_NAME_TOO_LONG = 0x8027003C
COPYENGINE_E_DIR_NOT_EMPTY = 0x8027003D
COPYENGINE_E_FAT_MAX_IN_ROOT = 0x8027003E
COPYENGINE_E_ACCESSDENIED_READONLY = 0x8027003F
COPYENGINE_E_REDIRECTED_TO_WEBPAGE = 0x80270040
COPYENGINE_E_SERVER_BAD_FILE_TYPE = 0x80270041

FOLDERID_NetworkFolder = "{D20BEEC4-5CA8-4905-AE3B-BF251EA09B53}"
FOLDERID_ComputerFolder = "{0AC0837C-BBF8-452A-850D-79D08E667CA7}"
FOLDERID_InternetFolder = "{4D9F7874-4E0C-4904-967B-40B0D20C3E4B}"
FOLDERID_ControlPanelFolder = "{82A74AEB-AEB4-465C-A014-D097EE346D63}"
FOLDERID_PrintersFolder = "{76FC4E2D-D6AD-4519-A663-37BD56068185}"
FOLDERID_SyncManagerFolder = "{43668BF8-C14E-49B2-97C9-747784D784B7}"
FOLDERID_SyncSetupFolder = "{0F214138-B1D3-4a90-BBA9-27CBC0C5389A}"
FOLDERID_ConflictFolder = "{4bfefb45-347d-4006-a5be-ac0cb0567192}"
FOLDERID_SyncResultsFolder = "{289a9a43-be44-4057-a41b-587a76d7e7f9}"
FOLDERID_RecycleBinFolder = "{B7534046-3ECB-4C18-BE4E-64CD4CB7D6AC}"
FOLDERID_ConnectionsFolder = "{6F0CD92B-2E97-45D1-88FF-B0D186B8DEDD}"
FOLDERID_Fonts = "{FD228CB7-AE11-4AE3-864C-16F3910AB8FE}"
FOLDERID_Desktop = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"
FOLDERID_Startup = "{B97D20BB-F46A-4C97-BA10-5E3608430854}"
FOLDERID_Programs = "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"
FOLDERID_StartMenu = "{625B53C3-AB48-4EC1-BA1F-A1EF4146FC19}"
FOLDERID_Recent = "{AE50C081-EBD2-438A-8655-8A092E34987A}"
FOLDERID_SendTo = "{8983036C-27C0-404B-8F08-102D10DCFD74}"
FOLDERID_Documents = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
FOLDERID_Favorites = "{1777F761-68AD-4D8A-87BD-30B759FA33DD}"
FOLDERID_NetHood = "{C5ABBF53-E17F-4121-8900-86626FC2C973}"
FOLDERID_PrintHood = "{9274BD8D-CFD1-41C3-B35E-B13F55A758F4}"
FOLDERID_Templates = "{A63293E8-664E-48DB-A079-DF759E0509F7}"
FOLDERID_CommonStartup = "{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}"
FOLDERID_CommonPrograms = "{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}"
FOLDERID_CommonStartMenu = "{A4115719-D62E-491D-AA7C-E74B8BE3B067}"
FOLDERID_PublicDesktop = "{C4AA340D-F20F-4863-AFEF-F87EF2E6BA25}"
FOLDERID_ProgramData = "{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}"
FOLDERID_CommonTemplates = "{B94237E7-57AC-4347-9151-B08C6C32D1F7}"
FOLDERID_PublicDocuments = "{ED4824AF-DCE4-45A8-81E2-FC7965083634}"
FOLDERID_RoamingAppData = "{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}"
FOLDERID_LocalAppData = "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"
FOLDERID_LocalAppDataLow = "{A520A1A4-1780-4FF6-BD18-167343C5AF16}"
FOLDERID_InternetCache = "{352481E8-33BE-4251-BA85-6007CAEDCF9D}"
FOLDERID_Cookies = "{2B0F765D-C0E9-4171-908E-08A611B84FF6}"
FOLDERID_History = "{D9DC8A3B-B784-432E-A781-5A1130A75963}"
FOLDERID_System = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
FOLDERID_SystemX86 = "{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}"
FOLDERID_Windows = "{F38BF404-1D43-42F2-9305-67DE0B28FC23}"
FOLDERID_Profile = "{5E6C858F-0E22-4760-9AFE-EA3317B67173}"
FOLDERID_Pictures = "{33E28130-4E1E-4676-835A-98395C3BC3BB}"
FOLDERID_ProgramFilesX86 = "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}"
FOLDERID_ProgramFilesCommonX86 = "{DE974D24-D9C6-4D3E-BF91-F4455120B917}"
FOLDERID_ProgramFilesX64 = "{6D809377-6AF0-444b-8957-A3773F02200E}"
FOLDERID_ProgramFilesCommonX64 = "{6365D5A7-0F0D-45e5-87F6-0DA56B6A4F7D}"
FOLDERID_ProgramFiles = "{905e63b6-c1bf-494e-b29c-65b732d3d21a}"
FOLDERID_ProgramFilesCommon = "{F7F1ED05-9F6D-47A2-AAAE-29D317C6F066}"
FOLDERID_UserProgramFiles = "{5cd7aee2-2219-4a67-b85d-6c9ce15660cb}"
FOLDERID_UserProgramFilesCommon = "{bcbd3057-ca5c-4622-b42d-bc56db0ae516}"
FOLDERID_AdminTools = "{724EF170-A42D-4FEF-9F26-B60E846FBA4F}"
FOLDERID_CommonAdminTools = "{D0384E7D-BAC3-4797-8F14-CBA229B392B5}"
FOLDERID_Music = "{4BD8D571-6D19-48D3-BE97-422220080E43}"
FOLDERID_Videos = "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}"
FOLDERID_Ringtones = "{C870044B-F49E-4126-A9C3-B52A1FF411E8}"
FOLDERID_PublicPictures = "{B6EBFB86-6907-413C-9AF7-4FC2ABF07CC5}"
FOLDERID_PublicMusic = "{3214FAB5-9757-4298-BB61-92A9DEAA44FF}"
FOLDERID_PublicVideos = "{2400183A-6185-49FB-A2D8-4A392A602BA3}"
FOLDERID_PublicRingtones = "{E555AB60-153B-4D17-9F04-A5FE99FC15EC}"
FOLDERID_ResourceDir = "{8AD10C31-2ADB-4296-A8F7-E4701232C972}"
FOLDERID_LocalizedResourcesDir = "{2A00375E-224C-49DE-B8D1-440DF7EF3DDC}"
FOLDERID_CommonOEMLinks = "{C1BAE2D0-10DF-4334-BEDD-7AA20B227A9D}"
FOLDERID_CDBurning = "{9E52AB10-F80D-49DF-ACB8-4330F5687855}"
FOLDERID_UserProfiles = "{0762D272-C50A-4BB0-A382-697DCD729B80}"
FOLDERID_Playlists = "{DE92C1C7-837F-4F69-A3BB-86E631204A23}"
FOLDERID_SamplePlaylists = "{15CA69B3-30EE-49C1-ACE1-6B5EC372AFB5}"
FOLDERID_SampleMusic = "{B250C668-F57D-4EE1-A63C-290EE7D1AA1F}"
FOLDERID_SamplePictures = "{C4900540-2379-4C75-844B-64E6FAF8716B}"
FOLDERID_SampleVideos = "{859EAD94-2E85-48AD-A71A-0969CB56A6CD}"
FOLDERID_PhotoAlbums = "{69D2CF90-FC33-4FB7-9A0C-EBB0F0FCB43C}"
FOLDERID_Public = "{DFDF76A2-C82A-4D63-906A-5644AC457385}"
FOLDERID_ChangeRemovePrograms = "{df7266ac-9274-4867-8d55-3bd661de872d}"
FOLDERID_AppUpdates = "{a305ce99-f527-492b-8b1a-7e76fa98d6e4}"
FOLDERID_AddNewPrograms = "{de61d971-5ebc-4f02-a3a9-6c82895e5c04}"
FOLDERID_Downloads = "{374DE290-123F-4565-9164-39C4925E467B}"
FOLDERID_PublicDownloads = "{3D644C9B-1FB8-4f30-9B45-F670235F79C0}"
FOLDERID_SavedSearches = "{7d1d3a04-debb-4115-95cf-2f29da2920da}"
FOLDERID_QuickLaunch = "{52a4f021-7b75-48a9-9f6b-4b87a210bc8f}"
FOLDERID_Contacts = "{56784854-C6CB-462b-8169-88E350ACB882}"
FOLDERID_SidebarParts = "{A75D362E-50FC-4fb7-AC2C-A8BEAA314493}"
FOLDERID_SidebarDefaultParts = "{7B396E54-9EC5-4300-BE0A-2482EBAE1A26}"
FOLDERID_PublicGameTasks = "{DEBF2536-E1A8-4c59-B6A2-414586476AEA}"
FOLDERID_GameTasks = "{054FAE61-4DD8-4787-80B6-090220C4B700}"
FOLDERID_SavedGames = "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}"
FOLDERID_Games = "{CAC52C1A-B53D-4edc-92D7-6B2E8AC19434}"
FOLDERID_SEARCH_MAPI = "{98ec0e18-2098-4d44-8644-66979315a281}"
FOLDERID_SEARCH_CSC = "{ee32e446-31ca-4aba-814f-a5ebd2fd6d5e}"
FOLDERID_Links = "{bfb9d5e0-c6a9-404c-b2b2-ae6db6af4968}"
FOLDERID_UsersFiles = "{f3ce0f7c-4901-4acc-8648-d5d44b04ef8f}"
FOLDERID_UsersLibraries = "{A302545D-DEFF-464b-ABE8-61C8648D939B}"
FOLDERID_SearchHome = "{190337d1-b8ca-4121-a639-6d472d16972a}"
FOLDERID_OriginalImages = "{2C36C0AA-5812-4b87-BFD0-4CD0DFB19B39}"
FOLDERID_DocumentsLibrary = "{7b0db17d-9cd2-4a93-9733-46cc89022e7c}"
FOLDERID_MusicLibrary = "{2112AB0A-C86A-4ffe-A368-0DE96E47012E}"
FOLDERID_PicturesLibrary = "{A990AE9F-A03B-4e80-94BC-9912D7504104}"
FOLDERID_VideosLibrary = "{491E922F-5643-4af4-A7EB-4E7A138D8174}"
FOLDERID_RecordedTVLibrary = "{1A6FDBA2-F42D-4358-A798-B74D745926C5}"
FOLDERID_HomeGroup = "{52528A6B-B9E3-4add-B60D-588C2DBA842D}"
FOLDERID_HomeGroupCurrentUser = "{9B74B6A3-0DFD-4f11-9E78-5F7800F2E772}"
FOLDERID_DeviceMetadataStore = "{5CE4A5E9-E4EB-479D-B89F-130C02886155}"
FOLDERID_Libraries = "{1B3EA5DC-B587-4786-B4EF-BD1DC332AEAE}"
FOLDERID_PublicLibraries = "{48daf80b-e6cf-4f4e-b800-0e69d84ee384}"
FOLDERID_UserPinned = "{9e3995ab-1f9c-4f13-b827-48b24b6c7174}"
FOLDERID_ImplicitAppShortcuts = "{bcb5256f-79f6-4cee-b725-dc34e402fd46}"
FOLDERID_AccountPictures = "{008ca0b1-55b4-4c56-b8a8-4de4b299d3be}"
FOLDERID_PublicUserTiles = "{0482af6c-08f1-4c34-8c90-e17ec98b1e17}"
FOLDERID_AppsFolder = "{1e87508d-89c2-42f0-8a7e-645a0f50ca58}"
FOLDERID_StartMenuAllPrograms = "{F26305EF-6948-40B9-B255-81453D09C785}"
FOLDERID_CommonStartMenuPlaces = "{A440879F-87A0-4F7D-B700-0207B966194A}"
FOLDERID_ApplicationShortcuts = "{A3918781-E5F2-4890-B3D9-A7E54332328C}"
FOLDERID_RoamingTiles = "{00BCFC5A-ED94-4e48-96A1-3F6217F21990}"
FOLDERID_RoamedTileImages = "{AAA8D5A5-F1D6-4259-BAA8-78E7EF60835E}"
FOLDERID_Screenshots = "{b7bede81-df94-4682-a7d8-57a52620b86f}"
FOLDERID_CameraRoll = "{AB5FB87B-7CE2-4F83-915D-550846C9537B}"
FOLDERID_SkyDrive = "{A52BBA46-E9E1-435f-B3D9-28DAA648C0F6}"
FOLDERID_OneDrive = "{A52BBA46-E9E1-435f-B3D9-28DAA648C0F6}"
FOLDERID_SkyDriveDocuments = "{24D89E24-2F19-4534-9DDE-6A6671FBB8FE}"
FOLDERID_SkyDrivePictures = "{339719B5-8C47-4894-94C2-D8F77ADD44A6}"
FOLDERID_SkyDriveMusic = "{C3F2459E-80D6-45DC-BFEF-1F769F2BE730}"
FOLDERID_SkyDriveCameraRoll = "{767E6811-49CB-4273-87C2-20F355E1085B}"
FOLDERID_SearchHistory = "{0D4C3DB6-03A3-462F-A0E6-08924C41B5D4}"
FOLDERID_SearchTemplates = "{7E636BFE-DFA9-4D5E-B456-D7B39851D8A9}"
FOLDERID_CameraRollLibrary = "{2B20DF75-1EDA-4039-8097-38798227D5B7}"
FOLDERID_SavedPictures = "{3B193882-D3AD-4eab-965A-69829D1FB59F}"
FOLDERID_SavedPicturesLibrary = "{E25B5812-BE88-4bd9-94B0-29233477B6C3}"
FOLDERID_RetailDemo = "{12D4C69E-24AD-4923-BE19-31321C43A767}"
FOLDERID_Device = "{1C2AC1DC-4358-4B6C-9733-AF21156576F0}"
FOLDERID_DevelopmentFiles = "{DBE8E08E-3053-4BBC-B183-2A7B2B191E59}"
FOLDERID_Objects3D = "{31C0DD25-9439-4F12-BF41-7FF4EDA38722}"
FOLDERID_AppCaptures = "{EDC0FE71-98D8-4F4A-B920-C8DC133CB165}"
FOLDERID_LocalDocuments = "{f42ee2d3-909f-4907-8871-4c22fc0bf756}"
FOLDERID_LocalPictures = "{0ddd015d-b06c-45d5-8c4c-f59713854639 }"
FOLDERID_LocalVideos = "{35286a68-3c57-41a1-bbb1-0eae73d76c95}"
FOLDERID_LocalMusic = "{a0c69a99-21c8-4671-8703-7934162fcf1d}"
FOLDERID_LocalDownloads = "{7d83ee9b-2244-4e70-b1f5-5393042af1e4}"
FOLDERID_RecordedCalls = "{2f8b40c2-83ed-48ee-b383-a1f157ec6f9a}"

KF_FLAG_DEFAULT = 0x00000000
KF_FLAG_FORCE_APP_DATA_REDIRECTION = 0x00080000
KF_FLAG_RETURN_FILTER_REDIRECTION_TARGET = 0x00040000
KF_FLAG_FORCE_PACKAGE_REDIRECTION = 0x00020000
KF_FLAG_NO_PACKAGE_REDIRECTION = 0x00010000
KF_FLAG_FORCE_APPCONTAINER_REDIRECTION = 0x00020000
KF_FLAG_NO_APPCONTAINER_REDIRECTION = 0x00010000
KF_FLAG_CREATE = 0x00008000
KF_FLAG_DONT_VERIFY = 0x00004000
KF_FLAG_DONT_UNEXPAND = 0x00002000
KF_FLAG_NO_ALIAS = 0x00001000
KF_FLAG_INIT = 0x00000800
KF_FLAG_DEFAULT_PATH = 0x00000400
KF_FLAG_NOT_PARENT_RELATIVE = 0x00000200
KF_FLAG_SIMPLE_IDLIST = 0x00000100
KF_FLAG_ALIAS_ONLY = 0x80000000

# === NexusCore/openenv\Lib\site-packages\matplotlib\offsetbox.py ===
r"""
Container classes for `.Artist`\s.

`OffsetBox`
    The base of all container artists defined in this module.

`AnchoredOffsetbox`, `AnchoredText`
    Anchor and align an arbitrary `.Artist` or a text relative to the parent
    axes or a specific anchor point.

`DrawingArea`
    A container with fixed width and height. Children have a fixed position
    inside the container and may be clipped.

`HPacker`, `VPacker`
    Containers for layouting their children vertically or horizontally.

`PaddedBox`
    A container to add a padding around an `.Artist`.

`TextArea`
    Contains a single `.Text` instance.
"""

import functools

import numpy as np

import matplotlib as mpl
from matplotlib import _api, _docstring
import matplotlib.artist as martist
import matplotlib.path as mpath
import matplotlib.text as mtext
import matplotlib.transforms as mtransforms
from matplotlib.font_manager import FontProperties
from matplotlib.image import BboxImage
from matplotlib.patches import (
    FancyBboxPatch, FancyArrowPatch, bbox_artist as mbbox_artist)
from matplotlib.transforms import Bbox, BboxBase, TransformedBbox


DEBUG = False


def _compat_get_offset(meth):
    """
    Decorator for the get_offset method of OffsetBox and subclasses, that
    allows supporting both the new signature (self, bbox, renderer) and the old
    signature (self, width, height, xdescent, ydescent, renderer).
    """
    sigs = [lambda self, width, height, xdescent, ydescent, renderer: locals(),
            lambda self, bbox, renderer: locals()]

    @functools.wraps(meth)
    def get_offset(self, *args, **kwargs):
        params = _api.select_matching_signature(sigs, self, *args, **kwargs)
        bbox = (params["bbox"] if "bbox" in params else
                Bbox.from_bounds(-params["xdescent"], -params["ydescent"],
                                 params["width"], params["height"]))
        return meth(params["self"], bbox, params["renderer"])
    return get_offset


# for debugging use
def _bbox_artist(*args, **kwargs):
    if DEBUG:
        mbbox_artist(*args, **kwargs)


def _get_packed_offsets(widths, total, sep, mode="fixed"):
    r"""
    Pack boxes specified by their *widths*.

    For simplicity of the description, the terminology used here assumes a
    horizontal layout, but the function works equally for a vertical layout.

    There are three packing *mode*\s:

    - 'fixed': The elements are packed tight to the left with a spacing of
      *sep* in between. If *total* is *None* the returned total will be the
      right edge of the last box. A non-*None* total will be passed unchecked
      to the output. In particular this means that right edge of the last
      box may be further to the right than the returned total.

    - 'expand': Distribute the boxes with equal spacing so that the left edge
      of the first box is at 0, and the right edge of the last box is at
      *total*. The parameter *sep* is ignored in this mode. A total of *None*
      is accepted and considered equal to 1. The total is returned unchanged
      (except for the conversion *None* to 1). If the total is smaller than
      the sum of the widths, the laid out boxes will overlap.

    - 'equal': If *total* is given, the total space is divided in N equal
      ranges and each box is left-aligned within its subspace.
      Otherwise (*total* is *None*), *sep* must be provided and each box is
      left-aligned in its subspace of width ``(max(widths) + sep)``. The
      total width is then calculated to be ``N * (max(widths) + sep)``.

    Parameters
    ----------
    widths : list of float
        Widths of boxes to be packed.
    total : float or None
        Intended total length. *None* if not used.
    sep : float or None
        Spacing between boxes.
    mode : {'fixed', 'expand', 'equal'}
        The packing mode.

    Returns
    -------
    total : float
        The total width needed to accommodate the laid out boxes.
    offsets : array of float
        The left offsets of the boxes.
    """
    _api.check_in_list(["fixed", "expand", "equal"], mode=mode)

    if mode == "fixed":
        offsets_ = np.cumsum([0] + [w + sep for w in widths])
        offsets = offsets_[:-1]
        if total is None:
            total = offsets_[-1] - sep
        return total, offsets

    elif mode == "expand":
        # This is a bit of a hack to avoid a TypeError when *total*
        # is None and used in conjugation with tight layout.
        if total is None:
            total = 1
        if len(widths) > 1:
            sep = (total - sum(widths)) / (len(widths) - 1)
        else:
            sep = 0
        offsets_ = np.cumsum([0] + [w + sep for w in widths])
        offsets = offsets_[:-1]
        return total, offsets

    elif mode == "equal":
        maxh = max(widths)
        if total is None:
            if sep is None:
                raise ValueError("total and sep cannot both be None when "
                                 "using layout mode 'equal'")
            total = (maxh + sep) * len(widths)
        else:
            sep = total / len(widths) - maxh
        offsets = (maxh + sep) * np.arange(len(widths))
        return total, offsets


def _get_aligned_offsets(yspans, height, align="baseline"):
    """
    Align boxes each specified by their ``(y0, y1)`` spans.

    For simplicity of the description, the terminology used here assumes a
    horizontal layout (i.e., vertical alignment), but the function works
    equally for a vertical layout.

    Parameters
    ----------
    yspans
        List of (y0, y1) spans of boxes to be aligned.
    height : float or None
        Intended total height. If None, the maximum of the heights
        (``y1 - y0``) in *yspans* is used.
    align : {'baseline', 'left', 'top', 'right', 'bottom', 'center'}
        The alignment anchor of the boxes.

    Returns
    -------
    (y0, y1)
        y range spanned by the packing.  If a *height* was originally passed
        in, then for all alignments other than "baseline", a span of ``(0,
        height)`` is used without checking that it is actually large enough).
    descent
        The descent of the packing.
    offsets
        The bottom offsets of the boxes.
    """

    _api.check_in_list(
        ["baseline", "left", "top", "right", "bottom", "center"], align=align)
    if height is None:
        height = max(y1 - y0 for y0, y1 in yspans)

    if align == "baseline":
        yspan = (min(y0 for y0, y1 in yspans), max(y1 for y0, y1 in yspans))
        offsets = [0] * len(yspans)
    elif align in ["left", "bottom"]:
        yspan = (0, height)
        offsets = [-y0 for y0, y1 in yspans]
    elif align in ["right", "top"]:
        yspan = (0, height)
        offsets = [height - y1 for y0, y1 in yspans]
    elif align == "center":
        yspan = (0, height)
        offsets = [(height - (y1 - y0)) * .5 - y0 for y0, y1 in yspans]

    return yspan, offsets


class OffsetBox(martist.Artist):
    """
    The OffsetBox is a simple container artist.

    The child artists are meant to be drawn at a relative position to its
    parent.

    Being an artist itself, all parameters are passed on to `.Artist`.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._internal_update(kwargs)
        # Clipping has not been implemented in the OffsetBox family, so
        # disable the clip flag for consistency. It can always be turned back
        # on to zero effect.
        self.set_clip_on(False)
        self._children = []
        self._offset = (0, 0)

    def set_figure(self, fig):
        """
        Set the `.Figure` for the `.OffsetBox` and all its children.

        Parameters
        ----------
        fig : `~matplotlib.figure.Figure`
        """
        super().set_figure(fig)
        for c in self.get_children():
            c.set_figure(fig)

    @martist.Artist.axes.setter
    def axes(self, ax):
        # TODO deal with this better
        martist.Artist.axes.fset(self, ax)
        for c in self.get_children():
            if c is not None:
                c.axes = ax

    def contains(self, mouseevent):
        """
        Delegate the mouse event contains-check to the children.

        As a container, the `.OffsetBox` does not respond itself to
        mouseevents.

        Parameters
        ----------
        mouseevent : `~matplotlib.backend_bases.MouseEvent`

        Returns
        -------
        contains : bool
            Whether any values are within the radius.
        details : dict
            An artist-specific dictionary of details of the event context,
            such as which points are contained in the pick radius. See the
            individual Artist subclasses for details.

        See Also
        --------
        .Artist.contains
        """
        if self._different_canvas(mouseevent):
            return False, {}
        for c in self.get_children():
            a, b = c.contains(mouseevent)
            if a:
                return a, b
        return False, {}

    def set_offset(self, xy):
        """
        Set the offset.

        Parameters
        ----------
        xy : (float, float) or callable
            The (x, y) coordinates of the offset in display units. These can
            either be given explicitly as a tuple (x, y), or by providing a
            function that converts the extent into the offset. This function
            must have the signature::

                def offset(width, height, xdescent, ydescent, renderer) \
-> (float, float)
        """
        self._offset = xy
        self.stale = True

    @_compat_get_offset
    def get_offset(self, bbox, renderer):
        """
        Return the offset as a tuple (x, y).

        The extent parameters have to be provided to handle the case where the
        offset is dynamically determined by a callable (see
        `~.OffsetBox.set_offset`).

        Parameters
        ----------
        bbox : `.Bbox`
        renderer : `.RendererBase` subclass
        """
        return (
            self._offset(bbox.width, bbox.height, -bbox.x0, -bbox.y0, renderer)
            if callable(self._offset)
            else self._offset)

    def set_width(self, width):
        """
        Set the width of the box.

        Parameters
        ----------
        width : float
        """
        self.width = width
        self.stale = True

    def set_height(self, height):
        """
        Set the height of the box.

        Parameters
        ----------
        height : float
        """
        self.height = height
        self.stale = True

    def get_visible_children(self):
        r"""Return a list of the visible child `.Artist`\s."""
        return [c for c in self._children if c.get_visible()]

    def get_children(self):
        r"""Return a list of the child `.Artist`\s."""
        return self._children

    def _get_bbox_and_child_offsets(self, renderer):
        """
        Return the bbox of the offsetbox and the child offsets.

        The bbox should satisfy ``x0 <= x1 and y0 <= y1``.

        Parameters
        ----------
        renderer : `.RendererBase` subclass

        Returns
        -------
        bbox
        list of (xoffset, yoffset) pairs
        """
        raise NotImplementedError(
            "get_bbox_and_offsets must be overridden in derived classes")

    def get_bbox(self, renderer):
        """Return the bbox of the offsetbox, ignoring parent offsets."""
        bbox, offsets = self._get_bbox_and_child_offsets(renderer)
        return bbox

    def get_window_extent(self, renderer=None):
        # docstring inherited
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        bbox = self.get_bbox(renderer)
        try:  # Some subclasses redefine get_offset to take no args.
            px, py = self.get_offset(bbox, renderer)
        except TypeError:
            px, py = self.get_offset()
        return bbox.translated(px, py)

    def draw(self, renderer):
        """
        Update the location of children if necessary and draw them
        to the given *renderer*.
        """
        bbox, offsets = self._get_bbox_and_child_offsets(renderer)
        px, py = self.get_offset(bbox, renderer)
        for c, (ox, oy) in zip(self.get_visible_children(), offsets):
            c.set_offset((px + ox, py + oy))
            c.draw(renderer)
        _bbox_artist(self, renderer, fill=False, props=dict(pad=0.))
        self.stale = False


class PackerBase(OffsetBox):
    def __init__(self, pad=0., sep=0., width=None, height=None,
                 align="baseline", mode="fixed", children=None):
        """
        Parameters
        ----------
        pad : float, default: 0.0
            The boundary padding in points.

        sep : float, default: 0.0
            The spacing between items in points.

        width, height : float, optional
            Width and height of the container box in pixels, calculated if
            *None*.

        align : {'top', 'bottom', 'left', 'right', 'center', 'baseline'}, \
default: 'baseline'
            Alignment of boxes.

        mode : {'fixed', 'expand', 'equal'}, default: 'fixed'
            The packing mode.

            - 'fixed' packs the given `.Artist`\\s tight with *sep* spacing.
            - 'expand' uses the maximal available space to distribute the
              artists with equal spacing in between.
            - 'equal': Each artist an equal fraction of the available space
              and is left-aligned (or top-aligned) therein.

        children : list of `.Artist`
            The artists to pack.

        Notes
        -----
        *pad* and *sep* are in points and will be scaled with the renderer
        dpi, while *width* and *height* are in pixels.
        """
        super().__init__()
        self.height = height
        self.width = width
        self.sep = sep
        self.pad = pad
        self.mode = mode
        self.align = align
        self._children = children


class VPacker(PackerBase):
    """
    VPacker packs its children vertically, automatically adjusting their
    relative positions at draw time.

    .. code-block:: none

       +---------+
       | Child 1 |
       | Child 2 |
       | Child 3 |
       +---------+
    """

    def _get_bbox_and_child_offsets(self, renderer):
        # docstring inherited
        dpicor = renderer.points_to_pixels(1.)
        pad = self.pad * dpicor
        sep = self.sep * dpicor

        if self.width is not None:
            for c in self.get_visible_children():
                if isinstance(c, PackerBase) and c.mode == "expand":
                    c.set_width(self.width)

        bboxes = [c.get_bbox(renderer) for c in self.get_visible_children()]
        (x0, x1), xoffsets = _get_aligned_offsets(
            [bbox.intervalx for bbox in bboxes], self.width, self.align)
        height, yoffsets = _get_packed_offsets(
            [bbox.height for bbox in bboxes], self.height, sep, self.mode)

        yoffsets = height - (yoffsets + [bbox.y1 for bbox in bboxes])
        ydescent = yoffsets[0]
        yoffsets = yoffsets - ydescent

        return (
            Bbox.from_bounds(x0, -ydescent, x1 - x0, height).padded(pad),
            [*zip(xoffsets, yoffsets)])


class HPacker(PackerBase):
    """
    HPacker packs its children horizontally, automatically adjusting their
    relative positions at draw time.

    .. code-block:: none

       +-------------------------------+
       | Child 1    Child 2    Child 3 |
       +-------------------------------+
    """

    def _get_bbox_and_child_offsets(self, renderer):
        # docstring inherited
        dpicor = renderer.points_to_pixels(1.)
        pad = self.pad * dpicor
        sep = self.sep * dpicor

        bboxes = [c.get_bbox(renderer) for c in self.get_visible_children()]
        if not bboxes:
            return Bbox.from_bounds(0, 0, 0, 0).padded(pad), []

        (y0, y1), yoffsets = _get_aligned_offsets(
            [bbox.intervaly for bbox in bboxes], self.height, self.align)
        width, xoffsets = _get_packed_offsets(
            [bbox.width for bbox in bboxes], self.width, sep, self.mode)

        x0 = bboxes[0].x0
        xoffsets -= ([bbox.x0 for bbox in bboxes] - x0)

        return (Bbox.from_bounds(x0, y0, width, y1 - y0).padded(pad),
                [*zip(xoffsets, yoffsets)])


class PaddedBox(OffsetBox):
    """
    A container to add a padding around an `.Artist`.

    The `.PaddedBox` contains a `.FancyBboxPatch` that is used to visualize
    it when rendering.

    .. code-block:: none

       +----------------------------+
       |                            |
       |                            |
       |                            |
       | <--pad--> Artist           |
       |             ^              |
       |            pad             |
       |             v              |
       +----------------------------+

    Attributes
    ----------
    pad : float
        The padding in points.
    patch : `.FancyBboxPatch`
        When *draw_frame* is True, this `.FancyBboxPatch` is made visible and
        creates a border around the box.
    """

    def __init__(self, child, pad=0., *, draw_frame=False, patch_attrs=None):
        """
        Parameters
        ----------
        child : `~matplotlib.artist.Artist`
            The contained `.Artist`.
        pad : float, default: 0.0
            The padding in points. This will be scaled with the renderer dpi.
            In contrast, *width* and *height* are in *pixels* and thus not
            scaled.
        draw_frame : bool
            Whether to draw the contained `.FancyBboxPatch`.
        patch_attrs : dict or None
            Additional parameters passed to the contained `.FancyBboxPatch`.
        """
        super().__init__()
        self.pad = pad
        self._children = [child]
        self.patch = FancyBboxPatch(
            xy=(0.0, 0.0), width=1., height=1.,
            facecolor='w', edgecolor='k',
            mutation_scale=1,  # self.prop.get_size_in_points(),
            snap=True,
            visible=draw_frame,
            boxstyle="square,pad=0",
        )
        if patch_attrs is not None:
            self.patch.update(patch_attrs)

    def _get_bbox_and_child_offsets(self, renderer):
        # docstring inherited.
        pad = self.pad * renderer.points_to_pixels(1.)
        return (self._children[0].get_bbox(renderer).padded(pad), [(0, 0)])

    def draw(self, renderer):
        # docstring inherited
        bbox, offsets = self._get_bbox_and_child_offsets(renderer)
        px, py = self.get_offset(bbox, renderer)
        for c, (ox, oy) in zip(self.get_visible_children(), offsets):
            c.set_offset((px + ox, py + oy))

        self.draw_frame(renderer)

        for c in self.get_visible_children():
            c.draw(renderer)

        self.stale = False

    def update_frame(self, bbox, fontsize=None):
        self.patch.set_bounds(bbox.bounds)
        if fontsize:
            self.patch.set_mutation_scale(fontsize)
        self.stale = True

    def draw_frame(self, renderer):
        # update the location and size of the legend
        self.update_frame(self.get_window_extent(renderer))
        self.patch.draw(renderer)


class DrawingArea(OffsetBox):
    """
    The DrawingArea can contain any Artist as a child. The DrawingArea
    has a fixed width and height. The position of children relative to
    the parent is fixed. The children can be clipped at the
    boundaries of the parent.
    """

    def __init__(self, width, height, xdescent=0., ydescent=0., clip=False):
        """
        Parameters
        ----------
        width, height : float
            Width and height of the container box.
        xdescent, ydescent : float
            Descent of the box in x- and y-direction.
        clip : bool
            Whether to clip the children to the box.
        """
        super().__init__()
        self.width = width
        self.height = height
        self.xdescent = xdescent
        self.ydescent = ydescent
        self._clip_children = clip
        self.offset_transform = mtransforms.Affine2D()
        self.dpi_transform = mtransforms.Affine2D()

    @property
    def clip_children(self):
        """
        If the children of this DrawingArea should be clipped
        by DrawingArea bounding box.
        """
        return self._clip_children

    @clip_children.setter
    def clip_children(self, val):
        self._clip_children = bool(val)
        self.stale = True

    def get_transform(self):
        """
        Return the `~matplotlib.transforms.Transform` applied to the children.
        """
        return self.dpi_transform + self.offset_transform

    def set_transform(self, t):
        """
        set_transform is ignored.
        """

    def set_offset(self, xy):
        """
        Set the offset of the container.

        Parameters
        ----------
        xy : (float, float)
            The (x, y) coordinates of the offset in display units.
        """
        self._offset = xy
        self.offset_transform.clear()
        self.offset_transform.translate(xy[0], xy[1])
        self.stale = True

    def get_offset(self):
        """Return offset of the container."""
        return self._offset

    def get_bbox(self, renderer):
        # docstring inherited
        dpi_cor = renderer.points_to_pixels(1.)
        return Bbox.from_bounds(
            -self.xdescent * dpi_cor, -self.ydescent * dpi_cor,
            self.width * dpi_cor, self.height * dpi_cor)

    def add_artist(self, a):
        """Add an `.Artist` to the container box."""
        self._children.append(a)
        if not a.is_transform_set():
            a.set_transform(self.get_transform())
        if self.axes is not None:
            a.axes = self.axes
        fig = self.get_figure(root=False)
        if fig is not None:
            a.set_figure(fig)

    def draw(self, renderer):
        # docstring inherited

        dpi_cor = renderer.points_to_pixels(1.)
        self.dpi_transform.clear()
        self.dpi_transform.scale(dpi_cor)

        # At this point the DrawingArea has a transform
        # to the display space so the path created is
        # good for clipping children
        tpath = mtransforms.TransformedPath(
            mpath.Path([[0, 0], [0, self.height],
                        [self.width, self.height],
                        [self.width, 0]]),
            self.get_transform())
        for c in self._children:
            if self._clip_children and not (c.clipbox or c._clippath):
                c.set_clip_path(tpath)
            c.draw(renderer)

        _bbox_artist(self, renderer, fill=False, props=dict(pad=0.))
        self.stale = False


class TextArea(OffsetBox):
    """
    The TextArea is a container artist for a single Text instance.

    The text is placed at (0, 0) with baseline+left alignment, by default. The
    width and height of the TextArea instance is the width and height of its
    child text.
    """

    def __init__(self, s,
                 *,
                 textprops=None,
                 multilinebaseline=False,
                 ):
        """
        Parameters
        ----------
        s : str
            The text to be displayed.
        textprops : dict, default: {}
            Dictionary of keyword parameters to be passed to the `.Text`
            instance in the TextArea.
        multilinebaseline : bool, default: False
            Whether the baseline for multiline text is adjusted so that it
            is (approximately) center-aligned with single-line text.
        """
        if textprops is None:
            textprops = {}
        self._text = mtext.Text(0, 0, s, **textprops)
        super().__init__()
        self._children = [self._text]
        self.offset_transform = mtransforms.Affine2D()
        self._baseline_transform = mtransforms.Affine2D()
        self._text.set_transform(self.offset_transform +
                                 self._baseline_transform)
        self._multilinebaseline = multilinebaseline

    def set_text(self, s):
        """Set the text of this area as a string."""
        self._text.set_text(s)
        self.stale = True

    def get_text(self):
        """Return the string representation of this area's text."""
        return self._text.get_text()

    def set_multilinebaseline(self, t):
        """
        Set multilinebaseline.

        If True, the baseline for multiline text is adjusted so that it is
        (approximately) center-aligned with single-line text.  This is used
        e.g. by the legend implementation so that single-line labels are
        baseline-aligned, but multiline labels are "center"-aligned with them.
        """
        self._multilinebaseline = t
        self.stale = True

    def get_multilinebaseline(self):
        """
        Get multilinebaseline.
        """
        return self._multilinebaseline

    def set_transform(self, t):
        """
        set_transform is ignored.
        """

    def set_offset(self, xy):
        """
        Set the offset of the container.

        Parameters
        ----------
        xy : (float, float)
            The (x, y) coordinates of the offset in display units.
        """
        self._offset = xy
        self.offset_transform.clear()
        self.offset_transform.translate(xy[0], xy[1])
        self.stale = True

    def get_offset(self):
        """Return offset of the container."""
        return self._offset

    def get_bbox(self, renderer):
        _, h_, d_ = mtext._get_text_metrics_with_cache(
            renderer, "lp", self._text._fontproperties,
            ismath="TeX" if self._text.get_usetex() else False,
            dpi=self.get_figure(root=True).dpi)

        bbox, info, yd = self._text._get_layout(renderer)
        w, h = bbox.size

        self._baseline_transform.clear()

        if len(info) > 1 and self._multilinebaseline:
            yd_new = 0.5 * h - 0.5 * (h_ - d_)
            self._baseline_transform.translate(0, yd - yd_new)
            yd = yd_new
        else:  # single line
            h_d = max(h_ - d_, h - yd)
            h = h_d + yd

        ha = self._text.get_horizontalalignment()
        x0 = {"left": 0, "center": -w / 2, "right": -w}[ha]

        return Bbox.from_bounds(x0, -yd, w, h)

    def draw(self, renderer):
        # docstring inherited
        self._text.draw(renderer)
        _bbox_artist(self, renderer, fill=False, props=dict(pad=0.))
        self.stale = False


class AuxTransformBox(OffsetBox):
    """
    Offset Box with the aux_transform. Its children will be
    transformed with the aux_transform first then will be
    offsetted. The absolute coordinate of the aux_transform is meaning
    as it will be automatically adjust so that the left-lower corner
    of the bounding box of children will be set to (0, 0) before the
    offset transform.

    It is similar to drawing area, except that the extent of the box
    is not predetermined but calculated from the window extent of its
    children. Furthermore, the extent of the children will be
    calculated in the transformed coordinate.
    """
    def __init__(self, aux_transform):
        self.aux_transform = aux_transform
        super().__init__()
        self.offset_transform = mtransforms.Affine2D()
        # ref_offset_transform makes offset_transform always relative to the
        # lower-left corner of the bbox of its children.
        self.ref_offset_transform = mtransforms.Affine2D()

    def add_artist(self, a):
        """Add an `.Artist` to the container box."""
        self._children.append(a)
        a.set_transform(self.get_transform())
        self.stale = True

    def get_transform(self):
        """
        Return the :class:`~matplotlib.transforms.Transform` applied
        to the children
        """
        return (self.aux_transform
                + self.ref_offset_transform
                + self.offset_transform)

    def set_transform(self, t):
        """
        set_transform is ignored.
        """

    def set_offset(self, xy):
        """
        Set the offset of the container.

        Parameters
        ----------
        xy : (float, float)
            The (x, y) coordinates of the offset in display units.
        """
        self._offset = xy
        self.offset_transform.clear()
        self.offset_transform.translate(xy[0], xy[1])
        self.stale = True

    def get_offset(self):
        """Return offset of the container."""
        return self._offset

    def get_bbox(self, renderer):
        # clear the offset transforms
        _off = self.offset_transform.get_matrix()  # to be restored later
        self.ref_offset_transform.clear()
        self.offset_transform.clear()
        # calculate the extent
        bboxes = [c.get_window_extent(renderer) for c in self._children]
        ub = Bbox.union(bboxes)
        # adjust ref_offset_transform
        self.ref_offset_transform.translate(-ub.x0, -ub.y0)
        # restore offset transform
        self.offset_transform.set_matrix(_off)
        return Bbox.from_bounds(0, 0, ub.width, ub.height)

    def draw(self, renderer):
        # docstring inherited
        for c in self._children:
            c.draw(renderer)
        _bbox_artist(self, renderer, fill=False, props=dict(pad=0.))
        self.stale = False


class AnchoredOffsetbox(OffsetBox):
    """
    An offset box placed according to location *loc*.

    AnchoredOffsetbox has a single child.  When multiple children are needed,
    use an extra OffsetBox to enclose them.  By default, the offset box is
    anchored against its parent Axes. You may explicitly specify the
    *bbox_to_anchor*.
    """
    zorder = 5  # zorder of the legend

    # Location codes
    codes = {'upper right': 1,
             'upper left': 2,
             'lower left': 3,
             'lower right': 4,
             'right': 5,
             'center left': 6,
             'center right': 7,
             'lower center': 8,
             'upper center': 9,
             'center': 10,
             }

    def __init__(self, loc, *,
                 pad=0.4, borderpad=0.5,
                 child=None, prop=None, frameon=True,
                 bbox_to_anchor=None,
                 bbox_transform=None,
                 **kwargs):
        """
        Parameters
        ----------
        loc : str
            The box location.  Valid locations are
            'upper left', 'upper center', 'upper right',
            'center left', 'center', 'center right',
            'lower left', 'lower center', 'lower right'.
            For backward compatibility, numeric values are accepted as well.
            See the parameter *loc* of `.Legend` for details.
        pad : float, default: 0.4
            Padding around the child as fraction of the fontsize.
        borderpad : float, default: 0.5
            Padding between the offsetbox frame and the *bbox_to_anchor*.
        child : `.OffsetBox`
            The box that will be anchored.
        prop : `.FontProperties`
            This is only used as a reference for paddings. If not given,
            :rc:`legend.fontsize` is used.
        frameon : bool
            Whether to draw a frame around the box.
        bbox_to_anchor : `.BboxBase`, 2-tuple, or 4-tuple of floats
            Box that is used to position the legend in conjunction with *loc*.
        bbox_transform : None or :class:`matplotlib.transforms.Transform`
            The transform for the bounding box (*bbox_to_anchor*).
        **kwargs
            All other parameters are passed on to `.OffsetBox`.

        Notes
        -----
        See `.Legend` for a detailed description of the anchoring mechanism.
        """
        super().__init__(**kwargs)

        self.set_bbox_to_anchor(bbox_to_anchor, bbox_transform)
        self.set_child(child)

        if isinstance(loc, str):
            loc = _api.check_getitem(self.codes, loc=loc)

        self.loc = loc
        self.borderpad = borderpad
        self.pad = pad

        if prop is None:
            self.prop = FontProperties(size=mpl.rcParams["legend.fontsize"])
        else:
            self.prop = FontProperties._from_any(prop)
            if isinstance(prop, dict) and "size" not in prop:
                self.prop.set_size(mpl.rcParams["legend.fontsize"])

        self.patch = FancyBboxPatch(
            xy=(0.0, 0.0), width=1., height=1.,
            facecolor='w', edgecolor='k',
            mutation_scale=self.prop.get_size_in_points(),
            snap=True,
            visible=frameon,
            boxstyle="square,pad=0",
        )

    def set_child(self, child):
        """Set the child to be anchored."""
        self._child = child
        if child is not None:
            child.axes = self.axes
        self.stale = True

    def get_child(self):
        """Return the child."""
        return self._child

    def get_children(self):
        """Return the list of children."""
        return [self._child]

    def get_bbox(self, renderer):
        # docstring inherited
        fontsize = renderer.points_to_pixels(self.prop.get_size_in_points())
        pad = self.pad * fontsize
        return self.get_child().get_bbox(renderer).padded(pad)

    def get_bbox_to_anchor(self):
        """Return the bbox that the box is anchored to."""
        if self._bbox_to_anchor is None:
            return self.axes.bbox
        else:
            transform = self._bbox_to_anchor_transform
            if transform is None:
                return self._bbox_to_anchor
            else:
                return TransformedBbox(self._bbox_to_anchor, transform)

    def set_bbox_to_anchor(self, bbox, transform=None):
        """
        Set the bbox that the box is anchored to.

        *bbox* can be a Bbox instance, a list of [left, bottom, width,
        height], or a list of [left, bottom] where the width and
        height will be assumed to be zero. The bbox will be
        transformed to display coordinate by the given transform.
        """
        if bbox is None or isinstance(bbox, BboxBase):
            self._bbox_to_anchor = bbox
        else:
            try:
                l = len(bbox)
            except TypeError as err:
                raise ValueError(f"Invalid bbox: {bbox}") from err

            if l == 2:
                bbox = [bbox[0], bbox[1], 0, 0]

            self._bbox_to_anchor = Bbox.from_bounds(*bbox)

        self._bbox_to_anchor_transform = transform
        self.stale = True

    @_compat_get_offset
    def get_offset(self, bbox, renderer):
        # docstring inherited
        pad = (self.borderpad
               * renderer.points_to_pixels(self.prop.get_size_in_points()))
        bbox_to_anchor = self.get_bbox_to_anchor()
        x0, y0 = _get_anchored_bbox(
            self.loc, Bbox.from_bounds(0, 0, bbox.width, bbox.height),
            bbox_to_anchor, pad)
        return x0 - bbox.x0, y0 - bbox.y0

    def update_frame(self, bbox, fontsize=None):
        self.patch.set_bounds(bbox.bounds)
        if fontsize:
            self.patch.set_mutation_scale(fontsize)

    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible():
            return

        # update the location and size of the legend
        bbox = self.get_window_extent(renderer)
        fontsize = renderer.points_to_pixels(self.prop.get_size_in_points())
        self.update_frame(bbox, fontsize)
        self.patch.draw(renderer)

        px, py = self.get_offset(self.get_bbox(renderer), renderer)
        self.get_child().set_offset((px, py))
        self.get_child().draw(renderer)
        self.stale = False


def _get_anchored_bbox(loc, bbox, parentbbox, borderpad):
    """
    Return the (x, y) position of the *bbox* anchored at the *parentbbox* with
    the *loc* code with the *borderpad*.
    """
    # This is only called internally and *loc* should already have been
    # validated.  If 0 (None), we just let ``bbox.anchored`` raise.
    c = [None, "NE", "NW", "SW", "SE", "E", "W", "E", "S", "N", "C"][loc]
    container = parentbbox.padded(-borderpad)
    return bbox.anchored(c, container=container).p0


class AnchoredText(AnchoredOffsetbox):
    """
    AnchoredOffsetbox with Text.
    """

    def __init__(self, s, loc, *, pad=0.4, borderpad=0.5, prop=None, **kwargs):
        """
        Parameters
        ----------
        s : str
            Text.

        loc : str
            Location code. See `AnchoredOffsetbox`.

        pad : float, default: 0.4
            Padding around the text as fraction of the fontsize.

        borderpad : float, default: 0.5
            Spacing between the offsetbox frame and the *bbox_to_anchor*.

        prop : dict, optional
            Dictionary of keyword parameters to be passed to the
            `~matplotlib.text.Text` instance contained inside AnchoredText.

        **kwargs
            All other parameters are passed to `AnchoredOffsetbox`.
        """

        if prop is None:
            prop = {}
        badkwargs = {'va', 'verticalalignment'}
        if badkwargs & set(prop):
            raise ValueError(
                'Mixing verticalalignment with AnchoredText is not supported.')

        self.txt = TextArea(s, textprops=prop)
        fp = self.txt._text.get_fontproperties()
        super().__init__(
            loc, pad=pad, borderpad=borderpad, child=self.txt, prop=fp,
            **kwargs)


class OffsetImage(OffsetBox):

    def __init__(self, arr, *,
                 zoom=1,
                 cmap=None,
                 norm=None,
                 interpolation=None,
                 origin=None,
                 filternorm=True,
                 filterrad=4.0,
                 resample=False,
                 dpi_cor=True,
                 **kwargs
                 ):

        super().__init__()
        self._dpi_cor = dpi_cor

        self.image = BboxImage(bbox=self.get_window_extent,
                               cmap=cmap,
                               norm=norm,
                               interpolation=interpolation,
                               origin=origin,
                               filternorm=filternorm,
                               filterrad=filterrad,
                               resample=resample,
                               **kwargs
                               )

        self._children = [self.image]

        self.set_zoom(zoom)
        self.set_data(arr)

    def set_data(self, arr):
        self._data = np.asarray(arr)
        self.image.set_data(self._data)
        self.stale = True

    def get_data(self):
        return self._data

    def set_zoom(self, zoom):
        self._zoom = zoom
        self.stale = True

    def get_zoom(self):
        return self._zoom

    def get_offset(self):
        """Return offset of the container."""
        return self._offset

    def get_children(self):
        return [self.image]

    def get_bbox(self, renderer):
        dpi_cor = renderer.points_to_pixels(1.) if self._dpi_cor else 1.
        zoom = self.get_zoom()
        data = self.get_data()
        ny, nx = data.shape[:2]
        w, h = dpi_cor * nx * zoom, dpi_cor * ny * zoom
        return Bbox.from_bounds(0, 0, w, h)

    def draw(self, renderer):
        # docstring inherited
        self.image.draw(renderer)
        # bbox_artist(self, renderer, fill=False, props=dict(pad=0.))
        self.stale = False


class AnnotationBbox(martist.Artist, mtext._AnnotationBase):
    """
    Container for an `OffsetBox` referring to a specific position *xy*.

    Optionally an arrow pointing from the offsetbox to *xy* can be drawn.

    This is like `.Annotation`, but with `OffsetBox` instead of `.Text`.
    """

    zorder = 3

    def __str__(self):
        return f"AnnotationBbox({self.xy[0]:g},{self.xy[1]:g})"

    @_docstring.interpd
    def __init__(self, offsetbox, xy, xybox=None, xycoords='data', boxcoords=None, *,
                 frameon=True, pad=0.4,  # FancyBboxPatch boxstyle.
                 annotation_clip=None,
                 box_alignment=(0.5, 0.5),
                 bboxprops=None,
                 arrowprops=None,
                 fontsize=None,
                 **kwargs):
        """
        Parameters
        ----------
        offsetbox : `OffsetBox`

        xy : (float, float)
            The point *(x, y)* to annotate. The coordinate system is determined
            by *xycoords*.

        xybox : (float, float), default: *xy*
            The position *(x, y)* to place the text at. The coordinate system
            is determined by *boxcoords*.

        xycoords : single or two-tuple of str or `.Artist` or `.Transform` or \
callable, default: 'data'
            The coordinate system that *xy* is given in. See the parameter
            *xycoords* in `.Annotation` for a detailed description.

        boxcoords : single or two-tuple of str or `.Artist` or `.Transform` \
or callable, default: value of *xycoords*
            The coordinate system that *xybox* is given in. See the parameter
            *textcoords* in `.Annotation` for a detailed description.

        frameon : bool, default: True
            By default, the text is surrounded by a white `.FancyBboxPatch`
            (accessible as the ``patch`` attribute of the `.AnnotationBbox`).
            If *frameon* is set to False, this patch is made invisible.

        annotation_clip: bool or None, default: None
            Whether to clip (i.e. not draw) the annotation when the annotation
            point *xy* is outside the Axes area.

            - If *True*, the annotation will be clipped when *xy* is outside
              the Axes.
            - If *False*, the annotation will always be drawn.
            - If *None*, the annotation will be clipped when *xy* is outside
              the Axes and *xycoords* is 'data'.

        pad : float, default: 0.4
            Padding around the offsetbox.

        box_alignment : (float, float)
            A tuple of two floats for a vertical and horizontal alignment of
            the offset box w.r.t. the *boxcoords*.
            The lower-left corner is (0, 0) and upper-right corner is (1, 1).

        bboxprops : dict, optional
            A dictionary of properties to set for the annotation bounding box,
            for example *boxstyle* and *alpha*.  See `.FancyBboxPatch` for
            details.

        arrowprops: dict, optional
            Arrow properties, see `.Annotation` for description.

        fontsize: float or str, optional
            Translated to points and passed as *mutation_scale* into
            `.FancyBboxPatch` to scale attributes of the box style (e.g. pad
            or rounding_size).  The name is chosen in analogy to `.Text` where
            *fontsize* defines the mutation scale as well.  If not given,
            :rc:`legend.fontsize` is used.  See `.Text.set_fontsize` for valid
            values.

        **kwargs
            Other `AnnotationBbox` properties.  See `.AnnotationBbox.set` for
            a list.
        """

        martist.Artist.__init__(self)
        mtext._AnnotationBase.__init__(
            self, xy, xycoords=xycoords, annotation_clip=annotation_clip)

        self.offsetbox = offsetbox
        self.arrowprops = arrowprops.copy() if arrowprops is not None else None
        self.set_fontsize(fontsize)
        self.xybox = xybox if xybox is not None else xy
        self.boxcoords = boxcoords if boxcoords is not None else xycoords
        self._box_alignment = box_alignment

        if arrowprops is not None:
            self._arrow_relpos = self.arrowprops.pop("relpos", (0.5, 0.5))
            self.arrow_patch = FancyArrowPatch((0, 0), (1, 1),
                                               **self.arrowprops)
        else:
            self._arrow_relpos = None
            self.arrow_patch = None

        self.patch = FancyBboxPatch(  # frame
            xy=(0.0, 0.0), width=1., height=1.,
            facecolor='w', edgecolor='k',
            mutation_scale=self.prop.get_size_in_points(),
            snap=True,
            visible=frameon,
        )
        self.patch.set_boxstyle("square", pad=pad)
        if bboxprops:
            self.patch.set(**bboxprops)

        self._internal_update(kwargs)

    @property
    def xyann(self):
        return self.xybox

    @xyann.setter
    def xyann(self, xyann):
        self.xybox = xyann
        self.stale = True

    @property
    def anncoords(self):
        return self.boxcoords

    @anncoords.setter
    def anncoords(self, coords):
        self.boxcoords = coords
        self.stale = True

    def contains(self, mouseevent):
        if self._different_canvas(mouseevent):
            return False, {}
        if not self._check_xy(None):
            return False, {}
        return self.offsetbox.contains(mouseevent)
        # self.arrow_patch is currently not checked as this can be a line - JJ

    def get_children(self):
        children = [self.offsetbox, self.patch]
        if self.arrow_patch:
            children.append(self.arrow_patch)
        return children

    def set_figure(self, fig):
        if self.arrow_patch is not None:
            self.arrow_patch.set_figure(fig)
        self.offsetbox.set_figure(fig)
        martist.Artist.set_figure(self, fig)

    def set_fontsize(self, s=None):
        """
        Set the fontsize in points.

        If *s* is not given, reset to :rc:`legend.fontsize`.
        """
        if s is None:
            s = mpl.rcParams["legend.fontsize"]

        self.prop = FontProperties(size=s)
        self.stale = True

    def get_fontsize(self):
        """Return the fontsize in points."""
        return self.prop.get_size_in_points()

    def get_window_extent(self, renderer=None):
        # docstring inherited
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        self.update_positions(renderer)
        return Bbox.union([child.get_window_extent(renderer)
                           for child in self.get_children()])

    def get_tightbbox(self, renderer=None):
        # docstring inherited
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        self.update_positions(renderer)
        return Bbox.union([child.get_tightbbox(renderer)
                           for child in self.get_children()])

    def update_positions(self, renderer):
        """Update pixel positions for the annotated point, the text, and the arrow."""

        ox0, oy0 = self._get_xy(renderer, self.xybox, self.boxcoords)
        bbox = self.offsetbox.get_bbox(renderer)
        fw, fh = self._box_alignment
        self.offsetbox.set_offset(
            (ox0 - fw*bbox.width - bbox.x0, oy0 - fh*bbox.height - bbox.y0))

        bbox = self.offsetbox.get_window_extent(renderer)
        self.patch.set_bounds(bbox.bounds)

        mutation_scale = renderer.points_to_pixels(self.get_fontsize())
        self.patch.set_mutation_scale(mutation_scale)

        if self.arrowprops:
            # Use FancyArrowPatch if self.arrowprops has "arrowstyle" key.

            # Adjust the starting point of the arrow relative to the textbox.
            # TODO: Rotation needs to be accounted.
            arrow_begin = bbox.p0 + bbox.size * self._arrow_relpos
            arrow_end = self._get_position_xy(renderer)
            # The arrow (from arrow_begin to arrow_end) will be first clipped
            # by patchA and patchB, then shrunk by shrinkA and shrinkB (in
            # points).  If patch A is not set, self.bbox_patch is used.
            self.arrow_patch.set_positions(arrow_begin, arrow_end)

            if "mutation_scale" in self.arrowprops:
                mutation_scale = renderer.points_to_pixels(
                    self.arrowprops["mutation_scale"])
                # Else, use fontsize-based mutation_scale defined above.
            self.arrow_patch.set_mutation_scale(mutation_scale)

            patchA = self.arrowprops.get("patchA", self.patch)
            self.arrow_patch.set_patchA(patchA)

    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible() or not self._check_xy(renderer):
            return
        renderer.open_group(self.__class__.__name__, gid=self.get_gid())
        self.update_positions(renderer)
        if self.arrow_patch is not None:
            if (self.arrow_patch.get_figure(root=False) is None and
                    (fig := self.get_figure(root=False)) is not None):
                self.arrow_patch.set_figure(fig)
            self.arrow_patch.draw(renderer)
        self.patch.draw(renderer)
        self.offsetbox.draw(renderer)
        renderer.close_group(self.__class__.__name__)
        self.stale = False


class DraggableBase:
    """
    Helper base class for a draggable artist (legend, offsetbox).

    Derived classes must override the following methods::

        def save_offset(self):
            '''
            Called when the object is picked for dragging; should save the
            reference position of the artist.
            '''

        def update_offset(self, dx, dy):
            '''
            Called during the dragging; (*dx*, *dy*) is the pixel offset from
            the point where the mouse drag started.
            '''

    Optionally, you may override the following method::

        def finalize_offset(self):
            '''Called when the mouse is released.'''

    In the current implementation of `.DraggableLegend` and
    `DraggableAnnotation`, `update_offset` places the artists in display
    coordinates, and `finalize_offset` recalculates their position in axes
    coordinate and set a relevant attribute.
    """

    def __init__(self, ref_artist, use_blit=False):
        self.ref_artist = ref_artist
        if not ref_artist.pickable():
            ref_artist.set_picker(self._picker)
        self.got_artist = False
        self._use_blit = use_blit and self.canvas.supports_blit
        callbacks = self.canvas.callbacks
        self._disconnectors = [
            functools.partial(
                callbacks.disconnect, callbacks._connect_picklable(name, func))
            for name, func in [
                ("pick_event", self.on_pick),
                ("button_release_event", self.on_release),
                ("motion_notify_event", self.on_motion),
            ]
        ]

    @staticmethod
    def _picker(artist, mouseevent):
        # A custom picker to prevent dragging on mouse scroll events
        return (artist.contains(mouseevent) and mouseevent.name != "scroll_event"), {}

    # A property, not an attribute, to maintain picklability.
    canvas = property(lambda self: self.ref_artist.get_figure(root=True).canvas)
    cids = property(lambda self: [
        disconnect.args[0] for disconnect in self._disconnectors[:2]])

    def on_motion(self, evt):
        if self._check_still_parented() and self.got_artist:
            dx = evt.x - self.mouse_x
            dy = evt.y - self.mouse_y
            self.update_offset(dx, dy)
            if self._use_blit:
                self.canvas.restore_region(self.background)
                self.ref_artist.draw(
                    self.ref_artist.get_figure(root=True)._get_renderer())
                self.canvas.blit()
            else:
                self.canvas.draw()

    def on_pick(self, evt):
        if self._check_still_parented():
            if evt.artist == self.ref_artist:
                self.mouse_x = evt.mouseevent.x
                self.mouse_y = evt.mouseevent.y
                self.save_offset()
                self.got_artist = True
            if self.got_artist and self._use_blit:
                self.ref_artist.set_animated(True)
                self.canvas.draw()
                fig = self.ref_artist.get_figure(root=False)
                self.background = self.canvas.copy_from_bbox(fig.bbox)
                self.ref_artist.draw(fig._get_renderer())
                self.canvas.blit()

    def on_release(self, event):
        if self._check_still_parented() and self.got_artist:
            self.finalize_offset()
            self.got_artist = False
            if self._use_blit:
                self.canvas.restore_region(self.background)
                self.ref_artist.draw(self.ref_artist.figure._get_renderer())
                self.canvas.blit()
                self.ref_artist.set_animated(False)

    def _check_still_parented(self):
        if self.ref_artist.get_figure(root=False) is None:
            self.disconnect()
            return False
        else:
            return True

    def disconnect(self):
        """Disconnect the callbacks."""
        for disconnector in self._disconnectors:
            disconnector()

    def save_offset(self):
        pass

    def update_offset(self, dx, dy):
        pass

    def finalize_offset(self):
        pass


class DraggableOffsetBox(DraggableBase):
    def __init__(self, ref_artist, offsetbox, use_blit=False):
        super().__init__(ref_artist, use_blit=use_blit)
        self.offsetbox = offsetbox

    def save_offset(self):
        offsetbox = self.offsetbox
        renderer = offsetbox.get_figure(root=True)._get_renderer()
        offset = offsetbox.get_offset(offsetbox.get_bbox(renderer), renderer)
        self.offsetbox_x, self.offsetbox_y = offset
        self.offsetbox.set_offset(offset)

    def update_offset(self, dx, dy):
        loc_in_canvas = self.offsetbox_x + dx, self.offsetbox_y + dy
        self.offsetbox.set_offset(loc_in_canvas)

    def get_loc_in_canvas(self):
        offsetbox = self.offsetbox
        renderer = offsetbox.get_figure(root=True)._get_renderer()
        bbox = offsetbox.get_bbox(renderer)
        ox, oy = offsetbox._offset
        loc_in_canvas = (ox + bbox.x0, oy + bbox.y0)
        return loc_in_canvas


class DraggableAnnotation(DraggableBase):
    def __init__(self, annotation, use_blit=False):
        super().__init__(annotation, use_blit=use_blit)
        self.annotation = annotation

    def save_offset(self):
        ann = self.annotation
        self.ox, self.oy = ann.get_transform().transform(ann.xyann)

    def update_offset(self, dx, dy):
        ann = self.annotation
        ann.xyann = ann.get_transform().inverted().transform(
            (self.ox + dx, self.oy + dy))

# === NexusCore/openenv\Lib\site-packages\dateutil\parser\_parser.py ===
# -*- coding: utf-8 -*-
"""
This module offers a generic date/time string parser which is able to parse
most known formats to represent a date and/or time.

This module attempts to be forgiving with regards to unlikely input formats,
returning a datetime object even for dates which are ambiguous. If an element
of a date/time stamp is omitted, the following rules are applied:

- If AM or PM is left unspecified, a 24-hour clock is assumed, however, an hour
  on a 12-hour clock (``0 <= hour <= 12``) *must* be specified if AM or PM is
  specified.
- If a time zone is omitted, a timezone-naive datetime is returned.

If any other elements are missing, they are taken from the
:class:`datetime.datetime` object passed to the parameter ``default``. If this
results in a day number exceeding the valid number of days per month, the
value falls back to the end of the month.

Additional resources about date/time string formats can be found below:

- `A summary of the international standard date and time notation
  <https://www.cl.cam.ac.uk/~mgk25/iso-time.html>`_
- `W3C Date and Time Formats <https://www.w3.org/TR/NOTE-datetime>`_
- `Time Formats (Planetary Rings Node) <https://pds-rings.seti.org:443/tools/time_formats.html>`_
- `CPAN ParseDate module
  <https://metacpan.org/pod/release/MUIR/Time-modules-2013.0912/lib/Time/ParseDate.pm>`_
- `Java SimpleDateFormat Class
  <https://docs.oracle.com/javase/6/docs/api/java/text/SimpleDateFormat.html>`_
"""
from __future__ import unicode_literals

import datetime
import re
import string
import time
import warnings

from calendar import monthrange
from io import StringIO

import six
from six import integer_types, text_type

from decimal import Decimal

from warnings import warn

from .. import relativedelta
from .. import tz

__all__ = ["parse", "parserinfo", "ParserError"]


# TODO: pandas.core.tools.datetimes imports this explicitly.  Might be worth
# making public and/or figuring out if there is something we can
# take off their plate.
class _timelex(object):
    # Fractional seconds are sometimes split by a comma
    _split_decimal = re.compile("([.,])")

    def __init__(self, instream):
        if isinstance(instream, (bytes, bytearray)):
            instream = instream.decode()

        if isinstance(instream, text_type):
            instream = StringIO(instream)
        elif getattr(instream, 'read', None) is None:
            raise TypeError('Parser must be a string or character stream, not '
                            '{itype}'.format(itype=instream.__class__.__name__))

        self.instream = instream
        self.charstack = []
        self.tokenstack = []
        self.eof = False

    def get_token(self):
        """
        This function breaks the time string into lexical units (tokens), which
        can be parsed by the parser. Lexical units are demarcated by changes in
        the character set, so any continuous string of letters is considered
        one unit, any continuous string of numbers is considered one unit.

        The main complication arises from the fact that dots ('.') can be used
        both as separators (e.g. "Sep.20.2009") or decimal points (e.g.
        "4:30:21.447"). As such, it is necessary to read the full context of
        any dot-separated strings before breaking it into tokens; as such, this
        function maintains a "token stack", for when the ambiguous context
        demands that multiple tokens be parsed at once.
        """
        if self.tokenstack:
            return self.tokenstack.pop(0)

        seenletters = False
        token = None
        state = None

        while not self.eof:
            # We only realize that we've reached the end of a token when we
            # find a character that's not part of the current token - since
            # that character may be part of the next token, it's stored in the
            # charstack.
            if self.charstack:
                nextchar = self.charstack.pop(0)
            else:
                nextchar = self.instream.read(1)
                while nextchar == '\x00':
                    nextchar = self.instream.read(1)

            if not nextchar:
                self.eof = True
                break
            elif not state:
                # First character of the token - determines if we're starting
                # to parse a word, a number or something else.
                token = nextchar
                if self.isword(nextchar):
                    state = 'a'
                elif self.isnum(nextchar):
                    state = '0'
                elif self.isspace(nextchar):
                    token = ' '
                    break  # emit token
                else:
                    break  # emit token
            elif state == 'a':
                # If we've already started reading a word, we keep reading
                # letters until we find something that's not part of a word.
                seenletters = True
                if self.isword(nextchar):
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break  # emit token
            elif state == '0':
                # If we've already started reading a number, we keep reading
                # numbers until we find something that doesn't fit.
                if self.isnum(nextchar):
                    token += nextchar
                elif nextchar == '.' or (nextchar == ',' and len(token) >= 2):
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break  # emit token
            elif state == 'a.':
                # If we've seen some letters and a dot separator, continue
                # parsing, and the tokens will be broken up later.
                seenletters = True
                if nextchar == '.' or self.isword(nextchar):
                    token += nextchar
                elif self.isnum(nextchar) and token[-1] == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break  # emit token
            elif state == '0.':
                # If we've seen at least one dot separator, keep going, we'll
                # break up the tokens later.
                if nextchar == '.' or self.isnum(nextchar):
                    token += nextchar
                elif self.isword(nextchar) and token[-1] == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break  # emit token

        if (state in ('a.', '0.') and (seenletters or token.count('.') > 1 or
                                       token[-1] in '.,')):
            l = self._split_decimal.split(token)
            token = l[0]
            for tok in l[1:]:
                if tok:
                    self.tokenstack.append(tok)

        if state == '0.' and token.count('.') == 0:
            token = token.replace(',', '.')

        return token

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_token()
        if token is None:
            raise StopIteration

        return token

    def next(self):
        return self.__next__()  # Python 2.x support

    @classmethod
    def split(cls, s):
        return list(cls(s))

    @classmethod
    def isword(cls, nextchar):
        """ Whether or not the next character is part of a word """
        return nextchar.isalpha()

    @classmethod
    def isnum(cls, nextchar):
        """ Whether the next character is part of a number """
        return nextchar.isdigit()

    @classmethod
    def isspace(cls, nextchar):
        """ Whether the next character is whitespace """
        return nextchar.isspace()


class _resultbase(object):

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def _repr(self, classname):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, repr(value)))
        return "%s(%s)" % (classname, ", ".join(l))

    def __len__(self):
        return (sum(getattr(self, attr) is not None
                    for attr in self.__slots__))

    def __repr__(self):
        return self._repr(self.__class__.__name__)


class parserinfo(object):
    """
    Class which handles what inputs are accepted. Subclass this to customize
    the language and acceptable values for each parameter.

    :param dayfirst:
        Whether to interpret the first value in an ambiguous 3-integer date
        (e.g. 01/05/09) as the day (``True``) or month (``False``). If
        ``yearfirst`` is set to ``True``, this distinguishes between YDM
        and YMD. Default is ``False``.

    :param yearfirst:
        Whether to interpret the first value in an ambiguous 3-integer date
        (e.g. 01/05/09) as the year. If ``True``, the first number is taken
        to be the year, otherwise the last number is taken to be the year.
        Default is ``False``.
    """

    # m from a.m/p.m, t from ISO T separator
    JUMP = [" ", ".", ",", ";", "-", "/", "'",
            "at", "on", "and", "ad", "m", "t", "of",
            "st", "nd", "rd", "th"]

    WEEKDAYS = [("Mon", "Monday"),
                ("Tue", "Tuesday"),     # TODO: "Tues"
                ("Wed", "Wednesday"),
                ("Thu", "Thursday"),    # TODO: "Thurs"
                ("Fri", "Friday"),
                ("Sat", "Saturday"),
                ("Sun", "Sunday")]
    MONTHS = [("Jan", "January"),
              ("Feb", "February"),      # TODO: "Febr"
              ("Mar", "March"),
              ("Apr", "April"),
              ("May", "May"),
              ("Jun", "June"),
              ("Jul", "July"),
              ("Aug", "August"),
              ("Sep", "Sept", "September"),
              ("Oct", "October"),
              ("Nov", "November"),
              ("Dec", "December")]
    HMS = [("h", "hour", "hours"),
           ("m", "minute", "minutes"),
           ("s", "second", "seconds")]
    AMPM = [("am", "a"),
            ("pm", "p")]
    UTCZONE = ["UTC", "GMT", "Z", "z"]
    PERTAIN = ["of"]
    TZOFFSET = {}
    # TODO: ERA = ["AD", "BC", "CE", "BCE", "Stardate",
    #              "Anno Domini", "Year of Our Lord"]

    def __init__(self, dayfirst=False, yearfirst=False):
        self._jump = self._convert(self.JUMP)
        self._weekdays = self._convert(self.WEEKDAYS)
        self._months = self._convert(self.MONTHS)
        self._hms = self._convert(self.HMS)
        self._ampm = self._convert(self.AMPM)
        self._utczone = self._convert(self.UTCZONE)
        self._pertain = self._convert(self.PERTAIN)

        self.dayfirst = dayfirst
        self.yearfirst = yearfirst

        self._year = time.localtime().tm_year
        self._century = self._year // 100 * 100

    def _convert(self, lst):
        dct = {}
        for i, v in enumerate(lst):
            if isinstance(v, tuple):
                for v in v:
                    dct[v.lower()] = i
            else:
                dct[v.lower()] = i
        return dct

    def jump(self, name):
        return name.lower() in self._jump

    def weekday(self, name):
        try:
            return self._weekdays[name.lower()]
        except KeyError:
            pass
        return None

    def month(self, name):
        try:
            return self._months[name.lower()] + 1
        except KeyError:
            pass
        return None

    def hms(self, name):
        try:
            return self._hms[name.lower()]
        except KeyError:
            return None

    def ampm(self, name):
        try:
            return self._ampm[name.lower()]
        except KeyError:
            return None

    def pertain(self, name):
        return name.lower() in self._pertain

    def utczone(self, name):
        return name.lower() in self._utczone

    def tzoffset(self, name):
        if name in self._utczone:
            return 0

        return self.TZOFFSET.get(name)

    def convertyear(self, year, century_specified=False):
        """
        Converts two-digit years to year within [-50, 49]
        range of self._year (current local time)
        """

        # Function contract is that the year is always positive
        assert year >= 0

        if year < 100 and not century_specified:
            # assume current century to start
            year += self._century

            if year >= self._year + 50:  # if too far in future
                year -= 100
            elif year < self._year - 50:  # if too far in past
                year += 100

        return year

    def validate(self, res):
        # move to info
        if res.year is not None:
            res.year = self.convertyear(res.year, res.century_specified)

        if ((res.tzoffset == 0 and not res.tzname) or
             (res.tzname == 'Z' or res.tzname == 'z')):
            res.tzname = "UTC"
            res.tzoffset = 0
        elif res.tzoffset != 0 and res.tzname and self.utczone(res.tzname):
            res.tzoffset = 0
        return True


class _ymd(list):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.century_specified = False
        self.dstridx = None
        self.mstridx = None
        self.ystridx = None

    @property
    def has_year(self):
        return self.ystridx is not None

    @property
    def has_month(self):
        return self.mstridx is not None

    @property
    def has_day(self):
        return self.dstridx is not None

    def could_be_day(self, value):
        if self.has_day:
            return False
        elif not self.has_month:
            return 1 <= value <= 31
        elif not self.has_year:
            # Be permissive, assume leap year
            month = self[self.mstridx]
            return 1 <= value <= monthrange(2000, month)[1]
        else:
            month = self[self.mstridx]
            year = self[self.ystridx]
            return 1 <= value <= monthrange(year, month)[1]

    def append(self, val, label=None):
        if hasattr(val, '__len__'):
            if val.isdigit() and len(val) > 2:
                self.century_specified = True
                if label not in [None, 'Y']:  # pragma: no cover
                    raise ValueError(label)
                label = 'Y'
        elif val > 100:
            self.century_specified = True
            if label not in [None, 'Y']:  # pragma: no cover
                raise ValueError(label)
            label = 'Y'

        super(self.__class__, self).append(int(val))

        if label == 'M':
            if self.has_month:
                raise ValueError('Month is already set')
            self.mstridx = len(self) - 1
        elif label == 'D':
            if self.has_day:
                raise ValueError('Day is already set')
            self.dstridx = len(self) - 1
        elif label == 'Y':
            if self.has_year:
                raise ValueError('Year is already set')
            self.ystridx = len(self) - 1

    def _resolve_from_stridxs(self, strids):
        """
        Try to resolve the identities of year/month/day elements using
        ystridx, mstridx, and dstridx, if enough of these are specified.
        """
        if len(self) == 3 and len(strids) == 2:
            # we can back out the remaining stridx value
            missing = [x for x in range(3) if x not in strids.values()]
            key = [x for x in ['y', 'm', 'd'] if x not in strids]
            assert len(missing) == len(key) == 1
            key = key[0]
            val = missing[0]
            strids[key] = val

        assert len(self) == len(strids)  # otherwise this should not be called
        out = {key: self[strids[key]] for key in strids}
        return (out.get('y'), out.get('m'), out.get('d'))

    def resolve_ymd(self, yearfirst, dayfirst):
        len_ymd = len(self)
        year, month, day = (None, None, None)

        strids = (('y', self.ystridx),
                  ('m', self.mstridx),
                  ('d', self.dstridx))

        strids = {key: val for key, val in strids if val is not None}
        if (len(self) == len(strids) > 0 or
                (len(self) == 3 and len(strids) == 2)):
            return self._resolve_from_stridxs(strids)

        mstridx = self.mstridx

        if len_ymd > 3:
            raise ValueError("More than three YMD values")
        elif len_ymd == 1 or (mstridx is not None and len_ymd == 2):
            # One member, or two members with a month string
            if mstridx is not None:
                month = self[mstridx]
                # since mstridx is 0 or 1, self[mstridx-1] always
                # looks up the other element
                other = self[mstridx - 1]
            else:
                other = self[0]

            if len_ymd > 1 or mstridx is None:
                if other > 31:
                    year = other
                else:
                    day = other

        elif len_ymd == 2:
            # Two members with numbers
            if self[0] > 31:
                # 99-01
                year, month = self
            elif self[1] > 31:
                # 01-99
                month, year = self
            elif dayfirst and self[1] <= 12:
                # 13-01
                day, month = self
            else:
                # 01-13
                month, day = self

        elif len_ymd == 3:
            # Three members
            if mstridx == 0:
                if self[1] > 31:
                    # Apr-2003-25
                    month, year, day = self
                else:
                    month, day, year = self
            elif mstridx == 1:
                if self[0] > 31 or (yearfirst and self[2] <= 31):
                    # 99-Jan-01
                    year, month, day = self
                else:
                    # 01-Jan-01
                    # Give precedence to day-first, since
                    # two-digit years is usually hand-written.
                    day, month, year = self

            elif mstridx == 2:
                # WTF!?
                if self[1] > 31:
                    # 01-99-Jan
                    day, year, month = self
                else:
                    # 99-01-Jan
                    year, day, month = self

            else:
                if (self[0] > 31 or
                    self.ystridx == 0 or
                        (yearfirst and self[1] <= 12 and self[2] <= 31)):
                    # 99-01-01
                    if dayfirst and self[2] <= 12:
                        year, day, month = self
                    else:
                        year, month, day = self
                elif self[0] > 12 or (dayfirst and self[1] <= 12):
                    # 13-01-01
                    day, month, year = self
                else:
                    # 01-13-01
                    month, day, year = self

        return year, month, day


class parser(object):
    def __init__(self, info=None):
        self.info = info or parserinfo()

    def parse(self, timestr, default=None,
              ignoretz=False, tzinfos=None, **kwargs):
        """
        Parse the date/time string into a :class:`datetime.datetime` object.

        :param timestr:
            Any date/time string using the supported formats.

        :param default:
            The default datetime object, if this is a datetime object and not
            ``None``, elements specified in ``timestr`` replace elements in the
            default object.

        :param ignoretz:
            If set ``True``, time zones in parsed strings are ignored and a
            naive :class:`datetime.datetime` object is returned.

        :param tzinfos:
            Additional time zone names / aliases which may be present in the
            string. This argument maps time zone names (and optionally offsets
            from those time zones) to time zones. This parameter can be a
            dictionary with timezone aliases mapping time zone names to time
            zones or a function taking two parameters (``tzname`` and
            ``tzoffset``) and returning a time zone.

            The timezones to which the names are mapped can be an integer
            offset from UTC in seconds or a :class:`tzinfo` object.

            .. doctest::
               :options: +NORMALIZE_WHITESPACE

                >>> from dateutil.parser import parse
                >>> from dateutil.tz import gettz
                >>> tzinfos = {"BRST": -7200, "CST": gettz("America/Chicago")}
                >>> parse("2012-01-19 17:21:00 BRST", tzinfos=tzinfos)
                datetime.datetime(2012, 1, 19, 17, 21, tzinfo=tzoffset(u'BRST', -7200))
                >>> parse("2012-01-19 17:21:00 CST", tzinfos=tzinfos)
                datetime.datetime(2012, 1, 19, 17, 21,
                                  tzinfo=tzfile('/usr/share/zoneinfo/America/Chicago'))

            This parameter is ignored if ``ignoretz`` is set.

        :param \\*\\*kwargs:
            Keyword arguments as passed to ``_parse()``.

        :return:
            Returns a :class:`datetime.datetime` object or, if the
            ``fuzzy_with_tokens`` option is ``True``, returns a tuple, the
            first element being a :class:`datetime.datetime` object, the second
            a tuple containing the fuzzy tokens.

        :raises ParserError:
            Raised for invalid or unknown string format, if the provided
            :class:`tzinfo` is not in a valid format, or if an invalid date
            would be created.

        :raises TypeError:
            Raised for non-string or character stream input.

        :raises OverflowError:
            Raised if the parsed date exceeds the largest valid C integer on
            your system.
        """

        if default is None:
            default = datetime.datetime.now().replace(hour=0, minute=0,
                                                      second=0, microsecond=0)

        res, skipped_tokens = self._parse(timestr, **kwargs)

        if res is None:
            raise ParserError("Unknown string format: %s", timestr)

        if len(res) == 0:
            raise ParserError("String does not contain a date: %s", timestr)

        try:
            ret = self._build_naive(res, default)
        except ValueError as e:
            six.raise_from(ParserError(str(e) + ": %s", timestr), e)

        if not ignoretz:
            ret = self._build_tzaware(ret, res, tzinfos)

        if kwargs.get('fuzzy_with_tokens', False):
            return ret, skipped_tokens
        else:
            return ret

    class _result(_resultbase):
        __slots__ = ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond",
                     "tzname", "tzoffset", "ampm","any_unused_tokens"]

    def _parse(self, timestr, dayfirst=None, yearfirst=None, fuzzy=False,
               fuzzy_with_tokens=False):
        """
        Private method which performs the heavy lifting of parsing, called from
        ``parse()``, which passes on its ``kwargs`` to this function.

        :param timestr:
            The string to parse.

        :param dayfirst:
            Whether to interpret the first value in an ambiguous 3-integer date
            (e.g. 01/05/09) as the day (``True``) or month (``False``). If
            ``yearfirst`` is set to ``True``, this distinguishes between YDM
            and YMD. If set to ``None``, this value is retrieved from the
            current :class:`parserinfo` object (which itself defaults to
            ``False``).

        :param yearfirst:
            Whether to interpret the first value in an ambiguous 3-integer date
            (e.g. 01/05/09) as the year. If ``True``, the first number is taken
            to be the year, otherwise the last number is taken to be the year.
            If this is set to ``None``, the value is retrieved from the current
            :class:`parserinfo` object (which itself defaults to ``False``).

        :param fuzzy:
            Whether to allow fuzzy parsing, allowing for string like "Today is
            January 1, 2047 at 8:21:00AM".

        :param fuzzy_with_tokens:
            If ``True``, ``fuzzy`` is automatically set to True, and the parser
            will return a tuple where the first element is the parsed
            :class:`datetime.datetime` datetimestamp and the second element is
            a tuple containing the portions of the string which were ignored:

            .. doctest::

                >>> from dateutil.parser import parse
                >>> parse("Today is January 1, 2047 at 8:21:00AM", fuzzy_with_tokens=True)
                (datetime.datetime(2047, 1, 1, 8, 21), (u'Today is ', u' ', u'at '))

        """
        if fuzzy_with_tokens:
            fuzzy = True

        info = self.info

        if dayfirst is None:
            dayfirst = info.dayfirst

        if yearfirst is None:
            yearfirst = info.yearfirst

        res = self._result()
        l = _timelex.split(timestr)         # Splits the timestr into tokens

        skipped_idxs = []

        # year/month/day list
        ymd = _ymd()

        len_l = len(l)
        i = 0
        try:
            while i < len_l:

                # Check if it's a number
                value_repr = l[i]
                try:
                    value = float(value_repr)
                except ValueError:
                    value = None

                if value is not None:
                    # Numeric token
                    i = self._parse_numeric_token(l, i, info, ymd, res, fuzzy)

                # Check weekday
                elif info.weekday(l[i]) is not None:
                    value = info.weekday(l[i])
                    res.weekday = value

                # Check month name
                elif info.month(l[i]) is not None:
                    value = info.month(l[i])
                    ymd.append(value, 'M')

                    if i + 1 < len_l:
                        if l[i + 1] in ('-', '/'):
                            # Jan-01[-99]
                            sep = l[i + 1]
                            ymd.append(l[i + 2])

                            if i + 3 < len_l and l[i + 3] == sep:
                                # Jan-01-99
                                ymd.append(l[i + 4])
                                i += 2

                            i += 2

                        elif (i + 4 < len_l and l[i + 1] == l[i + 3] == ' ' and
                              info.pertain(l[i + 2])):
                            # Jan of 01
                            # In this case, 01 is clearly year
                            if l[i + 4].isdigit():
                                # Convert it here to become unambiguous
                                value = int(l[i + 4])
                                year = str(info.convertyear(value))
                                ymd.append(year, 'Y')
                            else:
                                # Wrong guess
                                pass
                                # TODO: not hit in tests
                            i += 4

                # Check am/pm
                elif info.ampm(l[i]) is not None:
                    value = info.ampm(l[i])
                    val_is_ampm = self._ampm_valid(res.hour, res.ampm, fuzzy)

                    if val_is_ampm:
                        res.hour = self._adjust_ampm(res.hour, value)
                        res.ampm = value

                    elif fuzzy:
                        skipped_idxs.append(i)

                # Check for a timezone name
                elif self._could_be_tzname(res.hour, res.tzname, res.tzoffset, l[i]):
                    res.tzname = l[i]
                    res.tzoffset = info.tzoffset(res.tzname)

                    # Check for something like GMT+3, or BRST+3. Notice
                    # that it doesn't mean "I am 3 hours after GMT", but
                    # "my time +3 is GMT". If found, we reverse the
                    # logic so that timezone parsing code will get it
                    # right.
                    if i + 1 < len_l and l[i + 1] in ('+', '-'):
                        l[i + 1] = ('+', '-')[l[i + 1] == '+']
                        res.tzoffset = None
                        if info.utczone(res.tzname):
                            # With something like GMT+3, the timezone
                            # is *not* GMT.
                            res.tzname = None

                # Check for a numbered timezone
                elif res.hour is not None and l[i] in ('+', '-'):
                    signal = (-1, 1)[l[i] == '+']
                    len_li = len(l[i + 1])

                    # TODO: check that l[i + 1] is integer?
                    if len_li == 4:
                        # -0300
                        hour_offset = int(l[i + 1][:2])
                        min_offset = int(l[i + 1][2:])
                    elif i + 2 < len_l and l[i + 2] == ':':
                        # -03:00
                        hour_offset = int(l[i + 1])
                        min_offset = int(l[i + 3])  # TODO: Check that l[i+3] is minute-like?
                        i += 2
                    elif len_li <= 2:
                        # -[0]3
                        hour_offset = int(l[i + 1][:2])
                        min_offset = 0
                    else:
                        raise ValueError(timestr)

                    res.tzoffset = signal * (hour_offset * 3600 + min_offset * 60)

                    # Look for a timezone name between parenthesis
                    if (i + 5 < len_l and
                            info.jump(l[i + 2]) and l[i + 3] == '(' and
                            l[i + 5] == ')' and
                            3 <= len(l[i + 4]) and
                            self._could_be_tzname(res.hour, res.tzname,
                                                  None, l[i + 4])):
                        # -0300 (BRST)
                        res.tzname = l[i + 4]
                        i += 4

                    i += 1

                # Check jumps
                elif not (info.jump(l[i]) or fuzzy):
                    raise ValueError(timestr)

                else:
                    skipped_idxs.append(i)
                i += 1

            # Process year/month/day
            year, month, day = ymd.resolve_ymd(yearfirst, dayfirst)

            res.century_specified = ymd.century_specified
            res.year = year
            res.month = month
            res.day = day

        except (IndexError, ValueError):
            return None, None

        if not info.validate(res):
            return None, None

        if fuzzy_with_tokens:
            skipped_tokens = self._recombine_skipped(l, skipped_idxs)
            return res, tuple(skipped_tokens)
        else:
            return res, None

    def _parse_numeric_token(self, tokens, idx, info, ymd, res, fuzzy):
        # Token is a number
        value_repr = tokens[idx]
        try:
            value = self._to_decimal(value_repr)
        except Exception as e:
            six.raise_from(ValueError('Unknown numeric token'), e)

        len_li = len(value_repr)

        len_l = len(tokens)

        if (len(ymd) == 3 and len_li in (2, 4) and
            res.hour is None and
            (idx + 1 >= len_l or
             (tokens[idx + 1] != ':' and
              info.hms(tokens[idx + 1]) is None))):
            # 19990101T23[59]
            s = tokens[idx]
            res.hour = int(s[:2])

            if len_li == 4:
                res.minute = int(s[2:])

        elif len_li == 6 or (len_li > 6 and tokens[idx].find('.') == 6):
            # YYMMDD or HHMMSS[.ss]
            s = tokens[idx]

            if not ymd and '.' not in tokens[idx]:
                ymd.append(s[:2])
                ymd.append(s[2:4])
                ymd.append(s[4:])
            else:
                # 19990101T235959[.59]

                # TODO: Check if res attributes already set.
                res.hour = int(s[:2])
                res.minute = int(s[2:4])
                res.second, res.microsecond = self._parsems(s[4:])

        elif len_li in (8, 12, 14):
            # YYYYMMDD
            s = tokens[idx]
            ymd.append(s[:4], 'Y')
            ymd.append(s[4:6])
            ymd.append(s[6:8])

            if len_li > 8:
                res.hour = int(s[8:10])
                res.minute = int(s[10:12])

                if len_li > 12:
                    res.second = int(s[12:])

        elif self._find_hms_idx(idx, tokens, info, allow_jump=True) is not None:
            # HH[ ]h or MM[ ]m or SS[.ss][ ]s
            hms_idx = self._find_hms_idx(idx, tokens, info, allow_jump=True)
            (idx, hms) = self._parse_hms(idx, tokens, info, hms_idx)
            if hms is not None:
                # TODO: checking that hour/minute/second are not
                # already set?
                self._assign_hms(res, value_repr, hms)

        elif idx + 2 < len_l and tokens[idx + 1] == ':':
            # HH:MM[:SS[.ss]]
            res.hour = int(value)
            value = self._to_decimal(tokens[idx + 2])  # TODO: try/except for this?
            (res.minute, res.second) = self._parse_min_sec(value)

            if idx + 4 < len_l and tokens[idx + 3] == ':':
                res.second, res.microsecond = self._parsems(tokens[idx + 4])

                idx += 2

            idx += 2

        elif idx + 1 < len_l and tokens[idx + 1] in ('-', '/', '.'):
            sep = tokens[idx + 1]
            ymd.append(value_repr)

            if idx + 2 < len_l and not info.jump(tokens[idx + 2]):
                if tokens[idx + 2].isdigit():
                    # 01-01[-01]
                    ymd.append(tokens[idx + 2])
                else:
                    # 01-Jan[-01]
                    value = info.month(tokens[idx + 2])

                    if value is not None:
                        ymd.append(value, 'M')
                    else:
                        raise ValueError()

                if idx + 3 < len_l and tokens[idx + 3] == sep:
                    # We have three members
                    value = info.month(tokens[idx + 4])

                    if value is not None:
                        ymd.append(value, 'M')
                    else:
                        ymd.append(tokens[idx + 4])
                    idx += 2

                idx += 1
            idx += 1

        elif idx + 1 >= len_l or info.jump(tokens[idx + 1]):
            if idx + 2 < len_l and info.ampm(tokens[idx + 2]) is not None:
                # 12 am
                hour = int(value)
                res.hour = self._adjust_ampm(hour, info.ampm(tokens[idx + 2]))
                idx += 1
            else:
                # Year, month or day
                ymd.append(value)
            idx += 1

        elif info.ampm(tokens[idx + 1]) is not None and (0 <= value < 24):
            # 12am
            hour = int(value)
            res.hour = self._adjust_ampm(hour, info.ampm(tokens[idx + 1]))
            idx += 1

        elif ymd.could_be_day(value):
            ymd.append(value)

        elif not fuzzy:
            raise ValueError()

        return idx

    def _find_hms_idx(self, idx, tokens, info, allow_jump):
        len_l = len(tokens)

        if idx+1 < len_l and info.hms(tokens[idx+1]) is not None:
            # There is an "h", "m", or "s" label following this token.  We take
            # assign the upcoming label to the current token.
            # e.g. the "12" in 12h"
            hms_idx = idx + 1

        elif (allow_jump and idx+2 < len_l and tokens[idx+1] == ' ' and
              info.hms(tokens[idx+2]) is not None):
            # There is a space and then an "h", "m", or "s" label.
            # e.g. the "12" in "12 h"
            hms_idx = idx + 2

        elif idx > 0 and info.hms(tokens[idx-1]) is not None:
            # There is a "h", "m", or "s" preceding this token.  Since neither
            # of the previous cases was hit, there is no label following this
            # token, so we use the previous label.
            # e.g. the "04" in "12h04"
            hms_idx = idx-1

        elif (1 < idx == len_l-1 and tokens[idx-1] == ' ' and
              info.hms(tokens[idx-2]) is not None):
            # If we are looking at the final token, we allow for a
            # backward-looking check to skip over a space.
            # TODO: Are we sure this is the right condition here?
            hms_idx = idx - 2

        else:
            hms_idx = None

        return hms_idx

    def _assign_hms(self, res, value_repr, hms):
        # See GH issue #427, fixing float rounding
        value = self._to_decimal(value_repr)

        if hms == 0:
            # Hour
            res.hour = int(value)
            if value % 1:
                res.minute = int(60*(value % 1))

        elif hms == 1:
            (res.minute, res.second) = self._parse_min_sec(value)

        elif hms == 2:
            (res.second, res.microsecond) = self._parsems(value_repr)

    def _could_be_tzname(self, hour, tzname, tzoffset, token):
        return (hour is not None and
                tzname is None and
                tzoffset is None and
                len(token) <= 5 and
                (all(x in string.ascii_uppercase for x in token)
                 or token in self.info.UTCZONE))

    def _ampm_valid(self, hour, ampm, fuzzy):
        """
        For fuzzy parsing, 'a' or 'am' (both valid English words)
        may erroneously trigger the AM/PM flag. Deal with that
        here.
        """
        val_is_ampm = True

        # If there's already an AM/PM flag, this one isn't one.
        if fuzzy and ampm is not None:
            val_is_ampm = False

        # If AM/PM is found and hour is not, raise a ValueError
        if hour is None:
            if fuzzy:
                val_is_ampm = False
            else:
                raise ValueError('No hour specified with AM or PM flag.')
        elif not 0 <= hour <= 12:
            # If AM/PM is found, it's a 12 hour clock, so raise
            # an error for invalid range
            if fuzzy:
                val_is_ampm = False
            else:
                raise ValueError('Invalid hour specified for 12-hour clock.')

        return val_is_ampm

    def _adjust_ampm(self, hour, ampm):
        if hour < 12 and ampm == 1:
            hour += 12
        elif hour == 12 and ampm == 0:
            hour = 0
        return hour

    def _parse_min_sec(self, value):
        # TODO: Every usage of this function sets res.second to the return
        # value. Are there any cases where second will be returned as None and
        # we *don't* want to set res.second = None?
        minute = int(value)
        second = None

        sec_remainder = value % 1
        if sec_remainder:
            second = int(60 * sec_remainder)
        return (minute, second)

    def _parse_hms(self, idx, tokens, info, hms_idx):
        # TODO: Is this going to admit a lot of false-positives for when we
        # just happen to have digits and "h", "m" or "s" characters in non-date
        # text?  I guess hex hashes won't have that problem, but there's plenty
        # of random junk out there.
        if hms_idx is None:
            hms = None
            new_idx = idx
        elif hms_idx > idx:
            hms = info.hms(tokens[hms_idx])
            new_idx = hms_idx
        else:
            # Looking backwards, increment one.
            hms = info.hms(tokens[hms_idx]) + 1
            new_idx = idx

        return (new_idx, hms)

    # ------------------------------------------------------------------
    # Handling for individual tokens.  These are kept as methods instead
    #  of functions for the sake of customizability via subclassing.

    def _parsems(self, value):
        """Parse a I[.F] seconds value into (seconds, microseconds)."""
        if "." not in value:
            return int(value), 0
        else:
            i, f = value.split(".")
            return int(i), int(f.ljust(6, "0")[:6])

    def _to_decimal(self, val):
        try:
            decimal_value = Decimal(val)
            # See GH 662, edge case, infinite value should not be converted
            #  via `_to_decimal`
            if not decimal_value.is_finite():
                raise ValueError("Converted decimal value is infinite or NaN")
        except Exception as e:
            msg = "Could not convert %s to decimal" % val
            six.raise_from(ValueError(msg), e)
        else:
            return decimal_value

    # ------------------------------------------------------------------
    # Post-Parsing construction of datetime output.  These are kept as
    #  methods instead of functions for the sake of customizability via
    #  subclassing.

    def _build_tzinfo(self, tzinfos, tzname, tzoffset):
        if callable(tzinfos):
            tzdata = tzinfos(tzname, tzoffset)
        else:
            tzdata = tzinfos.get(tzname)
        # handle case where tzinfo is paased an options that returns None
        # eg tzinfos = {'BRST' : None}
        if isinstance(tzdata, datetime.tzinfo) or tzdata is None:
            tzinfo = tzdata
        elif isinstance(tzdata, text_type):
            tzinfo = tz.tzstr(tzdata)
        elif isinstance(tzdata, integer_types):
            tzinfo = tz.tzoffset(tzname, tzdata)
        else:
            raise TypeError("Offset must be tzinfo subclass, tz string, "
                            "or int offset.")
        return tzinfo

    def _build_tzaware(self, naive, res, tzinfos):
        if (callable(tzinfos) or (tzinfos and res.tzname in tzinfos)):
            tzinfo = self._build_tzinfo(tzinfos, res.tzname, res.tzoffset)
            aware = naive.replace(tzinfo=tzinfo)
            aware = self._assign_tzname(aware, res.tzname)

        elif res.tzname and res.tzname in time.tzname:
            aware = naive.replace(tzinfo=tz.tzlocal())

            # Handle ambiguous local datetime
            aware = self._assign_tzname(aware, res.tzname)

            # This is mostly relevant for winter GMT zones parsed in the UK
            if (aware.tzname() != res.tzname and
                    res.tzname in self.info.UTCZONE):
                aware = aware.replace(tzinfo=tz.UTC)

        elif res.tzoffset == 0:
            aware = naive.replace(tzinfo=tz.UTC)

        elif res.tzoffset:
            aware = naive.replace(tzinfo=tz.tzoffset(res.tzname, res.tzoffset))

        elif not res.tzname and not res.tzoffset:
            # i.e. no timezone information was found.
            aware = naive

        elif res.tzname:
            # tz-like string was parsed but we don't know what to do
            # with it
            warnings.warn("tzname {tzname} identified but not understood.  "
                          "Pass `tzinfos` argument in order to correctly "
                          "return a timezone-aware datetime.  In a future "
                          "version, this will raise an "
                          "exception.".format(tzname=res.tzname),
                          category=UnknownTimezoneWarning)
            aware = naive

        return aware

    def _build_naive(self, res, default):
        repl = {}
        for attr in ("year", "month", "day", "hour",
                     "minute", "second", "microsecond"):
            value = getattr(res, attr)
            if value is not None:
                repl[attr] = value

        if 'day' not in repl:
            # If the default day exceeds the last day of the month, fall back
            # to the end of the month.
            cyear = default.year if res.year is None else res.year
            cmonth = default.month if res.month is None else res.month
            cday = default.day if res.day is None else res.day

            if cday > monthrange(cyear, cmonth)[1]:
                repl['day'] = monthrange(cyear, cmonth)[1]

        naive = default.replace(**repl)

        if res.weekday is not None and not res.day:
            naive = naive + relativedelta.relativedelta(weekday=res.weekday)

        return naive

    def _assign_tzname(self, dt, tzname):
        if dt.tzname() != tzname:
            new_dt = tz.enfold(dt, fold=1)
            if new_dt.tzname() == tzname:
                return new_dt

        return dt

    def _recombine_skipped(self, tokens, skipped_idxs):
        """
        >>> tokens = ["foo", " ", "bar", " ", "19June2000", "baz"]
        >>> skipped_idxs = [0, 1, 2, 5]
        >>> _recombine_skipped(tokens, skipped_idxs)
        ["foo bar", "baz"]
        """
        skipped_tokens = []
        for i, idx in enumerate(sorted(skipped_idxs)):
            if i > 0 and idx - 1 == skipped_idxs[i - 1]:
                skipped_tokens[-1] = skipped_tokens[-1] + tokens[idx]
            else:
                skipped_tokens.append(tokens[idx])

        return skipped_tokens


DEFAULTPARSER = parser()


def parse(timestr, parserinfo=None, **kwargs):
    """

    Parse a string in one of the supported formats, using the
    ``parserinfo`` parameters.

    :param timestr:
        A string containing a date/time stamp.

    :param parserinfo:
        A :class:`parserinfo` object containing parameters for the parser.
        If ``None``, the default arguments to the :class:`parserinfo`
        constructor are used.

    The ``**kwargs`` parameter takes the following keyword arguments:

    :param default:
        The default datetime object, if this is a datetime object and not
        ``None``, elements specified in ``timestr`` replace elements in the
        default object.

    :param ignoretz:
        If set ``True``, time zones in parsed strings are ignored and a naive
        :class:`datetime` object is returned.

    :param tzinfos:
        Additional time zone names / aliases which may be present in the
        string. This argument maps time zone names (and optionally offsets
        from those time zones) to time zones. This parameter can be a
        dictionary with timezone aliases mapping time zone names to time
        zones or a function taking two parameters (``tzname`` and
        ``tzoffset``) and returning a time zone.

        The timezones to which the names are mapped can be an integer
        offset from UTC in seconds or a :class:`tzinfo` object.

        .. doctest::
           :options: +NORMALIZE_WHITESPACE

            >>> from dateutil.parser import parse
            >>> from dateutil.tz import gettz
            >>> tzinfos = {"BRST": -7200, "CST": gettz("America/Chicago")}
            >>> parse("2012-01-19 17:21:00 BRST", tzinfos=tzinfos)
            datetime.datetime(2012, 1, 19, 17, 21, tzinfo=tzoffset(u'BRST', -7200))
            >>> parse("2012-01-19 17:21:00 CST", tzinfos=tzinfos)
            datetime.datetime(2012, 1, 19, 17, 21,
                              tzinfo=tzfile('/usr/share/zoneinfo/America/Chicago'))

        This parameter is ignored if ``ignoretz`` is set.

    :param dayfirst:
        Whether to interpret the first value in an ambiguous 3-integer date
        (e.g. 01/05/09) as the day (``True``) or month (``False``). If
        ``yearfirst`` is set to ``True``, this distinguishes between YDM and
        YMD. If set to ``None``, this value is retrieved from the current
        :class:`parserinfo` object (which itself defaults to ``False``).

    :param yearfirst:
        Whether to interpret the first value in an ambiguous 3-integer date
        (e.g. 01/05/09) as the year. If ``True``, the first number is taken to
        be the year, otherwise the last number is taken to be the year. If
        this is set to ``None``, the value is retrieved from the current
        :class:`parserinfo` object (which itself defaults to ``False``).

    :param fuzzy:
        Whether to allow fuzzy parsing, allowing for string like "Today is
        January 1, 2047 at 8:21:00AM".

    :param fuzzy_with_tokens:
        If ``True``, ``fuzzy`` is automatically set to True, and the parser
        will return a tuple where the first element is the parsed
        :class:`datetime.datetime` datetimestamp and the second element is
        a tuple containing the portions of the string which were ignored:

        .. doctest::

            >>> from dateutil.parser import parse
            >>> parse("Today is January 1, 2047 at 8:21:00AM", fuzzy_with_tokens=True)
            (datetime.datetime(2047, 1, 1, 8, 21), (u'Today is ', u' ', u'at '))

    :return:
        Returns a :class:`datetime.datetime` object or, if the
        ``fuzzy_with_tokens`` option is ``True``, returns a tuple, the
        first element being a :class:`datetime.datetime` object, the second
        a tuple containing the fuzzy tokens.

    :raises ParserError:
        Raised for invalid or unknown string formats, if the provided
        :class:`tzinfo` is not in a valid format, or if an invalid date would
        be created.

    :raises OverflowError:
        Raised if the parsed date exceeds the largest valid C integer on
        your system.
    """
    if parserinfo:
        return parser(parserinfo).parse(timestr, **kwargs)
    else:
        return DEFAULTPARSER.parse(timestr, **kwargs)


class _tzparser(object):

    class _result(_resultbase):

        __slots__ = ["stdabbr", "stdoffset", "dstabbr", "dstoffset",
                     "start", "end"]

        class _attr(_resultbase):
            __slots__ = ["month", "week", "weekday",
                         "yday", "jyday", "day", "time"]

        def __repr__(self):
            return self._repr("")

        def __init__(self):
            _resultbase.__init__(self)
            self.start = self._attr()
            self.end = self._attr()

    def parse(self, tzstr):
        res = self._result()
        l = [x for x in re.split(r'([,:.]|[a-zA-Z]+|[0-9]+)',tzstr) if x]
        used_idxs = list()
        try:

            len_l = len(l)

            i = 0
            while i < len_l:
                # BRST+3[BRDT[+2]]
                j = i
                while j < len_l and not [x for x in l[j]
                                         if x in "0123456789:,-+"]:
                    j += 1
                if j != i:
                    if not res.stdabbr:
                        offattr = "stdoffset"
                        res.stdabbr = "".join(l[i:j])
                    else:
                        offattr = "dstoffset"
                        res.dstabbr = "".join(l[i:j])

                    for ii in range(j):
                        used_idxs.append(ii)
                    i = j
                    if (i < len_l and (l[i] in ('+', '-') or l[i][0] in
                                       "0123456789")):
                        if l[i] in ('+', '-'):
                            # Yes, that's right.  See the TZ variable
                            # documentation.
                            signal = (1, -1)[l[i] == '+']
                            used_idxs.append(i)
                            i += 1
                        else:
                            signal = -1
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            setattr(res, offattr, (int(l[i][:2]) * 3600 +
                                                   int(l[i][2:]) * 60) * signal)
                        elif i + 1 < len_l and l[i + 1] == ':':
                            # -03:00
                            setattr(res, offattr,
                                    (int(l[i]) * 3600 +
                                     int(l[i + 2]) * 60) * signal)
                            used_idxs.append(i)
                            i += 2
                        elif len_li <= 2:
                            # -[0]3
                            setattr(res, offattr,
                                    int(l[i][:2]) * 3600 * signal)
                        else:
                            return None
                        used_idxs.append(i)
                        i += 1
                    if res.dstabbr:
                        break
                else:
                    break


            if i < len_l:
                for j in range(i, len_l):
                    if l[j] == ';':
                        l[j] = ','

                assert l[i] == ','

                i += 1

            if i >= len_l:
                pass
            elif (8 <= l.count(',') <= 9 and
                  not [y for x in l[i:] if x != ','
                       for y in x if y not in "0123456789+-"]):
                # GMT0BST,3,0,30,3600,10,0,26,7200[,3600]
                for x in (res.start, res.end):
                    x.month = int(l[i])
                    used_idxs.append(i)
                    i += 2
                    if l[i] == '-':
                        value = int(l[i + 1]) * -1
                        used_idxs.append(i)
                        i += 1
                    else:
                        value = int(l[i])
                    used_idxs.append(i)
                    i += 2
                    if value:
                        x.week = value
                        x.weekday = (int(l[i]) - 1) % 7
                    else:
                        x.day = int(l[i])
                    used_idxs.append(i)
                    i += 2
                    x.time = int(l[i])
                    used_idxs.append(i)
                    i += 2
                if i < len_l:
                    if l[i] in ('-', '+'):
                        signal = (-1, 1)[l[i] == "+"]
                        used_idxs.append(i)
                        i += 1
                    else:
                        signal = 1
                    used_idxs.append(i)
                    res.dstoffset = (res.stdoffset + int(l[i]) * signal)

                # This was a made-up format that is not in normal use
                warn(('Parsed time zone "%s"' % tzstr) +
                     'is in a non-standard dateutil-specific format, which ' +
                     'is now deprecated; support for parsing this format ' +
                     'will be removed in future versions. It is recommended ' +
                     'that you switch to a standard format like the GNU ' +
                     'TZ variable format.', tz.DeprecatedTzFormatWarning)
            elif (l.count(',') == 2 and l[i:].count('/') <= 2 and
                  not [y for x in l[i:] if x not in (',', '/', 'J', 'M',
                                                     '.', '-', ':')
                       for y in x if y not in "0123456789"]):
                for x in (res.start, res.end):
                    if l[i] == 'J':
                        # non-leap year day (1 based)
                        used_idxs.append(i)
                        i += 1
                        x.jyday = int(l[i])
                    elif l[i] == 'M':
                        # month[-.]week[-.]weekday
                        used_idxs.append(i)
                        i += 1
                        x.month = int(l[i])
                        used_idxs.append(i)
                        i += 1
                        assert l[i] in ('-', '.')
                        used_idxs.append(i)
                        i += 1
                        x.week = int(l[i])
                        if x.week == 5:
                            x.week = -1
                        used_idxs.append(i)
                        i += 1
                        assert l[i] in ('-', '.')
                        used_idxs.append(i)
                        i += 1
                        x.weekday = (int(l[i]) - 1) % 7
                    else:
                        # year day (zero based)
                        x.yday = int(l[i]) + 1

                    used_idxs.append(i)
                    i += 1

                    if i < len_l and l[i] == '/':
                        used_idxs.append(i)
                        i += 1
                        # start time
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            x.time = (int(l[i][:2]) * 3600 +
                                      int(l[i][2:]) * 60)
                        elif i + 1 < len_l and l[i + 1] == ':':
                            # -03:00
                            x.time = int(l[i]) * 3600 + int(l[i + 2]) * 60
                            used_idxs.append(i)
                            i += 2
                            if i + 1 < len_l and l[i + 1] == ':':
                                used_idxs.append(i)
                                i += 2
                                x.time += int(l[i])
                        elif len_li <= 2:
                            # -[0]3
                            x.time = (int(l[i][:2]) * 3600)
                        else:
                            return None
                        used_idxs.append(i)
                        i += 1

                    assert i == len_l or l[i] == ','

                    i += 1

                assert i >= len_l

        except (IndexError, ValueError, AssertionError):
            return None

        unused_idxs = set(range(len_l)).difference(used_idxs)
        res.any_unused_tokens = not {l[n] for n in unused_idxs}.issubset({",",":"})
        return res


DEFAULTTZPARSER = _tzparser()


def _parsetz(tzstr):
    return DEFAULTTZPARSER.parse(tzstr)


class ParserError(ValueError):
    """Exception subclass used for any failure to parse a datetime string.

    This is a subclass of :py:exc:`ValueError`, and should be raised any time
    earlier versions of ``dateutil`` would have raised ``ValueError``.

    .. versionadded:: 2.8.1
    """
    def __str__(self):
        try:
            return self.args[0] % self.args[1:]
        except (TypeError, IndexError):
            return super(ParserError, self).__str__()

    def __repr__(self):
        args = ", ".join("'%s'" % arg for arg in self.args)
        return "%s(%s)" % (self.__class__.__name__, args)


class UnknownTimezoneWarning(RuntimeWarning):
    """Raised when the parser finds a timezone it cannot parse into a tzinfo.

    .. versionadded:: 2.7.0
    """
# vim:ts=4:sw=4:et