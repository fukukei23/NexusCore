
# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\model_management_endpoints.py ===
"""
Allow proxy admin to add/update/delete models in the db

Currently most endpoints are in `proxy_server.py`, but those should  be moved here over time.

Endpoints here: 

model/{model_id}/update - PATCH endpoint for model update.
"""

#### MODEL MANAGEMENT ####

import asyncio
import datetime
import json
import uuid
from typing import Dict, List, Literal, Optional, Tuple, Union, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from litellm._logging import verbose_proxy_logger
from litellm.constants import LITELLM_PROXY_ADMIN_NAME
from litellm.proxy._types import (
    CommonProxyErrors,
    LiteLLM_ProxyModelTable,
    LiteLLM_TeamTable,
    LitellmTableNames,
    LitellmUserRoles,
    ModelInfoDelete,
    PrismaCompatibleUpdateDBModel,
    ProxyErrorTypes,
    ProxyException,
    TeamModelAddRequest,
    UpdateTeamRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_utils.encrypt_decrypt_utils import encrypt_value_helper
from litellm.proxy.management_endpoints.common_utils import _is_user_team_admin
from litellm.proxy.management_endpoints.team_endpoints import (
    team_model_add,
    update_team,
)
from litellm.proxy.management_helpers.audit_logs import create_object_audit_log
from litellm.proxy.utils import PrismaClient
from litellm.types.router import (
    Deployment,
    DeploymentTypedDict,
    LiteLLMParamsTypedDict,
    updateDeployment,
)
from litellm.utils import get_utc_datetime

router = APIRouter()


async def get_db_model(
    model_id: str, prisma_client: PrismaClient
) -> Optional[Deployment]:
    db_model = cast(
        Optional[BaseModel],
        await prisma_client.db.litellm_proxymodeltable.find_unique(
            where={"model_id": model_id}
        ),
    )

    if not db_model:
        return None

    deployment_pydantic_obj = Deployment(**db_model.model_dump(exclude_none=True))
    return deployment_pydantic_obj


def update_db_model(
    db_model: Deployment, updated_patch: updateDeployment
) -> PrismaCompatibleUpdateDBModel:
    merged_deployment_dict = DeploymentTypedDict(
        model_name=db_model.model_name,
        litellm_params=LiteLLMParamsTypedDict(
            **db_model.litellm_params.model_dump(exclude_none=True)  # type: ignore
        ),
        model_info=db_model.model_info.model_dump(exclude_none=True),
    )
    # update model name
    if updated_patch.model_name:
        merged_deployment_dict["model_name"] = updated_patch.model_name

    # update litellm params
    if updated_patch.litellm_params:
        # Encrypt any sensitive values
        encrypted_params = {
            k: encrypt_value_helper(v)
            for k, v in updated_patch.litellm_params.model_dump(
                exclude_none=True
            ).items()
        }

        merged_deployment_dict["litellm_params"].update(encrypted_params)  # type: ignore

    # update model info
    if updated_patch.model_info:
        if "model_info" not in merged_deployment_dict:
            merged_deployment_dict["model_info"] = {}
        merged_deployment_dict["model_info"].update(
            updated_patch.model_info.model_dump(exclude_none=True)
        )

    # convert to prisma compatible format

    prisma_compatible_model_dict = PrismaCompatibleUpdateDBModel()
    if "model_name" in merged_deployment_dict:
        prisma_compatible_model_dict["model_name"] = merged_deployment_dict[
            "model_name"
        ]

    if "litellm_params" in merged_deployment_dict:
        prisma_compatible_model_dict["litellm_params"] = json.dumps(
            merged_deployment_dict["litellm_params"]
        )

    if "model_info" in merged_deployment_dict:
        model_info = merged_deployment_dict["model_info"]
        for key, value in model_info.items():
            if isinstance(value, datetime.datetime):
                model_info[key] = value.isoformat()
        prisma_compatible_model_dict["model_info"] = json.dumps(model_info)

    return prisma_compatible_model_dict


@router.patch(
    "/model/{model_id}/update",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def patch_model(
    model_id: str,  # Get model_id from path parameter
    patch_data: updateDeployment,  # Create a specific schema for PATCH operations
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    PATCH Endpoint for partial model updates.

    Only updates the fields specified in the request while preserving other existing values.
    Follows proper PATCH semantics by only modifying provided fields.

    Args:
        model_id: The ID of the model to update
        patch_data: The fields to update and their new values
        user_api_key_dict: User authentication information

    Returns:
        Updated model information

    Raises:
        ProxyException: For various error conditions including authentication and database errors
    """
    from litellm.proxy.proxy_server import (
        litellm_proxy_admin_name,
        llm_router,
        premium_user,
        prisma_client,
        store_model_in_db,
    )

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )

        # Verify model exists and is stored in DB
        if not store_model_in_db:
            raise ProxyException(
                message="Model updates only supported for DB-stored models",
                type=ProxyErrorTypes.validation_error.value,
                code=status.HTTP_400_BAD_REQUEST,
                param=None,
            )

        # Fetch existing model
        db_model = await get_db_model(model_id=model_id, prisma_client=prisma_client)

        if db_model is None:
            # Check if model exists in config but not DB
            if llm_router and llm_router.get_deployment(model_id=model_id) is not None:
                raise ProxyException(
                    message="Cannot edit config-based model. Store model in DB via /model/new first.",
                    type=ProxyErrorTypes.validation_error.value,
                    code=status.HTTP_400_BAD_REQUEST,
                    param=None,
                )
            raise ProxyException(
                message=f"Model {model_id} not found on proxy.",
                type=ProxyErrorTypes.not_found_error,
                code=status.HTTP_404_NOT_FOUND,
                param=None,
            )

        await ModelManagementAuthChecks.can_user_make_model_call(
            model_params=db_model,
            user_api_key_dict=user_api_key_dict,
            prisma_client=prisma_client,
            premium_user=premium_user,
        )
        # Create update dictionary only for provided fields
        update_data = update_db_model(db_model=db_model, updated_patch=patch_data)

        # Add metadata about update
        update_data["updated_by"] = (
            user_api_key_dict.user_id or litellm_proxy_admin_name
        )
        update_data["updated_at"] = cast(str, get_utc_datetime())

        # Perform partial update
        updated_model = await prisma_client.db.litellm_proxymodeltable.update(
            where={"model_id": model_id},
            data=update_data,
        )
        
        # Clear cache and reload models
        await clear_cache()

        return updated_model

    except Exception as e:
        verbose_proxy_logger.exception(f"Error in patch_model: {str(e)}")

        if isinstance(e, (HTTPException, ProxyException)):
            raise e

        raise ProxyException(
            message=f"Error updating model: {str(e)}",
            type=ProxyErrorTypes.internal_server_error,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            param=None,
        )


################################# Helper Functions #################################
####################################################################################
####################################################################################
####################################################################################


async def _add_model_to_db(
    model_params: Deployment,
    user_api_key_dict: UserAPIKeyAuth,
    prisma_client: PrismaClient,
    new_encryption_key: Optional[str] = None,
    should_create_model_in_db: bool = True,
) -> Optional[LiteLLM_ProxyModelTable]:
    # encrypt litellm params #
    _litellm_params_dict = model_params.litellm_params.dict(exclude_none=True)
    _orignal_litellm_model_name = model_params.litellm_params.model
    for k, v in _litellm_params_dict.items():
        encrypted_value = encrypt_value_helper(
            value=v, new_encryption_key=new_encryption_key
        )
        model_params.litellm_params[k] = encrypted_value
    _data: dict = {
        "model_id": model_params.model_info.id,
        "model_name": model_params.model_name,
        "litellm_params": model_params.litellm_params.model_dump_json(exclude_none=True),  # type: ignore
        "model_info": model_params.model_info.model_dump_json(  # type: ignore
            exclude_none=True
        ),
        "created_by": user_api_key_dict.user_id or LITELLM_PROXY_ADMIN_NAME,
        "updated_by": user_api_key_dict.user_id or LITELLM_PROXY_ADMIN_NAME,
    }
    if model_params.model_info.id is not None:
        _data["model_id"] = model_params.model_info.id
    if should_create_model_in_db:
        model_response = await prisma_client.db.litellm_proxymodeltable.create(
            data=_data  # type: ignore
        )
    else:
        model_response = LiteLLM_ProxyModelTable(**_data)
    return model_response


async def _add_team_model_to_db(
    model_params: Deployment,
    user_api_key_dict: UserAPIKeyAuth,
    prisma_client: PrismaClient,
) -> Optional[LiteLLM_ProxyModelTable]:
    """
    If 'team_id' is provided,

    - generate a unique 'model_name' for the model (e.g. 'model_name_{team_id}_{uuid})
    - store the model in the db with the unique 'model_name'
    - store a team model alias mapping {"model_name": "model_name_{team_id}_{uuid}"}
    """
    _team_id = model_params.model_info.team_id
    if _team_id is None:
        return None
    original_model_name = model_params.model_name
    if original_model_name:
        model_params.model_info.team_public_model_name = original_model_name

    unique_model_name = f"model_name_{_team_id}_{uuid.uuid4()}"

    model_params.model_name = unique_model_name

    ## CREATE MODEL IN DB ##
    model_response = await _add_model_to_db(
        model_params=model_params,
        user_api_key_dict=user_api_key_dict,
        prisma_client=prisma_client,
    )

    ## CREATE MODEL ALIAS IN DB ##
    await update_team(
        data=UpdateTeamRequest(
            team_id=_team_id,
            model_aliases={original_model_name: unique_model_name},
        ),
        user_api_key_dict=user_api_key_dict,
        http_request=Request(scope={"type": "http"}),
    )

    # add model to team object
    await team_model_add(
        data=TeamModelAddRequest(
            team_id=_team_id,
            models=[original_model_name],
        ),
        http_request=Request(scope={"type": "http"}),
        user_api_key_dict=user_api_key_dict,
    )

    return model_response


class ModelManagementAuthChecks:
    """
    Common auth checks for model management endpoints
    """

    @staticmethod
    def can_user_make_team_model_call(
        team_id: str,
        user_api_key_dict: UserAPIKeyAuth,
        team_obj: Optional[LiteLLM_TeamTable] = None,
        premium_user: bool = False,
    ) -> Literal[True]:
        if premium_user is False:
            raise HTTPException(
                status_code=403,
                detail={"error": CommonProxyErrors.not_premium_user.value},
            )
        if (
            user_api_key_dict.user_role
            and user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN
        ):
            return True
        elif team_obj is None or not _is_user_team_admin(
            user_api_key_dict=user_api_key_dict, team_obj=team_obj
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Team ID={} does not match the API key's team ID={}, OR you are not the admin for this team. Check `/user/info` to verify your team admin status.".format(
                        team_id, user_api_key_dict.team_id
                    )
                },
            )
        return True

    @staticmethod
    async def allow_team_model_action(
        model_params: Union[Deployment, updateDeployment],
        user_api_key_dict: UserAPIKeyAuth,
        prisma_client: PrismaClient,
        premium_user: bool,
    ) -> Literal[True]:
        if model_params.model_info is None or model_params.model_info.team_id is None:
            return True
        if model_params.model_info.team_id is not None and premium_user is not True:
            raise HTTPException(
                status_code=403,
                detail={"error": CommonProxyErrors.not_premium_user.value},
            )

        _existing_team_row = await prisma_client.db.litellm_teamtable.find_unique(
            where={"team_id": model_params.model_info.team_id}
        )

        if _existing_team_row is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Team id={} does not exist in db".format(
                        model_params.model_info.team_id
                    )
                },
            )
        existing_team_row = LiteLLM_TeamTable(**_existing_team_row.model_dump())

        ModelManagementAuthChecks.can_user_make_team_model_call(
            team_id=model_params.model_info.team_id,
            user_api_key_dict=user_api_key_dict,
            team_obj=existing_team_row,
            premium_user=premium_user,
        )
        return True

    @staticmethod
    async def can_user_make_model_call(
        model_params: Deployment,
        user_api_key_dict: UserAPIKeyAuth,
        prisma_client: PrismaClient,
        premium_user: bool,
    ) -> Literal[True]:
        ## Check team model auth
        if (
            model_params.model_info is not None
            and model_params.model_info.team_id is not None
        ):
            team_obj_row = await prisma_client.db.litellm_teamtable.find_unique(
                where={"team_id": model_params.model_info.team_id}
            )
            if team_obj_row is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Team id={} does not exist in db".format(
                            model_params.model_info.team_id
                        )
                    },
                )
            team_obj = LiteLLM_TeamTable(**team_obj_row.model_dump())

            return ModelManagementAuthChecks.can_user_make_team_model_call(
                team_id=model_params.model_info.team_id,
                user_api_key_dict=user_api_key_dict,
                team_obj=team_obj,
                premium_user=premium_user,
            )
        ## Check non-team model auth
        elif user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "User does not have permission to make this model call. Your role={}. You can only make model calls if you are a PROXY_ADMIN or if you are a team admin, by specifying a team_id in the model_info.".format(
                        user_api_key_dict.user_role
                    )
                },
            )
        else:
            return True

        return True


#### [BETA] - This is a beta endpoint, format might change based on user feedback. - https://github.com/BerriAI/litellm/issues/964
@router.post(
    "/model/delete",
    description="Allows deleting models in the model list in the config.yaml",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_model(
    model_info: ModelInfoDelete,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    from litellm.proxy.proxy_server import llm_router

    try:
        """
        [BETA] - This is a beta endpoint, format might change based on user feedback. - https://github.com/BerriAI/litellm/issues/964

        - Check if id in db
        - Delete
        """

        from litellm.proxy.proxy_server import (
            llm_router,
            premium_user,
            prisma_client,
            store_model_in_db,
        )

        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "No DB Connected. Here's how to do it - https://docs.litellm.ai/docs/proxy/virtual_keys"
                },
            )

        model_in_db = await prisma_client.db.litellm_proxymodeltable.find_unique(
            where={"model_id": model_info.id}
        )
        if model_in_db is None:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Model with id={model_info.id} not found in db"},
            )

        model_params = Deployment(**model_in_db.model_dump())
        await ModelManagementAuthChecks.can_user_make_model_call(
            model_params=model_params,
            user_api_key_dict=user_api_key_dict,
            prisma_client=prisma_client,
            premium_user=premium_user,
        )

        # delete team model alias
        if model_params.model_info.team_id is not None:
            removed_model_aliases = await delete_team_model_alias(
                public_model_name=model_params.model_name,
                prisma_client=prisma_client,
            )

            valid_team_model_aliases = [
                model
                for team_id, model in removed_model_aliases
                if team_id == model_params.model_info.team_id
            ]

            ## UPDATE TEAM TO NOT LIST MODEL ##
            existing_team_row = await prisma_client.db.litellm_teamtable.find_unique(
                where={"team_id": model_params.model_info.team_id}
            )
            if existing_team_row is not None:
                existing_team_row.models = [
                    model
                    for model in existing_team_row.models
                    if model not in valid_team_model_aliases
                ]

                await prisma_client.db.litellm_teamtable.update(
                    where={"team_id": model_params.model_info.team_id},
                    data={"models": existing_team_row.models},
                )

        # update DB
        if store_model_in_db is True:
            """
            - store model_list in db
            - store keys separately
            """
            # encrypt litellm params #
            result = await prisma_client.db.litellm_proxymodeltable.delete(
                where={"model_id": model_info.id}
            )

            if result is None:
                raise HTTPException(
                    status_code=400,
                    detail={"error": f"Model with id={model_info.id} not found in db"},
                )

            ## DELETE FROM ROUTER ##
            if llm_router is not None:
                llm_router.delete_deployment(id=model_info.id)

            ## CREATE AUDIT LOG ##
            asyncio.create_task(
                create_object_audit_log(
                    object_id=model_info.id,
                    action="deleted",
                    user_api_key_dict=user_api_key_dict,
                    table_name=LitellmTableNames.PROXY_MODEL_TABLE_NAME,
                    before_value=result.model_dump_json(exclude_none=True),
                    after_value=None,
                    litellm_changed_by=user_api_key_dict.user_id,
                    litellm_proxy_admin_name=LITELLM_PROXY_ADMIN_NAME,
                )
            )
            return {"message": f"Model: {result.model_id} deleted successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Set `'STORE_MODEL_IN_DB='True'` in your env to enable this feature."
                },
            )

    except Exception as e:
        verbose_proxy_logger.exception(
            f"Failed to delete model. Due to error - {str(e)}"
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


async def delete_team_model_alias(
    public_model_name: str,
    prisma_client: PrismaClient,
) -> List[Tuple[str, str]]:
    """
    Delete a team model alias

    Iterate through all team model aliases and delete the one that matches the model_id

    Returns:
    - List of team id + model alias pairs that were removed
    """
    team_model_aliases = await prisma_client.db.litellm_modeltable.find_many(
        include={"team": True}
    )
    tasks = []
    removed_model_aliases = []
    for team_model_alias in team_model_aliases:
        model_aliases = team_model_alias.model_aliases  # {"alias": "public model name"}
        id = team_model_alias.id

        if public_model_name in model_aliases.values():
            key = list(model_aliases.keys())[
                list(model_aliases.values()).index(public_model_name)
            ]
            if team_model_alias.team is not None:
                removed_model_aliases.append((team_model_alias.team.team_id, key))
            del model_aliases[key]
            tasks.append(
                prisma_client.db.litellm_modeltable.update(
                    where={"id": id},
                    data={"model_aliases": json.dumps(model_aliases)},
                )
            )
    await asyncio.gather(*tasks)

    return removed_model_aliases


#### [BETA] - This is a beta endpoint, format might change based on user feedback. - https://github.com/BerriAI/litellm/issues/964
@router.post(
    "/model/new",
    description="Allows adding new models to the model list in the config.yaml",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def add_new_model(
    model_params: Deployment,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    from litellm.proxy.proxy_server import (
        general_settings,
        premium_user,
        prisma_client,
        proxy_config,
        proxy_logging_obj,
        store_model_in_db,
    )

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "No DB Connected. Here's how to do it - https://docs.litellm.ai/docs/proxy/virtual_keys"
                },
            )

        ## Auth check
        await ModelManagementAuthChecks.can_user_make_model_call(
            model_params=model_params,
            user_api_key_dict=user_api_key_dict,
            prisma_client=prisma_client,
            premium_user=premium_user,
        )

        model_response: Optional[LiteLLM_ProxyModelTable] = None
        # update DB
        if store_model_in_db is True:
            """
            - store model_list in db
            - store keys separately
            """

            try:
                _original_litellm_model_name = model_params.model_name
                if model_params.model_info.team_id is None:
                    model_response = await _add_model_to_db(
                        model_params=model_params,
                        user_api_key_dict=user_api_key_dict,
                        prisma_client=prisma_client,
                    )
                else:
                    model_response = await _add_team_model_to_db(
                        model_params=model_params,
                        user_api_key_dict=user_api_key_dict,
                        prisma_client=prisma_client,
                    )
                await proxy_config.add_deployment(
                    prisma_client=prisma_client, proxy_logging_obj=proxy_logging_obj
                )
                # don't let failed slack alert block the /model/new response
                _alerting = general_settings.get("alerting", []) or []
                if "slack" in _alerting:
                    # send notification - new model added
                    await proxy_logging_obj.slack_alerting_instance.model_added_alert(
                        model_name=model_params.model_name,
                        litellm_model_name=_original_litellm_model_name,
                        passed_model_info=model_params.model_info,
                    )
            except Exception as e:
                verbose_proxy_logger.exception(f"Exception in add_new_model: {e}")

        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Set `'STORE_MODEL_IN_DB='True'` in your env to enable this feature."
                },
            )

        if model_response is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to add model to db. Check your server logs for more details."
                },
            )

        ## CREATE AUDIT LOG ##
        asyncio.create_task(
            create_object_audit_log(
                object_id=model_response.model_id,
                action="created",
                user_api_key_dict=user_api_key_dict,
                table_name=LitellmTableNames.PROXY_MODEL_TABLE_NAME,
                before_value=None,
                after_value=(
                    model_response.model_dump_json(exclude_none=True)
                    if isinstance(model_response, BaseModel)
                    else None
                ),
                litellm_changed_by=user_api_key_dict.user_id,
                litellm_proxy_admin_name=LITELLM_PROXY_ADMIN_NAME,
            )
        )

        return model_response

    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.add_new_model(): Exception occured - {}".format(
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


#### MODEL MANAGEMENT ####
@router.post(
    "/model/update",
    description="Edit existing model params",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_model(
    model_params: updateDeployment,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Old endpoint for model update. Makes a PUT request.

    Use `/model/{model_id}/update` to PATCH the stored model in db.
    """
    from litellm.proxy.proxy_server import (
        LITELLM_PROXY_ADMIN_NAME,
        llm_router,
        premium_user,
        prisma_client,
        store_model_in_db,
    )

    try:
        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "No DB Connected. Here's how to do it - https://docs.litellm.ai/docs/proxy/virtual_keys"
                },
            )

        _model_id = None
        _model_info = getattr(model_params, "model_info", None)
        if _model_info is None:
            raise Exception("model_info not provided")

        _model_id = _model_info.id
        if _model_id is None:
            raise Exception("model_info.id not provided")

        _existing_litellm_params = (
            await prisma_client.db.litellm_proxymodeltable.find_unique(
                where={"model_id": _model_id}
            )
        )

        if _existing_litellm_params is None:
            if (
                llm_router is not None
                and llm_router.get_deployment(model_id=_model_id) is not None
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Can't edit model. Model in config. Store model in db via `/model/new`. to edit."
                    },
                )
            else:
                raise Exception("model not found")
        deployment = Deployment(**_existing_litellm_params.model_dump())

        await ModelManagementAuthChecks.can_user_make_model_call(
            model_params=deployment,
            user_api_key_dict=user_api_key_dict,
            prisma_client=prisma_client,
            premium_user=premium_user,
        )

        # update DB
        if store_model_in_db is True:
            _existing_litellm_params_dict = dict(
                _existing_litellm_params.litellm_params
            )

            if model_params.litellm_params is None:
                raise Exception("litellm_params not provided")

            _new_litellm_params_dict = model_params.litellm_params.dict(
                exclude_none=True
            )

            ### ENCRYPT PARAMS ###
            for k, v in _new_litellm_params_dict.items():
                encrypted_value = encrypt_value_helper(value=v)
                model_params.litellm_params[k] = encrypted_value

            ### MERGE WITH EXISTING DATA ###
            merged_dictionary = {}
            _mp = model_params.litellm_params.dict()

            for key, value in _mp.items():
                if value is not None:
                    merged_dictionary[key] = value
                elif (
                    key in _existing_litellm_params_dict
                    and _existing_litellm_params_dict[key] is not None
                ):
                    merged_dictionary[key] = _existing_litellm_params_dict[key]
                else:
                    pass

            _data: dict = {
                "litellm_params": json.dumps(merged_dictionary),  # type: ignore
                "updated_by": user_api_key_dict.user_id or LITELLM_PROXY_ADMIN_NAME,
            }
            model_response = await prisma_client.db.litellm_proxymodeltable.update(
                where={"model_id": _model_id},
                data=_data,  # type: ignore
            )

            ## CREATE AUDIT LOG ##
            asyncio.create_task(
                create_object_audit_log(
                    object_id=_model_id,
                    action="updated",
                    user_api_key_dict=user_api_key_dict,
                    table_name=LitellmTableNames.PROXY_MODEL_TABLE_NAME,
                    before_value=(
                        _existing_litellm_params.model_dump_json(exclude_none=True)
                        if isinstance(_existing_litellm_params, BaseModel)
                        else None
                    ),
                    after_value=(
                        model_response.model_dump_json(exclude_none=True)
                        if isinstance(model_response, BaseModel)
                        else None
                    ),
                    litellm_changed_by=user_api_key_dict.user_id,
                    litellm_proxy_admin_name=LITELLM_PROXY_ADMIN_NAME,
                )
            )

            return model_response
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.update_model(): Exception occured - {}".format(
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


def _deduplicate_litellm_router_models(models: List[Dict]) -> List[Dict]:
    """
    Deduplicate models based on their model_info.id field.
    Returns a list of unique models keeping only the first occurrence of each model ID.

    Args:
        models: List of model dictionaries containing model_info

    Returns:
        List of deduplicated model dictionaries
    """
    seen_ids = set()
    unique_models = []
    for model in models:
        model_id = model.get("model_info", {}).get("id", None)
        if model_id is not None and model_id not in seen_ids:
            unique_models.append(model)
            seen_ids.add(model_id)
    return unique_models

async def clear_cache():
    """
    Clear router caches and reload models.
    """
    from litellm.proxy.proxy_server import (
        proxy_config,
        llm_router,
        prisma_client,
        proxy_logging_obj,
        verbose_proxy_logger,
    )
    try:
        llm_router.model_list.clear()
        
        await proxy_config.add_deployment(
            prisma_client=prisma_client, 
            proxy_logging_obj=proxy_logging_obj
        )
    except Exception as e:
        verbose_proxy_logger.exception(
            f"Failed to clear cache and reload models. Due to error - {str(e)}"
        )

# === NexusCore/tree_sitter_languages\tree-sitter-python\examples\python2-grammar.py ===
# Python test set -- part 1, grammar.
# This just tests whether the parser accepts them all.

# NOTE: When you run this test as a script from the command line, you
# get warnings about certain hex/oct constants.  Since those are
# issued by the parser, you can't suppress them by adding a
# filterwarnings() call to this module.  Therefore, to shut up the
# regression test, the filterwarnings() call has been added to
# regrtest.py.

from test.test_support import run_unittest, check_syntax_error
import unittest
import sys
# testing import *
from sys import *

class TokenTests(unittest.TestCase):

    def testBackslash(self):
        # Backslash means line continuation:
        x = 1 \
        + 1
        self.assertEquals(x, 2, 'backslash for line continuation')

        # Backslash does not means continuation in comments :\
        x = 0
        self.assertEquals(x, 0, 'backslash ending comment')

    def testPlainIntegers(self):
        self.assertEquals(0xff, 255)
        self.assertEquals(0377, 255)
        self.assertEquals(2147483647, 017777777777)
        # "0x" is not a valid literal
        self.assertRaises(SyntaxError, eval, "0x")
        from sys import maxint
        if maxint == 2147483647:
            self.assertEquals(-2147483647-1, -020000000000)
            # XXX -2147483648
            self.assert_(037777777777 > 0)
            self.assert_(0xffffffff > 0)
            for s in '2147483648', '040000000000', '0x100000000':
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        elif maxint == 9223372036854775807:
            self.assertEquals(-9223372036854775807-1, -01000000000000000000000)
            self.assert_(01777777777777777777777 > 0)
            self.assert_(0xffffffffffffffff > 0)
            for s in '9223372036854775808', '02000000000000000000000', \
                     '0x10000000000000000':
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        else:
            self.fail('Weird maxint value %r' % maxint)

    def testLongIntegers(self):
        x = 0L
        x = 0l
        x = 0xffffffffffffffffL
        x = 0xffffffffffffffffl
        x = 077777777777777777L
        x = 077777777777777777l
        x = 123456789012345678901234567890L
        x = 123456789012345678901234567890l

    def testFloats(self):
        x = 3.14
        x = 314.
        x = 0.314
        # XXX x = 000.314
        x = .314
        x = 3e14
        x = 3E14
        x = 3e-14
        x = 3e+14
        x = 3.e14
        x = .3e14
        x = 3.1e4

class GrammarTests(unittest.TestCase):

    # single_input: NEWLINE | simple_stmt | compound_stmt NEWLINE
    # XXX can't test in a script -- this rule is only used when interactive

    # file_input: (NEWLINE | stmt)* ENDMARKER
    # Being tested as this very moment this very module

    # expr_input: testlist NEWLINE
    # XXX Hard to test -- used only in calls to input()

    def testEvalInput(self):
        # testlist ENDMARKER
        x = eval('1, 0 or 1')

    def testFuncdef(self):
        ### 'def' NAME parameters ':' suite
        ### parameters: '(' [varargslist] ')'
        ### varargslist: (fpdef ['=' test] ',')* ('*' NAME [',' ('**'|'*' '*') NAME]
        ###            | ('**'|'*' '*') NAME)
        ###            | fpdef ['=' test] (',' fpdef ['=' test])* [',']
        ### fpdef: NAME | '(' fplist ')'
        ### fplist: fpdef (',' fpdef)* [',']
        ### arglist: (argument ',')* (argument | *' test [',' '**' test] | '**' test)
        ### argument: [test '='] test   # Really [keyword '='] test
        def f1(): pass
        f1()
        f1(*())
        f1(*(), **{})
        def f2(one_argument): pass
        def f3(two, arguments): pass
        def f4(two, (compound, (argument, list))): pass
        def f5((compound, first), two): pass
        self.assertEquals(f2.func_code.co_varnames, ('one_argument',))
        self.assertEquals(f3.func_code.co_varnames, ('two', 'arguments'))
        if sys.platform.startswith('java'):
            self.assertEquals(f4.func_code.co_varnames,
                   ('two', '(compound, (argument, list))', 'compound', 'argument',
                                'list',))
            self.assertEquals(f5.func_code.co_varnames,
                   ('(compound, first)', 'two', 'compound', 'first'))
        else:
            self.assertEquals(f4.func_code.co_varnames,
                  ('two', '.1', 'compound', 'argument',  'list'))
            self.assertEquals(f5.func_code.co_varnames,
                  ('.0', 'two', 'compound', 'first'))
        def a1(one_arg,): pass
        def a2(two, args,): pass
        def v0(*rest): pass
        def v1(a, *rest): pass
        def v2(a, b, *rest): pass
        def v3(a, (b, c), *rest): return a, b, c, rest

        f1()
        f2(1)
        f2(1,)
        f3(1, 2)
        f3(1, 2,)
        f4(1, (2, (3, 4)))
        v0()
        v0(1)
        v0(1,)
        v0(1,2)
        v0(1,2,3,4,5,6,7,8,9,0)
        v1(1)
        v1(1,)
        v1(1,2)
        v1(1,2,3)
        v1(1,2,3,4,5,6,7,8,9,0)
        v2(1,2)
        v2(1,2,3)
        v2(1,2,3,4)
        v2(1,2,3,4,5,6,7,8,9,0)
        v3(1,(2,3))
        v3(1,(2,3),4)
        v3(1,(2,3),4,5,6,7,8,9,0)

        # ceval unpacks the formal arguments into the first argcount names;
        # thus, the names nested inside tuples must appear after these names.
        if sys.platform.startswith('java'):
            self.assertEquals(v3.func_code.co_varnames, ('a', '(b, c)', 'rest', 'b', 'c'))
        else:
            self.assertEquals(v3.func_code.co_varnames, ('a', '.1', 'rest', 'b', 'c'))
        self.assertEquals(v3(1, (2, 3), 4), (1, 2, 3, (4,)))
        def d01(a=1): pass
        d01()
        d01(1)
        d01(*(1,))
        d01(**{'a':2})
        def d11(a, b=1): pass
        d11(1)
        d11(1, 2)
        d11(1, **{'b':2})
        def d21(a, b, c=1): pass
        d21(1, 2)
        d21(1, 2, 3)
        d21(*(1, 2, 3))
        d21(1, *(2, 3))
        d21(1, 2, *(3,))
        d21(1, 2, **{'c':3})
        def d02(a=1, b=2): pass
        d02()
        d02(1)
        d02(1, 2)
        d02(*(1, 2))
        d02(1, *(2,))
        d02(1, **{'b':2})
        d02(**{'a': 1, 'b': 2})
        def d12(a, b=1, c=2): pass
        d12(1)
        d12(1, 2)
        d12(1, 2, 3)
        def d22(a, b, c=1, d=2): pass
        d22(1, 2)
        d22(1, 2, 3)
        d22(1, 2, 3, 4)
        def d01v(a=1, *rest): pass
        d01v()
        d01v(1)
        d01v(1, 2)
        d01v(*(1, 2, 3, 4))
        d01v(*(1,))
        d01v(**{'a':2})
        def d11v(a, b=1, *rest): pass
        d11v(1)
        d11v(1, 2)
        d11v(1, 2, 3)
        def d21v(a, b, c=1, *rest): pass
        d21v(1, 2)
        d21v(1, 2, 3)
        d21v(1, 2, 3, 4)
        d21v(*(1, 2, 3, 4))
        d21v(1, 2, **{'c': 3})
        def d02v(a=1, b=2, *rest): pass
        d02v()
        d02v(1)
        d02v(1, 2)
        d02v(1, 2, 3)
        d02v(1, *(2, 3, 4))
        d02v(**{'a': 1, 'b': 2})
        def d12v(a, b=1, c=2, *rest): pass
        d12v(1)
        d12v(1, 2)
        d12v(1, 2, 3)
        d12v(1, 2, 3, 4)
        d12v(*(1, 2, 3, 4))
        d12v(1, 2, *(3, 4, 5))
        d12v(1, *(2,), **{'c': 3})
        def d22v(a, b, c=1, d=2, *rest): pass
        d22v(1, 2)
        d22v(1, 2, 3)
        d22v(1, 2, 3, 4)
        d22v(1, 2, 3, 4, 5)
        d22v(*(1, 2, 3, 4))
        d22v(1, 2, *(3, 4, 5))
        d22v(1, *(2, 3), **{'d': 4})
        def d31v((x)): pass
        d31v(1)
        def d32v((x,)): pass
        d32v((1,))

        # keyword arguments after *arglist
        def f(*args, **kwargs):
            return args, kwargs
        self.assertEquals(f(1, x=2, *[3, 4], y=5), ((1, 3, 4),
                                                    {'x':2, 'y':5}))
        self.assertRaises(SyntaxError, eval, "f(1, *(2,3), 4)")
        self.assertRaises(SyntaxError, eval, "f(1, x=2, *(3,4), x=5)")

        # Check ast errors in *args and *kwargs
        check_syntax_error(self, "f(*g(1=2))")
        check_syntax_error(self, "f(**g(1=2))")

    def testLambdef(self):
        ### lambdef: 'lambda' [varargslist] ':' test
        l1 = lambda : 0
        self.assertEquals(l1(), 0)
        l2 = lambda : a[d] # XXX just testing the expression
        l3 = lambda : [2 < x for x in [-1, 3, 0L]]
        self.assertEquals(l3(), [0, 1, 0])
        l4 = lambda x = lambda y = lambda z=1 : z : y() : x()
        self.assertEquals(l4(), 1)
        l5 = lambda x, y, z=2: x + y + z
        self.assertEquals(l5(1, 2), 5)
        self.assertEquals(l5(1, 2, 3), 6)
        check_syntax_error(self, "lambda x: x = 2")
        check_syntax_error(self, "lambda (None,): None")

    ### stmt: simple_stmt | compound_stmt
    # Tested below

    def testSimpleStmt(self):
        ### simple_stmt: small_stmt (';' small_stmt)* [';']
        x = 1; pass; del x
        def foo():
            # verify statements that end with semi-colons
            x = 1; pass; del x;
        foo()

    ### small_stmt: expr_stmt | print_stmt  | pass_stmt | del_stmt | flow_stmt | import_stmt | global_stmt | access_stmt | exec_stmt
    # Tested below

    def testExprStmt(self):
        # (exprlist '=')* exprlist
        1
        1, 2, 3
        x = 1
        x = 1, 2, 3
        x = y = z = 1, 2, 3
        x, y, z = 1, 2, 3
        abc = a, b, c = x, y, z = xyz = 1, 2, (3, 4)

        check_syntax_error(self, "x + 1 = 1")
        check_syntax_error(self, "a + 1 = b + 2")

    def testPrintStmt(self):
        # 'print' (test ',')* [test]
        import StringIO

        # Can't test printing to real stdout without comparing output
        # which is not available in unittest.
        save_stdout = sys.stdout
        sys.stdout = StringIO.StringIO()

        print 1, 2, 3
        print 1, 2, 3,
        print
        print 0 or 1, 0 or 1,
        print 0 or 1

        # 'print' '>>' test ','
        print >> sys.stdout, 1, 2, 3
        print >> sys.stdout, 1, 2, 3,
        print >> sys.stdout
        print >> sys.stdout, 0 or 1, 0 or 1,
        print >> sys.stdout, 0 or 1

        # test printing to an instance
        class Gulp:
            def write(self, msg): pass

        gulp = Gulp()
        print >> gulp, 1, 2, 3
        print >> gulp, 1, 2, 3,
        print >> gulp
        print >> gulp, 0 or 1, 0 or 1,
        print >> gulp, 0 or 1

        # test print >> None
        def driver():
            oldstdout = sys.stdout
            sys.stdout = Gulp()
            try:
                tellme(Gulp())
                tellme()
            finally:
                sys.stdout = oldstdout

        # we should see this once
        def tellme(file=sys.stdout):
            print >> file, 'hello world'

        driver()

        # we should not see this at all
        def tellme(file=None):
            print >> file, 'goodbye universe'

        driver()

        self.assertEqual(sys.stdout.getvalue(), '''\
1 2 3
1 2 3
1 1 1
1 2 3
1 2 3
1 1 1
hello world
''')
        sys.stdout = save_stdout

        # syntax errors
        check_syntax_error(self, 'print ,')
        check_syntax_error(self, 'print >> x,')

    def testDelStmt(self):
        # 'del' exprlist
        abc = [1,2,3]
        x, y, z = abc
        xyz = x, y, z

        del abc
        del x, y, (z, xyz)

    def testPassStmt(self):
        # 'pass'
        pass

    # flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt
    # Tested below

    def testBreakStmt(self):
        # 'break'
        while 1: break

    def testContinueStmt(self):
        # 'continue'
        i = 1
        while i: i = 0; continue

        msg = ""
        while not msg:
            msg = "ok"
            try:
                continue
                msg = "continue failed to continue inside try"
            except:
                msg = "continue inside try called except block"
        if msg != "ok":
            self.fail(msg)

        msg = ""
        while not msg:
            msg = "finally block not called"
            try:
                continue
            finally:
                msg = "ok"
        if msg != "ok":
            self.fail(msg)

    def test_break_continue_loop(self):
        # This test warrants an explanation. It is a test specifically for SF bugs
        # #463359 and #462937. The bug is that a 'break' statement executed or
        # exception raised inside a try/except inside a loop, *after* a continue
        # statement has been executed in that loop, will cause the wrong number of
        # arguments to be popped off the stack and the instruction pointer reset to
        # a very small number (usually 0.) Because of this, the following test
        # *must* written as a function, and the tracking vars *must* be function
        # arguments with default values. Otherwise, the test will loop and loop.

        def test_inner(extra_burning_oil = 1, count=0):
            big_hippo = 2
            while big_hippo:
                count += 1
                try:
                    if extra_burning_oil and big_hippo == 1:
                        extra_burning_oil -= 1
                        break
                    big_hippo -= 1
                    continue
                except:
                    raise
            if count > 2 or big_hippo <> 1:
                self.fail("continue then break in try/except in loop broken!")
        test_inner()

    def testReturn(self):
        # 'return' [testlist]
        def g1(): return
        def g2(): return 1
        g1()
        x = g2()
        check_syntax_error(self, "class foo:return 1")

    def testYield(self):
        check_syntax_error(self, "class foo:yield 1")

    def testRaise(self):
        # 'raise' test [',' test]
        try: raise RuntimeError, 'just testing'
        except RuntimeError: pass
        try: raise KeyboardInterrupt
        except KeyboardInterrupt: pass

    def testImport(self):
        # 'import' dotted_as_names
        import sys
        import time, sys
        # 'from' dotted_name 'import' ('*' | '(' import_as_names ')' | import_as_names)
        from time import time
        from time import (time)
        # not testable inside a function, but already done at top of the module
        # from sys import *
        from sys import path, argv
        from sys import (path, argv)
        from sys import (path, argv,)

    def testGlobal(self):
        # 'global' NAME (',' NAME)*
        global a
        global a, b
        global one, two, three, four, five, six, seven, eight, nine, ten

    def testExec(self):
        # 'exec' expr ['in' expr [',' expr]]
        z = None
        del z
        exec 'z=1+1\n'
        if z != 2: self.fail('exec \'z=1+1\'\\n')
        del z
        exec 'z=1+1'
        if z != 2: self.fail('exec \'z=1+1\'')
        z = None
        del z
        import types
        if hasattr(types, "UnicodeType"):
            exec r"""if 1:
            exec u'z=1+1\n'
            if z != 2: self.fail('exec u\'z=1+1\'\\n')
            del z
            exec u'z=1+1'
            if z != 2: self.fail('exec u\'z=1+1\'')"""
        g = {}
        exec 'z = 1' in g
        if g.has_key('__builtins__'): del g['__builtins__']
        if g != {'z': 1}: self.fail('exec \'z = 1\' in g')
        g = {}
        l = {}

        import warnings
        warnings.filterwarnings("ignore", "global statement", module="<string>")
        exec 'global a; a = 1; b = 2' in g, l
        if g.has_key('__builtins__'): del g['__builtins__']
        if l.has_key('__builtins__'): del l['__builtins__']
        if (g, l) != ({'a':1}, {'b':2}):
            self.fail('exec ... in g (%s), l (%s)' %(g,l))

    def testAssert(self):
        # assert_stmt: 'assert' test [',' test]
        assert 1
        assert 1, 1
        assert lambda x:x
        assert 1, lambda x:x+1
        try:
            assert 0, "msg"
        except AssertionError, e:
            self.assertEquals(e.args[0], "msg")
        else:
            if __debug__:
                self.fail("AssertionError not raised by assert 0")

    ### compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | funcdef | classdef
    # Tested below

    def testIf(self):
        # 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        if 1: pass
        if 1: pass
        else: pass
        if 0: pass
        elif 0: pass
        if 0: pass
        elif 0: pass
        elif 0: pass
        elif 0: pass
        else: pass

    def testWhile(self):
        # 'while' test ':' suite ['else' ':' suite]
        while 0: pass
        while 0: pass
        else: pass

        # Issue1920: "while 0" is optimized away,
        # ensure that the "else" clause is still present.
        x = 0
        while 0:
            x = 1
        else:
            x = 2
        self.assertEquals(x, 2)

    def testFor(self):
        # 'for' exprlist 'in' exprlist ':' suite ['else' ':' suite]
        for i in 1, 2, 3: pass
        for i, j, k in (): pass
        else: pass
        class Squares:
            def __init__(self, max):
                self.max = max
                self.sofar = []
            def __len__(self): return len(self.sofar)
            def __getitem__(self, i):
                if not 0 <= i < self.max: raise IndexError
                n = len(self.sofar)
                while n <= i:
                    self.sofar.append(n*n)
                    n = n+1
                return self.sofar[i]
        n = 0
        for x in Squares(10): n = n+x
        if n != 285:
            self.fail('for over growing sequence')

        result = []
        for x, in [(1,), (2,), (3,)]:
            result.append(x)
        self.assertEqual(result, [1, 2, 3])

    def testTry(self):
        ### try_stmt: 'try' ':' suite (except_clause ':' suite)+ ['else' ':' suite]
        ###         | 'try' ':' suite 'finally' ':' suite
        ### except_clause: 'except' [expr [('as' | ',') expr]]
        try:
            1/0
        except ZeroDivisionError:
            pass
        else:
            pass
        try: 1/0
        except EOFError: pass
        except TypeError as msg: pass
        except RuntimeError, msg: pass
        except: pass
        else: pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError): pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError), msg: pass
        try: pass
        finally: pass

    def testSuite(self):
        # simple_stmt | NEWLINE INDENT NEWLINE* (stmt NEWLINE*)+ DEDENT
        if 1: pass
        if 1:
            pass
        if 1:
            #
            #
            #
            pass
            pass
            #
            pass
            #

    def testTest(self):
        ### and_test ('or' and_test)*
        ### and_test: not_test ('and' not_test)*
        ### not_test: 'not' not_test | comparison
        if not 1: pass
        if 1 and 1: pass
        if 1 or 1: pass
        if not not not 1: pass
        if not 1 and 1 and 1: pass
        if 1 and 1 or 1 and 1 and 1 or not 1 and 1: pass

    def testComparison(self):
        ### comparison: expr (comp_op expr)*
        ### comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        if 1: pass
        x = (1 == 1)
        if 1 == 1: pass
        if 1 != 1: pass
        if 1 <> 1: pass
        if 1 < 1: pass
        if 1 > 1: pass
        if 1 <= 1: pass
        if 1 >= 1: pass
        if 1 is 1: pass
        if 1 is not 1: pass
        if 1 in (): pass
        if 1 not in (): pass
        if 1 < 1 > 1 == 1 >= 1 <= 1 <> 1 != 1 in 1 not in 1 is 1 is not 1: pass

    def testBinaryMaskOps(self):
        x = 1 & 1
        x = 1 ^ 1
        x = 1 | 1

    def testShiftOps(self):
        x = 1 << 1
        x = 1 >> 1
        x = 1 << 1 >> 1

    def testAdditiveOps(self):
        x = 1
        x = 1 + 1
        x = 1 - 1 - 1
        x = 1 - 1 + 1 - 1 + 1

    def testMultiplicativeOps(self):
        x = 1 * 1
        x = 1 / 1
        x = 1 % 1
        x = 1 / 1 * 1 % 1

    def testUnaryOps(self):
        x = +1
        x = -1
        x = ~1
        x = ~1 ^ 1 & 1 | 1 & 1 ^ -1
        x = -1*1/1 + 1*1 - ---1*1

    def testSelectors(self):
        ### trailer: '(' [testlist] ')' | '[' subscript ']' | '.' NAME
        ### subscript: expr | [expr] ':' [expr]

        import sys, time
        c = sys.path[0]
        x = time.time()
        x = sys.modules['time'].time()
        a = '01234'
        c = a[0]
        c = a[-1]
        s = a[0:5]
        s = a[:5]
        s = a[0:]
        s = a[:]
        s = a[-5:]
        s = a[:-1]
        s = a[-4:-3]
        # A rough test of SF bug 1333982.  http://python.org/sf/1333982
        # The testing here is fairly incomplete.
        # Test cases should include: commas with 1 and 2 colons
        d = {}
        d[1] = 1
        d[1,] = 2
        d[1,2] = 3
        d[1,2,3] = 4
        L = list(d)
        L.sort()
        self.assertEquals(str(L), '[1, (1,), (1, 2), (1, 2, 3)]')

    def testAtoms(self):
        ### atom: '(' [testlist] ')' | '[' [testlist] ']' | '{' [dictmaker] '}' | '`' testlist '`' | NAME | NUMBER | STRING
        ### dictmaker: test ':' test (',' test ':' test)* [',']

        x = (1)
        x = (1 or 2 or 3)
        x = (1 or 2 or 3, 2, 3)

        x = []
        x = [1]
        x = [1 or 2 or 3]
        x = [1 or 2 or 3, 2, 3]
        x = []

        x = {}
        x = {'one': 1}
        x = {'one': 1,}
        x = {'one' or 'two': 1 or 2}
        x = {'one': 1, 'two': 2}
        x = {'one': 1, 'two': 2,}
        x = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}

        x = `x`
        x = `1 or 2 or 3`
        self.assertEqual(`1,2`, '(1, 2)')

        x = x
        x = 'x'
        x = 123

    ### exprlist: expr (',' expr)* [',']
    ### testlist: test (',' test)* [',']
    # These have been exercised enough above

    def testClassdef(self):
        # 'class' NAME ['(' [testlist] ')'] ':' suite
        class B: pass
        class B2(): pass
        class C1(B): pass
        class C2(B): pass
        class D(C1, C2, B): pass
        class C:
            def meth1(self): pass
            def meth2(self, arg): pass
            def meth3(self, a1, a2): pass
        # decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        # decorators: decorator+
        # decorated: decorators (classdef | funcdef)
        def class_decorator(x):
            x.decorated = True
            return x
        @class_decorator
        class G:
            pass
        self.assertEqual(G.decorated, True)

    def testListcomps(self):
        # list comprehension tests
        nums = [1, 2, 3, 4, 5]
        strs = ["Apple", "Banana", "Coconut"]
        spcs = ["  Apple", " Banana ", "Coco  nut  "]

        self.assertEqual([s.strip() for s in spcs], ['Apple', 'Banana', 'Coco  nut'])
        self.assertEqual([3 * x for x in nums], [3, 6, 9, 12, 15])
        self.assertEqual([x for x in nums if x > 2], [3, 4, 5])
        self.assertEqual([(i, s) for i in nums for s in strs],
                         [(1, 'Apple'), (1, 'Banana'), (1, 'Coconut'),
                          (2, 'Apple'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Apple'), (3, 'Banana'), (3, 'Coconut'),
                          (4, 'Apple'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Apple'), (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(i, s) for i in nums for s in [f for f in strs if "n" in f]],
                         [(1, 'Banana'), (1, 'Coconut'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Banana'), (3, 'Coconut'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(lambda a:[a**i for i in range(a+1)])(j) for j in range(5)],
                         [[1], [1, 1], [1, 2, 4], [1, 3, 9, 27], [1, 4, 16, 64, 256]])

        def test_in_func(l):
            return [None < x < 3 for x in l if x > 2]

        self.assertEqual(test_in_func(nums), [False, False, False])

        def test_nested_front():
            self.assertEqual([[y for y in [x, x + 1]] for x in [1,3,5]],
                             [[1, 2], [3, 4], [5, 6]])

        test_nested_front()

        check_syntax_error(self, "[i, s for i in nums for s in strs]")
        check_syntax_error(self, "[x if y]")

        suppliers = [
          (1, "Boeing"),
          (2, "Ford"),
          (3, "Macdonalds")
        ]

        parts = [
          (10, "Airliner"),
          (20, "Engine"),
          (30, "Cheeseburger")
        ]

        suppart = [
          (1, 10), (1, 20), (2, 20), (3, 30)
        ]

        x = [
          (sname, pname)
            for (sno, sname) in suppliers
              for (pno, pname) in parts
                for (sp_sno, sp_pno) in suppart
                  if sno == sp_sno and pno == sp_pno
        ]

        self.assertEqual(x, [('Boeing', 'Airliner'), ('Boeing', 'Engine'), ('Ford', 'Engine'),
                             ('Macdonalds', 'Cheeseburger')])

    def testGenexps(self):
        # generator expression tests
        g = ([x for x in range(10)] for x in range(1))
        self.assertEqual(g.next(), [x for x in range(10)])
        try:
            g.next()
            self.fail('should produce StopIteration exception')
        except StopIteration:
            pass

        a = 1
        try:
            g = (a for d in a)
            g.next()
            self.fail('should produce TypeError')
        except TypeError:
            pass

        self.assertEqual(list((x, y) for x in 'abcd' for y in 'abcd'), [(x, y) for x in 'abcd' for y in 'abcd'])
        self.assertEqual(list((x, y) for x in 'ab' for y in 'xy'), [(x, y) for x in 'ab' for y in 'xy'])

        a = [x for x in range(10)]
        b = (x for x in (y for y in a))
        self.assertEqual(sum(b), sum([x for x in range(10)]))

        self.assertEqual(sum(x**2 for x in range(10)), sum([x**2 for x in range(10)]))
        self.assertEqual(sum(x*x for x in range(10) if x%2), sum([x*x for x in range(10) if x%2]))
        self.assertEqual(sum(x for x in (y for y in range(10))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10)))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in [y for y in (z for z in range(10))]), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True)) if True), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True) if False) if True), 0)
        check_syntax_error(self, "foo(x for x in range(10), 100)")
        check_syntax_error(self, "foo(100, x for x in range(10))")

    def testComprehensionSpecials(self):
        # test for outmost iterable precomputation
        x = 10; g = (i for i in range(x)); x = 5
        self.assertEqual(len(list(g)), 10)

        # This should hold, since we're only precomputing outmost iterable.
        x = 10; t = False; g = ((i,j) for i in range(x) if t for j in range(x))
        x = 5; t = True;
        self.assertEqual([(i,j) for i in range(10) for j in range(5)], list(g))

        # Grammar allows multiple adjacent 'if's in listcomps and genexps,
        # even though it's silly. Make sure it works (ifelse broke this.)
        self.assertEqual([ x for x in range(10) if x % 2 if x % 3 ], [1, 5, 7])
        self.assertEqual(list(x for x in range(10) if x % 2 if x % 3), [1, 5, 7])

        # verify unpacking single element tuples in listcomp/genexp.
        self.assertEqual([x for x, in [(4,), (5,), (6,)]], [4, 5, 6])
        self.assertEqual(list(x for x, in [(7,), (8,), (9,)]), [7, 8, 9])

    def test_with_statement(self):
        class manager(object):
            def __enter__(self):
                return (1, 2)
            def __exit__(self, *args):
                pass

        with manager():
            pass
        with manager() as x:
            pass
        with manager() as (x, y):
            pass
        with manager(), manager():
            pass
        with manager() as x, manager() as y:
            pass
        with manager() as x, manager():
            pass

    def testIfElseExpr(self):
        # Test ifelse expressions in various cases
        def _checkeval(msg, ret):
            "helper to check that evaluation of expressions is done correctly"
            print x
            return ret

        self.assertEqual([ x() for x in lambda: True, lambda: False if x() ], [True])
        self.assertEqual([ x() for x in (lambda: True, lambda: False) if x() ], [True])
        self.assertEqual([ x(False) for x in (lambda x: False if x else True, lambda x: True if x else False) if x(False) ], [True])
        self.assertEqual((5 if 1 else _checkeval("check 1", 0)), 5)
        self.assertEqual((_checkeval("check 2", 0) if 0 else 5), 5)
        self.assertEqual((5 and 6 if 0 else 1), 1)
        self.assertEqual(((5 and 6) if 0 else 1), 1)
        self.assertEqual((5 and (6 if 1 else 1)), 6)
        self.assertEqual((0 or _checkeval("check 3", 2) if 0 else 3), 3)
        self.assertEqual((1 or _checkeval("check 4", 2) if 1 else _checkeval("check 5", 3)), 1)
        self.assertEqual((0 or 5 if 1 else _checkeval("check 6", 3)), 5)
        self.assertEqual((not 5 if 1 else 1), False)
        self.assertEqual((not 5 if 0 else 1), 1)
        self.assertEqual((6 + 1 if 1 else 2), 7)
        self.assertEqual((6 - 1 if 1 else 2), 5)
        self.assertEqual((6 * 2 if 1 else 4), 12)
        self.assertEqual((6 / 2 if 1 else 3), 3)
        self.assertEqual((6 < 4 if 0 else 2), 2)

    def testStringLiterals(self):
        x = ''; y = ""; self.assert_(len(x) == 0 and x == y)
        x = '\''; y = "'"; self.assert_(len(x) == 1 and x == y and ord(x) == 39)
        x = '"'; y = "\""; self.assert_(len(x) == 1 and x == y and ord(x) == 34)
        x = "doesn't \"shrink\" does it"
        y = 'doesn\'t "shrink" does it'
        self.assert_(len(x) == 24 and x == y)
        x = "does \"shrink\" doesn't it"
        y = 'does "shrink" doesn\'t it'
        self.assert_(len(x) == 24 and x == y)
        x = """
The "quick"
brown fox
jumps over
the 'lazy' dog.
"""
        y = '\nThe "quick"\nbrown fox\njumps over\nthe \'lazy\' dog.\n'
        self.assertEquals(x, y)
        y = '''
The "quick"
brown fox
jumps over
the 'lazy' dog.
'''
        self.assertEquals(x, y)
        y = "\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the 'lazy' dog.\n\
"
        self.assertEquals(x, y)
        y = '\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the \'lazy\' dog.\n\
'
        self.assertEquals(x, y)



def test_main():
    run_unittest(TokenTests, GrammarTests)

if __name__ == '__main__':
    test_main()


# === NexusCore/openenv\Lib\site-packages\zmq\constants.py ===
"""zmq constants as enums"""

from __future__ import annotations

import errno
import sys
from enum import Enum, IntEnum, IntFlag

_HAUSNUMERO = 156384712


class Errno(IntEnum):
    """libzmq error codes

    .. versionadded:: 23
    """

    EAGAIN = errno.EAGAIN
    EFAULT = errno.EFAULT
    EINVAL = errno.EINVAL

    if sys.platform.startswith("win"):
        # Windows: libzmq uses errno.h
        # while Python errno prefers WSA* variants
        # many of these were introduced to errno.h in vs2010
        # ref: https://github.com/python/cpython/blob/3.9/Modules/errnomodule.c#L10-L37
        # source: https://docs.microsoft.com/en-us/cpp/c-runtime-library/errno-constants
        ENOTSUP = 129
        EPROTONOSUPPORT = 135
        ENOBUFS = 119
        ENETDOWN = 116
        EADDRINUSE = 100
        EADDRNOTAVAIL = 101
        ECONNREFUSED = 107
        EINPROGRESS = 112
        ENOTSOCK = 128
        EMSGSIZE = 115
        EAFNOSUPPORT = 102
        ENETUNREACH = 118
        ECONNABORTED = 106
        ECONNRESET = 108
        ENOTCONN = 126
        ETIMEDOUT = 138
        EHOSTUNREACH = 110
        ENETRESET = 117

    else:
        ENOTSUP = getattr(errno, "ENOTSUP", _HAUSNUMERO + 1)
        EPROTONOSUPPORT = getattr(errno, "EPROTONOSUPPORT", _HAUSNUMERO + 2)
        ENOBUFS = getattr(errno, "ENOBUFS", _HAUSNUMERO + 3)
        ENETDOWN = getattr(errno, "ENETDOWN", _HAUSNUMERO + 4)
        EADDRINUSE = getattr(errno, "EADDRINUSE", _HAUSNUMERO + 5)
        EADDRNOTAVAIL = getattr(errno, "EADDRNOTAVAIL", _HAUSNUMERO + 6)
        ECONNREFUSED = getattr(errno, "ECONNREFUSED", _HAUSNUMERO + 7)
        EINPROGRESS = getattr(errno, "EINPROGRESS", _HAUSNUMERO + 8)
        ENOTSOCK = getattr(errno, "ENOTSOCK", _HAUSNUMERO + 9)
        EMSGSIZE = getattr(errno, "EMSGSIZE", _HAUSNUMERO + 10)
        EAFNOSUPPORT = getattr(errno, "EAFNOSUPPORT", _HAUSNUMERO + 11)
        ENETUNREACH = getattr(errno, "ENETUNREACH", _HAUSNUMERO + 12)
        ECONNABORTED = getattr(errno, "ECONNABORTED", _HAUSNUMERO + 13)
        ECONNRESET = getattr(errno, "ECONNRESET", _HAUSNUMERO + 14)
        ENOTCONN = getattr(errno, "ENOTCONN", _HAUSNUMERO + 15)
        ETIMEDOUT = getattr(errno, "ETIMEDOUT", _HAUSNUMERO + 16)
        EHOSTUNREACH = getattr(errno, "EHOSTUNREACH", _HAUSNUMERO + 17)
        ENETRESET = getattr(errno, "ENETRESET", _HAUSNUMERO + 18)

    # Native 0MQ error codes
    EFSM = _HAUSNUMERO + 51
    ENOCOMPATPROTO = _HAUSNUMERO + 52
    ETERM = _HAUSNUMERO + 53
    EMTHREAD = _HAUSNUMERO + 54


class ContextOption(IntEnum):
    """Options for Context.get/set

    .. versionadded:: 23
    """

    IO_THREADS = 1
    MAX_SOCKETS = 2
    SOCKET_LIMIT = 3
    THREAD_PRIORITY = 3
    THREAD_SCHED_POLICY = 4
    MAX_MSGSZ = 5
    MSG_T_SIZE = 6
    THREAD_AFFINITY_CPU_ADD = 7
    THREAD_AFFINITY_CPU_REMOVE = 8
    THREAD_NAME_PREFIX = 9


class SocketType(IntEnum):
    """zmq socket types

    .. versionadded:: 23
    """

    PAIR = 0
    PUB = 1
    SUB = 2
    REQ = 3
    REP = 4
    DEALER = 5
    ROUTER = 6
    PULL = 7
    PUSH = 8
    XPUB = 9
    XSUB = 10
    STREAM = 11

    # deprecated aliases
    XREQ = DEALER
    XREP = ROUTER

    # DRAFT socket types
    SERVER = 12
    CLIENT = 13
    RADIO = 14
    DISH = 15
    GATHER = 16
    SCATTER = 17
    DGRAM = 18
    PEER = 19
    CHANNEL = 20


class _OptType(Enum):
    int = 'int'
    int64 = 'int64'
    bytes = 'bytes'
    fd = 'fd'


class SocketOption(IntEnum):
    """Options for Socket.get/set

    .. versionadded:: 23
    """

    _opt_type: _OptType

    def __new__(cls, value: int, opt_type: _OptType = _OptType.int):
        """Attach option type as `._opt_type`"""
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._opt_type = opt_type
        return obj

    HWM = 1
    AFFINITY = 4, _OptType.int64
    ROUTING_ID = 5, _OptType.bytes
    SUBSCRIBE = 6, _OptType.bytes
    UNSUBSCRIBE = 7, _OptType.bytes
    RATE = 8
    RECOVERY_IVL = 9
    SNDBUF = 11
    RCVBUF = 12
    RCVMORE = 13
    FD = 14, _OptType.fd
    EVENTS = 15
    TYPE = 16
    LINGER = 17
    RECONNECT_IVL = 18
    BACKLOG = 19
    RECONNECT_IVL_MAX = 21
    MAXMSGSIZE = 22, _OptType.int64
    SNDHWM = 23
    RCVHWM = 24
    MULTICAST_HOPS = 25
    RCVTIMEO = 27
    SNDTIMEO = 28
    LAST_ENDPOINT = 32, _OptType.bytes
    ROUTER_MANDATORY = 33
    TCP_KEEPALIVE = 34
    TCP_KEEPALIVE_CNT = 35
    TCP_KEEPALIVE_IDLE = 36
    TCP_KEEPALIVE_INTVL = 37
    IMMEDIATE = 39
    XPUB_VERBOSE = 40
    ROUTER_RAW = 41
    IPV6 = 42
    MECHANISM = 43
    PLAIN_SERVER = 44
    PLAIN_USERNAME = 45, _OptType.bytes
    PLAIN_PASSWORD = 46, _OptType.bytes
    CURVE_SERVER = 47
    CURVE_PUBLICKEY = 48, _OptType.bytes
    CURVE_SECRETKEY = 49, _OptType.bytes
    CURVE_SERVERKEY = 50, _OptType.bytes
    PROBE_ROUTER = 51
    REQ_CORRELATE = 52
    REQ_RELAXED = 53
    CONFLATE = 54
    ZAP_DOMAIN = 55, _OptType.bytes
    ROUTER_HANDOVER = 56
    TOS = 57
    CONNECT_ROUTING_ID = 61, _OptType.bytes
    GSSAPI_SERVER = 62
    GSSAPI_PRINCIPAL = 63, _OptType.bytes
    GSSAPI_SERVICE_PRINCIPAL = 64, _OptType.bytes
    GSSAPI_PLAINTEXT = 65
    HANDSHAKE_IVL = 66
    SOCKS_PROXY = 68, _OptType.bytes
    XPUB_NODROP = 69
    BLOCKY = 70
    XPUB_MANUAL = 71
    XPUB_WELCOME_MSG = 72, _OptType.bytes
    STREAM_NOTIFY = 73
    INVERT_MATCHING = 74
    HEARTBEAT_IVL = 75
    HEARTBEAT_TTL = 76
    HEARTBEAT_TIMEOUT = 77
    XPUB_VERBOSER = 78
    CONNECT_TIMEOUT = 79
    TCP_MAXRT = 80
    THREAD_SAFE = 81
    MULTICAST_MAXTPDU = 84
    VMCI_BUFFER_SIZE = 85, _OptType.int64
    VMCI_BUFFER_MIN_SIZE = 86, _OptType.int64
    VMCI_BUFFER_MAX_SIZE = 87, _OptType.int64
    VMCI_CONNECT_TIMEOUT = 88
    USE_FD = 89
    GSSAPI_PRINCIPAL_NAMETYPE = 90
    GSSAPI_SERVICE_PRINCIPAL_NAMETYPE = 91
    BINDTODEVICE = 92, _OptType.bytes

    # Deprecated options and aliases
    # must not use name-assignment, must have the same value
    IDENTITY = ROUTING_ID
    CONNECT_RID = CONNECT_ROUTING_ID
    TCP_ACCEPT_FILTER = 38, _OptType.bytes
    IPC_FILTER_PID = 58
    IPC_FILTER_UID = 59
    IPC_FILTER_GID = 60
    IPV4ONLY = 31
    DELAY_ATTACH_ON_CONNECT = IMMEDIATE
    FAIL_UNROUTABLE = ROUTER_MANDATORY
    ROUTER_BEHAVIOR = ROUTER_MANDATORY

    # Draft socket options
    ZAP_ENFORCE_DOMAIN = 93
    LOOPBACK_FASTPATH = 94
    METADATA = 95, _OptType.bytes
    MULTICAST_LOOP = 96
    ROUTER_NOTIFY = 97
    XPUB_MANUAL_LAST_VALUE = 98
    SOCKS_USERNAME = 99, _OptType.bytes
    SOCKS_PASSWORD = 100, _OptType.bytes
    IN_BATCH_SIZE = 101
    OUT_BATCH_SIZE = 102
    WSS_KEY_PEM = 103, _OptType.bytes
    WSS_CERT_PEM = 104, _OptType.bytes
    WSS_TRUST_PEM = 105, _OptType.bytes
    WSS_HOSTNAME = 106, _OptType.bytes
    WSS_TRUST_SYSTEM = 107
    ONLY_FIRST_SUBSCRIBE = 108
    RECONNECT_STOP = 109
    HELLO_MSG = 110, _OptType.bytes
    DISCONNECT_MSG = 111, _OptType.bytes
    PRIORITY = 112
    # 4.3.5
    BUSY_POLL = 113
    HICCUP_MSG = 114, _OptType.bytes
    XSUB_VERBOSE_UNSUBSCRIBE = 115
    TOPICS_COUNT = 116
    NORM_MODE = 117
    NORM_UNICAST_NACK = 118
    NORM_BUFFER_SIZE = 119
    NORM_SEGMENT_SIZE = 120
    NORM_BLOCK_SIZE = 121
    NORM_NUM_PARITY = 122
    NORM_NUM_AUTOPARITY = 123
    NORM_PUSH = 124


class MessageOption(IntEnum):
    """Options on zmq.Frame objects

    .. versionadded:: 23
    """

    MORE = 1
    SHARED = 3
    # Deprecated message options
    SRCFD = 2


class Flag(IntFlag):
    """Send/recv flags

    .. versionadded:: 23
    """

    DONTWAIT = 1
    SNDMORE = 2
    NOBLOCK = DONTWAIT


class RouterNotify(IntEnum):
    """Values for zmq.ROUTER_NOTIFY socket option

    .. versionadded:: 26
    .. versionadded:: libzmq-4.3.0 (draft)
    """

    @staticmethod
    def _global_name(name):
        return f"NOTIFY_{name}"

    CONNECT = 1
    DISCONNECT = 2


class NormMode(IntEnum):
    """Values for zmq.NORM_MODE socket option

    .. versionadded:: 26
    .. versionadded:: libzmq-4.3.5 (draft)
    """

    @staticmethod
    def _global_name(name):
        return f"NORM_{name}"

    FIXED = 0
    CC = 1
    CCL = 2
    CCE = 3
    CCE_ECNONLY = 4


class SecurityMechanism(IntEnum):
    """Security mechanisms (as returned by ``socket.get(zmq.MECHANISM)``)

    .. versionadded:: 23
    """

    NULL = 0
    PLAIN = 1
    CURVE = 2
    GSSAPI = 3


class ReconnectStop(IntEnum):
    """Select behavior for socket.reconnect_stop

    .. versionadded:: 25
    """

    @staticmethod
    def _global_name(name):
        return f"RECONNECT_STOP_{name}"

    CONN_REFUSED = 0x1
    HANDSHAKE_FAILED = 0x2
    AFTER_DISCONNECT = 0x4


class Event(IntFlag):
    """Socket monitoring events

    .. versionadded:: 23
    """

    @staticmethod
    def _global_name(name):
        if name.startswith("PROTOCOL_ERROR_"):
            return name
        else:
            # add EVENT_ prefix
            return "EVENT_" + name

    PROTOCOL_ERROR_WS_UNSPECIFIED = 0x30000000
    PROTOCOL_ERROR_ZMTP_UNSPECIFIED = 0x10000000
    PROTOCOL_ERROR_ZMTP_UNEXPECTED_COMMAND = 0x10000001
    PROTOCOL_ERROR_ZMTP_INVALID_SEQUENCE = 0x10000002
    PROTOCOL_ERROR_ZMTP_KEY_EXCHANGE = 0x10000003
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_UNSPECIFIED = 0x10000011
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_MESSAGE = 0x10000012
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_HELLO = 0x10000013
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_INITIATE = 0x10000014
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_ERROR = 0x10000015
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_READY = 0x10000016
    PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_WELCOME = 0x10000017
    PROTOCOL_ERROR_ZMTP_INVALID_METADATA = 0x10000018

    PROTOCOL_ERROR_ZMTP_CRYPTOGRAPHIC = 0x11000001
    PROTOCOL_ERROR_ZMTP_MECHANISM_MISMATCH = 0x11000002
    PROTOCOL_ERROR_ZAP_UNSPECIFIED = 0x20000000
    PROTOCOL_ERROR_ZAP_MALFORMED_REPLY = 0x20000001
    PROTOCOL_ERROR_ZAP_BAD_REQUEST_ID = 0x20000002
    PROTOCOL_ERROR_ZAP_BAD_VERSION = 0x20000003
    PROTOCOL_ERROR_ZAP_INVALID_STATUS_CODE = 0x20000004
    PROTOCOL_ERROR_ZAP_INVALID_METADATA = 0x20000005

    # define event types _after_ overlapping protocol error masks
    CONNECTED = 0x0001
    CONNECT_DELAYED = 0x0002
    CONNECT_RETRIED = 0x0004
    LISTENING = 0x0008
    BIND_FAILED = 0x0010
    ACCEPTED = 0x0020
    ACCEPT_FAILED = 0x0040
    CLOSED = 0x0080
    CLOSE_FAILED = 0x0100
    DISCONNECTED = 0x0200
    MONITOR_STOPPED = 0x0400

    HANDSHAKE_FAILED_NO_DETAIL = 0x0800
    HANDSHAKE_SUCCEEDED = 0x1000
    HANDSHAKE_FAILED_PROTOCOL = 0x2000
    HANDSHAKE_FAILED_AUTH = 0x4000

    ALL_V1 = 0xFFFF
    ALL = ALL_V1

    # DRAFT Socket monitoring events
    PIPES_STATS = 0x10000
    ALL_V2 = ALL_V1 | PIPES_STATS


class PollEvent(IntFlag):
    """Which events to poll for in poll methods

    .. versionadded: 23
    """

    POLLIN = 1
    POLLOUT = 2
    POLLERR = 4
    POLLPRI = 8


class DeviceType(IntEnum):
    """Device type constants for zmq.device

    .. versionadded: 23
    """

    STREAMER = 1
    FORWARDER = 2
    QUEUE = 3


# AUTOGENERATED_BELOW_HERE


IO_THREADS: int = ContextOption.IO_THREADS
MAX_SOCKETS: int = ContextOption.MAX_SOCKETS
SOCKET_LIMIT: int = ContextOption.SOCKET_LIMIT
THREAD_PRIORITY: int = ContextOption.THREAD_PRIORITY
THREAD_SCHED_POLICY: int = ContextOption.THREAD_SCHED_POLICY
MAX_MSGSZ: int = ContextOption.MAX_MSGSZ
MSG_T_SIZE: int = ContextOption.MSG_T_SIZE
THREAD_AFFINITY_CPU_ADD: int = ContextOption.THREAD_AFFINITY_CPU_ADD
THREAD_AFFINITY_CPU_REMOVE: int = ContextOption.THREAD_AFFINITY_CPU_REMOVE
THREAD_NAME_PREFIX: int = ContextOption.THREAD_NAME_PREFIX
STREAMER: int = DeviceType.STREAMER
FORWARDER: int = DeviceType.FORWARDER
QUEUE: int = DeviceType.QUEUE
EAGAIN: int = Errno.EAGAIN
EFAULT: int = Errno.EFAULT
EINVAL: int = Errno.EINVAL
ENOTSUP: int = Errno.ENOTSUP
EPROTONOSUPPORT: int = Errno.EPROTONOSUPPORT
ENOBUFS: int = Errno.ENOBUFS
ENETDOWN: int = Errno.ENETDOWN
EADDRINUSE: int = Errno.EADDRINUSE
EADDRNOTAVAIL: int = Errno.EADDRNOTAVAIL
ECONNREFUSED: int = Errno.ECONNREFUSED
EINPROGRESS: int = Errno.EINPROGRESS
ENOTSOCK: int = Errno.ENOTSOCK
EMSGSIZE: int = Errno.EMSGSIZE
EAFNOSUPPORT: int = Errno.EAFNOSUPPORT
ENETUNREACH: int = Errno.ENETUNREACH
ECONNABORTED: int = Errno.ECONNABORTED
ECONNRESET: int = Errno.ECONNRESET
ENOTCONN: int = Errno.ENOTCONN
ETIMEDOUT: int = Errno.ETIMEDOUT
EHOSTUNREACH: int = Errno.EHOSTUNREACH
ENETRESET: int = Errno.ENETRESET
EFSM: int = Errno.EFSM
ENOCOMPATPROTO: int = Errno.ENOCOMPATPROTO
ETERM: int = Errno.ETERM
EMTHREAD: int = Errno.EMTHREAD
PROTOCOL_ERROR_WS_UNSPECIFIED: int = Event.PROTOCOL_ERROR_WS_UNSPECIFIED
PROTOCOL_ERROR_ZMTP_UNSPECIFIED: int = Event.PROTOCOL_ERROR_ZMTP_UNSPECIFIED
PROTOCOL_ERROR_ZMTP_UNEXPECTED_COMMAND: int = (
    Event.PROTOCOL_ERROR_ZMTP_UNEXPECTED_COMMAND
)
PROTOCOL_ERROR_ZMTP_INVALID_SEQUENCE: int = Event.PROTOCOL_ERROR_ZMTP_INVALID_SEQUENCE
PROTOCOL_ERROR_ZMTP_KEY_EXCHANGE: int = Event.PROTOCOL_ERROR_ZMTP_KEY_EXCHANGE
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_UNSPECIFIED: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_UNSPECIFIED
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_MESSAGE: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_MESSAGE
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_HELLO: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_HELLO
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_INITIATE: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_INITIATE
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_ERROR: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_ERROR
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_READY: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_READY
)
PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_WELCOME: int = (
    Event.PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_WELCOME
)
PROTOCOL_ERROR_ZMTP_INVALID_METADATA: int = Event.PROTOCOL_ERROR_ZMTP_INVALID_METADATA
PROTOCOL_ERROR_ZMTP_CRYPTOGRAPHIC: int = Event.PROTOCOL_ERROR_ZMTP_CRYPTOGRAPHIC
PROTOCOL_ERROR_ZMTP_MECHANISM_MISMATCH: int = (
    Event.PROTOCOL_ERROR_ZMTP_MECHANISM_MISMATCH
)
PROTOCOL_ERROR_ZAP_UNSPECIFIED: int = Event.PROTOCOL_ERROR_ZAP_UNSPECIFIED
PROTOCOL_ERROR_ZAP_MALFORMED_REPLY: int = Event.PROTOCOL_ERROR_ZAP_MALFORMED_REPLY
PROTOCOL_ERROR_ZAP_BAD_REQUEST_ID: int = Event.PROTOCOL_ERROR_ZAP_BAD_REQUEST_ID
PROTOCOL_ERROR_ZAP_BAD_VERSION: int = Event.PROTOCOL_ERROR_ZAP_BAD_VERSION
PROTOCOL_ERROR_ZAP_INVALID_STATUS_CODE: int = (
    Event.PROTOCOL_ERROR_ZAP_INVALID_STATUS_CODE
)
PROTOCOL_ERROR_ZAP_INVALID_METADATA: int = Event.PROTOCOL_ERROR_ZAP_INVALID_METADATA
EVENT_CONNECTED: int = Event.CONNECTED
EVENT_CONNECT_DELAYED: int = Event.CONNECT_DELAYED
EVENT_CONNECT_RETRIED: int = Event.CONNECT_RETRIED
EVENT_LISTENING: int = Event.LISTENING
EVENT_BIND_FAILED: int = Event.BIND_FAILED
EVENT_ACCEPTED: int = Event.ACCEPTED
EVENT_ACCEPT_FAILED: int = Event.ACCEPT_FAILED
EVENT_CLOSED: int = Event.CLOSED
EVENT_CLOSE_FAILED: int = Event.CLOSE_FAILED
EVENT_DISCONNECTED: int = Event.DISCONNECTED
EVENT_MONITOR_STOPPED: int = Event.MONITOR_STOPPED
EVENT_HANDSHAKE_FAILED_NO_DETAIL: int = Event.HANDSHAKE_FAILED_NO_DETAIL
EVENT_HANDSHAKE_SUCCEEDED: int = Event.HANDSHAKE_SUCCEEDED
EVENT_HANDSHAKE_FAILED_PROTOCOL: int = Event.HANDSHAKE_FAILED_PROTOCOL
EVENT_HANDSHAKE_FAILED_AUTH: int = Event.HANDSHAKE_FAILED_AUTH
EVENT_ALL_V1: int = Event.ALL_V1
EVENT_ALL: int = Event.ALL
EVENT_PIPES_STATS: int = Event.PIPES_STATS
EVENT_ALL_V2: int = Event.ALL_V2
DONTWAIT: int = Flag.DONTWAIT
SNDMORE: int = Flag.SNDMORE
NOBLOCK: int = Flag.NOBLOCK
MORE: int = MessageOption.MORE
SHARED: int = MessageOption.SHARED
SRCFD: int = MessageOption.SRCFD
NORM_FIXED: int = NormMode.FIXED
NORM_CC: int = NormMode.CC
NORM_CCL: int = NormMode.CCL
NORM_CCE: int = NormMode.CCE
NORM_CCE_ECNONLY: int = NormMode.CCE_ECNONLY
POLLIN: int = PollEvent.POLLIN
POLLOUT: int = PollEvent.POLLOUT
POLLERR: int = PollEvent.POLLERR
POLLPRI: int = PollEvent.POLLPRI
RECONNECT_STOP_CONN_REFUSED: int = ReconnectStop.CONN_REFUSED
RECONNECT_STOP_HANDSHAKE_FAILED: int = ReconnectStop.HANDSHAKE_FAILED
RECONNECT_STOP_AFTER_DISCONNECT: int = ReconnectStop.AFTER_DISCONNECT
NOTIFY_CONNECT: int = RouterNotify.CONNECT
NOTIFY_DISCONNECT: int = RouterNotify.DISCONNECT
NULL: int = SecurityMechanism.NULL
PLAIN: int = SecurityMechanism.PLAIN
CURVE: int = SecurityMechanism.CURVE
GSSAPI: int = SecurityMechanism.GSSAPI
HWM: int = SocketOption.HWM
AFFINITY: int = SocketOption.AFFINITY
ROUTING_ID: int = SocketOption.ROUTING_ID
SUBSCRIBE: int = SocketOption.SUBSCRIBE
UNSUBSCRIBE: int = SocketOption.UNSUBSCRIBE
RATE: int = SocketOption.RATE
RECOVERY_IVL: int = SocketOption.RECOVERY_IVL
SNDBUF: int = SocketOption.SNDBUF
RCVBUF: int = SocketOption.RCVBUF
RCVMORE: int = SocketOption.RCVMORE
FD: int = SocketOption.FD
EVENTS: int = SocketOption.EVENTS
TYPE: int = SocketOption.TYPE
LINGER: int = SocketOption.LINGER
RECONNECT_IVL: int = SocketOption.RECONNECT_IVL
BACKLOG: int = SocketOption.BACKLOG
RECONNECT_IVL_MAX: int = SocketOption.RECONNECT_IVL_MAX
MAXMSGSIZE: int = SocketOption.MAXMSGSIZE
SNDHWM: int = SocketOption.SNDHWM
RCVHWM: int = SocketOption.RCVHWM
MULTICAST_HOPS: int = SocketOption.MULTICAST_HOPS
RCVTIMEO: int = SocketOption.RCVTIMEO
SNDTIMEO: int = SocketOption.SNDTIMEO
LAST_ENDPOINT: int = SocketOption.LAST_ENDPOINT
ROUTER_MANDATORY: int = SocketOption.ROUTER_MANDATORY
TCP_KEEPALIVE: int = SocketOption.TCP_KEEPALIVE
TCP_KEEPALIVE_CNT: int = SocketOption.TCP_KEEPALIVE_CNT
TCP_KEEPALIVE_IDLE: int = SocketOption.TCP_KEEPALIVE_IDLE
TCP_KEEPALIVE_INTVL: int = SocketOption.TCP_KEEPALIVE_INTVL
IMMEDIATE: int = SocketOption.IMMEDIATE
XPUB_VERBOSE: int = SocketOption.XPUB_VERBOSE
ROUTER_RAW: int = SocketOption.ROUTER_RAW
IPV6: int = SocketOption.IPV6
MECHANISM: int = SocketOption.MECHANISM
PLAIN_SERVER: int = SocketOption.PLAIN_SERVER
PLAIN_USERNAME: int = SocketOption.PLAIN_USERNAME
PLAIN_PASSWORD: int = SocketOption.PLAIN_PASSWORD
CURVE_SERVER: int = SocketOption.CURVE_SERVER
CURVE_PUBLICKEY: int = SocketOption.CURVE_PUBLICKEY
CURVE_SECRETKEY: int = SocketOption.CURVE_SECRETKEY
CURVE_SERVERKEY: int = SocketOption.CURVE_SERVERKEY
PROBE_ROUTER: int = SocketOption.PROBE_ROUTER
REQ_CORRELATE: int = SocketOption.REQ_CORRELATE
REQ_RELAXED: int = SocketOption.REQ_RELAXED
CONFLATE: int = SocketOption.CONFLATE
ZAP_DOMAIN: int = SocketOption.ZAP_DOMAIN
ROUTER_HANDOVER: int = SocketOption.ROUTER_HANDOVER
TOS: int = SocketOption.TOS
CONNECT_ROUTING_ID: int = SocketOption.CONNECT_ROUTING_ID
GSSAPI_SERVER: int = SocketOption.GSSAPI_SERVER
GSSAPI_PRINCIPAL: int = SocketOption.GSSAPI_PRINCIPAL
GSSAPI_SERVICE_PRINCIPAL: int = SocketOption.GSSAPI_SERVICE_PRINCIPAL
GSSAPI_PLAINTEXT: int = SocketOption.GSSAPI_PLAINTEXT
HANDSHAKE_IVL: int = SocketOption.HANDSHAKE_IVL
SOCKS_PROXY: int = SocketOption.SOCKS_PROXY
XPUB_NODROP: int = SocketOption.XPUB_NODROP
BLOCKY: int = SocketOption.BLOCKY
XPUB_MANUAL: int = SocketOption.XPUB_MANUAL
XPUB_WELCOME_MSG: int = SocketOption.XPUB_WELCOME_MSG
STREAM_NOTIFY: int = SocketOption.STREAM_NOTIFY
INVERT_MATCHING: int = SocketOption.INVERT_MATCHING
HEARTBEAT_IVL: int = SocketOption.HEARTBEAT_IVL
HEARTBEAT_TTL: int = SocketOption.HEARTBEAT_TTL
HEARTBEAT_TIMEOUT: int = SocketOption.HEARTBEAT_TIMEOUT
XPUB_VERBOSER: int = SocketOption.XPUB_VERBOSER
CONNECT_TIMEOUT: int = SocketOption.CONNECT_TIMEOUT
TCP_MAXRT: int = SocketOption.TCP_MAXRT
THREAD_SAFE: int = SocketOption.THREAD_SAFE
MULTICAST_MAXTPDU: int = SocketOption.MULTICAST_MAXTPDU
VMCI_BUFFER_SIZE: int = SocketOption.VMCI_BUFFER_SIZE
VMCI_BUFFER_MIN_SIZE: int = SocketOption.VMCI_BUFFER_MIN_SIZE
VMCI_BUFFER_MAX_SIZE: int = SocketOption.VMCI_BUFFER_MAX_SIZE
VMCI_CONNECT_TIMEOUT: int = SocketOption.VMCI_CONNECT_TIMEOUT
USE_FD: int = SocketOption.USE_FD
GSSAPI_PRINCIPAL_NAMETYPE: int = SocketOption.GSSAPI_PRINCIPAL_NAMETYPE
GSSAPI_SERVICE_PRINCIPAL_NAMETYPE: int = SocketOption.GSSAPI_SERVICE_PRINCIPAL_NAMETYPE
BINDTODEVICE: int = SocketOption.BINDTODEVICE
IDENTITY: int = SocketOption.IDENTITY
CONNECT_RID: int = SocketOption.CONNECT_RID
TCP_ACCEPT_FILTER: int = SocketOption.TCP_ACCEPT_FILTER
IPC_FILTER_PID: int = SocketOption.IPC_FILTER_PID
IPC_FILTER_UID: int = SocketOption.IPC_FILTER_UID
IPC_FILTER_GID: int = SocketOption.IPC_FILTER_GID
IPV4ONLY: int = SocketOption.IPV4ONLY
DELAY_ATTACH_ON_CONNECT: int = SocketOption.DELAY_ATTACH_ON_CONNECT
FAIL_UNROUTABLE: int = SocketOption.FAIL_UNROUTABLE
ROUTER_BEHAVIOR: int = SocketOption.ROUTER_BEHAVIOR
ZAP_ENFORCE_DOMAIN: int = SocketOption.ZAP_ENFORCE_DOMAIN
LOOPBACK_FASTPATH: int = SocketOption.LOOPBACK_FASTPATH
METADATA: int = SocketOption.METADATA
MULTICAST_LOOP: int = SocketOption.MULTICAST_LOOP
ROUTER_NOTIFY: int = SocketOption.ROUTER_NOTIFY
XPUB_MANUAL_LAST_VALUE: int = SocketOption.XPUB_MANUAL_LAST_VALUE
SOCKS_USERNAME: int = SocketOption.SOCKS_USERNAME
SOCKS_PASSWORD: int = SocketOption.SOCKS_PASSWORD
IN_BATCH_SIZE: int = SocketOption.IN_BATCH_SIZE
OUT_BATCH_SIZE: int = SocketOption.OUT_BATCH_SIZE
WSS_KEY_PEM: int = SocketOption.WSS_KEY_PEM
WSS_CERT_PEM: int = SocketOption.WSS_CERT_PEM
WSS_TRUST_PEM: int = SocketOption.WSS_TRUST_PEM
WSS_HOSTNAME: int = SocketOption.WSS_HOSTNAME
WSS_TRUST_SYSTEM: int = SocketOption.WSS_TRUST_SYSTEM
ONLY_FIRST_SUBSCRIBE: int = SocketOption.ONLY_FIRST_SUBSCRIBE
RECONNECT_STOP: int = SocketOption.RECONNECT_STOP
HELLO_MSG: int = SocketOption.HELLO_MSG
DISCONNECT_MSG: int = SocketOption.DISCONNECT_MSG
PRIORITY: int = SocketOption.PRIORITY
BUSY_POLL: int = SocketOption.BUSY_POLL
HICCUP_MSG: int = SocketOption.HICCUP_MSG
XSUB_VERBOSE_UNSUBSCRIBE: int = SocketOption.XSUB_VERBOSE_UNSUBSCRIBE
TOPICS_COUNT: int = SocketOption.TOPICS_COUNT
NORM_MODE: int = SocketOption.NORM_MODE
NORM_UNICAST_NACK: int = SocketOption.NORM_UNICAST_NACK
NORM_BUFFER_SIZE: int = SocketOption.NORM_BUFFER_SIZE
NORM_SEGMENT_SIZE: int = SocketOption.NORM_SEGMENT_SIZE
NORM_BLOCK_SIZE: int = SocketOption.NORM_BLOCK_SIZE
NORM_NUM_PARITY: int = SocketOption.NORM_NUM_PARITY
NORM_NUM_AUTOPARITY: int = SocketOption.NORM_NUM_AUTOPARITY
NORM_PUSH: int = SocketOption.NORM_PUSH
PAIR: int = SocketType.PAIR
PUB: int = SocketType.PUB
SUB: int = SocketType.SUB
REQ: int = SocketType.REQ
REP: int = SocketType.REP
DEALER: int = SocketType.DEALER
ROUTER: int = SocketType.ROUTER
PULL: int = SocketType.PULL
PUSH: int = SocketType.PUSH
XPUB: int = SocketType.XPUB
XSUB: int = SocketType.XSUB
STREAM: int = SocketType.STREAM
XREQ: int = SocketType.XREQ
XREP: int = SocketType.XREP
SERVER: int = SocketType.SERVER
CLIENT: int = SocketType.CLIENT
RADIO: int = SocketType.RADIO
DISH: int = SocketType.DISH
GATHER: int = SocketType.GATHER
SCATTER: int = SocketType.SCATTER
DGRAM: int = SocketType.DGRAM
PEER: int = SocketType.PEER
CHANNEL: int = SocketType.CHANNEL

__all__: list[str] = [
    "ContextOption",
    "IO_THREADS",
    "MAX_SOCKETS",
    "SOCKET_LIMIT",
    "THREAD_PRIORITY",
    "THREAD_SCHED_POLICY",
    "MAX_MSGSZ",
    "MSG_T_SIZE",
    "THREAD_AFFINITY_CPU_ADD",
    "THREAD_AFFINITY_CPU_REMOVE",
    "THREAD_NAME_PREFIX",
    "DeviceType",
    "STREAMER",
    "FORWARDER",
    "QUEUE",
    "Enum",
    "Errno",
    "EAGAIN",
    "EFAULT",
    "EINVAL",
    "ENOTSUP",
    "EPROTONOSUPPORT",
    "ENOBUFS",
    "ENETDOWN",
    "EADDRINUSE",
    "EADDRNOTAVAIL",
    "ECONNREFUSED",
    "EINPROGRESS",
    "ENOTSOCK",
    "EMSGSIZE",
    "EAFNOSUPPORT",
    "ENETUNREACH",
    "ECONNABORTED",
    "ECONNRESET",
    "ENOTCONN",
    "ETIMEDOUT",
    "EHOSTUNREACH",
    "ENETRESET",
    "EFSM",
    "ENOCOMPATPROTO",
    "ETERM",
    "EMTHREAD",
    "Event",
    "PROTOCOL_ERROR_WS_UNSPECIFIED",
    "PROTOCOL_ERROR_ZMTP_UNSPECIFIED",
    "PROTOCOL_ERROR_ZMTP_UNEXPECTED_COMMAND",
    "PROTOCOL_ERROR_ZMTP_INVALID_SEQUENCE",
    "PROTOCOL_ERROR_ZMTP_KEY_EXCHANGE",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_UNSPECIFIED",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_MESSAGE",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_HELLO",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_INITIATE",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_ERROR",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_READY",
    "PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_WELCOME",
    "PROTOCOL_ERROR_ZMTP_INVALID_METADATA",
    "PROTOCOL_ERROR_ZMTP_CRYPTOGRAPHIC",
    "PROTOCOL_ERROR_ZMTP_MECHANISM_MISMATCH",
    "PROTOCOL_ERROR_ZAP_UNSPECIFIED",
    "PROTOCOL_ERROR_ZAP_MALFORMED_REPLY",
    "PROTOCOL_ERROR_ZAP_BAD_REQUEST_ID",
    "PROTOCOL_ERROR_ZAP_BAD_VERSION",
    "PROTOCOL_ERROR_ZAP_INVALID_STATUS_CODE",
    "PROTOCOL_ERROR_ZAP_INVALID_METADATA",
    "EVENT_CONNECTED",
    "EVENT_CONNECT_DELAYED",
    "EVENT_CONNECT_RETRIED",
    "EVENT_LISTENING",
    "EVENT_BIND_FAILED",
    "EVENT_ACCEPTED",
    "EVENT_ACCEPT_FAILED",
    "EVENT_CLOSED",
    "EVENT_CLOSE_FAILED",
    "EVENT_DISCONNECTED",
    "EVENT_MONITOR_STOPPED",
    "EVENT_HANDSHAKE_FAILED_NO_DETAIL",
    "EVENT_HANDSHAKE_SUCCEEDED",
    "EVENT_HANDSHAKE_FAILED_PROTOCOL",
    "EVENT_HANDSHAKE_FAILED_AUTH",
    "EVENT_ALL_V1",
    "EVENT_ALL",
    "EVENT_PIPES_STATS",
    "EVENT_ALL_V2",
    "Flag",
    "DONTWAIT",
    "SNDMORE",
    "NOBLOCK",
    "IntEnum",
    "IntFlag",
    "MessageOption",
    "MORE",
    "SHARED",
    "SRCFD",
    "NormMode",
    "NORM_FIXED",
    "NORM_CC",
    "NORM_CCL",
    "NORM_CCE",
    "NORM_CCE_ECNONLY",
    "PollEvent",
    "POLLIN",
    "POLLOUT",
    "POLLERR",
    "POLLPRI",
    "ReconnectStop",
    "RECONNECT_STOP_CONN_REFUSED",
    "RECONNECT_STOP_HANDSHAKE_FAILED",
    "RECONNECT_STOP_AFTER_DISCONNECT",
    "RouterNotify",
    "NOTIFY_CONNECT",
    "NOTIFY_DISCONNECT",
    "SecurityMechanism",
    "NULL",
    "PLAIN",
    "CURVE",
    "GSSAPI",
    "SocketOption",
    "HWM",
    "AFFINITY",
    "ROUTING_ID",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "RATE",
    "RECOVERY_IVL",
    "SNDBUF",
    "RCVBUF",
    "RCVMORE",
    "FD",
    "EVENTS",
    "TYPE",
    "LINGER",
    "RECONNECT_IVL",
    "BACKLOG",
    "RECONNECT_IVL_MAX",
    "MAXMSGSIZE",
    "SNDHWM",
    "RCVHWM",
    "MULTICAST_HOPS",
    "RCVTIMEO",
    "SNDTIMEO",
    "LAST_ENDPOINT",
    "ROUTER_MANDATORY",
    "TCP_KEEPALIVE",
    "TCP_KEEPALIVE_CNT",
    "TCP_KEEPALIVE_IDLE",
    "TCP_KEEPALIVE_INTVL",
    "IMMEDIATE",
    "XPUB_VERBOSE",
    "ROUTER_RAW",
    "IPV6",
    "MECHANISM",
    "PLAIN_SERVER",
    "PLAIN_USERNAME",
    "PLAIN_PASSWORD",
    "CURVE_SERVER",
    "CURVE_PUBLICKEY",
    "CURVE_SECRETKEY",
    "CURVE_SERVERKEY",
    "PROBE_ROUTER",
    "REQ_CORRELATE",
    "REQ_RELAXED",
    "CONFLATE",
    "ZAP_DOMAIN",
    "ROUTER_HANDOVER",
    "TOS",
    "CONNECT_ROUTING_ID",
    "GSSAPI_SERVER",
    "GSSAPI_PRINCIPAL",
    "GSSAPI_SERVICE_PRINCIPAL",
    "GSSAPI_PLAINTEXT",
    "HANDSHAKE_IVL",
    "SOCKS_PROXY",
    "XPUB_NODROP",
    "BLOCKY",
    "XPUB_MANUAL",
    "XPUB_WELCOME_MSG",
    "STREAM_NOTIFY",
    "INVERT_MATCHING",
    "HEARTBEAT_IVL",
    "HEARTBEAT_TTL",
    "HEARTBEAT_TIMEOUT",
    "XPUB_VERBOSER",
    "CONNECT_TIMEOUT",
    "TCP_MAXRT",
    "THREAD_SAFE",
    "MULTICAST_MAXTPDU",
    "VMCI_BUFFER_SIZE",
    "VMCI_BUFFER_MIN_SIZE",
    "VMCI_BUFFER_MAX_SIZE",
    "VMCI_CONNECT_TIMEOUT",
    "USE_FD",
    "GSSAPI_PRINCIPAL_NAMETYPE",
    "GSSAPI_SERVICE_PRINCIPAL_NAMETYPE",
    "BINDTODEVICE",
    "IDENTITY",
    "CONNECT_RID",
    "TCP_ACCEPT_FILTER",
    "IPC_FILTER_PID",
    "IPC_FILTER_UID",
    "IPC_FILTER_GID",
    "IPV4ONLY",
    "DELAY_ATTACH_ON_CONNECT",
    "FAIL_UNROUTABLE",
    "ROUTER_BEHAVIOR",
    "ZAP_ENFORCE_DOMAIN",
    "LOOPBACK_FASTPATH",
    "METADATA",
    "MULTICAST_LOOP",
    "ROUTER_NOTIFY",
    "XPUB_MANUAL_LAST_VALUE",
    "SOCKS_USERNAME",
    "SOCKS_PASSWORD",
    "IN_BATCH_SIZE",
    "OUT_BATCH_SIZE",
    "WSS_KEY_PEM",
    "WSS_CERT_PEM",
    "WSS_TRUST_PEM",
    "WSS_HOSTNAME",
    "WSS_TRUST_SYSTEM",
    "ONLY_FIRST_SUBSCRIBE",
    "RECONNECT_STOP",
    "HELLO_MSG",
    "DISCONNECT_MSG",
    "PRIORITY",
    "BUSY_POLL",
    "HICCUP_MSG",
    "XSUB_VERBOSE_UNSUBSCRIBE",
    "TOPICS_COUNT",
    "NORM_MODE",
    "NORM_UNICAST_NACK",
    "NORM_BUFFER_SIZE",
    "NORM_SEGMENT_SIZE",
    "NORM_BLOCK_SIZE",
    "NORM_NUM_PARITY",
    "NORM_NUM_AUTOPARITY",
    "NORM_PUSH",
    "SocketType",
    "PAIR",
    "PUB",
    "SUB",
    "REQ",
    "REP",
    "DEALER",
    "ROUTER",
    "PULL",
    "PUSH",
    "XPUB",
    "XSUB",
    "STREAM",
    "XREQ",
    "XREP",
    "SERVER",
    "CLIENT",
    "RADIO",
    "DISH",
    "GATHER",
    "SCATTER",
    "DGRAM",
    "PEER",
    "CHANNEL",
]

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_assertions.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections.abc
from typing import Any, List, Optional, Pattern, Sequence, Union
from urllib.parse import urljoin

from playwright._impl._api_structures import (
    AriaRole,
    ExpectedTextValue,
    FrameExpectOptions,
)
from playwright._impl._connection import format_call_log
from playwright._impl._errors import Error
from playwright._impl._fetch import APIResponse
from playwright._impl._helper import is_textual_mime_type
from playwright._impl._locator import Locator
from playwright._impl._page import Page
from playwright._impl._str_utils import escape_regex_flags


class AssertionsBase:
    def __init__(
        self,
        locator: Locator,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        self._actual_locator = locator
        self._loop = locator._loop
        self._dispatcher_fiber = locator._dispatcher_fiber
        self._timeout = timeout
        self._is_not = is_not
        self._custom_message = message

    async def _expect_impl(
        self,
        expression: str,
        expect_options: FrameExpectOptions,
        expected: Any,
        message: str,
    ) -> None:
        __tracebackhide__ = True
        expect_options["isNot"] = self._is_not
        if expect_options.get("timeout") is None:
            expect_options["timeout"] = self._timeout or 5_000
        if expect_options["isNot"]:
            message = message.replace("expected to", "expected not to")
        if "useInnerText" in expect_options and expect_options["useInnerText"] is None:
            del expect_options["useInnerText"]
        result = await self._actual_locator._expect(expression, expect_options)
        if result["matches"] == self._is_not:
            actual = result.get("received")
            if self._custom_message:
                out_message = self._custom_message
                if expected is not None:
                    out_message += f"\nExpected value: '{expected or '<None>'}'"
            else:
                out_message = (
                    f"{message} '{expected}'" if expected is not None else f"{message}"
                )
            raise AssertionError(
                f"{out_message}\nActual value: {actual} {format_call_log(result.get('log'))}"
            )


class PageAssertions(AssertionsBase):
    def __init__(
        self,
        page: Page,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(page.locator(":root"), timeout, is_not, message)
        self._actual_page = page

    @property
    def _not(self) -> "PageAssertions":
        return PageAssertions(
            self._actual_page, self._timeout, not self._is_not, self._custom_message
        )

    async def to_have_title(
        self, titleOrRegExp: Union[Pattern[str], str], timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [titleOrRegExp], normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.title",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            titleOrRegExp,
            "Page title expected to be",
        )

    async def not_to_have_title(
        self, titleOrRegExp: Union[Pattern[str], str], timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_title(titleOrRegExp, timeout)

    async def to_have_url(
        self,
        urlOrRegExp: Union[str, Pattern[str]],
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        base_url = self._actual_page.context._options.get("baseURL")
        if isinstance(urlOrRegExp, str) and base_url:
            urlOrRegExp = urljoin(base_url, urlOrRegExp)
        expected_text = to_expected_text_values([urlOrRegExp], ignoreCase=ignoreCase)
        await self._expect_impl(
            "to.have.url",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            urlOrRegExp,
            "Page URL expected to be",
        )

    async def not_to_have_url(
        self,
        urlOrRegExp: Union[Pattern[str], str],
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_url(urlOrRegExp, timeout, ignoreCase)


class LocatorAssertions(AssertionsBase):
    def __init__(
        self,
        locator: Locator,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(locator, timeout, is_not, message)
        self._actual_locator = locator

    @property
    def _not(self) -> "LocatorAssertions":
        return LocatorAssertions(
            self._actual_locator, self._timeout, not self._is_not, self._custom_message
        )

    async def to_contain_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(
                expected,
                match_substring=True,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.contain.text.array",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to contain text",
            )
        else:
            expected_text = to_expected_text_values(
                [expected],
                match_substring=True,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.have.text",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to contain text",
            )

    async def not_to_contain_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_contain_text(expected, useInnerText, timeout, ignoreCase)

    async def to_have_attribute(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value], ignoreCase=ignoreCase)
        await self._expect_impl(
            "to.have.attribute.value",
            FrameExpectOptions(
                expressionArg=name, expectedText=expected_text, timeout=timeout
            ),
            value,
            "Locator expected to have attribute",
        )

    async def not_to_have_attribute(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_attribute(
            name, value, ignoreCase=ignoreCase, timeout=timeout
        )

    async def to_have_class(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(expected)
            await self._expect_impl(
                "to.have.class.array",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to have class",
            )
        else:
            expected_text = to_expected_text_values([expected])
            await self._expect_impl(
                "to.have.class",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to have class",
            )

    async def not_to_have_class(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_class(expected, timeout)

    async def to_contain_class(
        self,
        expected: Union[
            Sequence[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(expected)
            await self._expect_impl(
                "to.contain.class.array",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to contain class names",
            )
        else:
            expected_text = to_expected_text_values([expected])
            await self._expect_impl(
                "to.contain.class",
                FrameExpectOptions(expectedText=expected_text, timeout=timeout),
                expected,
                "Locator expected to contain class",
            )

    async def not_to_contain_class(
        self,
        expected: Union[
            Sequence[str],
            str,
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_contain_class(expected, timeout)

    async def to_have_count(
        self,
        count: int,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.have.count",
            FrameExpectOptions(expectedNumber=count, timeout=timeout),
            count,
            "Locator expected to have count",
        )

    async def not_to_have_count(
        self,
        count: int,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_count(count, timeout)

    async def to_have_css(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value])
        await self._expect_impl(
            "to.have.css",
            FrameExpectOptions(
                expressionArg=name, expectedText=expected_text, timeout=timeout
            ),
            value,
            "Locator expected to have CSS",
        )

    async def not_to_have_css(
        self,
        name: str,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_css(name, value, timeout)

    async def to_have_id(
        self,
        id: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([id])
        await self._expect_impl(
            "to.have.id",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            id,
            "Locator expected to have ID",
        )

    async def not_to_have_id(
        self,
        id: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_id(id, timeout)

    async def to_have_js_property(
        self,
        name: str,
        value: Any,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.have.property",
            FrameExpectOptions(
                expressionArg=name, expectedValue=value, timeout=timeout
            ),
            value,
            "Locator expected to have JS Property",
        )

    async def not_to_have_js_property(
        self,
        name: str,
        value: Any,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_js_property(name, value, timeout)

    async def to_have_value(
        self,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values([value])
        await self._expect_impl(
            "to.have.value",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            value,
            "Locator expected to have Value",
        )

    async def not_to_have_value(
        self,
        value: Union[str, Pattern[str]],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_value(value, timeout)

    async def to_have_values(
        self,
        values: Union[
            Sequence[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]]
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_text = to_expected_text_values(values)
        await self._expect_impl(
            "to.have.values",
            FrameExpectOptions(expectedText=expected_text, timeout=timeout),
            values,
            "Locator expected to have Values",
        )

    async def not_to_have_values(
        self,
        values: Union[
            Sequence[str], Sequence[Pattern[str]], Sequence[Union[Pattern[str], str]]
        ],
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_values(values, timeout)

    async def to_have_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        if isinstance(expected, collections.abc.Sequence) and not isinstance(
            expected, str
        ):
            expected_text = to_expected_text_values(
                expected,
                normalize_white_space=True,
                ignoreCase=ignoreCase,
            )
            await self._expect_impl(
                "to.have.text.array",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to have text",
            )
        else:
            expected_text = to_expected_text_values(
                [expected], normalize_white_space=True, ignoreCase=ignoreCase
            )
            await self._expect_impl(
                "to.have.text",
                FrameExpectOptions(
                    expectedText=expected_text,
                    useInnerText=useInnerText,
                    timeout=timeout,
                ),
                expected,
                "Locator expected to have text",
            )

    async def not_to_have_text(
        self,
        expected: Union[
            Sequence[str],
            Sequence[Pattern[str]],
            Sequence[Union[Pattern[str], str]],
            Pattern[str],
            str,
        ],
        useInnerText: bool = None,
        timeout: float = None,
        ignoreCase: bool = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_text(expected, useInnerText, timeout, ignoreCase)

    async def to_be_attached(
        self,
        attached: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if attached is None:
            attached = True
        attached_string = "attached" if attached else "detached"
        await self._expect_impl(
            ("to.be.attached" if attached else "to.be.detached"),
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {attached_string}",
        )

    async def to_be_checked(
        self,
        timeout: float = None,
        checked: bool = None,
        indeterminate: bool = None,
    ) -> None:
        __tracebackhide__ = True
        expected_value = {}
        if indeterminate is not None:
            expected_value["indeterminate"] = indeterminate
        if checked is not None:
            expected_value["checked"] = checked
        checked_string: str
        if indeterminate:
            checked_string = "indeterminate"
        else:
            checked_string = "unchecked" if checked is False else "checked"
        await self._expect_impl(
            "to.be.checked",
            FrameExpectOptions(timeout=timeout, expectedValue=expected_value),
            None,
            f"Locator expected to be {checked_string}",
        )

    async def not_to_be_attached(
        self,
        attached: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_attached(attached=attached, timeout=timeout)

    async def not_to_be_checked(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_checked(timeout)

    async def to_be_disabled(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.disabled",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be disabled",
        )

    async def not_to_be_disabled(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_disabled(timeout)

    async def to_be_editable(
        self,
        editable: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if editable is None:
            editable = True
        editable_string = "editable" if editable else "readonly"
        await self._expect_impl(
            "to.be.editable" if editable else "to.be.readonly",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {editable_string}",
        )

    async def not_to_be_editable(
        self,
        editable: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_editable(editable, timeout)

    async def to_be_empty(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.empty",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be empty",
        )

    async def not_to_be_empty(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_empty(timeout)

    async def to_be_enabled(
        self,
        enabled: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if enabled is None:
            enabled = True
        enabled_string = "enabled" if enabled else "disabled"
        await self._expect_impl(
            "to.be.enabled" if enabled else "to.be.disabled",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {enabled_string}",
        )

    async def not_to_be_enabled(
        self,
        enabled: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_enabled(enabled, timeout)

    async def to_be_hidden(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.hidden",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be hidden",
        )

    async def not_to_be_hidden(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_hidden(timeout)

    async def to_be_visible(
        self,
        visible: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        if visible is None:
            visible = True
        visible_string = "visible" if visible else "hidden"
        await self._expect_impl(
            "to.be.visible" if visible else "to.be.hidden",
            FrameExpectOptions(timeout=timeout),
            None,
            f"Locator expected to be {visible_string}",
        )

    async def not_to_be_visible(
        self,
        visible: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_visible(visible, timeout)

    async def to_be_focused(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.focused",
            FrameExpectOptions(timeout=timeout),
            None,
            "Locator expected to be focused",
        )

    async def not_to_be_focused(
        self,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_focused(timeout)

    async def to_be_in_viewport(
        self,
        ratio: float = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.be.in.viewport",
            FrameExpectOptions(timeout=timeout, expectedNumber=ratio),
            None,
            "Locator expected to be in viewport",
        )

    async def not_to_be_in_viewport(
        self, ratio: float = None, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_be_in_viewport(ratio=ratio, timeout=timeout)

    async def to_have_accessible_description(
        self,
        description: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [description], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.description",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible description",
        )

    async def not_to_have_accessible_description(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_description(name, ignoreCase, timeout)

    async def to_have_accessible_name(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [name], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.name",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible name",
        )

    async def not_to_have_accessible_name(
        self,
        name: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_name(name, ignoreCase, timeout)

    async def to_have_role(self, role: AriaRole, timeout: float = None) -> None:
        __tracebackhide__ = True
        if isinstance(role, Pattern):
            raise Error('"role" argument in to_have_role must be a string')
        expected_values = to_expected_text_values([role])
        await self._expect_impl(
            "to.have.role",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible role",
        )

    async def to_have_accessible_error_message(
        self,
        errorMessage: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        expected_values = to_expected_text_values(
            [errorMessage], ignoreCase=ignoreCase, normalize_white_space=True
        )
        await self._expect_impl(
            "to.have.accessible.error.message",
            FrameExpectOptions(expectedText=expected_values, timeout=timeout),
            None,
            "Locator expected to have accessible error message",
        )

    async def not_to_have_accessible_error_message(
        self,
        errorMessage: Union[str, Pattern[str]],
        ignoreCase: bool = None,
        timeout: float = None,
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_have_accessible_error_message(
            errorMessage=errorMessage, ignoreCase=ignoreCase, timeout=timeout
        )

    async def not_to_have_role(self, role: AriaRole, timeout: float = None) -> None:
        __tracebackhide__ = True
        await self._not.to_have_role(role, timeout)

    async def to_match_aria_snapshot(
        self, expected: str, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._expect_impl(
            "to.match.aria",
            FrameExpectOptions(expectedValue=expected, timeout=timeout),
            expected,
            "Locator expected to match Aria snapshot",
        )

    async def not_to_match_aria_snapshot(
        self, expected: str, timeout: float = None
    ) -> None:
        __tracebackhide__ = True
        await self._not.to_match_aria_snapshot(expected, timeout)


class APIResponseAssertions:
    def __init__(
        self,
        response: APIResponse,
        timeout: float = None,
        is_not: bool = False,
        message: Optional[str] = None,
    ) -> None:
        self._loop = response._loop
        self._dispatcher_fiber = response._dispatcher_fiber
        self._timeout = timeout
        self._is_not = is_not
        self._actual = response
        self._custom_message = message

    @property
    def _not(self) -> "APIResponseAssertions":
        return APIResponseAssertions(
            self._actual, self._timeout, not self._is_not, self._custom_message
        )

    async def to_be_ok(
        self,
    ) -> None:
        __tracebackhide__ = True
        if self._is_not is not self._actual.ok:
            return
        message = f"Response status expected to be within [200..299] range, was '{self._actual.status}'"
        if self._is_not:
            message = message.replace("expected to", "expected not to")
        out_message = self._custom_message or message
        out_message += format_call_log(await self._actual._fetch_log())

        content_type = self._actual.headers.get("content-type")
        is_text_encoding = content_type and is_textual_mime_type(content_type)
        text = await self._actual.text() if is_text_encoding else None
        if text is not None:
            out_message += f"\n Response Text:\n{text[:1000]}"

        raise AssertionError(out_message)

    async def not_to_be_ok(self) -> None:
        __tracebackhide__ = True
        await self._not.to_be_ok()


def expected_regex(
    pattern: Pattern[str],
    match_substring: bool,
    normalize_white_space: bool,
    ignoreCase: Optional[bool] = None,
) -> ExpectedTextValue:
    expected = ExpectedTextValue(
        regexSource=pattern.pattern,
        regexFlags=escape_regex_flags(pattern),
        matchSubstring=match_substring,
        normalizeWhiteSpace=normalize_white_space,
        ignoreCase=ignoreCase,
    )
    if expected["ignoreCase"] is None:
        del expected["ignoreCase"]
    return expected


def to_expected_text_values(
    items: Union[
        Sequence[Pattern[str]], Sequence[str], Sequence[Union[str, Pattern[str]]]
    ],
    match_substring: bool = False,
    normalize_white_space: bool = False,
    ignoreCase: Optional[bool] = None,
) -> Sequence[ExpectedTextValue]:
    out: List[ExpectedTextValue] = []
    assert isinstance(items, (list, tuple))
    for item in items:
        if isinstance(item, str):
            o = ExpectedTextValue(
                string=item,
                matchSubstring=match_substring,
                normalizeWhiteSpace=normalize_white_space,
                ignoreCase=ignoreCase,
            )
            if o["ignoreCase"] is None:
                del o["ignoreCase"]
            out.append(o)
        elif isinstance(item, Pattern):
            out.append(
                expected_regex(item, match_substring, normalize_white_space, ignoreCase)
            )
        else:
            raise Error("value must be a string or regular expression")
    return out

# === NexusCore/openenv\Lib\site-packages\blessed\colorspace.py ===
"""
Color reference data.

References,

- https://github.com/freedesktop/xorg-rgb/blob/master/rgb.txt
- https://github.com/ThomasDickey/xterm-snapshots/blob/master/256colres.h
- https://github.com/ThomasDickey/xterm-snapshots/blob/master/XTerm-col.ad
- https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
- https://gist.github.com/XVilka/8346728
- https://devblogs.microsoft.com/commandline/24-bit-color-in-the-windows-console/
- http://jdebp.uk/Softwares/nosh/guide/TerminalCapabilities.html
"""

# std imports
import collections

__all__ = (
    'CGA_COLORS',
    'RGBColor',
    'RGB_256TABLE',
    'X11_COLORNAMES_TO_RGB',
)

CGA_COLORS = {'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'}


class RGBColor(collections.namedtuple("RGBColor", ["red", "green", "blue"])):
    """Named tuple for an RGB color definition."""

    def __str__(self):
        return '#{0:02x}{1:02x}{2:02x}'.format(*self)


#: X11 Color names to (XTerm-defined) RGB values from xorg-rgb/rgb.txt
X11_COLORNAMES_TO_RGB = {
    'aliceblue': RGBColor(240, 248, 255),
    'antiquewhite': RGBColor(250, 235, 215),
    'antiquewhite1': RGBColor(255, 239, 219),
    'antiquewhite2': RGBColor(238, 223, 204),
    'antiquewhite3': RGBColor(205, 192, 176),
    'antiquewhite4': RGBColor(139, 131, 120),
    'aqua': RGBColor(0, 255, 255),
    'aquamarine': RGBColor(127, 255, 212),
    'aquamarine1': RGBColor(127, 255, 212),
    'aquamarine2': RGBColor(118, 238, 198),
    'aquamarine3': RGBColor(102, 205, 170),
    'aquamarine4': RGBColor(69, 139, 116),
    'azure': RGBColor(240, 255, 255),
    'azure1': RGBColor(240, 255, 255),
    'azure2': RGBColor(224, 238, 238),
    'azure3': RGBColor(193, 205, 205),
    'azure4': RGBColor(131, 139, 139),
    'beige': RGBColor(245, 245, 220),
    'bisque': RGBColor(255, 228, 196),
    'bisque1': RGBColor(255, 228, 196),
    'bisque2': RGBColor(238, 213, 183),
    'bisque3': RGBColor(205, 183, 158),
    'bisque4': RGBColor(139, 125, 107),
    'black': RGBColor(0, 0, 0),
    'blanchedalmond': RGBColor(255, 235, 205),
    'blue': RGBColor(0, 0, 255),
    'blue1': RGBColor(0, 0, 255),
    'blue2': RGBColor(0, 0, 238),
    'blue3': RGBColor(0, 0, 205),
    'blue4': RGBColor(0, 0, 139),
    'blueviolet': RGBColor(138, 43, 226),
    'brown': RGBColor(165, 42, 42),
    'brown1': RGBColor(255, 64, 64),
    'brown2': RGBColor(238, 59, 59),
    'brown3': RGBColor(205, 51, 51),
    'brown4': RGBColor(139, 35, 35),
    'burlywood': RGBColor(222, 184, 135),
    'burlywood1': RGBColor(255, 211, 155),
    'burlywood2': RGBColor(238, 197, 145),
    'burlywood3': RGBColor(205, 170, 125),
    'burlywood4': RGBColor(139, 115, 85),
    'cadetblue': RGBColor(95, 158, 160),
    'cadetblue1': RGBColor(152, 245, 255),
    'cadetblue2': RGBColor(142, 229, 238),
    'cadetblue3': RGBColor(122, 197, 205),
    'cadetblue4': RGBColor(83, 134, 139),
    'chartreuse': RGBColor(127, 255, 0),
    'chartreuse1': RGBColor(127, 255, 0),
    'chartreuse2': RGBColor(118, 238, 0),
    'chartreuse3': RGBColor(102, 205, 0),
    'chartreuse4': RGBColor(69, 139, 0),
    'chocolate': RGBColor(210, 105, 30),
    'chocolate1': RGBColor(255, 127, 36),
    'chocolate2': RGBColor(238, 118, 33),
    'chocolate3': RGBColor(205, 102, 29),
    'chocolate4': RGBColor(139, 69, 19),
    'coral': RGBColor(255, 127, 80),
    'coral1': RGBColor(255, 114, 86),
    'coral2': RGBColor(238, 106, 80),
    'coral3': RGBColor(205, 91, 69),
    'coral4': RGBColor(139, 62, 47),
    'cornflowerblue': RGBColor(100, 149, 237),
    'cornsilk': RGBColor(255, 248, 220),
    'cornsilk1': RGBColor(255, 248, 220),
    'cornsilk2': RGBColor(238, 232, 205),
    'cornsilk3': RGBColor(205, 200, 177),
    'cornsilk4': RGBColor(139, 136, 120),
    'crimson': RGBColor(220, 20, 60),
    'cyan': RGBColor(0, 255, 255),
    'cyan1': RGBColor(0, 255, 255),
    'cyan2': RGBColor(0, 238, 238),
    'cyan3': RGBColor(0, 205, 205),
    'cyan4': RGBColor(0, 139, 139),
    'darkblue': RGBColor(0, 0, 139),
    'darkcyan': RGBColor(0, 139, 139),
    'darkgoldenrod': RGBColor(184, 134, 11),
    'darkgoldenrod1': RGBColor(255, 185, 15),
    'darkgoldenrod2': RGBColor(238, 173, 14),
    'darkgoldenrod3': RGBColor(205, 149, 12),
    'darkgoldenrod4': RGBColor(139, 101, 8),
    'darkgray': RGBColor(169, 169, 169),
    'darkgreen': RGBColor(0, 100, 0),
    'darkgrey': RGBColor(169, 169, 169),
    'darkkhaki': RGBColor(189, 183, 107),
    'darkmagenta': RGBColor(139, 0, 139),
    'darkolivegreen': RGBColor(85, 107, 47),
    'darkolivegreen1': RGBColor(202, 255, 112),
    'darkolivegreen2': RGBColor(188, 238, 104),
    'darkolivegreen3': RGBColor(162, 205, 90),
    'darkolivegreen4': RGBColor(110, 139, 61),
    'darkorange': RGBColor(255, 140, 0),
    'darkorange1': RGBColor(255, 127, 0),
    'darkorange2': RGBColor(238, 118, 0),
    'darkorange3': RGBColor(205, 102, 0),
    'darkorange4': RGBColor(139, 69, 0),
    'darkorchid': RGBColor(153, 50, 204),
    'darkorchid1': RGBColor(191, 62, 255),
    'darkorchid2': RGBColor(178, 58, 238),
    'darkorchid3': RGBColor(154, 50, 205),
    'darkorchid4': RGBColor(104, 34, 139),
    'darkred': RGBColor(139, 0, 0),
    'darksalmon': RGBColor(233, 150, 122),
    'darkseagreen': RGBColor(143, 188, 143),
    'darkseagreen1': RGBColor(193, 255, 193),
    'darkseagreen2': RGBColor(180, 238, 180),
    'darkseagreen3': RGBColor(155, 205, 155),
    'darkseagreen4': RGBColor(105, 139, 105),
    'darkslateblue': RGBColor(72, 61, 139),
    'darkslategray': RGBColor(47, 79, 79),
    'darkslategray1': RGBColor(151, 255, 255),
    'darkslategray2': RGBColor(141, 238, 238),
    'darkslategray3': RGBColor(121, 205, 205),
    'darkslategray4': RGBColor(82, 139, 139),
    'darkslategrey': RGBColor(47, 79, 79),
    'darkturquoise': RGBColor(0, 206, 209),
    'darkviolet': RGBColor(148, 0, 211),
    'deeppink': RGBColor(255, 20, 147),
    'deeppink1': RGBColor(255, 20, 147),
    'deeppink2': RGBColor(238, 18, 137),
    'deeppink3': RGBColor(205, 16, 118),
    'deeppink4': RGBColor(139, 10, 80),
    'deepskyblue': RGBColor(0, 191, 255),
    'deepskyblue1': RGBColor(0, 191, 255),
    'deepskyblue2': RGBColor(0, 178, 238),
    'deepskyblue3': RGBColor(0, 154, 205),
    'deepskyblue4': RGBColor(0, 104, 139),
    'dimgray': RGBColor(105, 105, 105),
    'dimgrey': RGBColor(105, 105, 105),
    'dodgerblue': RGBColor(30, 144, 255),
    'dodgerblue1': RGBColor(30, 144, 255),
    'dodgerblue2': RGBColor(28, 134, 238),
    'dodgerblue3': RGBColor(24, 116, 205),
    'dodgerblue4': RGBColor(16, 78, 139),
    'firebrick': RGBColor(178, 34, 34),
    'firebrick1': RGBColor(255, 48, 48),
    'firebrick2': RGBColor(238, 44, 44),
    'firebrick3': RGBColor(205, 38, 38),
    'firebrick4': RGBColor(139, 26, 26),
    'floralwhite': RGBColor(255, 250, 240),
    'forestgreen': RGBColor(34, 139, 34),
    'fuchsia': RGBColor(255, 0, 255),
    'gainsboro': RGBColor(220, 220, 220),
    'ghostwhite': RGBColor(248, 248, 255),
    'gold': RGBColor(255, 215, 0),
    'gold1': RGBColor(255, 215, 0),
    'gold2': RGBColor(238, 201, 0),
    'gold3': RGBColor(205, 173, 0),
    'gold4': RGBColor(139, 117, 0),
    'goldenrod': RGBColor(218, 165, 32),
    'goldenrod1': RGBColor(255, 193, 37),
    'goldenrod2': RGBColor(238, 180, 34),
    'goldenrod3': RGBColor(205, 155, 29),
    'goldenrod4': RGBColor(139, 105, 20),
    'gray': RGBColor(190, 190, 190),
    'gray0': RGBColor(0, 0, 0),
    'gray1': RGBColor(3, 3, 3),
    'gray10': RGBColor(26, 26, 26),
    'gray100': RGBColor(255, 255, 255),
    'gray11': RGBColor(28, 28, 28),
    'gray12': RGBColor(31, 31, 31),
    'gray13': RGBColor(33, 33, 33),
    'gray14': RGBColor(36, 36, 36),
    'gray15': RGBColor(38, 38, 38),
    'gray16': RGBColor(41, 41, 41),
    'gray17': RGBColor(43, 43, 43),
    'gray18': RGBColor(46, 46, 46),
    'gray19': RGBColor(48, 48, 48),
    'gray2': RGBColor(5, 5, 5),
    'gray20': RGBColor(51, 51, 51),
    'gray21': RGBColor(54, 54, 54),
    'gray22': RGBColor(56, 56, 56),
    'gray23': RGBColor(59, 59, 59),
    'gray24': RGBColor(61, 61, 61),
    'gray25': RGBColor(64, 64, 64),
    'gray26': RGBColor(66, 66, 66),
    'gray27': RGBColor(69, 69, 69),
    'gray28': RGBColor(71, 71, 71),
    'gray29': RGBColor(74, 74, 74),
    'gray3': RGBColor(8, 8, 8),
    'gray30': RGBColor(77, 77, 77),
    'gray31': RGBColor(79, 79, 79),
    'gray32': RGBColor(82, 82, 82),
    'gray33': RGBColor(84, 84, 84),
    'gray34': RGBColor(87, 87, 87),
    'gray35': RGBColor(89, 89, 89),
    'gray36': RGBColor(92, 92, 92),
    'gray37': RGBColor(94, 94, 94),
    'gray38': RGBColor(97, 97, 97),
    'gray39': RGBColor(99, 99, 99),
    'gray4': RGBColor(10, 10, 10),
    'gray40': RGBColor(102, 102, 102),
    'gray41': RGBColor(105, 105, 105),
    'gray42': RGBColor(107, 107, 107),
    'gray43': RGBColor(110, 110, 110),
    'gray44': RGBColor(112, 112, 112),
    'gray45': RGBColor(115, 115, 115),
    'gray46': RGBColor(117, 117, 117),
    'gray47': RGBColor(120, 120, 120),
    'gray48': RGBColor(122, 122, 122),
    'gray49': RGBColor(125, 125, 125),
    'gray5': RGBColor(13, 13, 13),
    'gray50': RGBColor(127, 127, 127),
    'gray51': RGBColor(130, 130, 130),
    'gray52': RGBColor(133, 133, 133),
    'gray53': RGBColor(135, 135, 135),
    'gray54': RGBColor(138, 138, 138),
    'gray55': RGBColor(140, 140, 140),
    'gray56': RGBColor(143, 143, 143),
    'gray57': RGBColor(145, 145, 145),
    'gray58': RGBColor(148, 148, 148),
    'gray59': RGBColor(150, 150, 150),
    'gray6': RGBColor(15, 15, 15),
    'gray60': RGBColor(153, 153, 153),
    'gray61': RGBColor(156, 156, 156),
    'gray62': RGBColor(158, 158, 158),
    'gray63': RGBColor(161, 161, 161),
    'gray64': RGBColor(163, 163, 163),
    'gray65': RGBColor(166, 166, 166),
    'gray66': RGBColor(168, 168, 168),
    'gray67': RGBColor(171, 171, 171),
    'gray68': RGBColor(173, 173, 173),
    'gray69': RGBColor(176, 176, 176),
    'gray7': RGBColor(18, 18, 18),
    'gray70': RGBColor(179, 179, 179),
    'gray71': RGBColor(181, 181, 181),
    'gray72': RGBColor(184, 184, 184),
    'gray73': RGBColor(186, 186, 186),
    'gray74': RGBColor(189, 189, 189),
    'gray75': RGBColor(191, 191, 191),
    'gray76': RGBColor(194, 194, 194),
    'gray77': RGBColor(196, 196, 196),
    'gray78': RGBColor(199, 199, 199),
    'gray79': RGBColor(201, 201, 201),
    'gray8': RGBColor(20, 20, 20),
    'gray80': RGBColor(204, 204, 204),
    'gray81': RGBColor(207, 207, 207),
    'gray82': RGBColor(209, 209, 209),
    'gray83': RGBColor(212, 212, 212),
    'gray84': RGBColor(214, 214, 214),
    'gray85': RGBColor(217, 217, 217),
    'gray86': RGBColor(219, 219, 219),
    'gray87': RGBColor(222, 222, 222),
    'gray88': RGBColor(224, 224, 224),
    'gray89': RGBColor(227, 227, 227),
    'gray9': RGBColor(23, 23, 23),
    'gray90': RGBColor(229, 229, 229),
    'gray91': RGBColor(232, 232, 232),
    'gray92': RGBColor(235, 235, 235),
    'gray93': RGBColor(237, 237, 237),
    'gray94': RGBColor(240, 240, 240),
    'gray95': RGBColor(242, 242, 242),
    'gray96': RGBColor(245, 245, 245),
    'gray97': RGBColor(247, 247, 247),
    'gray98': RGBColor(250, 250, 250),
    'gray99': RGBColor(252, 252, 252),
    'green': RGBColor(0, 255, 0),
    'green1': RGBColor(0, 255, 0),
    'green2': RGBColor(0, 238, 0),
    'green3': RGBColor(0, 205, 0),
    'green4': RGBColor(0, 139, 0),
    'greenyellow': RGBColor(173, 255, 47),
    'grey': RGBColor(190, 190, 190),
    'grey0': RGBColor(0, 0, 0),
    'grey1': RGBColor(3, 3, 3),
    'grey10': RGBColor(26, 26, 26),
    'grey100': RGBColor(255, 255, 255),
    'grey11': RGBColor(28, 28, 28),
    'grey12': RGBColor(31, 31, 31),
    'grey13': RGBColor(33, 33, 33),
    'grey14': RGBColor(36, 36, 36),
    'grey15': RGBColor(38, 38, 38),
    'grey16': RGBColor(41, 41, 41),
    'grey17': RGBColor(43, 43, 43),
    'grey18': RGBColor(46, 46, 46),
    'grey19': RGBColor(48, 48, 48),
    'grey2': RGBColor(5, 5, 5),
    'grey20': RGBColor(51, 51, 51),
    'grey21': RGBColor(54, 54, 54),
    'grey22': RGBColor(56, 56, 56),
    'grey23': RGBColor(59, 59, 59),
    'grey24': RGBColor(61, 61, 61),
    'grey25': RGBColor(64, 64, 64),
    'grey26': RGBColor(66, 66, 66),
    'grey27': RGBColor(69, 69, 69),
    'grey28': RGBColor(71, 71, 71),
    'grey29': RGBColor(74, 74, 74),
    'grey3': RGBColor(8, 8, 8),
    'grey30': RGBColor(77, 77, 77),
    'grey31': RGBColor(79, 79, 79),
    'grey32': RGBColor(82, 82, 82),
    'grey33': RGBColor(84, 84, 84),
    'grey34': RGBColor(87, 87, 87),
    'grey35': RGBColor(89, 89, 89),
    'grey36': RGBColor(92, 92, 92),
    'grey37': RGBColor(94, 94, 94),
    'grey38': RGBColor(97, 97, 97),
    'grey39': RGBColor(99, 99, 99),
    'grey4': RGBColor(10, 10, 10),
    'grey40': RGBColor(102, 102, 102),
    'grey41': RGBColor(105, 105, 105),
    'grey42': RGBColor(107, 107, 107),
    'grey43': RGBColor(110, 110, 110),
    'grey44': RGBColor(112, 112, 112),
    'grey45': RGBColor(115, 115, 115),
    'grey46': RGBColor(117, 117, 117),
    'grey47': RGBColor(120, 120, 120),
    'grey48': RGBColor(122, 122, 122),
    'grey49': RGBColor(125, 125, 125),
    'grey5': RGBColor(13, 13, 13),
    'grey50': RGBColor(127, 127, 127),
    'grey51': RGBColor(130, 130, 130),
    'grey52': RGBColor(133, 133, 133),
    'grey53': RGBColor(135, 135, 135),
    'grey54': RGBColor(138, 138, 138),
    'grey55': RGBColor(140, 140, 140),
    'grey56': RGBColor(143, 143, 143),
    'grey57': RGBColor(145, 145, 145),
    'grey58': RGBColor(148, 148, 148),
    'grey59': RGBColor(150, 150, 150),
    'grey6': RGBColor(15, 15, 15),
    'grey60': RGBColor(153, 153, 153),
    'grey61': RGBColor(156, 156, 156),
    'grey62': RGBColor(158, 158, 158),
    'grey63': RGBColor(161, 161, 161),
    'grey64': RGBColor(163, 163, 163),
    'grey65': RGBColor(166, 166, 166),
    'grey66': RGBColor(168, 168, 168),
    'grey67': RGBColor(171, 171, 171),
    'grey68': RGBColor(173, 173, 173),
    'grey69': RGBColor(176, 176, 176),
    'grey7': RGBColor(18, 18, 18),
    'grey70': RGBColor(179, 179, 179),
    'grey71': RGBColor(181, 181, 181),
    'grey72': RGBColor(184, 184, 184),
    'grey73': RGBColor(186, 186, 186),
    'grey74': RGBColor(189, 189, 189),
    'grey75': RGBColor(191, 191, 191),
    'grey76': RGBColor(194, 194, 194),
    'grey77': RGBColor(196, 196, 196),
    'grey78': RGBColor(199, 199, 199),
    'grey79': RGBColor(201, 201, 201),
    'grey8': RGBColor(20, 20, 20),
    'grey80': RGBColor(204, 204, 204),
    'grey81': RGBColor(207, 207, 207),
    'grey82': RGBColor(209, 209, 209),
    'grey83': RGBColor(212, 212, 212),
    'grey84': RGBColor(214, 214, 214),
    'grey85': RGBColor(217, 217, 217),
    'grey86': RGBColor(219, 219, 219),
    'grey87': RGBColor(222, 222, 222),
    'grey88': RGBColor(224, 224, 224),
    'grey89': RGBColor(227, 227, 227),
    'grey9': RGBColor(23, 23, 23),
    'grey90': RGBColor(229, 229, 229),
    'grey91': RGBColor(232, 232, 232),
    'grey92': RGBColor(235, 235, 235),
    'grey93': RGBColor(237, 237, 237),
    'grey94': RGBColor(240, 240, 240),
    'grey95': RGBColor(242, 242, 242),
    'grey96': RGBColor(245, 245, 245),
    'grey97': RGBColor(247, 247, 247),
    'grey98': RGBColor(250, 250, 250),
    'grey99': RGBColor(252, 252, 252),
    'honeydew': RGBColor(240, 255, 240),
    'honeydew1': RGBColor(240, 255, 240),
    'honeydew2': RGBColor(224, 238, 224),
    'honeydew3': RGBColor(193, 205, 193),
    'honeydew4': RGBColor(131, 139, 131),
    'hotpink': RGBColor(255, 105, 180),
    'hotpink1': RGBColor(255, 110, 180),
    'hotpink2': RGBColor(238, 106, 167),
    'hotpink3': RGBColor(205, 96, 144),
    'hotpink4': RGBColor(139, 58, 98),
    'indianred': RGBColor(205, 92, 92),
    'indianred1': RGBColor(255, 106, 106),
    'indianred2': RGBColor(238, 99, 99),
    'indianred3': RGBColor(205, 85, 85),
    'indianred4': RGBColor(139, 58, 58),
    'indigo': RGBColor(75, 0, 130),
    'ivory': RGBColor(255, 255, 240),
    'ivory1': RGBColor(255, 255, 240),
    'ivory2': RGBColor(238, 238, 224),
    'ivory3': RGBColor(205, 205, 193),
    'ivory4': RGBColor(139, 139, 131),
    'khaki': RGBColor(240, 230, 140),
    'khaki1': RGBColor(255, 246, 143),
    'khaki2': RGBColor(238, 230, 133),
    'khaki3': RGBColor(205, 198, 115),
    'khaki4': RGBColor(139, 134, 78),
    'lavender': RGBColor(230, 230, 250),
    'lavenderblush': RGBColor(255, 240, 245),
    'lavenderblush1': RGBColor(255, 240, 245),
    'lavenderblush2': RGBColor(238, 224, 229),
    'lavenderblush3': RGBColor(205, 193, 197),
    'lavenderblush4': RGBColor(139, 131, 134),
    'lawngreen': RGBColor(124, 252, 0),
    'lemonchiffon': RGBColor(255, 250, 205),
    'lemonchiffon1': RGBColor(255, 250, 205),
    'lemonchiffon2': RGBColor(238, 233, 191),
    'lemonchiffon3': RGBColor(205, 201, 165),
    'lemonchiffon4': RGBColor(139, 137, 112),
    'lightblue': RGBColor(173, 216, 230),
    'lightblue1': RGBColor(191, 239, 255),
    'lightblue2': RGBColor(178, 223, 238),
    'lightblue3': RGBColor(154, 192, 205),
    'lightblue4': RGBColor(104, 131, 139),
    'lightcoral': RGBColor(240, 128, 128),
    'lightcyan': RGBColor(224, 255, 255),
    'lightcyan1': RGBColor(224, 255, 255),
    'lightcyan2': RGBColor(209, 238, 238),
    'lightcyan3': RGBColor(180, 205, 205),
    'lightcyan4': RGBColor(122, 139, 139),
    'lightgoldenrod': RGBColor(238, 221, 130),
    'lightgoldenrod1': RGBColor(255, 236, 139),
    'lightgoldenrod2': RGBColor(238, 220, 130),
    'lightgoldenrod3': RGBColor(205, 190, 112),
    'lightgoldenrod4': RGBColor(139, 129, 76),
    'lightgoldenrodyellow': RGBColor(250, 250, 210),
    'lightgray': RGBColor(211, 211, 211),
    'lightgreen': RGBColor(144, 238, 144),
    'lightgrey': RGBColor(211, 211, 211),
    'lightpink': RGBColor(255, 182, 193),
    'lightpink1': RGBColor(255, 174, 185),
    'lightpink2': RGBColor(238, 162, 173),
    'lightpink3': RGBColor(205, 140, 149),
    'lightpink4': RGBColor(139, 95, 101),
    'lightsalmon': RGBColor(255, 160, 122),
    'lightsalmon1': RGBColor(255, 160, 122),
    'lightsalmon2': RGBColor(238, 149, 114),
    'lightsalmon3': RGBColor(205, 129, 98),
    'lightsalmon4': RGBColor(139, 87, 66),
    'lightseagreen': RGBColor(32, 178, 170),
    'lightskyblue': RGBColor(135, 206, 250),
    'lightskyblue1': RGBColor(176, 226, 255),
    'lightskyblue2': RGBColor(164, 211, 238),
    'lightskyblue3': RGBColor(141, 182, 205),
    'lightskyblue4': RGBColor(96, 123, 139),
    'lightslateblue': RGBColor(132, 112, 255),
    'lightslategray': RGBColor(119, 136, 153),
    'lightslategrey': RGBColor(119, 136, 153),
    'lightsteelblue': RGBColor(176, 196, 222),
    'lightsteelblue1': RGBColor(202, 225, 255),
    'lightsteelblue2': RGBColor(188, 210, 238),
    'lightsteelblue3': RGBColor(162, 181, 205),
    'lightsteelblue4': RGBColor(110, 123, 139),
    'lightyellow': RGBColor(255, 255, 224),
    'lightyellow1': RGBColor(255, 255, 224),
    'lightyellow2': RGBColor(238, 238, 209),
    'lightyellow3': RGBColor(205, 205, 180),
    'lightyellow4': RGBColor(139, 139, 122),
    'lime': RGBColor(0, 255, 0),
    'limegreen': RGBColor(50, 205, 50),
    'linen': RGBColor(250, 240, 230),
    'magenta': RGBColor(255, 0, 255),
    'magenta1': RGBColor(255, 0, 255),
    'magenta2': RGBColor(238, 0, 238),
    'magenta3': RGBColor(205, 0, 205),
    'magenta4': RGBColor(139, 0, 139),
    'maroon': RGBColor(176, 48, 96),
    'maroon1': RGBColor(255, 52, 179),
    'maroon2': RGBColor(238, 48, 167),
    'maroon3': RGBColor(205, 41, 144),
    'maroon4': RGBColor(139, 28, 98),
    'mediumaquamarine': RGBColor(102, 205, 170),
    'mediumblue': RGBColor(0, 0, 205),
    'mediumorchid': RGBColor(186, 85, 211),
    'mediumorchid1': RGBColor(224, 102, 255),
    'mediumorchid2': RGBColor(209, 95, 238),
    'mediumorchid3': RGBColor(180, 82, 205),
    'mediumorchid4': RGBColor(122, 55, 139),
    'mediumpurple': RGBColor(147, 112, 219),
    'mediumpurple1': RGBColor(171, 130, 255),
    'mediumpurple2': RGBColor(159, 121, 238),
    'mediumpurple3': RGBColor(137, 104, 205),
    'mediumpurple4': RGBColor(93, 71, 139),
    'mediumseagreen': RGBColor(60, 179, 113),
    'mediumslateblue': RGBColor(123, 104, 238),
    'mediumspringgreen': RGBColor(0, 250, 154),
    'mediumturquoise': RGBColor(72, 209, 204),
    'mediumvioletred': RGBColor(199, 21, 133),
    'midnightblue': RGBColor(25, 25, 112),
    'mintcream': RGBColor(245, 255, 250),
    'mistyrose': RGBColor(255, 228, 225),
    'mistyrose1': RGBColor(255, 228, 225),
    'mistyrose2': RGBColor(238, 213, 210),
    'mistyrose3': RGBColor(205, 183, 181),
    'mistyrose4': RGBColor(139, 125, 123),
    'moccasin': RGBColor(255, 228, 181),
    'navajowhite': RGBColor(255, 222, 173),
    'navajowhite1': RGBColor(255, 222, 173),
    'navajowhite2': RGBColor(238, 207, 161),
    'navajowhite3': RGBColor(205, 179, 139),
    'navajowhite4': RGBColor(139, 121, 94),
    'navy': RGBColor(0, 0, 128),
    'navyblue': RGBColor(0, 0, 128),
    'oldlace': RGBColor(253, 245, 230),
    'olive': RGBColor(128, 128, 0),
    'olivedrab': RGBColor(107, 142, 35),
    'olivedrab1': RGBColor(192, 255, 62),
    'olivedrab2': RGBColor(179, 238, 58),
    'olivedrab3': RGBColor(154, 205, 50),
    'olivedrab4': RGBColor(105, 139, 34),
    'orange': RGBColor(255, 165, 0),
    'orange1': RGBColor(255, 165, 0),
    'orange2': RGBColor(238, 154, 0),
    'orange3': RGBColor(205, 133, 0),
    'orange4': RGBColor(139, 90, 0),
    'orangered': RGBColor(255, 69, 0),
    'orangered1': RGBColor(255, 69, 0),
    'orangered2': RGBColor(238, 64, 0),
    'orangered3': RGBColor(205, 55, 0),
    'orangered4': RGBColor(139, 37, 0),
    'orchid': RGBColor(218, 112, 214),
    'orchid1': RGBColor(255, 131, 250),
    'orchid2': RGBColor(238, 122, 233),
    'orchid3': RGBColor(205, 105, 201),
    'orchid4': RGBColor(139, 71, 137),
    'palegoldenrod': RGBColor(238, 232, 170),
    'palegreen': RGBColor(152, 251, 152),
    'palegreen1': RGBColor(154, 255, 154),
    'palegreen2': RGBColor(144, 238, 144),
    'palegreen3': RGBColor(124, 205, 124),
    'palegreen4': RGBColor(84, 139, 84),
    'paleturquoise': RGBColor(175, 238, 238),
    'paleturquoise1': RGBColor(187, 255, 255),
    'paleturquoise2': RGBColor(174, 238, 238),
    'paleturquoise3': RGBColor(150, 205, 205),
    'paleturquoise4': RGBColor(102, 139, 139),
    'palevioletred': RGBColor(219, 112, 147),
    'palevioletred1': RGBColor(255, 130, 171),
    'palevioletred2': RGBColor(238, 121, 159),
    'palevioletred3': RGBColor(205, 104, 137),
    'palevioletred4': RGBColor(139, 71, 93),
    'papayawhip': RGBColor(255, 239, 213),
    'peachpuff': RGBColor(255, 218, 185),
    'peachpuff1': RGBColor(255, 218, 185),
    'peachpuff2': RGBColor(238, 203, 173),
    'peachpuff3': RGBColor(205, 175, 149),
    'peachpuff4': RGBColor(139, 119, 101),
    'peru': RGBColor(205, 133, 63),
    'pink': RGBColor(255, 192, 203),
    'pink1': RGBColor(255, 181, 197),
    'pink2': RGBColor(238, 169, 184),
    'pink3': RGBColor(205, 145, 158),
    'pink4': RGBColor(139, 99, 108),
    'plum': RGBColor(221, 160, 221),
    'plum1': RGBColor(255, 187, 255),
    'plum2': RGBColor(238, 174, 238),
    'plum3': RGBColor(205, 150, 205),
    'plum4': RGBColor(139, 102, 139),
    'powderblue': RGBColor(176, 224, 230),
    'purple': RGBColor(160, 32, 240),
    'purple1': RGBColor(155, 48, 255),
    'purple2': RGBColor(145, 44, 238),
    'purple3': RGBColor(125, 38, 205),
    'purple4': RGBColor(85, 26, 139),
    'rebeccapurple': RGBColor(102, 51, 153),
    'red': RGBColor(255, 0, 0),
    'red1': RGBColor(255, 0, 0),
    'red2': RGBColor(238, 0, 0),
    'red3': RGBColor(205, 0, 0),
    'red4': RGBColor(139, 0, 0),
    'rosybrown': RGBColor(188, 143, 143),
    'rosybrown1': RGBColor(255, 193, 193),
    'rosybrown2': RGBColor(238, 180, 180),
    'rosybrown3': RGBColor(205, 155, 155),
    'rosybrown4': RGBColor(139, 105, 105),
    'royalblue': RGBColor(65, 105, 225),
    'royalblue1': RGBColor(72, 118, 255),
    'royalblue2': RGBColor(67, 110, 238),
    'royalblue3': RGBColor(58, 95, 205),
    'royalblue4': RGBColor(39, 64, 139),
    'saddlebrown': RGBColor(139, 69, 19),
    'salmon': RGBColor(250, 128, 114),
    'salmon1': RGBColor(255, 140, 105),
    'salmon2': RGBColor(238, 130, 98),
    'salmon3': RGBColor(205, 112, 84),
    'salmon4': RGBColor(139, 76, 57),
    'sandybrown': RGBColor(244, 164, 96),
    'seagreen': RGBColor(46, 139, 87),
    'seagreen1': RGBColor(84, 255, 159),
    'seagreen2': RGBColor(78, 238, 148),
    'seagreen3': RGBColor(67, 205, 128),
    'seagreen4': RGBColor(46, 139, 87),
    'seashell': RGBColor(255, 245, 238),
    'seashell1': RGBColor(255, 245, 238),
    'seashell2': RGBColor(238, 229, 222),
    'seashell3': RGBColor(205, 197, 191),
    'seashell4': RGBColor(139, 134, 130),
    'sienna': RGBColor(160, 82, 45),
    'sienna1': RGBColor(255, 130, 71),
    'sienna2': RGBColor(238, 121, 66),
    'sienna3': RGBColor(205, 104, 57),
    'sienna4': RGBColor(139, 71, 38),
    'silver': RGBColor(192, 192, 192),
    'skyblue': RGBColor(135, 206, 235),
    'skyblue1': RGBColor(135, 206, 255),
    'skyblue2': RGBColor(126, 192, 238),
    'skyblue3': RGBColor(108, 166, 205),
    'skyblue4': RGBColor(74, 112, 139),
    'slateblue': RGBColor(106, 90, 205),
    'slateblue1': RGBColor(131, 111, 255),
    'slateblue2': RGBColor(122, 103, 238),
    'slateblue3': RGBColor(105, 89, 205),
    'slateblue4': RGBColor(71, 60, 139),
    'slategray': RGBColor(112, 128, 144),
    'slategray1': RGBColor(198, 226, 255),
    'slategray2': RGBColor(185, 211, 238),
    'slategray3': RGBColor(159, 182, 205),
    'slategray4': RGBColor(108, 123, 139),
    'slategrey': RGBColor(112, 128, 144),
    'snow': RGBColor(255, 250, 250),
    'snow1': RGBColor(255, 250, 250),
    'snow2': RGBColor(238, 233, 233),
    'snow3': RGBColor(205, 201, 201),
    'snow4': RGBColor(139, 137, 137),
    'springgreen': RGBColor(0, 255, 127),
    'springgreen1': RGBColor(0, 255, 127),
    'springgreen2': RGBColor(0, 238, 118),
    'springgreen3': RGBColor(0, 205, 102),
    'springgreen4': RGBColor(0, 139, 69),
    'steelblue': RGBColor(70, 130, 180),
    'steelblue1': RGBColor(99, 184, 255),
    'steelblue2': RGBColor(92, 172, 238),
    'steelblue3': RGBColor(79, 148, 205),
    'steelblue4': RGBColor(54, 100, 139),
    'tan': RGBColor(210, 180, 140),
    'tan1': RGBColor(255, 165, 79),
    'tan2': RGBColor(238, 154, 73),
    'tan3': RGBColor(205, 133, 63),
    'tan4': RGBColor(139, 90, 43),
    'teal': RGBColor(0, 128, 128),
    'thistle': RGBColor(216, 191, 216),
    'thistle1': RGBColor(255, 225, 255),
    'thistle2': RGBColor(238, 210, 238),
    'thistle3': RGBColor(205, 181, 205),
    'thistle4': RGBColor(139, 123, 139),
    'tomato': RGBColor(255, 99, 71),
    'tomato1': RGBColor(255, 99, 71),
    'tomato2': RGBColor(238, 92, 66),
    'tomato3': RGBColor(205, 79, 57),
    'tomato4': RGBColor(139, 54, 38),
    'turquoise': RGBColor(64, 224, 208),
    'turquoise1': RGBColor(0, 245, 255),
    'turquoise2': RGBColor(0, 229, 238),
    'turquoise3': RGBColor(0, 197, 205),
    'turquoise4': RGBColor(0, 134, 139),
    'violet': RGBColor(238, 130, 238),
    'violetred': RGBColor(208, 32, 144),
    'violetred1': RGBColor(255, 62, 150),
    'violetred2': RGBColor(238, 58, 140),
    'violetred3': RGBColor(205, 50, 120),
    'violetred4': RGBColor(139, 34, 82),
    'webgray': RGBColor(128, 128, 128),
    'webgreen': RGBColor(0, 128, 0),
    'webgrey': RGBColor(128, 128, 128),
    'webmaroon': RGBColor(128, 0, 0),
    'webpurple': RGBColor(128, 0, 128),
    'wheat': RGBColor(245, 222, 179),
    'wheat1': RGBColor(255, 231, 186),
    'wheat2': RGBColor(238, 216, 174),
    'wheat3': RGBColor(205, 186, 150),
    'wheat4': RGBColor(139, 126, 102),
    'white': RGBColor(255, 255, 255),
    'whitesmoke': RGBColor(245, 245, 245),
    'x11gray': RGBColor(190, 190, 190),
    'x11green': RGBColor(0, 255, 0),
    'x11grey': RGBColor(190, 190, 190),
    'x11maroon': RGBColor(176, 48, 96),
    'x11purple': RGBColor(160, 32, 240),
    'yellow': RGBColor(255, 255, 0),
    'yellow1': RGBColor(255, 255, 0),
    'yellow2': RGBColor(238, 238, 0),
    'yellow3': RGBColor(205, 205, 0),
    'yellow4': RGBColor(139, 139, 0),
    'yellowgreen': RGBColor(154, 205, 50)
}

#: Curses color indices of 8, 16, and 256-color terminals
RGB_256TABLE = (
    RGBColor(0, 0, 0),
    RGBColor(205, 0, 0),
    RGBColor(0, 205, 0),
    RGBColor(205, 205, 0),
    RGBColor(0, 0, 238),
    RGBColor(205, 0, 205),
    RGBColor(0, 205, 205),
    RGBColor(229, 229, 229),
    RGBColor(127, 127, 127),
    RGBColor(255, 0, 0),
    RGBColor(0, 255, 0),
    RGBColor(255, 255, 0),
    RGBColor(92, 92, 255),
    RGBColor(255, 0, 255),
    RGBColor(0, 255, 255),
    RGBColor(255, 255, 255),
    RGBColor(0, 0, 0),
    RGBColor(0, 0, 95),
    RGBColor(0, 0, 135),
    RGBColor(0, 0, 175),
    RGBColor(0, 0, 215),
    RGBColor(0, 0, 255),
    RGBColor(0, 95, 0),
    RGBColor(0, 95, 95),
    RGBColor(0, 95, 135),
    RGBColor(0, 95, 175),
    RGBColor(0, 95, 215),
    RGBColor(0, 95, 255),
    RGBColor(0, 135, 0),
    RGBColor(0, 135, 95),
    RGBColor(0, 135, 135),
    RGBColor(0, 135, 175),
    RGBColor(0, 135, 215),
    RGBColor(0, 135, 255),
    RGBColor(0, 175, 0),
    RGBColor(0, 175, 95),
    RGBColor(0, 175, 135),
    RGBColor(0, 175, 175),
    RGBColor(0, 175, 215),
    RGBColor(0, 175, 255),
    RGBColor(0, 215, 0),
    RGBColor(0, 215, 95),
    RGBColor(0, 215, 135),
    RGBColor(0, 215, 175),
    RGBColor(0, 215, 215),
    RGBColor(0, 215, 255),
    RGBColor(0, 255, 0),
    RGBColor(0, 255, 95),
    RGBColor(0, 255, 135),
    RGBColor(0, 255, 175),
    RGBColor(0, 255, 215),
    RGBColor(0, 255, 255),
    RGBColor(95, 0, 0),
    RGBColor(95, 0, 95),
    RGBColor(95, 0, 135),
    RGBColor(95, 0, 175),
    RGBColor(95, 0, 215),
    RGBColor(95, 0, 255),
    RGBColor(95, 95, 0),
    RGBColor(95, 95, 95),
    RGBColor(95, 95, 135),
    RGBColor(95, 95, 175),
    RGBColor(95, 95, 215),
    RGBColor(95, 95, 255),
    RGBColor(95, 135, 0),
    RGBColor(95, 135, 95),
    RGBColor(95, 135, 135),
    RGBColor(95, 135, 175),
    RGBColor(95, 135, 215),
    RGBColor(95, 135, 255),
    RGBColor(95, 175, 0),
    RGBColor(95, 175, 95),
    RGBColor(95, 175, 135),
    RGBColor(95, 175, 175),
    RGBColor(95, 175, 215),
    RGBColor(95, 175, 255),
    RGBColor(95, 215, 0),
    RGBColor(95, 215, 95),
    RGBColor(95, 215, 135),
    RGBColor(95, 215, 175),
    RGBColor(95, 215, 215),
    RGBColor(95, 215, 255),
    RGBColor(95, 255, 0),
    RGBColor(95, 255, 95),
    RGBColor(95, 255, 135),
    RGBColor(95, 255, 175),
    RGBColor(95, 255, 215),
    RGBColor(95, 255, 255),
    RGBColor(135, 0, 0),
    RGBColor(135, 0, 95),
    RGBColor(135, 0, 135),
    RGBColor(135, 0, 175),
    RGBColor(135, 0, 215),
    RGBColor(135, 0, 255),
    RGBColor(135, 95, 0),
    RGBColor(135, 95, 95),
    RGBColor(135, 95, 135),
    RGBColor(135, 95, 175),
    RGBColor(135, 95, 215),
    RGBColor(135, 95, 255),
    RGBColor(135, 135, 0),
    RGBColor(135, 135, 95),
    RGBColor(135, 135, 135),
    RGBColor(135, 135, 175),
    RGBColor(135, 135, 215),
    RGBColor(135, 135, 255),
    RGBColor(135, 175, 0),
    RGBColor(135, 175, 95),
    RGBColor(135, 175, 135),
    RGBColor(135, 175, 175),
    RGBColor(135, 175, 215),
    RGBColor(135, 175, 255),
    RGBColor(135, 215, 0),
    RGBColor(135, 215, 95),
    RGBColor(135, 215, 135),
    RGBColor(135, 215, 175),
    RGBColor(135, 215, 215),
    RGBColor(135, 215, 255),
    RGBColor(135, 255, 0),
    RGBColor(135, 255, 95),
    RGBColor(135, 255, 135),
    RGBColor(135, 255, 175),
    RGBColor(135, 255, 215),
    RGBColor(135, 255, 255),
    RGBColor(175, 0, 0),
    RGBColor(175, 0, 95),
    RGBColor(175, 0, 135),
    RGBColor(175, 0, 175),
    RGBColor(175, 0, 215),
    RGBColor(175, 0, 255),
    RGBColor(175, 95, 0),
    RGBColor(175, 95, 95),
    RGBColor(175, 95, 135),
    RGBColor(175, 95, 175),
    RGBColor(175, 95, 215),
    RGBColor(175, 95, 255),
    RGBColor(175, 135, 0),
    RGBColor(175, 135, 95),
    RGBColor(175, 135, 135),
    RGBColor(175, 135, 175),
    RGBColor(175, 135, 215),
    RGBColor(175, 135, 255),
    RGBColor(175, 175, 0),
    RGBColor(175, 175, 95),
    RGBColor(175, 175, 135),
    RGBColor(175, 175, 175),
    RGBColor(175, 175, 215),
    RGBColor(175, 175, 255),
    RGBColor(175, 215, 0),
    RGBColor(175, 215, 95),
    RGBColor(175, 215, 135),
    RGBColor(175, 215, 175),
    RGBColor(175, 215, 215),
    RGBColor(175, 215, 255),
    RGBColor(175, 255, 0),
    RGBColor(175, 255, 95),
    RGBColor(175, 255, 135),
    RGBColor(175, 255, 175),
    RGBColor(175, 255, 215),
    RGBColor(175, 255, 255),
    RGBColor(215, 0, 0),
    RGBColor(215, 0, 95),
    RGBColor(215, 0, 135),
    RGBColor(215, 0, 175),
    RGBColor(215, 0, 215),
    RGBColor(215, 0, 255),
    RGBColor(215, 95, 0),
    RGBColor(215, 95, 95),
    RGBColor(215, 95, 135),
    RGBColor(215, 95, 175),
    RGBColor(215, 95, 215),
    RGBColor(215, 95, 255),
    RGBColor(215, 135, 0),
    RGBColor(215, 135, 95),
    RGBColor(215, 135, 135),
    RGBColor(215, 135, 175),
    RGBColor(215, 135, 215),
    RGBColor(215, 135, 255),
    RGBColor(215, 175, 0),
    RGBColor(215, 175, 95),
    RGBColor(215, 175, 135),
    RGBColor(215, 175, 175),
    RGBColor(215, 175, 215),
    RGBColor(215, 175, 255),
    RGBColor(215, 215, 0),
    RGBColor(215, 215, 95),
    RGBColor(215, 215, 135),
    RGBColor(215, 215, 175),
    RGBColor(215, 215, 215),
    RGBColor(215, 215, 255),
    RGBColor(215, 255, 0),
    RGBColor(215, 255, 95),
    RGBColor(215, 255, 135),
    RGBColor(215, 255, 175),
    RGBColor(215, 255, 215),
    RGBColor(215, 255, 255),
    RGBColor(255, 0, 0),
    RGBColor(255, 0, 135),
    RGBColor(255, 0, 95),
    RGBColor(255, 0, 175),
    RGBColor(255, 0, 215),
    RGBColor(255, 0, 255),
    RGBColor(255, 95, 0),
    RGBColor(255, 95, 95),
    RGBColor(255, 95, 135),
    RGBColor(255, 95, 175),
    RGBColor(255, 95, 215),
    RGBColor(255, 95, 255),
    RGBColor(255, 135, 0),
    RGBColor(255, 135, 95),
    RGBColor(255, 135, 135),
    RGBColor(255, 135, 175),
    RGBColor(255, 135, 215),
    RGBColor(255, 135, 255),
    RGBColor(255, 175, 0),
    RGBColor(255, 175, 95),
    RGBColor(255, 175, 135),
    RGBColor(255, 175, 175),
    RGBColor(255, 175, 215),
    RGBColor(255, 175, 255),
    RGBColor(255, 215, 0),
    RGBColor(255, 215, 95),
    RGBColor(255, 215, 135),
    RGBColor(255, 215, 175),
    RGBColor(255, 215, 215),
    RGBColor(255, 215, 255),
    RGBColor(255, 255, 0),
    RGBColor(255, 255, 95),
    RGBColor(255, 255, 135),
    RGBColor(255, 255, 175),
    RGBColor(255, 255, 215),
    RGBColor(255, 255, 255),
    RGBColor(8, 8, 8),
    RGBColor(18, 18, 18),
    RGBColor(28, 28, 28),
    RGBColor(38, 38, 38),
    RGBColor(48, 48, 48),
    RGBColor(58, 58, 58),
    RGBColor(68, 68, 68),
    RGBColor(78, 78, 78),
    RGBColor(88, 88, 88),
    RGBColor(98, 98, 98),
    RGBColor(108, 108, 108),
    RGBColor(118, 118, 118),
    RGBColor(128, 128, 128),
    RGBColor(138, 138, 138),
    RGBColor(148, 148, 148),
    RGBColor(158, 158, 158),
    RGBColor(168, 168, 168),
    RGBColor(178, 178, 178),
    RGBColor(188, 188, 188),
    RGBColor(198, 198, 198),
    RGBColor(208, 208, 208),
    RGBColor(218, 218, 218),
    RGBColor(228, 228, 228),
    RGBColor(238, 238, 238),
)

# === NexusCore/tree_sitter_languages\tree-sitter-python\examples\python2-grammar-crlf.py ===
# Python test set -- part 1, grammar.
# This just tests whether the parser accepts them all.

# NOTE: When you run this test as a script from the command line, you
# get warnings about certain hex/oct constants.  Since those are
# issued by the parser, you can't suppress them by adding a
# filterwarnings() call to this module.  Therefore, to shut up the
# regression test, the filterwarnings() call has been added to
# regrtest.py.

from test.test_support import run_unittest, check_syntax_error
import unittest
import sys
# testing import *
from sys import *

class TokenTests(unittest.TestCase):

    def testBackslash(self):
        # Backslash means line continuation:
        x = 1 \
        + 1
        self.assertEquals(x, 2, 'backslash for line continuation')

        # Backslash does not means continuation in comments :\
        x = 0
        self.assertEquals(x, 0, 'backslash ending comment')

    def testPlainIntegers(self):
        self.assertEquals(0xff, 255)
        self.assertEquals(0377, 255)
        self.assertEquals(2147483647, 017777777777)
        # "0x" is not a valid literal
        self.assertRaises(SyntaxError, eval, "0x")
        from sys import maxint
        if maxint == 2147483647:
            self.assertEquals(-2147483647-1, -020000000000)
            # XXX -2147483648
            self.assert_(037777777777 > 0)
            self.assert_(0xffffffff > 0)
            for s in '2147483648', '040000000000', '0x100000000':
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        elif maxint == 9223372036854775807:
            self.assertEquals(-9223372036854775807-1, -01000000000000000000000)
            self.assert_(01777777777777777777777 > 0)
            self.assert_(0xffffffffffffffff > 0)
            for s in '9223372036854775808', '02000000000000000000000','0x10000000000000000':
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        else:
            self.fail('Weird maxint value %r' % maxint)

    def testLongIntegers(self):
        x = 0L
        x = 0l
        x = 0xffffffffffffffffL
        x = 0xffffffffffffffffl
        x = 077777777777777777L
        x = 077777777777777777l
        x = 123456789012345678901234567890L
        x = 123456789012345678901234567890l

    def testFloats(self):
        x = 3.14
        x = 314.
        x = 0.314
        # XXX x = 000.314
        x = .314
        x = 3e14
        x = 3E14
        x = 3e-14
        x = 3e+14
        x = 3.e14
        x = .3e14
        x = 3.1e4

class GrammarTests(unittest.TestCase):

    # single_input: NEWLINE | simple_stmt | compound_stmt NEWLINE
    # XXX can't test in a script -- this rule is only used when interactive

    # file_input: (NEWLINE | stmt)* ENDMARKER
    # Being tested as this very moment this very module

    # expr_input: testlist NEWLINE
    # XXX Hard to test -- used only in calls to input()

    def testEvalInput(self):
        # testlist ENDMARKER
        x = eval('1, 0 or 1')

    def testFuncdef(self):
        ### 'def' NAME parameters ':' suite
        ### parameters: '(' [varargslist] ')'
        ### varargslist: (fpdef ['=' test] ',')* ('*' NAME [',' ('**'|'*' '*') NAME]
        ###            | ('**'|'*' '*') NAME)
        ###            | fpdef ['=' test] (',' fpdef ['=' test])* [',']
        ### fpdef: NAME | '(' fplist ')'
        ### fplist: fpdef (',' fpdef)* [',']
        ### arglist: (argument ',')* (argument | *' test [',' '**' test] | '**' test)
        ### argument: [test '='] test   # Really [keyword '='] test
        def f1(): pass
        f1()
        f1(*())
        f1(*(), **{})
        def f2(one_argument): pass
        def f3(two, arguments): pass
        def f4(two, (compound, (argument, list))): pass
        def f5((compound, first), two): pass
        self.assertEquals(f2.func_code.co_varnames, ('one_argument',))
        self.assertEquals(f3.func_code.co_varnames, ('two', 'arguments'))
        if sys.platform.startswith('java'):
            self.assertEquals(f4.func_code.co_varnames,
                   ('two', '(compound, (argument, list))', 'compound', 'argument',
                                'list',))
            self.assertEquals(f5.func_code.co_varnames,
                   ('(compound, first)', 'two', 'compound', 'first'))
        else:
            self.assertEquals(f4.func_code.co_varnames,
                  ('two', '.1', 'compound', 'argument',  'list'))
            self.assertEquals(f5.func_code.co_varnames,
                  ('.0', 'two', 'compound', 'first'))
        def a1(one_arg,): pass
        def a2(two, args,): pass
        def v0(*rest): pass
        def v1(a, *rest): pass
        def v2(a, b, *rest): pass
        def v3(a, (b, c), *rest): return a, b, c, rest

        f1()
        f2(1)
        f2(1,)
        f3(1, 2)
        f3(1, 2,)
        f4(1, (2, (3, 4)))
        v0()
        v0(1)
        v0(1,)
        v0(1,2)
        v0(1,2,3,4,5,6,7,8,9,0)
        v1(1)
        v1(1,)
        v1(1,2)
        v1(1,2,3)
        v1(1,2,3,4,5,6,7,8,9,0)
        v2(1,2)
        v2(1,2,3)
        v2(1,2,3,4)
        v2(1,2,3,4,5,6,7,8,9,0)
        v3(1,(2,3))
        v3(1,(2,3),4)
        v3(1,(2,3),4,5,6,7,8,9,0)

        # ceval unpacks the formal arguments into the first argcount names;
        # thus, the names nested inside tuples must appear after these names.
        if sys.platform.startswith('java'):
            self.assertEquals(v3.func_code.co_varnames, ('a', '(b, c)', 'rest', 'b', 'c'))
        else:
            self.assertEquals(v3.func_code.co_varnames, ('a', '.1', 'rest', 'b', 'c'))
        self.assertEquals(v3(1, (2, 3), 4), (1, 2, 3, (4,)))
        def d01(a=1): pass
        d01()
        d01(1)
        d01(*(1,))
        d01(**{'a':2})
        def d11(a, b=1): pass
        d11(1)
        d11(1, 2)
        d11(1, **{'b':2})
        def d21(a, b, c=1): pass
        d21(1, 2)
        d21(1, 2, 3)
        d21(*(1, 2, 3))
        d21(1, *(2, 3))
        d21(1, 2, *(3,))
        d21(1, 2, **{'c':3})
        def d02(a=1, b=2): pass
        d02()
        d02(1)
        d02(1, 2)
        d02(*(1, 2))
        d02(1, *(2,))
        d02(1, **{'b':2})
        d02(**{'a': 1, 'b': 2})
        def d12(a, b=1, c=2): pass
        d12(1)
        d12(1, 2)
        d12(1, 2, 3)
        def d22(a, b, c=1, d=2): pass
        d22(1, 2)
        d22(1, 2, 3)
        d22(1, 2, 3, 4)
        def d01v(a=1, *rest): pass
        d01v()
        d01v(1)
        d01v(1, 2)
        d01v(*(1, 2, 3, 4))
        d01v(*(1,))
        d01v(**{'a':2})
        def d11v(a, b=1, *rest): pass
        d11v(1)
        d11v(1, 2)
        d11v(1, 2, 3)
        def d21v(a, b, c=1, *rest): pass
        d21v(1, 2)
        d21v(1, 2, 3)
        d21v(1, 2, 3, 4)
        d21v(*(1, 2, 3, 4))
        d21v(1, 2, **{'c': 3})
        def d02v(a=1, b=2, *rest): pass
        d02v()
        d02v(1)
        d02v(1, 2)
        d02v(1, 2, 3)
        d02v(1, *(2, 3, 4))
        d02v(**{'a': 1, 'b': 2})
        def d12v(a, b=1, c=2, *rest): pass
        d12v(1)
        d12v(1, 2)
        d12v(1, 2, 3)
        d12v(1, 2, 3, 4)
        d12v(*(1, 2, 3, 4))
        d12v(1, 2, *(3, 4, 5))
        d12v(1, *(2,), **{'c': 3})
        def d22v(a, b, c=1, d=2, *rest): pass
        d22v(1, 2)
        d22v(1, 2, 3)
        d22v(1, 2, 3, 4)
        d22v(1, 2, 3, 4, 5)
        d22v(*(1, 2, 3, 4))
        d22v(1, 2, *(3, 4, 5))
        d22v(1, *(2, 3), **{'d': 4})
        def d31v((x)): pass
        d31v(1)
        def d32v((x,)): pass
        d32v((1,))

        # keyword arguments after *arglist
        def f(*args, **kwargs):
            return args, kwargs
        self.assertEquals(f(1, x=2, *[3, 4], y=5), ((1, 3, 4),
                                                    {'x':2, 'y':5}))
        self.assertRaises(SyntaxError, eval, "f(1, *(2,3), 4)")
        self.assertRaises(SyntaxError, eval, "f(1, x=2, *(3,4), x=5)")

        # Check ast errors in *args and *kwargs
        check_syntax_error(self, "f(*g(1=2))")
        check_syntax_error(self, "f(**g(1=2))")

    def testLambdef(self):
        ### lambdef: 'lambda' [varargslist] ':' test
        l1 = lambda : 0
        self.assertEquals(l1(), 0)
        l2 = lambda : a[d] # XXX just testing the expression
        l3 = lambda : [2 < x for x in [-1, 3, 0L]]
        self.assertEquals(l3(), [0, 1, 0])
        l4 = lambda x = lambda y = lambda z=1 : z : y() : x()
        self.assertEquals(l4(), 1)
        l5 = lambda x, y, z=2: x + y + z
        self.assertEquals(l5(1, 2), 5)
        self.assertEquals(l5(1, 2, 3), 6)
        check_syntax_error(self, "lambda x: x = 2")
        check_syntax_error(self, "lambda (None,): None")

    ### stmt: simple_stmt | compound_stmt
    # Tested below

    def testSimpleStmt(self):
        ### simple_stmt: small_stmt (';' small_stmt)* [';']
        x = 1; pass; del x
        def foo():
            # verify statements that end with semi-colons
            x = 1; pass; del x;
        foo()

    ### small_stmt: expr_stmt | print_stmt  | pass_stmt | del_stmt | flow_stmt | import_stmt | global_stmt | access_stmt | exec_stmt
    # Tested below

    def testExprStmt(self):
        # (exprlist '=')* exprlist
        1
        1, 2, 3
        x = 1
        x = 1, 2, 3
        x = y = z = 1, 2, 3
        x, y, z = 1, 2, 3
        abc = a, b, c = x, y, z = xyz = 1, 2, (3, 4)

        check_syntax_error(self, "x + 1 = 1")
        check_syntax_error(self, "a + 1 = b + 2")

    def testPrintStmt(self):
        # 'print' (test ',')* [test]
        import StringIO

        # Can't test printing to real stdout without comparing output
        # which is not available in unittest.
        save_stdout = sys.stdout
        sys.stdout = StringIO.StringIO()

        print 1, 2, 3
        print 1, 2, 3,
        print
        print 0 or 1, 0 or 1,
        print 0 or 1

        # 'print' '>>' test ','
        print >> sys.stdout, 1, 2, 3
        print >> sys.stdout, 1, 2, 3,
        print >> sys.stdout
        print >> sys.stdout, 0 or 1, 0 or 1,
        print >> sys.stdout, 0 or 1

        # test printing to an instance
        class Gulp:
            def write(self, msg): pass

        gulp = Gulp()
        print >> gulp, 1, 2, 3
        print >> gulp, 1, 2, 3,
        print >> gulp
        print >> gulp, 0 or 1, 0 or 1,
        print >> gulp, 0 or 1

        # test print >> None
        def driver():
            oldstdout = sys.stdout
            sys.stdout = Gulp()
            try:
                tellme(Gulp())
                tellme()
            finally:
                sys.stdout = oldstdout

        # we should see this once
        def tellme(file=sys.stdout):
            print >> file, 'hello world'

        driver()

        # we should not see this at all
        def tellme(file=None):
            print >> file, 'goodbye universe'

        driver()

        self.assertEqual(sys.stdout.getvalue(), '''\
1 2 3
1 2 3
1 1 1
1 2 3
1 2 3
1 1 1
hello world
''')
        sys.stdout = save_stdout

        # syntax errors
        check_syntax_error(self, 'print ,')
        check_syntax_error(self, 'print >> x,')

    def testDelStmt(self):
        # 'del' exprlist
        abc = [1,2,3]
        x, y, z = abc
        xyz = x, y, z

        del abc
        del x, y, (z, xyz)

    def testPassStmt(self):
        # 'pass'
        pass

    # flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt
    # Tested below

    def testBreakStmt(self):
        # 'break'
        while 1: break

    def testContinueStmt(self):
        # 'continue'
        i = 1
        while i: i = 0; continue

        msg = ""
        while not msg:
            msg = "ok"
            try:
                continue
                msg = "continue failed to continue inside try"
            except:
                msg = "continue inside try called except block"
        if msg != "ok":
            self.fail(msg)

        msg = ""
        while not msg:
            msg = "finally block not called"
            try:
                continue
            finally:
                msg = "ok"
        if msg != "ok":
            self.fail(msg)

    def test_break_continue_loop(self):
        # This test warrants an explanation. It is a test specifically for SF bugs
        # #463359 and #462937. The bug is that a 'break' statement executed or
        # exception raised inside a try/except inside a loop, *after* a continue
        # statement has been executed in that loop, will cause the wrong number of
        # arguments to be popped off the stack and the instruction pointer reset to
        # a very small number (usually 0.) Because of this, the following test
        # *must* written as a function, and the tracking vars *must* be function
        # arguments with default values. Otherwise, the test will loop and loop.

        def test_inner(extra_burning_oil = 1, count=0):
            big_hippo = 2
            while big_hippo:
                count += 1
                try:
                    if extra_burning_oil and big_hippo == 1:
                        extra_burning_oil -= 1
                        break
                    big_hippo -= 1
                    continue
                except:
                    raise
            if count > 2 or big_hippo <> 1:
                self.fail("continue then break in try/except in loop broken!")
        test_inner()

    def testReturn(self):
        # 'return' [testlist]
        def g1(): return
        def g2(): return 1
        g1()
        x = g2()
        check_syntax_error(self, "class foo:return 1")

    def testYield(self):
        check_syntax_error(self, "class foo:yield 1")

    def testRaise(self):
        # 'raise' test [',' test]
        try: raise RuntimeError, 'just testing'
        except RuntimeError: pass
        try: raise KeyboardInterrupt
        except KeyboardInterrupt: pass

    def testImport(self):
        # 'import' dotted_as_names
        import sys
        import time, sys
        # 'from' dotted_name 'import' ('*' | '(' import_as_names ')' | import_as_names)
        from time import time
        from time import (time)
        # not testable inside a function, but already done at top of the module
        # from sys import *
        from sys import path, argv
        from sys import (path, argv)
        from sys import (path, argv,)

    def testGlobal(self):
        # 'global' NAME (',' NAME)*
        global a
        global a, b
        global one, two, three, four, five, six, seven, eight, nine, ten

    def testExec(self):
        # 'exec' expr ['in' expr [',' expr]]
        z = None
        del z
        exec 'z=1+1\n'
        if z != 2: self.fail('exec \'z=1+1\'\\n')
        del z
        exec 'z=1+1'
        if z != 2: self.fail('exec \'z=1+1\'')
        z = None
        del z
        import types
        if hasattr(types, "UnicodeType"):
            exec r"""if 1:
            exec u'z=1+1\n'
            if z != 2: self.fail('exec u\'z=1+1\'\\n')
            del z
            exec u'z=1+1'
            if z != 2: self.fail('exec u\'z=1+1\'')"""
        g = {}
        exec 'z = 1' in g
        if g.has_key('__builtins__'): del g['__builtins__']
        if g != {'z': 1}: self.fail('exec \'z = 1\' in g')
        g = {}
        l = {}

        import warnings
        warnings.filterwarnings("ignore", "global statement", module="<string>")
        exec 'global a; a = 1; b = 2' in g, l
        if g.has_key('__builtins__'): del g['__builtins__']
        if l.has_key('__builtins__'): del l['__builtins__']
        if (g, l) != ({'a':1}, {'b':2}):
            self.fail('exec ... in g (%s), l (%s)' %(g,l))

    def testAssert(self):
        # assert_stmt: 'assert' test [',' test]
        assert 1
        assert 1, 1
        assert lambda x:x
        assert 1, lambda x:x+1
        try:
            assert 0, "msg"
        except AssertionError, e:
            self.assertEquals(e.args[0], "msg")
        else:
            if __debug__:
                self.fail("AssertionError not raised by assert 0")

    ### compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | funcdef | classdef
    # Tested below

    def testIf(self):
        # 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        if 1: pass
        if 1: pass
        else: pass
        if 0: pass
        elif 0: pass
        if 0: pass
        elif 0: pass
        elif 0: pass
        elif 0: pass
        else: pass

    def testWhile(self):
        # 'while' test ':' suite ['else' ':' suite]
        while 0: pass
        while 0: pass
        else: pass

        # Issue1920: "while 0" is optimized away,
        # ensure that the "else" clause is still present.
        x = 0
        while 0:
            x = 1
        else:
            x = 2
        self.assertEquals(x, 2)

    def testFor(self):
        # 'for' exprlist 'in' exprlist ':' suite ['else' ':' suite]
        for i in 1, 2, 3: pass
        for i, j, k in (): pass
        else: pass
        class Squares:
            def __init__(self, max):
                self.max = max
                self.sofar = []
            def __len__(self): return len(self.sofar)
            def __getitem__(self, i):
                if not 0 <= i < self.max: raise IndexError
                n = len(self.sofar)
                while n <= i:
                    self.sofar.append(n*n)
                    n = n+1
                return self.sofar[i]
        n = 0
        for x in Squares(10): n = n+x
        if n != 285:
            self.fail('for over growing sequence')

        result = []
        for x, in [(1,), (2,), (3,)]:
            result.append(x)
        self.assertEqual(result, [1, 2, 3])

    def testTry(self):
        ### try_stmt: 'try' ':' suite (except_clause ':' suite)+ ['else' ':' suite]
        ###         | 'try' ':' suite 'finally' ':' suite
        ### except_clause: 'except' [expr [('as' | ',') expr]]
        try:
            1/0
        except ZeroDivisionError:
            pass
        else:
            pass
        try: 1/0
        except EOFError: pass
        except TypeError as msg: pass
        except RuntimeError, msg: pass
        except: pass
        else: pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError): pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError), msg: pass
        try: pass
        finally: pass

    def testSuite(self):
        # simple_stmt | NEWLINE INDENT NEWLINE* (stmt NEWLINE*)+ DEDENT
        if 1: pass
        if 1:
            pass
        if 1:
            #
            #
            #
            pass
            pass
            #
            pass
            #

    def testTest(self):
        ### and_test ('or' and_test)*
        ### and_test: not_test ('and' not_test)*
        ### not_test: 'not' not_test | comparison
        if not 1: pass
        if 1 and 1: pass
        if 1 or 1: pass
        if not not not 1: pass
        if not 1 and 1 and 1: pass
        if 1 and 1 or 1 and 1 and 1 or not 1 and 1: pass

    def testComparison(self):
        ### comparison: expr (comp_op expr)*
        ### comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        if 1: pass
        x = (1 == 1)
        if 1 == 1: pass
        if 1 != 1: pass
        if 1 <> 1: pass
        if 1 < 1: pass
        if 1 > 1: pass
        if 1 <= 1: pass
        if 1 >= 1: pass
        if 1 is 1: pass
        if 1 is not 1: pass
        if 1 in (): pass
        if 1 not in (): pass
        if 1 < 1 > 1 == 1 >= 1 <= 1 <> 1 != 1 in 1 not in 1 is 1 is not 1: pass

    def testBinaryMaskOps(self):
        x = 1 & 1
        x = 1 ^ 1
        x = 1 | 1

    def testShiftOps(self):
        x = 1 << 1
        x = 1 >> 1
        x = 1 << 1 >> 1

    def testAdditiveOps(self):
        x = 1
        x = 1 + 1
        x = 1 - 1 - 1
        x = 1 - 1 + 1 - 1 + 1

    def testMultiplicativeOps(self):
        x = 1 * 1
        x = 1 / 1
        x = 1 % 1
        x = 1 / 1 * 1 % 1

    def testUnaryOps(self):
        x = +1
        x = -1
        x = ~1
        x = ~1 ^ 1 & 1 | 1 & 1 ^ -1
        x = -1*1/1 + 1*1 - ---1*1

    def testSelectors(self):
        ### trailer: '(' [testlist] ')' | '[' subscript ']' | '.' NAME
        ### subscript: expr | [expr] ':' [expr]

        import sys, time
        c = sys.path[0]
        x = time.time()
        x = sys.modules['time'].time()
        a = '01234'
        c = a[0]
        c = a[-1]
        s = a[0:5]
        s = a[:5]
        s = a[0:]
        s = a[:]
        s = a[-5:]
        s = a[:-1]
        s = a[-4:-3]
        # A rough test of SF bug 1333982.  http://python.org/sf/1333982
        # The testing here is fairly incomplete.
        # Test cases should include: commas with 1 and 2 colons
        d = {}
        d[1] = 1
        d[1,] = 2
        d[1,2] = 3
        d[1,2,3] = 4
        L = list(d)
        L.sort()
        self.assertEquals(str(L), '[1, (1,), (1, 2), (1, 2, 3)]')

    def testAtoms(self):
        ### atom: '(' [testlist] ')' | '[' [testlist] ']' | '{' [dictmaker] '}' | '`' testlist '`' | NAME | NUMBER | STRING
        ### dictmaker: test ':' test (',' test ':' test)* [',']

        x = (1)
        x = (1 or 2 or 3)
        x = (1 or 2 or 3, 2, 3)

        x = []
        x = [1]
        x = [1 or 2 or 3]
        x = [1 or 2 or 3, 2, 3]
        x = []

        x = {}
        x = {'one': 1}
        x = {'one': 1,}
        x = {'one' or 'two': 1 or 2}
        x = {'one': 1, 'two': 2}
        x = {'one': 1, 'two': 2,}
        x = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}

        x = `x`
        x = `1 or 2 or 3`
        self.assertEqual(`1,2`, '(1, 2)')

        x = x
        x = 'x'
        x = 123

    ### exprlist: expr (',' expr)* [',']
    ### testlist: test (',' test)* [',']
    # These have been exercised enough above

    def testClassdef(self):
        # 'class' NAME ['(' [testlist] ')'] ':' suite
        class B: pass
        class B2(): pass
        class C1(B): pass
        class C2(B): pass
        class D(C1, C2, B): pass
        class C:
            def meth1(self): pass
            def meth2(self, arg): pass
            def meth3(self, a1, a2): pass
        # decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        # decorators: decorator+
        # decorated: decorators (classdef | funcdef)
        def class_decorator(x):
            x.decorated = True
            return x
        @class_decorator
        class G:
            pass
        self.assertEqual(G.decorated, True)

    def testListcomps(self):
        # list comprehension tests
        nums = [1, 2, 3, 4, 5]
        strs = ["Apple", "Banana", "Coconut"]
        spcs = ["  Apple", " Banana ", "Coco  nut  "]

        self.assertEqual([s.strip() for s in spcs], ['Apple', 'Banana', 'Coco  nut'])
        self.assertEqual([3 * x for x in nums], [3, 6, 9, 12, 15])
        self.assertEqual([x for x in nums if x > 2], [3, 4, 5])
        self.assertEqual([(i, s) for i in nums for s in strs],
                         [(1, 'Apple'), (1, 'Banana'), (1, 'Coconut'),
                          (2, 'Apple'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Apple'), (3, 'Banana'), (3, 'Coconut'),
                          (4, 'Apple'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Apple'), (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(i, s) for i in nums for s in [f for f in strs if "n" in f]],
                         [(1, 'Banana'), (1, 'Coconut'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Banana'), (3, 'Coconut'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(lambda a:[a**i for i in range(a+1)])(j) for j in range(5)],
                         [[1], [1, 1], [1, 2, 4], [1, 3, 9, 27], [1, 4, 16, 64, 256]])

        def test_in_func(l):
            return [None < x < 3 for x in l if x > 2]

        self.assertEqual(test_in_func(nums), [False, False, False])

        def test_nested_front():
            self.assertEqual([[y for y in [x, x + 1]] for x in [1,3,5]],
                             [[1, 2], [3, 4], [5, 6]])

        test_nested_front()

        check_syntax_error(self, "[i, s for i in nums for s in strs]")
        check_syntax_error(self, "[x if y]")

        suppliers = [
          (1, "Boeing"),
          (2, "Ford"),
          (3, "Macdonalds")
        ]

        parts = [
          (10, "Airliner"),
          (20, "Engine"),
          (30, "Cheeseburger")
        ]

        suppart = [
          (1, 10), (1, 20), (2, 20), (3, 30)
        ]

        x = [
          (sname, pname)
            for (sno, sname) in suppliers
              for (pno, pname) in parts
                for (sp_sno, sp_pno) in suppart
                  if sno == sp_sno and pno == sp_pno
        ]

        self.assertEqual(x, [('Boeing', 'Airliner'), ('Boeing', 'Engine'), ('Ford', 'Engine'),
                             ('Macdonalds', 'Cheeseburger')])

    def testGenexps(self):
        # generator expression tests
        g = ([x for x in range(10)] for x in range(1))
        self.assertEqual(g.next(), [x for x in range(10)])
        try:
            g.next()
            self.fail('should produce StopIteration exception')
        except StopIteration:
            pass

        a = 1
        try:
            g = (a for d in a)
            g.next()
            self.fail('should produce TypeError')
        except TypeError:
            pass

        self.assertEqual(list((x, y) for x in 'abcd' for y in 'abcd'), [(x, y) for x in 'abcd' for y in 'abcd'])
        self.assertEqual(list((x, y) for x in 'ab' for y in 'xy'), [(x, y) for x in 'ab' for y in 'xy'])

        a = [x for x in range(10)]
        b = (x for x in (y for y in a))
        self.assertEqual(sum(b), sum([x for x in range(10)]))

        self.assertEqual(sum(x**2 for x in range(10)), sum([x**2 for x in range(10)]))
        self.assertEqual(sum(x*x for x in range(10) if x%2), sum([x*x for x in range(10) if x%2]))
        self.assertEqual(sum(x for x in (y for y in range(10))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10)))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in [y for y in (z for z in range(10))]), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True)) if True), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True) if False) if True), 0)
        check_syntax_error(self, "foo(x for x in range(10), 100)")
        check_syntax_error(self, "foo(100, x for x in range(10))")

    def testComprehensionSpecials(self):
        # test for outmost iterable precomputation
        x = 10; g = (i for i in range(x)); x = 5
        self.assertEqual(len(list(g)), 10)

        # This should hold, since we're only precomputing outmost iterable.
        x = 10; t = False; g = ((i,j) for i in range(x) if t for j in range(x))
        x = 5; t = True;
        self.assertEqual([(i,j) for i in range(10) for j in range(5)], list(g))

        # Grammar allows multiple adjacent 'if's in listcomps and genexps,
        # even though it's silly. Make sure it works (ifelse broke this.)
        self.assertEqual([ x for x in range(10) if x % 2 if x % 3 ], [1, 5, 7])
        self.assertEqual(list(x for x in range(10) if x % 2 if x % 3), [1, 5, 7])

        # verify unpacking single element tuples in listcomp/genexp.
        self.assertEqual([x for x, in [(4,), (5,), (6,)]], [4, 5, 6])
        self.assertEqual(list(x for x, in [(7,), (8,), (9,)]), [7, 8, 9])

    def test_with_statement(self):
        class manager(object):
            def __enter__(self):
                return (1, 2)
            def __exit__(self, *args):
                pass

        with manager():
            pass
        with manager() as x:
            pass
        with manager() as (x, y):
            pass
        with manager(), manager():
            pass
        with manager() as x, manager() as y:
            pass
        with manager() as x, manager():
            pass

    def testIfElseExpr(self):
        # Test ifelse expressions in various cases
        def _checkeval(msg, ret):
            "helper to check that evaluation of expressions is done correctly"
            print x
            return ret

        self.assertEqual([ x() for x in lambda: True, lambda: False if x() ], [True])
        self.assertEqual([ x() for x in (lambda: True, lambda: False) if x() ], [True])
        self.assertEqual([ x(False) for x in (lambda x: False if x else True, lambda x: True if x else False) if x(False) ], [True])
        self.assertEqual((5 if 1 else _checkeval("check 1", 0)), 5)
        self.assertEqual((_checkeval("check 2", 0) if 0 else 5), 5)
        self.assertEqual((5 and 6 if 0 else 1), 1)
        self.assertEqual(((5 and 6) if 0 else 1), 1)
        self.assertEqual((5 and (6 if 1 else 1)), 6)
        self.assertEqual((0 or _checkeval("check 3", 2) if 0 else 3), 3)
        self.assertEqual((1 or _checkeval("check 4", 2) if 1 else _checkeval("check 5", 3)), 1)
        self.assertEqual((0 or 5 if 1 else _checkeval("check 6", 3)), 5)
        self.assertEqual((not 5 if 1 else 1), False)
        self.assertEqual((not 5 if 0 else 1), 1)
        self.assertEqual((6 + 1 if 1 else 2), 7)
        self.assertEqual((6 - 1 if 1 else 2), 5)
        self.assertEqual((6 * 2 if 1 else 4), 12)
        self.assertEqual((6 / 2 if 1 else 3), 3)
        self.assertEqual((6 < 4 if 0 else 2), 2)

    def testStringLiterals(self):
        x = ''; y = ""; self.assert_(len(x) == 0 and x == y)
        x = '\''; y = "'"; self.assert_(len(x) == 1 and x == y and ord(x) == 39)
        x = '"'; y = "\""; self.assert_(len(x) == 1 and x == y and ord(x) == 34)
        x = "doesn't \"shrink\" does it"
        y = 'doesn\'t "shrink" does it'
        self.assert_(len(x) == 24 and x == y)
        x = "does \"shrink\" doesn't it"
        y = 'does "shrink" doesn\'t it'
        self.assert_(len(x) == 24 and x == y)
        x = """
The "quick"
brown fox
jumps over
the 'lazy' dog.
"""
        y = '\nThe "quick"\nbrown fox\njumps over\nthe \'lazy\' dog.\n'
        self.assertEquals(x, y)
        y = '''
The "quick"
brown fox
jumps over
the 'lazy' dog.
'''
        self.assertEquals(x, y)
        y = "\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the 'lazy' dog.\n\
"
        self.assertEquals(x, y)
        y = '\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the \'lazy\' dog.\n\
'
        self.assertEquals(x, y)



def test_main():
    run_unittest(TokenTests, GrammarTests)

if __name__ == '__main__':
    test_main()

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\demos\servers\shell_view.py ===
# A sample shell namespace view

# To demostrate:
# * Execute this script to register the namespace.
# * Open Windows Explorer, and locate the new "Python Path Shell Browser"
#   folder off "My Computer"
# * Browse this tree - .py files are shown expandable, with classes and
#   methods selectable.  Selecting a Python file, or a class/method, will
#   display the file using Scintilla.
# Known problems:
# * Classes and methods don't have icons - this is a demo, so we keep it small
#   See icon_handler.py for examples of how to work with icons.
#
#
# Notes on PIDLs
# PIDLS are complicated, but fairly well documented in MSDN.  If you need to
# do much with these shell extensions, you must understand their concept.
# Here is a short-course, as it applies to this sample:
# A PIDL identifies an item, much in the same way that a filename does
# (however, the shell is not limited to displaying "files").
# An "ItemID" is a single string, each being an item in the hierarchy.
# A "PIDL" is a list of these strings.
# All shell etc functions work with PIDLs, so even in the case where
# an ItemID is conceptually used, a 1-item list is always used.
# Conceptually, think of:
#    pidl = pathname.split("\\") # pidl is a list of "parent" items.
#    # each item is a string 'item id', but these are ever used directly
# As there is no concept of passing a single item, to open a file using only
# a relative filename, conceptually you would say:
#   open_file([filename]) # Pass a single-itemed relative "PIDL"
# and continuing the analogy, a "listdir" type function would return a list
# of single-itemed lists - each list containing the relative PIDL of the child.
#
# Each PIDL entry is a binary string, and may contain any character.  For
# PIDLs not created by you, they can not be interpreted - they are just
# blobs.  PIDLs created by you (ie, children of your IShellFolder) can
# store and interpret the string however makes most sense for your application.
# (but within PIDL rules - they must be persistable, etc)
# There is no reason that pickled strings, for example, couldn't be used
# as an EntryID.
# This application takes a simple approach - each PIDL is a string of form
# "directory\0directory_name", "file\0file_name" or
# "object\0file_name\0class_name[.method_name"
# The first string in each example is literal (ie, the word 'directory',
# 'file' or 'object', and every other string is variable.  We use '\0' as
# a field sep just 'cos we can (and 'cos it can't possibly conflict with the
# string content)

import os
import pyclbr
import sys

import commctrl
import pythoncom
import win32api
import win32con
import win32gui
import win32gui_struct
import winerror
from pywin.scintilla import scintillacon
from win32com.server.exception import COMException
from win32com.server.util import NewEnum, wrap
from win32com.shell import shell, shellcon
from win32com.util import IIDToInterfaceName

# Set this to 1 to cause debug version to be registered and used.  A debug
# version will spew output to win32traceutil.
debug = 0
if debug:
    import win32traceutil

# markh is toying with an implementation that allows auto reload of a module
# if this attribute exists.
com_auto_reload = True


# Helper function to get a system IShellFolder interface, and the PIDL within
# that folder for an existing file/directory.
def GetFolderAndPIDLForPath(filename):
    desktop = shell.SHGetDesktopFolder()
    info = desktop.ParseDisplayName(0, None, os.path.abspath(filename))
    cchEaten, pidl, attr = info
    # We must walk the ID list, looking for one child at a time.
    folder = desktop
    while len(pidl) > 1:
        this = pidl.pop(0)
        folder = folder.BindToObject([this], None, shell.IID_IShellFolder)
    # We are left with the pidl for the specific item.  Leave it as
    # a list, so it remains a valid PIDL.
    return folder, pidl


# A cache of pyclbr module objects, so we only parse a given filename once.
clbr_modules = {}  # Indexed by path, item is dict as returned from pyclbr


def get_clbr_for_file(path):
    try:
        objects = clbr_modules[path]
    except KeyError:
        dir, filename = os.path.split(path)
        base, ext = os.path.splitext(filename)
        objects = pyclbr.readmodule_ex(base, [dir])
        clbr_modules[path] = objects
    return objects


# Our COM interfaces.


# Base class for a shell folder.
# All child classes use a simple PIDL of the form:
#  "object_type\0object_name[\0extra ...]"
class ShellFolderBase:
    _com_interfaces_ = [
        shell.IID_IBrowserFrameOptions,
        pythoncom.IID_IPersist,
        shell.IID_IPersistFolder,
        shell.IID_IShellFolder,
    ]

    _public_methods_ = (
        shellcon.IBrowserFrame_Methods
        + shellcon.IPersistFolder_Methods
        + shellcon.IShellFolder_Methods
    )

    def GetFrameOptions(self, mask):
        # print("GetFrameOptions", self, mask)
        return 0

    def ParseDisplayName(self, hwnd, reserved, displayName, attr):
        print("ParseDisplayName", displayName)
        # return cchEaten, pidl, attr

    def BindToStorage(self, pidl, bc, iid):
        print("BTS", iid, IIDToInterfaceName(iid))

    def BindToObject(self, pidl, bc, iid):
        # We may be passed a set of relative PIDLs here - ie
        # [pidl_of_dir, pidl_of_child_dir, pidl_of_file, pidl_of_function]
        # But each of our PIDLs keeps the fully qualified name anyway - so
        # just jump directly to the last.
        final_pidl = pidl[-1]
        typ, extra = final_pidl.split("\0", 1)
        if typ == "directory":
            klass = ShellFolderDirectory
        elif typ == "file":
            klass = ShellFolderFile
        elif typ == "object":
            klass = ShellFolderObject
        else:
            raise RuntimeError(f"What is {typ!r}")
        ret = wrap(klass(extra), iid, useDispatcher=(debug > 0))
        return ret


# A ShellFolder for an object with CHILDREN on the file system
# Note that this means our "File" folder is *not* a 'FileSystem' folder,
# as it's children (functions and classes) are not on the file system.
#
class ShellFolderFileSystem(ShellFolderBase):
    def _GetFolderAndPIDLForPIDL(self, my_idl):
        typ, name = my_idl[0].split("\0")
        return GetFolderAndPIDLForPath(name)

    # Interface methods
    def CompareIDs(self, param, id1, id2):
        if id1 < id2:
            return -1
        if id1 == id2:
            return 0
        return 1

    def GetUIObjectOf(self, hwndOwner, pidls, iid, inout):
        # delegate to the shell.
        assert len(pidls) == 1, "oops - aren't expecting more than one!"
        pidl = pidls[0]
        folder, child_pidl = self._GetFolderAndPIDLForPIDL(pidl)
        try:
            inout, ret = folder.GetUIObjectOf(hwndOwner, [child_pidl], iid, inout, iid)
        except pythoncom.com_error as exc:
            raise COMException(hresult=exc.hresult)
        return inout, ret
        # return object of IID

    def GetDisplayNameOf(self, pidl, flags):
        # delegate to the shell.
        folder, child_pidl = self._GetFolderAndPIDLForPIDL(pidl)
        ret = folder.GetDisplayNameOf(child_pidl, flags)
        return ret

    def GetAttributesOf(self, pidls, attrFlags):
        ret_flags = -1
        for pidl in pidls:
            pidl = pidl[0]  # ??
            typ, name = pidl.split("\0")
            flags = shellcon.SHGFI_ATTRIBUTES
            rc, info = shell.SHGetFileInfo(name, 0, flags)
            hIcon, iIcon, dwAttr, name, typeName = info
            # All our items, even files, have sub-items
            extras = (
                shellcon.SFGAO_HASSUBFOLDER
                | shellcon.SFGAO_FOLDER
                | shellcon.SFGAO_FILESYSANCESTOR
                | shellcon.SFGAO_BROWSABLE
            )
            ret_flags &= dwAttr | extras
        return ret_flags


class ShellFolderDirectory(ShellFolderFileSystem):
    def __init__(self, path):
        self.path = os.path.abspath(path)

    def CreateViewObject(self, hwnd, iid):
        # delegate to the shell.
        folder, child_pidl = GetFolderAndPIDLForPath(self.path)
        return folder.CreateViewObject(hwnd, iid)

    def EnumObjects(self, hwndOwner, flags):
        pidls = []
        for fname in os.listdir(self.path):
            fqn = os.path.join(self.path, fname)
            if os.path.isdir(fqn):
                type_name = "directory"
                type_class = ShellFolderDirectory
            else:
                base, ext = os.path.splitext(fname)
                if ext in [".py", ".pyw"]:
                    type_class = ShellFolderFile
                    type_name = "file"
                else:
                    type_class = None
            if type_class is not None:
                pidls.append([type_name + "\0" + fqn])
        return NewEnum(pidls, iid=shell.IID_IEnumIDList, useDispatcher=(debug > 0))

    def GetDisplayNameOf(self, pidl, flags):
        final_pidl = pidl[-1]
        full_fname = final_pidl.split("\0")[-1]
        return os.path.split(full_fname)[-1]

    def GetAttributesOf(self, pidls, attrFlags):
        return (
            shellcon.SFGAO_HASSUBFOLDER
            | shellcon.SFGAO_FOLDER
            | shellcon.SFGAO_FILESYSANCESTOR
            | shellcon.SFGAO_BROWSABLE
        )


# As per comments above, even though this manages a file, it is *not* a
# ShellFolderFileSystem, as the children are not on the file system.
class ShellFolderFile(ShellFolderBase):
    def __init__(self, path):
        self.path = os.path.abspath(path)

    def EnumObjects(self, hwndOwner, flags):
        objects = get_clbr_for_file(self.path)
        pidls = []
        for name in objects:
            pidls.append(["object\0" + self.path + "\0" + name])
        return NewEnum(pidls, iid=shell.IID_IEnumIDList, useDispatcher=(debug > 0))

    def GetAttributesOf(self, pidls, attrFlags):
        ret_flags = -1
        for pidl in pidls:
            assert len(pidl) == 1, "Expecting relative pidls"
            pidl = pidl[0]
            typ, filename, obname = pidl.split("\0")
            obs = get_clbr_for_file(filename)
            ob = obs[obname]
            flags = (
                shellcon.SFGAO_BROWSABLE
                | shellcon.SFGAO_FOLDER
                | shellcon.SFGAO_FILESYSANCESTOR
            )
            if hasattr(ob, "methods"):
                flags |= shellcon.SFGAO_HASSUBFOLDER
            ret_flags &= flags
        return ret_flags

    def GetDisplayNameOf(self, pidl, flags):
        assert len(pidl) == 1, "Expecting relative PIDL"
        typ, fname, obname = pidl[0].split("\0")
        fqname = os.path.splitext(fname)[0] + "." + obname
        if flags & shellcon.SHGDN_INFOLDER:
            ret = obname
        else:  # SHGDN_NORMAL is the default
            ret = fqname
        # No need to look at the SHGDN_FOR* modifiers.
        return ret

    def CreateViewObject(self, hwnd, iid):
        return wrap(ScintillaShellView(hwnd, self.path), iid, useDispatcher=debug > 0)


# A ShellFolder for our Python objects
class ShellFolderObject(ShellFolderBase):
    def __init__(self, details):
        self.path, details = details.split("\0")
        if details.find(".") > 0:
            self.class_name, self.method_name = details.split(".")
        else:
            self.class_name = details
            self.method_name = None

    def CreateViewObject(self, hwnd, iid):
        mod_objects = get_clbr_for_file(self.path)
        object = mod_objects[self.class_name]
        if self.method_name is None:
            lineno = object.lineno
        else:
            lineno = object.methods[self.method_name]
            return wrap(
                ScintillaShellView(hwnd, self.path, lineno),
                iid,
                useDispatcher=debug > 0,
            )

    def EnumObjects(self, hwndOwner, flags):
        assert self.method_name is None, "Should not be enuming methods!"
        mod_objects = get_clbr_for_file(self.path)
        my_objects = mod_objects[self.class_name]
        pidls = []
        for func_name in my_objects.methods:
            pidl = ["object\0" + self.path + "\0" + self.class_name + "." + func_name]
            pidls.append(pidl)
        return NewEnum(pidls, iid=shell.IID_IEnumIDList, useDispatcher=(debug > 0))

    def GetDisplayNameOf(self, pidl, flags):
        assert len(pidl) == 1, "Expecting relative PIDL"
        typ, fname, obname = pidl[0].split("\0")
        class_name, method_name = obname.split(".")
        fqname = os.path.splitext(fname)[0] + "." + obname
        if flags & shellcon.SHGDN_INFOLDER:
            ret = method_name
        else:  # SHGDN_NORMAL is the default
            ret = fqname
        # No need to look at the SHGDN_FOR* modifiers.
        return ret

    def GetAttributesOf(self, pidls, attrFlags):
        ret_flags = -1
        for pidl in pidls:
            assert len(pidl) == 1, "Expecting relative pidls"
            flags = (
                shellcon.SFGAO_BROWSABLE
                | shellcon.SFGAO_FOLDER
                | shellcon.SFGAO_FILESYSANCESTOR
            )
            ret_flags &= flags
        return ret_flags


# The "Root" folder of our namespace.  As all children are directories,
# it is derived from ShellFolderFileSystem
# This is the only COM object actually registered and externally created.
class ShellFolderRoot(ShellFolderFileSystem):
    _reg_progid_ = "Python.ShellExtension.Folder"
    _reg_desc_ = "Python Path Shell Browser"
    _reg_clsid_ = "{f6287035-3074-4cb5-a8a6-d3c80e206944}"

    def GetClassID(self):
        return self._reg_clsid_

    def Initialize(self, pidl):
        # This is the PIDL of us, as created by the shell.  This is our
        # top-level ID.  All other items under us have PIDLs defined
        # by us - see the notes at the top of the file.
        # print("Initialize called with pidl={pidl!r}")
        self.pidl = pidl

    def CreateViewObject(self, hwnd, iid):
        return wrap(FileSystemView(self, hwnd), iid, useDispatcher=debug > 0)

    def EnumObjects(self, hwndOwner, flags):
        items = [["directory\0" + p] for p in sys.path if os.path.isdir(p)]
        return NewEnum(items, iid=shell.IID_IEnumIDList, useDispatcher=(debug > 0))

    def GetDisplayNameOf(self, pidl, flags):
        ## return full path for sys.path dirs, since they don't appear under a parent folder
        final_pidl = pidl[-1]
        display_name = final_pidl.split("\0")[-1]
        return display_name


# Simple shell view implementations


# Uses a builtin listview control to display simple lists of directories
# or filenames.
class FileSystemView:
    _public_methods_ = shellcon.IShellView_Methods
    _com_interfaces_ = [
        pythoncom.IID_IOleWindow,
        shell.IID_IShellView,
    ]

    def __init__(self, folder, hwnd):
        self.hwnd_parent = hwnd  # provided by explorer.
        self.hwnd = None  # intermediate window for catching command notifications.
        self.hwnd_child = None  # our ListView
        self.activate_state = None
        self.hmenu = None
        self.browser = None
        self.folder = folder
        self.children = None

    # IOleWindow
    def GetWindow(self):
        return self.hwnd

    def ContextSensitiveHelp(self, enter_mode):
        raise COMException(hresult=winerror.E_NOTIMPL)

    # IShellView
    def CreateViewWindow(self, prev, settings, browser, rect):
        print("FileSystemView.CreateViewWindow", prev, settings, browser, rect)
        self.cur_foldersettings = settings
        self.browser = browser
        self._CreateMainWindow(prev, settings, browser, rect)
        self._CreateChildWindow(prev)

        # This isn't part of the sample, but the most convenient place to
        # test/demonstrate how you can get an IShellBrowser from a HWND
        # (but ONLY when you are in the same process as the IShellBrowser!)
        # Obviously it is not necessary here - we already have the browser!
        browser_ad = win32gui.SendMessage(self.hwnd_parent, win32con.WM_USER + 7, 0, 0)
        browser_ob = pythoncom.ObjectFromAddress(browser_ad, shell.IID_IShellBrowser)
        assert browser == browser_ob
        # and make a call on the object to prove it doesn't die :)
        assert browser.QueryActiveShellView() == browser_ob.QueryActiveShellView()

    def _CreateMainWindow(self, prev, settings, browser, rect):
        # Creates a parent window that hosts the view window.  This window
        # gets the control notifications etc sent from the child.
        style = win32con.WS_CHILD | win32con.WS_VISIBLE  #
        wclass_name = "ShellViewDemo_DefView"
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32gui.dllhandle
        wc.lpszClassName = wclass_name
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        try:
            win32gui.RegisterClass(wc)
        except win32gui.error as details:
            # Should only happen when this module is reloaded
            if details[0] != winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise

        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_NOTIFY: self.OnNotify,
            win32con.WM_CONTEXTMENU: self.OnContextMenu,
            win32con.WM_SIZE: self.OnSize,
        }

        self.hwnd = win32gui.CreateWindow(
            wclass_name,
            "",
            style,
            rect[0],
            rect[1],
            rect[2] - rect[0],
            rect[3] - rect[1],
            self.hwnd_parent,
            0,
            win32gui.dllhandle,
            None,
        )
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, message_map)
        print("View 's hwnd is", self.hwnd)
        return self.hwnd

    def _CreateChildWindow(self, prev):
        # Creates the list view window.
        assert self.hwnd_child is None, "already have a window"
        assert self.cur_foldersettings is not None, "no settings"
        style = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | win32con.WS_BORDER
            | commctrl.LVS_SHAREIMAGELISTS
            | commctrl.LVS_EDITLABELS
        )

        view_mode, view_flags = self.cur_foldersettings
        if view_mode == shellcon.FVM_ICON:
            style |= commctrl.LVS_ICON | commctrl.LVS_AUTOARRANGE
        elif view_mode == shellcon.FVM_SMALLICON:
            style |= commctrl.LVS_SMALLICON | commctrl.LVS_AUTOARRANGE
        elif view_mode == shellcon.FVM_LIST:
            style |= commctrl.LVS_LIST | commctrl.LVS_AUTOARRANGE
        elif view_mode == shellcon.FVM_DETAILS:
            style |= commctrl.LVS_REPORT | commctrl.LVS_AUTOARRANGE
        else:
            # XP 'thumbnails' etc
            view_mode = shellcon.FVM_DETAILS
            # Default to 'report'
            style |= commctrl.LVS_REPORT | commctrl.LVS_AUTOARRANGE

        for f_flag, l_flag in [
            (shellcon.FWF_SINGLESEL, commctrl.LVS_SINGLESEL),
            (shellcon.FWF_ALIGNLEFT, commctrl.LVS_ALIGNLEFT),
            (shellcon.FWF_SHOWSELALWAYS, commctrl.LVS_SHOWSELALWAYS),
        ]:
            if view_flags & f_flag:
                style |= l_flag

        self.hwnd_child = win32gui.CreateWindowEx(
            win32con.WS_EX_CLIENTEDGE,
            "SysListView32",
            None,
            style,
            0,
            0,
            0,
            0,
            self.hwnd,
            1000,
            0,
            None,
        )

        cr = win32gui.GetClientRect(self.hwnd)
        win32gui.MoveWindow(self.hwnd_child, 0, 0, cr[2] - cr[0], cr[3] - cr[1], True)

        # Setup the columns for the view.
        lvc, extras = win32gui_struct.PackLVCOLUMN(
            fmt=commctrl.LVCFMT_LEFT, subItem=1, text="Name", cx=300
        )
        win32gui.SendMessage(self.hwnd_child, commctrl.LVM_INSERTCOLUMN, 0, lvc)

        lvc, extras = win32gui_struct.PackLVCOLUMN(
            fmt=commctrl.LVCFMT_RIGHT, subItem=1, text="Exists", cx=50
        )
        win32gui.SendMessage(self.hwnd_child, commctrl.LVM_INSERTCOLUMN, 1, lvc)
        # and fill it with the content
        self.Refresh()

    def GetCurrentInfo(self):
        return self.cur_foldersettings

    def UIActivate(self, activate_state):
        print("OnActivate")

    def _OnActivate(self, activate_state):
        if self.activate_state == activate_state:
            return
        self._OnDeactivate()  # restore menu's first, if necessary.
        if activate_state != shellcon.SVUIA_DEACTIVATE:
            assert self.hmenu is None, "Should have destroyed it!"
            self.hmenu = win32gui.CreateMenu()
            widths = 0, 0, 0, 0, 0, 0
            # Ask explorer to add its standard items.
            self.browser.InsertMenusSB(self.hmenu, widths)
            # Merge with these standard items
            self._MergeMenus(activate_state)
            self.browser.SetMenuSB(self.hmenu, 0, self.hwnd)
        self.activate_state = activate_state

    def _OnDeactivate(self):
        if self.browser is not None and self.hmenu is not None:
            self.browser.SetMenuSB(0, 0, 0)
            self.browser.RemoveMenusSB(self.hmenu)
            win32gui.DestroyMenu(self.hmenu)
            self.hmenu = None
        self.hsubmenus = None
        self.activate_state = shellcon.SVUIA_DEACTIVATE

    def _MergeMenus(self, activate_state):
        # Merge the operations we support into the top-level menus.
        # NOTE: This function it *not* called each time the selection changes.
        # SVUIA_ACTIVATE_FOCUS really means "have a selection?"
        have_sel = activate_state == shellcon.SVUIA_ACTIVATE_FOCUS
        # only do "file" menu here, and only 1 item on it!
        mid = shellcon.FCIDM_MENU_FILE
        # Get the hmenu for the menu
        buf, extras = win32gui_struct.EmptyMENUITEMINFO(win32con.MIIM_SUBMENU)
        win32gui.GetMenuItemInfo(self.hmenu, mid, False, buf)
        data = win32gui_struct.UnpackMENUITEMINFO(buf)
        submenu = data[3]
        print("Do someting with the file menu!")

    def Refresh(self):
        stateMask = commctrl.LVIS_SELECTED | commctrl.LVIS_DROPHILITED
        state = 0
        self.children = []
        # Enumerate and store the child PIDLs
        for cid in self.folder.EnumObjects(self.hwnd, 0):
            self.children.append(cid)

        for row_index, data in enumerate(self.children):
            assert len(data) == 1, "expecting just a child PIDL"
            typ, path = data[0].split("\0")
            desc = os.path.exists(path) and "Yes" or "No"
            prop_vals = (path, desc)
            # first col
            data, extras = win32gui_struct.PackLVITEM(
                item=row_index,
                subItem=0,
                text=prop_vals[0],
                state=state,
                stateMask=stateMask,
            )
            win32gui.SendMessage(
                self.hwnd_child, commctrl.LVM_INSERTITEM, row_index, data
            )
            # rest of the cols.
            col_index = 1
            for prop_val in prop_vals[1:]:
                data, extras = win32gui_struct.PackLVITEM(
                    item=row_index, subItem=col_index, text=prop_val
                )

                win32gui.SendMessage(self.hwnd_child, commctrl.LVM_SETITEM, 0, data)
                col_index += 1

    def SelectItem(self, pidl, flag):
        # For the sake of brevity, we don't implement this yet.
        # You would need to locate the index of the item in the shell-view
        # with that PIDL, then ask the list-view to select it.
        print("Please implement SelectItem for PIDL", pidl)

    def GetItemObject(self, item_num, iid):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def TranslateAccelerator(self, msg):
        return winerror.S_FALSE

    def DestroyViewWindow(self):
        win32gui.DestroyWindow(self.hwnd)
        self.hwnd = None
        print("Destroyed view window")

    # Message handlers.
    def OnDestroy(self, hwnd, msg, wparam, lparam):
        print("OnDestory")

    def OnCommand(self, hwnd, msg, wparam, lparam):
        print("OnCommand")

    def OnNotify(self, hwnd, msg, wparam, lparam):
        hwndFrom, idFrom, code = win32gui_struct.UnpackWMNOTIFY(lparam)
        # print("OnNotify code=0x%x (0x%x, 0x%x)" % (code, wparam, lparam))
        if code == commctrl.NM_SETFOCUS:
            # Control got focus - Explorer may not know - tell it
            if self.browser is not None:
                self.browser.OnViewWindowActive(None)
            # And do our menu thang
            self._OnActivate(shellcon.SVUIA_ACTIVATE_FOCUS)
        elif code == commctrl.NM_KILLFOCUS:
            self._OnDeactivate()
        elif code == commctrl.NM_DBLCLK:
            # This DblClick implementation leaves a little to be desired :)
            # It demonstrates some useful concepts, such as asking the
            # folder for its context-menu and invoking a command from it.
            # However, as our folder delegates IContextMenu to the shell
            # itself, the end result is that the folder is opened in
            # its "normal" place in Windows explorer rather than inside
            # our shell-extension.
            # Determine the selected items.
            sel = []
            n = -1
            while 1:
                n = win32gui.SendMessage(
                    self.hwnd_child, commctrl.LVM_GETNEXTITEM, n, commctrl.LVNI_SELECTED
                )
                if n == -1:
                    break
                sel.append(self.children[n][-1:])
            print("Selection is", sel)
            hmenu = win32gui.CreateMenu()
            try:
                # Get the IContextMenu for the items.
                inout, cm = self.folder.GetUIObjectOf(
                    self.hwnd_parent, sel, shell.IID_IContextMenu, 0
                )

                # As per 'Q179911', we need to determine if the default operation
                # should be 'open' or 'explore'
                flags = shellcon.CMF_DEFAULTONLY
                try:
                    self.browser.GetControlWindow(shellcon.FCW_TREE)
                    flags |= shellcon.CMF_EXPLORE
                except pythoncom.com_error:
                    pass
                # *sob* - delegating to the shell does work - but lands us
                # in the original location.  Q179911 also shows that
                # ShellExecuteEx should work - but I can't make it work as
                # described (XP: function call succeeds, but another thread
                # shows a dialog with text of E_INVALID_PARAM, and new
                # Explorer window opens with desktop view. Vista: function
                # call succeeds, but no window created at all.
                # On Vista, I'd love to get an IExplorerBrowser interface
                # from the shell, but a QI fails, and although the
                # IShellBrowser does appear to support IServiceProvider, I
                # still can't get it
                if 0:
                    id_cmd_first = 1  # TrackPopupMenu makes it hard to use 0
                    cm.QueryContextMenu(hmenu, 0, id_cmd_first, -1, flags)
                    # Find the default item in the returned menu.
                    cmd = win32gui.GetMenuDefaultItem(hmenu, False, 0)
                    if cmd == -1:
                        print("Oops: _doDefaultActionFor found no default menu")
                    else:
                        ci = (
                            0,
                            self.hwnd_parent,
                            cmd - id_cmd_first,
                            None,
                            None,
                            0,
                            0,
                            0,
                        )
                        cm.InvokeCommand(ci)
                else:
                    rv = shell.ShellExecuteEx(
                        hwnd=self.hwnd_parent,
                        nShow=win32con.SW_NORMAL,
                        lpClass="folder",
                        lpVerb="explore",
                        lpIDList=sel[0],
                    )
                    print("ShellExecuteEx returned", rv)
            finally:
                win32gui.DestroyMenu(hmenu)

    def OnContextMenu(self, hwnd, msg, wparam, lparam):
        # Get the selected items.
        pidls = []
        n = -1
        while 1:
            n = win32gui.SendMessage(
                self.hwnd_child, commctrl.LVM_GETNEXTITEM, n, commctrl.LVNI_SELECTED
            )
            if n == -1:
                break
            pidls.append(self.children[n][-1:])

        spt = win32api.GetCursorPos()
        if not pidls:
            print("Ignoring background click")
            return
        # Get the IContextMenu for the items.
        inout, cm = self.folder.GetUIObjectOf(
            self.hwnd_parent, pidls, shell.IID_IContextMenu, 0
        )
        hmenu = win32gui.CreatePopupMenu()
        sel = None
        # As per 'Q179911', we need to determine if the default operation
        # should be 'open' or 'explore'
        try:
            flags = 0
            try:
                self.browser.GetControlWindow(shellcon.FCW_TREE)
                flags |= shellcon.CMF_EXPLORE
            except pythoncom.com_error:
                pass
            id_cmd_first = 1  # TrackPopupMenu makes it hard to use 0
            cm.QueryContextMenu(hmenu, 0, id_cmd_first, -1, flags)
            tpm_flags = (
                win32con.TPM_LEFTALIGN
                | win32con.TPM_RETURNCMD
                | win32con.TPM_RIGHTBUTTON
            )
            sel = win32gui.TrackPopupMenu(
                hmenu, tpm_flags, spt[0], spt[1], 0, self.hwnd, None
            )
            print("TrackPopupMenu returned", sel)
        finally:
            win32gui.DestroyMenu(hmenu)
        if sel:
            ci = 0, self.hwnd_parent, sel - id_cmd_first, None, None, 0, 0, 0
            cm.InvokeCommand(ci)

    def OnSize(self, hwnd, msg, wparam, lparam):
        # print("OnSize", self.hwnd_child, win32api.LOWORD(lparam), win32api.HIWORD(lparam))
        if self.hwnd_child is not None:
            x = win32api.LOWORD(lparam)
            y = win32api.HIWORD(lparam)
            win32gui.MoveWindow(self.hwnd_child, 0, 0, x, y, False)


# This uses scintilla to display a filename, and optionally jump to a line
# number.
class ScintillaShellView:
    _public_methods_ = shellcon.IShellView_Methods
    _com_interfaces_ = [
        pythoncom.IID_IOleWindow,
        shell.IID_IShellView,
    ]

    def __init__(self, hwnd, filename, lineno=None):
        self.filename = filename
        self.lineno = lineno
        self.hwnd_parent = hwnd
        self.hwnd = None

    def _SendSci(self, msg, wparam=0, lparam=0):
        return win32gui.SendMessage(self.hwnd, msg, wparam, lparam)

    # IShellView
    def CreateViewWindow(self, prev, settings, browser, rect):
        print("ScintillaShellView.CreateViewWindow", prev, settings, browser, rect)
        # Make sure scintilla.dll is loaded.  If not, find it on sys.path
        # (which it generally is for Pythonwin)
        try:
            win32api.GetModuleHandle("Scintilla.dll")
        except win32api.error:
            for p in sys.path:
                fname = os.path.join(p, "Scintilla.dll")
                if not os.path.isfile(fname):
                    fname = os.path.join(p, "Build", "Scintilla.dll")
                if os.path.isfile(fname):
                    win32api.LoadLibrary(fname)
                    break
            else:
                raise RuntimeError("Can't find scintilla!")

        style = (
            win32con.WS_CHILD
            | win32con.WS_VSCROLL
            | win32con.WS_HSCROLL
            | win32con.WS_CLIPCHILDREN
            | win32con.WS_VISIBLE
        )
        self.hwnd = win32gui.CreateWindow(
            "Scintilla",
            "Scintilla",
            style,
            rect[0],
            rect[1],
            rect[2] - rect[0],
            rect[3] - rect[1],
            self.hwnd_parent,
            1000,
            0,
            None,
        )

        message_map = {
            win32con.WM_SIZE: self.OnSize,
        }
        #        win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, message_map)

        file_data = open(self.filename, "U").read()

        self._SetupLexer()
        self._SendSci(scintillacon.SCI_ADDTEXT, len(file_data), file_data)
        if self.lineno is not None:
            self._SendSci(scintillacon.SCI_GOTOLINE, self.lineno)
        print("Scintilla's hwnd is", self.hwnd)

    def _SetupLexer(self):
        h = self.hwnd
        styles = [
            ((0, 0, 200, 0, 0x808080), None, scintillacon.SCE_P_DEFAULT),
            ((0, 2, 200, 0, 0x008000), None, scintillacon.SCE_P_COMMENTLINE),
            ((0, 2, 200, 0, 0x808080), None, scintillacon.SCE_P_COMMENTBLOCK),
            ((0, 0, 200, 0, 0x808000), None, scintillacon.SCE_P_NUMBER),
            ((0, 0, 200, 0, 0x008080), None, scintillacon.SCE_P_STRING),
            ((0, 0, 200, 0, 0x008080), None, scintillacon.SCE_P_CHARACTER),
            ((0, 0, 200, 0, 0x008080), None, scintillacon.SCE_P_TRIPLE),
            ((0, 0, 200, 0, 0x008080), None, scintillacon.SCE_P_TRIPLEDOUBLE),
            ((0, 0, 200, 0, 0x000000), 0x008080, scintillacon.SCE_P_STRINGEOL),
            ((0, 1, 200, 0, 0x800000), None, scintillacon.SCE_P_WORD),
            ((0, 1, 200, 0, 0xFF0000), None, scintillacon.SCE_P_CLASSNAME),
            ((0, 1, 200, 0, 0x808000), None, scintillacon.SCE_P_DEFNAME),
            ((0, 0, 200, 0, 0x000000), None, scintillacon.SCE_P_OPERATOR),
            ((0, 0, 200, 0, 0x000000), None, scintillacon.SCE_P_IDENTIFIER),
        ]
        self._SendSci(scintillacon.SCI_SETLEXER, scintillacon.SCLEX_PYTHON, 0)
        self._SendSci(scintillacon.SCI_SETSTYLEBITS, 5)
        baseFormat = (-402653169, 0, 200, 0, 0, 0, 49, "Courier New")
        for f, bg, stylenum in styles:
            self._SendSci(scintillacon.SCI_STYLESETFORE, stylenum, f[4])
            self._SendSci(scintillacon.SCI_STYLESETFONT, stylenum, baseFormat[7])
            if f[1] & 1:
                self._SendSci(scintillacon.SCI_STYLESETBOLD, stylenum, 1)
            else:
                self._SendSci(scintillacon.SCI_STYLESETBOLD, stylenum, 0)
            if f[1] & 2:
                self._SendSci(scintillacon.SCI_STYLESETITALIC, stylenum, 1)
            else:
                self._SendSci(scintillacon.SCI_STYLESETITALIC, stylenum, 0)
            self._SendSci(
                scintillacon.SCI_STYLESETSIZE, stylenum, int(baseFormat[2] / 20)
            )
            if bg is not None:
                self._SendSci(scintillacon.SCI_STYLESETBACK, stylenum, bg)
            self._SendSci(
                scintillacon.SCI_STYLESETEOLFILLED, stylenum, 1
            )  # Only needed for unclosed strings.

    # IOleWindow
    def GetWindow(self):
        return self.hwnd

    def UIActivate(self, activate_state):
        print("OnActivate")

    def DestroyViewWindow(self):
        win32gui.DestroyWindow(self.hwnd)
        self.hwnd = None
        print("Destroyed scintilla window")

    def TranslateAccelerator(self, msg):
        return winerror.S_FALSE

    def OnSize(self, hwnd, msg, wparam, lparam):
        x = win32api.LOWORD(lparam)
        y = win32api.HIWORD(lparam)
        win32gui.MoveWindow(self.hwnd, 0, 0, x, y, False)


def DllRegisterServer():
    import winreg

    key = winreg.CreateKey(
        winreg.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
        "Explorer\\Desktop\\Namespace\\" + ShellFolderRoot._reg_clsid_,
    )
    winreg.SetValueEx(key, None, 0, winreg.REG_SZ, ShellFolderRoot._reg_desc_)
    # And special shell keys under our CLSID
    key = winreg.CreateKey(
        winreg.HKEY_CLASSES_ROOT,
        "CLSID\\" + ShellFolderRoot._reg_clsid_ + "\\ShellFolder",
    )
    # 'Attributes' is an int stored as a binary! use struct
    attr = (
        shellcon.SFGAO_FOLDER | shellcon.SFGAO_HASSUBFOLDER | shellcon.SFGAO_BROWSABLE
    )
    import struct

    s = struct.pack("i", attr)
    winreg.SetValueEx(key, "Attributes", 0, winreg.REG_BINARY, s)
    print(ShellFolderRoot._reg_desc_, "registration complete.")


def DllUnregisterServer():
    import winreg

    try:
        key = winreg.DeleteKey(
            winreg.HKEY_LOCAL_MACHINE,
            "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
            "Explorer\\Desktop\\Namespace\\" + ShellFolderRoot._reg_clsid_,
        )
    except OSError as details:
        import errno

        if details.errno != errno.ENOENT:
            raise
    print(ShellFolderRoot._reg_desc_, "unregistration complete.")


if __name__ == "__main__":
    from win32com.server import register

    register.UseCommandLine(
        ShellFolderRoot,
        debug=debug,
        finalize_register=DllRegisterServer,
        finalize_unregister=DllUnregisterServer,
    )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\dsls.py ===
"""
    pygments.lexers.dsls
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for various domain-specific languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, RegexLexer, bygroups, words, \
    include, default, this, using, combined
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['ProtoBufLexer', 'ZeekLexer', 'PuppetLexer', 'RslLexer',
           'MscgenLexer', 'VGLLexer', 'AlloyLexer', 'PanLexer',
           'CrmshLexer', 'ThriftLexer', 'FlatlineLexer', 'SnowballLexer']


class ProtoBufLexer(RegexLexer):
    """
    Lexer for Protocol Buffer definition files.
    """

    name = 'Protocol Buffer'
    url = 'https://developers.google.com/protocol-buffers/'
    aliases = ['protobuf', 'proto']
    filenames = ['*.proto']
    version_added = '1.4'

    tokens = {
        'root': [
            (r'[ \t]+', Whitespace),
            (r'[,;{}\[\]()<>]', Punctuation),
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?\*(.|\n)*?\*(\\\n)?/', Comment.Multiline),
            (words((
                'import', 'option', 'optional', 'required', 'repeated',
                'reserved', 'default', 'packed', 'ctype', 'extensions', 'to',
                'max', 'rpc', 'returns', 'oneof', 'syntax'), prefix=r'\b', suffix=r'\b'),
             Keyword),
            (words((
                'int32', 'int64', 'uint32', 'uint64', 'sint32', 'sint64',
                'fixed32', 'fixed64', 'sfixed32', 'sfixed64',
                'float', 'double', 'bool', 'string', 'bytes'), suffix=r'\b'),
             Keyword.Type),
            (r'(true|false)\b', Keyword.Constant),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'package'),
            (r'(message|extend)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'message'),
            (r'(enum|group|service)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'type'),
            (r'\".*?\"', String),
            (r'\'.*?\'', String),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[LlUu]*', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'(\-?(inf|nan))\b', Number.Float),
            (r'0x[0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'0[0-7]+[LlUu]*', Number.Oct),
            (r'\d+[LlUu]*', Number.Integer),
            (r'[+-=]', Operator),
            (r'([a-zA-Z_][\w.]*)([ \t]*)(=)',
             bygroups(Name.Attribute, Whitespace, Operator)),
            (r'[a-zA-Z_][\w.]*', Name),
        ],
        'package': [
            (r'[a-zA-Z_]\w*', Name.Namespace, '#pop'),
            default('#pop'),
        ],
        'message': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            default('#pop'),
        ],
        'type': [
            (r'[a-zA-Z_]\w*', Name, '#pop'),
            default('#pop'),
        ],
    }


class ThriftLexer(RegexLexer):
    """
    For Thrift interface definitions.
    """
    name = 'Thrift'
    url = 'https://thrift.apache.org/'
    aliases = ['thrift']
    filenames = ['*.thrift']
    mimetypes = ['application/x-thrift']
    version_added = '2.1'

    tokens = {
        'root': [
            include('whitespace'),
            include('comments'),
            (r'"', String.Double, combined('stringescape', 'dqs')),
            (r'\'', String.Single, combined('stringescape', 'sqs')),
            (r'(namespace)(\s+)',
                bygroups(Keyword.Namespace, Whitespace), 'namespace'),
            (r'(enum|union|struct|service|exception)(\s+)',
                bygroups(Keyword.Declaration, Whitespace), 'class'),
            (r'((?:(?:[^\W\d]|\$)[\w.\[\]$<>]*\s+)+?)'  # return arguments
             r'((?:[^\W\d]|\$)[\w$]*)'                  # method name
             r'(\s*)(\()',                              # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            include('keywords'),
            include('numbers'),
            (r'[&=]', Operator),
            (r'[:;,{}()<>\[\]]', Punctuation),
            (r'[a-zA-Z_](\.\w|\w)*', Name),
        ],
        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
        ],
        'comments': [
            (r'#.*$', Comment),
            (r'//.*?\n', Comment),
            (r'/\*[\w\W]*?\*/', Comment.Multiline),
        ],
        'stringescape': [
            (r'\\([\\nrt"\'])', String.Escape),
        ],
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'[^\\"\n]+', String.Double),
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r'[^\\\'\n]+', String.Single),
        ],
        'namespace': [
            (r'[a-z*](\.\w|\w)*', Name.Namespace, '#pop'),
            default('#pop'),
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            default('#pop'),
        ],
        'keywords': [
            (r'(async|oneway|extends|throws|required|optional)\b', Keyword),
            (r'(true|false)\b', Keyword.Constant),
            (r'(const|typedef)\b', Keyword.Declaration),
            (words((
                'cpp_namespace', 'cpp_include', 'cpp_type', 'java_package',
                'cocoa_prefix', 'csharp_namespace', 'delphi_namespace',
                'php_namespace', 'py_module', 'perl_package',
                'ruby_namespace', 'smalltalk_category', 'smalltalk_prefix',
                'xsd_all', 'xsd_optional', 'xsd_nillable', 'xsd_namespace',
                'xsd_attrs', 'include'), suffix=r'\b'),
             Keyword.Namespace),
            (words((
                'void', 'bool', 'byte', 'i16', 'i32', 'i64', 'double',
                'string', 'binary', 'map', 'list', 'set', 'slist',
                'senum'), suffix=r'\b'),
             Keyword.Type),
            (words((
                'BEGIN', 'END', '__CLASS__', '__DIR__', '__FILE__',
                '__FUNCTION__', '__LINE__', '__METHOD__', '__NAMESPACE__',
                'abstract', 'alias', 'and', 'args', 'as', 'assert', 'begin',
                'break', 'case', 'catch', 'class', 'clone', 'continue',
                'declare', 'def', 'default', 'del', 'delete', 'do', 'dynamic',
                'elif', 'else', 'elseif', 'elsif', 'end', 'enddeclare',
                'endfor', 'endforeach', 'endif', 'endswitch', 'endwhile',
                'ensure', 'except', 'exec', 'finally', 'float', 'for',
                'foreach', 'function', 'global', 'goto', 'if', 'implements',
                'import', 'in', 'inline', 'instanceof', 'interface', 'is',
                'lambda', 'module', 'native', 'new', 'next', 'nil', 'not',
                'or', 'pass', 'public', 'print', 'private', 'protected',
                'raise', 'redo', 'rescue', 'retry', 'register', 'return',
                'self', 'sizeof', 'static', 'super', 'switch', 'synchronized',
                'then', 'this', 'throw', 'transient', 'try', 'undef',
                'unless', 'unsigned', 'until', 'use', 'var', 'virtual',
                'volatile', 'when', 'while', 'with', 'xor', 'yield'),
                prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
        ],
        'numbers': [
            (r'[+-]?(\d+\.\d+([eE][+-]?\d+)?|\.?\d+[eE][+-]?\d+)', Number.Float),
            (r'[+-]?0x[0-9A-Fa-f]+', Number.Hex),
            (r'[+-]?[0-9]+', Number.Integer),
        ],
    }


class ZeekLexer(RegexLexer):
    """
    For Zeek scripts.
    """
    name = 'Zeek'
    url = 'https://www.zeek.org/'
    aliases = ['zeek', 'bro']
    filenames = ['*.zeek', '*.bro']
    version_added = '2.5'

    _hex = r'[0-9a-fA-F]'
    _float = r'((\d*\.?\d+)|(\d+\.?\d*))([eE][-+]?\d+)?'
    _h = r'[A-Za-z0-9][-A-Za-z0-9]*'

    tokens = {
        'root': [
            include('whitespace'),
            include('comments'),
            include('directives'),
            include('attributes'),
            include('types'),
            include('keywords'),
            include('literals'),
            include('operators'),
            include('punctuation'),
            (r'((?:[A-Za-z_]\w*)(?:::(?:[A-Za-z_]\w*))*)(?=\s*\()',
                Name.Function),
            include('identifiers'),
        ],

        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'(\\)(\n)', bygroups(Text, Whitespace)),
        ],

        'comments': [
            (r'#.*$', Comment),
        ],

        'directives': [
            (r'@(load-plugin|load-sigs|load|unload)\b.*$', Comment.Preproc),
            (r'@(DEBUG|DIR|FILENAME|deprecated|if|ifdef|ifndef|else|endif)\b', Comment.Preproc),
            (r'(@prefixes)(\s*)((\+?=).*)$', bygroups(Comment.Preproc,
                Whitespace, Comment.Preproc)),
        ],

        'attributes': [
            (words(('redef', 'priority', 'log', 'optional', 'default', 'add_func',
                    'delete_func', 'expire_func', 'read_expire', 'write_expire',
                    'create_expire', 'synchronized', 'persistent', 'rotate_interval',
                    'rotate_size', 'encrypt', 'raw_output', 'mergeable', 'error_handler',
                    'type_column', 'deprecated'),
                prefix=r'&', suffix=r'\b'),
             Keyword.Pseudo),
        ],

        'types': [
            (words(('any',
                    'enum', 'record', 'set', 'table', 'vector',
                    'function', 'hook', 'event',
                    'addr', 'bool', 'count', 'double', 'file', 'int', 'interval',
                    'pattern', 'port', 'string', 'subnet', 'time'),
                suffix=r'\b'),
             Keyword.Type),

            (r'(opaque)(\s+)(of)(\s+)((?:[A-Za-z_]\w*)(?:::(?:[A-Za-z_]\w*))*)\b',
                bygroups(Keyword.Type, Whitespace, Operator.Word, Whitespace, Keyword.Type)),

            (r'(type)(\s+)((?:[A-Za-z_]\w*)(?:::(?:[A-Za-z_]\w*))*)(\s*)(:)(\s*)\b(record|enum)\b',
                bygroups(Keyword, Whitespace, Name.Class, Whitespace, Operator, Whitespace, Keyword.Type)),

            (r'(type)(\s+)((?:[A-Za-z_]\w*)(?:::(?:[A-Za-z_]\w*))*)(\s*)(:)',
                bygroups(Keyword, Whitespace, Name, Whitespace, Operator)),

            (r'(redef)(\s+)(record|enum)(\s+)((?:[A-Za-z_]\w*)(?:::(?:[A-Za-z_]\w*))*)\b',
                bygroups(Keyword, Whitespace, Keyword.Type, Whitespace, Name.Class)),
        ],

        'keywords': [
            (words(('redef', 'export', 'if', 'else', 'for', 'while',
                    'return', 'break', 'next', 'continue', 'fallthrough',
                    'switch', 'default', 'case',
                    'add', 'delete',
                    'when', 'timeout', 'schedule'),
                suffix=r'\b'),
             Keyword),
            (r'(print)\b', Keyword),
            (r'(global|local|const|option)\b', Keyword.Declaration),
            (r'(module)(\s+)(([A-Za-z_]\w*)(?:::([A-Za-z_]\w*))*)\b',
                bygroups(Keyword.Namespace, Whitespace, Name.Namespace)),
        ],

        'literals': [
            (r'"', String, 'string'),

            # Not the greatest match for patterns, but generally helps
            # disambiguate between start of a pattern and just a division
            # operator.
            (r'/(?=.*/)', String.Regex, 'regex'),

            (r'(T|F)\b', Keyword.Constant),

            # Port
            (r'\d{1,5}/(udp|tcp|icmp|unknown)\b', Number),

            # IPv4 Address
            (r'(\d{1,3}.){3}(\d{1,3})\b', Number),

            # IPv6 Address
            (r'\[([0-9a-fA-F]{0,4}:){2,7}([0-9a-fA-F]{0,4})?((\d{1,3}.){3}(\d{1,3}))?\]', Number),

            # Numeric
            (r'0[xX]' + _hex + r'+\b', Number.Hex),
            (_float + r'\s*(day|hr|min|sec|msec|usec)s?\b', Number.Float),
            (_float + r'\b', Number.Float),
            (r'(\d+)\b', Number.Integer),

            # Hostnames
            (_h + r'(\.' + _h + r')+', String),
        ],

        'operators': [
            (r'[!%*/+<=>~|&^-]', Operator),
            (r'([-+=&|]{2}|[+=!><-]=)', Operator),
            (r'(in|as|is|of)\b', Operator.Word),
            (r'\??\$', Operator),
        ],

        'punctuation': [
            (r'[{}()\[\],;.]', Punctuation),
            # The "ternary if", which uses '?' and ':', could instead be
            # treated as an Operator, but colons are more frequently used to
            # separate field/identifier names from their types, so the (often)
            # less-prominent Punctuation is used even with '?' for consistency.
            (r'[?:]', Punctuation),
        ],

        'identifiers': [
            (r'([a-zA-Z_]\w*)(::)', bygroups(Name, Punctuation)),
            (r'[a-zA-Z_]\w*', Name)
        ],

        'string': [
            (r'\\.', String.Escape),
            (r'%-?[0-9]*(\.[0-9]+)?[DTd-gsx]', String.Escape),
            (r'"', String, '#pop'),
            (r'.', String),
        ],

        'regex': [
            (r'\\.', String.Escape),
            (r'/', String.Regex, '#pop'),
            (r'.', String.Regex),
        ],
    }


BroLexer = ZeekLexer


class PuppetLexer(RegexLexer):
    """
    For Puppet configuration DSL.
    """
    name = 'Puppet'
    url = 'https://puppet.com/'
    aliases = ['puppet']
    filenames = ['*.pp']
    version_added = '1.6'

    tokens = {
        'root': [
            include('comments'),
            include('keywords'),
            include('names'),
            include('numbers'),
            include('operators'),
            include('strings'),

            (r'[]{}:(),;[]', Punctuation),
            (r'\s+', Whitespace),
        ],

        'comments': [
            (r'(\s*)(#.*)$', bygroups(Whitespace, Comment)),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
        ],

        'operators': [
            (r'(=>|\?|<|>|=|\+|-|/|\*|~|!|\|)', Operator),
            (r'(in|and|or|not)\b', Operator.Word),
        ],

        'names': [
            (r'[a-zA-Z_]\w*', Name.Attribute),
            (r'(\$\S+)(\[)(\S+)(\])', bygroups(Name.Variable, Punctuation,
                                               String, Punctuation)),
            (r'\$\S+', Name.Variable),
        ],

        'numbers': [
            # Copypasta from the Python lexer
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ],

        'keywords': [
            # Left out 'group' and 'require'
            # Since they're often used as attributes
            (words((
                'absent', 'alert', 'alias', 'audit', 'augeas', 'before', 'case',
                'check', 'class', 'computer', 'configured', 'contained',
                'create_resources', 'crit', 'cron', 'debug', 'default',
                'define', 'defined', 'directory', 'else', 'elsif', 'emerg',
                'err', 'exec', 'extlookup', 'fail', 'false', 'file',
                'filebucket', 'fqdn_rand', 'generate', 'host', 'if', 'import',
                'include', 'info', 'inherits', 'inline_template', 'installed',
                'interface', 'k5login', 'latest', 'link', 'loglevel',
                'macauthorization', 'mailalias', 'maillist', 'mcx', 'md5',
                'mount', 'mounted', 'nagios_command', 'nagios_contact',
                'nagios_contactgroup', 'nagios_host', 'nagios_hostdependency',
                'nagios_hostescalation', 'nagios_hostextinfo', 'nagios_hostgroup',
                'nagios_service', 'nagios_servicedependency', 'nagios_serviceescalation',
                'nagios_serviceextinfo', 'nagios_servicegroup', 'nagios_timeperiod',
                'node', 'noop', 'notice', 'notify', 'package', 'present', 'purged',
                'realize', 'regsubst', 'resources', 'role', 'router', 'running',
                'schedule', 'scheduled_task', 'search', 'selboolean', 'selmodule',
                'service', 'sha1', 'shellquote', 'split', 'sprintf',
                'ssh_authorized_key', 'sshkey', 'stage', 'stopped', 'subscribe',
                'tag', 'tagged', 'template', 'tidy', 'true', 'undef', 'unmounted',
                'user', 'versioncmp', 'vlan', 'warning', 'yumrepo', 'zfs', 'zone',
                'zpool'), prefix='(?i)', suffix=r'\b'),
             Keyword),
        ],

        'strings': [
            (r'"([^"])*"', String),
            (r"'(\\'|[^'])*'", String),
        ],

    }


class RslLexer(RegexLexer):
    """
    RSL is the formal specification
    language used in RAISE (Rigorous Approach to Industrial Software Engineering)
    method.
    """
    name = 'RSL'
    url = 'http://en.wikipedia.org/wiki/RAISE'
    aliases = ['rsl']
    filenames = ['*.rsl']
    mimetypes = ['text/rsl']
    version_added = '2.0'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            (words((
                'Bool', 'Char', 'Int', 'Nat', 'Real', 'Text', 'Unit', 'abs',
                'all', 'always', 'any', 'as', 'axiom', 'card', 'case', 'channel',
                'chaos', 'class', 'devt_relation', 'dom', 'elems', 'else', 'elif',
                'end', 'exists', 'extend', 'false', 'for', 'hd', 'hide', 'if',
                'in', 'is', 'inds', 'initialise', 'int', 'inter', 'isin', 'len',
                'let', 'local', 'ltl_assertion', 'object', 'of', 'out', 'post',
                'pre', 'read', 'real', 'rng', 'scheme', 'skip', 'stop', 'swap',
                'then', 'theory', 'test_case', 'tl', 'transition_system', 'true',
                'type', 'union', 'until', 'use', 'value', 'variable', 'while',
                'with', 'write', '~isin', '-inflist', '-infset', '-list',
                '-set'), prefix=r'\b', suffix=r'\b'),
             Keyword),
            (r'(variable|value)\b', Keyword.Declaration),
            (r'--.*?\n', Comment),
            (r'<:.*?:>', Comment),
            (r'\{!.*?!\}', Comment),
            (r'/\*.*?\*/', Comment),
            (r'^([ \t]*)([\w]+)([ \t]*)(:[^:])', bygroups(Whitespace,
                Name.Function, Whitespace, Name.Function)),
            (r'(^[ \t]*)([\w]+)([ \t]*)(\([\w\s,]*\))([ \t]*)(is|as)',
             bygroups(Whitespace, Name.Function, Whitespace, Text,
                 Whitespace, Keyword)),
            (r'\b[A-Z]\w*\b', Keyword.Type),
            (r'(true|false)\b', Keyword.Constant),
            (r'".*"', String),
            (r'\'.\'', String.Char),
            (r'(><|->|-m->|/\\|<=|<<=|<\.|\|\||\|\^\||-~->|-~m->|\\/|>=|>>|'
             r'\.>|\+\+|-\\|<->|=>|:-|~=|\*\*|<<|>>=|\+>|!!|\|=\||#)',
             Operator),
            (r'[0-9]+\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
    }

    def analyse_text(text):
        """
        Check for the most common text in the beginning of a RSL file.
        """
        if re.search(r'scheme\s*.*?=\s*class\s*type', text, re.I) is not None:
            return 1.0


class MscgenLexer(RegexLexer):
    """
    For Mscgen files.
    """
    name = 'Mscgen'
    url = 'http://www.mcternan.me.uk/mscgen/'
    aliases = ['mscgen', 'msc']
    filenames = ['*.msc']
    version_added = '1.6'

    _var = r'(\w+|"(?:\\"|[^"])*")'

    tokens = {
        'root': [
            (r'msc\b', Keyword.Type),
            # Options
            (r'(hscale|HSCALE|width|WIDTH|wordwraparcs|WORDWRAPARCS'
             r'|arcgradient|ARCGRADIENT)\b', Name.Property),
            # Operators
            (r'(abox|ABOX|rbox|RBOX|box|BOX|note|NOTE)\b', Operator.Word),
            (r'(\.|-|\|){3}', Keyword),
            (r'(?:-|=|\.|:){2}'
             r'|<<=>>|<->|<=>|<<>>|<:>'
             r'|->|=>>|>>|=>|:>|-x|-X'
             r'|<-|<<=|<<|<=|<:|x-|X-|=', Operator),
            # Names
            (r'\*', Name.Builtin),
            (_var, Name.Variable),
            # Other
            (r'\[', Punctuation, 'attrs'),
            (r'\{|\}|,|;', Punctuation),
            include('comments')
        ],
        'attrs': [
            (r'\]', Punctuation, '#pop'),
            (_var + r'(\s*)(=)(\s*)' + _var,
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace,
                      String)),
            (r',', Punctuation),
            include('comments')
        ],
        'comments': [
            (r'(?://|#).*?\n', Comment.Single),
            (r'/\*(?:.|\n)*?\*/', Comment.Multiline),
            (r'[ \t\r\n]+', Whitespace)
        ]
    }


class VGLLexer(RegexLexer):
    """
    For SampleManager VGL source code.
    """
    name = 'VGL'
    url = 'http://www.thermoscientific.com/samplemanager'
    aliases = ['vgl']
    filenames = ['*.rpf']
    version_added = '1.6'

    flags = re.MULTILINE | re.DOTALL | re.IGNORECASE

    tokens = {
        'root': [
            (r'\{[^}]*\}', Comment.Multiline),
            (r'declare', Keyword.Constant),
            (r'(if|then|else|endif|while|do|endwhile|and|or|prompt|object'
             r'|create|on|line|with|global|routine|value|endroutine|constant'
             r'|global|set|join|library|compile_option|file|exists|create|copy'
             r'|delete|enable|windows|name|notprotected)(?! *[=<>.,()])',
             Keyword),
            (r'(true|false|null|empty|error|locked)', Keyword.Constant),
            (r'[~^*#!%&\[\]()<>|+=:;,./?-]', Operator),
            (r'"[^"]*"', String),
            (r'(\.)([a-z_$][\w$]*)', bygroups(Operator, Name.Attribute)),
            (r'[0-9][0-9]*(\.[0-9]+(e[+\-]?[0-9]+)?)?', Number),
            (r'[a-z_$][\w$]*', Name),
            (r'[\r\n]+', Whitespace),
            (r'\s+', Whitespace)
        ]
    }


class AlloyLexer(RegexLexer):
    """
    For Alloy source code.
    """

    name = 'Alloy'
    url = 'http://alloy.mit.edu'
    aliases = ['alloy']
    filenames = ['*.als']
    mimetypes = ['text/x-alloy']
    version_added = '2.0'

    flags = re.MULTILINE | re.DOTALL

    iden_rex = r'[a-zA-Z_][\w]*"*'
    string_rex = r'"\b(\\\\|\\[^\\]|[^"\\])*"'
    text_tuple = (r'[^\S\n]+', Whitespace)

    tokens = {
        'sig': [
            (r'(extends)\b', Keyword, '#pop'),
            (iden_rex, Name),
            text_tuple,
            (r',', Punctuation),
            (r'\{', Operator, '#pop'),
        ],
        'module': [
            text_tuple,
            (iden_rex, Name, '#pop'),
        ],
        'fun': [
            text_tuple,
            (r'\{', Operator, '#pop'),
            (iden_rex, Name, '#pop'),
        ],
        'fact': [
            include('fun'),
            (string_rex, String, '#pop'),
        ],
        'root': [
            (r'--.*?$', Comment.Single),
            (r'//.*?$', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            text_tuple,
            (r'(module|open)(\s+)', bygroups(Keyword.Namespace, Whitespace),
                'module'),
            (r'(sig|enum)(\s+)', bygroups(Keyword.Declaration, Whitespace), 'sig'),
            (r'(iden|univ|none)\b', Keyword.Constant),
            (r'(int|Int)\b', Keyword.Type),
            (r'(var|this|abstract|extends|set|seq|one|lone|let)\b', Keyword),
            (r'(all|some|no|sum|disj|when|else)\b', Keyword),
            (r'(run|check|for|but|exactly|expect|as|steps)\b', Keyword),
            (r'(always|after|eventually|until|release)\b', Keyword), # future time operators
            (r'(historically|before|once|since|triggered)\b', Keyword), # past time operators
            (r'(and|or|implies|iff|in)\b', Operator.Word),
            (r'(fun|pred|assert)(\s+)', bygroups(Keyword, Whitespace), 'fun'),
            (r'(fact)(\s+)', bygroups(Keyword, Whitespace), 'fact'),
            (r'!|#|&&|\+\+|<<|>>|>=|<=>|<=|\.\.|\.|->', Operator),
            (r'[-+/*%=<>&!^|~{}\[\]().\';]', Operator),
            (iden_rex, Name),
            (r'[:,]', Punctuation),
            (r'[0-9]+', Number.Integer),
            (string_rex, String),
            (r'\n', Whitespace),
        ]
    }


class PanLexer(RegexLexer):
    """
    Lexer for pan source files.

    Based on tcsh lexer.
    """

    name = 'Pan'
    url = 'https://github.com/quattor/pan/'
    aliases = ['pan']
    filenames = ['*.pan']
    version_added = '2.0'

    tokens = {
        'root': [
            include('basic'),
            (r'\(', Keyword, 'paren'),
            (r'\{', Keyword, 'curly'),
            include('data'),
        ],
        'basic': [
            (words((
                'if', 'for', 'with', 'else', 'type', 'bind', 'while', 'valid', 'final',
                'prefix', 'unique', 'object', 'foreach', 'include', 'template',
                'function', 'variable', 'structure', 'extensible', 'declaration'),
                prefix=r'\b', suffix=r'\b'),
             Keyword),
            (words((
                'file_contents', 'format', 'index', 'length', 'match', 'matches',
                'replace', 'splice', 'split', 'substr', 'to_lowercase', 'to_uppercase',
                'debug', 'error', 'traceback', 'deprecated', 'base64_decode',
                'base64_encode', 'digest', 'escape', 'unescape', 'append', 'create',
                'first', 'nlist', 'key', 'list', 'merge', 'next', 'prepend', 'is_boolean',
                'is_defined', 'is_double', 'is_list', 'is_long', 'is_nlist', 'is_null',
                'is_number', 'is_property', 'is_resource', 'is_string', 'to_boolean',
                'to_double', 'to_long', 'to_string', 'clone', 'delete', 'exists',
                'path_exists', 'if_exists', 'return', 'value'),
                prefix=r'\b', suffix=r'\b'),
             Name.Builtin),
            (r'#.*', Comment),
            (r'\\[\w\W]', String.Escape),
            (r'(\b\w+)(\s*)(=)', bygroups(Name.Variable, Whitespace, Operator)),
            (r'[\[\]{}()=]+', Operator),
            (r'<<\s*(\'?)\\?(\w+)[\w\W]+?\2', String),
            (r';', Punctuation),
        ],
        'data': [
            (r'(?s)"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
            (r"(?s)'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r'\s+', Whitespace),
            (r'[^=\s\[\]{}()$"\'`\\;#]+', Text),
            (r'\d+(?= |\Z)', Number),
        ],
        'curly': [
            (r'\}', Keyword, '#pop'),
            (r':-', Keyword),
            (r'\w+', Name.Variable),
            (r'[^}:"\'`$]+', Punctuation),
            (r':', Punctuation),
            include('root'),
        ],
        'paren': [
            (r'\)', Keyword, '#pop'),
            include('root'),
        ],
    }


class CrmshLexer(RegexLexer):
    """
    Lexer for crmsh configuration files for Pacemaker clusters.
    """
    name = 'Crmsh'
    url = 'http://crmsh.github.io/'
    aliases = ['crmsh', 'pcmk']
    filenames = ['*.crmsh', '*.pcmk']
    mimetypes = []
    version_added = '2.1'

    elem = words((
        'node', 'primitive', 'group', 'clone', 'ms', 'location',
        'colocation', 'order', 'fencing_topology', 'rsc_ticket',
        'rsc_template', 'property', 'rsc_defaults',
        'op_defaults', 'acl_target', 'acl_group', 'user', 'role',
        'tag'), suffix=r'(?![\w#$-])')
    sub = words((
        'params', 'meta', 'operations', 'op', 'rule',
        'attributes', 'utilization'), suffix=r'(?![\w#$-])')
    acl = words(('read', 'write', 'deny'), suffix=r'(?![\w#$-])')
    bin_rel = words(('and', 'or'), suffix=r'(?![\w#$-])')
    un_ops = words(('defined', 'not_defined'), suffix=r'(?![\w#$-])')
    date_exp = words(('in_range', 'date', 'spec', 'in'), suffix=r'(?![\w#$-])')
    acl_mod = (r'(?:tag|ref|reference|attribute|type|xpath)')
    bin_ops = (r'(?:lt|gt|lte|gte|eq|ne)')
    val_qual = (r'(?:string|version|number)')
    rsc_role_action = (r'(?:Master|Started|Slave|Stopped|'
                       r'start|promote|demote|stop)')

    tokens = {
        'root': [
            (r'^(#.*)(\n)?', bygroups(Comment, Whitespace)),
            # attr=value (nvpair)
            (r'([\w#$-]+)(=)("(?:""|[^"])*"|\S+)',
                bygroups(Name.Attribute, Punctuation, String)),
            # need this construct, otherwise numeric node ids
            # are matched as scores
            # elem id:
            (r'(node)(\s+)([\w#$-]+)(:)',
                bygroups(Keyword, Whitespace, Name, Punctuation)),
            # scores
            (r'([+-]?([0-9]+|inf)):', Number),
            # keywords (elements and other)
            (elem, Keyword),
            (sub, Keyword),
            (acl, Keyword),
            # binary operators
            (rf'(?:{val_qual}:)?({bin_ops})(?![\w#$-])', Operator.Word),
            # other operators
            (bin_rel, Operator.Word),
            (un_ops, Operator.Word),
            (date_exp, Operator.Word),
            # builtin attributes (e.g. #uname)
            (r'#[a-z]+(?![\w#$-])', Name.Builtin),
            # acl_mod:blah
            (rf'({acl_mod})(:)("(?:""|[^"])*"|\S+)',
             bygroups(Keyword, Punctuation, Name)),
            # rsc_id[:(role|action)]
            # NB: this matches all other identifiers
            (rf'([\w#$-]+)(?:(:)({rsc_role_action}))?(?![\w#$-])',
             bygroups(Name, Punctuation, Operator.Word)),
            # punctuation
            (r'(\\(?=\n)|[\[\](){}/:@])', Punctuation),
            (r'\s+|\n', Whitespace),
        ],
    }


class FlatlineLexer(RegexLexer):
    """
    Lexer for Flatline expressions.
    """
    name = 'Flatline'
    url = 'https://github.com/bigmlcom/flatline'
    aliases = ['flatline']
    filenames = []
    mimetypes = ['text/x-flatline']
    version_added = '2.2'

    special_forms = ('let',)

    builtins = (
        "!=", "*", "+", "-", "<", "<=", "=", ">", ">=", "abs", "acos", "all",
        "all-but", "all-with-defaults", "all-with-numeric-default", "and",
        "asin", "atan", "avg", "avg-window", "bin-center", "bin-count", "call",
        "category-count", "ceil", "cond", "cond-window", "cons", "cos", "cosh",
        "count", "diff-window", "div", "ensure-value", "ensure-weighted-value",
        "epoch", "epoch-day", "epoch-fields", "epoch-hour", "epoch-millisecond",
        "epoch-minute", "epoch-month", "epoch-second", "epoch-weekday",
        "epoch-year", "exp", "f", "field", "field-prop", "fields", "filter",
        "first", "floor", "head", "if", "in", "integer", "language", "length",
        "levenshtein", "linear-regression", "list", "ln", "log", "log10", "map",
        "matches", "matches?", "max", "maximum", "md5", "mean", "median", "min",
        "minimum", "missing", "missing-count", "missing?", "missing_count",
        "mod", "mode", "normalize", "not", "nth", "occurrences", "or",
        "percentile", "percentile-label", "population", "population-fraction",
        "pow", "preferred", "preferred?", "quantile-label", "rand", "rand-int",
        "random-value", "re-quote", "real", "replace", "replace-first", "rest",
        "round", "row-number", "segment-label", "sha1", "sha256", "sin", "sinh",
        "sqrt", "square", "standard-deviation", "standard_deviation", "str",
        "subs", "sum", "sum-squares", "sum-window", "sum_squares", "summary",
        "summary-no", "summary-str", "tail", "tan", "tanh", "to-degrees",
        "to-radians", "variance", "vectorize", "weighted-random-value", "window",
        "winnow", "within-percentiles?", "z-score",
    )

    valid_name = r'(?!#)[\w!$%*+<=>?/.#-]+'

    tokens = {
        'root': [
            # whitespaces - usually not relevant
            (r'[,]+', Text),
            (r'\s+', Whitespace),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            (r'0x-?[a-f\d]+', Number.Hex),

            # strings, symbols and characters
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"\\(.|[a-z]+)", String.Char),

            # expression template placeholder
            (r'_', String.Symbol),

            # highlight the special forms
            (words(special_forms, suffix=' '), Keyword),

            # highlight the builtins
            (words(builtins, suffix=' '), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),

            # find the remaining variables
            (valid_name, Name.Variable),

            # parentheses
            (r'(\(|\))', Punctuation),
        ],
    }


class SnowballLexer(ExtendedRegexLexer):
    """
    Lexer for Snowball source code.
    """

    name = 'Snowball'
    url = 'https://snowballstem.org/'
    aliases = ['snowball']
    filenames = ['*.sbl']
    version_added = '2.2'

    _ws = r'\n\r\t '

    def __init__(self, **options):
        self._reset_stringescapes()
        ExtendedRegexLexer.__init__(self, **options)

    def _reset_stringescapes(self):
        self._start = "'"
        self._end = "'"

    def _string(do_string_first):
        def callback(lexer, match, ctx):
            s = match.start()
            text = match.group()
            string = re.compile(rf'([^{re.escape(lexer._start)}]*)(.)').match
            escape = re.compile(rf'([^{re.escape(lexer._end)}]*)(.)').match
            pos = 0
            do_string = do_string_first
            while pos < len(text):
                if do_string:
                    match = string(text, pos)
                    yield s + match.start(1), String.Single, match.group(1)
                    if match.group(2) == "'":
                        yield s + match.start(2), String.Single, match.group(2)
                        ctx.stack.pop()
                        break
                    yield s + match.start(2), String.Escape, match.group(2)
                    pos = match.end()
                match = escape(text, pos)
                yield s + match.start(), String.Escape, match.group()
                if match.group(2) != lexer._end:
                    ctx.stack[-1] = 'escape'
                    break
                pos = match.end()
                do_string = True
            ctx.pos = s + match.end()
        return callback

    def _stringescapes(lexer, match, ctx):
        lexer._start = match.group(3)
        lexer._end = match.group(5)
        return bygroups(Keyword.Reserved, Whitespace, String.Escape, Whitespace,
                        String.Escape)(lexer, match, ctx)

    tokens = {
        'root': [
            (r'len\b', Name.Builtin),
            (r'lenof\b', Operator.Word),
            include('root1'),
        ],
        'root1': [
            (rf'[{_ws}]+', Whitespace),
            (r'\d+', Number.Integer),
            (r"'", String.Single, 'string'),
            (r'[()]', Punctuation),
            (r'/\*[\w\W]*?\*/', Comment.Multiline),
            (r'//.*', Comment.Single),
            (r'[!*+\-/<=>]=|[-=]>|<[+-]|[$*+\-/<=>?\[\]]', Operator),
            (words(('as', 'get', 'hex', 'among', 'define', 'decimal',
                    'backwardmode'), suffix=r'\b'),
             Keyword.Reserved),
            (words(('strings', 'booleans', 'integers', 'routines', 'externals',
                    'groupings'), suffix=r'\b'),
             Keyword.Reserved, 'declaration'),
            (words(('do', 'or', 'and', 'for', 'hop', 'non', 'not', 'set', 'try',
                    'fail', 'goto', 'loop', 'next', 'test', 'true',
                    'false', 'unset', 'atmark', 'attach', 'delete', 'gopast',
                    'insert', 'repeat', 'sizeof', 'tomark', 'atleast',
                    'atlimit', 'reverse', 'setmark', 'tolimit', 'setlimit',
                    'backwards', 'substring'), suffix=r'\b'),
             Operator.Word),
            (words(('size', 'limit', 'cursor', 'maxint', 'minint'),
                   suffix=r'\b'),
             Name.Builtin),
            (rf'(stringdef\b)([{_ws}]*)([^{_ws}]+)',
             bygroups(Keyword.Reserved, Whitespace, String.Escape)),
            (rf'(stringescapes\b)([{_ws}]*)(.)([{_ws}]*)(.)',
             _stringescapes),
            (r'[A-Za-z]\w*', Name),
        ],
        'declaration': [
            (r'\)', Punctuation, '#pop'),
            (words(('len', 'lenof'), suffix=r'\b'), Name,
             ('root1', 'declaration')),
            include('root1'),
        ],
        'string': [
            (r"[^']*'", _string(True)),
        ],
        'escape': [
            (r"[^']*'", _string(False)),
        ],
    }

    def get_tokens_unprocessed(self, text=None, context=None):
        self._reset_stringescapes()
        return ExtendedRegexLexer.get_tokens_unprocessed(self, text, context)

# === NexusCore/openenv\Lib\site-packages\proto\message.py ===
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import collections.abc
import copy
import re
from typing import Any, Dict, List, Optional, Type
import warnings

import google.protobuf
from google.protobuf import descriptor_pb2
from google.protobuf import message
from google.protobuf.json_format import MessageToDict, MessageToJson, Parse

from proto import _file_info
from proto import _package_info
from proto.fields import Field
from proto.fields import MapField
from proto.fields import RepeatedField
from proto.marshal import Marshal
from proto.primitives import ProtoType
from proto.utils import has_upb


PROTOBUF_VERSION = google.protobuf.__version__

_upb = has_upb()  # Important to cache result here.


class MessageMeta(type):
    """A metaclass for building and registering Message subclasses."""

    def __new__(mcls, name, bases, attrs):
        # Do not do any special behavior for Message itself.
        if not bases:
            return super().__new__(mcls, name, bases, attrs)

        # Get the essential information about the proto package, and where
        # this component belongs within the file.
        package, marshal = _package_info.compile(name, attrs)

        # Determine the local path of this proto component within the file.
        local_path = tuple(attrs.get("__qualname__", name).split("."))

        # Sanity check: We get the wrong full name if a class is declared
        # inside a function local scope; correct this.
        if "<locals>" in local_path:
            ix = local_path.index("<locals>")
            local_path = local_path[: ix - 1] + local_path[ix + 1 :]

        # Determine the full name in protocol buffers.
        full_name = ".".join((package,) + local_path).lstrip(".")

        # Special case: Maps. Map fields are special; they are essentially
        # shorthand for a nested message and a repeated field of that message.
        # Decompose each map into its constituent form.
        # https://developers.google.com/protocol-buffers/docs/proto3#maps
        map_fields = {}
        for key, field in attrs.items():
            if not isinstance(field, MapField):
                continue

            # Determine the name of the entry message.
            msg_name = "{pascal_key}Entry".format(
                pascal_key=re.sub(
                    r"_\w",
                    lambda m: m.group()[1:].upper(),
                    key,
                ).replace(key[0], key[0].upper(), 1),
            )

            # Create the "entry" message (with the key and value fields).
            #
            # Note: We instantiate an ordered dictionary here and then
            # attach key and value in order to ensure that the fields are
            # iterated in the correct order when the class is created.
            # This is only an issue in Python 3.5, where the order is
            # random (and the wrong order causes the pool to refuse to add
            # the descriptor because reasons).
            entry_attrs = collections.OrderedDict(
                {
                    "__module__": attrs.get("__module__", None),
                    "__qualname__": "{prefix}.{name}".format(
                        prefix=attrs.get("__qualname__", name),
                        name=msg_name,
                    ),
                    "_pb_options": {"map_entry": True},
                }
            )
            entry_attrs["key"] = Field(field.map_key_type, number=1)
            entry_attrs["value"] = Field(
                field.proto_type,
                number=2,
                enum=field.enum,
                message=field.message,
            )
            map_fields[msg_name] = MessageMeta(msg_name, (Message,), entry_attrs)

            # Create the repeated field for the entry message.
            map_fields[key] = RepeatedField(
                ProtoType.MESSAGE,
                number=field.number,
                message=map_fields[msg_name],
            )

        # Add the new entries to the attrs
        attrs.update(map_fields)

        # Okay, now we deal with all the rest of the fields.
        # Iterate over all the attributes and separate the fields into
        # their own sequence.
        fields = []
        new_attrs = {}
        oneofs = collections.OrderedDict()
        proto_imports = set()
        index = 0
        for key, field in attrs.items():
            # Sanity check: If this is not a field, do nothing.
            if not isinstance(field, Field):
                # The field objects themselves should not be direct attributes.
                new_attrs[key] = field
                continue

            # Add data that the field requires that we do not take in the
            # constructor because we can derive it from the metaclass.
            # (The goal is to make the declaration syntax as nice as possible.)
            field.mcls_data = {
                "name": key,
                "parent_name": full_name,
                "index": index,
                "package": package,
            }

            # Add the field to the list of fields.
            fields.append(field)
            # If this field is part of a "oneof", ensure the oneof itself
            # is represented.
            if field.oneof:
                # Keep a running tally of the index of each oneof, and assign
                # that index to the field's descriptor.
                oneofs.setdefault(field.oneof, len(oneofs))
                field.descriptor.oneof_index = oneofs[field.oneof]

            # If this field references a message, it may be from another
            # proto file; ensure we know about the import (to faithfully
            # construct our file descriptor proto).
            if field.message and not isinstance(field.message, str):
                field_msg = field.message
                if hasattr(field_msg, "pb") and callable(field_msg.pb):
                    field_msg = field_msg.pb()
                # Sanity check: The field's message may not yet be defined if
                # it was a Message defined in the same file, and the file
                # descriptor proto has not yet been generated.
                #
                # We do nothing in this situation; everything will be handled
                # correctly when the file descriptor is created later.
                if field_msg:
                    proto_imports.add(field_msg.DESCRIPTOR.file.name)

            # Same thing, but for enums.
            elif field.enum and not isinstance(field.enum, str):
                field_enum = (
                    field.enum._meta.pb
                    if hasattr(field.enum, "_meta")
                    else field.enum.DESCRIPTOR
                )

                if field_enum:
                    proto_imports.add(field_enum.file.name)

            # Increment the field index counter.
            index += 1

        # As per descriptor.proto, all synthetic oneofs must be ordered after
        # 'real' oneofs.
        opt_attrs = {}
        for field in fields:
            if field.optional:
                field.oneof = "_{}".format(field.name)
                field.descriptor.oneof_index = oneofs[field.oneof] = len(oneofs)
                opt_attrs[field.name] = field.name

        # Generating a metaclass dynamically provides class attributes that
        # instances can't see. This provides idiomatically named constants
        # that enable the following pattern to check for field presence:
        #
        # class MyMessage(proto.Message):
        #     field = proto.Field(proto.INT32, number=1, optional=True)
        #
        # m = MyMessage()
        # MyMessage.field in m
        if opt_attrs:
            mcls = type("AttrsMeta", (mcls,), opt_attrs)

        # Determine the filename.
        # We determine an appropriate proto filename based on the
        # Python module.
        filename = _file_info._FileInfo.proto_file_name(
            new_attrs.get("__module__", name.lower())
        )

        # Get or create the information about the file, including the
        # descriptor to which the new message descriptor shall be added.
        file_info = _file_info._FileInfo.maybe_add_descriptor(filename, package)

        # Ensure any imports that would be necessary are assigned to the file
        # descriptor proto being created.
        for proto_import in proto_imports:
            if proto_import not in file_info.descriptor.dependency:
                file_info.descriptor.dependency.append(proto_import)

        # Retrieve any message options.
        opts = descriptor_pb2.MessageOptions(**new_attrs.pop("_pb_options", {}))

        # Create the underlying proto descriptor.
        desc = descriptor_pb2.DescriptorProto(
            name=name,
            field=[i.descriptor for i in fields],
            oneof_decl=[
                descriptor_pb2.OneofDescriptorProto(name=i) for i in oneofs.keys()
            ],
            options=opts,
        )

        # If any descriptors were nested under this one, they need to be
        # attached as nested types here.
        child_paths = [p for p in file_info.nested.keys() if local_path == p[:-1]]
        for child_path in child_paths:
            desc.nested_type.add().MergeFrom(file_info.nested.pop(child_path))

        # Same thing, but for enums
        child_paths = [p for p in file_info.nested_enum.keys() if local_path == p[:-1]]
        for child_path in child_paths:
            desc.enum_type.add().MergeFrom(file_info.nested_enum.pop(child_path))

        # Add the descriptor to the file if it is a top-level descriptor,
        # or to a "holding area" for nested messages otherwise.
        if len(local_path) == 1:
            file_info.descriptor.message_type.add().MergeFrom(desc)
        else:
            file_info.nested[local_path] = desc

        # Create the MessageInfo instance to be attached to this message.
        new_attrs["_meta"] = _MessageInfo(
            fields=fields,
            full_name=full_name,
            marshal=marshal,
            options=opts,
            package=package,
        )

        # Run the superclass constructor.
        cls = super().__new__(mcls, name, bases, new_attrs)

        # The info class and fields need a reference to the class just created.
        cls._meta.parent = cls
        for field in cls._meta.fields.values():
            field.parent = cls

        # Add this message to the _FileInfo instance; this allows us to
        # associate the descriptor with the message once the descriptor
        # is generated.
        file_info.messages[full_name] = cls

        # Generate the descriptor for the file if it is ready.
        if file_info.ready(new_class=cls):
            file_info.generate_file_pb(new_class=cls, fallback_salt=full_name)

        # Done; return the class.
        return cls

    @classmethod
    def __prepare__(mcls, name, bases, **kwargs):
        return collections.OrderedDict()

    @property
    def meta(cls):
        return cls._meta

    def __dir__(self):
        try:
            names = set(dir(type))
            names.update(
                (
                    "meta",
                    "pb",
                    "wrap",
                    "serialize",
                    "deserialize",
                    "to_json",
                    "from_json",
                    "to_dict",
                    "copy_from",
                )
            )
            desc = self.pb().DESCRIPTOR
            names.update(t.name for t in desc.nested_types)
            names.update(e.name for e in desc.enum_types)

            return names
        except AttributeError:
            return dir(type)

    def pb(cls, obj=None, *, coerce: bool = False):
        """Return the underlying protobuf Message class or instance.

        Args:
            obj: If provided, and an instance of ``cls``, return the
                underlying protobuf instance.
            coerce (bool): If provided, will attempt to coerce ``obj`` to
                ``cls`` if it is not already an instance.
        """
        if obj is None:
            return cls.meta.pb
        if not isinstance(obj, cls):
            if coerce:
                obj = cls(obj)
            else:
                raise TypeError(
                    "%r is not an instance of %s"
                    % (
                        obj,
                        cls.__name__,
                    )
                )
        return obj._pb

    def wrap(cls, pb):
        """Return a Message object that shallowly wraps the descriptor.

        Args:
            pb: A protocol buffer object, such as would be returned by
                :meth:`pb`.
        """
        # Optimized fast path.
        instance = cls.__new__(cls)
        super(cls, instance).__setattr__("_pb", pb)
        return instance

    def serialize(cls, instance) -> bytes:
        """Return the serialized proto.

        Args:
            instance: An instance of this message type, or something
                compatible (accepted by the type's constructor).

        Returns:
            bytes: The serialized representation of the protocol buffer.
        """
        return cls.pb(instance, coerce=True).SerializeToString()

    def deserialize(cls, payload: bytes) -> "Message":
        """Given a serialized proto, deserialize it into a Message instance.

        Args:
            payload (bytes): The serialized proto.

        Returns:
            ~.Message: An instance of the message class against which this
            method was called.
        """
        return cls.wrap(cls.pb().FromString(payload))

    def _warn_if_including_default_value_fields_is_used_protobuf_5(
        cls, including_default_value_fields: Optional[bool]
    ) -> None:
        """
        Warn Protobuf 5.x+ users that `including_default_value_fields` is deprecated if it is set.

        Args:
            including_default_value_fields (Optional(bool)): The value of `including_default_value_fields` set by the user.
        """
        if (
            PROTOBUF_VERSION[0] not in ("3", "4")
            and including_default_value_fields is not None
        ):
            warnings.warn(
                """The argument `including_default_value_fields` has been removed from
                Protobuf 5.x. Please use `always_print_fields_with_no_presence` instead.
                """,
                DeprecationWarning,
            )

    def _raise_if_print_fields_values_are_set_and_differ(
        cls,
        always_print_fields_with_no_presence: Optional[bool],
        including_default_value_fields: Optional[bool],
    ) -> None:
        """
        Raise Exception if both `always_print_fields_with_no_presence` and `including_default_value_fields` are set
            and the values differ.

        Args:
            always_print_fields_with_no_presence (Optional(bool)): The value of `always_print_fields_with_no_presence` set by the user.
            including_default_value_fields (Optional(bool)): The value of `including_default_value_fields` set by the user.
        Returns:
            None
        Raises:
            ValueError: if both `always_print_fields_with_no_presence` and `including_default_value_fields` are set and
                the values differ.
        """
        if (
            always_print_fields_with_no_presence is not None
            and including_default_value_fields is not None
            and always_print_fields_with_no_presence != including_default_value_fields
        ):
            raise ValueError(
                "Arguments `always_print_fields_with_no_presence` and `including_default_value_fields` must match"
            )

    def _normalize_print_fields_without_presence(
        cls,
        always_print_fields_with_no_presence: Optional[bool],
        including_default_value_fields: Optional[bool],
    ) -> bool:
        """
        Return true if fields with no presence should be included in the results.
        By default, fields with no presence will be included in the results
        when both `always_print_fields_with_no_presence` and
        `including_default_value_fields` are not set

        Args:
            always_print_fields_with_no_presence (Optional(bool)): The value of `always_print_fields_with_no_presence` set by the user.
            including_default_value_fields (Optional(bool)): The value of `including_default_value_fields` set by the user.
        Returns:
            None
        Raises:
            ValueError: if both `always_print_fields_with_no_presence` and `including_default_value_fields` are set and
                the values differ.
        """

        cls._warn_if_including_default_value_fields_is_used_protobuf_5(
            including_default_value_fields
        )
        cls._raise_if_print_fields_values_are_set_and_differ(
            always_print_fields_with_no_presence, including_default_value_fields
        )
        # Default to True if neither `always_print_fields_with_no_presence` or `including_default_value_fields` is set
        return (
            (
                always_print_fields_with_no_presence is None
                and including_default_value_fields is None
            )
            or always_print_fields_with_no_presence
            or including_default_value_fields
        )

    def to_json(
        cls,
        instance,
        *,
        use_integers_for_enums=True,
        including_default_value_fields=None,
        preserving_proto_field_name=False,
        sort_keys=False,
        indent=2,
        float_precision=None,
        always_print_fields_with_no_presence=None,
    ) -> str:
        """Given a message instance, serialize it to json

        Args:
            instance: An instance of this message type, or something
                compatible (accepted by the type's constructor).
            use_integers_for_enums (Optional(bool)): An option that determines whether enum
                values should be represented by strings (False) or integers (True).
                Default is True.
            including_default_value_fields (Optional(bool)): Deprecated. Use argument
                `always_print_fields_with_no_presence` instead. An option that
                determines whether the default field values should be included in the results.
                This value must match `always_print_fields_with_no_presence`,
                if both arguments are explicitly set.
            preserving_proto_field_name (Optional(bool)): An option that
                determines whether field name representations preserve
                proto case (snake_case) or use lowerCamelCase. Default is False.
            sort_keys (Optional(bool)): If True, then the output will be sorted by field names.
                Default is False.
            indent (Optional(int)): The JSON object will be pretty-printed with this indent level.
                An indent level of 0 or negative will only insert newlines.
                Pass None for the most compact representation without newlines.
            float_precision (Optional(int)): If set, use this to specify float field valid digits.
                Default is None.
            always_print_fields_with_no_presence (Optional(bool)): If True, fields without
                presence (implicit presence scalars, repeated fields, and map fields) will
                always be serialized. Any field that supports presence is not affected by
                this option (including singular message fields and oneof fields).
                This value must match `including_default_value_fields`,
                if both arguments are explicitly set.
        Returns:
            str: The json string representation of the protocol buffer.
        """

        print_fields = cls._normalize_print_fields_without_presence(
            always_print_fields_with_no_presence, including_default_value_fields
        )

        if PROTOBUF_VERSION[0] in ("3", "4"):
            return MessageToJson(
                cls.pb(instance),
                use_integers_for_enums=use_integers_for_enums,
                including_default_value_fields=print_fields,
                preserving_proto_field_name=preserving_proto_field_name,
                sort_keys=sort_keys,
                indent=indent,
                float_precision=float_precision,
            )
        else:
            # The `including_default_value_fields` argument was removed from protobuf 5.x
            # and replaced with `always_print_fields_with_no_presence` which very similar but has
            # handles optional fields consistently by not affecting them.
            # The old flag accidentally had inconsistent behavior between proto2
            # optional and proto3 optional fields.
            return MessageToJson(
                cls.pb(instance),
                use_integers_for_enums=use_integers_for_enums,
                always_print_fields_with_no_presence=print_fields,
                preserving_proto_field_name=preserving_proto_field_name,
                sort_keys=sort_keys,
                indent=indent,
                float_precision=float_precision,
            )

    def from_json(cls, payload, *, ignore_unknown_fields=False) -> "Message":
        """Given a json string representing an instance,
        parse it into a message.

        Args:
            payload: A json string representing a message.
            ignore_unknown_fields (Optional(bool)): If True, do not raise errors
                for unknown fields.

        Returns:
            ~.Message: An instance of the message class against which this
            method was called.
        """
        instance = cls()
        Parse(payload, instance._pb, ignore_unknown_fields=ignore_unknown_fields)
        return instance

    def to_dict(
        cls,
        instance,
        *,
        use_integers_for_enums=True,
        preserving_proto_field_name=True,
        including_default_value_fields=None,
        float_precision=None,
        always_print_fields_with_no_presence=None,
    ) -> Dict[str, Any]:
        """Given a message instance, return its representation as a python dict.

        Args:
            instance: An instance of this message type, or something
                compatible (accepted by the type's constructor).
            use_integers_for_enums (Optional(bool)): An option that determines whether enum
                values should be represented by strings (False) or integers (True).
                Default is True.
            preserving_proto_field_name (Optional(bool)): An option that
                determines whether field name representations preserve
                proto case (snake_case) or use lowerCamelCase. Default is True.
            including_default_value_fields (Optional(bool)): Deprecated. Use argument
                `always_print_fields_with_no_presence` instead. An option that
                determines whether the default field values should be included in the results.
                This value must match `always_print_fields_with_no_presence`,
                if both arguments are explicitly set.
            float_precision (Optional(int)): If set, use this to specify float field valid digits.
                Default is None.
            always_print_fields_with_no_presence (Optional(bool)): If True, fields without
                presence (implicit presence scalars, repeated fields, and map fields) will
                always be serialized. Any field that supports presence is not affected by
                this option (including singular message fields and oneof fields). This value
                must match `including_default_value_fields`, if both arguments are explicitly set.

        Returns:
            dict: A representation of the protocol buffer using pythonic data structures.
                  Messages and map fields are represented as dicts,
                  repeated fields are represented as lists.
        """

        print_fields = cls._normalize_print_fields_without_presence(
            always_print_fields_with_no_presence, including_default_value_fields
        )

        if PROTOBUF_VERSION[0] in ("3", "4"):
            return MessageToDict(
                cls.pb(instance),
                including_default_value_fields=print_fields,
                preserving_proto_field_name=preserving_proto_field_name,
                use_integers_for_enums=use_integers_for_enums,
                float_precision=float_precision,
            )
        else:
            # The `including_default_value_fields` argument was removed from protobuf 5.x
            # and replaced with `always_print_fields_with_no_presence` which very similar but has
            # handles optional fields consistently by not affecting them.
            # The old flag accidentally had inconsistent behavior between proto2
            # optional and proto3 optional fields.
            return MessageToDict(
                cls.pb(instance),
                always_print_fields_with_no_presence=print_fields,
                preserving_proto_field_name=preserving_proto_field_name,
                use_integers_for_enums=use_integers_for_enums,
                float_precision=float_precision,
            )

    def copy_from(cls, instance, other):
        """Equivalent for protobuf.Message.CopyFrom

        Args:
            instance: An instance of this message type
            other: (Union[dict, ~.Message):
                A dictionary or message to reinitialize the values for this message.
        """
        if isinstance(other, cls):
            # Just want the underlying proto.
            other = Message.pb(other)
        elif isinstance(other, cls.pb()):
            # Don't need to do anything.
            pass
        elif isinstance(other, collections.abc.Mapping):
            # Coerce into a proto
            other = cls._meta.pb(**other)
        else:
            raise TypeError(
                "invalid argument type to copy to {}: {}".format(
                    cls.__name__, other.__class__.__name__
                )
            )

        # Note: we can't just run self.__init__ because this may be a message field
        # for a higher order proto; the memory layout for protos is NOT LIKE the
        # python memory model. We cannot rely on just setting things by reference.
        # Non-trivial complexity is (partially) hidden by the protobuf runtime.
        cls.pb(instance).CopyFrom(other)


class Message(metaclass=MessageMeta):
    """The abstract base class for a message.

    Args:
        mapping (Union[dict, ~.Message]): A dictionary or message to be
            used to determine the values for this message.
        ignore_unknown_fields (Optional(bool)): If True, do not raise errors for
            unknown fields. Only applied if `mapping` is a mapping type or there
            are keyword parameters.
        kwargs (dict): Keys and values corresponding to the fields of the
            message.
    """

    def __init__(
        self,
        mapping=None,
        *,
        ignore_unknown_fields=False,
        **kwargs,
    ):
        # We accept several things for `mapping`:
        #   * An instance of this class.
        #   * An instance of the underlying protobuf descriptor class.
        #   * A dict
        #   * Nothing (keyword arguments only).
        if mapping is None:
            if not kwargs:
                # Special fast path for empty construction.
                super().__setattr__("_pb", self._meta.pb())
                return

            mapping = kwargs
        elif isinstance(mapping, self._meta.pb):
            # Make a copy of the mapping.
            # This is a constructor for a new object, so users will assume
            # that it will not have side effects on the arguments being
            # passed in.
            #
            # The `wrap` method on the metaclass is the public API for taking
            # ownership of the passed in protobuf object.
            mapping = copy.deepcopy(mapping)
            if kwargs:
                mapping.MergeFrom(self._meta.pb(**kwargs))

            super().__setattr__("_pb", mapping)
            return
        elif isinstance(mapping, type(self)):
            # Just use the above logic on mapping's underlying pb.
            self.__init__(mapping=mapping._pb, **kwargs)
            return
        elif isinstance(mapping, collections.abc.Mapping):
            # Can't have side effects on mapping.
            mapping = copy.copy(mapping)
            # kwargs entries take priority for duplicate keys.
            mapping.update(kwargs)
        else:
            # Sanity check: Did we get something not a map? Error if so.
            raise TypeError(
                "Invalid constructor input for %s: %r"
                % (
                    self.__class__.__name__,
                    mapping,
                )
            )

        params = {}
        # Update the mapping to address any values that need to be
        # coerced.
        marshal = self._meta.marshal
        for key, value in mapping.items():
            (key, pb_type) = self._get_pb_type_from_key(key)
            if pb_type is None:
                if ignore_unknown_fields:
                    continue

                raise ValueError(
                    "Unknown field for {}: {}".format(self.__class__.__name__, key)
                )

            pb_value = marshal.to_proto(pb_type, value)

            if pb_value is not None:
                params[key] = pb_value

        # Create the internal protocol buffer.
        super().__setattr__("_pb", self._meta.pb(**params))

    def _get_pb_type_from_key(self, key):
        """Given a key, return the corresponding pb_type.

        Args:
            key(str): The name of the field.

        Returns:
            A tuple containing a key and pb_type. The pb_type will be
            the composite type of the field, or the primitive type if a primitive.
            If no corresponding field exists, return None.
        """

        pb_type = None

        try:
            pb_type = self._meta.fields[key].pb_type
        except KeyError:
            # Underscores may be appended to field names
            # that collide with python or proto-plus keywords.
            # In case a key only exists with a `_` suffix, coerce the key
            # to include the `_` suffix. It's not possible to
            # natively define the same field with a trailing underscore in protobuf.
            # See related issue
            # https://github.com/googleapis/python-api-core/issues/227
            if f"{key}_" in self._meta.fields:
                key = f"{key}_"
                pb_type = self._meta.fields[key].pb_type

        return (key, pb_type)

    def __dir__(self):
        desc = type(self).pb().DESCRIPTOR
        names = {f_name for f_name in self._meta.fields.keys()}
        names.update(m.name for m in desc.nested_types)
        names.update(e.name for e in desc.enum_types)
        names.update(dir(object()))
        # Can't think of a better way of determining
        # the special methods than manually listing them.
        names.update(
            (
                "__bool__",
                "__contains__",
                "__dict__",
                "__getattr__",
                "__getstate__",
                "__module__",
                "__setstate__",
                "__weakref__",
            )
        )

        return names

    def __bool__(self):
        """Return True if any field is truthy, False otherwise."""
        return any(k in self and getattr(self, k) for k in self._meta.fields.keys())

    def __contains__(self, key):
        """Return True if this field was set to something non-zero on the wire.

        In most cases, this method will return True when ``__getattr__``
        would return a truthy value and False when it would return a falsy
        value, so explicitly calling this is not useful.

        The exception case is empty messages explicitly set on the wire,
        which are falsy from ``__getattr__``. This method allows to
        distinguish between an explicitly provided empty message and the
        absence of that message, which is useful in some edge cases.

        The most common edge case is the use of ``google.protobuf.BoolValue``
        to get a boolean that distinguishes between ``False`` and ``None``
        (or the same for a string, int, etc.). This library transparently
        handles that case for you, but this method remains available to
        accommodate cases not automatically covered.

        Args:
            key (str): The name of the field.

        Returns:
            bool: Whether the field's value corresponds to a non-empty
                wire serialization.
        """
        pb_value = getattr(self._pb, key)
        try:
            # Protocol buffers "HasField" is unfriendly; it only works
            # against composite, non-repeated fields, and raises ValueError
            # against any repeated field or primitive.
            #
            # There is no good way to test whether it is valid to provide
            # a field to this method, so sadly we are stuck with a
            # somewhat inefficient try/except.
            return self._pb.HasField(key)
        except ValueError:
            return bool(pb_value)

    def __delattr__(self, key):
        """Delete the value on the given field.

        This is generally equivalent to setting a falsy value.
        """
        self._pb.ClearField(key)

    def __eq__(self, other):
        """Return True if the messages are equal, False otherwise."""
        # If these are the same type, use internal protobuf's equality check.
        if isinstance(other, type(self)):
            return self._pb == other._pb

        # If the other type is the target protobuf object, honor that also.
        if isinstance(other, self._meta.pb):
            return self._pb == other

        # Ask the other object.
        return NotImplemented

    def __getattr__(self, key):
        """Retrieve the given field's value.

        In protocol buffers, the presence of a field on a message is
        sufficient for it to always be "present".

        For primitives, a value of the correct type will always be returned
        (the "falsy" values in protocol buffers consistently match those
        in Python). For repeated fields, the falsy value is always an empty
        sequence.

        For messages, protocol buffers does distinguish between an empty
        message and absence, but this distinction is subtle and rarely
        relevant. Therefore, this method always returns an empty message
        (following the official implementation). To check for message
        presence, use ``key in self`` (in other words, ``__contains__``).

        .. note::

            Some well-known protocol buffer types
            (e.g. ``google.protobuf.Timestamp``) will be converted to
            their Python equivalents. See the ``marshal`` module for
            more details.
        """
        (key, pb_type) = self._get_pb_type_from_key(key)
        if pb_type is None:
            raise AttributeError(
                "Unknown field for {}: {}".format(self.__class__.__name__, key)
            )
        pb_value = getattr(self._pb, key)
        marshal = self._meta.marshal
        return marshal.to_python(pb_type, pb_value, absent=key not in self)

    def __ne__(self, other):
        """Return True if the messages are unequal, False otherwise."""
        return not self == other

    def __repr__(self):
        return repr(self._pb)

    def __setattr__(self, key, value):
        """Set the value on the given field.

        For well-known protocol buffer types which are marshalled, either
        the protocol buffer object or the Python equivalent is accepted.
        """
        if key[0] == "_":
            return super().__setattr__(key, value)
        marshal = self._meta.marshal
        (key, pb_type) = self._get_pb_type_from_key(key)
        if pb_type is None:
            raise AttributeError(
                "Unknown field for {}: {}".format(self.__class__.__name__, key)
            )

        pb_value = marshal.to_proto(pb_type, value)

        # Clear the existing field.
        # This is the only way to successfully write nested falsy values,
        # because otherwise MergeFrom will no-op on them.
        self._pb.ClearField(key)

        # Merge in the value being set.
        if pb_value is not None:
            self._pb.MergeFrom(self._meta.pb(**{key: pb_value}))

    def __getstate__(self):
        """Serialize for pickling."""
        return self._pb.SerializeToString()

    def __setstate__(self, value):
        """Deserialization for pickling."""
        new_pb = self._meta.pb().FromString(value)
        super().__setattr__("_pb", new_pb)


class _MessageInfo:
    """Metadata about a message.

    Args:
        fields (Tuple[~.fields.Field]): The fields declared on the message.
        package (str): The proto package.
        full_name (str): The full name of the message.
        file_info (~._FileInfo): The file descriptor and messages for the
            file containing this message.
        marshal (~.Marshal): The marshal instance to which this message was
            automatically registered.
        options (~.descriptor_pb2.MessageOptions): Any options that were
            set on the message.
    """

    def __init__(
        self,
        *,
        fields: List[Field],
        package: str,
        full_name: str,
        marshal: Marshal,
        options: descriptor_pb2.MessageOptions,
    ) -> None:
        self.package = package
        self.full_name = full_name
        self.options = options
        self.fields = collections.OrderedDict((i.name, i) for i in fields)
        self.fields_by_number = collections.OrderedDict((i.number, i) for i in fields)
        self.marshal = marshal
        self._pb = None

    @property
    def pb(self) -> Type[message.Message]:
        """Return the protobuf message type for this descriptor.

        If a field on the message references another message which has not
        loaded, then this method returns None.
        """
        return self._pb


__all__ = ("Message",)

# === NexusCore/openenv\Lib\site-packages\cffi\api.py ===
import sys, types
from .lock import allocate_lock
from .error import CDefError
from . import model

try:
    callable
except NameError:
    # Python 3.1
    from collections import Callable
    callable = lambda x: isinstance(x, Callable)

try:
    basestring
except NameError:
    # Python 3.x
    basestring = str

_unspecified = object()



class FFI(object):
    r'''
    The main top-level class that you instantiate once, or once per module.

    Example usage:

        ffi = FFI()
        ffi.cdef("""
            int printf(const char *, ...);
        """)

        C = ffi.dlopen(None)   # standard library
        -or-
        C = ffi.verify()  # use a C compiler: verify the decl above is right

        C.printf("hello, %s!\n", ffi.new("char[]", "world"))
    '''

    def __init__(self, backend=None):
        """Create an FFI instance.  The 'backend' argument is used to
        select a non-default backend, mostly for tests.
        """
        if backend is None:
            # You need PyPy (>= 2.0 beta), or a CPython (>= 2.6) with
            # _cffi_backend.so compiled.
            import _cffi_backend as backend
            from . import __version__
            if backend.__version__ != __version__:
                # bad version!  Try to be as explicit as possible.
                if hasattr(backend, '__file__'):
                    # CPython
                    raise Exception("Version mismatch: this is the 'cffi' package version %s, located in %r.  When we import the top-level '_cffi_backend' extension module, we get version %s, located in %r.  The two versions should be equal; check your installation." % (
                        __version__, __file__,
                        backend.__version__, backend.__file__))
                else:
                    # PyPy
                    raise Exception("Version mismatch: this is the 'cffi' package version %s, located in %r.  This interpreter comes with a built-in '_cffi_backend' module, which is version %s.  The two versions should be equal; check your installation." % (
                        __version__, __file__, backend.__version__))
            # (If you insist you can also try to pass the option
            # 'backend=backend_ctypes.CTypesBackend()', but don't
            # rely on it!  It's probably not going to work well.)

        from . import cparser
        self._backend = backend
        self._lock = allocate_lock()
        self._parser = cparser.Parser()
        self._cached_btypes = {}
        self._parsed_types = types.ModuleType('parsed_types').__dict__
        self._new_types = types.ModuleType('new_types').__dict__
        self._function_caches = []
        self._libraries = []
        self._cdefsources = []
        self._included_ffis = []
        self._windows_unicode = None
        self._init_once_cache = {}
        self._cdef_version = None
        self._embedding = None
        self._typecache = model.get_typecache(backend)
        if hasattr(backend, 'set_ffi'):
            backend.set_ffi(self)
        for name in list(backend.__dict__):
            if name.startswith('RTLD_'):
                setattr(self, name, getattr(backend, name))
        #
        with self._lock:
            self.BVoidP = self._get_cached_btype(model.voidp_type)
            self.BCharA = self._get_cached_btype(model.char_array_type)
        if isinstance(backend, types.ModuleType):
            # _cffi_backend: attach these constants to the class
            if not hasattr(FFI, 'NULL'):
                FFI.NULL = self.cast(self.BVoidP, 0)
                FFI.CData, FFI.CType = backend._get_types()
        else:
            # ctypes backend: attach these constants to the instance
            self.NULL = self.cast(self.BVoidP, 0)
            self.CData, self.CType = backend._get_types()
        self.buffer = backend.buffer

    def cdef(self, csource, override=False, packed=False, pack=None):
        """Parse the given C source.  This registers all declared functions,
        types, and global variables.  The functions and global variables can
        then be accessed via either 'ffi.dlopen()' or 'ffi.verify()'.
        The types can be used in 'ffi.new()' and other functions.
        If 'packed' is specified as True, all structs declared inside this
        cdef are packed, i.e. laid out without any field alignment at all.
        Alternatively, 'pack' can be a small integer, and requests for
        alignment greater than that are ignored (pack=1 is equivalent to
        packed=True).
        """
        self._cdef(csource, override=override, packed=packed, pack=pack)

    def embedding_api(self, csource, packed=False, pack=None):
        self._cdef(csource, packed=packed, pack=pack, dllexport=True)
        if self._embedding is None:
            self._embedding = ''

    def _cdef(self, csource, override=False, **options):
        if not isinstance(csource, str):    # unicode, on Python 2
            if not isinstance(csource, basestring):
                raise TypeError("cdef() argument must be a string")
            csource = csource.encode('ascii')
        with self._lock:
            self._cdef_version = object()
            self._parser.parse(csource, override=override, **options)
            self._cdefsources.append(csource)
            if override:
                for cache in self._function_caches:
                    cache.clear()
            finishlist = self._parser._recomplete
            if finishlist:
                self._parser._recomplete = []
                for tp in finishlist:
                    tp.finish_backend_type(self, finishlist)

    def dlopen(self, name, flags=0):
        """Load and return a dynamic library identified by 'name'.
        The standard C library can be loaded by passing None.
        Note that functions and types declared by 'ffi.cdef()' are not
        linked to a particular library, just like C headers; in the
        library we only look for the actual (untyped) symbols.
        """
        if not (isinstance(name, basestring) or
                name is None or
                isinstance(name, self.CData)):
            raise TypeError("dlopen(name): name must be a file name, None, "
                            "or an already-opened 'void *' handle")
        with self._lock:
            lib, function_cache = _make_ffi_library(self, name, flags)
            self._function_caches.append(function_cache)
            self._libraries.append(lib)
        return lib

    def dlclose(self, lib):
        """Close a library obtained with ffi.dlopen().  After this call,
        access to functions or variables from the library will fail
        (possibly with a segmentation fault).
        """
        type(lib).__cffi_close__(lib)

    def _typeof_locked(self, cdecl):
        # call me with the lock!
        key = cdecl
        if key in self._parsed_types:
            return self._parsed_types[key]
        #
        if not isinstance(cdecl, str):    # unicode, on Python 2
            cdecl = cdecl.encode('ascii')
        #
        type = self._parser.parse_type(cdecl)
        really_a_function_type = type.is_raw_function
        if really_a_function_type:
            type = type.as_function_pointer()
        btype = self._get_cached_btype(type)
        result = btype, really_a_function_type
        self._parsed_types[key] = result
        return result

    def _typeof(self, cdecl, consider_function_as_funcptr=False):
        # string -> ctype object
        try:
            result = self._parsed_types[cdecl]
        except KeyError:
            with self._lock:
                result = self._typeof_locked(cdecl)
        #
        btype, really_a_function_type = result
        if really_a_function_type and not consider_function_as_funcptr:
            raise CDefError("the type %r is a function type, not a "
                            "pointer-to-function type" % (cdecl,))
        return btype

    def typeof(self, cdecl):
        """Parse the C type given as a string and return the
        corresponding <ctype> object.
        It can also be used on 'cdata' instance to get its C type.
        """
        if isinstance(cdecl, basestring):
            return self._typeof(cdecl)
        if isinstance(cdecl, self.CData):
            return self._backend.typeof(cdecl)
        if isinstance(cdecl, types.BuiltinFunctionType):
            res = _builtin_function_type(cdecl)
            if res is not None:
                return res
        if (isinstance(cdecl, types.FunctionType)
                and hasattr(cdecl, '_cffi_base_type')):
            with self._lock:
                return self._get_cached_btype(cdecl._cffi_base_type)
        raise TypeError(type(cdecl))

    def sizeof(self, cdecl):
        """Return the size in bytes of the argument.  It can be a
        string naming a C type, or a 'cdata' instance.
        """
        if isinstance(cdecl, basestring):
            BType = self._typeof(cdecl)
            return self._backend.sizeof(BType)
        else:
            return self._backend.sizeof(cdecl)

    def alignof(self, cdecl):
        """Return the natural alignment size in bytes of the C type
        given as a string.
        """
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        return self._backend.alignof(cdecl)

    def offsetof(self, cdecl, *fields_or_indexes):
        """Return the offset of the named field inside the given
        structure or array, which must be given as a C type name.
        You can give several field names in case of nested structures.
        You can also give numeric values which correspond to array
        items, in case of an array type.
        """
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        return self._typeoffsetof(cdecl, *fields_or_indexes)[1]

    def new(self, cdecl, init=None):
        """Allocate an instance according to the specified C type and
        return a pointer to it.  The specified C type must be either a
        pointer or an array: ``new('X *')`` allocates an X and returns
        a pointer to it, whereas ``new('X[n]')`` allocates an array of
        n X'es and returns an array referencing it (which works
        mostly like a pointer, like in C).  You can also use
        ``new('X[]', n)`` to allocate an array of a non-constant
        length n.

        The memory is initialized following the rules of declaring a
        global variable in C: by default it is zero-initialized, but
        an explicit initializer can be given which can be used to
        fill all or part of the memory.

        When the returned <cdata> object goes out of scope, the memory
        is freed.  In other words the returned <cdata> object has
        ownership of the value of type 'cdecl' that it points to.  This
        means that the raw data can be used as long as this object is
        kept alive, but must not be used for a longer time.  Be careful
        about that when copying the pointer to the memory somewhere
        else, e.g. into another structure.
        """
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        return self._backend.newp(cdecl, init)

    def new_allocator(self, alloc=None, free=None,
                      should_clear_after_alloc=True):
        """Return a new allocator, i.e. a function that behaves like ffi.new()
        but uses the provided low-level 'alloc' and 'free' functions.

        'alloc' is called with the size as argument.  If it returns NULL, a
        MemoryError is raised.  'free' is called with the result of 'alloc'
        as argument.  Both can be either Python function or directly C
        functions.  If 'free' is None, then no free function is called.
        If both 'alloc' and 'free' are None, the default is used.

        If 'should_clear_after_alloc' is set to False, then the memory
        returned by 'alloc' is assumed to be already cleared (or you are
        fine with garbage); otherwise CFFI will clear it.
        """
        compiled_ffi = self._backend.FFI()
        allocator = compiled_ffi.new_allocator(alloc, free,
                                               should_clear_after_alloc)
        def allocate(cdecl, init=None):
            if isinstance(cdecl, basestring):
                cdecl = self._typeof(cdecl)
            return allocator(cdecl, init)
        return allocate

    def cast(self, cdecl, source):
        """Similar to a C cast: returns an instance of the named C
        type initialized with the given 'source'.  The source is
        casted between integers or pointers of any type.
        """
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        return self._backend.cast(cdecl, source)

    def string(self, cdata, maxlen=-1):
        """Return a Python string (or unicode string) from the 'cdata'.
        If 'cdata' is a pointer or array of characters or bytes, returns
        the null-terminated string.  The returned string extends until
        the first null character, or at most 'maxlen' characters.  If
        'cdata' is an array then 'maxlen' defaults to its length.

        If 'cdata' is a pointer or array of wchar_t, returns a unicode
        string following the same rules.

        If 'cdata' is a single character or byte or a wchar_t, returns
        it as a string or unicode string.

        If 'cdata' is an enum, returns the value of the enumerator as a
        string, or 'NUMBER' if the value is out of range.
        """
        return self._backend.string(cdata, maxlen)

    def unpack(self, cdata, length):
        """Unpack an array of C data of the given length,
        returning a Python string/unicode/list.

        If 'cdata' is a pointer to 'char', returns a byte string.
        It does not stop at the first null.  This is equivalent to:
        ffi.buffer(cdata, length)[:]

        If 'cdata' is a pointer to 'wchar_t', returns a unicode string.
        'length' is measured in wchar_t's; it is not the size in bytes.

        If 'cdata' is a pointer to anything else, returns a list of
        'length' items.  This is a faster equivalent to:
        [cdata[i] for i in range(length)]
        """
        return self._backend.unpack(cdata, length)

   #def buffer(self, cdata, size=-1):
   #    """Return a read-write buffer object that references the raw C data
   #    pointed to by the given 'cdata'.  The 'cdata' must be a pointer or
   #    an array.  Can be passed to functions expecting a buffer, or directly
   #    manipulated with:
   #
   #        buf[:]          get a copy of it in a regular string, or
   #        buf[idx]        as a single character
   #        buf[:] = ...
   #        buf[idx] = ...  change the content
   #    """
   #    note that 'buffer' is a type, set on this instance by __init__

    def from_buffer(self, cdecl, python_buffer=_unspecified,
                    require_writable=False):
        """Return a cdata of the given type pointing to the data of the
        given Python object, which must support the buffer interface.
        Note that this is not meant to be used on the built-in types
        str or unicode (you can build 'char[]' arrays explicitly)
        but only on objects containing large quantities of raw data
        in some other format, like 'array.array' or numpy arrays.

        The first argument is optional and default to 'char[]'.
        """
        if python_buffer is _unspecified:
            cdecl, python_buffer = self.BCharA, cdecl
        elif isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        return self._backend.from_buffer(cdecl, python_buffer,
                                         require_writable)

    def memmove(self, dest, src, n):
        """ffi.memmove(dest, src, n) copies n bytes of memory from src to dest.

        Like the C function memmove(), the memory areas may overlap;
        apart from that it behaves like the C function memcpy().

        'src' can be any cdata ptr or array, or any Python buffer object.
        'dest' can be any cdata ptr or array, or a writable Python buffer
        object.  The size to copy, 'n', is always measured in bytes.

        Unlike other methods, this one supports all Python buffer including
        byte strings and bytearrays---but it still does not support
        non-contiguous buffers.
        """
        return self._backend.memmove(dest, src, n)

    def callback(self, cdecl, python_callable=None, error=None, onerror=None):
        """Return a callback object or a decorator making such a
        callback object.  'cdecl' must name a C function pointer type.
        The callback invokes the specified 'python_callable' (which may
        be provided either directly or via a decorator).  Important: the
        callback object must be manually kept alive for as long as the
        callback may be invoked from the C level.
        """
        def callback_decorator_wrap(python_callable):
            if not callable(python_callable):
                raise TypeError("the 'python_callable' argument "
                                "is not callable")
            return self._backend.callback(cdecl, python_callable,
                                          error, onerror)
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl, consider_function_as_funcptr=True)
        if python_callable is None:
            return callback_decorator_wrap                # decorator mode
        else:
            return callback_decorator_wrap(python_callable)  # direct mode

    def getctype(self, cdecl, replace_with=''):
        """Return a string giving the C type 'cdecl', which may be itself
        a string or a <ctype> object.  If 'replace_with' is given, it gives
        extra text to append (or insert for more complicated C types), like
        a variable name, or '*' to get actually the C type 'pointer-to-cdecl'.
        """
        if isinstance(cdecl, basestring):
            cdecl = self._typeof(cdecl)
        replace_with = replace_with.strip()
        if (replace_with.startswith('*')
                and '&[' in self._backend.getcname(cdecl, '&')):
            replace_with = '(%s)' % replace_with
        elif replace_with and not replace_with[0] in '[(':
            replace_with = ' ' + replace_with
        return self._backend.getcname(cdecl, replace_with)

    def gc(self, cdata, destructor, size=0):
        """Return a new cdata object that points to the same
        data.  Later, when this new cdata object is garbage-collected,
        'destructor(old_cdata_object)' will be called.

        The optional 'size' gives an estimate of the size, used to
        trigger the garbage collection more eagerly.  So far only used
        on PyPy.  It tells the GC that the returned object keeps alive
        roughly 'size' bytes of external memory.
        """
        return self._backend.gcp(cdata, destructor, size)

    def _get_cached_btype(self, type):
        assert self._lock.acquire(False) is False
        # call me with the lock!
        try:
            BType = self._cached_btypes[type]
        except KeyError:
            finishlist = []
            BType = type.get_cached_btype(self, finishlist)
            for type in finishlist:
                type.finish_backend_type(self, finishlist)
        return BType

    def verify(self, source='', tmpdir=None, **kwargs):
        """Verify that the current ffi signatures compile on this
        machine, and return a dynamic library object.  The dynamic
        library can be used to call functions and access global
        variables declared in this 'ffi'.  The library is compiled
        by the C compiler: it gives you C-level API compatibility
        (including calling macros).  This is unlike 'ffi.dlopen()',
        which requires binary compatibility in the signatures.
        """
        from .verifier import Verifier, _caller_dir_pycache
        #
        # If set_unicode(True) was called, insert the UNICODE and
        # _UNICODE macro declarations
        if self._windows_unicode:
            self._apply_windows_unicode(kwargs)
        #
        # Set the tmpdir here, and not in Verifier.__init__: it picks
        # up the caller's directory, which we want to be the caller of
        # ffi.verify(), as opposed to the caller of Veritier().
        tmpdir = tmpdir or _caller_dir_pycache()
        #
        # Make a Verifier() and use it to load the library.
        self.verifier = Verifier(self, source, tmpdir, **kwargs)
        lib = self.verifier.load_library()
        #
        # Save the loaded library for keep-alive purposes, even
        # if the caller doesn't keep it alive itself (it should).
        self._libraries.append(lib)
        return lib

    def _get_errno(self):
        return self._backend.get_errno()
    def _set_errno(self, errno):
        self._backend.set_errno(errno)
    errno = property(_get_errno, _set_errno, None,
                     "the value of 'errno' from/to the C calls")

    def getwinerror(self, code=-1):
        return self._backend.getwinerror(code)

    def _pointer_to(self, ctype):
        with self._lock:
            return model.pointer_cache(self, ctype)

    def addressof(self, cdata, *fields_or_indexes):
        """Return the address of a <cdata 'struct-or-union'>.
        If 'fields_or_indexes' are given, returns the address of that
        field or array item in the structure or array, recursively in
        case of nested structures.
        """
        try:
            ctype = self._backend.typeof(cdata)
        except TypeError:
            if '__addressof__' in type(cdata).__dict__:
                return type(cdata).__addressof__(cdata, *fields_or_indexes)
            raise
        if fields_or_indexes:
            ctype, offset = self._typeoffsetof(ctype, *fields_or_indexes)
        else:
            if ctype.kind == "pointer":
                raise TypeError("addressof(pointer)")
            offset = 0
        ctypeptr = self._pointer_to(ctype)
        return self._backend.rawaddressof(ctypeptr, cdata, offset)

    def _typeoffsetof(self, ctype, field_or_index, *fields_or_indexes):
        ctype, offset = self._backend.typeoffsetof(ctype, field_or_index)
        for field1 in fields_or_indexes:
            ctype, offset1 = self._backend.typeoffsetof(ctype, field1, 1)
            offset += offset1
        return ctype, offset

    def include(self, ffi_to_include):
        """Includes the typedefs, structs, unions and enums defined
        in another FFI instance.  Usage is similar to a #include in C,
        where a part of the program might include types defined in
        another part for its own usage.  Note that the include()
        method has no effect on functions, constants and global
        variables, which must anyway be accessed directly from the
        lib object returned by the original FFI instance.
        """
        if not isinstance(ffi_to_include, FFI):
            raise TypeError("ffi.include() expects an argument that is also of"
                            " type cffi.FFI, not %r" % (
                                type(ffi_to_include).__name__,))
        if ffi_to_include is self:
            raise ValueError("self.include(self)")
        with ffi_to_include._lock:
            with self._lock:
                self._parser.include(ffi_to_include._parser)
                self._cdefsources.append('[')
                self._cdefsources.extend(ffi_to_include._cdefsources)
                self._cdefsources.append(']')
                self._included_ffis.append(ffi_to_include)

    def new_handle(self, x):
        return self._backend.newp_handle(self.BVoidP, x)

    def from_handle(self, x):
        return self._backend.from_handle(x)

    def release(self, x):
        self._backend.release(x)

    def set_unicode(self, enabled_flag):
        """Windows: if 'enabled_flag' is True, enable the UNICODE and
        _UNICODE defines in C, and declare the types like TCHAR and LPTCSTR
        to be (pointers to) wchar_t.  If 'enabled_flag' is False,
        declare these types to be (pointers to) plain 8-bit characters.
        This is mostly for backward compatibility; you usually want True.
        """
        if self._windows_unicode is not None:
            raise ValueError("set_unicode() can only be called once")
        enabled_flag = bool(enabled_flag)
        if enabled_flag:
            self.cdef("typedef wchar_t TBYTE;"
                      "typedef wchar_t TCHAR;"
                      "typedef const wchar_t *LPCTSTR;"
                      "typedef const wchar_t *PCTSTR;"
                      "typedef wchar_t *LPTSTR;"
                      "typedef wchar_t *PTSTR;"
                      "typedef TBYTE *PTBYTE;"
                      "typedef TCHAR *PTCHAR;")
        else:
            self.cdef("typedef char TBYTE;"
                      "typedef char TCHAR;"
                      "typedef const char *LPCTSTR;"
                      "typedef const char *PCTSTR;"
                      "typedef char *LPTSTR;"
                      "typedef char *PTSTR;"
                      "typedef TBYTE *PTBYTE;"
                      "typedef TCHAR *PTCHAR;")
        self._windows_unicode = enabled_flag

    def _apply_windows_unicode(self, kwds):
        defmacros = kwds.get('define_macros', ())
        if not isinstance(defmacros, (list, tuple)):
            raise TypeError("'define_macros' must be a list or tuple")
        defmacros = list(defmacros) + [('UNICODE', '1'),
                                       ('_UNICODE', '1')]
        kwds['define_macros'] = defmacros

    def _apply_embedding_fix(self, kwds):
        # must include an argument like "-lpython2.7" for the compiler
        def ensure(key, value):
            lst = kwds.setdefault(key, [])
            if value not in lst:
                lst.append(value)
        #
        if '__pypy__' in sys.builtin_module_names:
            import os
            if sys.platform == "win32":
                # we need 'libpypy-c.lib'.  Current distributions of
                # pypy (>= 4.1) contain it as 'libs/python27.lib'.
                pythonlib = "python{0[0]}{0[1]}".format(sys.version_info)
                if hasattr(sys, 'prefix'):
                    ensure('library_dirs', os.path.join(sys.prefix, 'libs'))
            else:
                # we need 'libpypy-c.{so,dylib}', which should be by
                # default located in 'sys.prefix/bin' for installed
                # systems.
                if sys.version_info < (3,):
                    pythonlib = "pypy-c"
                else:
                    pythonlib = "pypy3-c"
                if hasattr(sys, 'prefix'):
                    ensure('library_dirs', os.path.join(sys.prefix, 'bin'))
            # On uninstalled pypy's, the libpypy-c is typically found in
            # .../pypy/goal/.
            if hasattr(sys, 'prefix'):
                ensure('library_dirs', os.path.join(sys.prefix, 'pypy', 'goal'))
        else:
            if sys.platform == "win32":
                template = "python%d%d"
                if hasattr(sys, 'gettotalrefcount'):
                    template += '_d'
            else:
                try:
                    import sysconfig
                except ImportError:    # 2.6
                    from cffi._shimmed_dist_utils import sysconfig
                template = "python%d.%d"
                if sysconfig.get_config_var('DEBUG_EXT'):
                    template += sysconfig.get_config_var('DEBUG_EXT')
            pythonlib = (template %
                    (sys.hexversion >> 24, (sys.hexversion >> 16) & 0xff))
            if hasattr(sys, 'abiflags'):
                pythonlib += sys.abiflags
        ensure('libraries', pythonlib)
        if sys.platform == "win32":
            ensure('extra_link_args', '/MANIFEST')

    def set_source(self, module_name, source, source_extension='.c', **kwds):
        import os
        if hasattr(self, '_assigned_source'):
            raise ValueError("set_source() cannot be called several times "
                             "per ffi object")
        if not isinstance(module_name, basestring):
            raise TypeError("'module_name' must be a string")
        if os.sep in module_name or (os.altsep and os.altsep in module_name):
            raise ValueError("'module_name' must not contain '/': use a dotted "
                             "name to make a 'package.module' location")
        self._assigned_source = (str(module_name), source,
                                 source_extension, kwds)

    def set_source_pkgconfig(self, module_name, pkgconfig_libs, source,
                             source_extension='.c', **kwds):
        from . import pkgconfig
        if not isinstance(pkgconfig_libs, list):
            raise TypeError("the pkgconfig_libs argument must be a list "
                            "of package names")
        kwds2 = pkgconfig.flags_from_pkgconfig(pkgconfig_libs)
        pkgconfig.merge_flags(kwds, kwds2)
        self.set_source(module_name, source, source_extension, **kwds)

    def distutils_extension(self, tmpdir='build', verbose=True):
        from cffi._shimmed_dist_utils import mkpath
        from .recompiler import recompile
        #
        if not hasattr(self, '_assigned_source'):
            if hasattr(self, 'verifier'):     # fallback, 'tmpdir' ignored
                return self.verifier.get_extension()
            raise ValueError("set_source() must be called before"
                             " distutils_extension()")
        module_name, source, source_extension, kwds = self._assigned_source
        if source is None:
            raise TypeError("distutils_extension() is only for C extension "
                            "modules, not for dlopen()-style pure Python "
                            "modules")
        mkpath(tmpdir)
        ext, updated = recompile(self, module_name,
                                 source, tmpdir=tmpdir, extradir=tmpdir,
                                 source_extension=source_extension,
                                 call_c_compiler=False, **kwds)
        if verbose:
            if updated:
                sys.stderr.write("regenerated: %r\n" % (ext.sources[0],))
            else:
                sys.stderr.write("not modified: %r\n" % (ext.sources[0],))
        return ext

    def emit_c_code(self, filename):
        from .recompiler import recompile
        #
        if not hasattr(self, '_assigned_source'):
            raise ValueError("set_source() must be called before emit_c_code()")
        module_name, source, source_extension, kwds = self._assigned_source
        if source is None:
            raise TypeError("emit_c_code() is only for C extension modules, "
                            "not for dlopen()-style pure Python modules")
        recompile(self, module_name, source,
                  c_file=filename, call_c_compiler=False,
                  uses_ffiplatform=False, **kwds)

    def emit_python_code(self, filename):
        from .recompiler import recompile
        #
        if not hasattr(self, '_assigned_source'):
            raise ValueError("set_source() must be called before emit_c_code()")
        module_name, source, source_extension, kwds = self._assigned_source
        if source is not None:
            raise TypeError("emit_python_code() is only for dlopen()-style "
                            "pure Python modules, not for C extension modules")
        recompile(self, module_name, source,
                  c_file=filename, call_c_compiler=False,
                  uses_ffiplatform=False, **kwds)

    def compile(self, tmpdir='.', verbose=0, target=None, debug=None):
        """The 'target' argument gives the final file name of the
        compiled DLL.  Use '*' to force distutils' choice, suitable for
        regular CPython C API modules.  Use a file name ending in '.*'
        to ask for the system's default extension for dynamic libraries
        (.so/.dll/.dylib).

        The default is '*' when building a non-embedded C API extension,
        and (module_name + '.*') when building an embedded library.
        """
        from .recompiler import recompile
        #
        if not hasattr(self, '_assigned_source'):
            raise ValueError("set_source() must be called before compile()")
        module_name, source, source_extension, kwds = self._assigned_source
        return recompile(self, module_name, source, tmpdir=tmpdir,
                         target=target, source_extension=source_extension,
                         compiler_verbose=verbose, debug=debug, **kwds)

    def init_once(self, func, tag):
        # Read _init_once_cache[tag], which is either (False, lock) if
        # we're calling the function now in some thread, or (True, result).
        # Don't call setdefault() in most cases, to avoid allocating and
        # immediately freeing a lock; but still use setdefaut() to avoid
        # races.
        try:
            x = self._init_once_cache[tag]
        except KeyError:
            x = self._init_once_cache.setdefault(tag, (False, allocate_lock()))
        # Common case: we got (True, result), so we return the result.
        if x[0]:
            return x[1]
        # Else, it's a lock.  Acquire it to serialize the following tests.
        with x[1]:
            # Read again from _init_once_cache the current status.
            x = self._init_once_cache[tag]
            if x[0]:
                return x[1]
            # Call the function and store the result back.
            result = func()
            self._init_once_cache[tag] = (True, result)
        return result

    def embedding_init_code(self, pysource):
        if self._embedding:
            raise ValueError("embedding_init_code() can only be called once")
        # fix 'pysource' before it gets dumped into the C file:
        # - remove empty lines at the beginning, so it starts at "line 1"
        # - dedent, if all non-empty lines are indented
        # - check for SyntaxErrors
        import re
        match = re.match(r'\s*\n', pysource)
        if match:
            pysource = pysource[match.end():]
        lines = pysource.splitlines() or ['']
        prefix = re.match(r'\s*', lines[0]).group()
        for i in range(1, len(lines)):
            line = lines[i]
            if line.rstrip():
                while not line.startswith(prefix):
                    prefix = prefix[:-1]
        i = len(prefix)
        lines = [line[i:]+'\n' for line in lines]
        pysource = ''.join(lines)
        #
        compile(pysource, "cffi_init", "exec")
        #
        self._embedding = pysource

    def def_extern(self, *args, **kwds):
        raise ValueError("ffi.def_extern() is only available on API-mode FFI "
                         "objects")

    def list_types(self):
        """Returns the user type names known to this FFI instance.
        This returns a tuple containing three lists of names:
        (typedef_names, names_of_structs, names_of_unions)
        """
        typedefs = []
        structs = []
        unions = []
        for key in self._parser._declarations:
            if key.startswith('typedef '):
                typedefs.append(key[8:])
            elif key.startswith('struct '):
                structs.append(key[7:])
            elif key.startswith('union '):
                unions.append(key[6:])
        typedefs.sort()
        structs.sort()
        unions.sort()
        return (typedefs, structs, unions)


def _load_backend_lib(backend, name, flags):
    import os
    if not isinstance(name, basestring):
        if sys.platform != "win32" or name is not None:
            return backend.load_library(name, flags)
        name = "c"    # Windows: load_library(None) fails, but this works
                      # on Python 2 (backward compatibility hack only)
    first_error = None
    if '.' in name or '/' in name or os.sep in name:
        try:
            return backend.load_library(name, flags)
        except OSError as e:
            first_error = e
    import ctypes.util
    path = ctypes.util.find_library(name)
    if path is None:
        if name == "c" and sys.platform == "win32" and sys.version_info >= (3,):
            raise OSError("dlopen(None) cannot work on Windows for Python 3 "
                          "(see http://bugs.python.org/issue23606)")
        msg = ("ctypes.util.find_library() did not manage "
               "to locate a library called %r" % (name,))
        if first_error is not None:
            msg = "%s.  Additionally, %s" % (first_error, msg)
        raise OSError(msg)
    return backend.load_library(path, flags)

def _make_ffi_library(ffi, libname, flags):
    backend = ffi._backend
    backendlib = _load_backend_lib(backend, libname, flags)
    #
    def accessor_function(name):
        key = 'function ' + name
        tp, _ = ffi._parser._declarations[key]
        BType = ffi._get_cached_btype(tp)
        value = backendlib.load_function(BType, name)
        library.__dict__[name] = value
    #
    def accessor_variable(name):
        key = 'variable ' + name
        tp, _ = ffi._parser._declarations[key]
        BType = ffi._get_cached_btype(tp)
        read_variable = backendlib.read_variable
        write_variable = backendlib.write_variable
        setattr(FFILibrary, name, property(
            lambda self: read_variable(BType, name),
            lambda self, value: write_variable(BType, name, value)))
    #
    def addressof_var(name):
        try:
            return addr_variables[name]
        except KeyError:
            with ffi._lock:
                if name not in addr_variables:
                    key = 'variable ' + name
                    tp, _ = ffi._parser._declarations[key]
                    BType = ffi._get_cached_btype(tp)
                    if BType.kind != 'array':
                        BType = model.pointer_cache(ffi, BType)
                    p = backendlib.load_function(BType, name)
                    addr_variables[name] = p
            return addr_variables[name]
    #
    def accessor_constant(name):
        raise NotImplementedError("non-integer constant '%s' cannot be "
                                  "accessed from a dlopen() library" % (name,))
    #
    def accessor_int_constant(name):
        library.__dict__[name] = ffi._parser._int_constants[name]
    #
    accessors = {}
    accessors_version = [False]
    addr_variables = {}
    #
    def update_accessors():
        if accessors_version[0] is ffi._cdef_version:
            return
        #
        for key, (tp, _) in ffi._parser._declarations.items():
            if not isinstance(tp, model.EnumType):
                tag, name = key.split(' ', 1)
                if tag == 'function':
                    accessors[name] = accessor_function
                elif tag == 'variable':
                    accessors[name] = accessor_variable
                elif tag == 'constant':
                    accessors[name] = accessor_constant
            else:
                for i, enumname in enumerate(tp.enumerators):
                    def accessor_enum(name, tp=tp, i=i):
                        tp.check_not_partial()
                        library.__dict__[name] = tp.enumvalues[i]
                    accessors[enumname] = accessor_enum
        for name in ffi._parser._int_constants:
            accessors.setdefault(name, accessor_int_constant)
        accessors_version[0] = ffi._cdef_version
    #
    def make_accessor(name):
        with ffi._lock:
            if name in library.__dict__ or name in FFILibrary.__dict__:
                return    # added by another thread while waiting for the lock
            if name not in accessors:
                update_accessors()
                if name not in accessors:
                    raise AttributeError(name)
            accessors[name](name)
    #
    class FFILibrary(object):
        def __getattr__(self, name):
            make_accessor(name)
            return getattr(self, name)
        def __setattr__(self, name, value):
            try:
                property = getattr(self.__class__, name)
            except AttributeError:
                make_accessor(name)
                setattr(self, name, value)
            else:
                property.__set__(self, value)
        def __dir__(self):
            with ffi._lock:
                update_accessors()
                return accessors.keys()
        def __addressof__(self, name):
            if name in library.__dict__:
                return library.__dict__[name]
            if name in FFILibrary.__dict__:
                return addressof_var(name)
            make_accessor(name)
            if name in library.__dict__:
                return library.__dict__[name]
            if name in FFILibrary.__dict__:
                return addressof_var(name)
            raise AttributeError("cffi library has no function or "
                                 "global variable named '%s'" % (name,))
        def __cffi_close__(self):
            backendlib.close_lib()
            self.__dict__.clear()
    #
    if isinstance(libname, basestring):
        try:
            if not isinstance(libname, str):    # unicode, on Python 2
                libname = libname.encode('utf-8')
            FFILibrary.__name__ = 'FFILibrary_%s' % libname
        except UnicodeError:
            pass
    library = FFILibrary()
    return library, library.__dict__

def _builtin_function_type(func):
    # a hack to make at least ffi.typeof(builtin_function) work,
    # if the builtin function was obtained by 'vengine_cpy'.
    import sys
    try:
        module = sys.modules[func.__module__]
        ffi = module._cffi_original_ffi
        types_of_builtin_funcs = module._cffi_types_of_builtin_funcs
        tp = types_of_builtin_funcs[func]
    except (KeyError, AttributeError, TypeError):
        return None
    else:
        with ffi._lock:
            return ffi._get_cached_btype(tp)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\syntax.py ===
import os.path
import re
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from pip._vendor.pygments.lexer import Lexer
from pip._vendor.pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pip._vendor.pygments.style import Style as PygmentsStyle
from pip._vendor.pygments.styles import get_style_by_name
from pip._vendor.pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
    Whitespace,
)
from pip._vendor.pygments.util import ClassNotFound

from pip._vendor.rich.containers import Lines
from pip._vendor.rich.padding import Padding, PaddingDimensions

from ._loop import loop_first
from .cells import cell_len
from .color import Color, blend_rgb
from .console import Console, ConsoleOptions, JustifyMethod, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment, Segments
from .style import Style, StyleType
from .text import Text

TokenType = Tuple[str, ...]

WINDOWS = sys.platform == "win32"
DEFAULT_THEME = "monokai"

# The following styles are based on https://github.com/pygments/pygments/blob/master/pygments/formatters/terminal.py
# A few modifications were made

ANSI_LIGHT: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="white"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="cyan"),
    Keyword: Style(color="blue"),
    Keyword.Type: Style(color="cyan"),
    Operator.Word: Style(color="magenta"),
    Name.Builtin: Style(color="cyan"),
    Name.Function: Style(color="green"),
    Name.Namespace: Style(color="cyan", underline=True),
    Name.Class: Style(color="green", underline=True),
    Name.Exception: Style(color="cyan"),
    Name.Decorator: Style(color="magenta", bold=True),
    Name.Variable: Style(color="red"),
    Name.Constant: Style(color="red"),
    Name.Attribute: Style(color="cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

ANSI_DARK: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="bright_black"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="bright_cyan"),
    Keyword: Style(color="bright_blue"),
    Keyword.Type: Style(color="bright_cyan"),
    Operator.Word: Style(color="bright_magenta"),
    Name.Builtin: Style(color="bright_cyan"),
    Name.Function: Style(color="bright_green"),
    Name.Namespace: Style(color="bright_cyan", underline=True),
    Name.Class: Style(color="bright_green", underline=True),
    Name.Exception: Style(color="bright_cyan"),
    Name.Decorator: Style(color="bright_magenta", bold=True),
    Name.Variable: Style(color="bright_red"),
    Name.Constant: Style(color="bright_red"),
    Name.Attribute: Style(color="bright_cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="bright_blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="bright_green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="bright_magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

RICH_SYNTAX_THEMES = {"ansi_light": ANSI_LIGHT, "ansi_dark": ANSI_DARK}
NUMBERS_COLUMN_DEFAULT_PADDING = 2


class SyntaxTheme(ABC):
    """Base class for a syntax theme."""

    @abstractmethod
    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style for a given Pygments token."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_background_style(self) -> Style:
        """Get the background color."""
        raise NotImplementedError  # pragma: no cover


class PygmentsSyntaxTheme(SyntaxTheme):
    """Syntax theme that delegates to Pygments theme."""

    def __init__(self, theme: Union[str, Type[PygmentsStyle]]) -> None:
        self._style_cache: Dict[TokenType, Style] = {}
        if isinstance(theme, str):
            try:
                self._pygments_style_class = get_style_by_name(theme)
            except ClassNotFound:
                self._pygments_style_class = get_style_by_name("default")
        else:
            self._pygments_style_class = theme

        self._background_color = self._pygments_style_class.background_color
        self._background_style = Style(bgcolor=self._background_color)

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style from a Pygments class."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            try:
                pygments_style = self._pygments_style_class.style_for_token(token_type)
            except KeyError:
                style = Style.null()
            else:
                color = pygments_style["color"]
                bgcolor = pygments_style["bgcolor"]
                style = Style(
                    color="#" + color if color else "#000000",
                    bgcolor="#" + bgcolor if bgcolor else self._background_color,
                    bold=pygments_style["bold"],
                    italic=pygments_style["italic"],
                    underline=pygments_style["underline"],
                )
            self._style_cache[token_type] = style
        return style

    def get_background_style(self) -> Style:
        return self._background_style


class ANSISyntaxTheme(SyntaxTheme):
    """Syntax theme to use standard colors."""

    def __init__(self, style_map: Dict[TokenType, Style]) -> None:
        self.style_map = style_map
        self._missing_style = Style.null()
        self._background_style = Style.null()
        self._style_cache: Dict[TokenType, Style] = {}

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Look up style in the style map."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            # Styles form a hierarchy
            # We need to go from most to least specific
            # e.g. ("foo", "bar", "baz") to ("foo", "bar")  to ("foo",)
            get_style = self.style_map.get
            token = tuple(token_type)
            style = self._missing_style
            while token:
                _style = get_style(token)
                if _style is not None:
                    style = _style
                    break
                token = token[:-1]
            self._style_cache[token_type] = style
            return style

    def get_background_style(self) -> Style:
        return self._background_style


SyntaxPosition = Tuple[int, int]


class _SyntaxHighlightRange(NamedTuple):
    """
    A range to highlight in a Syntax object.
    `start` and `end` are 2-integers tuples, where the first integer is the line number
    (starting from 1) and the second integer is the column index (starting from 0).
    """

    style: StyleType
    start: SyntaxPosition
    end: SyntaxPosition
    style_before: bool = False


class Syntax(JupyterMixin):
    """Construct a Syntax object to render syntax highlighted code.

    Args:
        code (str): Code to highlight.
        lexer (Lexer | str): Lexer to use (see https://pygments.org/docs/lexers/)
        theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "monokai".
        dedent (bool, optional): Enable stripping of initial whitespace. Defaults to False.
        line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
        start_line (int, optional): Starting number for line numbers. Defaults to 1.
        line_range (Tuple[int | None, int | None], optional): If given should be a tuple of the start and end line to render.
            A value of None in the tuple indicates the range is open in that direction.
        highlight_lines (Set[int]): A set of line numbers to highlight.
        code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
        tab_size (int, optional): Size of tabs. Defaults to 4.
        word_wrap (bool, optional): Enable word wrapping.
        background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
        indent_guides (bool, optional): Show indent guides. Defaults to False.
        padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).
    """

    _pygments_style_class: Type[PygmentsStyle]
    _theme: SyntaxTheme

    @classmethod
    def get_theme(cls, name: Union[str, SyntaxTheme]) -> SyntaxTheme:
        """Get a syntax theme instance."""
        if isinstance(name, SyntaxTheme):
            return name
        theme: SyntaxTheme
        if name in RICH_SYNTAX_THEMES:
            theme = ANSISyntaxTheme(RICH_SYNTAX_THEMES[name])
        else:
            theme = PygmentsSyntaxTheme(name)
        return theme

    def __init__(
        self,
        code: str,
        lexer: Union[Lexer, str],
        *,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        start_line: int = 1,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> None:
        self.code = code
        self._lexer = lexer
        self.dedent = dedent
        self.line_numbers = line_numbers
        self.start_line = start_line
        self.line_range = line_range
        self.highlight_lines = highlight_lines or set()
        self.code_width = code_width
        self.tab_size = tab_size
        self.word_wrap = word_wrap
        self.background_color = background_color
        self.background_style = (
            Style(bgcolor=background_color) if background_color else Style()
        )
        self.indent_guides = indent_guides
        self.padding = padding

        self._theme = self.get_theme(theme)
        self._stylized_ranges: List[_SyntaxHighlightRange] = []

    @classmethod
    def from_path(
        cls,
        path: str,
        encoding: str = "utf-8",
        lexer: Optional[Union[Lexer, str]] = None,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        line_range: Optional[Tuple[int, int]] = None,
        start_line: int = 1,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> "Syntax":
        """Construct a Syntax object from a file.

        Args:
            path (str): Path to file to highlight.
            encoding (str): Encoding of file.
            lexer (str | Lexer, optional): Lexer to use. If None, lexer will be auto-detected from path/file content.
            theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "emacs".
            dedent (bool, optional): Enable stripping of initial whitespace. Defaults to True.
            line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
            start_line (int, optional): Starting number for line numbers. Defaults to 1.
            line_range (Tuple[int, int], optional): If given should be a tuple of the start and end line to render.
            highlight_lines (Set[int]): A set of line numbers to highlight.
            code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
            tab_size (int, optional): Size of tabs. Defaults to 4.
            word_wrap (bool, optional): Enable word wrapping of code.
            background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
            indent_guides (bool, optional): Show indent guides. Defaults to False.
            padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).

        Returns:
            [Syntax]: A Syntax object that may be printed to the console
        """
        code = Path(path).read_text(encoding=encoding)

        if not lexer:
            lexer = cls.guess_lexer(path, code=code)

        return cls(
            code,
            lexer,
            theme=theme,
            dedent=dedent,
            line_numbers=line_numbers,
            line_range=line_range,
            start_line=start_line,
            highlight_lines=highlight_lines,
            code_width=code_width,
            tab_size=tab_size,
            word_wrap=word_wrap,
            background_color=background_color,
            indent_guides=indent_guides,
            padding=padding,
        )

    @classmethod
    def guess_lexer(cls, path: str, code: Optional[str] = None) -> str:
        """Guess the alias of the Pygments lexer to use based on a path and an optional string of code.
        If code is supplied, it will use a combination of the code and the filename to determine the
        best lexer to use. For example, if the file is ``index.html`` and the file contains Django
        templating syntax, then "html+django" will be returned. If the file is ``index.html``, and no
        templating language is used, the "html" lexer will be used. If no string of code
        is supplied, the lexer will be chosen based on the file extension..

        Args:
             path (AnyStr): The path to the file containing the code you wish to know the lexer for.
             code (str, optional): Optional string of code that will be used as a fallback if no lexer
                is found for the supplied path.

        Returns:
            str: The name of the Pygments lexer that best matches the supplied path/code.
        """
        lexer: Optional[Lexer] = None
        lexer_name = "default"
        if code:
            try:
                lexer = guess_lexer_for_filename(path, code)
            except ClassNotFound:
                pass

        if not lexer:
            try:
                _, ext = os.path.splitext(path)
                if ext:
                    extension = ext.lstrip(".").lower()
                    lexer = get_lexer_by_name(extension)
            except ClassNotFound:
                pass

        if lexer:
            if lexer.aliases:
                lexer_name = lexer.aliases[0]
            else:
                lexer_name = lexer.name

        return lexer_name

    def _get_base_style(self) -> Style:
        """Get the base style."""
        default_style = self._theme.get_background_style() + self.background_style
        return default_style

    def _get_token_color(self, token_type: TokenType) -> Optional[Color]:
        """Get a color (if any) for the given token.

        Args:
            token_type (TokenType): A token type tuple from Pygments.

        Returns:
            Optional[Color]: Color from theme, or None for no color.
        """
        style = self._theme.get_style_for_token(token_type)
        return style.color

    @property
    def lexer(self) -> Optional[Lexer]:
        """The lexer for this syntax, or None if no lexer was found.

        Tries to find the lexer by name if a string was passed to the constructor.
        """

        if isinstance(self._lexer, Lexer):
            return self._lexer
        try:
            return get_lexer_by_name(
                self._lexer,
                stripnl=False,
                ensurenl=True,
                tabsize=self.tab_size,
            )
        except ClassNotFound:
            return None

    @property
    def default_lexer(self) -> Lexer:
        """A Pygments Lexer to use if one is not specified or invalid."""
        return get_lexer_by_name(
            "text",
            stripnl=False,
            ensurenl=True,
            tabsize=self.tab_size,
        )

    def highlight(
        self,
        code: str,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
    ) -> Text:
        """Highlight code and return a Text instance.

        Args:
            code (str): Code to highlight.
            line_range(Tuple[int, int], optional): Optional line range to highlight.

        Returns:
            Text: A text instance containing highlighted syntax.
        """

        base_style = self._get_base_style()
        justify: JustifyMethod = (
            "default" if base_style.transparent_background else "left"
        )

        text = Text(
            justify=justify,
            style=base_style,
            tab_size=self.tab_size,
            no_wrap=not self.word_wrap,
        )
        _get_theme_style = self._theme.get_style_for_token

        lexer = self.lexer or self.default_lexer

        if lexer is None:
            text.append(code)
        else:
            if line_range:
                # More complicated path to only stylize a portion of the code
                # This speeds up further operations as there are less spans to process
                line_start, line_end = line_range

                def line_tokenize() -> Iterable[Tuple[Any, str]]:
                    """Split tokens to one per line."""
                    assert lexer  # required to make MyPy happy - we know lexer is not None at this point

                    for token_type, token in lexer.get_tokens(code):
                        while token:
                            line_token, new_line, token = token.partition("\n")
                            yield token_type, line_token + new_line

                def tokens_to_spans() -> Iterable[Tuple[str, Optional[Style]]]:
                    """Convert tokens to spans."""
                    tokens = iter(line_tokenize())
                    line_no = 0
                    _line_start = line_start - 1 if line_start else 0

                    # Skip over tokens until line start
                    while line_no < _line_start:
                        try:
                            _token_type, token = next(tokens)
                        except StopIteration:
                            break
                        yield (token, None)
                        if token.endswith("\n"):
                            line_no += 1
                    # Generate spans until line end
                    for token_type, token in tokens:
                        yield (token, _get_theme_style(token_type))
                        if token.endswith("\n"):
                            line_no += 1
                            if line_end and line_no >= line_end:
                                break

                text.append_tokens(tokens_to_spans())

            else:
                text.append_tokens(
                    (token, _get_theme_style(token_type))
                    for token_type, token in lexer.get_tokens(code)
                )
            if self.background_color is not None:
                text.stylize(f"on {self.background_color}")

        if self._stylized_ranges:
            self._apply_stylized_ranges(text)

        return text

    def stylize_range(
        self,
        style: StyleType,
        start: SyntaxPosition,
        end: SyntaxPosition,
        style_before: bool = False,
    ) -> None:
        """
        Adds a custom style on a part of the code, that will be applied to the syntax display when it's rendered.
        Line numbers are 1-based, while column indexes are 0-based.

        Args:
            style (StyleType): The style to apply.
            start (Tuple[int, int]): The start of the range, in the form `[line number, column index]`.
            end (Tuple[int, int]): The end of the range, in the form `[line number, column index]`.
            style_before (bool): Apply the style before any existing styles.
        """
        self._stylized_ranges.append(
            _SyntaxHighlightRange(style, start, end, style_before)
        )

    def _get_line_numbers_color(self, blend: float = 0.3) -> Color:
        background_style = self._theme.get_background_style() + self.background_style
        background_color = background_style.bgcolor
        if background_color is None or background_color.is_system_defined:
            return Color.default()
        foreground_color = self._get_token_color(Token.Text)
        if foreground_color is None or foreground_color.is_system_defined:
            return foreground_color or Color.default()
        new_color = blend_rgb(
            background_color.get_truecolor(),
            foreground_color.get_truecolor(),
            cross_fade=blend,
        )
        return Color.from_triplet(new_color)

    @property
    def _numbers_column_width(self) -> int:
        """Get the number of characters used to render the numbers column."""
        column_width = 0
        if self.line_numbers:
            column_width = (
                len(str(self.start_line + self.code.count("\n")))
                + NUMBERS_COLUMN_DEFAULT_PADDING
            )
        return column_width

    def _get_number_styles(self, console: Console) -> Tuple[Style, Style, Style]:
        """Get background, number, and highlight styles for line numbers."""
        background_style = self._get_base_style()
        if background_style.transparent_background:
            return Style.null(), Style(dim=True), Style.null()
        if console.color_system in ("256", "truecolor"):
            number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(color=self._get_line_numbers_color()),
                self.background_style,
            )
            highlight_number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(bold=True, color=self._get_line_numbers_color(0.9)),
                self.background_style,
            )
        else:
            number_style = background_style + Style(dim=True)
            highlight_number_style = background_style + Style(dim=False)
        return background_style, number_style, highlight_number_style

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        if self.code_width is not None:
            width = self.code_width + self._numbers_column_width + padding + 1
            return Measurement(self._numbers_column_width, width)
        lines = self.code.splitlines()
        width = (
            self._numbers_column_width
            + padding
            + (max(cell_len(line) for line in lines) if lines else 0)
        )
        if self.line_numbers:
            width += 1
        return Measurement(self._numbers_column_width, width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        segments = Segments(self._get_syntax(console, options))
        if self.padding:
            yield Padding(segments, style=self._get_base_style(), pad=self.padding)
        else:
            yield segments

    def _get_syntax(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> Iterable[Segment]:
        """
        Get the Segments for the Syntax object, excluding any vertical/horizontal padding
        """
        transparent_background = self._get_base_style().transparent_background
        code_width = (
            (
                (options.max_width - self._numbers_column_width - 1)
                if self.line_numbers
                else options.max_width
            )
            if self.code_width is None
            else self.code_width
        )

        ends_on_nl, processed_code = self._process_code(self.code)
        text = self.highlight(processed_code, self.line_range)

        if not self.line_numbers and not self.word_wrap and not self.line_range:
            if not ends_on_nl:
                text.remove_suffix("\n")
            # Simple case of just rendering text
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            if self.indent_guides and not options.ascii_only:
                text = text.with_indent_guides(self.tab_size, style=style)
                text.overflow = "crop"
            if style.transparent_background:
                yield from console.render(
                    text, options=options.update(width=code_width)
                )
            else:
                syntax_lines = console.render_lines(
                    text,
                    options.update(width=code_width, height=None, justify="left"),
                    style=self.background_style,
                    pad=True,
                    new_lines=True,
                )
                for syntax_line in syntax_lines:
                    yield from syntax_line
            return

        start_line, end_line = self.line_range or (None, None)
        line_offset = 0
        if start_line:
            line_offset = max(0, start_line - 1)
        lines: Union[List[Text], Lines] = text.split("\n", allow_blank=ends_on_nl)
        if self.line_range:
            if line_offset > len(lines):
                return
            lines = lines[line_offset:end_line]

        if self.indent_guides and not options.ascii_only:
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            lines = (
                Text("\n")
                .join(lines)
                .with_indent_guides(self.tab_size, style=style + Style(italic=False))
                .split("\n", allow_blank=True)
            )

        numbers_column_width = self._numbers_column_width
        render_options = options.update(width=code_width)

        highlight_line = self.highlight_lines.__contains__
        _Segment = Segment
        new_line = _Segment("\n")

        line_pointer = "> " if options.legacy_windows else "❱ "

        (
            background_style,
            number_style,
            highlight_number_style,
        ) = self._get_number_styles(console)

        for line_no, line in enumerate(lines, self.start_line + line_offset):
            if self.word_wrap:
                wrapped_lines = console.render_lines(
                    line,
                    render_options.update(height=None, justify="left"),
                    style=background_style,
                    pad=not transparent_background,
                )
            else:
                segments = list(line.render(console, end=""))
                if options.no_wrap:
                    wrapped_lines = [segments]
                else:
                    wrapped_lines = [
                        _Segment.adjust_line_length(
                            segments,
                            render_options.max_width,
                            style=background_style,
                            pad=not transparent_background,
                        )
                    ]

            if self.line_numbers:
                wrapped_line_left_pad = _Segment(
                    " " * numbers_column_width + " ", background_style
                )
                for first, wrapped_line in loop_first(wrapped_lines):
                    if first:
                        line_column = str(line_no).rjust(numbers_column_width - 2) + " "
                        if highlight_line(line_no):
                            yield _Segment(line_pointer, Style(color="red"))
                            yield _Segment(line_column, highlight_number_style)
                        else:
                            yield _Segment("  ", highlight_number_style)
                            yield _Segment(line_column, number_style)
                    else:
                        yield wrapped_line_left_pad
                    yield from wrapped_line
                    yield new_line
            else:
                for wrapped_line in wrapped_lines:
                    yield from wrapped_line
                    yield new_line

    def _apply_stylized_ranges(self, text: Text) -> None:
        """
        Apply stylized ranges to a text instance,
        using the given code to determine the right portion to apply the style to.

        Args:
            text (Text): Text instance to apply the style to.
        """
        code = text.plain
        newlines_offsets = [
            # Let's add outer boundaries at each side of the list:
            0,
            # N.B. using "\n" here is much faster than using metacharacters such as "^" or "\Z":
            *[
                match.start() + 1
                for match in re.finditer("\n", code, flags=re.MULTILINE)
            ],
            len(code) + 1,
        ]

        for stylized_range in self._stylized_ranges:
            start = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.start
            )
            end = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.end
            )
            if start is not None and end is not None:
                if stylized_range.style_before:
                    text.stylize_before(stylized_range.style, start, end)
                else:
                    text.stylize(stylized_range.style, start, end)

    def _process_code(self, code: str) -> Tuple[bool, str]:
        """
        Applies various processing to a raw code string
        (normalises it so it always ends with a line return, dedents it if necessary, etc.)

        Args:
            code (str): The raw code string to process

        Returns:
            Tuple[bool, str]: the boolean indicates whether the raw code ends with a line return,
                while the string is the processed code.
        """
        ends_on_nl = code.endswith("\n")
        processed_code = code if ends_on_nl else code + "\n"
        processed_code = (
            textwrap.dedent(processed_code) if self.dedent else processed_code
        )
        processed_code = processed_code.expandtabs(self.tab_size)
        return ends_on_nl, processed_code


def _get_code_index_for_syntax_position(
    newlines_offsets: Sequence[int], position: SyntaxPosition
) -> Optional[int]:
    """
    Returns the index of the code string for the given positions.

    Args:
        newlines_offsets (Sequence[int]): The offset of each newline character found in the code snippet.
        position (SyntaxPosition): The position to search for.

    Returns:
        Optional[int]: The index of the code string for this position, or `None`
            if the given position's line number is out of range (if it's the column that is out of range
            we silently clamp its value so that it reaches the end of the line)
    """
    lines_count = len(newlines_offsets)

    line_number, column_index = position
    if line_number > lines_count or len(newlines_offsets) < (line_number + 1):
        return None  # `line_number` is out of range
    line_index = line_number - 1
    line_length = newlines_offsets[line_index + 1] - newlines_offsets[line_index] - 1
    # If `column_index` is out of range: let's silently clamp it:
    column_index = min(line_length, column_index)
    return newlines_offsets[line_index] + column_index


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Render syntax to the console with Rich"
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-c",
        "--force-color",
        dest="force_color",
        action="store_true",
        default=None,
        help="force color for non-terminals",
    )
    parser.add_argument(
        "-i",
        "--indent-guides",
        dest="indent_guides",
        action="store_true",
        default=False,
        help="display indent guides",
    )
    parser.add_argument(
        "-l",
        "--line-numbers",
        dest="line_numbers",
        action="store_true",
        help="render line numbers",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        dest="width",
        default=None,
        help="width of output (default will auto-detect)",
    )
    parser.add_argument(
        "-r",
        "--wrap",
        dest="word_wrap",
        action="store_true",
        default=False,
        help="word wrap long lines",
    )
    parser.add_argument(
        "-s",
        "--soft-wrap",
        action="store_true",
        dest="soft_wrap",
        default=False,
        help="enable soft wrapping mode",
    )
    parser.add_argument(
        "-t", "--theme", dest="theme", default="monokai", help="pygments theme"
    )
    parser.add_argument(
        "-b",
        "--background-color",
        dest="background_color",
        default=None,
        help="Override background color",
    )
    parser.add_argument(
        "-x",
        "--lexer",
        default=None,
        dest="lexer_name",
        help="Lexer name",
    )
    parser.add_argument(
        "-p", "--padding", type=int, default=0, dest="padding", help="Padding"
    )
    parser.add_argument(
        "--highlight-line",
        type=int,
        default=None,
        dest="highlight_line",
        help="The line number (not index!) to highlight",
    )
    args = parser.parse_args()

    from pip._vendor.rich.console import Console

    console = Console(force_terminal=args.force_color, width=args.width)

    if args.path == "-":
        code = sys.stdin.read()
        syntax = Syntax(
            code=code,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    else:
        syntax = Syntax.from_path(
            args.path,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    console.print(syntax, soft_wrap=args.soft_wrap)