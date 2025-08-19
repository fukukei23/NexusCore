
# === NexusCore/tools\exports\export_20250803_114325\combined_170.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\editor.py ===
#####################################################################
#
# editor.py
#
# A general purpose text editor, built on top of the win32ui edit
# type, which is built on an MFC CEditView
#
#
# We now support reloading of externally modified documented
# (eg, presumably by some other process, such as source control or
# another editor.
# We also support auto-loading of externally modified files.
# - if the current document has not been modified in this
# editor, but has been modified on disk, then the file
# can be automatically reloaded.
#
# Note that it will _always_ prompt you if the file in the editor has been modified.


import re

import win32api
import win32con
import win32ui
from pywin.framework.editor import (
    GetEditorFontOption,
    GetEditorOption,
    defaultCharacterFormat,
)
from pywin.mfc import afxres
from pywin.mfc.docview import RichEditView as ParentEditorView

from .document import EditorDocumentBase as ParentEditorDocument

# from pywin.mfc.docview import EditView as ParentEditorView
# from pywin.mfc.docview import Document as ParentEditorDocument

patImport = re.compile(r"import (?P<name>.*)")
patIndent = re.compile(r"^([ \t]*[~ \t])")

ID_LOCATE_FILE = 0xE200
ID_GOTO_LINE = 0xE2001
# WARNING: Duplicated in document.py and coloreditor.py
MSG_CHECK_EXTERNAL_FILE = win32con.WM_USER + 1999

# Key Codes that modify the bufffer when Ctrl or Alt are NOT pressed.
MODIFYING_VK_KEYS = [
    win32con.VK_BACK,
    win32con.VK_TAB,
    win32con.VK_RETURN,
    win32con.VK_SPACE,
    win32con.VK_DELETE,
]
for k in range(48, 91):
    MODIFYING_VK_KEYS.append(k)

# Key Codes that modify the bufffer when Ctrl is pressed.
MODIFYING_VK_KEYS_CTRL = [
    win32con.VK_BACK,
    win32con.VK_RETURN,
    win32con.VK_SPACE,
    win32con.VK_DELETE,
]

# Key Codes that modify the bufffer when Alt is pressed.
MODIFYING_VK_KEYS_ALT = [
    win32con.VK_BACK,
    win32con.VK_RETURN,
    win32con.VK_SPACE,
    win32con.VK_DELETE,
]


# The editor itself starts here.
# Using the MFC Document/View model, we have an EditorDocument, which is responsible for
# managing the contents of the file, and a view which is responsible for rendering it.
#
# Due to a limitation in the Windows edit controls, we are limited to one view
# per document, although nothing in this code assumes this (I hope!)

isRichText = 1  # We are using the Rich Text control.  This has not been tested with value "0" for quite some time!


class EditorDocument(ParentEditorDocument):
    #
    # File loading and saving operations
    #
    def OnOpenDocument(self, filename):
        #
        # handle Unix and PC text file format.
        #

        # Get the "long name" of the file name, as it may have been translated
        # to short names by the shell.
        self.SetPathName(filename)  # Must set this early!
        # Now do the work!
        self.BeginWaitCursor()
        win32ui.SetStatusText("Loading file...", 1)
        try:
            f = open(filename, "rb")
        except OSError:
            win32ui.MessageBox(
                filename
                + "\nCan not find this file\nPlease verify that the correct path and file name are given"
            )
            self.EndWaitCursor()
            return 0
        raw = f.read()
        f.close()
        contents = self.TranslateLoadedData(raw)
        rc = 0
        try:
            self.GetFirstView().SetWindowText(contents)
            rc = 1
        except TypeError:  # Null byte in file.
            win32ui.MessageBox("This file contains NULL bytes, and can not be edited")
            rc = 0

        self.EndWaitCursor()
        self.SetModifiedFlag(0)  # No longer dirty
        self._DocumentStateChanged()
        return rc

    def TranslateLoadedData(self, data):
        """Given raw data read from a file, massage it suitable for the edit window"""
        # if a CR in the first 250 chars, then perform the expensive translate
        if data[:250].find("\r") == -1:
            win32ui.SetStatusText(
                "Translating from Unix file format - please wait...", 1
            )
            return re.sub(r"\r*\n", "\r\n", data)
        else:
            return data

    def SaveFile(self, fileName, encoding=None):
        if isRichText:
            view = self.GetFirstView()
            view.SaveTextFile(fileName, encoding=encoding)
        else:  # Old style edit view window.
            self.GetFirstView().SaveFile(fileName)
        try:
            # Make sure line cache has updated info about me!
            import linecache

            linecache.checkcache()
        except:
            pass

    #
    # Color state stuff
    #
    def SetAllLineColors(self, color=None):
        for view in self.GetAllViews():
            view.SetAllLineColors(color)

    def SetLineColor(self, lineNo, color):
        "Color a line of all views"
        for view in self.GetAllViews():
            view.SetLineColor(lineNo, color)


# 	def StreamTextOut(self, data): ### This seems unreliable???
# 		self.saveFileHandle.write(data)
# 		return 1 # keep em coming!


class EditorView(ParentEditorView):
    def __init__(self, doc):
        ParentEditorView.__init__(self, doc)
        if isRichText:
            self.SetWordWrap(win32ui.CRichEditView_WrapNone)

        self.addToMRU = 1
        self.HookHandlers()
        self.bCheckingFile = 0

        self.defCharFormat = GetEditorFontOption("Default Font", defaultCharacterFormat)

        # Smart tabs override everything else if context can be worked out.
        self.bSmartTabs = GetEditorOption("Smart Tabs", 1)

        self.tabSize = GetEditorOption("Tab Size", 8)
        self.indentSize = GetEditorOption("Indent Size", 8)
        # If next indent is at a tab position, and useTabs is set, a tab will be inserted.
        self.bUseTabs = GetEditorOption("Use Tabs", 1)

    def OnInitialUpdate(self):
        rc = self._obj_.OnInitialUpdate()
        self.SetDefaultCharFormat(self.defCharFormat)
        return rc

    def CutCurLine(self):
        curLine = self._obj_.LineFromChar()
        nextLine = curLine + 1
        start = self._obj_.LineIndex(curLine)
        end = self._obj_.LineIndex(nextLine)
        if end == 0:  # must be last line.
            end = start + self.end.GetLineLength(curLine)
        self._obj_.SetSel(start, end)
        self._obj_.Cut()

    def _PrepareUserStateChange(self):
        "Return selection, lineindex, etc info, so it can be restored"
        self.SetRedraw(0)
        return self.GetModify(), self.GetSel(), self.GetFirstVisibleLine()

    def _EndUserStateChange(self, info):
        scrollOff = info[2] - self.GetFirstVisibleLine()
        if scrollOff:
            self.LineScroll(scrollOff)
        self.SetSel(info[1])
        self.SetModify(info[0])
        self.SetRedraw(1)
        self.InvalidateRect()
        self.UpdateWindow()

    def _UpdateUIForState(self):
        self.SetReadOnly(self.GetDocument()._IsReadOnly())

    def SetAllLineColors(self, color=None):
        if isRichText:
            info = self._PrepareUserStateChange()
            try:
                if color is None:
                    color = self.defCharFormat[4]
                self.SetSel(0, -1)
                self.SetSelectionCharFormat((win32con.CFM_COLOR, 0, 0, 0, color))
            finally:
                self._EndUserStateChange(info)

    def SetLineColor(self, lineNo, color):
        "lineNo is the 1 based line number to set.  If color is None, default color is used."
        if isRichText:
            info = self._PrepareUserStateChange()
            try:
                if color is None:
                    color = self.defCharFormat[4]
                lineNo -= 1
                startIndex = self.LineIndex(lineNo)
                if startIndex != -1:
                    self.SetSel(startIndex, self.LineIndex(lineNo + 1))
                    self.SetSelectionCharFormat((win32con.CFM_COLOR, 0, 0, 0, color))
            finally:
                self._EndUserStateChange(info)

    def Indent(self):
        """Insert an indent to move the cursor to the next tab position.

        Honors the tab size and 'use tabs' settings.  Assumes the cursor is already at the
        position to be indented, and the selection is a single character (ie, not a block)
        """
        start, end = self._obj_.GetSel()
        startLine = self._obj_.LineFromChar(start)
        line = self._obj_.GetLine(startLine)
        realCol = start - self._obj_.LineIndex(startLine)
        # Calulate the next tab stop.
        # Expand existing tabs.
        curCol = 0
        for ch in line[:realCol]:
            if ch == "\t":
                curCol = ((curCol / self.tabSize) + 1) * self.tabSize
            else:
                curCol += 1
        nextColumn = ((curCol / self.indentSize) + 1) * self.indentSize
        # print("curCol is", curCol, "nextColumn is", nextColumn)
        ins = None
        if self.bSmartTabs:
            # Look for some context.
            if realCol == 0:  # Start of the line - see if the line above can tell us
                lookLine = startLine - 1
                while lookLine >= 0:
                    check = self._obj_.GetLine(lookLine)[0:1]
                    if check in ("\t", " "):
                        ins = check
                        break
                    lookLine -= 1
            else:  # See if the previous char can tell us
                check = line[realCol - 1]
                if check in ("\t", " "):
                    ins = check

        # Either smart tabs off, or not smart enough!
        # Use the "old style" settings.
        if ins is None:
            if self.bUseTabs and nextColumn % self.tabSize == 0:
                ins = "\t"
            else:
                ins = " "

        if ins == " ":
            # Calc the number of spaces to take us to the next stop
            ins *= nextColumn - curCol

        self._obj_.ReplaceSel(ins)

    def BlockDent(self, isIndent, startLine, endLine):
        "Indent/Undent all lines specified"
        if not self.GetDocument().CheckMakeDocumentWritable():
            return 0
        tabSize = self.tabSize  # hard-code for now!
        info = self._PrepareUserStateChange()
        try:
            for lineNo in range(startLine, endLine):
                pos = self._obj_.LineIndex(lineNo)
                self._obj_.SetSel(pos, pos)
                if isIndent:
                    self.Indent()
                else:
                    line = self._obj_.GetLine(lineNo)
                    try:
                        noToDel = 0
                        if line[0] == "\t":
                            noToDel = 1
                        elif line[0] == " ":
                            for noToDel in range(0, tabSize):
                                if line[noToDel] != " ":
                                    break
                            else:
                                noToDel = tabSize
                        if noToDel:
                            self._obj_.SetSel(pos, pos + noToDel)
                            self._obj_.Clear()
                    except IndexError:
                        pass
        finally:
            self._EndUserStateChange(info)
        self.GetDocument().SetModifiedFlag(1)  # Now dirty
        self._obj_.SetSel(self.LineIndex(startLine), self.LineIndex(endLine))

    def GotoLine(self, lineNo=None):
        try:
            if lineNo is None:
                lineNo = int(input("Enter Line Number"))
        except (ValueError, KeyboardInterrupt):
            return 0
        self.GetLineCount()  # Seems to be needed when file first opened???
        charNo = self.LineIndex(lineNo - 1)
        self.SetSel(charNo)

    def HookHandlers(self):  # children can override, but should still call me!
        # 		self.HookAllKeyStrokes(self.OnKey)
        self.HookMessage(self.OnCheckExternalDocumentUpdated, MSG_CHECK_EXTERNAL_FILE)
        self.HookMessage(self.OnRClick, win32con.WM_RBUTTONDOWN)
        self.HookMessage(self.OnSetFocus, win32con.WM_SETFOCUS)
        self.HookMessage(self.OnKeyDown, win32con.WM_KEYDOWN)
        self.HookKeyStroke(self.OnKeyCtrlY, 25)  # ^Y
        self.HookKeyStroke(self.OnKeyCtrlG, 7)  # ^G
        self.HookKeyStroke(self.OnKeyTab, 9)  # TAB
        self.HookKeyStroke(self.OnKeyEnter, 13)  # Enter
        self.HookCommand(self.OnCmdLocateFile, ID_LOCATE_FILE)
        self.HookCommand(self.OnCmdGotoLine, ID_GOTO_LINE)
        self.HookCommand(self.OnEditPaste, afxres.ID_EDIT_PASTE)
        self.HookCommand(self.OnEditCut, afxres.ID_EDIT_CUT)

    # Hook Handlers
    def OnSetFocus(self, msg):
        # Even though we use file change notifications, we should be very sure about it here.
        self.OnCheckExternalDocumentUpdated(msg)

    def OnRClick(self, params):
        menu = win32ui.CreatePopupMenu()

        # look for a module name
        line = self._obj_.GetLine().strip()
        flags = win32con.MF_STRING | win32con.MF_ENABLED
        matchResult = patImport.match(line)
        if matchResult and matchResult[0] == line:
            menu.AppendMenu(
                flags, ID_LOCATE_FILE, "&Locate %s.py" % matchResult.group("name")
            )
            menu.AppendMenu(win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, win32ui.ID_EDIT_UNDO, "&Undo")
        menu.AppendMenu(win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, win32ui.ID_EDIT_CUT, "Cu&t")
        menu.AppendMenu(flags, win32ui.ID_EDIT_COPY, "&Copy")
        menu.AppendMenu(flags, win32ui.ID_EDIT_PASTE, "&Paste")
        menu.AppendMenu(flags, win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, win32ui.ID_EDIT_SELECT_ALL, "&Select all")
        menu.AppendMenu(flags, win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, ID_GOTO_LINE, "&Goto line...")
        menu.TrackPopupMenu(params[5])
        return 0

    def OnCmdGotoLine(self, cmd, code):
        self.GotoLine()
        return 0

    def OnCmdLocateFile(self, cmd, code):
        modName = patImport.group("name")
        if not modName:
            return 0
        import pywin.framework.scriptutils

        fileName = pywin.framework.scriptutils.LocatePythonFile(modName)
        if fileName is None:
            win32ui.SetStatusText("Can't locate module %s" % modName)
        else:
            win32ui.GetApp().OpenDocumentFile(fileName)
        return 0

    # Key handlers
    def OnKeyEnter(self, key):
        if not self.GetDocument().CheckMakeDocumentWritable():
            return 0
        curLine = self._obj_.GetLine()
        self._obj_.ReplaceSel("\r\n")  # insert the newline
        # If the current line indicates the next should be indented,
        # then copy the current indentation to this line.
        res = patIndent.match(curLine, 0)
        if res > 0 and curLine.strip():
            curIndent = patIndent.group(1)
            self._obj_.ReplaceSel(curIndent)
        return 0  # don't pass on

    def OnKeyCtrlY(self, key):
        if not self.GetDocument().CheckMakeDocumentWritable():
            return 0
        self.CutCurLine()
        return 0  # don't let him have it!

    def OnKeyCtrlG(self, key):
        self.GotoLine()
        return 0  # don't let him have it!

    def OnKeyTab(self, key):
        if not self.GetDocument().CheckMakeDocumentWritable():
            return 0
        start, end = self._obj_.GetSel()
        if start == end:  # normal TAB key
            self.Indent()
            return 0  # we handled this.

        # Otherwise it is a block indent/dedent.
        if start > end:
            start, end = end, start  # swap them.
        startLine = self._obj_.LineFromChar(start)
        endLine = self._obj_.LineFromChar(end)

        self.BlockDent(win32api.GetKeyState(win32con.VK_SHIFT) >= 0, startLine, endLine)
        return 0

    def OnEditPaste(self, id, code):
        # Return 1 if we can make the file editable.(or it already is!)
        return self.GetDocument().CheckMakeDocumentWritable()

    def OnEditCut(self, id, code):
        # Return 1 if we can make the file editable.(or it already is!)
        return self.GetDocument().CheckMakeDocumentWritable()

    def OnKeyDown(self, msg):
        key = msg[2]
        if win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000:
            modList = MODIFYING_VK_KEYS_CTRL
        elif win32api.GetKeyState(win32con.VK_MENU) & 0x8000:
            modList = MODIFYING_VK_KEYS_ALT
        else:
            modList = MODIFYING_VK_KEYS

        if key in modList:
            # Return 1 if we can make the file editable.(or it already is!)
            return self.GetDocument().CheckMakeDocumentWritable()
        return 1  # Pass it on OK

    # 	def OnKey(self, key):
    # 		return self.GetDocument().CheckMakeDocumentWritable()

    def OnCheckExternalDocumentUpdated(self, msg):
        if self._obj_ is None or self.bCheckingFile:
            return
        self.bCheckingFile = 1
        self.GetDocument().CheckExternalDocumentUpdated()
        self.bCheckingFile = 0


from .template import EditorTemplateBase


class EditorTemplate(EditorTemplateBase):
    def __init__(
        self, res=win32ui.IDR_TEXTTYPE, makeDoc=None, makeFrame=None, makeView=None
    ):
        if makeDoc is None:
            makeDoc = EditorDocument
        if makeView is None:
            makeView = EditorView
        EditorTemplateBase.__init__(self, res, makeDoc, makeFrame, makeView)

    def _CreateDocTemplate(self, resourceId):
        return win32ui.CreateRichEditDocTemplate(resourceId)

    def CreateWin32uiDocument(self):
        return self.DoCreateRichEditDoc()


def Create(fileName=None, title=None, template=None):
    return editorTemplate.OpenDocumentFile(fileName)


from pywin.framework.editor import GetDefaultEditorModuleName

prefModule = GetDefaultEditorModuleName()
# Initialize only if this is the "default" editor.
if __name__ == prefModule:
    # For debugging purposes, when this module may be reloaded many times.
    try:
        win32ui.GetApp().RemoveDocTemplate(editorTemplate)  # type: ignore[has-type, used-before-def]
    except (NameError, win32ui.error):
        pass

    editorTemplate = EditorTemplate()
    win32ui.GetApp().AddDocTemplate(editorTemplate)

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\local.py ===
import datetime
import io
import logging
import os
import os.path as osp
import shutil
import stat
import tempfile
from functools import lru_cache

from fsspec import AbstractFileSystem
from fsspec.compression import compr
from fsspec.core import get_compression
from fsspec.utils import isfilelike, stringify_path

logger = logging.getLogger("fsspec.local")


class LocalFileSystem(AbstractFileSystem):
    """Interface to files on local storage

    Parameters
    ----------
    auto_mkdir: bool
        Whether, when opening a file, the directory containing it should
        be created (if it doesn't already exist). This is assumed by pyarrow
        code.
    """

    root_marker = "/"
    protocol = "file", "local"
    local_file = True

    def __init__(self, auto_mkdir=False, **kwargs):
        super().__init__(**kwargs)
        self.auto_mkdir = auto_mkdir

    @property
    def fsid(self):
        return "local"

    def mkdir(self, path, create_parents=True, **kwargs):
        path = self._strip_protocol(path)
        if self.exists(path):
            raise FileExistsError(path)
        if create_parents:
            self.makedirs(path, exist_ok=True)
        else:
            os.mkdir(path, **kwargs)

    def makedirs(self, path, exist_ok=False):
        path = self._strip_protocol(path)
        os.makedirs(path, exist_ok=exist_ok)

    def rmdir(self, path):
        path = self._strip_protocol(path)
        os.rmdir(path)

    def ls(self, path, detail=False, **kwargs):
        path = self._strip_protocol(path)
        path_info = self.info(path)
        infos = []
        if path_info["type"] == "directory":
            with os.scandir(path) as it:
                for f in it:
                    try:
                        # Only get the info if requested since it is a bit expensive (the stat call inside)
                        # The strip_protocol is also used in info() and calls make_path_posix to always return posix paths
                        info = self.info(f) if detail else self._strip_protocol(f.path)
                        infos.append(info)
                    except FileNotFoundError:
                        pass
        else:
            infos = [path_info] if detail else [path_info["name"]]

        return infos

    def info(self, path, **kwargs):
        if isinstance(path, os.DirEntry):
            # scandir DirEntry
            out = path.stat(follow_symlinks=False)
            link = path.is_symlink()
            if path.is_dir(follow_symlinks=False):
                t = "directory"
            elif path.is_file(follow_symlinks=False):
                t = "file"
            else:
                t = "other"

            size = out.st_size
            if link:
                try:
                    out2 = path.stat(follow_symlinks=True)
                    size = out2.st_size
                except OSError:
                    size = 0
            path = self._strip_protocol(path.path)
        else:
            # str or path-like
            path = self._strip_protocol(path)
            out = os.stat(path, follow_symlinks=False)
            link = stat.S_ISLNK(out.st_mode)
            if link:
                out = os.stat(path, follow_symlinks=True)
            size = out.st_size
            if stat.S_ISDIR(out.st_mode):
                t = "directory"
            elif stat.S_ISREG(out.st_mode):
                t = "file"
            else:
                t = "other"
        result = {
            "name": path,
            "size": size,
            "type": t,
            "created": out.st_ctime,
            "islink": link,
        }
        for field in ["mode", "uid", "gid", "mtime", "ino", "nlink"]:
            result[field] = getattr(out, f"st_{field}")
        if link:
            result["destination"] = os.readlink(path)
        return result

    def lexists(self, path, **kwargs):
        return osp.lexists(path)

    def cp_file(self, path1, path2, **kwargs):
        path1 = self._strip_protocol(path1)
        path2 = self._strip_protocol(path2)
        if self.auto_mkdir:
            self.makedirs(self._parent(path2), exist_ok=True)
        if self.isfile(path1):
            shutil.copyfile(path1, path2)
        elif self.isdir(path1):
            self.mkdirs(path2, exist_ok=True)
        else:
            raise FileNotFoundError(path1)

    def isfile(self, path):
        path = self._strip_protocol(path)
        return os.path.isfile(path)

    def isdir(self, path):
        path = self._strip_protocol(path)
        return os.path.isdir(path)

    def get_file(self, path1, path2, callback=None, **kwargs):
        if isfilelike(path2):
            with open(path1, "rb") as f:
                shutil.copyfileobj(f, path2)
        else:
            return self.cp_file(path1, path2, **kwargs)

    def put_file(self, path1, path2, callback=None, **kwargs):
        return self.cp_file(path1, path2, **kwargs)

    def mv(self, path1, path2, recursive: bool = True, **kwargs):
        """Move files/directories
        For the specific case of local, all ops on directories are recursive and
        the recursive= kwarg is ignored.
        """
        path1 = self._strip_protocol(path1)
        path2 = self._strip_protocol(path2)
        shutil.move(path1, path2)

    def link(self, src, dst, **kwargs):
        src = self._strip_protocol(src)
        dst = self._strip_protocol(dst)
        os.link(src, dst, **kwargs)

    def symlink(self, src, dst, **kwargs):
        src = self._strip_protocol(src)
        dst = self._strip_protocol(dst)
        os.symlink(src, dst, **kwargs)

    def islink(self, path) -> bool:
        return os.path.islink(self._strip_protocol(path))

    def rm_file(self, path):
        os.remove(self._strip_protocol(path))

    def rm(self, path, recursive=False, maxdepth=None):
        if not isinstance(path, list):
            path = [path]

        for p in path:
            p = self._strip_protocol(p)
            if self.isdir(p):
                if not recursive:
                    raise ValueError("Cannot delete directory, set recursive=True")
                if osp.abspath(p) == os.getcwd():
                    raise ValueError("Cannot delete current working directory")
                shutil.rmtree(p)
            else:
                os.remove(p)

    def unstrip_protocol(self, name):
        name = self._strip_protocol(name)  # normalise for local/win/...
        return f"file://{name}"

    def _open(self, path, mode="rb", block_size=None, **kwargs):
        path = self._strip_protocol(path)
        if self.auto_mkdir and "w" in mode:
            self.makedirs(self._parent(path), exist_ok=True)
        return LocalFileOpener(path, mode, fs=self, **kwargs)

    def touch(self, path, truncate=True, **kwargs):
        path = self._strip_protocol(path)
        if self.auto_mkdir:
            self.makedirs(self._parent(path), exist_ok=True)
        if self.exists(path):
            os.utime(path, None)
        else:
            open(path, "a").close()
        if truncate:
            os.truncate(path, 0)

    def created(self, path):
        info = self.info(path=path)
        return datetime.datetime.fromtimestamp(
            info["created"], tz=datetime.timezone.utc
        )

    def modified(self, path):
        info = self.info(path=path)
        return datetime.datetime.fromtimestamp(info["mtime"], tz=datetime.timezone.utc)

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if os.sep == "/":
            # posix native
            return path.rsplit("/", 1)[0] or "/"
        else:
            # NT
            path_ = path.rsplit("/", 1)[0]
            if len(path_) <= 3:
                if path_[1:2] == ":":
                    # nt root (something like c:/)
                    return path_[0] + ":/"
            # More cases may be required here
            return path_

    @classmethod
    def _strip_protocol(cls, path):
        path = stringify_path(path)
        if path.startswith("file://"):
            path = path[7:]
        elif path.startswith("file:"):
            path = path[5:]
        elif path.startswith("local://"):
            path = path[8:]
        elif path.startswith("local:"):
            path = path[6:]

        path = make_path_posix(path)
        if os.sep != "/":
            # This code-path is a stripped down version of
            # > drive, path = ntpath.splitdrive(path)
            if path[1:2] == ":":
                # Absolute drive-letter path, e.g. X:\Windows
                # Relative path with drive, e.g. X:Windows
                drive, path = path[:2], path[2:]
            elif path[:2] == "//":
                # UNC drives, e.g. \\server\share or \\?\UNC\server\share
                # Device drives, e.g. \\.\device or \\?\device
                if (index1 := path.find("/", 2)) == -1 or (
                    index2 := path.find("/", index1 + 1)
                ) == -1:
                    drive, path = path, ""
                else:
                    drive, path = path[:index2], path[index2:]
            else:
                # Relative path, e.g. Windows
                drive = ""

            path = path.rstrip("/") or cls.root_marker
            return drive + path

        else:
            return path.rstrip("/") or cls.root_marker

    def _isfilestore(self):
        # Inheriting from DaskFileSystem makes this False (S3, etc. were)
        # the original motivation. But we are a posix-like file system.
        # See https://github.com/dask/dask/issues/5526
        return True

    def chmod(self, path, mode):
        path = stringify_path(path)
        return os.chmod(path, mode)


def make_path_posix(path):
    """Make path generic and absolute for current OS"""
    if not isinstance(path, str):
        if isinstance(path, (list, set, tuple)):
            return type(path)(make_path_posix(p) for p in path)
        else:
            path = stringify_path(path)
            if not isinstance(path, str):
                raise TypeError(f"could not convert {path!r} to string")
    if os.sep == "/":
        # Native posix
        if path.startswith("/"):
            # most common fast case for posix
            return path
        elif path.startswith("~"):
            return osp.expanduser(path)
        elif path.startswith("./"):
            path = path[2:]
        elif path == ".":
            path = ""
        return f"{os.getcwd()}/{path}"
    else:
        # NT handling
        if path[0:1] == "/" and path[2:3] == ":":
            # path is like "/c:/local/path"
            path = path[1:]
        if path[1:2] == ":":
            # windows full path like "C:\\local\\path"
            if len(path) <= 3:
                # nt root (something like c:/)
                return path[0] + ":/"
            path = path.replace("\\", "/")
            return path
        elif path[0:1] == "~":
            return make_path_posix(osp.expanduser(path))
        elif path.startswith(("\\\\", "//")):
            # windows UNC/DFS-style paths
            return "//" + path[2:].replace("\\", "/")
        elif path.startswith(("\\", "/")):
            # windows relative path with root
            path = path.replace("\\", "/")
            return f"{osp.splitdrive(os.getcwd())[0]}{path}"
        else:
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            elif path == ".":
                path = ""
            return f"{make_path_posix(os.getcwd())}/{path}"


def trailing_sep(path):
    """Return True if the path ends with a path separator.

    A forward slash is always considered a path separator, even on Operating
    Systems that normally use a backslash.
    """
    # TODO: if all incoming paths were posix-compliant then separator would
    # always be a forward slash, simplifying this function.
    # See https://github.com/fsspec/filesystem_spec/pull/1250
    return path.endswith(os.sep) or (os.altsep is not None and path.endswith(os.altsep))


@lru_cache(maxsize=1)
def get_umask(mask: int = 0o666) -> int:
    """Get the current umask.

    Follows https://stackoverflow.com/a/44130549 to get the umask.
    Temporarily sets the umask to the given value, and then resets it to the
    original value.
    """
    value = os.umask(mask)
    os.umask(value)
    return value


class LocalFileOpener(io.IOBase):
    def __init__(
        self, path, mode, autocommit=True, fs=None, compression=None, **kwargs
    ):
        logger.debug("open file: %s", path)
        self.path = path
        self.mode = mode
        self.fs = fs
        self.f = None
        self.autocommit = autocommit
        self.compression = get_compression(path, compression)
        self.blocksize = io.DEFAULT_BUFFER_SIZE
        self._open()

    def _open(self):
        if self.f is None or self.f.closed:
            if self.autocommit or "w" not in self.mode:
                self.f = open(self.path, mode=self.mode)
                if self.compression:
                    compress = compr[self.compression]
                    self.f = compress(self.f, mode=self.mode)
            else:
                # TODO: check if path is writable?
                i, name = tempfile.mkstemp()
                os.close(i)  # we want normal open and normal buffered file
                self.temp = name
                self.f = open(name, mode=self.mode)
            if "w" not in self.mode:
                self.size = self.f.seek(0, 2)
                self.f.seek(0)
                self.f.size = self.size

    def _fetch_range(self, start, end):
        # probably only used by cached FS
        if "r" not in self.mode:
            raise ValueError
        self._open()
        self.f.seek(start)
        return self.f.read(end - start)

    def __setstate__(self, state):
        self.f = None
        loc = state.pop("loc", None)
        self.__dict__.update(state)
        if "r" in state["mode"]:
            self.f = None
            self._open()
            self.f.seek(loc)

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop("f")
        if "r" in self.mode:
            d["loc"] = self.f.tell()
        else:
            if not self.f.closed:
                raise ValueError("Cannot serialise open write-mode local file")
        return d

    def commit(self):
        if self.autocommit:
            raise RuntimeError("Can only commit if not already set to autocommit")
        try:
            shutil.move(self.temp, self.path)
        except PermissionError as e:
            # shutil.move raises PermissionError if os.rename
            # and the default copy2 fallback with shutil.copystats fail.
            # The file should be there nonetheless, but without copied permissions.
            # If it doesn't exist, there was no permission to create the file.
            if not os.path.exists(self.path):
                raise e
        else:
            # If PermissionError is not raised, permissions can be set.
            try:
                mask = 0o666
                os.chmod(self.path, mask & ~get_umask(mask))
            except RuntimeError:
                pass

    def discard(self):
        if self.autocommit:
            raise RuntimeError("Cannot discard if set to autocommit")
        os.remove(self.temp)

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return "r" not in self.mode

    def read(self, *args, **kwargs):
        return self.f.read(*args, **kwargs)

    def write(self, *args, **kwargs):
        return self.f.write(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self.f.tell(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self.f.seek(*args, **kwargs)

    def seekable(self, *args, **kwargs):
        return self.f.seekable(*args, **kwargs)

    def readline(self, *args, **kwargs):
        return self.f.readline(*args, **kwargs)

    def readlines(self, *args, **kwargs):
        return self.f.readlines(*args, **kwargs)

    def close(self):
        return self.f.close()

    def truncate(self, size=None) -> int:
        return self.f.truncate(size)

    @property
    def closed(self):
        return self.f.closed

    def fileno(self):
        return self.raw.fileno()

    def flush(self) -> None:
        self.f.flush()

    def __iter__(self):
        return self.f.__iter__()

    def __getattr__(self, item):
        return getattr(self.f, item)

    def __enter__(self):
        self._incontext = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._incontext = False
        self.f.__exit__(exc_type, exc_value, traceback)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\gemini\transformation.py ===
"""
Transformation logic from OpenAI format to Gemini format. 

Why separate file? Make it easy to see how transformation works
"""

import os
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple, Union, cast

import httpx
from pydantic import BaseModel

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    _get_image_mime_type_from_url,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    convert_generic_image_chunk_to_openai_image_obj,
    convert_to_anthropic_image_obj,
    convert_to_gemini_tool_call_invoke,
    convert_to_gemini_tool_call_result,
    response_schema_prompt,
)
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.types.files import (
    get_file_mime_type_for_file_type,
    get_file_type_from_extension,
    is_gemini_1_5_accepted_file_type,
)
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionAudioObject,
    ChatCompletionFileObject,
    ChatCompletionImageObject,
    ChatCompletionTextObject,
)
from litellm.types.llms.vertex_ai import *
from litellm.types.llms.vertex_ai import (
    GenerationConfig,
    PartType,
    RequestBody,
    SafetSettingsConfig,
    SystemInstructions,
    ToolConfig,
    Tools,
)
from litellm.types.utils import GenericImageParsingChunk

