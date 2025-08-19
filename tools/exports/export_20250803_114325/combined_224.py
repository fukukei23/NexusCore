
# === NexusCore/openenv\Lib\site-packages\openai\types\beta\assistant_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..shared.chat_model import ChatModel
from .assistant_tool_param import AssistantToolParam
from ..shared_params.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from .assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = [
    "AssistantCreateParams",
    "ToolResources",
    "ToolResourcesCodeInterpreter",
    "ToolResourcesFileSearch",
    "ToolResourcesFileSearchVectorStore",
    "ToolResourcesFileSearchVectorStoreChunkingStrategy",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyAuto",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyStatic",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic",
]


class AssistantCreateParams(TypedDict, total=False):
    model: Required[Union[str, ChatModel]]
    """ID of the model to use.

    You can use the
    [List models](https://platform.openai.com/docs/api-reference/models/list) API to
    see all of your available models, or see our
    [Model overview](https://platform.openai.com/docs/models) for descriptions of
    them.
    """

    description: Optional[str]
    """The description of the assistant. The maximum length is 512 characters."""

    instructions: Optional[str]
    """The system instructions that the assistant uses.

    The maximum length is 256,000 characters.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    name: Optional[str]
    """The name of the assistant. The maximum length is 256 characters."""

    reasoning_effort: Optional[ReasoningEffort]
    """**o-series models only**

    Constrains effort on reasoning for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
    supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
    result in faster responses and fewer tokens used on reasoning in a response.
    """

    response_format: Optional[AssistantResponseFormatOptionParam]
    """Specifies the format that the model must output.

    Compatible with [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
    [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
    and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

    Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
    Outputs which ensures the model will match your supplied JSON schema. Learn more
    in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
    message the model generates is valid JSON.

    **Important:** when using JSON mode, you **must** also instruct the model to
    produce JSON yourself via a system or user message. Without this, the model may
    generate an unending stream of whitespace until the generation reaches the token
    limit, resulting in a long-running and seemingly "stuck" request. Also note that
    the message content may be partially cut off if `finish_reason="length"`, which
    indicates the generation exceeded `max_tokens` or the conversation exceeded the
    max context length.
    """

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic.
    """

    tool_resources: Optional[ToolResources]
    """A set of resources that are used by the assistant's tools.

    The resources are specific to the type of tool. For example, the
    `code_interpreter` tool requires a list of file IDs, while the `file_search`
    tool requires a list of vector store IDs.
    """

    tools: Iterable[AssistantToolParam]
    """A list of tool enabled on the assistant.

    There can be a maximum of 128 tools per assistant. Tools can be of types
    `code_interpreter`, `file_search`, or `function`.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or temperature but not both.
    """


class ToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs made
    available to the `code_interpreter` tool. There can be a maximum of 20 files
    associated with the tool.
    """


class ToolResourcesFileSearchVectorStoreChunkingStrategyAuto(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""


class ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic(TypedDict, total=False):
    chunk_overlap_tokens: Required[int]
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: Required[int]
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class ToolResourcesFileSearchVectorStoreChunkingStrategyStatic(TypedDict, total=False):
    static: Required[ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic]

    type: Required[Literal["static"]]
    """Always `static`."""


ToolResourcesFileSearchVectorStoreChunkingStrategy: TypeAlias = Union[
    ToolResourcesFileSearchVectorStoreChunkingStrategyAuto, ToolResourcesFileSearchVectorStoreChunkingStrategyStatic
]


class ToolResourcesFileSearchVectorStore(TypedDict, total=False):
    chunking_strategy: ToolResourcesFileSearchVectorStoreChunkingStrategy
    """The chunking strategy used to chunk the file(s).

    If not set, will use the `auto` strategy.
    """

    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs to
    add to the vector store. There can be a maximum of 10000 files in a vector
    store.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """


class ToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    The
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this assistant. There can be a maximum of 1 vector store attached to
    the assistant.
    """

    vector_stores: Iterable[ToolResourcesFileSearchVectorStore]
    """
    A helper to create a
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    with file_ids and attach it to this assistant. There can be a maximum of 1
    vector store attached to the assistant.
    """


class ToolResources(TypedDict, total=False):
    code_interpreter: ToolResourcesCodeInterpreter

    file_search: ToolResourcesFileSearch

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\response_computer_tool_call.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union
from typing_extensions import Literal, Annotated, TypeAlias

from ..._utils import PropertyInfo
from ..._models import BaseModel

__all__ = [
    "ResponseComputerToolCall",
    "Action",
    "ActionClick",
    "ActionDoubleClick",
    "ActionDrag",
    "ActionDragPath",
    "ActionKeypress",
    "ActionMove",
    "ActionScreenshot",
    "ActionScroll",
    "ActionType",
    "ActionWait",
    "PendingSafetyCheck",
]


class ActionClick(BaseModel):
    button: Literal["left", "right", "wheel", "back", "forward"]
    """Indicates which mouse button was pressed during the click.

    One of `left`, `right`, `wheel`, `back`, or `forward`.
    """

    type: Literal["click"]
    """Specifies the event type.

    For a click action, this property is always set to `click`.
    """

    x: int
    """The x-coordinate where the click occurred."""

    y: int
    """The y-coordinate where the click occurred."""


class ActionDoubleClick(BaseModel):
    type: Literal["double_click"]
    """Specifies the event type.

    For a double click action, this property is always set to `double_click`.
    """

    x: int
    """The x-coordinate where the double click occurred."""

    y: int
    """The y-coordinate where the double click occurred."""


class ActionDragPath(BaseModel):
    x: int
    """The x-coordinate."""

    y: int
    """The y-coordinate."""


class ActionDrag(BaseModel):
    path: List[ActionDragPath]
    """An array of coordinates representing the path of the drag action.

    Coordinates will appear as an array of objects, eg

    ```
    [
      { x: 100, y: 200 },
      { x: 200, y: 300 }
    ]
    ```
    """

    type: Literal["drag"]
    """Specifies the event type.

    For a drag action, this property is always set to `drag`.
    """


class ActionKeypress(BaseModel):
    keys: List[str]
    """The combination of keys the model is requesting to be pressed.

    This is an array of strings, each representing a key.
    """

    type: Literal["keypress"]
    """Specifies the event type.

    For a keypress action, this property is always set to `keypress`.
    """


class ActionMove(BaseModel):
    type: Literal["move"]
    """Specifies the event type.

    For a move action, this property is always set to `move`.
    """

    x: int
    """The x-coordinate to move to."""

    y: int
    """The y-coordinate to move to."""


class ActionScreenshot(BaseModel):
    type: Literal["screenshot"]
    """Specifies the event type.

    For a screenshot action, this property is always set to `screenshot`.
    """


class ActionScroll(BaseModel):
    scroll_x: int
    """The horizontal scroll distance."""

    scroll_y: int
    """The vertical scroll distance."""

    type: Literal["scroll"]
    """Specifies the event type.

    For a scroll action, this property is always set to `scroll`.
    """

    x: int
    """The x-coordinate where the scroll occurred."""

    y: int
    """The y-coordinate where the scroll occurred."""


class ActionType(BaseModel):
    text: str
    """The text to type."""

    type: Literal["type"]
    """Specifies the event type.

    For a type action, this property is always set to `type`.
    """


class ActionWait(BaseModel):
    type: Literal["wait"]
    """Specifies the event type.

    For a wait action, this property is always set to `wait`.
    """


Action: TypeAlias = Annotated[
    Union[
        ActionClick,
        ActionDoubleClick,
        ActionDrag,
        ActionKeypress,
        ActionMove,
        ActionScreenshot,
        ActionScroll,
        ActionType,
        ActionWait,
    ],
    PropertyInfo(discriminator="type"),
]


class PendingSafetyCheck(BaseModel):
    id: str
    """The ID of the pending safety check."""

    code: str
    """The type of the pending safety check."""

    message: str
    """Details about the pending safety check."""


class ResponseComputerToolCall(BaseModel):
    id: str
    """The unique ID of the computer call."""

    action: Action
    """A click action."""

    call_id: str
    """An identifier used when responding to the tool call with output."""

    pending_safety_checks: List[PendingSafetyCheck]
    """The pending safety checks for the computer call."""

    status: Literal["in_progress", "completed", "incomplete"]
    """The status of the item.

    One of `in_progress`, `completed`, or `incomplete`. Populated when items are
    returned via API.
    """

    type: Literal["computer_call"]
    """The type of the computer call. Always `computer_call`."""

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\fortran.py ===
"""
    pygments.lexers.fortran
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Fortran languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, include, words, using, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic

__all__ = ['FortranLexer', 'FortranFixedLexer']


class FortranLexer(RegexLexer):
    """
    Lexer for FORTRAN 90 code.
    """
    name = 'Fortran'
    url = 'https://fortran-lang.org/'
    aliases = ['fortran', 'f90']
    filenames = ['*.f03', '*.f90', '*.F03', '*.F90']
    mimetypes = ['text/x-fortran']
    version_added = '0.10'
    flags = re.IGNORECASE | re.MULTILINE

    # Data Types: INTEGER, REAL, COMPLEX, LOGICAL, CHARACTER and DOUBLE PRECISION
    # Operators: **, *, +, -, /, <, >, <=, >=, ==, /=
    # Logical (?): NOT, AND, OR, EQV, NEQV

    # Builtins:
    # http://gcc.gnu.org/onlinedocs/gcc-3.4.6/g77/Table-of-Intrinsic-Functions.html

    tokens = {
        'root': [
            (r'^#.*\n', Comment.Preproc),
            (r'!.*\n', Comment),
            include('strings'),
            include('core'),
            (r'[a-z][\w$]*', Name),
            include('nums'),
            (r'[\s]+', Text.Whitespace),
        ],
        'core': [
            # Statements

            (r'\b(DO)(\s+)(CONCURRENT)\b', bygroups(Keyword, Text.Whitespace, Keyword)),
            (r'\b(GO)(\s*)(TO)\b', bygroups(Keyword, Text.Whitespace, Keyword)),

            (words((
                'ABSTRACT', 'ACCEPT', 'ALL', 'ALLSTOP', 'ALLOCATABLE', 'ALLOCATE',
                'ARRAY', 'ASSIGN', 'ASSOCIATE', 'ASYNCHRONOUS', 'BACKSPACE', 'BIND',
                'BLOCK', 'BLOCKDATA', 'BYTE', 'CALL', 'CASE', 'CLASS', 'CLOSE',
                'CODIMENSION', 'COMMON', 'CONTIGUOUS', 'CONTAINS',
                'CONTINUE', 'CRITICAL', 'CYCLE', 'DATA', 'DEALLOCATE', 'DECODE',
                'DEFERRED', 'DIMENSION', 'DO', 'ELEMENTAL', 'ELSE', 'ELSEIF', 'ENCODE',
                'END', 'ENDASSOCIATE', 'ENDBLOCK', 'ENDDO', 'ENDENUM', 'ENDFORALL',
                'ENDFUNCTION',  'ENDIF', 'ENDINTERFACE', 'ENDMODULE', 'ENDPROGRAM',
                'ENDSELECT', 'ENDSUBMODULE', 'ENDSUBROUTINE', 'ENDTYPE', 'ENDWHERE',
                'ENTRY', 'ENUM', 'ENUMERATOR', 'EQUIVALENCE', 'ERROR STOP', 'EXIT',
                'EXTENDS', 'EXTERNAL', 'EXTRINSIC', 'FILE', 'FINAL', 'FORALL', 'FORMAT',
                'FUNCTION', 'GENERIC', 'IF', 'IMAGES', 'IMPLICIT',
                'IMPORT', 'IMPURE', 'INCLUDE', 'INQUIRE', 'INTENT', 'INTERFACE',
                'INTRINSIC', 'IS', 'LOCK', 'MEMORY', 'MODULE', 'NAMELIST', 'NULLIFY',
                'NONE', 'NON_INTRINSIC', 'NON_OVERRIDABLE', 'NOPASS', 'ONLY', 'OPEN',
                'OPTIONAL', 'OPTIONS', 'PARAMETER', 'PASS', 'PAUSE', 'POINTER', 'PRINT',
                'PRIVATE', 'PROGRAM', 'PROCEDURE', 'PROTECTED', 'PUBLIC', 'PURE', 'READ',
                'RECURSIVE', 'RESULT', 'RETURN', 'REWIND', 'SAVE', 'SELECT', 'SEQUENCE',
                'STOP', 'SUBMODULE', 'SUBROUTINE', 'SYNC', 'SYNCALL', 'SYNCIMAGES',
                'SYNCMEMORY', 'TARGET', 'THEN', 'TYPE', 'UNLOCK', 'USE', 'VALUE',
                'VOLATILE', 'WHERE', 'WRITE', 'WHILE'), prefix=r'\b', suffix=r'\s*\b'),
             Keyword),

            # Data Types
            (words((
                'CHARACTER', 'COMPLEX', 'DOUBLE PRECISION', 'DOUBLE COMPLEX', 'INTEGER',
                'LOGICAL', 'REAL', 'C_INT', 'C_SHORT', 'C_LONG', 'C_LONG_LONG',
                'C_SIGNED_CHAR', 'C_SIZE_T', 'C_INT8_T', 'C_INT16_T', 'C_INT32_T',
                'C_INT64_T', 'C_INT_LEAST8_T', 'C_INT_LEAST16_T', 'C_INT_LEAST32_T',
                'C_INT_LEAST64_T', 'C_INT_FAST8_T', 'C_INT_FAST16_T', 'C_INT_FAST32_T',
                'C_INT_FAST64_T', 'C_INTMAX_T', 'C_INTPTR_T', 'C_FLOAT', 'C_DOUBLE',
                'C_LONG_DOUBLE', 'C_FLOAT_COMPLEX', 'C_DOUBLE_COMPLEX',
                'C_LONG_DOUBLE_COMPLEX', 'C_BOOL', 'C_CHAR', 'C_PTR', 'C_FUNPTR'),
                   prefix=r'\b', suffix=r'\s*\b'),
             Keyword.Type),

            # Operators
            (r'(\*\*|\*|\+|-|\/|<|>|<=|>=|==|\/=|=)', Operator),

            (r'(::)', Keyword.Declaration),

            (r'[()\[\],:&%;.]', Punctuation),
            # Intrinsics
            (words((
                'Abort', 'Abs', 'Access', 'AChar', 'ACos', 'ACosH', 'AdjustL',
                'AdjustR', 'AImag', 'AInt', 'Alarm', 'All', 'Allocated', 'ALog',
                'AMax', 'AMin', 'AMod', 'And', 'ANInt', 'Any', 'ASin', 'ASinH',
                'Associated', 'ATan', 'ATanH', 'Atomic_Define', 'Atomic_Ref',
                'BesJ', 'BesJN', 'Bessel_J0', 'Bessel_J1', 'Bessel_JN', 'Bessel_Y0',
                'Bessel_Y1', 'Bessel_YN', 'BesY', 'BesYN', 'BGE', 'BGT', 'BLE',
                'BLT', 'Bit_Size', 'BTest', 'CAbs', 'CCos', 'Ceiling', 'CExp',
                'Char', 'ChDir', 'ChMod', 'CLog', 'Cmplx', 'Command_Argument_Count',
                'Complex', 'Conjg', 'Cos', 'CosH', 'Count', 'CPU_Time', 'CShift',
                'CSin', 'CSqRt', 'CTime', 'C_Loc', 'C_Associated',
                'C_Null_Ptr', 'C_Null_Funptr', 'C_F_Pointer', 'C_F_ProcPointer',
                'C_Null_Char', 'C_Alert', 'C_Backspace', 'C_Form_Feed', 'C_FunLoc',
                'C_Sizeof', 'C_New_Line', 'C_Carriage_Return',
                'C_Horizontal_Tab', 'C_Vertical_Tab', 'DAbs', 'DACos', 'DASin',
                'DATan', 'Date_and_Time', 'DbesJ', 'DbesJN', 'DbesY',
                'DbesYN', 'Dble', 'DCos', 'DCosH', 'DDiM', 'DErF',
                'DErFC', 'DExp', 'Digits', 'DiM', 'DInt', 'DLog', 'DMax',
                'DMin', 'DMod', 'DNInt', 'Dot_Product', 'DProd', 'DSign', 'DSinH',
                'DShiftL', 'DShiftR', 'DSin', 'DSqRt', 'DTanH', 'DTan', 'DTime',
                'EOShift', 'Epsilon', 'ErF', 'ErFC', 'ErFC_Scaled', 'ETime',
                'Execute_Command_Line', 'Exit', 'Exp', 'Exponent', 'Extends_Type_Of',
                'FDate', 'FGet', 'FGetC', 'FindLoc', 'Float', 'Floor', 'Flush',
                'FNum', 'FPutC', 'FPut', 'Fraction', 'FSeek', 'FStat', 'FTell',
                'Gamma', 'GError', 'GetArg', 'Get_Command', 'Get_Command_Argument',
                'Get_Environment_Variable', 'GetCWD', 'GetEnv', 'GetGId', 'GetLog',
                'GetPId', 'GetUId', 'GMTime', 'HostNm', 'Huge', 'Hypot', 'IAbs',
                'IAChar', 'IAll', 'IAnd', 'IAny', 'IArgC', 'IBClr', 'IBits',
                'IBSet', 'IChar', 'IDate', 'IDiM', 'IDInt', 'IDNInt', 'IEOr',
                'IErrNo', 'IFix', 'Imag', 'ImagPart', 'Image_Index', 'Index',
                'Int', 'IOr', 'IParity', 'IRand', 'IsaTty', 'IShft', 'IShftC',
                'ISign', 'Iso_C_Binding', 'Is_Contiguous', 'Is_Iostat_End',
                'Is_Iostat_Eor', 'ITime', 'Kill', 'Kind', 'LBound', 'LCoBound',
                'Len', 'Len_Trim', 'LGe', 'LGt', 'Link', 'LLe', 'LLt', 'LnBlnk',
                'Loc', 'Log', 'Log_Gamma', 'Logical', 'Long', 'LShift', 'LStat',
                'LTime', 'MaskL', 'MaskR', 'MatMul', 'Max', 'MaxExponent',
                'MaxLoc', 'MaxVal', 'MClock', 'Merge', 'Merge_Bits', 'Move_Alloc',
                'Min', 'MinExponent', 'MinLoc', 'MinVal', 'Mod', 'Modulo', 'MvBits',
                'Nearest', 'New_Line', 'NInt', 'Norm2', 'Not', 'Null', 'Num_Images',
                'Or', 'Pack', 'Parity', 'PError', 'Precision', 'Present', 'Product',
                'Radix', 'Rand', 'Random_Number', 'Random_Seed', 'Range', 'Real',
                'RealPart', 'Rename', 'Repeat', 'Reshape', 'RRSpacing', 'RShift',
                'Same_Type_As', 'Scale', 'Scan', 'Second', 'Selected_Char_Kind',
                'Selected_Int_Kind', 'Selected_Real_Kind', 'Set_Exponent', 'Shape',
                'ShiftA', 'ShiftL', 'ShiftR', 'Short', 'Sign', 'Signal', 'SinH',
                'Sin', 'Sleep', 'Sngl', 'Spacing', 'Spread', 'SqRt', 'SRand',
                'Stat', 'Storage_Size', 'Sum', 'SymLnk', 'System', 'System_Clock',
                'Tan', 'TanH', 'Time', 'This_Image', 'Tiny', 'TrailZ', 'Transfer',
                'Transpose', 'Trim', 'TtyNam', 'UBound', 'UCoBound', 'UMask',
                'Unlink', 'Unpack', 'Verify', 'XOr', 'ZAbs', 'ZCos', 'ZExp',
                'ZLog', 'ZSin', 'ZSqRt'), prefix=r'\b', suffix=r'\s*\b'),
             Name.Builtin),

            # Booleans
            (r'\.(true|false)\.', Name.Builtin),
            # Comparing Operators
            (r'\.(eq|ne|lt|le|gt|ge|not|and|or|eqv|neqv)\.', Operator.Word),
        ],

        'strings': [
            (r'"(\\[0-7]+|\\[^0-7]|[^"\\])*"', String.Double),
            (r"'(\\[0-7]+|\\[^0-7]|[^'\\])*'", String.Single),
        ],

        'nums': [
            (r'\d+(?![.e])(_([1-9]|[a-z]\w*))?', Number.Integer),
            (r'[+-]?\d*\.\d+([ed][-+]?\d+)?(_([1-9]|[a-z]\w*))?', Number.Float),
            (r'[+-]?\d+\.\d*([ed][-+]?\d+)?(_([1-9]|[a-z]\w*))?', Number.Float),
            (r'[+-]?\d+(\.\d*)?[ed][-+]?\d+(_([1-9]|[a-z]\w*))?', Number.Float),
        ],
    }


class FortranFixedLexer(RegexLexer):
    """
    Lexer for fixed format Fortran.
    """
    name = 'FortranFixed'
    aliases = ['fortranfixed']
    filenames = ['*.f', '*.F']
    url = 'https://fortran-lang.org/'
    version_added = '2.1'

    flags = re.IGNORECASE

    def _lex_fortran(self, match, ctx=None):
        """Lex a line just as free form fortran without line break."""
        lexer = FortranLexer()
        text = match.group(0) + "\n"
        for index, token, value in lexer.get_tokens_unprocessed(text):
            value = value.replace('\n', '')
            if value != '':
                yield index, token, value

    tokens = {
        'root': [
            (r'[C*].*\n', Comment),
            (r'#.*\n', Comment.Preproc),
            (r' {0,4}!.*\n', Comment),
            (r'(.{5})', Name.Label, 'cont-char'),
            (r'.*\n', using(FortranLexer)),
        ],
        'cont-char': [
            (' ', Text, 'code'),
            ('0', Comment, 'code'),
            ('.', Generic.Strong, 'code'),
        ],
        'code': [
            (r'(.{66})(.*)(\n)',
             bygroups(_lex_fortran, Comment, Text.Whitespace), 'root'),
            (r'(.*)(\n)', bygroups(_lex_fortran, Text.Whitespace), 'root'),
            default('root'),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\make.py ===
"""
    pygments.lexers.make
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Makefiles and similar.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, include, bygroups, \
    do_insertions, using
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Punctuation, Whitespace
from pygments.lexers.shell import BashLexer

__all__ = ['MakefileLexer', 'BaseMakefileLexer', 'CMakeLexer']


class MakefileLexer(Lexer):
    """
    Lexer for BSD and GNU make extensions (lenient enough to handle both in
    the same file even).

    *Rewritten in Pygments 0.10.*
    """

    name = 'Makefile'
    aliases = ['make', 'makefile', 'mf', 'bsdmake']
    filenames = ['*.mak', '*.mk', 'Makefile', 'makefile', 'Makefile.*', 'GNUmakefile']
    mimetypes = ['text/x-makefile']
    url = 'https://en.wikipedia.org/wiki/Make_(software)'
    version_added = ''

    r_special = re.compile(
        r'^(?:'
        # BSD Make
        r'\.\s*(include|undef|error|warning|if|else|elif|endif|for|endfor)|'
        # GNU Make
        r'\s*(ifeq|ifneq|ifdef|ifndef|else|endif|-?include|define|endef|:|vpath)|'
        # GNU Automake
        r'\s*(if|else|endif))(?=\s)')
    r_comment = re.compile(r'^\s*@?#')

    def get_tokens_unprocessed(self, text):
        ins = []
        lines = text.splitlines(keepends=True)
        done = ''
        lex = BaseMakefileLexer(**self.options)
        backslashflag = False
        for line in lines:
            if self.r_special.match(line) or backslashflag:
                ins.append((len(done), [(0, Comment.Preproc, line)]))
                backslashflag = line.strip().endswith('\\')
            elif self.r_comment.match(line):
                ins.append((len(done), [(0, Comment, line)]))
            else:
                done += line
        yield from do_insertions(ins, lex.get_tokens_unprocessed(done))

    def analyse_text(text):
        # Many makefiles have $(BIG_CAPS) style variables
        if re.search(r'\$\([A-Z_]+\)', text):
            return 0.1


class BaseMakefileLexer(RegexLexer):
    """
    Lexer for simple Makefiles (no preprocessing).
    """

    name = 'Base Makefile'
    aliases = ['basemake']
    filenames = []
    mimetypes = []
    url = 'https://en.wikipedia.org/wiki/Make_(software)'
    version_added = '0.10'

    tokens = {
        'root': [
            # recipes (need to allow spaces because of expandtabs)
            (r'^(?:[\t ]+.*\n|\n)+', using(BashLexer)),
            # special variables
            (r'\$[<@$+%?|*]', Keyword),
            (r'\s+', Whitespace),
            (r'#.*?\n', Comment),
            (r'((?:un)?export)(\s+)(?=[\w${}\t -]+\n)',
             bygroups(Keyword, Whitespace), 'export'),
            (r'(?:un)?export\s+', Keyword),
            # assignment
            (r'([\w${}().-]+)(\s*)([!?:+]?=)([ \t]*)((?:.*\\\n)+|.*\n)',
             bygroups(
                Name.Variable, Whitespace, Operator, Whitespace,
                using(BashLexer))),
            # strings
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            # targets
            (r'([^\n:]+)(:+)([ \t]*)', bygroups(
                Name.Function, Operator, Whitespace),
             'block-header'),
            # expansions
            (r'\$\(', Keyword, 'expansion'),
        ],
        'expansion': [
            (r'[^\w$().-]+', Text),
            (r'[\w.-]+', Name.Variable),
            (r'\$', Keyword),
            (r'\(', Keyword, '#push'),
            (r'\)', Keyword, '#pop'),
        ],
        'export': [
            (r'[\w${}-]+', Name.Variable),
            (r'\n', Text, '#pop'),
            (r'\s+', Whitespace),
        ],
        'block-header': [
            (r'[,|]', Punctuation),
            (r'#.*?\n', Comment, '#pop'),
            (r'\\\n', Text),  # line continuation
            (r'\$\(', Keyword, 'expansion'),
            (r'[a-zA-Z_]+', Name),
            (r'\n', Whitespace, '#pop'),
            (r'.', Text),
        ],
    }


class CMakeLexer(RegexLexer):
    """
    Lexer for CMake files.
    """
    name = 'CMake'
    url = 'https://cmake.org/documentation/'
    aliases = ['cmake']
    filenames = ['*.cmake', 'CMakeLists.txt']
    mimetypes = ['text/x-cmake']
    version_added = '1.2'

    tokens = {
        'root': [
            # (r'(ADD_CUSTOM_COMMAND|ADD_CUSTOM_TARGET|ADD_DEFINITIONS|'
            # r'ADD_DEPENDENCIES|ADD_EXECUTABLE|ADD_LIBRARY|ADD_SUBDIRECTORY|'
            # r'ADD_TEST|AUX_SOURCE_DIRECTORY|BUILD_COMMAND|BUILD_NAME|'
            # r'CMAKE_MINIMUM_REQUIRED|CONFIGURE_FILE|CREATE_TEST_SOURCELIST|'
            # r'ELSE|ELSEIF|ENABLE_LANGUAGE|ENABLE_TESTING|ENDFOREACH|'
            # r'ENDFUNCTION|ENDIF|ENDMACRO|ENDWHILE|EXEC_PROGRAM|'
            # r'EXECUTE_PROCESS|EXPORT_LIBRARY_DEPENDENCIES|FILE|FIND_FILE|'
            # r'FIND_LIBRARY|FIND_PACKAGE|FIND_PATH|FIND_PROGRAM|FLTK_WRAP_UI|'
            # r'FOREACH|FUNCTION|GET_CMAKE_PROPERTY|GET_DIRECTORY_PROPERTY|'
            # r'GET_FILENAME_COMPONENT|GET_SOURCE_FILE_PROPERTY|'
            # r'GET_TARGET_PROPERTY|GET_TEST_PROPERTY|IF|INCLUDE|'
            # r'INCLUDE_DIRECTORIES|INCLUDE_EXTERNAL_MSPROJECT|'
            # r'INCLUDE_REGULAR_EXPRESSION|INSTALL|INSTALL_FILES|'
            # r'INSTALL_PROGRAMS|INSTALL_TARGETS|LINK_DIRECTORIES|'
            # r'LINK_LIBRARIES|LIST|LOAD_CACHE|LOAD_COMMAND|MACRO|'
            # r'MAKE_DIRECTORY|MARK_AS_ADVANCED|MATH|MESSAGE|OPTION|'
            # r'OUTPUT_REQUIRED_FILES|PROJECT|QT_WRAP_CPP|QT_WRAP_UI|REMOVE|'
            # r'REMOVE_DEFINITIONS|SEPARATE_ARGUMENTS|SET|'
            # r'SET_DIRECTORY_PROPERTIES|SET_SOURCE_FILES_PROPERTIES|'
            # r'SET_TARGET_PROPERTIES|SET_TESTS_PROPERTIES|SITE_NAME|'
            # r'SOURCE_GROUP|STRING|SUBDIR_DEPENDS|SUBDIRS|'
            # r'TARGET_LINK_LIBRARIES|TRY_COMPILE|TRY_RUN|UNSET|'
            # r'USE_MANGLED_MESA|UTILITY_SOURCE|VARIABLE_REQUIRES|'
            # r'VTK_MAKE_INSTANTIATOR|VTK_WRAP_JAVA|VTK_WRAP_PYTHON|'
            # r'VTK_WRAP_TCL|WHILE|WRITE_FILE|'
            # r'COUNTARGS)\b', Name.Builtin, 'args'),
            (r'\b(\w+)([ \t]*)(\()', bygroups(Name.Builtin, Whitespace,
                                              Punctuation), 'args'),
            include('keywords'),
            include('ws')
        ],
        'args': [
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
            (r'(\$\{)(.+?)(\})', bygroups(Operator, Name.Variable, Operator)),
            (r'(\$ENV\{)(.+?)(\})', bygroups(Operator, Name.Variable, Operator)),
            (r'(\$<)(.+?)(>)', bygroups(Operator, Name.Variable, Operator)),
            (r'(?s)".*?"', String.Double),
            (r'\\\S+', String),
            (r'\[(?P<level>=*)\[[\w\W]*?\](?P=level)\]', String.Multiline),
            (r'[^)$"# \t\n]+', String),
            (r'\n', Whitespace),  # explicitly legal
            include('keywords'),
            include('ws')
        ],
        'string': [

        ],
        'keywords': [
            (r'\b(WIN32|UNIX|APPLE|CYGWIN|BORLAND|MINGW|MSVC|MSVC_IDE|MSVC60|'
             r'MSVC70|MSVC71|MSVC80|MSVC90)\b', Keyword),
        ],
        'ws': [
            (r'[ \t]+', Whitespace),
            (r'#\[(?P<level>=*)\[[\w\W]*?\](?P=level)\]', Comment),
            (r'#.*\n', Comment),
        ]
    }

    def analyse_text(text):
        exp = (
            r'^[ \t]*CMAKE_MINIMUM_REQUIRED[ \t]*'
            r'\([ \t]*VERSION[ \t]*\d+(\.\d+)*[ \t]*'
            r'([ \t]FATAL_ERROR)?[ \t]*\)[ \t]*'
            r'(#[^\n]*)?$'
        )
        if re.search(exp, text, flags=re.MULTILINE | re.IGNORECASE):
            return 0.8
        return 0.0

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\expressions.py ===
import io
import sys
import traceback
from pprint import pprint

import winerror

from . import axdebug, gateways
from .util import RaiseNotImpl, _wrap


# Given an object, return a nice string
def MakeNiceString(ob):
    stream = io.StringIO()
    pprint(ob, stream)
    return stream.getvalue().strip()


class ProvideExpressionContexts(gateways.ProvideExpressionContexts):
    pass


class ExpressionContext(gateways.DebugExpressionContext):
    def __init__(self, frame):
        self.frame = frame

    def ParseLanguageText(self, code, radix, delim, flags):
        return _wrap(
            Expression(self.frame, code, radix, delim, flags),
            axdebug.IID_IDebugExpression,
        )

    def GetLanguageInfo(self):
        # print("GetLanguageInfo")
        return "Python", "{DF630910-1C1D-11d0-AE36-8C0F5E000000}"


class Expression(gateways.DebugExpression):
    def __init__(self, frame, code, radix, delim, flags):
        self.callback = None
        self.frame = frame
        self.code = code
        self.radix = radix
        self.delim = delim
        self.flags = flags
        self.isComplete = 0
        self.result = None
        self.hresult = winerror.E_UNEXPECTED

    def Start(self, callback):
        try:
            try:
                try:
                    self.result = eval(
                        self.code, self.frame.f_globals, self.frame.f_locals
                    )
                except SyntaxError:
                    exec(self.code, self.frame.f_globals, self.frame.f_locals)
                    self.result = ""
                self.hresult = 0
            except:
                l = traceback.format_exception_only(
                    sys.exc_info()[0], sys.exc_info()[1]
                )
                # l is a list of strings with trailing "\n"
                self.result = "\n".join(s[:-1] for s in l)
                self.hresult = winerror.E_FAIL
        finally:
            self.isComplete = 1
            callback.onComplete()

    def Abort(self):
        print("** ABORT **")

    def QueryIsComplete(self):
        return self.isComplete

    def GetResultAsString(self):
        # print("GetStrAsResult returning", self.result)
        return self.hresult, MakeNiceString(self.result)

    def GetResultAsDebugProperty(self):
        result = _wrap(
            DebugProperty(self.code, self.result, None, self.hresult),
            axdebug.IID_IDebugProperty,
        )
        return self.hresult, result


def MakeEnumDebugProperty(object, dwFieldSpec, nRadix, iid, stackFrame=None):
    name_vals = []
    if hasattr(object, "items") and hasattr(object, "keys"):  # If it is a dict.
        name_vals = object.items()
        dictionary = object
    elif hasattr(object, "__dict__"):  # object with dictionary, module
        name_vals = object.__dict__.items()
        dictionary = object.__dict__
    infos = []
    for name, val in name_vals:
        infos.append(
            GetPropertyInfo(name, val, dwFieldSpec, nRadix, 0, dictionary, stackFrame)
        )
    return _wrap(EnumDebugPropertyInfo(infos), axdebug.IID_IEnumDebugPropertyInfo)


def GetPropertyInfo(
    obname, obvalue, dwFieldSpec, nRadix, hresult=0, dictionary=None, stackFrame=None
):
    # returns a tuple
    name = typ = value = fullname = attrib = dbgprop = None
    if dwFieldSpec & axdebug.DBGPROP_INFO_VALUE:
        value = MakeNiceString(obvalue)
    if dwFieldSpec & axdebug.DBGPROP_INFO_NAME:
        name = obname
    if dwFieldSpec & axdebug.DBGPROP_INFO_TYPE:
        if hresult:
            typ = "Error"
        else:
            try:
                typ = type(obvalue).__name__
            except AttributeError:
                typ = str(type(obvalue))
    if dwFieldSpec & axdebug.DBGPROP_INFO_FULLNAME:
        fullname = obname
    if dwFieldSpec & axdebug.DBGPROP_INFO_ATTRIBUTES:
        if hasattr(obvalue, "has_key") or hasattr(
            obvalue, "__dict__"
        ):  # If it is a dict or object
            attrib = axdebug.DBGPROP_ATTRIB_VALUE_IS_EXPANDABLE
        else:
            attrib = 0
    if dwFieldSpec & axdebug.DBGPROP_INFO_DEBUGPROP:
        dbgprop = _wrap(
            DebugProperty(name, obvalue, None, hresult, dictionary, stackFrame),
            axdebug.IID_IDebugProperty,
        )
    return name, typ, value, fullname, attrib, dbgprop


from win32com.server.util import ListEnumeratorGateway


class EnumDebugPropertyInfo(ListEnumeratorGateway):
    """A class to expose a Python sequence as an EnumDebugCodeContexts

    Create an instance of this class passing a sequence (list, tuple, or
    any sequence protocol supporting object) and it will automatically
    support the EnumDebugCodeContexts interface for the object.

    """

    _public_methods_ = ListEnumeratorGateway._public_methods_ + ["GetCount"]
    _com_interfaces_ = [axdebug.IID_IEnumDebugPropertyInfo]

    def GetCount(self):
        return len(self._list_)

    def _wrap(self, ob):
        return ob


class DebugProperty:
    _com_interfaces_ = [axdebug.IID_IDebugProperty]
    _public_methods_ = [
        "GetPropertyInfo",
        "GetExtendedInfo",
        "SetValueAsString",
        "EnumMembers",
        "GetParent",
    ]

    def __init__(
        self, name, value, parent=None, hresult=0, dictionary=None, stackFrame=None
    ):
        self.name = name
        self.value = value
        self.parent = parent
        self.hresult = hresult
        self.dictionary = dictionary
        self.stackFrame = stackFrame

    def GetPropertyInfo(self, dwFieldSpec, nRadix):
        return GetPropertyInfo(
            self.name,
            self.value,
            dwFieldSpec,
            nRadix,
            self.hresult,
            self.dictionary,
            self.stackFrame,
        )

    def GetExtendedInfo(self):  ### Note - not in the framework.
        RaiseNotImpl("DebugProperty::GetExtendedInfo")

    def SetValueAsString(self, value, radix):
        if self.stackFrame and self.dictionary:
            self.dictionary[self.name] = eval(
                value, self.stackFrame.f_globals, self.stackFrame.f_locals
            )
        else:
            RaiseNotImpl("DebugProperty::SetValueAsString")

    def EnumMembers(self, dwFieldSpec, nRadix, iid):
        # Returns IEnumDebugPropertyInfo
        return MakeEnumDebugProperty(
            self.value, dwFieldSpec, nRadix, iid, self.stackFrame
        )

    def GetParent(self):
        # return IDebugProperty
        RaiseNotImpl("DebugProperty::GetParent")

# === NexusCore/openenv\Lib\site-packages\zmq\eventloop\_deprecated.py ===
"""tornado IOLoop API with zmq compatibility

If you have tornado ≥ 3.0, this is a subclass of tornado's IOLoop,
otherwise we ship a minimal subset of tornado in zmq.eventloop.minitornado.

The minimal shipped version of tornado's IOLoop does not include
support for concurrent futures - this will only be available if you
have tornado ≥ 3.0.
"""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import time
import warnings
from typing import Tuple

from zmq import ETERM, POLLERR, POLLIN, POLLOUT, Poller, ZMQError

tornado_version: Tuple = ()
try:
    import tornado

    tornado_version = tornado.version_info
except (ImportError, AttributeError):
    pass

from .minitornado.ioloop import PeriodicCallback, PollIOLoop
from .minitornado.log import gen_log


class DelayedCallback(PeriodicCallback):
    """Schedules the given callback to be called once.

    The callback is called once, after callback_time milliseconds.

    `start` must be called after the DelayedCallback is created.

    The timeout is calculated from when `start` is called.
    """

    def __init__(self, callback, callback_time, io_loop=None):
        # PeriodicCallback require callback_time to be positive
        warnings.warn(
            """DelayedCallback is deprecated.
        Use loop.add_timeout instead.""",
            DeprecationWarning,
        )
        callback_time = max(callback_time, 1e-3)
        super().__init__(callback, callback_time, io_loop)

    def start(self):
        """Starts the timer."""
        self._running = True
        self._firstrun = True
        self._next_timeout = time.time() + self.callback_time / 1000.0
        self.io_loop.add_timeout(self._next_timeout, self._run)

    def _run(self):
        if not self._running:
            return
        self._running = False
        try:
            self.callback()
        except Exception:
            gen_log.error("Error in delayed callback", exc_info=True)


class ZMQPoller:
    """A poller that can be used in the tornado IOLoop.

    This simply wraps a regular zmq.Poller, scaling the timeout
    by 1000, so that it is in seconds rather than milliseconds.
    """

    def __init__(self):
        self._poller = Poller()

    @staticmethod
    def _map_events(events):
        """translate IOLoop.READ/WRITE/ERROR event masks into zmq.POLLIN/OUT/ERR"""
        z_events = 0
        if events & IOLoop.READ:
            z_events |= POLLIN
        if events & IOLoop.WRITE:
            z_events |= POLLOUT
        if events & IOLoop.ERROR:
            z_events |= POLLERR
        return z_events

    @staticmethod
    def _remap_events(z_events):
        """translate zmq.POLLIN/OUT/ERR event masks into IOLoop.READ/WRITE/ERROR"""
        events = 0
        if z_events & POLLIN:
            events |= IOLoop.READ
        if z_events & POLLOUT:
            events |= IOLoop.WRITE
        if z_events & POLLERR:
            events |= IOLoop.ERROR
        return events

    def register(self, fd, events):
        return self._poller.register(fd, self._map_events(events))

    def modify(self, fd, events):
        return self._poller.modify(fd, self._map_events(events))

    def unregister(self, fd):
        return self._poller.unregister(fd)

    def poll(self, timeout):
        """poll in seconds rather than milliseconds.

        Event masks will be IOLoop.READ/WRITE/ERROR
        """
        z_events = self._poller.poll(1000 * timeout)
        return [(fd, self._remap_events(evt)) for (fd, evt) in z_events]

    def close(self):
        pass


class ZMQIOLoop(PollIOLoop):
    """ZMQ subclass of tornado's IOLoop

    Minor modifications, so that .current/.instance return self
    """

    _zmq_impl = ZMQPoller

    def initialize(self, impl=None, **kwargs):
        impl = self._zmq_impl() if impl is None else impl
        super().initialize(impl=impl, **kwargs)

    @classmethod
    def instance(cls, *args, **kwargs):
        """Returns a global `IOLoop` instance.

        Most applications have a single, global `IOLoop` running on the
        main thread.  Use this method to get this instance from
        another thread.  To get the current thread's `IOLoop`, use `current()`.
        """
        # install ZMQIOLoop as the active IOLoop implementation
        # when using tornado 3
        if tornado_version >= (3,):
            PollIOLoop.configure(cls)
        loop = PollIOLoop.instance(*args, **kwargs)
        if not isinstance(loop, cls):
            warnings.warn(
                f"IOLoop.current expected instance of {cls!r}, got {loop!r}",
                RuntimeWarning,
                stacklevel=2,
            )
        return loop

    @classmethod
    def current(cls, *args, **kwargs):
        """Returns the current thread’s IOLoop."""
        # install ZMQIOLoop as the active IOLoop implementation
        # when using tornado 3
        if tornado_version >= (3,):
            PollIOLoop.configure(cls)
        loop = PollIOLoop.current(*args, **kwargs)
        if not isinstance(loop, cls):
            warnings.warn(
                f"IOLoop.current expected instance of {cls!r}, got {loop!r}",
                RuntimeWarning,
                stacklevel=2,
            )
        return loop

    def start(self):
        try:
            super().start()
        except ZMQError as e:
            if e.errno == ETERM:
                # quietly return on ETERM
                pass
            else:
                raise


# public API name
IOLoop = ZMQIOLoop


def install():
    """set the tornado IOLoop instance with the pyzmq IOLoop.

    After calling this function, tornado's IOLoop.instance() and pyzmq's
    IOLoop.instance() will return the same object.

    An assertion error will be raised if tornado's IOLoop has been initialized
    prior to calling this function.
    """
    from tornado import ioloop

    # check if tornado's IOLoop is already initialized to something other
    # than the pyzmq IOLoop instance:
    assert (
        not ioloop.IOLoop.initialized()
    ) or ioloop.IOLoop.instance() is IOLoop.instance(), (
        "tornado IOLoop already initialized"
    )

    if tornado_version >= (3,):
        # tornado 3 has an official API for registering new defaults, yay!
        ioloop.IOLoop.configure(ZMQIOLoop)
    else:
        # we have to set the global instance explicitly
        ioloop.IOLoop._instance = IOLoop.instance()

# === NexusCore/openenv\Lib\site-packages\urllib3\__init__.py ===
"""
Python HTTP library with thread-safe connection pooling, file post support, user friendly, and more
"""

from __future__ import annotations

# Set default logging handler to avoid "No handler found" warnings.
import logging
import sys
import typing
import warnings
from logging import NullHandler

from . import exceptions
from ._base_connection import _TYPE_BODY
from ._collections import HTTPHeaderDict
from ._version import __version__
from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool, connection_from_url
from .filepost import _TYPE_FIELDS, encode_multipart_formdata
from .poolmanager import PoolManager, ProxyManager, proxy_from_url
from .response import BaseHTTPResponse, HTTPResponse
from .util.request import make_headers
from .util.retry import Retry
from .util.timeout import Timeout

# Ensure that Python is compiled with OpenSSL 1.1.1+
# If the 'ssl' module isn't available at all that's
# fine, we only care if the module is available.
try:
    import ssl
except ImportError:
    pass
else:
    if not ssl.OPENSSL_VERSION.startswith("OpenSSL "):  # Defensive:
        warnings.warn(
            "urllib3 v2 only supports OpenSSL 1.1.1+, currently "
            f"the 'ssl' module is compiled with {ssl.OPENSSL_VERSION!r}. "
            "See: https://github.com/urllib3/urllib3/issues/3020",
            exceptions.NotOpenSSLWarning,
        )
    elif ssl.OPENSSL_VERSION_INFO < (1, 1, 1):  # Defensive:
        raise ImportError(
            "urllib3 v2 only supports OpenSSL 1.1.1+, currently "
            f"the 'ssl' module is compiled with {ssl.OPENSSL_VERSION!r}. "
            "See: https://github.com/urllib3/urllib3/issues/2168"
        )

__author__ = "Andrey Petrov (andrey.petrov@shazow.net)"
__license__ = "MIT"
__version__ = __version__

__all__ = (
    "HTTPConnectionPool",
    "HTTPHeaderDict",
    "HTTPSConnectionPool",
    "PoolManager",
    "ProxyManager",
    "HTTPResponse",
    "Retry",
    "Timeout",
    "add_stderr_logger",
    "connection_from_url",
    "disable_warnings",
    "encode_multipart_formdata",
    "make_headers",
    "proxy_from_url",
    "request",
    "BaseHTTPResponse",
)

logging.getLogger(__name__).addHandler(NullHandler())


def add_stderr_logger(
    level: int = logging.DEBUG,
) -> logging.StreamHandler[typing.TextIO]:
    """
    Helper for quickly adding a StreamHandler to the logger. Useful for
    debugging.

    Returns the handler after adding it.
    """
    # This method needs to be in this __init__.py to get the __name__ correct
    # even if urllib3 is vendored within another package.
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.debug("Added a stderr logging handler to logger: %s", __name__)
    return handler


# ... Clean up.
del NullHandler


# All warning filters *must* be appended unless you're really certain that they
# shouldn't be: otherwise, it's very hard for users to use most Python
# mechanisms to silence them.
# SecurityWarning's always go off by default.
warnings.simplefilter("always", exceptions.SecurityWarning, append=True)
# InsecurePlatformWarning's don't vary between requests, so we keep it default.
warnings.simplefilter("default", exceptions.InsecurePlatformWarning, append=True)


def disable_warnings(category: type[Warning] = exceptions.HTTPWarning) -> None:
    """
    Helper for quickly disabling all urllib3 warnings.
    """
    warnings.simplefilter("ignore", category)


_DEFAULT_POOL = PoolManager()


def request(
    method: str,
    url: str,
    *,
    body: _TYPE_BODY | None = None,
    fields: _TYPE_FIELDS | None = None,
    headers: typing.Mapping[str, str] | None = None,
    preload_content: bool | None = True,
    decode_content: bool | None = True,
    redirect: bool | None = True,
    retries: Retry | bool | int | None = None,
    timeout: Timeout | float | int | None = 3,
    json: typing.Any | None = None,
) -> BaseHTTPResponse:
    """
    A convenience, top-level request method. It uses a module-global ``PoolManager`` instance.
    Therefore, its side effects could be shared across dependencies relying on it.
    To avoid side effects create a new ``PoolManager`` instance and use it instead.
    The method does not accept low-level ``**urlopen_kw`` keyword arguments.

    :param method:
        HTTP request method (such as GET, POST, PUT, etc.)

    :param url:
        The URL to perform the request on.

    :param body:
        Data to send in the request body, either :class:`str`, :class:`bytes`,
        an iterable of :class:`str`/:class:`bytes`, or a file-like object.

    :param fields:
        Data to encode and send in the request body.

    :param headers:
        Dictionary of custom headers to send, such as User-Agent,
        If-None-Match, etc.

    :param bool preload_content:
        If True, the response's body will be preloaded into memory.

    :param bool decode_content:
        If True, will attempt to decode the body based on the
        'content-encoding' header.

    :param redirect:
        If True, automatically handle redirects (status codes 301, 302,
        303, 307, 308). Each redirect counts as a retry. Disabling retries
        will disable redirect, too.

    :param retries:
        Configure the number of retries to allow before raising a
        :class:`~urllib3.exceptions.MaxRetryError` exception.

        If ``None`` (default) will retry 3 times, see ``Retry.DEFAULT``. Pass a
        :class:`~urllib3.util.retry.Retry` object for fine-grained control
        over different types of retries.
        Pass an integer number to retry connection errors that many times,
        but no other types of errors. Pass zero to never retry.

        If ``False``, then retries are disabled and any exception is raised
        immediately. Also, instead of raising a MaxRetryError on redirects,
        the redirect response will be returned.

    :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

    :param timeout:
        If specified, overrides the default timeout for this one
        request. It may be a float (in seconds) or an instance of
        :class:`urllib3.util.Timeout`.

    :param json:
        Data to encode and send as JSON with UTF-encoded in the request body.
        The ``"Content-Type"`` header will be set to ``"application/json"``
        unless specified otherwise.
    """

    return _DEFAULT_POOL.request(
        method,
        url,
        body=body,
        fields=fields,
        headers=headers,
        preload_content=preload_content,
        decode_content=decode_content,
        redirect=redirect,
        retries=retries,
        timeout=timeout,
        json=json,
    )


if sys.platform == "emscripten":
    from .contrib.emscripten import inject_into_urllib3  # noqa: 401

    inject_into_urllib3()

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\jpl_units\Epoch.py ===
"""Epoch module."""

import functools
import operator
import math
import datetime as DT

from matplotlib import _api
from matplotlib.dates import date2num


class Epoch:
    # Frame conversion offsets in seconds
    # t(TO) = t(FROM) + allowed[ FROM ][ TO ]
    allowed = {
        "ET": {
            "UTC": +64.1839,
            },
        "UTC": {
            "ET": -64.1839,
            },
        }

    def __init__(self, frame, sec=None, jd=None, daynum=None, dt=None):
        """
        Create a new Epoch object.

        Build an epoch 1 of 2 ways:

        Using seconds past a Julian date:
        #   Epoch('ET', sec=1e8, jd=2451545)

        or using a matplotlib day number
        #   Epoch('ET', daynum=730119.5)

        = ERROR CONDITIONS
        - If the input units are not in the allowed list, an error is thrown.

        = INPUT VARIABLES
        - frame     The frame of the epoch.  Must be 'ET' or 'UTC'
        - sec        The number of seconds past the input JD.
        - jd         The Julian date of the epoch.
        - daynum    The matplotlib day number of the epoch.
        - dt         A python datetime instance.
        """
        if ((sec is None and jd is not None) or
                (sec is not None and jd is None) or
                (daynum is not None and
                 (sec is not None or jd is not None)) or
                (daynum is None and dt is None and
                 (sec is None or jd is None)) or
                (daynum is not None and dt is not None) or
                (dt is not None and (sec is not None or jd is not None)) or
                ((dt is not None) and not isinstance(dt, DT.datetime))):
            raise ValueError(
                "Invalid inputs.  Must enter sec and jd together, "
                "daynum by itself, or dt (must be a python datetime).\n"
                "Sec = %s\n"
                "JD  = %s\n"
                "dnum= %s\n"
                "dt  = %s" % (sec, jd, daynum, dt))

        _api.check_in_list(self.allowed, frame=frame)
        self._frame = frame

        if dt is not None:
            daynum = date2num(dt)

        if daynum is not None:
            # 1-JAN-0001 in JD = 1721425.5
            jd = float(daynum) + 1721425.5
            self._jd = math.floor(jd)
            self._seconds = (jd - self._jd) * 86400.0

        else:
            self._seconds = float(sec)
            self._jd = float(jd)

            # Resolve seconds down to [ 0, 86400)
            deltaDays = math.floor(self._seconds / 86400)
            self._jd += deltaDays
            self._seconds -= deltaDays * 86400.0

    def convert(self, frame):
        if self._frame == frame:
            return self

        offset = self.allowed[self._frame][frame]

        return Epoch(frame, self._seconds + offset, self._jd)

    def frame(self):
        return self._frame

    def julianDate(self, frame):
        t = self
        if frame != self._frame:
            t = self.convert(frame)

        return t._jd + t._seconds / 86400.0

    def secondsPast(self, frame, jd):
        t = self
        if frame != self._frame:
            t = self.convert(frame)

        delta = t._jd - jd
        return t._seconds + delta * 86400

    def _cmp(self, op, rhs):
        """Compare Epochs *self* and *rhs* using operator *op*."""
        t = self
        if self._frame != rhs._frame:
            t = self.convert(rhs._frame)
        if t._jd != rhs._jd:
            return op(t._jd, rhs._jd)
        return op(t._seconds, rhs._seconds)

    __eq__ = functools.partialmethod(_cmp, operator.eq)
    __ne__ = functools.partialmethod(_cmp, operator.ne)
    __lt__ = functools.partialmethod(_cmp, operator.lt)
    __le__ = functools.partialmethod(_cmp, operator.le)
    __gt__ = functools.partialmethod(_cmp, operator.gt)
    __ge__ = functools.partialmethod(_cmp, operator.ge)

    def __add__(self, rhs):
        """
        Add a duration to an Epoch.

        = INPUT VARIABLES
        - rhs     The Epoch to subtract.

        = RETURN VALUE
        - Returns the difference of ourselves and the input Epoch.
        """
        t = self
        if self._frame != rhs.frame():
            t = self.convert(rhs._frame)

        sec = t._seconds + rhs.seconds()

        return Epoch(t._frame, sec, t._jd)

    def __sub__(self, rhs):
        """
        Subtract two Epoch's or a Duration from an Epoch.

        Valid:
        Duration = Epoch - Epoch
        Epoch = Epoch - Duration

        = INPUT VARIABLES
        - rhs     The Epoch to subtract.

        = RETURN VALUE
        - Returns either the duration between to Epoch's or the a new
          Epoch that is the result of subtracting a duration from an epoch.
        """
        # Delay-load due to circular dependencies.
        import matplotlib.testing.jpl_units as U

        # Handle Epoch - Duration
        if isinstance(rhs, U.Duration):
            return self + -rhs

        t = self
        if self._frame != rhs._frame:
            t = self.convert(rhs._frame)

        days = t._jd - rhs._jd
        sec = t._seconds - rhs._seconds

        return U.Duration(rhs._frame, days*86400 + sec)

    def __str__(self):
        """Print the Epoch."""
        return f"{self.julianDate(self._frame):22.15e} {self._frame}"

    def __repr__(self):
        """Print the Epoch."""
        return str(self)

    @staticmethod
    def range(start, stop, step):
        """
        Generate a range of Epoch objects.

        Similar to the Python range() method.  Returns the range [
        start, stop) at the requested step.  Each element will be a
        Epoch object.

        = INPUT VARIABLES
        - start     The starting value of the range.
        - stop      The stop value of the range.
        - step      Step to use.

        = RETURN VALUE
        - Returns a list containing the requested Epoch values.
        """
        elems = []

        i = 0
        while True:
            d = start + i * step
            if d >= stop:
                break

            elems.append(d)
            i += 1

        return elems

# === NexusCore/openenv\Lib\site-packages\win32comext\mapi\mapiutil.py ===
# General utilities for MAPI and MAPI objects.
from __future__ import annotations

import pythoncom
from pywintypes import TimeType

from . import mapi, mapitags

prTable: dict[int, str] = {}


def GetPropTagName(pt):
    if not prTable:
        for name, value in mapitags.__dict__.items():
            if name[:3] == "PR_":
                # Store both the full ID (including type) and just the ID.
                # This is so PR_FOO_A and PR_FOO_W are still differentiated,
                # but should we get a PT_FOO with PT_ERROR set, we fallback
                # to the ID.

                # String types should have 3 definitions in mapitags.py
                # PR_BODY	= PROP_TAG( PT_TSTRING,	4096)
                # PR_BODY_W	= PROP_TAG( PT_UNICODE, 4096)
                # PR_BODY_A	= PROP_TAG( PT_STRING8, 4096)
                # The following change ensures a lookup using only the the
                # property id returns the conditional default.

                # PT_TSTRING is a conditional assignment for either PT_UNICODE or
                # PT_STRING8 and should not be returned during a lookup.

                if (
                    mapitags.PROP_TYPE(value) == mapitags.PT_UNICODE
                    or mapitags.PROP_TYPE(value) == mapitags.PT_STRING8
                ):
                    if name[-2:] == "_A" or name[-2:] == "_W":
                        prTable[value] = name
                    else:
                        prTable[mapitags.PROP_ID(value)] = name

                else:
                    prTable[value] = name
                    prTable[mapitags.PROP_ID(value)] = name

    try:
        try:
            return prTable[pt]
        except KeyError:
            # Can't find it exactly - see if the raw ID exists.
            return prTable[mapitags.PROP_ID(pt)]
    except KeyError:
        # god-damn bullshit hex() warnings: I don't see a way to get the
        # old behaviour without a warning!!
        ret = hex(int(pt))
        # -0x8000000L -> 0x80000000
        if ret[0] == "-":
            ret = ret[1:]
        if ret[-1] == "L":
            ret = ret[:-1]
        return ret


mapiErrorTable: dict[int, str] = {}


def GetScodeString(hr):
    if not mapiErrorTable:
        for name, value in mapi.__dict__.items():
            if name[:7] in ["MAPI_E_", "MAPI_W_"]:
                mapiErrorTable[value] = name
    return mapiErrorTable.get(hr, pythoncom.GetScodeString(hr))


ptTable: dict[int, str] = {}


def GetMapiTypeName(propType, rawType=True):
    """Given a mapi type flag, return a string description of the type"""
    if not ptTable:
        for name, value in mapitags.__dict__.items():
            if name[:3] == "PT_":
                # PT_TSTRING is a conditional assignment
                # for either PT_UNICODE or PT_STRING8 and
                # should not be returned during a lookup.
                if name in ["PT_TSTRING", "PT_MV_TSTRING"]:
                    continue
                ptTable[value] = name

    if rawType:
        propType &= ~mapitags.MV_FLAG
    return ptTable.get(propType, str(hex(propType)))


def GetProperties(obj, propList):
    """Given a MAPI object and a list of properties, return a list of property values.

    Allows a single property to be passed, and the result is a single object.

    Each request property can be an integer or a string.  Of a string, it is
    automatically converted to an integer via the GetIdsFromNames function.

    If the property fetch fails, the result is None.
    """
    bRetList = 1
    if not isinstance(propList, (tuple, list)):
        bRetList = 0
        propList = (propList,)
    realPropList = []
    rc = []
    for prop in propList:
        if not isinstance(prop, int):
            props = ((mapi.PS_PUBLIC_STRINGS, prop),)
            propIds = obj.GetIDsFromNames(props, 0)
            prop = mapitags.PROP_TAG(
                mapitags.PT_UNSPECIFIED, mapitags.PROP_ID(propIds[0])
            )
        realPropList.append(prop)

    hr, data = obj.GetProps(realPropList, 0)
    if hr != 0:
        data = None
        return None
    if bRetList:
        return [v[1] for v in data]
    else:
        return data[0][1]


def GetAllProperties(obj, make_tag_names=True):
    tags = obj.GetPropList(0)
    hr, data = obj.GetProps(tags)
    ret = []
    for tag, val in data:
        if make_tag_names:
            hr, tags, array = obj.GetNamesFromIDs((tag,))
            if isinstance(array[0][1], str):
                name = array[0][1]
            else:
                name = GetPropTagName(tag)
        else:
            name = tag
        ret.append((name, val))
    return ret


_MapiTypeMap = {
    float: mapitags.PT_DOUBLE,
    int: mapitags.PT_I4,
    bytes: mapitags.PT_STRING8,
    str: mapitags.PT_UNICODE,
    type(None): mapitags.PT_UNSPECIFIED,
    bool: mapitags.PT_BOOLEAN,
}


def SetPropertyValue(obj, prop, val):
    if not isinstance(prop, int):
        props = ((mapi.PS_PUBLIC_STRINGS, prop),)
        propIds = obj.GetIDsFromNames(props, mapi.MAPI_CREATE)
        if val == True or val == False:
            type_tag = mapitags.PT_BOOLEAN
        else:
            type_tag = _MapiTypeMap.get(type(val))
            if type_tag is None:
                raise ValueError(
                    f"Don't know what to do with '{val!r}' ('{type(val)}')"
                )
        prop = mapitags.PROP_TAG(type_tag, mapitags.PROP_ID(propIds[0]))
    if val is None:
        # Delete the property
        obj.DeleteProps((prop,))
    else:
        obj.SetProps(((prop, val),))


def SetProperties(msg, propDict):
    """Given a Python dictionary, set the objects properties.

    If the dictionary key is a string, then a property ID is queried
    otherwise the ID is assumed native.

    Coded for maximum efficiency wrt server calls - ie, maximum of
    2 calls made to the object, regardless of the dictionary contents
    (only 1 if dictionary full of int keys)
    """

    newProps = []
    # First pass over the properties we should get IDs for.
    for key, val in propDict.items():
        if isinstance(key, str):
            newProps.append((mapi.PS_PUBLIC_STRINGS, key))
    # Query for the new IDs
    if newProps:
        newIds = msg.GetIDsFromNames(newProps, mapi.MAPI_CREATE)
    newIdNo = 0
    newProps = []
    for key, val in propDict.items():
        if isinstance(key, str):
            if isinstance(val, str):
                tagType = mapitags.PT_UNICODE
            elif isinstance(val, int):
                tagType = mapitags.PT_I4
            elif isinstance(val, TimeType):
                tagType = mapitags.PT_SYSTIME
            else:
                raise ValueError(
                    f"The type of object {val!r}({type(val)}) can not be written"
                )
            key = mapitags.PROP_TAG(tagType, mapitags.PROP_ID(newIds[newIdNo]))
            newIdNo += 1
        newProps.append((key, val))
    msg.SetProps(newProps)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\network\lazy_wheel.py ===
"""Lazy ZIP over HTTP"""

__all__ = ["HTTPRangeRequestUnsupported", "dist_from_wheel_url"]

from bisect import bisect_left, bisect_right
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Generator, List, Optional, Tuple
from zipfile import BadZipFile, ZipFile

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, Response

from pip._internal.metadata import BaseDistribution, MemoryWheel, get_wheel_distribution
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks


class HTTPRangeRequestUnsupported(Exception):
    pass


def dist_from_wheel_url(name: str, url: str, session: PipSession) -> BaseDistribution:
    """Return a distribution object from the given wheel URL.

    This uses HTTP range requests to only fetch the portion of the wheel
    containing metadata, just enough for the object to be constructed.
    If such requests are not supported, HTTPRangeRequestUnsupported
    is raised.
    """
    with LazyZipOverHTTP(url, session) as zf:
        # For read-only ZIP files, ZipFile only needs methods read,
        # seek, seekable and tell, not the whole IO protocol.
        wheel = MemoryWheel(zf.name, zf)  # type: ignore
        # After context manager exit, wheel.name
        # is an invalid file by intention.
        return get_wheel_distribution(wheel, canonicalize_name(name))


class LazyZipOverHTTP:
    """File-like object mapped to a ZIP file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content,
    which is supposed to be fed to ZipFile.  If such requests are not
    supported by the server, raise HTTPRangeRequestUnsupported
    during initialization.
    """

    def __init__(
        self, url: str, session: PipSession, chunk_size: int = CONTENT_CHUNK_SIZE
    ) -> None:
        head = session.head(url, headers=HEADERS)
        raise_for_status(head)
        assert head.status_code == 200
        self._session, self._url, self._chunk_size = session, url, chunk_size
        self._length = int(head.headers["Content-Length"])
        self._file = NamedTemporaryFile()
        self.truncate(self._length)
        self._left: List[int] = []
        self._right: List[int] = []
        if "bytes" not in head.headers.get("Accept-Ranges", "none"):
            raise HTTPRangeRequestUnsupported("range request is not supported")
        self._check_zip()

    @property
    def mode(self) -> str:
        """Opening mode, which is always rb."""
        return "rb"

    @property
    def name(self) -> str:
        """Path to the underlying file."""
        return self._file.name

    def seekable(self) -> bool:
        """Return whether random access is supported, which is True."""
        return True

    def close(self) -> None:
        """Close the file."""
        self._file.close()

    @property
    def closed(self) -> bool:
        """Whether the file is closed."""
        return self._file.closed

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.
        """
        download_size = max(size, self._chunk_size)
        start, length = self.tell(), self._length
        stop = length if size < 0 else min(start + download_size, length)
        start = max(0, stop - download_size)
        self._download(start, stop - 1)
        return self._file.read(size)

    def readable(self) -> bool:
        """Return whether the file is readable, which is True."""
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position and return the new absolute position.

        Seek to offset relative position indicated by whence:
        * 0: Start of stream (the default).  pos should be >= 0;
        * 1: Current position - pos may be negative;
        * 2: End of stream - pos usually negative.
        """
        return self._file.seek(offset, whence)

    def tell(self) -> int:
        """Return the current position."""
        return self._file.tell()

    def truncate(self, size: Optional[int] = None) -> int:
        """Resize the stream to the given size in bytes.

        If size is unspecified resize to the current position.
        The current stream position isn't changed.

        Return the new file size.
        """
        return self._file.truncate(size)

    def writable(self) -> bool:
        """Return False."""
        return False

    def __enter__(self) -> "LazyZipOverHTTP":
        self._file.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._file.__exit__(*exc)

    @contextmanager
    def _stay(self) -> Generator[None, None, None]:
        """Return a context manager keeping the position.

        At the end of the block, seek back to original position.
        """
        pos = self.tell()
        try:
            yield
        finally:
            self.seek(pos)

    def _check_zip(self) -> None:
        """Check and download until the file is a valid ZIP."""
        end = self._length - 1
        for start in reversed(range(0, end, self._chunk_size)):
            self._download(start, end)
            with self._stay():
                try:
                    # For read-only ZIP files, ZipFile only needs
                    # methods read, seek, seekable and tell.
                    ZipFile(self)
                except BadZipFile:
                    pass
                else:
                    break

    def _stream_response(
        self, start: int, end: int, base_headers: Dict[str, str] = HEADERS
    ) -> Response:
        """Return HTTP response to a range request from start to end."""
        headers = base_headers.copy()
        headers["Range"] = f"bytes={start}-{end}"
        # TODO: Get range requests to be correctly cached
        headers["Cache-Control"] = "no-cache"
        return self._session.get(self._url, headers=headers, stream=True)

    def _merge(
        self, start: int, end: int, left: int, right: int
    ) -> Generator[Tuple[int, int], None, None]:
        """Return a generator of intervals to be fetched.

        Args:
            start (int): Start of needed interval
            end (int): End of needed interval
            left (int): Index of first overlapping downloaded data
            right (int): Index after last overlapping downloaded data
        """
        lslice, rslice = self._left[left:right], self._right[left:right]
        i = start = min([start] + lslice[:1])
        end = max([end] + rslice[-1:])
        for j, k in zip(lslice, rslice):
            if j > i:
                yield i, j - 1
            i = k + 1
        if i <= end:
            yield i, end
        self._left[left:right], self._right[left:right] = [start], [end]

    def _download(self, start: int, end: int) -> None:
        """Download bytes from start to end inclusively."""
        with self._stay():
            left = bisect_left(self._right, start)
            right = bisect_right(self._left, end)
            for start, end in self._merge(start, end, left, right):
                response = self._stream_response(start, end)
                response.raise_for_status()
                self.seek(start)
                for chunk in response_chunks(response, self._chunk_size):
                    self._file.write(chunk)

# === NexusCore/openenv\Lib\site-packages\parso\parser.py ===
# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.
# 99% of the code is different from pgen2, now.

"""
The ``Parser`` tries to convert the available Python code in an easy to read
format, something like an abstract syntax tree. The classes who represent this
tree, are sitting in the :mod:`parso.tree` module.

The Python module ``tokenize`` is a very important part in the ``Parser``,
because it splits the code into different words (tokens).  Sometimes it looks a
bit messy. Sorry for that! You might ask now: "Why didn't you use the ``ast``
module for this? Well, ``ast`` does a very good job understanding proper Python
code, but fails to work as soon as there's a single line of broken code.

There's one important optimization that needs to be known: Statements are not
being parsed completely. ``Statement`` is just a representation of the tokens
within the statement. This lowers memory usage and cpu time and reduces the
complexity of the ``Parser`` (there's another parser sitting inside
``Statement``, which produces ``Array`` and ``Call``).
"""
from typing import Dict, Type

from parso import tree
from parso.pgen2.generator import ReservedString


class ParserSyntaxError(Exception):
    """
    Contains error information about the parser tree.

    May be raised as an exception.
    """
    def __init__(self, message, error_leaf):
        self.message = message
        self.error_leaf = error_leaf


class InternalParseError(Exception):
    """
    Exception to signal the parser is stuck and error recovery didn't help.
    Basically this shouldn't happen. It's a sign that something is really
    wrong.
    """

    def __init__(self, msg, type_, value, start_pos):
        Exception.__init__(self, "%s: type=%r, value=%r, start_pos=%r" %
                           (msg, type_.name, value, start_pos))
        self.msg = msg
        self.type = type
        self.value = value
        self.start_pos = start_pos


class Stack(list):
    def _allowed_transition_names_and_token_types(self):
        def iterate():
            # An API just for Jedi.
            for stack_node in reversed(self):
                for transition in stack_node.dfa.transitions:
                    if isinstance(transition, ReservedString):
                        yield transition.value
                    else:
                        yield transition  # A token type

                if not stack_node.dfa.is_final:
                    break

        return list(iterate())


class StackNode:
    def __init__(self, dfa):
        self.dfa = dfa
        self.nodes = []

    @property
    def nonterminal(self):
        return self.dfa.from_rule

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.dfa, self.nodes)


def _token_to_transition(grammar, type_, value):
    # Map from token to label
    if type_.value.contains_syntax:
        # Check for reserved words (keywords)
        try:
            return grammar.reserved_syntax_strings[value]
        except KeyError:
            pass

    return type_


class BaseParser:
    """Parser engine.

    A Parser instance contains state pertaining to the current token
    sequence, and should not be used concurrently by different threads
    to parse separate token sequences.

    See python/tokenize.py for how to get input tokens by a string.

    When a syntax error occurs, error_recovery() is called.
    """

    node_map: Dict[str, Type[tree.BaseNode]] = {}
    default_node = tree.Node

    leaf_map: Dict[str, Type[tree.Leaf]] = {}
    default_leaf = tree.Leaf

    def __init__(self, pgen_grammar, start_nonterminal='file_input', error_recovery=False):
        self._pgen_grammar = pgen_grammar
        self._start_nonterminal = start_nonterminal
        self._error_recovery = error_recovery

    def parse(self, tokens):
        first_dfa = self._pgen_grammar.nonterminal_to_dfas[self._start_nonterminal][0]
        self.stack = Stack([StackNode(first_dfa)])

        for token in tokens:
            self._add_token(token)

        while True:
            tos = self.stack[-1]
            if not tos.dfa.is_final:
                # We never broke out -- EOF is too soon -- Unfinished statement.
                # However, the error recovery might have added the token again, if
                # the stack is empty, we're fine.
                raise InternalParseError(
                    "incomplete input", token.type, token.string, token.start_pos
                )

            if len(self.stack) > 1:
                self._pop()
            else:
                return self.convert_node(tos.nonterminal, tos.nodes)

    def error_recovery(self, token):
        if self._error_recovery:
            raise NotImplementedError("Error Recovery is not implemented")
        else:
            type_, value, start_pos, prefix = token
            error_leaf = tree.ErrorLeaf(type_, value, start_pos, prefix)
            raise ParserSyntaxError('SyntaxError: invalid syntax', error_leaf)

    def convert_node(self, nonterminal, children):
        try:
            node = self.node_map[nonterminal](children)
        except KeyError:
            node = self.default_node(nonterminal, children)
        return node

    def convert_leaf(self, type_, value, prefix, start_pos):
        try:
            return self.leaf_map[type_](value, start_pos, prefix)
        except KeyError:
            return self.default_leaf(value, start_pos, prefix)

    def _add_token(self, token):
        """
        This is the only core function for parsing. Here happens basically
        everything. Everything is well prepared by the parser generator and we
        only apply the necessary steps here.
        """
        grammar = self._pgen_grammar
        stack = self.stack
        type_, value, start_pos, prefix = token
        transition = _token_to_transition(grammar, type_, value)

        while True:
            try:
                plan = stack[-1].dfa.transitions[transition]
                break
            except KeyError:
                if stack[-1].dfa.is_final:
                    self._pop()
                else:
                    self.error_recovery(token)
                    return
            except IndexError:
                raise InternalParseError("too much input", type_, value, start_pos)

        stack[-1].dfa = plan.next_dfa

        for push in plan.dfa_pushes:
            stack.append(StackNode(push))

        leaf = self.convert_leaf(type_, value, prefix, start_pos)
        stack[-1].nodes.append(leaf)

    def _pop(self):
        tos = self.stack.pop()
        # If there's exactly one child, return that child instead of
        # creating a new node.  We still create expr_stmt and
        # file_input though, because a lot of Jedi depends on its
        # logic.
        if len(tos.nodes) == 1:
            new_node = tos.nodes[0]
        else:
            new_node = self.convert_node(tos.dfa.from_rule, tos.nodes)

        self.stack[-1].nodes.append(new_node)

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\width.py ===
# -*- coding: utf-8 -*-

"""T2CharString glyph width optimizer.

CFF glyphs whose width equals the CFF Private dictionary's ``defaultWidthX``
value do not need to specify their width in their charstring, saving bytes.
This module determines the optimum ``defaultWidthX`` and ``nominalWidthX``
values for a font, when provided with a list of glyph widths."""

from fontTools.ttLib import TTFont
from collections import defaultdict
from operator import add
from functools import reduce


__all__ = ["optimizeWidths", "main"]


class missingdict(dict):
    def __init__(self, missing_func):
        self.missing_func = missing_func

    def __missing__(self, v):
        return self.missing_func(v)


def cumSum(f, op=add, start=0, decreasing=False):
    keys = sorted(f.keys())
    minx, maxx = keys[0], keys[-1]

    total = reduce(op, f.values(), start)

    if decreasing:
        missing = lambda x: start if x > maxx else total
        domain = range(maxx, minx - 1, -1)
    else:
        missing = lambda x: start if x < minx else total
        domain = range(minx, maxx + 1)

    out = missingdict(missing)

    v = start
    for x in domain:
        v = op(v, f[x])
        out[x] = v

    return out


def byteCost(widths, default, nominal):
    if not hasattr(widths, "items"):
        d = defaultdict(int)
        for w in widths:
            d[w] += 1
        widths = d

    cost = 0
    for w, freq in widths.items():
        if w == default:
            continue
        diff = abs(w - nominal)
        if diff <= 107:
            cost += freq
        elif diff <= 1131:
            cost += freq * 2
        else:
            cost += freq * 5
    return cost


def optimizeWidthsBruteforce(widths):
    """Bruteforce version.  Veeeeeeeeeeeeeeeeery slow.  Only works for smallests of fonts."""

    d = defaultdict(int)
    for w in widths:
        d[w] += 1

    # Maximum number of bytes using default can possibly save
    maxDefaultAdvantage = 5 * max(d.values())

    minw, maxw = min(widths), max(widths)
    domain = list(range(minw, maxw + 1))

    bestCostWithoutDefault = min(byteCost(widths, None, nominal) for nominal in domain)

    bestCost = len(widths) * 5 + 1
    for nominal in domain:
        if byteCost(widths, None, nominal) > bestCost + maxDefaultAdvantage:
            continue
        for default in domain:
            cost = byteCost(widths, default, nominal)
            if cost < bestCost:
                bestCost = cost
                bestDefault = default
                bestNominal = nominal

    return bestDefault, bestNominal


def optimizeWidths(widths):
    """Given a list of glyph widths, or dictionary mapping glyph width to number of
    glyphs having that, returns a tuple of best CFF default and nominal glyph widths.

    This algorithm is linear in UPEM+numGlyphs."""

    if not hasattr(widths, "items"):
        d = defaultdict(int)
        for w in widths:
            d[w] += 1
        widths = d

    keys = sorted(widths.keys())
    minw, maxw = keys[0], keys[-1]
    domain = list(range(minw, maxw + 1))

    # Cumulative sum/max forward/backward.
    cumFrqU = cumSum(widths, op=add)
    cumMaxU = cumSum(widths, op=max)
    cumFrqD = cumSum(widths, op=add, decreasing=True)
    cumMaxD = cumSum(widths, op=max, decreasing=True)

    # Cost per nominal choice, without default consideration.
    nomnCostU = missingdict(
        lambda x: cumFrqU[x] + cumFrqU[x - 108] + cumFrqU[x - 1132] * 3
    )
    nomnCostD = missingdict(
        lambda x: cumFrqD[x] + cumFrqD[x + 108] + cumFrqD[x + 1132] * 3
    )
    nomnCost = missingdict(lambda x: nomnCostU[x] + nomnCostD[x] - widths[x])

    # Cost-saving per nominal choice, by best default choice.
    dfltCostU = missingdict(
        lambda x: max(cumMaxU[x], cumMaxU[x - 108] * 2, cumMaxU[x - 1132] * 5)
    )
    dfltCostD = missingdict(
        lambda x: max(cumMaxD[x], cumMaxD[x + 108] * 2, cumMaxD[x + 1132] * 5)
    )
    dfltCost = missingdict(lambda x: max(dfltCostU[x], dfltCostD[x]))

    # Combined cost per nominal choice.
    bestCost = missingdict(lambda x: nomnCost[x] - dfltCost[x])

    # Best nominal.
    nominal = min(domain, key=lambda x: bestCost[x])

    # Work back the best default.
    bestC = bestCost[nominal]
    dfltC = nomnCost[nominal] - bestCost[nominal]
    ends = []
    if dfltC == dfltCostU[nominal]:
        starts = [nominal, nominal - 108, nominal - 1132]
        for start in starts:
            while cumMaxU[start] and cumMaxU[start] == cumMaxU[start - 1]:
                start -= 1
            ends.append(start)
    else:
        starts = [nominal, nominal + 108, nominal + 1132]
        for start in starts:
            while cumMaxD[start] and cumMaxD[start] == cumMaxD[start + 1]:
                start += 1
            ends.append(start)
    default = min(ends, key=lambda default: byteCost(widths, default, nominal))

    return default, nominal


def main(args=None):
    """Calculate optimum defaultWidthX/nominalWidthX values"""

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools cffLib.width",
        description=main.__doc__,
    )
    parser.add_argument(
        "inputs", metavar="FILE", type=str, nargs="+", help="Input TTF files"
    )
    parser.add_argument(
        "-b",
        "--brute-force",
        dest="brute",
        action="store_true",
        help="Use brute-force approach (VERY slow)",
    )

    args = parser.parse_args(args)

    for fontfile in args.inputs:
        font = TTFont(fontfile)
        hmtx = font["hmtx"]
        widths = [m[0] for m in hmtx.metrics.values()]
        if args.brute:
            default, nominal = optimizeWidthsBruteforce(widths)
        else:
            default, nominal = optimizeWidths(widths)
        print(
            "glyphs=%d default=%d nominal=%d byteCost=%d"
            % (len(widths), default, nominal, byteCost(widths, default, nominal))
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        import doctest

        sys.exit(doctest.testmod().failed)
    main()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\serialization\_base.py ===
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
"""Contains helpers to split tensors into shards."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from .. import logging


TensorT = TypeVar("TensorT")
TensorSizeFn_T = Callable[[TensorT], int]
StorageIDFn_T = Callable[[TensorT], Optional[Any]]

MAX_SHARD_SIZE = "5GB"
SIZE_UNITS = {
    "TB": 10**12,
    "GB": 10**9,
    "MB": 10**6,
    "KB": 10**3,
}


logger = logging.get_logger(__file__)


@dataclass
class StateDictSplit:
    is_sharded: bool = field(init=False)
    metadata: Dict[str, Any]
    filename_to_tensors: Dict[str, List[str]]
    tensor_to_filename: Dict[str, str]

    def __post_init__(self):
        self.is_sharded = len(self.filename_to_tensors) > 1


def split_state_dict_into_shards_factory(
    state_dict: Dict[str, TensorT],
    *,
    get_storage_size: TensorSizeFn_T,
    filename_pattern: str,
    get_storage_id: StorageIDFn_T = lambda tensor: None,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
) -> StateDictSplit:
    """
    Split a model state dictionary in shards so that each shard is smaller than a given size.

    The shards are determined by iterating through the `state_dict` in the order of its keys. There is no optimization
    made to make each shard as close as possible to the maximum size passed. For example, if the limit is 10GB and we
    have tensors of sizes [6GB, 6GB, 2GB, 6GB, 2GB, 2GB] they will get sharded as [6GB], [6+2GB], [6+2+2GB] and not
    [6+2+2GB], [6+2GB], [6GB].

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    Args:
        state_dict (`Dict[str, Tensor]`):
            The state dictionary to save.
        get_storage_size (`Callable[[Tensor], int]`):
            A function that returns the size of a tensor when saved on disk in bytes.
        get_storage_id (`Callable[[Tensor], Optional[Any]]`, *optional*):
            A function that returns a unique identifier to a tensor storage. Multiple different tensors can share the
            same underlying storage. This identifier is guaranteed to be unique and constant for this tensor's storage
            during its lifetime. Two tensor storages with non-overlapping lifetimes may have the same id.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.

    Returns:
        [`StateDictSplit`]: A `StateDictSplit` object containing the shards and the index to retrieve them.
    """
    storage_id_to_tensors: Dict[Any, List[str]] = {}

    shard_list: List[Dict[str, TensorT]] = []
    current_shard: Dict[str, TensorT] = {}
    current_shard_size = 0
    total_size = 0

    if isinstance(max_shard_size, str):
        max_shard_size = parse_size_to_int(max_shard_size)

    for key, tensor in state_dict.items():
        # when bnb serialization is used the weights in the state dict can be strings
        # check: https://github.com/huggingface/transformers/pull/24416 for more details
        if isinstance(tensor, str):
            logger.info("Skipping tensor %s as it is a string (bnb serialization)", key)
            continue

        # If a `tensor` shares the same underlying storage as another tensor, we put `tensor` in the same `block`
        storage_id = get_storage_id(tensor)
        if storage_id is not None:
            if storage_id in storage_id_to_tensors:
                # We skip this tensor for now and will reassign to correct shard later
                storage_id_to_tensors[storage_id].append(key)
                continue
            else:
                # This is the first tensor with this storage_id, we create a new entry
                # in the storage_id_to_tensors dict => we will assign the shard id later
                storage_id_to_tensors[storage_id] = [key]

        # Compute tensor size
        tensor_size = get_storage_size(tensor)

        # If this tensor is bigger than the maximal size, we put it in its own shard
        if tensor_size > max_shard_size:
            total_size += tensor_size
            shard_list.append({key: tensor})
            continue

        # If this tensor is going to tip up over the maximal size, we split.
        # Current shard already has some tensors, we add it to the list of shards and create a new one.
        if current_shard_size + tensor_size > max_shard_size:
            shard_list.append(current_shard)
            current_shard = {}
            current_shard_size = 0

        # Add the tensor to the current shard
        current_shard[key] = tensor
        current_shard_size += tensor_size
        total_size += tensor_size

    # Add the last shard
    if len(current_shard) > 0:
        shard_list.append(current_shard)
    nb_shards = len(shard_list)

    # Loop over the tensors that share the same storage and assign them together
    for storage_id, keys in storage_id_to_tensors.items():
        # Let's try to find the shard where the first tensor of this storage is and put all tensors in the same shard
        for shard in shard_list:
            if keys[0] in shard:
                for key in keys:
                    shard[key] = state_dict[key]
                break

    # If we only have one shard, we return it => no need to build the index
    if nb_shards == 1:
        filename = filename_pattern.format(suffix="")
        return StateDictSplit(
            metadata={"total_size": total_size},
            filename_to_tensors={filename: list(state_dict.keys())},
            tensor_to_filename={key: filename for key in state_dict.keys()},
        )

    # Now that each tensor is assigned to a shard, let's assign a filename to each shard
    tensor_name_to_filename = {}
    filename_to_tensors = {}
    for idx, shard in enumerate(shard_list):
        filename = filename_pattern.format(suffix=f"-{idx + 1:05d}-of-{nb_shards:05d}")
        for key in shard:
            tensor_name_to_filename[key] = filename
        filename_to_tensors[filename] = list(shard.keys())

    # Build the index and return
    return StateDictSplit(
        metadata={"total_size": total_size},
        filename_to_tensors=filename_to_tensors,
        tensor_to_filename=tensor_name_to_filename,
    )


def parse_size_to_int(size_as_str: str) -> int:
    """
    Parse a size expressed as a string with digits and unit (like `"5MB"`) to an integer (in bytes).

    Supported units are "TB", "GB", "MB", "KB".

    Args:
        size_as_str (`str`): The size to convert. Will be directly returned if an `int`.

    Example:

    ```py
    >>> parse_size_to_int("5MB")
    5000000
    ```
    """
    size_as_str = size_as_str.strip()

    # Parse unit
    unit = size_as_str[-2:].upper()
    if unit not in SIZE_UNITS:
        raise ValueError(f"Unit '{unit}' not supported. Supported units are TB, GB, MB, KB. Got '{size_as_str}'.")
    multiplier = SIZE_UNITS[unit]

    # Parse value
    try:
        value = float(size_as_str[:-2].strip())
    except ValueError as e:
        raise ValueError(f"Could not parse the size value from '{size_as_str}': {e}") from e

    return int(value * multiplier)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\batches\handler.py ===
"""
Azure Batches API Handler
"""

from typing import Any, Coroutine, Optional, Union, cast

import httpx

from litellm.llms.azure.azure import AsyncAzureOpenAI, AzureOpenAI
from litellm.types.llms.openai import (
    Batch,
    CancelBatchRequest,
    CreateBatchRequest,
    RetrieveBatchRequest,
)
from litellm.types.utils import LiteLLMBatch

from ..common_utils import BaseAzureLLM


class AzureBatchesAPI(BaseAzureLLM):
    """
    Azure methods to support for batches
    - create_batch()
    - retrieve_batch()
    - cancel_batch()
    - list_batch()
    """

    def __init__(self) -> None:
        super().__init__()

    async def acreate_batch(
        self,
        create_batch_data: CreateBatchRequest,
        azure_client: AsyncAzureOpenAI,
    ) -> LiteLLMBatch:
        response = await azure_client.batches.create(**create_batch_data)
        return LiteLLMBatch(**response.model_dump())

    def create_batch(
        self,
        _is_async: bool,
        create_batch_data: CreateBatchRequest,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ) -> Union[LiteLLMBatch, Coroutine[Any, Any, LiteLLMBatch]]:
        azure_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
            litellm_params=litellm_params or {},
        )
        if azure_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.acreate_batch(  # type: ignore
                create_batch_data=create_batch_data, azure_client=azure_client
            )
        response = cast(AzureOpenAI, azure_client).batches.create(**create_batch_data)
        return LiteLLMBatch(**response.model_dump())

    async def aretrieve_batch(
        self,
        retrieve_batch_data: RetrieveBatchRequest,
        client: AsyncAzureOpenAI,
    ) -> LiteLLMBatch:
        response = await client.batches.retrieve(**retrieve_batch_data)
        return LiteLLMBatch(**response.model_dump())

    def retrieve_batch(
        self,
        _is_async: bool,
        retrieve_batch_data: RetrieveBatchRequest,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ):
        azure_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
            litellm_params=litellm_params or {},
        )
        if azure_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.aretrieve_batch(  # type: ignore
                retrieve_batch_data=retrieve_batch_data, client=azure_client
            )
        response = cast(AzureOpenAI, azure_client).batches.retrieve(
            **retrieve_batch_data
        )
        return LiteLLMBatch(**response.model_dump())

    async def acancel_batch(
        self,
        cancel_batch_data: CancelBatchRequest,
        client: AsyncAzureOpenAI,
    ) -> Batch:
        response = await client.batches.cancel(**cancel_batch_data)
        return response

    def cancel_batch(
        self,
        _is_async: bool,
        cancel_batch_data: CancelBatchRequest,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ):
        azure_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
            litellm_params=litellm_params or {},
        )
        if azure_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )
        response = azure_client.batches.cancel(**cancel_batch_data)
        return response

    async def alist_batches(
        self,
        client: AsyncAzureOpenAI,
        after: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        response = await client.batches.list(after=after, limit=limit)  # type: ignore
        return response

    def list_batches(
        self,
        _is_async: bool,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        after: Optional[str] = None,
        limit: Optional[int] = None,
        client: Optional[AzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ):
        azure_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
            litellm_params=litellm_params or {},
        )
        if azure_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.alist_batches(  # type: ignore
                client=azure_client, after=after, limit=limit
            )
        response = azure_client.batches.list(after=after, limit=limit)  # type: ignore
        return response

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_initializers.py ===
# litellm/proxy/guardrails/guardrail_initializers.py
import litellm
from litellm.proxy._types import CommonProxyErrors
from litellm.types.guardrails import *


def initialize_aporia(
    litellm_params: LitellmParams,
    guardrail: Guardrail,
):
    from litellm.proxy.guardrails.guardrail_hooks.aporia_ai import AporiaGuardrail

    _aporia_callback = AporiaGuardrail(
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_aporia_callback)
    return _aporia_callback


def initialize_bedrock(litellm_params: LitellmParams, guardrail: Guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.bedrock_guardrails import (
        BedrockGuardrail,
    )

    _bedrock_callback = BedrockGuardrail(
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        guardrailIdentifier=litellm_params.guardrailIdentifier,
        guardrailVersion=litellm_params.guardrailVersion,
        default_on=litellm_params.default_on,
        mask_request_content=litellm_params.mask_request_content,
        mask_response_content=litellm_params.mask_response_content,
        aws_region_name=litellm_params.aws_region_name,
        aws_access_key_id=litellm_params.aws_access_key_id,
        aws_secret_access_key=litellm_params.aws_secret_access_key,
        aws_session_token=litellm_params.aws_session_token,
        aws_session_name=litellm_params.aws_session_name,
        aws_profile_name=litellm_params.aws_profile_name,
        aws_role_name=litellm_params.aws_role_name,
        aws_web_identity_token=litellm_params.aws_web_identity_token,
        aws_sts_endpoint=litellm_params.aws_sts_endpoint,
        aws_bedrock_runtime_endpoint=litellm_params.aws_bedrock_runtime_endpoint,
    )
    litellm.logging_callback_manager.add_litellm_callback(_bedrock_callback)
    return _bedrock_callback


def initialize_lakera(litellm_params: LitellmParams, guardrail: Guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.lakera_ai import lakeraAI_Moderation

    _lakera_callback = lakeraAI_Moderation(
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        category_thresholds=litellm_params.category_thresholds,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_lakera_callback)
    return _lakera_callback


def initialize_lakera_v2(litellm_params: LitellmParams, guardrail: Guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.lakera_ai_v2 import LakeraAIGuardrail

    _lakera_v2_callback = LakeraAIGuardrail(
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        default_on=litellm_params.default_on,
        project_id=litellm_params.project_id,
        payload=litellm_params.payload,
        breakdown=litellm_params.breakdown,
        metadata=litellm_params.metadata,
        dev_info=litellm_params.dev_info,
    )
    litellm.logging_callback_manager.add_litellm_callback(_lakera_v2_callback)
    return _lakera_v2_callback


def initialize_aim(litellm_params: LitellmParams, guardrail: Guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.aim import AimGuardrail

    _aim_callback = AimGuardrail(
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_aim_callback)

    return _aim_callback


def initialize_presidio(litellm_params: LitellmParams, guardrail: Guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.presidio import (
        _OPTIONAL_PresidioPIIMasking,
    )

    _presidio_callback = _OPTIONAL_PresidioPIIMasking(
        guardrail_name=guardrail.get("guardrail_name", ""),
        event_hook=litellm_params.mode,
        output_parse_pii=litellm_params.output_parse_pii,
        presidio_ad_hoc_recognizers=litellm_params.presidio_ad_hoc_recognizers,
        mock_redacted_text=litellm_params.mock_redacted_text,
        default_on=litellm_params.default_on,
        pii_entities_config=litellm_params.pii_entities_config,
        presidio_analyzer_api_base=litellm_params.presidio_analyzer_api_base,
        presidio_anonymizer_api_base=litellm_params.presidio_anonymizer_api_base,
        presidio_language=litellm_params.presidio_language,
    )
    litellm.logging_callback_manager.add_litellm_callback(_presidio_callback)

    if litellm_params.output_parse_pii:
        _success_callback = _OPTIONAL_PresidioPIIMasking(
            output_parse_pii=True,
            guardrail_name=guardrail.get("guardrail_name", ""),
            event_hook=GuardrailEventHooks.post_call.value,
            presidio_ad_hoc_recognizers=litellm_params.presidio_ad_hoc_recognizers,
            default_on=litellm_params.default_on,
            presidio_analyzer_api_base=litellm_params.presidio_analyzer_api_base,
            presidio_anonymizer_api_base=litellm_params.presidio_anonymizer_api_base,
            presidio_language=litellm_params.presidio_language,
        )
        litellm.logging_callback_manager.add_litellm_callback(_success_callback)

    return _presidio_callback


def initialize_hide_secrets(litellm_params: LitellmParams, guardrail: Guardrail):
    try:
        from litellm_enterprise.enterprise_callbacks.secret_detection import (
            _ENTERPRISE_SecretDetection,
        )
    except ImportError:
        raise Exception(
            "Trying to use Secret Detection"
            + CommonProxyErrors.missing_enterprise_package.value
        )

    _secret_detection_object = _ENTERPRISE_SecretDetection(
        detect_secrets_config=litellm_params.detect_secrets_config,
        event_hook=litellm_params.mode,
        guardrail_name=guardrail.get("guardrail_name", ""),
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_secret_detection_object)
    return _secret_detection_object


def initialize_guardrails_ai(litellm_params, guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.guardrails_ai import GuardrailsAI

    _guard_name = litellm_params.guard_name
    if not _guard_name:
        raise Exception(
            "GuardrailsAIException - Please pass the Guardrails AI guard name via 'litellm_params::guard_name'"
        )

    _guardrails_ai_callback = GuardrailsAI(
        api_base=litellm_params.api_base,
        guard_name=_guard_name,
        guardrail_name=SupportedGuardrailIntegrations.GURDRAILS_AI.value,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_guardrails_ai_callback)

    return _guardrails_ai_callback


def initialize_pangea(litellm_params, guardrail):
    from litellm.proxy.guardrails.guardrail_hooks.pangea import PangeaHandler

    _pangea_callback = PangeaHandler(
        guardrail_name=guardrail["guardrail_name"],
        pangea_input_recipe=litellm_params.pangea_input_recipe,
        pangea_output_recipe=litellm_params.pangea_output_recipe,
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_pangea_callback)

    return _pangea_callback


def initialize_lasso(
    litellm_params: LitellmParams,
    guardrail: Guardrail,
):
    from litellm.proxy.guardrails.guardrail_hooks.lasso import LassoGuardrail

    _lasso_callback = LassoGuardrail(
        guardrail_name=guardrail.get("guardrail_name", ""),
        lasso_api_key=litellm_params.api_key,
        api_base=litellm_params.api_base,
        user_id=litellm_params.lasso_user_id,
        conversation_id=litellm_params.lasso_conversation_id,
        event_hook=litellm_params.mode,
        default_on=litellm_params.default_on,
    )
    litellm.logging_callback_manager.add_litellm_callback(_lasso_callback)

    return _lasso_callback

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_json2csv_corpus.py ===
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Regression tests for `json2csv()` and `json2csv_entities()` in Twitter
package.
"""
from pathlib import Path

import pytest

from nltk.corpus import twitter_samples
from nltk.twitter.common import json2csv, json2csv_entities


def files_are_identical(pathA, pathB):
    """
    Compare two files, ignoring carriage returns,
    leading whitespace, and trailing whitespace
    """
    f1 = [l.strip() for l in pathA.read_bytes().splitlines()]
    f2 = [l.strip() for l in pathB.read_bytes().splitlines()]
    return f1 == f2


subdir = Path(__file__).parent / "files"


@pytest.fixture
def infile():
    with open(twitter_samples.abspath("tweets.20150430-223406.json")) as infile:
        return [next(infile) for x in range(100)]


def test_textoutput(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.text.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.text.csv"
    json2csv(infile, outfn, ["text"], gzip_compress=False)
    assert files_are_identical(outfn, ref_fn)


def test_tweet_metadata(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.tweet.csv.ref"
    fields = [
        "created_at",
        "favorite_count",
        "id",
        "in_reply_to_status_id",
        "in_reply_to_user_id",
        "retweet_count",
        "retweeted",
        "text",
        "truncated",
        "user.id",
    ]

    outfn = tmp_path / "tweets.20150430-223406.tweet.csv"
    json2csv(infile, outfn, fields, gzip_compress=False)
    assert files_are_identical(outfn, ref_fn)


def test_user_metadata(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.user.csv.ref"
    fields = ["id", "text", "user.id", "user.followers_count", "user.friends_count"]

    outfn = tmp_path / "tweets.20150430-223406.user.csv"
    json2csv(infile, outfn, fields, gzip_compress=False)
    assert files_are_identical(outfn, ref_fn)


def test_tweet_hashtag(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.hashtag.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.hashtag.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id", "text"],
        "hashtags",
        ["text"],
        gzip_compress=False,
    )
    assert files_are_identical(outfn, ref_fn)


def test_tweet_usermention(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.usermention.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.usermention.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id", "text"],
        "user_mentions",
        ["id", "screen_name"],
        gzip_compress=False,
    )
    assert files_are_identical(outfn, ref_fn)


def test_tweet_media(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.media.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.media.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id"],
        "media",
        ["media_url", "url"],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_tweet_url(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.url.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.url.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id"],
        "urls",
        ["url", "expanded_url"],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_userurl(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.userurl.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.userurl.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id", "screen_name"],
        "user.urls",
        ["url", "expanded_url"],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_tweet_place(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.place.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.place.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id", "text"],
        "place",
        ["name", "country"],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_tweet_place_boundingbox(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.placeboundingbox.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.placeboundingbox.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id", "name"],
        "place.bounding_box",
        ["coordinates"],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_retweet_original_tweet(tmp_path, infile):
    ref_fn = subdir / "tweets.20150430-223406.retweet.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.retweet.csv"
    json2csv_entities(
        infile,
        outfn,
        ["id"],
        "retweeted_status",
        [
            "created_at",
            "favorite_count",
            "id",
            "in_reply_to_status_id",
            "in_reply_to_user_id",
            "retweet_count",
            "text",
            "truncated",
            "user.id",
        ],
        gzip_compress=False,
    )

    assert files_are_identical(outfn, ref_fn)


def test_file_is_wrong(tmp_path, infile):
    """
    Sanity check that file comparison is not giving false positives.
    """
    ref_fn = subdir / "tweets.20150430-223406.retweet.csv.ref"
    outfn = tmp_path / "tweets.20150430-223406.text.csv"
    json2csv(infile, outfn, ["text"], gzip_compress=False)
    assert not files_are_identical(outfn, ref_fn)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\network\lazy_wheel.py ===
"""Lazy ZIP over HTTP"""

__all__ = ["HTTPRangeRequestUnsupported", "dist_from_wheel_url"]

from bisect import bisect_left, bisect_right
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Generator, List, Optional, Tuple
from zipfile import BadZipFile, ZipFile

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, Response

from pip._internal.metadata import BaseDistribution, MemoryWheel, get_wheel_distribution
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks


class HTTPRangeRequestUnsupported(Exception):
    pass


def dist_from_wheel_url(name: str, url: str, session: PipSession) -> BaseDistribution:
    """Return a distribution object from the given wheel URL.

    This uses HTTP range requests to only fetch the portion of the wheel
    containing metadata, just enough for the object to be constructed.
    If such requests are not supported, HTTPRangeRequestUnsupported
    is raised.
    """
    with LazyZipOverHTTP(url, session) as zf:
        # For read-only ZIP files, ZipFile only needs methods read,
        # seek, seekable and tell, not the whole IO protocol.
        wheel = MemoryWheel(zf.name, zf)  # type: ignore
        # After context manager exit, wheel.name
        # is an invalid file by intention.
        return get_wheel_distribution(wheel, canonicalize_name(name))


class LazyZipOverHTTP:
    """File-like object mapped to a ZIP file over HTTP.

    This uses HTTP range requests to lazily fetch the file's content,
    which is supposed to be fed to ZipFile.  If such requests are not
    supported by the server, raise HTTPRangeRequestUnsupported
    during initialization.
    """

    def __init__(
        self, url: str, session: PipSession, chunk_size: int = CONTENT_CHUNK_SIZE
    ) -> None:
        head = session.head(url, headers=HEADERS)
        raise_for_status(head)
        assert head.status_code == 200
        self._session, self._url, self._chunk_size = session, url, chunk_size
        self._length = int(head.headers["Content-Length"])
        self._file = NamedTemporaryFile()
        self.truncate(self._length)
        self._left: List[int] = []
        self._right: List[int] = []
        if "bytes" not in head.headers.get("Accept-Ranges", "none"):
            raise HTTPRangeRequestUnsupported("range request is not supported")
        self._check_zip()

    @property
    def mode(self) -> str:
        """Opening mode, which is always rb."""
        return "rb"

    @property
    def name(self) -> str:
        """Path to the underlying file."""
        return self._file.name

    def seekable(self) -> bool:
        """Return whether random access is supported, which is True."""
        return True

    def close(self) -> None:
        """Close the file."""
        self._file.close()

    @property
    def closed(self) -> bool:
        """Whether the file is closed."""
        return self._file.closed

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the object and return them.

        As a convenience, if size is unspecified or -1,
        all bytes until EOF are returned.  Fewer than
        size bytes may be returned if EOF is reached.
        """
        download_size = max(size, self._chunk_size)
        start, length = self.tell(), self._length
        stop = length if size < 0 else min(start + download_size, length)
        start = max(0, stop - download_size)
        self._download(start, stop - 1)
        return self._file.read(size)

    def readable(self) -> bool:
        """Return whether the file is readable, which is True."""
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        """Change stream position and return the new absolute position.

        Seek to offset relative position indicated by whence:
        * 0: Start of stream (the default).  pos should be >= 0;
        * 1: Current position - pos may be negative;
        * 2: End of stream - pos usually negative.
        """
        return self._file.seek(offset, whence)

    def tell(self) -> int:
        """Return the current position."""
        return self._file.tell()

    def truncate(self, size: Optional[int] = None) -> int:
        """Resize the stream to the given size in bytes.

        If size is unspecified resize to the current position.
        The current stream position isn't changed.

        Return the new file size.
        """
        return self._file.truncate(size)

    def writable(self) -> bool:
        """Return False."""
        return False

    def __enter__(self) -> "LazyZipOverHTTP":
        self._file.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._file.__exit__(*exc)

    @contextmanager
    def _stay(self) -> Generator[None, None, None]:
        """Return a context manager keeping the position.

        At the end of the block, seek back to original position.
        """
        pos = self.tell()
        try:
            yield
        finally:
            self.seek(pos)

    def _check_zip(self) -> None:
        """Check and download until the file is a valid ZIP."""
        end = self._length - 1
        for start in reversed(range(0, end, self._chunk_size)):
            self._download(start, end)
            with self._stay():
                try:
                    # For read-only ZIP files, ZipFile only needs
                    # methods read, seek, seekable and tell.
                    ZipFile(self)
                except BadZipFile:
                    pass
                else:
                    break

    def _stream_response(
        self, start: int, end: int, base_headers: Dict[str, str] = HEADERS
    ) -> Response:
        """Return HTTP response to a range request from start to end."""
        headers = base_headers.copy()
        headers["Range"] = f"bytes={start}-{end}"
        # TODO: Get range requests to be correctly cached
        headers["Cache-Control"] = "no-cache"
        return self._session.get(self._url, headers=headers, stream=True)

    def _merge(
        self, start: int, end: int, left: int, right: int
    ) -> Generator[Tuple[int, int], None, None]:
        """Return a generator of intervals to be fetched.

        Args:
            start (int): Start of needed interval
            end (int): End of needed interval
            left (int): Index of first overlapping downloaded data
            right (int): Index after last overlapping downloaded data
        """
        lslice, rslice = self._left[left:right], self._right[left:right]
        i = start = min([start] + lslice[:1])
        end = max([end] + rslice[-1:])
        for j, k in zip(lslice, rslice):
            if j > i:
                yield i, j - 1
            i = k + 1
        if i <= end:
            yield i, end
        self._left[left:right], self._right[left:right] = [start], [end]

    def _download(self, start: int, end: int) -> None:
        """Download bytes from start to end inclusively."""
        with self._stay():
            left = bisect_left(self._right, start)
            right = bisect_right(self._left, end)
            for start, end in self._merge(start, end, left, right):
                response = self._stream_response(start, end)
                response.raise_for_status()
                self.seek(start)
                for chunk in response_chunks(response, self._chunk_size):
                    self._file.write(chunk)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\mime.py ===
"""
    pygments.lexers.mime
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for Multipurpose Internet Mail Extensions (MIME) data.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include
from pygments.lexers import get_lexer_for_mimetype
from pygments.token import Text, Name, String, Operator, Comment, Other
from pygments.util import get_int_opt, ClassNotFound

__all__ = ["MIMELexer"]


class MIMELexer(RegexLexer):
    """
    Lexer for Multipurpose Internet Mail Extensions (MIME) data. This lexer is
    designed to process nested multipart data.

    It assumes that the given data contains both header and body (and is
    split at an empty line). If no valid header is found, then the entire data
    will be treated as body.

    Additional options accepted:

    `MIME-max-level`
        Max recursion level for nested MIME structure. Any negative number
        would treated as unlimited. (default: -1)

    `Content-Type`
        Treat the data as a specific content type. Useful when header is
        missing, or this lexer would try to parse from header. (default:
        `text/plain`)

    `Multipart-Boundary`
        Set the default multipart boundary delimiter. This option is only used
        when `Content-Type` is `multipart` and header is missing. This lexer
        would try to parse from header by default. (default: None)

    `Content-Transfer-Encoding`
        Treat the data as a specific encoding. Or this lexer would try to parse
        from header by default. (default: None)
    """

    name = "MIME"
    aliases = ["mime"]
    mimetypes = ["multipart/mixed",
                 "multipart/related",
                 "multipart/alternative"]
    url = 'https://en.wikipedia.org/wiki/MIME'
    version_added = '2.5'

    def __init__(self, **options):
        super().__init__(**options)
        self.boundary = options.get("Multipart-Boundary")
        self.content_transfer_encoding = options.get("Content_Transfer_Encoding")
        self.content_type = options.get("Content_Type", "text/plain")
        self.max_nested_level = get_int_opt(options, "MIME-max-level", -1)

    def get_header_tokens(self, match):
        field = match.group(1)

        if field.lower() in self.attention_headers:
            yield match.start(1), Name.Tag, field + ":"
            yield match.start(2), Text.Whitespace, match.group(2)

            pos = match.end(2)
            body = match.group(3)
            for i, t, v in self.get_tokens_unprocessed(body, ("root", field.lower())):
                yield pos + i, t, v

        else:
            yield match.start(), Comment, match.group()

    def get_body_tokens(self, match):
        pos_body_start = match.start()
        entire_body = match.group()

        # skip first newline
        if entire_body[0] == '\n':
            yield pos_body_start, Text.Whitespace, '\n'
            pos_body_start = pos_body_start + 1
            entire_body = entire_body[1:]

        # if it is not a multipart
        if not self.content_type.startswith("multipart") or not self.boundary:
            for i, t, v in self.get_bodypart_tokens(entire_body):
                yield pos_body_start + i, t, v
            return

        # find boundary
        bdry_pattern = rf"^--{re.escape(self.boundary)}(--)?\n"
        bdry_matcher = re.compile(bdry_pattern, re.MULTILINE)

        # some data has prefix text before first boundary
        m = bdry_matcher.search(entire_body)
        if m:
            pos_part_start = pos_body_start + m.end()
            pos_iter_start = lpos_end = m.end()
            yield pos_body_start, Text, entire_body[:m.start()]
            yield pos_body_start + lpos_end, String.Delimiter, m.group()
        else:
            pos_part_start = pos_body_start
            pos_iter_start = 0

        # process tokens of each body part
        for m in bdry_matcher.finditer(entire_body, pos_iter_start):
            # bodypart
            lpos_start = pos_part_start - pos_body_start
            lpos_end = m.start()
            part = entire_body[lpos_start:lpos_end]
            for i, t, v in self.get_bodypart_tokens(part):
                yield pos_part_start + i, t, v

            # boundary
            yield pos_body_start + lpos_end, String.Delimiter, m.group()
            pos_part_start = pos_body_start + m.end()

        # some data has suffix text after last boundary
        lpos_start = pos_part_start - pos_body_start
        if lpos_start != len(entire_body):
            yield pos_part_start, Text, entire_body[lpos_start:]

    def get_bodypart_tokens(self, text):
        # return if:
        #  * no content
        #  * no content type specific
        #  * content encoding is not readable
        #  * max recurrsion exceed
        if not text.strip() or not self.content_type:
            return [(0, Other, text)]

        cte = self.content_transfer_encoding
        if cte and cte not in {"8bit", "7bit", "quoted-printable"}:
            return [(0, Other, text)]

        if self.max_nested_level == 0:
            return [(0, Other, text)]

        # get lexer
        try:
            lexer = get_lexer_for_mimetype(self.content_type)
        except ClassNotFound:
            return [(0, Other, text)]

        if isinstance(lexer, type(self)):
            lexer.max_nested_level = self.max_nested_level - 1

        return lexer.get_tokens_unprocessed(text)

    def store_content_type(self, match):
        self.content_type = match.group(1)

        prefix_len = match.start(1) - match.start(0)
        yield match.start(0), Text.Whitespace, match.group(0)[:prefix_len]
        yield match.start(1), Name.Label, match.group(2)
        yield match.end(2), String.Delimiter, '/'
        yield match.start(3), Name.Label, match.group(3)

    def get_content_type_subtokens(self, match):
        yield match.start(1), Text, match.group(1)
        yield match.start(2), Text.Whitespace, match.group(2)
        yield match.start(3), Name.Attribute, match.group(3)
        yield match.start(4), Operator, match.group(4)
        yield match.start(5), String, match.group(5)

        if match.group(3).lower() == "boundary":
            boundary = match.group(5).strip()
            if boundary[0] == '"' and boundary[-1] == '"':
                boundary = boundary[1:-1]
            self.boundary = boundary

    def store_content_transfer_encoding(self, match):
        self.content_transfer_encoding = match.group(0).lower()
        yield match.start(0), Name.Constant, match.group(0)

    attention_headers = {"content-type", "content-transfer-encoding"}

    tokens = {
        "root": [
            (r"^([\w-]+):( *)([\s\S]*?\n)(?![ \t])", get_header_tokens),
            (r"^$[\s\S]+", get_body_tokens),
        ],
        "header": [
            # folding
            (r"\n[ \t]", Text.Whitespace),
            (r"\n(?![ \t])", Text.Whitespace, "#pop"),
        ],
        "content-type": [
            include("header"),
            (
                r"^\s*((multipart|application|audio|font|image|model|text|video"
                r"|message)/([\w-]+))",
                store_content_type,
            ),
            (r'(;)((?:[ \t]|\n[ \t])*)([\w:-]+)(=)([\s\S]*?)(?=;|\n(?![ \t]))',
             get_content_type_subtokens),
            (r';[ \t]*\n(?![ \t])', Text, '#pop'),
        ],
        "content-transfer-encoding": [
            include("header"),
            (r"([\w-]+)", store_content_transfer_encoding),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\tornado\test\netutil_test.py ===
import errno
import signal
import socket
from subprocess import Popen
import sys
import time
import unittest

from tornado.netutil import (
    BlockingResolver,
    OverrideResolver,
    ThreadedResolver,
    is_valid_ip,
    bind_sockets,
)
from tornado.testing import AsyncTestCase, gen_test, bind_unused_port
from tornado.test.util import skipIfNoNetwork, abstract_base_test

import typing

try:
    import pycares  # type: ignore
except ImportError:
    pycares = None
else:
    from tornado.platform.caresresolver import CaresResolver


@abstract_base_test
class _ResolverTestMixin(AsyncTestCase):
    resolver = None  # type: typing.Any

    @gen_test
    def test_localhost(self):
        addrinfo = yield self.resolver.resolve("localhost", 80, socket.AF_UNSPEC)
        # Most of the time localhost resolves to either the ipv4 loopback
        # address alone, or ipv4+ipv6. But some versions of pycares will only
        # return the ipv6 version, so we have to check for either one alone.
        self.assertTrue(
            ((socket.AF_INET, ("127.0.0.1", 80)) in addrinfo)
            or ((socket.AF_INET6, ("::1", 80)) in addrinfo),
            f"loopback address not found in {addrinfo}",
        )


# It is impossible to quickly and consistently generate an error in name
# resolution, so test this case separately, using mocks as needed.
@abstract_base_test
class _ResolverErrorTestMixin(AsyncTestCase):
    resolver = None  # type: typing.Any

    @gen_test
    def test_bad_host(self):
        with self.assertRaises(IOError):
            yield self.resolver.resolve("an invalid domain", 80, socket.AF_UNSPEC)


def _failing_getaddrinfo(*args):
    """Dummy implementation of getaddrinfo for use in mocks"""
    raise socket.gaierror(errno.EIO, "mock: lookup failed")


@skipIfNoNetwork
class BlockingResolverTest(_ResolverTestMixin):
    def setUp(self):
        super().setUp()
        self.resolver = BlockingResolver()


# getaddrinfo-based tests need mocking to reliably generate errors;
# some configurations are slow to produce errors and take longer than
# our default timeout.
class BlockingResolverErrorTest(_ResolverErrorTestMixin):
    def setUp(self):
        super().setUp()
        self.resolver = BlockingResolver()
        self.real_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = _failing_getaddrinfo

    def tearDown(self):
        socket.getaddrinfo = self.real_getaddrinfo
        super().tearDown()


class OverrideResolverTest(_ResolverTestMixin):
    def setUp(self):
        super().setUp()
        mapping = {
            ("google.com", 80): ("1.2.3.4", 80),
            ("google.com", 80, socket.AF_INET): ("1.2.3.4", 80),
            ("google.com", 80, socket.AF_INET6): (
                "2a02:6b8:7c:40c:c51e:495f:e23a:3",
                80,
            ),
        }
        self.resolver = OverrideResolver(BlockingResolver(), mapping)

    @gen_test
    def test_resolve_multiaddr(self):
        result = yield self.resolver.resolve("google.com", 80, socket.AF_INET)
        self.assertIn((socket.AF_INET, ("1.2.3.4", 80)), result)

        result = yield self.resolver.resolve("google.com", 80, socket.AF_INET6)
        self.assertIn(
            (socket.AF_INET6, ("2a02:6b8:7c:40c:c51e:495f:e23a:3", 80, 0, 0)), result
        )


@skipIfNoNetwork
class ThreadedResolverTest(_ResolverTestMixin):
    def setUp(self):
        super().setUp()
        self.resolver = ThreadedResolver()

    def tearDown(self):
        self.resolver.close()
        super().tearDown()


class ThreadedResolverErrorTest(_ResolverErrorTestMixin):
    def setUp(self):
        super().setUp()
        self.resolver = BlockingResolver()
        self.real_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = _failing_getaddrinfo

    def tearDown(self):
        socket.getaddrinfo = self.real_getaddrinfo
        super().tearDown()


@skipIfNoNetwork
@unittest.skipIf(sys.platform == "win32", "preexec_fn not available on win32")
class ThreadedResolverImportTest(unittest.TestCase):
    def test_import(self):
        TIMEOUT = 5

        # Test for a deadlock when importing a module that runs the
        # ThreadedResolver at import-time. See resolve_test.py for
        # full explanation.
        command = [sys.executable, "-c", "import tornado.test.resolve_test_helper"]

        start = time.time()
        popen = Popen(command, preexec_fn=lambda: signal.alarm(TIMEOUT))
        while time.time() - start < TIMEOUT:
            return_code = popen.poll()
            if return_code is not None:
                self.assertEqual(0, return_code)
                return  # Success.
            time.sleep(0.05)

        self.fail("import timed out")


# We do not test errors with CaresResolver:
# Some DNS-hijacking ISPs (e.g. Time Warner) return non-empty results
# with an NXDOMAIN status code.  Most resolvers treat this as an error;
# C-ares returns the results, making the "bad_host" tests unreliable.
# C-ares will try to resolve even malformed names, such as the
# name with spaces used in this test.
@skipIfNoNetwork
@unittest.skipIf(pycares is None, "pycares module not present")
@unittest.skipIf(sys.platform == "win32", "pycares doesn't return loopback on windows")
@unittest.skipIf(sys.platform == "darwin", "pycares doesn't return 127.0.0.1 on darwin")
class CaresResolverTest(_ResolverTestMixin):
    def setUp(self):
        super().setUp()
        self.resolver = CaresResolver()


class IsValidIPTest(unittest.TestCase):
    def test_is_valid_ip(self):
        self.assertTrue(is_valid_ip("127.0.0.1"))
        self.assertTrue(is_valid_ip("4.4.4.4"))
        self.assertTrue(is_valid_ip("::1"))
        self.assertTrue(is_valid_ip("2620:0:1cfe:face:b00c::3"))
        self.assertFalse(is_valid_ip("www.google.com"))
        self.assertFalse(is_valid_ip("localhost"))
        self.assertFalse(is_valid_ip("4.4.4.4<"))
        self.assertFalse(is_valid_ip(" 127.0.0.1"))
        self.assertFalse(is_valid_ip(""))
        self.assertFalse(is_valid_ip(" "))
        self.assertFalse(is_valid_ip("\n"))
        self.assertFalse(is_valid_ip("\x00"))
        self.assertFalse(is_valid_ip("a" * 100))


class TestPortAllocation(unittest.TestCase):
    def test_same_port_allocation(self):
        sockets = bind_sockets(0, "localhost")
        try:
            port = sockets[0].getsockname()[1]
            self.assertTrue(all(s.getsockname()[1] == port for s in sockets[1:]))
        finally:
            for sock in sockets:
                sock.close()

    @unittest.skipIf(
        not hasattr(socket, "SO_REUSEPORT"), "SO_REUSEPORT is not supported"
    )
    def test_reuse_port(self):
        sockets: typing.List[socket.socket] = []
        sock, port = bind_unused_port(reuse_port=True)
        try:
            sockets = bind_sockets(port, "127.0.0.1", reuse_port=True)
            self.assertTrue(all(s.getsockname()[1] == port for s in sockets))
        finally:
            sock.close()
            for sock in sockets:
                sock.close()

# === NexusCore/openenv\Lib\site-packages\win32\Demos\SystemParametersInfo.py ===
import glob
import os
import time

import win32api
import win32con
import win32gui

## some of these tests will fail for systems prior to XP

for pname in (
    ## Set actions all take an unsigned int in pvParam
    "SPI_GETMOUSESPEED",
    "SPI_GETACTIVEWNDTRKTIMEOUT",
    "SPI_GETCARETWIDTH",
    "SPI_GETFOREGROUNDFLASHCOUNT",
    "SPI_GETFOREGROUNDLOCKTIMEOUT",
    ## Set actions all take an unsigned int in uiParam
    "SPI_GETWHEELSCROLLLINES",
    "SPI_GETKEYBOARDDELAY",
    "SPI_GETKEYBOARDSPEED",
    "SPI_GETMOUSEHOVERHEIGHT",
    "SPI_GETMOUSEHOVERWIDTH",
    "SPI_GETMOUSEHOVERTIME",
    "SPI_GETSCREENSAVETIMEOUT",
    "SPI_GETMENUSHOWDELAY",
    "SPI_GETLOWPOWERTIMEOUT",
    "SPI_GETPOWEROFFTIMEOUT",
    "SPI_GETBORDER",
    ## below are winxp only:
    "SPI_GETFONTSMOOTHINGCONTRAST",
    "SPI_GETFONTSMOOTHINGTYPE",
    "SPI_GETFOCUSBORDERHEIGHT",
    "SPI_GETFOCUSBORDERWIDTH",
    "SPI_GETMOUSECLICKLOCKTIME",
):
    print(pname)
    cget = getattr(win32con, pname)
    cset = getattr(win32con, pname.replace("_GET", "_SET"))
    orig_value = win32gui.SystemParametersInfo(cget)
    print("\toriginal setting:", orig_value)
    win32gui.SystemParametersInfo(cset, orig_value + 1)
    new_value = win32gui.SystemParametersInfo(cget)
    print("\tnew value:", new_value)
    # On Vista, some of these values seem to be ignored.  So only "fail" if
    # the new value isn't what we set or the original
    if new_value != orig_value + 1:
        assert new_value == orig_value
        print(f"Strange - setting {pname} seems to have been ignored")
    win32gui.SystemParametersInfo(cset, orig_value)
    assert win32gui.SystemParametersInfo(cget) == orig_value


# these take a boolean value in pvParam
# change to opposite, check that it was changed and change back
for pname in (
    "SPI_GETFLATMENU",
    "SPI_GETDROPSHADOW",
    "SPI_GETKEYBOARDCUES",
    "SPI_GETMENUFADE",
    "SPI_GETCOMBOBOXANIMATION",
    "SPI_GETCURSORSHADOW",
    "SPI_GETGRADIENTCAPTIONS",
    "SPI_GETHOTTRACKING",
    "SPI_GETLISTBOXSMOOTHSCROLLING",
    "SPI_GETMENUANIMATION",
    "SPI_GETSELECTIONFADE",
    "SPI_GETTOOLTIPANIMATION",
    "SPI_GETTOOLTIPFADE",
    "SPI_GETUIEFFECTS",
    "SPI_GETACTIVEWINDOWTRACKING",
    "SPI_GETACTIVEWNDTRKZORDER",
):
    print(pname)
    cget = getattr(win32con, pname)
    cset = getattr(win32con, pname.replace("_GET", "_SET"))
    orig_value = win32gui.SystemParametersInfo(cget)
    print(orig_value)
    win32gui.SystemParametersInfo(cset, not orig_value)
    new_value = win32gui.SystemParametersInfo(cget)
    print(new_value)
    assert orig_value != new_value
    win32gui.SystemParametersInfo(cset, orig_value)
    assert win32gui.SystemParametersInfo(cget) == orig_value


# these take a boolean in uiParam
#  could combine with above section now that SystemParametersInfo only takes a single parameter
for pname in (
    "SPI_GETFONTSMOOTHING",
    "SPI_GETICONTITLEWRAP",
    "SPI_GETBEEP",
    "SPI_GETBLOCKSENDINPUTRESETS",
    "SPI_GETKEYBOARDPREF",
    "SPI_GETSCREENSAVEACTIVE",
    "SPI_GETMENUDROPALIGNMENT",
    "SPI_GETDRAGFULLWINDOWS",
    "SPI_GETSHOWIMEUI",
):
    cget = getattr(win32con, pname)
    cset = getattr(win32con, pname.replace("_GET", "_SET"))
    orig_value = win32gui.SystemParametersInfo(cget)
    win32gui.SystemParametersInfo(cset, not orig_value)
    new_value = win32gui.SystemParametersInfo(cget)
    # Some of these also can't be changed (eg, SPI_GETSCREENSAVEACTIVE) so
    # don't actually get upset.
    if orig_value != new_value:
        print("successfully toggled", pname, "from", orig_value, "to", new_value)
    else:
        print("couldn't toggle", pname, "from", orig_value)
    win32gui.SystemParametersInfo(cset, orig_value)
    assert win32gui.SystemParametersInfo(cget) == orig_value


print("SPI_GETICONTITLELOGFONT")
lf = win32gui.SystemParametersInfo(win32con.SPI_GETICONTITLELOGFONT)
orig_height = lf.lfHeight
orig_italic = lf.lfItalic
print("Height:", orig_height, "Italic:", orig_italic)
lf.lfHeight += 2
lf.lfItalic = not lf.lfItalic
win32gui.SystemParametersInfo(win32con.SPI_SETICONTITLELOGFONT, lf)
new_lf = win32gui.SystemParametersInfo(win32con.SPI_GETICONTITLELOGFONT)
print("New Height:", new_lf.lfHeight, "New Italic:", new_lf.lfItalic)
assert new_lf.lfHeight == orig_height + 2
assert new_lf.lfItalic != orig_italic

lf.lfHeight = orig_height
lf.lfItalic = orig_italic
win32gui.SystemParametersInfo(win32con.SPI_SETICONTITLELOGFONT, lf)
new_lf = win32gui.SystemParametersInfo(win32con.SPI_GETICONTITLELOGFONT)
assert new_lf.lfHeight == orig_height
assert new_lf.lfItalic == orig_italic


print("SPI_GETMOUSEHOVERWIDTH, SPI_GETMOUSEHOVERHEIGHT, SPI_GETMOUSEHOVERTIME")
w = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERWIDTH)
h = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERHEIGHT)
t = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERTIME)
print("w,h,t:", w, h, t)

win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERWIDTH, w + 1)
win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERHEIGHT, h + 2)
win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERTIME, t + 3)
new_w = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERWIDTH)
new_h = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERHEIGHT)
new_t = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERTIME)
print("new w,h,t:", new_w, new_h, new_t)
assert new_w == w + 1
assert new_h == h + 2
assert new_t == t + 3

win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERWIDTH, w)
win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERHEIGHT, h)
win32gui.SystemParametersInfo(win32con.SPI_SETMOUSEHOVERTIME, t)
new_w = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERWIDTH)
new_h = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERHEIGHT)
new_t = win32gui.SystemParametersInfo(win32con.SPI_GETMOUSEHOVERTIME)
assert new_w == w
assert new_h == h
assert new_t == t


print("SPI_SETDOUBLECLKWIDTH, SPI_SETDOUBLECLKHEIGHT")
x = win32api.GetSystemMetrics(win32con.SM_CXDOUBLECLK)
y = win32api.GetSystemMetrics(win32con.SM_CYDOUBLECLK)
print("x,y:", x, y)
win32gui.SystemParametersInfo(win32con.SPI_SETDOUBLECLKWIDTH, x + 1)
win32gui.SystemParametersInfo(win32con.SPI_SETDOUBLECLKHEIGHT, y + 2)
new_x = win32api.GetSystemMetrics(win32con.SM_CXDOUBLECLK)
new_y = win32api.GetSystemMetrics(win32con.SM_CYDOUBLECLK)
print("new x,y:", new_x, new_y)
assert new_x == x + 1
assert new_y == y + 2
win32gui.SystemParametersInfo(win32con.SPI_SETDOUBLECLKWIDTH, x)
win32gui.SystemParametersInfo(win32con.SPI_SETDOUBLECLKHEIGHT, y)
new_x = win32api.GetSystemMetrics(win32con.SM_CXDOUBLECLK)
new_y = win32api.GetSystemMetrics(win32con.SM_CYDOUBLECLK)
assert new_x == x
assert new_y == y


print("SPI_SETDRAGWIDTH, SPI_SETDRAGHEIGHT")
dw = win32api.GetSystemMetrics(win32con.SM_CXDRAG)
dh = win32api.GetSystemMetrics(win32con.SM_CYDRAG)
print("dw,dh:", dw, dh)
win32gui.SystemParametersInfo(win32con.SPI_SETDRAGWIDTH, dw + 1)
win32gui.SystemParametersInfo(win32con.SPI_SETDRAGHEIGHT, dh + 2)
new_dw = win32api.GetSystemMetrics(win32con.SM_CXDRAG)
new_dh = win32api.GetSystemMetrics(win32con.SM_CYDRAG)
print("new dw,dh:", new_dw, new_dh)
assert new_dw == dw + 1
assert new_dh == dh + 2
win32gui.SystemParametersInfo(win32con.SPI_SETDRAGWIDTH, dw)
win32gui.SystemParametersInfo(win32con.SPI_SETDRAGHEIGHT, dh)
new_dw = win32api.GetSystemMetrics(win32con.SM_CXDRAG)
new_dh = win32api.GetSystemMetrics(win32con.SM_CYDRAG)
assert new_dw == dw
assert new_dh == dh


orig_wallpaper = win32gui.SystemParametersInfo(Action=win32con.SPI_GETDESKWALLPAPER)
print("Original: ", orig_wallpaper)
for bmp in glob.glob(os.path.join(os.environ["windir"], "*.bmp")):
    print(bmp)
    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, Param=bmp)
    print(win32gui.SystemParametersInfo(Action=win32con.SPI_GETDESKWALLPAPER))
    time.sleep(1)

win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, Param=orig_wallpaper)

# === NexusCore/openenv\Lib\site-packages\astor\rtrip.py ===
#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright (c) 2015 Patrick Maupin
"""

import sys
import os
import ast
import shutil
import logging

from astor.code_gen import to_source
from astor.file_util import code_to_ast
from astor.node_util import (allow_ast_comparison, dump_tree,
                             strip_tree, fast_compare)


dsttree = 'tmp_rtrip'

# TODO:  Remove this workaround once we remove version 2 support


def out_prep(s, pre_encoded=(sys.version_info[0] == 2)):
    return s if pre_encoded else s.encode('utf-8')


def convert(srctree, dsttree=dsttree, readonly=False, dumpall=False,
            ignore_exceptions=False, fullcomp=False):
    """Walk the srctree, and convert/copy all python files
    into the dsttree

    """

    if fullcomp:
        allow_ast_comparison()

    parse_file = code_to_ast.parse_file
    find_py_files = code_to_ast.find_py_files
    srctree = os.path.normpath(srctree)

    if not readonly:
        dsttree = os.path.normpath(dsttree)
        logging.info('')
        logging.info('Trashing ' + dsttree)
        shutil.rmtree(dsttree, True)

    unknown_src_nodes = set()
    unknown_dst_nodes = set()
    badfiles = set()
    broken = []

    oldpath = None

    allfiles = find_py_files(srctree, None if readonly else dsttree)
    for srcpath, fname in allfiles:
        # Create destination directory
        if not readonly and srcpath != oldpath:
            oldpath = srcpath
            if srcpath >= srctree:
                dstpath = srcpath.replace(srctree, dsttree, 1)
                if not dstpath.startswith(dsttree):
                    raise ValueError("%s not a subdirectory of %s" %
                                     (dstpath, dsttree))
            else:
                assert srctree.startswith(srcpath)
                dstpath = dsttree
            os.makedirs(dstpath)

        srcfname = os.path.join(srcpath, fname)
        logging.info('Converting %s' % srcfname)
        try:
            srcast = parse_file(srcfname)
        except SyntaxError:
            badfiles.add(srcfname)
            continue

        try:
            dsttxt = to_source(srcast)
        except Exception:
            if not ignore_exceptions:
                raise
            dsttxt = ''

        if not readonly:
            dstfname = os.path.join(dstpath, fname)
            try:
                with open(dstfname, 'wb') as f:
                    f.write(out_prep(dsttxt))
            except UnicodeEncodeError:
                badfiles.add(dstfname)

        # As a sanity check, make sure that ASTs themselves
        # round-trip OK
        try:
            dstast = ast.parse(dsttxt) if readonly else parse_file(dstfname)
        except SyntaxError:
            dstast = []
        if fullcomp:
            unknown_src_nodes.update(strip_tree(srcast))
            unknown_dst_nodes.update(strip_tree(dstast))
            bad = srcast != dstast
        else:
            bad = not fast_compare(srcast, dstast)
        if dumpall or bad:
            srcdump = dump_tree(srcast)
            dstdump = dump_tree(dstast)
            logging.warning('    calculating dump -- %s' %
                            ('bad' if bad else 'OK'))
            if bad:
                broken.append(srcfname)
            if dumpall or bad:
                if not readonly:
                    try:
                        with open(dstfname[:-3] + '.srcdmp', 'wb') as f:
                            f.write(out_prep(srcdump))
                    except UnicodeEncodeError:
                        badfiles.add(dstfname[:-3] + '.srcdmp')
                    try:
                        with open(dstfname[:-3] + '.dstdmp', 'wb') as f:
                            f.write(out_prep(dstdump))
                    except UnicodeEncodeError:
                        badfiles.add(dstfname[:-3] + '.dstdmp')
                elif dumpall:
                    sys.stdout.write('\n\nAST:\n\n    ')
                    sys.stdout.write(srcdump.replace('\n', '\n    '))
                    sys.stdout.write('\n\nDecompile:\n\n    ')
                    sys.stdout.write(dsttxt.replace('\n', '\n    '))
                    sys.stdout.write('\n\nNew AST:\n\n    ')
                    sys.stdout.write('(same as old)' if dstdump == srcdump
                                     else dstdump.replace('\n', '\n    '))
                    sys.stdout.write('\n')

    if badfiles:
        logging.warning('\nFiles not processed due to syntax errors:')
        for fname in sorted(badfiles):
            logging.warning('    %s' % fname)
    if broken:
        logging.warning('\nFiles failed to round-trip to AST:')
        for srcfname in broken:
            logging.warning('    %s' % srcfname)

    ok_to_strip = 'col_offset _precedence _use_parens lineno _p_op _pp'
    ok_to_strip = set(ok_to_strip.split())
    bad_nodes = (unknown_dst_nodes | unknown_src_nodes) - ok_to_strip
    if bad_nodes:
        logging.error('\nERROR -- UNKNOWN NODES STRIPPED: %s' % bad_nodes)
    logging.info('\n')
    return broken


def usage(msg):
    raise SystemExit(textwrap.dedent("""

        Error: %s

        Usage:

            python -m astor.rtrip [readonly] [<source>]


        This utility tests round-tripping of Python source to AST
        and back to source.

        If readonly is specified, then the source will be tested,
        but no files will be written.

        if the source is specified to be "stdin" (without quotes)
        then any source entered at the command line will be compiled
        into an AST, converted back to text, and then compiled to
        an AST again, and the results will be displayed to stdout.

        If neither readonly nor stdin is specified, then rtrip
        will create a mirror directory named tmp_rtrip and will
        recursively round-trip all the Python source from the source
        into the tmp_rtrip dir, after compiling it and then reconstituting
        it through code_gen.to_source.

        If the source is not specified, the entire Python library will be used.

        """) % msg)


if __name__ == '__main__':
    import textwrap

    args = sys.argv[1:]

    readonly = 'readonly' in args
    if readonly:
        args.remove('readonly')

    if not args:
        args = [os.path.dirname(textwrap.__file__)]

    if len(args) > 1:
        usage("Too many arguments")

    fname, = args
    dumpall = False
    if not os.path.exists(fname):
        dumpall = fname == 'stdin' or usage("Cannot find directory %s" % fname)

    logging.basicConfig(format='%(msg)s', level=logging.INFO)
    convert(fname, readonly=readonly or dumpall, dumpall=dumpall)

# === NexusCore/openenv\Lib\site-packages\nltk\__init__.py ===
# Natural Language Toolkit (NLTK)
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Steven Bird <stevenbird1@gmail.com>
#          Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
The Natural Language Toolkit (NLTK) is an open source Python library
for Natural Language Processing.  A free online book is available.
(If you use the library for academic research, please cite the book.)

Steven Bird, Ewan Klein, and Edward Loper (2009).
Natural Language Processing with Python.  O'Reilly Media Inc.
https://www.nltk.org/book/

isort:skip_file
"""

import os

# //////////////////////////////////////////////////////
# Metadata
# //////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# in the file VERSION.
try:
    # If a VERSION file exists, use it!
    version_file = os.path.join(os.path.dirname(__file__), "VERSION")
    with open(version_file) as infile:
        __version__ = infile.read().strip()
except NameError:
    __version__ = "unknown (running code interactively?)"
except OSError as ex:
    __version__ = "unknown (%s)" % ex

if __doc__ is not None:  # fix for the ``python -OO``
    __doc__ += "\n@version: " + __version__


# Copyright notice
__copyright__ = """\
Copyright (C) 2001-2024 NLTK Project.

Distributed and Licensed under the Apache License, Version 2.0,
which is included by reference.
"""

__license__ = "Apache License, Version 2.0"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Language Toolkit (NLTK) is a Python package for
natural language processing.  NLTK requires Python 3.8, 3.9, 3.10, 3.11 or 3.12."""
__keywords__ = [
    "NLP",
    "CL",
    "natural language processing",
    "computational linguistics",
    "parsing",
    "tagging",
    "tokenizing",
    "syntax",
    "linguistics",
    "language",
    "natural language",
    "text analytics",
]
__url__ = "https://www.nltk.org/"

# Maintainer, contributors, etc.
__maintainer__ = "NLTK Team"
__maintainer_email__ = "nltk.team@gmail.com"
__author__ = __maintainer__
__author_email__ = __maintainer_email__

# "Trove" classifiers for Python Package Index.
__classifiers__ = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Scientific/Engineering :: Human Machine Interfaces",
    "Topic :: Scientific/Engineering :: Information Analysis",
    "Topic :: Text Processing",
    "Topic :: Text Processing :: Filters",
    "Topic :: Text Processing :: General",
    "Topic :: Text Processing :: Indexing",
    "Topic :: Text Processing :: Linguistic",
]

from nltk.internals import config_java

# support numpy from pypy
try:
    import numpypy
except ImportError:
    pass

# Override missing methods on environments where it cannot be used like GAE.
import subprocess

if not hasattr(subprocess, "PIPE"):

    def _fake_PIPE(*args, **kwargs):
        raise NotImplementedError("subprocess.PIPE is not supported.")

    subprocess.PIPE = _fake_PIPE
if not hasattr(subprocess, "Popen"):

    def _fake_Popen(*args, **kwargs):
        raise NotImplementedError("subprocess.Popen is not supported.")

    subprocess.Popen = _fake_Popen

###########################################################
# TOP-LEVEL MODULES
###########################################################

# Import top-level functionality into top-level namespace

from nltk.collocations import *
from nltk.decorators import decorator, memoize
from nltk.featstruct import *
from nltk.grammar import *
from nltk.probability import *
from nltk.text import *
from nltk.util import *
from nltk.jsontags import *

###########################################################
# PACKAGES
###########################################################

from nltk.chunk import *
from nltk.classify import *
from nltk.inference import *
from nltk.metrics import *
from nltk.parse import *
from nltk.tag import *
from nltk.tokenize import *
from nltk.translate import *
from nltk.tree import *
from nltk.sem import *
from nltk.stem import *

# Packages which can be lazily imported
# (a) we don't import *
# (b) they're slow to import or have run-time dependencies
#     that can safely fail at run time

from nltk import lazyimport

app = lazyimport.LazyModule("app", locals(), globals())
chat = lazyimport.LazyModule("chat", locals(), globals())
corpus = lazyimport.LazyModule("corpus", locals(), globals())
draw = lazyimport.LazyModule("draw", locals(), globals())
toolbox = lazyimport.LazyModule("toolbox", locals(), globals())

# Optional loading

try:
    import numpy
except ImportError:
    pass
else:
    from nltk import cluster

from nltk.downloader import download, download_shell

try:
    import tkinter
except ImportError:
    pass
else:
    try:
        from nltk.downloader import download_gui
    except RuntimeError as e:
        import warnings

        warnings.warn(
            "Corpus downloader GUI not loaded "
            "(RuntimeError during import: %s)" % str(e)
        )

# explicitly import all top-level modules (ensuring
# they override the same names inadvertently imported
# from a subpackage)

from nltk import ccg, chunk, classify, collocations
from nltk import data, featstruct, grammar, help, inference, metrics
from nltk import misc, parse, probability, sem, stem, wsd
from nltk import tag, tbl, text, tokenize, translate, tree, util


# FIXME:  override any accidentally imported demo, see https://github.com/nltk/nltk/issues/2116
def demo():
    print("To run the demo code for a module, type nltk.module.demo()")

# === NexusCore/openenv\Lib\site-packages\xmod\__init__.py ===
"""
# 🌱 Turn any object into a module 🌱

Callable modules!  Indexable modules!?

Ever wanted to call a module directly, or index it?  Or just sick of seeing
`from foo import foo` in your examples?

Give your module the awesome power of an object, or maybe just save a
little typing, with `xmod`.

`xmod` is a tiny library that lets a module to do things that normally
only a class could do - handy for modules that "just do one thing".

## Example: Make a module callable like a function!

    # In your_module.py
    import xmod

    @xmod
    def a_function():
        return 'HERE!!'


    # Test at the command line
    >>> import your_module
    >>> your_module()
    HERE!!

## Example: Make a module look like a list!?!

    # In your_module.py
    import xmod

    xmod(list(), __name__)

    # Test at the command line
    >>> import your_module
    >>> assert your_module == []
    >>> your_module.extend(range(3))
    >>> print(your_module)
    [0, 1, 2]
"""
__all__ = ('xmod',)

import functools
import sys
import typing as t

_OMIT = {
    '__class__',
    '__getattr__',
    '__getattribute__',
    '__init__',
    '__init_subclass__',
    '__new__',
    '__setattr__',
}

_EXTENSION_ATTRIBUTE = '_xmod_extension'
_WRAPPED_ATTRIBUTE = '_xmod_wrapped'


def xmod(
    extension: t.Any = None,
    name: t.Optional[str] = None,
    full: t.Optional[bool] = None,
    omit: t.Optional[t.Sequence[str]] = None,
    mutable: bool = False,
) -> t.Any:
    """
    Extend the system module at `name` with any Python object.

    The original module is replaced in `sys.modules` by a proxy class
    which delegates attributes to the original module, and then adds
    attributes from the extension.

    In the most common use case, the extension is a callable and only the
    `__call__` method is delegated, so `xmod` can also be used as a
    decorator, both with and without parameters.

    Args:
      extension: The object whose methods and properties extend the namespace.
        This includes magic methods like __call__ and __getitem__.

      name: The name of this symbol in `sys.modules`.  If this is `None`
        then `xmod` will use `extension.__module__`.

        This only needs to be be set if `extension` is _not_ a function or
        class defined in the module that's being extended.

        If the `name` argument is given, it should almost certainly be
        `__name__`.

      full: If `False`, just add extension as a callable.

        If `True`, extend the module with all members of `extension`.

        If `None`, the default, add the extension if it's a callable, otherwise
        extend the module with all members of `extension`.

      mutable: If `True`, the attributes on the proxy are mutable and write
        through to the underlying module.  If `False`, the default, attributes
        on the proxy cannot be changed.

      omit: A list of methods _not_ to delegate from the proxy to the extension

        If `omit` is None, it defaults to `xmod._OMIT`, which seems to
        work well.

    Returns:
        `extension`, the original item that got decorated
    """
    if extension is None:
        # It's a decorator with properties
        return functools.partial(
            xmod, name=name, full=full, omit=omit, mutable=mutable
        )

    def method(f) -> t.Callable:
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            return f(*args, **kwargs)

        return wrapped

    def mutator(f) -> t.Callable:
        def fail(*args, **kwargs):
            raise TypeError(f'Class is immutable {args} {kwargs}')

        return method(f) if mutable else fail

    def prop(k) -> property:
        return property(
            method(lambda: getattr(extension, k)),
            mutator(lambda v: setattr(extension, k, v)),
            mutator(lambda: delattr(extension, k)),
        )

    name = name or getattr(extension, '__module__', None)
    if not name:
        raise ValueError('`name` parameter must be set')

    module = sys.modules[name]

    def _getattr(k) -> t.Any:
        try:
            return getattr(extension, k)
        except AttributeError:
            return getattr(module, k)

    def _setattr(k, v) -> None:
        if hasattr(extension, k):
            setattr(extension, k, v)
        else:
            setattr(module, k, v)

    def _delattr(k) -> None:
        success = True
        try:
            delattr(extension, k)
        except AttributeError:
            success = False
        try:
            delattr(module, k)
        except AttributeError:
            if not success:
                raise

    members = {
        _WRAPPED_ATTRIBUTE: module,
        '__getattr__': method(_getattr),
        '__setattr__': mutator(_setattr),
        '__delattr__': mutator(_delattr),
        '__doc__': getattr(module, '__doc__'),
    }

    if callable(extension):
        members['__call__'] = method(extension)
        members[_EXTENSION_ATTRIBUTE] = staticmethod(extension)

    elif full is False:
        raise ValueError('extension must be callable if full is False')

    else:
        members[_EXTENSION_ATTRIBUTE] = extension
        full = True

    om = _OMIT if omit is None else set(omit)
    for a in dir(extension) if full else ():
        if a not in om:
            value = getattr(extension, a)
            is_magic = a.startswith('__') and callable(value)
            if is_magic:
                members[a] = method(value)
            elif False:  # TODO: enable or delete this
                members[a] = prop(a)

    def directory(self) -> t.List:
        return sorted(set(members).union(dir(module)))

    members['__dir__'] = directory

    proxy_class = type(name, (object,), members)
    sys.modules[name] = proxy_class()
    return extension


xmod(xmod)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\gradual\conversion.py ===
from jedi import debug
from jedi.inference.base_value import ValueSet, \
    NO_VALUES
from jedi.inference.utils import to_list
from jedi.inference.gradual.stub_value import StubModuleValue
from jedi.inference.gradual.typeshed import try_to_load_stub_cached
from jedi.inference.value.decorator import Decoratee


def _stub_to_python_value_set(stub_value, ignore_compiled=False):
    stub_module_context = stub_value.get_root_context()
    if not stub_module_context.is_stub():
        return ValueSet([stub_value])

    decorates = None
    if isinstance(stub_value, Decoratee):
        decorates = stub_value._original_value

    was_instance = stub_value.is_instance()
    if was_instance:
        arguments = getattr(stub_value, '_arguments', None)
        stub_value = stub_value.py__class__()

    qualified_names = stub_value.get_qualified_names()
    if qualified_names is None:
        return NO_VALUES

    was_bound_method = stub_value.is_bound_method()
    if was_bound_method:
        # Infer the object first. We can infer the method later.
        method_name = qualified_names[-1]
        qualified_names = qualified_names[:-1]
        was_instance = True
        arguments = None

    values = _infer_from_stub(stub_module_context, qualified_names, ignore_compiled)
    if was_instance:
        values = ValueSet.from_sets(
            c.execute_with_values() if arguments is None else c.execute(arguments)
            for c in values
            if c.is_class()
        )
    if was_bound_method:
        # Now that the instance has been properly created, we can simply get
        # the method.
        values = values.py__getattribute__(method_name)
    if decorates is not None:
        values = ValueSet(Decoratee(v, decorates) for v in values)
    return values


def _infer_from_stub(stub_module_context, qualified_names, ignore_compiled):
    from jedi.inference.compiled.mixed import MixedObject
    stub_module = stub_module_context.get_value()
    assert isinstance(stub_module, (StubModuleValue, MixedObject)), stub_module_context
    non_stubs = stub_module.non_stub_value_set
    if ignore_compiled:
        non_stubs = non_stubs.filter(lambda c: not c.is_compiled())
    for name in qualified_names:
        non_stubs = non_stubs.py__getattribute__(name)
    return non_stubs


@to_list
def _try_stub_to_python_names(names, prefer_stub_to_compiled=False):
    for name in names:
        module_context = name.get_root_context()
        if not module_context.is_stub():
            yield name
            continue

        if name.api_type == 'module':
            values = convert_values(name.infer(), ignore_compiled=prefer_stub_to_compiled)
            if values:
                for v in values:
                    yield v.name
                continue
        else:
            v = name.get_defining_qualified_value()
            if v is not None:
                converted = _stub_to_python_value_set(v, ignore_compiled=prefer_stub_to_compiled)
                if converted:
                    converted_names = converted.goto(name.get_public_name())
                    if converted_names:
                        for n in converted_names:
                            if n.get_root_context().is_stub():
                                # If it's a stub again, it means we're going in
                                # a circle. Probably some imports make it a
                                # stub again.
                                yield name
                            else:
                                yield n
                        continue
        yield name


def _load_stub_module(module):
    if module.is_stub():
        return module
    return try_to_load_stub_cached(
        module.inference_state,
        import_names=module.string_names,
        python_value_set=ValueSet([module]),
        parent_module_value=None,
        sys_path=module.inference_state.get_sys_path(),
    )


@to_list
def _python_to_stub_names(names, fallback_to_python=False):
    for name in names:
        module_context = name.get_root_context()
        if module_context.is_stub():
            yield name
            continue

        if name.api_type == 'module':
            found_name = False
            for n in name.goto():
                if n.api_type == 'module':
                    values = convert_values(n.infer(), only_stubs=True)
                    for v in values:
                        yield v.name
                        found_name = True
                else:
                    for x in _python_to_stub_names([n], fallback_to_python=fallback_to_python):
                        yield x
                        found_name = True
            if found_name:
                continue
        else:
            v = name.get_defining_qualified_value()
            if v is not None:
                converted = to_stub(v)
                if converted:
                    converted_names = converted.goto(name.get_public_name())
                    if converted_names:
                        yield from converted_names
                        continue
        if fallback_to_python:
            # This is the part where if we haven't found anything, just return
            # the stub name.
            yield name


def convert_names(names, only_stubs=False, prefer_stubs=False, prefer_stub_to_compiled=True):
    if only_stubs and prefer_stubs:
        raise ValueError("You cannot use both of only_stubs and prefer_stubs.")

    with debug.increase_indent_cm('convert names'):
        if only_stubs or prefer_stubs:
            return _python_to_stub_names(names, fallback_to_python=prefer_stubs)
        else:
            return _try_stub_to_python_names(
                names, prefer_stub_to_compiled=prefer_stub_to_compiled)


def convert_values(values, only_stubs=False, prefer_stubs=False, ignore_compiled=True):
    assert not (only_stubs and prefer_stubs)
    with debug.increase_indent_cm('convert values'):
        if only_stubs or prefer_stubs:
            return ValueSet.from_sets(
                to_stub(value)
                or (ValueSet({value}) if prefer_stubs else NO_VALUES)
                for value in values
            )
        else:
            return ValueSet.from_sets(
                _stub_to_python_value_set(stub_value, ignore_compiled=ignore_compiled)
                or ValueSet({stub_value})
                for stub_value in values
            )


def to_stub(value):
    if value.is_stub():
        return ValueSet([value])

    was_instance = value.is_instance()
    if was_instance:
        value = value.py__class__()

    qualified_names = value.get_qualified_names()
    stub_module = _load_stub_module(value.get_root_context().get_value())
    if stub_module is None or qualified_names is None:
        return NO_VALUES

    was_bound_method = value.is_bound_method()
    if was_bound_method:
        # Infer the object first. We can infer the method later.
        method_name = qualified_names[-1]
        qualified_names = qualified_names[:-1]
        was_instance = True

    stub_values = ValueSet([stub_module])
    for name in qualified_names:
        stub_values = stub_values.py__getattribute__(name)

    if was_instance:
        stub_values = ValueSet.from_sets(
            c.execute_with_values()
            for c in stub_values
            if c.is_class()
        )
    if was_bound_method:
        # Now that the instance has been properly created, we can simply get
        # the method.
        stub_values = stub_values.py__getattribute__(method_name)
    return stub_values

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\messages\invoke_transformations\anthropic_claude3_transformation.py ===
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import httpx

from litellm.llms.anthropic.experimental_pass_through.messages.transformation import (
    AnthropicMessagesConfig,
)
from litellm.llms.base_llm.anthropic_messages.transformation import (
    BaseAnthropicMessagesConfig,
)
from litellm.llms.bedrock.chat.invoke_handler import AWSEventStreamDecoder
from litellm.llms.bedrock.chat.invoke_transformations.base_invoke_transformation import (
    AmazonInvokeConfig,
)
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import GenericStreamingChunk
from litellm.types.utils import GenericStreamingChunk as GChunk
from litellm.types.utils import ModelResponseStream

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class AmazonAnthropicClaude3MessagesConfig(
    AnthropicMessagesConfig,
    AmazonInvokeConfig,
):
    """
    Call Claude model family in the /v1/messages API spec
    """

    DEFAULT_BEDROCK_ANTHROPIC_API_VERSION = "bedrock-2023-05-31"

    def __init__(self, **kwargs):
        BaseAnthropicMessagesConfig.__init__(self, **kwargs)
        AmazonInvokeConfig.__init__(self, **kwargs)

    def validate_anthropic_messages_environment(
        self,
        headers: dict,
        model: str,
        messages: List[Any],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Tuple[dict, Optional[str]]:
        return headers, api_base

    def sign_request(
        self,
        headers: dict,
        optional_params: dict,
        request_data: dict,
        api_base: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        fake_stream: Optional[bool] = None,
    ) -> Tuple[dict, Optional[bytes]]:
        return AmazonInvokeConfig.sign_request(
            self=self,
            headers=headers,
            optional_params=optional_params,
            request_data=request_data,
            api_base=api_base,
            model=model,
            stream=stream,
            fake_stream=fake_stream,
        )

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        return AmazonInvokeConfig.get_complete_url(
            self=self,
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=optional_params,
            litellm_params=litellm_params,
            stream=stream,
        )

    def transform_anthropic_messages_request(
        self,
        model: str,
        messages: List[Dict],
        anthropic_messages_optional_request_params: Dict,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Dict:
        anthropic_messages_request = AnthropicMessagesConfig.transform_anthropic_messages_request(
            self=self,
            model=model,
            messages=messages,
            anthropic_messages_optional_request_params=anthropic_messages_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        #########################################################
        ############## BEDROCK Invoke SPECIFIC TRANSFORMATION ###
        #########################################################

        # 1. anthropic_version is required for all claude models
        if "anthropic_version" not in anthropic_messages_request:
            anthropic_messages_request["anthropic_version"] = (
                self.DEFAULT_BEDROCK_ANTHROPIC_API_VERSION
            )

        # 2. `stream` is not allowed in request body for bedrock invoke
        if "stream" in anthropic_messages_request:
            anthropic_messages_request.pop("stream", None)

        # 3. `model` is not allowed in request body for bedrock invoke
        if "model" in anthropic_messages_request:
            anthropic_messages_request.pop("model", None)
        return anthropic_messages_request

    def get_async_streaming_response_iterator(
        self,
        model: str,
        httpx_response: httpx.Response,
        request_body: dict,
        litellm_logging_obj: LiteLLMLoggingObj,
    ) -> AsyncIterator:
        aws_decoder = AmazonAnthropicClaudeMessagesStreamDecoder(
            model=model,
        )
        completion_stream = aws_decoder.aiter_bytes(
            httpx_response.aiter_bytes(chunk_size=aws_decoder.DEFAULT_CHUNK_SIZE)
        )
        # Convert decoded Bedrock events to Server-Sent Events expected by Anthropic clients.
        return self.bedrock_sse_wrapper(
            completion_stream=completion_stream, 
            litellm_logging_obj=litellm_logging_obj,
            request_body=request_body,
        )

    async def bedrock_sse_wrapper(
        self,
        completion_stream: AsyncIterator[
            Union[bytes, GenericStreamingChunk, ModelResponseStream, dict]
        ],
        litellm_logging_obj: LiteLLMLoggingObj,
        request_body: dict,
    ):
        """
        Bedrock invoke does not return SSE formatted data. This function is a wrapper to ensure litellm chunks are SSE formatted.
        """
        from litellm.llms.anthropic.experimental_pass_through.messages.streaming_iterator import (
            BaseAnthropicMessagesStreamingIterator,
        )
        handler = BaseAnthropicMessagesStreamingIterator(
            litellm_logging_obj=litellm_logging_obj,
            request_body=request_body,
        )
        
        async for chunk in handler.async_sse_wrapper(completion_stream):
            yield chunk
        


class AmazonAnthropicClaudeMessagesStreamDecoder(AWSEventStreamDecoder):
    def __init__(
        self,
        model: str,
    ) -> None:
        """
        Iterator to return Bedrock invoke response in anthropic /messages format
        """
        super().__init__(model=model)
        self.DEFAULT_CHUNK_SIZE = 1024

    def _chunk_parser(
        self, chunk_data: dict
    ) -> Union[GChunk, ModelResponseStream, dict]:
        """
        Parse the chunk data into anthropic /messages format

        Bedrock returns usage metrics using camelCase keys. Convert these to
        the Anthropic `/v1/messages` specification so callers receive a
        consistent response shape when streaming.
        """
        amazon_bedrock_invocation_metrics = chunk_data.pop(
            "amazon-bedrock-invocationMetrics", {}
        )
        if amazon_bedrock_invocation_metrics:
            anthropic_usage = {}
            if "inputTokenCount" in amazon_bedrock_invocation_metrics:
                anthropic_usage["input_tokens"] = amazon_bedrock_invocation_metrics[
                    "inputTokenCount"
                ]
            if "outputTokenCount" in amazon_bedrock_invocation_metrics:
                anthropic_usage["output_tokens"] = amazon_bedrock_invocation_metrics[
                    "outputTokenCount"
                ]
            chunk_data["usage"] = anthropic_usage
        return chunk_data

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\user_management_event_hooks.py ===
"""
Hooks that are triggered when a litellm user event occurs
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    AUDIT_ACTIONS,
    CommonProxyErrors,
    LiteLLM_AuditLogs,
    Litellm_EntityType,
    LiteLLM_UserTable,
    LitellmTableNames,
    NewUserRequest,
    NewUserResponse,
    UserAPIKeyAuth,
    WebhookEvent,
)
from litellm.proxy.management_helpers.audit_logs import create_audit_log_for_update


class UserManagementEventHooks:
    @staticmethod
    async def async_user_created_hook(
        data: NewUserRequest,
        response: NewUserResponse,
        user_api_key_dict: UserAPIKeyAuth,
    ):
        """
        This hook is called when a new user is created on litellm

        Handles:
        - Creating an audit log for the user creation
        - Sending a user invitation email to the user
        """
        from litellm.proxy.proxy_server import litellm_proxy_admin_name, prisma_client

        #########################################################
        ########## Send User Invitation Email ################
        #########################################################
        await UserManagementEventHooks.async_send_user_invitation_email(
            data=data,
            response=response,
            user_api_key_dict=user_api_key_dict,
        )

        #########################################################
        ########## CREATE AUDIT LOG ################
        #########################################################
        try:
            if prisma_client is None:
                raise Exception(CommonProxyErrors.db_not_connected_error.value)
            user_row: BaseModel = await prisma_client.db.litellm_usertable.find_first(
                where={"user_id": response.user_id}
            )

            user_row_litellm_typed = LiteLLM_UserTable(
                **user_row.model_dump(exclude_none=True)
            )
            asyncio.create_task(
                UserManagementEventHooks.create_internal_user_audit_log(
                    user_id=user_row_litellm_typed.user_id,
                    action="created",
                    litellm_changed_by=user_api_key_dict.user_id,
                    user_api_key_dict=user_api_key_dict,
                    litellm_proxy_admin_name=litellm_proxy_admin_name,
                    before_value=None,
                    after_value=user_row_litellm_typed.model_dump_json(
                        exclude_none=True
                    ),
                )
            )
        except Exception as e:
            verbose_proxy_logger.warning(
                "Unable to create audit log for user on `/user/new` - {}".format(str(e))
            )
        pass

    @staticmethod
    async def async_send_user_invitation_email(
        data: NewUserRequest,
        response: NewUserResponse,
        user_api_key_dict: UserAPIKeyAuth,
    ):
        """
        Send a user invitation email to the user
        """
        event = WebhookEvent(
            event="internal_user_created",
            event_group=Litellm_EntityType.USER,
            event_message="Welcome to LiteLLM Proxy",
            token=response.token,
            spend=response.spend or 0.0,
            max_budget=response.max_budget,
            user_id=response.user_id,
            user_email=response.user_email,
            team_id=response.team_id,
            key_alias=response.key_alias,
        )

        #########################################################
        ########## V2 USER INVITATION EMAIL ################
        #########################################################
        try:
            from litellm_enterprise.enterprise_callbacks.send_emails.base_email import (
                BaseEmailLogger,
            )

            use_enterprise_email_hooks = True
        except ImportError:
            verbose_proxy_logger.warning(
                "Defaulting to using Legacy Email Hooks."
                + CommonProxyErrors.missing_enterprise_package.value
            )
            use_enterprise_email_hooks = False

        if use_enterprise_email_hooks:
            initialized_email_loggers = litellm.logging_callback_manager.get_custom_loggers_for_type(
                callback_type=BaseEmailLogger  # type: ignore
            )
            if len(initialized_email_loggers) > 0:
                for email_logger in initialized_email_loggers:
                    if isinstance(email_logger, BaseEmailLogger):  # type: ignore
                        await email_logger.send_user_invitation_email(  # type: ignore
                            event=event,
                        )

        #########################################################
        ########## LEGACY V1 USER INVITATION EMAIL ################
        #########################################################
        if data.send_invite_email is True:
            await UserManagementEventHooks.send_legacy_v1_user_invitation_email(
                data=data,
                response=response,
                user_api_key_dict=user_api_key_dict,
                event=event,
            )

    @staticmethod
    async def send_legacy_v1_user_invitation_email(
        data: NewUserRequest,
        response: NewUserResponse,
        user_api_key_dict: UserAPIKeyAuth,
        event: WebhookEvent,
    ):
        """
        Send a user invitation email to the user
        """
        from litellm.proxy.proxy_server import general_settings, proxy_logging_obj

        # check if user has setup email alerting
        if "email" not in general_settings.get("alerting", []):
            raise ValueError(
                "Email alerting not setup on config.yaml. Please set `alerting=['email']. \nDocs: https://docs.litellm.ai/docs/proxy/email`"
            )

        # If user configured email alerting - send an Email letting their end-user know the key was created
        asyncio.create_task(
            proxy_logging_obj.slack_alerting_instance.send_key_created_or_user_invited_email(
                webhook_event=event,
            )
        )

    @staticmethod
    async def create_internal_user_audit_log(
        user_id: str,
        action: AUDIT_ACTIONS,
        litellm_changed_by: Optional[str],
        user_api_key_dict: UserAPIKeyAuth,
        litellm_proxy_admin_name: Optional[str],
        before_value: Optional[str] = None,
        after_value: Optional[str] = None,
    ):
        """
        Create an audit log for an internal user.

        Parameters:
        - user_id: str - The id of the user to create the audit log for.
        - action: AUDIT_ACTIONS - The action to create the audit log for.
        - user_row: LiteLLM_UserTable - The user row to create the audit log for.
        - litellm_changed_by: Optional[str] - The user id of the user who is changing the user.
        - user_api_key_dict: UserAPIKeyAuth - The user api key dictionary.
        - litellm_proxy_admin_name: Optional[str] - The name of the proxy admin.
        """
        if not litellm.store_audit_logs:
            return

        await create_audit_log_for_update(
            request_data=LiteLLM_AuditLogs(
                id=str(uuid.uuid4()),
                updated_at=datetime.now(timezone.utc),
                changed_by=litellm_changed_by
                or user_api_key_dict.user_id
                or litellm_proxy_admin_name,
                changed_by_api_key=user_api_key_dict.api_key,
                table_name=LitellmTableNames.USER_TABLE_NAME,
                object_id=user_id,
                action=action,
                updated_values=after_value,
                before_value=before_value,
            )
        )

# === NexusCore/openenv\Lib\site-packages\nltk\stem\cistem.py ===
# Natural Language Toolkit: CISTEM Stemmer for German
# Copyright (C) 2001-2024 NLTK Project
# Author: Leonie Weissweiler <l.weissweiler@outlook.de>
#         Tom Aarsen <> (modifications)
# Algorithm: Leonie Weissweiler <l.weissweiler@outlook.de>
#            Alexander Fraser <fraser@cis.lmu.de>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
from typing import Tuple

from nltk.stem.api import StemmerI


class Cistem(StemmerI):
    """
    CISTEM Stemmer for German

    This is the official Python implementation of the CISTEM stemmer.
    It is based on the paper
    Leonie Weissweiler, Alexander Fraser (2017). Developing a Stemmer for German
    Based on a Comparative Analysis of Publicly Available Stemmers.
    In Proceedings of the German Society for Computational Linguistics and Language
    Technology (GSCL)
    which can be read here:
    https://www.cis.lmu.de/~weissweiler/cistem/

    In the paper, we conducted an analysis of publicly available stemmers,
    developed two gold standards for German stemming and evaluated the stemmers
    based on the two gold standards. We then proposed the stemmer implemented here
    and show that it achieves slightly better f-measure than the other stemmers and
    is thrice as fast as the Snowball stemmer for German while being about as fast
    as most other stemmers.

    case_insensitive is a a boolean specifying if case-insensitive stemming
    should be used. Case insensitivity improves performance only if words in the
    text may be incorrectly upper case. For all-lowercase and correctly cased
    text, best performance is achieved by setting case_insensitive for false.

    :param case_insensitive: if True, the stemming is case insensitive. False by default.
    :type case_insensitive: bool
    """

    strip_ge = re.compile(r"^ge(.{4,})")
    repl_xx = re.compile(r"(.)\1")
    strip_emr = re.compile(r"e[mr]$")
    strip_nd = re.compile(r"nd$")
    strip_t = re.compile(r"t$")
    strip_esn = re.compile(r"[esn]$")
    repl_xx_back = re.compile(r"(.)\*")

    def __init__(self, case_insensitive: bool = False):
        self._case_insensitive = case_insensitive

    @staticmethod
    def replace_to(word: str) -> str:
        word = word.replace("sch", "$")
        word = word.replace("ei", "%")
        word = word.replace("ie", "&")
        word = Cistem.repl_xx.sub(r"\1*", word)

        return word

    @staticmethod
    def replace_back(word: str) -> str:
        word = Cistem.repl_xx_back.sub(r"\1\1", word)
        word = word.replace("%", "ei")
        word = word.replace("&", "ie")
        word = word.replace("$", "sch")

        return word

    def stem(self, word: str) -> str:
        """Stems the input word.

        :param word: The word that is to be stemmed.
        :type word: str
        :return: The stemmed word.
        :rtype: str

        >>> from nltk.stem.cistem import Cistem
        >>> stemmer = Cistem()
        >>> s1 = "Speicherbehältern"
        >>> stemmer.stem(s1)
        'speicherbehalt'
        >>> s2 = "Grenzpostens"
        >>> stemmer.stem(s2)
        'grenzpost'
        >>> s3 = "Ausgefeiltere"
        >>> stemmer.stem(s3)
        'ausgefeilt'
        >>> stemmer = Cistem(True)
        >>> stemmer.stem(s1)
        'speicherbehal'
        >>> stemmer.stem(s2)
        'grenzpo'
        >>> stemmer.stem(s3)
        'ausgefeil'
        """
        if len(word) == 0:
            return word

        upper = word[0].isupper()
        word = word.lower()

        word = word.replace("ü", "u")
        word = word.replace("ö", "o")
        word = word.replace("ä", "a")
        word = word.replace("ß", "ss")

        word = Cistem.strip_ge.sub(r"\1", word)

        return self._segment_inner(word, upper)[0]

    def segment(self, word: str) -> Tuple[str, str]:
        """
        This method works very similarly to stem (:func:'cistem.stem'). The difference is that in
        addition to returning the stem, it also returns the rest that was removed at
        the end. To be able to return the stem unchanged so the stem and the rest
        can be concatenated to form the original word, all subsitutions that altered
        the stem in any other way than by removing letters at the end were left out.

        :param word: The word that is to be stemmed.
        :type word: str
        :return: A tuple of the stemmed word and the removed suffix.
        :rtype: Tuple[str, str]

        >>> from nltk.stem.cistem import Cistem
        >>> stemmer = Cistem()
        >>> s1 = "Speicherbehältern"
        >>> stemmer.segment(s1)
        ('speicherbehält', 'ern')
        >>> s2 = "Grenzpostens"
        >>> stemmer.segment(s2)
        ('grenzpost', 'ens')
        >>> s3 = "Ausgefeiltere"
        >>> stemmer.segment(s3)
        ('ausgefeilt', 'ere')
        >>> stemmer = Cistem(True)
        >>> stemmer.segment(s1)
        ('speicherbehäl', 'tern')
        >>> stemmer.segment(s2)
        ('grenzpo', 'stens')
        >>> stemmer.segment(s3)
        ('ausgefeil', 'tere')
        """
        if len(word) == 0:
            return ("", "")

        upper = word[0].isupper()
        word = word.lower()

        return self._segment_inner(word, upper)

    def _segment_inner(self, word: str, upper: bool):
        """Inner method for iteratively applying the code stemming regexes.
        This method receives a pre-processed variant of the word to be stemmed,
        or the word to be segmented, and returns a tuple of the word and the
        removed suffix.

        :param word: A pre-processed variant of the word that is to be stemmed.
        :type word: str
        :param upper: Whether the original word started with a capital letter.
        :type upper: bool
        :return: A tuple of the stemmed word and the removed suffix.
        :rtype: Tuple[str, str]
        """

        rest_length = 0
        word_copy = word[:]

        # Pre-processing before applying the substitution patterns
        word = Cistem.replace_to(word)
        rest = ""

        # Apply the substitution patterns
        while len(word) > 3:
            if len(word) > 5:
                word, n = Cistem.strip_emr.subn("", word)
                if n != 0:
                    rest_length += 2
                    continue

                word, n = Cistem.strip_nd.subn("", word)
                if n != 0:
                    rest_length += 2
                    continue

            if not upper or self._case_insensitive:
                word, n = Cistem.strip_t.subn("", word)
                if n != 0:
                    rest_length += 1
                    continue

            word, n = Cistem.strip_esn.subn("", word)
            if n != 0:
                rest_length += 1
                continue
            else:
                break

        # Post-processing after applying the substitution patterns
        word = Cistem.replace_back(word)

        if rest_length:
            rest = word_copy[-rest_length:]

        return (word, rest)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\telnet\protocol.py ===
"""
Parser for the Telnet protocol. (Not a complete implementation of the telnet
specification, but sufficient for a command line interface.)

Inspired by `Twisted.conch.telnet`.
"""

from __future__ import annotations

import struct
from typing import Callable, Generator

from .log import logger

__all__ = [
    "TelnetProtocolParser",
]


def int2byte(number: int) -> bytes:
    return bytes((number,))


# Telnet constants.
NOP = int2byte(0)
SGA = int2byte(3)

IAC = int2byte(255)
DO = int2byte(253)
DONT = int2byte(254)
LINEMODE = int2byte(34)
SB = int2byte(250)
WILL = int2byte(251)
WONT = int2byte(252)
MODE = int2byte(1)
SE = int2byte(240)
ECHO = int2byte(1)
NAWS = int2byte(31)
LINEMODE = int2byte(34)
SUPPRESS_GO_AHEAD = int2byte(3)

TTYPE = int2byte(24)
SEND = int2byte(1)
IS = int2byte(0)

DM = int2byte(242)
BRK = int2byte(243)
IP = int2byte(244)
AO = int2byte(245)
AYT = int2byte(246)
EC = int2byte(247)
EL = int2byte(248)
GA = int2byte(249)


class TelnetProtocolParser:
    """
    Parser for the Telnet protocol.
    Usage::

        def data_received(data):
            print(data)

        def size_received(rows, columns):
            print(rows, columns)

        p = TelnetProtocolParser(data_received, size_received)
        p.feed(binary_data)
    """

    def __init__(
        self,
        data_received_callback: Callable[[bytes], None],
        size_received_callback: Callable[[int, int], None],
        ttype_received_callback: Callable[[str], None],
    ) -> None:
        self.data_received_callback = data_received_callback
        self.size_received_callback = size_received_callback
        self.ttype_received_callback = ttype_received_callback

        self._parser = self._parse_coroutine()
        self._parser.send(None)  # type: ignore

    def received_data(self, data: bytes) -> None:
        self.data_received_callback(data)

    def do_received(self, data: bytes) -> None:
        """Received telnet DO command."""
        logger.info("DO %r", data)

    def dont_received(self, data: bytes) -> None:
        """Received telnet DONT command."""
        logger.info("DONT %r", data)

    def will_received(self, data: bytes) -> None:
        """Received telnet WILL command."""
        logger.info("WILL %r", data)

    def wont_received(self, data: bytes) -> None:
        """Received telnet WONT command."""
        logger.info("WONT %r", data)

    def command_received(self, command: bytes, data: bytes) -> None:
        if command == DO:
            self.do_received(data)

        elif command == DONT:
            self.dont_received(data)

        elif command == WILL:
            self.will_received(data)

        elif command == WONT:
            self.wont_received(data)

        else:
            logger.info("command received %r %r", command, data)

    def naws(self, data: bytes) -> None:
        """
        Received NAWS. (Window dimensions.)
        """
        if len(data) == 4:
            # NOTE: the first parameter of struct.unpack should be
            # a 'str' object. Both on Py2/py3. This crashes on OSX
            # otherwise.
            columns, rows = struct.unpack("!HH", data)
            self.size_received_callback(rows, columns)
        else:
            logger.warning("Wrong number of NAWS bytes")

    def ttype(self, data: bytes) -> None:
        """
        Received terminal type.
        """
        subcmd, data = data[0:1], data[1:]
        if subcmd == IS:
            ttype = data.decode("ascii")
            self.ttype_received_callback(ttype)
        else:
            logger.warning("Received a non-IS terminal type Subnegotiation")

    def negotiate(self, data: bytes) -> None:
        """
        Got negotiate data.
        """
        command, payload = data[0:1], data[1:]

        if command == NAWS:
            self.naws(payload)
        elif command == TTYPE:
            self.ttype(payload)
        else:
            logger.info("Negotiate (%r got bytes)", len(data))

    def _parse_coroutine(self) -> Generator[None, bytes, None]:
        """
        Parser state machine.
        Every 'yield' expression returns the next byte.
        """
        while True:
            d = yield

            if d == int2byte(0):
                pass  # NOP

            # Go to state escaped.
            elif d == IAC:
                d2 = yield

                if d2 == IAC:
                    self.received_data(d2)

                # Handle simple commands.
                elif d2 in (NOP, DM, BRK, IP, AO, AYT, EC, EL, GA):
                    self.command_received(d2, b"")

                # Handle IAC-[DO/DONT/WILL/WONT] commands.
                elif d2 in (DO, DONT, WILL, WONT):
                    d3 = yield
                    self.command_received(d2, d3)

                # Subnegotiation
                elif d2 == SB:
                    # Consume everything until next IAC-SE
                    data = []

                    while True:
                        d3 = yield

                        if d3 == IAC:
                            d4 = yield
                            if d4 == SE:
                                break
                            else:
                                data.append(d4)
                        else:
                            data.append(d3)

                    self.negotiate(b"".join(data))
            else:
                self.received_data(d)

    def feed(self, data: bytes) -> None:
        """
        Feed data to the parser.
        """
        for b in data:
            self._parser.send(int2byte(b))

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_schema_gather.py ===
# pyright: reportTypedDictNotRequiredAccess=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from pydantic_core.core_schema import ComputedField, CoreSchema, DefinitionReferenceSchema, SerSchema
from typing_extensions import TypeAlias

AllSchemas: TypeAlias = 'CoreSchema | SerSchema | ComputedField'


class GatherResult(TypedDict):
    """Schema traversing result."""

    collected_references: dict[str, DefinitionReferenceSchema | None]
    """The collected definition references.

    If a definition reference schema can be inlined, it means that there is
    only one in the whole core schema. As such, it is stored as the value.
    Otherwise, the value is set to `None`.
    """

    deferred_discriminator_schemas: list[CoreSchema]
    """The list of core schemas having the discriminator application deferred."""


class MissingDefinitionError(LookupError):
    """A reference was pointing to a non-existing core schema."""

    def __init__(self, schema_reference: str, /) -> None:
        self.schema_reference = schema_reference


@dataclass
class GatherContext:
    """The current context used during core schema traversing.

    Context instances should only be used during schema traversing.
    """

    definitions: dict[str, CoreSchema]
    """The available definitions."""

    deferred_discriminator_schemas: list[CoreSchema] = field(init=False, default_factory=list)
    """The list of core schemas having the discriminator application deferred.

    Internally, these core schemas have a specific key set in the core metadata dict.
    """

    collected_references: dict[str, DefinitionReferenceSchema | None] = field(init=False, default_factory=dict)
    """The collected definition references.

    If a definition reference schema can be inlined, it means that there is
    only one in the whole core schema. As such, it is stored as the value.
    Otherwise, the value is set to `None`.

    During schema traversing, definition reference schemas can be added as candidates, or removed
    (by setting the value to `None`).
    """


def traverse_metadata(schema: AllSchemas, ctx: GatherContext) -> None:
    meta = schema.get('metadata')
    if meta is not None and 'pydantic_internal_union_discriminator' in meta:
        ctx.deferred_discriminator_schemas.append(schema)  # pyright: ignore[reportArgumentType]


def traverse_definition_ref(def_ref_schema: DefinitionReferenceSchema, ctx: GatherContext) -> None:
    schema_ref = def_ref_schema['schema_ref']

    if schema_ref not in ctx.collected_references:
        definition = ctx.definitions.get(schema_ref)
        if definition is None:
            raise MissingDefinitionError(schema_ref)

        # The `'definition-ref'` schema was only encountered once, make it
        # a candidate to be inlined:
        ctx.collected_references[schema_ref] = def_ref_schema
        traverse_schema(definition, ctx)
        if 'serialization' in def_ref_schema:
            traverse_schema(def_ref_schema['serialization'], ctx)
        traverse_metadata(def_ref_schema, ctx)
    else:
        # The `'definition-ref'` schema was already encountered, meaning
        # the previously encountered schema (and this one) can't be inlined:
        ctx.collected_references[schema_ref] = None


def traverse_schema(schema: AllSchemas, context: GatherContext) -> None:
    # TODO When we drop 3.9, use a match statement to get better type checking and remove
    # file-level type ignore.
    # (the `'type'` could also be fetched in every `if/elif` statement, but this alters performance).
    schema_type = schema['type']

    if schema_type == 'definition-ref':
        traverse_definition_ref(schema, context)
        # `traverse_definition_ref` handles the possible serialization and metadata schemas:
        return
    elif schema_type == 'definitions':
        traverse_schema(schema['schema'], context)
        for definition in schema['definitions']:
            traverse_schema(definition, context)
    elif schema_type in {'list', 'set', 'frozenset', 'generator'}:
        if 'items_schema' in schema:
            traverse_schema(schema['items_schema'], context)
    elif schema_type == 'tuple':
        if 'items_schema' in schema:
            for s in schema['items_schema']:
                traverse_schema(s, context)
    elif schema_type == 'dict':
        if 'keys_schema' in schema:
            traverse_schema(schema['keys_schema'], context)
        if 'values_schema' in schema:
            traverse_schema(schema['values_schema'], context)
    elif schema_type == 'union':
        for choice in schema['choices']:
            if isinstance(choice, tuple):
                traverse_schema(choice[0], context)
            else:
                traverse_schema(choice, context)
    elif schema_type == 'tagged-union':
        for v in schema['choices'].values():
            traverse_schema(v, context)
    elif schema_type == 'chain':
        for step in schema['steps']:
            traverse_schema(step, context)
    elif schema_type == 'lax-or-strict':
        traverse_schema(schema['lax_schema'], context)
        traverse_schema(schema['strict_schema'], context)
    elif schema_type == 'json-or-python':
        traverse_schema(schema['json_schema'], context)
        traverse_schema(schema['python_schema'], context)
    elif schema_type in {'model-fields', 'typed-dict'}:
        if 'extras_schema' in schema:
            traverse_schema(schema['extras_schema'], context)
        if 'computed_fields' in schema:
            for s in schema['computed_fields']:
                traverse_schema(s, context)
        for s in schema['fields'].values():
            traverse_schema(s, context)
    elif schema_type == 'dataclass-args':
        if 'computed_fields' in schema:
            for s in schema['computed_fields']:
                traverse_schema(s, context)
        for s in schema['fields']:
            traverse_schema(s, context)
    elif schema_type == 'arguments':
        for s in schema['arguments_schema']:
            traverse_schema(s['schema'], context)
        if 'var_args_schema' in schema:
            traverse_schema(schema['var_args_schema'], context)
        if 'var_kwargs_schema' in schema:
            traverse_schema(schema['var_kwargs_schema'], context)
    elif schema_type == 'arguments-v3':
        for s in schema['arguments_schema']:
            traverse_schema(s['schema'], context)
    elif schema_type == 'call':
        traverse_schema(schema['arguments_schema'], context)
        if 'return_schema' in schema:
            traverse_schema(schema['return_schema'], context)
    elif schema_type == 'computed-field':
        traverse_schema(schema['return_schema'], context)
    elif schema_type == 'function-before':
        if 'schema' in schema:
            traverse_schema(schema['schema'], context)
        if 'json_schema_input_schema' in schema:
            traverse_schema(schema['json_schema_input_schema'], context)
    elif schema_type == 'function-plain':
        # TODO duplicate schema types for serializers and validators, needs to be deduplicated.
        if 'return_schema' in schema:
            traverse_schema(schema['return_schema'], context)
        if 'json_schema_input_schema' in schema:
            traverse_schema(schema['json_schema_input_schema'], context)
    elif schema_type == 'function-wrap':
        # TODO duplicate schema types for serializers and validators, needs to be deduplicated.
        if 'return_schema' in schema:
            traverse_schema(schema['return_schema'], context)
        if 'schema' in schema:
            traverse_schema(schema['schema'], context)
        if 'json_schema_input_schema' in schema:
            traverse_schema(schema['json_schema_input_schema'], context)
    else:
        if 'schema' in schema:
            traverse_schema(schema['schema'], context)

    if 'serialization' in schema:
        traverse_schema(schema['serialization'], context)
    traverse_metadata(schema, context)


def gather_schemas_for_cleaning(schema: CoreSchema, definitions: dict[str, CoreSchema]) -> GatherResult:
    """Traverse the core schema and definitions and return the necessary information for schema cleaning.

    During the core schema traversing, any `'definition-ref'` schema is:

    - Validated: the reference must point to an existing definition. If this is not the case, a
      `MissingDefinitionError` exception is raised.
    - Stored in the context: the actual reference is stored in the context. Depending on whether
      the `'definition-ref'` schema is encountered more that once, the schema itself is also
      saved in the context to be inlined (i.e. replaced by the definition it points to).
    """
    context = GatherContext(definitions)
    traverse_schema(schema, context)

    return {
        'collected_references': context.collected_references,
        'deferred_discriminator_schemas': context.deferred_discriminator_schemas,
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\testing.py ===
"""
    pygments.lexers.testing
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for testing languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups
from pygments.token import Comment, Keyword, Name, String, Number, Generic, Text

__all__ = ['GherkinLexer', 'TAPLexer']


class GherkinLexer(RegexLexer):
    """
    For Gherkin syntax.
    """
    name = 'Gherkin'
    aliases = ['gherkin', 'cucumber']
    filenames = ['*.feature']
    mimetypes = ['text/x-gherkin']
    url = 'https://cucumber.io/docs/gherkin'
    version_added = '1.2'

    feature_keywords = '^(기능|機能|功能|フィーチャ|خاصية|תכונה|Функціонал|Функционалност|Функционал|Фича|Особина|Могућност|Özellik|Właściwość|Tính năng|Trajto|Savybė|Požiadavka|Požadavek|Osobina|Ominaisuus|Omadus|OH HAI|Mogućnost|Mogucnost|Jellemző|Fīča|Funzionalità|Funktionalität|Funkcionalnost|Funkcionalitāte|Funcționalitate|Functionaliteit|Functionalitate|Funcionalitat|Funcionalidade|Fonctionnalité|Fitur|Feature|Egenskap|Egenskab|Crikey|Característica|Arwedd)(:)(.*)$'
    feature_element_keywords = '^(\\s*)(시나리오 개요|시나리오|배경|背景|場景大綱|場景|场景大纲|场景|劇本大綱|劇本|剧本大纲|剧本|テンプレ|シナリオテンプレート|シナリオテンプレ|シナリオアウトライン|シナリオ|سيناريو مخطط|سيناريو|الخلفية|תרחיש|תבנית תרחיש|רקע|Тарих|Сценарій|Сценарио|Сценарий структураси|Сценарий|Структура сценарію|Структура сценарија|Структура сценария|Скица|Рамка на сценарий|Пример|Предыстория|Предистория|Позадина|Передумова|Основа|Концепт|Контекст|Założenia|Wharrimean is|Tình huống|The thing of it is|Tausta|Taust|Tapausaihio|Tapaus|Szenariogrundriss|Szenario|Szablon scenariusza|Stsenaarium|Struktura scenarija|Skica|Skenario konsep|Skenario|Situācija|Senaryo taslağı|Senaryo|Scénář|Scénario|Schema dello scenario|Scenārijs pēc parauga|Scenārijs|Scenár|Scenaro|Scenariusz|Scenariul de şablon|Scenariul de sablon|Scenariu|Scenario Outline|Scenario Amlinellol|Scenario|Scenarijus|Scenarijaus šablonas|Scenarij|Scenarie|Rerefons|Raamstsenaarium|Primer|Pozadí|Pozadina|Pozadie|Plan du scénario|Plan du Scénario|Osnova scénáře|Osnova|Náčrt Scénáře|Náčrt Scenáru|Mate|MISHUN SRSLY|MISHUN|Kịch bản|Konturo de la scenaro|Kontext|Konteksts|Kontekstas|Kontekst|Koncept|Khung tình huống|Khung kịch bản|Háttér|Grundlage|Geçmiş|Forgatókönyv vázlat|Forgatókönyv|Fono|Esquema do Cenário|Esquema do Cenario|Esquema del escenario|Esquema de l\'escenari|Escenario|Escenari|Dis is what went down|Dasar|Contexto|Contexte|Contesto|Condiţii|Conditii|Cenário|Cenario|Cefndir|Bối cảnh|Blokes|Bakgrunn|Bakgrund|Baggrund|Background|B4|Antecedents|Antecedentes|All y\'all|Achtergrond|Abstrakt Scenario|Abstract Scenario)(:)(.*)$'
    examples_keywords = '^(\\s*)(예|例子|例|サンプル|امثلة|דוגמאות|Сценарији|Примери|Приклади|Мисоллар|Значения|Örnekler|Voorbeelden|Variantai|Tapaukset|Scenarios|Scenariji|Scenarijai|Příklady|Példák|Príklady|Przykłady|Primjeri|Primeri|Piemēri|Pavyzdžiai|Paraugs|Juhtumid|Exemplos|Exemples|Exemplele|Exempel|Examples|Esempi|Enghreifftiau|Ekzemploj|Eksempler|Ejemplos|EXAMPLZ|Dữ liệu|Contoh|Cobber|Beispiele)(:)(.*)$'
    step_keywords = '^(\\s*)(하지만|조건|먼저|만일|만약|단|그리고|그러면|那麼|那么|而且|當|当|前提|假設|假设|假如|假定|但是|但し|並且|并且|同時|同时|もし|ならば|ただし|しかし|かつ|و |متى |لكن |عندما |ثم |بفرض |اذاً |כאשר |וגם |בהינתן |אזי |אז |אבל |Якщо |Унда |То |Припустимо, що |Припустимо |Онда |Но |Нехай |Лекин |Когато |Када |Кад |К тому же |И |Задато |Задати |Задате |Если |Допустим |Дадено |Ва |Бирок |Аммо |Али |Але |Агар |А |І |Și |És |Zatati |Zakładając |Zadato |Zadate |Zadano |Zadani |Zadan |Youse know when youse got |Youse know like when |Yna |Ya know how |Ya gotta |Y |Wun |Wtedy |When y\'all |When |Wenn |WEN |Và |Ve |Und |Un |Thì |Then y\'all |Then |Tapi |Tak |Tada |Tad |Så |Stel |Soit |Siis |Si |Sed |Se |Quando |Quand |Quan |Pryd |Pokud |Pokiaľ |Però |Pero |Pak |Oraz |Onda |Ond |Oletetaan |Og |Och |O zaman |Når |När |Niin |Nhưng |N |Mutta |Men |Mas |Maka |Majd |Mais |Maar |Ma |Lorsque |Lorsqu\'|Kun |Kuid |Kui |Khi |Keď |Ketika |Když |Kaj |Kai |Kada |Kad |Jeżeli |Ja |Ir |I CAN HAZ |I |Ha |Givun |Givet |Given y\'all |Given |Gitt |Gegeven |Gegeben sei |Fakat |Eğer ki |Etant donné |Et |Então |Entonces |Entao |En |Eeldades |E |Duota |Dun |Donitaĵo |Donat |Donada |Do |Diyelim ki |Dengan |Den youse gotta |De |Dato |Dar |Dann |Dan |Dado |Dacă |Daca |DEN |Când |Cuando |Cho |Cept |Cand |Cal |But y\'all |But |Buh |Biết |Bet |BUT |Atès |Atunci |Atesa |Anrhegedig a |Angenommen |And y\'all |And |An |Ama |Als |Alors |Allora |Ali |Aleshores |Ale |Akkor |Aber |AN |A také |A |\\* )'

    tokens = {
        'comments': [
            (r'^\s*#.*$', Comment),
        ],
        'feature_elements': [
            (step_keywords, Keyword, "step_content_stack"),
            include('comments'),
            (r"(\s|.)", Name.Function),
        ],
        'feature_elements_on_stack': [
            (step_keywords, Keyword, "#pop:2"),
            include('comments'),
            (r"(\s|.)", Name.Function),
        ],
        'examples_table': [
            (r"\s+\|", Keyword, 'examples_table_header'),
            include('comments'),
            (r"(\s|.)", Name.Function),
        ],
        'examples_table_header': [
            (r"\s+\|\s*$", Keyword, "#pop:2"),
            include('comments'),
            (r"\\\|", Name.Variable),
            (r"\s*\|", Keyword),
            (r"[^|]", Name.Variable),
        ],
        'scenario_sections_on_stack': [
            (feature_element_keywords,
             bygroups(Name.Function, Keyword, Keyword, Name.Function),
             "feature_elements_on_stack"),
        ],
        'narrative': [
            include('scenario_sections_on_stack'),
            include('comments'),
            (r"(\s|.)", Name.Function),
        ],
        'table_vars': [
            (r'(<[^>]+>)', Name.Variable),
        ],
        'numbers': [
            (r'(\d+\.?\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', String),
        ],
        'string': [
            include('table_vars'),
            (r'(\s|.)', String),
        ],
        'py_string': [
            (r'"""', Keyword, "#pop"),
            include('string'),
        ],
        'step_content_root': [
            (r"$", Keyword, "#pop"),
            include('step_content'),
        ],
        'step_content_stack': [
            (r"$", Keyword, "#pop:2"),
            include('step_content'),
        ],
        'step_content': [
            (r'"', Name.Function, "double_string"),
            include('table_vars'),
            include('numbers'),
            include('comments'),
            (r'(\s|.)', Name.Function),
        ],
        'table_content': [
            (r"\s+\|\s*$", Keyword, "#pop"),
            include('comments'),
            (r"\\\|", String),
            (r"\s*\|", Keyword),
            include('string'),
        ],
        'double_string': [
            (r'"', Name.Function, "#pop"),
            include('string'),
        ],
        'root': [
            (r'\n', Name.Function),
            include('comments'),
            (r'"""', Keyword, "py_string"),
            (r'\s+\|', Keyword, 'table_content'),
            (r'"', Name.Function, "double_string"),
            include('table_vars'),
            include('numbers'),
            (r'(\s*)(@[^@\r\n\t ]+)', bygroups(Name.Function, Name.Tag)),
            (step_keywords, bygroups(Name.Function, Keyword),
             'step_content_root'),
            (feature_keywords, bygroups(Keyword, Keyword, Name.Function),
             'narrative'),
            (feature_element_keywords,
             bygroups(Name.Function, Keyword, Keyword, Name.Function),
             'feature_elements'),
            (examples_keywords,
             bygroups(Name.Function, Keyword, Keyword, Name.Function),
             'examples_table'),
            (r'(\s|.)', Name.Function),
        ]
    }

    def analyse_text(self, text):
        return


class TAPLexer(RegexLexer):
    """
    For Test Anything Protocol (TAP) output.
    """
    name = 'TAP'
    url = 'https://testanything.org/'
    aliases = ['tap']
    filenames = ['*.tap']
    version_added = '2.1'

    tokens = {
        'root': [
            # A TAP version may be specified.
            (r'^TAP version \d+\n', Name.Namespace),

            # Specify a plan with a plan line.
            (r'^1\.\.\d+', Keyword.Declaration, 'plan'),

            # A test failure
            (r'^(not ok)([^\S\n]*)(\d*)',
             bygroups(Generic.Error, Text, Number.Integer), 'test'),

            # A test success
            (r'^(ok)([^\S\n]*)(\d*)',
             bygroups(Keyword.Reserved, Text, Number.Integer), 'test'),

            # Diagnostics start with a hash.
            (r'^#.*\n', Comment),

            # TAP's version of an abort statement.
            (r'^Bail out!.*\n', Generic.Error),

            # TAP ignores any unrecognized lines.
            (r'^.*\n', Text),
        ],
        'plan': [
            # Consume whitespace (but not newline).
            (r'[^\S\n]+', Text),

            # A plan may have a directive with it.
            (r'#', Comment, 'directive'),

            # Or it could just end.
            (r'\n', Comment, '#pop'),

            # Anything else is wrong.
            (r'.*\n', Generic.Error, '#pop'),
        ],
        'test': [
            # Consume whitespace (but not newline).
            (r'[^\S\n]+', Text),

            # A test may have a directive with it.
            (r'#', Comment, 'directive'),

            (r'\S+', Text),

            (r'\n', Text, '#pop'),
        ],
        'directive': [
            # Consume whitespace (but not newline).
            (r'[^\S\n]+', Comment),

            # Extract todo items.
            (r'(?i)\bTODO\b', Comment.Preproc),

            # Extract skip items.
            (r'(?i)\bSKIP\S*', Comment.Preproc),

            (r'\S+', Comment),

            (r'\n', Comment, '#pop:2'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\astor\node_util.py ===
# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright 2012-2015 (c) Patrick Maupin
Copyright 2013-2015 (c) Berker Peksag

Utilities for node (and, by extension, tree) manipulation.
For a whole-tree approach, see the treewalk submodule.

"""

import ast
import itertools

try:
    zip_longest = itertools.zip_longest
except AttributeError:
    zip_longest = itertools.izip_longest


class NonExistent(object):
    """This is not the class you are looking for.
    """
    pass


def iter_node(node, name='', unknown=None,
              # Runtime optimization
              list=list, getattr=getattr, isinstance=isinstance,
              enumerate=enumerate, missing=NonExistent):
    """Iterates over an object:

       - If the object has a _fields attribute,
         it gets attributes in the order of this
         and returns name, value pairs.

       - Otherwise, if the object is a list instance,
         it returns name, value pairs for each item
         in the list, where the name is passed into
         this function (defaults to blank).

       - Can update an unknown set with information about
         attributes that do not exist in fields.
    """
    fields = getattr(node, '_fields', None)
    if fields is not None:
        for name in fields:
            value = getattr(node, name, missing)
            if value is not missing:
                yield value, name
        if unknown is not None:
            unknown.update(set(vars(node)) - set(fields))
    elif isinstance(node, list):
        for value in node:
            yield value, name


def dump_tree(node, name=None, initial_indent='', indentation='    ',
              maxline=120, maxmerged=80,
              # Runtime optimization
              iter_node=iter_node, special=ast.AST,
              list=list, isinstance=isinstance, type=type, len=len):
    """Dumps an AST or similar structure:

       - Pretty-prints with indentation
       - Doesn't print line/column/ctx info

    """
    def dump(node, name=None, indent=''):
        level = indent + indentation
        name = name and name + '=' or ''
        values = list(iter_node(node))
        if isinstance(node, list):
            prefix, suffix = '%s[' % name, ']'
        elif values:
            prefix, suffix = '%s%s(' % (name, type(node).__name__), ')'
        elif isinstance(node, special):
            prefix, suffix = name + type(node).__name__, ''
        else:
            return '%s%s' % (name, repr(node))
        node = [dump(a, b, level) for a, b in values if b != 'ctx']
        oneline = '%s%s%s' % (prefix, ', '.join(node), suffix)
        if len(oneline) + len(indent) < maxline:
            return '%s' % oneline
        if node and len(prefix) + len(node[0]) < maxmerged:
            prefix = '%s%s,' % (prefix, node.pop(0))
        node = (',\n%s' % level).join(node).lstrip()
        return '%s\n%s%s%s' % (prefix, level, node, suffix)
    return dump(node, name, initial_indent)


def strip_tree(node,
               # Runtime optimization
               iter_node=iter_node, special=ast.AST,
               list=list, isinstance=isinstance, type=type, len=len):
    """Strips an AST by removing all attributes not in _fields.

    Returns a set of the names of all attributes stripped.

    This canonicalizes two trees for comparison purposes.
    """
    stripped = set()

    def strip(node, indent):
        unknown = set()
        leaf = True
        for subnode, _ in iter_node(node, unknown=unknown):
            leaf = False
            strip(subnode, indent + '    ')
        if leaf:
            if isinstance(node, special):
                unknown = set(vars(node))
        stripped.update(unknown)
        for name in unknown:
            delattr(node, name)
        if hasattr(node, 'ctx'):
            delattr(node, 'ctx')
            if 'ctx' in node._fields:
                mylist = list(node._fields)
                mylist.remove('ctx')
                node._fields = mylist
    strip(node, '')
    return stripped


class ExplicitNodeVisitor(ast.NodeVisitor):
    """This expands on the ast module's NodeVisitor class
    to remove any implicit visits.

    """

    def abort_visit(node):  # XXX: self?
        msg = 'No defined handler for node of type %s'
        raise AttributeError(msg % node.__class__.__name__)

    def visit(self, node, abort=abort_visit):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, abort)
        return visitor(node)


def allow_ast_comparison():
    """This ugly little monkey-patcher adds in a helper class
    to all the AST node types.  This helper class allows
    eq/ne comparisons to work, so that entire trees can
    be easily compared by Python's comparison machinery.
    Used by the anti8 functions to compare old and new ASTs.
    Could also be used by the test library.


    """

    class CompareHelper(object):
        def __eq__(self, other):
            return type(self) == type(other) and vars(self) == vars(other)

        def __ne__(self, other):
            return type(self) != type(other) or vars(self) != vars(other)

    for item in vars(ast).values():
        if type(item) != type:
            continue
        if issubclass(item, ast.AST):
            try:
                item.__bases__ = tuple(list(item.__bases__) + [CompareHelper])
            except TypeError:
                pass


def fast_compare(tree1, tree2):
    """ This is optimized to compare two AST trees for equality.
        It makes several assumptions that are currently true for
        AST trees used by rtrip, and it doesn't examine the _attributes.
    """

    geta = ast.AST.__getattribute__

    work = [(tree1, tree2)]
    pop = work.pop
    extend = work.extend
    # TypeError in cPython, AttributeError in PyPy
    exception = TypeError, AttributeError
    zipl = zip_longest
    type_ = type
    list_ = list
    while work:
        n1, n2 = pop()
        try:
            f1 = geta(n1, '_fields')
            f2 = geta(n2, '_fields')
        except exception:
            if type_(n1) is list_:
                extend(zipl(n1, n2))
                continue
            if n1 == n2:
                continue
            return False
        else:
            f1 = [x for x in f1 if x != 'ctx']
            if f1 != [x for x in f2 if x != 'ctx']:
                return False
            extend((geta(n1, fname), geta(n2, fname)) for fname in f1)

    return True

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_plugin_utils.py ===
import types

from _pydev_bundle import pydev_log
from typing import Tuple, Literal

try:
    from pydevd_plugins import django_debug
except:
    django_debug = None
    pydev_log.debug("Unable to load django_debug plugin")

try:
    from pydevd_plugins import jinja2_debug
except:
    jinja2_debug = None
    pydev_log.debug("Unable to load jinja2_debug plugin")


def load_plugins():
    plugins = []
    if django_debug is not None:
        plugins.append(django_debug)

    if jinja2_debug is not None:
        plugins.append(jinja2_debug)
    return plugins


def bind_func_to_method(func, obj, method_name):
    bound_method = types.MethodType(func, obj)

    setattr(obj, method_name, bound_method)
    return bound_method


class PluginManager(object):
    EMPTY_SENTINEL = object()

    def __init__(self, main_debugger):
        self.plugins = load_plugins()

        # When some breakpoint is added for a given plugin it becomes active.
        self.active_plugins = []

        self.main_debugger = main_debugger

    def add_breakpoint(self, func_name, *args, **kwargs):
        # add breakpoint for plugin
        for plugin in self.plugins:
            if hasattr(plugin, func_name):
                func = getattr(plugin, func_name)
                result = func(*args, **kwargs)
                if result:
                    self.activate(plugin)
                    return result
        return None

    def activate(self, plugin):
        if plugin not in self.active_plugins:
            self.active_plugins.append(plugin)

    # These are not a part of the API, rather, `add_breakpoint` should be used with `add_line_breakpoint` or `add_exception_breakpoint`
    # which will call it for all plugins and then if it's valid it'll be activated.
    #
    # def add_line_breakpoint(self, py_db, type, canonical_normalized_filename, breakpoint_id, line, condition, expression, func_name, hit_condition=None, is_logpoint=False, add_breakpoint_result=None, on_changed_breakpoint_state=None):
    # def add_exception_breakpoint(plugin, py_db, type, exception):

    def after_breakpoints_consolidated(self, py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints):
        for plugin in self.active_plugins:
            plugin.after_breakpoints_consolidated(py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints)

    def remove_exception_breakpoint(self, py_db, exception_type, exception):
        """
        :param exception_type: 'django', 'jinja2' (can be extended)
        """
        for plugin in self.active_plugins:
            ret = plugin.remove_exception_breakpoint(py_db, exception_type, exception)
            if ret:
                return ret

        return None

    def remove_all_exception_breakpoints(self, py_db):
        for plugin in self.active_plugins:
            plugin.remove_all_exception_breakpoints(py_db)

    def get_breakpoints(self, py_db, breakpoint_type):
        """
        :param breakpoint_type: 'django-line', 'jinja2-line'
        """
        for plugin in self.active_plugins:
            ret = plugin.get_breakpoints(py_db, breakpoint_type)
            if ret:
                return ret

    def can_skip(self, py_db, frame):
        for plugin in self.active_plugins:
            if not plugin.can_skip(py_db, frame):
                return False
        return True

    def required_events_breakpoint(self) -> Tuple[Literal["line", "call"], ...]:
        ret = ()
        for plugin in self.active_plugins:
            new = plugin.required_events_breakpoint()
            if new:
                ret += new

        return ret

    def required_events_stepping(self) -> Tuple[Literal["line", "call", "return"], ...]:
        ret = ()
        for plugin in self.active_plugins:
            new = plugin.required_events_stepping()
            if new:
                ret += new

        return ret

    def is_tracked_frame(self, frame) -> bool:
        for plugin in self.active_plugins:
            if plugin.is_tracked_frame(frame):
                return True
        return False

    def has_exception_breaks(self, py_db) -> bool:
        for plugin in self.active_plugins:
            if plugin.has_exception_breaks(py_db):
                return True
        return False

    def has_line_breaks(self, py_db) -> bool:
        for plugin in self.active_plugins:
            if plugin.has_line_breaks(py_db):
                return True
        return False

    def cmd_step_into(self, py_db, frame, event, info, thread, stop_info, stop: bool):
        """
        :param stop_info: in/out information. If it should stop then it'll be
            filled by the plugin.
        :param stop: whether the stop has already been flagged for this frame.
        :returns:
            tuple(stop, plugin_stop)
        """
        plugin_stop = False
        for plugin in self.active_plugins:
            stop, plugin_stop = plugin.cmd_step_into(py_db, frame, event, info, thread, stop_info, stop)
            if plugin_stop:
                return stop, plugin_stop
        return stop, plugin_stop

    def cmd_step_over(self, py_db, frame, event, info, thread, stop_info, stop):
        plugin_stop = False
        for plugin in self.active_plugins:
            stop, plugin_stop = plugin.cmd_step_over(py_db, frame, event, info, thread, stop_info, stop)
            if plugin_stop:
                return stop, plugin_stop
        return stop, plugin_stop

    def stop(self, py_db, frame, event, thread, stop_info, arg, step_cmd):
        """
        The way this works is that the `cmd_step_into` or `cmd_step_over`
        is called which then fills the `stop_info` and then this method
        is called to do the actual stop.
        """
        for plugin in self.active_plugins:
            stopped = plugin.stop(py_db, frame, event, thread, stop_info, arg, step_cmd)
            if stopped:
                return stopped
        return False

    def get_breakpoint(self, py_db, frame, event, info):
        for plugin in self.active_plugins:
            ret = plugin.get_breakpoint(py_db, frame, event, info)
            if ret:
                return ret
        return None

    def suspend(self, py_db, thread, frame, bp_type):
        """
        :param bp_type: 'django' or 'jinja2'

        :return:
            The frame for the suspend or None if it should not be suspended.
        """
        for plugin in self.active_plugins:
            ret = plugin.suspend(py_db, thread, frame, bp_type)
            if ret is not None:
                return ret

        return None

    def exception_break(self, py_db, frame, thread, arg, is_unwind=False):
        for plugin in self.active_plugins:
            ret = plugin.exception_break(py_db, frame, thread, arg, is_unwind)
            if ret is not None:
                return ret

        return None

    def change_variable(self, frame, attr, expression, scope=None):
        for plugin in self.active_plugins:
            ret = plugin.change_variable(frame, attr, expression, self.EMPTY_SENTINEL, scope)
            if ret is not self.EMPTY_SENTINEL:
                return ret

        return self.EMPTY_SENTINEL

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\bytecode\bytecode.py ===
# alias to keep the 'bytecode' variable free
import sys
from _pydevd_frame_eval.vendored import bytecode as _bytecode
from _pydevd_frame_eval.vendored.bytecode.instr import UNSET, Label, SetLineno, Instr
from _pydevd_frame_eval.vendored.bytecode.flags import infer_flags


class BaseBytecode:
    def __init__(self):
        self.argcount = 0
        if sys.version_info > (3, 8):
            self.posonlyargcount = 0
        self.kwonlyargcount = 0
        self.first_lineno = 1
        self.name = "<module>"
        self.filename = "<string>"
        self.docstring = UNSET
        self.cellvars = []
        # we cannot recreate freevars from instructions because of super()
        # special-case
        self.freevars = []
        self._flags = _bytecode.CompilerFlags(0)

    def _copy_attr_from(self, bytecode):
        self.argcount = bytecode.argcount
        if sys.version_info > (3, 8):
            self.posonlyargcount = bytecode.posonlyargcount
        self.kwonlyargcount = bytecode.kwonlyargcount
        self.flags = bytecode.flags
        self.first_lineno = bytecode.first_lineno
        self.name = bytecode.name
        self.filename = bytecode.filename
        self.docstring = bytecode.docstring
        self.cellvars = list(bytecode.cellvars)
        self.freevars = list(bytecode.freevars)

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        if self.argcount != other.argcount:
            return False
        if sys.version_info > (3, 8):
            if self.posonlyargcount != other.posonlyargcount:
                return False
        if self.kwonlyargcount != other.kwonlyargcount:
            return False
        if self.flags != other.flags:
            return False
        if self.first_lineno != other.first_lineno:
            return False
        if self.filename != other.filename:
            return False
        if self.name != other.name:
            return False
        if self.docstring != other.docstring:
            return False
        if self.cellvars != other.cellvars:
            return False
        if self.freevars != other.freevars:
            return False
        if self.compute_stacksize() != other.compute_stacksize():
            return False

        return True

    @property
    def flags(self):
        return self._flags

    @flags.setter
    def flags(self, value):
        if not isinstance(value, _bytecode.CompilerFlags):
            value = _bytecode.CompilerFlags(value)
        self._flags = value

    def update_flags(self, *, is_async=None):
        self.flags = infer_flags(self, is_async)


class _BaseBytecodeList(BaseBytecode, list):
    """List subclass providing type stable slicing and copying."""

    def __getitem__(self, index):
        value = super().__getitem__(index)
        if isinstance(index, slice):
            value = type(self)(value)
            value._copy_attr_from(self)

        return value

    def copy(self):
        new = type(self)(super().copy())
        new._copy_attr_from(self)
        return new

    def legalize(self):
        """Check that all the element of the list are valid and remove SetLineno."""
        lineno_pos = []
        set_lineno = None
        current_lineno = self.first_lineno

        for pos, instr in enumerate(self):
            if isinstance(instr, SetLineno):
                set_lineno = instr.lineno
                lineno_pos.append(pos)
                continue
            # Filter out Labels
            if not isinstance(instr, Instr):
                continue
            if set_lineno is not None:
                instr.lineno = set_lineno
            elif instr.lineno is None:
                instr.lineno = current_lineno
            else:
                current_lineno = instr.lineno

        for i in reversed(lineno_pos):
            del self[i]

    def __iter__(self):
        instructions = super().__iter__()
        for instr in instructions:
            self._check_instr(instr)
            yield instr

    def _check_instr(self, instr):
        raise NotImplementedError()


class _InstrList(list):
    def _flat(self):
        instructions = []
        labels = {}
        jumps = []

        offset = 0
        for index, instr in enumerate(self):
            if isinstance(instr, Label):
                instructions.append("label_instr%s" % index)
                labels[instr] = offset
            else:
                if isinstance(instr, Instr) and isinstance(instr.arg, Label):
                    target_label = instr.arg
                    instr = _bytecode.ConcreteInstr(instr.name, 0, lineno=instr.lineno)
                    jumps.append((target_label, instr))
                instructions.append(instr)
                offset += 1

        for target_label, instr in jumps:
            instr.arg = labels[target_label]

        return instructions

    def __eq__(self, other):
        if not isinstance(other, _InstrList):
            other = _InstrList(other)

        return self._flat() == other._flat()


class Bytecode(_InstrList, _BaseBytecodeList):
    def __init__(self, instructions=()):
        BaseBytecode.__init__(self)
        self.argnames = []
        for instr in instructions:
            self._check_instr(instr)
        self.extend(instructions)

    def __iter__(self):
        instructions = super().__iter__()
        for instr in instructions:
            self._check_instr(instr)
            yield instr

    def _check_instr(self, instr):
        if not isinstance(instr, (Label, SetLineno, Instr)):
            raise ValueError(
                "Bytecode must only contain Label, " "SetLineno, and Instr objects, " "but %s was found" % type(instr).__name__
            )

    def _copy_attr_from(self, bytecode):
        super()._copy_attr_from(bytecode)
        if isinstance(bytecode, Bytecode):
            self.argnames = bytecode.argnames

    @staticmethod
    def from_code(code):
        if sys.version_info[:2] >= (3, 11):
            raise RuntimeError("This is not updated for Python 3.11 onwards, use only up to Python 3.10!!")
        concrete = _bytecode.ConcreteBytecode.from_code(code)
        return concrete.to_bytecode()

    def compute_stacksize(self, *, check_pre_and_post=True):
        cfg = _bytecode.ControlFlowGraph.from_bytecode(self)
        return cfg.compute_stacksize(check_pre_and_post=check_pre_and_post)

    def to_code(self, compute_jumps_passes=None, stacksize=None, *, check_pre_and_post=True):
        # Prevent reconverting the concrete bytecode to bytecode and cfg to do the
        # calculation if we need to do it.
        if stacksize is None:
            stacksize = self.compute_stacksize(check_pre_and_post=check_pre_and_post)
        bc = self.to_concrete_bytecode(compute_jumps_passes=compute_jumps_passes)
        return bc.to_code(stacksize=stacksize)

    def to_concrete_bytecode(self, compute_jumps_passes=None):
        converter = _bytecode._ConvertBytecodeToConcrete(self)
        return converter.to_concrete_bytecode(compute_jumps_passes=compute_jumps_passes)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\discuss_types.py ===
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
"""Type definitions for the discuss service."""

import abc
import dataclasses
from typing import Any, Dict, Union, Iterable, Optional, Tuple, List
from typing_extensions import TypedDict

from google.generativeai import protos
from google.generativeai import string_utils

from google.generativeai.types import palm_safety_types
from google.generativeai.types import citation_types


__all__ = [
    "MessageDict",
    "MessageOptions",
    "MessagesOptions",
    "ExampleDict",
    "ExampleOptions",
    "ExamplesOptions",
    "MessagePromptDict",
    "MessagePromptOptions",
    "ResponseDict",
    "ChatResponse",
    "AuthorError",
]


class TokenCount(TypedDict):
    token_count: int


class MessageDict(TypedDict):
    """A dict representation of a `protos.Message`."""

    author: str
    content: str
    citation_metadata: Optional[citation_types.CitationMetadataDict]


MessageOptions = Union[str, MessageDict, protos.Message]
MESSAGE_OPTIONS = (str, dict, protos.Message)

MessagesOptions = Union[
    MessageOptions,
    Iterable[MessageOptions],
]
MESSAGES_OPTIONS = (MESSAGE_OPTIONS, Iterable)


class ExampleDict(TypedDict):
    """A dict representation of a `protos.Example`."""

    input: MessageOptions
    output: MessageOptions


ExampleOptions = Union[
    Tuple[MessageOptions, MessageOptions],
    Iterable[MessageOptions],
    ExampleDict,
    protos.Example,
]
EXAMPLE_OPTIONS = (protos.Example, dict, Iterable)
ExamplesOptions = Union[ExampleOptions, Iterable[ExampleOptions]]


class MessagePromptDict(TypedDict, total=False):
    """A dict representation of a `protos.MessagePrompt`."""

    context: str
    examples: ExamplesOptions
    messages: MessagesOptions


MessagePromptOptions = Union[
    str,
    protos.Message,
    Iterable[Union[str, protos.Message]],
    MessagePromptDict,
    protos.MessagePrompt,
]
MESSAGE_PROMPT_KEYS = {"context", "examples", "messages"}


class ResponseDict(TypedDict):
    """A dict representation of a `protos.GenerateMessageResponse`."""

    messages: List[MessageDict]
    candidates: List[MessageDict]


@string_utils.prettyprint
@dataclasses.dataclass(init=False)
class ChatResponse(abc.ABC):
    """A chat response from the model.

    * Use `response.last` (settable) for easy access to the text of the last response.
        (`messages[-1]['content']`)
    * Use `response.messages` to access the message history (including `.last`).
    * Use `response.candidates` to access all the responses generated by the model.

    Other attributes are just saved from the arguments to `genai.chat`, so you
    can easily continue a conversation:

    ```
    import google.generativeai as genai

    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

    response = genai.chat(messages=["Hello."])
    print(response.last) #  'Hello! What can I help you with?'
    response.reply("Can you tell me a joke?")
    ```

    See `genai.chat` for more details.

    Attributes:
        candidates: A list of candidate responses from the model.

            The top candidate is appended to the `messages` field.

            This list will contain a *maximum* of `candidate_count` candidates.
            It may contain fewer (duplicates are dropped), it will contain at least one.

            Note: The `temperature` field affects the variability of the responses. Low
            temperatures will return few candidates. Setting `temperature=0` is deterministic,
            so it will only ever return one candidate.
        filters: This indicates which `types.SafetyCategory`(s) blocked a
           candidate from this response, the lowest `types.HarmProbability`
           that triggered a block, and the `types.HarmThreshold` setting for that category.
           This indicates the smallest change to the `types.SafetySettings` that would be
           necessary to unblock at least 1 response.

           The blocking is configured by the `types.SafetySettings` in the request (or the
           default `types.SafetySettings` of the API).
        messages: Contains all the `messages` that were passed when the model was called,
            plus the top `candidate` message.
        model: The model name.
        context: Text that should be provided to the model first, to ground the response.
        examples: Examples of what the model should generate.
        messages: A snapshot of the conversation history sorted chronologically.
        temperature: Controls the randomness of the output. Must be positive.
        candidate_count: The **maximum** number of generated response messages to return.
        top_k: The maximum number of tokens to consider when sampling.
        top_p: The maximum cumulative probability of tokens to consider when sampling.

    """

    model: str
    context: str
    examples: List[ExampleDict]
    messages: List[Optional[MessageDict]]
    temperature: Optional[float]
    candidate_count: Optional[int]
    candidates: List[MessageDict]
    filters: List[palm_safety_types.ContentFilterDict]
    top_p: Optional[float] = None
    top_k: Optional[float] = None

    @property
    @abc.abstractmethod
    def last(self) -> Optional[str]:
        """A settable property that provides simple access to the last response string

        A shortcut for `response.messages[0]['content']`.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "model": self.model,
            "context": self.context,
            "examples": self.examples,
            "messages": self.messages,
            "temperature": self.temperature,
            "candidate_count": self.candidate_count,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "candidates": self.candidates,
        }
        return result

    @abc.abstractmethod
    def reply(self, message: MessageOptions) -> "ChatResponse":
        "Add a message to the conversation, and get the model's response."
        pass


class AuthorError(Exception):
    """Raised by the `chat` (or `reply`) functions when the author list can't be normalized."""

    pass

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\response_computer_tool_call_param.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = [
    "ResponseComputerToolCallParam",
    "Action",
    "ActionClick",
    "ActionDoubleClick",
    "ActionDrag",
    "ActionDragPath",
    "ActionKeypress",
    "ActionMove",
    "ActionScreenshot",
    "ActionScroll",
    "ActionType",
    "ActionWait",
    "PendingSafetyCheck",
]


class ActionClick(TypedDict, total=False):
    button: Required[Literal["left", "right", "wheel", "back", "forward"]]
    """Indicates which mouse button was pressed during the click.

    One of `left`, `right`, `wheel`, `back`, or `forward`.
    """

    type: Required[Literal["click"]]
    """Specifies the event type.

    For a click action, this property is always set to `click`.
    """

    x: Required[int]
    """The x-coordinate where the click occurred."""

    y: Required[int]
    """The y-coordinate where the click occurred."""


class ActionDoubleClick(TypedDict, total=False):
    type: Required[Literal["double_click"]]
    """Specifies the event type.

    For a double click action, this property is always set to `double_click`.
    """

    x: Required[int]
    """The x-coordinate where the double click occurred."""

    y: Required[int]
    """The y-coordinate where the double click occurred."""


class ActionDragPath(TypedDict, total=False):
    x: Required[int]
    """The x-coordinate."""

    y: Required[int]
    """The y-coordinate."""


class ActionDrag(TypedDict, total=False):
    path: Required[Iterable[ActionDragPath]]
    """An array of coordinates representing the path of the drag action.

    Coordinates will appear as an array of objects, eg

    ```
    [
      { x: 100, y: 200 },
      { x: 200, y: 300 }
    ]
    ```
    """

    type: Required[Literal["drag"]]
    """Specifies the event type.

    For a drag action, this property is always set to `drag`.
    """


class ActionKeypress(TypedDict, total=False):
    keys: Required[List[str]]
    """The combination of keys the model is requesting to be pressed.

    This is an array of strings, each representing a key.
    """

    type: Required[Literal["keypress"]]
    """Specifies the event type.

    For a keypress action, this property is always set to `keypress`.
    """


class ActionMove(TypedDict, total=False):
    type: Required[Literal["move"]]
    """Specifies the event type.

    For a move action, this property is always set to `move`.
    """

    x: Required[int]
    """The x-coordinate to move to."""

    y: Required[int]
    """The y-coordinate to move to."""


class ActionScreenshot(TypedDict, total=False):
    type: Required[Literal["screenshot"]]
    """Specifies the event type.

    For a screenshot action, this property is always set to `screenshot`.
    """


class ActionScroll(TypedDict, total=False):
    scroll_x: Required[int]
    """The horizontal scroll distance."""

    scroll_y: Required[int]
    """The vertical scroll distance."""

    type: Required[Literal["scroll"]]
    """Specifies the event type.

    For a scroll action, this property is always set to `scroll`.
    """

    x: Required[int]
    """The x-coordinate where the scroll occurred."""

    y: Required[int]
    """The y-coordinate where the scroll occurred."""


class ActionType(TypedDict, total=False):
    text: Required[str]
    """The text to type."""

    type: Required[Literal["type"]]
    """Specifies the event type.

    For a type action, this property is always set to `type`.
    """


class ActionWait(TypedDict, total=False):
    type: Required[Literal["wait"]]
    """Specifies the event type.

    For a wait action, this property is always set to `wait`.
    """


Action: TypeAlias = Union[
    ActionClick,
    ActionDoubleClick,
    ActionDrag,
    ActionKeypress,
    ActionMove,
    ActionScreenshot,
    ActionScroll,
    ActionType,
    ActionWait,
]


class PendingSafetyCheck(TypedDict, total=False):
    id: Required[str]
    """The ID of the pending safety check."""

    code: Required[str]
    """The type of the pending safety check."""

    message: Required[str]
    """Details about the pending safety check."""


class ResponseComputerToolCallParam(TypedDict, total=False):
    id: Required[str]
    """The unique ID of the computer call."""

    action: Required[Action]
    """A click action."""

    call_id: Required[str]
    """An identifier used when responding to the tool call with output."""

    pending_safety_checks: Required[Iterable[PendingSafetyCheck]]
    """The pending safety checks for the computer call."""

    status: Required[Literal["in_progress", "completed", "incomplete"]]
    """The status of the item.

    One of `in_progress`, `completed`, or `incomplete`. Populated when items are
    returned via API.
    """

    type: Required[Literal["computer_call"]]
    """The type of the computer call. Always `computer_call`."""

# === NexusCore/openenv\Lib\site-packages\aiohappyeyeballs\_staggered.py ===
import asyncio
import contextlib

# PY3.9: Import Callable from typing until we drop Python 3.9 support
# https://github.com/python/cpython/issues/87131
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

_T = TypeVar("_T")

RE_RAISE_EXCEPTIONS = (SystemExit, KeyboardInterrupt)


def _set_result(wait_next: "asyncio.Future[None]") -> None:
    """Set the result of a future if it is not already done."""
    if not wait_next.done():
        wait_next.set_result(None)


async def _wait_one(
    futures: "Iterable[asyncio.Future[Any]]",
    loop: asyncio.AbstractEventLoop,
) -> _T:
    """Wait for the first future to complete."""
    wait_next = loop.create_future()

    def _on_completion(fut: "asyncio.Future[Any]") -> None:
        if not wait_next.done():
            wait_next.set_result(fut)

    for f in futures:
        f.add_done_callback(_on_completion)

    try:
        return await wait_next
    finally:
        for f in futures:
            f.remove_done_callback(_on_completion)


async def staggered_race(
    coro_fns: Iterable[Callable[[], Awaitable[_T]]],
    delay: Optional[float],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> Tuple[Optional[_T], Optional[int], List[Optional[BaseException]]]:
    """
    Run coroutines with staggered start times and take the first to finish.

    This method takes an iterable of coroutine functions. The first one is
    started immediately. From then on, whenever the immediately preceding one
    fails (raises an exception), or when *delay* seconds has passed, the next
    coroutine is started. This continues until one of the coroutines complete
    successfully, in which case all others are cancelled, or until all
    coroutines fail.

    The coroutines provided should be well-behaved in the following way:

    * They should only ``return`` if completed successfully.

    * They should always raise an exception if they did not complete
      successfully. In particular, if they handle cancellation, they should
      probably reraise, like this::

        try:
            # do work
        except asyncio.CancelledError:
            # undo partially completed work
            raise

    Args:
    ----
        coro_fns: an iterable of coroutine functions, i.e. callables that
            return a coroutine object when called. Use ``functools.partial`` or
            lambdas to pass arguments.

        delay: amount of time, in seconds, between starting coroutines. If
            ``None``, the coroutines will run sequentially.

        loop: the event loop to use. If ``None``, the running loop is used.

    Returns:
    -------
        tuple *(winner_result, winner_index, exceptions)* where

        - *winner_result*: the result of the winning coroutine, or ``None``
          if no coroutines won.

        - *winner_index*: the index of the winning coroutine in
          ``coro_fns``, or ``None`` if no coroutines won. If the winning
          coroutine may return None on success, *winner_index* can be used
          to definitively determine whether any coroutine won.

        - *exceptions*: list of exceptions returned by the coroutines.
          ``len(exceptions)`` is equal to the number of coroutines actually
          started, and the order is the same as in ``coro_fns``. The winning
          coroutine's entry is ``None``.

    """
    loop = loop or asyncio.get_running_loop()
    exceptions: List[Optional[BaseException]] = []
    tasks: Set[asyncio.Task[Optional[Tuple[_T, int]]]] = set()

    async def run_one_coro(
        coro_fn: Callable[[], Awaitable[_T]],
        this_index: int,
        start_next: "asyncio.Future[None]",
    ) -> Optional[Tuple[_T, int]]:
        """
        Run a single coroutine.

        If the coroutine fails, set the exception in the exceptions list and
        start the next coroutine by setting the result of the start_next.

        If the coroutine succeeds, return the result and the index of the
        coroutine in the coro_fns list.

        If SystemExit or KeyboardInterrupt is raised, re-raise it.
        """
        try:
            result = await coro_fn()
        except RE_RAISE_EXCEPTIONS:
            raise
        except BaseException as e:
            exceptions[this_index] = e
            _set_result(start_next)  # Kickstart the next coroutine
            return None

        return result, this_index

    start_next_timer: Optional[asyncio.TimerHandle] = None
    start_next: Optional[asyncio.Future[None]]
    task: asyncio.Task[Optional[Tuple[_T, int]]]
    done: Union[asyncio.Future[None], asyncio.Task[Optional[Tuple[_T, int]]]]
    coro_iter = iter(coro_fns)
    this_index = -1
    try:
        while True:
            if coro_fn := next(coro_iter, None):
                this_index += 1
                exceptions.append(None)
                start_next = loop.create_future()
                task = loop.create_task(run_one_coro(coro_fn, this_index, start_next))
                tasks.add(task)
                start_next_timer = (
                    loop.call_later(delay, _set_result, start_next) if delay else None
                )
            elif not tasks:
                # We exhausted the coro_fns list and no tasks are running
                # so we have no winner and all coroutines failed.
                break

            while tasks or start_next:
                done = await _wait_one(
                    (*tasks, start_next) if start_next else tasks, loop
                )
                if done is start_next:
                    # The current task has failed or the timer has expired
                    # so we need to start the next task.
                    start_next = None
                    if start_next_timer:
                        start_next_timer.cancel()
                        start_next_timer = None

                    # Break out of the task waiting loop to start the next
                    # task.
                    break

                if TYPE_CHECKING:
                    assert isinstance(done, asyncio.Task)

                tasks.remove(done)
                if winner := done.result():
                    return *winner, exceptions
    finally:
        # We either have:
        #  - a winner
        #  - all tasks failed
        #  - a KeyboardInterrupt or SystemExit.

        #
        # If the timer is still running, cancel it.
        #
        if start_next_timer:
            start_next_timer.cancel()

        #
        # If there are any tasks left, cancel them and than
        # wait them so they fill the exceptions list.
        #
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return None, None, exceptions

# === NexusCore/openenv\Lib\site-packages\contourpy\dechunk.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from contourpy._contourpy import FillType, LineType
from contourpy.array import (
    concat_codes_or_none,
    concat_offsets_or_none,
    concat_points_or_none,
    concat_points_or_none_with_nan,
)
from contourpy.enum_util import as_fill_type, as_line_type
from contourpy.typecheck import check_filled, check_lines

if TYPE_CHECKING:
    import contourpy._contourpy as cpy


def dechunk_filled(filled: cpy.FillReturn, fill_type: FillType | str) -> cpy.FillReturn:
    """Return the specified filled contours with chunked data moved into the first chunk.

    Filled contours that are not chunked (``FillType.OuterCode`` and ``FillType.OuterOffset``) and
    those that are but only contain a single chunk are returned unmodified. Individual polygons are
    unchanged, they are not geometrically combined.

    Args:
        filled (sequence of arrays): Filled contour data, such as returned by
            :meth:`.ContourGenerator.filled`.
        fill_type (FillType or str): Type of :meth:`~.ContourGenerator.filled` as enum or string
            equivalent.

    Return:
        Filled contours in a single chunk.

    .. versionadded:: 1.2.0
    """
    fill_type = as_fill_type(fill_type)

    if fill_type in (FillType.OuterCode, FillType.OuterOffset):
        # No-op if fill_type is not chunked.
        return filled

    check_filled(filled, fill_type)
    if len(filled[0]) < 2:
        # No-op if just one chunk.
        return filled

    if TYPE_CHECKING:
        filled = cast(cpy.FillReturn_Chunk, filled)
    points = concat_points_or_none(filled[0])

    if fill_type == FillType.ChunkCombinedCode:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCode, filled)
        if points is None:
            ret1: cpy.FillReturn_ChunkCombinedCode = ([None], [None])
        else:
            ret1 = ([points], [concat_codes_or_none(filled[1])])
        return ret1
    elif fill_type == FillType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffset, filled)
        if points is None:
            ret2: cpy.FillReturn_ChunkCombinedOffset = ([None], [None])
        else:
            ret2 = ([points], [concat_offsets_or_none(filled[1])])
        return ret2
    elif fill_type == FillType.ChunkCombinedCodeOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCodeOffset, filled)
        if points is None:
            ret3: cpy.FillReturn_ChunkCombinedCodeOffset = ([None], [None], [None])
        else:
            outer_offsets = concat_offsets_or_none(filled[2])
            ret3 = ([points], [concat_codes_or_none(filled[1])], [outer_offsets])
        return ret3
    elif fill_type == FillType.ChunkCombinedOffsetOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffsetOffset, filled)
        if points is None:
            ret4: cpy.FillReturn_ChunkCombinedOffsetOffset = ([None], [None], [None])
        else:
            outer_offsets = concat_offsets_or_none(filled[2])
            ret4 = ([points], [concat_offsets_or_none(filled[1])], [outer_offsets])
        return ret4
    else:
        raise ValueError(f"Invalid FillType {fill_type}")


def dechunk_lines(lines: cpy.LineReturn, line_type: LineType | str) -> cpy.LineReturn:
    """Return the specified contour lines with chunked data moved into the first chunk.

    Contour lines that are not chunked (``LineType.Separate`` and ``LineType.SeparateCode``) and
    those that are but only contain a single chunk are returned unmodified. Individual lines are
    unchanged, they are not geometrically combined.

    Args:
        lines (sequence of arrays): Contour line data, such as returned by
            :meth:`.ContourGenerator.lines`.
        line_type (LineType or str): Type of :meth:`~.ContourGenerator.lines` as enum or string
            equivalent.

    Return:
        Contour lines in a single chunk.

    .. versionadded:: 1.2.0
    """
    line_type = as_line_type(line_type)

    if line_type in (LineType.Separate, LineType.SeparateCode):
        # No-op if line_type is not chunked.
        return lines

    check_lines(lines, line_type)
    if len(lines[0]) < 2:
        # No-op if just one chunk.
        return lines

    if TYPE_CHECKING:
        lines = cast(cpy.LineReturn_Chunk, lines)

    if line_type == LineType.ChunkCombinedCode:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedCode, lines)
        points = concat_points_or_none(lines[0])
        if points is None:
            ret1: cpy.LineReturn_ChunkCombinedCode = ([None], [None])
        else:
            ret1 = ([points], [concat_codes_or_none(lines[1])])
        return ret1
    elif line_type == LineType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedOffset, lines)
        points = concat_points_or_none(lines[0])
        if points is None:
            ret2: cpy.LineReturn_ChunkCombinedOffset = ([None], [None])
        else:
            ret2 = ([points], [concat_offsets_or_none(lines[1])])
        return ret2
    elif line_type == LineType.ChunkCombinedNan:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedNan, lines)
        points = concat_points_or_none_with_nan(lines[0])
        ret3: cpy.LineReturn_ChunkCombinedNan = ([points],)
        return ret3
    else:
        raise ValueError(f"Invalid LineType {line_type}")


def dechunk_multi_filled(
    multi_filled: list[cpy.FillReturn],
    fill_type: FillType | str,
) -> list[cpy.FillReturn]:
    """Return multiple sets of filled contours with chunked data moved into the first chunks.

    Filled contours that are not chunked (``FillType.OuterCode`` and ``FillType.OuterOffset``) and
    those that are but only contain a single chunk are returned unmodified. Individual polygons are
    unchanged, they are not geometrically combined.

    Args:
        multi_filled (nested sequence of arrays): Filled contour data, such as returned by
            :meth:`.ContourGenerator.multi_filled`.
        fill_type (FillType or str): Type of :meth:`~.ContourGenerator.filled` as enum or string
            equivalent.

    Return:
        Multiple sets of filled contours in a single chunk.

    .. versionadded:: 1.3.0
    """
    fill_type = as_fill_type(fill_type)

    if fill_type in (FillType.OuterCode, FillType.OuterOffset):
        # No-op if fill_type is not chunked.
        return multi_filled

    return [dechunk_filled(filled, fill_type) for filled in multi_filled]


def dechunk_multi_lines(
    multi_lines: list[cpy.LineReturn],
    line_type: LineType | str,
) -> list[cpy.LineReturn]:
    """Return multiple sets of contour lines with all chunked data moved into the first chunks.

    Contour lines that are not chunked (``LineType.Separate`` and ``LineType.SeparateCode``) and
    those that are but only contain a single chunk are returned unmodified. Individual lines are
    unchanged, they are not geometrically combined.

    Args:
        multi_lines (nested sequence of arrays): Contour line data, such as returned by
            :meth:`.ContourGenerator.multi_lines`.
        line_type (LineType or str): Type of :meth:`~.ContourGenerator.lines` as enum or string
            equivalent.

    Return:
        Multiple sets of contour lines in a single chunk.

    .. versionadded:: 1.3.0
    """
    line_type = as_line_type(line_type)

    if line_type in (LineType.Separate, LineType.SeparateCode):
        # No-op if line_type is not chunked.
        return multi_lines

    return [dechunk_lines(lines, line_type) for lines in multi_lines]

# === NexusCore/openenv\Lib\site-packages\googleapiclient\_helpers.py ===
# Copyright 2015 Google Inc. All rights reserved.
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

"""Helper functions for commonly used utilities."""

import functools
import inspect
import logging
import urllib

logger = logging.getLogger(__name__)

POSITIONAL_WARNING = "WARNING"
POSITIONAL_EXCEPTION = "EXCEPTION"
POSITIONAL_IGNORE = "IGNORE"
POSITIONAL_SET = frozenset(
    [POSITIONAL_WARNING, POSITIONAL_EXCEPTION, POSITIONAL_IGNORE]
)

positional_parameters_enforcement = POSITIONAL_WARNING

_SYM_LINK_MESSAGE = "File: {0}: Is a symbolic link."
_IS_DIR_MESSAGE = "{0}: Is a directory"
_MISSING_FILE_MESSAGE = "Cannot access {0}: No such file or directory"


def positional(max_positional_args):
    """A decorator to declare that only the first N arguments may be positional.

    This decorator makes it easy to support Python 3 style keyword-only
    parameters. For example, in Python 3 it is possible to write::

        def fn(pos1, *, kwonly1=None, kwonly2=None):
            ...

    All named parameters after ``*`` must be a keyword::

        fn(10, 'kw1', 'kw2')  # Raises exception.
        fn(10, kwonly1='kw1')  # Ok.

    Example
    ^^^^^^^

    To define a function like above, do::

        @positional(1)
        def fn(pos1, kwonly1=None, kwonly2=None):
            ...

    If no default value is provided to a keyword argument, it becomes a
    required keyword argument::

        @positional(0)
        def fn(required_kw):
            ...

    This must be called with the keyword parameter::

        fn()  # Raises exception.
        fn(10)  # Raises exception.
        fn(required_kw=10)  # Ok.

    When defining instance or class methods always remember to account for
    ``self`` and ``cls``::

        class MyClass(object):

            @positional(2)
            def my_method(self, pos1, kwonly1=None):
                ...

            @classmethod
            @positional(2)
            def my_method(cls, pos1, kwonly1=None):
                ...

    The positional decorator behavior is controlled by
    ``_helpers.positional_parameters_enforcement``, which may be set to
    ``POSITIONAL_EXCEPTION``, ``POSITIONAL_WARNING`` or
    ``POSITIONAL_IGNORE`` to raise an exception, log a warning, or do
    nothing, respectively, if a declaration is violated.

    Args:
        max_positional_arguments: Maximum number of positional arguments. All
                                  parameters after this index must be
                                  keyword only.

    Returns:
        A decorator that prevents using arguments after max_positional_args
        from being used as positional parameters.

    Raises:
        TypeError: if a keyword-only argument is provided as a positional
                   parameter, but only if
                   _helpers.positional_parameters_enforcement is set to
                   POSITIONAL_EXCEPTION.
    """

    def positional_decorator(wrapped):
        @functools.wraps(wrapped)
        def positional_wrapper(*args, **kwargs):
            if len(args) > max_positional_args:
                plural_s = ""
                if max_positional_args != 1:
                    plural_s = "s"
                message = (
                    "{function}() takes at most {args_max} positional "
                    "argument{plural} ({args_given} given)".format(
                        function=wrapped.__name__,
                        args_max=max_positional_args,
                        args_given=len(args),
                        plural=plural_s,
                    )
                )
                if positional_parameters_enforcement == POSITIONAL_EXCEPTION:
                    raise TypeError(message)
                elif positional_parameters_enforcement == POSITIONAL_WARNING:
                    logger.warning(message)
            return wrapped(*args, **kwargs)

        return positional_wrapper

    if isinstance(max_positional_args, int):
        return positional_decorator
    else:
        args, _, _, defaults, _, _, _ = inspect.getfullargspec(max_positional_args)
        return positional(len(args) - len(defaults))(max_positional_args)


def parse_unique_urlencoded(content):
    """Parses unique key-value parameters from urlencoded content.

    Args:
        content: string, URL-encoded key-value pairs.

    Returns:
        dict, The key-value pairs from ``content``.

    Raises:
        ValueError: if one of the keys is repeated.
    """
    urlencoded_params = urllib.parse.parse_qs(content)
    params = {}
    for key, value in urlencoded_params.items():
        if len(value) != 1:
            msg = "URL-encoded content contains a repeated value:" "%s -> %s" % (
                key,
                ", ".join(value),
            )
            raise ValueError(msg)
        params[key] = value[0]
    return params


def update_query_params(uri, params):
    """Updates a URI with new query parameters.

    If a given key from ``params`` is repeated in the ``uri``, then
    the URI will be considered invalid and an error will occur.

    If the URI is valid, then each value from ``params`` will
    replace the corresponding value in the query parameters (if
    it exists).

    Args:
        uri: string, A valid URI, with potential existing query parameters.
        params: dict, A dictionary of query parameters.

    Returns:
        The same URI but with the new query parameters added.
    """
    parts = urllib.parse.urlparse(uri)
    query_params = parse_unique_urlencoded(parts.query)
    query_params.update(params)
    new_query = urllib.parse.urlencode(query_params)
    new_parts = parts._replace(query=new_query)
    return urllib.parse.urlunparse(new_parts)


def _add_query_parameter(url, name, value):
    """Adds a query parameter to a url.

    Replaces the current value if it already exists in the URL.

    Args:
        url: string, url to add the query parameter to.
        name: string, query parameter name.
        value: string, query parameter value.

    Returns:
        Updated query parameter. Does not update the url if value is None.
    """
    if value is None:
        return url
    else:
        return update_query_params(url, {name: value})

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3709.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add maps for use with opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Logotypes in X.509 Certificates
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc3709.txt
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc6170

MAX = float('inf')


class HashAlgAndValue(univ.Sequence):
    pass

HashAlgAndValue.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hashAlg', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('hashValue', univ.OctetString())
)


class LogotypeDetails(univ.Sequence):
    pass

LogotypeDetails.componentType = namedtype.NamedTypes(
    namedtype.NamedType('mediaType', char.IA5String()),
    namedtype.NamedType('logotypeHash', univ.SequenceOf(
        componentType=HashAlgAndValue()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('logotypeURI', univ.SequenceOf(
        componentType=char.IA5String()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX)))
)


class LogotypeAudioInfo(univ.Sequence):
    pass

LogotypeAudioInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('fileSize', univ.Integer()),
    namedtype.NamedType('playTime', univ.Integer()),
    namedtype.NamedType('channels', univ.Integer()),
    namedtype.OptionalNamedType('sampleRate', univ.Integer().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.OptionalNamedType('language', char.IA5String().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)))
)


class LogotypeAudio(univ.Sequence):
    pass

LogotypeAudio.componentType = namedtype.NamedTypes(
    namedtype.NamedType('audioDetails', LogotypeDetails()),
    namedtype.OptionalNamedType('audioInfo', LogotypeAudioInfo())
)


class LogotypeImageType(univ.Integer):
    pass

LogotypeImageType.namedValues = namedval.NamedValues(
    ('grayScale', 0),
    ('color', 1)
)


class LogotypeImageResolution(univ.Choice):
    pass

LogotypeImageResolution.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numBits',
        univ.Integer().subtype(implicitTag=tag.Tag(
            tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('tableSize',
        univ.Integer().subtype(implicitTag=tag.Tag(
            tag.tagClassContext, tag.tagFormatSimple, 2)))
)


class LogotypeImageInfo(univ.Sequence):
    pass

LogotypeImageInfo.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('type', LogotypeImageType().subtype(
        implicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 0)).subtype(value='color')),
    namedtype.NamedType('fileSize', univ.Integer()),
    namedtype.NamedType('xSize', univ.Integer()),
    namedtype.NamedType('ySize', univ.Integer()),
    namedtype.OptionalNamedType('resolution', LogotypeImageResolution()),
    namedtype.OptionalNamedType('language', char.IA5String().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)))
)


