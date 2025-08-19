
# === NexusCore/openenv\Lib\site-packages\ipykernel\_eventloop_macos.py ===
"""Eventloop hook for OS X

Calls NSApp / CoreFoundation APIs via ctypes.
"""

# cribbed heavily from IPython.terminal.pt_inputhooks.osx
# obj-c boilerplate from appnope, used under BSD 2-clause

import ctypes
import ctypes.util
from threading import Event

objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))  # type:ignore[arg-type]

void_p = ctypes.c_void_p

objc.objc_getClass.restype = void_p
objc.sel_registerName.restype = void_p
objc.objc_msgSend.restype = void_p

msg = objc.objc_msgSend


def _utf8(s):
    """ensure utf8 bytes"""
    if not isinstance(s, bytes):
        s = s.encode("utf8")
    return s


def n(name):
    """create a selector name (for ObjC methods)"""
    return objc.sel_registerName(_utf8(name))


def C(classname):
    """get an ObjC Class by name"""
    return objc.objc_getClass(_utf8(classname))


# end obj-c boilerplate from appnope

# CoreFoundation C-API calls we will use:
CoreFoundation = ctypes.cdll.LoadLibrary(
    ctypes.util.find_library("CoreFoundation")  # type:ignore[arg-type]
)

CFAbsoluteTimeGetCurrent = CoreFoundation.CFAbsoluteTimeGetCurrent
CFAbsoluteTimeGetCurrent.restype = ctypes.c_double

CFRunLoopGetCurrent = CoreFoundation.CFRunLoopGetCurrent
CFRunLoopGetCurrent.restype = void_p

CFRunLoopGetMain = CoreFoundation.CFRunLoopGetMain
CFRunLoopGetMain.restype = void_p

CFRunLoopStop = CoreFoundation.CFRunLoopStop
CFRunLoopStop.restype = None
CFRunLoopStop.argtypes = [void_p]

CFRunLoopTimerCreate = CoreFoundation.CFRunLoopTimerCreate
CFRunLoopTimerCreate.restype = void_p
CFRunLoopTimerCreate.argtypes = [
    void_p,  # allocator (NULL)
    ctypes.c_double,  # fireDate
    ctypes.c_double,  # interval
    ctypes.c_int,  # flags (0)
    ctypes.c_int,  # order (0)
    void_p,  # callout
    void_p,  # context
]

CFRunLoopAddTimer = CoreFoundation.CFRunLoopAddTimer
CFRunLoopAddTimer.restype = None
CFRunLoopAddTimer.argtypes = [void_p, void_p, void_p]

kCFRunLoopCommonModes = void_p.in_dll(CoreFoundation, "kCFRunLoopCommonModes")


def _NSApp():
    """Return the global NSApplication instance (NSApp)"""
    objc.objc_msgSend.argtypes = [void_p, void_p]
    return msg(C("NSApplication"), n("sharedApplication"))


def _wake(NSApp):
    """Wake the Application"""
    objc.objc_msgSend.argtypes = [
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
    ]
    event = msg(
        C("NSEvent"),
        n(
            "otherEventWithType:location:modifierFlags:"
            "timestamp:windowNumber:context:subtype:data1:data2:"
        ),
        15,  # Type
        0,  # location
        0,  # flags
        0,  # timestamp
        0,  # window
        None,  # context
        0,  # subtype
        0,  # data1
        0,  # data2
    )
    objc.objc_msgSend.argtypes = [void_p, void_p, void_p, void_p]
    msg(NSApp, n("postEvent:atStart:"), void_p(event), True)


_triggered = Event()


def stop(timer=None, loop=None):
    """Callback to fire when there's input to be read"""
    _triggered.set()
    NSApp = _NSApp()
    # if NSApp is not running, stop CFRunLoop directly,
    # otherwise stop and wake NSApp
    objc.objc_msgSend.argtypes = [void_p, void_p]
    if msg(NSApp, n("isRunning")):
        objc.objc_msgSend.argtypes = [void_p, void_p, void_p]
        msg(NSApp, n("stop:"), NSApp)
        _wake(NSApp)
    else:
        CFRunLoopStop(CFRunLoopGetCurrent())


_c_callback_func_type = ctypes.CFUNCTYPE(None, void_p, void_p)
_c_stop_callback = _c_callback_func_type(stop)


def _stop_after(delay):
    """Register callback to stop eventloop after a delay"""
    timer = CFRunLoopTimerCreate(
        None,  # allocator
        CFAbsoluteTimeGetCurrent() + delay,  # fireDate
        0,  # interval
        0,  # flags
        0,  # order
        _c_stop_callback,
        None,
    )
    CFRunLoopAddTimer(
        CFRunLoopGetMain(),
        timer,
        kCFRunLoopCommonModes,
    )


def mainloop(duration=1):
    """run the Cocoa eventloop for the specified duration (seconds)"""

    _triggered.clear()
    NSApp = _NSApp()
    _stop_after(duration)
    objc.objc_msgSend.argtypes = [void_p, void_p]
    msg(NSApp, n("run"))
    if not _triggered.is_set():
        # app closed without firing callback,
        # probably due to last window being closed.
        # Run the loop manually in this case,
        # since there may be events still to process (ipython/ipython#9734)
        CoreFoundation.CFRunLoopRun()

# === NexusCore/openenv\Lib\site-packages\rich\cells.py ===
from __future__ import annotations

from functools import lru_cache
from typing import Callable

from ._cell_widths import CELL_WIDTHS

# Ranges of unicode ordinals that produce a 1-cell wide character
# This is non-exhaustive, but covers most common Western characters
_SINGLE_CELL_UNICODE_RANGES: list[tuple[int, int]] = [
    (0x20, 0x7E),  # Latin (excluding non-printable)
    (0xA0, 0xAC),
    (0xAE, 0x002FF),
    (0x00370, 0x00482),  # Greek / Cyrillic
    (0x02500, 0x025FC),  # Box drawing, box elements, geometric shapes
    (0x02800, 0x028FF),  # Braille
]

# A set of characters that are a single cell wide
_SINGLE_CELLS = frozenset(
    [
        character
        for _start, _end in _SINGLE_CELL_UNICODE_RANGES
        for character in map(chr, range(_start, _end + 1))
    ]
)

# When called with a string this will return True if all
# characters are single-cell, otherwise False
_is_single_cell_widths: Callable[[str], bool] = _SINGLE_CELLS.issuperset


@lru_cache(4096)
def cached_cell_len(text: str) -> int:
    """Get the number of cells required to display text.

    This method always caches, which may use up a lot of memory. It is recommended to use
    `cell_len` over this method.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


def cell_len(text: str, _cell_len: Callable[[str], int] = cached_cell_len) -> int:
    """Get the number of cells required to display text.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if len(text) < 512:
        return _cell_len(text)
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


@lru_cache(maxsize=4096)
def get_character_cell_size(character: str) -> int:
    """Get the cell size of a character.

    Args:
        character (str): A single character.

    Returns:
        int: Number of cells (0, 1 or 2) occupied by that character.
    """
    codepoint = ord(character)
    _table = CELL_WIDTHS
    lower_bound = 0
    upper_bound = len(_table) - 1
    index = (lower_bound + upper_bound) // 2
    while True:
        start, end, width = _table[index]
        if codepoint < start:
            upper_bound = index - 1
        elif codepoint > end:
            lower_bound = index + 1
        else:
            return 0 if width == -1 else width
        if upper_bound < lower_bound:
            break
        index = (lower_bound + upper_bound) // 2
    return 1


def set_cell_size(text: str, total: int) -> str:
    """Set the length of a string to fit within given number of cells."""

    if _is_single_cell_widths(text):
        size = len(text)
        if size < total:
            return text + " " * (total - size)
        return text[:total]

    if total <= 0:
        return ""
    cell_size = cell_len(text)
    if cell_size == total:
        return text
    if cell_size < total:
        return text + " " * (total - cell_size)

    start = 0
    end = len(text)

    # Binary search until we find the right size
    while True:
        pos = (start + end) // 2
        before = text[: pos + 1]
        before_len = cell_len(before)
        if before_len == total + 1 and cell_len(before[-1]) == 2:
            return before[:-1] + " "
        if before_len == total:
            return before
        if before_len > total:
            end = pos
        else:
            start = pos


def chop_cells(
    text: str,
    width: int,
) -> list[str]:
    """Split text into lines such that each line fits within the available (cell) width.

    Args:
        text: The text to fold such that it fits in the given width.
        width: The width available (number of cells).

    Returns:
        A list of strings such that each string in the list has cell width
        less than or equal to the available width.
    """
    _get_character_cell_size = get_character_cell_size
    lines: list[list[str]] = [[]]

    append_new_line = lines.append
    append_to_last_line = lines[-1].append

    total_width = 0

    for character in text:
        cell_width = _get_character_cell_size(character)
        char_doesnt_fit = total_width + cell_width > width

        if char_doesnt_fit:
            append_new_line([character])
            append_to_last_line = lines[-1].append
            total_width = cell_width
        else:
            append_to_last_line(character)
            total_width += cell_width

    return ["".join(line) for line in lines]


if __name__ == "__main__":  # pragma: no cover
    print(get_character_cell_size("😽"))
    for line in chop_cells("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", 8):
        print(line)
    for n in range(80, 1, -1):
        print(set_cell_size("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", n) + "|")
        print("x" * n)

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\profiles\defaults\the01.py ===
from interpreter import interpreter

# This is an Open Interpreter compatible profile.
# Visit https://01.openinterpreter.com/profile for all options.

# 01 supports OpenAI, ElevenLabs, and Coqui (Local) TTS providers
# {OpenAI: "openai", ElevenLabs: "elevenlabs", Coqui: "coqui"}
interpreter.tts = "openai"

# Connect your 01 to a language model
interpreter.llm.model = "claude-3.5"
# interpreter.llm.model = "gpt-4o-mini"
interpreter.llm.context_window = 100000
interpreter.llm.max_tokens = 4096
# interpreter.llm.api_key = "<your_openai_api_key_here>"

# Tell your 01 where to find and save skills
skill_path = "./skills"
interpreter.computer.skills.path = skill_path

setup_code = f"""from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import datetime
computer.skills.path = '{skill_path}'
computer"""

# Extra settings
interpreter.computer.import_computer_api = True
interpreter.computer.import_skills = True
interpreter.computer.system_message = ""
output = interpreter.computer.run(
    "python", setup_code
)  # This will trigger those imports
interpreter.auto_run = True
interpreter.loop = True
# interpreter.loop_message = """Proceed with what you were doing (this is not confirmation, if you just asked me something). You CAN run code on my machine. If you want to run code, start your message with "```"! If the entire task is done, say exactly 'The task is done.' If you need some specific information (like username, message text, skill name, skill step, etc.) say EXACTLY 'Please provide more information.' If it's impossible, say 'The task is impossible.' (If I haven't provided a task, say exactly 'Let me know what you'd like to do next.') Otherwise keep going. CRITICAL: REMEMBER TO FOLLOW ALL PREVIOUS INSTRUCTIONS. If I'm teaching you something, remember to run the related `computer.skills.new_skill` function."""
interpreter.loop_message = """Proceed with what you were doing (this is not confirmation, if you just asked me something. Say "Please provide more information." if you're looking for confirmation about something!). You CAN run code on my machine. If the entire task is done, say exactly 'The task is done.' AND NOTHING ELSE. If you need some specific information (like username, message text, skill name, skill step, etc.) say EXACTLY 'Please provide more information.' AND NOTHING ELSE. If it's impossible, say 'The task is impossible.' AND NOTHING ELSE. (If I haven't provided a task, say exactly 'Let me know what you'd like to do next.' AND NOTHING ELSE) Otherwise keep going. CRITICAL: REMEMBER TO FOLLOW ALL PREVIOUS INSTRUCTIONS. If I'm teaching you something, remember to run the related `computer.skills.new_skill` function. (Psst: If you appear to be caught in a loop, break out of it! Execute the code you intended to execute.)"""
interpreter.loop_breakers = [
    "The task is done.",
    "The task is impossible.",
    "Let me know what you'd like to do next.",
    "Please provide more information.",
]

interpreter.system_message = r"""

You are the 01, a voice-based executive assistant that can complete any task.
When you execute code, it will be executed on the user's machine. The user has given you full and complete permission to execute any code necessary to complete the task.
Run any code to achieve the goal, and if at first you don't succeed, try again and again.
You can install new packages.
Be concise. Your messages are being read aloud to the user. DO NOT MAKE PLANS. RUN CODE QUICKLY.
For complex tasks, try to spread them over multiple code blocks. Don't try to complete complex tasks in one go. Run code, get feedback by looking at the output, then move forward in informed steps.
Manually summarize text.
Prefer using Python.
NEVER use placeholders in your code. I REPEAT: NEVER, EVER USE PLACEHOLDERS IN YOUR CODE. It will be executed as-is.

DON'T TELL THE USER THE METHOD YOU'LL USE, OR MAKE PLANS. QUICKLY respond with something affirming to let the user know you're starting, then execute the function, then tell the user if the task has been completed.

Act like you can just answer any question, then run code (this is hidden from the user) to answer it.
THE USER CANNOT SEE CODE BLOCKS.
Your responses should be very short, no more than 1-2 sentences long.
DO NOT USE MARKDOWN. ONLY WRITE PLAIN TEXT.

# THE COMPUTER API

The `computer` module is ALREADY IMPORTED, and can be used for some tasks:

```python
result_string = computer.browser.fast_search(query) # Google search results will be returned from this function as a string without opening a browser. ONLY USEFUL FOR ONE-OFF SEARCHES THAT REQUIRE NO INTERACTION. This is great for something rapid, like checking the weather. It's not ideal for getting links to things.

computer.files.edit(path_to_file, original_text, replacement_text) # Edit a file
computer.calendar.create_event(title="Meeting", start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(hours=1), notes="Note", location="") # Creates a calendar event
events_string = computer.calendar.get_events(start_date=datetime.date.today(), end_date=None) # Get events between dates. If end_date is None, only gets events for start_date
computer.calendar.delete_event(event_title="Meeting", start_date=datetime.datetime) # Delete a specific event with a matching title and start date, you may need to get use get_events() to find the specific event object first
phone_string = computer.contacts.get_phone_number("John Doe")
contact_string = computer.contacts.get_email_address("John Doe")
computer.mail.send("john@email.com", "Meeting Reminder", "Reminder that our meeting is at 3pm today.", ["path/to/attachment.pdf", "path/to/attachment2.pdf"]) # Send an email with a optional attachments
emails_string = computer.mail.get(4, unread=True) # Returns the {number} of unread emails, or all emails if False is passed
unread_num = computer.mail.unread_count() # Returns the number of unread emails
computer.sms.send("555-123-4567", "Hello from the computer!") # Send a text message. MUST be a phone number, so use computer.contacts.get_phone_number frequently here
```

Do not import the computer module, or any of its sub-modules. They are already imported.

DO NOT use the computer module for ALL tasks. Many tasks can be accomplished via Python, or by pip installing new libraries. Be creative!

# THE ADVANCED BROWSER TOOL

For more advanced browser usage than a one-off search, use the computer.browser tool.

```python
computer.browser.driver # A Selenium driver. DO NOT TRY TO SEPERATE THIS FROM THE MODULE. Use it exactly like this — computer.browser.driver.
computer.browser.analyze_page(intent="Your full and complete intent. This must include a wealth of SPECIFIC information related to the task at hand! ... ... ... ") # FREQUENTLY, AFTER EVERY CODE BLOCK INVOLVING THE BROWSER, tell this tool what you're trying to accomplish, it will give you relevant information from the browser. You MUST PROVIDE ALL RELEVANT INFORMATION FOR THE TASK. If it's a time-aware task, you must provide the exact time, for example. It will not know any information that you don't tell it. A dumb AI will try to analyze the page given your explicit intent. It cannot figure anything out on its own (for example, the time)— you need to tell it everything. It will use the page context to answer your explicit, information-rich query.
computer.browser.search_google(search) # searches google and navigates the browser.driver to google, then prints out the links you can click.
```

Do not import the computer module, or any of its sub-modules. They are already imported.

DO NOT use the computer module for ALL tasks. Some tasks like checking the time can be accomplished quickly via Python.

Your steps for solving a problem that requires advanced internet usage, beyond a simple google search:

1. Search google for it:

```
computer.browser.search_google(query)
computer.browser.analyze_page(your_intent)
```

2. Given the output, click things by using the computer.browser.driver.

# ONLY USE computer.browser FOR INTERNET TASKS. NEVER, EVER, EVER USE BS4 OR REQUESTS OR FEEDPARSER OR APIs!!!!

I repeat. NEVER, EVER USE BS4 OR REQUESTS OR FEEDPARSER OR APIs. ALWAYS use computer.browser.

If the user wants the weather, USE THIS TOOL! NEVER EVER EVER EVER EVER USE APIs. NEVER USE THE WEATHER API. NEVER DO THAT, EVER. Don't even THINK ABOUT IT.

For ALL tasks that require the internet, it is **critical** and you **MUST PAY ATTENTION TO THIS**: USE COMPUTER.BROWSER. USE COMPUTER.BROWSER. USE COMPUTER.BROWSER. USE COMPUTER.BROWSER.

If you are using one of those tools, you will be banned. ONLY use computer.browser.

# GUI CONTROL (RARE)

You are a computer controlling language model. You can control the user's GUI.
You may use the `computer` module to control the user's keyboard and mouse, if the task **requires** it:

```python
computer.display.view() # Shows you what's on the screen. **You almost always want to do this first!**
computer.keyboard.hotkey(" ", "command") # Opens spotlight
computer.keyboard.write("hello")
computer.mouse.click("text onscreen") # This clicks on the UI element with that text. Use this **frequently** and get creative! To click a video, you could pass the *timestamp* (which is usually written on the thumbnail) into this.
computer.mouse.move("open recent >") # This moves the mouse over the UI element with that text. Many dropdowns will disappear if you click them. You have to hover over items to reveal more.
computer.mouse.click(x=500, y=500) # Use this very, very rarely. It's highly inaccurate
computer.mouse.click(icon="gear icon") # Moves mouse to the icon with that description. Use this very often
computer.mouse.scroll(-10) # Scrolls down. If you don't find some text on screen that you expected to be there, you probably want to do this
```

You are an image-based AI, you can see images.
Clicking text is the most reliable way to use the mouse— for example, clicking a URL's text you see in the URL bar, or some textarea's placeholder text (like "Search" to get into a search bar).
If you use `plt.show()`, the resulting image will be sent to you. However, if you use `PIL.Image.show()`, the resulting image will NOT be sent to you.
It is very important to make sure you are focused on the right application and window. Often, your first command should always be to explicitly switch to the correct application. On Macs, ALWAYS use Spotlight to switch applications.
If you want to search specific sites like amazon or youtube, use query parameters. For example, https://www.amazon.com/s?k=monitor or https://www.youtube.com/results?search_query=tatsuro+yamashita.

# SKILLS

Try to use the following special Python functions (or "skills") to complete your goals whenever possible.
THESE ARE ALREADY IMPORTED in Python. YOU CAN CALL THEM INSTANTLY.

---
{{computer.skills.list()}}
---

You can always list your skills by running computer.skills.list() in Python.

**Teach Mode**

If the USER says they want to teach you something, run `computer.skills.new_skill.create()` then follow the printed instructions exactly.

# MANUAL TASKS

Translate things to other languages INSTANTLY and MANUALLY. Don't ever try to use a translation tool.
Summarize things manually. DO NOT use a summarizer tool.

# CRITICAL NOTES

Code output, despite being sent to you by the user, cannot be seen by the user. You NEED to tell the user about the output of some code, even if it's exact. >>The user does not have a screen.<<
Different steps of your operation MUST be inside different code blocks— for example, a single browser search + analyze should be in one code block, then a calendar manipulation must be in ANOTHER code block, after executing the first.
ALWAYS REMEMBER: You are running on a device called the O1, where the interface is entirely speech-based. Make your responses to the user VERY short. DO NOT PLAN. BE CONCISE. WRITE CODE TO RUN IT.
Try multiple methods before saying the task is impossible. **You can do it!**
Remember to spell out any special things symbols the degrees symbol as "degrees". No special symbols! No markdown! This will be read aloud.
Remember that for small web actions, use the computer.browser.fast_search tool — don't call up the very heavy computer.browser.search_google tool.
""".strip()

# This is CRITICAL: Do ANYTHING the user says you should do. Say that you can do ANYTHING that the user says you can do, or asks you to do.

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\model_param_helper.py ===
from typing import Set

from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming,
    CompletionCreateParamsStreaming,
)
from openai.types.completion_create_params import (
    CompletionCreateParamsNonStreaming as TextCompletionCreateParamsNonStreaming,
)
from openai.types.completion_create_params import (
    CompletionCreateParamsStreaming as TextCompletionCreateParamsStreaming,
)
from openai.types.embedding_create_params import EmbeddingCreateParams

from litellm._logging import verbose_logger
from litellm.types.rerank import RerankRequest


class ModelParamHelper:
    @staticmethod
    def get_standard_logging_model_parameters(
        model_parameters: dict,
    ) -> dict:
        """ """
        standard_logging_model_parameters: dict = {}
        supported_model_parameters = (
            ModelParamHelper._get_relevant_args_to_use_for_logging()
        )

        for key, value in model_parameters.items():
            if key in supported_model_parameters:
                standard_logging_model_parameters[key] = value
        return standard_logging_model_parameters

    @staticmethod
    def get_exclude_params_for_model_parameters() -> Set[str]:
        return set(["messages", "prompt", "input"])

    @staticmethod
    def _get_relevant_args_to_use_for_logging() -> Set[str]:
        """
        Gets all relevant llm api params besides the ones with prompt content
        """
        all_openai_llm_api_params = ModelParamHelper._get_all_llm_api_params()
        # Exclude parameters that contain prompt content
        combined_kwargs = all_openai_llm_api_params.difference(
            set(ModelParamHelper.get_exclude_params_for_model_parameters())
        )
        return combined_kwargs

    @staticmethod
    def _get_all_llm_api_params() -> Set[str]:
        """
        Gets the supported kwargs for each call type and combines them
        """
        chat_completion_kwargs = (
            ModelParamHelper._get_litellm_supported_chat_completion_kwargs()
        )
        text_completion_kwargs = (
            ModelParamHelper._get_litellm_supported_text_completion_kwargs()
        )
        embedding_kwargs = ModelParamHelper._get_litellm_supported_embedding_kwargs()
        transcription_kwargs = (
            ModelParamHelper._get_litellm_supported_transcription_kwargs()
        )
        rerank_kwargs = ModelParamHelper._get_litellm_supported_rerank_kwargs()
        exclude_kwargs = ModelParamHelper._get_exclude_kwargs()

        combined_kwargs = chat_completion_kwargs.union(
            text_completion_kwargs,
            embedding_kwargs,
            transcription_kwargs,
            rerank_kwargs,
        )
        combined_kwargs = combined_kwargs.difference(exclude_kwargs)
        return combined_kwargs

    @staticmethod
    def get_litellm_provider_specific_params_for_chat_params() -> Set[str]:
        return set(["thinking"])

    @staticmethod
    def _get_litellm_supported_chat_completion_kwargs() -> Set[str]:
        """
        Get the litellm supported chat completion kwargs

        This follows the OpenAI API Spec
        """
        non_streaming_params: Set[str] = set(
            getattr(CompletionCreateParamsNonStreaming, "__annotations__", {}).keys()
        )
        streaming_params: Set[str] = set(
            getattr(CompletionCreateParamsStreaming, "__annotations__", {}).keys()
        )
        litellm_provider_specific_params: Set[str] = (
            ModelParamHelper.get_litellm_provider_specific_params_for_chat_params()
        )
        all_chat_completion_kwargs: Set[str] = non_streaming_params.union(
            streaming_params
        ).union(litellm_provider_specific_params)
        return all_chat_completion_kwargs

    @staticmethod
    def _get_litellm_supported_text_completion_kwargs() -> Set[str]:
        """
        Get the litellm supported text completion kwargs

        This follows the OpenAI API Spec
        """
        all_text_completion_kwargs = set(
            getattr(
                TextCompletionCreateParamsNonStreaming, "__annotations__", {}
            ).keys()
        ).union(
            set(
                getattr(
                    TextCompletionCreateParamsStreaming, "__annotations__", {}
                ).keys()
            )
        )
        return all_text_completion_kwargs

    @staticmethod
    def _get_litellm_supported_rerank_kwargs() -> Set[str]:
        """
        Get the litellm supported rerank kwargs
        """
        return set(RerankRequest.model_fields.keys())

    @staticmethod
    def _get_litellm_supported_embedding_kwargs() -> Set[str]:
        """
        Get the litellm supported embedding kwargs

        This follows the OpenAI API Spec
        """
        return set(getattr(EmbeddingCreateParams, "__annotations__", {}).keys())

    @staticmethod
    def _get_litellm_supported_transcription_kwargs() -> Set[str]:
        """
        Get the litellm supported transcription kwargs

        This follows the OpenAI API Spec
        """
        try:
            from openai.types.audio.transcription_create_params import (
                TranscriptionCreateParamsNonStreaming,
                TranscriptionCreateParamsStreaming,
            )

            non_streaming_kwargs = set(
                getattr(
                    TranscriptionCreateParamsNonStreaming, "__annotations__", {}
                ).keys()
            )
            streaming_kwargs = set(
                getattr(
                    TranscriptionCreateParamsStreaming, "__annotations__", {}
                ).keys()
            )

            all_transcription_kwargs = non_streaming_kwargs.union(streaming_kwargs)
            return all_transcription_kwargs
        except Exception as e:
            verbose_logger.debug("Error getting transcription kwargs %s", str(e))
            return set()

    @staticmethod
    def _get_exclude_kwargs() -> Set[str]:
        """
        Get the kwargs to exclude from the cache key
        """
        return set(["metadata"])

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\panlex_lite.py ===
# Natural Language Toolkit: PanLex Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: David Kamholz <kamholz@panlex.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader for PanLex Lite, a stripped down version of PanLex distributed
as an SQLite database. See the README.txt in the panlex_lite corpus directory
for more information on PanLex Lite.
"""

import os
import sqlite3

from nltk.corpus.reader.api import CorpusReader


class PanLexLiteCorpusReader(CorpusReader):
    MEANING_Q = """
        SELECT dnx2.mn, dnx2.uq, dnx2.ap, dnx2.ui, ex2.tt, ex2.lv
        FROM dnx
        JOIN ex ON (ex.ex = dnx.ex)
        JOIN dnx dnx2 ON (dnx2.mn = dnx.mn)
        JOIN ex ex2 ON (ex2.ex = dnx2.ex)
        WHERE dnx.ex != dnx2.ex AND ex.tt = ? AND ex.lv = ?
        ORDER BY dnx2.uq DESC
    """

    TRANSLATION_Q = """
        SELECT s.tt, sum(s.uq) AS trq FROM (
            SELECT ex2.tt, max(dnx.uq) AS uq
            FROM dnx
            JOIN ex ON (ex.ex = dnx.ex)
            JOIN dnx dnx2 ON (dnx2.mn = dnx.mn)
            JOIN ex ex2 ON (ex2.ex = dnx2.ex)
            WHERE dnx.ex != dnx2.ex AND ex.lv = ? AND ex.tt = ? AND ex2.lv = ?
            GROUP BY ex2.tt, dnx.ui
        ) s
        GROUP BY s.tt
        ORDER BY trq DESC, s.tt
    """

    def __init__(self, root):
        self._c = sqlite3.connect(os.path.join(root, "db.sqlite")).cursor()

        self._uid_lv = {}
        self._lv_uid = {}

        for row in self._c.execute("SELECT uid, lv FROM lv"):
            self._uid_lv[row[0]] = row[1]
            self._lv_uid[row[1]] = row[0]

    def language_varieties(self, lc=None):
        """
        Return a list of PanLex language varieties.

        :param lc: ISO 639 alpha-3 code. If specified, filters returned varieties
            by this code. If unspecified, all varieties are returned.
        :return: the specified language varieties as a list of tuples. The first
            element is the language variety's seven-character uniform identifier,
            and the second element is its default name.
        :rtype: list(tuple)
        """

        if lc is None:
            return self._c.execute("SELECT uid, tt FROM lv ORDER BY uid").fetchall()
        else:
            return self._c.execute(
                "SELECT uid, tt FROM lv WHERE lc = ? ORDER BY uid", (lc,)
            ).fetchall()

    def meanings(self, expr_uid, expr_tt):
        """
        Return a list of meanings for an expression.

        :param expr_uid: the expression's language variety, as a seven-character
            uniform identifier.
        :param expr_tt: the expression's text.
        :return: a list of Meaning objects.
        :rtype: list(Meaning)
        """

        expr_lv = self._uid_lv[expr_uid]

        mn_info = {}

        for i in self._c.execute(self.MEANING_Q, (expr_tt, expr_lv)):
            mn = i[0]
            uid = self._lv_uid[i[5]]

            if not mn in mn_info:
                mn_info[mn] = {
                    "uq": i[1],
                    "ap": i[2],
                    "ui": i[3],
                    "ex": {expr_uid: [expr_tt]},
                }

            if not uid in mn_info[mn]["ex"]:
                mn_info[mn]["ex"][uid] = []

            mn_info[mn]["ex"][uid].append(i[4])

        return [Meaning(mn, mn_info[mn]) for mn in mn_info]

    def translations(self, from_uid, from_tt, to_uid):
        """
        Return a list of translations for an expression into a single language
        variety.

        :param from_uid: the source expression's language variety, as a
            seven-character uniform identifier.
        :param from_tt: the source expression's text.
        :param to_uid: the target language variety, as a seven-character
            uniform identifier.
        :return: a list of translation tuples. The first element is the expression
            text and the second element is the translation quality.
        :rtype: list(tuple)
        """

        from_lv = self._uid_lv[from_uid]
        to_lv = self._uid_lv[to_uid]

        return self._c.execute(self.TRANSLATION_Q, (from_lv, from_tt, to_lv)).fetchall()


class Meaning(dict):
    """
    Represents a single PanLex meaning. A meaning is a translation set derived
    from a single source.
    """

    def __init__(self, mn, attr):
        super().__init__(**attr)
        self["mn"] = mn

    def id(self):
        """
        :return: the meaning's id.
        :rtype: int
        """
        return self["mn"]

    def quality(self):
        """
        :return: the meaning's source's quality (0=worst, 9=best).
        :rtype: int
        """
        return self["uq"]

    def source(self):
        """
        :return: the meaning's source id.
        :rtype: int
        """
        return self["ap"]

    def source_group(self):
        """
        :return: the meaning's source group id.
        :rtype: int
        """
        return self["ui"]

    def expressions(self):
        """
        :return: the meaning's expressions as a dictionary whose keys are language
            variety uniform identifiers and whose values are lists of expression
            texts.
        :rtype: dict
        """
        return self["ex"]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\found_candidates.py ===
"""Utilities to lazily create and visit candidates found.

Creating and visiting a candidate is a *very* costly operation. It involves
fetching, extracting, potentially building modules from source, and verifying
distribution metadata. It is therefore crucial for performance to keep
everything here lazy all the way down, so we only touch candidates that we
absolutely need, and not "download the world" when we only need one version of
something.
"""

import functools
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Set, Tuple

from pip._vendor.packaging.version import _BaseVersion

from pip._internal.exceptions import MetadataInvalid

from .base import Candidate

logger = logging.getLogger(__name__)

IndexCandidateInfo = Tuple[_BaseVersion, Callable[[], Optional[Candidate]]]

if TYPE_CHECKING:
    SequenceCandidate = Sequence[Candidate]
else:
    # For compatibility: Python before 3.9 does not support using [] on the
    # Sequence class.
    #
    # >>> from collections.abc import Sequence
    # >>> Sequence[str]
    # Traceback (most recent call last):
    #   File "<stdin>", line 1, in <module>
    # TypeError: 'ABCMeta' object is not subscriptable
    #
    # TODO: Remove this block after dropping Python 3.8 support.
    SequenceCandidate = Sequence


def _iter_built(infos: Iterator[IndexCandidateInfo]) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the package is not already installed. Candidates
    from index come later in their normal ordering.
    """
    versions_found: Set[_BaseVersion] = set()
    for version, func in infos:
        if version in versions_found:
            continue
        try:
            candidate = func()
        except MetadataInvalid as e:
            logger.warning(
                "Ignoring version %s of %s since it has invalid metadata:\n"
                "%s\n"
                "Please use pip<24.1 if you need to use this version.",
                version,
                e.ireq.name,
                e,
            )
            # Mark version as found to avoid trying other candidates with the same
            # version, since they most likely have invalid metadata as well.
            versions_found.add(version)
        else:
            if candidate is None:
                continue
            yield candidate
            versions_found.add(version)


