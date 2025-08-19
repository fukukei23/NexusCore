
# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_webhooks_server.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
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
"""Contains `WebhooksServer` and `webhook_endpoint` to create a webhook server easily."""

import atexit
import inspect
import os
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from .utils import experimental, is_fastapi_available, is_gradio_available


if TYPE_CHECKING:
    import gradio as gr
    from fastapi import Request

if is_fastapi_available():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
else:
    # Will fail at runtime if FastAPI is not available
    FastAPI = Request = JSONResponse = None  # type: ignore [misc, assignment]


_global_app: Optional["WebhooksServer"] = None
_is_local = os.environ.get("SPACE_ID") is None


@experimental
class WebhooksServer:
    """
    The [`WebhooksServer`] class lets you create an instance of a Gradio app that can receive Huggingface webhooks.
    These webhooks can be registered using the [`~WebhooksServer.add_webhook`] decorator. Webhook endpoints are added to
    the app as a POST endpoint to the FastAPI router. Once all the webhooks are registered, the `launch` method has to be
    called to start the app.

    It is recommended to accept [`WebhookPayload`] as the first argument of the webhook function. It is a Pydantic
    model that contains all the information about the webhook event. The data will be parsed automatically for you.

    Check out the [webhooks guide](../guides/webhooks_server) for a step-by-step tutorial on how to setup your
    WebhooksServer and deploy it on a Space.

    <Tip warning={true}>

    `WebhooksServer` is experimental. Its API is subject to change in the future.

    </Tip>

    <Tip warning={true}>

    You must have `gradio` installed to use `WebhooksServer` (`pip install --upgrade gradio`).

    </Tip>

    Args:
        ui (`gradio.Blocks`, optional):
            A Gradio UI instance to be used as the Space landing page. If `None`, a UI displaying instructions
            about the configured webhooks is created.
        webhook_secret (`str`, optional):
            A secret key to verify incoming webhook requests. You can set this value to any secret you want as long as
            you also configure it in your [webhooks settings panel](https://huggingface.co/settings/webhooks). You
            can also set this value as the `WEBHOOK_SECRET` environment variable. If no secret is provided, the
            webhook endpoints are opened without any security.

    Example:

        ```python
        import gradio as gr
        from huggingface_hub import WebhooksServer, WebhookPayload

        with gr.Blocks() as ui:
            ...

        app = WebhooksServer(ui=ui, webhook_secret="my_secret_key")

        @app.add_webhook("/say_hello")
        async def hello(payload: WebhookPayload):
            return {"message": "hello"}

        app.launch()
        ```
    """

    def __new__(cls, *args, **kwargs) -> "WebhooksServer":
        if not is_gradio_available():
            raise ImportError(
                "You must have `gradio` installed to use `WebhooksServer`. Please run `pip install --upgrade gradio`"
                " first."
            )
        if not is_fastapi_available():
            raise ImportError(
                "You must have `fastapi` installed to use `WebhooksServer`. Please run `pip install --upgrade fastapi`"
                " first."
            )
        return super().__new__(cls)

    def __init__(
        self,
        ui: Optional["gr.Blocks"] = None,
        webhook_secret: Optional[str] = None,
    ) -> None:
        self._ui = ui

        self.webhook_secret = webhook_secret or os.getenv("WEBHOOK_SECRET")
        self.registered_webhooks: Dict[str, Callable] = {}
        _warn_on_empty_secret(self.webhook_secret)

    def add_webhook(self, path: Optional[str] = None) -> Callable:
        """
        Decorator to add a webhook to the [`WebhooksServer`] server.

        Args:
            path (`str`, optional):
                The URL path to register the webhook function. If not provided, the function name will be used as the
                path. In any case, all webhooks are registered under `/webhooks`.

        Raises:
            ValueError: If the provided path is already registered as a webhook.

        Example:
            ```python
            from huggingface_hub import WebhooksServer, WebhookPayload

            app = WebhooksServer()

            @app.add_webhook
            async def trigger_training(payload: WebhookPayload):
                if payload.repo.type == "dataset" and payload.event.action == "update":
                    # Trigger a training job if a dataset is updated
                    ...

            app.launch()
        ```
        """
        # Usage: directly as decorator. Example: `@app.add_webhook`
        if callable(path):
            # If path is a function, it means it was used as a decorator without arguments
            return self.add_webhook()(path)

        # Usage: provide a path. Example: `@app.add_webhook(...)`
        @wraps(FastAPI.post)
        def _inner_post(*args, **kwargs):
            func = args[0]
            abs_path = f"/webhooks/{(path or func.__name__).strip('/')}"
            if abs_path in self.registered_webhooks:
                raise ValueError(f"Webhook {abs_path} already exists.")
            self.registered_webhooks[abs_path] = func

        return _inner_post

    def launch(self, prevent_thread_lock: bool = False, **launch_kwargs: Any) -> None:
        """Launch the Gradio app and register webhooks to the underlying FastAPI server.

        Input parameters are forwarded to Gradio when launching the app.
        """
        ui = self._ui or self._get_default_ui()

        # Start Gradio App
        #   - as non-blocking so that webhooks can be added afterwards
        #   - as shared if launch locally (to debug webhooks)
        launch_kwargs.setdefault("share", _is_local)
        self.fastapi_app, _, _ = ui.launch(prevent_thread_lock=True, **launch_kwargs)

        # Register webhooks to FastAPI app
        for path, func in self.registered_webhooks.items():
            # Add secret check if required
            if self.webhook_secret is not None:
                func = _wrap_webhook_to_check_secret(func, webhook_secret=self.webhook_secret)

            # Add route to FastAPI app
            self.fastapi_app.post(path)(func)

        # Print instructions and block main thread
        space_host = os.environ.get("SPACE_HOST")
        url = "https://" + space_host if space_host is not None else (ui.share_url or ui.local_url)
        if url is None:
            raise ValueError("Cannot find the URL of the app. Please provide a valid `ui` or update `gradio` version.")
        url = url.strip("/")
        message = "\nWebhooks are correctly setup and ready to use:"
        message += "\n" + "\n".join(f"  - POST {url}{webhook}" for webhook in self.registered_webhooks)
        message += "\nGo to https://huggingface.co/settings/webhooks to setup your webhooks."
        print(message)

        if not prevent_thread_lock:
            ui.block_thread()

    def _get_default_ui(self) -> "gr.Blocks":
        """Default UI if not provided (lists webhooks and provides basic instructions)."""
        import gradio as gr

        with gr.Blocks() as ui:
            gr.Markdown("# This is an app to process 🤗 Webhooks")
            gr.Markdown(
                "Webhooks are a foundation for MLOps-related features. They allow you to listen for new changes on"
                " specific repos or to all repos belonging to particular set of users/organizations (not just your"
                " repos, but any repo). Check out this [guide](https://huggingface.co/docs/hub/webhooks) to get to"
                " know more about webhooks on the Huggingface Hub."
            )
            gr.Markdown(
                f"{len(self.registered_webhooks)} webhook(s) are registered:"
                + "\n\n"
                + "\n ".join(
                    f"- [{webhook_path}]({_get_webhook_doc_url(webhook.__name__, webhook_path)})"
                    for webhook_path, webhook in self.registered_webhooks.items()
                )
            )
            gr.Markdown(
                "Go to https://huggingface.co/settings/webhooks to setup your webhooks."
                + "\nYou app is running locally. Please look at the logs to check the full URL you need to set."
                if _is_local
                else (
                    "\nThis app is running on a Space. You can find the corresponding URL in the options menu"
                    " (top-right) > 'Embed the Space'. The URL looks like 'https://{username}-{repo_name}.hf.space'."
                )
            )
        return ui


@experimental
def webhook_endpoint(path: Optional[str] = None) -> Callable:
    """Decorator to start a [`WebhooksServer`] and register the decorated function as a webhook endpoint.

    This is a helper to get started quickly. If you need more flexibility (custom landing page or webhook secret),
    you can use [`WebhooksServer`] directly. You can register multiple webhook endpoints (to the same server) by using
    this decorator multiple times.

    Check out the [webhooks guide](../guides/webhooks_server) for a step-by-step tutorial on how to setup your
    server and deploy it on a Space.

    <Tip warning={true}>

    `webhook_endpoint` is experimental. Its API is subject to change in the future.

    </Tip>

    <Tip warning={true}>

    You must have `gradio` installed to use `webhook_endpoint` (`pip install --upgrade gradio`).

    </Tip>

    Args:
        path (`str`, optional):
            The URL path to register the webhook function. If not provided, the function name will be used as the path.
            In any case, all webhooks are registered under `/webhooks`.

    Examples:
        The default usage is to register a function as a webhook endpoint. The function name will be used as the path.
        The server will be started automatically at exit (i.e. at the end of the script).

        ```python
        from huggingface_hub import webhook_endpoint, WebhookPayload

        @webhook_endpoint
        async def trigger_training(payload: WebhookPayload):
            if payload.repo.type == "dataset" and payload.event.action == "update":
                # Trigger a training job if a dataset is updated
                ...

        # Server is automatically started at the end of the script.
        ```

        Advanced usage: register a function as a webhook endpoint and start the server manually. This is useful if you
        are running it in a notebook.

        ```python
        from huggingface_hub import webhook_endpoint, WebhookPayload

        @webhook_endpoint
        async def trigger_training(payload: WebhookPayload):
            if payload.repo.type == "dataset" and payload.event.action == "update":
                # Trigger a training job if a dataset is updated
                ...

        # Start the server manually
        trigger_training.launch()
        ```
    """
    if callable(path):
        # If path is a function, it means it was used as a decorator without arguments
        return webhook_endpoint()(path)

    @wraps(WebhooksServer.add_webhook)
    def _inner(func: Callable) -> Callable:
        app = _get_global_app()
        app.add_webhook(path)(func)
        if len(app.registered_webhooks) == 1:
            # Register `app.launch` to run at exit (only once)
            atexit.register(app.launch)

        @wraps(app.launch)
        def _launch_now():
            # Run the app directly (without waiting atexit)
            atexit.unregister(app.launch)
            app.launch()

        func.launch = _launch_now  # type: ignore
        return func

    return _inner


def _get_global_app() -> WebhooksServer:
    global _global_app
    if _global_app is None:
        _global_app = WebhooksServer()
    return _global_app


def _warn_on_empty_secret(webhook_secret: Optional[str]) -> None:
    if webhook_secret is None:
        print("Webhook secret is not defined. This means your webhook endpoints will be open to everyone.")
        print(
            "To add a secret, set `WEBHOOK_SECRET` as environment variable or pass it at initialization: "
            "\n\t`app = WebhooksServer(webhook_secret='my_secret', ...)`"
        )
        print(
            "For more details about webhook secrets, please refer to"
            " https://huggingface.co/docs/hub/webhooks#webhook-secret."
        )
    else:
        print("Webhook secret is correctly defined.")


def _get_webhook_doc_url(webhook_name: str, webhook_path: str) -> str:
    """Returns the anchor to a given webhook in the docs (experimental)"""
    return "/docs#/default/" + webhook_name + webhook_path.replace("/", "_") + "_post"


