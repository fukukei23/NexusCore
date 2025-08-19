
# === NexusCore/openenv\Lib\site-packages\pygments\lexers\j.py ===
"""
    pygments.lexers.j
    ~~~~~~~~~~~~~~~~~

    Lexer for the J programming language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, include, bygroups
from pygments.token import Comment, Keyword, Name, Number, Operator, \
    Punctuation, String, Whitespace

__all__ = ['JLexer']


class JLexer(RegexLexer):
    """
    For J source code.
    """

    name = 'J'
    url = 'http://jsoftware.com/'
    aliases = ['j']
    filenames = ['*.ijs']
    mimetypes = ['text/x-j']
    version_added = '2.1'

    validName = r'\b[a-zA-Z]\w*'

    tokens = {
        'root': [
            # Shebang script
            (r'#!.*$', Comment.Preproc),

            # Comments
            (r'NB\..*', Comment.Single),
            (r'(\n+\s*)(Note)', bygroups(Whitespace, Comment.Multiline),
                'comment'),
            (r'(\s*)(Note.*)', bygroups(Whitespace, Comment.Single)),

            # Whitespace
            (r'\s+', Whitespace),

            # Strings
            (r"'", String, 'singlequote'),

            # Definitions
            (r'0\s+:\s*0', Name.Entity, 'nounDefinition'),
            (r'(noun)(\s+)(define)(\s*)$', bygroups(Name.Entity, Whitespace,
                Name.Entity, Whitespace), 'nounDefinition'),
            (r'([1-4]|13)\s+:\s*0\b',
                Name.Function, 'explicitDefinition'),
            (r'(adverb|conjunction|dyad|monad|verb)(\s+)(define)\b',
                bygroups(Name.Function, Whitespace, Name.Function),
                'explicitDefinition'),

            # Flow Control
            (words(('for_', 'goto_', 'label_'), suffix=validName+r'\.'), Name.Label),
            (words((
                'assert', 'break', 'case', 'catch', 'catchd',
                'catcht', 'continue', 'do', 'else', 'elseif',
                'end', 'fcase', 'for', 'if', 'return',
                'select', 'throw', 'try', 'while', 'whilst',
                ), suffix=r'\.'), Name.Label),

            # Variable Names
            (validName, Name.Variable),

            # Standard Library
            (words((
                'ARGV', 'CR', 'CRLF', 'DEL', 'Debug',
                'EAV', 'EMPTY', 'FF', 'JVERSION', 'LF',
                'LF2', 'Note', 'TAB', 'alpha17', 'alpha27',
                'apply', 'bind', 'boxopen', 'boxxopen', 'bx',
                'clear', 'cutLF', 'cutopen', 'datatype', 'def',
                'dfh', 'drop', 'each', 'echo', 'empty',
                'erase', 'every', 'evtloop', 'exit', 'expand',
                'fetch', 'file2url', 'fixdotdot', 'fliprgb', 'getargs',
                'getenv', 'hfd', 'inv', 'inverse', 'iospath',
                'isatty', 'isutf8', 'items', 'leaf', 'list',
                'nameclass', 'namelist', 'names', 'nc',
                'nl', 'on', 'pick', 'rows',
                'script', 'scriptd', 'sign', 'sminfo', 'smoutput',
                'sort', 'split', 'stderr', 'stdin', 'stdout',
                'table', 'take', 'timespacex', 'timex', 'tmoutput',
                'toCRLF', 'toHOST', 'toJ', 'tolower', 'toupper',
                'type', 'ucp', 'ucpcount', 'usleep', 'utf8',
                'uucp',
                )), Name.Function),

            # Copula
            (r'=[.:]', Operator),

            # Builtins
            (r'[-=+*#$%@!~`^&";:.,<>{}\[\]\\|/?]', Operator),

            # Short Keywords
            (r'[abCdDeEfHiIjLMoprtT]\.',  Keyword.Reserved),
            (r'[aDiLpqsStux]\:', Keyword.Reserved),
            (r'(_[0-9])\:', Keyword.Constant),

            # Parens
            (r'\(', Punctuation, 'parentheses'),

            # Numbers
            include('numbers'),
        ],

        'comment': [
            (r'[^)]', Comment.Multiline),
            (r'^\)', Comment.Multiline, '#pop'),
            (r'[)]', Comment.Multiline),
        ],

        'explicitDefinition': [
            (r'\b[nmuvxy]\b', Name.Decorator),
            include('root'),
            (r'[^)]', Name),
            (r'^\)', Name.Label, '#pop'),
            (r'[)]', Name),
        ],

        'numbers': [
            (r'\b_{1,2}\b', Number),
            (r'_?\d+(\.\d+)?(\s*[ejr]\s*)_?\d+(\.?=\d+)?', Number),
            (r'_?\d+\.(?=\d+)', Number.Float),
            (r'_?\d+x', Number.Integer.Long),
            (r'_?\d+', Number.Integer),
        ],

        'nounDefinition': [
            (r'[^)]+', String),
            (r'^\)', Name.Label, '#pop'),
            (r'[)]', String),
        ],

        'parentheses': [
            (r'\)', Punctuation, '#pop'),
            # include('nounDefinition'),
            include('explicitDefinition'),
            include('root'),
        ],

        'singlequote': [
            (r"[^']+", String),
            (r"''", String),
            (r"'", String, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\mfc\docview.py ===
# document and view classes for MFC.
import win32ui

from . import object, window


class View(window.Wnd):
    def __init__(self, initobj):
        window.Wnd.__init__(self, initobj)

    def OnInitialUpdate(self):
        pass


# Simple control based views.
class CtrlView(View):
    def __init__(self, doc, wndclass, style=0):
        View.__init__(self, win32ui.CreateCtrlView(doc, wndclass, style))


class EditView(CtrlView):
    def __init__(self, doc):
        View.__init__(self, win32ui.CreateEditView(doc))


class RichEditView(CtrlView):
    def __init__(self, doc):
        View.__init__(self, win32ui.CreateRichEditView(doc))


class ListView(CtrlView):
    def __init__(self, doc):
        View.__init__(self, win32ui.CreateListView(doc))


class TreeView(CtrlView):
    def __init__(self, doc):
        View.__init__(self, win32ui.CreateTreeView(doc))


# Other more advanced views.
class ScrollView(View):
    def __init__(self, doc):
        View.__init__(self, win32ui.CreateView(doc))


class FormView(View):
    def __init__(self, doc, id):
        View.__init__(self, win32ui.CreateFormView(doc, id))


class Document(object.CmdTarget):
    def __init__(self, template, docobj=None):
        if docobj is None:
            docobj = template.DoCreateDoc()
        object.CmdTarget.__init__(self, docobj)


class RichEditDoc(object.CmdTarget):
    def __init__(self, template):
        object.CmdTarget.__init__(self, template.DoCreateRichEditDoc())


class CreateContext:
    "A transient base class used as a CreateContext"

    def __init__(self, template, doc=None):
        self.template = template
        self.doc = doc

    def __del__(self):
        self.close()

    def close(self):
        self.doc = None
        self.template = None


class DocTemplate(object.CmdTarget):
    def __init__(
        self, resourceId=None, MakeDocument=None, MakeFrame=None, MakeView=None
    ):
        if resourceId is None:
            resourceId = win32ui.IDR_PYTHONTYPE
        object.CmdTarget.__init__(self, self._CreateDocTemplate(resourceId))
        self.MakeDocument = MakeDocument
        self.MakeFrame = MakeFrame
        self.MakeView = MakeView
        self._SetupSharedMenu_()

    def _SetupSharedMenu_(self):
        pass  # to be overridden by each "app"

    def _CreateDocTemplate(self, resourceId):
        return win32ui.CreateDocTemplate(resourceId)

    def __del__(self):
        object.CmdTarget.__del__(self)

    def CreateCreateContext(self, doc=None):
        return CreateContext(self, doc)

    def CreateNewFrame(self, doc):
        makeFrame = self.MakeFrame
        if makeFrame is None:
            makeFrame = window.MDIChildWnd
        wnd = makeFrame()
        context = self.CreateCreateContext(doc)
        wnd.LoadFrame(
            self.GetResourceID(), -1, None, context
        )  # triggers OnCreateClient...
        return wnd

    def CreateNewDocument(self):
        makeDocument = self.MakeDocument
        if makeDocument is None:
            makeDocument = Document
        return makeDocument(self)

    def CreateView(self, frame, context):
        makeView = self.MakeView
        if makeView is None:
            makeView = EditView
        view = makeView(context.doc)
        view.CreateWindow(frame)


class RichEditDocTemplate(DocTemplate):
    def __init__(
        self, resourceId=None, MakeDocument=None, MakeFrame=None, MakeView=None
    ):
        if MakeView is None:
            MakeView = RichEditView
        if MakeDocument is None:
            MakeDocument = RichEditDoc
        DocTemplate.__init__(self, resourceId, MakeDocument, MakeFrame, MakeView)

    def _CreateDocTemplate(self, resourceId):
        return win32ui.CreateRichEditDocTemplate(resourceId)


def t():
    class FormTemplate(DocTemplate):
        def CreateView(self, frame, context):
            makeView = self.MakeView
            # 			view = FormView(context.doc, win32ui.IDD_PROPDEMO1)
            view = ListView(context.doc)
            view.CreateWindow(frame)

    t = FormTemplate()
    return t.OpenDocumentFile(None)

# === NexusCore/openenv\Lib\site-packages\tokenizers\implementations\bert_wordpiece.py ===
from typing import Dict, Iterator, List, Optional, Union

from tokenizers import AddedToken, Tokenizer, decoders, trainers
from tokenizers.models import WordPiece
from tokenizers.normalizers import BertNormalizer
from tokenizers.pre_tokenizers import BertPreTokenizer
from tokenizers.processors import BertProcessing

from .base_tokenizer import BaseTokenizer


class BertWordPieceTokenizer(BaseTokenizer):
    """Bert WordPiece Tokenizer"""

    def __init__(
        self,
        vocab: Optional[Union[str, Dict[str, int]]] = None,
        unk_token: Union[str, AddedToken] = "[UNK]",
        sep_token: Union[str, AddedToken] = "[SEP]",
        cls_token: Union[str, AddedToken] = "[CLS]",
        pad_token: Union[str, AddedToken] = "[PAD]",
        mask_token: Union[str, AddedToken] = "[MASK]",
        clean_text: bool = True,
        handle_chinese_chars: bool = True,
        strip_accents: Optional[bool] = None,
        lowercase: bool = True,
        wordpieces_prefix: str = "##",
    ):
        if vocab is not None:
            tokenizer = Tokenizer(WordPiece(vocab, unk_token=str(unk_token)))
        else:
            tokenizer = Tokenizer(WordPiece(unk_token=str(unk_token)))

        # Let the tokenizer know about special tokens if they are part of the vocab
        if tokenizer.token_to_id(str(unk_token)) is not None:
            tokenizer.add_special_tokens([str(unk_token)])
        if tokenizer.token_to_id(str(sep_token)) is not None:
            tokenizer.add_special_tokens([str(sep_token)])
        if tokenizer.token_to_id(str(cls_token)) is not None:
            tokenizer.add_special_tokens([str(cls_token)])
        if tokenizer.token_to_id(str(pad_token)) is not None:
            tokenizer.add_special_tokens([str(pad_token)])
        if tokenizer.token_to_id(str(mask_token)) is not None:
            tokenizer.add_special_tokens([str(mask_token)])

        tokenizer.normalizer = BertNormalizer(
            clean_text=clean_text,
            handle_chinese_chars=handle_chinese_chars,
            strip_accents=strip_accents,
            lowercase=lowercase,
        )
        tokenizer.pre_tokenizer = BertPreTokenizer()

        if vocab is not None:
            sep_token_id = tokenizer.token_to_id(str(sep_token))
            if sep_token_id is None:
                raise TypeError("sep_token not found in the vocabulary")
            cls_token_id = tokenizer.token_to_id(str(cls_token))
            if cls_token_id is None:
                raise TypeError("cls_token not found in the vocabulary")

            tokenizer.post_processor = BertProcessing((str(sep_token), sep_token_id), (str(cls_token), cls_token_id))
        tokenizer.decoder = decoders.WordPiece(prefix=wordpieces_prefix)

        parameters = {
            "model": "BertWordPiece",
            "unk_token": unk_token,
            "sep_token": sep_token,
            "cls_token": cls_token,
            "pad_token": pad_token,
            "mask_token": mask_token,
            "clean_text": clean_text,
            "handle_chinese_chars": handle_chinese_chars,
            "strip_accents": strip_accents,
            "lowercase": lowercase,
            "wordpieces_prefix": wordpieces_prefix,
        }

        super().__init__(tokenizer, parameters)

    @staticmethod
    def from_file(vocab: str, **kwargs):
        vocab = WordPiece.read_file(vocab)
        return BertWordPieceTokenizer(vocab, **kwargs)

    def train(
        self,
        files: Union[str, List[str]],
        vocab_size: int = 30000,
        min_frequency: int = 2,
        limit_alphabet: int = 1000,
        initial_alphabet: List[str] = [],
        special_tokens: List[Union[str, AddedToken]] = [
            "[PAD]",
            "[UNK]",
            "[CLS]",
            "[SEP]",
            "[MASK]",
        ],
        show_progress: bool = True,
        wordpieces_prefix: str = "##",
    ):
        """Train the model using the given files"""

        trainer = trainers.WordPieceTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            limit_alphabet=limit_alphabet,
            initial_alphabet=initial_alphabet,
            special_tokens=special_tokens,
            show_progress=show_progress,
            continuing_subword_prefix=wordpieces_prefix,
        )
        if isinstance(files, str):
            files = [files]
        self._tokenizer.train(files, trainer=trainer)

    def train_from_iterator(
        self,
        iterator: Union[Iterator[str], Iterator[Iterator[str]]],
        vocab_size: int = 30000,
        min_frequency: int = 2,
        limit_alphabet: int = 1000,
        initial_alphabet: List[str] = [],
        special_tokens: List[Union[str, AddedToken]] = [
            "[PAD]",
            "[UNK]",
            "[CLS]",
            "[SEP]",
            "[MASK]",
        ],
        show_progress: bool = True,
        wordpieces_prefix: str = "##",
        length: Optional[int] = None,
    ):
        """Train the model using the given iterator"""

        trainer = trainers.WordPieceTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            limit_alphabet=limit_alphabet,
            initial_alphabet=initial_alphabet,
            special_tokens=special_tokens,
            show_progress=show_progress,
            continuing_subword_prefix=wordpieces_prefix,
        )
        self._tokenizer.train_from_iterator(
            iterator,
            trainer=trainer,
            length=length,
        )

# === NexusCore/openenv\Lib\site-packages\win32comext\adsi\demos\search.py ===
import pythoncom
import pywintypes
from win32com.adsi import adsi, adsicon
from win32com.adsi.adsicon import *

options = None  # set to optparse options object

ADsTypeNameMap = {}


def getADsTypeName(type_val):
    # convert integer type to the 'typename' as known in the headerfiles.
    if not ADsTypeNameMap:
        for n, v in adsicon.__dict__.items():
            if n.startswith("ADSTYPE_"):
                ADsTypeNameMap[v] = n
    return ADsTypeNameMap.get(type_val, hex(type_val))


def _guid_from_buffer(b):
    return pywintypes.IID(b, True)


def _sid_from_buffer(b):
    return str(pywintypes.SID(b))


_null_converter = lambda x: x

converters = {
    "objectGUID": _guid_from_buffer,
    "objectSid": _sid_from_buffer,
    "instanceType": getADsTypeName,
}


def log(level, msg, *args):
    if options.verbose >= level:
        print("log:", msg % args)


def getGC():
    cont = adsi.ADsOpenObject(
        "GC:", options.user, options.password, 0, adsi.IID_IADsContainer
    )
    enum = adsi.ADsBuildEnumerator(cont)
    # Only 1 child of the global catalog.
    for e in enum:
        gc = e.QueryInterface(adsi.IID_IDirectorySearch)
        return gc
    return None


def print_attribute(col_data):
    prop_name, prop_type, values = col_data
    if values is not None:
        log(2, "property '%s' has type '%s'", prop_name, getADsTypeName(prop_type))
        value = [converters.get(prop_name, _null_converter)(v[0]) for v in values]
        if len(value) == 1:
            value = value[0]
        print(f" {prop_name}={value!r}")
    else:
        print(f" {prop_name} is None")


def search():
    gc = getGC()
    if gc is None:
        log(0, "Can't find the global catalog")
        return

    prefs = [(ADS_SEARCHPREF_SEARCH_SCOPE, (ADS_SCOPE_SUBTREE,))]
    hr, statuses = gc.SetSearchPreference(prefs)
    log(3, "SetSearchPreference returned %d/%r", hr, statuses)

    if options.attributes:
        attributes = options.attributes.split(",")
    else:
        attributes = None

    h = gc.ExecuteSearch(options.filter, attributes)
    hr = gc.GetNextRow(h)
    while hr != S_ADS_NOMORE_ROWS:
        print("-- new row --")
        if attributes is None:
            # Loop over all columns returned
            while 1:
                col_name = gc.GetNextColumnName(h)
                if col_name is None:
                    break
                data = gc.GetColumn(h, col_name)
                print_attribute(data)
        else:
            # loop over attributes specified.
            for a in attributes:
                try:
                    data = gc.GetColumn(h, a)
                    print_attribute(data)
                except adsi.error as details:
                    if details[0] != E_ADS_COLUMN_NOT_SET:
                        raise
                    print_attribute((a, None, None))
        hr = gc.GetNextRow(h)
    gc.CloseSearchHandle(h)


def main():
    global options
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option(
        "-f", "--file", dest="filename", help="write report to FILE", metavar="FILE"
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="increase verbosity of output",
    )
    parser.add_option(
        "-q", "--quiet", action="store_true", help="suppress output messages"
    )

    parser.add_option("-U", "--user", help="specify the username used to connect")
    parser.add_option("-P", "--password", help="specify the password used to connect")
    parser.add_option(
        "",
        "--filter",
        default="(&(objectCategory=person)(objectClass=User))",
        help="specify the search filter",
    )
    parser.add_option(
        "", "--attributes", help="comma sep'd list of attribute names to print"
    )

    options, args = parser.parse_args()
    if options.quiet:
        if options.verbose != 1:
            parser.error("Can not use '--verbose' and '--quiet'")
        options.verbose = 0

    if args:
        parser.error("You need not specify args")

    search()


if __name__ == "__main__":
    main()

# === NexusCore/project_structure_and_code_export.py ===
import os
import json
import zipfile
import fnmatch
from pathlib import Path
from datetime import datetime

# ===== チューニング設定 =====
MAX_FILE_SIZE_MB = 1
MAX_DEPTH = 5
FILE_TYPES = ('.py', '.md', '.txt', 'package.json')
GITIGNORE_PATH = ".gitignore"

# ===== 除外対象（固定値） =====
DEFAULT_IGNORED_DIRS = {
    '.git', '.venv', '__pycache__', 'node_modules',
    'output', 'dist', 'build', 'sandbox_output', 'deploy_output'
}
DEFAULT_IGNORED_FILES = {
    '.env', 'secrets.json', 'config.local.json', '.DS_Store', '*.log'
}

# ===== ユーティリティ関数 =====
def get_depth(path, base):
    return len(os.path.relpath(path, base).split(os.sep))

def load_gitignore(path=GITIGNORE_PATH):
    ignored_dirs, ignored_files = set(), set()
    if not os.path.exists(path):
        return ignored_dirs, ignored_files
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith('/'):
                ignored_dirs.add(line.rstrip('/'))
            else:
                ignored_files.add(line)
    return ignored_dirs, ignored_files

def create_folder_structure_json(path, base_path, ignored_dirs, ignored_files):
    if get_depth(path, base_path) > MAX_DEPTH:
        return None
    result = {
        'name': os.path.basename(path),
        'type': 'folder',
        'children': []
    }
    for entry in sorted(os.listdir(path)):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            if entry in ignored_dirs:
                continue
            child = create_folder_structure_json(full_path, base_path, ignored_dirs, ignored_files)
            if child:
                result['children'].append(child)
        else:
            if entry in ignored_files or any(fnmatch.fnmatch(entry, pattern) for pattern in ignored_files):
                continue
            result['children'].append({'name': entry, 'type': 'file'})
    return result

def create_folder_structure_md(path, prefix, base_path, ignored_dirs, ignored_files):
    lines = []
    if get_depth(path, base_path) > MAX_DEPTH:
        return lines
    for i, entry in enumerate(sorted(os.listdir(path))):
        full_path = os.path.join(path, entry)
        if entry in ignored_dirs or entry in ignored_files or any(fnmatch.fnmatch(entry, pattern) for pattern in ignored_files):
            continue
        connector = "└── " if i == len(os.listdir(path)) - 1 else "├── "
        lines.append(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "    " if i == len(os.listdir(path)) - 1 else "│   "
            lines.extend(create_folder_structure_md(full_path, prefix + extension, base_path, ignored_dirs, ignored_files))
    return lines

def combine_files(root_path, output_file, file_types, ignored_dirs, ignored_files):
    buffer = []
    for dirpath, _, filenames in os.walk(root_path):
        if any(part in ignored_dirs for part in dirpath.split(os.sep)):
            continue
        if get_depth(dirpath, root_path) > MAX_DEPTH:
            continue
        for filename in sorted(filenames):
            if filename in ignored_files or any(fnmatch.fnmatch(filename, pattern) for pattern in ignored_files):
                continue
            if not (filename.endswith(file_types) or filename in file_types):
                continue
            file_path = os.path.join(dirpath, filename)
            if os.path.getsize(file_path) > MAX_FILE_SIZE_MB * 1024 * 1024:
                continue
            rel_path = os.path.relpath(file_path, root_path)
            buffer.append(f"\n\n# === File: {rel_path} ===\n\n")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    buffer.append(f.read())
            except Exception as e:
                buffer.append(f"[読み込みエラー: {e}]")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(buffer))

def zip_outputs(output_dir, archive_name):
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, output_dir)
                zipf.write(full_path, arcname)

# ===== メイン処理 =====
if __name__ == "__main__":
    PROJECT_PATH = "./"
    OUTPUT_DIR = "output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = os.path.basename(os.getcwd())

    STRUCTURE_JSON = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.json")
    STRUCTURE_MD = os.path.join(OUTPUT_DIR, f"{project_name}_structure_{timestamp}.md")
    COMBINED_CODE = os.path.join(OUTPUT_DIR, f"{project_name}_combined_{timestamp}.txt")
    ARCHIVE_ZIP = os.path.join(OUTPUT_DIR, f"{project_name}_bundle_{timestamp}.zip")

    print("🚀 .gitignoreを読み込み中...")
    gitignore_dirs, gitignore_files = load_gitignore()
    IGNORED_DIRS = DEFAULT_IGNORED_DIRS.union(gitignore_dirs)
    IGNORED_FILES = DEFAULT_IGNORED_FILES.union(gitignore_files)

    print("📁 ディレクトリ構造の解析を開始します...")
    structure = create_folder_structure_json(PROJECT_PATH, PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(STRUCTURE_JSON, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=4, ensure_ascii=False)
    print(f"✅ JSON出力: {STRUCTURE_JSON}")

    md_lines = create_folder_structure_md(PROJECT_PATH, "", PROJECT_PATH, IGNORED_DIRS, IGNORED_FILES)
    with open(STRUCTURE_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    print(f"✅ Markdown出力: {STRUCTURE_MD}")

    print("📦 ソース統合中...")
    combine_files(PROJECT_PATH, COMBINED_CODE, FILE_TYPES, IGNORED_DIRS, IGNORED_FILES)
    print(f"✅ 統合コード出力: {COMBINED_CODE}")

    print("🗜️ アーカイブ作成中...")
    zip_outputs(OUTPUT_DIR, ARCHIVE_ZIP)
    print(f"✅ zip出力完了: {ARCHIVE_ZIP}")

    print("\n🎉 すべての処理が完了しました。")

# === NexusCore/run_self_healing.py ===
# ==============================================================================
# フォルダ: (プロジェクトルート)
# ファイル名: run_self_healing.py
# メモ: 構造化ログの保存先ディレクトリをOrchestratorに渡すように
#      アップグレードされた最終テストスクリプト。
# ==============================================================================
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

VERBOSE = True # 詳細ログの表示/非表示を切り替え

def setup_logging(level=logging.INFO):
    log_format = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=level, format=log_format)

def main():
    log_level = logging.DEBUG if VERBOSE else logging.INFO
    setup_logging(log_level)
    
    logging.info("--- NexusCore Self-Healing System (Test with Structured Logging) ---")

    try:
        project_root = Path(__file__).resolve().parent
        sandbox_path = project_root / "healing_sandbox"
        
        # (ファイルパスの定義は変更なし)
        # ...
        agent_sources = {
            "orchestrator.py": project_root / "src" / "agents" / "orchestrator.py",
            "debugger_agent.py": project_root / "src" / "agents" / "debugger_agent.py",
            "patch_applier.py": project_root / "src" / "agents" / "patch_applier.py",
            "base_agent.py": project_root / "src" / "agents" / "base_agent.py",
            "fkb_local.json": project_root / "fkb_local.json"
        }
        crm_app_sources = {
            "main.py": project_root / "my-crm-app" / "app" / "main.py",
            "test_main.py": project_root / "my-crm-app" / "tests" / "test_main.py"
        }


        logging.info("Verifying required files...")
        all_sources = {**agent_sources, **crm_app_sources}
        for name, path in all_sources.items():
            if not path.exists():
                raise FileNotFoundError(f"Required file not found: '{path}'")
            logging.debug(f"Found: {path.relative_to(project_root)}")

        logging.info(f"Setting up sandbox environment at: {sandbox_path}")
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
        
        # (ディレクトリ作成は変更なし)
        # ...
        (sandbox_path / "app").mkdir(parents=True, exist_ok=True)
        (sandbox_path / "tests").mkdir(exist_ok=True)
        (sandbox_path / "src" / "agents").mkdir(parents=True, exist_ok=True)
        # ★★★★★ ログ保存用ディレクトリを追加 ★★★★★
        (sandbox_path / "logs").mkdir(exist_ok=True)


        # (ファイルコピーは変更なし)
        # ...
        for name, src_path in agent_sources.items():
            dest_folder = (sandbox_path / "src" / "agents") if name.endswith(".py") else sandbox_path
            shutil.copy(src_path, dest_folder / name)
        
        shutil.copy(crm_app_sources["main.py"], sandbox_path / "app" / "main.py")
        shutil.copy(crm_app_sources["test_main.py"], sandbox_path / "tests" / "test_main.py")
        logging.debug("Copied all required files to sandbox.")

        (sandbox_path / "app" / "__init__.py").touch()
        (sandbox_path / "tests" / "__init__.py").touch()
        (sandbox_path / "src" / "__init__.py").touch()
        (sandbox_path / "src" / "agents" / "__init__.py").touch()


        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        runner_script_code = f"""
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

log_level_str = "{logging.getLevelName(log_level)}"
log_level = logging.getLevelName(log_level_str)
log_format = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
logging.basicConfig(level=log_level, format=log_format)

from src.agents.orchestrator import Orchestrator
from src.agents.debugger_agent import DebuggerAgent
from src.agents.patch_applier import PatchApplier

def run():
    logging.info(">> Starting Self-Healing Cycle for CRM App...")
    
    debugger = DebuggerAgent(api_key="dummy_key", model="dummy_model", knowledge_base_path="fkb_local.json")
    patcher = PatchApplier()
    
    # Orchestratorにログ保存先のパスを渡す
    orchestrator = Orchestrator(
        debugger_agent=debugger,
        patch_applier=patcher,
        log_dir="logs", # サンドボックス内のlogsディレクトリを指定
        max_retries=3
    )
    
    orchestrator.self_healing_cycle(
        test_file_path="tests/test_main.py",
        source_file_path="app/main.py"
    )

if __name__ == '__main__':
    run()
"""
        # --- ★★★★★ ここまで ★★★★★ ---
        runner_script_path = sandbox_path / "sandbox_runner.py"
        runner_script_path.write_text(runner_script_code, encoding='utf-8')
        logging.debug("Created sandbox runner script.")

        logging.info("Executing the self-healing cycle for CRM App...")
        result = subprocess.run(
            [sys.executable, "sandbox_runner.py"],
            cwd=sandbox_path,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        
        print("\\n--- Execution Log ---")
        print(result.stdout)
        if result.stderr:
            print("\\n--- Errors ---")
            print(result.stderr)
        print("---------------------")

        logging.info("Self-healing cycle finished.")
        print(f"\\n[INFO] Structured logs have been saved in '{sandbox_path / 'logs'}'")

    except FileNotFoundError as e:
        logging.critical(f"A required file was not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

# === NexusCore/openenv\Lib\site-packages\anthropic\_qs.py ===
from __future__ import annotations

from typing import Any, List, Tuple, Union, Mapping, TypeVar
from urllib.parse import parse_qs, urlencode
from typing_extensions import Literal, get_args

from ._types import NOT_GIVEN, NotGiven, NotGivenOr
from ._utils import flatten

_T = TypeVar("_T")


ArrayFormat = Literal["comma", "repeat", "indices", "brackets"]
NestedFormat = Literal["dots", "brackets"]

PrimitiveData = Union[str, int, float, bool, None]
# this should be Data = Union[PrimitiveData, "List[Data]", "Tuple[Data]", "Mapping[str, Data]"]
# https://github.com/microsoft/pyright/issues/3555
Data = Union[PrimitiveData, List[Any], Tuple[Any], "Mapping[str, Any]"]
Params = Mapping[str, Data]


class Querystring:
    array_format: ArrayFormat
    nested_format: NestedFormat

    def __init__(
        self,
        *,
        array_format: ArrayFormat = "repeat",
        nested_format: NestedFormat = "brackets",
    ) -> None:
        self.array_format = array_format
        self.nested_format = nested_format

    def parse(self, query: str) -> Mapping[str, object]:
        # Note: custom format syntax is not supported yet
        return parse_qs(query)

    def stringify(
        self,
        params: Params,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> str:
        return urlencode(
            self.stringify_items(
                params,
                array_format=array_format,
                nested_format=nested_format,
            )
        )

    def stringify_items(
        self,
        params: Params,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> list[tuple[str, str]]:
        opts = Options(
            qs=self,
            array_format=array_format,
            nested_format=nested_format,
        )
        return flatten([self._stringify_item(key, value, opts) for key, value in params.items()])

    def _stringify_item(
        self,
        key: str,
        value: Data,
        opts: Options,
    ) -> list[tuple[str, str]]:
        if isinstance(value, Mapping):
            items: list[tuple[str, str]] = []
            nested_format = opts.nested_format
            for subkey, subvalue in value.items():
                items.extend(
                    self._stringify_item(
                        # TODO: error if unknown format
                        f"{key}.{subkey}" if nested_format == "dots" else f"{key}[{subkey}]",
                        subvalue,
                        opts,
                    )
                )
            return items

        if isinstance(value, (list, tuple)):
            array_format = opts.array_format
            if array_format == "comma":
                return [
                    (
                        key,
                        ",".join(self._primitive_value_to_str(item) for item in value if item is not None),
                    ),
                ]
            elif array_format == "repeat":
                items = []
                for item in value:
                    items.extend(self._stringify_item(key, item, opts))
                return items
            elif array_format == "indices":
                raise NotImplementedError("The array indices format is not supported yet")
            elif array_format == "brackets":
                items = []
                key = key + "[]"
                for item in value:
                    items.extend(self._stringify_item(key, item, opts))
                return items
            else:
                raise NotImplementedError(
                    f"Unknown array_format value: {array_format}, choose from {', '.join(get_args(ArrayFormat))}"
                )

        serialised = self._primitive_value_to_str(value)
        if not serialised:
            return []
        return [(key, serialised)]

    def _primitive_value_to_str(self, value: PrimitiveData) -> str:
        # copied from httpx
        if value is True:
            return "true"
        elif value is False:
            return "false"
        elif value is None:
            return ""
        return str(value)


_qs = Querystring()
parse = _qs.parse
stringify = _qs.stringify
stringify_items = _qs.stringify_items


class Options:
    array_format: ArrayFormat
    nested_format: NestedFormat

    def __init__(
        self,
        qs: Querystring = _qs,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> None:
        self.array_format = qs.array_format if isinstance(array_format, NotGiven) else array_format
        self.nested_format = qs.nested_format if isinstance(nested_format, NotGiven) else nested_format

# === NexusCore/openenv\Lib\site-packages\openai\_qs.py ===
from __future__ import annotations

from typing import Any, List, Tuple, Union, Mapping, TypeVar
from urllib.parse import parse_qs, urlencode
from typing_extensions import Literal, get_args

from ._types import NOT_GIVEN, NotGiven, NotGivenOr
from ._utils import flatten

_T = TypeVar("_T")


ArrayFormat = Literal["comma", "repeat", "indices", "brackets"]
NestedFormat = Literal["dots", "brackets"]

PrimitiveData = Union[str, int, float, bool, None]
# this should be Data = Union[PrimitiveData, "List[Data]", "Tuple[Data]", "Mapping[str, Data]"]
# https://github.com/microsoft/pyright/issues/3555
Data = Union[PrimitiveData, List[Any], Tuple[Any], "Mapping[str, Any]"]
Params = Mapping[str, Data]


class Querystring:
    array_format: ArrayFormat
    nested_format: NestedFormat

    def __init__(
        self,
        *,
        array_format: ArrayFormat = "repeat",
        nested_format: NestedFormat = "brackets",
    ) -> None:
        self.array_format = array_format
        self.nested_format = nested_format

    def parse(self, query: str) -> Mapping[str, object]:
        # Note: custom format syntax is not supported yet
        return parse_qs(query)

    def stringify(
        self,
        params: Params,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> str:
        return urlencode(
            self.stringify_items(
                params,
                array_format=array_format,
                nested_format=nested_format,
            )
        )

    def stringify_items(
        self,
        params: Params,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> list[tuple[str, str]]:
        opts = Options(
            qs=self,
            array_format=array_format,
            nested_format=nested_format,
        )
        return flatten([self._stringify_item(key, value, opts) for key, value in params.items()])

    def _stringify_item(
        self,
        key: str,
        value: Data,
        opts: Options,
    ) -> list[tuple[str, str]]:
        if isinstance(value, Mapping):
            items: list[tuple[str, str]] = []
            nested_format = opts.nested_format
            for subkey, subvalue in value.items():
                items.extend(
                    self._stringify_item(
                        # TODO: error if unknown format
                        f"{key}.{subkey}" if nested_format == "dots" else f"{key}[{subkey}]",
                        subvalue,
                        opts,
                    )
                )
            return items

        if isinstance(value, (list, tuple)):
            array_format = opts.array_format
            if array_format == "comma":
                return [
                    (
                        key,
                        ",".join(self._primitive_value_to_str(item) for item in value if item is not None),
                    ),
                ]
            elif array_format == "repeat":
                items = []
                for item in value:
                    items.extend(self._stringify_item(key, item, opts))
                return items
            elif array_format == "indices":
                raise NotImplementedError("The array indices format is not supported yet")
            elif array_format == "brackets":
                items = []
                key = key + "[]"
                for item in value:
                    items.extend(self._stringify_item(key, item, opts))
                return items
            else:
                raise NotImplementedError(
                    f"Unknown array_format value: {array_format}, choose from {', '.join(get_args(ArrayFormat))}"
                )

        serialised = self._primitive_value_to_str(value)
        if not serialised:
            return []
        return [(key, serialised)]

    def _primitive_value_to_str(self, value: PrimitiveData) -> str:
        # copied from httpx
        if value is True:
            return "true"
        elif value is False:
            return "false"
        elif value is None:
            return ""
        return str(value)


_qs = Querystring()
parse = _qs.parse
stringify = _qs.stringify
stringify_items = _qs.stringify_items


class Options:
    array_format: ArrayFormat
    nested_format: NestedFormat

    def __init__(
        self,
        qs: Querystring = _qs,
        *,
        array_format: NotGivenOr[ArrayFormat] = NOT_GIVEN,
        nested_format: NotGivenOr[NestedFormat] = NOT_GIVEN,
    ) -> None:
        self.array_format = qs.array_format if isinstance(array_format, NotGiven) else array_format
        self.nested_format = qs.nested_format if isinstance(nested_format, NotGiven) else nested_format

# === NexusCore/openenv\Lib\site-packages\starlette\schemas.py ===
from __future__ import annotations

import inspect
import re
import typing

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Host, Mount, Route

try:
    import yaml
except ModuleNotFoundError:  # pragma: nocover
    yaml = None  # type: ignore[assignment]


class OpenAPIResponse(Response):
    media_type = "application/vnd.oai.openapi"

    def render(self, content: typing.Any) -> bytes:
        assert yaml is not None, "`pyyaml` must be installed to use OpenAPIResponse."
        assert isinstance(
            content, dict
        ), "The schema passed to OpenAPIResponse should be a dictionary."
        return yaml.dump(content, default_flow_style=False).encode("utf-8")


class EndpointInfo(typing.NamedTuple):
    path: str
    http_method: str
    func: typing.Callable[..., typing.Any]


class BaseSchemaGenerator:
    def get_schema(self, routes: list[BaseRoute]) -> dict[str, typing.Any]:
        raise NotImplementedError()  # pragma: no cover

    def get_endpoints(self, routes: list[BaseRoute]) -> list[EndpointInfo]:
        """
        Given the routes, yields the following information:

        - path
            eg: /users/
        - http_method
            one of 'get', 'post', 'put', 'patch', 'delete', 'options'
        - func
            method ready to extract the docstring
        """
        endpoints_info: list[EndpointInfo] = []

        for route in routes:
            if isinstance(route, (Mount, Host)):
                routes = route.routes or []
                if isinstance(route, Mount):
                    path = self._remove_converter(route.path)
                else:
                    path = ""
                sub_endpoints = [
                    EndpointInfo(
                        path="".join((path, sub_endpoint.path)),
                        http_method=sub_endpoint.http_method,
                        func=sub_endpoint.func,
                    )
                    for sub_endpoint in self.get_endpoints(routes)
                ]
                endpoints_info.extend(sub_endpoints)

            elif not isinstance(route, Route) or not route.include_in_schema:
                continue

            elif inspect.isfunction(route.endpoint) or inspect.ismethod(route.endpoint):
                path = self._remove_converter(route.path)
                for method in route.methods or ["GET"]:
                    if method == "HEAD":
                        continue
                    endpoints_info.append(
                        EndpointInfo(path, method.lower(), route.endpoint)
                    )
            else:
                path = self._remove_converter(route.path)
                for method in ["get", "post", "put", "patch", "delete", "options"]:
                    if not hasattr(route.endpoint, method):
                        continue
                    func = getattr(route.endpoint, method)
                    endpoints_info.append(EndpointInfo(path, method.lower(), func))

        return endpoints_info

    def _remove_converter(self, path: str) -> str:
        """
        Remove the converter from the path.
        For example, a route like this:
            Route("/users/{id:int}", endpoint=get_user, methods=["GET"])
        Should be represented as `/users/{id}` in the OpenAPI schema.
        """
        return re.sub(r":\w+}", "}", path)

    def parse_docstring(
        self, func_or_method: typing.Callable[..., typing.Any]
    ) -> dict[str, typing.Any]:
        """
        Given a function, parse the docstring as YAML and return a dictionary of info.
        """
        docstring = func_or_method.__doc__
        if not docstring:
            return {}

        assert yaml is not None, "`pyyaml` must be installed to use parse_docstring."

        # We support having regular docstrings before the schema
        # definition. Here we return just the schema part from
        # the docstring.
        docstring = docstring.split("---")[-1]

        parsed = yaml.safe_load(docstring)

        if not isinstance(parsed, dict):
            # A regular docstring (not yaml formatted) can return
            # a simple string here, which wouldn't follow the schema.
            return {}

        return parsed

    def OpenAPIResponse(self, request: Request) -> Response:
        routes = request.app.routes
        schema = self.get_schema(routes=routes)
        return OpenAPIResponse(schema)


class SchemaGenerator(BaseSchemaGenerator):
    def __init__(self, base_schema: dict[str, typing.Any]) -> None:
        self.base_schema = base_schema

    def get_schema(self, routes: list[BaseRoute]) -> dict[str, typing.Any]:
        schema = dict(self.base_schema)
        schema.setdefault("paths", {})
        endpoints_info = self.get_endpoints(routes)

        for endpoint in endpoints_info:
            parsed = self.parse_docstring(endpoint.func)

            if not parsed:
                continue

            if endpoint.path not in schema["paths"]:
                schema["paths"][endpoint.path] = {}

            schema["paths"][endpoint.path][endpoint.http_method] = parsed

        return schema

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\inputhookglut.py ===
# coding: utf-8
"""
GLUT Inputhook support functions
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# GLUT is quite an old library and it is difficult to ensure proper
# integration within IPython since original GLUT does not allow to handle
# events one by one. Instead, it requires for the mainloop to be entered
# and never returned (there is not even a function to exit he
# mainloop). Fortunately, there are alternatives such as freeglut
# (available for linux and windows) and the OSX implementation gives
# access to a glutCheckLoop() function that blocks itself until a new
# event is received. This means we have to setup the idle callback to
# ensure we got at least one event that will unblock the function.
#
# Furthermore, it is not possible to install these handlers without a window
# being first created. We choose to make this window invisible. This means that
# display mode options are set at this level and user won't be able to change
# them later without modifying the code. This should probably be made available
# via IPython options system.

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import os
import sys
from _pydev_bundle._pydev_saved_modules import time
import signal
import OpenGL.GLUT as glut  # @UnresolvedImport
import OpenGL.platform as platform  # @UnresolvedImport
from timeit import default_timer as clock
from pydev_ipython.inputhook import stdin_ready

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Frame per second : 60
# Should probably be an IPython option
glut_fps = 60