from ..common_utils import (
    _check_text_in_content,
    get_supports_response_schema,
    get_supports_system_message,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


def _process_gemini_image(image_url: str, format: Optional[str] = None) -> PartType:
    """
    Given an image URL, return the appropriate PartType for Gemini
    """

    try:
        # GCS URIs
        if "gs://" in image_url:
            # Figure out file type
            extension_with_dot = os.path.splitext(image_url)[-1]  # Ex: ".png"
            extension = extension_with_dot[1:]  # Ex: "png"

            if not format:
                file_type = get_file_type_from_extension(extension)

                # Validate the file type is supported by Gemini
                if not is_gemini_1_5_accepted_file_type(file_type):
                    raise Exception(f"File type not supported by gemini - {file_type}")

                mime_type = get_file_mime_type_for_file_type(file_type)
            else:
                mime_type = format
            file_data = FileDataType(mime_type=mime_type, file_uri=image_url)

            return PartType(file_data=file_data)
        elif (
            "https://" in image_url
            and (image_type := format or _get_image_mime_type_from_url(image_url))
            is not None
        ):
            file_data = FileDataType(file_uri=image_url, mime_type=image_type)
            return PartType(file_data=file_data)
        elif "http://" in image_url or "https://" in image_url or "base64" in image_url:
            # https links for unsupported mime types and base64 images
            image = convert_to_anthropic_image_obj(image_url, format=format)
            _blob = BlobType(data=image["data"], mime_type=image["media_type"])
            return PartType(inline_data=_blob)
        raise Exception("Invalid image received - {}".format(image_url))
    except Exception as e:
        raise e


def _gemini_convert_messages_with_history(  # noqa: PLR0915
    messages: List[AllMessageValues],
) -> List[ContentType]:
    """
    Converts given messages from OpenAI format to Gemini format

    - Parts must be iterable
    - Roles must alternate b/w 'user' and 'model' (same as anthropic -> merge consecutive roles)
    - Please ensure that function response turn comes immediately after a function call turn
    """
    user_message_types = {"user", "system"}
    contents: List[ContentType] = []

    last_message_with_tool_calls = None

    msg_i = 0
    tool_call_responses = []
    try:
        while msg_i < len(messages):
            user_content: List[PartType] = []
            init_msg_i = msg_i
            ## MERGE CONSECUTIVE USER CONTENT ##
            while (
                msg_i < len(messages) and messages[msg_i]["role"] in user_message_types
            ):
                _message_content = messages[msg_i].get("content")
                if _message_content is not None and isinstance(_message_content, list):
                    _parts: List[PartType] = []
                    for element_idx, element in enumerate(_message_content):
                        if (
                            element["type"] == "text"
                            and "text" in element
                            and len(element["text"]) > 0
                        ):
                            element = cast(ChatCompletionTextObject, element)
                            _part = PartType(text=element["text"])
                            _parts.append(_part)
                        elif element["type"] == "image_url":
                            element = cast(ChatCompletionImageObject, element)
                            img_element = element
                            format: Optional[str] = None
                            if isinstance(img_element["image_url"], dict):
                                image_url = img_element["image_url"]["url"]
                                format = img_element["image_url"].get("format")
                            else:
                                image_url = img_element["image_url"]
                            _part = _process_gemini_image(
                                image_url=image_url, format=format
                            )
                            _parts.append(_part)
                        elif element["type"] == "input_audio":
                            audio_element = cast(ChatCompletionAudioObject, element)
                            audio_data = audio_element["input_audio"].get("data")
                            audio_format = audio_element["input_audio"].get("format")
                            if audio_data is not None and audio_format is not None:
                                audio_format_modified = (
                                    "audio/" + audio_format
                                    if audio_format.startswith("audio/") is False
                                    else audio_format
                                )  # Gemini expects audio/wav, audio/mp3, etc.
                                openai_image_str = (
                                    convert_generic_image_chunk_to_openai_image_obj(
                                        image_chunk=GenericImageParsingChunk(
                                            type="base64",
                                            media_type=audio_format_modified,
                                            data=audio_data,
                                        )
                                    )
                                )
                                _part = _process_gemini_image(
                                    image_url=openai_image_str,
                                    format=audio_format_modified,
                                )
                                _parts.append(_part)
                        elif element["type"] == "file":
                            file_element = cast(ChatCompletionFileObject, element)
                            file_id = file_element["file"].get("file_id")
                            format = file_element["file"].get("format")
                            file_data = file_element["file"].get("file_data")
                            passed_file = file_id or file_data
                            if passed_file is None:
                                raise Exception(
                                    "Unknown file type. Please pass in a file_id or file_data"
                                )
                            try:
                                _part = _process_gemini_image(
                                    image_url=passed_file, format=format
                                )
                                _parts.append(_part)
                            except Exception:
                                raise Exception(
                                    "Unable to determine mime type for file_id: {}, set this explicitly using message[{}].content[{}].file.format".format(
                                        file_id, msg_i, element_idx
                                    )
                                )
                    user_content.extend(_parts)
                elif (
                    _message_content is not None
                    and isinstance(_message_content, str)
                    and len(_message_content) > 0
                ):
                    _part = PartType(text=_message_content)
                    user_content.append(_part)

                msg_i += 1

            if user_content:
                """
                check that user_content has 'text' parameter.
                    - Known Vertex Error: Unable to submit request because it must have a text parameter.
                    - Relevant Issue: https://github.com/BerriAI/litellm/issues/5515
                """
                has_text_in_content = _check_text_in_content(user_content)
                if has_text_in_content is False:
                    verbose_logger.warning(
                        "No text in user content. Adding a blank text to user content, to ensure Gemini doesn't fail the request. Relevant Issue - https://github.com/BerriAI/litellm/issues/5515"
                    )
                    user_content.append(
                        PartType(text=" ")
                    )  # add a blank text, to ensure Gemini doesn't fail the request.
                contents.append(ContentType(role="user", parts=user_content))
            assistant_content = []
            ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
            while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
                if isinstance(messages[msg_i], BaseModel):
                    msg_dict: Union[ChatCompletionAssistantMessage, dict] = messages[msg_i].model_dump()  # type: ignore
                else:
                    msg_dict = messages[msg_i]  # type: ignore
                assistant_msg = ChatCompletionAssistantMessage(**msg_dict)  # type: ignore
                _message_content = assistant_msg.get("content", None)
                reasoning_content = assistant_msg.get("reasoning_content", None)
                if reasoning_content is not None:
                    assistant_content.append(
                        PartType(thought=True, text=reasoning_content)
                    )
                if _message_content is not None and isinstance(_message_content, list):
                    _parts = []
                    for element in _message_content:
                        if isinstance(element, dict):
                            if element["type"] == "text":
                                _part = PartType(text=element["text"])
                                _parts.append(_part)

                    assistant_content.extend(_parts)
                elif (
                    _message_content is not None
                    and isinstance(_message_content, str)
                    and _message_content
                ):
                    assistant_text = _message_content  # either string or none
                    assistant_content.append(PartType(text=assistant_text))  # type: ignore

                ## HANDLE ASSISTANT FUNCTION CALL
                if (
                    assistant_msg.get("tool_calls", []) is not None
                    or assistant_msg.get("function_call") is not None
                ):  # support assistant tool invoke conversion
                    assistant_content.extend(
                        convert_to_gemini_tool_call_invoke(assistant_msg)
                    )
                    last_message_with_tool_calls = assistant_msg

                msg_i += 1

            if assistant_content:
                contents.append(ContentType(role="model", parts=assistant_content))

            ## APPEND TOOL CALL MESSAGES ##
            tool_call_message_roles = ["tool", "function"]
            if (
                msg_i < len(messages)
                and messages[msg_i]["role"] in tool_call_message_roles
            ):
                _part = convert_to_gemini_tool_call_result(
                    messages[msg_i], last_message_with_tool_calls  # type: ignore
                )
                msg_i += 1
                tool_call_responses.append(_part)
            if msg_i < len(messages) and (
                messages[msg_i]["role"] not in tool_call_message_roles
            ):
                if len(tool_call_responses) > 0:
                    contents.append(ContentType(parts=tool_call_responses))
                    tool_call_responses = []

            if msg_i == init_msg_i:  # prevent infinite loops
                raise Exception(
                    "Invalid Message passed in - {}. File an issue https://github.com/BerriAI/litellm/issues".format(
                        messages[msg_i]
                    )
                )
        if len(tool_call_responses) > 0:
            contents.append(ContentType(parts=tool_call_responses))
        return contents
    except Exception as e:
        raise e


def _transform_request_body(
    messages: List[AllMessageValues],
    model: str,
    optional_params: dict,
    custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"],
    litellm_params: dict,
    cached_content: Optional[str],
) -> RequestBody:
    """
    Common transformation logic across sync + async Gemini /generateContent calls.
    """
    # Separate system prompt from rest of message
    supports_system_message = get_supports_system_message(
        model=model, custom_llm_provider=custom_llm_provider
    )
    system_instructions, messages = _transform_system_message(
        supports_system_message=supports_system_message, messages=messages
    )
    # Checks for 'response_schema' support - if passed in
    if "response_schema" in optional_params:
        supports_response_schema = get_supports_response_schema(
            model=model, custom_llm_provider=custom_llm_provider
        )
        if supports_response_schema is False:
            user_response_schema_message = response_schema_prompt(
                model=model, response_schema=optional_params.get("response_schema")  # type: ignore
            )
            messages.append({"role": "user", "content": user_response_schema_message})
            optional_params.pop("response_schema")

    # Check for any 'litellm_param_*' set during optional param mapping

    remove_keys = []
    for k, v in optional_params.items():
        if k.startswith("litellm_param_"):
            litellm_params.update({k: v})
            remove_keys.append(k)

    optional_params = {k: v for k, v in optional_params.items() if k not in remove_keys}

    try:
        if custom_llm_provider == "gemini":
            content = litellm.GoogleAIStudioGeminiConfig()._transform_messages(
                messages=messages
            )
        else:
            content = litellm.VertexGeminiConfig()._transform_messages(
                messages=messages
            )
        tools: Optional[Tools] = optional_params.pop("tools", None)
        tool_choice: Optional[ToolConfig] = optional_params.pop("tool_choice", None)
        safety_settings: Optional[List[SafetSettingsConfig]] = optional_params.pop(
            "safety_settings", None
        )  # type: ignore
        config_fields = GenerationConfig.__annotations__.keys()

        filtered_params = {
            k: v for k, v in optional_params.items() if k in config_fields
        }

        generation_config: Optional[GenerationConfig] = GenerationConfig(
            **filtered_params
        )
        data = RequestBody(contents=content)
        if system_instructions is not None:
            data["system_instruction"] = system_instructions
        if tools is not None:
            data["tools"] = tools
        if tool_choice is not None:
            data["toolConfig"] = tool_choice
        if safety_settings is not None:
            data["safetySettings"] = safety_settings
        if generation_config is not None:
            data["generationConfig"] = generation_config
        if cached_content is not None:
            data["cachedContent"] = cached_content
    except Exception as e:
        raise e

    return data


def sync_transform_request_body(
    gemini_api_key: Optional[str],
    messages: List[AllMessageValues],
    api_base: Optional[str],
    model: str,
    client: Optional[HTTPHandler],
    timeout: Optional[Union[float, httpx.Timeout]],
    extra_headers: Optional[dict],
    optional_params: dict,
    logging_obj: LiteLLMLoggingObj,
    custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"],
    litellm_params: dict,
) -> RequestBody:
    from ..context_caching.vertex_ai_context_caching import ContextCachingEndpoints

    context_caching_endpoints = ContextCachingEndpoints()

    if gemini_api_key is not None:
        messages, cached_content = context_caching_endpoints.check_and_create_cache(
            messages=messages,
            api_key=gemini_api_key,
            api_base=api_base,
            model=model,
            client=client,
            timeout=timeout,
            extra_headers=extra_headers,
            cached_content=optional_params.pop("cached_content", None),
            logging_obj=logging_obj,
        )
    else:  # [TODO] implement context caching for gemini as well
        cached_content = optional_params.pop("cached_content", None)

    return _transform_request_body(
        messages=messages,
        model=model,
        custom_llm_provider=custom_llm_provider,
        litellm_params=litellm_params,
        cached_content=cached_content,
        optional_params=optional_params,
    )


async def async_transform_request_body(
    gemini_api_key: Optional[str],
    messages: List[AllMessageValues],
    api_base: Optional[str],
    model: str,
    client: Optional[AsyncHTTPHandler],
    timeout: Optional[Union[float, httpx.Timeout]],
    extra_headers: Optional[dict],
    optional_params: dict,
    logging_obj: litellm.litellm_core_utils.litellm_logging.Logging,  # type: ignore
    custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"],
    litellm_params: dict,
) -> RequestBody:
    from ..context_caching.vertex_ai_context_caching import ContextCachingEndpoints

    context_caching_endpoints = ContextCachingEndpoints()

    if gemini_api_key is not None:
        (
            messages,
            cached_content,
        ) = await context_caching_endpoints.async_check_and_create_cache(
            messages=messages,
            api_key=gemini_api_key,
            api_base=api_base,
            model=model,
            client=client,
            timeout=timeout,
            extra_headers=extra_headers,
            cached_content=optional_params.pop("cached_content", None),
            logging_obj=logging_obj,
        )
    else:  # [TODO] implement context caching for gemini as well
        cached_content = optional_params.pop("cached_content", None)

    return _transform_request_body(
        messages=messages,
        model=model,
        custom_llm_provider=custom_llm_provider,
        litellm_params=litellm_params,
        cached_content=cached_content,
        optional_params=optional_params,
    )


def _transform_system_message(
    supports_system_message: bool, messages: List[AllMessageValues]
) -> Tuple[Optional[SystemInstructions], List[AllMessageValues]]:
    """
    Extracts the system message from the openai message list.

    Converts the system message to Gemini format

    Returns
    - system_content_blocks: Optional[SystemInstructions] - the system message list in Gemini format.
    - messages: List[AllMessageValues] - filtered list of messages in OpenAI format (transformed separately)
    """
    # Separate system prompt from rest of message
    system_prompt_indices = []
    system_content_blocks: List[PartType] = []
    if supports_system_message is True:
        for idx, message in enumerate(messages):
            if message["role"] == "system":
                _system_content_block: Optional[PartType] = None
                if isinstance(message["content"], str):
                    _system_content_block = PartType(text=message["content"])
                elif isinstance(message["content"], list):
                    system_text = ""
                    for content in message["content"]:
                        system_text += content.get("text") or ""
                    _system_content_block = PartType(text=system_text)
                if _system_content_block is not None:
                    system_content_blocks.append(_system_content_block)
                    system_prompt_indices.append(idx)
        if len(system_prompt_indices) > 0:
            for idx in reversed(system_prompt_indices):
                messages.pop(idx)

    if len(system_content_blocks) > 0:
        return SystemInstructions(parts=system_content_blocks), messages

    return None, messages

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\timit.py ===
# Natural Language Toolkit: TIMIT Corpus Reader
#
# Copyright (C) 2001-2007 NLTK Project
# Author: Haejoong Lee <haejoong@ldc.upenn.edu>
#         Steven Bird <stevenbird1@gmail.com>
#         Jacob Perkins <japerk@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# [xx] this docstring is out-of-date:
"""
Read tokens, phonemes and audio data from the NLTK TIMIT Corpus.

This corpus contains selected portion of the TIMIT corpus.

 - 16 speakers from 8 dialect regions
 - 1 male and 1 female from each dialect region
 - total 130 sentences (10 sentences per speaker.  Note that some
   sentences are shared among other speakers, especially sa1 and sa2
   are spoken by all speakers.)
 - total 160 recording of sentences (10 recordings per speaker)
 - audio format: NIST Sphere, single channel, 16kHz sampling,
   16 bit sample, PCM encoding


Module contents
===============

The timit corpus reader provides 4 functions and 4 data items.

 - utterances

   List of utterances in the corpus.  There are total 160 utterances,
   each of which corresponds to a unique utterance of a speaker.
   Here's an example of an utterance identifier in the list::

       dr1-fvmh0/sx206
         - _----  _---
         | |  |   | |
         | |  |   | |
         | |  |   | `--- sentence number
         | |  |   `----- sentence type (a:all, i:shared, x:exclusive)
         | |  `--------- speaker ID
         | `------------ sex (m:male, f:female)
         `-------------- dialect region (1..8)

 - speakers

   List of speaker IDs.  An example of speaker ID::

       dr1-fvmh0

   Note that if you split an item ID with colon and take the first element of
   the result, you will get a speaker ID.

       >>> itemid = 'dr1-fvmh0/sx206'
       >>> spkrid , sentid = itemid.split('/')
       >>> spkrid
       'dr1-fvmh0'

   The second element of the result is a sentence ID.

 - dictionary()

   Phonetic dictionary of words contained in this corpus.  This is a Python
   dictionary from words to phoneme lists.

 - spkrinfo()

   Speaker information table.  It's a Python dictionary from speaker IDs to
   records of 10 fields.  Speaker IDs the same as the ones in timie.speakers.
   Each record is a dictionary from field names to values, and the fields are
   as follows::

     id         speaker ID as defined in the original TIMIT speaker info table
     sex        speaker gender (M:male, F:female)
     dr         speaker dialect region (1:new england, 2:northern,
                3:north midland, 4:south midland, 5:southern, 6:new york city,
                7:western, 8:army brat (moved around))
     use        corpus type (TRN:training, TST:test)
                in this sample corpus only TRN is available
     recdate    recording date
     birthdate  speaker birth date
     ht         speaker height
     race       speaker race (WHT:white, BLK:black, AMR:american indian,
                SPN:spanish-american, ORN:oriental,???:unknown)
     edu        speaker education level (HS:high school, AS:associate degree,
                BS:bachelor's degree (BS or BA), MS:master's degree (MS or MA),
                PHD:doctorate degree (PhD,JD,MD), ??:unknown)
     comments   comments by the recorder

The 4 functions are as follows.

 - tokenized(sentences=items, offset=False)

   Given a list of items, returns an iterator of a list of word lists,
   each of which corresponds to an item (sentence).  If offset is set to True,
   each element of the word list is a tuple of word(string), start offset and
   end offset, where offset is represented as a number of 16kHz samples.

 - phonetic(sentences=items, offset=False)

   Given a list of items, returns an iterator of a list of phoneme lists,
   each of which corresponds to an item (sentence).  If offset is set to True,
   each element of the phoneme list is a tuple of word(string), start offset
   and end offset, where offset is represented as a number of 16kHz samples.

 - audiodata(item, start=0, end=None)

   Given an item, returns a chunk of audio samples formatted into a string.
   When the function is called, if start and end are omitted, the entire
   samples of the recording will be returned.  If only end is omitted,
   samples from the start offset to the end of the recording will be returned.

 - play(data)

   Play the given audio samples. The audio samples can be obtained from the
   timit.audiodata function.

"""
import sys
import time

from nltk.corpus.reader.api import *
from nltk.internals import import_from_stdlib
from nltk.tree import Tree


class TimitCorpusReader(CorpusReader):
    """
    Reader for the TIMIT corpus (or any other corpus with the same
    file layout and use of file formats).  The corpus root directory
    should contain the following files:

      - timitdic.txt: dictionary of standard transcriptions
      - spkrinfo.txt: table of speaker information

    In addition, the root directory should contain one subdirectory
    for each speaker, containing three files for each utterance:

      - <utterance-id>.txt: text content of utterances
      - <utterance-id>.wrd: tokenized text content of utterances
      - <utterance-id>.phn: phonetic transcription of utterances
      - <utterance-id>.wav: utterance sound file
    """

    _FILE_RE = r"(\w+-\w+/\w+\.(phn|txt|wav|wrd))|" + r"timitdic\.txt|spkrinfo\.txt"
    """A regexp matching fileids that are used by this corpus reader."""
    _UTTERANCE_RE = r"\w+-\w+/\w+\.txt"

    def __init__(self, root, encoding="utf8"):
        """
        Construct a new TIMIT corpus reader in the given directory.
        :param root: The root directory for this corpus.
        """
        # Ensure that wave files don't get treated as unicode data:
        if isinstance(encoding, str):
            encoding = [(r".*\.wav", None), (".*", encoding)]

        CorpusReader.__init__(
            self, root, find_corpus_fileids(root, self._FILE_RE), encoding=encoding
        )

        self._utterances = [
            name[:-4] for name in find_corpus_fileids(root, self._UTTERANCE_RE)
        ]
        """A list of the utterance identifiers for all utterances in
        this corpus."""

        self._speakerinfo = None
        self._root = root
        self.speakers = sorted({u.split("/")[0] for u in self._utterances})

    def fileids(self, filetype=None):
        """
        Return a list of file identifiers for the files that make up
        this corpus.

        :param filetype: If specified, then ``filetype`` indicates that
            only the files that have the given type should be
            returned.  Accepted values are: ``txt``, ``wrd``, ``phn``,
            ``wav``, or ``metadata``,
        """
        if filetype is None:
            return CorpusReader.fileids(self)
        elif filetype in ("txt", "wrd", "phn", "wav"):
            return [f"{u}.{filetype}" for u in self._utterances]
        elif filetype == "metadata":
            return ["timitdic.txt", "spkrinfo.txt"]
        else:
            raise ValueError("Bad value for filetype: %r" % filetype)

    def utteranceids(
        self, dialect=None, sex=None, spkrid=None, sent_type=None, sentid=None
    ):
        """
        :return: A list of the utterance identifiers for all
            utterances in this corpus, or for the given speaker, dialect
            region, gender, sentence type, or sentence number, if
            specified.
        """
        if isinstance(dialect, str):
            dialect = [dialect]
        if isinstance(sex, str):
            sex = [sex]
        if isinstance(spkrid, str):
            spkrid = [spkrid]
        if isinstance(sent_type, str):
            sent_type = [sent_type]
        if isinstance(sentid, str):
            sentid = [sentid]

        utterances = self._utterances[:]
        if dialect is not None:
            utterances = [u for u in utterances if u[2] in dialect]
        if sex is not None:
            utterances = [u for u in utterances if u[4] in sex]
        if spkrid is not None:
            utterances = [u for u in utterances if u[:9] in spkrid]
        if sent_type is not None:
            utterances = [u for u in utterances if u[11] in sent_type]
        if sentid is not None:
            utterances = [u for u in utterances if u[10:] in spkrid]
        return utterances

    def transcription_dict(self):
        """
        :return: A dictionary giving the 'standard' transcription for
            each word.
        """
        _transcriptions = {}
        with self.open("timitdic.txt") as fp:
            for line in fp:
                if not line.strip() or line[0] == ";":
                    continue
                m = re.match(r"\s*(\S+)\s+/(.*)/\s*$", line)
                if not m:
                    raise ValueError("Bad line: %r" % line)
                _transcriptions[m.group(1)] = m.group(2).split()
        return _transcriptions

    def spkrid(self, utterance):
        return utterance.split("/")[0]

    def sentid(self, utterance):
        return utterance.split("/")[1]

    def utterance(self, spkrid, sentid):
        return f"{spkrid}/{sentid}"

    def spkrutteranceids(self, speaker):
        """
        :return: A list of all utterances associated with a given
            speaker.
        """
        return [
            utterance
            for utterance in self._utterances
            if utterance.startswith(speaker + "/")
        ]

    def spkrinfo(self, speaker):
        """
        :return: A dictionary mapping .. something.
        """
        if speaker in self._utterances:
            speaker = self.spkrid(speaker)

        if self._speakerinfo is None:
            self._speakerinfo = {}
            with self.open("spkrinfo.txt") as fp:
                for line in fp:
                    if not line.strip() or line[0] == ";":
                        continue
                    rec = line.strip().split(None, 9)
                    key = f"dr{rec[2]}-{rec[1].lower()}{rec[0].lower()}"
                    self._speakerinfo[key] = SpeakerInfo(*rec)

        return self._speakerinfo[speaker]

    def phones(self, utterances=None):
        results = []
        for fileid in self._utterance_fileids(utterances, ".phn"):
            with self.open(fileid) as fp:
                for line in fp:
                    if line.strip():
                        results.append(line.split()[-1])
        return results

    def phone_times(self, utterances=None):
        """
        offset is represented as a number of 16kHz samples!
        """
        results = []
        for fileid in self._utterance_fileids(utterances, ".phn"):
            with self.open(fileid) as fp:
                for line in fp:
                    if line.strip():
                        results.append(
                            (
                                line.split()[2],
                                int(line.split()[0]),
                                int(line.split()[1]),
                            )
                        )
        return results

    def words(self, utterances=None):
        results = []
        for fileid in self._utterance_fileids(utterances, ".wrd"):
            with self.open(fileid) as fp:
                for line in fp:
                    if line.strip():
                        results.append(line.split()[-1])
        return results

    def word_times(self, utterances=None):
        results = []
        for fileid in self._utterance_fileids(utterances, ".wrd"):
            with self.open(fileid) as fp:
                for line in fp:
                    if line.strip():
                        results.append(
                            (
                                line.split()[2],
                                int(line.split()[0]),
                                int(line.split()[1]),
                            )
                        )
        return results

    def sents(self, utterances=None):
        results = []
        for fileid in self._utterance_fileids(utterances, ".wrd"):
            with self.open(fileid) as fp:
                results.append([line.split()[-1] for line in fp if line.strip()])
        return results

    def sent_times(self, utterances=None):
        # TODO: Check this
        return [
            (
                line.split(None, 2)[-1].strip(),
                int(line.split()[0]),
                int(line.split()[1]),
            )
            for fileid in self._utterance_fileids(utterances, ".txt")
            for line in self.open(fileid)
            if line.strip()
        ]

    def phone_trees(self, utterances=None):
        if utterances is None:
            utterances = self._utterances
        if isinstance(utterances, str):
            utterances = [utterances]

        trees = []
        for utterance in utterances:
            word_times = self.word_times(utterance)
            phone_times = self.phone_times(utterance)
            sent_times = self.sent_times(utterance)

            while sent_times:
                (sent, sent_start, sent_end) = sent_times.pop(0)
                trees.append(Tree("S", []))
                while (
                    word_times and phone_times and phone_times[0][2] <= word_times[0][1]
                ):
                    trees[-1].append(phone_times.pop(0)[0])
                while word_times and word_times[0][2] <= sent_end:
                    (word, word_start, word_end) = word_times.pop(0)
                    trees[-1].append(Tree(word, []))
                    while phone_times and phone_times[0][2] <= word_end:
                        trees[-1][-1].append(phone_times.pop(0)[0])
                while phone_times and phone_times[0][2] <= sent_end:
                    trees[-1].append(phone_times.pop(0)[0])
        return trees

    # [xx] NOTE: This is currently broken -- we're assuming that the
    # fileids are WAV fileids (aka RIFF), but they're actually NIST SPHERE
    # fileids.
    def wav(self, utterance, start=0, end=None):
        # nltk.chunk conflicts with the stdlib module 'chunk'
        wave = import_from_stdlib("wave")

        w = wave.open(self.open(utterance + ".wav"), "rb")

        if end is None:
            end = w.getnframes()

        # Skip past frames before start, then read the frames we want
        w.readframes(start)
        frames = w.readframes(end - start)

        # Open a new temporary file -- the wave module requires
        # an actual file, and won't work w/ stringio. :(
        tf = tempfile.TemporaryFile()
        out = wave.open(tf, "w")

        # Write the parameters & data to the new file.
        out.setparams(w.getparams())
        out.writeframes(frames)
        out.close()

        # Read the data back from the file, and return it.  The
        # file will automatically be deleted when we return.
        tf.seek(0)
        return tf.read()

    def audiodata(self, utterance, start=0, end=None):
        assert end is None or end > start
        headersize = 44
        with self.open(utterance + ".wav") as fp:
            if end is None:
                data = fp.read()
            else:
                data = fp.read(headersize + end * 2)
        return data[headersize + start * 2 :]

    def _utterance_fileids(self, utterances, extension):
        if utterances is None:
            utterances = self._utterances
        if isinstance(utterances, str):
            utterances = [utterances]
        return [f"{u}{extension}" for u in utterances]

    def play(self, utterance, start=0, end=None):
        """
        Play the given audio sample.

        :param utterance: The utterance id of the sample to play
        """
        # Method 1: os audio dev.
        try:
            import ossaudiodev

            try:
                dsp = ossaudiodev.open("w")
                dsp.setfmt(ossaudiodev.AFMT_S16_LE)
                dsp.channels(1)
                dsp.speed(16000)
                dsp.write(self.audiodata(utterance, start, end))
                dsp.close()
            except OSError as e:
                print(
                    (
                        "can't acquire the audio device; please "
                        "activate your audio device."
                    ),
                    file=sys.stderr,
                )
                print("system error message:", str(e), file=sys.stderr)
            return
        except ImportError:
            pass

        # Method 2: pygame
        try:
            # FIXME: this won't work under python 3
            import pygame.mixer
            import StringIO

            pygame.mixer.init(16000)
            f = StringIO.StringIO(self.wav(utterance, start, end))
            pygame.mixer.Sound(f).play()
            while pygame.mixer.get_busy():
                time.sleep(0.01)
            return
        except ImportError:
            pass

        # Method 3: complain. :)
        print(
            ("you must install pygame or ossaudiodev " "for audio playback."),
            file=sys.stderr,
        )


class SpeakerInfo:
    def __init__(
        self, id, sex, dr, use, recdate, birthdate, ht, race, edu, comments=None
    ):
        self.id = id
        self.sex = sex
        self.dr = dr
        self.use = use
        self.recdate = recdate
        self.birthdate = birthdate
        self.ht = ht
        self.race = race
        self.edu = edu
        self.comments = comments

    def __repr__(self):
        attribs = "id sex dr use recdate birthdate ht race edu comments"
        args = [f"{attr}={getattr(self, attr)!r}" for attr in attribs.split()]
        return "SpeakerInfo(%s)" % (", ".join(args))


def read_timit_block(stream):
    """
    Block reader for timit tagged sentences, which are preceded by a sentence
    number that will be ignored.
    """
    line = stream.readline()
    if not line:
        return []
    n, sent = line.split(" ", 1)
    return [sent]

# === NexusCore/openenv\Lib\site-packages\matplotlib\_api\deprecation.py ===
"""
Helper functions for deprecating parts of the Matplotlib API.

This documentation is only relevant for Matplotlib developers, not for users.

.. warning::

    This module is for internal use only.  Do not use it in your own code.
    We may change the API at any time with no warning.

"""

import contextlib
import functools
import inspect
import math
import warnings


class MatplotlibDeprecationWarning(DeprecationWarning):
    """A class for issuing deprecation warnings for Matplotlib users."""


def _generate_deprecation_warning(
        since, message='', name='', alternative='', pending=False, obj_type='',
        addendum='', *, removal=''):
    if pending:
        if removal:
            raise ValueError("A pending deprecation cannot have a scheduled removal")
    elif removal == '':
        macro, meso, *_ = since.split('.')
        removal = f'{macro}.{int(meso) + 2}'
    if not message:
        message = (
            ("The %(name)s %(obj_type)s" if obj_type else "%(name)s") +
            (" will be deprecated in a future version" if pending else
             (" was deprecated in Matplotlib %(since)s" +
              (" and will be removed in %(removal)s" if removal else ""))) +
            "." +
            (" Use %(alternative)s instead." if alternative else "") +
            (" %(addendum)s" if addendum else ""))
    warning_cls = PendingDeprecationWarning if pending else MatplotlibDeprecationWarning
    return warning_cls(message % dict(
        func=name, name=name, obj_type=obj_type, since=since, removal=removal,
        alternative=alternative, addendum=addendum))


def warn_deprecated(
        since, *, message='', name='', alternative='', pending=False,
        obj_type='', addendum='', removal=''):
    """
    Display a standardized deprecation.

    Parameters
    ----------
    since : str
        The release at which this API became deprecated.
    message : str, optional
        Override the default deprecation message.  The ``%(since)s``,
        ``%(name)s``, ``%(alternative)s``, ``%(obj_type)s``, ``%(addendum)s``,
        and ``%(removal)s`` format specifiers will be replaced by the values
        of the respective arguments passed to this function.
    name : str, optional
        The name of the deprecated object.
    alternative : str, optional
        An alternative API that the user may use in place of the deprecated
        API.  The deprecation warning will tell the user about this alternative
        if provided.
    pending : bool, optional
        If True, uses a PendingDeprecationWarning instead of a
        DeprecationWarning.  Cannot be used together with *removal*.
    obj_type : str, optional
        The object type being deprecated.
    addendum : str, optional
        Additional text appended directly to the final message.
    removal : str, optional
        The expected removal version.  With the default (an empty string), a
        removal version is automatically computed from *since*.  Set to other
        Falsy values to not schedule a removal date.  Cannot be used together
        with *pending*.

    Examples
    --------
    ::

        # To warn of the deprecation of "matplotlib.name_of_module"
        warn_deprecated('1.4.0', name='matplotlib.name_of_module',
                        obj_type='module')
    """
    warning = _generate_deprecation_warning(
        since, message, name, alternative, pending, obj_type, addendum,
        removal=removal)
    from . import warn_external
    warn_external(warning, category=MatplotlibDeprecationWarning)


def deprecated(since, *, message='', name='', alternative='', pending=False,
               obj_type=None, addendum='', removal=''):
    """
    Decorator to mark a function, a class, or a property as deprecated.

    When deprecating a classmethod, a staticmethod, or a property, the
    ``@deprecated`` decorator should go *under* ``@classmethod`` and
    ``@staticmethod`` (i.e., `deprecated` should directly decorate the
    underlying callable), but *over* ``@property``.

    When deprecating a class ``C`` intended to be used as a base class in a
    multiple inheritance hierarchy, ``C`` *must* define an ``__init__`` method
    (if ``C`` instead inherited its ``__init__`` from its own base class, then
    ``@deprecated`` would mess up ``__init__`` inheritance when installing its
    own (deprecation-emitting) ``C.__init__``).

    Parameters are the same as for `warn_deprecated`, except that *obj_type*
    defaults to 'class' if decorating a class, 'attribute' if decorating a
    property, and 'function' otherwise.

    Examples
    --------
    ::

        @deprecated('1.4.0')
        def the_function_to_deprecate():
            pass
    """

    def deprecate(obj, message=message, name=name, alternative=alternative,
                  pending=pending, obj_type=obj_type, addendum=addendum):
        from matplotlib._api import classproperty

        if isinstance(obj, type):
            if obj_type is None:
                obj_type = "class"
            func = obj.__init__
            name = name or obj.__name__
            old_doc = obj.__doc__

            def finalize(wrapper, new_doc):
                try:
                    obj.__doc__ = new_doc
                except AttributeError:  # Can't set on some extension objects.
                    pass
                obj.__init__ = functools.wraps(obj.__init__)(wrapper)
                return obj

        elif isinstance(obj, (property, classproperty)):
            if obj_type is None:
                obj_type = "attribute"
            func = None
            name = name or obj.fget.__name__
            old_doc = obj.__doc__

            class _deprecated_property(type(obj)):
                def __get__(self, instance, owner=None):
                    if instance is not None or owner is not None \
                            and isinstance(self, classproperty):
                        emit_warning()
                    return super().__get__(instance, owner)

                def __set__(self, instance, value):
                    if instance is not None:
                        emit_warning()
                    return super().__set__(instance, value)

                def __delete__(self, instance):
                    if instance is not None:
                        emit_warning()
                    return super().__delete__(instance)

                def __set_name__(self, owner, set_name):
                    nonlocal name
                    if name == "<lambda>":
                        name = set_name

            def finalize(_, new_doc):
                return _deprecated_property(
                    fget=obj.fget, fset=obj.fset, fdel=obj.fdel, doc=new_doc)

        else:
            if obj_type is None:
                obj_type = "function"
            func = obj
            name = name or obj.__name__
            old_doc = func.__doc__

            def finalize(wrapper, new_doc):
                wrapper = functools.wraps(func)(wrapper)
                wrapper.__doc__ = new_doc
                return wrapper

        def emit_warning():
            warn_deprecated(
                since, message=message, name=name, alternative=alternative,
                pending=pending, obj_type=obj_type, addendum=addendum,
                removal=removal)

        def wrapper(*args, **kwargs):
            emit_warning()
            return func(*args, **kwargs)

        old_doc = inspect.cleandoc(old_doc or '').strip('\n')

        notes_header = '\nNotes\n-----'
        second_arg = ' '.join([t.strip() for t in
                               (message, f"Use {alternative} instead."
                                if alternative else "", addendum) if t])
        new_doc = (f"[*Deprecated*] {old_doc}\n"
                   f"{notes_header if notes_header not in old_doc else ''}\n"
                   f".. deprecated:: {since}\n"
                   f"   {second_arg}")

        if not old_doc:
            # This is to prevent a spurious 'unexpected unindent' warning from
            # docutils when the original docstring was blank.
            new_doc += r'\ '

        return finalize(wrapper, new_doc)

    return deprecate


class deprecate_privatize_attribute:
    """
    Helper to deprecate public access to an attribute (or method).

    This helper should only be used at class scope, as follows::

        class Foo:
            attr = _deprecate_privatize_attribute(*args, **kwargs)

    where *all* parameters are forwarded to `deprecated`.  This form makes
    ``attr`` a property which forwards read and write access to ``self._attr``
    (same name but with a leading underscore), with a deprecation warning.
    Note that the attribute name is derived from *the name this helper is
    assigned to*.  This helper also works for deprecating methods.
    """

    def __init__(self, *args, **kwargs):
        self.deprecator = deprecated(*args, **kwargs)

    def __set_name__(self, owner, name):
        setattr(owner, name, self.deprecator(
            property(lambda self: getattr(self, f"_{name}"),
                     lambda self, value: setattr(self, f"_{name}", value)),
            name=name))


# Used by _copy_docstring_and_deprecators to redecorate pyplot wrappers and
# boilerplate.py to retrieve original signatures.  It may seem natural to store
# this information as an attribute on the wrapper, but if the wrapper gets
# itself functools.wraps()ed, then such attributes are silently propagated to
# the outer wrapper, which is not desired.
DECORATORS = {}


def rename_parameter(since, old, new, func=None):
    """
    Decorator indicating that parameter *old* of *func* is renamed to *new*.

    The actual implementation of *func* should use *new*, not *old*.  If *old*
    is passed to *func*, a DeprecationWarning is emitted, and its value is
    used, even if *new* is also passed by keyword (this is to simplify pyplot
    wrapper functions, which always pass *new* explicitly to the Axes method).
    If *new* is also passed but positionally, a TypeError will be raised by the
    underlying function during argument binding.

    Examples
    --------
    ::

        @_api.rename_parameter("3.1", "bad_name", "good_name")
        def func(good_name): ...
    """

    decorator = functools.partial(rename_parameter, since, old, new)

    if func is None:
        return decorator

    signature = inspect.signature(func)
    assert old not in signature.parameters, (
        f"Matplotlib internal error: {old!r} cannot be a parameter for "
        f"{func.__name__}()")
    assert new in signature.parameters, (
        f"Matplotlib internal error: {new!r} must be a parameter for "
        f"{func.__name__}()")

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if old in kwargs:
            warn_deprecated(
                since, message=f"The {old!r} parameter of {func.__name__}() "
                f"has been renamed {new!r} since Matplotlib {since}; support "
                f"for the old name will be dropped in %(removal)s.")
            kwargs[new] = kwargs.pop(old)
        return func(*args, **kwargs)

    # wrapper() must keep the same documented signature as func(): if we
    # instead made both *old* and *new* appear in wrapper()'s signature, they
    # would both show up in the pyplot function for an Axes method as well and
    # pyplot would explicitly pass both arguments to the Axes method.

    DECORATORS[wrapper] = decorator
    return wrapper


class _deprecated_parameter_class:
    def __repr__(self):
        return "<deprecated parameter>"


_deprecated_parameter = _deprecated_parameter_class()


def delete_parameter(since, name, func=None, **kwargs):
    """
    Decorator indicating that parameter *name* of *func* is being deprecated.

    The actual implementation of *func* should keep the *name* parameter in its
    signature, or accept a ``**kwargs`` argument (through which *name* would be
    passed).

    Parameters that come after the deprecated parameter effectively become
    keyword-only (as they cannot be passed positionally without triggering the
    DeprecationWarning on the deprecated parameter), and should be marked as
    such after the deprecation period has passed and the deprecated parameter
    is removed.

    Parameters other than *since*, *name*, and *func* are keyword-only and
    forwarded to `.warn_deprecated`.

    Examples
    --------
    ::

        @_api.delete_parameter("3.1", "unused")
        def func(used_arg, other_arg, unused, more_args): ...
    """

    decorator = functools.partial(delete_parameter, since, name, **kwargs)

    if func is None:
        return decorator

    signature = inspect.signature(func)
    # Name of `**kwargs` parameter of the decorated function, typically
    # "kwargs" if such a parameter exists, or None if the decorated function
    # doesn't accept `**kwargs`.
    kwargs_name = next((param.name for param in signature.parameters.values()
                        if param.kind == inspect.Parameter.VAR_KEYWORD), None)
    if name in signature.parameters:
        kind = signature.parameters[name].kind
        is_varargs = kind is inspect.Parameter.VAR_POSITIONAL
        is_varkwargs = kind is inspect.Parameter.VAR_KEYWORD
        if not is_varargs and not is_varkwargs:
            name_idx = (
                # Deprecated parameter can't be passed positionally.
                math.inf if kind is inspect.Parameter.KEYWORD_ONLY
                # If call site has no more than this number of parameters, the
                # deprecated parameter can't have been passed positionally.
                else [*signature.parameters].index(name))
            func.__signature__ = signature = signature.replace(parameters=[
                param.replace(default=_deprecated_parameter)
                if param.name == name else param
                for param in signature.parameters.values()])
        else:
            name_idx = -1  # Deprecated parameter can always have been passed.
    else:
        is_varargs = is_varkwargs = False
        # Deprecated parameter can't be passed positionally.
        name_idx = math.inf
        assert kwargs_name, (
            f"Matplotlib internal error: {name!r} must be a parameter for "
            f"{func.__name__}()")

    addendum = kwargs.pop('addendum', None)

    @functools.wraps(func)
    def wrapper(*inner_args, **inner_kwargs):
        if len(inner_args) <= name_idx and name not in inner_kwargs:
            # Early return in the simple, non-deprecated case (much faster than
            # calling bind()).
            return func(*inner_args, **inner_kwargs)
        arguments = signature.bind(*inner_args, **inner_kwargs).arguments
        if is_varargs and arguments.get(name):
            warn_deprecated(
                since, message=f"Additional positional arguments to "
                f"{func.__name__}() are deprecated since %(since)s and "
                f"support for them will be removed in %(removal)s.")
        elif is_varkwargs and arguments.get(name):
            warn_deprecated(
                since, message=f"Additional keyword arguments to "
                f"{func.__name__}() are deprecated since %(since)s and "
                f"support for them will be removed in %(removal)s.")
        # We cannot just check `name not in arguments` because the pyplot
        # wrappers always pass all arguments explicitly.
        elif any(name in d and d[name] != _deprecated_parameter
                 for d in [arguments, arguments.get(kwargs_name, {})]):
            deprecation_addendum = (
                f"If any parameter follows {name!r}, they should be passed as "
                f"keyword, not positionally.")
            warn_deprecated(
                since,
                name=repr(name),
                obj_type=f"parameter of {func.__name__}()",
                addendum=(addendum + " " + deprecation_addendum) if addendum
                         else deprecation_addendum,
                **kwargs)
        return func(*inner_args, **inner_kwargs)

    DECORATORS[wrapper] = decorator
    return wrapper


def make_keyword_only(since, name, func=None):
    """
    Decorator indicating that passing parameter *name* (or any of the following
    ones) positionally to *func* is being deprecated.

    When used on a method that has a pyplot wrapper, this should be the
    outermost decorator, so that :file:`boilerplate.py` can access the original
    signature.
    """

    decorator = functools.partial(make_keyword_only, since, name)

    if func is None:
        return decorator

    signature = inspect.signature(func)
    POK = inspect.Parameter.POSITIONAL_OR_KEYWORD
    KWO = inspect.Parameter.KEYWORD_ONLY
    assert (name in signature.parameters
            and signature.parameters[name].kind == POK), (
        f"Matplotlib internal error: {name!r} must be a positional-or-keyword "
        f"parameter for {func.__name__}(). If this error happens on a function with a "
        f"pyplot wrapper, make sure make_keyword_only() is the outermost decorator.")
    names = [*signature.parameters]
    name_idx = names.index(name)
    kwonly = [name for name in names[name_idx:]
              if signature.parameters[name].kind == POK]

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Don't use signature.bind here, as it would fail when stacked with
        # rename_parameter and an "old" argument name is passed in
        # (signature.bind would fail, but the actual call would succeed).
        if len(args) > name_idx:
            warn_deprecated(
                since, message="Passing the %(name)s %(obj_type)s "
                "positionally is deprecated since Matplotlib %(since)s; the "
                "parameter will become keyword-only in %(removal)s.",
                name=name, obj_type=f"parameter of {func.__name__}()")
        return func(*args, **kwargs)

    # Don't modify *func*'s signature, as boilerplate.py needs it.
    wrapper.__signature__ = signature.replace(parameters=[
        param.replace(kind=KWO) if param.name in kwonly else param
        for param in signature.parameters.values()])
    DECORATORS[wrapper] = decorator
    return wrapper


def deprecate_method_override(method, obj, *, allow_empty=False, **kwargs):
    """
    Return ``obj.method`` with a deprecation if it was overridden, else None.

    Parameters
    ----------
    method
        An unbound method, i.e. an expression of the form
        ``Class.method_name``.  Remember that within the body of a method, one
        can always use ``__class__`` to refer to the class that is currently
        being defined.
    obj
        Either an object of the class where *method* is defined, or a subclass
        of that class.
    allow_empty : bool, default: False
        Whether to allow overrides by "empty" methods without emitting a
        warning.
    **kwargs
        Additional parameters passed to `warn_deprecated` to generate the
        deprecation warning; must at least include the "since" key.
    """

    def empty(): pass
    def empty_with_docstring(): """doc"""

    name = method.__name__
    bound_child = getattr(obj, name)
    bound_base = (
        method  # If obj is a class, then we need to use unbound methods.
        if isinstance(bound_child, type(empty)) and isinstance(obj, type)
        else method.__get__(obj))
    if (bound_child != bound_base
            and (not allow_empty
                 or (getattr(getattr(bound_child, "__code__", None),
                             "co_code", None)
                     not in [empty.__code__.co_code,
                             empty_with_docstring.__code__.co_code]))):
        warn_deprecated(**{"name": name, "obj_type": "method", **kwargs})
        return bound_child
    return None


@contextlib.contextmanager
def suppress_matplotlib_deprecation_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MatplotlibDeprecationWarning)
        yield

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\index.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
try:
    from threading import Thread