class LogotypeImage(univ.Sequence):
    pass

LogotypeImage.componentType = namedtype.NamedTypes(
    namedtype.NamedType('imageDetails', LogotypeDetails()),
    namedtype.OptionalNamedType('imageInfo', LogotypeImageInfo())
)


class LogotypeData(univ.Sequence):
    pass

LogotypeData.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('image', univ.SequenceOf(
        componentType=LogotypeImage())),
    namedtype.OptionalNamedType('audio', univ.SequenceOf(
        componentType=LogotypeAudio()).subtype(
            implicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 1)))
)


class LogotypeReference(univ.Sequence):
    pass

LogotypeReference.componentType = namedtype.NamedTypes(
    namedtype.NamedType('refStructHash', univ.SequenceOf(
        componentType=HashAlgAndValue()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('refStructURI', univ.SequenceOf(
        componentType=char.IA5String()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX)))
)


class LogotypeInfo(univ.Choice):
    pass

LogotypeInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('direct',
        LogotypeData().subtype(implicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatConstructed, 0))),
    namedtype.NamedType('indirect', LogotypeReference().subtype(
        implicitTag=tag.Tag(tag.tagClassContext,
             tag.tagFormatConstructed, 1)))
)

# Other logotype type and associated object identifiers

id_logo_background = univ.ObjectIdentifier('1.3.6.1.5.5.7.20.2')