# Display mode : double buffeed + rgba + depth
# Should probably be an IPython option
glut_display_mode = glut.GLUT_DOUBLE | glut.GLUT_RGBA | glut.GLUT_DEPTH

glutMainLoopEvent = None
if sys.platform == "darwin":
    try:
        glutCheckLoop = platform.createBaseFunction(
            "glutCheckLoop",
            dll=platform.GLUT,
            resultType=None,
            argTypes=[],
            doc="glutCheckLoop(  ) -> None",
            argNames=(),
        )
    except AttributeError:
        raise RuntimeError("""Your glut implementation does not allow interactive sessions""" """Consider installing freeglut.""")
    glutMainLoopEvent = glutCheckLoop
elif glut.HAVE_FREEGLUT:
    glutMainLoopEvent = glut.glutMainLoopEvent
else:
    raise RuntimeError("""Your glut implementation does not allow interactive sessions. """ """Consider installing freeglut.""")

# -----------------------------------------------------------------------------
# Callback functions
# -----------------------------------------------------------------------------


def glut_display():
    # Dummy display function
    pass


def glut_idle():
    # Dummy idle function
    pass


def glut_close():
    # Close function only hides the current window
    glut.glutHideWindow()
    glutMainLoopEvent()


def glut_int_handler(signum, frame):
    # Catch sigint and print the defautl message
    signal.signal(signal.SIGINT, signal.default_int_handler)
    print("\nKeyboardInterrupt")
    # Need to reprint the prompt at this stage


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------
def inputhook_glut():
    """Run the pyglet event loop by processing pending events only.

    This keeps processing pending events until stdin is ready.  After
    processing all pending events, a call to time.sleep is inserted.  This is
    needed, otherwise, CPU usage is at 100%.  This sleep time should be tuned
    though for best performance.
    """
    # We need to protect against a user pressing Control-C when IPython is
    # idle and this is running. We trap KeyboardInterrupt and pass.

    signal.signal(signal.SIGINT, glut_int_handler)

    try:
        t = clock()

        # Make sure the default window is set after a window has been closed
        if glut.glutGetWindow() == 0:
            glut.glutSetWindow(1)
            glutMainLoopEvent()
            return 0

        while not stdin_ready():
            glutMainLoopEvent()
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
    except KeyboardInterrupt:
        pass
    return 0

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_net_command.py ===
from _pydevd_bundle.pydevd_constants import (
    DebugInfoHolder,
    get_global_debugger,
    GetGlobalDebugger,
    set_global_debugger,
)  # Keep for backward compatibility @UnusedImport
from _pydevd_bundle.pydevd_utils import quote_smart as quote, to_string
from _pydevd_bundle.pydevd_comm_constants import ID_TO_MEANING, CMD_EXIT
from _pydevd_bundle.pydevd_constants import HTTP_PROTOCOL, HTTP_JSON_PROTOCOL, get_protocol, IS_JYTHON, ForkSafeLock
import json
from _pydev_bundle import pydev_log


class _BaseNetCommand(object):
    # Command id. Should be set in instance.
    id = -1

    # Dict representation of the command to be set in instance. Only set for json commands.
    as_dict = None

    def send(self, *args, **kwargs):
        pass

    def call_after_send(self, callback):
        pass


class _NullNetCommand(_BaseNetCommand):
    pass


class _NullExitCommand(_NullNetCommand):
    id = CMD_EXIT


# Constant meant to be passed to the writer when the command is meant to be ignored.
NULL_NET_COMMAND = _NullNetCommand()

# Exit command -- only internal (we don't want/need to send this to the IDE).
NULL_EXIT_COMMAND = _NullExitCommand()


class NetCommand(_BaseNetCommand):
    """
    Commands received/sent over the network.

    Command can represent command received from the debugger,
    or one to be sent by daemon.
    """

    next_seq = 0  # sequence numbers

    _showing_debug_info = 0
    _show_debug_info_lock = ForkSafeLock(rlock=True)

    _after_send = None

    def __init__(self, cmd_id, seq, text, is_json=False):
        """
        If sequence is 0, new sequence will be generated (otherwise, this was the response
        to a command from the client).
        """
        protocol = get_protocol()
        self.id = cmd_id
        if seq == 0:
            NetCommand.next_seq += 2
            seq = NetCommand.next_seq

        self.seq = seq

        if is_json:
            if hasattr(text, "to_dict"):
                as_dict = text.to_dict(update_ids_to_dap=True)
            else:
                assert isinstance(text, dict)
                as_dict = text
            as_dict["pydevd_cmd_id"] = cmd_id
            as_dict["seq"] = seq
            self.as_dict = as_dict
            try:
                text = json.dumps(as_dict)
            except TypeError:
                text = json.dumps(as_dict, default=str)

        assert isinstance(text, str)

        if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
            self._show_debug_info(cmd_id, seq, text)

        if is_json:
            msg = text
        else:
            if protocol not in (HTTP_PROTOCOL, HTTP_JSON_PROTOCOL):
                encoded = quote(to_string(text), '/<>_=" \t')
                msg = "%s\t%s\t%s\n" % (cmd_id, seq, encoded)

            else:
                msg = "%s\t%s\t%s" % (cmd_id, seq, text)

        if isinstance(msg, str):
            msg = msg.encode("utf-8")

        assert isinstance(msg, bytes)
        as_bytes = msg
        self._as_bytes = as_bytes

    def send(self, sock):
        as_bytes = self._as_bytes
        try:
            if get_protocol() in (HTTP_PROTOCOL, HTTP_JSON_PROTOCOL):
                sock.sendall(("Content-Length: %s\r\n\r\n" % len(as_bytes)).encode("ascii"))
            sock.sendall(as_bytes)
            if self._after_send:
                for method in self._after_send:
                    method(sock)
        except:
            if IS_JYTHON:
                # Ignore errors in sock.sendall in Jython (seems to be common for Jython to
                # give spurious exceptions at interpreter shutdown here).
                pass
            else:
                raise

    def call_after_send(self, callback):
        if not self._after_send:
            self._after_send = [callback]
        else:
            self._after_send.append(callback)

    @classmethod
    def _show_debug_info(cls, cmd_id, seq, text):
        with cls._show_debug_info_lock:
            # Only one thread each time (rlock).
            if cls._showing_debug_info:
                # avoid recursing in the same thread (just printing could create
                # a new command when redirecting output).
                return

            cls._showing_debug_info += 1
            try:
                out_message = "sending cmd (%s) --> " % (get_protocol(),)
                out_message += "%20s" % ID_TO_MEANING.get(str(cmd_id), "UNKNOWN")
                out_message += " "
                out_message += text.replace("\n", " ")
                try:
                    pydev_log.critical("%s\n", out_message)
                except:
                    pass
            finally:
                cls._showing_debug_info -= 1

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\magics.py ===
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
"""Colab Magics class.

Installs %%llm magics.
"""
from __future__ import annotations

import abc

from google.auth import credentials
from google.generativeai import client as genai
from google.generativeai.notebook import gspread_client
from google.generativeai.notebook import ipython_env
from google.generativeai.notebook import ipython_env_impl
from google.generativeai.notebook import magics_engine
from google.generativeai.notebook import post_process_utils
from google.generativeai.notebook import sheets_utils

import IPython
from IPython.core import magic


# Set the UA to distinguish the magic from the client. Do this at import-time
# so that a user can still call `genai.configure()`, and both their settings
# and this are honored.
genai.USER_AGENT = "genai-py-magic"

SheetsInputs = sheets_utils.SheetsInputs
SheetsOutputs = sheets_utils.SheetsOutputs

# Decorator functions for post-processing.
post_process_add_fn = post_process_utils.post_process_add_fn
post_process_replace_fn = post_process_utils.post_process_replace_fn

# Globals.
_ipython_env: ipython_env.IPythonEnv | None = None


def _get_ipython_env() -> ipython_env.IPythonEnv:
    """Lazily constructs and returns a global IPythonEnv instance."""
    global _ipython_env
    if _ipython_env is None:
        _ipython_env = ipython_env_impl.IPythonEnvImpl()
    return _ipython_env


def authorize(creds: credentials.Credentials) -> None:
    """Sets up credentials.

    This is used for interacting Google APIs, such as Google Sheets.

    Args:
      creds: The credentials that will be used (e.g. to read from Google Sheets.)
    """
    gspread_client.authorize(creds=creds, env=_get_ipython_env())


class AbstractMagics(abc.ABC):
    """Defines interface to Magics class."""

    @abc.abstractmethod
    def llm(self, cell_line: str | None, cell_body: str | None):
        """Perform various LLM-related operations.

        Args:
          cell_line: String to pass to the MagicsEngine.
          cell_body: Contents of the cell body.
        """
        raise NotImplementedError()


class MagicsImpl(AbstractMagics):
    """Actual class implementing the magics functionality.

    We use a separate class to ensure a single, global instance
    of the magics class.
    """

    def __init__(self):
        self._engine = magics_engine.MagicsEngine(env=_get_ipython_env())

    def llm(self, cell_line: str | None, cell_body: str | None):
        """Perform various LLM-related operations.

        Args:
          cell_line: String to pass to the MagicsEngine.
          cell_body: Contents of the cell body.

        Returns:
          Results from running MagicsEngine.
        """
        cell_line = cell_line or ""
        cell_body = cell_body or ""
        return self._engine.execute_cell(cell_line, cell_body)


@magic.magics_class
class Magics(magic.Magics):
    """Class to register the magic with Colab.

    Objects of this class delegate all calls to a single,
    global instance.
    """

    # Global instance
    _instance = None

    @classmethod
    def get_instance(cls) -> AbstractMagics:
        """Retrieve global instance of the Magics object."""
        if cls._instance is None:
            cls._instance = MagicsImpl()
        return cls._instance

    @magic.line_cell_magic
    def llm(self, cell_line: str | None, cell_body: str | None):
        """Perform various LLM-related operations.

        Args:
          cell_line: String to pass to the MagicsEngine.
          cell_body: Contents of the cell body.

        Returns:
          Results from running MagicsEngine.
        """
        return Magics.get_instance().llm(cell_line=cell_line, cell_body=cell_body)

    @magic.line_cell_magic
    def palm(self, cell_line: str | None, cell_body: str | None):
        return self.llm(cell_line, cell_body)

    @magic.line_cell_magic
    def gemini(self, cell_line: str | None, cell_body: str | None):
        return self.llm(cell_line, cell_body)


IPython.get_ipython().register_magics(Magics)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_experimental\mcp_server\sse_transport.py ===
"""
This is a modification of code from: https://github.com/SecretiveShell/MCP-Bridge/blob/master/mcp_bridge/mcp_server/sse_transport.py

Credit to the maintainers of SecretiveShell for their SSE Transport implementation

"""

from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

import anyio
import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from fastapi.requests import Request
from fastapi.responses import Response
from pydantic import ValidationError
from sse_starlette import EventSourceResponse
from starlette.types import Receive, Scope, Send

from litellm._logging import verbose_logger


class SseServerTransport:
    """
    SSE server transport for MCP. This class provides _two_ ASGI applications,
    suitable to be used with a framework like Starlette and a server like Hypercorn:

        1. connect_sse() is an ASGI application which receives incoming GET requests,
           and sets up a new SSE stream to send server messages to the client.
        2. handle_post_message() is an ASGI application which receives incoming POST
           requests, which should contain client messages that link to a
           previously-established SSE session.
    """

    _endpoint: str
    _read_stream_writers: dict[
        UUID, MemoryObjectSendStream[types.JSONRPCMessage | Exception]
    ]

    def __init__(self, endpoint: str) -> None:
        """
        Creates a new SSE server transport, which will direct the client to POST
        messages to the relative or absolute URL given.
        """

        super().__init__()
        self._endpoint = endpoint
        self._read_stream_writers = {}
        verbose_logger.debug(
            f"SseServerTransport initialized with endpoint: {endpoint}"
        )

    @asynccontextmanager
    async def connect_sse(self, request: Request):
        if request.scope["type"] != "http":
            verbose_logger.error("connect_sse received non-HTTP request")
            raise ValueError("connect_sse can only handle HTTP requests")

        verbose_logger.debug("Setting up SSE connection")
        read_stream: MemoryObjectReceiveStream[types.JSONRPCMessage | Exception]
        read_stream_writer: MemoryObjectSendStream[types.JSONRPCMessage | Exception]

        write_stream: MemoryObjectSendStream[types.JSONRPCMessage]
        write_stream_reader: MemoryObjectReceiveStream[types.JSONRPCMessage]

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        session_id = uuid4()
        session_uri = f"{quote(self._endpoint)}?session_id={session_id.hex}"
        self._read_stream_writers[session_id] = read_stream_writer
        verbose_logger.debug(f"Created new session with ID: {session_id}")

        sse_stream_writer: MemoryObjectSendStream[dict[str, Any]]
        sse_stream_reader: MemoryObjectReceiveStream[dict[str, Any]]
        sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream(
            0, dict[str, Any]
        )

        async def sse_writer():
            verbose_logger.debug("Starting SSE writer")
            async with sse_stream_writer, write_stream_reader:
                await sse_stream_writer.send({"event": "endpoint", "data": session_uri})
                verbose_logger.debug(f"Sent endpoint event: {session_uri}")

                async for message in write_stream_reader:
                    verbose_logger.debug(f"Sending message via SSE: {message}")
                    await sse_stream_writer.send(
                        {
                            "event": "message",
                            "data": message.model_dump_json(
                                by_alias=True, exclude_none=True
                            ),
                        }
                    )

        async with anyio.create_task_group() as tg:
            response = EventSourceResponse(
                content=sse_stream_reader, data_sender_callable=sse_writer
            )
            verbose_logger.debug("Starting SSE response task")
            tg.start_soon(response, request.scope, request.receive, request._send)

            verbose_logger.debug("Yielding read and write streams")
            yield (read_stream, write_stream)

    async def handle_post_message(
        self, scope: Scope, receive: Receive, send: Send
    ) -> Response:
        verbose_logger.debug("Handling POST message")
        request = Request(scope, receive)

        session_id_param = request.query_params.get("session_id")
        if session_id_param is None:
            verbose_logger.warning("Received request without session_id")
            response = Response("session_id is required", status_code=400)
            return response

        try:
            session_id = UUID(hex=session_id_param)
            verbose_logger.debug(f"Parsed session ID: {session_id}")
        except ValueError:
            verbose_logger.warning(f"Received invalid session ID: {session_id_param}")
            response = Response("Invalid session ID", status_code=400)
            return response

        writer = self._read_stream_writers.get(session_id)
        if not writer:
            verbose_logger.warning(f"Could not find session for ID: {session_id}")
            response = Response("Could not find session", status_code=404)
            return response

        json = await request.json()
        verbose_logger.debug(f"Received JSON: {json}")

        try:
            message = types.JSONRPCMessage.model_validate(json)
            verbose_logger.debug(f"Validated client message: {message}")
        except ValidationError as err:
            verbose_logger.error(f"Failed to parse message: {err}")
            response = Response("Could not parse message", status_code=400)
            await writer.send(err)
            return response

        verbose_logger.debug(f"Sending message to writer: {message}")
        response = Response("Accepted", status_code=202)
        await writer.send(message)
        return response

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\vip.py ===
"""
    pygments.lexers.vip
    ~~~~~~~~~~~~~~~~~~~

    Lexers for Visual Prolog & Grammar files.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, inherit, words, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['VisualPrologLexer', 'VisualPrologGrammarLexer']


class VisualPrologBaseLexer(RegexLexer):
    minorendkw = ('try', 'foreach', 'if')
    minorkwexp = ('and', 'catch', 'do', 'else', 'elseif', 'erroneous', 'externally', 'failure', 'finally', 'foreach', 'if', 'or', 'orelse', 'otherwise', 'then',
                  'try', 'div', 'mod', 'rem', 'quot')
    dockw = ('short', 'detail', 'end', 'withdomain')
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (words(minorendkw, prefix=r'\bend\s+', suffix=r'\b'), Keyword.Minor),
            (r'end', Keyword),
            (words(minorkwexp, suffix=r'\b'), Keyword.Minor),
            (r'0[xo][\da-fA-F_]+', Number),
            (r'((\d[\d_]*)?\.)?\d[\d_]*([eE][\-+]?\d+)?', Number),
            (r'_\w*', Name.Variable.Anonymous),
            (r'[A-Z]\w*', Name.Variable),
            (r'@\w+', Name.Variable),
            (r'[a-z]\w*', Name),
            (r'/\*', Comment, 'comment'),
            (r'\%', Comment, 'commentline'),
            (r'"', String.Symbol, 'string'),
            (r'\'', String.Symbol, 'stringsingle'),
            (r'@"', String.Symbol, 'atstring'),
            (r'[\-+*^/!?<>=~:]+', Operator),
            (r'[$,.[\]|(){}\\]+', Punctuation),
            (r'.', Text),
        ],
        'commentdoc': [
            (words(dockw, prefix=r'@', suffix=r'\b'), Comment.Preproc),
            (r'@', Comment),
        ],
        'commentline': [
            include('commentdoc'),
            (r'[^@\n]+', Comment),
            (r'$', Comment, '#pop'),
        ],
        'comment': [
            include('commentdoc'),
            (r'[^@*/]+', Comment),
            (r'/\*', Comment, '#push'),
            (r'\*/', Comment, '#pop'),
            (r'[*/]', Comment),
        ],
        'stringescape': [
            (r'\\u[0-9a-fA-F]{4}', String.Escape),
            (r'\\[\'"ntr\\]', String.Escape),
        ],
        'stringsingle': [
            include('stringescape'),
            (r'\'', String.Symbol, '#pop'),
            (r'[^\'\\\n]+', String),
            (r'\n', String.Escape.Error, '#pop'),
        ],
        'string': [
            include('stringescape'),
            (r'"', String.Symbol, '#pop'),
            (r'[^"\\\n]+', String),
            (r'\n', String.Escape.Error, '#pop'),
        ],
        'atstring': [
            (r'""', String.Escape),
            (r'"', String.Symbol, '#pop'),
            (r'[^"]+', String),
        ]
    }


class VisualPrologLexer(VisualPrologBaseLexer):
    """Lexer for VisualProlog
    """
    name = 'Visual Prolog'
    url = 'https://www.visual-prolog.com/'
    aliases = ['visualprolog']
    filenames = ['*.pro', '*.cl', '*.i', '*.pack', '*.ph']
    version_added = '2.17'

    majorkw = ('goal', 'namespace', 'interface', 'class', 'implement', 'where', 'open', 'inherits', 'supports', 'resolve',
               'delegate', 'monitor', 'constants', 'domains', 'predicates', 'constructors', 'properties', 'clauses', 'facts')
    minorkw = ('align', 'anyflow', 'as', 'bitsize', 'determ', 'digits', 'erroneous', 'externally', 'failure', 'from',
               'guard', 'multi', 'nondeterm', 'or', 'orelse', 'otherwise', 'procedure', 'resolve', 'single', 'suspending')
    directivekw = ('bininclude', 'else', 'elseif', 'endif', 'error', 'export', 'externally', 'from', 'grammargenerate',
                   'grammarinclude', 'if', 'include', 'message', 'options', 'orrequires', 'requires', 'stringinclude', 'then')
    tokens = {
        'root': [
            (words(minorkw, suffix=r'\b'), Keyword.Minor),
            (words(majorkw, suffix=r'\b'), Keyword),
            (words(directivekw, prefix='#', suffix=r'\b'), Keyword.Directive),
            inherit
        ]
    }

    def analyse_text(text):
        """Competes with IDL and Prolog on *.pro; div. lisps on*.cl and SwigLexer on *.i"""
        # These are *really* good indicators (and not conflicting with the other languages)
        # end-scope first on line e.g. 'end implement'
        # section keyword alone on line e.g. 'clauses'
        if re.search(r'^\s*(end\s+(interface|class|implement)|(clauses|predicates|domains|facts|constants|properties)\s*$)', text):
            return 0.98
        else:
            return 0


class VisualPrologGrammarLexer(VisualPrologBaseLexer):
    """Lexer for VisualProlog grammar
    """

    name = 'Visual Prolog Grammar'
    url = 'https://www.visual-prolog.com/'
    aliases = ['visualprologgrammar']
    filenames = ['*.vipgrm']
    version_added = '2.17'

    majorkw = ('open', 'namespace', 'grammar', 'nonterminals',
               'startsymbols', 'terminals', 'rules', 'precedence')
    directivekw = ('bininclude', 'stringinclude')
    tokens = {
        'root': [
            (words(majorkw, suffix=r'\b'), Keyword),
            (words(directivekw, prefix='#', suffix=r'\b'), Keyword.Directive),
            inherit
        ]
    }

    def analyse_text(text):
        """No competditors (currently)"""
        # These are *really* good indicators
        # end-scope first on line e.g. 'end grammar'
        # section keyword alone on line e.g. 'rules'
        if re.search(r'^\s*(end\s+grammar|(nonterminals|startsymbols|terminals|rules|precedence)\s*$)', text):
            return 0.98
        else:
            return 0

# === NexusCore/openenv\Lib\site-packages\tokenizers\implementations\char_level_bpe.py ===
from typing import Dict, Iterator, List, Optional, Tuple, Union

from .. import AddedToken, Tokenizer, decoders, pre_tokenizers, trainers
from ..models import BPE
from ..normalizers import BertNormalizer, Lowercase, Sequence, unicode_normalizer_from_str
from .base_tokenizer import BaseTokenizer


class CharBPETokenizer(BaseTokenizer):
    """Original BPE Tokenizer

    Represents the BPE algorithm, as introduced by Rico Sennrich
    (https://arxiv.org/abs/1508.07909)

    The defaults settings corresponds to OpenAI GPT BPE tokenizers and differs from the original
    Sennrich subword-nmt implementation by the following options that you can deactivate:
        - adding a normalizer to clean up the text (deactivate with `bert_normalizer=False`) by:
            * removing any control characters and replacing all whitespaces by the classic one.
            * handle chinese chars by putting spaces around them.
            * strip all accents.
        - spitting on punctuation in addition to whitespaces (deactivate it with
          `split_on_whitespace_only=True`)
    """

    def __init__(
        self,
        vocab: Optional[Union[str, Dict[str, int]]] = None,
        merges: Optional[Union[str, Dict[Tuple[int, int], Tuple[int, int]]]] = None,
        unk_token: Union[str, AddedToken] = "<unk>",
        suffix: str = "</w>",
        dropout: Optional[float] = None,
        lowercase: bool = False,
        unicode_normalizer: Optional[str] = None,
        bert_normalizer: bool = True,
        split_on_whitespace_only: bool = False,
    ):
        if vocab is not None and merges is not None:
            tokenizer = Tokenizer(
                BPE(
                    vocab,
                    merges,
                    dropout=dropout,
                    unk_token=str(unk_token),
                    end_of_word_suffix=suffix,
                )
            )
        else:
            tokenizer = Tokenizer(BPE(unk_token=str(unk_token), dropout=dropout, end_of_word_suffix=suffix))

        if tokenizer.token_to_id(str(unk_token)) is not None:
            tokenizer.add_special_tokens([str(unk_token)])

        # Check for Unicode normalization first (before everything else)
        normalizers = []

        if unicode_normalizer:
            normalizers += [unicode_normalizer_from_str(unicode_normalizer)]

        if bert_normalizer:
            normalizers += [BertNormalizer(lowercase=False)]

        if lowercase:
            normalizers += [Lowercase()]

        # Create the normalizer structure
        if len(normalizers) > 0:
            if len(normalizers) > 1:
                tokenizer.normalizer = Sequence(normalizers)
            else:
                tokenizer.normalizer = normalizers[0]

        if split_on_whitespace_only:
            tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
        else:
            tokenizer.pre_tokenizer = pre_tokenizers.BertPreTokenizer()

        tokenizer.decoder = decoders.BPEDecoder(suffix=suffix)

        parameters = {
            "model": "BPE",
            "unk_token": unk_token,
            "suffix": suffix,
            "dropout": dropout,
            "lowercase": lowercase,
            "unicode_normalizer": unicode_normalizer,
            "bert_normalizer": bert_normalizer,
            "split_on_whitespace_only": split_on_whitespace_only,
        }

        super().__init__(tokenizer, parameters)

    @staticmethod
    def from_file(vocab_filename: str, merges_filename: str, **kwargs):
        vocab, merges = BPE.read_file(vocab_filename, merges_filename)
        return CharBPETokenizer(vocab, merges, **kwargs)

    def train(
        self,
        files: Union[str, List[str]],
        vocab_size: int = 30000,
        min_frequency: int = 2,
        special_tokens: List[Union[str, AddedToken]] = ["<unk>"],
        limit_alphabet: int = 1000,
        initial_alphabet: List[str] = [],
        suffix: Optional[str] = "</w>",
        show_progress: bool = True,
    ):
        """Train the model using the given files"""

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=special_tokens,
            limit_alphabet=limit_alphabet,
            initial_alphabet=initial_alphabet,
            end_of_word_suffix=suffix,
            show_progress=show_progress,
        )
        if isinstance(files, str):
            files = [files]
        self._tokenizer.train(files, trainer=trainer)

    def train_from_iterator(
        self,
        iterator: Union[Iterator[str], Iterator[Iterator[str]]],
        vocab_size: int = 30000,
        min_frequency: int = 2,
        special_tokens: List[Union[str, AddedToken]] = ["<unk>"],
        limit_alphabet: int = 1000,
        initial_alphabet: List[str] = [],
        suffix: Optional[str] = "</w>",
        show_progress: bool = True,
        length: Optional[int] = None,
    ):
        """Train the model using the given iterator"""

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=special_tokens,
            limit_alphabet=limit_alphabet,
            initial_alphabet=initial_alphabet,
            end_of_word_suffix=suffix,
            show_progress=show_progress,
        )
        self._tokenizer.train_from_iterator(
            iterator,
            trainer=trainer,
            length=length,
        )

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\filesystem.py ===
import fnmatch
import os
import os.path
import random
import sys
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, Generator, List, Union, cast

from pip._internal.utils.compat import get_path_uid
from pip._internal.utils.misc import format_size
from pip._internal.utils.retry import retry


def check_path_owner(path: str) -> bool:
    # If we don't have a way to check the effective uid of this process, then
    # we'll just assume that we own the directory.
    if sys.platform == "win32" or not hasattr(os, "geteuid"):
        return True

    assert os.path.isabs(path)

    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Check if path is writable by current user.
            if os.geteuid() == 0:
                # Special handling for root user in order to handle properly
                # cases where users use sudo without -H flag.
                try:
                    path_uid = get_path_uid(path)
                except OSError:
                    return False
                return path_uid == 0
            else:
                return os.access(path, os.W_OK)
        else:
            previous, path = path, os.path.dirname(path)
    return False  # assume we don't own the path


@contextmanager
def adjacent_tmp_file(path: str, **kwargs: Any) -> Generator[BinaryIO, None, None]:
    """Return a file-like object pointing to a tmp file next to path.

    The file is created securely and is ensured to be written to disk
    after the context reaches its end.

    kwargs will be passed to tempfile.NamedTemporaryFile to control
    the way the temporary file will be opened.
    """
    with NamedTemporaryFile(
        delete=False,
        dir=os.path.dirname(path),
        prefix=os.path.basename(path),
        suffix=".tmp",
        **kwargs,
    ) as f:
        result = cast(BinaryIO, f)
        try:
            yield result
        finally:
            result.flush()
            os.fsync(result.fileno())


replace = retry(stop_after_delay=1, wait=0.25)(os.replace)


# test_writable_dir and _test_writable_dir_win are copied from Flit,
# with the author's agreement to also place them under pip's license.
def test_writable_dir(path: str) -> bool:
    """Check if a directory is writable.

    Uses os.access() on POSIX, tries creating files on Windows.
    """
    # If the directory doesn't exist, find the closest parent that does.
    while not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break  # Should never get here, but infinite loops are bad
        path = parent

    if os.name == "posix":
        return os.access(path, os.W_OK)

    return _test_writable_dir_win(path)


def _test_writable_dir_win(path: str) -> bool:
    # os.access doesn't work on Windows: http://bugs.python.org/issue2528
    # and we can't use tempfile: http://bugs.python.org/issue22107
    basename = "accesstest_deleteme_fishfingers_custard_"
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(10):
        name = basename + "".join(random.choice(alphabet) for _ in range(6))
        file = os.path.join(path, name)
        try:
            fd = os.open(file, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            pass
        except PermissionError:
            # This could be because there's a directory with the same name.
            # But it's highly unlikely there's a directory called that,
            # so we'll assume it's because the parent dir is not writable.
            # This could as well be because the parent dir is not readable,
            # due to non-privileged user access.
            return False
        else:
            os.close(fd)
            os.unlink(file)
            return True

    # This should never be reached
    raise OSError("Unexpected condition testing for writable directory")


def find_files(path: str, pattern: str) -> List[str]:
    """Returns a list of absolute paths of files beneath path, recursively,
    with filenames which match the UNIX-style shell glob pattern."""
    result: List[str] = []
    for root, _, files in os.walk(path):
        matches = fnmatch.filter(files, pattern)
        result.extend(os.path.join(root, f) for f in matches)
    return result


def file_size(path: str) -> Union[int, float]:
    # If it's a symlink, return 0.
    if os.path.islink(path):
        return 0
    return os.path.getsize(path)


def format_file_size(path: str) -> str:
    return format_size(file_size(path))


def directory_size(path: str) -> Union[int, float]:
    size = 0.0
    for root, _dirs, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            size += file_size(file_path)
    return size


def format_directory_size(path: str) -> str:
    return format_size(directory_size(path))

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\repr.py ===
import inspect
from functools import partial
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")


Result = Iterable[Union[Any, Tuple[Any], Tuple[str, Any], Tuple[str, Any, Any]]]
RichReprResult = Result


class ReprError(Exception):
    """An error occurred when attempting to build a repr."""


@overload
def auto(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def auto(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def auto(
    cls: Optional[Type[T]] = None, *, angular: Optional[bool] = None
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """Class decorator to create __repr__ from __rich_repr__"""

    def do_replace(cls: Type[T], angular: Optional[bool] = None) -> Type[T]:
        def auto_repr(self: T) -> str:
            """Create repr string from __rich_repr__"""
            repr_str: List[str] = []
            append = repr_str.append

            angular: bool = getattr(self.__rich_repr__, "angular", False)  # type: ignore[attr-defined]
            for arg in self.__rich_repr__():  # type: ignore[attr-defined]
                if isinstance(arg, tuple):
                    if len(arg) == 1:
                        append(repr(arg[0]))
                    else:
                        key, value, *default = arg
                        if key is None:
                            append(repr(value))
                        else:
                            if default and default[0] == value:
                                continue
                            append(f"{key}={value!r}")
                else:
                    append(repr(arg))
            if angular:
                return f"<{self.__class__.__name__} {' '.join(repr_str)}>"
            else:
                return f"{self.__class__.__name__}({', '.join(repr_str)})"

        def auto_rich_repr(self: Type[T]) -> Result:
            """Auto generate __rich_rep__ from signature of __init__"""
            try:
                signature = inspect.signature(self.__init__)
                for name, param in signature.parameters.items():
                    if param.kind == param.POSITIONAL_ONLY:
                        yield getattr(self, name)
                    elif param.kind in (
                        param.POSITIONAL_OR_KEYWORD,
                        param.KEYWORD_ONLY,
                    ):
                        if param.default is param.empty:
                            yield getattr(self, param.name)
                        else:
                            yield param.name, getattr(self, param.name), param.default
            except Exception as error:
                raise ReprError(
                    f"Failed to auto generate __rich_repr__; {error}"
                ) from None

        if not hasattr(cls, "__rich_repr__"):
            auto_rich_repr.__doc__ = "Build a rich repr"
            cls.__rich_repr__ = auto_rich_repr  # type: ignore[attr-defined]

        auto_repr.__doc__ = "Return repr(self)"
        cls.__repr__ = auto_repr  # type: ignore[assignment]
        if angular is not None:
            cls.__rich_repr__.angular = angular  # type: ignore[attr-defined]
        return cls

    if cls is None:
        return partial(do_replace, angular=angular)
    else:
        return do_replace(cls, angular=angular)


@overload
def rich_repr(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def rich_repr(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def rich_repr(
    cls: Optional[Type[T]] = None, *, angular: bool = False
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    if cls is None:
        return auto(angular=angular)
    else:
        return auto(cls)


if __name__ == "__main__":

    @auto
    class Foo:
        def __rich_repr__(self) -> Result:
            yield "foo"
            yield "bar", {"shopping": ["eggs", "ham", "pineapple"]}
            yield "buy", "hand sanitizer"

    foo = Foo()
    from pip._vendor.rich.console import Console

    console = Console()

    console.rule("Standard repr")
    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

    console.rule("Angular repr")
    Foo.__rich_repr__.angular = True  # type: ignore[attr-defined]

    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\connection.py ===
from __future__ import absolute_import

import socket

from ..contrib import _appengine_environ
from ..exceptions import LocationParseError
from ..packages import six
from .wait import NoWayToWaitForSocketError, wait_for_read


def is_connection_dropped(conn):  # Platform-specific
    """
    Returns True if the connection is dropped and should be closed.

    :param conn:
        :class:`http.client.HTTPConnection` object.

    Note: For platforms like AppEngine, this will always return ``False`` to
    let the platform handle connection recycling transparently for us.
    """
    sock = getattr(conn, "sock", False)
    if sock is False:  # Platform-specific: AppEngine
        return False
    if sock is None:  # Connection already closed (such as by httplib).
        return True
    try:
        # Returns True if readable, which here means it's been dropped
        return wait_for_read(sock, timeout=0.0)
    except NoWayToWaitForSocketError:  # Platform-specific: AppEngine
        return False


# This function is copied from socket.py in the Python 2.7 standard
# library test suite. Added to its signature is only `socket_options`.
# One additional modification is that we avoid binding to IPv6 servers
# discovered in DNS if the system doesn't have IPv6 functionality.
def create_connection(
    address,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address=None,
    socket_options=None,
):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`socket.getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.
    """

    host, port = address
    if host.startswith("["):
        host = host.strip("[]")
    err = None

    # Using the value from allowed_gai_family() in the context of getaddrinfo lets
    # us select whether to work with IPv4 DNS records, IPv6 records, or both.
    # The original create_connection function always returns all records.
    family = allowed_gai_family()

    try:
        host.encode("idna")
    except UnicodeError:
        return six.raise_from(
            LocationParseError(u"'%s', label empty or too long" % host), None
        )

    for res in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)

            # If provided, set socket level options before connecting.
            _set_socket_options(sock, socket_options)

            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except socket.error as e:
            err = e
            if sock is not None:
                sock.close()
                sock = None

    if err is not None:
        raise err

    raise socket.error("getaddrinfo returns an empty list")