except ImportError:  # pragma: no cover
    from dummy_threading import Thread

from . import DistlibException
from .compat import (HTTPBasicAuthHandler, Request, HTTPPasswordMgr,
                     urlparse, build_opener, string_types)
from .util import zip_dir, ServerProxy

logger = logging.getLogger(__name__)

DEFAULT_INDEX = 'https://pypi.org/pypi'
DEFAULT_REALM = 'pypi'


class PackageIndex(object):
    """
    This class represents a package index compatible with PyPI, the Python
    Package Index.
    """

    boundary = b'----------ThIs_Is_tHe_distlib_index_bouNdaRY_$'

    def __init__(self, url=None):
        """
        Initialise an instance.

        :param url: The URL of the index. If not specified, the URL for PyPI is
                    used.
        """
        self.url = url or DEFAULT_INDEX
        self.read_configuration()
        scheme, netloc, path, params, query, frag = urlparse(self.url)
        if params or query or frag or scheme not in ('http', 'https'):
            raise DistlibException('invalid repository: %s' % self.url)
        self.password_handler = None
        self.ssl_verifier = None
        self.gpg = None
        self.gpg_home = None
        with open(os.devnull, 'w') as sink:
            # Use gpg by default rather than gpg2, as gpg2 insists on
            # prompting for passwords
            for s in ('gpg', 'gpg2'):
                try:
                    rc = subprocess.check_call([s, '--version'], stdout=sink,
                                               stderr=sink)
                    if rc == 0:
                        self.gpg = s
                        break
                except OSError:
                    pass

    def _get_pypirc_command(self):
        """
        Get the distutils command for interacting with PyPI configurations.
        :return: the command.
        """
        from .util import _get_pypirc_command as cmd
        return cmd()

    def read_configuration(self):
        """
        Read the PyPI access configuration as supported by distutils. This populates
        ``username``, ``password``, ``realm`` and ``url`` attributes from the
        configuration.
        """
        from .util import _load_pypirc
        cfg = _load_pypirc(self)
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.realm = cfg.get('realm', 'pypi')
        self.url = cfg.get('repository', self.url)

    def save_configuration(self):
        """
        Save the PyPI access configuration. You must have set ``username`` and
        ``password`` attributes before calling this method.
        """
        self.check_credentials()
        from .util import _store_pypirc
        _store_pypirc(self)

    def check_credentials(self):
        """
        Check that ``username`` and ``password`` have been set, and raise an
        exception if not.
        """
        if self.username is None or self.password is None:
            raise DistlibException('username and password must be set')
        pm = HTTPPasswordMgr()
        _, netloc, _, _, _, _ = urlparse(self.url)
        pm.add_password(self.realm, netloc, self.username, self.password)
        self.password_handler = HTTPBasicAuthHandler(pm)

    def register(self, metadata):  # pragma: no cover
        """
        Register a distribution on PyPI, using the provided metadata.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the distribution to be
                         registered.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        metadata.validate()
        d = metadata.todict()
        d[':action'] = 'verify'
        request = self.encode_request(d.items(), [])
        self.send_request(request)
        d[':action'] = 'submit'
        request = self.encode_request(d.items(), [])
        return self.send_request(request)

    def _reader(self, name, stream, outbuf):
        """
        Thread runner for reading lines of from a subprocess into a buffer.

        :param name: The logical name of the stream (used for logging only).
        :param stream: The stream to read from. This will typically a pipe
                       connected to the output stream of a subprocess.
        :param outbuf: The list to append the read lines to.
        """
        while True:
            s = stream.readline()
            if not s:
                break
            s = s.decode('utf-8').rstrip()
            outbuf.append(s)
            logger.debug('%s: %s' % (name, s))
        stream.close()

    def get_sign_command(self, filename, signer, sign_password, keystore=None):  # pragma: no cover
        """
        Return a suitable command for signing a file.

        :param filename: The pathname to the file to be signed.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: The signing command as a list suitable to be
                 passed to :class:`subprocess.Popen`.
        """
        cmd = [self.gpg, '--status-fd', '2', '--no-tty']
        if keystore is None:
            keystore = self.gpg_home
        if keystore:
            cmd.extend(['--homedir', keystore])
        if sign_password is not None:
            cmd.extend(['--batch', '--passphrase-fd', '0'])
        td = tempfile.mkdtemp()
        sf = os.path.join(td, os.path.basename(filename) + '.asc')
        cmd.extend(['--detach-sign', '--armor', '--local-user',
                    signer, '--output', sf, filename])
        logger.debug('invoking: %s', ' '.join(cmd))
        return cmd, sf

    def run_command(self, cmd, input_data=None):
        """
        Run a command in a child process , passing it any input data specified.

        :param cmd: The command to run.
        :param input_data: If specified, this must be a byte string containing
                           data to be sent to the child process.
        :return: A tuple consisting of the subprocess' exit code, a list of
                 lines read from the subprocess' ``stdout``, and a list of
                 lines read from the subprocess' ``stderr``.
        """
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }
        if input_data is not None:
            kwargs['stdin'] = subprocess.PIPE
        stdout = []
        stderr = []
        p = subprocess.Popen(cmd, **kwargs)
        # We don't use communicate() here because we may need to
        # get clever with interacting with the command
        t1 = Thread(target=self._reader, args=('stdout', p.stdout, stdout))
        t1.start()
        t2 = Thread(target=self._reader, args=('stderr', p.stderr, stderr))
        t2.start()
        if input_data is not None:
            p.stdin.write(input_data)
            p.stdin.close()

        p.wait()
        t1.join()
        t2.join()
        return p.returncode, stdout, stderr

    def sign_file(self, filename, signer, sign_password, keystore=None):  # pragma: no cover
        """
        Sign a file.

        :param filename: The pathname to the file to be signed.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param keystore: The path to a directory which contains the keys
                         used in signing. If not specified, the instance's
                         ``gpg_home`` attribute is used instead.
        :return: The absolute pathname of the file where the signature is
                 stored.
        """
        cmd, sig_file = self.get_sign_command(filename, signer, sign_password,
                                              keystore)
        rc, stdout, stderr = self.run_command(cmd,
                                              sign_password.encode('utf-8'))
        if rc != 0:
            raise DistlibException('sign command failed with error '
                                   'code %s' % rc)
        return sig_file

    def upload_file(self, metadata, filename, signer=None, sign_password=None,
                    filetype='sdist', pyversion='source', keystore=None):
        """
        Upload a release file to the index.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the file to be uploaded.
        :param filename: The pathname of the file to be uploaded.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param filetype: The type of the file being uploaded. This is the
                        distutils command which produced that file, e.g.
                        ``sdist`` or ``bdist_wheel``.
        :param pyversion: The version of Python which the release relates
                          to. For code compatible with any Python, this would
                          be ``source``, otherwise it would be e.g. ``3.2``.
        :param keystore: The path to a directory which contains the keys
                         used in signing. If not specified, the instance's
                         ``gpg_home`` attribute is used instead.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        if not os.path.exists(filename):
            raise DistlibException('not found: %s' % filename)
        metadata.validate()
        d = metadata.todict()
        sig_file = None
        if signer:
            if not self.gpg:
                logger.warning('no signing program available - not signed')
            else:
                sig_file = self.sign_file(filename, signer, sign_password,
                                          keystore)
        with open(filename, 'rb') as f:
            file_data = f.read()
        md5_digest = hashlib.md5(file_data).hexdigest()
        sha256_digest = hashlib.sha256(file_data).hexdigest()
        d.update({
            ':action': 'file_upload',
            'protocol_version': '1',
            'filetype': filetype,
            'pyversion': pyversion,
            'md5_digest': md5_digest,
            'sha256_digest': sha256_digest,
        })
        files = [('content', os.path.basename(filename), file_data)]
        if sig_file:
            with open(sig_file, 'rb') as f:
                sig_data = f.read()
            files.append(('gpg_signature', os.path.basename(sig_file),
                         sig_data))
            shutil.rmtree(os.path.dirname(sig_file))
        request = self.encode_request(d.items(), files)
        return self.send_request(request)

    def upload_documentation(self, metadata, doc_dir):  # pragma: no cover
        """
        Upload documentation to the index.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the documentation to be
                         uploaded.
        :param doc_dir: The pathname of the directory which contains the
                        documentation. This should be the directory that
                        contains the ``index.html`` for the documentation.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        if not os.path.isdir(doc_dir):
            raise DistlibException('not a directory: %r' % doc_dir)
        fn = os.path.join(doc_dir, 'index.html')
        if not os.path.exists(fn):
            raise DistlibException('not found: %r' % fn)
        metadata.validate()
        name, version = metadata.name, metadata.version
        zip_data = zip_dir(doc_dir).getvalue()
        fields = [(':action', 'doc_upload'),
                  ('name', name), ('version', version)]
        files = [('content', name, zip_data)]
        request = self.encode_request(fields, files)
        return self.send_request(request)

    def get_verify_command(self, signature_filename, data_filename,
                           keystore=None):
        """
        Return a suitable command for verifying a file.

        :param signature_filename: The pathname to the file containing the
                                   signature.
        :param data_filename: The pathname to the file containing the
                              signed data.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: The verifying command as a list suitable to be
                 passed to :class:`subprocess.Popen`.
        """
        cmd = [self.gpg, '--status-fd', '2', '--no-tty']
        if keystore is None:
            keystore = self.gpg_home
        if keystore:
            cmd.extend(['--homedir', keystore])
        cmd.extend(['--verify', signature_filename, data_filename])
        logger.debug('invoking: %s', ' '.join(cmd))
        return cmd

    def verify_signature(self, signature_filename, data_filename,
                         keystore=None):
        """
        Verify a signature for a file.

        :param signature_filename: The pathname to the file containing the
                                   signature.
        :param data_filename: The pathname to the file containing the
                              signed data.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: True if the signature was verified, else False.
        """
        if not self.gpg:
            raise DistlibException('verification unavailable because gpg '
                                   'unavailable')
        cmd = self.get_verify_command(signature_filename, data_filename,
                                      keystore)
        rc, stdout, stderr = self.run_command(cmd)
        if rc not in (0, 1):
            raise DistlibException('verify command failed with error code %s' % rc)
        return rc == 0

    def download_file(self, url, destfile, digest=None, reporthook=None):
        """
        This is a convenience method for downloading a file from an URL.
        Normally, this will be a file from the index, though currently
        no check is made for this (i.e. a file can be downloaded from
        anywhere).

        The method is just like the :func:`urlretrieve` function in the
        standard library, except that it allows digest computation to be
        done during download and checking that the downloaded data
        matched any expected value.

        :param url: The URL of the file to be downloaded (assumed to be
                    available via an HTTP GET request).
        :param destfile: The pathname where the downloaded file is to be
                         saved.
        :param digest: If specified, this must be a (hasher, value)
                       tuple, where hasher is the algorithm used (e.g.
                       ``'md5'``) and ``value`` is the expected value.
        :param reporthook: The same as for :func:`urlretrieve` in the
                           standard library.
        """
        if digest is None:
            digester = None
            logger.debug('No digest specified')
        else:
            if isinstance(digest, (list, tuple)):
                hasher, digest = digest
            else:
                hasher = 'md5'
            digester = getattr(hashlib, hasher)()
            logger.debug('Digest specified: %s' % digest)
        # The following code is equivalent to urlretrieve.
        # We need to do it this way so that we can compute the
        # digest of the file as we go.
        with open(destfile, 'wb') as dfp:
            # addinfourl is not a context manager on 2.x
            # so we have to use try/finally
            sfp = self.send_request(Request(url))
            try:
                headers = sfp.info()
                blocksize = 8192
                size = -1
                read = 0
                blocknum = 0
                if "content-length" in headers:
                    size = int(headers["Content-Length"])
                if reporthook:
                    reporthook(blocknum, blocksize, size)
                while True:
                    block = sfp.read(blocksize)
                    if not block:
                        break
                    read += len(block)
                    dfp.write(block)
                    if digester:
                        digester.update(block)
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, blocksize, size)
            finally:
                sfp.close()

        # check that we got the whole file, if we can
        if size >= 0 and read < size:
            raise DistlibException(
                'retrieval incomplete: got only %d out of %d bytes'
                % (read, size))
        # if we have a digest, it must match.
        if digester:
            actual = digester.hexdigest()
            if digest != actual:
                raise DistlibException('%s digest mismatch for %s: expected '
                                       '%s, got %s' % (hasher, destfile,
                                                       digest, actual))
            logger.debug('Digest verified: %s', digest)

    def send_request(self, req):
        """
        Send a standard library :class:`Request` to PyPI and return its
        response.

        :param req: The request to send.
        :return: The HTTP response from PyPI (a standard library HTTPResponse).
        """
        handlers = []
        if self.password_handler:
            handlers.append(self.password_handler)
        if self.ssl_verifier:
            handlers.append(self.ssl_verifier)
        opener = build_opener(*handlers)
        return opener.open(req)

    def encode_request(self, fields, files):
        """
        Encode fields and files for posting to an HTTP server.

        :param fields: The fields to send as a list of (fieldname, value)
                       tuples.
        :param files: The files to send as a list of (fieldname, filename,
                      file_bytes) tuple.
        """
        # Adapted from packaging, which in turn was adapted from
        # http://code.activestate.com/recipes/146306

        parts = []
        boundary = self.boundary
        for k, values in fields:
            if not isinstance(values, (list, tuple)):
                values = [values]

            for v in values:
                parts.extend((
                    b'--' + boundary,
                    ('Content-Disposition: form-data; name="%s"' %
                     k).encode('utf-8'),
                    b'',
                    v.encode('utf-8')))
        for key, filename, value in files:
            parts.extend((
                b'--' + boundary,
                ('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename)).encode('utf-8'),
                b'',
                value))

        parts.extend((b'--' + boundary + b'--', b''))

        body = b'\r\n'.join(parts)
        ct = b'multipart/form-data; boundary=' + boundary
        headers = {
            'Content-type': ct,
            'Content-length': str(len(body))
        }
        return Request(self.url, body, headers)

    def search(self, terms, operator=None):  # pragma: no cover
        if isinstance(terms, string_types):
            terms = {'name': terms}
        rpc_proxy = ServerProxy(self.url, timeout=3.0)
        try:
            return rpc_proxy.search(terms, operator or 'and')
        finally:
            rpc_proxy('close')()

# === NexusCore/openenv\Lib\site-packages\google\oauth2\_client.py ===
# Copyright 2016 Google LLC
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

"""OAuth 2.0 client.

This is a client for interacting with an OAuth 2.0 authorization server's
token endpoint.

For more information about the token endpoint, see
`Section 3.1 of rfc6749`_

.. _Section 3.1 of rfc6749: https://tools.ietf.org/html/rfc6749#section-3.2
"""

import datetime
import http.client as http_client
import json
import urllib

from google.auth import _exponential_backoff
from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.auth import jwt
from google.auth import metrics
from google.auth import transport

_URLENCODED_CONTENT_TYPE = "application/x-www-form-urlencoded"
_JSON_CONTENT_TYPE = "application/json"
_JWT_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_REFRESH_GRANT_TYPE = "refresh_token"


def _handle_error_response(response_data, retryable_error):
    """Translates an error response into an exception.

    Args:
        response_data (Mapping | str): The decoded response data.
        retryable_error Optional[bool]: A boolean indicating if an error is retryable.
            Defaults to False.

    Raises:
        google.auth.exceptions.RefreshError: The errors contained in response_data.
    """

    retryable_error = retryable_error if retryable_error else False

    if isinstance(response_data, str):
        raise exceptions.RefreshError(response_data, retryable=retryable_error)
    try:
        error_details = "{}: {}".format(
            response_data["error"], response_data.get("error_description")
        )
    # If no details could be extracted, use the response data.
    except (KeyError, ValueError):
        error_details = json.dumps(response_data)

    raise exceptions.RefreshError(
        error_details, response_data, retryable=retryable_error
    )


def _can_retry(status_code, response_data):
    """Checks if a request can be retried by inspecting the status code
    and response body of the request.

    Args:
        status_code (int): The response status code.
        response_data (Mapping | str): The decoded response data.

    Returns:
      bool: True if the response is retryable. False otherwise.
    """
    if status_code in transport.DEFAULT_RETRYABLE_STATUS_CODES:
        return True

    try:
        # For a failed response, response_body could be a string
        error_desc = response_data.get("error_description") or ""
        error_code = response_data.get("error") or ""

        if not isinstance(error_code, str) or not isinstance(error_desc, str):
            return False

        # Per Oauth 2.0 RFC https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2.1
        # This is needed because a redirect will not return a 500 status code.
        retryable_error_descriptions = {
            "internal_failure",
            "server_error",
            "temporarily_unavailable",
        }

        if any(e in retryable_error_descriptions for e in (error_code, error_desc)):
            return True

    except AttributeError:
        pass

    return False


def _parse_expiry(response_data):
    """Parses the expiry field from a response into a datetime.

    Args:
        response_data (Mapping): The JSON-parsed response data.

    Returns:
        Optional[datetime]: The expiration or ``None`` if no expiration was
            specified.
    """
    expires_in = response_data.get("expires_in", None)

    if expires_in is not None:
        # Some services do not respect the OAUTH2.0 RFC and send expires_in as a
        # JSON String.
        if isinstance(expires_in, str):
            expires_in = int(expires_in)

        return _helpers.utcnow() + datetime.timedelta(seconds=expires_in)
    else:
        return None


def _token_endpoint_request_no_throw(
    request,
    token_uri,
    body,
    access_token=None,
    use_json=False,
    can_retry=True,
    headers=None,
    **kwargs
):
    """Makes a request to the OAuth 2.0 authorization server's token endpoint.
    This function doesn't throw on response errors.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        body (Mapping[str, str]): The parameters to send in the request body.
        access_token (Optional(str)): The access token needed to make the request.
        use_json (Optional(bool)): Use urlencoded format or json format for the
            content type. The default value is False.
        can_retry (bool): Enable or disable request retry behavior.
        headers (Optional[Mapping[str, str]]): The headers for the request.
        kwargs: Additional arguments passed on to the request method. The
            kwargs will be passed to `requests.request` method, see:
            https://docs.python-requests.org/en/latest/api/#requests.request.
            For example, you can use `cert=("cert_pem_path", "key_pem_path")`
            to set up client side SSL certificate, and use
            `verify="ca_bundle_path"` to set up the CA certificates for sever
            side SSL certificate verification.

    Returns:
        Tuple(bool, Mapping[str, str], Optional[bool]): A boolean indicating
          if the request is successful, a mapping for the JSON-decoded response
          data and in the case of an error a boolean indicating if the error
          is retryable.
    """
    if use_json:
        headers_to_use = {"Content-Type": _JSON_CONTENT_TYPE}
        body = json.dumps(body).encode("utf-8")
    else:
        headers_to_use = {"Content-Type": _URLENCODED_CONTENT_TYPE}
        body = urllib.parse.urlencode(body).encode("utf-8")

    if access_token:
        headers_to_use["Authorization"] = "Bearer {}".format(access_token)

    if headers:
        headers_to_use.update(headers)

    response_data = {}
    retryable_error = False

    retries = _exponential_backoff.ExponentialBackoff()
    for _ in retries:
        response = request(
            method="POST", url=token_uri, headers=headers_to_use, body=body, **kwargs
        )
        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        try:
            # response_body should be a JSON
            response_data = json.loads(response_body)
        except ValueError:
            response_data = response_body

        if response.status == http_client.OK:
            return True, response_data, None

        retryable_error = _can_retry(
            status_code=response.status, response_data=response_data
        )

        if not can_retry or not retryable_error:
            return False, response_data, retryable_error

    return False, response_data, retryable_error


def _token_endpoint_request(
    request,
    token_uri,
    body,
    access_token=None,
    use_json=False,
    can_retry=True,
    headers=None,
    **kwargs
):
    """Makes a request to the OAuth 2.0 authorization server's token endpoint.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        body (Mapping[str, str]): The parameters to send in the request body.
        access_token (Optional(str)): The access token needed to make the request.
        use_json (Optional(bool)): Use urlencoded format or json format for the
            content type. The default value is False.
        can_retry (bool): Enable or disable request retry behavior.
        headers (Optional[Mapping[str, str]]): The headers for the request.
        kwargs: Additional arguments passed on to the request method. The
            kwargs will be passed to `requests.request` method, see:
            https://docs.python-requests.org/en/latest/api/#requests.request.
            For example, you can use `cert=("cert_pem_path", "key_pem_path")`
            to set up client side SSL certificate, and use
            `verify="ca_bundle_path"` to set up the CA certificates for sever
            side SSL certificate verification.

    Returns:
        Mapping[str, str]: The JSON-decoded response data.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """

    response_status_ok, response_data, retryable_error = _token_endpoint_request_no_throw(
        request,
        token_uri,
        body,
        access_token=access_token,
        use_json=use_json,
        can_retry=can_retry,
        headers=headers,
        **kwargs
    )
    if not response_status_ok:
        _handle_error_response(response_data, retryable_error)
    return response_data


def jwt_grant(request, token_uri, assertion, can_retry=True):
    """Implements the JWT Profile for OAuth 2.0 Authorization Grants.

    For more details, see `rfc7523 section 4`_.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        assertion (str): The OAuth 2.0 assertion.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, Optional[datetime], Mapping[str, str]]: The access token,
            expiration, and additional data returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc7523 section 4: https://tools.ietf.org/html/rfc7523#section-4
    """
    body = {"assertion": assertion, "grant_type": _JWT_GRANT_TYPE}

    response_data = _token_endpoint_request(
        request,
        token_uri,
        body,
        can_retry=can_retry,
        headers={
            metrics.API_CLIENT_HEADER: metrics.token_request_access_token_sa_assertion()
        },
    )

    try:
        access_token = response_data["access_token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No access token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    expiry = _parse_expiry(response_data)

    return access_token, expiry, response_data


def call_iam_generate_id_token_endpoint(
    request,
    iam_id_token_endpoint,
    signer_email,
    audience,
    access_token,
    universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
):
    """Call iam.generateIdToken endpoint to get ID token.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        iam_id_token_endpoint (str): The IAM ID token endpoint to use.
        signer_email (str): The signer email used to form the IAM
            generateIdToken endpoint.
        audience (str): The audience for the ID token.
        access_token (str): The access token used to call the IAM endpoint.

    Returns:
        Tuple[str, datetime]: The ID token and expiration.
    """
    body = {"audience": audience, "includeEmail": "true", "useEmailAzp": "true"}

    response_data = _token_endpoint_request(
        request,
        iam_id_token_endpoint.replace(
            credentials.DEFAULT_UNIVERSE_DOMAIN, universe_domain
        ).format(signer_email),
        body,
        access_token=access_token,
        use_json=True,
    )

    try:
        id_token = response_data["token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No ID token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    payload = jwt.decode(id_token, verify=False)
    expiry = datetime.datetime.utcfromtimestamp(payload["exp"])

    return id_token, expiry


def id_token_jwt_grant(request, token_uri, assertion, can_retry=True):
    """Implements the JWT Profile for OAuth 2.0 Authorization Grants, but
    requests an OpenID Connect ID Token instead of an access token.

    This is a variant on the standard JWT Profile that is currently unique
    to Google. This was added for the benefit of authenticating to services
    that require ID Tokens instead of access tokens or JWT bearer tokens.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorization server's token endpoint
            URI.
        assertion (str): JWT token signed by a service account. The token's
            payload must include a ``target_audience`` claim.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, Optional[datetime], Mapping[str, str]]:
            The (encoded) Open ID Connect ID Token, expiration, and additional
            data returned by the endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    body = {"assertion": assertion, "grant_type": _JWT_GRANT_TYPE}

    response_data = _token_endpoint_request(
        request,
        token_uri,
        body,
        can_retry=can_retry,
        headers={
            metrics.API_CLIENT_HEADER: metrics.token_request_id_token_sa_assertion()
        },
    )

    try:
        id_token = response_data["id_token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No ID token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    payload = jwt.decode(id_token, verify=False)
    expiry = datetime.datetime.utcfromtimestamp(payload["exp"])

    return id_token, expiry, response_data


def _handle_refresh_grant_response(response_data, refresh_token):
    """Extract tokens from refresh grant response.

    Args:
        response_data (Mapping[str, str]): Refresh grant response data.
        refresh_token (str): Current refresh token.

    Returns:
        Tuple[str, str, Optional[datetime], Mapping[str, str]]: The access token,
            refresh token, expiration, and additional data returned by the token
            endpoint. If response_data doesn't have refresh token, then the current
            refresh token will be returned.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    try:
        access_token = response_data["access_token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No access token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    refresh_token = response_data.get("refresh_token", refresh_token)
    expiry = _parse_expiry(response_data)

    return access_token, refresh_token, expiry, response_data


def refresh_grant(
    request,
    token_uri,
    refresh_token,
    client_id,
    client_secret,
    scopes=None,
    rapt_token=None,
    can_retry=True,
):
    """Implements the OAuth 2.0 refresh token grant.

    For more details, see `rfc678 section 6`_.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        refresh_token (str): The refresh token to use to get a new access
            token.
        client_id (str): The OAuth 2.0 application's client ID.
        client_secret (str): The Oauth 2.0 appliaction's client secret.
        scopes (Optional(Sequence[str])): Scopes to request. If present, all
            scopes must be authorized for the refresh token. Useful if refresh
            token has a wild card scope (e.g.
            'https://www.googleapis.com/auth/any-api').
        rapt_token (Optional(str)): The reauth Proof Token.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, str, Optional[datetime], Mapping[str, str]]: The access
            token, new or current refresh token, expiration, and additional data
            returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc6748 section 6: https://tools.ietf.org/html/rfc6749#section-6
    """
    body = {
        "grant_type": _REFRESH_GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    if scopes:
        body["scope"] = " ".join(scopes)
    if rapt_token:
        body["rapt"] = rapt_token

    response_data = _token_endpoint_request(
        request, token_uri, body, can_retry=can_retry
    )
    return _handle_refresh_grant_response(response_data, refresh_token)

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\distance.py ===
# Natural Language Toolkit: Distance Metrics
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Tom Lippincott <tom@cs.columbia.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Distance Metrics.

Compute the distance between two items (usually strings).
As metrics, they must satisfy the following three requirements:

1. d(a, a) = 0
2. d(a, b) >= 0
3. d(a, c) <= d(a, b) + d(b, c)
"""

