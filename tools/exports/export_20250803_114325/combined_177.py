
# === NexusCore/openenv\Lib\site-packages\interpreter\core\respond.py ===
import json
import os
import re
import time
import traceback

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm
import openai

from .render_message import render_message


def respond(interpreter):
    """
    Yields chunks.
    Responds until it decides not to run any more code or say anything else.
    """

    last_unsupported_code = ""
    insert_loop_message = False

    while True:
        ## RENDER SYSTEM MESSAGE ##

        system_message = interpreter.system_message

        # Add language-specific system messages
        for language in interpreter.computer.terminal.languages:
            if hasattr(language, "system_message"):
                system_message += "\n\n" + language.system_message

        # Add custom instructions
        if interpreter.custom_instructions:
            system_message += "\n\n" + interpreter.custom_instructions

        # Add computer API system message
        if interpreter.computer.import_computer_api:
            if interpreter.computer.system_message not in system_message:
                system_message = (
                    system_message + "\n\n" + interpreter.computer.system_message
                )

        # Storing the messages so they're accessible in the interpreter's computer
        # no... this is a huge time sink.....
        # if interpreter.sync_computer:
        #     output = interpreter.computer.run(
        #         "python", f"messages={interpreter.messages}"
        #     )

        ## Rendering ↓
        rendered_system_message = render_message(interpreter, system_message)
        ## Rendering ↑

        rendered_system_message = {
            "role": "system",
            "type": "message",
            "content": rendered_system_message,
        }

        # Create the version of messages that we'll send to the LLM
        messages_for_llm = interpreter.messages.copy()
        messages_for_llm = [rendered_system_message] + messages_for_llm

        if insert_loop_message:
            messages_for_llm.append(
                {
                    "role": "user",
                    "type": "message",
                    "content": loop_message,
                }
            )
            # Yield two newlines to separate the LLMs reply from previous messages.
            yield {"role": "assistant", "type": "message", "content": "\n\n"}
            insert_loop_message = False

        ### RUN THE LLM ###

        assert (
            len(interpreter.messages) > 0
        ), "User message was not passed in. You need to pass in at least one message."

        if (
            interpreter.messages[-1]["type"] != "code"
        ):  # If it is, we should run the code (we do below)
            try:
                for chunk in interpreter.llm.run(messages_for_llm):
                    yield {"role": "assistant", **chunk}

            except litellm.exceptions.BudgetExceededError:
                interpreter.display_message(
                    f"""> Max budget exceeded

                    **Session spend:** ${litellm._current_cost}
                    **Max budget:** ${interpreter.max_budget}

                    Press CTRL-C then run `interpreter --max_budget [higher USD amount]` to proceed.
                """
                )
                break

                # Provide extra information on how to change API keys, if we encounter that error
                # (Many people writing GitHub issues were struggling with this)

            except Exception as e:
                error_message = str(e).lower()
                if (
                    interpreter.offline == False
                    and "auth" in error_message
                    or "api key" in error_message
                ):
                    output = traceback.format_exc()
                    raise Exception(
                        f"{output}\n\nThere might be an issue with your API key(s).\n\nTo reset your API key (we'll use OPENAI_API_KEY for this example, but you may need to reset your ANTHROPIC_API_KEY, HUGGINGFACE_API_KEY, etc):\n        Mac/Linux: 'export OPENAI_API_KEY=your-key-here'. Update your ~/.zshrc on MacOS or ~/.bashrc on Linux with the new key if it has already been persisted there.,\n        Windows: 'setx OPENAI_API_KEY your-key-here' then restart terminal.\n\n"
                    )
                elif (
                    type(e) == litellm.exceptions.RateLimitError
                    and "exceeded" in str(e).lower()
                    or "insufficient_quota" in str(e).lower()
                ):
                    display_markdown_message(
                        f""" > You ran out of current quota for OpenAI's API, please check your plan and billing details. You can either wait for the quota to reset or upgrade your plan.

                        To check your current usage and billing details, visit the [OpenAI billing page](https://platform.openai.com/settings/organization/billing/overview).

                        You can also use `interpreter --max_budget [higher USD amount]` to set a budget for your sessions.
                        """
                    )

                elif (
                    interpreter.offline == False and "not have access" in str(e).lower()
                ):
                    """
                    Check for invalid model in error message and then fallback.
                    """
                    if (
                        "invalid model" in error_message
                        or "model does not exist" in error_message
                    ):
                        provider_message = f"\n\nThe model '{interpreter.llm.model}' does not exist or is invalid. Please check the model name and try again.\n\nWould you like to try Open Interpreter's hosted `i` model instead? (y/n)\n\n  "
                    elif "groq" in error_message:
                        provider_message = f"\n\nYou do not have access to {interpreter.llm.model}. Please check with Groq for more details.\n\nWould you like to try Open Interpreter's hosted `i` model instead? (y/n)\n\n  "
                    else:
                        provider_message = f"\n\nYou do not have access to {interpreter.llm.model}. If you are using an OpenAI model, you may need to add a payment method and purchase credits for the OpenAI API billing page (this is different from ChatGPT Plus).\n\nhttps://platform.openai.com/account/billing/overview\n\nWould you like to try Open Interpreter's hosted `i` model instead? (y/n)\n\n"

                    print(provider_message)

                    response = input()
                    print("")  # <- Aesthetic choice

                    if response.strip().lower() == "y":
                        interpreter.llm.model = "i"
                        interpreter.display_message(f"> Model set to `i`")
                        interpreter.display_message(
                            "***Note:*** *Conversations with this model will be used to train our open-source model.*\n"
                        )

                    else:
                        raise
                elif interpreter.offline and not interpreter.os:
                    raise
                else:
                    raise

        ### RUN CODE (if it's there) ###

        if interpreter.messages[-1]["type"] == "code":
            if interpreter.verbose:
                print("Running code:", interpreter.messages[-1])

            try:
                # What language/code do you want to run?
                language = interpreter.messages[-1]["format"].lower().strip()
                code = interpreter.messages[-1]["content"]

                if code.startswith("`\n"):
                    code = code[2:].strip()
                    if interpreter.verbose:
                        print("Removing `\n")
                    interpreter.messages[-1]["content"] = code  # So the LLM can see it.

                # A common hallucination
                if code.startswith("functions.execute("):
                    edited_code = code.replace("functions.execute(", "").rstrip(")")
                    try:
                        code_dict = json.loads(edited_code)
                        language = code_dict.get("language", language)
                        code = code_dict.get("code", code)
                        interpreter.messages[-1][
                            "content"
                        ] = code  # So the LLM can see it.
                        interpreter.messages[-1][
                            "format"
                        ] = language  # So the LLM can see it.
                    except:
                        pass

                # print(code)
                # print("---")
                # time.sleep(2)

                if code.strip().endswith("executeexecute"):
                    code = code.replace("executeexecute", "")
                    try:
                        interpreter.messages[-1][
                            "content"
                        ] = code  # So the LLM can see it.
                    except:
                        pass

                if code.replace("\n", "").replace(" ", "").startswith('{"language":'):
                    try:
                        code_dict = json.loads(code)
                        if set(code_dict.keys()) == {"language", "code"}:
                            language = code_dict["language"]
                            code = code_dict["code"]
                            interpreter.messages[-1][
                                "content"
                            ] = code  # So the LLM can see it.
                            interpreter.messages[-1][
                                "format"
                            ] = language  # So the LLM can see it.
                    except:
                        pass

                if code.replace("\n", "").replace(" ", "").startswith("{language:"):
                    try:
                        code = code.replace("language: ", '"language": ').replace(
                            "code: ", '"code": '
                        )
                        code_dict = json.loads(code)
                        if set(code_dict.keys()) == {"language", "code"}:
                            language = code_dict["language"]
                            code = code_dict["code"]
                            interpreter.messages[-1][
                                "content"
                            ] = code  # So the LLM can see it.
                            interpreter.messages[-1][
                                "format"
                            ] = language  # So the LLM can see it.
                    except:
                        pass

                if (
                    language == "text"
                    or language == "markdown"
                    or language == "plaintext"
                ):
                    # It does this sometimes just to take notes. Let it, it's useful.
                    # In the future we should probably not detect this behavior as code at all.
                    real_content = interpreter.messages[-1]["content"]
                    interpreter.messages[-1] = {
                        "role": "assistant",
                        "type": "message",
                        "content": f"```\n{real_content}\n```",
                    }
                    continue

                # Is this language enabled/supported?
                if interpreter.computer.terminal.get_language(language) == None:
                    output = f"`{language}` disabled or not supported."

                    yield {
                        "role": "computer",
                        "type": "console",
                        "format": "output",
                        "content": output,
                    }

                    # Let the response continue so it can deal with the unsupported code in another way. Also prevent looping on the same piece of code.
                    if code != last_unsupported_code:
                        last_unsupported_code = code
                        continue
                    else:
                        break

                # Is there any code at all?
                if code.strip() == "":
                    yield {
                        "role": "computer",
                        "type": "console",
                        "format": "output",
                        "content": "Code block was empty. Please try again, be sure to write code before executing.",
                    }
                    continue

                # Yield a message, such that the user can stop code execution if they want to
                try:
                    yield {
                        "role": "computer",
                        "type": "confirmation",
                        "format": "execution",
                        "content": {
                            "type": "code",
                            "format": language,
                            "content": code,
                        },
                    }
                except GeneratorExit:
                    # The user might exit here.
                    # We need to tell python what we (the generator) should do if they exit
                    break

                # They may have edited the code! Grab it again
                code = [m for m in interpreter.messages if m["type"] == "code"][-1][
                    "content"
                ]

                # don't let it import computer — we handle that!
                if interpreter.computer.import_computer_api and language == "python":
                    code = code.replace("import computer\n", "pass\n")
                    code = re.sub(
                        r"import computer\.(\w+) as (\w+)", r"\2 = computer.\1", code
                    )
                    code = re.sub(
                        r"from computer import (.+)",
                        lambda m: "\n".join(
                            f"{x.strip()} = computer.{x.strip()}"
                            for x in m.group(1).split(", ")
                        ),
                        code,
                    )
                    code = re.sub(r"import computer\.\w+\n", "pass\n", code)
                    # If it does this it sees the screenshot twice (which is expected jupyter behavior)
                    if any(
                        [
                            code.strip().split("\n")[-1].startswith(text)
                            for text in [
                                "computer.display.view",
                                "computer.display.screenshot",
                                "computer.view",
                                "computer.screenshot",
                            ]
                        ]
                    ):
                        code = code + "\npass"

                # sync up some things (is this how we want to do this?)
                interpreter.computer.verbose = interpreter.verbose
                interpreter.computer.debug = interpreter.debug
                interpreter.computer.emit_images = interpreter.llm.supports_vision
                interpreter.computer.max_output = interpreter.max_output

                # sync up the interpreter's computer with your computer
                try:
                    if interpreter.sync_computer and language == "python":
                        computer_dict = interpreter.computer.to_dict()
                        if "_hashes" in computer_dict:
                            computer_dict.pop("_hashes")
                        if "system_message" in computer_dict:
                            computer_dict.pop("system_message")
                        computer_json = json.dumps(computer_dict)
                        sync_code = f"""import json\ncomputer.load_dict(json.loads('''{computer_json}'''))"""
                        interpreter.computer.run("python", sync_code)
                except Exception as e:
                    if interpreter.debug:
                        raise
                    print(str(e))
                    print("Failed to sync iComputer with your Computer. Continuing...")

                ## ↓ CODE IS RUN HERE

                for line in interpreter.computer.run(language, code, stream=True):
                    yield {"role": "computer", **line}

                ## ↑ CODE IS RUN HERE

                # sync up your computer with the interpreter's computer
                try:
                    if interpreter.sync_computer and language == "python":
                        # sync up the interpreter's computer with your computer
                        result = interpreter.computer.run(
                            "python",
                            """
                            import json
                            computer_dict = computer.to_dict()
                            if '_hashes' in computer_dict:
                                computer_dict.pop('_hashes')
                            if "system_message" in computer_dict:
                                computer_dict.pop("system_message")
                            print(json.dumps(computer_dict))
                            """,
                        )
                        result = result[-1]["content"]
                        interpreter.computer.load_dict(
                            json.loads(result.strip('"').strip("'"))
                        )
                except Exception as e:
                    if interpreter.debug:
                        raise
                    print(str(e))
                    print("Failed to sync your Computer with iComputer. Continuing.")

                # yield final "active_line" message, as if to say, no more code is running. unlightlight active lines
                # (is this a good idea? is this our responsibility? i think so — we're saying what line of code is running! ...?)
                yield {
                    "role": "computer",
                    "type": "console",
                    "format": "active_line",
                    "content": None,
                }

            except KeyboardInterrupt:
                break  # It's fine.
            except:
                yield {
                    "role": "computer",
                    "type": "console",
                    "format": "output",
                    "content": traceback.format_exc(),
                }

        else:
            ## LOOP MESSAGE
            # This makes it utter specific phrases if it doesn't want to be told to "Proceed."

            loop_message = interpreter.loop_message
            if interpreter.os:
                loop_message = loop_message.replace(
                    "If the entire task I asked for is done,",
                    "If the entire task I asked for is done, take a screenshot to verify it's complete, or if you've already taken a screenshot and verified it's complete,",
                )
            loop_breakers = interpreter.loop_breakers

            if (
                interpreter.loop
                and interpreter.messages
                and interpreter.messages[-1].get("role", "") == "assistant"
                and not any(
                    task_status in interpreter.messages[-1].get("content", "")
                    for task_status in loop_breakers
                )
            ):
                # Remove past loop_message messages
                interpreter.messages = [
                    message
                    for message in interpreter.messages
                    if message.get("content", "") != loop_message
                ]
                # Combine adjacent assistant messages, so hopefully it learns to just keep going!
                combined_messages = []
                for message in interpreter.messages:
                    if (
                        combined_messages
                        and message["role"] == "assistant"
                        and combined_messages[-1]["role"] == "assistant"
                        and message["type"] == "message"
                        and combined_messages[-1]["type"] == "message"
                    ):
                        combined_messages[-1]["content"] += "\n" + message["content"]
                    else:
                        combined_messages.append(message)
                interpreter.messages = combined_messages

                # Send model the loop_message:
                insert_loop_message = True

                continue

            # Doesn't want to run code. We're done!
            break

    return

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\freetypePen.py ===
# -*- coding: utf-8 -*-

"""Pen to rasterize paths with FreeType."""

__all__ = ["FreeTypePen"]

import os
import ctypes
import platform
import subprocess
import collections
import math

import freetype
from freetype.raw import FT_Outline_Get_Bitmap, FT_Outline_Get_BBox, FT_Outline_Get_CBox
from freetype.ft_types import FT_Pos
from freetype.ft_structs import FT_Vector, FT_BBox, FT_Bitmap, FT_Outline
from freetype.ft_enums import (
    FT_OUTLINE_NONE,
    FT_OUTLINE_EVEN_ODD_FILL,
    FT_PIXEL_MODE_GRAY,
    FT_CURVE_TAG_ON,
    FT_CURVE_TAG_CONIC,
    FT_CURVE_TAG_CUBIC,
)
from freetype.ft_errors import FT_Exception

from fontTools.pens.basePen import BasePen, PenError
from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform

Contour = collections.namedtuple("Contour", ("points", "tags"))


class FreeTypePen(BasePen):
    """Pen to rasterize paths with FreeType. Requires `freetype-py` module.

    Constructs ``FT_Outline`` from the paths, and renders it within a bitmap
    buffer.

    For ``array()`` and ``show()``, `numpy` and `matplotlib` must be installed.
    For ``image()``, `Pillow` is required. Each module is lazily loaded when the
    corresponding method is called.

    Args:
        glyphSet: a dictionary of drawable glyph objects keyed by name
            used to resolve component references in composite glyphs.

    Examples:
        If `numpy` and `matplotlib` is available, the following code will
        show the glyph image of `fi` in a new window::

            from fontTools.ttLib import TTFont
            from fontTools.pens.freetypePen import FreeTypePen
            from fontTools.misc.transform import Offset
            pen = FreeTypePen(None)
            font = TTFont('SourceSansPro-Regular.otf')
            glyph = font.getGlyphSet()['fi']
            glyph.draw(pen)
            width, ascender, descender = glyph.width, font['OS/2'].usWinAscent, -font['OS/2'].usWinDescent
            height = ascender - descender
            pen.show(width=width, height=height, transform=Offset(0, -descender))

        Combining with `uharfbuzz`, you can typeset a chunk of glyphs in a pen::

            import uharfbuzz as hb
            from fontTools.pens.freetypePen import FreeTypePen
            from fontTools.pens.transformPen import TransformPen
            from fontTools.misc.transform import Offset

            en1, en2, ar, ja = 'Typesetting', 'Jeff', 'صف الحروف', 'たいぷせっと'
            for text, font_path, direction, typo_ascender, typo_descender, vhea_ascender, vhea_descender, contain, features in (
                (en1, 'NotoSans-Regular.ttf',       'ltr', 2189, -600, None, None, False, {"kern": True, "liga": True}),
                (en2, 'NotoSans-Regular.ttf',       'ltr', 2189, -600, None, None, True,  {"kern": True, "liga": True}),
                (ar,  'NotoSansArabic-Regular.ttf', 'rtl', 1374, -738, None, None, False, {"kern": True, "liga": True}),
                (ja,  'NotoSansJP-Regular.otf',     'ltr', 880,  -120, 500,  -500, False, {"palt": True, "kern": True}),
                (ja,  'NotoSansJP-Regular.otf',     'ttb', 880,  -120, 500,  -500, False, {"vert": True, "vpal": True, "vkrn": True})
            ):
                blob = hb.Blob.from_file_path(font_path)
                face = hb.Face(blob)
                font = hb.Font(face)
                buf = hb.Buffer()
                buf.direction = direction
                buf.add_str(text)
                buf.guess_segment_properties()
                hb.shape(font, buf, features)

                x, y = 0, 0
                pen = FreeTypePen(None)
                for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
                    gid = info.codepoint
                    transformed = TransformPen(pen, Offset(x + pos.x_offset, y + pos.y_offset))
                    font.draw_glyph_with_pen(gid, transformed)
                    x += pos.x_advance
                    y += pos.y_advance

                offset, width, height = None, None, None
                if direction in ('ltr', 'rtl'):
                    offset = (0, -typo_descender)
                    width  = x
                    height = typo_ascender - typo_descender
                else:
                    offset = (-vhea_descender, -y)
                    width  = vhea_ascender - vhea_descender
                    height = -y
                pen.show(width=width, height=height, transform=Offset(*offset), contain=contain)

        For Jupyter Notebook, the rendered image will be displayed in a cell if
        you replace ``show()`` with ``image()`` in the examples.
    """

    def __init__(self, glyphSet):
        BasePen.__init__(self, glyphSet)
        self.contours = []

    def outline(self, transform=None, evenOdd=False):
        """Converts the current contours to ``FT_Outline``.

        Args:
            transform: An optional 6-tuple containing an affine transformation,
                or a ``Transform`` object from the ``fontTools.misc.transform``
                module.
            evenOdd: Pass ``True`` for even-odd fill instead of non-zero.
        """
        transform = transform or Transform()
        if not hasattr(transform, "transformPoint"):
            transform = Transform(*transform)
        n_contours = len(self.contours)
        n_points = sum((len(contour.points) for contour in self.contours))
        points = []
        for contour in self.contours:
            for point in contour.points:
                point = transform.transformPoint(point)
                points.append(
                    FT_Vector(
                        FT_Pos(otRound(point[0] * 64)), FT_Pos(otRound(point[1] * 64))
                    )
                )
        tags = []
        for contour in self.contours:
            for tag in contour.tags:
                tags.append(tag)
        contours = []
        contours_sum = 0
        for contour in self.contours:
            contours_sum += len(contour.points)
            contours.append(contours_sum - 1)
        flags = FT_OUTLINE_EVEN_ODD_FILL if evenOdd else FT_OUTLINE_NONE
        return FT_Outline(
            (ctypes.c_short)(n_contours),
            (ctypes.c_short)(n_points),
            (FT_Vector * n_points)(*points),
            (ctypes.c_ubyte * n_points)(*tags),
            (ctypes.c_short * n_contours)(*contours),
            (ctypes.c_int)(flags),
        )

    def buffer(
        self, width=None, height=None, transform=None, contain=False, evenOdd=False
    ):
        """Renders the current contours within a bitmap buffer.

        Args:
            width: Image width of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            height: Image height of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            transform: An optional 6-tuple containing an affine transformation,
                or a ``Transform`` object from the ``fontTools.misc.transform``
                module. The bitmap size is not affected by this matrix.
            contain: If ``True``, the image size will be automatically expanded
                so that it fits to the bounding box of the paths. Useful for
                rendering glyphs with negative sidebearings without clipping.
            evenOdd: Pass ``True`` for even-odd fill instead of non-zero.

        Returns:
            A tuple of ``(buffer, size)``, where ``buffer`` is a ``bytes``
            object of the resulted bitmap and ``size`` is a 2-tuple of its
            dimension.

        Notes:
            The image size should always be given explicitly if you need to get
            a proper glyph image. When ``width`` and ``height`` are omitted, it
            forcifully fits to the bounding box and the side bearings get
            cropped. If you pass ``0`` to both ``width`` and ``height`` and set
            ``contain`` to ``True``, it expands to the bounding box while
            maintaining the origin of the contours, meaning that LSB will be
            maintained but RSB won’t. The difference between the two becomes
            more obvious when rotate or skew transformation is applied.

        Example:
            .. code-block:: pycon

                >>>
                >> pen = FreeTypePen(None)
                >> glyph.draw(pen)
                >> buf, size = pen.buffer(width=500, height=1000)
                >> type(buf), len(buf), size
                (<class 'bytes'>, 500000, (500, 1000))
        """
        transform = transform or Transform()
        if not hasattr(transform, "transformPoint"):
            transform = Transform(*transform)
        contain_x, contain_y = contain or width is None, contain or height is None
        if contain_x or contain_y:
            dx, dy = transform.dx, transform.dy
            bbox = self.bbox
            p1, p2, p3, p4 = (
                transform.transformPoint((bbox[0], bbox[1])),
                transform.transformPoint((bbox[2], bbox[1])),
                transform.transformPoint((bbox[0], bbox[3])),
                transform.transformPoint((bbox[2], bbox[3])),
            )
            px, py = (p1[0], p2[0], p3[0], p4[0]), (p1[1], p2[1], p3[1], p4[1])
            if contain_x:
                if width is None:
                    dx = dx - min(*px)
                    width = max(*px) - min(*px)
                else:
                    dx = dx - min(min(*px), 0.0)
                    width = max(width, max(*px) - min(min(*px), 0.0))
            if contain_y:
                if height is None:
                    dy = dy - min(*py)
                    height = max(*py) - min(*py)
                else:
                    dy = dy - min(min(*py), 0.0)
                    height = max(height, max(*py) - min(min(*py), 0.0))
            transform = Transform(*transform[:4], dx, dy)
        width, height = math.ceil(width), math.ceil(height)
        buf = ctypes.create_string_buffer(width * height)
        bitmap = FT_Bitmap(
            (ctypes.c_int)(height),
            (ctypes.c_int)(width),
            (ctypes.c_int)(width),
            (ctypes.POINTER(ctypes.c_ubyte))(buf),
            (ctypes.c_short)(256),
            (ctypes.c_ubyte)(FT_PIXEL_MODE_GRAY),
            (ctypes.c_char)(0),
            (ctypes.c_void_p)(None),
        )
        outline = self.outline(transform=transform, evenOdd=evenOdd)
        err = FT_Outline_Get_Bitmap(
            freetype.get_handle(), ctypes.byref(outline), ctypes.byref(bitmap)
        )
        if err != 0:
            raise FT_Exception(err)
        return buf.raw, (width, height)

    def array(
        self, width=None, height=None, transform=None, contain=False, evenOdd=False
    ):
        """Returns the rendered contours as a numpy array. Requires `numpy`.

        Args:
            width: Image width of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            height: Image height of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            transform: An optional 6-tuple containing an affine transformation,
                or a ``Transform`` object from the ``fontTools.misc.transform``
                module. The bitmap size is not affected by this matrix.
            contain: If ``True``, the image size will be automatically expanded
                so that it fits to the bounding box of the paths. Useful for
                rendering glyphs with negative sidebearings without clipping.
            evenOdd: Pass ``True`` for even-odd fill instead of non-zero.

        Returns:
            A ``numpy.ndarray`` object with a shape of ``(height, width)``.
            Each element takes a value in the range of ``[0.0, 1.0]``.

        Notes:
            The image size should always be given explicitly if you need to get
            a proper glyph image. When ``width`` and ``height`` are omitted, it
            forcifully fits to the bounding box and the side bearings get
            cropped. If you pass ``0`` to both ``width`` and ``height`` and set
            ``contain`` to ``True``, it expands to the bounding box while
            maintaining the origin of the contours, meaning that LSB will be
            maintained but RSB won’t. The difference between the two becomes
            more obvious when rotate or skew transformation is applied.

        Example:
            .. code-block:: pycon

                >>>
                >> pen = FreeTypePen(None)
                >> glyph.draw(pen)
                >> arr = pen.array(width=500, height=1000)
                >> type(a), a.shape
                (<class 'numpy.ndarray'>, (1000, 500))
        """

        import numpy as np

        buf, size = self.buffer(
            width=width,
            height=height,
            transform=transform,
            contain=contain,
            evenOdd=evenOdd,
        )
        return np.frombuffer(buf, "B").reshape((size[1], size[0])) / 255.0

    def show(
        self, width=None, height=None, transform=None, contain=False, evenOdd=False
    ):
        """Plots the rendered contours with `pyplot`. Requires `numpy` and
        `matplotlib`.

        Args:
            width: Image width of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            height: Image height of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            transform: An optional 6-tuple containing an affine transformation,
                or a ``Transform`` object from the ``fontTools.misc.transform``
                module. The bitmap size is not affected by this matrix.
            contain: If ``True``, the image size will be automatically expanded
                so that it fits to the bounding box of the paths. Useful for
                rendering glyphs with negative sidebearings without clipping.
            evenOdd: Pass ``True`` for even-odd fill instead of non-zero.

        Notes:
            The image size should always be given explicitly if you need to get
            a proper glyph image. When ``width`` and ``height`` are omitted, it
            forcifully fits to the bounding box and the side bearings get
            cropped. If you pass ``0`` to both ``width`` and ``height`` and set
            ``contain`` to ``True``, it expands to the bounding box while
            maintaining the origin of the contours, meaning that LSB will be
            maintained but RSB won’t. The difference between the two becomes
            more obvious when rotate or skew transformation is applied.

        Example:
            .. code-block:: pycon

                >>>
                >> pen = FreeTypePen(None)
                >> glyph.draw(pen)
                >> pen.show(width=500, height=1000)
        """
        from matplotlib import pyplot as plt

        a = self.array(
            width=width,
            height=height,
            transform=transform,
            contain=contain,
            evenOdd=evenOdd,
        )
        plt.imshow(a, cmap="gray_r", vmin=0, vmax=1)
        plt.show()

    def image(
        self, width=None, height=None, transform=None, contain=False, evenOdd=False
    ):
        """Returns the rendered contours as a PIL image. Requires `Pillow`.
        Can be used to display a glyph image in Jupyter Notebook.

        Args:
            width: Image width of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            height: Image height of the bitmap in pixels. If omitted, it
                automatically fits to the bounding box of the contours.
            transform: An optional 6-tuple containing an affine transformation,
                or a ``Transform`` object from the ``fontTools.misc.transform``
                module. The bitmap size is not affected by this matrix.
            contain: If ``True``, the image size will be automatically expanded
                so that it fits to the bounding box of the paths. Useful for
                rendering glyphs with negative sidebearings without clipping.
            evenOdd: Pass ``True`` for even-odd fill instead of non-zero.

        Returns:
            A ``PIL.image`` object. The image is filled in black with alpha
            channel obtained from the rendered bitmap.

        Notes:
            The image size should always be given explicitly if you need to get
            a proper glyph image. When ``width`` and ``height`` are omitted, it
            forcifully fits to the bounding box and the side bearings get
            cropped. If you pass ``0`` to both ``width`` and ``height`` and set
            ``contain`` to ``True``, it expands to the bounding box while
            maintaining the origin of the contours, meaning that LSB will be
            maintained but RSB won’t. The difference between the two becomes
            more obvious when rotate or skew transformation is applied.

        Example:
            .. code-block:: pycon

                >>>
                >> pen = FreeTypePen(None)
                >> glyph.draw(pen)
                >> img = pen.image(width=500, height=1000)
                >> type(img), img.size
                (<class 'PIL.Image.Image'>, (500, 1000))
        """
        from PIL import Image

        buf, size = self.buffer(
            width=width,
            height=height,
            transform=transform,
            contain=contain,
            evenOdd=evenOdd,
        )
        img = Image.new("L", size, 0)
        img.putalpha(Image.frombuffer("L", size, buf))
        return img

    @property
    def bbox(self):
        """Computes the exact bounding box of an outline.

        Returns:
            A tuple of ``(xMin, yMin, xMax, yMax)``.
        """
        bbox = FT_BBox()
        outline = self.outline()
        FT_Outline_Get_BBox(ctypes.byref(outline), ctypes.byref(bbox))
        return (bbox.xMin / 64.0, bbox.yMin / 64.0, bbox.xMax / 64.0, bbox.yMax / 64.0)

    @property
    def cbox(self):
        """Returns an outline's ‘control box’.

        Returns:
            A tuple of ``(xMin, yMin, xMax, yMax)``.
        """
        cbox = FT_BBox()
        outline = self.outline()
        FT_Outline_Get_CBox(ctypes.byref(outline), ctypes.byref(cbox))
        return (cbox.xMin / 64.0, cbox.yMin / 64.0, cbox.xMax / 64.0, cbox.yMax / 64.0)

    def _moveTo(self, pt):
        contour = Contour([], [])
        self.contours.append(contour)
        contour.points.append(pt)
        contour.tags.append(FT_CURVE_TAG_ON)

    def _lineTo(self, pt):
        if not (self.contours and len(self.contours[-1].points) > 0):
            raise PenError("Contour missing required initial moveTo")
        contour = self.contours[-1]
        contour.points.append(pt)
        contour.tags.append(FT_CURVE_TAG_ON)

    def _curveToOne(self, p1, p2, p3):
        if not (self.contours and len(self.contours[-1].points) > 0):
            raise PenError("Contour missing required initial moveTo")
        t1, t2, t3 = FT_CURVE_TAG_CUBIC, FT_CURVE_TAG_CUBIC, FT_CURVE_TAG_ON
        contour = self.contours[-1]
        for p, t in ((p1, t1), (p2, t2), (p3, t3)):
            contour.points.append(p)
            contour.tags.append(t)

    def _qCurveToOne(self, p1, p2):
        if not (self.contours and len(self.contours[-1].points) > 0):
            raise PenError("Contour missing required initial moveTo")
        t1, t2 = FT_CURVE_TAG_CONIC, FT_CURVE_TAG_ON
        contour = self.contours[-1]
        for p, t in ((p1, t1), (p2, t2)):
            contour.points.append(p)
            contour.tags.append(t)

# === NexusCore/openenv\Lib\site-packages\litellm\caching\dual_cache.py ===
"""
Dual Cache implementation - Class to update both Redis and an in-memory cache simultaneously.

Has 4 primary methods:
    - set_cache
    - get_cache
    - async_set_cache
    - async_get_cache
"""

import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from litellm.types.caching import RedisPipelineIncrementOperation

import litellm
from litellm._logging import print_verbose, verbose_logger

from .base_cache import BaseCache
from .in_memory_cache import InMemoryCache
from .redis_cache import RedisCache

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any

from collections import OrderedDict


