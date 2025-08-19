
# === NexusCore/tools\exports\export_20250803_114325\combined_139.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\sgrepmdi.py ===
# SGrepMDI is by Gordon McMillan (gmcm@hypernet.com)
# It does basically what Find In Files does in MSVC with a couple enhancements.
# - It saves any directories in the app's ini file (if you want to get rid
# 	of them you'll have to edit the file)
# - "Directories" can be directories,
#  -	semicolon separated lists of "directories",
#  -	environment variables that evaluate to "directories",
#  -	registry path names that evaluate to "directories",
#  -	all of which is recursive, so you can mix them all up.
# - It is MDI, so you can 'nest' greps and return to earlier ones,
# 	(ie, have multiple results open at the same time)
# - Like FIF, double clicking a line opens an editor and takes you to the line.
# - You can highlight text, right click and start a new grep with the selected
# 	text as search pattern and same directories etc as before.
# - You can save grep parameters (so you don't lose your hardearned pattern)
# 	from File|Save
# - You can save grep results by right clicking in the result window.
# Hats off to Mark Hammond for providing an environment where I could cobble
# something like this together in a couple evenings!

import glob
import os
import re

import win32api
import win32con
import win32ui
from pywin.mfc import dialog, docview, window

from . import scriptutils


def getsubdirs(d):
    dlist = []
    flist = glob.glob(d + "\\*")
    for f in flist:
        if os.path.isdir(f):
            dlist.append(f)
            dlist += getsubdirs(f)
    return dlist


class dirpath:
    def __init__(self, str, recurse=0):
        dp = str.split(";")
        dirs = {}
        for d in dp:
            if os.path.isdir(d):
                d = d.lower()
                if d not in dirs:
                    dirs[d] = None
                    if recurse:
                        subdirs = getsubdirs(d)
                        for sd in subdirs:
                            sd = sd.lower()
                            if sd not in dirs:
                                dirs[sd] = None
            elif os.path.isfile(d):
                pass
            else:
                x = None
                if d in os.environ:
                    x = dirpath(os.environ[d])
                elif d[:5] == "HKEY_":
                    keystr = d.split("\\")
                    try:
                        root = eval("win32con." + keystr[0])
                    except:
                        win32ui.MessageBox(
                            "Can't interpret registry key name '%s'" % keystr[0]
                        )
                    try:
                        subkey = "\\".join(keystr[1:])
                        val = win32api.RegQueryValue(root, subkey)
                        if val:
                            x = dirpath(val)
                        else:
                            win32ui.MessageBox(
                                "Registry path '%s' did not return a path entry" % d
                            )
                    except:
                        win32ui.MessageBox(
                            "Can't interpret registry key value: %s" % keystr[1:]
                        )
                else:
                    win32ui.MessageBox("Directory '%s' not found" % d)
                if x:
                    for xd in x:
                        if xd not in dirs:
                            dirs[xd] = None
                            if recurse:
                                subdirs = getsubdirs(xd)
                                for sd in subdirs:
                                    sd = sd.lower()
                                    if sd not in dirs:
                                        dirs[sd] = None
        self.dirs = list(dirs)

    def __getitem__(self, key):
        return self.dirs[key]

    def __len__(self):
        return len(self.dirs)

    def __setitem__(self, key, value):
        self.dirs[key] = value

    def __delitem__(self, key):
        del self.dirs[key]

    def __getslice__(self, lo, hi):
        return self.dirs[lo:hi]

    def __setslice__(self, lo, hi, seq):
        self.dirs[lo:hi] = seq

    def __delslice__(self, lo, hi):
        del self.dirs[lo:hi]

    def __add__(self, other):
        if isinstance(other, (dirpath, list)):
            return self.dirs + other.dirs

    def __radd__(self, other):
        if isinstance(other, (dirpath, list)):
            return other.dirs + self.dirs


# Group(1) is the filename, group(2) is the lineno.
regexGrep = re.compile(r"^([a-zA-Z]:[^(]*)\(([0-9]+)\)")

# these are the atom numbers defined by Windows for basic dialog controls

BUTTON = 0x80
EDIT = 0x81
STATIC = 0x82
LISTBOX = 0x83
SCROLLBAR = 0x84
COMBOBOX = 0x85


class GrepTemplate(docview.RichEditDocTemplate):
    def __init__(self):
        docview.RichEditDocTemplate.__init__(
            self, win32ui.IDR_TEXTTYPE, GrepDocument, GrepFrame, GrepView
        )
        self.SetDocStrings("\nGrep\nGrep\nGrep params (*.grep)\n.grep\n\n\n")
        win32ui.GetApp().AddDocTemplate(self)
        self.docparams = None

    def MatchDocType(self, fileName, fileType):
        doc = self.FindOpenDocument(fileName)
        if doc:
            return doc
        ext = os.path.splitext(fileName)[1].lower()
        if ext == ".grep":
            return win32ui.CDocTemplate_Confidence_yesAttemptNative
        return win32ui.CDocTemplate_Confidence_noAttempt

    def setParams(self, params):
        self.docparams = params

    def readParams(self):
        tmp = self.docparams
        self.docparams = None
        return tmp


class GrepFrame(window.MDIChildWnd):
    # The template and doc params will one day be removed.
    def __init__(self, wnd=None):
        window.MDIChildWnd.__init__(self, wnd)


class GrepDocument(docview.RichEditDoc):
    def __init__(self, template):
        docview.RichEditDoc.__init__(self, template)
        self.dirpattern = ""
        self.filpattern = ""
        self.greppattern = ""
        self.casesensitive = 1
        self.recurse = 1
        self.verbose = 0

    def OnOpenDocument(self, fnm):
        # this bizarre stuff with params is so right clicking in a result window
        # and starting a new grep can communicate the default parameters to the
        # new grep.
        try:
            params = open(fnm, "r").read()
        except:
            params = None
        self.setInitParams(params)
        return self.OnNewDocument()

    def OnCloseDocument(self):
        try:
            win32ui.GetApp().DeleteIdleHandler(self.SearchFile)
        except:
            pass
        return self._obj_.OnCloseDocument()

    def saveInitParams(self):
        # Only save the flags, not the text boxes.
        paramstr = "\t%s\t\t%d\t%d" % (
            self.filpattern,
            self.casesensitive,
            self.recurse,
        )
        win32ui.WriteProfileVal("Grep", "Params", paramstr)

    def setInitParams(self, paramstr):
        if paramstr is None:
            paramstr = win32ui.GetProfileVal("Grep", "Params", "\t\t\t1\t0\t0")
        params = paramstr.split("\t")
        if len(params) < 3:
            params.extend([""] * (3 - len(params)))
        if len(params) < 6:
            params.extend([0] * (6 - len(params)))
        self.dirpattern = params[0]
        self.filpattern = params[1]
        self.greppattern = params[2]
        self.casesensitive = int(params[3])
        self.recurse = int(params[4])
        self.verbose = int(params[5])
        # setup some reasonable defaults.
        if not self.dirpattern:
            try:
                editor = win32ui.GetMainFrame().MDIGetActive()[0].GetEditorView()
                self.dirpattern = os.path.abspath(
                    os.path.dirname(editor.GetDocument().GetPathName())
                )
            except (AttributeError, win32ui.error):
                self.dirpattern = os.getcwd()
        if not self.filpattern:
            self.filpattern = "*.py"

    def OnNewDocument(self):
        if self.dirpattern == "":
            self.setInitParams(greptemplate.readParams())
        d = GrepDialog(
            self.dirpattern,
            self.filpattern,
            self.greppattern,
            self.casesensitive,
            self.recurse,
            self.verbose,
        )
        if d.DoModal() == win32con.IDOK:
            self.dirpattern = d["dirpattern"]
            self.filpattern = d["filpattern"]
            self.greppattern = d["greppattern"]
            self.casesensitive = d["casesensitive"]
            self.recurse = d["recursive"]
            self.verbose = d["verbose"]
            self.doSearch()
            self.saveInitParams()
            return 1
        return 0  # cancelled - return zero to stop frame creation.

    def doSearch(self):
        self.dp = dirpath(self.dirpattern, self.recurse)
        self.SetTitle(f"Grep for {self.greppattern} in {self.filpattern}")
        # self.text = []
        self.GetFirstView().Append(f"#Search {self.dirpattern}\n")
        if self.verbose:
            self.GetFirstView().Append(f"#   ={self.dp.dirs!r}\n")
        self.GetFirstView().Append(f"# Files {self.filpattern}\n")
        self.GetFirstView().Append(f"#   For {self.greppattern}\n")
        self.fplist = self.filpattern.split(";")
        if self.casesensitive:
            self.pat = re.compile(self.greppattern)
        else:
            self.pat = re.compile(self.greppattern, re.IGNORECASE)
        win32ui.SetStatusText("Searching.  Please wait...", 0)
        self.dpndx = self.fpndx = 0
        self.fndx = -1
        if not self.dp:
            self.GetFirstView().Append(
                "# ERROR: '%s' does not resolve to any search locations"
                % self.dirpattern
            )
            self.SetModifiedFlag(0)
        else:
            self.flist = glob.glob(self.dp[0] + "\\" + self.fplist[0])
            win32ui.GetApp().AddIdleHandler(self.SearchFile)

    def SearchFile(self, handler, count):
        self.fndx += 1
        if self.fndx < len(self.flist):
            f = self.flist[self.fndx]
            if self.verbose:
                self.GetFirstView().Append("# .." + f + "\n")
            # Directories may match the file type pattern, and files may be removed
            #  while grep is running
            if os.path.isfile(f):
                win32ui.SetStatusText("Searching " + f, 0)
                lines = open(f, "r").readlines()
                for i in range(len(lines)):
                    line = lines[i]
                    if self.pat.search(line) is not None:
                        self.GetFirstView().Append(f"{f} ({i + 1!r}) {line}")
        else:
            self.fndx = -1
            self.fpndx += 1
            if self.fpndx < len(self.fplist):
                self.flist = glob.glob(
                    self.dp[self.dpndx] + "\\" + self.fplist[self.fpndx]
                )
            else:
                self.fpndx = 0
                self.dpndx += 1
                if self.dpndx < len(self.dp):
                    self.flist = glob.glob(
                        self.dp[self.dpndx] + "\\" + self.fplist[self.fpndx]
                    )
                else:
                    win32ui.SetStatusText("Search complete.", 0)
                    self.SetModifiedFlag(0)  # default to not modified.
                    try:
                        win32ui.GetApp().DeleteIdleHandler(self.SearchFile)
                    except:
                        pass
                    return 0
        return 1

    def GetParams(self):
        return "{}\t{}\t{}\t{!r}\t{!r}\t{!r}".format(
            self.dirpattern,
            self.filpattern,
            self.greppattern,
            self.casesensitive,
            self.recurse,
            self.verbose,
        )

    def OnSaveDocument(self, filename):
        # print("OnSaveDocument() filename=", filename)
        savefile = open(filename, "wb")
        txt = self.GetParams() + "\n"
        # print("writing", txt)
        savefile.write(txt)
        savefile.close()
        self.SetModifiedFlag(0)
        return 1


ID_OPEN_FILE = 0xE400
ID_GREP = 0xE401
ID_SAVERESULTS = 0x402
ID_TRYAGAIN = 0x403


class GrepView(docview.RichEditView):
    def __init__(self, doc):
        docview.RichEditView.__init__(self, doc)
        self.SetWordWrap(win32ui.CRichEditView_WrapNone)
        self.HookHandlers()

    def OnInitialUpdate(self):
        rc = self._obj_.OnInitialUpdate()
        format = (-402653169, 0, 200, 0, 0, 0, 49, "Courier New")
        self.SetDefaultCharFormat(format)
        return rc

    def HookHandlers(self):
        self.HookMessage(self.OnRClick, win32con.WM_RBUTTONDOWN)
        self.HookCommand(self.OnCmdOpenFile, ID_OPEN_FILE)
        self.HookCommand(self.OnCmdGrep, ID_GREP)
        self.HookCommand(self.OnCmdSave, ID_SAVERESULTS)
        self.HookCommand(self.OnTryAgain, ID_TRYAGAIN)
        self.HookMessage(self.OnLDblClick, win32con.WM_LBUTTONDBLCLK)

    def OnLDblClick(self, params):
        line = self.GetLine()
        regexGrepResult = regexGrep.match(line)
        if regexGrepResult:
            fname = regexGrepResult.group(1)
            line = int(regexGrepResult.group(2))
            scriptutils.JumpToDocument(fname, line)
            return 0  # don't pass on
        return 1  # pass it on by default.

    def OnRClick(self, params):
        menu = win32ui.CreatePopupMenu()
        flags = win32con.MF_STRING | win32con.MF_ENABLED
        lineno = self._obj_.LineFromChar(-1)  # selection or current line
        line = self._obj_.GetLine(lineno)
        regexGrepResult = regexGrep.match(line)
        if regexGrepResult:
            self.fnm = regexGrepResult.group(1)
            self.lnnum = int(regexGrepResult.group(2))
            menu.AppendMenu(flags, ID_OPEN_FILE, "&Open " + self.fnm)
            menu.AppendMenu(win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, ID_TRYAGAIN, "&Try Again")
        charstart, charend = self._obj_.GetSel()
        if charstart != charend:
            linestart = self._obj_.LineIndex(lineno)
            self.sel = line[charstart - linestart : charend - linestart]
            menu.AppendMenu(flags, ID_GREP, "&Grep for " + self.sel)
            menu.AppendMenu(win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, win32ui.ID_EDIT_CUT, "Cu&t")
        menu.AppendMenu(flags, win32ui.ID_EDIT_COPY, "&Copy")
        menu.AppendMenu(flags, win32ui.ID_EDIT_PASTE, "&Paste")
        menu.AppendMenu(flags, win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, win32ui.ID_EDIT_SELECT_ALL, "&Select all")
        menu.AppendMenu(flags, win32con.MF_SEPARATOR)
        menu.AppendMenu(flags, ID_SAVERESULTS, "Sa&ve results")
        menu.TrackPopupMenu(params[5])
        return 0

    def OnCmdOpenFile(self, cmd, code):
        doc = win32ui.GetApp().OpenDocumentFile(self.fnm)
        if doc:
            vw = doc.GetFirstView()
            # hope you have an editor that implements GotoLine()!
            try:
                vw.GotoLine(int(self.lnnum))
            except:
                pass
        return 0

    def OnCmdGrep(self, cmd, code):
        if code != 0:
            return 1
        curparamsstr = self.GetDocument().GetParams()
        params = curparamsstr.split("\t")
        params[2] = self.sel
        greptemplate.setParams("\t".join(params))
        greptemplate.OpenDocumentFile()
        return 0

    def OnTryAgain(self, cmd, code):
        if code != 0:
            return 1
        greptemplate.setParams(self.GetDocument().GetParams())
        greptemplate.OpenDocumentFile()
        return 0

    def OnCmdSave(self, cmd, code):
        if code != 0:
            return 1
        flags = win32con.OFN_OVERWRITEPROMPT
        dlg = win32ui.CreateFileDialog(
            0, None, None, flags, "Text Files (*.txt)|*.txt||", self
        )
        dlg.SetOFNTitle("Save Results As")
        if dlg.DoModal() == win32con.IDOK:
            pn = dlg.GetPathName()
            self._obj_.SaveTextFile(pn)
        return 0

    def Append(self, strng):
        numlines = self.GetLineCount()
        endpos = self.LineIndex(numlines - 1) + len(self.GetLine(numlines - 1))
        self.SetSel(endpos, endpos)
        self.ReplaceSel(strng)


class GrepDialog(dialog.Dialog):
    def __init__(self, dp, fp, gp, cs, r, v):
        style = (
            win32con.DS_MODALFRAME
            | win32con.WS_POPUP
            | win32con.WS_VISIBLE
            | win32con.WS_CAPTION
            | win32con.WS_SYSMENU
            | win32con.DS_SETFONT
        )
        CS = win32con.WS_CHILD | win32con.WS_VISIBLE
        tmp = [
            ["Grep", (0, 0, 210, 90), style, None, (8, "MS Sans Serif")],
        ]
        tmp.append([STATIC, "Grep For:", -1, (7, 7, 50, 9), CS])
        tmp.append(
            [
                EDIT,
                gp,
                101,
                (52, 7, 144, 11),
                CS | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL | win32con.WS_BORDER,
            ]
        )
        tmp.append([STATIC, "Directories:", -1, (7, 20, 50, 9), CS])
        tmp.append(
            [
                EDIT,
                dp,
                102,
                (52, 20, 128, 11),
                CS | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL | win32con.WS_BORDER,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "...",
                110,
                (182, 20, 16, 11),
                CS | win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        tmp.append([STATIC, "File types:", -1, (7, 33, 50, 9), CS])
        tmp.append(
            [
                EDIT,
                fp,
                103,
                (52, 33, 128, 11),
                CS | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL | win32con.WS_BORDER,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "...",
                111,
                (182, 33, 16, 11),
                CS | win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Case sensitive",
                104,
                (7, 45, 72, 9),
                CS
                | win32con.BS_AUTOCHECKBOX
                | win32con.BS_LEFTTEXT
                | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Subdirectories",
                105,
                (7, 56, 72, 9),
                CS
                | win32con.BS_AUTOCHECKBOX
                | win32con.BS_LEFTTEXT
                | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Verbose",
                106,
                (7, 67, 72, 9),
                CS
                | win32con.BS_AUTOCHECKBOX
                | win32con.BS_LEFTTEXT
                | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "OK",
                win32con.IDOK,
                (166, 53, 32, 12),
                CS | win32con.BS_DEFPUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Cancel",
                win32con.IDCANCEL,
                (166, 67, 32, 12),
                CS | win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        dialog.Dialog.__init__(self, tmp)
        self.AddDDX(101, "greppattern")
        self.AddDDX(102, "dirpattern")
        self.AddDDX(103, "filpattern")
        self.AddDDX(104, "casesensitive")
        self.AddDDX(105, "recursive")
        self.AddDDX(106, "verbose")
        self._obj_.data["greppattern"] = gp
        self._obj_.data["dirpattern"] = dp
        self._obj_.data["filpattern"] = fp
        self._obj_.data["casesensitive"] = cs
        self._obj_.data["recursive"] = r
        self._obj_.data["verbose"] = v
        self.HookCommand(self.OnMoreDirectories, 110)
        self.HookCommand(self.OnMoreFiles, 111)

    def OnMoreDirectories(self, cmd, code):
        if code != 0:
            return 1
        self.getMore("Grep\\Directories", "dirpattern")

    def OnMoreFiles(self, cmd, code):
        if code != 0:
            return 1
        self.getMore("Grep\\File Types", "filpattern")

    def getMore(self, section, key):
        self.UpdateData(1)
        # get the items out of the ini file
        ini = win32ui.GetProfileFileName()
        secitems = win32api.GetProfileSection(section, ini)
        items = []
        for secitem in secitems:
            items.append(secitem.split("=")[1])
        dlg = GrepParamsDialog(items)
        if dlg.DoModal() == win32con.IDOK:
            itemstr = ";".join(dlg.getItems())
            self._obj_.data[key] = itemstr
            # update the ini file with dlg.getNew()
            i = 0
            newitems = dlg.getNew()
            if newitems:
                items.extend(newitems)
                for item in items:
                    win32api.WriteProfileVal(section, repr(i), item, ini)
                    i += 1
            self.UpdateData(0)

    def OnOK(self):
        self.UpdateData(1)
        for id, name in (
            (101, "greppattern"),
            (102, "dirpattern"),
            (103, "filpattern"),
        ):
            if not self[name]:
                self.GetDlgItem(id).SetFocus()
                win32api.MessageBeep()
                win32ui.SetStatusText("Please enter a value")
                return
        self._obj_.OnOK()


class GrepParamsDialog(dialog.Dialog):
    def __init__(self, items):
        self.items = items
        self.newitems = []
        style = (
            win32con.DS_MODALFRAME
            | win32con.WS_POPUP
            | win32con.WS_VISIBLE
            | win32con.WS_CAPTION
            | win32con.WS_SYSMENU
            | win32con.DS_SETFONT
        )
        CS = win32con.WS_CHILD | win32con.WS_VISIBLE
        tmp = [
            ["Grep Parameters", (0, 0, 205, 100), style, None, (8, "MS Sans Serif")],
        ]
        tmp.append(
            [
                LISTBOX,
                "",
                107,
                (7, 7, 150, 72),
                CS
                | win32con.LBS_MULTIPLESEL
                | win32con.LBS_STANDARD
                | win32con.LBS_HASSTRINGS
                | win32con.WS_TABSTOP
                | win32con.LBS_NOTIFY,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "OK",
                win32con.IDOK,
                (167, 7, 32, 12),
                CS | win32con.BS_DEFPUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Cancel",
                win32con.IDCANCEL,
                (167, 23, 32, 12),
                CS | win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        tmp.append([STATIC, "New:", -1, (2, 83, 15, 12), CS])
        tmp.append(
            [
                EDIT,
                "",
                108,
                (18, 83, 139, 12),
                CS | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL | win32con.WS_BORDER,
            ]
        )
        tmp.append(
            [
                BUTTON,
                "Add",
                109,
                (167, 83, 32, 12),
                CS | win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            ]
        )
        dialog.Dialog.__init__(self, tmp)
        self.HookCommand(self.OnAddItem, 109)
        self.HookCommand(self.OnListDoubleClick, 107)

    def OnInitDialog(self):
        lb = self.GetDlgItem(107)
        for item in self.items:
            lb.AddString(item)
        return self._obj_.OnInitDialog()

    def OnAddItem(self, cmd, code):
        if code != 0:
            return 1
        eb = self.GetDlgItem(108)
        item = eb.GetLine(0)
        self.newitems.append(item)
        lb = self.GetDlgItem(107)
        i = lb.AddString(item)
        lb.SetSel(i, 1)
        return 1

    def OnListDoubleClick(self, cmd, code):
        if code == win32con.LBN_DBLCLK:
            self.OnOK()
            return 1

    def OnOK(self):
        lb = self.GetDlgItem(107)
        self.selections = lb.GetSelTextItems()
        self._obj_.OnOK()

    def getItems(self):
        return self.selections

    def getNew(self):
        return self.newitems


try:
    win32ui.GetApp().RemoveDocTemplate(greptemplate)  # type: ignore[has-type, used-before-def]
except NameError:
    pass

greptemplate = GrepTemplate()

# === NexusCore/openenv\Lib\site-packages\yaml\constructor.py ===

__all__ = [
    'BaseConstructor',
    'SafeConstructor',
    'FullConstructor',
    'UnsafeConstructor',
    'Constructor',
    'ConstructorError'
]

from .error import *
from .nodes import *

import collections.abc, datetime, base64, binascii, re, sys, types

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor:

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.state_generators = []
        self.deep_construct = False

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def check_state_key(self, key):
        """Block special attributes/methods from being set in a newly created
        object, to prevent user-controlled methods from being called during
        deserialization"""
        if self.get_state_keys_blacklist_regexp().match(key):
            raise ConstructorError(None, None,
                "blacklisted key '%s' in instance state found" % (key,), None)

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def get_single_data(self):
        # Ensure that the stream contains a single document and construct it.
        node = self.get_single_node()
        if node is not None:
            return self.construct_document(node)
        return None

    def construct_document(self, node):
        data = self.construct_object(node)
        while self.state_generators:
            state_generators = self.state_generators
            self.state_generators = []
            for generator in state_generators:
                for dummy in generator:
                    pass
        self.constructed_objects = {}
        self.recursive_objects = {}
        self.deep_construct = False
        return data

    def construct_object(self, node, deep=False):
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if deep:
            old_deep = self.deep_construct
            self.deep_construct = True
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found unconstructable recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        tag_suffix = None
        if node.tag in self.yaml_constructors:
            constructor = self.yaml_constructors[node.tag]
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if tag_prefix is not None and node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = self.yaml_multi_constructors[tag_prefix]
                    break
            else:
                if None in self.yaml_multi_constructors:
                    tag_suffix = node.tag
                    constructor = self.yaml_multi_constructors[None]
                elif None in self.yaml_constructors:
                    constructor = self.yaml_constructors[None]
                elif isinstance(node, ScalarNode):
                    constructor = self.__class__.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.__class__.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.__class__.construct_mapping
        if tag_suffix is None:
            data = constructor(self, node)
        else:
            data = constructor(self, tag_suffix, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = next(generator)
            if self.deep_construct:
                for dummy in generator:
                    pass
            else:
                self.state_generators.append(generator)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        if deep:
            self.deep_construct = old_deep
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node, deep=False):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child, deep=deep)
                for child in node.value]

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.abc.Hashable):
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

    def construct_pairs(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            pairs.append((key, value))
        return pairs

    @classmethod
    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor

    @classmethod
    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor

class SafeConstructor(BaseConstructor):

    def construct_scalar(self, node):
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if key_node.tag == 'tag:yaml.org,2002:value':
                    return self.construct_scalar(value_node)
        return super().construct_scalar(node)

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == 'tag:yaml.org,2002:merge':
                del node.value[index]
                if isinstance(value_node, MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == 'tag:yaml.org,2002:value':
                key_node.tag = 'tag:yaml.org,2002:str'
                index += 1
            else:
                index += 1
        if merge:
            node.value = merge + node.value

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        return super().construct_mapping(node, deep=deep)

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        'yes':      True,
        'no':       False,
        'true':     True,
        'false':    False,
        'on':       True,
        'off':      False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = self.construct_scalar(node)
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300
    while inf_value != inf_value*inf_value:
        inf_value *= inf_value
    nan_value = -inf_value/inf_value   # Trying to make a quiet NaN (like C99).

    def construct_yaml_float(self, node):
        value = self.construct_scalar(node)
        value = value.replace('_', '').lower()
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '.inf':
            return sign*self.inf_value
        elif value == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*float(value)

    def construct_yaml_binary(self, node):
        try:
            value = self.construct_scalar(node).encode('ascii')
        except UnicodeEncodeError as exc:
            raise ConstructorError(None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
        try:
            if hasattr(base64, 'decodebytes'):
                return base64.decodebytes(value)
            else:
                return base64.decodestring(value)
        except binascii.Error as exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    timestamp_regexp = re.compile(
            r'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?P<tz>Z|(?P<tz_sign>[-+])(?P<tz_hour>[0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9]))?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        year = int(values['year'])
        month = int(values['month'])
        day = int(values['day'])
        if not values['hour']:
            return datetime.date(year, month, day)
        hour = int(values['hour'])
        minute = int(values['minute'])
        second = int(values['second'])
        fraction = 0
        tzinfo = None
        if values['fraction']:
            fraction = values['fraction'][:6]
            while len(fraction) < 6:
                fraction += '0'
            fraction = int(fraction)
        if values['tz_sign']:
            tz_hour = int(values['tz_hour'])
            tz_minute = int(values['tz_minute'] or 0)
            delta = datetime.timedelta(hours=tz_hour, minutes=tz_minute)
            if values['tz_sign'] == '-':
                delta = -delta
            tzinfo = datetime.timezone(delta)
        elif values['tz']:
            tzinfo = datetime.timezone.utc
        return datetime.datetime(year, month, day, hour, minute, second, fraction,
                                 tzinfo=tzinfo)

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        omap = []
        yield omap
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap.append((key, value))

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        pairs = []
        yield pairs
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            pairs.append((key, value))

    def construct_yaml_set(self, node):
        data = set()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_str(self, node):
        return self.construct_scalar(node)

    def construct_yaml_seq(self, node):
        data = []
        yield data
        data.extend(self.construct_sequence(node))

    def construct_yaml_map(self, node):
        data = {}
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_yaml_object(self, node, cls):
        data = cls.__new__(cls)
        yield data
        if hasattr(data, '__setstate__'):
            state = self.construct_mapping(node, deep=True)
            data.__setstate__(state)
        else:
            state = self.construct_mapping(node)
            data.__dict__.update(state)

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag,
                node.start_mark)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:timestamp',
        SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class FullConstructor(SafeConstructor):
    # 'extend' is blacklisted because it is used by
    # construct_python_object_apply to add `listitems` to a newly generate
    # python instance
    def get_state_keys_blacklist(self):
        return ['^extend$', '^__.*__$']

    def get_state_keys_blacklist_regexp(self):
        if not hasattr(self, 'state_keys_blacklist_regexp'):
            self.state_keys_blacklist_regexp = re.compile('(' + '|'.join(self.get_state_keys_blacklist()) + ')')
        return self.state_keys_blacklist_regexp

    def construct_python_str(self, node):
        return self.construct_scalar(node)

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_bytes(self, node):
        try:
            value = self.construct_scalar(node).encode('ascii')
        except UnicodeEncodeError as exc:
            raise ConstructorError(None, None,
                    "failed to convert base64 data into ascii: %s" % exc,
                    node.start_mark)
        try:
            if hasattr(base64, 'decodebytes'):
                return base64.decodebytes(value)
            else:
                return base64.decodestring(value)
        except binascii.Error as exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark)

    def construct_python_long(self, node):
        return self.construct_yaml_int(node)

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def find_python_module(self, name, mark, unsafe=False):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        if unsafe:
            try:
                __import__(name)
            except ImportError as exc:
                raise ConstructorError("while constructing a Python module", mark,
                        "cannot find module %r (%s)" % (name, exc), mark)
        if name not in sys.modules:
            raise ConstructorError("while constructing a Python module", mark,
                    "module %r is not imported" % name, mark)
        return sys.modules[name]

    def find_python_name(self, name, mark, unsafe=False):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if '.' in name:
            module_name, object_name = name.rsplit('.', 1)
        else:
            module_name = 'builtins'
            object_name = name
        if unsafe:
            try:
                __import__(module_name)
            except ImportError as exc:
                raise ConstructorError("while constructing a Python object", mark,
                        "cannot find module %r (%s)" % (module_name, exc), mark)
        if module_name not in sys.modules:
            raise ConstructorError("while constructing a Python object", mark,
                    "module %r is not imported" % module_name, mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r"
                    % (object_name, module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value, node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value, node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False, unsafe=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if not (unsafe or isinstance(cls, type)):
            raise ConstructorError("while constructing a Python instance", node.start_mark,
                    "expected a class, but found %r" % type(cls),
                    node.start_mark)
        if newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state, unsafe=False):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                if not unsafe and state:
                    for key in state.keys():
                        self.check_state_key(key)
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                if not unsafe:
                    self.check_state_key(key)
                setattr(instance, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        yield instance
        deep = hasattr(instance, '__setstate__')
        state = self.construct_mapping(node, deep=deep)
        self.set_python_instance_state(instance, state)

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node, deep=True)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node, deep=True)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/none',
    FullConstructor.construct_yaml_null)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/bool',
    FullConstructor.construct_yaml_bool)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/str',
    FullConstructor.construct_python_str)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/unicode',
    FullConstructor.construct_python_unicode)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/bytes',
    FullConstructor.construct_python_bytes)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/int',
    FullConstructor.construct_yaml_int)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/long',
    FullConstructor.construct_python_long)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/float',
    FullConstructor.construct_yaml_float)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/complex',
    FullConstructor.construct_python_complex)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/list',
    FullConstructor.construct_yaml_seq)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/tuple',
    FullConstructor.construct_python_tuple)

FullConstructor.add_constructor(
    'tag:yaml.org,2002:python/dict',
    FullConstructor.construct_yaml_map)

FullConstructor.add_multi_constructor(
    'tag:yaml.org,2002:python/name:',
    FullConstructor.construct_python_name)

class UnsafeConstructor(FullConstructor):

    def find_python_module(self, name, mark):
        return super(UnsafeConstructor, self).find_python_module(name, mark, unsafe=True)

    def find_python_name(self, name, mark):
        return super(UnsafeConstructor, self).find_python_name(name, mark, unsafe=True)

    def make_python_instance(self, suffix, node, args=None, kwds=None, newobj=False):
        return super(UnsafeConstructor, self).make_python_instance(
            suffix, node, args, kwds, newobj, unsafe=True)

    def set_python_instance_state(self, instance, state):
        return super(UnsafeConstructor, self).set_python_instance_state(
            instance, state, unsafe=True)

UnsafeConstructor.add_multi_constructor(
    'tag:yaml.org,2002:python/module:',
    UnsafeConstructor.construct_python_module)

UnsafeConstructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object:',
    UnsafeConstructor.construct_python_object)

UnsafeConstructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object/new:',
    UnsafeConstructor.construct_python_object_new)

UnsafeConstructor.add_multi_constructor(
    'tag:yaml.org,2002:python/object/apply:',
    UnsafeConstructor.construct_python_object_apply)

# Constructor is same as UnsafeConstructor. Need to leave this in place in case
# people have extended it directly.
class Constructor(UnsafeConstructor):
    pass

# === NexusCore/openenv\Lib\site-packages\numpy\_core\getlimits.py ===
"""Machine limits for Float32 and Float64 and (long double) if available...

"""
__all__ = ['finfo', 'iinfo']

import types
import warnings

from numpy._utils import set_module

from . import numeric
from . import numerictypes as ntypes
from ._machar import MachAr
from .numeric import array, inf, nan
from .umath import exp2, isnan, log10, nextafter


def _fr0(a):
    """fix rank-0 --> rank-1"""
    if a.ndim == 0:
        a = a.copy()
        a.shape = (1,)
    return a


def _fr1(a):
    """fix rank > 0 --> rank-0"""
    if a.size == 1:
        a = a.copy()
        a.shape = ()
    return a