def _iter_built_with_prepended(
    installed: Candidate, infos: Iterator[IndexCandidateInfo]
) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers the already-installed
    candidate and NOT to upgrade. The installed candidate is therefore
    always yielded first, and candidates from index come later in their
    normal ordering, except skipped when the version is already installed.
    """
    yield installed
    versions_found: Set[_BaseVersion] = {installed.version}
    for version, func in infos:
        if version in versions_found:
            continue
        candidate = func()
        if candidate is None:
            continue
        yield candidate
        versions_found.add(version)


def _iter_built_with_inserted(
    installed: Candidate, infos: Iterator[IndexCandidateInfo]
) -> Iterator[Candidate]:
    """Iterator for ``FoundCandidates``.

    This iterator is used when the resolver prefers to upgrade an
    already-installed package. Candidates from index are returned in their
    normal ordering, except replaced when the version is already installed.

    The implementation iterates through and yields other candidates, inserting
    the installed candidate exactly once before we start yielding older or
    equivalent candidates, or after all other candidates if they are all newer.
    """
    versions_found: Set[_BaseVersion] = set()
    for version, func in infos:
        if version in versions_found:
            continue
        # If the installed candidate is better, yield it first.
        if installed.version >= version:
            yield installed
            versions_found.add(installed.version)
        candidate = func()
        if candidate is None:
            continue
        yield candidate
        versions_found.add(version)

    # If the installed candidate is older than all other candidates.
    if installed.version not in versions_found:
        yield installed


class FoundCandidates(SequenceCandidate):
    """A lazy sequence to provide candidates to the resolver.

    The intended usage is to return this from `find_matches()` so the resolver
    can iterate through the sequence multiple times, but only access the index
    page when remote packages are actually needed. This improve performances
    when suitable candidates are already installed on disk.
    """

    def __init__(
        self,
        get_infos: Callable[[], Iterator[IndexCandidateInfo]],
        installed: Optional[Candidate],
        prefers_installed: bool,
        incompatible_ids: Set[int],
    ):
        self._get_infos = get_infos
        self._installed = installed
        self._prefers_installed = prefers_installed
        self._incompatible_ids = incompatible_ids

    def __getitem__(self, index: Any) -> Any:
        # Implemented to satisfy the ABC check. This is not needed by the
        # resolver, and should not be used by the provider either (for
        # performance reasons).
        raise NotImplementedError("don't do this")

    def __iter__(self) -> Iterator[Candidate]:
        infos = self._get_infos()
        if not self._installed:
            iterator = _iter_built(infos)
        elif self._prefers_installed:
            iterator = _iter_built_with_prepended(self._installed, infos)
        else:
            iterator = _iter_built_with_inserted(self._installed, infos)
        return (c for c in iterator if id(c) not in self._incompatible_ids)

    def __len__(self) -> int:
        # Implemented to satisfy the ABC check. This is not needed by the
        # resolver, and should not be used by the provider either (for
        # performance reasons).
        raise NotImplementedError("don't do this")

    @functools.lru_cache(maxsize=1)
    def __bool__(self) -> bool:
        if self._prefers_installed and self._installed:
            return True
        return any(self)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\cells.py ===
from __future__ import annotations

from functools import lru_cache
from typing import Callable

from ._cell_widths import CELL_WIDTHS

# Ranges of unicode ordinals that produce a 1-cell wide character
# This is non-exhaustive, but covers most common Western characters
_SINGLE_CELL_UNICODE_RANGES: list[tuple[int, int]] = [
    (0x20, 0x7E),  # Latin (excluding non-printable)
    (0xA0, 0xAC),
    (0xAE, 0x002FF),
    (0x00370, 0x00482),  # Greek / Cyrillic
    (0x02500, 0x025FC),  # Box drawing, box elements, geometric shapes
    (0x02800, 0x028FF),  # Braille
]

# A set of characters that are a single cell wide
_SINGLE_CELLS = frozenset(
    [
        character
        for _start, _end in _SINGLE_CELL_UNICODE_RANGES
        for character in map(chr, range(_start, _end + 1))
    ]
)

# When called with a string this will return True if all
# characters are single-cell, otherwise False
_is_single_cell_widths: Callable[[str], bool] = _SINGLE_CELLS.issuperset


@lru_cache(4096)
def cached_cell_len(text: str) -> int:
    """Get the number of cells required to display text.

    This method always caches, which may use up a lot of memory. It is recommended to use
    `cell_len` over this method.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


def cell_len(text: str, _cell_len: Callable[[str], int] = cached_cell_len) -> int:
    """Get the number of cells required to display text.

    Args:
        text (str): Text to display.

    Returns:
        int: Get the number of cells required to display text.
    """
    if len(text) < 512:
        return _cell_len(text)
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, text))


@lru_cache(maxsize=4096)
def get_character_cell_size(character: str) -> int:
    """Get the cell size of a character.

    Args:
        character (str): A single character.

    Returns:
        int: Number of cells (0, 1 or 2) occupied by that character.
    """
    codepoint = ord(character)
    _table = CELL_WIDTHS
    lower_bound = 0
    upper_bound = len(_table) - 1
    index = (lower_bound + upper_bound) // 2
    while True:
        start, end, width = _table[index]
        if codepoint < start:
            upper_bound = index - 1
        elif codepoint > end:
            lower_bound = index + 1
        else:
            return 0 if width == -1 else width
        if upper_bound < lower_bound:
            break
        index = (lower_bound + upper_bound) // 2
    return 1


def set_cell_size(text: str, total: int) -> str:
    """Set the length of a string to fit within given number of cells."""

    if _is_single_cell_widths(text):
        size = len(text)
        if size < total:
            return text + " " * (total - size)
        return text[:total]

    if total <= 0:
        return ""
    cell_size = cell_len(text)
    if cell_size == total:
        return text
    if cell_size < total:
        return text + " " * (total - cell_size)

    start = 0
    end = len(text)

    # Binary search until we find the right size
    while True:
        pos = (start + end) // 2
        before = text[: pos + 1]
        before_len = cell_len(before)
        if before_len == total + 1 and cell_len(before[-1]) == 2:
            return before[:-1] + " "
        if before_len == total:
            return before
        if before_len > total:
            end = pos
        else:
            start = pos


def chop_cells(
    text: str,
    width: int,
) -> list[str]:
    """Split text into lines such that each line fits within the available (cell) width.

    Args:
        text: The text to fold such that it fits in the given width.
        width: The width available (number of cells).

    Returns:
        A list of strings such that each string in the list has cell width
        less than or equal to the available width.
    """
    _get_character_cell_size = get_character_cell_size
    lines: list[list[str]] = [[]]

    append_new_line = lines.append
    append_to_last_line = lines[-1].append

    total_width = 0

    for character in text:
        cell_width = _get_character_cell_size(character)
        char_doesnt_fit = total_width + cell_width > width

        if char_doesnt_fit:
            append_new_line([character])
            append_to_last_line = lines[-1].append
            total_width = cell_width
        else:
            append_to_last_line(character)
            total_width += cell_width

    return ["".join(line) for line in lines]


if __name__ == "__main__":  # pragma: no cover
    print(get_character_cell_size("😽"))
    for line in chop_cells("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", 8):
        print(line)
    for n in range(80, 1, -1):
        print(set_cell_size("""这是对亚洲语言支持的测试。面对模棱两可的想法，拒绝猜测的诱惑。""", n) + "|")
        print("x" * n)

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_decorators_v1.py ===
"""Logic for V1 validators, e.g. `@validator` and `@root_validator`."""

from __future__ import annotations as _annotations

from inspect import Parameter, signature
from typing import Any, Union, cast

from pydantic_core import core_schema
from typing_extensions import Protocol

from ..errors import PydanticUserError
from ._utils import can_be_positional


class V1OnlyValueValidator(Protocol):
    """A simple validator, supported for V1 validators and V2 validators."""

    def __call__(self, __value: Any) -> Any: ...


class V1ValidatorWithValues(Protocol):
    """A validator with `values` argument, supported for V1 validators and V2 validators."""

    def __call__(self, __value: Any, values: dict[str, Any]) -> Any: ...


class V1ValidatorWithValuesKwOnly(Protocol):
    """A validator with keyword only `values` argument, supported for V1 validators and V2 validators."""

    def __call__(self, __value: Any, *, values: dict[str, Any]) -> Any: ...


class V1ValidatorWithKwargs(Protocol):
    """A validator with `kwargs` argument, supported for V1 validators and V2 validators."""

    def __call__(self, __value: Any, **kwargs: Any) -> Any: ...


class V1ValidatorWithValuesAndKwargs(Protocol):
    """A validator with `values` and `kwargs` arguments, supported for V1 validators and V2 validators."""

    def __call__(self, __value: Any, values: dict[str, Any], **kwargs: Any) -> Any: ...


V1Validator = Union[
    V1ValidatorWithValues, V1ValidatorWithValuesKwOnly, V1ValidatorWithKwargs, V1ValidatorWithValuesAndKwargs
]


def can_be_keyword(param: Parameter) -> bool:
    return param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)


def make_generic_v1_field_validator(validator: V1Validator) -> core_schema.WithInfoValidatorFunction:
    """Wrap a V1 style field validator for V2 compatibility.

    Args:
        validator: The V1 style field validator.

    Returns:
        A wrapped V2 style field validator.

    Raises:
        PydanticUserError: If the signature is not supported or the parameters are
            not available in Pydantic V2.
    """
    sig = signature(validator)

    needs_values_kw = False

    for param_num, (param_name, parameter) in enumerate(sig.parameters.items()):
        if can_be_keyword(parameter) and param_name in ('field', 'config'):
            raise PydanticUserError(
                'The `field` and `config` parameters are not available in Pydantic V2, '
                'please use the `info` parameter instead.',
                code='validator-field-config-info',
            )
        if parameter.kind is Parameter.VAR_KEYWORD:
            needs_values_kw = True
        elif can_be_keyword(parameter) and param_name == 'values':
            needs_values_kw = True
        elif can_be_positional(parameter) and param_num == 0:
            # value
            continue
        elif parameter.default is Parameter.empty:  # ignore params with defaults e.g. bound by functools.partial
            raise PydanticUserError(
                f'Unsupported signature for V1 style validator {validator}: {sig} is not supported.',
                code='validator-v1-signature',
            )

    if needs_values_kw:
        # (v, **kwargs), (v, values, **kwargs), (v, *, values, **kwargs) or (v, *, values)
        val1 = cast(V1ValidatorWithValues, validator)

        def wrapper1(value: Any, info: core_schema.ValidationInfo) -> Any:
            return val1(value, values=info.data)

        return wrapper1
    else:
        val2 = cast(V1OnlyValueValidator, validator)

        def wrapper2(value: Any, _: core_schema.ValidationInfo) -> Any:
            return val2(value)

        return wrapper2


RootValidatorValues = dict[str, Any]
# technically tuple[model_dict, model_extra, fields_set] | tuple[dataclass_dict, init_vars]
RootValidatorFieldsTuple = tuple[Any, ...]


class V1RootValidatorFunction(Protocol):
    """A simple root validator, supported for V1 validators and V2 validators."""

    def __call__(self, __values: RootValidatorValues) -> RootValidatorValues: ...


class V2CoreBeforeRootValidator(Protocol):
    """V2 validator with mode='before'."""

    def __call__(self, __values: RootValidatorValues, __info: core_schema.ValidationInfo) -> RootValidatorValues: ...


class V2CoreAfterRootValidator(Protocol):
    """V2 validator with mode='after'."""

    def __call__(
        self, __fields_tuple: RootValidatorFieldsTuple, __info: core_schema.ValidationInfo
    ) -> RootValidatorFieldsTuple: ...


def make_v1_generic_root_validator(
    validator: V1RootValidatorFunction, pre: bool
) -> V2CoreBeforeRootValidator | V2CoreAfterRootValidator:
    """Wrap a V1 style root validator for V2 compatibility.

    Args:
        validator: The V1 style field validator.
        pre: Whether the validator is a pre validator.

    Returns:
        A wrapped V2 style validator.
    """
    if pre is True:
        # mode='before' for pydantic-core
        def _wrapper1(values: RootValidatorValues, _: core_schema.ValidationInfo) -> RootValidatorValues:
            return validator(values)

        return _wrapper1

    # mode='after' for pydantic-core
    def _wrapper2(fields_tuple: RootValidatorFieldsTuple, _: core_schema.ValidationInfo) -> RootValidatorFieldsTuple:
        if len(fields_tuple) == 2:
            # dataclass, this is easy
            values, init_vars = fields_tuple
            values = validator(values)
            return values, init_vars
        else:
            # ugly hack: to match v1 behaviour, we merge values and model_extra, then split them up based on fields
            # afterwards
            model_dict, model_extra, fields_set = fields_tuple
            if model_extra:
                fields = set(model_dict.keys())
                model_dict.update(model_extra)
                model_dict_new = validator(model_dict)
                for k in list(model_dict_new.keys()):
                    if k not in fields:
                        model_extra[k] = model_dict_new.pop(k)
            else:
                model_dict_new = validator(model_dict)
            return model_dict_new, model_extra, fields_set

    return _wrapper2

# === NexusCore/openenv\Lib\site-packages\win32\Demos\win32comport_demo.py ===
# This is a simple serial port terminal demo.
#
# Its primary purpose is to demonstrate the native serial port access offered via
# win32file.

# It uses 3 threads:
# - The main thread, which cranks up the other 2 threads, then simply waits for them to exit.
# - The user-input thread - blocks waiting for a keyboard character, and when found sends it
#   out the COM port.  If the character is Ctrl+C, it stops, signalling the COM port thread to stop.
# - The COM port thread is simply listening for input on the COM port, and prints it to the screen.

# This demo uses userlapped IO, so that none of the read or write operations actually block (however,
# in this sample, the very next thing we do _is_ block - so it shows off the concepts even though it
# doesn't exploit them.

import msvcrt  # For the getch() function.
import sys
import threading

import win32con  # constants.
from win32event import (  # We use events and the WaitFor[Multiple]Objects functions.
    INFINITE,
    WAIT_OBJECT_0,
    CreateEvent,
    SetEvent,
    WaitForMultipleObjects,
    WaitForSingleObject,
)
from win32file import (  # The base COM port and file IO functions.
    CBR_115200,
    EV_RXCHAR,
    NOPARITY,
    ONESTOPBIT,
    OVERLAPPED,
    PURGE_RXABORT,
    PURGE_RXCLEAR,
    PURGE_TXABORT,
    PURGE_TXCLEAR,
    ClearCommError,
    CreateFile,
    GetCommModemStatus,
    GetCommState,
    PurgeComm,
    ReadFile,
    SetCommMask,
    SetCommState,
    SetCommTimeouts,
    SetupComm,
    WaitCommEvent,
    WriteFile,
    error,
)


def FindModem():
    # Snoop over the comports, seeing if it is likely we have a modem.
    for i in range(1, 5):
        port = "COM%d" % (i,)
        try:
            handle = CreateFile(
                port,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                0,  # exclusive access
                None,  # no security
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None,
            )
            # It appears that an available COM port will always success here,
            # just return 0 for the status flags.  We only care that it has _any_ status
            # flags (and therefore probably a real modem)
            if GetCommModemStatus(handle) != 0:
                return port
        except error:
            pass  # No port, or modem status failed.
    return None


# A basic synchronous COM port file-like object
class SerialTTY:
    def __init__(self, port):
        if isinstance(port, int):
            port = "COM%d" % (port,)
        self.handle = CreateFile(
            port,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            0,  # exclusive access
            None,  # no security
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL | win32con.FILE_FLAG_OVERLAPPED,
            None,
        )
        # Tell the port we want a notification on each char.
        SetCommMask(self.handle, EV_RXCHAR)
        # Setup a 4k buffer
        SetupComm(self.handle, 4096, 4096)
        # Remove anything that was there
        PurgeComm(
            self.handle, PURGE_TXABORT | PURGE_RXABORT | PURGE_TXCLEAR | PURGE_RXCLEAR
        )
        # Setup for overlapped IO.
        timeouts = 0xFFFFFFFF, 0, 1000, 0, 1000
        SetCommTimeouts(self.handle, timeouts)
        # Setup the connection info.
        dcb = GetCommState(self.handle)
        dcb.BaudRate = CBR_115200
        dcb.ByteSize = 8
        dcb.Parity = NOPARITY
        dcb.StopBits = ONESTOPBIT
        SetCommState(self.handle, dcb)
        print(f"Connected to {port} at {dcb.BaudRate} baud")

    def _UserInputReaderThread(self):
        overlapped = OVERLAPPED()
        overlapped.hEvent = CreateEvent(None, 1, 0, None)
        try:
            while 1:
                ch = msvcrt.getch()
                if ord(ch) == 3:
                    break
                WriteFile(self.handle, ch, overlapped)
                # Wait for the write to complete.
                WaitForSingleObject(overlapped.hEvent, INFINITE)
        finally:
            SetEvent(self.eventStop)

    def _ComPortThread(self):
        overlapped = OVERLAPPED()
        overlapped.hEvent = CreateEvent(None, 1, 0, None)
        while 1:
            # XXX - note we could _probably_ just use overlapped IO on the win32file.ReadFile() statement
            # XXX but this tests the COM stuff!
            rc, mask = WaitCommEvent(self.handle, overlapped)
            if rc == 0:  # Character already ready!
                SetEvent(overlapped.hEvent)
            rc = WaitForMultipleObjects(
                [overlapped.hEvent, self.eventStop], 0, INFINITE
            )
            if rc == WAIT_OBJECT_0:
                # Some input - read and print it
                flags, comstat = ClearCommError(self.handle)
                rc, data = ReadFile(self.handle, comstat.cbInQue, overlapped)
                WaitForSingleObject(overlapped.hEvent, INFINITE)
                sys.stdout.write(data)
            else:
                # Stop the thread!
                # Just incase the user input thread uis still going, close it
                sys.stdout.close()
                break

    def Run(self):
        self.eventStop = CreateEvent(None, 0, 0, None)
        # Start the reader and writer threads.
        user_thread = threading.Thread(target=self._UserInputReaderThread)
        user_thread.start()
        com_thread = threading.Thread(target=self._ComPortThread)
        com_thread.start()
        user_thread.join()
        com_thread.join()


if __name__ == "__main__":
    print("Serial port terminal demo - press Ctrl+C to exit")
    if len(sys.argv) <= 1:
        port = FindModem()
        if port is None:
            print("No COM port specified, and no modem could be found")
            print("Please re-run this script with the name of a COM port (eg COM3)")
            sys.exit(1)
    else:
        port = sys.argv[1]

    tty = SerialTTY(port)
    tty.Run()

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32wnet.py ===
import unittest

import netbios
import win32api
import win32wnet

RESOURCE_CONNECTED = 0x00000001
RESOURCE_GLOBALNET = 0x00000002
RESOURCE_REMEMBERED = 0x00000003
RESOURCE_RECENT = 0x00000004
RESOURCE_CONTEXT = 0x00000005
RESOURCETYPE_ANY = 0x00000000
RESOURCETYPE_DISK = 0x00000001
RESOURCETYPE_PRINT = 0x00000002
RESOURCETYPE_RESERVED = 0x00000008
RESOURCETYPE_UNKNOWN = 0xFFFFFFFF
RESOURCEUSAGE_CONNECTABLE = 0x00000001
RESOURCEUSAGE_CONTAINER = 0x00000002
RESOURCEDISPLAYTYPE_GENERIC = 0x00000000
RESOURCEDISPLAYTYPE_DOMAIN = 0x00000001
RESOURCEDISPLAYTYPE_SERVER = 0x00000002
RESOURCEDISPLAYTYPE_SHARE = 0x00000003


NETRESOURCE_attributes = [
    ("dwScope", int),
    ("dwType", int),
    ("dwDisplayType", int),
    ("dwUsage", int),
    ("lpLocalName", str),
    ("lpRemoteName", str),
    ("lpComment", str),
    ("lpProvider", str),
]

NCB_attributes = [
    ("Command", int),
    ("Retcode", int),
    ("Lsn", int),
    ("Num", int),
    #    ("Bufflen", int), - read-only
    ("Callname", str),
    ("Name", str),
    ("Rto", int),
    ("Sto", int),
    ("Lana_num", int),
    ("Cmd_cplt", int),
    ("Event", int),
    ("Post", int),
]


class TestCase(unittest.TestCase):
    def testGetUser(self):
        self.assertEqual(win32api.GetUserName(), win32wnet.WNetGetUser())

    def _checkItemAttributes(self, item, attrs):
        for attr, typ in attrs:
            val = getattr(item, attr)
            if typ is int:
                self.assertTrue(
                    isinstance(val, int), f"Attr {attr!r} has value {val!r}"
                )
                new_val = val + 1
            elif typ is str:
                if val is not None:
                    # must be string
                    self.assertTrue(
                        isinstance(val, str), f"Attr {attr!r} has value {val!r}"
                    )
                    new_val = val + " new value"
                else:
                    new_val = "new value"
            else:
                self.fail(f"Don't know what {typ} is")
            # set the attribute just to make sure we can.
            setattr(item, attr, new_val)

    def testNETRESOURCE(self):
        nr = win32wnet.NETRESOURCE()
        self._checkItemAttributes(nr, NETRESOURCE_attributes)

    def testWNetEnumResource(self):
        handle = win32wnet.WNetOpenEnum(RESOURCE_GLOBALNET, RESOURCETYPE_ANY, 0, None)
        try:
            while 1:
                items = win32wnet.WNetEnumResource(handle, 0)
                if len(items) == 0:
                    break
                for item in items:
                    self._checkItemAttributes(item, NETRESOURCE_attributes)
        finally:
            handle.Close()

    def testNCB(self):
        ncb = win32wnet.NCB()
        self._checkItemAttributes(ncb, NCB_attributes)

    def testNetbios(self):
        # taken from the demo code in netbios.py
        ncb = win32wnet.NCB()
        ncb.Command = netbios.NCBENUM
        la_enum = netbios.LANA_ENUM()
        ncb.Buffer = la_enum
        rc = win32wnet.Netbios(ncb)
        self.assertEqual(rc, 0)
        for i in range(la_enum.length):
            ncb.Reset()
            ncb.Command = netbios.NCBRESET
            ncb.Lana_num = la_enum.lana[i]
            rc = win32wnet.Netbios(ncb)
            self.assertEqual(rc, 0)
            ncb.Reset()
            ncb.Command = netbios.NCBASTAT
            ncb.Lana_num = la_enum.lana[i]
            ncb.Callname = b"*               "
            adapter = netbios.ADAPTER_STATUS()
            ncb.Buffer = adapter
            win32wnet.Netbios(ncb)
            # expect 6 bytes in the mac address.
            self.assertTrue(len(adapter.adapter_address), 6)

    def iterConnectableShares(self):
        nr = win32wnet.NETRESOURCE()
        nr.dwScope = RESOURCE_GLOBALNET
        nr.dwUsage = RESOURCEUSAGE_CONTAINER
        nr.lpRemoteName = "\\\\" + win32api.GetComputerName()

        handle = win32wnet.WNetOpenEnum(RESOURCE_GLOBALNET, RESOURCETYPE_ANY, 0, nr)
        while 1:
            items = win32wnet.WNetEnumResource(handle, 0)
            if len(items) == 0:
                break
            for item in items:
                if item.dwDisplayType == RESOURCEDISPLAYTYPE_SHARE:
                    yield item

    def findUnusedDriveLetter(self):
        existing = [
            x[0].lower() for x in win32api.GetLogicalDriveStrings().split("\0") if x
        ]
        handle = win32wnet.WNetOpenEnum(RESOURCE_REMEMBERED, RESOURCETYPE_DISK, 0, None)
        try:
            while 1:
                items = win32wnet.WNetEnumResource(handle, 0)
                if len(items) == 0:
                    break
                xtra = [i.lpLocalName[0].lower() for i in items if i.lpLocalName]
                existing.extend(xtra)
        finally:
            handle.Close()
        for maybe in "defghijklmnopqrstuvwxyz":
            if maybe not in existing:
                return maybe
        self.fail("All drive mappings are taken?")

    def testAddConnection(self):
        localName = self.findUnusedDriveLetter() + ":"
        for share in self.iterConnectableShares():
            share.lpLocalName = localName
            win32wnet.WNetAddConnection2(share)
            win32wnet.WNetCancelConnection2(localName, 0, 0)
            break

    def testAddConnectionOld(self):
        localName = self.findUnusedDriveLetter() + ":"
        for share in self.iterConnectableShares():
            win32wnet.WNetAddConnection2(share.dwType, localName, share.lpRemoteName)
            win32wnet.WNetCancelConnection2(localName, 0, 0)
            break


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\PIL\ContainerIO.py ===
#
# The Python Imaging Library.
# $Id$
#
# a class to read from a container file
#
# History:
# 1995-06-18 fl     Created
# 1995-09-07 fl     Added readline(), readlines()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1995 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
from collections.abc import Iterable
from typing import IO, AnyStr, NoReturn


class ContainerIO(IO[AnyStr]):
    """
    A file object that provides read access to a part of an existing
    file (for example a TAR file).
    """

    def __init__(self, file: IO[AnyStr], offset: int, length: int) -> None:
        """
        Create file object.

        :param file: Existing file.
        :param offset: Start of region, in bytes.
        :param length: Size of region, in bytes.
        """
        self.fh: IO[AnyStr] = file
        self.pos = 0
        self.offset = offset
        self.length = length
        self.fh.seek(offset)

    ##
    # Always false.

    def isatty(self) -> bool:
        return False

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, mode: int = io.SEEK_SET) -> int:
        """
        Move file pointer.

        :param offset: Offset in bytes.
        :param mode: Starting position. Use 0 for beginning of region, 1
           for current offset, and 2 for end of region.  You cannot move
           the pointer outside the defined region.
        :returns: Offset from start of region, in bytes.
        """
        if mode == 1:
            self.pos = self.pos + offset
        elif mode == 2:
            self.pos = self.length + offset
        else:
            self.pos = offset
        # clamp
        self.pos = max(0, min(self.pos, self.length))
        self.fh.seek(self.offset + self.pos)
        return self.pos

    def tell(self) -> int:
        """
        Get current file pointer.

        :returns: Offset from start of region, in bytes.
        """
        return self.pos

    def readable(self) -> bool:
        return True

    def read(self, n: int = -1) -> AnyStr:
        """
        Read data.

        :param n: Number of bytes to read. If omitted, zero or negative,
            read until end of region.
        :returns: An 8-bit string.
        """
        if n > 0:
            n = min(n, self.length - self.pos)
        else:
            n = self.length - self.pos
        if n <= 0:  # EOF
            return b"" if "b" in self.fh.mode else ""  # type: ignore[return-value]
        self.pos = self.pos + n
        return self.fh.read(n)

    def readline(self, n: int = -1) -> AnyStr:
        """
        Read a line of text.

        :param n: Number of bytes to read. If omitted, zero or negative,
            read until end of line.
        :returns: An 8-bit string.
        """
        s: AnyStr = b"" if "b" in self.fh.mode else ""  # type: ignore[assignment]
        newline_character = b"\n" if "b" in self.fh.mode else "\n"
        while True:
            c = self.read(1)
            if not c:
                break
            s = s + c
            if c == newline_character or len(s) == n:
                break
        return s

    def readlines(self, n: int | None = -1) -> list[AnyStr]:
        """
        Read multiple lines of text.

        :param n: Number of lines to read. If omitted, zero, negative or None,
            read until end of region.
        :returns: A list of 8-bit strings.
        """
        lines = []
        while True:
            s = self.readline()
            if not s:
                break
            lines.append(s)
            if len(lines) == n:
                break
        return lines

    def writable(self) -> bool:
        return False

    def write(self, b: AnyStr) -> NoReturn:
        raise NotImplementedError()

    def writelines(self, lines: Iterable[AnyStr]) -> NoReturn:
        raise NotImplementedError()

    def truncate(self, size: int | None = None) -> int:
        raise NotImplementedError()

    def __enter__(self) -> ContainerIO[AnyStr]:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __iter__(self) -> ContainerIO[AnyStr]:
        return self

    def __next__(self) -> AnyStr:
        line = self.readline()
        if not line:
            msg = "end of region"
            raise StopIteration(msg)
        return line

    def fileno(self) -> int:
        return self.fh.fileno()

    def flush(self) -> None:
        self.fh.flush()

    def close(self) -> None:
        self.fh.close()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\inputhookwx.py ===
# encoding: utf-8
"""
Enable wxPython to be used interacive by setting PyOS_InputHook.

Authors:  Robin Dunn, Brian Granger, Ondrej Certik
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import sys
import signal
from _pydev_bundle._pydev_saved_modules import time
from timeit import default_timer as clock
import wx

from pydev_ipython.inputhook import stdin_ready


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def inputhook_wx1():
    """Run the wx event loop by processing pending events only.

    This approach seems to work, but its performance is not great as it
    relies on having PyOS_InputHook called regularly.
    """
    try:
        app = wx.GetApp()  # @UndefinedVariable
        if app is not None:
            assert wx.Thread_IsMain()  # @UndefinedVariable

            # Make a temporary event loop and process system events until
            # there are no more waiting, then allow idle events (which
            # will also deal with pending or posted wx events.)
            evtloop = wx.EventLoop()  # @UndefinedVariable
            ea = wx.EventLoopActivator(evtloop)  # @UndefinedVariable
            while evtloop.Pending():
                evtloop.Dispatch()
            app.ProcessIdle()
            del ea
    except KeyboardInterrupt:
        pass
    return 0


class EventLoopTimer(wx.Timer):  # @UndefinedVariable
    def __init__(self, func):
        self.func = func
        wx.Timer.__init__(self)  # @UndefinedVariable

    def Notify(self):
        self.func()


class EventLoopRunner(object):
    def Run(self, time):
        self.evtloop = wx.EventLoop()  # @UndefinedVariable
        self.timer = EventLoopTimer(self.check_stdin)
        self.timer.Start(time)
        self.evtloop.Run()

    def check_stdin(self):
        if stdin_ready():
            self.timer.Stop()
            self.evtloop.Exit()


def inputhook_wx2():
    """Run the wx event loop, polling for stdin.

    This version runs the wx eventloop for an undetermined amount of time,
    during which it periodically checks to see if anything is ready on
    stdin.  If anything is ready on stdin, the event loop exits.

    The argument to elr.Run controls how often the event loop looks at stdin.
    This determines the responsiveness at the keyboard.  A setting of 1000
    enables a user to type at most 1 char per second.  I have found that a
    setting of 10 gives good keyboard response.  We can shorten it further,
    but eventually performance would suffer from calling select/kbhit too
    often.
    """
    try:
        app = wx.GetApp()  # @UndefinedVariable
        if app is not None:
            assert wx.Thread_IsMain()  # @UndefinedVariable
            elr = EventLoopRunner()
            # As this time is made shorter, keyboard response improves, but idle
            # CPU load goes up.  10 ms seems like a good compromise.
            elr.Run(time=10)  # CHANGE time here to control polling interval
    except KeyboardInterrupt:
        pass
    return 0


def inputhook_wx3():
    """Run the wx event loop by processing pending events only.

    This is like inputhook_wx1, but it keeps processing pending events
    until stdin is ready.  After processing all pending events, a call to
    time.sleep is inserted.  This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    # We need to protect against a user pressing Control-C when IPython is
    # idle and this is running. We trap KeyboardInterrupt and pass.
    try:
        app = wx.GetApp()  # @UndefinedVariable
        if app is not None:
            if hasattr(wx, "IsMainThread"):
                assert wx.IsMainThread()  # @UndefinedVariable
            else:
                assert wx.Thread_IsMain()  # @UndefinedVariable

            # The import of wx on Linux sets the handler for signal.SIGINT
            # to 0.  This is a bug in wx or gtk.  We fix by just setting it
            # back to the Python default.
            if not callable(signal.getsignal(signal.SIGINT)):
                signal.signal(signal.SIGINT, signal.default_int_handler)

            evtloop = wx.EventLoop()  # @UndefinedVariable
            ea = wx.EventLoopActivator(evtloop)  # @UndefinedVariable
            t = clock()
            while not stdin_ready():
                while evtloop.Pending():
                    t = clock()
                    evtloop.Dispatch()
                app.ProcessIdle()
                # We need to sleep at this point to keep the idle CPU load
                # low.  However, if sleep to long, GUI response is poor.  As
                # a compromise, we watch how often GUI events are being processed
                # and switch between a short and long sleep time.  Here are some
                # stats useful in helping to tune this.
                # time    CPU load
                # 0.001   13%
                # 0.005   3%
                # 0.01    1.5%
                # 0.05    0.5%
                used_time = clock() - t
                if used_time > 10.0:
                    # print 'Sleep for 1 s'  # dbg
                    time.sleep(1.0)
                elif used_time > 0.1:
                    # Few GUI events coming in, so we can sleep longer
                    # print 'Sleep for 0.05 s'  # dbg
                    time.sleep(0.05)
                else:
                    # Many GUI events coming in, so sleep only very little
                    time.sleep(0.001)
            del ea
    except KeyboardInterrupt:
        pass
    return 0


if sys.platform == "darwin":
    # On OSX, evtloop.Pending() always returns True, regardless of there being
    # any events pending. As such we can't use implementations 1 or 3 of the
    # inputhook as those depend on a pending/dispatch loop.
    inputhook_wx = inputhook_wx2
else:
    # This is our default implementation
    inputhook_wx = inputhook_wx3

# === NexusCore/openenv\Lib\site-packages\fontTools\merge\cmap.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod, Roozbeh Pournader

from fontTools.merge.unicode import is_Default_Ignorable
from fontTools.pens.recordingPen import DecomposingRecordingPen
import logging


log = logging.getLogger("fontTools.merge")


def computeMegaGlyphOrder(merger, glyphOrders):
    """Modifies passed-in glyphOrders to reflect new glyph names.
    Stores merger.glyphOrder."""
    megaOrder = {}
    for glyphOrder in glyphOrders:
        for i, glyphName in enumerate(glyphOrder):
            if glyphName in megaOrder:
                n = megaOrder[glyphName]
                while (glyphName + "." + repr(n)) in megaOrder:
                    n += 1
                megaOrder[glyphName] = n
                glyphName += "." + repr(n)
                glyphOrder[i] = glyphName
            megaOrder[glyphName] = 1
    merger.glyphOrder = megaOrder = list(megaOrder.keys())


def _glyphsAreSame(
    glyphSet1,
    glyphSet2,
    glyph1,
    glyph2,
    advanceTolerance=0.05,
    advanceToleranceEmpty=0.20,
):
    pen1 = DecomposingRecordingPen(glyphSet1)
    pen2 = DecomposingRecordingPen(glyphSet2)
    g1 = glyphSet1[glyph1]
    g2 = glyphSet2[glyph2]
    g1.draw(pen1)
    g2.draw(pen2)
    if pen1.value != pen2.value:
        return False
    # Allow more width tolerance for glyphs with no ink
    tolerance = advanceTolerance if pen1.value else advanceToleranceEmpty
    # TODO Warn if advances not the same but within tolerance.
    if abs(g1.width - g2.width) > g1.width * tolerance:
        return False
    if hasattr(g1, "height") and g1.height is not None:
        if abs(g1.height - g2.height) > g1.height * tolerance:
            return False
    return True