def _wrap_webhook_to_check_secret(func: Callable, webhook_secret: str) -> Callable:
    """Wraps a webhook function to check the webhook secret before calling the function.

    This is a hacky way to add the `request` parameter to the function signature. Since FastAPI based itself on route
    parameters to inject the values to the function, we need to hack the function signature to retrieve the `Request`
    object (and hence the headers). A far cleaner solution would be to use a middleware. However, since
    `fastapi==0.90.1`, a middleware cannot be added once the app has started. And since the FastAPI app is started by
    Gradio internals (and not by us), we cannot add a middleware.

    This method is called only when a secret has been defined by the user. If a request is sent without the
    "x-webhook-secret", the function will return a 401 error (unauthorized). If the header is sent but is incorrect,
    the function will return a 403 error (forbidden).

    Inspired by https://stackoverflow.com/a/33112180.
    """
    initial_sig = inspect.signature(func)

    @wraps(func)
    async def _protected_func(request: Request, **kwargs):
        request_secret = request.headers.get("x-webhook-secret")
        if request_secret is None:
            return JSONResponse({"error": "x-webhook-secret header not set."}, status_code=401)
        if request_secret != webhook_secret:
            return JSONResponse({"error": "Invalid webhook secret."}, status_code=403)

        # Inject `request` in kwargs if required
        if "request" in initial_sig.parameters:
            kwargs["request"] = request

        # Handle both sync and async routes
        if inspect.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return func(**kwargs)

    # Update signature to include request
    if "request" not in initial_sig.parameters:
        _protected_func.__signature__ = initial_sig.replace(  # type: ignore
            parameters=(
                inspect.Parameter(name="request", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            )
            + tuple(initial_sig.parameters.values())
        )

    # Return protected route
    return _protected_func

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\instancer\names.py ===
"""Helpers for instantiating name table records."""

from contextlib import contextmanager
from copy import deepcopy
from enum import IntEnum
import re


class NameID(IntEnum):
    FAMILY_NAME = 1
    SUBFAMILY_NAME = 2
    UNIQUE_FONT_IDENTIFIER = 3
    FULL_FONT_NAME = 4
    VERSION_STRING = 5
    POSTSCRIPT_NAME = 6
    TYPOGRAPHIC_FAMILY_NAME = 16
    TYPOGRAPHIC_SUBFAMILY_NAME = 17
    VARIATIONS_POSTSCRIPT_NAME_PREFIX = 25


ELIDABLE_AXIS_VALUE_NAME = 2


def getVariationNameIDs(varfont):
    used = []
    if "fvar" in varfont:
        fvar = varfont["fvar"]
        for axis in fvar.axes:
            used.append(axis.axisNameID)
        for instance in fvar.instances:
            used.append(instance.subfamilyNameID)
            if instance.postscriptNameID != 0xFFFF:
                used.append(instance.postscriptNameID)
    if "STAT" in varfont:
        stat = varfont["STAT"].table
        for axis in stat.DesignAxisRecord.Axis if stat.DesignAxisRecord else ():
            used.append(axis.AxisNameID)
        for value in stat.AxisValueArray.AxisValue if stat.AxisValueArray else ():
            used.append(value.ValueNameID)
        elidedFallbackNameID = getattr(stat, "ElidedFallbackNameID", None)
        if elidedFallbackNameID is not None:
            used.append(elidedFallbackNameID)
    # nameIDs <= 255 are reserved by OT spec so we don't touch them
    return {nameID for nameID in used if nameID > 255}


@contextmanager
def pruningUnusedNames(varfont):
    from . import log

    origNameIDs = getVariationNameIDs(varfont)

    yield

    log.info("Pruning name table")
    exclude = origNameIDs - getVariationNameIDs(varfont)
    varfont["name"].names[:] = [
        record for record in varfont["name"].names if record.nameID not in exclude
    ]
    if "ltag" in varfont:
        # Drop the whole 'ltag' table if all the language-dependent Unicode name
        # records that reference it have been dropped.
        # TODO: Only prune unused ltag tags, renumerating langIDs accordingly.
        # Note ltag can also be used by feat or morx tables, so check those too.
        if not any(
            record
            for record in varfont["name"].names
            if record.platformID == 0 and record.langID != 0xFFFF
        ):
            del varfont["ltag"]


def updateNameTable(varfont, axisLimits):
    """Update instatiated variable font's name table using STAT AxisValues.

    Raises ValueError if the STAT table is missing or an Axis Value table is
    missing for requested axis locations.

    First, collect all STAT AxisValues that match the new default axis locations
    (excluding "elided" ones); concatenate the strings in design axis order,
    while giving priority to "synthetic" values (Format 4), to form the
    typographic subfamily name associated with the new default instance.
    Finally, update all related records in the name table, making sure that
    legacy family/sub-family names conform to the the R/I/B/BI (Regular, Italic,
    Bold, Bold Italic) naming model.

    Example: Updating a partial variable font:
    | >>> ttFont = TTFont("OpenSans[wdth,wght].ttf")
    | >>> updateNameTable(ttFont, {"wght": (400, 900), "wdth": 75})

    The name table records will be updated in the following manner:
    NameID 1 familyName: "Open Sans" --> "Open Sans Condensed"
    NameID 2 subFamilyName: "Regular" --> "Regular"
    NameID 3 Unique font identifier: "3.000;GOOG;OpenSans-Regular" --> \
        "3.000;GOOG;OpenSans-Condensed"
    NameID 4 Full font name: "Open Sans Regular" --> "Open Sans Condensed"
    NameID 6 PostScript name: "OpenSans-Regular" --> "OpenSans-Condensed"
    NameID 16 Typographic Family name: None --> "Open Sans"
    NameID 17 Typographic Subfamily name: None --> "Condensed"

    References:
    https://docs.microsoft.com/en-us/typography/opentype/spec/stat
    https://docs.microsoft.com/en-us/typography/opentype/spec/name#name-ids
    """
    from . import AxisLimits, axisValuesFromAxisLimits

    if "STAT" not in varfont:
        raise ValueError("Cannot update name table since there is no STAT table.")
    stat = varfont["STAT"].table
    if not stat.AxisValueArray:
        raise ValueError("Cannot update name table since there are no STAT Axis Values")
    fvar = varfont["fvar"]

    # The updated name table will reflect the new 'zero origin' of the font.
    # If we're instantiating a partial font, we will populate the unpinned
    # axes with their default axis values from fvar.
    axisLimits = AxisLimits(axisLimits).limitAxesAndPopulateDefaults(varfont)
    partialDefaults = axisLimits.defaultLocation()
    fvarDefaults = {a.axisTag: a.defaultValue for a in fvar.axes}
    defaultAxisCoords = AxisLimits({**fvarDefaults, **partialDefaults})
    assert all(v.minimum == v.maximum for v in defaultAxisCoords.values())

    axisValueTables = axisValuesFromAxisLimits(stat, defaultAxisCoords)
    checkAxisValuesExist(stat, axisValueTables, defaultAxisCoords.pinnedLocation())

    # ignore "elidable" axis values, should be omitted in application font menus.
    axisValueTables = [
        v for v in axisValueTables if not v.Flags & ELIDABLE_AXIS_VALUE_NAME
    ]
    axisValueTables = _sortAxisValues(axisValueTables)
    _updateNameRecords(varfont, axisValueTables)


def checkAxisValuesExist(stat, axisValues, axisCoords):
    seen = set()
    designAxes = stat.DesignAxisRecord.Axis
    hasValues = set()
    for value in stat.AxisValueArray.AxisValue:
        if value.Format in (1, 2, 3):
            hasValues.add(designAxes[value.AxisIndex].AxisTag)
        elif value.Format == 4:
            for rec in value.AxisValueRecord:
                hasValues.add(designAxes[rec.AxisIndex].AxisTag)

    for axisValueTable in axisValues:
        axisValueFormat = axisValueTable.Format
        if axisValueTable.Format in (1, 2, 3):
            axisTag = designAxes[axisValueTable.AxisIndex].AxisTag
            if axisValueFormat == 2:
                axisValue = axisValueTable.NominalValue
            else:
                axisValue = axisValueTable.Value
            if axisTag in axisCoords and axisValue == axisCoords[axisTag]:
                seen.add(axisTag)
        elif axisValueTable.Format == 4:
            for rec in axisValueTable.AxisValueRecord:
                axisTag = designAxes[rec.AxisIndex].AxisTag
                if axisTag in axisCoords and rec.Value == axisCoords[axisTag]:
                    seen.add(axisTag)

    missingAxes = (set(axisCoords) - seen) & hasValues
    if missingAxes:
        missing = ", ".join(f"'{i}': {axisCoords[i]}" for i in missingAxes)
        raise ValueError(f"Cannot find Axis Values {{{missing}}}")


def _sortAxisValues(axisValues):
    # Sort by axis index, remove duplicates and ensure that format 4 AxisValues
    # are dominant.
    # The MS Spec states: "if a format 1, format 2 or format 3 table has a
    # (nominal) value used in a format 4 table that also has values for
    # other axes, the format 4 table, being the more specific match, is used",
    # https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-value-table-format-4
    results = []
    seenAxes = set()
    # Sort format 4 axes so the tables with the most AxisValueRecords are first
    format4 = sorted(
        [v for v in axisValues if v.Format == 4],
        key=lambda v: len(v.AxisValueRecord),
        reverse=True,
    )

    for val in format4:
        axisIndexes = set(r.AxisIndex for r in val.AxisValueRecord)
        minIndex = min(axisIndexes)
        if not seenAxes & axisIndexes:
            seenAxes |= axisIndexes
            results.append((minIndex, val))

    for val in axisValues:
        if val in format4:
            continue
        axisIndex = val.AxisIndex
        if axisIndex not in seenAxes:
            seenAxes.add(axisIndex)
            results.append((axisIndex, val))

    return [axisValue for _, axisValue in sorted(results)]


def _updateNameRecords(varfont, axisValues):
    # Update nametable based on the axisValues using the R/I/B/BI model.
    nametable = varfont["name"]
    stat = varfont["STAT"].table

    axisValueNameIDs = [a.ValueNameID for a in axisValues]
    ribbiNameIDs = [n for n in axisValueNameIDs if _isRibbi(nametable, n)]
    nonRibbiNameIDs = [n for n in axisValueNameIDs if n not in ribbiNameIDs]
    elidedNameID = stat.ElidedFallbackNameID
    elidedNameIsRibbi = _isRibbi(nametable, elidedNameID)

    getName = nametable.getName
    platforms = set((r.platformID, r.platEncID, r.langID) for r in nametable.names)
    for platform in platforms:
        if not all(getName(i, *platform) for i in (1, 2, elidedNameID)):
            # Since no family name and subfamily name records were found,
            # we cannot update this set of name Records.
            continue

        subFamilyName = " ".join(
            getName(n, *platform).toUnicode() for n in ribbiNameIDs
        )
        if nonRibbiNameIDs:
            typoSubFamilyName = " ".join(
                getName(n, *platform).toUnicode() for n in axisValueNameIDs
            )
        else:
            typoSubFamilyName = None

        # If neither subFamilyName and typographic SubFamilyName exist,
        # we will use the STAT's elidedFallbackName
        if not typoSubFamilyName and not subFamilyName:
            if elidedNameIsRibbi:
                subFamilyName = getName(elidedNameID, *platform).toUnicode()
            else:
                typoSubFamilyName = getName(elidedNameID, *platform).toUnicode()

        familyNameSuffix = " ".join(
            getName(n, *platform).toUnicode() for n in nonRibbiNameIDs
        )

        _updateNameTableStyleRecords(
            varfont,
            familyNameSuffix,
            subFamilyName,
            typoSubFamilyName,
            *platform,
        )


def _isRibbi(nametable, nameID):
    englishRecord = nametable.getName(nameID, 3, 1, 0x409)
    return (
        True
        if englishRecord is not None
        and englishRecord.toUnicode() in ("Regular", "Italic", "Bold", "Bold Italic")
        else False
    )


def _updateNameTableStyleRecords(
    varfont,
    familyNameSuffix,
    subFamilyName,
    typoSubFamilyName,
    platformID=3,
    platEncID=1,
    langID=0x409,
):
    # TODO (Marc F) It may be nice to make this part a standalone
    # font renamer in the future.
    nametable = varfont["name"]
    platform = (platformID, platEncID, langID)

    currentFamilyName = nametable.getName(
        NameID.TYPOGRAPHIC_FAMILY_NAME, *platform
    ) or nametable.getName(NameID.FAMILY_NAME, *platform)

    currentStyleName = nametable.getName(
        NameID.TYPOGRAPHIC_SUBFAMILY_NAME, *platform
    ) or nametable.getName(NameID.SUBFAMILY_NAME, *platform)

    if not all([currentFamilyName, currentStyleName]):
        raise ValueError(f"Missing required NameIDs 1 and 2 for platform {platform}")

    currentFamilyName = currentFamilyName.toUnicode()
    currentStyleName = currentStyleName.toUnicode()

    nameIDs = {
        NameID.FAMILY_NAME: currentFamilyName,
        NameID.SUBFAMILY_NAME: subFamilyName or "Regular",
    }
    if typoSubFamilyName:
        nameIDs[NameID.FAMILY_NAME] = f"{currentFamilyName} {familyNameSuffix}".strip()
        nameIDs[NameID.TYPOGRAPHIC_FAMILY_NAME] = currentFamilyName
        nameIDs[NameID.TYPOGRAPHIC_SUBFAMILY_NAME] = typoSubFamilyName
    else:
        # Remove previous Typographic Family and SubFamily names since they're
        # no longer required
        for nameID in (
            NameID.TYPOGRAPHIC_FAMILY_NAME,
            NameID.TYPOGRAPHIC_SUBFAMILY_NAME,
        ):
            nametable.removeNames(nameID=nameID)

    newFamilyName = (
        nameIDs.get(NameID.TYPOGRAPHIC_FAMILY_NAME) or nameIDs[NameID.FAMILY_NAME]
    )
    newStyleName = (
        nameIDs.get(NameID.TYPOGRAPHIC_SUBFAMILY_NAME) or nameIDs[NameID.SUBFAMILY_NAME]
    )

    nameIDs[NameID.FULL_FONT_NAME] = f"{newFamilyName} {newStyleName}"
    nameIDs[NameID.POSTSCRIPT_NAME] = _updatePSNameRecord(
        varfont, newFamilyName, newStyleName, platform
    )

    uniqueID = _updateUniqueIdNameRecord(varfont, nameIDs, platform)
    if uniqueID:
        nameIDs[NameID.UNIQUE_FONT_IDENTIFIER] = uniqueID

    for nameID, string in nameIDs.items():
        assert string, nameID
        nametable.setName(string, nameID, *platform)

    if "fvar" not in varfont:
        nametable.removeNames(NameID.VARIATIONS_POSTSCRIPT_NAME_PREFIX)


def _updatePSNameRecord(varfont, familyName, styleName, platform):
    # Implementation based on Adobe Technical Note #5902 :
    # https://wwwimages2.adobe.com/content/dam/acom/en/devnet/font/pdfs/5902.AdobePSNameGeneration.pdf
    nametable = varfont["name"]

    family_prefix = nametable.getName(
        NameID.VARIATIONS_POSTSCRIPT_NAME_PREFIX, *platform
    )
    if family_prefix:
        family_prefix = family_prefix.toUnicode()
    else:
        family_prefix = familyName

    psName = f"{family_prefix}-{styleName}"
    # Remove any characters other than uppercase Latin letters, lowercase
    # Latin letters, digits and hyphens.
    psName = re.sub(r"[^A-Za-z0-9-]", r"", psName)

    if len(psName) > 127:
        # Abbreviating the stylename so it fits within 127 characters whilst
        # conforming to every vendor's specification is too complex. Instead
        # we simply truncate the psname and add the required "..."
        return f"{psName[:124]}..."
    return psName


def _updateUniqueIdNameRecord(varfont, nameIDs, platform):
    nametable = varfont["name"]
    currentRecord = nametable.getName(NameID.UNIQUE_FONT_IDENTIFIER, *platform)
    if not currentRecord:
        return None

    # Check if full name and postscript name are a substring of currentRecord
    for nameID in (NameID.FULL_FONT_NAME, NameID.POSTSCRIPT_NAME):
        nameRecord = nametable.getName(nameID, *platform)
        if not nameRecord:
            continue
        if nameRecord.toUnicode() in currentRecord.toUnicode():
            return currentRecord.toUnicode().replace(
                nameRecord.toUnicode(), nameIDs[nameRecord.nameID]
            )

    # Create a new string since we couldn't find any substrings.
    fontVersion = _fontVersion(varfont, platform)
    achVendID = varfont["OS/2"].achVendID
    # Remove non-ASCII characers and trailing spaces
    vendor = re.sub(r"[^\x00-\x7F]", "", achVendID).strip()
    psName = nameIDs[NameID.POSTSCRIPT_NAME]
    return f"{fontVersion};{vendor};{psName}"


def _fontVersion(font, platform=(3, 1, 0x409)):
    nameRecord = font["name"].getName(NameID.VERSION_STRING, *platform)
    if nameRecord is None:
        return f'{font["head"].fontRevision:.3f}'
    # "Version 1.101; ttfautohint (v1.8.1.43-b0c9)" --> "1.101"
    # Also works fine with inputs "Version 1.101" or "1.101" etc
    versionNumber = nameRecord.toUnicode().split(";")[0]
    return versionNumber.lstrip("Version ").strip()

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\dirfs.py ===
from .. import filesystem
from ..asyn import AsyncFileSystem


class DirFileSystem(AsyncFileSystem):
    """Directory prefix filesystem

    The DirFileSystem is a filesystem-wrapper. It assumes every path it is dealing with
    is relative to the `path`. After performing the necessary paths operation it
    delegates everything to the wrapped filesystem.
    """

    protocol = "dir"

    def __init__(
        self,
        path=None,
        fs=None,
        fo=None,
        target_protocol=None,
        target_options=None,
        **storage_options,
    ):
        """
        Parameters
        ----------
        path: str
            Path to the directory.
        fs: AbstractFileSystem
            An instantiated filesystem to wrap.
        target_protocol, target_options:
            if fs is none, construct it from these
        fo: str
            Alternate for path; do not provide both
        """
        super().__init__(**storage_options)
        if fs is None:
            fs = filesystem(protocol=target_protocol, **(target_options or {}))
        path = path or fo

        if self.asynchronous and not fs.async_impl:
            raise ValueError("can't use asynchronous with non-async fs")

        if fs.async_impl and self.asynchronous != fs.asynchronous:
            raise ValueError("both dirfs and fs should be in the same sync/async mode")

        self.path = fs._strip_protocol(path)
        self.fs = fs

    def _join(self, path):
        if isinstance(path, str):
            if not self.path:
                return path
            if not path:
                return self.path
            return self.fs.sep.join((self.path, self._strip_protocol(path)))
        if isinstance(path, dict):
            return {self._join(_path): value for _path, value in path.items()}
        return [self._join(_path) for _path in path]

    def _relpath(self, path):
        if isinstance(path, str):
            if not self.path:
                return path
            # We need to account for S3FileSystem returning paths that do not
            # start with a '/'
            if path == self.path or (
                self.path.startswith(self.fs.sep) and path == self.path[1:]
            ):
                return ""
            prefix = self.path + self.fs.sep
            if self.path.startswith(self.fs.sep) and not path.startswith(self.fs.sep):
                prefix = prefix[1:]
            assert path.startswith(prefix)
            return path[len(prefix) :]
        return [self._relpath(_path) for _path in path]

    # Wrappers below

    @property
    def sep(self):
        return self.fs.sep

    async def set_session(self, *args, **kwargs):
        return await self.fs.set_session(*args, **kwargs)

    async def _rm_file(self, path, **kwargs):
        return await self.fs._rm_file(self._join(path), **kwargs)

    def rm_file(self, path, **kwargs):
        return self.fs.rm_file(self._join(path), **kwargs)

    async def _rm(self, path, *args, **kwargs):
        return await self.fs._rm(self._join(path), *args, **kwargs)

    def rm(self, path, *args, **kwargs):
        return self.fs.rm(self._join(path), *args, **kwargs)

    async def _cp_file(self, path1, path2, **kwargs):
        return await self.fs._cp_file(self._join(path1), self._join(path2), **kwargs)

    def cp_file(self, path1, path2, **kwargs):
        return self.fs.cp_file(self._join(path1), self._join(path2), **kwargs)

    async def _copy(
        self,
        path1,
        path2,
        *args,
        **kwargs,
    ):
        return await self.fs._copy(
            self._join(path1),
            self._join(path2),
            *args,
            **kwargs,
        )

    def copy(self, path1, path2, *args, **kwargs):
        return self.fs.copy(
            self._join(path1),
            self._join(path2),
            *args,
            **kwargs,
        )

    async def _pipe(self, path, *args, **kwargs):
        return await self.fs._pipe(self._join(path), *args, **kwargs)

    def pipe(self, path, *args, **kwargs):
        return self.fs.pipe(self._join(path), *args, **kwargs)

    async def _pipe_file(self, path, *args, **kwargs):
        return await self.fs._pipe_file(self._join(path), *args, **kwargs)

    def pipe_file(self, path, *args, **kwargs):
        return self.fs.pipe_file(self._join(path), *args, **kwargs)

    async def _cat_file(self, path, *args, **kwargs):
        return await self.fs._cat_file(self._join(path), *args, **kwargs)

    def cat_file(self, path, *args, **kwargs):
        return self.fs.cat_file(self._join(path), *args, **kwargs)

    async def _cat(self, path, *args, **kwargs):
        ret = await self.fs._cat(
            self._join(path),
            *args,
            **kwargs,
        )

        if isinstance(ret, dict):
            return {self._relpath(key): value for key, value in ret.items()}

        return ret

    def cat(self, path, *args, **kwargs):
        ret = self.fs.cat(
            self._join(path),
            *args,
            **kwargs,
        )

        if isinstance(ret, dict):
            return {self._relpath(key): value for key, value in ret.items()}

        return ret

    async def _put_file(self, lpath, rpath, **kwargs):
        return await self.fs._put_file(lpath, self._join(rpath), **kwargs)

    def put_file(self, lpath, rpath, **kwargs):
        return self.fs.put_file(lpath, self._join(rpath), **kwargs)

    async def _put(
        self,
        lpath,
        rpath,
        *args,
        **kwargs,
    ):
        return await self.fs._put(
            lpath,
            self._join(rpath),
            *args,
            **kwargs,
        )

    def put(self, lpath, rpath, *args, **kwargs):
        return self.fs.put(
            lpath,
            self._join(rpath),
            *args,
            **kwargs,
        )

    async def _get_file(self, rpath, lpath, **kwargs):
        return await self.fs._get_file(self._join(rpath), lpath, **kwargs)

    def get_file(self, rpath, lpath, **kwargs):
        return self.fs.get_file(self._join(rpath), lpath, **kwargs)

    async def _get(self, rpath, *args, **kwargs):
        return await self.fs._get(self._join(rpath), *args, **kwargs)

    def get(self, rpath, *args, **kwargs):
        return self.fs.get(self._join(rpath), *args, **kwargs)

    async def _isfile(self, path):
        return await self.fs._isfile(self._join(path))

    def isfile(self, path):
        return self.fs.isfile(self._join(path))

    async def _isdir(self, path):
        return await self.fs._isdir(self._join(path))

    def isdir(self, path):
        return self.fs.isdir(self._join(path))

    async def _size(self, path):
        return await self.fs._size(self._join(path))

    def size(self, path):
        return self.fs.size(self._join(path))

    async def _exists(self, path):
        return await self.fs._exists(self._join(path))

    def exists(self, path):
        return self.fs.exists(self._join(path))

    async def _info(self, path, **kwargs):
        info = await self.fs._info(self._join(path), **kwargs)
        info = info.copy()
        info["name"] = self._relpath(info["name"])
        return info

    def info(self, path, **kwargs):
        info = self.fs.info(self._join(path), **kwargs)
        info = info.copy()
        info["name"] = self._relpath(info["name"])
        return info

    async def _ls(self, path, detail=True, **kwargs):
        ret = (await self.fs._ls(self._join(path), detail=detail, **kwargs)).copy()
        if detail:
            out = []
            for entry in ret:
                entry = entry.copy()
                entry["name"] = self._relpath(entry["name"])
                out.append(entry)
            return out

        return self._relpath(ret)

    def ls(self, path, detail=True, **kwargs):
        ret = self.fs.ls(self._join(path), detail=detail, **kwargs).copy()
        if detail:
            out = []
            for entry in ret:
                entry = entry.copy()
                entry["name"] = self._relpath(entry["name"])
                out.append(entry)
            return out

        return self._relpath(ret)

    async def _walk(self, path, *args, **kwargs):
        async for root, dirs, files in self.fs._walk(self._join(path), *args, **kwargs):
            yield self._relpath(root), dirs, files

    def walk(self, path, *args, **kwargs):
        for root, dirs, files in self.fs.walk(self._join(path), *args, **kwargs):
            yield self._relpath(root), dirs, files

    async def _glob(self, path, **kwargs):
        detail = kwargs.get("detail", False)
        ret = await self.fs._glob(self._join(path), **kwargs)
        if detail:
            return {self._relpath(path): info for path, info in ret.items()}
        return self._relpath(ret)

    def glob(self, path, **kwargs):
        detail = kwargs.get("detail", False)
        ret = self.fs.glob(self._join(path), **kwargs)
        if detail:
            return {self._relpath(path): info for path, info in ret.items()}
        return self._relpath(ret)

    async def _du(self, path, *args, **kwargs):
        total = kwargs.get("total", True)
        ret = await self.fs._du(self._join(path), *args, **kwargs)
        if total:
            return ret

        return {self._relpath(path): size for path, size in ret.items()}

    def du(self, path, *args, **kwargs):
        total = kwargs.get("total", True)
        ret = self.fs.du(self._join(path), *args, **kwargs)
        if total:
            return ret

        return {self._relpath(path): size for path, size in ret.items()}

    async def _find(self, path, *args, **kwargs):
        detail = kwargs.get("detail", False)
        ret = await self.fs._find(self._join(path), *args, **kwargs)
        if detail:
            return {self._relpath(path): info for path, info in ret.items()}
        return self._relpath(ret)

    def find(self, path, *args, **kwargs):
        detail = kwargs.get("detail", False)
        ret = self.fs.find(self._join(path), *args, **kwargs)
        if detail:
            return {self._relpath(path): info for path, info in ret.items()}
        return self._relpath(ret)

    async def _expand_path(self, path, *args, **kwargs):
        return self._relpath(
            await self.fs._expand_path(self._join(path), *args, **kwargs)
        )

    def expand_path(self, path, *args, **kwargs):
        return self._relpath(self.fs.expand_path(self._join(path), *args, **kwargs))

    async def _mkdir(self, path, *args, **kwargs):
        return await self.fs._mkdir(self._join(path), *args, **kwargs)

    def mkdir(self, path, *args, **kwargs):
        return self.fs.mkdir(self._join(path), *args, **kwargs)

    async def _makedirs(self, path, *args, **kwargs):
        return await self.fs._makedirs(self._join(path), *args, **kwargs)

    def makedirs(self, path, *args, **kwargs):
        return self.fs.makedirs(self._join(path), *args, **kwargs)

    def rmdir(self, path):
        return self.fs.rmdir(self._join(path))

    def mv(self, path1, path2, **kwargs):
        return self.fs.mv(
            self._join(path1),
            self._join(path2),
            **kwargs,
        )

    def touch(self, path, **kwargs):
        return self.fs.touch(self._join(path), **kwargs)

    def created(self, path):
        return self.fs.created(self._join(path))

    def modified(self, path):
        return self.fs.modified(self._join(path))

    def sign(self, path, *args, **kwargs):
        return self.fs.sign(self._join(path), *args, **kwargs)

    def __repr__(self):
        return f"{self.__class__.__qualname__}(path='{self.path}', fs={self.fs})"

    def open(
        self,
        path,
        *args,
        **kwargs,
    ):
        return self.fs.open(
            self._join(path),
            *args,
            **kwargs,
        )

    async def open_async(
        self,
        path,
        *args,
        **kwargs,
    ):
        return await self.fs.open_async(
            self._join(path),
            *args,
            **kwargs,
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage\__init__.py ===
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
from google.ai.generativelanguage import gapic_version as package_version

__version__ = package_version.__version__


from google.ai.generativelanguage_v1beta.services.cache_service.async_client import (
    CacheServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.cache_service.client import (
    CacheServiceClient,
)
from google.ai.generativelanguage_v1beta.services.discuss_service.async_client import (
    DiscussServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.discuss_service.client import (
    DiscussServiceClient,
)
from google.ai.generativelanguage_v1beta.services.file_service.async_client import (
    FileServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.file_service.client import (
    FileServiceClient,
)
from google.ai.generativelanguage_v1beta.services.generative_service.async_client import (
    GenerativeServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.generative_service.client import (
    GenerativeServiceClient,
)
from google.ai.generativelanguage_v1beta.services.model_service.async_client import (
    ModelServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.model_service.client import (
    ModelServiceClient,
)
from google.ai.generativelanguage_v1beta.services.permission_service.async_client import (
    PermissionServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.permission_service.client import (
    PermissionServiceClient,
)
from google.ai.generativelanguage_v1beta.services.retriever_service.async_client import (
    RetrieverServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.retriever_service.client import (
    RetrieverServiceClient,
)
from google.ai.generativelanguage_v1beta.services.text_service.async_client import (
    TextServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.text_service.client import (
    TextServiceClient,
)
from google.ai.generativelanguage_v1beta.types.cache_service import (
    CreateCachedContentRequest,
    DeleteCachedContentRequest,
    GetCachedContentRequest,
    ListCachedContentsRequest,
    ListCachedContentsResponse,
    UpdateCachedContentRequest,
)
from google.ai.generativelanguage_v1beta.types.cached_content import CachedContent
from google.ai.generativelanguage_v1beta.types.citation import (
    CitationMetadata,
    CitationSource,
)
from google.ai.generativelanguage_v1beta.types.content import (
    Blob,
    CodeExecution,
    CodeExecutionResult,
    Content,
    ExecutableCode,
    FileData,
    FunctionCall,
    FunctionCallingConfig,
    FunctionDeclaration,
    FunctionResponse,
    GroundingPassage,
    GroundingPassages,
    Part,
    Schema,
    Tool,
    ToolConfig,
    Type,
)
from google.ai.generativelanguage_v1beta.types.discuss_service import (
    CountMessageTokensRequest,
    CountMessageTokensResponse,
    Example,
    GenerateMessageRequest,
    GenerateMessageResponse,
    Message,
    MessagePrompt,
)
from google.ai.generativelanguage_v1beta.types.file import File, VideoMetadata
from google.ai.generativelanguage_v1beta.types.file_service import (
    CreateFileRequest,
    CreateFileResponse,
    DeleteFileRequest,
    GetFileRequest,
    ListFilesRequest,
    ListFilesResponse,
)
from google.ai.generativelanguage_v1beta.types.generative_service import (
    AttributionSourceId,
    BatchEmbedContentsRequest,
    BatchEmbedContentsResponse,
    Candidate,
    ContentEmbedding,
    CountTokensRequest,
    CountTokensResponse,
    EmbedContentRequest,
    EmbedContentResponse,
    GenerateAnswerRequest,
    GenerateAnswerResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerationConfig,
    GroundingAttribution,
    SemanticRetrieverConfig,
    TaskType,
)
from google.ai.generativelanguage_v1beta.types.model import Model
from google.ai.generativelanguage_v1beta.types.model_service import (
    CreateTunedModelMetadata,
    CreateTunedModelRequest,
    DeleteTunedModelRequest,
    GetModelRequest,
    GetTunedModelRequest,
    ListModelsRequest,
    ListModelsResponse,
    ListTunedModelsRequest,
    ListTunedModelsResponse,
    UpdateTunedModelRequest,
)
from google.ai.generativelanguage_v1beta.types.permission import Permission
from google.ai.generativelanguage_v1beta.types.permission_service import (
    CreatePermissionRequest,
    DeletePermissionRequest,
    GetPermissionRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    UpdatePermissionRequest,
)
from google.ai.generativelanguage_v1beta.types.retriever import (
    Chunk,
    ChunkData,
    Condition,
    Corpus,
    CustomMetadata,
    Document,
    MetadataFilter,
    StringList,
)
from google.ai.generativelanguage_v1beta.types.retriever_service import (
    BatchCreateChunksRequest,
    BatchCreateChunksResponse,
    BatchDeleteChunksRequest,
    BatchUpdateChunksRequest,
    BatchUpdateChunksResponse,
    CreateChunkRequest,
    CreateCorpusRequest,
    CreateDocumentRequest,
    DeleteChunkRequest,
    DeleteCorpusRequest,
    DeleteDocumentRequest,
    GetChunkRequest,
    GetCorpusRequest,
    GetDocumentRequest,
    ListChunksRequest,
    ListChunksResponse,
    ListCorporaRequest,
    ListCorporaResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
    QueryCorpusRequest,
    QueryCorpusResponse,
    QueryDocumentRequest,
    QueryDocumentResponse,
    RelevantChunk,
    UpdateChunkRequest,
    UpdateCorpusRequest,
    UpdateDocumentRequest,
)
from google.ai.generativelanguage_v1beta.types.safety import (
    ContentFilter,
    HarmCategory,
    SafetyFeedback,
    SafetyRating,
    SafetySetting,
)
from google.ai.generativelanguage_v1beta.types.text_service import (
    BatchEmbedTextRequest,
    BatchEmbedTextResponse,
    CountTextTokensRequest,
    CountTextTokensResponse,
    Embedding,
    EmbedTextRequest,
    EmbedTextResponse,
    GenerateTextRequest,
    GenerateTextResponse,
    TextCompletion,
    TextPrompt,
)
from google.ai.generativelanguage_v1beta.types.tuned_model import (
    Dataset,
    Hyperparameters,
    TunedModel,
    TunedModelSource,
    TuningExample,
    TuningExamples,
    TuningSnapshot,
    TuningTask,
)

__all__ = (
    "CacheServiceClient",
    "CacheServiceAsyncClient",
    "DiscussServiceClient",
    "DiscussServiceAsyncClient",
    "FileServiceClient",
    "FileServiceAsyncClient",
    "GenerativeServiceClient",
    "GenerativeServiceAsyncClient",
    "ModelServiceClient",
    "ModelServiceAsyncClient",
    "PermissionServiceClient",
    "PermissionServiceAsyncClient",
    "RetrieverServiceClient",
    "RetrieverServiceAsyncClient",
    "TextServiceClient",
    "TextServiceAsyncClient",
    "CreateCachedContentRequest",
    "DeleteCachedContentRequest",
    "GetCachedContentRequest",
    "ListCachedContentsRequest",
    "ListCachedContentsResponse",
    "UpdateCachedContentRequest",
    "CachedContent",
    "CitationMetadata",
    "CitationSource",
    "Blob",
    "CodeExecution",
    "CodeExecutionResult",
    "Content",
    "ExecutableCode",
    "FileData",
    "FunctionCall",
    "FunctionCallingConfig",
    "FunctionDeclaration",
    "FunctionResponse",
    "GroundingPassage",
    "GroundingPassages",
    "Part",
    "Schema",
    "Tool",
    "ToolConfig",
    "Type",
    "CountMessageTokensRequest",
    "CountMessageTokensResponse",
    "Example",
    "GenerateMessageRequest",
    "GenerateMessageResponse",
    "Message",
    "MessagePrompt",
    "File",
    "VideoMetadata",
    "CreateFileRequest",
    "CreateFileResponse",
    "DeleteFileRequest",
    "GetFileRequest",
    "ListFilesRequest",
    "ListFilesResponse",
    "AttributionSourceId",
    "BatchEmbedContentsRequest",
    "BatchEmbedContentsResponse",
    "Candidate",
    "ContentEmbedding",
    "CountTokensRequest",
    "CountTokensResponse",
    "EmbedContentRequest",
    "EmbedContentResponse",
    "GenerateAnswerRequest",
    "GenerateAnswerResponse",
    "GenerateContentRequest",
    "GenerateContentResponse",
    "GenerationConfig",
    "GroundingAttribution",
    "SemanticRetrieverConfig",
    "TaskType",
    "Model",
    "CreateTunedModelMetadata",
    "CreateTunedModelRequest",
    "DeleteTunedModelRequest",
    "GetModelRequest",
    "GetTunedModelRequest",
    "ListModelsRequest",
    "ListModelsResponse",
    "ListTunedModelsRequest",
    "ListTunedModelsResponse",
    "UpdateTunedModelRequest",
    "Permission",
    "CreatePermissionRequest",
    "DeletePermissionRequest",
    "GetPermissionRequest",
    "ListPermissionsRequest",
    "ListPermissionsResponse",
    "TransferOwnershipRequest",
    "TransferOwnershipResponse",
    "UpdatePermissionRequest",
    "Chunk",
    "ChunkData",
    "Condition",
    "Corpus",
    "CustomMetadata",
    "Document",
    "MetadataFilter",
    "StringList",
    "BatchCreateChunksRequest",
    "BatchCreateChunksResponse",
    "BatchDeleteChunksRequest",
    "BatchUpdateChunksRequest",
    "BatchUpdateChunksResponse",
    "CreateChunkRequest",
    "CreateCorpusRequest",
    "CreateDocumentRequest",
    "DeleteChunkRequest",
    "DeleteCorpusRequest",
    "DeleteDocumentRequest",
    "GetChunkRequest",
    "GetCorpusRequest",
    "GetDocumentRequest",
    "ListChunksRequest",
    "ListChunksResponse",
    "ListCorporaRequest",
    "ListCorporaResponse",
    "ListDocumentsRequest",
    "ListDocumentsResponse",
    "QueryCorpusRequest",
    "QueryCorpusResponse",
    "QueryDocumentRequest",
    "QueryDocumentResponse",
    "RelevantChunk",
    "UpdateChunkRequest",
    "UpdateCorpusRequest",
    "UpdateDocumentRequest",
    "ContentFilter",
    "SafetyFeedback",
    "SafetyRating",
    "SafetySetting",
    "HarmCategory",
    "BatchEmbedTextRequest",
    "BatchEmbedTextResponse",
    "CountTextTokensRequest",
    "CountTextTokensResponse",
    "Embedding",
    "EmbedTextRequest",
    "EmbedTextResponse",
    "GenerateTextRequest",
    "GenerateTextResponse",
    "TextCompletion",
    "TextPrompt",
    "Dataset",
    "Hyperparameters",
    "TunedModel",
    "TunedModelSource",
    "TuningExample",
    "TuningExamples",
    "TuningSnapshot",
    "TuningTask",
)

# === NexusCore/openenv\Lib\site-packages\matplotlib\backend_managers.py ===
from matplotlib import _api, backend_tools, cbook, widgets


class ToolEvent:
    """Event for tool manipulation (add/remove)."""
    def __init__(self, name, sender, tool, data=None):
        self.name = name
        self.sender = sender
        self.tool = tool
        self.data = data


class ToolTriggerEvent(ToolEvent):
    """Event to inform that a tool has been triggered."""
    def __init__(self, name, sender, tool, canvasevent=None, data=None):
        super().__init__(name, sender, tool, data)
        self.canvasevent = canvasevent


class ToolManagerMessageEvent:
    """
    Event carrying messages from toolmanager.

    Messages usually get displayed to the user by the toolbar.
    """
    def __init__(self, name, sender, message):
        self.name = name
        self.sender = sender
        self.message = message


class ToolManager:
    """
    Manager for actions triggered by user interactions (key press, toolbar
    clicks, ...) on a Figure.

    Attributes
    ----------
    figure : `.Figure`
    keypresslock : `~matplotlib.widgets.LockDraw`
        `.LockDraw` object to know if the `canvas` key_press_event is locked.
    messagelock : `~matplotlib.widgets.LockDraw`
        `.LockDraw` object to know if the message is available to write.
    """

    def __init__(self, figure=None):

        self._key_press_handler_id = None

        self._tools = {}
        self._keys = {}
        self._toggled = {}
        self._callbacks = cbook.CallbackRegistry()

        # to process keypress event
        self.keypresslock = widgets.LockDraw()
        self.messagelock = widgets.LockDraw()

        self._figure = None
        self.set_figure(figure)

    @property
    def canvas(self):
        """Canvas managed by FigureManager."""
        if not self._figure:
            return None
        return self._figure.canvas

    @property
    def figure(self):
        """Figure that holds the canvas."""
        return self._figure

    @figure.setter
    def figure(self, figure):
        self.set_figure(figure)

    def set_figure(self, figure, update_tools=True):
        """
        Bind the given figure to the tools.

        Parameters
        ----------
        figure : `.Figure`
        update_tools : bool, default: True
            Force tools to update figure.
        """
        if self._key_press_handler_id:
            self.canvas.mpl_disconnect(self._key_press_handler_id)
        self._figure = figure
        if figure:
            self._key_press_handler_id = self.canvas.mpl_connect(
                'key_press_event', self._key_press)
        if update_tools:
            for tool in self._tools.values():
                tool.figure = figure

    def toolmanager_connect(self, s, func):
        """
        Connect event with string *s* to *func*.

        Parameters
        ----------
        s : str
            The name of the event. The following events are recognized:

            - 'tool_message_event'
            - 'tool_removed_event'
            - 'tool_added_event'

            For every tool added a new event is created

            - 'tool_trigger_TOOLNAME', where TOOLNAME is the id of the tool.

        func : callable
            Callback function for the toolmanager event with signature::

                def func(event: ToolEvent) -> Any

        Returns
        -------
        cid
            The callback id for the connection. This can be used in
            `.toolmanager_disconnect`.
        """
        return self._callbacks.connect(s, func)

    def toolmanager_disconnect(self, cid):
        """
        Disconnect callback id *cid*.

        Example usage::

            cid = toolmanager.toolmanager_connect('tool_trigger_zoom', onpress)
            #...later
            toolmanager.toolmanager_disconnect(cid)
        """
        return self._callbacks.disconnect(cid)

    def message_event(self, message, sender=None):
        """Emit a `ToolManagerMessageEvent`."""
        if sender is None:
            sender = self

        s = 'tool_message_event'
        event = ToolManagerMessageEvent(s, sender, message)
        self._callbacks.process(s, event)

    @property
    def active_toggle(self):
        """Currently toggled tools."""
        return self._toggled

    def get_tool_keymap(self, name):
        """
        Return the keymap associated with the specified tool.

        Parameters
        ----------
        name : str
            Name of the Tool.

        Returns
        -------
        list of str
            List of keys associated with the tool.
        """

        keys = [k for k, i in self._keys.items() if i == name]
        return keys

    def _remove_keys(self, name):
        for k in self.get_tool_keymap(name):
            del self._keys[k]

    def update_keymap(self, name, key):
        """
        Set the keymap to associate with the specified tool.

        Parameters
        ----------
        name : str
            Name of the Tool.
        key : str or list of str
            Keys to associate with the tool.
        """
        if name not in self._tools:
            raise KeyError(f'{name!r} not in Tools')
        self._remove_keys(name)
        if isinstance(key, str):
            key = [key]
        for k in key:
            if k in self._keys:
                _api.warn_external(
                    f'Key {k} changed from {self._keys[k]} to {name}')
            self._keys[k] = name

    def remove_tool(self, name):
        """
        Remove tool named *name*.

        Parameters
        ----------
        name : str
            Name of the tool.
        """
        tool = self.get_tool(name)
        if getattr(tool, 'toggled', False):  # If it's a toggled toggle tool, untoggle
            self.trigger_tool(tool, 'toolmanager')
        self._remove_keys(name)
        event = ToolEvent('tool_removed_event', self, tool)
        self._callbacks.process(event.name, event)
        del self._tools[name]

    def add_tool(self, name, tool, *args, **kwargs):
        """
        Add *tool* to `ToolManager`.

        If successful, adds a new event ``tool_trigger_{name}`` where
        ``{name}`` is the *name* of the tool; the event is fired every time the
        tool is triggered.

        Parameters
        ----------
        name : str
            Name of the tool, treated as the ID, has to be unique.
        tool : type
            Class of the tool to be added.  A subclass will be used
            instead if one was registered for the current canvas class.
        *args, **kwargs
            Passed to the *tool*'s constructor.

        See Also
        --------
        matplotlib.backend_tools.ToolBase : The base class for tools.
        """

        tool_cls = backend_tools._find_tool_class(type(self.canvas), tool)
        if not tool_cls:
            raise ValueError('Impossible to find class for %s' % str(tool))

        if name in self._tools:
            _api.warn_external('A "Tool class" with the same name already '
                               'exists, not added')
            return self._tools[name]

        tool_obj = tool_cls(self, name, *args, **kwargs)
        self._tools[name] = tool_obj

        if tool_obj.default_keymap is not None:
            self.update_keymap(name, tool_obj.default_keymap)

        # For toggle tools init the radio_group in self._toggled
        if isinstance(tool_obj, backend_tools.ToolToggleBase):
            # None group is not mutually exclusive, a set is used to keep track
            # of all toggled tools in this group
            if tool_obj.radio_group is None:
                self._toggled.setdefault(None, set())
            else:
                self._toggled.setdefault(tool_obj.radio_group, None)

            # If initially toggled
            if tool_obj.toggled:
                self._handle_toggle(tool_obj, None, None)
        tool_obj.set_figure(self.figure)

        event = ToolEvent('tool_added_event', self, tool_obj)
        self._callbacks.process(event.name, event)

        return tool_obj

    def _handle_toggle(self, tool, canvasevent, data):
        """
        Toggle tools, need to untoggle prior to using other Toggle tool.
        Called from trigger_tool.

        Parameters
        ----------
        tool : `.ToolBase`
        canvasevent : Event
            Original Canvas event or None.
        data : object
            Extra data to pass to the tool when triggering.
        """

        radio_group = tool.radio_group
        # radio_group None is not mutually exclusive
        # just keep track of toggled tools in this group
        if radio_group is None:
            if tool.name in self._toggled[None]:
                self._toggled[None].remove(tool.name)
            else:
                self._toggled[None].add(tool.name)
            return

        # If the tool already has a toggled state, untoggle it
        if self._toggled[radio_group] == tool.name:
            toggled = None
        # If no tool was toggled in the radio_group
        # toggle it
        elif self._toggled[radio_group] is None:
            toggled = tool.name
        # Other tool in the radio_group is toggled
        else:
            # Untoggle previously toggled tool
            self.trigger_tool(self._toggled[radio_group],
                              self,
                              canvasevent,
                              data)
            toggled = tool.name

        # Keep track of the toggled tool in the radio_group
        self._toggled[radio_group] = toggled

    def trigger_tool(self, name, sender=None, canvasevent=None, data=None):
        """
        Trigger a tool and emit the ``tool_trigger_{name}`` event.

        Parameters
        ----------
        name : str
            Name of the tool.
        sender : object
            Object that wishes to trigger the tool.
        canvasevent : Event
            Original Canvas event or None.
        data : object
            Extra data to pass to the tool when triggering.
        """
        tool = self.get_tool(name)
        if tool is None:
            return

        if sender is None:
            sender = self

        if isinstance(tool, backend_tools.ToolToggleBase):
            self._handle_toggle(tool, canvasevent, data)

        tool.trigger(sender, canvasevent, data)  # Actually trigger Tool.

        s = 'tool_trigger_%s' % name
        event = ToolTriggerEvent(s, sender, tool, canvasevent, data)
        self._callbacks.process(s, event)

    def _key_press(self, event):
        if event.key is None or self.keypresslock.locked():
            return

        name = self._keys.get(event.key, None)
        if name is None:
            return
        self.trigger_tool(name, canvasevent=event)

    @property
    def tools(self):
        """A dict mapping tool name -> controlled tool."""
        return self._tools

    def get_tool(self, name, warn=True):
        """
        Return the tool object with the given name.

        For convenience, this passes tool objects through.

        Parameters
        ----------
        name : str or `.ToolBase`
            Name of the tool, or the tool itself.
        warn : bool, default: True
            Whether a warning should be emitted it no tool with the given name
            exists.

        Returns
        -------
        `.ToolBase` or None
            The tool or None if no tool with the given name exists.
        """
        if (isinstance(name, backend_tools.ToolBase)
                and name.name in self._tools):
            return name
        if name not in self._tools:
            if warn:
                _api.warn_external(
                    f"ToolManager does not control tool {name!r}")
            return None
        return self._tools[name]

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\abstract_operations_client.py ===
# -*- coding: utf-8 -*-
# Copyright 2020 Google LLC
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
from typing import Optional, Sequence, Tuple, Union

from google.api_core import client_options as client_options_lib  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core import retry as retries  # type: ignore
from google.api_core.operations_v1 import pagers
from google.api_core.operations_v1.transports.base import (
    DEFAULT_CLIENT_INFO,
    OperationsTransport,
)
from google.api_core.operations_v1.abstract_operations_base_client import (
    AbstractOperationsBaseClient,
)
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2
from google.oauth2 import service_account  # type: ignore
import grpc

OptionalRetry = Union[retries.Retry, object]


class AbstractOperationsClient(AbstractOperationsBaseClient):
    """Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be
    designed to return [Operation][google.api_core.operations_v1.Operation] to the
    client, and the client can use this interface to receive the real
    response asynchronously by polling the operation resource, or pass
    the operation resource to another API (such as Google Cloud Pub/Sub
    API) to receive the response. Any API service that returns
    long-running operations should implement the ``Operations``
    interface so developers can have a consistent client experience.
    """

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Union[str, OperationsTransport, None] = None,
        client_options: Optional[client_options_lib.ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the operations client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Union[str, OperationsTransport]): The
                transport to use. If set to None, a transport is chosen
                automatically.
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. It won't take effect if a ``transport`` instance is provided.
                (1) The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client. GOOGLE_API_USE_MTLS_ENDPOINT
                environment variable can also be used to override the endpoint:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto switch to the
                default mTLS endpoint if client certificate is present, this is
                the default value). However, the ``api_endpoint`` property takes
                precedence if provided.
                (2) If GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide client certificate for mutual TLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        super().__init__(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            AbstractOperationsClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            AbstractOperationsClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    def list_operations(
        self,
        name: str,
        filter_: Optional[str] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListOperationsPager:
        r"""Lists operations that match the specified filter in the request.
        If the server doesn't support this method, it returns
        ``UNIMPLEMENTED``.

        NOTE: the ``name`` binding allows API services to override the
        binding to use different resource name schemes, such as
        ``users/*/operations``. To override the binding, API services
        can add a binding such as ``"/v1/{name=users/*}/operations"`` to
        their service configuration. For backwards compatibility, the
        default name includes the operations collection id, however
        overriding users must ensure the name binding is the parent
        resource, without the operations collection id.

        Args:
            name (str):
                The name of the operation's parent
                resource.
            filter_ (str):
                The standard list filter.
                This corresponds to the ``filter`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operations_v1.pagers.ListOperationsPager:
                The response message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create a protobuf request object.
        request = operations_pb2.ListOperationsRequest(name=name, filter=filter_)
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_operations]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListOperationsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_operation(
        self,
        name: str,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Gets the latest state of a long-running operation.
        Clients can use this method to poll the operation result
        at intervals as recommended by the API service.

        Args:
            name (str):
                The name of the operation resource.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.longrunning.operations_pb2.Operation:
                This resource represents a long-
                running operation that is the result of a
                network API call.

        """

        request = operations_pb2.GetOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def delete_operation(
        self,
        name: str,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a long-running operation. This method indicates that the
        client is no longer interested in the operation result. It does
        not cancel the operation. If the server doesn't support this
        method, it returns ``google.rpc.Code.UNIMPLEMENTED``.

        Args:
            name (str):
                The name of the operation resource to
                be deleted.

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create the request object.
        request = operations_pb2.DeleteOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

    def cancel_operation(
        self,
        name: Optional[str] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Starts asynchronous cancellation on a long-running operation.
        The server makes a best effort to cancel the operation, but
        success is not guaranteed. If the server doesn't support this
        method, it returns ``google.rpc.Code.UNIMPLEMENTED``. Clients
        can use
        [Operations.GetOperation][google.api_core.operations_v1.Operations.GetOperation]
        or other methods to check whether the cancellation succeeded or
        whether the operation completed despite cancellation. On
        successful cancellation, the operation is not deleted; instead,
        it becomes an operation with an
        [Operation.error][google.api_core.operations_v1.Operation.error] value with
        a [google.rpc.Status.code][google.rpc.Status.code] of 1,
        corresponding to ``Code.CANCELLED``.

        Args:
            name (str):
                The name of the operation resource to
                be cancelled.

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create the request object.
        request = operations_pb2.CancelOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.cancel_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\model_types.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
"""Type definitions for the models service."""
from __future__ import annotations

from collections.abc import Mapping
import csv
import dataclasses
import datetime
import json
import pathlib
import re

from typing import Any, Iterable, Union

import urllib.request
from typing_extensions import TypedDict

from google.generativeai import protos
from google.generativeai.types import permission_types
from google.generativeai import string_utils


__all__ = [
    "Model",
    "ModelNameOptions",
    "AnyModelNameOptions",
    "BaseModelNameOptions",
    "TunedModelNameOptions",
    "ModelsIterable",
    "TunedModel",
    "TunedModelState",
]

TunedModelState = protos.TunedModel.State

TunedModelStateOptions = Union[None, str, int, TunedModelState]

_TUNED_MODEL_VALID_NAME = r"[a-z](([a-z0-9-]{0,61}[a-z0-9])?)$"
TUNED_MODEL_NAME_ERROR_MSG = """The `name` must consist of alphanumeric characters (or -) and be at most 63 characters; The name you entered:
\tlen(name)== {length}
\tname={name}
"""


def valid_tuned_model_name(name: str) -> bool:
    return re.match(_TUNED_MODEL_VALID_NAME, name) is not None


# fmt: off
_TUNED_MODEL_STATES: dict[TunedModelStateOptions, TunedModelState] = {
    TunedModelState.ACTIVE: TunedModelState.ACTIVE,
    int(TunedModelState.ACTIVE): TunedModelState.ACTIVE,
    "active": TunedModelState.ACTIVE,

    TunedModelState.CREATING: TunedModelState.CREATING,
    int(TunedModelState.CREATING): TunedModelState.CREATING,
    "creating": TunedModelState.CREATING,

    TunedModelState.FAILED: TunedModelState.FAILED,
    int(TunedModelState.FAILED): TunedModelState.FAILED,
    "failed": TunedModelState.FAILED,

    TunedModelState.STATE_UNSPECIFIED: TunedModelState.STATE_UNSPECIFIED,
    int(TunedModelState.STATE_UNSPECIFIED): TunedModelState.STATE_UNSPECIFIED,
    "state_unspecified": TunedModelState.STATE_UNSPECIFIED,
    "unspecified": TunedModelState.STATE_UNSPECIFIED,
    None: TunedModelState.STATE_UNSPECIFIED,
}
# fmt: on


def to_tuned_model_state(x: TunedModelStateOptions) -> TunedModelState:
    if isinstance(x, str):
        x = x.lower()
    return _TUNED_MODEL_STATES[x]


@string_utils.prettyprint
@dataclasses.dataclass
class Model:
    """A dataclass representation of a `protos.Model`.

    Attributes:
        name: The resource name of the `Model`. Format: `models/{model}` with a `{model}` naming
           convention of: "{base_model_id}-{version}". For example: `models/chat-bison-001`.
        base_model_id: The base name of the model. For example: `chat-bison`.
        version:  The major version number of the model. For example: `001`.
        display_name: The human-readable name of the model. E.g. `"Chat Bison"`. The name can be up
           to 128 characters long and can consist of any UTF-8 characters.
        description: A short description of the model.
        input_token_limit: Maximum number of input tokens allowed for this model.
        output_token_limit: Maximum number of output tokens available for this model.
        supported_generation_methods: lists which methods are supported by the model. The method
          names are defined as Pascal case strings, such as `generateMessage` which correspond to
          API methods.
    """

    name: str
    base_model_id: str
    version: str
    display_name: str
    description: str
    input_token_limit: int
    output_token_limit: int
    supported_generation_methods: list[str]
    temperature: float | None = None
    max_temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None


def _fix_microseconds(match):
    # microseconds needs exactly 6 digits
    fraction = float(match.group(0))
    return f".{int(round(fraction*1e6)):06d}"


def idecode_time(parent: dict["str", Any], name: str):
    time = parent.pop(name, None)
    if time is not None:
        if "." in time:
            time = re.sub(r"\.\d+", _fix_microseconds, time)
            dt = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            dt = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")

        dt = dt.replace(tzinfo=datetime.timezone.utc)
        parent[name] = dt


def decode_tuned_model(tuned_model: protos.TunedModel | dict["str", Any]) -> TunedModel:
    if isinstance(tuned_model, protos.TunedModel):
        tuned_model = type(tuned_model).to_dict(tuned_model)  # pytype: disable=attribute-error
    tuned_model["state"] = to_tuned_model_state(tuned_model.pop("state", None))

    base_model = tuned_model.pop("base_model", None)
    tuned_model_source = tuned_model.pop("tuned_model_source", None)
    if base_model is not None:
        tuned_model["base_model"] = base_model
        tuned_model["source_model"] = base_model
    elif tuned_model_source is not None:
        tuned_model["base_model"] = tuned_model_source["base_model"]
        tuned_model["source_model"] = tuned_model_source["tuned_model"]

    idecode_time(tuned_model, "create_time")
    idecode_time(tuned_model, "update_time")

    task = tuned_model.pop("tuning_task", None)
    if task is not None:
        hype = task.pop("hyperparameters", None)
        if hype is not None:
            hype = Hyperparameters(**hype)
            task["hyperparameters"] = hype

        idecode_time(task, "start_time")
        idecode_time(task, "complete_time")

        snapshots = task.pop("snapshots", None)
        if snapshots is not None:
            for snap in snapshots:
                idecode_time(snap, "compute_time")
            task["snapshots"] = snapshots
        task = TuningTask(**task)
        tuned_model["tuning_task"] = task
    return TunedModel(**tuned_model)


@string_utils.prettyprint
@dataclasses.dataclass
class TunedModel:
    """A dataclass representation of a `protos.TunedModel`."""

    name: str | None = None
    source_model: str | None = None
    base_model: str | None = None
    display_name: str = ""
    description: str = ""
    temperature: float | None = None
    top_p: float | None = None
    top_k: float | None = None
    state: TunedModelState = TunedModelState.STATE_UNSPECIFIED
    create_time: datetime.datetime | None = None
    update_time: datetime.datetime | None = None
    tuning_task: TuningTask | None = None

    @property
    def permissions(self) -> permission_types.Permissions:
        return permission_types.Permissions(self)


@string_utils.prettyprint
@dataclasses.dataclass
class TuningTask:
    start_time: datetime.datetime | None = None
    complete_time: datetime.datetime | None = None
    snapshots: list[TuningSnapshot] = dataclasses.field(default_factory=list)
    hyperparameters: Hyperparameters | None = None


class TuningExampleDict(TypedDict):
    text_input: str
    output: str


TuningExampleOptions = Union[TuningExampleDict, protos.TuningExample, tuple[str, str], list[str]]

# TODO(markdaoust): gs:// URLS? File-type argument for files without extension?
TuningDataOptions = Union[
    pathlib.Path,
    str,
    protos.Dataset,
    Mapping[str, Iterable[str]],
    Iterable[TuningExampleOptions],
]


def encode_tuning_data(
    data: TuningDataOptions, input_key="text_input", output_key="output"
) -> protos.Dataset:
    if isinstance(data, protos.Dataset):
        return data

    if isinstance(data, str):
        # Strings are either URLs or system paths.
        if re.match(r"^\w+://\S+$", data):
            data = _normalize_url(data)
        else:
            # Normalize system paths to use pathlib
            data = pathlib.Path(data)

    if isinstance(data, (str, pathlib.Path)):
        if isinstance(data, str):
            f = urllib.request.urlopen(data)
            # csv needs strings, json does not.
            content = (line.decode("utf-8") for line in f)
        else:
            f = data.open("r")
            content = f

        if str(data).lower().endswith(".json"):
            with f:
                data = json.load(f)
        else:
            with f:
                data = csv.DictReader(content)
                return _convert_iterable(data, input_key, output_key)

    if hasattr(data, "keys"):
        return _convert_dict(data, input_key, output_key)
    else:
        return _convert_iterable(data, input_key, output_key)


def _normalize_url(url: str) -> str:
    sheet_base = "https://docs.google.com/spreadsheets"
    if url.startswith(sheet_base):
        # Normalize google-sheets URLs to download the csv.
        id_match = re.match(f"{sheet_base}/d/[^/]+", url)
        if id_match is None:
            raise ValueError("Incomplete Google Sheets URL: {data}")

        if tab_match := re.search(r"gid=(\d+)", url):
            tab_param = f"&gid={tab_match.group(1)}"
        else:
            tab_param = ""

        url = f"{id_match.group(0)}/export?format=csv{tab_param}"

    return url


def _convert_dict(data, input_key, output_key):
    new_data = list()

    try:
        inputs = data[input_key]
    except KeyError:
        raise KeyError(
            f"Invalid key: The input key '{input_key}' does not exist in the data. "
            f"Available keys are: {sorted(data.keys())}."
        )

    try:
        outputs = data[output_key]
    except KeyError:
        raise KeyError(
            f"Invalid key: The output key '{output_key}' does not exist in the data. "
            f"Available keys are: {sorted(data.keys())}."
        )

    for i, o in zip(inputs, outputs):
        new_data.append(protos.TuningExample({"text_input": str(i), "output": str(o)}))
    return protos.Dataset(examples=protos.TuningExamples(examples=new_data))


def _convert_iterable(data, input_key, output_key):
    new_data = list()
    for example in data:
        example = encode_tuning_example(example, input_key, output_key)
        new_data.append(example)
    return protos.Dataset(examples=protos.TuningExamples(examples=new_data))


def encode_tuning_example(example: TuningExampleOptions, input_key, output_key):
    if isinstance(example, protos.TuningExample):
        return example
    elif isinstance(example, (tuple, list)):
        a, b = example
        example = protos.TuningExample(text_input=a, output=b)
    else:  # dict
        example = protos.TuningExample(text_input=example[input_key], output=example[output_key])
    return example


@string_utils.prettyprint
@dataclasses.dataclass
class TuningSnapshot:
    step: int
    epoch: int
    mean_score: float
    compute_time: datetime.datetime


@string_utils.prettyprint
@dataclasses.dataclass
class Hyperparameters:
    epoch_count: int = 0
    batch_size: int = 0
    learning_rate: float = 0.0


BaseModelNameOptions = Union[str, Model, protos.Model]
TunedModelNameOptions = Union[str, TunedModel, protos.TunedModel]
AnyModelNameOptions = Union[str, Model, protos.Model, TunedModel, protos.TunedModel]
ModelNameOptions = AnyModelNameOptions


def make_model_name(name: AnyModelNameOptions):
    if isinstance(name, (Model, protos.Model, TunedModel, protos.TunedModel)):
        name = name.name  # pytype: disable=attribute-error
    elif isinstance(name, str):
        name = name
    else:
        raise TypeError(
            "Invalid input type. Expected one of the following types: `str`, `Model`, or `TunedModel`."
        )

    if not (name.startswith("models/") or name.startswith("tunedModels/")):
        raise ValueError(
            f"Invalid model name: '{name}'. Model names should start with 'models/' or 'tunedModels/'."
        )

    return name


ModelsIterable = Iterable[Model]
TunedModelsIterable = Iterable[TunedModel]


@string_utils.prettyprint
@dataclasses.dataclass
class TokenCount:
    """A dataclass representation of a `protos.TokenCountResponse`.

    Attributes:
        token_count: The number of tokens returned by the model's tokenizer for the `input_text`.
        token_count_limit:
    """

    token_count: int
    token_count_limit: int

    def over_limit(self):
        return self.token_count > self.token_count_limit

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\serialization\_dduf.py ===
import json
import logging
import mmap
import os
import shutil
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, Tuple, Union

from ..errors import DDUFCorruptedFileError, DDUFExportError, DDUFInvalidEntryNameError


logger = logging.getLogger(__name__)

DDUF_ALLOWED_ENTRIES = {
    # Allowed file extensions in a DDUF file
    ".json",
    ".model",
    ".safetensors",
    ".txt",
}

DDUF_FOLDER_REQUIRED_ENTRIES = {
    # Each folder must contain at least one of these entries
    "config.json",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "scheduler_config.json",
}


@dataclass
class DDUFEntry:
    """Object representing a file entry in a DDUF file.

    See [`read_dduf_file`] for how to read a DDUF file.

    Attributes:
        filename (str):
            The name of the file in the DDUF archive.
        offset (int):
            The offset of the file in the DDUF archive.
        length (int):
            The length of the file in the DDUF archive.
        dduf_path (str):
            The path to the DDUF archive (for internal use).
    """

    filename: str
    length: int
    offset: int

    dduf_path: Path = field(repr=False)

    @contextmanager
    def as_mmap(self) -> Generator[bytes, None, None]:
        """Open the file as a memory-mapped file.

        Useful to load safetensors directly from the file.

        Example:
            ```py
            >>> import safetensors.torch
            >>> with entry.as_mmap() as mm:
            ...     tensors = safetensors.torch.load(mm)
            ```
        """
        with self.dduf_path.open("rb") as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mm:
                yield mm[self.offset : self.offset + self.length]

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read the file as text.

        Useful for '.txt' and '.json' entries.

        Example:
            ```py
            >>> import json
            >>> index = json.loads(entry.read_text())
            ```
        """
        with self.dduf_path.open("rb") as f:
            f.seek(self.offset)
            return f.read(self.length).decode(encoding=encoding)


def read_dduf_file(dduf_path: Union[os.PathLike, str]) -> Dict[str, DDUFEntry]:
    """
    Read a DDUF file and return a dictionary of entries.

    Only the metadata is read, the data is not loaded in memory.

    Args:
        dduf_path (`str` or `os.PathLike`):
            The path to the DDUF file to read.

    Returns:
        `Dict[str, DDUFEntry]`:
            A dictionary of [`DDUFEntry`] indexed by filename.

    Raises:
        - [`DDUFCorruptedFileError`]: If the DDUF file is corrupted (i.e. doesn't follow the DDUF format).

    Example:
        ```python
        >>> import json
        >>> import safetensors.torch
        >>> from huggingface_hub import read_dduf_file

        # Read DDUF metadata
        >>> dduf_entries = read_dduf_file("FLUX.1-dev.dduf")

        # Returns a mapping filename <> DDUFEntry
        >>> dduf_entries["model_index.json"]
        DDUFEntry(filename='model_index.json', offset=66, length=587)

        # Load model index as JSON
        >>> json.loads(dduf_entries["model_index.json"].read_text())
        {'_class_name': 'FluxPipeline', '_diffusers_version': '0.32.0.dev0', '_name_or_path': 'black-forest-labs/FLUX.1-dev', ...

        # Load VAE weights using safetensors
        >>> with dduf_entries["vae/diffusion_pytorch_model.safetensors"].as_mmap() as mm:
        ...     state_dict = safetensors.torch.load(mm)
        ```
    """
    entries = {}
    dduf_path = Path(dduf_path)
    logger.info(f"Reading DDUF file {dduf_path}")
    with zipfile.ZipFile(str(dduf_path), "r") as zf:
        for info in zf.infolist():
            logger.debug(f"Reading entry {info.filename}")
            if info.compress_type != zipfile.ZIP_STORED:
                raise DDUFCorruptedFileError("Data must not be compressed in DDUF file.")

            try:
                _validate_dduf_entry_name(info.filename)
            except DDUFInvalidEntryNameError as e:
                raise DDUFCorruptedFileError(f"Invalid entry name in DDUF file: {info.filename}") from e

            offset = _get_data_offset(zf, info)

            entries[info.filename] = DDUFEntry(
                filename=info.filename, offset=offset, length=info.file_size, dduf_path=dduf_path
            )

    # Consistency checks on the DDUF file
    if "model_index.json" not in entries:
        raise DDUFCorruptedFileError("Missing required 'model_index.json' entry in DDUF file.")
    index = json.loads(entries["model_index.json"].read_text())
    _validate_dduf_structure(index, entries.keys())

    logger.info(f"Done reading DDUF file {dduf_path}. Found {len(entries)} entries")
    return entries


def export_entries_as_dduf(
    dduf_path: Union[str, os.PathLike], entries: Iterable[Tuple[str, Union[str, Path, bytes]]]
) -> None:
    """Write a DDUF file from an iterable of entries.

    This is a lower-level helper than [`export_folder_as_dduf`] that allows more flexibility when serializing data.
    In particular, you don't need to save the data on disk before exporting it in the DDUF file.

    Args:
        dduf_path (`str` or `os.PathLike`):
            The path to the DDUF file to write.
        entries (`Iterable[Tuple[str, Union[str, Path, bytes]]]`):
            An iterable of entries to write in the DDUF file. Each entry is a tuple with the filename and the content.
            The filename should be the path to the file in the DDUF archive.
            The content can be a string or a pathlib.Path representing a path to a file on the local disk or directly the content as bytes.

    Raises:
        - [`DDUFExportError`]: If anything goes wrong during the export (e.g. invalid entry name, missing 'model_index.json', etc.).

    Example:
        ```python
        # Export specific files from the local disk.
        >>> from huggingface_hub import export_entries_as_dduf
        >>> export_entries_as_dduf(
        ...     dduf_path="stable-diffusion-v1-4-FP16.dduf",
        ...     entries=[ # List entries to add to the DDUF file (here, only FP16 weights)
        ...         ("model_index.json", "path/to/model_index.json"),
        ...         ("vae/config.json", "path/to/vae/config.json"),
        ...         ("vae/diffusion_pytorch_model.fp16.safetensors", "path/to/vae/diffusion_pytorch_model.fp16.safetensors"),
        ...         ("text_encoder/config.json", "path/to/text_encoder/config.json"),
        ...         ("text_encoder/model.fp16.safetensors", "path/to/text_encoder/model.fp16.safetensors"),
        ...         # ... add more entries here
        ...     ]
        ... )
        ```

        ```python
        # Export state_dicts one by one from a loaded pipeline
        >>> from diffusers import DiffusionPipeline
        >>> from typing import Generator, Tuple
        >>> import safetensors.torch
        >>> from huggingface_hub import export_entries_as_dduf
        >>> pipe = DiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4")
        ... # ... do some work with the pipeline

        >>> def as_entries(pipe: DiffusionPipeline) -> Generator[Tuple[str, bytes], None, None]:
        ...     # Build an generator that yields the entries to add to the DDUF file.
        ...     # The first element of the tuple is the filename in the DDUF archive (must use UNIX separator!). The second element is the content of the file.
        ...     # Entries will be evaluated lazily when the DDUF file is created (only 1 entry is loaded in memory at a time)
        ...     yield "vae/config.json", pipe.vae.to_json_string().encode()
        ...     yield "vae/diffusion_pytorch_model.safetensors", safetensors.torch.save(pipe.vae.state_dict())
        ...     yield "text_encoder/config.json", pipe.text_encoder.config.to_json_string().encode()
        ...     yield "text_encoder/model.safetensors", safetensors.torch.save(pipe.text_encoder.state_dict())
        ...     # ... add more entries here

        >>> export_entries_as_dduf(dduf_path="stable-diffusion-v1-4.dduf", entries=as_entries(pipe))
        ```
    """
    logger.info(f"Exporting DDUF file '{dduf_path}'")
    filenames = set()
    index = None
    with zipfile.ZipFile(str(dduf_path), "w", zipfile.ZIP_STORED) as archive:
        for filename, content in entries:
            if filename in filenames:
                raise DDUFExportError(f"Can't add duplicate entry: {filename}")
            filenames.add(filename)

            if filename == "model_index.json":
                try:
                    index = json.loads(_load_content(content).decode())
                except json.JSONDecodeError as e:
                    raise DDUFExportError("Failed to parse 'model_index.json'.") from e

            try:
                filename = _validate_dduf_entry_name(filename)
            except DDUFInvalidEntryNameError as e:
                raise DDUFExportError(f"Invalid entry name: {filename}") from e
            logger.debug(f"Adding entry '{filename}' to DDUF file")
            _dump_content_in_archive(archive, filename, content)

    # Consistency checks on the DDUF file
    if index is None:
        raise DDUFExportError("Missing required 'model_index.json' entry in DDUF file.")
    try:
        _validate_dduf_structure(index, filenames)
    except DDUFCorruptedFileError as e:
        raise DDUFExportError("Invalid DDUF file structure.") from e

    logger.info(f"Done writing DDUF file {dduf_path}")


def export_folder_as_dduf(dduf_path: Union[str, os.PathLike], folder_path: Union[str, os.PathLike]) -> None:
    """
    Export a folder as a DDUF file.

    AUses [`export_entries_as_dduf`] under the hood.

    Args:
        dduf_path (`str` or `os.PathLike`):
            The path to the DDUF file to write.
        folder_path (`str` or `os.PathLike`):
            The path to the folder containing the diffusion model.

    Example:
        ```python
        >>> from huggingface_hub import export_folder_as_dduf
        >>> export_folder_as_dduf(dduf_path="FLUX.1-dev.dduf", folder_path="path/to/FLUX.1-dev")
        ```
    """
    folder_path = Path(folder_path)

    def _iterate_over_folder() -> Iterable[Tuple[str, Path]]:
        for path in Path(folder_path).glob("**/*"):
            if not path.is_file():
                continue
            if path.suffix not in DDUF_ALLOWED_ENTRIES:
                logger.debug(f"Skipping file '{path}' (file type not allowed)")
                continue
            path_in_archive = path.relative_to(folder_path)
            if len(path_in_archive.parts) >= 3:
                logger.debug(f"Skipping file '{path}' (nested directories not allowed)")
                continue
            yield path_in_archive.as_posix(), path

    export_entries_as_dduf(dduf_path, _iterate_over_folder())


def _dump_content_in_archive(archive: zipfile.ZipFile, filename: str, content: Union[str, os.PathLike, bytes]) -> None:
    with archive.open(filename, "w", force_zip64=True) as archive_fh:
        if isinstance(content, (str, Path)):
            content_path = Path(content)
            with content_path.open("rb") as content_fh:
                shutil.copyfileobj(content_fh, archive_fh, 1024 * 1024 * 8)  # type: ignore[misc]
        elif isinstance(content, bytes):
            archive_fh.write(content)
        else:
            raise DDUFExportError(f"Invalid content type for {filename}. Must be str, Path or bytes.")


def _load_content(content: Union[str, Path, bytes]) -> bytes:
    """Load the content of an entry as bytes.

    Used only for small checks (not to dump content into archive).
    """
    if isinstance(content, (str, Path)):
        return Path(content).read_bytes()
    elif isinstance(content, bytes):
        return content
    else:
        raise DDUFExportError(f"Invalid content type. Must be str, Path or bytes. Got {type(content)}.")


def _validate_dduf_entry_name(entry_name: str) -> str:
    if "." + entry_name.split(".")[-1] not in DDUF_ALLOWED_ENTRIES:
        raise DDUFInvalidEntryNameError(f"File type not allowed: {entry_name}")
    if "\\" in entry_name:
        raise DDUFInvalidEntryNameError(f"Entry names must use UNIX separators ('/'). Got {entry_name}.")
    entry_name = entry_name.strip("/")
    if entry_name.count("/") > 1:
        raise DDUFInvalidEntryNameError(f"DDUF only supports 1 level of directory. Got {entry_name}.")
    return entry_name


def _validate_dduf_structure(index: Any, entry_names: Iterable[str]) -> None:
    """
    Consistency checks on the DDUF file structure.

    Rules:
    - The 'model_index.json' entry is required and must contain a dictionary.
    - Each folder name must correspond to an entry in 'model_index.json'.
    - Each folder must contain at least a config file ('config.json', 'tokenizer_config.json', 'preprocessor_config.json', 'scheduler_config.json').

    Args:
        index (Any):
            The content of the 'model_index.json' entry.
        entry_names (Iterable[str]):
            The list of entry names in the DDUF file.

    Raises:
        - [`DDUFCorruptedFileError`]: If the DDUF file is corrupted (i.e. doesn't follow the DDUF format).
    """
    if not isinstance(index, dict):
        raise DDUFCorruptedFileError(f"Invalid 'model_index.json' content. Must be a dictionary. Got {type(index)}.")

    dduf_folders = {entry.split("/")[0] for entry in entry_names if "/" in entry}
    for folder in dduf_folders:
        if folder not in index:
            raise DDUFCorruptedFileError(f"Missing required entry '{folder}' in 'model_index.json'.")
        if not any(f"{folder}/{required_entry}" in entry_names for required_entry in DDUF_FOLDER_REQUIRED_ENTRIES):
            raise DDUFCorruptedFileError(
                f"Missing required file in folder '{folder}'. Must contains at least one of {DDUF_FOLDER_REQUIRED_ENTRIES}."
            )


def _get_data_offset(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> int:
    """
    Calculate the data offset for a file in a ZIP archive.

    Args:
        zf (`zipfile.ZipFile`):
            The opened ZIP file. Must be opened in read mode.
        info (`zipfile.ZipInfo`):
            The file info.

    Returns:
        int: The offset of the file data in the ZIP archive.
    """
    if zf.fp is None:
        raise DDUFCorruptedFileError("ZipFile object must be opened in read mode.")

    # Step 1: Get the local file header offset
    header_offset = info.header_offset

    # Step 2: Read the local file header
    zf.fp.seek(header_offset)
    local_file_header = zf.fp.read(30)  # Fixed-size part of the local header

    if len(local_file_header) < 30:
        raise DDUFCorruptedFileError("Incomplete local file header.")

    # Step 3: Parse the header fields to calculate the start of file data
    # Local file header: https://en.wikipedia.org/wiki/ZIP_(file_format)#File_headers
    filename_len = int.from_bytes(local_file_header[26:28], "little")
    extra_field_len = int.from_bytes(local_file_header[28:30], "little")

    # Data offset is after the fixed header, filename, and extra fields
    data_offset = header_offset + 30 + filename_len + extra_field_len

    return data_offset

# === NexusCore/openenv\Lib\site-packages\trio\_core\_io_epoll.py ===
from __future__ import annotations

import contextlib
import select
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Literal

import attrs

from .. import _core
from ._io_common import wake_all
from ._run import Task, _public
from ._wakeup_socketpair import WakeupSocketpair

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from .._core import Abort, RaiseCancelT
    from .._file_io import _HasFileNo


@attrs.define(eq=False)
class EpollWaiters:
    read_task: Task | None = None
    write_task: Task | None = None
    current_flags: int = 0


assert not TYPE_CHECKING or sys.platform == "linux"


EventResult: TypeAlias = "list[tuple[int, int]]"


@attrs.frozen(eq=False)
class _EpollStatistics:
    tasks_waiting_read: int
    tasks_waiting_write: int
    backend: Literal["epoll"] = attrs.field(init=False, default="epoll")


# Some facts about epoll
# ----------------------
#
# Internally, an epoll object is sort of like a WeakKeyDictionary where the
# keys are tuples of (fd number, file object). When you call epoll_ctl, you
# pass in an fd; that gets converted to an (fd number, file object) tuple by
# looking up the fd in the process's fd table at the time of the call. When an
# event happens on the file object, epoll_wait drops the file object part, and
# just returns the fd number in its event. So from the outside it looks like
# it's keeping a table of fds, but really it's a bit more complicated. This
# has some subtle consequences.
#
# In general, file objects inside the kernel are reference counted. Each entry
# in a process's fd table holds a strong reference to the corresponding file
# object, and most operations that use file objects take a temporary strong
# reference while they're working. So when you call close() on an fd, that
# might or might not cause the file object to be deallocated -- it depends on
# whether there are any other references to that file object. Some common ways
# this can happen:
#
# - after calling dup(), you have two fds in the same process referring to the
#   same file object. Even if you close one fd (= remove that entry from the
#   fd table), the file object will be kept alive by the other fd.
# - when calling fork(), the child inherits a copy of the parent's fd table,
#   so all the file objects get another reference. (But if the fork() is
#   followed by exec(), then all of the child's fds that have the CLOEXEC flag
#   set will be closed at that point.)
# - most syscalls that work on fds take a strong reference to the underlying
#   file object while they're using it. So there's one thread blocked in
#   read(fd), and then another thread calls close() on the last fd referring
#   to that object, the underlying file won't actually be closed until
#   after read() returns.
#
# However, epoll does *not* take a reference to any of the file objects in its
# interest set (that's what makes it similar to a WeakKeyDictionary). File
# objects inside an epoll interest set will be deallocated if all *other*
# references to them are closed. And when that happens, the epoll object will
# automatically deregister that file object and stop reporting events on it.
# So that's quite handy.
#
# But, what happens if we do this?
#
#   fd1 = open(...)
#   epoll_ctl(EPOLL_CTL_ADD, fd1, ...)
#   fd2 = dup(fd1)
#   close(fd1)
#
# In this case, the dup() keeps the underlying file object alive, so it
# remains registered in the epoll object's interest set, as the tuple (fd1,
# file object). But, fd1 no longer refers to this file object! You might think
# there was some magic to handle this, but unfortunately no; the consequences
# are totally predictable from what I said above:
#
# If any events occur on the file object, then epoll will report them as
# happening on fd1, even though that doesn't make sense.
#
# Perhaps we would like to deregister fd1 to stop getting nonsensical events.
# But how? When we call epoll_ctl, we have to pass an fd number, which will
# get expanded to an (fd number, file object) tuple. We can't pass fd1,
# because when epoll_ctl tries to look it up, it won't find our file object.
# And we can't pass fd2, because that will get expanded to (fd2, file object),
# which is a different lookup key. In fact, it's *impossible* to de-register
# this fd!
#
# We could even have fd1 get assigned to another file object, and then we can
# have multiple keys registered simultaneously using the same fd number, like:
# (fd1, file object 1), (fd1, file object 2). And if events happen on either
# file object, then epoll will happily report that something happened to
# "fd1".
#
# Now here's what makes this especially nasty: suppose the old file object
# becomes, say, readable. That means that every time we call epoll_wait, it
# will return immediately to tell us that "fd1" is readable. Normally, we
# would handle this by de-registering fd1, waking up the corresponding call to
# wait_readable, then the user will call read() or recv() or something, and
# we're fine. But if this happens on a stale fd where we can't remove the
# registration, then we might get stuck in a state where epoll_wait *always*
# returns immediately, so our event loop becomes unable to sleep, and now our
# program is burning 100% of the CPU doing nothing, with no way out.
#
#
# What does this mean for Trio?
# -----------------------------
#
# Since we don't control the user's code, we have no way to guarantee that we
# don't get stuck with stale fd's in our epoll interest set. For example, a
# user could call wait_readable(fd) in one task, and then while that's
# running, they might close(fd) from another task. In this situation, they're
# *supposed* to call notify_closing(fd) to let us know what's happening, so we
# can interrupt the wait_readable() call and avoid getting into this mess. And
# that's the only thing that can possibly work correctly in all cases. But
# sometimes user code has bugs. So if this does happen, we'd like to degrade
# gracefully, and survive without corrupting Trio's internal state or
# otherwise causing the whole program to explode messily.
#
# Our solution: we always use EPOLLONESHOT. This way, we might get *one*
# spurious event on a stale fd, but then epoll will automatically silence it
# until we explicitly say that we want more events... and if we have a stale
# fd, then we actually can't re-enable it! So we can't get stuck in an
# infinite busy-loop. If there's a stale fd hanging around, then it might
# cause a spurious `BusyResourceError`, or cause one wait_* call to return
# before it should have... but in general, the wait_* functions are allowed to
# have some spurious wakeups; the user code will just attempt the operation,
# get EWOULDBLOCK, and call wait_* again. And the program as a whole will
# survive, any exceptions will propagate, etc.
#
# As a bonus, EPOLLONESHOT also saves us having to explicitly deregister fds
# on the normal wakeup path, so it's a bit more efficient in general.
#
# However, EPOLLONESHOT has a few trade-offs to consider:
#
# First, you can't combine EPOLLONESHOT with EPOLLEXCLUSIVE. This is a bit sad
# in one somewhat rare case: if you have a multi-process server where a group
# of processes all share the same listening socket, then EPOLLEXCLUSIVE can be
# used to avoid "thundering herd" problems when a new connection comes in. But
# this isn't too bad. It's not clear if EPOLLEXCLUSIVE even works for us
# anyway:
#
#   https://stackoverflow.com/questions/41582560/how-does-epolls-epollexclusive-mode-interact-with-level-triggering
#
# And it's not clear that EPOLLEXCLUSIVE is a great approach either:
#
#   https://blog.cloudflare.com/the-sad-state-of-linux-socket-balancing/
#
# And if we do need to support this, we could always add support through some
# more-specialized API in the future. So this isn't a blocker to using
# EPOLLONESHOT.
#
# Second, EPOLLONESHOT does not actually *deregister* the fd after delivering
# an event (EPOLL_CTL_DEL). Instead, it keeps the fd registered, but
# effectively does an EPOLL_CTL_MOD to set the fd's interest flags to
# all-zeros. So we could still end up with an fd hanging around in the
# interest set for a long time, even if we're not using it.
#
# Fortunately, this isn't a problem, because it's only a weak reference – if
# we have a stale fd that's been silenced by EPOLLONESHOT, then it wastes a
# tiny bit of kernel memory remembering this fd that can never be revived, but
# when the underlying file object is eventually closed, that memory will be
# reclaimed. So that's OK.
#
# The other issue is that when someone calls wait_*, using EPOLLONESHOT means
# that if we have ever waited for this fd before, we have to use EPOLL_CTL_MOD
# to re-enable it; but if it's a new fd, we have to use EPOLL_CTL_ADD. How do
# we know which one to use? There's no reasonable way to track which fds are
# currently registered -- remember, we're assuming the user might have gone
# and rearranged their fds without telling us!
#
# Fortunately, this also has a simple solution: if we wait on a socket or
# other fd once, then we'll probably wait on it lots of times. And the epoll
# object itself knows which fds it already has registered. So when an fd comes
# in, we optimistically assume that it's been waited on before, and try doing
# EPOLL_CTL_MOD. And if that fails with an ENOENT error, then we try again
# with EPOLL_CTL_ADD.
#
# So that's why this code is the way it is. And now you know more than you
# wanted to about how epoll works.


@attrs.define(eq=False)
class EpollIOManager:
    # Using lambda here because otherwise crash on import with gevent monkey patching
    # See https://github.com/python-trio/trio/issues/2848
    _epoll: select.epoll = attrs.Factory(lambda: select.epoll())
    # {fd: EpollWaiters}
    _registered: defaultdict[int, EpollWaiters] = attrs.Factory(
        lambda: defaultdict(EpollWaiters),
    )
    _force_wakeup: WakeupSocketpair = attrs.Factory(WakeupSocketpair)
    _force_wakeup_fd: int | None = None

    def __attrs_post_init__(self) -> None:
        self._epoll.register(self._force_wakeup.wakeup_sock, select.EPOLLIN)
        self._force_wakeup_fd = self._force_wakeup.wakeup_sock.fileno()

    def statistics(self) -> _EpollStatistics:
        tasks_waiting_read = 0
        tasks_waiting_write = 0
        for waiter in self._registered.values():
            if waiter.read_task is not None:
                tasks_waiting_read += 1
            if waiter.write_task is not None:
                tasks_waiting_write += 1
        return _EpollStatistics(
            tasks_waiting_read=tasks_waiting_read,
            tasks_waiting_write=tasks_waiting_write,
        )

    def close(self) -> None:
        self._epoll.close()
        self._force_wakeup.close()

    def force_wakeup(self) -> None:
        self._force_wakeup.wakeup_thread_and_signal_safe()

    # Return value must be False-y IFF the timeout expired, NOT if any I/O
    # happened or force_wakeup was called. Otherwise it can be anything; gets
    # passed straight through to process_events.
    def get_events(self, timeout: float) -> EventResult:
        # max_events must be > 0 or epoll gets cranky
        # accessing self._registered from a thread looks dangerous, but it's
        # OK because it doesn't matter if our value is a little bit off.
        max_events = max(1, len(self._registered))
        return self._epoll.poll(timeout, max_events)

    def process_events(self, events: EventResult) -> None:
        for fd, flags in events:
            if fd == self._force_wakeup_fd:
                self._force_wakeup.drain()
                continue
            waiters = self._registered[fd]
            # EPOLLONESHOT always clears the flags when an event is delivered
            waiters.current_flags = 0
            # Clever hack stolen from selectors.EpollSelector: an event
            # with EPOLLHUP or EPOLLERR flags wakes both readers and
            # writers.
            if flags & ~select.EPOLLIN and waiters.write_task is not None:
                _core.reschedule(waiters.write_task)
                waiters.write_task = None
            if flags & ~select.EPOLLOUT and waiters.read_task is not None:
                _core.reschedule(waiters.read_task)
                waiters.read_task = None
            self._update_registrations(fd)

    def _update_registrations(self, fd: int) -> None:
        waiters = self._registered[fd]
        wanted_flags = 0
        if waiters.read_task is not None:
            wanted_flags |= select.EPOLLIN
        if waiters.write_task is not None:
            wanted_flags |= select.EPOLLOUT
        if wanted_flags != waiters.current_flags:
            try:
                try:
                    # First try EPOLL_CTL_MOD
                    self._epoll.modify(fd, wanted_flags | select.EPOLLONESHOT)
                except OSError:
                    # If that fails, it might be a new fd; try EPOLL_CTL_ADD
                    self._epoll.register(fd, wanted_flags | select.EPOLLONESHOT)
                waiters.current_flags = wanted_flags
            except OSError as exc:
                # If everything fails, probably it's a bad fd, e.g. because
                # the fd was closed behind our back. In this case we don't
                # want to try to unregister the fd, because that will probably
                # fail too. Just clear our state and wake everyone up.
                del self._registered[fd]
                # This could raise (in case we're calling this inside one of
                # the to-be-woken tasks), so we have to do it last.
                wake_all(waiters, exc)
                return
        if not wanted_flags:
            del self._registered[fd]

    async def _epoll_wait(self, fd: int | _HasFileNo, attr_name: str) -> None:
        if not isinstance(fd, int):
            fd = fd.fileno()
        waiters = self._registered[fd]
        if getattr(waiters, attr_name) is not None:
            raise _core.BusyResourceError(
                "another task is already reading / writing this fd",
            )
        setattr(waiters, attr_name, _core.current_task())
        self._update_registrations(fd)

        def abort(_: RaiseCancelT) -> Abort:
            setattr(waiters, attr_name, None)
            self._update_registrations(fd)
            return _core.Abort.SUCCEEDED

        await _core.wait_task_rescheduled(abort)

    @_public
    async def wait_readable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is readable.

        On Unix systems, ``fd`` must either be an integer file descriptor,
        or else an object with a ``.fileno()`` method which returns an
        integer file descriptor. Any kind of file descriptor can be passed,
        though the exact semantics will depend on your kernel. For example,
        this probably won't do anything useful for on-disk files.

        On Windows systems, ``fd`` must either be an integer ``SOCKET``
        handle, or else an object with a ``.fileno()`` method which returns
        an integer ``SOCKET`` handle. File descriptors aren't supported,
        and neither are handles that refer to anything besides a
        ``SOCKET``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become readable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._epoll_wait(fd, "read_task")

    @_public
    async def wait_writable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is writable.

        See `wait_readable` for the definition of ``fd``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become writable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._epoll_wait(fd, "write_task")

    @_public
    def notify_closing(self, fd: int | _HasFileNo) -> None:
        """Notify waiters of the given object that it will be closed.

        Call this before closing a file descriptor (on Unix) or socket (on
        Windows). This will cause any `wait_readable` or `wait_writable`
        calls on the given object to immediately wake up and raise
        `~trio.ClosedResourceError`.

        This doesn't actually close the object – you still have to do that
        yourself afterwards. Also, you want to be careful to make sure no
        new tasks start waiting on the object in between when you call this
        and when it's actually closed. So to close something properly, you
        usually want to do these steps in order:

        1. Explicitly mark the object as closed, so that any new attempts
           to use it will abort before they start.
        2. Call `notify_closing` to wake up any already-existing users.
        3. Actually close the object.

        It's also possible to do them in a different order if that's more
        convenient, *but only if* you make sure not to have any checkpoints in
        between the steps. This way they all happen in a single atomic
        step, so other tasks won't be able to tell what order they happened
        in anyway.
        """
        if not isinstance(fd, int):
            fd = fd.fileno()
        wake_all(
            self._registered[fd],
            _core.ClosedResourceError("another task closed this fd"),
        )
        del self._registered[fd]
        with contextlib.suppress(OSError, ValueError):
            self._epoll.unregister(fd)

# === NexusCore/openenv\Lib\site-packages\jedi\api\refactoring\extract.py ===
from textwrap import dedent

from parso import split_lines

from jedi import debug
from jedi.api.exceptions import RefactoringError
from jedi.api.refactoring import Refactoring, EXPRESSION_PARTS
from jedi.common import indent_block
from jedi.parser_utils import function_is_classmethod, function_is_staticmethod


_DEFINITION_SCOPES = ('suite', 'file_input')
_VARIABLE_EXCTRACTABLE = EXPRESSION_PARTS + \
    ('atom testlist_star_expr testlist test lambdef lambdef_nocond '
     'keyword name number string fstring').split()


def extract_variable(inference_state, path, module_node, name, pos, until_pos):
    nodes = _find_nodes(module_node, pos, until_pos)
    debug.dbg('Extracting nodes: %s', nodes)

    is_expression, message = _is_expression_with_error(nodes)
    if not is_expression:
        raise RefactoringError(message)

    generated_code = name + ' = ' + _expression_nodes_to_string(nodes)
    file_to_node_changes = {path: _replace(nodes, name, generated_code, pos)}
    return Refactoring(inference_state, file_to_node_changes)


def _is_expression_with_error(nodes):
    """
    Returns a tuple (is_expression, error_string).
    """
    if any(node.type == 'name' and node.is_definition() for node in nodes):
        return False, 'Cannot extract a name that defines something'

    if nodes[0].type not in _VARIABLE_EXCTRACTABLE:
        return False, 'Cannot extract a "%s"' % nodes[0].type
    return True, ''


def _find_nodes(module_node, pos, until_pos):
    """
    Looks up a module and tries to find the appropriate amount of nodes that
    are in there.
    """
    start_node = module_node.get_leaf_for_position(pos, include_prefixes=True)

    if until_pos is None:
        if start_node.type == 'operator':
            next_leaf = start_node.get_next_leaf()
            if next_leaf is not None and next_leaf.start_pos == pos:
                start_node = next_leaf

        if _is_not_extractable_syntax(start_node):
            start_node = start_node.parent

        if start_node.parent.type == 'trailer':
            start_node = start_node.parent.parent
        while start_node.parent.type in EXPRESSION_PARTS:
            start_node = start_node.parent

        nodes = [start_node]
    else:
        # Get the next leaf if we are at the end of a leaf
        if start_node.end_pos == pos:
            next_leaf = start_node.get_next_leaf()
            if next_leaf is not None:
                start_node = next_leaf

        # Some syntax is not exactable, just use its parent
        if _is_not_extractable_syntax(start_node):
            start_node = start_node.parent

        # Find the end
        end_leaf = module_node.get_leaf_for_position(until_pos, include_prefixes=True)
        if end_leaf.start_pos > until_pos:
            end_leaf = end_leaf.get_previous_leaf()
            if end_leaf is None:
                raise RefactoringError('Cannot extract anything from that')

        parent_node = start_node
        while parent_node.end_pos < end_leaf.end_pos:
            parent_node = parent_node.parent

        nodes = _remove_unwanted_expression_nodes(parent_node, pos, until_pos)

    # If the user marks just a return statement, we return the expression
    # instead of the whole statement, because the user obviously wants to
    # extract that part.
    if len(nodes) == 1 and start_node.type in ('return_stmt', 'yield_expr'):
        return [nodes[0].children[1]]
    return nodes


def _replace(nodes, expression_replacement, extracted, pos,
             insert_before_leaf=None, remaining_prefix=None):
    # Now try to replace the nodes found with a variable and move the code
    # before the current statement.
    definition = _get_parent_definition(nodes[0])
    if insert_before_leaf is None:
        insert_before_leaf = definition.get_first_leaf()
    first_node_leaf = nodes[0].get_first_leaf()

    lines = split_lines(insert_before_leaf.prefix, keepends=True)
    if first_node_leaf is insert_before_leaf:
        if remaining_prefix is not None:
            # The remaining prefix has already been calculated.
            lines[:-1] = remaining_prefix
    lines[-1:-1] = [indent_block(extracted, lines[-1]) + '\n']
    extracted_prefix = ''.join(lines)

    replacement_dct = {}
    if first_node_leaf is insert_before_leaf:
        replacement_dct[nodes[0]] = extracted_prefix + expression_replacement
    else:
        if remaining_prefix is None:
            p = first_node_leaf.prefix
        else:
            p = remaining_prefix + _get_indentation(nodes[0])
        replacement_dct[nodes[0]] = p + expression_replacement
        replacement_dct[insert_before_leaf] = extracted_prefix + insert_before_leaf.value

    for node in nodes[1:]:
        replacement_dct[node] = ''
    return replacement_dct


def _expression_nodes_to_string(nodes):
    return ''.join(n.get_code(include_prefix=i != 0) for i, n in enumerate(nodes))


def _suite_nodes_to_string(nodes, pos):
    n = nodes[0]
    prefix, part_of_code = _split_prefix_at(n.get_first_leaf(), pos[0] - 1)
    code = part_of_code + n.get_code(include_prefix=False) \
        + ''.join(n.get_code() for n in nodes[1:])
    return prefix, code


def _split_prefix_at(leaf, until_line):
    """
    Returns a tuple of the leaf's prefix, split at the until_line
    position.
    """
    # second means the second returned part
    second_line_count = leaf.start_pos[0] - until_line
    lines = split_lines(leaf.prefix, keepends=True)
    return ''.join(lines[:-second_line_count]), ''.join(lines[-second_line_count:])


def _get_indentation(node):
    return split_lines(node.get_first_leaf().prefix)[-1]


def _get_parent_definition(node):
    """
    Returns the statement where a node is defined.
    """
    while node is not None:
        if node.parent.type in _DEFINITION_SCOPES:
            return node
        node = node.parent
    raise NotImplementedError('We should never even get here')


def _remove_unwanted_expression_nodes(parent_node, pos, until_pos):
    """
    This function makes it so for `1 * 2 + 3` you can extract `2 + 3`, even
    though it is not part of the expression.
    """
    typ = parent_node.type
    is_suite_part = typ in ('suite', 'file_input')
    if typ in EXPRESSION_PARTS or is_suite_part:
        nodes = parent_node.children
        for i, n in enumerate(nodes):
            if n.end_pos > pos:
                start_index = i
                if n.type == 'operator':
                    start_index -= 1
                break
        for i, n in reversed(list(enumerate(nodes))):
            if n.start_pos < until_pos:
                end_index = i
                if n.type == 'operator':
                    end_index += 1

                # Something like `not foo or bar` should not be cut after not
                for n2 in nodes[i:]:
                    if _is_not_extractable_syntax(n2):
                        end_index += 1
                    else:
                        break
                break
        nodes = nodes[start_index:end_index + 1]
        if not is_suite_part:
            nodes[0:1] = _remove_unwanted_expression_nodes(nodes[0], pos, until_pos)
            nodes[-1:] = _remove_unwanted_expression_nodes(nodes[-1], pos, until_pos)
        return nodes
    return [parent_node]


def _is_not_extractable_syntax(node):
    return node.type == 'operator' \
        or node.type == 'keyword' and node.value not in ('None', 'True', 'False')


def extract_function(inference_state, path, module_context, name, pos, until_pos):
    nodes = _find_nodes(module_context.tree_node, pos, until_pos)
    assert len(nodes)

    is_expression, _ = _is_expression_with_error(nodes)
    context = module_context.create_context(nodes[0])
    is_bound_method = context.is_bound_method()
    params, return_variables = list(_find_inputs_and_outputs(module_context, context, nodes))

    # Find variables
    # Is a class method / method
    if context.is_module():
        insert_before_leaf = None  # Leaf will be determined later
    else:
        node = _get_code_insertion_node(context.tree_node, is_bound_method)
        insert_before_leaf = node.get_first_leaf()
    if is_expression:
        code_block = 'return ' + _expression_nodes_to_string(nodes) + '\n'
        remaining_prefix = None
        has_ending_return_stmt = False
    else:
        has_ending_return_stmt = _is_node_ending_return_stmt(nodes[-1])
        if not has_ending_return_stmt:
            # Find the actually used variables (of the defined ones). If none are
            # used (e.g. if the range covers the whole function), return the last
            # defined variable.
            return_variables = list(_find_needed_output_variables(
                context,
                nodes[0].parent,
                nodes[-1].end_pos,
                return_variables
            )) or [return_variables[-1]] if return_variables else []

        remaining_prefix, code_block = _suite_nodes_to_string(nodes, pos)
        after_leaf = nodes[-1].get_next_leaf()
        first, second = _split_prefix_at(after_leaf, until_pos[0])
        code_block += first

        code_block = dedent(code_block)
        if not has_ending_return_stmt:
            output_var_str = ', '.join(return_variables)
            code_block += 'return ' + output_var_str + '\n'

    # Check if we have to raise RefactoringError
    _check_for_non_extractables(nodes[:-1] if has_ending_return_stmt else nodes)

    decorator = ''
    self_param = None
    if is_bound_method:
        if not function_is_staticmethod(context.tree_node):
            function_param_names = context.get_value().get_param_names()
            if len(function_param_names):
                self_param = function_param_names[0].string_name
                params = [p for p in params if p != self_param]

        if function_is_classmethod(context.tree_node):
            decorator = '@classmethod\n'
    else:
        code_block += '\n'

    function_code = '%sdef %s(%s):\n%s' % (
        decorator,
        name,
        ', '.join(params if self_param is None else [self_param] + params),
        indent_block(code_block)
    )

    function_call = '%s(%s)' % (
        ('' if self_param is None else self_param + '.') + name,
        ', '.join(params)
    )
    if is_expression:
        replacement = function_call
    else:
        if has_ending_return_stmt:
            replacement = 'return ' + function_call + '\n'
        else:
            replacement = output_var_str + ' = ' + function_call + '\n'

    replacement_dct = _replace(nodes, replacement, function_code, pos,
                               insert_before_leaf, remaining_prefix)
    if not is_expression:
        replacement_dct[after_leaf] = second + after_leaf.value
    file_to_node_changes = {path: replacement_dct}
    return Refactoring(inference_state, file_to_node_changes)


def _check_for_non_extractables(nodes):
    for n in nodes:
        try:
            children = n.children
        except AttributeError:
            if n.value == 'return':
                raise RefactoringError(
                    'Can only extract return statements if they are at the end.')
            if n.value == 'yield':
                raise RefactoringError('Cannot extract yield statements.')
        else:
            _check_for_non_extractables(children)


def _is_name_input(module_context, names, first, last):
    for name in names:
        if name.api_type == 'param' or not name.parent_context.is_module():
            if name.get_root_context() is not module_context:
                return True
            if name.start_pos is None or not (first <= name.start_pos < last):
                return True
    return False


def _find_inputs_and_outputs(module_context, context, nodes):
    first = nodes[0].start_pos
    last = nodes[-1].end_pos

    inputs = []
    outputs = []
    for name in _find_non_global_names(nodes):
        if name.is_definition():
            if name not in outputs:
                outputs.append(name.value)
        else:
            if name.value not in inputs:
                name_definitions = context.goto(name, name.start_pos)
                if not name_definitions \
                        or _is_name_input(module_context, name_definitions, first, last):
                    inputs.append(name.value)

    # Check if outputs are really needed:
    return inputs, outputs


def _find_non_global_names(nodes):
    for node in nodes:
        try:
            children = node.children
        except AttributeError:
            if node.type == 'name':
                yield node
        else:
            # We only want to check foo in foo.bar
            if node.type == 'trailer' and node.children[0] == '.':
                continue

            yield from _find_non_global_names(children)


def _get_code_insertion_node(node, is_bound_method):
    if not is_bound_method or function_is_staticmethod(node):
        while node.parent.type != 'file_input':
            node = node.parent

    while node.parent.type in ('async_funcdef', 'decorated', 'async_stmt'):
        node = node.parent
    return node


def _find_needed_output_variables(context, search_node, at_least_pos, return_variables):
    """
    Searches everything after at_least_pos in a node and checks if any of the
    return_variables are used in there and returns those.
    """
    for node in search_node.children:
        if node.start_pos < at_least_pos:
            continue

        return_variables = set(return_variables)
        for name in _find_non_global_names([node]):
            if not name.is_definition() and name.value in return_variables:
                return_variables.remove(name.value)
                yield name.value


def _is_node_ending_return_stmt(node):
    t = node.type
    if t == 'simple_stmt':
        return _is_node_ending_return_stmt(node.children[0])
    return t == 'return_stmt'

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_base_server.py ===
# Copyright 2020 The gRPC Authors
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
"""Abstract base classes for server-side classes."""

import abc
from typing import Generic, Iterable, Mapping, NoReturn, Optional, Sequence

import grpc

from ._metadata import Metadata  # pylint: disable=unused-import
from ._typing import DoneCallbackType
from ._typing import MetadataType
from ._typing import RequestType
from ._typing import ResponseType


class Server(abc.ABC):
    """Serves RPCs."""

    @abc.abstractmethod
    def add_generic_rpc_handlers(
        self, generic_rpc_handlers: Sequence[grpc.GenericRpcHandler]
    ) -> None:
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        Args:
          generic_rpc_handlers: A sequence of GenericRpcHandlers that will be
          used to service RPCs.
        """

    @abc.abstractmethod
    def add_insecure_port(self, address: str) -> int:
        """Opens an insecure port for accepting RPCs.

        A port is a communication endpoint that used by networking protocols,
        like TCP and UDP. To date, we only support TCP.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port. If the port is 0,
            or not specified in the address, then the gRPC runtime will choose a port.

        Returns:
          An integer port on which the server will accept RPC requests.
        """

    @abc.abstractmethod
    def add_secure_port(
        self, address: str, server_credentials: grpc.ServerCredentials
    ) -> int:
        """Opens a secure port for accepting RPCs.

        A port is a communication endpoint that used by networking protocols,
        like TCP and UDP. To date, we only support TCP.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port.
            if the port is 0, or not specified in the address, then the gRPC
            runtime will choose a port.
          server_credentials: A ServerCredentials object.

        Returns:
          An integer port on which the server will accept RPC requests.
        """

    @abc.abstractmethod
    async def start(self) -> None:
        """Starts this Server.

        This method may only be called once. (i.e. it is not idempotent).
        """

    @abc.abstractmethod
    async def stop(self, grace: Optional[float]) -> None:
        """Stops this Server.

        This method immediately stops the server from servicing new RPCs in
        all cases.

        If a grace period is specified, this method waits until all active
        RPCs are finished or until the grace period is reached. RPCs that haven't
        been terminated within the grace period are aborted.
        If a grace period is not specified (by passing None for grace), all
        existing RPCs are aborted immediately and this method blocks until
        the last RPC handler terminates.

        This method is idempotent and may be called at any time. Passing a
        smaller grace value in a subsequent call will have the effect of
        stopping the Server sooner (passing None will have the effect of
        stopping the server immediately). Passing a larger grace value in a
        subsequent call will not have the effect of stopping the server later
        (i.e. the most restrictive grace value is used).

        Args:
          grace: A duration of time in seconds or None.
        """

    @abc.abstractmethod
    async def wait_for_termination(
        self, timeout: Optional[float] = None
    ) -> bool:
        """Continues current coroutine once the server stops.

        This is an EXPERIMENTAL API.

        The wait will not consume computational resources during blocking, and
        it will block until one of the two following conditions are met:

        1) The server is stopped or terminated;
        2) A timeout occurs if timeout is not `None`.

        The timeout argument works in the same way as `threading.Event.wait()`.
        https://docs.python.org/3/library/threading.html#threading.Event.wait

        Args:
          timeout: A floating point number specifying a timeout for the
            operation in seconds.

        Returns:
          A bool indicates if the operation times out.
        """

    def add_registered_method_handlers(self, service_name, method_handlers):
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        Args:
          service_name: The service name.
          method_handlers: A dictionary that maps method names to corresponding
            RpcMethodHandler.
        """


# pylint: disable=too-many-public-methods
class ServicerContext(Generic[RequestType, ResponseType], abc.ABC):
    """A context object passed to method implementations."""

    @abc.abstractmethod
    async def read(self) -> RequestType:
        """Reads one message from the RPC.

        Only one read operation is allowed simultaneously.

        Returns:
          A response message of the RPC.

        Raises:
          An RpcError exception if the read failed.
        """

    @abc.abstractmethod
    async def write(self, message: ResponseType) -> None:
        """Writes one message to the RPC.

        Only one write operation is allowed simultaneously.

        Raises:
          An RpcError exception if the write failed.
        """

    @abc.abstractmethod
    async def send_initial_metadata(
        self, initial_metadata: MetadataType
    ) -> None:
        """Sends the initial metadata value to the client.

        This method need not be called by implementations if they have no
        metadata to add to what the gRPC runtime will transmit.

        Args:
          initial_metadata: The initial :term:`metadata`.
        """

    @abc.abstractmethod
    async def abort(
        self,
        code: grpc.StatusCode,
        details: str = "",
        trailing_metadata: MetadataType = tuple(),
    ) -> NoReturn:
        """Raises an exception to terminate the RPC with a non-OK status.

        The code and details passed as arguments will supersede any existing
        ones.

        Args:
          code: A StatusCode object to be sent to the client.
            It must not be StatusCode.OK.
          details: A UTF-8-encodable string to be sent to the client upon
            termination of the RPC.
          trailing_metadata: A sequence of tuple represents the trailing
            :term:`metadata`.

        Raises:
          Exception: An exception is always raised to signal the abortion the
            RPC to the gRPC runtime.
        """

    @abc.abstractmethod
    def set_trailing_metadata(self, trailing_metadata: MetadataType) -> None:
        """Sends the trailing metadata for the RPC.

        This method need not be called by implementations if they have no
        metadata to add to what the gRPC runtime will transmit.

        Args:
          trailing_metadata: The trailing :term:`metadata`.
        """

    @abc.abstractmethod
    def invocation_metadata(self) -> Optional[MetadataType]:
        """Accesses the metadata sent by the client.

        Returns:
          The invocation :term:`metadata`.
        """

    @abc.abstractmethod
    def set_code(self, code: grpc.StatusCode) -> None:
        """Sets the value to be used as status code upon RPC completion.

        This method need not be called by method implementations if they wish
        the gRPC runtime to determine the status code of the RPC.

        Args:
          code: A StatusCode object to be sent to the client.
        """

    @abc.abstractmethod
    def set_details(self, details: str) -> None:
        """Sets the value to be used the as detail string upon RPC completion.

        This method need not be called by method implementations if they have
        no details to transmit.

        Args:
          details: A UTF-8-encodable string to be sent to the client upon
            termination of the RPC.
        """

    @abc.abstractmethod
    def set_compression(self, compression: grpc.Compression) -> None:
        """Set the compression algorithm to be used for the entire call.

        Args:
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.
        """

    @abc.abstractmethod
    def disable_next_message_compression(self) -> None:
        """Disables compression for the next response message.

        This method will override any compression configuration set during
        server creation or set on the call.
        """

    @abc.abstractmethod
    def peer(self) -> str:
        """Identifies the peer that invoked the RPC being serviced.

        Returns:
          A string identifying the peer that invoked the RPC being serviced.
          The string format is determined by gRPC runtime.
        """

    @abc.abstractmethod
    def peer_identities(self) -> Optional[Iterable[bytes]]:
        """Gets one or more peer identity(s).

        Equivalent to
        servicer_context.auth_context().get(servicer_context.peer_identity_key())

        Returns:
          An iterable of the identities, or None if the call is not
          authenticated. Each identity is returned as a raw bytes type.
        """

    @abc.abstractmethod
    def peer_identity_key(self) -> Optional[str]:
        """The auth property used to identify the peer.

        For example, "x509_common_name" or "x509_subject_alternative_name" are
        used to identify an SSL peer.

        Returns:
          The auth property (string) that indicates the
          peer identity, or None if the call is not authenticated.
        """

    @abc.abstractmethod
    def auth_context(self) -> Mapping[str, Iterable[bytes]]:
        """Gets the auth context for the call.

        Returns:
          A map of strings to an iterable of bytes for each auth property.
        """

    def time_remaining(self) -> float:
        """Describes the length of allowed time remaining for the RPC.

        Returns:
          A nonnegative float indicating the length of allowed time in seconds
          remaining for the RPC to complete before it is considered to have
          timed out, or None if no deadline was specified for the RPC.
        """

    def trailing_metadata(self):
        """Access value to be used as trailing metadata upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The trailing :term:`metadata` for the RPC.
        """
        raise NotImplementedError()

    def code(self):
        """Accesses the value to be used as status code upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The StatusCode value for the RPC.
        """
        raise NotImplementedError()

    def details(self):
        """Accesses the value to be used as detail string upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The details string of the RPC.
        """
        raise NotImplementedError()

    def add_done_callback(self, callback: DoneCallbackType) -> None:
        """Registers a callback to be called on RPC termination.

        This is an EXPERIMENTAL API.

        Args:
          callback: A callable object will be called with the servicer context
            object as its only argument.
        """

    def cancelled(self) -> bool:
        """Return True if the RPC is cancelled.

        The RPC is cancelled when the cancellation was requested with cancel().

        This is an EXPERIMENTAL API.

        Returns:
          A bool indicates whether the RPC is cancelled or not.
        """

    def done(self) -> bool:
        """Return True if the RPC is done.

        An RPC is done if the RPC is completed, cancelled or aborted.

        This is an EXPERIMENTAL API.

        Returns:
          A bool indicates if the RPC is done.
        """

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\manifest.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Class representing the list of files in a distribution.

Equivalent to distutils.filelist, but fixes some problems.
"""
import fnmatch
import logging
import os
import re
import sys

from . import DistlibException
from .compat import fsdecode
from .util import convert_path


__all__ = ['Manifest']

logger = logging.getLogger(__name__)

# a \ followed by some spaces + EOL
_COLLAPSE_PATTERN = re.compile('\\\\w*\n', re.M)
_COMMENTED_LINE = re.compile('#.*?(?=\n)|\n(?=$)', re.M | re.S)

#
# Due to the different results returned by fnmatch.translate, we need
# to do slightly different processing for Python 2.7 and 3.2 ... this needed
# to be brought in for Python 3.6 onwards.
#
_PYTHON_VERSION = sys.version_info[:2]


class Manifest(object):
    """
    A list of files built by exploring the filesystem and filtered by applying various
    patterns to what we find there.
    """

    def __init__(self, base=None):
        """
        Initialise an instance.

        :param base: The base directory to explore under.
        """
        self.base = os.path.abspath(os.path.normpath(base or os.getcwd()))
        self.prefix = self.base + os.sep
        self.allfiles = None
        self.files = set()

    #
    # Public API
    #

    def findall(self):
        """Find all files under the base and set ``allfiles`` to the absolute
        pathnames of files found.
        """
        from stat import S_ISREG, S_ISDIR, S_ISLNK

        self.allfiles = allfiles = []
        root = self.base
        stack = [root]
        pop = stack.pop
        push = stack.append

        while stack:
            root = pop()
            names = os.listdir(root)

            for name in names:
                fullname = os.path.join(root, name)

                # Avoid excess stat calls -- just one will do, thank you!
                stat = os.stat(fullname)
                mode = stat.st_mode
                if S_ISREG(mode):
                    allfiles.append(fsdecode(fullname))
                elif S_ISDIR(mode) and not S_ISLNK(mode):
                    push(fullname)

    def add(self, item):
        """
        Add a file to the manifest.

        :param item: The pathname to add. This can be relative to the base.
        """
        if not item.startswith(self.prefix):
            item = os.path.join(self.base, item)
        self.files.add(os.path.normpath(item))

    def add_many(self, items):
        """
        Add a list of files to the manifest.

        :param items: The pathnames to add. These can be relative to the base.
        """
        for item in items:
            self.add(item)

    def sorted(self, wantdirs=False):
        """
        Return sorted files in directory order
        """

        def add_dir(dirs, d):
            dirs.add(d)
            logger.debug('add_dir added %s', d)
            if d != self.base:
                parent, _ = os.path.split(d)
                assert parent not in ('', '/')
                add_dir(dirs, parent)

        result = set(self.files)    # make a copy!
        if wantdirs:
            dirs = set()
            for f in result:
                add_dir(dirs, os.path.dirname(f))
            result |= dirs
        return [os.path.join(*path_tuple) for path_tuple in
                sorted(os.path.split(path) for path in result)]

    def clear(self):
        """Clear all collected files."""
        self.files = set()
        self.allfiles = []

    def process_directive(self, directive):
        """
        Process a directive which either adds some files from ``allfiles`` to
        ``files``, or removes some files from ``files``.

        :param directive: The directive to process. This should be in a format
                     compatible with distutils ``MANIFEST.in`` files:

                     http://docs.python.org/distutils/sourcedist.html#commands
        """
        # Parse the line: split it up, make sure the right number of words
        # is there, and return the relevant words.  'action' is always
        # defined: it's the first word of the line.  Which of the other
        # three are defined depends on the action; it'll be either
        # patterns, (dir and patterns), or (dirpattern).
        action, patterns, thedir, dirpattern = self._parse_directive(directive)

        # OK, now we know that the action is valid and we have the
        # right number of words on the line for that action -- so we
        # can proceed with minimal error-checking.
        if action == 'include':
            for pattern in patterns:
                if not self._include_pattern(pattern, anchor=True):
                    logger.warning('no files found matching %r', pattern)

        elif action == 'exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, anchor=True)

        elif action == 'global-include':
            for pattern in patterns:
                if not self._include_pattern(pattern, anchor=False):
                    logger.warning('no files found matching %r '
                                   'anywhere in distribution', pattern)

        elif action == 'global-exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, anchor=False)

        elif action == 'recursive-include':
            for pattern in patterns:
                if not self._include_pattern(pattern, prefix=thedir):
                    logger.warning('no files found matching %r '
                                   'under directory %r', pattern, thedir)

        elif action == 'recursive-exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, prefix=thedir)

        elif action == 'graft':
            if not self._include_pattern(None, prefix=dirpattern):
                logger.warning('no directories found matching %r',
                               dirpattern)

        elif action == 'prune':
            if not self._exclude_pattern(None, prefix=dirpattern):
                logger.warning('no previously-included directories found '
                               'matching %r', dirpattern)
        else:   # pragma: no cover
            # This should never happen, as it should be caught in
            # _parse_template_line
            raise DistlibException(
                'invalid action %r' % action)

    #
    # Private API
    #

    def _parse_directive(self, directive):
        """
        Validate a directive.
        :param directive: The directive to validate.
        :return: A tuple of action, patterns, thedir, dir_patterns
        """
        words = directive.split()
        if len(words) == 1 and words[0] not in ('include', 'exclude',
                                                'global-include',
                                                'global-exclude',
                                                'recursive-include',
                                                'recursive-exclude',
                                                'graft', 'prune'):
            # no action given, let's use the default 'include'
            words.insert(0, 'include')

        action = words[0]
        patterns = thedir = dir_pattern = None

        if action in ('include', 'exclude',
                      'global-include', 'global-exclude'):
            if len(words) < 2:
                raise DistlibException(
                    '%r expects <pattern1> <pattern2> ...' % action)

            patterns = [convert_path(word) for word in words[1:]]

        elif action in ('recursive-include', 'recursive-exclude'):
            if len(words) < 3:
                raise DistlibException(
                    '%r expects <dir> <pattern1> <pattern2> ...' % action)

            thedir = convert_path(words[1])
            patterns = [convert_path(word) for word in words[2:]]

        elif action in ('graft', 'prune'):
            if len(words) != 2:
                raise DistlibException(
                    '%r expects a single <dir_pattern>' % action)

            dir_pattern = convert_path(words[1])

        else:
            raise DistlibException('unknown action %r' % action)

        return action, patterns, thedir, dir_pattern

    def _include_pattern(self, pattern, anchor=True, prefix=None,
                         is_regex=False):
        """Select strings (presumably filenames) from 'self.files' that
        match 'pattern', a Unix-style wildcard (glob) pattern.

        Patterns are not quite the same as implemented by the 'fnmatch'
        module: '*' and '?'  match non-special characters, where "special"
        is platform-dependent: slash on Unix; colon, slash, and backslash on
        DOS/Windows; and colon on Mac OS.

        If 'anchor' is true (the default), then the pattern match is more
        stringent: "*.py" will match "foo.py" but not "foo/bar.py".  If
        'anchor' is false, both of these will match.

        If 'prefix' is supplied, then only filenames starting with 'prefix'
        (itself a pattern) and ending with 'pattern', with anything in between
        them, will match.  'anchor' is ignored in this case.

        If 'is_regex' is true, 'anchor' and 'prefix' are ignored, and
        'pattern' is assumed to be either a string containing a regex or a
        regex object -- no translation is done, the regex is just compiled
        and used as-is.

        Selected strings will be added to self.files.

        Return True if files are found.
        """
        # XXX docstring lying about what the special chars are?
        found = False
        pattern_re = self._translate_pattern(pattern, anchor, prefix, is_regex)

        # delayed loading of allfiles list
        if self.allfiles is None:
            self.findall()

        for name in self.allfiles:
            if pattern_re.search(name):
                self.files.add(name)
                found = True
        return found

    def _exclude_pattern(self, pattern, anchor=True, prefix=None,
                         is_regex=False):
        """Remove strings (presumably filenames) from 'files' that match
        'pattern'.

        Other parameters are the same as for 'include_pattern()', above.
        The list 'self.files' is modified in place. Return True if files are
        found.

        This API is public to allow e.g. exclusion of SCM subdirs, e.g. when
        packaging source distributions
        """
        found = False
        pattern_re = self._translate_pattern(pattern, anchor, prefix, is_regex)
        for f in list(self.files):
            if pattern_re.search(f):
                self.files.remove(f)
                found = True
        return found

    def _translate_pattern(self, pattern, anchor=True, prefix=None,
                           is_regex=False):
        """Translate a shell-like wildcard pattern to a compiled regular
        expression.

        Return the compiled regex.  If 'is_regex' true,
        then 'pattern' is directly compiled to a regex (if it's a string)
        or just returned as-is (assumes it's a regex object).
        """
        if is_regex:
            if isinstance(pattern, str):
                return re.compile(pattern)
            else:
                return pattern

        if _PYTHON_VERSION > (3, 2):
            # ditch start and end characters
            start, _, end = self._glob_to_re('_').partition('_')

        if pattern:
            pattern_re = self._glob_to_re(pattern)
            if _PYTHON_VERSION > (3, 2):
                assert pattern_re.startswith(start) and pattern_re.endswith(end)
        else:
            pattern_re = ''

        base = re.escape(os.path.join(self.base, ''))
        if prefix is not None:
            # ditch end of pattern character
            if _PYTHON_VERSION <= (3, 2):
                empty_pattern = self._glob_to_re('')
                prefix_re = self._glob_to_re(prefix)[:-len(empty_pattern)]
            else:
                prefix_re = self._glob_to_re(prefix)
                assert prefix_re.startswith(start) and prefix_re.endswith(end)
                prefix_re = prefix_re[len(start): len(prefix_re) - len(end)]
            sep = os.sep
            if os.sep == '\\':
                sep = r'\\'
            if _PYTHON_VERSION <= (3, 2):
                pattern_re = '^' + base + sep.join((prefix_re,
                                                    '.*' + pattern_re))
            else:
                pattern_re = pattern_re[len(start): len(pattern_re) - len(end)]
                pattern_re = r'%s%s%s%s.*%s%s' % (start, base, prefix_re, sep,
                                                  pattern_re, end)
        else:  # no prefix -- respect anchor flag
            if anchor:
                if _PYTHON_VERSION <= (3, 2):
                    pattern_re = '^' + base + pattern_re
                else:
                    pattern_re = r'%s%s%s' % (start, base, pattern_re[len(start):])

        return re.compile(pattern_re)

    def _glob_to_re(self, pattern):
        """Translate a shell-like glob pattern to a regular expression.

        Return a string containing the regex.  Differs from
        'fnmatch.translate()' in that '*' does not match "special characters"
        (which are platform-specific).
        """
        pattern_re = fnmatch.translate(pattern)

        # '?' and '*' in the glob pattern become '.' and '.*' in the RE, which
        # IMHO is wrong -- '?' and '*' aren't supposed to match slash in Unix,
        # and by extension they shouldn't match such "special characters" under
        # any OS.  So change all non-escaped dots in the RE to match any
        # character except the special characters (currently: just os.sep).
        sep = os.sep
        if os.sep == '\\':
            # we're using a regex to manipulate a regex, so we need
            # to escape the backslash twice
            sep = r'\\\\'
        escaped = r'\1[^%s]' % sep
        pattern_re = re.sub(r'((?<!\\)(\\\\)*)\.', escaped, pattern_re)
        return pattern_re

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\duration_parser.py ===
"""
Helper utilities for parsing durations - 1s, 1d, 10d, 30d, 1mo, 2mo

duration_in_seconds is used in diff parts of the code base, example 
- Router - Provider budget routing
- Proxy - Key, Team Generation
"""

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def _extract_from_regex(duration: str) -> Tuple[int, str]:
    match = re.match(r"(\d+)(mo|[smhdw]?)", duration)

    if not match:
        raise ValueError("Invalid duration format")

    value, unit = match.groups()
    value = int(value)

    return value, unit


def get_last_day_of_month(year, month):
    # Handle December case
    if month == 12:
        return 31
    # Next month is January, so subtract a day from March 1st
    next_month = datetime(year=year, month=month + 1, day=1)
    last_day_of_month = (next_month - timedelta(days=1)).day
    return last_day_of_month


def duration_in_seconds(duration: str) -> int:
    """
    Parameters:
    - duration:
        - "<number>s" - seconds
        - "<number>m" - minutes
        - "<number>h" - hours
        - "<number>d" - days
        - "<number>w" - weeks
        - "<number>mo" - months

    Returns time in seconds till when budget needs to be reset
    """
    value, unit = _extract_from_regex(duration=duration)

    if unit == "s":
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    elif unit == "w":
        return value * 604800
    elif unit == "mo":
        now = time.time()
        current_time = datetime.fromtimestamp(now)

        if current_time.month == 12:
            target_year = current_time.year + 1
            target_month = 1
        else:
            target_year = current_time.year
            target_month = current_time.month + value

        # Determine the day to set for next month
        target_day = current_time.day
        last_day_of_target_month = get_last_day_of_month(target_year, target_month)

        if target_day > last_day_of_target_month:
            target_day = last_day_of_target_month

        next_month = datetime(
            year=target_year,
            month=target_month,
            day=target_day,
            hour=current_time.hour,
            minute=current_time.minute,
            second=current_time.second,
            microsecond=current_time.microsecond,
        )

        # Calculate the duration until the first day of the next month
        duration_until_next_month = next_month - current_time
        return int(duration_until_next_month.total_seconds())

    else:
        raise ValueError(f"Unsupported duration unit, passed duration: {duration}")


def get_next_standardized_reset_time(
    duration: str, current_time: datetime, timezone_str: str = "UTC"
) -> datetime:
    """
    Get the next standardized reset time based on the duration.

    All durations will reset at predictable intervals, aligned from the current time:
    - Nd: If N=1, reset at next midnight; if N>1, reset every N days from now
    - Nh: Every N hours, aligned to hour boundaries (e.g., 1:00, 2:00)
    - Nm: Every N minutes, aligned to minute boundaries (e.g., 1:05, 1:10)
    - Ns: Every N seconds, aligned to second boundaries

    Parameters:
    - duration: Duration string (e.g. "30s", "30m", "30h", "30d")
    - current_time: Current datetime
    - timezone_str: Timezone string (e.g. "UTC", "US/Eastern", "Asia/Kolkata")

    Returns:
    - Next reset time at a standardized interval in the specified timezone
    """
    # Set up timezone and normalize current time
    current_time, timezone = _setup_timezone(current_time, timezone_str)

    # Parse duration
    value, unit = _parse_duration(duration)
    if value is None:
        # Fall back to default if format is invalid
        return current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

    # Midnight of the current day in the specified timezone
    base_midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Handle different time units
    if unit == "d":
        return _handle_day_reset(current_time, base_midnight, value, timezone)
    elif unit == "h":
        return _handle_hour_reset(current_time, base_midnight, value)
    elif unit == "m":
        return _handle_minute_reset(current_time, base_midnight, value)
    elif unit == "s":
        return _handle_second_reset(current_time, base_midnight, value)
    elif unit == "mo":
        return _handle_month_reset(current_time, base_midnight, value)
    else:
        # Unrecognized unit, default to next midnight
        return base_midnight + timedelta(days=1)


def _setup_timezone(
    current_time: datetime, timezone_str: str = "UTC"
) -> Tuple[datetime, timezone]:
    """Set up timezone and normalize current time to that timezone."""
    try:
        if timezone_str is None:
            tz = timezone.utc
        else:
            # Map common timezone strings to their UTC offsets
            timezone_map = {
                "US/Eastern": timezone(timedelta(hours=-4)),  # EDT
                "US/Pacific": timezone(timedelta(hours=-7)),  # PDT
                "Asia/Kolkata": timezone(timedelta(hours=5, minutes=30)),  # IST
                "Europe/London": timezone(timedelta(hours=1)),  # BST
                "UTC": timezone.utc,
            }
            tz = timezone_map.get(timezone_str, timezone.utc)
    except Exception:
        # If timezone is invalid, fall back to UTC
        tz = timezone.utc

    # Convert current_time to the target timezone
    if current_time.tzinfo is None:
        # Naive datetime - assume it's UTC
        utc_time = current_time.replace(tzinfo=timezone.utc)
        current_time = utc_time.astimezone(tz)
    else:
        # Already has timezone - convert to target timezone
        current_time = current_time.astimezone(tz)

    return current_time, tz


def _parse_duration(duration: str) -> Tuple[Optional[int], Optional[str]]:
    """Parse the duration string into value and unit."""
    match = re.match(r"(\d+)([a-z]+)", duration)
    if not match:
        return None, None

    value, unit = match.groups()
    return int(value), unit


def _handle_day_reset(
    current_time: datetime, base_midnight: datetime, value: int, timezone: timezone
) -> datetime:
    """Handle day-based reset times."""
    if value == 1:  # Daily reset at midnight
        return base_midnight + timedelta(days=1)
    elif value == 7:  # Weekly reset on Monday at midnight
        days_until_monday = (7 - current_time.weekday()) % 7
        if days_until_monday == 0:  # If today is Monday
            days_until_monday = 7
        return base_midnight + timedelta(days=days_until_monday)
    elif value == 30:  # Monthly reset on 1st at midnight
        # Get 1st of next month at midnight
        if current_time.month == 12:
            next_reset = datetime(
                year=current_time.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone,
            )
        else:
            next_reset = datetime(
                year=current_time.year,
                month=current_time.month + 1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=timezone,
            )
        return next_reset
    else:  # Custom day value - next interval is value days from current
        return current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=value)


def _handle_hour_reset(
    current_time: datetime, base_midnight: datetime, value: int
) -> datetime:
    """Handle hour-based reset times."""
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_second = current_time.second
    current_microsecond = current_time.microsecond

    # Calculate next hour aligned with the value
    if current_minute == 0 and current_second == 0 and current_microsecond == 0:
        next_hour = (
            current_hour + value - (current_hour % value)
            if current_hour % value != 0
            else current_hour + value
        )
    else:
        next_hour = (
            current_hour + value - (current_hour % value)
            if current_hour % value != 0
            else current_hour + value
        )

    # Handle overnight case
    if next_hour >= 24:
        next_hour = next_hour % 24
        next_day = base_midnight + timedelta(days=1)
        return next_day.replace(hour=next_hour)

    return current_time.replace(hour=next_hour, minute=0, second=0, microsecond=0)


def _handle_minute_reset(
    current_time: datetime, base_midnight: datetime, value: int
) -> datetime:
    """Handle minute-based reset times."""
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_second = current_time.second
    current_microsecond = current_time.microsecond

    # Calculate next minute aligned with the value
    if current_second == 0 and current_microsecond == 0:
        next_minute = (
            current_minute + value - (current_minute % value)
            if current_minute % value != 0
            else current_minute + value
        )
    else:
        next_minute = (
            current_minute + value - (current_minute % value)
            if current_minute % value != 0
            else current_minute + value
        )

    # Handle hour rollover
    next_hour = current_hour + (next_minute // 60)
    next_minute = next_minute % 60

    # Handle overnight case
    if next_hour >= 24:
        next_hour = next_hour % 24
        next_day = base_midnight + timedelta(days=1)
        return next_day.replace(
            hour=next_hour, minute=next_minute, second=0, microsecond=0
        )

    return current_time.replace(
        hour=next_hour, minute=next_minute, second=0, microsecond=0
    )


def _handle_second_reset(
    current_time: datetime, base_midnight: datetime, value: int
) -> datetime:
    """Handle second-based reset times."""
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_second = current_time.second
    current_microsecond = current_time.microsecond

    # Calculate next second aligned with the value
    if current_microsecond == 0:
        next_second = (
            current_second + value - (current_second % value)
            if current_second % value != 0
            else current_second + value
        )
    else:
        next_second = (
            current_second + value - (current_second % value)
            if current_second % value != 0
            else current_second + value
        )

    # Handle minute rollover
    additional_minutes = next_second // 60
    next_second = next_second % 60
    next_minute = current_minute + additional_minutes

    # Handle hour rollover
    next_hour = current_hour + (next_minute // 60)
    next_minute = next_minute % 60

    # Handle overnight case
    if next_hour >= 24:
        next_hour = next_hour % 24
        next_day = base_midnight + timedelta(days=1)
        return next_day.replace(
            hour=next_hour, minute=next_minute, second=next_second, microsecond=0
        )

    return current_time.replace(
        hour=next_hour, minute=next_minute, second=next_second, microsecond=0
    )


def _handle_month_reset(
    current_time: datetime, base_midnight: datetime, value: int
) -> datetime:
    """
    Handle monthly reset times. For monthly resets, we always reset at the start of the next month.

    Args:
        current_time: Current datetime
        base_midnight: Midnight of current day
        value: Number of months (currently only supports 1 month resets)

    Returns:
        datetime: First day of next month at midnight
    """
    if value != 1:
        raise ValueError("Monthly resets currently only support 1 month intervals")

    # Get the first day of next month
    if current_time.month == 12:
        next_month = 1
        next_year = current_time.year + 1
    else:
        next_month = current_time.month + 1
        next_year = current_time.year

    return datetime(
        year=next_year,
        month=next_month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=current_time.tzinfo,
    )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\manifest.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Class representing the list of files in a distribution.

Equivalent to distutils.filelist, but fixes some problems.
"""
import fnmatch
import logging
import os
import re
import sys

from . import DistlibException
from .compat import fsdecode
from .util import convert_path


__all__ = ['Manifest']

logger = logging.getLogger(__name__)

# a \ followed by some spaces + EOL
_COLLAPSE_PATTERN = re.compile('\\\\w*\n', re.M)
_COMMENTED_LINE = re.compile('#.*?(?=\n)|\n(?=$)', re.M | re.S)

#
# Due to the different results returned by fnmatch.translate, we need
# to do slightly different processing for Python 2.7 and 3.2 ... this needed
# to be brought in for Python 3.6 onwards.
#
_PYTHON_VERSION = sys.version_info[:2]


class Manifest(object):
    """
    A list of files built by exploring the filesystem and filtered by applying various
    patterns to what we find there.
    """

    def __init__(self, base=None):
        """
        Initialise an instance.

        :param base: The base directory to explore under.
        """
        self.base = os.path.abspath(os.path.normpath(base or os.getcwd()))
        self.prefix = self.base + os.sep
        self.allfiles = None
        self.files = set()

    #
    # Public API
    #

    def findall(self):
        """Find all files under the base and set ``allfiles`` to the absolute
        pathnames of files found.
        """
        from stat import S_ISREG, S_ISDIR, S_ISLNK

        self.allfiles = allfiles = []
        root = self.base
        stack = [root]
        pop = stack.pop
        push = stack.append

        while stack:
            root = pop()
            names = os.listdir(root)

            for name in names:
                fullname = os.path.join(root, name)

                # Avoid excess stat calls -- just one will do, thank you!
                stat = os.stat(fullname)
                mode = stat.st_mode
                if S_ISREG(mode):
                    allfiles.append(fsdecode(fullname))
                elif S_ISDIR(mode) and not S_ISLNK(mode):
                    push(fullname)

    def add(self, item):
        """
        Add a file to the manifest.

        :param item: The pathname to add. This can be relative to the base.
        """
        if not item.startswith(self.prefix):
            item = os.path.join(self.base, item)
        self.files.add(os.path.normpath(item))

    def add_many(self, items):
        """
        Add a list of files to the manifest.

        :param items: The pathnames to add. These can be relative to the base.
        """
        for item in items:
            self.add(item)

    def sorted(self, wantdirs=False):
        """
        Return sorted files in directory order
        """

        def add_dir(dirs, d):
            dirs.add(d)
            logger.debug('add_dir added %s', d)
            if d != self.base:
                parent, _ = os.path.split(d)
                assert parent not in ('', '/')
                add_dir(dirs, parent)

        result = set(self.files)    # make a copy!
        if wantdirs:
            dirs = set()
            for f in result:
                add_dir(dirs, os.path.dirname(f))
            result |= dirs
        return [os.path.join(*path_tuple) for path_tuple in
                sorted(os.path.split(path) for path in result)]

    def clear(self):
        """Clear all collected files."""
        self.files = set()
        self.allfiles = []

    def process_directive(self, directive):
        """
        Process a directive which either adds some files from ``allfiles`` to
        ``files``, or removes some files from ``files``.

        :param directive: The directive to process. This should be in a format
                     compatible with distutils ``MANIFEST.in`` files:

                     http://docs.python.org/distutils/sourcedist.html#commands
        """
        # Parse the line: split it up, make sure the right number of words
        # is there, and return the relevant words.  'action' is always
        # defined: it's the first word of the line.  Which of the other
        # three are defined depends on the action; it'll be either
        # patterns, (dir and patterns), or (dirpattern).
        action, patterns, thedir, dirpattern = self._parse_directive(directive)

        # OK, now we know that the action is valid and we have the
        # right number of words on the line for that action -- so we
        # can proceed with minimal error-checking.
        if action == 'include':
            for pattern in patterns:
                if not self._include_pattern(pattern, anchor=True):
                    logger.warning('no files found matching %r', pattern)

        elif action == 'exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, anchor=True)

        elif action == 'global-include':
            for pattern in patterns:
                if not self._include_pattern(pattern, anchor=False):
                    logger.warning('no files found matching %r '
                                   'anywhere in distribution', pattern)

        elif action == 'global-exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, anchor=False)

        elif action == 'recursive-include':
            for pattern in patterns:
                if not self._include_pattern(pattern, prefix=thedir):
                    logger.warning('no files found matching %r '
                                   'under directory %r', pattern, thedir)

        elif action == 'recursive-exclude':
            for pattern in patterns:
                self._exclude_pattern(pattern, prefix=thedir)

        elif action == 'graft':
            if not self._include_pattern(None, prefix=dirpattern):
                logger.warning('no directories found matching %r',
                               dirpattern)

        elif action == 'prune':
            if not self._exclude_pattern(None, prefix=dirpattern):
                logger.warning('no previously-included directories found '
                               'matching %r', dirpattern)
        else:   # pragma: no cover
            # This should never happen, as it should be caught in
            # _parse_template_line
            raise DistlibException(
                'invalid action %r' % action)

    #
    # Private API
    #

    def _parse_directive(self, directive):
        """
        Validate a directive.
        :param directive: The directive to validate.
        :return: A tuple of action, patterns, thedir, dir_patterns
        """
        words = directive.split()
        if len(words) == 1 and words[0] not in ('include', 'exclude',
                                                'global-include',
                                                'global-exclude',
                                                'recursive-include',
                                                'recursive-exclude',
                                                'graft', 'prune'):
            # no action given, let's use the default 'include'
            words.insert(0, 'include')

        action = words[0]
        patterns = thedir = dir_pattern = None

        if action in ('include', 'exclude',
                      'global-include', 'global-exclude'):
            if len(words) < 2:
                raise DistlibException(
                    '%r expects <pattern1> <pattern2> ...' % action)

            patterns = [convert_path(word) for word in words[1:]]

        elif action in ('recursive-include', 'recursive-exclude'):
            if len(words) < 3:
                raise DistlibException(
                    '%r expects <dir> <pattern1> <pattern2> ...' % action)

            thedir = convert_path(words[1])
            patterns = [convert_path(word) for word in words[2:]]

        elif action in ('graft', 'prune'):
            if len(words) != 2:
                raise DistlibException(
                    '%r expects a single <dir_pattern>' % action)

            dir_pattern = convert_path(words[1])

        else:
            raise DistlibException('unknown action %r' % action)

        return action, patterns, thedir, dir_pattern

    def _include_pattern(self, pattern, anchor=True, prefix=None,
                         is_regex=False):
        """Select strings (presumably filenames) from 'self.files' that
        match 'pattern', a Unix-style wildcard (glob) pattern.

        Patterns are not quite the same as implemented by the 'fnmatch'
        module: '*' and '?'  match non-special characters, where "special"
        is platform-dependent: slash on Unix; colon, slash, and backslash on
        DOS/Windows; and colon on Mac OS.

        If 'anchor' is true (the default), then the pattern match is more
        stringent: "*.py" will match "foo.py" but not "foo/bar.py".  If
        'anchor' is false, both of these will match.

        If 'prefix' is supplied, then only filenames starting with 'prefix'
        (itself a pattern) and ending with 'pattern', with anything in between
        them, will match.  'anchor' is ignored in this case.

        If 'is_regex' is true, 'anchor' and 'prefix' are ignored, and
        'pattern' is assumed to be either a string containing a regex or a
        regex object -- no translation is done, the regex is just compiled
        and used as-is.

        Selected strings will be added to self.files.

        Return True if files are found.
        """
        # XXX docstring lying about what the special chars are?
        found = False
        pattern_re = self._translate_pattern(pattern, anchor, prefix, is_regex)

        # delayed loading of allfiles list
        if self.allfiles is None:
            self.findall()

        for name in self.allfiles:
            if pattern_re.search(name):
                self.files.add(name)
                found = True
        return found

    def _exclude_pattern(self, pattern, anchor=True, prefix=None,
                         is_regex=False):
        """Remove strings (presumably filenames) from 'files' that match
        'pattern'.

        Other parameters are the same as for 'include_pattern()', above.
        The list 'self.files' is modified in place. Return True if files are
        found.

        This API is public to allow e.g. exclusion of SCM subdirs, e.g. when
        packaging source distributions
        """
        found = False
        pattern_re = self._translate_pattern(pattern, anchor, prefix, is_regex)
        for f in list(self.files):
            if pattern_re.search(f):
                self.files.remove(f)
                found = True
        return found

    def _translate_pattern(self, pattern, anchor=True, prefix=None,
                           is_regex=False):
        """Translate a shell-like wildcard pattern to a compiled regular
        expression.

        Return the compiled regex.  If 'is_regex' true,
        then 'pattern' is directly compiled to a regex (if it's a string)
        or just returned as-is (assumes it's a regex object).
        """
        if is_regex:
            if isinstance(pattern, str):
                return re.compile(pattern)
            else:
                return pattern

        if _PYTHON_VERSION > (3, 2):
            # ditch start and end characters
            start, _, end = self._glob_to_re('_').partition('_')

        if pattern:
            pattern_re = self._glob_to_re(pattern)
            if _PYTHON_VERSION > (3, 2):
                assert pattern_re.startswith(start) and pattern_re.endswith(end)
        else:
            pattern_re = ''

        base = re.escape(os.path.join(self.base, ''))
        if prefix is not None:
            # ditch end of pattern character
            if _PYTHON_VERSION <= (3, 2):
                empty_pattern = self._glob_to_re('')
                prefix_re = self._glob_to_re(prefix)[:-len(empty_pattern)]
            else:
                prefix_re = self._glob_to_re(prefix)
                assert prefix_re.startswith(start) and prefix_re.endswith(end)
                prefix_re = prefix_re[len(start): len(prefix_re) - len(end)]
            sep = os.sep
            if os.sep == '\\':
                sep = r'\\'
            if _PYTHON_VERSION <= (3, 2):
                pattern_re = '^' + base + sep.join((prefix_re,
                                                    '.*' + pattern_re))
            else:
                pattern_re = pattern_re[len(start): len(pattern_re) - len(end)]
                pattern_re = r'%s%s%s%s.*%s%s' % (start, base, prefix_re, sep,
                                                  pattern_re, end)
        else:  # no prefix -- respect anchor flag
            if anchor:
                if _PYTHON_VERSION <= (3, 2):
                    pattern_re = '^' + base + pattern_re
                else:
                    pattern_re = r'%s%s%s' % (start, base, pattern_re[len(start):])

        return re.compile(pattern_re)

    def _glob_to_re(self, pattern):
        """Translate a shell-like glob pattern to a regular expression.

        Return a string containing the regex.  Differs from
        'fnmatch.translate()' in that '*' does not match "special characters"
        (which are platform-specific).
        """
        pattern_re = fnmatch.translate(pattern)

        # '?' and '*' in the glob pattern become '.' and '.*' in the RE, which
        # IMHO is wrong -- '?' and '*' aren't supposed to match slash in Unix,
        # and by extension they shouldn't match such "special characters" under
        # any OS.  So change all non-escaped dots in the RE to match any
        # character except the special characters (currently: just os.sep).
        sep = os.sep
        if os.sep == '\\':
            # we're using a regex to manipulate a regex, so we need
            # to escape the backslash twice
            sep = r'\\\\'
        escaped = r'\1[^%s]' % sep
        pattern_re = re.sub(r'((?<!\\)(\\\\)*)\.', escaped, pattern_re)
        return pattern_re

# === NexusCore/myenv\Lib\site-packages\pip\_internal\configuration.py ===
"""Configuration management setup

Some terminology:
- name
  As written in config files.
- value
  Value associated with a name
- key
  Name combined with it's section (section.name)
- variant
  A single word describing where the configuration key-value pair came from
"""

import configparser
import locale
import os
import sys
from typing import Any, Dict, Iterable, List, NewType, Optional, Tuple

from pip._internal.exceptions import (
    ConfigurationError,
    ConfigurationFileCouldNotBeLoaded,
)
from pip._internal.utils import appdirs
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import ensure_dir, enum

RawConfigParser = configparser.RawConfigParser  # Shorthand
Kind = NewType("Kind", str)

CONFIG_BASENAME = "pip.ini" if WINDOWS else "pip.conf"
ENV_NAMES_IGNORED = "version", "help"

# The kinds of configurations there are.
kinds = enum(
    USER="user",  # User Specific
    GLOBAL="global",  # System Wide
    SITE="site",  # [Virtual] Environment Specific
    ENV="env",  # from PIP_CONFIG_FILE
    ENV_VAR="env-var",  # from Environment Variables
)
OVERRIDE_ORDER = kinds.GLOBAL, kinds.USER, kinds.SITE, kinds.ENV, kinds.ENV_VAR
VALID_LOAD_ONLY = kinds.USER, kinds.GLOBAL, kinds.SITE

logger = getLogger(__name__)


# NOTE: Maybe use the optionx attribute to normalize keynames.
def _normalize_name(name: str) -> str:
    """Make a name consistent regardless of source (environment or file)"""
    name = name.lower().replace("_", "-")
    if name.startswith("--"):
        name = name[2:]  # only prefer long opts
    return name


def _disassemble_key(name: str) -> List[str]:
    if "." not in name:
        error_message = (
            "Key does not contain dot separated section and key. "
            f"Perhaps you wanted to use 'global.{name}' instead?"
        )
        raise ConfigurationError(error_message)
    return name.split(".", 1)


def get_configuration_files() -> Dict[Kind, List[str]]:
    global_config_files = [
        os.path.join(path, CONFIG_BASENAME) for path in appdirs.site_config_dirs("pip")
    ]

    site_config_file = os.path.join(sys.prefix, CONFIG_BASENAME)
    legacy_config_file = os.path.join(
        os.path.expanduser("~"),
        "pip" if WINDOWS else ".pip",
        CONFIG_BASENAME,
    )
    new_config_file = os.path.join(appdirs.user_config_dir("pip"), CONFIG_BASENAME)
    return {
        kinds.GLOBAL: global_config_files,
        kinds.SITE: [site_config_file],
        kinds.USER: [legacy_config_file, new_config_file],
    }


class Configuration:
    """Handles management of configuration.

    Provides an interface to accessing and managing configuration files.

    This class converts provides an API that takes "section.key-name" style
    keys and stores the value associated with it as "key-name" under the
    section "section".

    This allows for a clean interface wherein the both the section and the
    key-name are preserved in an easy to manage form in the configuration files
    and the data stored is also nice.
    """

    def __init__(self, isolated: bool, load_only: Optional[Kind] = None) -> None:
        super().__init__()

        if load_only is not None and load_only not in VALID_LOAD_ONLY:
            raise ConfigurationError(
                "Got invalid value for load_only - should be one of {}".format(
                    ", ".join(map(repr, VALID_LOAD_ONLY))
                )
            )
        self.isolated = isolated
        self.load_only = load_only

        # Because we keep track of where we got the data from
        self._parsers: Dict[Kind, List[Tuple[str, RawConfigParser]]] = {
            variant: [] for variant in OVERRIDE_ORDER
        }
        self._config: Dict[Kind, Dict[str, Any]] = {
            variant: {} for variant in OVERRIDE_ORDER
        }
        self._modified_parsers: List[Tuple[str, RawConfigParser]] = []

    def load(self) -> None:
        """Loads configuration from configuration files and environment"""
        self._load_config_files()
        if not self.isolated:
            self._load_environment_vars()

    def get_file_to_edit(self) -> Optional[str]:
        """Returns the file with highest priority in configuration"""
        assert self.load_only is not None, "Need to be specified a file to be editing"

        try:
            return self._get_parser_to_modify()[0]
        except IndexError:
            return None

    def items(self) -> Iterable[Tuple[str, Any]]:
        """Returns key-value pairs like dict.items() representing the loaded
        configuration
        """
        return self._dictionary.items()

    def get_value(self, key: str) -> Any:
        """Get a value from the configuration."""
        orig_key = key
        key = _normalize_name(key)
        try:
            return self._dictionary[key]
        except KeyError:
            # disassembling triggers a more useful error message than simply
            # "No such key" in the case that the key isn't in the form command.option
            _disassemble_key(key)
            raise ConfigurationError(f"No such key - {orig_key}")

    def set_value(self, key: str, value: Any) -> None:
        """Modify a value in the configuration."""
        key = _normalize_name(key)
        self._ensure_have_load_only()

        assert self.load_only
        fname, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)

            # Modify the parser and the configuration
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, name, value)

        self._config[self.load_only][key] = value
        self._mark_as_modified(fname, parser)

    def unset_value(self, key: str) -> None:
        """Unset a value in the configuration."""
        orig_key = key
        key = _normalize_name(key)
        self._ensure_have_load_only()

        assert self.load_only
        if key not in self._config[self.load_only]:
            raise ConfigurationError(f"No such key - {orig_key}")

        fname, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)
            if not (
                parser.has_section(section) and parser.remove_option(section, name)
            ):
                # The option was not removed.
                raise ConfigurationError(
                    "Fatal Internal error [id=1]. Please report as a bug."
                )

            # The section may be empty after the option was removed.
            if not parser.items(section):
                parser.remove_section(section)
            self._mark_as_modified(fname, parser)

        del self._config[self.load_only][key]

    def save(self) -> None:
        """Save the current in-memory state."""
        self._ensure_have_load_only()

        for fname, parser in self._modified_parsers:
            logger.info("Writing to %s", fname)

            # Ensure directory exists.
            ensure_dir(os.path.dirname(fname))

            # Ensure directory's permission(need to be writeable)
            try:
                with open(fname, "w") as f:
                    parser.write(f)
            except OSError as error:
                raise ConfigurationError(
                    f"An error occurred while writing to the configuration file "
                    f"{fname}: {error}"
                )

    #
    # Private routines
    #

    def _ensure_have_load_only(self) -> None:
        if self.load_only is None:
            raise ConfigurationError("Needed a specific file to be modifying.")
        logger.debug("Will be working with %s variant only", self.load_only)

    @property
    def _dictionary(self) -> Dict[str, Any]:
        """A dictionary representing the loaded configuration."""
        # NOTE: Dictionaries are not populated if not loaded. So, conditionals
        #       are not needed here.
        retval = {}

        for variant in OVERRIDE_ORDER:
            retval.update(self._config[variant])

        return retval

    def _load_config_files(self) -> None:
        """Loads configuration from configuration files"""
        config_files = dict(self.iter_config_files())
        if config_files[kinds.ENV][0:1] == [os.devnull]:
            logger.debug(
                "Skipping loading configuration files due to "
                "environment's PIP_CONFIG_FILE being os.devnull"
            )
            return

        for variant, files in config_files.items():
            for fname in files:
                # If there's specific variant set in `load_only`, load only
                # that variant, not the others.
                if self.load_only is not None and variant != self.load_only:
                    logger.debug("Skipping file '%s' (variant: %s)", fname, variant)
                    continue

                parser = self._load_file(variant, fname)

                # Keeping track of the parsers used
                self._parsers[variant].append((fname, parser))

    def _load_file(self, variant: Kind, fname: str) -> RawConfigParser:
        logger.verbose("For variant '%s', will try loading '%s'", variant, fname)
        parser = self._construct_parser(fname)

        for section in parser.sections():
            items = parser.items(section)
            self._config[variant].update(self._normalized_keys(section, items))

        return parser

    def _construct_parser(self, fname: str) -> RawConfigParser:
        parser = configparser.RawConfigParser()
        # If there is no such file, don't bother reading it but create the
        # parser anyway, to hold the data.
        # Doing this is useful when modifying and saving files, where we don't
        # need to construct a parser.
        if os.path.exists(fname):
            locale_encoding = locale.getpreferredencoding(False)
            try:
                parser.read(fname, encoding=locale_encoding)
            except UnicodeDecodeError:
                # See https://github.com/pypa/pip/issues/4963
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"contains invalid {locale_encoding} characters",
                    fname=fname,
                )
            except configparser.Error as error:
                # See https://github.com/pypa/pip/issues/4893
                raise ConfigurationFileCouldNotBeLoaded(error=error)
        return parser

    def _load_environment_vars(self) -> None:
        """Loads configuration from environment variables"""
        self._config[kinds.ENV_VAR].update(
            self._normalized_keys(":env:", self.get_environ_vars())
        )

    def _normalized_keys(
        self, section: str, items: Iterable[Tuple[str, Any]]
    ) -> Dict[str, Any]:
        """Normalizes items to construct a dictionary with normalized keys.

        This routine is where the names become keys and are made the same
        regardless of source - configuration files or environment.
        """
        normalized = {}
        for name, val in items:
            key = section + "." + _normalize_name(name)
            normalized[key] = val
        return normalized

    def get_environ_vars(self) -> Iterable[Tuple[str, str]]:
        """Returns a generator with all environmental vars with prefix PIP_"""
        for key, val in os.environ.items():
            if key.startswith("PIP_"):
                name = key[4:].lower()
                if name not in ENV_NAMES_IGNORED:
                    yield name, val

    # XXX: This is patched in the tests.
    def iter_config_files(self) -> Iterable[Tuple[Kind, List[str]]]:
        """Yields variant and configuration files associated with it.

        This should be treated like items of a dictionary. The order
        here doesn't affect what gets overridden. That is controlled
        by OVERRIDE_ORDER. However this does control the order they are
        displayed to the user. It's probably most ergonomic to display
        things in the same order as OVERRIDE_ORDER
        """
        # SMELL: Move the conditions out of this function

        env_config_file = os.environ.get("PIP_CONFIG_FILE", None)
        config_files = get_configuration_files()

        yield kinds.GLOBAL, config_files[kinds.GLOBAL]

        # per-user config is not loaded when env_config_file exists
        should_load_user_config = not self.isolated and not (
            env_config_file and os.path.exists(env_config_file)
        )
        if should_load_user_config:
            # The legacy config file is overridden by the new config file
            yield kinds.USER, config_files[kinds.USER]

        # virtualenv config
        yield kinds.SITE, config_files[kinds.SITE]

        if env_config_file is not None:
            yield kinds.ENV, [env_config_file]
        else:
            yield kinds.ENV, []

    def get_values_in_config(self, variant: Kind) -> Dict[str, Any]:
        """Get values present in a config file"""
        return self._config[variant]

    def _get_parser_to_modify(self) -> Tuple[str, RawConfigParser]:
        # Determine which parser to modify
        assert self.load_only
        parsers = self._parsers[self.load_only]
        if not parsers:
            # This should not happen if everything works correctly.
            raise ConfigurationError(
                "Fatal Internal error [id=2]. Please report as a bug."
            )

        # Use the highest priority parser.
        return parsers[-1]

    # XXX: This is patched in the tests.
    def _mark_as_modified(self, fname: str, parser: RawConfigParser) -> None:
        file_parser_tuple = (fname, parser)
        if file_parser_tuple not in self._modified_parsers:
            self._modified_parsers.append(file_parser_tuple)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._dictionary!r})"

# === NexusCore/openenv\Lib\site-packages\pydantic\dataclasses.py ===
"""Provide an enhanced dataclass that performs validation."""

from __future__ import annotations as _annotations

import dataclasses
import sys
import types
from typing import TYPE_CHECKING, Any, Callable, Generic, Literal, NoReturn, TypeVar, overload
from warnings import warn

from typing_extensions import TypeGuard, dataclass_transform

from ._internal import _config, _decorators, _namespace_utils, _typing_extra
from ._internal import _dataclasses as _pydantic_dataclasses
from ._migration import getattr_migration
from .config import ConfigDict
from .errors import PydanticUserError
from .fields import Field, FieldInfo, PrivateAttr

if TYPE_CHECKING:
    from ._internal._dataclasses import PydanticDataclass
    from ._internal._namespace_utils import MappingNamespace

__all__ = 'dataclass', 'rebuild_dataclass'

_T = TypeVar('_T')

if sys.version_info >= (3, 10):

    @dataclass_transform(field_specifiers=(dataclasses.field, Field, PrivateAttr))
    @overload
    def dataclass(
        *,
        init: Literal[False] = False,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        config: ConfigDict | type[object] | None = None,
        validate_on_init: bool | None = None,
        kw_only: bool = ...,
        slots: bool = ...,
    ) -> Callable[[type[_T]], type[PydanticDataclass]]:  # type: ignore
        ...

    @dataclass_transform(field_specifiers=(dataclasses.field, Field, PrivateAttr))
    @overload
    def dataclass(
        _cls: type[_T],  # type: ignore
        *,
        init: Literal[False] = False,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool | None = None,
        config: ConfigDict | type[object] | None = None,
        validate_on_init: bool | None = None,
        kw_only: bool = ...,
        slots: bool = ...,
    ) -> type[PydanticDataclass]: ...

else:

    @dataclass_transform(field_specifiers=(dataclasses.field, Field, PrivateAttr))
    @overload
    def dataclass(
        *,
        init: Literal[False] = False,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool | None = None,
        config: ConfigDict | type[object] | None = None,
        validate_on_init: bool | None = None,
    ) -> Callable[[type[_T]], type[PydanticDataclass]]:  # type: ignore
        ...

    @dataclass_transform(field_specifiers=(dataclasses.field, Field, PrivateAttr))
    @overload
    def dataclass(
        _cls: type[_T],  # type: ignore
        *,
        init: Literal[False] = False,
        repr: bool = True,
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool | None = None,
        config: ConfigDict | type[object] | None = None,
        validate_on_init: bool | None = None,
    ) -> type[PydanticDataclass]: ...


@dataclass_transform(field_specifiers=(dataclasses.field, Field, PrivateAttr))
def dataclass(
    _cls: type[_T] | None = None,
    *,
    init: Literal[False] = False,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool | None = None,
    config: ConfigDict | type[object] | None = None,
    validate_on_init: bool | None = None,
    kw_only: bool = False,
    slots: bool = False,
) -> Callable[[type[_T]], type[PydanticDataclass]] | type[PydanticDataclass]:
    """!!! abstract "Usage Documentation"
        [`dataclasses`](../concepts/dataclasses.md)

    A decorator used to create a Pydantic-enhanced dataclass, similar to the standard Python `dataclass`,
    but with added validation.

    This function should be used similarly to `dataclasses.dataclass`.

    Args:
        _cls: The target `dataclass`.
        init: Included for signature compatibility with `dataclasses.dataclass`, and is passed through to
            `dataclasses.dataclass` when appropriate. If specified, must be set to `False`, as pydantic inserts its
            own  `__init__` function.
        repr: A boolean indicating whether to include the field in the `__repr__` output.
        eq: Determines if a `__eq__` method should be generated for the class.
        order: Determines if comparison magic methods should be generated, such as `__lt__`, but not `__eq__`.
        unsafe_hash: Determines if a `__hash__` method should be included in the class, as in `dataclasses.dataclass`.
        frozen: Determines if the generated class should be a 'frozen' `dataclass`, which does not allow its
            attributes to be modified after it has been initialized. If not set, the value from the provided `config` argument will be used (and will default to `False` otherwise).
        config: The Pydantic config to use for the `dataclass`.
        validate_on_init: A deprecated parameter included for backwards compatibility; in V2, all Pydantic dataclasses
            are validated on init.
        kw_only: Determines if `__init__` method parameters must be specified by keyword only. Defaults to `False`.
        slots: Determines if the generated class should be a 'slots' `dataclass`, which does not allow the addition of
            new attributes after instantiation.

    Returns:
        A decorator that accepts a class as its argument and returns a Pydantic `dataclass`.

    Raises:
        AssertionError: Raised if `init` is not `False` or `validate_on_init` is `False`.
    """
    assert init is False, 'pydantic.dataclasses.dataclass only supports init=False'
    assert validate_on_init is not False, 'validate_on_init=False is no longer supported'

    if sys.version_info >= (3, 10):
        kwargs = {'kw_only': kw_only, 'slots': slots}
    else:
        kwargs = {}

    def make_pydantic_fields_compatible(cls: type[Any]) -> None:
        """Make sure that stdlib `dataclasses` understands `Field` kwargs like `kw_only`
        To do that, we simply change
          `x: int = pydantic.Field(..., kw_only=True)`
        into
          `x: int = dataclasses.field(default=pydantic.Field(..., kw_only=True), kw_only=True)`
        """
        for annotation_cls in cls.__mro__:
            annotations: dict[str, Any] = getattr(annotation_cls, '__annotations__', {})
            for field_name in annotations:
                field_value = getattr(cls, field_name, None)
                # Process only if this is an instance of `FieldInfo`.
                if not isinstance(field_value, FieldInfo):
                    continue

                # Initialize arguments for the standard `dataclasses.field`.
                field_args: dict = {'default': field_value}

                # Handle `kw_only` for Python 3.10+
                if sys.version_info >= (3, 10) and field_value.kw_only:
                    field_args['kw_only'] = True

                # Set `repr` attribute if it's explicitly specified to be not `True`.
                if field_value.repr is not True:
                    field_args['repr'] = field_value.repr

                setattr(cls, field_name, dataclasses.field(**field_args))
                # In Python 3.9, when subclassing, information is pulled from cls.__dict__['__annotations__']
                # for annotations, so we must make sure it's initialized before we add to it.
                if cls.__dict__.get('__annotations__') is None:
                    cls.__annotations__ = {}
                cls.__annotations__[field_name] = annotations[field_name]

    def create_dataclass(cls: type[Any]) -> type[PydanticDataclass]:
        """Create a Pydantic dataclass from a regular dataclass.

        Args:
            cls: The class to create the Pydantic dataclass from.

        Returns:
            A Pydantic dataclass.
        """
        from ._internal._utils import is_model_class

        if is_model_class(cls):
            raise PydanticUserError(
                f'Cannot create a Pydantic dataclass from {cls.__name__} as it is already a Pydantic model',
                code='dataclass-on-model',
            )

        original_cls = cls

        # we warn on conflicting config specifications, but only if the class doesn't have a dataclass base
        # because a dataclass base might provide a __pydantic_config__ attribute that we don't want to warn about
        has_dataclass_base = any(dataclasses.is_dataclass(base) for base in cls.__bases__)
        if not has_dataclass_base and config is not None and hasattr(cls, '__pydantic_config__'):
            warn(
                f'`config` is set via both the `dataclass` decorator and `__pydantic_config__` for dataclass {cls.__name__}. '
                f'The `config` specification from `dataclass` decorator will take priority.',
                category=UserWarning,
                stacklevel=2,
            )

        # if config is not explicitly provided, try to read it from the type
        config_dict = config if config is not None else getattr(cls, '__pydantic_config__', None)
        config_wrapper = _config.ConfigWrapper(config_dict)
        decorators = _decorators.DecoratorInfos.build(cls)

        # Keep track of the original __doc__ so that we can restore it after applying the dataclasses decorator
        # Otherwise, classes with no __doc__ will have their signature added into the JSON schema description,
        # since dataclasses.dataclass will set this as the __doc__
        original_doc = cls.__doc__

        if _pydantic_dataclasses.is_builtin_dataclass(cls):
            # Don't preserve the docstring for vanilla dataclasses, as it may include the signature
            # This matches v1 behavior, and there was an explicit test for it
            original_doc = None

            # We don't want to add validation to the existing std lib dataclass, so we will subclass it
            #   If the class is generic, we need to make sure the subclass also inherits from Generic
            #   with all the same parameters.
            bases = (cls,)
            if issubclass(cls, Generic):
                generic_base = Generic[cls.__parameters__]  # type: ignore
                bases = bases + (generic_base,)
            cls = types.new_class(cls.__name__, bases)

        make_pydantic_fields_compatible(cls)

        # Respect frozen setting from dataclass constructor and fallback to config setting if not provided
        if frozen is not None:
            frozen_ = frozen
            if config_wrapper.frozen:
                # It's not recommended to define both, as the setting from the dataclass decorator will take priority.
                warn(
                    f'`frozen` is set via both the `dataclass` decorator and `config` for dataclass {cls.__name__!r}.'
                    'This is not recommended. The `frozen` specification on `dataclass` will take priority.',
                    category=UserWarning,
                    stacklevel=2,
                )
        else:
            frozen_ = config_wrapper.frozen or False

        cls = dataclasses.dataclass(  # type: ignore[call-overload]
            cls,
            # the value of init here doesn't affect anything except that it makes it easier to generate a signature
            init=True,
            repr=repr,
            eq=eq,
            order=order,
            unsafe_hash=unsafe_hash,
            frozen=frozen_,
            **kwargs,
        )

        # This is an undocumented attribute to distinguish stdlib/Pydantic dataclasses.
        # It should be set as early as possible:
        cls.__is_pydantic_dataclass__ = True

        cls.__pydantic_decorators__ = decorators  # type: ignore
        cls.__doc__ = original_doc
        cls.__module__ = original_cls.__module__
        cls.__qualname__ = original_cls.__qualname__
        cls.__pydantic_fields_complete__ = classmethod(_pydantic_fields_complete)
        cls.__pydantic_complete__ = False  # `complete_dataclass` will set it to `True` if successful.
        # TODO `parent_namespace` is currently None, but we could do the same thing as Pydantic models:
        # fetch the parent ns using `parent_frame_namespace` (if the dataclass was defined in a function),
        # and possibly cache it (see the `__pydantic_parent_namespace__` logic for models).
        _pydantic_dataclasses.complete_dataclass(cls, config_wrapper, raise_errors=False)
        return cls

    return create_dataclass if _cls is None else create_dataclass(_cls)


def _pydantic_fields_complete(cls: type[PydanticDataclass]) -> bool:
    """Return whether the fields where successfully collected (i.e. type hints were successfully resolves).

    This is a private property, not meant to be used outside Pydantic.
    """
    return all(field_info._complete for field_info in cls.__pydantic_fields__.values())


__getattr__ = getattr_migration(__name__)

if sys.version_info < (3, 11):
    # Monkeypatch dataclasses.InitVar so that typing doesn't error if it occurs as a type when evaluating type hints
    # Starting in 3.11, typing.get_type_hints will not raise an error if the retrieved type hints are not callable.

    def _call_initvar(*args: Any, **kwargs: Any) -> NoReturn:
        """This function does nothing but raise an error that is as similar as possible to what you'd get
        if you were to try calling `InitVar[int]()` without this monkeypatch. The whole purpose is just
        to ensure typing._type_check does not error if the type hint evaluates to `InitVar[<parameter>]`.
        """
        raise TypeError("'InitVar' object is not callable")

    dataclasses.InitVar.__call__ = _call_initvar


def rebuild_dataclass(
    cls: type[PydanticDataclass],
    *,
    force: bool = False,
    raise_errors: bool = True,
    _parent_namespace_depth: int = 2,
    _types_namespace: MappingNamespace | None = None,
) -> bool | None:
    """Try to rebuild the pydantic-core schema for the dataclass.

    This may be necessary when one of the annotations is a ForwardRef which could not be resolved during
    the initial attempt to build the schema, and automatic rebuilding fails.

    This is analogous to `BaseModel.model_rebuild`.

    Args:
        cls: The class to rebuild the pydantic-core schema for.
        force: Whether to force the rebuilding of the schema, defaults to `False`.
        raise_errors: Whether to raise errors, defaults to `True`.
        _parent_namespace_depth: The depth level of the parent namespace, defaults to 2.
        _types_namespace: The types namespace, defaults to `None`.

    Returns:
        Returns `None` if the schema is already "complete" and rebuilding was not required.
        If rebuilding _was_ required, returns `True` if rebuilding was successful, otherwise `False`.
    """
    if not force and cls.__pydantic_complete__:
        return None

    for attr in ('__pydantic_core_schema__', '__pydantic_validator__', '__pydantic_serializer__'):
        if attr in cls.__dict__:
            # Deleting the validator/serializer is necessary as otherwise they can get reused in
            # pydantic-core. Same applies for the core schema that can be reused in schema generation.
            delattr(cls, attr)

    cls.__pydantic_complete__ = False

    if _types_namespace is not None:
        rebuild_ns = _types_namespace
    elif _parent_namespace_depth > 0:
        rebuild_ns = _typing_extra.parent_frame_namespace(parent_depth=_parent_namespace_depth, force=True) or {}
    else:
        rebuild_ns = {}

    ns_resolver = _namespace_utils.NsResolver(
        parent_namespace=rebuild_ns,
    )

    return _pydantic_dataclasses.complete_dataclass(
        cls,
        _config.ConfigWrapper(cls.__pydantic_config__, check=False),
        raise_errors=raise_errors,
        ns_resolver=ns_resolver,
        # We could provide a different config instead (with `'defer_build'` set to `True`)
        # of this explicit `_force_build` argument, but because config can come from the
        # decorator parameter or the `__pydantic_config__` attribute, `complete_dataclass`
        # will overwrite `__pydantic_config__` with the provided config above:
        _force_build=True,
    )


def is_pydantic_dataclass(class_: type[Any], /) -> TypeGuard[type[PydanticDataclass]]:
    """Whether a class is a pydantic dataclass.

    Args:
        class_: The class.

    Returns:
        `True` if the class is a pydantic dataclass, `False` otherwise.
    """
    try:
        return '__is_pydantic_dataclass__' in class_.__dict__ and dataclasses.is_dataclass(class_)
    except AttributeError:
        return False

# === NexusCore/openenv\Lib\site-packages\IPython\lib\__init__.py ===
# encoding: utf-8
"""
Extra capabilities for IPython
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\mcp_management_endpoints.py ===
"""
1. Allow proxy admin to perform create, update, and delete operations on MCP servers in the db.
2. Allows users to view the mcp servers they have access to.

Endpoints here:
- GET `/v1/mcp/server` - Returns all of the configured mcp servers in the db filtered by requestor's access
- GET `/v1/mcp/server/{server_id}` - Returns the the specific mcp server in the db given `server_id` filtered by requestor's access
- GET `/v1/mcp/server/{server_id}/tools` - Get all the tools from the mcp server specified by the `server_id`
- POST `/v1/mcp/server` - Add a new external mcp server.
- PUT `/v1/mcp/server` -  Edits an existing mcp server.
- DELETE `/v1/mcp/server/{server_id}` - Deletes the mcp server given `server_id`.
"""

import importlib
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.responses import JSONResponse

import litellm
from litellm._logging import verbose_logger, verbose_proxy_logger
from litellm.constants import LITELLM_PROXY_ADMIN_NAME

router = APIRouter(prefix="/v1/mcp", tags=["mcp"])
MCP_AVAILABLE: bool = True
try:
    importlib.import_module("mcp")
except ImportError as e:
    verbose_logger.debug(f"MCP module not found: {e}")
    MCP_AVAILABLE = False

if MCP_AVAILABLE:
    from litellm.proxy._experimental.mcp_server.db import (
        create_mcp_server,
        delete_mcp_server,
        get_all_mcp_servers,
        get_all_mcp_servers_for_user,
        get_mcp_server,
        update_mcp_server,
    )
    from litellm.proxy._experimental.mcp_server.mcp_server_manager import (
        global_mcp_server_manager,
    )
    from litellm.proxy._types import (
        LiteLLM_MCPServerTable,
        LitellmUserRoles,
        NewMCPServerRequest,
        SpecialMCPServerName,
        UpdateMCPServerRequest,
        UserAPIKeyAuth,
    )
    from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
    from litellm.proxy.management_endpoints.common_utils import _user_has_admin_view
    from litellm.proxy.management_helpers.utils import management_endpoint_wrapper

    def get_prisma_client_or_throw(message: str):
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": message},
            )
        return prisma_client

    def does_mcp_server_exist(
        mcp_server_records: Iterable[LiteLLM_MCPServerTable], mcp_server_id: str
    ) -> bool:
        """
        Check if the mcp server with the given id exists in the iterable of mcp servers
        """
        for mcp_server_record in mcp_server_records:
            if mcp_server_record.server_id == mcp_server_id:
                return True
        return False

    ## FastAPI Routes
    @router.get(
        "/server",
        description="Returns the mcp server list",
        dependencies=[Depends(user_api_key_auth)],
        response_model=List[LiteLLM_MCPServerTable],
    )
    async def fetch_all_mcp_servers(
        user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    ):
        """
        Get all of the configured mcp servers for the user in the db
        ```
        curl --location 'http://localhost:4000/v1/mcp/server' \
        --header 'Authorization: Bearer your_api_key_here'
        ```
        """
        from datetime import datetime

        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy"
        )

        LIST_MCP_SERVERS: List[LiteLLM_MCPServerTable] = []

        # perform authz check to filter the mcp servers user has access to
        if _user_has_admin_view(user_api_key_dict):
            LIST_MCP_SERVERS = await get_all_mcp_servers(prisma_client)
        else:
            # Find all mcp servers the user has access to
            LIST_MCP_SERVERS = await get_all_mcp_servers_for_user(
                prisma_client, user_api_key_dict
            )

        #########################################################
        # Allowed MCP Servers from config.yaml
        #########################################################
        ALLOWED_MCP_SERVER_IDS = (
            await global_mcp_server_manager.get_allowed_mcp_servers(
                user_api_key_auth=user_api_key_dict
            )
        )
        ALL_CONFIG_MCP_SERVERS = global_mcp_server_manager.config_mcp_servers
        for _server_id, _server_config in ALL_CONFIG_MCP_SERVERS.items():
            if _server_id in ALLOWED_MCP_SERVER_IDS:
                LIST_MCP_SERVERS.append(
                    LiteLLM_MCPServerTable(
                        server_id=_server_id,
                        alias=_server_config.name,
                        url=_server_config.url,
                        transport=_server_config.transport,
                        spec_version=_server_config.spec_version,
                        auth_type=_server_config.auth_type,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                )
        #########################################################
        return LIST_MCP_SERVERS

    @router.get(
        "/server/{server_id}",
        description="Returns the mcp server info",
        dependencies=[Depends(user_api_key_auth)],
        response_model=LiteLLM_MCPServerTable,
    )
    async def fetch_mcp_server(
        server_id: str,
        user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    ):
        """
        Get the info on the mcp server specified by the `server_id`
        Parameters:
        - server_id: str - Required. The unique identifier of the mcp server to get info on.
        ```
        curl --location 'http://localhost:4000/v1/mcp/server/server_id' \
        --header 'Authorization: Bearer your_api_key_here'
        ```
        """
        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy"
        )

        # check to see if server exists for all users
        mcp_server = await get_mcp_server(prisma_client, server_id)
        if mcp_server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"MCP Server with id {server_id} not found"},
            )

        # Implement authz restriction from requested user
        if _user_has_admin_view(user_api_key_dict):
            return mcp_server

        # Perform authz check to filter the mcp servers user has access to
        mcp_server_records = await get_all_mcp_servers_for_user(
            prisma_client, user_api_key_dict
        )
        exists = does_mcp_server_exist(mcp_server_records, server_id)

        if exists:
            global_mcp_server_manager.add_update_server(mcp_server)
            return mcp_server
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": f"User does not have permission to view mcp server with id {server_id}. You can only view mcp servers that you have access to."
                },
            )

    @router.post(
        "/server",
        description="Allows creation of mcp servers",
        dependencies=[Depends(user_api_key_auth)],
        response_model=LiteLLM_MCPServerTable,
        status_code=status.HTTP_201_CREATED,
    )
    @management_endpoint_wrapper
    async def add_mcp_server(
        payload: NewMCPServerRequest,
        user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
        litellm_changed_by: Optional[str] = Header(
            None,
            description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
        ),
    ):
        """
        Allow users to add a new external mcp server.
        """
        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy"
        )

        # AuthZ - restrict only proxy admins to create mcp servers
        if LitellmUserRoles.PROXY_ADMIN != user_api_key_dict.user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "User does not have permission to create mcp servers. You can only create mcp servers if you are a PROXY_ADMIN."
                },
            )
        elif payload.server_id is not None:
            # fail if the mcp server with id already exists
            mcp_server = await get_mcp_server(prisma_client, payload.server_id)
            if mcp_server is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": f"MCP Server with id {payload.server_id} already exists. Cannot create another."
                    },
                )
        elif (
            SpecialMCPServerName.all_team_servers == payload.server_id
            or SpecialMCPServerName.all_proxy_servers == payload.server_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": f"MCP Server with id {payload.server_id} is special and cannot be used."
                },
            )

        # TODO: audit log for create

        # Attempt to create the mcp server
        try:
            new_mcp_server = await create_mcp_server(
                prisma_client,
                payload,
                touched_by=user_api_key_dict.user_id or LITELLM_PROXY_ADMIN_NAME,
            )
            global_mcp_server_manager.add_update_server(new_mcp_server)
        except Exception as e:
            verbose_proxy_logger.exception(f"Error creating mcp server: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": f"Error creating mcp server: {str(e)}"},
            )
        return new_mcp_server

    @router.delete(
        "/server/{server_id}",
        description="Allows deleting mcp serves in the db",
        dependencies=[Depends(user_api_key_auth)],
        response_class=JSONResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    @management_endpoint_wrapper
    async def remove_mcp_server(
        server_id: str,
        user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
        litellm_changed_by: Optional[str] = Header(
            None,
            description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
        ),
    ):
        """
        Delete MCP Server from db and associated MCP related server entities.

        Parameters:
        - server_id: str - Required. The unique identifier of the mcp server to delete.
        ```
        curl -X "DELETE" --location 'http://localhost:4000/v1/mcp/server/server_id' \
        --header 'Authorization: Bearer your_api_key_here'
        ```
        """
        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
        )

        # Authz - restrict only admins to delete mcp servers
        if LitellmUserRoles.PROXY_ADMIN != user_api_key_dict.user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Call not allowed to delete MCP server. User is not a proxy admin. route={}".format(
                        "DELETE /v1/mcp/server"
                    )
                },
            )

        # try to delete the mcp server
        mcp_server_record_deleted = await delete_mcp_server(prisma_client, server_id)

        if mcp_server_record_deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"MCP Server not found, passed server_id={server_id}"},
            )
        global_mcp_server_manager.remove_server(mcp_server_record_deleted)

        # TODO: Enterprise: Finish audit log trail
        if litellm.store_audit_logs:
            pass

        # TODO: Delete from virtual keys

        # TODO: Delete from teams

        # Update from global mcp store

        return Response(status_code=status.HTTP_202_ACCEPTED)

    @router.put(
        "/server",
        description="Allows deleting mcp serves in the db",
        dependencies=[Depends(user_api_key_auth)],
        response_model=LiteLLM_MCPServerTable,
        status_code=status.HTTP_202_ACCEPTED,
    )
    @management_endpoint_wrapper
    async def edit_mcp_server(
        payload: UpdateMCPServerRequest,
        user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
        litellm_changed_by: Optional[str] = Header(
            None,
            description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
        ),
    ):
        """
        Updates the MCP Server in the db.

        Parameters:
        - payload: UpdateMCPServerRequest - Required. The updated mcp server data.
        ```
        curl -X "PUT" --location 'http://localhost:4000/v1/mcp/server' \
        --header 'Authorization: Bearer your_api_key_here'
        ```
        """
        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
        )

        # Authz - restrict only admins to delete mcp servers
        if LitellmUserRoles.PROXY_ADMIN != user_api_key_dict.user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Call not allowed to update MCP server. User is not a proxy admin. route={}".format(
                        "PUT /v1/mcp/server"
                    )
                },
            )

        # try to update the mcp server
        mcp_server_record_updated = await update_mcp_server(
            prisma_client,
            payload,
            touched_by=user_api_key_dict.user_id or LITELLM_PROXY_ADMIN_NAME,
        )

        if mcp_server_record_updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": f"MCP Server not found, passed server_id={payload.server_id}"
                },
            )
        global_mcp_server_manager.add_update_server(mcp_server_record_updated)

        # TODO: Enterprise: Finish audit log trail
        if litellm.store_audit_logs:
            pass

        return mcp_server_record_updated

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\team_callback_endpoints.py ===
"""
Endpoints to control callbacks per team

Use this when each team should control its own callbacks
"""