class LimitedSizeOrderedDict(OrderedDict):
    def __init__(self, *args, max_size=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_size = max_size

    def __setitem__(self, key, value):
        # If inserting a new key exceeds max size, remove the oldest item
        if len(self) >= self.max_size:
            self.popitem(last=False)
        super().__setitem__(key, value)


class DualCache(BaseCache):
    """
    DualCache is a cache implementation that updates both Redis and an in-memory cache simultaneously.
    When data is updated or inserted, it is written to both the in-memory cache + Redis.
    This ensures that even if Redis hasn't been updated yet, the in-memory cache reflects the most recent data.
    """

    def __init__(
        self,
        in_memory_cache: Optional[InMemoryCache] = None,
        redis_cache: Optional[RedisCache] = None,
        default_in_memory_ttl: Optional[float] = None,
        default_redis_ttl: Optional[float] = None,
        default_redis_batch_cache_expiry: Optional[float] = None,
        default_max_redis_batch_cache_size: int = 100,
    ) -> None:
        super().__init__()
        # If in_memory_cache is not provided, use the default InMemoryCache
        self.in_memory_cache = in_memory_cache or InMemoryCache()
        # If redis_cache is not provided, use the default RedisCache
        self.redis_cache = redis_cache
        self.last_redis_batch_access_time = LimitedSizeOrderedDict(
            max_size=default_max_redis_batch_cache_size
        )
        self.redis_batch_cache_expiry = (
            default_redis_batch_cache_expiry
            or litellm.default_redis_batch_cache_expiry
            or 10
        )
        self.default_in_memory_ttl = (
            default_in_memory_ttl or litellm.default_in_memory_ttl
        )
        self.default_redis_ttl = default_redis_ttl or litellm.default_redis_ttl

    def update_cache_ttl(
        self, default_in_memory_ttl: Optional[float], default_redis_ttl: Optional[float]
    ):
        if default_in_memory_ttl is not None:
            self.default_in_memory_ttl = default_in_memory_ttl

        if default_redis_ttl is not None:
            self.default_redis_ttl = default_redis_ttl

    def set_cache(self, key, value, local_only: bool = False, **kwargs):
        # Update both Redis and in-memory cache
        try:
            if self.in_memory_cache is not None:
                if "ttl" not in kwargs and self.default_in_memory_ttl is not None:
                    kwargs["ttl"] = self.default_in_memory_ttl

                self.in_memory_cache.set_cache(key, value, **kwargs)

            if self.redis_cache is not None and local_only is False:
                self.redis_cache.set_cache(key, value, **kwargs)
        except Exception as e:
            print_verbose(e)

    def increment_cache(
        self, key, value: int, local_only: bool = False, **kwargs
    ) -> int:
        """
        Key - the key in cache

        Value - int - the value you want to increment by

        Returns - int - the incremented value
        """
        try:
            result: int = value
            if self.in_memory_cache is not None:
                result = self.in_memory_cache.increment_cache(key, value, **kwargs)

            if self.redis_cache is not None and local_only is False:
                result = self.redis_cache.increment_cache(key, value, **kwargs)

            return result
        except Exception as e:
            verbose_logger.error(f"LiteLLM Cache: Excepton async add_cache: {str(e)}")
            raise e

    def get_cache(
        self,
        key,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
        **kwargs,
    ):
        # Try to fetch from in-memory cache first
        try:
            result = None
            if self.in_memory_cache is not None:
                in_memory_result = self.in_memory_cache.get_cache(key, **kwargs)

                if in_memory_result is not None:
                    result = in_memory_result

            if result is None and self.redis_cache is not None and local_only is False:
                # If not found in in-memory cache, try fetching from Redis
                redis_result = self.redis_cache.get_cache(
                    key, parent_otel_span=parent_otel_span
                )

                if redis_result is not None:
                    # Update in-memory cache with the value from Redis
                    self.in_memory_cache.set_cache(key, redis_result, **kwargs)

                result = redis_result

            print_verbose(f"get cache: cache result: {result}")
            return result
        except Exception:
            verbose_logger.error(traceback.format_exc())

    def batch_get_cache(
        self,
        keys: list,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
        **kwargs,
    ):
        received_args = locals()
        received_args.pop("self")

        def run_in_new_loop():
            """Run the coroutine in a new event loop within this thread."""
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(
                    self.async_batch_get_cache(**received_args)
                )
            finally:
                new_loop.close()
                asyncio.set_event_loop(None)

        try:
            # First, try to get the current event loop
            _ = asyncio.get_running_loop()
            # If we're already in an event loop, run in a separate thread
            # to avoid nested event loop issues
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()

        except RuntimeError:
            # No running event loop, we can safely run in this thread
            return run_in_new_loop()

    async def async_get_cache(
        self,
        key,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
        **kwargs,
    ):
        # Try to fetch from in-memory cache first
        try:
            print_verbose(
                f"async get cache: cache key: {key}; local_only: {local_only}"
            )
            result = None
            if self.in_memory_cache is not None:
                in_memory_result = await self.in_memory_cache.async_get_cache(
                    key, **kwargs
                )

                print_verbose(f"in_memory_result: {in_memory_result}")
                if in_memory_result is not None:
                    result = in_memory_result

            if result is None and self.redis_cache is not None and local_only is False:
                # If not found in in-memory cache, try fetching from Redis
                redis_result = await self.redis_cache.async_get_cache(
                    key, parent_otel_span=parent_otel_span
                )

                if redis_result is not None:
                    # Update in-memory cache with the value from Redis
                    await self.in_memory_cache.async_set_cache(
                        key, redis_result, **kwargs
                    )

                result = redis_result

            print_verbose(f"get cache: cache result: {result}")
            return result
        except Exception:
            verbose_logger.error(traceback.format_exc())

    def get_redis_batch_keys(
        self,
        current_time: float,
        keys: List[str],
        result: List[Any],
    ) -> List[str]:
        sublist_keys = []
        for key, value in zip(keys, result):
            if value is None:
                if (
                    key not in self.last_redis_batch_access_time
                    or current_time - self.last_redis_batch_access_time[key]
                    >= self.redis_batch_cache_expiry
                ):
                    sublist_keys.append(key)
        return sublist_keys

    async def async_batch_get_cache(
        self,
        keys: list,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
        **kwargs,
    ):
        try:
            result = [None for _ in range(len(keys))]
            if self.in_memory_cache is not None:
                in_memory_result = await self.in_memory_cache.async_batch_get_cache(
                    keys, **kwargs
                )

                if in_memory_result is not None:
                    result = in_memory_result

            if None in result and self.redis_cache is not None and local_only is False:
                """
                - for the none values in the result
                - check the redis cache
                """
                current_time = time.time()
                sublist_keys = self.get_redis_batch_keys(current_time, keys, result)

                # Only hit Redis if the last access time was more than 5 seconds ago
                if len(sublist_keys) > 0:
                    # If not found in in-memory cache, try fetching from Redis
                    redis_result = await self.redis_cache.async_batch_get_cache(
                        sublist_keys, parent_otel_span=parent_otel_span
                    )

                    if redis_result is not None:
                        # Update in-memory cache with the value from Redis
                        for key, value in redis_result.items():
                            if value is not None:
                                await self.in_memory_cache.async_set_cache(
                                    key, redis_result[key], **kwargs
                                )
                            # Update the last access time for each key fetched from Redis
                            self.last_redis_batch_access_time[key] = current_time

                    for key, value in redis_result.items():
                        index = keys.index(key)
                        result[index] = value

            return result
        except Exception:
            verbose_logger.error(traceback.format_exc())

    async def async_set_cache(self, key, value, local_only: bool = False, **kwargs):
        print_verbose(
            f"async set cache: cache key: {key}; local_only: {local_only}; value: {value}"
        )
        try:
            if self.in_memory_cache is not None:
                await self.in_memory_cache.async_set_cache(key, value, **kwargs)

            if self.redis_cache is not None and local_only is False:
                await self.redis_cache.async_set_cache(key, value, **kwargs)
        except Exception as e:
            verbose_logger.exception(
                f"LiteLLM Cache: Excepton async add_cache: {str(e)}"
            )

    # async_batch_set_cache
    async def async_set_cache_pipeline(
        self, cache_list: list, local_only: bool = False, **kwargs
    ):
        """
        Batch write values to the cache
        """
        print_verbose(
            f"async batch set cache: cache keys: {cache_list}; local_only: {local_only}"
        )
        try:
            if self.in_memory_cache is not None:
                await self.in_memory_cache.async_set_cache_pipeline(
                    cache_list=cache_list, **kwargs
                )

            if self.redis_cache is not None and local_only is False:
                await self.redis_cache.async_set_cache_pipeline(
                    cache_list=cache_list, ttl=kwargs.pop("ttl", None), **kwargs
                )
        except Exception as e:
            verbose_logger.exception(
                f"LiteLLM Cache: Excepton async add_cache: {str(e)}"
            )

    async def async_increment_cache(
        self,
        key,
        value: float,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
        **kwargs,
    ) -> float:
        """
        Key - the key in cache

        Value - float - the value you want to increment by

        Returns - float - the incremented value
        """
        try:
            result: float = value
            if self.in_memory_cache is not None:
                result = await self.in_memory_cache.async_increment(
                    key, value, **kwargs
                )

            if self.redis_cache is not None and local_only is False:
                result = await self.redis_cache.async_increment(
                    key,
                    value,
                    parent_otel_span=parent_otel_span,
                    ttl=kwargs.get("ttl", None),
                )

            return result
        except Exception as e:
            raise e  # don't log if exception is raised

    async def async_increment_cache_pipeline(
        self,
        increment_list: List["RedisPipelineIncrementOperation"],
        local_only: bool = False,
        parent_otel_span: Optional[Span] = None,
        **kwargs,
    ) -> Optional[List[float]]:
        try:
            result: Optional[List[float]] = None
            if self.in_memory_cache is not None:
                result = await self.in_memory_cache.async_increment_pipeline(
                    increment_list=increment_list,
                    parent_otel_span=parent_otel_span,
                )

            if self.redis_cache is not None and local_only is False:
                result = await self.redis_cache.async_increment_pipeline(
                    increment_list=increment_list,
                    parent_otel_span=parent_otel_span,
                )

            return result
        except Exception as e:
            raise e  # don't log if exception is raised

    async def async_set_cache_sadd(
        self, key, value: List, local_only: bool = False, **kwargs
    ) -> None:
        """
        Add value to a set

        Key - the key in cache

        Value - str - the value you want to add to the set

        Returns - None
        """
        try:
            if self.in_memory_cache is not None:
                _ = await self.in_memory_cache.async_set_cache_sadd(
                    key, value, ttl=kwargs.get("ttl", None)
                )

            if self.redis_cache is not None and local_only is False:
                _ = await self.redis_cache.async_set_cache_sadd(
                    key, value, ttl=kwargs.get("ttl", None)
                )

            return None
        except Exception as e:
            raise e  # don't log, if exception is raised

    def flush_cache(self):
        if self.in_memory_cache is not None:
            self.in_memory_cache.flush_cache()
        if self.redis_cache is not None:
            self.redis_cache.flush_cache()

    def delete_cache(self, key):
        """
        Delete a key from the cache
        """
        if self.in_memory_cache is not None:
            self.in_memory_cache.delete_cache(key)
        if self.redis_cache is not None:
            self.redis_cache.delete_cache(key)

    async def async_delete_cache(self, key: str):
        """
        Delete a key from the cache
        """
        if self.in_memory_cache is not None:
            self.in_memory_cache.delete_cache(key)
        if self.redis_cache is not None:
            await self.redis_cache.async_delete_cache(key)

    async def async_get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL of a key in in-memory cache or redis
        """
        ttl = await self.in_memory_cache.async_get_ttl(key)
        if ttl is None and self.redis_cache is not None:
            ttl = await self.redis_cache.async_get_ttl(key)
        return ttl

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\layer_tree.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: LayerTree (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom


class LayerId(str):
    '''
    Unique Layer identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> LayerId:
        return cls(json)

    def __repr__(self):
        return 'LayerId({})'.format(super().__repr__())


class SnapshotId(str):
    '''
    Unique snapshot identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SnapshotId:
        return cls(json)

    def __repr__(self):
        return 'SnapshotId({})'.format(super().__repr__())


@dataclass
class ScrollRect:
    '''
    Rectangle where scrolling happens on the main thread.
    '''
    #: Rectangle itself.
    rect: dom.Rect

    #: Reason for rectangle to force scrolling on the main thread
    type_: str

    def to_json(self):
        json = dict()
        json['rect'] = self.rect.to_json()
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rect=dom.Rect.from_json(json['rect']),
            type_=str(json['type']),
        )


@dataclass
class StickyPositionConstraint:
    '''
    Sticky position constraints.
    '''
    #: Layout rectangle of the sticky element before being shifted
    sticky_box_rect: dom.Rect

    #: Layout rectangle of the containing block of the sticky element
    containing_block_rect: dom.Rect

    #: The nearest sticky layer that shifts the sticky box
    nearest_layer_shifting_sticky_box: typing.Optional[LayerId] = None

    #: The nearest sticky layer that shifts the containing block
    nearest_layer_shifting_containing_block: typing.Optional[LayerId] = None

    def to_json(self):
        json = dict()
        json['stickyBoxRect'] = self.sticky_box_rect.to_json()
        json['containingBlockRect'] = self.containing_block_rect.to_json()
        if self.nearest_layer_shifting_sticky_box is not None:
            json['nearestLayerShiftingStickyBox'] = self.nearest_layer_shifting_sticky_box.to_json()
        if self.nearest_layer_shifting_containing_block is not None:
            json['nearestLayerShiftingContainingBlock'] = self.nearest_layer_shifting_containing_block.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            sticky_box_rect=dom.Rect.from_json(json['stickyBoxRect']),
            containing_block_rect=dom.Rect.from_json(json['containingBlockRect']),
            nearest_layer_shifting_sticky_box=LayerId.from_json(json['nearestLayerShiftingStickyBox']) if 'nearestLayerShiftingStickyBox' in json else None,
            nearest_layer_shifting_containing_block=LayerId.from_json(json['nearestLayerShiftingContainingBlock']) if 'nearestLayerShiftingContainingBlock' in json else None,
        )


@dataclass
class PictureTile:
    '''
    Serialized fragment of layer picture along with its offset within the layer.
    '''
    #: Offset from owning layer left boundary
    x: float

    #: Offset from owning layer top boundary
    y: float

    #: Base64-encoded snapshot data.
    picture: str

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['picture'] = self.picture
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            picture=str(json['picture']),
        )


@dataclass
class Layer:
    '''
    Information about a compositing layer.
    '''
    #: The unique id for this layer.
    layer_id: LayerId

    #: Offset from parent layer, X coordinate.
    offset_x: float

    #: Offset from parent layer, Y coordinate.
    offset_y: float

    #: Layer width.
    width: float

    #: Layer height.
    height: float

    #: Indicates how many time this layer has painted.
    paint_count: int

    #: Indicates whether this layer hosts any content, rather than being used for
    #: transform/scrolling purposes only.
    draws_content: bool

    #: The id of parent (not present for root).
    parent_layer_id: typing.Optional[LayerId] = None

    #: The backend id for the node associated with this layer.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Transformation matrix for layer, default is identity matrix
    transform: typing.Optional[typing.List[float]] = None

    #: Transform anchor point X, absent if no transform specified
    anchor_x: typing.Optional[float] = None

    #: Transform anchor point Y, absent if no transform specified
    anchor_y: typing.Optional[float] = None

    #: Transform anchor point Z, absent if no transform specified
    anchor_z: typing.Optional[float] = None

    #: Set if layer is not visible.
    invisible: typing.Optional[bool] = None

    #: Rectangles scrolling on main thread only.
    scroll_rects: typing.Optional[typing.List[ScrollRect]] = None

    #: Sticky position constraint information
    sticky_position_constraint: typing.Optional[StickyPositionConstraint] = None

    def to_json(self):
        json = dict()
        json['layerId'] = self.layer_id.to_json()
        json['offsetX'] = self.offset_x
        json['offsetY'] = self.offset_y
        json['width'] = self.width
        json['height'] = self.height
        json['paintCount'] = self.paint_count
        json['drawsContent'] = self.draws_content
        if self.parent_layer_id is not None:
            json['parentLayerId'] = self.parent_layer_id.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.transform is not None:
            json['transform'] = [i for i in self.transform]
        if self.anchor_x is not None:
            json['anchorX'] = self.anchor_x
        if self.anchor_y is not None:
            json['anchorY'] = self.anchor_y
        if self.anchor_z is not None:
            json['anchorZ'] = self.anchor_z
        if self.invisible is not None:
            json['invisible'] = self.invisible
        if self.scroll_rects is not None:
            json['scrollRects'] = [i.to_json() for i in self.scroll_rects]
        if self.sticky_position_constraint is not None:
            json['stickyPositionConstraint'] = self.sticky_position_constraint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            offset_x=float(json['offsetX']),
            offset_y=float(json['offsetY']),
            width=float(json['width']),
            height=float(json['height']),
            paint_count=int(json['paintCount']),
            draws_content=bool(json['drawsContent']),
            parent_layer_id=LayerId.from_json(json['parentLayerId']) if 'parentLayerId' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            transform=[float(i) for i in json['transform']] if 'transform' in json else None,
            anchor_x=float(json['anchorX']) if 'anchorX' in json else None,
            anchor_y=float(json['anchorY']) if 'anchorY' in json else None,
            anchor_z=float(json['anchorZ']) if 'anchorZ' in json else None,
            invisible=bool(json['invisible']) if 'invisible' in json else None,
            scroll_rects=[ScrollRect.from_json(i) for i in json['scrollRects']] if 'scrollRects' in json else None,
            sticky_position_constraint=StickyPositionConstraint.from_json(json['stickyPositionConstraint']) if 'stickyPositionConstraint' in json else None,
        )


class PaintProfile(list):
    '''
    Array of timings, one per paint step.
    '''
    def to_json(self) -> typing.List[float]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[float]) -> PaintProfile:
        return cls(json)

    def __repr__(self):
        return 'PaintProfile({})'.format(super().__repr__())


def compositing_reasons(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[str], typing.List[str]]]:
    '''
    Provides the reasons why the given layer was composited.

    :param layer_id: The id of the layer for which we want to get the reasons it was composited.
    :returns: A tuple with the following items:

        0. **compositingReasons** - A list of strings specifying reasons for the given layer to become composited.
        1. **compositingReasonIds** - A list of strings specifying reason IDs for the given layer to become composited.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.compositingReasons',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [str(i) for i in json['compositingReasons']],
        [str(i) for i in json['compositingReasonIds']]
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.enable',
    }
    json = yield cmd_dict


def load_snapshot(
        tiles: typing.List[PictureTile]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the snapshot identifier.

    :param tiles: An array of tiles composing the snapshot.
    :returns: The id of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['tiles'] = [i.to_json() for i in tiles]
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.loadSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def make_snapshot(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the layer snapshot identifier.

    :param layer_id: The id of the layer.
    :returns: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.makeSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def profile_snapshot(
        snapshot_id: SnapshotId,
        min_repeat_count: typing.Optional[int] = None,
        min_duration: typing.Optional[float] = None,
        clip_rect: typing.Optional[dom.Rect] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[PaintProfile]]:
    '''
    :param snapshot_id: The id of the layer snapshot.
    :param min_repeat_count: *(Optional)* The maximum number of times to replay the snapshot (1, if not specified).
    :param min_duration: *(Optional)* The minimum duration (in seconds) to replay the snapshot.
    :param clip_rect: *(Optional)* The clip rectangle to apply when replaying the snapshot.
    :returns: The array of paint profiles, one per run.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if min_repeat_count is not None:
        params['minRepeatCount'] = min_repeat_count
    if min_duration is not None:
        params['minDuration'] = min_duration
    if clip_rect is not None:
        params['clipRect'] = clip_rect.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.profileSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return [PaintProfile.from_json(i) for i in json['timings']]


def release_snapshot(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases layer snapshot captured by the back-end.

    :param snapshot_id: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.releaseSnapshot',
        'params': params,
    }
    json = yield cmd_dict


def replay_snapshot(
        snapshot_id: SnapshotId,
        from_step: typing.Optional[int] = None,
        to_step: typing.Optional[int] = None,
        scale: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Replays the layer snapshot and returns the resulting bitmap.

    :param snapshot_id: The id of the layer snapshot.
    :param from_step: *(Optional)* The first step to replay from (replay from the very start if not specified).
    :param to_step: *(Optional)* The last step to replay to (replay till the end if not specified).
    :param scale: *(Optional)* The scale to apply while replaying (defaults to 1).
    :returns: A data: URL for resulting image.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if from_step is not None:
        params['fromStep'] = from_step
    if to_step is not None:
        params['toStep'] = to_step
    if scale is not None:
        params['scale'] = scale
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.replaySnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['dataURL'])


def snapshot_command_log(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[dict]]:
    '''
    Replays the layer snapshot and returns canvas log.

    :param snapshot_id: The id of the layer snapshot.
    :returns: The array of canvas function calls.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.snapshotCommandLog',
        'params': params,
    }
    json = yield cmd_dict
    return [dict(i) for i in json['commandLog']]


@event_class('LayerTree.layerPainted')
@dataclass
class LayerPainted:
    #: The id of the painted layer.
    layer_id: LayerId
    #: Clip rectangle.
    clip: dom.Rect

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerPainted:
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            clip=dom.Rect.from_json(json['clip'])
        )


@event_class('LayerTree.layerTreeDidChange')
@dataclass
class LayerTreeDidChange:
    #: Layer tree, absent if not in the compositing mode.
    layers: typing.Optional[typing.List[Layer]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerTreeDidChange:
        return cls(
            layers=[Layer.from_json(i) for i in json['layers']] if 'layers' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\layer_tree.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: LayerTree (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom


class LayerId(str):
    '''
    Unique Layer identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> LayerId:
        return cls(json)

    def __repr__(self):
        return 'LayerId({})'.format(super().__repr__())


class SnapshotId(str):
    '''
    Unique snapshot identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SnapshotId:
        return cls(json)

    def __repr__(self):
        return 'SnapshotId({})'.format(super().__repr__())


@dataclass
class ScrollRect:
    '''
    Rectangle where scrolling happens on the main thread.
    '''
    #: Rectangle itself.
    rect: dom.Rect

    #: Reason for rectangle to force scrolling on the main thread
    type_: str

    def to_json(self):
        json = dict()
        json['rect'] = self.rect.to_json()
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rect=dom.Rect.from_json(json['rect']),
            type_=str(json['type']),
        )


@dataclass
class StickyPositionConstraint:
    '''
    Sticky position constraints.
    '''
    #: Layout rectangle of the sticky element before being shifted
    sticky_box_rect: dom.Rect

    #: Layout rectangle of the containing block of the sticky element
    containing_block_rect: dom.Rect

    #: The nearest sticky layer that shifts the sticky box
    nearest_layer_shifting_sticky_box: typing.Optional[LayerId] = None

    #: The nearest sticky layer that shifts the containing block
    nearest_layer_shifting_containing_block: typing.Optional[LayerId] = None

    def to_json(self):
        json = dict()
        json['stickyBoxRect'] = self.sticky_box_rect.to_json()
        json['containingBlockRect'] = self.containing_block_rect.to_json()
        if self.nearest_layer_shifting_sticky_box is not None:
            json['nearestLayerShiftingStickyBox'] = self.nearest_layer_shifting_sticky_box.to_json()
        if self.nearest_layer_shifting_containing_block is not None:
            json['nearestLayerShiftingContainingBlock'] = self.nearest_layer_shifting_containing_block.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            sticky_box_rect=dom.Rect.from_json(json['stickyBoxRect']),
            containing_block_rect=dom.Rect.from_json(json['containingBlockRect']),
            nearest_layer_shifting_sticky_box=LayerId.from_json(json['nearestLayerShiftingStickyBox']) if 'nearestLayerShiftingStickyBox' in json else None,
            nearest_layer_shifting_containing_block=LayerId.from_json(json['nearestLayerShiftingContainingBlock']) if 'nearestLayerShiftingContainingBlock' in json else None,
        )


@dataclass
class PictureTile:
    '''
    Serialized fragment of layer picture along with its offset within the layer.
    '''
    #: Offset from owning layer left boundary
    x: float

    #: Offset from owning layer top boundary
    y: float

    #: Base64-encoded snapshot data.
    picture: str

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['picture'] = self.picture
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            picture=str(json['picture']),
        )


@dataclass
class Layer:
    '''
    Information about a compositing layer.
    '''
    #: The unique id for this layer.
    layer_id: LayerId

    #: Offset from parent layer, X coordinate.
    offset_x: float

    #: Offset from parent layer, Y coordinate.
    offset_y: float

    #: Layer width.
    width: float

    #: Layer height.
    height: float

    #: Indicates how many time this layer has painted.
    paint_count: int

    #: Indicates whether this layer hosts any content, rather than being used for
    #: transform/scrolling purposes only.
    draws_content: bool

    #: The id of parent (not present for root).
    parent_layer_id: typing.Optional[LayerId] = None

    #: The backend id for the node associated with this layer.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Transformation matrix for layer, default is identity matrix
    transform: typing.Optional[typing.List[float]] = None

    #: Transform anchor point X, absent if no transform specified
    anchor_x: typing.Optional[float] = None

    #: Transform anchor point Y, absent if no transform specified
    anchor_y: typing.Optional[float] = None

    #: Transform anchor point Z, absent if no transform specified
    anchor_z: typing.Optional[float] = None

    #: Set if layer is not visible.
    invisible: typing.Optional[bool] = None

    #: Rectangles scrolling on main thread only.
    scroll_rects: typing.Optional[typing.List[ScrollRect]] = None

    #: Sticky position constraint information
    sticky_position_constraint: typing.Optional[StickyPositionConstraint] = None

    def to_json(self):
        json = dict()
        json['layerId'] = self.layer_id.to_json()
        json['offsetX'] = self.offset_x
        json['offsetY'] = self.offset_y
        json['width'] = self.width
        json['height'] = self.height
        json['paintCount'] = self.paint_count
        json['drawsContent'] = self.draws_content
        if self.parent_layer_id is not None:
            json['parentLayerId'] = self.parent_layer_id.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.transform is not None:
            json['transform'] = [i for i in self.transform]
        if self.anchor_x is not None:
            json['anchorX'] = self.anchor_x
        if self.anchor_y is not None:
            json['anchorY'] = self.anchor_y
        if self.anchor_z is not None:
            json['anchorZ'] = self.anchor_z
        if self.invisible is not None:
            json['invisible'] = self.invisible
        if self.scroll_rects is not None:
            json['scrollRects'] = [i.to_json() for i in self.scroll_rects]
        if self.sticky_position_constraint is not None:
            json['stickyPositionConstraint'] = self.sticky_position_constraint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            offset_x=float(json['offsetX']),
            offset_y=float(json['offsetY']),
            width=float(json['width']),
            height=float(json['height']),
            paint_count=int(json['paintCount']),
            draws_content=bool(json['drawsContent']),
            parent_layer_id=LayerId.from_json(json['parentLayerId']) if 'parentLayerId' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            transform=[float(i) for i in json['transform']] if 'transform' in json else None,
            anchor_x=float(json['anchorX']) if 'anchorX' in json else None,
            anchor_y=float(json['anchorY']) if 'anchorY' in json else None,
            anchor_z=float(json['anchorZ']) if 'anchorZ' in json else None,
            invisible=bool(json['invisible']) if 'invisible' in json else None,
            scroll_rects=[ScrollRect.from_json(i) for i in json['scrollRects']] if 'scrollRects' in json else None,
            sticky_position_constraint=StickyPositionConstraint.from_json(json['stickyPositionConstraint']) if 'stickyPositionConstraint' in json else None,
        )


class PaintProfile(list):
    '''
    Array of timings, one per paint step.
    '''
    def to_json(self) -> typing.List[float]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[float]) -> PaintProfile:
        return cls(json)

    def __repr__(self):
        return 'PaintProfile({})'.format(super().__repr__())


def compositing_reasons(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[str], typing.List[str]]]:
    '''
    Provides the reasons why the given layer was composited.

    :param layer_id: The id of the layer for which we want to get the reasons it was composited.
    :returns: A tuple with the following items:

        0. **compositingReasons** - A list of strings specifying reasons for the given layer to become composited.
        1. **compositingReasonIds** - A list of strings specifying reason IDs for the given layer to become composited.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.compositingReasons',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [str(i) for i in json['compositingReasons']],
        [str(i) for i in json['compositingReasonIds']]
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.enable',
    }
    json = yield cmd_dict


def load_snapshot(
        tiles: typing.List[PictureTile]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the snapshot identifier.

    :param tiles: An array of tiles composing the snapshot.
    :returns: The id of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['tiles'] = [i.to_json() for i in tiles]
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.loadSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def make_snapshot(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the layer snapshot identifier.

    :param layer_id: The id of the layer.
    :returns: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.makeSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def profile_snapshot(
        snapshot_id: SnapshotId,
        min_repeat_count: typing.Optional[int] = None,
        min_duration: typing.Optional[float] = None,
        clip_rect: typing.Optional[dom.Rect] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[PaintProfile]]:
    '''
    :param snapshot_id: The id of the layer snapshot.
    :param min_repeat_count: *(Optional)* The maximum number of times to replay the snapshot (1, if not specified).
    :param min_duration: *(Optional)* The minimum duration (in seconds) to replay the snapshot.
    :param clip_rect: *(Optional)* The clip rectangle to apply when replaying the snapshot.
    :returns: The array of paint profiles, one per run.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if min_repeat_count is not None:
        params['minRepeatCount'] = min_repeat_count
    if min_duration is not None:
        params['minDuration'] = min_duration
    if clip_rect is not None:
        params['clipRect'] = clip_rect.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.profileSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return [PaintProfile.from_json(i) for i in json['timings']]


def release_snapshot(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases layer snapshot captured by the back-end.

    :param snapshot_id: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.releaseSnapshot',
        'params': params,
    }
    json = yield cmd_dict


def replay_snapshot(
        snapshot_id: SnapshotId,
        from_step: typing.Optional[int] = None,
        to_step: typing.Optional[int] = None,
        scale: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Replays the layer snapshot and returns the resulting bitmap.

    :param snapshot_id: The id of the layer snapshot.
    :param from_step: *(Optional)* The first step to replay from (replay from the very start if not specified).
    :param to_step: *(Optional)* The last step to replay to (replay till the end if not specified).
    :param scale: *(Optional)* The scale to apply while replaying (defaults to 1).
    :returns: A data: URL for resulting image.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if from_step is not None:
        params['fromStep'] = from_step
    if to_step is not None:
        params['toStep'] = to_step
    if scale is not None:
        params['scale'] = scale
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.replaySnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['dataURL'])


def snapshot_command_log(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[dict]]:
    '''
    Replays the layer snapshot and returns canvas log.

    :param snapshot_id: The id of the layer snapshot.
    :returns: The array of canvas function calls.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.snapshotCommandLog',
        'params': params,
    }
    json = yield cmd_dict
    return [dict(i) for i in json['commandLog']]


@event_class('LayerTree.layerPainted')
@dataclass
class LayerPainted:
    #: The id of the painted layer.
    layer_id: LayerId
    #: Clip rectangle.
    clip: dom.Rect

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerPainted:
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            clip=dom.Rect.from_json(json['clip'])
        )


@event_class('LayerTree.layerTreeDidChange')
@dataclass
class LayerTreeDidChange:
    #: Layer tree, absent if not in the compositing mode.
    layers: typing.Optional[typing.List[Layer]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerTreeDidChange:
        return cls(
            layers=[Layer.from_json(i) for i in json['layers']] if 'layers' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\layer_tree.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: LayerTree (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom


class LayerId(str):
    '''
    Unique Layer identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> LayerId:
        return cls(json)

    def __repr__(self):
        return 'LayerId({})'.format(super().__repr__())


class SnapshotId(str):
    '''
    Unique snapshot identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SnapshotId:
        return cls(json)

    def __repr__(self):
        return 'SnapshotId({})'.format(super().__repr__())


@dataclass
class ScrollRect:
    '''
    Rectangle where scrolling happens on the main thread.
    '''
    #: Rectangle itself.
    rect: dom.Rect

    #: Reason for rectangle to force scrolling on the main thread
    type_: str

    def to_json(self):
        json = dict()
        json['rect'] = self.rect.to_json()
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rect=dom.Rect.from_json(json['rect']),
            type_=str(json['type']),
        )


@dataclass
class StickyPositionConstraint:
    '''
    Sticky position constraints.
    '''
    #: Layout rectangle of the sticky element before being shifted
    sticky_box_rect: dom.Rect

    #: Layout rectangle of the containing block of the sticky element
    containing_block_rect: dom.Rect

    #: The nearest sticky layer that shifts the sticky box
    nearest_layer_shifting_sticky_box: typing.Optional[LayerId] = None

    #: The nearest sticky layer that shifts the containing block
    nearest_layer_shifting_containing_block: typing.Optional[LayerId] = None

    def to_json(self):
        json = dict()
        json['stickyBoxRect'] = self.sticky_box_rect.to_json()
        json['containingBlockRect'] = self.containing_block_rect.to_json()
        if self.nearest_layer_shifting_sticky_box is not None:
            json['nearestLayerShiftingStickyBox'] = self.nearest_layer_shifting_sticky_box.to_json()
        if self.nearest_layer_shifting_containing_block is not None:
            json['nearestLayerShiftingContainingBlock'] = self.nearest_layer_shifting_containing_block.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            sticky_box_rect=dom.Rect.from_json(json['stickyBoxRect']),
            containing_block_rect=dom.Rect.from_json(json['containingBlockRect']),
            nearest_layer_shifting_sticky_box=LayerId.from_json(json['nearestLayerShiftingStickyBox']) if 'nearestLayerShiftingStickyBox' in json else None,
            nearest_layer_shifting_containing_block=LayerId.from_json(json['nearestLayerShiftingContainingBlock']) if 'nearestLayerShiftingContainingBlock' in json else None,
        )


@dataclass
class PictureTile:
    '''
    Serialized fragment of layer picture along with its offset within the layer.
    '''
    #: Offset from owning layer left boundary
    x: float

    #: Offset from owning layer top boundary
    y: float

    #: Base64-encoded snapshot data.
    picture: str

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['picture'] = self.picture
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            picture=str(json['picture']),
        )


@dataclass
class Layer:
    '''
    Information about a compositing layer.
    '''
    #: The unique id for this layer.
    layer_id: LayerId

    #: Offset from parent layer, X coordinate.
    offset_x: float

    #: Offset from parent layer, Y coordinate.
    offset_y: float

    #: Layer width.
    width: float

    #: Layer height.
    height: float

    #: Indicates how many time this layer has painted.
    paint_count: int

    #: Indicates whether this layer hosts any content, rather than being used for
    #: transform/scrolling purposes only.
    draws_content: bool

    #: The id of parent (not present for root).
    parent_layer_id: typing.Optional[LayerId] = None

    #: The backend id for the node associated with this layer.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Transformation matrix for layer, default is identity matrix
    transform: typing.Optional[typing.List[float]] = None

    #: Transform anchor point X, absent if no transform specified
    anchor_x: typing.Optional[float] = None

    #: Transform anchor point Y, absent if no transform specified
    anchor_y: typing.Optional[float] = None

    #: Transform anchor point Z, absent if no transform specified
    anchor_z: typing.Optional[float] = None

    #: Set if layer is not visible.
    invisible: typing.Optional[bool] = None

    #: Rectangles scrolling on main thread only.
    scroll_rects: typing.Optional[typing.List[ScrollRect]] = None

    #: Sticky position constraint information
    sticky_position_constraint: typing.Optional[StickyPositionConstraint] = None

    def to_json(self):
        json = dict()
        json['layerId'] = self.layer_id.to_json()
        json['offsetX'] = self.offset_x
        json['offsetY'] = self.offset_y
        json['width'] = self.width
        json['height'] = self.height
        json['paintCount'] = self.paint_count
        json['drawsContent'] = self.draws_content
        if self.parent_layer_id is not None:
            json['parentLayerId'] = self.parent_layer_id.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.transform is not None:
            json['transform'] = [i for i in self.transform]
        if self.anchor_x is not None:
            json['anchorX'] = self.anchor_x
        if self.anchor_y is not None:
            json['anchorY'] = self.anchor_y
        if self.anchor_z is not None:
            json['anchorZ'] = self.anchor_z
        if self.invisible is not None:
            json['invisible'] = self.invisible
        if self.scroll_rects is not None:
            json['scrollRects'] = [i.to_json() for i in self.scroll_rects]
        if self.sticky_position_constraint is not None:
            json['stickyPositionConstraint'] = self.sticky_position_constraint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            offset_x=float(json['offsetX']),
            offset_y=float(json['offsetY']),
            width=float(json['width']),
            height=float(json['height']),
            paint_count=int(json['paintCount']),
            draws_content=bool(json['drawsContent']),
            parent_layer_id=LayerId.from_json(json['parentLayerId']) if 'parentLayerId' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            transform=[float(i) for i in json['transform']] if 'transform' in json else None,
            anchor_x=float(json['anchorX']) if 'anchorX' in json else None,
            anchor_y=float(json['anchorY']) if 'anchorY' in json else None,
            anchor_z=float(json['anchorZ']) if 'anchorZ' in json else None,
            invisible=bool(json['invisible']) if 'invisible' in json else None,
            scroll_rects=[ScrollRect.from_json(i) for i in json['scrollRects']] if 'scrollRects' in json else None,
            sticky_position_constraint=StickyPositionConstraint.from_json(json['stickyPositionConstraint']) if 'stickyPositionConstraint' in json else None,
        )


class PaintProfile(list):
    '''
    Array of timings, one per paint step.
    '''
    def to_json(self) -> typing.List[float]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[float]) -> PaintProfile:
        return cls(json)

    def __repr__(self):
        return 'PaintProfile({})'.format(super().__repr__())


def compositing_reasons(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[str], typing.List[str]]]:
    '''
    Provides the reasons why the given layer was composited.

    :param layer_id: The id of the layer for which we want to get the reasons it was composited.
    :returns: A tuple with the following items:

        0. **compositingReasons** - A list of strings specifying reasons for the given layer to become composited.
        1. **compositingReasonIds** - A list of strings specifying reason IDs for the given layer to become composited.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.compositingReasons',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [str(i) for i in json['compositingReasons']],
        [str(i) for i in json['compositingReasonIds']]
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables compositing tree inspection.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.enable',
    }
    json = yield cmd_dict


def load_snapshot(
        tiles: typing.List[PictureTile]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the snapshot identifier.

    :param tiles: An array of tiles composing the snapshot.
    :returns: The id of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['tiles'] = [i.to_json() for i in tiles]
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.loadSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def make_snapshot(
        layer_id: LayerId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SnapshotId]:
    '''
    Returns the layer snapshot identifier.

    :param layer_id: The id of the layer.
    :returns: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['layerId'] = layer_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.makeSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return SnapshotId.from_json(json['snapshotId'])


def profile_snapshot(
        snapshot_id: SnapshotId,
        min_repeat_count: typing.Optional[int] = None,
        min_duration: typing.Optional[float] = None,
        clip_rect: typing.Optional[dom.Rect] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[PaintProfile]]:
    '''
    :param snapshot_id: The id of the layer snapshot.
    :param min_repeat_count: *(Optional)* The maximum number of times to replay the snapshot (1, if not specified).
    :param min_duration: *(Optional)* The minimum duration (in seconds) to replay the snapshot.
    :param clip_rect: *(Optional)* The clip rectangle to apply when replaying the snapshot.
    :returns: The array of paint profiles, one per run.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if min_repeat_count is not None:
        params['minRepeatCount'] = min_repeat_count
    if min_duration is not None:
        params['minDuration'] = min_duration
    if clip_rect is not None:
        params['clipRect'] = clip_rect.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.profileSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return [PaintProfile.from_json(i) for i in json['timings']]


def release_snapshot(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases layer snapshot captured by the back-end.

    :param snapshot_id: The id of the layer snapshot.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.releaseSnapshot',
        'params': params,
    }
    json = yield cmd_dict


def replay_snapshot(
        snapshot_id: SnapshotId,
        from_step: typing.Optional[int] = None,
        to_step: typing.Optional[int] = None,
        scale: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Replays the layer snapshot and returns the resulting bitmap.

    :param snapshot_id: The id of the layer snapshot.
    :param from_step: *(Optional)* The first step to replay from (replay from the very start if not specified).
    :param to_step: *(Optional)* The last step to replay to (replay till the end if not specified).
    :param scale: *(Optional)* The scale to apply while replaying (defaults to 1).
    :returns: A data: URL for resulting image.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    if from_step is not None:
        params['fromStep'] = from_step
    if to_step is not None:
        params['toStep'] = to_step
    if scale is not None:
        params['scale'] = scale
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.replaySnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['dataURL'])


def snapshot_command_log(
        snapshot_id: SnapshotId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[dict]]:
    '''
    Replays the layer snapshot and returns canvas log.

    :param snapshot_id: The id of the layer snapshot.
    :returns: The array of canvas function calls.
    '''
    params: T_JSON_DICT = dict()
    params['snapshotId'] = snapshot_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'LayerTree.snapshotCommandLog',
        'params': params,
    }
    json = yield cmd_dict
    return [dict(i) for i in json['commandLog']]


@event_class('LayerTree.layerPainted')
@dataclass
class LayerPainted:
    #: The id of the painted layer.
    layer_id: LayerId
    #: Clip rectangle.
    clip: dom.Rect

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerPainted:
        return cls(
            layer_id=LayerId.from_json(json['layerId']),
            clip=dom.Rect.from_json(json['clip'])
        )


@event_class('LayerTree.layerTreeDidChange')
@dataclass
class LayerTreeDidChange:
    #: Layer tree, absent if not in the compositing mode.
    layers: typing.Optional[typing.List[Layer]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LayerTreeDidChange:
        return cls(
            layers=[Layer.from_json(i) for i in json['layers']] if 'layers' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\context_i386.py ===
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
CONTEXT structure for i386.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.version import ARCH_I386

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- CONTEXT structures and constants -----------------------------------------

# The following values specify the type of access in the first parameter
# of the exception record when the exception code specifies an access
# violation.
EXCEPTION_READ_FAULT = 0  # exception caused by a read
EXCEPTION_WRITE_FAULT = 1  # exception caused by a write
EXCEPTION_EXECUTE_FAULT = 8  # exception caused by an instruction fetch

CONTEXT_i386 = 0x00010000  # this assumes that i386 and
CONTEXT_i486 = 0x00010000  # i486 have identical context records

CONTEXT_CONTROL = CONTEXT_i386 | long(0x00000001)  # SS:SP, CS:IP, FLAGS, BP
CONTEXT_INTEGER = CONTEXT_i386 | long(0x00000002)  # AX, BX, CX, DX, SI, DI
CONTEXT_SEGMENTS = CONTEXT_i386 | long(0x00000004)  # DS, ES, FS, GS
CONTEXT_FLOATING_POINT = CONTEXT_i386 | long(0x00000008)  # 387 state
CONTEXT_DEBUG_REGISTERS = CONTEXT_i386 | long(0x00000010)  # DB 0-3,6,7
CONTEXT_EXTENDED_REGISTERS = CONTEXT_i386 | long(0x00000020)  # cpu specific extensions

CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS

CONTEXT_ALL = (
    CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS | CONTEXT_FLOATING_POINT | CONTEXT_DEBUG_REGISTERS | CONTEXT_EXTENDED_REGISTERS
)

SIZE_OF_80387_REGISTERS = 80
MAXIMUM_SUPPORTED_EXTENSION = 512


# typedef struct _FLOATING_SAVE_AREA {
#     DWORD   ControlWord;
#     DWORD   StatusWord;
#     DWORD   TagWord;
#     DWORD   ErrorOffset;
#     DWORD   ErrorSelector;
#     DWORD   DataOffset;
#     DWORD   DataSelector;
#     BYTE    RegisterArea[SIZE_OF_80387_REGISTERS];
#     DWORD   Cr0NpxState;
# } FLOATING_SAVE_AREA;
class FLOATING_SAVE_AREA(Structure):
    _pack_ = 1
    _fields_ = [
        ("ControlWord", DWORD),
        ("StatusWord", DWORD),
        ("TagWord", DWORD),
        ("ErrorOffset", DWORD),
        ("ErrorSelector", DWORD),
        ("DataOffset", DWORD),
        ("DataSelector", DWORD),
        ("RegisterArea", BYTE * SIZE_OF_80387_REGISTERS),
        ("Cr0NpxState", DWORD),
    ]

    _integer_members = ("ControlWord", "StatusWord", "TagWord", "ErrorOffset", "ErrorSelector", "DataOffset", "DataSelector", "Cr0NpxState")

    @classmethod
    def from_dict(cls, fsa):
        "Instance a new structure from a Python dictionary."
        fsa = dict(fsa)
        s = cls()
        for key in cls._integer_members:
            setattr(s, key, fsa.get(key))
        ra = fsa.get("RegisterArea", None)
        if ra is not None:
            for index in compat.xrange(0, SIZE_OF_80387_REGISTERS):
                s.RegisterArea[index] = ra[index]
        return s

    def to_dict(self):
        "Convert a structure into a Python dictionary."
        fsa = dict()
        for key in self._integer_members:
            fsa[key] = getattr(self, key)
        ra = [self.RegisterArea[index] for index in compat.xrange(0, SIZE_OF_80387_REGISTERS)]
        ra = tuple(ra)
        fsa["RegisterArea"] = ra
        return fsa


PFLOATING_SAVE_AREA = POINTER(FLOATING_SAVE_AREA)
LPFLOATING_SAVE_AREA = PFLOATING_SAVE_AREA


# typedef struct _CONTEXT {
#     DWORD ContextFlags;
#     DWORD   Dr0;
#     DWORD   Dr1;
#     DWORD   Dr2;
#     DWORD   Dr3;
#     DWORD   Dr6;
#     DWORD   Dr7;
#     FLOATING_SAVE_AREA FloatSave;
#     DWORD   SegGs;
#     DWORD   SegFs;
#     DWORD   SegEs;
#     DWORD   SegDs;
#     DWORD   Edi;
#     DWORD   Esi;
#     DWORD   Ebx;
#     DWORD   Edx;
#     DWORD   Ecx;
#     DWORD   Eax;
#     DWORD   Ebp;
#     DWORD   Eip;
#     DWORD   SegCs;
#     DWORD   EFlags;
#     DWORD   Esp;
#     DWORD   SegSs;
#     BYTE    ExtendedRegisters[MAXIMUM_SUPPORTED_EXTENSION];
# } CONTEXT;
class CONTEXT(Structure):
    arch = ARCH_I386

    _pack_ = 1

    # Context Frame
    #
    #  This frame has a several purposes: 1) it is used as an argument to
    #  NtContinue, 2) is is used to constuct a call frame for APC delivery,
    #  and 3) it is used in the user level thread creation routines.
    #
    #  The layout of the record conforms to a standard call frame.

    _fields_ = [
        # The flags values within this flag control the contents of
        # a CONTEXT record.
        #
        # If the context record is used as an input parameter, then
        # for each portion of the context record controlled by a flag
        # whose value is set, it is assumed that that portion of the
        # context record contains valid context. If the context record
        # is being used to modify a threads context, then only that
        # portion of the threads context will be modified.
        #
        # If the context record is used as an IN OUT parameter to capture
        # the context of a thread, then only those portions of the thread's
        # context corresponding to set flags will be returned.
        #
        # The context record is never used as an OUT only parameter.
        ("ContextFlags", DWORD),
        # This section is specified/returned if CONTEXT_DEBUG_REGISTERS is
        # set in ContextFlags.  Note that CONTEXT_DEBUG_REGISTERS is NOT
        # included in CONTEXT_FULL.
        ("Dr0", DWORD),
        ("Dr1", DWORD),
        ("Dr2", DWORD),
        ("Dr3", DWORD),
        ("Dr6", DWORD),
        ("Dr7", DWORD),
        # This section is specified/returned if the
        # ContextFlags word contains the flag CONTEXT_FLOATING_POINT.
        ("FloatSave", FLOATING_SAVE_AREA),
        # This section is specified/returned if the
        # ContextFlags word contains the flag CONTEXT_SEGMENTS.
        ("SegGs", DWORD),
        ("SegFs", DWORD),
        ("SegEs", DWORD),
        ("SegDs", DWORD),
        # This section is specified/returned if the
        # ContextFlags word contains the flag CONTEXT_INTEGER.
        ("Edi", DWORD),
        ("Esi", DWORD),
        ("Ebx", DWORD),
        ("Edx", DWORD),
        ("Ecx", DWORD),
        ("Eax", DWORD),
        # This section is specified/returned if the
        # ContextFlags word contains the flag CONTEXT_CONTROL.
        ("Ebp", DWORD),
        ("Eip", DWORD),
        ("SegCs", DWORD),  # MUST BE SANITIZED
        ("EFlags", DWORD),  # MUST BE SANITIZED
        ("Esp", DWORD),
        ("SegSs", DWORD),
        # This section is specified/returned if the ContextFlags word
        # contains the flag CONTEXT_EXTENDED_REGISTERS.
        # The format and contexts are processor specific.
        ("ExtendedRegisters", BYTE * MAXIMUM_SUPPORTED_EXTENSION),
    ]

    _ctx_debug = ("Dr0", "Dr1", "Dr2", "Dr3", "Dr6", "Dr7")
    _ctx_segs = (
        "SegGs",
        "SegFs",
        "SegEs",
        "SegDs",
    )
    _ctx_int = ("Edi", "Esi", "Ebx", "Edx", "Ecx", "Eax")
    _ctx_ctrl = ("Ebp", "Eip", "SegCs", "EFlags", "Esp", "SegSs")

    @classmethod
    def from_dict(cls, ctx):
        "Instance a new structure from a Python dictionary."
        ctx = Context(ctx)
        s = cls()
        ContextFlags = ctx["ContextFlags"]
        setattr(s, "ContextFlags", ContextFlags)
        if (ContextFlags & CONTEXT_DEBUG_REGISTERS) == CONTEXT_DEBUG_REGISTERS:
            for key in s._ctx_debug:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_FLOATING_POINT) == CONTEXT_FLOATING_POINT:
            fsa = ctx["FloatSave"]
            s.FloatSave = FLOATING_SAVE_AREA.from_dict(fsa)
        if (ContextFlags & CONTEXT_SEGMENTS) == CONTEXT_SEGMENTS:
            for key in s._ctx_segs:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_INTEGER) == CONTEXT_INTEGER:
            for key in s._ctx_int:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_CONTROL) == CONTEXT_CONTROL:
            for key in s._ctx_ctrl:
                setattr(s, key, ctx[key])
        if (ContextFlags & CONTEXT_EXTENDED_REGISTERS) == CONTEXT_EXTENDED_REGISTERS:
            er = ctx["ExtendedRegisters"]
            for index in compat.xrange(0, MAXIMUM_SUPPORTED_EXTENSION):
                s.ExtendedRegisters[index] = er[index]
        return s

    def to_dict(self):
        "Convert a structure into a Python native type."
        ctx = Context()
        ContextFlags = self.ContextFlags
        ctx["ContextFlags"] = ContextFlags
        if (ContextFlags & CONTEXT_DEBUG_REGISTERS) == CONTEXT_DEBUG_REGISTERS:
            for key in self._ctx_debug:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_FLOATING_POINT) == CONTEXT_FLOATING_POINT:
            ctx["FloatSave"] = self.FloatSave.to_dict()
        if (ContextFlags & CONTEXT_SEGMENTS) == CONTEXT_SEGMENTS:
            for key in self._ctx_segs:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_INTEGER) == CONTEXT_INTEGER:
            for key in self._ctx_int:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_CONTROL) == CONTEXT_CONTROL:
            for key in self._ctx_ctrl:
                ctx[key] = getattr(self, key)
        if (ContextFlags & CONTEXT_EXTENDED_REGISTERS) == CONTEXT_EXTENDED_REGISTERS:
            er = [self.ExtendedRegisters[index] for index in compat.xrange(0, MAXIMUM_SUPPORTED_EXTENSION)]
            er = tuple(er)
            ctx["ExtendedRegisters"] = er
        return ctx


PCONTEXT = POINTER(CONTEXT)
LPCONTEXT = PCONTEXT


class Context(dict):
    """
    Register context dictionary for the i386 architecture.
    """

    arch = CONTEXT.arch

    def __get_pc(self):
        return self["Eip"]

    def __set_pc(self, value):
        self["Eip"] = value

    pc = property(__get_pc, __set_pc)

    def __get_sp(self):
        return self["Esp"]

    def __set_sp(self, value):
        self["Esp"] = value

    sp = property(__get_sp, __set_sp)

    def __get_fp(self):
        return self["Ebp"]

    def __set_fp(self, value):
        self["Ebp"] = value

    fp = property(__get_fp, __set_fp)


# --- LDT_ENTRY structure ------------------------------------------------------

# typedef struct _LDT_ENTRY {
#   WORD LimitLow;
#   WORD BaseLow;
#   union {
#     struct {
#       BYTE BaseMid;
#       BYTE Flags1;
#       BYTE Flags2;
#       BYTE BaseHi;
#     } Bytes;
#     struct {
#       DWORD BaseMid  :8;
#       DWORD Type  :5;
#       DWORD Dpl  :2;
#       DWORD Pres  :1;
#       DWORD LimitHi  :4;
#       DWORD Sys  :1;
#       DWORD Reserved_0  :1;
#       DWORD Default_Big  :1;
#       DWORD Granularity  :1;
#       DWORD BaseHi  :8;
#     } Bits;
#   } HighWord;
# } LDT_ENTRY,
#  *PLDT_ENTRY;


class _LDT_ENTRY_BYTES_(Structure):
    _pack_ = 1
    _fields_ = [
        ("BaseMid", BYTE),
        ("Flags1", BYTE),
        ("Flags2", BYTE),
        ("BaseHi", BYTE),
    ]


class _LDT_ENTRY_BITS_(Structure):
    _pack_ = 1
    _fields_ = [
        ("BaseMid", DWORD, 8),
        ("Type", DWORD, 5),
        ("Dpl", DWORD, 2),
        ("Pres", DWORD, 1),
        ("LimitHi", DWORD, 4),
        ("Sys", DWORD, 1),
        ("Reserved_0", DWORD, 1),
        ("Default_Big", DWORD, 1),
        ("Granularity", DWORD, 1),
        ("BaseHi", DWORD, 8),
    ]


class _LDT_ENTRY_HIGHWORD_(Union):
    _pack_ = 1
    _fields_ = [
        ("Bytes", _LDT_ENTRY_BYTES_),
        ("Bits", _LDT_ENTRY_BITS_),
    ]


class LDT_ENTRY(Structure):
    _pack_ = 1
    _fields_ = [
        ("LimitLow", WORD),
        ("BaseLow", WORD),
        ("HighWord", _LDT_ENTRY_HIGHWORD_),
    ]


PLDT_ENTRY = POINTER(LDT_ENTRY)
LPLDT_ENTRY = PLDT_ENTRY

###############################################################################


# BOOL WINAPI GetThreadSelectorEntry(
#   __in   HANDLE hThread,
#   __in   DWORD dwSelector,
#   __out  LPLDT_ENTRY lpSelectorEntry
# );
def GetThreadSelectorEntry(hThread, dwSelector):
    _GetThreadSelectorEntry = windll.kernel32.GetThreadSelectorEntry
    _GetThreadSelectorEntry.argtypes = [HANDLE, DWORD, LPLDT_ENTRY]
    _GetThreadSelectorEntry.restype = bool
    _GetThreadSelectorEntry.errcheck = RaiseIfZero

    ldt = LDT_ENTRY()
    _GetThreadSelectorEntry(hThread, dwSelector, byref(ldt))
    return ldt


# BOOL WINAPI GetThreadContext(
#   __in     HANDLE hThread,
#   __inout  LPCONTEXT lpContext
# );
def GetThreadContext(hThread, ContextFlags=None, raw=False):
    _GetThreadContext = windll.kernel32.GetThreadContext
    _GetThreadContext.argtypes = [HANDLE, LPCONTEXT]
    _GetThreadContext.restype = bool
    _GetThreadContext.errcheck = RaiseIfZero

    if ContextFlags is None:
        ContextFlags = CONTEXT_ALL | CONTEXT_i386
    Context = CONTEXT()
    Context.ContextFlags = ContextFlags
    _GetThreadContext(hThread, byref(Context))
    if raw:
        return Context
    return Context.to_dict()


# BOOL WINAPI SetThreadContext(
#   __in  HANDLE hThread,
#   __in  const CONTEXT* lpContext
# );
def SetThreadContext(hThread, lpContext):
    _SetThreadContext = windll.kernel32.SetThreadContext
    _SetThreadContext.argtypes = [HANDLE, LPCONTEXT]
    _SetThreadContext.restype = bool
    _SetThreadContext.errcheck = RaiseIfZero

    if isinstance(lpContext, dict):
        lpContext = CONTEXT.from_dict(lpContext)
    _SetThreadContext(hThread, byref(lpContext))


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\function.py ===
from parso.python import tree

from jedi import debug
from jedi.inference.cache import inference_state_method_cache, CachedMetaClass
from jedi.inference import compiled
from jedi.inference import recursion
from jedi.inference import docstrings
from jedi.inference import flow_analysis
from jedi.inference.signature import TreeSignature
from jedi.inference.filters import ParserTreeFilter, FunctionExecutionFilter, \
    AnonymousFunctionExecutionFilter
from jedi.inference.names import ValueName, AbstractNameDefinition, \
    AnonymousParamName, ParamName, NameWrapper
from jedi.inference.base_value import ContextualizedNode, NO_VALUES, \
    ValueSet, TreeValue, ValueWrapper
from jedi.inference.lazy_value import LazyKnownValues, LazyKnownValue, \
    LazyTreeValue
from jedi.inference.context import ValueContext, TreeContextMixin
from jedi.inference.value import iterable
from jedi import parser_utils
from jedi.inference.parser_cache import get_yield_exprs
from jedi.inference.helpers import values_from_qualified_names
from jedi.inference.gradual.generics import TupleGenericManager


class LambdaName(AbstractNameDefinition):
    string_name = '<lambda>'
    api_type = 'function'

    def __init__(self, lambda_value):
        self._lambda_value = lambda_value
        self.parent_context = lambda_value.parent_context

    @property
    def start_pos(self):
        return self._lambda_value.tree_node.start_pos

    def infer(self):
        return ValueSet([self._lambda_value])


class FunctionAndClassBase(TreeValue):
    def get_qualified_names(self):
        if self.parent_context.is_class():
            n = self.parent_context.get_qualified_names()
            if n is None:
                # This means that the parent class lives within a function.
                return None
            return n + (self.py__name__(),)
        elif self.parent_context.is_module():
            return (self.py__name__(),)
        else:
            return None


class FunctionMixin:
    api_type = 'function'

    def get_filters(self, origin_scope=None):
        cls = self.py__class__()
        for instance in cls.execute_with_values():
            yield from instance.get_filters(origin_scope=origin_scope)

    def py__get__(self, instance, class_value):
        from jedi.inference.value.instance import BoundMethod
        if instance is None:
            # Calling the Foo.bar results in the original bar function.
            return ValueSet([self])
        return ValueSet([BoundMethod(instance, class_value.as_context(), self)])

    def get_param_names(self):
        return [AnonymousParamName(self, param.name)
                for param in self.tree_node.get_params()]

    @property
    def name(self):
        if self.tree_node.type == 'lambdef':
            return LambdaName(self)
        return ValueName(self, self.tree_node.name)

    def is_function(self):
        return True

    def py__name__(self):
        return self.name.string_name

    def get_type_hint(self, add_class_info=True):
        return_annotation = self.tree_node.annotation
        if return_annotation is None:
            def param_name_to_str(n):
                s = n.string_name
                annotation = n.infer().get_type_hint()
                if annotation is not None:
                    s += ': ' + annotation
                if n.default_node is not None:
                    s += '=' + n.default_node.get_code(include_prefix=False)
                return s

            function_execution = self.as_context()
            result = function_execution.infer()
            return_hint = result.get_type_hint()
            body = self.py__name__() + '(%s)' % ', '.join([
                param_name_to_str(n)
                for n in function_execution.get_param_names()
            ])
            if return_hint is None:
                return body
        else:
            return_hint = return_annotation.get_code(include_prefix=False)
            body = self.py__name__() + self.tree_node.children[2].get_code(include_prefix=False)

        return body + ' -> ' + return_hint

    def py__call__(self, arguments):
        function_execution = self.as_context(arguments)
        return function_execution.infer()

    def _as_context(self, arguments=None):
        if arguments is None:
            return AnonymousFunctionExecution(self)
        return FunctionExecutionContext(self, arguments)

    def get_signatures(self):
        return [TreeSignature(f) for f in self.get_signature_functions()]


class FunctionValue(FunctionMixin, FunctionAndClassBase, metaclass=CachedMetaClass):
    @classmethod
    def from_context(cls, context, tree_node):
        def create(tree_node):
            if context.is_class():
                return MethodValue(
                    context.inference_state,
                    context,
                    parent_context=parent_context,
                    tree_node=tree_node
                )
            else:
                return cls(
                    context.inference_state,
                    parent_context=parent_context,
                    tree_node=tree_node
                )

        overloaded_funcs = list(_find_overload_functions(context, tree_node))

        parent_context = context
        while parent_context.is_class() or parent_context.is_instance():
            parent_context = parent_context.parent_context

        function = create(tree_node)

        if overloaded_funcs:
            return OverloadedFunctionValue(
                function,
                # Get them into the correct order: lower line first.
                list(reversed([create(f) for f in overloaded_funcs]))
            )
        return function

    def py__class__(self):
        c, = values_from_qualified_names(self.inference_state, 'types', 'FunctionType')
        return c

    def get_default_param_context(self):
        return self.parent_context

    def get_signature_functions(self):
        return [self]


class FunctionNameInClass(NameWrapper):
    def __init__(self, class_context, name):
        super().__init__(name)
        self._class_context = class_context

    def get_defining_qualified_value(self):
        return self._class_context.get_value()  # Might be None.


class MethodValue(FunctionValue):
    def __init__(self, inference_state, class_context, *args, **kwargs):
        super().__init__(inference_state, *args, **kwargs)
        self.class_context = class_context

    def get_default_param_context(self):
        return self.class_context

    def get_qualified_names(self):
        # Need to implement this, because the parent value of a method
        # value is not the class value but the module.
        names = self.class_context.get_qualified_names()
        if names is None:
            return None
        return names + (self.py__name__(),)

    @property
    def name(self):
        return FunctionNameInClass(self.class_context, super().name)


class BaseFunctionExecutionContext(ValueContext, TreeContextMixin):
    def infer_annotations(self):
        raise NotImplementedError

    @inference_state_method_cache(default=NO_VALUES)
    @recursion.execution_recursion_decorator()
    def get_return_values(self, check_yields=False):
        funcdef = self.tree_node
        if funcdef.type == 'lambdef':
            return self.infer_node(funcdef.children[-1])

        if check_yields:
            value_set = NO_VALUES
            returns = get_yield_exprs(self.inference_state, funcdef)
        else:
            value_set = self.infer_annotations()
            if value_set:
                # If there are annotations, prefer them over anything else.
                # This will make it faster.
                return value_set
            value_set |= docstrings.infer_return_types(self._value)
            returns = funcdef.iter_return_stmts()

        for r in returns:
            if check_yields:
                value_set |= ValueSet.from_sets(
                    lazy_value.infer()
                    for lazy_value in self._get_yield_lazy_value(r)
                )
            else:
                check = flow_analysis.reachability_check(self, funcdef, r)
                if check is flow_analysis.UNREACHABLE:
                    debug.dbg('Return unreachable: %s', r)
                else:
                    try:
                        children = r.children
                    except AttributeError:
                        ctx = compiled.builtin_from_name(self.inference_state, 'None')
                        value_set |= ValueSet([ctx])
                    else:
                        value_set |= self.infer_node(children[1])
                if check is flow_analysis.REACHABLE:
                    debug.dbg('Return reachable: %s', r)
                    break
        return value_set

    def _get_yield_lazy_value(self, yield_expr):
        if yield_expr.type == 'keyword':
            # `yield` just yields None.
            ctx = compiled.builtin_from_name(self.inference_state, 'None')
            yield LazyKnownValue(ctx)
            return

        node = yield_expr.children[1]
        if node.type == 'yield_arg':  # It must be a yield from.
            cn = ContextualizedNode(self, node.children[1])
            yield from cn.infer().iterate(cn)
        else:
            yield LazyTreeValue(self, node)

    @recursion.execution_recursion_decorator(default=iter([]))
    def get_yield_lazy_values(self, is_async=False):
        # TODO: if is_async, wrap yield statements in Awaitable/async_generator_asend
        for_parents = [(y, tree.search_ancestor(y, 'for_stmt', 'funcdef',
                                                'while_stmt', 'if_stmt'))
                       for y in get_yield_exprs(self.inference_state, self.tree_node)]

        # Calculate if the yields are placed within the same for loop.
        yields_order = []
        last_for_stmt = None
        for yield_, for_stmt in for_parents:
            # For really simple for loops we can predict the order. Otherwise
            # we just ignore it.
            parent = for_stmt.parent
            if parent.type == 'suite':
                parent = parent.parent
            if for_stmt.type == 'for_stmt' and parent == self.tree_node \
                    and parser_utils.for_stmt_defines_one_name(for_stmt):  # Simplicity for now.
                if for_stmt == last_for_stmt:
                    yields_order[-1][1].append(yield_)
                else:
                    yields_order.append((for_stmt, [yield_]))
            elif for_stmt == self.tree_node:
                yields_order.append((None, [yield_]))
            else:
                types = self.get_return_values(check_yields=True)
                if types:
                    yield LazyKnownValues(types, min=0, max=float('inf'))
                return
            last_for_stmt = for_stmt

        for for_stmt, yields in yields_order:
            if for_stmt is None:
                # No for_stmt, just normal yields.
                for yield_ in yields:
                    yield from self._get_yield_lazy_value(yield_)
            else:
                input_node = for_stmt.get_testlist()
                cn = ContextualizedNode(self, input_node)
                ordered = cn.infer().iterate(cn)
                ordered = list(ordered)
                for lazy_value in ordered:
                    dct = {str(for_stmt.children[1].value): lazy_value.infer()}
                    with self.predefine_names(for_stmt, dct):
                        for yield_in_same_for_stmt in yields:
                            yield from self._get_yield_lazy_value(yield_in_same_for_stmt)

    def merge_yield_values(self, is_async=False):
        return ValueSet.from_sets(
            lazy_value.infer()
            for lazy_value in self.get_yield_lazy_values()
        )

    def is_generator(self):
        return bool(get_yield_exprs(self.inference_state, self.tree_node))

    def infer(self):
        """
        Created to be used by inheritance.
        """
        inference_state = self.inference_state
        is_coroutine = self.tree_node.parent.type in ('async_stmt', 'async_funcdef')
        from jedi.inference.gradual.base import GenericClass

        if is_coroutine:
            if self.is_generator():
                async_generator_classes = inference_state.typing_module \
                    .py__getattribute__('AsyncGenerator')

                yield_values = self.merge_yield_values(is_async=True)
                # The contravariant doesn't seem to be defined.
                generics = (yield_values.py__class__(), NO_VALUES)
                return ValueSet(
                    GenericClass(c, TupleGenericManager(generics))
                    for c in async_generator_classes
                ).execute_annotation()
            else:
                async_classes = inference_state.typing_module.py__getattribute__('Coroutine')
                return_values = self.get_return_values()
                # Only the first generic is relevant.
                generics = (return_values.py__class__(), NO_VALUES, NO_VALUES)
                return ValueSet(
                    GenericClass(c, TupleGenericManager(generics)) for c in async_classes
                ).execute_annotation()
        else:
            # If there are annotations, prefer them over anything else.
            if self.is_generator() and not self.infer_annotations():
                return ValueSet([iterable.Generator(inference_state, self)])
            else:
                return self.get_return_values()


class FunctionExecutionContext(BaseFunctionExecutionContext):
    def __init__(self, function_value, arguments):
        super().__init__(function_value)
        self._arguments = arguments

    def get_filters(self, until_position=None, origin_scope=None):
        yield FunctionExecutionFilter(
            self, self._value,
            until_position=until_position,
            origin_scope=origin_scope,
            arguments=self._arguments
        )

    def infer_annotations(self):
        from jedi.inference.gradual.annotation import infer_return_types
        return infer_return_types(self._value, self._arguments)

    def get_param_names(self):
        return [
            ParamName(self._value, param.name, self._arguments)
            for param in self._value.tree_node.get_params()
        ]


class AnonymousFunctionExecution(BaseFunctionExecutionContext):
    def infer_annotations(self):
        # I don't think inferring anonymous executions is a big thing.
        # Anonymous contexts are mostly there for the user to work in. ~ dave
        return NO_VALUES

    def get_filters(self, until_position=None, origin_scope=None):
        yield AnonymousFunctionExecutionFilter(
            self, self._value,
            until_position=until_position,
            origin_scope=origin_scope,
        )

    def get_param_names(self):
        return self._value.get_param_names()


class OverloadedFunctionValue(FunctionMixin, ValueWrapper):
    def __init__(self, function, overloaded_functions):
        super().__init__(function)
        self._overloaded_functions = overloaded_functions

    def py__call__(self, arguments):
        debug.dbg("Execute overloaded function %s", self._wrapped_value, color='BLUE')
        function_executions = []
        for signature in self.get_signatures():
            function_execution = signature.value.as_context(arguments)
            function_executions.append(function_execution)
            if signature.matches_signature(arguments):
                return function_execution.infer()

        if self.inference_state.is_analysis:
            # In this case we want precision.
            return NO_VALUES
        return ValueSet.from_sets(fe.infer() for fe in function_executions)

    def get_signature_functions(self):
        return self._overloaded_functions

    def get_type_hint(self, add_class_info=True):
        return 'Union[%s]' % ', '.join(f.get_type_hint() for f in self._overloaded_functions)


def _find_overload_functions(context, tree_node):
    def _is_overload_decorated(funcdef):
        if funcdef.parent.type == 'decorated':
            decorators = funcdef.parent.children[0]
            if decorators.type == 'decorator':
                decorators = [decorators]
            else:
                decorators = decorators.children
            for decorator in decorators:
                dotted_name = decorator.children[1]
                if dotted_name.type == 'name' and dotted_name.value == 'overload':
                    # TODO check with values if it's the right overload
                    return True
        return False

    if tree_node.type == 'lambdef':
        return

    if _is_overload_decorated(tree_node):
        yield tree_node

    while True:
        filter = ParserTreeFilter(
            context,
            until_position=tree_node.start_pos
        )
        names = filter.get(tree_node.name.value)
        assert isinstance(names, list)
        if not names:
            break

        found = False
        for name in names:
            funcdef = name.tree_name.parent
            if funcdef.type == 'funcdef' and _is_overload_decorated(funcdef):
                tree_node = funcdef
                found = True
                yield funcdef

        if not found:
            break

# === NexusCore/openenv\Lib\site-packages\fontTools\tfmLib.py ===
"""Module for reading TFM (TeX Font Metrics) files.

The TFM format is described in the TFtoPL WEB source code, whose typeset form
can be found on `CTAN <http://mirrors.ctan.org/info/knuth-pdf/texware/tftopl.pdf>`_.

	>>> from fontTools.tfmLib import TFM
	>>> tfm = TFM("Tests/tfmLib/data/cmr10.tfm")
	>>>
	>>> # Accessing an attribute gets you metadata.
	>>> tfm.checksum
	1274110073
	>>> tfm.designsize
	10.0
	>>> tfm.codingscheme
	'TeX text'
	>>> tfm.family
	'CMR'
	>>> tfm.seven_bit_safe_flag
	False
	>>> tfm.face
	234
	>>> tfm.extraheader
	{}
	>>> tfm.fontdimens
	{'SLANT': 0.0, 'SPACE': 0.33333396911621094, 'STRETCH': 0.16666698455810547, 'SHRINK': 0.11111164093017578, 'XHEIGHT': 0.4305553436279297, 'QUAD': 1.0000028610229492, 'EXTRASPACE': 0.11111164093017578}
	>>> # Accessing a character gets you its metrics.
	>>> # “width” is always available, other metrics are available only when
	>>> # applicable. All values are relative to “designsize”.
	>>> tfm.chars[ord("g")]
	{'width': 0.5000019073486328, 'height': 0.4305553436279297, 'depth': 0.1944446563720703, 'italic': 0.013888359069824219}
	>>> # Kerning and ligature can be accessed as well.
	>>> tfm.kerning[ord("c")]
	{104: -0.02777862548828125, 107: -0.02777862548828125}
	>>> tfm.ligatures[ord("f")]
	{105: ('LIG', 12), 102: ('LIG', 11), 108: ('LIG', 13)}
"""

from types import SimpleNamespace

from fontTools.misc.sstruct import calcsize, unpack, unpack2

SIZES_FORMAT = """
    >
    lf: h    # length of the entire file, in words
    lh: h    # length of the header data, in words
    bc: h    # smallest character code in the font
    ec: h    # largest character code in the font
    nw: h    # number of words in the width table
    nh: h    # number of words in the height table
    nd: h    # number of words in the depth table
    ni: h    # number of words in the italic correction table
    nl: h    # number of words in the ligature/kern table
    nk: h    # number of words in the kern table
    ne: h    # number of words in the extensible character table
    np: h    # number of font parameter words
"""

SIZES_SIZE = calcsize(SIZES_FORMAT)

FIXED_FORMAT = "12.20F"

HEADER_FORMAT1 = f"""
    >
    checksum:            L
    designsize:          {FIXED_FORMAT}
"""

HEADER_FORMAT2 = f"""
    {HEADER_FORMAT1}
    codingscheme:        40p
"""

HEADER_FORMAT3 = f"""
    {HEADER_FORMAT2}
    family:              20p
"""

HEADER_FORMAT4 = f"""
    {HEADER_FORMAT3}
    seven_bit_safe_flag: ?
    ignored:             x
    ignored:             x
    face:                B
"""

HEADER_SIZE1 = calcsize(HEADER_FORMAT1)
HEADER_SIZE2 = calcsize(HEADER_FORMAT2)
HEADER_SIZE3 = calcsize(HEADER_FORMAT3)
HEADER_SIZE4 = calcsize(HEADER_FORMAT4)

LIG_KERN_COMMAND = """
    >
    skip_byte: B
    next_char: B
    op_byte: B
    remainder: B
"""

BASE_PARAMS = [
    "SLANT",
    "SPACE",
    "STRETCH",
    "SHRINK",
    "XHEIGHT",
    "QUAD",
    "EXTRASPACE",
]

MATHSY_PARAMS = [
    "NUM1",
    "NUM2",
    "NUM3",
    "DENOM1",
    "DENOM2",
    "SUP1",
    "SUP2",
    "SUP3",
    "SUB1",
    "SUB2",
    "SUPDROP",
    "SUBDROP",
    "DELIM1",
    "DELIM2",
    "AXISHEIGHT",
]

MATHEX_PARAMS = [
    "DEFAULTRULETHICKNESS",
    "BIGOPSPACING1",
    "BIGOPSPACING2",
    "BIGOPSPACING3",
    "BIGOPSPACING4",
    "BIGOPSPACING5",
]

VANILLA = 0
MATHSY = 1
MATHEX = 2

UNREACHABLE = 0
PASSTHROUGH = 1
ACCESSABLE = 2

NO_TAG = 0
LIG_TAG = 1
LIST_TAG = 2
EXT_TAG = 3

STOP_FLAG = 128
KERN_FLAG = 128


class TFMException(Exception):
    def __init__(self, message):
        super().__init__(message)


class TFM:
    def __init__(self, file):
        self._read(file)

    def __repr__(self):
        return (
            f"<TFM"
            f" for {self.family}"
            f" in {self.codingscheme}"
            f" at {self.designsize:g}pt>"
        )

    def _read(self, file):
        if hasattr(file, "read"):
            data = file.read()
        else:
            with open(file, "rb") as fp:
                data = fp.read()

        self._data = data

        if len(data) < SIZES_SIZE:
            raise TFMException("Too short input file")

        sizes = SimpleNamespace()
        unpack2(SIZES_FORMAT, data, sizes)

        # Do some file structure sanity checks.
        # TeX and TFtoPL do additional functional checks and might even correct
        # “errors” in the input file, but we instead try to output the file as
        # it is as long as it is parsable, even if the data make no sense.

        if sizes.lf < 0:
            raise TFMException("The file claims to have negative or zero length!")

        if len(data) < sizes.lf * 4:
            raise TFMException("The file has fewer bytes than it claims!")

        for name, length in vars(sizes).items():
            if length < 0:
                raise TFMException("The subfile size: '{name}' is negative!")

        if sizes.lh < 2:
            raise TFMException(f"The header length is only {sizes.lh}!")

        if sizes.bc > sizes.ec + 1 or sizes.ec > 255:
            raise TFMException(
                f"The character code range {sizes.bc}..{sizes.ec} is illegal!"
            )

        if sizes.nw == 0 or sizes.nh == 0 or sizes.nd == 0 or sizes.ni == 0:
            raise TFMException("Incomplete subfiles for character dimensions!")

        if sizes.ne > 256:
            raise TFMException(f"There are {ne} extensible recipes!")

        if sizes.lf != (
            6
            + sizes.lh
            + (sizes.ec - sizes.bc + 1)
            + sizes.nw
            + sizes.nh
            + sizes.nd
            + sizes.ni
            + sizes.nl
            + sizes.nk
            + sizes.ne
            + sizes.np
        ):
            raise TFMException("Subfile sizes don’t add up to the stated total")

        # Subfile offsets, used in the helper function below. These all are
        # 32-bit word offsets not 8-bit byte offsets.
        char_base = 6 + sizes.lh - sizes.bc
        width_base = char_base + sizes.ec + 1
        height_base = width_base + sizes.nw
        depth_base = height_base + sizes.nh
        italic_base = depth_base + sizes.nd
        lig_kern_base = italic_base + sizes.ni
        kern_base = lig_kern_base + sizes.nl
        exten_base = kern_base + sizes.nk
        param_base = exten_base + sizes.ne

        # Helper functions for accessing individual data. If this looks
        # nonidiomatic Python, I blame the effect of reading the literate WEB
        # documentation of TFtoPL.
        def char_info(c):
            return 4 * (char_base + c)

        def width_index(c):
            return data[char_info(c)]

        def noneexistent(c):
            return c < sizes.bc or c > sizes.ec or width_index(c) == 0

        def height_index(c):
            return data[char_info(c) + 1] // 16

        def depth_index(c):
            return data[char_info(c) + 1] % 16

        def italic_index(c):
            return data[char_info(c) + 2] // 4

        def tag(c):
            return data[char_info(c) + 2] % 4

        def remainder(c):
            return data[char_info(c) + 3]

        def width(c):
            r = 4 * (width_base + width_index(c))
            return read_fixed(r, "v")["v"]

        def height(c):
            r = 4 * (height_base + height_index(c))
            return read_fixed(r, "v")["v"]

        def depth(c):
            r = 4 * (depth_base + depth_index(c))
            return read_fixed(r, "v")["v"]

        def italic(c):
            r = 4 * (italic_base + italic_index(c))
            return read_fixed(r, "v")["v"]

        def exten(c):
            return 4 * (exten_base + remainder(c))

        def lig_step(i):
            return 4 * (lig_kern_base + i)

        def lig_kern_command(i):
            command = SimpleNamespace()
            unpack2(LIG_KERN_COMMAND, data[i:], command)
            return command

        def kern(i):
            r = 4 * (kern_base + i)
            return read_fixed(r, "v")["v"]

        def param(i):
            return 4 * (param_base + i)

        def read_fixed(index, key, obj=None):
            ret = unpack2(f">;{key}:{FIXED_FORMAT}", data[index:], obj)
            return ret[0]

        # Set all attributes to empty values regardless of the header size.
        unpack(HEADER_FORMAT4, [0] * HEADER_SIZE4, self)

        offset = 24
        length = sizes.lh * 4
        self.extraheader = {}
        if length >= HEADER_SIZE4:
            rest = unpack2(HEADER_FORMAT4, data[offset:], self)[1]
            if self.face < 18:
                s = self.face % 2
                b = self.face // 2
                self.face = "MBL"[b % 3] + "RI"[s] + "RCE"[b // 3]
            for i in range(sizes.lh - HEADER_SIZE4 // 4):
                rest = unpack2(f">;HEADER{i + 18}:l", rest, self.extraheader)[1]
        elif length >= HEADER_SIZE3:
            unpack2(HEADER_FORMAT3, data[offset:], self)
        elif length >= HEADER_SIZE2:
            unpack2(HEADER_FORMAT2, data[offset:], self)
        elif length >= HEADER_SIZE1:
            unpack2(HEADER_FORMAT1, data[offset:], self)

        self.fonttype = VANILLA
        scheme = self.codingscheme.upper()
        if scheme.startswith("TEX MATH SY"):
            self.fonttype = MATHSY
        elif scheme.startswith("TEX MATH EX"):
            self.fonttype = MATHEX

        self.fontdimens = {}
        for i in range(sizes.np):
            name = f"PARAMETER{i+1}"
            if i <= 6:
                name = BASE_PARAMS[i]
            elif self.fonttype == MATHSY and i <= 21:
                name = MATHSY_PARAMS[i - 7]
            elif self.fonttype == MATHEX and i <= 12:
                name = MATHEX_PARAMS[i - 7]
            read_fixed(param(i), name, self.fontdimens)

        lig_kern_map = {}
        self.right_boundary_char = None
        self.left_boundary_char = None
        if sizes.nl > 0:
            cmd = lig_kern_command(lig_step(0))
            if cmd.skip_byte == 255:
                self.right_boundary_char = cmd.next_char

            cmd = lig_kern_command(lig_step((sizes.nl - 1)))
            if cmd.skip_byte == 255:
                self.left_boundary_char = 256
                r = 256 * cmd.op_byte + cmd.remainder
                lig_kern_map[self.left_boundary_char] = r

        self.chars = {}
        for c in range(sizes.bc, sizes.ec + 1):
            if width_index(c) > 0:
                self.chars[c] = info = {}
                info["width"] = width(c)
                if height_index(c) > 0:
                    info["height"] = height(c)
                if depth_index(c) > 0:
                    info["depth"] = depth(c)
                if italic_index(c) > 0:
                    info["italic"] = italic(c)
                char_tag = tag(c)
                if char_tag == NO_TAG:
                    pass
                elif char_tag == LIG_TAG:
                    lig_kern_map[c] = remainder(c)
                elif char_tag == LIST_TAG:
                    info["nextlarger"] = remainder(c)
                elif char_tag == EXT_TAG:
                    info["varchar"] = varchar = {}
                    for i in range(4):
                        part = data[exten(c) + i]
                        if i == 3 or part > 0:
                            name = "rep"
                            if i == 0:
                                name = "top"
                            elif i == 1:
                                name = "mid"
                            elif i == 2:
                                name = "bot"
                            if noneexistent(part):
                                varchar[name] = c
                            else:
                                varchar[name] = part

        self.ligatures = {}
        self.kerning = {}
        for c, i in sorted(lig_kern_map.items()):
            cmd = lig_kern_command(lig_step(i))
            if cmd.skip_byte > STOP_FLAG:
                i = 256 * cmd.op_byte + cmd.remainder

            while i < sizes.nl:
                cmd = lig_kern_command(lig_step(i))
                if cmd.skip_byte > STOP_FLAG:
                    pass
                else:
                    if cmd.op_byte >= KERN_FLAG:
                        r = 256 * (cmd.op_byte - KERN_FLAG) + cmd.remainder
                        self.kerning.setdefault(c, {})[cmd.next_char] = kern(r)
                    else:
                        r = cmd.op_byte
                        if r == 4 or (r > 7 and r != 11):
                            # Ligature step with nonstandard code, we output
                            # the code verbatim.
                            lig = r
                        else:
                            lig = ""
                            if r % 4 > 1:
                                lig += "/"
                            lig += "LIG"
                            if r % 2 != 0:
                                lig += "/"
                            while r > 3:
                                lig += ">"
                                r -= 4
                        self.ligatures.setdefault(c, {})[cmd.next_char] = (
                            lig,
                            cmd.remainder,
                        )

                if cmd.skip_byte >= STOP_FLAG:
                    break
                i += cmd.skip_byte + 1


if __name__ == "__main__":
    import sys

    tfm = TFM(sys.argv[1])
    print(
        "\n".join(
            x
            for x in [
                f"tfm.checksum={tfm.checksum}",
                f"tfm.designsize={tfm.designsize}",
                f"tfm.codingscheme={tfm.codingscheme}",
                f"tfm.fonttype={tfm.fonttype}",
                f"tfm.family={tfm.family}",
                f"tfm.seven_bit_safe_flag={tfm.seven_bit_safe_flag}",
                f"tfm.face={tfm.face}",
                f"tfm.extraheader={tfm.extraheader}",
                f"tfm.fontdimens={tfm.fontdimens}",
                f"tfm.right_boundary_char={tfm.right_boundary_char}",
                f"tfm.left_boundary_char={tfm.left_boundary_char}",
                f"tfm.kerning={tfm.kerning}",
                f"tfm.ligatures={tfm.ligatures}",
                f"tfm.chars={tfm.chars}",
            ]
        )
    )
    print(tfm)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\lfs.py ===
# coding=utf-8
# Copyright 2019-present, the HuggingFace Inc. team.
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
"""Git LFS related type definitions and utilities"""

import inspect
import io
import re
import warnings
from dataclasses import dataclass
from math import ceil
from os.path import getsize
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Dict, Iterable, List, Optional, Tuple, TypedDict
from urllib.parse import unquote

from huggingface_hub import constants

from .utils import (
    build_hf_headers,
    fix_hf_endpoint_in_url,
    get_session,
    hf_raise_for_status,
    http_backoff,
    logging,
    tqdm,
    validate_hf_hub_args,
)
from .utils._lfs import SliceFileObj
from .utils.sha import sha256, sha_fileobj
from .utils.tqdm import is_tqdm_disabled


if TYPE_CHECKING:
    from ._commit_api import CommitOperationAdd

logger = logging.get_logger(__name__)

OID_REGEX = re.compile(r"^[0-9a-f]{40}$")

LFS_MULTIPART_UPLOAD_COMMAND = "lfs-multipart-upload"

LFS_HEADERS = {
    "Accept": "application/vnd.git-lfs+json",
    "Content-Type": "application/vnd.git-lfs+json",
}


@dataclass
class UploadInfo:
    """
    Dataclass holding required information to determine whether a blob
    should be uploaded to the hub using the LFS protocol or the regular protocol

    Args:
        sha256 (`bytes`):
            SHA256 hash of the blob
        size (`int`):
            Size in bytes of the blob
        sample (`bytes`):
            First 512 bytes of the blob
    """

    sha256: bytes
    size: int
    sample: bytes

    @classmethod
    def from_path(cls, path: str):
        size = getsize(path)
        with io.open(path, "rb") as file:
            sample = file.peek(512)[:512]
            sha = sha_fileobj(file)
        return cls(size=size, sha256=sha, sample=sample)

    @classmethod
    def from_bytes(cls, data: bytes):
        sha = sha256(data).digest()
        return cls(size=len(data), sample=data[:512], sha256=sha)

    @classmethod
    def from_fileobj(cls, fileobj: BinaryIO):
        sample = fileobj.read(512)
        fileobj.seek(0, io.SEEK_SET)
        sha = sha_fileobj(fileobj)
        size = fileobj.tell()
        fileobj.seek(0, io.SEEK_SET)
        return cls(size=size, sha256=sha, sample=sample)


@validate_hf_hub_args
def post_lfs_batch_info(
    upload_infos: Iterable[UploadInfo],
    token: Optional[str],
    repo_type: str,
    repo_id: str,
    revision: Optional[str] = None,
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[List[dict], List[dict]]:
    """
    Requests the LFS batch endpoint to retrieve upload instructions

    Learn more: https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md

    Args:
        upload_infos (`Iterable` of `UploadInfo`):
            `UploadInfo` for the files that are being uploaded, typically obtained
            from `CommitOperationAdd.upload_info`
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated
            by a `/`.
        revision (`str`, *optional*):
            The git revision to upload to.
        headers (`dict`, *optional*):
            Additional headers to include in the request

    Returns:
        `LfsBatchInfo`: 2-tuple:
            - First element is the list of upload instructions from the server
            - Second element is an list of errors, if any

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If an argument is invalid or the server response is malformed.
        [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
            If the server returned an error.
    """
    endpoint = endpoint if endpoint is not None else constants.ENDPOINT
    url_prefix = ""
    if repo_type in constants.REPO_TYPES_URL_PREFIXES:
        url_prefix = constants.REPO_TYPES_URL_PREFIXES[repo_type]
    batch_url = f"{endpoint}/{url_prefix}{repo_id}.git/info/lfs/objects/batch"
    payload: Dict = {
        "operation": "upload",
        "transfers": ["basic", "multipart"],
        "objects": [
            {
                "oid": upload.sha256.hex(),
                "size": upload.size,
            }
            for upload in upload_infos
        ],
        "hash_algo": "sha256",
    }
    if revision is not None:
        payload["ref"] = {"name": unquote(revision)}  # revision has been previously 'quoted'

    headers = {
        **LFS_HEADERS,
        **build_hf_headers(token=token),
        **(headers or {}),
    }
    resp = get_session().post(batch_url, headers=headers, json=payload)
    hf_raise_for_status(resp)
    batch_info = resp.json()

    objects = batch_info.get("objects", None)
    if not isinstance(objects, list):
        raise ValueError("Malformed response from server")

    return (
        [_validate_batch_actions(obj) for obj in objects if "error" not in obj],
        [_validate_batch_error(obj) for obj in objects if "error" in obj],
    )


class PayloadPartT(TypedDict):
    partNumber: int
    etag: str


class CompletionPayloadT(TypedDict):
    """Payload that will be sent to the Hub when uploading multi-part."""

    oid: str
    parts: List[PayloadPartT]


def lfs_upload(
    operation: "CommitOperationAdd",
    lfs_batch_action: Dict,
    token: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    endpoint: Optional[str] = None,
) -> None:
    """
    Handles uploading a given object to the Hub with the LFS protocol.

    Can be a No-op if the content of the file is already present on the hub large file storage.

    Args:
        operation (`CommitOperationAdd`):
            The add operation triggering this upload.
        lfs_batch_action (`dict`):
            Upload instructions from the LFS batch endpoint for this object. See [`~utils.lfs.post_lfs_batch_info`] for
            more details.
        headers (`dict`, *optional*):
            Headers to include in the request, including authentication and user agent headers.

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `lfs_batch_action` is improperly formatted
        [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
            If the upload resulted in an error
    """
    # 0. If LFS file is already present, skip upload
    _validate_batch_actions(lfs_batch_action)
    actions = lfs_batch_action.get("actions")
    if actions is None:
        # The file was already uploaded
        logger.debug(f"Content of file {operation.path_in_repo} is already present upstream - skipping upload")
        return

    # 1. Validate server response (check required keys in dict)
    upload_action = lfs_batch_action["actions"]["upload"]
    _validate_lfs_action(upload_action)
    verify_action = lfs_batch_action["actions"].get("verify")
    if verify_action is not None:
        _validate_lfs_action(verify_action)

    # 2. Upload file (either single part or multi-part)
    header = upload_action.get("header", {})
    chunk_size = header.get("chunk_size")
    upload_url = fix_hf_endpoint_in_url(upload_action["href"], endpoint=endpoint)
    if chunk_size is not None:
        try:
            chunk_size = int(chunk_size)
        except (ValueError, TypeError):
            raise ValueError(
                f"Malformed response from LFS batch endpoint: `chunk_size` should be an integer. Got '{chunk_size}'."
            )
        _upload_multi_part(operation=operation, header=header, chunk_size=chunk_size, upload_url=upload_url)
    else:
        _upload_single_part(operation=operation, upload_url=upload_url)

    # 3. Verify upload went well
    if verify_action is not None:
        _validate_lfs_action(verify_action)
        verify_url = fix_hf_endpoint_in_url(verify_action["href"], endpoint)
        verify_resp = get_session().post(
            verify_url,
            headers=build_hf_headers(token=token, headers=headers),
            json={"oid": operation.upload_info.sha256.hex(), "size": operation.upload_info.size},
        )
        hf_raise_for_status(verify_resp)
    logger.debug(f"{operation.path_in_repo}: Upload successful")


def _validate_lfs_action(lfs_action: dict):
    """validates response from the LFS batch endpoint"""
    if not (
        isinstance(lfs_action.get("href"), str)
        and (lfs_action.get("header") is None or isinstance(lfs_action.get("header"), dict))
    ):
        raise ValueError("lfs_action is improperly formatted")
    return lfs_action


def _validate_batch_actions(lfs_batch_actions: dict):
    """validates response from the LFS batch endpoint"""
    if not (isinstance(lfs_batch_actions.get("oid"), str) and isinstance(lfs_batch_actions.get("size"), int)):
        raise ValueError("lfs_batch_actions is improperly formatted")

    upload_action = lfs_batch_actions.get("actions", {}).get("upload")
    verify_action = lfs_batch_actions.get("actions", {}).get("verify")
    if upload_action is not None:
        _validate_lfs_action(upload_action)
    if verify_action is not None:
        _validate_lfs_action(verify_action)
    return lfs_batch_actions


def _validate_batch_error(lfs_batch_error: dict):
    """validates response from the LFS batch endpoint"""
    if not (isinstance(lfs_batch_error.get("oid"), str) and isinstance(lfs_batch_error.get("size"), int)):
        raise ValueError("lfs_batch_error is improperly formatted")
    error_info = lfs_batch_error.get("error")
    if not (
        isinstance(error_info, dict)
        and isinstance(error_info.get("message"), str)
        and isinstance(error_info.get("code"), int)
    ):
        raise ValueError("lfs_batch_error is improperly formatted")
    return lfs_batch_error


def _upload_single_part(operation: "CommitOperationAdd", upload_url: str) -> None:
    """
    Uploads `fileobj` as a single PUT HTTP request (basic LFS transfer protocol)

    Args:
        upload_url (`str`):
            The URL to PUT the file to.
        fileobj:
            The file-like object holding the data to upload.

    Returns: `requests.Response`

    Raises:
     [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
        If the upload resulted in an error.
    """
    with operation.as_file(with_tqdm=True) as fileobj:
        # S3 might raise a transient 500 error -> let's retry if that happens
        response = http_backoff("PUT", upload_url, data=fileobj, retry_on_status_codes=(500, 502, 503, 504))
        hf_raise_for_status(response)


def _upload_multi_part(operation: "CommitOperationAdd", header: Dict, chunk_size: int, upload_url: str) -> None:
    """
    Uploads file using HF multipart LFS transfer protocol.
    """
    # 1. Get upload URLs for each part
    sorted_parts_urls = _get_sorted_parts_urls(header=header, upload_info=operation.upload_info, chunk_size=chunk_size)

    # 2. Upload parts (either with hf_transfer or in pure Python)
    use_hf_transfer = constants.HF_HUB_ENABLE_HF_TRANSFER
    if (
        constants.HF_HUB_ENABLE_HF_TRANSFER
        and not isinstance(operation.path_or_fileobj, str)
        and not isinstance(operation.path_or_fileobj, Path)
    ):
        warnings.warn(
            "hf_transfer is enabled but does not support uploading from bytes or BinaryIO, falling back to regular"
            " upload"
        )
        use_hf_transfer = False

    response_headers = (
        _upload_parts_hf_transfer(operation=operation, sorted_parts_urls=sorted_parts_urls, chunk_size=chunk_size)
        if use_hf_transfer
        else _upload_parts_iteratively(operation=operation, sorted_parts_urls=sorted_parts_urls, chunk_size=chunk_size)
    )

    # 3. Send completion request
    completion_res = get_session().post(
        upload_url,
        json=_get_completion_payload(response_headers, operation.upload_info.sha256.hex()),
        headers=LFS_HEADERS,
    )
    hf_raise_for_status(completion_res)


def _get_sorted_parts_urls(header: Dict, upload_info: UploadInfo, chunk_size: int) -> List[str]:
    sorted_part_upload_urls = [
        upload_url
        for _, upload_url in sorted(
            [
                (int(part_num, 10), upload_url)
                for part_num, upload_url in header.items()
                if part_num.isdigit() and len(part_num) > 0
            ],
            key=lambda t: t[0],
        )
    ]
    num_parts = len(sorted_part_upload_urls)
    if num_parts != ceil(upload_info.size / chunk_size):
        raise ValueError("Invalid server response to upload large LFS file")
    return sorted_part_upload_urls


def _get_completion_payload(response_headers: List[Dict], oid: str) -> CompletionPayloadT:
    parts: List[PayloadPartT] = []
    for part_number, header in enumerate(response_headers):
        etag = header.get("etag")
        if etag is None or etag == "":
            raise ValueError(f"Invalid etag (`{etag}`) returned for part {part_number + 1}")
        parts.append(
            {
                "partNumber": part_number + 1,
                "etag": etag,
            }
        )
    return {"oid": oid, "parts": parts}


def _upload_parts_iteratively(
    operation: "CommitOperationAdd", sorted_parts_urls: List[str], chunk_size: int
) -> List[Dict]:
    headers = []
    with operation.as_file(with_tqdm=True) as fileobj:
        for part_idx, part_upload_url in enumerate(sorted_parts_urls):
            with SliceFileObj(
                fileobj,
                seek_from=chunk_size * part_idx,
                read_limit=chunk_size,
            ) as fileobj_slice:
                # S3 might raise a transient 500 error -> let's retry if that happens
                part_upload_res = http_backoff(
                    "PUT", part_upload_url, data=fileobj_slice, retry_on_status_codes=(500, 502, 503, 504)
                )
                hf_raise_for_status(part_upload_res)
                headers.append(part_upload_res.headers)
    return headers  # type: ignore


def _upload_parts_hf_transfer(
    operation: "CommitOperationAdd", sorted_parts_urls: List[str], chunk_size: int
) -> List[Dict]:
    # Upload file using an external Rust-based package. Upload is faster but support less features (no progress bars).
    try:
        from hf_transfer import multipart_upload
    except ImportError:
        raise ValueError(
            "Fast uploading using 'hf_transfer' is enabled (HF_HUB_ENABLE_HF_TRANSFER=1) but 'hf_transfer' package is"
            " not available in your environment. Try `pip install hf_transfer`."
        )

    supports_callback = "callback" in inspect.signature(multipart_upload).parameters
    if not supports_callback:
        warnings.warn(
            "You are using an outdated version of `hf_transfer`. Consider upgrading to latest version to enable progress bars using `pip install -U hf_transfer`."
        )

    total = operation.upload_info.size
    desc = operation.path_in_repo
    if len(desc) > 40:
        desc = f"(…){desc[-40:]}"

    with tqdm(
        unit="B",
        unit_scale=True,
        total=total,
        initial=0,
        desc=desc,
        disable=is_tqdm_disabled(logger.getEffectiveLevel()),
        name="huggingface_hub.lfs_upload",
    ) as progress:
        try:
            output = multipart_upload(
                file_path=operation.path_or_fileobj,
                parts_urls=sorted_parts_urls,
                chunk_size=chunk_size,
                max_files=128,
                parallel_failures=127,  # could be removed
                max_retries=5,
                **({"callback": progress.update} if supports_callback else {}),
            )
        except Exception as e:
            raise RuntimeError(
                "An error occurred while uploading using `hf_transfer`. Consider disabling HF_HUB_ENABLE_HF_TRANSFER for"
                " better error handling."
            ) from e
        if not supports_callback:
            progress.update(total)
        return output

# === NexusCore/openenv\Lib\site-packages\decorator.py ===
# #########################     LICENSE     ############################ #

# Copyright (c) 2005-2025, Michele Simionato
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#   Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#   Redistributions in bytecode form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

"""
Decorator module, see
https://github.com/micheles/decorator/blob/master/docs/documentation.md
for the documentation.
"""
import re
import sys
import inspect
import operator
import itertools
import functools
from contextlib import _GeneratorContextManager
from inspect import getfullargspec, iscoroutinefunction, isgeneratorfunction

__version__ = '5.2.1'

DEF = re.compile(r'\s*def\s*([_\w][_\w\d]*)\s*\(')
POS = inspect.Parameter.POSITIONAL_OR_KEYWORD
EMPTY = inspect.Parameter.empty


# this is not used anymore in the core, but kept for backward compatibility
class FunctionMaker(object):
    """
    An object with the ability to create functions with a given signature.
    It has attributes name, doc, module, signature, defaults, dict and
    methods update and make.
    """

    # Atomic get-and-increment provided by the GIL
    _compile_count = itertools.count()

    # make pylint happy
    args = varargs = varkw = defaults = kwonlyargs = kwonlydefaults = ()

    def __init__(self, func=None, name=None, signature=None,
                 defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            # func can be a class or a callable, but not an instance method
            self.name = func.__name__
            if self.name == '<lambda>':  # small hack for lambda functions
                self.name = '_lambda_'
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isroutine(func) or isinstance(func, functools.partial):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                          'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for i, arg in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                allargs = list(self.args)
                allshortargs = list(self.args)
                if self.varargs:
                    allargs.append('*' + self.varargs)
                    allshortargs.append('*' + self.varargs)
                elif self.kwonlyargs:
                    allargs.append('*')  # single star syntax
                for a in self.kwonlyargs:
                    allargs.append('%s=None' % a)
                    allshortargs.append('%s=%s' % (a, a))
                if self.varkw:
                    allargs.append('**' + self.varkw)
                    allshortargs.append('**' + self.varkw)
                self.signature = ', '.join(allargs)
                self.shortsignature = ', '.join(allshortargs)
                self.dict = func.__dict__.copy()
        # func=None happens when decorating a caller
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        # check existence required attributes
        assert hasattr(self, 'name')
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        """
        Update the signature of func with the data in self
        """
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.__defaults__ = self.defaults
        func.__kwdefaults__ = self.kwonlydefaults or None
        func.__annotations__ = getattr(self, 'annotations', None)
        try:
            frame = sys._getframe(3)
        except AttributeError:  # for IronPython and similar implementations
            callermodule = '?'
        else:
            callermodule = frame.f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        """
        Make a new function from a given template and update the signature
        """
        src = src_templ % vars(self)  # expand name and signature
        evaldict = evaldict or {}
        mo = DEF.search(src)
        if mo is None:
            raise SyntaxError('not a valid function template\n%s' % src)
        name = mo.group(1)  # extract the function name
        names = set([name] + [arg.strip(' *') for arg in
                              self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError('%s is overridden in\n%s' % (n, src))

        if not src.endswith('\n'):  # add a newline for old Pythons
            src += '\n'

        # Ensure each generated function has a unique filename for profilers
        # (such as cProfile) that depend on the tuple of (<filename>,
        # <definition line>, <function name>) being unique.
        filename = '<decorator-gen-%d>' % next(self._compile_count)
        try:
            code = compile(src, filename, 'single')
            exec(code, evaldict)
        except Exception:
            print('Error in generated code:', file=sys.stderr)
            print(src, file=sys.stderr)
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None,
               doc=None, module=None, addsource=True, **attrs):
        """
        Create a function from the strings name, signature and body.
        evaldict is the evaluation dictionary. If addsource is true an
        attribute __source__ is added to the result. The attributes attrs
        are added, if any.
        """
        if isinstance(obj, str):  # "name(signature)"
            name, rest = obj.strip().split('(', 1)
            signature = rest[:-1]  # strip a right parens
            func = None
        else:  # a function
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        caller = evaldict.get('_call_')  # when called from `decorate`
        if caller and iscoroutinefunction(caller):
            body = ('async def %(name)s(%(signature)s):\n' + ibody).replace(
                'return', 'return await')
        else:
            body = 'def %(name)s(%(signature)s):\n' + ibody
        return self.make(body, evaldict, addsource, **attrs)


def fix(args, kwargs, sig):
    """
    Fix args and kwargs to be consistent with the signature
    """
    ba = sig.bind(*args, **kwargs)
    ba.apply_defaults()  # needed for test_dan_schult
    return ba.args, ba.kwargs


def decorate(func, caller, extras=(), kwsyntax=False):
    """
    Decorates a function/generator/coroutine using a caller.
    If kwsyntax is True calling the decorated functions with keyword
    syntax will pass the named arguments inside the ``kw`` dictionary,
    even if such argument are positional, similarly to what functools.wraps
    does. By default kwsyntax is False and the the arguments are untouched.
    """
    sig = inspect.signature(func)
    if isinstance(func, functools.partial):
        func = functools.update_wrapper(func, func.func)
    if iscoroutinefunction(caller):
        async def fun(*args, **kw):
            if not kwsyntax:
                args, kw = fix(args, kw, sig)
            return await caller(func, *(extras + args), **kw)
    elif isgeneratorfunction(caller):
        def fun(*args, **kw):
            if not kwsyntax:
                args, kw = fix(args, kw, sig)
            for res in caller(func, *(extras + args), **kw):
                yield res
    else:
        def fun(*args, **kw):
            if not kwsyntax:
                args, kw = fix(args, kw, sig)
            return caller(func, *(extras + args), **kw)

    fun.__name__ = func.__name__
    fun.__doc__ = func.__doc__
    fun.__wrapped__ = func
    fun.__signature__ = sig
    fun.__qualname__ = func.__qualname__
    # builtin functions like defaultdict.__setitem__ lack many attributes
    try:
        fun.__defaults__ = func.__defaults__
    except AttributeError:
        pass
    try:
        fun.__kwdefaults__ = func.__kwdefaults__
    except AttributeError:
        pass
    try:
        fun.__annotations__ = func.__annotations__
    except AttributeError:
        pass
    try:
        fun.__module__ = func.__module__
    except AttributeError:
        pass
    try:
        fun.__name__ = func.__name__
    except AttributeError:  # happens with old versions of numpy.vectorize
        func.__name__ == 'noname'
    try:
        fun.__dict__.update(func.__dict__)
    except AttributeError:
        pass
    return fun


def decoratorx(caller):
    """
    A version of "decorator" implemented via "exec" and not via the
    Signature object. Use this if you are want to preserve the `.__code__`
    object properties (https://github.com/micheles/decorator/issues/129).
    """
    def dec(func):
        return FunctionMaker.create(
            func,
            "return _call_(_func_, %(shortsignature)s)",
            dict(_call_=caller, _func_=func),
            __wrapped__=func, __qualname__=func.__qualname__)
    return dec


def decorator(caller, _func=None, kwsyntax=False):
    """
    decorator(caller) converts a caller function into a decorator
    """
    if _func is not None:  # return a decorated function
        # this is obsolete behavior; you should use decorate instead
        return decorate(_func, caller, (), kwsyntax)
    # else return a decorator function
    sig = inspect.signature(caller)
    dec_params = [p for p in sig.parameters.values() if p.kind is POS]

    def dec(func=None, *args, **kw):
        na = len(args) + 1
        extras = args + tuple(kw.get(p.name, p.default)
                              for p in dec_params[na:]
                              if p.default is not EMPTY)
        if func is None:
            return lambda func: decorate(func, caller, extras, kwsyntax)
        else:
            return decorate(func, caller, extras, kwsyntax)
    dec.__signature__ = sig.replace(parameters=dec_params)
    dec.__name__ = caller.__name__
    dec.__doc__ = caller.__doc__
    dec.__wrapped__ = caller
    dec.__qualname__ = caller.__qualname__
    dec.__kwdefaults__ = getattr(caller, '__kwdefaults__', None)
    dec.__dict__.update(caller.__dict__)
    return dec


# ####################### contextmanager ####################### #


class ContextManager(_GeneratorContextManager):
    def __init__(self, g, *a, **k):
        _GeneratorContextManager.__init__(self, g, a, k)

    def __call__(self, func):
        def caller(f, *a, **k):
            with self.__class__(self.func, *self.args, **self.kwds):
                return f(*a, **k)
        return decorate(func, caller)


_contextmanager = decorator(ContextManager)


def contextmanager(func):
    # Enable Pylint config: contextmanager-decorators=decorator.contextmanager
    return _contextmanager(func)


# ############################ dispatch_on ############################ #

def append(a, vancestors):
    """
    Append ``a`` to the list of the virtual ancestors, unless it is already
    included.
    """
    add = True
    for j, va in enumerate(vancestors):
        if issubclass(va, a):
            add = False
            break
        if issubclass(a, va):
            vancestors[j] = a
            add = False
    if add:
        vancestors.append(a)


# inspired from simplegeneric by P.J. Eby and functools.singledispatch
def dispatch_on(*dispatch_args):
    """
    Factory of decorators turning a function into a generic function
    dispatching on the given arguments.
    """
    assert dispatch_args, 'No dispatch args passed'
    dispatch_str = '(%s,)' % ', '.join(dispatch_args)

    def check(arguments, wrong=operator.ne, msg=''):
        """Make sure one passes the expected number of arguments"""
        if wrong(len(arguments), len(dispatch_args)):
            raise TypeError('Expected %d arguments, got %d%s' %
                            (len(dispatch_args), len(arguments), msg))

    def gen_func_dec(func):
        """Decorator turning a function into a generic function"""

        # first check the dispatch arguments
        argset = set(getfullargspec(func).args)
        if not set(dispatch_args) <= argset:
            raise NameError('Unknown dispatch arguments %s' % dispatch_str)

        typemap = {}

        def vancestors(*types):
            """
            Get a list of sets of virtual ancestors for the given types
            """
            check(types)
            ras = [[] for _ in range(len(dispatch_args))]
            for types_ in typemap:
                for t, type_, ra in zip(types, types_, ras):
                    if issubclass(t, type_) and type_ not in t.mro():
                        append(type_, ra)
            return [set(ra) for ra in ras]

        def ancestors(*types):
            """
            Get a list of virtual MROs, one for each type
            """
            check(types)
            lists = []
            for t, vas in zip(types, vancestors(*types)):
                n_vas = len(vas)
                if n_vas > 1:
                    raise RuntimeError(
                        'Ambiguous dispatch for %s: %s' % (t, vas))
                elif n_vas == 1:
                    va, = vas
                    mro = type('t', (t, va), {}).mro()[1:]
                else:
                    mro = t.mro()
                lists.append(mro[:-1])  # discard t and object
            return lists

        def register(*types):
            """
            Decorator to register an implementation for the given types
            """
            check(types)

            def dec(f):
                check(getfullargspec(f).args, operator.lt, ' in ' + f.__name__)
                typemap[types] = f
                return f
            return dec

        def dispatch_info(*types):
            """
            An utility to introspect the dispatch algorithm
            """
            check(types)
            lst = []
            for ancs in itertools.product(*ancestors(*types)):
                lst.append(tuple(a.__name__ for a in ancs))
            return lst

        def _dispatch(dispatch_args, *args, **kw):
            types = tuple(type(arg) for arg in dispatch_args)
            try:  # fast path
                f = typemap[types]
            except KeyError:
                pass
            else:
                return f(*args, **kw)
            combinations = itertools.product(*ancestors(*types))
            next(combinations)  # the first one has been already tried
            for types_ in combinations:
                f = typemap.get(types_)
                if f is not None:
                    return f(*args, **kw)

            # else call the default implementation
            return func(*args, **kw)

        return FunctionMaker.create(
            func, 'return _f_(%s, %%(shortsignature)s)' % dispatch_str,
            dict(_f_=_dispatch), register=register, default=func,
            typemap=typemap, vancestors=vancestors, ancestors=ancestors,
            dispatch_info=dispatch_info, __wrapped__=func)

    gen_func_dec.__name__ = 'dispatch_on' + dispatch_str
    return gen_func_dec

# === NexusCore/openenv\Lib\site-packages\websocket\_utils.py ===
from typing import Union

"""
_url.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
__all__ = ["NoLock", "validate_utf8", "extract_err_message", "extract_error_code"]


class NoLock:
    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass


try:
    # If wsaccel is available we use compiled routines to validate UTF-8
    # strings.
    from wsaccel.utf8validator import Utf8Validator

    def _validate_utf8(utfbytes: Union[str, bytes]) -> bool:
        result: bool = Utf8Validator().validate(utfbytes)[0]
        return result

except ImportError:
    # UTF-8 validator
    # python implementation of http://bjoern.hoehrmann.de/utf-8/decoder/dfa/

    _UTF8_ACCEPT = 0
    _UTF8_REJECT = 12

    _UTF8D = [
        # The first part of the table maps bytes to character classes that
        # to reduce the size of the transition table and create bitmasks.
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        7,
        8,
        8,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        10,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        4,
        3,
        3,
        11,
        6,
        6,
        6,
        5,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        # The second part is a transition table that maps a combination
        # of a state of the automaton and a character class to a state.
        0,
        12,
        24,
        36,
        60,
        96,
        84,
        12,
        12,
        12,
        48,
        72,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        0,
        12,
        12,
        12,
        12,
        12,
        0,
        12,
        0,
        12,
        12,
        12,
        24,
        12,
        12,
        12,
        12,
        12,
        24,
        12,
        24,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        24,
        12,
        12,
        12,
        12,
        12,
        24,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        24,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        36,
        12,
        36,
        12,
        12,
        12,
        36,
        12,
        12,
        12,
        12,
        12,
        36,
        12,
        36,
        12,
        12,
        12,
        36,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
    ]

    def _decode(state: int, codep: int, ch: int) -> tuple:
        tp = _UTF8D[ch]

        codep = (
            (ch & 0x3F) | (codep << 6) if (state != _UTF8_ACCEPT) else (0xFF >> tp) & ch
        )
        state = _UTF8D[256 + state + tp]

        return state, codep

    def _validate_utf8(utfbytes: Union[str, bytes]) -> bool:
        state = _UTF8_ACCEPT
        codep = 0
        for i in utfbytes:
            state, codep = _decode(state, codep, int(i))
            if state == _UTF8_REJECT:
                return False

        return True


def validate_utf8(utfbytes: Union[str, bytes]) -> bool:
    """
    validate utf8 byte string.
    utfbytes: utf byte string to check.
    return value: if valid utf8 string, return true. Otherwise, return false.
    """
    return _validate_utf8(utfbytes)


def extract_err_message(exception: Exception) -> Union[str, None]:
    if exception.args:
        exception_message: str = exception.args[0]
        return exception_message
    else:
        return None


def extract_error_code(exception: Exception) -> Union[int, None]:
    if exception.args and len(exception.args) > 1:
        return exception.args[0] if isinstance(exception.args[0], int) else None

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

from .base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .grpc import PermissionServiceGrpcTransport


class PermissionServiceGrpcAsyncIOTransport(PermissionServiceTransport):
    """gRPC AsyncIO backend transport for PermissionService.

    Provides methods for managing permissions to PaLM API
    resources.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest],
        Awaitable[gag_permission.Permission],
    ]:
        r"""Return a callable for the create permission method over gRPC.

        Create a permission to a specific resource.

        Returns:
            Callable[[~.CreatePermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_permission" not in self._stubs:
            self._stubs["create_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/CreatePermission",
                request_serializer=permission_service.CreatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["create_permission"]

    @property
    def get_permission(
        self,
    ) -> Callable[
        [permission_service.GetPermissionRequest], Awaitable[permission.Permission]
    ]:
        r"""Return a callable for the get permission method over gRPC.

        Gets information about a specific Permission.

        Returns:
            Callable[[~.GetPermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_permission" not in self._stubs:
            self._stubs["get_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/GetPermission",
                request_serializer=permission_service.GetPermissionRequest.serialize,
                response_deserializer=permission.Permission.deserialize,
            )
        return self._stubs["get_permission"]

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        Awaitable[permission_service.ListPermissionsResponse],
    ]:
        r"""Return a callable for the list permissions method over gRPC.

        Lists permissions for the specific resource.

        Returns:
            Callable[[~.ListPermissionsRequest],
                    Awaitable[~.ListPermissionsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_permissions" not in self._stubs:
            self._stubs["list_permissions"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/ListPermissions",
                request_serializer=permission_service.ListPermissionsRequest.serialize,
                response_deserializer=permission_service.ListPermissionsResponse.deserialize,
            )
        return self._stubs["list_permissions"]

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest],
        Awaitable[gag_permission.Permission],
    ]:
        r"""Return a callable for the update permission method over gRPC.

        Updates the permission.

        Returns:
            Callable[[~.UpdatePermissionRequest],
                    Awaitable[~.Permission]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_permission" not in self._stubs:
            self._stubs["update_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/UpdatePermission",
                request_serializer=permission_service.UpdatePermissionRequest.serialize,
                response_deserializer=gag_permission.Permission.deserialize,
            )
        return self._stubs["update_permission"]

    @property
    def delete_permission(
        self,
    ) -> Callable[
        [permission_service.DeletePermissionRequest], Awaitable[empty_pb2.Empty]
    ]:
        r"""Return a callable for the delete permission method over gRPC.

        Deletes the permission.

        Returns:
            Callable[[~.DeletePermissionRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_permission" not in self._stubs:
            self._stubs["delete_permission"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/DeletePermission",
                request_serializer=permission_service.DeletePermissionRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_permission"]

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        Awaitable[permission_service.TransferOwnershipResponse],
    ]:
        r"""Return a callable for the transfer ownership method over gRPC.

        Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        Returns:
            Callable[[~.TransferOwnershipRequest],
                    Awaitable[~.TransferOwnershipResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "transfer_ownership" not in self._stubs:
            self._stubs["transfer_ownership"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.PermissionService/TransferOwnership",
                request_serializer=permission_service.TransferOwnershipRequest.serialize,
                response_deserializer=permission_service.TransferOwnershipResponse.deserialize,
            )
        return self._stubs["transfer_ownership"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.create_permission: gapic_v1.method_async.wrap_method(
                self.create_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_permission: gapic_v1.method_async.wrap_method(
                self.get_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_permissions: gapic_v1.method_async.wrap_method(
                self.list_permissions,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_permission: gapic_v1.method_async.wrap_method(
                self.update_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_permission: gapic_v1.method_async.wrap_method(
                self.delete_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.transfer_ownership: gapic_v1.method_async.wrap_method(
                self.transfer_ownership,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("PermissionServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\casual.py ===
#
# Natural Language Toolkit: Twitter Tokenizer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Christopher Potts <cgpotts@stanford.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk> (modifications)
#         Pierpaolo Pantone <> (modifications)
#         Tom Aarsen <> (modifications)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#


"""
Twitter-aware tokenizer, designed to be flexible and easy to adapt to new
domains and tasks. The basic logic is this:

1. The tuple REGEXPS defines a list of regular expression
   strings.

2. The REGEXPS strings are put, in order, into a compiled
   regular expression object called WORD_RE, under the TweetTokenizer
   class.

3. The tokenization is done by WORD_RE.findall(s), where s is the
   user-supplied string, inside the tokenize() method of the class
   TweetTokenizer.

4. When instantiating Tokenizer objects, there are several options:
    * preserve_case. By default, it is set to True. If it is set to
      False, then the tokenizer will downcase everything except for
      emoticons.
    * reduce_len. By default, it is set to False. It specifies whether
      to replace repeated character sequences of length 3 or greater
      with sequences of length 3.
    * strip_handles. By default, it is set to False. It specifies
      whether to remove Twitter handles of text used in the
      `tokenize` method.
    * match_phone_numbers. By default, it is set to True. It indicates
      whether the `tokenize` method should look for phone numbers.
"""


######################################################################

import html
from typing import List

import regex  # https://github.com/nltk/nltk/issues/2409

from nltk.tokenize.api import TokenizerI

######################################################################
# The following strings are components in the regular expression
# that is used for tokenizing. It's important that phone_number
# appears first in the final regex (since it can contain whitespace).
# It also could matter that tags comes after emoticons, due to the
# possibility of having text like
#
#     <:| and some text >:)
#
# Most importantly, the final element should always be last, since it
# does a last ditch whitespace-based tokenization of whatever is left.

# ToDo: Update with https://en.wikipedia.org/wiki/List_of_emoticons ?

# This particular element is used in a couple ways, so we define it
# with a name:
EMOTICONS = r"""
    (?:
      [<>]?
      [:;=8]                     # eyes
      [\-o\*\']?                 # optional nose
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      |
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      [\-o\*\']?                 # optional nose
      [:;=8]                     # eyes
      [<>]?
      |
      </?3                       # heart
    )"""

# URL pattern due to John Gruber, modified by Tom Winzig. See
# https://gist.github.com/winzig/8894715

URLS = r"""			# Capture 1: entire matched URL
  (?:
  https?:				# URL protocol and colon
    (?:
      /{1,3}				# 1-3 slashes
      |					#   or
      [a-z0-9%]				# Single letter or digit or '%'
                                       # (Trying not to match e.g. "URI::Escape")
    )
    |					#   or
                                       # looks like domain name followed by a slash:
    [a-z0-9.\-]+[.]
    (?:[a-z]{2,13})
    /
  )
  (?:					# One or more:
    [^\s()<>{}\[\]]+			# Run of non-space, non-()<>{}[]
    |					#   or
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\) # balanced parens, one level deep: (...(...)...)
    |
    \([^\s]+?\)				# balanced parens, non-recursive: (...)
  )+
  (?:					# End with:
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\) # balanced parens, one level deep: (...(...)...)
    |
    \([^\s]+?\)				# balanced parens, non-recursive: (...)
    |					#   or
    [^\s`!()\[\]{};:'".,<>?«»“”‘’]	# not a space or one of these punct chars
  )
  |					# OR, the following to match naked domains:
  (?:
  	(?<!@)			        # not preceded by a @, avoid matching foo@_gmail.com_
    [a-z0-9]+
    (?:[.\-][a-z0-9]+)*
    [.]
    (?:[a-z]{2,13})
    \b
    /?
    (?!@)			        # not succeeded by a @,
                            # avoid matching "foo.na" in "foo.na@example.com"
  )
"""

# emoji flag sequence
# https://en.wikipedia.org/wiki/Regional_indicator_symbol
# For regex simplicity, include all possible enclosed letter pairs,
# not the ISO subset of two-letter regional indicator symbols.
# See https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Current_codes
# Future regional flag support may be handled with the regex for
# U+1F3F4 🏴 followed by emoji tag sequences:
# r'\U0001F3F4[\U000E0000-\U000E007E]{5}\U000E007F'
FLAGS = r"""
  (?:
    [\U0001F1E6-\U0001F1FF]{2}  # all enclosed letter pairs
    |
    # English flag
    \U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006e\U000E0067\U000E007F
    |
    # Scottish flag
    \U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F
    |
    # For Wales? Why Richard, it profit a man nothing to give his soul for the whole world … but for Wales!
    \U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F
  )
"""

# Regex for recognizing phone numbers:
PHONE_REGEX = r"""
    (?:
      (?:            # (international)
        \+?[01]
        [ *\-.\)]*
      )?
      (?:            # (area code)
        [\(]?
        \d{3}
        [ *\-.\)]*
      )?
      \d{3}          # exchange
      [ *\-.\)]*
      \d{4}          # base
    )"""

# The components of the tokenizer:
REGEXPS = (
    URLS,
    # ASCII Emoticons
    EMOTICONS,
    # HTML tags:
    r"""<[^>\s]+>""",
    # ASCII Arrows
    r"""[\-]+>|<[\-]+""",
    # Twitter username:
    r"""(?:@[\w_]+)""",
    # Twitter hashtags:
    r"""(?:\#+[\w_]+[\w\'_\-]*[\w_]+)""",
    # email addresses
    r"""[\w.+-]+@[\w-]+\.(?:[\w-]\.?)+[\w-]""",
    # Zero-Width-Joiner and Skin tone modifier emojis
    """.(?:
        [\U0001F3FB-\U0001F3FF]?(?:\u200d.[\U0001F3FB-\U0001F3FF]?)+
        |
        [\U0001F3FB-\U0001F3FF]
    )""",
    # flags
    FLAGS,
    # Remaining word types:
    r"""
    (?:[^\W\d_](?:[^\W\d_]|['\-_])+[^\W\d_]) # Words with apostrophes or dashes.
    |
    (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
    |
    (?:[\w_]+)                     # Words without apostrophes or dashes.
    |
    (?:\.(?:\s*\.){1,})            # Ellipsis dots.
    |
    (?:\S)                         # Everything else that isn't whitespace.
    """,
)

# Take the main components and add a phone regex as the second parameter
REGEXPS_PHONE = (REGEXPS[0], PHONE_REGEX, *REGEXPS[1:])

######################################################################
# TweetTokenizer.WORD_RE and TweetTokenizer.PHONE_WORD_RE represent
# the core tokenizing regexes. They are compiled lazily.

# WORD_RE performs poorly on these patterns:
HANG_RE = regex.compile(r"([^a-zA-Z0-9])\1{3,}")

# The emoticon string gets its own regex so that we can preserve case for
# them as needed:
EMOTICON_RE = regex.compile(EMOTICONS, regex.VERBOSE | regex.I | regex.UNICODE)

# These are for regularizing HTML entities to Unicode:
ENT_RE = regex.compile(r"&(#?(x?))([^&;\s]+);")

# For stripping away handles from a tweet:
HANDLES_RE = regex.compile(
    r"(?<![A-Za-z0-9_!@#\$%&*])@"
    r"(([A-Za-z0-9_]){15}(?!@)|([A-Za-z0-9_]){1,14}(?![A-Za-z0-9_]*@))"
)


######################################################################
# Functions for converting html entities
######################################################################


def _str_to_unicode(text, encoding=None, errors="strict"):
    if encoding is None:
        encoding = "utf-8"
    if isinstance(text, bytes):
        return text.decode(encoding, errors)
    return text


def _replace_html_entities(text, keep=(), remove_illegal=True, encoding="utf-8"):
    """
    Remove entities from text by converting them to their
    corresponding unicode character.

    :param text: a unicode string or a byte string encoded in the given
    `encoding` (which defaults to 'utf-8').

    :param list keep:  list of entity names which should not be replaced.\
    This supports both numeric entities (``&#nnnn;`` and ``&#hhhh;``)
    and named entities (such as ``&nbsp;`` or ``&gt;``).

    :param bool remove_illegal: If `True`, entities that can't be converted are\
    removed. Otherwise, entities that can't be converted are kept "as
    is".

    :returns: A unicode string with the entities removed.

    See https://github.com/scrapy/w3lib/blob/master/w3lib/html.py

        >>> from nltk.tokenize.casual import _replace_html_entities
        >>> _replace_html_entities(b'Price: &pound;100')
        'Price: \\xa3100'
        >>> print(_replace_html_entities(b'Price: &pound;100'))
        Price: £100
        >>>
    """

    def _convert_entity(match):
        entity_body = match.group(3)
        if match.group(1):
            try:
                if match.group(2):
                    number = int(entity_body, 16)
                else:
                    number = int(entity_body, 10)
                # Numeric character references in the 80-9F range are typically
                # interpreted by browsers as representing the characters mapped
                # to bytes 80-9F in the Windows-1252 encoding. For more info
                # see: https://en.wikipedia.org/wiki/ISO/IEC_8859-1#Similar_character_sets
                if 0x80 <= number <= 0x9F:
                    return bytes((number,)).decode("cp1252")
            except ValueError:
                number = None
        else:
            if entity_body in keep:
                return match.group(0)
            number = html.entities.name2codepoint.get(entity_body)
        if number is not None:
            try:
                return chr(number)
            except (ValueError, OverflowError):
                pass

        return "" if remove_illegal else match.group(0)

    return ENT_RE.sub(_convert_entity, _str_to_unicode(text, encoding))


######################################################################


class TweetTokenizer(TokenizerI):
    r"""
    Tokenizer for tweets.

        >>> from nltk.tokenize import TweetTokenizer
        >>> tknzr = TweetTokenizer()
        >>> s0 = "This is a cooool #dummysmiley: :-) :-P <3 and some arrows < > -> <--"
        >>> tknzr.tokenize(s0) # doctest: +NORMALIZE_WHITESPACE
        ['This', 'is', 'a', 'cooool', '#dummysmiley', ':', ':-)', ':-P', '<3', 'and', 'some', 'arrows', '<', '>', '->',
         '<--']

    Examples using `strip_handles` and `reduce_len parameters`:

        >>> tknzr = TweetTokenizer(strip_handles=True, reduce_len=True)
        >>> s1 = '@remy: This is waaaaayyyy too much for you!!!!!!'
        >>> tknzr.tokenize(s1)
        [':', 'This', 'is', 'waaayyy', 'too', 'much', 'for', 'you', '!', '!', '!']
    """

    # Values used to lazily compile WORD_RE and PHONE_WORD_RE,
    # which are the core tokenizing regexes.
    _WORD_RE = None
    _PHONE_WORD_RE = None

    ######################################################################

    def __init__(
        self,
        preserve_case=True,
        reduce_len=False,
        strip_handles=False,
        match_phone_numbers=True,
    ):
        """
        Create a `TweetTokenizer` instance with settings for use in the `tokenize` method.

        :param preserve_case: Flag indicating whether to preserve the casing (capitalisation)
            of text used in the `tokenize` method. Defaults to True.
        :type preserve_case: bool
        :param reduce_len: Flag indicating whether to replace repeated character sequences
            of length 3 or greater with sequences of length 3. Defaults to False.
        :type reduce_len: bool
        :param strip_handles: Flag indicating whether to remove Twitter handles of text used
            in the `tokenize` method. Defaults to False.
        :type strip_handles: bool
        :param match_phone_numbers: Flag indicating whether the `tokenize` method should look
            for phone numbers. Defaults to True.
        :type match_phone_numbers: bool
        """
        self.preserve_case = preserve_case
        self.reduce_len = reduce_len
        self.strip_handles = strip_handles
        self.match_phone_numbers = match_phone_numbers

    def tokenize(self, text: str) -> List[str]:
        """Tokenize the input text.

        :param text: str
        :rtype: list(str)
        :return: a tokenized list of strings; joining this list returns\
        the original string if `preserve_case=False`.
        """
        # Fix HTML character entities:
        text = _replace_html_entities(text)
        # Remove username handles
        if self.strip_handles:
            text = remove_handles(text)
        # Normalize word lengthening
        if self.reduce_len:
            text = reduce_lengthening(text)
        # Shorten problematic sequences of characters
        safe_text = HANG_RE.sub(r"\1\1\1", text)
        # Recognise phone numbers during tokenization
        if self.match_phone_numbers:
            words = self.PHONE_WORD_RE.findall(safe_text)
        else:
            words = self.WORD_RE.findall(safe_text)
        # Possibly alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:
            words = list(
                map((lambda x: x if EMOTICON_RE.search(x) else x.lower()), words)
            )
        return words

    @property
    def WORD_RE(self) -> "regex.Pattern":
        """Core TweetTokenizer regex"""
        # Compiles the regex for this and all future instantiations of TweetTokenizer.
        if not type(self)._WORD_RE:
            type(self)._WORD_RE = regex.compile(
                f"({'|'.join(REGEXPS)})",
                regex.VERBOSE | regex.I | regex.UNICODE,
            )
        return type(self)._WORD_RE

    @property
    def PHONE_WORD_RE(self) -> "regex.Pattern":
        """Secondary core TweetTokenizer regex"""
        # Compiles the regex for this and all future instantiations of TweetTokenizer.
        if not type(self)._PHONE_WORD_RE:
            type(self)._PHONE_WORD_RE = regex.compile(
                f"({'|'.join(REGEXPS_PHONE)})",
                regex.VERBOSE | regex.I | regex.UNICODE,
            )
        return type(self)._PHONE_WORD_RE


######################################################################
# Normalization Functions
######################################################################


def reduce_lengthening(text):
    """
    Replace repeated character sequences of length 3 or greater with sequences
    of length 3.
    """
    pattern = regex.compile(r"(.)\1{2,}")
    return pattern.sub(r"\1\1\1", text)


def remove_handles(text):
    """
    Remove Twitter username handles from text.
    """
    # Substitute handles with ' ' to ensure that text on either side of removed handles are tokenized correctly
    return HANDLES_RE.sub(" ", text)


######################################################################
# Tokenization Function
######################################################################


def casual_tokenize(
    text,
    preserve_case=True,
    reduce_len=False,
    strip_handles=False,
    match_phone_numbers=True,
):
    """
    Convenience function for wrapping the tokenizer.
    """
    return TweetTokenizer(
        preserve_case=preserve_case,
        reduce_len=reduce_len,
        strip_handles=strip_handles,
        match_phone_numbers=match_phone_numbers,
    ).tokenize(text)


###############################################################################

# === NexusCore/openenv\Lib\site-packages\nltk\stem\arlstem2.py ===
#
# Natural Language Toolkit: ARLSTem Stemmer v2
#
# Copyright (C) 2001-2024 NLTK Project
#
# Author: Kheireddine Abainia (x-programer) <k.abainia@gmail.com>
# Algorithms: Kheireddine Abainia <k.abainia@gmail.com>
#                         Hamza Rebbani <hamrebbani@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
ARLSTem2 Arabic Light Stemmer
The details about the implementation of this algorithm are described in:
K. Abainia and H. Rebbani, Comparing the Effectiveness of the Improved ARLSTem
Algorithm with Existing Arabic Light Stemmers, International Conference on
Theoretical and Applicative Aspects of Computer Science (ICTAACS'19), Skikda,
Algeria, December 15-16, 2019.
ARLSTem2 is an Arabic light stemmer based on removing the affixes from
the words (i.e. prefixes, suffixes and infixes). It is an improvement
of the previous Arabic light stemmer (ARLSTem). The new version was compared to
the original algorithm and several existing Arabic light stemmers, where the
results showed that the new version considerably improves the under-stemming
errors that are common to light stemmers. Both ARLSTem and ARLSTem2 can be run
online and do not use any dictionary.
"""
import re

from nltk.stem.api import StemmerI


class ARLSTem2(StemmerI):
    """
    Return a stemmed Arabic word after removing affixes. This an improved
    version of the previous algorithm, which reduces under-stemming errors.
    Typically used in Arabic search engine, information retrieval and NLP.

        >>> from nltk.stem import arlstem2
        >>> stemmer = ARLSTem2()
        >>> word = stemmer.stem('يعمل')
        >>> print(word)
        عمل

    :param token: The input Arabic word (unicode) to be stemmed
    :type token: unicode
    :return: A unicode Arabic word
    """

    def __init__(self):
        # different Alif with hamza
        self.re_hamzated_alif = re.compile(r"[\u0622\u0623\u0625]")
        self.re_alifMaqsura = re.compile(r"[\u0649]")
        self.re_diacritics = re.compile(r"[\u064B-\u065F]")

        # Alif Laam, Laam Laam, Fa Laam, Fa Ba
        self.pr2 = ["\u0627\u0644", "\u0644\u0644", "\u0641\u0644", "\u0641\u0628"]
        # Ba Alif Laam, Kaaf Alif Laam, Waaw Alif Laam
        self.pr3 = ["\u0628\u0627\u0644", "\u0643\u0627\u0644", "\u0648\u0627\u0644"]
        # Fa Laam Laam, Waaw Laam Laam
        self.pr32 = ["\u0641\u0644\u0644", "\u0648\u0644\u0644"]
        # Fa Ba Alif Laam, Waaw Ba Alif Laam, Fa Kaaf Alif Laam
        self.pr4 = [
            "\u0641\u0628\u0627\u0644",
            "\u0648\u0628\u0627\u0644",
            "\u0641\u0643\u0627\u0644",
        ]

        # Kaf Yaa, Kaf Miim
        self.su2 = ["\u0643\u064A", "\u0643\u0645"]
        # Ha Alif, Ha Miim
        self.su22 = ["\u0647\u0627", "\u0647\u0645"]
        # Kaf Miim Alif, Kaf Noon Shadda
        self.su3 = ["\u0643\u0645\u0627", "\u0643\u0646\u0651"]
        # Ha Miim Alif, Ha Noon Shadda
        self.su32 = ["\u0647\u0645\u0627", "\u0647\u0646\u0651"]

        # Alif Noon, Ya Noon, Waaw Noon
        self.pl_si2 = ["\u0627\u0646", "\u064A\u0646", "\u0648\u0646"]
        # Taa Alif Noon, Taa Ya Noon
        self.pl_si3 = ["\u062A\u0627\u0646", "\u062A\u064A\u0646"]

        # Alif Noon, Waaw Noon
        self.verb_su2 = ["\u0627\u0646", "\u0648\u0646"]
        # Siin Taa, Siin Yaa
        self.verb_pr2 = ["\u0633\u062A", "\u0633\u064A"]
        # Siin Alif, Siin Noon
        self.verb_pr22 = ["\u0633\u0627", "\u0633\u0646"]
        # Lam Noon, Lam Taa, Lam Yaa, Lam Hamza
        self.verb_pr33 = [
            "\u0644\u0646",
            "\u0644\u062A",
            "\u0644\u064A",
            "\u0644\u0623",
        ]
        # Taa Miim Alif, Taa Noon Shadda
        self.verb_suf3 = ["\u062A\u0645\u0627", "\u062A\u0646\u0651"]
        # Noon Alif, Taa Miim, Taa Alif, Waaw Alif
        self.verb_suf2 = [
            "\u0646\u0627",
            "\u062A\u0645",
            "\u062A\u0627",
            "\u0648\u0627",
        ]
        # Taa, Alif, Noon
        self.verb_suf1 = ["\u062A", "\u0627", "\u0646"]

    def stem1(self, token):
        """
        call this function to get the first stem
        """
        try:
            if token is None:
                raise ValueError(
                    "The word could not be stemmed, because \
                                 it is empty !"
                )
            self.is_verb = False
            # remove Arabic diacritics and replace some letters with others
            token = self.norm(token)
            # strip the common noun prefixes
            pre = self.pref(token)
            if pre is not None:
                token = pre
            # transform the feminine form to masculine form
            fm = self.fem2masc(token)
            if fm is not None:
                return fm
            # strip the adjective affixes
            adj = self.adjective(token)
            if adj is not None:
                return adj
            # strip the suffixes that are common to nouns and verbs
            token = self.suff(token)
            # transform a plural noun to a singular noun
            ps = self.plur2sing(token)
            if ps is None:
                if pre is None:  # if the noun prefixes are not stripped
                    # strip the verb prefixes and suffixes
                    verb = self.verb(token)
                    if verb is not None:
                        self.is_verb = True
                        return verb
            else:
                return ps
            return token
        except ValueError as e:
            print(e)

    def stem(self, token):
        # stem the input word
        try:
            if token is None:
                raise ValueError(
                    "The word could not be stemmed, because \
                                 it is empty !"
                )
            # run the first round of stemming
            token = self.stem1(token)
            # check if there is some additional noun affixes
            if len(token) > 4:
                # ^Taa, $Yaa + char
                if token.startswith("\u062A") and token[-2] == "\u064A":
                    token = token[1:-2] + token[-1]
                    return token
                # ^Miim, $Waaw + char
                if token.startswith("\u0645") and token[-2] == "\u0648":
                    token = token[1:-2] + token[-1]
                    return token
            if len(token) > 3:
                # !^Alif, $Yaa
                if not token.startswith("\u0627") and token.endswith("\u064A"):
                    token = token[:-1]
                    return token
                # $Laam
                if token.startswith("\u0644"):
                    return token[1:]
            return token
        except ValueError as e:
            print(e)

    def norm(self, token):
        """
        normalize the word by removing diacritics, replace hamzated Alif
        with Alif bare, replace AlifMaqsura with Yaa and remove Waaw at the
        beginning.
        """
        # strip Arabic diacritics
        token = self.re_diacritics.sub("", token)
        # replace Hamzated Alif with Alif bare
        token = self.re_hamzated_alif.sub("\u0627", token)
        # replace alifMaqsura with Yaa
        token = self.re_alifMaqsura.sub("\u064A", token)
        # strip the Waaw from the word beginning if the remaining is
        # tri-literal at least
        if token.startswith("\u0648") and len(token) > 3:
            token = token[1:]
        return token

    def pref(self, token):
        """
        remove prefixes from the words' beginning.
        """
        if len(token) > 5:
            for p3 in self.pr3:
                if token.startswith(p3):
                    return token[3:]
        if len(token) > 6:
            for p4 in self.pr4:
                if token.startswith(p4):
                    return token[4:]
        if len(token) > 5:
            for p3 in self.pr32:
                if token.startswith(p3):
                    return token[3:]
        if len(token) > 4:
            for p2 in self.pr2:
                if token.startswith(p2):
                    return token[2:]

    def adjective(self, token):
        """
        remove the infixes from adjectives
        """
        # ^Alif, Alif, $Yaa
        if len(token) > 5:
            if (
                token.startswith("\u0627")
                and token[-3] == "\u0627"
                and token.endswith("\u064A")
            ):
                return token[:-3] + token[-2]

    def suff(self, token):
        """
        remove the suffixes from the word's ending.
        """
        if token.endswith("\u0643") and len(token) > 3:
            return token[:-1]
        if len(token) > 4:
            for s2 in self.su2:
                if token.endswith(s2):
                    return token[:-2]
        if len(token) > 5:
            for s3 in self.su3:
                if token.endswith(s3):
                    return token[:-3]
        if token.endswith("\u0647") and len(token) > 3:
            token = token[:-1]
            return token
        if len(token) > 4:
            for s2 in self.su22:
                if token.endswith(s2):
                    return token[:-2]
        if len(token) > 5:
            for s3 in self.su32:
                if token.endswith(s3):
                    return token[:-3]
        # $Noon and Alif
        if token.endswith("\u0646\u0627") and len(token) > 4:
            return token[:-2]
        return token

    def fem2masc(self, token):
        """
        transform the word from the feminine form to the masculine form.
        """
        if len(token) > 6:
            # ^Taa, Yaa, $Yaa and Taa Marbuta
            if (
                token.startswith("\u062A")
                and token[-4] == "\u064A"
                and token.endswith("\u064A\u0629")
            ):
                return token[1:-4] + token[-3]
            # ^Alif, Yaa, $Yaa and Taa Marbuta
            if (
                token.startswith("\u0627")
                and token[-4] == "\u0627"
                and token.endswith("\u064A\u0629")
            ):
                return token[:-4] + token[-3]
        # $Alif, Yaa and Taa Marbuta
        if token.endswith("\u0627\u064A\u0629") and len(token) > 5:
            return token[:-2]
        if len(token) > 4:
            # Alif, $Taa Marbuta
            if token[1] == "\u0627" and token.endswith("\u0629"):
                return token[0] + token[2:-1]
            # $Yaa and Taa Marbuta
            if token.endswith("\u064A\u0629"):
                return token[:-2]
        # $Taa Marbuta
        if token.endswith("\u0629") and len(token) > 3:
            return token[:-1]

    def plur2sing(self, token):
        """
        transform the word from the plural form to the singular form.
        """
        # ^Haa, $Noon, Waaw
        if len(token) > 5:
            if token.startswith("\u0645") and token.endswith("\u0648\u0646"):
                return token[1:-2]
        if len(token) > 4:
            for ps2 in self.pl_si2:
                if token.endswith(ps2):
                    return token[:-2]
        if len(token) > 5:
            for ps3 in self.pl_si3:
                if token.endswith(ps3):
                    return token[:-3]
        if len(token) > 4:
            # $Alif, Taa
            if token.endswith("\u0627\u062A"):
                return token[:-2]
            # ^Alif Alif
            if token.startswith("\u0627") and token[2] == "\u0627":
                return token[:2] + token[3:]
            # ^Alif Alif
            if token.startswith("\u0627") and token[-2] == "\u0627":
                return token[1:-2] + token[-1]

    def verb(self, token):
        """
        stem the verb prefixes and suffixes or both
        """
        vb = self.verb_t1(token)
        if vb is not None:
            return vb
        vb = self.verb_t2(token)
        if vb is not None:
            return vb
        vb = self.verb_t3(token)
        if vb is not None:
            return vb
        vb = self.verb_t4(token)
        if vb is not None:
            return vb
        vb = self.verb_t5(token)
        if vb is not None:
            return vb
        vb = self.verb_t6(token)
        return vb

    def verb_t1(self, token):
        """
        stem the present tense co-occurred prefixes and suffixes
        """
        if len(token) > 5 and token.startswith("\u062A"):  # Taa
            for s2 in self.pl_si2:
                if token.endswith(s2):
                    return token[1:-2]
        if len(token) > 5 and token.startswith("\u064A"):  # Yaa
            for s2 in self.verb_su2:
                if token.endswith(s2):
                    return token[1:-2]
        if len(token) > 4 and token.startswith("\u0627"):  # Alif
            # Waaw Alif
            if len(token) > 5 and token.endswith("\u0648\u0627"):
                return token[1:-2]
            # Yaa
            if token.endswith("\u064A"):
                return token[1:-1]
            # Alif
            if token.endswith("\u0627"):
                return token[1:-1]
            # Noon
            if token.endswith("\u0646"):
                return token[1:-1]
        # ^Yaa, Noon$
        if len(token) > 4 and token.startswith("\u064A") and token.endswith("\u0646"):
            return token[1:-1]
        # ^Taa, Noon$
        if len(token) > 4 and token.startswith("\u062A") and token.endswith("\u0646"):
            return token[1:-1]

    def verb_t2(self, token):
        """
        stem the future tense co-occurred prefixes and suffixes
        """
        if len(token) > 6:
            for s2 in self.pl_si2:
                # ^Siin Taa
                if token.startswith(self.verb_pr2[0]) and token.endswith(s2):
                    return token[2:-2]
            # ^Siin Yaa, Alif Noon$
            if token.startswith(self.verb_pr2[1]) and token.endswith(self.pl_si2[0]):
                return token[2:-2]
            # ^Siin Yaa, Waaw Noon$
            if token.startswith(self.verb_pr2[1]) and token.endswith(self.pl_si2[2]):
                return token[2:-2]
        # ^Siin Taa, Noon$
        if (
            len(token) > 5
            and token.startswith(self.verb_pr2[0])
            and token.endswith("\u0646")
        ):
            return token[2:-1]
        # ^Siin Yaa, Noon$
        if (
            len(token) > 5
            and token.startswith(self.verb_pr2[1])
            and token.endswith("\u0646")
        ):
            return token[2:-1]

    def verb_t3(self, token):
        """
        stem the present tense suffixes
        """
        if len(token) > 5:
            for su3 in self.verb_suf3:
                if token.endswith(su3):
                    return token[:-3]
        if len(token) > 4:
            for su2 in self.verb_suf2:
                if token.endswith(su2):
                    return token[:-2]
        if len(token) > 3:
            for su1 in self.verb_suf1:
                if token.endswith(su1):
                    return token[:-1]

    def verb_t4(self, token):
        """
        stem the present tense prefixes
        """
        if len(token) > 3:
            for pr1 in self.verb_suf1:
                if token.startswith(pr1):
                    return token[1:]
            if token.startswith("\u064A"):
                return token[1:]

    def verb_t5(self, token):
        """
        stem the future tense prefixes
        """
        if len(token) > 4:
            for pr2 in self.verb_pr22:
                if token.startswith(pr2):
                    return token[2:]
            for pr2 in self.verb_pr2:
                if token.startswith(pr2):
                    return token[2:]

    def verb_t6(self, token):
        """
        stem the imperative tense prefixes
        """
        if len(token) > 4:
            for pr3 in self.verb_pr33:
                if token.startswith(pr3):
                    return token[2:]

        return token

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_stata_builtins.py ===
"""
    pygments.lexers._stata_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builtins for Stata

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


builtins_special = (
    "if", "in", "using", "replace", "by", "gen", "generate"
)

builtins_base = (
    "if", "else", "in", "foreach", "for", "forv", "forva",
    "forval", "forvalu", "forvalue", "forvalues", "by", "bys",
    "bysort", "quietly", "qui", "about", "ac",
    "ac_7", "acprplot", "acprplot_7", "adjust", "ado", "adopath",
    "adoupdate", "alpha", "ameans", "an", "ano", "anov", "anova",
    "anova_estat", "anova_terms", "anovadef", "aorder", "ap", "app",
    "appe", "appen", "append", "arch", "arch_dr", "arch_estat",
    "arch_p", "archlm", "areg", "areg_p", "args", "arima",
    "arima_dr", "arima_estat", "arima_p", "as", "asmprobit",
    "asmprobit_estat", "asmprobit_lf", "asmprobit_mfx__dlg",
    "asmprobit_p", "ass", "asse", "asser", "assert", "avplot",
    "avplot_7", "avplots", "avplots_7", "bcskew0", "bgodfrey",
    "binreg", "bip0_lf", "biplot", "bipp_lf", "bipr_lf",
    "bipr_p", "biprobit", "bitest", "bitesti", "bitowt", "blogit",
    "bmemsize", "boot", "bootsamp", "bootstrap", "bootstrap_8",
    "boxco_l", "boxco_p", "boxcox", "boxcox_6", "boxcox_p",
    "bprobit", "br", "break", "brier", "bro", "brow", "brows",
    "browse", "brr", "brrstat", "bs", "bs_7", "bsampl_w",
    "bsample", "bsample_7", "bsqreg", "bstat", "bstat_7", "bstat_8",
    "bstrap", "bstrap_7", "ca", "ca_estat", "ca_p", "cabiplot",
    "camat", "canon", "canon_8", "canon_8_p", "canon_estat",
    "canon_p", "cap", "caprojection", "capt", "captu", "captur",
    "capture", "cat", "cc", "cchart", "cchart_7", "cci",
    "cd", "censobs_table", "centile", "cf", "char", "chdir",
    "checkdlgfiles", "checkestimationsample", "checkhlpfiles",
    "checksum", "chelp", "ci", "cii", "cl", "class", "classutil",
    "clear", "cli", "clis", "clist", "clo", "clog", "clog_lf",
    "clog_p", "clogi", "clogi_sw", "clogit", "clogit_lf",
    "clogit_p", "clogitp", "clogl_sw", "cloglog", "clonevar",
    "clslistarray", "cluster", "cluster_measures", "cluster_stop",
    "cluster_tree", "cluster_tree_8", "clustermat", "cmdlog",
    "cnr", "cnre", "cnreg", "cnreg_p", "cnreg_sw", "cnsreg",
    "codebook", "collaps4", "collapse", "colormult_nb",
    "colormult_nw", "compare", "compress", "conf", "confi",
    "confir", "confirm", "conren", "cons", "const", "constr",
    "constra", "constrai", "constrain", "constraint", "continue",
    "contract", "copy", "copyright", "copysource", "cor", "corc",
    "corr", "corr2data", "corr_anti", "corr_kmo", "corr_smc",
    "corre", "correl", "correla", "correlat", "correlate",
    "corrgram", "cou", "coun", "count", "cox", "cox_p", "cox_sw",
    "coxbase", "coxhaz", "coxvar", "cprplot", "cprplot_7",
    "crc", "cret", "cretu", "cretur", "creturn", "cross", "cs",
    "cscript", "cscript_log", "csi", "ct", "ct_is", "ctset",
    "ctst_5", "ctst_st", "cttost", "cumsp", "cumsp_7", "cumul",
    "cusum", "cusum_7", "cutil", "d", "datasig", "datasign",
    "datasigna", "datasignat", "datasignatu", "datasignatur",
    "datasignature", "datetof", "db", "dbeta", "de", "dec",
    "deco", "decod", "decode", "deff", "des", "desc", "descr",
    "descri", "describ", "describe", "destring", "dfbeta",
    "dfgls", "dfuller", "di", "di_g", "dir", "dirstats", "dis",
    "discard", "disp", "disp_res", "disp_s", "displ", "displa",
    "display", "distinct", "do", "doe", "doed", "doedi",
    "doedit", "dotplot", "dotplot_7", "dprobit", "drawnorm",
    "drop", "ds", "ds_util", "dstdize", "duplicates", "durbina",
    "dwstat", "dydx", "e", "ed", "edi", "edit", "egen",
    "eivreg", "emdef", "end", "en", "enc", "enco", "encod", "encode",
    "eq", "erase", "ereg", "ereg_lf", "ereg_p", "ereg_sw",
    "ereghet", "ereghet_glf", "ereghet_glf_sh", "ereghet_gp",
    "ereghet_ilf", "ereghet_ilf_sh", "ereghet_ip", "eret",
    "eretu", "eretur", "ereturn", "err", "erro", "error", "est",
    "est_cfexist", "est_cfname", "est_clickable", "est_expand",
    "est_hold", "est_table", "est_unhold", "est_unholdok",
    "estat", "estat_default", "estat_summ", "estat_vce_only",
    "esti", "estimates", "etodow", "etof", "etomdy", "ex",
    "exi", "exit", "expand", "expandcl", "fac", "fact", "facto",
    "factor", "factor_estat", "factor_p", "factor_pca_rotated",
    "factor_rotate", "factormat", "fcast", "fcast_compute",
    "fcast_graph", "fdades", "fdadesc", "fdadescr", "fdadescri",
    "fdadescrib", "fdadescribe", "fdasav", "fdasave", "fdause",
    "fh_st", "open", "read", "close",
    "file", "filefilter", "fillin", "find_hlp_file", "findfile",
    "findit", "findit_7", "fit", "fl", "fli", "flis", "flist",
    "for5_0", "form", "forma", "format", "fpredict", "frac_154",
    "frac_adj", "frac_chk", "frac_cox", "frac_ddp", "frac_dis",
    "frac_dv", "frac_in", "frac_mun", "frac_pp", "frac_pq",
    "frac_pv", "frac_wgt", "frac_xo", "fracgen", "fracplot",
    "fracplot_7", "fracpoly", "fracpred", "fron_ex", "fron_hn",
    "fron_p", "fron_tn", "fron_tn2", "frontier", "ftodate", "ftoe",
    "ftomdy", "ftowdate", "g", "gamhet_glf", "gamhet_gp",
    "gamhet_ilf", "gamhet_ip", "gamma", "gamma_d2", "gamma_p",
    "gamma_sw", "gammahet", "gdi_hexagon", "gdi_spokes", "ge",
    "gen", "gene", "gener", "genera", "generat", "generate",
    "genrank", "genstd", "genvmean", "gettoken", "gl", "gladder",
    "gladder_7", "glim_l01", "glim_l02", "glim_l03", "glim_l04",
    "glim_l05", "glim_l06", "glim_l07", "glim_l08", "glim_l09",
    "glim_l10", "glim_l11", "glim_l12", "glim_lf", "glim_mu",
    "glim_nw1", "glim_nw2", "glim_nw3", "glim_p", "glim_v1",
    "glim_v2", "glim_v3", "glim_v4", "glim_v5", "glim_v6",
    "glim_v7", "glm", "glm_6", "glm_p", "glm_sw", "glmpred", "glo",
    "glob", "globa", "global", "glogit", "glogit_8", "glogit_p",
    "gmeans", "gnbre_lf", "gnbreg", "gnbreg_5", "gnbreg_p",
    "gomp_lf", "gompe_sw", "gomper_p", "gompertz", "gompertzhet",
    "gomphet_glf", "gomphet_glf_sh", "gomphet_gp", "gomphet_ilf",
    "gomphet_ilf_sh", "gomphet_ip", "gphdot", "gphpen",
    "gphprint", "gprefs", "gprobi_p", "gprobit", "gprobit_8", "gr",
    "gr7", "gr_copy", "gr_current", "gr_db", "gr_describe",
    "gr_dir", "gr_draw", "gr_draw_replay", "gr_drop", "gr_edit",
    "gr_editviewopts", "gr_example", "gr_example2", "gr_export",
    "gr_print", "gr_qscheme", "gr_query", "gr_read", "gr_rename",
    "gr_replay", "gr_save", "gr_set", "gr_setscheme", "gr_table",
    "gr_undo", "gr_use", "graph", "graph7", "grebar", "greigen",
    "greigen_7", "greigen_8", "grmeanby", "grmeanby_7",
    "gs_fileinfo", "gs_filetype", "gs_graphinfo", "gs_stat",
    "gsort", "gwood", "h", "hadimvo", "hareg", "hausman",
    "haver", "he", "heck_d2", "heckma_p", "heckman", "heckp_lf",
    "heckpr_p", "heckprob", "hel", "help", "hereg", "hetpr_lf",
    "hetpr_p", "hetprob", "hettest", "hexdump", "hilite",
    "hist", "hist_7", "histogram", "hlogit", "hlu", "hmeans",
    "hotel", "hotelling", "hprobit", "hreg", "hsearch", "icd9",
    "icd9_ff", "icd9p", "iis", "impute", "imtest", "inbase",
    "include", "inf", "infi", "infil", "infile", "infix", "inp",
    "inpu", "input", "ins", "insheet", "insp", "inspe",
    "inspec", "inspect", "integ", "inten", "intreg", "intreg_7",
    "intreg_p", "intrg2_ll", "intrg_ll", "intrg_ll2", "ipolate",
    "iqreg", "ir", "irf", "irf_create", "irfm", "iri", "is_svy",
    "is_svysum", "isid", "istdize", "ivprob_1_lf", "ivprob_lf",
    "ivprobit", "ivprobit_p", "ivreg", "ivreg_footnote",
    "ivtob_1_lf", "ivtob_lf", "ivtobit", "ivtobit_p", "jackknife",
    "jacknife", "jknife", "jknife_6", "jknife_8", "jkstat",
    "joinby", "kalarma1", "kap", "kap_3", "kapmeier", "kappa",
    "kapwgt", "kdensity", "kdensity_7", "keep", "ksm", "ksmirnov",
    "ktau", "kwallis", "l", "la", "lab", "labe", "label",
    "labelbook", "ladder", "levels", "levelsof", "leverage",
    "lfit", "lfit_p", "li", "lincom", "line", "linktest",
    "lis", "list", "lloghet_glf", "lloghet_glf_sh", "lloghet_gp",
    "lloghet_ilf", "lloghet_ilf_sh", "lloghet_ip", "llogi_sw",
    "llogis_p", "llogist", "llogistic", "llogistichet",
    "lnorm_lf", "lnorm_sw", "lnorma_p", "lnormal", "lnormalhet",
    "lnormhet_glf", "lnormhet_glf_sh", "lnormhet_gp",
    "lnormhet_ilf", "lnormhet_ilf_sh", "lnormhet_ip", "lnskew0",
    "loadingplot", "loc", "loca", "local", "log", "logi",
    "logis_lf", "logistic", "logistic_p", "logit", "logit_estat",
    "logit_p", "loglogs", "logrank", "loneway", "lookfor",
    "lookup", "lowess", "lowess_7", "lpredict", "lrecomp", "lroc",
    "lroc_7", "lrtest", "ls", "lsens", "lsens_7", "lsens_x",
    "lstat", "ltable", "ltable_7", "ltriang", "lv", "lvr2plot",
    "lvr2plot_7", "m", "ma", "mac", "macr", "macro", "makecns",
    "man", "manova", "manova_estat", "manova_p", "manovatest",
    "mantel", "mark", "markin", "markout", "marksample", "mat",
    "mat_capp", "mat_order", "mat_put_rr", "mat_rapp", "mata",
    "mata_clear", "mata_describe", "mata_drop", "mata_matdescribe",
    "mata_matsave", "mata_matuse", "mata_memory", "mata_mlib",
    "mata_mosave", "mata_rename", "mata_which", "matalabel",
    "matcproc", "matlist", "matname", "matr", "matri",
    "matrix", "matrix_input__dlg", "matstrik", "mcc", "mcci",
    "md0_", "md1_", "md1debug_", "md2_", "md2debug_", "mds",
    "mds_estat", "mds_p", "mdsconfig", "mdslong", "mdsmat",
    "mdsshepard", "mdytoe", "mdytof", "me_derd", "mean",
    "means", "median", "memory", "memsize", "meqparse", "mer",
    "merg", "merge", "mfp", "mfx", "mhelp", "mhodds", "minbound",
    "mixed_ll", "mixed_ll_reparm", "mkassert", "mkdir",
    "mkmat", "mkspline", "ml", "ml_5", "ml_adjs", "ml_bhhhs",
    "ml_c_d", "ml_check", "ml_clear", "ml_cnt", "ml_debug",
    "ml_defd", "ml_e0", "ml_e0_bfgs", "ml_e0_cycle", "ml_e0_dfp",
    "ml_e0i", "ml_e1", "ml_e1_bfgs", "ml_e1_bhhh", "ml_e1_cycle",
    "ml_e1_dfp", "ml_e2", "ml_e2_cycle", "ml_ebfg0", "ml_ebfr0",
    "ml_ebfr1", "ml_ebh0q", "ml_ebhh0", "ml_ebhr0", "ml_ebr0i",
    "ml_ecr0i", "ml_edfp0", "ml_edfr0", "ml_edfr1", "ml_edr0i",
    "ml_eds", "ml_eer0i", "ml_egr0i", "ml_elf", "ml_elf_bfgs",
    "ml_elf_bhhh", "ml_elf_cycle", "ml_elf_dfp", "ml_elfi",
    "ml_elfs", "ml_enr0i", "ml_enrr0", "ml_erdu0", "ml_erdu0_bfgs",
    "ml_erdu0_bhhh", "ml_erdu0_bhhhq", "ml_erdu0_cycle",
    "ml_erdu0_dfp", "ml_erdu0_nrbfgs", "ml_exde", "ml_footnote",
    "ml_geqnr", "ml_grad0", "ml_graph", "ml_hbhhh", "ml_hd0",
    "ml_hold", "ml_init", "ml_inv", "ml_log", "ml_max",
    "ml_mlout", "ml_mlout_8", "ml_model", "ml_nb0", "ml_opt",
    "ml_p", "ml_plot", "ml_query", "ml_rdgrd", "ml_repor",
    "ml_s_e", "ml_score", "ml_searc", "ml_technique", "ml_unhold",
    "mleval", "mlf_", "mlmatbysum", "mlmatsum", "mlog", "mlogi",
    "mlogit", "mlogit_footnote", "mlogit_p", "mlopts", "mlsum",
    "mlvecsum", "mnl0_", "mor", "more", "mov", "move", "mprobit",
    "mprobit_lf", "mprobit_p", "mrdu0_", "mrdu1_", "mvdecode",
    "mvencode", "mvreg", "mvreg_estat", "n", "nbreg",
    "nbreg_al", "nbreg_lf", "nbreg_p", "nbreg_sw", "nestreg", "net",
    "newey", "newey_7", "newey_p", "news", "nl", "nl_7", "nl_9",
    "nl_9_p", "nl_p", "nl_p_7", "nlcom", "nlcom_p", "nlexp2",
    "nlexp2_7", "nlexp2a", "nlexp2a_7", "nlexp3", "nlexp3_7",
    "nlgom3", "nlgom3_7", "nlgom4", "nlgom4_7", "nlinit", "nllog3",
    "nllog3_7", "nllog4", "nllog4_7", "nlog_rd", "nlogit",
    "nlogit_p", "nlogitgen", "nlogittree", "nlpred", "no",
    "nobreak", "noi", "nois", "noisi", "noisil", "noisily", "note",
    "notes", "notes_dlg", "nptrend", "numlabel", "numlist", "odbc",
    "old_ver", "olo", "olog", "ologi", "ologi_sw", "ologit",
    "ologit_p", "ologitp", "on", "one", "onew", "onewa", "oneway",
    "op_colnm", "op_comp", "op_diff", "op_inv", "op_str", "opr",
    "opro", "oprob", "oprob_sw", "oprobi", "oprobi_p", "oprobit",
    "oprobitp", "opts_exclusive", "order", "orthog", "orthpoly",
    "ou", "out", "outf", "outfi", "outfil", "outfile", "outs",
    "outsh", "outshe", "outshee", "outsheet", "ovtest", "pac",
    "pac_7", "palette", "parse", "parse_dissim", "pause", "pca",
    "pca_8", "pca_display", "pca_estat", "pca_p", "pca_rotate",
    "pcamat", "pchart", "pchart_7", "pchi", "pchi_7", "pcorr",
    "pctile", "pentium", "pergram", "pergram_7", "permute",
    "permute_8", "personal", "peto_st", "pkcollapse", "pkcross",
    "pkequiv", "pkexamine", "pkexamine_7", "pkshape", "pksumm",
    "pksumm_7", "pl", "plo", "plot", "plugin", "pnorm",
    "pnorm_7", "poisgof", "poiss_lf", "poiss_sw", "poisso_p",
    "poisson", "poisson_estat", "post", "postclose", "postfile",
    "postutil", "pperron", "pr", "prais", "prais_e", "prais_e2",
    "prais_p", "predict", "predictnl", "preserve", "print",
    "pro", "prob", "probi", "probit", "probit_estat", "probit_p",
    "proc_time", "procoverlay", "procrustes", "procrustes_estat",
    "procrustes_p", "profiler", "prog", "progr", "progra",
    "program", "prop", "proportion", "prtest", "prtesti", "pwcorr",
    "pwd", "q", "s", "qby", "qbys", "qchi", "qchi_7", "qladder",
    "qladder_7", "qnorm", "qnorm_7", "qqplot", "qqplot_7", "qreg",
    "qreg_c", "qreg_p", "qreg_sw", "qu", "quadchk", "quantile",
    "quantile_7", "que", "quer", "query", "range", "ranksum",
    "ratio", "rchart", "rchart_7", "rcof", "recast", "reclink",
    "recode", "reg", "reg3", "reg3_p", "regdw", "regr", "regre",
    "regre_p2", "regres", "regres_p", "regress", "regress_estat",
    "regriv_p", "remap", "ren", "rena", "renam", "rename",
    "renpfix", "repeat", "replace", "report", "reshape",
    "restore", "ret", "retu", "retur", "return", "rm", "rmdir",
    "robvar", "roccomp", "roccomp_7", "roccomp_8", "rocf_lf",
    "rocfit", "rocfit_8", "rocgold", "rocplot", "rocplot_7",
    "roctab", "roctab_7", "rolling", "rologit", "rologit_p",
    "rot", "rota", "rotat", "rotate", "rotatemat", "rreg",
    "rreg_p", "ru", "run", "runtest", "rvfplot", "rvfplot_7",
    "rvpplot", "rvpplot_7", "sa", "safesum", "sample",
    "sampsi", "sav", "save", "savedresults", "saveold", "sc",
    "sca", "scal", "scala", "scalar", "scatter", "scm_mine",
    "sco", "scob_lf", "scob_p", "scobi_sw", "scobit", "scor",
    "score", "scoreplot", "scoreplot_help", "scree", "screeplot",
    "screeplot_help", "sdtest", "sdtesti", "se", "search",
    "separate", "seperate", "serrbar", "serrbar_7", "serset", "set",
    "set_defaults", "sfrancia", "sh", "she", "shel", "shell",
    "shewhart", "shewhart_7", "signestimationsample", "signrank",
    "signtest", "simul", "simul_7", "simulate", "simulate_8",
    "sktest", "sleep", "slogit", "slogit_d2", "slogit_p", "smooth",
    "snapspan", "so", "sor", "sort", "spearman", "spikeplot",
    "spikeplot_7", "spikeplt", "spline_x", "split", "sqreg",
    "sqreg_p", "sret", "sretu", "sretur", "sreturn", "ssc", "st",
    "st_ct", "st_hc", "st_hcd", "st_hcd_sh", "st_is", "st_issys",
    "st_note", "st_promo", "st_set", "st_show", "st_smpl",
    "st_subid", "stack", "statsby", "statsby_8", "stbase", "stci",
    "stci_7", "stcox", "stcox_estat", "stcox_fr", "stcox_fr_ll",
    "stcox_p", "stcox_sw", "stcoxkm", "stcoxkm_7", "stcstat",
    "stcurv", "stcurve", "stcurve_7", "stdes", "stem", "stepwise",
    "stereg", "stfill", "stgen", "stir", "stjoin", "stmc", "stmh",
    "stphplot", "stphplot_7", "stphtest", "stphtest_7",
    "stptime", "strate", "strate_7", "streg", "streg_sw", "streset",
    "sts", "sts_7", "stset", "stsplit", "stsum", "sttocc",
    "sttoct", "stvary", "stweib", "su", "suest", "suest_8",
    "sum", "summ", "summa", "summar", "summari", "summariz",
    "summarize", "sunflower", "sureg", "survcurv", "survsum",
    "svar", "svar_p", "svmat", "svy", "svy_disp", "svy_dreg",
    "svy_est", "svy_est_7", "svy_estat", "svy_get", "svy_gnbreg_p",
    "svy_head", "svy_header", "svy_heckman_p", "svy_heckprob_p",
    "svy_intreg_p", "svy_ivreg_p", "svy_logistic_p", "svy_logit_p",
    "svy_mlogit_p", "svy_nbreg_p", "svy_ologit_p", "svy_oprobit_p",
    "svy_poisson_p", "svy_probit_p", "svy_regress_p", "svy_sub",
    "svy_sub_7", "svy_x", "svy_x_7", "svy_x_p", "svydes",
    "svydes_8", "svygen", "svygnbreg", "svyheckman", "svyheckprob",
    "svyintreg", "svyintreg_7", "svyintrg", "svyivreg", "svylc",
    "svylog_p", "svylogit", "svymarkout", "svymarkout_8",
    "svymean", "svymlog", "svymlogit", "svynbreg", "svyolog",
    "svyologit", "svyoprob", "svyoprobit", "svyopts",
    "svypois", "svypois_7", "svypoisson", "svyprobit", "svyprobt",
    "svyprop", "svyprop_7", "svyratio", "svyreg", "svyreg_p",
    "svyregress", "svyset", "svyset_7", "svyset_8", "svytab",
    "svytab_7", "svytest", "svytotal", "sw", "sw_8", "swcnreg",
    "swcox", "swereg", "swilk", "swlogis", "swlogit",
    "swologit", "swoprbt", "swpois", "swprobit", "swqreg",
    "swtobit", "swweib", "symmetry", "symmi", "symplot",
    "symplot_7", "syntax", "sysdescribe", "sysdir", "sysuse",
    "szroeter", "ta", "tab", "tab1", "tab2", "tab_or", "tabd",
    "tabdi", "tabdis", "tabdisp", "tabi", "table", "tabodds",
    "tabodds_7", "tabstat", "tabu", "tabul", "tabula", "tabulat",
    "tabulate", "te", "tempfile", "tempname", "tempvar", "tes",
    "test", "testnl", "testparm", "teststd", "tetrachoric",
    "time_it", "timer", "tis", "tob", "tobi", "tobit", "tobit_p",
    "tobit_sw", "token", "tokeni", "tokeniz", "tokenize",
    "tostring", "total", "translate", "translator", "transmap",
    "treat_ll", "treatr_p", "treatreg", "trim", "trnb_cons",
    "trnb_mean", "trpoiss_d2", "trunc_ll", "truncr_p", "truncreg",
    "tsappend", "tset", "tsfill", "tsline", "tsline_ex",
    "tsreport", "tsrevar", "tsrline", "tsset", "tssmooth",
    "tsunab", "ttest", "ttesti", "tut_chk", "tut_wait", "tutorial",
    "tw", "tware_st", "two", "twoway", "twoway__fpfit_serset",
    "twoway__function_gen", "twoway__histogram_gen",
    "twoway__ipoint_serset", "twoway__ipoints_serset",
    "twoway__kdensity_gen", "twoway__lfit_serset",
    "twoway__normgen_gen", "twoway__pci_serset",
    "twoway__qfit_serset", "twoway__scatteri_serset",
    "twoway__sunflower_gen", "twoway_ksm_serset", "ty", "typ",
    "type", "typeof", "u", "unab", "unabbrev", "unabcmd",
    "update", "us", "use", "uselabel", "var", "var_mkcompanion",
    "var_p", "varbasic", "varfcast", "vargranger", "varirf",
    "varirf_add", "varirf_cgraph", "varirf_create", "varirf_ctable",
    "varirf_describe", "varirf_dir", "varirf_drop", "varirf_erase",
    "varirf_graph", "varirf_ograph", "varirf_rename", "varirf_set",
    "varirf_table", "varlist", "varlmar", "varnorm", "varsoc",
    "varstable", "varstable_w", "varstable_w2", "varwle",
    "vce", "vec", "vec_fevd", "vec_mkphi", "vec_p", "vec_p_w",
    "vecirf_create", "veclmar", "veclmar_w", "vecnorm",
    "vecnorm_w", "vecrank", "vecstable", "verinst", "vers",
    "versi", "versio", "version", "view", "viewsource", "vif",
    "vwls", "wdatetof", "webdescribe", "webseek", "webuse",
    "weib1_lf", "weib2_lf", "weib_lf", "weib_lf0", "weibhet_glf",
    "weibhet_glf_sh", "weibhet_glfa", "weibhet_glfa_sh",
    "weibhet_gp", "weibhet_ilf", "weibhet_ilf_sh", "weibhet_ilfa",
    "weibhet_ilfa_sh", "weibhet_ip", "weibu_sw", "weibul_p",
    "weibull", "weibull_c", "weibull_s", "weibullhet",
    "wh", "whelp", "whi", "which", "whil", "while", "wilc_st",
    "wilcoxon", "win", "wind", "windo", "window", "winexec",
    "wntestb", "wntestb_7", "wntestq", "xchart", "xchart_7",
    "xcorr", "xcorr_7", "xi", "xi_6", "xmlsav", "xmlsave",
    "xmluse", "xpose", "xsh", "xshe", "xshel", "xshell",
    "xt_iis", "xt_tis", "xtab_p", "xtabond", "xtbin_p",
    "xtclog", "xtcloglog", "xtcloglog_8", "xtcloglog_d2",
    "xtcloglog_pa_p", "xtcloglog_re_p", "xtcnt_p", "xtcorr",
    "xtdata", "xtdes", "xtfront_p", "xtfrontier", "xtgee",
    "xtgee_elink", "xtgee_estat", "xtgee_makeivar", "xtgee_p",
    "xtgee_plink", "xtgls", "xtgls_p", "xthaus", "xthausman",
    "xtht_p", "xthtaylor", "xtile", "xtint_p", "xtintreg",
    "xtintreg_8", "xtintreg_d2", "xtintreg_p", "xtivp_1",
    "xtivp_2", "xtivreg", "xtline", "xtline_ex", "xtlogit",
    "xtlogit_8", "xtlogit_d2", "xtlogit_fe_p", "xtlogit_pa_p",
    "xtlogit_re_p", "xtmixed", "xtmixed_estat", "xtmixed_p",
    "xtnb_fe", "xtnb_lf", "xtnbreg", "xtnbreg_pa_p",
    "xtnbreg_refe_p", "xtpcse", "xtpcse_p", "xtpois", "xtpoisson",
    "xtpoisson_d2", "xtpoisson_pa_p", "xtpoisson_refe_p", "xtpred",
    "xtprobit", "xtprobit_8", "xtprobit_d2", "xtprobit_re_p",
    "xtps_fe", "xtps_lf", "xtps_ren", "xtps_ren_8", "xtrar_p",
    "xtrc", "xtrc_p", "xtrchh", "xtrefe_p", "xtreg", "xtreg_be",
    "xtreg_fe", "xtreg_ml", "xtreg_pa_p", "xtreg_re",
    "xtregar", "xtrere_p", "xtset", "xtsf_ll", "xtsf_llti",
    "xtsum", "xttab", "xttest0", "xttobit", "xttobit_8",
    "xttobit_p", "xttrans", "yx", "yxview__barlike_draw",
    "yxview_area_draw", "yxview_bar_draw", "yxview_dot_draw",
    "yxview_dropline_draw", "yxview_function_draw",
    "yxview_iarrow_draw", "yxview_ilabels_draw",
    "yxview_normal_draw", "yxview_pcarrow_draw",
    "yxview_pcbarrow_draw", "yxview_pccapsym_draw",
    "yxview_pcscatter_draw", "yxview_pcspike_draw",
    "yxview_rarea_draw", "yxview_rbar_draw", "yxview_rbarm_draw",
    "yxview_rcap_draw", "yxview_rcapsym_draw",
    "yxview_rconnected_draw", "yxview_rline_draw",
    "yxview_rscatter_draw", "yxview_rspike_draw",
    "yxview_spike_draw", "yxview_sunflower_draw", "zap_s", "zinb",
    "zinb_llf", "zinb_plf", "zip", "zip_llf", "zip_p", "zip_plf",
    "zt_ct_5", "zt_hc_5", "zt_hcd_5", "zt_is_5", "zt_iss_5",
    "zt_sho_5", "zt_smp_5", "ztbase_5", "ztcox_5", "ztdes_5",
    "ztereg_5", "ztfill_5", "ztgen_5", "ztir_5", "ztjoin_5", "ztnb",
    "ztnb_p", "ztp", "ztp_p", "zts_5", "ztset_5", "ztspli_5",
    "ztsum_5", "zttoct_5", "ztvary_5", "ztweib_5"
)



builtins_functions = (
    "abbrev", "abs", "acos", "acosh", "asin", "asinh", "atan",
    "atan2", "atanh", "autocode", "betaden", "binomial",
    "binomialp", "binomialtail", "binormal", "bofd",
    "byteorder", "c", "_caller", "cauchy", "cauchyden",
    "cauchytail", "Cdhms", "ceil", "char", "chi2", "chi2den",
    "chi2tail", "Chms", "chop", "cholesky", "clip", "Clock",
    "clock", "cloglog", "Cmdyhms", "Cofc", "cofC", "Cofd", "cofd",
    "coleqnumb", "collatorlocale", "collatorversion",
    "colnfreeparms", "colnumb", "colsof", "comb", "cond", "corr",
    "cos", "cosh", "daily", "date", "day", "det", "dgammapda",
    "dgammapdada", "dgammapdadx", "dgammapdx", "dgammapdxdx",
    "dhms", "diag", "diag0cnt", "digamma", "dofb", "dofC", "dofc",
    "dofh", "dofm", "dofq", "dofw", "dofy", "dow", "doy",
    "dunnettprob", "e", "el", "esample", "epsdouble", "epsfloat",
    "exp", "expm1", "exponential", "exponentialden",
    "exponentialtail", "F", "Fden", "fileexists", "fileread",
    "filereaderror", "filewrite", "float", "floor", "fmtwidth",
    "frval", "_frval", "Ftail", "gammaden", "gammap", "gammaptail",
    "get", "hadamard", "halfyear", "halfyearly", "has_eprop", "hh",
    "hhC", "hms", "hofd", "hours", "hypergeometric",
    "hypergeometricp", "I", "ibeta", "ibetatail", "igaussian",
    "igaussianden", "igaussiantail", "indexnot", "inlist",
    "inrange", "int", "inv", "invbinomial", "invbinomialtail",
    "invcauchy", "invcauchytail", "invchi2", "invchi2tail",
    "invcloglog", "invdunnettprob", "invexponential",
    "invexponentialtail", "invF", "invFtail", "invgammap",
    "invgammaptail", "invibeta", "invibetatail", "invigaussian",
    "invigaussiantail", "invlaplace", "invlaplacetail",
    "invlogisticp", "invlogisticsp", "invlogisticmsp",
    "invlogistictailp", "invlogistictailsp", "invlogistictailmsp",
    "invlogit", "invnbinomial", "invnbinomialtail", "invnchi2",
    "invnchi2tail", "invnF", "invnFtail", "invnibeta",
    "invnormal", "invnt", "invnttail", "invpoisson",
    "invpoissontail", "invsym", "invt", "invttail", "invtukeyprob",
    "invweibullabp", "invweibullabgp", "invweibullphabp",
    "invweibullphabgp", "invweibullphtailabp",
    "invweibullphtailabgp", "invweibulltailabp",
    "invweibulltailabgp", "irecode", "issymmetric", "J", "laplace",
    "laplaceden", "laplacetail", "ln", "ln1m", "ln1p", "lncauchyden",
    "lnfactorial", "lngamma", "lnigammaden", "lnigaussianden",
    "lniwishartden", "lnlaplaceden", "lnmvnormalden", "lnnormal",
    "lnnormalden", "lnnormaldenxs", "lnnormaldenxms", "lnwishartden",
    "log", "log10", "log1m", "log1p", "logisticx", "logisticsx",
    "logisticmsx", "logisticdenx", "logisticdensx", "logisticdenmsx",
    "logistictailx", "logistictailsx", "logistictailmsx", "logit",
    "matmissing", "matrix", "matuniform", "max", "maxbyte",
    "maxdouble", "maxfloat", "maxint", "maxlong", "mdy", "mdyhms",
    "mi", "min", "minbyte", "mindouble", "minfloat", "minint",
    "minlong", "minutes", "missing", "mm", "mmC", "mod", "mofd",
    "month", "monthly", "mreldif", "msofhours", "msofminutes",
    "msofseconds", "nbetaden", "nbinomial", "nbinomialp",
    "nbinomialtail", "nchi2", "nchi2den", "nchi2tail", "nF",
    "nFden", "nFtail", "nibeta", "normal", "normalden",
    "normaldenxs", "normaldenxms", "npnchi2", "npnF", "npnt",
    "nt", "ntden", "nttail", "nullmat", "plural", "plurals1",
    "poisson", "poissonp", "poissontail", "qofd", "quarter",
    "quarterly", "r", "rbeta", "rbinomial", "rcauchy", "rchi2",
    "recode", "real", "regexm", "regexr", "regexs", "reldif",
    "replay", "return", "rexponential", "rgamma", "rhypergeometric",
    "rigaussian", "rlaplace", "rlogistic", "rlogistics",
    "rlogisticms", "rnbinomial", "rnormal", "rnormalm", "rnormalms",
    "round", "roweqnumb", "rownfreeparms", "rownumb", "rowsof",
    "rpoisson", "rt", "runiform", "runiformab", "runiformint",
    "rweibullab", "rweibullabg", "rweibullphab", "rweibullphabg",
    "s", "scalar", "seconds", "sign", "sin", "sinh",
    "smallestdouble", "soundex", "soundex_nara", "sqrt", "ss",
    "ssC", "strcat", "strdup", "string", "stringns", "stritrim",
    "strlen", "strlower", "strltrim", "strmatch", "strofreal",
    "strofrealns", "strpos", "strproper", "strreverse", "strrpos",
    "strrtrim", "strtoname", "strtrim", "strupper", "subinstr",
    "subinword", "substr", "sum", "sweep", "t", "tan", "tanh",
    "tC", "tc", "td", "tden", "th", "tin", "tm", "tobytes", "tq",
    "trace", "trigamma", "trunc", "ttail", "tukeyprob", "tw",
    "twithin", "uchar", "udstrlen", "udsubstr", "uisdigit",
    "uisletter", "ustrcompare", "ustrfix", "ustrfrom",
    "ustrinvalidcnt", "ustrleft", "ustrlen", "ustrlower",
    "ustrltrim", "ustrnormalize", "ustrpos", "ustrregexm",
    "ustrregexra", "ustrregexrf", "ustrregexs", "ustrreverse",
    "ustrright", "ustrrpos", "ustrrtrim", "ustrsortkey",
    "ustrtitle", "ustrto", "ustrtohex", "ustrtoname",
    "ustrtrim", "ustrunescape", "ustrupper", "ustrword",
    "ustrwordcount", "usubinstr", "usubstr", "vec", "vecdiag",
    "week", "weekly", "weibullabx", "weibullabgx", "weibulldenabx",
    "weibulldenabgx", "weibullphabx", "weibullphabgx",
    "weibullphdenabx", "weibullphdenabgx", "weibullphtailabx",
    "weibullphtailabgx", "weibulltailabx", "weibulltailabgx",
    "wofd", "word", "wordbreaklocale", "wordcount",
    "year", "yearly", "yh", "ym", "yofd", "yq", "yw" 
)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\locations\__init__.py ===
import functools
import logging
import os
import pathlib
import sys
import sysconfig
from typing import Any, Dict, Generator, Optional, Tuple

from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.virtualenv import running_under_virtualenv

from . import _sysconfig
from .base import (
    USER_CACHE_DIR,
    get_major_minor_version,
    get_src_prefix,
    is_osx_framework,
    site_packages,
    user_site,
)

__all__ = [
    "USER_CACHE_DIR",
    "get_bin_prefix",
    "get_bin_user",
    "get_major_minor_version",
    "get_platlib",
    "get_purelib",
    "get_scheme",
    "get_src_prefix",
    "site_packages",
    "user_site",
]


logger = logging.getLogger(__name__)


_PLATLIBDIR: str = getattr(sys, "platlibdir", "lib")

_USE_SYSCONFIG_DEFAULT = sys.version_info >= (3, 10)


def _should_use_sysconfig() -> bool:
    """This function determines the value of _USE_SYSCONFIG.

    By default, pip uses sysconfig on Python 3.10+.
    But Python distributors can override this decision by setting:
        sysconfig._PIP_USE_SYSCONFIG = True / False
    Rationale in https://github.com/pypa/pip/issues/10647

    This is a function for testability, but should be constant during any one
    run.
    """
    return bool(getattr(sysconfig, "_PIP_USE_SYSCONFIG", _USE_SYSCONFIG_DEFAULT))


_USE_SYSCONFIG = _should_use_sysconfig()

if not _USE_SYSCONFIG:
    # Import distutils lazily to avoid deprecation warnings,
    # but import it soon enough that it is in memory and available during
    # a pip reinstall.
    from . import _distutils

# Be noisy about incompatibilities if this platforms "should" be using
# sysconfig, but is explicitly opting out and using distutils instead.
if _USE_SYSCONFIG_DEFAULT and not _USE_SYSCONFIG:
    _MISMATCH_LEVEL = logging.WARNING
else:
    _MISMATCH_LEVEL = logging.DEBUG


def _looks_like_bpo_44860() -> bool:
    """The resolution to bpo-44860 will change this incorrect platlib.

    See <https://bugs.python.org/issue44860>.
    """
    from distutils.command.install import INSTALL_SCHEMES

    try:
        unix_user_platlib = INSTALL_SCHEMES["unix_user"]["platlib"]
    except KeyError:
        return False
    return unix_user_platlib == "$usersite"


def _looks_like_red_hat_patched_platlib_purelib(scheme: Dict[str, str]) -> bool:
    platlib = scheme["platlib"]
    if "/$platlibdir/" in platlib:
        platlib = platlib.replace("/$platlibdir/", f"/{_PLATLIBDIR}/")
    if "/lib64/" not in platlib:
        return False
    unpatched = platlib.replace("/lib64/", "/lib/")
    return unpatched.replace("$platbase/", "$base/") == scheme["purelib"]


@functools.lru_cache(maxsize=None)
def _looks_like_red_hat_lib() -> bool:
    """Red Hat patches platlib in unix_prefix and unix_home, but not purelib.

    This is the only way I can see to tell a Red Hat-patched Python.
    """
    from distutils.command.install import INSTALL_SCHEMES

    return all(
        k in INSTALL_SCHEMES
        and _looks_like_red_hat_patched_platlib_purelib(INSTALL_SCHEMES[k])
        for k in ("unix_prefix", "unix_home")
    )


@functools.lru_cache(maxsize=None)
def _looks_like_debian_scheme() -> bool:
    """Debian adds two additional schemes."""
    from distutils.command.install import INSTALL_SCHEMES

    return "deb_system" in INSTALL_SCHEMES and "unix_local" in INSTALL_SCHEMES


@functools.lru_cache(maxsize=None)
def _looks_like_red_hat_scheme() -> bool:
    """Red Hat patches ``sys.prefix`` and ``sys.exec_prefix``.

    Red Hat's ``00251-change-user-install-location.patch`` changes the install
    command's ``prefix`` and ``exec_prefix`` to append ``"/local"``. This is
    (fortunately?) done quite unconditionally, so we create a default command
    object without any configuration to detect this.
    """
    from distutils.command.install import install
    from distutils.dist import Distribution

    cmd: Any = install(Distribution())
    cmd.finalize_options()
    return (
        cmd.exec_prefix == f"{os.path.normpath(sys.exec_prefix)}/local"
        and cmd.prefix == f"{os.path.normpath(sys.prefix)}/local"
    )


@functools.lru_cache(maxsize=None)
def _looks_like_slackware_scheme() -> bool:
    """Slackware patches sysconfig but fails to patch distutils and site.

    Slackware changes sysconfig's user scheme to use ``"lib64"`` for the lib
    path, but does not do the same to the site module.
    """
    if user_site is None:  # User-site not available.
        return False
    try:
        paths = sysconfig.get_paths(scheme="posix_user", expand=False)
    except KeyError:  # User-site not available.
        return False
    return "/lib64/" in paths["purelib"] and "/lib64/" not in user_site


@functools.lru_cache(maxsize=None)
def _looks_like_msys2_mingw_scheme() -> bool:
    """MSYS2 patches distutils and sysconfig to use a UNIX-like scheme.

    However, MSYS2 incorrectly patches sysconfig ``nt`` scheme. The fix is
    likely going to be included in their 3.10 release, so we ignore the warning.
    See msys2/MINGW-packages#9319.

    MSYS2 MINGW's patch uses lowercase ``"lib"`` instead of the usual uppercase,
    and is missing the final ``"site-packages"``.
    """
    paths = sysconfig.get_paths("nt", expand=False)
    return all(
        "Lib" not in p and "lib" in p and not p.endswith("site-packages")
        for p in (paths[key] for key in ("platlib", "purelib"))
    )


def _fix_abiflags(parts: Tuple[str]) -> Generator[str, None, None]:
    ldversion = sysconfig.get_config_var("LDVERSION")
    abiflags = getattr(sys, "abiflags", None)

    # LDVERSION does not end with sys.abiflags. Just return the path unchanged.
    if not ldversion or not abiflags or not ldversion.endswith(abiflags):
        yield from parts
        return

    # Strip sys.abiflags from LDVERSION-based path components.
    for part in parts:
        if part.endswith(ldversion):
            part = part[: (0 - len(abiflags))]
        yield part


@functools.lru_cache(maxsize=None)
def _warn_mismatched(old: pathlib.Path, new: pathlib.Path, *, key: str) -> None:
    issue_url = "https://github.com/pypa/pip/issues/10151"
    message = (
        "Value for %s does not match. Please report this to <%s>"
        "\ndistutils: %s"
        "\nsysconfig: %s"
    )
    logger.log(_MISMATCH_LEVEL, message, key, issue_url, old, new)


def _warn_if_mismatch(old: pathlib.Path, new: pathlib.Path, *, key: str) -> bool:
    if old == new:
        return False
    _warn_mismatched(old, new, key=key)
    return True


@functools.lru_cache(maxsize=None)
def _log_context(
    *,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    prefix: Optional[str] = None,
) -> None:
    parts = [
        "Additional context:",
        "user = %r",
        "home = %r",
        "root = %r",
        "prefix = %r",
    ]

    logger.log(_MISMATCH_LEVEL, "\n".join(parts), user, home, root, prefix)


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> Scheme:
    new = _sysconfig.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )

    warning_contexts = []
    for k in SCHEME_KEYS:
        old_v = pathlib.Path(getattr(old, k))
        new_v = pathlib.Path(getattr(new, k))

        if old_v == new_v:
            continue

        # distutils incorrectly put PyPy packages under ``site-packages/python``
        # in the ``posix_home`` scheme, but PyPy devs said they expect the
        # directory name to be ``pypy`` instead. So we treat this as a bug fix
        # and not warn about it. See bpo-43307 and python/cpython#24628.
        skip_pypy_special_case = (
            sys.implementation.name == "pypy"
            and home is not None
            and k in ("platlib", "purelib")
            and old_v.parent == new_v.parent
            and old_v.name.startswith("python")
            and new_v.name.startswith("pypy")
        )
        if skip_pypy_special_case:
            continue

        # sysconfig's ``osx_framework_user`` does not include ``pythonX.Y`` in
        # the ``include`` value, but distutils's ``headers`` does. We'll let
        # CPython decide whether this is a bug or feature. See bpo-43948.
        skip_osx_framework_user_special_case = (
            user
            and is_osx_framework()
            and k == "headers"
            and old_v.parent.parent == new_v.parent
            and old_v.parent.name.startswith("python")
        )
        if skip_osx_framework_user_special_case:
            continue

        # On Red Hat and derived Linux distributions, distutils is patched to
        # use "lib64" instead of "lib" for platlib.
        if k == "platlib" and _looks_like_red_hat_lib():
            continue

        # On Python 3.9+, sysconfig's posix_user scheme sets platlib against
        # sys.platlibdir, but distutils's unix_user incorrectly coninutes
        # using the same $usersite for both platlib and purelib. This creates a
        # mismatch when sys.platlibdir is not "lib".
        skip_bpo_44860 = (
            user
            and k == "platlib"
            and not WINDOWS
            and sys.version_info >= (3, 9)
            and _PLATLIBDIR != "lib"
            and _looks_like_bpo_44860()
        )
        if skip_bpo_44860:
            continue

        # Slackware incorrectly patches posix_user to use lib64 instead of lib,
        # but not usersite to match the location.
        skip_slackware_user_scheme = (
            user
            and k in ("platlib", "purelib")
            and not WINDOWS
            and _looks_like_slackware_scheme()
        )
        if skip_slackware_user_scheme:
            continue

        # Both Debian and Red Hat patch Python to place the system site under
        # /usr/local instead of /usr. Debian also places lib in dist-packages
        # instead of site-packages, but the /usr/local check should cover it.
        skip_linux_system_special_case = (
            not (user or home or prefix or running_under_virtualenv())
            and old_v.parts[1:3] == ("usr", "local")
            and len(new_v.parts) > 1
            and new_v.parts[1] == "usr"
            and (len(new_v.parts) < 3 or new_v.parts[2] != "local")
            and (_looks_like_red_hat_scheme() or _looks_like_debian_scheme())
        )
        if skip_linux_system_special_case:
            continue

        # MSYS2 MINGW's sysconfig patch does not include the "site-packages"
        # part of the path. This is incorrect and will be fixed in MSYS.
        skip_msys2_mingw_bug = (
            WINDOWS and k in ("platlib", "purelib") and _looks_like_msys2_mingw_scheme()
        )
        if skip_msys2_mingw_bug:
            continue

        # CPython's POSIX install script invokes pip (via ensurepip) against the
        # interpreter located in the source tree, not the install site. This
        # triggers special logic in sysconfig that's not present in distutils.
        # https://github.com/python/cpython/blob/8c21941ddaf/Lib/sysconfig.py#L178-L194
        skip_cpython_build = (
            sysconfig.is_python_build(check_home=True)
            and not WINDOWS
            and k in ("headers", "include", "platinclude")
        )
        if skip_cpython_build:
            continue

        warning_contexts.append((old_v, new_v, f"scheme.{k}"))

    if not warning_contexts:
        return old

    # Check if this path mismatch is caused by distutils config files. Those
    # files will no longer work once we switch to sysconfig, so this raises a
    # deprecation message for them.
    default_old = _distutils.distutils_scheme(
        dist_name,
        user,
        home,
        root,
        isolated,
        prefix,
        ignore_config_files=True,
    )
    if any(default_old[k] != getattr(old, k) for k in SCHEME_KEYS):
        deprecated(
            reason=(
                "Configuring installation scheme with distutils config files "
                "is deprecated and will no longer work in the near future. If you "
                "are using a Homebrew or Linuxbrew Python, please see discussion "
                "at https://github.com/Homebrew/homebrew-core/issues/76621"
            ),
            replacement=None,
            gone_in=None,
        )
        return old

    # Post warnings about this mismatch so user can report them back.
    for old_v, new_v, key in warning_contexts:
        _warn_mismatched(old_v, new_v, key=key)
    _log_context(user=user, home=home, root=root, prefix=prefix)

    return old


def get_bin_prefix() -> str:
    new = _sysconfig.get_bin_prefix()
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_bin_prefix()
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="bin_prefix"):
        _log_context()
    return old


def get_bin_user() -> str:
    return _sysconfig.get_scheme("", user=True).scripts


def _looks_like_deb_system_dist_packages(value: str) -> bool:
    """Check if the value is Debian's APT-controlled dist-packages.

    Debian's ``distutils.sysconfig.get_python_lib()`` implementation returns the
    default package path controlled by APT, but does not patch ``sysconfig`` to
    do the same. This is similar to the bug worked around in ``get_scheme()``,
    but here the default is ``deb_system`` instead of ``unix_local``. Ultimately
    we can't do anything about this Debian bug, and this detection allows us to
    skip the warning when needed.
    """
    if not _looks_like_debian_scheme():
        return False
    if value == "/usr/lib/python3/dist-packages":
        return True
    return False


def get_purelib() -> str:
    """Return the default pure-Python lib location."""
    new = _sysconfig.get_purelib()
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_purelib()
    if _looks_like_deb_system_dist_packages(old):
        return old
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="purelib"):
        _log_context()
    return old


def get_platlib() -> str:
    """Return the default platform-shared lib location."""
    new = _sysconfig.get_platlib()
    if _USE_SYSCONFIG:
        return new

    from . import _distutils

    old = _distutils.get_platlib()
    if _looks_like_deb_system_dist_packages(old):
        return old
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="platlib"):
        _log_context()
    return old

# === NexusCore/openenv\Lib\site-packages\zipp\__init__.py ===
"""
A Path-like interface for zipfiles.

This codebase is shared between zipfile.Path in the stdlib
and zipp in PyPI. See
https://github.com/python/importlib_metadata/wiki/Development-Methodology
for more detail.
"""

import functools
import io
import itertools
import pathlib
import posixpath
import re
import stat
import sys
import zipfile

from ._functools import save_method_args
from .compat.py310 import text_encoding
from .glob import Translator

__all__ = ['Path']


def _parents(path):
    """
    Given a path with elements separated by
    posixpath.sep, generate all parents of that path.

    >>> list(_parents('b/d'))
    ['b']
    >>> list(_parents('/b/d/'))
    ['/b']
    >>> list(_parents('b/d/f/'))
    ['b/d', 'b']
    >>> list(_parents('b'))
    []
    >>> list(_parents(''))
    []
    """
    return itertools.islice(_ancestry(path), 1, None)


def _ancestry(path):
    """
    Given a path with elements separated by
    posixpath.sep, generate all elements of that path.

    >>> list(_ancestry('b/d'))
    ['b/d', 'b']
    >>> list(_ancestry('/b/d/'))
    ['/b/d', '/b']
    >>> list(_ancestry('b/d/f/'))
    ['b/d/f', 'b/d', 'b']
    >>> list(_ancestry('b'))
    ['b']
    >>> list(_ancestry(''))
    []

    Multiple separators are treated like a single.

    >>> list(_ancestry('//b//d///f//'))
    ['//b//d///f', '//b//d', '//b']
    """
    path = path.rstrip(posixpath.sep)
    while path.rstrip(posixpath.sep):
        yield path
        path, tail = posixpath.split(path)


_dedupe = dict.fromkeys
"""Deduplicate an iterable in original order"""


def _difference(minuend, subtrahend):
    """
    Return items in minuend not in subtrahend, retaining order
    with O(1) lookup.
    """
    return itertools.filterfalse(set(subtrahend).__contains__, minuend)


class InitializedState:
    """
    Mix-in to save the initialization state for pickling.
    """

    @save_method_args
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getstate__(self):
        return self._saved___init__.args, self._saved___init__.kwargs

    def __setstate__(self, state):
        args, kwargs = state
        super().__init__(*args, **kwargs)


class CompleteDirs(InitializedState, zipfile.ZipFile):
    """
    A ZipFile subclass that ensures that implied directories
    are always included in the namelist.

    >>> list(CompleteDirs._implied_dirs(['foo/bar.txt', 'foo/bar/baz.txt']))
    ['foo/', 'foo/bar/']
    >>> list(CompleteDirs._implied_dirs(['foo/bar.txt', 'foo/bar/baz.txt', 'foo/bar/']))
    ['foo/']
    """

    @staticmethod
    def _implied_dirs(names):
        parents = itertools.chain.from_iterable(map(_parents, names))
        as_dirs = (p + posixpath.sep for p in parents)
        return _dedupe(_difference(as_dirs, names))

    def namelist(self):
        names = super().namelist()
        return names + list(self._implied_dirs(names))

    def _name_set(self):
        return set(self.namelist())

    def resolve_dir(self, name):
        """
        If the name represents a directory, return that name
        as a directory (with the trailing slash).
        """
        names = self._name_set()
        dirname = name + '/'
        dir_match = name not in names and dirname in names
        return dirname if dir_match else name

    def getinfo(self, name):
        """
        Supplement getinfo for implied dirs.
        """
        try:
            return super().getinfo(name)
        except KeyError:
            if not name.endswith('/') or name not in self._name_set():
                raise
            return zipfile.ZipInfo(filename=name)

    @classmethod
    def make(cls, source):
        """
        Given a source (filename or zipfile), return an
        appropriate CompleteDirs subclass.
        """
        if isinstance(source, CompleteDirs):
            return source

        if not isinstance(source, zipfile.ZipFile):
            return cls(source)

        # Only allow for FastLookup when supplied zipfile is read-only
        if 'r' not in source.mode:
            cls = CompleteDirs

        source.__class__ = cls
        return source

    @classmethod
    def inject(cls, zf: zipfile.ZipFile) -> zipfile.ZipFile:
        """
        Given a writable zip file zf, inject directory entries for
        any directories implied by the presence of children.
        """
        for name in cls._implied_dirs(zf.namelist()):
            zf.writestr(name, b"")
        return zf


class FastLookup(CompleteDirs):
    """
    ZipFile subclass to ensure implicit
    dirs exist and are resolved rapidly.
    """

    def namelist(self):
        return self._namelist

    @functools.cached_property
    def _namelist(self):
        return super().namelist()

    def _name_set(self):
        return self._name_set_prop

    @functools.cached_property
    def _name_set_prop(self):
        return super()._name_set()


def _extract_text_encoding(encoding=None, *args, **kwargs):
    # compute stack level so that the caller of the caller sees any warning.
    is_pypy = sys.implementation.name == 'pypy'
    # PyPy no longer special cased after 7.3.19 (or maybe 7.3.18)
    # See jaraco/zipp#143
    is_old_pypi = is_pypy and sys.pypy_version_info < (7, 3, 19)
    stack_level = 3 + is_old_pypi
    return text_encoding(encoding, stack_level), args, kwargs


class Path:
    """
    A :class:`importlib.resources.abc.Traversable` interface for zip files.

    Implements many of the features users enjoy from
    :class:`pathlib.Path`.

    Consider a zip file with this structure::

        .
        ├── a.txt
        └── b
            ├── c.txt
            └── d
                └── e.txt

    >>> data = io.BytesIO()
    >>> zf = zipfile.ZipFile(data, 'w')
    >>> zf.writestr('a.txt', 'content of a')
    >>> zf.writestr('b/c.txt', 'content of c')
    >>> zf.writestr('b/d/e.txt', 'content of e')
    >>> zf.filename = 'mem/abcde.zip'

    Path accepts the zipfile object itself or a filename

    >>> path = Path(zf)

    From there, several path operations are available.

    Directory iteration (including the zip file itself):

    >>> a, b = path.iterdir()
    >>> a
    Path('mem/abcde.zip', 'a.txt')
    >>> b
    Path('mem/abcde.zip', 'b/')

    name property:

    >>> b.name
    'b'

    join with divide operator:

    >>> c = b / 'c.txt'
    >>> c
    Path('mem/abcde.zip', 'b/c.txt')
    >>> c.name
    'c.txt'

    Read text:

    >>> c.read_text(encoding='utf-8')
    'content of c'

    existence:

    >>> c.exists()
    True
    >>> (b / 'missing.txt').exists()
    False

    Coercion to string:

    >>> import os
    >>> str(c).replace(os.sep, posixpath.sep)
    'mem/abcde.zip/b/c.txt'

    At the root, ``name``, ``filename``, and ``parent``
    resolve to the zipfile.

    >>> str(path)
    'mem/abcde.zip/'
    >>> path.name
    'abcde.zip'
    >>> path.filename == pathlib.Path('mem/abcde.zip')
    True
    >>> str(path.parent)
    'mem'

    If the zipfile has no filename, such attributes are not
    valid and accessing them will raise an Exception.

    >>> zf.filename = None
    >>> path.name
    Traceback (most recent call last):
    ...
    TypeError: ...

    >>> path.filename
    Traceback (most recent call last):
    ...
    TypeError: ...

    >>> path.parent
    Traceback (most recent call last):
    ...
    TypeError: ...

    # workaround python/cpython#106763
    >>> pass
    """

    __repr = "{self.__class__.__name__}({self.root.filename!r}, {self.at!r})"

    def __init__(self, root, at=""):
        """
        Construct a Path from a ZipFile or filename.

        Note: When the source is an existing ZipFile object,
        its type (__class__) will be mutated to a
        specialized type. If the caller wishes to retain the
        original type, the caller should either create a
        separate ZipFile object or pass a filename.
        """
        self.root = FastLookup.make(root)
        self.at = at

    def __eq__(self, other):
        """
        >>> Path(zipfile.ZipFile(io.BytesIO(), 'w')) == 'foo'
        False
        """
        if self.__class__ is not other.__class__:
            return NotImplemented
        return (self.root, self.at) == (other.root, other.at)

    def __hash__(self):
        return hash((self.root, self.at))

    def open(self, mode='r', *args, pwd=None, **kwargs):
        """
        Open this entry as text or binary following the semantics
        of ``pathlib.Path.open()`` by passing arguments through
        to io.TextIOWrapper().
        """
        if self.is_dir():
            raise IsADirectoryError(self)
        zip_mode = mode[0]
        if zip_mode == 'r' and not self.exists():
            raise FileNotFoundError(self)
        stream = self.root.open(self.at, zip_mode, pwd=pwd)
        if 'b' in mode:
            if args or kwargs:
                raise ValueError("encoding args invalid for binary operation")
            return stream
        # Text mode:
        encoding, args, kwargs = _extract_text_encoding(*args, **kwargs)
        return io.TextIOWrapper(stream, encoding, *args, **kwargs)

    def _base(self):
        return pathlib.PurePosixPath(self.at) if self.at else self.filename

    @property
    def name(self):
        return self._base().name

    @property
    def suffix(self):
        return self._base().suffix

    @property
    def suffixes(self):
        return self._base().suffixes

    @property
    def stem(self):
        return self._base().stem

    @property
    def filename(self):
        return pathlib.Path(self.root.filename).joinpath(self.at)

    def read_text(self, *args, **kwargs):
        encoding, args, kwargs = _extract_text_encoding(*args, **kwargs)
        with self.open('r', encoding, *args, **kwargs) as strm:
            return strm.read()

    def read_bytes(self):
        with self.open('rb') as strm:
            return strm.read()

    def _is_child(self, path):
        return posixpath.dirname(path.at.rstrip("/")) == self.at.rstrip("/")

    def _next(self, at):
        return self.__class__(self.root, at)

    def is_dir(self):
        return not self.at or self.at.endswith("/")

    def is_file(self):
        return self.exists() and not self.is_dir()

    def exists(self):
        return self.at in self.root._name_set()

    def iterdir(self):
        if not self.is_dir():
            raise ValueError("Can't listdir a file")
        subs = map(self._next, self.root.namelist())
        return filter(self._is_child, subs)

    def match(self, path_pattern):
        return pathlib.PurePosixPath(self.at).match(path_pattern)

    def is_symlink(self):
        """
        Return whether this path is a symlink.
        """
        info = self.root.getinfo(self.at)
        mode = info.external_attr >> 16
        return stat.S_ISLNK(mode)

    def glob(self, pattern):
        if not pattern:
            raise ValueError(f"Unacceptable pattern: {pattern!r}")

        prefix = re.escape(self.at)
        tr = Translator(seps='/')
        matches = re.compile(prefix + tr.translate(pattern)).fullmatch
        return map(self._next, filter(matches, self.root.namelist()))

    def rglob(self, pattern):
        return self.glob(f'**/{pattern}')

    def relative_to(self, other, *extra):
        return posixpath.relpath(str(self), str(other.joinpath(*extra)))

    def __str__(self):
        return posixpath.join(self.root.filename, self.at)

    def __repr__(self):
        return self.__repr.format(self=self)

    def joinpath(self, *other):
        next = posixpath.join(self.at, *other)
        return self._next(self.root.resolve_dir(next))

    __truediv__ = joinpath

    @property
    def parent(self):
        if not self.at:
            return self.filename.parent
        parent_at = posixpath.dirname(self.at.rstrip('/'))
        if parent_at:
            parent_at += '/'
        return self._next(parent_at)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\etree.py ===
"""Shim module exporting the same ElementTree API for lxml and
xml.etree backends.

When lxml is installed, it is automatically preferred over the built-in
xml.etree module.
On Python 2.7, the cElementTree module is preferred over the pure-python
ElementTree module.

Besides exporting a unified interface, this also defines extra functions
or subclasses built-in ElementTree classes to add features that are
only availble in lxml, like OrderedDict for attributes, pretty_print and
iterwalk.
"""

from fontTools.misc.textTools import tostr


XML_DECLARATION = """<?xml version='1.0' encoding='%s'?>"""

__all__ = [
    # public symbols
    "Comment",
    "dump",
    "Element",
    "ElementTree",
    "fromstring",
    "fromstringlist",
    "iselement",
    "iterparse",
    "parse",
    "ParseError",
    "PI",
    "ProcessingInstruction",
    "QName",
    "SubElement",
    "tostring",
    "tostringlist",
    "TreeBuilder",
    "XML",
    "XMLParser",
    "register_namespace",
]

try:
    from lxml.etree import *

    _have_lxml = True
except ImportError:
    try:
        from xml.etree.cElementTree import *

        # the cElementTree version of XML function doesn't support
        # the optional 'parser' keyword argument
        from xml.etree.ElementTree import XML
    except ImportError:  # pragma: no cover
        from xml.etree.ElementTree import *
    _have_lxml = False

    _Attrib = dict

    if isinstance(Element, type):
        _Element = Element
    else:
        # in py27, cElementTree.Element cannot be subclassed, so
        # we need to import the pure-python class
        from xml.etree.ElementTree import Element as _Element

    class Element(_Element):
        """Element subclass that keeps the order of attributes."""

        def __init__(self, tag, attrib=_Attrib(), **extra):
            super(Element, self).__init__(tag)
            self.attrib = _Attrib()
            if attrib:
                self.attrib.update(attrib)
            if extra:
                self.attrib.update(extra)

    def SubElement(parent, tag, attrib=_Attrib(), **extra):
        """Must override SubElement as well otherwise _elementtree.SubElement
        fails if 'parent' is a subclass of Element object.
        """
        element = parent.__class__(tag, attrib, **extra)
        parent.append(element)
        return element

    def _iterwalk(element, events, tag):
        include = tag is None or element.tag == tag
        if include and "start" in events:
            yield ("start", element)
        for e in element:
            for item in _iterwalk(e, events, tag):
                yield item
        if include:
            yield ("end", element)

    def iterwalk(element_or_tree, events=("end",), tag=None):
        """A tree walker that generates events from an existing tree as
        if it was parsing XML data with iterparse().
        Drop-in replacement for lxml.etree.iterwalk.
        """
        if iselement(element_or_tree):
            element = element_or_tree
        else:
            element = element_or_tree.getroot()
        if tag == "*":
            tag = None
        for item in _iterwalk(element, events, tag):
            yield item

    _ElementTree = ElementTree

    class ElementTree(_ElementTree):
        """ElementTree subclass that adds 'pretty_print' and 'doctype'
        arguments to the 'write' method.
        Currently these are only supported for the default XML serialization
        'method', and not also for "html" or "text", for these are delegated
        to the base class.
        """

        def write(
            self,
            file_or_filename,
            encoding=None,
            xml_declaration=False,
            method=None,
            doctype=None,
            pretty_print=False,
        ):
            if method and method != "xml":
                # delegate to super-class
                super(ElementTree, self).write(
                    file_or_filename,
                    encoding=encoding,
                    xml_declaration=xml_declaration,
                    method=method,
                )
                return

            if encoding is not None and encoding.lower() == "unicode":
                if xml_declaration:
                    raise ValueError(
                        "Serialisation to unicode must not request an XML declaration"
                    )
                write_declaration = False
                encoding = "unicode"
            elif xml_declaration is None:
                # by default, write an XML declaration only for non-standard encodings
                write_declaration = encoding is not None and encoding.upper() not in (
                    "ASCII",
                    "UTF-8",
                    "UTF8",
                    "US-ASCII",
                )
            else:
                write_declaration = xml_declaration

            if encoding is None:
                encoding = "ASCII"

            if pretty_print:
                # NOTE this will modify the tree in-place
                _indent(self._root)

            with _get_writer(file_or_filename, encoding) as write:
                if write_declaration:
                    write(XML_DECLARATION % encoding.upper())
                    if pretty_print:
                        write("\n")
                if doctype:
                    write(_tounicode(doctype))
                    if pretty_print:
                        write("\n")

                qnames, namespaces = _namespaces(self._root)
                _serialize_xml(write, self._root, qnames, namespaces)

    import io

    def tostring(
        element,
        encoding=None,
        xml_declaration=None,
        method=None,
        doctype=None,
        pretty_print=False,
    ):
        """Custom 'tostring' function that uses our ElementTree subclass, with
        pretty_print support.
        """
        stream = io.StringIO() if encoding == "unicode" else io.BytesIO()
        ElementTree(element).write(
            stream,
            encoding=encoding,
            xml_declaration=xml_declaration,
            method=method,
            doctype=doctype,
            pretty_print=pretty_print,
        )
        return stream.getvalue()

    # serialization support

    import re

    # Valid XML strings can include any Unicode character, excluding control
    # characters, the surrogate blocks, FFFE, and FFFF:
    #   Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # Here we reversed the pattern to match only the invalid characters.
    _invalid_xml_string = re.compile(
        "[\u0000-\u0008\u000B-\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE-\uFFFF]"
    )

    def _tounicode(s):
        """Test if a string is valid user input and decode it to unicode string
        using ASCII encoding if it's a bytes string.
        Reject all bytes/unicode input that contains non-XML characters.
        Reject all bytes input that contains non-ASCII characters.
        """
        try:
            s = tostr(s, encoding="ascii", errors="strict")
        except UnicodeDecodeError:
            raise ValueError(
                "Bytes strings can only contain ASCII characters. "
                "Use unicode strings for non-ASCII characters."
            )
        except AttributeError:
            _raise_serialization_error(s)
        if s and _invalid_xml_string.search(s):
            raise ValueError(
                "All strings must be XML compatible: Unicode or ASCII, "
                "no NULL bytes or control characters"
            )
        return s

    import contextlib

    @contextlib.contextmanager
    def _get_writer(file_or_filename, encoding):
        # returns text write method and release all resources after using
        try:
            write = file_or_filename.write
        except AttributeError:
            # file_or_filename is a file name
            f = open(
                file_or_filename,
                "w",
                encoding="utf-8" if encoding == "unicode" else encoding,
                errors="xmlcharrefreplace",
            )
            with f:
                yield f.write
        else:
            # file_or_filename is a file-like object
            # encoding determines if it is a text or binary writer
            if encoding == "unicode":
                # use a text writer as is
                yield write
            else:
                # wrap a binary writer with TextIOWrapper
                detach_buffer = False
                if isinstance(file_or_filename, io.BufferedIOBase):
                    buf = file_or_filename
                elif isinstance(file_or_filename, io.RawIOBase):
                    buf = io.BufferedWriter(file_or_filename)
                    detach_buffer = True
                else:
                    # This is to handle passed objects that aren't in the
                    # IOBase hierarchy, but just have a write method
                    buf = io.BufferedIOBase()
                    buf.writable = lambda: True
                    buf.write = write
                    try:
                        # TextIOWrapper uses this methods to determine
                        # if BOM (for UTF-16, etc) should be added
                        buf.seekable = file_or_filename.seekable
                        buf.tell = file_or_filename.tell
                    except AttributeError:
                        pass
                wrapper = io.TextIOWrapper(
                    buf,
                    encoding=encoding,
                    errors="xmlcharrefreplace",
                    newline="\n",
                )
                try:
                    yield wrapper.write
                finally:
                    # Keep the original file open when the TextIOWrapper and
                    # the BufferedWriter are destroyed
                    wrapper.detach()
                    if detach_buffer:
                        buf.detach()

    from xml.etree.ElementTree import _namespace_map

    def _namespaces(elem):
        # identify namespaces used in this tree

        # maps qnames to *encoded* prefix:local names
        qnames = {None: None}

        # maps uri:s to prefixes
        namespaces = {}

        def add_qname(qname):
            # calculate serialized qname representation
            try:
                qname = _tounicode(qname)
                if qname[:1] == "{":
                    uri, tag = qname[1:].rsplit("}", 1)
                    prefix = namespaces.get(uri)
                    if prefix is None:
                        prefix = _namespace_map.get(uri)
                        if prefix is None:
                            prefix = "ns%d" % len(namespaces)
                        else:
                            prefix = _tounicode(prefix)
                        if prefix != "xml":
                            namespaces[uri] = prefix
                    if prefix:
                        qnames[qname] = "%s:%s" % (prefix, tag)
                    else:
                        qnames[qname] = tag  # default element
                else:
                    qnames[qname] = qname
            except TypeError:
                _raise_serialization_error(qname)

        # populate qname and namespaces table
        for elem in elem.iter():
            tag = elem.tag
            if isinstance(tag, QName):
                if tag.text not in qnames:
                    add_qname(tag.text)
            elif isinstance(tag, str):
                if tag not in qnames:
                    add_qname(tag)
            elif tag is not None and tag is not Comment and tag is not PI:
                _raise_serialization_error(tag)
            for key, value in elem.items():
                if isinstance(key, QName):
                    key = key.text
                if key not in qnames:
                    add_qname(key)
                if isinstance(value, QName) and value.text not in qnames:
                    add_qname(value.text)
            text = elem.text
            if isinstance(text, QName) and text.text not in qnames:
                add_qname(text.text)
        return qnames, namespaces

    def _serialize_xml(write, elem, qnames, namespaces, **kwargs):
        tag = elem.tag
        text = elem.text
        if tag is Comment:
            write("<!--%s-->" % _tounicode(text))
        elif tag is ProcessingInstruction:
            write("<?%s?>" % _tounicode(text))
        else:
            tag = qnames[_tounicode(tag) if tag is not None else None]
            if tag is None:
                if text:
                    write(_escape_cdata(text))
                for e in elem:
                    _serialize_xml(write, e, qnames, None)
            else:
                write("<" + tag)
                if namespaces:
                    for uri, prefix in sorted(
                        namespaces.items(), key=lambda x: x[1]
                    ):  # sort on prefix
                        if prefix:
                            prefix = ":" + prefix
                        write(' xmlns%s="%s"' % (prefix, _escape_attrib(uri)))
                attrs = elem.attrib
                if attrs:
                    # try to keep existing attrib order
                    if len(attrs) <= 1 or type(attrs) is _Attrib:
                        items = attrs.items()
                    else:
                        # if plain dict, use lexical order
                        items = sorted(attrs.items())
                    for k, v in items:
                        if isinstance(k, QName):
                            k = _tounicode(k.text)
                        else:
                            k = _tounicode(k)
                        if isinstance(v, QName):
                            v = qnames[_tounicode(v.text)]
                        else:
                            v = _escape_attrib(v)
                        write(' %s="%s"' % (qnames[k], v))
                if text is not None or len(elem):
                    write(">")
                    if text:
                        write(_escape_cdata(text))
                    for e in elem:
                        _serialize_xml(write, e, qnames, None)
                    write("</" + tag + ">")
                else:
                    write("/>")
        if elem.tail:
            write(_escape_cdata(elem.tail))

    def _raise_serialization_error(text):
        raise TypeError("cannot serialize %r (type %s)" % (text, type(text).__name__))

    def _escape_cdata(text):
        # escape character data
        try:
            text = _tounicode(text)
            # it's worth avoiding do-nothing calls for short strings
            if "&" in text:
                text = text.replace("&", "&amp;")
            if "<" in text:
                text = text.replace("<", "&lt;")
            if ">" in text:
                text = text.replace(">", "&gt;")
            return text
        except (TypeError, AttributeError):
            _raise_serialization_error(text)

    def _escape_attrib(text):
        # escape attribute value
        try:
            text = _tounicode(text)
            if "&" in text:
                text = text.replace("&", "&amp;")
            if "<" in text:
                text = text.replace("<", "&lt;")
            if ">" in text:
                text = text.replace(">", "&gt;")
            if '"' in text:
                text = text.replace('"', "&quot;")
            if "\n" in text:
                text = text.replace("\n", "&#10;")
            return text
        except (TypeError, AttributeError):
            _raise_serialization_error(text)

    def _indent(elem, level=0):
        # From http://effbot.org/zone/element-lib.htm#prettyprint
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                _indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

# === NexusCore/openenv\Lib\site-packages\pip\_internal\locations\__init__.py ===
import functools
import logging
import os
import pathlib
import sys
import sysconfig
from typing import Any, Dict, Generator, Optional, Tuple

from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.virtualenv import running_under_virtualenv

from . import _sysconfig
from .base import (
    USER_CACHE_DIR,
    get_major_minor_version,
    get_src_prefix,
    is_osx_framework,
    site_packages,
    user_site,
)

__all__ = [
    "USER_CACHE_DIR",
    "get_bin_prefix",
    "get_bin_user",
    "get_major_minor_version",
    "get_platlib",
    "get_purelib",
    "get_scheme",
    "get_src_prefix",
    "site_packages",
    "user_site",
]


logger = logging.getLogger(__name__)


_PLATLIBDIR: str = getattr(sys, "platlibdir", "lib")

_USE_SYSCONFIG_DEFAULT = sys.version_info >= (3, 10)


def _should_use_sysconfig() -> bool:
    """This function determines the value of _USE_SYSCONFIG.

    By default, pip uses sysconfig on Python 3.10+.
    But Python distributors can override this decision by setting:
        sysconfig._PIP_USE_SYSCONFIG = True / False
    Rationale in https://github.com/pypa/pip/issues/10647

    This is a function for testability, but should be constant during any one
    run.
    """
    return bool(getattr(sysconfig, "_PIP_USE_SYSCONFIG", _USE_SYSCONFIG_DEFAULT))


_USE_SYSCONFIG = _should_use_sysconfig()

if not _USE_SYSCONFIG:
    # Import distutils lazily to avoid deprecation warnings,
    # but import it soon enough that it is in memory and available during
    # a pip reinstall.
    from . import _distutils

# Be noisy about incompatibilities if this platforms "should" be using
# sysconfig, but is explicitly opting out and using distutils instead.
if _USE_SYSCONFIG_DEFAULT and not _USE_SYSCONFIG:
    _MISMATCH_LEVEL = logging.WARNING
else:
    _MISMATCH_LEVEL = logging.DEBUG


def _looks_like_bpo_44860() -> bool:
    """The resolution to bpo-44860 will change this incorrect platlib.

    See <https://bugs.python.org/issue44860>.
    """
    from distutils.command.install import INSTALL_SCHEMES

    try:
        unix_user_platlib = INSTALL_SCHEMES["unix_user"]["platlib"]
    except KeyError:
        return False
    return unix_user_platlib == "$usersite"


def _looks_like_red_hat_patched_platlib_purelib(scheme: Dict[str, str]) -> bool:
    platlib = scheme["platlib"]
    if "/$platlibdir/" in platlib:
        platlib = platlib.replace("/$platlibdir/", f"/{_PLATLIBDIR}/")
    if "/lib64/" not in platlib:
        return False
    unpatched = platlib.replace("/lib64/", "/lib/")
    return unpatched.replace("$platbase/", "$base/") == scheme["purelib"]


@functools.lru_cache(maxsize=None)
def _looks_like_red_hat_lib() -> bool:
    """Red Hat patches platlib in unix_prefix and unix_home, but not purelib.

    This is the only way I can see to tell a Red Hat-patched Python.
    """
    from distutils.command.install import INSTALL_SCHEMES

    return all(
        k in INSTALL_SCHEMES
        and _looks_like_red_hat_patched_platlib_purelib(INSTALL_SCHEMES[k])
        for k in ("unix_prefix", "unix_home")
    )


@functools.lru_cache(maxsize=None)
def _looks_like_debian_scheme() -> bool:
    """Debian adds two additional schemes."""
    from distutils.command.install import INSTALL_SCHEMES

    return "deb_system" in INSTALL_SCHEMES and "unix_local" in INSTALL_SCHEMES


@functools.lru_cache(maxsize=None)
def _looks_like_red_hat_scheme() -> bool:
    """Red Hat patches ``sys.prefix`` and ``sys.exec_prefix``.

    Red Hat's ``00251-change-user-install-location.patch`` changes the install
    command's ``prefix`` and ``exec_prefix`` to append ``"/local"``. This is
    (fortunately?) done quite unconditionally, so we create a default command
    object without any configuration to detect this.
    """
    from distutils.command.install import install
    from distutils.dist import Distribution

    cmd: Any = install(Distribution())
    cmd.finalize_options()
    return (
        cmd.exec_prefix == f"{os.path.normpath(sys.exec_prefix)}/local"
        and cmd.prefix == f"{os.path.normpath(sys.prefix)}/local"
    )


@functools.lru_cache(maxsize=None)
def _looks_like_slackware_scheme() -> bool:
    """Slackware patches sysconfig but fails to patch distutils and site.

    Slackware changes sysconfig's user scheme to use ``"lib64"`` for the lib
    path, but does not do the same to the site module.
    """
    if user_site is None:  # User-site not available.
        return False
    try:
        paths = sysconfig.get_paths(scheme="posix_user", expand=False)
    except KeyError:  # User-site not available.
        return False
    return "/lib64/" in paths["purelib"] and "/lib64/" not in user_site


@functools.lru_cache(maxsize=None)
def _looks_like_msys2_mingw_scheme() -> bool:
    """MSYS2 patches distutils and sysconfig to use a UNIX-like scheme.

    However, MSYS2 incorrectly patches sysconfig ``nt`` scheme. The fix is
    likely going to be included in their 3.10 release, so we ignore the warning.
    See msys2/MINGW-packages#9319.

    MSYS2 MINGW's patch uses lowercase ``"lib"`` instead of the usual uppercase,
    and is missing the final ``"site-packages"``.
    """
    paths = sysconfig.get_paths("nt", expand=False)
    return all(
        "Lib" not in p and "lib" in p and not p.endswith("site-packages")
        for p in (paths[key] for key in ("platlib", "purelib"))
    )


def _fix_abiflags(parts: Tuple[str]) -> Generator[str, None, None]:
    ldversion = sysconfig.get_config_var("LDVERSION")
    abiflags = getattr(sys, "abiflags", None)

    # LDVERSION does not end with sys.abiflags. Just return the path unchanged.
    if not ldversion or not abiflags or not ldversion.endswith(abiflags):
        yield from parts
        return

    # Strip sys.abiflags from LDVERSION-based path components.
    for part in parts:
        if part.endswith(ldversion):
            part = part[: (0 - len(abiflags))]
        yield part


@functools.lru_cache(maxsize=None)
def _warn_mismatched(old: pathlib.Path, new: pathlib.Path, *, key: str) -> None:
    issue_url = "https://github.com/pypa/pip/issues/10151"
    message = (
        "Value for %s does not match. Please report this to <%s>"
        "\ndistutils: %s"
        "\nsysconfig: %s"
    )
    logger.log(_MISMATCH_LEVEL, message, key, issue_url, old, new)


def _warn_if_mismatch(old: pathlib.Path, new: pathlib.Path, *, key: str) -> bool:
    if old == new:
        return False
    _warn_mismatched(old, new, key=key)
    return True


@functools.lru_cache(maxsize=None)
def _log_context(
    *,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    prefix: Optional[str] = None,
) -> None:
    parts = [
        "Additional context:",
        "user = %r",
        "home = %r",
        "root = %r",
        "prefix = %r",
    ]

    logger.log(_MISMATCH_LEVEL, "\n".join(parts), user, home, root, prefix)


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> Scheme:
    new = _sysconfig.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )

    warning_contexts = []
    for k in SCHEME_KEYS:
        old_v = pathlib.Path(getattr(old, k))
        new_v = pathlib.Path(getattr(new, k))

        if old_v == new_v:
            continue

        # distutils incorrectly put PyPy packages under ``site-packages/python``
        # in the ``posix_home`` scheme, but PyPy devs said they expect the
        # directory name to be ``pypy`` instead. So we treat this as a bug fix
        # and not warn about it. See bpo-43307 and python/cpython#24628.
        skip_pypy_special_case = (
            sys.implementation.name == "pypy"
            and home is not None
            and k in ("platlib", "purelib")
            and old_v.parent == new_v.parent
            and old_v.name.startswith("python")
            and new_v.name.startswith("pypy")
        )
        if skip_pypy_special_case:
            continue

        # sysconfig's ``osx_framework_user`` does not include ``pythonX.Y`` in
        # the ``include`` value, but distutils's ``headers`` does. We'll let
        # CPython decide whether this is a bug or feature. See bpo-43948.
        skip_osx_framework_user_special_case = (
            user
            and is_osx_framework()
            and k == "headers"
            and old_v.parent.parent == new_v.parent
            and old_v.parent.name.startswith("python")
        )
        if skip_osx_framework_user_special_case:
            continue

        # On Red Hat and derived Linux distributions, distutils is patched to
        # use "lib64" instead of "lib" for platlib.
        if k == "platlib" and _looks_like_red_hat_lib():
            continue

        # On Python 3.9+, sysconfig's posix_user scheme sets platlib against
        # sys.platlibdir, but distutils's unix_user incorrectly coninutes
        # using the same $usersite for both platlib and purelib. This creates a
        # mismatch when sys.platlibdir is not "lib".
        skip_bpo_44860 = (
            user
            and k == "platlib"
            and not WINDOWS
            and sys.version_info >= (3, 9)
            and _PLATLIBDIR != "lib"
            and _looks_like_bpo_44860()
        )
        if skip_bpo_44860:
            continue

        # Slackware incorrectly patches posix_user to use lib64 instead of lib,
        # but not usersite to match the location.
        skip_slackware_user_scheme = (
            user
            and k in ("platlib", "purelib")
            and not WINDOWS
            and _looks_like_slackware_scheme()
        )
        if skip_slackware_user_scheme:
            continue

        # Both Debian and Red Hat patch Python to place the system site under
        # /usr/local instead of /usr. Debian also places lib in dist-packages
        # instead of site-packages, but the /usr/local check should cover it.
        skip_linux_system_special_case = (
            not (user or home or prefix or running_under_virtualenv())
            and old_v.parts[1:3] == ("usr", "local")
            and len(new_v.parts) > 1
            and new_v.parts[1] == "usr"
            and (len(new_v.parts) < 3 or new_v.parts[2] != "local")
            and (_looks_like_red_hat_scheme() or _looks_like_debian_scheme())
        )
        if skip_linux_system_special_case:
            continue

        # MSYS2 MINGW's sysconfig patch does not include the "site-packages"
        # part of the path. This is incorrect and will be fixed in MSYS.
        skip_msys2_mingw_bug = (
            WINDOWS and k in ("platlib", "purelib") and _looks_like_msys2_mingw_scheme()
        )
        if skip_msys2_mingw_bug:
            continue

        # CPython's POSIX install script invokes pip (via ensurepip) against the
        # interpreter located in the source tree, not the install site. This
        # triggers special logic in sysconfig that's not present in distutils.
        # https://github.com/python/cpython/blob/8c21941ddaf/Lib/sysconfig.py#L178-L194
        skip_cpython_build = (
            sysconfig.is_python_build(check_home=True)
            and not WINDOWS
            and k in ("headers", "include", "platinclude")
        )
        if skip_cpython_build:
            continue

        warning_contexts.append((old_v, new_v, f"scheme.{k}"))

    if not warning_contexts:
        return old

    # Check if this path mismatch is caused by distutils config files. Those
    # files will no longer work once we switch to sysconfig, so this raises a
    # deprecation message for them.
    default_old = _distutils.distutils_scheme(
        dist_name,
        user,
        home,
        root,
        isolated,
        prefix,
        ignore_config_files=True,
    )
    if any(default_old[k] != getattr(old, k) for k in SCHEME_KEYS):
        deprecated(
            reason=(
                "Configuring installation scheme with distutils config files "
                "is deprecated and will no longer work in the near future. If you "
                "are using a Homebrew or Linuxbrew Python, please see discussion "
                "at https://github.com/Homebrew/homebrew-core/issues/76621"
            ),
            replacement=None,
            gone_in=None,
        )
        return old

    # Post warnings about this mismatch so user can report them back.
    for old_v, new_v, key in warning_contexts:
        _warn_mismatched(old_v, new_v, key=key)
    _log_context(user=user, home=home, root=root, prefix=prefix)

    return old


def get_bin_prefix() -> str:
    new = _sysconfig.get_bin_prefix()
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_bin_prefix()
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="bin_prefix"):
        _log_context()
    return old


def get_bin_user() -> str:
    return _sysconfig.get_scheme("", user=True).scripts


def _looks_like_deb_system_dist_packages(value: str) -> bool:
    """Check if the value is Debian's APT-controlled dist-packages.

    Debian's ``distutils.sysconfig.get_python_lib()`` implementation returns the
    default package path controlled by APT, but does not patch ``sysconfig`` to
    do the same. This is similar to the bug worked around in ``get_scheme()``,
    but here the default is ``deb_system`` instead of ``unix_local``. Ultimately
    we can't do anything about this Debian bug, and this detection allows us to
    skip the warning when needed.
    """
    if not _looks_like_debian_scheme():
        return False
    if value == "/usr/lib/python3/dist-packages":
        return True
    return False


def get_purelib() -> str:
    """Return the default pure-Python lib location."""
    new = _sysconfig.get_purelib()
    if _USE_SYSCONFIG:
        return new

    old = _distutils.get_purelib()
    if _looks_like_deb_system_dist_packages(old):
        return old
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="purelib"):
        _log_context()
    return old


def get_platlib() -> str:
    """Return the default platform-shared lib location."""
    new = _sysconfig.get_platlib()
    if _USE_SYSCONFIG:
        return new

    from . import _distutils

    old = _distutils.get_platlib()
    if _looks_like_deb_system_dist_packages(old):
        return old
    if _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="platlib"):
        _log_context()
    return old

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_experimental\mcp_server\server.py ===
"""
LiteLLM MCP Server Routes
"""

import asyncio
import contextlib
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException
from pydantic import ConfigDict
from starlette.types import Receive, Scope, Send

from litellm._logging import verbose_logger
from litellm.constants import MCP_TOOL_NAME_PREFIX
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.proxy._experimental.mcp_server.auth.user_api_key_auth_mcp import (
    UserAPIKeyAuthMCP,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.mcp_server.mcp_server_manager import MCPInfo
from litellm.types.utils import StandardLoggingMCPToolCall
from litellm.utils import client

LITELLM_MCP_SERVER_NAME = "litellm-mcp-server"
LITELLM_MCP_SERVER_VERSION = "1.0.0"
LITELLM_MCP_SERVER_DESCRIPTION = "MCP Server for LiteLLM"

# Check if MCP is available
# "mcp" requires python 3.10 or higher, but several litellm users use python 3.8
# We're making this conditional import to avoid breaking users who use python 3.8.
# TODO: Make this a util function for litellm client usage
MCP_AVAILABLE: bool = True
try:
    from mcp.server import Server
except ImportError as e:
    verbose_logger.debug(f"MCP module not found: {e}")
    MCP_AVAILABLE = False


# Global variables to track initialization
_SESSION_MANAGERS_INITIALIZED = False
_SESSION_MANAGER_TASK = None

if MCP_AVAILABLE:
    from mcp.server import Server

    # Import auth context variables and middleware
    from mcp.server.auth.middleware.auth_context import (
        AuthContextMiddleware,
        auth_context_var,
    )
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.types import EmbeddedResource as MCPEmbeddedResource
    from mcp.types import ImageContent as MCPImageContent
    from mcp.types import TextContent as MCPTextContent
    from mcp.types import Tool as MCPTool

    from litellm.proxy._experimental.mcp_server.auth.litellm_auth_handler import (
        LiteLLMAuthenticatedUser,
    )
    from litellm.proxy._experimental.mcp_server.mcp_server_manager import (
        global_mcp_server_manager,
    )
    from litellm.proxy._experimental.mcp_server.sse_transport import SseServerTransport
    from litellm.proxy._experimental.mcp_server.tool_registry import (
        global_mcp_tool_registry,
    )

    ######################################################
    ############ MCP Tools List REST API Response Object #
    # Defined here because we don't want to add `mcp` as a
    # required dependency for `litellm` pip package
    ######################################################
    class ListMCPToolsRestAPIResponseObject(MCPTool):
        """
        Object returned by the /tools/list REST API route.
        """

        mcp_info: Optional[MCPInfo] = None
        model_config = ConfigDict(arbitrary_types_allowed=True)

    ########################################################
    ############ Initialize the MCP Server #################
    ########################################################
    server: Server = Server(
        name=LITELLM_MCP_SERVER_NAME,
        version=LITELLM_MCP_SERVER_VERSION,
    )
    sse: SseServerTransport = SseServerTransport("/mcp/sse/messages")

    # Create session managers
    session_manager = StreamableHTTPSessionManager(
        app=server,
        event_store=None,
        json_response=True,  # Use JSON responses instead of SSE by default
        stateless=True,
    )

    # Create SSE session manager
    sse_session_manager = StreamableHTTPSessionManager(
        app=server,
        event_store=None,
        json_response=False,  # Use SSE responses for this endpoint
        stateless=True,
    )

    async def initialize_session_managers():
        """Initialize the session managers. Can be called from main app lifespan."""
        global _SESSION_MANAGERS_INITIALIZED, _SESSION_MANAGER_TASK

        if _SESSION_MANAGERS_INITIALIZED:
            return

        verbose_logger.info("Initializing MCP session managers...")

        # Create a task to run the session managers
        async def run_session_managers():
            async with session_manager.run():
                async with sse_session_manager.run():
                    verbose_logger.info(
                        "MCP Server started with StreamableHTTP and SSE session managers!"
                    )
                    try:
                        # Keep running until cancelled
                        while True:
                            await asyncio.sleep(1)
                    except asyncio.CancelledError:
                        verbose_logger.info("MCP session managers shutting down...")
                        raise

        _SESSION_MANAGER_TASK = asyncio.create_task(run_session_managers())
        _SESSION_MANAGERS_INITIALIZED = True
        verbose_logger.info("MCP session managers initialization completed!")

    async def shutdown_session_managers():
        """Shutdown the session managers."""
        global _SESSION_MANAGERS_INITIALIZED, _SESSION_MANAGER_TASK

        if _SESSION_MANAGER_TASK and not _SESSION_MANAGER_TASK.done():
            verbose_logger.info("Shutting down MCP session managers...")
            _SESSION_MANAGER_TASK.cancel()
            try:
                await _SESSION_MANAGER_TASK
            except asyncio.CancelledError:
                pass

        _SESSION_MANAGERS_INITIALIZED = False
        _SESSION_MANAGER_TASK = None

    @contextlib.asynccontextmanager
    async def lifespan(app) -> AsyncIterator[None]:
        """Application lifespan context manager."""
        await initialize_session_managers()
        try:
            yield
        finally:
            await shutdown_session_managers()

    ########################################################
    ############### MCP Server Routes #######################
    ########################################################

    @server.list_tools()
    async def list_tools() -> list[MCPTool]:
        """
        List all available tools
        """
        # Get user authentication from context variable
        user_api_key_auth, mcp_auth_header = get_auth_context()
        verbose_logger.debug(
            f"MCP list_tools - User API Key Auth from context: {user_api_key_auth}"
        )
        return await _list_mcp_tools(
            user_api_key_auth=user_api_key_auth,
            mcp_auth_header=mcp_auth_header,
        )

    @server.call_tool()
    async def mcp_server_tool_call(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]:
        """
        Call a specific tool with the provided arguments

        Args:
            name (str): Name of the tool to call
            arguments (Dict[str, Any] | None): Arguments to pass to the tool

        Returns:
            List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]: Tool execution results

        Raises:
            HTTPException: If tool not found or arguments missing
        """
        # Validate arguments
        user_api_key_auth, mcp_auth_header = get_auth_context()
        verbose_logger.debug(
            f"MCP mcp_server_tool_call - User API Key Auth from context: {user_api_key_auth}"
        )
        response = await call_mcp_tool(
            name=name,
            arguments=arguments,
            user_api_key_auth=user_api_key_auth,
            mcp_auth_header=mcp_auth_header,
        )
        return response

    ########################################################
    ############ End of MCP Server Routes ##################
    ########################################################

    ########################################################
    ############ Helper Functions ##########################
    ########################################################

    async def _list_mcp_tools(
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
        mcp_auth_header: Optional[str] = None,
    ) -> List[MCPTool]:
        """
        List all available tools

        Args:
            user_api_key_auth: User authentication info for access control
        """
        tools = []
        for tool in global_mcp_tool_registry.list_tools():
            tools.append(
                MCPTool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.input_schema,
                )
            )
        verbose_logger.debug(
            "GLOBAL MCP TOOLS: %s", global_mcp_tool_registry.list_tools()
        )

        tools_from_mcp_servers: List[MCPTool] = (
            await global_mcp_server_manager.list_tools(
                user_api_key_auth=user_api_key_auth,
                mcp_auth_header=mcp_auth_header,
            )
        )
        verbose_logger.debug("TOOLS FROM MCP SERVERS: %s", tools_from_mcp_servers)
        if tools_from_mcp_servers is not None:
            tools.extend(tools_from_mcp_servers)
        return tools

    @client
    async def call_mcp_tool(
        name: str, 
        arguments: Optional[Dict[str, Any]] = None, 
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
        mcp_auth_header: Optional[str] = None, 
        **kwargs: Any
    ) -> List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]:
        """
        Call a specific tool with the provided arguments
        """
        if arguments is None:
            raise HTTPException(
                status_code=400, detail="Request arguments are required"
            )

        standard_logging_mcp_tool_call: StandardLoggingMCPToolCall = (
            _get_standard_logging_mcp_tool_call(
                name=name,
                arguments=arguments,
            )
        )
        litellm_logging_obj: Optional[LiteLLMLoggingObj] = kwargs.get(
            "litellm_logging_obj", None
        )
        if litellm_logging_obj:
            litellm_logging_obj.model_call_details["mcp_tool_call_metadata"] = (
                standard_logging_mcp_tool_call
            )
            litellm_logging_obj.model_call_details["model"] = (
                f"{MCP_TOOL_NAME_PREFIX}: {standard_logging_mcp_tool_call.get('name') or ''}"
            )
            litellm_logging_obj.model_call_details["custom_llm_provider"] = (
                standard_logging_mcp_tool_call.get("mcp_server_name")
            )

        # Try managed server tool first
        if name in global_mcp_server_manager.tool_name_to_mcp_server_name_mapping:
            return await _handle_managed_mcp_tool(
                name=name,
                arguments=arguments,
                user_api_key_auth=user_api_key_auth,
                mcp_auth_header=mcp_auth_header,
            )

        # Fall back to local tool registry
        return await _handle_local_mcp_tool(name, arguments)

    def _get_standard_logging_mcp_tool_call(
        name: str,
        arguments: Dict[str, Any],
    ) -> StandardLoggingMCPToolCall:
        mcp_server = global_mcp_server_manager._get_mcp_server_from_tool_name(name)
        if mcp_server:
            mcp_info = mcp_server.mcp_info or {}
            return StandardLoggingMCPToolCall(
                name=name,
                arguments=arguments,
                mcp_server_name=mcp_info.get("server_name"),
                mcp_server_logo_url=mcp_info.get("logo_url"),
            )
        else:
            return StandardLoggingMCPToolCall(
                name=name,
                arguments=arguments,
            )

    async def _handle_managed_mcp_tool(
        name: str, 
        arguments: Dict[str, Any],
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
        mcp_auth_header: Optional[str] = None,
    ) -> List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]:
        """Handle tool execution for managed server tools"""
        call_tool_result = await global_mcp_server_manager.call_tool(
            name=name,
            arguments=arguments,
            user_api_key_auth=user_api_key_auth,
            mcp_auth_header=mcp_auth_header,
        )
        verbose_logger.debug("CALL TOOL RESULT: %s", call_tool_result)
        return call_tool_result.content

    async def _handle_local_mcp_tool(
        name: str, arguments: Dict[str, Any]
    ) -> List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]:
        """Handle tool execution for local registry tools"""
        tool = global_mcp_tool_registry.get_tool(name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")

        try:
            result = tool.handler(**arguments)
            return [MCPTextContent(text=str(result), type="text")]
        except Exception as e:
            return [MCPTextContent(text=f"Error: {str(e)}", type="text")]

    async def handle_streamable_http_mcp(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle MCP requests through StreamableHTTP."""
        try:
            # Validate headers and log request info
            user_api_key_auth, mcp_auth_header = (
                await UserAPIKeyAuthMCP.user_api_key_auth_mcp(scope)
            )
            # Set the auth context variable for easy access in MCP functions
            set_auth_context(
                user_api_key_auth=user_api_key_auth,
                mcp_auth_header=mcp_auth_header,
            )

            # Ensure session managers are initialized
            if not _SESSION_MANAGERS_INITIALIZED:
                await initialize_session_managers()
                # Give it a moment to start up
                await asyncio.sleep(0.1)

            await session_manager.handle_request(scope, receive, send)
        except Exception as e:
            verbose_logger.exception(f"Error handling MCP request: {e}")
            raise e

    async def handle_sse_mcp(scope: Scope, receive: Receive, send: Send) -> None:
        """Handle MCP requests through SSE."""
        try:
            # Validate headers and log request info
            user_api_key_auth, mcp_auth_header = (
                await UserAPIKeyAuthMCP.user_api_key_auth_mcp(scope)
            )
            # Set the auth context variable for easy access in MCP functions
            set_auth_context(
                user_api_key_auth=user_api_key_auth,
                mcp_auth_header=mcp_auth_header,
            )

            # Ensure session managers are initialized
            if not _SESSION_MANAGERS_INITIALIZED:
                await initialize_session_managers()
                # Give it a moment to start up
                await asyncio.sleep(0.1)

            await sse_session_manager.handle_request(scope, receive, send)
        except Exception as e:
            verbose_logger.exception(f"Error handling MCP request: {e}")
            raise e

    app = FastAPI(
        title=LITELLM_MCP_SERVER_NAME,
        description=LITELLM_MCP_SERVER_DESCRIPTION,
        version=LITELLM_MCP_SERVER_VERSION,
        lifespan=lifespan,
    )

    # Routes
    @app.get(
        "/enabled",
        description="Returns if the MCP server is enabled",
    )
    def get_mcp_server_enabled() -> Dict[str, bool]:
        """
        Returns if the MCP server is enabled
        """
        return {"enabled": MCP_AVAILABLE}

    # Mount the MCP handlers
    app.mount("/", handle_streamable_http_mcp)
    app.mount("/sse", handle_sse_mcp)
    app.add_middleware(AuthContextMiddleware)

    ########################################################
    ############ Auth Context Functions ####################
    ########################################################

    def set_auth_context(user_api_key_auth: UserAPIKeyAuth, mcp_auth_header: Optional[str] = None) -> None:
        """
        Set the UserAPIKeyAuth in the auth context variable.

        Args:
            user_api_key_auth: UserAPIKeyAuth object
            mcp_auth_header: MCP auth header to be passed to the MCP server
        """
        auth_user = LiteLLMAuthenticatedUser(
            user_api_key_auth=user_api_key_auth,
            mcp_auth_header=mcp_auth_header,
        )
        auth_context_var.set(auth_user)

    def get_auth_context() -> Tuple[Optional[UserAPIKeyAuth], Optional[str]]:
        """
        Get the UserAPIKeyAuth from the auth context variable.

        Returns:
            Tuple[Optional[UserAPIKeyAuth], Optional[str]]: UserAPIKeyAuth object and MCP auth header
        """
        auth_user = auth_context_var.get()
        if auth_user and isinstance(auth_user, LiteLLMAuthenticatedUser):
            return auth_user.user_api_key_auth, auth_user.mcp_auth_header
        return None, None

    ########################################################
    ############ End of Auth Context Functions #############
    ########################################################

else:
    app = FastAPI()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_cell_widths.py ===
# Auto generated by make_terminal_widths.py

CELL_WIDTHS = [
    (0, 0, 0),
    (1, 31, -1),
    (127, 159, -1),
    (173, 173, 0),
    (768, 879, 0),
    (1155, 1161, 0),
    (1425, 1469, 0),
    (1471, 1471, 0),
    (1473, 1474, 0),
    (1476, 1477, 0),
    (1479, 1479, 0),
    (1536, 1541, 0),
    (1552, 1562, 0),
    (1564, 1564, 0),
    (1611, 1631, 0),
    (1648, 1648, 0),
    (1750, 1757, 0),
    (1759, 1764, 0),
    (1767, 1768, 0),
    (1770, 1773, 0),
    (1807, 1807, 0),
    (1809, 1809, 0),
    (1840, 1866, 0),
    (1958, 1968, 0),
    (2027, 2035, 0),
    (2045, 2045, 0),
    (2070, 2073, 0),
    (2075, 2083, 0),
    (2085, 2087, 0),
    (2089, 2093, 0),
    (2137, 2139, 0),
    (2192, 2193, 0),
    (2200, 2207, 0),
    (2250, 2307, 0),
    (2362, 2364, 0),
    (2366, 2383, 0),
    (2385, 2391, 0),
    (2402, 2403, 0),
    (2433, 2435, 0),
    (2492, 2492, 0),
    (2494, 2500, 0),
    (2503, 2504, 0),
    (2507, 2509, 0),
    (2519, 2519, 0),
    (2530, 2531, 0),
    (2558, 2558, 0),
    (2561, 2563, 0),
    (2620, 2620, 0),
    (2622, 2626, 0),
    (2631, 2632, 0),
    (2635, 2637, 0),
    (2641, 2641, 0),
    (2672, 2673, 0),
    (2677, 2677, 0),
    (2689, 2691, 0),
    (2748, 2748, 0),
    (2750, 2757, 0),
    (2759, 2761, 0),
    (2763, 2765, 0),
    (2786, 2787, 0),
    (2810, 2815, 0),
    (2817, 2819, 0),
    (2876, 2876, 0),
    (2878, 2884, 0),
    (2887, 2888, 0),
    (2891, 2893, 0),
    (2901, 2903, 0),
    (2914, 2915, 0),
    (2946, 2946, 0),
    (3006, 3010, 0),
    (3014, 3016, 0),
    (3018, 3021, 0),
    (3031, 3031, 0),
    (3072, 3076, 0),
    (3132, 3132, 0),
    (3134, 3140, 0),
    (3142, 3144, 0),
    (3146, 3149, 0),
    (3157, 3158, 0),
    (3170, 3171, 0),
    (3201, 3203, 0),
    (3260, 3260, 0),
    (3262, 3268, 0),
    (3270, 3272, 0),
    (3274, 3277, 0),
    (3285, 3286, 0),
    (3298, 3299, 0),
    (3315, 3315, 0),
    (3328, 3331, 0),
    (3387, 3388, 0),
    (3390, 3396, 0),
    (3398, 3400, 0),
    (3402, 3405, 0),
    (3415, 3415, 0),
    (3426, 3427, 0),
    (3457, 3459, 0),
    (3530, 3530, 0),
    (3535, 3540, 0),
    (3542, 3542, 0),
    (3544, 3551, 0),
    (3570, 3571, 0),
    (3633, 3633, 0),
    (3636, 3642, 0),
    (3655, 3662, 0),
    (3761, 3761, 0),
    (3764, 3772, 0),
    (3784, 3790, 0),
    (3864, 3865, 0),
    (3893, 3893, 0),
    (3895, 3895, 0),
    (3897, 3897, 0),
    (3902, 3903, 0),
    (3953, 3972, 0),
    (3974, 3975, 0),
    (3981, 3991, 0),
    (3993, 4028, 0),
    (4038, 4038, 0),
    (4139, 4158, 0),
    (4182, 4185, 0),
    (4190, 4192, 0),
    (4194, 4196, 0),
    (4199, 4205, 0),
    (4209, 4212, 0),
    (4226, 4237, 0),
    (4239, 4239, 0),
    (4250, 4253, 0),
    (4352, 4447, 2),
    (4448, 4607, 0),
    (4957, 4959, 0),
    (5906, 5909, 0),
    (5938, 5940, 0),
    (5970, 5971, 0),
    (6002, 6003, 0),
    (6068, 6099, 0),
    (6109, 6109, 0),
    (6155, 6159, 0),
    (6277, 6278, 0),
    (6313, 6313, 0),
    (6432, 6443, 0),
    (6448, 6459, 0),
    (6679, 6683, 0),
    (6741, 6750, 0),
    (6752, 6780, 0),
    (6783, 6783, 0),
    (6832, 6862, 0),
    (6912, 6916, 0),
    (6964, 6980, 0),
    (7019, 7027, 0),
    (7040, 7042, 0),
    (7073, 7085, 0),
    (7142, 7155, 0),
    (7204, 7223, 0),
    (7376, 7378, 0),
    (7380, 7400, 0),
    (7405, 7405, 0),
    (7412, 7412, 0),
    (7415, 7417, 0),
    (7616, 7679, 0),
    (8203, 8207, 0),
    (8232, 8238, 0),
    (8288, 8292, 0),
    (8294, 8303, 0),
    (8400, 8432, 0),
    (8986, 8987, 2),
    (9001, 9002, 2),
    (9193, 9196, 2),
    (9200, 9200, 2),
    (9203, 9203, 2),
    (9725, 9726, 2),
    (9748, 9749, 2),
    (9800, 9811, 2),
    (9855, 9855, 2),
    (9875, 9875, 2),
    (9889, 9889, 2),
    (9898, 9899, 2),
    (9917, 9918, 2),
    (9924, 9925, 2),
    (9934, 9934, 2),
    (9940, 9940, 2),
    (9962, 9962, 2),
    (9970, 9971, 2),
    (9973, 9973, 2),
    (9978, 9978, 2),
    (9981, 9981, 2),
    (9989, 9989, 2),
    (9994, 9995, 2),
    (10024, 10024, 2),
    (10060, 10060, 2),
    (10062, 10062, 2),
    (10067, 10069, 2),
    (10071, 10071, 2),
    (10133, 10135, 2),
    (10160, 10160, 2),
    (10175, 10175, 2),
    (11035, 11036, 2),
    (11088, 11088, 2),
    (11093, 11093, 2),
    (11503, 11505, 0),
    (11647, 11647, 0),
    (11744, 11775, 0),
    (11904, 11929, 2),
    (11931, 12019, 2),
    (12032, 12245, 2),
    (12272, 12329, 2),
    (12330, 12335, 0),
    (12336, 12350, 2),
    (12353, 12438, 2),
    (12441, 12442, 0),
    (12443, 12543, 2),
    (12549, 12591, 2),
    (12593, 12686, 2),
    (12688, 12771, 2),
    (12783, 12830, 2),
    (12832, 12871, 2),
    (12880, 19903, 2),
    (19968, 42124, 2),
    (42128, 42182, 2),
    (42607, 42610, 0),
    (42612, 42621, 0),
    (42654, 42655, 0),
    (42736, 42737, 0),
    (43010, 43010, 0),
    (43014, 43014, 0),
    (43019, 43019, 0),
    (43043, 43047, 0),
    (43052, 43052, 0),
    (43136, 43137, 0),
    (43188, 43205, 0),
    (43232, 43249, 0),
    (43263, 43263, 0),
    (43302, 43309, 0),
    (43335, 43347, 0),
    (43360, 43388, 2),
    (43392, 43395, 0),
    (43443, 43456, 0),
    (43493, 43493, 0),
    (43561, 43574, 0),
    (43587, 43587, 0),
    (43596, 43597, 0),
    (43643, 43645, 0),
    (43696, 43696, 0),
    (43698, 43700, 0),
    (43703, 43704, 0),
    (43710, 43711, 0),
    (43713, 43713, 0),
    (43755, 43759, 0),
    (43765, 43766, 0),
    (44003, 44010, 0),
    (44012, 44013, 0),
    (44032, 55203, 2),
    (55216, 55295, 0),
    (63744, 64255, 2),
    (64286, 64286, 0),
    (65024, 65039, 0),
    (65040, 65049, 2),
    (65056, 65071, 0),
    (65072, 65106, 2),
    (65108, 65126, 2),
    (65128, 65131, 2),
    (65279, 65279, 0),
    (65281, 65376, 2),
    (65504, 65510, 2),
    (65529, 65531, 0),
    (66045, 66045, 0),
    (66272, 66272, 0),
    (66422, 66426, 0),
    (68097, 68099, 0),
    (68101, 68102, 0),
    (68108, 68111, 0),
    (68152, 68154, 0),
    (68159, 68159, 0),
    (68325, 68326, 0),
    (68900, 68903, 0),
    (69291, 69292, 0),
    (69373, 69375, 0),
    (69446, 69456, 0),
    (69506, 69509, 0),
    (69632, 69634, 0),
    (69688, 69702, 0),
    (69744, 69744, 0),
    (69747, 69748, 0),
    (69759, 69762, 0),
    (69808, 69818, 0),
    (69821, 69821, 0),
    (69826, 69826, 0),
    (69837, 69837, 0),
    (69888, 69890, 0),
    (69927, 69940, 0),
    (69957, 69958, 0),
    (70003, 70003, 0),
    (70016, 70018, 0),
    (70067, 70080, 0),
    (70089, 70092, 0),
    (70094, 70095, 0),
    (70188, 70199, 0),
    (70206, 70206, 0),
    (70209, 70209, 0),
    (70367, 70378, 0),
    (70400, 70403, 0),
    (70459, 70460, 0),
    (70462, 70468, 0),
    (70471, 70472, 0),
    (70475, 70477, 0),
    (70487, 70487, 0),
    (70498, 70499, 0),
    (70502, 70508, 0),
    (70512, 70516, 0),
    (70709, 70726, 0),
    (70750, 70750, 0),
    (70832, 70851, 0),
    (71087, 71093, 0),
    (71096, 71104, 0),
    (71132, 71133, 0),
    (71216, 71232, 0),
    (71339, 71351, 0),
    (71453, 71467, 0),
    (71724, 71738, 0),
    (71984, 71989, 0),
    (71991, 71992, 0),
    (71995, 71998, 0),
    (72000, 72000, 0),
    (72002, 72003, 0),
    (72145, 72151, 0),
    (72154, 72160, 0),
    (72164, 72164, 0),
    (72193, 72202, 0),
    (72243, 72249, 0),
    (72251, 72254, 0),
    (72263, 72263, 0),
    (72273, 72283, 0),
    (72330, 72345, 0),
    (72751, 72758, 0),
    (72760, 72767, 0),
    (72850, 72871, 0),
    (72873, 72886, 0),
    (73009, 73014, 0),
    (73018, 73018, 0),
    (73020, 73021, 0),
    (73023, 73029, 0),
    (73031, 73031, 0),
    (73098, 73102, 0),
    (73104, 73105, 0),
    (73107, 73111, 0),
    (73459, 73462, 0),
    (73472, 73473, 0),
    (73475, 73475, 0),
    (73524, 73530, 0),
    (73534, 73538, 0),
    (78896, 78912, 0),
    (78919, 78933, 0),
    (92912, 92916, 0),
    (92976, 92982, 0),
    (94031, 94031, 0),
    (94033, 94087, 0),
    (94095, 94098, 0),
    (94176, 94179, 2),
    (94180, 94180, 0),
    (94192, 94193, 0),
    (94208, 100343, 2),
    (100352, 101589, 2),
    (101632, 101640, 2),
    (110576, 110579, 2),
    (110581, 110587, 2),
    (110589, 110590, 2),
    (110592, 110882, 2),
    (110898, 110898, 2),
    (110928, 110930, 2),
    (110933, 110933, 2),
    (110948, 110951, 2),
    (110960, 111355, 2),
    (113821, 113822, 0),
    (113824, 113827, 0),
    (118528, 118573, 0),
    (118576, 118598, 0),
    (119141, 119145, 0),
    (119149, 119170, 0),
    (119173, 119179, 0),
    (119210, 119213, 0),
    (119362, 119364, 0),
    (121344, 121398, 0),
    (121403, 121452, 0),
    (121461, 121461, 0),
    (121476, 121476, 0),
    (121499, 121503, 0),
    (121505, 121519, 0),
    (122880, 122886, 0),
    (122888, 122904, 0),
    (122907, 122913, 0),
    (122915, 122916, 0),
    (122918, 122922, 0),
    (123023, 123023, 0),
    (123184, 123190, 0),
    (123566, 123566, 0),
    (123628, 123631, 0),
    (124140, 124143, 0),
    (125136, 125142, 0),
    (125252, 125258, 0),
    (126980, 126980, 2),
    (127183, 127183, 2),
    (127374, 127374, 2),
    (127377, 127386, 2),
    (127488, 127490, 2),
    (127504, 127547, 2),
    (127552, 127560, 2),
    (127568, 127569, 2),
    (127584, 127589, 2),
    (127744, 127776, 2),
    (127789, 127797, 2),
    (127799, 127868, 2),
    (127870, 127891, 2),
    (127904, 127946, 2),
    (127951, 127955, 2),
    (127968, 127984, 2),
    (127988, 127988, 2),
    (127992, 127994, 2),
    (127995, 127999, 0),
    (128000, 128062, 2),
    (128064, 128064, 2),
    (128066, 128252, 2),
    (128255, 128317, 2),
    (128331, 128334, 2),
    (128336, 128359, 2),
    (128378, 128378, 2),
    (128405, 128406, 2),
    (128420, 128420, 2),
    (128507, 128591, 2),
    (128640, 128709, 2),
    (128716, 128716, 2),
    (128720, 128722, 2),
    (128725, 128727, 2),
    (128732, 128735, 2),
    (128747, 128748, 2),
    (128756, 128764, 2),
    (128992, 129003, 2),
    (129008, 129008, 2),
    (129292, 129338, 2),
    (129340, 129349, 2),
    (129351, 129535, 2),
    (129648, 129660, 2),
    (129664, 129672, 2),
    (129680, 129725, 2),
    (129727, 129733, 2),
    (129742, 129755, 2),
    (129760, 129768, 2),
    (129776, 129784, 2),
    (131072, 196605, 2),
    (196608, 262141, 2),
    (917505, 917505, 0),
    (917536, 917631, 0),
    (917760, 917999, 0),
]