import operator
import warnings


def _edit_dist_init(len1, len2):
    lev = []
    for i in range(len1):
        lev.append([0] * len2)  # initialize 2D array to zero
    for i in range(len1):
        lev[i][0] = i  # column 0: 0,1,2,3,4,...
    for j in range(len2):
        lev[0][j] = j  # row 0: 0,1,2,3,4,...
    return lev


def _last_left_t_init(sigma):
    return {c: 0 for c in sigma}


def _edit_dist_step(
    lev, i, j, s1, s2, last_left, last_right, substitution_cost=1, transpositions=False
):
    c1 = s1[i - 1]
    c2 = s2[j - 1]

    # skipping a character in s1
    a = lev[i - 1][j] + 1
    # skipping a character in s2
    b = lev[i][j - 1] + 1
    # substitution
    c = lev[i - 1][j - 1] + (substitution_cost if c1 != c2 else 0)

    # transposition
    d = c + 1  # never picked by default
    if transpositions and last_left > 0 and last_right > 0:
        d = lev[last_left - 1][last_right - 1] + i - last_left + j - last_right - 1

    # pick the cheapest
    lev[i][j] = min(a, b, c, d)


def edit_distance(s1, s2, substitution_cost=1, transpositions=False):
    """
    Calculate the Levenshtein edit-distance between two strings.
    The edit distance is the number of characters that need to be
    substituted, inserted, or deleted, to transform s1 into s2.  For
    example, transforming "rain" to "shine" requires three steps,
    consisting of two substitutions and one insertion:
    "rain" -> "sain" -> "shin" -> "shine".  These operations could have
    been done in other orders, but at least three steps are needed.

    Allows specifying the cost of substitution edits (e.g., "a" -> "b"),
    because sometimes it makes sense to assign greater penalties to
    substitutions.

    This also optionally allows transposition edits (e.g., "ab" -> "ba"),
    though this is disabled by default.

    :param s1, s2: The strings to be analysed
    :param transpositions: Whether to allow transposition edits
    :type s1: str
    :type s2: str
    :type substitution_cost: int
    :type transpositions: bool
    :rtype: int
    """
    # set up a 2-D array
    len1 = len(s1)
    len2 = len(s2)
    lev = _edit_dist_init(len1 + 1, len2 + 1)

    # retrieve alphabet
    sigma = set()
    sigma.update(s1)
    sigma.update(s2)

    # set up table to remember positions of last seen occurrence in s1
    last_left_t = _last_left_t_init(sigma)

    # iterate over the array
    # i and j start from 1 and not 0 to stay close to the wikipedia pseudo-code
    # see https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance
    for i in range(1, len1 + 1):
        last_right_buf = 0
        for j in range(1, len2 + 1):
            last_left = last_left_t[s2[j - 1]]
            last_right = last_right_buf
            if s1[i - 1] == s2[j - 1]:
                last_right_buf = j
            _edit_dist_step(
                lev,
                i,
                j,
                s1,
                s2,
                last_left,
                last_right,
                substitution_cost=substitution_cost,
                transpositions=transpositions,
            )
        last_left_t[s1[i - 1]] = i
    return lev[len1][len2]


def _edit_dist_backtrace(lev):
    i, j = len(lev) - 1, len(lev[0]) - 1
    alignment = [(i, j)]

    while (i, j) != (0, 0):
        directions = [
            (i - 1, j - 1),  # substitution
            (i - 1, j),  # skip s1
            (i, j - 1),  # skip s2
        ]

        direction_costs = (
            (lev[i][j] if (i >= 0 and j >= 0) else float("inf"), (i, j))
            for i, j in directions
        )
        _, (i, j) = min(direction_costs, key=operator.itemgetter(0))

        alignment.append((i, j))
    return list(reversed(alignment))


def edit_distance_align(s1, s2, substitution_cost=1):
    """
    Calculate the minimum Levenshtein edit-distance based alignment
    mapping between two strings. The alignment finds the mapping
    from string s1 to s2 that minimizes the edit distance cost.
    For example, mapping "rain" to "shine" would involve 2
    substitutions, 2 matches and an insertion resulting in
    the following mapping:
    [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (4, 5)]
    NB: (0, 0) is the start state without any letters associated
    See more: https://web.stanford.edu/class/cs124/lec/med.pdf

    In case of multiple valid minimum-distance alignments, the
    backtrace has the following operation precedence:

    1. Substitute s1 and s2 characters
    2. Skip s1 character
    3. Skip s2 character

    The backtrace is carried out in reverse string order.

    This function does not support transposition.

    :param s1, s2: The strings to be aligned
    :type s1: str
    :type s2: str
    :type substitution_cost: int
    :rtype: List[Tuple(int, int)]
    """
    # set up a 2-D array
    len1 = len(s1)
    len2 = len(s2)
    lev = _edit_dist_init(len1 + 1, len2 + 1)

    # iterate over the array
    for i in range(len1):
        for j in range(len2):
            _edit_dist_step(
                lev,
                i + 1,
                j + 1,
                s1,
                s2,
                0,
                0,
                substitution_cost=substitution_cost,
                transpositions=False,
            )

    # backtrace to find alignment
    alignment = _edit_dist_backtrace(lev)
    return alignment


def binary_distance(label1, label2):
    """Simple equality test.

    0.0 if the labels are identical, 1.0 if they are different.

    >>> from nltk.metrics import binary_distance
    >>> binary_distance(1,1)
    0.0

    >>> binary_distance(1,3)
    1.0
    """

    return 0.0 if label1 == label2 else 1.0


def jaccard_distance(label1, label2):
    """Distance metric comparing set-similarity."""
    return (len(label1.union(label2)) - len(label1.intersection(label2))) / len(
        label1.union(label2)
    )


def masi_distance(label1, label2):
    """Distance metric that takes into account partial agreement when multiple
    labels are assigned.

    >>> from nltk.metrics import masi_distance
    >>> masi_distance(set([1, 2]), set([1, 2, 3, 4]))
    0.665

    Passonneau 2006, Measuring Agreement on Set-Valued Items (MASI)
    for Semantic and Pragmatic Annotation.
    """

    len_intersection = len(label1.intersection(label2))
    len_union = len(label1.union(label2))
    len_label1 = len(label1)
    len_label2 = len(label2)
    if len_label1 == len_label2 and len_label1 == len_intersection:
        m = 1
    elif len_intersection == min(len_label1, len_label2):
        m = 0.67
    elif len_intersection > 0:
        m = 0.33
    else:
        m = 0

    return 1 - len_intersection / len_union * m


def interval_distance(label1, label2):
    """Krippendorff's interval distance metric

    >>> from nltk.metrics import interval_distance
    >>> interval_distance(1,10)
    81

    Krippendorff 1980, Content Analysis: An Introduction to its Methodology
    """

    try:
        return pow(label1 - label2, 2)
    #        return pow(list(label1)[0]-list(label2)[0],2)
    except:
        print("non-numeric labels not supported with interval distance")


def presence(label):
    """Higher-order function to test presence of a given label"""

    return lambda x, y: 1.0 * ((label in x) == (label in y))


def fractional_presence(label):
    return (
        lambda x, y: abs((1.0 / len(x)) - (1.0 / len(y))) * (label in x and label in y)
        or 0.0 * (label not in x and label not in y)
        or abs(1.0 / len(x)) * (label in x and label not in y)
        or (1.0 / len(y)) * (label not in x and label in y)
    )


def custom_distance(file):
    data = {}
    with open(file) as infile:
        for l in infile:
            labelA, labelB, dist = l.strip().split("\t")
            labelA = frozenset([labelA])
            labelB = frozenset([labelB])
            data[frozenset([labelA, labelB])] = float(dist)
    return lambda x, y: data[frozenset([x, y])]