import json
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    AddTeamCallback,
    ProxyErrorTypes,
    ProxyException,
    TeamCallbackMetadata,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.management_helpers.utils import management_endpoint_wrapper

router = APIRouter()


@router.post(
    "/team/{team_id:path}/callback",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def add_team_callbacks(
    data: AddTeamCallback,
    http_request: Request,
    team_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    Add a success/failure callback to a team

    Use this if if you want different teams to have different success/failure callbacks

    Parameters:
    - callback_name (Literal["langfuse", "langsmith", "gcs"], required): The name of the callback to add
    - callback_type (Literal["success", "failure", "success_and_failure"], required): The type of callback to add. One of:
        - "success": Callback for successful LLM calls
        - "failure": Callback for failed LLM calls
        - "success_and_failure": Callback for both successful and failed LLM calls
    - callback_vars (StandardCallbackDynamicParams, required): A dictionary of variables to pass to the callback
        - langfuse_public_key: The public key for the Langfuse callback
        - langfuse_secret_key: The secret key for the Langfuse callback
        - langfuse_secret: The secret for the Langfuse callback
        - langfuse_host: The host for the Langfuse callback
        - gcs_bucket_name: The name of the GCS bucket
        - gcs_path_service_account: The path to the GCS service account
        - langsmith_api_key: The API key for the Langsmith callback
        - langsmith_project: The project for the Langsmith callback
        - langsmith_base_url: The base URL for the Langsmith callback

    Example curl:
    ```
    curl -X POST 'http:/localhost:4000/team/dbe2f686-a686-4896-864a-4c3924458709/callback' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer sk-1234' \
        -d '{
        "callback_name": "langfuse",
        "callback_type": "success",
        "callback_vars": {"langfuse_public_key": "pk-lf-xxxx1", "langfuse_secret_key": "sk-xxxxx"}
        
    }'
    ```

    This means for the team where team_id = dbe2f686-a686-4896-864a-4c3924458709, all LLM calls will be logged to langfuse using the public key pk-lf-xxxx1 and the secret key sk-xxxxx

    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})

        # Check if team_id exists already
        _existing_team = await prisma_client.get_data(
            team_id=team_id, table_name="team", query_type="find_unique"
        )
        if _existing_team is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Team id = {team_id} does not exist. Please use a different team id."
                },
            )

        # store team callback settings in metadata
        team_metadata = _existing_team.metadata
        team_callback_settings = team_metadata.get("callback_settings", {})
        # expect callback settings to be
        team_callback_settings_obj = TeamCallbackMetadata(**team_callback_settings)
        if data.callback_type == "success":
            if team_callback_settings_obj.success_callback is None:
                team_callback_settings_obj.success_callback = []

            if data.callback_name in team_callback_settings_obj.success_callback:
                raise ProxyException(
                    message=f"callback_name = {data.callback_name} already exists in failure_callback, for team_id = {team_id}. \n Existing failure_callback = {team_callback_settings_obj.success_callback}",
                    code=status.HTTP_400_BAD_REQUEST,
                    type=ProxyErrorTypes.bad_request_error,
                    param="callback_name",
                )

            team_callback_settings_obj.success_callback.append(data.callback_name)
        elif data.callback_type == "failure":
            if team_callback_settings_obj.failure_callback is None:
                team_callback_settings_obj.failure_callback = []

            if data.callback_name in team_callback_settings_obj.failure_callback:
                raise ProxyException(
                    message=f"callback_name = {data.callback_name} already exists in failure_callback, for team_id = {team_id}. \n Existing failure_callback = {team_callback_settings_obj.failure_callback}",
                    code=status.HTTP_400_BAD_REQUEST,
                    type=ProxyErrorTypes.bad_request_error,
                    param="callback_name",
                )
            team_callback_settings_obj.failure_callback.append(data.callback_name)
        elif data.callback_type == "success_and_failure":
            if team_callback_settings_obj.success_callback is None:
                team_callback_settings_obj.success_callback = []
            if team_callback_settings_obj.failure_callback is None:
                team_callback_settings_obj.failure_callback = []
            if data.callback_name in team_callback_settings_obj.success_callback:
                raise ProxyException(
                    message=f"callback_name = {data.callback_name} already exists in success_callback, for team_id = {team_id}. \n Existing success_callback = {team_callback_settings_obj.success_callback}",
                    code=status.HTTP_400_BAD_REQUEST,
                    type=ProxyErrorTypes.bad_request_error,
                    param="callback_name",
                )

            if data.callback_name in team_callback_settings_obj.failure_callback:
                raise ProxyException(
                    message=f"callback_name = {data.callback_name} already exists in failure_callback, for team_id = {team_id}. \n Existing failure_callback = {team_callback_settings_obj.failure_callback}",
                    code=status.HTTP_400_BAD_REQUEST,
                    type=ProxyErrorTypes.bad_request_error,
                    param="callback_name",
                )

            team_callback_settings_obj.success_callback.append(data.callback_name)
            team_callback_settings_obj.failure_callback.append(data.callback_name)
        for var, value in data.callback_vars.items():
            if team_callback_settings_obj.callback_vars is None:
                team_callback_settings_obj.callback_vars = {}
            team_callback_settings_obj.callback_vars[var] = value

        team_callback_settings_obj_dict = team_callback_settings_obj.model_dump()

        team_metadata["callback_settings"] = team_callback_settings_obj_dict
        team_metadata_json = json.dumps(team_metadata)  # update team_metadata

        new_team_row = await prisma_client.db.litellm_teamtable.update(
            where={"team_id": team_id}, data={"metadata": team_metadata_json}  # type: ignore
        )

        return {
            "status": "success",
            "data": new_team_row,
        }

    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.add_team_callbacks(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type=ProxyErrorTypes.internal_server_error.value,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type=ProxyErrorTypes.internal_server_error.value,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post(
    "/team/{team_id}/disable_logging",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def disable_team_logging(
    http_request: Request,
    team_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Disable all logging callbacks for a team

    Parameters:
    - team_id (str, required): The unique identifier for the team

    Example curl:
    ```
    curl -X POST 'http://localhost:4000/team/dbe2f686-a686-4896-864a-4c3924458709/disable_logging' \
        -H 'Authorization: Bearer sk-1234'
    ```


    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})

        # Check if team exists
        _existing_team = await prisma_client.get_data(
            team_id=team_id, table_name="team", query_type="find_unique"
        )
        if _existing_team is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Team id = {team_id} does not exist."},
            )

        # Update team metadata to disable logging
        team_metadata = _existing_team.metadata
        team_callback_settings = team_metadata.get("callback_settings", {})
        team_callback_settings_obj = TeamCallbackMetadata(**team_callback_settings)

        # Reset callbacks
        team_callback_settings_obj.success_callback = []
        team_callback_settings_obj.failure_callback = []

        # Update metadata
        team_metadata["callback_settings"] = team_callback_settings_obj.model_dump()
        team_metadata_json = json.dumps(team_metadata)

        # Update team in database
        updated_team = await prisma_client.db.litellm_teamtable.update(
            where={"team_id": team_id}, data={"metadata": team_metadata_json}  # type: ignore
        )

        if updated_team is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Team id = {team_id} does not exist. Error updating team logging"
                },
            )

        return {
            "status": "success",
            "message": f"Logging disabled for team {team_id}",
            "data": {
                "team_id": updated_team.team_id,
                "success_callbacks": [],
                "failure_callbacks": [],
            },
        }

    except Exception as e:
        verbose_proxy_logger.error(
            f"litellm.proxy.proxy_server.disable_team_logging(): Exception occurred - {str(e)}"
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type=ProxyErrorTypes.internal_server_error.value,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type=ProxyErrorTypes.internal_server_error.value,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/team/{team_id:path}/callback",
    tags=["team management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def get_team_callbacks(
    http_request: Request,
    team_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get the success/failure callbacks and variables for a team

    Parameters:
    - team_id (str, required): The unique identifier for the team

    Example curl:
    ```
    curl -X GET 'http://localhost:4000/team/dbe2f686-a686-4896-864a-4c3924458709/callback' \
        -H 'Authorization: Bearer sk-1234'
    ```

    This will return the callback settings for the team with id dbe2f686-a686-4896-864a-4c3924458709

    Returns {
            "status": "success",
            "data": {
                "team_id": team_id,
                "success_callbacks": team_callback_settings_obj.success_callback,
                "failure_callbacks": team_callback_settings_obj.failure_callback,
                "callback_vars": team_callback_settings_obj.callback_vars,
            },
        }
    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})

        # Check if team_id exists
        _existing_team = await prisma_client.get_data(
            team_id=team_id, table_name="team", query_type="find_unique"
        )
        if _existing_team is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Team id = {team_id} does not exist."},
            )

        # Retrieve team callback settings from metadata
        team_metadata = _existing_team.metadata
        team_callback_settings = team_metadata.get("callback_settings", {})

        # Convert to TeamCallbackMetadata object for consistent structure
        team_callback_settings_obj = TeamCallbackMetadata(**team_callback_settings)

        return {
            "status": "success",
            "data": {
                "team_id": team_id,
                "success_callbacks": team_callback_settings_obj.success_callback,
                "failure_callbacks": team_callback_settings_obj.failure_callback,
                "callback_vars": team_callback_settings_obj.callback_vars,
            },
        }

    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.get_team_callbacks(): Exception occurred - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type=ProxyErrorTypes.internal_server_error.value,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type=ProxyErrorTypes.internal_server_error.value,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\inference\mace.py ===