class MachArLike:
    """ Object to simulate MachAr instance """
    def __init__(self, ftype, *, eps, epsneg, huge, tiny,
                 ibeta, smallest_subnormal=None, **kwargs):
        self.params = _MACHAR_PARAMS[ftype]
        self.ftype = ftype
        self.title = self.params['title']
        # Parameter types same as for discovered MachAr object.
        if not smallest_subnormal:
            self._smallest_subnormal = nextafter(
                self.ftype(0), self.ftype(1), dtype=self.ftype)
        else:
            self._smallest_subnormal = smallest_subnormal
        self.epsilon = self.eps = self._float_to_float(eps)
        self.epsneg = self._float_to_float(epsneg)
        self.xmax = self.huge = self._float_to_float(huge)
        self.xmin = self._float_to_float(tiny)
        self.smallest_normal = self.tiny = self._float_to_float(tiny)
        self.ibeta = self.params['itype'](ibeta)
        self.__dict__.update(kwargs)
        self.precision = int(-log10(self.eps))
        self.resolution = self._float_to_float(
            self._float_conv(10) ** (-self.precision))
        self._str_eps = self._float_to_str(self.eps)
        self._str_epsneg = self._float_to_str(self.epsneg)
        self._str_xmin = self._float_to_str(self.xmin)
        self._str_xmax = self._float_to_str(self.xmax)
        self._str_resolution = self._float_to_str(self.resolution)
        self._str_smallest_normal = self._float_to_str(self.xmin)

    @property
    def smallest_subnormal(self):
        """Return the value for the smallest subnormal.

        Returns
        -------
        smallest_subnormal : float
            value for the smallest subnormal.

        Warns
        -----
        UserWarning
            If the calculated value for the smallest subnormal is zero.
        """
        # Check that the calculated value is not zero, in case it raises a
        # warning.
        value = self._smallest_subnormal
        if self.ftype(0) == value:
            warnings.warn(
                f'The value of the smallest subnormal for {self.ftype} type is zero.',
                UserWarning, stacklevel=2)

        return self._float_to_float(value)

    @property
    def _str_smallest_subnormal(self):
        """Return the string representation of the smallest subnormal."""
        return self._float_to_str(self.smallest_subnormal)

    def _float_to_float(self, value):
        """Converts float to float.

        Parameters
        ----------
        value : float
            value to be converted.
        """
        return _fr1(self._float_conv(value))

    def _float_conv(self, value):
        """Converts float to conv.

        Parameters
        ----------
        value : float
            value to be converted.
        """
        return array([value], self.ftype)

    def _float_to_str(self, value):
        """Converts float to str.

        Parameters
        ----------
        value : float
            value to be converted.
        """
        return self.params['fmt'] % array(_fr0(value)[0], self.ftype)


_convert_to_float = {
    ntypes.csingle: ntypes.single,
    ntypes.complex128: ntypes.float64,
    ntypes.clongdouble: ntypes.longdouble
    }

# Parameters for creating MachAr / MachAr-like objects
_title_fmt = 'numpy {} precision floating point number'
_MACHAR_PARAMS = {
    ntypes.double: {
        'itype': ntypes.int64,
        'fmt': '%24.16e',
        'title': _title_fmt.format('double')},
    ntypes.single: {
        'itype': ntypes.int32,
        'fmt': '%15.7e',
        'title': _title_fmt.format('single')},
    ntypes.longdouble: {
        'itype': ntypes.longlong,
        'fmt': '%s',
        'title': _title_fmt.format('long double')},
    ntypes.half: {
        'itype': ntypes.int16,
        'fmt': '%12.5e',
        'title': _title_fmt.format('half')}}

# Key to identify the floating point type.  Key is result of
#
#    ftype = np.longdouble        # or float64, float32, etc.
#    v = (ftype(-1.0) / ftype(10.0))
#    v.view(v.dtype.newbyteorder('<')).tobytes()
#
# Uses division to work around deficiencies in strtold on some platforms.
# See:
# https://perl5.git.perl.org/perl.git/blob/3118d7d684b56cbeb702af874f4326683c45f045:/Configure

_KNOWN_TYPES = {}
def _register_type(machar, bytepat):
    _KNOWN_TYPES[bytepat] = machar


_float_ma = {}


def _register_known_types():
    # Known parameters for float16
    # See docstring of MachAr class for description of parameters.
    f16 = ntypes.float16
    float16_ma = MachArLike(f16,
                            machep=-10,
                            negep=-11,
                            minexp=-14,
                            maxexp=16,
                            it=10,
                            iexp=5,
                            ibeta=2,
                            irnd=5,
                            ngrd=0,
                            eps=exp2(f16(-10)),
                            epsneg=exp2(f16(-11)),
                            huge=f16(65504),
                            tiny=f16(2 ** -14))
    _register_type(float16_ma, b'f\xae')
    _float_ma[16] = float16_ma

    # Known parameters for float32
    f32 = ntypes.float32
    float32_ma = MachArLike(f32,
                            machep=-23,
                            negep=-24,
                            minexp=-126,
                            maxexp=128,
                            it=23,
                            iexp=8,
                            ibeta=2,
                            irnd=5,
                            ngrd=0,
                            eps=exp2(f32(-23)),
                            epsneg=exp2(f32(-24)),
                            huge=f32((1 - 2 ** -24) * 2**128),
                            tiny=exp2(f32(-126)))
    _register_type(float32_ma, b'\xcd\xcc\xcc\xbd')
    _float_ma[32] = float32_ma

    # Known parameters for float64
    f64 = ntypes.float64
    epsneg_f64 = 2.0 ** -53.0
    tiny_f64 = 2.0 ** -1022.0
    float64_ma = MachArLike(f64,
                            machep=-52,
                            negep=-53,
                            minexp=-1022,
                            maxexp=1024,
                            it=52,
                            iexp=11,
                            ibeta=2,
                            irnd=5,
                            ngrd=0,
                            eps=2.0 ** -52.0,
                            epsneg=epsneg_f64,
                            huge=(1.0 - epsneg_f64) / tiny_f64 * f64(4),
                            tiny=tiny_f64)
    _register_type(float64_ma, b'\x9a\x99\x99\x99\x99\x99\xb9\xbf')
    _float_ma[64] = float64_ma

    # Known parameters for IEEE 754 128-bit binary float
    ld = ntypes.longdouble
    epsneg_f128 = exp2(ld(-113))
    tiny_f128 = exp2(ld(-16382))
    # Ignore runtime error when this is not f128
    with numeric.errstate(all='ignore'):
        huge_f128 = (ld(1) - epsneg_f128) / tiny_f128 * ld(4)
    float128_ma = MachArLike(ld,
                             machep=-112,
                             negep=-113,
                             minexp=-16382,
                             maxexp=16384,
                             it=112,
                             iexp=15,
                             ibeta=2,
                             irnd=5,
                             ngrd=0,
                             eps=exp2(ld(-112)),
                             epsneg=epsneg_f128,
                             huge=huge_f128,
                             tiny=tiny_f128)
    # IEEE 754 128-bit binary float
    _register_type(float128_ma,
        b'\x9a\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\x99\xfb\xbf')
    _float_ma[128] = float128_ma

    # Known parameters for float80 (Intel 80-bit extended precision)
    epsneg_f80 = exp2(ld(-64))
    tiny_f80 = exp2(ld(-16382))
    # Ignore runtime error when this is not f80
    with numeric.errstate(all='ignore'):
        huge_f80 = (ld(1) - epsneg_f80) / tiny_f80 * ld(4)
    float80_ma = MachArLike(ld,
                            machep=-63,
                            negep=-64,
                            minexp=-16382,
                            maxexp=16384,
                            it=63,
                            iexp=15,
                            ibeta=2,
                            irnd=5,
                            ngrd=0,
                            eps=exp2(ld(-63)),
                            epsneg=epsneg_f80,
                            huge=huge_f80,
                            tiny=tiny_f80)
    # float80, first 10 bytes containing actual storage
    _register_type(float80_ma, b'\xcd\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xfb\xbf')
    _float_ma[80] = float80_ma

    # Guessed / known parameters for double double; see:
    # https://en.wikipedia.org/wiki/Quadruple-precision_floating-point_format#Double-double_arithmetic
    # These numbers have the same exponent range as float64, but extended
    # number of digits in the significand.
    huge_dd = nextafter(ld(inf), ld(0), dtype=ld)
    # As the smallest_normal in double double is so hard to calculate we set
    # it to NaN.
    smallest_normal_dd = nan
    # Leave the same value for the smallest subnormal as double
    smallest_subnormal_dd = ld(nextafter(0., 1.))
    float_dd_ma = MachArLike(ld,
                             machep=-105,
                             negep=-106,
                             minexp=-1022,
                             maxexp=1024,
                             it=105,
                             iexp=11,
                             ibeta=2,
                             irnd=5,
                             ngrd=0,
                             eps=exp2(ld(-105)),
                             epsneg=exp2(ld(-106)),
                             huge=huge_dd,
                             tiny=smallest_normal_dd,
                             smallest_subnormal=smallest_subnormal_dd)
    # double double; low, high order (e.g. PPC 64)
    _register_type(float_dd_ma,
        b'\x9a\x99\x99\x99\x99\x99Y<\x9a\x99\x99\x99\x99\x99\xb9\xbf')
    # double double; high, low order (e.g. PPC 64 le)
    _register_type(float_dd_ma,
        b'\x9a\x99\x99\x99\x99\x99\xb9\xbf\x9a\x99\x99\x99\x99\x99Y<')
    _float_ma['dd'] = float_dd_ma


def _get_machar(ftype):
    """ Get MachAr instance or MachAr-like instance

    Get parameters for floating point type, by first trying signatures of
    various known floating point types, then, if none match, attempting to
    identify parameters by analysis.

    Parameters
    ----------
    ftype : class
        Numpy floating point type class (e.g. ``np.float64``)

    Returns
    -------
    ma_like : instance of :class:`MachAr` or :class:`MachArLike`
        Object giving floating point parameters for `ftype`.

    Warns
    -----
    UserWarning
        If the binary signature of the float type is not in the dictionary of
        known float types.
    """
    params = _MACHAR_PARAMS.get(ftype)
    if params is None:
        raise ValueError(repr(ftype))
    # Detect known / suspected types
    # ftype(-1.0) / ftype(10.0) is better than ftype('-0.1') because stold
    # may be deficient
    key = (ftype(-1.0) / ftype(10.))
    key = key.view(key.dtype.newbyteorder("<")).tobytes()
    ma_like = None
    if ftype == ntypes.longdouble:
        # Could be 80 bit == 10 byte extended precision, where last bytes can
        # be random garbage.
        # Comparing first 10 bytes to pattern first to avoid branching on the
        # random garbage.
        ma_like = _KNOWN_TYPES.get(key[:10])
    if ma_like is None:
        # see if the full key is known.
        ma_like = _KNOWN_TYPES.get(key)
    if ma_like is None and len(key) == 16:
        # machine limits could be f80 masquerading as np.float128,
        # find all keys with length 16 and make new dict, but make the keys
        # only 10 bytes long, the last bytes can be random garbage
        _kt = {k[:10]: v for k, v in _KNOWN_TYPES.items() if len(k) == 16}
        ma_like = _kt.get(key[:10])
    if ma_like is not None:
        return ma_like
    # Fall back to parameter discovery
    warnings.warn(
        f'Signature {key} for {ftype} does not match any known type: '
        'falling back to type probe function.\n'
        'This warnings indicates broken support for the dtype!',
        UserWarning, stacklevel=2)
    return _discovered_machar(ftype)


def _discovered_machar(ftype):
    """ Create MachAr instance with found information on float types

    TODO: MachAr should be retired completely ideally.  We currently only
          ever use it system with broken longdouble (valgrind, WSL).
    """
    params = _MACHAR_PARAMS[ftype]
    return MachAr(lambda v: array([v], ftype),
                  lambda v: _fr0(v.astype(params['itype']))[0],
                  lambda v: array(_fr0(v)[0], ftype),
                  lambda v: params['fmt'] % array(_fr0(v)[0], ftype),
                  params['title'])


@set_module('numpy')
class finfo:
    """
    finfo(dtype)

    Machine limits for floating point types.

    Attributes
    ----------
    bits : int
        The number of bits occupied by the type.
    dtype : dtype
        Returns the dtype for which `finfo` returns information. For complex
        input, the returned dtype is the associated ``float*`` dtype for its
        real and complex components.
    eps : float
        The difference between 1.0 and the next smallest representable float
        larger than 1.0. For example, for 64-bit binary floats in the IEEE-754
        standard, ``eps = 2**-52``, approximately 2.22e-16.
    epsneg : float
        The difference between 1.0 and the next smallest representable float
        less than 1.0. For example, for 64-bit binary floats in the IEEE-754
        standard, ``epsneg = 2**-53``, approximately 1.11e-16.
    iexp : int
        The number of bits in the exponent portion of the floating point
        representation.
    machep : int
        The exponent that yields `eps`.
    max : floating point number of the appropriate type
        The largest representable number.
    maxexp : int
        The smallest positive power of the base (2) that causes overflow.
    min : floating point number of the appropriate type
        The smallest representable number, typically ``-max``.
    minexp : int
        The most negative power of the base (2) consistent with there
        being no leading 0's in the mantissa.
    negep : int
        The exponent that yields `epsneg`.
    nexp : int
        The number of bits in the exponent including its sign and bias.
    nmant : int
        The number of bits in the mantissa.
    precision : int
        The approximate number of decimal digits to which this kind of
        float is precise.
    resolution : floating point number of the appropriate type
        The approximate decimal resolution of this type, i.e.,
        ``10**-precision``.
    tiny : float
        An alias for `smallest_normal`, kept for backwards compatibility.
    smallest_normal : float
        The smallest positive floating point number with 1 as leading bit in
        the mantissa following IEEE-754 (see Notes).
    smallest_subnormal : float
        The smallest positive floating point number with 0 as leading bit in
        the mantissa following IEEE-754.

    Parameters
    ----------
    dtype : float, dtype, or instance
        Kind of floating point or complex floating point
        data-type about which to get information.

    See Also
    --------
    iinfo : The equivalent for integer data types.
    spacing : The distance between a value and the nearest adjacent number
    nextafter : The next floating point value after x1 towards x2

    Notes
    -----
    For developers of NumPy: do not instantiate this at the module level.
    The initial calculation of these parameters is expensive and negatively
    impacts import times.  These objects are cached, so calling ``finfo()``
    repeatedly inside your functions is not a problem.

    Note that ``smallest_normal`` is not actually the smallest positive
    representable value in a NumPy floating point type. As in the IEEE-754
    standard [1]_, NumPy floating point types make use of subnormal numbers to
    fill the gap between 0 and ``smallest_normal``. However, subnormal numbers
    may have significantly reduced precision [2]_.

    This function can also be used for complex data types as well. If used,
    the output will be the same as the corresponding real float type
    (e.g. numpy.finfo(numpy.csingle) is the same as numpy.finfo(numpy.single)).
    However, the output is true for the real and imaginary components.

    References
    ----------
    .. [1] IEEE Standard for Floating-Point Arithmetic, IEEE Std 754-2008,
           pp.1-70, 2008, https://doi.org/10.1109/IEEESTD.2008.4610935
    .. [2] Wikipedia, "Denormal Numbers",
           https://en.wikipedia.org/wiki/Denormal_number

    Examples
    --------
    >>> import numpy as np
    >>> np.finfo(np.float64).dtype
    dtype('float64')
    >>> np.finfo(np.complex64).dtype
    dtype('float32')

    """

    _finfo_cache = {}

    __class_getitem__ = classmethod(types.GenericAlias)

    def __new__(cls, dtype):
        try:
            obj = cls._finfo_cache.get(dtype)  # most common path
            if obj is not None:
                return obj
        except TypeError:
            pass

        if dtype is None:
            # Deprecated in NumPy 1.25, 2023-01-16
            warnings.warn(
                "finfo() dtype cannot be None. This behavior will "
                "raise an error in the future. (Deprecated in NumPy 1.25)",
                DeprecationWarning,
                stacklevel=2
            )

        try:
            dtype = numeric.dtype(dtype)
        except TypeError:
            # In case a float instance was given
            dtype = numeric.dtype(type(dtype))

        obj = cls._finfo_cache.get(dtype)
        if obj is not None:
            return obj
        dtypes = [dtype]
        newdtype = ntypes.obj2sctype(dtype)
        if newdtype is not dtype:
            dtypes.append(newdtype)
            dtype = newdtype
        if not issubclass(dtype, numeric.inexact):
            raise ValueError(f"data type {dtype!r} not inexact")
        obj = cls._finfo_cache.get(dtype)
        if obj is not None:
            return obj
        if not issubclass(dtype, numeric.floating):
            newdtype = _convert_to_float[dtype]
            if newdtype is not dtype:
                # dtype changed, for example from complex128 to float64
                dtypes.append(newdtype)
                dtype = newdtype

                obj = cls._finfo_cache.get(dtype, None)
                if obj is not None:
                    # the original dtype was not in the cache, but the new
                    # dtype is in the cache. we add the original dtypes to
                    # the cache and return the result
                    for dt in dtypes:
                        cls._finfo_cache[dt] = obj
                    return obj
        obj = object.__new__(cls)._init(dtype)
        for dt in dtypes:
            cls._finfo_cache[dt] = obj
        return obj

    def _init(self, dtype):
        self.dtype = numeric.dtype(dtype)
        machar = _get_machar(dtype)

        for word in ['precision', 'iexp',
                     'maxexp', 'minexp', 'negep',
                     'machep']:
            setattr(self, word, getattr(machar, word))
        for word in ['resolution', 'epsneg', 'smallest_subnormal']:
            setattr(self, word, getattr(machar, word).flat[0])
        self.bits = self.dtype.itemsize * 8
        self.max = machar.huge.flat[0]
        self.min = -self.max
        self.eps = machar.eps.flat[0]
        self.nexp = machar.iexp
        self.nmant = machar.it
        self._machar = machar
        self._str_tiny = machar._str_xmin.strip()
        self._str_max = machar._str_xmax.strip()
        self._str_epsneg = machar._str_epsneg.strip()
        self._str_eps = machar._str_eps.strip()
        self._str_resolution = machar._str_resolution.strip()
        self._str_smallest_normal = machar._str_smallest_normal.strip()
        self._str_smallest_subnormal = machar._str_smallest_subnormal.strip()
        return self

    def __str__(self):
        fmt = (
            'Machine parameters for %(dtype)s\n'
            '---------------------------------------------------------------\n'
            'precision = %(precision)3s   resolution = %(_str_resolution)s\n'
            'machep = %(machep)6s   eps =        %(_str_eps)s\n'
            'negep =  %(negep)6s   epsneg =     %(_str_epsneg)s\n'
            'minexp = %(minexp)6s   tiny =       %(_str_tiny)s\n'
            'maxexp = %(maxexp)6s   max =        %(_str_max)s\n'
            'nexp =   %(nexp)6s   min =        -max\n'
            'smallest_normal = %(_str_smallest_normal)s   '
            'smallest_subnormal = %(_str_smallest_subnormal)s\n'
            '---------------------------------------------------------------\n'
            )
        return fmt % self.__dict__

    def __repr__(self):
        c = self.__class__.__name__
        d = self.__dict__.copy()
        d['klass'] = c
        return (("%(klass)s(resolution=%(resolution)s, min=-%(_str_max)s,"
                 " max=%(_str_max)s, dtype=%(dtype)s)") % d)

    @property
    def smallest_normal(self):
        """Return the value for the smallest normal.

        Returns
        -------
        smallest_normal : float
            Value for the smallest normal.

        Warns
        -----
        UserWarning
            If the calculated value for the smallest normal is requested for
            double-double.
        """
        # This check is necessary because the value for smallest_normal is
        # platform dependent for longdouble types.
        if isnan(self._machar.smallest_normal.flat[0]):
            warnings.warn(
                'The value of smallest normal is undefined for double double',
                UserWarning, stacklevel=2)
        return self._machar.smallest_normal.flat[0]

    @property
    def tiny(self):
        """Return the value for tiny, alias of smallest_normal.

        Returns
        -------
        tiny : float
            Value for the smallest normal, alias of smallest_normal.

        Warns
        -----
        UserWarning
            If the calculated value for the smallest normal is requested for
            double-double.
        """
        return self.smallest_normal


@set_module('numpy')
class iinfo:
    """
    iinfo(type)

    Machine limits for integer types.

    Attributes
    ----------
    bits : int
        The number of bits occupied by the type.
    dtype : dtype
        Returns the dtype for which `iinfo` returns information.
    min : int
        The smallest integer expressible by the type.
    max : int
        The largest integer expressible by the type.

    Parameters
    ----------
    int_type : integer type, dtype, or instance
        The kind of integer data type to get information about.

    See Also
    --------
    finfo : The equivalent for floating point data types.

    Examples
    --------
    With types:

    >>> import numpy as np
    >>> ii16 = np.iinfo(np.int16)
    >>> ii16.min
    -32768
    >>> ii16.max
    32767
    >>> ii32 = np.iinfo(np.int32)
    >>> ii32.min
    -2147483648
    >>> ii32.max
    2147483647

    With instances:

    >>> ii32 = np.iinfo(np.int32(10))
    >>> ii32.min
    -2147483648
    >>> ii32.max
    2147483647

    """

    _min_vals = {}
    _max_vals = {}

    __class_getitem__ = classmethod(types.GenericAlias)

    def __init__(self, int_type):
        try:
            self.dtype = numeric.dtype(int_type)
        except TypeError:
            self.dtype = numeric.dtype(type(int_type))
        self.kind = self.dtype.kind
        self.bits = self.dtype.itemsize * 8
        self.key = "%s%d" % (self.kind, self.bits)
        if self.kind not in 'iu':
            raise ValueError(f"Invalid integer data type {self.kind!r}.")

    @property
    def min(self):
        """Minimum value of given dtype."""
        if self.kind == 'u':
            return 0
        else:
            try:
                val = iinfo._min_vals[self.key]
            except KeyError:
                val = int(-(1 << (self.bits - 1)))
                iinfo._min_vals[self.key] = val
            return val

    @property
    def max(self):
        """Maximum value of given dtype."""
        try:
            val = iinfo._max_vals[self.key]
        except KeyError:
            if self.kind == 'u':
                val = int((1 << self.bits) - 1)
            else:
                val = int((1 << (self.bits - 1)) - 1)
            iinfo._max_vals[self.key] = val
        return val

    def __str__(self):
        """String representation."""
        fmt = (
            'Machine parameters for %(dtype)s\n'
            '---------------------------------------------------------------\n'
            'min = %(min)s\n'
            'max = %(max)s\n'
            '---------------------------------------------------------------\n'
            )
        return fmt % {'dtype': self.dtype, 'min': self.min, 'max': self.max}

    def __repr__(self):
        return "%s(min=%s, max=%s, dtype=%s)" % (self.__class__.__name__,
                                    self.min, self.max, self.dtype)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\menus.py ===
from __future__ import annotations

import math
from itertools import zip_longest
from typing import TYPE_CHECKING, Callable, Iterable, Sequence, TypeVar, cast
from weakref import WeakKeyDictionary

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import CompletionState
from prompt_toolkit.completion import Completion
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_completions,
    is_done,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    StyleAndTextTuples,
    fragment_list_width,
    to_formatted_text,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from .containers import ConditionalContainer, HSplit, ScrollOffsets, Window
from .controls import GetLinePrefixCallable, UIContent, UIControl
from .dimension import Dimension
from .margins import ScrollbarMargin

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindings,
        NotImplementedOrNone,
    )


__all__ = [
    "CompletionsMenu",
    "MultiColumnCompletionsMenu",
]

E = KeyPressEvent