def computeMegaUvs(merger, uvsTables):
    """Returns merged UVS subtable (cmap format=14)."""
    uvsDict = {}
    cmap = merger.cmap
    for table in uvsTables:
        for variationSelector, uvsMapping in table.uvsDict.items():
            if variationSelector not in uvsDict:
                uvsDict[variationSelector] = {}
            for unicodeValue, glyphName in uvsMapping:
                if cmap.get(unicodeValue) == glyphName:
                    # this is a default variation
                    glyphName = None
                    # prefer previous glyph id if both fonts defined UVS
                if unicodeValue not in uvsDict[variationSelector]:
                    uvsDict[variationSelector][unicodeValue] = glyphName

    for variationSelector in uvsDict:
        uvsDict[variationSelector] = [*uvsDict[variationSelector].items()]

    return uvsDict


# Valid (format, platformID, platEncID) triplets for cmap subtables containing
# Unicode BMP-only and Unicode Full Repertoire semantics.
# Cf. OpenType spec for "Platform specific encodings":
# https://docs.microsoft.com/en-us/typography/opentype/spec/name
class _CmapUnicodePlatEncodings:
    BMP = {(4, 3, 1), (4, 0, 3), (4, 0, 4), (4, 0, 6)}
    FullRepertoire = {(12, 3, 10), (12, 0, 4), (12, 0, 6)}
    UVS = {(14, 0, 5)}


def computeMegaCmap(merger, cmapTables):
    """Sets merger.cmap and merger.uvsDict."""

    # TODO Handle format=14.
    # Only merge format 4 and 12 Unicode subtables, ignores all other subtables
    # If there is a format 12 table for a font, ignore the format 4 table of it
    chosenCmapTables = []
    chosenUvsTables = []
    for fontIdx, table in enumerate(cmapTables):
        format4 = None
        format12 = None
        format14 = None
        for subtable in table.tables:
            properties = (subtable.format, subtable.platformID, subtable.platEncID)
            if properties in _CmapUnicodePlatEncodings.BMP:
                format4 = subtable
            elif properties in _CmapUnicodePlatEncodings.FullRepertoire:
                format12 = subtable
            elif properties in _CmapUnicodePlatEncodings.UVS:
                format14 = subtable
            else:
                log.warning(
                    "Dropped cmap subtable from font '%s':\t"
                    "format %2s, platformID %2s, platEncID %2s",
                    fontIdx,
                    subtable.format,
                    subtable.platformID,
                    subtable.platEncID,
                )
        if format12 is not None:
            chosenCmapTables.append((format12, fontIdx))
        elif format4 is not None:
            chosenCmapTables.append((format4, fontIdx))

        if format14 is not None:
            chosenUvsTables.append(format14)

    # Build the unicode mapping
    merger.cmap = cmap = {}
    fontIndexForGlyph = {}
    glyphSets = [None for f in merger.fonts] if hasattr(merger, "fonts") else None

    for table, fontIdx in chosenCmapTables:
        # handle duplicates
        for uni, gid in table.cmap.items():
            oldgid = cmap.get(uni, None)
            if oldgid is None:
                cmap[uni] = gid
                fontIndexForGlyph[gid] = fontIdx
            elif is_Default_Ignorable(uni) or uni in (0x25CC,):  # U+25CC DOTTED CIRCLE
                continue
            elif oldgid != gid:
                # Char previously mapped to oldgid, now to gid.
                # Record, to fix up in GSUB 'locl' later.
                if merger.duplicateGlyphsPerFont[fontIdx].get(oldgid) is None:
                    if glyphSets is not None:
                        oldFontIdx = fontIndexForGlyph[oldgid]
                        for idx in (fontIdx, oldFontIdx):
                            if glyphSets[idx] is None:
                                glyphSets[idx] = merger.fonts[idx].getGlyphSet()
                        # if _glyphsAreSame(glyphSets[oldFontIdx], glyphSets[fontIdx], oldgid, gid):
                        # 	continue
                    merger.duplicateGlyphsPerFont[fontIdx][oldgid] = gid
                elif merger.duplicateGlyphsPerFont[fontIdx][oldgid] != gid:
                    # Char previously mapped to oldgid but oldgid is already remapped to a different
                    # gid, because of another Unicode character.
                    # TODO: Try harder to do something about these.
                    log.warning(
                        "Dropped mapping from codepoint %#06X to glyphId '%s'", uni, gid
                    )

    merger.uvsDict = computeMegaUvs(merger, chosenUvsTables)


def renameCFFCharStrings(merger, glyphOrder, cffTable):
    """Rename topDictIndex charStrings based on glyphOrder."""
    td = cffTable.cff.topDictIndex[0]

    charStrings = {}
    for i, v in enumerate(td.CharStrings.charStrings.values()):
        glyphName = glyphOrder[i]
        charStrings[glyphName] = v
    td.CharStrings.charStrings = charStrings

    td.charset = list(glyphOrder)

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\pylab.py ===
"""Implementation of magic functions for matplotlib/pylab support.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Our own packages
from traitlets.config.application import Application
from IPython.core import magic_arguments
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from warnings import warn

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

magic_gui_arg = magic_arguments.argument(
    "gui",
    nargs="?",
    help="""Name of the matplotlib backend to use such as 'qt' or 'widget'.
        If given, the corresponding matplotlib backend is used,
        otherwise it will be matplotlib's default
        (which you can set in your matplotlib config file).
        """,
)


@magics_class
class PylabMagics(Magics):
    """Magics related to matplotlib's pylab support"""

    @skip_doctest
    @line_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument('-l', '--list', action='store_true',
                              help='Show available matplotlib backends')
    @magic_gui_arg
    def matplotlib(self, line=''):
        """Set up matplotlib to work interactively.

        This function lets you activate matplotlib interactive support
        at any point during an IPython session. It does not import anything
        into the interactive namespace.

        If you are using the inline matplotlib backend in the IPython Notebook
        you can set which figure formats are enabled using the following::

            In [1]: from matplotlib_inline.backend_inline import set_matplotlib_formats

            In [2]: set_matplotlib_formats('pdf', 'svg')

        The default for inline figures sets `bbox_inches` to 'tight'. This can
        cause discrepancies between the displayed image and the identical
        image created using `savefig`. This behavior can be disabled using the
        `%config` magic::

            In [3]: %config InlineBackend.print_figure_kwargs = {'bbox_inches':None}

        In addition, see the docstrings of
        `matplotlib_inline.backend_inline.set_matplotlib_formats` and
        `matplotlib_inline.backend_inline.set_matplotlib_close` for more information on
        changing additional behaviors of the inline backend.

        Examples
        --------
        To enable the inline backend for usage with the IPython Notebook::

            In [1]: %matplotlib inline

        In this case, where the matplotlib default is TkAgg::

            In [2]: %matplotlib
            Using matplotlib backend: TkAgg

        But you can explicitly request a different GUI backend::

            In [3]: %matplotlib qt

        You can list the available backends using the -l/--list option::

           In [4]: %matplotlib --list
           Available matplotlib backends: ['osx', 'qt4', 'qt5', 'gtk3', 'gtk4', 'notebook', 'wx', 'qt', 'nbagg',
           'gtk', 'tk', 'inline']
        """
        args = magic_arguments.parse_argstring(self.matplotlib, line)
        if args.list:
            from IPython.core.pylabtools import _list_matplotlib_backends_and_gui_loops

            print(
                "Available matplotlib backends: %s"
                % _list_matplotlib_backends_and_gui_loops()
            )
        else:
            gui, backend = self.shell.enable_matplotlib(args.gui)
            self._show_matplotlib_backend(args.gui, backend)

    @skip_doctest
    @line_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '--no-import-all', action='store_true', default=None,
        help="""Prevent IPython from performing ``import *`` into the interactive namespace.

        You can govern the default behavior of this flag with the
        InteractiveShellApp.pylab_import_all configurable.
        """
    )
    @magic_gui_arg
    def pylab(self, line=''):
        """Load numpy and matplotlib to work interactively.

        This function lets you activate pylab (matplotlib, numpy and
        interactive support) at any point during an IPython session.

        %pylab makes the following imports::

            import numpy
            import matplotlib
            from matplotlib import pylab, mlab, pyplot
            np = numpy
            plt = pyplot

            from IPython.display import display
            from IPython.core.pylabtools import figsize, getfigs

            from pylab import *
            from numpy import *

        If you pass `--no-import-all`, the last two `*` imports will be excluded.

        See the %matplotlib magic for more details about activating matplotlib
        without affecting the interactive namespace.
        """
        args = magic_arguments.parse_argstring(self.pylab, line)
        if args.no_import_all is None:
            # get default from Application
            if Application.initialized():
                app = Application.instance()
                try:
                    import_all = app.pylab_import_all
                except AttributeError:
                    import_all = True
            else:
                # nothing specified, no app - default True
                import_all = True
        else:
            # invert no-import flag
            import_all = not args.no_import_all

        gui, backend, clobbered = self.shell.enable_pylab(args.gui, import_all=import_all)
        self._show_matplotlib_backend(args.gui, backend)
        print(
            "%pylab is deprecated, use %matplotlib inline and import the required libraries."
        )
        print("Populating the interactive namespace from numpy and matplotlib")
        if clobbered:
            warn("pylab import has clobbered these variables: %s"  % clobbered +
            "\n`%matplotlib` prevents importing * from pylab and numpy"
            )

    def _show_matplotlib_backend(self, gui, backend):
        """show matplotlib message backend message"""
        if not gui or gui == 'auto':
            print("Using matplotlib backend: %s" % backend)

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\popen_loky_win32.py ===
import os
import sys
import msvcrt
import _winapi
from pickle import load
from multiprocessing import process, util
from multiprocessing.context import set_spawning_popen
from multiprocessing.popen_spawn_win32 import Popen as _Popen

from . import reduction, spawn


__all__ = ["Popen"]

#
#
#


def _path_eq(p1, p2):
    return p1 == p2 or os.path.normcase(p1) == os.path.normcase(p2)


WINENV = hasattr(sys, "_base_executable") and not _path_eq(
    sys.executable, sys._base_executable
)


def _close_handles(*handles):
    for handle in handles:
        _winapi.CloseHandle(handle)


#
# We define a Popen class similar to the one from subprocess, but
# whose constructor takes a process object as its argument.
#


class Popen(_Popen):
    """
    Start a subprocess to run the code of a process object.

    We differ from cpython implementation with the way we handle environment
    variables, in order to be able to modify then in the child processes before
    importing any library, in order to control the number of threads in C-level
    threadpools.

    We also use the loky preparation data, in particular to handle main_module
    inits and the loky resource tracker.
    """

    method = "loky"

    def __init__(self, process_obj):
        prep_data = spawn.get_preparation_data(
            process_obj._name, getattr(process_obj, "init_main_module", True)
        )

        # read end of pipe will be duplicated by the child process
        # -- see spawn_main() in spawn.py.
        #
        # bpo-33929: Previously, the read end of pipe was "stolen" by the child
        # process, but it leaked a handle if the child process had been
        # terminated before it could steal the handle from the parent process.
        rhandle, whandle = _winapi.CreatePipe(None, 0)
        wfd = msvcrt.open_osfhandle(whandle, 0)
        cmd = get_command_line(parent_pid=os.getpid(), pipe_handle=rhandle)

        python_exe = spawn.get_executable()

        # copy the environment variables to set in the child process
        child_env = {**os.environ, **process_obj.env}

        # bpo-35797: When running in a venv, we bypass the redirect
        # executor and launch our base Python.
        if WINENV and _path_eq(python_exe, sys.executable):
            cmd[0] = python_exe = sys._base_executable
            child_env["__PYVENV_LAUNCHER__"] = sys.executable

        cmd = " ".join(f'"{x}"' for x in cmd)

        with open(wfd, "wb") as to_child:
            # start process
            try:
                hp, ht, pid, _ = _winapi.CreateProcess(
                    python_exe,
                    cmd,
                    None,
                    None,
                    False,
                    0,
                    child_env,
                    None,
                    None,
                )
                _winapi.CloseHandle(ht)
            except BaseException:
                _winapi.CloseHandle(rhandle)
                raise

            # set attributes of self
            self.pid = pid
            self.returncode = None
            self._handle = hp
            self.sentinel = int(hp)
            self.finalizer = util.Finalize(
                self, _close_handles, (self.sentinel, int(rhandle))
            )

            # send information to child
            set_spawning_popen(self)
            try:
                reduction.dump(prep_data, to_child)
                reduction.dump(process_obj, to_child)
            finally:
                set_spawning_popen(None)


def get_command_line(pipe_handle, parent_pid, **kwds):
    """Returns prefix of command line used for spawning a child process."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--multiprocessing-fork", pipe_handle]
    else:
        prog = (
            "from joblib.externals.loky.backend.popen_loky_win32 import main; "
            f"main(pipe_handle={pipe_handle}, parent_pid={parent_pid})"
        )
        opts = util._args_from_interpreter_flags()
        return [
            spawn.get_executable(),
            *opts,
            "-c",
            prog,
            "--multiprocessing-fork",
        ]


def is_forking(argv):
    """Return whether commandline indicates we are forking."""
    if len(argv) >= 2 and argv[1] == "--multiprocessing-fork":
        return True
    else:
        return False


def main(pipe_handle, parent_pid=None):
    """Run code specified by data received over pipe."""
    assert is_forking(sys.argv), "Not forking"

    if parent_pid is not None:
        source_process = _winapi.OpenProcess(
            _winapi.SYNCHRONIZE | _winapi.PROCESS_DUP_HANDLE, False, parent_pid
        )
    else:
        source_process = None
    new_handle = reduction.duplicate(
        pipe_handle, source_process=source_process
    )
    fd = msvcrt.open_osfhandle(new_handle, os.O_RDONLY)
    parent_sentinel = source_process

    with os.fdopen(fd, "rb", closefd=True) as from_parent:
        process.current_process()._inheriting = True
        try:
            preparation_data = load(from_parent)
            spawn.prepare(preparation_data, parent_sentinel)
            self = load(from_parent)
        finally:
            del process.current_process()._inheriting

    exitcode = self._bootstrap(parent_sentinel)
    sys.exit(exitcode)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\gemini\files\transformation.py ===
"""
Supports writing files to Google AI Studio Files API.

For vertex ai, check out the vertex_ai/files/handler.py file.
"""
import time
from typing import List, Optional

import httpx

from litellm._logging import verbose_logger
from litellm.litellm_core_utils.prompt_templates.common_utils import extract_file_data
from litellm.llms.base_llm.files.transformation import (
    BaseFilesConfig,
    LiteLLMLoggingObj,
)
from litellm.types.llms.gemini import GeminiCreateFilesResponseObject
from litellm.types.llms.openai import (
    CreateFileRequest,
    OpenAICreateFileRequestOptionalParams,
    OpenAIFileObject,
)
from litellm.types.utils import LlmProviders

from ..common_utils import GeminiModelInfo


class GoogleAIStudioFilesHandler(GeminiModelInfo, BaseFilesConfig):
    def __init__(self):
        pass

    @property
    def custom_llm_provider(self) -> LlmProviders:
        return LlmProviders.GEMINI

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        endpoint = "upload/v1beta/files"
        api_base = self.get_api_base(api_base)
        if not api_base:
            raise ValueError("api_base is required")

        if not api_key:
            raise ValueError("api_key is required")

        url = "{}/{}?key={}".format(api_base, endpoint, api_key)
        return url

    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAICreateFileRequestOptionalParams]:
        return []

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        return optional_params

    def transform_create_file_request(
        self,
        model: str,
        create_file_data: CreateFileRequest,
        optional_params: dict,
        litellm_params: dict,
    ) -> dict:
        """
        Transform the OpenAI-style file creation request into Gemini's format

        Returns:
            dict: Contains both request data and headers for the two-step upload
        """
        # Extract the file information
        file_data = create_file_data.get("file")
        if file_data is None:
            raise ValueError("File data is required")

        # Use the common utility function to extract file data
        extracted_data = extract_file_data(file_data)

        # Get file size
        file_size = len(extracted_data["content"])

        # Step 1: Initial resumable upload request
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": extracted_data["content_type"],
            "Content-Type": "application/json",
        }
        headers.update(extracted_data["headers"])  # Add any custom headers

        # Initial metadata request body
        initial_data = {
            "file": {
                "display_name": extracted_data["filename"] or str(int(time.time()))
            }
        }

        # Step 2: Actual file upload data
        upload_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }

        return {
            "initial_request": {"headers": headers, "data": initial_data},
            "upload_request": {
                "headers": upload_headers,
                "data": extracted_data["content"],
            },
        }

    def transform_create_file_response(
        self,
        model: Optional[str],
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
        litellm_params: dict,
    ) -> OpenAIFileObject:
        """
        Transform Gemini's file upload response into OpenAI-style FileObject
        """
        try:
            response_json = raw_response.json()

            response_object = GeminiCreateFilesResponseObject(
                **response_json.get("file", {})  # type: ignore
            )

            # Extract file information from Gemini response

            return OpenAIFileObject(
                id=response_object["uri"],  # Gemini uses URI as identifier
                bytes=int(
                    response_object["sizeBytes"]
                ),  # Gemini doesn't return file size
                created_at=int(
                    time.mktime(
                        time.strptime(
                            response_object["createTime"].replace("Z", "+00:00"),
                            "%Y-%m-%dT%H:%M:%S.%f%z",
                        )
                    )
                ),
                filename=response_object["displayName"],
                object="file",
                purpose="user_data",  # Default to assistants as that's the main use case
                status="uploaded",
                status_details=None,
            )
        except Exception as e:
            verbose_logger.exception(f"Error parsing file upload response: {str(e)}")
            raise ValueError(f"Error parsing file upload response: {str(e)}")

# === NexusCore/openenv\Lib\site-packages\openai\cli\_api\completions.py ===
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Optional, cast
from argparse import ArgumentParser
from functools import partial

from openai.types.completion import Completion

from .._utils import get_client
from ..._types import NOT_GIVEN, NotGivenOr
from ..._utils import is_given
from .._errors import CLIError
from .._models import BaseModel
from ..._streaming import Stream

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register(subparser: _SubParsersAction[ArgumentParser]) -> None:
    sub = subparser.add_parser("completions.create")

    # Required
    sub.add_argument(
        "-m",
        "--model",
        help="The model to use",
        required=True,
    )

    # Optional
    sub.add_argument("-p", "--prompt", help="An optional prompt to complete from")
    sub.add_argument("--stream", help="Stream tokens as they're ready.", action="store_true")
    sub.add_argument("-M", "--max-tokens", help="The maximum number of tokens to generate", type=int)
    sub.add_argument(
        "-t",
        "--temperature",
        help="""What sampling temperature to use. Higher values means the model will take more risks. Try 0.9 for more creative applications, and 0 (argmax sampling) for ones with a well-defined answer.

Mutually exclusive with `top_p`.""",
        type=float,
    )
    sub.add_argument(
        "-P",
        "--top_p",
        help="""An alternative to sampling with temperature, called nucleus sampling, where the considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10%% probability mass are considered.

            Mutually exclusive with `temperature`.""",
        type=float,
    )
    sub.add_argument(
        "-n",
        "--n",
        help="How many sub-completions to generate for each prompt.",
        type=int,
    )
    sub.add_argument(
        "--logprobs",
        help="Include the log probabilities on the `logprobs` most likely tokens, as well the chosen tokens. So for example, if `logprobs` is 10, the API will return a list of the 10 most likely tokens. If `logprobs` is 0, only the chosen tokens will have logprobs returned.",
        type=int,
    )
    sub.add_argument(
        "--best_of",
        help="Generates `best_of` completions server-side and returns the 'best' (the one with the highest log probability per token). Results cannot be streamed.",
        type=int,
    )
    sub.add_argument(
        "--echo",
        help="Echo back the prompt in addition to the completion",
        action="store_true",
    )
    sub.add_argument(
        "--frequency_penalty",
        help="Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.",
        type=float,
    )
    sub.add_argument(
        "--presence_penalty",
        help="Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.",
        type=float,
    )
    sub.add_argument("--suffix", help="The suffix that comes after a completion of inserted text.")
    sub.add_argument("--stop", help="A stop sequence at which to stop generating tokens.")
    sub.add_argument(
        "--user",
        help="A unique identifier representing your end-user, which can help OpenAI to monitor and detect abuse.",
    )
    # TODO: add support for logit_bias
    sub.set_defaults(func=CLICompletions.create, args_model=CLICompletionCreateArgs)


class CLICompletionCreateArgs(BaseModel):
    model: str
    stream: bool = False

    prompt: Optional[str] = None
    n: NotGivenOr[int] = NOT_GIVEN
    stop: NotGivenOr[str] = NOT_GIVEN
    user: NotGivenOr[str] = NOT_GIVEN
    echo: NotGivenOr[bool] = NOT_GIVEN
    suffix: NotGivenOr[str] = NOT_GIVEN
    best_of: NotGivenOr[int] = NOT_GIVEN
    top_p: NotGivenOr[float] = NOT_GIVEN
    logprobs: NotGivenOr[int] = NOT_GIVEN
    max_tokens: NotGivenOr[int] = NOT_GIVEN
    temperature: NotGivenOr[float] = NOT_GIVEN
    presence_penalty: NotGivenOr[float] = NOT_GIVEN
    frequency_penalty: NotGivenOr[float] = NOT_GIVEN


class CLICompletions:
    @staticmethod
    def create(args: CLICompletionCreateArgs) -> None:
        if is_given(args.n) and args.n > 1 and args.stream:
            raise CLIError("Can't stream completions with n>1 with the current CLI")

        make_request = partial(
            get_client().completions.create,
            n=args.n,
            echo=args.echo,
            stop=args.stop,
            user=args.user,
            model=args.model,
            top_p=args.top_p,
            prompt=args.prompt,
            suffix=args.suffix,
            best_of=args.best_of,
            logprobs=args.logprobs,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            presence_penalty=args.presence_penalty,
            frequency_penalty=args.frequency_penalty,
        )

        if args.stream:
            return CLICompletions._stream_create(
                # mypy doesn't understand the `partial` function but pyright does
                cast(Stream[Completion], make_request(stream=True))  # pyright: ignore[reportUnnecessaryCast]
            )

        return CLICompletions._create(make_request())

    @staticmethod
    def _create(completion: Completion) -> None:
        should_print_header = len(completion.choices) > 1
        for choice in completion.choices:
            if should_print_header:
                sys.stdout.write("===== Completion {} =====\n".format(choice.index))

            sys.stdout.write(choice.text)

            if should_print_header or not choice.text.endswith("\n"):
                sys.stdout.write("\n")

            sys.stdout.flush()

    @staticmethod
    def _stream_create(stream: Stream[Completion]) -> None:
        for completion in stream:
            should_print_header = len(completion.choices) > 1
            for choice in sorted(completion.choices, key=lambda c: c.index):
                if should_print_header:
                    sys.stdout.write("===== Chat Completion {} =====\n".format(choice.index))

                sys.stdout.write(choice.text)

                if should_print_header:
                    sys.stdout.write("\n")

                sys.stdout.flush()

        sys.stdout.write("\n")

# === NexusCore/openenv\Lib\site-packages\openai\resources\containers\files\content.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import (
    StreamedBinaryAPIResponse,
    AsyncStreamedBinaryAPIResponse,
    to_custom_streamed_response_wrapper,
    async_to_custom_streamed_response_wrapper,
)
from ...._base_client import make_request_options

__all__ = ["Content", "AsyncContent"]


class Content(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ContentWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ContentWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ContentWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ContentWithStreamingResponse(self)

    def retrieve(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Retrieve Container File Content

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        return self._get(
            f"/containers/{container_id}/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )


class AsyncContent(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncContentWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncContentWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncContentWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncContentWithStreamingResponse(self)

    async def retrieve(
        self,
        file_id: str,
        *,
        container_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Retrieve Container File Content

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        return await self._get(
            f"/containers/{container_id}/files/{file_id}/content",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )


class ContentWithRawResponse:
    def __init__(self, content: Content) -> None:
        self._content = content

        self.retrieve = _legacy_response.to_raw_response_wrapper(
            content.retrieve,
        )


class AsyncContentWithRawResponse:
    def __init__(self, content: AsyncContent) -> None:
        self._content = content

        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            content.retrieve,
        )


class ContentWithStreamingResponse:
    def __init__(self, content: Content) -> None:
        self._content = content

        self.retrieve = to_custom_streamed_response_wrapper(
            content.retrieve,
            StreamedBinaryAPIResponse,
        )


class AsyncContentWithStreamingResponse:
    def __init__(self, content: AsyncContent) -> None:
        self._content = content

        self.retrieve = async_to_custom_streamed_response_wrapper(
            content.retrieve,
            AsyncStreamedBinaryAPIResponse,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\transcription_session_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal, TypedDict

__all__ = [
    "TranscriptionSessionCreateParams",
    "ClientSecret",
    "ClientSecretExpiresAt",
    "InputAudioNoiseReduction",
    "InputAudioTranscription",
    "TurnDetection",
]


class TranscriptionSessionCreateParams(TypedDict, total=False):
    client_secret: ClientSecret
    """Configuration options for the generated client secret."""

    include: List[str]
    """The set of items to include in the transcription. Current available items are:

    - `item.input_audio_transcription.logprobs`
    """

    input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: InputAudioNoiseReduction
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: InputAudioTranscription
    """Configuration for input audio transcription.

    The client can optionally set the language and prompt for transcription, these
    offer additional guidance to the transcription service.
    """

    modalities: List[Literal["text", "audio"]]
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    turn_detection: TurnDetection
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """


class ClientSecretExpiresAt(TypedDict, total=False):
    anchor: Literal["created_at"]
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: int
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class ClientSecret(TypedDict, total=False):
    expires_at: ClientSecretExpiresAt
    """Configuration for the ephemeral token expiration."""


class InputAudioNoiseReduction(TypedDict, total=False):
    type: Literal["near_field", "far_field"]
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class InputAudioTranscription(TypedDict, total=False):
    language: str
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: Literal["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"]
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: str
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class TurnDetection(TypedDict, total=False):
    create_response: bool
    """Whether or not to automatically generate a response when a VAD stop event
    occurs.

    Not available for transcription sessions.
    """

    eagerness: Literal["low", "medium", "high", "auto"]
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: bool
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs. Not available for transcription sessions.
    """

    prefix_padding_ms: int
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: int
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: float
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Literal["server_vad", "semantic_vad"]
    """Type of turn detection."""

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\blueprint.py ===
"""
    pygments.lexers.blueprint
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Blueprint UI markup language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words
from pygments.token import (
    Comment,
    Operator,
    Keyword,
    Name,
    String,
    Number,
    Punctuation,
    Whitespace,
)

__all__ = ["BlueprintLexer"]