# Natural Language Toolkit: Interface to the Mace4 Model Builder
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A model builder that makes use of the external 'Mace4' package.
"""

import os
import tempfile

from nltk.inference.api import BaseModelBuilderCommand, ModelBuilder
from nltk.inference.prover9 import Prover9CommandParent, Prover9Parent
from nltk.sem import Expression, Valuation
from nltk.sem.logic import is_indvar


class MaceCommand(Prover9CommandParent, BaseModelBuilderCommand):
    """
    A ``MaceCommand`` specific to the ``Mace`` model builder.  It contains
    a print_assumptions() method that is used to print the list
    of assumptions in multiple formats.
    """

    _interpformat_bin = None

    def __init__(self, goal=None, assumptions=None, max_models=500, model_builder=None):
        """
        :param goal: Input expression to prove
        :type goal: sem.Expression
        :param assumptions: Input expressions to use as assumptions in
            the proof.
        :type assumptions: list(sem.Expression)
        :param max_models: The maximum number of models that Mace will try before
            simply returning false. (Use 0 for no maximum.)
        :type max_models: int
        """
        if model_builder is not None:
            assert isinstance(model_builder, Mace)
        else:
            model_builder = Mace(max_models)

        BaseModelBuilderCommand.__init__(self, model_builder, goal, assumptions)

    @property
    def valuation(mbc):
        return mbc.model("valuation")

    def _convert2val(self, valuation_str):
        """
        Transform the output file into an NLTK-style Valuation.

        :return: A model if one is generated; None otherwise.
        :rtype: sem.Valuation
        """
        valuation_standard_format = self._transform_output(valuation_str, "standard")

        val = []
        for line in valuation_standard_format.splitlines(False):
            l = line.strip()

            if l.startswith("interpretation"):
                # find the number of entities in the model
                num_entities = int(l[l.index("(") + 1 : l.index(",")].strip())

            elif l.startswith("function") and l.find("_") == -1:
                # replace the integer identifier with a corresponding alphabetic character
                name = l[l.index("(") + 1 : l.index(",")].strip()
                if is_indvar(name):
                    name = name.upper()
                value = int(l[l.index("[") + 1 : l.index("]")].strip())
                val.append((name, MaceCommand._make_model_var(value)))

            elif l.startswith("relation"):
                l = l[l.index("(") + 1 :]
                if "(" in l:
                    # relation is not nullary
                    name = l[: l.index("(")].strip()
                    values = [
                        int(v.strip())
                        for v in l[l.index("[") + 1 : l.index("]")].split(",")
                    ]
                    val.append(
                        (name, MaceCommand._make_relation_set(num_entities, values))
                    )
                else:
                    # relation is nullary
                    name = l[: l.index(",")].strip()
                    value = int(l[l.index("[") + 1 : l.index("]")].strip())
                    val.append((name, value == 1))

        return Valuation(val)

    @staticmethod
    def _make_relation_set(num_entities, values):
        """
        Convert a Mace4-style relation table into a dictionary.

        :param num_entities: the number of entities in the model; determines the row length in the table.
        :type num_entities: int
        :param values: a list of 1's and 0's that represent whether a relation holds in a Mace4 model.
        :type values: list of int
        """
        r = set()
        for position in [pos for (pos, v) in enumerate(values) if v == 1]:
            r.add(
                tuple(MaceCommand._make_relation_tuple(position, values, num_entities))
            )
        return r

    @staticmethod
    def _make_relation_tuple(position, values, num_entities):
        if len(values) == 1:
            return []
        else:
            sublist_size = len(values) // num_entities
            sublist_start = position // sublist_size
            sublist_position = int(position % sublist_size)

            sublist = values[
                sublist_start * sublist_size : (sublist_start + 1) * sublist_size
            ]
            return [
                MaceCommand._make_model_var(sublist_start)
            ] + MaceCommand._make_relation_tuple(
                sublist_position, sublist, num_entities
            )

    @staticmethod
    def _make_model_var(value):
        """
        Pick an alphabetic character as identifier for an entity in the model.

        :param value: where to index into the list of characters
        :type value: int
        """
        letter = [
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
        ][value]
        num = value // 26
        return letter + str(num) if num > 0 else letter

    def _decorate_model(self, valuation_str, format):
        """
        Print out a Mace4 model using any Mace4 ``interpformat`` format.
        See https://www.cs.unm.edu/~mccune/mace4/manual/ for details.

        :param valuation_str: str with the model builder's output
        :param format: str indicating the format for displaying
        models. Defaults to 'standard' format.
        :return: str
        """
        if not format:
            return valuation_str
        elif format == "valuation":
            return self._convert2val(valuation_str)
        else:
            return self._transform_output(valuation_str, format)

    def _transform_output(self, valuation_str, format):
        """
        Transform the output file into any Mace4 ``interpformat`` format.

        :param format: Output format for displaying models.
        :type format: str
        """
        if format in [
            "standard",
            "standard2",
            "portable",
            "tabular",
            "raw",
            "cooked",
            "xml",
            "tex",
        ]:
            return self._call_interpformat(valuation_str, [format])[0]
        else:
            raise LookupError("The specified format does not exist")

    def _call_interpformat(self, input_str, args=[], verbose=False):
        """
        Call the ``interpformat`` binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param args: A list of command-line arguments.
        :return: A tuple (stdout, returncode)
        :see: ``config_prover9``
        """
        if self._interpformat_bin is None:
            self._interpformat_bin = self._modelbuilder._find_binary(
                "interpformat", verbose
            )

        return self._modelbuilder._call(
            input_str, self._interpformat_bin, args, verbose
        )


class Mace(Prover9Parent, ModelBuilder):
    _mace4_bin = None

    def __init__(self, end_size=500):
        self._end_size = end_size
        """The maximum model size that Mace will try before
           simply returning false. (Use -1 for no maximum.)"""

    def _build_model(self, goal=None, assumptions=None, verbose=False):
        """
        Use Mace4 to build a first order model.

        :return: ``True`` if a model was found (i.e. Mace returns value of 0),
        else ``False``
        """
        if not assumptions:
            assumptions = []

        stdout, returncode = self._call_mace4(
            self.prover9_input(goal, assumptions), verbose=verbose
        )
        return (returncode == 0, stdout)

    def _call_mace4(self, input_str, args=[], verbose=False):
        """
        Call the ``mace4`` binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param args: A list of command-line arguments.
        :return: A tuple (stdout, returncode)
        :see: ``config_prover9``
        """
        if self._mace4_bin is None:
            self._mace4_bin = self._find_binary("mace4", verbose)

        updated_input_str = ""
        if self._end_size > 0:
            updated_input_str += "assign(end_size, %d).\n\n" % self._end_size
        updated_input_str += input_str

        return self._call(updated_input_str, self._mace4_bin, args, verbose)


def spacer(num=30):
    print("-" * num)


def decode_result(found):
    """
    Decode the result of model_found()

    :param found: The output of model_found()
    :type found: bool
    """
    return {True: "Countermodel found", False: "No countermodel found", None: "None"}[
        found
    ]


def test_model_found(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for goal, assumptions in arguments:
        g = Expression.fromstring(goal)
        alist = [lp.parse(a) for a in assumptions]
        m = MaceCommand(g, assumptions=alist, max_models=50)
        found = m.build_model()
        for a in alist:
            print("   %s" % a)
        print(f"|- {g}: {decode_result(found)}\n")


def test_build_model(arguments):
    """
    Try to build a ``nltk.sem.Valuation``.
    """
    g = Expression.fromstring("all x.man(x)")
    alist = [
        Expression.fromstring(a)
        for a in [
            "man(John)",
            "man(Socrates)",
            "man(Bill)",
            "some x.(-(x = John) & man(x) & sees(John,x))",
            "some x.(-(x = Bill) & man(x))",
            "all x.some y.(man(x) -> gives(Socrates,x,y))",
        ]
    ]

    m = MaceCommand(g, assumptions=alist)
    m.build_model()
    spacer()
    print("Assumptions and Goal")
    spacer()
    for a in alist:
        print("   %s" % a)
    print(f"|- {g}: {decode_result(m.build_model())}\n")
    spacer()
    # print(m.model('standard'))
    # print(m.model('cooked'))
    print("Valuation")
    spacer()
    print(m.valuation, "\n")


def test_transform_output(argument_pair):
    """
    Transform the model into various Mace4 ``interpformat`` formats.
    """
    g = Expression.fromstring(argument_pair[0])
    alist = [lp.parse(a) for a in argument_pair[1]]
    m = MaceCommand(g, assumptions=alist)
    m.build_model()
    for a in alist:
        print("   %s" % a)
    print(f"|- {g}: {m.build_model()}\n")
    for format in ["standard", "portable", "xml", "cooked"]:
        spacer()
        print("Using '%s' format" % format)
        spacer()
        print(m.model(format=format))


def test_make_relation_set():
    print(
        MaceCommand._make_relation_set(num_entities=3, values=[1, 0, 1])
        == {("c",), ("a",)}
    )
    print(
        MaceCommand._make_relation_set(
            num_entities=3, values=[0, 0, 0, 0, 0, 0, 1, 0, 0]
        )
        == {("c", "a")}
    )
    print(
        MaceCommand._make_relation_set(num_entities=2, values=[0, 0, 1, 0, 0, 0, 1, 0])
        == {("a", "b", "a"), ("b", "b", "a")}
    )


arguments = [
    ("mortal(Socrates)", ["all x.(man(x) -> mortal(x))", "man(Socrates)"]),
    ("(not mortal(Socrates))", ["all x.(man(x) -> mortal(x))", "man(Socrates)"]),
]


def demo():
    test_model_found(arguments)
    test_build_model(arguments)
    test_transform_output(arguments[1])


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\configuration.py ===
"""Configuration management setup