id_logo_loyalty = univ.ObjectIdentifier('1.3.6.1.5.5.7.20.1')

id_logo_certImage = rfc6170.id_logo_certImage


class OtherLogotypeInfo(univ.Sequence):
    pass

OtherLogotypeInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('logotypeType', univ.ObjectIdentifier()),
    namedtype.NamedType('info', LogotypeInfo())
)


# Logotype Certificate Extension

id_pe_logotype = univ.ObjectIdentifier('1.3.6.1.5.5.7.1.12')


class LogotypeExtn(univ.Sequence):
    pass

LogotypeExtn.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('communityLogos', univ.SequenceOf(
        componentType=LogotypeInfo()).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('issuerLogo', LogotypeInfo().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.OptionalNamedType('subjectLogo', LogotypeInfo().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.OptionalNamedType('otherLogos', univ.SequenceOf(
        componentType=OtherLogotypeInfo()).subtype(explicitTag=tag.Tag(
            tag.tagClassContext, tag.tagFormatSimple, 3)))
)


# Map of Certificate Extension OIDs to Extensions added to the
# ones that are in rfc5280.py

_certificateExtensionsMapUpdate = {
    id_pe_logotype: LogotypeExtn(),
}

rfc5280.certificateExtensionsMap.update(_certificateExtensionsMapUpdate)

# === NexusCore/openenv\Lib\site-packages\tokentrim\tokentrim.py ===
import tiktoken
from typing import List, Dict, Any, Tuple, Optional, Union
from .model_map import MODEL_MAX_TOKENS
from .format_function_calls import get_function_calls_token_count

MAX_ITERATIONS = 12


def get_encoding(model):
  # Attempt to get the encoding for the specified model
  if model == None:
    encoding = tiktoken.get_encoding("cl100k_base")
  else:
    try:
      encoding = tiktoken.encoding_for_model(model)
    except KeyError:
      encoding = tiktoken.get_encoding("cl100k_base")

  return encoding


def num_tokens_from_messages(messages: List[Dict[str, Any]], model) -> int:
  """
  Function to return the number of tokens used by a list of messages.
  """

  encoding = get_encoding(model)

  # Token handling specifics for different model types
  if model == None:
    # Slightly raised numbers for an unknown model / prompt template
    # In the future this should be customizable
    tokens_per_message = 4
    tokens_per_name = 2
  else:
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
      tokens_per_message = 3
      tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
      tokens_per_message = 4
      tokens_per_name = -1
    elif "gpt-3.5-turbo" in model:
      return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
      return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
      # Slightly raised numbers for an unknown model / prompt template
      # In the future this should be customizable
      tokens_per_message = 4
      tokens_per_name = 2

  # Calculate the number of tokens
  num_tokens = 0
  for message in messages:
    num_tokens += tokens_per_message
    for key, value in message.items():
      try:
        num_tokens += len(encoding.encode(str(value)))
        if key == "name":
          num_tokens += tokens_per_name
      except:
        print(f"Failed to parse '{key}'.")
        pass

  num_tokens += 3
  return num_tokens


def shorten_message_to_fit_limit(message: Dict[str, Any], tokens_needed: int,
                                 model) -> None:
  """
  Shorten a message to fit within a token limit by removing characters from the middle.
  """
  iterations = 0

  encoding = get_encoding(model)

  content = message["content"]

  while iterations < MAX_ITERATIONS:
    total_tokens = num_tokens_from_messages([message], model)

    if total_tokens <= tokens_needed:
      break

    ratio = (tokens_needed) / total_tokens

    new_length = int(len(encoding.encode(content)) * ratio)

    half_length = new_length // 2
    left_half = encoding.decode(encoding.encode(content[:half_length]))
    right_half = encoding.decode(encoding.encode(content[-half_length:]))

    trimmed_content = left_half + '...' + right_half
    message["content"] = trimmed_content
    content = trimmed_content

    iterations += 1


def trim(
  messages: List[Dict[str, Any]],
  model=None,
  system_message: Optional[str] = None,
  trim_ratio: float = 0.75,
  return_response_tokens: bool = False,
  max_tokens=None,
  function_calls: Optional[List[Dict]] = None,
) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], int]]:
  """
    Trim a list of messages to fit within a model's token limit.

    Args:
        messages: Input messages to be trimmed. Each message is a dictionary with 'role' and 'content'.
        model: The OpenAI model being used (determines the token limit).
        system_message: Optional system message to preserve at the start of the conversation.
        trim_ratio: Target ratio of tokens to use after trimming. Default is 0.75, meaning it will trim messages so they use about 75% of the model's token limit.
        return_response_tokens: If True, also return the number of tokens left available for the response after trimming.
        max_tokens: Instead of specifying a model or trim_ratio, you can specify this directly.

    Returns:
        Trimmed messages and optionally the number of tokens available for response.
    """

  # Initialize max_tokens
  if max_tokens == None:

    # Check if model is valid
    if model not in MODEL_MAX_TOKENS:
      raise ValueError(f"Invalid model: {model}. Specify max_tokens instead")

    max_tokens = int(MODEL_MAX_TOKENS[model] * trim_ratio)

  if function_calls is not None:
    function_calls_token_cnt = get_function_calls_token_count(
      get_encoding(model), function_calls)
    max_tokens -= function_calls_token_cnt

  # Deduct the system message tokens from the max_tokens if system message exists
  if system_message:

    system_message_event = {"role": "system", "content": system_message}
    system_message_tokens = num_tokens_from_messages([system_message_event],
                                                     model)

    if system_message_tokens > max_tokens:
      print(
        "`tokentrim`: Warning, system message exceeds token limit, which is probably undesired. Trimming..."
      )

      shorten_message_to_fit_limit(system_message_event, max_tokens, model)
      system_message_tokens = num_tokens_from_messages([system_message_event],
                                                       model)

    max_tokens -= system_message_tokens

    max_tokens -= system_message_tokens

  final_messages = []

  # Reverse the messages so we process oldest messages first
  messages = messages[::-1]

  # Process the messages
  for message in messages:
    temp_messages = [message] + final_messages
    temp_messages_tokens = num_tokens_from_messages(temp_messages, model)

    if temp_messages_tokens <= max_tokens:
      # If adding the next message doesn't exceed the token limit, add it to final_messages
      final_messages = [message] + final_messages
    else:
      final_messages_tokens = num_tokens_from_messages(final_messages, model)
      tokens_remaining = max_tokens - final_messages_tokens

      # If we have some tokens to play with, we can try trimming the top message.
      if True:

        # If adding the next message exceeds the token limit, try trimming it
        # (This only works for non-function call messages)
        if "function_call" not in message:
          shorten_message_to_fit_limit(message, tokens_remaining, model)

        # If the trimmed message can fit, add it
        if num_tokens_from_messages(
          [message], model) + final_messages_tokens <= max_tokens:
          final_messages = [message] + final_messages

      break

  # Add system message to the start of final_messages if it exists
  if system_message:
    final_messages = [system_message_event] + final_messages

  if return_response_tokens:
    response_tokens = max_tokens - num_tokens_from_messages(
      final_messages, model)
    return final_messages, response_tokens

  return final_messages

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\terminal.py ===
import json
import os
import time
import subprocess
import getpass