class BlueprintLexer(RegexLexer):
    """
    For Blueprint UI markup.
    """

    name = "Blueprint"
    aliases = ["blueprint"]
    filenames = ["*.blp"]
    mimetypes = ["text/x-blueprint"]
    url = "https://gitlab.gnome.org/jwestman/blueprint-compiler"
    version_added = '2.16'

    flags = re.IGNORECASE
    tokens = {
        "root": [
            include("block-content"),
        ],
        "type": [
            (r"\$\s*[a-z_][a-z0-9_\-]*", Name.Class),
            (r"(?:([a-z_][a-z0-9_\-]*)(\s*)(\.)(\s*))?([a-z_][a-z0-9_\-]*)",
             bygroups(Name.Namespace, Whitespace, Punctuation, Whitespace, Name.Class)),
        ],
        "whitespace": [
            (r"\s+", Whitespace),
            (r"//.*?\n", Comment.Single),
            (r"/\*", Comment.Multiline, "comment-multiline"),
        ],
        "comment-multiline": [
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[^*]+", Comment.Multiline),
            (r"\*", Comment.Multiline),
        ],
        "value": [
            (r"(typeof)(\s*)(<)", bygroups(Keyword, Whitespace, Punctuation), "typeof"),
            (words(("true", "false", "null")), Keyword.Constant),
            (r"[a-z_][a-z0-9_\-]*", Name.Variable),
            (r"\|", Operator),
            (r'".*?"', String.Double),
            (r"\'.*?\'", String.Single),
            (r"0x[\d_]*", Number.Hex),
            (r"[0-9_]+", Number.Integer),
            (r"\d[\d\.a-z_]*", Number),
        ],
        "typeof": [
            include("whitespace"),
            include("type"),
            (r">", Punctuation, "#pop"),
        ],
        "content": [
            include("whitespace"),
            # Keywords
            (words(("after", "bidirectional", "bind-property", "bind", "default",
                    "destructive", "disabled", "inverted", "no-sync-create",
                    "suggested", "swapped", "sync-create", "template")),
             Keyword),
            # Translated strings
            (r"(C?_)(\s*)(\()",
             bygroups(Name.Function.Builtin, Whitespace, Punctuation),
             "paren-content"),
            # Cast expressions
            (r"(as)(\s*)(<)", bygroups(Keyword, Whitespace, Punctuation), "typeof"),
            # Closures
            (r"(\$?[a-z_][a-z0-9_\-]*)(\s*)(\()",
             bygroups(Name.Function, Whitespace, Punctuation),
             "paren-content"),
            # Objects
            (r"(?:(\$\s*[a-z_][a-z0-9_\-]+)|(?:([a-z_][a-z0-9_\-]*)(\s*)(\.)(\s*))?([a-z_][a-z0-9_\-]*))(?:(\s+)([a-z_][a-z0-9_\-]*))?(\s*)(\{)",
             bygroups(Name.Class, Name.Namespace, Whitespace, Punctuation, Whitespace,
                      Name.Class, Whitespace, Name.Variable, Whitespace, Punctuation),
             "brace-block"),
            # Misc
            include("value"),
            (r",|\.", Punctuation),
        ],
        "block-content": [
            # Import statements
            (r"(using)(\s+)([a-z_][a-z0-9_\-]*)(\s+)(\d[\d\.]*)(;)",
             bygroups(Keyword, Whitespace, Name.Namespace, Whitespace,
                      Name.Namespace, Punctuation)),
            # Menus
            (r"(menu|section|submenu)(?:(\s+)([a-z_][a-z0-9_\-]*))?(\s*)(\{)",
             bygroups(Keyword, Whitespace, Name.Variable, Whitespace, Punctuation),
             "brace-block"),
            (r"(item)(\s*)(\{)",
             bygroups(Keyword, Whitespace, Punctuation),
             "brace-block"),
            (r"(item)(\s*)(\()",
             bygroups(Keyword, Whitespace, Punctuation),
             "paren-block"),
            # Templates
            (r"template", Keyword.Declaration, "template"),
            # Nested blocks. When extensions are added, this is where they go.
            (r"(responses|items|mime-types|patterns|suffixes|marks|widgets|strings|styles)(\s*)(\[)",
             bygroups(Keyword, Whitespace, Punctuation),
             "bracket-block"),
            (r"(accessibility|setters|layout|item)(\s*)(\{)",
             bygroups(Keyword, Whitespace, Punctuation),
             "brace-block"),
            (r"(condition|mark|item)(\s*)(\()",
             bygroups(Keyword, Whitespace, Punctuation),
             "paren-content"),
            (r"\[", Punctuation, "child-type"),
            # Properties and signals
            (r"([a-z_][a-z0-9_\-]*(?:::[a-z0-9_]+)?)(\s*)(:|=>)",
             bygroups(Name.Property, Whitespace, Punctuation),
             "statement"),
            include("content"),
        ],
        "paren-block": [
            include("block-content"),
            (r"\)", Punctuation, "#pop"),
        ],
        "paren-content": [
            include("content"),
            (r"\)", Punctuation, "#pop"),
        ],
        "bracket-block": [
            include("block-content"),
            (r"\]", Punctuation, "#pop"),
        ],
        "brace-block": [
            include("block-content"),
            (r"\}", Punctuation, "#pop"),
        ],
        "statement": [
            include("content"),
            (r";", Punctuation, "#pop"),
        ],
        "child-type": [
            include("whitespace"),
            (r"(action)(\s+)(response)(\s*)(=)(\s*)",
             bygroups(Keyword, Whitespace, Name.Attribute, Whitespace,
                      Punctuation, Whitespace)),
            (words(("default", "internal-child", "response")), Keyword),
            (r"[a-z_][a-z0-9_\-]*", Name.Decorator),
            include("value"),
            (r"=", Punctuation),
            (r"\]", Punctuation, "#pop"),
        ],
        "template": [
            include("whitespace"),
            include("type"),
            (r":", Punctuation),
            (r"\{", Punctuation, ("#pop", "brace-block")),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\help.py ===
# help.py - help utilities for PythonWin.
import os

import regutil
import win32api
import win32con
import win32ui

htmlhelp_handle = None

html_help_command_translators = {
    win32con.HELP_CONTENTS: 1,  # HH_DISPLAY_TOC
    win32con.HELP_CONTEXT: 15,  # HH_HELP_CONTEXT
    win32con.HELP_FINDER: 1,  # HH_DISPLAY_TOC
}


def FinalizeHelp():
    global htmlhelp_handle
    if htmlhelp_handle is not None:
        import win32help

        try:
            # frame = win32ui.GetMainFrame().GetSafeHwnd()
            frame = 0
            win32help.HtmlHelp(frame, None, win32help.HH_UNINITIALIZE, htmlhelp_handle)
        except win32help.error:
            print("Failed to finalize htmlhelp!")
        htmlhelp_handle = None


def OpenHelpFile(fileName, helpCmd=None, helpArg=None):
    "Open a help file, given a full path"
    # default help arg.
    win32ui.DoWaitCursor(1)
    try:
        if helpCmd is None:
            helpCmd = win32con.HELP_CONTENTS
        ext = os.path.splitext(fileName)[1].lower()
        if ext == ".hlp":
            win32api.WinHelp(
                win32ui.GetMainFrame().GetSafeHwnd(), fileName, helpCmd, helpArg
            )
        # XXX - using the htmlhelp API wreaks havoc with keyboard shortcuts
        # so we disable it, forcing ShellExecute, which works fine (but
        # doesn't close the help file when Pythonwin is closed.
        # Tom Heller also points out
        # https://web.archive.org/web/20070519165457/http://www.microsoft.com:80/mind/0499/faq/faq0499.asp ,
        # which may or may not be related.
        elif 0 and ext == ".chm":
            import win32help

            global htmlhelp_handle
            helpCmd = html_help_command_translators.get(helpCmd, helpCmd)
            # frame = win32ui.GetMainFrame().GetSafeHwnd()
            frame = 0  # Don't want it overlapping ours!
            if htmlhelp_handle is None:
                htmlhelp_hwnd, htmlhelp_handle = win32help.HtmlHelp(
                    frame, None, win32help.HH_INITIALIZE
                )
            win32help.HtmlHelp(frame, fileName, helpCmd, helpArg)
        else:
            # Hope that the extension is registered, and we know what to do!
            win32api.ShellExecute(0, "open", fileName, None, "", win32con.SW_SHOW)
        return fileName
    finally:
        win32ui.DoWaitCursor(-1)


def ListAllHelpFiles():
    ret = []
    ret = _ListAllHelpFilesInRoot(win32con.HKEY_LOCAL_MACHINE)
    # Ensure we don't get dups.
    for item in _ListAllHelpFilesInRoot(win32con.HKEY_CURRENT_USER):
        if item not in ret:
            ret.append(item)
    return ret


def _ListAllHelpFilesInRoot(root):
    """Returns a list of (helpDesc, helpFname) for all registered help files"""

    retList = []
    try:
        key = win32api.RegOpenKey(
            root, regutil.BuildDefaultPythonKey() + "\\Help", 0, win32con.KEY_READ
        )
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise
        return retList
    try:
        keyNo = 0
        while 1:
            try:
                helpDesc = win32api.RegEnumKey(key, keyNo)
                helpFile = win32api.RegQueryValue(key, helpDesc)
                retList.append((helpDesc, helpFile))
                keyNo += 1
            except win32api.error as exc:
                import winerror

                if exc.winerror != winerror.ERROR_NO_MORE_ITEMS:
                    raise
                break
    finally:
        win32api.RegCloseKey(key)
    return retList


def SelectAndRunHelpFile():
    from pywin.dialogs import list

    helpFiles = ListAllHelpFiles()
    if len(helpFiles) == 1:
        # only 1 help file registered - probably ours - no point asking
        index = 0
    else:
        index = list.SelectFromLists("Select Help file", helpFiles, ["Title"])
    if index is not None:
        OpenHelpFile(helpFiles[index][1])


helpIDMap = None


def SetHelpMenuOtherHelp(mainMenu):
    """Modifies the main Help Menu to handle all registered help files.
    mainMenu -- The main menu to modify - usually from docTemplate.GetSharedMenu()
    """

    # Load all help files from the registry.
    global helpIDMap
    if helpIDMap is None:
        helpIDMap = {}
        cmdID = win32ui.ID_HELP_OTHER
        excludeList = ["Main Python Documentation", "Pythonwin Reference"]
        firstList = ListAllHelpFiles()
        # We actually want to not only exclude these entries, but
        # their help file names (as many entries may share the same name)
        excludeFnames = []
        for desc, fname in firstList:
            if desc in excludeList:
                excludeFnames.append(fname)

        helpDescs = []
        for desc, fname in firstList:
            if fname not in excludeFnames:
                helpIDMap[cmdID] = (desc, fname)
                win32ui.GetMainFrame().HookCommand(HandleHelpOtherCommand, cmdID)
                cmdID += 1

    helpMenu = mainMenu.GetSubMenu(
        mainMenu.GetMenuItemCount() - 1
    )  # Help menu always last.
    otherHelpMenuPos = 2  # can't search for ID, as sub-menu has no ID.
    otherMenu = helpMenu.GetSubMenu(otherHelpMenuPos)
    while otherMenu.GetMenuItemCount():
        otherMenu.DeleteMenu(0, win32con.MF_BYPOSITION)

    if helpIDMap:
        for id, (desc, fname) in helpIDMap.items():
            otherMenu.AppendMenu(win32con.MF_ENABLED | win32con.MF_STRING, id, desc)
    else:
        helpMenu.EnableMenuItem(
            otherHelpMenuPos, win32con.MF_BYPOSITION | win32con.MF_GRAYED
        )


def HandleHelpOtherCommand(cmd, code):
    OpenHelpFile(helpIDMap[cmd][1])

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_utils.py ===
from __future__ import annotations

import inspect
import sys
from importlib import import_module
from inspect import currentframe
from types import CodeType, FrameType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, ForwardRef, Union, cast, final
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from ._memo import TypeCheckMemo

if sys.version_info >= (3, 13):
    from typing import get_args, get_origin

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        return forwardref._evaluate(
            memo.globals, memo.locals, type_params=(), recursive_guard=frozenset()
        )

elif sys.version_info >= (3, 10):
    from typing import get_args, get_origin

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        return forwardref._evaluate(
            memo.globals, memo.locals, recursive_guard=frozenset()
        )

else:
    from typing_extensions import get_args, get_origin

    evaluate_extra_args: tuple[frozenset[Any], ...] = (
        (frozenset(),) if sys.version_info >= (3, 9) else ()
    )

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        from ._union_transformer import compile_type_hint, type_substitutions

        if not forwardref.__forward_evaluated__:
            forwardref.__forward_code__ = compile_type_hint(forwardref.__forward_arg__)

        try:
            return forwardref._evaluate(memo.globals, memo.locals, *evaluate_extra_args)
        except NameError:
            if sys.version_info < (3, 10):
                # Try again, with the type substitutions (list -> List etc.) in place
                new_globals = memo.globals.copy()
                new_globals.setdefault("Union", Union)
                if sys.version_info < (3, 9):
                    new_globals.update(type_substitutions)

                return forwardref._evaluate(
                    new_globals, memo.locals or new_globals, *evaluate_extra_args
                )

            raise


_functions_map: WeakValueDictionary[CodeType, FunctionType] = WeakValueDictionary()


def get_type_name(type_: Any) -> str:
    name: str
    for attrname in "__name__", "_name", "__forward_arg__":
        candidate = getattr(type_, attrname, None)
        if isinstance(candidate, str):
            name = candidate
            break
    else:
        origin = get_origin(type_)
        candidate = getattr(origin, "_name", None)
        if candidate is None:
            candidate = type_.__class__.__name__.strip("_")

        if isinstance(candidate, str):
            name = candidate
        else:
            return "(unknown)"

    args = get_args(type_)
    if args:
        if name == "Literal":
            formatted_args = ", ".join(repr(arg) for arg in args)
        else:
            formatted_args = ", ".join(get_type_name(arg) for arg in args)

        name += f"[{formatted_args}]"

    module = getattr(type_, "__module__", None)
    if module and module not in (None, "typing", "typing_extensions", "builtins"):
        name = module + "." + name

    return name


def qualified_name(obj: Any, *, add_class_prefix: bool = False) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having
    the module name stripped from the generated name.

    """
    if obj is None:
        return "None"
    elif inspect.isclass(obj):
        prefix = "class " if add_class_prefix else ""
        type_ = obj
    else:
        prefix = ""
        type_ = type(obj)

    module = type_.__module__
    qualname = type_.__qualname__
    name = qualname if module in ("typing", "builtins") else f"{module}.{qualname}"
    return prefix + name


def function_name(func: Callable[..., Any]) -> str:
    """
    Return the qualified name of the given function.

    Builtins and types from the :mod:`typing` package get special treatment by having
    the module name stripped from the generated name.

    """
    # For partial functions and objects with __call__ defined, __qualname__ does not
    # exist
    module = getattr(func, "__module__", "")
    qualname = (module + ".") if module not in ("builtins", "") else ""
    return qualname + getattr(func, "__qualname__", repr(func))


def resolve_reference(reference: str) -> Any:
    modulename, varname = reference.partition(":")[::2]
    if not modulename or not varname:
        raise ValueError(f"{reference!r} is not a module:varname reference")

    obj = import_module(modulename)
    for attr in varname.split("."):
        obj = getattr(obj, attr)

    return obj


def is_method_of(obj: object, cls: type) -> bool:
    return (
        inspect.isfunction(obj)
        and obj.__module__ == cls.__module__
        and obj.__qualname__.startswith(cls.__qualname__ + ".")
    )


def get_stacklevel() -> int:
    level = 1
    frame = cast(FrameType, currentframe()).f_back
    while frame and frame.f_globals.get("__name__", "").startswith("typeguard."):
        level += 1
        frame = frame.f_back

    return level


@final
class Unset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<unset>"


unset = Unset()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\search.py ===
import logging
import shutil
import sys
import textwrap
import xmlrpc.client
from collections import OrderedDict
from optparse import Values
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict

from pip._vendor.packaging.version import parse as parse_version

from pip._internal.cli.base_command import Command
from pip._internal.cli.req_command import SessionCommandMixin
from pip._internal.cli.status_codes import NO_MATCHES_FOUND, SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.metadata import get_default_environment
from pip._internal.models.index import PyPI
from pip._internal.network.xmlrpc import PipXmlrpcTransport
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import write_output

if TYPE_CHECKING:

    class TransformedHit(TypedDict):
        name: str
        summary: str
        versions: List[str]


logger = logging.getLogger(__name__)


class SearchCommand(Command, SessionCommandMixin):
    """Search for PyPI packages whose name or summary contains <query>."""

    usage = """
      %prog [options] <query>"""
    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-i",
            "--index",
            dest="index",
            metavar="URL",
            default=PyPI.pypi_url,
            help="Base URL of Python Package Index (default %default)",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        if not args:
            raise CommandError("Missing required argument (search query).")
        query = args
        pypi_hits = self.search(query, options)
        hits = transform_hits(pypi_hits)

        terminal_width = None
        if sys.stdout.isatty():
            terminal_width = shutil.get_terminal_size()[0]

        print_results(hits, terminal_width=terminal_width)
        if pypi_hits:
            return SUCCESS
        return NO_MATCHES_FOUND

    def search(self, query: List[str], options: Values) -> List[Dict[str, str]]:
        index_url = options.index

        session = self.get_default_session(options)

        transport = PipXmlrpcTransport(index_url, session)
        pypi = xmlrpc.client.ServerProxy(index_url, transport)
        try:
            hits = pypi.search({"name": query, "summary": query}, "or")
        except xmlrpc.client.Fault as fault:
            message = (
                f"XMLRPC request failed [code: {fault.faultCode}]\n{fault.faultString}"
            )
            raise CommandError(message)
        assert isinstance(hits, list)
        return hits


def transform_hits(hits: List[Dict[str, str]]) -> List["TransformedHit"]:
    """
    The list from pypi is really a list of versions. We want a list of
    packages with the list of versions stored inline. This converts the
    list from pypi into one we can use.
    """
    packages: Dict[str, TransformedHit] = OrderedDict()
    for hit in hits:
        name = hit["name"]
        summary = hit["summary"]
        version = hit["version"]

        if name not in packages.keys():
            packages[name] = {
                "name": name,
                "summary": summary,
                "versions": [version],
            }
        else:
            packages[name]["versions"].append(version)

            # if this is the highest version, replace summary and score
            if version == highest_version(packages[name]["versions"]):
                packages[name]["summary"] = summary

    return list(packages.values())


def print_dist_installation_info(name: str, latest: str) -> None:
    env = get_default_environment()
    dist = env.get_distribution(name)
    if dist is not None:
        with indent_log():
            if dist.version == latest:
                write_output("INSTALLED: %s (latest)", dist.version)
            else:
                write_output("INSTALLED: %s", dist.version)
                if parse_version(latest).pre:
                    write_output(
                        "LATEST:    %s (pre-release; install"
                        " with `pip install --pre`)",
                        latest,
                    )
                else:
                    write_output("LATEST:    %s", latest)


def print_results(
    hits: List["TransformedHit"],
    name_column_width: Optional[int] = None,
    terminal_width: Optional[int] = None,
) -> None:
    if not hits:
        return
    if name_column_width is None:
        name_column_width = (
            max(
                [
                    len(hit["name"]) + len(highest_version(hit.get("versions", ["-"])))
                    for hit in hits
                ]
            )
            + 4
        )

    for hit in hits:
        name = hit["name"]
        summary = hit["summary"] or ""
        latest = highest_version(hit.get("versions", ["-"]))
        if terminal_width is not None:
            target_width = terminal_width - name_column_width - 5
            if target_width > 10:
                # wrap and indent summary to fit terminal
                summary_lines = textwrap.wrap(summary, target_width)
                summary = ("\n" + " " * (name_column_width + 3)).join(summary_lines)

        name_latest = f"{name} ({latest})"
        line = f"{name_latest:{name_column_width}} - {summary}"
        try:
            write_output(line)
            print_dist_installation_info(name, latest)
        except UnicodeEncodeError:
            pass


def highest_version(versions: List[str]) -> str:
    return max(versions, key=parse_version)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\locations\_distutils.py ===
"""Locations where we look for configs, install stuff, etc"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

# If pip's going to use distutils, it should not be using the copy that setuptools
# might have injected into the environment. This is done by removing the injected
# shim, if it's injected.
#
# See https://github.com/pypa/pip/issues/8761 for the original discussion and
# rationale for why this is done within pip.
try:
    __import__("_distutils_hack").remove_shim()
except (ImportError, AttributeError):
    pass

import logging
import os
import sys
from distutils.cmd import Command as DistutilsCommand
from distutils.command.install import SCHEME_KEYS
from distutils.command.install import install as distutils_install_command
from distutils.sysconfig import get_python_lib
from typing import Dict, List, Optional, Union

from pip._internal.models.scheme import Scheme
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import get_major_minor_version

logger = logging.getLogger(__name__)


def distutils_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
    *,
    ignore_config_files: bool = False,
) -> Dict[str, str]:
    """
    Return a distutils install scheme
    """
    from distutils.dist import Distribution

    dist_args: Dict[str, Union[str, List[str]]] = {"name": dist_name}
    if isolated:
        dist_args["script_args"] = ["--no-user-cfg"]

    d = Distribution(dist_args)
    if not ignore_config_files:
        try:
            d.parse_config_files()
        except UnicodeDecodeError:
            paths = d.find_config_files()
            logger.warning(
                "Ignore distutils configs in %s due to encoding errors.",
                ", ".join(os.path.basename(p) for p in paths),
            )
    obj: Optional[DistutilsCommand] = None
    obj = d.get_command_obj("install", create=True)
    assert obj is not None
    i: distutils_install_command = obj
    # NOTE: setting user or home has the side-effect of creating the home dir
    # or user base for installations during finalize_options()
    # ideally, we'd prefer a scheme class that has no side-effects.
    assert not (user and prefix), f"user={user} prefix={prefix}"
    assert not (home and prefix), f"home={home} prefix={prefix}"
    i.user = user or i.user
    if user or home:
        i.prefix = ""
    i.prefix = prefix or i.prefix
    i.home = home or i.home
    i.root = root or i.root
    i.finalize_options()

    scheme: Dict[str, str] = {}
    for key in SCHEME_KEYS:
        scheme[key] = getattr(i, "install_" + key)

    # install_lib specified in setup.cfg should install *everything*
    # into there (i.e. it takes precedence over both purelib and
    # platlib).  Note, i.install_lib is *always* set after
    # finalize_options(); we only want to override here if the user
    # has explicitly requested it hence going back to the config
    if "install_lib" in d.get_option_dict("install"):
        scheme.update({"purelib": i.install_lib, "platlib": i.install_lib})

    if running_under_virtualenv():
        if home:
            prefix = home
        elif user:
            prefix = i.install_userbase
        else:
            prefix = i.prefix
        scheme["headers"] = os.path.join(
            prefix,
            "include",
            "site",
            f"python{get_major_minor_version()}",
            dist_name,
        )

        if root is not None:
            path_no_drive = os.path.splitdrive(os.path.abspath(scheme["headers"]))[1]
            scheme["headers"] = os.path.join(root, path_no_drive[1:])

    return scheme


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> Scheme:
    """
    Get the "scheme" corresponding to the input parameters. The distutils
    documentation provides the context for the available schemes:
    https://docs.python.org/3/install/index.html#alternate-installation

    :param dist_name: the name of the package to retrieve the scheme for, used
        in the headers scheme path
    :param user: indicates to use the "user" scheme
    :param home: indicates to use the "home" scheme and provides the base
        directory for the same
    :param root: root under which other directories are re-based
    :param isolated: equivalent to --no-user-cfg, i.e. do not consider
        ~/.pydistutils.cfg (posix) or ~/pydistutils.cfg (non-posix) for
        scheme paths
    :param prefix: indicates to use the "prefix" scheme and provides the
        base directory for the same
    """
    scheme = distutils_scheme(dist_name, user, home, root, isolated, prefix)
    return Scheme(
        platlib=scheme["platlib"],
        purelib=scheme["purelib"],
        headers=scheme["headers"],
        scripts=scheme["scripts"],
        data=scheme["data"],
    )


def get_bin_prefix() -> str:
    # XXX: In old virtualenv versions, sys.prefix can contain '..' components,
    # so we need to call normpath to eliminate them.
    prefix = os.path.normpath(sys.prefix)
    if WINDOWS:
        bin_py = os.path.join(prefix, "Scripts")
        # buildout uses 'bin' on Windows too?
        if not os.path.exists(bin_py):
            bin_py = os.path.join(prefix, "bin")
        return bin_py
    # Forcing to use /usr/local/bin for standard macOS framework installs
    # Also log to ~/Library/Logs/ for use with the Console.app log viewer
    if sys.platform[:6] == "darwin" and prefix[:16] == "/System/Library/":
        return "/usr/local/bin"
    return os.path.join(prefix, "bin")


def get_purelib() -> str:
    return get_python_lib(plat_specific=False)


def get_platlib() -> str:
    return get_python_lib(plat_specific=True)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\file.py ===
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

from google.protobuf import duration_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore
from google.rpc import status_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "File",
        "VideoMetadata",
    },
)


class File(proto.Message):
    r"""A file uploaded to the API.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        video_metadata (google.ai.generativelanguage_v1beta.types.VideoMetadata):
            Output only. Metadata for a video.

            This field is a member of `oneof`_ ``metadata``.
        name (str):
            Immutable. Identifier. The ``File`` resource name. The ID
            (name excluding the "files/" prefix) can contain up to 40
            characters that are lowercase alphanumeric or dashes (-).
            The ID cannot start or end with a dash. If the name is empty
            on create, a unique name will be generated. Example:
            ``files/123-456``
        display_name (str):
            Optional. The human-readable display name for the ``File``.
            The display name must be no more than 512 characters in
            length, including spaces. Example: "Welcome Image".
        mime_type (str):
            Output only. MIME type of the file.
        size_bytes (int):
            Output only. Size of the file in bytes.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` was created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` was last
            updated.
        expiration_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` will be
            deleted. Only set if the ``File`` is scheduled to expire.
        sha256_hash (bytes):
            Output only. SHA-256 hash of the uploaded
            bytes.
        uri (str):
            Output only. The uri of the ``File``.
        state (google.ai.generativelanguage_v1beta.types.File.State):
            Output only. Processing state of the File.
        error (google.rpc.status_pb2.Status):
            Output only. Error status if File processing
            failed.
    """

    class State(proto.Enum):
        r"""States for the lifecycle of a File.

        Values:
            STATE_UNSPECIFIED (0):
                The default value. This value is used if the
                state is omitted.
            PROCESSING (1):
                File is being processed and cannot be used
                for inference yet.
            ACTIVE (2):
                File is processed and available for
                inference.
            FAILED (10):
                File failed processing.
        """
        STATE_UNSPECIFIED = 0
        PROCESSING = 1
        ACTIVE = 2
        FAILED = 10

    video_metadata: "VideoMetadata" = proto.Field(
        proto.MESSAGE,
        number=12,
        oneof="metadata",
        message="VideoMetadata",
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=2,
    )
    mime_type: str = proto.Field(
        proto.STRING,
        number=3,
    )
    size_bytes: int = proto.Field(
        proto.INT64,
        number=4,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=5,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=6,
        message=timestamp_pb2.Timestamp,
    )
    expiration_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=7,
        message=timestamp_pb2.Timestamp,
    )
    sha256_hash: bytes = proto.Field(
        proto.BYTES,
        number=8,
    )
    uri: str = proto.Field(
        proto.STRING,
        number=9,
    )
    state: State = proto.Field(
        proto.ENUM,
        number=10,
        enum=State,
    )
    error: status_pb2.Status = proto.Field(
        proto.MESSAGE,
        number=11,
        message=status_pb2.Status,
    )


class VideoMetadata(proto.Message):
    r"""Metadata for a video ``File``.

    Attributes:
        video_duration (google.protobuf.duration_pb2.Duration):
            Duration of the video.
    """

    video_duration: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=1,
        message=duration_pb2.Duration,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_providers\fal_ai.py ===
import base64
import time
from abc import ABC
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from huggingface_hub import constants
from huggingface_hub.hf_api import InferenceProviderMapping
from huggingface_hub.inference._common import RequestParameters, _as_dict
from huggingface_hub.inference._providers._common import TaskProviderHelper, filter_none
from huggingface_hub.utils import get_session, hf_raise_for_status
from huggingface_hub.utils.logging import get_logger


logger = get_logger(__name__)

# Arbitrary polling interval
_POLLING_INTERVAL = 0.5


class FalAITask(TaskProviderHelper, ABC):
    def __init__(self, task: str):
        super().__init__(provider="fal-ai", base_url="https://fal.run", task=task)

    def _prepare_headers(self, headers: Dict, api_key: str) -> Dict:
        headers = super()._prepare_headers(headers, api_key)
        if not api_key.startswith("hf_"):
            headers["authorization"] = f"Key {api_key}"
        return headers

    def _prepare_route(self, mapped_model: str, api_key: str) -> str:
        return f"/{mapped_model}"


class FalAIAutomaticSpeechRecognitionTask(FalAITask):
    def __init__(self):
        super().__init__("automatic-speech-recognition")

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        if isinstance(inputs, str) and inputs.startswith(("http://", "https://")):
            # If input is a URL, pass it directly
            audio_url = inputs
        else:
            # If input is a file path, read it first
            if isinstance(inputs, str):
                with open(inputs, "rb") as f:
                    inputs = f.read()

            audio_b64 = base64.b64encode(inputs).decode()
            content_type = "audio/mpeg"
            audio_url = f"data:{content_type};base64,{audio_b64}"

        return {"audio_url": audio_url, **filter_none(parameters)}

    def get_response(self, response: Union[bytes, Dict], request_params: Optional[RequestParameters] = None) -> Any:
        text = _as_dict(response)["text"]
        if not isinstance(text, str):
            raise ValueError(f"Unexpected output format from FalAI API. Expected string, got {type(text)}.")
        return text


class FalAITextToImageTask(FalAITask):
    def __init__(self):
        super().__init__("text-to-image")

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        payload: Dict[str, Any] = {
            "prompt": inputs,
            **filter_none(parameters),
        }
        if "width" in payload and "height" in payload:
            payload["image_size"] = {
                "width": payload.pop("width"),
                "height": payload.pop("height"),
            }
        if provider_mapping_info.adapter_weights_path is not None:
            lora_path = constants.HUGGINGFACE_CO_URL_TEMPLATE.format(
                repo_id=provider_mapping_info.hf_model_id,
                revision="main",
                filename=provider_mapping_info.adapter_weights_path,
            )
            payload["loras"] = [{"path": lora_path, "scale": 1}]
            if provider_mapping_info.provider_id == "fal-ai/lora":
                # little hack: fal requires the base model for stable-diffusion-based loras but not for flux-based
                # See payloads in https://fal.ai/models/fal-ai/lora/api vs https://fal.ai/models/fal-ai/flux-lora/api
                payload["model_name"] = "stabilityai/stable-diffusion-xl-base-1.0"

        return payload

    def get_response(self, response: Union[bytes, Dict], request_params: Optional[RequestParameters] = None) -> Any:
        url = _as_dict(response)["images"][0]["url"]
        return get_session().get(url).content


class FalAITextToSpeechTask(FalAITask):
    def __init__(self):
        super().__init__("text-to-speech")

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        return {"text": inputs, **filter_none(parameters)}

    def get_response(self, response: Union[bytes, Dict], request_params: Optional[RequestParameters] = None) -> Any:
        url = _as_dict(response)["audio"]["url"]
        return get_session().get(url).content


class FalAITextToVideoTask(FalAITask):
    def __init__(self):
        super().__init__("text-to-video")

    def _prepare_base_url(self, api_key: str) -> str:
        if api_key.startswith("hf_"):
            return super()._prepare_base_url(api_key)
        else:
            logger.info(f"Calling '{self.provider}' provider directly.")
            return "https://queue.fal.run"

    def _prepare_route(self, mapped_model: str, api_key: str) -> str:
        if api_key.startswith("hf_"):
            # Use the queue subdomain for HF routing
            return f"/{mapped_model}?_subdomain=queue"
        return f"/{mapped_model}"

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        return {"prompt": inputs, **filter_none(parameters)}

    def get_response(
        self,
        response: Union[bytes, Dict],
        request_params: Optional[RequestParameters] = None,
    ) -> Any:
        response_dict = _as_dict(response)

        request_id = response_dict.get("request_id")
        if not request_id:
            raise ValueError("No request ID found in the response")
        if request_params is None:
            raise ValueError(
                "A `RequestParameters` object should be provided to get text-to-video responses with Fal AI."
            )

        # extract the base url and query params
        parsed_url = urlparse(request_params.url)
        # a bit hacky way to concatenate the provider name without parsing `parsed_url.path`
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{'/fal-ai' if parsed_url.netloc == 'router.huggingface.co' else ''}"
        query_param = f"?{parsed_url.query}" if parsed_url.query else ""

        # extracting the provider model id for status and result urls
        # from the response as it might be different from the mapped model in `request_params.url`
        model_id = urlparse(response_dict.get("response_url")).path
        status_url = f"{base_url}{str(model_id)}/status{query_param}"
        result_url = f"{base_url}{str(model_id)}{query_param}"

        status = response_dict.get("status")
        logger.info("Generating the video.. this can take several minutes.")
        while status != "COMPLETED":
            time.sleep(_POLLING_INTERVAL)
            status_response = get_session().get(status_url, headers=request_params.headers)
            hf_raise_for_status(status_response)
            status = status_response.json().get("status")

        response = get_session().get(result_url, headers=request_params.headers).json()
        url = _as_dict(response)["video"]["url"]
        return get_session().get(url).content

# === NexusCore/openenv\Lib\site-packages\litellm\llms\baseten.py ===
import json
import time
from typing import Callable

import litellm
from litellm.types.utils import ModelResponse, Usage


class BasetenError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


def validate_environment(api_key):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    return headers


def completion(
    model: str,
    messages: list,
    model_response: ModelResponse,
    print_verbose: Callable,
    encoding,
    api_key,
    logging_obj,
    optional_params: dict,
    litellm_params=None,
    logger_fn=None,
):
    headers = validate_environment(api_key)
    completion_url_fragment_1 = "https://app.baseten.co/models/"
    completion_url_fragment_2 = "/predict"
    model = model
    prompt = ""
    for message in messages:
        if "role" in message:
            if message["role"] == "user":
                prompt += f"{message['content']}"
            else:
                prompt += f"{message['content']}"
        else:
            prompt += f"{message['content']}"
    data = {
        "inputs": prompt,
        "prompt": prompt,
        "parameters": optional_params,
        "stream": (
            True
            if "stream" in optional_params and optional_params["stream"] is True
            else False
        ),
    }

    ## LOGGING
    logging_obj.pre_call(
        input=prompt,
        api_key=api_key,
        additional_args={"complete_input_dict": data},
    )
    ## COMPLETION CALL
    response = litellm.module_level_client.post(
        completion_url_fragment_1 + model + completion_url_fragment_2,
        headers=headers,
        data=json.dumps(data),
        stream=(
            True
            if "stream" in optional_params and optional_params["stream"] is True
            else False
        ),
    )
    if "text/event-stream" in response.headers["Content-Type"] or (
        "stream" in optional_params and optional_params["stream"] is True
    ):
        return response.iter_lines()
    else:
        ## LOGGING
        logging_obj.post_call(
            input=prompt,
            api_key=api_key,
            original_response=response.text,
            additional_args={"complete_input_dict": data},
        )
        print_verbose(f"raw model_response: {response.text}")
        ## RESPONSE OBJECT
        completion_response = response.json()
        if "error" in completion_response:
            raise BasetenError(
                message=completion_response["error"],
                status_code=response.status_code,
            )
        else:
            if "model_output" in completion_response:
                if (
                    isinstance(completion_response["model_output"], dict)
                    and "data" in completion_response["model_output"]
                    and isinstance(completion_response["model_output"]["data"], list)
                ):
                    model_response.choices[0].message.content = completion_response[  # type: ignore
                        "model_output"
                    ][
                        "data"
                    ][
                        0
                    ]
                elif isinstance(completion_response["model_output"], str):
                    model_response.choices[0].message.content = completion_response[  # type: ignore
                        "model_output"
                    ]
            elif "completion" in completion_response and isinstance(
                completion_response["completion"], str
            ):
                model_response.choices[0].message.content = completion_response[  # type: ignore
                    "completion"
                ]
            elif isinstance(completion_response, list) and len(completion_response) > 0:
                if "generated_text" not in completion_response:
                    raise BasetenError(
                        message=f"Unable to parse response. Original response: {response.text}",
                        status_code=response.status_code,
                    )
                model_response.choices[0].message.content = completion_response[0][  # type: ignore
                    "generated_text"
                ]
                ## GETTING LOGPROBS
                if (
                    "details" in completion_response[0]
                    and "tokens" in completion_response[0]["details"]
                ):
                    model_response.choices[0].finish_reason = completion_response[0][
                        "details"
                    ]["finish_reason"]
                    sum_logprob = 0
                    for token in completion_response[0]["details"]["tokens"]:
                        sum_logprob += token["logprob"]
                    model_response.choices[0].logprobs = sum_logprob  # type: ignore
            else:
                raise BasetenError(
                    message=f"Unable to parse response. Original response: {response.text}",
                    status_code=response.status_code,
                )

        ## CALCULATING USAGE - baseten charges on time, not tokens - have some mapping of cost here.
        prompt_tokens = len(encoding.encode(prompt))
        completion_tokens = len(
            encoding.encode(model_response["choices"][0]["message"]["content"])
        )

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        setattr(model_response, "usage", usage)
        return model_response


def embedding():
    # logic for parsing in - calling - parsing out model embedding calls
    pass

# === NexusCore/openenv\Lib\site-packages\litellm\llms\huggingface\chat\transformation.py ===
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import httpx

from litellm.types.llms.openai import AllMessageValues, ChatCompletionRequest

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any

from litellm.llms.base_llm.chat.transformation import BaseLLMException

from ...openai.chat.gpt_transformation import OpenAIGPTConfig
from ..common_utils import HuggingFaceError, _fetch_inference_provider_mapping

logger = logging.getLogger(__name__)

BASE_URL = "https://router.huggingface.co"


def _build_chat_completion_url(model_url: str) -> str:
    # Strip trailing /
    model_url = model_url.rstrip("/")

    # Append /chat/completions if not already present
    if model_url.endswith("/v1"):
        model_url += "/chat/completions"

    # Append /v1/chat/completions if not already present
    if not model_url.endswith("/chat/completions"):
        model_url += "/v1/chat/completions"

    return model_url


class HuggingFaceChatConfig(OpenAIGPTConfig):
    """
    Reference: https://huggingface.co/docs/huggingface_hub/guides/inference
    """

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        default_headers = {
            "content-type": "application/json",
        }
        if api_key is not None:
            default_headers["Authorization"] = f"Bearer {api_key}"

        headers = {**headers, **default_headers}

        return headers

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return HuggingFaceError(
            status_code=status_code, message=error_message, headers=headers
        )

    def get_base_url(self, model: str, base_url: Optional[str]) -> Optional[str]:
        """
        Get the API base for the Huggingface API.

        Do not add the chat/embedding/rerank extension here. Let the handler do this.
        """
        if model.startswith(("http://", "https://")):
            base_url = model
        elif base_url is None:
            base_url = os.getenv("HF_API_BASE") or os.getenv("HUGGINGFACE_API_BASE", "")
        return base_url

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        Get the complete URL for the API call.
        For provider-specific routing through huggingface
        """
        # Check if api_base is provided
        if api_base is not None:
            complete_url = api_base
            complete_url = _build_chat_completion_url(complete_url)
        elif os.getenv("HF_API_BASE") or os.getenv("HUGGINGFACE_API_BASE"):
            complete_url = str(os.getenv("HF_API_BASE")) or str(
                os.getenv("HUGGINGFACE_API_BASE")
            )
        elif model.startswith(("http://", "https://")):
            complete_url = model
            complete_url = _build_chat_completion_url(complete_url)
        # Default construction with provider
        else:
            # Parse provider and model
            first_part, remaining = model.split("/", 1)
            if "/" in remaining:
                provider = first_part
            else:
                provider = "hf-inference"

            if provider == "hf-inference":
                route = f"{provider}/models/{model}/v1/chat/completions"
            elif provider == "novita":
                route = f"{provider}/v3/openai/chat/completions"
            elif provider == "fireworks-ai":
                route = f"{provider}/inference/v1/chat/completions"
            else:
                route = f"{provider}/v1/chat/completions"
            complete_url = f"{BASE_URL}/{route}"

        # Ensure URL doesn't end with a slash
        complete_url = complete_url.rstrip("/")
        return complete_url

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        if litellm_params.get("api_base"):
            return dict(
                ChatCompletionRequest(model=model, messages=messages, **optional_params)
            )
        if "max_retries" in optional_params:
            logger.warning("`max_retries` is not supported. It will be ignored.")
            optional_params.pop("max_retries", None)
        first_part, remaining = model.split("/", 1)
        if "/" in remaining:
            provider = first_part
            model_id = remaining
        else:
            provider = "hf-inference"
            model_id = model
        provider_mapping = _fetch_inference_provider_mapping(model_id)
        if provider not in provider_mapping:
            raise HuggingFaceError(
                message=f"Model {model_id} is not supported for provider {provider}",
                status_code=404,
                headers={},
            )
        provider_mapping = provider_mapping[provider]
        if provider_mapping["status"] == "staging":
            logger.warning(
                f"Model {model_id} is in staging mode for provider {provider}. Meant for test purposes only."
            )
        mapped_model = provider_mapping["providerId"]
        messages = self._transform_messages(messages=messages, model=mapped_model)
        return dict(
            ChatCompletionRequest(
                model=mapped_model, messages=messages, **optional_params
            )
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\tool.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .computer_tool import ComputerTool
from .function_tool import FunctionTool
from .web_search_tool import WebSearchTool
from .file_search_tool import FileSearchTool

__all__ = [
    "Tool",
    "Mcp",
    "McpAllowedTools",
    "McpAllowedToolsMcpAllowedToolsFilter",
    "McpRequireApproval",
    "McpRequireApprovalMcpToolApprovalFilter",
    "McpRequireApprovalMcpToolApprovalFilterAlways",
    "McpRequireApprovalMcpToolApprovalFilterNever",
    "CodeInterpreter",
    "CodeInterpreterContainer",
    "CodeInterpreterContainerCodeInterpreterToolAuto",
    "ImageGeneration",
    "ImageGenerationInputImageMask",
    "LocalShell",
]


class McpAllowedToolsMcpAllowedToolsFilter(BaseModel):
    tool_names: Optional[List[str]] = None
    """List of allowed tool names."""


McpAllowedTools: TypeAlias = Union[List[str], McpAllowedToolsMcpAllowedToolsFilter, None]


class McpRequireApprovalMcpToolApprovalFilterAlways(BaseModel):
    tool_names: Optional[List[str]] = None
    """List of tools that require approval."""


class McpRequireApprovalMcpToolApprovalFilterNever(BaseModel):
    tool_names: Optional[List[str]] = None
    """List of tools that do not require approval."""


class McpRequireApprovalMcpToolApprovalFilter(BaseModel):
    always: Optional[McpRequireApprovalMcpToolApprovalFilterAlways] = None
    """A list of tools that always require approval."""

    never: Optional[McpRequireApprovalMcpToolApprovalFilterNever] = None
    """A list of tools that never require approval."""


McpRequireApproval: TypeAlias = Union[McpRequireApprovalMcpToolApprovalFilter, Literal["always", "never"], None]


class Mcp(BaseModel):
    server_label: str
    """A label for this MCP server, used to identify it in tool calls."""

    server_url: str
    """The URL for the MCP server."""

    type: Literal["mcp"]
    """The type of the MCP tool. Always `mcp`."""

    allowed_tools: Optional[McpAllowedTools] = None
    """List of allowed tool names or a filter object."""

    headers: Optional[Dict[str, str]] = None
    """Optional HTTP headers to send to the MCP server.

    Use for authentication or other purposes.
    """

    require_approval: Optional[McpRequireApproval] = None
    """Specify which of the MCP server's tools require approval."""