Some terminology:
- name
  As written in config files.
- value
  Value associated with a name
- key
  Name combined with it's section (section.name)
- variant
  A single word describing where the configuration key-value pair came from
"""

import configparser
import locale
import os
import sys
from typing import Any, Dict, Iterable, List, NewType, Optional, Tuple

from pip._internal.exceptions import (
    ConfigurationError,
    ConfigurationFileCouldNotBeLoaded,
)
from pip._internal.utils import appdirs
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import ensure_dir, enum

RawConfigParser = configparser.RawConfigParser  # Shorthand
Kind = NewType("Kind", str)

CONFIG_BASENAME = "pip.ini" if WINDOWS else "pip.conf"
ENV_NAMES_IGNORED = "version", "help"

# The kinds of configurations there are.
kinds = enum(
    USER="user",  # User Specific
    GLOBAL="global",  # System Wide
    SITE="site",  # [Virtual] Environment Specific
    ENV="env",  # from PIP_CONFIG_FILE
    ENV_VAR="env-var",  # from Environment Variables
)
OVERRIDE_ORDER = kinds.GLOBAL, kinds.USER, kinds.SITE, kinds.ENV, kinds.ENV_VAR
VALID_LOAD_ONLY = kinds.USER, kinds.GLOBAL, kinds.SITE

logger = getLogger(__name__)


# NOTE: Maybe use the optionx attribute to normalize keynames.
def _normalize_name(name: str) -> str:
    """Make a name consistent regardless of source (environment or file)"""
    name = name.lower().replace("_", "-")
    if name.startswith("--"):
        name = name[2:]  # only prefer long opts
    return name


def _disassemble_key(name: str) -> List[str]:
    if "." not in name:
        error_message = (
            "Key does not contain dot separated section and key. "
            f"Perhaps you wanted to use 'global.{name}' instead?"
        )
        raise ConfigurationError(error_message)
    return name.split(".", 1)


def get_configuration_files() -> Dict[Kind, List[str]]:
    global_config_files = [
        os.path.join(path, CONFIG_BASENAME) for path in appdirs.site_config_dirs("pip")
    ]

    site_config_file = os.path.join(sys.prefix, CONFIG_BASENAME)
    legacy_config_file = os.path.join(
        os.path.expanduser("~"),
        "pip" if WINDOWS else ".pip",
        CONFIG_BASENAME,
    )
    new_config_file = os.path.join(appdirs.user_config_dir("pip"), CONFIG_BASENAME)
    return {
        kinds.GLOBAL: global_config_files,
        kinds.SITE: [site_config_file],
        kinds.USER: [legacy_config_file, new_config_file],
    }


class Configuration:
    """Handles management of configuration.

    Provides an interface to accessing and managing configuration files.

    This class converts provides an API that takes "section.key-name" style
    keys and stores the value associated with it as "key-name" under the
    section "section".

    This allows for a clean interface wherein the both the section and the
    key-name are preserved in an easy to manage form in the configuration files
    and the data stored is also nice.
    """

    def __init__(self, isolated: bool, load_only: Optional[Kind] = None) -> None:
        super().__init__()

        if load_only is not None and load_only not in VALID_LOAD_ONLY:
            raise ConfigurationError(
                "Got invalid value for load_only - should be one of {}".format(
                    ", ".join(map(repr, VALID_LOAD_ONLY))
                )
            )
        self.isolated = isolated
        self.load_only = load_only

        # Because we keep track of where we got the data from
        self._parsers: Dict[Kind, List[Tuple[str, RawConfigParser]]] = {
            variant: [] for variant in OVERRIDE_ORDER
        }
        self._config: Dict[Kind, Dict[str, Any]] = {
            variant: {} for variant in OVERRIDE_ORDER
        }
        self._modified_parsers: List[Tuple[str, RawConfigParser]] = []

    def load(self) -> None:
        """Loads configuration from configuration files and environment"""
        self._load_config_files()
        if not self.isolated:
            self._load_environment_vars()

    def get_file_to_edit(self) -> Optional[str]:
        """Returns the file with highest priority in configuration"""
        assert self.load_only is not None, "Need to be specified a file to be editing"

        try:
            return self._get_parser_to_modify()[0]
        except IndexError:
            return None

    def items(self) -> Iterable[Tuple[str, Any]]:
        """Returns key-value pairs like dict.items() representing the loaded
        configuration
        """
        return self._dictionary.items()

    def get_value(self, key: str) -> Any:
        """Get a value from the configuration."""
        orig_key = key
        key = _normalize_name(key)
        try:
            return self._dictionary[key]
        except KeyError:
            # disassembling triggers a more useful error message than simply
            # "No such key" in the case that the key isn't in the form command.option
            _disassemble_key(key)
            raise ConfigurationError(f"No such key - {orig_key}")

    def set_value(self, key: str, value: Any) -> None:
        """Modify a value in the configuration."""
        key = _normalize_name(key)
        self._ensure_have_load_only()

        assert self.load_only
        fname, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)

            # Modify the parser and the configuration
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, name, value)

        self._config[self.load_only][key] = value
        self._mark_as_modified(fname, parser)

    def unset_value(self, key: str) -> None:
        """Unset a value in the configuration."""
        orig_key = key
        key = _normalize_name(key)
        self._ensure_have_load_only()

        assert self.load_only
        if key not in self._config[self.load_only]:
            raise ConfigurationError(f"No such key - {orig_key}")

        fname, parser = self._get_parser_to_modify()

        if parser is not None:
            section, name = _disassemble_key(key)
            if not (
                parser.has_section(section) and parser.remove_option(section, name)
            ):
                # The option was not removed.
                raise ConfigurationError(
                    "Fatal Internal error [id=1]. Please report as a bug."
                )

            # The section may be empty after the option was removed.
            if not parser.items(section):
                parser.remove_section(section)
            self._mark_as_modified(fname, parser)

        del self._config[self.load_only][key]

    def save(self) -> None:
        """Save the current in-memory state."""
        self._ensure_have_load_only()

        for fname, parser in self._modified_parsers:
            logger.info("Writing to %s", fname)

            # Ensure directory exists.
            ensure_dir(os.path.dirname(fname))

            # Ensure directory's permission(need to be writeable)
            try:
                with open(fname, "w") as f:
                    parser.write(f)
            except OSError as error:
                raise ConfigurationError(
                    f"An error occurred while writing to the configuration file "
                    f"{fname}: {error}"
                )

    #
    # Private routines
    #

    def _ensure_have_load_only(self) -> None:
        if self.load_only is None:
            raise ConfigurationError("Needed a specific file to be modifying.")
        logger.debug("Will be working with %s variant only", self.load_only)

    @property
    def _dictionary(self) -> Dict[str, Any]:
        """A dictionary representing the loaded configuration."""
        # NOTE: Dictionaries are not populated if not loaded. So, conditionals
        #       are not needed here.
        retval = {}

        for variant in OVERRIDE_ORDER:
            retval.update(self._config[variant])

        return retval

    def _load_config_files(self) -> None:
        """Loads configuration from configuration files"""
        config_files = dict(self.iter_config_files())
        if config_files[kinds.ENV][0:1] == [os.devnull]:
            logger.debug(
                "Skipping loading configuration files due to "
                "environment's PIP_CONFIG_FILE being os.devnull"
            )
            return

        for variant, files in config_files.items():
            for fname in files:
                # If there's specific variant set in `load_only`, load only
                # that variant, not the others.
                if self.load_only is not None and variant != self.load_only:
                    logger.debug("Skipping file '%s' (variant: %s)", fname, variant)
                    continue

                parser = self._load_file(variant, fname)

                # Keeping track of the parsers used
                self._parsers[variant].append((fname, parser))

    def _load_file(self, variant: Kind, fname: str) -> RawConfigParser:
        logger.verbose("For variant '%s', will try loading '%s'", variant, fname)
        parser = self._construct_parser(fname)

        for section in parser.sections():
            items = parser.items(section)
            self._config[variant].update(self._normalized_keys(section, items))

        return parser

    def _construct_parser(self, fname: str) -> RawConfigParser:
        parser = configparser.RawConfigParser()
        # If there is no such file, don't bother reading it but create the
        # parser anyway, to hold the data.
        # Doing this is useful when modifying and saving files, where we don't
        # need to construct a parser.
        if os.path.exists(fname):
            locale_encoding = locale.getpreferredencoding(False)
            try:
                parser.read(fname, encoding=locale_encoding)
            except UnicodeDecodeError:
                # See https://github.com/pypa/pip/issues/4963
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"contains invalid {locale_encoding} characters",
                    fname=fname,
                )
            except configparser.Error as error:
                # See https://github.com/pypa/pip/issues/4893
                raise ConfigurationFileCouldNotBeLoaded(error=error)
        return parser

    def _load_environment_vars(self) -> None:
        """Loads configuration from environment variables"""
        self._config[kinds.ENV_VAR].update(
            self._normalized_keys(":env:", self.get_environ_vars())
        )

    def _normalized_keys(
        self, section: str, items: Iterable[Tuple[str, Any]]
    ) -> Dict[str, Any]:
        """Normalizes items to construct a dictionary with normalized keys.

        This routine is where the names become keys and are made the same
        regardless of source - configuration files or environment.
        """
        normalized = {}
        for name, val in items:
            key = section + "." + _normalize_name(name)
            normalized[key] = val
        return normalized

    def get_environ_vars(self) -> Iterable[Tuple[str, str]]:
        """Returns a generator with all environmental vars with prefix PIP_"""
        for key, val in os.environ.items():
            if key.startswith("PIP_"):
                name = key[4:].lower()
                if name not in ENV_NAMES_IGNORED:
                    yield name, val

    # XXX: This is patched in the tests.
    def iter_config_files(self) -> Iterable[Tuple[Kind, List[str]]]:
        """Yields variant and configuration files associated with it.

        This should be treated like items of a dictionary. The order
        here doesn't affect what gets overridden. That is controlled
        by OVERRIDE_ORDER. However this does control the order they are
        displayed to the user. It's probably most ergonomic to display
        things in the same order as OVERRIDE_ORDER
        """
        # SMELL: Move the conditions out of this function

        env_config_file = os.environ.get("PIP_CONFIG_FILE", None)
        config_files = get_configuration_files()

        yield kinds.GLOBAL, config_files[kinds.GLOBAL]

        # per-user config is not loaded when env_config_file exists
        should_load_user_config = not self.isolated and not (
            env_config_file and os.path.exists(env_config_file)
        )
        if should_load_user_config:
            # The legacy config file is overridden by the new config file
            yield kinds.USER, config_files[kinds.USER]

        # virtualenv config
        yield kinds.SITE, config_files[kinds.SITE]

        if env_config_file is not None:
            yield kinds.ENV, [env_config_file]
        else:
            yield kinds.ENV, []

    def get_values_in_config(self, variant: Kind) -> Dict[str, Any]:
        """Get values present in a config file"""
        return self._config[variant]

    def _get_parser_to_modify(self) -> Tuple[str, RawConfigParser]:
        # Determine which parser to modify
        assert self.load_only
        parsers = self._parsers[self.load_only]
        if not parsers:
            # This should not happen if everything works correctly.
            raise ConfigurationError(
                "Fatal Internal error [id=2]. Please report as a bug."
            )

        # Use the highest priority parser.
        return parsers[-1]

    # XXX: This is patched in the tests.
    def _mark_as_modified(self, fname: str, parser: RawConfigParser) -> None:
        file_parser_tuple = (fname, parser)
        if file_parser_tuple not in self._modified_parsers:
            self._modified_parsers.append(file_parser_tuple)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._dictionary!r})"

# === NexusCore/openenv\Lib\site-packages\PIL\ExifTags.py ===
#
# The Python Imaging Library.
# $Id$
#
# EXIF tags
#
# Copyright (c) 2003 by Secret Labs AB
#
# See the README file for information on usage and redistribution.
#

"""
This module provides constants and clear-text names for various
well-known EXIF tags.
"""
from __future__ import annotations

from enum import IntEnum


class Base(IntEnum):
    # possibly incomplete
    InteropIndex = 0x0001
    ProcessingSoftware = 0x000B
    NewSubfileType = 0x00FE
    SubfileType = 0x00FF
    ImageWidth = 0x0100
    ImageLength = 0x0101
    BitsPerSample = 0x0102
    Compression = 0x0103
    PhotometricInterpretation = 0x0106
    Thresholding = 0x0107
    CellWidth = 0x0108
    CellLength = 0x0109
    FillOrder = 0x010A
    DocumentName = 0x010D
    ImageDescription = 0x010E
    Make = 0x010F
    Model = 0x0110
    StripOffsets = 0x0111
    Orientation = 0x0112
    SamplesPerPixel = 0x0115
    RowsPerStrip = 0x0116
    StripByteCounts = 0x0117
    MinSampleValue = 0x0118
    MaxSampleValue = 0x0119
    XResolution = 0x011A
    YResolution = 0x011B
    PlanarConfiguration = 0x011C
    PageName = 0x011D
    FreeOffsets = 0x0120
    FreeByteCounts = 0x0121
    GrayResponseUnit = 0x0122
    GrayResponseCurve = 0x0123
    T4Options = 0x0124
    T6Options = 0x0125
    ResolutionUnit = 0x0128
    PageNumber = 0x0129
    TransferFunction = 0x012D
    Software = 0x0131
    DateTime = 0x0132
    Artist = 0x013B
    HostComputer = 0x013C
    Predictor = 0x013D
    WhitePoint = 0x013E
    PrimaryChromaticities = 0x013F
    ColorMap = 0x0140
    HalftoneHints = 0x0141
    TileWidth = 0x0142
    TileLength = 0x0143
    TileOffsets = 0x0144
    TileByteCounts = 0x0145
    SubIFDs = 0x014A
    InkSet = 0x014C
    InkNames = 0x014D
    NumberOfInks = 0x014E
    DotRange = 0x0150
    TargetPrinter = 0x0151
    ExtraSamples = 0x0152
    SampleFormat = 0x0153
    SMinSampleValue = 0x0154
    SMaxSampleValue = 0x0155
    TransferRange = 0x0156
    ClipPath = 0x0157
    XClipPathUnits = 0x0158
    YClipPathUnits = 0x0159
    Indexed = 0x015A
    JPEGTables = 0x015B
    OPIProxy = 0x015F
    JPEGProc = 0x0200
    JpegIFOffset = 0x0201
    JpegIFByteCount = 0x0202
    JpegRestartInterval = 0x0203
    JpegLosslessPredictors = 0x0205
    JpegPointTransforms = 0x0206
    JpegQTables = 0x0207
    JpegDCTables = 0x0208
    JpegACTables = 0x0209
    YCbCrCoefficients = 0x0211
    YCbCrSubSampling = 0x0212
    YCbCrPositioning = 0x0213
    ReferenceBlackWhite = 0x0214
    XMLPacket = 0x02BC
    RelatedImageFileFormat = 0x1000
    RelatedImageWidth = 0x1001
    RelatedImageLength = 0x1002
    Rating = 0x4746
    RatingPercent = 0x4749
    ImageID = 0x800D
    CFARepeatPatternDim = 0x828D
    BatteryLevel = 0x828F
    Copyright = 0x8298
    ExposureTime = 0x829A
    FNumber = 0x829D
    IPTCNAA = 0x83BB
    ImageResources = 0x8649
    ExifOffset = 0x8769
    InterColorProfile = 0x8773
    ExposureProgram = 0x8822
    SpectralSensitivity = 0x8824
    GPSInfo = 0x8825
    ISOSpeedRatings = 0x8827
    OECF = 0x8828
    Interlace = 0x8829
    TimeZoneOffset = 0x882A
    SelfTimerMode = 0x882B
    SensitivityType = 0x8830
    StandardOutputSensitivity = 0x8831
    RecommendedExposureIndex = 0x8832
    ISOSpeed = 0x8833
    ISOSpeedLatitudeyyy = 0x8834
    ISOSpeedLatitudezzz = 0x8835
    ExifVersion = 0x9000
    DateTimeOriginal = 0x9003
    DateTimeDigitized = 0x9004
    OffsetTime = 0x9010
    OffsetTimeOriginal = 0x9011
    OffsetTimeDigitized = 0x9012
    ComponentsConfiguration = 0x9101
    CompressedBitsPerPixel = 0x9102
    ShutterSpeedValue = 0x9201
    ApertureValue = 0x9202
    BrightnessValue = 0x9203
    ExposureBiasValue = 0x9204
    MaxApertureValue = 0x9205
    SubjectDistance = 0x9206
    MeteringMode = 0x9207
    LightSource = 0x9208
    Flash = 0x9209
    FocalLength = 0x920A
    Noise = 0x920D
    ImageNumber = 0x9211
    SecurityClassification = 0x9212
    ImageHistory = 0x9213
    TIFFEPStandardID = 0x9216
    MakerNote = 0x927C
    UserComment = 0x9286
    SubsecTime = 0x9290
    SubsecTimeOriginal = 0x9291
    SubsecTimeDigitized = 0x9292
    AmbientTemperature = 0x9400
    Humidity = 0x9401
    Pressure = 0x9402
    WaterDepth = 0x9403
    Acceleration = 0x9404
    CameraElevationAngle = 0x9405
    XPTitle = 0x9C9B
    XPComment = 0x9C9C
    XPAuthor = 0x9C9D
    XPKeywords = 0x9C9E
    XPSubject = 0x9C9F
    FlashPixVersion = 0xA000
    ColorSpace = 0xA001
    ExifImageWidth = 0xA002
    ExifImageHeight = 0xA003
    RelatedSoundFile = 0xA004
    ExifInteroperabilityOffset = 0xA005
    FlashEnergy = 0xA20B
    SpatialFrequencyResponse = 0xA20C
    FocalPlaneXResolution = 0xA20E
    FocalPlaneYResolution = 0xA20F
    FocalPlaneResolutionUnit = 0xA210
    SubjectLocation = 0xA214
    ExposureIndex = 0xA215
    SensingMethod = 0xA217
    FileSource = 0xA300
    SceneType = 0xA301
    CFAPattern = 0xA302
    CustomRendered = 0xA401
    ExposureMode = 0xA402
    WhiteBalance = 0xA403
    DigitalZoomRatio = 0xA404
    FocalLengthIn35mmFilm = 0xA405
    SceneCaptureType = 0xA406
    GainControl = 0xA407
    Contrast = 0xA408
    Saturation = 0xA409
    Sharpness = 0xA40A
    DeviceSettingDescription = 0xA40B
    SubjectDistanceRange = 0xA40C
    ImageUniqueID = 0xA420
    CameraOwnerName = 0xA430
    BodySerialNumber = 0xA431
    LensSpecification = 0xA432
    LensMake = 0xA433
    LensModel = 0xA434
    LensSerialNumber = 0xA435
    CompositeImage = 0xA460
    CompositeImageCount = 0xA461
    CompositeImageExposureTimes = 0xA462
    Gamma = 0xA500
    PrintImageMatching = 0xC4A5
    DNGVersion = 0xC612
    DNGBackwardVersion = 0xC613
    UniqueCameraModel = 0xC614
    LocalizedCameraModel = 0xC615
    CFAPlaneColor = 0xC616
    CFALayout = 0xC617
    LinearizationTable = 0xC618
    BlackLevelRepeatDim = 0xC619
    BlackLevel = 0xC61A
    BlackLevelDeltaH = 0xC61B
    BlackLevelDeltaV = 0xC61C
    WhiteLevel = 0xC61D
    DefaultScale = 0xC61E
    DefaultCropOrigin = 0xC61F
    DefaultCropSize = 0xC620
    ColorMatrix1 = 0xC621
    ColorMatrix2 = 0xC622
    CameraCalibration1 = 0xC623
    CameraCalibration2 = 0xC624
    ReductionMatrix1 = 0xC625
    ReductionMatrix2 = 0xC626
    AnalogBalance = 0xC627
    AsShotNeutral = 0xC628
    AsShotWhiteXY = 0xC629
    BaselineExposure = 0xC62A
    BaselineNoise = 0xC62B
    BaselineSharpness = 0xC62C
    BayerGreenSplit = 0xC62D
    LinearResponseLimit = 0xC62E
    CameraSerialNumber = 0xC62F
    LensInfo = 0xC630
    ChromaBlurRadius = 0xC631
    AntiAliasStrength = 0xC632
    ShadowScale = 0xC633
    DNGPrivateData = 0xC634
    MakerNoteSafety = 0xC635
    CalibrationIlluminant1 = 0xC65A
    CalibrationIlluminant2 = 0xC65B
    BestQualityScale = 0xC65C
    RawDataUniqueID = 0xC65D
    OriginalRawFileName = 0xC68B
    OriginalRawFileData = 0xC68C
    ActiveArea = 0xC68D
    MaskedAreas = 0xC68E
    AsShotICCProfile = 0xC68F
    AsShotPreProfileMatrix = 0xC690
    CurrentICCProfile = 0xC691
    CurrentPreProfileMatrix = 0xC692
    ColorimetricReference = 0xC6BF
    CameraCalibrationSignature = 0xC6F3
    ProfileCalibrationSignature = 0xC6F4
    AsShotProfileName = 0xC6F6
    NoiseReductionApplied = 0xC6F7
    ProfileName = 0xC6F8
    ProfileHueSatMapDims = 0xC6F9
    ProfileHueSatMapData1 = 0xC6FA
    ProfileHueSatMapData2 = 0xC6FB
    ProfileToneCurve = 0xC6FC
    ProfileEmbedPolicy = 0xC6FD
    ProfileCopyright = 0xC6FE
    ForwardMatrix1 = 0xC714
    ForwardMatrix2 = 0xC715
    PreviewApplicationName = 0xC716
    PreviewApplicationVersion = 0xC717
    PreviewSettingsName = 0xC718
    PreviewSettingsDigest = 0xC719
    PreviewColorSpace = 0xC71A
    PreviewDateTime = 0xC71B
    RawImageDigest = 0xC71C
    OriginalRawFileDigest = 0xC71D
    SubTileBlockSize = 0xC71E
    RowInterleaveFactor = 0xC71F
    ProfileLookTableDims = 0xC725
    ProfileLookTableData = 0xC726
    OpcodeList1 = 0xC740
    OpcodeList2 = 0xC741
    OpcodeList3 = 0xC74E
    NoiseProfile = 0xC761


"""Maps EXIF tags to tag names."""
TAGS = {
    **{i.value: i.name for i in Base},
    0x920C: "SpatialFrequencyResponse",
    0x9214: "SubjectLocation",
    0x9215: "ExposureIndex",
    0x828E: "CFAPattern",
    0x920B: "FlashEnergy",
    0x9216: "TIFF/EPStandardID",
}


class GPS(IntEnum):
    GPSVersionID = 0x00
    GPSLatitudeRef = 0x01
    GPSLatitude = 0x02
    GPSLongitudeRef = 0x03
    GPSLongitude = 0x04
    GPSAltitudeRef = 0x05
    GPSAltitude = 0x06
    GPSTimeStamp = 0x07
    GPSSatellites = 0x08
    GPSStatus = 0x09
    GPSMeasureMode = 0x0A
    GPSDOP = 0x0B
    GPSSpeedRef = 0x0C
    GPSSpeed = 0x0D
    GPSTrackRef = 0x0E
    GPSTrack = 0x0F
    GPSImgDirectionRef = 0x10
    GPSImgDirection = 0x11
    GPSMapDatum = 0x12
    GPSDestLatitudeRef = 0x13
    GPSDestLatitude = 0x14
    GPSDestLongitudeRef = 0x15
    GPSDestLongitude = 0x16
    GPSDestBearingRef = 0x17
    GPSDestBearing = 0x18
    GPSDestDistanceRef = 0x19
    GPSDestDistance = 0x1A
    GPSProcessingMethod = 0x1B
    GPSAreaInformation = 0x1C
    GPSDateStamp = 0x1D
    GPSDifferential = 0x1E
    GPSHPositioningError = 0x1F


"""Maps EXIF GPS tags to tag names."""
GPSTAGS = {i.value: i.name for i in GPS}


class Interop(IntEnum):
    InteropIndex = 0x0001
    InteropVersion = 0x0002
    RelatedImageFileFormat = 0x1000
    RelatedImageWidth = 0x1001
    RelatedImageHeight = 0x1002


class IFD(IntEnum):
    Exif = 0x8769
    GPSInfo = 0x8825
    MakerNote = 0x927C
    Makernote = 0x927C  # Deprecated
    Interop = 0xA005
    IFD1 = -1


class LightSource(IntEnum):
    Unknown = 0x00
    Daylight = 0x01
    Fluorescent = 0x02
    Tungsten = 0x03
    Flash = 0x04
    Fine = 0x09
    Cloudy = 0x0A
    Shade = 0x0B
    DaylightFluorescent = 0x0C
    DayWhiteFluorescent = 0x0D
    CoolWhiteFluorescent = 0x0E
    WhiteFluorescent = 0x0F
    StandardLightA = 0x11
    StandardLightB = 0x12
    StandardLightC = 0x13
    D55 = 0x14
    D65 = 0x15
    D75 = 0x16
    D50 = 0x17
    ISO = 0x18
    Other = 0xFF

# === NexusCore/openenv\Lib\site-packages\anthropic\_utils\_transform.py ===
from __future__ import annotations

import io
import base64
import pathlib
from typing import Any, Mapping, TypeVar, cast
from datetime import date, datetime
from typing_extensions import Literal, get_args, override, get_type_hints

import anyio
import pydantic

from ._utils import (
    is_list,
    is_mapping,
    is_iterable,
)
from .._files import is_base64_file_input
from ._typing import (
    is_list_type,
    is_union_type,
    extract_type_arg,
    is_iterable_type,
    is_required_type,
    is_annotated_type,
    strip_annotated_type,
)
from .._compat import model_dump, is_typeddict

_T = TypeVar("_T")


# TODO: support for drilling globals() and locals()
# TODO: ensure works correctly with forward references in all cases


PropertyFormat = Literal["iso8601", "base64", "custom"]


class PropertyInfo:
    """Metadata class to be used in Annotated types to provide information about a given type.

    For example:

    class MyParams(TypedDict):
        account_holder_name: Annotated[str, PropertyInfo(alias='accountHolderName')]

    This means that {'account_holder_name': 'Robert'} will be transformed to {'accountHolderName': 'Robert'} before being sent to the API.
    """

    alias: str | None
    format: PropertyFormat | None
    format_template: str | None
    discriminator: str | None

    def __init__(
        self,
        *,
        alias: str | None = None,
        format: PropertyFormat | None = None,
        format_template: str | None = None,
        discriminator: str | None = None,
    ) -> None:
        self.alias = alias
        self.format = format
        self.format_template = format_template
        self.discriminator = discriminator

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(alias='{self.alias}', format={self.format}, format_template='{self.format_template}', discriminator='{self.discriminator}')"


def maybe_transform(
    data: object,
    expected_type: object,
) -> Any | None:
    """Wrapper over `transform()` that allows `None` to be passed.

    See `transform()` for more details.
    """
    if data is None:
        return None
    return transform(data, expected_type)


# Wrapper over _transform_recursive providing fake types
def transform(
    data: _T,
    expected_type: object,
) -> _T:
    """Transform dictionaries based off of type information from the given type, for example:

    ```py
    class Params(TypedDict, total=False):
        card_id: Required[Annotated[str, PropertyInfo(alias="cardID")]]


    transformed = transform({"card_id": "<my card ID>"}, Params)
    # {'cardID': '<my card ID>'}
    ```

    Any keys / data that does not have type information given will be included as is.

    It should be noted that the transformations that this function does are not represented in the type system.
    """
    transformed = _transform_recursive(data, annotation=cast(type, expected_type))
    return cast(_T, transformed)


def _get_annotated_type(type_: type) -> type | None:
    """If the given type is an `Annotated` type then it is returned, if not `None` is returned.

    This also unwraps the type when applicable, e.g. `Required[Annotated[T, ...]]`
    """
    if is_required_type(type_):
        # Unwrap `Required[Annotated[T, ...]]` to `Annotated[T, ...]`
        type_ = get_args(type_)[0]

    if is_annotated_type(type_):
        return type_

    return None


def _maybe_transform_key(key: str, type_: type) -> str:
    """Transform the given `data` based on the annotations provided in `type_`.

    Note: this function only looks at `Annotated` types that contain `PropertInfo` metadata.
    """
    annotated_type = _get_annotated_type(type_)
    if annotated_type is None:
        # no `Annotated` definition for this type, no transformation needed
        return key

    # ignore the first argument as it is the actual type
    annotations = get_args(annotated_type)[1:]
    for annotation in annotations:
        if isinstance(annotation, PropertyInfo) and annotation.alias is not None:
            return annotation.alias

    return key


def _transform_recursive(
    data: object,
    *,
    annotation: type,
    inner_type: type | None = None,
) -> object:
    """Transform the given data against the expected type.

    Args:
        annotation: The direct type annotation given to the particular piece of data.
            This may or may not be wrapped in metadata types, e.g. `Required[T]`, `Annotated[T, ...]` etc

        inner_type: If applicable, this is the "inside" type. This is useful in certain cases where the outside type
            is a container type such as `List[T]`. In that case `inner_type` should be set to `T` so that each entry in
            the list can be transformed using the metadata from the container type.

            Defaults to the same value as the `annotation` argument.
    """
    if inner_type is None:
        inner_type = annotation

    stripped_type = strip_annotated_type(inner_type)
    if is_typeddict(stripped_type) and is_mapping(data):
        return _transform_typeddict(data, stripped_type)

    if (
        # List[T]
        (is_list_type(stripped_type) and is_list(data))
        # Iterable[T]
        or (is_iterable_type(stripped_type) and is_iterable(data) and not isinstance(data, str))
    ):
        inner_type = extract_type_arg(stripped_type, 0)
        return [_transform_recursive(d, annotation=annotation, inner_type=inner_type) for d in data]

    if is_union_type(stripped_type):
        # For union types we run the transformation against all subtypes to ensure that everything is transformed.
        #
        # TODO: there may be edge cases where the same normalized field name will transform to two different names
        # in different subtypes.
        for subtype in get_args(stripped_type):
            data = _transform_recursive(data, annotation=annotation, inner_type=subtype)
        return data

    if isinstance(data, pydantic.BaseModel):
        return model_dump(data, exclude_unset=True)

    annotated_type = _get_annotated_type(annotation)
    if annotated_type is None:
        return data

    # ignore the first argument as it is the actual type
    annotations = get_args(annotated_type)[1:]
    for annotation in annotations:
        if isinstance(annotation, PropertyInfo) and annotation.format is not None:
            return _format_data(data, annotation.format, annotation.format_template)

    return data


def _format_data(data: object, format_: PropertyFormat, format_template: str | None) -> object:
    if isinstance(data, (date, datetime)):
        if format_ == "iso8601":
            return data.isoformat()

        if format_ == "custom" and format_template is not None:
            return data.strftime(format_template)

    if format_ == "base64" and is_base64_file_input(data):
        binary: str | bytes | None = None

        if isinstance(data, pathlib.Path):
            binary = data.read_bytes()
        elif isinstance(data, io.IOBase):
            binary = data.read()

            if isinstance(binary, str):  # type: ignore[unreachable]
                binary = binary.encode()

        if not isinstance(binary, bytes):
            raise RuntimeError(f"Could not read bytes from {data}; Received {type(binary)}")

        return base64.b64encode(binary).decode("ascii")

    return data


def _transform_typeddict(
    data: Mapping[str, object],
    expected_type: type,
) -> Mapping[str, object]:
    result: dict[str, object] = {}
    annotations = get_type_hints(expected_type, include_extras=True)
    for key, value in data.items():
        type_ = annotations.get(key)
        if type_ is None:
            # we do not have a type annotation for this field, leave it as is
            result[key] = value
        else:
            result[_maybe_transform_key(key, type_)] = _transform_recursive(value, annotation=type_)
    return result


async def async_maybe_transform(
    data: object,
    expected_type: object,
) -> Any | None:
    """Wrapper over `async_transform()` that allows `None` to be passed.

    See `async_transform()` for more details.
    """
    if data is None:
        return None
    return await async_transform(data, expected_type)


async def async_transform(
    data: _T,
    expected_type: object,
) -> _T:
    """Transform dictionaries based off of type information from the given type, for example:

    ```py
    class Params(TypedDict, total=False):
        card_id: Required[Annotated[str, PropertyInfo(alias="cardID")]]


    transformed = transform({"card_id": "<my card ID>"}, Params)
    # {'cardID': '<my card ID>'}
    ```

    Any keys / data that does not have type information given will be included as is.

    It should be noted that the transformations that this function does are not represented in the type system.
    """
    transformed = await _async_transform_recursive(data, annotation=cast(type, expected_type))
    return cast(_T, transformed)


async def _async_transform_recursive(
    data: object,
    *,
    annotation: type,
    inner_type: type | None = None,
) -> object:
    """Transform the given data against the expected type.

    Args:
        annotation: The direct type annotation given to the particular piece of data.
            This may or may not be wrapped in metadata types, e.g. `Required[T]`, `Annotated[T, ...]` etc

        inner_type: If applicable, this is the "inside" type. This is useful in certain cases where the outside type
            is a container type such as `List[T]`. In that case `inner_type` should be set to `T` so that each entry in
            the list can be transformed using the metadata from the container type.

            Defaults to the same value as the `annotation` argument.
    """
    if inner_type is None:
        inner_type = annotation

    stripped_type = strip_annotated_type(inner_type)
    if is_typeddict(stripped_type) and is_mapping(data):
        return await _async_transform_typeddict(data, stripped_type)

    if (
        # List[T]
        (is_list_type(stripped_type) and is_list(data))
        # Iterable[T]
        or (is_iterable_type(stripped_type) and is_iterable(data) and not isinstance(data, str))
    ):
        inner_type = extract_type_arg(stripped_type, 0)
        return [await _async_transform_recursive(d, annotation=annotation, inner_type=inner_type) for d in data]

    if is_union_type(stripped_type):
        # For union types we run the transformation against all subtypes to ensure that everything is transformed.
        #
        # TODO: there may be edge cases where the same normalized field name will transform to two different names
        # in different subtypes.
        for subtype in get_args(stripped_type):
            data = await _async_transform_recursive(data, annotation=annotation, inner_type=subtype)
        return data

    if isinstance(data, pydantic.BaseModel):
        return model_dump(data, exclude_unset=True)

    annotated_type = _get_annotated_type(annotation)
    if annotated_type is None:
        return data

    # ignore the first argument as it is the actual type
    annotations = get_args(annotated_type)[1:]
    for annotation in annotations:
        if isinstance(annotation, PropertyInfo) and annotation.format is not None:
            return await _async_format_data(data, annotation.format, annotation.format_template)

    return data


async def _async_format_data(data: object, format_: PropertyFormat, format_template: str | None) -> object:
    if isinstance(data, (date, datetime)):
        if format_ == "iso8601":
            return data.isoformat()

        if format_ == "custom" and format_template is not None:
            return data.strftime(format_template)

    if format_ == "base64" and is_base64_file_input(data):
        binary: str | bytes | None = None

        if isinstance(data, pathlib.Path):
            binary = await anyio.Path(data).read_bytes()
        elif isinstance(data, io.IOBase):
            binary = data.read()

            if isinstance(binary, str):  # type: ignore[unreachable]
                binary = binary.encode()

        if not isinstance(binary, bytes):
            raise RuntimeError(f"Could not read bytes from {data}; Received {type(binary)}")

        return base64.b64encode(binary).decode("ascii")

    return data


async def _async_transform_typeddict(
    data: Mapping[str, object],
    expected_type: type,
) -> Mapping[str, object]:
    result: dict[str, object] = {}
    annotations = get_type_hints(expected_type, include_extras=True)
    for key, value in data.items():
        type_ = annotations.get(key)
        if type_ is None:
            # we do not have a type annotation for this field, leave it as is
            result[key] = value
        else:
            result[_maybe_transform_key(key, type_)] = await _async_transform_recursive(value, annotation=type_)
    return result

# === NexusCore/openenv\Lib\site-packages\IPython\core\completerlib.py ===
# encoding: utf-8
"""Implementations for various useful completers.