from ..utils.recipient_utils import parse_for_recipient
from .languages.applescript import AppleScript
from .languages.html import HTML
from .languages.java import Java
from .languages.javascript import JavaScript
from .languages.powershell import PowerShell
from .languages.python import Python
from .languages.r import R
from .languages.react import React
from .languages.ruby import Ruby
from .languages.shell import Shell

# Should this be renamed to OS or System?

import_computer_api_code = """
import os
os.environ["INTERPRETER_COMPUTER_API"] = "False" # To prevent infinite recurring import of the computer API

import time
import datetime
from interpreter import interpreter

computer = interpreter.computer
""".strip()


class Terminal:
    def __init__(self, computer):
        self.computer = computer
        self.languages = [
            Ruby,
            Python,
            Shell,
            JavaScript,
            HTML,
            AppleScript,
            R,
            PowerShell,
            React,
            Java,
        ]
        self._active_languages = {}

    def sudo_install(self, package):
        try:
            # First, try to install without sudo
            subprocess.run(['apt', 'install', '-y', package], check=True)
        except subprocess.CalledProcessError:
            # If it fails, try with sudo
            print(f"Installation of {package} requires sudo privileges.")
            sudo_password = getpass.getpass("Enter sudo password: ")

            try:
                # Use sudo with password
                subprocess.run(
                    ['sudo', '-S', 'apt', 'install', '-y', package],
                    input=sudo_password.encode(),
                    check=True
                )
                print(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}. Error: {e}")
                return False

        return True

    def get_language(self, language):
        for lang in self.languages:
            if language.lower() == lang.name.lower() or (
                hasattr(lang, "aliases")
                and language.lower() in (alias.lower() for alias in lang.aliases)
            ):
                return lang
        return None

    def run(self, language, code, stream=False, display=False):
        # Check if this is an apt install command
        if language == "shell" and code.strip().startswith("apt install"):
            package = code.split()[-1]
            if self.sudo_install(package):
                return [{"type": "console", "format": "output", "content": f"Package {package} installed successfully."}]
            else:
                return [{"type": "console", "format": "output", "content": f"Failed to install package {package}."}]

        if language == "python":
            if (
                self.computer.import_computer_api
                and not self.computer._has_imported_computer_api
                and "computer" in code
                and os.getenv("INTERPRETER_COMPUTER_API", "True") != "False"
            ):
                self.computer._has_imported_computer_api = True
                # Give it access to the computer via Python
                time.sleep(0.5)
                self.computer.run(
                    language="python",
                    code=import_computer_api_code,
                    display=self.computer.verbose,
                )

            if self.computer.import_skills and not self.computer._has_imported_skills:
                self.computer._has_imported_skills = True
                self.computer.skills.import_skills()

            # This won't work because truncated code is stored in interpreter.messages :/
            # If the full code was stored, we could do this:
            if False and "get_last_output()" in code:
                if "# We wouldn't want to have maximum recursion depth!" in code:
                    # We just tried to run this, in a moment.
                    pass
                else:
                    code_outputs = [
                        m
                        for m in self.computer.interpreter.messages
                        if m["role"] == "computer"
                        and "content" in m
                        and m["content"] != ""
                    ]
                    if len(code_outputs) > 0:
                        last_output = code_outputs[-1]["content"]
                    else:
                        last_output = ""
                    last_output = json.dumps(last_output)

                    self.computer.run(
                        "python",
                        f"# We wouldn't want to have maximum recursion depth!\nimport json\ndef get_last_output():\n    return '''{last_output}'''",
                    )

        if stream == False:
            # If stream == False, *pull* from _streaming_run.
            output_messages = []
            for chunk in self._streaming_run(language, code, display=display):
                if chunk.get("format") != "active_line":
                    # Should we append this to the last message, or make a new one?
                    if (
                        output_messages != []
                        and output_messages[-1].get("type") == chunk["type"]
                        and output_messages[-1].get("format") == chunk["format"]
                    ):
                        output_messages[-1]["content"] += chunk["content"]
                    else:
                        output_messages.append(chunk)
            return output_messages

        elif stream == True:
            # If stream == True, replace this with _streaming_run.
            return self._streaming_run(language, code, display=display)

    def _streaming_run(self, language, code, display=False):
        if language not in self._active_languages:
            # Get the language. Pass in self.computer *if it takes a single argument*
            # but pass in nothing if not. This makes custom languages easier to add / understand.
            lang_class = self.get_language(language)
            if lang_class.__init__.__code__.co_argcount > 1:
                self._active_languages[language] = lang_class(self.computer)
            else:
                self._active_languages[language] = lang_class()
        try:
            for chunk in self._active_languages[language].run(code):
                # self.format_to_recipient can format some messages as having a certain recipient.
                # Here we add that to the LMC messages:
                if chunk["type"] == "console" and chunk.get("format") == "output":
                    recipient, content = parse_for_recipient(chunk["content"])
                    if recipient:
                        chunk["recipient"] = recipient
                        chunk["content"] = content

                    # Sometimes, we want to hide the traceback to preserve tokens.
                    # (is this a good idea?)
                    if "@@@HIDE_TRACEBACK@@@" in content:
                        chunk["content"] = (
                            "Stopping execution.\n\n"
                            + content.split("@@@HIDE_TRACEBACK@@@")[-1].strip()
                        )

                yield chunk

                # Print it also if display = True
                if (
                    display
                    and chunk.get("format") != "active_line"
                    and chunk.get("content")
                ):
                    print(chunk["content"], end="")

        except GeneratorExit:
            self.stop()

    def stop(self):
        for language in self._active_languages.values():
            language.stop()

    def terminate(self):
        for language_name in list(self._active_languages.keys()):
            language = self._active_languages[language_name]
            if (
                language
            ):  # Not sure why this is None sometimes. We should look into this
                language.terminate()
            del self._active_languages[language_name]

