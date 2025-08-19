
# === NexusCore/tools\exports\export_20250803_114325\combined_46.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\spend_tracking\spend_management_endpoints.py ===
#### SPEND MANAGEMENT #####
import collections
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

import fastapi
from fastapi import APIRouter, Depends, HTTPException, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy._types import ProviderBudgetResponse, ProviderBudgetResponseObject
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.spend_tracking.spend_tracking_utils import (
    get_spend_by_team_and_customer,
)
from litellm.proxy.utils import handle_exception_on_proxy

if TYPE_CHECKING:
    from litellm.proxy.proxy_server import PrismaClient
else:
    PrismaClient = Any

router = APIRouter()


@router.get(
    "/spend/keys",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def spend_key_fn():
    """
    View all keys created, ordered by spend

    Example Request:
    ```
    curl -X GET "http://0.0.0.0:8000/spend/keys" \
-H "Authorization: Bearer sk-1234"
    ```
    """

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        key_info = await prisma_client.get_data(table_name="key", query_type="find_all")
        return key_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get(
    "/spend/users",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def spend_user_fn(
    user_id: Optional[str] = fastapi.Query(
        default=None,
        description="Get User Table row for user_id",
    ),
):
    """
    View all users created, ordered by spend

    Example Request:
    ```
    curl -X GET "http://0.0.0.0:8000/spend/users" \
-H "Authorization: Bearer sk-1234"
    ```

    View User Table row for user_id
    ```
    curl -X GET "http://0.0.0.0:8000/spend/users?user_id=1234" \
-H "Authorization: Bearer sk-1234"
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if user_id is not None:
            user_info = await prisma_client.get_data(
                table_name="user", query_type="find_unique", user_id=user_id
            )
            return [user_info]
        else:
            user_info = await prisma_client.get_data(
                table_name="user", query_type="find_all"
            )

        return user_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get(
    "/spend/tags",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def view_spend_tags(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing key spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view key spend",
    ),
):
    """
    LiteLLM Enterprise - View Spend Per Request Tag

    Example Request:
    ```
    curl -X GET "http://0.0.0.0:8000/spend/tags" \
-H "Authorization: Bearer sk-1234"
    ```

    Spend with Start Date and End Date
    ```
    curl -X GET "http://0.0.0.0:8000/spend/tags?start_date=2022-01-01&end_date=2022-02-01" \
-H "Authorization: Bearer sk-1234"
    ```
    """

    try:
        from enterprise.utils import get_spend_by_tags
    except ImportError:
        raise Exception(
            "Trying to use Spend by Tags"
            + CommonProxyErrors.missing_enterprise_package_docker.value
        )
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        # run the following SQL query on prisma
        """
        SELECT
        jsonb_array_elements_text(request_tags) AS individual_request_tag,
        COUNT(*) AS log_count,
        SUM(spend) AS total_spend
        FROM "LiteLLM_SpendLogs"
        GROUP BY individual_request_tag;
        """
        response = await get_spend_by_tags(
            start_date=start_date, end_date=end_date, prisma_client=prisma_client
        )

        return response
    except Exception as e:
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/spend/tags Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/spend/tags Error" + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def get_global_activity_internal_user(
    user_api_key_dict: UserAPIKeyAuth, start_date: datetime, end_date: datetime
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    user_id = user_api_key_dict.user_id
    if user_id is None:
        raise HTTPException(status_code=500, detail={"error": "No user_id found"})

    sql_query = """
    SELECT
        date_trunc('day', "startTime") AS date,
        COUNT(*) AS api_requests,
        SUM(total_tokens) AS total_tokens
    FROM "LiteLLM_SpendLogs"
    WHERE "startTime" BETWEEN $1::date AND $2::date + interval '1 day'
    AND "user" = $3
    GROUP BY date_trunc('day', "startTime")
    """
    db_response = await prisma_client.db.query_raw(
        sql_query, start_date, end_date, user_id
    )

    return db_response


@router.get(
    "/global/activity",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
    include_in_schema=False,
)
async def get_global_activity(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get number of API Requests, total tokens through proxy

    {
        "daily_data": [
                const chartdata = [
                {
                date: 'Jan 22',
                api_requests: 10,
                total_tokens: 2000
                },
                {
                date: 'Jan 23',
                api_requests: 10,
                total_tokens: 12
                },
        ],
        "sum_api_requests": 20,
        "sum_total_tokens": 2012
    }
    """

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if (
            user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
            or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
        ):
            db_response = await get_global_activity_internal_user(
                user_api_key_dict, start_date_obj, end_date_obj
            )
        else:
            sql_query = """
            SELECT
                date_trunc('day', "startTime") AS date,
                COUNT(*) AS api_requests,
                SUM(total_tokens) AS total_tokens
            FROM "LiteLLM_SpendLogs"
            WHERE "startTime" BETWEEN $1::date AND $2::date + interval '1 day'
            GROUP BY date_trunc('day', "startTime")
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )

        if db_response is None:
            return []

        sum_api_requests = 0
        sum_total_tokens = 0
        daily_data = []
        for row in db_response:
            # cast date to datetime
            _date_obj = datetime.fromisoformat(row["date"])
            row["date"] = _date_obj.strftime("%b %d")

            daily_data.append(row)
            sum_api_requests += row.get("api_requests", 0)
            sum_total_tokens += row.get("total_tokens", 0)

        # sort daily_data by date
        daily_data = sorted(daily_data, key=lambda x: x["date"])

        data_to_return = {
            "daily_data": daily_data,
            "sum_api_requests": sum_api_requests,
            "sum_total_tokens": sum_total_tokens,
        }

        return data_to_return

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


async def get_global_activity_model_internal_user(
    user_api_key_dict: UserAPIKeyAuth, start_date: datetime, end_date: datetime
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    user_id = user_api_key_dict.user_id
    if user_id is None:
        raise HTTPException(status_code=500, detail={"error": "No user_id found"})

    sql_query = """
    SELECT
        model_group,
        date_trunc('day', "startTime") AS date,
        COUNT(*) AS api_requests,
        SUM(total_tokens) AS total_tokens
    FROM "LiteLLM_SpendLogs"
    WHERE "startTime" BETWEEN $1::date AND $2::date + interval '1 day'
    AND "user" = $3
    GROUP BY model_group, date_trunc('day', "startTime")
    """
    db_response = await prisma_client.db.query_raw(
        sql_query, start_date, end_date, user_id
    )

    return db_response


@router.get(
    "/global/activity/model",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
    include_in_schema=False,
)
async def get_global_activity_model(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get number of API Requests, total tokens through proxy - Grouped by MODEL

    [
        {
            "model": "gpt-4",
            "daily_data": [
                    const chartdata = [
                    {
                    date: 'Jan 22',
                    api_requests: 10,
                    total_tokens: 2000
                    },
                    {
                    date: 'Jan 23',
                    api_requests: 10,
                    total_tokens: 12
                    },
            ],
            "sum_api_requests": 20,
            "sum_total_tokens": 2012

        },
        {
            "model": "azure/gpt-4-turbo",
            "daily_data": [
                    const chartdata = [
                    {
                    date: 'Jan 22',
                    api_requests: 10,
                    total_tokens: 2000
                    },
                    {
                    date: 'Jan 23',
                    api_requests: 10,
                    total_tokens: 12
                    },
            ],
            "sum_api_requests": 20,
            "sum_total_tokens": 2012

        },
    ]
    """

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if (
            user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
            or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
        ):
            db_response = await get_global_activity_model_internal_user(
                user_api_key_dict, start_date_obj, end_date_obj
            )
        else:
            sql_query = """
            SELECT
                model_group,
                date_trunc('day', "startTime") AS date,
                COUNT(*) AS api_requests,
                SUM(total_tokens) AS total_tokens
            FROM "LiteLLM_SpendLogs"
            WHERE "startTime" BETWEEN $1::date AND $2::date + interval '1 day'
            GROUP BY model_group, date_trunc('day', "startTime")
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )
        if db_response is None:
            return []

        model_ui_data: dict = (
            {}
        )  # {"gpt-4": {"daily_data": [], "sum_api_requests": 0, "sum_total_tokens": 0}}

        for row in db_response:
            _model = row["model_group"]
            if _model not in model_ui_data:
                model_ui_data[_model] = {
                    "daily_data": [],
                    "sum_api_requests": 0,
                    "sum_total_tokens": 0,
                }
            _date_obj = datetime.fromisoformat(row["date"])
            row["date"] = _date_obj.strftime("%b %d")

            model_ui_data[_model]["daily_data"].append(row)
            model_ui_data[_model]["sum_api_requests"] += row.get("api_requests", 0)
            model_ui_data[_model]["sum_total_tokens"] += row.get("total_tokens", 0)

        # sort mode ui data by sum_api_requests -> get top 10 models
        model_ui_data = dict(
            sorted(
                model_ui_data.items(),
                key=lambda x: x[1]["sum_api_requests"],
                reverse=True,
            )[:10]
        )

        response = []
        for model, data in model_ui_data.items():
            _sort_daily_data = sorted(data["daily_data"], key=lambda x: x["date"])

            response.append(
                {
                    "model": model,
                    "daily_data": _sort_daily_data,
                    "sum_api_requests": data["sum_api_requests"],
                    "sum_total_tokens": data["sum_total_tokens"],
                }
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)},
        )


@router.get(
    "/global/activity/exceptions/deployment",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
    include_in_schema=False,
)
async def get_global_activity_exceptions_per_deployment(
    model_group: str = fastapi.Query(
        description="Filter by model group",
    ),
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
):
    """
    Get number of 429 errors - Grouped by deployment

    [
        {
            "deployment": "https://azure-us-east-1.openai.azure.com/",
            "daily_data": [
                    const chartdata = [
                    {
                    date: 'Jan 22',
                    num_rate_limit_exceptions: 10
                    },
                    {
                    date: 'Jan 23',
                    num_rate_limit_exceptions: 12
                    },
            ],
            "sum_num_rate_limit_exceptions": 20,

        },
        {
            "deployment": "https://azure-us-east-1.openai.azure.com/",
            "daily_data": [
                    const chartdata = [
                    {
                    date: 'Jan 22',
                    num_rate_limit_exceptions: 10,
                    },
                    {
                    date: 'Jan 23',
                    num_rate_limit_exceptions: 12
                    },
            ],
            "sum_num_rate_limit_exceptions": 20,

        },
    ]
    """

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        sql_query = """
        SELECT
            api_base,
            date_trunc('day', "startTime")::date AS date,
            COUNT(*) AS num_rate_limit_exceptions
        FROM
            "LiteLLM_ErrorLogs"
        WHERE
            "startTime" >= $1::date
            AND "startTime" < ($2::date + INTERVAL '1 day')
            AND model_group = $3
            AND status_code = '429'
        GROUP BY
            api_base,
            date_trunc('day', "startTime")
        ORDER BY
            date;
        """
        db_response = await prisma_client.db.query_raw(
            sql_query, start_date_obj, end_date_obj, model_group
        )
        if db_response is None:
            return []

        model_ui_data: dict = (
            {}
        )  # {"gpt-4": {"daily_data": [], "sum_api_requests": 0, "sum_total_tokens": 0}}

        for row in db_response:
            _model = row["api_base"]
            if _model not in model_ui_data:
                model_ui_data[_model] = {
                    "daily_data": [],
                    "sum_num_rate_limit_exceptions": 0,
                }
            _date_obj = datetime.fromisoformat(row["date"])
            row["date"] = _date_obj.strftime("%b %d")

            model_ui_data[_model]["daily_data"].append(row)
            model_ui_data[_model]["sum_num_rate_limit_exceptions"] += row.get(
                "num_rate_limit_exceptions", 0
            )

        # sort mode ui data by sum_api_requests -> get top 10 models
        model_ui_data = dict(
            sorted(
                model_ui_data.items(),
                key=lambda x: x[1]["sum_num_rate_limit_exceptions"],
                reverse=True,
            )[:10]
        )

        response = []
        for model, data in model_ui_data.items():
            _sort_daily_data = sorted(data["daily_data"], key=lambda x: x["date"])

            response.append(
                {
                    "api_base": model,
                    "daily_data": _sort_daily_data,
                    "sum_num_rate_limit_exceptions": data[
                        "sum_num_rate_limit_exceptions"
                    ],
                }
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)},
        )


@router.get(
    "/global/activity/exceptions",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
    include_in_schema=False,
)
async def get_global_activity_exceptions(
    model_group: str = fastapi.Query(
        description="Filter by model group",
    ),
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
):
    """
    Get number of API Requests, total tokens through proxy

    {
        "daily_data": [
                const chartdata = [
                {
                date: 'Jan 22',
                num_rate_limit_exceptions: 10,
                },
                {
                date: 'Jan 23',
                num_rate_limit_exceptions: 10,
                },
        ],
        "sum_api_exceptions": 20,
    }
    """

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        sql_query = """
        SELECT
            date_trunc('day', "startTime")::date AS date,
            COUNT(*) AS num_rate_limit_exceptions
        FROM
            "LiteLLM_ErrorLogs"
        WHERE
            "startTime" >= $1::date
            AND "startTime" < ($2::date + INTERVAL '1 day')
            AND model_group = $3
            AND status_code = '429'
        GROUP BY
            date_trunc('day', "startTime")
        ORDER BY
            date;
        """
        db_response = await prisma_client.db.query_raw(
            sql_query, start_date_obj, end_date_obj, model_group
        )

        if db_response is None:
            return []

        sum_num_rate_limit_exceptions = 0
        daily_data = []
        for row in db_response:
            # cast date to datetime
            _date_obj = datetime.fromisoformat(row["date"])
            row["date"] = _date_obj.strftime("%b %d")

            daily_data.append(row)
            sum_num_rate_limit_exceptions += row.get("num_rate_limit_exceptions", 0)

        # sort daily_data by date
        daily_data = sorted(daily_data, key=lambda x: x["date"])

        data_to_return = {
            "daily_data": daily_data,
            "sum_num_rate_limit_exceptions": sum_num_rate_limit_exceptions,
        }

        return data_to_return

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get(
    "/global/spend/provider",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def get_global_spend_provider(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get breakdown of spend per provider
    [
        {
            "provider": "Azure OpenAI",
            "spend": 20
        },
        {
            "provider": "OpenAI",
            "spend": 10
        },
        {
            "provider": "VertexAI",
            "spend": 30
        }
    ]
    """
    from collections import defaultdict

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import llm_router, prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if (
            user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
            or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
        ):
            user_id = user_api_key_dict.user_id
            if user_id is None:
                raise HTTPException(
                    status_code=400, detail={"error": "No user_id found"}
                )

            sql_query = """
            SELECT
            model_id,
            SUM(spend) AS spend
            FROM "LiteLLM_SpendLogs"
            WHERE "startTime" BETWEEN $1::date AND $2::date 
            AND length(model_id) > 0
            AND "user" = $3
            GROUP BY model_id
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj, user_id
            )
        else:
            sql_query = """
            SELECT
            model_id,
            SUM(spend) AS spend
            FROM "LiteLLM_SpendLogs"
            WHERE "startTime" BETWEEN $1::date AND $2::date AND length(model_id) > 0
            GROUP BY model_id
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )

        if db_response is None:
            return []

        ###################################
        # Convert model_id -> to Provider #
        ###################################

        # we use the in memory router for this
        ui_response = []
        provider_spend_mapping: defaultdict = defaultdict(int)
        for row in db_response:
            _model_id = row["model_id"]
            _provider = "Unknown"
            if llm_router is not None:
                _deployment = llm_router.get_deployment(model_id=_model_id)
                if _deployment is not None:
                    try:
                        _, _provider, _, _ = litellm.get_llm_provider(
                            model=_deployment.litellm_params.model,
                            custom_llm_provider=_deployment.litellm_params.custom_llm_provider,
                            api_base=_deployment.litellm_params.api_base,
                            litellm_params=_deployment.litellm_params,
                        )
                        provider_spend_mapping[_provider] += row["spend"]
                    except Exception:
                        pass

        for provider, spend in provider_spend_mapping.items():
            ui_response.append({"provider": provider, "spend": spend})

        return ui_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get(
    "/global/spend/report",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def get_global_spend_report(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view spend",
    ),
    group_by: Optional[Literal["team", "customer", "api_key"]] = fastapi.Query(
        default="team",
        description="Group spend by internal team or customer or api_key",
    ),
    api_key: Optional[str] = fastapi.Query(
        default=None,
        description="View spend for a specific api_key. Example api_key='sk-1234",
    ),
    internal_user_id: Optional[str] = fastapi.Query(
        default=None,
        description="View spend for a specific internal_user_id. Example internal_user_id='1234",
    ),
    team_id: Optional[str] = fastapi.Query(
        default=None,
        description="View spend for a specific team_id. Example team_id='1234",
    ),
    customer_id: Optional[str] = fastapi.Query(
        default=None,
        description="View spend for a specific customer_id. Example customer_id='1234. Can be used in conjunction with team_id as well.",
    ),
):
    """
    Get Daily Spend per Team, based on specific startTime and endTime. Per team, view usage by each key, model
    [
        {
            "group-by-day": "2024-05-10",
            "teams": [
                {
                    "team_name": "team-1"
                    "spend": 10,
                    "keys": [
                        "key": "1213",
                        "usage": {
                            "model-1": {
                                    "cost": 12.50,
                                    "input_tokens": 1000,
                                    "output_tokens": 5000,
                                    "requests": 100
                                },
                                "audio-modelname1": {
                                "cost": 25.50,
                                "seconds": 25,
                                "requests": 50
                        },
                        }
                    }
            ]
        ]
    }
    """
    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    from litellm.proxy.proxy_server import premium_user, prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if premium_user is not True:
            verbose_proxy_logger.debug("accessing /spend/report but not a premium user")
            raise ValueError(
                "/spend/report endpoint " + CommonProxyErrors.not_premium_user.value
            )
        if api_key is not None:
            verbose_proxy_logger.debug("Getting /spend for api_key: %s", api_key)
            if api_key.startswith("sk-"):
                api_key = hash_token(token=api_key)
            sql_query = """
                WITH SpendByModelApiKey AS (
                    SELECT
                        sl.api_key,
                        sl.model,
                        SUM(sl.spend) AS model_cost,
                        SUM(sl.prompt_tokens) AS model_input_tokens,
                        SUM(sl.completion_tokens) AS model_output_tokens
                    FROM
                        "LiteLLM_SpendLogs" sl
                    WHERE
                        sl."startTime" BETWEEN $1::date AND $2::date AND sl.api_key = $3
                    GROUP BY
                        sl.api_key,
                        sl.model
                )
                SELECT
                    api_key,
                    SUM(model_cost) AS total_cost,
                    SUM(model_input_tokens) AS total_input_tokens,
                    SUM(model_output_tokens) AS total_output_tokens,
                    jsonb_agg(jsonb_build_object(
                        'model', model,
                        'total_cost', model_cost,
                        'total_input_tokens', model_input_tokens,
                        'total_output_tokens', model_output_tokens
                    )) AS model_details
                FROM
                    SpendByModelApiKey
                GROUP BY
                    api_key
                ORDER BY
                    total_cost DESC;
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj, api_key
            )
            if db_response is None:
                return []

            return db_response
        elif internal_user_id is not None:
            verbose_proxy_logger.debug(
                "Getting /spend for internal_user_id: %s", internal_user_id
            )
            sql_query = """
                WITH SpendByModelApiKey AS (
                    SELECT
                        sl.api_key,
                        sl.model,
                        SUM(sl.spend) AS model_cost,
                        SUM(sl.prompt_tokens) AS model_input_tokens,
                        SUM(sl.completion_tokens) AS model_output_tokens
                    FROM
                        "LiteLLM_SpendLogs" sl
                    WHERE
                        sl."startTime" BETWEEN $1::date AND $2::date AND sl.user = $3
                    GROUP BY
                        sl.api_key,
                        sl.model
                )
                SELECT
                    api_key,
                    SUM(model_cost) AS total_cost,
                    SUM(model_input_tokens) AS total_input_tokens,
                    SUM(model_output_tokens) AS total_output_tokens,
                    jsonb_agg(jsonb_build_object(
                        'model', model,
                        'total_cost', model_cost,
                        'total_input_tokens', model_input_tokens,
                        'total_output_tokens', model_output_tokens
                    )) AS model_details
                FROM
                    SpendByModelApiKey
                GROUP BY
                    api_key
                ORDER BY
                    total_cost DESC;
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj, internal_user_id
            )
            if db_response is None:
                return []

            return db_response
        elif team_id is not None and customer_id is not None:
            return await get_spend_by_team_and_customer(
                start_date_obj, end_date_obj, team_id, customer_id, prisma_client
            )
        if group_by == "team":
            # first get data from spend logs -> SpendByModelApiKey
            # then read data from "SpendByModelApiKey" to format the response obj
            sql_query = """

            WITH SpendByModelApiKey AS (
                SELECT
                    date_trunc('day', sl."startTime") AS group_by_day,
                    COALESCE(tt.team_alias, 'Unassigned Team') AS team_name,
                    sl.model,
                    sl.api_key,
                    SUM(sl.spend) AS model_api_spend,
                    SUM(sl.total_tokens) AS model_api_tokens
                FROM 
                    "LiteLLM_SpendLogs" sl
                LEFT JOIN 
                    "LiteLLM_TeamTable" tt 
                ON 
                    sl.team_id = tt.team_id
                WHERE
                    sl."startTime" BETWEEN $1::date AND $2::date
                GROUP BY
                    date_trunc('day', sl."startTime"),
                    tt.team_alias,
                    sl.model,
                    sl.api_key
            )
                SELECT
                    group_by_day,
                    jsonb_agg(jsonb_build_object(
                        'team_name', team_name,
                        'total_spend', total_spend,
                        'metadata', metadata
                    )) AS teams
                FROM (
                    SELECT
                        group_by_day,
                        team_name,
                        SUM(model_api_spend) AS total_spend,
                        jsonb_agg(jsonb_build_object(
                            'model', model,
                            'api_key', api_key,
                            'spend', model_api_spend,
                            'total_tokens', model_api_tokens
                        )) AS metadata
                    FROM 
                        SpendByModelApiKey
                    GROUP BY
                        group_by_day,
                        team_name
                ) AS aggregated
                GROUP BY
                    group_by_day
                ORDER BY
                    group_by_day;
                """

            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )
            if db_response is None:
                return []

            return db_response

        elif group_by == "customer":
            sql_query = """

            WITH SpendByModelApiKey AS (
                SELECT
                    date_trunc('day', sl."startTime") AS group_by_day,
                    sl.end_user AS customer,
                    sl.model,
                    sl.api_key,
                    SUM(sl.spend) AS model_api_spend,
                    SUM(sl.total_tokens) AS model_api_tokens
                FROM
                    "LiteLLM_SpendLogs" sl
                WHERE
                    sl."startTime" BETWEEN $1::date AND $2::date
                GROUP BY
                    date_trunc('day', sl."startTime"),
                    customer,
                    sl.model,
                    sl.api_key
            )
            SELECT
                group_by_day,
                jsonb_agg(jsonb_build_object(
                    'customer', customer,
                    'total_spend', total_spend,
                    'metadata', metadata
                )) AS customers
            FROM
                (
                    SELECT
                        group_by_day,
                        customer,
                        SUM(model_api_spend) AS total_spend,
                        jsonb_agg(jsonb_build_object(
                            'model', model,
                            'api_key', api_key,
                            'spend', model_api_spend,
                            'total_tokens', model_api_tokens
                        )) AS metadata
                    FROM
                        SpendByModelApiKey
                    GROUP BY
                        group_by_day,
                        customer
                ) AS aggregated
            GROUP BY
                group_by_day
            ORDER BY
                group_by_day;
                """

            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )
            if db_response is None:
                return []

            return db_response
        elif group_by == "api_key":
            sql_query = """
                WITH SpendByModelApiKey AS (
                    SELECT
                        sl.api_key,
                        sl.model,
                        SUM(sl.spend) AS model_cost,
                        SUM(sl.prompt_tokens) AS model_input_tokens,
                        SUM(sl.completion_tokens) AS model_output_tokens
                    FROM
                        "LiteLLM_SpendLogs" sl
                    WHERE
                        sl."startTime" BETWEEN $1::date AND $2::date
                    GROUP BY
                        sl.api_key,
                        sl.model
                )
                SELECT
                    api_key,
                    SUM(model_cost) AS total_cost,
                    SUM(model_input_tokens) AS total_input_tokens,
                    SUM(model_output_tokens) AS total_output_tokens,
                    jsonb_agg(jsonb_build_object(
                        'model', model,
                        'total_cost', model_cost,
                        'total_input_tokens', model_input_tokens,
                        'total_output_tokens', model_output_tokens
                    )) AS model_details
                FROM
                    SpendByModelApiKey
                GROUP BY
                    api_key
                ORDER BY
                    total_cost DESC;
            """
            db_response = await prisma_client.db.query_raw(
                sql_query, start_date_obj, end_date_obj
            )
            if db_response is None:
                return []

            return db_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get(
    "/global/spend/all_tag_names",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def global_get_all_tag_names():
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        sql_query = """
        SELECT DISTINCT
            jsonb_array_elements_text(request_tags) AS individual_request_tag
        FROM "LiteLLM_SpendLogs";
        """

        db_response = await prisma_client.db.query_raw(sql_query)
        if db_response is None:
            return []

        _tag_names = []
        for row in db_response:
            _tag_names.append(row.get("individual_request_tag"))

        return {"tag_names": _tag_names}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/spend/all_tag_names Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/spend/all_tag_names Error" + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/global/spend/tags",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def global_view_spend_tags(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing key spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view key spend",
    ),
    tags: Optional[str] = fastapi.Query(
        default=None,
        description="comman separated tags to filter on",
    ),
):
    """
    LiteLLM Enterprise - View Spend Per Request Tag. Used by LiteLLM UI

    Example Request:
    ```
    curl -X GET "http://0.0.0.0:4000/spend/tags" \
-H "Authorization: Bearer sk-1234"
    ```

    Spend with Start Date and End Date
    ```
    curl -X GET "http://0.0.0.0:4000/spend/tags?start_date=2022-01-01&end_date=2022-02-01" \
-H "Authorization: Bearer sk-1234"
    ```
    """
    import traceback

    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        if end_date is None or start_date is None:
            raise ProxyException(
                message="Please provide start_date and end_date",
                type="bad_request",
                param=None,
                code=status.HTTP_400_BAD_REQUEST,
            )
        response = await ui_get_spend_by_tags(
            start_date=start_date,
            end_date=end_date,
            tags_str=tags,
            prisma_client=prisma_client,
        )

        return response
    except Exception as e:
        error_trace = traceback.format_exc()
        error_str = str(e) + "\n" + error_trace
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/spend/tags Error({error_str})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/spend/tags Error" + error_str,
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _get_spend_report_for_time_range(
    start_date: str,
    end_date: str,
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        verbose_proxy_logger.error(
            "Database not connected. Connect a database to your proxy for weekly, monthly spend reports"
        )
        return None

    try:
        sql_query = """
        SELECT
            t.team_alias,
            SUM(s.spend) AS total_spend
        FROM
            "LiteLLM_SpendLogs" s
        LEFT JOIN
            "LiteLLM_TeamTable" t ON s.team_id = t.team_id
        WHERE
            s."startTime"::DATE >= $1::date AND s."startTime"::DATE <= $2::date
        GROUP BY
            t.team_alias
        ORDER BY
            total_spend DESC;
        """
        response = await prisma_client.db.query_raw(sql_query, start_date, end_date)

        # get spend per tag for today
        sql_query = """
        SELECT 
        jsonb_array_elements_text(request_tags) AS individual_request_tag,
        SUM(spend) AS total_spend
        FROM "LiteLLM_SpendLogs"
        WHERE "startTime"::DATE >= $1::date AND "startTime"::DATE <= $2::date
        GROUP BY individual_request_tag
        ORDER BY total_spend DESC;
        """

        spend_per_tag = await prisma_client.db.query_raw(
            sql_query, start_date, end_date
        )

        return response, spend_per_tag
    except Exception as e:
        verbose_proxy_logger.error(
            "Exception in _get_daily_spend_reports {}".format(str(e))
        )


@router.post(
    "/spend/calculate",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {
            "cost": {
                "description": "The calculated cost",
                "example": 0.0,
                "type": "float",
            }
        }
    },
)
async def calculate_spend(request: SpendCalculateRequest):
    """
    Accepts all the params of completion_cost.

    Calculate spend **before** making call:

    Note: If you see a spend of $0.0 you need to set custom_pricing for your model: https://docs.litellm.ai/docs/proxy/custom_pricing

    ```
    curl --location 'http://localhost:4000/spend/calculate'
    --header 'Authorization: Bearer sk-1234'
    --header 'Content-Type: application/json'
    --data '{
        "model": "anthropic.claude-v2",
        "messages": [{"role": "user", "content": "Hey, how'''s it going?"}]
    }'
    ```

    Calculate spend **after** making call:

    ```
    curl --location 'http://localhost:4000/spend/calculate'
    --header 'Authorization: Bearer sk-1234'
    --header 'Content-Type: application/json'
    --data '{
        "completion_response": {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-3.5-turbo-0125",
            "system_fingerprint": "fp_44709d6fcb",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello there, how may I assist you today?"
                },
                "logprobs": null,
                "finish_reason": "stop"
            }]
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 12,
                "total_tokens": 21
            }
        }
    }'
    ```
    """
    try:
        from litellm import completion_cost
        from litellm.cost_calculator import CostPerToken
        from litellm.proxy.proxy_server import llm_router

        _cost = None
        if request.model is not None:
            if request.messages is None:
                raise HTTPException(
                    status_code=400,
                    detail="Bad Request - messages must be provided if 'model' is provided",
                )

            # check if model in llm_router
            _model_in_llm_router = None
            cost_per_token: Optional[CostPerToken] = None
            if llm_router is not None:
                if (
                    llm_router.model_group_alias is not None
                    and request.model in llm_router.model_group_alias
                ):
                    # lookup alias in llm_router
                    _model_group_name = llm_router.model_group_alias[request.model]
                    for model in llm_router.model_list:
                        if model.get("model_name") == _model_group_name:
                            _model_in_llm_router = model

                else:
                    # no model_group aliases set -> try finding model in llm_router
                    # find model in llm_router
                    for model in llm_router.model_list:
                        if model.get("model_name") == request.model:
                            _model_in_llm_router = model

            """
            3 cases for /spend/calculate

            1. user passes model, and model is defined on litellm config.yaml or in DB. use info on config or in DB in this case
            2. user passes model, and model is not defined on litellm config.yaml or in DB. Pass model as is to litellm.completion_cost
            3. user passes completion_response
            
            """
            if _model_in_llm_router is not None:
                _litellm_params = _model_in_llm_router.get("litellm_params")
                _litellm_model_name = _litellm_params.get("model")
                input_cost_per_token = _litellm_params.get("input_cost_per_token")
                output_cost_per_token = _litellm_params.get("output_cost_per_token")
                if (
                    input_cost_per_token is not None
                    or output_cost_per_token is not None
                ):
                    cost_per_token = CostPerToken(
                        input_cost_per_token=input_cost_per_token,
                        output_cost_per_token=output_cost_per_token,
                    )

                _cost = completion_cost(
                    model=_litellm_model_name,
                    messages=request.messages,
                    custom_cost_per_token=cost_per_token,
                )
            else:
                _cost = completion_cost(model=request.model, messages=request.messages)
        elif request.completion_response is not None:
            _completion_response = litellm.ModelResponse(**request.completion_response)
            _cost = completion_cost(completion_response=_completion_response)
        else:
            raise HTTPException(
                status_code=400,
                detail="Bad Request - Either 'model' or 'completion_response' must be provided",
            )
        return {"cost": _cost}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", str(e)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        error_msg = f"{str(e)}"
        raise ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )


@router.get(
    "/spend/logs/ui",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def ui_view_spend_logs(  # noqa: PLR0915
    api_key: Optional[str] = fastapi.Query(
        default=None,
        description="Get spend logs based on api key",
    ),
    user_id: Optional[str] = fastapi.Query(
        default=None,
        description="Get spend logs based on user_id",
    ),
    request_id: Optional[str] = fastapi.Query(
        default=None,
        description="request_id to get spend logs for specific request_id",
    ),
    team_id: Optional[str] = fastapi.Query(
        default=None,
        description="Filter spend logs by team_id",
    ),
    min_spend: Optional[float] = fastapi.Query(
        default=None,
        description="Filter logs with spend greater than or equal to this value",
    ),
    max_spend: Optional[float] = fastapi.Query(
        default=None,
        description="Filter logs with spend less than or equal to this value",
    ),
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing key spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view key spend",
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=50, description="Number of items per page", ge=1, le=100
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    status_filter: Optional[str] = fastapi.Query(
        default=None, description="Filter logs by status (e.g., success, failure)"
    ),
    model: Optional[str] = fastapi.Query(
        default=None, description="Filter logs by model"
    ),
):
    """
    View spend logs for UI with pagination support

    Returns:
        {
            "data": List[LiteLLM_SpendLogs],  # Paginated spend logs
            "total": int,                      # Total number of records
            "page": int,                       # Current page number
            "page_size": int,                  # Number of items per page
            "total_pages": int                 # Total number of pages
        }
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    if start_date is None or end_date is None:
        raise ProxyException(
            message="Start date and end date are required",
            type="bad_request",
            param="None",
            code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Convert the date strings to datetime objects
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )

        # Convert to ISO format strings for Prisma
        start_date_iso = start_date_obj.isoformat()  # Already in UTC, no need to add Z
        end_date_iso = end_date_obj.isoformat()  # Already in UTC, no need to add Z

        # Build where conditions
        where_conditions: dict[str, Any] = {
            "startTime": {"gte": start_date_iso, "lte": end_date_iso},
        }

        if team_id is not None:
            where_conditions["team_id"] = team_id

        status_condition = _build_status_filter_condition(status_filter)
        if status_condition:
            where_conditions.update(status_condition)

        if api_key is not None:
            where_conditions["api_key"] = api_key

        if user_id is not None:
            where_conditions["user"] = user_id

        if request_id is not None:
            where_conditions["request_id"] = request_id

        if model is not None:
            where_conditions["model"] = model

        if min_spend is not None or max_spend is not None:
            where_conditions["spend"] = {}
            if min_spend is not None:
                where_conditions["spend"]["gte"] = min_spend
            if max_spend is not None:
                where_conditions["spend"]["lte"] = max_spend
        # Calculate skip value for pagination
        skip = (page - 1) * page_size

        # Get total count of records
        total_records = await prisma_client.db.litellm_spendlogs.count(
            where=where_conditions,
        )

        # Get paginated data
        data = await prisma_client.db.litellm_spendlogs.find_many(
            where=where_conditions,
            order={
                "startTime": "desc",
            },
            skip=skip,
            take=page_size,
        )

        # Calculate total pages
        total_pages = (total_records + page_size - 1) // page_size

        verbose_proxy_logger.debug("data= %s", json.dumps(data, indent=4, default=str))

        return {
            "data": data,
            "total": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        verbose_proxy_logger.exception(f"Error in ui_view_spend_logs: {e}")
        raise handle_exception_on_proxy(e)


@lru_cache(maxsize=128)
@router.get(
    "/spend/logs/ui/{request_id}",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def ui_view_request_response_for_request_id(
    request_id: str,
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing key spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view key spend",
    ),
):
    """
    View request / response for a specific request_id

    - goes through all callbacks, checks if any of them have a @property -> has_request_response_payload
    - if so, it will return the request and response payload
    """
    custom_loggers = (
        litellm.logging_callback_manager.get_active_additional_logging_utils_from_custom_logger()
    )
    start_date_obj: Optional[datetime] = None
    end_date_obj: Optional[datetime] = None
    if start_date is not None:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    if end_date is not None:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )

    for custom_logger in custom_loggers:
        payload = await custom_logger.get_request_response_payload(
            request_id=request_id,
            start_time_utc=start_date_obj,
            end_time_utc=end_date_obj,
        )
        if payload is not None:
            return payload

    return None


@router.get(
    "/spend/logs",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def view_spend_logs(  # noqa: PLR0915
    api_key: Optional[str] = fastapi.Query(
        default=None,
        description="Get spend logs based on api key",
    ),
    user_id: Optional[str] = fastapi.Query(
        default=None,
        description="Get spend logs based on user_id",
    ),
    request_id: Optional[str] = fastapi.Query(
        default=None,
        description="request_id to get spend logs for specific request_id. If none passed then pass spend logs for all requests",
    ),
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time from which to start viewing key spend",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="Time till which to view key spend",
    ),
    summarize: bool = fastapi.Query(
        default=True,
        description="When start_date and end_date are provided, summarize=true returns aggregated data by date (legacy behavior), summarize=false returns filtered individual logs",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    View all spend logs, if request_id is provided, only logs for that request_id will be returned

    When start_date and end_date are provided:
    - summarize=true (default): Returns aggregated spend data grouped by date (maintains backward compatibility)
    - summarize=false: Returns filtered individual log entries within the date range

    Example Request for all logs
    ```
    curl -X GET "http://0.0.0.0:8000/spend/logs" \
-H "Authorization: Bearer sk-1234"
    ```

    Example Request for specific request_id
    ```
    curl -X GET "http://0.0.0.0:8000/spend/logs?request_id=chatcmpl-6dcb2540-d3d7-4e49-bb27-291f863f112e" \
-H "Authorization: Bearer sk-1234"
    ```

    Example Request for specific api_key
    ```
    curl -X GET "http://0.0.0.0:8000/spend/logs?api_key=sk-Fn8Ej39NkBQmUagFEoUWPQ" \
-H "Authorization: Bearer sk-1234"
    ```

    Example Request for specific user_id
    ```
    curl -X GET "http://0.0.0.0:8000/spend/logs?user_id=ishaan@berri.ai" \
-H "Authorization: Bearer sk-1234"
    ```

    Example Request for date range with individual logs (unsummarized)
    ```
    curl -X GET "http://0.0.0.0:8000/spend/logs?start_date=2024-01-01&end_date=2024-01-02&summarize=false" \
-H "Authorization: Bearer sk-1234"
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if (
        user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
        or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
    ):
        user_id = user_api_key_dict.user_id

    try:
        verbose_proxy_logger.debug("inside view_spend_logs")
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )
        spend_logs = []
        if (
            start_date is not None
            and isinstance(start_date, str)
            and end_date is not None
            and isinstance(end_date, str)
        ):
            # Convert the date strings to datetime objects
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

            filter_query = {
                "startTime": {
                    "gte": start_date_obj,  # Greater than or equal to Start Date
                    "lte": end_date_obj,  # Less than or equal to End Date
                }
            }

            if api_key is not None and isinstance(api_key, str):
                filter_query["api_key"] = api_key  # type: ignore
            elif request_id is not None and isinstance(request_id, str):
                filter_query["request_id"] = request_id  # type: ignore
            elif user_id is not None and isinstance(user_id, str):
                filter_query["user"] = user_id  # type: ignore

            # Check if user wants unsummarized data
            if not summarize:
                # Return filtered individual log entries (similar to UI endpoint)
                data = await prisma_client.db.litellm_spendlogs.find_many(
                    where=filter_query,  # type: ignore
                    order={
                        "startTime": "desc",
                    },
                )
                return data

            # Legacy behavior: return summarized data (when summarize=true)
            # SQL query
            response = await prisma_client.db.litellm_spendlogs.group_by(
                by=["api_key", "user", "model", "startTime"],
                where=filter_query,  # type: ignore
                sum={
                    "spend": True,
                },
            )

            if (
                isinstance(response, list)
                and len(response) > 0
                and isinstance(response[0], dict)
            ):
                result: dict = {}
                for record in response:
                    dt_object = datetime.strptime(str(record["startTime"]), "%Y-%m-%dT%H:%M:%S.%fZ")  # type: ignore
                    date = dt_object.date()
                    if date not in result:
                        result[date] = {"users": {}, "models": {}}
                    api_key = record["api_key"]  # type: ignore
                    user_id = record["user"]  # type: ignore
                    model = record["model"]  # type: ignore
                    result[date]["spend"] = result[date].get("spend", 0) + record.get(
                        "_sum", {}
                    ).get("spend", 0)
                    result[date][api_key] = result[date].get(api_key, 0) + record.get(
                        "_sum", {}
                    ).get("spend", 0)
                    result[date]["users"][user_id] = result[date]["users"].get(
                        user_id, 0
                    ) + record.get("_sum", {}).get("spend", 0)
                    result[date]["models"][model] = result[date]["models"].get(
                        model, 0
                    ) + record.get("_sum", {}).get("spend", 0)
                return_list = []
                final_date = None
                for k, v in sorted(result.items()):
                    return_list.append({**v, "startTime": k})
                    final_date = k

                end_date_date = end_date_obj.date()
                if final_date is not None and final_date < end_date_date:
                    current_date = final_date + timedelta(days=1)
                    while current_date <= end_date_date:
                        # Represent current_date as string because original response has it this way
                        return_list.append(
                            {
                                "startTime": current_date,
                                "spend": 0,
                                "users": {},
                                "models": {},
                            }
                        )  # If no data, will stay as zero
                        current_date += timedelta(days=1)  # Move on to the next day

                return return_list

            return response

        elif api_key is not None and isinstance(api_key, str):
            if api_key.startswith("sk-"):
                hashed_token = prisma_client.hash_token(token=api_key)
            else:
                hashed_token = api_key
            spend_log = await prisma_client.get_data(
                table_name="spend",
                query_type="find_all",
                key_val={"key": "api_key", "value": hashed_token},
            )
            if isinstance(spend_log, list):
                return spend_log
            else:
                return [spend_log]
        elif request_id is not None:
            spend_log = await prisma_client.get_data(
                table_name="spend",
                query_type="find_unique",
                key_val={"key": "request_id", "value": request_id},
            )
            return [spend_log]
        elif user_id is not None:
            spend_log = await prisma_client.get_data(
                table_name="spend",
                query_type="find_all",
                key_val={"key": "user", "value": user_id},
            )
            if isinstance(spend_log, list):
                return spend_log
            else:
                return [spend_log]
        else:
            spend_logs = await prisma_client.get_data(
                table_name="spend", query_type="find_all"
            )

            return spend_logs

        return None

    except Exception as e:
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/spend/logs Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/spend/logs Error" + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post(
    "/global/spend/reset",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
)
async def global_spend_reset():
    """
    ADMIN ONLY / MASTER KEY Only Endpoint

    Globally reset spend for All API Keys and Teams, maintain LiteLLM_SpendLogs

    1. LiteLLM_SpendLogs will maintain the logs on spend, no data gets deleted from there
    2. LiteLLM_VerificationTokens spend will be set = 0
    3. LiteLLM_TeamTable spend will be set = 0

    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    await prisma_client.db.litellm_verificationtoken.update_many(
        data={"spend": 0.0}, where={}
    )
    await prisma_client.db.litellm_teamtable.update_many(data={"spend": 0.0}, where={})

    return {
        "message": "Spend for all API Keys and Teams reset successfully",
        "status": "success",
    }


@router.post(
    "/global/spend/refresh",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_refresh():
    """
    ADMIN ONLY / MASTER KEY Only Endpoint

    Globally refresh spend MonthlyGlobalSpend view
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    ## RESET GLOBAL SPEND VIEW ###
    async def is_materialized_global_spend_view() -> bool:
        """
        Return True if materialized view exists

        Else False
        """
        sql_query = """
        SELECT relname, relkind
        FROM pg_class
        WHERE relname = 'MonthlyGlobalSpend';            
        """
        try:
            resp = await prisma_client.db.query_raw(sql_query)

            return resp[0]["relkind"] == "m"
        except Exception:
            return False

    view_exists = await is_materialized_global_spend_view()

    if view_exists:
        # refresh materialized view
        sql_query = """
        REFRESH MATERIALIZED VIEW "MonthlyGlobalSpend";    
        """
        try:
            from litellm.proxy._types import CommonProxyErrors
            from litellm.proxy.proxy_server import proxy_logging_obj
            from litellm.proxy.utils import PrismaClient

            db_url = os.getenv("DATABASE_URL")
            if db_url is None:
                raise Exception(CommonProxyErrors.db_not_connected_error.value)
            new_client = PrismaClient(
                database_url=db_url,
                proxy_logging_obj=proxy_logging_obj,
                http_client={
                    "timeout": 6000,
                },
            )
            await new_client.db.connect()
            await new_client.db.query_raw(sql_query)
            verbose_proxy_logger.info("MonthlyGlobalSpend view refreshed")
            return {
                "message": "MonthlyGlobalSpend view refreshed",
                "status": "success",
            }

        except Exception as e:
            verbose_proxy_logger.exception(
                "Failed to refresh materialized view - {}".format(str(e))
            )
            return {
                "message": "Failed to refresh materialized view",
                "status": "failure",
            }


async def global_spend_for_internal_user(
    api_key: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    try:
        user_id = user_api_key_dict.user_id
        if user_id is None:
            raise ValueError("/global/spend/logs Error: User ID is None")
        if api_key is not None:
            sql_query = """
                SELECT * FROM "MonthlyGlobalSpendPerUserPerKey"
                WHERE "api_key" = $1 AND "user" = $2
                ORDER BY "date";
                """

            response = await prisma_client.db.query_raw(sql_query, api_key, user_id)

            return response

        sql_query = """SELECT * FROM "MonthlyGlobalSpendPerUserPerKey"  WHERE "user" = $1 ORDER BY "date";"""

        response = await prisma_client.db.query_raw(sql_query, user_id)

        return response
    except Exception as e:
        verbose_proxy_logger.error(f"/global/spend/logs Error: {str(e)}")
        raise e


@router.get(
    "/global/spend/logs",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_logs(
    api_key: Optional[str] = fastapi.Query(
        default=None,
        description="API Key to get global spend (spend per day for last 30d). Admin-only endpoint",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to get global spend (spend per day for last 30d). Admin-only endpoint

    More efficient implementation of /spend/logs, by creating a view over the spend logs table.
    """
    import traceback

    from litellm.integrations.prometheus_helpers.prometheus_api import (
        get_daily_spend_from_prometheus,
        is_prometheus_connected,
    )
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise ProxyException(
                message="Prisma Client is not initialized",
                type="internal_error",
                param="None",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if (
            user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
            or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
        ):
            response = await global_spend_for_internal_user(
                api_key=api_key, user_api_key_dict=user_api_key_dict
            )

            return response

        prometheus_api_enabled = is_prometheus_connected()

        if prometheus_api_enabled:
            response = await get_daily_spend_from_prometheus(api_key=api_key)
            return response
        else:
            if api_key is None:
                sql_query = """SELECT * FROM "MonthlyGlobalSpend" ORDER BY "date";"""

                response = await prisma_client.db.query_raw(query=sql_query)

                return response
            else:
                sql_query = """
                    SELECT * FROM "MonthlyGlobalSpendPerKey"
                    WHERE "api_key" = $1
                    ORDER BY "date";
                    """

                response = await prisma_client.db.query_raw(sql_query, api_key)

                return response

    except Exception as e:
        error_trace = traceback.format_exc()
        error_str = str(e) + "\n" + error_trace
        verbose_proxy_logger.error(f"/global/spend/logs Error: {error_str}")
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/global/spend/logs Error({error_str})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/global/spend/logs Error" + error_str,
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/global/spend",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend():
    """
    [BETA] This is a beta endpoint. It will change.

    View total spend across all proxy keys
    """
    import traceback

    from litellm.proxy.proxy_server import prisma_client

    try:
        total_spend = 0.0

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})
        sql_query = """SELECT SUM(spend) as total_spend FROM "MonthlyGlobalSpend";"""
        response = await prisma_client.db.query_raw(query=sql_query)
        if response is not None:
            if isinstance(response, list) and len(response) > 0:
                total_spend = response[0].get("total_spend", 0.0)

        return {"spend": total_spend, "max_budget": litellm.max_budget}
    except Exception as e:
        error_trace = traceback.format_exc()
        error_str = str(e) + "\n" + error_trace
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"/global/spend Error({error_str})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="/global/spend Error" + error_str,
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def global_spend_key_internal_user(
    user_api_key_dict: UserAPIKeyAuth, limit: int = 10
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    user_id = user_api_key_dict.user_id
    if user_id is None:
        raise HTTPException(status_code=500, detail={"error": "No user_id found"})

    sql_query = """
            WITH top_api_keys AS (
            SELECT 
                api_key,
                SUM(spend) as total_spend
            FROM 
                "LiteLLM_SpendLogs"
            WHERE 
                "user" = $1
            GROUP BY 
                api_key
            ORDER BY 
                total_spend DESC
            LIMIT $2  -- Adjust this number to get more or fewer top keys
        )
        SELECT 
            t.api_key,
            t.total_spend,
            v.key_alias,
            v.key_name
        FROM 
            top_api_keys t
        LEFT JOIN 
            "LiteLLM_VerificationToken" v ON t.api_key = v.token
        ORDER BY 
            t.total_spend DESC;
    
    """

    response = await prisma_client.db.query_raw(sql_query, user_id, limit)

    return response


@router.get(
    "/global/spend/keys",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_keys(
    limit: int = fastapi.Query(
        default=None,
        description="Number of keys to get. Will return Top 'n' keys.",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to get the top 'n' keys with the highest spend, ordered by spend.
    """
    from litellm.proxy.proxy_server import prisma_client

    if (
        user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
        or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
    ):
        response = await global_spend_key_internal_user(
            user_api_key_dict=user_api_key_dict
        )

        return response
    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})
    sql_query = """SELECT * FROM "Last30dKeysBySpend";"""

    if limit is None:
        response = await prisma_client.db.query_raw(sql_query)
        return response
    try:
        limit = int(limit)
        if limit < 1:
            raise ValueError("Limit must be greater than 0")
        sql_query = """SELECT * FROM "Last30dKeysBySpend" LIMIT $1 ;"""
        response = await prisma_client.db.query_raw(sql_query, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail={"error": f"Invalid limit: {limit}, error: {e}"}
        ) from e

    return response


@router.get(
    "/global/spend/teams",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_per_team():
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to get daily spend, grouped by `team_id` and `date`
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})
    sql_query = """
        SELECT
            t.team_alias as team_alias,
            DATE(s."startTime") AS spend_date,
            SUM(s.spend) AS total_spend
        FROM
            "LiteLLM_SpendLogs" s
        LEFT JOIN
            "LiteLLM_TeamTable" t ON s.team_id = t.team_id
        WHERE
            s."startTime" >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY
            t.team_alias,
            DATE(s."startTime")
        ORDER BY
            spend_date;
        """
    response = await prisma_client.db.query_raw(query=sql_query)

    # transform the response for the Admin UI
    spend_by_date = {}
    team_aliases = set()
    total_spend_per_team = {}
    for row in response:
        row_date = row["spend_date"]
        if row_date is None:
            continue
        team_alias = row["team_alias"]
        if team_alias is None:
            team_alias = "Unassigned"
        team_aliases.add(team_alias)
        if row_date in spend_by_date:
            # get the team_id for this entry
            # get the spend for this entry
            spend = row["total_spend"]
            spend = round(spend, 2)
            current_date_entries = spend_by_date[row_date]
            current_date_entries[team_alias] = spend
        else:
            spend = row["total_spend"]
            spend = round(spend, 2)
            spend_by_date[row_date] = {team_alias: spend}

        if team_alias in total_spend_per_team:
            total_spend_per_team[team_alias] += spend
        else:
            total_spend_per_team[team_alias] = spend

    total_spend_per_team_ui = []
    # order the elements in total_spend_per_team by spend
    total_spend_per_team = dict(
        sorted(total_spend_per_team.items(), key=lambda item: item[1], reverse=True)
    )
    for team_id in total_spend_per_team:
        # only add first 10 elements to total_spend_per_team_ui
        if len(total_spend_per_team_ui) >= 10:
            break
        if team_id is None:
            team_id = "Unassigned"
        total_spend_per_team_ui.append(
            {"team_id": team_id, "total_spend": total_spend_per_team[team_id]}
        )

    # sort spend_by_date by it's key (which is a date)

    response_data = []
    for key in spend_by_date:
        value = spend_by_date[key]
        response_data.append({"date": key, **value})

    return {
        "daily_spend": response_data,
        "teams": list(team_aliases),
        "total_spend_per_team": total_spend_per_team_ui,
    }


@router.get(
    "/global/all_end_users",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_view_all_end_users():
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to just get all the unique `end_users`
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    sql_query = """
    SELECT DISTINCT end_user FROM "LiteLLM_SpendLogs"
    """

    db_response = await prisma_client.db.query_raw(query=sql_query)
    if db_response is None:
        return []

    _end_users = []
    for row in db_response:
        _end_users.append(row["end_user"])

    return {"end_users": _end_users}


@router.post(
    "/global/spend/end_users",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_end_users(data: Optional[GlobalEndUsersSpend] = None):
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to get the top 'n' keys with the highest spend, ordered by spend.
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    """
    Gets the top 100 end-users for a given api key
    """
    startTime = None
    endTime = None
    selected_api_key = None
    if data is not None:
        startTime = data.startTime
        endTime = data.endTime
        selected_api_key = data.api_key

    startTime = startTime or datetime.now() - timedelta(days=30)
    endTime = endTime or datetime.now()

    sql_query = """
SELECT end_user, COUNT(*) AS total_count, SUM(spend) AS total_spend
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= $1::timestamp
  AND "startTime" < $2::timestamp
  AND (
    CASE
      WHEN $3::TEXT IS NULL THEN TRUE
      ELSE api_key = $3
    END
  )
GROUP BY end_user
ORDER BY total_spend DESC
LIMIT 100
    """
    response = await prisma_client.db.query_raw(
        sql_query, startTime, endTime, selected_api_key
    )

    return response


async def global_spend_models_internal_user(
    user_api_key_dict: UserAPIKeyAuth, limit: int = 10
):
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    user_id = user_api_key_dict.user_id
    if user_id is None:
        raise HTTPException(status_code=500, detail={"error": "No user_id found"})

    sql_query = """
        SELECT 
            model,
            SUM(spend) as total_spend,
            SUM(total_tokens) as total_tokens
        FROM 
            "LiteLLM_SpendLogs"
        WHERE 
            "user" = $1
        GROUP BY 
            model
        ORDER BY 
            total_spend DESC
        LIMIT $2;
    """

    response = await prisma_client.db.query_raw(sql_query, user_id, limit)

    return response


@router.get(
    "/global/spend/models",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def global_spend_models(
    limit: int = fastapi.Query(
        default=10,
        description="Number of models to get. Will return Top 'n' models.",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [BETA] This is a beta endpoint. It will change.

    Use this to get the top 'n' models with the highest spend, ordered by spend.
    """
    from litellm.proxy.proxy_server import prisma_client

    if (
        user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER
        or user_api_key_dict.user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
    ):
        response = await global_spend_models_internal_user(
            user_api_key_dict=user_api_key_dict, limit=limit
        )
        return response

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    sql_query = """SELECT * FROM "Last30dModelsBySpend" LIMIT $1 ;"""

    response = await prisma_client.db.query_raw(sql_query, int(limit))

    return response


@router.get("/provider/budgets", response_model=ProviderBudgetResponse)
async def provider_budgets() -> ProviderBudgetResponse:
    """
    Provider Budget Routing - Get Budget, Spend Details https://docs.litellm.ai/docs/proxy/provider_budget_routing

    Use this endpoint to check current budget, spend and budget reset time for a provider

    Example Request

    ```bash
    curl -X GET http://localhost:4000/provider/budgets \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-1234"
    ```

    Example Response

    ```json
    {
        "providers": {
            "openai": {
                "budget_limit": 1e-12,
                "time_period": "1d",
                "spend": 0.0,
                "budget_reset_at": null
            },
            "azure": {
                "budget_limit": 100.0,
                "time_period": "1d",
                "spend": 0.0,
                "budget_reset_at": null
            },
            "anthropic": {
                "budget_limit": 100.0,
                "time_period": "10d",
                "spend": 0.0,
                "budget_reset_at": null
            },
            "vertex_ai": {
                "budget_limit": 100.0,
                "time_period": "12d",
                "spend": 0.0,
                "budget_reset_at": null
            }
        }
    }
    ```

    """
    from litellm.proxy.proxy_server import llm_router

    try:
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": "No llm_router found"}
            )

        provider_budget_config = llm_router.provider_budget_config
        if provider_budget_config is None:
            raise ValueError(
                "No provider budget config found. Please set a provider budget config in the router settings. https://docs.litellm.ai/docs/proxy/provider_budget_routing"
            )

        provider_budget_response_dict: Dict[str, ProviderBudgetResponseObject] = {}
        for _provider, _budget_info in provider_budget_config.items():
            if llm_router.router_budget_logger is None:
                raise ValueError("No router budget logger found")
            _provider_spend = (
                await llm_router.router_budget_logger._get_current_provider_spend(
                    _provider
                )
                or 0.0
            )
            _provider_budget_ttl = await llm_router.router_budget_logger._get_current_provider_budget_reset_at(
                _provider
            )
            provider_budget_response_object = ProviderBudgetResponseObject(
                budget_limit=_budget_info.max_budget,
                time_period=_budget_info.budget_duration,
                spend=_provider_spend,
                budget_reset_at=_provider_budget_ttl,
            )
            provider_budget_response_dict[_provider] = provider_budget_response_object
        return ProviderBudgetResponse(providers=provider_budget_response_dict)
    except Exception as e:
        verbose_proxy_logger.exception(
            "/provider/budgets: Exception occured - {}".format(str(e))
        )
        raise handle_exception_on_proxy(e)


async def get_spend_by_tags(
    prisma_client: PrismaClient, start_date=None, end_date=None
):
    response = await prisma_client.db.query_raw(
        """
        SELECT
        jsonb_array_elements_text(request_tags) AS individual_request_tag,
        COUNT(*) AS log_count,
        SUM(spend) AS total_spend
        FROM "LiteLLM_SpendLogs"
        GROUP BY individual_request_tag;
        """
    )

    return response


async def ui_get_spend_by_tags(
    start_date: str,
    end_date: str,
    prisma_client: Optional[PrismaClient] = None,
    tags_str: Optional[str] = None,
):
    """
    Should cover 2 cases:
    1. When user is getting spend for all_tags. "all_tags" in tags_list
    2. When user is getting spend for specific tags.
    """

    # tags_str is a list of strings csv of tags
    # tags_str = tag1,tag2,tag3
    # convert to list if it's not None
    tags_list: Optional[List[str]] = None
    if tags_str is not None and len(tags_str) > 0:
        tags_list = tags_str.split(",")

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    response = None
    if tags_list is None or (isinstance(tags_list, list) and "all-tags" in tags_list):
        # Get spend for all tags
        sql_query = """
        SELECT
            individual_request_tag,
            spend_date,
            log_count,
            total_spend
        FROM "DailyTagSpend"
        WHERE spend_date >= $1::date AND spend_date <= $2::date
        ORDER BY total_spend DESC;
        """
        response = await prisma_client.db.query_raw(
            sql_query,
            start_date,
            end_date,
        )
    else:
        # filter by tags list
        sql_query = """
        SELECT
            individual_request_tag,
            SUM(log_count) AS log_count,
            SUM(total_spend) AS total_spend
        FROM "DailyTagSpend"
        WHERE spend_date >= $1::date AND spend_date <= $2::date
          AND individual_request_tag = ANY($3::text[])
        GROUP BY individual_request_tag
        ORDER BY total_spend DESC;
        """
        response = await prisma_client.db.query_raw(
            sql_query,
            start_date,
            end_date,
            tags_list,
        )

    # print("tags - spend")
    # print(response)
    # Bar Chart 1 - Spend per tag - Top 10 tags by spend
    total_spend_per_tag: collections.defaultdict = collections.defaultdict(float)
    total_requests_per_tag: collections.defaultdict = collections.defaultdict(int)
    for row in response:
        tag_name = row["individual_request_tag"]
        tag_spend = row["total_spend"]

        total_spend_per_tag[tag_name] += tag_spend
        total_requests_per_tag[tag_name] += row["log_count"]

    sorted_tags = sorted(total_spend_per_tag.items(), key=lambda x: x[1], reverse=True)
    # convert to ui format
    ui_tags = []
    for tag in sorted_tags:
        current_spend = tag[1]
        if current_spend is not None and isinstance(current_spend, float):
            current_spend = round(current_spend, 4)
        ui_tags.append(
            {
                "name": tag[0],
                "spend": current_spend,
                "log_count": total_requests_per_tag[tag[0]],
            }
        )

    return {"spend_per_tag": ui_tags}


@router.get(
    "/spend/logs/session/ui",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_SpendLogs]},
    },
)
async def ui_view_session_spend_logs(
    session_id: str = fastapi.Query(
        description="Get all spend logs for a particular session",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get all spend logs for a particular session
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not connected",
            )

        # Build query conditions
        where_conditions = {"session_id": session_id}
        # Query the database
        result = await prisma_client.db.litellm_spendlogs.find_many(
            where=where_conditions, order={"startTime": "asc"}
        )
        return result
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )


def _build_status_filter_condition(status_filter: Optional[str]) -> Dict[str, Any]:
    """
    Helper function to build the status filter condition for database queries.

    Args:
        status_filter (Optional[str]): The status to filter by. Can be "success" or "failure".

    Returns:
        Dict[str, Any]: A dictionary containing the status filter condition.
    """
    if status_filter is None:
        return {}

    if status_filter == "success":
        return {"OR": [{"status": {"equals": "success"}}, {"status": None}]}
    else:
        return {"status": {"equals": status_filter}}

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\__init__.py ===
#-------------------------------------------------------------------
# tarfile.py
#-------------------------------------------------------------------
# Copyright (C) 2002 Lars Gustaebel <lars@gustaebel.de>
# All rights reserved.
#
# Permission  is  hereby granted,  free  of charge,  to  any person
# obtaining a  copy of  this software  and associated documentation
# files  (the  "Software"),  to   deal  in  the  Software   without
# restriction,  including  without limitation  the  rights to  use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies  of  the  Software,  and to  permit  persons  to  whom the
# Software  is  furnished  to  do  so,  subject  to  the  following
# conditions:
#
# The above copyright  notice and this  permission notice shall  be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS  IS", WITHOUT WARRANTY OF ANY  KIND,
# EXPRESS OR IMPLIED, INCLUDING  BUT NOT LIMITED TO  THE WARRANTIES
# OF  MERCHANTABILITY,  FITNESS   FOR  A  PARTICULAR   PURPOSE  AND
# NONINFRINGEMENT.  IN  NO  EVENT SHALL  THE  AUTHORS  OR COPYRIGHT
# HOLDERS  BE LIABLE  FOR ANY  CLAIM, DAMAGES  OR OTHER  LIABILITY,
# WHETHER  IN AN  ACTION OF  CONTRACT, TORT  OR OTHERWISE,  ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""Read from and write to tar format archives.
"""

version     = "0.9.0"
__author__  = "Lars Gust\u00e4bel (lars@gustaebel.de)"
__credits__ = "Gustavo Niemeyer, Niels Gust\u00e4bel, Richard Townsend."

#---------
# Imports
#---------
from builtins import open as bltn_open
import sys
import os
import io
import shutil
import stat
import time
import struct
import copy
import re

from .compat.py38 import removesuffix

try:
    import pwd
except ImportError:
    pwd = None
try:
    import grp
except ImportError:
    grp = None

# os.symlink on Windows prior to 6.0 raises NotImplementedError
# OSError (winerror=1314) will be raised if the caller does not hold the
# SeCreateSymbolicLinkPrivilege privilege
symlink_exception = (AttributeError, NotImplementedError, OSError)

# from tarfile import *
__all__ = ["TarFile", "TarInfo", "is_tarfile", "TarError", "ReadError",
           "CompressionError", "StreamError", "ExtractError", "HeaderError",
           "ENCODING", "USTAR_FORMAT", "GNU_FORMAT", "PAX_FORMAT",
           "DEFAULT_FORMAT", "open","fully_trusted_filter", "data_filter",
           "tar_filter", "FilterError", "AbsoluteLinkError",
           "OutsideDestinationError", "SpecialFileError", "AbsolutePathError",
           "LinkOutsideDestinationError"]


#---------------------------------------------------------
# tar constants
#---------------------------------------------------------
NUL = b"\0"                     # the null character
BLOCKSIZE = 512                 # length of processing blocks
RECORDSIZE = BLOCKSIZE * 20     # length of records
GNU_MAGIC = b"ustar  \0"        # magic gnu tar string
POSIX_MAGIC = b"ustar\x0000"    # magic posix tar string

LENGTH_NAME = 100               # maximum length of a filename
LENGTH_LINK = 100               # maximum length of a linkname
LENGTH_PREFIX = 155             # maximum length of the prefix field

REGTYPE = b"0"                  # regular file
AREGTYPE = b"\0"                # regular file
LNKTYPE = b"1"                  # link (inside tarfile)
SYMTYPE = b"2"                  # symbolic link
CHRTYPE = b"3"                  # character special device
BLKTYPE = b"4"                  # block special device
DIRTYPE = b"5"                  # directory
FIFOTYPE = b"6"                 # fifo special device
CONTTYPE = b"7"                 # contiguous file

GNUTYPE_LONGNAME = b"L"         # GNU tar longname
GNUTYPE_LONGLINK = b"K"         # GNU tar longlink
GNUTYPE_SPARSE = b"S"           # GNU tar sparse file

XHDTYPE = b"x"                  # POSIX.1-2001 extended header
XGLTYPE = b"g"                  # POSIX.1-2001 global header
SOLARIS_XHDTYPE = b"X"          # Solaris extended header

USTAR_FORMAT = 0                # POSIX.1-1988 (ustar) format
GNU_FORMAT = 1                  # GNU tar format
PAX_FORMAT = 2                  # POSIX.1-2001 (pax) format
DEFAULT_FORMAT = PAX_FORMAT

#---------------------------------------------------------
# tarfile constants
#---------------------------------------------------------
# File types that tarfile supports:
SUPPORTED_TYPES = (REGTYPE, AREGTYPE, LNKTYPE,
                   SYMTYPE, DIRTYPE, FIFOTYPE,
                   CONTTYPE, CHRTYPE, BLKTYPE,
                   GNUTYPE_LONGNAME, GNUTYPE_LONGLINK,
                   GNUTYPE_SPARSE)

# File types that will be treated as a regular file.
REGULAR_TYPES = (REGTYPE, AREGTYPE,
                 CONTTYPE, GNUTYPE_SPARSE)

# File types that are part of the GNU tar format.
GNU_TYPES = (GNUTYPE_LONGNAME, GNUTYPE_LONGLINK,
             GNUTYPE_SPARSE)

# Fields from a pax header that override a TarInfo attribute.
PAX_FIELDS = ("path", "linkpath", "size", "mtime",
              "uid", "gid", "uname", "gname")

# Fields from a pax header that are affected by hdrcharset.
PAX_NAME_FIELDS = {"path", "linkpath", "uname", "gname"}

# Fields in a pax header that are numbers, all other fields
# are treated as strings.
PAX_NUMBER_FIELDS = {
    "atime": float,
    "ctime": float,
    "mtime": float,
    "uid": int,
    "gid": int,
    "size": int
}

#---------------------------------------------------------
# initialization
#---------------------------------------------------------
if os.name == "nt":
    ENCODING = "utf-8"
else:
    ENCODING = sys.getfilesystemencoding()

#---------------------------------------------------------
# Some useful functions
#---------------------------------------------------------

def stn(s, length, encoding, errors):
    """Convert a string to a null-terminated bytes object.
    """
    if s is None:
        raise ValueError("metadata cannot contain None")
    s = s.encode(encoding, errors)
    return s[:length] + (length - len(s)) * NUL

def nts(s, encoding, errors):
    """Convert a null-terminated bytes object to a string.
    """
    p = s.find(b"\0")
    if p != -1:
        s = s[:p]
    return s.decode(encoding, errors)

def nti(s):
    """Convert a number field to a python number.
    """
    # There are two possible encodings for a number field, see
    # itn() below.
    if s[0] in (0o200, 0o377):
        n = 0
        for i in range(len(s) - 1):
            n <<= 8
            n += s[i + 1]
        if s[0] == 0o377:
            n = -(256 ** (len(s) - 1) - n)
    else:
        try:
            s = nts(s, "ascii", "strict")
            n = int(s.strip() or "0", 8)
        except ValueError:
            raise InvalidHeaderError("invalid header")
    return n

def itn(n, digits=8, format=DEFAULT_FORMAT):
    """Convert a python number to a number field.
    """
    # POSIX 1003.1-1988 requires numbers to be encoded as a string of
    # octal digits followed by a null-byte, this allows values up to
    # (8**(digits-1))-1. GNU tar allows storing numbers greater than
    # that if necessary. A leading 0o200 or 0o377 byte indicate this
    # particular encoding, the following digits-1 bytes are a big-endian
    # base-256 representation. This allows values up to (256**(digits-1))-1.
    # A 0o200 byte indicates a positive number, a 0o377 byte a negative
    # number.
    original_n = n
    n = int(n)
    if 0 <= n < 8 ** (digits - 1):
        s = bytes("%0*o" % (digits - 1, n), "ascii") + NUL
    elif format == GNU_FORMAT and -256 ** (digits - 1) <= n < 256 ** (digits - 1):
        if n >= 0:
            s = bytearray([0o200])
        else:
            s = bytearray([0o377])
            n = 256 ** digits + n

        for i in range(digits - 1):
            s.insert(1, n & 0o377)
            n >>= 8
    else:
        raise ValueError("overflow in number field")

    return s

def calc_chksums(buf):
    """Calculate the checksum for a member's header by summing up all
       characters except for the chksum field which is treated as if
       it was filled with spaces. According to the GNU tar sources,
       some tars (Sun and NeXT) calculate chksum with signed char,
       which will be different if there are chars in the buffer with
       the high bit set. So we calculate two checksums, unsigned and
       signed.
    """
    unsigned_chksum = 256 + sum(struct.unpack_from("148B8x356B", buf))
    signed_chksum = 256 + sum(struct.unpack_from("148b8x356b", buf))
    return unsigned_chksum, signed_chksum

def copyfileobj(src, dst, length=None, exception=OSError, bufsize=None):
    """Copy length bytes from fileobj src to fileobj dst.
       If length is None, copy the entire content.
    """
    bufsize = bufsize or 16 * 1024
    if length == 0:
        return
    if length is None:
        shutil.copyfileobj(src, dst, bufsize)
        return

    blocks, remainder = divmod(length, bufsize)
    for b in range(blocks):
        buf = src.read(bufsize)
        if len(buf) < bufsize:
            raise exception("unexpected end of data")
        dst.write(buf)

    if remainder != 0:
        buf = src.read(remainder)
        if len(buf) < remainder:
            raise exception("unexpected end of data")
        dst.write(buf)
    return

def _safe_print(s):
    encoding = getattr(sys.stdout, 'encoding', None)
    if encoding is not None:
        s = s.encode(encoding, 'backslashreplace').decode(encoding)
    print(s, end=' ')


class TarError(Exception):
    """Base exception."""
    pass
class ExtractError(TarError):
    """General exception for extract errors."""
    pass
class ReadError(TarError):
    """Exception for unreadable tar archives."""
    pass
class CompressionError(TarError):
    """Exception for unavailable compression methods."""
    pass
class StreamError(TarError):
    """Exception for unsupported operations on stream-like TarFiles."""
    pass
class HeaderError(TarError):
    """Base exception for header errors."""
    pass
class EmptyHeaderError(HeaderError):
    """Exception for empty headers."""
    pass
class TruncatedHeaderError(HeaderError):
    """Exception for truncated headers."""
    pass
class EOFHeaderError(HeaderError):
    """Exception for end of file headers."""
    pass
class InvalidHeaderError(HeaderError):
    """Exception for invalid headers."""
    pass
class SubsequentHeaderError(HeaderError):
    """Exception for missing and invalid extended headers."""
    pass

#---------------------------
# internal stream interface
#---------------------------
class _LowLevelFile:
    """Low-level file object. Supports reading and writing.
       It is used instead of a regular file object for streaming
       access.
    """

    def __init__(self, name, mode):
        mode = {
            "r": os.O_RDONLY,
            "w": os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        }[mode]
        if hasattr(os, "O_BINARY"):
            mode |= os.O_BINARY
        self.fd = os.open(name, mode, 0o666)

    def close(self):
        os.close(self.fd)

    def read(self, size):
        return os.read(self.fd, size)

    def write(self, s):
        os.write(self.fd, s)

class _Stream:
    """Class that serves as an adapter between TarFile and
       a stream-like object.  The stream-like object only
       needs to have a read() or write() method that works with bytes,
       and the method is accessed blockwise.
       Use of gzip or bzip2 compression is possible.
       A stream-like object could be for example: sys.stdin.buffer,
       sys.stdout.buffer, a socket, a tape device etc.

       _Stream is intended to be used only internally.
    """

    def __init__(self, name, mode, comptype, fileobj, bufsize,
                 compresslevel):
        """Construct a _Stream object.
        """
        self._extfileobj = True
        if fileobj is None:
            fileobj = _LowLevelFile(name, mode)
            self._extfileobj = False

        if comptype == '*':
            # Enable transparent compression detection for the
            # stream interface
            fileobj = _StreamProxy(fileobj)
            comptype = fileobj.getcomptype()

        self.name     = name or ""
        self.mode     = mode
        self.comptype = comptype
        self.fileobj  = fileobj
        self.bufsize  = bufsize
        self.buf      = b""
        self.pos      = 0
        self.closed   = False

        try:
            if comptype == "gz":
                try:
                    import zlib
                except ImportError:
                    raise CompressionError("zlib module is not available") from None
                self.zlib = zlib
                self.crc = zlib.crc32(b"")
                if mode == "r":
                    self.exception = zlib.error
                    self._init_read_gz()
                else:
                    self._init_write_gz(compresslevel)

            elif comptype == "bz2":
                try:
                    import bz2
                except ImportError:
                    raise CompressionError("bz2 module is not available") from None
                if mode == "r":
                    self.dbuf = b""
                    self.cmp = bz2.BZ2Decompressor()
                    self.exception = OSError
                else:
                    self.cmp = bz2.BZ2Compressor(compresslevel)

            elif comptype == "xz":
                try:
                    import lzma
                except ImportError:
                    raise CompressionError("lzma module is not available") from None
                if mode == "r":
                    self.dbuf = b""
                    self.cmp = lzma.LZMADecompressor()
                    self.exception = lzma.LZMAError
                else:
                    self.cmp = lzma.LZMACompressor()

            elif comptype != "tar":
                raise CompressionError("unknown compression type %r" % comptype)

        except:
            if not self._extfileobj:
                self.fileobj.close()
            self.closed = True
            raise

    def __del__(self):
        if hasattr(self, "closed") and not self.closed:
            self.close()

    def _init_write_gz(self, compresslevel):
        """Initialize for writing with gzip compression.
        """
        self.cmp = self.zlib.compressobj(compresslevel,
                                         self.zlib.DEFLATED,
                                         -self.zlib.MAX_WBITS,
                                         self.zlib.DEF_MEM_LEVEL,
                                         0)
        timestamp = struct.pack("<L", int(time.time()))
        self.__write(b"\037\213\010\010" + timestamp + b"\002\377")
        if self.name.endswith(".gz"):
            self.name = self.name[:-3]
        # Honor "directory components removed" from RFC1952
        self.name = os.path.basename(self.name)
        # RFC1952 says we must use ISO-8859-1 for the FNAME field.
        self.__write(self.name.encode("iso-8859-1", "replace") + NUL)

    def write(self, s):
        """Write string s to the stream.
        """
        if self.comptype == "gz":
            self.crc = self.zlib.crc32(s, self.crc)
        self.pos += len(s)
        if self.comptype != "tar":
            s = self.cmp.compress(s)
        self.__write(s)

    def __write(self, s):
        """Write string s to the stream if a whole new block
           is ready to be written.
        """
        self.buf += s
        while len(self.buf) > self.bufsize:
            self.fileobj.write(self.buf[:self.bufsize])
            self.buf = self.buf[self.bufsize:]

    def close(self):
        """Close the _Stream object. No operation should be
           done on it afterwards.
        """
        if self.closed:
            return

        self.closed = True
        try:
            if self.mode == "w" and self.comptype != "tar":
                self.buf += self.cmp.flush()

            if self.mode == "w" and self.buf:
                self.fileobj.write(self.buf)
                self.buf = b""
                if self.comptype == "gz":
                    self.fileobj.write(struct.pack("<L", self.crc))
                    self.fileobj.write(struct.pack("<L", self.pos & 0xffffFFFF))
        finally:
            if not self._extfileobj:
                self.fileobj.close()

    def _init_read_gz(self):
        """Initialize for reading a gzip compressed fileobj.
        """
        self.cmp = self.zlib.decompressobj(-self.zlib.MAX_WBITS)
        self.dbuf = b""

        # taken from gzip.GzipFile with some alterations
        if self.__read(2) != b"\037\213":
            raise ReadError("not a gzip file")
        if self.__read(1) != b"\010":
            raise CompressionError("unsupported compression method")

        flag = ord(self.__read(1))
        self.__read(6)

        if flag & 4:
            xlen = ord(self.__read(1)) + 256 * ord(self.__read(1))
            self.read(xlen)
        if flag & 8:
            while True:
                s = self.__read(1)
                if not s or s == NUL:
                    break
        if flag & 16:
            while True:
                s = self.__read(1)
                if not s or s == NUL:
                    break
        if flag & 2:
            self.__read(2)

    def tell(self):
        """Return the stream's file pointer position.
        """
        return self.pos

    def seek(self, pos=0):
        """Set the stream's file pointer to pos. Negative seeking
           is forbidden.
        """
        if pos - self.pos >= 0:
            blocks, remainder = divmod(pos - self.pos, self.bufsize)
            for i in range(blocks):
                self.read(self.bufsize)
            self.read(remainder)
        else:
            raise StreamError("seeking backwards is not allowed")
        return self.pos

    def read(self, size):
        """Return the next size number of bytes from the stream."""
        assert size is not None
        buf = self._read(size)
        self.pos += len(buf)
        return buf

    def _read(self, size):
        """Return size bytes from the stream.
        """
        if self.comptype == "tar":
            return self.__read(size)

        c = len(self.dbuf)
        t = [self.dbuf]
        while c < size:
            # Skip underlying buffer to avoid unaligned double buffering.
            if self.buf:
                buf = self.buf
                self.buf = b""
            else:
                buf = self.fileobj.read(self.bufsize)
                if not buf:
                    break
            try:
                buf = self.cmp.decompress(buf)
            except self.exception as e:
                raise ReadError("invalid compressed data") from e
            t.append(buf)
            c += len(buf)
        t = b"".join(t)
        self.dbuf = t[size:]
        return t[:size]

    def __read(self, size):
        """Return size bytes from stream. If internal buffer is empty,
           read another block from the stream.
        """
        c = len(self.buf)
        t = [self.buf]
        while c < size:
            buf = self.fileobj.read(self.bufsize)
            if not buf:
                break
            t.append(buf)
            c += len(buf)
        t = b"".join(t)
        self.buf = t[size:]
        return t[:size]
# class _Stream

class _StreamProxy(object):
    """Small proxy class that enables transparent compression
       detection for the Stream interface (mode 'r|*').
    """

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = self.fileobj.read(BLOCKSIZE)

    def read(self, size):
        self.read = self.fileobj.read
        return self.buf

    def getcomptype(self):
        if self.buf.startswith(b"\x1f\x8b\x08"):
            return "gz"
        elif self.buf[0:3] == b"BZh" and self.buf[4:10] == b"1AY&SY":
            return "bz2"
        elif self.buf.startswith((b"\x5d\x00\x00\x80", b"\xfd7zXZ")):
            return "xz"
        else:
            return "tar"

    def close(self):
        self.fileobj.close()
# class StreamProxy

#------------------------
# Extraction file object
#------------------------
class _FileInFile(object):
    """A thin wrapper around an existing file object that
       provides a part of its data as an individual file
       object.
    """

    def __init__(self, fileobj, offset, size, name, blockinfo=None):
        self.fileobj = fileobj
        self.offset = offset
        self.size = size
        self.position = 0
        self.name = name
        self.closed = False

        if blockinfo is None:
            blockinfo = [(0, size)]

        # Construct a map with data and zero blocks.
        self.map_index = 0
        self.map = []
        lastpos = 0
        realpos = self.offset
        for offset, size in blockinfo:
            if offset > lastpos:
                self.map.append((False, lastpos, offset, None))
            self.map.append((True, offset, offset + size, realpos))
            realpos += size
            lastpos = offset + size
        if lastpos < self.size:
            self.map.append((False, lastpos, self.size, None))

    def flush(self):
        pass

    @property
    def mode(self):
        return 'rb'

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return self.fileobj.seekable()

    def tell(self):
        """Return the current file position.
        """
        return self.position

    def seek(self, position, whence=io.SEEK_SET):
        """Seek to a position in the file.
        """
        if whence == io.SEEK_SET:
            self.position = min(max(position, 0), self.size)
        elif whence == io.SEEK_CUR:
            if position < 0:
                self.position = max(self.position + position, 0)
            else:
                self.position = min(self.position + position, self.size)
        elif whence == io.SEEK_END:
            self.position = max(min(self.size + position, self.size), 0)
        else:
            raise ValueError("Invalid argument")
        return self.position

    def read(self, size=None):
        """Read data from the file.
        """
        if size is None:
            size = self.size - self.position
        else:
            size = min(size, self.size - self.position)

        buf = b""
        while size > 0:
            while True:
                data, start, stop, offset = self.map[self.map_index]
                if start <= self.position < stop:
                    break
                else:
                    self.map_index += 1
                    if self.map_index == len(self.map):
                        self.map_index = 0
            length = min(size, stop - self.position)
            if data:
                self.fileobj.seek(offset + (self.position - start))
                b = self.fileobj.read(length)
                if len(b) != length:
                    raise ReadError("unexpected end of data")
                buf += b
            else:
                buf += NUL * length
            size -= length
            self.position += length
        return buf

    def readinto(self, b):
        buf = self.read(len(b))
        b[:len(buf)] = buf
        return len(buf)

    def close(self):
        self.closed = True
#class _FileInFile

class ExFileObject(io.BufferedReader):

    def __init__(self, tarfile, tarinfo):
        fileobj = _FileInFile(tarfile.fileobj, tarinfo.offset_data,
                tarinfo.size, tarinfo.name, tarinfo.sparse)
        super().__init__(fileobj)
#class ExFileObject


#-----------------------------
# extraction filters (PEP 706)
#-----------------------------

class FilterError(TarError):
    pass

class AbsolutePathError(FilterError):
    def __init__(self, tarinfo):
        self.tarinfo = tarinfo
        super().__init__(f'member {tarinfo.name!r} has an absolute path')

class OutsideDestinationError(FilterError):
    def __init__(self, tarinfo, path):
        self.tarinfo = tarinfo
        self._path = path
        super().__init__(f'{tarinfo.name!r} would be extracted to {path!r}, '
                         + 'which is outside the destination')

class SpecialFileError(FilterError):
    def __init__(self, tarinfo):
        self.tarinfo = tarinfo
        super().__init__(f'{tarinfo.name!r} is a special file')

class AbsoluteLinkError(FilterError):
    def __init__(self, tarinfo):
        self.tarinfo = tarinfo
        super().__init__(f'{tarinfo.name!r} is a link to an absolute path')

class LinkOutsideDestinationError(FilterError):
    def __init__(self, tarinfo, path):
        self.tarinfo = tarinfo
        self._path = path
        super().__init__(f'{tarinfo.name!r} would link to {path!r}, '
                         + 'which is outside the destination')

def _get_filtered_attrs(member, dest_path, for_data=True):
    new_attrs = {}
    name = member.name
    dest_path = os.path.realpath(dest_path)
    # Strip leading / (tar's directory separator) from filenames.
    # Include os.sep (target OS directory separator) as well.
    if name.startswith(('/', os.sep)):
        name = new_attrs['name'] = member.path.lstrip('/' + os.sep)
    if os.path.isabs(name):
        # Path is absolute even after stripping.
        # For example, 'C:/foo' on Windows.
        raise AbsolutePathError(member)
    # Ensure we stay in the destination
    target_path = os.path.realpath(os.path.join(dest_path, name))
    if os.path.commonpath([target_path, dest_path]) != dest_path:
        raise OutsideDestinationError(member, target_path)
    # Limit permissions (no high bits, and go-w)
    mode = member.mode
    if mode is not None:
        # Strip high bits & group/other write bits
        mode = mode & 0o755
        if for_data:
            # For data, handle permissions & file types
            if member.isreg() or member.islnk():
                if not mode & 0o100:
                    # Clear executable bits if not executable by user
                    mode &= ~0o111
                # Ensure owner can read & write
                mode |= 0o600
            elif member.isdir() or member.issym():
                # Ignore mode for directories & symlinks
                mode = None
            else:
                # Reject special files
                raise SpecialFileError(member)
        if mode != member.mode:
            new_attrs['mode'] = mode
    if for_data:
        # Ignore ownership for 'data'
        if member.uid is not None:
            new_attrs['uid'] = None
        if member.gid is not None:
            new_attrs['gid'] = None
        if member.uname is not None:
            new_attrs['uname'] = None
        if member.gname is not None:
            new_attrs['gname'] = None
        # Check link destination for 'data'
        if member.islnk() or member.issym():
            if os.path.isabs(member.linkname):
                raise AbsoluteLinkError(member)
            if member.issym():
                target_path = os.path.join(dest_path,
                                           os.path.dirname(name),
                                           member.linkname)
            else:
                target_path = os.path.join(dest_path,
                                           member.linkname)
            target_path = os.path.realpath(target_path)
            if os.path.commonpath([target_path, dest_path]) != dest_path:
                raise LinkOutsideDestinationError(member, target_path)
    return new_attrs

def fully_trusted_filter(member, dest_path):
    return member

def tar_filter(member, dest_path):
    new_attrs = _get_filtered_attrs(member, dest_path, False)
    if new_attrs:
        return member.replace(**new_attrs, deep=False)
    return member

def data_filter(member, dest_path):
    new_attrs = _get_filtered_attrs(member, dest_path, True)
    if new_attrs:
        return member.replace(**new_attrs, deep=False)
    return member

_NAMED_FILTERS = {
    "fully_trusted": fully_trusted_filter,
    "tar": tar_filter,
    "data": data_filter,
}

#------------------
# Exported Classes
#------------------

# Sentinel for replace() defaults, meaning "don't change the attribute"
_KEEP = object()

class TarInfo(object):
    """Informational class which holds the details about an
       archive member given by a tar header block.
       TarInfo objects are returned by TarFile.getmember(),
       TarFile.getmembers() and TarFile.gettarinfo() and are
       usually created internally.
    """

    __slots__ = dict(
        name = 'Name of the archive member.',
        mode = 'Permission bits.',
        uid = 'User ID of the user who originally stored this member.',
        gid = 'Group ID of the user who originally stored this member.',
        size = 'Size in bytes.',
        mtime = 'Time of last modification.',
        chksum = 'Header checksum.',
        type = ('File type. type is usually one of these constants: '
                'REGTYPE, AREGTYPE, LNKTYPE, SYMTYPE, DIRTYPE, FIFOTYPE, '
                'CONTTYPE, CHRTYPE, BLKTYPE, GNUTYPE_SPARSE.'),
        linkname = ('Name of the target file name, which is only present '
                    'in TarInfo objects of type LNKTYPE and SYMTYPE.'),
        uname = 'User name.',
        gname = 'Group name.',
        devmajor = 'Device major number.',
        devminor = 'Device minor number.',
        offset = 'The tar header starts here.',
        offset_data = "The file's data starts here.",
        pax_headers = ('A dictionary containing key-value pairs of an '
                       'associated pax extended header.'),
        sparse = 'Sparse member information.',
        _tarfile = None,
        _sparse_structs = None,
        _link_target = None,
        )

    def __init__(self, name=""):
        """Construct a TarInfo object. name is the optional name
           of the member.
        """
        self.name = name        # member name
        self.mode = 0o644       # file permissions
        self.uid = 0            # user id
        self.gid = 0            # group id
        self.size = 0           # file size
        self.mtime = 0          # modification time
        self.chksum = 0         # header checksum
        self.type = REGTYPE     # member type
        self.linkname = ""      # link name
        self.uname = ""         # user name
        self.gname = ""         # group name
        self.devmajor = 0       # device major number
        self.devminor = 0       # device minor number

        self.offset = 0         # the tar header starts here
        self.offset_data = 0    # the file's data starts here

        self.sparse = None      # sparse member information
        self.pax_headers = {}   # pax header information

    @property
    def tarfile(self):
        import warnings
        warnings.warn(
            'The undocumented "tarfile" attribute of TarInfo objects '
            + 'is deprecated and will be removed in Python 3.16',
            DeprecationWarning, stacklevel=2)
        return self._tarfile

    @tarfile.setter
    def tarfile(self, tarfile):
        import warnings
        warnings.warn(
            'The undocumented "tarfile" attribute of TarInfo objects '
            + 'is deprecated and will be removed in Python 3.16',
            DeprecationWarning, stacklevel=2)
        self._tarfile = tarfile

    @property
    def path(self):
        'In pax headers, "name" is called "path".'
        return self.name

    @path.setter
    def path(self, name):
        self.name = name

    @property
    def linkpath(self):
        'In pax headers, "linkname" is called "linkpath".'
        return self.linkname

    @linkpath.setter
    def linkpath(self, linkname):
        self.linkname = linkname

    def __repr__(self):
        return "<%s %r at %#x>" % (self.__class__.__name__,self.name,id(self))

    def replace(self, *,
                name=_KEEP, mtime=_KEEP, mode=_KEEP, linkname=_KEEP,
                uid=_KEEP, gid=_KEEP, uname=_KEEP, gname=_KEEP,
                deep=True, _KEEP=_KEEP):
        """Return a deep copy of self with the given attributes replaced.
        """
        if deep:
            result = copy.deepcopy(self)
        else:
            result = copy.copy(self)
        if name is not _KEEP:
            result.name = name
        if mtime is not _KEEP:
            result.mtime = mtime
        if mode is not _KEEP:
            result.mode = mode
        if linkname is not _KEEP:
            result.linkname = linkname
        if uid is not _KEEP:
            result.uid = uid
        if gid is not _KEEP:
            result.gid = gid
        if uname is not _KEEP:
            result.uname = uname
        if gname is not _KEEP:
            result.gname = gname
        return result

    def get_info(self):
        """Return the TarInfo's attributes as a dictionary.
        """
        if self.mode is None:
            mode = None
        else:
            mode = self.mode & 0o7777
        info = {
            "name":     self.name,
            "mode":     mode,
            "uid":      self.uid,
            "gid":      self.gid,
            "size":     self.size,
            "mtime":    self.mtime,
            "chksum":   self.chksum,
            "type":     self.type,
            "linkname": self.linkname,
            "uname":    self.uname,
            "gname":    self.gname,
            "devmajor": self.devmajor,
            "devminor": self.devminor
        }

        if info["type"] == DIRTYPE and not info["name"].endswith("/"):
            info["name"] += "/"

        return info

    def tobuf(self, format=DEFAULT_FORMAT, encoding=ENCODING, errors="surrogateescape"):
        """Return a tar header as a string of 512 byte blocks.
        """
        info = self.get_info()
        for name, value in info.items():
            if value is None:
                raise ValueError("%s may not be None" % name)

        if format == USTAR_FORMAT:
            return self.create_ustar_header(info, encoding, errors)
        elif format == GNU_FORMAT:
            return self.create_gnu_header(info, encoding, errors)
        elif format == PAX_FORMAT:
            return self.create_pax_header(info, encoding)
        else:
            raise ValueError("invalid format")

    def create_ustar_header(self, info, encoding, errors):
        """Return the object as a ustar header block.
        """
        info["magic"] = POSIX_MAGIC

        if len(info["linkname"].encode(encoding, errors)) > LENGTH_LINK:
            raise ValueError("linkname is too long")

        if len(info["name"].encode(encoding, errors)) > LENGTH_NAME:
            info["prefix"], info["name"] = self._posix_split_name(info["name"], encoding, errors)

        return self._create_header(info, USTAR_FORMAT, encoding, errors)

    def create_gnu_header(self, info, encoding, errors):
        """Return the object as a GNU header block sequence.
        """
        info["magic"] = GNU_MAGIC

        buf = b""
        if len(info["linkname"].encode(encoding, errors)) > LENGTH_LINK:
            buf += self._create_gnu_long_header(info["linkname"], GNUTYPE_LONGLINK, encoding, errors)

        if len(info["name"].encode(encoding, errors)) > LENGTH_NAME:
            buf += self._create_gnu_long_header(info["name"], GNUTYPE_LONGNAME, encoding, errors)

        return buf + self._create_header(info, GNU_FORMAT, encoding, errors)

    def create_pax_header(self, info, encoding):
        """Return the object as a ustar header block. If it cannot be
           represented this way, prepend a pax extended header sequence
           with supplement information.
        """
        info["magic"] = POSIX_MAGIC
        pax_headers = self.pax_headers.copy()

        # Test string fields for values that exceed the field length or cannot
        # be represented in ASCII encoding.
        for name, hname, length in (
                ("name", "path", LENGTH_NAME), ("linkname", "linkpath", LENGTH_LINK),
                ("uname", "uname", 32), ("gname", "gname", 32)):

            if hname in pax_headers:
                # The pax header has priority.
                continue

            # Try to encode the string as ASCII.
            try:
                info[name].encode("ascii", "strict")
            except UnicodeEncodeError:
                pax_headers[hname] = info[name]
                continue

            if len(info[name]) > length:
                pax_headers[hname] = info[name]

        # Test number fields for values that exceed the field limit or values
        # that like to be stored as float.
        for name, digits in (("uid", 8), ("gid", 8), ("size", 12), ("mtime", 12)):
            needs_pax = False

            val = info[name]
            val_is_float = isinstance(val, float)
            val_int = round(val) if val_is_float else val
            if not 0 <= val_int < 8 ** (digits - 1):
                # Avoid overflow.
                info[name] = 0
                needs_pax = True
            elif val_is_float:
                # Put rounded value in ustar header, and full
                # precision value in pax header.
                info[name] = val_int
                needs_pax = True

            # The existing pax header has priority.
            if needs_pax and name not in pax_headers:
                pax_headers[name] = str(val)

        # Create a pax extended header if necessary.
        if pax_headers:
            buf = self._create_pax_generic_header(pax_headers, XHDTYPE, encoding)
        else:
            buf = b""

        return buf + self._create_header(info, USTAR_FORMAT, "ascii", "replace")

    @classmethod
    def create_pax_global_header(cls, pax_headers):
        """Return the object as a pax global header block sequence.
        """
        return cls._create_pax_generic_header(pax_headers, XGLTYPE, "utf-8")

    def _posix_split_name(self, name, encoding, errors):
        """Split a name longer than 100 chars into a prefix
           and a name part.
        """
        components = name.split("/")
        for i in range(1, len(components)):
            prefix = "/".join(components[:i])
            name = "/".join(components[i:])
            if len(prefix.encode(encoding, errors)) <= LENGTH_PREFIX and \
                    len(name.encode(encoding, errors)) <= LENGTH_NAME:
                break
        else:
            raise ValueError("name is too long")

        return prefix, name

    @staticmethod
    def _create_header(info, format, encoding, errors):
        """Return a header block. info is a dictionary with file
           information, format must be one of the *_FORMAT constants.
        """
        has_device_fields = info.get("type") in (CHRTYPE, BLKTYPE)
        if has_device_fields:
            devmajor = itn(info.get("devmajor", 0), 8, format)
            devminor = itn(info.get("devminor", 0), 8, format)
        else:
            devmajor = stn("", 8, encoding, errors)
            devminor = stn("", 8, encoding, errors)

        # None values in metadata should cause ValueError.
        # itn()/stn() do this for all fields except type.
        filetype = info.get("type", REGTYPE)
        if filetype is None:
            raise ValueError("TarInfo.type must not be None")

        parts = [
            stn(info.get("name", ""), 100, encoding, errors),
            itn(info.get("mode", 0) & 0o7777, 8, format),
            itn(info.get("uid", 0), 8, format),
            itn(info.get("gid", 0), 8, format),
            itn(info.get("size", 0), 12, format),
            itn(info.get("mtime", 0), 12, format),
            b"        ", # checksum field
            filetype,
            stn(info.get("linkname", ""), 100, encoding, errors),
            info.get("magic", POSIX_MAGIC),
            stn(info.get("uname", ""), 32, encoding, errors),
            stn(info.get("gname", ""), 32, encoding, errors),
            devmajor,
            devminor,
            stn(info.get("prefix", ""), 155, encoding, errors)
        ]

        buf = struct.pack("%ds" % BLOCKSIZE, b"".join(parts))
        chksum = calc_chksums(buf[-BLOCKSIZE:])[0]
        buf = buf[:-364] + bytes("%06o\0" % chksum, "ascii") + buf[-357:]
        return buf

    @staticmethod
    def _create_payload(payload):
        """Return the string payload filled with zero bytes
           up to the next 512 byte border.
        """
        blocks, remainder = divmod(len(payload), BLOCKSIZE)
        if remainder > 0:
            payload += (BLOCKSIZE - remainder) * NUL
        return payload

    @classmethod
    def _create_gnu_long_header(cls, name, type, encoding, errors):
        """Return a GNUTYPE_LONGNAME or GNUTYPE_LONGLINK sequence
           for name.
        """
        name = name.encode(encoding, errors) + NUL

        info = {}
        info["name"] = "././@LongLink"
        info["type"] = type
        info["size"] = len(name)
        info["magic"] = GNU_MAGIC

        # create extended header + name blocks.
        return cls._create_header(info, USTAR_FORMAT, encoding, errors) + \
                cls._create_payload(name)

    @classmethod
    def _create_pax_generic_header(cls, pax_headers, type, encoding):
        """Return a POSIX.1-2008 extended or global header sequence
           that contains a list of keyword, value pairs. The values
           must be strings.
        """
        # Check if one of the fields contains surrogate characters and thereby
        # forces hdrcharset=BINARY, see _proc_pax() for more information.
        binary = False
        for keyword, value in pax_headers.items():
            try:
                value.encode("utf-8", "strict")
            except UnicodeEncodeError:
                binary = True
                break

        records = b""
        if binary:
            # Put the hdrcharset field at the beginning of the header.
            records += b"21 hdrcharset=BINARY\n"

        for keyword, value in pax_headers.items():
            keyword = keyword.encode("utf-8")
            if binary:
                # Try to restore the original byte representation of 'value'.
                # Needless to say, that the encoding must match the string.
                value = value.encode(encoding, "surrogateescape")
            else:
                value = value.encode("utf-8")

            l = len(keyword) + len(value) + 3   # ' ' + '=' + '\n'
            n = p = 0
            while True:
                n = l + len(str(p))
                if n == p:
                    break
                p = n
            records += bytes(str(p), "ascii") + b" " + keyword + b"=" + value + b"\n"

        # We use a hardcoded "././@PaxHeader" name like star does
        # instead of the one that POSIX recommends.
        info = {}
        info["name"] = "././@PaxHeader"
        info["type"] = type
        info["size"] = len(records)
        info["magic"] = POSIX_MAGIC

        # Create pax header + record blocks.
        return cls._create_header(info, USTAR_FORMAT, "ascii", "replace") + \
                cls._create_payload(records)

    @classmethod
    def frombuf(cls, buf, encoding, errors):
        """Construct a TarInfo object from a 512 byte bytes object.
        """
        if len(buf) == 0:
            raise EmptyHeaderError("empty header")
        if len(buf) != BLOCKSIZE:
            raise TruncatedHeaderError("truncated header")
        if buf.count(NUL) == BLOCKSIZE:
            raise EOFHeaderError("end of file header")

        chksum = nti(buf[148:156])
        if chksum not in calc_chksums(buf):
            raise InvalidHeaderError("bad checksum")

        obj = cls()
        obj.name = nts(buf[0:100], encoding, errors)
        obj.mode = nti(buf[100:108])
        obj.uid = nti(buf[108:116])
        obj.gid = nti(buf[116:124])
        obj.size = nti(buf[124:136])
        obj.mtime = nti(buf[136:148])
        obj.chksum = chksum
        obj.type = buf[156:157]
        obj.linkname = nts(buf[157:257], encoding, errors)
        obj.uname = nts(buf[265:297], encoding, errors)
        obj.gname = nts(buf[297:329], encoding, errors)
        obj.devmajor = nti(buf[329:337])
        obj.devminor = nti(buf[337:345])
        prefix = nts(buf[345:500], encoding, errors)

        # Old V7 tar format represents a directory as a regular
        # file with a trailing slash.
        if obj.type == AREGTYPE and obj.name.endswith("/"):
            obj.type = DIRTYPE

        # The old GNU sparse format occupies some of the unused
        # space in the buffer for up to 4 sparse structures.
        # Save them for later processing in _proc_sparse().
        if obj.type == GNUTYPE_SPARSE:
            pos = 386
            structs = []
            for i in range(4):
                try:
                    offset = nti(buf[pos:pos + 12])
                    numbytes = nti(buf[pos + 12:pos + 24])
                except ValueError:
                    break
                structs.append((offset, numbytes))
                pos += 24
            isextended = bool(buf[482])
            origsize = nti(buf[483:495])
            obj._sparse_structs = (structs, isextended, origsize)

        # Remove redundant slashes from directories.
        if obj.isdir():
            obj.name = obj.name.rstrip("/")

        # Reconstruct a ustar longname.
        if prefix and obj.type not in GNU_TYPES:
            obj.name = prefix + "/" + obj.name
        return obj

    @classmethod
    def fromtarfile(cls, tarfile):
        """Return the next TarInfo object from TarFile object
           tarfile.
        """
        buf = tarfile.fileobj.read(BLOCKSIZE)
        obj = cls.frombuf(buf, tarfile.encoding, tarfile.errors)
        obj.offset = tarfile.fileobj.tell() - BLOCKSIZE
        return obj._proc_member(tarfile)

    #--------------------------------------------------------------------------
    # The following are methods that are called depending on the type of a
    # member. The entry point is _proc_member() which can be overridden in a
    # subclass to add custom _proc_*() methods. A _proc_*() method MUST
    # implement the following
    # operations:
    # 1. Set self.offset_data to the position where the data blocks begin,
    #    if there is data that follows.
    # 2. Set tarfile.offset to the position where the next member's header will
    #    begin.
    # 3. Return self or another valid TarInfo object.
    def _proc_member(self, tarfile):
        """Choose the right processing method depending on
           the type and call it.
        """
        if self.type in (GNUTYPE_LONGNAME, GNUTYPE_LONGLINK):
            return self._proc_gnulong(tarfile)
        elif self.type == GNUTYPE_SPARSE:
            return self._proc_sparse(tarfile)
        elif self.type in (XHDTYPE, XGLTYPE, SOLARIS_XHDTYPE):
            return self._proc_pax(tarfile)
        else:
            return self._proc_builtin(tarfile)

    def _proc_builtin(self, tarfile):
        """Process a builtin type or an unknown type which
           will be treated as a regular file.
        """
        self.offset_data = tarfile.fileobj.tell()
        offset = self.offset_data
        if self.isreg() or self.type not in SUPPORTED_TYPES:
            # Skip the following data blocks.
            offset += self._block(self.size)
        tarfile.offset = offset

        # Patch the TarInfo object with saved global
        # header information.
        self._apply_pax_info(tarfile.pax_headers, tarfile.encoding, tarfile.errors)

        # Remove redundant slashes from directories. This is to be consistent
        # with frombuf().
        if self.isdir():
            self.name = self.name.rstrip("/")

        return self

    def _proc_gnulong(self, tarfile):
        """Process the blocks that hold a GNU longname
           or longlink member.
        """
        buf = tarfile.fileobj.read(self._block(self.size))

        # Fetch the next header and process it.
        try:
            next = self.fromtarfile(tarfile)
        except HeaderError as e:
            raise SubsequentHeaderError(str(e)) from None

        # Patch the TarInfo object from the next header with
        # the longname information.
        next.offset = self.offset
        if self.type == GNUTYPE_LONGNAME:
            next.name = nts(buf, tarfile.encoding, tarfile.errors)
        elif self.type == GNUTYPE_LONGLINK:
            next.linkname = nts(buf, tarfile.encoding, tarfile.errors)

        # Remove redundant slashes from directories. This is to be consistent
        # with frombuf().
        if next.isdir():
            next.name = removesuffix(next.name, "/")

        return next

    def _proc_sparse(self, tarfile):
        """Process a GNU sparse header plus extra headers.
        """
        # We already collected some sparse structures in frombuf().
        structs, isextended, origsize = self._sparse_structs
        del self._sparse_structs

        # Collect sparse structures from extended header blocks.
        while isextended:
            buf = tarfile.fileobj.read(BLOCKSIZE)
            pos = 0
            for i in range(21):
                try:
                    offset = nti(buf[pos:pos + 12])
                    numbytes = nti(buf[pos + 12:pos + 24])
                except ValueError:
                    break
                if offset and numbytes:
                    structs.append((offset, numbytes))
                pos += 24
            isextended = bool(buf[504])
        self.sparse = structs

        self.offset_data = tarfile.fileobj.tell()
        tarfile.offset = self.offset_data + self._block(self.size)
        self.size = origsize
        return self

    def _proc_pax(self, tarfile):
        """Process an extended or global header as described in
           POSIX.1-2008.
        """
        # Read the header information.
        buf = tarfile.fileobj.read(self._block(self.size))

        # A pax header stores supplemental information for either
        # the following file (extended) or all following files
        # (global).
        if self.type == XGLTYPE:
            pax_headers = tarfile.pax_headers
        else:
            pax_headers = tarfile.pax_headers.copy()

        # Check if the pax header contains a hdrcharset field. This tells us
        # the encoding of the path, linkpath, uname and gname fields. Normally,
        # these fields are UTF-8 encoded but since POSIX.1-2008 tar
        # implementations are allowed to store them as raw binary strings if
        # the translation to UTF-8 fails.
        match = re.search(br"\d+ hdrcharset=([^\n]+)\n", buf)
        if match is not None:
            pax_headers["hdrcharset"] = match.group(1).decode("utf-8")

        # For the time being, we don't care about anything other than "BINARY".
        # The only other value that is currently allowed by the standard is
        # "ISO-IR 10646 2000 UTF-8" in other words UTF-8.
        hdrcharset = pax_headers.get("hdrcharset")
        if hdrcharset == "BINARY":
            encoding = tarfile.encoding
        else:
            encoding = "utf-8"

        # Parse pax header information. A record looks like that:
        # "%d %s=%s\n" % (length, keyword, value). length is the size
        # of the complete record including the length field itself and
        # the newline. keyword and value are both UTF-8 encoded strings.
        regex = re.compile(br"(\d+) ([^=]+)=")
        pos = 0
        while match := regex.match(buf, pos):
            length, keyword = match.groups()
            length = int(length)
            if length == 0:
                raise InvalidHeaderError("invalid header")
            value = buf[match.end(2) + 1:match.start(1) + length - 1]

            # Normally, we could just use "utf-8" as the encoding and "strict"
            # as the error handler, but we better not take the risk. For
            # example, GNU tar <= 1.23 is known to store filenames it cannot
            # translate to UTF-8 as raw strings (unfortunately without a
            # hdrcharset=BINARY header).
            # We first try the strict standard encoding, and if that fails we
            # fall back on the user's encoding and error handler.
            keyword = self._decode_pax_field(keyword, "utf-8", "utf-8",
                    tarfile.errors)
            if keyword in PAX_NAME_FIELDS:
                value = self._decode_pax_field(value, encoding, tarfile.encoding,
                        tarfile.errors)
            else:
                value = self._decode_pax_field(value, "utf-8", "utf-8",
                        tarfile.errors)

            pax_headers[keyword] = value
            pos += length

        # Fetch the next header.
        try:
            next = self.fromtarfile(tarfile)
        except HeaderError as e:
            raise SubsequentHeaderError(str(e)) from None

        # Process GNU sparse information.
        if "GNU.sparse.map" in pax_headers:
            # GNU extended sparse format version 0.1.
            self._proc_gnusparse_01(next, pax_headers)

        elif "GNU.sparse.size" in pax_headers:
            # GNU extended sparse format version 0.0.
            self._proc_gnusparse_00(next, pax_headers, buf)

        elif pax_headers.get("GNU.sparse.major") == "1" and pax_headers.get("GNU.sparse.minor") == "0":
            # GNU extended sparse format version 1.0.
            self._proc_gnusparse_10(next, pax_headers, tarfile)

        if self.type in (XHDTYPE, SOLARIS_XHDTYPE):
            # Patch the TarInfo object with the extended header info.
            next._apply_pax_info(pax_headers, tarfile.encoding, tarfile.errors)
            next.offset = self.offset

            if "size" in pax_headers:
                # If the extended header replaces the size field,
                # we need to recalculate the offset where the next
                # header starts.
                offset = next.offset_data
                if next.isreg() or next.type not in SUPPORTED_TYPES:
                    offset += next._block(next.size)
                tarfile.offset = offset

        return next

    def _proc_gnusparse_00(self, next, pax_headers, buf):
        """Process a GNU tar extended sparse header, version 0.0.
        """
        offsets = []
        for match in re.finditer(br"\d+ GNU.sparse.offset=(\d+)\n", buf):
            offsets.append(int(match.group(1)))
        numbytes = []
        for match in re.finditer(br"\d+ GNU.sparse.numbytes=(\d+)\n", buf):
            numbytes.append(int(match.group(1)))
        next.sparse = list(zip(offsets, numbytes))

    def _proc_gnusparse_01(self, next, pax_headers):
        """Process a GNU tar extended sparse header, version 0.1.
        """
        sparse = [int(x) for x in pax_headers["GNU.sparse.map"].split(",")]
        next.sparse = list(zip(sparse[::2], sparse[1::2]))

    def _proc_gnusparse_10(self, next, pax_headers, tarfile):
        """Process a GNU tar extended sparse header, version 1.0.
        """
        fields = None
        sparse = []
        buf = tarfile.fileobj.read(BLOCKSIZE)
        fields, buf = buf.split(b"\n", 1)
        fields = int(fields)
        while len(sparse) < fields * 2:
            if b"\n" not in buf:
                buf += tarfile.fileobj.read(BLOCKSIZE)
            number, buf = buf.split(b"\n", 1)
            sparse.append(int(number))
        next.offset_data = tarfile.fileobj.tell()
        next.sparse = list(zip(sparse[::2], sparse[1::2]))

    def _apply_pax_info(self, pax_headers, encoding, errors):
        """Replace fields with supplemental information from a previous
           pax extended or global header.
        """
        for keyword, value in pax_headers.items():
            if keyword == "GNU.sparse.name":
                setattr(self, "path", value)
            elif keyword == "GNU.sparse.size":
                setattr(self, "size", int(value))
            elif keyword == "GNU.sparse.realsize":
                setattr(self, "size", int(value))
            elif keyword in PAX_FIELDS:
                if keyword in PAX_NUMBER_FIELDS:
                    try:
                        value = PAX_NUMBER_FIELDS[keyword](value)
                    except ValueError:
                        value = 0
                if keyword == "path":
                    value = value.rstrip("/")
                setattr(self, keyword, value)

        self.pax_headers = pax_headers.copy()

    def _decode_pax_field(self, value, encoding, fallback_encoding, fallback_errors):
        """Decode a single field from a pax record.
        """
        try:
            return value.decode(encoding, "strict")
        except UnicodeDecodeError:
            return value.decode(fallback_encoding, fallback_errors)

    def _block(self, count):
        """Round up a byte count by BLOCKSIZE and return it,
           e.g. _block(834) => 1024.
        """
        blocks, remainder = divmod(count, BLOCKSIZE)
        if remainder:
            blocks += 1
        return blocks * BLOCKSIZE

    def isreg(self):
        'Return True if the Tarinfo object is a regular file.'
        return self.type in REGULAR_TYPES

    def isfile(self):
        'Return True if the Tarinfo object is a regular file.'
        return self.isreg()

    def isdir(self):
        'Return True if it is a directory.'
        return self.type == DIRTYPE

    def issym(self):
        'Return True if it is a symbolic link.'
        return self.type == SYMTYPE

    def islnk(self):
        'Return True if it is a hard link.'
        return self.type == LNKTYPE

    def ischr(self):
        'Return True if it is a character device.'
        return self.type == CHRTYPE

    def isblk(self):
        'Return True if it is a block device.'
        return self.type == BLKTYPE

    def isfifo(self):
        'Return True if it is a FIFO.'
        return self.type == FIFOTYPE

    def issparse(self):
        return self.sparse is not None

    def isdev(self):
        'Return True if it is one of character device, block device or FIFO.'
        return self.type in (CHRTYPE, BLKTYPE, FIFOTYPE)
# class TarInfo

class TarFile(object):
    """The TarFile Class provides an interface to tar archives.
    """

    debug = 0                   # May be set from 0 (no msgs) to 3 (all msgs)

    dereference = False         # If true, add content of linked file to the
                                # tar file, else the link.

    ignore_zeros = False        # If true, skips empty or invalid blocks and
                                # continues processing.

    errorlevel = 1              # If 0, fatal errors only appear in debug
                                # messages (if debug >= 0). If > 0, errors
                                # are passed to the caller as exceptions.

    format = DEFAULT_FORMAT     # The format to use when creating an archive.

    encoding = ENCODING         # Encoding for 8-bit character strings.

    errors = None               # Error handler for unicode conversion.

    tarinfo = TarInfo           # The default TarInfo class to use.

    fileobject = ExFileObject   # The file-object for extractfile().

    extraction_filter = None    # The default filter for extraction.

    def __init__(self, name=None, mode="r", fileobj=None, format=None,
            tarinfo=None, dereference=None, ignore_zeros=None, encoding=None,
            errors="surrogateescape", pax_headers=None, debug=None,
            errorlevel=None, copybufsize=None, stream=False):
        """Open an (uncompressed) tar archive 'name'. 'mode' is either 'r' to
           read from an existing archive, 'a' to append data to an existing
           file or 'w' to create a new file overwriting an existing one. 'mode'
           defaults to 'r'.
           If 'fileobj' is given, it is used for reading or writing data. If it
           can be determined, 'mode' is overridden by 'fileobj's mode.
           'fileobj' is not closed, when TarFile is closed.
        """
        modes = {"r": "rb", "a": "r+b", "w": "wb", "x": "xb"}
        if mode not in modes:
            raise ValueError("mode must be 'r', 'a', 'w' or 'x'")
        self.mode = mode
        self._mode = modes[mode]

        if not fileobj:
            if self.mode == "a" and not os.path.exists(name):
                # Create nonexistent files in append mode.
                self.mode = "w"
                self._mode = "wb"
            fileobj = bltn_open(name, self._mode)
            self._extfileobj = False
        else:
            if (name is None and hasattr(fileobj, "name") and
                isinstance(fileobj.name, (str, bytes))):
                name = fileobj.name
            if hasattr(fileobj, "mode"):
                self._mode = fileobj.mode
            self._extfileobj = True
        self.name = os.path.abspath(name) if name else None
        self.fileobj = fileobj

        self.stream = stream

        # Init attributes.
        if format is not None:
            self.format = format
        if tarinfo is not None:
            self.tarinfo = tarinfo
        if dereference is not None:
            self.dereference = dereference
        if ignore_zeros is not None:
            self.ignore_zeros = ignore_zeros
        if encoding is not None:
            self.encoding = encoding
        self.errors = errors

        if pax_headers is not None and self.format == PAX_FORMAT:
            self.pax_headers = pax_headers
        else:
            self.pax_headers = {}

        if debug is not None:
            self.debug = debug
        if errorlevel is not None:
            self.errorlevel = errorlevel

        # Init datastructures.
        self.copybufsize = copybufsize
        self.closed = False
        self.members = []       # list of members as TarInfo objects
        self._loaded = False    # flag if all members have been read
        self.offset = self.fileobj.tell()
                                # current position in the archive file
        self.inodes = {}        # dictionary caching the inodes of
                                # archive members already added

        try:
            if self.mode == "r":
                self.firstmember = None
                self.firstmember = self.next()

            if self.mode == "a":
                # Move to the end of the archive,
                # before the first empty block.
                while True:
                    self.fileobj.seek(self.offset)
                    try:
                        tarinfo = self.tarinfo.fromtarfile(self)
                        self.members.append(tarinfo)
                    except EOFHeaderError:
                        self.fileobj.seek(self.offset)
                        break
                    except HeaderError as e:
                        raise ReadError(str(e)) from None

            if self.mode in ("a", "w", "x"):
                self._loaded = True

                if self.pax_headers:
                    buf = self.tarinfo.create_pax_global_header(self.pax_headers.copy())
                    self.fileobj.write(buf)
                    self.offset += len(buf)
        except:
            if not self._extfileobj:
                self.fileobj.close()
            self.closed = True
            raise

    #--------------------------------------------------------------------------
    # Below are the classmethods which act as alternate constructors to the
    # TarFile class. The open() method is the only one that is needed for
    # public use; it is the "super"-constructor and is able to select an
    # adequate "sub"-constructor for a particular compression using the mapping
    # from OPEN_METH.
    #
    # This concept allows one to subclass TarFile without losing the comfort of
    # the super-constructor. A sub-constructor is registered and made available
    # by adding it to the mapping in OPEN_METH.

    @classmethod
    def open(cls, name=None, mode="r", fileobj=None, bufsize=RECORDSIZE, **kwargs):
        r"""Open a tar archive for reading, writing or appending. Return
           an appropriate TarFile class.

           mode:
           'r' or 'r:\*' open for reading with transparent compression
           'r:'         open for reading exclusively uncompressed
           'r:gz'       open for reading with gzip compression
           'r:bz2'      open for reading with bzip2 compression
           'r:xz'       open for reading with lzma compression
           'a' or 'a:'  open for appending, creating the file if necessary
           'w' or 'w:'  open for writing without compression
           'w:gz'       open for writing with gzip compression
           'w:bz2'      open for writing with bzip2 compression
           'w:xz'       open for writing with lzma compression

           'x' or 'x:'  create a tarfile exclusively without compression, raise
                        an exception if the file is already created
           'x:gz'       create a gzip compressed tarfile, raise an exception
                        if the file is already created
           'x:bz2'      create a bzip2 compressed tarfile, raise an exception
                        if the file is already created
           'x:xz'       create an lzma compressed tarfile, raise an exception
                        if the file is already created

           'r|\*'        open a stream of tar blocks with transparent compression
           'r|'         open an uncompressed stream of tar blocks for reading
           'r|gz'       open a gzip compressed stream of tar blocks
           'r|bz2'      open a bzip2 compressed stream of tar blocks
           'r|xz'       open an lzma compressed stream of tar blocks
           'w|'         open an uncompressed stream for writing
           'w|gz'       open a gzip compressed stream for writing
           'w|bz2'      open a bzip2 compressed stream for writing
           'w|xz'       open an lzma compressed stream for writing
        """

        if not name and not fileobj:
            raise ValueError("nothing to open")

        if mode in ("r", "r:*"):
            # Find out which *open() is appropriate for opening the file.
            def not_compressed(comptype):
                return cls.OPEN_METH[comptype] == 'taropen'
            error_msgs = []
            for comptype in sorted(cls.OPEN_METH, key=not_compressed):
                func = getattr(cls, cls.OPEN_METH[comptype])
                if fileobj is not None:
                    saved_pos = fileobj.tell()
                try:
                    return func(name, "r", fileobj, **kwargs)
                except (ReadError, CompressionError) as e:
                    error_msgs.append(f'- method {comptype}: {e!r}')
                    if fileobj is not None:
                        fileobj.seek(saved_pos)
                    continue
            error_msgs_summary = '\n'.join(error_msgs)
            raise ReadError(f"file could not be opened successfully:\n{error_msgs_summary}")

        elif ":" in mode:
            filemode, comptype = mode.split(":", 1)
            filemode = filemode or "r"
            comptype = comptype or "tar"

            # Select the *open() function according to
            # given compression.
            if comptype in cls.OPEN_METH:
                func = getattr(cls, cls.OPEN_METH[comptype])
            else:
                raise CompressionError("unknown compression type %r" % comptype)
            return func(name, filemode, fileobj, **kwargs)

        elif "|" in mode:
            filemode, comptype = mode.split("|", 1)
            filemode = filemode or "r"
            comptype = comptype or "tar"

            if filemode not in ("r", "w"):
                raise ValueError("mode must be 'r' or 'w'")

            compresslevel = kwargs.pop("compresslevel", 9)
            stream = _Stream(name, filemode, comptype, fileobj, bufsize,
                             compresslevel)
            try:
                t = cls(name, filemode, stream, **kwargs)
            except:
                stream.close()
                raise
            t._extfileobj = False
            return t

        elif mode in ("a", "w", "x"):
            return cls.taropen(name, mode, fileobj, **kwargs)

        raise ValueError("undiscernible mode")

    @classmethod
    def taropen(cls, name, mode="r", fileobj=None, **kwargs):
        """Open uncompressed tar archive name for reading or writing.
        """
        if mode not in ("r", "a", "w", "x"):
            raise ValueError("mode must be 'r', 'a', 'w' or 'x'")
        return cls(name, mode, fileobj, **kwargs)

    @classmethod
    def gzopen(cls, name, mode="r", fileobj=None, compresslevel=9, **kwargs):
        """Open gzip compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        if mode not in ("r", "w", "x"):
            raise ValueError("mode must be 'r', 'w' or 'x'")

        try:
            from gzip import GzipFile
        except ImportError:
            raise CompressionError("gzip module is not available") from None

        try:
            fileobj = GzipFile(name, mode + "b", compresslevel, fileobj)
        except OSError as e:
            if fileobj is not None and mode == 'r':
                raise ReadError("not a gzip file") from e
            raise

        try:
            t = cls.taropen(name, mode, fileobj, **kwargs)
        except OSError as e:
            fileobj.close()
            if mode == 'r':
                raise ReadError("not a gzip file") from e
            raise
        except:
            fileobj.close()
            raise
        t._extfileobj = False
        return t

    @classmethod
    def bz2open(cls, name, mode="r", fileobj=None, compresslevel=9, **kwargs):
        """Open bzip2 compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        if mode not in ("r", "w", "x"):
            raise ValueError("mode must be 'r', 'w' or 'x'")

        try:
            from bz2 import BZ2File
        except ImportError:
            raise CompressionError("bz2 module is not available") from None

        fileobj = BZ2File(fileobj or name, mode, compresslevel=compresslevel)

        try:
            t = cls.taropen(name, mode, fileobj, **kwargs)
        except (OSError, EOFError) as e:
            fileobj.close()
            if mode == 'r':
                raise ReadError("not a bzip2 file") from e
            raise
        except:
            fileobj.close()
            raise
        t._extfileobj = False
        return t

    @classmethod
    def xzopen(cls, name, mode="r", fileobj=None, preset=None, **kwargs):
        """Open lzma compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        if mode not in ("r", "w", "x"):
            raise ValueError("mode must be 'r', 'w' or 'x'")

        try:
            from lzma import LZMAFile, LZMAError
        except ImportError:
            raise CompressionError("lzma module is not available") from None

        fileobj = LZMAFile(fileobj or name, mode, preset=preset)

        try:
            t = cls.taropen(name, mode, fileobj, **kwargs)
        except (LZMAError, EOFError) as e:
            fileobj.close()
            if mode == 'r':
                raise ReadError("not an lzma file") from e
            raise
        except:
            fileobj.close()
            raise
        t._extfileobj = False
        return t

    # All *open() methods are registered here.
    OPEN_METH = {
        "tar": "taropen",   # uncompressed tar
        "gz":  "gzopen",    # gzip compressed tar
        "bz2": "bz2open",   # bzip2 compressed tar
        "xz":  "xzopen"     # lzma compressed tar
    }

    #--------------------------------------------------------------------------
    # The public methods which TarFile provides:

    def close(self):
        """Close the TarFile. In write-mode, two finishing zero blocks are
           appended to the archive.
        """
        if self.closed:
            return

        self.closed = True
        try:
            if self.mode in ("a", "w", "x"):
                self.fileobj.write(NUL * (BLOCKSIZE * 2))
                self.offset += (BLOCKSIZE * 2)
                # fill up the end with zero-blocks
                # (like option -b20 for tar does)
                blocks, remainder = divmod(self.offset, RECORDSIZE)
                if remainder > 0:
                    self.fileobj.write(NUL * (RECORDSIZE - remainder))
        finally:
            if not self._extfileobj:
                self.fileobj.close()

    def getmember(self, name):
        """Return a TarInfo object for member 'name'. If 'name' can not be
           found in the archive, KeyError is raised. If a member occurs more
           than once in the archive, its last occurrence is assumed to be the
           most up-to-date version.
        """
        tarinfo = self._getmember(name.rstrip('/'))
        if tarinfo is None:
            raise KeyError("filename %r not found" % name)
        return tarinfo

    def getmembers(self):
        """Return the members of the archive as a list of TarInfo objects. The
           list has the same order as the members in the archive.
        """
        self._check()
        if not self._loaded:    # if we want to obtain a list of
            self._load()        # all members, we first have to
                                # scan the whole archive.
        return self.members

    def getnames(self):
        """Return the members of the archive as a list of their names. It has
           the same order as the list returned by getmembers().
        """
        return [tarinfo.name for tarinfo in self.getmembers()]

    def gettarinfo(self, name=None, arcname=None, fileobj=None):
        """Create a TarInfo object from the result of os.stat or equivalent
           on an existing file. The file is either named by 'name', or
           specified as a file object 'fileobj' with a file descriptor. If
           given, 'arcname' specifies an alternative name for the file in the
           archive, otherwise, the name is taken from the 'name' attribute of
           'fileobj', or the 'name' argument. The name should be a text
           string.
        """
        self._check("awx")

        # When fileobj is given, replace name by
        # fileobj's real name.
        if fileobj is not None:
            name = fileobj.name

        # Building the name of the member in the archive.
        # Backward slashes are converted to forward slashes,
        # Absolute paths are turned to relative paths.
        if arcname is None:
            arcname = name
        drv, arcname = os.path.splitdrive(arcname)
        arcname = arcname.replace(os.sep, "/")
        arcname = arcname.lstrip("/")

        # Now, fill the TarInfo object with
        # information specific for the file.
        tarinfo = self.tarinfo()
        tarinfo._tarfile = self  # To be removed in 3.16.

        # Use os.stat or os.lstat, depending on if symlinks shall be resolved.
        if fileobj is None:
            if not self.dereference:
                statres = os.lstat(name)
            else:
                statres = os.stat(name)
        else:
            statres = os.fstat(fileobj.fileno())
        linkname = ""

        stmd = statres.st_mode
        if stat.S_ISREG(stmd):
            inode = (statres.st_ino, statres.st_dev)
            if not self.dereference and statres.st_nlink > 1 and \
                    inode in self.inodes and arcname != self.inodes[inode]:
                # Is it a hardlink to an already
                # archived file?
                type = LNKTYPE
                linkname = self.inodes[inode]
            else:
                # The inode is added only if its valid.
                # For win32 it is always 0.
                type = REGTYPE
                if inode[0]:
                    self.inodes[inode] = arcname
        elif stat.S_ISDIR(stmd):
            type = DIRTYPE
        elif stat.S_ISFIFO(stmd):
            type = FIFOTYPE
        elif stat.S_ISLNK(stmd):
            type = SYMTYPE
            linkname = os.readlink(name)
        elif stat.S_ISCHR(stmd):
            type = CHRTYPE
        elif stat.S_ISBLK(stmd):
            type = BLKTYPE
        else:
            return None

        # Fill the TarInfo object with all
        # information we can get.
        tarinfo.name = arcname
        tarinfo.mode = stmd
        tarinfo.uid = statres.st_uid
        tarinfo.gid = statres.st_gid
        if type == REGTYPE:
            tarinfo.size = statres.st_size
        else:
            tarinfo.size = 0
        tarinfo.mtime = statres.st_mtime
        tarinfo.type = type
        tarinfo.linkname = linkname
        if pwd:
            try:
                tarinfo.uname = pwd.getpwuid(tarinfo.uid)[0]
            except KeyError:
                pass
        if grp:
            try:
                tarinfo.gname = grp.getgrgid(tarinfo.gid)[0]
            except KeyError:
                pass

        if type in (CHRTYPE, BLKTYPE):
            if hasattr(os, "major") and hasattr(os, "minor"):
                tarinfo.devmajor = os.major(statres.st_rdev)
                tarinfo.devminor = os.minor(statres.st_rdev)
        return tarinfo

    def list(self, verbose=True, *, members=None):
        """Print a table of contents to sys.stdout. If 'verbose' is False, only
           the names of the members are printed. If it is True, an 'ls -l'-like
           output is produced. 'members' is optional and must be a subset of the
           list returned by getmembers().
        """
        # Convert tarinfo type to stat type.
        type2mode = {REGTYPE: stat.S_IFREG, SYMTYPE: stat.S_IFLNK,
                     FIFOTYPE: stat.S_IFIFO, CHRTYPE: stat.S_IFCHR,
                     DIRTYPE: stat.S_IFDIR, BLKTYPE: stat.S_IFBLK}
        self._check()

        if members is None:
            members = self
        for tarinfo in members:
            if verbose:
                if tarinfo.mode is None:
                    _safe_print("??????????")
                else:
                    modetype = type2mode.get(tarinfo.type, 0)
                    _safe_print(stat.filemode(modetype | tarinfo.mode))
                _safe_print("%s/%s" % (tarinfo.uname or tarinfo.uid,
                                       tarinfo.gname or tarinfo.gid))
                if tarinfo.ischr() or tarinfo.isblk():
                    _safe_print("%10s" %
                            ("%d,%d" % (tarinfo.devmajor, tarinfo.devminor)))
                else:
                    _safe_print("%10d" % tarinfo.size)
                if tarinfo.mtime is None:
                    _safe_print("????-??-?? ??:??:??")
                else:
                    _safe_print("%d-%02d-%02d %02d:%02d:%02d" \
                                % time.localtime(tarinfo.mtime)[:6])

            _safe_print(tarinfo.name + ("/" if tarinfo.isdir() else ""))

            if verbose:
                if tarinfo.issym():
                    _safe_print("-> " + tarinfo.linkname)
                if tarinfo.islnk():
                    _safe_print("link to " + tarinfo.linkname)
            print()

    def add(self, name, arcname=None, recursive=True, *, filter=None):
        """Add the file 'name' to the archive. 'name' may be any type of file
           (directory, fifo, symbolic link, etc.). If given, 'arcname'
           specifies an alternative name for the file in the archive.
           Directories are added recursively by default. This can be avoided by
           setting 'recursive' to False. 'filter' is a function
           that expects a TarInfo object argument and returns the changed
           TarInfo object, if it returns None the TarInfo object will be
           excluded from the archive.
        """
        self._check("awx")

        if arcname is None:
            arcname = name

        # Skip if somebody tries to archive the archive...
        if self.name is not None and os.path.abspath(name) == self.name:
            self._dbg(2, "tarfile: Skipped %r" % name)
            return

        self._dbg(1, name)

        # Create a TarInfo object from the file.
        tarinfo = self.gettarinfo(name, arcname)

        if tarinfo is None:
            self._dbg(1, "tarfile: Unsupported type %r" % name)
            return

        # Change or exclude the TarInfo object.
        if filter is not None:
            tarinfo = filter(tarinfo)
            if tarinfo is None:
                self._dbg(2, "tarfile: Excluded %r" % name)
                return

        # Append the tar header and data to the archive.
        if tarinfo.isreg():
            with bltn_open(name, "rb") as f:
                self.addfile(tarinfo, f)

        elif tarinfo.isdir():
            self.addfile(tarinfo)
            if recursive:
                for f in sorted(os.listdir(name)):
                    self.add(os.path.join(name, f), os.path.join(arcname, f),
                            recursive, filter=filter)

        else:
            self.addfile(tarinfo)

    def addfile(self, tarinfo, fileobj=None):
        """Add the TarInfo object 'tarinfo' to the archive. If 'tarinfo' represents
           a non zero-size regular file, the 'fileobj' argument should be a binary file,
           and tarinfo.size bytes are read from it and added to the archive.
           You can create TarInfo objects directly, or by using gettarinfo().
        """
        self._check("awx")

        if fileobj is None and tarinfo.isreg() and tarinfo.size != 0:
            raise ValueError("fileobj not provided for non zero-size regular file")

        tarinfo = copy.copy(tarinfo)

        buf = tarinfo.tobuf(self.format, self.encoding, self.errors)
        self.fileobj.write(buf)
        self.offset += len(buf)
        bufsize=self.copybufsize
        # If there's data to follow, append it.
        if fileobj is not None:
            copyfileobj(fileobj, self.fileobj, tarinfo.size, bufsize=bufsize)
            blocks, remainder = divmod(tarinfo.size, BLOCKSIZE)
            if remainder > 0:
                self.fileobj.write(NUL * (BLOCKSIZE - remainder))
                blocks += 1
            self.offset += blocks * BLOCKSIZE

        self.members.append(tarinfo)

    def _get_filter_function(self, filter):
        if filter is None:
            filter = self.extraction_filter
            if filter is None:
                import warnings
                warnings.warn(
                    'Python 3.14 will, by default, filter extracted tar '
                    + 'archives and reject files or modify their metadata. '
                    + 'Use the filter argument to control this behavior.',
                    DeprecationWarning, stacklevel=3)
                return fully_trusted_filter
            if isinstance(filter, str):
                raise TypeError(
                    'String names are not supported for '
                    + 'TarFile.extraction_filter. Use a function such as '
                    + 'tarfile.data_filter directly.')
            return filter
        if callable(filter):
            return filter
        try:
            return _NAMED_FILTERS[filter]
        except KeyError:
            raise ValueError(f"filter {filter!r} not found") from None

    def extractall(self, path=".", members=None, *, numeric_owner=False,
                   filter=None):
        """Extract all members from the archive to the current working
           directory and set owner, modification time and permissions on
           directories afterwards. 'path' specifies a different directory
           to extract to. 'members' is optional and must be a subset of the
           list returned by getmembers(). If 'numeric_owner' is True, only
           the numbers for user/group names are used and not the names.

           The 'filter' function will be called on each member just
           before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        """
        directories = []

        filter_function = self._get_filter_function(filter)
        if members is None:
            members = self

        for member in members:
            tarinfo = self._get_extract_tarinfo(member, filter_function, path)
            if tarinfo is None:
                continue
            if tarinfo.isdir():
                # For directories, delay setting attributes until later,
                # since permissions can interfere with extraction and
                # extracting contents can reset mtime.
                directories.append(tarinfo)
            self._extract_one(tarinfo, path, set_attrs=not tarinfo.isdir(),
                              numeric_owner=numeric_owner)

        # Reverse sort directories.
        directories.sort(key=lambda a: a.name, reverse=True)

        # Set correct owner, mtime and filemode on directories.
        for tarinfo in directories:
            dirpath = os.path.join(path, tarinfo.name)
            try:
                self.chown(tarinfo, dirpath, numeric_owner=numeric_owner)
                self.utime(tarinfo, dirpath)
                self.chmod(tarinfo, dirpath)
            except ExtractError as e:
                self._handle_nonfatal_error(e)

    def extract(self, member, path="", set_attrs=True, *, numeric_owner=False,
                filter=None):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. 'member' may be a filename or a TarInfo object. You can
           specify a different directory using 'path'. File attributes (owner,
           mtime, mode) are set unless 'set_attrs' is False. If 'numeric_owner'
           is True, only the numbers for user/group names are used and not
           the names.

           The 'filter' function will be called before extraction.
           It can return a changed TarInfo or None to skip the member.
           String names of common filters are accepted.
        """
        filter_function = self._get_filter_function(filter)
        tarinfo = self._get_extract_tarinfo(member, filter_function, path)
        if tarinfo is not None:
            self._extract_one(tarinfo, path, set_attrs, numeric_owner)

    def _get_extract_tarinfo(self, member, filter_function, path):
        """Get filtered TarInfo (or None) from member, which might be a str"""
        if isinstance(member, str):
            tarinfo = self.getmember(member)
        else:
            tarinfo = member

        unfiltered = tarinfo
        try:
            tarinfo = filter_function(tarinfo, path)
        except (OSError, FilterError) as e:
            self._handle_fatal_error(e)
        except ExtractError as e:
            self._handle_nonfatal_error(e)
        if tarinfo is None:
            self._dbg(2, "tarfile: Excluded %r" % unfiltered.name)
            return None
        # Prepare the link target for makelink().
        if tarinfo.islnk():
            tarinfo = copy.copy(tarinfo)
            tarinfo._link_target = os.path.join(path, tarinfo.linkname)
        return tarinfo

    def _extract_one(self, tarinfo, path, set_attrs, numeric_owner):
        """Extract from filtered tarinfo to disk"""
        self._check("r")

        try:
            self._extract_member(tarinfo, os.path.join(path, tarinfo.name),
                                 set_attrs=set_attrs,
                                 numeric_owner=numeric_owner)
        except OSError as e:
            self._handle_fatal_error(e)
        except ExtractError as e:
            self._handle_nonfatal_error(e)

    def _handle_nonfatal_error(self, e):
        """Handle non-fatal error (ExtractError) according to errorlevel"""
        if self.errorlevel > 1:
            raise
        else:
            self._dbg(1, "tarfile: %s" % e)

    def _handle_fatal_error(self, e):
        """Handle "fatal" error according to self.errorlevel"""
        if self.errorlevel > 0:
            raise
        elif isinstance(e, OSError):
            if e.filename is None:
                self._dbg(1, "tarfile: %s" % e.strerror)
            else:
                self._dbg(1, "tarfile: %s %r" % (e.strerror, e.filename))
        else:
            self._dbg(1, "tarfile: %s %s" % (type(e).__name__, e))

    def extractfile(self, member):
        """Extract a member from the archive as a file object. 'member' may be
           a filename or a TarInfo object. If 'member' is a regular file or
           a link, an io.BufferedReader object is returned. For all other
           existing members, None is returned. If 'member' does not appear
           in the archive, KeyError is raised.
        """
        self._check("r")

        if isinstance(member, str):
            tarinfo = self.getmember(member)
        else:
            tarinfo = member

        if tarinfo.isreg() or tarinfo.type not in SUPPORTED_TYPES:
            # Members with unknown types are treated as regular files.
            return self.fileobject(self, tarinfo)

        elif tarinfo.islnk() or tarinfo.issym():
            if isinstance(self.fileobj, _Stream):
                # A small but ugly workaround for the case that someone tries
                # to extract a (sym)link as a file-object from a non-seekable
                # stream of tar blocks.
                raise StreamError("cannot extract (sym)link as file object")
            else:
                # A (sym)link's file object is its target's file object.
                return self.extractfile(self._find_link_target(tarinfo))
        else:
            # If there's no data associated with the member (directory, chrdev,
            # blkdev, etc.), return None instead of a file object.
            return None

    def _extract_member(self, tarinfo, targetpath, set_attrs=True,
                        numeric_owner=False):
        """Extract the TarInfo object tarinfo to a physical
           file called targetpath.
        """
        # Fetch the TarInfo object for the given name
        # and build the destination pathname, replacing
        # forward slashes to platform specific separators.
        targetpath = targetpath.rstrip("/")
        targetpath = targetpath.replace("/", os.sep)

        # Create all upper directories.
        upperdirs = os.path.dirname(targetpath)
        if upperdirs and not os.path.exists(upperdirs):
            # Create directories that are not part of the archive with
            # default permissions.
            os.makedirs(upperdirs, exist_ok=True)

        if tarinfo.islnk() or tarinfo.issym():
            self._dbg(1, "%s -> %s" % (tarinfo.name, tarinfo.linkname))
        else:
            self._dbg(1, tarinfo.name)

        if tarinfo.isreg():
            self.makefile(tarinfo, targetpath)
        elif tarinfo.isdir():
            self.makedir(tarinfo, targetpath)
        elif tarinfo.isfifo():
            self.makefifo(tarinfo, targetpath)
        elif tarinfo.ischr() or tarinfo.isblk():
            self.makedev(tarinfo, targetpath)
        elif tarinfo.islnk() or tarinfo.issym():
            self.makelink(tarinfo, targetpath)
        elif tarinfo.type not in SUPPORTED_TYPES:
            self.makeunknown(tarinfo, targetpath)
        else:
            self.makefile(tarinfo, targetpath)

        if set_attrs:
            self.chown(tarinfo, targetpath, numeric_owner)
            if not tarinfo.issym():
                self.chmod(tarinfo, targetpath)
                self.utime(tarinfo, targetpath)

    #--------------------------------------------------------------------------
    # Below are the different file methods. They are called via
    # _extract_member() when extract() is called. They can be replaced in a
    # subclass to implement other functionality.

    def makedir(self, tarinfo, targetpath):
        """Make a directory called targetpath.
        """
        try:
            if tarinfo.mode is None:
                # Use the system's default mode
                os.mkdir(targetpath)
            else:
                # Use a safe mode for the directory, the real mode is set
                # later in _extract_member().
                os.mkdir(targetpath, 0o700)
        except FileExistsError:
            if not os.path.isdir(targetpath):
                raise

    def makefile(self, tarinfo, targetpath):
        """Make a file called targetpath.
        """
        source = self.fileobj
        source.seek(tarinfo.offset_data)
        bufsize = self.copybufsize
        with bltn_open(targetpath, "wb") as target:
            if tarinfo.sparse is not None:
                for offset, size in tarinfo.sparse:
                    target.seek(offset)
                    copyfileobj(source, target, size, ReadError, bufsize)
                target.seek(tarinfo.size)
                target.truncate()
            else:
                copyfileobj(source, target, tarinfo.size, ReadError, bufsize)

    def makeunknown(self, tarinfo, targetpath):
        """Make a file from a TarInfo object with an unknown type
           at targetpath.
        """
        self.makefile(tarinfo, targetpath)
        self._dbg(1, "tarfile: Unknown file type %r, " \
                     "extracted as regular file." % tarinfo.type)

    def makefifo(self, tarinfo, targetpath):
        """Make a fifo called targetpath.
        """
        if hasattr(os, "mkfifo"):
            os.mkfifo(targetpath)
        else:
            raise ExtractError("fifo not supported by system")

    def makedev(self, tarinfo, targetpath):
        """Make a character or block device called targetpath.
        """
        if not hasattr(os, "mknod") or not hasattr(os, "makedev"):
            raise ExtractError("special devices not supported by system")

        mode = tarinfo.mode
        if mode is None:
            # Use mknod's default
            mode = 0o600
        if tarinfo.isblk():
            mode |= stat.S_IFBLK
        else:
            mode |= stat.S_IFCHR

        os.mknod(targetpath, mode,
                 os.makedev(tarinfo.devmajor, tarinfo.devminor))

    def makelink(self, tarinfo, targetpath):
        """Make a (symbolic) link called targetpath. If it cannot be created
          (platform limitation), we try to make a copy of the referenced file
          instead of a link.
        """
        try:
            # For systems that support symbolic and hard links.
            if tarinfo.issym():
                if os.path.lexists(targetpath):
                    # Avoid FileExistsError on following os.symlink.
                    os.unlink(targetpath)
                os.symlink(tarinfo.linkname, targetpath)
            else:
                if os.path.exists(tarinfo._link_target):
                    os.link(tarinfo._link_target, targetpath)
                else:
                    self._extract_member(self._find_link_target(tarinfo),
                                         targetpath)
        except symlink_exception:
            try:
                self._extract_member(self._find_link_target(tarinfo),
                                     targetpath)
            except KeyError:
                raise ExtractError("unable to resolve link inside archive") from None

    def chown(self, tarinfo, targetpath, numeric_owner):
        """Set owner of targetpath according to tarinfo. If numeric_owner
           is True, use .gid/.uid instead of .gname/.uname. If numeric_owner
           is False, fall back to .gid/.uid when the search based on name
           fails.
        """
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            # We have to be root to do so.
            g = tarinfo.gid
            u = tarinfo.uid
            if not numeric_owner:
                try:
                    if grp and tarinfo.gname:
                        g = grp.getgrnam(tarinfo.gname)[2]
                except KeyError:
                    pass
                try:
                    if pwd and tarinfo.uname:
                        u = pwd.getpwnam(tarinfo.uname)[2]
                except KeyError:
                    pass
            if g is None:
                g = -1
            if u is None:
                u = -1
            try:
                if tarinfo.issym() and hasattr(os, "lchown"):
                    os.lchown(targetpath, u, g)
                else:
                    os.chown(targetpath, u, g)
            except (OSError, OverflowError) as e:
                # OverflowError can be raised if an ID doesn't fit in 'id_t'
                raise ExtractError("could not change owner") from e

    def chmod(self, tarinfo, targetpath):
        """Set file permissions of targetpath according to tarinfo.
        """
        if tarinfo.mode is None:
            return
        try:
            os.chmod(targetpath, tarinfo.mode)
        except OSError as e:
            raise ExtractError("could not change mode") from e

    def utime(self, tarinfo, targetpath):
        """Set modification time of targetpath according to tarinfo.
        """
        mtime = tarinfo.mtime
        if mtime is None:
            return
        if not hasattr(os, 'utime'):
            return
        try:
            os.utime(targetpath, (mtime, mtime))
        except OSError as e:
            raise ExtractError("could not change modification time") from e

    #--------------------------------------------------------------------------
    def next(self):
        """Return the next member of the archive as a TarInfo object, when
           TarFile is opened for reading. Return None if there is no more
           available.
        """
        self._check("ra")
        if self.firstmember is not None:
            m = self.firstmember
            self.firstmember = None
            return m

        # Advance the file pointer.
        if self.offset != self.fileobj.tell():
            if self.offset == 0:
                return None
            self.fileobj.seek(self.offset - 1)
            if not self.fileobj.read(1):
                raise ReadError("unexpected end of data")

        # Read the next block.
        tarinfo = None
        while True:
            try:
                tarinfo = self.tarinfo.fromtarfile(self)
            except EOFHeaderError as e:
                if self.ignore_zeros:
                    self._dbg(2, "0x%X: %s" % (self.offset, e))
                    self.offset += BLOCKSIZE
                    continue
            except InvalidHeaderError as e:
                if self.ignore_zeros:
                    self._dbg(2, "0x%X: %s" % (self.offset, e))
                    self.offset += BLOCKSIZE
                    continue
                elif self.offset == 0:
                    raise ReadError(str(e)) from None
            except EmptyHeaderError:
                if self.offset == 0:
                    raise ReadError("empty file") from None
            except TruncatedHeaderError as e:
                if self.offset == 0:
                    raise ReadError(str(e)) from None
            except SubsequentHeaderError as e:
                raise ReadError(str(e)) from None
            except Exception as e:
                try:
                    import zlib
                    if isinstance(e, zlib.error):
                        raise ReadError(f'zlib error: {e}') from None
                    else:
                        raise e
                except ImportError:
                    raise e
            break

        if tarinfo is not None:
            # if streaming the file we do not want to cache the tarinfo
            if not self.stream:
                self.members.append(tarinfo)
        else:
            self._loaded = True

        return tarinfo

    #--------------------------------------------------------------------------
    # Little helper methods:

    def _getmember(self, name, tarinfo=None, normalize=False):
        """Find an archive member by name from bottom to top.
           If tarinfo is given, it is used as the starting point.
        """
        # Ensure that all members have been loaded.
        members = self.getmembers()

        # Limit the member search list up to tarinfo.
        skipping = False
        if tarinfo is not None:
            try:
                index = members.index(tarinfo)
            except ValueError:
                # The given starting point might be a (modified) copy.
                # We'll later skip members until we find an equivalent.
                skipping = True
            else:
                # Happy fast path
                members = members[:index]

        if normalize:
            name = os.path.normpath(name)

        for member in reversed(members):
            if skipping:
                if tarinfo.offset == member.offset:
                    skipping = False
                continue
            if normalize:
                member_name = os.path.normpath(member.name)
            else:
                member_name = member.name

            if name == member_name:
                return member

        if skipping:
            # Starting point was not found
            raise ValueError(tarinfo)

    def _load(self):
        """Read through the entire archive file and look for readable
           members. This should not run if the file is set to stream.
        """
        if not self.stream:
            while self.next() is not None:
                pass
            self._loaded = True

    def _check(self, mode=None):
        """Check if TarFile is still open, and if the operation's mode
           corresponds to TarFile's mode.
        """
        if self.closed:
            raise OSError("%s is closed" % self.__class__.__name__)
        if mode is not None and self.mode not in mode:
            raise OSError("bad operation for mode %r" % self.mode)

    def _find_link_target(self, tarinfo):
        """Find the target member of a symlink or hardlink member in the
           archive.
        """
        if tarinfo.issym():
            # Always search the entire archive.
            linkname = "/".join(filter(None, (os.path.dirname(tarinfo.name), tarinfo.linkname)))
            limit = None
        else:
            # Search the archive before the link, because a hard link is
            # just a reference to an already archived file.
            linkname = tarinfo.linkname
            limit = tarinfo

        member = self._getmember(linkname, tarinfo=limit, normalize=True)
        if member is None:
            raise KeyError("linkname %r not found" % linkname)
        return member

    def __iter__(self):
        """Provide an iterator object.
        """
        if self._loaded:
            yield from self.members
            return

        # Yield items using TarFile's next() method.
        # When all members have been read, set TarFile as _loaded.
        index = 0
        # Fix for SF #1100429: Under rare circumstances it can
        # happen that getmembers() is called during iteration,
        # which will have already exhausted the next() method.
        if self.firstmember is not None:
            tarinfo = self.next()
            index += 1
            yield tarinfo

        while True:
            if index < len(self.members):
                tarinfo = self.members[index]
            elif not self._loaded:
                tarinfo = self.next()
                if not tarinfo:
                    self._loaded = True
                    return
            else:
                return
            index += 1
            yield tarinfo

    def _dbg(self, level, msg):
        """Write debugging output to sys.stderr.
        """
        if level <= self.debug:
            print(msg, file=sys.stderr)

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, type, value, traceback):
        if type is None:
            self.close()
        else:
            # An exception occurred. We must not call close() because
            # it would try to write end-of-archive blocks and padding.
            if not self._extfileobj:
                self.fileobj.close()
            self.closed = True

#--------------------
# exported functions
#--------------------

def is_tarfile(name):
    """Return True if name points to a tar archive that we
       are able to handle, else return False.

       'name' should be a string, file, or file-like object.
    """
    try:
        if hasattr(name, "read"):
            pos = name.tell()
            t = open(fileobj=name)
            name.seek(pos)
        else:
            t = open(name)
        t.close()
        return True
    except TarError:
        return False

open = TarFile.open


def main():
    import argparse

    description = 'A simple command-line interface for tarfile module.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Verbose output')
    parser.add_argument('--filter', metavar='<filtername>',
                        choices=_NAMED_FILTERS,
                        help='Filter for extraction')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--list', metavar='<tarfile>',
                       help='Show listing of a tarfile')
    group.add_argument('-e', '--extract', nargs='+',
                       metavar=('<tarfile>', '<output_dir>'),
                       help='Extract tarfile into target dir')
    group.add_argument('-c', '--create', nargs='+',
                       metavar=('<name>', '<file>'),
                       help='Create tarfile from sources')
    group.add_argument('-t', '--test', metavar='<tarfile>',
                       help='Test if a tarfile is valid')

    args = parser.parse_args()

    if args.filter and args.extract is None:
        parser.exit(1, '--filter is only valid for extraction\n')

    if args.test is not None:
        src = args.test
        if is_tarfile(src):
            with open(src, 'r') as tar:
                tar.getmembers()
                print(tar.getmembers(), file=sys.stderr)
            if args.verbose:
                print('{!r} is a tar archive.'.format(src))
        else:
            parser.exit(1, '{!r} is not a tar archive.\n'.format(src))

    elif args.list is not None:
        src = args.list
        if is_tarfile(src):
            with TarFile.open(src, 'r:*') as tf:
                tf.list(verbose=args.verbose)
        else:
            parser.exit(1, '{!r} is not a tar archive.\n'.format(src))

    elif args.extract is not None:
        if len(args.extract) == 1:
            src = args.extract[0]
            curdir = os.curdir
        elif len(args.extract) == 2:
            src, curdir = args.extract
        else:
            parser.exit(1, parser.format_help())

        if is_tarfile(src):
            with TarFile.open(src, 'r:*') as tf:
                tf.extractall(path=curdir, filter=args.filter)
            if args.verbose:
                if curdir == '.':
                    msg = '{!r} file is extracted.'.format(src)
                else:
                    msg = ('{!r} file is extracted '
                           'into {!r} directory.').format(src, curdir)
                print(msg)
        else:
            parser.exit(1, '{!r} is not a tar archive.\n'.format(src))

    elif args.create is not None:
        tar_name = args.create.pop(0)
        _, ext = os.path.splitext(tar_name)
        compressions = {
            # gz
            '.gz': 'gz',
            '.tgz': 'gz',
            # xz
            '.xz': 'xz',
            '.txz': 'xz',
            # bz2
            '.bz2': 'bz2',
            '.tbz': 'bz2',
            '.tbz2': 'bz2',
            '.tb2': 'bz2',
        }
        tar_mode = 'w:' + compressions[ext] if ext in compressions else 'w'
        tar_files = args.create

        with TarFile.open(tar_name, tar_mode) as tf:
            for file_name in tar_files:
                tf.add(file_name)

        if args.verbose:
            print('{!r} file created.'.format(tar_name))

if __name__ == '__main__':
    main()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\key_management_endpoints.py ===
"""
KEY MANAGEMENT

All /key management endpoints

/key/generate
/key/info
/key/update
/key/delete
"""

import asyncio
import copy
import json
import secrets
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional, Tuple, cast

import fastapi
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache
from litellm.constants import LENGTH_OF_LITELLM_GENERATED_KEY, UI_SESSION_TOKEN_TEAM_ID
from litellm.litellm_core_utils.duration_parser import duration_in_seconds
from litellm.proxy._types import *
from litellm.proxy.auth.auth_checks import (
    _cache_key_object,
    _delete_cache_key_object,
    can_team_access_model,
    get_key_object,
    get_team_object,
)
from litellm.proxy.auth.auth_utils import abbreviate_api_key
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time
from litellm.proxy.hooks.key_management_event_hooks import KeyManagementEventHooks
from litellm.proxy.management_endpoints.common_utils import (
    _is_user_team_admin,
    _set_object_metadata_field,
)
from litellm.proxy.management_endpoints.model_management_endpoints import (
    _add_model_to_db,
)
from litellm.proxy.management_helpers.object_permission_utils import (
    handle_update_object_permission_common,
)
from litellm.proxy.management_helpers.team_member_permission_checks import (
    TeamMemberPermissionChecks,
)
from litellm.proxy.management_helpers.utils import management_endpoint_wrapper
from litellm.proxy.spend_tracking.spend_tracking_utils import _is_master_key
from litellm.proxy.utils import (
    PrismaClient,
    _hash_token_if_needed,
    handle_exception_on_proxy,
    jsonify_object,
)
from litellm.router import Router
from litellm.secret_managers.main import get_secret
from litellm.types.router import Deployment
from litellm.types.utils import (
    BudgetConfig,
    PersonalUIKeyGenerationConfig,
    TeamUIKeyGenerationConfig,
)


def _is_team_key(data: Union[GenerateKeyRequest, LiteLLM_VerificationToken]):
    return data.team_id is not None


def _get_user_in_team(
    team_table: LiteLLM_TeamTableCachedObj, user_id: Optional[str]
) -> Optional[Member]:
    if user_id is None:
        return None
    for member in team_table.members_with_roles:
        if member.user_id is not None and member.user_id == user_id:
            return member

    return None


def _is_allowed_to_make_key_request(
    user_api_key_dict: UserAPIKeyAuth, user_id: Optional[str], team_id: Optional[str]
) -> bool:
    """
    Assert user only creates keys for themselves

    Relevant issue: https://github.com/BerriAI/litellm/issues/7336
    """
    ## BASE CASE - PROXY ADMIN
    if (
        user_api_key_dict.user_role is not None
        and user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value
    ):
        return True

    if user_id is not None:
        assert (
            user_id == user_api_key_dict.user_id
        ), "User can only create keys for themselves. Got user_id={}, Your ID={}".format(
            user_id, user_api_key_dict.user_id
        )

    if team_id is not None:
        if (
            user_api_key_dict.team_id is not None
            and user_api_key_dict.team_id == UI_TEAM_ID
        ):
            return True  # handle https://github.com/BerriAI/litellm/issues/7482

    return True


def _team_key_operation_team_member_check(
    assigned_user_id: Optional[str],
    team_table: LiteLLM_TeamTableCachedObj,
    user_api_key_dict: UserAPIKeyAuth,
    team_key_generation: TeamUIKeyGenerationConfig,
    route: KeyManagementRoutes,
):
    if assigned_user_id is not None:
        key_assigned_user_in_team = _get_user_in_team(
            team_table=team_table, user_id=assigned_user_id
        )

        if key_assigned_user_in_team is None:
            raise HTTPException(
                status_code=400,
                detail=f"User={assigned_user_id} not assigned to team={team_table.team_id}",
            )

    team_member_object = _get_user_in_team(
        team_table=team_table, user_id=user_api_key_dict.user_id
    )

    is_admin = (
        user_api_key_dict.user_role is not None
        and user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value
    )

    if is_admin:
        return True
    elif team_member_object is None:
        raise HTTPException(
            status_code=400,
            detail=f"User={user_api_key_dict.user_id} not assigned to team={team_table.team_id}",
        )
    elif (
        "allowed_team_member_roles" in team_key_generation
        and team_member_object.role
        not in team_key_generation["allowed_team_member_roles"]
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Team member role {team_member_object.role} not in allowed_team_member_roles={team_key_generation['allowed_team_member_roles']}",
        )

    TeamMemberPermissionChecks.does_team_member_have_permissions_for_endpoint(
        team_member_object=team_member_object,
        team_table=team_table,
        route=route,
    )
    return True


def _key_generation_required_param_check(
    data: GenerateKeyRequest, required_params: Optional[List[str]]
):
    if required_params is None:
        return True

    data_dict = data.model_dump(exclude_unset=True)
    for param in required_params:
        if param not in data_dict:
            raise HTTPException(
                status_code=400,
                detail=f"Required param {param} not in data",
            )
    return True


def _team_key_generation_check(
    team_table: LiteLLM_TeamTableCachedObj,
    user_api_key_dict: UserAPIKeyAuth,
    data: GenerateKeyRequest,
    route: KeyManagementRoutes,
):
    if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value:
        return True
    if (
        litellm.key_generation_settings is not None
        and "team_key_generation" in litellm.key_generation_settings
    ):
        _team_key_generation = litellm.key_generation_settings["team_key_generation"]
    else:
        _team_key_generation = TeamUIKeyGenerationConfig(
            allowed_team_member_roles=["admin", "user"],
        )

    _team_key_operation_team_member_check(
        assigned_user_id=data.user_id,
        team_table=team_table,
        user_api_key_dict=user_api_key_dict,
        team_key_generation=_team_key_generation,
        route=route,
    )
    _key_generation_required_param_check(
        data,
        _team_key_generation.get("required_params"),
    )

    return True


def _personal_key_membership_check(
    user_api_key_dict: UserAPIKeyAuth,
    personal_key_generation: Optional[PersonalUIKeyGenerationConfig],
):
    if (
        personal_key_generation is None
        or "allowed_user_roles" not in personal_key_generation
    ):
        return True

    if user_api_key_dict.user_role not in personal_key_generation["allowed_user_roles"]:
        raise HTTPException(
            status_code=400,
            detail=f"Personal key creation has been restricted by admin. Allowed roles={litellm.key_generation_settings['personal_key_generation']['allowed_user_roles']}. Your role={user_api_key_dict.user_role}",  # type: ignore
        )

    return True


def _personal_key_generation_check(
    user_api_key_dict: UserAPIKeyAuth, data: GenerateKeyRequest
):
    if (
        litellm.key_generation_settings is None
        or litellm.key_generation_settings.get("personal_key_generation") is None
    ):
        return True

    _personal_key_generation = litellm.key_generation_settings["personal_key_generation"]  # type: ignore

    _personal_key_membership_check(
        user_api_key_dict,
        personal_key_generation=_personal_key_generation,
    )

    _key_generation_required_param_check(
        data,
        _personal_key_generation.get("required_params"),
    )

    return True


def key_generation_check(
    team_table: Optional[LiteLLM_TeamTableCachedObj],
    user_api_key_dict: UserAPIKeyAuth,
    data: GenerateKeyRequest,
    route: KeyManagementRoutes,
) -> bool:
    """
    Check if admin has restricted key creation to certain roles for teams or individuals
    """

    ## check if key is for team or individual
    is_team_key = _is_team_key(data=data)
    if is_team_key:
        if team_table is None and litellm.key_generation_settings is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to find team object in database. Team ID: {data.team_id}",
            )
        elif team_table is None:
            return True  # assume user is assigning team_id without using the team table
        return _team_key_generation_check(
            team_table=team_table,
            user_api_key_dict=user_api_key_dict,
            data=data,
            route=route,
        )
    else:
        return _personal_key_generation_check(
            user_api_key_dict=user_api_key_dict, data=data
        )


def common_key_access_checks(
    user_api_key_dict: UserAPIKeyAuth,
    data: Union[GenerateKeyRequest, UpdateKeyRequest],
    llm_router: Optional[Router],
    premium_user: bool,
) -> Literal[True]:
    """
    Check if user is allowed to make a key request, for this key
    """
    try:
        _is_allowed_to_make_key_request(
            user_api_key_dict=user_api_key_dict,
            user_id=data.user_id,
            team_id=data.team_id,
        )
    except AssertionError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    _check_model_access_group(
        models=data.models,
        llm_router=llm_router,
        premium_user=premium_user,
    )
    return True


router = APIRouter()


@router.post(
    "/key/generate",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=GenerateKeyResponse,
)
@management_endpoint_wrapper
async def generate_key_fn(  # noqa: PLR0915
    data: GenerateKeyRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Generate an API key based on the provided data.

    Docs: https://docs.litellm.ai/docs/proxy/virtual_keys

    Parameters:
    - duration: Optional[str] - Specify the length of time the token is valid for. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d").
    - key_alias: Optional[str] - User defined key alias
    - key: Optional[str] - User defined key value. If not set, a 16-digit unique sk-key is created for you.
    - team_id: Optional[str] - The team id of the key
    - user_id: Optional[str] - The user id of the key
    - budget_id: Optional[str] - The budget id associated with the key. Created by calling `/budget/new`.
    - models: Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models)
    - aliases: Optional[dict] - Any alias mappings, on top of anything in the config.yaml model list. - https://docs.litellm.ai/docs/proxy/virtual_keys#managing-auth---upgradedowngrade-models
    - config: Optional[dict] - any key-specific configs, overrides config in config.yaml
    - spend: Optional[int] - Amount spent by key. Default is 0. Will be updated by proxy whenever key is used. https://docs.litellm.ai/docs/proxy/virtual_keys#managing-auth---tracking-spend
    - send_invite_email: Optional[bool] - Whether to send an invite email to the user_id, with the generate key
    - max_budget: Optional[float] - Specify max budget for a given key.
    - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d").
    - max_parallel_requests: Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x.
    - metadata: Optional[dict] - Metadata for key, store information for key. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
    - guardrails: Optional[List[str]] - List of active guardrails for the key
    - permissions: Optional[dict] - key-specific permissions. Currently just used for turning off pii masking (if connected). Example - {"pii": false}
    - model_max_budget: Optional[Dict[str, BudgetConfig]] - Model-specific budgets {"gpt-4": {"budget_limit": 0.0005, "time_period": "30d"}}}. IF null or {} then no model specific budget.
    - model_rpm_limit: Optional[dict] - key-specific model rpm limit. Example - {"text-davinci-002": 1000, "gpt-3.5-turbo": 1000}. IF null or {} then no model specific rpm limit.
    - model_tpm_limit: Optional[dict] - key-specific model tpm limit. Example - {"text-davinci-002": 1000, "gpt-3.5-turbo": 1000}. IF null or {} then no model specific tpm limit.
    - allowed_cache_controls: Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.litellm.ai/docs/proxy/caching#turn-on--off-caching-per-request
    - blocked: Optional[bool] - Whether the key is blocked.
    - rpm_limit: Optional[int] - Specify rpm limit for a given key (Requests per minute)
    - tpm_limit: Optional[int] - Specify tpm limit for a given key (Tokens per minute)
    - soft_budget: Optional[float] - Specify soft budget for a given key. Will trigger a slack alert when this soft budget is reached.
    - tags: Optional[List[str]] - Tags for [tracking spend](https://litellm.vercel.app/docs/proxy/enterprise#tracking-spend-for-custom-tags) and/or doing [tag-based routing](https://litellm.vercel.app/docs/proxy/tag_routing).
    - enforced_params: Optional[List[str]] - List of enforced params for the key (Enterprise only). [Docs](https://docs.litellm.ai/docs/proxy/enterprise#enforce-required-params-for-llm-requests)
    - allowed_routes: Optional[list] - List of allowed routes for the key. Store the actual route or store a wildcard pattern for a set of routes. Example - ["/chat/completions", "/embeddings", "/keys/*"]
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - key-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    Examples:

    1. Allow users to turn on/off pii masking

    ```bash
    curl --location 'http://0.0.0.0:4000/key/generate' \
        --header 'Authorization: Bearer sk-1234' \
        --header 'Content-Type: application/json' \
        --data '{
            "permissions": {"allow_pii_controls": true}
    }'
    ```

    Returns:
    - key: (str) The generated api key
    - expires: (datetime) Datetime object for when key expires.
    - user_id: (str) Unique user id - used for tracking spend across multiple keys for same user id.
    """
    try:
        from litellm.proxy.proxy_server import (
            litellm_proxy_admin_name,
            llm_router,
            premium_user,
            prisma_client,
            user_api_key_cache,
            user_custom_key_generate,
        )

        verbose_proxy_logger.debug("entered /key/generate")

        if user_custom_key_generate is not None:
            if asyncio.iscoroutinefunction(user_custom_key_generate):
                result = await user_custom_key_generate(data)  # type: ignore
            else:
                raise ValueError("user_custom_key_generate must be a coroutine")
            decision = result.get("decision", True)
            message = result.get("message", "Authentication Failed - Custom Auth Rule")
            if not decision:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=message
                )
        team_table: Optional[LiteLLM_TeamTableCachedObj] = None
        if data.team_id is not None:
            try:
                team_table = await get_team_object(
                    team_id=data.team_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=user_api_key_dict.parent_otel_span,
                    check_db_only=True,
                )
            except Exception as e:
                verbose_proxy_logger.debug(
                    f"Error getting team object in `/key/generate`: {e}"
                )
                team_table = None

        key_generation_check(
            team_table=team_table,
            user_api_key_dict=user_api_key_dict,
            data=data,
            route=KeyManagementRoutes.KEY_GENERATE,
        )

        common_key_access_checks(
            user_api_key_dict=user_api_key_dict,
            data=data,
            llm_router=llm_router,
            premium_user=premium_user,
        )

        # check if user set default key/generate params on config.yaml
        if litellm.default_key_generate_params is not None:
            for elem in data:
                key, value = elem
                if value is None and key in [
                    "max_budget",
                    "user_id",
                    "team_id",
                    "max_parallel_requests",
                    "tpm_limit",
                    "rpm_limit",
                    "budget_duration",
                ]:
                    setattr(
                        data, key, litellm.default_key_generate_params.get(key, None)
                    )
                elif key == "models" and value == []:
                    setattr(data, key, litellm.default_key_generate_params.get(key, []))
                elif key == "metadata" and value == {}:
                    setattr(data, key, litellm.default_key_generate_params.get(key, {}))

        # check if user set default key/generate params on config.yaml
        if litellm.upperbound_key_generate_params is not None:
            for elem in data:
                key, value = elem
                upperbound_value = getattr(
                    litellm.upperbound_key_generate_params, key, None
                )
                if upperbound_value is not None:
                    if value is None:
                        # Use the upperbound value if user didn't provide a value
                        setattr(data, key, upperbound_value)
                    else:
                        # Compare with upperbound for numeric fields
                        if key in [
                            "max_budget",
                            "max_parallel_requests",
                            "tpm_limit",
                            "rpm_limit",
                        ]:
                            if value > upperbound_value:
                                raise HTTPException(
                                    status_code=400,
                                    detail={
                                        "error": f"{key} is over max limit set in config - user_value={value}; max_value={upperbound_value}"
                                    },
                                )
                        # Compare durations
                        elif key in ["budget_duration", "duration"]:
                            upperbound_duration = duration_in_seconds(
                                duration=upperbound_value
                            )
                            user_duration = duration_in_seconds(duration=value)
                            if user_duration > upperbound_duration:
                                raise HTTPException(
                                    status_code=400,
                                    detail={
                                        "error": f"{key} is over max limit set in config - user_value={value}; max_value={upperbound_value}"
                                    },
                                )

        # TODO: @ishaan-jaff: Migrate all budget tracking to use LiteLLM_BudgetTable
        _budget_id = data.budget_id
        if prisma_client is not None and data.soft_budget is not None:
            # create the Budget Row for the LiteLLM Verification Token
            budget_row = LiteLLM_BudgetTable(
                soft_budget=data.soft_budget,
                model_max_budget=data.model_max_budget or {},
            )
            new_budget = prisma_client.jsonify_object(
                budget_row.json(exclude_none=True)
            )

            _budget = await prisma_client.db.litellm_budgettable.create(
                data={
                    **new_budget,  # type: ignore
                    "created_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
                    "updated_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
                }
            )
            _budget_id = getattr(_budget, "budget_id", None)

        # ADD METADATA FIELDS
        # Set Management Endpoint Metadata Fields
        for field in LiteLLM_ManagementEndpoint_MetadataFields_Premium:
            if getattr(data, field) is not None:
                _set_object_metadata_field(
                    object_data=data,
                    field_name=field,
                    value=getattr(data, field),
                )

        data_json = data.model_dump(exclude_unset=True, exclude_none=True)  # type: ignore

        # if we get max_budget passed to /key/generate, then use it as key_max_budget. Since generate_key_helper_fn is used to make new users
        if "max_budget" in data_json:
            data_json["key_max_budget"] = data_json.pop("max_budget", None)
        if _budget_id is not None:
            data_json["budget_id"] = _budget_id

        if "budget_duration" in data_json:
            data_json["key_budget_duration"] = data_json.pop("budget_duration", None)

        if user_api_key_dict.user_id is not None:
            data_json["created_by"] = user_api_key_dict.user_id
            data_json["updated_by"] = user_api_key_dict.user_id

        # Set tags on the new key
        if "tags" in data_json:
            from litellm.proxy.proxy_server import premium_user

            if premium_user is not True and data_json["tags"] is not None:
                raise ValueError(
                    f"Only premium users can add tags to keys. {CommonProxyErrors.not_premium_user.value}"
                )

            _metadata = data_json.get("metadata")
            if not _metadata:
                data_json["metadata"] = {"tags": data_json["tags"]}
            else:
                data_json["metadata"]["tags"] = data_json["tags"]

            data_json.pop("tags")

        data_json = await _set_object_permission(
            data_json=data_json,
            prisma_client=prisma_client,
        )

        await _enforce_unique_key_alias(
            key_alias=data_json.get("key_alias", None),
            prisma_client=prisma_client,
        )

        response = await generate_key_helper_fn(
            request_type="key", **data_json, table_name="key"
        )

        response[
            "soft_budget"
        ] = data.soft_budget  # include the user-input soft budget in the response

        response = GenerateKeyResponse(**response)

        response.token = (
            response.token_id
        )  # remap token to use the hash, and leave the key in the `key` field [TODO]: clean up generate_key_helper_fn to do this

        asyncio.create_task(
            KeyManagementEventHooks.async_key_generated_hook(
                data=data,
                response=response,
                user_api_key_dict=user_api_key_dict,
                litellm_changed_by=litellm_changed_by,
            )
        )

        return response
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.generate_key_fn(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


def prepare_metadata_fields(
    data: BaseModel, non_default_values: dict, existing_metadata: dict
) -> dict:
    """
    Check LiteLLM_ManagementEndpoint_MetadataFields (proxy/_types.py) for fields that are allowed to be updated
    """
    if "metadata" not in non_default_values:  # allow user to set metadata to none
        non_default_values["metadata"] = existing_metadata.copy()

    casted_metadata = cast(dict, non_default_values["metadata"])

    data_json = data.model_dump(exclude_unset=True, exclude_none=True)

    try:
        for k, v in data_json.items():
            if k in LiteLLM_ManagementEndpoint_MetadataFields:
                if isinstance(v, datetime):
                    casted_metadata[k] = v.isoformat()
                else:
                    casted_metadata[k] = v

    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.prepare_metadata_fields(): Exception occured - {}".format(
                str(e)
            )
        )

    non_default_values["metadata"] = casted_metadata
    return non_default_values


async def _set_object_permission(
    data_json: dict,
    prisma_client: Optional[PrismaClient],
):
    """
    Creates the LiteLLM_ObjectPermissionTable record for the key.
    - Handles permissions for vector stores and mcp servers.
    """
    if prisma_client is None:
        return data_json

    if "object_permission" in data_json:
        created_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.create(
                data=data_json["object_permission"],
            )
        )
        data_json[
            "object_permission_id"
        ] = created_object_permission.object_permission_id

        # delete the object_permission from the data_json
        data_json.pop("object_permission")
    return data_json


async def prepare_key_update_data(
    data: Union[UpdateKeyRequest, RegenerateKeyRequest],
    existing_key_row: LiteLLM_VerificationToken,
):
    data_json: dict = data.model_dump(exclude_unset=True)
    data_json.pop("key", None)
    non_default_values = {}
    for k, v in data_json.items():
        if k in LiteLLM_ManagementEndpoint_MetadataFields:
            continue
        non_default_values[k] = v

    if "duration" in non_default_values:
        duration = non_default_values.pop("duration")
        if duration and (isinstance(duration, str)) and len(duration) > 0:
            duration_s = duration_in_seconds(duration=duration)
            expires = datetime.now(timezone.utc) + timedelta(seconds=duration_s)
            non_default_values["expires"] = expires

    if "budget_duration" in non_default_values:
        budget_duration = non_default_values.pop("budget_duration")
        if (
            budget_duration
            and (isinstance(budget_duration, str))
            and len(budget_duration) > 0
        ):
            from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time

            key_reset_at = get_budget_reset_time(budget_duration=budget_duration)
            non_default_values["budget_reset_at"] = key_reset_at
            non_default_values["budget_duration"] = budget_duration

    if "object_permission" in non_default_values:
        non_default_values = await _handle_update_object_permission(
            data_json=non_default_values,
            existing_key_row=existing_key_row,
        )

    _metadata = existing_key_row.metadata or {}

    # validate model_max_budget
    if "model_max_budget" in non_default_values:
        validate_model_max_budget(non_default_values["model_max_budget"])

    non_default_values = prepare_metadata_fields(
        data=data, non_default_values=non_default_values, existing_metadata=_metadata
    )

    return non_default_values


async def _handle_update_object_permission(
    data_json: dict,
    existing_key_row: LiteLLM_VerificationToken,
) -> dict:
    """
    Handle the update of object permission.
    """
    from litellm.proxy.proxy_server import prisma_client

    # Use the common helper to handle the object permission update
    object_permission_id = await handle_update_object_permission_common(
        data_json=data_json,
        existing_object_permission_id=existing_key_row.object_permission_id,
        prisma_client=prisma_client,
    )

    # Add the object_permission_id to data_json if one was created/updated
    if object_permission_id is not None:
        data_json["object_permission_id"] = object_permission_id
        verbose_proxy_logger.debug(
            f"updated object_permission_id: {object_permission_id}"
        )

    return data_json


def is_different_team(
    data: UpdateKeyRequest, existing_key_row: LiteLLM_VerificationToken
) -> bool:
    if data.team_id is None:
        return False
    if existing_key_row.team_id is None:
        return True
    return data.team_id != existing_key_row.team_id


@router.post(
    "/key/update", tags=["key management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def update_key_fn(
    request: Request,
    data: UpdateKeyRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Update an existing API key's parameters.

    Parameters:
    - key: str - The key to update
    - key_alias: Optional[str] - User-friendly key alias
    - user_id: Optional[str] - User ID associated with key
    - team_id: Optional[str] - Team ID associated with key
    - budget_id: Optional[str] - The budget id associated with the key. Created by calling `/budget/new`.
    - models: Optional[list] - Model_name's a user is allowed to call
    - tags: Optional[List[str]] - Tags for organizing keys (Enterprise only)
    - enforced_params: Optional[List[str]] - List of enforced params for the key (Enterprise only). [Docs](https://docs.litellm.ai/docs/proxy/enterprise#enforce-required-params-for-llm-requests)
    - spend: Optional[float] - Amount spent by key
    - max_budget: Optional[float] - Max budget for key
    - model_max_budget: Optional[Dict[str, BudgetConfig]] - Model-specific budgets {"gpt-4": {"budget_limit": 0.0005, "time_period": "30d"}}
    - budget_duration: Optional[str] - Budget reset period ("30d", "1h", etc.)
    - soft_budget: Optional[float] - [TODO] Soft budget limit (warning vs. hard stop). Will trigger a slack alert when this soft budget is reached.
    - max_parallel_requests: Optional[int] - Rate limit for parallel requests
    - metadata: Optional[dict] - Metadata for key. Example {"team": "core-infra", "app": "app2"}
    - tpm_limit: Optional[int] - Tokens per minute limit
    - rpm_limit: Optional[int] - Requests per minute limit
    - model_rpm_limit: Optional[dict] - Model-specific RPM limits {"gpt-4": 100, "claude-v1": 200}
    - model_tpm_limit: Optional[dict] - Model-specific TPM limits {"gpt-4": 100000, "claude-v1": 200000}
    - allowed_cache_controls: Optional[list] - List of allowed cache control values
    - duration: Optional[str] - Key validity duration ("30d", "1h", etc.)
    - permissions: Optional[dict] - Key-specific permissions
    - send_invite_email: Optional[bool] - Send invite email to user_id
    - guardrails: Optional[List[str]] - List of active guardrails for the key
    - blocked: Optional[bool] - Whether the key is blocked
    - aliases: Optional[dict] - Model aliases for the key - [Docs](https://litellm.vercel.app/docs/proxy/virtual_keys#model-aliases)
    - config: Optional[dict] - [DEPRECATED PARAM] Key-specific config.
    - temp_budget_increase: Optional[float] - Temporary budget increase for the key (Enterprise only).
    - temp_budget_expiry: Optional[str] - Expiry time for the temporary budget increase (Enterprise only).
    - allowed_routes: Optional[list] - List of allowed routes for the key. Store the actual route or store a wildcard pattern for a set of routes. Example - ["/chat/completions", "/embeddings", "/keys/*"]
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - key-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    Example:
    ```bash
    curl --location 'http://0.0.0.0:4000/key/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "key": "sk-1234",
        "key_alias": "my-key",
        "user_id": "user-1234",
        "team_id": "team-1234",
        "max_budget": 100,
        "metadata": {"any_key": "any-val"},
    }'
    ```
    """
    from litellm.proxy.proxy_server import (
        llm_router,
        premium_user,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    try:
        data_json: dict = data.model_dump(exclude_unset=True, exclude_none=True)
        key = data_json.pop("key")

        # get the row from db
        if prisma_client is None:
            raise Exception("Not connected to DB!")

        common_key_access_checks(
            user_api_key_dict=user_api_key_dict,
            data=data,
            llm_router=llm_router,
            premium_user=premium_user,
        )

        existing_key_row = await prisma_client.get_data(
            token=data.key, table_name="key", query_type="find_unique"
        )

        if existing_key_row is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Team not found, passed team_id={data.team_id}"},
            )

        # check if user has permission to update key
        await TeamMemberPermissionChecks.can_team_member_execute_key_management_endpoint(
            user_api_key_dict=user_api_key_dict,
            route=KeyManagementRoutes.KEY_UPDATE,
            prisma_client=prisma_client,
            existing_key_row=existing_key_row,
            user_api_key_cache=user_api_key_cache,
        )

        # if team change - check if this is possible
        if is_different_team(data=data, existing_key_row=existing_key_row):
            team_obj = await get_team_object(
                team_id=cast(str, data.team_id),
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                check_db_only=True,
            )
            if llm_router is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "LLM router not found. Please set it up by passing in a valid config.yaml or adding models via the UI."
                    },
                )
            validate_key_team_change(
                key=existing_key_row,
                team=team_obj,
                change_initiated_by=user_api_key_dict,
                llm_router=llm_router,
            )
        non_default_values = await prepare_key_update_data(
            data=data, existing_key_row=existing_key_row
        )

        await _enforce_unique_key_alias(
            key_alias=non_default_values.get("key_alias", None),
            prisma_client=prisma_client,
            existing_key_token=existing_key_row.token,
        )

        _data = {**non_default_values, "token": key}
        response = await prisma_client.update_data(token=key, data=_data)

        # Delete - key from cache, since it's been updated!
        # key updated - a new model could have been added to this key. it should not block requests after this is done
        await _delete_cache_key_object(
            hashed_token=hash_token(key),
            user_api_key_cache=user_api_key_cache,
            proxy_logging_obj=proxy_logging_obj,
        )

        asyncio.create_task(
            KeyManagementEventHooks.async_key_updated_hook(
                data=data,
                existing_key_row=existing_key_row,
                response=response,
                user_api_key_dict=user_api_key_dict,
                litellm_changed_by=litellm_changed_by,
            )
        )

        if response is None:
            raise ValueError("Failed to update key got response = None")

        return {"key": key, **response["data"]}
        # update based on remaining passed in values
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.update_key_fn(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


def validate_key_team_change(
    key: LiteLLM_VerificationToken,
    team: LiteLLM_TeamTable,
    change_initiated_by: UserAPIKeyAuth,
    llm_router: Router,
):
    """
    Validate that a key can be moved to a new team.

    - The team must have access to the key's models
    - The key's user_id must be a member of the team
    - The key's tpm/rpm limit must be less than the team's tpm/rpm limit
    - The person initiating the change must be either Proxy Admin or Team Admin
    """
    # Check if the team has access to the key's models
    if len(key.models) > 0:
        for model in key.models:
            can_team_access_model(
                model=model,
                team_object=team,
                llm_router=llm_router,
            )

    # Check if the key's user_id is a member of the team
    if key.user_id is not None:
        is_member = False
        for member in team.members_with_roles:
            if member.user_id == key.user_id:
                is_member = True
                break
        if not is_member:
            raise HTTPException(
                status_code=403,
                detail=f"User={key.user_id} is not a member of the team={team.team_id}. Check team members via `/team/info`.",
            )

    # Check if the key's tpm/rpm limit is less than the team's tpm/rpm limit
    if key.tpm_limit is not None:
        if team.tpm_limit and key.tpm_limit > team.tpm_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Key={key.token} has a tpm_limit={key.tpm_limit} which is greater than the team's tpm_limit={team.tpm_limit}.",
            )
        if team.rpm_limit and key.rpm_limit and key.rpm_limit > team.rpm_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Key={key.token} has a rpm_limit={key.rpm_limit} which is greater than the team's rpm_limit={team.rpm_limit}.",
            )

    # Check if the person initiating the change is a Proxy Admin or Team Admin
    if change_initiated_by.user_role == LitellmUserRoles.PROXY_ADMIN.value:
        return
    elif _is_user_team_admin(
        user_api_key_dict=change_initiated_by,
        team_obj=team,
    ):
        return
    else:
        raise HTTPException(
            status_code=403,
            detail=f"User={change_initiated_by.user_id} is not a Proxy Admin or Team Admin for team={team.team_id}.",
        )


@router.post(
    "/key/delete", tags=["key management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def delete_key_fn(
    data: KeyRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Delete a key from the key management system.

    Parameters::
    - keys (List[str]): A list of keys or hashed keys to delete. Example {"keys": ["sk-QWrxEynunsNpV1zT48HIrw", "837e17519f44683334df5291321d97b8bf1098cd490e49e215f6fea935aa28be"]}
    - key_aliases (List[str]): A list of key aliases to delete. Can be passed instead of `keys`.Example {"key_aliases": ["alias1", "alias2"]}

    Returns:
    - deleted_keys (List[str]): A list of deleted keys. Example {"deleted_keys": ["sk-QWrxEynunsNpV1zT48HIrw", "837e17519f44683334df5291321d97b8bf1098cd490e49e215f6fea935aa28be"]}

    Example:
    ```bash
    curl --location 'http://0.0.0.0:4000/key/delete' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "keys": ["sk-QWrxEynunsNpV1zT48HIrw"]
    }'
    ```

    Raises:
        HTTPException: If an error occurs during key deletion.
    """
    try:
        from litellm.proxy.proxy_server import prisma_client, user_api_key_cache

        if prisma_client is None:
            raise Exception("Not connected to DB!")

        ## only allow user to delete keys they own
        verbose_proxy_logger.debug(
            f"user_api_key_dict.user_role: {user_api_key_dict.user_role}"
        )

        num_keys_to_be_deleted = 0
        deleted_keys = []
        if data.keys:
            number_deleted_keys, _keys_being_deleted = await delete_verification_tokens(
                tokens=data.keys,
                user_api_key_cache=user_api_key_cache,
                user_api_key_dict=user_api_key_dict,
            )
            num_keys_to_be_deleted = len(data.keys)
            deleted_keys = data.keys
        elif data.key_aliases:
            number_deleted_keys, _keys_being_deleted = await delete_key_aliases(
                key_aliases=data.key_aliases,
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                user_api_key_dict=user_api_key_dict,
            )
            num_keys_to_be_deleted = len(data.key_aliases)
            deleted_keys = data.key_aliases
        else:
            raise ValueError("Invalid request type")

        if number_deleted_keys is None:
            raise ProxyException(
                message="Failed to delete keys got None response from delete_verification_token",
                type=ProxyErrorTypes.internal_server_error,
                param="keys",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        verbose_proxy_logger.debug(f"/key/delete - deleted_keys={number_deleted_keys}")

        try:
            assert num_keys_to_be_deleted == len(deleted_keys)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Not all keys passed in were deleted. This probably means you don't have access to delete all the keys passed in. Keys passed in={num_keys_to_be_deleted}, Deleted keys ={number_deleted_keys}"
                },
            )

        verbose_proxy_logger.debug(
            f"/keys/delete - cache after delete: {user_api_key_cache.in_memory_cache.cache_dict}"
        )

        asyncio.create_task(
            KeyManagementEventHooks.async_key_deleted_hook(
                data=data,
                keys_being_deleted=_keys_being_deleted,
                user_api_key_dict=user_api_key_dict,
                litellm_changed_by=litellm_changed_by,
                response=number_deleted_keys,
            )
        )

        return {"deleted_keys": deleted_keys}
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.delete_key_fn(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.post(
    "/v2/key/info",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def info_key_fn_v2(
    data: Optional[KeyRequest] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Retrieve information about a list of keys.

    **New endpoint**. Currently admin only.
    Parameters:
        keys: Optional[list] = body parameter representing the key(s) in the request
        user_api_key_dict: UserAPIKeyAuth = Dependency representing the user's API key
    Returns:
        Dict containing the key and its associated information

    Example Curl:
    ```
    curl -X GET "http://0.0.0.0:4000/key/info" \
    -H "Authorization: Bearer sk-1234" \
    -d {"keys": ["sk-1", "sk-2", "sk-3"]}
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Malformed request. No keys passed in."},
            )

        key_info = await prisma_client.get_data(
            token=data.keys, table_name="key", query_type="find_all"
        )
        if key_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "No keys found"},
            )
        filtered_key_info = []
        for k in key_info:
            try:
                k = k.model_dump()  # noqa
            except Exception:
                # if using pydantic v1
                k = k.dict()
            filtered_key_info.append(k)
        return {"key": data.keys, "info": filtered_key_info}

    except Exception as e:
        raise handle_exception_on_proxy(e)


@router.get(
    "/key/info", tags=["key management"], dependencies=[Depends(user_api_key_auth)]
)
async def info_key_fn(
    key: Optional[str] = fastapi.Query(
        default=None, description="Key in the request parameters"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Retrieve information about a key.
    Parameters:
        key: Optional[str] = Query parameter representing the key in the request
        user_api_key_dict: UserAPIKeyAuth = Dependency representing the user's API key
    Returns:
        Dict containing the key and its associated information

    Example Curl:
    ```
    curl -X GET "http://0.0.0.0:4000/key/info?key=sk-02Wr4IAlN3NvPXvL5JVvDA" \
-H "Authorization: Bearer sk-1234"
    ```

    Example Curl - if no key is passed, it will use the Key Passed in Authorization Header
    ```
    curl -X GET "http://0.0.0.0:4000/key/info" \
-H "Authorization: Bearer sk-02Wr4IAlN3NvPXvL5JVvDA"
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )

        # default to using Auth token if no key is passed in
        key = key or user_api_key_dict.api_key
        hashed_key: Optional[str] = key
        if key is not None:
            hashed_key = _hash_token_if_needed(token=key)
        key_info = await prisma_client.db.litellm_verificationtoken.find_unique(
            where={"token": hashed_key},  # type: ignore
            include={"litellm_budget_table": True},
        )
        if key_info is None:
            raise ProxyException(
                message="Key not found in database",
                type=ProxyErrorTypes.not_found_error,
                param="key",
                code=status.HTTP_404_NOT_FOUND,
            )

        if (
            await _can_user_query_key_info(
                user_api_key_dict=user_api_key_dict,
                key=key,
                key_info=key_info,
            )
            is not True
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this key's info. Your role={}".format(
                    user_api_key_dict.user_role
                ),
            )
        ## REMOVE HASHED TOKEN INFO BEFORE RETURNING ##
        try:
            key_info = key_info.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            key_info = key_info.dict()
        key_info.pop("token")
        return {"key": key, "info": key_info}
    except Exception as e:
        raise handle_exception_on_proxy(e)


def _check_model_access_group(
    models: Optional[List[str]], llm_router: Optional[Router], premium_user: bool
) -> Literal[True]:
    """
    if is_model_access_group is True + is_wildcard_route is True, check if user is a premium user

    Return True if user is a premium user, False otherwise
    """
    if models is None or llm_router is None:
        return True

    for model in models:
        if llm_router._is_model_access_group_for_wildcard_route(
            model_access_group=model
        ):
            if not premium_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Setting a model access group on a wildcard model is only available for LiteLLM Enterprise users.{}".format(
                            CommonProxyErrors.not_premium_user.value
                        )
                    },
                )

    return True


async def generate_key_helper_fn(  # noqa: PLR0915
    request_type: Literal[
        "user", "key"
    ],  # identifies if this request is from /user/new or /key/generate
    duration: Optional[str] = None,
    models: list = [],
    aliases: dict = {},
    config: dict = {},
    spend: float = 0.0,
    key_max_budget: Optional[float] = None,  # key_max_budget is used to Budget Per key
    key_budget_duration: Optional[str] = None,
    budget_id: Optional[float] = None,  # budget id <-> LiteLLM_BudgetTable
    soft_budget: Optional[
        float
    ] = None,  # soft_budget is used to set soft Budgets Per user
    max_budget: Optional[float] = None,  # max_budget is used to Budget Per user
    blocked: Optional[bool] = None,
    budget_duration: Optional[str] = None,  # max_budget is used to Budget Per user
    token: Optional[str] = None,
    key: Optional[
        str
    ] = None,  # dev-friendly alt param for 'token'. Exposed on `/key/generate` for setting key value yourself.
    user_id: Optional[str] = None,
    user_alias: Optional[str] = None,
    team_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    max_parallel_requests: Optional[int] = None,
    metadata: Optional[dict] = {},
    tpm_limit: Optional[int] = None,
    rpm_limit: Optional[int] = None,
    query_type: Literal["insert_data", "update_data"] = "insert_data",
    update_key_values: Optional[dict] = None,
    key_alias: Optional[str] = None,
    allowed_cache_controls: Optional[list] = [],
    permissions: Optional[dict] = {},
    model_max_budget: Optional[dict] = {},
    model_rpm_limit: Optional[dict] = None,
    model_tpm_limit: Optional[dict] = None,
    guardrails: Optional[list] = None,
    teams: Optional[list] = None,
    organization_id: Optional[str] = None,
    table_name: Optional[Literal["key", "user"]] = None,
    send_invite_email: Optional[bool] = None,
    created_by: Optional[str] = None,
    updated_by: Optional[str] = None,
    allowed_routes: Optional[list] = None,
    sso_user_id: Optional[str] = None,
    object_permission_id: Optional[
        str
    ] = None,  # object_permission_id <-> LiteLLM_ObjectPermissionTable
    object_permission: Optional[LiteLLM_ObjectPermissionBase] = None,
):
    from litellm.proxy.proxy_server import (
        litellm_proxy_budget_name,
        premium_user,
        prisma_client,
    )

    if prisma_client is None:
        raise Exception(
            "Connect Proxy to database to generate keys - https://docs.litellm.ai/docs/proxy/virtual_keys "
        )

    if token is None:
        if key is not None:
            token = key
        else:
            token = f"sk-{secrets.token_urlsafe(LENGTH_OF_LITELLM_GENERATED_KEY)}"

    if duration is None:  # allow tokens that never expire
        expires = None
    else:
        duration_s = duration_in_seconds(duration=duration)
        expires = datetime.now(timezone.utc) + timedelta(seconds=duration_s)

    if key_budget_duration is None:  # one-time budget
        key_reset_at = None
    else:
        duration_s = duration_in_seconds(duration=key_budget_duration)
        key_reset_at = datetime.now(timezone.utc) + timedelta(seconds=duration_s)

    if budget_duration is None:  # one-time budget
        reset_at = None
    else:
        reset_at = get_budget_reset_time(budget_duration=budget_duration)

    aliases_json = json.dumps(aliases)
    config_json = json.dumps(config)
    permissions_json = json.dumps(permissions)

    # Add model_rpm_limit and model_tpm_limit to metadata
    if model_rpm_limit is not None:
        metadata = metadata or {}
        metadata["model_rpm_limit"] = model_rpm_limit
    if model_tpm_limit is not None:
        metadata = metadata or {}
        metadata["model_tpm_limit"] = model_tpm_limit
    if guardrails is not None:
        metadata = metadata or {}
        metadata["guardrails"] = guardrails

    metadata_json = json.dumps(metadata)
    validate_model_max_budget(model_max_budget)
    model_max_budget_json = json.dumps(model_max_budget)
    user_role = user_role
    tpm_limit = tpm_limit
    rpm_limit = rpm_limit
    allowed_cache_controls = allowed_cache_controls

    try:
        # Create a new verification token (you may want to enhance this logic based on your needs)

        user_data = {
            "max_budget": max_budget,
            "user_email": user_email,
            "user_id": user_id,
            "user_alias": user_alias,
            "team_id": team_id,
            "organization_id": organization_id,
            "user_role": user_role,
            "spend": spend,
            "models": models,
            "metadata": metadata_json,
            "max_parallel_requests": max_parallel_requests,
            "tpm_limit": tpm_limit,
            "rpm_limit": rpm_limit,
            "budget_duration": budget_duration,
            "budget_reset_at": reset_at,
            "allowed_cache_controls": allowed_cache_controls,
            "sso_user_id": sso_user_id,
            "object_permission_id": object_permission_id,
        }
        if teams is not None:
            user_data["teams"] = teams
        key_data = {
            "token": token,
            "key_alias": key_alias,
            "expires": expires,
            "models": models,
            "aliases": aliases_json,
            "config": config_json,
            "spend": spend,
            "max_budget": key_max_budget,
            "user_id": user_id,
            "team_id": team_id,
            "max_parallel_requests": max_parallel_requests,
            "metadata": metadata_json,
            "tpm_limit": tpm_limit,
            "rpm_limit": rpm_limit,
            "budget_duration": key_budget_duration,
            "budget_reset_at": key_reset_at,
            "allowed_cache_controls": allowed_cache_controls,
            "permissions": permissions_json,
            "model_max_budget": model_max_budget_json,
            "budget_id": budget_id,
            "blocked": blocked,
            "created_by": created_by,
            "updated_by": updated_by,
            "allowed_routes": allowed_routes or [],
            "object_permission_id": object_permission_id,
        }

        if (
            get_secret("DISABLE_KEY_NAME", False) is True
        ):  # allow user to disable storing abbreviated key name (shown in UI, to help figure out which key spent how much)
            pass
        else:
            key_data["key_name"] = abbreviate_api_key(api_key=token)
        saved_token = copy.deepcopy(key_data)
        if isinstance(saved_token["aliases"], str):
            saved_token["aliases"] = json.loads(saved_token["aliases"])
        if isinstance(saved_token["config"], str):
            saved_token["config"] = json.loads(saved_token["config"])
        if isinstance(saved_token["metadata"], str):
            saved_token["metadata"] = json.loads(saved_token["metadata"])
        if isinstance(saved_token["permissions"], str):
            if (
                "get_spend_routes" in saved_token["permissions"]
                and premium_user is not True
            ):
                raise ValueError(
                    "get_spend_routes permission is only available for LiteLLM Enterprise users"
                )

            saved_token["permissions"] = json.loads(saved_token["permissions"])
        if isinstance(saved_token["model_max_budget"], str):
            saved_token["model_max_budget"] = json.loads(
                saved_token["model_max_budget"]
            )

        if saved_token.get("expires", None) is not None and isinstance(
            saved_token["expires"], datetime
        ):
            saved_token["expires"] = saved_token["expires"].isoformat()
        if prisma_client is not None:
            if (
                table_name is None or table_name == "user"
            ):  # do not auto-create users for `/key/generate`
                ## CREATE USER (If necessary)
                if query_type == "insert_data":
                    user_row = await prisma_client.insert_data(
                        data=user_data, table_name="user"
                    )

                    if user_row is None:
                        raise Exception("Failed to create user")
                    ## use default user model list if no key-specific model list provided
                    if len(user_row.models) > 0 and len(key_data["models"]) == 0:  # type: ignore
                        key_data["models"] = user_row.models  # type: ignore
                elif query_type == "update_data":
                    user_row = await prisma_client.update_data(
                        data=user_data,
                        table_name="user",
                        update_key_values=update_key_values,
                    )
            if user_id == litellm_proxy_budget_name or (
                table_name is not None and table_name == "user"
            ):
                # do not create a key for litellm_proxy_budget_name or if table name is set to just 'user'
                # we only need to ensure this exists in the user table
                # the LiteLLM_VerificationToken table will increase in size if we don't do this check
                return user_data

            ## CREATE KEY
            verbose_proxy_logger.debug("prisma_client: Creating Key= %s", key_data)
            create_key_response = await prisma_client.insert_data(
                data=key_data, table_name="key"
            )

            key_data["token_id"] = getattr(create_key_response, "token", None)
            key_data["litellm_budget_table"] = getattr(
                create_key_response, "litellm_budget_table", None
            )
            key_data["created_at"] = getattr(create_key_response, "created_at", None)
            key_data["updated_at"] = getattr(create_key_response, "updated_at", None)
    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.generate_key_helper_fn(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal Server Error."},
        )

    # Add budget related info in key_data - this ensures it's returned
    key_data["budget_id"] = budget_id

    if request_type == "user":
        # if this is a /user/new request update the key_date with user_data fields
        key_data.update(user_data)
    return key_data


async def _team_key_deletion_check(
    user_api_key_dict: UserAPIKeyAuth,
    key_info: LiteLLM_VerificationToken,
    prisma_client: PrismaClient,
    user_api_key_cache: DualCache,
):
    is_team_key = _is_team_key(data=key_info)

    if is_team_key and key_info.team_id is not None:
        team_table = await get_team_object(
            team_id=key_info.team_id,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            check_db_only=True,
        )
        if (
            litellm.key_generation_settings is not None
            and "team_key_generation" in litellm.key_generation_settings
        ):
            _team_key_generation = litellm.key_generation_settings[
                "team_key_generation"
            ]
        else:
            _team_key_generation = TeamUIKeyGenerationConfig(
                allowed_team_member_roles=["admin", "user"],
            )
        # check if user is team admin
        if team_table is not None:
            return _team_key_operation_team_member_check(
                assigned_user_id=user_api_key_dict.user_id,
                team_table=team_table,
                user_api_key_dict=user_api_key_dict,
                team_key_generation=_team_key_generation,
                route=KeyManagementRoutes.KEY_DELETE,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": f"Team not found in db, and user not proxy admin. Team id = {key_info.team_id}"
                },
            )
    return False


async def can_delete_verification_token(
    key_info: LiteLLM_VerificationToken,
    user_api_key_cache: DualCache,
    user_api_key_dict: UserAPIKeyAuth,
    prisma_client: PrismaClient,
) -> bool:
    """
    - check if user is proxy admin
    - check if user is team admin and key is a team key
    - check if key is personal key
    """
    is_team_key = _is_team_key(data=key_info)
    if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value:
        return True
    elif is_team_key and key_info.team_id is not None:
        return await _team_key_deletion_check(
            user_api_key_dict=user_api_key_dict,
            key_info=key_info,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
        )
    elif key_info.user_id is not None and key_info.user_id == user_api_key_dict.user_id:
        return True
    else:
        return False


async def delete_verification_tokens(
    tokens: List,
    user_api_key_cache: DualCache,
    user_api_key_dict: UserAPIKeyAuth,
) -> Tuple[Optional[Dict], List[LiteLLM_VerificationToken]]:
    """
    Helper that deletes the list of tokens from the database

    - check if user is proxy admin
    - check if user is team admin and key is a team key

    Args:
        tokens: List of tokens to delete
        user_id: Optional user_id to filter by

    Returns:
        Tuple[Optional[Dict], List[LiteLLM_VerificationToken]]:
            Optional[Dict]:
                - Number of deleted tokens
            List[LiteLLM_VerificationToken]:
                - List of keys being deleted, this contains information about the key_alias, token, and user_id being deleted,
                this is passed down to the KeyManagementEventHooks to delete the keys from the secret manager and handle audit logs
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client:
            tokens = [_hash_token_if_needed(token=key) for key in tokens]
            _keys_being_deleted: List[
                LiteLLM_VerificationToken
            ] = await prisma_client.db.litellm_verificationtoken.find_many(
                where={"token": {"in": tokens}}
            )

            if len(_keys_being_deleted) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": "No keys found"},
                )

            # Assuming 'db' is your Prisma Client instance
            # check if admin making request - don't filter by user-id
            if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value:
                deleted_tokens = await prisma_client.delete_data(tokens=tokens)
            # else
            else:
                tasks = []
                deleted_tokens = []
                for key in _keys_being_deleted:

                    async def _delete_key(key: LiteLLM_VerificationToken):
                        if await can_delete_verification_token(
                            key_info=key,
                            user_api_key_cache=user_api_key_cache,
                            user_api_key_dict=user_api_key_dict,
                            prisma_client=prisma_client,
                        ):
                            await prisma_client.delete_data(tokens=[key.token])
                            deleted_tokens.append(key.token)
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail={
                                    "error": "You are not authorized to delete this key"
                                },
                            )

                    tasks.append(_delete_key(key))
                await asyncio.gather(*tasks)

                _num_deleted_tokens = len(deleted_tokens)
                if _num_deleted_tokens != len(tokens):
                    failed_tokens = [
                        token for token in tokens if token not in deleted_tokens
                    ]
                    raise Exception(
                        "Failed to delete all tokens. Failed to delete tokens: "
                        + str(failed_tokens)
                    )
        else:
            raise Exception("DB not connected. prisma_client is None")
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.delete_verification_tokens(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        raise e

    for key in tokens:
        user_api_key_cache.delete_cache(key)
        # remove hash token from cache
        hashed_token = hash_token(cast(str, key))
        user_api_key_cache.delete_cache(hashed_token)

    return {"deleted_keys": deleted_tokens}, _keys_being_deleted


async def delete_key_aliases(
    key_aliases: List[str],
    user_api_key_cache: DualCache,
    prisma_client: PrismaClient,
    user_api_key_dict: UserAPIKeyAuth,
) -> Tuple[Optional[Dict], List[LiteLLM_VerificationToken]]:
    _keys_being_deleted = await prisma_client.db.litellm_verificationtoken.find_many(
        where={"key_alias": {"in": key_aliases}}
    )

    tokens = [key.token for key in _keys_being_deleted]
    return await delete_verification_tokens(
        tokens=tokens,
        user_api_key_cache=user_api_key_cache,
        user_api_key_dict=user_api_key_dict,
    )


async def _rotate_master_key(
    prisma_client: PrismaClient,
    user_api_key_dict: UserAPIKeyAuth,
    current_master_key: str,
    new_master_key: str,
) -> None:
    """
    Rotate the master key

    1. Get the values from the DB
        - Get models from DB
        - Get config from DB
    2. Decrypt the values
        - ModelTable
            - [{"model_name": "str", "litellm_params": {}}]
        - ConfigTable
    3. Encrypt the values with the new master key
    4. Update the values in the DB
    """
    from litellm.proxy.proxy_server import proxy_config

    try:
        models: Optional[
            List
        ] = await prisma_client.db.litellm_proxymodeltable.find_many()
    except Exception:
        models = None
    # 2. process model table
    if models:
        decrypted_models = proxy_config.decrypt_model_list_from_db(new_models=models)
        verbose_proxy_logger.info(
            "ABLE TO DECRYPT MODELS - len(decrypted_models): %s", len(decrypted_models)
        )
        new_models = []
        for model in decrypted_models:
            new_model = await _add_model_to_db(
                model_params=Deployment(**model),
                user_api_key_dict=user_api_key_dict,
                prisma_client=prisma_client,
                new_encryption_key=new_master_key,
                should_create_model_in_db=False,
            )
            if new_model:
                new_models.append(jsonify_object(new_model.model_dump()))
        verbose_proxy_logger.info("Resetting proxy model table")
        await prisma_client.db.litellm_proxymodeltable.delete_many()
        verbose_proxy_logger.info("Creating %s models", len(new_models))
        await prisma_client.db.litellm_proxymodeltable.create_many(
            data=new_models,
        )
    # 3. process config table
    try:
        config = await prisma_client.db.litellm_config.find_many()
    except Exception:
        config = None

    if config:
        """If environment_variables is found, decrypt it and encrypt it with the new master key"""
        environment_variables_dict = {}
        for c in config:
            if c.param_name == "environment_variables":
                environment_variables_dict = c.param_value

        if environment_variables_dict:
            decrypted_env_vars = proxy_config._decrypt_and_set_db_env_variables(
                environment_variables=environment_variables_dict
            )
            encrypted_env_vars = proxy_config._encrypt_env_variables(
                environment_variables=decrypted_env_vars,
                new_encryption_key=new_master_key,
            )

            if encrypted_env_vars:
                await prisma_client.db.litellm_config.update(
                    where={"param_name": "environment_variables"},
                    data={"param_value": jsonify_object(encrypted_env_vars)},
                )


@router.post(
    "/key/{key:path}/regenerate",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.post(
    "/key/regenerate",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def regenerate_key_fn(
    key: Optional[str] = None,
    data: Optional[RegenerateKeyRequest] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
) -> Optional[GenerateKeyResponse]:
    """
    Regenerate an existing API key while optionally updating its parameters.

    Parameters:
    - key: str (path parameter) - The key to regenerate
    - data: Optional[RegenerateKeyRequest] - Request body containing optional parameters to update
        - key_alias: Optional[str] - User-friendly key alias
        - user_id: Optional[str] - User ID associated with key
        - team_id: Optional[str] - Team ID associated with key
        - models: Optional[list] - Model_name's a user is allowed to call
        - tags: Optional[List[str]] - Tags for organizing keys (Enterprise only)
        - spend: Optional[float] - Amount spent by key
        - max_budget: Optional[float] - Max budget for key
        - model_max_budget: Optional[Dict[str, BudgetConfig]] - Model-specific budgets {"gpt-4": {"budget_limit": 0.0005, "time_period": "30d"}}
        - budget_duration: Optional[str] - Budget reset period ("30d", "1h", etc.)
        - soft_budget: Optional[float] - Soft budget limit (warning vs. hard stop). Will trigger a slack alert when this soft budget is reached.
        - max_parallel_requests: Optional[int] - Rate limit for parallel requests
        - metadata: Optional[dict] - Metadata for key. Example {"team": "core-infra", "app": "app2"}
        - tpm_limit: Optional[int] - Tokens per minute limit
        - rpm_limit: Optional[int] - Requests per minute limit
        - model_rpm_limit: Optional[dict] - Model-specific RPM limits {"gpt-4": 100, "claude-v1": 200}
        - model_tpm_limit: Optional[dict] - Model-specific TPM limits {"gpt-4": 100000, "claude-v1": 200000}
        - allowed_cache_controls: Optional[list] - List of allowed cache control values
        - duration: Optional[str] - Key validity duration ("30d", "1h", etc.)
        - permissions: Optional[dict] - Key-specific permissions
        - guardrails: Optional[List[str]] - List of active guardrails for the key
        - blocked: Optional[bool] - Whether the key is blocked


    Returns:
    - GenerateKeyResponse containing the new key and its updated parameters

    Example:
    ```bash
    curl --location --request POST 'http://localhost:4000/key/sk-1234/regenerate' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "max_budget": 100,
        "metadata": {"team": "core-infra"},
        "models": ["gpt-4", "gpt-3.5-turbo"]
    }'
    ```

    Note: This is an Enterprise feature. It requires a premium license to use.
    """
    try:
        from litellm.proxy.proxy_server import (
            hash_token,
            master_key,
            premium_user,
            prisma_client,
            proxy_logging_obj,
            user_api_key_cache,
        )

        is_master_key_regeneration = data and data.new_master_key is not None

        if (
            premium_user is not True and not is_master_key_regeneration
        ):  # allow master key regeneration for non-premium users
            raise ValueError(
                f"Regenerating Virtual Keys is an Enterprise feature, {CommonProxyErrors.not_premium_user.value}"
            )

        # Check if key exists, raise exception if key is not in the DB
        key = data.key if data and data.key else key
        if not key:
            raise HTTPException(status_code=400, detail={"error": "No key passed in."})
        ### 1. Create New copy that is duplicate of existing key
        ######################################################################

        # create duplicate of existing key
        # set token = new token generated
        # insert new token in DB

        # create hash of token
        if prisma_client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "DB not connected. prisma_client is None"},
            )

        _is_master_key_valid = _is_master_key(api_key=key, _master_key=master_key)

        if master_key is not None and data and _is_master_key_valid:
            if data.new_master_key is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "New master key is required."},
                )
            await _rotate_master_key(
                prisma_client=prisma_client,
                user_api_key_dict=user_api_key_dict,
                current_master_key=master_key,
                new_master_key=data.new_master_key,
            )
            return GenerateKeyResponse(
                key=data.new_master_key,
                token=data.new_master_key,
                key_name=data.new_master_key,
                expires=None,
            )

        if "sk" not in key:
            hashed_api_key = key
        else:
            hashed_api_key = hash_token(key)

        _key_in_db = await prisma_client.db.litellm_verificationtoken.find_unique(
            where={"token": hashed_api_key},
        )
        if _key_in_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Key {key} not found."},
            )

        # check if user has permission to regenerate key
        await TeamMemberPermissionChecks.can_team_member_execute_key_management_endpoint(
            user_api_key_dict=user_api_key_dict,
            route=KeyManagementRoutes.KEY_REGENERATE,
            prisma_client=prisma_client,
            existing_key_row=_key_in_db,
            user_api_key_cache=user_api_key_cache,
        )

        verbose_proxy_logger.debug("key_in_db: %s", _key_in_db)

        new_token = f"sk-{secrets.token_urlsafe(LENGTH_OF_LITELLM_GENERATED_KEY)}"
        new_token_hash = hash_token(new_token)
        new_token_key_name = f"sk-...{new_token[-4:]}"

        # Prepare the update data
        update_data = {
            "token": new_token_hash,
            "key_name": new_token_key_name,
        }

        non_default_values = {}
        if data is not None:
            # Update with any provided parameters from GenerateKeyRequest
            non_default_values = await prepare_key_update_data(
                data=data, existing_key_row=_key_in_db
            )
            verbose_proxy_logger.debug("non_default_values: %s", non_default_values)

        update_data.update(non_default_values)
        update_data = prisma_client.jsonify_object(data=update_data)
        # Update the token in the database
        updated_token = await prisma_client.db.litellm_verificationtoken.update(
            where={"token": hashed_api_key},
            data=update_data,  # type: ignore
        )

        updated_token_dict = {}
        if updated_token is not None:
            updated_token_dict = dict(updated_token)

        updated_token_dict["key"] = new_token
        updated_token_dict["token_id"] = updated_token_dict.pop("token")

        ### 3. remove existing key entry from cache
        ######################################################################
        if key:
            await _delete_cache_key_object(
                hashed_token=hash_token(key),
                user_api_key_cache=user_api_key_cache,
                proxy_logging_obj=proxy_logging_obj,
            )

        if hashed_api_key:
            await _delete_cache_key_object(
                hashed_token=hash_token(key),
                user_api_key_cache=user_api_key_cache,
                proxy_logging_obj=proxy_logging_obj,
            )

        response = GenerateKeyResponse(
            **updated_token_dict,
        )

        asyncio.create_task(
            KeyManagementEventHooks.async_key_rotated_hook(
                data=data,
                existing_key_row=_key_in_db,
                response=response,
                user_api_key_dict=user_api_key_dict,
                litellm_changed_by=litellm_changed_by,
            )
        )

        return response
    except Exception as e:
        verbose_proxy_logger.exception("Error regenerating key: %s", e)
        raise handle_exception_on_proxy(e)


async def validate_key_list_check(
    user_api_key_dict: UserAPIKeyAuth,
    user_id: Optional[str],
    team_id: Optional[str],
    organization_id: Optional[str],
    key_alias: Optional[str],
    key_hash: Optional[str],
    prisma_client: PrismaClient,
) -> Optional[LiteLLM_UserTable]:
    if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value:
        return None

    if user_api_key_dict.user_id is None:
        raise ProxyException(
            message="You are not authorized to access this endpoint. No 'user_id' is associated with your API key.",
            type=ProxyErrorTypes.bad_request_error,
            param="user_id",
            code=status.HTTP_403_FORBIDDEN,
        )
    complete_user_info_db_obj: Optional[
        BaseModel
    ] = await prisma_client.db.litellm_usertable.find_unique(
        where={"user_id": user_api_key_dict.user_id},
        include={"organization_memberships": True},
    )

    if complete_user_info_db_obj is None:
        raise ProxyException(
            message="You are not authorized to access this endpoint. No 'user_id' is associated with your API key.",
            type=ProxyErrorTypes.bad_request_error,
            param="user_id",
            code=status.HTTP_403_FORBIDDEN,
        )

    complete_user_info = LiteLLM_UserTable(**complete_user_info_db_obj.model_dump())

    # internal user can only see their own keys
    if user_id:
        if complete_user_info.user_id != user_id:
            raise ProxyException(
                message="You are not authorized to check another user's keys",
                type=ProxyErrorTypes.bad_request_error,
                param="user_id",
                code=status.HTTP_403_FORBIDDEN,
            )

    if team_id:
        if team_id not in complete_user_info.teams:
            raise ProxyException(
                message="You are not authorized to check this team's keys",
                type=ProxyErrorTypes.bad_request_error,
                param="team_id",
                code=status.HTTP_403_FORBIDDEN,
            )

    if organization_id:
        if (
            complete_user_info.organization_memberships is None
            or organization_id
            not in [
                membership.organization_id
                for membership in complete_user_info.organization_memberships
            ]
        ):
            raise ProxyException(
                message="You are not authorized to check this organization's keys",
                type=ProxyErrorTypes.bad_request_error,
                param="organization_id",
                code=status.HTTP_403_FORBIDDEN,
            )

    if key_hash:
        try:
            key_info = await prisma_client.db.litellm_verificationtoken.find_unique(
                where={"token": key_hash},
            )
        except Exception:
            raise ProxyException(
                message="Key Hash not found.",
                type=ProxyErrorTypes.bad_request_error,
                param="key_hash",
                code=status.HTTP_403_FORBIDDEN,
            )
        can_user_query_key_info = await _can_user_query_key_info(
            user_api_key_dict=user_api_key_dict,
            key=key_hash,
            key_info=key_info,
        )
        if not can_user_query_key_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this key's info. Your role={}".format(
                    user_api_key_dict.user_role
                ),
            )
    return complete_user_info


async def get_admin_team_ids(
    complete_user_info: Optional[LiteLLM_UserTable],
    user_api_key_dict: UserAPIKeyAuth,
    prisma_client: PrismaClient,
) -> List[str]:
    """
    Get all team IDs where the user is an admin.
    """
    if complete_user_info is None:
        return []
    # Get all teams that user is an admin of
    teams: Optional[
        List[BaseModel]
    ] = await prisma_client.db.litellm_teamtable.find_many(
        where={"team_id": {"in": complete_user_info.teams}}
    )
    if teams is None:
        return []

    teams_pydantic_obj = [LiteLLM_TeamTable(**team.model_dump()) for team in teams]

    admin_team_ids = [
        team.team_id
        for team in teams_pydantic_obj
        if _is_user_team_admin(user_api_key_dict=user_api_key_dict, team_obj=team)
    ]
    return admin_team_ids


@router.get(
    "/key/list",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def list_keys(
    request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    page: int = Query(1, description="Page number", ge=1),
    size: int = Query(10, description="Page size", ge=1, le=100),
    user_id: Optional[str] = Query(None, description="Filter keys by user ID"),
    team_id: Optional[str] = Query(None, description="Filter keys by team ID"),
    organization_id: Optional[str] = Query(
        None, description="Filter keys by organization ID"
    ),
    key_hash: Optional[str] = Query(None, description="Filter keys by key hash"),
    key_alias: Optional[str] = Query(None, description="Filter keys by key alias"),
    return_full_object: bool = Query(False, description="Return full key object"),
    include_team_keys: bool = Query(
        False, description="Include all keys for teams that user is an admin of."
    ),
    sort_by: Optional[str] = Query(
        default=None,
        description="Column to sort by (e.g. 'user_id', 'created_at', 'spend')",
    ),
    sort_order: str = Query(default="desc", description="Sort order ('asc' or 'desc')"),
) -> KeyListResponseObject:
    """
    List all keys for a given user / team / organization.

    Returns:
        {
            "keys": List[str] or List[UserAPIKeyAuth],
            "total_count": int,
            "current_page": int,
            "total_pages": int,
        }
    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        verbose_proxy_logger.debug("Entering list_keys function")

        if prisma_client is None:
            verbose_proxy_logger.error("Database not connected")
            raise Exception("Database not connected")

        complete_user_info = await validate_key_list_check(
            user_api_key_dict=user_api_key_dict,
            user_id=user_id,
            team_id=team_id,
            organization_id=organization_id,
            key_alias=key_alias,
            key_hash=key_hash,
            prisma_client=prisma_client,
        )

        if include_team_keys:
            admin_team_ids = await get_admin_team_ids(
                complete_user_info=complete_user_info,
                user_api_key_dict=user_api_key_dict,
                prisma_client=prisma_client,
            )
        else:
            admin_team_ids = None

        if user_id is None and user_api_key_dict.user_role not in [
            LitellmUserRoles.PROXY_ADMIN.value,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY.value,
        ]:
            user_id = user_api_key_dict.user_id

        response = await _list_key_helper(
            prisma_client=prisma_client,
            page=page,
            size=size,
            user_id=user_id,
            team_id=team_id,
            key_alias=key_alias,
            key_hash=key_hash,
            return_full_object=return_full_object,
            organization_id=organization_id,
            admin_team_ids=admin_team_ids,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        verbose_proxy_logger.debug("Successfully prepared response")

        return response

    except Exception as e:
        verbose_proxy_logger.exception(f"Error in list_keys: {e}")
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"error({str(e)})"),
                type=ProxyErrorTypes.internal_server_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.internal_server_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _validate_sort_params(
    sort_by: Optional[str], sort_order: str
) -> Optional[Dict[str, str]]:
    order_by: Dict[str, str] = {}

    if sort_by is None:
        return None
    # Validate sort_by is a valid column
    valid_columns = [
        "spend",
        "max_budget",
        "created_at",
        "updated_at",
        "token",
        "key_alias",
    ]
    if sort_by not in valid_columns:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid sort column. Must be one of: {', '.join(valid_columns)}"
            },
        )

    # Validate sort_order
    if sort_order.lower() not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid sort order. Must be 'asc' or 'desc'"},
        )

    order_by[sort_by] = sort_order.lower()

    return order_by


async def _list_key_helper(
    prisma_client: PrismaClient,
    page: int,
    size: int,
    user_id: Optional[str],
    team_id: Optional[str],
    organization_id: Optional[str],
    key_alias: Optional[str],
    key_hash: Optional[str],
    exclude_team_id: Optional[str] = None,
    return_full_object: bool = False,
    admin_team_ids: Optional[
        List[str]
    ] = None,  # New parameter for teams where user is admin
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> KeyListResponseObject:
    """
    Helper function to list keys
    Args:
        page: int
        size: int
        user_id: Optional[str]
        team_id: Optional[str]
        key_alias: Optional[str]
        exclude_team_id: Optional[str] # exclude a specific team_id
        return_full_object: bool # when true, will return UserAPIKeyAuth objects instead of just the token
        admin_team_ids: Optional[List[str]] # list of team IDs where the user is an admin

    Returns:
        KeyListResponseObject
        {
            "keys": List[str] or List[UserAPIKeyAuth],  # Updated to reflect possible return types
            "total_count": int,
            "current_page": int,
            "total_pages": int,
        }
    """
    # Prepare filter conditions
    where: Dict[str, Union[str, Dict[str, Any], List[Dict[str, Any]]]] = {}
    where.update(_get_condition_to_filter_out_ui_session_tokens())

    # Build the OR conditions for user's keys and admin team keys
    or_conditions: List[Dict[str, Any]] = []

    # Base conditions for user's own keys
    user_condition: Dict[str, Any] = {}
    if user_id and isinstance(user_id, str):
        user_condition["user_id"] = user_id
    if team_id and isinstance(team_id, str):
        user_condition["team_id"] = team_id
    if key_alias and isinstance(key_alias, str):
        user_condition["key_alias"] = key_alias
    if exclude_team_id and isinstance(exclude_team_id, str):
        user_condition["team_id"] = {"not": exclude_team_id}
    if organization_id and isinstance(organization_id, str):
        user_condition["organization_id"] = organization_id
    if key_hash and isinstance(key_hash, str):
        user_condition["token"] = key_hash

    if user_condition:
        or_conditions.append(user_condition)

    # Add condition for admin team keys if provided
    if admin_team_ids:
        or_conditions.append({"team_id": {"in": admin_team_ids}})

    # Combine conditions with OR if we have multiple conditions
    if len(or_conditions) > 1:
        where = {"AND": [where, {"OR": or_conditions}]}
    elif len(or_conditions) == 1:
        where.update(or_conditions[0])

    verbose_proxy_logger.debug(f"Filter conditions: {where}")

    # Calculate skip for pagination
    skip = (page - 1) * size

    verbose_proxy_logger.debug(f"Pagination: skip={skip}, take={size}")

    order_by: Optional[Dict[str, str]] = (
        _validate_sort_params(sort_by, sort_order)
        if sort_by is not None and isinstance(sort_by, str)
        else None
    )

    # Fetch keys with pagination
    keys = await prisma_client.db.litellm_verificationtoken.find_many(
        where=where,  # type: ignore
        skip=skip,  # type: ignore
        take=size,  # type: ignore
        order=order_by
        if order_by
        else [
            {"created_at": "desc"},
            {"token": "desc"},  # fallback sort
        ],
        include={"object_permission": True},
    )

    verbose_proxy_logger.debug(f"Fetched {len(keys)} keys")

    # Get total count of keys
    total_count = await prisma_client.db.litellm_verificationtoken.count(
        where=where  # type: ignore
    )

    verbose_proxy_logger.debug(f"Total count of keys: {total_count}")

    # Calculate total pages
    total_pages = -(-total_count // size)  # Ceiling division

    # Prepare response
    key_list: List[Union[str, UserAPIKeyAuth]] = []
    for key in keys:
        if return_full_object is True:
            key_list.append(UserAPIKeyAuth(**key.dict()))  # Return full key object
        else:
            _token = key.dict().get("token")
            key_list.append(_token)  # Return only the token

    return KeyListResponseObject(
        keys=key_list,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
    )


def _get_condition_to_filter_out_ui_session_tokens() -> Dict[str, Any]:
    """
    Condition to filter out UI session tokens
    """
    return {
        "OR": [
            {"team_id": None},  # Include records where team_id is null
            {
                "team_id": {"not": UI_SESSION_TOKEN_TEAM_ID}
            },  # Include records where team_id != UI_SESSION_TOKEN_TEAM_ID
        ]
    }


@router.post(
    "/key/block", tags=["key management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def block_key(
    data: BlockKeyRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
) -> Optional[LiteLLM_VerificationToken]:
    """
    Block an Virtual key from making any requests.

    Parameters:
    - key: str - The key to block. Can be either the unhashed key (sk-...) or the hashed key value

     Example:
    ```bash
    curl --location 'http://0.0.0.0:4000/key/block' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "key": "sk-Fn8Ej39NxjAXrvpUGKghGw"
    }'
    ```

    Note: This is an admin-only endpoint. Only proxy admins can block keys.
    """
    from litellm.proxy.proxy_server import (
        create_audit_log_for_update,
        hash_token,
        litellm_proxy_admin_name,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise Exception("{}".format(CommonProxyErrors.db_not_connected_error.value))

    if data.key.startswith("sk-"):
        hashed_token = hash_token(token=data.key)
    else:
        hashed_token = data.key

    if litellm.store_audit_logs is True:
        # make an audit log for key update
        record = await prisma_client.db.litellm_verificationtoken.find_unique(
            where={"token": hashed_token}
        )
        if record is None:
            raise ProxyException(
                message=f"Key {data.key} not found",
                type=ProxyErrorTypes.bad_request_error,
                param="key",
                code=status.HTTP_404_NOT_FOUND,
            )
        asyncio.create_task(
            create_audit_log_for_update(
                request_data=LiteLLM_AuditLogs(
                    id=str(uuid.uuid4()),
                    updated_at=datetime.now(timezone.utc),
                    changed_by=litellm_changed_by
                    or user_api_key_dict.user_id
                    or litellm_proxy_admin_name,
                    changed_by_api_key=user_api_key_dict.api_key,
                    table_name=LitellmTableNames.KEY_TABLE_NAME,
                    object_id=hashed_token,
                    action="blocked",
                    updated_values="{}",
                    before_value=record.model_dump_json(),
                )
            )
        )

    record = await prisma_client.db.litellm_verificationtoken.update(
        where={"token": hashed_token}, data={"blocked": True}  # type: ignore
    )

    ## UPDATE KEY CACHE

    ### get cached object ###
    key_object = await get_key_object(
        hashed_token=hashed_token,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        parent_otel_span=None,
        proxy_logging_obj=proxy_logging_obj,
    )

    ### update cached object ###
    key_object.blocked = True

    ### store cached object ###
    await _cache_key_object(
        hashed_token=hashed_token,
        user_api_key_obj=key_object,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )

    return record


@router.post(
    "/key/unblock", tags=["key management"], dependencies=[Depends(user_api_key_auth)]
)
@management_endpoint_wrapper
async def unblock_key(
    data: BlockKeyRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Unblock a Virtual key to allow it to make requests again.

    Parameters:
    - key: str - The key to unblock. Can be either the unhashed key (sk-...) or the hashed key value

    Example:
    ```bash
    curl --location 'http://0.0.0.0:4000/key/unblock' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "key": "sk-Fn8Ej39NxjAXrvpUGKghGw"
    }'
    ```

    Note: This is an admin-only endpoint. Only proxy admins can unblock keys.
    """
    from litellm.proxy.proxy_server import (
        create_audit_log_for_update,
        hash_token,
        litellm_proxy_admin_name,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if prisma_client is None:
        raise Exception("{}".format(CommonProxyErrors.db_not_connected_error.value))

    if data.key.startswith("sk-"):
        hashed_token = hash_token(token=data.key)
    else:
        hashed_token = data.key

    if litellm.store_audit_logs is True:
        # make an audit log for key update
        record = await prisma_client.db.litellm_verificationtoken.find_unique(
            where={"token": hashed_token}
        )
        if record is None:
            raise ProxyException(
                message=f"Key {data.key} not found",
                type=ProxyErrorTypes.bad_request_error,
                param="key",
                code=status.HTTP_404_NOT_FOUND,
            )
        asyncio.create_task(
            create_audit_log_for_update(
                request_data=LiteLLM_AuditLogs(
                    id=str(uuid.uuid4()),
                    updated_at=datetime.now(timezone.utc),
                    changed_by=litellm_changed_by
                    or user_api_key_dict.user_id
                    or litellm_proxy_admin_name,
                    changed_by_api_key=user_api_key_dict.api_key,
                    table_name=LitellmTableNames.KEY_TABLE_NAME,
                    object_id=hashed_token,
                    action="blocked",
                    updated_values="{}",
                    before_value=record.model_dump_json(),
                )
            )
        )

    record = await prisma_client.db.litellm_verificationtoken.update(
        where={"token": hashed_token}, data={"blocked": False}  # type: ignore
    )

    ## UPDATE KEY CACHE

    ### get cached object ###
    key_object = await get_key_object(
        hashed_token=hashed_token,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
        parent_otel_span=None,
        proxy_logging_obj=proxy_logging_obj,
    )

    ### update cached object ###
    key_object.blocked = False

    ### store cached object ###
    await _cache_key_object(
        hashed_token=hashed_token,
        user_api_key_obj=key_object,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )

    return record


@router.post(
    "/key/health",
    tags=["key management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=KeyHealthResponse,
)
@management_endpoint_wrapper
async def key_health(
    request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Check the health of the key

    Checks:
    - If key based logging is configured correctly - sends a test log

    Usage 

    Pass the key in the request header

    ```bash
    curl -X POST "http://localhost:4000/key/health" \
     -H "Authorization: Bearer sk-1234" \
     -H "Content-Type: application/json"
    ```

    Response when logging callbacks are setup correctly:

    ```json
    {
      "key": "healthy",
      "logging_callbacks": {
        "callbacks": [
          "gcs_bucket"
        ],
        "status": "healthy",
        "details": "No logger exceptions triggered, system is healthy. Manually check if logs were sent to ['gcs_bucket']"
      }
    }
    ```


    Response when logging callbacks are not setup correctly:
    ```json
    {
      "key": "unhealthy",
      "logging_callbacks": {
        "callbacks": [
          "gcs_bucket"
        ],
        "status": "unhealthy",
        "details": "Logger exceptions triggered, system is unhealthy: Failed to load vertex credentials. Check to see if credentials containing partial/invalid information."
      }
    }
    ```
    """
    try:
        # Get the key's metadata
        key_metadata = user_api_key_dict.metadata

        health_status: KeyHealthResponse = KeyHealthResponse(
            key="healthy",
            logging_callbacks=None,
        )

        # Check if logging is configured in metadata
        if key_metadata and "logging" in key_metadata:
            logging_statuses = await test_key_logging(
                user_api_key_dict=user_api_key_dict,
                request=request,
                key_logging=key_metadata["logging"],
            )
            health_status["logging_callbacks"] = logging_statuses

            # Check if any logging callback is unhealthy
            if logging_statuses.get("status") == "unhealthy":
                health_status["key"] = "unhealthy"

        return KeyHealthResponse(**health_status)

    except Exception as e:
        raise ProxyException(
            message=f"Key health check failed: {str(e)}",
            type=ProxyErrorTypes.internal_server_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _can_user_query_key_info(
    user_api_key_dict: UserAPIKeyAuth,
    key: Optional[str],
    key_info: LiteLLM_VerificationToken,
) -> bool:
    """
    Helper to check if the user has access to the key's info
    """
    if (
        user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN.value
        or user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY.value
    ):
        return True
    elif user_api_key_dict.api_key == key:
        return True
    # user can query their own key info
    elif key_info.user_id == user_api_key_dict.user_id:
        return True
    elif await TeamMemberPermissionChecks.user_belongs_to_keys_team(
        user_api_key_dict=user_api_key_dict,
        existing_key_row=key_info,
    ):
        return True
    return False


async def test_key_logging(
    user_api_key_dict: UserAPIKeyAuth,
    request: Request,
    key_logging: List[Dict[str, Any]],
) -> LoggingCallbackStatus:
    """
    Test the key-based logging

    - Test that key logging is correctly formatted and all args are passed correctly
    - Make a mock completion call -> user can check if it's correctly logged
    - Check if any logger.exceptions were triggered -> if they were then returns it to the user client side
    """
    import logging
    from io import StringIO

    from litellm.proxy.litellm_pre_call_utils import add_litellm_data_to_request
    from litellm.proxy.proxy_server import general_settings, proxy_config

    logging_callbacks: List[str] = []
    for callback in key_logging:
        if callback.get("callback_name") is not None:
            logging_callbacks.append(callback["callback_name"])
        else:
            raise ValueError("callback_name is required in key_logging")

    log_capture_string = StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.ERROR)
    logger = logging.getLogger()
    logger.addHandler(ch)

    try:
        data = {
            "model": "openai/litellm-key-health-test",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, this is a test from litellm /key/health. No LLM API call was made for this",
                }
            ],
            "mock_response": "test response",
        }
        data = await add_litellm_data_to_request(
            data=data,
            user_api_key_dict=user_api_key_dict,
            proxy_config=proxy_config,
            general_settings=general_settings,
            request=request,
        )
        await litellm.acompletion(
            **data
        )  # make mock completion call to trigger key based callbacks
    except Exception as e:
        return LoggingCallbackStatus(
            callbacks=logging_callbacks,
            status="unhealthy",
            details=f"Logging test failed: {str(e)}",
        )

    await asyncio.sleep(
        2
    )  # wait for callbacks to run, callbacks use batching so wait for the flush event

    # Check if any logger exceptions were triggered
    log_contents = log_capture_string.getvalue()
    logger.removeHandler(ch)
    if log_contents:
        return LoggingCallbackStatus(
            callbacks=logging_callbacks,
            status="unhealthy",
            details=f"Logger exceptions triggered, system is unhealthy: {log_contents}",
        )
    else:
        return LoggingCallbackStatus(
            callbacks=logging_callbacks,
            status="healthy",
            details=f"No logger exceptions triggered, system is healthy. Manually check if logs were sent to {logging_callbacks} ",
        )


async def _enforce_unique_key_alias(
    key_alias: Optional[str],
    prisma_client: Any,
    existing_key_token: Optional[str] = None,
) -> None:
    """
    Helper to enforce unique key aliases across all keys.

    Args:
        key_alias (Optional[str]): The key alias to check
        prisma_client (Any): Prisma client instance
        existing_key_token (Optional[str]): ID of existing key being updated, to exclude from uniqueness check
            (The Admin UI passes key_alias, in all Edit key requests. So we need to be sure that if we find a key with the same alias, it's not the same key we're updating)

    Raises:
        ProxyException: If key alias already exists on a different key
    """
    if key_alias is not None and prisma_client is not None:
        where_clause: dict[str, Any] = {"key_alias": key_alias}
        if existing_key_token:
            # Exclude the current key from the uniqueness check
            where_clause["NOT"] = {"token": existing_key_token}

        existing_key = await prisma_client.db.litellm_verificationtoken.find_first(
            where=where_clause
        )
        if existing_key is not None:
            raise ProxyException(
                message=f"Key with alias '{key_alias}' already exists. Unique key aliases across all keys are required.",
                type=ProxyErrorTypes.bad_request_error,
                param="key_alias",
                code=status.HTTP_400_BAD_REQUEST,
            )


def validate_model_max_budget(model_max_budget: Optional[Dict]) -> None:
    """
    Validate the model_max_budget is GenericBudgetConfigType + enforce user has an enterprise license

    Raises:
        Exception: If model_max_budget is not a valid GenericBudgetConfigType
    """
    try:
        if model_max_budget is None:
            return
        if len(model_max_budget) == 0:
            return
        if model_max_budget is not None:
            from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

            if premium_user is not True:
                raise ValueError(
                    f"You must have an enterprise license to set model_max_budget. {CommonProxyErrors.not_premium_user.value}"
                )
            for _model, _budget_info in model_max_budget.items():
                assert isinstance(_model, str)

                # /CRUD endpoints can pass budget_limit as a string, so we need to convert it to a float
                if "budget_limit" in _budget_info:
                    _budget_info["budget_limit"] = float(_budget_info["budget_limit"])
                BudgetConfig(**_budget_info)
    except Exception as e:
        raise ValueError(
            f"Invalid model_max_budget: {str(e)}. Example of valid model_max_budget: https://docs.litellm.ai/docs/proxy/users"
        )

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_generate_schema.py ===
"""Convert python types to pydantic-core schema."""

from __future__ import annotations as _annotations

import collections.abc
import dataclasses
import datetime
import inspect
import os
import pathlib
import re
import sys
import typing
import warnings
from collections.abc import Generator, Iterable, Iterator, Mapping
from contextlib import contextmanager
from copy import copy
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import partial
from inspect import Parameter, _ParameterKind, signature
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from itertools import chain
from operator import attrgetter
from types import FunctionType, GenericAlias, LambdaType, MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    ForwardRef,
    Literal,
    TypeVar,
    Union,
    cast,
    overload,
)
from uuid import UUID
from warnings import warn
from zoneinfo import ZoneInfo

import typing_extensions
from pydantic_core import (
    CoreSchema,
    MultiHostUrl,
    PydanticCustomError,
    PydanticSerializationUnexpectedValue,
    PydanticUndefined,
    Url,
    core_schema,
    to_jsonable_python,
)
from typing_extensions import TypeAlias, TypeAliasType, TypedDict, get_args, get_origin, is_typeddict
from typing_inspection import typing_objects
from typing_inspection.introspection import AnnotationSource, get_literal_values, is_union_origin

from ..aliases import AliasChoices, AliasGenerator, AliasPath
from ..annotated_handlers import GetCoreSchemaHandler, GetJsonSchemaHandler
from ..config import ConfigDict, JsonDict, JsonEncoder, JsonSchemaExtraCallable
from ..errors import PydanticSchemaGenerationError, PydanticUndefinedAnnotation, PydanticUserError
from ..functional_validators import AfterValidator, BeforeValidator, FieldValidatorModes, PlainValidator, WrapValidator
from ..json_schema import JsonSchemaValue
from ..version import version_short
from ..warnings import PydanticDeprecatedSince20
from . import _decorators, _discriminated_union, _known_annotated_metadata, _repr, _typing_extra
from ._config import ConfigWrapper, ConfigWrapperStack
from ._core_metadata import CoreMetadata, update_core_metadata
from ._core_utils import (
    get_ref,
    get_type_ref,
    is_list_like_schema_with_items_schema,
    validate_core_schema,
)
from ._decorators import (
    Decorator,
    DecoratorInfos,
    FieldSerializerDecoratorInfo,
    FieldValidatorDecoratorInfo,
    ModelSerializerDecoratorInfo,
    ModelValidatorDecoratorInfo,
    RootValidatorDecoratorInfo,
    ValidatorDecoratorInfo,
    get_attribute_from_bases,
    inspect_field_serializer,
    inspect_model_serializer,
    inspect_validator,
)
from ._docs_extraction import extract_docstrings_from_cls
from ._fields import (
    collect_dataclass_fields,
    rebuild_dataclass_fields,
    rebuild_model_fields,
    takes_validated_data_argument,
)
from ._forward_ref import PydanticRecursiveRef
from ._generics import get_standard_typevars_map, replace_types
from ._import_utils import import_cached_base_model, import_cached_field_info
from ._mock_val_ser import MockCoreSchema
from ._namespace_utils import NamespacesTuple, NsResolver
from ._schema_gather import MissingDefinitionError, gather_schemas_for_cleaning
from ._schema_generation_shared import CallbackGetCoreSchemaHandler
from ._utils import lenient_issubclass, smart_deepcopy

if TYPE_CHECKING:
    from ..fields import ComputedFieldInfo, FieldInfo
    from ..main import BaseModel
    from ..types import Discriminator
    from ._dataclasses import StandardDataclass
    from ._schema_generation_shared import GetJsonSchemaFunction

_SUPPORTS_TYPEDDICT = sys.version_info >= (3, 12)

FieldDecoratorInfo = Union[ValidatorDecoratorInfo, FieldValidatorDecoratorInfo, FieldSerializerDecoratorInfo]
FieldDecoratorInfoType = TypeVar('FieldDecoratorInfoType', bound=FieldDecoratorInfo)
AnyFieldDecorator = Union[
    Decorator[ValidatorDecoratorInfo],
    Decorator[FieldValidatorDecoratorInfo],
    Decorator[FieldSerializerDecoratorInfo],
]

ModifyCoreSchemaWrapHandler: TypeAlias = GetCoreSchemaHandler
GetCoreSchemaFunction: TypeAlias = Callable[[Any, ModifyCoreSchemaWrapHandler], core_schema.CoreSchema]
ParametersCallback: TypeAlias = "Callable[[int, str, Any], Literal['skip'] | None]"

TUPLE_TYPES: list[type] = [typing.Tuple, tuple]  # noqa: UP006
LIST_TYPES: list[type] = [typing.List, list, collections.abc.MutableSequence]  # noqa: UP006
SET_TYPES: list[type] = [typing.Set, set, collections.abc.MutableSet]  # noqa: UP006
FROZEN_SET_TYPES: list[type] = [typing.FrozenSet, frozenset, collections.abc.Set]  # noqa: UP006
DICT_TYPES: list[type] = [typing.Dict, dict]  # noqa: UP006
IP_TYPES: list[type] = [IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network]
SEQUENCE_TYPES: list[type] = [typing.Sequence, collections.abc.Sequence]
ITERABLE_TYPES: list[type] = [typing.Iterable, collections.abc.Iterable, typing.Generator, collections.abc.Generator]
TYPE_TYPES: list[type] = [typing.Type, type]  # noqa: UP006
PATTERN_TYPES: list[type] = [typing.Pattern, re.Pattern]
PATH_TYPES: list[type] = [
    os.PathLike,
    pathlib.Path,
    pathlib.PurePath,
    pathlib.PosixPath,
    pathlib.PurePosixPath,
    pathlib.PureWindowsPath,
]
MAPPING_TYPES = [
    typing.Mapping,
    typing.MutableMapping,
    collections.abc.Mapping,
    collections.abc.MutableMapping,
    collections.OrderedDict,
    typing_extensions.OrderedDict,
    typing.DefaultDict,  # noqa: UP006
    collections.defaultdict,
]
COUNTER_TYPES = [collections.Counter, typing.Counter]
DEQUE_TYPES: list[type] = [collections.deque, typing.Deque]  # noqa: UP006

# Note: This does not play very well with type checkers. For example,
# `a: LambdaType = lambda x: x` will raise a type error by Pyright.
ValidateCallSupportedTypes = Union[
    LambdaType,
    FunctionType,
    MethodType,
    partial,
]

VALIDATE_CALL_SUPPORTED_TYPES = get_args(ValidateCallSupportedTypes)

_mode_to_validator: dict[
    FieldValidatorModes, type[BeforeValidator | AfterValidator | PlainValidator | WrapValidator]
] = {'before': BeforeValidator, 'after': AfterValidator, 'plain': PlainValidator, 'wrap': WrapValidator}


def check_validator_fields_against_field_name(
    info: FieldDecoratorInfo,
    field: str,
) -> bool:
    """Check if field name is in validator fields.

    Args:
        info: The field info.
        field: The field name to check.

    Returns:
        `True` if field name is in validator fields, `False` otherwise.
    """
    fields = info.fields
    return '*' in fields or field in fields


def check_decorator_fields_exist(decorators: Iterable[AnyFieldDecorator], fields: Iterable[str]) -> None:
    """Check if the defined fields in decorators exist in `fields` param.

    It ignores the check for a decorator if the decorator has `*` as field or `check_fields=False`.

    Args:
        decorators: An iterable of decorators.
        fields: An iterable of fields name.

    Raises:
        PydanticUserError: If one of the field names does not exist in `fields` param.
    """
    fields = set(fields)
    for dec in decorators:
        if '*' in dec.info.fields:
            continue
        if dec.info.check_fields is False:
            continue
        for field in dec.info.fields:
            if field not in fields:
                raise PydanticUserError(
                    f'Decorators defined with incorrect fields: {dec.cls_ref}.{dec.cls_var_name}'
                    " (use check_fields=False if you're inheriting from the model and intended this)",
                    code='decorator-missing-field',
                )


def filter_field_decorator_info_by_field(
    validator_functions: Iterable[Decorator[FieldDecoratorInfoType]], field: str
) -> list[Decorator[FieldDecoratorInfoType]]:
    return [dec for dec in validator_functions if check_validator_fields_against_field_name(dec.info, field)]


def apply_each_item_validators(
    schema: core_schema.CoreSchema,
    each_item_validators: list[Decorator[ValidatorDecoratorInfo]],
    field_name: str | None,
) -> core_schema.CoreSchema:
    # This V1 compatibility shim should eventually be removed

    # fail early if each_item_validators is empty
    if not each_item_validators:
        return schema

    # push down any `each_item=True` validators
    # note that this won't work for any Annotated types that get wrapped by a function validator
    # but that's okay because that didn't exist in V1
    if schema['type'] == 'nullable':
        schema['schema'] = apply_each_item_validators(schema['schema'], each_item_validators, field_name)
        return schema
    elif schema['type'] == 'tuple':
        if (variadic_item_index := schema.get('variadic_item_index')) is not None:
            schema['items_schema'][variadic_item_index] = apply_validators(
                schema['items_schema'][variadic_item_index],
                each_item_validators,
                field_name,
            )
    elif is_list_like_schema_with_items_schema(schema):
        inner_schema = schema.get('items_schema', core_schema.any_schema())
        schema['items_schema'] = apply_validators(inner_schema, each_item_validators, field_name)
    elif schema['type'] == 'dict':
        inner_schema = schema.get('values_schema', core_schema.any_schema())
        schema['values_schema'] = apply_validators(inner_schema, each_item_validators, field_name)
    else:
        raise TypeError(
            f'`@validator(..., each_item=True)` cannot be applied to fields with a schema of {schema["type"]}'
        )
    return schema


def _extract_json_schema_info_from_field_info(
    info: FieldInfo | ComputedFieldInfo,
) -> tuple[JsonDict | None, JsonDict | JsonSchemaExtraCallable | None]:
    json_schema_updates = {
        'title': info.title,
        'description': info.description,
        'deprecated': bool(info.deprecated) or info.deprecated == '' or None,
        'examples': to_jsonable_python(info.examples),
    }
    json_schema_updates = {k: v for k, v in json_schema_updates.items() if v is not None}
    return (json_schema_updates or None, info.json_schema_extra)


JsonEncoders = dict[type[Any], JsonEncoder]


def _add_custom_serialization_from_json_encoders(
    json_encoders: JsonEncoders | None, tp: Any, schema: CoreSchema
) -> CoreSchema:
    """Iterate over the json_encoders and add the first matching encoder to the schema.

    Args:
        json_encoders: A dictionary of types and their encoder functions.
        tp: The type to check for a matching encoder.
        schema: The schema to add the encoder to.
    """
    if not json_encoders:
        return schema
    if 'serialization' in schema:
        return schema
    # Check the class type and its superclasses for a matching encoder
    # Decimal.__class__.__mro__ (and probably other cases) doesn't include Decimal itself
    # if the type is a GenericAlias (e.g. from list[int]) we need to use __class__ instead of .__mro__
    for base in (tp, *getattr(tp, '__mro__', tp.__class__.__mro__)[:-1]):
        encoder = json_encoders.get(base)
        if encoder is None:
            continue

        warnings.warn(
            f'`json_encoders` is deprecated. See https://docs.pydantic.dev/{version_short()}/concepts/serialization/#custom-serializers for alternatives',
            PydanticDeprecatedSince20,
        )

        # TODO: in theory we should check that the schema accepts a serialization key
        schema['serialization'] = core_schema.plain_serializer_function_ser_schema(encoder, when_used='json')
        return schema

    return schema


def _get_first_non_null(a: Any, b: Any) -> Any:
    """Return the first argument if it is not None, otherwise return the second argument.

    Use case: serialization_alias (argument a) and alias (argument b) are both defined, and serialization_alias is ''.
    This function will return serialization_alias, which is the first argument, even though it is an empty string.
    """
    return a if a is not None else b


class InvalidSchemaError(Exception):
    """The core schema is invalid."""


class GenerateSchema:
    """Generate core schema for a Pydantic model, dataclass and types like `str`, `datetime`, ... ."""

    __slots__ = (
        '_config_wrapper_stack',
        '_ns_resolver',
        '_typevars_map',
        'field_name_stack',
        'model_type_stack',
        'defs',
    )

    def __init__(
        self,
        config_wrapper: ConfigWrapper,
        ns_resolver: NsResolver | None = None,
        typevars_map: Mapping[TypeVar, Any] | None = None,
    ) -> None:
        # we need a stack for recursing into nested models
        self._config_wrapper_stack = ConfigWrapperStack(config_wrapper)
        self._ns_resolver = ns_resolver or NsResolver()
        self._typevars_map = typevars_map
        self.field_name_stack = _FieldNameStack()
        self.model_type_stack = _ModelTypeStack()
        self.defs = _Definitions()

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        warnings.warn(
            'Subclassing `GenerateSchema` is not supported. The API is highly subject to change in minor versions.',
            UserWarning,
            stacklevel=2,
        )

    @property
    def _config_wrapper(self) -> ConfigWrapper:
        return self._config_wrapper_stack.tail

    @property
    def _types_namespace(self) -> NamespacesTuple:
        return self._ns_resolver.types_namespace

    @property
    def _arbitrary_types(self) -> bool:
        return self._config_wrapper.arbitrary_types_allowed

    # the following methods can be overridden but should be considered
    # unstable / private APIs
    def _list_schema(self, items_type: Any) -> CoreSchema:
        return core_schema.list_schema(self.generate_schema(items_type))

    def _dict_schema(self, keys_type: Any, values_type: Any) -> CoreSchema:
        return core_schema.dict_schema(self.generate_schema(keys_type), self.generate_schema(values_type))

    def _set_schema(self, items_type: Any) -> CoreSchema:
        return core_schema.set_schema(self.generate_schema(items_type))

    def _frozenset_schema(self, items_type: Any) -> CoreSchema:
        return core_schema.frozenset_schema(self.generate_schema(items_type))

    def _enum_schema(self, enum_type: type[Enum]) -> CoreSchema:
        cases: list[Any] = list(enum_type.__members__.values())

        enum_ref = get_type_ref(enum_type)
        description = None if not enum_type.__doc__ else inspect.cleandoc(enum_type.__doc__)
        if (
            description == 'An enumeration.'
        ):  # This is the default value provided by enum.EnumMeta.__new__; don't use it
            description = None
        js_updates = {'title': enum_type.__name__, 'description': description}
        js_updates = {k: v for k, v in js_updates.items() if v is not None}

        sub_type: Literal['str', 'int', 'float'] | None = None
        if issubclass(enum_type, int):
            sub_type = 'int'
            value_ser_type: core_schema.SerSchema = core_schema.simple_ser_schema('int')
        elif issubclass(enum_type, str):
            # this handles `StrEnum` (3.11 only), and also `Foobar(str, Enum)`
            sub_type = 'str'
            value_ser_type = core_schema.simple_ser_schema('str')
        elif issubclass(enum_type, float):
            sub_type = 'float'
            value_ser_type = core_schema.simple_ser_schema('float')
        else:
            # TODO this is an ugly hack, how do we trigger an Any schema for serialization?
            value_ser_type = core_schema.plain_serializer_function_ser_schema(lambda x: x)

        if cases:

            def get_json_schema(schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
                json_schema = handler(schema)
                original_schema = handler.resolve_ref_schema(json_schema)
                original_schema.update(js_updates)
                return json_schema

            # we don't want to add the missing to the schema if it's the default one
            default_missing = getattr(enum_type._missing_, '__func__', None) is Enum._missing_.__func__  # pyright: ignore[reportFunctionMemberAccess]
            enum_schema = core_schema.enum_schema(
                enum_type,
                cases,
                sub_type=sub_type,
                missing=None if default_missing else enum_type._missing_,
                ref=enum_ref,
                metadata={'pydantic_js_functions': [get_json_schema]},
            )

            if self._config_wrapper.use_enum_values:
                enum_schema = core_schema.no_info_after_validator_function(
                    attrgetter('value'), enum_schema, serialization=value_ser_type
                )

            return enum_schema

        else:

            def get_json_schema_no_cases(_, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
                json_schema = handler(core_schema.enum_schema(enum_type, cases, sub_type=sub_type, ref=enum_ref))
                original_schema = handler.resolve_ref_schema(json_schema)
                original_schema.update(js_updates)
                return json_schema

            # Use an isinstance check for enums with no cases.
            # The most important use case for this is creating TypeVar bounds for generics that should
            # be restricted to enums. This is more consistent than it might seem at first, since you can only
            # subclass enum.Enum (or subclasses of enum.Enum) if all parent classes have no cases.
            # We use the get_json_schema function when an Enum subclass has been declared with no cases
            # so that we can still generate a valid json schema.
            return core_schema.is_instance_schema(
                enum_type,
                metadata={'pydantic_js_functions': [get_json_schema_no_cases]},
            )

    def _ip_schema(self, tp: Any) -> CoreSchema:
        from ._validators import IP_VALIDATOR_LOOKUP, IpType

        ip_type_json_schema_format: dict[type[IpType], str] = {
            IPv4Address: 'ipv4',
            IPv4Network: 'ipv4network',
            IPv4Interface: 'ipv4interface',
            IPv6Address: 'ipv6',
            IPv6Network: 'ipv6network',
            IPv6Interface: 'ipv6interface',
        }

        def ser_ip(ip: Any, info: core_schema.SerializationInfo) -> str | IpType:
            if not isinstance(ip, (tp, str)):
                raise PydanticSerializationUnexpectedValue(
                    f"Expected `{tp}` but got `{type(ip)}` with value `'{ip}'` - serialized value may not be as expected."
                )
            if info.mode == 'python':
                return ip
            return str(ip)

        return core_schema.lax_or_strict_schema(
            lax_schema=core_schema.no_info_plain_validator_function(IP_VALIDATOR_LOOKUP[tp]),
            strict_schema=core_schema.json_or_python_schema(
                json_schema=core_schema.no_info_after_validator_function(tp, core_schema.str_schema()),
                python_schema=core_schema.is_instance_schema(tp),
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(ser_ip, info_arg=True, when_used='always'),
            metadata={
                'pydantic_js_functions': [lambda _1, _2: {'type': 'string', 'format': ip_type_json_schema_format[tp]}]
            },
        )

    def _path_schema(self, tp: Any, path_type: Any) -> CoreSchema:
        if tp is os.PathLike and (path_type not in {str, bytes} and not typing_objects.is_any(path_type)):
            raise PydanticUserError(
                '`os.PathLike` can only be used with `str`, `bytes` or `Any`', code='schema-for-unknown-type'
            )

        path_constructor = pathlib.PurePath if tp is os.PathLike else tp
        strict_inner_schema = (
            core_schema.bytes_schema(strict=True) if (path_type is bytes) else core_schema.str_schema(strict=True)
        )
        lax_inner_schema = core_schema.bytes_schema() if (path_type is bytes) else core_schema.str_schema()

        def path_validator(input_value: str | bytes) -> os.PathLike[Any]:  # type: ignore
            try:
                if path_type is bytes:
                    if isinstance(input_value, bytes):
                        try:
                            input_value = input_value.decode()
                        except UnicodeDecodeError as e:
                            raise PydanticCustomError('bytes_type', 'Input must be valid bytes') from e
                    else:
                        raise PydanticCustomError('bytes_type', 'Input must be bytes')
                elif not isinstance(input_value, str):
                    raise PydanticCustomError('path_type', 'Input is not a valid path')

                return path_constructor(input_value)  # type: ignore
            except TypeError as e:
                raise PydanticCustomError('path_type', 'Input is not a valid path') from e

        def ser_path(path: Any, info: core_schema.SerializationInfo) -> str | os.PathLike[Any]:
            if not isinstance(path, (tp, str)):
                raise PydanticSerializationUnexpectedValue(
                    f"Expected `{tp}` but got `{type(path)}` with value `'{path}'` - serialized value may not be as expected."
                )
            if info.mode == 'python':
                return path
            return str(path)

        instance_schema = core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_after_validator_function(path_validator, lax_inner_schema),
            python_schema=core_schema.is_instance_schema(tp),
        )

        schema = core_schema.lax_or_strict_schema(
            lax_schema=core_schema.union_schema(
                [
                    instance_schema,
                    core_schema.no_info_after_validator_function(path_validator, strict_inner_schema),
                ],
                custom_error_type='path_type',
                custom_error_message=f'Input is not a valid path for {tp}',
            ),
            strict_schema=instance_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(ser_path, info_arg=True, when_used='always'),
            metadata={'pydantic_js_functions': [lambda source, handler: {**handler(source), 'format': 'path'}]},
        )
        return schema

    def _deque_schema(self, items_type: Any) -> CoreSchema:
        from ._serializers import serialize_sequence_via_list
        from ._validators import deque_validator

        item_type_schema = self.generate_schema(items_type)

        # we have to use a lax list schema here, because we need to validate the deque's
        # items via a list schema, but it's ok if the deque itself is not a list
        list_schema = core_schema.list_schema(item_type_schema, strict=False)

        check_instance = core_schema.json_or_python_schema(
            json_schema=list_schema,
            python_schema=core_schema.is_instance_schema(collections.deque, cls_repr='Deque'),
        )

        lax_schema = core_schema.no_info_wrap_validator_function(deque_validator, list_schema)

        return core_schema.lax_or_strict_schema(
            lax_schema=lax_schema,
            strict_schema=core_schema.chain_schema([check_instance, lax_schema]),
            serialization=core_schema.wrap_serializer_function_ser_schema(
                serialize_sequence_via_list, schema=item_type_schema, info_arg=True
            ),
        )

    def _mapping_schema(self, tp: Any, keys_type: Any, values_type: Any) -> CoreSchema:
        from ._validators import MAPPING_ORIGIN_MAP, defaultdict_validator, get_defaultdict_default_default_factory

        mapped_origin = MAPPING_ORIGIN_MAP[tp]
        keys_schema = self.generate_schema(keys_type)
        values_schema = self.generate_schema(values_type)
        dict_schema = core_schema.dict_schema(keys_schema, values_schema, strict=False)

        if mapped_origin is dict:
            schema = dict_schema
        else:
            check_instance = core_schema.json_or_python_schema(
                json_schema=dict_schema,
                python_schema=core_schema.is_instance_schema(mapped_origin),
            )

            if tp is collections.defaultdict:
                default_default_factory = get_defaultdict_default_default_factory(values_type)
                coerce_instance_wrap = partial(
                    core_schema.no_info_wrap_validator_function,
                    partial(defaultdict_validator, default_default_factory=default_default_factory),
                )
            else:
                coerce_instance_wrap = partial(core_schema.no_info_after_validator_function, mapped_origin)

            lax_schema = coerce_instance_wrap(dict_schema)
            strict_schema = core_schema.chain_schema([check_instance, lax_schema])

            schema = core_schema.lax_or_strict_schema(
                lax_schema=lax_schema,
                strict_schema=strict_schema,
                serialization=core_schema.wrap_serializer_function_ser_schema(
                    lambda v, h: h(v), schema=dict_schema, info_arg=False
                ),
            )

        return schema

    def _fraction_schema(self) -> CoreSchema:
        """Support for [`fractions.Fraction`][fractions.Fraction]."""
        from ._validators import fraction_validator

        # TODO: note, this is a fairly common pattern, re lax / strict for attempted type coercion,
        # can we use a helper function to reduce boilerplate?
        return core_schema.lax_or_strict_schema(
            lax_schema=core_schema.no_info_plain_validator_function(fraction_validator),
            strict_schema=core_schema.json_or_python_schema(
                json_schema=core_schema.no_info_plain_validator_function(fraction_validator),
                python_schema=core_schema.is_instance_schema(Fraction),
            ),
            # use str serialization to guarantee round trip behavior
            serialization=core_schema.to_string_ser_schema(when_used='always'),
            metadata={'pydantic_js_functions': [lambda _1, _2: {'type': 'string', 'format': 'fraction'}]},
        )

    def _arbitrary_type_schema(self, tp: Any) -> CoreSchema:
        if not isinstance(tp, type):
            warn(
                f'{tp!r} is not a Python type (it may be an instance of an object),'
                ' Pydantic will allow any object with no validation since we cannot even'
                ' enforce that the input is an instance of the given type.'
                ' To get rid of this error wrap the type with `pydantic.SkipValidation`.',
                UserWarning,
            )
            return core_schema.any_schema()
        return core_schema.is_instance_schema(tp)

    def _unknown_type_schema(self, obj: Any) -> CoreSchema:
        raise PydanticSchemaGenerationError(
            f'Unable to generate pydantic-core schema for {obj!r}. '
            'Set `arbitrary_types_allowed=True` in the model_config to ignore this error'
            ' or implement `__get_pydantic_core_schema__` on your type to fully support it.'
            '\n\nIf you got this error by calling handler(<some type>) within'
            ' `__get_pydantic_core_schema__` then you likely need to call'
            ' `handler.generate_schema(<some type>)` since we do not call'
            ' `__get_pydantic_core_schema__` on `<some type>` otherwise to avoid infinite recursion.'
        )

    def _apply_discriminator_to_union(
        self, schema: CoreSchema, discriminator: str | Discriminator | None
    ) -> CoreSchema:
        if discriminator is None:
            return schema
        try:
            return _discriminated_union.apply_discriminator(
                schema,
                discriminator,
                self.defs._definitions,
            )
        except _discriminated_union.MissingDefinitionForUnionRef:
            # defer until defs are resolved
            _discriminated_union.set_discriminator_in_metadata(
                schema,
                discriminator,
            )
            return schema

    def clean_schema(self, schema: CoreSchema) -> CoreSchema:
        schema = self.defs.finalize_schema(schema)
        schema = validate_core_schema(schema)
        return schema

    def _add_js_function(self, metadata_schema: CoreSchema, js_function: Callable[..., Any]) -> None:
        metadata = metadata_schema.get('metadata', {})
        pydantic_js_functions = metadata.setdefault('pydantic_js_functions', [])
        # because of how we generate core schemas for nested generic models
        # we can end up adding `BaseModel.__get_pydantic_json_schema__` multiple times
        # this check may fail to catch duplicates if the function is a `functools.partial`
        # or something like that, but if it does it'll fail by inserting the duplicate
        if js_function not in pydantic_js_functions:
            pydantic_js_functions.append(js_function)
        metadata_schema['metadata'] = metadata

    def generate_schema(
        self,
        obj: Any,
    ) -> core_schema.CoreSchema:
        """Generate core schema.

        Args:
            obj: The object to generate core schema for.

        Returns:
            The generated core schema.

        Raises:
            PydanticUndefinedAnnotation:
                If it is not possible to evaluate forward reference.
            PydanticSchemaGenerationError:
                If it is not possible to generate pydantic-core schema.
            TypeError:
                - If `alias_generator` returns a disallowed type (must be str, AliasPath or AliasChoices).
                - If V1 style validator with `each_item=True` applied on a wrong field.
            PydanticUserError:
                - If `typing.TypedDict` is used instead of `typing_extensions.TypedDict` on Python < 3.12.
                - If `__modify_schema__` method is used instead of `__get_pydantic_json_schema__`.
        """
        schema = self._generate_schema_from_get_schema_method(obj, obj)

        if schema is None:
            schema = self._generate_schema_inner(obj)

        metadata_js_function = _extract_get_pydantic_json_schema(obj)
        if metadata_js_function is not None:
            metadata_schema = resolve_original_schema(schema, self.defs)
            if metadata_schema:
                self._add_js_function(metadata_schema, metadata_js_function)

        schema = _add_custom_serialization_from_json_encoders(self._config_wrapper.json_encoders, obj, schema)

        return schema

    def _model_schema(self, cls: type[BaseModel]) -> core_schema.CoreSchema:
        """Generate schema for a Pydantic model."""
        BaseModel_ = import_cached_base_model()

        with self.defs.get_schema_or_ref(cls) as (model_ref, maybe_schema):
            if maybe_schema is not None:
                return maybe_schema

            schema = cls.__dict__.get('__pydantic_core_schema__')
            if schema is not None and not isinstance(schema, MockCoreSchema):
                if schema['type'] == 'definitions':
                    schema = self.defs.unpack_definitions(schema)
                ref = get_ref(schema)
                if ref:
                    return self.defs.create_definition_reference_schema(schema)
                else:
                    return schema

            config_wrapper = ConfigWrapper(cls.model_config, check=False)

            with self._config_wrapper_stack.push(config_wrapper), self._ns_resolver.push(cls):
                core_config = self._config_wrapper.core_config(title=cls.__name__)

                if cls.__pydantic_fields_complete__ or cls is BaseModel_:
                    fields = getattr(cls, '__pydantic_fields__', {})
                else:
                    if not hasattr(cls, '__pydantic_fields__'):
                        # This happens when we have a loop in the schema generation:
                        # class Base[T](BaseModel):
                        #     t: T
                        #
                        # class Other(BaseModel):
                        #     b: 'Base[Other]'
                        # When we build fields for `Other`, we evaluate the forward annotation.
                        # At this point, `Other` doesn't have the model fields set. We create
                        # `Base[Other]`; model fields are successfully built, and we try to generate
                        # a schema for `t: Other`. As `Other.__pydantic_fields__` aren't set, we abort.
                        raise PydanticUndefinedAnnotation(
                            name=cls.__name__,
                            message=f'Class {cls.__name__!r} is not defined',
                        )
                    try:
                        fields = rebuild_model_fields(
                            cls,
                            ns_resolver=self._ns_resolver,
                            typevars_map=self._typevars_map or {},
                        )
                    except NameError as e:
                        raise PydanticUndefinedAnnotation.from_name_error(e) from e

                decorators = cls.__pydantic_decorators__
                computed_fields = decorators.computed_fields
                check_decorator_fields_exist(
                    chain(
                        decorators.field_validators.values(),
                        decorators.field_serializers.values(),
                        decorators.validators.values(),
                    ),
                    {*fields.keys(), *computed_fields.keys()},
                )

                model_validators = decorators.model_validators.values()

                extras_schema = None
                extras_keys_schema = None
                if core_config.get('extra_fields_behavior') == 'allow':
                    assert cls.__mro__[0] is cls
                    assert cls.__mro__[-1] is object
                    for candidate_cls in cls.__mro__[:-1]:
                        extras_annotation = getattr(candidate_cls, '__annotations__', {}).get(
                            '__pydantic_extra__', None
                        )
                        if extras_annotation is not None:
                            if isinstance(extras_annotation, str):
                                extras_annotation = _typing_extra.eval_type_backport(
                                    _typing_extra._make_forward_ref(
                                        extras_annotation, is_argument=False, is_class=True
                                    ),
                                    *self._types_namespace,
                                )
                            tp = get_origin(extras_annotation)
                            if tp not in DICT_TYPES:
                                raise PydanticSchemaGenerationError(
                                    'The type annotation for `__pydantic_extra__` must be `dict[str, ...]`'
                                )
                            extra_keys_type, extra_items_type = self._get_args_resolving_forward_refs(
                                extras_annotation,
                                required=True,
                            )
                            if extra_keys_type is not str:
                                extras_keys_schema = self.generate_schema(extra_keys_type)
                            if not typing_objects.is_any(extra_items_type):
                                extras_schema = self.generate_schema(extra_items_type)
                            if extras_keys_schema is not None or extras_schema is not None:
                                break

                generic_origin: type[BaseModel] | None = getattr(cls, '__pydantic_generic_metadata__', {}).get('origin')

                if cls.__pydantic_root_model__:
                    root_field = self._common_field_schema('root', fields['root'], decorators)
                    inner_schema = root_field['schema']
                    inner_schema = apply_model_validators(inner_schema, model_validators, 'inner')
                    model_schema = core_schema.model_schema(
                        cls,
                        inner_schema,
                        generic_origin=generic_origin,
                        custom_init=getattr(cls, '__pydantic_custom_init__', None),
                        root_model=True,
                        post_init=getattr(cls, '__pydantic_post_init__', None),
                        config=core_config,
                        ref=model_ref,
                    )
                else:
                    fields_schema: core_schema.CoreSchema = core_schema.model_fields_schema(
                        {k: self._generate_md_field_schema(k, v, decorators) for k, v in fields.items()},
                        computed_fields=[
                            self._computed_field_schema(d, decorators.field_serializers)
                            for d in computed_fields.values()
                        ],
                        extras_schema=extras_schema,
                        extras_keys_schema=extras_keys_schema,
                        model_name=cls.__name__,
                    )
                    inner_schema = apply_validators(fields_schema, decorators.root_validators.values(), None)
                    inner_schema = apply_model_validators(inner_schema, model_validators, 'inner')

                    model_schema = core_schema.model_schema(
                        cls,
                        inner_schema,
                        generic_origin=generic_origin,
                        custom_init=getattr(cls, '__pydantic_custom_init__', None),
                        root_model=False,
                        post_init=getattr(cls, '__pydantic_post_init__', None),
                        config=core_config,
                        ref=model_ref,
                    )

                schema = self._apply_model_serializers(model_schema, decorators.model_serializers.values())
                schema = apply_model_validators(schema, model_validators, 'outer')
                return self.defs.create_definition_reference_schema(schema)

    def _resolve_self_type(self, obj: Any) -> Any:
        obj = self.model_type_stack.get()
        if obj is None:
            raise PydanticUserError('`typing.Self` is invalid in this context', code='invalid-self-type')
        return obj

    def _generate_schema_from_get_schema_method(self, obj: Any, source: Any) -> core_schema.CoreSchema | None:
        BaseModel_ = import_cached_base_model()

        get_schema = getattr(obj, '__get_pydantic_core_schema__', None)
        is_base_model_get_schema = (
            getattr(get_schema, '__func__', None) is BaseModel_.__get_pydantic_core_schema__.__func__  # pyright: ignore[reportFunctionMemberAccess]
        )

        if (
            get_schema is not None
            # BaseModel.__get_pydantic_core_schema__ is defined for backwards compatibility,
            # to allow existing code to call `super().__get_pydantic_core_schema__` in Pydantic
            # model that overrides `__get_pydantic_core_schema__`. However, it raises a deprecation
            # warning stating that the method will be removed, and during the core schema gen we actually
            # don't call the method:
            and not is_base_model_get_schema
        ):
            # Some referenceable types might have a `__get_pydantic_core_schema__` method
            # defined on it by users (e.g. on a dataclass). This generally doesn't play well
            # as these types are already recognized by the `GenerateSchema` class and isn't ideal
            # as we might end up calling `get_schema_or_ref` (expensive) on types that are actually
            # not referenceable:
            with self.defs.get_schema_or_ref(obj) as (_, maybe_schema):
                if maybe_schema is not None:
                    return maybe_schema

            if obj is source:
                ref_mode = 'unpack'
            else:
                ref_mode = 'to-def'
            schema = get_schema(
                source, CallbackGetCoreSchemaHandler(self._generate_schema_inner, self, ref_mode=ref_mode)
            )
            if schema['type'] == 'definitions':
                schema = self.defs.unpack_definitions(schema)

            ref = get_ref(schema)
            if ref:
                return self.defs.create_definition_reference_schema(schema)

            # Note: if schema is of type `'definition-ref'`, we might want to copy it as a
            # safety measure (because these are inlined in place -- i.e. mutated directly)
            return schema

        if get_schema is None and (validators := getattr(obj, '__get_validators__', None)) is not None:
            from pydantic.v1 import BaseModel as BaseModelV1

            if issubclass(obj, BaseModelV1):
                warn(
                    f'Mixing V1 models and V2 models (or constructs, like `TypeAdapter`) is not supported. Please upgrade `{obj.__name__}` to V2.',
                    UserWarning,
                )
            else:
                warn(
                    '`__get_validators__` is deprecated and will be removed, use `__get_pydantic_core_schema__` instead.',
                    PydanticDeprecatedSince20,
                )
            return core_schema.chain_schema([core_schema.with_info_plain_validator_function(v) for v in validators()])

    def _resolve_forward_ref(self, obj: Any) -> Any:
        # we assume that types_namespace has the target of forward references in its scope,
        # but this could fail, for example, if calling Validator on an imported type which contains
        # forward references to other types only defined in the module from which it was imported
        # `Validator(SomeImportedTypeAliasWithAForwardReference)`
        # or the equivalent for BaseModel
        # class Model(BaseModel):
        #   x: SomeImportedTypeAliasWithAForwardReference
        try:
            obj = _typing_extra.eval_type_backport(obj, *self._types_namespace)
        except NameError as e:
            raise PydanticUndefinedAnnotation.from_name_error(e) from e

        # if obj is still a ForwardRef, it means we can't evaluate it, raise PydanticUndefinedAnnotation
        if isinstance(obj, ForwardRef):
            raise PydanticUndefinedAnnotation(obj.__forward_arg__, f'Unable to evaluate forward reference {obj}')

        if self._typevars_map:
            obj = replace_types(obj, self._typevars_map)

        return obj

    @overload
    def _get_args_resolving_forward_refs(self, obj: Any, required: Literal[True]) -> tuple[Any, ...]: ...

    @overload
    def _get_args_resolving_forward_refs(self, obj: Any) -> tuple[Any, ...] | None: ...

    def _get_args_resolving_forward_refs(self, obj: Any, required: bool = False) -> tuple[Any, ...] | None:
        args = get_args(obj)
        if args:
            if isinstance(obj, GenericAlias):
                # PEP 585 generic aliases don't convert args to ForwardRefs, unlike `typing.List/Dict` etc.
                args = (_typing_extra._make_forward_ref(a) if isinstance(a, str) else a for a in args)
            args = tuple(self._resolve_forward_ref(a) if isinstance(a, ForwardRef) else a for a in args)
        elif required:  # pragma: no cover
            raise TypeError(f'Expected {obj} to have generic parameters but it had none')
        return args

    def _get_first_arg_or_any(self, obj: Any) -> Any:
        args = self._get_args_resolving_forward_refs(obj)
        if not args:
            return Any
        return args[0]

    def _get_first_two_args_or_any(self, obj: Any) -> tuple[Any, Any]:
        args = self._get_args_resolving_forward_refs(obj)
        if not args:
            return (Any, Any)
        if len(args) < 2:
            origin = get_origin(obj)
            raise TypeError(f'Expected two type arguments for {origin}, got 1')
        return args[0], args[1]

    def _generate_schema_inner(self, obj: Any) -> core_schema.CoreSchema:
        if typing_objects.is_self(obj):
            obj = self._resolve_self_type(obj)

        if typing_objects.is_annotated(get_origin(obj)):
            return self._annotated_schema(obj)

        if isinstance(obj, dict):
            # we assume this is already a valid schema
            return obj  # type: ignore[return-value]

        if isinstance(obj, str):
            obj = ForwardRef(obj)

        if isinstance(obj, ForwardRef):
            return self.generate_schema(self._resolve_forward_ref(obj))

        BaseModel = import_cached_base_model()

        if lenient_issubclass(obj, BaseModel):
            with self.model_type_stack.push(obj):
                return self._model_schema(obj)

        if isinstance(obj, PydanticRecursiveRef):
            return core_schema.definition_reference_schema(schema_ref=obj.type_ref)

        return self.match_type(obj)

    def match_type(self, obj: Any) -> core_schema.CoreSchema:  # noqa: C901
        """Main mapping of types to schemas.

        The general structure is a series of if statements starting with the simple cases
        (non-generic primitive types) and then handling generics and other more complex cases.

        Each case either generates a schema directly, calls into a public user-overridable method
        (like `GenerateSchema.tuple_variable_schema`) or calls into a private method that handles some
        boilerplate before calling into the user-facing method (e.g. `GenerateSchema._tuple_schema`).

        The idea is that we'll evolve this into adding more and more user facing methods over time
        as they get requested and we figure out what the right API for them is.
        """
        if obj is str:
            return core_schema.str_schema()
        elif obj is bytes:
            return core_schema.bytes_schema()
        elif obj is int:
            return core_schema.int_schema()
        elif obj is float:
            return core_schema.float_schema()
        elif obj is bool:
            return core_schema.bool_schema()
        elif obj is complex:
            return core_schema.complex_schema()
        elif typing_objects.is_any(obj) or obj is object:
            return core_schema.any_schema()
        elif obj is datetime.date:
            return core_schema.date_schema()
        elif obj is datetime.datetime:
            return core_schema.datetime_schema()
        elif obj is datetime.time:
            return core_schema.time_schema()
        elif obj is datetime.timedelta:
            return core_schema.timedelta_schema()
        elif obj is Decimal:
            return core_schema.decimal_schema()
        elif obj is UUID:
            return core_schema.uuid_schema()
        elif obj is Url:
            return core_schema.url_schema()
        elif obj is Fraction:
            return self._fraction_schema()
        elif obj is MultiHostUrl:
            return core_schema.multi_host_url_schema()
        elif obj is None or obj is _typing_extra.NoneType:
            return core_schema.none_schema()
        elif obj in IP_TYPES:
            return self._ip_schema(obj)
        elif obj in TUPLE_TYPES:
            return self._tuple_schema(obj)
        elif obj in LIST_TYPES:
            return self._list_schema(Any)
        elif obj in SET_TYPES:
            return self._set_schema(Any)
        elif obj in FROZEN_SET_TYPES:
            return self._frozenset_schema(Any)
        elif obj in SEQUENCE_TYPES:
            return self._sequence_schema(Any)
        elif obj in ITERABLE_TYPES:
            return self._iterable_schema(obj)
        elif obj in DICT_TYPES:
            return self._dict_schema(Any, Any)
        elif obj in PATH_TYPES:
            return self._path_schema(obj, Any)
        elif obj in DEQUE_TYPES:
            return self._deque_schema(Any)
        elif obj in MAPPING_TYPES:
            return self._mapping_schema(obj, Any, Any)
        elif obj in COUNTER_TYPES:
            return self._mapping_schema(obj, Any, int)
        elif typing_objects.is_typealiastype(obj):
            return self._type_alias_type_schema(obj)
        elif obj is type:
            return self._type_schema()
        elif _typing_extra.is_callable(obj):
            return core_schema.callable_schema()
        elif typing_objects.is_literal(get_origin(obj)):
            return self._literal_schema(obj)
        elif is_typeddict(obj):
            return self._typed_dict_schema(obj, None)
        elif _typing_extra.is_namedtuple(obj):
            return self._namedtuple_schema(obj, None)
        elif typing_objects.is_newtype(obj):
            # NewType, can't use isinstance because it fails <3.10
            return self.generate_schema(obj.__supertype__)
        elif obj in PATTERN_TYPES:
            return self._pattern_schema(obj)
        elif _typing_extra.is_hashable(obj):
            return self._hashable_schema()
        elif isinstance(obj, typing.TypeVar):
            return self._unsubstituted_typevar_schema(obj)
        elif _typing_extra.is_finalvar(obj):
            if obj is Final:
                return core_schema.any_schema()
            return self.generate_schema(
                self._get_first_arg_or_any(obj),
            )
        elif isinstance(obj, VALIDATE_CALL_SUPPORTED_TYPES):
            return self._call_schema(obj)
        elif inspect.isclass(obj) and issubclass(obj, Enum):
            return self._enum_schema(obj)
        elif obj is ZoneInfo:
            return self._zoneinfo_schema()

        # dataclasses.is_dataclass coerces dc instances to types, but we only handle
        # the case of a dc type here
        if dataclasses.is_dataclass(obj):
            return self._dataclass_schema(obj, None)  # pyright: ignore[reportArgumentType]

        origin = get_origin(obj)
        if origin is not None:
            return self._match_generic_type(obj, origin)

        if self._arbitrary_types:
            return self._arbitrary_type_schema(obj)
        return self._unknown_type_schema(obj)

    def _match_generic_type(self, obj: Any, origin: Any) -> CoreSchema:  # noqa: C901
        # Need to handle generic dataclasses before looking for the schema properties because attribute accesses
        # on _GenericAlias delegate to the origin type, so lose the information about the concrete parametrization
        # As a result, currently, there is no way to cache the schema for generic dataclasses. This may be possible
        # to resolve by modifying the value returned by `Generic.__class_getitem__`, but that is a dangerous game.
        if dataclasses.is_dataclass(origin):
            return self._dataclass_schema(obj, origin)  # pyright: ignore[reportArgumentType]
        if _typing_extra.is_namedtuple(origin):
            return self._namedtuple_schema(obj, origin)

        schema = self._generate_schema_from_get_schema_method(origin, obj)
        if schema is not None:
            return schema

        if typing_objects.is_typealiastype(origin):
            return self._type_alias_type_schema(obj)
        elif is_union_origin(origin):
            return self._union_schema(obj)
        elif origin in TUPLE_TYPES:
            return self._tuple_schema(obj)
        elif origin in LIST_TYPES:
            return self._list_schema(self._get_first_arg_or_any(obj))
        elif origin in SET_TYPES:
            return self._set_schema(self._get_first_arg_or_any(obj))
        elif origin in FROZEN_SET_TYPES:
            return self._frozenset_schema(self._get_first_arg_or_any(obj))
        elif origin in DICT_TYPES:
            return self._dict_schema(*self._get_first_two_args_or_any(obj))
        elif origin in PATH_TYPES:
            return self._path_schema(origin, self._get_first_arg_or_any(obj))
        elif origin in DEQUE_TYPES:
            return self._deque_schema(self._get_first_arg_or_any(obj))
        elif origin in MAPPING_TYPES:
            return self._mapping_schema(origin, *self._get_first_two_args_or_any(obj))
        elif origin in COUNTER_TYPES:
            return self._mapping_schema(origin, self._get_first_arg_or_any(obj), int)
        elif is_typeddict(origin):
            return self._typed_dict_schema(obj, origin)
        elif origin in TYPE_TYPES:
            return self._subclass_schema(obj)
        elif origin in SEQUENCE_TYPES:
            return self._sequence_schema(self._get_first_arg_or_any(obj))
        elif origin in ITERABLE_TYPES:
            return self._iterable_schema(obj)
        elif origin in PATTERN_TYPES:
            return self._pattern_schema(obj)

        if self._arbitrary_types:
            return self._arbitrary_type_schema(origin)
        return self._unknown_type_schema(obj)

    def _generate_td_field_schema(
        self,
        name: str,
        field_info: FieldInfo,
        decorators: DecoratorInfos,
        *,
        required: bool = True,
    ) -> core_schema.TypedDictField:
        """Prepare a TypedDictField to represent a model or typeddict field."""
        common_field = self._common_field_schema(name, field_info, decorators)
        return core_schema.typed_dict_field(
            common_field['schema'],
            required=False if not field_info.is_required() else required,
            serialization_exclude=common_field['serialization_exclude'],
            validation_alias=common_field['validation_alias'],
            serialization_alias=common_field['serialization_alias'],
            metadata=common_field['metadata'],
        )

    def _generate_md_field_schema(
        self,
        name: str,
        field_info: FieldInfo,
        decorators: DecoratorInfos,
    ) -> core_schema.ModelField:
        """Prepare a ModelField to represent a model field."""
        common_field = self._common_field_schema(name, field_info, decorators)
        return core_schema.model_field(
            common_field['schema'],
            serialization_exclude=common_field['serialization_exclude'],
            validation_alias=common_field['validation_alias'],
            serialization_alias=common_field['serialization_alias'],
            frozen=common_field['frozen'],
            metadata=common_field['metadata'],
        )

    def _generate_dc_field_schema(
        self,
        name: str,
        field_info: FieldInfo,
        decorators: DecoratorInfos,
    ) -> core_schema.DataclassField:
        """Prepare a DataclassField to represent the parameter/field, of a dataclass."""
        common_field = self._common_field_schema(name, field_info, decorators)
        return core_schema.dataclass_field(
            name,
            common_field['schema'],
            init=field_info.init,
            init_only=field_info.init_var or None,
            kw_only=None if field_info.kw_only else False,
            serialization_exclude=common_field['serialization_exclude'],
            validation_alias=common_field['validation_alias'],
            serialization_alias=common_field['serialization_alias'],
            frozen=common_field['frozen'],
            metadata=common_field['metadata'],
        )

    @staticmethod
    def _apply_alias_generator_to_field_info(
        alias_generator: Callable[[str], str] | AliasGenerator, field_info: FieldInfo, field_name: str
    ) -> None:
        """Apply an alias_generator to aliases on a FieldInfo instance if appropriate.

        Args:
            alias_generator: A callable that takes a string and returns a string, or an AliasGenerator instance.
            field_info: The FieldInfo instance to which the alias_generator is (maybe) applied.
            field_name: The name of the field from which to generate the alias.
        """
        # Apply an alias_generator if
        # 1. An alias is not specified
        # 2. An alias is specified, but the priority is <= 1
        if (
            field_info.alias_priority is None
            or field_info.alias_priority <= 1
            or field_info.alias is None
            or field_info.validation_alias is None
            or field_info.serialization_alias is None
        ):
            alias, validation_alias, serialization_alias = None, None, None

            if isinstance(alias_generator, AliasGenerator):
                alias, validation_alias, serialization_alias = alias_generator.generate_aliases(field_name)
            elif isinstance(alias_generator, Callable):
                alias = alias_generator(field_name)
                if not isinstance(alias, str):
                    raise TypeError(f'alias_generator {alias_generator} must return str, not {alias.__class__}')

            # if priority is not set, we set to 1
            # which supports the case where the alias_generator from a child class is used
            # to generate an alias for a field in a parent class
            if field_info.alias_priority is None or field_info.alias_priority <= 1:
                field_info.alias_priority = 1

            # if the priority is 1, then we set the aliases to the generated alias
            if field_info.alias_priority == 1:
                field_info.serialization_alias = _get_first_non_null(serialization_alias, alias)
                field_info.validation_alias = _get_first_non_null(validation_alias, alias)
                field_info.alias = alias

            # if any of the aliases are not set, then we set them to the corresponding generated alias
            if field_info.alias is None:
                field_info.alias = alias
            if field_info.serialization_alias is None:
                field_info.serialization_alias = _get_first_non_null(serialization_alias, alias)
            if field_info.validation_alias is None:
                field_info.validation_alias = _get_first_non_null(validation_alias, alias)

    @staticmethod
    def _apply_alias_generator_to_computed_field_info(
        alias_generator: Callable[[str], str] | AliasGenerator,
        computed_field_info: ComputedFieldInfo,
        computed_field_name: str,
    ):
        """Apply an alias_generator to alias on a ComputedFieldInfo instance if appropriate.

        Args:
            alias_generator: A callable that takes a string and returns a string, or an AliasGenerator instance.
            computed_field_info: The ComputedFieldInfo instance to which the alias_generator is (maybe) applied.
            computed_field_name: The name of the computed field from which to generate the alias.
        """
        # Apply an alias_generator if
        # 1. An alias is not specified
        # 2. An alias is specified, but the priority is <= 1

        if (
            computed_field_info.alias_priority is None
            or computed_field_info.alias_priority <= 1
            or computed_field_info.alias is None
        ):
            alias, validation_alias, serialization_alias = None, None, None

            if isinstance(alias_generator, AliasGenerator):
                alias, validation_alias, serialization_alias = alias_generator.generate_aliases(computed_field_name)
            elif isinstance(alias_generator, Callable):
                alias = alias_generator(computed_field_name)
                if not isinstance(alias, str):
                    raise TypeError(f'alias_generator {alias_generator} must return str, not {alias.__class__}')

            # if priority is not set, we set to 1
            # which supports the case where the alias_generator from a child class is used
            # to generate an alias for a field in a parent class
            if computed_field_info.alias_priority is None or computed_field_info.alias_priority <= 1:
                computed_field_info.alias_priority = 1

            # if the priority is 1, then we set the aliases to the generated alias
            # note that we use the serialization_alias with priority over alias, as computed_field
            # aliases are used for serialization only (not validation)
            if computed_field_info.alias_priority == 1:
                computed_field_info.alias = _get_first_non_null(serialization_alias, alias)

    @staticmethod
    def _apply_field_title_generator_to_field_info(
        config_wrapper: ConfigWrapper, field_info: FieldInfo | ComputedFieldInfo, field_name: str
    ) -> None:
        """Apply a field_title_generator on a FieldInfo or ComputedFieldInfo instance if appropriate
        Args:
            config_wrapper: The config of the model
            field_info: The FieldInfo or ComputedField instance to which the title_generator is (maybe) applied.
            field_name: The name of the field from which to generate the title.
        """
        field_title_generator = field_info.field_title_generator or config_wrapper.field_title_generator

        if field_title_generator is None:
            return

        if field_info.title is None:
            title = field_title_generator(field_name, field_info)  # type: ignore
            if not isinstance(title, str):
                raise TypeError(f'field_title_generator {field_title_generator} must return str, not {title.__class__}')

            field_info.title = title

    def _common_field_schema(  # C901
        self, name: str, field_info: FieldInfo, decorators: DecoratorInfos
    ) -> _CommonField:
        source_type, annotations = field_info.annotation, field_info.metadata

        def set_discriminator(schema: CoreSchema) -> CoreSchema:
            schema = self._apply_discriminator_to_union(schema, field_info.discriminator)
            return schema

        # Convert `@field_validator` decorators to `Before/After/Plain/WrapValidator` instances:
        validators_from_decorators = []
        for decorator in filter_field_decorator_info_by_field(decorators.field_validators.values(), name):
            validators_from_decorators.append(_mode_to_validator[decorator.info.mode]._from_decorator(decorator))

        with self.field_name_stack.push(name):
            if field_info.discriminator is not None:
                schema = self._apply_annotations(
                    source_type, annotations + validators_from_decorators, transform_inner_schema=set_discriminator
                )
            else:
                schema = self._apply_annotations(
                    source_type,
                    annotations + validators_from_decorators,
                )

        # This V1 compatibility shim should eventually be removed
        # push down any `each_item=True` validators
        # note that this won't work for any Annotated types that get wrapped by a function validator
        # but that's okay because that didn't exist in V1
        this_field_validators = filter_field_decorator_info_by_field(decorators.validators.values(), name)
        if _validators_require_validate_default(this_field_validators):
            field_info.validate_default = True
        each_item_validators = [v for v in this_field_validators if v.info.each_item is True]
        this_field_validators = [v for v in this_field_validators if v not in each_item_validators]
        schema = apply_each_item_validators(schema, each_item_validators, name)

        schema = apply_validators(schema, this_field_validators, name)

        # the default validator needs to go outside of any other validators
        # so that it is the topmost validator for the field validator
        # which uses it to check if the field has a default value or not
        if not field_info.is_required():
            schema = wrap_default(field_info, schema)

        schema = self._apply_field_serializers(
            schema, filter_field_decorator_info_by_field(decorators.field_serializers.values(), name)
        )
        self._apply_field_title_generator_to_field_info(self._config_wrapper, field_info, name)

        pydantic_js_updates, pydantic_js_extra = _extract_json_schema_info_from_field_info(field_info)
        core_metadata: dict[str, Any] = {}
        update_core_metadata(
            core_metadata, pydantic_js_updates=pydantic_js_updates, pydantic_js_extra=pydantic_js_extra
        )

        alias_generator = self._config_wrapper.alias_generator
        if alias_generator is not None:
            self._apply_alias_generator_to_field_info(alias_generator, field_info, name)

        if isinstance(field_info.validation_alias, (AliasChoices, AliasPath)):
            validation_alias = field_info.validation_alias.convert_to_aliases()
        else:
            validation_alias = field_info.validation_alias

        return _common_field(
            schema,
            serialization_exclude=True if field_info.exclude else None,
            validation_alias=validation_alias,
            serialization_alias=field_info.serialization_alias,
            frozen=field_info.frozen,
            metadata=core_metadata,
        )

    def _union_schema(self, union_type: Any) -> core_schema.CoreSchema:
        """Generate schema for a Union."""
        args = self._get_args_resolving_forward_refs(union_type, required=True)
        choices: list[CoreSchema] = []
        nullable = False
        for arg in args:
            if arg is None or arg is _typing_extra.NoneType:
                nullable = True
            else:
                choices.append(self.generate_schema(arg))

        if len(choices) == 1:
            s = choices[0]
        else:
            choices_with_tags: list[CoreSchema | tuple[CoreSchema, str]] = []
            for choice in choices:
                tag = cast(CoreMetadata, choice.get('metadata', {})).get('pydantic_internal_union_tag_key')
                if tag is not None:
                    choices_with_tags.append((choice, tag))
                else:
                    choices_with_tags.append(choice)
            s = core_schema.union_schema(choices_with_tags)

        if nullable:
            s = core_schema.nullable_schema(s)
        return s

    def _type_alias_type_schema(self, obj: TypeAliasType) -> CoreSchema:
        with self.defs.get_schema_or_ref(obj) as (ref, maybe_schema):
            if maybe_schema is not None:
                return maybe_schema

            origin: TypeAliasType = get_origin(obj) or obj
            typevars_map = get_standard_typevars_map(obj)

            with self._ns_resolver.push(origin):
                try:
                    annotation = _typing_extra.eval_type(origin.__value__, *self._types_namespace)
                except NameError as e:
                    raise PydanticUndefinedAnnotation.from_name_error(e) from e
                annotation = replace_types(annotation, typevars_map)
                schema = self.generate_schema(annotation)
                assert schema['type'] != 'definitions'
                schema['ref'] = ref  # type: ignore
            return self.defs.create_definition_reference_schema(schema)

    def _literal_schema(self, literal_type: Any) -> CoreSchema:
        """Generate schema for a Literal."""
        expected = list(get_literal_values(literal_type, type_check=False, unpack_type_aliases='eager'))
        assert expected, f'literal "expected" cannot be empty, obj={literal_type}'
        schema = core_schema.literal_schema(expected)

        if self._config_wrapper.use_enum_values and any(isinstance(v, Enum) for v in expected):
            schema = core_schema.no_info_after_validator_function(
                lambda v: v.value if isinstance(v, Enum) else v, schema
            )

        return schema

    def _typed_dict_schema(self, typed_dict_cls: Any, origin: Any) -> core_schema.CoreSchema:
        """Generate a core schema for a `TypedDict` class.

        To be able to build a `DecoratorInfos` instance for the `TypedDict` class (which will include
        validators, serializers, etc.), we need to have access to the original bases of the class
        (see https://docs.python.org/3/library/types.html#types.get_original_bases).
        However, the `__orig_bases__` attribute was only added in 3.12 (https://github.com/python/cpython/pull/103698).

        For this reason, we require Python 3.12 (or using the `typing_extensions` backport).
        """
        FieldInfo = import_cached_field_info()

        with (
            self.model_type_stack.push(typed_dict_cls),
            self.defs.get_schema_or_ref(typed_dict_cls) as (
                typed_dict_ref,
                maybe_schema,
            ),
        ):
            if maybe_schema is not None:
                return maybe_schema

            typevars_map = get_standard_typevars_map(typed_dict_cls)
            if origin is not None:
                typed_dict_cls = origin

            if not _SUPPORTS_TYPEDDICT and type(typed_dict_cls).__module__ == 'typing':
                raise PydanticUserError(
                    'Please use `typing_extensions.TypedDict` instead of `typing.TypedDict` on Python < 3.12.',
                    code='typed-dict-version',
                )

            try:
                # if a typed dictionary class doesn't have config, we use the parent's config, hence a default of `None`
                # see https://github.com/pydantic/pydantic/issues/10917
                config: ConfigDict | None = get_attribute_from_bases(typed_dict_cls, '__pydantic_config__')
            except AttributeError:
                config = None

            with self._config_wrapper_stack.push(config):
                core_config = self._config_wrapper.core_config(title=typed_dict_cls.__name__)

                required_keys: frozenset[str] = typed_dict_cls.__required_keys__

                fields: dict[str, core_schema.TypedDictField] = {}

                decorators = DecoratorInfos.build(typed_dict_cls)

                if self._config_wrapper.use_attribute_docstrings:
                    field_docstrings = extract_docstrings_from_cls(typed_dict_cls, use_inspect=True)
                else:
                    field_docstrings = None

                try:
                    annotations = _typing_extra.get_cls_type_hints(typed_dict_cls, ns_resolver=self._ns_resolver)
                except NameError as e:
                    raise PydanticUndefinedAnnotation.from_name_error(e) from e

                readonly_fields: list[str] = []

                for field_name, annotation in annotations.items():
                    field_info = FieldInfo.from_annotation(annotation, _source=AnnotationSource.TYPED_DICT)
                    field_info.annotation = replace_types(field_info.annotation, typevars_map)

                    required = (
                        field_name in required_keys or 'required' in field_info._qualifiers
                    ) and 'not_required' not in field_info._qualifiers
                    if 'read_only' in field_info._qualifiers:
                        readonly_fields.append(field_name)

                    if (
                        field_docstrings is not None
                        and field_info.description is None
                        and field_name in field_docstrings
                    ):
                        field_info.description = field_docstrings[field_name]
                    self._apply_field_title_generator_to_field_info(self._config_wrapper, field_info, field_name)
                    fields[field_name] = self._generate_td_field_schema(
                        field_name, field_info, decorators, required=required
                    )

                if readonly_fields:
                    fields_repr = ', '.join(repr(f) for f in readonly_fields)
                    plural = len(readonly_fields) >= 2
                    warnings.warn(
                        f'Item{"s" if plural else ""} {fields_repr} on TypedDict class {typed_dict_cls.__name__!r} '
                        f'{"are" if plural else "is"} using the `ReadOnly` qualifier. Pydantic will not protect items '
                        'from any mutation on dictionary instances.',
                        UserWarning,
                    )

                td_schema = core_schema.typed_dict_schema(
                    fields,
                    cls=typed_dict_cls,
                    computed_fields=[
                        self._computed_field_schema(d, decorators.field_serializers)
                        for d in decorators.computed_fields.values()
                    ],
                    ref=typed_dict_ref,
                    config=core_config,
                )

                schema = self._apply_model_serializers(td_schema, decorators.model_serializers.values())
                schema = apply_model_validators(schema, decorators.model_validators.values(), 'all')
                return self.defs.create_definition_reference_schema(schema)

    def _namedtuple_schema(self, namedtuple_cls: Any, origin: Any) -> core_schema.CoreSchema:
        """Generate schema for a NamedTuple."""
        with (
            self.model_type_stack.push(namedtuple_cls),
            self.defs.get_schema_or_ref(namedtuple_cls) as (
                namedtuple_ref,
                maybe_schema,
            ),
        ):
            if maybe_schema is not None:
                return maybe_schema
            typevars_map = get_standard_typevars_map(namedtuple_cls)
            if origin is not None:
                namedtuple_cls = origin

            try:
                annotations = _typing_extra.get_cls_type_hints(namedtuple_cls, ns_resolver=self._ns_resolver)
            except NameError as e:
                raise PydanticUndefinedAnnotation.from_name_error(e) from e
            if not annotations:
                # annotations is empty, happens if namedtuple_cls defined via collections.namedtuple(...)
                annotations: dict[str, Any] = {k: Any for k in namedtuple_cls._fields}

            if typevars_map:
                annotations = {
                    field_name: replace_types(annotation, typevars_map)
                    for field_name, annotation in annotations.items()
                }

            arguments_schema = core_schema.arguments_schema(
                [
                    self._generate_parameter_schema(
                        field_name,
                        annotation,
                        source=AnnotationSource.NAMED_TUPLE,
                        default=namedtuple_cls._field_defaults.get(field_name, Parameter.empty),
                    )
                    for field_name, annotation in annotations.items()
                ],
                metadata={'pydantic_js_prefer_positional_arguments': True},
            )
            schema = core_schema.call_schema(arguments_schema, namedtuple_cls, ref=namedtuple_ref)
            return self.defs.create_definition_reference_schema(schema)

    def _generate_parameter_schema(
        self,
        name: str,
        annotation: type[Any],
        source: AnnotationSource,
        default: Any = Parameter.empty,
        mode: Literal['positional_only', 'positional_or_keyword', 'keyword_only'] | None = None,
    ) -> core_schema.ArgumentsParameter:
        """Generate the definition of a field in a namedtuple or a parameter in a function signature.

        This definition is meant to be used for the `'arguments'` core schema, which will be replaced
        in V3 by the `'arguments-v3`'.
        """
        FieldInfo = import_cached_field_info()

        if default is Parameter.empty:
            field = FieldInfo.from_annotation(annotation, _source=source)
        else:
            field = FieldInfo.from_annotated_attribute(annotation, default, _source=source)
        assert field.annotation is not None, 'field.annotation should not be None when generating a schema'
        with self.field_name_stack.push(name):
            schema = self._apply_annotations(field.annotation, [field])

        if not field.is_required():
            schema = wrap_default(field, schema)

        parameter_schema = core_schema.arguments_parameter(name, schema)
        if mode is not None:
            parameter_schema['mode'] = mode
        if field.alias is not None:
            parameter_schema['alias'] = field.alias
        else:
            alias_generator = self._config_wrapper.alias_generator
            if isinstance(alias_generator, AliasGenerator) and alias_generator.alias is not None:
                parameter_schema['alias'] = alias_generator.alias(name)
            elif callable(alias_generator):
                parameter_schema['alias'] = alias_generator(name)
        return parameter_schema

    def _generate_parameter_v3_schema(
        self,
        name: str,
        annotation: Any,
        source: AnnotationSource,
        mode: Literal[
            'positional_only',
            'positional_or_keyword',
            'keyword_only',
            'var_args',
            'var_kwargs_uniform',
            'var_kwargs_unpacked_typed_dict',
        ],
        default: Any = Parameter.empty,
    ) -> core_schema.ArgumentsV3Parameter:
        """Generate the definition of a parameter in a function signature.

        This definition is meant to be used for the `'arguments-v3'` core schema, which will replace
        the `'arguments`' schema in V3.
        """
        FieldInfo = import_cached_field_info()

        if default is Parameter.empty:
            field = FieldInfo.from_annotation(annotation, _source=source)
        else:
            field = FieldInfo.from_annotated_attribute(annotation, default, _source=source)

        with self.field_name_stack.push(name):
            schema = self._apply_annotations(field.annotation, [field])

        if not field.is_required():
            schema = wrap_default(field, schema)

        parameter_schema = core_schema.arguments_v3_parameter(
            name=name,
            schema=schema,
            mode=mode,
        )
        if field.alias is not None:
            parameter_schema['alias'] = field.alias
        else:
            alias_generator = self._config_wrapper.alias_generator
            if isinstance(alias_generator, AliasGenerator) and alias_generator.alias is not None:
                parameter_schema['alias'] = alias_generator.alias(name)
            elif callable(alias_generator):
                parameter_schema['alias'] = alias_generator(name)

        return parameter_schema

    def _tuple_schema(self, tuple_type: Any) -> core_schema.CoreSchema:
        """Generate schema for a Tuple, e.g. `tuple[int, str]` or `tuple[int, ...]`."""
        # TODO: do we really need to resolve type vars here?
        typevars_map = get_standard_typevars_map(tuple_type)
        params = self._get_args_resolving_forward_refs(tuple_type)

        if typevars_map and params:
            params = tuple(replace_types(param, typevars_map) for param in params)

        # NOTE: subtle difference: `tuple[()]` gives `params=()`, whereas `typing.Tuple[()]` gives `params=((),)`
        # This is only true for <3.11, on Python 3.11+ `typing.Tuple[()]` gives `params=()`
        if not params:
            if tuple_type in TUPLE_TYPES:
                return core_schema.tuple_schema([core_schema.any_schema()], variadic_item_index=0)
            else:
                # special case for `tuple[()]` which means `tuple[]` - an empty tuple
                return core_schema.tuple_schema([])
        elif params[-1] is Ellipsis:
            if len(params) == 2:
                return core_schema.tuple_schema([self.generate_schema(params[0])], variadic_item_index=0)
            else:
                # TODO: something like https://github.com/pydantic/pydantic/issues/5952
                raise ValueError('Variable tuples can only have one type')
        elif len(params) == 1 and params[0] == ():
            # special case for `tuple[()]` which means `tuple[]` - an empty tuple
            # NOTE: This conditional can be removed when we drop support for Python 3.10.
            return core_schema.tuple_schema([])
        else:
            return core_schema.tuple_schema([self.generate_schema(param) for param in params])

    def _type_schema(self) -> core_schema.CoreSchema:
        return core_schema.custom_error_schema(
            core_schema.is_instance_schema(type),
            custom_error_type='is_type',
            custom_error_message='Input should be a type',
        )

    def _zoneinfo_schema(self) -> core_schema.CoreSchema:
        """Generate schema for a zone_info.ZoneInfo object"""
        from ._validators import validate_str_is_valid_iana_tz

        metadata = {'pydantic_js_functions': [lambda _1, _2: {'type': 'string', 'format': 'zoneinfo'}]}
        return core_schema.no_info_plain_validator_function(
            validate_str_is_valid_iana_tz,
            serialization=core_schema.to_string_ser_schema(),
            metadata=metadata,
        )

    def _union_is_subclass_schema(self, union_type: Any) -> core_schema.CoreSchema:
        """Generate schema for `type[Union[X, ...]]`."""
        args = self._get_args_resolving_forward_refs(union_type, required=True)
        return core_schema.union_schema([self.generate_schema(type[args]) for args in args])

    def _subclass_schema(self, type_: Any) -> core_schema.CoreSchema:
        """Generate schema for a type, e.g. `type[int]`."""
        type_param = self._get_first_arg_or_any(type_)

        # Assume `type[Annotated[<typ>, ...]]` is equivalent to `type[<typ>]`:
        type_param = _typing_extra.annotated_type(type_param) or type_param

        if typing_objects.is_any(type_param):
            return self._type_schema()
        elif typing_objects.is_typealiastype(type_param):
            return self.generate_schema(type[type_param.__value__])
        elif typing_objects.is_typevar(type_param):
            if type_param.__bound__:
                if is_union_origin(get_origin(type_param.__bound__)):
                    return self._union_is_subclass_schema(type_param.__bound__)
                return core_schema.is_subclass_schema(type_param.__bound__)
            elif type_param.__constraints__:
                return core_schema.union_schema([self.generate_schema(type[c]) for c in type_param.__constraints__])
            else:
                return self._type_schema()
        elif is_union_origin(get_origin(type_param)):
            return self._union_is_subclass_schema(type_param)
        else:
            if typing_objects.is_self(type_param):
                type_param = self._resolve_self_type(type_param)
            if _typing_extra.is_generic_alias(type_param):
                raise PydanticUserError(
                    'Subscripting `type[]` with an already parametrized type is not supported. '
                    f'Instead of using type[{type_param!r}], use type[{_repr.display_as_type(get_origin(type_param))}].',
                    code=None,
                )
            if not inspect.isclass(type_param):
                # when using type[None], this doesn't type convert to type[NoneType], and None isn't a class
                # so we handle it manually here
                if type_param is None:
                    return core_schema.is_subclass_schema(_typing_extra.NoneType)
                raise TypeError(f'Expected a class, got {type_param!r}')
            return core_schema.is_subclass_schema(type_param)

    def _sequence_schema(self, items_type: Any) -> core_schema.CoreSchema:
        """Generate schema for a Sequence, e.g. `Sequence[int]`."""
        from ._serializers import serialize_sequence_via_list

        item_type_schema = self.generate_schema(items_type)
        list_schema = core_schema.list_schema(item_type_schema)

        json_schema = smart_deepcopy(list_schema)
        python_schema = core_schema.is_instance_schema(typing.Sequence, cls_repr='Sequence')
        if not typing_objects.is_any(items_type):
            from ._validators import sequence_validator

            python_schema = core_schema.chain_schema(
                [python_schema, core_schema.no_info_wrap_validator_function(sequence_validator, list_schema)],
            )

        serialization = core_schema.wrap_serializer_function_ser_schema(
            serialize_sequence_via_list, schema=item_type_schema, info_arg=True
        )
        return core_schema.json_or_python_schema(
            json_schema=json_schema, python_schema=python_schema, serialization=serialization
        )

    def _iterable_schema(self, type_: Any) -> core_schema.GeneratorSchema:
        """Generate a schema for an `Iterable`."""
        item_type = self._get_first_arg_or_any(type_)

        return core_schema.generator_schema(self.generate_schema(item_type))

    def _pattern_schema(self, pattern_type: Any) -> core_schema.CoreSchema:
        from . import _validators

        metadata = {'pydantic_js_functions': [lambda _1, _2: {'type': 'string', 'format': 'regex'}]}
        ser = core_schema.plain_serializer_function_ser_schema(
            attrgetter('pattern'), when_used='json', return_schema=core_schema.str_schema()
        )
        if pattern_type is typing.Pattern or pattern_type is re.Pattern:
            # bare type
            return core_schema.no_info_plain_validator_function(
                _validators.pattern_either_validator, serialization=ser, metadata=metadata
            )

        param = self._get_args_resolving_forward_refs(
            pattern_type,
            required=True,
        )[0]
        if param is str:
            return core_schema.no_info_plain_validator_function(
                _validators.pattern_str_validator, serialization=ser, metadata=metadata
            )
        elif param is bytes:
            return core_schema.no_info_plain_validator_function(
                _validators.pattern_bytes_validator, serialization=ser, metadata=metadata
            )
        else:
            raise PydanticSchemaGenerationError(f'Unable to generate pydantic-core schema for {pattern_type!r}.')

    def _hashable_schema(self) -> core_schema.CoreSchema:
        return core_schema.custom_error_schema(
            schema=core_schema.json_or_python_schema(
                json_schema=core_schema.chain_schema(
                    [core_schema.any_schema(), core_schema.is_instance_schema(collections.abc.Hashable)]
                ),
                python_schema=core_schema.is_instance_schema(collections.abc.Hashable),
            ),
            custom_error_type='is_hashable',
            custom_error_message='Input should be hashable',
        )

    def _dataclass_schema(
        self, dataclass: type[StandardDataclass], origin: type[StandardDataclass] | None
    ) -> core_schema.CoreSchema:
        """Generate schema for a dataclass."""
        with (
            self.model_type_stack.push(dataclass),
            self.defs.get_schema_or_ref(dataclass) as (
                dataclass_ref,
                maybe_schema,
            ),
        ):
            if maybe_schema is not None:
                return maybe_schema

            schema = dataclass.__dict__.get('__pydantic_core_schema__')
            if schema is not None and not isinstance(schema, MockCoreSchema):
                if schema['type'] == 'definitions':
                    schema = self.defs.unpack_definitions(schema)
                ref = get_ref(schema)
                if ref:
                    return self.defs.create_definition_reference_schema(schema)
                else:
                    return schema

            typevars_map = get_standard_typevars_map(dataclass)
            if origin is not None:
                dataclass = origin

            # if (plain) dataclass doesn't have config, we use the parent's config, hence a default of `None`
            # (Pydantic dataclasses have an empty dict config by default).
            # see https://github.com/pydantic/pydantic/issues/10917
            config = getattr(dataclass, '__pydantic_config__', None)

            from ..dataclasses import is_pydantic_dataclass

            with self._ns_resolver.push(dataclass), self._config_wrapper_stack.push(config):
                if is_pydantic_dataclass(dataclass):
                    if dataclass.__pydantic_fields_complete__():
                        # Copy the field info instances to avoid mutating the `FieldInfo` instances
                        # of the generic dataclass generic origin (e.g. `apply_typevars_map` below).
                        # Note that we don't apply `deepcopy` on `__pydantic_fields__` because we
                        # don't want to copy the `FieldInfo` attributes:
                        fields = {
                            f_name: copy(field_info) for f_name, field_info in dataclass.__pydantic_fields__.items()
                        }
                        if typevars_map:
                            for field in fields.values():
                                field.apply_typevars_map(typevars_map, *self._types_namespace)
                    else:
                        try:
                            fields = rebuild_dataclass_fields(
                                dataclass,
                                config_wrapper=self._config_wrapper,
                                ns_resolver=self._ns_resolver,
                                typevars_map=typevars_map or {},
                            )
                        except NameError as e:
                            raise PydanticUndefinedAnnotation.from_name_error(e) from e
                else:
                    fields = collect_dataclass_fields(
                        dataclass,
                        typevars_map=typevars_map,
                        config_wrapper=self._config_wrapper,
                    )

                if self._config_wrapper.extra == 'allow':
                    # disallow combination of init=False on a dataclass field and extra='allow' on a dataclass
                    for field_name, field in fields.items():
                        if field.init is False:
                            raise PydanticUserError(
                                f'Field {field_name} has `init=False` and dataclass has config setting `extra="allow"`. '
                                f'This combination is not allowed.',
                                code='dataclass-init-false-extra-allow',
                            )

                decorators = dataclass.__dict__.get('__pydantic_decorators__') or DecoratorInfos.build(dataclass)
                # Move kw_only=False args to the start of the list, as this is how vanilla dataclasses work.
                # Note that when kw_only is missing or None, it is treated as equivalent to kw_only=True
                args = sorted(
                    (self._generate_dc_field_schema(k, v, decorators) for k, v in fields.items()),
                    key=lambda a: a.get('kw_only') is not False,
                )
                has_post_init = hasattr(dataclass, '__post_init__')
                has_slots = hasattr(dataclass, '__slots__')

                args_schema = core_schema.dataclass_args_schema(
                    dataclass.__name__,
                    args,
                    computed_fields=[
                        self._computed_field_schema(d, decorators.field_serializers)
                        for d in decorators.computed_fields.values()
                    ],
                    collect_init_only=has_post_init,
                )

                inner_schema = apply_validators(args_schema, decorators.root_validators.values(), None)

                model_validators = decorators.model_validators.values()
                inner_schema = apply_model_validators(inner_schema, model_validators, 'inner')

                core_config = self._config_wrapper.core_config(title=dataclass.__name__)

                dc_schema = core_schema.dataclass_schema(
                    dataclass,
                    inner_schema,
                    generic_origin=origin,
                    post_init=has_post_init,
                    ref=dataclass_ref,
                    fields=[field.name for field in dataclasses.fields(dataclass)],
                    slots=has_slots,
                    config=core_config,
                    # we don't use a custom __setattr__ for dataclasses, so we must
                    # pass along the frozen config setting to the pydantic-core schema
                    frozen=self._config_wrapper_stack.tail.frozen,
                )
                schema = self._apply_model_serializers(dc_schema, decorators.model_serializers.values())
                schema = apply_model_validators(schema, model_validators, 'outer')
                return self.defs.create_definition_reference_schema(schema)

    def _call_schema(self, function: ValidateCallSupportedTypes) -> core_schema.CallSchema:
        """Generate schema for a Callable.

        TODO support functional validators once we support them in Config
        """
        arguments_schema = self._arguments_schema(function)

        return_schema: core_schema.CoreSchema | None = None
        config_wrapper = self._config_wrapper
        if config_wrapper.validate_return:
            sig = signature(function)
            return_hint = sig.return_annotation
            if return_hint is not sig.empty:
                globalns, localns = self._types_namespace
                type_hints = _typing_extra.get_function_type_hints(
                    function, globalns=globalns, localns=localns, include_keys={'return'}
                )
                return_schema = self.generate_schema(type_hints['return'])

        return core_schema.call_schema(
            arguments_schema,
            function,
            return_schema=return_schema,
        )

    def _arguments_schema(
        self, function: ValidateCallSupportedTypes, parameters_callback: ParametersCallback | None = None
    ) -> core_schema.ArgumentsSchema:
        """Generate schema for a Signature."""
        mode_lookup: dict[_ParameterKind, Literal['positional_only', 'positional_or_keyword', 'keyword_only']] = {
            Parameter.POSITIONAL_ONLY: 'positional_only',
            Parameter.POSITIONAL_OR_KEYWORD: 'positional_or_keyword',
            Parameter.KEYWORD_ONLY: 'keyword_only',
        }

        sig = signature(function)
        globalns, localns = self._types_namespace
        type_hints = _typing_extra.get_function_type_hints(function, globalns=globalns, localns=localns)

        arguments_list: list[core_schema.ArgumentsParameter] = []
        var_args_schema: core_schema.CoreSchema | None = None
        var_kwargs_schema: core_schema.CoreSchema | None = None
        var_kwargs_mode: core_schema.VarKwargsMode | None = None

        for i, (name, p) in enumerate(sig.parameters.items()):
            if p.annotation is sig.empty:
                annotation = typing.cast(Any, Any)
            else:
                annotation = type_hints[name]

            if parameters_callback is not None:
                result = parameters_callback(i, name, annotation)
                if result == 'skip':
                    continue

            parameter_mode = mode_lookup.get(p.kind)
            if parameter_mode is not None:
                arg_schema = self._generate_parameter_schema(
                    name, annotation, AnnotationSource.FUNCTION, p.default, parameter_mode
                )
                arguments_list.append(arg_schema)
            elif p.kind == Parameter.VAR_POSITIONAL:
                var_args_schema = self.generate_schema(annotation)
            else:
                assert p.kind == Parameter.VAR_KEYWORD, p.kind

                unpack_type = _typing_extra.unpack_type(annotation)
                if unpack_type is not None:
                    origin = get_origin(unpack_type) or unpack_type
                    if not is_typeddict(origin):
                        raise PydanticUserError(
                            f'Expected a `TypedDict` class inside `Unpack[...]`, got {unpack_type!r}',
                            code='unpack-typed-dict',
                        )
                    non_pos_only_param_names = {
                        name for name, p in sig.parameters.items() if p.kind != Parameter.POSITIONAL_ONLY
                    }
                    overlapping_params = non_pos_only_param_names.intersection(origin.__annotations__)
                    if overlapping_params:
                        raise PydanticUserError(
                            f'Typed dictionary {origin.__name__!r} overlaps with parameter'
                            f'{"s" if len(overlapping_params) >= 2 else ""} '
                            f'{", ".join(repr(p) for p in sorted(overlapping_params))}',
                            code='overlapping-unpack-typed-dict',
                        )

                    var_kwargs_mode = 'unpacked-typed-dict'
                    var_kwargs_schema = self._typed_dict_schema(unpack_type, get_origin(unpack_type))
                else:
                    var_kwargs_mode = 'uniform'
                    var_kwargs_schema = self.generate_schema(annotation)

        return core_schema.arguments_schema(
            arguments_list,
            var_args_schema=var_args_schema,
            var_kwargs_mode=var_kwargs_mode,
            var_kwargs_schema=var_kwargs_schema,
            validate_by_name=self._config_wrapper.validate_by_name,
        )

    def _arguments_v3_schema(
        self, function: ValidateCallSupportedTypes, parameters_callback: ParametersCallback | None = None
    ) -> core_schema.ArgumentsV3Schema:
        mode_lookup: dict[
            _ParameterKind, Literal['positional_only', 'positional_or_keyword', 'var_args', 'keyword_only']
        ] = {
            Parameter.POSITIONAL_ONLY: 'positional_only',
            Parameter.POSITIONAL_OR_KEYWORD: 'positional_or_keyword',
            Parameter.VAR_POSITIONAL: 'var_args',
            Parameter.KEYWORD_ONLY: 'keyword_only',
        }

        sig = signature(function)
        globalns, localns = self._types_namespace
        type_hints = _typing_extra.get_function_type_hints(function, globalns=globalns, localns=localns)

        parameters_list: list[core_schema.ArgumentsV3Parameter] = []

        for i, (name, p) in enumerate(sig.parameters.items()):
            if parameters_callback is not None:
                result = parameters_callback(i, name, p.annotation)
                if result == 'skip':
                    continue

            if p.annotation is Parameter.empty:
                annotation = typing.cast(Any, Any)
            else:
                annotation = type_hints[name]

            parameter_mode = mode_lookup.get(p.kind)
            if parameter_mode is None:
                assert p.kind == Parameter.VAR_KEYWORD, p.kind

                unpack_type = _typing_extra.unpack_type(annotation)
                if unpack_type is not None:
                    origin = get_origin(unpack_type) or unpack_type
                    if not is_typeddict(origin):
                        raise PydanticUserError(
                            f'Expected a `TypedDict` class inside `Unpack[...]`, got {unpack_type!r}',
                            code='unpack-typed-dict',
                        )
                    non_pos_only_param_names = {
                        name for name, p in sig.parameters.items() if p.kind != Parameter.POSITIONAL_ONLY
                    }
                    overlapping_params = non_pos_only_param_names.intersection(origin.__annotations__)
                    if overlapping_params:
                        raise PydanticUserError(
                            f'Typed dictionary {origin.__name__!r} overlaps with parameter'
                            f'{"s" if len(overlapping_params) >= 2 else ""} '
                            f'{", ".join(repr(p) for p in sorted(overlapping_params))}',
                            code='overlapping-unpack-typed-dict',
                        )
                    parameter_mode = 'var_kwargs_unpacked_typed_dict'
                    annotation = unpack_type
                else:
                    parameter_mode = 'var_kwargs_uniform'

            parameters_list.append(
                self._generate_parameter_v3_schema(
                    name, annotation, AnnotationSource.FUNCTION, parameter_mode, default=p.default
                )
            )

        return core_schema.arguments_v3_schema(
            parameters_list,
            validate_by_name=self._config_wrapper.validate_by_name,
        )

    def _unsubstituted_typevar_schema(self, typevar: typing.TypeVar) -> core_schema.CoreSchema:
        try:
            has_default = typevar.has_default()
        except AttributeError:
            # Happens if using `typing.TypeVar` (and not `typing_extensions`) on Python < 3.13
            pass
        else:
            if has_default:
                return self.generate_schema(typevar.__default__)

        if constraints := typevar.__constraints__:
            return self._union_schema(typing.Union[constraints])

        if bound := typevar.__bound__:
            schema = self.generate_schema(bound)
            schema['serialization'] = core_schema.wrap_serializer_function_ser_schema(
                lambda x, h: h(x),
                schema=core_schema.any_schema(),
            )
            return schema

        return core_schema.any_schema()

    def _computed_field_schema(
        self,
        d: Decorator[ComputedFieldInfo],
        field_serializers: dict[str, Decorator[FieldSerializerDecoratorInfo]],
    ) -> core_schema.ComputedField:
        if d.info.return_type is not PydanticUndefined:
            return_type = d.info.return_type
        else:
            try:
                # Do not pass in globals as the function could be defined in a different module.
                # Instead, let `get_callable_return_type` infer the globals to use, but still pass
                # in locals that may contain a parent/rebuild namespace:
                return_type = _decorators.get_callable_return_type(d.func, localns=self._types_namespace.locals)
            except NameError as e:
                raise PydanticUndefinedAnnotation.from_name_error(e) from e
        if return_type is PydanticUndefined:
            raise PydanticUserError(
                'Computed field is missing return type annotation or specifying `return_type`'
                ' to the `@computed_field` decorator (e.g. `@computed_field(return_type=int | str)`)',
                code='model-field-missing-annotation',
            )

        return_type = replace_types(return_type, self._typevars_map)
        # Create a new ComputedFieldInfo so that different type parametrizations of the same
        # generic model's computed field can have different return types.
        d.info = dataclasses.replace(d.info, return_type=return_type)
        return_type_schema = self.generate_schema(return_type)
        # Apply serializers to computed field if there exist
        return_type_schema = self._apply_field_serializers(
            return_type_schema,
            filter_field_decorator_info_by_field(field_serializers.values(), d.cls_var_name),
        )

        alias_generator = self._config_wrapper.alias_generator
        if alias_generator is not None:
            self._apply_alias_generator_to_computed_field_info(
                alias_generator=alias_generator, computed_field_info=d.info, computed_field_name=d.cls_var_name
            )
        self._apply_field_title_generator_to_field_info(self._config_wrapper, d.info, d.cls_var_name)

        pydantic_js_updates, pydantic_js_extra = _extract_json_schema_info_from_field_info(d.info)
        core_metadata: dict[str, Any] = {}
        update_core_metadata(
            core_metadata,
            pydantic_js_updates={'readOnly': True, **(pydantic_js_updates if pydantic_js_updates else {})},
            pydantic_js_extra=pydantic_js_extra,
        )
        return core_schema.computed_field(
            d.cls_var_name, return_schema=return_type_schema, alias=d.info.alias, metadata=core_metadata
        )

    def _annotated_schema(self, annotated_type: Any) -> core_schema.CoreSchema:
        """Generate schema for an Annotated type, e.g. `Annotated[int, Field(...)]` or `Annotated[int, Gt(0)]`."""
        FieldInfo = import_cached_field_info()
        source_type, *annotations = self._get_args_resolving_forward_refs(
            annotated_type,
            required=True,
        )
        schema = self._apply_annotations(source_type, annotations)
        # put the default validator last so that TypeAdapter.get_default_value() works
        # even if there are function validators involved
        for annotation in annotations:
            if isinstance(annotation, FieldInfo):
                schema = wrap_default(annotation, schema)
        return schema

    def _apply_annotations(
        self,
        source_type: Any,
        annotations: list[Any],
        transform_inner_schema: Callable[[CoreSchema], CoreSchema] = lambda x: x,
    ) -> CoreSchema:
        """Apply arguments from `Annotated` or from `FieldInfo` to a schema.

        This gets called by `GenerateSchema._annotated_schema` but differs from it in that it does
        not expect `source_type` to be an `Annotated` object, it expects it to be  the first argument of that
        (in other words, `GenerateSchema._annotated_schema` just unpacks `Annotated`, this process it).
        """
        annotations = list(_known_annotated_metadata.expand_grouped_metadata(annotations))

        pydantic_js_annotation_functions: list[GetJsonSchemaFunction] = []

        def inner_handler(obj: Any) -> CoreSchema:
            schema = self._generate_schema_from_get_schema_method(obj, source_type)

            if schema is None:
                schema = self._generate_schema_inner(obj)

            metadata_js_function = _extract_get_pydantic_json_schema(obj)
            if metadata_js_function is not None:
                metadata_schema = resolve_original_schema(schema, self.defs)
                if metadata_schema is not None:
                    self._add_js_function(metadata_schema, metadata_js_function)
            return transform_inner_schema(schema)

        get_inner_schema = CallbackGetCoreSchemaHandler(inner_handler, self)

        for annotation in annotations:
            if annotation is None:
                continue
            get_inner_schema = self._get_wrapped_inner_schema(
                get_inner_schema, annotation, pydantic_js_annotation_functions
            )

        schema = get_inner_schema(source_type)
        if pydantic_js_annotation_functions:
            core_metadata = schema.setdefault('metadata', {})
            update_core_metadata(core_metadata, pydantic_js_annotation_functions=pydantic_js_annotation_functions)
        return _add_custom_serialization_from_json_encoders(self._config_wrapper.json_encoders, source_type, schema)

    def _apply_single_annotation(self, schema: core_schema.CoreSchema, metadata: Any) -> core_schema.CoreSchema:
        FieldInfo = import_cached_field_info()

        if isinstance(metadata, FieldInfo):
            for field_metadata in metadata.metadata:
                schema = self._apply_single_annotation(schema, field_metadata)

            if metadata.discriminator is not None:
                schema = self._apply_discriminator_to_union(schema, metadata.discriminator)
            return schema

        if schema['type'] == 'nullable':
            # for nullable schemas, metadata is automatically applied to the inner schema
            inner = schema.get('schema', core_schema.any_schema())
            inner = self._apply_single_annotation(inner, metadata)
            if inner:
                schema['schema'] = inner
            return schema

        original_schema = schema
        ref = schema.get('ref')
        if ref is not None:
            schema = schema.copy()
            new_ref = ref + f'_{repr(metadata)}'
            if (existing := self.defs.get_schema_from_ref(new_ref)) is not None:
                return existing
            schema['ref'] = new_ref  # pyright: ignore[reportGeneralTypeIssues]
        elif schema['type'] == 'definition-ref':
            ref = schema['schema_ref']
            if (referenced_schema := self.defs.get_schema_from_ref(ref)) is not None:
                schema = referenced_schema.copy()
                new_ref = ref + f'_{repr(metadata)}'
                if (existing := self.defs.get_schema_from_ref(new_ref)) is not None:
                    return existing
                schema['ref'] = new_ref  # pyright: ignore[reportGeneralTypeIssues]

        maybe_updated_schema = _known_annotated_metadata.apply_known_metadata(metadata, schema)

        if maybe_updated_schema is not None:
            return maybe_updated_schema
        return original_schema

    def _apply_single_annotation_json_schema(
        self, schema: core_schema.CoreSchema, metadata: Any
    ) -> core_schema.CoreSchema:
        FieldInfo = import_cached_field_info()

        if isinstance(metadata, FieldInfo):
            for field_metadata in metadata.metadata:
                schema = self._apply_single_annotation_json_schema(schema, field_metadata)

            pydantic_js_updates, pydantic_js_extra = _extract_json_schema_info_from_field_info(metadata)
            core_metadata = schema.setdefault('metadata', {})
            update_core_metadata(
                core_metadata, pydantic_js_updates=pydantic_js_updates, pydantic_js_extra=pydantic_js_extra
            )
        return schema

    def _get_wrapped_inner_schema(
        self,
        get_inner_schema: GetCoreSchemaHandler,
        annotation: Any,
        pydantic_js_annotation_functions: list[GetJsonSchemaFunction],
    ) -> CallbackGetCoreSchemaHandler:
        annotation_get_schema: GetCoreSchemaFunction | None = getattr(annotation, '__get_pydantic_core_schema__', None)

        def new_handler(source: Any) -> core_schema.CoreSchema:
            if annotation_get_schema is not None:
                schema = annotation_get_schema(source, get_inner_schema)
            else:
                schema = get_inner_schema(source)
                schema = self._apply_single_annotation(schema, annotation)
                schema = self._apply_single_annotation_json_schema(schema, annotation)

            metadata_js_function = _extract_get_pydantic_json_schema(annotation)
            if metadata_js_function is not None:
                pydantic_js_annotation_functions.append(metadata_js_function)
            return schema

        return CallbackGetCoreSchemaHandler(new_handler, self)

    def _apply_field_serializers(
        self,
        schema: core_schema.CoreSchema,
        serializers: list[Decorator[FieldSerializerDecoratorInfo]],
    ) -> core_schema.CoreSchema:
        """Apply field serializers to a schema."""
        if serializers:
            schema = copy(schema)
            if schema['type'] == 'definitions':
                inner_schema = schema['schema']
                schema['schema'] = self._apply_field_serializers(inner_schema, serializers)
                return schema
            elif 'ref' in schema:
                schema = self.defs.create_definition_reference_schema(schema)

            # use the last serializer to make it easy to override a serializer set on a parent model
            serializer = serializers[-1]
            is_field_serializer, info_arg = inspect_field_serializer(serializer.func, serializer.info.mode)

            if serializer.info.return_type is not PydanticUndefined:
                return_type = serializer.info.return_type
            else:
                try:
                    # Do not pass in globals as the function could be defined in a different module.
                    # Instead, let `get_callable_return_type` infer the globals to use, but still pass
                    # in locals that may contain a parent/rebuild namespace:
                    return_type = _decorators.get_callable_return_type(
                        serializer.func, localns=self._types_namespace.locals
                    )
                except NameError as e:
                    raise PydanticUndefinedAnnotation.from_name_error(e) from e

            if return_type is PydanticUndefined:
                return_schema = None
            else:
                return_schema = self.generate_schema(return_type)

            if serializer.info.mode == 'wrap':
                schema['serialization'] = core_schema.wrap_serializer_function_ser_schema(
                    serializer.func,
                    is_field_serializer=is_field_serializer,
                    info_arg=info_arg,
                    return_schema=return_schema,
                    when_used=serializer.info.when_used,
                )
            else:
                assert serializer.info.mode == 'plain'
                schema['serialization'] = core_schema.plain_serializer_function_ser_schema(
                    serializer.func,
                    is_field_serializer=is_field_serializer,
                    info_arg=info_arg,
                    return_schema=return_schema,
                    when_used=serializer.info.when_used,
                )
        return schema

    def _apply_model_serializers(
        self, schema: core_schema.CoreSchema, serializers: Iterable[Decorator[ModelSerializerDecoratorInfo]]
    ) -> core_schema.CoreSchema:
        """Apply model serializers to a schema."""
        ref: str | None = schema.pop('ref', None)  # type: ignore
        if serializers:
            serializer = list(serializers)[-1]
            info_arg = inspect_model_serializer(serializer.func, serializer.info.mode)

            if serializer.info.return_type is not PydanticUndefined:
                return_type = serializer.info.return_type
            else:
                try:
                    # Do not pass in globals as the function could be defined in a different module.
                    # Instead, let `get_callable_return_type` infer the globals to use, but still pass
                    # in locals that may contain a parent/rebuild namespace:
                    return_type = _decorators.get_callable_return_type(
                        serializer.func, localns=self._types_namespace.locals
                    )
                except NameError as e:
                    raise PydanticUndefinedAnnotation.from_name_error(e) from e

            if return_type is PydanticUndefined:
                return_schema = None
            else:
                return_schema = self.generate_schema(return_type)

            if serializer.info.mode == 'wrap':
                ser_schema: core_schema.SerSchema = core_schema.wrap_serializer_function_ser_schema(
                    serializer.func,
                    info_arg=info_arg,
                    return_schema=return_schema,
                    when_used=serializer.info.when_used,
                )
            else:
                # plain
                ser_schema = core_schema.plain_serializer_function_ser_schema(
                    serializer.func,
                    info_arg=info_arg,
                    return_schema=return_schema,
                    when_used=serializer.info.when_used,
                )
            schema['serialization'] = ser_schema
        if ref:
            schema['ref'] = ref  # type: ignore
        return schema


_VALIDATOR_F_MATCH: Mapping[
    tuple[FieldValidatorModes, Literal['no-info', 'with-info']],
    Callable[[Callable[..., Any], core_schema.CoreSchema, str | None], core_schema.CoreSchema],
] = {
    ('before', 'no-info'): lambda f, schema, _: core_schema.no_info_before_validator_function(f, schema),
    ('after', 'no-info'): lambda f, schema, _: core_schema.no_info_after_validator_function(f, schema),
    ('plain', 'no-info'): lambda f, _1, _2: core_schema.no_info_plain_validator_function(f),
    ('wrap', 'no-info'): lambda f, schema, _: core_schema.no_info_wrap_validator_function(f, schema),
    ('before', 'with-info'): lambda f, schema, field_name: core_schema.with_info_before_validator_function(
        f, schema, field_name=field_name
    ),
    ('after', 'with-info'): lambda f, schema, field_name: core_schema.with_info_after_validator_function(
        f, schema, field_name=field_name
    ),
    ('plain', 'with-info'): lambda f, _, field_name: core_schema.with_info_plain_validator_function(
        f, field_name=field_name
    ),
    ('wrap', 'with-info'): lambda f, schema, field_name: core_schema.with_info_wrap_validator_function(
        f, schema, field_name=field_name
    ),
}


# TODO V3: this function is only used for deprecated decorators. It should
# be removed once we drop support for those.
def apply_validators(
    schema: core_schema.CoreSchema,
    validators: Iterable[Decorator[RootValidatorDecoratorInfo]]
    | Iterable[Decorator[ValidatorDecoratorInfo]]
    | Iterable[Decorator[FieldValidatorDecoratorInfo]],
    field_name: str | None,
) -> core_schema.CoreSchema:
    """Apply validators to a schema.

    Args:
        schema: The schema to apply validators on.
        validators: An iterable of validators.
        field_name: The name of the field if validators are being applied to a model field.

    Returns:
        The updated schema.
    """
    for validator in validators:
        info_arg = inspect_validator(validator.func, validator.info.mode)
        val_type = 'with-info' if info_arg else 'no-info'

        schema = _VALIDATOR_F_MATCH[(validator.info.mode, val_type)](validator.func, schema, field_name)
    return schema


def _validators_require_validate_default(validators: Iterable[Decorator[ValidatorDecoratorInfo]]) -> bool:
    """In v1, if any of the validators for a field had `always=True`, the default value would be validated.

    This serves as an auxiliary function for re-implementing that logic, by looping over a provided
    collection of (v1-style) ValidatorDecoratorInfo's and checking if any of them have `always=True`.

    We should be able to drop this function and the associated logic calling it once we drop support
    for v1-style validator decorators. (Or we can extend it and keep it if we add something equivalent
    to the v1-validator `always` kwarg to `field_validator`.)
    """
    for validator in validators:
        if validator.info.always:
            return True
    return False


def apply_model_validators(
    schema: core_schema.CoreSchema,
    validators: Iterable[Decorator[ModelValidatorDecoratorInfo]],
    mode: Literal['inner', 'outer', 'all'],
) -> core_schema.CoreSchema:
    """Apply model validators to a schema.

    If mode == 'inner', only "before" validators are applied
    If mode == 'outer', validators other than "before" are applied
    If mode == 'all', all validators are applied

    Args:
        schema: The schema to apply validators on.
        validators: An iterable of validators.
        mode: The validator mode.

    Returns:
        The updated schema.
    """
    ref: str | None = schema.pop('ref', None)  # type: ignore
    for validator in validators:
        if mode == 'inner' and validator.info.mode != 'before':
            continue
        if mode == 'outer' and validator.info.mode == 'before':
            continue
        info_arg = inspect_validator(validator.func, validator.info.mode)
        if validator.info.mode == 'wrap':
            if info_arg:
                schema = core_schema.with_info_wrap_validator_function(function=validator.func, schema=schema)
            else:
                schema = core_schema.no_info_wrap_validator_function(function=validator.func, schema=schema)
        elif validator.info.mode == 'before':
            if info_arg:
                schema = core_schema.with_info_before_validator_function(function=validator.func, schema=schema)
            else:
                schema = core_schema.no_info_before_validator_function(function=validator.func, schema=schema)
        else:
            assert validator.info.mode == 'after'
            if info_arg:
                schema = core_schema.with_info_after_validator_function(function=validator.func, schema=schema)
            else:
                schema = core_schema.no_info_after_validator_function(function=validator.func, schema=schema)
    if ref:
        schema['ref'] = ref  # type: ignore
    return schema


def wrap_default(field_info: FieldInfo, schema: core_schema.CoreSchema) -> core_schema.CoreSchema:
    """Wrap schema with default schema if default value or `default_factory` are available.

    Args:
        field_info: The field info object.
        schema: The schema to apply default on.

    Returns:
        Updated schema by default value or `default_factory`.
    """
    if field_info.default_factory:
        return core_schema.with_default_schema(
            schema,
            default_factory=field_info.default_factory,
            default_factory_takes_data=takes_validated_data_argument(field_info.default_factory),
            validate_default=field_info.validate_default,
        )
    elif field_info.default is not PydanticUndefined:
        return core_schema.with_default_schema(
            schema, default=field_info.default, validate_default=field_info.validate_default
        )
    else:
        return schema


def _extract_get_pydantic_json_schema(tp: Any) -> GetJsonSchemaFunction | None:
    """Extract `__get_pydantic_json_schema__` from a type, handling the deprecated `__modify_schema__`."""
    js_modify_function = getattr(tp, '__get_pydantic_json_schema__', None)

    if hasattr(tp, '__modify_schema__'):
        BaseModel = import_cached_base_model()

        has_custom_v2_modify_js_func = (
            js_modify_function is not None
            and BaseModel.__get_pydantic_json_schema__.__func__  # type: ignore
            not in (js_modify_function, getattr(js_modify_function, '__func__', None))
        )

        if not has_custom_v2_modify_js_func:
            cls_name = getattr(tp, '__name__', None)
            raise PydanticUserError(
                f'The `__modify_schema__` method is not supported in Pydantic v2. '
                f'Use `__get_pydantic_json_schema__` instead{f" in class `{cls_name}`" if cls_name else ""}.',
                code='custom-json-schema',
            )

    if (origin := get_origin(tp)) is not None:
        # Generic aliases proxy attribute access to the origin, *except* dunder attributes,
        # such as `__get_pydantic_json_schema__`, hence the explicit check.
        return _extract_get_pydantic_json_schema(origin)

    if js_modify_function is None:
        return None

    return js_modify_function


class _CommonField(TypedDict):
    schema: core_schema.CoreSchema
    validation_alias: str | list[str | int] | list[list[str | int]] | None
    serialization_alias: str | None
    serialization_exclude: bool | None
    frozen: bool | None
    metadata: dict[str, Any]


def _common_field(
    schema: core_schema.CoreSchema,
    *,
    validation_alias: str | list[str | int] | list[list[str | int]] | None = None,
    serialization_alias: str | None = None,
    serialization_exclude: bool | None = None,
    frozen: bool | None = None,
    metadata: Any = None,
) -> _CommonField:
    return {
        'schema': schema,
        'validation_alias': validation_alias,
        'serialization_alias': serialization_alias,
        'serialization_exclude': serialization_exclude,
        'frozen': frozen,
        'metadata': metadata,
    }


def resolve_original_schema(schema: CoreSchema, definitions: _Definitions) -> CoreSchema | None:
    if schema['type'] == 'definition-ref':
        return definitions.get_schema_from_ref(schema['schema_ref'])
    elif schema['type'] == 'definitions':
        return schema['schema']
    else:
        return schema


def _inlining_behavior(
    def_ref: core_schema.DefinitionReferenceSchema,
) -> Literal['inline', 'keep', 'preserve_metadata']:
    """Determine the inlining behavior of the `'definition-ref'` schema.

    - If no `'serialization'` schema and no metadata is attached, the schema can safely be inlined.
    - If it has metadata but only related to the deferred discriminator application, it can be inlined
      provided that such metadata is kept.
    - Otherwise, the schema should not be inlined. Doing so would remove the `'serialization'` schema or metadata.
    """
    if 'serialization' in def_ref:
        return 'keep'
    metadata = def_ref.get('metadata')
    if not metadata:
        return 'inline'
    if len(metadata) == 1 and 'pydantic_internal_union_discriminator' in metadata:
        return 'preserve_metadata'
    return 'keep'


class _Definitions:
    """Keeps track of references and definitions."""

    _recursively_seen: set[str]
    """A set of recursively seen references.

    When a referenceable type is encountered, the `get_schema_or_ref` context manager is
    entered to compute the reference. If the type references itself by some way (e.g. for
    a dataclass a Pydantic model, the class can be referenced as a field annotation),
    entering the context manager again will yield a `'definition-ref'` schema that should
    short-circuit the normal generation process, as the reference was already in this set.
    """

    _definitions: dict[str, core_schema.CoreSchema]
    """A mapping of references to their corresponding schema.

    When a schema for a referenceable type is generated, it is stored in this mapping. If the
    same type is encountered again, the reference is yielded by the `get_schema_or_ref` context
    manager.
    """

    def __init__(self) -> None:
        self._recursively_seen = set()
        self._definitions = {}

    @contextmanager
    def get_schema_or_ref(self, tp: Any, /) -> Generator[tuple[str, core_schema.DefinitionReferenceSchema | None]]:
        """Get a definition for `tp` if one exists.

        If a definition exists, a tuple of `(ref_string, CoreSchema)` is returned.
        If no definition exists yet, a tuple of `(ref_string, None)` is returned.

        Note that the returned `CoreSchema` will always be a `DefinitionReferenceSchema`,
        not the actual definition itself.

        This should be called for any type that can be identified by reference.
        This includes any recursive types.

        At present the following types can be named/recursive:

        - Pydantic model
        - Pydantic and stdlib dataclasses
        - Typed dictionaries
        - Named tuples
        - `TypeAliasType` instances
        - Enums
        """
        ref = get_type_ref(tp)
        # return the reference if we're either (1) in a cycle or (2) it the reference was already encountered:
        if ref in self._recursively_seen or ref in self._definitions:
            yield (ref, core_schema.definition_reference_schema(ref))
        else:
            self._recursively_seen.add(ref)
            try:
                yield (ref, None)
            finally:
                self._recursively_seen.discard(ref)

    def get_schema_from_ref(self, ref: str) -> CoreSchema | None:
        """Resolve the schema from the given reference."""
        return self._definitions.get(ref)

    def create_definition_reference_schema(self, schema: CoreSchema) -> core_schema.DefinitionReferenceSchema:
        """Store the schema as a definition and return a `'definition-reference'` schema pointing to it.

        The schema must have a reference attached to it.
        """
        ref = schema['ref']  # pyright: ignore
        self._definitions[ref] = schema
        return core_schema.definition_reference_schema(ref)

    def unpack_definitions(self, schema: core_schema.DefinitionsSchema) -> CoreSchema:
        """Store the definitions of the `'definitions'` core schema and return the inner core schema."""
        for def_schema in schema['definitions']:
            self._definitions[def_schema['ref']] = def_schema  # pyright: ignore
        return schema['schema']

    def finalize_schema(self, schema: CoreSchema) -> CoreSchema:
        """Finalize the core schema.

        This traverses the core schema and referenced definitions, replaces `'definition-ref'` schemas
        by the referenced definition if possible, and applies deferred discriminators.
        """
        definitions = self._definitions
        try:
            gather_result = gather_schemas_for_cleaning(
                schema,
                definitions=definitions,
            )
        except MissingDefinitionError as e:
            raise InvalidSchemaError from e

        remaining_defs: dict[str, CoreSchema] = {}

        # Note: this logic doesn't play well when core schemas with deferred discriminator metadata
        # and references are encountered. See the `test_deferred_discriminated_union_and_references()` test.
        for ref, inlinable_def_ref in gather_result['collected_references'].items():
            if inlinable_def_ref is not None and (inlining_behavior := _inlining_behavior(inlinable_def_ref)) != 'keep':
                if inlining_behavior == 'inline':
                    # `ref` was encountered, and only once:
                    #  - `inlinable_def_ref` is a `'definition-ref'` schema and is guaranteed to be
                    #    the only one. Transform it into the definition it points to.
                    #  - Do not store the definition in the `remaining_defs`.
                    inlinable_def_ref.clear()  # pyright: ignore[reportAttributeAccessIssue]
                    inlinable_def_ref.update(self._resolve_definition(ref, definitions))  # pyright: ignore
                elif inlining_behavior == 'preserve_metadata':
                    # `ref` was encountered, and only once, but contains discriminator metadata.
                    # We will do the same thing as if `inlining_behavior` was `'inline'`, but make
                    # sure to keep the metadata for the deferred discriminator application logic below.
                    meta = inlinable_def_ref.pop('metadata')
                    inlinable_def_ref.clear()  # pyright: ignore[reportAttributeAccessIssue]
                    inlinable_def_ref.update(self._resolve_definition(ref, definitions))  # pyright: ignore
                    inlinable_def_ref['metadata'] = meta
            else:
                # `ref` was encountered, at least two times (or only once, but with metadata or a serialization schema):
                # - Do not inline the `'definition-ref'` schemas (they are not provided in the gather result anyway).
                # - Store the the definition in the `remaining_defs`
                remaining_defs[ref] = self._resolve_definition(ref, definitions)

        for cs in gather_result['deferred_discriminator_schemas']:
            discriminator: str | None = cs['metadata'].pop('pydantic_internal_union_discriminator', None)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            if discriminator is None:
                # This can happen in rare scenarios, when a deferred schema is present multiple times in the
                # gather result (e.g. when using the `Sequence` type -- see `test_sequence_discriminated_union()`).
                # In this case, a previous loop iteration applied the discriminator and so we can just skip it here.
                continue
            applied = _discriminated_union.apply_discriminator(cs.copy(), discriminator, remaining_defs)
            # Mutate the schema directly to have the discriminator applied
            cs.clear()  # pyright: ignore[reportAttributeAccessIssue]
            cs.update(applied)  # pyright: ignore

        if remaining_defs:
            schema = core_schema.definitions_schema(schema=schema, definitions=[*remaining_defs.values()])
        return schema

    def _resolve_definition(self, ref: str, definitions: dict[str, CoreSchema]) -> CoreSchema:
        definition = definitions[ref]
        if definition['type'] != 'definition-ref':
            return definition

        # Some `'definition-ref'` schemas might act as "intermediate" references (e.g. when using
        # a PEP 695 type alias (which is referenceable) that references another PEP 695 type alias):
        visited: set[str] = set()
        while definition['type'] == 'definition-ref' and _inlining_behavior(definition) == 'inline':
            schema_ref = definition['schema_ref']
            if schema_ref in visited:
                raise PydanticUserError(
                    f'{ref} contains a circular reference to itself.', code='circular-reference-schema'
                )
            visited.add(schema_ref)
            definition = definitions[schema_ref]
        return {**definition, 'ref': ref}  # pyright: ignore[reportReturnType]


class _FieldNameStack:
    __slots__ = ('_stack',)

    def __init__(self) -> None:
        self._stack: list[str] = []

    @contextmanager
    def push(self, field_name: str) -> Iterator[None]:
        self._stack.append(field_name)
        yield
        self._stack.pop()

    def get(self) -> str | None:
        if self._stack:
            return self._stack[-1]
        else:
            return None


class _ModelTypeStack:
    __slots__ = ('_stack',)

    def __init__(self) -> None:
        self._stack: list[type] = []

    @contextmanager
    def push(self, type_obj: type) -> Iterator[None]:
        self._stack.append(type_obj)
        yield
        self._stack.pop()

    def get(self) -> type | None:
        if self._stack:
            return self._stack[-1]
        else:
            return None