These are all loaded by default by IPython.
"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2010-2011 The IPython Development Team.
#
#  Distributed under the terms of the BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib imports
import glob
import inspect
import os
import re
import sys
from importlib import import_module
from importlib.machinery import all_suffixes


# Third-party imports
from time import time
from zipimport import zipimporter

# Our own imports
from .completer import expand_user, compress_user
from .error import TryNext
from ..utils._process_common import arg_split

# FIXME: this should be pulled in with the right call via the component system
from IPython import get_ipython

from typing import List

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------
_suffixes = all_suffixes()

# Time in seconds after which the rootmodules will be stored permanently in the
# ipython ip.db database (kept in the user's .ipython dir).
TIMEOUT_STORAGE = 2

# Time in seconds after which we give up
TIMEOUT_GIVEUP = 20

# Regular expression for the python import statement
import_re = re.compile(r'(?P<name>[^\W\d]\w*?)'
                       r'(?P<package>[/\\]__init__)?'
                       r'(?P<suffix>%s)$' %
                       r'|'.join(re.escape(s) for s in _suffixes))

# RE for the ipython %run command (python + ipython scripts)
magic_run_re = re.compile(r'.*(\.ipy|\.ipynb|\.py[w]?)$')

#-----------------------------------------------------------------------------
# Local utilities
#-----------------------------------------------------------------------------