# === NexusCore/openenv\Lib\site-packages\nltk\tag\crf.py ===
# Natural Language Toolkit: Interface to the CRFSuite Tagger
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for POS tagging using CRFSuite
"""

import re
import unicodedata

from nltk.tag.api import TaggerI

try:
    import pycrfsuite
except ImportError:
    pass


class CRFTagger(TaggerI):
    """
    A module for POS tagging using CRFSuite https://pypi.python.org/pypi/python-crfsuite

    >>> from nltk.tag import CRFTagger
    >>> ct = CRFTagger()  # doctest: +SKIP

    >>> train_data = [[('University','Noun'), ('is','Verb'), ('a','Det'), ('good','Adj'), ('place','Noun')],
    ... [('dog','Noun'),('eat','Verb'),('meat','Noun')]]

    >>> ct.train(train_data,'model.crf.tagger')  # doctest: +SKIP
    >>> ct.tag_sents([['dog','is','good'], ['Cat','eat','meat']])  # doctest: +SKIP
    [[('dog', 'Noun'), ('is', 'Verb'), ('good', 'Adj')], [('Cat', 'Noun'), ('eat', 'Verb'), ('meat', 'Noun')]]

    >>> gold_sentences = [[('dog','Noun'),('is','Verb'),('good','Adj')] , [('Cat','Noun'),('eat','Verb'), ('meat','Noun')]]
    >>> ct.accuracy(gold_sentences)  # doctest: +SKIP
    1.0

    Setting learned model file
    >>> ct = CRFTagger()  # doctest: +SKIP
    >>> ct.set_model_file('model.crf.tagger')  # doctest: +SKIP
    >>> ct.accuracy(gold_sentences)  # doctest: +SKIP
    1.0
    """

    def __init__(self, feature_func=None, verbose=False, training_opt={}):
        """
        Initialize the CRFSuite tagger

        :param feature_func: The function that extracts features for each token of a sentence. This function should take
            2 parameters: tokens and index which extract features at index position from tokens list. See the build in
            _get_features function for more detail.
        :param verbose: output the debugging messages during training.
        :type verbose: boolean
        :param training_opt: python-crfsuite training options
        :type training_opt: dictionary

        Set of possible training options (using LBFGS training algorithm).
            :'feature.minfreq': The minimum frequency of features.
            :'feature.possible_states': Force to generate possible state features.
            :'feature.possible_transitions': Force to generate possible transition features.
            :'c1': Coefficient for L1 regularization.
            :'c2': Coefficient for L2 regularization.
            :'max_iterations': The maximum number of iterations for L-BFGS optimization.
            :'num_memories': The number of limited memories for approximating the inverse hessian matrix.
            :'epsilon': Epsilon for testing the convergence of the objective.
            :'period': The duration of iterations to test the stopping criterion.
            :'delta': The threshold for the stopping criterion; an L-BFGS iteration stops when the
                improvement of the log likelihood over the last ${period} iterations is no greater than this threshold.
            :'linesearch': The line search algorithm used in L-BFGS updates:

                - 'MoreThuente': More and Thuente's method,
                - 'Backtracking': Backtracking method with regular Wolfe condition,
                - 'StrongBacktracking': Backtracking method with strong Wolfe condition
            :'max_linesearch':  The maximum number of trials for the line search algorithm.
        """

        self._model_file = ""
        self._tagger = pycrfsuite.Tagger()

        if feature_func is None:
            self._feature_func = self._get_features
        else:
            self._feature_func = feature_func

        self._verbose = verbose
        self._training_options = training_opt
        self._pattern = re.compile(r"\d")

    def set_model_file(self, model_file):
        self._model_file = model_file
        self._tagger.open(self._model_file)

    def _get_features(self, tokens, idx):
        """
        Extract basic features about this word including
            - Current word
            - is it capitalized?
            - Does it have punctuation?
            - Does it have a number?
            - Suffixes up to length 3

        Note that : we might include feature over previous word, next word etc.

        :return: a list which contains the features
        :rtype: list(str)
        """
        token = tokens[idx]

        feature_list = []

        if not token:
            return feature_list

        # Capitalization
        if token[0].isupper():
            feature_list.append("CAPITALIZATION")

        # Number
        if re.search(self._pattern, token) is not None:
            feature_list.append("HAS_NUM")

        # Punctuation
        punc_cat = {"Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"}
        if all(unicodedata.category(x) in punc_cat for x in token):
            feature_list.append("PUNCTUATION")

        # Suffix up to length 3
        if len(token) > 1:
            feature_list.append("SUF_" + token[-1:])
        if len(token) > 2:
            feature_list.append("SUF_" + token[-2:])
        if len(token) > 3:
            feature_list.append("SUF_" + token[-3:])

        feature_list.append("WORD_" + token)

        return feature_list

    def tag_sents(self, sents):
        """
        Tag a list of sentences. NB before using this function, user should specify the mode_file either by

        - Train a new model using ``train`` function
        - Use the pre-trained model which is set via ``set_model_file`` function

        :params sentences: list of sentences needed to tag.
        :type sentences: list(list(str))
        :return: list of tagged sentences.
        :rtype: list(list(tuple(str,str)))
        """
        if self._model_file == "":
            raise Exception(
                " No model file is found !! Please use train or set_model_file function"
            )

        # We need the list of sentences instead of the list generator for matching the input and output
        result = []
        for tokens in sents:
            features = [self._feature_func(tokens, i) for i in range(len(tokens))]
            labels = self._tagger.tag(features)

            if len(labels) != len(tokens):
                raise Exception(" Predicted Length Not Matched, Expect Errors !")

            tagged_sent = list(zip(tokens, labels))
            result.append(tagged_sent)

        return result

    def train(self, train_data, model_file):
        """
        Train the CRF tagger using CRFSuite
        :params train_data : is the list of annotated sentences.
        :type train_data : list (list(tuple(str,str)))
        :params model_file : the model will be saved to this file.

        """
        trainer = pycrfsuite.Trainer(verbose=self._verbose)
        trainer.set_params(self._training_options)

        for sent in train_data:
            tokens, labels = zip(*sent)
            features = [self._feature_func(tokens, i) for i in range(len(tokens))]
            trainer.append(features, labels)

        # Now train the model, the output should be model_file
        trainer.train(model_file)
        # Save the model file
        self.set_model_file(model_file)

    def tag(self, tokens):
        """
        Tag a sentence using Python CRFSuite Tagger. NB before using this function, user should specify the mode_file either by

        - Train a new model using ``train`` function
        - Use the pre-trained model which is set via ``set_model_file`` function

        :params tokens: list of tokens needed to tag.
        :type tokens: list(str)
        :return: list of tagged tokens.
        :rtype: list(tuple(str,str))
        """

        return self.tag_sents([tokens])[0]

# === NexusCore/openenv\Lib\site-packages\numpy\testing\print_coercion_tables.py ===
#!/usr/bin/env python3
"""Prints type-coercion tables for the built-in NumPy types