def _set_socket_options(sock, options):
    if options is None:
        return

    for opt in options:
        sock.setsockopt(*opt)


def allowed_gai_family():
    """This function is designed to work in the context of
    getaddrinfo, where family=socket.AF_UNSPEC is the default and
    will perform a DNS search for both IPv6 and IPv4 records."""

    family = socket.AF_INET
    if HAS_IPV6:
        family = socket.AF_UNSPEC
    return family


def _has_ipv6(host):
    """Returns True if the system can bind an IPv6 address."""
    sock = None
    has_ipv6 = False

    # App Engine doesn't support IPV6 sockets and actually has a quota on the
    # number of sockets that can be used, so just early out here instead of
    # creating a socket needlessly.
    # See https://github.com/urllib3/urllib3/issues/1446
    if _appengine_environ.is_appengine_sandbox():
        return False

    if socket.has_ipv6:
        # has_ipv6 returns true if cPython was compiled with IPv6 support.
        # It does not tell us if the system has IPv6 support enabled. To
        # determine that we must bind to an IPv6 address.
        # https://github.com/urllib3/urllib3/pull/611
        # https://bugs.python.org/issue658327
        try:
            sock = socket.socket(socket.AF_INET6)
            sock.bind((host, 0))
            has_ipv6 = True
        except Exception:
            pass

    if sock:
        sock.close()
    return has_ipv6


HAS_IPV6 = _has_ipv6("::1")

# === NexusCore/openenv\Lib\site-packages\PIL\GimpGradientFile.py ===
#
# Python Imaging Library
# $Id$
#
# stuff to read (and render) GIMP gradient files
#
# History:
#       97-08-23 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

"""
Stuff to translate curve segments to palette values (derived from
the corresponding code in GIMP, written by Federico Mena Quintero.
See the GIMP distribution for more information.)
"""
from __future__ import annotations

from math import log, pi, sin, sqrt
from typing import IO, Callable

from ._binary import o8

EPSILON = 1e-10
""""""  # Enable auto-doc for data member


def linear(middle: float, pos: float) -> float:
    if pos <= middle:
        if middle < EPSILON:
            return 0.0
        else:
            return 0.5 * pos / middle
    else:
        pos = pos - middle
        middle = 1.0 - middle
        if middle < EPSILON:
            return 1.0
        else:
            return 0.5 + 0.5 * pos / middle


def curved(middle: float, pos: float) -> float:
    return pos ** (log(0.5) / log(max(middle, EPSILON)))


def sine(middle: float, pos: float) -> float:
    return (sin((-pi / 2.0) + pi * linear(middle, pos)) + 1.0) / 2.0


def sphere_increasing(middle: float, pos: float) -> float:
    return sqrt(1.0 - (linear(middle, pos) - 1.0) ** 2)


def sphere_decreasing(middle: float, pos: float) -> float:
    return 1.0 - sqrt(1.0 - linear(middle, pos) ** 2)


SEGMENTS = [linear, curved, sine, sphere_increasing, sphere_decreasing]
""""""  # Enable auto-doc for data member


class GradientFile:
    gradient: (
        list[
            tuple[
                float,
                float,
                float,
                list[float],
                list[float],
                Callable[[float, float], float],
            ]
        ]
        | None
    ) = None

    def getpalette(self, entries: int = 256) -> tuple[bytes, str]:
        assert self.gradient is not None
        palette = []

        ix = 0
        x0, x1, xm, rgb0, rgb1, segment = self.gradient[ix]

        for i in range(entries):
            x = i / (entries - 1)

            while x1 < x:
                ix += 1
                x0, x1, xm, rgb0, rgb1, segment = self.gradient[ix]

            w = x1 - x0

            if w < EPSILON:
                scale = segment(0.5, 0.5)
            else:
                scale = segment((xm - x0) / w, (x - x0) / w)

            # expand to RGBA
            r = o8(int(255 * ((rgb1[0] - rgb0[0]) * scale + rgb0[0]) + 0.5))
            g = o8(int(255 * ((rgb1[1] - rgb0[1]) * scale + rgb0[1]) + 0.5))
            b = o8(int(255 * ((rgb1[2] - rgb0[2]) * scale + rgb0[2]) + 0.5))
            a = o8(int(255 * ((rgb1[3] - rgb0[3]) * scale + rgb0[3]) + 0.5))

            # add to palette
            palette.append(r + g + b + a)

        return b"".join(palette), "RGBA"


class GimpGradientFile(GradientFile):
    """File handler for GIMP's gradient format."""

    def __init__(self, fp: IO[bytes]) -> None:
        if not fp.readline().startswith(b"GIMP Gradient"):
            msg = "not a GIMP gradient file"
            raise SyntaxError(msg)

        line = fp.readline()

        # GIMP 1.2 gradient files don't contain a name, but GIMP 1.3 files do
        if line.startswith(b"Name: "):
            line = fp.readline().strip()

        count = int(line)

        self.gradient = []

        for i in range(count):
            s = fp.readline().split()
            w = [float(x) for x in s[:11]]

            x0, x1 = w[0], w[2]
            xm = w[1]
            rgb0 = w[3:7]
            rgb1 = w[7:11]

            segment = SEGMENTS[int(s[11])]
            cspace = int(s[12])

            if cspace != 0:
                msg = "cannot handle HSV colour space"
                raise OSError(msg)

            self.gradient.append((x0, x1, xm, rgb0, rgb1, segment))

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc8226.py ===
# This file is being contributed to pyasn1-modules software.
#
# Created by Russ Housley with assistance from the asn1ate tool, with manual
#   changes to implement appropriate constraints and added comments.
# Modified by Russ Housley to add maps for use with opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# JWT Claim Constraints and TN Authorization List for certificate extensions.
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc8226.txt (with errata corrected)

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280

MAX = float('inf')


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


class JWTClaimName(char.IA5String):
    pass


class JWTClaimNames(univ.SequenceOf):
    pass

JWTClaimNames.componentType = JWTClaimName()
JWTClaimNames.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class JWTClaimPermittedValues(univ.Sequence):
    pass

JWTClaimPermittedValues.componentType = namedtype.NamedTypes(
    namedtype.NamedType('claim', JWTClaimName()),
    namedtype.NamedType('permitted', univ.SequenceOf(
        componentType=char.UTF8String()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX)))
)


class JWTClaimPermittedValuesList(univ.SequenceOf):
    pass

JWTClaimPermittedValuesList.componentType = JWTClaimPermittedValues()
JWTClaimPermittedValuesList.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class JWTClaimConstraints(univ.Sequence):
    pass

JWTClaimConstraints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('mustInclude',
        JWTClaimNames().subtype(explicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('permittedValues',
        JWTClaimPermittedValuesList().subtype(explicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 1)))
)

JWTClaimConstraints.subtypeSpec = constraint.ConstraintsUnion(
    constraint.WithComponentsConstraint(
        ('mustInclude', constraint.ComponentPresentConstraint())),
    constraint.WithComponentsConstraint(
        ('permittedValues', constraint.ComponentPresentConstraint()))
)


id_pe_JWTClaimConstraints = _OID(1, 3, 6, 1, 5, 5, 7, 1, 27)


class ServiceProviderCode(char.IA5String):
    pass


class TelephoneNumber(char.IA5String):
    pass

TelephoneNumber.subtypeSpec = constraint.ConstraintsIntersection(
    constraint.ValueSizeConstraint(1, 15),
    constraint.PermittedAlphabetConstraint(
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '#', '*')
)


class TelephoneNumberRange(univ.Sequence):
    pass

TelephoneNumberRange.componentType = namedtype.NamedTypes(
    namedtype.NamedType('start', TelephoneNumber()),
    namedtype.NamedType('count',
        univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(2, MAX)))
)


class TNEntry(univ.Choice):
    pass

TNEntry.componentType = namedtype.NamedTypes(
    namedtype.NamedType('spc',
        ServiceProviderCode().subtype(explicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 0))),
    namedtype.NamedType('range',
        TelephoneNumberRange().subtype(explicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatConstructed, 1))),
    namedtype.NamedType('one',
        TelephoneNumber().subtype(explicitTag=tag.Tag(tag.tagClassContext,
            tag.tagFormatSimple, 2)))
)


class TNAuthorizationList(univ.SequenceOf):
    pass

TNAuthorizationList.componentType = TNEntry()
TNAuthorizationList.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_pe_TNAuthList = _OID(1, 3, 6, 1, 5, 5, 7, 1, 26)


id_ad_stirTNList = _OID(1, 3, 6, 1, 5, 5, 7, 48, 14)


# Map of Certificate Extension OIDs to Extensions added to the
# ones that are in rfc5280.py

_certificateExtensionsMapUpdate = {
    id_pe_TNAuthList: TNAuthorizationList(),
    id_pe_JWTClaimConstraints: JWTClaimConstraints(),
}

rfc5280.certificateExtensionsMap.update(_certificateExtensionsMapUpdate)

# === NexusCore/openenv\Lib\site-packages\rich\repr.py ===
import inspect
from functools import partial
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")


Result = Iterable[Union[Any, Tuple[Any], Tuple[str, Any], Tuple[str, Any, Any]]]
RichReprResult = Result


class ReprError(Exception):
    """An error occurred when attempting to build a repr."""