class CompletionsMenuControl(UIControl):
    """
    Helper for drawing the complete menu to the screen.

    :param scroll_offset: Number (integer) representing the preferred amount of
        completions to be displayed before and after the current one. When this
        is a very high number, the current completion will be shown in the
        middle most of the time.
    """

    # Preferred minimum size of the menu control.
    # The CompletionsMenu class defines a width of 8, and there is a scrollbar
    # of 1.)
    MIN_WIDTH = 7

    def has_focus(self) -> bool:
        return False

    def preferred_width(self, max_available_width: int) -> int | None:
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            menu_width = self._get_menu_width(500, complete_state)
            menu_meta_width = self._get_menu_meta_width(500, complete_state)

            return menu_width + menu_meta_width
        else:
            return 0

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            return len(complete_state.completions)
        else:
            return 0

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Create a UIContent object for this control.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            completions = complete_state.completions
            index = complete_state.complete_index  # Can be None!

            # Calculate width of completions menu.
            menu_width = self._get_menu_width(width, complete_state)
            menu_meta_width = self._get_menu_meta_width(
                width - menu_width, complete_state
            )
            show_meta = self._show_meta(complete_state)

            def get_line(i: int) -> StyleAndTextTuples:
                c = completions[i]
                is_current_completion = i == index
                result = _get_menu_item_fragments(
                    c, is_current_completion, menu_width, space_after=True
                )

                if show_meta:
                    result += self._get_menu_item_meta_fragments(
                        c, is_current_completion, menu_meta_width
                    )
                return result

            return UIContent(
                get_line=get_line,
                cursor_position=Point(x=0, y=index or 0),
                line_count=len(completions),
            )

        return UIContent()

    def _show_meta(self, complete_state: CompletionState) -> bool:
        """
        Return ``True`` if we need to show a column with meta information.
        """
        return any(c.display_meta_text for c in complete_state.completions)

    def _get_menu_width(self, max_width: int, complete_state: CompletionState) -> int:
        """
        Return the width of the main column.
        """
        return min(
            max_width,
            max(
                self.MIN_WIDTH,
                max(get_cwidth(c.display_text) for c in complete_state.completions) + 2,
            ),
        )

    def _get_menu_meta_width(
        self, max_width: int, complete_state: CompletionState
    ) -> int:
        """
        Return the width of the meta column.
        """

        def meta_width(completion: Completion) -> int:
            return get_cwidth(completion.display_meta_text)

        if self._show_meta(complete_state):
            # If the amount of completions is over 200, compute the width based
            # on the first 200 completions, otherwise this can be very slow.
            completions = complete_state.completions
            if len(completions) > 200:
                completions = completions[:200]

            return min(max_width, max(meta_width(c) for c in completions) + 2)
        else:
            return 0

    def _get_menu_item_meta_fragments(
        self, completion: Completion, is_current_completion: bool, width: int
    ) -> StyleAndTextTuples:
        if is_current_completion:
            style_str = "class:completion-menu.meta.completion.current"
        else:
            style_str = "class:completion-menu.meta.completion"

        text, tw = _trim_formatted_text(completion.display_meta, width - 2)
        padding = " " * (width - 1 - tw)

        return to_formatted_text(
            cast(StyleAndTextTuples, []) + [("", " ")] + text + [("", padding)],
            style=style_str,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """
        Handle mouse events: clicking and scrolling.
        """
        b = get_app().current_buffer

        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            # Select completion.
            b.go_to_completion(mouse_event.position.y)
            b.complete_state = None

        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            # Scroll up.
            b.complete_next(count=3, disable_wrap_around=True)

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            # Scroll down.
            b.complete_previous(count=3, disable_wrap_around=True)

        return None


def _get_menu_item_fragments(
    completion: Completion,
    is_current_completion: bool,
    width: int,
    space_after: bool = False,
) -> StyleAndTextTuples:
    """
    Get the style/text tuples for a menu item, styled and trimmed to the given
    width.
    """
    if is_current_completion:
        style_str = f"class:completion-menu.completion.current {completion.style} {completion.selected_style}"
    else:
        style_str = "class:completion-menu.completion " + completion.style

    text, tw = _trim_formatted_text(
        completion.display, (width - 2 if space_after else width - 1)
    )

    padding = " " * (width - 1 - tw)

    return to_formatted_text(
        cast(StyleAndTextTuples, []) + [("", " ")] + text + [("", padding)],
        style=style_str,
    )


def _trim_formatted_text(
    formatted_text: StyleAndTextTuples, max_width: int
) -> tuple[StyleAndTextTuples, int]:
    """
    Trim the text to `max_width`, append dots when the text is too long.
    Returns (text, width) tuple.
    """
    width = fragment_list_width(formatted_text)

    # When the text is too wide, trim it.
    if width > max_width:
        result = []  # Text fragments.
        remaining_width = max_width - 3

        for style_and_ch in explode_text_fragments(formatted_text):
            ch_width = get_cwidth(style_and_ch[1])

            if ch_width <= remaining_width:
                result.append(style_and_ch)
                remaining_width -= ch_width
            else:
                break

        result.append(("", "..."))

        return result, max_width - remaining_width
    else:
        return formatted_text, width


class CompletionsMenu(ConditionalContainer):
    # NOTE: We use a pretty big z_index by default. Menus are supposed to be
    #       above anything else. We also want to make sure that the content is
    #       visible at the point where we draw this menu.
    def __init__(
        self,
        max_height: int | None = None,
        scroll_offset: int | Callable[[], int] = 0,
        extra_filter: FilterOrBool = True,
        display_arrows: FilterOrBool = False,
        z_index: int = 10**8,
    ) -> None:
        extra_filter = to_filter(extra_filter)
        display_arrows = to_filter(display_arrows)

        super().__init__(
            content=Window(
                content=CompletionsMenuControl(),
                width=Dimension(min=8),
                height=Dimension(min=1, max=max_height),
                scroll_offsets=ScrollOffsets(top=scroll_offset, bottom=scroll_offset),
                right_margins=[ScrollbarMargin(display_arrows=display_arrows)],
                dont_extend_width=True,
                style="class:completion-menu",
                z_index=z_index,
            ),
            # Show when there are completions but not at the point we are
            # returning the input.
            filter=extra_filter & has_completions & ~is_done,
        )


class MultiColumnCompletionMenuControl(UIControl):
    """
    Completion menu that displays all the completions in several columns.
    When there are more completions than space for them to be displayed, an
    arrow is shown on the left or right side.

    `min_rows` indicates how many rows will be available in any possible case.
    When this is larger than one, it will try to use less columns and more
    rows until this value is reached.
    Be careful passing in a too big value, if less than the given amount of
    rows are available, more columns would have been required, but
    `preferred_width` doesn't know about that and reports a too small value.
    This results in less completions displayed and additional scrolling.
    (It's a limitation of how the layout engine currently works: first the
    widths are calculated, then the heights.)

    :param suggested_max_column_width: The suggested max width of a column.
        The column can still be bigger than this, but if there is place for two
        columns of this width, we will display two columns. This to avoid that
        if there is one very wide completion, that it doesn't significantly
        reduce the amount of columns.
    """

    _required_margin = 3  # One extra padding on the right + space for arrows.

    def __init__(self, min_rows: int = 3, suggested_max_column_width: int = 30) -> None:
        assert min_rows >= 1

        self.min_rows = min_rows
        self.suggested_max_column_width = suggested_max_column_width
        self.scroll = 0

        # Cache for column width computations. This computation is not cheap,
        # so we don't want to do it over and over again while the user
        # navigates through the completions.
        # (map `completion_state` to `(completion_count, width)`. We remember
        # the count, because a completer can add new completions to the
        # `CompletionState` while loading.)
        self._column_width_for_completion_state: WeakKeyDictionary[
            CompletionState, tuple[int, int]
        ] = WeakKeyDictionary()

        # Info of last rendering.
        self._rendered_rows = 0
        self._rendered_columns = 0
        self._total_columns = 0
        self._render_pos_to_completion: dict[tuple[int, int], Completion] = {}
        self._render_left_arrow = False
        self._render_right_arrow = False
        self._render_width = 0

    def reset(self) -> None:
        self.scroll = 0

    def has_focus(self) -> bool:
        return False

    def preferred_width(self, max_available_width: int) -> int | None:
        """
        Preferred width: prefer to use at least min_rows, but otherwise as much
        as possible horizontally.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return 0

        column_width = self._get_column_width(complete_state)
        result = int(
            column_width
            * math.ceil(len(complete_state.completions) / float(self.min_rows))
        )

        # When the desired width is still more than the maximum available,
        # reduce by removing columns until we are less than the available
        # width.
        while (
            result > column_width
            and result > max_available_width - self._required_margin
        ):
            result -= column_width
        return result + self._required_margin

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """
        Preferred height: as much as needed in order to display all the completions.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return 0

        column_width = self._get_column_width(complete_state)
        column_count = max(1, (width - self._required_margin) // column_width)

        return int(math.ceil(len(complete_state.completions) / float(column_count)))

    def create_content(self, width: int, height: int) -> UIContent:
        """
        Create a UIContent object for this menu.
        """
        complete_state = get_app().current_buffer.complete_state
        if complete_state is None:
            return UIContent()

        column_width = self._get_column_width(complete_state)
        self._render_pos_to_completion = {}

        _T = TypeVar("_T")

        def grouper(
            n: int, iterable: Iterable[_T], fillvalue: _T | None = None
        ) -> Iterable[Sequence[_T | None]]:
            "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
            args = [iter(iterable)] * n
            return zip_longest(fillvalue=fillvalue, *args)

        def is_current_completion(completion: Completion) -> bool:
            "Returns True when this completion is the currently selected one."
            return (
                complete_state is not None
                and complete_state.complete_index is not None
                and c == complete_state.current_completion
            )

        # Space required outside of the regular columns, for displaying the
        # left and right arrow.
        HORIZONTAL_MARGIN_REQUIRED = 3

        # There should be at least one column, but it cannot be wider than
        # the available width.
        column_width = min(width - HORIZONTAL_MARGIN_REQUIRED, column_width)

        # However, when the columns tend to be very wide, because there are
        # some very wide entries, shrink it anyway.
        if column_width > self.suggested_max_column_width:
            # `column_width` can still be bigger that `suggested_max_column_width`,
            # but if there is place for two columns, we divide by two.
            column_width //= column_width // self.suggested_max_column_width

        visible_columns = max(1, (width - self._required_margin) // column_width)

        columns_ = list(grouper(height, complete_state.completions))
        rows_ = list(zip(*columns_))

        # Make sure the current completion is always visible: update scroll offset.
        selected_column = (complete_state.complete_index or 0) // height
        self.scroll = min(
            selected_column, max(self.scroll, selected_column - visible_columns + 1)
        )

        render_left_arrow = self.scroll > 0
        render_right_arrow = self.scroll < len(rows_[0]) - visible_columns

        # Write completions to screen.
        fragments_for_line = []

        for row_index, row in enumerate(rows_):
            fragments: StyleAndTextTuples = []
            middle_row = row_index == len(rows_) // 2

            # Draw left arrow if we have hidden completions on the left.
            if render_left_arrow:
                fragments.append(("class:scrollbar", "<" if middle_row else " "))
            elif render_right_arrow:
                # Reserve one column empty space. (If there is a right
                # arrow right now, there can be a left arrow as well.)
                fragments.append(("", " "))

            # Draw row content.
            for column_index, c in enumerate(row[self.scroll :][:visible_columns]):
                if c is not None:
                    fragments += _get_menu_item_fragments(
                        c, is_current_completion(c), column_width, space_after=False
                    )

                    # Remember render position for mouse click handler.
                    for x in range(column_width):
                        self._render_pos_to_completion[
                            (column_index * column_width + x, row_index)
                        ] = c
                else:
                    fragments.append(("class:completion", " " * column_width))

            # Draw trailing padding for this row.
            # (_get_menu_item_fragments only returns padding on the left.)
            if render_left_arrow or render_right_arrow:
                fragments.append(("class:completion", " "))

            # Draw right arrow if we have hidden completions on the right.
            if render_right_arrow:
                fragments.append(("class:scrollbar", ">" if middle_row else " "))
            elif render_left_arrow:
                fragments.append(("class:completion", " "))

            # Add line.
            fragments_for_line.append(
                to_formatted_text(fragments, style="class:completion-menu")
            )

        self._rendered_rows = height
        self._rendered_columns = visible_columns
        self._total_columns = len(columns_)
        self._render_left_arrow = render_left_arrow
        self._render_right_arrow = render_right_arrow
        self._render_width = (
            column_width * visible_columns + render_left_arrow + render_right_arrow + 1
        )

        def get_line(i: int) -> StyleAndTextTuples:
            return fragments_for_line[i]

        return UIContent(get_line=get_line, line_count=len(rows_))

    def _get_column_width(self, completion_state: CompletionState) -> int:
        """
        Return the width of each column.
        """
        try:
            count, width = self._column_width_for_completion_state[completion_state]
            if count != len(completion_state.completions):
                # Number of completions changed, recompute.
                raise KeyError
            return width
        except KeyError:
            result = (
                max(get_cwidth(c.display_text) for c in completion_state.completions)
                + 1
            )
            self._column_width_for_completion_state[completion_state] = (
                len(completion_state.completions),
                result,
            )
            return result

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """
        Handle scroll and click events.
        """
        b = get_app().current_buffer

        def scroll_left() -> None:
            b.complete_previous(count=self._rendered_rows, disable_wrap_around=True)
            self.scroll = max(0, self.scroll - 1)

        def scroll_right() -> None:
            b.complete_next(count=self._rendered_rows, disable_wrap_around=True)
            self.scroll = min(
                self._total_columns - self._rendered_columns, self.scroll + 1
            )

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            scroll_right()

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            scroll_left()

        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            x = mouse_event.position.x
            y = mouse_event.position.y

            # Mouse click on left arrow.
            if x == 0:
                if self._render_left_arrow:
                    scroll_left()

            # Mouse click on right arrow.
            elif x == self._render_width - 1:
                if self._render_right_arrow:
                    scroll_right()

            # Mouse click on completion.
            else:
                completion = self._render_pos_to_completion.get((x, y))
                if completion:
                    b.apply_completion(completion)

        return None

    def get_key_bindings(self) -> KeyBindings:
        """
        Expose key bindings that handle the left/right arrow keys when the menu
        is displayed.
        """
        from prompt_toolkit.key_binding.key_bindings import KeyBindings

        kb = KeyBindings()

        @Condition
        def filter() -> bool:
            "Only handle key bindings if this menu is visible."
            app = get_app()
            complete_state = app.current_buffer.complete_state

            # There need to be completions, and one needs to be selected.
            if complete_state is None or complete_state.complete_index is None:
                return False

            # This menu needs to be visible.
            return any(window.content == self for window in app.layout.visible_windows)

        def move(right: bool = False) -> None:
            buff = get_app().current_buffer
            complete_state = buff.complete_state

            if complete_state is not None and complete_state.complete_index is not None:
                # Calculate new complete index.
                new_index = complete_state.complete_index
                if right:
                    new_index += self._rendered_rows
                else:
                    new_index -= self._rendered_rows

                if 0 <= new_index < len(complete_state.completions):
                    buff.go_to_completion(new_index)

        # NOTE: the is_global is required because the completion menu will
        #       never be focussed.

        @kb.add("left", is_global=True, filter=filter)
        def _left(event: E) -> None:
            move()

        @kb.add("right", is_global=True, filter=filter)
        def _right(event: E) -> None:
            move(True)

        return kb


class MultiColumnCompletionsMenu(HSplit):
    """
    Container that displays the completions in several columns.
    When `show_meta` (a :class:`~prompt_toolkit.filters.Filter`) evaluates
    to True, it shows the meta information at the bottom.
    """

    def __init__(
        self,
        min_rows: int = 3,
        suggested_max_column_width: int = 30,
        show_meta: FilterOrBool = True,
        extra_filter: FilterOrBool = True,
        z_index: int = 10**8,
    ) -> None:
        show_meta = to_filter(show_meta)
        extra_filter = to_filter(extra_filter)

        # Display filter: show when there are completions but not at the point
        # we are returning the input.
        full_filter = extra_filter & has_completions & ~is_done

        @Condition
        def any_completion_has_meta() -> bool:
            complete_state = get_app().current_buffer.complete_state
            return complete_state is not None and any(
                c.display_meta for c in complete_state.completions
            )

        # Create child windows.
        # NOTE: We don't set style='class:completion-menu' to the
        #       `MultiColumnCompletionMenuControl`, because this is used in a
        #       Float that is made transparent, and the size of the control
        #       doesn't always correspond exactly with the size of the
        #       generated content.
        completions_window = ConditionalContainer(
            content=Window(
                content=MultiColumnCompletionMenuControl(
                    min_rows=min_rows,
                    suggested_max_column_width=suggested_max_column_width,
                ),
                width=Dimension(min=8),
                height=Dimension(min=1),
            ),
            filter=full_filter,
        )

        meta_window = ConditionalContainer(
            content=Window(content=_SelectedCompletionMetaControl()),
            filter=full_filter & show_meta & any_completion_has_meta,
        )

        # Initialize split.
        super().__init__([completions_window, meta_window], z_index=z_index)


class _SelectedCompletionMetaControl(UIControl):
    """
    Control that shows the meta information of the selected completion.
    """

    def preferred_width(self, max_available_width: int) -> int | None:
        """
        Report the width of the longest meta text as the preferred width of this control.

        It could be that we use less width, but this way, we're sure that the
        layout doesn't change when we select another completion (E.g. that
        completions are suddenly shown in more or fewer columns.)
        """
        app = get_app()
        if app.current_buffer.complete_state:
            state = app.current_buffer.complete_state

            if len(state.completions) >= 30:
                # When there are many completions, calling `get_cwidth` for
                # every `display_meta_text` is too expensive. In this case,
                # just return the max available width. There will be enough
                # columns anyway so that the whole screen is filled with
                # completions and `create_content` will then take up as much
                # space as needed.
                return max_available_width

            return 2 + max(
                get_cwidth(c.display_meta_text) for c in state.completions[:100]
            )
        else:
            return 0

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        return 1

    def create_content(self, width: int, height: int) -> UIContent:
        fragments = self._get_text_fragments()

        def get_line(i: int) -> StyleAndTextTuples:
            return fragments

        return UIContent(get_line=get_line, line_count=1 if fragments else 0)

    def _get_text_fragments(self) -> StyleAndTextTuples:
        style = "class:completion-menu.multi-column-meta"
        state = get_app().current_buffer.complete_state

        if (
            state
            and state.current_completion
            and state.current_completion.display_meta_text
        ):
            return to_formatted_text(
                cast(StyleAndTextTuples, [("", " ")])
                + state.current_completion.display_meta
                + [("", " ")],
                style=style,
            )

        return []

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\networks.py ===
import re
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
    _BaseAddress,
    _BaseNetwork,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    Generator,
    List,
    Match,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    Union,
    cast,
    no_type_check,
)

from pydantic.v1 import errors
from pydantic.v1.utils import Representation, update_not_none
from pydantic.v1.validators import constr_length_validator, str_validator

if TYPE_CHECKING:
    import email_validator
    from typing_extensions import TypedDict

    from pydantic.v1.config import BaseConfig
    from pydantic.v1.fields import ModelField
    from pydantic.v1.typing import AnyCallable

    CallableGenerator = Generator[AnyCallable, None, None]

    class Parts(TypedDict, total=False):
        scheme: str
        user: Optional[str]
        password: Optional[str]
        ipv4: Optional[str]
        ipv6: Optional[str]
        domain: Optional[str]
        port: Optional[str]
        path: Optional[str]
        query: Optional[str]
        fragment: Optional[str]

    class HostParts(TypedDict, total=False):
        host: str
        tld: Optional[str]
        host_type: Optional[str]
        port: Optional[str]
        rebuild: bool

else:
    email_validator = None

    class Parts(dict):
        pass


NetworkType = Union[str, bytes, int, Tuple[Union[str, bytes, int], Union[str, int]]]

__all__ = [
    'AnyUrl',
    'AnyHttpUrl',
    'FileUrl',
    'HttpUrl',
    'stricturl',
    'EmailStr',
    'NameEmail',
    'IPvAnyAddress',
    'IPvAnyInterface',
    'IPvAnyNetwork',
    'PostgresDsn',
    'CockroachDsn',
    'AmqpDsn',
    'RedisDsn',
    'MongoDsn',
    'KafkaDsn',
    'validate_email',
]

_url_regex_cache = None
_multi_host_url_regex_cache = None
_ascii_domain_regex_cache = None
_int_domain_regex_cache = None
_host_regex_cache = None

_host_regex = (
    r'(?:'
    r'(?P<ipv4>(?:\d{1,3}\.){3}\d{1,3})(?=$|[/:#?])|'  # ipv4
    r'(?P<ipv6>\[[A-F0-9]*:[A-F0-9:]+\])(?=$|[/:#?])|'  # ipv6
    r'(?P<domain>[^\s/:?#]+)'  # domain, validation occurs later
    r')?'
    r'(?::(?P<port>\d+))?'  # port
)
_scheme_regex = r'(?:(?P<scheme>[a-z][a-z0-9+\-.]+)://)?'  # scheme https://tools.ietf.org/html/rfc3986#appendix-A
_user_info_regex = r'(?:(?P<user>[^\s:/]*)(?::(?P<password>[^\s/]*))?@)?'
_path_regex = r'(?P<path>/[^\s?#]*)?'
_query_regex = r'(?:\?(?P<query>[^\s#]*))?'
_fragment_regex = r'(?:#(?P<fragment>[^\s#]*))?'


def url_regex() -> Pattern[str]:
    global _url_regex_cache
    if _url_regex_cache is None:
        _url_regex_cache = re.compile(
            rf'{_scheme_regex}{_user_info_regex}{_host_regex}{_path_regex}{_query_regex}{_fragment_regex}',
            re.IGNORECASE,
        )
    return _url_regex_cache


def multi_host_url_regex() -> Pattern[str]:
    """
    Compiled multi host url regex.

    Additionally to `url_regex` it allows to match multiple hosts.
    E.g. host1.db.net,host2.db.net
    """
    global _multi_host_url_regex_cache
    if _multi_host_url_regex_cache is None:
        _multi_host_url_regex_cache = re.compile(
            rf'{_scheme_regex}{_user_info_regex}'
            r'(?P<hosts>([^/]*))'  # validation occurs later
            rf'{_path_regex}{_query_regex}{_fragment_regex}',
            re.IGNORECASE,
        )
    return _multi_host_url_regex_cache


def ascii_domain_regex() -> Pattern[str]:
    global _ascii_domain_regex_cache
    if _ascii_domain_regex_cache is None:
        ascii_chunk = r'[_0-9a-z](?:[-_0-9a-z]{0,61}[_0-9a-z])?'
        ascii_domain_ending = r'(?P<tld>\.[a-z]{2,63})?\.?'
        _ascii_domain_regex_cache = re.compile(
            fr'(?:{ascii_chunk}\.)*?{ascii_chunk}{ascii_domain_ending}', re.IGNORECASE
        )
    return _ascii_domain_regex_cache


def int_domain_regex() -> Pattern[str]:
    global _int_domain_regex_cache
    if _int_domain_regex_cache is None:
        int_chunk = r'[_0-9a-\U00040000](?:[-_0-9a-\U00040000]{0,61}[_0-9a-\U00040000])?'
        int_domain_ending = r'(?P<tld>(\.[^\W\d_]{2,63})|(\.(?:xn--)[_0-9a-z-]{2,63}))?\.?'
        _int_domain_regex_cache = re.compile(fr'(?:{int_chunk}\.)*?{int_chunk}{int_domain_ending}', re.IGNORECASE)
    return _int_domain_regex_cache


def host_regex() -> Pattern[str]:
    global _host_regex_cache
    if _host_regex_cache is None:
        _host_regex_cache = re.compile(
            _host_regex,
            re.IGNORECASE,
        )
    return _host_regex_cache


class AnyUrl(str):
    strip_whitespace = True
    min_length = 1
    max_length = 2**16
    allowed_schemes: Optional[Collection[str]] = None
    tld_required: bool = False
    user_required: bool = False
    host_required: bool = True
    hidden_parts: Set[str] = set()

    __slots__ = ('scheme', 'user', 'password', 'host', 'tld', 'host_type', 'port', 'path', 'query', 'fragment')

    @no_type_check
    def __new__(cls, url: Optional[str], **kwargs) -> object:
        return str.__new__(cls, cls.build(**kwargs) if url is None else url)

    def __init__(
        self,
        url: str,
        *,
        scheme: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        tld: Optional[str] = None,
        host_type: str = 'domain',
        port: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ) -> None:
        str.__init__(url)
        self.scheme = scheme
        self.user = user
        self.password = password
        self.host = host
        self.tld = tld
        self.host_type = host_type
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment

    @classmethod
    def build(
        cls,
        *,
        scheme: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: str,
        port: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
        **_kwargs: str,
    ) -> str:
        parts = Parts(
            scheme=scheme,
            user=user,
            password=password,
            host=host,
            port=port,
            path=path,
            query=query,
            fragment=fragment,
            **_kwargs,  # type: ignore[misc]
        )

        url = scheme + '://'
        if user:
            url += user
        if password:
            url += ':' + password
        if user or password:
            url += '@'
        url += host
        if port and ('port' not in cls.hidden_parts or cls.get_default_parts(parts).get('port') != port):
            url += ':' + port
        if path:
            url += path
        if query:
            url += '?' + query
        if fragment:
            url += '#' + fragment
        return url

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        update_not_none(field_schema, minLength=cls.min_length, maxLength=cls.max_length, format='uri')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, field: 'ModelField', config: 'BaseConfig') -> 'AnyUrl':
        if value.__class__ == cls:
            return value
        value = str_validator(value)
        if cls.strip_whitespace:
            value = value.strip()
        url: str = cast(str, constr_length_validator(value, field, config))

        m = cls._match_url(url)
        # the regex should always match, if it doesn't please report with details of the URL tried
        assert m, 'URL regex failed unexpectedly'

        original_parts = cast('Parts', m.groupdict())
        parts = cls.apply_default_parts(original_parts)
        parts = cls.validate_parts(parts)

        if m.end() != len(url):
            raise errors.UrlExtraError(extra=url[m.end() :])

        return cls._build_url(m, url, parts)

    @classmethod
    def _build_url(cls, m: Match[str], url: str, parts: 'Parts') -> 'AnyUrl':
        """
        Validate hosts and build the AnyUrl object. Split from `validate` so this method
        can be altered in `MultiHostDsn`.
        """
        host, tld, host_type, rebuild = cls.validate_host(parts)

        return cls(
            None if rebuild else url,
            scheme=parts['scheme'],
            user=parts['user'],
            password=parts['password'],
            host=host,
            tld=tld,
            host_type=host_type,
            port=parts['port'],
            path=parts['path'],
            query=parts['query'],
            fragment=parts['fragment'],
        )

    @staticmethod
    def _match_url(url: str) -> Optional[Match[str]]:
        return url_regex().match(url)

    @staticmethod
    def _validate_port(port: Optional[str]) -> None:
        if port is not None and int(port) > 65_535:
            raise errors.UrlPortError()

    @classmethod
    def validate_parts(cls, parts: 'Parts', validate_port: bool = True) -> 'Parts':
        """
        A method used to validate parts of a URL.
        Could be overridden to set default values for parts if missing
        """
        scheme = parts['scheme']
        if scheme is None:
            raise errors.UrlSchemeError()

        if cls.allowed_schemes and scheme.lower() not in cls.allowed_schemes:
            raise errors.UrlSchemePermittedError(set(cls.allowed_schemes))

        if validate_port:
            cls._validate_port(parts['port'])

        user = parts['user']
        if cls.user_required and user is None:
            raise errors.UrlUserInfoError()

        return parts

    @classmethod
    def validate_host(cls, parts: 'Parts') -> Tuple[str, Optional[str], str, bool]:
        tld, host_type, rebuild = None, None, False
        for f in ('domain', 'ipv4', 'ipv6'):
            host = parts[f]  # type: ignore[literal-required]
            if host:
                host_type = f
                break

        if host is None:
            if cls.host_required:
                raise errors.UrlHostError()
        elif host_type == 'domain':
            is_international = False
            d = ascii_domain_regex().fullmatch(host)
            if d is None:
                d = int_domain_regex().fullmatch(host)
                if d is None:
                    raise errors.UrlHostError()
                is_international = True

            tld = d.group('tld')
            if tld is None and not is_international:
                d = int_domain_regex().fullmatch(host)
                assert d is not None
                tld = d.group('tld')
                is_international = True

            if tld is not None:
                tld = tld[1:]
            elif cls.tld_required:
                raise errors.UrlHostTldError()

            if is_international:
                host_type = 'int_domain'
                rebuild = True
                host = host.encode('idna').decode('ascii')
                if tld is not None:
                    tld = tld.encode('idna').decode('ascii')

        return host, tld, host_type, rebuild  # type: ignore

    @staticmethod
    def get_default_parts(parts: 'Parts') -> 'Parts':
        return {}

    @classmethod
    def apply_default_parts(cls, parts: 'Parts') -> 'Parts':
        for key, value in cls.get_default_parts(parts).items():
            if not parts[key]:  # type: ignore[literal-required]
                parts[key] = value  # type: ignore[literal-required]
        return parts

    def __repr__(self) -> str:
        extra = ', '.join(f'{n}={getattr(self, n)!r}' for n in self.__slots__ if getattr(self, n) is not None)
        return f'{self.__class__.__name__}({super().__repr__()}, {extra})'


class AnyHttpUrl(AnyUrl):
    allowed_schemes = {'http', 'https'}

    __slots__ = ()


class HttpUrl(AnyHttpUrl):
    tld_required = True
    # https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
    max_length = 2083
    hidden_parts = {'port'}

    @staticmethod
    def get_default_parts(parts: 'Parts') -> 'Parts':
        return {'port': '80' if parts['scheme'] == 'http' else '443'}


class FileUrl(AnyUrl):
    allowed_schemes = {'file'}
    host_required = False

    __slots__ = ()


class MultiHostDsn(AnyUrl):
    __slots__ = AnyUrl.__slots__ + ('hosts',)

    def __init__(self, *args: Any, hosts: Optional[List['HostParts']] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.hosts = hosts

    @staticmethod
    def _match_url(url: str) -> Optional[Match[str]]:
        return multi_host_url_regex().match(url)

    @classmethod
    def validate_parts(cls, parts: 'Parts', validate_port: bool = True) -> 'Parts':
        return super().validate_parts(parts, validate_port=False)

    @classmethod
    def _build_url(cls, m: Match[str], url: str, parts: 'Parts') -> 'MultiHostDsn':
        hosts_parts: List['HostParts'] = []
        host_re = host_regex()
        for host in m.groupdict()['hosts'].split(','):
            d: Parts = host_re.match(host).groupdict()  # type: ignore
            host, tld, host_type, rebuild = cls.validate_host(d)
            port = d.get('port')
            cls._validate_port(port)
            hosts_parts.append(
                {
                    'host': host,
                    'host_type': host_type,
                    'tld': tld,
                    'rebuild': rebuild,
                    'port': port,
                }
            )

        if len(hosts_parts) > 1:
            return cls(
                None if any([hp['rebuild'] for hp in hosts_parts]) else url,
                scheme=parts['scheme'],
                user=parts['user'],
                password=parts['password'],
                path=parts['path'],
                query=parts['query'],
                fragment=parts['fragment'],
                host_type=None,
                hosts=hosts_parts,
            )
        else:
            # backwards compatibility with single host
            host_part = hosts_parts[0]
            return cls(
                None if host_part['rebuild'] else url,
                scheme=parts['scheme'],
                user=parts['user'],
                password=parts['password'],
                host=host_part['host'],
                tld=host_part['tld'],
                host_type=host_part['host_type'],
                port=host_part.get('port'),
                path=parts['path'],
                query=parts['query'],
                fragment=parts['fragment'],
            )


class PostgresDsn(MultiHostDsn):
    allowed_schemes = {
        'postgres',
        'postgresql',
        'postgresql+asyncpg',
        'postgresql+pg8000',
        'postgresql+psycopg',
        'postgresql+psycopg2',
        'postgresql+psycopg2cffi',
        'postgresql+py-postgresql',
        'postgresql+pygresql',
    }
    user_required = True

    __slots__ = ()


class CockroachDsn(AnyUrl):
    allowed_schemes = {
        'cockroachdb',
        'cockroachdb+psycopg2',
        'cockroachdb+asyncpg',
    }
    user_required = True


class AmqpDsn(AnyUrl):
    allowed_schemes = {'amqp', 'amqps'}
    host_required = False


class RedisDsn(AnyUrl):
    __slots__ = ()
    allowed_schemes = {'redis', 'rediss'}
    host_required = False

    @staticmethod
    def get_default_parts(parts: 'Parts') -> 'Parts':
        return {
            'domain': 'localhost' if not (parts['ipv4'] or parts['ipv6']) else '',
            'port': '6379',
            'path': '/0',
        }


class MongoDsn(AnyUrl):
    allowed_schemes = {'mongodb'}

    # TODO: Needed to generic "Parts" for "Replica Set", "Sharded Cluster", and other mongodb deployment modes
    @staticmethod
    def get_default_parts(parts: 'Parts') -> 'Parts':
        return {
            'port': '27017',
        }


class KafkaDsn(AnyUrl):
    allowed_schemes = {'kafka'}

    @staticmethod
    def get_default_parts(parts: 'Parts') -> 'Parts':
        return {
            'domain': 'localhost',
            'port': '9092',
        }


def stricturl(
    *,
    strip_whitespace: bool = True,
    min_length: int = 1,
    max_length: int = 2**16,
    tld_required: bool = True,
    host_required: bool = True,
    allowed_schemes: Optional[Collection[str]] = None,
) -> Type[AnyUrl]:
    # use kwargs then define conf in a dict to aid with IDE type hinting
    namespace = dict(
        strip_whitespace=strip_whitespace,
        min_length=min_length,
        max_length=max_length,
        tld_required=tld_required,
        host_required=host_required,
        allowed_schemes=allowed_schemes,
    )
    return type('UrlValue', (AnyUrl,), namespace)


def import_email_validator() -> None:
    global email_validator
    try:
        import email_validator
    except ImportError as e:
        raise ImportError('email-validator is not installed, run `pip install pydantic[email]`') from e


class EmailStr(str):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='email')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        # included here and below so the error happens straight away
        import_email_validator()

        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str]) -> str:
        return validate_email(value)[1]


class NameEmail(Representation):
    __slots__ = 'name', 'email'

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NameEmail) and (self.name, self.email) == (other.name, other.email)

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='name-email')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        import_email_validator()

        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> 'NameEmail':
        if value.__class__ == cls:
            return value
        value = str_validator(value)
        return cls(*validate_email(value))

    def __str__(self) -> str:
        return f'{self.name} <{self.email}>'


class IPvAnyAddress(_BaseAddress):
    __slots__ = ()

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='ipvanyaddress')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str, bytes, int]) -> Union[IPv4Address, IPv6Address]:
        try:
            return IPv4Address(value)
        except ValueError:
            pass

        try:
            return IPv6Address(value)
        except ValueError:
            raise errors.IPvAnyAddressError()


class IPvAnyInterface(_BaseAddress):
    __slots__ = ()

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='ipvanyinterface')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, value: NetworkType) -> Union[IPv4Interface, IPv6Interface]:
        try:
            return IPv4Interface(value)
        except ValueError:
            pass

        try:
            return IPv6Interface(value)
        except ValueError:
            raise errors.IPvAnyInterfaceError()


class IPvAnyNetwork(_BaseNetwork):  # type: ignore
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='ipvanynetwork')

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls.validate

    @classmethod
    def validate(cls, value: NetworkType) -> Union[IPv4Network, IPv6Network]:
        # Assume IP Network is defined with a default value for ``strict`` argument.
        # Define your own class if you want to specify network address check strictness.
        try:
            return IPv4Network(value)
        except ValueError:
            pass

        try:
            return IPv6Network(value)
        except ValueError:
            raise errors.IPvAnyNetworkError()


pretty_email_regex = re.compile(r'([\w ]*?) *<(.*)> *')
MAX_EMAIL_LENGTH = 2048
"""Maximum length for an email.
A somewhat arbitrary but very generous number compared to what is allowed by most implementations.
"""


def validate_email(value: Union[str]) -> Tuple[str, str]:
    """
    Email address validation using https://pypi.org/project/email-validator/
    Notes:
    * raw ip address (literal) domain parts are not allowed.
    * "John Doe <local_part@domain.com>" style "pretty" email addresses are processed
    * spaces are striped from the beginning and end of addresses but no error is raised
    """
    if email_validator is None:
        import_email_validator()

    if len(value) > MAX_EMAIL_LENGTH:
        raise errors.EmailError()

    m = pretty_email_regex.fullmatch(value)
    name: Union[str, None] = None
    if m:
        name, value = m.groups()
    email = value.strip()
    try:
        parts = email_validator.validate_email(email, check_deliverability=False)
    except email_validator.EmailNotValidError as e:
        raise errors.EmailError from e

    if hasattr(parts, 'normalized'):
        # email-validator >= 2
        email = parts.normalized
        assert email is not None
        name = name or parts.local_part
        return name, email
    else:
        # email-validator >1, <2
        at_index = email.index('@')
        local_part = email[:at_index]  # RFC 5321, local part must be case-sensitive.
        global_part = email[at_index:].lower()

        return name or local_part, local_part + global_part

# === NexusCore/openenv\Lib\site-packages\ipykernel\debugger.py ===
"""Debugger implementation for the IPython kernel."""
import os
import re
import sys
import typing as t
from pathlib import Path

import zmq
from IPython.core.getipython import get_ipython
from IPython.core.inputtransformer2 import leading_empty_lines
from tornado.locks import Event
from tornado.queues import Queue
from zmq.utils import jsonapi

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default

from .compiler import get_file_name, get_tmp_directory, get_tmp_hash_seed

try:
    # This import is required to have the next ones working...
    from debugpy.server import api  # noqa: F401

    from _pydevd_bundle import pydevd_frame_utils  # isort: skip
    from _pydevd_bundle.pydevd_suspended_frames import (  # isort: skip
        SuspendedFramesManager,
        _FramesTracker,
    )

    _is_debugpy_available = True
except ImportError:
    _is_debugpy_available = False
except Exception as e:
    # We cannot import the module where the DebuggerInitializationError
    # is defined
    if e.__class__.__name__ == "DebuggerInitializationError":
        _is_debugpy_available = False
    else:
        raise e


# Required for backwards compatibility
ROUTING_ID = getattr(zmq, "ROUTING_ID", None) or zmq.IDENTITY


class _FakeCode:
    """Fake code class."""

    def __init__(self, co_filename, co_name):
        """Init."""
        self.co_filename = co_filename
        self.co_name = co_name


class _FakeFrame:
    """Fake frame class."""

    def __init__(self, f_code, f_globals, f_locals):
        """Init."""
        self.f_code = f_code
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_back = None


class _DummyPyDB:
    """Fake PyDb class."""

    def __init__(self):
        """Init."""
        from _pydevd_bundle.pydevd_api import PyDevdAPI

        self.variable_presentation = PyDevdAPI.VariablePresentation()


class VariableExplorer:
    """A variable explorer."""

    def __init__(self):
        """Initialize the explorer."""
        self.suspended_frame_manager = SuspendedFramesManager()
        self.py_db = _DummyPyDB()
        self.tracker = _FramesTracker(self.suspended_frame_manager, self.py_db)
        self.frame = None

    def track(self):
        """Start tracking."""
        var = get_ipython().user_ns
        self.frame = _FakeFrame(_FakeCode("<module>", get_file_name("sys._getframe()")), var, var)
        self.tracker.track("thread1", pydevd_frame_utils.create_frames_list_from_frame(self.frame))

    def untrack_all(self):
        """Stop tracking."""
        self.tracker.untrack_all()

    def get_children_variables(self, variable_ref=None):
        """Get the child variables for a variable reference."""
        var_ref = variable_ref
        if not var_ref:
            var_ref = id(self.frame)
        variables = self.suspended_frame_manager.get_variable(var_ref)
        return [x.get_var_data() for x in variables.get_children_variables()]


class DebugpyMessageQueue:
    """A debugpy message queue."""

    HEADER = "Content-Length: "
    HEADER_LENGTH = 16
    SEPARATOR = "\r\n\r\n"
    SEPARATOR_LENGTH = 4

    def __init__(self, event_callback, log):
        """Init the queue."""
        self.tcp_buffer = ""
        self._reset_tcp_pos()
        self.event_callback = event_callback
        self.message_queue: Queue[t.Any] = Queue()
        self.log = log

    def _reset_tcp_pos(self):
        self.header_pos = -1
        self.separator_pos = -1
        self.message_size = 0
        self.message_pos = -1

    def _put_message(self, raw_msg):
        self.log.debug("QUEUE - _put_message:")
        msg = t.cast(t.Dict[str, t.Any], jsonapi.loads(raw_msg))
        if msg["type"] == "event":
            self.log.debug("QUEUE - received event:")
            self.log.debug(msg)
            self.event_callback(msg)
        else:
            self.log.debug("QUEUE - put message:")
            self.log.debug(msg)
            self.message_queue.put_nowait(msg)

    def put_tcp_frame(self, frame):
        """Put a tcp frame in the queue."""
        self.tcp_buffer += frame

        self.log.debug("QUEUE - received frame")
        while True:
            # Finds header
            if self.header_pos == -1:
                self.header_pos = self.tcp_buffer.find(DebugpyMessageQueue.HEADER)
            if self.header_pos == -1:
                return

            self.log.debug("QUEUE - found header at pos %i", self.header_pos)

            # Finds separator
            if self.separator_pos == -1:
                hint = self.header_pos + DebugpyMessageQueue.HEADER_LENGTH
                self.separator_pos = self.tcp_buffer.find(DebugpyMessageQueue.SEPARATOR, hint)
            if self.separator_pos == -1:
                return

            self.log.debug("QUEUE - found separator at pos %i", self.separator_pos)

            if self.message_pos == -1:
                size_pos = self.header_pos + DebugpyMessageQueue.HEADER_LENGTH
                self.message_pos = self.separator_pos + DebugpyMessageQueue.SEPARATOR_LENGTH
                self.message_size = int(self.tcp_buffer[size_pos : self.separator_pos])

            self.log.debug("QUEUE - found message at pos %i", self.message_pos)
            self.log.debug("QUEUE - message size is %i", self.message_size)

            if len(self.tcp_buffer) - self.message_pos < self.message_size:
                return

            self._put_message(
                self.tcp_buffer[self.message_pos : self.message_pos + self.message_size]
            )
            if len(self.tcp_buffer) - self.message_pos == self.message_size:
                self.log.debug("QUEUE - resetting tcp_buffer")
                self.tcp_buffer = ""
                self._reset_tcp_pos()
                return

            self.tcp_buffer = self.tcp_buffer[self.message_pos + self.message_size :]
            self.log.debug("QUEUE - slicing tcp_buffer: %s", self.tcp_buffer)
            self._reset_tcp_pos()

    async def get_message(self):
        """Get a message from the queue."""
        return await self.message_queue.get()


class DebugpyClient:
    """A client for debugpy."""

    def __init__(self, log, debugpy_stream, event_callback):
        """Initialize the client."""
        self.log = log
        self.debugpy_stream = debugpy_stream
        self.event_callback = event_callback
        self.message_queue = DebugpyMessageQueue(self._forward_event, self.log)
        self.debugpy_host = "127.0.0.1"
        self.debugpy_port = -1
        self.routing_id = None
        self.wait_for_attach = True
        self.init_event = Event()
        self.init_event_seq = -1

    def _get_endpoint(self):
        host, port = self.get_host_port()
        return "tcp://" + host + ":" + str(port)

    def _forward_event(self, msg):
        if msg["event"] == "initialized":
            self.init_event.set()
            self.init_event_seq = msg["seq"]
        self.event_callback(msg)

    def _send_request(self, msg):
        if self.routing_id is None:
            self.routing_id = self.debugpy_stream.socket.getsockopt(ROUTING_ID)
        content = jsonapi.dumps(
            msg,
            default=json_default,
            ensure_ascii=False,
            allow_nan=False,
        )
        content_length = str(len(content))
        buf = (DebugpyMessageQueue.HEADER + content_length + DebugpyMessageQueue.SEPARATOR).encode(
            "ascii"
        )
        buf += content
        self.log.debug("DEBUGPYCLIENT:")
        self.log.debug(self.routing_id)
        self.log.debug(buf)
        self.debugpy_stream.send_multipart((self.routing_id, buf))

    async def _wait_for_response(self):
        # Since events are never pushed to the message_queue
        # we can safely assume the next message in queue
        # will be an answer to the previous request
        return await self.message_queue.get_message()

    async def _handle_init_sequence(self):
        # 1] Waits for initialized event
        await self.init_event.wait()

        # 2] Sends configurationDone request
        configurationDone = {
            "type": "request",
            "seq": int(self.init_event_seq) + 1,
            "command": "configurationDone",
        }
        self._send_request(configurationDone)

        # 3]  Waits for configurationDone response
        await self._wait_for_response()

        # 4] Waits for attachResponse and returns it
        return await self._wait_for_response()

    def get_host_port(self):
        """Get the host debugpy port."""
        if self.debugpy_port == -1:
            socket = self.debugpy_stream.socket
            socket.bind_to_random_port("tcp://" + self.debugpy_host)
            self.endpoint = socket.getsockopt(zmq.LAST_ENDPOINT).decode("utf-8")
            socket.unbind(self.endpoint)
            index = self.endpoint.rfind(":")
            self.debugpy_port = self.endpoint[index + 1 :]
        return self.debugpy_host, self.debugpy_port

    def connect_tcp_socket(self):
        """Connect to the tcp socket."""
        self.debugpy_stream.socket.connect(self._get_endpoint())
        self.routing_id = self.debugpy_stream.socket.getsockopt(ROUTING_ID)

    def disconnect_tcp_socket(self):
        """Disconnect from the tcp socket."""
        self.debugpy_stream.socket.disconnect(self._get_endpoint())
        self.routing_id = None
        self.init_event = Event()
        self.init_event_seq = -1
        self.wait_for_attach = True

    def receive_dap_frame(self, frame):
        """Receive a dap frame."""
        self.message_queue.put_tcp_frame(frame)

    async def send_dap_request(self, msg):
        """Send a dap request."""
        self._send_request(msg)
        if self.wait_for_attach and msg["command"] == "attach":
            rep = await self._handle_init_sequence()
            self.wait_for_attach = False
            return rep

        rep = await self._wait_for_response()
        self.log.debug("DEBUGPYCLIENT - returning:")
        self.log.debug(rep)
        return rep