"""
from collections import namedtuple

import numpy as np
from numpy._core.numerictypes import obj2sctype


# Generic object that can be added, but doesn't do anything else
class GenericObject:
    def __init__(self, v):
        self.v = v

    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    dtype = np.dtype('O')

def print_cancast_table(ntypes):
    print('X', end=' ')
    for char in ntypes:
        print(char, end=' ')
    print()
    for row in ntypes:
        print(row, end=' ')
        for col in ntypes:
            if np.can_cast(row, col, "equiv"):
                cast = "#"
            elif np.can_cast(row, col, "safe"):
                cast = "="
            elif np.can_cast(row, col, "same_kind"):
                cast = "~"
            elif np.can_cast(row, col, "unsafe"):
                cast = "."
            else:
                cast = " "
            print(cast, end=' ')
        print()

def print_coercion_table(ntypes, inputfirstvalue, inputsecondvalue, firstarray,
                         use_promote_types=False):
    print('+', end=' ')
    for char in ntypes:
        print(char, end=' ')
    print()
    for row in ntypes:
        if row == 'O':
            rowtype = GenericObject
        else:
            rowtype = obj2sctype(row)

        print(row, end=' ')
        for col in ntypes:
            if col == 'O':
                coltype = GenericObject
            else:
                coltype = obj2sctype(col)
            try:
                if firstarray:
                    rowvalue = np.array([rowtype(inputfirstvalue)], dtype=rowtype)
                else:
                    rowvalue = rowtype(inputfirstvalue)
                colvalue = coltype(inputsecondvalue)
                if use_promote_types:
                    char = np.promote_types(rowvalue.dtype, colvalue.dtype).char
                else:
                    value = np.add(rowvalue, colvalue)
                    if isinstance(value, np.ndarray):
                        char = value.dtype.char
                    else:
                        char = np.dtype(type(value)).char
            except ValueError:
                char = '!'
            except OverflowError:
                char = '@'
            except TypeError:
                char = '#'
            print(char, end=' ')
        print()


def print_new_cast_table(*, can_cast=True, legacy=False, flags=False):
    """Prints new casts, the values given are default "can-cast" values, not
    actual ones.
    """
    from numpy._core._multiarray_tests import get_all_cast_information

    cast_table = {
        -1: " ",
        0: "#",  # No cast (classify as equivalent here)
        1: "#",  # equivalent casting
        2: "=",  # safe casting
        3: "~",  # same-kind casting
        4: ".",  # unsafe casting
    }
    flags_table = {
        0: "▗", 7: "█",
        1: "▚", 2: "▐", 4: "▄",
                3: "▜", 5: "▙",
                        6: "▟",
    }

    cast_info = namedtuple("cast_info", ["can_cast", "legacy", "flags"])
    no_cast_info = cast_info(" ", " ", " ")

    casts = get_all_cast_information()
    table = {}
    dtypes = set()
    for cast in casts:
        dtypes.add(cast["from"])
        dtypes.add(cast["to"])

        if cast["from"] not in table:
            table[cast["from"]] = {}
        to_dict = table[cast["from"]]

        can_cast = cast_table[cast["casting"]]
        legacy = "L" if cast["legacy"] else "."
        flags = 0
        if cast["requires_pyapi"]:
            flags |= 1
        if cast["supports_unaligned"]:
            flags |= 2
        if cast["no_floatingpoint_errors"]:
            flags |= 4

        flags = flags_table[flags]
        to_dict[cast["to"]] = cast_info(can_cast=can_cast, legacy=legacy, flags=flags)

    # The np.dtype(x.type) is a bit strange, because dtype classes do
    # not expose much yet.
    types = np.typecodes["All"]

    def sorter(x):
        # This is a bit weird hack, to get a table as close as possible to
        # the one printing all typecodes (but expecting user-dtypes).
        dtype = np.dtype(x.type)
        try:
            indx = types.index(dtype.char)
        except ValueError:
            indx = np.inf
        return (indx, dtype.char)

    dtypes = sorted(dtypes, key=sorter)

    def print_table(field="can_cast"):
        print('X', end=' ')
        for dt in dtypes:
            print(np.dtype(dt.type).char, end=' ')
        print()
        for from_dt in dtypes:
            print(np.dtype(from_dt.type).char, end=' ')
            row = table.get(from_dt, {})
            for to_dt in dtypes:
                print(getattr(row.get(to_dt, no_cast_info), field), end=' ')
            print()

    if can_cast:
        # Print the actual table:
        print()
        print("Casting: # is equivalent, = is safe, ~ is same-kind, and . is unsafe")
        print()
        print_table("can_cast")

    if legacy:
        print()
        print("L denotes a legacy cast . a non-legacy one.")
        print()
        print_table("legacy")

    if flags:
        print()
        print(f"{flags_table[0]}: no flags, "
              f"{flags_table[1]}: PyAPI, "
              f"{flags_table[2]}: supports unaligned, "
              f"{flags_table[4]}: no-float-errors")
        print()
        print_table("flags")


if __name__ == '__main__':
    print("can cast")
    print_cancast_table(np.typecodes['All'])
    print()
    print("In these tables, ValueError is '!', OverflowError is '@', TypeError is '#'")
    print()
    print("scalar + scalar")
    print_coercion_table(np.typecodes['All'], 0, 0, False)
    print()
    print("scalar + neg scalar")
    print_coercion_table(np.typecodes['All'], 0, -1, False)
    print()
    print("array + scalar")
    print_coercion_table(np.typecodes['All'], 0, 0, True)
    print()
    print("array + neg scalar")
    print_coercion_table(np.typecodes['All'], 0, -1, True)
    print()
    print("promote_types")
    print_coercion_table(np.typecodes['All'], 0, 0, False, True)
    print("New casting type promotion:")
    print_new_cast_table(can_cast=True, legacy=True, flags=True)

# === NexusCore/evaluation\evalplus\tools\humaneval\to_original_fmt.py ===
import ast
import inspect
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from tqdm import tqdm

from evalplus.data.humaneval import (
    HUMANEVAL_PLUS_VERSION,
    get_human_eval_plus,
    get_human_eval_plus_hash,
)
from evalplus.eval import is_floats
from evalplus.eval._special_oracle import _poly
from evalplus.evaluate import get_groundtruth

HUMANEVAL_TEST_TEMPLATE = """\
{imports}