@overload
def auto(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def auto(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def auto(
    cls: Optional[Type[T]] = None, *, angular: Optional[bool] = None
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """Class decorator to create __repr__ from __rich_repr__"""

    def do_replace(cls: Type[T], angular: Optional[bool] = None) -> Type[T]:
        def auto_repr(self: T) -> str:
            """Create repr string from __rich_repr__"""
            repr_str: List[str] = []
            append = repr_str.append

            angular: bool = getattr(self.__rich_repr__, "angular", False)  # type: ignore[attr-defined]
            for arg in self.__rich_repr__():  # type: ignore[attr-defined]
                if isinstance(arg, tuple):
                    if len(arg) == 1:
                        append(repr(arg[0]))
                    else:
                        key, value, *default = arg
                        if key is None:
                            append(repr(value))
                        else:
                            if default and default[0] == value:
                                continue
                            append(f"{key}={value!r}")
                else:
                    append(repr(arg))
            if angular:
                return f"<{self.__class__.__name__} {' '.join(repr_str)}>"
            else:
                return f"{self.__class__.__name__}({', '.join(repr_str)})"

        def auto_rich_repr(self: Type[T]) -> Result:
            """Auto generate __rich_rep__ from signature of __init__"""
            try:
                signature = inspect.signature(self.__init__)
                for name, param in signature.parameters.items():
                    if param.kind == param.POSITIONAL_ONLY:
                        yield getattr(self, name)
                    elif param.kind in (
                        param.POSITIONAL_OR_KEYWORD,
                        param.KEYWORD_ONLY,
                    ):
                        if param.default is param.empty:
                            yield getattr(self, param.name)
                        else:
                            yield param.name, getattr(self, param.name), param.default
            except Exception as error:
                raise ReprError(
                    f"Failed to auto generate __rich_repr__; {error}"
                ) from None

        if not hasattr(cls, "__rich_repr__"):
            auto_rich_repr.__doc__ = "Build a rich repr"
            cls.__rich_repr__ = auto_rich_repr  # type: ignore[attr-defined]

        auto_repr.__doc__ = "Return repr(self)"
        cls.__repr__ = auto_repr  # type: ignore[assignment]
        if angular is not None:
            cls.__rich_repr__.angular = angular  # type: ignore[attr-defined]
        return cls

    if cls is None:
        return partial(do_replace, angular=angular)
    else:
        return do_replace(cls, angular=angular)


@overload
def rich_repr(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def rich_repr(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def rich_repr(
    cls: Optional[Type[T]] = None, *, angular: bool = False
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    if cls is None:
        return auto(angular=angular)
    else:
        return auto(cls)


if __name__ == "__main__":

    @auto
    class Foo:
        def __rich_repr__(self) -> Result:
            yield "foo"
            yield "bar", {"shopping": ["eggs", "ham", "pineapple"]}
            yield "buy", "hand sanitizer"

    foo = Foo()
    from rich.console import Console

    console = Console()

    console.rule("Standard repr")
    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

    console.rule("Angular repr")
    Foo.__rich_repr__.angular = True  # type: ignore[attr-defined]

    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

# === NexusCore/openenv\Lib\site-packages\typer\completion.py ===
import os
import sys
from typing import Any, MutableMapping, Tuple

import click

from ._completion_classes import completion_init
from ._completion_shared import Shells, get_completion_script, install
from .models import ParamMeta
from .params import Option
from .utils import get_params_from_function

try:
    import shellingham
except ImportError:  # pragma: no cover
    shellingham = None


_click_patched = False


def get_completion_inspect_parameters() -> Tuple[ParamMeta, ParamMeta]:
    completion_init()
    test_disable_detection = os.getenv("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION")
    if shellingham and not test_disable_detection:
        parameters = get_params_from_function(_install_completion_placeholder_function)
    else:
        parameters = get_params_from_function(
            _install_completion_no_auto_placeholder_function
        )
    install_param, show_param = parameters.values()
    return install_param, show_param


def install_callback(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    if not value or ctx.resilient_parsing:
        return value  # pragma: no cover
    if isinstance(value, str):
        shell, path = install(shell=value)
    else:
        shell, path = install()
    click.secho(f"{shell} completion installed in {path}", fg="green")
    click.echo("Completion will take effect once you restart the terminal")
    sys.exit(0)


def show_callback(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    if not value or ctx.resilient_parsing:
        return value  # pragma: no cover
    prog_name = ctx.find_root().info_name
    assert prog_name
    complete_var = "_{}_COMPLETE".format(prog_name.replace("-", "_").upper())
    shell = ""
    test_disable_detection = os.getenv("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION")
    if isinstance(value, str):
        shell = value
    elif shellingham and not test_disable_detection:
        shell, _ = shellingham.detect_shell()
    script_content = get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    click.echo(script_content)
    sys.exit(0)


# Create a fake command function to extract the completion parameters
def _install_completion_placeholder_function(
    install_completion: bool = Option(
        None,
        "--install-completion",
        is_flag=True,
        callback=install_callback,
        expose_value=False,
        help="Install completion for the current shell.",
    ),
    show_completion: bool = Option(
        None,
        "--show-completion",
        is_flag=True,
        callback=show_callback,
        expose_value=False,
        help="Show completion for the current shell, to copy it or customize the installation.",
    ),
) -> Any:
    pass  # pragma: no cover


def _install_completion_no_auto_placeholder_function(
    install_completion: Shells = Option(
        None,
        callback=install_callback,
        expose_value=False,
        help="Install completion for the specified shell.",
    ),
    show_completion: Shells = Option(
        None,
        callback=show_callback,
        expose_value=False,
        help="Show completion for the specified shell, to copy it or customize the installation.",
    ),
) -> Any:
    pass  # pragma: no cover


# Re-implement Click's shell_complete to add error message with:
# Invalid completion instruction
# To use 7.x instruction style for compatibility
# And to add extra error messages, for compatibility with Typer in previous versions
# This is only called in new Command method, only used by Click 8.x+
def shell_complete(
    cli: click.Command,
    ctx_args: MutableMapping[str, Any],
    prog_name: str,
    complete_var: str,
    instruction: str,
) -> int:
    import click
    import click.shell_completion

    if "_" not in instruction:
        click.echo("Invalid completion instruction.", err=True)
        return 1

    # Click 8 changed the order/style of shell instructions from e.g.
    # source_bash to bash_source
    # Typer override to preserve the old style for compatibility
    # Original in Click 8.x commented:
    # shell, _, instruction = instruction.partition("_")
    instruction, _, shell = instruction.partition("_")
    # Typer override end

    comp_cls = click.shell_completion.get_completion_class(shell)

    if comp_cls is None:
        click.echo(f"Shell {shell} not supported.", err=True)
        return 1

    comp = comp_cls(cli, ctx_args, prog_name, complete_var)

    if instruction == "source":
        click.echo(comp.source())
        return 0

    if instruction == "complete":
        click.echo(comp.complete())
        return 0

    click.echo(f'Completion instruction "{instruction}" not supported.', err=True)
    return 1

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\stat.py ===
"""Extra methods for DesignSpaceDocument to generate its STAT table data."""

from __future__ import annotations

from typing import Dict, List, Union

import fontTools.otlLib.builder
from fontTools.designspaceLib import (
    AxisLabelDescriptor,
    DesignSpaceDocument,
    DesignSpaceDocumentError,
    LocationLabelDescriptor,
)
from fontTools.designspaceLib.types import Region, getVFUserRegion, locationInRegion
from fontTools.ttLib import TTFont


def buildVFStatTable(ttFont: TTFont, doc: DesignSpaceDocument, vfName: str) -> None:
    """Build the STAT table for the variable font identified by its name in
    the given document.

    Knowing which variable we're building STAT data for is needed to subset
    the STAT locations to only include what the variable font actually ships.

    .. versionadded:: 5.0

    .. seealso::
        - :func:`getStatAxes()`
        - :func:`getStatLocations()`
        - :func:`fontTools.otlLib.builder.buildStatTable()`
    """
    for vf in doc.getVariableFonts():
        if vf.name == vfName:
            break
    else:
        raise DesignSpaceDocumentError(
            f"Cannot find the variable font by name {vfName}"
        )

    region = getVFUserRegion(doc, vf)

    # if there are not currently any mac names don't add them here, that's inconsistent
    # https://github.com/fonttools/fonttools/issues/683
    macNames = any(
        nr.platformID == 1 for nr in getattr(ttFont.get("name"), "names", ())
    )

    return fontTools.otlLib.builder.buildStatTable(
        ttFont,
        getStatAxes(doc, region),
        getStatLocations(doc, region),
        doc.elidedFallbackName if doc.elidedFallbackName is not None else 2,
        macNames=macNames,
    )


def getStatAxes(doc: DesignSpaceDocument, userRegion: Region) -> List[Dict]:
    """Return a list of axis dicts suitable for use as the ``axes``
    argument to :func:`fontTools.otlLib.builder.buildStatTable()`.

    .. versionadded:: 5.0
    """
    # First, get the axis labels with explicit ordering
    # then append the others in the order they appear.
    maxOrdering = max(
        (axis.axisOrdering for axis in doc.axes if axis.axisOrdering is not None),
        default=-1,
    )
    axisOrderings = []
    for axis in doc.axes:
        if axis.axisOrdering is not None:
            axisOrderings.append(axis.axisOrdering)
        else:
            maxOrdering += 1
            axisOrderings.append(maxOrdering)
    return [
        dict(
            tag=axis.tag,
            name={"en": axis.name, **axis.labelNames},
            ordering=ordering,
            values=[
                _axisLabelToStatLocation(label)
                for label in axis.axisLabels
                if locationInRegion({axis.name: label.userValue}, userRegion)
            ],
        )
        for axis, ordering in zip(doc.axes, axisOrderings)
    ]


def getStatLocations(doc: DesignSpaceDocument, userRegion: Region) -> List[Dict]:
    """Return a list of location dicts suitable for use as the ``locations``
    argument to :func:`fontTools.otlLib.builder.buildStatTable()`.

    .. versionadded:: 5.0
    """
    axesByName = {axis.name: axis for axis in doc.axes}
    return [
        dict(
            name={"en": label.name, **label.labelNames},
            # Location in the designspace is keyed by axis name
            # Location in buildStatTable by axis tag
            location={
                axesByName[name].tag: value
                for name, value in label.getFullUserLocation(doc).items()
            },
            flags=_labelToFlags(label),
        )
        for label in doc.locationLabels
        if locationInRegion(label.getFullUserLocation(doc), userRegion)
    ]


def _labelToFlags(label: Union[AxisLabelDescriptor, LocationLabelDescriptor]) -> int:
    flags = 0
    if label.olderSibling:
        flags |= 1
    if label.elidable:
        flags |= 2
    return flags


def _axisLabelToStatLocation(
    label: AxisLabelDescriptor,
) -> Dict:
    label_format = label.getFormat()
    name = {"en": label.name, **label.labelNames}
    flags = _labelToFlags(label)
    if label_format == 1:
        return dict(name=name, value=label.userValue, flags=flags)
    if label_format == 3:
        return dict(
            name=name,
            value=label.userValue,
            linkedValue=label.linkedUserValue,
            flags=flags,
        )
    if label_format == 2:
        res = dict(
            name=name,
            nominalValue=label.userValue,
            flags=flags,
        )
        if label.userMinimum is not None:
            res["rangeMinValue"] = label.userMinimum
        if label.userMaximum is not None:
            res["rangeMaxValue"] = label.userMaximum
        return res
    raise NotImplementedError("Unknown STAT label format")

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\F__e_a_t.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import floatToFixedToStr
from fontTools.misc.textTools import safeEval
from . import DefaultTable
from . import grUtils
import struct

Feat_hdr_format = """
    >
    version:    16.16F
"""


class table_F__e_a_t(DefaultTable.DefaultTable):
    """Feature table

    The ``Feat`` table is used exclusively by the Graphite shaping engine
    to store features and possible settings specified in GDL. Graphite features
    determine what rules are applied to transform a glyph stream.

    Not to be confused with ``feat``, or the OpenType Layout tables
    ``GSUB``/``GPOS``.

    See also https://graphite.sil.org/graphite_techAbout#graphite-font-tables
    """

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.features = {}

    def decompile(self, data, ttFont):
        (_, data) = sstruct.unpack2(Feat_hdr_format, data, self)
        self.version = float(floatToFixedToStr(self.version, precisionBits=16))
        (numFeats,) = struct.unpack(">H", data[:2])
        data = data[8:]
        allfeats = []
        maxsetting = 0
        for i in range(numFeats):
            if self.version >= 2.0:
                (fid, nums, _, offset, flags, lid) = struct.unpack(
                    ">LHHLHH", data[16 * i : 16 * (i + 1)]
                )
                offset = int((offset - 12 - 16 * numFeats) / 4)
            else:
                (fid, nums, offset, flags, lid) = struct.unpack(
                    ">HHLHH", data[12 * i : 12 * (i + 1)]
                )
                offset = int((offset - 12 - 12 * numFeats) / 4)
            allfeats.append((fid, nums, offset, flags, lid))
            maxsetting = max(maxsetting, offset + nums)
        data = data[16 * numFeats :]
        allsettings = []
        for i in range(maxsetting):
            if len(data) >= 4 * (i + 1):
                (val, lid) = struct.unpack(">HH", data[4 * i : 4 * (i + 1)])
                allsettings.append((val, lid))
        for i, f in enumerate(allfeats):
            (fid, nums, offset, flags, lid) = f
            fobj = Feature()
            fobj.flags = flags
            fobj.label = lid
            self.features[grUtils.num2tag(fid)] = fobj
            fobj.settings = {}
            fobj.default = None
            fobj.index = i
            for i in range(offset, offset + nums):
                if i >= len(allsettings):
                    continue
                (vid, vlid) = allsettings[i]
                fobj.settings[vid] = vlid
                if fobj.default is None:
                    fobj.default = vid

    def compile(self, ttFont):
        fdat = b""
        vdat = b""
        offset = 0
        for f, v in sorted(self.features.items(), key=lambda x: x[1].index):
            fnum = grUtils.tag2num(f)
            if self.version >= 2.0:
                fdat += struct.pack(
                    ">LHHLHH",
                    grUtils.tag2num(f),
                    len(v.settings),
                    0,
                    offset * 4 + 12 + 16 * len(self.features),
                    v.flags,
                    v.label,
                )
            elif fnum > 65535:  # self healing for alphabetic ids
                self.version = 2.0
                return self.compile(ttFont)
            else:
                fdat += struct.pack(
                    ">HHLHH",
                    grUtils.tag2num(f),
                    len(v.settings),
                    offset * 4 + 12 + 12 * len(self.features),
                    v.flags,
                    v.label,
                )
            for s, l in sorted(
                v.settings.items(), key=lambda x: (-1, x[1]) if x[0] == v.default else x
            ):
                vdat += struct.pack(">HH", s, l)
            offset += len(v.settings)
        hdr = sstruct.pack(Feat_hdr_format, self)
        return hdr + struct.pack(">HHL", len(self.features), 0, 0) + fdat + vdat

    def toXML(self, writer, ttFont):
        writer.simpletag("version", version=self.version)
        writer.newline()
        for f, v in sorted(self.features.items(), key=lambda x: x[1].index):
            writer.begintag(
                "feature",
                fid=f,
                label=v.label,
                flags=v.flags,
                default=(v.default if v.default else 0),
            )
            writer.newline()
            for s, l in sorted(v.settings.items()):
                writer.simpletag("setting", value=s, label=l)
                writer.newline()
            writer.endtag("feature")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = float(safeEval(attrs["version"]))
        elif name == "feature":
            fid = attrs["fid"]
            fobj = Feature()
            fobj.flags = int(safeEval(attrs["flags"]))
            fobj.label = int(safeEval(attrs["label"]))
            fobj.default = int(safeEval(attrs.get("default", "0")))
            fobj.index = len(self.features)
            self.features[fid] = fobj
            fobj.settings = {}
            for element in content:
                if not isinstance(element, tuple):
                    continue
                tag, a, c = element
                if tag == "setting":
                    fobj.settings[int(safeEval(a["value"]))] = int(safeEval(a["label"]))


class Feature(object):
    pass

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\sbixGlyph.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import readHex, safeEval
import struct


sbixGlyphHeaderFormat = """
	>
	originOffsetX: h	# The x-value of the point in the glyph relative to its
						# lower-left corner which corresponds to the origin of
						# the glyph on the screen, that is the point on the
						# baseline at the left edge of the glyph.
	originOffsetY: h	# The y-value of the point in the glyph relative to its
						# lower-left corner which corresponds to the origin of
						# the glyph on the screen, that is the point on the
						# baseline at the left edge of the glyph.
	graphicType:  4s	# e.g. "png "
"""

sbixGlyphHeaderFormatSize = sstruct.calcsize(sbixGlyphHeaderFormat)


class Glyph(object):
    def __init__(
        self,
        glyphName=None,
        referenceGlyphName=None,
        originOffsetX=0,
        originOffsetY=0,
        graphicType=None,
        imageData=None,
        rawdata=None,
        gid=0,
    ):
        self.gid = gid
        self.glyphName = glyphName
        self.referenceGlyphName = referenceGlyphName
        self.originOffsetX = originOffsetX
        self.originOffsetY = originOffsetY
        self.rawdata = rawdata
        self.graphicType = graphicType
        self.imageData = imageData

        # fix self.graphicType if it is null terminated or too short
        if self.graphicType is not None:
            if self.graphicType[-1] == "\0":
                self.graphicType = self.graphicType[:-1]
            if len(self.graphicType) > 4:
                from fontTools import ttLib

                raise ttLib.TTLibError(
                    "Glyph.graphicType must not be longer than 4 characters."
                )
            elif len(self.graphicType) < 4:
                # pad with spaces
                self.graphicType += "    "[: (4 - len(self.graphicType))]

    def is_reference_type(self):
        """Returns True if this glyph is a reference to another glyph's image data."""
        return self.graphicType == "dupe" or self.graphicType == "flip"

    def decompile(self, ttFont):
        self.glyphName = ttFont.getGlyphName(self.gid)
        if self.rawdata is None:
            from fontTools import ttLib

            raise ttLib.TTLibError("No table data to decompile")
        if len(self.rawdata) > 0:
            if len(self.rawdata) < sbixGlyphHeaderFormatSize:
                from fontTools import ttLib

                # print "Glyph %i header too short: Expected %x, got %x." % (self.gid, sbixGlyphHeaderFormatSize, len(self.rawdata))
                raise ttLib.TTLibError("Glyph header too short.")

            sstruct.unpack(
                sbixGlyphHeaderFormat, self.rawdata[:sbixGlyphHeaderFormatSize], self
            )

            if self.is_reference_type():
                # this glyph is a reference to another glyph's image data
                (gid,) = struct.unpack(">H", self.rawdata[sbixGlyphHeaderFormatSize:])
                self.referenceGlyphName = ttFont.getGlyphName(gid)
            else:
                self.imageData = self.rawdata[sbixGlyphHeaderFormatSize:]
                self.referenceGlyphName = None
        # clean up
        del self.rawdata
        del self.gid

    def compile(self, ttFont):
        if self.glyphName is None:
            from fontTools import ttLib

            raise ttLib.TTLibError("Can't compile Glyph without glyph name")
            # TODO: if ttFont has no maxp, cmap etc., ignore glyph names and compile by index?
            # (needed if you just want to compile the sbix table on its own)
        self.gid = struct.pack(">H", ttFont.getGlyphID(self.glyphName))
        if self.graphicType is None:
            rawdata = b""
        else:
            rawdata = sstruct.pack(sbixGlyphHeaderFormat, self)
            if self.is_reference_type():
                rawdata += struct.pack(">H", ttFont.getGlyphID(self.referenceGlyphName))
            else:
                assert self.imageData is not None
                rawdata += self.imageData
        self.rawdata = rawdata

    def toXML(self, xmlWriter, ttFont):
        if self.graphicType is None:
            # TODO: ignore empty glyphs?
            # a glyph data entry is required for each glyph,
            # but empty ones can be calculated at compile time
            xmlWriter.simpletag("glyph", name=self.glyphName)
            xmlWriter.newline()
            return
        xmlWriter.begintag(
            "glyph",
            graphicType=self.graphicType,
            name=self.glyphName,
            originOffsetX=self.originOffsetX,
            originOffsetY=self.originOffsetY,
        )
        xmlWriter.newline()
        if self.is_reference_type():
            # this glyph is a reference to another glyph id.
            xmlWriter.simpletag("ref", glyphname=self.referenceGlyphName)
        else:
            xmlWriter.begintag("hexdata")
            xmlWriter.newline()
            xmlWriter.dumphex(self.imageData)
            xmlWriter.endtag("hexdata")
        xmlWriter.newline()
        xmlWriter.endtag("glyph")
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "ref":
            # this glyph i.e. a reference to another glyph's image data.
            # in this case imageData contains the glyph id of the reference glyph
            # get glyph id from glyphname
            glyphname = safeEval("'''" + attrs["glyphname"] + "'''")
            self.imageData = struct.pack(">H", ttFont.getGlyphID(glyphname))
            self.referenceGlyphName = glyphname
        elif name == "hexdata":
            self.imageData = readHex(content)
        else:
            from fontTools import ttLib

            raise ttLib.TTLibError("can't handle '%s' element" % name)

# === NexusCore/openenv\Lib\site-packages\httpx\_transports\wsgi.py ===
from __future__ import annotations

import io
import itertools
import sys
import typing

from .._models import Request, Response
from .._types import SyncByteStream
from .base import BaseTransport

if typing.TYPE_CHECKING:
    from _typeshed import OptExcInfo  # pragma: no cover
    from _typeshed.wsgi import WSGIApplication  # pragma: no cover

_T = typing.TypeVar("_T")


__all__ = ["WSGITransport"]


def _skip_leading_empty_chunks(body: typing.Iterable[_T]) -> typing.Iterable[_T]:
    body = iter(body)
    for chunk in body:
        if chunk:
            return itertools.chain([chunk], body)
    return []


class WSGIByteStream(SyncByteStream):
    def __init__(self, result: typing.Iterable[bytes]) -> None:
        self._close = getattr(result, "close", None)
        self._result = _skip_leading_empty_chunks(result)

    def __iter__(self) -> typing.Iterator[bytes]:
        for part in self._result:
            yield part

    def close(self) -> None:
        if self._close is not None:
            self._close()


class WSGITransport(BaseTransport):
    """
    A custom transport that handles sending requests directly to an WSGI app.
    The simplest way to use this functionality is to use the `app` argument.

    ```
    client = httpx.Client(app=app)
    ```

    Alternatively, you can setup the transport instance explicitly.
    This allows you to include any additional configuration arguments specific
    to the WSGITransport class:

    ```
    transport = httpx.WSGITransport(
        app=app,
        script_name="/submount",
        remote_addr="1.2.3.4"
    )
    client = httpx.Client(transport=transport)
    ```

    Arguments:

    * `app` - The WSGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `script_name` - The root path on which the WSGI application should be mounted.
    * `remote_addr` - A string indicating the client IP of incoming requests.
    ```
    """

    def __init__(
        self,
        app: WSGIApplication,
        raise_app_exceptions: bool = True,
        script_name: str = "",
        remote_addr: str = "127.0.0.1",
        wsgi_errors: typing.TextIO | None = None,
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.script_name = script_name
        self.remote_addr = remote_addr
        self.wsgi_errors = wsgi_errors

    def handle_request(self, request: Request) -> Response:
        request.read()
        wsgi_input = io.BytesIO(request.content)

        port = request.url.port or {"http": 80, "https": 443}[request.url.scheme]
        environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.url.scheme,
            "wsgi.input": wsgi_input,
            "wsgi.errors": self.wsgi_errors or sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": self.script_name,
            "PATH_INFO": request.url.path,
            "QUERY_STRING": request.url.query.decode("ascii"),
            "SERVER_NAME": request.url.host,
            "SERVER_PORT": str(port),
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": self.remote_addr,
        }
        for header_key, header_value in request.headers.raw:
            key = header_key.decode("ascii").upper().replace("-", "_")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = "HTTP_" + key
            environ[key] = header_value.decode("ascii")

        seen_status = None
        seen_response_headers = None
        seen_exc_info = None

        def start_response(
            status: str,
            response_headers: list[tuple[str, str]],
            exc_info: OptExcInfo | None = None,
        ) -> typing.Callable[[bytes], typing.Any]:
            nonlocal seen_status, seen_response_headers, seen_exc_info
            seen_status = status
            seen_response_headers = response_headers
            seen_exc_info = exc_info
            return lambda _: None

        result = self.app(environ, start_response)

        stream = WSGIByteStream(result)

        assert seen_status is not None
        assert seen_response_headers is not None
        if seen_exc_info and seen_exc_info[0] and self.raise_app_exceptions:
            raise seen_exc_info[1]

        status_code = int(seen_status.split()[0])
        headers = [
            (key.encode("ascii"), value.encode("ascii"))
            for key, value in seen_response_headers
        ]

        return Response(status_code, headers=headers, stream=stream)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\petals\completion\handler.py ===
import time
from typing import Callable, Optional, Union

import litellm
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
)
from litellm.utils import ModelResponse, Usage

from ..common_utils import PetalsError


def completion(
    model: str,
    messages: list,
    api_base: Optional[str],
    model_response: ModelResponse,
    print_verbose: Callable,
    encoding,
    logging_obj,
    optional_params: dict,
    stream=False,
    litellm_params=None,
    logger_fn=None,
    client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
):
    ## Load Config
    config = litellm.PetalsConfig.get_config()
    for k, v in config.items():
        if (
            k not in optional_params
        ):  # completion(top_k=3) > petals_config(top_k=3) <- allows for dynamic variables to be passed in
            optional_params[k] = v

    if model in litellm.custom_prompt_dict:
        # check if the model has a registered custom prompt
        model_prompt_details = litellm.custom_prompt_dict[model]
        prompt = custom_prompt(
            role_dict=model_prompt_details["roles"],
            initial_prompt_value=model_prompt_details["initial_prompt_value"],
            final_prompt_value=model_prompt_details["final_prompt_value"],
            messages=messages,
        )
    else:
        prompt = prompt_factory(model=model, messages=messages)

    output_text: Optional[str] = None
    if api_base:
        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": optional_params,
                "api_base": api_base,
            },
        )
        data = {"model": model, "inputs": prompt, **optional_params}

        ## COMPLETION CALL
        if client is None or not isinstance(client, HTTPHandler):
            client = _get_httpx_client()
        response = client.post(api_base, data=data)

        ## LOGGING
        logging_obj.post_call(
            input=prompt,
            api_key="",
            original_response=response.text,
            additional_args={"complete_input_dict": optional_params},
        )

        ## RESPONSE OBJECT
        try:
            output_text = response.json()["outputs"]
        except Exception as e:
            PetalsError(
                status_code=response.status_code,
                message=str(e),
                headers=response.headers,
            )

    else:
        try:
            from petals import AutoDistributedModelForCausalLM  # type: ignore
            from transformers import AutoTokenizer
        except Exception:
            raise Exception(
                "Importing torch, transformers, petals failed\nTry pip installing petals \npip install git+https://github.com/bigscience-workshop/petals"
            )

        model = model

        tokenizer = AutoTokenizer.from_pretrained(
            model, use_fast=False, add_bos_token=False
        )
        model_obj = AutoDistributedModelForCausalLM.from_pretrained(model)

        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={"complete_input_dict": optional_params},
        )

        ## COMPLETION CALL
        inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]

        # optional params: max_new_tokens=1,temperature=0.9, top_p=0.6
        outputs = model_obj.generate(inputs, **optional_params)

        ## LOGGING
        logging_obj.post_call(
            input=prompt,
            api_key="",
            original_response=outputs,
            additional_args={"complete_input_dict": optional_params},
        )
        ## RESPONSE OBJECT
        output_text = tokenizer.decode(outputs[0])

    if output_text is not None and len(output_text) > 0:
        model_response.choices[0].message.content = output_text  # type: ignore

    prompt_tokens = len(encoding.encode(prompt))
    completion_tokens = len(
        encoding.encode(model_response["choices"][0]["message"].get("content"))
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

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\batch_redis_get.py ===
# What this does?
## Gets a key's redis cache, and store it in memory for 1 minute.
## This reduces the number of REDIS GET requests made during high-traffic by the proxy.
### [BETA] this is in Beta. And might change.

import traceback
from typing import Literal, Optional

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache, InMemoryCache, RedisCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth


class _PROXY_BatchRedisRequests(CustomLogger):
    # Class variables or attributes
    in_memory_cache: Optional[InMemoryCache] = None

    def __init__(self):
        if litellm.cache is not None:
            litellm.cache.async_get_cache = (
                self.async_get_cache
            )  # map the litellm 'get_cache' function to our custom function

    def print_verbose(
        self, print_statement, debug_level: Literal["INFO", "DEBUG"] = "DEBUG"
    ):
        if debug_level == "DEBUG":
            verbose_proxy_logger.debug(print_statement)
        elif debug_level == "INFO":
            verbose_proxy_logger.debug(print_statement)
        if litellm.set_verbose is True:
            print(print_statement)  # noqa

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        try:
            """
            Get the user key

            Check if a key starting with `litellm:<api_key>:<call_type:` exists in-memory

            If no, then get relevant cache from redis
            """
            api_key = user_api_key_dict.api_key

            cache_key_name = f"litellm:{api_key}:{call_type}"
            self.in_memory_cache = cache.in_memory_cache

            key_value_dict = {}
            in_memory_cache_exists = False
            for key in cache.in_memory_cache.cache_dict.keys():
                if isinstance(key, str) and key.startswith(cache_key_name):
                    in_memory_cache_exists = True

            if in_memory_cache_exists is False and litellm.cache is not None:
                """
                - Check if `litellm.Cache` is redis
                - Get the relevant values
                """
                if litellm.cache.type is not None and isinstance(
                    litellm.cache.cache, RedisCache
                ):
                    # Initialize an empty list to store the keys
                    keys = []
                    self.print_verbose(f"cache_key_name: {cache_key_name}")
                    # Use the SCAN iterator to fetch keys matching the pattern
                    keys = await litellm.cache.cache.async_scan_iter(
                        pattern=cache_key_name, count=100
                    )
                    # If you need the truly "last" based on time or another criteria,
                    # ensure your key naming or storage strategy allows this determination
                    # Here you would sort or filter the keys as needed based on your strategy
                    self.print_verbose(f"redis keys: {keys}")
                    if len(keys) > 0:
                        key_value_dict = (
                            await litellm.cache.cache.async_batch_get_cache(
                                key_list=keys
                            )
                        )

            ## Add to cache
            if len(key_value_dict.items()) > 0:
                await cache.in_memory_cache.async_set_cache_pipeline(
                    cache_list=list(key_value_dict.items()), ttl=60
                )
            ## Set cache namespace if it's a miss
            data["metadata"]["redis_namespace"] = cache_key_name
        except HTTPException as e:
            raise e
        except Exception as e:
            verbose_proxy_logger.error(
                "litellm.proxy.hooks.batch_redis_get.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            verbose_proxy_logger.debug(traceback.format_exc())

    async def async_get_cache(self, *args, **kwargs):
        """
        - Check if the cache key is in-memory

        - Else:
            - add missing cache key from REDIS
            - update in-memory cache
            - return redis cache request
        """
        try:  # never block execution
            cache_key: Optional[str] = None
            if "cache_key" in kwargs:
                cache_key = kwargs["cache_key"]
            elif litellm.cache is not None:
                cache_key = litellm.cache.get_cache_key(
                    *args, **kwargs
                )  # returns "<cache_key_name>:<hash>" - we pass redis_namespace in async_pre_call_hook. Done to avoid rewriting the async_set_cache logic

            if (
                cache_key is not None
                and self.in_memory_cache is not None
                and litellm.cache is not None
            ):
                cache_control_args = kwargs.get("cache", {})
                max_age = cache_control_args.get(
                    "s-max-age", cache_control_args.get("s-maxage", float("inf"))
                )
                cached_result = self.in_memory_cache.get_cache(
                    cache_key, *args, **kwargs
                )
                if cached_result is None:
                    cached_result = await litellm.cache.cache.async_get_cache(
                        cache_key, *args, **kwargs
                    )
                    if cached_result is not None:
                        await self.in_memory_cache.async_set_cache(
                            cache_key, cached_result, ttl=60
                        )
                return litellm.cache._get_cache_logic(
                    cached_result=cached_result, max_age=max_age
                )
        except Exception:
            return None

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_transaction_queue\daily_spend_update_queue.py ===
import asyncio
from copy import deepcopy
from typing import Dict, List, Optional

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import BaseDailySpendTransaction
from litellm.proxy.db.db_transaction_queue.base_update_queue import (
    BaseUpdateQueue,
    service_logger_obj,
)
from litellm.types.services import ServiceTypes


class DailySpendUpdateQueue(BaseUpdateQueue):
    """
    In memory buffer for daily spend updates that should be committed to the database

    To add a new daily spend update transaction, use the following format:
        daily_spend_update_queue.add_update({
            "user1_date_api_key_model_custom_llm_provider": {
                "spend": 10,
                "prompt_tokens": 100,
                "completion_tokens": 100,
            }
        })

    Queue contains a list of daily spend update transactions

    eg
        queue = [
            {
                "user1_date_api_key_model_custom_llm_provider": {
                    "spend": 10,
                    "prompt_tokens": 100,
                    "completion_tokens": 100,
                    "api_requests": 100,
                    "successful_requests": 100,
                    "failed_requests": 100,
                }
            },
            {
                "user2_date_api_key_model_custom_llm_provider": {
                    "spend": 10,
                    "prompt_tokens": 100,
                    "completion_tokens": 100,
                    "api_requests": 100,
                    "successful_requests": 100,
                    "failed_requests": 100,
                }
            }
        ]
    """

    def __init__(self):
        super().__init__()
        self.update_queue: asyncio.Queue[Dict[str, BaseDailySpendTransaction]] = (
            asyncio.Queue()
        )

    async def add_update(self, update: Dict[str, BaseDailySpendTransaction]):
        """Enqueue an update."""
        verbose_proxy_logger.debug("Adding update to queue: %s", update)
        await self.update_queue.put(update)
        if self.update_queue.qsize() >= self.MAX_SIZE_IN_MEMORY_QUEUE:
            verbose_proxy_logger.warning(
                "Spend update queue is full. Aggregating all entries in queue to concatenate entries."
            )
            await self.aggregate_queue_updates()

    async def aggregate_queue_updates(self):
        """
        Combine all updates in the queue into a single update.
        This is used to reduce the size of the in-memory queue.
        """
        updates: List[Dict[str, BaseDailySpendTransaction]] = (
            await self.flush_all_updates_from_in_memory_queue()
        )
        aggregated_updates = self.get_aggregated_daily_spend_update_transactions(
            updates
        )
        await self.update_queue.put(aggregated_updates)

    async def flush_and_get_aggregated_daily_spend_update_transactions(
        self,
    ) -> Dict[str, BaseDailySpendTransaction]:
        """Get all updates from the queue and return all updates aggregated by daily_transaction_key. Works for both user and team spend updates."""
        updates = await self.flush_all_updates_from_in_memory_queue()
        aggregated_daily_spend_update_transactions = (
            DailySpendUpdateQueue.get_aggregated_daily_spend_update_transactions(
                updates
            )
        )
        verbose_proxy_logger.debug(
            "Aggregated daily spend update transactions: %s",
            aggregated_daily_spend_update_transactions,
        )
        return aggregated_daily_spend_update_transactions

    @staticmethod
    def get_aggregated_daily_spend_update_transactions(
        updates: List[Dict[str, BaseDailySpendTransaction]],
    ) -> Dict[str, BaseDailySpendTransaction]:
        """Aggregate updates by daily_transaction_key."""
        aggregated_daily_spend_update_transactions: Dict[
            str, BaseDailySpendTransaction
        ] = {}
        for _update in updates:
            for _key, payload in _update.items():
                if _key in aggregated_daily_spend_update_transactions:
                    daily_transaction = aggregated_daily_spend_update_transactions[_key]
                    daily_transaction["spend"] += payload["spend"]
                    daily_transaction["prompt_tokens"] += payload["prompt_tokens"]
                    daily_transaction["completion_tokens"] += payload[
                        "completion_tokens"
                    ]
                    daily_transaction["api_requests"] += payload["api_requests"]
                    daily_transaction["successful_requests"] += payload[
                        "successful_requests"
                    ]
                    daily_transaction["failed_requests"] += payload["failed_requests"]

                    # Add optional metrics cache_read_input_tokens and cache_creation_input_tokens
                    daily_transaction["cache_read_input_tokens"] = (
                        payload.get("cache_read_input_tokens", 0) or 0
                    ) + daily_transaction.get("cache_read_input_tokens", 0)

                    daily_transaction["cache_creation_input_tokens"] = (
                        payload.get("cache_creation_input_tokens", 0) or 0
                    ) + daily_transaction.get("cache_creation_input_tokens", 0)

                else:
                    aggregated_daily_spend_update_transactions[_key] = deepcopy(payload)
        return aggregated_daily_spend_update_transactions

    async def _emit_new_item_added_to_queue_event(
        self,
        queue_size: Optional[int] = None,
    ):
        asyncio.create_task(
            service_logger_obj.async_service_success_hook(
                service=ServiceTypes.IN_MEMORY_DAILY_SPEND_UPDATE_QUEUE,
                duration=0,
                call_type="_emit_new_item_added_to_queue_event",
                event_metadata={
                    "gauge_labels": ServiceTypes.IN_MEMORY_DAILY_SPEND_UPDATE_QUEUE,
                    "gauge_value": queue_size,
                },
            )
        )

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_core\linkify.py ===
from __future__ import annotations

import re
from typing import Protocol

from ..common.utils import arrayReplaceAt, isLinkClose, isLinkOpen
from ..token import Token
from .state_core import StateCore

HTTP_RE = re.compile(r"^http://")
MAILTO_RE = re.compile(r"^mailto:")
TEST_MAILTO_RE = re.compile(r"^mailto:", flags=re.IGNORECASE)


def linkify(state: StateCore) -> None:
    """Rule for identifying plain-text links."""
    if not state.md.options.linkify:
        return

    if not state.md.linkify:
        raise ModuleNotFoundError("Linkify enabled but not installed.")

    for inline_token in state.tokens:
        if inline_token.type != "inline" or not state.md.linkify.pretest(
            inline_token.content
        ):
            continue

        tokens = inline_token.children

        htmlLinkLevel = 0

        # We scan from the end, to keep position when new tags added.
        # Use reversed logic in links start/end match
        assert tokens is not None
        i = len(tokens)
        while i >= 1:
            i -= 1
            assert isinstance(tokens, list)
            currentToken = tokens[i]

            # Skip content of markdown links
            if currentToken.type == "link_close":
                i -= 1
                while (
                    tokens[i].level != currentToken.level
                    and tokens[i].type != "link_open"
                ):
                    i -= 1
                continue

            # Skip content of html tag links
            if currentToken.type == "html_inline":
                if isLinkOpen(currentToken.content) and htmlLinkLevel > 0:
                    htmlLinkLevel -= 1
                if isLinkClose(currentToken.content):
                    htmlLinkLevel += 1
            if htmlLinkLevel > 0:
                continue

            if currentToken.type == "text" and state.md.linkify.test(
                currentToken.content
            ):
                text = currentToken.content
                links: list[_LinkType] = state.md.linkify.match(text) or []

                # Now split string to nodes
                nodes = []
                level = currentToken.level
                lastPos = 0

                # forbid escape sequence at the start of the string,
                # this avoids http\://example.com/ from being linkified as
                # http:<a href="//example.com/">//example.com/</a>
                if (
                    links
                    and links[0].index == 0
                    and i > 0
                    and tokens[i - 1].type == "text_special"
                ):
                    links = links[1:]

                for link in links:
                    url = link.url
                    fullUrl = state.md.normalizeLink(url)
                    if not state.md.validateLink(fullUrl):
                        continue

                    urlText = link.text

                    # Linkifier might send raw hostnames like "example.com", where url
                    # starts with domain name. So we prepend http:// in those cases,
                    # and remove it afterwards.
                    if not link.schema:
                        urlText = HTTP_RE.sub(
                            "", state.md.normalizeLinkText("http://" + urlText)
                        )
                    elif link.schema == "mailto:" and TEST_MAILTO_RE.search(urlText):
                        urlText = MAILTO_RE.sub(
                            "", state.md.normalizeLinkText("mailto:" + urlText)
                        )
                    else:
                        urlText = state.md.normalizeLinkText(urlText)

                    pos = link.index

                    if pos > lastPos:
                        token = Token("text", "", 0)
                        token.content = text[lastPos:pos]
                        token.level = level
                        nodes.append(token)

                    token = Token("link_open", "a", 1)
                    token.attrs = {"href": fullUrl}
                    token.level = level
                    level += 1
                    token.markup = "linkify"
                    token.info = "auto"
                    nodes.append(token)

                    token = Token("text", "", 0)
                    token.content = urlText
                    token.level = level
                    nodes.append(token)

                    token = Token("link_close", "a", -1)
                    level -= 1
                    token.level = level
                    token.markup = "linkify"
                    token.info = "auto"
                    nodes.append(token)

                    lastPos = link.last_index

                if lastPos < len(text):
                    token = Token("text", "", 0)
                    token.content = text[lastPos:]
                    token.level = level
                    nodes.append(token)

                inline_token.children = tokens = arrayReplaceAt(tokens, i, nodes)


class _LinkType(Protocol):
    url: str
    text: str
    index: int
    last_index: int
    schema: str | None

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\repp.py ===
# Natural Language Toolkit: Interface to the Repp Tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Authors: Rebecca Dridan and Stephan Oepen
# Contributors: Liling Tan
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import re
import subprocess
import sys
import tempfile

from nltk.data import ZipFilePathPointer
from nltk.internals import find_dir
from nltk.tokenize.api import TokenizerI


class ReppTokenizer(TokenizerI):
    """
    A class for word tokenization using the REPP parser described in
    Rebecca Dridan and Stephan Oepen (2012) Tokenization: Returning to a
    Long Solved Problem - A Survey, Contrastive  Experiment, Recommendations,
    and Toolkit. In ACL. http://anthology.aclweb.org/P/P12/P12-2.pdf#page=406

    >>> sents = ['Tokenization is widely regarded as a solved problem due to the high accuracy that rulebased tokenizers achieve.' ,
    ... 'But rule-based tokenizers are hard to maintain and their rules language specific.' ,
    ... 'We evaluated our method on three languages and obtained error rates of 0.27% (English), 0.35% (Dutch) and 0.76% (Italian) for our best models.'
    ... ]
    >>> tokenizer = ReppTokenizer('/home/alvas/repp/') # doctest: +SKIP
    >>> for sent in sents:                             # doctest: +SKIP
    ...     tokenizer.tokenize(sent)                   # doctest: +SKIP
    ...
    (u'Tokenization', u'is', u'widely', u'regarded', u'as', u'a', u'solved', u'problem', u'due', u'to', u'the', u'high', u'accuracy', u'that', u'rulebased', u'tokenizers', u'achieve', u'.')
    (u'But', u'rule-based', u'tokenizers', u'are', u'hard', u'to', u'maintain', u'and', u'their', u'rules', u'language', u'specific', u'.')
    (u'We', u'evaluated', u'our', u'method', u'on', u'three', u'languages', u'and', u'obtained', u'error', u'rates', u'of', u'0.27', u'%', u'(', u'English', u')', u',', u'0.35', u'%', u'(', u'Dutch', u')', u'and', u'0.76', u'%', u'(', u'Italian', u')', u'for', u'our', u'best', u'models', u'.')

    >>> for sent in tokenizer.tokenize_sents(sents): # doctest: +SKIP
    ...     print(sent)                              # doctest: +SKIP
    ...
    (u'Tokenization', u'is', u'widely', u'regarded', u'as', u'a', u'solved', u'problem', u'due', u'to', u'the', u'high', u'accuracy', u'that', u'rulebased', u'tokenizers', u'achieve', u'.')
    (u'But', u'rule-based', u'tokenizers', u'are', u'hard', u'to', u'maintain', u'and', u'their', u'rules', u'language', u'specific', u'.')
    (u'We', u'evaluated', u'our', u'method', u'on', u'three', u'languages', u'and', u'obtained', u'error', u'rates', u'of', u'0.27', u'%', u'(', u'English', u')', u',', u'0.35', u'%', u'(', u'Dutch', u')', u'and', u'0.76', u'%', u'(', u'Italian', u')', u'for', u'our', u'best', u'models', u'.')
    >>> for sent in tokenizer.tokenize_sents(sents, keep_token_positions=True): # doctest: +SKIP
    ...     print(sent)                                                         # doctest: +SKIP
    ...
    [(u'Tokenization', 0, 12), (u'is', 13, 15), (u'widely', 16, 22), (u'regarded', 23, 31), (u'as', 32, 34), (u'a', 35, 36), (u'solved', 37, 43), (u'problem', 44, 51), (u'due', 52, 55), (u'to', 56, 58), (u'the', 59, 62), (u'high', 63, 67), (u'accuracy', 68, 76), (u'that', 77, 81), (u'rulebased', 82, 91), (u'tokenizers', 92, 102), (u'achieve', 103, 110), (u'.', 110, 111)]
    [(u'But', 0, 3), (u'rule-based', 4, 14), (u'tokenizers', 15, 25), (u'are', 26, 29), (u'hard', 30, 34), (u'to', 35, 37), (u'maintain', 38, 46), (u'and', 47, 50), (u'their', 51, 56), (u'rules', 57, 62), (u'language', 63, 71), (u'specific', 72, 80), (u'.', 80, 81)]
    [(u'We', 0, 2), (u'evaluated', 3, 12), (u'our', 13, 16), (u'method', 17, 23), (u'on', 24, 26), (u'three', 27, 32), (u'languages', 33, 42), (u'and', 43, 46), (u'obtained', 47, 55), (u'error', 56, 61), (u'rates', 62, 67), (u'of', 68, 70), (u'0.27', 71, 75), (u'%', 75, 76), (u'(', 77, 78), (u'English', 78, 85), (u')', 85, 86), (u',', 86, 87), (u'0.35', 88, 92), (u'%', 92, 93), (u'(', 94, 95), (u'Dutch', 95, 100), (u')', 100, 101), (u'and', 102, 105), (u'0.76', 106, 110), (u'%', 110, 111), (u'(', 112, 113), (u'Italian', 113, 120), (u')', 120, 121), (u'for', 122, 125), (u'our', 126, 129), (u'best', 130, 134), (u'models', 135, 141), (u'.', 141, 142)]
    """

    def __init__(self, repp_dir, encoding="utf8"):
        self.repp_dir = self.find_repptokenizer(repp_dir)
        # Set a directory to store the temporary files.
        self.working_dir = tempfile.gettempdir()
        # Set an encoding for the input strings.
        self.encoding = encoding

    def tokenize(self, sentence):
        """
        Use Repp to tokenize a single sentence.

        :param sentence: A single sentence string.
        :type sentence: str
        :return: A tuple of tokens.
        :rtype: tuple(str)
        """
        return next(self.tokenize_sents([sentence]))

    def tokenize_sents(self, sentences, keep_token_positions=False):
        """
        Tokenize multiple sentences using Repp.

        :param sentences: A list of sentence strings.
        :type sentences: list(str)
        :return: A list of tuples of tokens
        :rtype: iter(tuple(str))
        """
        with tempfile.NamedTemporaryFile(
            prefix="repp_input.", dir=self.working_dir, mode="w", delete=False
        ) as input_file:
            # Write sentences to temporary input file.
            for sent in sentences:
                input_file.write(str(sent) + "\n")
            input_file.close()
            # Generate command to run REPP.
            cmd = self.generate_repp_command(input_file.name)
            # Decode the stdout and strips the ending newline.
            repp_output = self._execute(cmd).decode(self.encoding).strip()
            for tokenized_sent in self.parse_repp_outputs(repp_output):
                if not keep_token_positions:
                    # Removes token position information.
                    tokenized_sent, starts, ends = zip(*tokenized_sent)
                yield tokenized_sent

    def generate_repp_command(self, inputfilename):
        """
        This module generates the REPP command to be used at the terminal.

        :param inputfilename: path to the input file
        :type inputfilename: str
        """
        cmd = [self.repp_dir + "/src/repp"]
        cmd += ["-c", self.repp_dir + "/erg/repp.set"]
        cmd += ["--format", "triple"]
        cmd += [inputfilename]
        return cmd

    @staticmethod
    def _execute(cmd):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        return stdout

    @staticmethod
    def parse_repp_outputs(repp_output):
        """
        This module parses the tri-tuple format that REPP outputs using the
        "--format triple" option and returns an generator with tuple of string
        tokens.

        :param repp_output:
        :type repp_output: type
        :return: an iterable of the tokenized sentences as tuples of strings
        :rtype: iter(tuple)
        """
        line_regex = re.compile(r"^\((\d+), (\d+), (.+)\)$", re.MULTILINE)
        for section in repp_output.split("\n\n"):
            words_with_positions = [
                (token, int(start), int(end))
                for start, end, token in line_regex.findall(section)
            ]
            words = tuple(t[2] for t in words_with_positions)
            yield words_with_positions

    def find_repptokenizer(self, repp_dirname):
        """
        A module to find REPP tokenizer binary and its *repp.set* config file.
        """
        if os.path.exists(repp_dirname):  # If a full path is given.
            _repp_dir = repp_dirname
        else:  # Try to find path to REPP directory in environment variables.
            _repp_dir = find_dir(repp_dirname, env_vars=("REPP_TOKENIZER",))
        # Checks for the REPP binary and erg/repp.set config file.
        assert os.path.exists(_repp_dir + "/src/repp")
        assert os.path.exists(_repp_dir + "/erg/repp.set")
        return _repp_dir

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\diagnose.py ===
#!/usr/bin/env python3
import os
import sys
import tempfile


def run():
    _path = os.getcwd()
    os.chdir(tempfile.gettempdir())
    print('------')
    print(f'os.name={os.name!r}')
    print('------')
    print(f'sys.platform={sys.platform!r}')
    print('------')
    print('sys.version:')
    print(sys.version)
    print('------')
    print('sys.prefix:')
    print(sys.prefix)
    print('------')
    print(f"sys.path={':'.join(sys.path)!r}")
    print('------')

    try:
        import numpy
        has_newnumpy = 1
    except ImportError as e:
        print('Failed to import new numpy:', e)
        has_newnumpy = 0

    try:
        from numpy.f2py import f2py2e
        has_f2py2e = 1
    except ImportError as e:
        print('Failed to import f2py2e:', e)
        has_f2py2e = 0

    try:
        import numpy.distutils
        has_numpy_distutils = 2
    except ImportError:
        try:
            import numpy_distutils
            has_numpy_distutils = 1
        except ImportError as e:
            print('Failed to import numpy_distutils:', e)
            has_numpy_distutils = 0

    if has_newnumpy:
        try:
            print(f'Found new numpy version {numpy.__version__!r} in {numpy.__file__}')
        except Exception as msg:
            print('error:', msg)
            print('------')

    if has_f2py2e:
        try:
            print('Found f2py2e version %r in %s' %
                  (f2py2e.__version__.version, f2py2e.__file__))
        except Exception as msg:
            print('error:', msg)
            print('------')

    if has_numpy_distutils:
        try:
            if has_numpy_distutils == 2:
                print('Found numpy.distutils version %r in %r' % (
                    numpy.distutils.__version__,
                    numpy.distutils.__file__))
            else:
                print('Found numpy_distutils version %r in %r' % (
                    numpy_distutils.numpy_distutils_version.numpy_distutils_version,
                    numpy_distutils.__file__))
            print('------')
        except Exception as msg:
            print('error:', msg)
            print('------')
        try:
            if has_numpy_distutils == 1:
                print(
                    'Importing numpy_distutils.command.build_flib ...', end=' ')
                import numpy_distutils.command.build_flib as build_flib
                print('ok')
                print('------')
                try:
                    print(
                        'Checking availability of supported Fortran compilers:')
                    for compiler_class in build_flib.all_compilers:
                        compiler_class(verbose=1).is_available()
                        print('------')
                except Exception as msg:
                    print('error:', msg)
                    print('------')
        except Exception as msg:
            print(
                'error:', msg, '(ignore it, build_flib is obsolete for numpy.distutils 0.2.2 and up)')
            print('------')
        try:
            if has_numpy_distutils == 2:
                print('Importing numpy.distutils.fcompiler ...', end=' ')
                import numpy.distutils.fcompiler as fcompiler
            else:
                print('Importing numpy_distutils.fcompiler ...', end=' ')
                import numpy_distutils.fcompiler as fcompiler
            print('ok')
            print('------')
            try:
                print('Checking availability of supported Fortran compilers:')
                fcompiler.show_fcompilers()
                print('------')
            except Exception as msg:
                print('error:', msg)
                print('------')
        except Exception as msg:
            print('error:', msg)
            print('------')
        try:
            if has_numpy_distutils == 2:
                print('Importing numpy.distutils.cpuinfo ...', end=' ')
                from numpy.distutils.cpuinfo import cpuinfo
                print('ok')
                print('------')
            else:
                try:
                    print(
                        'Importing numpy_distutils.command.cpuinfo ...', end=' ')
                    from numpy_distutils.command.cpuinfo import cpuinfo
                    print('ok')
                    print('------')
                except Exception as msg:
                    print('error:', msg, '(ignore it)')
                    print('Importing numpy_distutils.cpuinfo ...', end=' ')
                    from numpy_distutils.cpuinfo import cpuinfo
                    print('ok')
                    print('------')
            cpu = cpuinfo()
            print('CPU information:', end=' ')
            for name in dir(cpuinfo):
                if name[0] == '_' and name[1] != '_' and getattr(cpu, name[1:])():
                    print(name[1:], end=' ')
            print('------')
        except Exception as msg:
            print('error:', msg)
            print('------')
    os.chdir(_path)


if __name__ == "__main__":
    run()

# === NexusCore/openenv\Lib\site-packages\openai\types\audio\transcription_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..._types import FileTypes
from ..audio_model import AudioModel
from .transcription_include import TranscriptionInclude
from ..audio_response_format import AudioResponseFormat

__all__ = [
    "TranscriptionCreateParamsBase",
    "ChunkingStrategy",
    "ChunkingStrategyVadConfig",
    "TranscriptionCreateParamsNonStreaming",
    "TranscriptionCreateParamsStreaming",
]


class TranscriptionCreateParamsBase(TypedDict, total=False):
    file: Required[FileTypes]
    """
    The audio file object (not file name) to transcribe, in one of these formats:
    flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
    """

    model: Required[Union[str, AudioModel]]
    """ID of the model to use.

    The options are `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, and `whisper-1`
    (which is powered by our open source Whisper V2 model).
    """

    chunking_strategy: Optional[ChunkingStrategy]
    """Controls how the audio is cut into chunks.

    When set to `"auto"`, the server first normalizes loudness and then uses voice
    activity detection (VAD) to choose boundaries. `server_vad` object can be
    provided to tweak VAD detection parameters manually. If unset, the audio is
    transcribed as a single block.
    """

    include: List[TranscriptionInclude]
    """Additional information to include in the transcription response.

    `logprobs` will return the log probabilities of the tokens in the response to
    understand the model's confidence in the transcription. `logprobs` only works
    with response_format set to `json` and only with the models `gpt-4o-transcribe`
    and `gpt-4o-mini-transcribe`.
    """

    language: str
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    prompt: str
    """An optional text to guide the model's style or continue a previous audio
    segment.

    The [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
    should match the audio language.
    """

    response_format: AudioResponseFormat
    """
    The format of the output, in one of these options: `json`, `text`, `srt`,
    `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
    the only supported format is `json`.
    """

    temperature: float
    """The sampling temperature, between 0 and 1.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. If set to 0, the model will use
    [log probability](https://en.wikipedia.org/wiki/Log_probability) to
    automatically increase the temperature until certain thresholds are hit.
    """

    timestamp_granularities: List[Literal["word", "segment"]]
    """The timestamp granularities to populate for this transcription.

    `response_format` must be set `verbose_json` to use timestamp granularities.
    Either or both of these options are supported: `word`, or `segment`. Note: There
    is no additional latency for segment timestamps, but generating word timestamps
    incurs additional latency.
    """


class ChunkingStrategyVadConfig(TypedDict, total=False):
    type: Required[Literal["server_vad"]]
    """Must be set to `server_vad` to enable manual chunking using server side VAD."""

    prefix_padding_ms: int
    """Amount of audio to include before the VAD detected speech (in milliseconds)."""

    silence_duration_ms: int
    """
    Duration of silence to detect speech stop (in milliseconds). With shorter values
    the model will respond more quickly, but may jump in on short pauses from the
    user.
    """

    threshold: float
    """Sensitivity threshold (0.0 to 1.0) for voice activity detection.

    A higher threshold will require louder audio to activate the model, and thus
    might perform better in noisy environments.
    """


ChunkingStrategy: TypeAlias = Union[Literal["auto"], ChunkingStrategyVadConfig]


class TranscriptionCreateParamsNonStreaming(TranscriptionCreateParamsBase, total=False):
    stream: Optional[Literal[False]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
    for more information.

    Note: Streaming is not supported for the `whisper-1` model and will be ignored.
    """


class TranscriptionCreateParamsStreaming(TranscriptionCreateParamsBase):
    stream: Required[Literal[True]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
    for more information.

    Note: Streaming is not supported for the `whisper-1` model and will be ignored.
    """


TranscriptionCreateParams = Union[TranscriptionCreateParamsNonStreaming, TranscriptionCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\filesystem.py ===
import fnmatch
import os
import os.path
import random
import sys
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, Generator, List, Union, cast

from pip._internal.utils.compat import get_path_uid
from pip._internal.utils.misc import format_size
from pip._internal.utils.retry import retry


def check_path_owner(path: str) -> bool:
    # If we don't have a way to check the effective uid of this process, then
    # we'll just assume that we own the directory.
    if sys.platform == "win32" or not hasattr(os, "geteuid"):
        return True

    assert os.path.isabs(path)

    previous = None
    while path != previous:
        if os.path.lexists(path):
            # Check if path is writable by current user.
            if os.geteuid() == 0:
                # Special handling for root user in order to handle properly
                # cases where users use sudo without -H flag.
                try:
                    path_uid = get_path_uid(path)
                except OSError:
                    return False
                return path_uid == 0
            else:
                return os.access(path, os.W_OK)
        else:
            previous, path = path, os.path.dirname(path)
    return False  # assume we don't own the path


@contextmanager
def adjacent_tmp_file(path: str, **kwargs: Any) -> Generator[BinaryIO, None, None]:
    """Return a file-like object pointing to a tmp file next to path.

    The file is created securely and is ensured to be written to disk
    after the context reaches its end.

    kwargs will be passed to tempfile.NamedTemporaryFile to control
    the way the temporary file will be opened.
    """
    with NamedTemporaryFile(
        delete=False,
        dir=os.path.dirname(path),
        prefix=os.path.basename(path),
        suffix=".tmp",
        **kwargs,
    ) as f:
        result = cast(BinaryIO, f)
        try:
            yield result
        finally:
            result.flush()
            os.fsync(result.fileno())


replace = retry(stop_after_delay=1, wait=0.25)(os.replace)


# test_writable_dir and _test_writable_dir_win are copied from Flit,
# with the author's agreement to also place them under pip's license.
def test_writable_dir(path: str) -> bool:
    """Check if a directory is writable.

    Uses os.access() on POSIX, tries creating files on Windows.
    """
    # If the directory doesn't exist, find the closest parent that does.
    while not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break  # Should never get here, but infinite loops are bad
        path = parent

    if os.name == "posix":
        return os.access(path, os.W_OK)

    return _test_writable_dir_win(path)


def _test_writable_dir_win(path: str) -> bool:
    # os.access doesn't work on Windows: http://bugs.python.org/issue2528
    # and we can't use tempfile: http://bugs.python.org/issue22107
    basename = "accesstest_deleteme_fishfingers_custard_"
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(10):
        name = basename + "".join(random.choice(alphabet) for _ in range(6))
        file = os.path.join(path, name)
        try:
            fd = os.open(file, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            pass
        except PermissionError:
            # This could be because there's a directory with the same name.
            # But it's highly unlikely there's a directory called that,
            # so we'll assume it's because the parent dir is not writable.
            # This could as well be because the parent dir is not readable,
            # due to non-privileged user access.
            return False
        else:
            os.close(fd)
            os.unlink(file)
            return True

    # This should never be reached
    raise OSError("Unexpected condition testing for writable directory")


def find_files(path: str, pattern: str) -> List[str]:
    """Returns a list of absolute paths of files beneath path, recursively,
    with filenames which match the UNIX-style shell glob pattern."""
    result: List[str] = []
    for root, _, files in os.walk(path):
        matches = fnmatch.filter(files, pattern)
        result.extend(os.path.join(root, f) for f in matches)
    return result


def file_size(path: str) -> Union[int, float]:
    # If it's a symlink, return 0.
    if os.path.islink(path):
        return 0
    return os.path.getsize(path)


def format_file_size(path: str) -> str:
    return format_size(file_size(path))


def directory_size(path: str) -> Union[int, float]:
    size = 0.0
    for root, _dirs, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            size += file_size(file_path)
    return size


def format_directory_size(path: str) -> str:
    return format_size(directory_size(path))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\repr.py ===
import inspect
from functools import partial
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")


Result = Iterable[Union[Any, Tuple[Any], Tuple[str, Any], Tuple[str, Any, Any]]]
RichReprResult = Result


class ReprError(Exception):
    """An error occurred when attempting to build a repr."""


@overload
def auto(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def auto(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def auto(
    cls: Optional[Type[T]] = None, *, angular: Optional[bool] = None
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """Class decorator to create __repr__ from __rich_repr__"""

    def do_replace(cls: Type[T], angular: Optional[bool] = None) -> Type[T]:
        def auto_repr(self: T) -> str:
            """Create repr string from __rich_repr__"""
            repr_str: List[str] = []
            append = repr_str.append

            angular: bool = getattr(self.__rich_repr__, "angular", False)  # type: ignore[attr-defined]
            for arg in self.__rich_repr__():  # type: ignore[attr-defined]
                if isinstance(arg, tuple):
                    if len(arg) == 1:
                        append(repr(arg[0]))
                    else:
                        key, value, *default = arg
                        if key is None:
                            append(repr(value))
                        else:
                            if default and default[0] == value:
                                continue
                            append(f"{key}={value!r}")
                else:
                    append(repr(arg))
            if angular:
                return f"<{self.__class__.__name__} {' '.join(repr_str)}>"
            else:
                return f"{self.__class__.__name__}({', '.join(repr_str)})"

        def auto_rich_repr(self: Type[T]) -> Result:
            """Auto generate __rich_rep__ from signature of __init__"""
            try:
                signature = inspect.signature(self.__init__)
                for name, param in signature.parameters.items():
                    if param.kind == param.POSITIONAL_ONLY:
                        yield getattr(self, name)
                    elif param.kind in (
                        param.POSITIONAL_OR_KEYWORD,
                        param.KEYWORD_ONLY,
                    ):
                        if param.default is param.empty:
                            yield getattr(self, param.name)
                        else:
                            yield param.name, getattr(self, param.name), param.default
            except Exception as error:
                raise ReprError(
                    f"Failed to auto generate __rich_repr__; {error}"
                ) from None

        if not hasattr(cls, "__rich_repr__"):
            auto_rich_repr.__doc__ = "Build a rich repr"
            cls.__rich_repr__ = auto_rich_repr  # type: ignore[attr-defined]

        auto_repr.__doc__ = "Return repr(self)"
        cls.__repr__ = auto_repr  # type: ignore[assignment]
        if angular is not None:
            cls.__rich_repr__.angular = angular  # type: ignore[attr-defined]
        return cls

    if cls is None:
        return partial(do_replace, angular=angular)
    else:
        return do_replace(cls, angular=angular)


@overload
def rich_repr(cls: Optional[Type[T]]) -> Type[T]:
    ...


@overload
def rich_repr(*, angular: bool = False) -> Callable[[Type[T]], Type[T]]:
    ...


def rich_repr(
    cls: Optional[Type[T]] = None, *, angular: bool = False
) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    if cls is None:
        return auto(angular=angular)
    else:
        return auto(cls)


if __name__ == "__main__":

    @auto
    class Foo:
        def __rich_repr__(self) -> Result:
            yield "foo"
            yield "bar", {"shopping": ["eggs", "ham", "pineapple"]}
            yield "buy", "hand sanitizer"

    foo = Foo()
    from pip._vendor.rich.console import Console

    console = Console()

    console.rule("Standard repr")
    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

    console.rule("Angular repr")
    Foo.__rich_repr__.angular = True  # type: ignore[attr-defined]

    console.print(foo)

    console.print(foo, width=60)
    console.print(foo, width=30)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\connection.py ===
from __future__ import absolute_import

import socket

from ..contrib import _appengine_environ
from ..exceptions import LocationParseError
from ..packages import six
from .wait import NoWayToWaitForSocketError, wait_for_read


def is_connection_dropped(conn):  # Platform-specific
    """
    Returns True if the connection is dropped and should be closed.

    :param conn:
        :class:`http.client.HTTPConnection` object.

    Note: For platforms like AppEngine, this will always return ``False`` to
    let the platform handle connection recycling transparently for us.
    """
    sock = getattr(conn, "sock", False)
    if sock is False:  # Platform-specific: AppEngine
        return False
    if sock is None:  # Connection already closed (such as by httplib).
        return True
    try:
        # Returns True if readable, which here means it's been dropped
        return wait_for_read(sock, timeout=0.0)
    except NoWayToWaitForSocketError:  # Platform-specific: AppEngine
        return False


# This function is copied from socket.py in the Python 2.7 standard
# library test suite. Added to its signature is only `socket_options`.
# One additional modification is that we avoid binding to IPv6 servers
# discovered in DNS if the system doesn't have IPv6 functionality.
def create_connection(
    address,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address=None,
    socket_options=None,
):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`socket.getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.
    """

    host, port = address
    if host.startswith("["):
        host = host.strip("[]")
    err = None

    # Using the value from allowed_gai_family() in the context of getaddrinfo lets
    # us select whether to work with IPv4 DNS records, IPv6 records, or both.
    # The original create_connection function always returns all records.
    family = allowed_gai_family()

    try:
        host.encode("idna")
    except UnicodeError:
        return six.raise_from(
            LocationParseError(u"'%s', label empty or too long" % host), None
        )

    for res in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)

            # If provided, set socket level options before connecting.
            _set_socket_options(sock, socket_options)

            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except socket.error as e:
            err = e
            if sock is not None:
                sock.close()
                sock = None

    if err is not None:
        raise err

    raise socket.error("getaddrinfo returns an empty list")


def _set_socket_options(sock, options):
    if options is None:
        return

    for opt in options:
        sock.setsockopt(*opt)


def allowed_gai_family():
    """This function is designed to work in the context of
    getaddrinfo, where family=socket.AF_UNSPEC is the default and
    will perform a DNS search for both IPv6 and IPv4 records."""

    family = socket.AF_INET
    if HAS_IPV6:
        family = socket.AF_UNSPEC
    return family


def _has_ipv6(host):
    """Returns True if the system can bind an IPv6 address."""
    sock = None
    has_ipv6 = False

    # App Engine doesn't support IPV6 sockets and actually has a quota on the
    # number of sockets that can be used, so just early out here instead of
    # creating a socket needlessly.
    # See https://github.com/urllib3/urllib3/issues/1446
    if _appengine_environ.is_appengine_sandbox():
        return False

    if socket.has_ipv6:
        # has_ipv6 returns true if cPython was compiled with IPv6 support.
        # It does not tell us if the system has IPv6 support enabled. To
        # determine that we must bind to an IPv6 address.
        # https://github.com/urllib3/urllib3/pull/611
        # https://bugs.python.org/issue658327
        try:
            sock = socket.socket(socket.AF_INET6)
            sock.bind((host, 0))
            has_ipv6 = True
        except Exception:
            pass

    if sock:
        sock.close()
    return has_ipv6


HAS_IPV6 = _has_ipv6("::1")

# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\cer\decoder.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import warnings

from pyasn1 import error
from pyasn1.codec.streaming import readFromStream
from pyasn1.codec.ber import decoder
from pyasn1.type import univ

__all__ = ['decode', 'StreamingDecoder']

SubstrateUnderrunError = error.SubstrateUnderrunError


class BooleanPayloadDecoder(decoder.AbstractSimplePayloadDecoder):
    protoComponent = univ.Boolean(0)

    def valueDecoder(self, substrate, asn1Spec,
                     tagSet=None, length=None, state=None,
                     decodeFun=None, substrateFun=None,
                     **options):

        if length != 1:
            raise error.PyAsn1Error('Not single-octet Boolean payload')

        for chunk in readFromStream(substrate, length, options):
            if isinstance(chunk, SubstrateUnderrunError):
                yield chunk

        byte = chunk[0]

        # CER/DER specifies encoding of TRUE as 0xFF and FALSE as 0x0, while
        # BER allows any non-zero value as TRUE; cf. sections 8.2.2. and 11.1 
        # in https://www.itu.int/ITU-T/studygroups/com17/languages/X.690-0207.pdf
        if byte == 0xff:
            value = 1

        elif byte == 0x00:
            value = 0

        else:
            raise error.PyAsn1Error('Unexpected Boolean payload: %s' % byte)

        yield self._createComponent(asn1Spec, tagSet, value, **options)


# TODO: prohibit non-canonical encoding
BitStringPayloadDecoder = decoder.BitStringPayloadDecoder
OctetStringPayloadDecoder = decoder.OctetStringPayloadDecoder
RealPayloadDecoder = decoder.RealPayloadDecoder

TAG_MAP = decoder.TAG_MAP.copy()
TAG_MAP.update(
    {univ.Boolean.tagSet: BooleanPayloadDecoder(),
     univ.BitString.tagSet: BitStringPayloadDecoder(),
     univ.OctetString.tagSet: OctetStringPayloadDecoder(),
     univ.Real.tagSet: RealPayloadDecoder()}
)

TYPE_MAP = decoder.TYPE_MAP.copy()

# Put in non-ambiguous types for faster codec lookup
for typeDecoder in TAG_MAP.values():
    if typeDecoder.protoComponent is not None:
        typeId = typeDecoder.protoComponent.__class__.typeId
        if typeId is not None and typeId not in TYPE_MAP:
            TYPE_MAP[typeId] = typeDecoder


class SingleItemDecoder(decoder.SingleItemDecoder):
    __doc__ = decoder.SingleItemDecoder.__doc__

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP


class StreamingDecoder(decoder.StreamingDecoder):
    __doc__ = decoder.StreamingDecoder.__doc__

    SINGLE_ITEM_DECODER = SingleItemDecoder


class Decoder(decoder.Decoder):
    __doc__ = decoder.Decoder.__doc__

    STREAMING_DECODER = StreamingDecoder


#: Turns CER octet stream into an ASN.1 object.
#:
#: Takes CER octet-stream and decode it into an ASN.1 object
#: (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative) which
#: may be a scalar or an arbitrary nested structure.
#:
#: Parameters
#: ----------
#: substrate: :py:class:`bytes`
#:     CER octet-stream
#:
#: Keyword Args
#: ------------
#: asn1Spec: any pyasn1 type object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A pyasn1 type object to act as a template guiding the decoder. Depending on the ASN.1 structure
#:     being decoded, *asn1Spec* may or may not be required. Most common reason for
#:     it to require is that ASN.1 structure is encoded in *IMPLICIT* tagging mode.
#:
#: Returns
#: -------
#: : :py:class:`tuple`
#:     A tuple of pyasn1 object recovered from CER substrate (:py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     and the unprocessed trailing portion of the *substrate* (may be empty)
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error, ~pyasn1.error.SubstrateUnderrunError
#:     On decoding errors
#:
#: Examples
#: --------
#: Decode CER serialisation without ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> s, _ = decode(b'0\x80\x02\x01\x01\x02\x01\x02\x02\x01\x03\x00\x00')
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
#: Decode CER serialisation with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> s, _ = decode(b'0\x80\x02\x01\x01\x02\x01\x02\x02\x01\x03\x00\x00', asn1Spec=seq)
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
decode = Decoder()

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning)
        return globals()[newAttr]
    raise AttributeError(attr)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\chromium\options.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import base64
import os
from typing import BinaryIO, Dict, List, Optional, Union

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class ChromiumOptions(ArgOptions):
    KEY = "goog:chromeOptions"

    def __init__(self) -> None:
        super().__init__()
        self._binary_location: str = ""
        self._extension_files: List[str] = []
        self._extensions: List[str] = []
        self._experimental_options: Dict[str, Union[str, int, dict, List[str]]] = {}
        self._debugger_address: Optional[str] = None

    @property
    def binary_location(self) -> str:
        """:Returns: The location of the binary, otherwise an empty string."""
        return self._binary_location

    @binary_location.setter
    def binary_location(self, value: str) -> None:
        """Allows you to set where the chromium binary lives.

        :Args:
         - value: path to the Chromium binary
        """
        if not isinstance(value, str):
            raise TypeError(self.BINARY_LOCATION_ERROR)
        self._binary_location = value

    @property
    def debugger_address(self) -> Optional[str]:
        """:Returns: The address of the remote devtools instance."""
        return self._debugger_address

    @debugger_address.setter
    def debugger_address(self, value: str) -> None:
        """Allows you to set the address of the remote devtools instance that
        the ChromeDriver instance will try to connect to during an active wait.

        :Args:
         - value: address of remote devtools instance if any (hostname[:port])
        """
        if not isinstance(value, str):
            raise TypeError("Debugger Address must be a string")
        self._debugger_address = value

    @property
    def extensions(self) -> List[str]:
        """:Returns: A list of encoded extensions that will be loaded."""

        def _decode(file_data: BinaryIO) -> str:
            # Should not use base64.encodestring() which inserts newlines every
            # 76 characters (per RFC 1521).  Chromedriver has to remove those
            # unnecessary newlines before decoding, causing performance hit.
            return base64.b64encode(file_data.read()).decode("utf-8")

        encoded_extensions = []
        for extension in self._extension_files:
            with open(extension, "rb") as f:
                encoded_extensions.append(_decode(f))

        return encoded_extensions + self._extensions

    def add_extension(self, extension: str) -> None:
        """Adds the path to the extension to a list that will be used to
        extract it to the ChromeDriver.

        :Args:
         - extension: path to the \\*.crx file
        """
        if extension:
            extension_to_add = os.path.abspath(os.path.expanduser(extension))
            if os.path.exists(extension_to_add):
                self._extension_files.append(extension_to_add)
            else:
                raise OSError("Path to the extension doesn't exist")
        else:
            raise ValueError("argument can not be null")

    def add_encoded_extension(self, extension: str) -> None:
        """Adds Base64 encoded string with extension data to a list that will
        be used to extract it to the ChromeDriver.

        :Args:
         - extension: Base64 encoded string with extension data
        """
        if extension:
            self._extensions.append(extension)
        else:
            raise ValueError("argument can not be null")

    @property
    def experimental_options(self) -> dict:
        """:Returns: A dictionary of experimental options for chromium."""
        return self._experimental_options

    def add_experimental_option(self, name: str, value: Union[str, int, dict, List[str]]) -> None:
        """Adds an experimental option which is passed to chromium.

        :Args:
          name: The experimental option name.
          value: The option value.
        """
        self._experimental_options[name] = value

    def to_capabilities(self) -> dict:
        """Creates a capabilities with all the options that have been set
        :Returns: A dictionary with everything."""
        caps = self._caps
        chrome_options = self.experimental_options.copy()
        if self.mobile_options:
            chrome_options.update(self.mobile_options)
        chrome_options["extensions"] = self.extensions
        if self.binary_location:
            chrome_options["binary"] = self.binary_location
        chrome_options["args"] = self._arguments
        if self.debugger_address:
            chrome_options["debuggerAddress"] = self.debugger_address

        caps[self.KEY] = chrome_options

        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.CHROME.copy()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\log.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import json
import pkgutil
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any, AsyncGenerator, Dict, Optional

from selenium.webdriver.common.by import By

cdp = None


def import_cdp():
    global cdp
    if not cdp:
        cdp = import_module("selenium.webdriver.common.bidi.cdp")


class Log:
    """This class allows access to logging APIs that use the new WebDriver Bidi
    protocol.

    This class is not to be used directly and should be used from the
    webdriver base classes.
    """

    def __init__(self, driver, bidi_session) -> None:
        self.driver = driver
        self.session = bidi_session.session
        self.cdp = bidi_session.cdp
        self.devtools = bidi_session.devtools
        _pkg = ".".join(__name__.split(".")[:-1])
        # Ensure _mutation_listener_js is not None before decoding
        _mutation_listener_js_bytes: Optional[bytes] = pkgutil.get_data(_pkg, "mutation-listener.js")
        if _mutation_listener_js_bytes is None:
            raise ValueError("Failed to load mutation-listener.js")
        self._mutation_listener_js = _mutation_listener_js_bytes.decode("utf8").strip()

    @asynccontextmanager
    async def mutation_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for mutation events and emit them as they are found.

        :Usage:
             ::

               async with driver.log.mutation_events() as event:
                    pages.load("dynamic.html")
                    driver.find_element(By.ID, "reveal").click()
                    WebDriverWait(driver, 5)\
                        .until(EC.visibility_of(driver.find_element(By.ID, "revealed")))

                assert event["attribute_name"] == "style"
                assert event["current_value"] == ""
                assert event["old_value"] == "display:none;"
        """

        page = self.cdp.get_session_context("page.enable")
        await page.execute(self.devtools.page.enable())
        runtime = self.cdp.get_session_context("runtime.enable")
        await runtime.execute(self.devtools.runtime.enable())
        await runtime.execute(self.devtools.runtime.add_binding("__webdriver_attribute"))
        self.driver.pin_script(self._mutation_listener_js)
        script_key = await page.execute(
            self.devtools.page.add_script_to_evaluate_on_new_document(self._mutation_listener_js)
        )
        self.driver.pin_script(self._mutation_listener_js, script_key)
        self.driver.execute_script(f"return {self._mutation_listener_js}")

        event: Dict[str, Any] = {}
        async with runtime.wait_for(self.devtools.runtime.BindingCalled) as evnt:
            yield event

        payload = json.loads(evnt.value.payload)
        elements: list = self.driver.find_elements(By.CSS_SELECTOR, f'*[data-__webdriver_id="{payload["target"]}"]')
        if not elements:
            elements.append(None)
        event["element"] = elements[0]
        event["attribute_name"] = payload["name"]
        event["current_value"] = payload["value"]
        event["old_value"] = payload["oldValue"]

    @asynccontextmanager
    async def add_js_error_listener(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for JS errors and when the contextmanager exits check if
        there were JS Errors.

        :Usage:
             ::

                async with driver.log.add_js_error_listener() as error:
                    driver.find_element(By.ID, "throwing-mouseover").click()
                assert bool(error)
                assert error.exception_details.stack_trace.call_frames[0].function_name == "onmouseover"
        """

        session = self.cdp.get_session_context("page.enable")
        await session.execute(self.devtools.page.enable())
        session = self.cdp.get_session_context("runtime.enable")
        await session.execute(self.devtools.runtime.enable())
        js_exception = self.devtools.runtime.ExceptionThrown(None, None)
        async with session.wait_for(self.devtools.runtime.ExceptionThrown) as exception:
            yield js_exception
        js_exception.timestamp = exception.value.timestamp
        js_exception.exception_details = exception.value.exception_details

    @asynccontextmanager
    async def add_listener(self, event_type) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for certain events that are passed in.

        :Args:
         - event_type: The type of event that we want to look at.

        :Usage:
             ::

                async with driver.log.add_listener(Console.log) as messages:
                    driver.execute_script("console.log('I like cheese')")
                assert messages["message"] == "I love cheese"
        """

        from selenium.webdriver.common.bidi.console import Console

        session = self.cdp.get_session_context("page.enable")
        await session.execute(self.devtools.page.enable())
        session = self.cdp.get_session_context("runtime.enable")
        await session.execute(self.devtools.runtime.enable())
        console: Dict[str, Any] = {"message": None, "level": None}
        async with session.wait_for(self.devtools.runtime.ConsoleAPICalled) as messages:
            yield console

        if event_type == Console.ALL or event_type.value == messages.value.type_:
            console["message"] = messages.value.args[0].value
            console["level"] = messages.value.args[0].type_

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\switch_to.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Optional, Union

from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException, NoSuchWindowException
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from .command import Command


class SwitchTo:
    def __init__(self, driver) -> None:
        import weakref

        self._driver = weakref.proxy(driver)

    @property
    def active_element(self) -> WebElement:
        """Returns the element with focus, or BODY if nothing has focus.

        :Usage:
            ::

                element = driver.switch_to.active_element
        """
        return self._driver.execute(Command.W3C_GET_ACTIVE_ELEMENT)["value"]

    @property
    def alert(self) -> Alert:
        """Switches focus to an alert on the page.

        :Usage:
            ::

                alert = driver.switch_to.alert
        """
        alert = Alert(self._driver)
        _ = alert.text
        return alert

    def default_content(self) -> None:
        """Switch focus to the default frame.

        :Usage:
            ::

                driver.switch_to.default_content()
        """
        self._driver.execute(Command.SWITCH_TO_FRAME, {"id": None})

    def frame(self, frame_reference: Union[str, int, WebElement]) -> None:
        """Switches focus to the specified frame, by index, name, or
        webelement.

        :Args:
         - frame_reference: The name of the window to switch to, an integer representing the index,
                            or a webelement that is an (i)frame to switch to.

        :Usage:
            ::

                driver.switch_to.frame("frame_name")
                driver.switch_to.frame(1)
                driver.switch_to.frame(driver.find_elements(By.TAG_NAME, "iframe")[0])
        """
        if isinstance(frame_reference, str):
            try:
                frame_reference = self._driver.find_element(By.ID, frame_reference)
            except NoSuchElementException:
                try:
                    frame_reference = self._driver.find_element(By.NAME, frame_reference)
                except NoSuchElementException as exc:
                    raise NoSuchFrameException(frame_reference) from exc

        self._driver.execute(Command.SWITCH_TO_FRAME, {"id": frame_reference})

    def new_window(self, type_hint: Optional[str] = None) -> None:
        """Switches to a new top-level browsing context.

        The type hint can be one of "tab" or "window". If not specified the
        browser will automatically select it.

        :Usage:
            ::

                driver.switch_to.new_window("tab")
        """
        value = self._driver.execute(Command.NEW_WINDOW, {"type": type_hint})["value"]
        self._w3c_window(value["handle"])

    def parent_frame(self) -> None:
        """Switches focus to the parent context. If the current context is the
        top level browsing context, the context remains unchanged.

        :Usage:
            ::

                driver.switch_to.parent_frame()
        """
        self._driver.execute(Command.SWITCH_TO_PARENT_FRAME)

    def window(self, window_name: str) -> None:
        """Switches focus to the specified window.

        :Args:
         - window_name: The name or window handle of the window to switch to.

        :Usage:
            ::

                driver.switch_to.window("main")
        """
        self._w3c_window(window_name)

    def _w3c_window(self, window_name: str) -> None:
        def send_handle(h):
            self._driver.execute(Command.SWITCH_TO_WINDOW, {"handle": h})

        try:
            # Try using it as a handle first.
            send_handle(window_name)
        except NoSuchWindowException:
            # Check every window to try to find the given window name.
            original_handle = self._driver.current_window_handle
            handles = self._driver.window_handles
            for handle in handles:
                send_handle(handle)
                current_name = self._driver.execute_script("return window.name")
                if window_name == current_name:
                    return
            send_handle(original_handle)
            raise

# === NexusCore/openenv\Lib\site-packages\win32com\test\testGatewayAddresses.py ===
# The purpose of this test is to ensure that the gateways objects
# do the right thing WRT COM rules about object identity etc.

# Also includes a basic test that we support inheritance correctly in
# gateway interfaces.

# For our test, we create an object of type IID_IPersistStorage
# This interface derives from IPersist.
# Therefore, QI's for IID_IDispatch, IID_IUnknown, IID_IPersist and
# IID_IPersistStorage should all return the same gateway object.
#
# In addition, the interface should only need to declare itself as
# using the IPersistStorage interface, and as the gateway derives
# from IPersist, it should automatically be available without declaration.
#
# We also create an object of type IID_I??, and perform a QI for it.
# We then jump through a number of hoops, ensuring that the objects
# returned by the QIs follow all the rules.
#
# Here is Gregs summary of the rules:
# 1) the set of supported interfaces is static and unchanging
# 2) symmetric: if you QI an interface for that interface, it succeeds
# 3) reflexive: if you QI against A for B, the new pointer must succeed
#   for a QI for A
# 4) transitive: if you QI for B, then QI that for C, then QI'ing A for C
#   must succeed
#
#
# Note that 1) Requires cooperation of the Python programmer.  The rule to keep is:
# "whenever you return an _object_ from _query_interface_(), you must return the
# same object each time for a given IID.  Note that you must return the same
# _wrapped_ object
# you
# The rest are tested here.


import pythoncom
from win32com.server.util import wrap

from .util import CheckClean

numErrors = 0


# Check that the 2 objects both have identical COM pointers.
def CheckSameCOMObject(ob1, ob2):
    addr1 = repr(ob1).split()[6][:-1]
    addr2 = repr(ob2).split()[6][:-1]
    return addr1 == addr2


# Check that the objects conform to COM identity rules.
def CheckObjectIdentity(ob1, ob2):
    u1 = ob1.QueryInterface(pythoncom.IID_IUnknown)
    u2 = ob2.QueryInterface(pythoncom.IID_IUnknown)
    return CheckSameCOMObject(u1, u2)


def FailObjectIdentity(ob1, ob2, when):
    if not CheckObjectIdentity(ob1, ob2):
        global numErrors
        numErrors += 1
        print(f"{when} are not identical ({ob1!r}, {ob2!r})")


class Dummy:
    _public_methods_ = []  # We never attempt to make a call on this object.
    _com_interfaces_ = [pythoncom.IID_IPersistStorage]


class Dummy2:
    _public_methods_ = []  # We never attempt to make a call on this object.
    _com_interfaces_ = [
        pythoncom.IID_IPersistStorage,
        pythoncom.IID_IExternalConnection,
    ]


class DelegatedDummy:
    _public_methods_ = []


class Dummy3:
    _public_methods_ = []  # We never attempt to make a call on this object.
    _com_interfaces_ = [pythoncom.IID_IPersistStorage]

    def _query_interface_(self, iid):
        if iid == pythoncom.IID_IExternalConnection:
            # This will NEVER work - can only wrap the object once!
            return wrap(DelegatedDummy())


def TestGatewayInheritance():
    # By default, wrap() creates and discards a temporary object.
    # This is not necessary, but just the current implementation of wrap.
    # As the object is correctly discarded, it doesn't affect this test.
    o = wrap(Dummy(), pythoncom.IID_IPersistStorage)
    o2 = o.QueryInterface(pythoncom.IID_IUnknown)
    FailObjectIdentity(o, o2, "IID_IPersistStorage->IID_IUnknown")

    o3 = o2.QueryInterface(pythoncom.IID_IDispatch)

    FailObjectIdentity(o2, o3, "IID_IUnknown->IID_IDispatch")
    FailObjectIdentity(o, o3, "IID_IPersistStorage->IID_IDispatch")

    o4 = o3.QueryInterface(pythoncom.IID_IPersistStorage)
    FailObjectIdentity(o, o4, "IID_IPersistStorage->IID_IPersistStorage(2)")
    FailObjectIdentity(o2, o4, "IID_IUnknown->IID_IPersistStorage(2)")
    FailObjectIdentity(o3, o4, "IID_IDispatch->IID_IPersistStorage(2)")

    o5 = o4.QueryInterface(pythoncom.IID_IPersist)
    FailObjectIdentity(o, o5, "IID_IPersistStorage->IID_IPersist")
    FailObjectIdentity(o2, o5, "IID_IUnknown->IID_IPersist")
    FailObjectIdentity(o3, o5, "IID_IDispatch->IID_IPersist")
    FailObjectIdentity(o4, o5, "IID_IPersistStorage(2)->IID_IPersist")


def TestMultiInterface():
    o = wrap(Dummy2(), pythoncom.IID_IPersistStorage)
    o2 = o.QueryInterface(pythoncom.IID_IExternalConnection)

    FailObjectIdentity(o, o2, "IID_IPersistStorage->IID_IExternalConnection")

    # Make the same QI again, to make sure it is stable.
    o22 = o.QueryInterface(pythoncom.IID_IExternalConnection)
    FailObjectIdentity(o, o22, "IID_IPersistStorage->IID_IExternalConnection")
    FailObjectIdentity(
        o2, o22, "IID_IPersistStorage->IID_IExternalConnection (stability)"
    )

    o3 = o2.QueryInterface(pythoncom.IID_IPersistStorage)
    FailObjectIdentity(o2, o3, "IID_IExternalConnection->IID_IPersistStorage")
    FailObjectIdentity(
        o, o3, "IID_IPersistStorage->IID_IExternalConnection->IID_IPersistStorage"
    )


def test():
    TestGatewayInheritance()
    TestMultiInterface()
    if numErrors == 0:
        print("Worked ok")
    else:
        print("There were", numErrors, "errors.")


if __name__ == "__main__":
    test()
    CheckClean()

# === NexusCore/vscode-extension\node_modules\flatted\python\flatted.py ===
# ISC License
#
# Copyright (c) 2018-2025, Andrea Giammarchi, @WebReflection
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import json as _json

class _Known:
    def __init__(self):
        self.key = []
        self.value = []

class _String:
    def __init__(self, value):
        self.value = value


def _array_keys(value):
    keys = []
    i = 0
    for _ in value:
        keys.append(i)
        i += 1
    return keys

def _object_keys(value):
    keys = []
    for key in value:
        keys.append(key)
    return keys

def _is_array(value):
    return isinstance(value, (list, tuple))

def _is_object(value):
    return isinstance(value, dict)

def _is_string(value):
    return isinstance(value, str)

def _index(known, input, value):
    input.append(value)
    index = str(len(input) - 1)
    known.key.append(value)
    known.value.append(index)
    return index

def _loop(keys, input, known, output):
    for key in keys:
        value = output[key]
        if isinstance(value, _String):
            _ref(key, input[int(value.value)], input, known, output)

    return output

def _ref(key, value, input, known, output):
    if _is_array(value) and value not in known:
        known.append(value)
        value = _loop(_array_keys(value), input, known, value)
    elif _is_object(value) and value not in known:
        known.append(value)
        value = _loop(_object_keys(value), input, known, value)

    output[key] = value

def _relate(known, input, value):
    if _is_string(value) or _is_array(value) or _is_object(value):
        try:
            return known.value[known.key.index(value)]
        except:
            return _index(known, input, value)

    return value

def _transform(known, input, value):
    if _is_array(value):
        output = []
        for val in value:
            output.append(_relate(known, input, val))
        return output

    if _is_object(value):
        obj = {}
        for key in value:
            obj[key] = _relate(known, input, value[key])
        return obj

    return value

def _wrap(value):
    if _is_string(value):
        return _String(value)

    if _is_array(value):
        i = 0
        for val in value:
            value[i] = _wrap(val)
            i += 1

    elif _is_object(value):
        for key in value:
            value[key] = _wrap(value[key])

    return value

def parse(value, *args, **kwargs):
    json = _json.loads(value, *args, **kwargs)
    wrapped = []
    for value in json:
        wrapped.append(_wrap(value))

    input = []
    for value in wrapped:
        if isinstance(value, _String):
            input.append(value.value)
        else:
            input.append(value)

    value = input[0]

    if _is_array(value):
        return _loop(_array_keys(value), input, [value], value)

    if _is_object(value):
        return _loop(_object_keys(value), input, [value], value)

    return value


def stringify(value, *args, **kwargs):
    known = _Known()
    input = []
    output = []
    i = int(_index(known, input, value))
    while i < len(input):
        output.append(_transform(known, input, input[i]))
        i += 1
    return _json.dumps(output, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\trio\_highlevel_serve_listeners.py ===
from __future__ import annotations

import errno
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any, NoReturn, TypeVar

import trio

# Errors that accept(2) can return, and which indicate that the system is
# overloaded
ACCEPT_CAPACITY_ERRNOS = {
    errno.EMFILE,
    errno.ENFILE,
    errno.ENOMEM,
    errno.ENOBUFS,
}

# How long to sleep when we get one of those errors
SLEEP_TIME = 0.100

# The logger we use to complain when this happens
LOGGER = logging.getLogger("trio.serve_listeners")


StreamT = TypeVar("StreamT", bound=trio.abc.AsyncResource)
ListenerT = TypeVar("ListenerT", bound=trio.abc.Listener[Any])  # type: ignore[explicit-any]
Handler = Callable[[StreamT], Awaitable[object]]


async def _run_handler(stream: StreamT, handler: Handler[StreamT]) -> None:
    try:
        await handler(stream)
    finally:
        await trio.aclose_forcefully(stream)


async def _serve_one_listener(
    listener: trio.abc.Listener[StreamT],
    handler_nursery: trio.Nursery,
    handler: Handler[StreamT],
) -> NoReturn:
    async with listener:
        while True:
            try:
                stream = await listener.accept()
            except OSError as exc:
                if exc.errno in ACCEPT_CAPACITY_ERRNOS:
                    LOGGER.error(
                        "accept returned %s (%s); retrying in %s seconds",
                        errno.errorcode[exc.errno],
                        os.strerror(exc.errno),
                        SLEEP_TIME,
                        exc_info=True,
                    )
                    await trio.sleep(SLEEP_TIME)
                else:
                    raise
            else:
                handler_nursery.start_soon(_run_handler, stream, handler)


# This cannot be typed correctly, we need generic typevar bounds / HKT to indicate the
# relationship between StreamT & ListenerT.
# https://github.com/python/typing/issues/1226
# https://github.com/python/typing/issues/548


async def serve_listeners(  # type: ignore[explicit-any]
    handler: Handler[StreamT],
    listeners: list[ListenerT],
    *,
    handler_nursery: trio.Nursery | None = None,
    task_status: trio.TaskStatus[list[ListenerT]] = trio.TASK_STATUS_IGNORED,
) -> NoReturn:
    r"""Listen for incoming connections on ``listeners``, and for each one
    start a task running ``handler(stream)``.

    .. warning::

       If ``handler`` raises an exception, then this function doesn't do
       anything special to catch it – so by default the exception will
       propagate out and crash your server. If you don't want this, then catch
       exceptions inside your ``handler``, or use a ``handler_nursery`` object
       that responds to exceptions in some other way.

    Args:

      handler: An async callable, that will be invoked like
          ``handler_nursery.start_soon(handler, stream)`` for each incoming
          connection.

      listeners: A list of :class:`~trio.abc.Listener` objects.
          :func:`serve_listeners` takes responsibility for closing them.

      handler_nursery: The nursery used to start handlers, or any object with
          a ``start_soon`` method. If ``None`` (the default), then
          :func:`serve_listeners` will create a new nursery internally and use
          that.

      task_status: This function can be used with ``nursery.start``, which
          will return ``listeners``.

    Returns:

      This function never returns unless cancelled.

    Resource handling:

      If ``handler`` neglects to close the ``stream``, then it will be closed
      using :func:`trio.aclose_forcefully`.

    Error handling:

      Most errors coming from :meth:`~trio.abc.Listener.accept` are allowed to
      propagate out (crashing the server in the process). However, some errors –
      those which indicate that the server is temporarily overloaded – are
      handled specially. These are :class:`OSError`\s with one of the following
      errnos:

      * ``EMFILE``: process is out of file descriptors
      * ``ENFILE``: system is out of file descriptors
      * ``ENOBUFS``, ``ENOMEM``: the kernel hit some sort of memory limitation
        when trying to create a socket object

      When :func:`serve_listeners` gets one of these errors, then it:

      * Logs the error to the standard library logger ``trio.serve_listeners``
        (level = ERROR, with exception information included). By default this
        causes it to be printed to stderr.
      * Waits 100 ms before calling ``accept`` again, in hopes that the
        system will recover.

    """
    async with trio.open_nursery() as nursery:
        if handler_nursery is None:
            handler_nursery = nursery
        for listener in listeners:
            nursery.start_soon(_serve_one_listener, listener, handler_nursery, handler)
        # The listeners are already queueing connections when we're called,
        # but we wait until the end to call started() just in case we get an
        # error or whatever.
        task_status.started(listeners)

    raise AssertionError(
        "_serve_one_listener should never complete",
    )  # pragma: no cover

# === NexusCore/openenv\Lib\site-packages\anyio\streams\file.py ===
from __future__ import annotations

from collections.abc import Callable, Mapping
from io import SEEK_SET, UnsupportedOperation
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, cast

from .. import (
    BrokenResourceError,
    ClosedResourceError,
    EndOfStream,
    TypedAttributeSet,
    to_thread,
    typed_attribute,
)
from ..abc import ByteReceiveStream, ByteSendStream


class FileStreamAttribute(TypedAttributeSet):
    #: the open file descriptor
    file: BinaryIO = typed_attribute()
    #: the path of the file on the file system, if available (file must be a real file)
    path: Path = typed_attribute()
    #: the file number, if available (file must be a real file or a TTY)
    fileno: int = typed_attribute()


class _BaseFileStream:
    def __init__(self, file: BinaryIO):
        self._file = file

    async def aclose(self) -> None:
        await to_thread.run_sync(self._file.close)

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        attributes: dict[Any, Callable[[], Any]] = {
            FileStreamAttribute.file: lambda: self._file,
        }

        if hasattr(self._file, "name"):
            attributes[FileStreamAttribute.path] = lambda: Path(self._file.name)

        try:
            self._file.fileno()
        except UnsupportedOperation:
            pass
        else:
            attributes[FileStreamAttribute.fileno] = lambda: self._file.fileno()

        return attributes


class FileReadStream(_BaseFileStream, ByteReceiveStream):
    """
    A byte stream that reads from a file in the file system.

    :param file: a file that has been opened for reading in binary mode

    .. versionadded:: 3.0
    """

    @classmethod
    async def from_path(cls, path: str | PathLike[str]) -> FileReadStream:
        """
        Create a file read stream by opening the given file.

        :param path: path of the file to read from

        """
        file = await to_thread.run_sync(Path(path).open, "rb")
        return cls(cast(BinaryIO, file))

    async def receive(self, max_bytes: int = 65536) -> bytes:
        try:
            data = await to_thread.run_sync(self._file.read, max_bytes)
        except ValueError:
            raise ClosedResourceError from None
        except OSError as exc:
            raise BrokenResourceError from exc

        if data:
            return data
        else:
            raise EndOfStream

    async def seek(self, position: int, whence: int = SEEK_SET) -> int:
        """
        Seek the file to the given position.

        .. seealso:: :meth:`io.IOBase.seek`

        .. note:: Not all file descriptors are seekable.

        :param position: position to seek the file to
        :param whence: controls how ``position`` is interpreted
        :return: the new absolute position
        :raises OSError: if the file is not seekable

        """
        return await to_thread.run_sync(self._file.seek, position, whence)

    async def tell(self) -> int:
        """
        Return the current stream position.

        .. note:: Not all file descriptors are seekable.

        :return: the current absolute position
        :raises OSError: if the file is not seekable

        """
        return await to_thread.run_sync(self._file.tell)


class FileWriteStream(_BaseFileStream, ByteSendStream):
    """
    A byte stream that writes to a file in the file system.

    :param file: a file that has been opened for writing in binary mode

    .. versionadded:: 3.0
    """

    @classmethod
    async def from_path(
        cls, path: str | PathLike[str], append: bool = False
    ) -> FileWriteStream:
        """
        Create a file write stream by opening the given file for writing.

        :param path: path of the file to write to
        :param append: if ``True``, open the file for appending; if ``False``, any
            existing file at the given path will be truncated

        """
        mode = "ab" if append else "wb"
        file = await to_thread.run_sync(Path(path).open, mode)
        return cls(cast(BinaryIO, file))

    async def send(self, item: bytes) -> None:
        try:
            await to_thread.run_sync(self._file.write, item)
        except ValueError:
            raise ClosedResourceError from None
        except OSError as exc:
            raise BrokenResourceError from exc

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\__main__.py ===
import sys
from fontTools.ttLib import OPTIMIZE_FONT_SPEED, TTLibError, TTLibFileIsCollectionError
from fontTools.ttLib.ttFont import *
from fontTools.ttLib.ttCollection import TTCollection


def main(args=None):
    """Open/save fonts with TTFont() or TTCollection()

      ./fonttools ttLib [-oFILE] [-yNUMBER] files...

    If multiple files are given on the command-line,
    they are each opened (as a font or collection),
    and added to the font list.

    If -o (output-file) argument is given, the font
    list is then saved to the output file, either as
    a single font, if there is only one font, or as
    a collection otherwise.

    If -y (font-number) argument is given, only the
    specified font from collections is opened.

    The above allow extracting a single font from a
    collection, or combining multiple fonts into a
    collection.

    If --lazy or --no-lazy are give, those are passed
    to the TTFont() or TTCollection() constructors.
    """
    from fontTools import configLogger

    if args is None:
        args = sys.argv[1:]

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools ttLib",
        description="Open/save fonts with TTFont() or TTCollection()",
        epilog="""
		If multiple files are given on the command-line,
		they are each opened (as a font or collection),
		and added to the font list.

		The above, when combined with -o / --output,
		allows for extracting a single font from a
		collection, or combining multiple fonts into a
		collection.
		""",
    )
    parser.add_argument("font", metavar="font", nargs="*", help="Font file.")
    parser.add_argument(
        "-t", "--table", metavar="table", action="append", help="Tables to decompile."
    )
    parser.add_argument(
        "-o", "--output", metavar="FILE", default=None, help="Output file."
    )
    parser.add_argument(
        "-y", metavar="NUMBER", default=-1, help="Font number to load from collections."
    )
    parser.add_argument(
        "--lazy", action="store_true", default=None, help="Load fonts lazily."
    )
    parser.add_argument(
        "--no-lazy", dest="lazy", action="store_false", help="Load fonts immediately."
    )
    parser.add_argument(
        "--flavor",
        dest="flavor",
        default=None,
        help="Flavor of output font. 'woff' or 'woff2'.",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalcTimestamp",
        action="store_false",
        help="Keep the original font 'modified' timestamp.",
    )
    parser.add_argument(
        "-b",
        dest="recalcBBoxes",
        action="store_false",
        help="Don't recalc glyph bounding boxes: use the values in the original font.",
    )
    parser.add_argument(
        "--optimize-font-speed",
        action="store_true",
        help=(
            "Enable optimizations that prioritize speed over file size. This "
            "mainly affects how glyf table and gvar / VARC tables are compiled."
        ),
    )
    options = parser.parse_args(args)

    fontNumber = int(options.y) if options.y is not None else None
    outFile = options.output
    lazy = options.lazy
    flavor = options.flavor
    tables = options.table
    recalcBBoxes = options.recalcBBoxes
    recalcTimestamp = options.recalcTimestamp
    optimizeFontSpeed = options.optimize_font_speed

    fonts = []
    for f in options.font:
        try:
            font = TTFont(
                f,
                recalcBBoxes=recalcBBoxes,
                recalcTimestamp=recalcTimestamp,
                fontNumber=fontNumber,
                lazy=lazy,
            )
            if optimizeFontSpeed:
                font.cfg[OPTIMIZE_FONT_SPEED] = optimizeFontSpeed
            fonts.append(font)
        except TTLibFileIsCollectionError:
            collection = TTCollection(f, lazy=lazy)
            fonts.extend(collection.fonts)

    if tables is None:
        if lazy is False:
            tables = ["*"]
        elif optimizeFontSpeed:
            tables = {"glyf", "gvar", "VARC"}.intersection(font.keys())
        else:
            tables = []
    for font in fonts:
        if "GlyphOrder" in tables:
            font.getGlyphOrder()
        for table in tables if "*" not in tables else font.keys():
            font[table]  # Decompiles

    if outFile is not None:
        if len(fonts) == 1:
            fonts[0].flavor = flavor
            fonts[0].save(outFile)
        else:
            if flavor is not None:
                raise TTLibError("Cannot set flavor for collections.")
            collection = TTCollection()
            collection.fonts = fonts
            collection.save(outFile)


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\G_M_A_P_.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import tobytes, tostr, safeEval
from . import DefaultTable

GMAPFormat = """
		>	# big endian
		tableVersionMajor:	H
		tableVersionMinor: 	H
		flags:	H
		recordsCount:		H
		recordsOffset:		H
		fontNameLength:		H
"""
# psFontName is a byte string which follows the record above. This is zero padded
# to the beginning of the records array. The recordsOffsst is 32 bit aligned.

GMAPRecordFormat1 = """
		>	# big endian
		UV:			L
		cid:		H
		gid:		H
		ggid:		H
		name:		32s
"""


class GMAPRecord(object):
    def __init__(self, uv=0, cid=0, gid=0, ggid=0, name=""):
        self.UV = uv
        self.cid = cid
        self.gid = gid
        self.ggid = ggid
        self.name = name

    def toXML(self, writer, ttFont):
        writer.begintag("GMAPRecord")
        writer.newline()
        writer.simpletag("UV", value=self.UV)
        writer.newline()
        writer.simpletag("cid", value=self.cid)
        writer.newline()
        writer.simpletag("gid", value=self.gid)
        writer.newline()
        writer.simpletag("glyphletGid", value=self.gid)
        writer.newline()
        writer.simpletag("GlyphletName", value=self.name)
        writer.newline()
        writer.endtag("GMAPRecord")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        value = attrs["value"]
        if name == "GlyphletName":
            self.name = value
        else:
            setattr(self, name, safeEval(value))

    def compile(self, ttFont):
        if self.UV is None:
            self.UV = 0
        nameLen = len(self.name)
        if nameLen < 32:
            self.name = self.name + "\0" * (32 - nameLen)
        data = sstruct.pack(GMAPRecordFormat1, self)
        return data

    def __repr__(self):
        return (
            "GMAPRecord[ UV: "
            + str(self.UV)
            + ", cid: "
            + str(self.cid)
            + ", gid: "
            + str(self.gid)
            + ", ggid: "
            + str(self.ggid)
            + ", Glyphlet Name: "
            + str(self.name)
            + " ]"
        )


class table_G_M_A_P_(DefaultTable.DefaultTable):
    """Glyphlets GMAP table

    The ``GMAP`` table is used by Adobe's SING Glyphlets.

    See also https://web.archive.org/web/20080627183635/http://www.adobe.com/devnet/opentype/gdk/topic.html
    """

    dependencies = []

    def decompile(self, data, ttFont):
        dummy, newData = sstruct.unpack2(GMAPFormat, data, self)
        self.psFontName = tostr(newData[: self.fontNameLength])
        assert (
            self.recordsOffset % 4
        ) == 0, "GMAP error: recordsOffset is not 32 bit aligned."
        newData = data[self.recordsOffset :]
        self.gmapRecords = []
        for i in range(self.recordsCount):
            gmapRecord, newData = sstruct.unpack2(
                GMAPRecordFormat1, newData, GMAPRecord()
            )
            gmapRecord.name = gmapRecord.name.strip("\0")
            self.gmapRecords.append(gmapRecord)

    def compile(self, ttFont):
        self.recordsCount = len(self.gmapRecords)
        self.fontNameLength = len(self.psFontName)
        self.recordsOffset = 4 * (((self.fontNameLength + 12) + 3) // 4)
        data = sstruct.pack(GMAPFormat, self)
        data = data + tobytes(self.psFontName)
        data = data + b"\0" * (self.recordsOffset - len(data))
        for record in self.gmapRecords:
            data = data + record.compile(ttFont)
        return data

    def toXML(self, writer, ttFont):
        writer.comment("Most of this table will be recalculated by the compiler")
        writer.newline()
        formatstring, names, fixes = sstruct.getformat(GMAPFormat)
        for name in names:
            value = getattr(self, name)
            writer.simpletag(name, value=value)
            writer.newline()
        writer.simpletag("PSFontName", value=self.psFontName)
        writer.newline()
        for gmapRecord in self.gmapRecords:
            gmapRecord.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "GMAPRecord":
            if not hasattr(self, "gmapRecords"):
                self.gmapRecords = []
            gmapRecord = GMAPRecord()
            self.gmapRecords.append(gmapRecord)
            for element in content:
                if isinstance(element, str):
                    continue
                name, attrs, content = element
                gmapRecord.fromXML(name, attrs, content, ttFont)
        else:
            value = attrs["value"]
            if name == "PSFontName":
                self.psFontName = value
            else:
                setattr(self, name, safeEval(value))

# === NexusCore/openenv\Lib\site-packages\grpc\framework\foundation\stream_util.py ===
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
"""Helpful utilities related to the stream module."""

import logging
import threading

from grpc.framework.foundation import stream

_NO_VALUE = object()
_LOGGER = logging.getLogger(__name__)


class TransformingConsumer(stream.Consumer):
    """A stream.Consumer that passes a transformation of its input to another."""

    def __init__(self, transformation, downstream):
        self._transformation = transformation
        self._downstream = downstream

    def consume(self, value):
        self._downstream.consume(self._transformation(value))

    def terminate(self):
        self._downstream.terminate()

    def consume_and_terminate(self, value):
        self._downstream.consume_and_terminate(self._transformation(value))


class IterableConsumer(stream.Consumer):
    """A Consumer that when iterated over emits the values it has consumed."""

    def __init__(self):
        self._condition = threading.Condition()
        self._values = []
        self._active = True

    def consume(self, value):
        with self._condition:
            if self._active:
                self._values.append(value)
                self._condition.notify()

    def terminate(self):
        with self._condition:
            self._active = False
            self._condition.notify()

    def consume_and_terminate(self, value):
        with self._condition:
            if self._active:
                self._values.append(value)
                self._active = False
                self._condition.notify()

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        with self._condition:
            while self._active and not self._values:
                self._condition.wait()
            if self._values:
                return self._values.pop(0)
            else:
                raise StopIteration()


class ThreadSwitchingConsumer(stream.Consumer):
    """A Consumer decorator that affords serialization and asynchrony."""

    def __init__(self, sink, pool):
        self._lock = threading.Lock()
        self._sink = sink
        self._pool = pool
        # True if self._spin has been submitted to the pool to be called once and
        # that call has not yet returned, False otherwise.
        self._spinning = False
        self._values = []
        self._active = True

    def _spin(self, sink, value, terminate):
        while True:
            try:
                if value is _NO_VALUE:
                    sink.terminate()
                elif terminate:
                    sink.consume_and_terminate(value)
                else:
                    sink.consume(value)
            except Exception as e:  # pylint:disable=broad-except
                _LOGGER.exception(e)

            with self._lock:
                if terminate:
                    self._spinning = False
                    return
                elif self._values:
                    value = self._values.pop(0)
                    terminate = not self._values and not self._active
                elif not self._active:
                    value = _NO_VALUE
                    terminate = True
                else:
                    self._spinning = False
                    return

    def consume(self, value):
        with self._lock:
            if self._active:
                if self._spinning:
                    self._values.append(value)
                else:
                    self._pool.submit(self._spin, self._sink, value, False)
                    self._spinning = True

    def terminate(self):
        with self._lock:
            if self._active:
                self._active = False
                if not self._spinning:
                    self._pool.submit(self._spin, self._sink, _NO_VALUE, True)
                    self._spinning = True

    def consume_and_terminate(self, value):
        with self._lock:
            if self._active:
                self._active = False
                if self._spinning:
                    self._values.append(value)
                else:
                    self._pool.submit(self._spin, self._sink, value, True)
                    self._spinning = True

# === NexusCore/openenv\Lib\site-packages\IPython\testing\decorators.py ===
import os
import shutil
import sys
import tempfile
from importlib import import_module

import pytest

# Expose the unittest-driven decorators
from .ipunittest import ipdoctest, ipdocstring

def skipif(skip_condition, msg=None):
    """Make function raise SkipTest exception if skip_condition is true

    Parameters
    ----------

    skip_condition : bool or callable
      Flag to determine whether to skip test. If the condition is a
      callable, it is used at runtime to dynamically make the decision. This
      is useful for tests that may require costly imports, to delay the cost
      until the test suite is actually executed.
    msg : string
      Message to give on raising a SkipTest exception.

    Returns
    -------
    decorator : function
      Decorator, which, when applied to a function, causes SkipTest
      to be raised when the skip_condition was True, and the function
      to be called normally otherwise.
    """
    if msg is None:
        msg = "Test skipped due to test condition."

    assert isinstance(skip_condition, bool)
    return pytest.mark.skipif(skip_condition, reason=msg)


# A version with the condition set to true, common case just to attach a message
# to a skip decorator
def skip(msg=None):
    """Decorator factory - mark a test function for skipping from test suite.

    Parameters
    ----------
      msg : string
        Optional message to be added.

    Returns
    -------
       decorator : function
         Decorator, which, when applied to a function, causes SkipTest
         to be raised, with the optional message added.
    """
    if msg and not isinstance(msg, str):
        raise ValueError(
            "invalid object passed to `@skip` decorator, did you "
            "meant `@skip()` with brackets ?"
        )
    return skipif(True, msg)


def onlyif(condition, msg):
    """The reverse from skipif, see skipif for details."""

    return skipif(not condition, msg)


# -----------------------------------------------------------------------------
# Utility functions for decorators
def module_not_available(module):
    """Can module be imported?  Returns true if module does NOT import.

    This is used to make a decorator to skip tests that require module to be
    available, but delay the 'import numpy' to test execution time.
    """
    try:
        mod = import_module(module)
        mod_not_avail = False
    except ImportError:
        mod_not_avail = True

    return mod_not_avail


# -----------------------------------------------------------------------------
# Decorators for public use

# Decorators to skip certain tests on specific platforms.
skip_win32 = skipif(sys.platform == "win32", "This test does not run under Windows")


# Decorators to skip tests if not on specific platforms.
skip_if_not_win32 = skipif(sys.platform != "win32", "This test only runs under Windows")
skip_if_not_osx = skipif(
    not sys.platform.startswith("darwin"), "This test only runs under macOS"
)

_x11_skip_cond = (
    sys.platform not in ("darwin", "win32") and os.environ.get("DISPLAY", "") == ""
)
_x11_skip_msg = "Skipped under *nix when X11/XOrg not available"

skip_if_no_x11 = skipif(_x11_skip_cond, _x11_skip_msg)

# Other skip decorators

# generic skip without module
skip_without = lambda mod: skipif(
    module_not_available(mod), "This test requires %s" % mod
)

skipif_not_numpy = skip_without("numpy")

skipif_not_matplotlib = skip_without("matplotlib")

# A null 'decorator', useful to make more readable code that needs to pick
# between different decorators based on OS or other conditions
null_deco = lambda f: f

# Some tests only run where we can use unicode paths. Note that we can't just
# check os.path.supports_unicode_filenames, which is always False on Linux.
try:
    f = tempfile.NamedTemporaryFile(prefix="tmp€")
except UnicodeEncodeError:
    unicode_paths = False
# TODO: should this be finnally ?
else:
    unicode_paths = True
    f.close()

onlyif_unicode_paths = onlyif(
    unicode_paths,
    ("This test is only applicable where we can use unicode in filenames."),
)


def onlyif_cmds_exist(*commands):
    """
    Decorator to skip test when at least one of `commands` is not found.
    """
    for cmd in commands:
        reason = f"This test runs only if command '{cmd}' is installed"
        if not shutil.which(cmd):

            return pytest.mark.skip(reason=reason)
    return null_deco

# === NexusCore/openenv\Lib\site-packages\litellm\llms\litellm_proxy\chat\transformation.py ===
"""
Translate from OpenAI's `/v1/chat/completions` to VLLM's `/v1/chat/completions`
"""

from typing import TYPE_CHECKING, List, Optional, Tuple

from litellm.secret_managers.main import get_secret_bool, get_secret_str
from litellm.types.router import LiteLLM_Params

from ...openai.chat.gpt_transformation import OpenAIGPTConfig

if TYPE_CHECKING:
    from litellm.types.llms.openai import AllMessageValues


class LiteLLMProxyChatConfig(OpenAIGPTConfig):
    def get_supported_openai_params(self, model: str) -> List:
        params_list = super().get_supported_openai_params(model)
        params_list.append("thinking")
        params_list.append("reasoning_effort")
        return params_list

    def _map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        supported_openai_params = self.get_supported_openai_params(model)
        for param, value in non_default_params.items():
            if param == "thinking":
                optional_params.setdefault("extra_body", {})["thinking"] = value
            elif param in supported_openai_params:
                optional_params[param] = value
        return optional_params

    def _get_openai_compatible_provider_info(
        self, api_base: Optional[str], api_key: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        api_base = api_base or get_secret_str("LITELLM_PROXY_API_BASE")  # type: ignore
        dynamic_api_key = api_key or get_secret_str("LITELLM_PROXY_API_KEY")
        return api_base, dynamic_api_key

    def get_models(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None
    ) -> List[str]:
        api_base, api_key = self._get_openai_compatible_provider_info(api_base, api_key)
        if api_base is None:
            raise ValueError(
                "api_base not set for LiteLLM Proxy route. Set in env via `LITELLM_PROXY_API_BASE`"
            )
        models = super().get_models(api_key=api_key, api_base=api_base)
        return [f"litellm_proxy/{model}" for model in models]

    @staticmethod
    def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
        return api_key or get_secret_str("LITELLM_PROXY_API_KEY")

    @staticmethod
    def _should_use_litellm_proxy_by_default(
        litellm_params: Optional[LiteLLM_Params] = None,
    ):
        """
        Returns True if litellm proxy should be used by default for a given request

        Issue: https://github.com/BerriAI/litellm/issues/10559

        Use case:
        - When using Google ADK, users want a flag to dynamically enable sending the request to litellm proxy or not
        - Allow the model name to be passed in original format and still use litellm proxy:
        "gemini/gemini-1.5-pro", "openai/gpt-4", "mistral/llama-2-70b-chat" etc.
        """
        import litellm

        if get_secret_bool("USE_LITELLM_PROXY") is True:
            return True
        if litellm_params and litellm_params.use_litellm_proxy is True:
            return True
        if litellm.use_litellm_proxy is True:
            return True
        return False

    @staticmethod
    def litellm_proxy_get_custom_llm_provider_info(
        model: str, api_base: Optional[str] = None, api_key: Optional[str] = None
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        """
        Force use litellm proxy for all models

        Issue: https://github.com/BerriAI/litellm/issues/10559

        Expected behavior:
        - custom_llm_provider will be 'litellm_proxy'
        - api_base = api_base OR LITELLM_PROXY_API_BASE
        - api_key = api_key OR LITELLM_PROXY_API_KEY

        Use case:
        - When using Google ADK, users want a flag to dynamically enable sending the request to litellm proxy or not
        -  Allow the model name to be passed in original format and still use litellm proxy:
        "gemini/gemini-1.5-pro", "openai/gpt-4", "mistral/llama-2-70b-chat" etc.

        Return model, custom_llm_provider, dynamic_api_key, api_base
        """
        import litellm

        custom_llm_provider = "litellm_proxy"
        if model.startswith("litellm_proxy/"):
            model = model.split("/", 1)[1]

        (
            api_base,
            api_key,
        ) = litellm.LiteLLMProxyChatConfig()._get_openai_compatible_provider_info(
            api_base=api_base, api_key=api_key
        )

        return model, custom_llm_provider, api_key, api_base

    def transform_request(
        self,
        model: str,
        messages: List["AllMessageValues"],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        # don't transform the request
        return {
            "model": model,
            "messages": messages,
            **optional_params,
        }

    async def async_transform_request(
        self,
        model: str,
        messages: List["AllMessageValues"],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        # don't transform the request
        return {
            "model": model,
            "messages": messages,
            **optional_params,
        }

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_model_garden\main.py ===
"""
API Handler for calling Vertex AI Model Garden Models

Most Vertex Model Garden Models are OpenAI compatible - so this handler calls `openai_like_chat_completions`

Usage:

response = litellm.completion(
    model="vertex_ai/openai/5464397967697903616",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
)

Sent to this route when `model` is in the format `vertex_ai/openai/{MODEL_ID}`


Vertex Documentation for using the OpenAI /chat/completions endpoint: https://github.com/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/community/model_garden/model_garden_pytorch_llama3_deployment.ipynb
"""

from typing import Callable, Optional, Union

import httpx  # type: ignore

from litellm.utils import ModelResponse

from ..common_utils import VertexAIError
from ..vertex_llm_base import VertexBase


def create_vertex_url(
    vertex_location: str,
    vertex_project: str,
    stream: Optional[bool],
    model: str,
    api_base: Optional[str] = None,
) -> str:
    """Return the base url for the vertex garden models"""
    #  f"https://{self.endpoint.location}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{self.endpoint.location}"
    return f"https://{vertex_location}-aiplatform.googleapis.com/v1beta1/projects/{vertex_project}/locations/{vertex_location}/endpoints/{model}"


class VertexAIModelGardenModels(VertexBase):
    def __init__(self) -> None:
        pass

    def completion(
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        api_base: Optional[str],
        optional_params: dict,
        custom_prompt_dict: dict,
        headers: Optional[dict],
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        vertex_project=None,
        vertex_location=None,
        vertex_credentials=None,
        logger_fn=None,
        acompletion: bool = False,
        client=None,
    ):
        """
        Handles calling Vertex AI Model Garden Models in OpenAI compatible format

        Sent to this route when `model` is in the format `vertex_ai/openai/{MODEL_ID}`
        """
        try:
            import vertexai

            from litellm.llms.openai_like.chat.handler import OpenAILikeChatHandler
            from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
                VertexLLM,
            )
        except Exception as e:
            raise VertexAIError(
                status_code=400,
                message=f"""vertexai import failed please run `pip install -U "google-cloud-aiplatform>=1.38"`. Got error: {e}""",
            )

        if not (
            hasattr(vertexai, "preview") or hasattr(vertexai.preview, "language_models")
        ):
            raise VertexAIError(
                status_code=400,
                message="""Upgrade vertex ai. Run `pip install "google-cloud-aiplatform>=1.38"`""",
            )
        try:
            model = model.replace("openai/", "")
            vertex_httpx_logic = VertexLLM()

            access_token, project_id = vertex_httpx_logic._ensure_access_token(
                credentials=vertex_credentials,
                project_id=vertex_project,
                custom_llm_provider="vertex_ai",
            )

            openai_like_chat_completions = OpenAILikeChatHandler()

            ## CONSTRUCT API BASE
            stream: bool = optional_params.get("stream", False) or False
            optional_params["stream"] = stream
            default_api_base = create_vertex_url(
                vertex_location=vertex_location or "us-central1",
                vertex_project=vertex_project or project_id,
                stream=stream,
                model=model,
            )

            if len(default_api_base.split(":")) > 1:
                endpoint = default_api_base.split(":")[-1]
            else:
                endpoint = ""

            _, api_base = self._check_custom_proxy(
                api_base=api_base,
                custom_llm_provider="vertex_ai",
                gemini_api_key=None,
                endpoint=endpoint,
                stream=stream,
                auth_header=None,
                url=default_api_base,
            )
            model = ""
            return openai_like_chat_completions.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                api_key=access_token,
                custom_prompt_dict=custom_prompt_dict,
                model_response=model_response,
                print_verbose=print_verbose,
                logging_obj=logging_obj,
                optional_params=optional_params,
                acompletion=acompletion,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                client=client,
                timeout=timeout,
                encoding=encoding,
                custom_llm_provider="vertex_ai",
            )

        except Exception as e:
            raise VertexAIError(status_code=500, message=str(e))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\voyage\embedding\transformation.py ===
from typing import List, Optional, Union

import httpx

from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.base_llm.embedding.transformation import BaseEmbeddingConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllEmbeddingInputValues, AllMessageValues
from litellm.types.utils import EmbeddingResponse, Usage


class VoyageError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Union[dict, httpx.Headers] = {},
    ):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url="https://api.voyageai.com/v1/embeddings"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            status_code=status_code,
            message=message,
            headers=headers,
        )


class VoyageEmbeddingConfig(BaseEmbeddingConfig):
    """
    Reference: https://docs.voyageai.com/reference/embeddings-api
    """

    def __init__(self) -> None:
        pass

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        if api_base:
            if not api_base.endswith("/embeddings"):
                api_base = f"{api_base}/embeddings"
            return api_base
        return "https://api.voyageai.com/v1/embeddings"

    def get_supported_openai_params(self, model: str) -> list:
        return [
            "encoding_format",
            "dimensions",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        Map OpenAI params to Voyage params

        Reference: https://docs.voyageai.com/reference/embeddings-api
        """
        if "encoding_format" in non_default_params:
            optional_params["encoding_format"] = non_default_params["encoding_format"]
        if "dimensions" in non_default_params:
            optional_params["output_dimension"] = non_default_params["dimensions"]
        return optional_params

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
        if api_key is None:
            api_key = (
                get_secret_str("VOYAGE_API_KEY")
                or get_secret_str("VOYAGE_AI_API_KEY")
                or get_secret_str("VOYAGE_AI_TOKEN")
            )
        return {
            "Authorization": f"Bearer {api_key}",
        }

    def transform_embedding_request(
        self,
        model: str,
        input: AllEmbeddingInputValues,
        optional_params: dict,
        headers: dict,
    ) -> dict:
        return {
            "input": input,
            "model": model,
            **optional_params,
        }

    def transform_embedding_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: EmbeddingResponse,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str] = None,
        request_data: dict = {},
        optional_params: dict = {},
        litellm_params: dict = {},
    ) -> EmbeddingResponse:
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise VoyageError(
                message=raw_response.text, status_code=raw_response.status_code
            )

        # model_response.usage
        model_response.model = raw_response_json.get("model")
        model_response.data = raw_response_json.get("data")
        model_response.object = raw_response_json.get("object")

        usage = Usage(
            prompt_tokens=raw_response_json.get("usage", {}).get("total_tokens", 0),
            total_tokens=raw_response_json.get("usage", {}).get("total_tokens", 0),
        )
        model_response.usage = usage
        return model_response

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return VoyageError(
            message=error_message, status_code=status_code, headers=headers
        )

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_inline\image.py ===
# Process ![image](<src> "title")
from __future__ import annotations

from ..common.utils import isStrSpace, normalizeReference
from ..token import Token
from .state_inline import StateInline


def image(state: StateInline, silent: bool) -> bool:
    label = None
    href = ""
    oldPos = state.pos
    max = state.posMax

    if state.src[state.pos] != "!":
        return False

    if state.pos + 1 < state.posMax and state.src[state.pos + 1] != "[":
        return False

    labelStart = state.pos + 2
    labelEnd = state.md.helpers.parseLinkLabel(state, state.pos + 1, False)

    # parser failed to find ']', so it's not a valid link
    if labelEnd < 0:
        return False

    pos = labelEnd + 1

    if pos < max and state.src[pos] == "(":
        #
        # Inline link
        #

        # [link](  <href>  "title"  )
        #        ^^ skipping these spaces
        pos += 1
        while pos < max:
            ch = state.src[pos]
            if not isStrSpace(ch) and ch != "\n":
                break
            pos += 1

        if pos >= max:
            return False

        # [link](  <href>  "title"  )
        #          ^^^^^^ parsing link destination
        start = pos
        res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax)
        if res.ok:
            href = state.md.normalizeLink(res.str)
            if state.md.validateLink(href):
                pos = res.pos
            else:
                href = ""

        # [link](  <href>  "title"  )
        #                ^^ skipping these spaces
        start = pos
        while pos < max:
            ch = state.src[pos]
            if not isStrSpace(ch) and ch != "\n":
                break
            pos += 1

        # [link](  <href>  "title"  )
        #                  ^^^^^^^ parsing link title
        res = state.md.helpers.parseLinkTitle(state.src, pos, state.posMax)
        if pos < max and start != pos and res.ok:
            title = res.str
            pos = res.pos

            # [link](  <href>  "title"  )
            #                         ^^ skipping these spaces
            while pos < max:
                ch = state.src[pos]
                if not isStrSpace(ch) and ch != "\n":
                    break
                pos += 1
        else:
            title = ""

        if pos >= max or state.src[pos] != ")":
            state.pos = oldPos
            return False

        pos += 1

    else:
        #
        # Link reference
        #
        if "references" not in state.env:
            return False

        # /* [ */
        if pos < max and state.src[pos] == "[":
            start = pos + 1
            pos = state.md.helpers.parseLinkLabel(state, pos)
            if pos >= 0:
                label = state.src[start:pos]
                pos += 1
            else:
                pos = labelEnd + 1
        else:
            pos = labelEnd + 1

        # covers label == '' and label == undefined
        # (collapsed reference link and shortcut reference link respectively)
        if not label:
            label = state.src[labelStart:labelEnd]

        label = normalizeReference(label)

        ref = state.env["references"].get(label, None)
        if not ref:
            state.pos = oldPos
            return False

        href = ref["href"]
        title = ref["title"]

    #
    # We found the end of the link, and know for a fact it's a valid link
    # so all that's left to do is to call tokenizer.
    #
    if not silent:
        content = state.src[labelStart:labelEnd]

        tokens: list[Token] = []
        state.md.inline.parse(content, state.md, state.env, tokens)

        token = state.push("image", "img", 0)
        token.attrs = {"src": href, "alt": ""}
        token.children = tokens or None
        token.content = content

        if title:
            token.attrSet("title", title)

        # note, this is not part of markdown-it JS, but is useful for renderers
        if label and state.md.options.get("store_labels", False):
            token.meta["label"] = label

    state.pos = pos
    state.posMax = max
    return True

# === NexusCore/openenv\Lib\site-packages\nltk\sem\skolemize.py ===
# Natural Language Toolkit: Semantic Interpretation
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.sem.logic import (
    AllExpression,
    AndExpression,
    ApplicationExpression,
    EqualityExpression,
    ExistsExpression,
    IffExpression,
    ImpExpression,
    NegatedExpression,
    OrExpression,
    VariableExpression,
    skolem_function,
    unique_variable,
)


def skolemize(expression, univ_scope=None, used_variables=None):
    """
    Skolemize the expression and convert to conjunctive normal form (CNF)
    """
    if univ_scope is None:
        univ_scope = set()
    if used_variables is None:
        used_variables = set()

    if isinstance(expression, AllExpression):
        term = skolemize(
            expression.term,
            univ_scope | {expression.variable},
            used_variables | {expression.variable},
        )
        return term.replace(
            expression.variable,
            VariableExpression(unique_variable(ignore=used_variables)),
        )
    elif isinstance(expression, AndExpression):
        return skolemize(expression.first, univ_scope, used_variables) & skolemize(
            expression.second, univ_scope, used_variables
        )
    elif isinstance(expression, OrExpression):
        return to_cnf(
            skolemize(expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, ImpExpression):
        return to_cnf(
            skolemize(-expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, IffExpression):
        return to_cnf(
            skolemize(-expression.first, univ_scope, used_variables),
            skolemize(expression.second, univ_scope, used_variables),
        ) & to_cnf(
            skolemize(expression.first, univ_scope, used_variables),
            skolemize(-expression.second, univ_scope, used_variables),
        )
    elif isinstance(expression, EqualityExpression):
        return expression
    elif isinstance(expression, NegatedExpression):
        negated = expression.term
        if isinstance(negated, AllExpression):
            term = skolemize(
                -negated.term, univ_scope, used_variables | {negated.variable}
            )
            if univ_scope:
                return term.replace(negated.variable, skolem_function(univ_scope))
            else:
                skolem_constant = VariableExpression(
                    unique_variable(ignore=used_variables)
                )
                return term.replace(negated.variable, skolem_constant)
        elif isinstance(negated, AndExpression):
            return to_cnf(
                skolemize(-negated.first, univ_scope, used_variables),
                skolemize(-negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, OrExpression):
            return skolemize(-negated.first, univ_scope, used_variables) & skolemize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, ImpExpression):
            return skolemize(negated.first, univ_scope, used_variables) & skolemize(
                -negated.second, univ_scope, used_variables
            )
        elif isinstance(negated, IffExpression):
            return to_cnf(
                skolemize(-negated.first, univ_scope, used_variables),
                skolemize(-negated.second, univ_scope, used_variables),
            ) & to_cnf(
                skolemize(negated.first, univ_scope, used_variables),
                skolemize(negated.second, univ_scope, used_variables),
            )
        elif isinstance(negated, EqualityExpression):
            return expression
        elif isinstance(negated, NegatedExpression):
            return skolemize(negated.term, univ_scope, used_variables)
        elif isinstance(negated, ExistsExpression):
            term = skolemize(
                -negated.term,
                univ_scope | {negated.variable},
                used_variables | {negated.variable},
            )
            return term.replace(
                negated.variable,
                VariableExpression(unique_variable(ignore=used_variables)),
            )
        elif isinstance(negated, ApplicationExpression):
            return expression
        else:
            raise Exception("'%s' cannot be skolemized" % expression)
    elif isinstance(expression, ExistsExpression):
        term = skolemize(
            expression.term, univ_scope, used_variables | {expression.variable}
        )
        if univ_scope:
            return term.replace(expression.variable, skolem_function(univ_scope))
        else:
            skolem_constant = VariableExpression(unique_variable(ignore=used_variables))
            return term.replace(expression.variable, skolem_constant)
    elif isinstance(expression, ApplicationExpression):
        return expression
    else:
        raise Exception("'%s' cannot be skolemized" % expression)


def to_cnf(first, second):
    """
    Convert this split disjunction to conjunctive normal form (CNF)
    """
    if isinstance(first, AndExpression):
        r_first = to_cnf(first.first, second)
        r_second = to_cnf(first.second, second)
        return r_first & r_second
    elif isinstance(second, AndExpression):
        r_first = to_cnf(first, second.first)
        r_second = to_cnf(first, second.second)
        return r_first & r_second
    else:
        return first | second

# === NexusCore/openenv\Lib\site-packages\numpy\_typing\__init__.py ===
"""Private counterpart of ``numpy.typing``."""

from ._array_like import ArrayLike as ArrayLike
from ._array_like import NDArray as NDArray
from ._array_like import _ArrayLike as _ArrayLike
from ._array_like import _ArrayLikeAnyString_co as _ArrayLikeAnyString_co
from ._array_like import _ArrayLikeBool_co as _ArrayLikeBool_co
from ._array_like import _ArrayLikeBytes_co as _ArrayLikeBytes_co
from ._array_like import _ArrayLikeComplex128_co as _ArrayLikeComplex128_co
from ._array_like import _ArrayLikeComplex_co as _ArrayLikeComplex_co
from ._array_like import _ArrayLikeDT64_co as _ArrayLikeDT64_co
from ._array_like import _ArrayLikeFloat64_co as _ArrayLikeFloat64_co
from ._array_like import _ArrayLikeFloat_co as _ArrayLikeFloat_co
from ._array_like import _ArrayLikeInt as _ArrayLikeInt
from ._array_like import _ArrayLikeInt_co as _ArrayLikeInt_co
from ._array_like import _ArrayLikeNumber_co as _ArrayLikeNumber_co
from ._array_like import _ArrayLikeObject_co as _ArrayLikeObject_co
from ._array_like import _ArrayLikeStr_co as _ArrayLikeStr_co
from ._array_like import _ArrayLikeString_co as _ArrayLikeString_co
from ._array_like import _ArrayLikeTD64_co as _ArrayLikeTD64_co
from ._array_like import _ArrayLikeUInt_co as _ArrayLikeUInt_co
from ._array_like import _ArrayLikeVoid_co as _ArrayLikeVoid_co
from ._array_like import _FiniteNestedSequence as _FiniteNestedSequence
from ._array_like import _SupportsArray as _SupportsArray
from ._array_like import _SupportsArrayFunc as _SupportsArrayFunc

#
from ._char_codes import _BoolCodes as _BoolCodes
from ._char_codes import _ByteCodes as _ByteCodes
from ._char_codes import _BytesCodes as _BytesCodes
from ._char_codes import _CDoubleCodes as _CDoubleCodes
from ._char_codes import _CharacterCodes as _CharacterCodes
from ._char_codes import _CLongDoubleCodes as _CLongDoubleCodes
from ._char_codes import _Complex64Codes as _Complex64Codes
from ._char_codes import _Complex128Codes as _Complex128Codes
from ._char_codes import _ComplexFloatingCodes as _ComplexFloatingCodes
from ._char_codes import _CSingleCodes as _CSingleCodes
from ._char_codes import _DoubleCodes as _DoubleCodes
from ._char_codes import _DT64Codes as _DT64Codes
from ._char_codes import _FlexibleCodes as _FlexibleCodes
from ._char_codes import _Float16Codes as _Float16Codes
from ._char_codes import _Float32Codes as _Float32Codes
from ._char_codes import _Float64Codes as _Float64Codes
from ._char_codes import _FloatingCodes as _FloatingCodes
from ._char_codes import _GenericCodes as _GenericCodes
from ._char_codes import _HalfCodes as _HalfCodes
from ._char_codes import _InexactCodes as _InexactCodes
from ._char_codes import _Int8Codes as _Int8Codes
from ._char_codes import _Int16Codes as _Int16Codes
from ._char_codes import _Int32Codes as _Int32Codes
from ._char_codes import _Int64Codes as _Int64Codes
from ._char_codes import _IntCCodes as _IntCCodes
from ._char_codes import _IntCodes as _IntCodes
from ._char_codes import _IntegerCodes as _IntegerCodes
from ._char_codes import _IntPCodes as _IntPCodes
from ._char_codes import _LongCodes as _LongCodes
from ._char_codes import _LongDoubleCodes as _LongDoubleCodes
from ._char_codes import _LongLongCodes as _LongLongCodes
from ._char_codes import _NumberCodes as _NumberCodes
from ._char_codes import _ObjectCodes as _ObjectCodes
from ._char_codes import _ShortCodes as _ShortCodes
from ._char_codes import _SignedIntegerCodes as _SignedIntegerCodes
from ._char_codes import _SingleCodes as _SingleCodes
from ._char_codes import _StrCodes as _StrCodes
from ._char_codes import _StringCodes as _StringCodes
from ._char_codes import _TD64Codes as _TD64Codes
from ._char_codes import _UByteCodes as _UByteCodes
from ._char_codes import _UInt8Codes as _UInt8Codes
from ._char_codes import _UInt16Codes as _UInt16Codes
from ._char_codes import _UInt32Codes as _UInt32Codes
from ._char_codes import _UInt64Codes as _UInt64Codes
from ._char_codes import _UIntCCodes as _UIntCCodes
from ._char_codes import _UIntCodes as _UIntCodes
from ._char_codes import _UIntPCodes as _UIntPCodes
from ._char_codes import _ULongCodes as _ULongCodes
from ._char_codes import _ULongLongCodes as _ULongLongCodes
from ._char_codes import _UnsignedIntegerCodes as _UnsignedIntegerCodes
from ._char_codes import _UShortCodes as _UShortCodes
from ._char_codes import _VoidCodes as _VoidCodes

#
from ._dtype_like import DTypeLike as DTypeLike
from ._dtype_like import _DTypeLike as _DTypeLike
from ._dtype_like import _DTypeLikeBool as _DTypeLikeBool
from ._dtype_like import _DTypeLikeBytes as _DTypeLikeBytes
from ._dtype_like import _DTypeLikeComplex as _DTypeLikeComplex
from ._dtype_like import _DTypeLikeComplex_co as _DTypeLikeComplex_co
from ._dtype_like import _DTypeLikeDT64 as _DTypeLikeDT64
from ._dtype_like import _DTypeLikeFloat as _DTypeLikeFloat
from ._dtype_like import _DTypeLikeInt as _DTypeLikeInt
from ._dtype_like import _DTypeLikeObject as _DTypeLikeObject
from ._dtype_like import _DTypeLikeStr as _DTypeLikeStr
from ._dtype_like import _DTypeLikeTD64 as _DTypeLikeTD64
from ._dtype_like import _DTypeLikeUInt as _DTypeLikeUInt
from ._dtype_like import _DTypeLikeVoid as _DTypeLikeVoid
from ._dtype_like import _SupportsDType as _SupportsDType
from ._dtype_like import _VoidDTypeLike as _VoidDTypeLike

#
from ._nbit import _NBitByte as _NBitByte
from ._nbit import _NBitDouble as _NBitDouble
from ._nbit import _NBitHalf as _NBitHalf
from ._nbit import _NBitInt as _NBitInt
from ._nbit import _NBitIntC as _NBitIntC
from ._nbit import _NBitIntP as _NBitIntP
from ._nbit import _NBitLong as _NBitLong
from ._nbit import _NBitLongDouble as _NBitLongDouble
from ._nbit import _NBitLongLong as _NBitLongLong
from ._nbit import _NBitShort as _NBitShort
from ._nbit import _NBitSingle as _NBitSingle

#
from ._nbit_base import (
    NBitBase as NBitBase,  # type: ignore[deprecated]  # pyright: ignore[reportDeprecated]
)
from ._nbit_base import _8Bit as _8Bit
from ._nbit_base import _16Bit as _16Bit
from ._nbit_base import _32Bit as _32Bit
from ._nbit_base import _64Bit as _64Bit
from ._nbit_base import _96Bit as _96Bit
from ._nbit_base import _128Bit as _128Bit

#
from ._nested_sequence import _NestedSequence as _NestedSequence

#
from ._scalars import _BoolLike_co as _BoolLike_co
from ._scalars import _CharLike_co as _CharLike_co
from ._scalars import _ComplexLike_co as _ComplexLike_co
from ._scalars import _FloatLike_co as _FloatLike_co
from ._scalars import _IntLike_co as _IntLike_co
from ._scalars import _NumberLike_co as _NumberLike_co
from ._scalars import _ScalarLike_co as _ScalarLike_co
from ._scalars import _TD64Like_co as _TD64Like_co
from ._scalars import _UIntLike_co as _UIntLike_co
from ._scalars import _VoidLike_co as _VoidLike_co

#
from ._shape import _AnyShape as _AnyShape
from ._shape import _Shape as _Shape
from ._shape import _ShapeLike as _ShapeLike

#
from ._ufunc import _GUFunc_Nin2_Nout1 as _GUFunc_Nin2_Nout1
from ._ufunc import _UFunc_Nin1_Nout1 as _UFunc_Nin1_Nout1
from ._ufunc import _UFunc_Nin1_Nout2 as _UFunc_Nin1_Nout2
from ._ufunc import _UFunc_Nin2_Nout1 as _UFunc_Nin2_Nout1
from ._ufunc import _UFunc_Nin2_Nout2 as _UFunc_Nin2_Nout2

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\tcl.py ===
"""
    pygments.lexers.tcl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for Tcl and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Whitespace
from pygments.util import shebang_matches

__all__ = ['TclLexer']


class TclLexer(RegexLexer):
    """
    For Tcl source code.
    """

    keyword_cmds_re = words((
        'after', 'apply', 'array', 'break', 'catch', 'continue', 'elseif',
        'else', 'error', 'eval', 'expr', 'for', 'foreach', 'global', 'if',
        'namespace', 'proc', 'rename', 'return', 'set', 'switch', 'then',
        'trace', 'unset', 'update', 'uplevel', 'upvar', 'variable', 'vwait',
        'while'), prefix=r'\b', suffix=r'\b')

    builtin_cmds_re = words((
        'append', 'bgerror', 'binary', 'cd', 'chan', 'clock', 'close',
        'concat', 'dde', 'dict', 'encoding', 'eof', 'exec', 'exit', 'fblocked',
        'fconfigure', 'fcopy', 'file', 'fileevent', 'flush', 'format', 'gets',
        'glob', 'history', 'http', 'incr', 'info', 'interp', 'join', 'lappend',
        'lassign', 'lindex', 'linsert', 'list', 'llength', 'load', 'loadTk',
        'lrange', 'lrepeat', 'lreplace', 'lreverse', 'lsearch', 'lset', 'lsort',
        'mathfunc', 'mathop', 'memory', 'msgcat', 'open', 'package', 'pid',
        'pkg::create', 'pkg_mkIndex', 'platform', 'platform::shell', 'puts',
        'pwd', 're_syntax', 'read', 'refchan', 'regexp', 'registry', 'regsub',
        'scan', 'seek', 'socket', 'source', 'split', 'string', 'subst', 'tell',
        'time', 'tm', 'unknown', 'unload'), prefix=r'\b', suffix=r'\b')

    name = 'Tcl'
    url = 'https://www.tcl.tk/about/language.html'
    aliases = ['tcl']
    filenames = ['*.tcl', '*.rvt']
    mimetypes = ['text/x-tcl', 'text/x-script.tcl', 'application/x-tcl']
    version_added = '0.10'

    def _gen_command_rules(keyword_cmds_re, builtin_cmds_re, context=""):
        return [
            (keyword_cmds_re, Keyword, 'params' + context),
            (builtin_cmds_re, Name.Builtin, 'params' + context),
            (r'([\w.-]+)', Name.Variable, 'params' + context),
            (r'#', Comment, 'comment'),
        ]

    tokens = {
        'root': [
            include('command'),
            include('basic'),
            include('data'),
            (r'\}', Keyword),  # HACK: somehow we miscounted our braces
        ],
        'command': _gen_command_rules(keyword_cmds_re, builtin_cmds_re),
        'command-in-brace': _gen_command_rules(keyword_cmds_re,
                                               builtin_cmds_re,
                                               "-in-brace"),
        'command-in-bracket': _gen_command_rules(keyword_cmds_re,
                                                 builtin_cmds_re,
                                                 "-in-bracket"),
        'command-in-paren': _gen_command_rules(keyword_cmds_re,
                                               builtin_cmds_re,
                                               "-in-paren"),
        'basic': [
            (r'\(', Keyword, 'paren'),
            (r'\[', Keyword, 'bracket'),
            (r'\{', Keyword, 'brace'),
            (r'"', String.Double, 'string'),
            (r'(eq|ne|in|ni)\b', Operator.Word),
            (r'!=|==|<<|>>|<=|>=|&&|\|\||\*\*|[-+~!*/%<>&^|?:]', Operator),
        ],
        'data': [
            (r'\s+', Whitespace),
            (r'0x[a-fA-F0-9]+', Number.Hex),
            (r'0[0-7]+', Number.Oct),
            (r'\d+\.\d+', Number.Float),
            (r'\d+', Number.Integer),
            (r'\$[\w.:-]+', Name.Variable),
            (r'\$\{[\w.:-]+\}', Name.Variable),
            (r'[\w.,@:-]+', Text),
        ],
        'params': [
            (r';', Keyword, '#pop'),
            (r'\n', Text, '#pop'),
            (r'(else|elseif|then)\b', Keyword),
            include('basic'),
            include('data'),
        ],
        'params-in-brace': [
            (r'\}', Keyword, ('#pop', '#pop')),
            include('params')
        ],
        'params-in-paren': [
            (r'\)', Keyword, ('#pop', '#pop')),
            include('params')
        ],
        'params-in-bracket': [
            (r'\]', Keyword, ('#pop', '#pop')),
            include('params')
        ],
        'string': [
            (r'\[', String.Double, 'string-square'),
            (r'(?s)(\\\\|\\[0-7]+|\\.|[^"\\])', String.Double),
            (r'"', String.Double, '#pop')
        ],
        'string-square': [
            (r'\[', String.Double, 'string-square'),
            (r'(?s)(\\\\|\\[0-7]+|\\.|\\\n|[^\]\\])', String.Double),
            (r'\]', String.Double, '#pop')
        ],
        'brace': [
            (r'\}', Keyword, '#pop'),
            include('command-in-brace'),
            include('basic'),
            include('data'),
        ],
        'paren': [
            (r'\)', Keyword, '#pop'),
            include('command-in-paren'),
            include('basic'),
            include('data'),
        ],
        'bracket': [
            (r'\]', Keyword, '#pop'),
            include('command-in-bracket'),
            include('basic'),
            include('data'),
        ],
        'comment': [
            (r'.*[^\\]\n', Comment, '#pop'),
            (r'.*\\\n', Comment),
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'(tcl)')

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32pipe.py ===
import threading
import time
import unittest

import pywintypes
import win32con
import win32event
import win32file
import win32pipe
import winerror


class PipeTests(unittest.TestCase):
    pipename = "\\\\.\\pipe\\python_test_pipe"

    def _serverThread(self, pipe_handle, event, wait_time):
        # just do one connection and terminate.
        hr = win32pipe.ConnectNamedPipe(pipe_handle)
        self.assertTrue(
            hr in (0, winerror.ERROR_PIPE_CONNECTED), f"Got error code 0x{hr:x}"
        )
        hr, got = win32file.ReadFile(pipe_handle, 100)
        self.assertEqual(got, b"foo\0bar")
        time.sleep(wait_time)
        win32file.WriteFile(pipe_handle, b"bar\0foo")
        pipe_handle.Close()
        event.set()

    def startPipeServer(self, event, wait_time=0):
        openMode = win32pipe.PIPE_ACCESS_DUPLEX
        pipeMode = win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT

        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.SetSecurityDescriptorDacl(1, None, 0)

        pipe_handle = win32pipe.CreateNamedPipe(
            self.pipename,
            openMode,
            pipeMode,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            0,
            0,
            2000,
            sa,
        )

        threading.Thread(
            target=self._serverThread, args=(pipe_handle, event, wait_time)
        ).start()

    def testCallNamedPipe(self):
        event = threading.Event()
        self.startPipeServer(event)

        got = win32pipe.CallNamedPipe(
            self.pipename, b"foo\0bar", 1024, win32pipe.NMPWAIT_WAIT_FOREVER
        )
        self.assertEqual(got, b"bar\0foo")
        event.wait(5)
        self.assertTrue(event.isSet(), "Pipe server thread didn't terminate")

    def testTransactNamedPipeBlocking(self):
        event = threading.Event()
        self.startPipeServer(event)
        open_mode = win32con.GENERIC_READ | win32con.GENERIC_WRITE

        hpipe = win32file.CreateFile(
            self.pipename,
            open_mode,
            0,  # no sharing
            None,  # default security
            win32con.OPEN_EXISTING,
            0,  # win32con.FILE_FLAG_OVERLAPPED,
            None,
        )

        # set to message mode.
        win32pipe.SetNamedPipeHandleState(
            hpipe, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )

        hr, got = win32pipe.TransactNamedPipe(hpipe, b"foo\0bar", 1024, None)
        self.assertEqual(got, b"bar\0foo")
        event.wait(5)
        self.assertTrue(event.isSet(), "Pipe server thread didn't terminate")

    def testTransactNamedPipeBlockingBuffer(self):
        # Like testTransactNamedPipeBlocking, but a pre-allocated buffer is
        # passed (not really that useful, but it exercises the code path)
        event = threading.Event()
        self.startPipeServer(event)
        open_mode = win32con.GENERIC_READ | win32con.GENERIC_WRITE

        hpipe = win32file.CreateFile(
            self.pipename,
            open_mode,
            0,  # no sharing
            None,  # default security
            win32con.OPEN_EXISTING,
            0,  # win32con.FILE_FLAG_OVERLAPPED,
            None,
        )

        # set to message mode.
        win32pipe.SetNamedPipeHandleState(
            hpipe, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )

        buffer = win32file.AllocateReadBuffer(1024)
        hr, got = win32pipe.TransactNamedPipe(hpipe, b"foo\0bar", buffer, None)
        self.assertEqual(got, b"bar\0foo")
        event.wait(5)
        self.assertTrue(event.isSet(), "Pipe server thread didn't terminate")

    def testTransactNamedPipeAsync(self):
        event = threading.Event()
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        self.startPipeServer(event, 0.5)
        open_mode = win32con.GENERIC_READ | win32con.GENERIC_WRITE

        hpipe = win32file.CreateFile(
            self.pipename,
            open_mode,
            0,  # no sharing
            None,  # default security
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_OVERLAPPED,
            None,
        )

        # set to message mode.
        win32pipe.SetNamedPipeHandleState(
            hpipe, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )

        buffer = win32file.AllocateReadBuffer(1024)
        hr, got = win32pipe.TransactNamedPipe(hpipe, b"foo\0bar", buffer, overlapped)
        self.assertEqual(hr, winerror.ERROR_IO_PENDING)
        nbytes = win32file.GetOverlappedResult(hpipe, overlapped, True)
        got = buffer[:nbytes]
        self.assertEqual(got, b"bar\0foo")
        event.wait(5)
        self.assertTrue(event.isSet(), "Pipe server thread didn't terminate")


if __name__ == "__main__":
    unittest.main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\hashes.py ===
import hashlib
from typing import TYPE_CHECKING, BinaryIO, Dict, Iterable, List, NoReturn, Optional

from pip._internal.exceptions import HashMismatch, HashMissing, InstallationError
from pip._internal.utils.misc import read_chunks

if TYPE_CHECKING:
    from hashlib import _Hash


# The recommended hash algo of the moment. Change this whenever the state of
# the art changes; it won't hurt backward compatibility.
FAVORITE_HASH = "sha256"


# Names of hashlib algorithms allowed by the --hash option and ``pip hash``
# Currently, those are the ones at least as collision-resistant as sha256.
STRONG_HASHES = ["sha256", "sha384", "sha512"]


class Hashes:
    """A wrapper that builds multiple hashes at once and checks them against
    known-good values

    """

    def __init__(self, hashes: Optional[Dict[str, List[str]]] = None) -> None:
        """
        :param hashes: A dict of algorithm names pointing to lists of allowed
            hex digests
        """
        allowed = {}
        if hashes is not None:
            for alg, keys in hashes.items():
                # Make sure values are always sorted (to ease equality checks)
                allowed[alg] = [k.lower() for k in sorted(keys)]
        self._allowed = allowed

    def __and__(self, other: "Hashes") -> "Hashes":
        if not isinstance(other, Hashes):
            return NotImplemented

        # If either of the Hashes object is entirely empty (i.e. no hash
        # specified at all), all hashes from the other object are allowed.
        if not other:
            return self
        if not self:
            return other

        # Otherwise only hashes that present in both objects are allowed.
        new = {}
        for alg, values in other._allowed.items():
            if alg not in self._allowed:
                continue
            new[alg] = [v for v in values if v in self._allowed[alg]]
        return Hashes(new)

    @property
    def digest_count(self) -> int:
        return sum(len(digests) for digests in self._allowed.values())

    def is_hash_allowed(self, hash_name: str, hex_digest: str) -> bool:
        """Return whether the given hex digest is allowed."""
        return hex_digest in self._allowed.get(hash_name, [])

    def check_against_chunks(self, chunks: Iterable[bytes]) -> None:
        """Check good hashes against ones built from iterable of chunks of
        data.

        Raise HashMismatch if none match.

        """
        gots = {}
        for hash_name in self._allowed.keys():
            try:
                gots[hash_name] = hashlib.new(hash_name)
            except (ValueError, TypeError):
                raise InstallationError(f"Unknown hash name: {hash_name}")

        for chunk in chunks:
            for hash in gots.values():
                hash.update(chunk)

        for hash_name, got in gots.items():
            if got.hexdigest() in self._allowed[hash_name]:
                return
        self._raise(gots)

    def _raise(self, gots: Dict[str, "_Hash"]) -> "NoReturn":
        raise HashMismatch(self._allowed, gots)

    def check_against_file(self, file: BinaryIO) -> None:
        """Check good hashes against a file-like object

        Raise HashMismatch if none match.

        """
        return self.check_against_chunks(read_chunks(file))

    def check_against_path(self, path: str) -> None:
        with open(path, "rb") as file:
            return self.check_against_file(file)

    def has_one_of(self, hashes: Dict[str, str]) -> bool:
        """Return whether any of the given hashes are allowed."""
        for hash_name, hex_digest in hashes.items():
            if self.is_hash_allowed(hash_name, hex_digest):
                return True
        return False

    def __bool__(self) -> bool:
        """Return whether I know any known-good hashes."""
        return bool(self._allowed)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hashes):
            return NotImplemented
        return self._allowed == other._allowed

    def __hash__(self) -> int:
        return hash(
            ",".join(
                sorted(
                    ":".join((alg, digest))
                    for alg, digest_list in self._allowed.items()
                    for digest in digest_list
                )
            )
        )


class MissingHashes(Hashes):
    """A workalike for Hashes used when we're missing a hash for a requirement

    It computes the actual hash of the requirement and raises a HashMissing
    exception showing it to the user.

    """

    def __init__(self) -> None:
        """Don't offer the ``hashes`` kwarg."""
        # Pass our favorite hash in to generate a "gotten hash". With the
        # empty list, it will never match, so an error will always raise.
        super().__init__(hashes={FAVORITE_HASH: []})

    def _raise(self, gots: Dict[str, "_Hash"]) -> "NoReturn":
        raise HashMissing(gots[FAVORITE_HASH].hexdigest())

# === NexusCore/openenv\Lib\site-packages\markdown_it\parser_inline.py ===
"""Tokenizes paragraph content.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from . import rules_inline
from .ruler import Ruler
from .rules_inline.state_inline import StateInline
from .token import Token
from .utils import EnvType

if TYPE_CHECKING:
    from markdown_it import MarkdownIt


# Parser rules
RuleFuncInlineType = Callable[[StateInline, bool], bool]
"""(state: StateInline, silent: bool) -> matched: bool)

`silent` disables token generation, useful for lookahead.
"""
_rules: list[tuple[str, RuleFuncInlineType]] = [
    ("text", rules_inline.text),
    ("linkify", rules_inline.linkify),
    ("newline", rules_inline.newline),
    ("escape", rules_inline.escape),
    ("backticks", rules_inline.backtick),
    ("strikethrough", rules_inline.strikethrough.tokenize),
    ("emphasis", rules_inline.emphasis.tokenize),
    ("link", rules_inline.link),
    ("image", rules_inline.image),
    ("autolink", rules_inline.autolink),
    ("html_inline", rules_inline.html_inline),
    ("entity", rules_inline.entity),
]

# Note `rule2` ruleset was created specifically for emphasis/strikethrough
# post-processing and may be changed in the future.
#
# Don't use this for anything except pairs (plugins working with `balance_pairs`).
#
RuleFuncInline2Type = Callable[[StateInline], None]
_rules2: list[tuple[str, RuleFuncInline2Type]] = [
    ("balance_pairs", rules_inline.link_pairs),
    ("strikethrough", rules_inline.strikethrough.postProcess),
    ("emphasis", rules_inline.emphasis.postProcess),
    # rules for pairs separate '**' into its own text tokens, which may be left unused,
    # rule below merges unused segments back with the rest of the text
    ("fragments_join", rules_inline.fragments_join),
]


class ParserInline:
    def __init__(self) -> None:
        self.ruler = Ruler[RuleFuncInlineType]()
        for name, rule in _rules:
            self.ruler.push(name, rule)
        # Second ruler used for post-processing (e.g. in emphasis-like rules)
        self.ruler2 = Ruler[RuleFuncInline2Type]()
        for name, rule2 in _rules2:
            self.ruler2.push(name, rule2)

    def skipToken(self, state: StateInline) -> None:
        """Skip single token by running all rules in validation mode;
        returns `True` if any rule reported success
        """
        ok = False
        pos = state.pos
        rules = self.ruler.getRules("")
        maxNesting = state.md.options["maxNesting"]
        cache = state.cache

        if pos in cache:
            state.pos = cache[pos]
            return

        if state.level < maxNesting:
            for rule in rules:
                #  Increment state.level and decrement it later to limit recursion.
                # It's harmless to do here, because no tokens are created.
                # But ideally, we'd need a separate private state variable for this purpose.
                state.level += 1
                ok = rule(state, True)
                state.level -= 1
                if ok:
                    break
        else:
            # Too much nesting, just skip until the end of the paragraph.
            #
            # NOTE: this will cause links to behave incorrectly in the following case,
            #       when an amount of `[` is exactly equal to `maxNesting + 1`:
            #
            #       [[[[[[[[[[[[[[[[[[[[[foo]()
            #
            # TODO: remove this workaround when CM standard will allow nested links
            #       (we can replace it by preventing links from being parsed in
            #       validation mode)
            #
            state.pos = state.posMax

        if not ok:
            state.pos += 1
        cache[pos] = state.pos

    def tokenize(self, state: StateInline) -> None:
        """Generate tokens for input range."""
        ok = False
        rules = self.ruler.getRules("")
        end = state.posMax
        maxNesting = state.md.options["maxNesting"]

        while state.pos < end:
            # Try all possible rules.
            # On success, rule should:
            #
            # - update `state.pos`
            # - update `state.tokens`
            # - return true

            if state.level < maxNesting:
                for rule in rules:
                    ok = rule(state, False)
                    if ok:
                        break

            if ok:
                if state.pos >= end:
                    break
                continue

            state.pending += state.src[state.pos]
            state.pos += 1

        if state.pending:
            state.pushPending()

    def parse(
        self, src: str, md: MarkdownIt, env: EnvType, tokens: list[Token]
    ) -> list[Token]:
        """Process input string and push inline tokens into `tokens`"""
        state = StateInline(src, md, env, tokens)
        self.tokenize(state)
        rules2 = self.ruler2.getRules("")
        for rule in rules2:
            rule(state)
        return state.tokens

# === NexusCore/openenv\Lib\site-packages\matplotlib\stackplot.py ===
"""
Stacked area plot for 1D arrays inspired by Douglas Y'barbo's stackoverflow
answer:
https://stackoverflow.com/q/2225995/

(https://stackoverflow.com/users/66549/doug)
"""

import itertools

import numpy as np

from matplotlib import _api

__all__ = ['stackplot']


def stackplot(axes, x, *args,
              labels=(), colors=None, hatch=None, baseline='zero',
              **kwargs):
    """
    Draw a stacked area plot or a streamgraph.

    Parameters
    ----------
    x : (N,) array-like

    y : (M, N) array-like
        The data can be either stacked or unstacked. Each of the following
        calls is legal::

            stackplot(x, y)  # where y has shape (M, N) e.g. y = [y1, y2, y3, y4]
            stackplot(x, y1, y2, y3, y4)  # where y1, y2, y3, y4 have length N

    baseline : {'zero', 'sym', 'wiggle', 'weighted_wiggle'}
        Method used to calculate the baseline:

        - ``'zero'``: Constant zero baseline, i.e. a simple stacked plot.
        - ``'sym'``:  Symmetric around zero and is sometimes called
          'ThemeRiver'.
        - ``'wiggle'``: Minimizes the sum of the squared slopes.
        - ``'weighted_wiggle'``: Does the same but weights to account for
          size of each layer. It is also called 'Streamgraph'-layout. More
          details can be found at http://leebyron.com/streamgraph/.

    labels : list of str, optional
        A sequence of labels to assign to each data series. If unspecified,
        then no labels will be applied to artists.

    colors : list of :mpltype:`color`, optional
        A sequence of colors to be cycled through and used to color the stacked
        areas. The sequence need not be exactly the same length as the number
        of provided *y*, in which case the colors will repeat from the
        beginning.

        If not specified, the colors from the Axes property cycle will be used.

    hatch : list of str, default: None
        A sequence of hatching styles.  See
        :doc:`/gallery/shapes_and_collections/hatch_style_reference`.
        The sequence will be cycled through for filling the
        stacked areas from bottom to top.
        It need not be exactly the same length as the number
        of provided *y*, in which case the styles will repeat from the
        beginning.

        .. versionadded:: 3.9
           Support for list input

    data : indexable object, optional
        DATA_PARAMETER_PLACEHOLDER

    **kwargs
        All other keyword arguments are passed to `.Axes.fill_between`.

    Returns
    -------
    list of `.PolyCollection`
        A list of `.PolyCollection` instances, one for each element in the
        stacked area plot.
    """

    y = np.vstack(args)

    labels = iter(labels)
    if colors is not None:
        colors = itertools.cycle(colors)
    else:
        colors = (axes._get_lines.get_next_color() for _ in y)

    if hatch is None or isinstance(hatch, str):
        hatch = itertools.cycle([hatch])
    else:
        hatch = itertools.cycle(hatch)

    # Assume data passed has not been 'stacked', so stack it here.
    # We'll need a float buffer for the upcoming calculations.
    stack = np.cumsum(y, axis=0, dtype=np.promote_types(y.dtype, np.float32))

    _api.check_in_list(['zero', 'sym', 'wiggle', 'weighted_wiggle'],
                       baseline=baseline)
    if baseline == 'zero':
        first_line = 0.

    elif baseline == 'sym':
        first_line = -np.sum(y, 0) * 0.5
        stack += first_line[None, :]

    elif baseline == 'wiggle':
        m = y.shape[0]
        first_line = (y * (m - 0.5 - np.arange(m)[:, None])).sum(0)
        first_line /= -m
        stack += first_line

    elif baseline == 'weighted_wiggle':
        total = np.sum(y, 0)
        # multiply by 1/total (or zero) to avoid infinities in the division:
        inv_total = np.zeros_like(total)
        mask = total > 0
        inv_total[mask] = 1.0 / total[mask]
        increase = np.hstack((y[:, 0:1], np.diff(y)))
        below_size = total - stack
        below_size += 0.5 * y
        move_up = below_size * inv_total
        move_up[:, 0] = 0.5
        center = (move_up - 0.5) * increase
        center = np.cumsum(center.sum(0))
        first_line = center - 0.5 * total
        stack += first_line

    # Color between x = 0 and the first array.
    coll = axes.fill_between(x, first_line, stack[0, :],
                             facecolor=next(colors),
                             hatch=next(hatch),
                             label=next(labels, None),
                             **kwargs)
    coll.sticky_edges.y[:] = [0]
    r = [coll]

    # Color between array i-1 and array i
    for i in range(len(y) - 1):
        r.append(axes.fill_between(x, stack[i, :], stack[i + 1, :],
                                   facecolor=next(colors),
                                   hatch=next(hatch),
                                   label=next(labels, None),
                                   **kwargs))
    return r

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc6664.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with some assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# S/MIME Capabilities for Public Key Definitions
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc6664.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5751
from pyasn1_modules import rfc5480
from pyasn1_modules import rfc4055
from pyasn1_modules import rfc3279

MAX = float('inf')


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Imports from RFC 3279

dhpublicnumber = rfc3279.dhpublicnumber

Dss_Parms = rfc3279.Dss_Parms

id_dsa = rfc3279.id_dsa

id_ecPublicKey = rfc3279.id_ecPublicKey

rsaEncryption = rfc3279.rsaEncryption


# Imports from RFC 4055

id_mgf1 = rfc4055.id_mgf1

id_RSAES_OAEP = rfc4055.id_RSAES_OAEP

id_RSASSA_PSS = rfc4055.id_RSASSA_PSS


# Imports from RFC 5480

ECParameters = rfc5480.ECParameters

id_ecDH = rfc5480.id_ecDH

id_ecMQV = rfc5480.id_ecMQV


# RSA

class RSAKeySize(univ.Integer):
    # suggested values are 1024, 2048, 3072, 4096, 7680, 8192, and 15360;
    # however, the integer value is not limited to these suggestions
    pass


class RSAKeyCapabilities(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('minKeySize', RSAKeySize()),
        namedtype.OptionalNamedType('maxKeySize', RSAKeySize())
    )


class RsaSsa_Pss_sig_caps(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('hashAlg', AlgorithmIdentifier()),
        namedtype.OptionalNamedType('maskAlg', AlgorithmIdentifier()),
        namedtype.DefaultedNamedType('trailerField', univ.Integer().subtype(value=1))
    )


# Diffie-Hellman and DSA

class DSAKeySize(univ.Integer):
    subtypeSpec = constraint.SingleValueConstraint(1024, 2048, 3072, 7680, 15360)


class DSAKeyCapabilities(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('keySizes', univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('minKeySize',
                DSAKeySize()),
            namedtype.OptionalNamedType('maxKeySize',
                DSAKeySize()),
            namedtype.OptionalNamedType('maxSizeP',
                univ.Integer().subtype(explicitTag=tag.Tag(
                    tag.tagClassContext, tag.tagFormatSimple, 1))),
            namedtype.OptionalNamedType('maxSizeQ',
                univ.Integer().subtype(explicitTag=tag.Tag(
                    tag.tagClassContext, tag.tagFormatSimple, 2))),
            namedtype.OptionalNamedType('maxSizeG',
                univ.Integer().subtype(explicitTag=tag.Tag(
                    tag.tagClassContext, tag.tagFormatSimple, 3)))
        )).subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('keyParams',
            Dss_Parms().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


# Elliptic Curve

class EC_SMimeCaps(univ.SequenceOf):
    componentType = ECParameters()
    subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


# Update the SMIMECapabilities Attribute Map in rfc5751.py
#
# The map can either include an entry for scap-sa-rsaSSA-PSS or 
# scap-pk-rsaSSA-PSS, but not both.  One is associated with the
# public key and the other is associated with the signature
# algorithm; however, they use the same OID.  If you need the
# other one in your application, copy the map into a local dict,
# adjust as needed, and pass the local dict to the decoder with
# openTypes=your_local_map.

_smimeCapabilityMapUpdate = {
    rsaEncryption: RSAKeyCapabilities(),
    id_RSASSA_PSS: RSAKeyCapabilities(),
    # id_RSASSA_PSS: RsaSsa_Pss_sig_caps(),
    id_RSAES_OAEP: RSAKeyCapabilities(),
    id_dsa: DSAKeyCapabilities(),
    dhpublicnumber: DSAKeyCapabilities(),
    id_ecPublicKey: EC_SMimeCaps(),
    id_ecDH: EC_SMimeCaps(),
    id_ecMQV: EC_SMimeCaps(),
    id_mgf1: AlgorithmIdentifier(),
}

rfc5751.smimeCapabilityMap.update(_smimeCapabilityMapUpdate)

# === NexusCore/openenv\Lib\site-packages\aiohttp\_websocket\helpers.py ===
"""Helpers for WebSocket protocol versions 13 and 8."""

import functools
import re
from struct import Struct
from typing import TYPE_CHECKING, Final, List, Optional, Pattern, Tuple

from ..helpers import NO_EXTENSIONS
from .models import WSHandshakeError

UNPACK_LEN3 = Struct("!Q").unpack_from
UNPACK_CLOSE_CODE = Struct("!H").unpack
PACK_LEN1 = Struct("!BB").pack
PACK_LEN2 = Struct("!BBH").pack
PACK_LEN3 = Struct("!BBQ").pack
PACK_CLOSE_CODE = Struct("!H").pack
PACK_RANDBITS = Struct("!L").pack
MSG_SIZE: Final[int] = 2**14
MASK_LEN: Final[int] = 4

WS_KEY: Final[bytes] = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# Used by _websocket_mask_python
@functools.lru_cache
def _xor_table() -> List[bytes]:
    return [bytes(a ^ b for a in range(256)) for b in range(256)]


def _websocket_mask_python(mask: bytes, data: bytearray) -> None:
    """Websocket masking function.

    `mask` is a `bytes` object of length 4; `data` is a `bytearray`
    object of any length. The contents of `data` are masked with `mask`,
    as specified in section 5.3 of RFC 6455.

    Note that this function mutates the `data` argument.

    This pure-python implementation may be replaced by an optimized
    version when available.

    """
    assert isinstance(data, bytearray), data
    assert len(mask) == 4, mask

    if data:
        _XOR_TABLE = _xor_table()
        a, b, c, d = (_XOR_TABLE[n] for n in mask)
        data[::4] = data[::4].translate(a)
        data[1::4] = data[1::4].translate(b)
        data[2::4] = data[2::4].translate(c)
        data[3::4] = data[3::4].translate(d)


if TYPE_CHECKING or NO_EXTENSIONS:  # pragma: no cover
    websocket_mask = _websocket_mask_python
else:
    try:
        from .mask import _websocket_mask_cython  # type: ignore[import-not-found]

        websocket_mask = _websocket_mask_cython
    except ImportError:  # pragma: no cover
        websocket_mask = _websocket_mask_python


_WS_EXT_RE: Final[Pattern[str]] = re.compile(
    r"^(?:;\s*(?:"
    r"(server_no_context_takeover)|"
    r"(client_no_context_takeover)|"
    r"(server_max_window_bits(?:=(\d+))?)|"
    r"(client_max_window_bits(?:=(\d+))?)))*$"
)

_WS_EXT_RE_SPLIT: Final[Pattern[str]] = re.compile(r"permessage-deflate([^,]+)?")


def ws_ext_parse(extstr: Optional[str], isserver: bool = False) -> Tuple[int, bool]:
    if not extstr:
        return 0, False

    compress = 0
    notakeover = False
    for ext in _WS_EXT_RE_SPLIT.finditer(extstr):
        defext = ext.group(1)
        # Return compress = 15 when get `permessage-deflate`
        if not defext:
            compress = 15
            break
        match = _WS_EXT_RE.match(defext)
        if match:
            compress = 15
            if isserver:
                # Server never fail to detect compress handshake.
                # Server does not need to send max wbit to client
                if match.group(4):
                    compress = int(match.group(4))
                    # Group3 must match if group4 matches
                    # Compress wbit 8 does not support in zlib
                    # If compress level not support,
                    # CONTINUE to next extension
                    if compress > 15 or compress < 9:
                        compress = 0
                        continue
                if match.group(1):
                    notakeover = True
                # Ignore regex group 5 & 6 for client_max_window_bits
                break
            else:
                if match.group(6):
                    compress = int(match.group(6))
                    # Group5 must match if group6 matches
                    # Compress wbit 8 does not support in zlib
                    # If compress level not support,
                    # FAIL the parse progress
                    if compress > 15 or compress < 9:
                        raise WSHandshakeError("Invalid window size")
                if match.group(2):
                    notakeover = True
                # Ignore regex group 5 & 6 for client_max_window_bits
                break
        # Return Fail if client side and not match
        elif not isserver:
            raise WSHandshakeError("Extension for deflate not supported" + ext.group(1))

    return compress, notakeover


def ws_ext_gen(
    compress: int = 15, isserver: bool = False, server_notakeover: bool = False
) -> str:
    # client_notakeover=False not used for server
    # compress wbit 8 does not support in zlib
    if compress < 9 or compress > 15:
        raise ValueError(
            "Compress wbits must between 9 and 15, zlib does not support wbits=8"
        )
    enabledext = ["permessage-deflate"]
    if not isserver:
        enabledext.append("client_max_window_bits")

    if compress < 15:
        enabledext.append("server_max_window_bits=" + str(compress))
    if server_notakeover:
        enabledext.append("server_no_context_takeover")
    # if client_notakeover:
    #     enabledext.append('client_no_context_takeover')
    return "; ".join(enabledext)

# === NexusCore/openenv\Lib\site-packages\anyio\streams\text.py ===
from __future__ import annotations

import codecs
from collections.abc import Callable, Mapping
from dataclasses import InitVar, dataclass, field
from typing import Any

from ..abc import (
    AnyByteReceiveStream,
    AnyByteSendStream,
    AnyByteStream,
    ObjectReceiveStream,
    ObjectSendStream,
    ObjectStream,
)


@dataclass(eq=False)
class TextReceiveStream(ObjectReceiveStream[str]):
    """
    Stream wrapper that decodes bytes to strings using the given encoding.

    Decoding is done using :class:`~codecs.IncrementalDecoder` which returns any
    completely received unicode characters as soon as they come in.

    :param transport_stream: any bytes-based receive stream
    :param encoding: character encoding to use for decoding bytes to strings (defaults
        to ``utf-8``)
    :param errors: handling scheme for decoding errors (defaults to ``strict``; see the
        `codecs module documentation`_ for a comprehensive list of options)

    .. _codecs module documentation:
        https://docs.python.org/3/library/codecs.html#codec-objects
    """

    transport_stream: AnyByteReceiveStream
    encoding: InitVar[str] = "utf-8"
    errors: InitVar[str] = "strict"
    _decoder: codecs.IncrementalDecoder = field(init=False)

    def __post_init__(self, encoding: str, errors: str) -> None:
        decoder_class = codecs.getincrementaldecoder(encoding)
        self._decoder = decoder_class(errors=errors)

    async def receive(self) -> str:
        while True:
            chunk = await self.transport_stream.receive()
            decoded = self._decoder.decode(chunk)
            if decoded:
                return decoded

    async def aclose(self) -> None:
        await self.transport_stream.aclose()
        self._decoder.reset()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return self.transport_stream.extra_attributes


@dataclass(eq=False)
class TextSendStream(ObjectSendStream[str]):
    """
    Sends strings to the wrapped stream as bytes using the given encoding.

    :param AnyByteSendStream transport_stream: any bytes-based send stream
    :param str encoding: character encoding to use for encoding strings to bytes
        (defaults to ``utf-8``)
    :param str errors: handling scheme for encoding errors (defaults to ``strict``; see
        the `codecs module documentation`_ for a comprehensive list of options)

    .. _codecs module documentation:
        https://docs.python.org/3/library/codecs.html#codec-objects
    """

    transport_stream: AnyByteSendStream
    encoding: InitVar[str] = "utf-8"
    errors: str = "strict"
    _encoder: Callable[..., tuple[bytes, int]] = field(init=False)

    def __post_init__(self, encoding: str) -> None:
        self._encoder = codecs.getencoder(encoding)

    async def send(self, item: str) -> None:
        encoded = self._encoder(item, self.errors)[0]
        await self.transport_stream.send(encoded)

    async def aclose(self) -> None:
        await self.transport_stream.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return self.transport_stream.extra_attributes


@dataclass(eq=False)
class TextStream(ObjectStream[str]):
    """
    A bidirectional stream that decodes bytes to strings on receive and encodes strings
    to bytes on send.

    Extra attributes will be provided from both streams, with the receive stream
    providing the values in case of a conflict.

    :param AnyByteStream transport_stream: any bytes-based stream
    :param str encoding: character encoding to use for encoding/decoding strings to/from
        bytes (defaults to ``utf-8``)
    :param str errors: handling scheme for encoding errors (defaults to ``strict``; see
        the `codecs module documentation`_ for a comprehensive list of options)

    .. _codecs module documentation:
        https://docs.python.org/3/library/codecs.html#codec-objects
    """

    transport_stream: AnyByteStream
    encoding: InitVar[str] = "utf-8"
    errors: InitVar[str] = "strict"
    _receive_stream: TextReceiveStream = field(init=False)
    _send_stream: TextSendStream = field(init=False)

    def __post_init__(self, encoding: str, errors: str) -> None:
        self._receive_stream = TextReceiveStream(
            self.transport_stream, encoding=encoding, errors=errors
        )
        self._send_stream = TextSendStream(
            self.transport_stream, encoding=encoding, errors=errors
        )

    async def receive(self) -> str:
        return await self._receive_stream.receive()

    async def send(self, item: str) -> None:
        await self._send_stream.send(item)

    async def send_eof(self) -> None:
        await self.transport_stream.send_eof()

    async def aclose(self) -> None:
        await self._send_stream.aclose()
        await self._receive_stream.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return {
            **self._send_stream.extra_attributes,
            **self._receive_stream.extra_attributes,
        }

# === NexusCore/openenv\Lib\site-packages\fontTools\designspaceLib\types.py ===
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union, cast

from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    DesignSpaceDocumentError,
    RangeAxisSubsetDescriptor,
    SimpleLocationDict,
    ValueAxisSubsetDescriptor,
    VariableFontDescriptor,
)


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)


@dataclass
class Range:
    minimum: float
    """Inclusive minimum of the range."""
    maximum: float
    """Inclusive maximum of the range."""
    default: float = 0
    """Default value"""

    def __post_init__(self):
        self.minimum, self.maximum = sorted((self.minimum, self.maximum))
        self.default = clamp(self.default, self.minimum, self.maximum)

    def __contains__(self, value: Union[float, Range]) -> bool:
        if isinstance(value, Range):
            return self.minimum <= value.minimum and value.maximum <= self.maximum
        return self.minimum <= value <= self.maximum

    def intersection(self, other: Range) -> Optional[Range]:
        if self.maximum < other.minimum or self.minimum > other.maximum:
            return None
        else:
            return Range(
                max(self.minimum, other.minimum),
                min(self.maximum, other.maximum),
                self.default,  # We don't care about the default in this use-case
            )


# A region selection is either a range or a single value, as a Designspace v5
# axis-subset element only allows a single discrete value or a range for a
# variable-font element.
Region = Dict[str, Union[Range, float]]

# A conditionset is a set of named ranges.
ConditionSet = Dict[str, Range]

# A rule is a list of conditionsets where any has to be relevant for the whole rule to be relevant.
Rule = List[ConditionSet]
Rules = Dict[str, Rule]


def locationInRegion(location: SimpleLocationDict, region: Region) -> bool:
    for name, value in location.items():
        if name not in region:
            return False
        regionValue = region[name]
        if isinstance(regionValue, (float, int)):
            if value != regionValue:
                return False
        else:
            if value not in regionValue:
                return False
    return True


def regionInRegion(region: Region, superRegion: Region) -> bool:
    for name, value in region.items():
        if not name in superRegion:
            return False
        superValue = superRegion[name]
        if isinstance(superValue, (float, int)):
            if value != superValue:
                return False
        else:
            if value not in superValue:
                return False
    return True


def userRegionToDesignRegion(doc: DesignSpaceDocument, userRegion: Region) -> Region:
    designRegion = {}
    for name, value in userRegion.items():
        axis = doc.getAxis(name)
        if axis is None:
            raise DesignSpaceDocumentError(
                f"Cannot find axis named '{name}' for region."
            )
        if isinstance(value, (float, int)):
            designRegion[name] = axis.map_forward(value)
        else:
            designRegion[name] = Range(
                axis.map_forward(value.minimum),
                axis.map_forward(value.maximum),
                axis.map_forward(value.default),
            )
    return designRegion


def getVFUserRegion(doc: DesignSpaceDocument, vf: VariableFontDescriptor) -> Region:
    vfUserRegion: Region = {}
    # For each axis, 2 cases:
    #  - it has a range = it's an axis in the VF DS
    #  - it's a single location = use it to know which rules should apply in the VF
    for axisSubset in vf.axisSubsets:
        axis = doc.getAxis(axisSubset.name)
        if axis is None:
            raise DesignSpaceDocumentError(
                f"Cannot find axis named '{axisSubset.name}' for variable font '{vf.name}'."
            )
        if hasattr(axisSubset, "userMinimum"):
            # Mypy doesn't support narrowing union types via hasattr()
            # TODO(Python 3.10): use TypeGuard
            # https://mypy.readthedocs.io/en/stable/type_narrowing.html
            axisSubset = cast(RangeAxisSubsetDescriptor, axisSubset)
            if not hasattr(axis, "minimum"):
                raise DesignSpaceDocumentError(
                    f"Cannot select a range over '{axis.name}' for variable font '{vf.name}' "
                    "because it's a discrete axis, use only 'userValue' instead."
                )
            axis = cast(AxisDescriptor, axis)
            vfUserRegion[axis.name] = Range(
                max(axisSubset.userMinimum, axis.minimum),
                min(axisSubset.userMaximum, axis.maximum),
                axisSubset.userDefault or axis.default,
            )
        else:
            axisSubset = cast(ValueAxisSubsetDescriptor, axisSubset)
            vfUserRegion[axis.name] = axisSubset.userValue
    # Any axis not mentioned explicitly has a single location = default value
    for axis in doc.axes:
        if axis.name not in vfUserRegion:
            assert isinstance(
                axis.default, (int, float)
            ), f"Axis '{axis.name}' has no valid default value."
            vfUserRegion[axis.name] = axis.default
    return vfUserRegion

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\vector.py ===
from numbers import Number
import math
import operator
import warnings


__all__ = ["Vector"]


class Vector(tuple):
    """A math-like vector.

    Represents an n-dimensional numeric vector. ``Vector`` objects support
    vector addition and subtraction, scalar multiplication and division,
    negation, rounding, and comparison tests.
    """

    __slots__ = ()

    def __new__(cls, values, keep=False):
        if keep is not False:
            warnings.warn(
                "the 'keep' argument has been deprecated",
                DeprecationWarning,
            )
        if type(values) == Vector:
            # No need to create a new object
            return values
        return super().__new__(cls, values)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def _vectorOp(self, other, op):
        if isinstance(other, Vector):
            assert len(self) == len(other)
            return self.__class__(op(a, b) for a, b in zip(self, other))
        if isinstance(other, Number):
            return self.__class__(op(v, other) for v in self)
        raise NotImplementedError()

    def _scalarOp(self, other, op):
        if isinstance(other, Number):
            return self.__class__(op(v, other) for v in self)
        raise NotImplementedError()

    def _unaryOp(self, op):
        return self.__class__(op(v) for v in self)

    def __add__(self, other):
        return self._vectorOp(other, operator.add)

    __radd__ = __add__

    def __sub__(self, other):
        return self._vectorOp(other, operator.sub)

    def __rsub__(self, other):
        return self._vectorOp(other, _operator_rsub)

    def __mul__(self, other):
        return self._scalarOp(other, operator.mul)

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._scalarOp(other, operator.truediv)

    def __rtruediv__(self, other):
        return self._scalarOp(other, _operator_rtruediv)

    def __pos__(self):
        return self._unaryOp(operator.pos)

    def __neg__(self):
        return self._unaryOp(operator.neg)

    def __round__(self, *, round=round):
        return self._unaryOp(round)

    def __eq__(self, other):
        if isinstance(other, list):
            # bw compat Vector([1, 2, 3]) == [1, 2, 3]
            other = tuple(other)
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return any(self)

    __nonzero__ = __bool__

    def __abs__(self):
        return math.sqrt(sum(x * x for x in self))

    def length(self):
        """Return the length of the vector. Equivalent to abs(vector)."""
        return abs(self)

    def normalized(self):
        """Return the normalized vector of the vector."""
        return self / abs(self)

    def dot(self, other):
        """Performs vector dot product, returning the sum of
        ``a[0] * b[0], a[1] * b[1], ...``"""
        assert len(self) == len(other)
        return sum(a * b for a, b in zip(self, other))

    # Deprecated methods/properties

    def toInt(self):
        warnings.warn(
            "the 'toInt' method has been deprecated, use round(vector) instead",
            DeprecationWarning,
        )
        return self.__round__()

    @property
    def values(self):
        warnings.warn(
            "the 'values' attribute has been deprecated, use "
            "the vector object itself instead",
            DeprecationWarning,
        )
        return list(self)

    @values.setter
    def values(self, values):
        raise AttributeError(
            "can't set attribute, the 'values' attribute has been deprecated",
        )

    def isclose(self, other: "Vector", **kwargs) -> bool:
        """Return True if the vector is close to another Vector."""
        assert len(self) == len(other)
        return all(math.isclose(a, b, **kwargs) for a, b in zip(self, other))


def _operator_rsub(a, b):
    return operator.sub(b, a)


def _operator_rtruediv(a, b):
    return operator.truediv(b, a)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_h_h_e_a.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
from fontTools.misc.fixedTools import (
    ensureVersionIsLong as fi2ve,
    versionToFixed as ve2fi,
)
from . import DefaultTable
import math


hheaFormat = """
		>  # big endian
		tableVersion:           L
		ascent:                 h
		descent:                h
		lineGap:                h
		advanceWidthMax:        H
		minLeftSideBearing:     h
		minRightSideBearing:    h
		xMaxExtent:             h
		caretSlopeRise:         h
		caretSlopeRun:          h
		caretOffset:            h
		reserved0:              h
		reserved1:              h
		reserved2:              h
		reserved3:              h
		metricDataFormat:       h
		numberOfHMetrics:       H
"""


class table__h_h_e_a(DefaultTable.DefaultTable):
    """Horizontal Header table

    The ``hhea`` table contains information needed during horizontal
    text layout.

    .. note::
       This converter class is kept in sync with the :class:`._v_h_e_a.table__v_h_e_a`
       table constructor.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/hhea
    """

    # Note: Keep in sync with table__v_h_e_a

    dependencies = ["hmtx", "glyf", "CFF ", "CFF2"]

    # OpenType spec renamed these, add aliases for compatibility
    @property
    def ascender(self):
        return self.ascent

    @ascender.setter
    def ascender(self, value):
        self.ascent = value

    @property
    def descender(self):
        return self.descent

    @descender.setter
    def descender(self, value):
        self.descent = value

    def decompile(self, data, ttFont):
        sstruct.unpack(hheaFormat, data, self)

    def compile(self, ttFont):
        if ttFont.recalcBBoxes and (
            ttFont.isLoaded("glyf")
            or ttFont.isLoaded("CFF ")
            or ttFont.isLoaded("CFF2")
        ):
            self.recalc(ttFont)
        self.tableVersion = fi2ve(self.tableVersion)
        return sstruct.pack(hheaFormat, self)

    def recalc(self, ttFont):
        if "hmtx" not in ttFont:
            return

        hmtxTable = ttFont["hmtx"]
        self.advanceWidthMax = max(adv for adv, _ in hmtxTable.metrics.values())

        boundsWidthDict = {}
        if "glyf" in ttFont:
            glyfTable = ttFont["glyf"]
            for name in ttFont.getGlyphOrder():
                g = glyfTable[name]
                if g.numberOfContours == 0:
                    continue
                if g.numberOfContours < 0 and not hasattr(g, "xMax"):
                    # Composite glyph without extents set.
                    # Calculate those.
                    g.recalcBounds(glyfTable)
                boundsWidthDict[name] = g.xMax - g.xMin
        elif "CFF " in ttFont or "CFF2" in ttFont:
            if "CFF " in ttFont:
                topDict = ttFont["CFF "].cff.topDictIndex[0]
            else:
                topDict = ttFont["CFF2"].cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            for name in ttFont.getGlyphOrder():
                cs = charStrings[name]
                bounds = cs.calcBounds(charStrings)
                if bounds is not None:
                    boundsWidthDict[name] = int(
                        math.ceil(bounds[2]) - math.floor(bounds[0])
                    )

        if boundsWidthDict:
            minLeftSideBearing = float("inf")
            minRightSideBearing = float("inf")
            xMaxExtent = -float("inf")
            for name, boundsWidth in boundsWidthDict.items():
                advanceWidth, lsb = hmtxTable[name]
                rsb = advanceWidth - lsb - boundsWidth
                extent = lsb + boundsWidth
                minLeftSideBearing = min(minLeftSideBearing, lsb)
                minRightSideBearing = min(minRightSideBearing, rsb)
                xMaxExtent = max(xMaxExtent, extent)
            self.minLeftSideBearing = minLeftSideBearing
            self.minRightSideBearing = minRightSideBearing
            self.xMaxExtent = xMaxExtent

        else:  # No glyph has outlines.
            self.minLeftSideBearing = 0
            self.minRightSideBearing = 0
            self.xMaxExtent = 0

    def toXML(self, writer, ttFont):
        formatstring, names, fixes = sstruct.getformat(hheaFormat)
        for name in names:
            value = getattr(self, name)
            if name == "tableVersion":
                value = fi2ve(value)
                value = "0x%08x" % value
            writer.simpletag(name, value=value)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "tableVersion":
            setattr(self, name, ve2fi(attrs["value"]))
            return
        setattr(self, name, safeEval(attrs["value"]))

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_m_a_x_p.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
from . import DefaultTable

maxpFormat_0_5 = """
		>	# big endian
		tableVersion:           i
		numGlyphs:              H
"""

maxpFormat_1_0_add = """
		>	# big endian
		maxPoints:              H
		maxContours:            H
		maxCompositePoints:     H
		maxCompositeContours:   H
		maxZones:               H
		maxTwilightPoints:      H
		maxStorage:             H
		maxFunctionDefs:        H
		maxInstructionDefs:     H
		maxStackElements:       H
		maxSizeOfInstructions:  H
		maxComponentElements:   H
		maxComponentDepth:      H
"""


class table__m_a_x_p(DefaultTable.DefaultTable):
    """Maximum Profile table

    The ``maxp`` table contains the memory requirements for the data in
    the font.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/maxp
    """

    dependencies = ["glyf"]

    def decompile(self, data, ttFont):
        dummy, data = sstruct.unpack2(maxpFormat_0_5, data, self)
        self.numGlyphs = int(self.numGlyphs)
        if self.tableVersion != 0x00005000:
            dummy, data = sstruct.unpack2(maxpFormat_1_0_add, data, self)
        assert len(data) == 0

    def compile(self, ttFont):
        if "glyf" in ttFont:
            if ttFont.isLoaded("glyf") and ttFont.recalcBBoxes:
                self.recalc(ttFont)
        else:
            pass  # CFF
        self.numGlyphs = len(ttFont.getGlyphOrder())
        if self.tableVersion != 0x00005000:
            self.tableVersion = 0x00010000
        data = sstruct.pack(maxpFormat_0_5, self)
        if self.tableVersion == 0x00010000:
            data = data + sstruct.pack(maxpFormat_1_0_add, self)
        return data

    def recalc(self, ttFont):
        """Recalculate the font bounding box, and most other maxp values except
        for the TT instructions values. Also recalculate the value of bit 1
        of the flags field and the font bounding box of the 'head' table.
        """
        glyfTable = ttFont["glyf"]
        hmtxTable = ttFont["hmtx"]
        headTable = ttFont["head"]
        self.numGlyphs = len(glyfTable)
        INFINITY = 100000
        xMin = +INFINITY
        yMin = +INFINITY
        xMax = -INFINITY
        yMax = -INFINITY
        maxPoints = 0
        maxContours = 0
        maxCompositePoints = 0
        maxCompositeContours = 0
        maxComponentElements = 0
        maxComponentDepth = 0
        allXMinIsLsb = 1
        for glyphName in ttFont.getGlyphOrder():
            g = glyfTable[glyphName]
            if g.numberOfContours:
                if hmtxTable[glyphName][1] != g.xMin:
                    allXMinIsLsb = 0
                xMin = min(xMin, g.xMin)
                yMin = min(yMin, g.yMin)
                xMax = max(xMax, g.xMax)
                yMax = max(yMax, g.yMax)
                if g.numberOfContours > 0:
                    nPoints, nContours = g.getMaxpValues()
                    maxPoints = max(maxPoints, nPoints)
                    maxContours = max(maxContours, nContours)
                elif g.isComposite():
                    nPoints, nContours, componentDepth = g.getCompositeMaxpValues(
                        glyfTable
                    )
                    maxCompositePoints = max(maxCompositePoints, nPoints)
                    maxCompositeContours = max(maxCompositeContours, nContours)
                    maxComponentElements = max(maxComponentElements, len(g.components))
                    maxComponentDepth = max(maxComponentDepth, componentDepth)
        if xMin == +INFINITY:
            headTable.xMin = 0
            headTable.yMin = 0
            headTable.xMax = 0
            headTable.yMax = 0
        else:
            headTable.xMin = xMin
            headTable.yMin = yMin
            headTable.xMax = xMax
            headTable.yMax = yMax
        self.maxPoints = maxPoints
        self.maxContours = maxContours
        self.maxCompositePoints = maxCompositePoints
        self.maxCompositeContours = maxCompositeContours
        self.maxComponentElements = maxComponentElements
        self.maxComponentDepth = maxComponentDepth
        if allXMinIsLsb:
            headTable.flags = headTable.flags | 0x2
        else:
            headTable.flags = headTable.flags & ~0x2

    def testrepr(self):
        items = sorted(self.__dict__.items())
        print(". . . . . . . . .")
        for combo in items:
            print("  %s: %s" % combo)
        print(". . . . . . . . .")

    def toXML(self, writer, ttFont):
        if self.tableVersion != 0x00005000:
            writer.comment("Most of this table will be recalculated by the compiler")
            writer.newline()
        formatstring, names, fixes = sstruct.getformat(maxpFormat_0_5)
        if self.tableVersion != 0x00005000:
            formatstring, names_1_0, fixes = sstruct.getformat(maxpFormat_1_0_add)
            names = {**names, **names_1_0}
        for name in names:
            value = getattr(self, name)
            if name == "tableVersion":
                value = hex(value)
            writer.simpletag(name, value=value)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        setattr(self, name, safeEval(attrs["value"]))

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\repo.py ===
# Copyright 2025 The HuggingFace Team. All rights reserved.
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
"""Contains commands to interact with repositories on the Hugging Face Hub.

Usage:
    # create a new dataset repo on the Hub
    huggingface-cli repo create my-cool-dataset --repo-type=dataset

    # create a private model repo on the Hub
    huggingface-cli repo create my-cool-model --private
"""

import argparse
from argparse import _SubParsersAction
from typing import Optional

from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.commands._cli_utils import ANSI
from huggingface_hub.constants import SPACES_SDK_TYPES
from huggingface_hub.hf_api import HfApi
from huggingface_hub.utils import logging


logger = logging.get_logger(__name__)


class RepoCommands(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        repo_parser = parser.add_parser("repo", help="{create} Commands to interact with your huggingface.co repos.")
        repo_subparsers = repo_parser.add_subparsers(help="huggingface.co repos related commands")
        repo_create_parser = repo_subparsers.add_parser("create", help="Create a new repo on huggingface.co")
        repo_create_parser.add_argument(
            "repo_id",
            type=str,
            help="The ID of the repo to create to (e.g. `username/repo-name`). The username is optional and will be set to your username if not provided.",
        )
        repo_create_parser.add_argument(
            "--repo-type",
            type=str,
            help='Optional: set to "dataset" or "space" if creating a dataset or space, default is model.',
        )
        repo_create_parser.add_argument(
            "--space_sdk",
            type=str,
            help='Optional: Hugging Face Spaces SDK type. Required when --type is set to "space".',
            choices=SPACES_SDK_TYPES,
        )
        repo_create_parser.add_argument(
            "--private",
            action="store_true",
            help="Whether to create a private repository. Defaults to public unless the organization's default is private.",
        )
        repo_create_parser.add_argument(
            "--token",
            type=str,
            help="Hugging Face token. Will default to the locally saved token if not provided.",
        )
        repo_create_parser.add_argument(
            "--exist-ok",
            action="store_true",
            help="Do not raise an error if repo already exists.",
        )
        repo_create_parser.add_argument(
            "--resource-group-id",
            type=str,
            help="Resource group in which to create the repo. Resource groups is only available for Enterprise Hub organizations.",
        )
        repo_create_parser.add_argument(
            "--type",
            type=str,
            help="[Deprecated]: use --repo-type instead.",
        )
        repo_create_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="[Deprecated] no effect.",
        )
        repo_create_parser.add_argument(
            "--organization", type=str, help="[Deprecated] Pass the organization namespace directly in the repo_id."
        )
        repo_create_parser.set_defaults(func=lambda args: RepoCreateCommand(args))


class RepoCreateCommand:
    def __init__(self, args: argparse.Namespace):
        self.repo_id: str = args.repo_id
        self.repo_type: Optional[str] = args.repo_type or args.type
        self.space_sdk: Optional[str] = args.space_sdk
        self.organization: Optional[str] = args.organization
        self.yes: bool = args.yes
        self.private: bool = args.private
        self.token: Optional[str] = args.token
        self.exist_ok: bool = args.exist_ok
        self.resource_group_id: Optional[str] = args.resource_group_id

        if args.type is not None:
            print(
                ANSI.yellow(
                    "The --type argument is deprecated and will be removed in a future version. Use --repo-type instead."
                )
            )
        if self.organization is not None:
            print(
                ANSI.yellow(
                    "The --organization argument is deprecated and will be removed in a future version. Pass the organization namespace directly in the repo_id."
                )
            )
        if self.yes:
            print(
                ANSI.yellow(
                    "The --yes argument is deprecated and will be removed in a future version. It does not have any effect."
                )
            )

        self._api = HfApi()

    def run(self):
        if self.organization is not None:
            if "/" in self.repo_id:
                print(ANSI.red("You cannot pass both --organization and a repo_id with a namespace."))
                exit(1)
            self.repo_id = f"{self.organization}/{self.repo_id}"

        repo_url = self._api.create_repo(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            private=self.private,
            token=self.token,
            exist_ok=self.exist_ok,
            resource_group_id=self.resource_group_id,
            space_sdk=self.space_sdk,
        )
        print(f"Successfully created {ANSI.bold(repo_url.repo_id)} on the Hub.")
        print(f"Your repo is now available at {ANSI.bold(repo_url)}")