class Debugger:
    """The debugger class."""

    # Requests that requires that the debugger has started
    started_debug_msg_types = [
        "dumpCell",
        "setBreakpoints",
        "source",
        "stackTrace",
        "variables",
        "attach",
        "configurationDone",
    ]

    # Requests that can be handled even if the debugger is not running
    static_debug_msg_types = [
        "debugInfo",
        "inspectVariables",
        "richInspectVariables",
        "modules",
        "copyToGlobals",
    ]

    def __init__(
        self, log, debugpy_stream, event_callback, shell_socket, session, just_my_code=True
    ):
        """Initialize the debugger."""
        self.log = log
        self.debugpy_client = DebugpyClient(log, debugpy_stream, self._handle_event)
        self.shell_socket = shell_socket
        self.session = session
        self.is_started = False
        self.event_callback = event_callback
        self.just_my_code = just_my_code
        self.stopped_queue: Queue[t.Any] = Queue()

        self.started_debug_handlers = {}
        for msg_type in Debugger.started_debug_msg_types:
            self.started_debug_handlers[msg_type] = getattr(self, msg_type)

        self.static_debug_handlers = {}
        for msg_type in Debugger.static_debug_msg_types:
            self.static_debug_handlers[msg_type] = getattr(self, msg_type)

        self.breakpoint_list = {}
        self.stopped_threads = set()

        self.debugpy_initialized = False
        self._removed_cleanup = {}

        self.debugpy_host = "127.0.0.1"
        self.debugpy_port = 0
        self.endpoint = None

        self.variable_explorer = VariableExplorer()

    def _handle_event(self, msg):
        if msg["event"] == "stopped":
            if msg["body"]["allThreadsStopped"]:
                self.stopped_queue.put_nowait(msg)
                # Do not forward the event now, will be done in the handle_stopped_event
                return
            self.stopped_threads.add(msg["body"]["threadId"])
            self.event_callback(msg)
        elif msg["event"] == "continued":
            if msg["body"]["allThreadsContinued"]:
                self.stopped_threads = set()
            else:
                self.stopped_threads.remove(msg["body"]["threadId"])
            self.event_callback(msg)
        else:
            self.event_callback(msg)

    async def _forward_message(self, msg):
        return await self.debugpy_client.send_dap_request(msg)

    def _build_variables_response(self, request, variables):
        var_list = [var for var in variables if self.accept_variable(var["name"])]
        return {
            "seq": request["seq"],
            "type": "response",
            "request_seq": request["seq"],
            "success": True,
            "command": request["command"],
            "body": {"variables": var_list},
        }

    def _accept_stopped_thread(self, thread_name):
        # TODO: identify Thread-2, Thread-3 and Thread-4. These are NOT
        # Control, IOPub or Heartbeat threads
        forbid_list = ["IPythonHistorySavingThread", "Thread-2", "Thread-3", "Thread-4"]
        return thread_name not in forbid_list

    async def handle_stopped_event(self):
        """Handle a stopped event."""
        # Wait for a stopped event message in the stopped queue
        # This message is used for triggering the 'threads' request
        event = await self.stopped_queue.get()
        req = {"seq": event["seq"] + 1, "type": "request", "command": "threads"}
        rep = await self._forward_message(req)
        for thread in rep["body"]["threads"]:
            if self._accept_stopped_thread(thread["name"]):
                self.stopped_threads.add(thread["id"])
        self.event_callback(event)

    @property
    def tcp_client(self):
        return self.debugpy_client

    def start(self):
        """Start the debugger."""
        if not self.debugpy_initialized:
            tmp_dir = get_tmp_directory()
            if not Path(tmp_dir).exists():
                Path(tmp_dir).mkdir(parents=True)
            host, port = self.debugpy_client.get_host_port()
            code = "import debugpy;"
            code += 'debugpy.listen(("' + host + '",' + port + "))"
            content = {"code": code, "silent": True}
            self.session.send(
                self.shell_socket,
                "execute_request",
                content,
                None,
                (self.shell_socket.getsockopt(ROUTING_ID)),
            )

            ident, msg = self.session.recv(self.shell_socket, mode=0)
            self.debugpy_initialized = msg["content"]["status"] == "ok"

        # Don't remove leading empty lines when debugging so the breakpoints are correctly positioned
        cleanup_transforms = get_ipython().input_transformer_manager.cleanup_transforms
        if leading_empty_lines in cleanup_transforms:
            index = cleanup_transforms.index(leading_empty_lines)
            self._removed_cleanup[index] = cleanup_transforms.pop(index)

        self.debugpy_client.connect_tcp_socket()
        return self.debugpy_initialized

    def stop(self):
        """Stop the debugger."""
        self.debugpy_client.disconnect_tcp_socket()

        # Restore remove cleanup transformers
        cleanup_transforms = get_ipython().input_transformer_manager.cleanup_transforms
        for index in sorted(self._removed_cleanup):
            func = self._removed_cleanup.pop(index)
            cleanup_transforms.insert(index, func)

    async def dumpCell(self, message):
        """Handle a dump cell message."""
        code = message["arguments"]["code"]
        file_name = get_file_name(code)

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(code)

        return {
            "type": "response",
            "request_seq": message["seq"],
            "success": True,
            "command": message["command"],
            "body": {"sourcePath": file_name},
        }

    async def setBreakpoints(self, message):
        """Handle a set breakpoints message."""
        source = message["arguments"]["source"]["path"]
        self.breakpoint_list[source] = message["arguments"]["breakpoints"]
        message_response = await self._forward_message(message)
        # debugpy can set breakpoints on different lines than the ones requested,
        # so we want to record the breakpoints that were actually added
        if message_response.get("success"):
            self.breakpoint_list[source] = [
                {"line": breakpoint["line"]}
                for breakpoint in message_response["body"]["breakpoints"]
            ]
        return message_response

    async def source(self, message):
        """Handle a source message."""
        reply = {"type": "response", "request_seq": message["seq"], "command": message["command"]}
        source_path = message["arguments"]["source"]["path"]
        if Path(source_path).is_file():
            with open(source_path, encoding="utf-8") as f:
                reply["success"] = True
                reply["body"] = {"content": f.read()}
        else:
            reply["success"] = False
            reply["message"] = "source unavailable"
            reply["body"] = {}

        return reply

    async def stackTrace(self, message):
        """Handle a stack trace message."""
        reply = await self._forward_message(message)
        # The stackFrames array can have the following content:
        # { frames from the notebook}
        # ...
        # { 'id': xxx, 'name': '<module>', ... } <= this is the first frame of the code from the notebook
        # { frames from ipykernel }
        # ...
        # {'id': yyy, 'name': '<module>', ... } <= this is the first frame of ipykernel code
        # or only the frames from the notebook.
        # We want to remove all the frames from ipykernel when they are present.
        try:
            sf_list = reply["body"]["stackFrames"]
            module_idx = len(sf_list) - next(
                i for i, v in enumerate(reversed(sf_list), 1) if v["name"] == "<module>" and i != 1
            )
            reply["body"]["stackFrames"] = reply["body"]["stackFrames"][: module_idx + 1]
        except StopIteration:
            pass
        return reply

    def accept_variable(self, variable_name):
        """Accept a variable by name."""
        forbid_list = [
            "__name__",
            "__doc__",
            "__package__",
            "__loader__",
            "__spec__",
            "__annotations__",
            "__builtins__",
            "__builtin__",
            "__display__",
            "get_ipython",
            "debugpy",
            "exit",
            "quit",
            "In",
            "Out",
            "_oh",
            "_dh",
            "_",
            "__",
            "___",
        ]
        cond = variable_name not in forbid_list
        cond = cond and not bool(re.search(r"^_\d", variable_name))
        cond = cond and variable_name[0:2] != "_i"
        return cond  # noqa: RET504

    async def variables(self, message):
        """Handle a variables message."""
        reply = {}
        if not self.stopped_threads:
            variables = self.variable_explorer.get_children_variables(
                message["arguments"]["variablesReference"]
            )
            return self._build_variables_response(message, variables)

        reply = await self._forward_message(message)
        # TODO : check start and count arguments work as expected in debugpy
        reply["body"]["variables"] = [
            var for var in reply["body"]["variables"] if self.accept_variable(var["name"])
        ]
        return reply

    async def attach(self, message):
        """Handle an attach message."""
        host, port = self.debugpy_client.get_host_port()
        message["arguments"]["connect"] = {"host": host, "port": port}
        message["arguments"]["logToFile"] = True
        # Experimental option to break in non-user code.
        # The ipykernel source is in the call stack, so the user
        # has to manipulate the step-over and step-into in a wize way.
        # Set debugOptions for breakpoints in python standard library source.
        if not self.just_my_code:
            message["arguments"]["debugOptions"] = ["DebugStdLib"]
        return await self._forward_message(message)

    async def configurationDone(self, message):
        """Handle a configuration done message."""
        return {
            "seq": message["seq"],
            "type": "response",
            "request_seq": message["seq"],
            "success": True,
            "command": message["command"],
        }

    async def debugInfo(self, message):
        """Handle a debug info message."""
        breakpoint_list = []
        for key, value in self.breakpoint_list.items():
            breakpoint_list.append({"source": key, "breakpoints": value})
        return {
            "type": "response",
            "request_seq": message["seq"],
            "success": True,
            "command": message["command"],
            "body": {
                "isStarted": self.is_started,
                "hashMethod": "Murmur2",
                "hashSeed": get_tmp_hash_seed(),
                "tmpFilePrefix": get_tmp_directory() + os.sep,
                "tmpFileSuffix": ".py",
                "breakpoints": breakpoint_list,
                "stoppedThreads": list(self.stopped_threads),
                "richRendering": True,
                "exceptionPaths": ["Python Exceptions"],
                "copyToGlobals": True,
            },
        }

    async def inspectVariables(self, message):
        """Handle an inspect variables message."""
        self.variable_explorer.untrack_all()
        # looks like the implementation of untrack_all in ptvsd
        # destroys objects we nee din track. We have no choice but
        # reinstantiate the object
        self.variable_explorer = VariableExplorer()
        self.variable_explorer.track()
        variables = self.variable_explorer.get_children_variables()
        return self._build_variables_response(message, variables)

    async def richInspectVariables(self, message):
        """Handle a rich inspect variables message."""
        reply = {
            "type": "response",
            "sequence_seq": message["seq"],
            "success": False,
            "command": message["command"],
        }

        var_name = message["arguments"]["variableName"]
        valid_name = str.isidentifier(var_name)
        if not valid_name:
            reply["body"] = {"data": {}, "metadata": {}}
            if var_name == "special variables" or var_name == "function variables":
                reply["success"] = True
            return reply

        repr_data = {}
        repr_metadata = {}
        if not self.stopped_threads:
            # The code did not hit a breakpoint, we use the interpreter
            # to get the rich representation of the variable
            result = get_ipython().user_expressions({var_name: var_name})[var_name]
            if result.get("status", "error") == "ok":
                repr_data = result.get("data", {})
                repr_metadata = result.get("metadata", {})
        else:
            # The code has stopped on a breakpoint, we use the setExpression
            # request to get the rich representation of the variable
            code = f"get_ipython().display_formatter.format({var_name})"
            frame_id = message["arguments"]["frameId"]
            seq = message["seq"]
            reply = await self._forward_message(
                {
                    "type": "request",
                    "command": "evaluate",
                    "seq": seq + 1,
                    "arguments": {"expression": code, "frameId": frame_id, "context": "clipboard"},
                }
            )
            if reply["success"]:
                repr_data, repr_metadata = eval(reply["body"]["result"], {}, {})

        body = {
            "data": repr_data,
            "metadata": {k: v for k, v in repr_metadata.items() if k in repr_data},
        }

        reply["body"] = body
        reply["success"] = True
        return reply

    async def copyToGlobals(self, message):
        dst_var_name = message["arguments"]["dstVariableName"]
        src_var_name = message["arguments"]["srcVariableName"]
        src_frame_id = message["arguments"]["srcFrameId"]

        expression = f"globals()['{dst_var_name}']"
        seq = message["seq"]
        return await self._forward_message(
            {
                "type": "request",
                "command": "setExpression",
                "seq": seq + 1,
                "arguments": {
                    "expression": expression,
                    "value": src_var_name,
                    "frameId": src_frame_id,
                },
            }
        )

    async def modules(self, message):
        """Handle a modules message."""
        modules = list(sys.modules.values())
        startModule = message.get("startModule", 0)
        moduleCount = message.get("moduleCount", len(modules))
        mods = []
        for i in range(startModule, moduleCount):
            module = modules[i]
            filename = getattr(getattr(module, "__spec__", None), "origin", None)
            if filename and filename.endswith(".py"):
                mods.append({"id": i, "name": module.__name__, "path": filename})

        return {"body": {"modules": mods, "totalModules": len(modules)}}

    async def process_request(self, message):
        """Process a request."""
        reply = {}

        if message["command"] == "initialize":
            if self.is_started:
                self.log.info("The debugger has already started")
            else:
                self.is_started = self.start()
                if self.is_started:
                    self.log.info("The debugger has started")
                else:
                    reply = {
                        "command": "initialize",
                        "request_seq": message["seq"],
                        "seq": 3,
                        "success": False,
                        "type": "response",
                    }

        handler = self.static_debug_handlers.get(message["command"], None)
        if handler is not None:
            reply = await handler(message)
        elif self.is_started:
            handler = self.started_debug_handlers.get(message["command"], None)
            if handler is not None:
                reply = await handler(message)
            else:
                reply = await self._forward_message(message)

        if message["command"] == "disconnect":
            self.stop()
            self.breakpoint_list = {}
            self.stopped_threads = set()
            self.is_started = False
            self.log.info("The debugger has stopped")

        return reply

# === NexusCore/openenv\Lib\site-packages\regex\regex.py ===
#
# Secret Labs' Regular Expression Engine
#
# Copyright (c) 1998-2001 by Secret Labs AB.  All rights reserved.
#
# This version of the SRE library can be redistributed under CNRI's
# Python 1.6 license.  For any other use, please contact Secret Labs
# AB (info@pythonware.com).
#
# Portions of this engine have been developed in cooperation with
# CNRI.  Hewlett-Packard provided funding for 1.6 integration and
# other compatibility work.
#
# 2010-01-16 mrab Python front-end re-written and extended

r"""Support for regular expressions (RE).

This module provides regular expression matching operations similar to those
found in Perl. It supports both 8-bit and Unicode strings; both the pattern and
the strings being processed can contain null bytes and characters outside the
US ASCII range.

Regular expressions can contain both special and ordinary characters. Most
ordinary characters, like "A", "a", or "0", are the simplest regular
expressions; they simply match themselves. You can concatenate ordinary
characters, so last matches the string 'last'.

There are a few differences between the old (legacy) behaviour and the new
(enhanced) behaviour, which are indicated by VERSION0 or VERSION1.

The special characters are:
    "."                 Matches any character except a newline.
    "^"                 Matches the start of the string.
    "$"                 Matches the end of the string or just before the
                        newline at the end of the string.
    "*"                 Matches 0 or more (greedy) repetitions of the preceding
                        RE. Greedy means that it will match as many repetitions
                        as possible.
    "+"                 Matches 1 or more (greedy) repetitions of the preceding
                        RE.
    "?"                 Matches 0 or 1 (greedy) of the preceding RE.
    *?,+?,??            Non-greedy versions of the previous three special
                        characters.
    *+,++,?+            Possessive versions of the previous three special
                        characters.
    {m,n}               Matches from m to n repetitions of the preceding RE.
    {m,n}?              Non-greedy version of the above.
    {m,n}+              Possessive version of the above.
    {...}               Fuzzy matching constraints.
    "\\"                Either escapes special characters or signals a special
                        sequence.
    [...]               Indicates a set of characters. A "^" as the first
                        character indicates a complementing set.
    "|"                 A|B, creates an RE that will match either A or B.
    (...)               Matches the RE inside the parentheses. The contents are
                        captured and can be retrieved or matched later in the
                        string.
    (?flags-flags)      VERSION1: Sets/clears the flags for the remainder of
                        the group or pattern; VERSION0: Sets the flags for the
                        entire pattern.
    (?:...)             Non-capturing version of regular parentheses.
    (?>...)             Atomic non-capturing version of regular parentheses.
    (?flags-flags:...)  Non-capturing version of regular parentheses with local
                        flags.
    (?P<name>...)       The substring matched by the group is accessible by
                        name.
    (?<name>...)        The substring matched by the group is accessible by
                        name.
    (?P=name)           Matches the text matched earlier by the group named
                        name.
    (?#...)             A comment; ignored.
    (?=...)             Matches if ... matches next, but doesn't consume the
                        string.
    (?!...)             Matches if ... doesn't match next.
    (?<=...)            Matches if preceded by ....
    (?<!...)            Matches if not preceded by ....
    (?(id)yes|no)       Matches yes pattern if group id matched, the (optional)
                        no pattern otherwise.
    (?(DEFINE)...)      If there's no group called "DEFINE", then ... will be
                        ignored, but any group definitions will be available.
    (?|...|...)         (?|A|B), creates an RE that will match either A or B,
                        but reuses capture group numbers across the
                        alternatives.
    (*FAIL)             Forces matching to fail, which means immediate
                        backtracking.
    (*F)                Abbreviation for (*FAIL).
    (*PRUNE)            Discards the current backtracking information. Its
                        effect doesn't extend outside an atomic group or a
                        lookaround.
    (*SKIP)             Similar to (*PRUNE), except that it also sets where in
                        the text the next attempt at matching the entire
                        pattern will start. Its effect doesn't extend outside
                        an atomic group or a lookaround.

The fuzzy matching constraints are: "i" to permit insertions, "d" to permit
deletions, "s" to permit substitutions, "e" to permit any of these. Limits are
optional with "<=" and "<". If any type of error is provided then any type not
provided is not permitted.

A cost equation may be provided.

Examples:
    (?:fuzzy){i<=2}
    (?:fuzzy){i<=1,s<=2,d<=1,1i+1s+1d<3}

VERSION1: Set operators are supported, and a set can include nested sets. The
set operators, in order of increasing precedence, are:
    ||  Set union ("x||y" means "x or y").
    ~~  (double tilde) Symmetric set difference ("x~~y" means "x or y, but not
        both").
    &&  Set intersection ("x&&y" means "x and y").
    --  (double dash) Set difference ("x--y" means "x but not y").

Implicit union, ie, simple juxtaposition like in [ab], has the highest
precedence.

VERSION0 and VERSION1:
The special sequences consist of "\\" and a character from the list below. If
the ordinary character is not on the list, then the resulting RE will match the
second character.
    \number         Matches the contents of the group of the same number if
                    number is no more than 2 digits, otherwise the character
                    with the 3-digit octal code.
    \a              Matches the bell character.
    \A              Matches only at the start of the string.
    \b              Matches the empty string, but only at the start or end of a
                    word.
    \B              Matches the empty string, but not at the start or end of a
                    word.
    \d              Matches any decimal digit; equivalent to the set [0-9] when
                    matching a bytestring or a Unicode string with the ASCII
                    flag, or the whole range of Unicode digits when matching a
                    Unicode string.
    \D              Matches any non-digit character; equivalent to [^\d].
    \f              Matches the formfeed character.
    \g<name>        Matches the text matched by the group named name.
    \G              Matches the empty string, but only at the position where
                    the search started.
    \h              Matches horizontal whitespace.
    \K              Keeps only what follows for the entire match.
    \L<name>        Named list. The list is provided as a keyword argument.
    \m              Matches the empty string, but only at the start of a word.
    \M              Matches the empty string, but only at the end of a word.
    \n              Matches the newline character.
    \N{name}        Matches the named character.
    \p{name=value}  Matches the character if its property has the specified
                    value.
    \P{name=value}  Matches the character if its property hasn't the specified
                    value.
    \r              Matches the carriage-return character.
    \s              Matches any whitespace character; equivalent to
                    [ \t\n\r\f\v].
    \S              Matches any non-whitespace character; equivalent to [^\s].
    \t              Matches the tab character.
    \uXXXX          Matches the Unicode codepoint with 4-digit hex code XXXX.
    \UXXXXXXXX      Matches the Unicode codepoint with 8-digit hex code
                    XXXXXXXX.
    \v              Matches the vertical tab character.
    \w              Matches any alphanumeric character; equivalent to
                    [a-zA-Z0-9_] when matching a bytestring or a Unicode string
                    with the ASCII flag, or the whole range of Unicode
                    alphanumeric characters (letters plus digits plus
                    underscore) when matching a Unicode string. With LOCALE, it
                    will match the set [0-9_] plus characters defined as
                    letters for the current locale.
    \W              Matches the complement of \w; equivalent to [^\w].
    \xXX            Matches the character with 2-digit hex code XX.
    \X              Matches a grapheme.
    \Z              Matches only at the end of the string.
    \\              Matches a literal backslash.

This module exports the following functions:
    match      Match a regular expression pattern at the beginning of a string.
    fullmatch  Match a regular expression pattern against all of a string.
    search     Search a string for the presence of a pattern.
    sub        Substitute occurrences of a pattern found in a string using a
               template string.
    subf       Substitute occurrences of a pattern found in a string using a
               format string.
    subn       Same as sub, but also return the number of substitutions made.
    subfn      Same as subf, but also return the number of substitutions made.
    split      Split a string by the occurrences of a pattern. VERSION1: will
               split at zero-width match; VERSION0: won't split at zero-width
               match.
    splititer  Return an iterator yielding the parts of a split string.
    findall    Find all occurrences of a pattern in a string.
    finditer   Return an iterator yielding a match object for each match.
    compile    Compile a pattern into a Pattern object.
    purge      Clear the regular expression cache.
    escape     Backslash all non-alphanumerics or special characters in a
               string.

Most of the functions support a concurrent parameter: if True, the GIL will be
released during matching, allowing other Python threads to run concurrently. If
the string changes during matching, the behaviour is undefined. This parameter
is not needed when working on the builtin (immutable) string classes.

Some of the functions in this module take flags as optional parameters. Most of
these flags can also be set within an RE:
    A   a   ASCII         Make \w, \W, \b, \B, \d, and \D match the
                          corresponding ASCII character categories. Default
                          when matching a bytestring.
    B   b   BESTMATCH     Find the best fuzzy match (default is first).
    D       DEBUG         Print the parsed pattern.
    E   e   ENHANCEMATCH  Attempt to improve the fit after finding the first
                          fuzzy match.
    F   f   FULLCASE      Use full case-folding when performing
                          case-insensitive matching in Unicode.
    I   i   IGNORECASE    Perform case-insensitive matching.
    L   L   LOCALE        Make \w, \W, \b, \B, \d, and \D dependent on the
                          current locale. (One byte per character only.)
    M   m   MULTILINE     "^" matches the beginning of lines (after a newline)
                          as well as the string. "$" matches the end of lines
                          (before a newline) as well as the end of the string.
    P   p   POSIX         Perform POSIX-standard matching (leftmost longest).
    R   r   REVERSE       Searches backwards.
    S   s   DOTALL        "." matches any character at all, including the
                          newline.
    U   u   UNICODE       Make \w, \W, \b, \B, \d, and \D dependent on the
                          Unicode locale. Default when matching a Unicode
                          string.
    V0  V0  VERSION0      Turn on the old legacy behaviour.
    V1  V1  VERSION1      Turn on the new enhanced behaviour. This flag
                          includes the FULLCASE flag.
    W   w   WORD          Make \b and \B work with default Unicode word breaks
                          and make ".", "^" and "$" work with Unicode line
                          breaks.
    X   x   VERBOSE       Ignore whitespace and comments for nicer looking REs.

This module also defines an exception 'error'.

"""

# Public symbols.
__all__ = ["cache_all", "compile", "DEFAULT_VERSION", "escape", "findall",
  "finditer", "fullmatch", "match", "purge", "search", "split", "splititer",
  "sub", "subf", "subfn", "subn", "template", "Scanner", "A", "ASCII", "B",
  "BESTMATCH", "D", "DEBUG", "E", "ENHANCEMATCH", "S", "DOTALL", "F",
  "FULLCASE", "I", "IGNORECASE", "L", "LOCALE", "M", "MULTILINE", "P", "POSIX",
  "R", "REVERSE", "T", "TEMPLATE", "U", "UNICODE", "V0", "VERSION0", "V1",
  "VERSION1", "X", "VERBOSE", "W", "WORD", "error", "Regex", "__version__",
  "__doc__", "RegexFlag"]

__version__ = "2.5.148"

# --------------------------------------------------------------------
# Public interface.