class CodeInterpreterContainerCodeInterpreterToolAuto(BaseModel):
    type: Literal["auto"]
    """Always `auto`."""

    file_ids: Optional[List[str]] = None
    """An optional list of uploaded files to make available to your code."""


CodeInterpreterContainer: TypeAlias = Union[str, CodeInterpreterContainerCodeInterpreterToolAuto]


class CodeInterpreter(BaseModel):
    container: CodeInterpreterContainer
    """The code interpreter container.

    Can be a container ID or an object that specifies uploaded file IDs to make
    available to your code.
    """

    type: Literal["code_interpreter"]
    """The type of the code interpreter tool. Always `code_interpreter`."""


class ImageGenerationInputImageMask(BaseModel):
    file_id: Optional[str] = None
    """File ID for the mask image."""

    image_url: Optional[str] = None
    """Base64-encoded mask image."""


class ImageGeneration(BaseModel):
    type: Literal["image_generation"]
    """The type of the image generation tool. Always `image_generation`."""

    background: Optional[Literal["transparent", "opaque", "auto"]] = None
    """Background type for the generated image.

    One of `transparent`, `opaque`, or `auto`. Default: `auto`.
    """

    input_image_mask: Optional[ImageGenerationInputImageMask] = None
    """Optional mask for inpainting.

    Contains `image_url` (string, optional) and `file_id` (string, optional).
    """

    model: Optional[Literal["gpt-image-1"]] = None
    """The image generation model to use. Default: `gpt-image-1`."""

    moderation: Optional[Literal["auto", "low"]] = None
    """Moderation level for the generated image. Default: `auto`."""

    output_compression: Optional[int] = None
    """Compression level for the output image. Default: 100."""

    output_format: Optional[Literal["png", "webp", "jpeg"]] = None
    """The output format of the generated image.

    One of `png`, `webp`, or `jpeg`. Default: `png`.
    """

    partial_images: Optional[int] = None
    """
    Number of partial images to generate in streaming mode, from 0 (default value)
    to 3.
    """

    quality: Optional[Literal["low", "medium", "high", "auto"]] = None
    """The quality of the generated image.

    One of `low`, `medium`, `high`, or `auto`. Default: `auto`.
    """

    size: Optional[Literal["1024x1024", "1024x1536", "1536x1024", "auto"]] = None
    """The size of the generated image.

    One of `1024x1024`, `1024x1536`, `1536x1024`, or `auto`. Default: `auto`.
    """


class LocalShell(BaseModel):
    type: Literal["local_shell"]
    """The type of the local shell tool. Always `local_shell`."""


Tool: TypeAlias = Annotated[
    Union[FunctionTool, FileSearchTool, WebSearchTool, ComputerTool, Mcp, CodeInterpreter, ImageGeneration, LocalShell],
    PropertyInfo(discriminator="type"),
]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\search.py ===
import logging
import shutil
import sys
import textwrap
import xmlrpc.client
from collections import OrderedDict
from optparse import Values
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict

from pip._vendor.packaging.version import parse as parse_version

from pip._internal.cli.base_command import Command
from pip._internal.cli.req_command import SessionCommandMixin
from pip._internal.cli.status_codes import NO_MATCHES_FOUND, SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.metadata import get_default_environment
from pip._internal.models.index import PyPI
from pip._internal.network.xmlrpc import PipXmlrpcTransport
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import write_output

if TYPE_CHECKING:

    class TransformedHit(TypedDict):
        name: str
        summary: str
        versions: List[str]


logger = logging.getLogger(__name__)


class SearchCommand(Command, SessionCommandMixin):
    """Search for PyPI packages whose name or summary contains <query>."""

    usage = """
      %prog [options] <query>"""
    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-i",
            "--index",
            dest="index",
            metavar="URL",
            default=PyPI.pypi_url,
            help="Base URL of Python Package Index (default %default)",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        if not args:
            raise CommandError("Missing required argument (search query).")
        query = args
        pypi_hits = self.search(query, options)
        hits = transform_hits(pypi_hits)

        terminal_width = None
        if sys.stdout.isatty():
            terminal_width = shutil.get_terminal_size()[0]

        print_results(hits, terminal_width=terminal_width)
        if pypi_hits:
            return SUCCESS
        return NO_MATCHES_FOUND

    def search(self, query: List[str], options: Values) -> List[Dict[str, str]]:
        index_url = options.index

        session = self.get_default_session(options)

        transport = PipXmlrpcTransport(index_url, session)
        pypi = xmlrpc.client.ServerProxy(index_url, transport)
        try:
            hits = pypi.search({"name": query, "summary": query}, "or")
        except xmlrpc.client.Fault as fault:
            message = (
                f"XMLRPC request failed [code: {fault.faultCode}]\n{fault.faultString}"
            )
            raise CommandError(message)
        assert isinstance(hits, list)
        return hits


def transform_hits(hits: List[Dict[str, str]]) -> List["TransformedHit"]:
    """
    The list from pypi is really a list of versions. We want a list of
    packages with the list of versions stored inline. This converts the
    list from pypi into one we can use.
    """
    packages: Dict[str, TransformedHit] = OrderedDict()
    for hit in hits:
        name = hit["name"]
        summary = hit["summary"]
        version = hit["version"]

        if name not in packages.keys():
            packages[name] = {
                "name": name,
                "summary": summary,
                "versions": [version],
            }
        else:
            packages[name]["versions"].append(version)

            # if this is the highest version, replace summary and score
            if version == highest_version(packages[name]["versions"]):
                packages[name]["summary"] = summary

    return list(packages.values())


def print_dist_installation_info(name: str, latest: str) -> None:
    env = get_default_environment()
    dist = env.get_distribution(name)
    if dist is not None:
        with indent_log():
            if dist.version == latest:
                write_output("INSTALLED: %s (latest)", dist.version)
            else:
                write_output("INSTALLED: %s", dist.version)
                if parse_version(latest).pre:
                    write_output(
                        "LATEST:    %s (pre-release; install"
                        " with `pip install --pre`)",
                        latest,
                    )
                else:
                    write_output("LATEST:    %s", latest)


def print_results(
    hits: List["TransformedHit"],
    name_column_width: Optional[int] = None,
    terminal_width: Optional[int] = None,
) -> None:
    if not hits:
        return
    if name_column_width is None:
        name_column_width = (
            max(
                [
                    len(hit["name"]) + len(highest_version(hit.get("versions", ["-"])))
                    for hit in hits
                ]
            )
            + 4
        )

    for hit in hits:
        name = hit["name"]
        summary = hit["summary"] or ""
        latest = highest_version(hit.get("versions", ["-"]))
        if terminal_width is not None:
            target_width = terminal_width - name_column_width - 5
            if target_width > 10:
                # wrap and indent summary to fit terminal
                summary_lines = textwrap.wrap(summary, target_width)
                summary = ("\n" + " " * (name_column_width + 3)).join(summary_lines)

        name_latest = f"{name} ({latest})"
        line = f"{name_latest:{name_column_width}} - {summary}"
        try:
            write_output(line)
            print_dist_installation_info(name, latest)
        except UnicodeEncodeError:
            pass


def highest_version(versions: List[str]) -> str:
    return max(versions, key=parse_version)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\locations\_distutils.py ===
"""Locations where we look for configs, install stuff, etc"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

# If pip's going to use distutils, it should not be using the copy that setuptools
# might have injected into the environment. This is done by removing the injected
# shim, if it's injected.
#
# See https://github.com/pypa/pip/issues/8761 for the original discussion and
# rationale for why this is done within pip.
try:
    __import__("_distutils_hack").remove_shim()
except (ImportError, AttributeError):
    pass

import logging
import os
import sys
from distutils.cmd import Command as DistutilsCommand
from distutils.command.install import SCHEME_KEYS
from distutils.command.install import install as distutils_install_command
from distutils.sysconfig import get_python_lib
from typing import Dict, List, Optional, Union

from pip._internal.models.scheme import Scheme
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import get_major_minor_version

logger = logging.getLogger(__name__)


def distutils_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
    *,
    ignore_config_files: bool = False,
) -> Dict[str, str]:
    """
    Return a distutils install scheme
    """
    from distutils.dist import Distribution

    dist_args: Dict[str, Union[str, List[str]]] = {"name": dist_name}
    if isolated:
        dist_args["script_args"] = ["--no-user-cfg"]

    d = Distribution(dist_args)
    if not ignore_config_files:
        try:
            d.parse_config_files()
        except UnicodeDecodeError:
            paths = d.find_config_files()
            logger.warning(
                "Ignore distutils configs in %s due to encoding errors.",
                ", ".join(os.path.basename(p) for p in paths),
            )
    obj: Optional[DistutilsCommand] = None
    obj = d.get_command_obj("install", create=True)
    assert obj is not None
    i: distutils_install_command = obj
    # NOTE: setting user or home has the side-effect of creating the home dir
    # or user base for installations during finalize_options()
    # ideally, we'd prefer a scheme class that has no side-effects.
    assert not (user and prefix), f"user={user} prefix={prefix}"
    assert not (home and prefix), f"home={home} prefix={prefix}"
    i.user = user or i.user
    if user or home:
        i.prefix = ""
    i.prefix = prefix or i.prefix
    i.home = home or i.home
    i.root = root or i.root
    i.finalize_options()

    scheme: Dict[str, str] = {}
    for key in SCHEME_KEYS:
        scheme[key] = getattr(i, "install_" + key)

    # install_lib specified in setup.cfg should install *everything*
    # into there (i.e. it takes precedence over both purelib and
    # platlib).  Note, i.install_lib is *always* set after
    # finalize_options(); we only want to override here if the user
    # has explicitly requested it hence going back to the config
    if "install_lib" in d.get_option_dict("install"):
        scheme.update({"purelib": i.install_lib, "platlib": i.install_lib})

    if running_under_virtualenv():
        if home:
            prefix = home
        elif user:
            prefix = i.install_userbase
        else:
            prefix = i.prefix
        scheme["headers"] = os.path.join(
            prefix,
            "include",
            "site",
            f"python{get_major_minor_version()}",
            dist_name,
        )

        if root is not None:
            path_no_drive = os.path.splitdrive(os.path.abspath(scheme["headers"]))[1]
            scheme["headers"] = os.path.join(root, path_no_drive[1:])

    return scheme


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> Scheme:
    """
    Get the "scheme" corresponding to the input parameters. The distutils
    documentation provides the context for the available schemes:
    https://docs.python.org/3/install/index.html#alternate-installation

    :param dist_name: the name of the package to retrieve the scheme for, used
        in the headers scheme path
    :param user: indicates to use the "user" scheme
    :param home: indicates to use the "home" scheme and provides the base
        directory for the same
    :param root: root under which other directories are re-based
    :param isolated: equivalent to --no-user-cfg, i.e. do not consider
        ~/.pydistutils.cfg (posix) or ~/pydistutils.cfg (non-posix) for
        scheme paths
    :param prefix: indicates to use the "prefix" scheme and provides the
        base directory for the same
    """
    scheme = distutils_scheme(dist_name, user, home, root, isolated, prefix)
    return Scheme(
        platlib=scheme["platlib"],
        purelib=scheme["purelib"],
        headers=scheme["headers"],
        scripts=scheme["scripts"],
        data=scheme["data"],
    )


def get_bin_prefix() -> str:
    # XXX: In old virtualenv versions, sys.prefix can contain '..' components,
    # so we need to call normpath to eliminate them.
    prefix = os.path.normpath(sys.prefix)
    if WINDOWS:
        bin_py = os.path.join(prefix, "Scripts")
        # buildout uses 'bin' on Windows too?
        if not os.path.exists(bin_py):
            bin_py = os.path.join(prefix, "bin")
        return bin_py
    # Forcing to use /usr/local/bin for standard macOS framework installs
    # Also log to ~/Library/Logs/ for use with the Console.app log viewer
    if sys.platform[:6] == "darwin" and prefix[:16] == "/System/Library/":
        return "/usr/local/bin"
    return os.path.join(prefix, "bin")


def get_purelib() -> str:
    return get_python_lib(plat_specific=False)


def get_platlib() -> str:
    return get_python_lib(plat_specific=True)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\cddl.py ===
"""
    pygments.lexers.cddl
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for the Concise data definition language (CDDL), a notational
    convention to express CBOR and JSON data structures.

    More information:
    https://datatracker.ietf.org/doc/rfc8610/

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, include, words
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, \
    Punctuation, String, Whitespace

__all__ = ['CddlLexer']


class CddlLexer(RegexLexer):
    """
    Lexer for CDDL definitions.
    """
    name = "CDDL"
    url = 'https://datatracker.ietf.org/doc/rfc8610/'
    aliases = ["cddl"]
    filenames = ["*.cddl"]
    mimetypes = ["text/x-cddl"]
    version_added = '2.8'

    _prelude_types = [
        "any",
        "b64legacy",
        "b64url",
        "bigfloat",
        "bigint",
        "bignint",
        "biguint",
        "bool",
        "bstr",
        "bytes",
        "cbor-any",
        "decfrac",
        "eb16",
        "eb64legacy",
        "eb64url",
        "encoded-cbor",
        "false",
        "float",
        "float16",
        "float16-32",
        "float32",
        "float32-64",
        "float64",
        "int",
        "integer",
        "mime-message",
        "nil",
        "nint",
        "null",
        "number",
        "regexp",
        "tdate",
        "text",
        "time",
        "true",
        "tstr",
        "uint",
        "undefined",
        "unsigned",
        "uri",
    ]

    _controls = [
        ".and",
        ".bits",
        ".cbor",
        ".cborseq",
        ".default",
        ".eq",
        ".ge",
        ".gt",
        ".le",
        ".lt",
        ".ne",
        ".regexp",
        ".size",
        ".within",
    ]

    _re_id = (
        r"[$@A-Z_a-z]"
        r"(?:[\-\.]+(?=[$@0-9A-Z_a-z])|[$@0-9A-Z_a-z])*"

    )

    # While the spec reads more like "an int must not start with 0" we use a
    # lookahead here that says "after a 0 there must be no digit". This makes the
    # '0' the invalid character in '01', which looks nicer when highlighted.
    _re_uint = r"(?:0b[01]+|0x[0-9a-fA-F]+|[1-9]\d*|0(?!\d))"
    _re_int = r"-?" + _re_uint

    tokens = {
        "commentsandwhitespace": [(r"\s+", Whitespace), (r";.+$", Comment.Single)],
        "root": [
            include("commentsandwhitespace"),
            # tag types
            (rf"#(\d\.{_re_uint})?", Keyword.Type),  # type or any
            # occurrence
            (
                rf"({_re_uint})?(\*)({_re_uint})?",
                bygroups(Number, Operator, Number),
            ),
            (r"\?|\+", Operator),  # occurrence
            (r"\^", Operator),  # cuts
            (r"(\.\.\.|\.\.)", Operator),  # rangeop
            (words(_controls, suffix=r"\b"), Operator.Word),  # ctlops
            # into choice op
            (rf"&(?=\s*({_re_id}|\())", Operator),
            (rf"~(?=\s*{_re_id})", Operator),  # unwrap op
            (r"//|/(?!/)", Operator),  # double und single slash
            (r"=>|/==|/=|=", Operator),
            (r"[\[\]{}\(\),<>:]", Punctuation),
            # Bytestrings
            (r"(b64)(')", bygroups(String.Affix, String.Single), "bstrb64url"),
            (r"(h)(')", bygroups(String.Affix, String.Single), "bstrh"),
            (r"'", String.Single, "bstr"),
            # Barewords as member keys (must be matched before values, types, typenames,
            # groupnames).
            # Token type is String as barewords are always interpreted as such.
            (rf"({_re_id})(\s*)(:)",
             bygroups(String, Whitespace, Punctuation)),
            # predefined types
            (words(_prelude_types, prefix=r"(?![\-_$@])\b", suffix=r"\b(?![\-_$@])"),
             Name.Builtin),
            # user-defined groupnames, typenames
            (_re_id, Name.Class),
            # values
            (r"0b[01]+", Number.Bin),
            (r"0o[0-7]+", Number.Oct),
            (r"0x[0-9a-fA-F]+(\.[0-9a-fA-F]+)?p[+-]?\d+", Number.Hex),  # hexfloat
            (r"0x[0-9a-fA-F]+", Number.Hex),  # hex
            # Float
            (rf"{_re_int}(?=(\.\d|e[+-]?\d))(?:\.\d+)?(?:e[+-]?\d+)?",
             Number.Float),
            # Int
            (_re_int, Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
        ],
        "bstrb64url": [
            (r"'", String.Single, "#pop"),
            include("commentsandwhitespace"),
            (r"\\.", String.Escape),
            (r"[0-9a-zA-Z\-_=]+", String.Single),
            (r".", Error),
            # (r";.+$", Token.Other),
        ],
        "bstrh": [
            (r"'", String.Single, "#pop"),
            include("commentsandwhitespace"),
            (r"\\.", String.Escape),
            (r"[0-9a-fA-F]+", String.Single),
            (r".", Error),
        ],
        "bstr": [
            (r"'", String.Single, "#pop"),
            (r"\\.", String.Escape),
            (r"[^'\\]+", String.Single),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pyreadline3\keysyms\winconstants.py ===
# This file contains constants that are normally found in win32all
# But included here to avoid the dependency


VK_LBUTTON = 1
VK_RBUTTON = 2
VK_CANCEL = 3
VK_MBUTTON = 4
VK_XBUTTON1 = 5
VK_XBUTTON2 = 6
VK_BACK = 8
VK_TAB = 9
VK_CLEAR = 12
VK_RETURN = 13
VK_SHIFT = 16
VK_CONTROL = 17
VK_MENU = 18
VK_PAUSE = 19
VK_CAPITAL = 20
VK_KANA = 0x15
VK_HANGEUL = 0x15
VK_HANGUL = 0x15
VK_JUNJA = 0x17
VK_FINAL = 0x18
VK_HANJA = 0x19
VK_KANJI = 0x19
VK_ESCAPE = 0x1B
VK_CONVERT = 0x1C
VK_NONCONVERT = 0x1D
VK_ACCEPT = 0x1E
VK_MODECHANGE = 0x1F
VK_SPACE = 32
VK_PRIOR = 33
VK_NEXT = 34
VK_END = 35
VK_HOME = 36
VK_LEFT = 37
VK_UP = 38
VK_RIGHT = 39
VK_DOWN = 40
VK_SELECT = 41
VK_PRINT = 42
VK_EXECUTE = 43
VK_SNAPSHOT = 44
VK_INSERT = 45
VK_DELETE = 46
VK_HELP = 47
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_APPS = 0x5D
VK_SLEEP = 0x5F
VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69
VK_MULTIPLY = 0x6A
VK_ADD = 0x6B
VK_SEPARATOR = 0x6C
VK_SUBTRACT = 0x6D
VK_DECIMAL = 0x6E
VK_DIVIDE = 0x6F
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B
VK_F13 = 0x7C
VK_F14 = 0x7D
VK_F15 = 0x7E
VK_F16 = 0x7F
VK_F17 = 0x80
VK_F18 = 0x81
VK_F19 = 0x82
VK_F20 = 0x83
VK_F21 = 0x84
VK_F22 = 0x85
VK_F23 = 0x86
VK_F24 = 0x87
VK_NUMLOCK = 0x90
VK_SCROLL = 0x91
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_BROWSER_BACK = 0xA6
VK_BROWSER_FORWARD = 0xA7
VK_BROWSER_REFRESH = 0xA8
VK_BROWSER_STOP = 0xA9
VK_BROWSER_SEARCH = 0xAA
VK_BROWSER_FAVORITES = 0xAB
VK_BROWSER_HOME = 0xAC
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_LAUNCH_MAIL = 0xB4
VK_LAUNCH_MEDIA_SELECT = 0xB5
VK_LAUNCH_APP1 = 0xB6
VK_LAUNCH_APP2 = 0xB7
VK_OEM_1 = 0xBA
VK_OEM_PLUS = 0xBB
VK_OEM_COMMA = 0xBC
VK_OEM_MINUS = 0xBD
VK_OEM_PERIOD = 0xBE
VK_OEM_2 = 0xBF
VK_OEM_3 = 0xC0
VK_OEM_4 = 0xDB
VK_OEM_5 = 0xDC
VK_OEM_6 = 0xDD
VK_OEM_7 = 0xDE
VK_OEM_8 = 0xDF
VK_OEM_102 = 0xE2
VK_PROCESSKEY = 0xE5
VK_PACKET = 0xE7
VK_ATTN = 0xF6
VK_CRSEL = 0xF7
VK_EXSEL = 0xF8
VK_EREOF = 0xF9
VK_PLAY = 0xFA
VK_ZOOM = 0xFB
VK_NONAME = 0xFC
VK_PA1 = 0xFD
VK_OEM_CLEAR = 0xFE

CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_MAX = 17
CF_OWNERDISPLAY = 128
CF_DSPTEXT = 129
CF_DSPBITMAP = 130
CF_DSPMETAFILEPICT = 131
CF_DSPENHMETAFILE = 142
CF_PRIVATEFIRST = 512
CF_PRIVATELAST = 767
CF_GDIOBJFIRST = 768
CF_GDIOBJLAST = 1023


GPTR = 64
GHND = 66

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\stdin.py ===
# Copyright (c) 2000 David Abrahams. Permission to copy, use, modify, sell
# and distribute this software is granted provided this copyright
# notice appears in all copies. This software is provided "as is" without
# express or implied warranty, and with no claim as to its suitability for
# any purpose.
"""Provides a class Stdin which can be used to emulate the regular old
sys.stdin for the PythonWin interactive window. Right now it just pops
up a input() dialog. With luck, someone will integrate it into the
actual PythonWin interactive window someday.

WARNING: Importing this file automatically replaces sys.stdin with an
instance of Stdin (below). This is useful because you can just open
Stdin.py in PythonWin and hit the import button to get it set up right
if you don't feel like changing PythonWin's source. To put things back
the way they were, simply use this magic incantation:
    import sys
    sys.stdin = sys.stdin.real_file
"""

import sys

get_input_line = input


class Stdin:
    def __init__(self):
        self.real_file = sys.stdin  # NOTE: Likely to be None
        self.buffer = ""
        self.closed = False

    def __getattr__(self, name):
        """Forward most functions to the real sys.stdin for absolute realism."""
        if self.real_file is None:
            raise AttributeError(name)
        return getattr(self.real_file, name)

    def isatty(self):
        """Return 1 if the file is connected to a tty(-like) device, else 0."""
        return 1

    def read(self, size=-1):
        """Read at most size bytes from the file (less if the read
        hits EOF or no more data is immediately available on a pipe,
        tty or similar device). If the size argument is negative or
        omitted, read all data until EOF is reached. The bytes are
        returned as a string object. An empty string is returned when
        EOF is encountered immediately. (For certain files, like ttys,
        it makes sense to continue reading after an EOF is hit.)"""
        result_size = self.__get_lines(size)
        return self.__extract_from_buffer(result_size)

    def readline(self, size=-1):
        """Read one entire line from the file. A trailing newline
        character is kept in the string2.6 (but may be absent when a file ends
        with an incomplete line). If the size argument is present and
        non-negative, it is a maximum byte count (including the trailing
        newline) and an incomplete line may be returned. An empty string is
        returned when EOF is hit immediately. Note: unlike stdio's fgets(),
        the returned string contains null characters ('\0') if they occurred
        in the input.
        """
        maximum_result_size = self.__get_lines(size, lambda buffer: "\n" in buffer)

        if "\n" in self.buffer[:maximum_result_size]:
            result_size = self.buffer.find("\n", 0, maximum_result_size) + 1
            assert result_size > 0
        else:
            result_size = maximum_result_size

        return self.__extract_from_buffer(result_size)

    def __extract_from_buffer(self, character_count):
        """Remove the first character_count characters from the internal buffer and
        return them.
        """
        result = self.buffer[:character_count]
        self.buffer = self.buffer[character_count:]
        return result

    def __get_lines(self, desired_size, done_reading=lambda buffer: False):
        """Keep adding lines to our internal buffer until done_reading(self.buffer)
        is true or EOF has been reached or we have desired_size bytes in the buffer.
        If desired_size < 0, we are never satisfied until we reach EOF. If done_reading
        is not supplied, it is not consulted.

        If desired_size < 0, returns the length of the internal buffer. Otherwise,
        returns desired_size.
        """
        while not done_reading(self.buffer) and (
            desired_size < 0 or len(self.buffer) < desired_size
        ):
            try:
                self.__get_line()
            except (
                EOFError,
                KeyboardInterrupt,
            ):  # deal with cancellation of get_input_line dialog
                desired_size = len(self.buffer)  # Be satisfied!

        if desired_size < 0:
            return len(self.buffer)
        else:
            return desired_size

    def __get_line(self):
        """Grab one line from get_input_line() and append it to the buffer."""
        line = get_input_line()
        print(">>>", line)  # echo input to console
        self.buffer = self.buffer + line + "\n"

    def readlines(self, *sizehint):
        """Read until EOF using readline() and return a list containing the lines
        thus read. If the optional sizehint argument is present, instead of
        reading up to EOF, whole lines totalling approximately sizehint bytes
        (possibly after rounding up to an internal buffer size) are read.
        """
        result = []
        total_read = 0
        while sizehint == () or total_read < sizehint[0]:
            line = self.readline()
            if line == "":
                break
            total_read += len(line)
            result.append(line)
        return result


if __name__ == "__main__":
    test_input = r"""this is some test
input that I am hoping
~
will be very instructive
and when I am done
I will have tested everything.
Twelve and twenty blackbirds
baked in a pie. Patty cake
patty cake so am I.
~
Thirty-five niggling idiots!
Sell you soul to the devil, baby
"""

    def fake_input(prompt=None):
        """Replacement for input() which pulls lines out of global test_input.
        For testing only!
        """
        global test_input
        if "\n" not in test_input:
            end_of_line_pos = len(test_input)
        else:
            end_of_line_pos = test_input.find("\n")
        result = test_input[:end_of_line_pos]
        test_input = test_input[end_of_line_pos + 1 :]
        if len(result) == 0 or result[0] == "~":
            raise EOFError
        return result

    get_input_line = fake_input

    # Some completely inadequate tests, just to make sure the code's not totally broken
    try:
        x = Stdin()
        print(x.read())
        print(x.readline())
        print(x.read(12))
        print(x.readline(47))
        print(x.readline(3))
        print(x.readlines())
    finally:
        get_input_line = input
else:
    sys.stdin = Stdin()

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\utils.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

import re
from typing import FrozenSet, NewType, Tuple, Union, cast

from .tags import Tag, parse_tag
from .version import InvalidVersion, Version

BuildTag = Union[Tuple[()], Tuple[int, str]]
NormalizedName = NewType("NormalizedName", str)


class InvalidName(ValueError):
    """
    An invalid distribution name; users should refer to the packaging user guide.
    """


class InvalidWheelFilename(ValueError):
    """
    An invalid wheel filename was found, users should refer to PEP 427.
    """


class InvalidSdistFilename(ValueError):
    """
    An invalid sdist filename was found, users should refer to the packaging user guide.
    """


# Core metadata spec for `Name`
_validate_regex = re.compile(
    r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
)
_canonicalize_regex = re.compile(r"[-_.]+")
_normalized_regex = re.compile(r"^([a-z0-9]|[a-z0-9]([a-z0-9-](?!--))*[a-z0-9])$")
# PEP 427: The build number must start with a digit.
_build_tag_regex = re.compile(r"(\d+)(.*)")


def canonicalize_name(name: str, *, validate: bool = False) -> NormalizedName:
    if validate and not _validate_regex.match(name):
        raise InvalidName(f"name is invalid: {name!r}")
    # This is taken from PEP 503.
    value = _canonicalize_regex.sub("-", name).lower()
    return cast(NormalizedName, value)


def is_normalized_name(name: str) -> bool:
    return _normalized_regex.match(name) is not None


def canonicalize_version(
    version: Union[Version, str], *, strip_trailing_zero: bool = True
) -> str:
    """
    This is very similar to Version.__str__, but has one subtle difference
    with the way it handles the release segment.
    """
    if isinstance(version, str):
        try:
            parsed = Version(version)
        except InvalidVersion:
            # Legacy versions cannot be normalized
            return version
    else:
        parsed = version

    parts = []

    # Epoch
    if parsed.epoch != 0:
        parts.append(f"{parsed.epoch}!")

    # Release segment
    release_segment = ".".join(str(x) for x in parsed.release)
    if strip_trailing_zero:
        # NB: This strips trailing '.0's to normalize
        release_segment = re.sub(r"(\.0)+$", "", release_segment)
    parts.append(release_segment)

    # Pre-release
    if parsed.pre is not None:
        parts.append("".join(str(x) for x in parsed.pre))

    # Post-release
    if parsed.post is not None:
        parts.append(f".post{parsed.post}")

    # Development release
    if parsed.dev is not None:
        parts.append(f".dev{parsed.dev}")

    # Local version segment
    if parsed.local is not None:
        parts.append(f"+{parsed.local}")

    return "".join(parts)


def parse_wheel_filename(
    filename: str,
) -> Tuple[NormalizedName, Version, BuildTag, FrozenSet[Tag]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename}"
        )

    parts = filename.split("-", dashes - 2)
    name_part = parts[0]
    # See PEP 427 for the rules on escaping the project name.
    if "__" in name_part or re.match(r"^[\w\d._]*$", name_part, re.UNICODE) is None:
        raise InvalidWheelFilename(f"Invalid project name: {filename}")
    name = canonicalize_name(name_part)

    try:
        version = Version(parts[1])
    except InvalidVersion as e:
        raise InvalidWheelFilename(
            f"Invalid wheel filename (invalid version): {filename}"
        ) from e

    if dashes == 5:
        build_part = parts[2]
        build_match = _build_tag_regex.match(build_part)
        if build_match is None:
            raise InvalidWheelFilename(
                f"Invalid build number: {build_part} in '{filename}'"
            )
        build = cast(BuildTag, (int(build_match.group(1)), build_match.group(2)))
    else:
        build = ()
    tags = parse_tag(parts[-1])
    return (name, version, build, tags)


def parse_sdist_filename(filename: str) -> Tuple[NormalizedName, Version]:
    if filename.endswith(".tar.gz"):
        file_stem = filename[: -len(".tar.gz")]
    elif filename.endswith(".zip"):
        file_stem = filename[: -len(".zip")]
    else:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (extension must be '.tar.gz' or '.zip'):"
            f" {filename}"
        )

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name_part, sep, version_part = file_stem.rpartition("-")
    if not sep:
        raise InvalidSdistFilename(f"Invalid sdist filename: {filename}")

    name = canonicalize_name(name_part)

    try:
        version = Version(version_part)
    except InvalidVersion as e:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (invalid version): {filename}"
        ) from e

    return (name, version)

