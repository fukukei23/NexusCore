
# === NexusCore/tools\exports\export_20250803_114325\combined_235.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\llms\databricks\streaming_utils.py ===
import json
from typing import Optional

import litellm
from litellm import verbose_logger
from litellm.types.llms.openai import (
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionUsageBlock,
)
from litellm.types.utils import GenericStreamingChunk, Usage


class ModelResponseIterator:
    def __init__(self, streaming_response, sync_stream: bool):
        self.streaming_response = streaming_response

    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            processed_chunk = litellm.ModelResponseStream(**chunk)

            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None

            if processed_chunk.choices[0].delta.content is not None:  # type: ignore
                text = processed_chunk.choices[0].delta.content  # type: ignore

            if (
                processed_chunk.choices[0].delta.tool_calls is not None  # type: ignore
                and len(processed_chunk.choices[0].delta.tool_calls) > 0  # type: ignore
                and processed_chunk.choices[0].delta.tool_calls[0].function is not None  # type: ignore
                and processed_chunk.choices[0].delta.tool_calls[0].function.arguments  # type: ignore
                is not None
            ):
                tool_use = ChatCompletionToolCallChunk(
                    id=processed_chunk.choices[0].delta.tool_calls[0].id,  # type: ignore
                    type="function",
                    function=ChatCompletionToolCallFunctionChunk(
                        name=processed_chunk.choices[0]
                        .delta.tool_calls[0]  # type: ignore
                        .function.name,
                        arguments=processed_chunk.choices[0]
                        .delta.tool_calls[0]  # type: ignore
                        .function.arguments,
                    ),
                    index=processed_chunk.choices[0].delta.tool_calls[0].index,
                )

            if processed_chunk.choices[0].finish_reason is not None:
                is_finished = True
                finish_reason = processed_chunk.choices[0].finish_reason

            usage_chunk: Optional[Usage] = getattr(processed_chunk, "usage", None)
            if usage_chunk is not None:
                usage = ChatCompletionUsageBlock(
                    prompt_tokens=usage_chunk.prompt_tokens,
                    completion_tokens=usage_chunk.completion_tokens,
                    total_tokens=usage_chunk.total_tokens,
                )

            return GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=0,
            )
        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

    # Sync iterator
    def __iter__(self):
        self.response_iterator = self.streaming_response
        return self

    def __next__(self):
        if not hasattr(self, "response_iterator"):
            self.response_iterator = self.streaming_response
        try:
            chunk = self.response_iterator.__next__()
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            chunk = litellm.CustomStreamWrapper._strip_sse_data_from_chunk(chunk) or ""
            chunk = chunk.strip()
            if len(chunk) > 0:
                json_chunk = json.loads(chunk)
                return self.chunk_parser(chunk=json_chunk)
            else:
                return GenericStreamingChunk(
                    text="",
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                    index=0,
                    tool_use=None,
                )
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            verbose_logger.debug(
                f"Error parsing chunk: {e},\nReceived chunk: {chunk}. Defaulting to empty chunk here."
            )
            return GenericStreamingChunk(
                text="",
                is_finished=False,
                finish_reason="",
                usage=None,
                index=0,
                tool_use=None,
            )

    # Async iterator
    def __aiter__(self):
        self.async_response_iterator = self.streaming_response.__aiter__()
        return self

    async def __anext__(self):
        try:
            chunk = await self.async_response_iterator.__anext__()
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")
        except Exception as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            chunk = litellm.CustomStreamWrapper._strip_sse_data_from_chunk(chunk) or ""
            chunk = chunk.strip()
            if chunk == "[DONE]":
                raise StopAsyncIteration
            if len(chunk) > 0:
                json_chunk = json.loads(chunk)
                return self.chunk_parser(chunk=json_chunk)
            else:
                return GenericStreamingChunk(
                    text="",
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                    index=0,
                    tool_use=None,
                )
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            verbose_logger.debug(
                f"Error parsing chunk: {e},\nReceived chunk: {chunk}. Defaulting to empty chunk here."
            )
            return GenericStreamingChunk(
                text="",
                is_finished=False,
                finish_reason="",
                usage=None,
                index=0,
                tool_use=None,
            )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\image\amazon_nova_canvas_transformation.py ===
import types
from typing import Any, Dict, List, Optional

from openai.types.image import Image

from litellm.types.llms.bedrock import (
    AmazonNovaCanvasColorGuidedGenerationParams,
    AmazonNovaCanvasColorGuidedRequest,
    AmazonNovaCanvasImageGenerationConfig,
    AmazonNovaCanvasRequestBase,
    AmazonNovaCanvasTextToImageParams,
    AmazonNovaCanvasTextToImageRequest,
    AmazonNovaCanvasTextToImageResponse,
)
from litellm.types.utils import ImageResponse


class AmazonNovaCanvasConfig:
    """
    Reference: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/model-catalog/serverless/amazon.nova-canvas-v1:0

    """

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                ),
            )
            and v is not None
        }

    @classmethod
    def get_supported_openai_params(cls, model: Optional[str] = None) -> List:
        """ """
        return ["n", "size", "quality"]

    @classmethod
    def _is_nova_model(cls, model: Optional[str] = None) -> bool:
        """
        Returns True if the model is a Nova Canvas model

        Nova models follow this pattern:

        """
        if model:
            if "amazon.nova-canvas" in model:
                return True
        return False

    @classmethod
    def transform_request_body(
        cls, text: str, optional_params: dict
    ) -> AmazonNovaCanvasRequestBase:
        """
        Transform the request body for Amazon Nova Canvas model
        """
        task_type = optional_params.pop("taskType", "TEXT_IMAGE")
        image_generation_config = optional_params.pop("imageGenerationConfig", {})
        image_generation_config = {**image_generation_config, **optional_params}
        if task_type == "TEXT_IMAGE":
            text_to_image_params: Dict[str, Any] = image_generation_config.pop(
                "textToImageParams", {}
            )
            text_to_image_params = {"text": text, **text_to_image_params}
            try:
                text_to_image_params_typed = AmazonNovaCanvasTextToImageParams(
                    **text_to_image_params  # type: ignore
                )
            except Exception as e:
                raise ValueError(
                    f"Error transforming text to image params: {e}. Got params: {text_to_image_params}, Expected params: {AmazonNovaCanvasTextToImageParams.__annotations__}"
                )

            try:
                image_generation_config_typed = AmazonNovaCanvasImageGenerationConfig(
                    **image_generation_config
                )
            except Exception as e:
                raise ValueError(
                    f"Error transforming image generation config: {e}. Got params: {image_generation_config}, Expected params: {AmazonNovaCanvasImageGenerationConfig.__annotations__}"
                )

            return AmazonNovaCanvasTextToImageRequest(
                textToImageParams=text_to_image_params_typed,
                taskType=task_type,
                imageGenerationConfig=image_generation_config_typed,
            )
        if task_type == "COLOR_GUIDED_GENERATION":
            color_guided_generation_params: Dict[
                str, Any
            ] = image_generation_config.pop("colorGuidedGenerationParams", {})
            color_guided_generation_params = {
                "text": text,
                **color_guided_generation_params,
            }
            try:
                color_guided_generation_params_typed = AmazonNovaCanvasColorGuidedGenerationParams(
                    **color_guided_generation_params  # type: ignore
                )
            except Exception as e:
                raise ValueError(
                    f"Error transforming color guided generation params: {e}. Got params: {color_guided_generation_params}, Expected params: {AmazonNovaCanvasColorGuidedGenerationParams.__annotations__}"
                )

            try:
                image_generation_config_typed = AmazonNovaCanvasImageGenerationConfig(
                    **image_generation_config
                )
            except Exception as e:
                raise ValueError(
                    f"Error transforming image generation config: {e}. Got params: {image_generation_config}, Expected params: {AmazonNovaCanvasImageGenerationConfig.__annotations__}"
                )

            return AmazonNovaCanvasColorGuidedRequest(
                taskType=task_type,
                colorGuidedGenerationParams=color_guided_generation_params_typed,
                imageGenerationConfig=image_generation_config_typed,
            )
        raise NotImplementedError(f"Task type {task_type} is not supported")

    @classmethod
    def map_openai_params(cls, non_default_params: dict, optional_params: dict) -> dict:
        """
        Map the OpenAI params to the Bedrock params
        """
        _size = non_default_params.get("size")
        if _size is not None:
            width, height = _size.split("x")
            optional_params["width"], optional_params["height"] = int(width), int(
                height
            )
        if non_default_params.get("n") is not None:
            optional_params["numberOfImages"] = non_default_params.get("n")
        if non_default_params.get("quality") is not None:
            if non_default_params.get("quality") in ("hd", "premium"):
                optional_params["quality"] = "premium"
            if non_default_params.get("quality") == "standard":
                optional_params["quality"] = "standard"
        return optional_params

    @classmethod
    def transform_response_dict_to_openai_response(
        cls, model_response: ImageResponse, response_dict: dict
    ) -> ImageResponse:
        """
        Transform the response dict to the OpenAI response
        """

        nova_response = AmazonNovaCanvasTextToImageResponse(**response_dict)
        openai_images: List[Image] = []
        for _img in nova_response.get("images", []):
            openai_images.append(Image(b64_json=_img))

        model_response.data = openai_images
        return model_response

# === NexusCore/openenv\Lib\site-packages\openai\helpers\local_audio_player.py ===
# mypy: ignore-errors
from __future__ import annotations

import queue
import asyncio
from typing import Any, Union, Callable, AsyncGenerator, cast
from typing_extensions import TYPE_CHECKING

from .. import _legacy_response
from .._extras import numpy as np, sounddevice as sd
from .._response import StreamedBinaryAPIResponse, AsyncStreamedBinaryAPIResponse

if TYPE_CHECKING:
    import numpy.typing as npt

SAMPLE_RATE = 24000


class LocalAudioPlayer:
    def __init__(
        self,
        should_stop: Union[Callable[[], bool], None] = None,
    ):
        self.channels = 1
        self.dtype = np.float32
        self.should_stop = should_stop

    async def _tts_response_to_buffer(
        self,
        response: Union[
            _legacy_response.HttpxBinaryResponseContent,
            AsyncStreamedBinaryAPIResponse,
            StreamedBinaryAPIResponse,
        ],
    ) -> npt.NDArray[np.float32]:
        chunks: list[bytes] = []
        if isinstance(response, _legacy_response.HttpxBinaryResponseContent) or isinstance(
            response, StreamedBinaryAPIResponse
        ):
            for chunk in response.iter_bytes(chunk_size=1024):
                if chunk:
                    chunks.append(chunk)
        else:
            async for chunk in response.iter_bytes(chunk_size=1024):
                if chunk:
                    chunks.append(chunk)

        audio_bytes = b"".join(chunks)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
        audio_np = audio_np.reshape(-1, 1)
        return audio_np

    async def play(
        self,
        input: Union[
            npt.NDArray[np.int16],
            npt.NDArray[np.float32],
            _legacy_response.HttpxBinaryResponseContent,
            AsyncStreamedBinaryAPIResponse,
            StreamedBinaryAPIResponse,
        ],
    ) -> None:
        audio_content: npt.NDArray[np.float32]
        if isinstance(input, np.ndarray):
            if input.dtype == np.int16 and self.dtype == np.float32:
                audio_content = (input.astype(np.float32) / 32767.0).reshape(-1, self.channels)
            elif input.dtype == np.float32:
                audio_content = cast("npt.NDArray[np.float32]", input)
            else:
                raise ValueError(f"Unsupported dtype: {input.dtype}")
        else:
            audio_content = await self._tts_response_to_buffer(input)

        loop = asyncio.get_event_loop()
        event = asyncio.Event()
        idx = 0

        def callback(
            outdata: npt.NDArray[np.float32],
            frame_count: int,
            _time_info: Any,
            _status: Any,
        ):
            nonlocal idx

            remainder = len(audio_content) - idx
            if remainder == 0 or (callable(self.should_stop) and self.should_stop()):
                loop.call_soon_threadsafe(event.set)
                raise sd.CallbackStop
            valid_frames = frame_count if remainder >= frame_count else remainder
            outdata[:valid_frames] = audio_content[idx : idx + valid_frames]
            outdata[valid_frames:] = 0
            idx += valid_frames

        stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            callback=callback,
            dtype=audio_content.dtype,
            channels=audio_content.shape[1],
        )
        with stream:
            await event.wait()

    async def play_stream(
        self,
        buffer_stream: AsyncGenerator[Union[npt.NDArray[np.float32], npt.NDArray[np.int16], None], None],
    ) -> None:
        loop = asyncio.get_event_loop()
        event = asyncio.Event()
        buffer_queue: queue.Queue[Union[npt.NDArray[np.float32], npt.NDArray[np.int16], None]] = queue.Queue(maxsize=50)

        async def buffer_producer():
            async for buffer in buffer_stream:
                if buffer is None:
                    break
                await loop.run_in_executor(None, buffer_queue.put, buffer)
            await loop.run_in_executor(None, buffer_queue.put, None)  # Signal completion

        def callback(
            outdata: npt.NDArray[np.float32],
            frame_count: int,
            _time_info: Any,
            _status: Any,
        ):
            nonlocal current_buffer, buffer_pos

            frames_written = 0
            while frames_written < frame_count:
                if current_buffer is None or buffer_pos >= len(current_buffer):
                    try:
                        current_buffer = buffer_queue.get(timeout=0.1)
                        if current_buffer is None:
                            loop.call_soon_threadsafe(event.set)
                            raise sd.CallbackStop
                        buffer_pos = 0

                        if current_buffer.dtype == np.int16 and self.dtype == np.float32:
                            current_buffer = (current_buffer.astype(np.float32) / 32767.0).reshape(-1, self.channels)

                    except queue.Empty:
                        outdata[frames_written:] = 0
                        return

                remaining_frames = len(current_buffer) - buffer_pos
                frames_to_write = min(frame_count - frames_written, remaining_frames)
                outdata[frames_written : frames_written + frames_to_write] = current_buffer[
                    buffer_pos : buffer_pos + frames_to_write
                ]
                buffer_pos += frames_to_write
                frames_written += frames_to_write

        current_buffer = None
        buffer_pos = 0

        producer_task = asyncio.create_task(buffer_producer())

        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=self.channels,
            dtype=self.dtype,
            callback=callback,
        ):
            await event.wait()

        await producer_task

# === NexusCore/openenv\Lib\site-packages\trio\_core\_mock_clock.py ===
import time
from math import inf

from .. import _core
from .._abc import Clock
from .._util import final
from ._run import GLOBAL_RUN_CONTEXT

################################################################
# The glorious MockClock
################################################################


# Prior art:
#   https://twistedmatrix.com/documents/current/api/twisted.internet.task.Clock.html
#   https://github.com/ztellman/manifold/issues/57
@final
class MockClock(Clock):
    """A user-controllable clock suitable for writing tests.

    Args:
      rate (float): the initial :attr:`rate`.
      autojump_threshold (float): the initial :attr:`autojump_threshold`.

    .. attribute:: rate

       How many seconds of clock time pass per second of real time. Default is
       0.0, i.e. the clock only advances through manuals calls to :meth:`jump`
       or when the :attr:`autojump_threshold` is triggered. You can assign to
       this attribute to change it.

    .. attribute:: autojump_threshold

       The clock keeps an eye on the run loop, and if at any point it detects
       that all tasks have been blocked for this many real seconds (i.e.,
       according to the actual clock, not this clock), then the clock
       automatically jumps ahead to the run loop's next scheduled
       timeout. Default is :data:`math.inf`, i.e., to never autojump. You can
       assign to this attribute to change it.

       Basically the idea is that if you have code or tests that use sleeps
       and timeouts, you can use this to make it run much faster, totally
       automatically. (At least, as long as those sleeps/timeouts are
       happening inside Trio; if your test involves talking to external
       service and waiting for it to timeout then obviously we can't help you
       there.)

       You should set this to the smallest value that lets you reliably avoid
       "false alarms" where some I/O is in flight (e.g. between two halves of
       a socketpair) but the threshold gets triggered and time gets advanced
       anyway. This will depend on the details of your tests and test
       environment. If you aren't doing any I/O (like in our sleeping example
       above) then just set it to zero, and the clock will jump whenever all
       tasks are blocked.

       .. note:: If you use ``autojump_threshold`` and
          `wait_all_tasks_blocked` at the same time, then you might wonder how
          they interact, since they both cause things to happen after the run
          loop goes idle for some time. The answer is:
          `wait_all_tasks_blocked` takes priority. If there's a task blocked
          in `wait_all_tasks_blocked`, then the autojump feature treats that
          as active task and does *not* jump the clock.

    """

    def __init__(self, rate: float = 0.0, autojump_threshold: float = inf) -> None:
        # when the real clock said 'real_base', the virtual time was
        # 'virtual_base', and since then it's advanced at 'rate' virtual
        # seconds per real second.
        self._real_base = 0.0
        self._virtual_base = 0.0
        self._rate = 0.0

        # kept as an attribute so that our tests can monkeypatch it
        self._real_clock = time.perf_counter

        # use the property update logic to set initial values
        self.rate = rate
        self.autojump_threshold = autojump_threshold

    def __repr__(self) -> str:
        return f"<MockClock, time={self.current_time():.7f}, rate={self._rate} @ {id(self):#x}>"

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, new_rate: float) -> None:
        if new_rate < 0:
            raise ValueError("rate must be >= 0")
        else:
            real = self._real_clock()
            virtual = self._real_to_virtual(real)
            self._virtual_base = virtual
            self._real_base = real
            self._rate = float(new_rate)

    @property
    def autojump_threshold(self) -> float:
        return self._autojump_threshold

    @autojump_threshold.setter
    def autojump_threshold(self, new_autojump_threshold: float) -> None:
        self._autojump_threshold = float(new_autojump_threshold)
        self._try_resync_autojump_threshold()

    # runner.clock_autojump_threshold is an internal API that isn't easily
    # usable by custom third-party Clock objects. If you need access to this
    # functionality, let us know, and we'll figure out how to make a public
    # API. Discussion:
    #
    #     https://github.com/python-trio/trio/issues/1587
    def _try_resync_autojump_threshold(self) -> None:
        try:
            runner = GLOBAL_RUN_CONTEXT.runner
            if runner.is_guest:
                runner.force_guest_tick_asap()
        except AttributeError:
            pass
        else:
            if runner.clock is self:
                runner.clock_autojump_threshold = self._autojump_threshold

    # Invoked by the run loop when runner.clock_autojump_threshold is
    # exceeded.
    def _autojump(self) -> None:
        statistics = _core.current_statistics()
        jump = statistics.seconds_to_next_deadline
        if 0 < jump < inf:
            self.jump(jump)

    def _real_to_virtual(self, real: float) -> float:
        real_offset = real - self._real_base
        virtual_offset = self._rate * real_offset
        return self._virtual_base + virtual_offset

    def start_clock(self) -> None:
        self._try_resync_autojump_threshold()

    def current_time(self) -> float:
        return self._real_to_virtual(self._real_clock())

    def deadline_to_sleep_time(self, deadline: float) -> float:
        virtual_timeout = deadline - self.current_time()
        if virtual_timeout <= 0:
            return 0
        elif self._rate > 0:
            return virtual_timeout / self._rate
        else:
            return 999999999

    def jump(self, seconds: float) -> None:
        """Manually advance the clock by the given number of seconds.

        Args:
          seconds (float): the number of seconds to jump the clock forward.

        Raises:
          ValueError: if you try to pass a negative value for ``seconds``.

        """
        if seconds < 0:
            raise ValueError("time can't go backwards")
        self._virtual_base += seconds

# === NexusCore/run_policy_check_test.py ===
# ==============================================================================
# ファイル名: run_policy_check_test.py (修正版)
# 場所: プロジェクトのルートディレクトリ
# メモ: PolicyAgentが開発サイクルに正しく組み込まれ、ポリシー違反を
#      検知・ブロックできるかを検証するためのE2Eテストスクリプト。
#      << 修正点 >>
#      - __init__.py をテスト用サンドボックスに自動生成し、
#        pytestのモジュール解決エラーを修正。
# ==============================================================================

import os
import shutil
import logging
import json
from pathlib import Path # pathlibをインポート

# --- プロジェクトのコアコンポーネントをインポート ---
from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.patch_applier import PatchApplier

# --- テスト用の設定 ---
TEST_PROJECT_PATH = "policy_test_sandbox"
API_KEY = "dummy_key_for_testing"
MODEL = "dummy"

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_test_environment():
    """テスト用のサンドボックス環境を準備する"""
    logger.info(f"Setting up test environment at: ./{TEST_PROJECT_PATH}")
    if os.path.exists(TEST_PROJECT_PATH):
        shutil.rmtree(TEST_PROJECT_PATH)
    
    # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
    # 各ディレクトリを作成し、同時に__init__.pyファイルも作成する
    app_dir = Path(TEST_PROJECT_PATH) / "app"
    tests_dir = Path(TEST_PROJECT_PATH) / "tests"
    
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    
    # __init__.py を作成して、ディレクトリをPythonパッケージとして認識させる
    (app_dir / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()
    
    # ダミーの初期ファイルを作成
    (app_dir / "main.py").write_text("# Initial application file\n", encoding='utf-8')
    (tests_dir / "test_main.py").write_text("# Initial test file\n", encoding='utf-8')
    # --- ★★★★★ ここまでが最重要修正点 ★★★★★ ---
    
    logger.info("Test environment setup complete with package markers (__init__.py).")

def run_test():
    """PolicyAgentの統合テストを実行する"""
    setup_test_environment()

    logger.info("--- Initializing Agents ---")
    
    # 各エージェントを初期化
    architect = ArchitectAgent(API_KEY, MODEL)
    planner = PlannerAgent(API_KEY, MODEL)
    coder = CoderAgent(API_KEY, MODEL)
    tester = TesterAgent(API_KEY, MODEL)
    debugger = DebuggerAgent(API_KEY, MODEL, knowledge_base_path="fkb_local.json")
    guardian = GuardianAgent(API_KEY, MODEL)
    policy_agent = PolicyAgent(API_KEY, MODEL, policy_rules_path="config/policy_rules.json")

    logger.info("--- Initializing Orchestrator with PolicyAgent ---")
    
    orchestrator = Orchestrator(
        project_path=TEST_PROJECT_PATH,
        constitution="Test Constitution: Behave ethically.",
        architect=architect,
        planner=planner,
        coder=coder,
        tester=tester,
        debugger=debugger,
        guardian=guardian,
        policy_agent=policy_agent
    )

    policy_violating_task = {
        "name": "create_debug_greeting",
        "module": "main",
        "description": "Create a function 'debug_greet' that takes a name and prints a greeting message to the console."
    }
    
    logger.info("\n" + "="*50)
    logger.info("🚀 STARTING TEST: EXECUTING A POLICY-VIOLATING TASK")
    logger.info(f"TASK: {policy_violating_task['description']}")
    logger.info("="*50 + "\n")
    
    # 1. CoderAgentに違反コードを生成させる (Simulated)
    logger.info("--- 1. CoderAgent Phase (Simulated) ---")
    violating_code = "def debug_greet(name):\n    print(f'Hello, {name}!')\n"
    source_file_path = os.path.join(TEST_PROJECT_PATH, "app/main.py")
    with open(source_file_path, "w", encoding='utf-8') as f:
        f.write(violating_code)
    logger.info(f"CoderAgent generated violating code:\n---\n{violating_code}\n---")

    # 2. TesterAgentにテストを生成させる (Simulated)
    logger.info("--- 2. TesterAgent Phase (Simulated) ---")
    test_code = "from app.main import debug_greet\n\ndef test_debug_greet(capsys):\n    debug_greet('World')\n    captured = capsys.readouterr()\n    assert captured.out == 'Hello, World!\\n'"
    test_file_path = os.path.join(TEST_PROJECT_PATH, "tests/test_main.py")
    with open(test_file_path, "w", encoding='utf-8') as f:
        f.write(test_code)
    logger.info("TesterAgent generated corresponding tests.")

    # 3. テスト実行サイクル (Actual)
    logger.info("--- 3. Test Execution Cycle (Actual) ---")
    tests_passed, _ = orchestrator.run_tests(test_file_path)
    if not tests_passed:
        logger.error("Tests failed unexpectedly even after the fix. There might be another issue.")
        return
    logger.info("✅ Tests passed successfully.")

    # 4. PolicyAgentによる監査の実行 (Actual)
    logger.info("--- 3.5. PolicyAgent Audit Phase (Actual) ---")
    files_for_audit = [
        {"path": "app/main.py", "content": violating_code},
        {"path": "tests/test_main.py", "content": test_code}
    ]
    policy_result = orchestrator.policy_agent.audit(files_for_audit)

    # 5. 結果の検証
    logger.info("\n" + "="*50)
    logger.info("🔬 TEST RESULT VERIFICATION")
    logger.info("="*50)
    
    if policy_result.get("result") == "REJECTED":
        logger.info("✅ SUCCESS: PolicyAgent correctly REJECTED the code.")
        violations = policy_result.get("violations", [])
        logger.info(f"Found {len(violations)} violation(s):")
        for v in violations:
            logger.info(f"  - {v}")
        
        found_lint_violation = any(v.get("policy_id") == "POLICY_LINT_001" for v in violations)
        if found_lint_violation:
            logger.info("✅ SUCCESS: The correct policy (POLICY_LINT_001) was triggered.")
        else:
            logger.error("❌ FAILURE: The code was rejected, but not for the expected reason (POLICY_LINT_001).")
    else:
        logger.error("❌ FAILURE: PolicyAgent INCORRECTLY approved the code with violations.")

    logger.info("\n--- Test Finished ---")


if __name__ == "__main__":
    run_test()

# === NexusCore/tools\chatgpt_whisper_chatbot.py ===
# ファイル名: chatgpt_whisper_chatbot.py
# メモ:
# - OpenAIのChatGPT APIとWhisper APIを使った日本語対応チャットボット
# - テキスト入力も音声入力（Whisperで文字起こし）もOK
# - GradioでWeb UI
# - チャット履歴はGradio形式で管理
# - .envファイルに OPENAI_API_KEY=sk-... を記載しておくこと

import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import tempfile
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import threading
import time

# --- 環境変数・APIキー読み込み ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

# --- Whisper APIで音声ファイルを文字起こし ---
def transcribe_with_whisper(audio_path):
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja"
            )
        return transcript.text
    except Exception as e:
        raise gr.Error(f"Whisper APIエラー: {e}")

# --- ChatGPTでAIチャット応答（Gradio履歴形式に対応） ---
def chatgpt_respond(history, message):
    # history: [[user, ai], ...] 形式
    # OpenAI API用の履歴に変換
    api_history = []
    for pair in history:
        if pair[0] is not None:
            api_history.append({"role": "user", "content": pair[0]})
        if pair[1] is not None:
            api_history.append({"role": "assistant", "content": pair[1]})
    if message:
        api_history.append({"role": "user", "content": message})
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=api_history,
                max_tokens=512,
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content.strip()
        except Exception as e:
            raise gr.Error(f"ChatGPT APIエラー: {e}")
        # Gradio用履歴に追加
        history.append([message, ai_reply])
    return history, ""

# --- 音声録音（エンターで終了） ---
def record_until_keypress(max_duration=60, sample_rate=16000):
    logging.info(f"録音中... 最大{max_duration}秒、エンターキーで終了")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー入力待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)
    if recording:
        return np.concatenate(recording, axis=0), sample_rate
    return None, sample_rate

def process_audio():
    """音声を録音→Whisperで文字起こし→テキスト返却"""
    try:
        audio_data, fs = record_until_keypress(max_duration=60)
        if audio_data is None:
            raise gr.Warning("録音がキャンセルされました。")
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(temp_file.name, fs, audio_data)
        text = transcribe_with_whisper(temp_file.name)
        os.unlink(temp_file.name)
        return text
    except gr.Warning as w:
        raise w
    except Exception as e:
        logging.error(f"音声処理エラー: {str(e)}")
        raise gr.Error(f"音声処理エラー: {e}")

# --- Gradio UI（日本語化） ---
with gr.Blocks(title="ChatGPT＋Whisperチャットボット", theme=gr.themes.Soft(primary_hue="blue")) as demo:
    gr.Markdown(
        """
        # ChatGPT＋Whisper チャットボット
        - テキストまたは音声でメッセージを入力できます
        - Whisper（音声認識API）＋ChatGPT（AI応答API）両対応
        """
    )
    chatbot = gr.Chatbot(height=600, label="チャット履歴", show_copy_button=True)
    with gr.Group():
        with gr.Row():
            msg = gr.Textbox(
                container=False,
                show_label=False,
                label="メッセージを入力",
                placeholder="テキストを入力、または音声を録音...",
                scale=7,
                autofocus=True
            )
            sub = gr.Button("送信", variant="primary", scale=1, min_width=100)
            record_btn = gr.Button("🎤 録音", variant="secondary", scale=1, min_width=100)
    with gr.Row():
        clear = gr.Button("🗑️ 履歴クリア", variant="secondary")

    session_state = gr.State([])

    # 音声録音ボタン
    record_btn.click(
        process_audio,
        [],
        [msg]
    )

    # チャット送信（AI応答）
    sub.click(
        chatgpt_respond,
        inputs=[session_state, msg],
        outputs=[chatbot, msg]
    )

    # クリアボタン
    def clear_all():
        return [], ""
    clear.click(clear_all, inputs=[], outputs=[chatbot, msg])

demo.launch()

# === NexusCore/openenv\Lib\site-packages\jinxed\_keys.py ===
"""
Key code constants

Most of this information came from the terminfo man pages, part of ncurses
More information on ncurses can be found at:
https://www.gnu.org/software/ncurses/ncurses.html
"""

KEY_A1 = 348
KEY_A3 = 349
KEY_B2 = 350
KEY_BACKSPACE = 263
KEY_BEG = 354
KEY_BREAK = 257
KEY_BTAB = 353
KEY_C1 = 351
KEY_C3 = 352
KEY_CANCEL = 355
KEY_CATAB = 342
KEY_CLEAR = 333
KEY_CLOSE = 356
KEY_COMMAND = 357
KEY_COPY = 358
KEY_CREATE = 359
KEY_CTAB = 341
KEY_DC = 330
KEY_DL = 328
KEY_DOWN = 258
KEY_EIC = 332
KEY_END = 360
KEY_ENTER = 343
KEY_EOL = 335
KEY_EOS = 334
KEY_EXIT = 361
KEY_F0 = 264
KEY_F1 = 265
KEY_F10 = 274
KEY_F11 = 275
KEY_F12 = 276
KEY_F13 = 277
KEY_F14 = 278
KEY_F15 = 279
KEY_F16 = 280
KEY_F17 = 281
KEY_F18 = 282
KEY_F19 = 283
KEY_F2 = 266
KEY_F20 = 284
KEY_F21 = 285
KEY_F22 = 286
KEY_F23 = 287
KEY_F24 = 288
KEY_F25 = 289
KEY_F26 = 290
KEY_F27 = 291
KEY_F28 = 292
KEY_F29 = 293
KEY_F3 = 267
KEY_F30 = 294
KEY_F31 = 295
KEY_F32 = 296
KEY_F33 = 297
KEY_F34 = 298
KEY_F35 = 299
KEY_F36 = 300
KEY_F37 = 301
KEY_F38 = 302
KEY_F39 = 303
KEY_F4 = 268
KEY_F40 = 304
KEY_F41 = 305
KEY_F42 = 306
KEY_F43 = 307
KEY_F44 = 308
KEY_F45 = 309
KEY_F46 = 310
KEY_F47 = 311
KEY_F48 = 312
KEY_F49 = 313
KEY_F5 = 269
KEY_F50 = 314
KEY_F51 = 315
KEY_F52 = 316
KEY_F53 = 317
KEY_F54 = 318
KEY_F55 = 319
KEY_F56 = 320
KEY_F57 = 321
KEY_F58 = 322
KEY_F59 = 323
KEY_F6 = 270
KEY_F60 = 324
KEY_F61 = 325
KEY_F62 = 326
KEY_F63 = 327
KEY_F7 = 271
KEY_F8 = 272
KEY_F9 = 273
KEY_FIND = 362
KEY_HELP = 363
KEY_HOME = 262
KEY_IC = 331
KEY_IL = 329
KEY_LEFT = 260
KEY_LL = 347
KEY_MARK = 364
KEY_MAX = 511
KEY_MESSAGE = 365
KEY_MIN = 257
KEY_MOUSE = 409
KEY_MOVE = 366
KEY_NEXT = 367
KEY_NPAGE = 338
KEY_OPEN = 368
KEY_OPTIONS = 369
KEY_PPAGE = 339
KEY_PREVIOUS = 370
KEY_PRINT = 346
KEY_REDO = 371
KEY_REFERENCE = 372
KEY_REFRESH = 373
KEY_REPLACE = 374
KEY_RESET = 345
KEY_RESIZE = 410
KEY_RESTART = 375
KEY_RESUME = 376
KEY_RIGHT = 261
KEY_SAVE = 377
KEY_SBEG = 378
KEY_SCANCEL = 379
KEY_SCOMMAND = 380
KEY_SCOPY = 381
KEY_SCREATE = 382
KEY_SDC = 383
KEY_SDL = 384
KEY_SELECT = 385
KEY_SEND = 386
KEY_SEOL = 387
KEY_SEXIT = 388
KEY_SF = 336
KEY_SFIND = 389
KEY_SHELP = 390
KEY_SHOME = 391
KEY_SIC = 392
KEY_SLEFT = 393
KEY_SMESSAGE = 394
KEY_SMOVE = 395
KEY_SNEXT = 396
KEY_SOPTIONS = 397
KEY_SPREVIOUS = 398
KEY_SPRINT = 399
KEY_SR = 337
KEY_SREDO = 400
KEY_SREPLACE = 401
KEY_SRESET = 344
KEY_SRIGHT = 402
KEY_SRSUME = 403
KEY_SSAVE = 404
KEY_SSUSPEND = 405
KEY_STAB = 340
KEY_SUNDO = 406
KEY_SUSPEND = 407
KEY_UNDO = 408
KEY_UP = 259

# === NexusCore/openenv\Lib\site-packages\pycparser\ast_transforms.py ===
#------------------------------------------------------------------------------
# pycparser: ast_transforms.py
#
# Some utilities used by the parser to create a friendlier AST.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------