def jaro_similarity(s1, s2):
    """
    Computes the Jaro similarity between 2 sequences from:

        Matthew A. Jaro (1989). Advances in record linkage methodology
        as applied to the 1985 census of Tampa Florida. Journal of the
        American Statistical Association. 84 (406): 414-20.

    The Jaro distance between is the min no. of single-character transpositions
    required to change one word into another. The Jaro similarity formula from
    https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance :

        ``jaro_sim = 0 if m = 0 else 1/3 * (m/|s_1| + m/s_2 + (m-t)/m)``

    where
        - `|s_i|` is the length of string `s_i`
        - `m` is the no. of matching characters
        - `t` is the half no. of possible transpositions.
    """
    # First, store the length of the strings
    # because they will be re-used several times.
    len_s1, len_s2 = len(s1), len(s2)

    # The upper bound of the distance for being a matched character.
    match_bound = max(len_s1, len_s2) // 2 - 1

    # Initialize the counts for matches and transpositions.
    matches = 0  # no.of matched characters in s1 and s2
    transpositions = 0  # no. of transpositions between s1 and s2
    flagged_1 = []  # positions in s1 which are matches to some character in s2
    flagged_2 = []  # positions in s2 which are matches to some character in s1

    # Iterate through sequences, check for matches and compute transpositions.
    for i in range(len_s1):  # Iterate through each character.
        upperbound = min(i + match_bound, len_s2 - 1)
        lowerbound = max(0, i - match_bound)
        for j in range(lowerbound, upperbound + 1):
            if s1[i] == s2[j] and j not in flagged_2:
                matches += 1
                flagged_1.append(i)
                flagged_2.append(j)
                break
    flagged_2.sort()
    for i, j in zip(flagged_1, flagged_2):
        if s1[i] != s2[j]:
            transpositions += 1

    if matches == 0:
        return 0
    else:
        return (
            1
            / 3
            * (
                matches / len_s1
                + matches / len_s2
                + (matches - transpositions // 2) / matches
            )
        )


def jaro_winkler_similarity(s1, s2, p=0.1, max_l=4):
    """
    The Jaro Winkler distance is an extension of the Jaro similarity in:

        William E. Winkler. 1990. String Comparator Metrics and Enhanced
        Decision Rules in the Fellegi-Sunter Model of Record Linkage.
        Proceedings of the Section on Survey Research Methods.
        American Statistical Association: 354-359.

    such that:

        jaro_winkler_sim = jaro_sim + ( l * p * (1 - jaro_sim) )

    where,

    - jaro_sim is the output from the Jaro Similarity,
        see jaro_similarity()
    - l is the length of common prefix at the start of the string
        - this implementation provides an upperbound for the l value
            to keep the prefixes.A common value of this upperbound is 4.
    - p is the constant scaling factor to overweigh common prefixes.
        The Jaro-Winkler similarity will fall within the [0, 1] bound,
        given that max(p)<=0.25 , default is p=0.1 in Winkler (1990)


    Test using outputs from https://www.census.gov/srd/papers/pdf/rr93-8.pdf
    from "Table 5 Comparison of String Comparators Rescaled between 0 and 1"

    >>> winkler_examples = [("billy", "billy"), ("billy", "bill"), ("billy", "blily"),
    ... ("massie", "massey"), ("yvette", "yevett"), ("billy", "bolly"), ("dwayne", "duane"),
    ... ("dixon", "dickson"), ("billy", "susan")]

    >>> winkler_scores = [1.000, 0.967, 0.947, 0.944, 0.911, 0.893, 0.858, 0.853, 0.000]
    >>> jaro_scores =    [1.000, 0.933, 0.933, 0.889, 0.889, 0.867, 0.822, 0.790, 0.000]

    One way to match the values on the Winkler's paper is to provide a different
    p scaling factor for different pairs of strings, e.g.

    >>> p_factors = [0.1, 0.125, 0.20, 0.125, 0.20, 0.20, 0.20, 0.15, 0.1]

    >>> for (s1, s2), jscore, wscore, p in zip(winkler_examples, jaro_scores, winkler_scores, p_factors):
    ...     assert round(jaro_similarity(s1, s2), 3) == jscore
    ...     assert round(jaro_winkler_similarity(s1, s2, p=p), 3) == wscore


    Test using outputs from https://www.census.gov/srd/papers/pdf/rr94-5.pdf from
    "Table 2.1. Comparison of String Comparators Using Last Names, First Names, and Street Names"

    >>> winkler_examples = [('SHACKLEFORD', 'SHACKELFORD'), ('DUNNINGHAM', 'CUNNIGHAM'),
    ... ('NICHLESON', 'NICHULSON'), ('JONES', 'JOHNSON'), ('MASSEY', 'MASSIE'),
    ... ('ABROMS', 'ABRAMS'), ('HARDIN', 'MARTINEZ'), ('ITMAN', 'SMITH'),
    ... ('JERALDINE', 'GERALDINE'), ('MARHTA', 'MARTHA'), ('MICHELLE', 'MICHAEL'),
    ... ('JULIES', 'JULIUS'), ('TANYA', 'TONYA'), ('DWAYNE', 'DUANE'), ('SEAN', 'SUSAN'),
    ... ('JON', 'JOHN'), ('JON', 'JAN'), ('BROOKHAVEN', 'BRROKHAVEN'),
    ... ('BROOK HALLOW', 'BROOK HLLW'), ('DECATUR', 'DECATIR'), ('FITZRUREITER', 'FITZENREITER'),
    ... ('HIGBEE', 'HIGHEE'), ('HIGBEE', 'HIGVEE'), ('LACURA', 'LOCURA'), ('IOWA', 'IONA'), ('1ST', 'IST')]

    >>> jaro_scores =   [0.970, 0.896, 0.926, 0.790, 0.889, 0.889, 0.722, 0.467, 0.926,
    ... 0.944, 0.869, 0.889, 0.867, 0.822, 0.783, 0.917, 0.000, 0.933, 0.944, 0.905,
    ... 0.856, 0.889, 0.889, 0.889, 0.833, 0.000]

    >>> winkler_scores = [0.982, 0.896, 0.956, 0.832, 0.944, 0.922, 0.722, 0.467, 0.926,
    ... 0.961, 0.921, 0.933, 0.880, 0.858, 0.805, 0.933, 0.000, 0.947, 0.967, 0.943,
    ... 0.913, 0.922, 0.922, 0.900, 0.867, 0.000]

    One way to match the values on the Winkler's paper is to provide a different
    p scaling factor for different pairs of strings, e.g.

    >>> p_factors = [0.1, 0.1, 0.1, 0.1, 0.125, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.20,
    ... 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]


    >>> for (s1, s2), jscore, wscore, p in zip(winkler_examples, jaro_scores, winkler_scores, p_factors):
    ...     if (s1, s2) in [('JON', 'JAN'), ('1ST', 'IST')]:
    ...         continue  # Skip bad examples from the paper.
    ...     assert round(jaro_similarity(s1, s2), 3) == jscore
    ...     assert round(jaro_winkler_similarity(s1, s2, p=p), 3) == wscore



    This test-case proves that the output of Jaro-Winkler similarity depends on
    the product  l * p and not on the product max_l * p. Here the product max_l * p > 1
    however the product l * p <= 1

    >>> round(jaro_winkler_similarity('TANYA', 'TONYA', p=0.1, max_l=100), 3)
    0.88
    """
    # To ensure that the output of the Jaro-Winkler's similarity
    # falls between [0,1], the product of l * p needs to be
    # also fall between [0,1].
    if not 0 <= max_l * p <= 1:
        warnings.warn(
            str(
                "The product  `max_l * p` might not fall between [0,1]."
                "Jaro-Winkler similarity might not be between 0 and 1."
            )
        )

    # Compute the Jaro similarity
    jaro_sim = jaro_similarity(s1, s2)

    # Initialize the upper bound for the no. of prefixes.
    # if user did not pre-define the upperbound,
    # use shorter length between s1 and s2

    # Compute the prefix matches.
    l = 0
    # zip() will automatically loop until the end of shorter string.
    for s1_i, s2_i in zip(s1, s2):
        if s1_i == s2_i:
            l += 1
        else:
            break
        if l == max_l:
            break
    # Return the similarity value as described in docstring.
    return jaro_sim + (l * p * (1 - jaro_sim))


def demo():
    string_distance_examples = [
        ("rain", "shine"),
        ("abcdef", "acbdef"),
        ("language", "lnaguaeg"),
        ("language", "lnaugage"),
        ("language", "lngauage"),
    ]
    for s1, s2 in string_distance_examples:
        print(f"Edit distance btwn '{s1}' and '{s2}':", edit_distance(s1, s2))
        print(
            f"Edit dist with transpositions btwn '{s1}' and '{s2}':",
            edit_distance(s1, s2, transpositions=True),
        )
        print(f"Jaro similarity btwn '{s1}' and '{s2}':", jaro_similarity(s1, s2))
        print(
            f"Jaro-Winkler similarity btwn '{s1}' and '{s2}':",
            jaro_winkler_similarity(s1, s2),
        )
        print(
            f"Jaro-Winkler distance btwn '{s1}' and '{s2}':",
            1 - jaro_winkler_similarity(s1, s2),
        )
    s1 = {1, 2, 3, 4}
    s2 = {3, 4, 5}
    print("s1:", s1)
    print("s2:", s2)
    print("Binary distance:", binary_distance(s1, s2))
    print("Jaccard distance:", jaccard_distance(s1, s2))
    print("MASI distance:", masi_distance(s1, s2))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\index.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
try:
    from threading import Thread
except ImportError:  # pragma: no cover
    from dummy_threading import Thread

from . import DistlibException
from .compat import (HTTPBasicAuthHandler, Request, HTTPPasswordMgr,
                     urlparse, build_opener, string_types)
from .util import zip_dir, ServerProxy

logger = logging.getLogger(__name__)

DEFAULT_INDEX = 'https://pypi.org/pypi'
DEFAULT_REALM = 'pypi'


class PackageIndex(object):
    """
    This class represents a package index compatible with PyPI, the Python
    Package Index.
    """

    boundary = b'----------ThIs_Is_tHe_distlib_index_bouNdaRY_$'

    def __init__(self, url=None):
        """
        Initialise an instance.

        :param url: The URL of the index. If not specified, the URL for PyPI is
                    used.
        """
        self.url = url or DEFAULT_INDEX
        self.read_configuration()
        scheme, netloc, path, params, query, frag = urlparse(self.url)
        if params or query or frag or scheme not in ('http', 'https'):
            raise DistlibException('invalid repository: %s' % self.url)
        self.password_handler = None
        self.ssl_verifier = None
        self.gpg = None
        self.gpg_home = None
        with open(os.devnull, 'w') as sink:
            # Use gpg by default rather than gpg2, as gpg2 insists on
            # prompting for passwords
            for s in ('gpg', 'gpg2'):
                try:
                    rc = subprocess.check_call([s, '--version'], stdout=sink,
                                               stderr=sink)
                    if rc == 0:
                        self.gpg = s
                        break
                except OSError:
                    pass

    def _get_pypirc_command(self):
        """
        Get the distutils command for interacting with PyPI configurations.
        :return: the command.
        """
        from .util import _get_pypirc_command as cmd
        return cmd()

    def read_configuration(self):
        """
        Read the PyPI access configuration as supported by distutils. This populates
        ``username``, ``password``, ``realm`` and ``url`` attributes from the
        configuration.
        """
        from .util import _load_pypirc
        cfg = _load_pypirc(self)
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.realm = cfg.get('realm', 'pypi')
        self.url = cfg.get('repository', self.url)

    def save_configuration(self):
        """
        Save the PyPI access configuration. You must have set ``username`` and
        ``password`` attributes before calling this method.
        """
        self.check_credentials()
        from .util import _store_pypirc
        _store_pypirc(self)

    def check_credentials(self):
        """
        Check that ``username`` and ``password`` have been set, and raise an
        exception if not.
        """
        if self.username is None or self.password is None:
            raise DistlibException('username and password must be set')
        pm = HTTPPasswordMgr()
        _, netloc, _, _, _, _ = urlparse(self.url)
        pm.add_password(self.realm, netloc, self.username, self.password)
        self.password_handler = HTTPBasicAuthHandler(pm)

    def register(self, metadata):  # pragma: no cover
        """
        Register a distribution on PyPI, using the provided metadata.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the distribution to be
                         registered.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        metadata.validate()
        d = metadata.todict()
        d[':action'] = 'verify'
        request = self.encode_request(d.items(), [])
        self.send_request(request)
        d[':action'] = 'submit'
        request = self.encode_request(d.items(), [])
        return self.send_request(request)

    def _reader(self, name, stream, outbuf):
        """
        Thread runner for reading lines of from a subprocess into a buffer.

        :param name: The logical name of the stream (used for logging only).
        :param stream: The stream to read from. This will typically a pipe
                       connected to the output stream of a subprocess.
        :param outbuf: The list to append the read lines to.
        """
        while True:
            s = stream.readline()
            if not s:
                break
            s = s.decode('utf-8').rstrip()
            outbuf.append(s)
            logger.debug('%s: %s' % (name, s))
        stream.close()

    def get_sign_command(self, filename, signer, sign_password, keystore=None):  # pragma: no cover
        """
        Return a suitable command for signing a file.

        :param filename: The pathname to the file to be signed.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: The signing command as a list suitable to be
                 passed to :class:`subprocess.Popen`.
        """
        cmd = [self.gpg, '--status-fd', '2', '--no-tty']
        if keystore is None:
            keystore = self.gpg_home
        if keystore:
            cmd.extend(['--homedir', keystore])
        if sign_password is not None:
            cmd.extend(['--batch', '--passphrase-fd', '0'])
        td = tempfile.mkdtemp()
        sf = os.path.join(td, os.path.basename(filename) + '.asc')
        cmd.extend(['--detach-sign', '--armor', '--local-user',
                    signer, '--output', sf, filename])
        logger.debug('invoking: %s', ' '.join(cmd))
        return cmd, sf

    def run_command(self, cmd, input_data=None):
        """
        Run a command in a child process , passing it any input data specified.

        :param cmd: The command to run.
        :param input_data: If specified, this must be a byte string containing
                           data to be sent to the child process.
        :return: A tuple consisting of the subprocess' exit code, a list of
                 lines read from the subprocess' ``stdout``, and a list of
                 lines read from the subprocess' ``stderr``.
        """
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }
        if input_data is not None:
            kwargs['stdin'] = subprocess.PIPE
        stdout = []
        stderr = []
        p = subprocess.Popen(cmd, **kwargs)
        # We don't use communicate() here because we may need to
        # get clever with interacting with the command
        t1 = Thread(target=self._reader, args=('stdout', p.stdout, stdout))
        t1.start()
        t2 = Thread(target=self._reader, args=('stderr', p.stderr, stderr))
        t2.start()
        if input_data is not None:
            p.stdin.write(input_data)
            p.stdin.close()

        p.wait()
        t1.join()
        t2.join()
        return p.returncode, stdout, stderr

    def sign_file(self, filename, signer, sign_password, keystore=None):  # pragma: no cover
        """
        Sign a file.

        :param filename: The pathname to the file to be signed.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param keystore: The path to a directory which contains the keys
                         used in signing. If not specified, the instance's
                         ``gpg_home`` attribute is used instead.
        :return: The absolute pathname of the file where the signature is
                 stored.
        """
        cmd, sig_file = self.get_sign_command(filename, signer, sign_password,
                                              keystore)
        rc, stdout, stderr = self.run_command(cmd,
                                              sign_password.encode('utf-8'))
        if rc != 0:
            raise DistlibException('sign command failed with error '
                                   'code %s' % rc)
        return sig_file

    def upload_file(self, metadata, filename, signer=None, sign_password=None,
                    filetype='sdist', pyversion='source', keystore=None):
        """
        Upload a release file to the index.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the file to be uploaded.
        :param filename: The pathname of the file to be uploaded.
        :param signer: The identifier of the signer of the file.
        :param sign_password: The passphrase for the signer's
                              private key used for signing.
        :param filetype: The type of the file being uploaded. This is the
                        distutils command which produced that file, e.g.
                        ``sdist`` or ``bdist_wheel``.
        :param pyversion: The version of Python which the release relates
                          to. For code compatible with any Python, this would
                          be ``source``, otherwise it would be e.g. ``3.2``.
        :param keystore: The path to a directory which contains the keys
                         used in signing. If not specified, the instance's
                         ``gpg_home`` attribute is used instead.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        if not os.path.exists(filename):
            raise DistlibException('not found: %s' % filename)
        metadata.validate()
        d = metadata.todict()
        sig_file = None
        if signer:
            if not self.gpg:
                logger.warning('no signing program available - not signed')
            else:
                sig_file = self.sign_file(filename, signer, sign_password,
                                          keystore)
        with open(filename, 'rb') as f:
            file_data = f.read()
        md5_digest = hashlib.md5(file_data).hexdigest()
        sha256_digest = hashlib.sha256(file_data).hexdigest()
        d.update({
            ':action': 'file_upload',
            'protocol_version': '1',
            'filetype': filetype,
            'pyversion': pyversion,
            'md5_digest': md5_digest,
            'sha256_digest': sha256_digest,
        })
        files = [('content', os.path.basename(filename), file_data)]
        if sig_file:
            with open(sig_file, 'rb') as f:
                sig_data = f.read()
            files.append(('gpg_signature', os.path.basename(sig_file),
                         sig_data))
            shutil.rmtree(os.path.dirname(sig_file))
        request = self.encode_request(d.items(), files)
        return self.send_request(request)

    def upload_documentation(self, metadata, doc_dir):  # pragma: no cover
        """
        Upload documentation to the index.

        :param metadata: A :class:`Metadata` instance defining at least a name
                         and version number for the documentation to be
                         uploaded.
        :param doc_dir: The pathname of the directory which contains the
                        documentation. This should be the directory that
                        contains the ``index.html`` for the documentation.
        :return: The HTTP response received from PyPI upon submission of the
                request.
        """
        self.check_credentials()
        if not os.path.isdir(doc_dir):
            raise DistlibException('not a directory: %r' % doc_dir)
        fn = os.path.join(doc_dir, 'index.html')
        if not os.path.exists(fn):
            raise DistlibException('not found: %r' % fn)
        metadata.validate()
        name, version = metadata.name, metadata.version
        zip_data = zip_dir(doc_dir).getvalue()
        fields = [(':action', 'doc_upload'),
                  ('name', name), ('version', version)]
        files = [('content', name, zip_data)]
        request = self.encode_request(fields, files)
        return self.send_request(request)

    def get_verify_command(self, signature_filename, data_filename,
                           keystore=None):
        """
        Return a suitable command for verifying a file.

        :param signature_filename: The pathname to the file containing the
                                   signature.
        :param data_filename: The pathname to the file containing the
                              signed data.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: The verifying command as a list suitable to be
                 passed to :class:`subprocess.Popen`.
        """
        cmd = [self.gpg, '--status-fd', '2', '--no-tty']
        if keystore is None:
            keystore = self.gpg_home
        if keystore:
            cmd.extend(['--homedir', keystore])
        cmd.extend(['--verify', signature_filename, data_filename])
        logger.debug('invoking: %s', ' '.join(cmd))
        return cmd

    def verify_signature(self, signature_filename, data_filename,
                         keystore=None):
        """
        Verify a signature for a file.

        :param signature_filename: The pathname to the file containing the
                                   signature.
        :param data_filename: The pathname to the file containing the
                              signed data.
        :param keystore: The path to a directory which contains the keys
                         used in verification. If not specified, the
                         instance's ``gpg_home`` attribute is used instead.
        :return: True if the signature was verified, else False.
        """
        if not self.gpg:
            raise DistlibException('verification unavailable because gpg '
                                   'unavailable')
        cmd = self.get_verify_command(signature_filename, data_filename,
                                      keystore)
        rc, stdout, stderr = self.run_command(cmd)
        if rc not in (0, 1):
            raise DistlibException('verify command failed with error code %s' % rc)
        return rc == 0

    def download_file(self, url, destfile, digest=None, reporthook=None):
        """
        This is a convenience method for downloading a file from an URL.
        Normally, this will be a file from the index, though currently
        no check is made for this (i.e. a file can be downloaded from
        anywhere).

        The method is just like the :func:`urlretrieve` function in the
        standard library, except that it allows digest computation to be
        done during download and checking that the downloaded data
        matched any expected value.

        :param url: The URL of the file to be downloaded (assumed to be
                    available via an HTTP GET request).
        :param destfile: The pathname where the downloaded file is to be
                         saved.
        :param digest: If specified, this must be a (hasher, value)
                       tuple, where hasher is the algorithm used (e.g.
                       ``'md5'``) and ``value`` is the expected value.
        :param reporthook: The same as for :func:`urlretrieve` in the
                           standard library.
        """
        if digest is None:
            digester = None
            logger.debug('No digest specified')
        else:
            if isinstance(digest, (list, tuple)):
                hasher, digest = digest
            else:
                hasher = 'md5'
            digester = getattr(hashlib, hasher)()
            logger.debug('Digest specified: %s' % digest)
        # The following code is equivalent to urlretrieve.
        # We need to do it this way so that we can compute the
        # digest of the file as we go.
        with open(destfile, 'wb') as dfp:
            # addinfourl is not a context manager on 2.x
            # so we have to use try/finally
            sfp = self.send_request(Request(url))
            try:
                headers = sfp.info()
                blocksize = 8192
                size = -1
                read = 0
                blocknum = 0
                if "content-length" in headers:
                    size = int(headers["Content-Length"])
                if reporthook:
                    reporthook(blocknum, blocksize, size)
                while True:
                    block = sfp.read(blocksize)
                    if not block:
                        break
                    read += len(block)
                    dfp.write(block)
                    if digester:
                        digester.update(block)
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, blocksize, size)
            finally:
                sfp.close()

        # check that we got the whole file, if we can
        if size >= 0 and read < size:
            raise DistlibException(
                'retrieval incomplete: got only %d out of %d bytes'
                % (read, size))
        # if we have a digest, it must match.
        if digester:
            actual = digester.hexdigest()
            if digest != actual:
                raise DistlibException('%s digest mismatch for %s: expected '
                                       '%s, got %s' % (hasher, destfile,
                                                       digest, actual))
            logger.debug('Digest verified: %s', digest)

    def send_request(self, req):
        """
        Send a standard library :class:`Request` to PyPI and return its
        response.

        :param req: The request to send.
        :return: The HTTP response from PyPI (a standard library HTTPResponse).
        """
        handlers = []
        if self.password_handler:
            handlers.append(self.password_handler)
        if self.ssl_verifier:
            handlers.append(self.ssl_verifier)
        opener = build_opener(*handlers)
        return opener.open(req)

    def encode_request(self, fields, files):
        """
        Encode fields and files for posting to an HTTP server.

        :param fields: The fields to send as a list of (fieldname, value)
                       tuples.
        :param files: The files to send as a list of (fieldname, filename,
                      file_bytes) tuple.
        """
        # Adapted from packaging, which in turn was adapted from
        # http://code.activestate.com/recipes/146306

        parts = []
        boundary = self.boundary
        for k, values in fields:
            if not isinstance(values, (list, tuple)):
                values = [values]

            for v in values:
                parts.extend((
                    b'--' + boundary,
                    ('Content-Disposition: form-data; name="%s"' %
                     k).encode('utf-8'),
                    b'',
                    v.encode('utf-8')))
        for key, filename, value in files:
            parts.extend((
                b'--' + boundary,
                ('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename)).encode('utf-8'),
                b'',
                value))

        parts.extend((b'--' + boundary + b'--', b''))

        body = b'\r\n'.join(parts)
        ct = b'multipart/form-data; boundary=' + boundary
        headers = {
            'Content-type': ct,
            'Content-length': str(len(body))
        }
        return Request(self.url, body, headers)

    def search(self, terms, operator=None):  # pragma: no cover
        if isinstance(terms, string_types):
            terms = {'name': terms}
        rpc_proxy = ServerProxy(self.url, timeout=3.0)
        try:
            return rpc_proxy.search(terms, operator or 'and')
        finally:
            rpc_proxy('close')()

# === NexusCore/openenv\Lib\site-packages\nltk\inference\prover9.py ===
# Natural Language Toolkit: Interface to the Prover9 Theorem Prover
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
A theorem prover that makes use of the external 'Prover9' package.
"""

import os
import subprocess

import nltk
from nltk.inference.api import BaseProverCommand, Prover
from nltk.sem.logic import (
    AllExpression,
    AndExpression,
    EqualityExpression,
    ExistsExpression,
    Expression,
    IffExpression,
    ImpExpression,
    NegatedExpression,
    OrExpression,
)

#
# Following is not yet used. Return code for 2 actually realized as 512.
#
p9_return_codes = {
    0: True,
    1: "(FATAL)",  # A fatal error occurred (user's syntax error).
    2: False,  # (SOS_EMPTY) Prover9 ran out of things to do
    #   (sos list exhausted).
    3: "(MAX_MEGS)",  # The max_megs (memory limit) parameter was exceeded.
    4: "(MAX_SECONDS)",  # The max_seconds parameter was exceeded.
    5: "(MAX_GIVEN)",  # The max_given parameter was exceeded.
    6: "(MAX_KEPT)",  # The max_kept parameter was exceeded.
    7: "(ACTION)",  # A Prover9 action terminated the search.
    101: "(SIGSEGV)",  # Prover9 crashed, most probably due to a bug.
}


class Prover9CommandParent:
    """
    A common base class used by both ``Prover9Command`` and ``MaceCommand``,
    which is responsible for maintaining a goal and a set of assumptions,
    and generating prover9-style input files from them.
    """

    def print_assumptions(self, output_format="nltk"):
        """
        Print the list of the current assumptions.
        """
        if output_format.lower() == "nltk":
            for a in self.assumptions():
                print(a)
        elif output_format.lower() == "prover9":
            for a in convert_to_prover9(self.assumptions()):
                print(a)
        else:
            raise NameError(
                "Unrecognized value for 'output_format': %s" % output_format
            )


class Prover9Command(Prover9CommandParent, BaseProverCommand):
    """
    A ``ProverCommand`` specific to the ``Prover9`` prover.  It contains
    the a print_assumptions() method that is used to print the list
    of assumptions in multiple formats.
    """

    def __init__(self, goal=None, assumptions=None, timeout=60, prover=None):
        """
        :param goal: Input expression to prove
        :type goal: sem.Expression
        :param assumptions: Input expressions to use as assumptions in
            the proof.
        :type assumptions: list(sem.Expression)
        :param timeout: number of seconds before timeout; set to 0 for
            no timeout.
        :type timeout: int
        :param prover: a prover.  If not set, one will be created.
        :type prover: Prover9
        """
        if not assumptions:
            assumptions = []

        if prover is not None:
            assert isinstance(prover, Prover9)
        else:
            prover = Prover9(timeout)

        BaseProverCommand.__init__(self, prover, goal, assumptions)

    def decorate_proof(self, proof_string, simplify=True):
        """
        :see BaseProverCommand.decorate_proof()
        """
        if simplify:
            return self._prover._call_prooftrans(proof_string, ["striplabels"])[
                0
            ].rstrip()
        else:
            return proof_string.rstrip()


class Prover9Parent:
    """
    A common class extended by both ``Prover9`` and ``Mace <mace.Mace>``.
    It contains the functionality required to convert NLTK-style
    expressions into Prover9-style expressions.
    """

    _binary_location = None

    def config_prover9(self, binary_location, verbose=False):
        if binary_location is None:
            self._binary_location = None
            self._prover9_bin = None
        else:
            name = "prover9"
            self._prover9_bin = nltk.internals.find_binary(
                name,
                path_to_bin=binary_location,
                env_vars=["PROVER9"],
                url="https://www.cs.unm.edu/~mccune/prover9/",
                binary_names=[name, name + ".exe"],
                verbose=verbose,
            )
            self._binary_location = self._prover9_bin.rsplit(os.path.sep, 1)

    def prover9_input(self, goal, assumptions):
        """
        :return: The input string that should be provided to the
            prover9 binary.  This string is formed based on the goal,
            assumptions, and timeout value of this object.
        """
        s = ""

        if assumptions:
            s += "formulas(assumptions).\n"
            for p9_assumption in convert_to_prover9(assumptions):
                s += "    %s.\n" % p9_assumption
            s += "end_of_list.\n\n"

        if goal:
            s += "formulas(goals).\n"
            s += "    %s.\n" % convert_to_prover9(goal)
            s += "end_of_list.\n\n"

        return s

    def binary_locations(self):
        """
        A list of directories that should be searched for the prover9
        executables.  This list is used by ``config_prover9`` when searching
        for the prover9 executables.
        """
        return [
            "/usr/local/bin/prover9",
            "/usr/local/bin/prover9/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/usr/local/prover9",
            "/usr/local/share/prover9",
        ]

    def _find_binary(self, name, verbose=False):
        binary_locations = self.binary_locations()
        if self._binary_location is not None:
            binary_locations += [self._binary_location]
        return nltk.internals.find_binary(
            name,
            searchpath=binary_locations,
            env_vars=["PROVER9"],
            url="https://www.cs.unm.edu/~mccune/prover9/",
            binary_names=[name, name + ".exe"],
            verbose=verbose,
        )

    def _call(self, input_str, binary, args=[], verbose=False):
        """
        Call the binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param binary: The location of the binary to call
        :param args: A list of command-line arguments.
        :return: A tuple (stdout, returncode)
        :see: ``config_prover9``
        """
        if verbose:
            print("Calling:", binary)
            print("Args:", args)
            print("Input:\n", input_str, "\n")

        # Call prover9 via a subprocess
        cmd = [binary] + args
        try:
            input_str = input_str.encode("utf8")
        except AttributeError:
            pass
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE
        )
        (stdout, stderr) = p.communicate(input=input_str)

        if verbose:
            print("Return code:", p.returncode)
            if stdout:
                print("stdout:\n", stdout, "\n")
            if stderr:
                print("stderr:\n", stderr, "\n")

        return (stdout.decode("utf-8"), p.returncode)


def convert_to_prover9(input):
    """
    Convert a ``logic.Expression`` to Prover9 format.
    """
    if isinstance(input, list):
        result = []
        for s in input:
            try:
                result.append(_convert_to_prover9(s.simplify()))
            except:
                print("input %s cannot be converted to Prover9 input syntax" % input)
                raise
        return result
    else:
        try:
            return _convert_to_prover9(input.simplify())
        except:
            print("input %s cannot be converted to Prover9 input syntax" % input)
            raise


def _convert_to_prover9(expression):
    """
    Convert ``logic.Expression`` to Prover9 formatted string.
    """
    if isinstance(expression, ExistsExpression):
        return (
            "exists "
            + str(expression.variable)
            + " "
            + _convert_to_prover9(expression.term)
        )
    elif isinstance(expression, AllExpression):
        return (
            "all "
            + str(expression.variable)
            + " "
            + _convert_to_prover9(expression.term)
        )
    elif isinstance(expression, NegatedExpression):
        return "-(" + _convert_to_prover9(expression.term) + ")"
    elif isinstance(expression, AndExpression):
        return (
            "("
            + _convert_to_prover9(expression.first)
            + " & "
            + _convert_to_prover9(expression.second)
            + ")"
        )
    elif isinstance(expression, OrExpression):
        return (
            "("
            + _convert_to_prover9(expression.first)
            + " | "
            + _convert_to_prover9(expression.second)
            + ")"
        )
    elif isinstance(expression, ImpExpression):
        return (
            "("
            + _convert_to_prover9(expression.first)
            + " -> "
            + _convert_to_prover9(expression.second)
            + ")"
        )
    elif isinstance(expression, IffExpression):
        return (
            "("
            + _convert_to_prover9(expression.first)
            + " <-> "
            + _convert_to_prover9(expression.second)
            + ")"
        )
    elif isinstance(expression, EqualityExpression):
        return (
            "("
            + _convert_to_prover9(expression.first)
            + " = "
            + _convert_to_prover9(expression.second)
            + ")"
        )
    else:
        return str(expression)


class Prover9(Prover9Parent, Prover):
    _prover9_bin = None
    _prooftrans_bin = None

    def __init__(self, timeout=60):
        self._timeout = timeout
        """The timeout value for prover9.  If a proof can not be found
           in this amount of time, then prover9 will return false.
           (Use 0 for no timeout.)"""

    def _prove(self, goal=None, assumptions=None, verbose=False):
        """
        Use Prover9 to prove a theorem.
        :return: A pair whose first element is a boolean indicating if the
        proof was successful (i.e. returns value of 0) and whose second element
        is the output of the prover.
        """
        if not assumptions:
            assumptions = []

        stdout, returncode = self._call_prover9(
            self.prover9_input(goal, assumptions), verbose=verbose
        )
        return (returncode == 0, stdout)

    def prover9_input(self, goal, assumptions):
        """
        :see: Prover9Parent.prover9_input
        """
        s = "clear(auto_denials).\n"  # only one proof required
        return s + Prover9Parent.prover9_input(self, goal, assumptions)

    def _call_prover9(self, input_str, args=[], verbose=False):
        """
        Call the ``prover9`` binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param args: A list of command-line arguments.
        :return: A tuple (stdout, returncode)
        :see: ``config_prover9``
        """
        if self._prover9_bin is None:
            self._prover9_bin = self._find_binary("prover9", verbose)

        updated_input_str = ""
        if self._timeout > 0:
            updated_input_str += "assign(max_seconds, %d).\n\n" % self._timeout
        updated_input_str += input_str

        stdout, returncode = self._call(
            updated_input_str, self._prover9_bin, args, verbose
        )

        if returncode not in [0, 2]:
            errormsgprefix = "%%ERROR:"
            if errormsgprefix in stdout:
                msgstart = stdout.index(errormsgprefix)
                errormsg = stdout[msgstart:].strip()
            else:
                errormsg = None
            if returncode in [3, 4, 5, 6]:
                raise Prover9LimitExceededException(returncode, errormsg)
            else:
                raise Prover9FatalException(returncode, errormsg)

        return stdout, returncode

    def _call_prooftrans(self, input_str, args=[], verbose=False):
        """
        Call the ``prooftrans`` binary with the given input.

        :param input_str: A string whose contents are used as stdin.
        :param args: A list of command-line arguments.
        :return: A tuple (stdout, returncode)
        :see: ``config_prover9``
        """
        if self._prooftrans_bin is None:
            self._prooftrans_bin = self._find_binary("prooftrans", verbose)

        return self._call(input_str, self._prooftrans_bin, args, verbose)


class Prover9Exception(Exception):
    def __init__(self, returncode, message):
        msg = p9_return_codes[returncode]
        if message:
            msg += "\n%s" % message
        Exception.__init__(self, msg)


class Prover9FatalException(Prover9Exception):
    pass


class Prover9LimitExceededException(Prover9Exception):
    pass


######################################################################
# { Tests and Demos
######################################################################


def test_config():
    a = Expression.fromstring("(walk(j) & sing(j))")
    g = Expression.fromstring("walk(j)")
    p = Prover9Command(g, assumptions=[a])
    p._executable_path = None
    p.prover9_search = []
    p.prove()
    # config_prover9('/usr/local/bin')
    print(p.prove())
    print(p.proof())


def test_convert_to_prover9(expr):
    """
    Test that parsing works OK.
    """
    for t in expr:
        e = Expression.fromstring(t)
        print(convert_to_prover9(e))


def test_prove(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for goal, assumptions in arguments:
        g = Expression.fromstring(goal)
        alist = [Expression.fromstring(a) for a in assumptions]
        p = Prover9Command(g, assumptions=alist).prove()
        for a in alist:
            print("   %s" % a)
        print(f"|- {g}: {p}\n")


arguments = [
    ("(man(x) <-> (not (not man(x))))", []),
    ("(not (man(x) & (not man(x))))", []),
    ("(man(x) | (not man(x)))", []),
    ("(man(x) & (not man(x)))", []),
    ("(man(x) -> man(x))", []),
    ("(not (man(x) & (not man(x))))", []),
    ("(man(x) | (not man(x)))", []),
    ("(man(x) -> man(x))", []),
    ("(man(x) <-> man(x))", []),
    ("(not (man(x) <-> (not man(x))))", []),
    ("mortal(Socrates)", ["all x.(man(x) -> mortal(x))", "man(Socrates)"]),
    ("((all x.(man(x) -> walks(x)) & man(Socrates)) -> some y.walks(y))", []),
    ("(all x.man(x) -> all x.man(x))", []),
    ("some x.all y.sees(x,y)", []),
    (
        "some e3.(walk(e3) & subj(e3, mary))",
        [
            "some e1.(see(e1) & subj(e1, john) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))"
        ],
    ),
    (
        "some x e1.(see(e1) & subj(e1, x) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))",
        [
            "some e1.(see(e1) & subj(e1, john) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))"
        ],
    ),
]

expressions = [
    r"some x y.sees(x,y)",
    r"some x.(man(x) & walks(x))",
    r"\x.(man(x) & walks(x))",
    r"\x y.sees(x,y)",
    r"walks(john)",
    r"\x.big(x, \y.mouse(y))",
    r"(walks(x) & (runs(x) & (threes(x) & fours(x))))",
    r"(walks(x) -> runs(x))",
    r"some x.(PRO(x) & sees(John, x))",
    r"some x.(man(x) & (not walks(x)))",
    r"all x.(man(x) -> walks(x))",
]


def spacer(num=45):
    print("-" * num)


def demo():
    print("Testing configuration")
    spacer()
    test_config()
    print()
    print("Testing conversion to Prover9 format")
    spacer()
    test_convert_to_prover9(expressions)
    print()
    print("Testing proofs")
    spacer()
    test_prove(arguments)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\security.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Security
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network


class CertificateId(int):
    '''
    An internal certificate ID value.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> CertificateId:
        return cls(json)

    def __repr__(self):
        return 'CertificateId({})'.format(super().__repr__())


class MixedContentType(enum.Enum):
    '''
    A description of mixed content (HTTP resources on HTTPS pages), as defined by
    https://www.w3.org/TR/mixed-content/#categories
    '''
    BLOCKABLE = "blockable"
    OPTIONALLY_BLOCKABLE = "optionally-blockable"
    NONE = "none"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SecurityState(enum.Enum):
    '''
    The security level of a page or resource.
    '''
    UNKNOWN = "unknown"
    NEUTRAL = "neutral"
    INSECURE = "insecure"
    SECURE = "secure"
    INFO = "info"
    INSECURE_BROKEN = "insecure-broken"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CertificateSecurityState:
    '''
    Details about the security state of the page certificate.
    '''
    #: Protocol name (e.g. "TLS 1.2" or "QUIC").
    protocol: str

    #: Key Exchange used by the connection, or the empty string if not applicable.
    key_exchange: str

    #: Cipher name.
    cipher: str

    #: Page certificate.
    certificate: typing.List[str]

    #: Certificate subject name.
    subject_name: str

    #: Name of the issuing CA.
    issuer: str

    #: Certificate valid from date.
    valid_from: network.TimeSinceEpoch

    #: Certificate valid to (expiration) date
    valid_to: network.TimeSinceEpoch

    #: True if the certificate uses a weak signature algorithm.
    certificate_has_weak_signature: bool

    #: True if the certificate has a SHA1 signature in the chain.
    certificate_has_sha1_signature: bool

    #: True if modern SSL
    modern_ssl: bool

    #: True if the connection is using an obsolete SSL protocol.
    obsolete_ssl_protocol: bool

    #: True if the connection is using an obsolete SSL key exchange.
    obsolete_ssl_key_exchange: bool

    #: True if the connection is using an obsolete SSL cipher.
    obsolete_ssl_cipher: bool

    #: True if the connection is using an obsolete SSL signature.
    obsolete_ssl_signature: bool

    #: (EC)DH group used by the connection, if applicable.
    key_exchange_group: typing.Optional[str] = None

    #: TLS MAC. Note that AEAD ciphers do not have separate MACs.
    mac: typing.Optional[str] = None

    #: The highest priority network error code, if the certificate has an error.
    certificate_network_error: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['keyExchange'] = self.key_exchange
        json['cipher'] = self.cipher
        json['certificate'] = [i for i in self.certificate]
        json['subjectName'] = self.subject_name
        json['issuer'] = self.issuer
        json['validFrom'] = self.valid_from.to_json()
        json['validTo'] = self.valid_to.to_json()
        json['certificateHasWeakSignature'] = self.certificate_has_weak_signature
        json['certificateHasSha1Signature'] = self.certificate_has_sha1_signature
        json['modernSSL'] = self.modern_ssl
        json['obsoleteSslProtocol'] = self.obsolete_ssl_protocol
        json['obsoleteSslKeyExchange'] = self.obsolete_ssl_key_exchange
        json['obsoleteSslCipher'] = self.obsolete_ssl_cipher
        json['obsoleteSslSignature'] = self.obsolete_ssl_signature
        if self.key_exchange_group is not None:
            json['keyExchangeGroup'] = self.key_exchange_group
        if self.mac is not None:
            json['mac'] = self.mac
        if self.certificate_network_error is not None:
            json['certificateNetworkError'] = self.certificate_network_error
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            key_exchange=str(json['keyExchange']),
            cipher=str(json['cipher']),
            certificate=[str(i) for i in json['certificate']],
            subject_name=str(json['subjectName']),
            issuer=str(json['issuer']),
            valid_from=network.TimeSinceEpoch.from_json(json['validFrom']),
            valid_to=network.TimeSinceEpoch.from_json(json['validTo']),
            certificate_has_weak_signature=bool(json['certificateHasWeakSignature']),
            certificate_has_sha1_signature=bool(json['certificateHasSha1Signature']),
            modern_ssl=bool(json['modernSSL']),
            obsolete_ssl_protocol=bool(json['obsoleteSslProtocol']),
            obsolete_ssl_key_exchange=bool(json['obsoleteSslKeyExchange']),
            obsolete_ssl_cipher=bool(json['obsoleteSslCipher']),
            obsolete_ssl_signature=bool(json['obsoleteSslSignature']),
            key_exchange_group=str(json['keyExchangeGroup']) if 'keyExchangeGroup' in json else None,
            mac=str(json['mac']) if 'mac' in json else None,
            certificate_network_error=str(json['certificateNetworkError']) if 'certificateNetworkError' in json else None,
        )


class SafetyTipStatus(enum.Enum):
    BAD_REPUTATION = "badReputation"
    LOOKALIKE = "lookalike"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SafetyTipInfo:
    #: Describes whether the page triggers any safety tips or reputation warnings. Default is unknown.
    safety_tip_status: SafetyTipStatus

    #: The URL the safety tip suggested ("Did you mean?"). Only filled in for lookalike matches.
    safe_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['safetyTipStatus'] = self.safety_tip_status.to_json()
        if self.safe_url is not None:
            json['safeUrl'] = self.safe_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            safety_tip_status=SafetyTipStatus.from_json(json['safetyTipStatus']),
            safe_url=str(json['safeUrl']) if 'safeUrl' in json else None,
        )


@dataclass
class VisibleSecurityState:
    '''
    Security state information about the page.
    '''
    #: The security level of the page.
    security_state: SecurityState

    #: Array of security state issues ids.
    security_state_issue_ids: typing.List[str]

    #: Security state details about the page certificate.
    certificate_security_state: typing.Optional[CertificateSecurityState] = None

    #: The type of Safety Tip triggered on the page. Note that this field will be set even if the Safety Tip UI was not actually shown.
    safety_tip_info: typing.Optional[SafetyTipInfo] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['securityStateIssueIds'] = [i for i in self.security_state_issue_ids]
        if self.certificate_security_state is not None:
            json['certificateSecurityState'] = self.certificate_security_state.to_json()
        if self.safety_tip_info is not None:
            json['safetyTipInfo'] = self.safety_tip_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            security_state_issue_ids=[str(i) for i in json['securityStateIssueIds']],
            certificate_security_state=CertificateSecurityState.from_json(json['certificateSecurityState']) if 'certificateSecurityState' in json else None,
            safety_tip_info=SafetyTipInfo.from_json(json['safetyTipInfo']) if 'safetyTipInfo' in json else None,
        )


@dataclass
class SecurityStateExplanation:
    '''
    An explanation of an factor contributing to the security state.
    '''
    #: Security state representing the severity of the factor being explained.
    security_state: SecurityState

    #: Title describing the type of factor.
    title: str

    #: Short phrase describing the type of factor.
    summary: str

    #: Full text explanation of the factor.
    description: str

    #: The type of mixed content described by the explanation.
    mixed_content_type: MixedContentType

    #: Page certificate.
    certificate: typing.List[str]

    #: Recommendations to fix any issues.
    recommendations: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['title'] = self.title
        json['summary'] = self.summary
        json['description'] = self.description
        json['mixedContentType'] = self.mixed_content_type.to_json()
        json['certificate'] = [i for i in self.certificate]
        if self.recommendations is not None:
            json['recommendations'] = [i for i in self.recommendations]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            title=str(json['title']),
            summary=str(json['summary']),
            description=str(json['description']),
            mixed_content_type=MixedContentType.from_json(json['mixedContentType']),
            certificate=[str(i) for i in json['certificate']],
            recommendations=[str(i) for i in json['recommendations']] if 'recommendations' in json else None,
        )


@dataclass
class InsecureContentStatus:
    '''
    Information about insecure content on the page.
    '''
    #: Always false.
    ran_mixed_content: bool

    #: Always false.
    displayed_mixed_content: bool

    #: Always false.
    contained_mixed_form: bool

    #: Always false.
    ran_content_with_cert_errors: bool

    #: Always false.
    displayed_content_with_cert_errors: bool

    #: Always set to unknown.
    ran_insecure_content_style: SecurityState

    #: Always set to unknown.
    displayed_insecure_content_style: SecurityState

    def to_json(self):
        json = dict()
        json['ranMixedContent'] = self.ran_mixed_content
        json['displayedMixedContent'] = self.displayed_mixed_content
        json['containedMixedForm'] = self.contained_mixed_form
        json['ranContentWithCertErrors'] = self.ran_content_with_cert_errors
        json['displayedContentWithCertErrors'] = self.displayed_content_with_cert_errors
        json['ranInsecureContentStyle'] = self.ran_insecure_content_style.to_json()
        json['displayedInsecureContentStyle'] = self.displayed_insecure_content_style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            ran_mixed_content=bool(json['ranMixedContent']),
            displayed_mixed_content=bool(json['displayedMixedContent']),
            contained_mixed_form=bool(json['containedMixedForm']),
            ran_content_with_cert_errors=bool(json['ranContentWithCertErrors']),
            displayed_content_with_cert_errors=bool(json['displayedContentWithCertErrors']),
            ran_insecure_content_style=SecurityState.from_json(json['ranInsecureContentStyle']),
            displayed_insecure_content_style=SecurityState.from_json(json['displayedInsecureContentStyle']),
        )


class CertificateErrorAction(enum.Enum):
    '''
    The action to take when a certificate error occurs. continue will continue processing the
    request and cancel will cancel the request.
    '''
    CONTINUE = "continue"
    CANCEL = "cancel"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.enable',
    }
    json = yield cmd_dict


def set_ignore_certificate_errors(
        ignore: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable whether all certificate errors should be ignored.

    :param ignore: If true, all certificate errors will be ignored.
    '''
    params: T_JSON_DICT = dict()
    params['ignore'] = ignore
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setIgnoreCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


def handle_certificate_error(
        event_id: int,
        action: CertificateErrorAction
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Handles a certificate error that fired a certificateError event.

    :param event_id: The ID of the event.
    :param action: The action to take on the certificate error.
    '''
    params: T_JSON_DICT = dict()
    params['eventId'] = event_id
    params['action'] = action.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.handleCertificateError',
        'params': params,
    }
    json = yield cmd_dict


def set_override_certificate_errors(
        override: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable overriding certificate errors. If enabled, all certificate error events need to
    be handled by the DevTools client and should be answered with ``handleCertificateError`` commands.

    :param override: If true, certificate errors will be overridden.
    '''
    params: T_JSON_DICT = dict()
    params['override'] = override
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setOverrideCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Security.certificateError')
@dataclass
class CertificateError:
    '''
    There is a certificate error. If overriding certificate errors is enabled, then it should be
    handled with the ``handleCertificateError`` command. Note: this event does not fire if the
    certificate error has been allowed internally. Only one client per target should override
    certificate errors at the same time.
    '''
    #: The ID of the event.
    event_id: int
    #: The type of the error.
    error_type: str
    #: The url that was requested.
    request_url: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CertificateError:
        return cls(
            event_id=int(json['eventId']),
            error_type=str(json['errorType']),
            request_url=str(json['requestURL'])
        )


@event_class('Security.visibleSecurityStateChanged')
@dataclass
class VisibleSecurityStateChanged:
    '''
    **EXPERIMENTAL**

    The security state of the page changed.
    '''
    #: Security state information about the page.
    visible_security_state: VisibleSecurityState

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> VisibleSecurityStateChanged:
        return cls(
            visible_security_state=VisibleSecurityState.from_json(json['visibleSecurityState'])
        )


@event_class('Security.securityStateChanged')
@dataclass
class SecurityStateChanged:
    '''
    The security state of the page changed. No longer being sent.
    '''
    #: Security state.
    security_state: SecurityState
    #: True if the page was loaded over cryptographic transport such as HTTPS.
    scheme_is_cryptographic: bool
    #: Previously a list of explanations for the security state. Now always
    #: empty.
    explanations: typing.List[SecurityStateExplanation]
    #: Information about insecure content on the page.
    insecure_content_status: InsecureContentStatus
    #: Overrides user-visible description of the state. Always omitted.
    summary: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SecurityStateChanged:
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            scheme_is_cryptographic=bool(json['schemeIsCryptographic']),
            explanations=[SecurityStateExplanation.from_json(i) for i in json['explanations']],
            insecure_content_status=InsecureContentStatus.from_json(json['insecureContentStatus']),
            summary=str(json['summary']) if 'summary' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\security.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Security
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network


class CertificateId(int):
    '''
    An internal certificate ID value.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> CertificateId:
        return cls(json)

    def __repr__(self):
        return 'CertificateId({})'.format(super().__repr__())


class MixedContentType(enum.Enum):
    '''
    A description of mixed content (HTTP resources on HTTPS pages), as defined by
    https://www.w3.org/TR/mixed-content/#categories
    '''
    BLOCKABLE = "blockable"
    OPTIONALLY_BLOCKABLE = "optionally-blockable"
    NONE = "none"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SecurityState(enum.Enum):
    '''
    The security level of a page or resource.
    '''
    UNKNOWN = "unknown"
    NEUTRAL = "neutral"
    INSECURE = "insecure"
    SECURE = "secure"
    INFO = "info"
    INSECURE_BROKEN = "insecure-broken"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CertificateSecurityState:
    '''
    Details about the security state of the page certificate.
    '''
    #: Protocol name (e.g. "TLS 1.2" or "QUIC").
    protocol: str

    #: Key Exchange used by the connection, or the empty string if not applicable.
    key_exchange: str

    #: Cipher name.
    cipher: str

    #: Page certificate.
    certificate: typing.List[str]

    #: Certificate subject name.
    subject_name: str

    #: Name of the issuing CA.
    issuer: str

    #: Certificate valid from date.
    valid_from: network.TimeSinceEpoch

    #: Certificate valid to (expiration) date
    valid_to: network.TimeSinceEpoch

    #: True if the certificate uses a weak signature algorithm.
    certificate_has_weak_signature: bool

    #: True if the certificate has a SHA1 signature in the chain.
    certificate_has_sha1_signature: bool

    #: True if modern SSL
    modern_ssl: bool

    #: True if the connection is using an obsolete SSL protocol.
    obsolete_ssl_protocol: bool

    #: True if the connection is using an obsolete SSL key exchange.
    obsolete_ssl_key_exchange: bool

    #: True if the connection is using an obsolete SSL cipher.
    obsolete_ssl_cipher: bool

    #: True if the connection is using an obsolete SSL signature.
    obsolete_ssl_signature: bool

    #: (EC)DH group used by the connection, if applicable.
    key_exchange_group: typing.Optional[str] = None

    #: TLS MAC. Note that AEAD ciphers do not have separate MACs.
    mac: typing.Optional[str] = None

    #: The highest priority network error code, if the certificate has an error.
    certificate_network_error: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['keyExchange'] = self.key_exchange
        json['cipher'] = self.cipher
        json['certificate'] = [i for i in self.certificate]
        json['subjectName'] = self.subject_name
        json['issuer'] = self.issuer
        json['validFrom'] = self.valid_from.to_json()
        json['validTo'] = self.valid_to.to_json()
        json['certificateHasWeakSignature'] = self.certificate_has_weak_signature
        json['certificateHasSha1Signature'] = self.certificate_has_sha1_signature
        json['modernSSL'] = self.modern_ssl
        json['obsoleteSslProtocol'] = self.obsolete_ssl_protocol
        json['obsoleteSslKeyExchange'] = self.obsolete_ssl_key_exchange
        json['obsoleteSslCipher'] = self.obsolete_ssl_cipher
        json['obsoleteSslSignature'] = self.obsolete_ssl_signature
        if self.key_exchange_group is not None:
            json['keyExchangeGroup'] = self.key_exchange_group
        if self.mac is not None:
            json['mac'] = self.mac
        if self.certificate_network_error is not None:
            json['certificateNetworkError'] = self.certificate_network_error
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            key_exchange=str(json['keyExchange']),
            cipher=str(json['cipher']),
            certificate=[str(i) for i in json['certificate']],
            subject_name=str(json['subjectName']),
            issuer=str(json['issuer']),
            valid_from=network.TimeSinceEpoch.from_json(json['validFrom']),
            valid_to=network.TimeSinceEpoch.from_json(json['validTo']),
            certificate_has_weak_signature=bool(json['certificateHasWeakSignature']),
            certificate_has_sha1_signature=bool(json['certificateHasSha1Signature']),
            modern_ssl=bool(json['modernSSL']),
            obsolete_ssl_protocol=bool(json['obsoleteSslProtocol']),
            obsolete_ssl_key_exchange=bool(json['obsoleteSslKeyExchange']),
            obsolete_ssl_cipher=bool(json['obsoleteSslCipher']),
            obsolete_ssl_signature=bool(json['obsoleteSslSignature']),
            key_exchange_group=str(json['keyExchangeGroup']) if 'keyExchangeGroup' in json else None,
            mac=str(json['mac']) if 'mac' in json else None,
            certificate_network_error=str(json['certificateNetworkError']) if 'certificateNetworkError' in json else None,
        )


class SafetyTipStatus(enum.Enum):
    BAD_REPUTATION = "badReputation"
    LOOKALIKE = "lookalike"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SafetyTipInfo:
    #: Describes whether the page triggers any safety tips or reputation warnings. Default is unknown.
    safety_tip_status: SafetyTipStatus

    #: The URL the safety tip suggested ("Did you mean?"). Only filled in for lookalike matches.
    safe_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['safetyTipStatus'] = self.safety_tip_status.to_json()
        if self.safe_url is not None:
            json['safeUrl'] = self.safe_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            safety_tip_status=SafetyTipStatus.from_json(json['safetyTipStatus']),
            safe_url=str(json['safeUrl']) if 'safeUrl' in json else None,
        )


@dataclass
class VisibleSecurityState:
    '''
    Security state information about the page.
    '''
    #: The security level of the page.
    security_state: SecurityState

    #: Array of security state issues ids.
    security_state_issue_ids: typing.List[str]

    #: Security state details about the page certificate.
    certificate_security_state: typing.Optional[CertificateSecurityState] = None

    #: The type of Safety Tip triggered on the page. Note that this field will be set even if the Safety Tip UI was not actually shown.
    safety_tip_info: typing.Optional[SafetyTipInfo] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['securityStateIssueIds'] = [i for i in self.security_state_issue_ids]
        if self.certificate_security_state is not None:
            json['certificateSecurityState'] = self.certificate_security_state.to_json()
        if self.safety_tip_info is not None:
            json['safetyTipInfo'] = self.safety_tip_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            security_state_issue_ids=[str(i) for i in json['securityStateIssueIds']],
            certificate_security_state=CertificateSecurityState.from_json(json['certificateSecurityState']) if 'certificateSecurityState' in json else None,
            safety_tip_info=SafetyTipInfo.from_json(json['safetyTipInfo']) if 'safetyTipInfo' in json else None,
        )


@dataclass
class SecurityStateExplanation:
    '''
    An explanation of an factor contributing to the security state.
    '''
    #: Security state representing the severity of the factor being explained.
    security_state: SecurityState

    #: Title describing the type of factor.
    title: str

    #: Short phrase describing the type of factor.
    summary: str

    #: Full text explanation of the factor.
    description: str

    #: The type of mixed content described by the explanation.
    mixed_content_type: MixedContentType

    #: Page certificate.
    certificate: typing.List[str]

    #: Recommendations to fix any issues.
    recommendations: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['title'] = self.title
        json['summary'] = self.summary
        json['description'] = self.description
        json['mixedContentType'] = self.mixed_content_type.to_json()
        json['certificate'] = [i for i in self.certificate]
        if self.recommendations is not None:
            json['recommendations'] = [i for i in self.recommendations]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            title=str(json['title']),
            summary=str(json['summary']),
            description=str(json['description']),
            mixed_content_type=MixedContentType.from_json(json['mixedContentType']),
            certificate=[str(i) for i in json['certificate']],
            recommendations=[str(i) for i in json['recommendations']] if 'recommendations' in json else None,
        )


@dataclass
class InsecureContentStatus:
    '''
    Information about insecure content on the page.
    '''
    #: Always false.
    ran_mixed_content: bool

    #: Always false.
    displayed_mixed_content: bool

    #: Always false.
    contained_mixed_form: bool

    #: Always false.
    ran_content_with_cert_errors: bool

    #: Always false.
    displayed_content_with_cert_errors: bool

    #: Always set to unknown.
    ran_insecure_content_style: SecurityState

    #: Always set to unknown.
    displayed_insecure_content_style: SecurityState

    def to_json(self):
        json = dict()
        json['ranMixedContent'] = self.ran_mixed_content
        json['displayedMixedContent'] = self.displayed_mixed_content
        json['containedMixedForm'] = self.contained_mixed_form
        json['ranContentWithCertErrors'] = self.ran_content_with_cert_errors
        json['displayedContentWithCertErrors'] = self.displayed_content_with_cert_errors
        json['ranInsecureContentStyle'] = self.ran_insecure_content_style.to_json()
        json['displayedInsecureContentStyle'] = self.displayed_insecure_content_style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            ran_mixed_content=bool(json['ranMixedContent']),
            displayed_mixed_content=bool(json['displayedMixedContent']),
            contained_mixed_form=bool(json['containedMixedForm']),
            ran_content_with_cert_errors=bool(json['ranContentWithCertErrors']),
            displayed_content_with_cert_errors=bool(json['displayedContentWithCertErrors']),
            ran_insecure_content_style=SecurityState.from_json(json['ranInsecureContentStyle']),
            displayed_insecure_content_style=SecurityState.from_json(json['displayedInsecureContentStyle']),
        )


class CertificateErrorAction(enum.Enum):
    '''
    The action to take when a certificate error occurs. continue will continue processing the
    request and cancel will cancel the request.
    '''
    CONTINUE = "continue"
    CANCEL = "cancel"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.enable',
    }
    json = yield cmd_dict


def set_ignore_certificate_errors(
        ignore: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable whether all certificate errors should be ignored.

    :param ignore: If true, all certificate errors will be ignored.
    '''
    params: T_JSON_DICT = dict()
    params['ignore'] = ignore
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setIgnoreCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


def handle_certificate_error(
        event_id: int,
        action: CertificateErrorAction
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Handles a certificate error that fired a certificateError event.

    :param event_id: The ID of the event.
    :param action: The action to take on the certificate error.
    '''
    params: T_JSON_DICT = dict()
    params['eventId'] = event_id
    params['action'] = action.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.handleCertificateError',
        'params': params,
    }
    json = yield cmd_dict


def set_override_certificate_errors(
        override: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable overriding certificate errors. If enabled, all certificate error events need to
    be handled by the DevTools client and should be answered with ``handleCertificateError`` commands.

    :param override: If true, certificate errors will be overridden.
    '''
    params: T_JSON_DICT = dict()
    params['override'] = override
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setOverrideCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Security.certificateError')
@dataclass
class CertificateError:
    '''
    There is a certificate error. If overriding certificate errors is enabled, then it should be
    handled with the ``handleCertificateError`` command. Note: this event does not fire if the
    certificate error has been allowed internally. Only one client per target should override
    certificate errors at the same time.
    '''
    #: The ID of the event.
    event_id: int
    #: The type of the error.
    error_type: str
    #: The url that was requested.
    request_url: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CertificateError:
        return cls(
            event_id=int(json['eventId']),
            error_type=str(json['errorType']),
            request_url=str(json['requestURL'])
        )


@event_class('Security.visibleSecurityStateChanged')
@dataclass
class VisibleSecurityStateChanged:
    '''
    **EXPERIMENTAL**

    The security state of the page changed.
    '''
    #: Security state information about the page.
    visible_security_state: VisibleSecurityState

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> VisibleSecurityStateChanged:
        return cls(
            visible_security_state=VisibleSecurityState.from_json(json['visibleSecurityState'])
        )


@event_class('Security.securityStateChanged')
@dataclass
class SecurityStateChanged:
    '''
    The security state of the page changed. No longer being sent.
    '''
    #: Security state.
    security_state: SecurityState
    #: True if the page was loaded over cryptographic transport such as HTTPS.
    scheme_is_cryptographic: bool
    #: Previously a list of explanations for the security state. Now always
    #: empty.
    explanations: typing.List[SecurityStateExplanation]
    #: Information about insecure content on the page.
    insecure_content_status: InsecureContentStatus
    #: Overrides user-visible description of the state. Always omitted.
    summary: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SecurityStateChanged:
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            scheme_is_cryptographic=bool(json['schemeIsCryptographic']),
            explanations=[SecurityStateExplanation.from_json(i) for i in json['explanations']],
            insecure_content_status=InsecureContentStatus.from_json(json['insecureContentStatus']),
            summary=str(json['summary']) if 'summary' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\security.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Security
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network


class CertificateId(int):
    '''
    An internal certificate ID value.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> CertificateId:
        return cls(json)

    def __repr__(self):
        return 'CertificateId({})'.format(super().__repr__())


class MixedContentType(enum.Enum):
    '''
    A description of mixed content (HTTP resources on HTTPS pages), as defined by
    https://www.w3.org/TR/mixed-content/#categories
    '''
    BLOCKABLE = "blockable"
    OPTIONALLY_BLOCKABLE = "optionally-blockable"
    NONE = "none"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SecurityState(enum.Enum):
    '''
    The security level of a page or resource.
    '''
    UNKNOWN = "unknown"
    NEUTRAL = "neutral"
    INSECURE = "insecure"
    SECURE = "secure"
    INFO = "info"
    INSECURE_BROKEN = "insecure-broken"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CertificateSecurityState:
    '''
    Details about the security state of the page certificate.
    '''
    #: Protocol name (e.g. "TLS 1.2" or "QUIC").
    protocol: str

    #: Key Exchange used by the connection, or the empty string if not applicable.
    key_exchange: str

    #: Cipher name.
    cipher: str

    #: Page certificate.
    certificate: typing.List[str]

    #: Certificate subject name.
    subject_name: str

    #: Name of the issuing CA.
    issuer: str

    #: Certificate valid from date.
    valid_from: network.TimeSinceEpoch

    #: Certificate valid to (expiration) date
    valid_to: network.TimeSinceEpoch

    #: True if the certificate uses a weak signature algorithm.
    certificate_has_weak_signature: bool

    #: True if the certificate has a SHA1 signature in the chain.
    certificate_has_sha1_signature: bool

    #: True if modern SSL
    modern_ssl: bool

    #: True if the connection is using an obsolete SSL protocol.
    obsolete_ssl_protocol: bool

    #: True if the connection is using an obsolete SSL key exchange.
    obsolete_ssl_key_exchange: bool

    #: True if the connection is using an obsolete SSL cipher.
    obsolete_ssl_cipher: bool

    #: True if the connection is using an obsolete SSL signature.
    obsolete_ssl_signature: bool

    #: (EC)DH group used by the connection, if applicable.
    key_exchange_group: typing.Optional[str] = None

    #: TLS MAC. Note that AEAD ciphers do not have separate MACs.
    mac: typing.Optional[str] = None

    #: The highest priority network error code, if the certificate has an error.
    certificate_network_error: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['keyExchange'] = self.key_exchange
        json['cipher'] = self.cipher
        json['certificate'] = [i for i in self.certificate]
        json['subjectName'] = self.subject_name
        json['issuer'] = self.issuer
        json['validFrom'] = self.valid_from.to_json()
        json['validTo'] = self.valid_to.to_json()
        json['certificateHasWeakSignature'] = self.certificate_has_weak_signature
        json['certificateHasSha1Signature'] = self.certificate_has_sha1_signature
        json['modernSSL'] = self.modern_ssl
        json['obsoleteSslProtocol'] = self.obsolete_ssl_protocol
        json['obsoleteSslKeyExchange'] = self.obsolete_ssl_key_exchange
        json['obsoleteSslCipher'] = self.obsolete_ssl_cipher
        json['obsoleteSslSignature'] = self.obsolete_ssl_signature
        if self.key_exchange_group is not None:
            json['keyExchangeGroup'] = self.key_exchange_group
        if self.mac is not None:
            json['mac'] = self.mac
        if self.certificate_network_error is not None:
            json['certificateNetworkError'] = self.certificate_network_error
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            key_exchange=str(json['keyExchange']),
            cipher=str(json['cipher']),
            certificate=[str(i) for i in json['certificate']],
            subject_name=str(json['subjectName']),
            issuer=str(json['issuer']),
            valid_from=network.TimeSinceEpoch.from_json(json['validFrom']),
            valid_to=network.TimeSinceEpoch.from_json(json['validTo']),
            certificate_has_weak_signature=bool(json['certificateHasWeakSignature']),
            certificate_has_sha1_signature=bool(json['certificateHasSha1Signature']),
            modern_ssl=bool(json['modernSSL']),
            obsolete_ssl_protocol=bool(json['obsoleteSslProtocol']),
            obsolete_ssl_key_exchange=bool(json['obsoleteSslKeyExchange']),
            obsolete_ssl_cipher=bool(json['obsoleteSslCipher']),
            obsolete_ssl_signature=bool(json['obsoleteSslSignature']),
            key_exchange_group=str(json['keyExchangeGroup']) if 'keyExchangeGroup' in json else None,
            mac=str(json['mac']) if 'mac' in json else None,
            certificate_network_error=str(json['certificateNetworkError']) if 'certificateNetworkError' in json else None,
        )


class SafetyTipStatus(enum.Enum):
    BAD_REPUTATION = "badReputation"
    LOOKALIKE = "lookalike"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SafetyTipInfo:
    #: Describes whether the page triggers any safety tips or reputation warnings. Default is unknown.
    safety_tip_status: SafetyTipStatus

    #: The URL the safety tip suggested ("Did you mean?"). Only filled in for lookalike matches.
    safe_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['safetyTipStatus'] = self.safety_tip_status.to_json()
        if self.safe_url is not None:
            json['safeUrl'] = self.safe_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            safety_tip_status=SafetyTipStatus.from_json(json['safetyTipStatus']),
            safe_url=str(json['safeUrl']) if 'safeUrl' in json else None,
        )


@dataclass
class VisibleSecurityState:
    '''
    Security state information about the page.
    '''
    #: The security level of the page.
    security_state: SecurityState

    #: Array of security state issues ids.
    security_state_issue_ids: typing.List[str]

    #: Security state details about the page certificate.
    certificate_security_state: typing.Optional[CertificateSecurityState] = None

    #: The type of Safety Tip triggered on the page. Note that this field will be set even if the Safety Tip UI was not actually shown.
    safety_tip_info: typing.Optional[SafetyTipInfo] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['securityStateIssueIds'] = [i for i in self.security_state_issue_ids]
        if self.certificate_security_state is not None:
            json['certificateSecurityState'] = self.certificate_security_state.to_json()
        if self.safety_tip_info is not None:
            json['safetyTipInfo'] = self.safety_tip_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            security_state_issue_ids=[str(i) for i in json['securityStateIssueIds']],
            certificate_security_state=CertificateSecurityState.from_json(json['certificateSecurityState']) if 'certificateSecurityState' in json else None,
            safety_tip_info=SafetyTipInfo.from_json(json['safetyTipInfo']) if 'safetyTipInfo' in json else None,
        )


@dataclass
class SecurityStateExplanation:
    '''
    An explanation of an factor contributing to the security state.
    '''
    #: Security state representing the severity of the factor being explained.
    security_state: SecurityState

    #: Title describing the type of factor.
    title: str

    #: Short phrase describing the type of factor.
    summary: str

    #: Full text explanation of the factor.
    description: str

    #: The type of mixed content described by the explanation.
    mixed_content_type: MixedContentType

    #: Page certificate.
    certificate: typing.List[str]

    #: Recommendations to fix any issues.
    recommendations: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['securityState'] = self.security_state.to_json()
        json['title'] = self.title
        json['summary'] = self.summary
        json['description'] = self.description
        json['mixedContentType'] = self.mixed_content_type.to_json()
        json['certificate'] = [i for i in self.certificate]
        if self.recommendations is not None:
            json['recommendations'] = [i for i in self.recommendations]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            title=str(json['title']),
            summary=str(json['summary']),
            description=str(json['description']),
            mixed_content_type=MixedContentType.from_json(json['mixedContentType']),
            certificate=[str(i) for i in json['certificate']],
            recommendations=[str(i) for i in json['recommendations']] if 'recommendations' in json else None,
        )


@dataclass
class InsecureContentStatus:
    '''
    Information about insecure content on the page.
    '''
    #: Always false.
    ran_mixed_content: bool

    #: Always false.
    displayed_mixed_content: bool

    #: Always false.
    contained_mixed_form: bool

    #: Always false.
    ran_content_with_cert_errors: bool

    #: Always false.
    displayed_content_with_cert_errors: bool

    #: Always set to unknown.
    ran_insecure_content_style: SecurityState

    #: Always set to unknown.
    displayed_insecure_content_style: SecurityState

    def to_json(self):
        json = dict()
        json['ranMixedContent'] = self.ran_mixed_content
        json['displayedMixedContent'] = self.displayed_mixed_content
        json['containedMixedForm'] = self.contained_mixed_form
        json['ranContentWithCertErrors'] = self.ran_content_with_cert_errors
        json['displayedContentWithCertErrors'] = self.displayed_content_with_cert_errors
        json['ranInsecureContentStyle'] = self.ran_insecure_content_style.to_json()
        json['displayedInsecureContentStyle'] = self.displayed_insecure_content_style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            ran_mixed_content=bool(json['ranMixedContent']),
            displayed_mixed_content=bool(json['displayedMixedContent']),
            contained_mixed_form=bool(json['containedMixedForm']),
            ran_content_with_cert_errors=bool(json['ranContentWithCertErrors']),
            displayed_content_with_cert_errors=bool(json['displayedContentWithCertErrors']),
            ran_insecure_content_style=SecurityState.from_json(json['ranInsecureContentStyle']),
            displayed_insecure_content_style=SecurityState.from_json(json['displayedInsecureContentStyle']),
        )


class CertificateErrorAction(enum.Enum):
    '''
    The action to take when a certificate error occurs. continue will continue processing the
    request and cancel will cancel the request.
    '''
    CONTINUE = "continue"
    CANCEL = "cancel"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables tracking security state changes.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.enable',
    }
    json = yield cmd_dict


def set_ignore_certificate_errors(
        ignore: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable whether all certificate errors should be ignored.

    :param ignore: If true, all certificate errors will be ignored.
    '''
    params: T_JSON_DICT = dict()
    params['ignore'] = ignore
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setIgnoreCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


def handle_certificate_error(
        event_id: int,
        action: CertificateErrorAction
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Handles a certificate error that fired a certificateError event.

    :param event_id: The ID of the event.
    :param action: The action to take on the certificate error.
    '''
    params: T_JSON_DICT = dict()
    params['eventId'] = event_id
    params['action'] = action.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.handleCertificateError',
        'params': params,
    }
    json = yield cmd_dict


def set_override_certificate_errors(
        override: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable overriding certificate errors. If enabled, all certificate error events need to
    be handled by the DevTools client and should be answered with ``handleCertificateError`` commands.

    :param override: If true, certificate errors will be overridden.
    '''
    params: T_JSON_DICT = dict()
    params['override'] = override
    cmd_dict: T_JSON_DICT = {
        'method': 'Security.setOverrideCertificateErrors',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Security.certificateError')
@dataclass
class CertificateError:
    '''
    There is a certificate error. If overriding certificate errors is enabled, then it should be
    handled with the ``handleCertificateError`` command. Note: this event does not fire if the
    certificate error has been allowed internally. Only one client per target should override
    certificate errors at the same time.
    '''
    #: The ID of the event.
    event_id: int
    #: The type of the error.
    error_type: str
    #: The url that was requested.
    request_url: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CertificateError:
        return cls(
            event_id=int(json['eventId']),
            error_type=str(json['errorType']),
            request_url=str(json['requestURL'])
        )


@event_class('Security.visibleSecurityStateChanged')
@dataclass
class VisibleSecurityStateChanged:
    '''
    **EXPERIMENTAL**

    The security state of the page changed.
    '''
    #: Security state information about the page.
    visible_security_state: VisibleSecurityState

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> VisibleSecurityStateChanged:
        return cls(
            visible_security_state=VisibleSecurityState.from_json(json['visibleSecurityState'])
        )


@event_class('Security.securityStateChanged')
@dataclass
class SecurityStateChanged:
    '''
    The security state of the page changed. No longer being sent.
    '''
    #: Security state.
    security_state: SecurityState
    #: True if the page was loaded over cryptographic transport such as HTTPS.
    scheme_is_cryptographic: bool
    #: Previously a list of explanations for the security state. Now always
    #: empty.
    explanations: typing.List[SecurityStateExplanation]
    #: Information about insecure content on the page.
    insecure_content_status: InsecureContentStatus
    #: Overrides user-visible description of the state. Always omitted.
    summary: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SecurityStateChanged:
        return cls(
            security_state=SecurityState.from_json(json['securityState']),
            scheme_is_cryptographic=bool(json['schemeIsCryptographic']),
            explanations=[SecurityStateExplanation.from_json(i) for i in json['explanations']],
            insecure_content_status=InsecureContentStatus.from_json(json['insecureContentStatus']),
            summary=str(json['summary']) if 'summary' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\httpx\_main.py ===
from __future__ import annotations

import functools
import json
import sys
import typing

import click
import pygments.lexers
import pygments.util
import rich.console
import rich.markup
import rich.progress
import rich.syntax
import rich.table

from ._client import Client
from ._exceptions import RequestError
from ._models import Response
from ._status_codes import codes

if typing.TYPE_CHECKING:
    import httpcore  # pragma: no cover


def print_help() -> None:
    console = rich.console.Console()

    console.print("[bold]HTTPX :butterfly:", justify="center")
    console.print()
    console.print("A next generation HTTP client.", justify="center")
    console.print()
    console.print(
        "Usage: [bold]httpx[/bold] [cyan]<URL> [OPTIONS][/cyan] ", justify="left"
    )
    console.print()

    table = rich.table.Table.grid(padding=1, pad_edge=True)
    table.add_column("Parameter", no_wrap=True, justify="left", style="bold")
    table.add_column("Description")
    table.add_row(
        "-m, --method [cyan]METHOD",
        "Request method, such as GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD.\n"
        "[Default: GET, or POST if a request body is included]",
    )
    table.add_row(
        "-p, --params [cyan]<NAME VALUE> ...",
        "Query parameters to include in the request URL.",
    )
    table.add_row(
        "-c, --content [cyan]TEXT", "Byte content to include in the request body."
    )
    table.add_row(
        "-d, --data [cyan]<NAME VALUE> ...", "Form data to include in the request body."
    )
    table.add_row(
        "-f, --files [cyan]<NAME FILENAME> ...",
        "Form files to include in the request body.",
    )
    table.add_row("-j, --json [cyan]TEXT", "JSON data to include in the request body.")
    table.add_row(
        "-h, --headers [cyan]<NAME VALUE> ...",
        "Include additional HTTP headers in the request.",
    )
    table.add_row(
        "--cookies [cyan]<NAME VALUE> ...", "Cookies to include in the request."
    )
    table.add_row(
        "--auth [cyan]<USER PASS>",
        "Username and password to include in the request. Specify '-' for the password"
        " to use a password prompt. Note that using --verbose/-v will expose"
        " the Authorization header, including the password encoding"
        " in a trivially reversible format.",
    )

    table.add_row(
        "--proxy [cyan]URL",
        "Send the request via a proxy. Should be the URL giving the proxy address.",
    )

    table.add_row(
        "--timeout [cyan]FLOAT",
        "Timeout value to use for network operations, such as establishing the"
        " connection, reading some data, etc... [Default: 5.0]",
    )

    table.add_row("--follow-redirects", "Automatically follow redirects.")
    table.add_row("--no-verify", "Disable SSL verification.")
    table.add_row(
        "--http2", "Send the request using HTTP/2, if the remote server supports it."
    )

    table.add_row(
        "--download [cyan]FILE",
        "Save the response content as a file, rather than displaying it.",
    )

    table.add_row("-v, --verbose", "Verbose output. Show request as well as response.")
    table.add_row("--help", "Show this message and exit.")
    console.print(table)


def get_lexer_for_response(response: Response) -> str:
    content_type = response.headers.get("Content-Type")
    if content_type is not None:
        mime_type, _, _ = content_type.partition(";")
        try:
            return typing.cast(
                str, pygments.lexers.get_lexer_for_mimetype(mime_type.strip()).name
            )
        except pygments.util.ClassNotFound:  # pragma: no cover
            pass
    return ""  # pragma: no cover


def format_request_headers(request: httpcore.Request, http2: bool = False) -> str:
    version = "HTTP/2" if http2 else "HTTP/1.1"
    headers = [
        (name.lower() if http2 else name, value) for name, value in request.headers
    ]
    method = request.method.decode("ascii")
    target = request.url.target.decode("ascii")
    lines = [f"{method} {target} {version}"] + [
        f"{name.decode('ascii')}: {value.decode('ascii')}" for name, value in headers
    ]
    return "\n".join(lines)


def format_response_headers(
    http_version: bytes,
    status: int,
    reason_phrase: bytes | None,
    headers: list[tuple[bytes, bytes]],
) -> str:
    version = http_version.decode("ascii")
    reason = (
        codes.get_reason_phrase(status)
        if reason_phrase is None
        else reason_phrase.decode("ascii")
    )
    lines = [f"{version} {status} {reason}"] + [
        f"{name.decode('ascii')}: {value.decode('ascii')}" for name, value in headers
    ]
    return "\n".join(lines)


def print_request_headers(request: httpcore.Request, http2: bool = False) -> None:
    console = rich.console.Console()
    http_text = format_request_headers(request, http2=http2)
    syntax = rich.syntax.Syntax(http_text, "http", theme="ansi_dark", word_wrap=True)
    console.print(syntax)
    syntax = rich.syntax.Syntax("", "http", theme="ansi_dark", word_wrap=True)
    console.print(syntax)


def print_response_headers(
    http_version: bytes,
    status: int,
    reason_phrase: bytes | None,
    headers: list[tuple[bytes, bytes]],
) -> None:
    console = rich.console.Console()
    http_text = format_response_headers(http_version, status, reason_phrase, headers)
    syntax = rich.syntax.Syntax(http_text, "http", theme="ansi_dark", word_wrap=True)
    console.print(syntax)
    syntax = rich.syntax.Syntax("", "http", theme="ansi_dark", word_wrap=True)
    console.print(syntax)


def print_response(response: Response) -> None:
    console = rich.console.Console()
    lexer_name = get_lexer_for_response(response)
    if lexer_name:
        if lexer_name.lower() == "json":
            try:
                data = response.json()
                text = json.dumps(data, indent=4)
            except ValueError:  # pragma: no cover
                text = response.text
        else:
            text = response.text

        syntax = rich.syntax.Syntax(text, lexer_name, theme="ansi_dark", word_wrap=True)
        console.print(syntax)
    else:
        console.print(f"<{len(response.content)} bytes of binary data>")


_PCTRTT = typing.Tuple[typing.Tuple[str, str], ...]
_PCTRTTT = typing.Tuple[_PCTRTT, ...]
_PeerCertRetDictType = typing.Dict[str, typing.Union[str, _PCTRTTT, _PCTRTT]]


def format_certificate(cert: _PeerCertRetDictType) -> str:  # pragma: no cover
    lines = []
    for key, value in cert.items():
        if isinstance(value, (list, tuple)):
            lines.append(f"*   {key}:")
            for item in value:
                if key in ("subject", "issuer"):
                    for sub_item in item:
                        lines.append(f"*     {sub_item[0]}: {sub_item[1]!r}")
                elif isinstance(item, tuple) and len(item) == 2:
                    lines.append(f"*     {item[0]}: {item[1]!r}")
                else:
                    lines.append(f"*     {item!r}")
        else:
            lines.append(f"*   {key}: {value!r}")
    return "\n".join(lines)


def trace(
    name: str, info: typing.Mapping[str, typing.Any], verbose: bool = False
) -> None:
    console = rich.console.Console()
    if name == "connection.connect_tcp.started" and verbose:
        host = info["host"]
        console.print(f"* Connecting to {host!r}")
    elif name == "connection.connect_tcp.complete" and verbose:
        stream = info["return_value"]
        server_addr = stream.get_extra_info("server_addr")
        console.print(f"* Connected to {server_addr[0]!r} on port {server_addr[1]}")
    elif name == "connection.start_tls.complete" and verbose:  # pragma: no cover
        stream = info["return_value"]
        ssl_object = stream.get_extra_info("ssl_object")
        version = ssl_object.version()
        cipher = ssl_object.cipher()
        server_cert = ssl_object.getpeercert()
        alpn = ssl_object.selected_alpn_protocol()
        console.print(f"* SSL established using {version!r} / {cipher[0]!r}")
        console.print(f"* Selected ALPN protocol: {alpn!r}")
        if server_cert:
            console.print("* Server certificate:")
            console.print(format_certificate(server_cert))
    elif name == "http11.send_request_headers.started" and verbose:
        request = info["request"]
        print_request_headers(request, http2=False)
    elif name == "http2.send_request_headers.started" and verbose:  # pragma: no cover
        request = info["request"]
        print_request_headers(request, http2=True)
    elif name == "http11.receive_response_headers.complete":
        http_version, status, reason_phrase, headers = info["return_value"]
        print_response_headers(http_version, status, reason_phrase, headers)
    elif name == "http2.receive_response_headers.complete":  # pragma: no cover
        status, headers = info["return_value"]
        http_version = b"HTTP/2"
        reason_phrase = None
        print_response_headers(http_version, status, reason_phrase, headers)


def download_response(response: Response, download: typing.BinaryIO) -> None:
    console = rich.console.Console()
    console.print()
    content_length = response.headers.get("Content-Length")
    with rich.progress.Progress(
        "[progress.description]{task.description}",
        "[progress.percentage]{task.percentage:>3.0f}%",
        rich.progress.BarColumn(bar_width=None),
        rich.progress.DownloadColumn(),
        rich.progress.TransferSpeedColumn(),
    ) as progress:
        description = f"Downloading [bold]{rich.markup.escape(download.name)}"
        download_task = progress.add_task(
            description,
            total=int(content_length or 0),
            start=content_length is not None,
        )
        for chunk in response.iter_bytes():
            download.write(chunk)
            progress.update(download_task, completed=response.num_bytes_downloaded)


def validate_json(
    ctx: click.Context,
    param: click.Option | click.Parameter,
    value: typing.Any,
) -> typing.Any:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:  # pragma: no cover
        raise click.BadParameter("Not valid JSON")


def validate_auth(
    ctx: click.Context,
    param: click.Option | click.Parameter,
    value: typing.Any,
) -> typing.Any:
    if value == (None, None):
        return None

    username, password = value
    if password == "-":  # pragma: no cover
        password = click.prompt("Password", hide_input=True)
    return (username, password)


def handle_help(
    ctx: click.Context,
    param: click.Option | click.Parameter,
    value: typing.Any,
) -> None:
    if not value or ctx.resilient_parsing:
        return

    print_help()
    ctx.exit()


@click.command(add_help_option=False)
@click.argument("url", type=str)
@click.option(
    "--method",
    "-m",
    "method",
    type=str,
    help=(
        "Request method, such as GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD. "
        "[Default: GET, or POST if a request body is included]"
    ),
)
@click.option(
    "--params",
    "-p",
    "params",
    type=(str, str),
    multiple=True,
    help="Query parameters to include in the request URL.",
)
@click.option(
    "--content",
    "-c",
    "content",
    type=str,
    help="Byte content to include in the request body.",
)
@click.option(
    "--data",
    "-d",
    "data",
    type=(str, str),
    multiple=True,
    help="Form data to include in the request body.",
)
@click.option(
    "--files",
    "-f",
    "files",
    type=(str, click.File(mode="rb")),
    multiple=True,
    help="Form files to include in the request body.",
)
@click.option(
    "--json",
    "-j",
    "json",
    type=str,
    callback=validate_json,
    help="JSON data to include in the request body.",
)
@click.option(
    "--headers",
    "-h",
    "headers",
    type=(str, str),
    multiple=True,
    help="Include additional HTTP headers in the request.",
)
@click.option(
    "--cookies",
    "cookies",
    type=(str, str),
    multiple=True,
    help="Cookies to include in the request.",
)
@click.option(
    "--auth",
    "auth",
    type=(str, str),
    default=(None, None),
    callback=validate_auth,
    help=(
        "Username and password to include in the request. "
        "Specify '-' for the password to use a password prompt. "
        "Note that using --verbose/-v will expose the Authorization header, "
        "including the password encoding in a trivially reversible format."
    ),
)
@click.option(
    "--proxy",
    "proxy",
    type=str,
    default=None,
    help="Send the request via a proxy. Should be the URL giving the proxy address.",
)
@click.option(
    "--timeout",
    "timeout",
    type=float,
    default=5.0,
    help=(
        "Timeout value to use for network operations, such as establishing the "
        "connection, reading some data, etc... [Default: 5.0]"
    ),
)
@click.option(
    "--follow-redirects",
    "follow_redirects",
    is_flag=True,
    default=False,
    help="Automatically follow redirects.",
)
@click.option(
    "--no-verify",
    "verify",
    is_flag=True,
    default=True,
    help="Disable SSL verification.",
)
@click.option(
    "--http2",
    "http2",
    type=bool,
    is_flag=True,
    default=False,
    help="Send the request using HTTP/2, if the remote server supports it.",
)
@click.option(
    "--download",
    type=click.File("wb"),
    help="Save the response content as a file, rather than displaying it.",
)
@click.option(
    "--verbose",
    "-v",
    type=bool,
    is_flag=True,
    default=False,
    help="Verbose. Show request as well as response.",
)
@click.option(
    "--help",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=handle_help,
    help="Show this message and exit.",
)
def main(
    url: str,
    method: str,
    params: list[tuple[str, str]],
    content: str,
    data: list[tuple[str, str]],
    files: list[tuple[str, click.File]],
    json: str,
    headers: list[tuple[str, str]],
    cookies: list[tuple[str, str]],
    auth: tuple[str, str] | None,
    proxy: str,
    timeout: float,
    follow_redirects: bool,
    verify: bool,
    http2: bool,
    download: typing.BinaryIO | None,
    verbose: bool,
) -> None:
    """
    An HTTP command line client.
    Sends a request and displays the response.
    """
    if not method:
        method = "POST" if content or data or files or json else "GET"

    try:
        with Client(proxy=proxy, timeout=timeout, http2=http2, verify=verify) as client:
            with client.stream(
                method,
                url,
                params=list(params),
                content=content,
                data=dict(data),
                files=files,  # type: ignore
                json=json,
                headers=headers,
                cookies=dict(cookies),
                auth=auth,
                follow_redirects=follow_redirects,
                extensions={"trace": functools.partial(trace, verbose=verbose)},
            ) as response:
                if download is not None:
                    download_response(response, download)
                else:
                    response.read()
                    if response.content:
                        print_response(response)

    except RequestError as exc:
        console = rich.console.Console()
        console.print(f"[red]{type(exc).__name__}[/red]: {exc}")
        sys.exit(1)

    sys.exit(0 if response.is_success else 1)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\experimental_pass_through\adapters\transformation.py ===
import json
from typing import Any, AsyncIterator, List, Literal, Optional, Tuple, Union, cast

from openai.types.chat.chat_completion_chunk import Choice as OpenAIStreamingChoice

from litellm.types.llms.anthropic import (
    AllAnthropicToolsValues,
    AnthopicMessagesAssistantMessageParam,
    AnthropicFinishReason,
    AnthropicMessagesRequest,
    AnthropicMessagesToolChoice,
    AnthropicMessagesUserMessageParam,
    AnthropicResponseContentBlockText,
    AnthropicResponseContentBlockToolUse,
    ContentBlockDelta,
    ContentJsonBlockDelta,
    ContentTextBlockDelta,
    MessageBlockDelta,
    MessageDelta,
    UsageDelta,
)
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
    AnthropicUsage,
)
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionAssistantToolCall,
    ChatCompletionImageObject,
    ChatCompletionImageUrlObject,
    ChatCompletionRequest,
    ChatCompletionSystemMessage,
    ChatCompletionTextObject,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolChoiceFunctionParam,
    ChatCompletionToolChoiceObjectParam,
    ChatCompletionToolChoiceValues,
    ChatCompletionToolMessage,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    ChatCompletionUserMessage,
)
from litellm.types.utils import Choices, ModelResponse, Usage

from .streaming_iterator import AnthropicStreamWrapper


class AnthropicAdapter:
    def __init__(self) -> None:
        pass

    def translate_completion_input_params(
        self, kwargs
    ) -> Optional[ChatCompletionRequest]:
        """
        - translate params, where needed
        - pass rest, as is
        """

        #########################################################
        # Validate required params
        #########################################################
        model = kwargs.pop("model")
        messages = kwargs.pop("messages")
        if not model:
            raise ValueError(
                "Bad Request: model is required for Anthropic Messages Request"
            )
        if not messages:
            raise ValueError(
                "Bad Request: messages is required for Anthropic Messages Request"
            )

        #########################################################
        # Created Typed Request Body
        #########################################################
        request_body = AnthropicMessagesRequest(
            model=model, messages=messages, **kwargs
        )

        translated_body = (
            LiteLLMAnthropicMessagesAdapter().translate_anthropic_to_openai(
                anthropic_message_request=request_body
            )
        )

        return translated_body

    def translate_completion_output_params(
        self, response: ModelResponse
    ) -> Optional[AnthropicMessagesResponse]:

        return LiteLLMAnthropicMessagesAdapter().translate_openai_response_to_anthropic(
            response=response
        )

    def translate_completion_output_params_streaming(
        self, completion_stream: Any
    ) -> Union[AsyncIterator[bytes], None]:
        anthropic_wrapper = AnthropicStreamWrapper(completion_stream=completion_stream)
        # Return the SSE-wrapped version for proper event formatting
        return anthropic_wrapper.async_anthropic_sse_wrapper()


class LiteLLMAnthropicMessagesAdapter:
    def __init__(self):
        pass

    ### FOR [BETA] `/v1/messages` endpoint support

    def translatable_anthropic_params(self) -> List:
        """
        Which anthropic params, we need to translate to the openai format.
        """
        return ["messages", "metadata", "system", "tool_choice", "tools"]

    def translate_anthropic_messages_to_openai(  # noqa: PLR0915
        self,
        messages: List[
            Union[
                AnthropicMessagesUserMessageParam,
                AnthopicMessagesAssistantMessageParam,
            ]
        ],
    ) -> List:
        new_messages: List[AllMessageValues] = []
        for m in messages:
            user_message: Optional[ChatCompletionUserMessage] = None
            tool_message_list: List[ChatCompletionToolMessage] = []
            new_user_content_list: List[
                Union[ChatCompletionTextObject, ChatCompletionImageObject]
            ] = []
            ## USER MESSAGE ##
            if m["role"] == "user":
                ## translate user message
                message_content = m.get("content")
                if message_content and isinstance(message_content, str):
                    user_message = ChatCompletionUserMessage(
                        role="user", content=message_content
                    )
                elif message_content and isinstance(message_content, list):
                    for content in message_content:
                        if content.get("type") == "text":
                            text_obj = ChatCompletionTextObject(
                                type="text", text=content.get("text", "")
                            )
                            new_user_content_list.append(text_obj)
                        elif content.get("type") == "image":
                            image_url = ChatCompletionImageUrlObject(
                                url=f"data:{content.get('type', '')};base64,{content.get('source', '')}"
                            )
                            image_obj = ChatCompletionImageObject(
                                type="image_url", image_url=image_url
                            )

                            new_user_content_list.append(image_obj)
                        elif content.get("type") == "tool_result":
                            if "content" not in content:
                                tool_result = ChatCompletionToolMessage(
                                    role="tool",
                                    tool_call_id=content.get("tool_use_id", ""),
                                    content="",
                                )
                                tool_message_list.append(tool_result)
                            elif isinstance(content.get("content"), str):
                                tool_result = ChatCompletionToolMessage(
                                    role="tool",
                                    tool_call_id=content.get("tool_use_id", ""),
                                    content=str(content.get("content", "")),
                                )
                                tool_message_list.append(tool_result)
                            elif isinstance(content.get("content"), list):
                                for c in content.get("content", []):
                                    if isinstance(c, str):
                                        tool_result = ChatCompletionToolMessage(
                                            role="tool",
                                            tool_call_id=content.get("tool_use_id", ""),
                                            content=c,
                                        )
                                        tool_message_list.append(tool_result)
                                    elif isinstance(c, dict):
                                        if c.get("type") == "text":
                                            tool_result = ChatCompletionToolMessage(
                                                role="tool",
                                                tool_call_id=content.get(
                                                    "tool_use_id", ""
                                                ),
                                                content=c.get("text", ""),
                                            )
                                            tool_message_list.append(tool_result)
                                        elif c.get("type") == "image":
                                            image_str = f"data:{c.get('type', '')};base64,{c.get('source', '')}"
                                            tool_result = ChatCompletionToolMessage(
                                                role="tool",
                                                tool_call_id=content.get(
                                                    "tool_use_id", ""
                                                ),
                                                content=image_str,
                                            )
                                            tool_message_list.append(tool_result)

            if user_message is not None:
                new_messages.append(user_message)

            if len(new_user_content_list) > 0:
                new_messages.append({"role": "user", "content": new_user_content_list})  # type: ignore

            if len(tool_message_list) > 0:
                new_messages.extend(tool_message_list)

            ## ASSISTANT MESSAGE ##
            assistant_message_str: Optional[str] = None
            tool_calls: List[ChatCompletionAssistantToolCall] = []
            if m["role"] == "assistant":
                if isinstance(m.get("content"), str):
                    assistant_message_str = str(m.get("content", ""))
                elif isinstance(m.get("content"), list):
                    for content in m.get("content", []):
                        if isinstance(content, str):
                            assistant_message_str = str(content)
                        elif isinstance(content, dict):
                            if content.get("type") == "text":
                                if assistant_message_str is None:
                                    assistant_message_str = content.get("text", "")
                                else:
                                    assistant_message_str += content.get("text", "")
                            elif content.get("type") == "tool_use":
                                function_chunk = ChatCompletionToolCallFunctionChunk(
                                    name=content.get("name", ""),
                                    arguments=json.dumps(content.get("input", {})),
                                )

                                tool_calls.append(
                                    ChatCompletionAssistantToolCall(
                                        id=content.get("id", ""),
                                        type="function",
                                        function=function_chunk,
                                    )
                                )

            if assistant_message_str is not None or len(tool_calls) > 0:
                assistant_message = ChatCompletionAssistantMessage(
                    role="assistant",
                    content=assistant_message_str,
                )
                if len(tool_calls) > 0:
                    assistant_message["tool_calls"] = tool_calls
                new_messages.append(assistant_message)

        return new_messages

    def translate_anthropic_tool_choice_to_openai(
        self, tool_choice: AnthropicMessagesToolChoice
    ) -> ChatCompletionToolChoiceValues:
        if tool_choice["type"] == "any":
            return "required"
        elif tool_choice["type"] == "auto":
            return "auto"
        elif tool_choice["type"] == "tool":
            tc_function_param = ChatCompletionToolChoiceFunctionParam(
                name=tool_choice.get("name", "")
            )
            return ChatCompletionToolChoiceObjectParam(
                type="function", function=tc_function_param
            )
        else:
            raise ValueError(
                "Incompatible tool choice param submitted - {}".format(tool_choice)
            )

    def translate_anthropic_tools_to_openai(
        self, tools: List[AllAnthropicToolsValues]
    ) -> List[ChatCompletionToolParam]:
        new_tools: List[ChatCompletionToolParam] = []
        mapped_tool_params = ["name", "input_schema", "description"]
        for tool in tools:
            function_chunk = ChatCompletionToolParamFunctionChunk(
                name=tool["name"],
            )
            if "input_schema" in tool:
                function_chunk["parameters"] = tool["input_schema"]  # type: ignore
            if "description" in tool:
                function_chunk["description"] = tool["description"]  # type: ignore

            for k, v in tool.items():
                if k not in mapped_tool_params:  # pass additional computer kwargs
                    function_chunk.setdefault("parameters", {}).update({k: v})
            new_tools.append(
                ChatCompletionToolParam(type="function", function=function_chunk)
            )

        return new_tools

    def translate_anthropic_to_openai(
        self, anthropic_message_request: AnthropicMessagesRequest
    ) -> ChatCompletionRequest:
        """
        This is used by the beta Anthropic Adapter, for translating anthropic `/v1/messages` requests to the openai format.
        """
        new_messages: List[AllMessageValues] = []

        ## CONVERT ANTHROPIC MESSAGES TO OPENAI
        messages_list: List[
            Union[
                AnthropicMessagesUserMessageParam, AnthopicMessagesAssistantMessageParam
            ]
        ] = cast(
            List[
                Union[
                    AnthropicMessagesUserMessageParam,
                    AnthopicMessagesAssistantMessageParam,
                ]
            ],
            anthropic_message_request["messages"],
        )
        new_messages = self.translate_anthropic_messages_to_openai(
            messages=messages_list
        )
        ## ADD SYSTEM MESSAGE TO MESSAGES
        if "system" in anthropic_message_request:
            system_content = anthropic_message_request["system"]
            if system_content:
                new_messages.insert(
                    0,
                    ChatCompletionSystemMessage(role="system", content=system_content),
                )

        new_kwargs: ChatCompletionRequest = {
            "model": anthropic_message_request["model"],
            "messages": new_messages,
        }
        ## CONVERT METADATA (user_id)
        if "metadata" in anthropic_message_request:
            metadata = anthropic_message_request["metadata"]
            if metadata and "user_id" in metadata:
                new_kwargs["user"] = metadata["user_id"]

        # Pass litellm proxy specific metadata
        if "litellm_metadata" in anthropic_message_request:
            # metadata will be passed to litellm.acompletion(), it's a litellm_param
            new_kwargs["metadata"] = anthropic_message_request.pop("litellm_metadata")

        ## CONVERT TOOL CHOICE
        if "tool_choice" in anthropic_message_request:
            tool_choice = anthropic_message_request["tool_choice"]
            if tool_choice:
                new_kwargs["tool_choice"] = (
                    self.translate_anthropic_tool_choice_to_openai(
                        tool_choice=cast(AnthropicMessagesToolChoice, tool_choice)
                    )
                )
        ## CONVERT TOOLS
        if "tools" in anthropic_message_request:
            tools = anthropic_message_request["tools"]
            if tools:
                new_kwargs["tools"] = self.translate_anthropic_tools_to_openai(
                    tools=cast(List[AllAnthropicToolsValues], tools)
                )

        translatable_params = self.translatable_anthropic_params()
        for k, v in anthropic_message_request.items():
            if k not in translatable_params:  # pass remaining params as is
                new_kwargs[k] = v  # type: ignore

        return new_kwargs

    def _translate_openai_content_to_anthropic(
        self, choices: List[Choices]
    ) -> List[
        Union[AnthropicResponseContentBlockText, AnthropicResponseContentBlockToolUse]
    ]:
        new_content: List[
            Union[
                AnthropicResponseContentBlockText, AnthropicResponseContentBlockToolUse
            ]
        ] = []
        for choice in choices:
            if (
                choice.message.tool_calls is not None
                and len(choice.message.tool_calls) > 0
            ):
                for tool_call in choice.message.tool_calls:
                    new_content.append(
                        AnthropicResponseContentBlockToolUse(
                            type="tool_use",
                            id=tool_call.id,
                            name=tool_call.function.name or "",
                            input=json.loads(tool_call.function.arguments),
                        )
                    )
            elif choice.message.content is not None:
                new_content.append(
                    AnthropicResponseContentBlockText(
                        type="text", text=choice.message.content
                    )
                )

        return new_content

    def _translate_openai_finish_reason_to_anthropic(
        self, openai_finish_reason: str
    ) -> AnthropicFinishReason:
        if openai_finish_reason == "stop":
            return "end_turn"
        elif openai_finish_reason == "length":
            return "max_tokens"
        elif openai_finish_reason == "tool_calls":
            return "tool_use"
        return "end_turn"

    def translate_openai_response_to_anthropic(
        self, response: ModelResponse
    ) -> AnthropicMessagesResponse:
        ## translate content block
        anthropic_content = self._translate_openai_content_to_anthropic(choices=response.choices)  # type: ignore
        ## extract finish reason
        anthropic_finish_reason = self._translate_openai_finish_reason_to_anthropic(
            openai_finish_reason=response.choices[0].finish_reason  # type: ignore
        )
        # extract usage
        usage: Usage = getattr(response, "usage")
        anthropic_usage = AnthropicUsage(
            input_tokens=usage.prompt_tokens or 0,
            output_tokens=usage.completion_tokens or 0,
        )
        translated_obj = AnthropicMessagesResponse(
            id=response.id,
            type="message",
            role="assistant",
            model=response.model or "unknown-model",
            stop_sequence=None,
            usage=anthropic_usage,
            content=anthropic_content,  # type: ignore
            stop_reason=anthropic_finish_reason,
        )

        return translated_obj

    def _translate_streaming_openai_chunk_to_anthropic(
        self, choices: List[OpenAIStreamingChoice]
    ) -> Tuple[
        Literal["text_delta", "input_json_delta"],
        Union[ContentTextBlockDelta, ContentJsonBlockDelta],
    ]:
        text: str = ""
        partial_json: Optional[str] = None
        for choice in choices:
            if choice.delta.content is not None:
                text += choice.delta.content
            elif choice.delta.tool_calls is not None:
                partial_json = ""
                for tool in choice.delta.tool_calls:
                    if (
                        tool.function is not None
                        and tool.function.arguments is not None
                    ):
                        partial_json += tool.function.arguments

        if partial_json is not None:
            return "input_json_delta", ContentJsonBlockDelta(
                type="input_json_delta", partial_json=partial_json
            )
        else:
            return "text_delta", ContentTextBlockDelta(type="text_delta", text=text)

    def translate_streaming_openai_response_to_anthropic(
        self, response: ModelResponse
    ) -> Union[ContentBlockDelta, MessageBlockDelta]:
        ## base case - final chunk w/ finish reason
        if response.choices[0].finish_reason is not None:
            delta = MessageDelta(
                stop_reason=self._translate_openai_finish_reason_to_anthropic(
                    response.choices[0].finish_reason
                ),
            )
            if getattr(response, "usage", None) is not None:
                litellm_usage_chunk: Optional[Usage] = response.usage  # type: ignore
            elif (
                hasattr(response, "_hidden_params")
                and "usage" in response._hidden_params
            ):
                litellm_usage_chunk = response._hidden_params["usage"]
            else:
                litellm_usage_chunk = None
            if litellm_usage_chunk is not None:
                usage_delta = UsageDelta(
                    input_tokens=litellm_usage_chunk.prompt_tokens or 0,
                    output_tokens=litellm_usage_chunk.completion_tokens or 0,
                )
            else:
                usage_delta = UsageDelta(input_tokens=0, output_tokens=0)
            return MessageBlockDelta(
                type="message_delta", delta=delta, usage=usage_delta
            )
        (
            type_of_content,
            content_block_delta,
        ) = self._translate_streaming_openai_chunk_to_anthropic(
            choices=response.choices  # type: ignore
        )
        return ContentBlockDelta(
            type="content_block_delta",
            index=response.choices[0].index,
            delta=content_block_delta,
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\server\cli.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import json
import os
import re
import sys
from importlib.util import find_spec
from typing import Any, Union, Tuple, Dict

# debugpy.__main__ should have preloaded pydevd properly before importing this module.
# Otherwise, some stdlib modules above might have had imported threading before pydevd
# could perform the necessary detours in it.
assert "pydevd" in sys.modules
import pydevd

# Note: use the one bundled from pydevd so that it's invisible for the user.
from _pydevd_bundle import pydevd_runpy as runpy

import debugpy
import debugpy.server
from debugpy.common import log
from debugpy.server import api


TARGET = "<filename> | -m <module> | -c <code> | --pid <pid>"

HELP = """debugpy {0}
See https://aka.ms/debugpy for documentation.

Usage: debugpy --listen | --connect
               [<host>:]<port>
               [--wait-for-client]
               [--configure-<name> <value>]...
               [--log-to <path>] [--log-to-stderr]
               {1}
               [<arg>]...
""".format(
    debugpy.__version__, TARGET
)


class Options(object):
    mode = None
    address: Union[Tuple[str, int], None] = None
    log_to = None
    log_to_stderr = False
    target: Union[str, None] = None
    target_kind: Union[str, None] = None
    wait_for_client = False
    adapter_access_token = None
    config: Dict[str, Any] = {}


options = Options()
options.config = {"qt": "none", "subProcess": True}


def in_range(parser, start, stop):
    def parse(s):
        n = parser(s)
        if start is not None and n < start:
            raise ValueError("must be >= {0}".format(start))
        if stop is not None and n >= stop:
            raise ValueError("must be < {0}".format(stop))
        return n

    return parse


pid = in_range(int, 0, None)


def print_help_and_exit(switch, it):
    print(HELP, file=sys.stderr)
    sys.exit(0)


def print_version_and_exit(switch, it):
    print(debugpy.__version__)
    sys.exit(0)


def set_arg(varname, parser=(lambda x: x)):
    def do(arg, it):
        value = parser(next(it))
        setattr(options, varname, value)

    return do


def set_const(varname, value):
    def do(arg, it):
        setattr(options, varname, value)

    return do


def set_address(mode):
    def do(arg, it):
        if options.address is not None:
            raise ValueError("--listen and --connect are mutually exclusive")

        # It's either host:port, or just port.
        value = next(it)
        host, sep, port = value.partition(":")
        if not sep:
            host = "127.0.0.1"
            port = value
        try:
            port = int(port)
        except Exception:
            port = -1
        if not (0 <= port < 2**16):
            raise ValueError("invalid port number")

        options.mode = mode
        options.address = (host, port)

    return do


def set_config(arg, it):
    prefix = "--configure-"
    assert arg.startswith(prefix)
    name = arg[len(prefix) :]
    value = next(it)

    if name not in options.config:
        raise ValueError("unknown property {0!r}".format(name))

    expected_type = type(options.config[name])
    try:
        if expected_type is bool:
            value = {"true": True, "false": False}[value.lower()]
        else:
            value = expected_type(value)
    except Exception:
        raise ValueError("{0!r} must be a {1}".format(name, expected_type.__name__))

    options.config[name] = value


def set_target(kind: str, parser=(lambda x: x), positional=False):
    def do(arg, it):
        options.target_kind = kind
        target = parser(arg if positional else next(it))

        if isinstance(target, bytes):
            # target may be the code, so, try some additional encodings...
            try:
                target = target.decode(sys.getfilesystemencoding())
            except UnicodeDecodeError:
                try:
                    target = target.decode("utf-8")
                except UnicodeDecodeError:
                    import locale

                    target = target.decode(locale.getpreferredencoding(False))

        options.target = target

    return do


# fmt: off
switches = [
    # Switch                    Placeholder         Action
    # ======                    ===========         ======

    # Switches that are documented for use by end users.
    ("-(\\?|h|-help)",          None,               print_help_and_exit),
    ("-(V|-version)",           None,               print_version_and_exit),
    ("--log-to" ,               "<path>",           set_arg("log_to")),
    ("--log-to-stderr",         None,               set_const("log_to_stderr", True)),
    ("--listen",                "<address>",        set_address("listen")),
    ("--connect",               "<address>",        set_address("connect")),
    ("--wait-for-client",       None,               set_const("wait_for_client", True)),
    ("--configure-.+",          "<value>",          set_config),

    # Switches that are used internally by the client or debugpy itself.
    ("--adapter-access-token",   "<token>",         set_arg("adapter_access_token")),

    # Targets. The "" entry corresponds to positional command line arguments,
    # i.e. the ones not preceded by any switch name.
    ("",                        "<filename>",       set_target("file", positional=True)),
    ("-m",                      "<module>",         set_target("module")),
    ("-c",                      "<code>",           set_target("code")),
    ("--pid",                   "<pid>",            set_target("pid", pid)),
]
# fmt: on


# Consume all the args from argv
def consume_argv():
    while len(sys.argv) >= 2:
        value = sys.argv[1]
        del sys.argv[1]
        yield value


# Consume all the args from a given list
def consume_args(args: list):
    if args is sys.argv:
        yield from consume_argv()
    else:
        while args:
            value = args[0]
            del args[0]
            yield value


# Parse the args from the command line, then from the environment.
# Args from the environment are only used if they are not already set from the command line.
def parse_args():

    # keep track of the switches we've seen so far
    seen = set()

    parse_args_from_command_line(seen)
    parse_args_from_environment(seen)

    # if the target is not set, or is empty, this is an error
    if options.target is None or options.target == "":
        raise ValueError("missing target: " + TARGET)

    if options.mode is None:
        raise ValueError("either --listen or --connect is required")
    if options.adapter_access_token is not None and options.mode != "connect":
        raise ValueError("--adapter-access-token requires --connect")
    if options.target_kind == "pid" and options.wait_for_client:
        raise ValueError("--pid does not support --wait-for-client")

    assert options.target_kind is not None
    assert options.address is not None


def parse_args_from_command_line(seen: set):
    parse_args_helper(sys.argv, seen)


def parse_args_from_environment(seenFromCommandLine: set):
    args = os.environ.get("DEBUGPY_EXTRA_ARGV")
    if not args:
        return

    argsList = args.split()

    seenFromEnvironment = set()
    parse_args_helper(argsList, seenFromCommandLine, seenFromEnvironment, True)


def parse_args_helper(
    args: list,
    seenFromCommandLine: set,
    seenFromEnvironment: set = set(),
    isFromEnvironment=False,
):
    iterator = consume_args(args)

    while True:
        try:
            arg = next(iterator)
        except StopIteration:
            break

        switch = arg
        if not switch.startswith("-"):
            switch = ""
        for pattern, placeholder, action in switches:
            if re.match("^(" + pattern + ")$", switch):
                break
        else:
            raise ValueError("unrecognized switch " + switch)

        # if we're parsing from the command line, and we've already seen the switch on the command line, this is an error
        if not isFromEnvironment and switch in seenFromCommandLine:
            raise ValueError("duplicate switch on command line: " + switch)
        # if we're parsing from the environment, and we've already seen the switch in the environment, this is an error
        elif isFromEnvironment and switch in seenFromEnvironment:
            raise ValueError("duplicate switch from environment: " + switch)
        # if we're parsing from the environment, and we've already seen the switch on the command line, skip it, since command line takes precedence
        elif isFromEnvironment and switch in seenFromCommandLine:
            continue
        # otherwise, the switch is new, so add it to the appropriate set
        else:
            if isFromEnvironment:
                seenFromEnvironment.add(switch)
            else:
                seenFromCommandLine.add(switch)

        # process the switch, running the corresponding action
        try:
            action(arg, iterator)
        except StopIteration:
            assert placeholder is not None
            raise ValueError("{0}: missing {1}".format(switch, placeholder))
        except Exception as exc:
            raise ValueError("invalid {0} {1}: {2}".format(switch, placeholder, exc))

        # If we're parsing the command line, we're done after we've processed the target
        # Otherwise, we need to keep parsing until all args are consumed, since the target may be set from the command line
        # already, but there might be additional args in the environment that we want to process.
        if not isFromEnvironment and options.target is not None:
            break


def start_debugging(argv_0):
    # We need to set up sys.argv[0] before invoking either listen() or connect(),
    # because they use it to report the "process" event. Thus, we can't rely on
    # run_path() and run_module() doing that, even though they will eventually.
    sys.argv[0] = argv_0

    log.debug("sys.argv after patching: {0!r}", sys.argv)

    debugpy.configure(options.config)

    if os.environ.get("DEBUGPY_RUNNING", "false") != "true":
        if options.mode == "listen" and options.address is not None:
            debugpy.listen(options.address)
        elif options.mode == "connect" and options.address is not None:
            debugpy.connect(options.address, access_token=options.adapter_access_token)
        else:
            raise AssertionError(repr(options.mode))

        if options.wait_for_client:
            debugpy.wait_for_client()

    os.environ["DEBUGPY_RUNNING"] = "true"


def run_file():
    target = options.target
    start_debugging(target)

    # run_path has one difference with invoking Python from command-line:
    # if the target is a file (rather than a directory), it does not add its
    # parent directory to sys.path. Thus, importing other modules from the
    # same directory is broken unless sys.path is patched here.

    if target is not None and os.path.isfile(target):
        dir = os.path.dirname(target)
        sys.path.insert(0, dir)
    else:
        log.debug("Not a file: {0!r}", target)

    log.describe_environment("Pre-launch environment:")

    log.info("Running file {0!r}", target)
    runpy.run_path(target, run_name="__main__")


def run_module():
    # Add current directory to path, like Python itself does for -m. This must
    # be in place before trying to use find_spec below to resolve submodules.
    sys.path.insert(0, str(""))

    # We want to do the same thing that run_module() would do here, without
    # actually invoking it.
    argv_0 = sys.argv[0]
    try:
        spec = None if options.target is None else find_spec(options.target)
        if spec is not None:
            argv_0 = spec.origin
    except Exception:
        log.swallow_exception("Error determining module path for sys.argv")

    start_debugging(argv_0)
    log.describe_environment("Pre-launch environment:")
    log.info("Running module {0!r}", options.target)

    # Docs say that runpy.run_module is equivalent to -m, but it's not actually
    # the case for packages - -m sets __name__ to "__main__", but run_module sets
    # it to "pkg.__main__". This breaks everything that uses the standard pattern
    # __name__ == "__main__" to detect being run as a CLI app. On the other hand,
    # runpy._run_module_as_main is a private function that actually implements -m.
    try:
        run_module_as_main = runpy._run_module_as_main
    except AttributeError:
        log.warning("runpy._run_module_as_main is missing, falling back to run_module.")
        runpy.run_module(options.target, alter_sys=True)
    else:
        run_module_as_main(options.target, alter_argv=True)


def run_code():
    if options.target is not None:
        # Add current directory to path, like Python itself does for -c.
        sys.path.insert(0, str(""))
        code = compile(options.target, str("<string>"), str("exec"))

        start_debugging(str("-c"))

        log.describe_environment("Pre-launch environment:")
        log.info("Running code:\n\n{0}", options.target)

        eval(code, {})
    else:
        log.error("No target to run.")


def attach_to_pid():
    pid = options.target
    log.info("Attaching to process with PID={0}", pid)

    encode = lambda s: list(bytearray(s.encode("utf-8"))) if s is not None else None

    script_dir = os.path.dirname(debugpy.server.__file__)
    assert os.path.exists(script_dir)
    script_dir = encode(script_dir)

    setup = {
        "mode": options.mode,
        "address": options.address,
        "wait_for_client": options.wait_for_client,
        "log_to": options.log_to,
        "adapter_access_token": options.adapter_access_token,
    }
    setup = encode(json.dumps(setup))

    python_code = """
import codecs;
import json;
import sys;

decode = lambda s: codecs.utf_8_decode(bytearray(s))[0] if s is not None else None;

script_dir = decode({script_dir});
setup = json.loads(decode({setup}));

sys.path.insert(0, script_dir);
import attach_pid_injected;
del sys.path[0];

attach_pid_injected.attach(setup);
"""
    python_code = (
        python_code.replace("\r", "")
        .replace("\n", "")
        .format(script_dir=script_dir, setup=setup)
    )
    log.info("Code to be injected: \n{0}", python_code.replace(";", ";\n"))

    # pydevd restriction on characters in injected code.
    assert not (
        {'"', "'", "\r", "\n"} & set(python_code)
    ), "Injected code should not contain any single quotes, double quotes, or newlines."

    pydevd_attach_to_process_path = os.path.join(
        os.path.dirname(pydevd.__file__), "pydevd_attach_to_process"
    )

    assert os.path.exists(pydevd_attach_to_process_path)
    sys.path.append(pydevd_attach_to_process_path)

    try:
        import add_code_to_python_process  # noqa

        log.info("Injecting code into process with PID={0} ...", pid)
        add_code_to_python_process.run_python_code(
            pid,
            python_code,
            connect_debugger_tracing=True,
            show_debug_info=int(os.getenv("DEBUGPY_ATTACH_BY_PID_DEBUG_INFO", "0")),
        )
    except Exception:
        log.reraise_exception("Code injection into PID={0} failed:", pid)
    log.info("Code injection into PID={0} completed.", pid)


def main():
    original_argv = list(sys.argv)
    try:
        parse_args()
    except Exception as exc:
        print(str(HELP) + str("\nError: ") + str(exc), file=sys.stderr)
        sys.exit(2)

    if options.log_to is not None:
        debugpy.log_to(options.log_to)
    if options.log_to_stderr:
        debugpy.log_to(sys.stderr)

    api.ensure_logging()

    log.info(
        str("sys.argv before parsing: {0!r}\n" "         after parsing:  {1!r}"),
        original_argv,
        sys.argv,
    )

    try:
        if options.target_kind is not None:
            run = {
                "file": run_file,
                "module": run_module,
                "code": run_code,
                "pid": attach_to_pid,
            }[options.target_kind]
            run()
    except SystemExit as exc:
        log.reraise_exception(
            "Debuggee exited via SystemExit: {0!r}", exc.code, level="debug"
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\fetch.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Fetch
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io
from . import network
from . import page


class RequestId(str):
    '''
    Unique request identifier.
    Note that this does not identify individual HTTP requests that are part of
    a network request.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RequestId:
        return cls(json)

    def __repr__(self):
        return 'RequestId({})'.format(super().__repr__())


class RequestStage(enum.Enum):
    '''
    Stages of the request to handle. Request will intercept before the request is
    sent. Response will intercept after the response is received (but before response
    body is received).
    '''
    REQUEST = "Request"
    RESPONSE = "Response"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RequestPattern:
    #: Wildcards (``'*'`` -> zero or more, ``'?'`` -> exactly one) are allowed. Escape character is
    #: backslash. Omitting is equivalent to ``"*"``.
    url_pattern: typing.Optional[str] = None

    #: If set, only requests for matching resource types will be intercepted.
    resource_type: typing.Optional[network.ResourceType] = None

    #: Stage at which to begin intercepting requests. Default is Request.
    request_stage: typing.Optional[RequestStage] = None

    def to_json(self):
        json = dict()
        if self.url_pattern is not None:
            json['urlPattern'] = self.url_pattern
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request_stage is not None:
            json['requestStage'] = self.request_stage.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url_pattern=str(json['urlPattern']) if 'urlPattern' in json else None,
            resource_type=network.ResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request_stage=RequestStage.from_json(json['requestStage']) if 'requestStage' in json else None,
        )


@dataclass
class HeaderEntry:
    '''
    Response HTTP header entry
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class AuthChallenge:
    '''
    Authorization challenge for HTTP status code 401 or 407.
    '''
    #: Origin of the challenger.
    origin: str

    #: The authentication scheme used, such as basic or digest
    scheme: str

    #: The realm of the challenge. May be empty.
    realm: str

    #: Source of the authentication challenge.
    source: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['scheme'] = self.scheme
        json['realm'] = self.realm
        if self.source is not None:
            json['source'] = self.source
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            scheme=str(json['scheme']),
            realm=str(json['realm']),
            source=str(json['source']) if 'source' in json else None,
        )


@dataclass
class AuthChallengeResponse:
    '''
    Response to an AuthChallenge.
    '''
    #: The decision on what to do in response to the authorization challenge.  Default means
    #: deferring to the default behavior of the net stack, which will likely either the Cancel
    #: authentication or display a popup dialog box.
    response: str

    #: The username to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    username: typing.Optional[str] = None

    #: The password to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    password: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['response'] = self.response
        if self.username is not None:
            json['username'] = self.username
        if self.password is not None:
            json['password'] = self.password
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            response=str(json['response']),
            username=str(json['username']) if 'username' in json else None,
            password=str(json['password']) if 'password' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the fetch domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.disable',
    }
    json = yield cmd_dict


def enable(
        patterns: typing.Optional[typing.List[RequestPattern]] = None,
        handle_auth_requests: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issuing of requestPaused events. A request will be paused until client
    calls one of failRequest, fulfillRequest or continueRequest/continueWithAuth.

    :param patterns: *(Optional)* If specified, only requests matching any of these patterns will produce fetchRequested event and will be paused until clients response. If not set, all requests will be affected.
    :param handle_auth_requests: *(Optional)* If true, authRequired events will be issued and requests will be paused expecting a call to continueWithAuth.
    '''
    params: T_JSON_DICT = dict()
    if patterns is not None:
        params['patterns'] = [i.to_json() for i in patterns]
    if handle_auth_requests is not None:
        params['handleAuthRequests'] = handle_auth_requests
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.enable',
        'params': params,
    }
    json = yield cmd_dict


def fail_request(
        request_id: RequestId,
        error_reason: network.ErrorReason
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Causes the request to fail with specified reason.

    :param request_id: An id the client received in requestPaused event.
    :param error_reason: Causes the request to fail with the given reason.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['errorReason'] = error_reason.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.failRequest',
        'params': params,
    }
    json = yield cmd_dict


def fulfill_request(
        request_id: RequestId,
        response_code: int,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None,
        body: typing.Optional[str] = None,
        response_phrase: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Provides response to the request.

    :param request_id: An id the client received in requestPaused event.
    :param response_code: An HTTP response code.
    :param response_headers: *(Optional)* Response headers.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    :param body: *(Optional)* A response body. If absent, original response body will be used if the request is intercepted at the response stage and empty body will be used if the request is intercepted at the request stage.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['responseCode'] = response_code
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    if body is not None:
        params['body'] = body
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.fulfillRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_request(
        request_id: RequestId,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        post_data: typing.Optional[str] = None,
        headers: typing.Optional[typing.List[HeaderEntry]] = None,
        intercept_response: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues the request, optionally modifying some of its parameters.

    :param request_id: An id the client received in requestPaused event.
    :param url: *(Optional)* If set, the request url will be modified in a way that's not observable by page.
    :param method: *(Optional)* If set, the request method is overridden.
    :param post_data: *(Optional)* If set, overrides the post data in the request.
    :param headers: *(Optional)* If set, overrides the request headers. Note that the overrides do not extend to subsequent redirect hops, if a redirect happens. Another override may be applied to a different request produced by a redirect.
    :param intercept_response: **(EXPERIMENTAL)** *(Optional)* If set, overrides response interception behavior for this request.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if url is not None:
        params['url'] = url
    if method is not None:
        params['method'] = method
    if post_data is not None:
        params['postData'] = post_data
    if headers is not None:
        params['headers'] = [i.to_json() for i in headers]
    if intercept_response is not None:
        params['interceptResponse'] = intercept_response
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_with_auth(
        request_id: RequestId,
        auth_challenge_response: AuthChallengeResponse
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues a request supplying authChallengeResponse following authRequired event.

    :param request_id: An id the client received in authRequired event.
    :param auth_challenge_response: Response to  with an authChallenge.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['authChallengeResponse'] = auth_challenge_response.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueWithAuth',
        'params': params,
    }
    json = yield cmd_dict


def continue_response(
        request_id: RequestId,
        response_code: typing.Optional[int] = None,
        response_phrase: typing.Optional[str] = None,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues loading of the paused response, optionally modifying the
    response headers. If either responseCode or headers are modified, all of them
    must be present.

    **EXPERIMENTAL**

    :param request_id: An id the client received in requestPaused event.
    :param response_code: *(Optional)* An HTTP response code. If absent, original response code will be used.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    :param response_headers: *(Optional)* Response headers. If absent, original response headers will be used.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if response_code is not None:
        params['responseCode'] = response_code
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueResponse',
        'params': params,
    }
    json = yield cmd_dict


def get_response_body(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Causes the body of the response to be received from the server and
    returned as a single string. May only be issued for a request that
    is paused in the Response stage and is mutually exclusive with
    takeResponseBodyForInterceptionAsStream. Calling other methods that
    affect the request or disabling fetch domain before body is received
    results in an undefined behavior.
    Note that the response body is not available for redirects. Requests
    paused in the _redirect received_ state may be differentiated by
    ``responseCode`` and presence of ``location`` response header, see
    comments to ``requestPaused`` for details.

    :param request_id: Identifier for the intercepted request to get body for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.getResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def take_response_body_as_stream(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,io.StreamHandle]:
    '''
    Returns a handle to the stream representing the response body.
    The request must be paused in the HeadersReceived stage.
    Note that after this command the request can't be continued
    as is -- client either needs to cancel it or to provide the
    response body.
    The stream only supports sequential read, IO.read will fail if the position
    is specified.
    This method is mutually exclusive with getResponseBody.
    Calling other methods that affect the request or disabling fetch
    domain before body is received results in an undefined behavior.

    :param request_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.takeResponseBodyAsStream',
        'params': params,
    }
    json = yield cmd_dict
    return io.StreamHandle.from_json(json['stream'])


@event_class('Fetch.requestPaused')
@dataclass
class RequestPaused:
    '''
    Issued when the domain is enabled and the request URL matches the
    specified filter. The request is paused until the client responds
    with one of continueRequest, failRequest or fulfillRequest.
    The stage of the request can be determined by presence of responseErrorReason
    and responseStatusCode -- the request is at the response stage if either
    of these fields is present and in the request stage otherwise.
    Redirect responses and subsequent requests are reported similarly to regular
    responses and requests. Redirect responses may be distinguished by the value
    of ``responseStatusCode`` (which is one of 301, 302, 303, 307, 308) along with
    presence of the ``location`` header. Requests resulting from a redirect will
    have ``redirectedRequestId`` field set.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Response error if intercepted at response stage.
    response_error_reason: typing.Optional[network.ErrorReason]
    #: Response code if intercepted at response stage.
    response_status_code: typing.Optional[int]
    #: Response status text if intercepted at response stage.
    response_status_text: typing.Optional[str]
    #: Response headers if intercepted at the response stage.
    response_headers: typing.Optional[typing.List[HeaderEntry]]
    #: If the intercepted request had a corresponding Network.requestWillBeSent event fired for it,
    #: then this networkId will be the same as the requestId present in the requestWillBeSent event.
    network_id: typing.Optional[network.RequestId]
    #: If the request is due to a redirect response from the server, the id of the request that
    #: has caused the redirect.
    redirected_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestPaused:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            response_error_reason=network.ErrorReason.from_json(json['responseErrorReason']) if 'responseErrorReason' in json else None,
            response_status_code=int(json['responseStatusCode']) if 'responseStatusCode' in json else None,
            response_status_text=str(json['responseStatusText']) if 'responseStatusText' in json else None,
            response_headers=[HeaderEntry.from_json(i) for i in json['responseHeaders']] if 'responseHeaders' in json else None,
            network_id=network.RequestId.from_json(json['networkId']) if 'networkId' in json else None,
            redirected_request_id=RequestId.from_json(json['redirectedRequestId']) if 'redirectedRequestId' in json else None
        )


@event_class('Fetch.authRequired')
@dataclass
class AuthRequired:
    '''
    Issued when the domain is enabled with handleAuthRequests set to true.
    The request is paused until client responds with continueWithAuth.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Details of the Authorization Challenge encountered.
    #: If this is set, client should respond with continueRequest that
    #: contains AuthChallengeResponse.
    auth_challenge: AuthChallenge

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AuthRequired:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            auth_challenge=AuthChallenge.from_json(json['authChallenge'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\fetch.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Fetch
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io
from . import network
from . import page


class RequestId(str):
    '''
    Unique request identifier.
    Note that this does not identify individual HTTP requests that are part of
    a network request.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RequestId:
        return cls(json)

    def __repr__(self):
        return 'RequestId({})'.format(super().__repr__())


class RequestStage(enum.Enum):
    '''
    Stages of the request to handle. Request will intercept before the request is
    sent. Response will intercept after the response is received (but before response
    body is received).
    '''
    REQUEST = "Request"
    RESPONSE = "Response"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RequestPattern:
    #: Wildcards (``'*'`` -> zero or more, ``'?'`` -> exactly one) are allowed. Escape character is
    #: backslash. Omitting is equivalent to ``"*"``.
    url_pattern: typing.Optional[str] = None

    #: If set, only requests for matching resource types will be intercepted.
    resource_type: typing.Optional[network.ResourceType] = None

    #: Stage at which to begin intercepting requests. Default is Request.
    request_stage: typing.Optional[RequestStage] = None

    def to_json(self):
        json = dict()
        if self.url_pattern is not None:
            json['urlPattern'] = self.url_pattern
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request_stage is not None:
            json['requestStage'] = self.request_stage.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url_pattern=str(json['urlPattern']) if 'urlPattern' in json else None,
            resource_type=network.ResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request_stage=RequestStage.from_json(json['requestStage']) if 'requestStage' in json else None,
        )


@dataclass
class HeaderEntry:
    '''
    Response HTTP header entry
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class AuthChallenge:
    '''
    Authorization challenge for HTTP status code 401 or 407.
    '''
    #: Origin of the challenger.
    origin: str

    #: The authentication scheme used, such as basic or digest
    scheme: str

    #: The realm of the challenge. May be empty.
    realm: str

    #: Source of the authentication challenge.
    source: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['scheme'] = self.scheme
        json['realm'] = self.realm
        if self.source is not None:
            json['source'] = self.source
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            scheme=str(json['scheme']),
            realm=str(json['realm']),
            source=str(json['source']) if 'source' in json else None,
        )


@dataclass
class AuthChallengeResponse:
    '''
    Response to an AuthChallenge.
    '''
    #: The decision on what to do in response to the authorization challenge.  Default means
    #: deferring to the default behavior of the net stack, which will likely either the Cancel
    #: authentication or display a popup dialog box.
    response: str

    #: The username to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    username: typing.Optional[str] = None

    #: The password to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    password: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['response'] = self.response
        if self.username is not None:
            json['username'] = self.username
        if self.password is not None:
            json['password'] = self.password
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            response=str(json['response']),
            username=str(json['username']) if 'username' in json else None,
            password=str(json['password']) if 'password' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the fetch domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.disable',
    }
    json = yield cmd_dict


def enable(
        patterns: typing.Optional[typing.List[RequestPattern]] = None,
        handle_auth_requests: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issuing of requestPaused events. A request will be paused until client
    calls one of failRequest, fulfillRequest or continueRequest/continueWithAuth.

    :param patterns: *(Optional)* If specified, only requests matching any of these patterns will produce fetchRequested event and will be paused until clients response. If not set, all requests will be affected.
    :param handle_auth_requests: *(Optional)* If true, authRequired events will be issued and requests will be paused expecting a call to continueWithAuth.
    '''
    params: T_JSON_DICT = dict()
    if patterns is not None:
        params['patterns'] = [i.to_json() for i in patterns]
    if handle_auth_requests is not None:
        params['handleAuthRequests'] = handle_auth_requests
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.enable',
        'params': params,
    }
    json = yield cmd_dict


def fail_request(
        request_id: RequestId,
        error_reason: network.ErrorReason
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Causes the request to fail with specified reason.

    :param request_id: An id the client received in requestPaused event.
    :param error_reason: Causes the request to fail with the given reason.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['errorReason'] = error_reason.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.failRequest',
        'params': params,
    }
    json = yield cmd_dict


def fulfill_request(
        request_id: RequestId,
        response_code: int,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None,
        body: typing.Optional[str] = None,
        response_phrase: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Provides response to the request.

    :param request_id: An id the client received in requestPaused event.
    :param response_code: An HTTP response code.
    :param response_headers: *(Optional)* Response headers.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    :param body: *(Optional)* A response body. If absent, original response body will be used if the request is intercepted at the response stage and empty body will be used if the request is intercepted at the request stage.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['responseCode'] = response_code
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    if body is not None:
        params['body'] = body
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.fulfillRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_request(
        request_id: RequestId,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        post_data: typing.Optional[str] = None,
        headers: typing.Optional[typing.List[HeaderEntry]] = None,
        intercept_response: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues the request, optionally modifying some of its parameters.

    :param request_id: An id the client received in requestPaused event.
    :param url: *(Optional)* If set, the request url will be modified in a way that's not observable by page.
    :param method: *(Optional)* If set, the request method is overridden.
    :param post_data: *(Optional)* If set, overrides the post data in the request.
    :param headers: *(Optional)* If set, overrides the request headers. Note that the overrides do not extend to subsequent redirect hops, if a redirect happens. Another override may be applied to a different request produced by a redirect.
    :param intercept_response: **(EXPERIMENTAL)** *(Optional)* If set, overrides response interception behavior for this request.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if url is not None:
        params['url'] = url
    if method is not None:
        params['method'] = method
    if post_data is not None:
        params['postData'] = post_data
    if headers is not None:
        params['headers'] = [i.to_json() for i in headers]
    if intercept_response is not None:
        params['interceptResponse'] = intercept_response
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_with_auth(
        request_id: RequestId,
        auth_challenge_response: AuthChallengeResponse
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues a request supplying authChallengeResponse following authRequired event.

    :param request_id: An id the client received in authRequired event.
    :param auth_challenge_response: Response to  with an authChallenge.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['authChallengeResponse'] = auth_challenge_response.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueWithAuth',
        'params': params,
    }
    json = yield cmd_dict


def continue_response(
        request_id: RequestId,
        response_code: typing.Optional[int] = None,
        response_phrase: typing.Optional[str] = None,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues loading of the paused response, optionally modifying the
    response headers. If either responseCode or headers are modified, all of them
    must be present.

    **EXPERIMENTAL**

    :param request_id: An id the client received in requestPaused event.
    :param response_code: *(Optional)* An HTTP response code. If absent, original response code will be used.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    :param response_headers: *(Optional)* Response headers. If absent, original response headers will be used.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if response_code is not None:
        params['responseCode'] = response_code
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueResponse',
        'params': params,
    }
    json = yield cmd_dict


def get_response_body(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Causes the body of the response to be received from the server and
    returned as a single string. May only be issued for a request that
    is paused in the Response stage and is mutually exclusive with
    takeResponseBodyForInterceptionAsStream. Calling other methods that
    affect the request or disabling fetch domain before body is received
    results in an undefined behavior.
    Note that the response body is not available for redirects. Requests
    paused in the _redirect received_ state may be differentiated by
    ``responseCode`` and presence of ``location`` response header, see
    comments to ``requestPaused`` for details.

    :param request_id: Identifier for the intercepted request to get body for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.getResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def take_response_body_as_stream(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,io.StreamHandle]:
    '''
    Returns a handle to the stream representing the response body.
    The request must be paused in the HeadersReceived stage.
    Note that after this command the request can't be continued
    as is -- client either needs to cancel it or to provide the
    response body.
    The stream only supports sequential read, IO.read will fail if the position
    is specified.
    This method is mutually exclusive with getResponseBody.
    Calling other methods that affect the request or disabling fetch
    domain before body is received results in an undefined behavior.

    :param request_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.takeResponseBodyAsStream',
        'params': params,
    }
    json = yield cmd_dict
    return io.StreamHandle.from_json(json['stream'])


@event_class('Fetch.requestPaused')
@dataclass
class RequestPaused:
    '''
    Issued when the domain is enabled and the request URL matches the
    specified filter. The request is paused until the client responds
    with one of continueRequest, failRequest or fulfillRequest.
    The stage of the request can be determined by presence of responseErrorReason
    and responseStatusCode -- the request is at the response stage if either
    of these fields is present and in the request stage otherwise.
    Redirect responses and subsequent requests are reported similarly to regular
    responses and requests. Redirect responses may be distinguished by the value
    of ``responseStatusCode`` (which is one of 301, 302, 303, 307, 308) along with
    presence of the ``location`` header. Requests resulting from a redirect will
    have ``redirectedRequestId`` field set.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Response error if intercepted at response stage.
    response_error_reason: typing.Optional[network.ErrorReason]
    #: Response code if intercepted at response stage.
    response_status_code: typing.Optional[int]
    #: Response status text if intercepted at response stage.
    response_status_text: typing.Optional[str]
    #: Response headers if intercepted at the response stage.
    response_headers: typing.Optional[typing.List[HeaderEntry]]
    #: If the intercepted request had a corresponding Network.requestWillBeSent event fired for it,
    #: then this networkId will be the same as the requestId present in the requestWillBeSent event.
    network_id: typing.Optional[network.RequestId]
    #: If the request is due to a redirect response from the server, the id of the request that
    #: has caused the redirect.
    redirected_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestPaused:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            response_error_reason=network.ErrorReason.from_json(json['responseErrorReason']) if 'responseErrorReason' in json else None,
            response_status_code=int(json['responseStatusCode']) if 'responseStatusCode' in json else None,
            response_status_text=str(json['responseStatusText']) if 'responseStatusText' in json else None,
            response_headers=[HeaderEntry.from_json(i) for i in json['responseHeaders']] if 'responseHeaders' in json else None,
            network_id=network.RequestId.from_json(json['networkId']) if 'networkId' in json else None,
            redirected_request_id=RequestId.from_json(json['redirectedRequestId']) if 'redirectedRequestId' in json else None
        )


@event_class('Fetch.authRequired')
@dataclass
class AuthRequired:
    '''
    Issued when the domain is enabled with handleAuthRequests set to true.
    The request is paused until client responds with continueWithAuth.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Details of the Authorization Challenge encountered.
    #: If this is set, client should respond with continueRequest that
    #: contains AuthChallengeResponse.
    auth_challenge: AuthChallenge

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AuthRequired:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            auth_challenge=AuthChallenge.from_json(json['authChallenge'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\fetch.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Fetch
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import io
from . import network
from . import page


class RequestId(str):
    '''
    Unique request identifier.
    Note that this does not identify individual HTTP requests that are part of
    a network request.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RequestId:
        return cls(json)

    def __repr__(self):
        return 'RequestId({})'.format(super().__repr__())


class RequestStage(enum.Enum):
    '''
    Stages of the request to handle. Request will intercept before the request is
    sent. Response will intercept after the response is received (but before response
    body is received).
    '''
    REQUEST = "Request"
    RESPONSE = "Response"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RequestPattern:
    #: Wildcards (``'*'`` -> zero or more, ``'?'`` -> exactly one) are allowed. Escape character is
    #: backslash. Omitting is equivalent to ``"*"``.
    url_pattern: typing.Optional[str] = None

    #: If set, only requests for matching resource types will be intercepted.
    resource_type: typing.Optional[network.ResourceType] = None

    #: Stage at which to begin intercepting requests. Default is Request.
    request_stage: typing.Optional[RequestStage] = None

    def to_json(self):
        json = dict()
        if self.url_pattern is not None:
            json['urlPattern'] = self.url_pattern
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request_stage is not None:
            json['requestStage'] = self.request_stage.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url_pattern=str(json['urlPattern']) if 'urlPattern' in json else None,
            resource_type=network.ResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request_stage=RequestStage.from_json(json['requestStage']) if 'requestStage' in json else None,
        )


@dataclass
class HeaderEntry:
    '''
    Response HTTP header entry
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class AuthChallenge:
    '''
    Authorization challenge for HTTP status code 401 or 407.
    '''
    #: Origin of the challenger.
    origin: str

    #: The authentication scheme used, such as basic or digest
    scheme: str

    #: The realm of the challenge. May be empty.
    realm: str

    #: Source of the authentication challenge.
    source: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['scheme'] = self.scheme
        json['realm'] = self.realm
        if self.source is not None:
            json['source'] = self.source
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            scheme=str(json['scheme']),
            realm=str(json['realm']),
            source=str(json['source']) if 'source' in json else None,
        )


@dataclass
class AuthChallengeResponse:
    '''
    Response to an AuthChallenge.
    '''
    #: The decision on what to do in response to the authorization challenge.  Default means
    #: deferring to the default behavior of the net stack, which will likely either the Cancel
    #: authentication or display a popup dialog box.
    response: str

    #: The username to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    username: typing.Optional[str] = None

    #: The password to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    password: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['response'] = self.response
        if self.username is not None:
            json['username'] = self.username
        if self.password is not None:
            json['password'] = self.password
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            response=str(json['response']),
            username=str(json['username']) if 'username' in json else None,
            password=str(json['password']) if 'password' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the fetch domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.disable',
    }
    json = yield cmd_dict


def enable(
        patterns: typing.Optional[typing.List[RequestPattern]] = None,
        handle_auth_requests: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issuing of requestPaused events. A request will be paused until client
    calls one of failRequest, fulfillRequest or continueRequest/continueWithAuth.

    :param patterns: *(Optional)* If specified, only requests matching any of these patterns will produce fetchRequested event and will be paused until clients response. If not set, all requests will be affected.
    :param handle_auth_requests: *(Optional)* If true, authRequired events will be issued and requests will be paused expecting a call to continueWithAuth.
    '''
    params: T_JSON_DICT = dict()
    if patterns is not None:
        params['patterns'] = [i.to_json() for i in patterns]
    if handle_auth_requests is not None:
        params['handleAuthRequests'] = handle_auth_requests
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.enable',
        'params': params,
    }
    json = yield cmd_dict


def fail_request(
        request_id: RequestId,
        error_reason: network.ErrorReason
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Causes the request to fail with specified reason.

    :param request_id: An id the client received in requestPaused event.
    :param error_reason: Causes the request to fail with the given reason.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['errorReason'] = error_reason.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.failRequest',
        'params': params,
    }
    json = yield cmd_dict


def fulfill_request(
        request_id: RequestId,
        response_code: int,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None,
        body: typing.Optional[str] = None,
        response_phrase: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Provides response to the request.

    :param request_id: An id the client received in requestPaused event.
    :param response_code: An HTTP response code.
    :param response_headers: *(Optional)* Response headers.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    :param body: *(Optional)* A response body. If absent, original response body will be used if the request is intercepted at the response stage and empty body will be used if the request is intercepted at the request stage.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['responseCode'] = response_code
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    if body is not None:
        params['body'] = body
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.fulfillRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_request(
        request_id: RequestId,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        post_data: typing.Optional[str] = None,
        headers: typing.Optional[typing.List[HeaderEntry]] = None,
        intercept_response: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues the request, optionally modifying some of its parameters.

    :param request_id: An id the client received in requestPaused event.
    :param url: *(Optional)* If set, the request url will be modified in a way that's not observable by page.
    :param method: *(Optional)* If set, the request method is overridden.
    :param post_data: *(Optional)* If set, overrides the post data in the request.
    :param headers: *(Optional)* If set, overrides the request headers. Note that the overrides do not extend to subsequent redirect hops, if a redirect happens. Another override may be applied to a different request produced by a redirect.
    :param intercept_response: **(EXPERIMENTAL)** *(Optional)* If set, overrides response interception behavior for this request.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if url is not None:
        params['url'] = url
    if method is not None:
        params['method'] = method
    if post_data is not None:
        params['postData'] = post_data
    if headers is not None:
        params['headers'] = [i.to_json() for i in headers]
    if intercept_response is not None:
        params['interceptResponse'] = intercept_response
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueRequest',
        'params': params,
    }
    json = yield cmd_dict


def continue_with_auth(
        request_id: RequestId,
        auth_challenge_response: AuthChallengeResponse
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues a request supplying authChallengeResponse following authRequired event.

    :param request_id: An id the client received in authRequired event.
    :param auth_challenge_response: Response to  with an authChallenge.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['authChallengeResponse'] = auth_challenge_response.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueWithAuth',
        'params': params,
    }
    json = yield cmd_dict


def continue_response(
        request_id: RequestId,
        response_code: typing.Optional[int] = None,
        response_phrase: typing.Optional[str] = None,
        response_headers: typing.Optional[typing.List[HeaderEntry]] = None,
        binary_response_headers: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues loading of the paused response, optionally modifying the
    response headers. If either responseCode or headers are modified, all of them
    must be present.

    **EXPERIMENTAL**

    :param request_id: An id the client received in requestPaused event.
    :param response_code: *(Optional)* An HTTP response code. If absent, original response code will be used.
    :param response_phrase: *(Optional)* A textual representation of responseCode. If absent, a standard phrase matching responseCode is used.
    :param response_headers: *(Optional)* Response headers. If absent, original response headers will be used.
    :param binary_response_headers: *(Optional)* Alternative way of specifying response headers as a \0-separated series of name: value pairs. Prefer the above method unless you need to represent some non-UTF8 values that can't be transmitted over the protocol as text.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    if response_code is not None:
        params['responseCode'] = response_code
    if response_phrase is not None:
        params['responsePhrase'] = response_phrase
    if response_headers is not None:
        params['responseHeaders'] = [i.to_json() for i in response_headers]
    if binary_response_headers is not None:
        params['binaryResponseHeaders'] = binary_response_headers
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.continueResponse',
        'params': params,
    }
    json = yield cmd_dict


def get_response_body(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Causes the body of the response to be received from the server and
    returned as a single string. May only be issued for a request that
    is paused in the Response stage and is mutually exclusive with
    takeResponseBodyForInterceptionAsStream. Calling other methods that
    affect the request or disabling fetch domain before body is received
    results in an undefined behavior.
    Note that the response body is not available for redirects. Requests
    paused in the _redirect received_ state may be differentiated by
    ``responseCode`` and presence of ``location`` response header, see
    comments to ``requestPaused`` for details.

    :param request_id: Identifier for the intercepted request to get body for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.getResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def take_response_body_as_stream(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,io.StreamHandle]:
    '''
    Returns a handle to the stream representing the response body.
    The request must be paused in the HeadersReceived stage.
    Note that after this command the request can't be continued
    as is -- client either needs to cancel it or to provide the
    response body.
    The stream only supports sequential read, IO.read will fail if the position
    is specified.
    This method is mutually exclusive with getResponseBody.
    Calling other methods that affect the request or disabling fetch
    domain before body is received results in an undefined behavior.

    :param request_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Fetch.takeResponseBodyAsStream',
        'params': params,
    }
    json = yield cmd_dict
    return io.StreamHandle.from_json(json['stream'])


@event_class('Fetch.requestPaused')
@dataclass
class RequestPaused:
    '''
    Issued when the domain is enabled and the request URL matches the
    specified filter. The request is paused until the client responds
    with one of continueRequest, failRequest or fulfillRequest.
    The stage of the request can be determined by presence of responseErrorReason
    and responseStatusCode -- the request is at the response stage if either
    of these fields is present and in the request stage otherwise.
    Redirect responses and subsequent requests are reported similarly to regular
    responses and requests. Redirect responses may be distinguished by the value
    of ``responseStatusCode`` (which is one of 301, 302, 303, 307, 308) along with
    presence of the ``location`` header. Requests resulting from a redirect will
    have ``redirectedRequestId`` field set.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Response error if intercepted at response stage.
    response_error_reason: typing.Optional[network.ErrorReason]
    #: Response code if intercepted at response stage.
    response_status_code: typing.Optional[int]
    #: Response status text if intercepted at response stage.
    response_status_text: typing.Optional[str]
    #: Response headers if intercepted at the response stage.
    response_headers: typing.Optional[typing.List[HeaderEntry]]
    #: If the intercepted request had a corresponding Network.requestWillBeSent event fired for it,
    #: then this networkId will be the same as the requestId present in the requestWillBeSent event.
    network_id: typing.Optional[network.RequestId]
    #: If the request is due to a redirect response from the server, the id of the request that
    #: has caused the redirect.
    redirected_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestPaused:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            response_error_reason=network.ErrorReason.from_json(json['responseErrorReason']) if 'responseErrorReason' in json else None,
            response_status_code=int(json['responseStatusCode']) if 'responseStatusCode' in json else None,
            response_status_text=str(json['responseStatusText']) if 'responseStatusText' in json else None,
            response_headers=[HeaderEntry.from_json(i) for i in json['responseHeaders']] if 'responseHeaders' in json else None,
            network_id=network.RequestId.from_json(json['networkId']) if 'networkId' in json else None,
            redirected_request_id=RequestId.from_json(json['redirectedRequestId']) if 'redirectedRequestId' in json else None
        )


@event_class('Fetch.authRequired')
@dataclass
class AuthRequired:
    '''
    Issued when the domain is enabled with handleAuthRequests set to true.
    The request is paused until client responds with continueWithAuth.
    '''
    #: Each request the page makes will have a unique id.
    request_id: RequestId
    #: The details of the request.
    request: network.Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: network.ResourceType
    #: Details of the Authorization Challenge encountered.
    #: If this is set, client should respond with continueRequest that
    #: contains AuthChallengeResponse.
    auth_challenge: AuthChallenge

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AuthRequired:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            request=network.Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=network.ResourceType.from_json(json['resourceType']),
            auth_challenge=AuthChallenge.from_json(json['authChallenge'])
        )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\ssl_.py ===
from __future__ import absolute_import

import hashlib
import hmac
import os
import sys
import warnings
from binascii import hexlify, unhexlify

from ..exceptions import (
    InsecurePlatformWarning,
    ProxySchemeUnsupported,
    SNIMissingWarning,
    SSLError,
)
from ..packages import six
from .url import BRACELESS_IPV6_ADDRZ_RE, IPV4_RE

SSLContext = None
SSLTransport = None
HAS_SNI = False
IS_PYOPENSSL = False
IS_SECURETRANSPORT = False
ALPN_PROTOCOLS = ["http/1.1"]

# Maps the length of a digest to a possible hash function producing this digest
HASHFUNC_MAP = {
    length: getattr(hashlib, algorithm, None)
    for length, algorithm in ((32, "md5"), (40, "sha1"), (64, "sha256"))
}


def _const_compare_digest_backport(a, b):
    """
    Compare two digests of equal length in constant time.

    The digests must be of type str/bytes.
    Returns True if the digests match, and False otherwise.
    """
    result = abs(len(a) - len(b))
    for left, right in zip(bytearray(a), bytearray(b)):
        result |= left ^ right
    return result == 0


_const_compare_digest = getattr(hmac, "compare_digest", _const_compare_digest_backport)

try:  # Test for SSL features
    import ssl
    from ssl import CERT_REQUIRED, wrap_socket
except ImportError:
    pass

try:
    from ssl import HAS_SNI  # Has SNI?
except ImportError:
    pass

try:
    from .ssltransport import SSLTransport
except ImportError:
    pass


try:  # Platform-specific: Python 3.6
    from ssl import PROTOCOL_TLS

    PROTOCOL_SSLv23 = PROTOCOL_TLS
except ImportError:
    try:
        from ssl import PROTOCOL_SSLv23 as PROTOCOL_TLS

        PROTOCOL_SSLv23 = PROTOCOL_TLS
    except ImportError:
        PROTOCOL_SSLv23 = PROTOCOL_TLS = 2

try:
    from ssl import PROTOCOL_TLS_CLIENT
except ImportError:
    PROTOCOL_TLS_CLIENT = PROTOCOL_TLS


try:
    from ssl import OP_NO_COMPRESSION, OP_NO_SSLv2, OP_NO_SSLv3
except ImportError:
    OP_NO_SSLv2, OP_NO_SSLv3 = 0x1000000, 0x2000000
    OP_NO_COMPRESSION = 0x20000


try:  # OP_NO_TICKET was added in Python 3.6
    from ssl import OP_NO_TICKET
except ImportError:
    OP_NO_TICKET = 0x4000


# A secure default.
# Sources for more information on TLS ciphers:
#
# - https://wiki.mozilla.org/Security/Server_Side_TLS
# - https://www.ssllabs.com/projects/best-practices/index.html
# - https://hynek.me/articles/hardening-your-web-servers-ssl-ciphers/
#
# The general intent is:
# - prefer cipher suites that offer perfect forward secrecy (DHE/ECDHE),
# - prefer ECDHE over DHE for better performance,
# - prefer any AES-GCM and ChaCha20 over any AES-CBC for better performance and
#   security,
# - prefer AES-GCM over ChaCha20 because hardware-accelerated AES is common,
# - disable NULL authentication, MD5 MACs, DSS, and other
#   insecure ciphers for security reasons.
# - NOTE: TLS 1.3 cipher suites are managed through a different interface
#   not exposed by CPython (yet!) and are enabled by default if they're available.
DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)

try:
    from ssl import SSLContext  # Modern SSL?
except ImportError:

    class SSLContext(object):  # Platform-specific: Python 2
        def __init__(self, protocol_version):
            self.protocol = protocol_version
            # Use default values from a real SSLContext
            self.check_hostname = False
            self.verify_mode = ssl.CERT_NONE
            self.ca_certs = None
            self.options = 0
            self.certfile = None
            self.keyfile = None
            self.ciphers = None

        def load_cert_chain(self, certfile, keyfile):
            self.certfile = certfile
            self.keyfile = keyfile

        def load_verify_locations(self, cafile=None, capath=None, cadata=None):
            self.ca_certs = cafile

            if capath is not None:
                raise SSLError("CA directories not supported in older Pythons")

            if cadata is not None:
                raise SSLError("CA data not supported in older Pythons")

        def set_ciphers(self, cipher_suite):
            self.ciphers = cipher_suite

        def wrap_socket(self, socket, server_hostname=None, server_side=False):
            warnings.warn(
                "A true SSLContext object is not available. This prevents "
                "urllib3 from configuring SSL appropriately and may cause "
                "certain SSL connections to fail. You can upgrade to a newer "
                "version of Python to solve this. For more information, see "
                "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
                "#ssl-warnings",
                InsecurePlatformWarning,
            )
            kwargs = {
                "keyfile": self.keyfile,
                "certfile": self.certfile,
                "ca_certs": self.ca_certs,
                "cert_reqs": self.verify_mode,
                "ssl_version": self.protocol,
                "server_side": server_side,
            }
            return wrap_socket(socket, ciphers=self.ciphers, **kwargs)


def assert_fingerprint(cert, fingerprint):
    """
    Checks if given fingerprint matches the supplied certificate.

    :param cert:
        Certificate as bytes object.
    :param fingerprint:
        Fingerprint as string of hexdigits, can be interspersed by colons.
    """

    fingerprint = fingerprint.replace(":", "").lower()
    digest_length = len(fingerprint)
    if digest_length not in HASHFUNC_MAP:
        raise SSLError("Fingerprint of invalid length: {0}".format(fingerprint))
    hashfunc = HASHFUNC_MAP.get(digest_length)
    if hashfunc is None:
        raise SSLError(
            "Hash function implementation unavailable for fingerprint length: {0}".format(
                digest_length
            )
        )

    # We need encode() here for py32; works on py2 and p33.
    fingerprint_bytes = unhexlify(fingerprint.encode())

    cert_digest = hashfunc(cert).digest()

    if not _const_compare_digest(cert_digest, fingerprint_bytes):
        raise SSLError(
            'Fingerprints did not match. Expected "{0}", got "{1}".'.format(
                fingerprint, hexlify(cert_digest)
            )
        )


def resolve_cert_reqs(candidate):
    """
    Resolves the argument to a numeric constant, which can be passed to
    the wrap_socket function/method from the ssl module.
    Defaults to :data:`ssl.CERT_REQUIRED`.
    If given a string it is assumed to be the name of the constant in the
    :mod:`ssl` module or its abbreviation.
    (So you can specify `REQUIRED` instead of `CERT_REQUIRED`.
    If it's neither `None` nor a string we assume it is already the numeric
    constant which can directly be passed to wrap_socket.
    """
    if candidate is None:
        return CERT_REQUIRED

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "CERT_" + candidate)
        return res

    return candidate


def resolve_ssl_version(candidate):
    """
    like resolve_cert_reqs
    """
    if candidate is None:
        return PROTOCOL_TLS

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "PROTOCOL_" + candidate)
        return res

    return candidate


def create_urllib3_context(
    ssl_version=None, cert_reqs=None, options=None, ciphers=None
):
    """All arguments have the same meaning as ``ssl_wrap_socket``.

    By default, this function does a lot of the same work that
    ``ssl.create_default_context`` does on Python 3.4+. It:

    - Disables SSLv2, SSLv3, and compression
    - Sets a restricted set of server ciphers

    If you wish to enable SSLv3, you can do::

        from pip._vendor.urllib3.util import ssl_
        context = ssl_.create_urllib3_context()
        context.options &= ~ssl_.OP_NO_SSLv3

    You can do the same to enable compression (substituting ``COMPRESSION``
    for ``SSLv3`` in the last line above).

    :param ssl_version:
        The desired protocol version to use. This will default to
        PROTOCOL_SSLv23 which will negotiate the highest protocol that both
        the server and your installation of OpenSSL support.
    :param cert_reqs:
        Whether to require the certificate verification. This defaults to
        ``ssl.CERT_REQUIRED``.
    :param options:
        Specific OpenSSL options. These default to ``ssl.OP_NO_SSLv2``,
        ``ssl.OP_NO_SSLv3``, ``ssl.OP_NO_COMPRESSION``, and ``ssl.OP_NO_TICKET``.
    :param ciphers:
        Which cipher suites to allow the server to select.
    :returns:
        Constructed SSLContext object with specified options
    :rtype: SSLContext
    """
    # PROTOCOL_TLS is deprecated in Python 3.10
    if not ssl_version or ssl_version == PROTOCOL_TLS:
        ssl_version = PROTOCOL_TLS_CLIENT

    context = SSLContext(ssl_version)

    context.set_ciphers(ciphers or DEFAULT_CIPHERS)

    # Setting the default here, as we may have no ssl module on import
    cert_reqs = ssl.CERT_REQUIRED if cert_reqs is None else cert_reqs

    if options is None:
        options = 0
        # SSLv2 is easily broken and is considered harmful and dangerous
        options |= OP_NO_SSLv2
        # SSLv3 has several problems and is now dangerous
        options |= OP_NO_SSLv3
        # Disable compression to prevent CRIME attacks for OpenSSL 1.0+
        # (issue #309)
        options |= OP_NO_COMPRESSION
        # TLSv1.2 only. Unless set explicitly, do not request tickets.
        # This may save some bandwidth on wire, and although the ticket is encrypted,
        # there is a risk associated with it being on wire,
        # if the server is not rotating its ticketing keys properly.
        options |= OP_NO_TICKET

    context.options |= options

    # Enable post-handshake authentication for TLS 1.3, see GH #1634. PHA is
    # necessary for conditional client cert authentication with TLS 1.3.
    # The attribute is None for OpenSSL <= 1.1.0 or does not exist in older
    # versions of Python.  We only enable on Python 3.7.4+ or if certificate
    # verification is enabled to work around Python issue #37428
    # See: https://bugs.python.org/issue37428
    if (cert_reqs == ssl.CERT_REQUIRED or sys.version_info >= (3, 7, 4)) and getattr(
        context, "post_handshake_auth", None
    ) is not None:
        context.post_handshake_auth = True

    def disable_check_hostname():
        if (
            getattr(context, "check_hostname", None) is not None
        ):  # Platform-specific: Python 3.2
            # We do our own verification, including fingerprints and alternative
            # hostnames. So disable it here
            context.check_hostname = False

    # The order of the below lines setting verify_mode and check_hostname
    # matter due to safe-guards SSLContext has to prevent an SSLContext with
    # check_hostname=True, verify_mode=NONE/OPTIONAL. This is made even more
    # complex because we don't know whether PROTOCOL_TLS_CLIENT will be used
    # or not so we don't know the initial state of the freshly created SSLContext.
    if cert_reqs == ssl.CERT_REQUIRED:
        context.verify_mode = cert_reqs
        disable_check_hostname()
    else:
        disable_check_hostname()
        context.verify_mode = cert_reqs

    # Enable logging of TLS session keys via defacto standard environment variable
    # 'SSLKEYLOGFILE', if the feature is available (Python 3.8+). Skip empty values.
    if hasattr(context, "keylog_filename"):
        sslkeylogfile = os.environ.get("SSLKEYLOGFILE")
        if sslkeylogfile:
            context.keylog_filename = sslkeylogfile

    return context


def ssl_wrap_socket(
    sock,
    keyfile=None,
    certfile=None,
    cert_reqs=None,
    ca_certs=None,
    server_hostname=None,
    ssl_version=None,
    ciphers=None,
    ssl_context=None,
    ca_cert_dir=None,
    key_password=None,
    ca_cert_data=None,
    tls_in_tls=False,
):
    """
    All arguments except for server_hostname, ssl_context, and ca_cert_dir have
    the same meaning as they do when using :func:`ssl.wrap_socket`.

    :param server_hostname:
        When SNI is supported, the expected hostname of the certificate
    :param ssl_context:
        A pre-made :class:`SSLContext` object. If none is provided, one will
        be created using :func:`create_urllib3_context`.
    :param ciphers:
        A string of ciphers we wish the client to support.
    :param ca_cert_dir:
        A directory containing CA certificates in multiple separate files, as
        supported by OpenSSL's -CApath flag or the capath argument to
        SSLContext.load_verify_locations().
    :param key_password:
        Optional password if the keyfile is encrypted.
    :param ca_cert_data:
        Optional string containing CA certificates in PEM format suitable for
        passing as the cadata parameter to SSLContext.load_verify_locations()
    :param tls_in_tls:
        Use SSLTransport to wrap the existing socket.
    """
    context = ssl_context
    if context is None:
        # Note: This branch of code and all the variables in it are no longer
        # used by urllib3 itself. We should consider deprecating and removing
        # this code.
        context = create_urllib3_context(ssl_version, cert_reqs, ciphers=ciphers)

    if ca_certs or ca_cert_dir or ca_cert_data:
        try:
            context.load_verify_locations(ca_certs, ca_cert_dir, ca_cert_data)
        except (IOError, OSError) as e:
            raise SSLError(e)

    elif ssl_context is None and hasattr(context, "load_default_certs"):
        # try to load OS default certs; works well on Windows (require Python3.4+)
        context.load_default_certs()

    # Attempt to detect if we get the goofy behavior of the
    # keyfile being encrypted and OpenSSL asking for the
    # passphrase via the terminal and instead error out.
    if keyfile and key_password is None and _is_key_file_encrypted(keyfile):
        raise SSLError("Client private key is encrypted, password is required")

    if certfile:
        if key_password is None:
            context.load_cert_chain(certfile, keyfile)
        else:
            context.load_cert_chain(certfile, keyfile, key_password)

    try:
        if hasattr(context, "set_alpn_protocols"):
            context.set_alpn_protocols(ALPN_PROTOCOLS)
    except NotImplementedError:  # Defensive: in CI, we always have set_alpn_protocols
        pass

    # If we detect server_hostname is an IP address then the SNI
    # extension should not be used according to RFC3546 Section 3.1
    use_sni_hostname = server_hostname and not is_ipaddress(server_hostname)
    # SecureTransport uses server_hostname in certificate verification.
    send_sni = (use_sni_hostname and HAS_SNI) or (
        IS_SECURETRANSPORT and server_hostname
    )
    # Do not warn the user if server_hostname is an invalid SNI hostname.
    if not HAS_SNI and use_sni_hostname:
        warnings.warn(
            "An HTTPS request has been made, but the SNI (Server Name "
            "Indication) extension to TLS is not available on this platform. "
            "This may cause the server to present an incorrect TLS "
            "certificate, which can cause validation failures. You can upgrade to "
            "a newer version of Python to solve this. For more information, see "
            "https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html"
            "#ssl-warnings",
            SNIMissingWarning,
        )

    if send_sni:
        ssl_sock = _ssl_wrap_socket_impl(
            sock, context, tls_in_tls, server_hostname=server_hostname
        )
    else:
        ssl_sock = _ssl_wrap_socket_impl(sock, context, tls_in_tls)
    return ssl_sock


def is_ipaddress(hostname):
    """Detects whether the hostname given is an IPv4 or IPv6 address.
    Also detects IPv6 addresses with Zone IDs.

    :param str hostname: Hostname to examine.
    :return: True if the hostname is an IP address, False otherwise.
    """
    if not six.PY2 and isinstance(hostname, bytes):
        # IDN A-label bytes are ASCII compatible.
        hostname = hostname.decode("ascii")
    return bool(IPV4_RE.match(hostname) or BRACELESS_IPV6_ADDRZ_RE.match(hostname))


def _is_key_file_encrypted(key_file):
    """Detects if a key file is encrypted or not."""
    with open(key_file, "r") as f:
        for line in f:
            # Look for Proc-Type: 4,ENCRYPTED
            if "ENCRYPTED" in line:
                return True

    return False


def _ssl_wrap_socket_impl(sock, ssl_context, tls_in_tls, server_hostname=None):
    if tls_in_tls:
        if not SSLTransport:
            # Import error, ssl is not available.
            raise ProxySchemeUnsupported(
                "TLS in TLS requires support for the 'ssl' module"
            )

        SSLTransport._validate_ssl_context_for_tls_in_tls(ssl_context)
        return SSLTransport(sock, ssl_context, server_hostname)

    if server_hostname:
        return ssl_context.wrap_socket(sock, server_hostname=server_hostname)
    else:
        return ssl_context.wrap_socket(sock)