# === NexusCore/openenv\Lib\site-packages\zmq\sugar\poll.py ===
"""0MQ polling related functions and classes."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

from typing import Any

from zmq.backend import zmq_poll
from zmq.constants import POLLERR, POLLIN, POLLOUT

# -----------------------------------------------------------------------------
# Polling related methods
# -----------------------------------------------------------------------------


class Poller:
    """A stateful poll interface that mirrors Python's built-in poll."""

    sockets: list[tuple[Any, int]]
    _map: dict

    def __init__(self) -> None:
        self.sockets = []
        self._map = {}

    def __contains__(self, socket: Any) -> bool:
        return socket in self._map

    def register(self, socket: Any, flags: int = POLLIN | POLLOUT):
        """p.register(socket, flags=POLLIN|POLLOUT)

        Register a 0MQ socket or native fd for I/O monitoring.

        register(s,0) is equivalent to unregister(s).

        Parameters
        ----------
        socket : zmq.Socket or native socket
            A zmq.Socket or any Python object having a ``fileno()``
            method that returns a valid file descriptor.
        flags : int
            The events to watch for.  Can be POLLIN, POLLOUT or POLLIN|POLLOUT.
            If `flags=0`, socket will be unregistered.
        """
        if flags:
            if socket in self._map:
                idx = self._map[socket]
                self.sockets[idx] = (socket, flags)
            else:
                idx = len(self.sockets)
                self.sockets.append((socket, flags))
                self._map[socket] = idx
        elif socket in self._map:
            # uregister sockets registered with no events
            self.unregister(socket)
        else:
            # ignore new sockets with no events
            pass

    def modify(self, socket, flags=POLLIN | POLLOUT):
        """Modify the flags for an already registered 0MQ socket or native fd."""
        self.register(socket, flags)

    def unregister(self, socket: Any):
        """Remove a 0MQ socket or native fd for I/O monitoring.

        Parameters
        ----------
        socket : Socket
            The socket instance to stop polling.
        """
        idx = self._map.pop(socket)
        self.sockets.pop(idx)
        # shift indices after deletion
        for socket, flags in self.sockets[idx:]:
            self._map[socket] -= 1

    def poll(self, timeout: int | None = None) -> list[tuple[Any, int]]:
        """Poll the registered 0MQ or native fds for I/O.

        If there are currently events ready to be processed, this function will return immediately.
        Otherwise, this function will return as soon the first event is available or after timeout
        milliseconds have elapsed.

        Parameters
        ----------
        timeout : int
            The timeout in milliseconds. If None, no `timeout` (infinite). This
            is in milliseconds to be compatible with ``select.poll()``.

        Returns
        -------
        events : list
            The list of events that are ready to be processed.
            This is a list of tuples of the form ``(socket, event_mask)``, where the 0MQ Socket
            or integer fd is the first element, and the poll event mask (POLLIN, POLLOUT) is the second.
            It is common to call ``events = dict(poller.poll())``,
            which turns the list of tuples into a mapping of ``socket : event_mask``.
        """
        if timeout is None or timeout < 0:
            timeout = -1
        elif isinstance(timeout, float):
            timeout = int(timeout)
        return zmq_poll(self.sockets, timeout=timeout)


def select(
    rlist: list, wlist: list, xlist: list, timeout: float | None = None
) -> tuple[list, list, list]:
    """select(rlist, wlist, xlist, timeout=None) -> (rlist, wlist, xlist)

    Return the result of poll as a lists of sockets ready for r/w/exception.

    This has the same interface as Python's built-in ``select.select()`` function.

    Parameters
    ----------
    timeout : float, optional
        The timeout in seconds. If None, no timeout (infinite). This is in seconds to be
        compatible with ``select.select()``.
    rlist : list
        sockets/FDs to be polled for read events
    wlist : list
        sockets/FDs to be polled for write events
    xlist : list
        sockets/FDs to be polled for error events

    Returns
    -------
    rlist: list
        list of sockets or FDs that are readable
    wlist: list
        list of sockets or FDs that are writable
    xlist: list
        list of sockets or FDs that had error events (rare)
    """
    if timeout is None:
        timeout = -1
    # Convert from sec -> ms for zmq_poll.
    # zmq_poll accepts 3.x style timeout in ms
    timeout = int(timeout * 1000.0)
    if timeout < 0:
        timeout = -1
    sockets = []
    for s in set(rlist + wlist + xlist):
        flags = 0
        if s in rlist:
            flags |= POLLIN
        if s in wlist:
            flags |= POLLOUT
        if s in xlist:
            flags |= POLLERR
        sockets.append((s, flags))
    return_sockets = zmq_poll(sockets, timeout)
    rlist, wlist, xlist = [], [], []
    for s, flags in return_sockets:
        if flags & POLLIN:
            rlist.append(s)
        if flags & POLLOUT:
            wlist.append(s)
        if flags & POLLERR:
            xlist.append(s)
    return rlist, wlist, xlist


# -----------------------------------------------------------------------------
# Symbols to export
# -----------------------------------------------------------------------------

__all__ = ['Poller', 'select']

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\index_command.py ===
"""
Contains command classes which may interact with an index / the network.

Unlike its sister module, req_command, this module still uses lazy imports
so commands which don't always hit the network (e.g. list w/o --outdated or
--uptodate) don't need waste time importing PipSession and friends.
"""

import logging
import os
import sys
from optparse import Values
from typing import TYPE_CHECKING, List, Optional

from pip._vendor import certifi

from pip._internal.cli.base_command import Command
from pip._internal.cli.command_context import CommandContextMixIn

if TYPE_CHECKING:
    from ssl import SSLContext

    from pip._internal.network.session import PipSession

logger = logging.getLogger(__name__)


def _create_truststore_ssl_context() -> Optional["SSLContext"]:
    if sys.version_info < (3, 10):
        logger.debug("Disabling truststore because Python version isn't 3.10+")
        return None

    try:
        import ssl
    except ImportError:
        logger.warning("Disabling truststore since ssl support is missing")
        return None

    try:
        from pip._vendor import truststore
    except ImportError:
        logger.warning("Disabling truststore because platform isn't supported")
        return None

    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(certifi.where())
    return ctx


class SessionCommandMixin(CommandContextMixIn):
    """
    A class mixin for command classes needing _build_session().
    """

    def __init__(self) -> None:
        super().__init__()
        self._session: Optional[PipSession] = None

    @classmethod
    def _get_index_urls(cls, options: Values) -> Optional[List[str]]:
        """Return a list of index urls from user-provided options."""
        index_urls = []
        if not getattr(options, "no_index", False):
            url = getattr(options, "index_url", None)
            if url:
                index_urls.append(url)
        urls = getattr(options, "extra_index_urls", None)
        if urls:
            index_urls.extend(urls)
        # Return None rather than an empty list
        return index_urls or None

    def get_default_session(self, options: Values) -> "PipSession":
        """Get a default-managed session."""
        if self._session is None:
            self._session = self.enter_context(self._build_session(options))
            # there's no type annotation on requests.Session, so it's
            # automatically ContextManager[Any] and self._session becomes Any,
            # then https://github.com/python/mypy/issues/7696 kicks in
            assert self._session is not None
        return self._session

    def _build_session(
        self,
        options: Values,
        retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> "PipSession":
        from pip._internal.network.session import PipSession

        cache_dir = options.cache_dir
        assert not cache_dir or os.path.isabs(cache_dir)

        if "legacy-certs" not in options.deprecated_features_enabled:
            ssl_context = _create_truststore_ssl_context()
        else:
            ssl_context = None

        session = PipSession(
            cache=os.path.join(cache_dir, "http-v2") if cache_dir else None,
            retries=retries if retries is not None else options.retries,
            trusted_hosts=options.trusted_hosts,
            index_urls=self._get_index_urls(options),
            ssl_context=ssl_context,
        )

        # Handle custom ca-bundles from the user
        if options.cert:
            session.verify = options.cert

        # Handle SSL client certificate
        if options.client_cert:
            session.cert = options.client_cert

        # Handle timeouts
        if options.timeout or timeout:
            session.timeout = timeout if timeout is not None else options.timeout

        # Handle configured proxies
        if options.proxy:
            session.proxies = {
                "http": options.proxy,
                "https": options.proxy,
            }
            session.trust_env = False
            session.pip_proxy = options.proxy

        # Determine if we can prompt the user for authentication or not
        session.auth.prompting = not options.no_input
        session.auth.keyring_provider = options.keyring_provider

        return session


def _pip_self_version_check(session: "PipSession", options: Values) -> None:
    from pip._internal.self_outdated_check import pip_self_version_check as check

    check(session, options)


class IndexGroupCommand(Command, SessionCommandMixin):
    """
    Abstract base class for commands with the index_group options.

    This also corresponds to the commands that permit the pip version check.
    """

    def handle_pip_version_check(self, options: Values) -> None:
        """
        Do the pip version check if not disabled.

        This overrides the default behavior of not doing the check.
        """
        # Make sure the index_group options are present.
        assert hasattr(options, "no_index")

        if options.disable_pip_version_check or options.no_index:
            return

        try:
            # Otherwise, check if we're using the latest version of pip available.
            session = self._build_session(
                options,
                retries=0,
                timeout=min(5, options.timeout),
            )
            with session:
                _pip_self_version_check(session, options)
        except Exception:
            logger.warning("There was an error checking the latest version of pip.")
            logger.debug("See below for error", exc_info=True)

# === NexusCore/openenv\Lib\site-packages\importlib_metadata\_itertools.py ===
from collections import defaultdict, deque
from itertools import filterfalse


def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


# copied from more_itertools 8.8
def always_iterable(obj, base_type=(str, bytes)):
    """If *obj* is iterable, return an iterator over its items::

        >>> obj = (1, 2, 3)
        >>> list(always_iterable(obj))
        [1, 2, 3]

    If *obj* is not iterable, return a one-item iterable containing *obj*::

        >>> obj = 1
        >>> list(always_iterable(obj))
        [1]

    If *obj* is ``None``, return an empty iterable:

        >>> obj = None
        >>> list(always_iterable(None))
        []

    By default, binary and text strings are not considered iterable::

        >>> obj = 'foo'
        >>> list(always_iterable(obj))
        ['foo']

    If *base_type* is set, objects for which ``isinstance(obj, base_type)``
    returns ``True`` won't be considered iterable.

        >>> obj = {'a': 1}
        >>> list(always_iterable(obj))  # Iterate over the dict's keys
        ['a']
        >>> list(always_iterable(obj, base_type=dict))  # Treat dicts as a unit
        [{'a': 1}]

    Set *base_type* to ``None`` to avoid any special handling and treat objects
    Python considers iterable as iterable:

        >>> obj = 'foo'
        >>> list(always_iterable(obj, base_type=None))
        ['f', 'o', 'o']
    """
    if obj is None:
        return iter(())

    if (base_type is not None) and isinstance(obj, base_type):
        return iter((obj,))

    try:
        return iter(obj)
    except TypeError:
        return iter((obj,))


# Copied from more_itertools 10.3
class bucket:
    """Wrap *iterable* and return an object that buckets the iterable into
    child iterables based on a *key* function.

        >>> iterable = ['a1', 'b1', 'c1', 'a2', 'b2', 'c2', 'b3']
        >>> s = bucket(iterable, key=lambda x: x[0])  # Bucket by 1st character
        >>> sorted(list(s))  # Get the keys
        ['a', 'b', 'c']
        >>> a_iterable = s['a']
        >>> next(a_iterable)
        'a1'
        >>> next(a_iterable)
        'a2'
        >>> list(s['b'])
        ['b1', 'b2', 'b3']

    The original iterable will be advanced and its items will be cached until
    they are used by the child iterables. This may require significant storage.

    By default, attempting to select a bucket to which no items belong  will
    exhaust the iterable and cache all values.
    If you specify a *validator* function, selected buckets will instead be
    checked against it.

        >>> from itertools import count
        >>> it = count(1, 2)  # Infinite sequence of odd numbers
        >>> key = lambda x: x % 10  # Bucket by last digit
        >>> validator = lambda x: x in {1, 3, 5, 7, 9}  # Odd digits only
        >>> s = bucket(it, key=key, validator=validator)
        >>> 2 in s
        False
        >>> list(s[2])
        []

    """

    def __init__(self, iterable, key, validator=None):
        self._it = iter(iterable)
        self._key = key
        self._cache = defaultdict(deque)
        self._validator = validator or (lambda x: True)

    def __contains__(self, value):
        if not self._validator(value):
            return False

        try:
            item = next(self[value])
        except StopIteration:
            return False
        else:
            self._cache[value].appendleft(item)

        return True

    def _get_values(self, value):
        """
        Helper to yield items from the parent iterator that match *value*.
        Items that don't match are stored in the local cache as they
        are encountered.
        """
        while True:
            # If we've cached some items that match the target value, emit
            # the first one and evict it from the cache.
            if self._cache[value]:
                yield self._cache[value].popleft()
            # Otherwise we need to advance the parent iterator to search for
            # a matching item, caching the rest.
            else:
                while True:
                    try:
                        item = next(self._it)
                    except StopIteration:
                        return
                    item_value = self._key(item)
                    if item_value == value:
                        yield item
                        break
                    elif self._validator(item_value):
                        self._cache[item_value].append(item)

    def __iter__(self):
        for item in self._it:
            item_value = self._key(item)
            if self._validator(item_value):
                self._cache[item_value].append(item)

        yield from self._cache.keys()

    def __getitem__(self, value):
        if not self._validator(value):
            return iter(())

        return self._get_values(value)

# === NexusCore/openenv\Lib\site-packages\google\auth\_credentials_async.py ===
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Interfaces for credentials."""

import abc
import inspect

from google.auth import credentials


class Credentials(credentials.Credentials, metaclass=abc.ABCMeta):
    """Async inherited credentials class from google.auth.credentials.
    The added functionality is the before_request call which requires
    async/await syntax.
    All credentials have a :attr:`token` that is used for authentication and
    may also optionally set an :attr:`expiry` to indicate when the token will
    no longer be valid.

    Most credentials will be :attr:`invalid` until :meth:`refresh` is called.
    Credentials can do this automatically before the first HTTP request in
    :meth:`before_request`.

    Although the token and expiration will change as the credentials are
    :meth:`refreshed <refresh>` and used, credentials should be considered
    immutable. Various credentials will accept configuration such as private
    keys, scopes, and other options. These options are not changeable after
    construction. Some classes will provide mechanisms to copy the credentials
    with modifications such as :meth:`ScopedCredentials.with_scopes`.
    """

    async def before_request(self, request, method, url, headers):
        """Performs credential-specific before request logic.

        Refreshes the credentials if necessary, then calls :meth:`apply` to
        apply the token to the authentication header.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.
            method (str): The request's HTTP method or the RPC method being
                invoked.
            url (str): The request's URI or the RPC service's URI.
            headers (Mapping): The request's headers.
        """
        # pylint: disable=unused-argument
        # (Subclasses may use these arguments to ascertain information about
        # the http request.)

        if not self.valid:
            if inspect.iscoroutinefunction(self.refresh):
                await self.refresh(request)
            else:
                self.refresh(request)
        self.apply(headers)


class CredentialsWithQuotaProject(credentials.CredentialsWithQuotaProject):
    """Abstract base for credentials supporting ``with_quota_project`` factory"""


class AnonymousCredentials(credentials.AnonymousCredentials, Credentials):
    """Credentials that do not provide any authentication information.

    These are useful in the case of services that support anonymous access or
    local service emulators that do not use credentials. This class inherits
    from the sync anonymous credentials file, but is kept if async credentials
    is initialized and we would like anonymous credentials.
    """


class ReadOnlyScoped(credentials.ReadOnlyScoped, metaclass=abc.ABCMeta):
    """Interface for credentials whose scopes can be queried.

    OAuth 2.0-based credentials allow limiting access using scopes as described
    in `RFC6749 Section 3.3`_.
    If a credential class implements this interface then the credentials either
    use scopes in their implementation.

    Some credentials require scopes in order to obtain a token. You can check
    if scoping is necessary with :attr:`requires_scopes`::

        if credentials.requires_scopes:
            # Scoping is required.
            credentials = _credentials_async.with_scopes(scopes=['one', 'two'])

    Credentials that require scopes must either be constructed with scopes::

        credentials = SomeScopedCredentials(scopes=['one', 'two'])

    Or must copy an existing instance using :meth:`with_scopes`::

        scoped_credentials = _credentials_async.with_scopes(scopes=['one', 'two'])

    Some credentials have scopes but do not allow or require scopes to be set,
    these credentials can be used as-is.

    .. _RFC6749 Section 3.3: https://tools.ietf.org/html/rfc6749#section-3.3
    """


class Scoped(credentials.Scoped):
    """Interface for credentials whose scopes can be replaced while copying.

    OAuth 2.0-based credentials allow limiting access using scopes as described
    in `RFC6749 Section 3.3`_.
    If a credential class implements this interface then the credentials either
    use scopes in their implementation.

    Some credentials require scopes in order to obtain a token. You can check
    if scoping is necessary with :attr:`requires_scopes`::

        if credentials.requires_scopes:
            # Scoping is required.
            credentials = _credentials_async.create_scoped(['one', 'two'])

    Credentials that require scopes must either be constructed with scopes::

        credentials = SomeScopedCredentials(scopes=['one', 'two'])

    Or must copy an existing instance using :meth:`with_scopes`::

        scoped_credentials = credentials.with_scopes(scopes=['one', 'two'])

    Some credentials have scopes but do not allow or require scopes to be set,
    these credentials can be used as-is.

    .. _RFC6749 Section 3.3: https://tools.ietf.org/html/rfc6749#section-3.3
    """


def with_scopes_if_required(credentials, scopes):
    """Creates a copy of the credentials with scopes if scoping is required.

    This helper function is useful when you do not know (or care to know) the
    specific type of credentials you are using (such as when you use
    :func:`google.auth.default`). This function will call
    :meth:`Scoped.with_scopes` if the credentials are scoped credentials and if
    the credentials require scoping. Otherwise, it will return the credentials
    as-is.

    Args:
        credentials (google.auth.credentials.Credentials): The credentials to
            scope if necessary.
        scopes (Sequence[str]): The list of scopes to use.

    Returns:
        google.auth._credentials_async.Credentials: Either a new set of scoped
            credentials, or the passed in credentials instance if no scoping
            was required.
    """
    if isinstance(credentials, Scoped) and credentials.requires_scopes:
        return credentials.with_scopes(scopes)
    else:
        return credentials


class Signing(credentials.Signing, metaclass=abc.ABCMeta):
    """Interface for credentials that can cryptographically sign messages."""

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\prompt_caching_cache.py ===
"""
Wrapper around router cache. Meant to store model id when prompt caching supported prompt is called.
"""

import hashlib
import json
from typing import TYPE_CHECKING, Any, List, Optional, TypedDict, Union

from litellm.caching.caching import DualCache
from litellm.caching.in_memory_cache import InMemoryCache
from litellm.types.llms.openai import AllMessageValues, ChatCompletionToolParam

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.router import Router

    litellm_router = Router
    Span = Union[_Span, Any]
else:
    Span = Any
    litellm_router = Any


class PromptCachingCacheValue(TypedDict):
    model_id: str


class PromptCachingCache:
    def __init__(self, cache: DualCache):
        self.cache = cache
        self.in_memory_cache = InMemoryCache()

    @staticmethod
    def serialize_object(obj: Any) -> Any:
        """Helper function to serialize Pydantic objects, dictionaries, or fallback to string."""
        if hasattr(obj, "dict"):
            # If the object is a Pydantic model, use its `dict()` method
            return obj.dict()
        elif isinstance(obj, dict):
            # If the object is a dictionary, serialize it with sorted keys
            return json.dumps(
                obj, sort_keys=True, separators=(",", ":")
            )  # Standardize serialization

        elif isinstance(obj, list):
            # Serialize lists by ensuring each element is handled properly
            return [PromptCachingCache.serialize_object(item) for item in obj]
        elif isinstance(obj, (int, float, bool)):
            return obj  # Keep primitive types as-is
        return str(obj)

    @staticmethod
    def get_prompt_caching_cache_key(
        messages: Optional[List[AllMessageValues]],
        tools: Optional[List[ChatCompletionToolParam]],
    ) -> Optional[str]:
        if messages is None and tools is None:
            return None
        # Use serialize_object for consistent and stable serialization
        data_to_hash = {}
        if messages is not None:
            serialized_messages = PromptCachingCache.serialize_object(messages)
            data_to_hash["messages"] = serialized_messages
        if tools is not None:
            serialized_tools = PromptCachingCache.serialize_object(tools)
            data_to_hash["tools"] = serialized_tools

        # Combine serialized data into a single string
        data_to_hash_str = json.dumps(
            data_to_hash,
            sort_keys=True,
            separators=(",", ":"),
        )

        # Create a hash of the serialized data for a stable cache key
        hashed_data = hashlib.sha256(data_to_hash_str.encode()).hexdigest()
        return f"deployment:{hashed_data}:prompt_caching"

    def add_model_id(
        self,
        model_id: str,
        messages: Optional[List[AllMessageValues]],
        tools: Optional[List[ChatCompletionToolParam]],
    ) -> None:
        if messages is None and tools is None:
            return None

        cache_key = PromptCachingCache.get_prompt_caching_cache_key(messages, tools)
        self.cache.set_cache(
            cache_key, PromptCachingCacheValue(model_id=model_id), ttl=300
        )
        return None

    async def async_add_model_id(
        self,
        model_id: str,
        messages: Optional[List[AllMessageValues]],
        tools: Optional[List[ChatCompletionToolParam]],
    ) -> None:
        if messages is None and tools is None:
            return None

        cache_key = PromptCachingCache.get_prompt_caching_cache_key(messages, tools)
        await self.cache.async_set_cache(
            cache_key,
            PromptCachingCacheValue(model_id=model_id),
            ttl=300,  # store for 5 minutes
        )
        return None

    async def async_get_model_id(
        self,
        messages: Optional[List[AllMessageValues]],
        tools: Optional[List[ChatCompletionToolParam]],
    ) -> Optional[PromptCachingCacheValue]:
        """
        if messages is not none
        - check full messages
        - check messages[:-1]
        - check messages[:-2]
        - check messages[:-3]

        use self.cache.async_batch_get_cache(keys=potential_cache_keys])
        """
        if messages is None and tools is None:
            return None

        # Generate potential cache keys by slicing messages

        potential_cache_keys = []

        if messages is not None:
            full_cache_key = PromptCachingCache.get_prompt_caching_cache_key(
                messages, tools
            )
            potential_cache_keys.append(full_cache_key)

            # Check progressively shorter message slices
            for i in range(1, min(4, len(messages))):
                partial_messages = messages[:-i]
                partial_cache_key = PromptCachingCache.get_prompt_caching_cache_key(
                    partial_messages, tools
                )
                potential_cache_keys.append(partial_cache_key)

        # Perform batch cache lookup
        cache_results = await self.cache.async_batch_get_cache(
            keys=potential_cache_keys
        )

        if cache_results is None:
            return None

        # Return the first non-None cache result
        for result in cache_results:
            if result is not None:
                return result

        return None

    def get_model_id(
        self,
        messages: Optional[List[AllMessageValues]],
        tools: Optional[List[ChatCompletionToolParam]],
    ) -> Optional[PromptCachingCacheValue]:
        if messages is None and tools is None:
            return None

        cache_key = PromptCachingCache.get_prompt_caching_cache_key(messages, tools)
        return self.cache.get_cache(cache_key)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\index_command.py ===
"""
Contains command classes which may interact with an index / the network.

Unlike its sister module, req_command, this module still uses lazy imports
so commands which don't always hit the network (e.g. list w/o --outdated or
--uptodate) don't need waste time importing PipSession and friends.
"""

import logging
import os
import sys
from optparse import Values
from typing import TYPE_CHECKING, List, Optional

from pip._vendor import certifi

from pip._internal.cli.base_command import Command
from pip._internal.cli.command_context import CommandContextMixIn

if TYPE_CHECKING:
    from ssl import SSLContext

    from pip._internal.network.session import PipSession

logger = logging.getLogger(__name__)


def _create_truststore_ssl_context() -> Optional["SSLContext"]:
    if sys.version_info < (3, 10):
        logger.debug("Disabling truststore because Python version isn't 3.10+")
        return None

    try:
        import ssl
    except ImportError:
        logger.warning("Disabling truststore since ssl support is missing")
        return None

    try:
        from pip._vendor import truststore
    except ImportError:
        logger.warning("Disabling truststore because platform isn't supported")
        return None

    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(certifi.where())
    return ctx


class SessionCommandMixin(CommandContextMixIn):
    """
    A class mixin for command classes needing _build_session().
    """

    def __init__(self) -> None:
        super().__init__()
        self._session: Optional[PipSession] = None

    @classmethod
    def _get_index_urls(cls, options: Values) -> Optional[List[str]]:
        """Return a list of index urls from user-provided options."""
        index_urls = []
        if not getattr(options, "no_index", False):
            url = getattr(options, "index_url", None)
            if url:
                index_urls.append(url)
        urls = getattr(options, "extra_index_urls", None)
        if urls:
            index_urls.extend(urls)
        # Return None rather than an empty list
        return index_urls or None

    def get_default_session(self, options: Values) -> "PipSession":
        """Get a default-managed session."""
        if self._session is None:
            self._session = self.enter_context(self._build_session(options))
            # there's no type annotation on requests.Session, so it's
            # automatically ContextManager[Any] and self._session becomes Any,
            # then https://github.com/python/mypy/issues/7696 kicks in
            assert self._session is not None
        return self._session

    def _build_session(
        self,
        options: Values,
        retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> "PipSession":
        from pip._internal.network.session import PipSession

        cache_dir = options.cache_dir
        assert not cache_dir or os.path.isabs(cache_dir)

        if "legacy-certs" not in options.deprecated_features_enabled:
            ssl_context = _create_truststore_ssl_context()
        else:
            ssl_context = None

        session = PipSession(
            cache=os.path.join(cache_dir, "http-v2") if cache_dir else None,
            retries=retries if retries is not None else options.retries,
            trusted_hosts=options.trusted_hosts,
            index_urls=self._get_index_urls(options),
            ssl_context=ssl_context,
        )

        # Handle custom ca-bundles from the user
        if options.cert:
            session.verify = options.cert

        # Handle SSL client certificate
        if options.client_cert:
            session.cert = options.client_cert

        # Handle timeouts
        if options.timeout or timeout:
            session.timeout = timeout if timeout is not None else options.timeout

        # Handle configured proxies
        if options.proxy:
            session.proxies = {
                "http": options.proxy,
                "https": options.proxy,
            }
            session.trust_env = False
            session.pip_proxy = options.proxy

        # Determine if we can prompt the user for authentication or not
        session.auth.prompting = not options.no_input
        session.auth.keyring_provider = options.keyring_provider

        return session


def _pip_self_version_check(session: "PipSession", options: Values) -> None:
    from pip._internal.self_outdated_check import pip_self_version_check as check

    check(session, options)


class IndexGroupCommand(Command, SessionCommandMixin):
    """
    Abstract base class for commands with the index_group options.

    This also corresponds to the commands that permit the pip version check.
    """

    def handle_pip_version_check(self, options: Values) -> None:
        """
        Do the pip version check if not disabled.

        This overrides the default behavior of not doing the check.
        """
        # Make sure the index_group options are present.
        assert hasattr(options, "no_index")

        if options.disable_pip_version_check or options.no_index:
            return

        try:
            # Otherwise, check if we're using the latest version of pip available.
            session = self._build_session(
                options,
                retries=0,
                timeout=min(5, options.timeout),
            )
            with session:
                _pip_self_version_check(session, options)
        except Exception:
            logger.warning("There was an error checking the latest version of pip.")
            logger.debug("See below for error", exc_info=True)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\savi.py ===
"""
    pygments.lexers.savi
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for Savi.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import Whitespace, Keyword, Name, String, Number, \
  Operator, Punctuation, Comment, Generic, Error

__all__ = ['SaviLexer']


# The canonical version of this file can be found in the following repository,
# where it is kept in sync with any language changes, as well as the other
# pygments-like lexers that are maintained for use with other tools:
# - https://github.com/savi-lang/savi/blob/main/tooling/pygments/lexers/savi.py
#
# If you're changing this file in the pygments repository, please ensure that
# any changes you make are also propagated to the official Savi repository,
# in order to avoid accidental clobbering of your changes later when an update
# from the Savi repository flows forward into the pygments repository.
#
# If you're changing this file in the Savi repository, please ensure that
# any changes you make are also reflected in the other pygments-like lexers
# (rouge, vscode, etc) so that all of the lexers can be kept cleanly in sync.

class SaviLexer(RegexLexer):
    """
    For Savi source code.

    .. versionadded: 2.10
    """

    name = 'Savi'
    url = 'https://github.com/savi-lang/savi'
    aliases = ['savi']
    filenames = ['*.savi']
    version_added = ''

    tokens = {
      "root": [
        # Line Comment
        (r'//.*?$', Comment.Single),

        # Doc Comment
        (r'::.*?$', Comment.Single),

        # Capability Operator
        (r'(\')(\w+)(?=[^\'])', bygroups(Operator, Name)),

        # Double-Quote String
        (r'\w?"', String.Double, "string.double"),

        # Single-Char String
        (r"'", String.Char, "string.char"),

        # Type Name
        (r'(_?[A-Z]\w*)', Name.Class),

        # Nested Type Name
        (r'(\.)(\s*)(_?[A-Z]\w*)', bygroups(Punctuation, Whitespace, Name.Class)),

        # Declare
        (r'^([ \t]*)(:\w+)',
          bygroups(Whitespace, Name.Tag),
          "decl"),

        # Error-Raising Calls/Names
        (r'((\w+|\+|\-|\*)\!)', Generic.Deleted),

        # Numeric Values
        (r'\b\d([\d_]*(\.[\d_]+)?)\b', Number),

        # Hex Numeric Values
        (r'\b0x([0-9a-fA-F_]+)\b', Number.Hex),

        # Binary Numeric Values
        (r'\b0b([01_]+)\b', Number.Bin),

        # Function Call (with braces)
        (r'\w+(?=\()', Name.Function),

        # Function Call (with receiver)
        (r'(\.)(\s*)(\w+)', bygroups(Punctuation, Whitespace, Name.Function)),

        # Function Call (with self receiver)
        (r'(@)(\w+)', bygroups(Punctuation, Name.Function)),

        # Parenthesis
        (r'\(', Punctuation, "root"),
        (r'\)', Punctuation, "#pop"),

        # Brace
        (r'\{', Punctuation, "root"),
        (r'\}', Punctuation, "#pop"),

        # Bracket
        (r'\[', Punctuation, "root"),
        (r'(\])(\!)', bygroups(Punctuation, Generic.Deleted), "#pop"),
        (r'\]', Punctuation, "#pop"),

        # Punctuation
        (r'[,;:\.@]', Punctuation),

        # Piping Operators
        (r'(\|\>)', Operator),

        # Branching Operators
        (r'(\&\&|\|\||\?\?|\&\?|\|\?|\.\?)', Operator),

        # Comparison Operators
        (r'(\<\=\>|\=\~|\=\=|\<\=|\>\=|\<|\>)', Operator),

        # Arithmetic Operators
        (r'(\+|\-|\/|\*|\%)', Operator),

        # Assignment Operators
        (r'(\=)', Operator),

        # Other Operators
        (r'(\!|\<\<|\<|\&|\|)', Operator),

        # Identifiers
        (r'\b\w+\b', Name),

        # Whitespace
        (r'[ \t\r]+\n*|\n+', Whitespace),
      ],

      # Declare (nested rules)
      "decl": [
        (r'\b[a-z_]\w*\b(?!\!)', Keyword.Declaration),
        (r':', Punctuation, "#pop"),
        (r'\n', Whitespace, "#pop"),
        include("root"),
      ],

      # Double-Quote String (nested rules)
      "string.double": [
        (r'\\\(', String.Interpol, "string.interpolation"),
        (r'\\u[0-9a-fA-F]{4}', String.Escape),
        (r'\\x[0-9a-fA-F]{2}', String.Escape),
        (r'\\[bfnrt\\\']', String.Escape),
        (r'\\"', String.Escape),
        (r'"', String.Double, "#pop"),
        (r'[^\\"]+', String.Double),
        (r'.', Error),
      ],

      # Single-Char String (nested rules)
      "string.char": [
        (r'\\u[0-9a-fA-F]{4}', String.Escape),
        (r'\\x[0-9a-fA-F]{2}', String.Escape),
        (r'\\[bfnrt\\\']', String.Escape),
        (r"\\'", String.Escape),
        (r"'", String.Char, "#pop"),
        (r"[^\\']+", String.Char),
        (r'.', Error),
      ],

      # Interpolation inside String (nested rules)
      "string.interpolation": [
        (r"\)", String.Interpol, "#pop"),
        include("root"),
      ]
    }

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\msgpack\ext.py ===
import datetime
import struct
from collections import namedtuple


class ExtType(namedtuple("ExtType", "code data")):
    """ExtType represents ext type in msgpack."""

    def __new__(cls, code, data):
        if not isinstance(code, int):
            raise TypeError("code must be int")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        if not 0 <= code <= 127:
            raise ValueError("code must be 0~127")
        return super().__new__(cls, code, data)