from . import c_ast


def fix_switch_cases(switch_node):
    """ The 'case' statements in a 'switch' come out of parsing with one
        child node, so subsequent statements are just tucked to the parent
        Compound. Additionally, consecutive (fall-through) case statements
        come out messy. This is a peculiarity of the C grammar. The following:

            switch (myvar) {
                case 10:
                    k = 10;
                    p = k + 1;
                    return 10;
                case 20:
                case 30:
                    return 20;
                default:
                    break;
            }

        Creates this tree (pseudo-dump):

            Switch
                ID: myvar
                Compound:
                    Case 10:
                        k = 10
                    p = k + 1
                    return 10
                    Case 20:
                        Case 30:
                            return 20
                    Default:
                        break

        The goal of this transform is to fix this mess, turning it into the
        following:

            Switch
                ID: myvar
                Compound:
                    Case 10:
                        k = 10
                        p = k + 1
                        return 10
                    Case 20:
                    Case 30:
                        return 20
                    Default:
                        break

        A fixed AST node is returned. The argument may be modified.
    """
    assert isinstance(switch_node, c_ast.Switch)
    if not isinstance(switch_node.stmt, c_ast.Compound):
        return switch_node

    # The new Compound child for the Switch, which will collect children in the
    # correct order
    new_compound = c_ast.Compound([], switch_node.stmt.coord)

    # The last Case/Default node
    last_case = None

    # Goes over the children of the Compound below the Switch, adding them
    # either directly below new_compound or below the last Case as appropriate
    # (for `switch(cond) {}`, block_items would have been None)
    for child in (switch_node.stmt.block_items or []):
        if isinstance(child, (c_ast.Case, c_ast.Default)):
            # If it's a Case/Default:
            # 1. Add it to the Compound and mark as "last case"
            # 2. If its immediate child is also a Case or Default, promote it
            #    to a sibling.
            new_compound.block_items.append(child)
            _extract_nested_case(child, new_compound.block_items)
            last_case = new_compound.block_items[-1]
        else:
            # Other statements are added as children to the last case, if it
            # exists.
            if last_case is None:
                new_compound.block_items.append(child)
            else:
                last_case.stmts.append(child)

    switch_node.stmt = new_compound
    return switch_node


def _extract_nested_case(case_node, stmts_list):
    """ Recursively extract consecutive Case statements that are made nested
        by the parser and add them to the stmts_list.
    """
    if isinstance(case_node.stmts[0], (c_ast.Case, c_ast.Default)):
        stmts_list.append(case_node.stmts.pop())
        _extract_nested_case(stmts_list[-1], stmts_list)


def fix_atomic_specifiers(decl):
    """ Atomic specifiers like _Atomic(type) are unusually structured,
        conferring a qualifier upon the contained type.

        This function fixes a decl with atomic specifiers to have a sane AST
        structure, by removing spurious Typename->TypeDecl pairs and attaching
        the _Atomic qualifier in the right place.
    """
    # There can be multiple levels of _Atomic in a decl; fix them until a
    # fixed point is reached.
    while True:
        decl, found = _fix_atomic_specifiers_once(decl)
        if not found:
            break

    # Make sure to add an _Atomic qual on the topmost decl if needed. Also
    # restore the declname on the innermost TypeDecl (it gets placed in the
    # wrong place during construction).
    typ = decl
    while not isinstance(typ, c_ast.TypeDecl):
        try:
            typ = typ.type
        except AttributeError:
            return decl
    if '_Atomic' in typ.quals and '_Atomic' not in decl.quals:
        decl.quals.append('_Atomic')
    if typ.declname is None:
        typ.declname = decl.name

    return decl


def _fix_atomic_specifiers_once(decl):
    """ Performs one 'fix' round of atomic specifiers.
        Returns (modified_decl, found) where found is True iff a fix was made.
    """
    parent = decl
    grandparent = None
    node = decl.type
    while node is not None:
        if isinstance(node, c_ast.Typename) and '_Atomic' in node.quals:
            break
        try:
            grandparent = parent
            parent = node
            node = node.type
        except AttributeError:
            # If we've reached a node without a `type` field, it means we won't
            # find what we're looking for at this point; give up the search
            # and return the original decl unmodified.
            return decl, False

    assert isinstance(parent, c_ast.TypeDecl)
    grandparent.type = node.type
    if '_Atomic' not in node.type.quals:
        node.type.quals.append('_Atomic')
    return decl, True

# === NexusCore/openenv\Lib\site-packages\debugpy\common\util.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import inspect
import os
import sys


def evaluate(code, path=__file__, mode="eval"):
    # Setting file path here to avoid breaking here if users have set
    # "break on exception raised" setting. This code can potentially run
    # in user process and is indistinguishable if the path is not set.
    # We use the path internally to skip exception inside the debugger.
    expr = compile(code, path, "eval")
    return eval(expr, {}, sys.modules)


class Observable(object):
    """An object with change notifications."""

    observers = ()  # used when attributes are set before __init__ is invoked

    def __init__(self):
        self.observers = []

    def __setattr__(self, name, value):
        try:
            return super().__setattr__(name, value)
        finally:
            for ob in self.observers:
                ob(self, name)


class Env(dict):
    """A dict for environment variables."""

    @staticmethod
    def snapshot():
        """Returns a snapshot of the current environment."""
        return Env(os.environ)

    def copy(self, updated_from=None):
        result = Env(self)
        if updated_from is not None:
            result.update(updated_from)
        return result

    def prepend_to(self, key, entry):
        """Prepends a new entry to a PATH-style environment variable, creating
        it if it doesn't exist already.
        """
        try:
            tail = os.path.pathsep + self[key]
        except KeyError:
            tail = ""
        self[key] = entry + tail


def force_str(s, encoding, errors="strict"):
    """Converts s to str, using the provided encoding. If s is already str,
    it is returned as is.
    """
    return s.decode(encoding, errors) if isinstance(s, bytes) else str(s)


def force_bytes(s, encoding, errors="strict"):
    """Converts s to bytes, using the provided encoding. If s is already bytes,
    it is returned as is.

    If errors="strict" and s is bytes, its encoding is verified by decoding it;
    UnicodeError is raised if it cannot be decoded.
    """
    if isinstance(s, str):
        return s.encode(encoding, errors)
    else:
        s = bytes(s)
        if errors == "strict":
            # Return value ignored - invoked solely for verification.
            s.decode(encoding, errors)
        return s


def force_ascii(s, errors="strict"):
    """Same as force_bytes(s, "ascii", errors)"""
    return force_bytes(s, "ascii", errors)


def force_utf8(s, errors="strict"):
    """Same as force_bytes(s, "utf8", errors)"""
    return force_bytes(s, "utf8", errors)


def nameof(obj, quote=False):
    """Returns the most descriptive name of a Python module, class, or function,
    as a Unicode string

    If quote=True, name is quoted with repr().

    Best-effort, but guaranteed to not fail - always returns something.
    """

    try:
        name = obj.__qualname__
    except Exception:
        try:
            name = obj.__name__
        except Exception:
            # Fall back to raw repr(), and skip quoting.
            try:
                name = repr(obj)
            except Exception:
                return "<unknown>"
            else:
                quote = False

    if quote:
        try:
            name = repr(name)
        except Exception:
            pass

    return force_str(name, "utf-8", "replace")


def srcnameof(obj):
    """Returns the most descriptive name of a Python module, class, or function,
    including source information (filename and linenumber), if available.

    Best-effort, but guaranteed to not fail - always returns something.
    """

    name = nameof(obj, quote=True)

    # Get the source information if possible.
    try:
        src_file = inspect.getsourcefile(obj)
    except Exception:
        pass
    else:
        name += f" (file {src_file!r}"
        try:
            _, src_lineno = inspect.getsourcelines(obj)
        except Exception:
            pass
        else:
            name += f", line {src_lineno}"
        name += ")"

    return name


def hide_debugpy_internals():
    """Returns True if the caller should hide something from debugpy."""
    return "DEBUGPY_TRACE_DEBUGPY" not in os.environ


def hide_thread_from_debugger(thread):
    """Disables tracing for the given thread if DEBUGPY_TRACE_DEBUGPY is not set.
    DEBUGPY_TRACE_DEBUGPY is used to debug debugpy with debugpy
    """
    if hide_debugpy_internals():
        thread.pydev_do_not_trace = True
        thread.is_pydev_daemon_thread = True

# === NexusCore/openenv\Lib\site-packages\gitdb\test\test_stream.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Test for object db"""

from gitdb.test.lib import (
    TestBase,
    DummyStream,
    make_bytes,
    make_object,
    fixture_path
)

from gitdb import (
    DecompressMemMapReader,
    FDCompressedSha1Writer,
    LooseObjectDB,
    Sha1Writer,
    MemoryDB,
    IStream,
)
from gitdb.util import hex_to_bin

import zlib
from gitdb.typ import (
    str_blob_type
)

import tempfile
import os
from io import BytesIO


class TestStream(TestBase):

    """Test stream classes"""

    data_sizes = (15, 10000, 1000 * 1024 + 512)

    def _assert_stream_reader(self, stream, cdata, rewind_stream=lambda s: None):
        """Make stream tests - the orig_stream is seekable, allowing it to be
        rewound and reused
        :param cdata: the data we expect to read from stream, the contents
        :param rewind_stream: function called to rewind the stream to make it ready
            for reuse"""
        ns = 10
        assert len(cdata) > ns - 1, "Data must be larger than %i, was %i" % (ns, len(cdata))

        # read in small steps
        ss = len(cdata) // ns
        for i in range(ns):
            data = stream.read(ss)
            chunk = cdata[i * ss:(i + 1) * ss]
            assert data == chunk
        # END for each step
        rest = stream.read()
        if rest:
            assert rest == cdata[-len(rest):]
        # END handle rest

        if isinstance(stream, DecompressMemMapReader):
            assert len(stream.data()) == stream.compressed_bytes_read()
        # END handle special type

        rewind_stream(stream)

        # read everything
        rdata = stream.read()
        assert rdata == cdata

        if isinstance(stream, DecompressMemMapReader):
            assert len(stream.data()) == stream.compressed_bytes_read()
        # END handle special type

    def test_decompress_reader(self):
        for close_on_deletion in range(2):
            for with_size in range(2):
                for ds in self.data_sizes:
                    cdata = make_bytes(ds, randomize=False)

                    # zdata = zipped actual data
                    # cdata = original content data

                    # create reader
                    if with_size:
                        # need object data
                        zdata = zlib.compress(make_object(str_blob_type, cdata))
                        typ, size, reader = DecompressMemMapReader.new(zdata, close_on_deletion)
                        assert size == len(cdata)
                        assert typ == str_blob_type

                        # even if we don't set the size, it will be set automatically on first read
                        test_reader = DecompressMemMapReader(zdata, close_on_deletion=False)
                        assert test_reader._s == len(cdata)
                    else:
                        # here we need content data
                        zdata = zlib.compress(cdata)
                        reader = DecompressMemMapReader(zdata, close_on_deletion, len(cdata))
                        assert reader._s == len(cdata)
                    # END get reader

                    self._assert_stream_reader(reader, cdata, lambda r: r.seek(0))

                    # put in a dummy stream for closing
                    dummy = DummyStream()
                    reader._m = dummy

                    assert not dummy.closed
                    del(reader)
                    assert dummy.closed == close_on_deletion
                # END for each datasize
            # END whether size should be used
        # END whether stream should be closed when deleted

    def test_sha_writer(self):
        writer = Sha1Writer()
        assert 2 == writer.write(b"hi")
        assert len(writer.sha(as_hex=1)) == 40
        assert len(writer.sha(as_hex=0)) == 20

        # make sure it does something ;)
        prev_sha = writer.sha()
        writer.write(b"hi again")
        assert writer.sha() != prev_sha

    def test_compressed_writer(self):
        for ds in self.data_sizes:
            fd, path = tempfile.mkstemp()
            ostream = FDCompressedSha1Writer(fd)
            data = make_bytes(ds, randomize=False)

            # for now, just a single write, code doesn't care about chunking
            assert len(data) == ostream.write(data)
            ostream.close()

            # its closed already
            self.assertRaises(OSError, os.close, fd)

            # read everything back, compare to data we zip
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0))
            written_data = os.read(fd, os.path.getsize(path))
            assert len(written_data) == os.path.getsize(path)
            os.close(fd)
            assert written_data == zlib.compress(data, 1)   # best speed

            os.remove(path)
        # END for each os

    def test_decompress_reader_special_case(self):
        odb = LooseObjectDB(fixture_path('objects'))
        mdb = MemoryDB()
        for sha in (b'888401851f15db0eed60eb1bc29dec5ddcace911',
                    b'7bb839852ed5e3a069966281bb08d50012fb309b',):
            ostream = odb.stream(hex_to_bin(sha))

            # if there is a bug, we will be missing one byte exactly !
            data = ostream.read()
            assert len(data) == ostream.size

            # Putting it back in should yield nothing new - after all, we have
            dump = mdb.store(IStream(ostream.type, ostream.size, BytesIO(data)))
            assert dump.hexsha == sha
        # end for each loose object sha to test

# === NexusCore/openenv\Lib\site-packages\google\auth\_exponential_backoff.py ===
# Copyright 2022 Google LLC
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

import asyncio
import random
import time

from google.auth import exceptions

# The default amount of retry attempts
_DEFAULT_RETRY_TOTAL_ATTEMPTS = 3

# The default initial backoff period (1.0 second).
_DEFAULT_INITIAL_INTERVAL_SECONDS = 1.0

# The default randomization factor (0.1 which results in a random period ranging
# between 10% below and 10% above the retry interval).
_DEFAULT_RANDOMIZATION_FACTOR = 0.1

# The default multiplier value (2 which is 100% increase per back off).
_DEFAULT_MULTIPLIER = 2.0

"""Exponential Backoff Utility

This is a private module that implements the exponential back off algorithm.
It can be used as a utility for code that needs to retry on failure, for example
an HTTP request.
"""


class _BaseExponentialBackoff:
    """An exponential backoff iterator base class.

    Args:
        total_attempts Optional[int]:
            The maximum amount of retries that should happen.
            The default value is 3 attempts.
        initial_wait_seconds Optional[int]:
            The amount of time to sleep in the first backoff. This parameter
            should be in seconds.
            The default value is 1 second.
        randomization_factor Optional[float]:
            The amount of jitter that should be in each backoff. For example,
            a value of 0.1 will introduce a jitter range of 10% to the
            current backoff period.
            The default value is 0.1.
        multiplier Optional[float]:
            The backoff multipler. This adjusts how much each backoff will
            increase. For example a value of 2.0 leads to a 200% backoff
            on each attempt. If the initial_wait is 1.0 it would look like
            this sequence [1.0, 2.0, 4.0, 8.0].
            The default value is 2.0.
    """

    def __init__(
        self,
        total_attempts=_DEFAULT_RETRY_TOTAL_ATTEMPTS,
        initial_wait_seconds=_DEFAULT_INITIAL_INTERVAL_SECONDS,
        randomization_factor=_DEFAULT_RANDOMIZATION_FACTOR,
        multiplier=_DEFAULT_MULTIPLIER,
    ):
        if total_attempts < 1:
            raise exceptions.InvalidValue(
                f"total_attempts must be greater than or equal to 1 but was {total_attempts}"
            )

        self._total_attempts = total_attempts
        self._initial_wait_seconds = initial_wait_seconds

        self._current_wait_in_seconds = self._initial_wait_seconds

        self._randomization_factor = randomization_factor
        self._multiplier = multiplier
        self._backoff_count = 0

    @property
    def total_attempts(self):
        """The total amount of backoff attempts that will be made."""
        return self._total_attempts

    @property
    def backoff_count(self):
        """The current amount of backoff attempts that have been made."""
        return self._backoff_count

    def _reset(self):
        self._backoff_count = 0
        self._current_wait_in_seconds = self._initial_wait_seconds

    def _calculate_jitter(self):
        jitter_variance = self._current_wait_in_seconds * self._randomization_factor
        jitter = random.uniform(
            self._current_wait_in_seconds - jitter_variance,
            self._current_wait_in_seconds + jitter_variance,
        )

        return jitter


class ExponentialBackoff(_BaseExponentialBackoff):
    """An exponential backoff iterator. This can be used in a for loop to
    perform requests with exponential backoff.
    """

    def __init__(self, *args, **kwargs):
        super(ExponentialBackoff, self).__init__(*args, **kwargs)

    def __iter__(self):
        self._reset()
        return self

    def __next__(self):
        if self._backoff_count >= self._total_attempts:
            raise StopIteration
        self._backoff_count += 1

        if self._backoff_count <= 1:
            return self._backoff_count

        jitter = self._calculate_jitter()

        time.sleep(jitter)

        self._current_wait_in_seconds *= self._multiplier
        return self._backoff_count


class AsyncExponentialBackoff(_BaseExponentialBackoff):
    """An async exponential backoff iterator. This can be used in a for loop to
    perform async requests with exponential backoff.
    """

    def __init__(self, *args, **kwargs):
        super(AsyncExponentialBackoff, self).__init__(*args, **kwargs)

    def __aiter__(self):
        self._reset()
        return self

    async def __anext__(self):
        if self._backoff_count >= self._total_attempts:
            raise StopAsyncIteration
        self._backoff_count += 1

        if self._backoff_count <= 1:
            return self._backoff_count

        jitter = self._calculate_jitter()

        await asyncio.sleep(jitter)

        self._current_wait_in_seconds *= self._multiplier
        return self._backoff_count

# === NexusCore/openenv\Lib\site-packages\google\auth\_jwt_async.py ===
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

"""JSON Web Tokens

Provides support for creating (encoding) and verifying (decoding) JWTs,
especially JWTs generated and consumed by Google infrastructure.

See `rfc7519`_ for more details on JWTs.

To encode a JWT use :func:`encode`::

    from google.auth import crypt
    from google.auth import jwt_async

    signer = crypt.Signer(private_key)
    payload = {'some': 'payload'}
    encoded = jwt_async.encode(signer, payload)

To decode a JWT and verify claims use :func:`decode`::

    claims = jwt_async.decode(encoded, certs=public_certs)

You can also skip verification::

    claims = jwt_async.decode(encoded, verify=False)

.. _rfc7519: https://tools.ietf.org/html/rfc7519


NOTE: This async support is experimental and marked internal. This surface may
change in minor releases.
"""

from google.auth import _credentials_async
from google.auth import jwt


def encode(signer, payload, header=None, key_id=None):
    """Make a signed JWT.

    Args:
        signer (google.auth.crypt.Signer): The signer used to sign the JWT.
        payload (Mapping[str, str]): The JWT payload.
        header (Mapping[str, str]): Additional JWT header payload.
        key_id (str): The key id to add to the JWT header. If the
            signer has a key id it will be used as the default. If this is
            specified it will override the signer's key id.

    Returns:
        bytes: The encoded JWT.
    """
    return jwt.encode(signer, payload, header, key_id)


def decode(token, certs=None, verify=True, audience=None):
    """Decode and verify a JWT.

    Args:
        token (str): The encoded JWT.
        certs (Union[str, bytes, Mapping[str, Union[str, bytes]]]): The
            certificate used to validate the JWT signature. If bytes or string,
            it must the the public key certificate in PEM format. If a mapping,
            it must be a mapping of key IDs to public key certificates in PEM
            format. The mapping must contain the same key ID that's specified
            in the token's header.
        verify (bool): Whether to perform signature and claim validation.
            Verification is done by default.
        audience (str): The audience claim, 'aud', that this JWT should
            contain. If None then the JWT's 'aud' parameter is not verified.

    Returns:
        Mapping[str, str]: The deserialized JSON payload in the JWT.

    Raises:
        ValueError: if any verification checks failed.
    """

    return jwt.decode(token, certs, verify, audience)


class Credentials(
    jwt.Credentials, _credentials_async.Signing, _credentials_async.Credentials
):
    """Credentials that use a JWT as the bearer token.

    These credentials require an "audience" claim. This claim identifies the
    intended recipient of the bearer token.

    The constructor arguments determine the claims for the JWT that is
    sent with requests. Usually, you'll construct these credentials with
    one of the helper constructors as shown in the next section.

    To create JWT credentials using a Google service account private key
    JSON file::

        audience = 'https://pubsub.googleapis.com/google.pubsub.v1.Publisher'
        credentials = jwt_async.Credentials.from_service_account_file(
            'service-account.json',
            audience=audience)

    If you already have the service account file loaded and parsed::

        service_account_info = json.load(open('service_account.json'))
        credentials = jwt_async.Credentials.from_service_account_info(
            service_account_info,
            audience=audience)

    Both helper methods pass on arguments to the constructor, so you can
    specify the JWT claims::

        credentials = jwt_async.Credentials.from_service_account_file(
            'service-account.json',
            audience=audience,
            additional_claims={'meta': 'data'})

    You can also construct the credentials directly if you have a
    :class:`~google.auth.crypt.Signer` instance::

        credentials = jwt_async.Credentials(
            signer,
            issuer='your-issuer',
            subject='your-subject',
            audience=audience)

    The claims are considered immutable. If you want to modify the claims,
    you can easily create another instance using :meth:`with_claims`::

        new_audience = (
            'https://pubsub.googleapis.com/google.pubsub.v1.Subscriber')
        new_credentials = credentials.with_claims(audience=new_audience)
    """


class OnDemandCredentials(
    jwt.OnDemandCredentials, _credentials_async.Signing, _credentials_async.Credentials
):
    """On-demand JWT credentials.

    Like :class:`Credentials`, this class uses a JWT as the bearer token for
    authentication. However, this class does not require the audience at
    construction time. Instead, it will generate a new token on-demand for
    each request using the request URI as the audience. It caches tokens
    so that multiple requests to the same URI do not incur the overhead
    of generating a new token every time.

    This behavior is especially useful for `gRPC`_ clients. A gRPC service may
    have multiple audience and gRPC clients may not know all of the audiences
    required for accessing a particular service. With these credentials,
    no knowledge of the audiences is required ahead of time.

    .. _grpc: http://www.grpc.io/
    """

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\command_utils.py ===
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
"""Utilities for Commands.

Common methods for Commands such as RunCommand and CompileCommand.
"""
from __future__ import annotations

from typing import AbstractSet, Any, Callable, Sequence

from google.generativeai.notebook import ipython_env
from google.generativeai.notebook import model_registry
from google.generativeai.notebook import parsed_args_lib
from google.generativeai.notebook import post_process_utils
from google.generativeai.notebook.lib import llm_function
from google.generativeai.notebook.lib import llmfn_input_utils
from google.generativeai.notebook.lib import llmfn_output_row
from google.generativeai.notebook.lib import llmfn_outputs
from google.generativeai.notebook.lib import unique_fn


class _GroundTruthLLMFunction(llm_function.LLMFunction):
    """LLMFunction that returns pre-generated ground truth data."""

    def __init__(self, data: Sequence[str]):
        super().__init__(outputs_ipython_display_fn=None)
        self._data = data

    def get_placeholders(self) -> AbstractSet[str]:
        # Ground truth is fixed and thus has no placeholders.
        return frozenset({})

    def _call_impl(
        self, inputs: llmfn_input_utils.LLMFunctionInputs | None
    ) -> Sequence[llmfn_outputs.LLMFnOutputEntry]:
        normalized_inputs = llmfn_input_utils.to_normalized_inputs(inputs)
        if len(self._data) != len(normalized_inputs):
            raise RuntimeError(
                "Ground truth should have same number of entries as inputs: {} vs {}".format(
                    len(self._data), len(normalized_inputs)
                )
            )

        outputs: list[llmfn_outputs.LLMFnOutputEntry] = []
        for idx, (value, prompt_vars) in enumerate(zip(self._data, normalized_inputs)):
            output_row = llmfn_output_row.LLMFnOutputRow(
                data={
                    llmfn_outputs.ColumnNames.RESULT_NUM: 0,
                    llmfn_outputs.ColumnNames.TEXT_RESULT: value,
                },
                result_type=str,
            )
            outputs.append(
                llmfn_outputs.LLMFnOutputEntry(
                    prompt_num=0,
                    input_num=idx,
                    prompt_vars=prompt_vars,
                    output_rows=[output_row],
                )
            )
        return outputs


def _get_ipython_display_fn(
    env: ipython_env.IPythonEnv,
) -> Callable[[llmfn_outputs.LLMFnOutputs], None]:
    return lambda x: env.display(x.as_pandas_dataframe())


def create_llm_function(
    models: model_registry.ModelRegistry,
    env: ipython_env.IPythonEnv | None,
    parsed_args: parsed_args_lib.ParsedArgs,
    cell_content: str,
    post_processing_fns: Sequence[post_process_utils.ParsedPostProcessExpr],
) -> llm_function.LLMFunction:
    """Creates an LLMFunction from Command.execute() arguments."""
    prompts: list[str] = [cell_content]

    llmfn_outputs_display_fn = _get_ipython_display_fn(env) if env else None

    llm_fn = llm_function.LLMFunctionImpl(
        model=models.get_model(parsed_args.model_type),
        model_args=parsed_args.model_args,
        prompts=prompts,
        outputs_ipython_display_fn=llmfn_outputs_display_fn,
    )
    if parsed_args.unique:
        llm_fn = llm_fn.add_post_process_reorder_fn(name="unique", fn=unique_fn.unique_fn)
    for fn in post_processing_fns:
        llm_fn = fn.add_to_llm_function(llm_fn)

    return llm_fn


def _convert_simple_compare_fn(
    name_and_simple_fn: tuple[str, Callable[[str, str], Any]]
) -> tuple[str, llm_function.CompareFn]:
    simple_fn = name_and_simple_fn[1]
    new_fn = lambda x, y: simple_fn(x.result_value(), y.result_value())
    return name_and_simple_fn[0], new_fn


def create_llm_compare_function(
    env: ipython_env.IPythonEnv | None,
    parsed_args: parsed_args_lib.ParsedArgs,
    post_processing_fns: Sequence[post_process_utils.ParsedPostProcessExpr],
) -> llm_function.LLMFunction:
    """Creates an LLMCompareFunction from Command.execute() arguments."""
    llmfn_outputs_display_fn = _get_ipython_display_fn(env) if env else None

    llm_cmp_fn = llm_function.LLMCompareFunction(
        lhs_name_and_fn=parsed_args.lhs_name_and_fn,
        rhs_name_and_fn=parsed_args.rhs_name_and_fn,
        compare_name_and_fns=[_convert_simple_compare_fn(x) for x in parsed_args.compare_fn],
        outputs_ipython_display_fn=llmfn_outputs_display_fn,
    )
    for fn in post_processing_fns:
        llm_cmp_fn = fn.add_to_llm_function(llm_cmp_fn)

    return llm_cmp_fn


def create_llm_eval_function(
    models: model_registry.ModelRegistry,
    env: ipython_env.IPythonEnv | None,
    parsed_args: parsed_args_lib.ParsedArgs,
    cell_content: str,
    post_processing_fns: Sequence[post_process_utils.ParsedPostProcessExpr],
) -> llm_function.LLMFunction:
    """Creates an LLMCompareFunction from Command.execute() arguments."""
    llmfn_outputs_display_fn = _get_ipython_display_fn(env) if env else None

    # First construct a regular LLMFunction from the cell contents.
    llm_fn = create_llm_function(
        models=models,
        env=env,
        parsed_args=parsed_args,
        cell_content=cell_content,
        post_processing_fns=post_processing_fns,
    )

    # Next create a LLMCompareFunction.
    ground_truth_fn = _GroundTruthLLMFunction(data=parsed_args.ground_truth)
    llm_cmp_fn = llm_function.LLMCompareFunction(
        lhs_name_and_fn=("actual", llm_fn),
        rhs_name_and_fn=("ground_truth", ground_truth_fn),
        compare_name_and_fns=[_convert_simple_compare_fn(x) for x in parsed_args.compare_fn],
        outputs_ipython_display_fn=llmfn_outputs_display_fn,
    )

    return llm_cmp_fn

# === NexusCore/openenv\Lib\site-packages\litellm\experimental_mcp_client\client.py ===
"""
LiteLLM Proxy uses this MCP Client to connnect to other MCP servers.
"""
import base64
from datetime import timedelta
from typing import List, Optional

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolRequestParams as MCPCallToolRequestParams
from mcp.types import CallToolResult as MCPCallToolResult
from mcp.types import Tool as MCPTool

from litellm.types.mcp import MCPAuth, MCPAuthType, MCPTransport, MCPTransportType


def to_basic_auth(auth_value: str) -> str:
    """Convert auth value to Basic Auth format."""
    return base64.b64encode(auth_value.encode("utf-8")).decode()