{aux_fn}

def check(candidate):
    inputs = {inputs}
    results = {results}
    for i, (inp, exp) in enumerate(zip(inputs, results)):
        {assertion}
"""

HUMANEVAL_CROSSCHECK_TEMPLATE = """\
{aux_fn}

{ref_func}

def check(candidate):
    inputs = {inputs}
    for i, inp in enumerate(inputs):
        assertion(candidate(*inp), ref_func(*inp), {atol})
"""

ASSERTION_FN = f"""\
import numpy as np

{inspect.getsource(is_floats)}

def assertion(out, exp, atol):
    exact_match = out == exp

    if atol == 0 and is_floats(exp):
        atol = 1e-6
    if not exact_match and atol != 0:
        assert np.allclose(out, exp, rtol=1e-07, atol=atol)
    else:
        assert exact_match
"""


def synthesize_test_code(task_id, entry_point, inputs, results, ref_func, atol):
    # dataset size optimization for large outputs
    if entry_point in (
        "tri",
        "string_sequence",
        "starts_one_ends",
        "make_a_pile",
        "special_factorial",
        "all_prefixes",
    ):
        return task_id, HUMANEVAL_CROSSCHECK_TEMPLATE.format(
            aux_fn=ASSERTION_FN,
            inputs=inputs,
            ref_func=ref_func.replace(f" {entry_point}(", " ref_func("),
            atol=atol,
        )

    # default settings
    imports = set()
    aux_fn = ASSERTION_FN
    assertion = f"assertion(candidate(*inp), exp, {atol})"

    # special case: poly
    if entry_point == "find_zero":
        imports.add("import math")
        aux_fn = inspect.getsource(_poly) + "\n"
        assertion = f"assert _poly(*candidate(*inp), inp) <= {atol}"

    return task_id, HUMANEVAL_TEST_TEMPLATE.format(
        imports="\n".join(imports),
        aux_fn=aux_fn,
        inputs=inputs,
        results=results,
        assertion=assertion,
    )


def deduplicate(inputs, results):
    assert len(inputs) == len(results)
    unique_input_strs = set([f"{x}" for x in inputs])

    new_inputs, new_results = [], []
    for inp, res in zip(inputs, results):
        inp_str = f"{inp}"
        if inp_str in unique_input_strs:
            new_inputs.append(inp)
            new_results.append(res)
            unique_input_strs.remove(inp_str)

    return new_inputs, new_results


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-tasks", nargs="+", default=[], type=int)

    args = parser.parse_args()

    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(int(10e8))

    plus_problems = get_human_eval_plus(mini=False)
    dataset_hash = get_human_eval_plus_hash()

    compatible_problems = {}
    expected_outputs = get_groundtruth(plus_problems, dataset_hash, [])

    # debugging: monitoring test code size
    id2bytes = {}

    n_workers = max(1, multiprocessing.cpu_count() // 4)
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = []
        for task_id, plus_form in tqdm(plus_problems.items()):
            if args.debug_tasks and int(task_id.split("/")[-1]) not in args.debug_tasks:
                continue

            compatible_form = {}
            compatible_form["task_id"] = task_id
            compatible_form["prompt"] = plus_form["prompt"]
            compatible_form["canonical_solution"] = plus_form["canonical_solution"]
            compatible_form["entry_point"] = plus_form["entry_point"]
            compatible_problems[task_id] = compatible_form

            inputs = plus_form["base_input"] + plus_form["plus_input"]
            results = (
                expected_outputs[task_id]["base"] + expected_outputs[task_id]["plus"]
            )

            inputs, results = deduplicate(inputs, results)

            assert len(inputs) == len(results)
            atol = plus_form["atol"]

            simplified_prompt = ""
            for line in compatible_form["prompt"].split("\n"):
                if not line:
                    continue
                if '"""' in line or "'''" in line:
                    break
                simplified_prompt += line + "\n"

            futures.append(
                executor.submit(
                    synthesize_test_code,
                    task_id,
                    compatible_form["entry_point"],
                    inputs,
                    results,
                    simplified_prompt + compatible_form["canonical_solution"],
                    atol,
                )
            )

        for future in tqdm(as_completed(futures), total=len(plus_problems)):
            task_id, test_code = future.result()
            # syntax check of test_code
            ast.parse(test_code)
            id2bytes[task_id] = len(test_code.encode("utf-8"))
            compatible_problems[task_id]["test"] = test_code

    # print the top-10 largest test code
    print("Top-10 largest test code comes from problems (in megabytes):")
    for task_id, size in sorted(id2bytes.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"{task_id}:\t{size / 1024 / 1024:.2f}mb")

    if args.debug_tasks:
        for problem in compatible_problems.values():
            print("--- debugging:", problem["task_id"])
            print(problem["prompt"] + problem["canonical_solution"])
            test_code = problem["test"]
            if len(test_code) <= 2048 + 512:
                print(test_code)
            else:
                print(problem["test"][:1024], "...")
                print("...", problem["test"][-1024:])
    else:
        with open(f"HumanEvalPlus-OriginFmt-{HUMANEVAL_PLUS_VERSION}.jsonl", "w") as f:
            for problem in compatible_problems.values():
                f.write(json.dumps(problem) + "\n")


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\pure_eval\utils.py ===
from collections import OrderedDict, deque
from datetime import date, time, datetime
from decimal import Decimal
from fractions import Fraction
import ast
import enum
import typing