def match(pattern, string, flags=0, pos=None, endpos=None, partial=False,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Try to apply the pattern at the start of the string, returning a match
    object, or None if no match was found."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.match(string, pos, endpos, concurrent, partial, timeout)

def fullmatch(pattern, string, flags=0, pos=None, endpos=None, partial=False,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Try to apply the pattern against all of the string, returning a match
    object, or None if no match was found."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.fullmatch(string, pos, endpos, concurrent, partial, timeout)

def search(pattern, string, flags=0, pos=None, endpos=None, partial=False,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Search through string looking for a match to the pattern, returning a
    match object, or None if no match was found."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.search(string, pos, endpos, concurrent, partial, timeout)

def sub(pattern, repl, string, count=0, flags=0, pos=None, endpos=None,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return the string obtained by replacing the leftmost (or rightmost with a
    reverse pattern) non-overlapping occurrences of the pattern in string by the
    replacement repl. repl can be either a string or a callable; if a string,
    backslash escapes in it are processed; if a callable, it's passed the match
    object and must return a replacement string to be used."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.sub(repl, string, count, pos, endpos, concurrent, timeout)

def subf(pattern, format, string, count=0, flags=0, pos=None, endpos=None,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return the string obtained by replacing the leftmost (or rightmost with a
    reverse pattern) non-overlapping occurrences of the pattern in string by the
    replacement format. format can be either a string or a callable; if a string,
    it's treated as a format string; if a callable, it's passed the match object
    and must return a replacement string to be used."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.subf(format, string, count, pos, endpos, concurrent, timeout)

def subn(pattern, repl, string, count=0, flags=0, pos=None, endpos=None,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return a 2-tuple containing (new_string, number). new_string is the string
    obtained by replacing the leftmost (or rightmost with a reverse pattern)
    non-overlapping occurrences of the pattern in the source string by the
    replacement repl. number is the number of substitutions that were made. repl
    can be either a string or a callable; if a string, backslash escapes in it
    are processed; if a callable, it's passed the match object and must return a
    replacement string to be used."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.subn(repl, string, count, pos, endpos, concurrent, timeout)

def subfn(pattern, format, string, count=0, flags=0, pos=None, endpos=None,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return a 2-tuple containing (new_string, number). new_string is the string
    obtained by replacing the leftmost (or rightmost with a reverse pattern)
    non-overlapping occurrences of the pattern in the source string by the
    replacement format. number is the number of substitutions that were made. format
    can be either a string or a callable; if a string, it's treated as a format
    string; if a callable, it's passed the match object and must return a
    replacement string to be used."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.subfn(format, string, count, pos, endpos, concurrent, timeout)

def split(pattern, string, maxsplit=0, flags=0, concurrent=None, timeout=None,
  ignore_unused=False, **kwargs):
    """Split the source string by the occurrences of the pattern, returning a
    list containing the resulting substrings.  If capturing parentheses are used
    in pattern, then the text of all groups in the pattern are also returned as
    part of the resulting list.  If maxsplit is nonzero, at most maxsplit splits
    occur, and the remainder of the string is returned as the final element of
    the list."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.split(string, maxsplit, concurrent, timeout)

def splititer(pattern, string, maxsplit=0, flags=0, concurrent=None,
  timeout=None, ignore_unused=False, **kwargs):
    "Return an iterator yielding the parts of a split string."
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.splititer(string, maxsplit, concurrent, timeout)

def findall(pattern, string, flags=0, pos=None, endpos=None, overlapped=False,
  concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return a list of all matches in the string. The matches may be overlapped
    if overlapped is True. If one or more groups are present in the pattern,
    return a list of groups; this will be a list of tuples if the pattern has
    more than one group. Empty matches are included in the result."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.findall(string, pos, endpos, overlapped, concurrent, timeout)

def finditer(pattern, string, flags=0, pos=None, endpos=None, overlapped=False,
  partial=False, concurrent=None, timeout=None, ignore_unused=False, **kwargs):
    """Return an iterator over all matches in the string. The matches may be
    overlapped if overlapped is True. For each match, the iterator returns a
    match object. Empty matches are included in the result."""
    pat = _compile(pattern, flags, ignore_unused, kwargs, True)
    return pat.finditer(string, pos, endpos, overlapped, concurrent, partial,
      timeout)

def compile(pattern, flags=0, ignore_unused=False, cache_pattern=None, **kwargs):
    "Compile a regular expression pattern, returning a pattern object."
    if cache_pattern is None:
        cache_pattern = _cache_all
    return _compile(pattern, flags, ignore_unused, kwargs, cache_pattern)

def purge():
    "Clear the regular expression cache"
    _cache.clear()
    _locale_sensitive.clear()

# Whether to cache all patterns.
_cache_all = True

def cache_all(value=True):
    """Sets whether to cache all patterns, even those are compiled explicitly.
    Passing None has no effect, but returns the current setting."""
    global _cache_all

    if value is None:
        return _cache_all

    _cache_all = value

def template(pattern, flags=0):
    "Compile a template pattern, returning a pattern object."
    return _compile(pattern, flags | TEMPLATE, False, {}, False)

def escape(pattern, special_only=True, literal_spaces=False):
    """Escape a string for use as a literal in a pattern. If special_only is
    True, escape only special characters, else escape all non-alphanumeric
    characters. If literal_spaces is True, don't escape spaces."""
    # Convert it to Unicode.
    if isinstance(pattern, bytes):
        p = pattern.decode("latin-1")
    else:
        p = pattern

    s = []
    if special_only:
        for c in p:
            if c == " " and literal_spaces:
                s.append(c)
            elif c in _METACHARS or c.isspace():
                s.append("\\")
                s.append(c)
            else:
                s.append(c)
    else:
        for c in p:
            if c == " " and literal_spaces:
                s.append(c)
            elif c in _ALNUM:
                s.append(c)
            else:
                s.append("\\")
                s.append(c)

    r = "".join(s)
    # Convert it back to bytes if necessary.
    if isinstance(pattern, bytes):
        r = r.encode("latin-1")

    return r

# --------------------------------------------------------------------
# Internals.

import regex._regex_core as _regex_core
import regex._regex as _regex
from threading import RLock as _RLock
from locale import getpreferredencoding as _getpreferredencoding
from regex._regex_core import *
from regex._regex_core import (_ALL_VERSIONS, _ALL_ENCODINGS, _FirstSetError,
  _UnscopedFlagSet, _check_group_features, _compile_firstset,
  _compile_replacement, _flatten_code, _fold_case, _get_required_string,
  _parse_pattern, _shrink_cache)
from regex._regex_core import (ALNUM as _ALNUM, Info as _Info, OP as _OP, Source
  as _Source, Fuzzy as _Fuzzy)

# Version 0 is the old behaviour, compatible with the original 're' module.
# Version 1 is the new behaviour, which differs slightly.

DEFAULT_VERSION = VERSION0

_METACHARS = frozenset("()[]{}?*+|^$\\.-#&~")

_regex_core.DEFAULT_VERSION = DEFAULT_VERSION

# Caches for the patterns and replacements.
_cache = {}
_cache_lock = _RLock()
_named_args = {}
_replacement_cache = {}
_locale_sensitive = {}

# Maximum size of the cache.
_MAXCACHE = 500
_MAXREPCACHE = 500

def _compile(pattern, flags, ignore_unused, kwargs, cache_it):
    "Compiles a regular expression to a PatternObject."

    global DEFAULT_VERSION
    try:
        from regex import DEFAULT_VERSION
    except ImportError:
        pass

    # We won't bother to cache the pattern if we're debugging.
    if (flags & DEBUG) != 0:
        cache_it = False

    # What locale is this pattern using?
    locale_key = (type(pattern), pattern)
    if _locale_sensitive.get(locale_key, True) or (flags & LOCALE) != 0:
        # This pattern is, or might be, locale-sensitive.
        pattern_locale = _getpreferredencoding()
    else:
        # This pattern is definitely not locale-sensitive.
        pattern_locale = None

    def complain_unused_args():
        if ignore_unused:
            return

        # Complain about any unused keyword arguments, possibly resulting from a typo.
        unused_kwargs = set(kwargs) - {k for k, v in args_needed}
        if unused_kwargs:
            any_one = next(iter(unused_kwargs))
            raise ValueError('unused keyword argument {!a}'.format(any_one))

    if cache_it:
        try:
            # Do we know what keyword arguments are needed?
            args_key = pattern, type(pattern), flags
            args_needed = _named_args[args_key]

            # Are we being provided with its required keyword arguments?
            args_supplied = set()
            if args_needed:
                for k, v in args_needed:
                    try:
                        args_supplied.add((k, frozenset(kwargs[k])))
                    except KeyError:
                        raise error("missing named list: {!r}".format(k))

            complain_unused_args()

            args_supplied = frozenset(args_supplied)

            # Have we already seen this regular expression and named list?
            pattern_key = (pattern, type(pattern), flags, args_supplied,
              DEFAULT_VERSION, pattern_locale)
            return _cache[pattern_key]
        except KeyError:
            # It's a new pattern, or new named list for a known pattern.
            pass

    # Guess the encoding from the class of the pattern string.
    if isinstance(pattern, str):
        guess_encoding = UNICODE
    elif isinstance(pattern, bytes):
        guess_encoding = ASCII
    elif isinstance(pattern, Pattern):
        if flags:
            raise ValueError("cannot process flags argument with a compiled pattern")

        return pattern
    else:
        raise TypeError("first argument must be a string or compiled pattern")

    # Set the default version in the core code in case it has been changed.
    _regex_core.DEFAULT_VERSION = DEFAULT_VERSION

    global_flags = flags

    while True:
        caught_exception = None
        try:
            source = _Source(pattern)
            info = _Info(global_flags, source.char_type, kwargs)
            info.guess_encoding = guess_encoding
            source.ignore_space = bool(info.flags & VERBOSE)
            parsed = _parse_pattern(source, info)
            break
        except _UnscopedFlagSet:
            # Remember the global flags for the next attempt.
            global_flags = info.global_flags
        except error as e:
            caught_exception = e

        if caught_exception:
            raise error(caught_exception.msg, caught_exception.pattern,
              caught_exception.pos)

    if not source.at_end():
        raise error("unbalanced parenthesis", pattern, source.pos)

    # Check the global flags for conflicts.
    version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION
    if version not in (0, VERSION0, VERSION1):
        raise ValueError("VERSION0 and VERSION1 flags are mutually incompatible")

    if (info.flags & _ALL_ENCODINGS) not in (0, ASCII, LOCALE, UNICODE):
        raise ValueError("ASCII, LOCALE and UNICODE flags are mutually incompatible")

    if isinstance(pattern, bytes) and (info.flags & UNICODE):
        raise ValueError("cannot use UNICODE flag with a bytes pattern")

    if not (info.flags & _ALL_ENCODINGS):
        if isinstance(pattern, str):
            info.flags |= UNICODE
        else:
            info.flags |= ASCII

    reverse = bool(info.flags & REVERSE)
    fuzzy = isinstance(parsed, _Fuzzy)

    # Remember whether this pattern as an inline locale flag.
    _locale_sensitive[locale_key] = info.inline_locale

    # Fix the group references.
    caught_exception = None
    try:
        parsed.fix_groups(pattern, reverse, False)
    except error as e:
        caught_exception = e

    if caught_exception:
        raise error(caught_exception.msg, caught_exception.pattern,
          caught_exception.pos)

    # Should we print the parsed pattern?
    if flags & DEBUG:
        parsed.dump(indent=0, reverse=reverse)

    # Optimise the parsed pattern.
    parsed = parsed.optimise(info, reverse)
    parsed = parsed.pack_characters(info)

    # Get the required string.
    req_offset, req_chars, req_flags = _get_required_string(parsed, info.flags)

    # Build the named lists.
    named_lists = {}
    named_list_indexes = [None] * len(info.named_lists_used)
    args_needed = set()
    for key, index in info.named_lists_used.items():
        name, case_flags = key
        values = frozenset(kwargs[name])
        if case_flags:
            items = frozenset(_fold_case(info, v) for v in values)
        else:
            items = values
        named_lists[name] = values
        named_list_indexes[index] = items
        args_needed.add((name, values))

    complain_unused_args()

    # Check the features of the groups.
    _check_group_features(info, parsed)

    # Compile the parsed pattern. The result is a list of tuples.
    code = parsed.compile(reverse)

    # Is there a group call to the pattern as a whole?
    key = (0, reverse, fuzzy)
    ref = info.call_refs.get(key)
    if ref is not None:
        code = [(_OP.CALL_REF, ref)] + code + [(_OP.END, )]

    # Add the final 'success' opcode.
    code += [(_OP.SUCCESS, )]

    # Compile the additional copies of the groups that we need.
    for group, rev, fuz in info.additional_groups:
        code += group.compile(rev, fuz)

    # Flatten the code into a list of ints.
    code = _flatten_code(code)

    if not parsed.has_simple_start():
        # Get the first set, if possible.
        try:
            fs_code = _compile_firstset(info, parsed.get_firstset(reverse))
            fs_code = _flatten_code(fs_code)
            code = fs_code + code
        except _FirstSetError:
            pass

    # The named capture groups.
    index_group = dict((v, n) for n, v in info.group_index.items())

    # Create the PatternObject.
    #
    # Local flags like IGNORECASE affect the code generation, but aren't needed
    # by the PatternObject itself. Conversely, global flags like LOCALE _don't_
    # affect the code generation but _are_ needed by the PatternObject.
    compiled_pattern = _regex.compile(pattern, info.flags | version, code,
      info.group_index, index_group, named_lists, named_list_indexes,
      req_offset, req_chars, req_flags, info.group_count)

    # Do we need to reduce the size of the cache?
    if len(_cache) >= _MAXCACHE:
        with _cache_lock:
            _shrink_cache(_cache, _named_args, _locale_sensitive, _MAXCACHE)

    if cache_it:
        if (info.flags & LOCALE) == 0:
            pattern_locale = None

        args_needed = frozenset(args_needed)

        # Store this regular expression and named list.
        pattern_key = (pattern, type(pattern), flags, args_needed,
          DEFAULT_VERSION, pattern_locale)
        _cache[pattern_key] = compiled_pattern

        # Store what keyword arguments are needed.
        _named_args[args_key] = args_needed

    return compiled_pattern

def _compile_replacement_helper(pattern, template):
    "Compiles a replacement template."
    # This function is called by the _regex module.

    # Have we seen this before?
    key = pattern.pattern, pattern.flags, template
    compiled = _replacement_cache.get(key)
    if compiled is not None:
        return compiled

    if len(_replacement_cache) >= _MAXREPCACHE:
        _replacement_cache.clear()

    is_unicode = isinstance(template, str)
    source = _Source(template)
    if is_unicode:
        def make_string(char_codes):
            return "".join(chr(c) for c in char_codes)
    else:
        def make_string(char_codes):
            return bytes(char_codes)

    compiled = []
    literal = []
    while True:
        ch = source.get()
        if not ch:
            break
        if ch == "\\":
            # '_compile_replacement' will return either an int group reference
            # or a string literal. It returns items (plural) in order to handle
            # a 2-character literal (an invalid escape sequence).
            is_group, items = _compile_replacement(source, pattern, is_unicode)
            if is_group:
                # It's a group, so first flush the literal.
                if literal:
                    compiled.append(make_string(literal))
                    literal = []
                compiled.extend(items)
            else:
                literal.extend(items)
        else:
            literal.append(ord(ch))

    # Flush the literal.
    if literal:
        compiled.append(make_string(literal))

    _replacement_cache[key] = compiled

    return compiled

# We define Pattern here after all the support objects have been defined.
_pat = _compile('', 0, False, {}, False)
Pattern = type(_pat)
Match = type(_pat.match(''))
del _pat

# Make Pattern public for typing annotations.
__all__.append("Pattern")
__all__.append("Match")

# We'll define an alias for the 'compile' function so that the repr of a
# pattern object is eval-able.
Regex = compile

# Register myself for pickling.
import copyreg as _copy_reg

def _pickle(pattern):
    return _regex.compile, pattern._pickled_data

_copy_reg.pickle(Pattern, _pickle)

# === NexusCore/openenv\Lib\site-packages\typer\core.py ===
import errno
import inspect
import os
import sys
from enum import Enum
from gettext import gettext as _
from typing import (
    Any,
    Callable,
    Dict,
    List,
    MutableMapping,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Union,
    cast,
)

import click
import click.core
import click.formatting
import click.parser
import click.shell_completion
import click.types
import click.utils

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

MarkupMode = Literal["markdown", "rich", None]

try:
    import rich

    from . import rich_utils

    DEFAULT_MARKUP_MODE: MarkupMode = "rich"

except ImportError:  # pragma: no cover
    rich = None  # type: ignore
    DEFAULT_MARKUP_MODE = None


# Copy from click.parser._split_opt
def _split_opt(opt: str) -> Tuple[str, str]:
    first = opt[:1]
    if first.isalnum():
        return "", opt
    if opt[1:2] == first:
        return opt[:2], opt[2:]
    return first, opt[1:]


def _typer_param_setup_autocompletion_compat(
    self: click.Parameter,
    *,
    autocompletion: Optional[
        Callable[[click.Context, List[str], str], List[Union[Tuple[str, str], str]]]
    ] = None,
) -> None:
    if autocompletion is not None and self._custom_shell_complete is None:
        import warnings

        warnings.warn(
            "'autocompletion' is renamed to 'shell_complete'. The old name is"
            " deprecated and will be removed in Click 8.1. See the docs about"
            " 'Parameter' for information about new behavior.",
            DeprecationWarning,
            stacklevel=2,
        )

        def compat_autocompletion(
            ctx: click.Context, param: click.core.Parameter, incomplete: str
        ) -> List["click.shell_completion.CompletionItem"]:
            from click.shell_completion import CompletionItem

            out = []

            for c in autocompletion(ctx, [], incomplete):
                if isinstance(c, tuple):
                    use_completion = CompletionItem(c[0], help=c[1])
                else:
                    assert isinstance(c, str)
                    use_completion = CompletionItem(c)

                if use_completion.value.startswith(incomplete):
                    out.append(use_completion)

            return out

        self._custom_shell_complete = compat_autocompletion


def _get_default_string(
    obj: Union["TyperArgument", "TyperOption"],
    *,
    ctx: click.Context,
    show_default_is_str: bool,
    default_value: Union[List[Any], Tuple[Any, ...], str, Callable[..., Any], Any],
) -> str:
    # Extracted from click.core.Option.get_help_record() to be reused by
    # rich_utils avoiding RegEx hacks
    if show_default_is_str:
        default_string = f"({obj.show_default})"
    elif isinstance(default_value, (list, tuple)):
        default_string = ", ".join(
            _get_default_string(
                obj, ctx=ctx, show_default_is_str=show_default_is_str, default_value=d
            )
            for d in default_value
        )
    elif isinstance(default_value, Enum):
        default_string = str(default_value.value)
    elif inspect.isfunction(default_value):
        default_string = _("(dynamic)")
    elif isinstance(obj, TyperOption) and obj.is_bool_flag and obj.secondary_opts:
        # For boolean flags that have distinct True/False opts,
        # use the opt without prefix instead of the value.
        # Typer override, original commented
        # default_string = click.parser.split_opt(
        #     (self.opts if self.default else self.secondary_opts)[0]
        # )[1]
        if obj.default:
            if obj.opts:
                default_string = _split_opt(obj.opts[0])[1]
            else:
                default_string = str(default_value)
        else:
            default_string = _split_opt(obj.secondary_opts[0])[1]
        # Typer override end
    elif (
        isinstance(obj, TyperOption)
        and obj.is_bool_flag
        and not obj.secondary_opts
        and not default_value
    ):
        default_string = ""
    else:
        default_string = str(default_value)
    return default_string


def _extract_default_help_str(
    obj: Union["TyperArgument", "TyperOption"], *, ctx: click.Context
) -> Optional[Union[Any, Callable[[], Any]]]:
    # Extracted from click.core.Option.get_help_record() to be reused by
    # rich_utils avoiding RegEx hacks
    # Temporarily enable resilient parsing to avoid type casting
    # failing for the default. Might be possible to extend this to
    # help formatting in general.
    resilient = ctx.resilient_parsing
    ctx.resilient_parsing = True

    try:
        default_value = obj.get_default(ctx, call=False)
    finally:
        ctx.resilient_parsing = resilient
    return default_value


def _main(
    self: click.Command,
    *,
    args: Optional[Sequence[str]] = None,
    prog_name: Optional[str] = None,
    complete_var: Optional[str] = None,
    standalone_mode: bool = True,
    windows_expand_args: bool = True,
    rich_markup_mode: MarkupMode = DEFAULT_MARKUP_MODE,
    **extra: Any,
) -> Any:
    # Typer override, duplicated from click.main() to handle custom rich exceptions
    # Verify that the environment is configured correctly, or reject
    # further execution to avoid a broken script.
    if args is None:
        args = sys.argv[1:]

        # Covered in Click tests
        if os.name == "nt" and windows_expand_args:  # pragma: no cover
            args = click.utils._expand_args(args)
    else:
        args = list(args)

    if prog_name is None:
        prog_name = click.utils._detect_program_name()

    # Process shell completion requests and exit early.
    self._main_shell_completion(extra, prog_name, complete_var)

    try:
        try:
            with self.make_context(prog_name, args, **extra) as ctx:
                rv = self.invoke(ctx)
                if not standalone_mode:
                    return rv
                # it's not safe to `ctx.exit(rv)` here!
                # note that `rv` may actually contain data like "1" which
                # has obvious effects
                # more subtle case: `rv=[None, None]` can come out of
                # chained commands which all returned `None` -- so it's not
                # even always obvious that `rv` indicates success/failure
                # by its truthiness/falsiness
                ctx.exit()
        except (EOFError, KeyboardInterrupt) as e:
            click.echo(file=sys.stderr)
            raise click.Abort() from e
        except click.ClickException as e:
            if not standalone_mode:
                raise
            # Typer override
            if rich and rich_markup_mode is not None:
                rich_utils.rich_format_error(e)
            else:
                e.show()
            # Typer override end
            sys.exit(e.exit_code)
        except OSError as e:
            if e.errno == errno.EPIPE:
                sys.stdout = cast(TextIO, click.utils.PacifyFlushWrapper(sys.stdout))
                sys.stderr = cast(TextIO, click.utils.PacifyFlushWrapper(sys.stderr))
                sys.exit(1)
            else:
                raise
    except click.exceptions.Exit as e:
        if standalone_mode:
            sys.exit(e.exit_code)
        else:
            # in non-standalone mode, return the exit code
            # note that this is only reached if `self.invoke` above raises
            # an Exit explicitly -- thus bypassing the check there which
            # would return its result
            # the results of non-standalone execution may therefore be
            # somewhat ambiguous: if there are codepaths which lead to
            # `ctx.exit(1)` and to `return 1`, the caller won't be able to
            # tell the difference between the two
            return e.exit_code
    except click.Abort:
        if not standalone_mode:
            raise
        # Typer override
        if rich and rich_markup_mode is not None:
            rich_utils.rich_abort_error()
        else:
            click.echo(_("Aborted!"), file=sys.stderr)
        # Typer override end
        sys.exit(1)


class TyperArgument(click.core.Argument):
    def __init__(
        self,
        *,
        # Parameter
        param_decls: List[str],
        type: Optional[Any] = None,
        required: Optional[bool] = None,
        default: Optional[Any] = None,
        callback: Optional[Callable[..., Any]] = None,
        nargs: Optional[int] = None,
        metavar: Optional[str] = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: Optional[Union[str, List[str]]] = None,
        shell_complete: Optional[
            Callable[
                [click.Context, click.Parameter, str],
                Union[List["click.shell_completion.CompletionItem"], List[str]],
            ]
        ] = None,
        autocompletion: Optional[Callable[..., Any]] = None,
        # TyperArgument
        show_default: Union[bool, str] = True,
        show_choices: bool = True,
        show_envvar: bool = True,
        help: Optional[str] = None,
        hidden: bool = False,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        self.help = help
        self.show_default = show_default
        self.show_choices = show_choices
        self.show_envvar = show_envvar
        self.hidden = hidden
        self.rich_help_panel = rich_help_panel

        super().__init__(
            param_decls=param_decls,
            type=type,
            required=required,
            default=default,
            callback=callback,
            nargs=nargs,
            metavar=metavar,
            expose_value=expose_value,
            is_eager=is_eager,
            envvar=envvar,
            shell_complete=shell_complete,
        )
        _typer_param_setup_autocompletion_compat(self, autocompletion=autocompletion)

    def _get_default_string(
        self,
        *,
        ctx: click.Context,
        show_default_is_str: bool,
        default_value: Union[List[Any], Tuple[Any, ...], str, Callable[..., Any], Any],
    ) -> str:
        return _get_default_string(
            self,
            ctx=ctx,
            show_default_is_str=show_default_is_str,
            default_value=default_value,
        )

    def _extract_default_help_str(
        self, *, ctx: click.Context
    ) -> Optional[Union[Any, Callable[[], Any]]]:
        return _extract_default_help_str(self, ctx=ctx)

    def get_help_record(self, ctx: click.Context) -> Optional[Tuple[str, str]]:
        # Modified version of click.core.Option.get_help_record()
        # to support Arguments
        if self.hidden:
            return None
        name = self.make_metavar()
        help = self.help or ""
        extra = []
        if self.show_envvar:
            envvar = self.envvar
            # allow_from_autoenv is currently not supported in Typer for CLI Arguments
            if envvar is not None:
                var_str = (
                    ", ".join(str(d) for d in envvar)
                    if isinstance(envvar, (list, tuple))
                    else envvar
                )
                extra.append(f"env var: {var_str}")

        # Typer override:
        # Extracted to _extract_default_help_str() to allow re-using it in rich_utils
        default_value = self._extract_default_help_str(ctx=ctx)
        # Typer override end

        show_default_is_str = isinstance(self.show_default, str)

        if show_default_is_str or (
            default_value is not None and (self.show_default or ctx.show_default)
        ):
            # Typer override:
            # Extracted to _get_default_string() to allow re-using it in rich_utils
            default_string = self._get_default_string(
                ctx=ctx,
                show_default_is_str=show_default_is_str,
                default_value=default_value,
            )
            # Typer override end
            if default_string:
                extra.append(_("default: {default}").format(default=default_string))
        if self.required:
            extra.append(_("required"))
        if extra:
            extra_str = ";".join(extra)
            help = f"{help}  [{extra_str}]" if help else f"[{extra_str}]"
        return name, help

    def make_metavar(self) -> str:
        # Modified version of click.core.Argument.make_metavar()
        # to include Argument name
        if self.metavar is not None:
            return self.metavar
        var = (self.name or "").upper()
        if not self.required:
            var = f"[{var}]"
        type_var = self.type.get_metavar(self)
        if type_var:
            var += f":{type_var}"
        if self.nargs != 1:
            var += "..."
        return var


class TyperOption(click.core.Option):
    def __init__(
        self,
        *,
        # Parameter
        param_decls: List[str],
        type: Optional[Union[click.types.ParamType, Any]] = None,
        required: Optional[bool] = None,
        default: Optional[Any] = None,
        callback: Optional[Callable[..., Any]] = None,
        nargs: Optional[int] = None,
        metavar: Optional[str] = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: Optional[Union[str, List[str]]] = None,
        shell_complete: Optional[
            Callable[
                [click.Context, click.Parameter, str],
                Union[List["click.shell_completion.CompletionItem"], List[str]],
            ]
        ] = None,
        autocompletion: Optional[Callable[..., Any]] = None,
        # Option
        show_default: Union[bool, str] = False,
        prompt: Union[bool, str] = False,
        confirmation_prompt: Union[bool, str] = False,
        prompt_required: bool = True,
        hide_input: bool = False,
        is_flag: Optional[bool] = None,
        flag_value: Optional[Any] = None,
        multiple: bool = False,
        count: bool = False,
        allow_from_autoenv: bool = True,
        help: Optional[str] = None,
        hidden: bool = False,
        show_choices: bool = True,
        show_envvar: bool = False,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        super().__init__(
            param_decls=param_decls,
            type=type,
            required=required,
            default=default,
            callback=callback,
            nargs=nargs,
            metavar=metavar,
            expose_value=expose_value,
            is_eager=is_eager,
            envvar=envvar,
            show_default=show_default,
            prompt=prompt,
            confirmation_prompt=confirmation_prompt,
            hide_input=hide_input,
            is_flag=is_flag,
            flag_value=flag_value,
            multiple=multiple,
            count=count,
            allow_from_autoenv=allow_from_autoenv,
            help=help,
            hidden=hidden,
            show_choices=show_choices,
            show_envvar=show_envvar,
            prompt_required=prompt_required,
            shell_complete=shell_complete,
        )
        _typer_param_setup_autocompletion_compat(self, autocompletion=autocompletion)
        self.rich_help_panel = rich_help_panel

    def _get_default_string(
        self,
        *,
        ctx: click.Context,
        show_default_is_str: bool,
        default_value: Union[List[Any], Tuple[Any, ...], str, Callable[..., Any], Any],
    ) -> str:
        return _get_default_string(
            self,
            ctx=ctx,
            show_default_is_str=show_default_is_str,
            default_value=default_value,
        )

    def _extract_default_help_str(
        self, *, ctx: click.Context
    ) -> Optional[Union[Any, Callable[[], Any]]]:
        return _extract_default_help_str(self, ctx=ctx)

    def get_help_record(self, ctx: click.Context) -> Optional[Tuple[str, str]]:
        # Duplicate all of Click's logic only to modify a single line, to allow boolean
        # flags with only names for False values as it's currently supported by Typer
        # Ref: https://typer.tiangolo.com/tutorial/parameter-types/bool/#only-names-for-false
        if self.hidden:
            return None

        any_prefix_is_slash = False

        def _write_opts(opts: Sequence[str]) -> str:
            nonlocal any_prefix_is_slash

            rv, any_slashes = click.formatting.join_options(opts)

            if any_slashes:
                any_prefix_is_slash = True

            if not self.is_flag and not self.count:
                rv += f" {self.make_metavar()}"

            return rv

        rv = [_write_opts(self.opts)]

        if self.secondary_opts:
            rv.append(_write_opts(self.secondary_opts))

        help = self.help or ""
        extra = []

        if self.show_envvar:
            envvar = self.envvar

            if envvar is None:
                if (
                    self.allow_from_autoenv
                    and ctx.auto_envvar_prefix is not None
                    and self.name is not None
                ):
                    envvar = f"{ctx.auto_envvar_prefix}_{self.name.upper()}"

            if envvar is not None:
                var_str = (
                    envvar
                    if isinstance(envvar, str)
                    else ", ".join(str(d) for d in envvar)
                )
                extra.append(_("env var: {var}").format(var=var_str))

        # Typer override:
        # Extracted to _extract_default() to allow re-using it in rich_utils
        default_value = self._extract_default_help_str(ctx=ctx)
        # Typer override end

        show_default_is_str = isinstance(self.show_default, str)

        if show_default_is_str or (
            default_value is not None and (self.show_default or ctx.show_default)
        ):
            # Typer override:
            # Extracted to _get_default_string() to allow re-using it in rich_utils
            default_string = self._get_default_string(
                ctx=ctx,
                show_default_is_str=show_default_is_str,
                default_value=default_value,
            )
            # Typer override end
            if default_string:
                extra.append(_("default: {default}").format(default=default_string))

        if isinstance(self.type, click.types._NumberRangeBase):
            range_str = self.type._describe_range()

            if range_str:
                extra.append(range_str)

        if self.required:
            extra.append(_("required"))

        if extra:
            extra_str = "; ".join(extra)
            help = f"{help}  [{extra_str}]" if help else f"[{extra_str}]"

        return ("; " if any_prefix_is_slash else " / ").join(rv), help


def _typer_format_options(
    self: click.core.Command, *, ctx: click.Context, formatter: click.HelpFormatter
) -> None:
    args = []
    opts = []
    for param in self.get_params(ctx):
        rv = param.get_help_record(ctx)
        if rv is not None:
            if param.param_type_name == "argument":
                args.append(rv)
            elif param.param_type_name == "option":
                opts.append(rv)

    if args:
        with formatter.section(_("Arguments")):
            formatter.write_dl(args)
    if opts:
        with formatter.section(_("Options")):
            formatter.write_dl(opts)


def _typer_main_shell_completion(
    self: click.core.Command,
    *,
    ctx_args: MutableMapping[str, Any],
    prog_name: str,
    complete_var: Optional[str] = None,
) -> None:
    if complete_var is None:
        complete_var = f"_{prog_name}_COMPLETE".replace("-", "_").upper()

    instruction = os.environ.get(complete_var)

    if not instruction:
        return

    from .completion import shell_complete

    rv = shell_complete(self, ctx_args, prog_name, complete_var, instruction)
    sys.exit(rv)


class TyperCommand(click.core.Command):
    def __init__(
        self,
        name: Optional[str],
        *,
        context_settings: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
        params: Optional[List[click.Parameter]] = None,
        help: Optional[str] = None,
        epilog: Optional[str] = None,
        short_help: Optional[str] = None,
        options_metavar: Optional[str] = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        # Rich settings
        rich_markup_mode: MarkupMode = DEFAULT_MARKUP_MODE,
        rich_help_panel: Union[str, None] = None,
    ) -> None:
        super().__init__(
            name=name,
            context_settings=context_settings,
            callback=callback,
            params=params,
            help=help,
            epilog=epilog,
            short_help=short_help,
            options_metavar=options_metavar,
            add_help_option=add_help_option,
            no_args_is_help=no_args_is_help,
            hidden=hidden,
            deprecated=deprecated,
        )
        self.rich_markup_mode: MarkupMode = rich_markup_mode
        self.rich_help_panel = rich_help_panel

    def format_options(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        _typer_format_options(self, ctx=ctx, formatter=formatter)

    def _main_shell_completion(
        self,
        ctx_args: MutableMapping[str, Any],
        prog_name: str,
        complete_var: Optional[str] = None,
    ) -> None:
        _typer_main_shell_completion(
            self, ctx_args=ctx_args, prog_name=prog_name, complete_var=complete_var
        )

    def main(
        self,
        args: Optional[Sequence[str]] = None,
        prog_name: Optional[str] = None,
        complete_var: Optional[str] = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        return _main(
            self,
            args=args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            windows_expand_args=windows_expand_args,
            rich_markup_mode=self.rich_markup_mode,
            **extra,
        )

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if not rich or self.rich_markup_mode is None:
            return super().format_help(ctx, formatter)
        return rich_utils.rich_format_help(
            obj=self,
            ctx=ctx,
            markup_mode=self.rich_markup_mode,
        )


class TyperGroup(click.core.Group):
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        commands: Optional[
            Union[Dict[str, click.Command], Sequence[click.Command]]
        ] = None,
        # Rich settings
        rich_markup_mode: MarkupMode = DEFAULT_MARKUP_MODE,
        rich_help_panel: Union[str, None] = None,
        **attrs: Any,
    ) -> None:
        super().__init__(name=name, commands=commands, **attrs)
        self.rich_markup_mode: MarkupMode = rich_markup_mode
        self.rich_help_panel = rich_help_panel

    def format_options(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        _typer_format_options(self, ctx=ctx, formatter=formatter)
        self.format_commands(ctx, formatter)

    def _main_shell_completion(
        self,
        ctx_args: MutableMapping[str, Any],
        prog_name: str,
        complete_var: Optional[str] = None,
    ) -> None:
        _typer_main_shell_completion(
            self, ctx_args=ctx_args, prog_name=prog_name, complete_var=complete_var
        )

    def main(
        self,
        args: Optional[Sequence[str]] = None,
        prog_name: Optional[str] = None,
        complete_var: Optional[str] = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        return _main(
            self,
            args=args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            windows_expand_args=windows_expand_args,
            rich_markup_mode=self.rich_markup_mode,
            **extra,
        )

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if not rich or self.rich_markup_mode is None:
            return super().format_help(ctx, formatter)
        return rich_utils.rich_format_help(
            obj=self,
            ctx=ctx,
            markup_mode=self.rich_markup_mode,
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\target.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Target
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import page


class TargetID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> TargetID:
        return cls(json)

    def __repr__(self):
        return 'TargetID({})'.format(super().__repr__())


class SessionID(str):
    '''
    Unique identifier of attached debugging session.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SessionID:
        return cls(json)

    def __repr__(self):
        return 'SessionID({})'.format(super().__repr__())


@dataclass
class TargetInfo:
    target_id: TargetID

    #: List of types: https://source.chromium.org/chromium/chromium/src/+/main:content/browser/devtools/devtools_agent_host_impl.cc?ss=chromium&q=f:devtools%20-f:out%20%22::kTypeTab%5B%5D%22
    type_: str

    title: str

    url: str

    #: Whether the target has an attached client.
    attached: bool

    #: Whether the target has access to the originating window.
    can_access_opener: bool

    #: Opener target Id
    opener_id: typing.Optional[TargetID] = None

    #: Frame id of originating window (is only set if target has an opener).
    opener_frame_id: typing.Optional[page.FrameId] = None

    browser_context_id: typing.Optional[browser.BrowserContextID] = None

    #: Provides additional details for specific target types. For example, for
    #: the type of "page", this may be set to "prerender".
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['targetId'] = self.target_id.to_json()
        json['type'] = self.type_
        json['title'] = self.title
        json['url'] = self.url
        json['attached'] = self.attached
        json['canAccessOpener'] = self.can_access_opener
        if self.opener_id is not None:
            json['openerId'] = self.opener_id.to_json()
        if self.opener_frame_id is not None:
            json['openerFrameId'] = self.opener_frame_id.to_json()
        if self.browser_context_id is not None:
            json['browserContextId'] = self.browser_context_id.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            type_=str(json['type']),
            title=str(json['title']),
            url=str(json['url']),
            attached=bool(json['attached']),
            can_access_opener=bool(json['canAccessOpener']),
            opener_id=TargetID.from_json(json['openerId']) if 'openerId' in json else None,
            opener_frame_id=page.FrameId.from_json(json['openerFrameId']) if 'openerFrameId' in json else None,
            browser_context_id=browser.BrowserContextID.from_json(json['browserContextId']) if 'browserContextId' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class FilterEntry:
    '''
    A filter used by target query/discovery/auto-attach operations.
    '''
    #: If set, causes exclusion of matching targets from the list.
    exclude: typing.Optional[bool] = None

    #: If not present, matches any type.
    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.exclude is not None:
            json['exclude'] = self.exclude
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exclude=bool(json['exclude']) if 'exclude' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


class TargetFilter(list):
    '''
    The entries in TargetFilter are matched sequentially against targets and
    the first entry that matches determines if the target is included or not,
    depending on the value of ``exclude`` field in the entry.
    If filter is not specified, the one assumed is
    [{type: "browser", exclude: true}, {type: "tab", exclude: true}, {}]
    (i.e. include everything but ``browser`` and ``tab``).
    '''
    def to_json(self) -> typing.List[FilterEntry]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[FilterEntry]) -> TargetFilter:
        return cls(json)

    def __repr__(self):
        return 'TargetFilter({})'.format(super().__repr__())


@dataclass
class RemoteLocation:
    host: str

    port: int

    def to_json(self):
        json = dict()
        json['host'] = self.host
        json['port'] = self.port
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            host=str(json['host']),
            port=int(json['port']),
        )


class WindowState(enum.Enum):
    '''
    The state of the target window.
    '''
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def activate_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates (focuses) the target.

    :param target_id:
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.activateTarget',
        'params': params,
    }
    json = yield cmd_dict


def attach_to_target(
        target_id: TargetID,
        flatten: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the target with given id.

    :param target_id:
    :param flatten: *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :returns: Id assigned to the session.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if flatten is not None:
        params['flatten'] = flatten
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToTarget',
        'params': params,
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def attach_to_browser_target() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the browser target, only uses flat sessionId mode.

    **EXPERIMENTAL**

    :returns: Id assigned to the session.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToBrowserTarget',
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def close_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Closes the target. If the target is a page that gets closed too.

    :param target_id:
    :returns: Always set to true. If an error occurs, the response indicates protocol error.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.closeTarget',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['success'])


def expose_dev_tools_protocol(
        target_id: TargetID,
        binding_name: typing.Optional[str] = None,
        inherit_permissions: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Inject object to the target's main frame that provides a communication
    channel with browser target.

    Injected object will be available as ``window[bindingName]``.

    The object has the following API:
    - ``binding.send(json)`` - a method to send messages over the remote debugging protocol
    - ``binding.onmessage = json => handleMessage(json)`` - a callback that will be called for the protocol notifications and command responses.

    **EXPERIMENTAL**

    :param target_id:
    :param binding_name: *(Optional)* Binding name, 'cdp' if not specified.
    :param inherit_permissions: *(Optional)* If true, inherits the current root session's permissions (default: false).
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if binding_name is not None:
        params['bindingName'] = binding_name
    if inherit_permissions is not None:
        params['inheritPermissions'] = inherit_permissions
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.exposeDevToolsProtocol',
        'params': params,
    }
    json = yield cmd_dict


def create_browser_context(
        dispose_on_detach: typing.Optional[bool] = None,
        proxy_server: typing.Optional[str] = None,
        proxy_bypass_list: typing.Optional[str] = None,
        origins_with_universal_network_access: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,browser.BrowserContextID]:
    '''
    Creates a new empty BrowserContext. Similar to an incognito profile but you can have more than
    one.

    :param dispose_on_detach: **(EXPERIMENTAL)** *(Optional)* If specified, disposes this context when debugging session disconnects.
    :param proxy_server: **(EXPERIMENTAL)** *(Optional)* Proxy server, similar to the one passed to --proxy-server
    :param proxy_bypass_list: **(EXPERIMENTAL)** *(Optional)* Proxy bypass list, similar to the one passed to --proxy-bypass-list
    :param origins_with_universal_network_access: **(EXPERIMENTAL)** *(Optional)* An optional list of origins to grant unlimited cross-origin access to. Parts of the URL other than those constituting origin are ignored.
    :returns: The id of the context created.
    '''
    params: T_JSON_DICT = dict()
    if dispose_on_detach is not None:
        params['disposeOnDetach'] = dispose_on_detach
    if proxy_server is not None:
        params['proxyServer'] = proxy_server
    if proxy_bypass_list is not None:
        params['proxyBypassList'] = proxy_bypass_list
    if origins_with_universal_network_access is not None:
        params['originsWithUniversalNetworkAccess'] = [i for i in origins_with_universal_network_access]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createBrowserContext',
        'params': params,
    }
    json = yield cmd_dict
    return browser.BrowserContextID.from_json(json['browserContextId'])


def get_browser_contexts() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[browser.BrowserContextID]]:
    '''
    Returns all browser contexts created with ``Target.createBrowserContext`` method.

    :returns: An array of browser context ids.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getBrowserContexts',
    }
    json = yield cmd_dict
    return [browser.BrowserContextID.from_json(i) for i in json['browserContextIds']]


def create_target(
        url: str,
        left: typing.Optional[int] = None,
        top: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        height: typing.Optional[int] = None,
        window_state: typing.Optional[WindowState] = None,
        browser_context_id: typing.Optional[browser.BrowserContextID] = None,
        enable_begin_frame_control: typing.Optional[bool] = None,
        new_window: typing.Optional[bool] = None,
        background: typing.Optional[bool] = None,
        for_tab: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetID]:
    '''
    Creates a new page.

    :param url: The initial URL the page will be navigated to. An empty string indicates about:blank.
    :param left: **(EXPERIMENTAL)** *(Optional)* Frame left origin in DIP (requires newWindow to be true or headless shell).
    :param top: **(EXPERIMENTAL)** *(Optional)* Frame top origin in DIP (requires newWindow to be true or headless shell).
    :param width: *(Optional)* Frame width in DIP (requires newWindow to be true or headless shell).
    :param height: *(Optional)* Frame height in DIP (requires newWindow to be true or headless shell).
    :param window_state: *(Optional)* Frame window state (requires newWindow to be true or headless shell). Default is normal.
    :param browser_context_id: **(EXPERIMENTAL)** *(Optional)* The browser context to create the page in.
    :param enable_begin_frame_control: **(EXPERIMENTAL)** *(Optional)* Whether BeginFrames for this target will be controlled via DevTools (headless shell only, not supported on MacOS yet, false by default).
    :param new_window: *(Optional)* Whether to create a new Window or Tab (false by default, not supported by headless shell).
    :param background: *(Optional)* Whether to create the target in background or foreground (false by default, not supported by headless shell).
    :param for_tab: **(EXPERIMENTAL)** *(Optional)* Whether to create the target of type "tab".
    :returns: The id of the page opened.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    if left is not None:
        params['left'] = left
    if top is not None:
        params['top'] = top
    if width is not None:
        params['width'] = width
    if height is not None:
        params['height'] = height
    if window_state is not None:
        params['windowState'] = window_state.to_json()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    if enable_begin_frame_control is not None:
        params['enableBeginFrameControl'] = enable_begin_frame_control
    if new_window is not None:
        params['newWindow'] = new_window
    if background is not None:
        params['background'] = background
    if for_tab is not None:
        params['forTab'] = for_tab
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createTarget',
        'params': params,
    }
    json = yield cmd_dict
    return TargetID.from_json(json['targetId'])


def detach_from_target(
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Detaches session with given id.

    :param session_id: *(Optional)* Session to detach.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.detachFromTarget',
        'params': params,
    }
    json = yield cmd_dict


def dispose_browser_context(
        browser_context_id: browser.BrowserContextID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a BrowserContext. All the belonging pages will be closed without calling their
    beforeunload hooks.

    :param browser_context_id:
    '''
    params: T_JSON_DICT = dict()
    params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.disposeBrowserContext',
        'params': params,
    }
    json = yield cmd_dict


def get_target_info(
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetInfo]:
    '''
    Returns information about a target.

    **EXPERIMENTAL**

    :param target_id: *(Optional)*
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargetInfo',
        'params': params,
    }
    json = yield cmd_dict
    return TargetInfo.from_json(json['targetInfo'])


def get_targets(
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TargetInfo]]:
    '''
    Retrieves a list of available targets.

    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be reported. If filter is not specified and target discovery is currently enabled, a filter used for target discovery is used for consistency.
    :returns: The list of targets.
    '''
    params: T_JSON_DICT = dict()
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargets',
        'params': params,
    }
    json = yield cmd_dict
    return [TargetInfo.from_json(i) for i in json['targetInfos']]


def send_message_to_target(
        message: str,
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sends protocol message over session with given id.
    Consider using flat mode instead; see commands attachToTarget, setAutoAttach,
    and crbug.com/991325.

    :param message:
    :param session_id: *(Optional)* Identifier of the session.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    params['message'] = message
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.sendMessageToTarget',
        'params': params,
    }
    json = yield cmd_dict


def set_auto_attach(
        auto_attach: bool,
        wait_for_debugger_on_start: bool,
        flatten: typing.Optional[bool] = None,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to automatically attach to new targets which are considered to be related to
    this one. When turned on, attaches to all existing related targets as well. When turned off,
    automatically detaches from all currently attached targets.
    This also clears all targets added by ``autoAttachRelated`` from the list of targets to watch
    for creation of related targets.

    :param auto_attach: Whether to auto-attach to related targets.
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param flatten: **(EXPERIMENTAL)** *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['autoAttach'] = auto_attach
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if flatten is not None:
        params['flatten'] = flatten
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setAutoAttach',
        'params': params,
    }
    json = yield cmd_dict


def auto_attach_related(
        target_id: TargetID,
        wait_for_debugger_on_start: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Adds the specified target to the list of targets that will be monitored for any related target
    creation (such as child frames, child workers and new versions of service worker) and reported
    through ``attachedToTarget``. The specified target is also auto-attached.
    This cancels the effect of any previous ``setAutoAttach`` and is also cancelled by subsequent
    ``setAutoAttach``. Only available at the Browser target.

    **EXPERIMENTAL**

    :param target_id:
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.autoAttachRelated',
        'params': params,
    }
    json = yield cmd_dict


def set_discover_targets(
        discover: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to discover available targets and notify via
    ``targetCreated/targetInfoChanged/targetDestroyed`` events.

    :param discover: Whether to discover available targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached. If ```discover```` is false, ````filter``` must be omitted or empty.
    '''
    params: T_JSON_DICT = dict()
    params['discover'] = discover
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setDiscoverTargets',
        'params': params,
    }
    json = yield cmd_dict


def set_remote_locations(
        locations: typing.List[RemoteLocation]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables target discovery for the specified locations, when ``setDiscoverTargets`` was set to
    ``true``.

    **EXPERIMENTAL**

    :param locations: List of remote locations.
    '''
    params: T_JSON_DICT = dict()
    params['locations'] = [i.to_json() for i in locations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setRemoteLocations',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Target.attachedToTarget')
@dataclass
class AttachedToTarget:
    '''
    **EXPERIMENTAL**

    Issued when attached to target because of auto-attach or ``attachToTarget`` command.
    '''
    #: Identifier assigned to the session used to send/receive messages.
    session_id: SessionID
    target_info: TargetInfo
    waiting_for_debugger: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttachedToTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_info=TargetInfo.from_json(json['targetInfo']),
            waiting_for_debugger=bool(json['waitingForDebugger'])
        )


@event_class('Target.detachedFromTarget')
@dataclass
class DetachedFromTarget:
    '''
    **EXPERIMENTAL**

    Issued when detached from target for any reason (including ``detachFromTarget`` command). Can be
    issued multiple times per target if multiple sessions have been attached to it.
    '''
    #: Detached session identifier.
    session_id: SessionID
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DetachedFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.receivedMessageFromTarget')
@dataclass
class ReceivedMessageFromTarget:
    '''
    Notifies about a new protocol message received from the session (as reported in
    ``attachedToTarget`` event).
    '''
    #: Identifier of a session which sends a message.
    session_id: SessionID
    message: str
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReceivedMessageFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            message=str(json['message']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.targetCreated')
@dataclass
class TargetCreated:
    '''
    Issued when a possible inspection target is created.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCreated:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )


@event_class('Target.targetDestroyed')
@dataclass
class TargetDestroyed:
    '''
    Issued when a target is destroyed.
    '''
    target_id: TargetID

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetDestroyed:
        return cls(
            target_id=TargetID.from_json(json['targetId'])
        )


@event_class('Target.targetCrashed')
@dataclass
class TargetCrashed:
    '''
    Issued when a target has crashed.
    '''
    target_id: TargetID
    #: Termination status type.
    status: str
    #: Termination error code.
    error_code: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCrashed:
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            status=str(json['status']),
            error_code=int(json['errorCode'])
        )


@event_class('Target.targetInfoChanged')
@dataclass
class TargetInfoChanged:
    '''
    Issued when some information about a target has changed. This only happens between
    ``targetCreated`` and ``targetDestroyed``.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetInfoChanged:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\target.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Target
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import page


class TargetID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> TargetID:
        return cls(json)

    def __repr__(self):
        return 'TargetID({})'.format(super().__repr__())


class SessionID(str):
    '''
    Unique identifier of attached debugging session.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SessionID:
        return cls(json)

    def __repr__(self):
        return 'SessionID({})'.format(super().__repr__())


@dataclass
class TargetInfo:
    target_id: TargetID

    #: List of types: https://source.chromium.org/chromium/chromium/src/+/main:content/browser/devtools/devtools_agent_host_impl.cc?ss=chromium&q=f:devtools%20-f:out%20%22::kTypeTab%5B%5D%22
    type_: str

    title: str

    url: str

    #: Whether the target has an attached client.
    attached: bool

    #: Whether the target has access to the originating window.
    can_access_opener: bool

    #: Opener target Id
    opener_id: typing.Optional[TargetID] = None

    #: Frame id of originating window (is only set if target has an opener).
    opener_frame_id: typing.Optional[page.FrameId] = None

    browser_context_id: typing.Optional[browser.BrowserContextID] = None

    #: Provides additional details for specific target types. For example, for
    #: the type of "page", this may be set to "prerender".
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['targetId'] = self.target_id.to_json()
        json['type'] = self.type_
        json['title'] = self.title
        json['url'] = self.url
        json['attached'] = self.attached
        json['canAccessOpener'] = self.can_access_opener
        if self.opener_id is not None:
            json['openerId'] = self.opener_id.to_json()
        if self.opener_frame_id is not None:
            json['openerFrameId'] = self.opener_frame_id.to_json()
        if self.browser_context_id is not None:
            json['browserContextId'] = self.browser_context_id.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            type_=str(json['type']),
            title=str(json['title']),
            url=str(json['url']),
            attached=bool(json['attached']),
            can_access_opener=bool(json['canAccessOpener']),
            opener_id=TargetID.from_json(json['openerId']) if 'openerId' in json else None,
            opener_frame_id=page.FrameId.from_json(json['openerFrameId']) if 'openerFrameId' in json else None,
            browser_context_id=browser.BrowserContextID.from_json(json['browserContextId']) if 'browserContextId' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class FilterEntry:
    '''
    A filter used by target query/discovery/auto-attach operations.
    '''
    #: If set, causes exclusion of matching targets from the list.
    exclude: typing.Optional[bool] = None

    #: If not present, matches any type.
    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.exclude is not None:
            json['exclude'] = self.exclude
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exclude=bool(json['exclude']) if 'exclude' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


class TargetFilter(list):
    '''
    The entries in TargetFilter are matched sequentially against targets and
    the first entry that matches determines if the target is included or not,
    depending on the value of ``exclude`` field in the entry.
    If filter is not specified, the one assumed is
    [{type: "browser", exclude: true}, {type: "tab", exclude: true}, {}]
    (i.e. include everything but ``browser`` and ``tab``).
    '''
    def to_json(self) -> typing.List[FilterEntry]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[FilterEntry]) -> TargetFilter:
        return cls(json)

    def __repr__(self):
        return 'TargetFilter({})'.format(super().__repr__())


@dataclass
class RemoteLocation:
    host: str

    port: int

    def to_json(self):
        json = dict()
        json['host'] = self.host
        json['port'] = self.port
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            host=str(json['host']),
            port=int(json['port']),
        )


class WindowState(enum.Enum):
    '''
    The state of the target window.
    '''
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def activate_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates (focuses) the target.

    :param target_id:
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.activateTarget',
        'params': params,
    }
    json = yield cmd_dict


def attach_to_target(
        target_id: TargetID,
        flatten: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the target with given id.

    :param target_id:
    :param flatten: *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :returns: Id assigned to the session.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if flatten is not None:
        params['flatten'] = flatten
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToTarget',
        'params': params,
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def attach_to_browser_target() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the browser target, only uses flat sessionId mode.

    **EXPERIMENTAL**

    :returns: Id assigned to the session.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToBrowserTarget',
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def close_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Closes the target. If the target is a page that gets closed too.

    :param target_id:
    :returns: Always set to true. If an error occurs, the response indicates protocol error.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.closeTarget',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['success'])


def expose_dev_tools_protocol(
        target_id: TargetID,
        binding_name: typing.Optional[str] = None,
        inherit_permissions: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Inject object to the target's main frame that provides a communication
    channel with browser target.

    Injected object will be available as ``window[bindingName]``.

    The object has the following API:
    - ``binding.send(json)`` - a method to send messages over the remote debugging protocol
    - ``binding.onmessage = json => handleMessage(json)`` - a callback that will be called for the protocol notifications and command responses.

    **EXPERIMENTAL**

    :param target_id:
    :param binding_name: *(Optional)* Binding name, 'cdp' if not specified.
    :param inherit_permissions: *(Optional)* If true, inherits the current root session's permissions (default: false).
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if binding_name is not None:
        params['bindingName'] = binding_name
    if inherit_permissions is not None:
        params['inheritPermissions'] = inherit_permissions
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.exposeDevToolsProtocol',
        'params': params,
    }
    json = yield cmd_dict


def create_browser_context(
        dispose_on_detach: typing.Optional[bool] = None,
        proxy_server: typing.Optional[str] = None,
        proxy_bypass_list: typing.Optional[str] = None,
        origins_with_universal_network_access: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,browser.BrowserContextID]:
    '''
    Creates a new empty BrowserContext. Similar to an incognito profile but you can have more than
    one.

    :param dispose_on_detach: **(EXPERIMENTAL)** *(Optional)* If specified, disposes this context when debugging session disconnects.
    :param proxy_server: **(EXPERIMENTAL)** *(Optional)* Proxy server, similar to the one passed to --proxy-server
    :param proxy_bypass_list: **(EXPERIMENTAL)** *(Optional)* Proxy bypass list, similar to the one passed to --proxy-bypass-list
    :param origins_with_universal_network_access: **(EXPERIMENTAL)** *(Optional)* An optional list of origins to grant unlimited cross-origin access to. Parts of the URL other than those constituting origin are ignored.
    :returns: The id of the context created.
    '''
    params: T_JSON_DICT = dict()
    if dispose_on_detach is not None:
        params['disposeOnDetach'] = dispose_on_detach
    if proxy_server is not None:
        params['proxyServer'] = proxy_server
    if proxy_bypass_list is not None:
        params['proxyBypassList'] = proxy_bypass_list
    if origins_with_universal_network_access is not None:
        params['originsWithUniversalNetworkAccess'] = [i for i in origins_with_universal_network_access]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createBrowserContext',
        'params': params,
    }
    json = yield cmd_dict
    return browser.BrowserContextID.from_json(json['browserContextId'])


def get_browser_contexts() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[browser.BrowserContextID]]:
    '''
    Returns all browser contexts created with ``Target.createBrowserContext`` method.

    :returns: An array of browser context ids.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getBrowserContexts',
    }
    json = yield cmd_dict
    return [browser.BrowserContextID.from_json(i) for i in json['browserContextIds']]


def create_target(
        url: str,
        left: typing.Optional[int] = None,
        top: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        height: typing.Optional[int] = None,
        window_state: typing.Optional[WindowState] = None,
        browser_context_id: typing.Optional[browser.BrowserContextID] = None,
        enable_begin_frame_control: typing.Optional[bool] = None,
        new_window: typing.Optional[bool] = None,
        background: typing.Optional[bool] = None,
        for_tab: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetID]:
    '''
    Creates a new page.

    :param url: The initial URL the page will be navigated to. An empty string indicates about:blank.
    :param left: **(EXPERIMENTAL)** *(Optional)* Frame left origin in DIP (requires newWindow to be true or headless shell).
    :param top: **(EXPERIMENTAL)** *(Optional)* Frame top origin in DIP (requires newWindow to be true or headless shell).
    :param width: *(Optional)* Frame width in DIP (requires newWindow to be true or headless shell).
    :param height: *(Optional)* Frame height in DIP (requires newWindow to be true or headless shell).
    :param window_state: *(Optional)* Frame window state (requires newWindow to be true or headless shell). Default is normal.
    :param browser_context_id: **(EXPERIMENTAL)** *(Optional)* The browser context to create the page in.
    :param enable_begin_frame_control: **(EXPERIMENTAL)** *(Optional)* Whether BeginFrames for this target will be controlled via DevTools (headless shell only, not supported on MacOS yet, false by default).
    :param new_window: *(Optional)* Whether to create a new Window or Tab (false by default, not supported by headless shell).
    :param background: *(Optional)* Whether to create the target in background or foreground (false by default, not supported by headless shell).
    :param for_tab: **(EXPERIMENTAL)** *(Optional)* Whether to create the target of type "tab".
    :returns: The id of the page opened.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    if left is not None:
        params['left'] = left
    if top is not None:
        params['top'] = top
    if width is not None:
        params['width'] = width
    if height is not None:
        params['height'] = height
    if window_state is not None:
        params['windowState'] = window_state.to_json()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    if enable_begin_frame_control is not None:
        params['enableBeginFrameControl'] = enable_begin_frame_control
    if new_window is not None:
        params['newWindow'] = new_window
    if background is not None:
        params['background'] = background
    if for_tab is not None:
        params['forTab'] = for_tab
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createTarget',
        'params': params,
    }
    json = yield cmd_dict
    return TargetID.from_json(json['targetId'])


def detach_from_target(
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Detaches session with given id.

    :param session_id: *(Optional)* Session to detach.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.detachFromTarget',
        'params': params,
    }
    json = yield cmd_dict


def dispose_browser_context(
        browser_context_id: browser.BrowserContextID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a BrowserContext. All the belonging pages will be closed without calling their
    beforeunload hooks.

    :param browser_context_id:
    '''
    params: T_JSON_DICT = dict()
    params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.disposeBrowserContext',
        'params': params,
    }
    json = yield cmd_dict


def get_target_info(
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetInfo]:
    '''
    Returns information about a target.

    **EXPERIMENTAL**

    :param target_id: *(Optional)*
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargetInfo',
        'params': params,
    }
    json = yield cmd_dict
    return TargetInfo.from_json(json['targetInfo'])


def get_targets(
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TargetInfo]]:
    '''
    Retrieves a list of available targets.

    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be reported. If filter is not specified and target discovery is currently enabled, a filter used for target discovery is used for consistency.
    :returns: The list of targets.
    '''
    params: T_JSON_DICT = dict()
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargets',
        'params': params,
    }
    json = yield cmd_dict
    return [TargetInfo.from_json(i) for i in json['targetInfos']]


def send_message_to_target(
        message: str,
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sends protocol message over session with given id.
    Consider using flat mode instead; see commands attachToTarget, setAutoAttach,
    and crbug.com/991325.

    :param message:
    :param session_id: *(Optional)* Identifier of the session.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    params['message'] = message
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.sendMessageToTarget',
        'params': params,
    }
    json = yield cmd_dict


def set_auto_attach(
        auto_attach: bool,
        wait_for_debugger_on_start: bool,
        flatten: typing.Optional[bool] = None,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to automatically attach to new targets which are considered to be related to
    this one. When turned on, attaches to all existing related targets as well. When turned off,
    automatically detaches from all currently attached targets.
    This also clears all targets added by ``autoAttachRelated`` from the list of targets to watch
    for creation of related targets.

    :param auto_attach: Whether to auto-attach to related targets.
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param flatten: **(EXPERIMENTAL)** *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['autoAttach'] = auto_attach
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if flatten is not None:
        params['flatten'] = flatten
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setAutoAttach',
        'params': params,
    }
    json = yield cmd_dict


def auto_attach_related(
        target_id: TargetID,
        wait_for_debugger_on_start: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Adds the specified target to the list of targets that will be monitored for any related target
    creation (such as child frames, child workers and new versions of service worker) and reported
    through ``attachedToTarget``. The specified target is also auto-attached.
    This cancels the effect of any previous ``setAutoAttach`` and is also cancelled by subsequent
    ``setAutoAttach``. Only available at the Browser target.

    **EXPERIMENTAL**

    :param target_id:
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.autoAttachRelated',
        'params': params,
    }
    json = yield cmd_dict


def set_discover_targets(
        discover: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to discover available targets and notify via
    ``targetCreated/targetInfoChanged/targetDestroyed`` events.

    :param discover: Whether to discover available targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached. If ```discover```` is false, ````filter``` must be omitted or empty.
    '''
    params: T_JSON_DICT = dict()
    params['discover'] = discover
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setDiscoverTargets',
        'params': params,
    }
    json = yield cmd_dict


def set_remote_locations(
        locations: typing.List[RemoteLocation]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables target discovery for the specified locations, when ``setDiscoverTargets`` was set to
    ``true``.

    **EXPERIMENTAL**

    :param locations: List of remote locations.
    '''
    params: T_JSON_DICT = dict()
    params['locations'] = [i.to_json() for i in locations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setRemoteLocations',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Target.attachedToTarget')
@dataclass
class AttachedToTarget:
    '''
    **EXPERIMENTAL**

    Issued when attached to target because of auto-attach or ``attachToTarget`` command.
    '''
    #: Identifier assigned to the session used to send/receive messages.
    session_id: SessionID
    target_info: TargetInfo
    waiting_for_debugger: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttachedToTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_info=TargetInfo.from_json(json['targetInfo']),
            waiting_for_debugger=bool(json['waitingForDebugger'])
        )


@event_class('Target.detachedFromTarget')
@dataclass
class DetachedFromTarget:
    '''
    **EXPERIMENTAL**

    Issued when detached from target for any reason (including ``detachFromTarget`` command). Can be
    issued multiple times per target if multiple sessions have been attached to it.
    '''
    #: Detached session identifier.
    session_id: SessionID
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DetachedFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.receivedMessageFromTarget')
@dataclass
class ReceivedMessageFromTarget:
    '''
    Notifies about a new protocol message received from the session (as reported in
    ``attachedToTarget`` event).
    '''
    #: Identifier of a session which sends a message.
    session_id: SessionID
    message: str
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReceivedMessageFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            message=str(json['message']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.targetCreated')
@dataclass
class TargetCreated:
    '''
    Issued when a possible inspection target is created.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCreated:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )


@event_class('Target.targetDestroyed')
@dataclass
class TargetDestroyed:
    '''
    Issued when a target is destroyed.
    '''
    target_id: TargetID

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetDestroyed:
        return cls(
            target_id=TargetID.from_json(json['targetId'])
        )


@event_class('Target.targetCrashed')
@dataclass
class TargetCrashed:
    '''
    Issued when a target has crashed.
    '''
    target_id: TargetID
    #: Termination status type.
    status: str
    #: Termination error code.
    error_code: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCrashed:
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            status=str(json['status']),
            error_code=int(json['errorCode'])
        )


@event_class('Target.targetInfoChanged')
@dataclass
class TargetInfoChanged:
    '''
    Issued when some information about a target has changed. This only happens between
    ``targetCreated`` and ``targetDestroyed``.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetInfoChanged:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )

# === NexusCore/openenv\Lib\site-packages\PIL\ImageOps.py ===
#
# The Python Imaging Library.
# $Id$
#
# standard image operations
#
# History:
# 2001-10-20 fl   Created
# 2001-10-23 fl   Added autocontrast operator
# 2001-12-18 fl   Added Kevin's fit operator
# 2004-03-14 fl   Fixed potential division by zero in equalize
# 2005-05-05 fl   Fixed equalize for low number of values
#
# Copyright (c) 2001-2004 by Secret Labs AB
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import functools
import operator
import re
from collections.abc import Sequence
from typing import Literal, Protocol, cast, overload

from . import ExifTags, Image, ImagePalette

#
# helpers


def _border(border: int | tuple[int, ...]) -> tuple[int, int, int, int]:
    if isinstance(border, tuple):
        if len(border) == 2:
            left, top = right, bottom = border
        elif len(border) == 4:
            left, top, right, bottom = border
    else:
        left = top = right = bottom = border
    return left, top, right, bottom


def _color(color: str | int | tuple[int, ...], mode: str) -> int | tuple[int, ...]:
    if isinstance(color, str):
        from . import ImageColor

        color = ImageColor.getcolor(color, mode)
    return color


def _lut(image: Image.Image, lut: list[int]) -> Image.Image:
    if image.mode == "P":
        # FIXME: apply to lookup table, not image data
        msg = "mode P support coming soon"
        raise NotImplementedError(msg)
    elif image.mode in ("L", "RGB"):
        if image.mode == "RGB" and len(lut) == 256:
            lut = lut + lut + lut
        return image.point(lut)
    else:
        msg = f"not supported for mode {image.mode}"
        raise OSError(msg)


#
# actions


def autocontrast(
    image: Image.Image,
    cutoff: float | tuple[float, float] = 0,
    ignore: int | Sequence[int] | None = None,
    mask: Image.Image | None = None,
    preserve_tone: bool = False,
) -> Image.Image:
    """
    Maximize (normalize) image contrast. This function calculates a
    histogram of the input image (or mask region), removes ``cutoff`` percent of the
    lightest and darkest pixels from the histogram, and remaps the image
    so that the darkest pixel becomes black (0), and the lightest
    becomes white (255).

    :param image: The image to process.
    :param cutoff: The percent to cut off from the histogram on the low and
                   high ends. Either a tuple of (low, high), or a single
                   number for both.
    :param ignore: The background pixel value (use None for no background).
    :param mask: Histogram used in contrast operation is computed using pixels
                 within the mask. If no mask is given the entire image is used
                 for histogram computation.
    :param preserve_tone: Preserve image tone in Photoshop-like style autocontrast.

                          .. versionadded:: 8.2.0

    :return: An image.
    """
    if preserve_tone:
        histogram = image.convert("L").histogram(mask)
    else:
        histogram = image.histogram(mask)

    lut = []
    for layer in range(0, len(histogram), 256):
        h = histogram[layer : layer + 256]
        if ignore is not None:
            # get rid of outliers
            if isinstance(ignore, int):
                h[ignore] = 0
            else:
                for ix in ignore:
                    h[ix] = 0
        if cutoff:
            # cut off pixels from both ends of the histogram
            if not isinstance(cutoff, tuple):
                cutoff = (cutoff, cutoff)
            # get number of pixels
            n = 0
            for ix in range(256):
                n = n + h[ix]
            # remove cutoff% pixels from the low end
            cut = int(n * cutoff[0] // 100)
            for lo in range(256):
                if cut > h[lo]:
                    cut = cut - h[lo]
                    h[lo] = 0
                else:
                    h[lo] -= cut
                    cut = 0
                if cut <= 0:
                    break
            # remove cutoff% samples from the high end
            cut = int(n * cutoff[1] // 100)
            for hi in range(255, -1, -1):
                if cut > h[hi]:
                    cut = cut - h[hi]
                    h[hi] = 0
                else:
                    h[hi] -= cut
                    cut = 0
                if cut <= 0:
                    break
        # find lowest/highest samples after preprocessing
        for lo in range(256):
            if h[lo]:
                break
        for hi in range(255, -1, -1):
            if h[hi]:
                break
        if hi <= lo:
            # don't bother
            lut.extend(list(range(256)))
        else:
            scale = 255.0 / (hi - lo)
            offset = -lo * scale
            for ix in range(256):
                ix = int(ix * scale + offset)
                if ix < 0:
                    ix = 0
                elif ix > 255:
                    ix = 255
                lut.append(ix)
    return _lut(image, lut)


def colorize(
    image: Image.Image,
    black: str | tuple[int, ...],
    white: str | tuple[int, ...],
    mid: str | int | tuple[int, ...] | None = None,
    blackpoint: int = 0,
    whitepoint: int = 255,
    midpoint: int = 127,
) -> Image.Image:
    """
    Colorize grayscale image.
    This function calculates a color wedge which maps all black pixels in
    the source image to the first color and all white pixels to the
    second color. If ``mid`` is specified, it uses three-color mapping.
    The ``black`` and ``white`` arguments should be RGB tuples or color names;
    optionally you can use three-color mapping by also specifying ``mid``.
    Mapping positions for any of the colors can be specified
    (e.g. ``blackpoint``), where these parameters are the integer
    value corresponding to where the corresponding color should be mapped.
    These parameters must have logical order, such that
    ``blackpoint <= midpoint <= whitepoint`` (if ``mid`` is specified).

    :param image: The image to colorize.
    :param black: The color to use for black input pixels.
    :param white: The color to use for white input pixels.
    :param mid: The color to use for midtone input pixels.
    :param blackpoint: an int value [0, 255] for the black mapping.
    :param whitepoint: an int value [0, 255] for the white mapping.
    :param midpoint: an int value [0, 255] for the midtone mapping.
    :return: An image.
    """

    # Initial asserts
    assert image.mode == "L"
    if mid is None:
        assert 0 <= blackpoint <= whitepoint <= 255
    else:
        assert 0 <= blackpoint <= midpoint <= whitepoint <= 255

    # Define colors from arguments
    rgb_black = cast(Sequence[int], _color(black, "RGB"))
    rgb_white = cast(Sequence[int], _color(white, "RGB"))
    rgb_mid = cast(Sequence[int], _color(mid, "RGB")) if mid is not None else None

    # Empty lists for the mapping
    red = []
    green = []
    blue = []

    # Create the low-end values
    for i in range(blackpoint):
        red.append(rgb_black[0])
        green.append(rgb_black[1])
        blue.append(rgb_black[2])

    # Create the mapping (2-color)
    if rgb_mid is None:
        range_map = range(whitepoint - blackpoint)

        for i in range_map:
            red.append(
                rgb_black[0] + i * (rgb_white[0] - rgb_black[0]) // len(range_map)
            )
            green.append(
                rgb_black[1] + i * (rgb_white[1] - rgb_black[1]) // len(range_map)
            )
            blue.append(
                rgb_black[2] + i * (rgb_white[2] - rgb_black[2]) // len(range_map)
            )

    # Create the mapping (3-color)
    else:
        range_map1 = range(midpoint - blackpoint)
        range_map2 = range(whitepoint - midpoint)

        for i in range_map1:
            red.append(
                rgb_black[0] + i * (rgb_mid[0] - rgb_black[0]) // len(range_map1)
            )
            green.append(
                rgb_black[1] + i * (rgb_mid[1] - rgb_black[1]) // len(range_map1)
            )
            blue.append(
                rgb_black[2] + i * (rgb_mid[2] - rgb_black[2]) // len(range_map1)
            )
        for i in range_map2:
            red.append(rgb_mid[0] + i * (rgb_white[0] - rgb_mid[0]) // len(range_map2))
            green.append(
                rgb_mid[1] + i * (rgb_white[1] - rgb_mid[1]) // len(range_map2)
            )
            blue.append(rgb_mid[2] + i * (rgb_white[2] - rgb_mid[2]) // len(range_map2))

    # Create the high-end values
    for i in range(256 - whitepoint):
        red.append(rgb_white[0])
        green.append(rgb_white[1])
        blue.append(rgb_white[2])

    # Return converted image
    image = image.convert("RGB")
    return _lut(image, red + green + blue)


def contain(
    image: Image.Image, size: tuple[int, int], method: int = Image.Resampling.BICUBIC
) -> Image.Image:
    """
    Returns a resized version of the image, set to the maximum width and height
    within the requested size, while maintaining the original aspect ratio.

    :param image: The image to resize.
    :param size: The requested output size in pixels, given as a
                 (width, height) tuple.
    :param method: Resampling method to use. Default is
                   :py:attr:`~PIL.Image.Resampling.BICUBIC`.
                   See :ref:`concept-filters`.
    :return: An image.
    """

    im_ratio = image.width / image.height
    dest_ratio = size[0] / size[1]

    if im_ratio != dest_ratio:
        if im_ratio > dest_ratio:
            new_height = round(image.height / image.width * size[0])
            if new_height != size[1]:
                size = (size[0], new_height)
        else:
            new_width = round(image.width / image.height * size[1])
            if new_width != size[0]:
                size = (new_width, size[1])
    return image.resize(size, resample=method)


def cover(
    image: Image.Image, size: tuple[int, int], method: int = Image.Resampling.BICUBIC
) -> Image.Image:
    """
    Returns a resized version of the image, so that the requested size is
    covered, while maintaining the original aspect ratio.

    :param image: The image to resize.
    :param size: The requested output size in pixels, given as a
                 (width, height) tuple.
    :param method: Resampling method to use. Default is
                   :py:attr:`~PIL.Image.Resampling.BICUBIC`.
                   See :ref:`concept-filters`.
    :return: An image.
    """

    im_ratio = image.width / image.height
    dest_ratio = size[0] / size[1]

    if im_ratio != dest_ratio:
        if im_ratio < dest_ratio:
            new_height = round(image.height / image.width * size[0])
            if new_height != size[1]:
                size = (size[0], new_height)
        else:
            new_width = round(image.width / image.height * size[1])
            if new_width != size[0]:
                size = (new_width, size[1])
    return image.resize(size, resample=method)


def pad(
    image: Image.Image,
    size: tuple[int, int],
    method: int = Image.Resampling.BICUBIC,
    color: str | int | tuple[int, ...] | None = None,
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    """
    Returns a resized and padded version of the image, expanded to fill the
    requested aspect ratio and size.

    :param image: The image to resize and crop.
    :param size: The requested output size in pixels, given as a
                 (width, height) tuple.
    :param method: Resampling method to use. Default is
                   :py:attr:`~PIL.Image.Resampling.BICUBIC`.
                   See :ref:`concept-filters`.
    :param color: The background color of the padded image.
    :param centering: Control the position of the original image within the
                      padded version.

                          (0.5, 0.5) will keep the image centered
                          (0, 0) will keep the image aligned to the top left
                          (1, 1) will keep the image aligned to the bottom
                          right
    :return: An image.
    """

    resized = contain(image, size, method)
    if resized.size == size:
        out = resized
    else:
        out = Image.new(image.mode, size, color)
        if resized.palette:
            palette = resized.getpalette()
            if palette is not None:
                out.putpalette(palette)
        if resized.width != size[0]:
            x = round((size[0] - resized.width) * max(0, min(centering[0], 1)))
            out.paste(resized, (x, 0))
        else:
            y = round((size[1] - resized.height) * max(0, min(centering[1], 1)))
            out.paste(resized, (0, y))
    return out


def crop(image: Image.Image, border: int = 0) -> Image.Image:
    """
    Remove border from image.  The same amount of pixels are removed
    from all four sides.  This function works on all image modes.

    .. seealso:: :py:meth:`~PIL.Image.Image.crop`

    :param image: The image to crop.
    :param border: The number of pixels to remove.
    :return: An image.
    """
    left, top, right, bottom = _border(border)
    return image.crop((left, top, image.size[0] - right, image.size[1] - bottom))


def scale(
    image: Image.Image, factor: float, resample: int = Image.Resampling.BICUBIC
) -> Image.Image:
    """
    Returns a rescaled image by a specific factor given in parameter.
    A factor greater than 1 expands the image, between 0 and 1 contracts the
    image.

    :param image: The image to rescale.
    :param factor: The expansion factor, as a float.
    :param resample: Resampling method to use. Default is
                     :py:attr:`~PIL.Image.Resampling.BICUBIC`.
                     See :ref:`concept-filters`.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """
    if factor == 1:
        return image.copy()
    elif factor <= 0:
        msg = "the factor must be greater than 0"
        raise ValueError(msg)
    else:
        size = (round(factor * image.width), round(factor * image.height))
        return image.resize(size, resample)


class SupportsGetMesh(Protocol):
    """
    An object that supports the ``getmesh`` method, taking an image as an
    argument, and returning a list of tuples. Each tuple contains two tuples,
    the source box as a tuple of 4 integers, and a tuple of 8 integers for the
    final quadrilateral, in order of top left, bottom left, bottom right, top
    right.
    """

    def getmesh(
        self, image: Image.Image
    ) -> list[
        tuple[tuple[int, int, int, int], tuple[int, int, int, int, int, int, int, int]]
    ]: ...


def deform(
    image: Image.Image,
    deformer: SupportsGetMesh,
    resample: int = Image.Resampling.BILINEAR,
) -> Image.Image:
    """
    Deform the image.

    :param image: The image to deform.
    :param deformer: A deformer object.  Any object that implements a
                    ``getmesh`` method can be used.
    :param resample: An optional resampling filter. Same values possible as
       in the PIL.Image.transform function.
    :return: An image.
    """
    return image.transform(
        image.size, Image.Transform.MESH, deformer.getmesh(image), resample
    )


def equalize(image: Image.Image, mask: Image.Image | None = None) -> Image.Image:
    """
    Equalize the image histogram. This function applies a non-linear
    mapping to the input image, in order to create a uniform
    distribution of grayscale values in the output image.

    :param image: The image to equalize.
    :param mask: An optional mask.  If given, only the pixels selected by
                 the mask are included in the analysis.
    :return: An image.
    """
    if image.mode == "P":
        image = image.convert("RGB")
    h = image.histogram(mask)
    lut = []
    for b in range(0, len(h), 256):
        histo = [_f for _f in h[b : b + 256] if _f]
        if len(histo) <= 1:
            lut.extend(list(range(256)))
        else:
            step = (functools.reduce(operator.add, histo) - histo[-1]) // 255
            if not step:
                lut.extend(list(range(256)))
            else:
                n = step // 2
                for i in range(256):
                    lut.append(n // step)
                    n = n + h[i + b]
    return _lut(image, lut)


def expand(
    image: Image.Image,
    border: int | tuple[int, ...] = 0,
    fill: str | int | tuple[int, ...] = 0,
) -> Image.Image:
    """
    Add border to the image

    :param image: The image to expand.
    :param border: Border width, in pixels.
    :param fill: Pixel fill value (a color value).  Default is 0 (black).
    :return: An image.
    """
    left, top, right, bottom = _border(border)
    width = left + image.size[0] + right
    height = top + image.size[1] + bottom
    color = _color(fill, image.mode)
    if image.palette:
        palette = ImagePalette.ImagePalette(palette=image.getpalette())
        if isinstance(color, tuple) and (len(color) == 3 or len(color) == 4):
            color = palette.getcolor(color)
    else:
        palette = None
    out = Image.new(image.mode, (width, height), color)
    if palette:
        out.putpalette(palette.palette)
    out.paste(image, (left, top))
    return out


def fit(
    image: Image.Image,
    size: tuple[int, int],
    method: int = Image.Resampling.BICUBIC,
    bleed: float = 0.0,
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    """
    Returns a resized and cropped version of the image, cropped to the
    requested aspect ratio and size.

    This function was contributed by Kevin Cazabon.

    :param image: The image to resize and crop.
    :param size: The requested output size in pixels, given as a
                 (width, height) tuple.
    :param method: Resampling method to use. Default is
                   :py:attr:`~PIL.Image.Resampling.BICUBIC`.
                   See :ref:`concept-filters`.
    :param bleed: Remove a border around the outside of the image from all
                  four edges. The value is a decimal percentage (use 0.01 for
                  one percent). The default value is 0 (no border).
                  Cannot be greater than or equal to 0.5.
    :param centering: Control the cropping position.  Use (0.5, 0.5) for
                      center cropping (e.g. if cropping the width, take 50% off
                      of the left side, and therefore 50% off the right side).
                      (0.0, 0.0) will crop from the top left corner (i.e. if
                      cropping the width, take all of the crop off of the right
                      side, and if cropping the height, take all of it off the
                      bottom).  (1.0, 0.0) will crop from the bottom left
                      corner, etc. (i.e. if cropping the width, take all of the
                      crop off the left side, and if cropping the height take
                      none from the top, and therefore all off the bottom).
    :return: An image.
    """

    # by Kevin Cazabon, Feb 17/2000
    # kevin@cazabon.com
    # https://www.cazabon.com

    centering_x, centering_y = centering

    if not 0.0 <= centering_x <= 1.0:
        centering_x = 0.5
    if not 0.0 <= centering_y <= 1.0:
        centering_y = 0.5

    if not 0.0 <= bleed < 0.5:
        bleed = 0.0

    # calculate the area to use for resizing and cropping, subtracting
    # the 'bleed' around the edges

    # number of pixels to trim off on Top and Bottom, Left and Right
    bleed_pixels = (bleed * image.size[0], bleed * image.size[1])

    live_size = (
        image.size[0] - bleed_pixels[0] * 2,
        image.size[1] - bleed_pixels[1] * 2,
    )

    # calculate the aspect ratio of the live_size
    live_size_ratio = live_size[0] / live_size[1]

    # calculate the aspect ratio of the output image
    output_ratio = size[0] / size[1]

    # figure out if the sides or top/bottom will be cropped off
    if live_size_ratio == output_ratio:
        # live_size is already the needed ratio
        crop_width = live_size[0]
        crop_height = live_size[1]
    elif live_size_ratio >= output_ratio:
        # live_size is wider than what's needed, crop the sides
        crop_width = output_ratio * live_size[1]
        crop_height = live_size[1]
    else:
        # live_size is taller than what's needed, crop the top and bottom
        crop_width = live_size[0]
        crop_height = live_size[0] / output_ratio

    # make the crop
    crop_left = bleed_pixels[0] + (live_size[0] - crop_width) * centering_x
    crop_top = bleed_pixels[1] + (live_size[1] - crop_height) * centering_y

    crop = (crop_left, crop_top, crop_left + crop_width, crop_top + crop_height)

    # resize the image and return it
    return image.resize(size, method, box=crop)


def flip(image: Image.Image) -> Image.Image:
    """
    Flip the image vertically (top to bottom).

    :param image: The image to flip.
    :return: An image.
    """
    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)


def grayscale(image: Image.Image) -> Image.Image:
    """
    Convert the image to grayscale.

    :param image: The image to convert.
    :return: An image.
    """
    return image.convert("L")


def invert(image: Image.Image) -> Image.Image:
    """
    Invert (negate) the image.

    :param image: The image to invert.
    :return: An image.
    """
    lut = list(range(255, -1, -1))
    return image.point(lut) if image.mode == "1" else _lut(image, lut)


def mirror(image: Image.Image) -> Image.Image:
    """
    Flip image horizontally (left to right).

    :param image: The image to mirror.
    :return: An image.
    """
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def posterize(image: Image.Image, bits: int) -> Image.Image:
    """
    Reduce the number of bits for each color channel.

    :param image: The image to posterize.
    :param bits: The number of bits to keep for each channel (1-8).
    :return: An image.
    """
    mask = ~(2 ** (8 - bits) - 1)
    lut = [i & mask for i in range(256)]
    return _lut(image, lut)


def solarize(image: Image.Image, threshold: int = 128) -> Image.Image:
    """
    Invert all pixel values above a threshold.

    :param image: The image to solarize.
    :param threshold: All pixels above this grayscale level are inverted.
    :return: An image.
    """
    lut = []
    for i in range(256):
        if i < threshold:
            lut.append(i)
        else:
            lut.append(255 - i)
    return _lut(image, lut)


@overload
def exif_transpose(image: Image.Image, *, in_place: Literal[True]) -> None: ...


@overload
def exif_transpose(
    image: Image.Image, *, in_place: Literal[False] = False
) -> Image.Image: ...


def exif_transpose(image: Image.Image, *, in_place: bool = False) -> Image.Image | None:
    """
    If an image has an EXIF Orientation tag, other than 1, transpose the image
    accordingly, and remove the orientation data.

    :param image: The image to transpose.
    :param in_place: Boolean. Keyword-only argument.
        If ``True``, the original image is modified in-place, and ``None`` is returned.
        If ``False`` (default), a new :py:class:`~PIL.Image.Image` object is returned
        with the transposition applied. If there is no transposition, a copy of the
        image will be returned.
    """
    image.load()
    image_exif = image.getexif()
    orientation = image_exif.get(ExifTags.Base.Orientation, 1)
    method = {
        2: Image.Transpose.FLIP_LEFT_RIGHT,
        3: Image.Transpose.ROTATE_180,
        4: Image.Transpose.FLIP_TOP_BOTTOM,
        5: Image.Transpose.TRANSPOSE,
        6: Image.Transpose.ROTATE_270,
        7: Image.Transpose.TRANSVERSE,
        8: Image.Transpose.ROTATE_90,
    }.get(orientation)
    if method is not None:
        if in_place:
            image.im = image.im.transpose(method)
            image._size = image.im.size
        else:
            transposed_image = image.transpose(method)
        exif_image = image if in_place else transposed_image

        exif = exif_image.getexif()
        if ExifTags.Base.Orientation in exif:
            del exif[ExifTags.Base.Orientation]
            if "exif" in exif_image.info:
                exif_image.info["exif"] = exif.tobytes()
            elif "Raw profile type exif" in exif_image.info:
                exif_image.info["Raw profile type exif"] = exif.tobytes().hex()
            for key in ("XML:com.adobe.xmp", "xmp"):
                if key in exif_image.info:
                    for pattern in (
                        r'tiff:Orientation="([0-9])"',
                        r"<tiff:Orientation>([0-9])</tiff:Orientation>",
                    ):
                        value = exif_image.info[key]
                        if isinstance(value, str):
                            value = re.sub(pattern, "", value)
                        elif isinstance(value, tuple):
                            value = tuple(
                                re.sub(pattern.encode(), b"", v) for v in value
                            )
                        else:
                            value = re.sub(pattern.encode(), b"", value)
                        exif_image.info[key] = value
        if not in_place:
            return transposed_image
    elif not in_place:
        return image.copy()
    return None

# === NexusCore/openenv\Lib\site-packages\tornado\options.py ===
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

"""A command line parsing module that lets modules define their own options.

This module is inspired by Google's `gflags
<https://github.com/google/python-gflags>`_. The primary difference
with libraries such as `argparse` is that a global registry is used so
that options may be defined in any module (it also enables
`tornado.log` by default). The rest of Tornado does not depend on this
module, so feel free to use `argparse` or other configuration
libraries if you prefer them.

Options must be defined with `tornado.options.define` before use,
generally at the top level of a module. The options are then
accessible as attributes of `tornado.options.options`::

    # myapp/db.py
    from tornado.options import define, options

    define("mysql_host", default="127.0.0.1:3306", help="Main user DB")
    define("memcache_hosts", default="127.0.0.1:11011", multiple=True,
           help="Main user memcache servers")

    def connect():
        db = database.Connection(options.mysql_host)
        ...

    # myapp/server.py
    from tornado.options import define, options

    define("port", default=8080, help="port to listen on")

    def start_server():
        app = make_app()
        app.listen(options.port)

The ``main()`` method of your application does not need to be aware of all of
the options used throughout your program; they are all automatically loaded
when the modules are loaded.  However, all modules that define options
must have been imported before the command line is parsed.

Your ``main()`` method can parse the command line or parse a config file with
either `parse_command_line` or `parse_config_file`::

    import myapp.db, myapp.server
    import tornado

    if __name__ == '__main__':
        tornado.options.parse_command_line()
        # or
        tornado.options.parse_config_file("/etc/server.conf")

.. note::

   When using multiple ``parse_*`` functions, pass ``final=False`` to all
   but the last one, or side effects may occur twice (in particular,
   this can result in log messages being doubled).

`tornado.options.options` is a singleton instance of `OptionParser`, and
the top-level functions in this module (`define`, `parse_command_line`, etc)
simply call methods on it.  You may create additional `OptionParser`
instances to define isolated sets of options, such as for subcommands.

.. note::

   By default, several options are defined that will configure the
   standard `logging` module when `parse_command_line` or `parse_config_file`
   are called.  If you want Tornado to leave the logging configuration
   alone so you can manage it yourself, either pass ``--logging=none``
   on the command line or do the following to disable it in code::

       from tornado.options import options, parse_command_line
       options.logging = None
       parse_command_line()

.. note::

   `parse_command_line` or `parse_config_file` function should called after
   logging configuration and user-defined command line flags using the
   ``callback`` option definition, or these configurations will not take effect.

.. versionchanged:: 4.3
   Dashes and underscores are fully interchangeable in option names;
   options can be defined, set, and read with any mix of the two.
   Dashes are typical for command-line usage while config files require
   underscores.
"""

import datetime
import numbers
import re
import sys
import os
import textwrap

from tornado.escape import _unicode, native_str
from tornado.log import define_logging_options
from tornado.util import basestring_type, exec_in

from typing import (
    Any,
    Iterator,
    Iterable,
    Tuple,
    Set,
    Dict,
    Callable,
    List,
    TextIO,
    Optional,
)


class Error(Exception):
    """Exception raised by errors in the options module."""

    pass


class OptionParser:
    """A collection of options, a dictionary with object-like access.

    Normally accessed via static functions in the `tornado.options` module,
    which reference a global instance.
    """

    def __init__(self) -> None:
        # we have to use self.__dict__ because we override setattr.
        self.__dict__["_options"] = {}
        self.__dict__["_parse_callbacks"] = []
        self.define(
            "help",
            type=bool,
            help="show this help information",
            callback=self._help_callback,
        )

    def _normalize_name(self, name: str) -> str:
        return name.replace("_", "-")

    def __getattr__(self, name: str) -> Any:
        name = self._normalize_name(name)
        if isinstance(self._options.get(name), _Option):
            return self._options[name].value()
        raise AttributeError("Unrecognized option %r" % name)

    def __setattr__(self, name: str, value: Any) -> None:
        name = self._normalize_name(name)
        if isinstance(self._options.get(name), _Option):
            return self._options[name].set(value)
        raise AttributeError("Unrecognized option %r" % name)

    def __iter__(self) -> Iterator:
        return (opt.name for opt in self._options.values())

    def __contains__(self, name: str) -> bool:
        name = self._normalize_name(name)
        return name in self._options

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def __setitem__(self, name: str, value: Any) -> None:
        return self.__setattr__(name, value)

    def items(self) -> Iterable[Tuple[str, Any]]:
        """An iterable of (name, value) pairs.

        .. versionadded:: 3.1
        """
        return [(opt.name, opt.value()) for name, opt in self._options.items()]

    def groups(self) -> Set[str]:
        """The set of option-groups created by ``define``.

        .. versionadded:: 3.1
        """
        return {opt.group_name for opt in self._options.values()}

    def group_dict(self, group: str) -> Dict[str, Any]:
        """The names and values of options in a group.

        Useful for copying options into Application settings::

            from tornado.options import define, parse_command_line, options

            define('template_path', group='application')
            define('static_path', group='application')

            parse_command_line()

            application = Application(
                handlers, **options.group_dict('application'))

        .. versionadded:: 3.1
        """
        return {
            opt.name: opt.value()
            for name, opt in self._options.items()
            if not group or group == opt.group_name
        }

    def as_dict(self) -> Dict[str, Any]:
        """The names and values of all options.

        .. versionadded:: 3.1
        """
        return {opt.name: opt.value() for name, opt in self._options.items()}

    def define(
        self,
        name: str,
        default: Any = None,
        type: Optional[type] = None,
        help: Optional[str] = None,
        metavar: Optional[str] = None,
        multiple: bool = False,
        group: Optional[str] = None,
        callback: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Defines a new command line option.

        ``type`` can be any of `str`, `int`, `float`, `bool`,
        `~datetime.datetime`, or `~datetime.timedelta`. If no ``type``
        is given but a ``default`` is, ``type`` is the type of
        ``default``. Otherwise, ``type`` defaults to `str`.

        If ``multiple`` is True, the option value is a list of ``type``
        instead of an instance of ``type``.

        ``help`` and ``metavar`` are used to construct the
        automatically generated command line help string. The help
        message is formatted like::

           --name=METAVAR      help string

        ``group`` is used to group the defined options in logical
        groups. By default, command line options are grouped by the
        file in which they are defined.

        Command line option names must be unique globally.

        If a ``callback`` is given, it will be run with the new value whenever
        the option is changed.  This can be used to combine command-line
        and file-based options::

            define("config", type=str, help="path to config file",
                   callback=lambda path: parse_config_file(path, final=False))

        With this definition, options in the file specified by ``--config`` will
        override options set earlier on the command line, but can be overridden
        by later flags.

        """
        normalized = self._normalize_name(name)
        if normalized in self._options:
            raise Error(
                "Option %r already defined in %s"
                % (normalized, self._options[normalized].file_name)
            )
        frame = sys._getframe(0)
        if frame is not None:
            options_file = frame.f_code.co_filename

            # Can be called directly, or through top level define() fn, in which
            # case, step up above that frame to look for real caller.
            if (
                frame.f_back is not None
                and frame.f_back.f_code.co_filename == options_file
                and frame.f_back.f_code.co_name == "define"
            ):
                frame = frame.f_back

            assert frame.f_back is not None
            file_name = frame.f_back.f_code.co_filename
        else:
            file_name = "<unknown>"
        if file_name == options_file:
            file_name = ""
        if type is None:
            if not multiple and default is not None:
                type = default.__class__
            else:
                type = str
        if group:
            group_name = group  # type: Optional[str]
        else:
            group_name = file_name
        option = _Option(
            name,
            file_name=file_name,
            default=default,
            type=type,
            help=help,
            metavar=metavar,
            multiple=multiple,
            group_name=group_name,
            callback=callback,
        )
        self._options[normalized] = option

    def parse_command_line(
        self, args: Optional[List[str]] = None, final: bool = True
    ) -> List[str]:
        """Parses all options given on the command line (defaults to
        `sys.argv`).

        Options look like ``--option=value`` and are parsed according
        to their ``type``. For boolean options, ``--option`` is
        equivalent to ``--option=true``

        If the option has ``multiple=True``, comma-separated values
        are accepted. For multi-value integer options, the syntax
        ``x:y`` is also accepted and equivalent to ``range(x, y)``.

        Note that ``args[0]`` is ignored since it is the program name
        in `sys.argv`.

        We return a list of all arguments that are not parsed as options.

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.

        """
        if args is None:
            args = sys.argv
        remaining = []  # type: List[str]
        for i in range(1, len(args)):
            # All things after the last option are command line arguments
            if not args[i].startswith("-"):
                remaining = args[i:]
                break
            if args[i] == "--":
                remaining = args[i + 1 :]
                break
            arg = args[i].lstrip("-")
            name, equals, value = arg.partition("=")
            name = self._normalize_name(name)
            if name not in self._options:
                self.print_help()
                raise Error("Unrecognized command line option: %r" % name)
            option = self._options[name]
            if not equals:
                if option.type == bool:
                    value = "true"
                else:
                    raise Error("Option %r requires a value" % name)
            option.parse(value)

        if final:
            self.run_parse_callbacks()

        return remaining

    def parse_config_file(self, path: str, final: bool = True) -> None:
        """Parses and loads the config file at the given path.

        The config file contains Python code that will be executed (so
        it is **not safe** to use untrusted config files). Anything in
        the global namespace that matches a defined option will be
        used to set that option's value.

        Options may either be the specified type for the option or
        strings (in which case they will be parsed the same way as in
        `.parse_command_line`)

        Example (using the options defined in the top-level docs of
        this module)::

            port = 80
            mysql_host = 'mydb.example.com:3306'
            # Both lists and comma-separated strings are allowed for
            # multiple=True.
            memcache_hosts = ['cache1.example.com:11011',
                              'cache2.example.com:11011']
            memcache_hosts = 'cache1.example.com:11011,cache2.example.com:11011'

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.

        .. note::

            `tornado.options` is primarily a command-line library.
            Config file support is provided for applications that wish
            to use it, but applications that prefer config files may
            wish to look at other libraries instead.

        .. versionchanged:: 4.1
           Config files are now always interpreted as utf-8 instead of
           the system default encoding.

        .. versionchanged:: 4.4
           The special variable ``__file__`` is available inside config
           files, specifying the absolute path to the config file itself.

        .. versionchanged:: 5.1
           Added the ability to set options via strings in config files.

        """
        config = {"__file__": os.path.abspath(path)}
        with open(path, "rb") as f:
            exec_in(native_str(f.read()), config, config)
        for name in config:
            normalized = self._normalize_name(name)
            if normalized in self._options:
                option = self._options[normalized]
                if option.multiple:
                    if not isinstance(config[name], (list, str)):
                        raise Error(
                            "Option %r is required to be a list of %s "
                            "or a comma-separated string"
                            % (option.name, option.type.__name__)
                        )

                if type(config[name]) is str and (
                    option.type is not str or option.multiple
                ):
                    option.parse(config[name])
                else:
                    option.set(config[name])

        if final:
            self.run_parse_callbacks()

    def print_help(self, file: Optional[TextIO] = None) -> None:
        """Prints all the command line options to stderr (or another file)."""
        if file is None:
            file = sys.stderr
        print("Usage: %s [OPTIONS]" % sys.argv[0], file=file)
        print("\nOptions:\n", file=file)
        by_group = {}  # type: Dict[str, List[_Option]]
        for option in self._options.values():
            by_group.setdefault(option.group_name, []).append(option)

        for filename, o in sorted(by_group.items()):
            if filename:
                print("\n%s options:\n" % os.path.normpath(filename), file=file)
            o.sort(key=lambda option: option.name)
            for option in o:
                # Always print names with dashes in a CLI context.
                prefix = self._normalize_name(option.name)
                if option.metavar:
                    prefix += "=" + option.metavar
                description = option.help or ""
                if option.default is not None and option.default != "":
                    description += " (default %s)" % option.default
                lines = textwrap.wrap(description, 79 - 35)
                if len(prefix) > 30 or len(lines) == 0:
                    lines.insert(0, "")
                print("  --%-30s %s" % (prefix, lines[0]), file=file)
                for line in lines[1:]:
                    print("%-34s %s" % (" ", line), file=file)
        print(file=file)

    def _help_callback(self, value: bool) -> None:
        if value:
            self.print_help()
            sys.exit(0)

    def add_parse_callback(self, callback: Callable[[], None]) -> None:
        """Adds a parse callback, to be invoked when option parsing is done."""
        self._parse_callbacks.append(callback)

    def run_parse_callbacks(self) -> None:
        for callback in self._parse_callbacks:
            callback()

    def mockable(self) -> "_Mockable":
        """Returns a wrapper around self that is compatible with
        `unittest.mock.patch`.

        The `unittest.mock.patch` function is incompatible with objects like ``options`` that
        override ``__getattr__`` and ``__setattr__``.  This function returns an object that can be
        used with `mock.patch.object <unittest.mock.patch.object>` to modify option values::

            with mock.patch.object(options.mockable(), 'name', value):
                assert options.name == value
        """
        return _Mockable(self)


class _Mockable:
    """`mock.patch` compatible wrapper for `OptionParser`.

    As of ``mock`` version 1.0.1, when an object uses ``__getattr__``
    hooks instead of ``__dict__``, ``patch.__exit__`` tries to delete
    the attribute it set instead of setting a new one (assuming that
    the object does not capture ``__setattr__``, so the patch
    created a new attribute in ``__dict__``).

    _Mockable's getattr and setattr pass through to the underlying
    OptionParser, and delattr undoes the effect of a previous setattr.
    """

    def __init__(self, options: OptionParser) -> None:
        # Modify __dict__ directly to bypass __setattr__
        self.__dict__["_options"] = options
        self.__dict__["_originals"] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._options, name)

    def __setattr__(self, name: str, value: Any) -> None:
        assert name not in self._originals, "don't reuse mockable objects"
        self._originals[name] = getattr(self._options, name)
        setattr(self._options, name, value)

    def __delattr__(self, name: str) -> None:
        setattr(self._options, name, self._originals.pop(name))


class _Option:
    # This class could almost be made generic, but the way the types
    # interact with the multiple argument makes this tricky. (default
    # and the callback use List[T], but type is still Type[T]).
    UNSET = object()

    def __init__(
        self,
        name: str,
        default: Any = None,
        type: Optional[type] = None,
        help: Optional[str] = None,
        metavar: Optional[str] = None,
        multiple: bool = False,
        file_name: Optional[str] = None,
        group_name: Optional[str] = None,
        callback: Optional[Callable[[Any], None]] = None,
    ) -> None:
        if default is None and multiple:
            default = []
        self.name = name
        if type is None:
            raise ValueError("type must not be None")
        self.type = type
        self.help = help
        self.metavar = metavar
        self.multiple = multiple
        self.file_name = file_name
        self.group_name = group_name
        self.callback = callback
        self.default = default
        self._value = _Option.UNSET  # type: Any

    def value(self) -> Any:
        return self.default if self._value is _Option.UNSET else self._value

    def parse(self, value: str) -> Any:
        _parse = {
            datetime.datetime: self._parse_datetime,
            datetime.timedelta: self._parse_timedelta,
            bool: self._parse_bool,
            basestring_type: self._parse_string,
        }.get(
            self.type, self.type
        )  # type: Callable[[str], Any]
        if self.multiple:
            self._value = []
            for part in value.split(","):
                if issubclass(self.type, numbers.Integral):
                    # allow ranges of the form X:Y (inclusive at both ends)
                    lo_str, _, hi_str = part.partition(":")
                    lo = _parse(lo_str)
                    hi = _parse(hi_str) if hi_str else lo
                    self._value.extend(range(lo, hi + 1))
                else:
                    self._value.append(_parse(part))
        else:
            self._value = _parse(value)
        if self.callback is not None:
            self.callback(self._value)
        return self.value()

    def set(self, value: Any) -> None:
        if self.multiple:
            if not isinstance(value, list):
                raise Error(
                    "Option %r is required to be a list of %s"
                    % (self.name, self.type.__name__)
                )
            for item in value:
                if item is not None and not isinstance(item, self.type):
                    raise Error(
                        "Option %r is required to be a list of %s"
                        % (self.name, self.type.__name__)
                    )
        else:
            if value is not None and not isinstance(value, self.type):
                raise Error(
                    "Option %r is required to be a %s (%s given)"
                    % (self.name, self.type.__name__, type(value))
                )
        self._value = value
        if self.callback is not None:
            self.callback(self._value)

    # Supported date/time formats in our options
    _DATETIME_FORMATS = [
        "%a %b %d %H:%M:%S %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d",
        "%H:%M:%S",
        "%H:%M",
    ]

    def _parse_datetime(self, value: str) -> datetime.datetime:
        for format in self._DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                pass
        raise Error("Unrecognized date/time format: %r" % value)

    _TIMEDELTA_ABBREV_DICT = {
        "h": "hours",
        "m": "minutes",
        "min": "minutes",
        "s": "seconds",
        "sec": "seconds",
        "ms": "milliseconds",
        "us": "microseconds",
        "d": "days",
        "w": "weeks",
    }

    _FLOAT_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

    _TIMEDELTA_PATTERN = re.compile(
        r"\s*(%s)\s*(\w*)\s*" % _FLOAT_PATTERN, re.IGNORECASE
    )

    def _parse_timedelta(self, value: str) -> datetime.timedelta:
        try:
            sum = datetime.timedelta()
            start = 0
            while start < len(value):
                m = self._TIMEDELTA_PATTERN.match(value, start)
                if not m:
                    raise Exception()
                num = float(m.group(1))
                units = m.group(2) or "seconds"
                units = self._TIMEDELTA_ABBREV_DICT.get(units, units)

                sum += datetime.timedelta(**{units: num})
                start = m.end()
            return sum
        except Exception:
            raise

    def _parse_bool(self, value: str) -> bool:
        return value.lower() not in ("false", "0", "f")

    def _parse_string(self, value: str) -> str:
        return _unicode(value)


options = OptionParser()
"""Global options object.

All defined options are available as attributes on this object.
"""


def define(
    name: str,
    default: Any = None,
    type: Optional[type] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
    multiple: bool = False,
    group: Optional[str] = None,
    callback: Optional[Callable[[Any], None]] = None,
) -> None:
    """Defines an option in the global namespace.

    See `OptionParser.define`.
    """
    return options.define(
        name,
        default=default,
        type=type,
        help=help,
        metavar=metavar,
        multiple=multiple,
        group=group,
        callback=callback,
    )


def parse_command_line(
    args: Optional[List[str]] = None, final: bool = True
) -> List[str]:
    """Parses global options from the command line.

    See `OptionParser.parse_command_line`.
    """
    return options.parse_command_line(args, final=final)


def parse_config_file(path: str, final: bool = True) -> None:
    """Parses global options from a config file.

    See `OptionParser.parse_config_file`.
    """
    return options.parse_config_file(path, final=final)


def print_help(file: Optional[TextIO] = None) -> None:
    """Prints all the command line options to stderr (or another file).

    See `OptionParser.print_help`.
    """
    return options.print_help(file)


def add_parse_callback(callback: Callable[[], None]) -> None:
    """Adds a parse callback, to be invoked when option parsing is done.

    See `OptionParser.add_parse_callback`
    """
    options.add_parse_callback(callback)


# Default options
define_logging_options(options)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_browser_context.py ===
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
import json
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    Cookie,
    Geolocation,
    SetCookieParam,
    StorageState,
)
from playwright._impl._artifact import Artifact
from playwright._impl._cdp_session import CDPSession
from playwright._impl._clock import Clock
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._dialog import Dialog
from playwright._impl._errors import Error, TargetClosedError
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._har_router import HarRouter
from playwright._impl._helper import (
    HarContentPolicy,
    HarMode,
    HarRecordingMetadata,
    RouteFromHarNotFoundPolicy,
    RouteHandler,
    RouteHandlerCallback,
    TimeoutSettings,
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    async_writefile,
    locals_to_params,
    parse_error,
    prepare_record_har_options,
    to_impl,
)
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocketRoute,
    WebSocketRouteHandler,
    serialize_headers,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._tracing import Tracing
from playwright._impl._waiter import Waiter
from playwright._impl._web_error import WebError

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser import Browser


class BrowserContext(ChannelOwner):
    Events = SimpleNamespace(
        BackgroundPage="backgroundpage",
        Close="close",
        Console="console",
        Dialog="dialog",
        Page="page",
        WebError="weberror",
        ServiceWorker="serviceworker",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # circular import workaround:
        self._browser: Optional["Browser"] = None
        if parent.__class__.__name__ == "Browser":
            self._browser = cast("Browser", parent)
            self._browser._contexts.append(self)
        self._pages: List[Page] = []
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []
        self._bindings: Dict[str, Any] = {}
        self._timeout_settings = TimeoutSettings(None)
        self._owner_page: Optional[Page] = None
        self._options: Dict[str, Any] = {}
        self._background_pages: Set[Page] = set()
        self._service_workers: Set[Worker] = set()
        self._tracing = cast(Tracing, from_channel(initializer["tracing"]))
        self._har_recorders: Dict[str, HarRecordingMetadata] = {}
        self._request: APIRequestContext = from_channel(initializer["requestContext"])
        self._clock = Clock(self)
        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on(
            "page", lambda params: self._on_page(from_channel(params["page"]))
        )
        self._channel.on(
            "route",
            lambda params: self._loop.create_task(
                self._on_route(
                    from_channel(params.get("route")),
                )
            ),
        )
        self._channel.on(
            "webSocketRoute",
            lambda params: self._loop.create_task(
                self._on_web_socket_route(
                    from_channel(params["webSocketRoute"]),
                )
            ),
        )
        self._channel.on(
            "backgroundPage",
            lambda params: self._on_background_page(from_channel(params["page"])),
        )

        self._channel.on(
            "serviceWorker",
            lambda params: self._on_service_worker(from_channel(params["worker"])),
        )
        self._channel.on(
            "console",
            lambda event: self._on_console_message(event),
        )

        self._channel.on(
            "dialog", lambda params: self._on_dialog(from_channel(params["dialog"]))
        )
        self._channel.on(
            "pageError",
            lambda params: self._on_page_error(
                parse_error(params["error"]["error"]),
                from_nullable_channel(params["page"]),
            ),
        )
        self._channel.on(
            "request",
            lambda params: self._on_request(
                from_channel(params["request"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "response",
            lambda params: self._on_response(
                from_channel(params["response"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFailed",
            lambda params: self._on_request_failed(
                from_channel(params["request"]),
                params["responseEndTiming"],
                params.get("failureText"),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFinished",
            lambda params: self._on_request_finished(
                from_channel(params["request"]),
                from_nullable_channel(params.get("response")),
                params["responseEndTiming"],
                from_nullable_channel(params.get("page")),
            ),
        )
        self._closed_future: asyncio.Future = asyncio.Future()
        self.once(
            self.Events.Close, lambda context: self._closed_future.set_result(True)
        )
        self._close_reason: Optional[str] = None
        self._har_routers: List[HarRouter] = []
        self._set_event_to_subscription_mapping(
            {
                BrowserContext.Events.Console: "console",
                BrowserContext.Events.Dialog: "dialog",
                BrowserContext.Events.Request: "request",
                BrowserContext.Events.Response: "response",
                BrowserContext.Events.RequestFinished: "requestFinished",
                BrowserContext.Events.RequestFailed: "requestFailed",
            }
        )
        self._close_was_called = False

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"

    def _on_page(self, page: Page) -> None:
        self._pages.append(page)
        self.emit(BrowserContext.Events.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Page.Events.Popup, page)

    async def _on_route(self, route: Route) -> None:
        route._context = self
        page = route.request._safe_page()
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            # If the page or the context was closed we stall all requests right away.
            if (page and page._close_was_called) or self._close_was_called:
                return
            if not route_handler.matches(route.request.url):
                continue
            if route_handler not in self._routes:
                continue
            if route_handler.will_expire:
                self._routes.remove(route_handler)
            try:
                handled = await route_handler.handle(route)
            finally:
                if len(self._routes) == 0:
                    asyncio.create_task(
                        self._connection.wrap_api_call(
                            lambda: self._update_interception_patterns(), True
                        )
                    )
            if handled:
                return
        try:
            # If the page is closed or unrouteAll() was called without waiting and interception disabled,
            # the method will throw an error - silence it.
            await route._inner_continue(True)
        except Exception:
            pass

    async def _on_web_socket_route(self, web_socket_route: WebSocketRoute) -> None:
        route_handler = next(
            (
                route_handler
                for route_handler in self._web_socket_routes
                if route_handler.matches(web_socket_route.url)
            ),
            None,
        )
        if route_handler:
            await route_handler.handle(web_socket_route)
        else:
            web_socket_route.connect_to_server()

    def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func is None:
            return
        asyncio.create_task(binding_call.call(func))

    def set_default_navigation_timeout(self, timeout: float) -> None:
        return self._set_default_navigation_timeout_impl(timeout)

    def _set_default_navigation_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultNavigationTimeoutNoReply",
            {} if timeout is None else {"timeout": timeout},
        )

    def set_default_timeout(self, timeout: float) -> None:
        return self._set_default_timeout_impl(timeout)

    def _set_default_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultTimeoutNoReply", {} if timeout is None else {"timeout": timeout}
        )

    @property
    def pages(self) -> List[Page]:
        return self._pages.copy()

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

    def _set_options(self, context_options: Dict, browser_options: Dict) -> None:
        self._options = context_options
        if self._options.get("recordHar"):
            self._har_recorders[""] = {
                "path": self._options["recordHar"]["path"],
                "content": self._options["recordHar"].get("content"),
            }
        self._tracing._traces_dir = browser_options.get("tracesDir")

    async def new_page(self) -> Page:
        if self._owner_page:
            raise Error("Please use browser.new_context()")
        return from_channel(await self._channel.send("newPage"))

    async def cookies(self, urls: Union[str, Sequence[str]] = None) -> List[Cookie]:
        if urls is None:
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        return await self._channel.send("cookies", dict(urls=urls))

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.send("addCookies", dict(cookies=cookies))

    async def clear_cookies(
        self,
        name: Union[str, Pattern[str]] = None,
        domain: Union[str, Pattern[str]] = None,
        path: Union[str, Pattern[str]] = None,
    ) -> None:
        await self._channel.send(
            "clearCookies",
            {
                "name": name if isinstance(name, str) else None,
                "nameRegexSource": name.pattern if isinstance(name, Pattern) else None,
                "nameRegexFlags": (
                    escape_regex_flags(name) if isinstance(name, Pattern) else None
                ),
                "domain": domain if isinstance(domain, str) else None,
                "domainRegexSource": (
                    domain.pattern if isinstance(domain, Pattern) else None
                ),
                "domainRegexFlags": (
                    escape_regex_flags(domain) if isinstance(domain, Pattern) else None
                ),
                "path": path if isinstance(path, str) else None,
                "pathRegexSource": path.pattern if isinstance(path, Pattern) else None,
                "pathRegexFlags": (
                    escape_regex_flags(path) if isinstance(path, Pattern) else None
                ),
            },
        )

    async def grant_permissions(
        self, permissions: Sequence[str], origin: str = None
    ) -> None:
        await self._channel.send("grantPermissions", locals_to_params(locals()))

    async def clear_permissions(self) -> None:
        await self._channel.send("clearPermissions")

    async def set_geolocation(self, geolocation: Geolocation = None) -> None:
        await self._channel.send("setGeolocation", locals_to_params(locals()))

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", dict(headers=serialize_headers(headers))
        )

    async def set_offline(self, offline: bool) -> None:
        await self._channel.send("setOffline", dict(offline=offline))

    async def add_init_script(
        self, script: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            script = (await async_readfile(path)).decode()
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        await self._channel.send("addInitScript", dict(source=script))

    async def expose_binding(
        self, name: str, callback: Callable, handle: bool = None
    ) -> None:
        for page in self._pages:
            if name in page._bindings:
                raise Error(
                    f'Function "{name}" has been already registered in one of the pages'
                )
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        self._bindings[name] = callback
        await self._channel.send(
            "exposeBinding", dict(name=name, needsHandle=handle or False)
        )

    async def expose_function(self, name: str, callback: Callable) -> None:
        await self.expose_binding(name, lambda source, *args: callback(*args))

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: int = None
    ) -> None:
        self._routes.insert(
            0,
            RouteHandler(
                self._options.get("baseURL"),
                url,
                handler,
                True if self._dispatcher_fiber else False,
                times,
            ),
        )
        await self._update_interception_patterns()

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback] = None
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            if route.url != url or (handler and route.handler != handler):
                remaining.append(route)
            else:
                removed.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[RouteHandler],
        remaining: List[RouteHandler],
        behavior: Literal["default", "ignoreErrors", "wait"] = None,
    ) -> None:
        self._routes = remaining
        await self._update_interception_patterns()
        if behavior is None or behavior == "default":
            return
        await asyncio.gather(*map(lambda router: router.stop(behavior), removed))  # type: ignore

    async def route_web_socket(
        self, url: URLMatch, handler: WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(self._options.get("baseURL"), url, handler),
        )
        await self._update_web_socket_interception_patterns()

    def _dispose_har_routers(self) -> None:
        for router in self._har_routers:
            router.dispose()
        self._har_routers = []

    async def unroute_all(
        self, behavior: Literal["default", "ignoreErrors", "wait"] = None
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    async def _record_into_har(
        self,
        har: Union[Path, str],
        page: Optional[Page] = None,
        url: Union[Pattern[str], str] = None,
        update_content: HarContentPolicy = None,
        update_mode: HarMode = None,
    ) -> None:
        params: Dict[str, Any] = {
            "options": prepare_record_har_options(
                {
                    "recordHarPath": har,
                    "recordHarContent": update_content or "attach",
                    "recordHarMode": update_mode or "minimal",
                    "recordHarUrlFilter": url,
                }
            )
        }
        if page:
            params["page"] = page._channel
        har_id = await self._channel.send("harStart", params)
        self._har_recorders[har_id] = {
            "path": str(har),
            "content": update_content or "attach",
        }

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Union[Pattern[str], str] = None,
        notFound: RouteFromHarNotFoundPolicy = None,
        update: bool = None,
        updateContent: Literal["attach", "embed"] = None,
        updateMode: HarMode = None,
    ) -> None:
        if update:
            await self._record_into_har(
                har=har,
                page=None,
                url=url,
                update_content=updateContent,
                update_mode=updateMode,
            )
            return
        router = await HarRouter.create(
            local_utils=self._connection.local_utils,
            file=str(har),
            not_found_action=notFound or "abort",
            url_matcher=url,
        )
        self._har_routers.append(router)
        await router.add_context_route(self)

    async def _update_interception_patterns(self) -> None:
        patterns = RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.send(
            "setNetworkInterceptionPatterns", {"patterns": patterns}
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        patterns = WebSocketRouteHandler.prepare_interception_patterns(
            self._web_socket_routes
        )
        await self._channel.send(
            "setWebSocketInterceptionPatterns", {"patterns": patterns}
        )

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        waiter = Waiter(self, f"browser_context.expect_event({event})")
        waiter.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if event != BrowserContext.Events.Close:
            waiter.reject_on_event(
                self, BrowserContext.Events.Close, lambda: TargetClosedError()
            )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    def _on_close(self) -> None:
        if self._browser:
            self._browser._contexts.remove(self)

        self._dispose_har_routers()
        self._tracing._reset_stack_counter()
        self.emit(BrowserContext.Events.Close, self)

    async def close(self, reason: str = None) -> None:
        if self._close_was_called:
            return
        self._close_reason = reason
        self._close_was_called = True

        await self._channel._connection.wrap_api_call(
            lambda: self.request.dispose(reason=reason), True
        )

        async def _inner_close() -> None:
            for har_id, params in self._har_recorders.items():
                har = cast(
                    Artifact,
                    from_channel(
                        await self._channel.send("harExport", {"harId": har_id})
                    ),
                )
                # Server side will compress artifact if content is attach or if file is .zip.
                is_compressed = params.get("content") == "attach" or params[
                    "path"
                ].endswith(".zip")
                need_compressed = params["path"].endswith(".zip")
                if is_compressed and not need_compressed:
                    tmp_path = params["path"] + ".tmp"
                    await har.save_as(tmp_path)
                    await self._connection.local_utils.har_unzip(
                        zipFile=tmp_path, harFile=params["path"]
                    )
                else:
                    await har.save_as(params["path"])
                await har.delete()

        await self._channel._connection.wrap_api_call(_inner_close, True)
        await self._channel.send("close", {"reason": reason})
        await self._closed_future

    async def storage_state(
        self, path: Union[str, Path] = None, indexedDB: bool = None
    ) -> StorageState:
        result = await self._channel.send_return_as_dict(
            "storageState", {"indexedDB": indexedDB}
        )
        if path:
            await async_writefile(path, json.dumps(result))
        return result

    def _effective_close_reason(self) -> Optional[str]:
        if self._close_reason:
            return self._close_reason
        if self._browser:
            return self._browser._close_reason
        return None

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def expect_console_message(
        self,
        predicate: Callable[[ConsoleMessage], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(Page.Events.Console, predicate, timeout)

    def expect_page(
        self,
        predicate: Callable[[Page], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(BrowserContext.Events.Page, predicate, timeout)

    def _on_background_page(self, page: Page) -> None:
        self._background_pages.add(page)
        self.emit(BrowserContext.Events.BackgroundPage, page)

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(BrowserContext.Events.ServiceWorker, worker)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFailed, request)
        if page:
            page.emit(Page.Events.RequestFailed, request)

    def _on_request_finished(
        self,
        request: Request,
        response: Optional[Response],
        response_end_timing: float,
        page: Optional[Page],
    ) -> None:
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFinished, request)
        if page:
            page.emit(Page.Events.RequestFinished, request)
        if response:
            response._finished_future.set_result(True)

    def _on_console_message(self, event: Dict) -> None:
        message = ConsoleMessage(event, self._loop, self._dispatcher_fiber)
        self.emit(BrowserContext.Events.Console, message)
        page = message.page
        if page:
            page.emit(Page.Events.Console, message)

    def _on_dialog(self, dialog: Dialog) -> None:
        has_listeners = self.emit(BrowserContext.Events.Dialog, dialog)
        page = dialog.page
        if page:
            has_listeners = page.emit(Page.Events.Dialog, dialog) or has_listeners
        if not has_listeners:
            # Although we do similar handling on the server side, we still need this logic
            # on the client side due to a possible race condition between two async calls:
            # a) removing "dialog" listener subscription (client->server)
            # b) actual "dialog" event (server->client)
            if dialog.type == "beforeunload":
                asyncio.create_task(dialog.accept())
            else:
                asyncio.create_task(dialog.dismiss())

    def _on_page_error(self, error: Error, page: Optional[Page]) -> None:
        self.emit(
            BrowserContext.Events.WebError,
            WebError(self._loop, self._dispatcher_fiber, page, error),
        )
        if page:
            page.emit(Page.Events.PageError, error)

    def _on_request(self, request: Request, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Request, request)
        if page:
            page.emit(Page.Events.Request, request)

    def _on_response(self, response: Response, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Response, response)
        if page:
            page.emit(Page.Events.Response, response)

    @property
    def background_pages(self) -> List[Page]:
        return list(self._background_pages)

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        page = to_impl(page)
        params = {}
        if isinstance(page, Page):
            params["page"] = page._channel
        elif isinstance(page, Frame):
            params["frame"] = page._channel
        else:
            raise Error("page: expected Page or Frame")
        return from_channel(await self._channel.send("newCDPSession", params))

    @property
    def tracing(self) -> Tracing:
        return self._tracing

    @property
    def request(self) -> "APIRequestContext":
        return self._request

    @property
    def clock(self) -> Clock:
        return self._clock

# === NexusCore/openenv\Lib\site-packages\fsspec\core.py ===
from __future__ import annotations

import io
import logging
import os
import re
from glob import has_magic
from pathlib import Path

# for backwards compat, we export cache things from here too
from fsspec.caching import (  # noqa: F401
    BaseCache,
    BlockCache,
    BytesCache,
    MMapCache,
    ReadAheadCache,
    caches,
)
from fsspec.compression import compr
from fsspec.config import conf
from fsspec.registry import filesystem, get_filesystem_class
from fsspec.utils import (
    _unstrip_protocol,
    build_name_function,
    infer_compression,
    stringify_path,
)

logger = logging.getLogger("fsspec")


class OpenFile:
    """
    File-like object to be used in a context

    Can layer (buffered) text-mode and compression over any file-system, which
    are typically binary-only.

    These instances are safe to serialize, as the low-level file object
    is not created until invoked using ``with``.

    Parameters
    ----------
    fs: FileSystem
        The file system to use for opening the file. Should be a subclass or duck-type
        with ``fsspec.spec.AbstractFileSystem``
    path: str
        Location to open
    mode: str like 'rb', optional
        Mode of the opened file
    compression: str or None, optional
        Compression to apply
    encoding: str or None, optional
        The encoding to use if opened in text mode.
    errors: str or None, optional
        How to handle encoding errors if opened in text mode.
    newline: None or str
        Passed to TextIOWrapper in text mode, how to handle line endings.
    autoopen: bool
        If True, calls open() immediately. Mostly used by pickle
    pos: int
        If given and autoopen is True, seek to this location immediately
    """

    def __init__(
        self,
        fs,
        path,
        mode="rb",
        compression=None,
        encoding=None,
        errors=None,
        newline=None,
    ):
        self.fs = fs
        self.path = path
        self.mode = mode
        self.compression = get_compression(path, compression)
        self.encoding = encoding
        self.errors = errors
        self.newline = newline
        self.fobjects = []

    def __reduce__(self):
        return (
            OpenFile,
            (
                self.fs,
                self.path,
                self.mode,
                self.compression,
                self.encoding,
                self.errors,
                self.newline,
            ),
        )

    def __repr__(self):
        return f"<OpenFile '{self.path}'>"

    def __enter__(self):
        mode = self.mode.replace("t", "").replace("b", "") + "b"

        try:
            f = self.fs.open(self.path, mode=mode)
        except FileNotFoundError as e:
            if has_magic(self.path):
                raise FileNotFoundError(
                    "%s not found. The URL contains glob characters: you maybe needed\n"
                    "to pass expand=True in fsspec.open() or the storage_options of \n"
                    "your library. You can also set the config value 'open_expand'\n"
                    "before import, or fsspec.core.DEFAULT_EXPAND at runtime, to True.",
                    self.path,
                ) from e
            raise

        self.fobjects = [f]

        if self.compression is not None:
            compress = compr[self.compression]
            f = compress(f, mode=mode[0])
            self.fobjects.append(f)

        if "b" not in self.mode:
            # assume, for example, that 'r' is equivalent to 'rt' as in builtin
            f = PickleableTextIOWrapper(
                f, encoding=self.encoding, errors=self.errors, newline=self.newline
            )
            self.fobjects.append(f)

        return self.fobjects[-1]

    def __exit__(self, *args):
        self.close()

    @property
    def full_name(self):
        return _unstrip_protocol(self.path, self.fs)

    def open(self):
        """Materialise this as a real open file without context

        The OpenFile object should be explicitly closed to avoid enclosed file
        instances persisting. You must, therefore, keep a reference to the OpenFile
        during the life of the file-like it generates.
        """
        return self.__enter__()

    def close(self):
        """Close all encapsulated file objects"""
        for f in reversed(self.fobjects):
            if "r" not in self.mode and not f.closed:
                f.flush()
            f.close()
        self.fobjects.clear()


class OpenFiles(list):
    """List of OpenFile instances

    Can be used in a single context, which opens and closes all of the
    contained files. Normal list access to get the elements works as
    normal.

    A special case is made for caching filesystems - the files will
    be down/uploaded together at the start or end of the context, and
    this may happen concurrently, if the target filesystem supports it.
    """

    def __init__(self, *args, mode="rb", fs=None):
        self.mode = mode
        self.fs = fs
        self.files = []
        super().__init__(*args)

    def __enter__(self):
        if self.fs is None:
            raise ValueError("Context has already been used")

        fs = self.fs
        while True:
            if hasattr(fs, "open_many"):
                # check for concurrent cache download; or set up for upload
                self.files = fs.open_many(self)
                return self.files
            if hasattr(fs, "fs") and fs.fs is not None:
                fs = fs.fs
            else:
                break
        return [s.__enter__() for s in self]

    def __exit__(self, *args):
        fs = self.fs
        [s.__exit__(*args) for s in self]
        if "r" not in self.mode:
            while True:
                if hasattr(fs, "open_many"):
                    # check for concurrent cache upload
                    fs.commit_many(self.files)
                    return
                if hasattr(fs, "fs") and fs.fs is not None:
                    fs = fs.fs
                else:
                    break

    def __getitem__(self, item):
        out = super().__getitem__(item)
        if isinstance(item, slice):
            return OpenFiles(out, mode=self.mode, fs=self.fs)
        return out

    def __repr__(self):
        return f"<List of {len(self)} OpenFile instances>"


def open_files(
    urlpath,
    mode="rb",
    compression=None,
    encoding="utf8",
    errors=None,
    name_function=None,
    num=1,
    protocol=None,
    newline=None,
    auto_mkdir=True,
    expand=True,
    **kwargs,
):
    """Given a path or paths, return a list of ``OpenFile`` objects.

    For writing, a str path must contain the "*" character, which will be filled
    in by increasing numbers, e.g., "part*" ->  "part1", "part2" if num=2.

    For either reading or writing, can instead provide explicit list of paths.

    Parameters
    ----------
    urlpath: string or list
        Absolute or relative filepath(s). Prefix with a protocol like ``s3://``
        to read from alternative filesystems. To read from multiple files you
        can pass a globstring or a list of paths, with the caveat that they
        must all have the same protocol.
    mode: 'rb', 'wt', etc.
    compression: string or None
        If given, open file using compression codec. Can either be a compression
        name (a key in ``fsspec.compression.compr``) or "infer" to guess the
        compression from the filename suffix.
    encoding: str
        For text mode only
    errors: None or str
        Passed to TextIOWrapper in text mode
    name_function: function or None
        if opening a set of files for writing, those files do not yet exist,
        so we need to generate their names by formatting the urlpath for
        each sequence number
    num: int [1]
        if writing mode, number of files we expect to create (passed to
        name+function)
    protocol: str or None
        If given, overrides the protocol found in the URL.
    newline: bytes or None
        Used for line terminator in text mode. If None, uses system default;
        if blank, uses no translation.
    auto_mkdir: bool (True)
        If in write mode, this will ensure the target directory exists before
        writing, by calling ``fs.mkdirs(exist_ok=True)``.
    expand: bool
    **kwargs: dict
        Extra options that make sense to a particular storage connection, e.g.
        host, port, username, password, etc.

    Examples
    --------
    >>> files = open_files('2015-*-*.csv')  # doctest: +SKIP
    >>> files = open_files(
    ...     's3://bucket/2015-*-*.csv.gz', compression='gzip'
    ... )  # doctest: +SKIP

    Returns
    -------
    An ``OpenFiles`` instance, which is a list of ``OpenFile`` objects that can
    be used as a single context

    Notes
    -----
    For a full list of the available protocols and the implementations that
    they map across to see the latest online documentation:

    - For implementations built into ``fsspec`` see
      https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations
    - For implementations in separate packages see
      https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations
    """
    fs, fs_token, paths = get_fs_token_paths(
        urlpath,
        mode,
        num=num,
        name_function=name_function,
        storage_options=kwargs,
        protocol=protocol,
        expand=expand,
    )
    if fs.protocol == "file":
        fs.auto_mkdir = auto_mkdir
    elif "r" not in mode and auto_mkdir:
        parents = {fs._parent(path) for path in paths}
        for parent in parents:
            try:
                fs.makedirs(parent, exist_ok=True)
            except PermissionError:
                pass
    return OpenFiles(
        [
            OpenFile(
                fs,
                path,
                mode=mode,
                compression=compression,
                encoding=encoding,
                errors=errors,
                newline=newline,
            )
            for path in paths
        ],
        mode=mode,
        fs=fs,
    )


def _un_chain(path, kwargs):
    # Avoid a circular import
    from fsspec.implementations.cached import CachingFileSystem

    if "::" in path:
        x = re.compile(".*[^a-z]+.*")  # test for non protocol-like single word
        bits = []
        for p in path.split("::"):
            if "://" in p or x.match(p):
                bits.append(p)
            else:
                bits.append(p + "://")
    else:
        bits = [path]
    # [[url, protocol, kwargs], ...]
    out = []
    previous_bit = None
    kwargs = kwargs.copy()
    for bit in reversed(bits):
        protocol = kwargs.pop("protocol", None) or split_protocol(bit)[0] or "file"
        cls = get_filesystem_class(protocol)
        extra_kwargs = cls._get_kwargs_from_urls(bit)
        kws = kwargs.pop(protocol, {})
        if bit is bits[0]:
            kws.update(kwargs)
        kw = dict(
            **{k: v for k, v in extra_kwargs.items() if k not in kws or v != kws[k]},
            **kws,
        )
        bit = cls._strip_protocol(bit)
        if "target_protocol" not in kw and issubclass(cls, CachingFileSystem):
            bit = previous_bit
        out.append((bit, protocol, kw))
        previous_bit = bit
    out.reverse()
    return out


def url_to_fs(url, **kwargs):
    """
    Turn fully-qualified and potentially chained URL into filesystem instance

    Parameters
    ----------
    url : str
        The fsspec-compatible URL
    **kwargs: dict
        Extra options that make sense to a particular storage connection, e.g.
        host, port, username, password, etc.

    Returns
    -------
    filesystem : FileSystem
        The new filesystem discovered from ``url`` and created with
        ``**kwargs``.
    urlpath : str
        The file-systems-specific URL for ``url``.
    """
    url = stringify_path(url)
    # non-FS arguments that appear in fsspec.open()
    # inspect could keep this in sync with open()'s signature
    known_kwargs = {
        "compression",
        "encoding",
        "errors",
        "expand",
        "mode",
        "name_function",
        "newline",
        "num",
    }
    kwargs = {k: v for k, v in kwargs.items() if k not in known_kwargs}
    chain = _un_chain(url, kwargs)
    inkwargs = {}
    # Reverse iterate the chain, creating a nested target_* structure
    for i, ch in enumerate(reversed(chain)):
        urls, protocol, kw = ch
        if i == len(chain) - 1:
            inkwargs = dict(**kw, **inkwargs)
            continue
        inkwargs["target_options"] = dict(**kw, **inkwargs)
        inkwargs["target_protocol"] = protocol
        inkwargs["fo"] = urls
    urlpath, protocol, _ = chain[0]
    fs = filesystem(protocol, **inkwargs)
    return fs, urlpath


DEFAULT_EXPAND = conf.get("open_expand", False)


def open(
    urlpath,
    mode="rb",
    compression=None,
    encoding="utf8",
    errors=None,
    protocol=None,
    newline=None,
    expand=None,
    **kwargs,
):
    """Given a path or paths, return one ``OpenFile`` object.

    Parameters
    ----------
    urlpath: string or list
        Absolute or relative filepath. Prefix with a protocol like ``s3://``
        to read from alternative filesystems. Should not include glob
        character(s).
    mode: 'rb', 'wt', etc.
    compression: string or None
        If given, open file using compression codec. Can either be a compression
        name (a key in ``fsspec.compression.compr``) or "infer" to guess the
        compression from the filename suffix.
    encoding: str
        For text mode only
    errors: None or str
        Passed to TextIOWrapper in text mode
    protocol: str or None
        If given, overrides the protocol found in the URL.
    newline: bytes or None
        Used for line terminator in text mode. If None, uses system default;
        if blank, uses no translation.
    expand: bool or None
        Whether to regard file paths containing special glob characters as needing
        expansion (finding the first match) or absolute. Setting False allows using
        paths which do embed such characters. If None (default), this argument
        takes its value from the DEFAULT_EXPAND module variable, which takes
        its initial value from the "open_expand" config value at startup, which will
        be False if not set.
    **kwargs: dict
        Extra options that make sense to a particular storage connection, e.g.
        host, port, username, password, etc.

    Examples
    --------
    >>> openfile = open('2015-01-01.csv')  # doctest: +SKIP
    >>> openfile = open(
    ...     's3://bucket/2015-01-01.csv.gz', compression='gzip'
    ... )  # doctest: +SKIP
    >>> with openfile as f:
    ...     df = pd.read_csv(f)  # doctest: +SKIP
    ...

    Returns
    -------
    ``OpenFile`` object.

    Notes
    -----
    For a full list of the available protocols and the implementations that
    they map across to see the latest online documentation:

    - For implementations built into ``fsspec`` see
      https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations
    - For implementations in separate packages see
      https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations
    """
    expand = DEFAULT_EXPAND if expand is None else expand
    out = open_files(
        urlpath=[urlpath],
        mode=mode,
        compression=compression,
        encoding=encoding,
        errors=errors,
        protocol=protocol,
        newline=newline,
        expand=expand,
        **kwargs,
    )
    if not out:
        raise FileNotFoundError(urlpath)
    return out[0]


def open_local(
    url: str | list[str] | Path | list[Path],
    mode: str = "rb",
    **storage_options: dict,
) -> str | list[str]:
    """Open file(s) which can be resolved to local

    For files which either are local, or get downloaded upon open
    (e.g., by file caching)

    Parameters
    ----------
    url: str or list(str)
    mode: str
        Must be read mode
    storage_options:
        passed on to FS for or used by open_files (e.g., compression)
    """
    if "r" not in mode:
        raise ValueError("Can only ensure local files when reading")
    of = open_files(url, mode=mode, **storage_options)
    if not getattr(of[0].fs, "local_file", False):
        raise ValueError(
            "open_local can only be used on a filesystem which"
            " has attribute local_file=True"
        )
    with of as files:
        paths = [f.name for f in files]
    if (isinstance(url, str) and not has_magic(url)) or isinstance(url, Path):
        return paths[0]
    return paths


def get_compression(urlpath, compression):
    if compression == "infer":
        compression = infer_compression(urlpath)
    if compression is not None and compression not in compr:
        raise ValueError(f"Compression type {compression} not supported")
    return compression


def split_protocol(urlpath):
    """Return protocol, path pair"""
    urlpath = stringify_path(urlpath)
    if "://" in urlpath:
        protocol, path = urlpath.split("://", 1)
        if len(protocol) > 1:
            # excludes Windows paths
            return protocol, path
    if urlpath.startswith("data:"):
        return urlpath.split(":", 1)
    return None, urlpath


def strip_protocol(urlpath):
    """Return only path part of full URL, according to appropriate backend"""
    protocol, _ = split_protocol(urlpath)
    cls = get_filesystem_class(protocol)
    return cls._strip_protocol(urlpath)


def expand_paths_if_needed(paths, mode, num, fs, name_function):
    """Expand paths if they have a ``*`` in them (write mode) or any of ``*?[]``
    in them (read mode).

    :param paths: list of paths
    mode: str
        Mode in which to open files.
    num: int
        If opening in writing mode, number of files we expect to create.
    fs: filesystem object
    name_function: callable
        If opening in writing mode, this callable is used to generate path
        names. Names are generated for each partition by
        ``urlpath.replace('*', name_function(partition_index))``.
    :return: list of paths
    """
    expanded_paths = []
    paths = list(paths)

    if "w" in mode:  # read mode
        if sum(1 for p in paths if "*" in p) > 1:
            raise ValueError(
                "When writing data, only one filename mask can be specified."
            )
        num = max(num, len(paths))

        for curr_path in paths:
            if "*" in curr_path:
                # expand using name_function
                expanded_paths.extend(_expand_paths(curr_path, name_function, num))
            else:
                expanded_paths.append(curr_path)
        # if we generated more paths that asked for, trim the list
        if len(expanded_paths) > num:
            expanded_paths = expanded_paths[:num]

    else:  # read mode
        for curr_path in paths:
            if has_magic(curr_path):
                # expand using glob
                expanded_paths.extend(fs.glob(curr_path))
            else:
                expanded_paths.append(curr_path)

    return expanded_paths


def get_fs_token_paths(
    urlpath,
    mode="rb",
    num=1,
    name_function=None,
    storage_options=None,
    protocol=None,
    expand=True,
):
    """Filesystem, deterministic token, and paths from a urlpath and options.

    Parameters
    ----------
    urlpath: string or iterable
        Absolute or relative filepath, URL (may include protocols like
        ``s3://``), or globstring pointing to data.
    mode: str, optional
        Mode in which to open files.
    num: int, optional
        If opening in writing mode, number of files we expect to create.
    name_function: callable, optional
        If opening in writing mode, this callable is used to generate path
        names. Names are generated for each partition by
        ``urlpath.replace('*', name_function(partition_index))``.
    storage_options: dict, optional
        Additional keywords to pass to the filesystem class.
    protocol: str or None
        To override the protocol specifier in the URL
    expand: bool
        Expand string paths for writing, assuming the path is a directory
    """
    if isinstance(urlpath, (list, tuple, set)):
        if not urlpath:
            raise ValueError("empty urlpath sequence")
        urlpath0 = stringify_path(next(iter(urlpath)))
    else:
        urlpath0 = stringify_path(urlpath)
    storage_options = storage_options or {}
    if protocol:
        storage_options["protocol"] = protocol
    chain = _un_chain(urlpath0, storage_options or {})
    inkwargs = {}
    # Reverse iterate the chain, creating a nested target_* structure
    for i, ch in enumerate(reversed(chain)):
        urls, nested_protocol, kw = ch
        if i == len(chain) - 1:
            inkwargs = dict(**kw, **inkwargs)
            continue
        inkwargs["target_options"] = dict(**kw, **inkwargs)
        inkwargs["target_protocol"] = nested_protocol
        inkwargs["fo"] = urls
    paths, protocol, _ = chain[0]
    fs = filesystem(protocol, **inkwargs)
    if isinstance(urlpath, (list, tuple, set)):
        pchains = [
            _un_chain(stringify_path(u), storage_options or {})[0] for u in urlpath
        ]
        if len({pc[1] for pc in pchains}) > 1:
            raise ValueError("Protocol mismatch getting fs from %s", urlpath)
        paths = [pc[0] for pc in pchains]
    else:
        paths = fs._strip_protocol(paths)
    if isinstance(paths, (list, tuple, set)):
        if expand:
            paths = expand_paths_if_needed(paths, mode, num, fs, name_function)
        elif not isinstance(paths, list):
            paths = list(paths)
    else:
        if ("w" in mode or "x" in mode) and expand:
            paths = _expand_paths(paths, name_function, num)
        elif "*" in paths:
            paths = [f for f in sorted(fs.glob(paths)) if not fs.isdir(f)]
        else:
            paths = [paths]

    return fs, fs._fs_token, paths


def _expand_paths(path, name_function, num):
    if isinstance(path, str):
        if path.count("*") > 1:
            raise ValueError("Output path spec must contain exactly one '*'.")
        elif "*" not in path:
            path = os.path.join(path, "*.part")

        if name_function is None:
            name_function = build_name_function(num - 1)

        paths = [path.replace("*", name_function(i)) for i in range(num)]
        if paths != sorted(paths):
            logger.warning(
                "In order to preserve order between partitions"
                " paths created with ``name_function`` should "
                "sort to partition order"
            )
    elif isinstance(path, (tuple, list)):
        assert len(path) == num
        paths = list(path)
    else:
        raise ValueError(
            "Path should be either\n"
            "1. A list of paths: ['foo.json', 'bar.json', ...]\n"
            "2. A directory: 'foo/\n"
            "3. A path with a '*' in it: 'foo.*.json'"
        )
    return paths


class PickleableTextIOWrapper(io.TextIOWrapper):
    """TextIOWrapper cannot be pickled. This solves it.

    Requires that ``buffer`` be pickleable, which all instances of
    AbstractBufferedFile are.
    """

    def __init__(
        self,
        buffer,
        encoding=None,
        errors=None,
        newline=None,
        line_buffering=False,
        write_through=False,
    ):
        self.args = buffer, encoding, errors, newline, line_buffering, write_through
        super().__init__(*self.args)

    def __reduce__(self):
        return PickleableTextIOWrapper, self.args