class Timestamp:
    """Timestamp represents the Timestamp extension type in msgpack.

    When built with Cython, msgpack uses C methods to pack and unpack `Timestamp`.
    When using pure-Python msgpack, :func:`to_bytes` and :func:`from_bytes` are used to pack and
    unpack `Timestamp`.

    This class is immutable: Do not override seconds and nanoseconds.
    """

    __slots__ = ["seconds", "nanoseconds"]

    def __init__(self, seconds, nanoseconds=0):
        """Initialize a Timestamp object.

        :param int seconds:
            Number of seconds since the UNIX epoch (00:00:00 UTC Jan 1 1970, minus leap seconds).
            May be negative.

        :param int nanoseconds:
            Number of nanoseconds to add to `seconds` to get fractional time.
            Maximum is 999_999_999.  Default is 0.

        Note: Negative times (before the UNIX epoch) are represented as neg. seconds + pos. ns.
        """
        if not isinstance(seconds, int):
            raise TypeError("seconds must be an integer")
        if not isinstance(nanoseconds, int):
            raise TypeError("nanoseconds must be an integer")
        if not (0 <= nanoseconds < 10**9):
            raise ValueError("nanoseconds must be a non-negative integer less than 999999999.")
        self.seconds = seconds
        self.nanoseconds = nanoseconds

    def __repr__(self):
        """String representation of Timestamp."""
        return f"Timestamp(seconds={self.seconds}, nanoseconds={self.nanoseconds})"

    def __eq__(self, other):
        """Check for equality with another Timestamp object"""
        if type(other) is self.__class__:
            return self.seconds == other.seconds and self.nanoseconds == other.nanoseconds
        return False

    def __ne__(self, other):
        """not-equals method (see :func:`__eq__()`)"""
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.seconds, self.nanoseconds))

    @staticmethod
    def from_bytes(b):
        """Unpack bytes into a `Timestamp` object.

        Used for pure-Python msgpack unpacking.

        :param b: Payload from msgpack ext message with code -1
        :type b: bytes

        :returns: Timestamp object unpacked from msgpack ext payload
        :rtype: Timestamp
        """
        if len(b) == 4:
            seconds = struct.unpack("!L", b)[0]
            nanoseconds = 0
        elif len(b) == 8:
            data64 = struct.unpack("!Q", b)[0]
            seconds = data64 & 0x00000003FFFFFFFF
            nanoseconds = data64 >> 34
        elif len(b) == 12:
            nanoseconds, seconds = struct.unpack("!Iq", b)
        else:
            raise ValueError(
                "Timestamp type can only be created from 32, 64, or 96-bit byte objects"
            )
        return Timestamp(seconds, nanoseconds)

    def to_bytes(self):
        """Pack this Timestamp object into bytes.

        Used for pure-Python msgpack packing.

        :returns data: Payload for EXT message with code -1 (timestamp type)
        :rtype: bytes
        """
        if (self.seconds >> 34) == 0:  # seconds is non-negative and fits in 34 bits
            data64 = self.nanoseconds << 34 | self.seconds
            if data64 & 0xFFFFFFFF00000000 == 0:
                # nanoseconds is zero and seconds < 2**32, so timestamp 32
                data = struct.pack("!L", data64)
            else:
                # timestamp 64
                data = struct.pack("!Q", data64)
        else:
            # timestamp 96
            data = struct.pack("!Iq", self.nanoseconds, self.seconds)
        return data

    @staticmethod
    def from_unix(unix_sec):
        """Create a Timestamp from posix timestamp in seconds.

        :param unix_float: Posix timestamp in seconds.
        :type unix_float: int or float
        """
        seconds = int(unix_sec // 1)
        nanoseconds = int((unix_sec % 1) * 10**9)
        return Timestamp(seconds, nanoseconds)

    def to_unix(self):
        """Get the timestamp as a floating-point value.

        :returns: posix timestamp
        :rtype: float
        """
        return self.seconds + self.nanoseconds / 1e9

    @staticmethod
    def from_unix_nano(unix_ns):
        """Create a Timestamp from posix timestamp in nanoseconds.

        :param int unix_ns: Posix timestamp in nanoseconds.
        :rtype: Timestamp
        """
        return Timestamp(*divmod(unix_ns, 10**9))

    def to_unix_nano(self):
        """Get the timestamp as a unixtime in nanoseconds.

        :returns: posix timestamp in nanoseconds
        :rtype: int
        """
        return self.seconds * 10**9 + self.nanoseconds

    def to_datetime(self):
        """Get the timestamp as a UTC datetime.

        :rtype: `datetime.datetime`
        """
        utc = datetime.timezone.utc
        return datetime.datetime.fromtimestamp(0, utc) + datetime.timedelta(
            seconds=self.seconds, microseconds=self.nanoseconds // 1000
        )

    @staticmethod
    def from_datetime(dt):
        """Create a Timestamp from datetime with tzinfo.

        :rtype: Timestamp
        """
        return Timestamp(seconds=int(dt.timestamp()), nanoseconds=dt.microsecond * 1000)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\resolvelib\structs.py ===
import itertools

from .compat import collections_abc


class DirectedGraph(object):
    """A graph structure with directed edges."""

    def __init__(self):
        self._vertices = set()
        self._forwards = {}  # <key> -> Set[<key>]
        self._backwards = {}  # <key> -> Set[<key>]

    def __iter__(self):
        return iter(self._vertices)

    def __len__(self):
        return len(self._vertices)

    def __contains__(self, key):
        return key in self._vertices

    def copy(self):
        """Return a shallow copy of this graph."""
        other = DirectedGraph()
        other._vertices = set(self._vertices)
        other._forwards = {k: set(v) for k, v in self._forwards.items()}
        other._backwards = {k: set(v) for k, v in self._backwards.items()}
        return other

    def add(self, key):
        """Add a new vertex to the graph."""
        if key in self._vertices:
            raise ValueError("vertex exists")
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key):
        """Remove a vertex from the graph, disconnecting all edges from/to it."""
        self._vertices.remove(key)
        for f in self._forwards.pop(key):
            self._backwards[f].remove(key)
        for t in self._backwards.pop(key):
            self._forwards[t].remove(key)

    def connected(self, f, t):
        return f in self._backwards[t] and t in self._forwards[f]

    def connect(self, f, t):
        """Connect two existing vertices.

        Nothing happens if the vertices are already connected.
        """
        if t not in self._vertices:
            raise KeyError(t)
        self._forwards[f].add(t)
        self._backwards[t].add(f)

    def iter_edges(self):
        for f, children in self._forwards.items():
            for t in children:
                yield f, t

    def iter_children(self, key):
        return iter(self._forwards[key])

    def iter_parents(self, key):
        return iter(self._backwards[key])


class IteratorMapping(collections_abc.Mapping):
    def __init__(self, mapping, accessor, appends=None):
        self._mapping = mapping
        self._accessor = accessor
        self._appends = appends or {}

    def __repr__(self):
        return "IteratorMapping({!r}, {!r}, {!r})".format(
            self._mapping,
            self._accessor,
            self._appends,
        )

    def __bool__(self):
        return bool(self._mapping or self._appends)

    __nonzero__ = __bool__  # XXX: Python 2.

    def __contains__(self, key):
        return key in self._mapping or key in self._appends

    def __getitem__(self, k):
        try:
            v = self._mapping[k]
        except KeyError:
            return iter(self._appends[k])
        return itertools.chain(self._accessor(v), self._appends.get(k, ()))

    def __iter__(self):
        more = (k for k in self._appends if k not in self._mapping)
        return itertools.chain(self._mapping, more)

    def __len__(self):
        more = sum(1 for k in self._appends if k not in self._mapping)
        return len(self._mapping) + more


class _FactoryIterableView(object):
    """Wrap an iterator factory returned by `find_matches()`.

    Calling `iter()` on this class would invoke the underlying iterator
    factory, making it a "collection with ordering" that can be iterated
    through multiple times, but lacks random access methods presented in
    built-in Python sequence types.
    """

    def __init__(self, factory):
        self._factory = factory
        self._iterable = None

    def __repr__(self):
        return "{}({})".format(type(self).__name__, list(self))

    def __bool__(self):
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    __nonzero__ = __bool__  # XXX: Python 2.

    def __iter__(self):
        iterable = (
            self._factory() if self._iterable is None else self._iterable
        )
        self._iterable, current = itertools.tee(iterable)
        return current


class _SequenceIterableView(object):
    """Wrap an iterable returned by find_matches().

    This is essentially just a proxy to the underlying sequence that provides
    the same interface as `_FactoryIterableView`.
    """

    def __init__(self, sequence):
        self._sequence = sequence

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self._sequence)

    def __bool__(self):
        return bool(self._sequence)

    __nonzero__ = __bool__  # XXX: Python 2.

    def __iter__(self):
        return iter(self._sequence)


def build_iter_view(matches):
    """Build an iterable view from the value returned by `find_matches()`."""
    if callable(matches):
        return _FactoryIterableView(matches)
    if not isinstance(matches, collections_abc.Sequence):
        matches = list(matches)
    return _SequenceIterableView(matches)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\groff.py ===
"""
    pygments.formatters.groff
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for groff output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import math
from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_bool_opt, get_int_opt

__all__ = ['GroffFormatter']


class GroffFormatter(Formatter):
    """
    Format tokens with groff escapes to change their color and font style.

    .. versionadded:: 2.11

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `monospaced`
        If set to true, monospace font will be used (default: ``true``).

    `linenos`
        If set to true, print the line numbers (default: ``false``).

    `wrap`
        Wrap lines to the specified number of characters. Disabled if set to 0
        (default: ``0``).
    """

    name = 'groff'
    aliases = ['groff','troff','roff']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.monospaced = get_bool_opt(options, 'monospaced', True)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self._lineno = 0
        self.wrap = get_int_opt(options, 'wrap', 0)
        self._linelen = 0

        self.styles = {}
        self._make_styles()


    def _make_styles(self):
        regular = '\\f[CR]' if self.monospaced else '\\f[R]'
        bold = '\\f[CB]' if self.monospaced else '\\f[B]'
        italic = '\\f[CI]' if self.monospaced else '\\f[I]'

        for ttype, ndef in self.style:
            start = end = ''
            if ndef['color']:
                start += '\\m[{}]'.format(ndef['color'])
                end = '\\m[]' + end
            if ndef['bold']:
                start += bold
                end = regular + end
            if ndef['italic']:
                start += italic
                end = regular + end
            if ndef['bgcolor']:
                start += '\\M[{}]'.format(ndef['bgcolor'])
                end = '\\M[]' + end

            self.styles[ttype] = start, end


    def _define_colors(self, outfile):
        colors = set()
        for _, ndef in self.style:
            if ndef['color'] is not None:
                colors.add(ndef['color'])

        for color in sorted(colors):
            outfile.write('.defcolor ' + color + ' rgb #' + color + '\n')


    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s% 4d " % (self._lineno != 1 and '\n' or '', self._lineno))


    def _wrap_line(self, line):
        length = len(line.rstrip('\n'))
        space = '     ' if self.linenos else ''
        newline = ''

        if length > self.wrap:
            for i in range(0, math.floor(length / self.wrap)):
                chunk = line[i*self.wrap:i*self.wrap+self.wrap]
                newline += (chunk + '\n' + space)
            remainder = length % self.wrap
            if remainder > 0:
                newline += line[-remainder-1:]
                self._linelen = remainder
        elif self._linelen + length > self.wrap:
            newline = ('\n' + space) + line
            self._linelen = length
        else:
            newline = line
            self._linelen += length

        return newline


    def _escape_chars(self, text):
        text = text.replace('\\', '\\[u005C]'). \
                    replace('.', '\\[char46]'). \
                    replace('\'', '\\[u0027]'). \
                    replace('`', '\\[u0060]'). \
                    replace('~', '\\[u007E]')
        copy = text

        for char in copy:
            if len(char) != len(char.encode()):
                uni = char.encode('unicode_escape') \
                    .decode()[1:] \
                    .replace('x', 'u00') \
                    .upper()
                text = text.replace(char, '\\[u' + uni[1:] + ']')

        return text


    def format_unencoded(self, tokensource, outfile):
        self._define_colors(outfile)

        outfile.write('.nf\n\\f[CR]\n')

        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            start, end = self.styles[ttype]

            for line in value.splitlines(True):
                if self.wrap > 0:
                    line = self._wrap_line(line)

                if start and end:
                    text = self._escape_chars(line.rstrip('\n'))
                    if text != '':
                        outfile.write(''.join((start, text, end)))
                else:
                    outfile.write(self._escape_chars(line.rstrip('\n')))

                if line.endswith('\n'):
                    if self.linenos:
                        self._write_lineno(outfile)
                        self._linelen = 0
                    else:
                        outfile.write('\n')
                        self._linelen = 0

        outfile.write('\n.fi')

# === NexusCore/openenv\Lib\site-packages\numpy\__config__.py ===
# This file is generated by numpy's build process
# It contains system_info results at the time of building this package.
from enum import Enum
from numpy._core._multiarray_umath import (
    __cpu_features__,
    __cpu_baseline__,
    __cpu_dispatch__,
)

__all__ = ["show_config"]
_built_with_meson = True


class DisplayModes(Enum):
    stdout = "stdout"
    dicts = "dicts"


def _cleanup(d):
    """
    Removes empty values in a `dict` recursively
    This ensures we remove values that Meson could not provide to CONFIG
    """
    if isinstance(d, dict):
        return {k: _cleanup(v) for k, v in d.items() if v and _cleanup(v)}
    else:
        return d


CONFIG = _cleanup(
    {
        "Compilers": {
            "c": {
                "name": "msvc",
                "linker": r"link",
                "version": "19.43.34808",
                "commands": r"cl",
                "args": r"",
                "linker args": r"",
            },
            "cython": {
                "name": "cython",
                "linker": r"cython",
                "version": "3.1.2",
                "commands": r"cython",
                "args": r"",
                "linker args": r"",
            },
            "c++": {
                "name": "msvc",
                "linker": r"link",
                "version": "19.43.34808",
                "commands": r"cl",
                "args": r"",
                "linker args": r"",
            },
        },
        "Machine Information": {
            "host": {
                "cpu": "x86_64",
                "family": "x86_64",
                "endian": "little",
                "system": "windows",
            },
            "build": {
                "cpu": "x86_64",
                "family": "x86_64",
                "endian": "little",
                "system": "windows",
            },
            "cross-compiled": bool("False".lower().replace("false", "")),
        },
        "Build Dependencies": {
            "blas": {
                "name": "scipy-openblas",
                "found": bool("True".lower().replace("false", "")),
                "version": "0.3.29",
                "detection method": "pkgconfig",
                "include directory": r"C:/Users/runneradmin/AppData/Local/Temp/cibw-run-3haj0lk8/cp312-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/include",
                "lib directory": r"C:/Users/runneradmin/AppData/Local/Temp/cibw-run-3haj0lk8/cp312-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/lib",
                "openblas configuration": r"OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY Haswell MAX_THREADS=24",
                "pc file directory": r"D:/a/numpy/numpy/.openblas",
            },
            "lapack": {
                "name": "scipy-openblas",
                "found": bool("True".lower().replace("false", "")),
                "version": "0.3.29",
                "detection method": "pkgconfig",
                "include directory": r"C:/Users/runneradmin/AppData/Local/Temp/cibw-run-3haj0lk8/cp312-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/include",
                "lib directory": r"C:/Users/runneradmin/AppData/Local/Temp/cibw-run-3haj0lk8/cp312-win_amd64/build/venv/Lib/site-packages/scipy_openblas64/lib",
                "openblas configuration": r"OpenBLAS 0.3.29  USE64BITINT DYNAMIC_ARCH NO_AFFINITY Haswell MAX_THREADS=24",
                "pc file directory": r"D:/a/numpy/numpy/.openblas",
            },
        },
        "Python Information": {
            "path": r"C:\Users\runneradmin\AppData\Local\Temp\build-env-wvw460pp\Scripts\python.exe",
            "version": "3.12",
        },
        "SIMD Extensions": {
            "baseline": __cpu_baseline__,
            "found": [
                feature for feature in __cpu_dispatch__ if __cpu_features__[feature]
            ],
            "not found": [
                feature for feature in __cpu_dispatch__ if not __cpu_features__[feature]
            ],
        },
    }
)


def _check_pyyaml():
    import yaml

    return yaml


def show(mode=DisplayModes.stdout.value):
    """
    Show libraries and system information on which NumPy was built
    and is being used

    Parameters
    ----------
    mode : {`'stdout'`, `'dicts'`}, optional.
        Indicates how to display the config information.
        `'stdout'` prints to console, `'dicts'` returns a dictionary
        of the configuration.

    Returns
    -------
    out : {`dict`, `None`}
        If mode is `'dicts'`, a dict is returned, else None

    See Also
    --------
    get_include : Returns the directory containing NumPy C
                  header files.

    Notes
    -----
    1. The `'stdout'` mode will give more readable
       output if ``pyyaml`` is installed

    """
    if mode == DisplayModes.stdout.value:
        try:  # Non-standard library, check import
            yaml = _check_pyyaml()

            print(yaml.dump(CONFIG))
        except ModuleNotFoundError:
            import warnings
            import json

            warnings.warn("Install `pyyaml` for better output", stacklevel=1)
            print(json.dumps(CONFIG, indent=2))
    elif mode == DisplayModes.dicts.value:
        return CONFIG
    else:
        raise AttributeError(
            f"Invalid `mode`, use one of: {', '.join([e.value for e in DisplayModes])}"
        )


def show_config(mode=DisplayModes.stdout.value):
    return show(mode)


show_config.__doc__ = show.__doc__
show_config.__module__ = "numpy"

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\classifyTools.py ===
""" fontTools.misc.classifyTools.py -- tools for classifying things.
"""


class Classifier(object):
    """
    Main Classifier object, used to classify things into similar sets.
    """

    def __init__(self, sort=True):
        self._things = set()  # set of all things known so far
        self._sets = []  # list of class sets produced so far
        self._mapping = {}  # map from things to their class set
        self._dirty = False
        self._sort = sort

    def add(self, set_of_things):
        """
        Add a set to the classifier.  Any iterable is accepted.
        """
        if not set_of_things:
            return

        self._dirty = True

        things, sets, mapping = self._things, self._sets, self._mapping

        s = set(set_of_things)
        intersection = s.intersection(things)  # existing things
        s.difference_update(intersection)  # new things
        difference = s
        del s

        # Add new class for new things
        if difference:
            things.update(difference)
            sets.append(difference)
            for thing in difference:
                mapping[thing] = difference
        del difference

        while intersection:
            # Take one item and process the old class it belongs to
            old_class = mapping[next(iter(intersection))]
            old_class_intersection = old_class.intersection(intersection)

            # Update old class to remove items from new set
            old_class.difference_update(old_class_intersection)

            # Remove processed items from todo list
            intersection.difference_update(old_class_intersection)

            # Add new class for the intersection with old class
            sets.append(old_class_intersection)
            for thing in old_class_intersection:
                mapping[thing] = old_class_intersection
            del old_class_intersection

    def update(self, list_of_sets):
        """
        Add a a list of sets to the classifier.  Any iterable of iterables is accepted.
        """
        for s in list_of_sets:
            self.add(s)

    def _process(self):
        if not self._dirty:
            return

        # Do any deferred processing
        sets = self._sets
        self._sets = [s for s in sets if s]

        if self._sort:
            self._sets = sorted(self._sets, key=lambda s: (-len(s), sorted(s)))

        self._dirty = False

    # Output methods

    def getThings(self):
        """Returns the set of all things known so far.

        The return value belongs to the Classifier object and should NOT
        be modified while the classifier is still in use.
        """
        self._process()
        return self._things

    def getMapping(self):
        """Returns the mapping from things to their class set.

        The return value belongs to the Classifier object and should NOT
        be modified while the classifier is still in use.
        """
        self._process()
        return self._mapping

    def getClasses(self):
        """Returns the list of class sets.

        The return value belongs to the Classifier object and should NOT
        be modified while the classifier is still in use.
        """
        self._process()
        return self._sets


def classify(list_of_sets, sort=True):
    """
    Takes a iterable of iterables (list of sets from here on; but any
    iterable works.), and returns the smallest list of sets such that
    each set, is either a subset, or is disjoint from, each of the input
    sets.

    In other words, this function classifies all the things present in
    any of the input sets, into similar classes, based on which sets
    things are a member of.

    If sort=True, return class sets are sorted by decreasing size and
    their natural sort order within each class size.  Otherwise, class
    sets are returned in the order that they were identified, which is
    generally not significant.

    >>> classify([]) == ([], {})
    True
    >>> classify([[]]) == ([], {})
    True
    >>> classify([[], []]) == ([], {})
    True
    >>> classify([[1]]) == ([{1}], {1: {1}})
    True
    >>> classify([[1,2]]) == ([{1, 2}], {1: {1, 2}, 2: {1, 2}})
    True
    >>> classify([[1],[2]]) == ([{1}, {2}], {1: {1}, 2: {2}})
    True
    >>> classify([[1,2],[2]]) == ([{1}, {2}], {1: {1}, 2: {2}})
    True
    >>> classify([[1,2],[2,4]]) == ([{1}, {2}, {4}], {1: {1}, 2: {2}, 4: {4}})
    True
    >>> classify([[1,2],[2,4,5]]) == (
    ...     [{4, 5}, {1}, {2}], {1: {1}, 2: {2}, 4: {4, 5}, 5: {4, 5}})
    True
    >>> classify([[1,2],[2,4,5]], sort=False) == (
    ...     [{1}, {4, 5}, {2}], {1: {1}, 2: {2}, 4: {4, 5}, 5: {4, 5}})
    True
    >>> classify([[1,2,9],[2,4,5]], sort=False) == (
    ...     [{1, 9}, {4, 5}, {2}], {1: {1, 9}, 2: {2}, 4: {4, 5}, 5: {4, 5},
    ...     9: {1, 9}})
    True
    >>> classify([[1,2,9,15],[2,4,5]], sort=False) == (
    ...     [{1, 9, 15}, {4, 5}, {2}], {1: {1, 9, 15}, 2: {2}, 4: {4, 5},
    ...     5: {4, 5}, 9: {1, 9, 15}, 15: {1, 9, 15}})
    True
    >>> classes, mapping = classify([[1,2,9,15],[2,4,5],[15,5]], sort=False)
    >>> set([frozenset(c) for c in classes]) == set(
    ...     [frozenset(s) for s in ({1, 9}, {4}, {2}, {5}, {15})])
    True
    >>> mapping == {1: {1, 9}, 2: {2}, 4: {4}, 5: {5}, 9: {1, 9}, 15: {15}}
    True
    """
    classifier = Classifier(sort=sort)
    classifier.update(list_of_sets)
    return classifier.getClasses(), classifier.getMapping()


if __name__ == "__main__":
    import sys, doctest

    sys.exit(doctest.testmod(optionflags=doctest.ELLIPSIS).failed)

# === NexusCore/openenv\Lib\site-packages\IPython\utils\capture.py ===
# encoding: utf-8
"""IO capturing utilities."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import sys
from io import StringIO

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------


class RichOutput:
    def __init__(self, data=None, metadata=None, transient=None, update=False):
        self.data = data or {}
        self.metadata = metadata or {}
        self.transient = transient or {}
        self.update = update

    def display(self):
        from IPython.display import publish_display_data
        publish_display_data(data=self.data, metadata=self.metadata,
                             transient=self.transient, update=self.update)

    def _repr_mime_(self, mime):
        if mime not in self.data:
            return
        data = self.data[mime]
        if mime in self.metadata:
            return data, self.metadata[mime]
        else:
            return data

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self.data, self.metadata

    def _repr_html_(self):
        return self._repr_mime_("text/html")

    def _repr_latex_(self):
        return self._repr_mime_("text/latex")

    def _repr_json_(self):
        return self._repr_mime_("application/json")

    def _repr_javascript_(self):
        return self._repr_mime_("application/javascript")

    def _repr_png_(self):
        return self._repr_mime_("image/png")

    def _repr_jpeg_(self):
        return self._repr_mime_("image/jpeg")

    def _repr_svg_(self):
        return self._repr_mime_("image/svg+xml")