class MCPClient:
    """
    MCP Client supporting:
      SSE and HTTP transports
      Authentication via Bearer token, Basic Auth, or API Key
      Tool calling with error handling and result parsing
    """

    def __init__(
        self,
        server_url: str,
        transport_type: MCPTransportType = MCPTransport.http,
        auth_type: MCPAuthType = None,
        auth_value: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.server_url: str = server_url
        self.transport_type: MCPTransport = transport_type
        self.auth_type: MCPAuthType = auth_type
        self.timeout: float = timeout
        self._mcp_auth_value: Optional[str] = None
        self._session: Optional[ClientSession] = None
        self._context = None
        self._transport_ctx = None
        self._transport = None
        self._session_ctx = None

        # handle the basic auth value if provided
        if auth_value:
            self.update_auth_value(auth_value)

    async def __aenter__(self):
        """
        Enable async context manager support.
          Initializes the transport and session.
        """
        await self.connect()
        return self

    async def connect(self):
        """Initialize the transport and session."""
        if self._session:
            return  # Already connected
            
        headers = self._get_auth_headers()

        if self.transport_type == MCPTransport.sse:
            self._transport_ctx = sse_client(
                url=self.server_url,
                timeout=self.timeout,
                headers=headers,
            )
            self._transport = await self._transport_ctx.__aenter__()
            self._session_ctx = ClientSession(self._transport[0], self._transport[1])
            self._session = await self._session_ctx.__aenter__()
            await self._session.initialize()
        else:
            self._transport_ctx = streamablehttp_client(
                url=self.server_url,
                timeout=timedelta(seconds=self.timeout),
                headers=headers,
            )
            self._transport = await self._transport_ctx.__aenter__()
            self._session_ctx = ClientSession(self._transport[0], self._transport[1])
            self._session = await self._session_ctx.__aenter__()
            await self._session.initialize()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context manager."""
        if self._session:
            await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb) # type: ignore
        if self._transport_ctx:
            await self._transport_ctx.__aexit__(exc_type, exc_val, exc_tb)

    async def disconnect(self):
        """Clean up session and connections."""
        if self._session:
            try:
                # Ensure session is properly closed
                await self._session.close()  # type: ignore 
            except Exception:
                pass
            self._session = None

        if self._context:
            try:
                await self._context.__aexit__(None, None, None) # type: ignore
            except Exception:
                pass
            self._context = None

    def update_auth_value(self, mcp_auth_value: str):
        """
        Set the authentication header for the MCP client.
        """
        if self.auth_type == MCPAuth.basic:
            # Assuming mcp_auth_value is in format "username:password", convert it when updating
            mcp_auth_value = to_basic_auth(mcp_auth_value)
        self._mcp_auth_value = mcp_auth_value

    def _get_auth_headers(self) -> dict:
        """Generate authentication headers based on auth type."""
        if not self._mcp_auth_value:
            return {}

        if self.auth_type == MCPAuth.bearer_token:
            return {"Authorization": f"Bearer {self._mcp_auth_value}"}
        elif self.auth_type == MCPAuth.basic:
            return {"Authorization": f"Basic {self._mcp_auth_value}"}
        elif self.auth_type == MCPAuth.api_key:
            return {"X-API-Key": self._mcp_auth_value}
        return {}

    async def list_tools(self) -> List[MCPTool]:
        """List available tools from the server."""
        if not self._session:
            await self.connect()
        if self._session is None:
            raise ValueError("Session is not initialized")

        result = await self._session.list_tools()
        return result.tools

    async def call_tool(
        self, call_tool_request_params: MCPCallToolRequestParams
    ) -> MCPCallToolResult:
        """
        Call an MCP Tool.
        """
        if not self._session:
            await self.connect()

        if self._session is None:
            raise ValueError("Session is not initialized")
        
        tool_result = await self._session.call_tool(
            name=call_tool_request_params.name,
            arguments=call_tool_request_params.arguments,
        )
        return tool_result
        


# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\logging_utils.py ===
import asyncio
import functools
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Union

from litellm._logging import verbose_logger
from litellm.types.utils import (
    ModelResponse,
    ModelResponseStream,
    TextCompletionResponse,
)

if TYPE_CHECKING:
    from litellm import ModelResponse as _ModelResponse
    from litellm.litellm_core_utils.litellm_logging import (
        Logging as LiteLLMLoggingObject,
    )

    LiteLLMModelResponse = _ModelResponse
else:
    LiteLLMModelResponse = Any
    LiteLLMLoggingObject = Any


import litellm

"""
Helper utils used for logging callbacks
"""


def convert_litellm_response_object_to_str(
    response_obj: Union[Any, LiteLLMModelResponse]
) -> Optional[str]:
    """
    Get the string of the response object from LiteLLM

    """
    if isinstance(response_obj, litellm.ModelResponse):
        response_str = ""
        for choice in response_obj.choices:
            if isinstance(choice, litellm.Choices):
                if choice.message.content and isinstance(choice.message.content, str):
                    response_str += choice.message.content
        return response_str

    return None


def _assemble_complete_response_from_streaming_chunks(
    result: Union[ModelResponse, TextCompletionResponse, ModelResponseStream],
    start_time: datetime,
    end_time: datetime,
    request_kwargs: dict,
    streaming_chunks: List[Any],
    is_async: bool,
):
    """
    Assemble a complete response from a streaming chunks

    - assemble a complete streaming response if result.choices[0].finish_reason is not None
    - else append the chunk to the streaming_chunks


    Args:
        result: ModelResponse
        start_time: datetime
        end_time: datetime
        request_kwargs: dict
        streaming_chunks: List[Any]
        is_async: bool

    Returns:
        Optional[Union[ModelResponse, TextCompletionResponse]]: Complete streaming response

    """
    complete_streaming_response: Optional[
        Union[ModelResponse, TextCompletionResponse]
    ] = None

    if isinstance(result, ModelResponse):
        return result

    if result.choices[0].finish_reason is not None:  # if it's the last chunk
        streaming_chunks.append(result)
        try:
            complete_streaming_response = litellm.stream_chunk_builder(
                chunks=streaming_chunks,
                messages=request_kwargs.get("messages", None),
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            log_message = (
                "Error occurred building stream chunk in {} success logging: {}".format(
                    "async" if is_async else "sync", str(e)
                )
            )
            verbose_logger.exception(log_message)
            complete_streaming_response = None
    else:
        streaming_chunks.append(result)
    return complete_streaming_response


def _set_duration_in_model_call_details(
    logging_obj: Any,  # we're not guaranteed this will be `LiteLLMLoggingObject`
    start_time: datetime,
    end_time: datetime,
):
    """Helper to set duration in model_call_details, with error handling"""
    try:
        duration_ms = (end_time - start_time).total_seconds() * 1000
        if logging_obj and hasattr(logging_obj, "model_call_details"):
            logging_obj.model_call_details["llm_api_duration_ms"] = duration_ms
        else:
            verbose_logger.debug(
                "`logging_obj` not found - unable to track `llm_api_duration_ms"
            )
    except Exception as e:
        verbose_logger.warning(f"Error setting `llm_api_duration_ms`: {str(e)}")


def track_llm_api_timing():
    """
    Decorator to track LLM API call timing for both sync and async functions.
    The logging_obj is expected to be passed as an argument to the decorated function.
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = datetime.now()
                _set_duration_in_model_call_details(
                    logging_obj=kwargs.get("logging_obj", None),
                    start_time=start_time,
                    end_time=end_time,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = datetime.now()
                _set_duration_in_model_call_details(
                    logging_obj=kwargs.get("logging_obj", None),
                    start_time=start_time,
                    end_time=end_time,
                )

        # Check if the function is async or sync
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

# === NexusCore/openenv\Lib\site-packages\openai\cli\_tools\migrate.py ===
from __future__ import annotations

import os
import sys
import shutil
import tarfile
import platform
import subprocess
from typing import TYPE_CHECKING, List
from pathlib import Path
from argparse import ArgumentParser

import httpx

from .._errors import CLIError, SilentCLIError
from .._models import BaseModel

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register(subparser: _SubParsersAction[ArgumentParser]) -> None:
    sub = subparser.add_parser("migrate")
    sub.set_defaults(func=migrate, args_model=MigrateArgs, allow_unknown_args=True)

    sub = subparser.add_parser("grit")
    sub.set_defaults(func=grit, args_model=GritArgs, allow_unknown_args=True)


class GritArgs(BaseModel):
    # internal
    unknown_args: List[str] = []


def grit(args: GritArgs) -> None:
    grit_path = install()

    try:
        subprocess.check_call([grit_path, *args.unknown_args])
    except subprocess.CalledProcessError:
        # stdout and stderr are forwarded by subprocess so an error will already
        # have been displayed
        raise SilentCLIError() from None


class MigrateArgs(BaseModel):
    # internal
    unknown_args: List[str] = []


def migrate(args: MigrateArgs) -> None:
    grit_path = install()

    try:
        subprocess.check_call([grit_path, "apply", "openai", *args.unknown_args])
    except subprocess.CalledProcessError:
        # stdout and stderr are forwarded by subprocess so an error will already
        # have been displayed
        raise SilentCLIError() from None


# handles downloading the Grit CLI until they provide their own PyPi package

KEYGEN_ACCOUNT = "custodian-dev"


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg is not None:
        return Path(xdg)

    return Path.home() / ".cache"


def _debug(message: str) -> None:
    if not os.environ.get("DEBUG"):
        return

    sys.stdout.write(f"[DEBUG]: {message}\n")


def install() -> Path:
    """Installs the Grit CLI and returns the location of the binary"""
    if sys.platform == "win32":
        raise CLIError("Windows is not supported yet in the migration CLI")

    _debug("Using Grit installer from GitHub")

    platform = "apple-darwin" if sys.platform == "darwin" else "unknown-linux-gnu"

    dir_name = _cache_dir() / "openai-python"
    install_dir = dir_name / ".install"
    target_dir = install_dir / "bin"

    target_path = target_dir / "grit"
    temp_file = target_dir / "grit.tmp"

    if target_path.exists():
        _debug(f"{target_path} already exists")
        sys.stdout.flush()
        return target_path

    _debug(f"Using Grit CLI path: {target_path}")

    target_dir.mkdir(parents=True, exist_ok=True)

    if temp_file.exists():
        temp_file.unlink()

    arch = _get_arch()
    _debug(f"Using architecture {arch}")

    file_name = f"grit-{arch}-{platform}"
    download_url = f"https://github.com/getgrit/gritql/releases/latest/download/{file_name}.tar.gz"

    sys.stdout.write(f"Downloading Grit CLI from {download_url}\n")
    with httpx.Client() as client:
        download_response = client.get(download_url, follow_redirects=True)
        if download_response.status_code != 200:
            raise CLIError(f"Failed to download Grit CLI from {download_url}")
        with open(temp_file, "wb") as file:
            for chunk in download_response.iter_bytes():
                file.write(chunk)

    unpacked_dir = target_dir / "cli-bin"
    unpacked_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(temp_file, "r:gz") as archive:
        if sys.version_info >= (3, 12):
            archive.extractall(unpacked_dir, filter="data")
        else:
            archive.extractall(unpacked_dir)

    _move_files_recursively(unpacked_dir, target_dir)

    shutil.rmtree(unpacked_dir)
    os.remove(temp_file)
    os.chmod(target_path, 0o755)

    sys.stdout.flush()

    return target_path


def _move_files_recursively(source_dir: Path, target_dir: Path) -> None:
    for item in source_dir.iterdir():
        if item.is_file():
            item.rename(target_dir / item.name)
        elif item.is_dir():
            _move_files_recursively(item, target_dir)


def _get_arch() -> str:
    architecture = platform.machine().lower()

    # Map the architecture names to Grit equivalents
    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "armv7l": "aarch64",
        "arm64": "aarch64",
    }

    return arch_map.get(architecture, architecture)

# === NexusCore/openenv\Lib\site-packages\traitlets\config\sphinxdoc.py ===
"""Machinery for documenting traitlets config options with Sphinx.

This includes:

- A Sphinx extension defining directives and roles for config options.
- A function to generate an rst file given an Application instance.

To make this documentation, first set this module as an extension in Sphinx's
conf.py::

    extensions = [
        # ...
        'traitlets.config.sphinxdoc',
    ]

Autogenerate the config documentation by running code like this before
Sphinx builds::

    from traitlets.config.sphinxdoc import write_doc
    from myapp import MyApplication

    writedoc('config/options.rst',    # File to write
             'MyApp config options',  # Title
             MyApplication()
            )

The generated rST syntax looks like this::

    .. configtrait:: Application.log_datefmt

        Description goes here.

    Cross reference like this: :configtrait:`Application.log_datefmt`.
"""
from __future__ import annotations

import typing as t
from collections import defaultdict
from textwrap import dedent

from traitlets import HasTraits, Undefined
from traitlets.config.application import Application
from traitlets.utils.text import indent


def setup(app: t.Any) -> dict[str, t.Any]:
    """Registers the Sphinx extension.

    You shouldn't need to call this directly; configure Sphinx to use this
    module instead.
    """
    app.add_object_type("configtrait", "configtrait", objname="Config option")
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def interesting_default_value(dv: t.Any) -> bool:
    if (dv is None) or (dv is Undefined):
        return False
    if isinstance(dv, (str, list, tuple, dict, set)):
        return bool(dv)
    return True


def format_aliases(aliases: list[str]) -> str:
    fmted = []
    for a in aliases:
        dashes = "-" if len(a) == 1 else "--"
        fmted.append(f"``{dashes}{a}``")
    return ", ".join(fmted)


def class_config_rst_doc(cls: type[HasTraits], trait_aliases: dict[str, t.Any]) -> str:
    """Generate rST documentation for this class' config options.

    Excludes traits defined on parent classes.
    """
    lines = []
    classname = cls.__name__
    for _, trait in sorted(cls.class_traits(config=True).items()):
        ttype = trait.__class__.__name__

        fullname = classname + "." + (trait.name or "")
        lines += [".. configtrait:: " + fullname, ""]

        help = trait.help.rstrip() or "No description"
        lines.append(indent(dedent(help)) + "\n")

        # Choices or type
        if "Enum" in ttype:
            # include Enum choices
            lines.append(indent(":options: " + ", ".join("``%r``" % x for x in trait.values)))  # type:ignore[attr-defined]
        else:
            lines.append(indent(":trait type: " + ttype))

        # Default value
        # Ignore boring default values like None, [] or ''
        if interesting_default_value(trait.default_value):
            try:
                dvr = trait.default_value_repr()
            except Exception:
                dvr = None  # ignore defaults we can't construct
            if dvr is not None:
                if len(dvr) > 64:
                    dvr = dvr[:61] + "..."
                # Double up backslashes, so they get to the rendered docs
                dvr = dvr.replace("\\n", "\\\\n")
                lines.append(indent(":default: ``%s``" % dvr))

        # Command line aliases
        if trait_aliases[fullname]:
            fmt_aliases = format_aliases(trait_aliases[fullname])
            lines.append(indent(":CLI option: " + fmt_aliases))

        # Blank line
        lines.append("")

    return "\n".join(lines)


def reverse_aliases(app: Application) -> dict[str, list[str]]:
    """Produce a mapping of trait names to lists of command line aliases."""
    res = defaultdict(list)
    for alias, trait in app.aliases.items():
        res[trait].append(alias)

    # Flags also often act as aliases for a boolean trait.
    # Treat flags which set one trait to True as aliases.
    for flag, (cfg, _) in app.flags.items():
        if len(cfg) == 1:
            classname = next(iter(cfg))
            cls_cfg = cfg[classname]
            if len(cls_cfg) == 1:
                traitname = next(iter(cls_cfg))
                if cls_cfg[traitname] is True:
                    res[classname + "." + traitname].append(flag)

    return res


def write_doc(path: str, title: str, app: Application, preamble: str | None = None) -> None:
    """Write a rst file documenting config options for a traitlets application.

    Parameters
    ----------
    path : str
        The file to be written
    title : str
        The human-readable title of the document
    app : traitlets.config.Application
        An instance of the application class to be documented
    preamble : str
        Extra text to add just after the title (optional)
    """
    trait_aliases = reverse_aliases(app)
    with open(path, "w") as f:
        f.write(title + "\n")
        f.write(("=" * len(title)) + "\n")
        f.write("\n")
        if preamble is not None:
            f.write(preamble + "\n\n")

        for c in app._classes_inc_parents():
            f.write(class_config_rst_doc(c, trait_aliases))
            f.write("\n")

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\core\driver_cache.py ===
import datetime
import json
import os

from webdriver_manager.core.config import wdm_local, get_xdist_worker_id
from webdriver_manager.core.constants import (
    DEFAULT_PROJECT_ROOT_CACHE_PATH,
    DEFAULT_USER_HOME_CACHE_PATH, ROOT_FOLDER_NAME,
)
from webdriver_manager.core.driver import Driver
from webdriver_manager.core.file_manager import FileManager, File
from webdriver_manager.core.logger import log
from webdriver_manager.core.os_manager import OperationSystemManager
from webdriver_manager.core.utils import get_date_diff


class DriverCacheManager(object):
    def __init__(self, root_dir=None, valid_range=1, file_manager=None):
        self._root_dir = DEFAULT_USER_HOME_CACHE_PATH
        is_wdm_local = wdm_local()
        xdist_worker_id = get_xdist_worker_id()
        if xdist_worker_id:
            log(f"xdist worker is: {xdist_worker_id}")
            self._root_dir = os.path.join(self._root_dir, xdist_worker_id)

        if root_dir:
            self._root_dir = os.path.join(root_dir, ROOT_FOLDER_NAME, xdist_worker_id)

        if is_wdm_local:
            self._root_dir = os.path.join(DEFAULT_PROJECT_ROOT_CACHE_PATH, xdist_worker_id)

        self._drivers_root = "drivers"
        self._drivers_json_path = os.path.join(self._root_dir, "drivers.json")
        self._date_format = "%d/%m/%Y"
        self._drivers_directory = os.path.join(self._root_dir, self._drivers_root)
        self._cache_valid_days_range = valid_range
        self._cache_key_driver_version = None
        self._metadata_key = None
        self._driver_binary_path = None
        self._file_manager = file_manager
        self._os_system_manager = OperationSystemManager()
        if not self._file_manager:
            self._file_manager = FileManager(self._os_system_manager)

    def save_archive_file(self, file: File, path):
        return self._file_manager.save_archive_file(file, path)

    def unpack_archive(self, archive, path):
        return self._file_manager.unpack_archive(archive, path)

    def save_file_to_cache(self, driver: Driver, file: File):
        path = self.__get_path(driver)
        archive = self.save_archive_file(file, path)
        files = self.unpack_archive(archive, path)
        binary = self.__get_binary(files, driver.get_name())
        binary_path = os.path.join(path, binary)
        self.__save_metadata(driver, binary_path)
        log(f"Driver has been saved in cache [{path}]")
        return binary_path

    def __get_binary(self, files, driver_name):
        if not files:
            raise Exception(f"Can't find binary for {driver_name} among {files}")

        if len(files) == 1:
            return files[0]

        for f in files:
            if 'LICENSE' in f:
                continue
            if 'THIRD_PARTY' in f:
                continue
            if driver_name in f:
                return f

        raise Exception(f"Can't find binary for {driver_name} among {files}")

    def __save_metadata(self, driver: Driver, binary_path, date=None):
        if date is None:
            date = datetime.date.today()

        metadata = self.load_metadata_content()
        key = self.__get_metadata_key(driver)
        data = {
            key: {
                "timestamp": date.strftime(self._date_format),
                "binary_path": binary_path,
            }
        }

        metadata.update(data)
        with open(self._drivers_json_path, "w+") as outfile:
            json.dump(metadata, outfile, indent=4)

    def get_os_type(self):
        return self._os_system_manager.get_os_type()

    def find_driver(self, driver: Driver):
        """Find driver by '{os_type}_{driver_name}_{driver_version}_{browser_version}'."""
        os_type = self.get_os_type()
        driver_name = driver.get_name()
        browser_type = driver.get_browser_type()
        browser_version = self._os_system_manager.get_browser_version_from_os(browser_type)
        if not browser_version:
            return None

        driver_version = self.get_cache_key_driver_version(driver)
        metadata = self.load_metadata_content()

        key = self.__get_metadata_key(driver)
        if key not in metadata:
            log(f'There is no [{os_type}] {driver_name} "{driver_version}" for browser {browser_type} '
                f'"{browser_version}" in cache')
            return None

        driver_info = metadata[key]
        path = driver_info["binary_path"]
        if not os.path.exists(path):
            return None

        if not self.__is_valid(driver_info):
            return None

        path = driver_info["binary_path"]
        log(f"Driver [{path}] found in cache")
        return path

    def __is_valid(self, driver_info):
        dates_diff = get_date_diff(
            driver_info["timestamp"], datetime.date.today(), self._date_format
        )
        return dates_diff < self._cache_valid_days_range

    def load_metadata_content(self):
        if os.path.exists(self._drivers_json_path):
            with open(self._drivers_json_path, "r") as outfile:
                return json.load(outfile)
        return {}

    def __get_metadata_key(self, driver: Driver):
        if self._metadata_key:
            return self._metadata_key

        driver_version = self.get_cache_key_driver_version(driver)
        browser_version = driver.get_browser_version_from_os()
        browser_version = browser_version if browser_version else ""
        self._metadata_key = f"{self.get_os_type()}_{driver.get_name()}_{driver_version}" \
                             f"_for_{browser_version}"
        return self._metadata_key

    def get_cache_key_driver_version(self, driver: Driver):
        if self._cache_key_driver_version:
            return self._cache_key_driver_version
        return driver.get_driver_version_to_download()

    def __get_path(self, driver: Driver):
        if self._driver_binary_path is None:
            self._driver_binary_path = os.path.join(
                self._drivers_directory,
                driver.get_name(),
                self.get_os_type(),
                driver.get_driver_version_to_download(),
            )
        return self._driver_binary_path

# === NexusCore/myenv\Lib\site-packages\pip\_internal\vcs\mercurial.py ===
import configparser
import logging
import os
from typing import List, Optional, Tuple

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import HiddenText, display_path
from pip._internal.utils.subprocess import make_command
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs.versioncontrol import (
    RevOptions,
    VersionControl,
    find_path_to_project_root_from_repo_root,
    vcs,
)

logger = logging.getLogger(__name__)


class Mercurial(VersionControl):
    name = "hg"
    dirname = ".hg"
    repo_name = "clone"
    schemes = (
        "hg+file",
        "hg+http",
        "hg+https",
        "hg+ssh",
        "hg+static-http",
    )

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return [f"--rev={rev}"]

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info(
            "Cloning hg %s%s to %s",
            url,
            rev_display,
            display_path(dest),
        )
        if verbosity <= 0:
            flags: Tuple[str, ...] = ("--quiet",)
        elif verbosity == 1:
            flags = ()
        elif verbosity == 2:
            flags = ("--verbose",)
        else:
            flags = ("--verbose", "--debug")
        self.run_command(make_command("clone", "--noupdate", *flags, url, dest))
        self.run_command(
            make_command("update", *flags, rev_options.to_args()),
            cwd=dest,
        )

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        repo_config = os.path.join(dest, self.dirname, "hgrc")
        config = configparser.RawConfigParser()
        try:
            config.read(repo_config)
            config.set("paths", "default", url.secret)
            with open(repo_config, "w") as config_file:
                config.write(config_file)
        except (OSError, configparser.NoSectionError) as exc:
            logger.warning("Could not switch Mercurial repository to %s: %s", url, exc)
        else:
            cmd_args = make_command("update", "-q", rev_options.to_args())
            self.run_command(cmd_args, cwd=dest)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        self.run_command(["pull", "-q"], cwd=dest)
        cmd_args = make_command("update", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        url = cls.run_command(
            ["showconfig", "paths.default"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        if cls._is_local_repository(url):
            url = path_to_url(url)
        return url.strip()

    @classmethod
    def get_revision(cls, location: str) -> str:
        """
        Return the repository-local changeset revision number, as an integer.
        """
        current_revision = cls.run_command(
            ["parents", "--template={rev}"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        return current_revision

    @classmethod
    def get_requirement_revision(cls, location: str) -> str:
        """
        Return the changeset identification hash, as a 40-character
        hexadecimal string
        """
        current_rev_hash = cls.run_command(
            ["parents", "--template={node}"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        return current_rev_hash

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """Always assume the versions don't match"""
        return False

    @classmethod
    def get_subdirectory(cls, location: str) -> Optional[str]:
        """
        Return the path to Python project root, relative to the repo root.
        Return None if the project root is in the repo root.
        """
        # find the repo root
        repo_root = cls.run_command(
            ["root"], show_stdout=False, stdout_only=True, cwd=location
        ).strip()
        if not os.path.isabs(repo_root):
            repo_root = os.path.abspath(os.path.join(location, repo_root))
        return find_path_to_project_root_from_repo_root(location, repo_root)

    @classmethod
    def get_repository_root(cls, location: str) -> Optional[str]:
        loc = super().get_repository_root(location)
        if loc:
            return loc
        try:
            r = cls.run_command(
                ["root"],
                cwd=location,
                show_stdout=False,
                stdout_only=True,
                on_returncode="raise",
                log_failed_cmd=False,
            )
        except BadCommand:
            logger.debug(
                "could not determine if %s is under hg control "
                "because hg is not available",
                location,
            )
            return None
        except InstallationError:
            return None
        return os.path.normpath(r.rstrip("\r\n"))


vcs.register(Mercurial)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\utils.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import functools
import re
from typing import NewType, Tuple, Union, cast

from .tags import Tag, parse_tag
from .version import InvalidVersion, Version, _TrimmedRelease

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


@functools.singledispatch
def canonicalize_version(
    version: Version | str, *, strip_trailing_zero: bool = True
) -> str:
    """
    Return a canonical form of a version as a string.

    >>> canonicalize_version('1.0.1')
    '1.0.1'

    Per PEP 625, versions may have multiple canonical forms, differing
    only by trailing zeros.

    >>> canonicalize_version('1.0.0')
    '1'
    >>> canonicalize_version('1.0.0', strip_trailing_zero=False)
    '1.0.0'

    Invalid versions are returned unaltered.

    >>> canonicalize_version('foo bar baz')
    'foo bar baz'
    """
    return str(_TrimmedRelease(str(version)) if strip_trailing_zero else version)


@canonicalize_version.register
def _(version: str, *, strip_trailing_zero: bool = True) -> str:
    try:
        parsed = Version(version)
    except InvalidVersion:
        # Legacy versions cannot be normalized
        return version
    return canonicalize_version(parsed, strip_trailing_zero=strip_trailing_zero)


def parse_wheel_filename(
    filename: str,
) -> tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename!r}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename!r}"
        )

    parts = filename.split("-", dashes - 2)
    name_part = parts[0]
    # See PEP 427 for the rules on escaping the project name.
    if "__" in name_part or re.match(r"^[\w\d._]*$", name_part, re.UNICODE) is None:
        raise InvalidWheelFilename(f"Invalid project name: {filename!r}")
    name = canonicalize_name(name_part)

    try:
        version = Version(parts[1])
    except InvalidVersion as e:
        raise InvalidWheelFilename(
            f"Invalid wheel filename (invalid version): {filename!r}"
        ) from e

    if dashes == 5:
        build_part = parts[2]
        build_match = _build_tag_regex.match(build_part)
        if build_match is None:
            raise InvalidWheelFilename(
                f"Invalid build number: {build_part} in {filename!r}"
            )
        build = cast(BuildTag, (int(build_match.group(1)), build_match.group(2)))
    else:
        build = ()
    tags = parse_tag(parts[-1])
    return (name, version, build, tags)


def parse_sdist_filename(filename: str) -> tuple[NormalizedName, Version]:
    if filename.endswith(".tar.gz"):
        file_stem = filename[: -len(".tar.gz")]
    elif filename.endswith(".zip"):
        file_stem = filename[: -len(".zip")]
    else:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (extension must be '.tar.gz' or '.zip'):"
            f" {filename!r}"
        )

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name_part, sep, version_part = file_stem.rpartition("-")
    if not sep:
        raise InvalidSdistFilename(f"Invalid sdist filename: {filename!r}")

    name = canonicalize_name(name_part)

    try:
        version = Version(version_part)
    except InvalidVersion as e:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (invalid version): {filename!r}"
        ) from e

    return (name, version)

# === NexusCore/openenv\Lib\site-packages\ipykernel\jsonutil.py ===
"""Utilities to manipulate JSON objects."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import math
import numbers
import re
import types
from binascii import b2a_base64
from datetime import date, datetime

from jupyter_client._version import version_info as jupyter_client_version

next_attr_name = "__next__"

# -----------------------------------------------------------------------------
# Globals and constants
# -----------------------------------------------------------------------------

# timestamp formats
ISO8601 = "%Y-%m-%dT%H:%M:%S.%f"
ISO8601_PAT = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,6})?Z?([\+\-]\d{2}:?\d{2})?$"
)

# holy crap, strptime is not threadsafe.
# Calling it once at import seems to help.
datetime.strptime("1", "%d")

# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------


# constants for identifying png/jpeg data
PNG = b"\x89PNG\r\n\x1a\n"
# front of PNG base64-encoded
PNG64 = b"iVBORw0KG"
JPEG = b"\xff\xd8"
# front of JPEG base64-encoded
JPEG64 = b"/9"
# constants for identifying gif data
GIF_64 = b"R0lGODdh"
GIF89_64 = b"R0lGODlh"
# front of PDF base64-encoded
PDF64 = b"JVBER"

JUPYTER_CLIENT_MAJOR_VERSION = jupyter_client_version[0]


def encode_images(format_dict):
    """b64-encodes images in a displaypub format dict

    Perhaps this should be handled in json_clean itself?

    Parameters
    ----------
    format_dict : dict
        A dictionary of display data keyed by mime-type

    Returns
    -------
    format_dict : dict
        A copy of the same dictionary,
        but binary image data ('image/png', 'image/jpeg' or 'application/pdf')
        is base64-encoded.

    """

    # no need for handling of ambiguous bytestrings on Python 3,
    # where bytes objects always represent binary data and thus
    # base64-encoded.
    return format_dict


def json_clean(obj):  # pragma: no cover
    """Deprecated, this is a no-op for jupyter-client>=7.

    Clean an object to ensure it's safe to encode in JSON.

    Atomic, immutable objects are returned unmodified.  Sets and tuples are
    converted to lists, lists are copied and dicts are also copied.

    Note: dicts whose keys could cause collisions upon encoding (such as a dict
    with both the number 1 and the string '1' as keys) will cause a ValueError
    to be raised.

    Parameters
    ----------
    obj : any python object

    Returns
    -------
    out : object
        A version of the input which will not cause an encoding error when
        encoded as JSON.  Note that this function does not *encode* its inputs,
        it simply sanitizes it so that there will be no encoding errors later.

    """
    if int(JUPYTER_CLIENT_MAJOR_VERSION) >= 7:
        return obj

    # types that are 'atomic' and ok in json as-is.
    atomic_ok = (str, type(None))

    # containers that we need to convert into lists
    container_to_list = (tuple, set, types.GeneratorType)

    # Since bools are a subtype of Integrals, which are a subtype of Reals,
    # we have to check them in that order.

    if isinstance(obj, bool):
        return obj

    if isinstance(obj, numbers.Integral):
        # cast int to int, in case subclasses override __str__ (e.g. boost enum, #4598)
        return int(obj)

    if isinstance(obj, numbers.Real):
        # cast out-of-range floats to their reprs
        if math.isnan(obj) or math.isinf(obj):
            return repr(obj)
        return float(obj)

    if isinstance(obj, atomic_ok):
        return obj

    if isinstance(obj, bytes):
        # unanmbiguous binary data is base64-encoded
        # (this probably should have happened upstream)
        return b2a_base64(obj).decode("ascii")

    if isinstance(obj, container_to_list) or (
        hasattr(obj, "__iter__") and hasattr(obj, next_attr_name)
    ):
        obj = list(obj)

    if isinstance(obj, list):
        return [json_clean(x) for x in obj]

    if isinstance(obj, dict):
        # First, validate that the dict won't lose data in conversion due to
        # key collisions after stringification.  This can happen with keys like
        # True and 'true' or 1 and '1', which collide in JSON.
        nkeys = len(obj)
        nkeys_collapsed = len(set(map(str, obj)))
        if nkeys != nkeys_collapsed:
            msg = (
                "dict cannot be safely converted to JSON: "
                "key collision would lead to dropped values"
            )
            raise ValueError(msg)
        # If all OK, proceed by making the new dict that will be json-safe
        out = {}
        for k, v in obj.items():
            out[str(k)] = json_clean(v)
        return out
    if isinstance(obj, (datetime, date)):
        return obj.strftime(ISO8601)

    # we don't understand it, it's probably an unserializable object
    raise ValueError("Can't clean for JSON: %r" % obj)

# === NexusCore/openenv\Lib\site-packages\jedi\settings.py ===
"""
This module contains variables with global |jedi| settings. To change the
behavior of |jedi|, change the variables defined in :mod:`jedi.settings`.

Plugins should expose an interface so that the user can adjust the
configuration.


Example usage::

    from jedi import settings
    settings.case_insensitive_completion = True


Completion output
~~~~~~~~~~~~~~~~~

.. autodata:: case_insensitive_completion
.. autodata:: add_bracket_after_function


Filesystem cache
~~~~~~~~~~~~~~~~

.. autodata:: cache_directory


Parser
~~~~~~

.. autodata:: fast_parser


Dynamic stuff
~~~~~~~~~~~~~

.. autodata:: dynamic_array_additions
.. autodata:: dynamic_params
.. autodata:: dynamic_params_for_other_modules
.. autodata:: auto_import_modules


Caching
~~~~~~~

.. autodata:: call_signatures_validity


"""
import os
import platform

# ----------------
# Completion Output Settings
# ----------------

case_insensitive_completion = True
"""
Completions are by default case insensitive.
"""

add_bracket_after_function = False
"""
Adds an opening bracket after a function for completions.
"""

# ----------------
# Filesystem Cache
# ----------------

if platform.system().lower() == 'windows':
    _cache_directory = os.path.join(
        os.getenv('LOCALAPPDATA') or os.path.expanduser('~'),
        'Jedi',
        'Jedi',
    )
elif platform.system().lower() == 'darwin':
    _cache_directory = os.path.join('~', 'Library', 'Caches', 'Jedi')
else:
    _cache_directory = os.path.join(os.getenv('XDG_CACHE_HOME') or '~/.cache',
                                    'jedi')
cache_directory = os.path.expanduser(_cache_directory)
"""
The path where the cache is stored.

On Linux, this defaults to ``~/.cache/jedi/``, on OS X to
``~/Library/Caches/Jedi/`` and on Windows to ``%LOCALAPPDATA%\\Jedi\\Jedi\\``.
On Linux, if the environment variable ``$XDG_CACHE_HOME`` is set,
``$XDG_CACHE_HOME/jedi`` is used instead of the default one.
"""

# ----------------
# Parser
# ----------------

fast_parser = True
"""
Uses Parso's diff parser. If it is enabled, this might cause issues, please
read the warning on :class:`.Script`. This feature makes it possible to only
parse the parts again that have changed, while reusing the rest of the syntax
tree.
"""

_cropped_file_size = int(10e6)  # 1 Megabyte
"""
Jedi gets extremely slow if the file size exceed a few thousand lines.
To avoid getting stuck completely Jedi crops the file at some point.

One megabyte of typical Python code equals about 20'000 lines of code.
"""

# ----------------
# Dynamic Stuff
# ----------------

dynamic_array_additions = True
"""
check for `append`, etc. on arrays: [], {}, () as well as list/set calls.
"""

dynamic_params = True
"""
A dynamic param completion, finds the callees of the function, which define
the params of a function.
"""

dynamic_params_for_other_modules = True
"""
Do the same for other modules.
"""

dynamic_flow_information = True
"""
Check for `isinstance` and other information to infer a type.
"""

auto_import_modules = [
    'gi',  # This third-party repository (GTK stuff) doesn't really work with jedi
]
"""
Modules that will not be analyzed but imported, if they contain Python code.
This improves autocompletion for libraries that use ``setattr`` or
``globals()`` modifications a lot.
"""

allow_unsafe_interpreter_executions = True
"""
Controls whether descriptors are evaluated when using an Interpreter. This is
something you might want to control when using Jedi from a Repl (e.g. IPython)

Generally this setting allows Jedi to execute __getitem__ and descriptors like
`property`.
"""

# ----------------
# Caching Validity
# ----------------

call_signatures_validity = 3.0
"""
Finding function calls might be slow (0.1-0.5s). This is not acceptible for
normal writing. Therefore cache it for a short time.
"""

# === NexusCore/openenv\Lib\site-packages\joblib\__init__.py ===
"""Joblib is a set of tools to provide **lightweight pipelining in
Python**. In particular:

1. transparent disk-caching of functions and lazy re-evaluation
   (memoize pattern)

2. easy simple parallel computing

Joblib is optimized to be **fast** and **robust** on large
data in particular and has specific optimizations for `numpy` arrays. It is
**BSD-licensed**.


    ==================== ===============================================
    **Documentation:**       https://joblib.readthedocs.io

    **Download:**            https://pypi.python.org/pypi/joblib#downloads

    **Source code:**         https://github.com/joblib/joblib

    **Report issues:**       https://github.com/joblib/joblib/issues
    ==================== ===============================================


Vision
--------

The vision is to provide tools to easily achieve better performance and
reproducibility when working with long running jobs.

 *  **Avoid computing the same thing twice**: code is often rerun again and
    again, for instance when prototyping computational-heavy jobs (as in
    scientific development), but hand-crafted solutions to alleviate this
    issue are error-prone and often lead to unreproducible results.

 *  **Persist to disk transparently**: efficiently persisting
    arbitrary objects containing large data is hard. Using
    joblib's caching mechanism avoids hand-written persistence and
    implicitly links the file on disk to the execution context of
    the original Python object. As a result, joblib's persistence is
    good for resuming an application status or computational job, eg
    after a crash.

Joblib addresses these problems while **leaving your code and your flow
control as unmodified as possible** (no framework, no new paradigms).

Main features
------------------

1) **Transparent and fast disk-caching of output value:** a memoize or
   make-like functionality for Python functions that works well for
   arbitrary Python objects, including very large numpy arrays. Separate
   persistence and flow-execution logic from domain logic or algorithmic
   code by writing the operations as a set of steps with well-defined
   inputs and  outputs: Python functions. Joblib can save their
   computation to disk and rerun it only if necessary::

      >>> from joblib import Memory
      >>> location = 'your_cache_dir_goes_here'
      >>> mem = Memory(location, verbose=1)
      >>> import numpy as np
      >>> a = np.vander(np.arange(3)).astype(float)
      >>> square = mem.cache(np.square)
      >>> b = square(a)                                   # doctest: +ELLIPSIS
      ______________________________________________________________________...
      [Memory] Calling ...square...
      square(array([[0., 0., 1.],
             [1., 1., 1.],
             [4., 2., 1.]]))
      _________________________________________________...square - ...s, 0.0min

      >>> c = square(a)
      >>> # The above call did not trigger an evaluation

2) **Embarrassingly parallel helper:** to make it easy to write readable
   parallel code and debug it quickly::

      >>> from joblib import Parallel, delayed
      >>> from math import sqrt
      >>> Parallel(n_jobs=1)(delayed(sqrt)(i**2) for i in range(10))
      [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


3) **Fast compressed Persistence**: a replacement for pickle to work
   efficiently on Python objects containing large data (
   *joblib.dump* & *joblib.load* ).

..
    >>> import shutil ; shutil.rmtree(location)

"""

# PEP0440 compatible formatted version, see:
# https://www.python.org/dev/peps/pep-0440/
#
# Generic release markers:
# X.Y
# X.Y.Z # For bugfix releases
#
# Admissible pre-release markers:
# X.YaN # Alpha release
# X.YbN # Beta release
# X.YrcN # Release Candidate
# X.Y # Final release
#
# Dev branch marker is: 'X.Y.dev' or 'X.Y.devN' where N is an integer.
# 'X.Y.dev0' is the canonical version of 'X.Y.dev'
#
__version__ = "1.5.1"


import os

from ._cloudpickle_wrapper import wrap_non_picklable_objects
from ._parallel_backends import ParallelBackendBase
from ._store_backends import StoreBackendBase
from .compressor import register_compressor
from .hashing import hash
from .logger import Logger, PrintTime
from .memory import MemorizedResult, Memory, expires_after, register_store_backend
from .numpy_pickle import dump, load
from .parallel import (
    Parallel,
    cpu_count,
    delayed,
    effective_n_jobs,
    parallel_backend,
    parallel_config,
    register_parallel_backend,
)

__all__ = [
    # On-disk result caching
    "Memory",
    "MemorizedResult",
    "expires_after",
    # Parallel code execution
    "Parallel",
    "delayed",
    "cpu_count",
    "effective_n_jobs",
    "wrap_non_picklable_objects",
    # Context to change the backend globally
    "parallel_config",
    "parallel_backend",
    # Helpers to define and register store/parallel backends
    "ParallelBackendBase",
    "StoreBackendBase",
    "register_compressor",
    "register_parallel_backend",
    "register_store_backend",
    # Helpers kept for backward compatibility
    "PrintTime",
    "Logger",
    "hash",
    "dump",
    "load",
]


# Workaround issue discovered in intel-openmp 2019.5:
# https://github.com/ContinuumIO/anaconda-issues/issues/11294
os.environ.setdefault("KMP_INIT_AT_FORK", "FALSE")

# === NexusCore/openenv\Lib\site-packages\packaging\utils.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import functools
import re
from typing import NewType, Tuple, Union, cast

from .tags import Tag, parse_tag
from .version import InvalidVersion, Version, _TrimmedRelease

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


@functools.singledispatch
def canonicalize_version(
    version: Version | str, *, strip_trailing_zero: bool = True
) -> str:
    """
    Return a canonical form of a version as a string.

    >>> canonicalize_version('1.0.1')
    '1.0.1'

    Per PEP 625, versions may have multiple canonical forms, differing
    only by trailing zeros.

    >>> canonicalize_version('1.0.0')
    '1'
    >>> canonicalize_version('1.0.0', strip_trailing_zero=False)
    '1.0.0'

    Invalid versions are returned unaltered.

    >>> canonicalize_version('foo bar baz')
    'foo bar baz'
    """
    return str(_TrimmedRelease(str(version)) if strip_trailing_zero else version)


@canonicalize_version.register
def _(version: str, *, strip_trailing_zero: bool = True) -> str:
    try:
        parsed = Version(version)
    except InvalidVersion:
        # Legacy versions cannot be normalized
        return version
    return canonicalize_version(parsed, strip_trailing_zero=strip_trailing_zero)


def parse_wheel_filename(
    filename: str,
) -> tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename!r}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename!r}"
        )

    parts = filename.split("-", dashes - 2)
    name_part = parts[0]
    # See PEP 427 for the rules on escaping the project name.
    if "__" in name_part or re.match(r"^[\w\d._]*$", name_part, re.UNICODE) is None:
        raise InvalidWheelFilename(f"Invalid project name: {filename!r}")
    name = canonicalize_name(name_part)

    try:
        version = Version(parts[1])
    except InvalidVersion as e:
        raise InvalidWheelFilename(
            f"Invalid wheel filename (invalid version): {filename!r}"
        ) from e

    if dashes == 5:
        build_part = parts[2]
        build_match = _build_tag_regex.match(build_part)
        if build_match is None:
            raise InvalidWheelFilename(
                f"Invalid build number: {build_part} in {filename!r}"
            )
        build = cast(BuildTag, (int(build_match.group(1)), build_match.group(2)))
    else:
        build = ()
    tags = parse_tag(parts[-1])
    return (name, version, build, tags)


def parse_sdist_filename(filename: str) -> tuple[NormalizedName, Version]:
    if filename.endswith(".tar.gz"):
        file_stem = filename[: -len(".tar.gz")]
    elif filename.endswith(".zip"):
        file_stem = filename[: -len(".zip")]
    else:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (extension must be '.tar.gz' or '.zip'):"
            f" {filename!r}"
        )

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name_part, sep, version_part = file_stem.rpartition("-")
    if not sep:
        raise InvalidSdistFilename(f"Invalid sdist filename: {filename!r}")

    name = canonicalize_name(name_part)

    try:
        version = Version(version_part)
    except InvalidVersion as e:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (invalid version): {filename!r}"
        ) from e

    return (name, version)

# === NexusCore/openenv\Lib\site-packages\shellingham\nt.py ===
import contextlib
import ctypes
import os

from ctypes.wintypes import (
    BOOL,
    CHAR,
    DWORD,
    HANDLE,
    LONG,
    LPWSTR,
    MAX_PATH,
    PDWORD,
    ULONG,
)

from shellingham._core import SHELL_NAMES


INVALID_HANDLE_VALUE = HANDLE(-1).value
ERROR_NO_MORE_FILES = 18
ERROR_INSUFFICIENT_BUFFER = 122
TH32CS_SNAPPROCESS = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


kernel32 = ctypes.windll.kernel32


def _check_handle(error_val=0):
    def check(ret, func, args):
        if ret == error_val:
            raise ctypes.WinError()
        return ret

    return check


def _check_expected(expected):
    def check(ret, func, args):
        if ret:
            return True
        code = ctypes.GetLastError()
        if code == expected:
            return False
        raise ctypes.WinError(code)

    return check


class ProcessEntry32(ctypes.Structure):
    _fields_ = (
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ULONG)),
        ("th32ModuleID", DWORD),
        ("cntThreads", DWORD),
        ("th32ParentProcessID", DWORD),
        ("pcPriClassBase", LONG),
        ("dwFlags", DWORD),
        ("szExeFile", CHAR * MAX_PATH),
    )


kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.CloseHandle.restype = BOOL

kernel32.CreateToolhelp32Snapshot.argtypes = [DWORD, DWORD]
kernel32.CreateToolhelp32Snapshot.restype = HANDLE
kernel32.CreateToolhelp32Snapshot.errcheck = _check_handle(  # type: ignore
    INVALID_HANDLE_VALUE,
)

kernel32.Process32First.argtypes = [HANDLE, ctypes.POINTER(ProcessEntry32)]
kernel32.Process32First.restype = BOOL
kernel32.Process32First.errcheck = _check_expected(  # type: ignore
    ERROR_NO_MORE_FILES,
)

kernel32.Process32Next.argtypes = [HANDLE, ctypes.POINTER(ProcessEntry32)]
kernel32.Process32Next.restype = BOOL
kernel32.Process32Next.errcheck = _check_expected(  # type: ignore
    ERROR_NO_MORE_FILES,
)

kernel32.GetCurrentProcessId.argtypes = []
kernel32.GetCurrentProcessId.restype = DWORD

kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
kernel32.OpenProcess.restype = HANDLE
kernel32.OpenProcess.errcheck = _check_handle(  # type: ignore
    INVALID_HANDLE_VALUE,
)

kernel32.QueryFullProcessImageNameW.argtypes = [HANDLE, DWORD, LPWSTR, PDWORD]
kernel32.QueryFullProcessImageNameW.restype = BOOL
kernel32.QueryFullProcessImageNameW.errcheck = _check_expected(  # type: ignore
    ERROR_INSUFFICIENT_BUFFER,
)


@contextlib.contextmanager
def _handle(f, *args, **kwargs):
    handle = f(*args, **kwargs)
    try:
        yield handle
    finally:
        kernel32.CloseHandle(handle)


def _iter_processes():
    f = kernel32.CreateToolhelp32Snapshot
    with _handle(f, TH32CS_SNAPPROCESS, 0) as snap:
        entry = ProcessEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        ret = kernel32.Process32First(snap, entry)
        while ret:
            yield entry
            ret = kernel32.Process32Next(snap, entry)


def _get_full_path(proch):
    size = DWORD(MAX_PATH)
    while True:
        path_buff = ctypes.create_unicode_buffer("", size.value)
        if kernel32.QueryFullProcessImageNameW(proch, 0, path_buff, size):
            return path_buff.value
        size.value *= 2


def get_shell(pid=None, max_depth=10):
    proc_map = {
        proc.th32ProcessID: (proc.th32ParentProcessID, proc.szExeFile)
        for proc in _iter_processes()
    }
    pid = pid or os.getpid()

    for _ in range(0, max_depth + 1):
        try:
            ppid, executable = proc_map[pid]
        except KeyError:  # No such process? Give up.
            break

        # The executable name would be encoded with the current code page if
        # we're in ANSI mode (usually). Try to decode it into str/unicode,
        # replacing invalid characters to be safe (not thoeratically necessary,
        # I think). Note that we need to use 'mbcs' instead of encoding
        # settings from sys because this is from the Windows API, not Python
        # internals (which those settings reflect). (pypa/pipenv#3382)
        if isinstance(executable, bytes):
            executable = executable.decode("mbcs", "replace")

        name = executable.rpartition(".")[0].lower()
        if name not in SHELL_NAMES:
            pid = ppid
            continue

        key = PROCESS_QUERY_LIMITED_INFORMATION
        with _handle(kernel32.OpenProcess, key, 0, pid) as proch:
            return (name, _get_full_path(proch))

    return None

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\otTraverse.py ===
"""Methods for traversing trees of otData-driven OpenType tables."""

from collections import deque
from typing import Callable, Deque, Iterable, List, Optional, Tuple
from .otBase import BaseTable


__all__ = [
    "bfs_base_table",
    "dfs_base_table",
    "SubTablePath",
]


class SubTablePath(Tuple[BaseTable.SubTableEntry, ...]):
    def __str__(self) -> str:
        path_parts = []
        for entry in self:
            path_part = entry.name
            if entry.index is not None:
                path_part += f"[{entry.index}]"
            path_parts.append(path_part)
        return ".".join(path_parts)


# Given f(current frontier, new entries) add new entries to frontier
AddToFrontierFn = Callable[[Deque[SubTablePath], List[SubTablePath]], None]


def dfs_base_table(
    root: BaseTable,
    root_accessor: Optional[str] = None,
    skip_root: bool = False,
    predicate: Optional[Callable[[SubTablePath], bool]] = None,
    iter_subtables_fn: Optional[
        Callable[[BaseTable], Iterable[BaseTable.SubTableEntry]]
    ] = None,
) -> Iterable[SubTablePath]:
    """Depth-first search tree of BaseTables.

    Args:
        root (BaseTable): the root of the tree.
        root_accessor (Optional[str]): attribute name for the root table, if any (mostly
            useful for debugging).
        skip_root (Optional[bool]): if True, the root itself is not visited, only its
            children.
        predicate (Optional[Callable[[SubTablePath], bool]]): function to filter out
            paths. If True, the path is yielded and its subtables are added to the
            queue. If False, the path is skipped and its subtables are not traversed.
        iter_subtables_fn (Optional[Callable[[BaseTable], Iterable[BaseTable.SubTableEntry]]]):
            function to iterate over subtables of a table. If None, the default
            BaseTable.iterSubTables() is used.

    Yields:
        SubTablePath: tuples of BaseTable.SubTableEntry(name, table, index) namedtuples
        for each of the nodes in the tree. The last entry in a path is the current
        subtable, whereas preceding ones refer to its parent tables all the way up to
        the root.
    """
    yield from _traverse_ot_data(
        root,
        root_accessor,
        skip_root,
        predicate,
        lambda frontier, new: frontier.extendleft(reversed(new)),
        iter_subtables_fn,
    )


def bfs_base_table(
    root: BaseTable,
    root_accessor: Optional[str] = None,
    skip_root: bool = False,
    predicate: Optional[Callable[[SubTablePath], bool]] = None,
    iter_subtables_fn: Optional[
        Callable[[BaseTable], Iterable[BaseTable.SubTableEntry]]
    ] = None,
) -> Iterable[SubTablePath]:
    """Breadth-first search tree of BaseTables.

    Args:
        root
            the root of the tree.
        root_accessor (Optional[str]): attribute name for the root table, if any (mostly
            useful for debugging).
        skip_root (Optional[bool]): if True, the root itself is not visited, only its
            children.
        predicate (Optional[Callable[[SubTablePath], bool]]): function to filter out
            paths. If True, the path is yielded and its subtables are added to the
            queue. If False, the path is skipped and its subtables are not traversed.
        iter_subtables_fn (Optional[Callable[[BaseTable], Iterable[BaseTable.SubTableEntry]]]):
            function to iterate over subtables of a table. If None, the default
            BaseTable.iterSubTables() is used.

    Yields:
        SubTablePath: tuples of BaseTable.SubTableEntry(name, table, index) namedtuples
        for each of the nodes in the tree. The last entry in a path is the current
        subtable, whereas preceding ones refer to its parent tables all the way up to
        the root.
    """
    yield from _traverse_ot_data(
        root,
        root_accessor,
        skip_root,
        predicate,
        lambda frontier, new: frontier.extend(new),
        iter_subtables_fn,
    )


def _traverse_ot_data(
    root: BaseTable,
    root_accessor: Optional[str],
    skip_root: bool,
    predicate: Optional[Callable[[SubTablePath], bool]],
    add_to_frontier_fn: AddToFrontierFn,
    iter_subtables_fn: Optional[
        Callable[[BaseTable], Iterable[BaseTable.SubTableEntry]]
    ] = None,
) -> Iterable[SubTablePath]:
    # no visited because general otData cannot cycle (forward-offset only)
    if root_accessor is None:
        root_accessor = type(root).__name__

    if predicate is None:

        def predicate(path):
            return True

    if iter_subtables_fn is None:

        def iter_subtables_fn(table):
            return table.iterSubTables()

    frontier: Deque[SubTablePath] = deque()

    root_entry = BaseTable.SubTableEntry(root_accessor, root)
    if not skip_root:
        frontier.append((root_entry,))
    else:
        add_to_frontier_fn(
            frontier,
            [
                (root_entry, subtable_entry)
                for subtable_entry in iter_subtables_fn(root)
            ],
        )

    while frontier:
        # path is (value, attr_name) tuples. attr_name is attr of parent to get value
        path = frontier.popleft()
        current = path[-1].value

        if not predicate(path):
            continue

        yield SubTablePath(path)

        new_entries = [
            path + (subtable_entry,) for subtable_entry in iter_subtables_fn(current)
        ]

        add_to_frontier_fn(frontier, new_entries)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\post_process_utils.py ===
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
"""Utilities for working with post-processing tokens."""
from __future__ import annotations

import abc
from typing import Any, Callable, Sequence

from google.generativeai.notebook import py_utils
from google.generativeai.notebook.lib import llm_function
from google.generativeai.notebook.lib import llmfn_output_row
from google.generativeai.notebook.lib import llmfn_post_process


class PostProcessParseError(RuntimeError):
    """An error parsing the post-processing tokens."""


class ParsedPostProcessExpr(abc.ABC):
    """A post-processing expression parsed from the command line."""

    @abc.abstractmethod
    def name(self) -> str:
        """Returns the name of this expression."""

    @abc.abstractmethod
    def add_to_llm_function(self, llm_fn: llm_function.LLMFunction) -> llm_function.LLMFunction:
        """Adds this parsed expression to `llm_fn` as a post-processing command."""


class _ParsedPostProcessAddExpr(
    ParsedPostProcessExpr, llmfn_post_process.LLMFnPostProcessBatchAddFn
):
    """An expression that returns the value of a new column to add to a row."""

    def __init__(self, name: str, fn: Callable[[str], Any]):
        """Constructor.

        Args:
          name: The name of the expression. The name of the new column will be
            derived from this.
          fn: A function that takes the result of a row and returns a new value to
            add as a new column in the row.
        """
        self._name = name
        self._fn = fn

    def name(self) -> str:
        return self._name

    def __call__(self, rows: Sequence[llmfn_output_row.LLMFnOutputRowView]) -> Sequence[Any]:
        return [self._fn(row.result_value()) for row in rows]

    def add_to_llm_function(self, llm_fn: llm_function.LLMFunction) -> llm_function.LLMFunction:
        return llm_fn.add_post_process_add_fn(name=self._name, fn=self)


class _ParsedPostProcessReplaceExpr(
    ParsedPostProcessExpr, llmfn_post_process.LLMFnPostProcessBatchReplaceFn
):
    """An expression that returns the new result value for a row."""

    def __init__(self, name: str, fn: Callable[[str], str]):
        """Constructor.

        Args:
          name: The name of the expression.
          fn: A function that takes the result of a row and returns the new result.
        """
        self._name = name
        self._fn = fn

    def name(self) -> str:
        return self._name

    def __call__(self, rows: Sequence[llmfn_output_row.LLMFnOutputRowView]) -> Sequence[str]:
        return [self._fn(row.result_value()) for row in rows]

    def add_to_llm_function(self, llm_fn: llm_function.LLMFunction) -> llm_function.LLMFunction:
        return llm_fn.add_post_process_replace_fn(name=self._name, fn=self)


# Decorator functions.
def post_process_add_fn(fn: Callable[[str], Any]):
    return _ParsedPostProcessAddExpr(name=fn.__name__, fn=fn)


def post_process_replace_fn(fn: Callable[[str], str]):
    return _ParsedPostProcessReplaceExpr(name=fn.__name__, fn=fn)


def validate_one_post_processing_expression(
    tokens: Sequence[str],
) -> None:
    if not tokens:
        raise PostProcessParseError("Cannot have empty post-processing expression")
    if len(tokens) > 1:
        raise PostProcessParseError("Post-processing expression should be a single token")


def _resolve_one_post_processing_expression(
    tokens: Sequence[str],
) -> tuple[str, Any]:
    """Returns name and the resolved expression."""
    validate_one_post_processing_expression(tokens)

    token_parts = tokens[0].split(".")

    current_module = py_utils.get_main_module()
    for part_num, part in enumerate(token_parts):
        current_module_vars = vars(current_module)
        if part not in current_module_vars:
            raise PostProcessParseError(
                'Unable to resolve "{}"'.format(".".join(token_parts[: part_num + 1]))
            )

        current_module = current_module_vars[part]

    return (" ".join(tokens), current_module)


def resolve_post_processing_tokens(
    tokens: Sequence[Sequence[str]],
) -> Sequence[ParsedPostProcessExpr]:
    """Resolves post-processing tokens into ParsedPostProcessExprs.

    E.g. Given [["add_length"], ["to_upper"]] as input, this function will return
    a sequence of ParsedPostProcessExprs that will execute add_length() and
    to_upper() on each entry of the LLM output as post-processing operations.

    Raises:
      PostProcessParseError: An error parsing or resolving the tokens.

    Args:
      tokens: A sequence of post-processing tokens after splitting.

    Returns:
      A sequence of ParsedPostProcessExprs.
    """
    results: list[ParsedPostProcessExpr] = []
    for expression in tokens:
        expr_name, expr_value = _resolve_one_post_processing_expression(expression)
        if isinstance(expr_value, ParsedPostProcessExpr):
            results.append(expr_value)
        elif isinstance(expr_value, Callable):
            # By default, assume that an undecorated function is an "add" function.
            results.append(_ParsedPostProcessAddExpr(name=expr_name, fn=expr_value))
        else:
            raise PostProcessParseError("{} is not callable".format(expr_name))

    return results

# === NexusCore/openenv\Lib\site-packages\grpc\beta\interfaces.py ===
# Copyright 2015 gRPC authors.
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
"""Constants and interfaces of the Beta API of gRPC Python."""

import abc

import grpc

ChannelConnectivity = grpc.ChannelConnectivity
# FATAL_FAILURE was a Beta-API name for SHUTDOWN
ChannelConnectivity.FATAL_FAILURE = ChannelConnectivity.SHUTDOWN

StatusCode = grpc.StatusCode


class GRPCCallOptions(object):
    """A value encapsulating gRPC-specific options passed on RPC invocation.

    This class and its instances have no supported interface - it exists to
    define the type of its instances and its instances exist to be passed to
    other functions.
    """

    def __init__(self, disable_compression, subcall_of, credentials):
        self.disable_compression = disable_compression
        self.subcall_of = subcall_of
        self.credentials = credentials


def grpc_call_options(disable_compression=False, credentials=None):
    """Creates a GRPCCallOptions value to be passed at RPC invocation.

    All parameters are optional and should always be passed by keyword.

    Args:
      disable_compression: A boolean indicating whether or not compression should
        be disabled for the request object of the RPC. Only valid for
        request-unary RPCs.
      credentials: A CallCredentials object to use for the invoked RPC.
    """
    return GRPCCallOptions(disable_compression, None, credentials)


GRPCAuthMetadataContext = grpc.AuthMetadataContext
GRPCAuthMetadataPluginCallback = grpc.AuthMetadataPluginCallback
GRPCAuthMetadataPlugin = grpc.AuthMetadataPlugin


class GRPCServicerContext(abc.ABC):
    """Exposes gRPC-specific options and behaviors to code servicing RPCs."""

    @abc.abstractmethod
    def peer(self):
        """Identifies the peer that invoked the RPC being serviced.

        Returns:
          A string identifying the peer that invoked the RPC being serviced.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def disable_next_response_compression(self):
        """Disables compression of the next response passed by the application."""
        raise NotImplementedError()


class GRPCInvocationContext(abc.ABC):
    """Exposes gRPC-specific options and behaviors to code invoking RPCs."""

    @abc.abstractmethod
    def disable_next_request_compression(self):
        """Disables compression of the next request passed by the application."""
        raise NotImplementedError()


class Server(abc.ABC):
    """Services RPCs."""

    @abc.abstractmethod
    def add_insecure_port(self, address):
        """Reserves a port for insecure RPC service once this Server becomes active.

        This method may only be called before calling this Server's start method is
        called.

        Args:
          address: The address for which to open a port.

        Returns:
          An integer port on which RPCs will be serviced after this link has been
            started. This is typically the same number as the port number contained
            in the passed address, but will likely be different if the port number
            contained in the passed address was zero.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_secure_port(self, address, server_credentials):
        """Reserves a port for secure RPC service after this Server becomes active.

        This method may only be called before calling this Server's start method is
        called.

        Args:
          address: The address for which to open a port.
          server_credentials: A ServerCredentials.

        Returns:
          An integer port on which RPCs will be serviced after this link has been
            started. This is typically the same number as the port number contained
            in the passed address, but will likely be different if the port number
            contained in the passed address was zero.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def start(self):
        """Starts this Server's service of RPCs.

        This method may only be called while the server is not serving RPCs (i.e. it
        is not idempotent).
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self, grace):
        """Stops this Server's service of RPCs.

        All calls to this method immediately stop service of new RPCs. When existing
        RPCs are aborted is controlled by the grace period parameter passed to this
        method.

        This method may be called at any time and is idempotent. Passing a smaller
        grace value than has been passed in a previous call will have the effect of
        stopping the Server sooner. Passing a larger grace value than has been
        passed in a previous call will not have the effect of stopping the server
        later.

        Args:
          grace: A duration of time in seconds to allow existing RPCs to complete
            before being aborted by this Server's stopping. May be zero for
            immediate abortion of all in-progress RPCs.

        Returns:
          A threading.Event that will be set when this Server has completely
          stopped. The returned event may not be set until after the full grace
          period (if some ongoing RPC continues for the full length of the period)
          of it may be set much sooner (such as if this Server had no RPCs underway
          at the time it was stopped or if all RPCs that it had underway completed
          very early in the grace period).
        """
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\auth_checks_organization.py ===
"""
Auth Checks for Organizations
"""

from typing import Dict, List, Optional, Tuple

from fastapi import status

from litellm.proxy._types import *


def organization_role_based_access_check(
    request_body: dict,
    user_object: Optional[LiteLLM_UserTable],
    route: str,
):
    """
    Role based access control checks only run if a user is part of an Organization

    Organization Checks:
    ONLY RUN IF user_object.organization_memberships is not None

    1. Only Proxy Admins can access /organization/new
    2. IF route is a LiteLLMRoutes.org_admin_only_routes, then check if user is an Org Admin for that organization

    """

    if user_object is None:
        return

    passed_organization_id: Optional[str] = request_body.get("organization_id", None)

    if route == "/organization/new":
        if user_object.user_role != LitellmUserRoles.PROXY_ADMIN.value:
            raise ProxyException(
                message=f"Only proxy admins can create new organizations. You are {user_object.user_role}",
                type=ProxyErrorTypes.auth_error.value,
                param="user_role",
                code=status.HTTP_401_UNAUTHORIZED,
            )

    if user_object.user_role == LitellmUserRoles.PROXY_ADMIN.value:
        return

    # Checks if route is an Org Admin Only Route
    if route in LiteLLMRoutes.org_admin_only_routes.value:
        (
            _user_organizations,
            _user_organization_role_mapping,
        ) = get_user_organization_info(user_object)

        if user_object.organization_memberships is None:
            raise ProxyException(
                message=f"Tried to access route={route} but you are not a member of any organization. Please contact the proxy admin to request access.",
                type=ProxyErrorTypes.auth_error.value,
                param="organization_id",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        if passed_organization_id is None:
            raise ProxyException(
                message="Passed organization_id is None, please pass an organization_id in your request",
                type=ProxyErrorTypes.auth_error.value,
                param="organization_id",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        user_role: Optional[LitellmUserRoles] = _user_organization_role_mapping.get(
            passed_organization_id
        )
        if user_role is None:
            raise ProxyException(
                message=f"You do not have a role within the selected organization. Passed organization_id: {passed_organization_id}. Please contact the organization admin to request access.",
                type=ProxyErrorTypes.auth_error.value,
                param="organization_id",
                code=status.HTTP_401_UNAUTHORIZED,
            )

        if user_role != LitellmUserRoles.ORG_ADMIN.value:
            raise ProxyException(
                message=f"You do not have the required role to perform {route} in Organization {passed_organization_id}. Your role is {user_role} in Organization {passed_organization_id}",
                type=ProxyErrorTypes.auth_error.value,
                param="user_role",
                code=status.HTTP_401_UNAUTHORIZED,
            )
    elif route == "/team/new":
        # if user is part of multiple teams, then they need to specify the organization_id
        (
            _user_organizations,
            _user_organization_role_mapping,
        ) = get_user_organization_info(user_object)
        if (
            user_object.organization_memberships is not None
            and len(user_object.organization_memberships) > 0
        ):
            if passed_organization_id is None:
                raise ProxyException(
                    message=f"Passed organization_id is None, please specify the organization_id in your request. You are part of multiple organizations: {_user_organizations}",
                    type=ProxyErrorTypes.auth_error.value,
                    param="organization_id",
                    code=status.HTTP_401_UNAUTHORIZED,
                )

            _user_role_in_passed_org = _user_organization_role_mapping.get(
                passed_organization_id
            )
            if _user_role_in_passed_org != LitellmUserRoles.ORG_ADMIN.value:
                raise ProxyException(
                    message=f"You do not have the required role to call {route}. Your role is {_user_role_in_passed_org} in Organization {passed_organization_id}",
                    type=ProxyErrorTypes.auth_error.value,
                    param="user_role",
                    code=status.HTTP_401_UNAUTHORIZED,
                )


def get_user_organization_info(
    user_object: LiteLLM_UserTable,
) -> Tuple[List[str], Dict[str, Optional[LitellmUserRoles]]]:
    """
    Helper function to extract user organization information.

    Args:
        user_object (LiteLLM_UserTable): The user object containing organization memberships.

    Returns:
        Tuple[List[str], Dict[str, Optional[LitellmUserRoles]]]: A tuple containing:
            - List of organization IDs the user is a member of
            - Dictionary mapping organization IDs to user roles
    """
    _user_organizations: List[str] = []
    _user_organization_role_mapping: Dict[str, Optional[LitellmUserRoles]] = {}

    if user_object.organization_memberships is not None:
        for _membership in user_object.organization_memberships:
            if _membership.organization_id is not None:
                _user_organizations.append(_membership.organization_id)
                _user_organization_role_mapping[_membership.organization_id] = _membership.user_role  # type: ignore

    return _user_organizations, _user_organization_role_mapping


def _user_is_org_admin(
    request_data: dict,
    user_object: Optional[LiteLLM_UserTable] = None,
) -> bool:
    """
    Helper function to check if user is an org admin for the passed organization_id
    """
    if request_data.get("organization_id", None) is None:
        return False

    if user_object is None:
        return False

    if user_object.organization_memberships is None:
        return False

    for _membership in user_object.organization_memberships:
        if _membership.organization_id == request_data.get("organization_id", None):
            if _membership.user_role == LitellmUserRoles.ORG_ADMIN.value:
                return True

    return False

# === NexusCore/openenv\Lib\site-packages\nltk\lm\counter.py ===
# Natural Language Toolkit
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Language Model Counter
----------------------
"""

from collections import defaultdict
from collections.abc import Sequence

from nltk.probability import ConditionalFreqDist, FreqDist


class NgramCounter:
    """Class for counting ngrams.

    Will count any ngram sequence you give it ;)

    First we need to make sure we are feeding the counter sentences of ngrams.

    >>> text = [["a", "b", "c", "d"], ["a", "c", "d", "c"]]
    >>> from nltk.util import ngrams
    >>> text_bigrams = [ngrams(sent, 2) for sent in text]
    >>> text_unigrams = [ngrams(sent, 1) for sent in text]

    The counting itself is very simple.

    >>> from nltk.lm import NgramCounter
    >>> ngram_counts = NgramCounter(text_bigrams + text_unigrams)

    You can conveniently access ngram counts using standard python dictionary notation.
    String keys will give you unigram counts.

    >>> ngram_counts['a']
    2
    >>> ngram_counts['aliens']
    0

    If you want to access counts for higher order ngrams, use a list or a tuple.
    These are treated as "context" keys, so what you get is a frequency distribution
    over all continuations after the given context.

    >>> sorted(ngram_counts[['a']].items())
    [('b', 1), ('c', 1)]
    >>> sorted(ngram_counts[('a',)].items())
    [('b', 1), ('c', 1)]

    This is equivalent to specifying explicitly the order of the ngram (in this case
    2 for bigram) and indexing on the context.

    >>> ngram_counts[2][('a',)] is ngram_counts[['a']]
    True

    Note that the keys in `ConditionalFreqDist` cannot be lists, only tuples!
    It is generally advisable to use the less verbose and more flexible square
    bracket notation.

    To get the count of the full ngram "a b", do this:

    >>> ngram_counts[['a']]['b']
    1

    Specifying the ngram order as a number can be useful for accessing all ngrams
    in that order.

    >>> ngram_counts[2]
    <ConditionalFreqDist with 4 conditions>

    The keys of this `ConditionalFreqDist` are the contexts we discussed earlier.
    Unigrams can also be accessed with a human-friendly alias.

    >>> ngram_counts.unigrams is ngram_counts[1]
    True

    Similarly to `collections.Counter`, you can update counts after initialization.

    >>> ngram_counts['e']
    0
    >>> ngram_counts.update([ngrams(["d", "e", "f"], 1)])
    >>> ngram_counts['e']
    1

    """

    def __init__(self, ngram_text=None):
        """Creates a new NgramCounter.

        If `ngram_text` is specified, counts ngrams from it, otherwise waits for
        `update` method to be called explicitly.

        :param ngram_text: Optional text containing sentences of ngrams, as for `update` method.
        :type ngram_text: Iterable(Iterable(tuple(str))) or None

        """
        self._counts = defaultdict(ConditionalFreqDist)
        self._counts[1] = self.unigrams = FreqDist()

        if ngram_text:
            self.update(ngram_text)

    def update(self, ngram_text):
        """Updates ngram counts from `ngram_text`.

        Expects `ngram_text` to be a sequence of sentences (sequences).
        Each sentence consists of ngrams as tuples of strings.

        :param Iterable(Iterable(tuple(str))) ngram_text: Text containing sentences of ngrams.
        :raises TypeError: if the ngrams are not tuples.

        """

        for sent in ngram_text:
            for ngram in sent:
                if not isinstance(ngram, tuple):
                    raise TypeError(
                        "Ngram <{}> isn't a tuple, " "but {}".format(ngram, type(ngram))
                    )

                ngram_order = len(ngram)
                if ngram_order == 1:
                    self.unigrams[ngram[0]] += 1
                    continue

                context, word = ngram[:-1], ngram[-1]
                self[ngram_order][context][word] += 1

    def N(self):
        """Returns grand total number of ngrams stored.

        This includes ngrams from all orders, so some duplication is expected.
        :rtype: int

        >>> from nltk.lm import NgramCounter
        >>> counts = NgramCounter([[("a", "b"), ("c",), ("d", "e")]])
        >>> counts.N()
        3

        """
        return sum(val.N() for val in self._counts.values())

    def __getitem__(self, item):
        """User-friendly access to ngram counts."""
        if isinstance(item, int):
            return self._counts[item]
        elif isinstance(item, str):
            return self._counts.__getitem__(1)[item]
        elif isinstance(item, Sequence):
            return self._counts.__getitem__(len(item) + 1)[tuple(item)]

    def __str__(self):
        return "<{} with {} ngram orders and {} ngrams>".format(
            self.__class__.__name__, len(self._counts), self.N()
        )

    def __len__(self):
        return self._counts.__len__()

    def __contains__(self, item):
        return item in self._counts

# === NexusCore/openenv\Lib\site-packages\pip\_internal\vcs\mercurial.py ===
import configparser
import logging
import os
from typing import List, Optional, Tuple

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import HiddenText, display_path
from pip._internal.utils.subprocess import make_command
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs.versioncontrol import (
    RevOptions,
    VersionControl,
    find_path_to_project_root_from_repo_root,
    vcs,
)

logger = logging.getLogger(__name__)


class Mercurial(VersionControl):
    name = "hg"
    dirname = ".hg"
    repo_name = "clone"
    schemes = (
        "hg+file",
        "hg+http",
        "hg+https",
        "hg+ssh",
        "hg+static-http",
    )

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return [f"--rev={rev}"]

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info(
            "Cloning hg %s%s to %s",
            url,
            rev_display,
            display_path(dest),
        )
        if verbosity <= 0:
            flags: Tuple[str, ...] = ("--quiet",)
        elif verbosity == 1:
            flags = ()
        elif verbosity == 2:
            flags = ("--verbose",)
        else:
            flags = ("--verbose", "--debug")
        self.run_command(make_command("clone", "--noupdate", *flags, url, dest))
        self.run_command(
            make_command("update", *flags, rev_options.to_args()),
            cwd=dest,
        )

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        repo_config = os.path.join(dest, self.dirname, "hgrc")
        config = configparser.RawConfigParser()
        try:
            config.read(repo_config)
            config.set("paths", "default", url.secret)
            with open(repo_config, "w") as config_file:
                config.write(config_file)
        except (OSError, configparser.NoSectionError) as exc:
            logger.warning("Could not switch Mercurial repository to %s: %s", url, exc)
        else:
            cmd_args = make_command("update", "-q", rev_options.to_args())
            self.run_command(cmd_args, cwd=dest)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        self.run_command(["pull", "-q"], cwd=dest)
        cmd_args = make_command("update", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        url = cls.run_command(
            ["showconfig", "paths.default"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        if cls._is_local_repository(url):
            url = path_to_url(url)
        return url.strip()

    @classmethod
    def get_revision(cls, location: str) -> str:
        """
        Return the repository-local changeset revision number, as an integer.
        """
        current_revision = cls.run_command(
            ["parents", "--template={rev}"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        return current_revision

    @classmethod
    def get_requirement_revision(cls, location: str) -> str:
        """
        Return the changeset identification hash, as a 40-character
        hexadecimal string
        """
        current_rev_hash = cls.run_command(
            ["parents", "--template={node}"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        return current_rev_hash

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """Always assume the versions don't match"""
        return False

    @classmethod
    def get_subdirectory(cls, location: str) -> Optional[str]:
        """
        Return the path to Python project root, relative to the repo root.
        Return None if the project root is in the repo root.
        """
        # find the repo root
        repo_root = cls.run_command(
            ["root"], show_stdout=False, stdout_only=True, cwd=location
        ).strip()
        if not os.path.isabs(repo_root):
            repo_root = os.path.abspath(os.path.join(location, repo_root))
        return find_path_to_project_root_from_repo_root(location, repo_root)

    @classmethod
    def get_repository_root(cls, location: str) -> Optional[str]:
        loc = super().get_repository_root(location)
        if loc:
            return loc
        try:
            r = cls.run_command(
                ["root"],
                cwd=location,
                show_stdout=False,
                stdout_only=True,
                on_returncode="raise",
                log_failed_cmd=False,
            )
        except BadCommand:
            logger.debug(
                "could not determine if %s is under hg control "
                "because hg is not available",
                location,
            )
            return None
        except InstallationError:
            return None
        return os.path.normpath(r.rstrip("\r\n"))


vcs.register(Mercurial)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\utils.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import functools
import re
from typing import NewType, Tuple, Union, cast

from .tags import Tag, parse_tag
from .version import InvalidVersion, Version, _TrimmedRelease

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


@functools.singledispatch
def canonicalize_version(
    version: Version | str, *, strip_trailing_zero: bool = True
) -> str:
    """
    Return a canonical form of a version as a string.

    >>> canonicalize_version('1.0.1')
    '1.0.1'

    Per PEP 625, versions may have multiple canonical forms, differing
    only by trailing zeros.

    >>> canonicalize_version('1.0.0')
    '1'
    >>> canonicalize_version('1.0.0', strip_trailing_zero=False)
    '1.0.0'

    Invalid versions are returned unaltered.

    >>> canonicalize_version('foo bar baz')
    'foo bar baz'
    """
    return str(_TrimmedRelease(str(version)) if strip_trailing_zero else version)


@canonicalize_version.register
def _(version: str, *, strip_trailing_zero: bool = True) -> str:
    try:
        parsed = Version(version)
    except InvalidVersion:
        # Legacy versions cannot be normalized
        return version
    return canonicalize_version(parsed, strip_trailing_zero=strip_trailing_zero)


def parse_wheel_filename(
    filename: str,
) -> tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename!r}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename!r}"
        )

    parts = filename.split("-", dashes - 2)
    name_part = parts[0]
    # See PEP 427 for the rules on escaping the project name.
    if "__" in name_part or re.match(r"^[\w\d._]*$", name_part, re.UNICODE) is None:
        raise InvalidWheelFilename(f"Invalid project name: {filename!r}")
    name = canonicalize_name(name_part)

    try:
        version = Version(parts[1])
    except InvalidVersion as e:
        raise InvalidWheelFilename(
            f"Invalid wheel filename (invalid version): {filename!r}"
        ) from e

    if dashes == 5:
        build_part = parts[2]
        build_match = _build_tag_regex.match(build_part)
        if build_match is None:
            raise InvalidWheelFilename(
                f"Invalid build number: {build_part} in {filename!r}"
            )
        build = cast(BuildTag, (int(build_match.group(1)), build_match.group(2)))
    else:
        build = ()
    tags = parse_tag(parts[-1])
    return (name, version, build, tags)


def parse_sdist_filename(filename: str) -> tuple[NormalizedName, Version]:
    if filename.endswith(".tar.gz"):
        file_stem = filename[: -len(".tar.gz")]
    elif filename.endswith(".zip"):
        file_stem = filename[: -len(".zip")]
    else:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (extension must be '.tar.gz' or '.zip'):"
            f" {filename!r}"
        )

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name_part, sep, version_part = file_stem.rpartition("-")
    if not sep:
        raise InvalidSdistFilename(f"Invalid sdist filename: {filename!r}")

    name = canonicalize_name(name_part)

    try:
        version = Version(version_part)
    except InvalidVersion as e:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (invalid version): {filename!r}"
        ) from e

    return (name, version)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_waiter.py ===
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

import asyncio
import math
import uuid
from asyncio.tasks import Task
from typing import Any, Callable, List, Tuple, Union

from pyee import EventEmitter

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import Error, TimeoutError


class Waiter:
    def __init__(self, channel_owner: ChannelOwner, event: str) -> None:
        self._result: asyncio.Future = asyncio.Future()
        self._wait_id = uuid.uuid4().hex
        self._loop = channel_owner._loop
        self._pending_tasks: List[Task] = []
        self._channel = channel_owner._channel
        self._registered_listeners: List[Tuple[EventEmitter, str, Callable]] = []
        self._logs: List[str] = []
        self._wait_for_event_info_before(self._wait_id, event)

    def _wait_for_event_info_before(self, wait_id: str, event: str) -> None:
        self._channel.send_no_reply(
            "waitForEventInfo",
            {
                "info": {
                    "waitId": wait_id,
                    "phase": "before",
                    "event": event,
                }
            },
        )

    def _wait_for_event_info_after(self, wait_id: str, error: Exception = None) -> None:
        self._channel._connection.wrap_api_call_sync(
            lambda: self._channel.send_no_reply(
                "waitForEventInfo",
                {
                    "info": {
                        "waitId": wait_id,
                        "phase": "after",
                        **({"error": str(error)} if error else {}),
                    },
                },
            ),
            True,
        )

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Union[Error, Callable[..., Error]],
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._reject(error() if callable(error) else error)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def reject_on_timeout(self, timeout: float, message: str) -> None:
        if timeout == 0:
            return

        async def reject() -> None:
            await asyncio.sleep(timeout / 1000)
            self._reject(TimeoutError(message))

        self._pending_tasks.append(self._loop.create_task(reject()))

    def _cleanup(self) -> None:
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        for listener in self._registered_listeners:
            listener[0].remove_listener(listener[1], listener[2])

    def _fulfill(self, result: Any) -> None:
        self._cleanup()
        if not self._result.done():
            self._result.set_result(result)
        self._wait_for_event_info_after(self._wait_id)

    def _reject(self, exception: Exception) -> None:
        self._cleanup()
        if exception:
            base_class = TimeoutError if isinstance(exception, TimeoutError) else Error
            exception = base_class(str(exception) + format_log_recording(self._logs))
        if not self._result.done():
            self._result.set_exception(exception)
        self._wait_for_event_info_after(self._wait_id, exception)

    def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._fulfill(event_data)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def result(self) -> asyncio.Future:
        return self._result

    def log(self, message: str) -> None:
        self._logs.append(message)
        try:
            self._channel._connection.wrap_api_call_sync(
                lambda: self._channel.send_no_reply(
                    "waitForEventInfo",
                    {
                        "info": {
                            "waitId": self._wait_id,
                            "phase": "log",
                            "message": message,
                        },
                    },
                ),
                True,
            )
        except Exception:
            pass


def throw_on_timeout(timeout: float, exception: Exception) -> asyncio.Task:
    async def throw() -> None:
        await asyncio.sleep(timeout / 1000)
        raise exception

    return asyncio.create_task(throw())


def format_log_recording(log: List[str]) -> str:
    if not log:
        return ""
    header = " logs "
    header_length = 60
    left_length = math.floor((header_length - len(header)) / 2)
    right_length = header_length - len(header) - left_length
    new_line = "\n"
    return f"{new_line}{'=' * left_length}{header}{'=' * right_length}{new_line}{new_line.join(log)}{new_line}{'=' * header_length}"

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\extensions.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Extensions (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class StorageArea(enum.Enum):
    '''
    Storage areas.
    '''
    SESSION = "session"
    LOCAL = "local"
    SYNC = "sync"
    MANAGED = "managed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def load_unpacked(
        path: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Installs an unpacked extension from the filesystem similar to
    --load-extension CLI flags. Returns extension ID once the extension
    has been installed. Available if the client is connected using the
    --remote-debugging-pipe flag and the --enable-unsafe-extension-debugging
    flag is set.

    :param path: Absolute file path.
    :returns: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['path'] = path
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.loadUnpacked',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['id'])


def uninstall(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls an unpacked extension (others not supported) from the profile.
    Available if the client is connected using the --remote-debugging-pipe flag
    and the --enable-unsafe-extension-debugging.

    :param id_: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def get_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets data from extension storage in the given ``storageArea``. If ``keys`` is
    specified, these are used to filter the result.

    :param id_: ID of extension.
    :param storage_area: StorageArea to retrieve data from.
    :param keys: *(Optional)* Keys to retrieve.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    if keys is not None:
        params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.getStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['data'])


def remove_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes ``keys`` from extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    :param keys: Keys to remove.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.removeStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def clear_storage_items(
        id_: str,
        storage_area: StorageArea
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.clearStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_items(
        id_: str,
        storage_area: StorageArea,
        values: dict
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets ``values`` in extension storage in the given ``storageArea``. The provided ``values``
    will be merged with existing values in the storage area.

    :param id_: ID of extension.
    :param storage_area: StorageArea to set data in.
    :param values: Values to set.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['values'] = values
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.setStorageItems',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\extensions.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Extensions (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class StorageArea(enum.Enum):
    '''
    Storage areas.
    '''
    SESSION = "session"
    LOCAL = "local"
    SYNC = "sync"
    MANAGED = "managed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def load_unpacked(
        path: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Installs an unpacked extension from the filesystem similar to
    --load-extension CLI flags. Returns extension ID once the extension
    has been installed. Available if the client is connected using the
    --remote-debugging-pipe flag and the --enable-unsafe-extension-debugging
    flag is set.

    :param path: Absolute file path.
    :returns: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['path'] = path
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.loadUnpacked',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['id'])


def uninstall(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls an unpacked extension (others not supported) from the profile.
    Available if the client is connected using the --remote-debugging-pipe flag
    and the --enable-unsafe-extension-debugging.

    :param id_: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def get_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets data from extension storage in the given ``storageArea``. If ``keys`` is
    specified, these are used to filter the result.

    :param id_: ID of extension.
    :param storage_area: StorageArea to retrieve data from.
    :param keys: *(Optional)* Keys to retrieve.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    if keys is not None:
        params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.getStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['data'])


def remove_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes ``keys`` from extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    :param keys: Keys to remove.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.removeStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def clear_storage_items(
        id_: str,
        storage_area: StorageArea
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.clearStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_items(
        id_: str,
        storage_area: StorageArea,
        values: dict
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets ``values`` in extension storage in the given ``storageArea``. The provided ``values``
    will be merged with existing values in the storage area.

    :param id_: ID of extension.
    :param storage_area: StorageArea to set data in.
    :param values: Values to set.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['values'] = values
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.setStorageItems',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\extensions.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Extensions (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class StorageArea(enum.Enum):
    '''
    Storage areas.
    '''
    SESSION = "session"
    LOCAL = "local"
    SYNC = "sync"
    MANAGED = "managed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def load_unpacked(
        path: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Installs an unpacked extension from the filesystem similar to
    --load-extension CLI flags. Returns extension ID once the extension
    has been installed. Available if the client is connected using the
    --remote-debugging-pipe flag and the --enable-unsafe-extension-debugging
    flag is set.

    :param path: Absolute file path.
    :returns: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['path'] = path
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.loadUnpacked',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['id'])


def uninstall(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls an unpacked extension (others not supported) from the profile.
    Available if the client is connected using the --remote-debugging-pipe flag
    and the --enable-unsafe-extension-debugging.

    :param id_: Extension id.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def get_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets data from extension storage in the given ``storageArea``. If ``keys`` is
    specified, these are used to filter the result.

    :param id_: ID of extension.
    :param storage_area: StorageArea to retrieve data from.
    :param keys: *(Optional)* Keys to retrieve.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    if keys is not None:
        params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.getStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['data'])


def remove_storage_items(
        id_: str,
        storage_area: StorageArea,
        keys: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes ``keys`` from extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    :param keys: Keys to remove.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['keys'] = [i for i in keys]
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.removeStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def clear_storage_items(
        id_: str,
        storage_area: StorageArea
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears extension storage in the given ``storageArea``.

    :param id_: ID of extension.
    :param storage_area: StorageArea to remove data from.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.clearStorageItems',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_items(
        id_: str,
        storage_area: StorageArea,
        values: dict
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets ``values`` in extension storage in the given ``storageArea``. The provided ``values``
    will be merged with existing values in the storage area.

    :param id_: ID of extension.
    :param storage_area: StorageArea to set data in.
    :param values: Values to set.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    params['storageArea'] = storage_area.to_json()
    params['values'] = values
    cmd_dict: T_JSON_DICT = {
        'method': 'Extensions.setStorageItems',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\utils.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import functools
import re
from typing import NewType, Tuple, Union, cast

from .tags import Tag, parse_tag
from .version import InvalidVersion, Version, _TrimmedRelease

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


@functools.singledispatch
def canonicalize_version(
    version: Version | str, *, strip_trailing_zero: bool = True
) -> str:
    """
    Return a canonical form of a version as a string.

    >>> canonicalize_version('1.0.1')
    '1.0.1'

    Per PEP 625, versions may have multiple canonical forms, differing
    only by trailing zeros.

    >>> canonicalize_version('1.0.0')
    '1'
    >>> canonicalize_version('1.0.0', strip_trailing_zero=False)
    '1.0.0'

    Invalid versions are returned unaltered.

    >>> canonicalize_version('foo bar baz')
    'foo bar baz'
    """
    return str(_TrimmedRelease(str(version)) if strip_trailing_zero else version)


@canonicalize_version.register
def _(version: str, *, strip_trailing_zero: bool = True) -> str:
    try:
        parsed = Version(version)
    except InvalidVersion:
        # Legacy versions cannot be normalized
        return version
    return canonicalize_version(parsed, strip_trailing_zero=strip_trailing_zero)


def parse_wheel_filename(
    filename: str,
) -> tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename!r}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename!r}"
        )

    parts = filename.split("-", dashes - 2)
    name_part = parts[0]
    # See PEP 427 for the rules on escaping the project name.
    if "__" in name_part or re.match(r"^[\w\d._]*$", name_part, re.UNICODE) is None:
        raise InvalidWheelFilename(f"Invalid project name: {filename!r}")
    name = canonicalize_name(name_part)

    try:
        version = Version(parts[1])
    except InvalidVersion as e:
        raise InvalidWheelFilename(
            f"Invalid wheel filename (invalid version): {filename!r}"
        ) from e

    if dashes == 5:
        build_part = parts[2]
        build_match = _build_tag_regex.match(build_part)
        if build_match is None:
            raise InvalidWheelFilename(
                f"Invalid build number: {build_part} in {filename!r}"
            )
        build = cast(BuildTag, (int(build_match.group(1)), build_match.group(2)))
    else:
        build = ()
    tags = parse_tag(parts[-1])
    return (name, version, build, tags)


def parse_sdist_filename(filename: str) -> tuple[NormalizedName, Version]:
    if filename.endswith(".tar.gz"):
        file_stem = filename[: -len(".tar.gz")]
    elif filename.endswith(".zip"):
        file_stem = filename[: -len(".zip")]
    else:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (extension must be '.tar.gz' or '.zip'):"
            f" {filename!r}"
        )

    # We are requiring a PEP 440 version, which cannot contain dashes,
    # so we split on the last dash.
    name_part, sep, version_part = file_stem.rpartition("-")
    if not sep:
        raise InvalidSdistFilename(f"Invalid sdist filename: {filename!r}")

    name = canonicalize_name(name_part)

    try:
        version = Version(version_part)
    except InvalidVersion as e:
        raise InvalidSdistFilename(
            f"Invalid sdist filename (invalid version): {filename!r}"
        ) from e

    return (name, version)

# === NexusCore/openenv\Lib\site-packages\trio\_core\_unbounded_queue.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

import attrs

from .. import _core
from .._deprecate import deprecated
from .._util import final

T = TypeVar("T")

if TYPE_CHECKING:
    from typing_extensions import Self


@attrs.frozen
class UnboundedQueueStatistics:
    """An object containing debugging information.

    Currently, the following fields are defined:

    * ``qsize``: The number of items currently in the queue.
    * ``tasks_waiting``: The number of tasks blocked on this queue's
      :meth:`get_batch` method.

    """

    qsize: int
    tasks_waiting: int


@final
class UnboundedQueue(Generic[T]):
    """An unbounded queue suitable for certain unusual forms of inter-task
    communication.

    This class is designed for use as a queue in cases where the producer for
    some reason cannot be subjected to back-pressure, i.e., :meth:`put_nowait`
    has to always succeed. In order to prevent the queue backlog from actually
    growing without bound, the consumer API is modified to dequeue items in
    "batches". If a consumer task processes each batch without yielding, then
    this helps achieve (but does not guarantee) an effective bound on the
    queue's memory use, at the cost of potentially increasing system latencies
    in general. You should generally prefer to use a memory channel
    instead if you can.

    Currently each batch completely empties the queue, but `this may change in
    the future <https://github.com/python-trio/trio/issues/51>`__.

    A :class:`UnboundedQueue` object can be used as an asynchronous iterator,
    where each iteration returns a new batch of items. I.e., these two loops
    are equivalent::

       async for batch in queue:
           ...

       while True:
           obj = await queue.get_batch()
           ...

    """

    @deprecated(
        "0.9.0",
        issue=497,
        thing="trio.lowlevel.UnboundedQueue",
        instead="trio.open_memory_channel(math.inf)",
        use_triodeprecationwarning=True,
    )
    def __init__(self) -> None:
        self._lot = _core.ParkingLot()
        self._data: list[T] = []
        # used to allow handoff from put to the first task in the lot
        self._can_get = False

    def __repr__(self) -> str:
        return f"<UnboundedQueue holding {len(self._data)} items>"

    def qsize(self) -> int:
        """Returns the number of items currently in the queue."""
        return len(self._data)

    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise.

        There is some subtlety to interpreting this method's return value: see
        `issue #63 <https://github.com/python-trio/trio/issues/63>`__.

        """
        return not self._data

    @_core.enable_ki_protection
    def put_nowait(self, obj: T) -> None:
        """Put an object into the queue, without blocking.

        This always succeeds, because the queue is unbounded. We don't provide
        a blocking ``put`` method, because it would never need to block.

        Args:
          obj (object): The object to enqueue.

        """
        if not self._data:
            assert not self._can_get
            if self._lot:
                self._lot.unpark(count=1)
            else:
                self._can_get = True
        self._data.append(obj)

    def _get_batch_protected(self) -> list[T]:
        data = self._data.copy()
        self._data.clear()
        self._can_get = False
        return data

    def get_batch_nowait(self) -> list[T]:
        """Attempt to get the next batch from the queue, without blocking.

        Returns:
          list: A list of dequeued items, in order. On a successful call this
              list is always non-empty; if it would be empty we raise
              :exc:`~trio.WouldBlock` instead.

        Raises:
          ~trio.WouldBlock: if the queue is empty.

        """
        if not self._can_get:
            raise _core.WouldBlock
        return self._get_batch_protected()

    async def get_batch(self) -> list[T]:
        """Get the next batch from the queue, blocking as necessary.

        Returns:
          list: A list of dequeued items, in order. This list is always
              non-empty.

        """
        await _core.checkpoint_if_cancelled()
        if not self._can_get:
            await self._lot.park()
            return self._get_batch_protected()
        else:
            try:
                return self._get_batch_protected()
            finally:
                await _core.cancel_shielded_checkpoint()

    def statistics(self) -> UnboundedQueueStatistics:
        """Return an :class:`UnboundedQueueStatistics` object containing debugging information."""
        return UnboundedQueueStatistics(
            qsize=len(self._data),
            tasks_waiting=self._lot.statistics().tasks_waiting,
        )

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> list[T]:
        return await self.get_batch()

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\core\os_manager.py ===
import platform
import sys

from webdriver_manager.core.utils import linux_browser_apps_to_cmd, windows_browser_apps_to_cmd, \
    read_version_from_cmd


class ChromeType(object):
    GOOGLE = "google-chrome"
    CHROMIUM = "chromium"
    BRAVE = "brave-browser"
    MSEDGE = "edge"


class OSType(object):
    LINUX = "linux"
    MAC = "mac"
    WIN = "win"


PATTERN = {
    ChromeType.CHROMIUM: r"\d+\.\d+\.\d+",
    ChromeType.GOOGLE: r"\d+\.\d+\.\d+",
    ChromeType.MSEDGE: r"\d+\.\d+\.\d+",
    "brave-browser": r"\d+\.\d+\.\d+(\.\d+)?",
    "firefox": r"(\d+.\d+)",
}


class OperationSystemManager(object):

    def __init__(self, os_type=None):
        self._os_type = os_type

    @staticmethod
    def get_os_name():
        pl = sys.platform
        if pl == "linux" or pl == "linux2":
            return OSType.LINUX
        elif pl == "darwin":
            return OSType.MAC
        elif pl == "win32" or pl == "cygwin":
            return OSType.WIN

    @staticmethod
    def get_os_architecture():
        if platform.machine().endswith("64"):
            return 64
        else:
            return 32

    def get_os_type(self):
        if self._os_type:
            return self._os_type
        return f"{self.get_os_name()}{self.get_os_architecture()}"

    @staticmethod
    def is_arch(os_sys_type):
        if '_m1' in os_sys_type:
            return True
        return platform.processor() != 'i386'

    @staticmethod
    def is_mac_os(os_sys_type):
        return OSType.MAC in os_sys_type

    def get_browser_version_from_os(self, browser_type=None):
        """Return installed browser version."""
        cmd_mapping = {
            ChromeType.GOOGLE: {
                OSType.LINUX: linux_browser_apps_to_cmd(
                    "google-chrome",
                    "google-chrome-stable",
                    "google-chrome-beta",
                    "google-chrome-dev",
                ),
                OSType.MAC: r"/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version",
                OSType.WIN: windows_browser_apps_to_cmd(
                    r'(Get-Item -Path "$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Google\Chrome\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Google\Chrome\BLBeacon").version',
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome").version',
                ),
            },
            ChromeType.CHROMIUM: {
                OSType.LINUX: linux_browser_apps_to_cmd("chromium", "chromium-browser"),
                OSType.MAC: r"/Applications/Chromium.app/Contents/MacOS/Chromium --version",
                OSType.WIN: windows_browser_apps_to_cmd(
                    r'(Get-Item -Path "$env:PROGRAMFILES\Chromium\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Chromium\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:LOCALAPPDATA\Chromium\Application\chrome.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Chromium\BLBeacon").version',
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Chromium").version',
                ),
            },
            ChromeType.BRAVE: {
                OSType.LINUX: linux_browser_apps_to_cmd(
                    "brave-browser", "brave-browser-beta", "brave-browser-nightly"
                ),
                OSType.MAC: r"/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --version",
                OSType.WIN: windows_browser_apps_to_cmd(
                    r'(Get-Item -Path "$env:PROGRAMFILES\BraveSoftware\Brave-Browser\Application\brave.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\BraveSoftware\Brave-Browser\Application\brave.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\BraveSoftware\Brave-Browser\BLBeacon").version',
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\BraveSoftware Brave-Browser").version',
                ),
            },
            ChromeType.MSEDGE: {
                OSType.LINUX: linux_browser_apps_to_cmd(
                    "microsoft-edge",
                    "microsoft-edge-stable",
                    "microsoft-edge-beta",
                    "microsoft-edge-dev",
                ),
                OSType.MAC: r"/Applications/Microsoft\ Edge.app/Contents/MacOS/Microsoft\ Edge --version",
                OSType.WIN: windows_browser_apps_to_cmd(
                    # stable edge
                    r'(Get-Item -Path "$env:PROGRAMFILES\Microsoft\Edge\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Microsoft\Edge\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Microsoft\Edge\BLBeacon").version',
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{56EB18F8-8008-4CBD-B6D2-8C97FE7E9062}").pv',
                    # beta edge
                    r'(Get-Item -Path "$env:LOCALAPPDATA\Microsoft\Edge Beta\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES\Microsoft\Edge Beta\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Microsoft\Edge Beta\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Microsoft\Edge Beta\BLBeacon").version',
                    # dev edge
                    r'(Get-Item -Path "$env:LOCALAPPDATA\Microsoft\Edge Dev\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES\Microsoft\Edge Dev\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Microsoft\Edge Dev\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Microsoft\Edge Dev\BLBeacon").version',
                    # canary edge
                    r'(Get-Item -Path "$env:LOCALAPPDATA\Microsoft\Edge SxS\Application\msedge.exe").VersionInfo.FileVersion',
                    r'(Get-ItemProperty -Path Registry::"HKCU\SOFTWARE\Microsoft\Edge SxS\BLBeacon").version',
                    # highest edge
                    r"(Get-Item (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe').'(Default)').VersionInfo.ProductVersion",
                    r"[System.Diagnostics.FileVersionInfo]::GetVersionInfo((Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe').'(Default)').ProductVersion",
                    r"Get-AppxPackage -Name *MicrosoftEdge.* | Foreach Version",
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Edge").version',
                ),
            },
            "firefox": {
                OSType.LINUX: linux_browser_apps_to_cmd("firefox"),
                OSType.MAC: r"/Applications/Firefox.app/Contents/MacOS/firefox --version",
                OSType.WIN: windows_browser_apps_to_cmd(
                    r'(Get-Item -Path "$env:PROGRAMFILES\Mozilla Firefox\firefox.exe").VersionInfo.FileVersion',
                    r'(Get-Item -Path "$env:PROGRAMFILES (x86)\Mozilla Firefox\firefox.exe").VersionInfo.FileVersion',
                    r"(Get-Item (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe').'(Default)').VersionInfo.ProductVersion",
                    r'(Get-ItemProperty -Path Registry::"HKLM\SOFTWARE\Mozilla\Mozilla Firefox").CurrentVersion',
                ),
            },
        }

        try:
            cmd_mapping = cmd_mapping[browser_type][OperationSystemManager.get_os_name()]
            pattern = PATTERN[browser_type]
            version = read_version_from_cmd(cmd_mapping, pattern)
            return version
        except Exception:
            return None
            # raise Exception("Can not get browser version from OS")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\markers.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Parser for the environment markers micro-language defined in PEP 508.
"""

# Note: In PEP 345, the micro-language was Python compatible, so the ast
# module could be used to parse it. However, PEP 508 introduced operators such
# as ~= and === which aren't in Python, necessitating a different approach.

import os
import re
import sys
import platform

from .compat import string_types
from .util import in_venv, parse_marker
from .version import LegacyVersion as LV

__all__ = ['interpret']

_VERSION_PATTERN = re.compile(r'((\d+(\.\d+)*\w*)|\'(\d+(\.\d+)*\w*)\'|\"(\d+(\.\d+)*\w*)\")')
_VERSION_MARKERS = {'python_version', 'python_full_version'}


def _is_version_marker(s):
    return isinstance(s, string_types) and s in _VERSION_MARKERS


def _is_literal(o):
    if not isinstance(o, string_types) or not o:
        return False
    return o[0] in '\'"'


def _get_versions(s):
    return {LV(m.groups()[0]) for m in _VERSION_PATTERN.finditer(s)}


class Evaluator(object):
    """
    This class is used to evaluate marker expressions.
    """

    operations = {
        '==': lambda x, y: x == y,
        '===': lambda x, y: x == y,
        '~=': lambda x, y: x == y or x > y,
        '!=': lambda x, y: x != y,
        '<': lambda x, y: x < y,
        '<=': lambda x, y: x == y or x < y,
        '>': lambda x, y: x > y,
        '>=': lambda x, y: x == y or x > y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
    }

    def evaluate(self, expr, context):
        """
        Evaluate a marker expression returned by the :func:`parse_requirement`
        function in the specified context.
        """
        if isinstance(expr, string_types):
            if expr[0] in '\'"':
                result = expr[1:-1]
            else:
                if expr not in context:
                    raise SyntaxError('unknown variable: %s' % expr)
                result = context[expr]
        else:
            assert isinstance(expr, dict)
            op = expr['op']
            if op not in self.operations:
                raise NotImplementedError('op not implemented: %s' % op)
            elhs = expr['lhs']
            erhs = expr['rhs']
            if _is_literal(expr['lhs']) and _is_literal(expr['rhs']):
                raise SyntaxError('invalid comparison: %s %s %s' % (elhs, op, erhs))

            lhs = self.evaluate(elhs, context)
            rhs = self.evaluate(erhs, context)
            if ((_is_version_marker(elhs) or _is_version_marker(erhs)) and
                    op in ('<', '<=', '>', '>=', '===', '==', '!=', '~=')):
                lhs = LV(lhs)
                rhs = LV(rhs)
            elif _is_version_marker(elhs) and op in ('in', 'not in'):
                lhs = LV(lhs)
                rhs = _get_versions(rhs)
            result = self.operations[op](lhs, rhs)
        return result


_DIGITS = re.compile(r'\d+\.\d+')


def default_context():

    def format_full_version(info):
        version = '%s.%s.%s' % (info.major, info.minor, info.micro)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)
        return version

    if hasattr(sys, 'implementation'):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = '0'
        implementation_name = ''

    ppv = platform.python_version()
    m = _DIGITS.match(ppv)
    pv = m.group(0)
    result = {
        'implementation_name': implementation_name,
        'implementation_version': implementation_version,
        'os_name': os.name,
        'platform_machine': platform.machine(),
        'platform_python_implementation': platform.python_implementation(),
        'platform_release': platform.release(),
        'platform_system': platform.system(),
        'platform_version': platform.version(),
        'platform_in_venv': str(in_venv()),
        'python_full_version': ppv,
        'python_version': pv,
        'sys_platform': sys.platform,
    }
    return result


DEFAULT_CONTEXT = default_context()
del default_context

evaluator = Evaluator()


def interpret(marker, execution_context=None):
    """
    Interpret a marker and return a result depending on environment.

    :param marker: The marker to interpret.
    :type marker: str
    :param execution_context: The context used for name lookup.
    :type execution_context: mapping
    """
    try:
        expr, rest = parse_marker(marker)
    except Exception as e:
        raise SyntaxError('Unable to interpret marker syntax: %s: %s' % (marker, e))
    if rest and rest[0] != '#':
        raise SyntaxError('unexpected trailing data in marker: %s: %s' % (marker, rest))
    context = dict(DEFAULT_CONTEXT)
    if execution_context:
        context.update(execution_context)
    return evaluator.evaluate(expr, context)

# === NexusCore/openenv\Lib\site-packages\attr\converters.py ===
# SPDX-License-Identifier: MIT

"""
Commonly useful converters.
"""

import typing

from ._compat import _AnnotationExtractor
from ._make import NOTHING, Converter, Factory, pipe


__all__ = [
    "default_if_none",
    "optional",
    "pipe",
    "to_bool",
]


def optional(converter):
    """
    A converter that allows an attribute to be optional. An optional attribute
    is one which can be set to `None`.

    Type annotations will be inferred from the wrapped converter's, if it has
    any.

    Args:
        converter (typing.Callable):
            the converter that is used for non-`None` values.

    .. versionadded:: 17.1.0
    """

    if isinstance(converter, Converter):

        def optional_converter(val, inst, field):
            if val is None:
                return None
            return converter(val, inst, field)

    else:

        def optional_converter(val):
            if val is None:
                return None
            return converter(val)

    xtr = _AnnotationExtractor(converter)

    t = xtr.get_first_param_type()
    if t:
        optional_converter.__annotations__["val"] = typing.Optional[t]

    rt = xtr.get_return_type()
    if rt:
        optional_converter.__annotations__["return"] = typing.Optional[rt]

    if isinstance(converter, Converter):
        return Converter(optional_converter, takes_self=True, takes_field=True)

    return optional_converter


def default_if_none(default=NOTHING, factory=None):
    """
    A converter that allows to replace `None` values by *default* or the result
    of *factory*.

    Args:
        default:
            Value to be used if `None` is passed. Passing an instance of
            `attrs.Factory` is supported, however the ``takes_self`` option is
            *not*.

        factory (typing.Callable):
            A callable that takes no parameters whose result is used if `None`
            is passed.

    Raises:
        TypeError: If **neither** *default* or *factory* is passed.

        TypeError: If **both** *default* and *factory* are passed.

        ValueError:
            If an instance of `attrs.Factory` is passed with
            ``takes_self=True``.

    .. versionadded:: 18.2.0
    """
    if default is NOTHING and factory is None:
        msg = "Must pass either `default` or `factory`."
        raise TypeError(msg)

    if default is not NOTHING and factory is not None:
        msg = "Must pass either `default` or `factory` but not both."
        raise TypeError(msg)

    if factory is not None:
        default = Factory(factory)

    if isinstance(default, Factory):
        if default.takes_self:
            msg = "`takes_self` is not supported by default_if_none."
            raise ValueError(msg)

        def default_if_none_converter(val):
            if val is not None:
                return val

            return default.factory()

    else:

        def default_if_none_converter(val):
            if val is not None:
                return val

            return default

    return default_if_none_converter


def to_bool(val):
    """
    Convert "boolean" strings (for example, from environment variables) to real
    booleans.

    Values mapping to `True`:

    - ``True``
    - ``"true"`` / ``"t"``
    - ``"yes"`` / ``"y"``
    - ``"on"``
    - ``"1"``
    - ``1``

    Values mapping to `False`:

    - ``False``
    - ``"false"`` / ``"f"``
    - ``"no"`` / ``"n"``
    - ``"off"``
    - ``"0"``
    - ``0``

    Raises:
        ValueError: For any other value.

    .. versionadded:: 21.3.0
    """
    if isinstance(val, str):
        val = val.lower()

    if val in (True, "true", "t", "yes", "y", "on", "1", 1):
        return True
    if val in (False, "false", "f", "no", "n", "off", "0", 0):
        return False

    msg = f"Cannot convert value to bool: {val!r}"
    raise ValueError(msg)

# === NexusCore/openenv\Lib\site-packages\httpx\_status_codes.py ===
from __future__ import annotations

from enum import IntEnum

__all__ = ["codes"]


class codes(IntEnum):
    """HTTP status codes and reason phrases

    Status codes from the following RFCs are all observed:

        * RFC 7231: Hypertext Transfer Protocol (HTTP/1.1), obsoletes 2616
        * RFC 6585: Additional HTTP Status Codes
        * RFC 3229: Delta encoding in HTTP
        * RFC 4918: HTTP Extensions for WebDAV, obsoletes 2518
        * RFC 5842: Binding Extensions to WebDAV
        * RFC 7238: Permanent Redirect
        * RFC 2295: Transparent Content Negotiation in HTTP
        * RFC 2774: An HTTP Extension Framework
        * RFC 7540: Hypertext Transfer Protocol Version 2 (HTTP/2)
        * RFC 2324: Hyper Text Coffee Pot Control Protocol (HTCPCP/1.0)
        * RFC 7725: An HTTP Status Code to Report Legal Obstacles
        * RFC 8297: An HTTP Status Code for Indicating Hints
        * RFC 8470: Using Early Data in HTTP
    """

    def __new__(cls, value: int, phrase: str = "") -> codes:
        obj = int.__new__(cls, value)
        obj._value_ = value

        obj.phrase = phrase  # type: ignore[attr-defined]
        return obj

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def get_reason_phrase(cls, value: int) -> str:
        try:
            return codes(value).phrase  # type: ignore
        except ValueError:
            return ""

    @classmethod
    def is_informational(cls, value: int) -> bool:
        """
        Returns `True` for 1xx status codes, `False` otherwise.
        """
        return 100 <= value <= 199

    @classmethod
    def is_success(cls, value: int) -> bool:
        """
        Returns `True` for 2xx status codes, `False` otherwise.
        """
        return 200 <= value <= 299

    @classmethod
    def is_redirect(cls, value: int) -> bool:
        """
        Returns `True` for 3xx status codes, `False` otherwise.
        """
        return 300 <= value <= 399

    @classmethod
    def is_client_error(cls, value: int) -> bool:
        """
        Returns `True` for 4xx status codes, `False` otherwise.
        """
        return 400 <= value <= 499

    @classmethod
    def is_server_error(cls, value: int) -> bool:
        """
        Returns `True` for 5xx status codes, `False` otherwise.
        """
        return 500 <= value <= 599

    @classmethod
    def is_error(cls, value: int) -> bool:
        """
        Returns `True` for 4xx or 5xx status codes, `False` otherwise.
        """
        return 400 <= value <= 599

    # informational
    CONTINUE = 100, "Continue"
    SWITCHING_PROTOCOLS = 101, "Switching Protocols"
    PROCESSING = 102, "Processing"
    EARLY_HINTS = 103, "Early Hints"

    # success
    OK = 200, "OK"
    CREATED = 201, "Created"
    ACCEPTED = 202, "Accepted"
    NON_AUTHORITATIVE_INFORMATION = 203, "Non-Authoritative Information"
    NO_CONTENT = 204, "No Content"
    RESET_CONTENT = 205, "Reset Content"
    PARTIAL_CONTENT = 206, "Partial Content"
    MULTI_STATUS = 207, "Multi-Status"
    ALREADY_REPORTED = 208, "Already Reported"
    IM_USED = 226, "IM Used"

    # redirection
    MULTIPLE_CHOICES = 300, "Multiple Choices"
    MOVED_PERMANENTLY = 301, "Moved Permanently"
    FOUND = 302, "Found"
    SEE_OTHER = 303, "See Other"
    NOT_MODIFIED = 304, "Not Modified"
    USE_PROXY = 305, "Use Proxy"
    TEMPORARY_REDIRECT = 307, "Temporary Redirect"
    PERMANENT_REDIRECT = 308, "Permanent Redirect"

    # client error
    BAD_REQUEST = 400, "Bad Request"
    UNAUTHORIZED = 401, "Unauthorized"
    PAYMENT_REQUIRED = 402, "Payment Required"
    FORBIDDEN = 403, "Forbidden"
    NOT_FOUND = 404, "Not Found"
    METHOD_NOT_ALLOWED = 405, "Method Not Allowed"
    NOT_ACCEPTABLE = 406, "Not Acceptable"
    PROXY_AUTHENTICATION_REQUIRED = 407, "Proxy Authentication Required"
    REQUEST_TIMEOUT = 408, "Request Timeout"
    CONFLICT = 409, "Conflict"
    GONE = 410, "Gone"
    LENGTH_REQUIRED = 411, "Length Required"
    PRECONDITION_FAILED = 412, "Precondition Failed"
    REQUEST_ENTITY_TOO_LARGE = 413, "Request Entity Too Large"
    REQUEST_URI_TOO_LONG = 414, "Request-URI Too Long"
    UNSUPPORTED_MEDIA_TYPE = 415, "Unsupported Media Type"
    REQUESTED_RANGE_NOT_SATISFIABLE = 416, "Requested Range Not Satisfiable"
    EXPECTATION_FAILED = 417, "Expectation Failed"
    IM_A_TEAPOT = 418, "I'm a teapot"
    MISDIRECTED_REQUEST = 421, "Misdirected Request"
    UNPROCESSABLE_ENTITY = 422, "Unprocessable Entity"
    LOCKED = 423, "Locked"
    FAILED_DEPENDENCY = 424, "Failed Dependency"
    TOO_EARLY = 425, "Too Early"
    UPGRADE_REQUIRED = 426, "Upgrade Required"
    PRECONDITION_REQUIRED = 428, "Precondition Required"
    TOO_MANY_REQUESTS = 429, "Too Many Requests"
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, "Request Header Fields Too Large"
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, "Unavailable For Legal Reasons"

    # server errors
    INTERNAL_SERVER_ERROR = 500, "Internal Server Error"
    NOT_IMPLEMENTED = 501, "Not Implemented"
    BAD_GATEWAY = 502, "Bad Gateway"
    SERVICE_UNAVAILABLE = 503, "Service Unavailable"
    GATEWAY_TIMEOUT = 504, "Gateway Timeout"
    HTTP_VERSION_NOT_SUPPORTED = 505, "HTTP Version Not Supported"
    VARIANT_ALSO_NEGOTIATES = 506, "Variant Also Negotiates"
    INSUFFICIENT_STORAGE = 507, "Insufficient Storage"
    LOOP_DETECTED = 508, "Loop Detected"
    NOT_EXTENDED = 510, "Not Extended"
    NETWORK_AUTHENTICATION_REQUIRED = 511, "Network Authentication Required"


# Include lower-case styles for `requests` compatibility.
for code in codes:
    setattr(codes, code._name_.lower(), int(code))

# === NexusCore/openenv\Lib\site-packages\jupyter_client\restarter.py ===
"""A basic kernel monitor with autorestarting.

This watches a kernel's state using KernelManager.is_alive and auto
restarts the kernel if it dies.

It is an incomplete base class, and must be subclassed.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import time
import typing as t

from traitlets import Bool, Dict, Float, Instance, Integer, default
from traitlets.config.configurable import LoggingConfigurable


class KernelRestarter(LoggingConfigurable):
    """Monitor and autorestart a kernel."""

    kernel_manager = Instance("jupyter_client.KernelManager")

    debug = Bool(
        False,
        config=True,
        help="""Whether to include every poll event in debugging output.

        Has to be set explicitly, because there will be *a lot* of output.
        """,
    )

    time_to_dead = Float(3.0, config=True, help="""Kernel heartbeat interval in seconds.""")

    stable_start_time = Float(
        10.0,
        config=True,
        help="""The time in seconds to consider the kernel to have completed a stable start up.""",
    )

    restart_limit = Integer(
        5,
        config=True,
        help="""The number of consecutive autorestarts before the kernel is presumed dead.""",
    )

    random_ports_until_alive = Bool(
        True,
        config=True,
        help="""Whether to choose new random ports when restarting before the kernel is alive.""",
    )
    _restarting = Bool(False)
    _restart_count = Integer(0)
    _initial_startup = Bool(True)
    _last_dead = Float()

    @default("_last_dead")
    def _default_last_dead(self) -> float:
        return time.time()

    callbacks = Dict()

    def _callbacks_default(self) -> dict[str, list]:
        return {"restart": [], "dead": []}

    def start(self) -> None:
        """Start the polling of the kernel."""
        msg = "Must be implemented in a subclass"
        raise NotImplementedError(msg)

    def stop(self) -> None:
        """Stop the kernel polling."""
        msg = "Must be implemented in a subclass"
        raise NotImplementedError(msg)

    def add_callback(self, f: t.Callable[..., t.Any], event: str = "restart") -> None:
        """register a callback to fire on a particular event

        Possible values for event:

          'restart' (default): kernel has died, and will be restarted.
          'dead': restart has failed, kernel will be left dead.

        """
        self.callbacks[event].append(f)

    def remove_callback(self, f: t.Callable[..., t.Any], event: str = "restart") -> None:
        """unregister a callback to fire on a particular event

        Possible values for event:

          'restart' (default): kernel has died, and will be restarted.
          'dead': restart has failed, kernel will be left dead.

        """
        try:
            self.callbacks[event].remove(f)
        except ValueError:
            pass

    def _fire_callbacks(self, event: t.Any) -> None:
        """fire our callbacks for a particular event"""
        for callback in self.callbacks[event]:
            try:
                callback()
            except Exception:
                self.log.error(
                    "KernelRestarter: %s callback %r failed",
                    event,
                    callback,
                    exc_info=True,
                )

    def poll(self) -> None:
        if self.debug:
            self.log.debug("Polling kernel...")
        if self.kernel_manager.shutting_down:
            self.log.debug("Kernel shutdown in progress...")
            return
        now = time.time()
        if not self.kernel_manager.is_alive():
            self._last_dead = now
            if self._restarting:
                self._restart_count += 1
            else:
                self._restart_count = 1

            if self._restart_count > self.restart_limit:
                self.log.warning("KernelRestarter: restart failed")
                self._fire_callbacks("dead")
                self._restarting = False
                self._restart_count = 0
                self.stop()
            else:
                newports = self.random_ports_until_alive and self._initial_startup
                self.log.info(
                    "KernelRestarter: restarting kernel (%i/%i), %s random ports",
                    self._restart_count,
                    self.restart_limit,
                    "new" if newports else "keep",
                )
                self._fire_callbacks("restart")
                self.kernel_manager.restart_kernel(now=True, newports=newports)
                self._restarting = True
        else:
            # Since `is_alive` only tests that the kernel process is alive, it does not
            # indicate that the kernel has successfully completed startup. To solve this
            # correctly, we would need to wait for a kernel info reply, but it is not
            # necessarily appropriate to start a kernel client + channels in the
            # restarter. Therefore, we use "has been alive continuously for X time" as a
            # heuristic for a stable start up.
            # See https://github.com/jupyter/jupyter_client/pull/717 for details.
            stable_start_time = self.stable_start_time
            if self.kernel_manager.provisioner:
                stable_start_time = self.kernel_manager.provisioner.get_stable_start_time(
                    recommended=stable_start_time
                )
            if self._initial_startup and now - self._last_dead >= stable_start_time:
                self._initial_startup = False
            if self._restarting and now - self._last_dead >= stable_start_time:
                self.log.debug("KernelRestarter: restart apparently succeeded")
                self._restarting = False

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\bytecode\flags.py ===
# alias to keep the 'bytecode' variable free
import sys
from enum import IntFlag
from _pydevd_frame_eval.vendored import bytecode as _bytecode


class CompilerFlags(IntFlag):
    """Possible values of the co_flags attribute of Code object.

    Note: We do not rely on inspect values here as some of them are missing and
    furthermore would be version dependent.

    """

    OPTIMIZED = 0x00001  # noqa
    NEWLOCALS = 0x00002  # noqa
    VARARGS = 0x00004  # noqa
    VARKEYWORDS = 0x00008  # noqa
    NESTED = 0x00010  # noqa
    GENERATOR = 0x00020  # noqa
    NOFREE = 0x00040  # noqa
    # New in Python 3.5
    # Used for coroutines defined using async def ie native coroutine
    COROUTINE = 0x00080  # noqa
    # Used for coroutines defined as a generator and then decorated using
    # types.coroutine
    ITERABLE_COROUTINE = 0x00100  # noqa
    # New in Python 3.6
    # Generator defined in an async def function
    ASYNC_GENERATOR = 0x00200  # noqa

    # __future__ flags
    # future flags changed in Python 3.9
    if sys.version_info < (3, 9):
        FUTURE_GENERATOR_STOP = 0x80000  # noqa
        if sys.version_info > (3, 6):
            FUTURE_ANNOTATIONS = 0x100000
    else:
        FUTURE_GENERATOR_STOP = 0x800000  # noqa
        FUTURE_ANNOTATIONS = 0x1000000


def infer_flags(bytecode, is_async=None):
    """Infer the proper flags for a bytecode based on the instructions.

    Because the bytecode does not have enough context to guess if a function
    is asynchronous the algorithm tries to be conservative and will never turn
    a previously async code into a sync one.

    Parameters
    ----------
    bytecode : Bytecode | ConcreteBytecode | ControlFlowGraph
        Bytecode for which to infer the proper flags
    is_async : bool | None, optional
        Force the code to be marked as asynchronous if True, prevent it from
        being marked as asynchronous if False and simply infer the best
        solution based on the opcode and the existing flag if None.

    """
    flags = CompilerFlags(0)
    if not isinstance(
        bytecode,
        (_bytecode.Bytecode, _bytecode.ConcreteBytecode, _bytecode.ControlFlowGraph),
    ):
        msg = "Expected a Bytecode, ConcreteBytecode or ControlFlowGraph " "instance not %s"
        raise ValueError(msg % bytecode)

    instructions = bytecode.get_instructions() if isinstance(bytecode, _bytecode.ControlFlowGraph) else bytecode
    instr_names = {i.name for i in instructions if not isinstance(i, (_bytecode.SetLineno, _bytecode.Label))}

    # Identify optimized code
    if not (instr_names & {"STORE_NAME", "LOAD_NAME", "DELETE_NAME"}):
        flags |= CompilerFlags.OPTIMIZED

    # Check for free variables
    if not (
        instr_names
        & {
            "LOAD_CLOSURE",
            "LOAD_DEREF",
            "STORE_DEREF",
            "DELETE_DEREF",
            "LOAD_CLASSDEREF",
        }
    ):
        flags |= CompilerFlags.NOFREE

    # Copy flags for which we cannot infer the right value
    flags |= bytecode.flags & (CompilerFlags.NEWLOCALS | CompilerFlags.VARARGS | CompilerFlags.VARKEYWORDS | CompilerFlags.NESTED)

    sure_generator = instr_names & {"YIELD_VALUE"}
    maybe_generator = instr_names & {"YIELD_VALUE", "YIELD_FROM"}

    sure_async = instr_names & {
        "GET_AWAITABLE",
        "GET_AITER",
        "GET_ANEXT",
        "BEFORE_ASYNC_WITH",
        "SETUP_ASYNC_WITH",
        "END_ASYNC_FOR",
    }

    # If performing inference or forcing an async behavior, first inspect
    # the flags since this is the only way to identify iterable coroutines
    if is_async in (None, True):
        if bytecode.flags & CompilerFlags.COROUTINE:
            if sure_generator:
                flags |= CompilerFlags.ASYNC_GENERATOR
            else:
                flags |= CompilerFlags.COROUTINE
        elif bytecode.flags & CompilerFlags.ITERABLE_COROUTINE:
            if sure_async:
                msg = (
                    "The ITERABLE_COROUTINE flag is set but bytecode that"
                    "can only be used in async functions have been "
                    "detected. Please unset that flag before performing "
                    "inference."
                )
                raise ValueError(msg)
            flags |= CompilerFlags.ITERABLE_COROUTINE
        elif bytecode.flags & CompilerFlags.ASYNC_GENERATOR:
            if not sure_generator:
                flags |= CompilerFlags.COROUTINE
            else:
                flags |= CompilerFlags.ASYNC_GENERATOR

        # If the code was not asynchronous before determine if it should now be
        # asynchronous based on the opcode and the is_async argument.
        else:
            if sure_async:
                # YIELD_FROM is not allowed in async generator
                if sure_generator:
                    flags |= CompilerFlags.ASYNC_GENERATOR
                else:
                    flags |= CompilerFlags.COROUTINE

            elif maybe_generator:
                if is_async:
                    if sure_generator:
                        flags |= CompilerFlags.ASYNC_GENERATOR
                    else:
                        flags |= CompilerFlags.COROUTINE
                else:
                    flags |= CompilerFlags.GENERATOR

            elif is_async:
                flags |= CompilerFlags.COROUTINE

    # If the code should not be asynchronous, check first it is possible and
    # next set the GENERATOR flag if relevant
    else:
        if sure_async:
            raise ValueError(
                "The is_async argument is False but bytecodes " "that can only be used in async functions have " "been detected."
            )

        if maybe_generator:
            flags |= CompilerFlags.GENERATOR

    flags |= bytecode.flags & CompilerFlags.FUTURE_GENERATOR_STOP

    return flags

# === NexusCore/openenv\Lib\site-packages\google\api_core\future\async_future.py ===
# Copyright 2020, Google LLC
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

"""AsyncIO implementation of the abstract base Future class."""

import asyncio

from google.api_core import exceptions
from google.api_core import retry
from google.api_core import retry_async
from google.api_core.future import base


class _OperationNotComplete(Exception):
    """Private exception used for polling via retry."""

    pass


RETRY_PREDICATE = retry.if_exception_type(
    _OperationNotComplete,
    exceptions.TooManyRequests,
    exceptions.InternalServerError,
    exceptions.BadGateway,
)
DEFAULT_RETRY = retry_async.AsyncRetry(predicate=RETRY_PREDICATE)


class AsyncFuture(base.Future):
    """A Future that polls peer service to self-update.

    The :meth:`done` method should be implemented by subclasses. The polling
    behavior will repeatedly call ``done`` until it returns True.

    .. note::

        Privacy here is intended to prevent the final class from
        overexposing, not to prevent subclasses from accessing methods.

    Args:
        retry (google.api_core.retry.Retry): The retry configuration used
            when polling. This can be used to control how often :meth:`done`
            is polled. Regardless of the retry's ``deadline``, it will be
            overridden by the ``timeout`` argument to :meth:`result`.
    """

    def __init__(self, retry=DEFAULT_RETRY):
        super().__init__()
        self._retry = retry
        self._future = asyncio.get_event_loop().create_future()
        self._background_task = None

    async def done(self, retry=DEFAULT_RETRY):
        """Checks to see if the operation is complete.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the RPC.

        Returns:
            bool: True if the operation is complete, False otherwise.
        """
        # pylint: disable=redundant-returns-doc, missing-raises-doc
        raise NotImplementedError()

    async def _done_or_raise(self):
        """Check if the future is done and raise if it's not."""
        result = await self.done()
        if not result:
            raise _OperationNotComplete()

    async def running(self):
        """True if the operation is currently running."""
        result = await self.done()
        return not result

    async def _blocking_poll(self, timeout=None):
        """Poll and await for the Future to be resolved.

        Args:
            timeout (int):
                How long (in seconds) to wait for the operation to complete.
                If None, wait indefinitely.
        """
        if self._future.done():
            return

        retry_ = self._retry.with_timeout(timeout)

        try:
            await retry_(self._done_or_raise)()
        except exceptions.RetryError:
            raise asyncio.TimeoutError(
                "Operation did not complete within the designated " "timeout."
            )

    async def result(self, timeout=None):
        """Get the result of the operation.

        Args:
            timeout (int):
                How long (in seconds) to wait for the operation to complete.
                If None, wait indefinitely.

        Returns:
            google.protobuf.Message: The Operation's result.

        Raises:
            google.api_core.GoogleAPICallError: If the operation errors or if
                the timeout is reached before the operation completes.
        """
        await self._blocking_poll(timeout=timeout)
        return self._future.result()

    async def exception(self, timeout=None):
        """Get the exception from the operation.

        Args:
            timeout (int): How long to wait for the operation to complete.
                If None, wait indefinitely.

        Returns:
            Optional[google.api_core.GoogleAPICallError]: The operation's
                error.
        """
        await self._blocking_poll(timeout=timeout)
        return self._future.exception()

    def add_done_callback(self, fn):
        """Add a callback to be executed when the operation is complete.

        If the operation is completed, the callback will be scheduled onto the
        event loop. Otherwise, the callback will be stored and invoked when the
        future is done.

        Args:
            fn (Callable[Future]): The callback to execute when the operation
                is complete.
        """
        if self._background_task is None:
            self._background_task = asyncio.get_event_loop().create_task(
                self._blocking_poll()
            )
        self._future.add_done_callback(fn)

    def set_result(self, result):
        """Set the Future's result."""
        self._future.set_result(result)

    def set_exception(self, exception):
        """Set the Future's exception."""
        self._future.set_exception(exception)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\archived_server_1.py ===
import asyncio
import json
from typing import Generator

from .utils.lazy_import import lazy_import

uvicorn = lazy_import("uvicorn")
fastapi = lazy_import("fastapi")


def server(interpreter, host="0.0.0.0", port=8000):
    FastAPI, Request, Response, WebSocket = (
        fastapi.FastAPI,
        fastapi.Request,
        fastapi.Response,
        fastapi.WebSocket,
    )
    PlainTextResponse = fastapi.responses.PlainTextResponse

    app = FastAPI()

    @app.post("/chat")
    async def stream_endpoint(request: Request) -> Response:
        async def event_stream() -> Generator[str, None, None]:
            data = await request.json()
            for response in interpreter.chat(message=data["message"], stream=True):
                yield response

        return Response(event_stream(), media_type="text/event-stream")

    # Post endpoint
    # @app.post("/iv0", response_class=PlainTextResponse)
    # async def i_post_endpoint(request: Request):
    #     message = await request.body()
    #     message = message.decode("utf-8")  # Convert bytes to string

    #     async def event_stream() -> Generator[str, None, None]:
    #         for response in interpreter.chat(
    #             message=message, stream=True, display=False
    #         ):
    #             if (
    #                 response.get("type") == "message"
    #                 and response["role"] == "assistant"
    #                 and "content" in response
    #             ):
    #                 yield response["content"] + "\n"
    #             if (
    #                 response.get("type") == "message"
    #                 and response["role"] == "assistant"
    #                 and response.get("end") == True
    #             ):
    #                 yield " \n"

    #     return StreamingResponse(event_stream(), media_type="text/plain")

    @app.get("/test")
    async def test_ui():
        return PlainTextResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Chat</title>
            </head>
            <body>
                <form action="" onsubmit="sendMessage(event)">
                    <textarea id="messageInput" rows="10" cols="50" autocomplete="off"></textarea>
                    <button>Send</button>
                </form>
                <div id="messages"></div>
                <script>
                    var ws = new WebSocket("ws://localhost:8000/");
                    var lastMessageElement = null;
                    ws.onmessage = function(event) {
                        if (lastMessageElement == null) {
                            lastMessageElement = document.createElement('p');
                            document.getElementById('messages').appendChild(lastMessageElement);
                        }
                        lastMessageElement.innerHTML += event.data;
                    };
                    function sendMessage(event) {
                        event.preventDefault();
                        var input = document.getElementById("messageInput");
                        var message = input.value;
                        if (message.startsWith('{') && message.endsWith('}')) {
                            message = JSON.stringify(JSON.parse(message));
                        }
                        ws.send(message);
                        var userMessageElement = document.createElement('p');
                        userMessageElement.innerHTML = '<b>' + input.value + '</b><br>';
                        document.getElementById('messages').appendChild(userMessageElement);
                        lastMessageElement = document.createElement('p');
                        document.getElementById('messages').appendChild(lastMessageElement);
                        input.value = '';
                    }
                </script>
            </body>
            </html>
            """,
            media_type="text/html",
        )

    @app.websocket("/")
    async def i_test(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            while data.strip().lower() != "stop":  # Stop command
                task = asyncio.create_task(websocket.receive_text())

                # This would be terrible for production. Just for testing.
                try:
                    data_dict = json.loads(data)
                    if set(data_dict.keys()) == {"role", "content", "type"} or set(
                        data_dict.keys()
                    ) == {"role", "content", "type", "format"}:
                        data = data_dict
                except json.JSONDecodeError:
                    pass

                for response in interpreter.chat(
                    message=data, stream=True, display=False
                ):
                    if task.done():
                        data = task.result()  # Get the new message
                        break  # Break the loop and start processing the new message
                    # Send out assistant message chunks
                    if (
                        response.get("type") == "message"
                        and response["role"] == "assistant"
                        and "content" in response
                    ):
                        await websocket.send_text(response["content"])
                        await asyncio.sleep(0.01)  # Add a small delay
                    if (
                        response.get("type") == "message"
                        and response["role"] == "assistant"
                        and response.get("end") == True
                    ):
                        await websocket.send_text("\n")
                        await asyncio.sleep(0.01)  # Add a small delay
                if not task.done():
                    data = (
                        await task
                    )  # Wait for the next message if it hasn't arrived yet

    print(
        "\nOpening a simple `interpreter.chat(data)` POST endpoint at http://localhost:8000/chat."
    )
    print(
        "Opening an `i.protocol` compatible WebSocket endpoint at http://localhost:8000/."
    )
    print("\nVisit http://localhost:8000/test to test the WebSocket endpoint.\n")

    import socket

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    local_url = f"http://{local_ip}:8000"
    print(f"Local URL: {local_url}\n")

    uvicorn.run(app, host=host, port=port)

# === NexusCore/openenv\Lib\site-packages\isapi\samples\redirector_with_filter.py ===
# This is a sample configuration file for an ISAPI filter and extension
# written in Python.
#
# Please see README.txt in this directory, and specifically the
# information about the "loader" DLL - installing this sample will create
# "_redirector_with_filter.dll" in the current directory.  The readme explains
# this.

# Executing this script (or any server config script) will install the extension
# into your web server. As the server executes, the PyISAPI framework will load
# this module and create your Extension and Filter objects.

# This sample provides sample redirector:
# It is implemented by a filter and an extension, so that some requests can
# be ignored.  Compare with 'redirector_simple' which avoids the filter, but
# is unable to selectively ignore certain requests.
# The process is sample uses is:
# * The filter is installed globally, as all filters are.
# * A Virtual Directory named "python" is setup.  This dir has our ISAPI
#   extension as the only application, mapped to file-extension '*'.  Thus, our
#   extension handles *all* requests in this directory.
# The basic process is that the filter does URL rewriting, redirecting every
# URL to our Virtual Directory.  Our extension then handles this request,
# forwarding the data from the proxied site.
# For example:
# * URL of "index.html" comes in.
# * Filter rewrites this to "/python/index.html"
# * Our extension sees the full "/python/index.html", removes the leading
#   portion, and opens and forwards the remote URL.


# This sample is very small - it avoid most error handling, etc.  It is for
# demonstration purposes only.

import sys
import urllib.error
import urllib.parse
import urllib.request

from isapi import isapicon, threaded_extension
from isapi.simple import SimpleFilter

# sys.isapidllhandle will exist when we are loaded by the IIS framework.
# In this case we redirect our output to the win32traceutil collector.
if hasattr(sys, "isapidllhandle"):
    import win32traceutil

# The site we are proxying.
proxy = "https://www.python.org"
# The name of the virtual directory we install in, and redirect from.
virtualdir = "/python"

# The key feature of this redirector over the simple redirector is that it
# can choose to ignore certain responses by having the filter not rewrite them
# to our virtual dir. For this sample, we just exclude the IIS help directory.


# The ISAPI extension - handles requests in our virtual dir, and sends the
# response to the client.
class Extension(threaded_extension.ThreadPoolExtension):
    "Python sample Extension"

    def Dispatch(self, ecb):
        # Note that our ThreadPoolExtension base class will catch exceptions
        # in our Dispatch method, and write the traceback to the client.
        # That is perfect for this sample, so we don't catch our own.
        # print(f'IIS dispatching "{ecb.GetServerVariable("URL")}"')
        url = ecb.GetServerVariable("URL")
        if url.startswith(virtualdir):
            new_url = proxy + url[len(virtualdir) :]
            print("Opening", new_url)
            fp = urllib.request.urlopen(new_url)
            headers = fp.info()
            ecb.SendResponseHeaders("200 OK", str(headers) + "\r\n", False)
            ecb.WriteClient(fp.read())
            ecb.DoneWithSession()
            print(f"Returned data from '{new_url}'!")
        else:
            # this should never happen - we should only see requests that
            # start with our virtual directory name.
            print(f"Not proxying '{url}'")


# The ISAPI filter.
class Filter(SimpleFilter):
    "Sample Python Redirector"

    filter_flags = isapicon.SF_NOTIFY_PREPROC_HEADERS | isapicon.SF_NOTIFY_ORDER_DEFAULT

    def HttpFilterProc(self, fc):
        # print("Filter Dispatch")
        nt = fc.NotificationType
        if nt != isapicon.SF_NOTIFY_PREPROC_HEADERS:
            return isapicon.SF_STATUS_REQ_NEXT_NOTIFICATION

        pp = fc.GetData()
        url = pp.GetHeader("url")
        # print(f"URL is '{url}'")
        prefix = virtualdir
        if not url.startswith(prefix):
            new_url = prefix + url
            print(f"New proxied URL is '{new_url}'")
            pp.SetHeader("url", new_url)
            # For the sake of demonstration, show how the FilterContext
            # attribute is used.  It always starts out life as None, and
            # any assignments made are automatically decref'd by the
            # framework during a SF_NOTIFY_END_OF_NET_SESSION notification.
            if fc.FilterContext is None:
                fc.FilterContext = 0
            fc.FilterContext += 1
            print("This is request number %d on this connection" % fc.FilterContext)
            return isapicon.SF_STATUS_REQ_HANDLED_NOTIFICATION
        else:
            print(f"Filter ignoring URL '{url}'")

            # Some older code that handled SF_NOTIFY_URL_MAP.
            # print("Have URL_MAP notify")
            # urlmap = fc.GetData()
            # print("URI is", urlmap.URL)
            # print("Path is", urlmap.PhysicalPath)
            # if urlmap.URL.startswith("/UC/"):
            # # Find the /UC/ in the physical path, and nuke it (except
            # # as the path is physical, it is \)
            # p = urlmap.PhysicalPath
            # pos = p.index("\\UC\\")
            # p = p[:pos] + p[pos+3:]
            # p = r"E:\src\pyisapi\webroot\PyTest\formTest.htm"
            # print("New path is", p)
            # urlmap.PhysicalPath = p


# The entry points for the ISAPI extension.
def __FilterFactory__():
    return Filter()


def __ExtensionFactory__():
    return Extension()


if __name__ == "__main__":
    # If run from the command-line, install ourselves.
    from isapi.install import *

    params = ISAPIParameters()
    # Setup all filters - these are global to the site.
    params.Filters = [
        FilterParameters(Name="PythonRedirector", Description=Filter.__doc__),
    ]
    # Setup the virtual directories - this is a list of directories our
    # extension uses - in this case only 1.
    # Each extension has a "script map" - this is the mapping of ISAPI
    # extensions.
    sm = [ScriptMapParams(Extension="*", Flags=0)]
    vd = VirtualDirParameters(
        Name=virtualdir[1:],
        Description=Extension.__doc__,
        ScriptMaps=sm,
        ScriptMapUpdate="replace",
    )
    params.VirtualDirs = [vd]
    HandleCommandLine(params)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\streaming_handler.py ===
import asyncio
from datetime import datetime
from typing import List, Optional

import httpx

from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.thread_pool_executor import executor
from litellm.proxy._types import PassThroughEndpointLoggingResultValues
from litellm.types.passthrough_endpoints.pass_through_endpoints import EndpointType
from litellm.types.utils import StandardPassThroughResponseObject

from .llm_provider_handlers.anthropic_passthrough_logging_handler import (
    AnthropicPassthroughLoggingHandler,
)
from .llm_provider_handlers.vertex_passthrough_logging_handler import (
    VertexPassthroughLoggingHandler,
)
from .success_handler import PassThroughEndpointLogging


class PassThroughStreamingHandler:
    @staticmethod
    async def chunk_processor(
        response: httpx.Response,
        request_body: Optional[dict],
        litellm_logging_obj: LiteLLMLoggingObj,
        endpoint_type: EndpointType,
        start_time: datetime,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
    ):
        """
        - Yields chunks from the response
        - Collect non-empty chunks for post-processing (logging)
        """
        try:
            raw_bytes: List[bytes] = []
            async for chunk in response.aiter_bytes():
                raw_bytes.append(chunk)
                yield chunk

            # After all chunks are processed, handle post-processing
            end_time = datetime.now()

            asyncio.create_task(
                PassThroughStreamingHandler._route_streaming_logging_to_handler(
                    litellm_logging_obj=litellm_logging_obj,
                    passthrough_success_handler_obj=passthrough_success_handler_obj,
                    url_route=url_route,
                    request_body=request_body or {},
                    endpoint_type=endpoint_type,
                    start_time=start_time,
                    raw_bytes=raw_bytes,
                    end_time=end_time,
                )
            )
        except Exception as e:
            verbose_proxy_logger.error(f"Error in chunk_processor: {str(e)}")
            raise

    @staticmethod
    async def _route_streaming_logging_to_handler(
        litellm_logging_obj: LiteLLMLoggingObj,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
        request_body: dict,
        endpoint_type: EndpointType,
        start_time: datetime,
        raw_bytes: List[bytes],
        end_time: datetime,
    ):
        """
        Route the logging for the collected chunks to the appropriate handler

        Supported endpoint types:
        - Anthropic
        - Vertex AI
        """
        all_chunks = PassThroughStreamingHandler._convert_raw_bytes_to_str_lines(
            raw_bytes
        )
        standard_logging_response_object: Optional[
            PassThroughEndpointLoggingResultValues
        ] = None
        kwargs: dict = {}
        if endpoint_type == EndpointType.ANTHROPIC:
            anthropic_passthrough_logging_handler_result = AnthropicPassthroughLoggingHandler._handle_logging_anthropic_collected_chunks(
                litellm_logging_obj=litellm_logging_obj,
                passthrough_success_handler_obj=passthrough_success_handler_obj,
                url_route=url_route,
                request_body=request_body,
                endpoint_type=endpoint_type,
                start_time=start_time,
                all_chunks=all_chunks,
                end_time=end_time,
            )
            standard_logging_response_object = (
                anthropic_passthrough_logging_handler_result["result"]
            )
            kwargs = anthropic_passthrough_logging_handler_result["kwargs"]
        elif endpoint_type == EndpointType.VERTEX_AI:
            vertex_passthrough_logging_handler_result = (
                VertexPassthroughLoggingHandler._handle_logging_vertex_collected_chunks(
                    litellm_logging_obj=litellm_logging_obj,
                    passthrough_success_handler_obj=passthrough_success_handler_obj,
                    url_route=url_route,
                    request_body=request_body,
                    endpoint_type=endpoint_type,
                    start_time=start_time,
                    all_chunks=all_chunks,
                    end_time=end_time,
                )
            )
            standard_logging_response_object = (
                vertex_passthrough_logging_handler_result["result"]
            )
            kwargs = vertex_passthrough_logging_handler_result["kwargs"]

        if standard_logging_response_object is None:
            standard_logging_response_object = StandardPassThroughResponseObject(
                response=f"cannot parse chunks to standard response object. Chunks={all_chunks}"
            )

        await litellm_logging_obj.async_success_handler(
            result=standard_logging_response_object,
            start_time=start_time,
            end_time=end_time,
            cache_hit=False,
            **kwargs,
        )
        if litellm_logging_obj._should_run_sync_callbacks_for_async_calls() is False:
            return

        executor.submit(
            litellm_logging_obj.success_handler,
            result=standard_logging_response_object,
            end_time=end_time,
            cache_hit=False,
            start_time=start_time,
            **kwargs,
        )

    @staticmethod
    def _convert_raw_bytes_to_str_lines(raw_bytes: List[bytes]) -> List[str]:
        """
        Converts a list of raw bytes into a list of string lines, similar to aiter_lines()

        Args:
            raw_bytes: List of bytes chunks from aiter.bytes()

        Returns:
            List of string lines, with each line being a complete data: {} chunk
        """
        # Combine all bytes and decode to string
        combined_str = b"".join(raw_bytes).decode("utf-8")

        # Split by newlines and filter out empty lines
        lines = [line.strip() for line in combined_str.split("\n") if line.strip()]

        return lines

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_exceptions.py ===
"""
Various richly-typed exceptions, that also help us deal with string formatting
in python where it's easier.

By putting the formatting in `__str__`, we also avoid paying the cost for
users who silence the exceptions.
"""

def _unpack_tuple(tup):
    if len(tup) == 1:
        return tup[0]
    else:
        return tup


def _display_as_base(cls):
    """
    A decorator that makes an exception class look like its base.

    We use this to hide subclasses that are implementation details - the user
    should catch the base type, which is what the traceback will show them.

    Classes decorated with this decorator are subject to removal without a
    deprecation warning.
    """
    assert issubclass(cls, Exception)
    cls.__name__ = cls.__base__.__name__
    return cls


class UFuncTypeError(TypeError):
    """ Base class for all ufunc exceptions """
    def __init__(self, ufunc):
        self.ufunc = ufunc


@_display_as_base
class _UFuncNoLoopError(UFuncTypeError):
    """ Thrown when a ufunc loop cannot be found """
    def __init__(self, ufunc, dtypes):
        super().__init__(ufunc)
        self.dtypes = tuple(dtypes)

    def __str__(self):
        return (
            f"ufunc {self.ufunc.__name__!r} did not contain a loop with signature "
            f"matching types {_unpack_tuple(self.dtypes[:self.ufunc.nin])!r} "
            f"-> {_unpack_tuple(self.dtypes[self.ufunc.nin:])!r}"
        )


@_display_as_base
class _UFuncBinaryResolutionError(_UFuncNoLoopError):
    """ Thrown when a binary resolution fails """
    def __init__(self, ufunc, dtypes):
        super().__init__(ufunc, dtypes)
        assert len(self.dtypes) == 2

    def __str__(self):
        return (
            "ufunc {!r} cannot use operands with types {!r} and {!r}"
        ).format(
            self.ufunc.__name__, *self.dtypes
        )


@_display_as_base
class _UFuncCastingError(UFuncTypeError):
    def __init__(self, ufunc, casting, from_, to):
        super().__init__(ufunc)
        self.casting = casting
        self.from_ = from_
        self.to = to


@_display_as_base
class _UFuncInputCastingError(_UFuncCastingError):
    """ Thrown when a ufunc input cannot be casted """
    def __init__(self, ufunc, casting, from_, to, i):
        super().__init__(ufunc, casting, from_, to)
        self.in_i = i

    def __str__(self):
        # only show the number if more than one input exists
        i_str = f"{self.in_i} " if self.ufunc.nin != 1 else ""
        return (
            f"Cannot cast ufunc {self.ufunc.__name__!r} input {i_str}from "
            f"{self.from_!r} to {self.to!r} with casting rule {self.casting!r}"
        )


@_display_as_base
class _UFuncOutputCastingError(_UFuncCastingError):
    """ Thrown when a ufunc output cannot be casted """
    def __init__(self, ufunc, casting, from_, to, i):
        super().__init__(ufunc, casting, from_, to)
        self.out_i = i

    def __str__(self):
        # only show the number if more than one output exists
        i_str = f"{self.out_i} " if self.ufunc.nout != 1 else ""
        return (
            f"Cannot cast ufunc {self.ufunc.__name__!r} output {i_str}from "
            f"{self.from_!r} to {self.to!r} with casting rule {self.casting!r}"
        )


@_display_as_base
class _ArrayMemoryError(MemoryError):
    """ Thrown when an array cannot be allocated"""
    def __init__(self, shape, dtype):
        self.shape = shape
        self.dtype = dtype

    @property
    def _total_size(self):
        num_bytes = self.dtype.itemsize
        for dim in self.shape:
            num_bytes *= dim
        return num_bytes

    @staticmethod
    def _size_to_string(num_bytes):
        """ Convert a number of bytes into a binary size string """

        # https://en.wikipedia.org/wiki/Binary_prefix
        LOG2_STEP = 10
        STEP = 1024
        units = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']

        unit_i = max(num_bytes.bit_length() - 1, 1) // LOG2_STEP
        unit_val = 1 << (unit_i * LOG2_STEP)
        n_units = num_bytes / unit_val
        del unit_val

        # ensure we pick a unit that is correct after rounding
        if round(n_units) == STEP:
            unit_i += 1
            n_units /= STEP

        # deal with sizes so large that we don't have units for them
        if unit_i >= len(units):
            new_unit_i = len(units) - 1
            n_units *= 1 << ((unit_i - new_unit_i) * LOG2_STEP)
            unit_i = new_unit_i

        unit_name = units[unit_i]
        # format with a sensible number of digits
        if unit_i == 0:
            # no decimal point on bytes
            return f'{n_units:.0f} {unit_name}'
        elif round(n_units) < 1000:
            # 3 significant figures, if none are dropped to the left of the .
            return f'{n_units:#.3g} {unit_name}'
        else:
            # just give all the digits otherwise
            return f'{n_units:#.0f} {unit_name}'

    def __str__(self):
        size_str = self._size_to_string(self._total_size)
        return (f"Unable to allocate {size_str} for an array with shape "
                f"{self.shape} and data type {self.dtype}")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\markers.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Parser for the environment markers micro-language defined in PEP 508.
"""

# Note: In PEP 345, the micro-language was Python compatible, so the ast
# module could be used to parse it. However, PEP 508 introduced operators such
# as ~= and === which aren't in Python, necessitating a different approach.

import os
import re
import sys
import platform

from .compat import string_types
from .util import in_venv, parse_marker
from .version import LegacyVersion as LV

__all__ = ['interpret']

_VERSION_PATTERN = re.compile(r'((\d+(\.\d+)*\w*)|\'(\d+(\.\d+)*\w*)\'|\"(\d+(\.\d+)*\w*)\")')
_VERSION_MARKERS = {'python_version', 'python_full_version'}


def _is_version_marker(s):
    return isinstance(s, string_types) and s in _VERSION_MARKERS


def _is_literal(o):
    if not isinstance(o, string_types) or not o:
        return False
    return o[0] in '\'"'


def _get_versions(s):
    return {LV(m.groups()[0]) for m in _VERSION_PATTERN.finditer(s)}


class Evaluator(object):
    """
    This class is used to evaluate marker expressions.
    """

    operations = {
        '==': lambda x, y: x == y,
        '===': lambda x, y: x == y,
        '~=': lambda x, y: x == y or x > y,
        '!=': lambda x, y: x != y,
        '<': lambda x, y: x < y,
        '<=': lambda x, y: x == y or x < y,
        '>': lambda x, y: x > y,
        '>=': lambda x, y: x == y or x > y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
    }

    def evaluate(self, expr, context):
        """
        Evaluate a marker expression returned by the :func:`parse_requirement`
        function in the specified context.
        """
        if isinstance(expr, string_types):
            if expr[0] in '\'"':
                result = expr[1:-1]
            else:
                if expr not in context:
                    raise SyntaxError('unknown variable: %s' % expr)
                result = context[expr]
        else:
            assert isinstance(expr, dict)
            op = expr['op']
            if op not in self.operations:
                raise NotImplementedError('op not implemented: %s' % op)
            elhs = expr['lhs']
            erhs = expr['rhs']
            if _is_literal(expr['lhs']) and _is_literal(expr['rhs']):
                raise SyntaxError('invalid comparison: %s %s %s' % (elhs, op, erhs))

            lhs = self.evaluate(elhs, context)
            rhs = self.evaluate(erhs, context)
            if ((_is_version_marker(elhs) or _is_version_marker(erhs)) and
                    op in ('<', '<=', '>', '>=', '===', '==', '!=', '~=')):
                lhs = LV(lhs)
                rhs = LV(rhs)
            elif _is_version_marker(elhs) and op in ('in', 'not in'):
                lhs = LV(lhs)
                rhs = _get_versions(rhs)
            result = self.operations[op](lhs, rhs)
        return result


_DIGITS = re.compile(r'\d+\.\d+')


def default_context():

    def format_full_version(info):
        version = '%s.%s.%s' % (info.major, info.minor, info.micro)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)
        return version

    if hasattr(sys, 'implementation'):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = '0'
        implementation_name = ''

    ppv = platform.python_version()
    m = _DIGITS.match(ppv)
    pv = m.group(0)
    result = {
        'implementation_name': implementation_name,
        'implementation_version': implementation_version,
        'os_name': os.name,
        'platform_machine': platform.machine(),
        'platform_python_implementation': platform.python_implementation(),
        'platform_release': platform.release(),
        'platform_system': platform.system(),
        'platform_version': platform.version(),
        'platform_in_venv': str(in_venv()),
        'python_full_version': ppv,
        'python_version': pv,
        'sys_platform': sys.platform,
    }
    return result


DEFAULT_CONTEXT = default_context()
del default_context

evaluator = Evaluator()


def interpret(marker, execution_context=None):
    """
    Interpret a marker and return a result depending on environment.

    :param marker: The marker to interpret.
    :type marker: str
    :param execution_context: The context used for name lookup.
    :type execution_context: mapping
    """
    try:
        expr, rest = parse_marker(marker)
    except Exception as e:
        raise SyntaxError('Unable to interpret marker syntax: %s: %s' % (marker, e))
    if rest and rest[0] != '#':
        raise SyntaxError('unexpected trailing data in marker: %s: %s' % (marker, rest))
    context = dict(DEFAULT_CONTEXT)
    if execution_context:
        context.update(execution_context)
    return evaluator.evaluate(expr, context)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\styles\named_colors.py ===
"""
All modern web browsers support these 140 color names.
Taken from: https://www.w3schools.com/colors/colors_names.asp
"""

from __future__ import annotations

__all__ = [
    "NAMED_COLORS",
]


NAMED_COLORS: dict[str, str] = {
    "AliceBlue": "#f0f8ff",
    "AntiqueWhite": "#faebd7",
    "Aqua": "#00ffff",
    "Aquamarine": "#7fffd4",
    "Azure": "#f0ffff",
    "Beige": "#f5f5dc",
    "Bisque": "#ffe4c4",
    "Black": "#000000",
    "BlanchedAlmond": "#ffebcd",
    "Blue": "#0000ff",
    "BlueViolet": "#8a2be2",
    "Brown": "#a52a2a",
    "BurlyWood": "#deb887",
    "CadetBlue": "#5f9ea0",
    "Chartreuse": "#7fff00",
    "Chocolate": "#d2691e",
    "Coral": "#ff7f50",
    "CornflowerBlue": "#6495ed",
    "Cornsilk": "#fff8dc",
    "Crimson": "#dc143c",
    "Cyan": "#00ffff",
    "DarkBlue": "#00008b",
    "DarkCyan": "#008b8b",
    "DarkGoldenRod": "#b8860b",
    "DarkGray": "#a9a9a9",
    "DarkGreen": "#006400",
    "DarkGrey": "#a9a9a9",
    "DarkKhaki": "#bdb76b",
    "DarkMagenta": "#8b008b",
    "DarkOliveGreen": "#556b2f",
    "DarkOrange": "#ff8c00",
    "DarkOrchid": "#9932cc",
    "DarkRed": "#8b0000",
    "DarkSalmon": "#e9967a",
    "DarkSeaGreen": "#8fbc8f",
    "DarkSlateBlue": "#483d8b",
    "DarkSlateGray": "#2f4f4f",
    "DarkSlateGrey": "#2f4f4f",
    "DarkTurquoise": "#00ced1",
    "DarkViolet": "#9400d3",
    "DeepPink": "#ff1493",
    "DeepSkyBlue": "#00bfff",
    "DimGray": "#696969",
    "DimGrey": "#696969",
    "DodgerBlue": "#1e90ff",
    "FireBrick": "#b22222",
    "FloralWhite": "#fffaf0",
    "ForestGreen": "#228b22",
    "Fuchsia": "#ff00ff",
    "Gainsboro": "#dcdcdc",
    "GhostWhite": "#f8f8ff",
    "Gold": "#ffd700",
    "GoldenRod": "#daa520",
    "Gray": "#808080",
    "Green": "#008000",
    "GreenYellow": "#adff2f",
    "Grey": "#808080",
    "HoneyDew": "#f0fff0",
    "HotPink": "#ff69b4",
    "IndianRed": "#cd5c5c",
    "Indigo": "#4b0082",
    "Ivory": "#fffff0",
    "Khaki": "#f0e68c",
    "Lavender": "#e6e6fa",
    "LavenderBlush": "#fff0f5",
    "LawnGreen": "#7cfc00",
    "LemonChiffon": "#fffacd",
    "LightBlue": "#add8e6",
    "LightCoral": "#f08080",
    "LightCyan": "#e0ffff",
    "LightGoldenRodYellow": "#fafad2",
    "LightGray": "#d3d3d3",
    "LightGreen": "#90ee90",
    "LightGrey": "#d3d3d3",
    "LightPink": "#ffb6c1",
    "LightSalmon": "#ffa07a",
    "LightSeaGreen": "#20b2aa",
    "LightSkyBlue": "#87cefa",
    "LightSlateGray": "#778899",
    "LightSlateGrey": "#778899",
    "LightSteelBlue": "#b0c4de",
    "LightYellow": "#ffffe0",
    "Lime": "#00ff00",
    "LimeGreen": "#32cd32",
    "Linen": "#faf0e6",
    "Magenta": "#ff00ff",
    "Maroon": "#800000",
    "MediumAquaMarine": "#66cdaa",
    "MediumBlue": "#0000cd",
    "MediumOrchid": "#ba55d3",
    "MediumPurple": "#9370db",
    "MediumSeaGreen": "#3cb371",
    "MediumSlateBlue": "#7b68ee",
    "MediumSpringGreen": "#00fa9a",
    "MediumTurquoise": "#48d1cc",
    "MediumVioletRed": "#c71585",
    "MidnightBlue": "#191970",
    "MintCream": "#f5fffa",
    "MistyRose": "#ffe4e1",
    "Moccasin": "#ffe4b5",
    "NavajoWhite": "#ffdead",
    "Navy": "#000080",
    "OldLace": "#fdf5e6",
    "Olive": "#808000",
    "OliveDrab": "#6b8e23",
    "Orange": "#ffa500",
    "OrangeRed": "#ff4500",
    "Orchid": "#da70d6",
    "PaleGoldenRod": "#eee8aa",
    "PaleGreen": "#98fb98",
    "PaleTurquoise": "#afeeee",
    "PaleVioletRed": "#db7093",
    "PapayaWhip": "#ffefd5",
    "PeachPuff": "#ffdab9",
    "Peru": "#cd853f",
    "Pink": "#ffc0cb",
    "Plum": "#dda0dd",
    "PowderBlue": "#b0e0e6",
    "Purple": "#800080",
    "RebeccaPurple": "#663399",
    "Red": "#ff0000",
    "RosyBrown": "#bc8f8f",
    "RoyalBlue": "#4169e1",
    "SaddleBrown": "#8b4513",
    "Salmon": "#fa8072",
    "SandyBrown": "#f4a460",
    "SeaGreen": "#2e8b57",
    "SeaShell": "#fff5ee",
    "Sienna": "#a0522d",
    "Silver": "#c0c0c0",
    "SkyBlue": "#87ceeb",
    "SlateBlue": "#6a5acd",
    "SlateGray": "#708090",
    "SlateGrey": "#708090",
    "Snow": "#fffafa",
    "SpringGreen": "#00ff7f",
    "SteelBlue": "#4682b4",
    "Tan": "#d2b48c",
    "Teal": "#008080",
    "Thistle": "#d8bfd8",
    "Tomato": "#ff6347",
    "Turquoise": "#40e0d0",
    "Violet": "#ee82ee",
    "Wheat": "#f5deb3",
    "White": "#ffffff",
    "WhiteSmoke": "#f5f5f5",
    "Yellow": "#ffff00",
    "YellowGreen": "#9acd32",
}

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\cachecontrol\adapter.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import functools
import types
import zlib
from typing import TYPE_CHECKING, Any, Collection, Mapping

from pip._vendor.requests.adapters import HTTPAdapter

from pip._vendor.cachecontrol.cache import DictCache
from pip._vendor.cachecontrol.controller import PERMANENT_REDIRECT_STATUSES, CacheController
from pip._vendor.cachecontrol.filewrapper import CallbackFileWrapper

if TYPE_CHECKING:
    from pip._vendor.requests import PreparedRequest, Response
    from pip._vendor.urllib3 import HTTPResponse

    from pip._vendor.cachecontrol.cache import BaseCache
    from pip._vendor.cachecontrol.heuristics import BaseHeuristic
    from pip._vendor.cachecontrol.serialize import Serializer


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = {"PUT", "PATCH", "DELETE"}

    def __init__(
        self,
        cache: BaseCache | None = None,
        cache_etags: bool = True,
        controller_class: type[CacheController] | None = None,
        serializer: Serializer | None = None,
        heuristic: BaseHeuristic | None = None,
        cacheable_methods: Collection[str] | None = None,
        *args: Any,
        **kw: Any,
    ) -> None:
        super().__init__(*args, **kw)
        self.cache = DictCache() if cache is None else cache
        self.heuristic = heuristic
        self.cacheable_methods = cacheable_methods or ("GET",)

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache, cache_etags=cache_etags, serializer=serializer
        )

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: (None | bytes | str | tuple[bytes | str, bytes | str]) = None,
        proxies: Mapping[str, str] | None = None,
        cacheable_methods: Collection[str] | None = None,
    ) -> Response:
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        cacheable = cacheable_methods or self.cacheable_methods
        if request.method in cacheable:
            try:
                cached_response = self.controller.cached_request(request)
            except zlib.error:
                cached_response = None
            if cached_response:
                return self.build_response(request, cached_response, from_cache=True)

            # check for etags and add headers if appropriate
            request.headers.update(self.controller.conditional_headers(request))

        resp = super().send(request, stream, timeout, verify, cert, proxies)

        return resp

    def build_response(  # type: ignore[override]
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        from_cache: bool = False,
        cacheable_methods: Collection[str] | None = None,
    ) -> Response:
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        cacheable = cacheable_methods or self.cacheable_methods
        if not from_cache and request.method in cacheable:
            # Check for any heuristics that might update headers
            # before trying to cache.
            if self.heuristic:
                response = self.heuristic.apply(response)

            # apply any expiration heuristics
            if response.status == 304:
                # We must have sent an ETag request. This could mean
                # that we've been expired already or that we simply
                # have an etag. In either case, we want to try and
                # update the cache if that is the case.
                cached_response = self.controller.update_cached_response(
                    request, response
                )

                if cached_response is not response:
                    from_cache = True

                # We are done with the server response, read a
                # possible response body (compliant servers will
                # not return one, but we cannot be 100% sure) and
                # release the connection back to the pool.
                response.read(decode_content=False)
                response.release_conn()

                response = cached_response

            # We always cache the 301 responses
            elif int(response.status) in PERMANENT_REDIRECT_STATUSES:
                self.controller.cache_response(request, response)
            else:
                # Wrap the response file with a wrapper that will cache the
                #   response when the stream has been consumed.
                response._fp = CallbackFileWrapper(  # type: ignore[assignment]
                    response._fp,  # type: ignore[arg-type]
                    functools.partial(
                        self.controller.cache_response, request, response
                    ),
                )
                if response.chunked:
                    super_update_chunk_length = response._update_chunk_length

                    def _update_chunk_length(self: HTTPResponse) -> None:
                        super_update_chunk_length()
                        if self.chunk_left == 0:
                            self._fp._close()  # type: ignore[union-attr]

                    response._update_chunk_length = types.MethodType(  # type: ignore[method-assign]
                        _update_chunk_length, response
                    )

        resp: Response = super().build_response(request, response)

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            assert request.url is not None
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache  # type: ignore[attr-defined]

        return resp

    def close(self) -> None:
        self.cache.close()
        super().close()  # type: ignore[no-untyped-call]

# === NexusCore/openenv\Lib\site-packages\anyio\lowlevel.py ===
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar, overload
from weakref import WeakKeyDictionary

from ._core._eventloop import get_async_backend

T = TypeVar("T")
D = TypeVar("D")


async def checkpoint() -> None:
    """
    Check for cancellation and allow the scheduler to switch to another task.

    Equivalent to (but more efficient than)::

        await checkpoint_if_cancelled()
        await cancel_shielded_checkpoint()


    .. versionadded:: 3.0

    """
    await get_async_backend().checkpoint()


async def checkpoint_if_cancelled() -> None:
    """
    Enter a checkpoint if the enclosing cancel scope has been cancelled.

    This does not allow the scheduler to switch to a different task.

    .. versionadded:: 3.0

    """
    await get_async_backend().checkpoint_if_cancelled()


async def cancel_shielded_checkpoint() -> None:
    """
    Allow the scheduler to switch to another task but without checking for cancellation.

    Equivalent to (but potentially more efficient than)::

        with CancelScope(shield=True):
            await checkpoint()


    .. versionadded:: 3.0

    """
    await get_async_backend().cancel_shielded_checkpoint()


def current_token() -> object:
    """
    Return a backend specific token object that can be used to get back to the event
    loop.

    """
    return get_async_backend().current_token()


_run_vars: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()
_token_wrappers: dict[Any, _TokenWrapper] = {}


@dataclass(frozen=True)
class _TokenWrapper:
    __slots__ = "_token", "__weakref__"
    _token: object


class _NoValueSet(enum.Enum):
    NO_VALUE_SET = enum.auto()


class RunvarToken(Generic[T]):
    __slots__ = "_var", "_value", "_redeemed"

    def __init__(self, var: RunVar[T], value: T | Literal[_NoValueSet.NO_VALUE_SET]):
        self._var = var
        self._value: T | Literal[_NoValueSet.NO_VALUE_SET] = value
        self._redeemed = False


class RunVar(Generic[T]):
    """
    Like a :class:`~contextvars.ContextVar`, except scoped to the running event loop.
    """

    __slots__ = "_name", "_default"

    NO_VALUE_SET: Literal[_NoValueSet.NO_VALUE_SET] = _NoValueSet.NO_VALUE_SET

    _token_wrappers: set[_TokenWrapper] = set()

    def __init__(
        self, name: str, default: T | Literal[_NoValueSet.NO_VALUE_SET] = NO_VALUE_SET
    ):
        self._name = name
        self._default = default

    @property
    def _current_vars(self) -> dict[str, T]:
        token = current_token()
        try:
            return _run_vars[token]
        except KeyError:
            run_vars = _run_vars[token] = {}
            return run_vars

    @overload
    def get(self, default: D) -> T | D: ...

    @overload
    def get(self) -> T: ...

    def get(
        self, default: D | Literal[_NoValueSet.NO_VALUE_SET] = NO_VALUE_SET
    ) -> T | D:
        try:
            return self._current_vars[self._name]
        except KeyError:
            if default is not RunVar.NO_VALUE_SET:
                return default
            elif self._default is not RunVar.NO_VALUE_SET:
                return self._default

        raise LookupError(
            f'Run variable "{self._name}" has no value and no default set'
        )

    def set(self, value: T) -> RunvarToken[T]:
        current_vars = self._current_vars
        token = RunvarToken(self, current_vars.get(self._name, RunVar.NO_VALUE_SET))
        current_vars[self._name] = value
        return token

    def reset(self, token: RunvarToken[T]) -> None:
        if token._var is not self:
            raise ValueError("This token does not belong to this RunVar")

        if token._redeemed:
            raise ValueError("This token has already been used")

        if token._value is _NoValueSet.NO_VALUE_SET:
            try:
                del self._current_vars[self._name]
            except KeyError:
                pass
        else:
            self._current_vars[self._name] = token._value

        token._redeemed = True

    def __repr__(self) -> str:
        return f"<RunVar name={self._name!r}>"

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\types\base.py ===
# Copyright 2024 The HuggingFace Team. All rights reserved.
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
"""Contains a base class for all inference types."""

import inspect
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Type, TypeVar, Union, get_args


T = TypeVar("T", bound="BaseInferenceType")


def _repr_with_extra(self):
    fields = list(self.__dataclass_fields__.keys())
    other_fields = list(k for k in self.__dict__ if k not in fields)
    return f"{self.__class__.__name__}({', '.join(f'{k}={self.__dict__[k]!r}' for k in fields + other_fields)})"


def dataclass_with_extra(cls: Type[T]) -> Type[T]:
    """Decorator to add a custom __repr__ method to a dataclass, showing all fields, including extra ones.

    This decorator only works with dataclasses that inherit from `BaseInferenceType`.
    """
    cls = dataclass(cls)
    cls.__repr__ = _repr_with_extra  # type: ignore[method-assign]
    return cls


@dataclass
class BaseInferenceType(dict):
    """Base class for all inference types.

    Object is a dataclass and a dict for backward compatibility but plan is to remove the dict part in the future.

    Handle parsing from dict, list and json strings in a permissive way to ensure future-compatibility (e.g. all fields
    are made optional, and non-expected fields are added as dict attributes).
    """

    @classmethod
    def parse_obj_as_list(cls: Type[T], data: Union[bytes, str, List, Dict]) -> List[T]:
        """Alias to parse server response and return a single instance.

        See `parse_obj` for more details.
        """
        output = cls.parse_obj(data)
        if not isinstance(output, list):
            raise ValueError(f"Invalid input data for {cls}. Expected a list, but got {type(output)}.")
        return output

    @classmethod
    def parse_obj_as_instance(cls: Type[T], data: Union[bytes, str, List, Dict]) -> T:
        """Alias to parse server response and return a single instance.

        See `parse_obj` for more details.
        """
        output = cls.parse_obj(data)
        if isinstance(output, list):
            raise ValueError(f"Invalid input data for {cls}. Expected a single instance, but got a list.")
        return output

    @classmethod
    def parse_obj(cls: Type[T], data: Union[bytes, str, List, Dict]) -> Union[List[T], T]:
        """Parse server response as a dataclass or list of dataclasses.

        To enable future-compatibility, we want to handle cases where the server return more fields than expected.
        In such cases, we don't want to raise an error but still create the dataclass object. Remaining fields are
        added as dict attributes.
        """
        # Parse server response (from bytes)
        if isinstance(data, bytes):
            data = data.decode()
        if isinstance(data, str):
            data = json.loads(data)

        # If a list, parse each item individually
        if isinstance(data, List):
            return [cls.parse_obj(d) for d in data]  # type: ignore [misc]

        # At this point, we expect a dict
        if not isinstance(data, dict):
            raise ValueError(f"Invalid data type: {type(data)}")

        init_values = {}
        other_values = {}
        for key, value in data.items():
            key = normalize_key(key)
            if key in cls.__dataclass_fields__ and cls.__dataclass_fields__[key].init:
                if isinstance(value, dict) or isinstance(value, list):
                    field_type = cls.__dataclass_fields__[key].type

                    # if `field_type` is a `BaseInferenceType`, parse it
                    if inspect.isclass(field_type) and issubclass(field_type, BaseInferenceType):
                        value = field_type.parse_obj(value)

                    # otherwise, recursively parse nested dataclasses (if possible)
                    # `get_args` returns handle Union and Optional for us
                    else:
                        expected_types = get_args(field_type)
                        for expected_type in expected_types:
                            if getattr(expected_type, "_name", None) == "List":
                                expected_type = get_args(expected_type)[
                                    0
                                ]  # assume same type for all items in the list
                            if inspect.isclass(expected_type) and issubclass(expected_type, BaseInferenceType):
                                value = expected_type.parse_obj(value)
                                break
                init_values[key] = value
            else:
                other_values[key] = value

        # Make all missing fields default to None
        # => ensure that dataclass initialization will never fail even if the server does not return all fields.
        for key in cls.__dataclass_fields__:
            if key not in init_values:
                init_values[key] = None

        # Initialize dataclass with expected values
        item = cls(**init_values)

        # Add remaining fields as dict attributes
        item.update(other_values)

        # Add remaining fields as extra dataclass fields.
        # They won't be part of the dataclass fields but will be accessible as attributes.
        # Use @dataclass_with_extra to show them in __repr__.
        item.__dict__.update(other_values)
        return item

    def __post_init__(self):
        self.update(asdict(self))

    def __setitem__(self, __key: Any, __value: Any) -> None:
        # Hacky way to keep dataclass values in sync when dict is updated
        super().__setitem__(__key, __value)
        if __key in self.__dataclass_fields__ and getattr(self, __key, None) != __value:
            self.__setattr__(__key, __value)
        return

    def __setattr__(self, __name: str, __value: Any) -> None:
        # Hacky way to keep dict values is sync when dataclass is updated
        super().__setattr__(__name, __value)
        if self.get(__name) != __value:
            self[__name] = __value
        return


def normalize_key(key: str) -> str:
    # e.g "content-type" -> "content_type", "Accept" -> "accept"
    return key.replace("-", "_").replace(" ", "_").lower()

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\browser\browser.py ===
import threading
import time

import html2text
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


class Browser:
    def __init__(self, computer):
        self.computer = computer
        self._driver = None

    @property
    def driver(self, headless=False):
        if self._driver is None:
            self.setup(headless)
        return self._driver

    @driver.setter
    def driver(self, value):
        self._driver = value

    def search(self, query):
        """
        Searches the web for the specified query and returns the results.
        """
        response = requests.get(
            f'{self.computer.api_base.strip("/")}/browser/search',
            params={"query": query},
        )
        return response.json()["result"]

    def fast_search(self, query):
        """
        Searches the web for the specified query and returns the results.
        """

        # Start the request in a separate thread
        response_thread = threading.Thread(
            target=lambda: setattr(
                threading.current_thread(),
                "response",
                requests.get(
                    f'{self.computer.api_base.strip("/")}/browser/search',
                    params={"query": query},
                ),
            )
        )
        response_thread.start()

        # Perform the Google search
        self.search_google(query, delays=False)

        # Wait for the request to complete and get the result
        response_thread.join()
        response = response_thread.response

        return response.json()["result"]

    def setup(self, headless):
        try:
            self.service = Service(ChromeDriverManager().install())
            self.options = webdriver.ChromeOptions()
            # Run Chrome in headless mode
            if headless:
                self.options.add_argument("--headless")
                self.options.add_argument("--disable-gpu")
                self.options.add_argument("--no-sandbox")
            self._driver = webdriver.Chrome(service=self.service, options=self.options)
        except Exception as e:
            print(f"An error occurred while setting up the WebDriver: {e}")
            self._driver = None

    def go_to_url(self, url):
        """Navigate to a URL"""
        self.driver.get(url)
        time.sleep(1)

    def search_google(self, query, delays=True):
        """Perform a Google search"""
        self.driver.get("https://www.perplexity.ai")
        # search_box = self.driver.find_element(By.NAME, 'q')
        # search_box.send_keys(query)
        # search_box.send_keys(Keys.RETURN)
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.COMMAND + "k")
        time.sleep(0.5)
        active_element = self.driver.switch_to.active_element
        active_element.send_keys(query)
        active_element.send_keys(Keys.RETURN)
        if delays:
            time.sleep(3)

    def analyze_page(self, intent):
        """Extract HTML, list interactive elements, and analyze with AI"""
        html_content = self.driver.page_source
        text_content = html2text.html2text(html_content)

        # text_content = text_content[:len(text_content)//2]

        elements = (
            self.driver.find_elements(By.TAG_NAME, "a")
            + self.driver.find_elements(By.TAG_NAME, "button")
            + self.driver.find_elements(By.TAG_NAME, "input")
            + self.driver.find_elements(By.TAG_NAME, "select")
        )

        elements_info = [
            {
                "id": idx,
                "text": elem.text,
                "attributes": elem.get_attribute("outerHTML"),
            }
            for idx, elem in enumerate(elements)
        ]

        ai_query = f"""
        Below is the content of the current webpage along with interactive elements. 
        Given the intent "{intent}", please extract useful information and provide sufficient details 
        about interactive elements, focusing especially on those pertinent to the provided intent.
        
        If the information requested by the intent "{intent}" is present on the page, simply return that.

        If not, return the top 10 most relevant interactive elements in a concise, actionable format, listing them on separate lines
        with their ID, a description, and their possible action.

        Do not hallucinate.

        Page Content:
        {text_content}
        
        Interactive Elements:
        {elements_info}
        """

        # response = self.computer.ai.chat(ai_query)

        # screenshot = self.driver.get_screenshot_as_base64()
        # old_model = self.computer.interpreter.llm.model
        # self.computer.interpreter.llm.model = "gpt-4o-mini"
        # response = self.computer.ai.chat(ai_query, base64=screenshot)
        # self.computer.interpreter.llm.model = old_model

        old_model = self.computer.interpreter.llm.model
        self.computer.interpreter.llm.model = "gpt-4o-mini"
        response = self.computer.ai.chat(ai_query)
        self.computer.interpreter.llm.model = old_model

        print(response)
        print(
            "Please now utilize this information or interact with the interactive elements provided to answer the user's query."
        )

    def quit(self):
        """Close the browser"""
        self.driver.quit()

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\mail\mail.py ===
import os
import platform
import re
import subprocess

from ..utils.run_applescript import run_applescript, run_applescript_capture


class Mail:
    def __init__(self, computer):
        self.computer = computer
        # In the future, we should allow someone to specify their own mail app
        self.mail_app = "Mail"

    def get(self, number=5, unread: bool = False):
        """
        Retrieves the last {number} emails from the inbox, optionally filtering for only unread emails.
        """
        if platform.system() != "Darwin":
            return "This method is only supported on MacOS"

        too_many_emails_msg = ""
        if number > 50:
            number = min(number, 50)
            too_many_emails_msg = (
                "This method is limited to 10 emails, returning the first 10: "
            )
        # This is set up to retry if the number of emails is less than the number requested, but only a max of three times
        retries = 0  # Initialize the retry counter
        while retries < 3:
            read_status_filter = "whose read status is false" if unread else ""
            script = f"""
            tell application "{self.mail_app}"
                set latest_messages to messages of inbox {read_status_filter}
                set email_data to {{}}
                repeat with i from 1 to {number}
                    set this_message to item i of latest_messages
                    set end of email_data to {{subject:subject of this_message, sender:sender of this_message, content:content of this_message}}
                end repeat
                return email_data
            end tell
            """
            stdout, stderr = run_applescript_capture(script)

            # if the error is due to not having enough emails, retry with the available emails.
            if "Can’t get item" in stderr:
                match = re.search(r"Can’t get item (\d+) of", stderr)
                if match:
                    available_emails = int(match.group(1)) - 1
                    if available_emails > 0:
                        number = available_emails
                        retries += 1
                        continue
                break
            elif stdout:
                if too_many_emails_msg:
                    return f"{too_many_emails_msg}\n\n{stdout}"
                else:
                    return stdout

    def send(self, to, subject, body, attachments=None):
        """
        Sends an email with the given parameters using the default mail app.
        """
        if platform.system() != "Darwin":
            return "This method is only supported on MacOS"

        # Strip newlines from the to field
        to = to.replace("\n", "")

        attachment_clause = ""
        delay_seconds = 5  # Default delay in seconds

        if attachments:
            formatted_attachments = [
                self.format_path_for_applescript(path) for path in attachments
            ]

            # Generate AppleScript to attach each file
            attachment_clause = "\n".join(
                f"make new attachment with properties {{file name:{path}}} at after the last paragraph of the content of new_message"
                for path in formatted_attachments
            )

            # Calculate the delay based on the size of the attachments
            delay_seconds = self.calculate_upload_delay(attachments)

            print(f"Uploading attachments. This should take ~{delay_seconds} seconds.")

        # In the future, we might consider allowing the llm to specify an email to send from
        script = f"""
        tell application "{self.mail_app}"
            set new_message to make new outgoing message with properties {{subject:"{subject}", content:"{body}"}} at end of outgoing messages
            tell new_message
                set visible to true
                make new to recipient at end of to recipients with properties {{address:"{to}"}}
                {attachment_clause}
            end tell
            {f'delay {delay_seconds}' if attachments else ''}
            send new_message
        end tell
        """
        try:
            run_applescript(script)
            return f"""Email sent to {to}"""
        except subprocess.CalledProcessError:
            return "Failed to send email"

    def unread_count(self):
        """
        Retrieves the count of unread emails in the inbox, limited to 50.
        """
        if platform.system() != "Darwin":
            return "This method is only supported on MacOS"

        script = f"""
            tell application "{self.mail_app}"
                set unreadMessages to (messages of inbox whose read status is false)
                if (count of unreadMessages) > 50 then
                    return 50
                else
                    return count of unreadMessages
                end if
            end tell
            """
        try:
            unreads = int(run_applescript(script))
            if unreads >= 50:
                return "50 or more"
            return unreads
        except subprocess.CalledProcessError as e:
            print(e)
            return 0

    # Estimate how long something will take to upload
    def calculate_upload_delay(self, attachments):
        try:
            total_size_mb = sum(
                os.path.getsize(os.path.expanduser(att)) for att in attachments
            ) / (1024 * 1024)
            # Assume 1 MBps upload speed, which is conservative on purpose
            upload_speed_mbps = 1
            estimated_time_seconds = total_size_mb / upload_speed_mbps
            return round(
                max(0.2, estimated_time_seconds + 1), 1
            )  # Add 1 second buffer, ensure a minimum delay of 1.2 seconds, rounded to one decimal place
        except:
            # Return a default delay of 5 seconds if an error occurs
            return 5

    def format_path_for_applescript(self, file_path):
        # Escape backslashes, quotes, and curly braces for AppleScript
        file_path = (
            file_path.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("{", "\\{")
            .replace("}", "\\}")
        )
        # Convert to a POSIX path and quote for AppleScript
        posix_path = f'POSIX file "{file_path}"'
        return posix_path

# === NexusCore/openenv\Lib\site-packages\litellm\assistants\utils.py ===
from typing import Optional, Union

import litellm

from ..exceptions import UnsupportedParamsError
from ..types.llms.openai import *


def get_optional_params_add_message(
    role: Optional[str],
    content: Optional[
        Union[
            str,
            List[
                Union[
                    MessageContentTextObject,
                    MessageContentImageFileObject,
                    MessageContentImageURLObject,
                ]
            ],
        ]
    ],
    attachments: Optional[List[Attachment]],
    metadata: Optional[dict],
    custom_llm_provider: str,
    **kwargs,
):
    """
    Azure doesn't support 'attachments' for creating a message

    Reference - https://learn.microsoft.com/en-us/azure/ai-services/openai/assistants-reference-messages?tabs=python#create-message
    """
    passed_params = locals()
    custom_llm_provider = passed_params.pop("custom_llm_provider")
    special_params = passed_params.pop("kwargs")
    for k, v in special_params.items():
        passed_params[k] = v

    default_params = {
        "role": None,
        "content": None,
        "attachments": None,
        "metadata": None,
    }

    non_default_params = {
        k: v
        for k, v in passed_params.items()
        if (k in default_params and v != default_params[k])
    }
    optional_params = {}

    ## raise exception if non-default value passed for non-openai/azure embedding calls
    def _check_valid_arg(supported_params):
        if len(non_default_params.keys()) > 0:
            keys = list(non_default_params.keys())
            for k in keys:
                if (
                    litellm.drop_params is True and k not in supported_params
                ):  # drop the unsupported non-default values
                    non_default_params.pop(k, None)
                elif k not in supported_params:
                    raise litellm.utils.UnsupportedParamsError(
                        status_code=500,
                        message="k={}, not supported by {}. Supported params={}. To drop it from the call, set `litellm.drop_params = True`.".format(
                            k, custom_llm_provider, supported_params
                        ),
                    )
            return non_default_params

    if custom_llm_provider == "openai":
        optional_params = non_default_params
    elif custom_llm_provider == "azure":
        supported_params = (
            litellm.AzureOpenAIAssistantsAPIConfig().get_supported_openai_create_message_params()
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.AzureOpenAIAssistantsAPIConfig().map_openai_params_create_message_params(
            non_default_params=non_default_params, optional_params=optional_params
        )
    for k in passed_params.keys():
        if k not in default_params.keys():
            optional_params[k] = passed_params[k]
    return optional_params


def get_optional_params_image_gen(
    n: Optional[int] = None,
    quality: Optional[str] = None,
    response_format: Optional[str] = None,
    size: Optional[str] = None,
    style: Optional[str] = None,
    user: Optional[str] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
):
    # retrieve all parameters passed to the function
    passed_params = locals()
    custom_llm_provider = passed_params.pop("custom_llm_provider")
    special_params = passed_params.pop("kwargs")
    for k, v in special_params.items():
        passed_params[k] = v

    default_params = {
        "n": None,
        "quality": None,
        "response_format": None,
        "size": None,
        "style": None,
        "user": None,
    }

    non_default_params = {
        k: v
        for k, v in passed_params.items()
        if (k in default_params and v != default_params[k])
    }
    optional_params = {}

    ## raise exception if non-default value passed for non-openai/azure embedding calls
    def _check_valid_arg(supported_params):
        if len(non_default_params.keys()) > 0:
            keys = list(non_default_params.keys())
            for k in keys:
                if (
                    litellm.drop_params is True and k not in supported_params
                ):  # drop the unsupported non-default values
                    non_default_params.pop(k, None)
                elif k not in supported_params:
                    raise UnsupportedParamsError(
                        status_code=500,
                        message=f"Setting user/encoding format is not supported by {custom_llm_provider}. To drop it from the call, set `litellm.drop_params = True`.",
                    )
            return non_default_params

    if (
        custom_llm_provider == "openai"
        or custom_llm_provider == "azure"
        or custom_llm_provider in litellm.openai_compatible_providers
    ):
        optional_params = non_default_params
    elif custom_llm_provider == "bedrock":
        supported_params = ["size"]
        _check_valid_arg(supported_params=supported_params)
        if size is not None:
            width, height = size.split("x")
            optional_params["width"] = int(width)
            optional_params["height"] = int(height)
    elif custom_llm_provider == "vertex_ai":
        supported_params = ["n"]
        """
        All params here: https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/imagegeneration?project=adroit-crow-413218
        """
        _check_valid_arg(supported_params=supported_params)
        if n is not None:
            optional_params["sampleCount"] = int(n)

    for k in passed_params.keys():
        if k not in default_params.keys():
            optional_params[k] = passed_params[k]
    return optional_params

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_transaction_queue\spend_log_cleanup.py ===
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from litellm._logging import verbose_proxy_logger
from litellm.caching import RedisCache
from litellm.constants import (
    SPEND_LOG_CLEANUP_BATCH_SIZE,
    SPEND_LOG_CLEANUP_JOB_NAME,
    SPEND_LOG_RUN_LOOPS,
)
from litellm.litellm_core_utils.duration_parser import duration_in_seconds
from litellm.proxy.utils import PrismaClient


class SpendLogCleanup:
    """
    Handles cleaning up old spend logs based on maximum retention period.
    Deletes logs in batches to prevent timeouts.
    Uses PodLockManager to ensure only one pod runs cleanup in multi-pod deployments.
    """

    def __init__(self, general_settings=None, redis_cache: Optional[RedisCache] = None):
        self.batch_size = SPEND_LOG_CLEANUP_BATCH_SIZE
        self.retention_seconds: Optional[int] = None
        from litellm.proxy.proxy_server import general_settings as default_settings

        self.general_settings = general_settings or default_settings
        from litellm.proxy.proxy_server import proxy_logging_obj

        pod_lock_manager = proxy_logging_obj.db_spend_update_writer.pod_lock_manager
        self.pod_lock_manager = pod_lock_manager
        verbose_proxy_logger.info(
            f"SpendLogCleanup initialized with batch size: {self.batch_size}"
        )

    def _should_delete_spend_logs(self) -> bool:
        """
        Determines if logs should be deleted based on the max retention period in settings.
        """
        retention_setting = self.general_settings.get(
            "maximum_spend_logs_retention_period"
        )
        verbose_proxy_logger.info(f"Checking retention setting: {retention_setting}")

        if retention_setting is None:
            verbose_proxy_logger.info("No retention setting found")
            return False

        try:
            if isinstance(retention_setting, int):
                retention_setting = str(retention_setting)
            self.retention_seconds = duration_in_seconds(retention_setting)
            verbose_proxy_logger.info(
                f"Retention period set to {self.retention_seconds} seconds"
            )
            return True
        except ValueError as e:
            verbose_proxy_logger.error(
                f"Invalid maximum_spend_logs_retention_period value: {retention_setting}, error: {str(e)}"
            )
            return False

    async def _delete_old_logs(
        self, prisma_client: PrismaClient, cutoff_date: datetime
    ) -> int:
        """
        Helper method to delete old logs in batches.
        Returns the total number of logs deleted.
        """
        total_deleted = 0
        run_count = 0
        while True:
            if run_count > SPEND_LOG_RUN_LOOPS:
                verbose_proxy_logger.info(
                    "Max logs deleted - 1,00,000, rest of the logs will be deleted in next run"
                )
                break
            # Step 1: Find logs to delete
            logs_to_delete = await prisma_client.db.litellm_spendlogs.find_many(
                where={"startTime": {"lt": cutoff_date}},
                take=self.batch_size,
            )
            verbose_proxy_logger.info(f"Found {len(logs_to_delete)} logs in this batch")

            if not logs_to_delete:
                verbose_proxy_logger.info(
                    f"No more logs to delete. Total deleted: {total_deleted}"
                )
                break

            request_ids = [log.request_id for log in logs_to_delete]

            # Step 2: Delete them in one go
            await prisma_client.db.litellm_spendlogs.delete_many(
                where={"request_id": {"in": request_ids}}
            )

            total_deleted += len(logs_to_delete)
            run_count += 1

            # Add a small sleep to prevent overwhelming the database
            await asyncio.sleep(0.1)

        return total_deleted

    async def cleanup_old_spend_logs(self, prisma_client: PrismaClient) -> None:
        """
        Main cleanup function. Deletes old spend logs in batches.
        If pod_lock_manager is available, ensures only one pod runs cleanup.
        If no pod_lock_manager, runs cleanup without distributed locking.
        """
        try:
            verbose_proxy_logger.info(f"Cleanup job triggered at {datetime.now()}")

            if not self._should_delete_spend_logs():
                verbose_proxy_logger.info(
                    "Skipping cleanup — invalid or missing retention setting."
                )
                return

            if self.retention_seconds is None:
                verbose_proxy_logger.error(
                    "Retention seconds is None, cannot proceed with cleanup"
                )
                return

            # If we have a pod lock manager, try to acquire the lock
            if self.pod_lock_manager and self.pod_lock_manager.redis_cache:
                lock_acquired = await self.pod_lock_manager.acquire_lock(
                    cronjob_id=SPEND_LOG_CLEANUP_JOB_NAME,
                )
                verbose_proxy_logger.info(
                    f"Lock acquisition attempt: {'successful' if lock_acquired else 'failed'}  at {datetime.now()}"
                )

                if not lock_acquired:
                    verbose_proxy_logger.info("Another pod is already running cleanup")
                    return

            cutoff_date = datetime.now(timezone.utc) - timedelta(
                seconds=float(self.retention_seconds)
            )
            verbose_proxy_logger.info(
                f"Deleting logs older than {cutoff_date.isoformat()}"
            )

            # Perform the actual deletion
            total_deleted = await self._delete_old_logs(prisma_client, cutoff_date)
            verbose_proxy_logger.info(f"Deleted {total_deleted} logs")

        except Exception as e:
            verbose_proxy_logger.error(f"Error during cleanup: {str(e)}")
            return  # Return after error handling
        finally:
            # Always release the lock if we have a pod lock manager
            if self.pod_lock_manager and self.pod_lock_manager.redis_cache:
                await self.pod_lock_manager.release_lock(
                    cronjob_id=SPEND_LOG_CLEANUP_JOB_NAME
                )
                verbose_proxy_logger.info("Released cleanup lock")

# === NexusCore/openenv\Lib\site-packages\openai\types\fine_tuning\fine_tuning_job.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal

from ..._models import BaseModel
from .dpo_method import DpoMethod
from ..shared.metadata import Metadata
from .supervised_method import SupervisedMethod
from .reinforcement_method import ReinforcementMethod
from .fine_tuning_job_wandb_integration_object import FineTuningJobWandbIntegrationObject

__all__ = ["FineTuningJob", "Error", "Hyperparameters", "Method"]


class Error(BaseModel):
    code: str
    """A machine-readable error code."""

    message: str
    """A human-readable error message."""

    param: Optional[str] = None
    """The parameter that was invalid, usually `training_file` or `validation_file`.

    This field will be null if the failure was not parameter-specific.
    """


class Hyperparameters(BaseModel):
    batch_size: Union[Literal["auto"], int, None] = None
    """Number of examples in each batch.

    A larger batch size means that model parameters are updated less frequently, but
    with lower variance.
    """

    learning_rate_multiplier: Union[Literal["auto"], float, None] = None
    """Scaling factor for the learning rate.

    A smaller learning rate may be useful to avoid overfitting.
    """

    n_epochs: Union[Literal["auto"], int, None] = None
    """The number of epochs to train the model for.

    An epoch refers to one full cycle through the training dataset.
    """


class Method(BaseModel):
    type: Literal["supervised", "dpo", "reinforcement"]
    """The type of method. Is either `supervised`, `dpo`, or `reinforcement`."""

    dpo: Optional[DpoMethod] = None
    """Configuration for the DPO fine-tuning method."""

    reinforcement: Optional[ReinforcementMethod] = None
    """Configuration for the reinforcement fine-tuning method."""

    supervised: Optional[SupervisedMethod] = None
    """Configuration for the supervised fine-tuning method."""


class FineTuningJob(BaseModel):
    id: str
    """The object identifier, which can be referenced in the API endpoints."""

    created_at: int
    """The Unix timestamp (in seconds) for when the fine-tuning job was created."""

    error: Optional[Error] = None
    """
    For fine-tuning jobs that have `failed`, this will contain more information on
    the cause of the failure.
    """

    fine_tuned_model: Optional[str] = None
    """The name of the fine-tuned model that is being created.

    The value will be null if the fine-tuning job is still running.
    """

    finished_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the fine-tuning job was finished.

    The value will be null if the fine-tuning job is still running.
    """

    hyperparameters: Hyperparameters
    """The hyperparameters used for the fine-tuning job.

    This value will only be returned when running `supervised` jobs.
    """

    model: str
    """The base model that is being fine-tuned."""

    object: Literal["fine_tuning.job"]
    """The object type, which is always "fine_tuning.job"."""

    organization_id: str
    """The organization that owns the fine-tuning job."""

    result_files: List[str]
    """The compiled results file ID(s) for the fine-tuning job.

    You can retrieve the results with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    seed: int
    """The seed used for the fine-tuning job."""

    status: Literal["validating_files", "queued", "running", "succeeded", "failed", "cancelled"]
    """
    The current status of the fine-tuning job, which can be either
    `validating_files`, `queued`, `running`, `succeeded`, `failed`, or `cancelled`.
    """

    trained_tokens: Optional[int] = None
    """The total number of billable tokens processed by this fine-tuning job.

    The value will be null if the fine-tuning job is still running.
    """

    training_file: str
    """The file ID used for training.

    You can retrieve the training data with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    validation_file: Optional[str] = None
    """The file ID used for validation.

    You can retrieve the validation results with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    estimated_finish: Optional[int] = None
    """
    The Unix timestamp (in seconds) for when the fine-tuning job is estimated to
    finish. The value will be null if the fine-tuning job is not running.
    """

    integrations: Optional[List[FineTuningJobWandbIntegrationObject]] = None
    """A list of integrations to enable for this fine-tuning job."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    method: Optional[Method] = None
    """The method used for fine-tuning."""

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\cachecontrol\adapter.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import functools
import types
import zlib
from typing import TYPE_CHECKING, Any, Collection, Mapping

from pip._vendor.requests.adapters import HTTPAdapter

from pip._vendor.cachecontrol.cache import DictCache
from pip._vendor.cachecontrol.controller import PERMANENT_REDIRECT_STATUSES, CacheController
from pip._vendor.cachecontrol.filewrapper import CallbackFileWrapper

if TYPE_CHECKING:
    from pip._vendor.requests import PreparedRequest, Response
    from pip._vendor.urllib3 import HTTPResponse

    from pip._vendor.cachecontrol.cache import BaseCache
    from pip._vendor.cachecontrol.heuristics import BaseHeuristic
    from pip._vendor.cachecontrol.serialize import Serializer


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = {"PUT", "PATCH", "DELETE"}

    def __init__(
        self,
        cache: BaseCache | None = None,
        cache_etags: bool = True,
        controller_class: type[CacheController] | None = None,
        serializer: Serializer | None = None,
        heuristic: BaseHeuristic | None = None,
        cacheable_methods: Collection[str] | None = None,
        *args: Any,
        **kw: Any,
    ) -> None:
        super().__init__(*args, **kw)
        self.cache = DictCache() if cache is None else cache
        self.heuristic = heuristic
        self.cacheable_methods = cacheable_methods or ("GET",)

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache, cache_etags=cache_etags, serializer=serializer
        )

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: (None | bytes | str | tuple[bytes | str, bytes | str]) = None,
        proxies: Mapping[str, str] | None = None,
        cacheable_methods: Collection[str] | None = None,
    ) -> Response:
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        cacheable = cacheable_methods or self.cacheable_methods
        if request.method in cacheable:
            try:
                cached_response = self.controller.cached_request(request)
            except zlib.error:
                cached_response = None
            if cached_response:
                return self.build_response(request, cached_response, from_cache=True)

            # check for etags and add headers if appropriate
            request.headers.update(self.controller.conditional_headers(request))

        resp = super().send(request, stream, timeout, verify, cert, proxies)

        return resp

    def build_response(  # type: ignore[override]
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        from_cache: bool = False,
        cacheable_methods: Collection[str] | None = None,
    ) -> Response:
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        cacheable = cacheable_methods or self.cacheable_methods
        if not from_cache and request.method in cacheable:
            # Check for any heuristics that might update headers
            # before trying to cache.
            if self.heuristic:
                response = self.heuristic.apply(response)

            # apply any expiration heuristics
            if response.status == 304:
                # We must have sent an ETag request. This could mean
                # that we've been expired already or that we simply
                # have an etag. In either case, we want to try and
                # update the cache if that is the case.
                cached_response = self.controller.update_cached_response(
                    request, response
                )

                if cached_response is not response:
                    from_cache = True

                # We are done with the server response, read a
                # possible response body (compliant servers will
                # not return one, but we cannot be 100% sure) and
                # release the connection back to the pool.
                response.read(decode_content=False)
                response.release_conn()

                response = cached_response

            # We always cache the 301 responses
            elif int(response.status) in PERMANENT_REDIRECT_STATUSES:
                self.controller.cache_response(request, response)
            else:
                # Wrap the response file with a wrapper that will cache the
                #   response when the stream has been consumed.
                response._fp = CallbackFileWrapper(  # type: ignore[assignment]
                    response._fp,  # type: ignore[arg-type]
                    functools.partial(
                        self.controller.cache_response, request, response
                    ),
                )
                if response.chunked:
                    super_update_chunk_length = response._update_chunk_length

                    def _update_chunk_length(self: HTTPResponse) -> None:
                        super_update_chunk_length()
                        if self.chunk_left == 0:
                            self._fp._close()  # type: ignore[union-attr]

                    response._update_chunk_length = types.MethodType(  # type: ignore[method-assign]
                        _update_chunk_length, response
                    )

        resp: Response = super().build_response(request, response)

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            assert request.url is not None
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache  # type: ignore[attr-defined]

        return resp

    def close(self) -> None:
        self.cache.close()
        super().close()  # type: ignore[no-untyped-call]

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\error_wrappers.py ===
import json
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Sequence, Tuple, Type, Union

from pydantic.v1.json import pydantic_encoder
from pydantic.v1.utils import Representation

if TYPE_CHECKING:
    from typing_extensions import TypedDict

    from pydantic.v1.config import BaseConfig
    from pydantic.v1.types import ModelOrDc
    from pydantic.v1.typing import ReprArgs

    Loc = Tuple[Union[int, str], ...]

    class _ErrorDictRequired(TypedDict):
        loc: Loc
        msg: str
        type: str

    class ErrorDict(_ErrorDictRequired, total=False):
        ctx: Dict[str, Any]


__all__ = 'ErrorWrapper', 'ValidationError'


class ErrorWrapper(Representation):
    __slots__ = 'exc', '_loc'

    def __init__(self, exc: Exception, loc: Union[str, 'Loc']) -> None:
        self.exc = exc
        self._loc = loc

    def loc_tuple(self) -> 'Loc':
        if isinstance(self._loc, tuple):
            return self._loc
        else:
            return (self._loc,)

    def __repr_args__(self) -> 'ReprArgs':
        return [('exc', self.exc), ('loc', self.loc_tuple())]


# ErrorList is something like Union[List[Union[List[ErrorWrapper], ErrorWrapper]], ErrorWrapper]
# but recursive, therefore just use:
ErrorList = Union[Sequence[Any], ErrorWrapper]


class ValidationError(Representation, ValueError):
    __slots__ = 'raw_errors', 'model', '_error_cache'

    def __init__(self, errors: Sequence[ErrorList], model: 'ModelOrDc') -> None:
        self.raw_errors = errors
        self.model = model
        self._error_cache: Optional[List['ErrorDict']] = None

    def errors(self) -> List['ErrorDict']:
        if self._error_cache is None:
            try:
                config = self.model.__config__  # type: ignore
            except AttributeError:
                config = self.model.__pydantic_model__.__config__  # type: ignore
            self._error_cache = list(flatten_errors(self.raw_errors, config))
        return self._error_cache

    def json(self, *, indent: Union[None, int, str] = 2) -> str:
        return json.dumps(self.errors(), indent=indent, default=pydantic_encoder)

    def __str__(self) -> str:
        errors = self.errors()
        no_errors = len(errors)
        return (
            f'{no_errors} validation error{"" if no_errors == 1 else "s"} for {self.model.__name__}\n'
            f'{display_errors(errors)}'
        )

    def __repr_args__(self) -> 'ReprArgs':
        return [('model', self.model.__name__), ('errors', self.errors())]


def display_errors(errors: List['ErrorDict']) -> str:
    return '\n'.join(f'{_display_error_loc(e)}\n  {e["msg"]} ({_display_error_type_and_ctx(e)})' for e in errors)


def _display_error_loc(error: 'ErrorDict') -> str:
    return ' -> '.join(str(e) for e in error['loc'])


def _display_error_type_and_ctx(error: 'ErrorDict') -> str:
    t = 'type=' + error['type']
    ctx = error.get('ctx')
    if ctx:
        return t + ''.join(f'; {k}={v}' for k, v in ctx.items())
    else:
        return t


def flatten_errors(
    errors: Sequence[Any], config: Type['BaseConfig'], loc: Optional['Loc'] = None
) -> Generator['ErrorDict', None, None]:
    for error in errors:
        if isinstance(error, ErrorWrapper):
            if loc:
                error_loc = loc + error.loc_tuple()
            else:
                error_loc = error.loc_tuple()

            if isinstance(error.exc, ValidationError):
                yield from flatten_errors(error.exc.raw_errors, config, error_loc)
            else:
                yield error_dict(error.exc, config, error_loc)
        elif isinstance(error, list):
            yield from flatten_errors(error, config, loc=loc)
        else:
            raise RuntimeError(f'Unknown error object: {error}')


def error_dict(exc: Exception, config: Type['BaseConfig'], loc: 'Loc') -> 'ErrorDict':
    type_ = get_exc_type(exc.__class__)
    msg_template = config.error_msg_templates.get(type_) or getattr(exc, 'msg_template', None)
    ctx = exc.__dict__
    if msg_template:
        msg = msg_template.format(**ctx)
    else:
        msg = str(exc)

    d: 'ErrorDict' = {'loc': loc, 'msg': msg, 'type': type_}

    if ctx:
        d['ctx'] = ctx

    return d


_EXC_TYPE_CACHE: Dict[Type[Exception], str] = {}


def get_exc_type(cls: Type[Exception]) -> str:
    # slightly more efficient than using lru_cache since we don't need to worry about the cache filling up
    try:
        return _EXC_TYPE_CACHE[cls]
    except KeyError:
        r = _get_exc_type(cls)
        _EXC_TYPE_CACHE[cls] = r
        return r


def _get_exc_type(cls: Type[Exception]) -> str:
    if issubclass(cls, AssertionError):
        return 'assertion_error'

    base_name = 'type_error' if issubclass(cls, TypeError) else 'value_error'
    if cls in (TypeError, ValueError):
        # just TypeError or ValueError, no extra code
        return base_name

    # if it's not a TypeError or ValueError, we just take the lowercase of the exception name
    # no chaining or snake case logic, use "code" for more complex error types.
    code = getattr(cls, 'code', None) or cls.__name__.replace('Error', '').lower()
    return base_name + '.' + code

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\other.py ===
"""
    pygments.formatters.other
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Other formatters: NullFormatter, RawTokenFormatter.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_choice_opt
from pip._vendor.pygments.token import Token
from pip._vendor.pygments.console import colorize

__all__ = ['NullFormatter', 'RawTokenFormatter', 'TestcaseFormatter']


class NullFormatter(Formatter):
    """
    Output the text unchanged without any formatting.
    """
    name = 'Text only'
    aliases = ['text', 'null']
    filenames = ['*.txt']

    def format(self, tokensource, outfile):
        enc = self.encoding
        for ttype, value in tokensource:
            if enc:
                outfile.write(value.encode(enc))
            else:
                outfile.write(value)


class RawTokenFormatter(Formatter):
    r"""
    Format tokens as a raw representation for storing token streams.

    The format is ``tokentype<TAB>repr(tokenstring)\n``. The output can later
    be converted to a token stream with the `RawTokenLexer`, described in the
    :doc:`lexer list <lexers>`.

    Only two options are accepted:

    `compress`
        If set to ``'gz'`` or ``'bz2'``, compress the output with the given
        compression algorithm after encoding (default: ``''``).
    `error_color`
        If set to a color name, highlight error tokens using that color.  If
        set but with no value, defaults to ``'red'``.

        .. versionadded:: 0.11

    """
    name = 'Raw tokens'
    aliases = ['raw', 'tokens']
    filenames = ['*.raw']

    unicodeoutput = False

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        # We ignore self.encoding if it is set, since it gets set for lexer
        # and formatter if given with -Oencoding on the command line.
        # The RawTokenFormatter outputs only ASCII. Override here.
        self.encoding = 'ascii'  # let pygments.format() do the right thing
        self.compress = get_choice_opt(options, 'compress',
                                       ['', 'none', 'gz', 'bz2'], '')
        self.error_color = options.get('error_color', None)
        if self.error_color is True:
            self.error_color = 'red'
        if self.error_color is not None:
            try:
                colorize(self.error_color, '')
            except KeyError:
                raise ValueError(f"Invalid color {self.error_color!r} specified")

    def format(self, tokensource, outfile):
        try:
            outfile.write(b'')
        except TypeError:
            raise TypeError('The raw tokens formatter needs a binary '
                            'output file')
        if self.compress == 'gz':
            import gzip
            outfile = gzip.GzipFile('', 'wb', 9, outfile)

            write = outfile.write
            flush = outfile.close
        elif self.compress == 'bz2':
            import bz2
            compressor = bz2.BZ2Compressor(9)

            def write(text):
                outfile.write(compressor.compress(text))

            def flush():
                outfile.write(compressor.flush())
                outfile.flush()
        else:
            write = outfile.write
            flush = outfile.flush

        if self.error_color:
            for ttype, value in tokensource:
                line = b"%r\t%r\n" % (ttype, value)
                if ttype is Token.Error:
                    write(colorize(self.error_color, line))
                else:
                    write(line)
        else:
            for ttype, value in tokensource:
                write(b"%r\t%r\n" % (ttype, value))
        flush()


TESTCASE_BEFORE = '''\
    def testNeedsName(lexer):
        fragment = %r
        tokens = [
'''
TESTCASE_AFTER = '''\
        ]
        assert list(lexer.get_tokens(fragment)) == tokens
'''


class TestcaseFormatter(Formatter):
    """
    Format tokens as appropriate for a new testcase.

    .. versionadded:: 2.0
    """
    name = 'Testcase'
    aliases = ['testcase']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        if self.encoding is not None and self.encoding != 'utf-8':
            raise ValueError("Only None and utf-8 are allowed encodings.")

    def format(self, tokensource, outfile):
        indentation = ' ' * 12
        rawbuf = []
        outbuf = []
        for ttype, value in tokensource:
            rawbuf.append(value)
            outbuf.append(f'{indentation}({ttype}, {value!r}),\n')

        before = TESTCASE_BEFORE % (''.join(rawbuf),)
        during = ''.join(outbuf)
        after = TESTCASE_AFTER
        if self.encoding is None:
            outfile.write(before + during + after)
        else:
            outfile.write(before.encode('utf-8'))
            outfile.write(during.encode('utf-8'))
            outfile.write(after.encode('utf-8'))
        outfile.flush()