def module_list(path: str) -> List[str]:
    """
    Return the list containing the names of the modules available in the given
    folder.
    """
    # sys.path has the cwd as an empty string, but isdir/listdir need it as '.'
    if path == '':
        path = '.'

    # A few local constants to be used in loops below
    pjoin = os.path.join

    if os.path.isdir(path):
        # Build a list of all files in the directory and all files
        # in its subdirectories. For performance reasons, do not
        # recurse more than one level into subdirectories.
        files: List[str] = []
        for root, dirs, nondirs in os.walk(path, followlinks=True):
            subdir = root[len(path)+1:]
            if subdir:
                files.extend(pjoin(subdir, f) for f in nondirs)
                dirs[:] = [] # Do not recurse into additional subdirectories.
            else:
                files.extend(nondirs)

    else:
        try:
            files = list(zipimporter(path)._files.keys())  # type: ignore
        except Exception:
            files = []

    # Build a list of modules which match the import_re regex.
    modules = []
    for f in files:
        m = import_re.match(f)
        if m:
            modules.append(m.group('name'))
    return list(set(modules))


def get_root_modules():
    """
    Returns a list containing the names of all the modules available in the
    folders of the pythonpath.

    ip.db['rootmodules_cache'] maps sys.path entries to list of modules.
    """
    ip = get_ipython()
    if ip is None:
        # No global shell instance to store cached list of modules.
        # Don't try to scan for modules every time.
        return list(sys.builtin_module_names)

    if getattr(ip.db, "_mock", False):
        rootmodules_cache = {}
    else:
        rootmodules_cache = ip.db.get("rootmodules_cache", {})
    rootmodules = list(sys.builtin_module_names)
    start_time = time()
    store = False
    for path in sys.path:
        try:
            modules = rootmodules_cache[path]
        except KeyError:
            modules = module_list(path)
            try:
                modules.remove('__init__')
            except ValueError:
                pass
            if path not in ('', '.'): # cwd modules should not be cached
                rootmodules_cache[path] = modules
            if time() - start_time > TIMEOUT_STORAGE and not store:
                store = True
                print("\nCaching the list of root modules, please wait!")
                print("(This will only be done once - type '%rehashx' to "
                      "reset cache!)\n")
                sys.stdout.flush()
            if time() - start_time > TIMEOUT_GIVEUP:
                print("This is taking too long, we give up.\n")
                return []
        rootmodules.extend(modules)
    if store:
        ip.db['rootmodules_cache'] = rootmodules_cache
    rootmodules = list(set(rootmodules))
    return rootmodules


def is_importable(module, attr: str, only_modules) -> bool:
    if only_modules:
        try:
            mod = getattr(module, attr)
        except ModuleNotFoundError:
            # See gh-14434
            return False
        return inspect.ismodule(mod)
    else:
        return not(attr[:2] == '__' and attr[-2:] == '__')

def is_possible_submodule(module, attr):
    try:
        obj = getattr(module, attr)
    except AttributeError:
        # Is possibly an unimported submodule
        return True
    except TypeError:
        # https://github.com/ipython/ipython/issues/9678
        return False
    return inspect.ismodule(obj)


def try_import(mod: str, only_modules=False) -> List[str]:
    """
    Try to import given module and return list of potential completions.
    """
    mod = mod.rstrip('.')
    try:
        m = import_module(mod)
    except:
        return []

    m_is_init = '__init__' in (getattr(m, '__file__', '') or '')

    completions = []
    if (not hasattr(m, '__file__')) or (not only_modules) or m_is_init:
        completions.extend( [attr for attr in dir(m) if
                             is_importable(m, attr, only_modules)])

    m_all = getattr(m, "__all__", [])
    if only_modules:
        completions.extend(attr for attr in m_all if is_possible_submodule(m, attr))
    else:
        completions.extend(m_all)

    if m_is_init:
        file_ = m.__file__
        file_path = os.path.dirname(file_)  # type: ignore
        if file_path is not None:
            completions.extend(module_list(file_path))
    completions_set = {c for c in completions if isinstance(c, str)}
    completions_set.discard('__init__')
    return list(completions_set)


#-----------------------------------------------------------------------------
# Completion-related functions.
#-----------------------------------------------------------------------------

def quick_completer(cmd, completions):
    r""" Easily create a trivial completer for a command.

    Takes either a list of completions, or all completions in string (that will
    be split on whitespace).

    Example::

        [d:\ipython]|1> import ipy_completers
        [d:\ipython]|2> ipy_completers.quick_completer('foo', ['bar','baz'])
        [d:\ipython]|3> foo b<TAB>
        bar baz
        [d:\ipython]|3> foo ba
    """

    if isinstance(completions, str):
        completions = completions.split()

    def do_complete(self, event):
        return completions

    get_ipython().set_hook('complete_command',do_complete, str_key = cmd)

def module_completion(line):
    """
    Returns a list containing the completion possibilities for an import line.

    The line looks like this :
    'import xml.d'
    'from xml.dom import'
    """

    words = line.split(' ')
    nwords = len(words)

    # from whatever <tab> -> 'import '
    if nwords == 3 and words[0] == 'from':
        return ['import ']

    # 'from xy<tab>' or 'import xy<tab>'
    if nwords < 3 and (words[0] in {'%aimport', 'import', 'from'}) :
        if nwords == 1:
            return get_root_modules()
        mod = words[1].split('.')
        if len(mod) < 2:
            return get_root_modules()
        completion_list = try_import('.'.join(mod[:-1]), True)
        return ['.'.join(mod[:-1] + [el]) for el in completion_list]

    # 'from xyz import abc<tab>'
    if nwords >= 3 and words[0] == 'from':
        mod = words[1]
        return try_import(mod)

#-----------------------------------------------------------------------------
# Completers
#-----------------------------------------------------------------------------
# These all have the func(self, event) signature to be used as custom
# completers

def module_completer(self,event):
    """Give completions after user has typed 'import ...' or 'from ...'"""

    # This works in all versions of python.  While 2.5 has
    # pkgutil.walk_packages(), that particular routine is fairly dangerous,
    # since it imports *EVERYTHING* on sys.path.  That is: a) very slow b) full
    # of possibly problematic side effects.
    # This search the folders in the sys.path for available modules.

    return module_completion(event.line)

# FIXME: there's a lot of logic common to the run, cd and builtin file
# completers, that is currently reimplemented in each.

def magic_run_completer(self, event):
    """Complete files that end in .py or .ipy or .ipynb for the %run command.
    """
    comps = arg_split(event.line, strict=False)
    # relpath should be the current token that we need to complete.
    if (len(comps) > 1) and (not event.line.endswith(' ')):
        relpath = comps[-1].strip("'\"")
    else:
        relpath = ''

    #print("\nev=", event)  # dbg
    #print("rp=", relpath)  # dbg
    #print('comps=', comps)  # dbg

    lglob = glob.glob
    isdir = os.path.isdir
    relpath, tilde_expand, tilde_val = expand_user(relpath)

    # Find if the user has already typed the first filename, after which we
    # should complete on all files, since after the first one other files may
    # be arguments to the input script.

    if any(magic_run_re.match(c) for c in comps):
        matches =  [f.replace('\\','/') + ('/' if isdir(f) else '')
                            for f in lglob(relpath+'*')]
    else:
        dirs = [f.replace('\\','/') + "/" for f in lglob(relpath+'*') if isdir(f)]
        pys =  [f.replace('\\','/')
                for f in lglob(relpath+'*.py') + lglob(relpath+'*.ipy') +
                lglob(relpath+'*.ipynb') + lglob(relpath + '*.pyw')]

        matches = dirs + pys

    #print('run comp:', dirs+pys) # dbg
    return [compress_user(p, tilde_expand, tilde_val) for p in matches]


def cd_completer(self, event):
    """Completer function for cd, which only returns directories."""
    ip = get_ipython()
    relpath = event.symbol

    #print(event) # dbg
    if event.line.endswith('-b') or ' -b ' in event.line:
        # return only bookmark completions
        bkms = self.db.get('bookmarks', None)
        if bkms:
            return bkms.keys()
        else:
            return []

    if event.symbol == '-':
        width_dh = str(len(str(len(ip.user_ns['_dh']) + 1)))
        # jump in directory history by number
        fmt = '-%0' + width_dh +'d [%s]'
        ents = [ fmt % (i,s) for i,s in enumerate(ip.user_ns['_dh'])]
        if len(ents) > 1:
            return ents
        return []

    if event.symbol.startswith('--'):
        return ["--" + os.path.basename(d) for d in ip.user_ns['_dh']]

    # Expand ~ in path and normalize directory separators.
    relpath, tilde_expand, tilde_val = expand_user(relpath)
    relpath = relpath.replace('\\','/')

    found = []
    for d in [f.replace('\\','/') + '/' for f in glob.glob(relpath+'*')
              if os.path.isdir(f)]:
        if ' ' in d:
            # we don't want to deal with any of that, complex code
            # for this is elsewhere
            raise TryNext

        found.append(d)

    if not found:
        if os.path.isdir(relpath):
            return [compress_user(relpath, tilde_expand, tilde_val)]

        # if no completions so far, try bookmarks
        bks = self.db.get('bookmarks',{})
        bkmatches = [s for s in bks if s.startswith(event.symbol)]
        if bkmatches:
            return bkmatches

        raise TryNext

    return [compress_user(p, tilde_expand, tilde_val) for p in found]