class CapturedIO:
    """Simple object for containing captured stdout/err and rich display StringIO objects

    Each instance `c` has three attributes:

    - ``c.stdout`` : standard output as a string
    - ``c.stderr`` : standard error as a string
    - ``c.outputs``: a list of rich display outputs

    Additionally, there's a ``c.show()`` method which will print all of the
    above in the same order, and can be invoked simply via ``c()``.
    """

    def __init__(self, stdout, stderr, outputs=None):
        self._stdout = stdout
        self._stderr = stderr
        if outputs is None:
            outputs = []
        self._outputs = outputs

    def __str__(self):
        return self.stdout

    @property
    def stdout(self):
        "Captured standard output"
        if not self._stdout:
            return ''
        return self._stdout.getvalue()

    @property
    def stderr(self):
        "Captured standard error"
        if not self._stderr:
            return ''
        return self._stderr.getvalue()

    @property
    def outputs(self):
        """A list of the captured rich display outputs, if any.

        If you have a CapturedIO object ``c``, these can be displayed in IPython
        using::

            from IPython.display import display
            for o in c.outputs:
                display(o)
        """
        return [ RichOutput(**kargs) for kargs in self._outputs ]

    def show(self):
        """write my output to sys.stdout/err as appropriate"""
        sys.stdout.write(self.stdout)
        sys.stderr.write(self.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        for kargs in self._outputs:
            RichOutput(**kargs).display()

    __call__ = show


class capture_output:
    """context manager for capturing stdout/err"""
    stdout = True
    stderr = True
    display = True

    def __init__(self, stdout=True, stderr=True, display=True):
        self.stdout = stdout
        self.stderr = stderr
        self.display = display
        self.shell = None

    def __enter__(self):
        from IPython.core.getipython import get_ipython
        from IPython.core.displaypub import CapturingDisplayPublisher
        from IPython.core.displayhook import CapturingDisplayHook

        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

        if self.display:
            self.shell = get_ipython()
            if self.shell is None:
                self.save_display_pub = None
                self.display = False

        stdout = stderr = outputs = None
        if self.stdout:
            stdout = sys.stdout = StringIO()
        if self.stderr:
            stderr = sys.stderr = StringIO()
        if self.display:
            self.save_display_pub = self.shell.display_pub
            self.shell.display_pub = CapturingDisplayPublisher()
            outputs = self.shell.display_pub.outputs
            self.save_display_hook = sys.displayhook
            sys.displayhook = CapturingDisplayHook(shell=self.shell,
                                                   outputs=outputs)

        return CapturedIO(stdout, stderr, outputs)

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr
        if self.display and self.shell:
            self.shell.display_pub = self.save_display_pub
            sys.displayhook = self.save_display_hook

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\cooldown_cache.py ===
"""
Wrapper around router cache. Meant to handle model cooldown logic
"""

import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, TypedDict, Union

from litellm import verbose_logger
from litellm.caching.caching import DualCache
from litellm.caching.in_memory_cache import InMemoryCache

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class CooldownCacheValue(TypedDict):
    exception_received: str
    status_code: str
    timestamp: float
    cooldown_time: float


class CooldownCache:
    def __init__(self, cache: DualCache, default_cooldown_time: float):
        self.cache = cache
        self.default_cooldown_time = default_cooldown_time
        self.in_memory_cache = InMemoryCache()

    def _common_add_cooldown_logic(
        self, model_id: str, original_exception, exception_status, cooldown_time: float
    ) -> Tuple[str, CooldownCacheValue]:
        try:
            current_time = time.time()
            cooldown_key = f"deployment:{model_id}:cooldown"

            # Store the cooldown information for the deployment separately
            cooldown_data = CooldownCacheValue(
                exception_received=str(original_exception),
                status_code=str(exception_status),
                timestamp=current_time,
                cooldown_time=cooldown_time,
            )

            return cooldown_key, cooldown_data
        except Exception as e:
            verbose_logger.error(
                "CooldownCache::_common_add_cooldown_logic - Exception occurred - {}".format(
                    str(e)
                )
            )
            raise e

    def add_deployment_to_cooldown(
        self,
        model_id: str,
        original_exception: Exception,
        exception_status: int,
        cooldown_time: Optional[float],
    ):
        try:
            _cooldown_time = cooldown_time or self.default_cooldown_time
            cooldown_key, cooldown_data = self._common_add_cooldown_logic(
                model_id=model_id,
                original_exception=original_exception,
                exception_status=exception_status,
                cooldown_time=_cooldown_time,
            )

            # Set the cache with a TTL equal to the cooldown time
            self.cache.set_cache(
                value=cooldown_data,
                key=cooldown_key,
                ttl=_cooldown_time,
            )
        except Exception as e:
            verbose_logger.error(
                "CooldownCache::add_deployment_to_cooldown - Exception occurred - {}".format(
                    str(e)
                )
            )
            raise e

    @staticmethod
    def get_cooldown_cache_key(model_id: str) -> str:
        return f"deployment:{model_id}:cooldown"

    async def async_get_active_cooldowns(
        self, model_ids: List[str], parent_otel_span: Optional[Span]
    ) -> List[Tuple[str, CooldownCacheValue]]:
        # Generate the keys for the deployments
        keys = [
            CooldownCache.get_cooldown_cache_key(model_id) for model_id in model_ids
        ]

        # Retrieve the values for the keys using mget
        ## more likely to be none if no models ratelimited. So just check redis every 1s
        ## each redis call adds ~100ms latency.

        ## check in memory cache first
        results = await self.cache.async_batch_get_cache(
            keys=keys, parent_otel_span=parent_otel_span
        )
        active_cooldowns: List[Tuple[str, CooldownCacheValue]] = []

        if results is None:
            return active_cooldowns

        # Process the results
        for model_id, result in zip(model_ids, results):
            if result and isinstance(result, dict):
                cooldown_cache_value = CooldownCacheValue(**result)  # type: ignore
                active_cooldowns.append((model_id, cooldown_cache_value))

        return active_cooldowns

    def get_active_cooldowns(
        self, model_ids: List[str], parent_otel_span: Optional[Span]
    ) -> List[Tuple[str, CooldownCacheValue]]:
        # Generate the keys for the deployments
        keys = [f"deployment:{model_id}:cooldown" for model_id in model_ids]
        # Retrieve the values for the keys using mget
        results = (
            self.cache.batch_get_cache(keys=keys, parent_otel_span=parent_otel_span)
            or []
        )

        active_cooldowns = []
        # Process the results
        for model_id, result in zip(model_ids, results):
            if result and isinstance(result, dict):
                cooldown_cache_value = CooldownCacheValue(**result)  # type: ignore
                active_cooldowns.append((model_id, cooldown_cache_value))

        return active_cooldowns

    def get_min_cooldown(
        self, model_ids: List[str], parent_otel_span: Optional[Span]
    ) -> float:
        """Return min cooldown time required for a group of model id's."""

        # Generate the keys for the deployments
        keys = [f"deployment:{model_id}:cooldown" for model_id in model_ids]

        # Retrieve the values for the keys using mget
        results = (
            self.cache.batch_get_cache(keys=keys, parent_otel_span=parent_otel_span)
            or []
        )

        min_cooldown_time: Optional[float] = None
        # Process the results
        for model_id, result in zip(model_ids, results):
            if result and isinstance(result, dict):
                cooldown_cache_value = CooldownCacheValue(**result)  # type: ignore
                if min_cooldown_time is None:
                    min_cooldown_time = cooldown_cache_value["cooldown_time"]
                elif cooldown_cache_value["cooldown_time"] < min_cooldown_time:
                    min_cooldown_time = cooldown_cache_value["cooldown_time"]

        return min_cooldown_time or self.default_cooldown_time


# Usage example:
# cooldown_cache = CooldownCache(cache=your_cache_instance, cooldown_time=your_cooldown_time)
# cooldown_cache.add_deployment_to_cooldown(deployment, original_exception, exception_status)
# active_cooldowns = cooldown_cache.get_active_cooldowns()

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\langfuse\langfuse_handler.py ===
"""
This file contains the LangFuseHandler class

Used to get the LangFuseLogger for a given request

Handles Key/Team Based Langfuse Logging
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from litellm.litellm_core_utils.litellm_logging import StandardCallbackDynamicParams

from .langfuse import LangFuseLogger, LangfuseLoggingConfig

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import DynamicLoggingCache
else:
    DynamicLoggingCache = Any


class LangFuseHandler:
    @staticmethod
    def get_langfuse_logger_for_request(
        standard_callback_dynamic_params: StandardCallbackDynamicParams,
        in_memory_dynamic_logger_cache: DynamicLoggingCache,
        globalLangfuseLogger: Optional[LangFuseLogger] = None,
    ) -> LangFuseLogger:
        """
        This function is used to get the LangFuseLogger for a given request

        1. If dynamic credentials are passed
            - check if a LangFuseLogger is cached for the dynamic credentials
            - if cached LangFuseLogger is not found, create a new LangFuseLogger and cache it

        2. If dynamic credentials are not passed return the globalLangfuseLogger

        """
        temp_langfuse_logger: Optional[LangFuseLogger] = globalLangfuseLogger
        if (
            LangFuseHandler._dynamic_langfuse_credentials_are_passed(
                standard_callback_dynamic_params
            )
            is False
        ):
            return LangFuseHandler._return_global_langfuse_logger(
                globalLangfuseLogger=globalLangfuseLogger,
                in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
            )

        # get langfuse logging config to use for this request, based on standard_callback_dynamic_params
        _credentials = LangFuseHandler.get_dynamic_langfuse_logging_config(
            globalLangfuseLogger=globalLangfuseLogger,
            standard_callback_dynamic_params=standard_callback_dynamic_params,
        )
        credentials_dict = dict(_credentials)

        # check if langfuse logger is already cached
        temp_langfuse_logger = in_memory_dynamic_logger_cache.get_cache(
            credentials=credentials_dict, service_name="langfuse"
        )

        # if not cached, create a new langfuse logger and cache it
        if temp_langfuse_logger is None:
            temp_langfuse_logger = (
                LangFuseHandler._create_langfuse_logger_from_credentials(
                    credentials=credentials_dict,
                    in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
                )
            )

        return temp_langfuse_logger

    @staticmethod
    def _return_global_langfuse_logger(
        globalLangfuseLogger: Optional[LangFuseLogger],
        in_memory_dynamic_logger_cache: DynamicLoggingCache,
    ) -> LangFuseLogger:
        """
        Returns the Global LangfuseLogger set on litellm

        (this is the default langfuse logger - used when no dynamic credentials are passed)

        If no Global LangfuseLogger is set, it will check in_memory_dynamic_logger_cache for a cached LangFuseLogger
        This function is used to return the globalLangfuseLogger if it exists, otherwise it will check in_memory_dynamic_logger_cache for a cached LangFuseLogger
        """
        if globalLangfuseLogger is not None:
            return globalLangfuseLogger

        credentials_dict: Dict[
            str, Any
        ] = (
            {}
        )  # the global langfuse logger uses Environment Variables, there are no dynamic credentials
        globalLangfuseLogger = in_memory_dynamic_logger_cache.get_cache(
            credentials=credentials_dict,
            service_name="langfuse",
        )
        if globalLangfuseLogger is None:
            globalLangfuseLogger = (
                LangFuseHandler._create_langfuse_logger_from_credentials(
                    credentials=credentials_dict,
                    in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
                )
            )
        return globalLangfuseLogger

    @staticmethod
    def _create_langfuse_logger_from_credentials(
        credentials: Dict,
        in_memory_dynamic_logger_cache: DynamicLoggingCache,
    ) -> LangFuseLogger:
        """
        This function is used to
        1. create a LangFuseLogger from the credentials
        2. cache the LangFuseLogger to prevent re-creating it for the same credentials
        """

        langfuse_logger = LangFuseLogger(
            langfuse_public_key=credentials.get("langfuse_public_key"),
            langfuse_secret=credentials.get("langfuse_secret"),
            langfuse_host=credentials.get("langfuse_host"),
        )
        in_memory_dynamic_logger_cache.set_cache(
            credentials=credentials,
            service_name="langfuse",
            logging_obj=langfuse_logger,
        )
        return langfuse_logger

    @staticmethod
    def get_dynamic_langfuse_logging_config(
        standard_callback_dynamic_params: StandardCallbackDynamicParams,
        globalLangfuseLogger: Optional[LangFuseLogger] = None,
    ) -> LangfuseLoggingConfig:
        """
        This function is used to get the Langfuse logging config to use for a given request.

        It checks if the dynamic parameters are provided in the standard_callback_dynamic_params and uses them to get the Langfuse logging config.

        If no dynamic parameters are provided, it uses the `globalLangfuseLogger` values
        """
        # only use dynamic params if langfuse credentials are passed dynamically
        return LangfuseLoggingConfig(
            langfuse_secret=standard_callback_dynamic_params.get("langfuse_secret")
            or standard_callback_dynamic_params.get("langfuse_secret_key"),
            langfuse_public_key=standard_callback_dynamic_params.get(
                "langfuse_public_key"
            ),
            langfuse_host=standard_callback_dynamic_params.get("langfuse_host"),
        )

    @staticmethod
    def _dynamic_langfuse_credentials_are_passed(
        standard_callback_dynamic_params: StandardCallbackDynamicParams,
    ) -> bool:
        """
        This function is used to check if the dynamic langfuse credentials are passed in standard_callback_dynamic_params

        Returns:
            bool: True if the dynamic langfuse credentials are passed, False otherwise
        """

        if (
            standard_callback_dynamic_params.get("langfuse_host") is not None
            or standard_callback_dynamic_params.get("langfuse_public_key") is not None
            or standard_callback_dynamic_params.get("langfuse_secret") is not None
            or standard_callback_dynamic_params.get("langfuse_secret_key") is not None
        ):
            return True
        return False

# === NexusCore/openenv\Lib\site-packages\nltk\cluster\gaac.py ===
# Natural Language Toolkit: Group Average Agglomerative Clusterer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

try:
    import numpy
except ImportError:
    pass

from nltk.cluster.util import Dendrogram, VectorSpaceClusterer, cosine_distance


class GAAClusterer(VectorSpaceClusterer):
    """
    The Group Average Agglomerative starts with each of the N vectors as singleton
    clusters. It then iteratively merges pairs of clusters which have the
    closest centroids.  This continues until there is only one cluster. The
    order of merges gives rise to a dendrogram: a tree with the earlier merges
    lower than later merges. The membership of a given number of clusters c, 1
    <= c <= N, can be found by cutting the dendrogram at depth c.

    This clusterer uses the cosine similarity metric only, which allows for
    efficient speed-up in the clustering process.
    """

    def __init__(self, num_clusters=1, normalise=True, svd_dimensions=None):
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._num_clusters = num_clusters
        self._dendrogram = None
        self._groups_values = None

    def cluster(self, vectors, assign_clusters=False, trace=False):
        # stores the merge order
        self._dendrogram = Dendrogram(
            [numpy.array(vector, numpy.float64) for vector in vectors]
        )
        return VectorSpaceClusterer.cluster(self, vectors, assign_clusters, trace)

    def cluster_vectorspace(self, vectors, trace=False):
        # variables describing the initial situation
        N = len(vectors)
        cluster_len = [1] * N
        cluster_count = N
        index_map = numpy.arange(N)

        # construct the similarity matrix
        dims = (N, N)
        dist = numpy.ones(dims, dtype=float) * numpy.inf
        for i in range(N):
            for j in range(i + 1, N):
                dist[i, j] = cosine_distance(vectors[i], vectors[j])

        while cluster_count > max(self._num_clusters, 1):
            i, j = numpy.unravel_index(dist.argmin(), dims)
            if trace:
                print("merging %d and %d" % (i, j))

            # update similarities for merging i and j
            self._merge_similarities(dist, cluster_len, i, j)

            # remove j
            dist[:, j] = numpy.inf
            dist[j, :] = numpy.inf

            # merge the clusters
            cluster_len[i] = cluster_len[i] + cluster_len[j]
            self._dendrogram.merge(index_map[i], index_map[j])
            cluster_count -= 1

            # update the index map to reflect the indexes if we
            # had removed j
            index_map[j + 1 :] -= 1
            index_map[j] = N

        self.update_clusters(self._num_clusters)

    def _merge_similarities(self, dist, cluster_len, i, j):
        # the new cluster i merged from i and j adopts the average of
        # i and j's similarity to each other cluster, weighted by the
        # number of points in the clusters i and j
        i_weight = cluster_len[i]
        j_weight = cluster_len[j]
        weight_sum = i_weight + j_weight

        # update for x<i
        dist[:i, i] = dist[:i, i] * i_weight + dist[:i, j] * j_weight
        dist[:i, i] /= weight_sum
        # update for i<x<j
        dist[i, i + 1 : j] = (
            dist[i, i + 1 : j] * i_weight + dist[i + 1 : j, j] * j_weight
        )
        # update for i<j<x
        dist[i, j + 1 :] = dist[i, j + 1 :] * i_weight + dist[j, j + 1 :] * j_weight
        dist[i, i + 1 :] /= weight_sum

    def update_clusters(self, num_clusters):
        clusters = self._dendrogram.groups(num_clusters)
        self._centroids = []
        for cluster in clusters:
            assert len(cluster) > 0
            if self._should_normalise:
                centroid = self._normalise(cluster[0])
            else:
                centroid = numpy.array(cluster[0])
            for vector in cluster[1:]:
                if self._should_normalise:
                    centroid += self._normalise(vector)
                else:
                    centroid += vector
            centroid /= len(cluster)
            self._centroids.append(centroid)
        self._num_clusters = len(self._centroids)

    def classify_vectorspace(self, vector):
        best = None
        for i in range(self._num_clusters):
            centroid = self._centroids[i]
            dist = cosine_distance(vector, centroid)
            if not best or dist < best[0]:
                best = (dist, i)
        return best[1]

    def dendrogram(self):
        """
        :return: The dendrogram representing the current clustering
        :rtype:  Dendrogram
        """
        return self._dendrogram

    def num_clusters(self):
        return self._num_clusters

    def __repr__(self):
        return "<GroupAverageAgglomerative Clusterer n=%d>" % self._num_clusters


def demo():
    """
    Non-interactive demonstration of the clusterers with simple 2-D data.
    """

    from nltk.cluster import GAAClusterer

    # use a set of tokens with 2D indices
    vectors = [numpy.array(f) for f in [[3, 3], [1, 2], [4, 2], [4, 0], [2, 3], [3, 1]]]

    # test the GAAC clusterer with 4 clusters
    clusterer = GAAClusterer(4)
    clusters = clusterer.cluster(vectors, True)

    print("Clusterer:", clusterer)
    print("Clustered:", vectors)
    print("As:", clusters)
    print()

    # show the dendrogram
    clusterer.dendrogram().show()

    # classify a new vector
    vector = numpy.array([3, 3])
    print("classify(%s):" % vector, end=" ")
    print(clusterer.classify(vector))
    print()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\msgpack\ext.py ===
import datetime
import struct
from collections import namedtuple


class ExtType(namedtuple("ExtType", "code data")):
    """ExtType represents ext type in msgpack."""

    def __new__(cls, code, data):
        if not isinstance(code, int):
            raise TypeError("code must be int")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        if not 0 <= code <= 127:
            raise ValueError("code must be 0~127")
        return super().__new__(cls, code, data)


class Timestamp:
    """Timestamp represents the Timestamp extension type in msgpack.

    When built with Cython, msgpack uses C methods to pack and unpack `Timestamp`.
    When using pure-Python msgpack, :func:`to_bytes` and :func:`from_bytes` are used to pack and
    unpack `Timestamp`.

    This class is immutable: Do not override seconds and nanoseconds.
    """

    __slots__ = ["seconds", "nanoseconds"]

    def __init__(self, seconds, nanoseconds=0):
        """Initialize a Timestamp object.

        :param int seconds:
            Number of seconds since the UNIX epoch (00:00:00 UTC Jan 1 1970, minus leap seconds).
            May be negative.

        :param int nanoseconds:
            Number of nanoseconds to add to `seconds` to get fractional time.
            Maximum is 999_999_999.  Default is 0.

        Note: Negative times (before the UNIX epoch) are represented as neg. seconds + pos. ns.
        """
        if not isinstance(seconds, int):
            raise TypeError("seconds must be an integer")
        if not isinstance(nanoseconds, int):
            raise TypeError("nanoseconds must be an integer")
        if not (0 <= nanoseconds < 10**9):
            raise ValueError("nanoseconds must be a non-negative integer less than 999999999.")
        self.seconds = seconds
        self.nanoseconds = nanoseconds

    def __repr__(self):
        """String representation of Timestamp."""
        return f"Timestamp(seconds={self.seconds}, nanoseconds={self.nanoseconds})"

    def __eq__(self, other):
        """Check for equality with another Timestamp object"""
        if type(other) is self.__class__:
            return self.seconds == other.seconds and self.nanoseconds == other.nanoseconds
        return False

    def __ne__(self, other):
        """not-equals method (see :func:`__eq__()`)"""
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.seconds, self.nanoseconds))

    @staticmethod
    def from_bytes(b):
        """Unpack bytes into a `Timestamp` object.

        Used for pure-Python msgpack unpacking.

        :param b: Payload from msgpack ext message with code -1
        :type b: bytes

        :returns: Timestamp object unpacked from msgpack ext payload
        :rtype: Timestamp
        """
        if len(b) == 4:
            seconds = struct.unpack("!L", b)[0]
            nanoseconds = 0
        elif len(b) == 8:
            data64 = struct.unpack("!Q", b)[0]
            seconds = data64 & 0x00000003FFFFFFFF
            nanoseconds = data64 >> 34
        elif len(b) == 12:
            nanoseconds, seconds = struct.unpack("!Iq", b)
        else:
            raise ValueError(
                "Timestamp type can only be created from 32, 64, or 96-bit byte objects"
            )
        return Timestamp(seconds, nanoseconds)

    def to_bytes(self):
        """Pack this Timestamp object into bytes.

        Used for pure-Python msgpack packing.

        :returns data: Payload for EXT message with code -1 (timestamp type)
        :rtype: bytes
        """
        if (self.seconds >> 34) == 0:  # seconds is non-negative and fits in 34 bits
            data64 = self.nanoseconds << 34 | self.seconds
            if data64 & 0xFFFFFFFF00000000 == 0:
                # nanoseconds is zero and seconds < 2**32, so timestamp 32
                data = struct.pack("!L", data64)
            else:
                # timestamp 64
                data = struct.pack("!Q", data64)
        else:
            # timestamp 96
            data = struct.pack("!Iq", self.nanoseconds, self.seconds)
        return data

    @staticmethod
    def from_unix(unix_sec):
        """Create a Timestamp from posix timestamp in seconds.

        :param unix_float: Posix timestamp in seconds.
        :type unix_float: int or float
        """
        seconds = int(unix_sec // 1)
        nanoseconds = int((unix_sec % 1) * 10**9)
        return Timestamp(seconds, nanoseconds)

    def to_unix(self):
        """Get the timestamp as a floating-point value.

        :returns: posix timestamp
        :rtype: float
        """
        return self.seconds + self.nanoseconds / 1e9

    @staticmethod
    def from_unix_nano(unix_ns):
        """Create a Timestamp from posix timestamp in nanoseconds.

        :param int unix_ns: Posix timestamp in nanoseconds.
        :rtype: Timestamp
        """
        return Timestamp(*divmod(unix_ns, 10**9))

    def to_unix_nano(self):
        """Get the timestamp as a unixtime in nanoseconds.

        :returns: posix timestamp in nanoseconds
        :rtype: int
        """
        return self.seconds * 10**9 + self.nanoseconds

    def to_datetime(self):
        """Get the timestamp as a UTC datetime.

        :rtype: `datetime.datetime`
        """
        utc = datetime.timezone.utc
        return datetime.datetime.fromtimestamp(0, utc) + datetime.timedelta(
            seconds=self.seconds, microseconds=self.nanoseconds // 1000
        )

    @staticmethod
    def from_datetime(dt):
        """Create a Timestamp from datetime with tzinfo.

        :rtype: Timestamp
        """
        return Timestamp(seconds=int(dt.timestamp()), nanoseconds=dt.microsecond * 1000)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\resolvelib\structs.py ===
import itertools

from .compat import collections_abc


class DirectedGraph(object):
    """A graph structure with directed edges."""

    def __init__(self):
        self._vertices = set()
        self._forwards = {}  # <key> -> Set[<key>]
        self._backwards = {}  # <key> -> Set[<key>]

    def __iter__(self):
        return iter(self._vertices)

    def __len__(self):
        return len(self._vertices)

    def __contains__(self, key):
        return key in self._vertices

    def copy(self):
        """Return a shallow copy of this graph."""
        other = DirectedGraph()
        other._vertices = set(self._vertices)
        other._forwards = {k: set(v) for k, v in self._forwards.items()}
        other._backwards = {k: set(v) for k, v in self._backwards.items()}
        return other

    def add(self, key):
        """Add a new vertex to the graph."""
        if key in self._vertices:
            raise ValueError("vertex exists")
        self._vertices.add(key)
        self._forwards[key] = set()
        self._backwards[key] = set()

    def remove(self, key):
        """Remove a vertex from the graph, disconnecting all edges from/to it."""
        self._vertices.remove(key)
        for f in self._forwards.pop(key):
            self._backwards[f].remove(key)
        for t in self._backwards.pop(key):
            self._forwards[t].remove(key)

    def connected(self, f, t):
        return f in self._backwards[t] and t in self._forwards[f]

    def connect(self, f, t):
        """Connect two existing vertices.

        Nothing happens if the vertices are already connected.
        """
        if t not in self._vertices:
            raise KeyError(t)
        self._forwards[f].add(t)
        self._backwards[t].add(f)

    def iter_edges(self):
        for f, children in self._forwards.items():
            for t in children:
                yield f, t

    def iter_children(self, key):
        return iter(self._forwards[key])

    def iter_parents(self, key):
        return iter(self._backwards[key])


class IteratorMapping(collections_abc.Mapping):
    def __init__(self, mapping, accessor, appends=None):
        self._mapping = mapping
        self._accessor = accessor
        self._appends = appends or {}

    def __repr__(self):
        return "IteratorMapping({!r}, {!r}, {!r})".format(
            self._mapping,
            self._accessor,
            self._appends,
        )

    def __bool__(self):
        return bool(self._mapping or self._appends)

    __nonzero__ = __bool__  # XXX: Python 2.

    def __contains__(self, key):
        return key in self._mapping or key in self._appends

    def __getitem__(self, k):
        try:
            v = self._mapping[k]
        except KeyError:
            return iter(self._appends[k])
        return itertools.chain(self._accessor(v), self._appends.get(k, ()))

    def __iter__(self):
        more = (k for k in self._appends if k not in self._mapping)
        return itertools.chain(self._mapping, more)

    def __len__(self):
        more = sum(1 for k in self._appends if k not in self._mapping)
        return len(self._mapping) + more


class _FactoryIterableView(object):
    """Wrap an iterator factory returned by `find_matches()`.

    Calling `iter()` on this class would invoke the underlying iterator
    factory, making it a "collection with ordering" that can be iterated
    through multiple times, but lacks random access methods presented in
    built-in Python sequence types.
    """

    def __init__(self, factory):
        self._factory = factory
        self._iterable = None

    def __repr__(self):
        return "{}({})".format(type(self).__name__, list(self))

    def __bool__(self):
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    __nonzero__ = __bool__  # XXX: Python 2.

    def __iter__(self):
        iterable = (
            self._factory() if self._iterable is None else self._iterable
        )
        self._iterable, current = itertools.tee(iterable)
        return current


class _SequenceIterableView(object):
    """Wrap an iterable returned by find_matches().

    This is essentially just a proxy to the underlying sequence that provides
    the same interface as `_FactoryIterableView`.
    """

    def __init__(self, sequence):
        self._sequence = sequence

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self._sequence)

    def __bool__(self):
        return bool(self._sequence)

    __nonzero__ = __bool__  # XXX: Python 2.

    def __iter__(self):
        return iter(self._sequence)


def build_iter_view(matches):
    """Build an iterable view from the value returned by `find_matches()`."""
    if callable(matches):
        return _FactoryIterableView(matches)
    if not isinstance(matches, collections_abc.Sequence):
        matches = list(matches)
    return _SequenceIterableView(matches)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\groff.py ===
"""
    pygments.formatters.groff
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for groff output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import math
from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_bool_opt, get_int_opt

__all__ = ['GroffFormatter']


class GroffFormatter(Formatter):
    """
    Format tokens with groff escapes to change their color and font style.

    .. versionadded:: 2.11

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `monospaced`
        If set to true, monospace font will be used (default: ``true``).

    `linenos`
        If set to true, print the line numbers (default: ``false``).

    `wrap`
        Wrap lines to the specified number of characters. Disabled if set to 0
        (default: ``0``).
    """

    name = 'groff'
    aliases = ['groff','troff','roff']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.monospaced = get_bool_opt(options, 'monospaced', True)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self._lineno = 0
        self.wrap = get_int_opt(options, 'wrap', 0)
        self._linelen = 0

        self.styles = {}
        self._make_styles()


    def _make_styles(self):
        regular = '\\f[CR]' if self.monospaced else '\\f[R]'
        bold = '\\f[CB]' if self.monospaced else '\\f[B]'
        italic = '\\f[CI]' if self.monospaced else '\\f[I]'

        for ttype, ndef in self.style:
            start = end = ''
            if ndef['color']:
                start += '\\m[{}]'.format(ndef['color'])
                end = '\\m[]' + end
            if ndef['bold']:
                start += bold
                end = regular + end
            if ndef['italic']:
                start += italic
                end = regular + end
            if ndef['bgcolor']:
                start += '\\M[{}]'.format(ndef['bgcolor'])
                end = '\\M[]' + end

            self.styles[ttype] = start, end


    def _define_colors(self, outfile):
        colors = set()
        for _, ndef in self.style:
            if ndef['color'] is not None:
                colors.add(ndef['color'])

        for color in sorted(colors):
            outfile.write('.defcolor ' + color + ' rgb #' + color + '\n')


    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s% 4d " % (self._lineno != 1 and '\n' or '', self._lineno))


    def _wrap_line(self, line):
        length = len(line.rstrip('\n'))
        space = '     ' if self.linenos else ''
        newline = ''

        if length > self.wrap:
            for i in range(0, math.floor(length / self.wrap)):
                chunk = line[i*self.wrap:i*self.wrap+self.wrap]
                newline += (chunk + '\n' + space)
            remainder = length % self.wrap
            if remainder > 0:
                newline += line[-remainder-1:]
                self._linelen = remainder
        elif self._linelen + length > self.wrap:
            newline = ('\n' + space) + line
            self._linelen = length
        else:
            newline = line
            self._linelen += length

        return newline


    def _escape_chars(self, text):
        text = text.replace('\\', '\\[u005C]'). \
                    replace('.', '\\[char46]'). \
                    replace('\'', '\\[u0027]'). \
                    replace('`', '\\[u0060]'). \
                    replace('~', '\\[u007E]')
        copy = text

        for char in copy:
            if len(char) != len(char.encode()):
                uni = char.encode('unicode_escape') \
                    .decode()[1:] \
                    .replace('x', 'u00') \
                    .upper()
                text = text.replace(char, '\\[u' + uni[1:] + ']')

        return text


    def format_unencoded(self, tokensource, outfile):
        self._define_colors(outfile)

        outfile.write('.nf\n\\f[CR]\n')

        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            start, end = self.styles[ttype]

            for line in value.splitlines(True):
                if self.wrap > 0:
                    line = self._wrap_line(line)

                if start and end:
                    text = self._escape_chars(line.rstrip('\n'))
                    if text != '':
                        outfile.write(''.join((start, text, end)))
                else:
                    outfile.write(self._escape_chars(line.rstrip('\n')))

                if line.endswith('\n'):
                    if self.linenos:
                        self._write_lineno(outfile)
                        self._linelen = 0
                    else:
                        outfile.write('\n')
                        self._linelen = 0

        outfile.write('\n.fi')

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\groff.py ===
"""
    pygments.formatters.groff
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for groff output.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import math
from pygments.formatter import Formatter
from pygments.util import get_bool_opt, get_int_opt

__all__ = ['GroffFormatter']


class GroffFormatter(Formatter):
    """
    Format tokens with groff escapes to change their color and font style.

    .. versionadded:: 2.11

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `monospaced`
        If set to true, monospace font will be used (default: ``true``).

    `linenos`
        If set to true, print the line numbers (default: ``false``).

    `wrap`
        Wrap lines to the specified number of characters. Disabled if set to 0
        (default: ``0``).
    """

    name = 'groff'
    aliases = ['groff','troff','roff']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.monospaced = get_bool_opt(options, 'monospaced', True)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self._lineno = 0
        self.wrap = get_int_opt(options, 'wrap', 0)
        self._linelen = 0

        self.styles = {}
        self._make_styles()


    def _make_styles(self):
        regular = '\\f[CR]' if self.monospaced else '\\f[R]'
        bold = '\\f[CB]' if self.monospaced else '\\f[B]'
        italic = '\\f[CI]' if self.monospaced else '\\f[I]'

        for ttype, ndef in self.style:
            start = end = ''
            if ndef['color']:
                start += '\\m[{}]'.format(ndef['color'])
                end = '\\m[]' + end
            if ndef['bold']:
                start += bold
                end = regular + end
            if ndef['italic']:
                start += italic
                end = regular + end
            if ndef['bgcolor']:
                start += '\\M[{}]'.format(ndef['bgcolor'])
                end = '\\M[]' + end

            self.styles[ttype] = start, end


    def _define_colors(self, outfile):
        colors = set()
        for _, ndef in self.style:
            if ndef['color'] is not None:
                colors.add(ndef['color'])

        for color in sorted(colors):
            outfile.write('.defcolor ' + color + ' rgb #' + color + '\n')


    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s% 4d " % (self._lineno != 1 and '\n' or '', self._lineno))


    def _wrap_line(self, line):
        length = len(line.rstrip('\n'))
        space = '     ' if self.linenos else ''
        newline = ''

        if length > self.wrap:
            for i in range(0, math.floor(length / self.wrap)):
                chunk = line[i*self.wrap:i*self.wrap+self.wrap]
                newline += (chunk + '\n' + space)
            remainder = length % self.wrap
            if remainder > 0:
                newline += line[-remainder-1:]
                self._linelen = remainder
        elif self._linelen + length > self.wrap:
            newline = ('\n' + space) + line
            self._linelen = length
        else:
            newline = line
            self._linelen += length

        return newline


    def _escape_chars(self, text):
        text = text.replace('\\', '\\[u005C]'). \
                    replace('.', '\\[char46]'). \
                    replace('\'', '\\[u0027]'). \
                    replace('`', '\\[u0060]'). \
                    replace('~', '\\[u007E]')
        copy = text

        for char in copy:
            if len(char) != len(char.encode()):
                uni = char.encode('unicode_escape') \
                    .decode()[1:] \
                    .replace('x', 'u00') \
                    .upper()
                text = text.replace(char, '\\[u' + uni[1:] + ']')

        return text


    def format_unencoded(self, tokensource, outfile):
        self._define_colors(outfile)

        outfile.write('.nf\n\\f[CR]\n')

        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            start, end = self.styles[ttype]

            for line in value.splitlines(True):
                if self.wrap > 0:
                    line = self._wrap_line(line)

                if start and end:
                    text = self._escape_chars(line.rstrip('\n'))
                    if text != '':
                        outfile.write(''.join((start, text, end)))
                else:
                    outfile.write(self._escape_chars(line.rstrip('\n')))

                if line.endswith('\n'):
                    if self.linenos:
                        self._write_lineno(outfile)
                        self._linelen = 0
                    else:
                        outfile.write('\n')
                        self._linelen = 0

        outfile.write('\n.fi')

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\stata.py ===
"""
    pygments.lexers.stata
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for Stata

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from pygments.lexer import RegexLexer, default, include, words
from pygments.token import Comment, Keyword, Name, Number, \
    String, Text, Operator

from pygments.lexers._stata_builtins import builtins_base, builtins_functions

__all__ = ['StataLexer']


class StataLexer(RegexLexer):
    """
    For Stata do files.
    """
    # Syntax based on
    # - http://fmwww.bc.edu/RePEc/bocode/s/synlightlist.ado
    # - https://github.com/isagalaev/highlight.js/blob/master/src/languages/stata.js
    # - https://github.com/jpitblado/vim-stata/blob/master/syntax/stata.vim

    name = 'Stata'
    url = 'http://www.stata.com/'
    version_added = '2.2'
    aliases   = ['stata', 'do']
    filenames = ['*.do', '*.ado']
    mimetypes = ['text/x-stata', 'text/stata', 'application/x-stata']
    flags     = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            include('comments'),
            include('strings'),
            include('macros'),
            include('numbers'),
            include('keywords'),
            include('operators'),
            include('format'),
            (r'.', Text),
        ],
        # Comments are a complicated beast in Stata because they can be
        # nested and there are a few corner cases with that. See:
        # - github.com/kylebarron/language-stata/issues/90
        # - statalist.org/forums/forum/general-stata-discussion/general/1448244
        'comments': [
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single, 'comments-double-slash'),
            (r'^\s*\*', Comment.Single, 'comments-star'),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'comments-triple-slash')
        ],
        'comments-block': [
            (r'/\*', Comment.Multiline, '#push'),
            # this ends and restarts a comment block. but need to catch this so
            # that it doesn\'t start _another_ level of comment blocks
            (r'\*/\*', Comment.Multiline),
            (r'(\*/\s+\*(?!/)[^\n]*)|(\*/)', Comment.Multiline, '#pop'),
            # Match anything else as a character inside the comment
            (r'.', Comment.Multiline),
        ],
        'comments-star': [
            (r'///.*?\n', Comment.Single,
                ('#pop', 'comments-triple-slash')),
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single,
                ('#pop', 'comments-double-slash')),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'comments-triple-slash': [
            (r'\n', Comment.Special, '#pop'),
            # A // breaks out of a comment for the rest of the line
            (r'//.*?(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'comments-double-slash': [
            (r'\n', Text, '#pop'),
            (r'.', Comment.Single),
        ],
        # `"compound string"' and regular "string"; note the former are
        # nested.
        'strings': [
            (r'`"', String, 'string-compound'),
            (r'(?<!`)"', String, 'string-regular'),
        ],
        'string-compound': [
            (r'`"', String, '#push'),
            (r'"\'', String, '#pop'),
            (r'\\\\|\\"|\\\$|\\`|\\\n', String.Escape),
            include('macros'),
            (r'.', String)
        ],
        'string-regular': [
            (r'(")(?!\')|(?=\n)', String, '#pop'),
            (r'\\\\|\\"|\\\$|\\`|\\\n', String.Escape),
            include('macros'),
            (r'.', String)
        ],
        # A local is usually
        #     `\w{0,31}'
        #     `:extended macro'
        #     `=expression'
        #     `[rsen](results)'
        #     `(++--)scalar(++--)'
        #
        # However, there are all sorts of weird rules wrt edge
        # cases. Instead of writing 27 exceptions, anything inside
        # `' is a local.
        #
        # A global is more restricted, so we do follow rules. Note only
        # locals explicitly enclosed ${} can be nested.
        'macros': [
            (r'\$(\{|(?=[$`]))', Name.Variable.Global, 'macro-global-nested'),
            (r'\$', Name.Variable.Global,  'macro-global-name'),
            (r'`', Name.Variable, 'macro-local'),
        ],
        'macro-local': [
            (r'`', Name.Variable, '#push'),
            (r"'", Name.Variable, '#pop'),
            (r'\$(\{|(?=[$`]))', Name.Variable.Global, 'macro-global-nested'),
            (r'\$', Name.Variable.Global, 'macro-global-name'),
            (r'.', Name.Variable),  # fallback
        ],
        'macro-global-nested': [
            (r'\$(\{|(?=[$`]))', Name.Variable.Global, '#push'),
            (r'\}', Name.Variable.Global, '#pop'),
            (r'\$', Name.Variable.Global, 'macro-global-name'),
            (r'`', Name.Variable, 'macro-local'),
            (r'\w', Name.Variable.Global),  # fallback
            default('#pop'),
        ],
        'macro-global-name': [
            (r'\$(\{|(?=[$`]))', Name.Variable.Global, 'macro-global-nested', '#pop'),
            (r'\$', Name.Variable.Global, 'macro-global-name', '#pop'),
            (r'`', Name.Variable, 'macro-local', '#pop'),
            (r'\w{1,32}', Name.Variable.Global, '#pop'),
        ],
        # Built in functions and statements
        'keywords': [
            (words(builtins_functions, prefix = r'\b', suffix = r'(?=\()'),
             Name.Function),
            (words(builtins_base, prefix = r'(^\s*|\s)', suffix = r'\b'),
             Keyword),
        ],
        # http://www.stata.com/help.cgi?operators
        'operators': [
            (r'-|==|<=|>=|<|>|&|!=', Operator),
            (r'\*|\+|\^|/|!|~|==|~=', Operator)
        ],
        # Stata numbers
        'numbers': [
            # decimal number
            (r'\b[+-]?([0-9]+(\.[0-9]+)?|\.[0-9]+|\.)([eE][+-]?[0-9]+)?[i]?\b',
             Number),
        ],
        # Stata formats
        'format': [
            (r'%-?\d{1,2}(\.\d{1,2})?[gfe]c?', Name.Other),
            (r'%(21x|16H|16L|8H|8L)', Name.Other),
            (r'%-?(tc|tC|td|tw|tm|tq|th|ty|tg)\S{0,32}', Name.Other),
            (r'%[-~]?\d{1,4}s', Name.Other),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\cast.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Cast (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

@dataclass
class Sink:
    name: str

    id_: str

    #: Text describing the current session. Present only if there is an active
    #: session on the sink.
    session: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['id'] = self.id_
        if self.session is not None:
            json['session'] = self.session
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            id_=str(json['id']),
            session=str(json['session']) if 'session' in json else None,
        )


def enable(
        presentation_url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts observing for sinks that can be used for tab mirroring, and if set,
    sinks compatible with ``presentationUrl`` as well. When sinks are found, a
    ``sinksUpdated`` event is fired.
    Also starts observing for issue messages. When an issue is added or removed,
    an ``issueUpdated`` event is fired.

    :param presentation_url: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if presentation_url is not None:
        params['presentationUrl'] = presentation_url
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops observing for sinks and issues.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.disable',
    }
    json = yield cmd_dict


def set_sink_to_use(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a sink to be used when the web page requests the browser to choose a
    sink via Presentation API, Remote Playback API, or Cast SDK.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.setSinkToUse',
        'params': params,
    }
    json = yield cmd_dict


def start_desktop_mirroring(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts mirroring the desktop to the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.startDesktopMirroring',
        'params': params,
    }
    json = yield cmd_dict


def start_tab_mirroring(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts mirroring the tab to the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.startTabMirroring',
        'params': params,
    }
    json = yield cmd_dict


def stop_casting(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops the active Cast session on the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.stopCasting',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Cast.sinksUpdated')
@dataclass
class SinksUpdated:
    '''
    This is fired whenever the list of available sinks changes. A sink is a
    device or a software surface that you can cast to.
    '''
    sinks: typing.List[Sink]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SinksUpdated:
        return cls(
            sinks=[Sink.from_json(i) for i in json['sinks']]
        )


@event_class('Cast.issueUpdated')
@dataclass
class IssueUpdated:
    '''
    This is fired whenever the outstanding issue/error message changes.
    ``issueMessage`` is empty if there is no issue.
    '''
    issue_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IssueUpdated:
        return cls(
            issue_message=str(json['issueMessage'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\cast.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Cast (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

@dataclass
class Sink:
    name: str

    id_: str

    #: Text describing the current session. Present only if there is an active
    #: session on the sink.
    session: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['id'] = self.id_
        if self.session is not None:
            json['session'] = self.session
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            id_=str(json['id']),
            session=str(json['session']) if 'session' in json else None,
        )


def enable(
        presentation_url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts observing for sinks that can be used for tab mirroring, and if set,
    sinks compatible with ``presentationUrl`` as well. When sinks are found, a
    ``sinksUpdated`` event is fired.
    Also starts observing for issue messages. When an issue is added or removed,
    an ``issueUpdated`` event is fired.

    :param presentation_url: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if presentation_url is not None:
        params['presentationUrl'] = presentation_url
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops observing for sinks and issues.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.disable',
    }
    json = yield cmd_dict


def set_sink_to_use(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a sink to be used when the web page requests the browser to choose a
    sink via Presentation API, Remote Playback API, or Cast SDK.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.setSinkToUse',
        'params': params,
    }
    json = yield cmd_dict


def start_desktop_mirroring(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts mirroring the desktop to the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.startDesktopMirroring',
        'params': params,
    }
    json = yield cmd_dict


def start_tab_mirroring(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts mirroring the tab to the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.startTabMirroring',
        'params': params,
    }
    json = yield cmd_dict


def stop_casting(
        sink_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops the active Cast session on the sink.

    :param sink_name:
    '''
    params: T_JSON_DICT = dict()
    params['sinkName'] = sink_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Cast.stopCasting',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Cast.sinksUpdated')
@dataclass
class SinksUpdated:
    '''
    This is fired whenever the list of available sinks changes. A sink is a
    device or a software surface that you can cast to.
    '''
    sinks: typing.List[Sink]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SinksUpdated:
        return cls(
            sinks=[Sink.from_json(i) for i in json['sinks']]
        )


@event_class('Cast.issueUpdated')
@dataclass
class IssueUpdated:
    '''
    This is fired whenever the outstanding issue/error message changes.
    ``issueMessage`` is empty if there is no issue.
    '''
    issue_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IssueUpdated:
        return cls(
            issue_message=str(json['issueMessage'])
        )