class CannotEval(Exception):
    def __repr__(self):
        return self.__class__.__name__

    __str__ = __repr__


def is_any(x, *args):
    return any(
        x is arg
        for arg in args
    )


def of_type(x, *types):
    if is_any(type(x), *types):
        return x
    else:
        raise CannotEval


def of_standard_types(x, *, check_dict_values: bool, deep: bool):
    if is_standard_types(x, check_dict_values=check_dict_values, deep=deep):
        return x
    else:
        raise CannotEval


def is_standard_types(x, *, check_dict_values: bool, deep: bool):
    try:
        return _is_standard_types_deep(x, check_dict_values, deep)[0]
    except RecursionError:
        return False


def _is_standard_types_deep(x, check_dict_values: bool, deep: bool):
    typ = type(x)
    if is_any(
        typ,
        str,
        int,
        bool,
        float,
        bytes,
        complex,
        date,
        time,
        datetime,
        Fraction,
        Decimal,
        type(None),
        object,
    ):
        return True, 0

    if is_any(typ, tuple, frozenset, list, set, dict, OrderedDict, deque, slice):
        if typ in [slice]:
            length = 0
        else:
            length = len(x)
        assert isinstance(deep, bool)
        if not deep:
            return True, length

        if check_dict_values and typ in (dict, OrderedDict):
            items = (v for pair in x.items() for v in pair)
        elif typ is slice:
            items = [x.start, x.stop, x.step]
        else:
            items = x
        for item in items:
            if length > 100000:
                return False, length
            is_standard, item_length = _is_standard_types_deep(
                item, check_dict_values, deep
            )
            if not is_standard:
                return False, length
            length += item_length
        return True, length

    return False, 0


class _E(enum.Enum):
    pass


class _C:
    def foo(self): pass  # pragma: nocover

    def bar(self): pass  # pragma: nocover

    @classmethod
    def cm(cls): pass  # pragma: nocover

    @staticmethod
    def sm(): pass  # pragma: nocover


safe_name_samples = {
    "len": len,
    "append": list.append,
    "__add__": list.__add__,
    "insert": [].insert,
    "__mul__": [].__mul__,
    "fromkeys": dict.__dict__['fromkeys'],
    "is_any": is_any,
    "__repr__": CannotEval.__repr__,
    "foo": _C().foo,
    "bar": _C.bar,
    "cm": _C.cm,
    "sm": _C.sm,
    "ast": ast,
    "CannotEval": CannotEval,
    "_E": _E,
}

typing_annotation_samples = {
    name: getattr(typing, name)
    for name in "List Dict Tuple Set Callable Mapping".split()
}

safe_name_types = tuple({
    type(f)
    for f in safe_name_samples.values()
})


typing_annotation_types = tuple({
    type(f)
    for f in typing_annotation_samples.values()
})


def eq_checking_types(a, b):
    return type(a) is type(b) and a == b


def ast_name(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    else:
        return None


def safe_name(value):
    typ = type(value)
    if is_any(typ, *safe_name_types):
        return value.__name__
    elif value is typing.Optional:
        return "Optional"
    elif value is typing.Union:
        return "Union"
    elif is_any(typ, *typing_annotation_types):
        return getattr(value, "__name__", None) or getattr(value, "_name", None)
    else:
        return None


def has_ast_name(value, node):
    value_name = safe_name(value)
    if type(value_name) is not str:
        return False
    return eq_checking_types(ast_name(node), value_name)


def copy_ast_without_context(x):
    if isinstance(x, ast.AST):
        kwargs = {
            field: copy_ast_without_context(getattr(x, field))
            for field in x._fields
            if field != 'ctx'
            if hasattr(x, field)
        }
        a = type(x)(**kwargs)
        if hasattr(a, 'ctx'):
            # Python 3.13.0b2+ defaults to Load when we don't pass ctx
            # https://github.com/python/cpython/pull/118871
            del a.ctx
        return a
    elif isinstance(x, list):
        return list(map(copy_ast_without_context, x))
    else:
        return x


def ensure_dict(x):
    """
    Handles invalid non-dict inputs
    """
    try:
        return dict(x)
    except Exception:
        return {}

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles_nose.py ===
from nose.plugins.multiprocess import MultiProcessTestRunner  # @UnresolvedImport
from nose.plugins.base import Plugin  # @UnresolvedImport
import sys
from _pydev_runfiles import pydev_runfiles_xml_rpc
import time
from _pydev_runfiles.pydev_runfiles_coverage import start_coverage_support
from contextlib import contextmanager
from io import StringIO
import traceback


# =======================================================================================================================
# PydevPlugin
# =======================================================================================================================
class PydevPlugin(Plugin):
    def __init__(self, configuration):
        self.configuration = configuration
        Plugin.__init__(self)

    def begin(self):
        # Called before any test is run (it's always called, with multiprocess or not)
        self.start_time = time.time()
        self.coverage_files, self.coverage = start_coverage_support(self.configuration)

    def finalize(self, result):
        # Called after all tests are run (it's always called, with multiprocess or not)
        self.coverage.stop()
        self.coverage.save()

        pydev_runfiles_xml_rpc.notifyTestRunFinished("Finished in: %.2f secs." % (time.time() - self.start_time,))

    # ===================================================================================================================
    # Methods below are not called with multiprocess (so, we monkey-patch MultiProcessTestRunner.consolidate
    # so that they're called, but unfortunately we loose some info -- i.e.: the time for each test in this
    # process).
    # ===================================================================================================================

    class Sentinel(object):
        pass

    @contextmanager
    def _without_user_address(self, test):
        # #PyDev-1095: Conflict between address in test and test.address() in PydevPlugin().report_cond()
        user_test_instance = test.test
        user_address = self.Sentinel
        user_class_address = self.Sentinel
        try:
            if "address" in user_test_instance.__dict__:
                user_address = user_test_instance.__dict__.pop("address")
        except:
            # Just ignore anything here.
            pass
        try:
            user_class_address = user_test_instance.__class__.address
            del user_test_instance.__class__.address
        except:
            # Just ignore anything here.
            pass

        try:
            yield
        finally:
            if user_address is not self.Sentinel:
                user_test_instance.__dict__["address"] = user_address

            if user_class_address is not self.Sentinel:
                user_test_instance.__class__.address = user_class_address

    def _get_test_address(self, test):
        try:
            if hasattr(test, "address"):
                with self._without_user_address(test):
                    address = test.address()

                # test.address() is something as:
                # ('D:\\workspaces\\temp\\test_workspace\\pytesting1\\src\\mod1\\hello.py', 'mod1.hello', 'TestCase.testMet1')
                #
                # and we must pass: location, test
                #    E.g.: ['D:\\src\\mod1\\hello.py', 'TestCase.testMet1']
                address = address[0], address[2]
            else:
                # multiprocess
                try:
                    address = test[0], test[1]
                except TypeError:
                    # It may be an error at setup, in which case it's not really a test, but a Context object.
                    f = test.context.__file__
                    if f.endswith(".pyc"):
                        f = f[:-1]
                    elif f.endswith("$py.class"):
                        f = f[: -len("$py.class")] + ".py"
                    address = f, "?"
        except:
            sys.stderr.write("PyDev: Internal pydev error getting test address. Please report at the pydev bug tracker\n")
            traceback.print_exc()
            sys.stderr.write("\n\n\n")
            address = "?", "?"
        return address

    def report_cond(self, cond, test, captured_output, error=""):
        """
        @param cond: fail, error, ok
        """

        address = self._get_test_address(test)

        error_contents = self.get_io_from_error(error)
        try:
            time_str = "%.2f" % (time.time() - test._pydev_start_time)
        except:
            time_str = "?"

        pydev_runfiles_xml_rpc.notifyTest(cond, captured_output, error_contents, address[0], address[1], time_str)

    def startTest(self, test):
        test._pydev_start_time = time.time()
        file, test = self._get_test_address(test)
        pydev_runfiles_xml_rpc.notifyStartTest(file, test)

    def get_io_from_error(self, err):
        if type(err) == type(()):
            if len(err) != 3:
                if len(err) == 2:
                    return err[1]  # multiprocess
            s = StringIO()
            etype, value, tb = err
            if isinstance(value, str):
                return value
            traceback.print_exception(etype, value, tb, file=s)
            return s.getvalue()
        return err

    def get_captured_output(self, test):
        if hasattr(test, "capturedOutput") and test.capturedOutput:
            return test.capturedOutput
        return ""

    def addError(self, test, err):
        self.report_cond(
            "error",
            test,
            self.get_captured_output(test),
            err,
        )

    def addFailure(self, test, err):
        self.report_cond(
            "fail",
            test,
            self.get_captured_output(test),
            err,
        )

    def addSuccess(self, test):
        self.report_cond(
            "ok",
            test,
            self.get_captured_output(test),
            "",
        )


PYDEV_NOSE_PLUGIN_SINGLETON = None


def start_pydev_nose_plugin_singleton(configuration):
    global PYDEV_NOSE_PLUGIN_SINGLETON
    PYDEV_NOSE_PLUGIN_SINGLETON = PydevPlugin(configuration)
    return PYDEV_NOSE_PLUGIN_SINGLETON


original = MultiProcessTestRunner.consolidate


# =======================================================================================================================
# new_consolidate
# =======================================================================================================================
def new_consolidate(self, result, batch_result):
    """
    Used so that it can work with the multiprocess plugin.
    Monkeypatched because nose seems a bit unsupported at this time (ideally
    the plugin would have this support by default).
    """
    ret = original(self, result, batch_result)

    parent_frame = sys._getframe().f_back
    # addr is something as D:\pytesting1\src\mod1\hello.py:TestCase.testMet4
    # so, convert it to what report_cond expects
    addr = parent_frame.f_locals["addr"]
    i = addr.rindex(":")
    addr = [addr[:i], addr[i + 1 :]]

    output, testsRun, failures, errors, errorClasses = batch_result
    if failures or errors:
        for failure in failures:
            PYDEV_NOSE_PLUGIN_SINGLETON.report_cond("fail", addr, output, failure)

        for error in errors:
            PYDEV_NOSE_PLUGIN_SINGLETON.report_cond("error", addr, output, error)
    else:
        PYDEV_NOSE_PLUGIN_SINGLETON.report_cond("ok", addr, output)

    return ret


MultiProcessTestRunner.consolidate = new_consolidate

# === NexusCore/openenv\Lib\site-packages\fontTools\voltLib\__main__.py ===
import argparse
import logging
import sys
from io import StringIO
from pathlib import Path

from fontTools import configLogger
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.feaLib.error import FeatureLibError
from fontTools.feaLib.lexer import Lexer
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib.parser import Parser
from fontTools.voltLib.voltToFea import TABLES, VoltToFea

log = logging.getLogger("fontTools.feaLib")

SUPPORTED_TABLES = TABLES + ["cmap"]


def invalid_fea_glyph_name(name):
    """Check if the glyph name is valid according to FEA syntax."""
    if name[0] not in Lexer.CHAR_NAME_START_:
        return True
    if any(c not in Lexer.CHAR_NAME_CONTINUATION_ for c in name[1:]):
        return True
    return False


def sanitize_glyph_name(name):
    """Sanitize the glyph name to ensure it is valid according to FEA syntax."""
    sanitized = ""
    for i, c in enumerate(name):
        if i == 0 and c not in Lexer.CHAR_NAME_START_:
            sanitized += "a" + c
        elif c not in Lexer.CHAR_NAME_CONTINUATION_:
            sanitized += "_"
        else:
            sanitized += c

    return sanitized


def main(args=None):
    """Build tables from a MS VOLT project into an OTF font"""
    parser = argparse.ArgumentParser(
        description="Use fontTools to compile MS VOLT projects."
    )
    parser.add_argument(
        "input",
        metavar="INPUT",
        help="Path to the input font/VTP file to process",
        type=Path,
    )
    parser.add_argument(
        "-f",
        "--font",
        metavar="INPUT_FONT",
        help="Path to the input font (if INPUT is a VTP file)",
        type=Path,
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        metavar="OUTPUT",
        help="Path to the output font.",
        type=Path,
    )
    parser.add_argument(
        "-t",
        "--tables",
        metavar="TABLE_TAG",
        choices=SUPPORTED_TABLES,
        nargs="+",
        help="Specify the table(s) to be built.",
    )
    parser.add_argument(
        "-F",
        "--debug-feature-file",
        help="Write the generated feature file to disk.",
        action="store_true",
    )
    parser.add_argument(
        "--ship",
        help="Remove source VOLT tables from output font.",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase the logger verbosity. Multiple -v options are allowed.",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-T",
        "--traceback",
        help="show traceback for exceptions.",
        action="store_true",
    )
    options = parser.parse_args(args)

    levels = ["WARNING", "INFO", "DEBUG"]
    configLogger(level=levels[min(len(levels) - 1, options.verbose)])

    output_font = options.output or Path(
        makeOutputFileName(options.font or options.input)
    )
    log.info(f"Compiling MS VOLT to '{output_font}'")

    file_or_path = options.input
    font = None

    # If the input is a font file, extract the VOLT data from the "TSIV" table
    try:
        font = TTFont(file_or_path)
        if "TSIV" in font:
            file_or_path = StringIO(font["TSIV"].data.decode("utf-8"))
        else:
            log.error('"TSIV" table is missing')
            return 1
    except TTLibError:
        pass

    # If input is not a font file, the font must be provided
    if font is None:
        if not options.font:
            log.error("Please provide an input font")
            return 1
        font = TTFont(options.font)

    # FEA syntax does not allow some glyph names that VOLT accepts, so if we
    # found such glyph name we will temporarily rename such glyphs.
    glyphOrder = font.getGlyphOrder()
    tempGlyphOrder = None
    if any(invalid_fea_glyph_name(n) for n in glyphOrder):
        tempGlyphOrder = []
        for n in glyphOrder:
            if invalid_fea_glyph_name(n):
                n = sanitize_glyph_name(n)
                existing = set(tempGlyphOrder) | set(glyphOrder)
                while n in existing:
                    n = "a" + n
            tempGlyphOrder.append(n)
        font.setGlyphOrder(tempGlyphOrder)

    doc = Parser(file_or_path).parse()

    log.info("Converting VTP data to FEA")
    converter = VoltToFea(doc, font)
    try:
        fea = converter.convert(options.tables, ignore_unsupported_settings=True)
    except NotImplementedError as e:
        if options.traceback:
            raise
        location = getattr(e.args[0], "location", None)
        message = f'"{e}" is not supported'
        if location:
            path, line, column = location
            log.error(f"{path}:{line}:{column}: {message}")
        else:
            log.error(message)
        return 1

    fea_filename = options.input
    if options.debug_feature_file:
        fea_filename = output_font.with_suffix(".fea")
        log.info(f"Writing FEA to '{fea_filename}'")
        with open(fea_filename, "w") as fp:
            fp.write(fea)

    log.info("Compiling FEA to OpenType tables")
    try:
        addOpenTypeFeaturesFromString(
            font,
            fea,
            filename=fea_filename,
            tables=options.tables,
        )
    except FeatureLibError as e:
        if options.traceback:
            raise
        log.error(e)
        return 1

    if options.ship:
        for tag in ["TSIV", "TSIS", "TSIP", "TSID"]:
            if tag in font:
                del font[tag]

    # Restore original glyph names.
    if tempGlyphOrder:
        import io

        f = io.BytesIO()
        font.save(f)
        font = TTFont(f)
        font.setGlyphOrder(glyphOrder)
        font["post"].extraNames = []

    font.save(output_font)


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\gitdb\db\pack.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Module containing a database to deal with packs"""
from gitdb.db.base import (
    FileDBBase,
    ObjectDBR,
    CachingDB
)

from gitdb.util import LazyMixin

from gitdb.exc import (
    BadObject,
    UnsupportedOperation,
    AmbiguousObjectName
)

from gitdb.pack import PackEntity

from functools import reduce

import os
import glob

__all__ = ('PackedDB', )

#{ Utilities


class PackedDB(FileDBBase, ObjectDBR, CachingDB, LazyMixin):

    """A database operating on a set of object packs"""

    # sort the priority list every N queries
    # Higher values are better, performance tests don't show this has
    # any effect, but it should have one
    _sort_interval = 500

    def __init__(self, root_path):
        super().__init__(root_path)
        # list of lists with three items:
        # * hits - number of times the pack was hit with a request
        # * entity - Pack entity instance
        # * sha_to_index - PackIndexFile.sha_to_index method for direct cache query
        # self._entities = list()       # lazy loaded list
        self._hit_count = 0             # amount of hits
        self._st_mtime = 0              # last modification data of our root path

    def _set_cache_(self, attr):
        if attr == '_entities':
            self._entities = list()
            self.update_cache(force=True)
        # END handle entities initialization

    def _sort_entities(self):
        self._entities.sort(key=lambda l: l[0], reverse=True)

    def _pack_info(self, sha):
        """:return: tuple(entity, index) for an item at the given sha
        :param sha: 20 or 40 byte sha
        :raise BadObject:
        **Note:** This method is not thread-safe, but may be hit in multi-threaded
            operation. The worst thing that can happen though is a counter that
            was not incremented, or the list being in wrong order. So we safe
            the time for locking here, lets see how that goes"""
        # presort ?
        if self._hit_count % self._sort_interval == 0:
            self._sort_entities()
        # END update sorting

        for item in self._entities:
            index = item[2](sha)
            if index is not None:
                item[0] += 1            # one hit for you
                self._hit_count += 1    # general hit count
                return (item[1], index)
            # END index found in pack
        # END for each item

        # no hit, see whether we have to update packs
        # NOTE: considering packs don't change very often, we safe this call
        # and leave it to the super-caller to trigger that
        raise BadObject(sha)

    #{ Object DB Read

    def has_object(self, sha):
        try:
            self._pack_info(sha)
            return True
        except BadObject:
            return False
        # END exception handling

    def info(self, sha):
        entity, index = self._pack_info(sha)
        return entity.info_at_index(index)

    def stream(self, sha):
        entity, index = self._pack_info(sha)
        return entity.stream_at_index(index)

    def sha_iter(self):
        for entity in self.entities():
            index = entity.index()
            sha_by_index = index.sha
            for index in range(index.size()):
                yield sha_by_index(index)
            # END for each index
        # END for each entity

    def size(self):
        sizes = [item[1].index().size() for item in self._entities]
        return reduce(lambda x, y: x + y, sizes, 0)

    #} END object db read

    #{ object db write

    def store(self, istream):
        """Storing individual objects is not feasible as a pack is designed to
        hold multiple objects. Writing or rewriting packs for single objects is
        inefficient"""
        raise UnsupportedOperation()

    #} END object db write

    #{ Interface

    def update_cache(self, force=False):
        """
        Update our cache with the actually existing packs on disk. Add new ones,
        and remove deleted ones. We keep the unchanged ones

        :param force: If True, the cache will be updated even though the directory
            does not appear to have changed according to its modification timestamp.
        :return: True if the packs have been updated so there is new information,
            False if there was no change to the pack database"""
        stat = os.stat(self.root_path())
        if not force and stat.st_mtime <= self._st_mtime:
            return False
        # END abort early on no change
        self._st_mtime = stat.st_mtime

        # packs are supposed to be prefixed with pack- by git-convention
        # get all pack files, figure out what changed
        pack_files = set(glob.glob(os.path.join(self.root_path(), "pack-*.pack")))
        our_pack_files = {item[1].pack().path() for item in self._entities}

        # new packs
        for pack_file in (pack_files - our_pack_files):
            # init the hit-counter/priority with the size, a good measure for hit-
            # probability. Its implemented so that only 12 bytes will be read
            entity = PackEntity(pack_file)
            self._entities.append([entity.pack().size(), entity, entity.index().sha_to_index])
        # END for each new packfile

        # removed packs
        for pack_file in (our_pack_files - pack_files):
            del_index = -1
            for i, item in enumerate(self._entities):
                if item[1].pack().path() == pack_file:
                    del_index = i
                    break
                # END found index
            # END for each entity
            assert del_index != -1
            del(self._entities[del_index])
        # END for each removed pack

        # reinitialize prioritiess
        self._sort_entities()
        return True

    def entities(self):
        """:return: list of pack entities operated upon by this database"""
        return [item[1] for item in self._entities]

    def partial_to_complete_sha(self, partial_binsha, canonical_length):
        """:return: 20 byte sha as inferred by the given partial binary sha
        :param partial_binsha: binary sha with less than 20 bytes
        :param canonical_length: length of the corresponding canonical representation.
            It is required as binary sha's cannot display whether the original hex sha
            had an odd or even number of characters
        :raise AmbiguousObjectName:
        :raise BadObject: """
        candidate = None
        for item in self._entities:
            item_index = item[1].index().partial_sha_to_index(partial_binsha, canonical_length)
            if item_index is not None:
                sha = item[1].index().sha(item_index)
                if candidate and candidate != sha:
                    raise AmbiguousObjectName(partial_binsha)
                candidate = sha
            # END handle full sha could be found
        # END for each entity

        if candidate:
            return candidate

        # still not found ?
        raise BadObject(partial_binsha)

    #} END interface