def reset_completer(self, event):
    "A completer for %reset magic"
    return '-f -s in out array dhist'.split()

# === NexusCore/openenv\Lib\site-packages\parso\pgen2\generator.py ===
# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.

"""
This module defines the data structures used to represent a grammar.

Specifying grammars in pgen is possible with this grammar::

    grammar: (NEWLINE | rule)* ENDMARKER
    rule: NAME ':' rhs NEWLINE
    rhs: items ('|' items)*
    items: item+
    item: '[' rhs ']' | atom ['+' | '*']
    atom: '(' rhs ')' | NAME | STRING

This grammar is self-referencing.

This parser generator (pgen2) was created by Guido Rossum and used for lib2to3.
Most of the code has been refactored to make it more Pythonic. Since this was a
"copy" of the CPython Parser parser "pgen", there was some work needed to make
it more readable. It should also be slightly faster than the original pgen2,
because we made some optimizations.
"""

from ast import literal_eval
from typing import TypeVar, Generic, Mapping, Sequence, Set, Union

from parso.pgen2.grammar_parser import GrammarParser, NFAState

_TokenTypeT = TypeVar("_TokenTypeT")


class Grammar(Generic[_TokenTypeT]):
    """
    Once initialized, this class supplies the grammar tables for the
    parsing engine implemented by parse.py.  The parsing engine
    accesses the instance variables directly.

    The only important part in this parsers are dfas and transitions between
    dfas.
    """

    def __init__(self,
                 start_nonterminal: str,
                 rule_to_dfas: Mapping[str, Sequence['DFAState[_TokenTypeT]']],
                 reserved_syntax_strings: Mapping[str, 'ReservedString']):
        self.nonterminal_to_dfas = rule_to_dfas
        self.reserved_syntax_strings = reserved_syntax_strings
        self.start_nonterminal = start_nonterminal


class DFAPlan:
    """
    Plans are used for the parser to create stack nodes and do the proper
    DFA state transitions.
    """
    def __init__(self, next_dfa: 'DFAState', dfa_pushes: Sequence['DFAState'] = []):
        self.next_dfa = next_dfa
        self.dfa_pushes = dfa_pushes

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.next_dfa, self.dfa_pushes)


class DFAState(Generic[_TokenTypeT]):
    """
    The DFAState object is the core class for pretty much anything. DFAState
    are the vertices of an ordered graph while arcs and transitions are the
    edges.

    Arcs are the initial edges, where most DFAStates are not connected and
    transitions are then calculated to connect the DFA state machines that have
    different nonterminals.
    """
    def __init__(self, from_rule: str, nfa_set: Set[NFAState], final: NFAState):
        assert isinstance(nfa_set, set)
        assert isinstance(next(iter(nfa_set)), NFAState)
        assert isinstance(final, NFAState)
        self.from_rule = from_rule
        self.nfa_set = nfa_set
        # map from terminals/nonterminals to DFAState
        self.arcs: Mapping[str, DFAState] = {}
        # In an intermediary step we set these nonterminal arcs (which has the
        # same structure as arcs). These don't contain terminals anymore.
        self.nonterminal_arcs: Mapping[str, DFAState] = {}

        # Transitions are basically the only thing that  the parser is using
        # with is_final. Everyting else is purely here to create a parser.
        self.transitions: Mapping[Union[_TokenTypeT, ReservedString], DFAPlan] = {}
        self.is_final = final in nfa_set

    def add_arc(self, next_, label):
        assert isinstance(label, str)
        assert label not in self.arcs
        assert isinstance(next_, DFAState)
        self.arcs[label] = next_

    def unifystate(self, old, new):
        for label, next_ in self.arcs.items():
            if next_ is old:
                self.arcs[label] = new

    def __eq__(self, other):
        # Equality test -- ignore the nfa_set instance variable
        assert isinstance(other, DFAState)
        if self.is_final != other.is_final:
            return False
        # Can't just return self.arcs == other.arcs, because that
        # would invoke this method recursively, with cycles...
        if len(self.arcs) != len(other.arcs):
            return False
        for label, next_ in self.arcs.items():
            if next_ is not other.arcs.get(label):
                return False
        return True

    def __repr__(self):
        return '<%s: %s is_final=%s>' % (
            self.__class__.__name__, self.from_rule, self.is_final
        )


class ReservedString:
    """
    Most grammars will have certain keywords and operators that are mentioned
    in the grammar as strings (e.g. "if") and not token types (e.g. NUMBER).
    This class basically is the former.
    """

    def __init__(self, value: str):
        self.value = value

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.value)


def _simplify_dfas(dfas):
    """
    This is not theoretically optimal, but works well enough.
    Algorithm: repeatedly look for two states that have the same
    set of arcs (same labels pointing to the same nodes) and
    unify them, until things stop changing.

    dfas is a list of DFAState instances
    """
    changes = True
    while changes:
        changes = False
        for i, state_i in enumerate(dfas):
            for j in range(i + 1, len(dfas)):
                state_j = dfas[j]
                if state_i == state_j:
                    del dfas[j]
                    for state in dfas:
                        state.unifystate(state_j, state_i)
                    changes = True
                    break


def _make_dfas(start, finish):
    """
    Uses the powerset construction algorithm to create DFA states from sets of
    NFA states.

    Also does state reduction if some states are not needed.
    """
    # To turn an NFA into a DFA, we define the states of the DFA
    # to correspond to *sets* of states of the NFA.  Then do some
    # state reduction.
    assert isinstance(start, NFAState)
    assert isinstance(finish, NFAState)

    def addclosure(nfa_state, base_nfa_set):
        assert isinstance(nfa_state, NFAState)
        if nfa_state in base_nfa_set:
            return
        base_nfa_set.add(nfa_state)
        for nfa_arc in nfa_state.arcs:
            if nfa_arc.nonterminal_or_string is None:
                addclosure(nfa_arc.next, base_nfa_set)

    base_nfa_set = set()
    addclosure(start, base_nfa_set)
    states = [DFAState(start.from_rule, base_nfa_set, finish)]
    for state in states:  # NB states grows while we're iterating
        arcs = {}
        # Find state transitions and store them in arcs.
        for nfa_state in state.nfa_set:
            for nfa_arc in nfa_state.arcs:
                if nfa_arc.nonterminal_or_string is not None:
                    nfa_set = arcs.setdefault(nfa_arc.nonterminal_or_string, set())
                    addclosure(nfa_arc.next, nfa_set)

        # Now create the dfa's with no None's in arcs anymore. All Nones have
        # been eliminated and state transitions (arcs) are properly defined, we
        # just need to create the dfa's.
        for nonterminal_or_string, nfa_set in arcs.items():
            for nested_state in states:
                if nested_state.nfa_set == nfa_set:
                    # The DFA state already exists for this rule.
                    break
            else:
                nested_state = DFAState(start.from_rule, nfa_set, finish)
                states.append(nested_state)

            state.add_arc(nested_state, nonterminal_or_string)
    return states  # List of DFAState instances; first one is start


def _dump_nfa(start, finish):
    print("Dump of NFA for", start.from_rule)
    todo = [start]
    for i, state in enumerate(todo):
        print("  State", i, state is finish and "(final)" or "")
        for arc in state.arcs:
            label, next_ = arc.nonterminal_or_string, arc.next
            if next_ in todo:
                j = todo.index(next_)
            else:
                j = len(todo)
                todo.append(next_)
            if label is None:
                print("    -> %d" % j)
            else:
                print("    %s -> %d" % (label, j))


def _dump_dfas(dfas):
    print("Dump of DFA for", dfas[0].from_rule)
    for i, state in enumerate(dfas):
        print("  State", i, state.is_final and "(final)" or "")
        for nonterminal, next_ in state.arcs.items():
            print("    %s -> %d" % (nonterminal, dfas.index(next_)))


def generate_grammar(bnf_grammar: str, token_namespace) -> Grammar:
    """
    ``bnf_text`` is a grammar in extended BNF (using * for repetition, + for
    at-least-once repetition, [] for optional parts, | for alternatives and ()
    for grouping).

    It's not EBNF according to ISO/IEC 14977. It's a dialect Python uses in its
    own parser.
    """
    rule_to_dfas = {}
    start_nonterminal = None
    for nfa_a, nfa_z in GrammarParser(bnf_grammar).parse():
        # _dump_nfa(nfa_a, nfa_z)
        dfas = _make_dfas(nfa_a, nfa_z)
        # _dump_dfas(dfas)
        # oldlen = len(dfas)
        _simplify_dfas(dfas)
        # newlen = len(dfas)
        rule_to_dfas[nfa_a.from_rule] = dfas
        # print(nfa_a.from_rule, oldlen, newlen)

        if start_nonterminal is None:
            start_nonterminal = nfa_a.from_rule

    reserved_strings: Mapping[str, ReservedString] = {}
    for nonterminal, dfas in rule_to_dfas.items():
        for dfa_state in dfas:
            for terminal_or_nonterminal, next_dfa in dfa_state.arcs.items():
                if terminal_or_nonterminal in rule_to_dfas:
                    dfa_state.nonterminal_arcs[terminal_or_nonterminal] = next_dfa
                else:
                    transition = _make_transition(
                        token_namespace,
                        reserved_strings,
                        terminal_or_nonterminal
                    )
                    dfa_state.transitions[transition] = DFAPlan(next_dfa)

    _calculate_tree_traversal(rule_to_dfas)
    return Grammar(start_nonterminal, rule_to_dfas, reserved_strings)  # type: ignore[arg-type]


def _make_transition(token_namespace, reserved_syntax_strings, label):
    """
    Creates a reserved string ("if", "for", "*", ...) or returns the token type
    (NUMBER, STRING, ...) for a given grammar terminal.
    """
    if label[0].isalpha():
        # A named token (e.g. NAME, NUMBER, STRING)
        return getattr(token_namespace, label)
    else:
        # Either a keyword or an operator
        assert label[0] in ('"', "'"), label
        assert not label.startswith('"""') and not label.startswith("'''")
        value = literal_eval(label)
        try:
            return reserved_syntax_strings[value]
        except KeyError:
            r = reserved_syntax_strings[value] = ReservedString(value)
            return r


def _calculate_tree_traversal(nonterminal_to_dfas):
    """
    By this point we know how dfas can move around within a stack node, but we
    don't know how we can add a new stack node (nonterminal transitions).
    """
    # Map from grammar rule (nonterminal) name to a set of tokens.
    first_plans = {}

    nonterminals = list(nonterminal_to_dfas.keys())
    nonterminals.sort()
    for nonterminal in nonterminals:
        if nonterminal not in first_plans:
            _calculate_first_plans(nonterminal_to_dfas, first_plans, nonterminal)

    # Now that we have calculated the first terminals, we are sure that
    # there is no left recursion.

    for dfas in nonterminal_to_dfas.values():
        for dfa_state in dfas:
            transitions = dfa_state.transitions
            for nonterminal, next_dfa in dfa_state.nonterminal_arcs.items():
                for transition, pushes in first_plans[nonterminal].items():
                    if transition in transitions:
                        prev_plan = transitions[transition]
                        # Make sure these are sorted so that error messages are
                        # at least deterministic
                        choices = sorted([
                            (
                                prev_plan.dfa_pushes[0].from_rule
                                if prev_plan.dfa_pushes
                                else prev_plan.next_dfa.from_rule
                            ),
                            (
                                pushes[0].from_rule
                                if pushes else next_dfa.from_rule
                            ),
                        ])
                        raise ValueError(
                            "Rule %s is ambiguous; given a %s token, we "
                            "can't determine if we should evaluate %s or %s."
                            % (
                                (
                                    dfa_state.from_rule,
                                    transition,
                                ) + tuple(choices)
                            )
                        )
                    transitions[transition] = DFAPlan(next_dfa, pushes)


def _calculate_first_plans(nonterminal_to_dfas, first_plans, nonterminal):
    """
    Calculates the first plan in the first_plans dictionary for every given
    nonterminal. This is going to be used to know when to create stack nodes.
    """
    dfas = nonterminal_to_dfas[nonterminal]
    new_first_plans = {}
    first_plans[nonterminal] = None  # dummy to detect left recursion
    # We only need to check the first dfa. All the following ones are not
    # interesting to find first terminals.
    state = dfas[0]
    for transition, next_ in state.transitions.items():
        # It's a string. We have finally found a possible first token.
        new_first_plans[transition] = [next_.next_dfa]

    for nonterminal2, next_ in state.nonterminal_arcs.items():
        # It's a nonterminal and we have either a left recursion issue
        # in the grammar or we have to recurse.
        try:
            first_plans2 = first_plans[nonterminal2]
        except KeyError:
            first_plans2 = _calculate_first_plans(nonterminal_to_dfas, first_plans, nonterminal2)
        else:
            if first_plans2 is None:
                raise ValueError("left recursion for rule %r" % nonterminal)

        for t, pushes in first_plans2.items():
            new_first_plans[t] = [next_] + pushes

    first_plans[nonterminal] = new_first_plans
    return new_first_plans

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\regedit.py ===
# Regedit - a Registry Editor for Python

import commctrl
import regutil
import win32api
import win32con
import win32ui
from pywin.mfc import dialog, docview, window

from . import hierlist


def SafeApply(fn, args, err_desc=""):
    try:
        fn(*args)
        return 1
    except win32api.error as exc:
        msg = "Error " + err_desc + "\r\n\r\n" + exc.strerror
        win32ui.MessageBox(msg)
        return 0


class SplitterFrame(window.MDIChildWnd):
    def __init__(self):
        # call base CreateFrame
        self.images = None
        window.MDIChildWnd.__init__(self)

    def OnCreateClient(self, cp, context):
        splitter = win32ui.CreateSplitter()
        doc = context.doc
        frame_rect = self.GetWindowRect()
        size = ((frame_rect[2] - frame_rect[0]), (frame_rect[3] - frame_rect[1]) // 2)
        sub_size = (size[0] // 3, size[1])
        splitter.CreateStatic(self, 1, 2)
        # CTreeControl view
        self.keysview = RegistryTreeView(doc)
        # CListControl view
        self.valuesview = RegistryValueView(doc)

        splitter.CreatePane(self.keysview, 0, 0, (sub_size))
        splitter.CreatePane(self.valuesview, 0, 1, (0, 0))  # size ignored.
        splitter.SetRowInfo(0, size[1], 0)
        # Setup items in the imagelist

        return 1

    def OnItemDoubleClick(self, info, extra):
        (hwndFrom, idFrom, code) = info
        if idFrom == win32ui.AFX_IDW_PANE_FIRST:
            # Tree control
            return None
        elif idFrom == win32ui.AFX_IDW_PANE_FIRST + 1:
            item = self.keysview.SelectedItem()
            self.valuesview.EditValue(item)
            return 0
            # List control
        else:
            return None  # Pass it on

    def PerformItemSelected(self, item):
        return self.valuesview.UpdateForRegItem(item)

    def OnDestroy(self, msg):
        window.MDIChildWnd.OnDestroy(self, msg)
        if self.images:
            self.images.DeleteImageList()
            self.images = None


class RegistryTreeView(docview.TreeView):
    def OnInitialUpdate(self):
        rc = self._obj_.OnInitialUpdate()
        self.frame = self.GetParent().GetParent()
        self.hierList = hierlist.HierListWithItems(
            self.GetHLIRoot(), win32ui.IDB_HIERFOLDERS, win32ui.AFX_IDW_PANE_FIRST
        )
        self.hierList.HierInit(self.frame, self.GetTreeCtrl())
        self.hierList.SetStyle(
            commctrl.TVS_HASLINES | commctrl.TVS_LINESATROOT | commctrl.TVS_HASBUTTONS
        )
        self.hierList.PerformItemSelected = self.PerformItemSelected

        self.frame.HookNotify(self.frame.OnItemDoubleClick, commctrl.NM_DBLCLK)
        self.frame.HookNotify(self.OnItemRightClick, commctrl.NM_RCLICK)

    # 		self.HookMessage(self.OnItemRightClick, win32con.WM_RBUTTONUP)

    def GetHLIRoot(self):
        doc = self.GetDocument()
        regroot = doc.root
        subkey = doc.subkey
        return HLIRegistryKey(regroot, subkey, "Root")

    def OnItemRightClick(self, notify_data, extra):
        # First select the item we right-clicked on.
        pt = self.ScreenToClient(win32api.GetCursorPos())
        flags, hItem = self.HitTest(pt)
        if hItem == 0 or commctrl.TVHT_ONITEM & flags == 0:
            return None
        self.Select(hItem, commctrl.TVGN_CARET)

        menu = win32ui.CreatePopupMenu()
        menu.AppendMenu(win32con.MF_STRING | win32con.MF_ENABLED, 1000, "Add Key")
        menu.AppendMenu(win32con.MF_STRING | win32con.MF_ENABLED, 1001, "Add Value")
        menu.AppendMenu(win32con.MF_STRING | win32con.MF_ENABLED, 1002, "Delete Key")
        self.HookCommand(self.OnAddKey, 1000)
        self.HookCommand(self.OnAddValue, 1001)
        self.HookCommand(self.OnDeleteKey, 1002)
        menu.TrackPopupMenu(win32api.GetCursorPos())  # track at mouse position.
        return None

    def OnDeleteKey(self, command, code):
        hitem = self.hierList.GetSelectedItem()
        item = self.hierList.ItemFromHandle(hitem)
        msg = f"Are you sure you wish to delete the key '{item.keyName}'?"
        id = win32ui.MessageBox(msg, None, win32con.MB_YESNO)
        if id != win32con.IDYES:
            return
        if SafeApply(
            win32api.RegDeleteKey, (item.keyRoot, item.keyName), "deleting registry key"
        ):
            # Get the items parent.
            try:
                hparent = self.GetParentItem(hitem)
            except win32ui.error:
                hparent = None
            self.hierList.Refresh(hparent)

    def OnAddKey(self, command, code):
        val = dialog.GetSimpleInput("New key name", "", "Add new key")
        if val is None:
            return  # cancelled.
        hitem = self.hierList.GetSelectedItem()
        item = self.hierList.ItemFromHandle(hitem)
        if SafeApply(win32api.RegCreateKey, (item.keyRoot, item.keyName + "\\" + val)):
            self.hierList.Refresh(hitem)

    def OnAddValue(self, command, code):
        val = dialog.GetSimpleInput("New value", "", "Add new value")
        if val is None:
            return  # cancelled.
        hitem = self.hierList.GetSelectedItem()
        item = self.hierList.ItemFromHandle(hitem)
        if SafeApply(
            win32api.RegSetValue, (item.keyRoot, item.keyName, win32con.REG_SZ, val)
        ):
            # Simply re-select the current item to refresh the right spitter.
            self.PerformItemSelected(item)

    # 			self.Select(hitem, commctrl.TVGN_CARET)

    def PerformItemSelected(self, item):
        return self.frame.PerformItemSelected(item)

    def SelectedItem(self):
        return self.hierList.ItemFromHandle(self.hierList.GetSelectedItem())

    def SearchSelectedItem(self):
        handle = self.hierList.GetChildItem(0)
        while 1:
            # print("State is", self.hierList.GetItemState(handle, -1))
            if self.hierList.GetItemState(handle, commctrl.TVIS_SELECTED):
                # print("Item is ", self.hierList.ItemFromHandle(handle))
                return self.hierList.ItemFromHandle(handle)
            handle = self.hierList.GetNextSiblingItem(handle)


class RegistryValueView(docview.ListView):
    def OnInitialUpdate(self):
        hwnd = self._obj_.GetSafeHwnd()
        style = win32api.GetWindowLong(hwnd, win32con.GWL_STYLE)
        win32api.SetWindowLong(
            hwnd,
            win32con.GWL_STYLE,
            (style & ~commctrl.LVS_TYPEMASK) | commctrl.LVS_REPORT,
        )

        itemDetails = (commctrl.LVCFMT_LEFT, 100, "Name", 0)
        self.InsertColumn(0, itemDetails)
        itemDetails = (commctrl.LVCFMT_LEFT, 500, "Data", 0)
        self.InsertColumn(1, itemDetails)

    def UpdateForRegItem(self, item):
        self.DeleteAllItems()
        hkey = win32api.RegOpenKey(item.keyRoot, item.keyName)
        try:
            valNum = 0
            ret = []
            while 1:
                try:
                    res = win32api.RegEnumValue(hkey, valNum)
                except win32api.error:
                    break
                name = res[0]
                if not name:
                    name = "(Default)"
                self.InsertItem(valNum, name)
                self.SetItemText(valNum, 1, str(res[1]))
                valNum += 1
        finally:
            win32api.RegCloseKey(hkey)

    def EditValue(self, item):
        # Edit the current value
        class EditDialog(dialog.Dialog):
            def __init__(self, item):
                self.item = item
                dialog.Dialog.__init__(self, win32ui.IDD_LARGE_EDIT)

            def OnInitDialog(self):
                self.SetWindowText("Enter new value")
                self.GetDlgItem(win32con.IDCANCEL).ShowWindow(win32con.SW_SHOW)
                self.edit = self.GetDlgItem(win32ui.IDC_EDIT1)
                # Modify the edit windows style
                style = win32api.GetWindowLong(
                    self.edit.GetSafeHwnd(), win32con.GWL_STYLE
                )
                style &= ~win32con.ES_WANTRETURN
                win32api.SetWindowLong(
                    self.edit.GetSafeHwnd(), win32con.GWL_STYLE, style
                )
                self.edit.SetWindowText(str(self.item))
                self.edit.SetSel(-1)
                return dialog.Dialog.OnInitDialog(self)

            def OnDestroy(self, msg):
                self.newvalue = self.edit.GetWindowText()

        try:
            index = self.GetNextItem(-1, commctrl.LVNI_SELECTED)
        except win32ui.error:
            return  # No item selected.

        if index == 0:
            keyVal = ""
        else:
            keyVal = self.GetItemText(index, 0)
        # Query for a new value.
        try:
            newVal = self.GetItemsCurrentValue(item, keyVal)
        except TypeError as details:
            win32ui.MessageBox(details)
            return

        d = EditDialog(newVal)
        if d.DoModal() == win32con.IDOK:
            try:
                self.SetItemsCurrentValue(item, keyVal, d.newvalue)
            except win32api.error as exc:
                win32ui.MessageBox("Error setting value\r\n\n%s" % exc.strerror)
            self.UpdateForRegItem(item)

    def GetItemsCurrentValue(self, item, valueName):
        hkey = win32api.RegOpenKey(item.keyRoot, item.keyName)
        try:
            val, type = win32api.RegQueryValueEx(hkey, valueName)
            if type != win32con.REG_SZ:
                raise TypeError("Only strings can be edited")
            return val
        finally:
            win32api.RegCloseKey(hkey)

    def SetItemsCurrentValue(self, item, valueName, value):
        # ** Assumes already checked is a string.
        hkey = win32api.RegOpenKey(
            item.keyRoot, item.keyName, 0, win32con.KEY_SET_VALUE
        )
        try:
            win32api.RegSetValueEx(hkey, valueName, 0, win32con.REG_SZ, value)
        finally:
            win32api.RegCloseKey(hkey)


class RegTemplate(docview.DocTemplate):
    def __init__(self):
        docview.DocTemplate.__init__(
            self, win32ui.IDR_PYTHONTYPE, None, SplitterFrame, None
        )

    # 	def InitialUpdateFrame(self, frame, doc, makeVisible=1):
    # 		self._obj_.InitialUpdateFrame(frame, doc, makeVisible) # call default handler.
    # 		frame.InitialUpdateFrame(doc, makeVisible)

    def OpenRegistryKey(
        self, root=None, subkey=None
    ):  # Use this instead of OpenDocumentFile.
        # Look for existing open document
        if root is None:
            root = regutil.GetRootKey()
        if subkey is None:
            subkey = regutil.BuildDefaultPythonKey()
        for doc in self.GetDocumentList():
            if doc.root == root and doc.subkey == subkey:
                doc.GetFirstView().ActivateFrame()
                return doc
        # not found - new one.
        doc = RegDocument(self, root, subkey)
        frame = self.CreateNewFrame(doc)
        doc.OnNewDocument()
        self.InitialUpdateFrame(frame, doc, 1)
        return doc


class RegDocument(docview.Document):
    def __init__(self, template, root, subkey):
        docview.Document.__init__(self, template)
        self.root = root
        self.subkey = subkey
        self.SetTitle("Registry Editor: " + subkey)

    def OnOpenDocument(self, name):
        raise TypeError("This template can not open files")
        return 0


class HLIRegistryKey(hierlist.HierListItem):
    def __init__(self, keyRoot, keyName, userName):
        self.keyRoot = keyRoot
        self.keyName = keyName
        self.userName = userName
        hierlist.HierListItem.__init__(self)

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return (
            self.keyRoot == other.keyRoot
            and self.keyName == other.keyName
            and self.userName == other.userName
        )

    def __repr__(self):
        return "<{} with root={}, key={}>".format(
            self.__class__.__name__,
            self.keyRoot,
            self.keyName,
        )

    def GetText(self):
        return self.userName

    def IsExpandable(self):
        # All keys are expandable, even if they currently have zero children.
        return 1

    ##		hkey = win32api.RegOpenKey(self.keyRoot, self.keyName)
    ##		try:
    ##			keys, vals, dt = win32api.RegQueryInfoKey(hkey)
    ##			return (keys>0)
    ##		finally:
    ##			win32api.RegCloseKey(hkey)

    def GetSubList(self):
        hkey = win32api.RegOpenKey(self.keyRoot, self.keyName)
        win32ui.DoWaitCursor(1)
        try:
            keyNum = 0
            ret = []
            while 1:
                try:
                    key = win32api.RegEnumKey(hkey, keyNum)
                except win32api.error:
                    break
                ret.append(HLIRegistryKey(self.keyRoot, self.keyName + "\\" + key, key))
                keyNum += 1
        finally:
            win32api.RegCloseKey(hkey)
            win32ui.DoWaitCursor(0)
        return ret


template = RegTemplate()


def EditRegistry(root=None, key=None):
    doc = template.OpenRegistryKey(root, key)


if __name__ == "__main__":
    EditRegistry()

# === NexusCore/openenv\Lib\site-packages\joblib\_dask.py ===
from __future__ import absolute_import, division, print_function

import asyncio
import concurrent.futures
import contextlib
import time
import weakref
from uuid import uuid4

from ._utils import (
    _retrieve_traceback_capturing_wrapped_call,
    _TracebackCapturingWrapper,
)
from .parallel import AutoBatchingMixin, ParallelBackendBase, parallel_config

try:
    import dask
    import distributed
except ImportError:
    dask = None
    distributed = None

if dask is not None and distributed is not None:
    from dask.distributed import (
        Client,
        as_completed,
        get_client,
        rejoin,
        secede,
    )
    from dask.sizeof import sizeof
    from dask.utils import funcname
    from distributed.utils import thread_state

    try:
        # asyncio.TimeoutError, Python3-only error thrown by recent versions of
        # distributed
        from distributed.utils import TimeoutError as _TimeoutError
    except ImportError:
        from tornado.gen import TimeoutError as _TimeoutError


def is_weakrefable(obj):
    try:
        weakref.ref(obj)
        return True
    except TypeError:
        return False


class _WeakKeyDictionary:
    """A variant of weakref.WeakKeyDictionary for unhashable objects.

    This datastructure is used to store futures for broadcasted data objects
    such as large numpy arrays or pandas dataframes that are not hashable and
    therefore cannot be used as keys of traditional python dicts.

    Furthermore using a dict with id(array) as key is not safe because the
    Python is likely to reuse id of recently collected arrays.
    """

    def __init__(self):
        self._data = {}

    def __getitem__(self, obj):
        ref, val = self._data[id(obj)]
        if ref() is not obj:
            # In case of a race condition with on_destroy.
            raise KeyError(obj)
        return val

    def __setitem__(self, obj, value):
        key = id(obj)
        try:
            ref, _ = self._data[key]
            if ref() is not obj:
                # In case of race condition with on_destroy.
                raise KeyError(obj)
        except KeyError:
            # Insert the new entry in the mapping along with a weakref
            # callback to automatically delete the entry from the mapping
            # as soon as the object used as key is garbage collected.
            def on_destroy(_):
                del self._data[key]

            ref = weakref.ref(obj, on_destroy)
        self._data[key] = ref, value

    def __len__(self):
        return len(self._data)

    def clear(self):
        self._data.clear()


def _funcname(x):
    try:
        if isinstance(x, list):
            x = x[0][0]
    except Exception:
        pass
    return funcname(x)


def _make_tasks_summary(tasks):
    """Summarize of list of (func, args, kwargs) function calls"""
    unique_funcs = {func for func, args, kwargs in tasks}

    if len(unique_funcs) == 1:
        mixed = False
    else:
        mixed = True
    return len(tasks), mixed, _funcname(tasks)


class Batch:
    """dask-compatible wrapper that executes a batch of tasks"""

    def __init__(self, tasks):
        # collect some metadata from the tasks to ease Batch calls
        # introspection when debugging
        self._num_tasks, self._mixed, self._funcname = _make_tasks_summary(tasks)

    def __call__(self, tasks=None):
        results = []
        with parallel_config(backend="dask"):
            for func, args, kwargs in tasks:
                results.append(func(*args, **kwargs))
            return results

    def __repr__(self):
        descr = f"batch_of_{self._funcname}_{self._num_tasks}_calls"
        if self._mixed:
            descr = "mixed_" + descr
        return descr


def _joblib_probe_task():
    # Noop used by the joblib connector to probe when workers are ready.
    pass


class DaskDistributedBackend(AutoBatchingMixin, ParallelBackendBase):
    MIN_IDEAL_BATCH_DURATION = 0.2
    MAX_IDEAL_BATCH_DURATION = 1.0
    supports_retrieve_callback = True
    default_n_jobs = -1

    def __init__(
        self,
        scheduler_host=None,
        scatter=None,
        client=None,
        loop=None,
        wait_for_workers_timeout=10,
        **submit_kwargs,
    ):
        super().__init__()

        if distributed is None:
            msg = (
                "You are trying to use 'dask' as a joblib parallel backend "
                "but dask is not installed. Please install dask "
                "to fix this error."
            )
            raise ValueError(msg)

        if client is None:
            if scheduler_host:
                client = Client(scheduler_host, loop=loop, set_as_default=False)
            else:
                try:
                    client = get_client()
                except ValueError as e:
                    msg = (
                        "To use Joblib with Dask first create a Dask Client"
                        "\n\n"
                        "    from dask.distributed import Client\n"
                        "    client = Client()\n"
                        "or\n"
                        "    client = Client('scheduler-address:8786')"
                    )
                    raise ValueError(msg) from e

        self.client = client

        if scatter is not None and not isinstance(scatter, (list, tuple)):
            raise TypeError(
                "scatter must be a list/tuple, got `%s`" % type(scatter).__name__
            )

        if scatter is not None and len(scatter) > 0:
            # Keep a reference to the scattered data to keep the ids the same
            self._scatter = list(scatter)
            scattered = self.client.scatter(scatter, broadcast=True)
            self.data_futures = {id(x): f for x, f in zip(scatter, scattered)}
        else:
            self._scatter = []
            self.data_futures = {}
        self.wait_for_workers_timeout = wait_for_workers_timeout
        self.submit_kwargs = submit_kwargs
        self.waiting_futures = as_completed(
            [], loop=client.loop, with_results=True, raise_errors=False
        )
        self._results = {}
        self._callbacks = {}

    async def _collect(self):
        while self._continue:
            async for future, result in self.waiting_futures:
                cf_future = self._results.pop(future)
                callback = self._callbacks.pop(future)
                if future.status == "error":
                    typ, exc, tb = result
                    cf_future.set_exception(exc)
                else:
                    cf_future.set_result(result)
                    callback(result)
            await asyncio.sleep(0.01)

    def __reduce__(self):
        return (DaskDistributedBackend, ())

    def get_nested_backend(self):
        return DaskDistributedBackend(client=self.client), -1

    def configure(self, n_jobs=1, parallel=None, **backend_args):
        self.parallel = parallel
        return self.effective_n_jobs(n_jobs)

    def start_call(self):
        self._continue = True
        self.client.loop.add_callback(self._collect)
        self.call_data_futures = _WeakKeyDictionary()

    def stop_call(self):
        # The explicit call to clear is required to break a cycling reference
        # to the futures.
        self._continue = False
        # wait for the future collection routine (self._backend._collect) to
        # finish in order to limit asyncio warnings due to aborting _collect
        # during a following backend termination call
        time.sleep(0.01)
        self.call_data_futures.clear()

    def effective_n_jobs(self, n_jobs):
        effective_n_jobs = sum(self.client.ncores().values())
        if effective_n_jobs != 0 or not self.wait_for_workers_timeout:
            return effective_n_jobs

        # If there is no worker, schedule a probe task to wait for the workers
        # to come up and be available. If the dask cluster is in adaptive mode
        # task might cause the cluster to provision some workers.
        try:
            self.client.submit(_joblib_probe_task).result(
                timeout=self.wait_for_workers_timeout
            )
        except _TimeoutError as e:
            error_msg = (
                "DaskDistributedBackend has no worker after {} seconds. "
                "Make sure that workers are started and can properly connect "
                "to the scheduler and increase the joblib/dask connection "
                "timeout with:\n\n"
                "parallel_config(backend='dask', wait_for_workers_timeout={})"
            ).format(
                self.wait_for_workers_timeout,
                max(10, 2 * self.wait_for_workers_timeout),
            )
            raise TimeoutError(error_msg) from e
        return sum(self.client.ncores().values())

    async def _to_func_args(self, func):
        itemgetters = dict()

        # Futures that are dynamically generated during a single call to
        # Parallel.__call__.
        call_data_futures = getattr(self, "call_data_futures", None)

        async def maybe_to_futures(args):
            out = []
            for arg in args:
                arg_id = id(arg)
                if arg_id in itemgetters:
                    out.append(itemgetters[arg_id])
                    continue

                f = self.data_futures.get(arg_id, None)
                if f is None and call_data_futures is not None:
                    try:
                        f = await call_data_futures[arg]
                    except KeyError:
                        pass
                    if f is None:
                        if is_weakrefable(arg) and sizeof(arg) > 1e3:
                            # Automatically scatter large objects to some of
                            # the workers to avoid duplicated data transfers.
                            # Rely on automated inter-worker data stealing if
                            # more workers need to reuse this data
                            # concurrently.
                            # set hash=False - nested scatter calls (i.e
                            # calling client.scatter inside a dask worker)
                            # using hash=True often raise CancelledError,
                            # see dask/distributed#3703
                            _coro = self.client.scatter(
                                arg, asynchronous=True, hash=False
                            )
                            # Centralize the scattering of identical arguments
                            # between concurrent apply_async callbacks by
                            # exposing the running coroutine in
                            # call_data_futures before it completes.
                            t = asyncio.Task(_coro)
                            call_data_futures[arg] = t

                            f = await t

                if f is not None:
                    out.append(f)
                else:
                    out.append(arg)
            return out

        tasks = []
        for f, args, kwargs in func.items:
            args = list(await maybe_to_futures(args))
            kwargs = dict(zip(kwargs.keys(), await maybe_to_futures(kwargs.values())))
            tasks.append((f, args, kwargs))

        return (Batch(tasks), tasks)

    def apply_async(self, func, callback=None):
        cf_future = concurrent.futures.Future()
        cf_future.get = cf_future.result  # achieve AsyncResult API

        async def f(func, callback):
            batch, tasks = await self._to_func_args(func)
            key = f"{repr(batch)}-{uuid4().hex}"

            dask_future = self.client.submit(
                _TracebackCapturingWrapper(batch),
                tasks=tasks,
                key=key,
                **self.submit_kwargs,
            )
            self.waiting_futures.add(dask_future)
            self._callbacks[dask_future] = callback
            self._results[dask_future] = cf_future

        self.client.loop.add_callback(f, func, callback)

        return cf_future

    def retrieve_result_callback(self, out):
        return _retrieve_traceback_capturing_wrapped_call(out)

    def abort_everything(self, ensure_ready=True):
        """Tell the client to cancel any task submitted via this instance

        joblib.Parallel will never access those results
        """
        with self.waiting_futures.lock:
            self.waiting_futures.futures.clear()
            while not self.waiting_futures.queue.empty():
                self.waiting_futures.queue.get()

    @contextlib.contextmanager
    def retrieval_context(self):
        """Override ParallelBackendBase.retrieval_context to avoid deadlocks.

        This removes thread from the worker's thread pool (using 'secede').
        Seceding avoids deadlock in nested parallelism settings.
        """
        # See 'joblib.Parallel.__call__' and 'joblib.Parallel.retrieve' for how
        # this is used.
        if hasattr(thread_state, "execution_state"):
            # we are in a worker. Secede to avoid deadlock.
            secede()

        yield

        if hasattr(thread_state, "execution_state"):
            rejoin()