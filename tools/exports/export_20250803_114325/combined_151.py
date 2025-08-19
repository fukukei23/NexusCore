
# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\coloreditor.py ===
# Color Editor originally by Neil Hodgson, but restructured by mh to integrate
# even tighter into Pythonwin.

import pywin.scintilla.keycodes
import pywin.scintilla.view
import win32api
import win32con
import win32ui
from pywin.debugger import dbgcon
from pywin.framework.editor import GetEditorOption
from pywin.framework.editor.document import EditorDocumentBase
from pywin.framework.editor.frame import EditorFrame
from pywin.framework.editor.template import EditorTemplateBase
from pywin.scintilla import bindings, scintillacon
from pywin.scintilla.view import CScintillaView as SyntEditViewParent

# WARNING: Duplicated in document.py and editor.py
MSG_CHECK_EXTERNAL_FILE = win32con.WM_USER + 1999

# Define a few common markers
MARKER_BOOKMARK = 0
MARKER_BREAKPOINT = 1
MARKER_CURRENT = 2


class SyntEditDocument(EditorDocumentBase):
    "A SyntEdit document."

    def OnDebuggerStateChange(self, state):
        self._ApplyOptionalToViews("OnDebuggerStateChange", state)

    def HookViewNotifications(self, view):
        EditorDocumentBase.HookViewNotifications(self, view)
        view.SCISetUndoCollection(1)

    def FinalizeViewCreation(self, view):
        EditorDocumentBase.FinalizeViewCreation(self, view)
        if view == self.GetFirstView():
            self.GetDocTemplate().CheckIDLEMenus(view.idle)


class SyntEditView(SyntEditViewParent):
    "A view of a SyntEdit.  Obtains data from document."

    def __init__(self, doc):
        SyntEditViewParent.__init__(self, doc)
        self.bCheckingFile = 0

    def OnInitialUpdate(self):
        SyntEditViewParent.OnInitialUpdate(self)

        self.HookMessage(self.OnRClick, win32con.WM_RBUTTONDOWN)

        for id in (
            win32ui.ID_VIEW_FOLD_COLLAPSE,
            win32ui.ID_VIEW_FOLD_COLLAPSE_ALL,
            win32ui.ID_VIEW_FOLD_EXPAND,
            win32ui.ID_VIEW_FOLD_EXPAND_ALL,
        ):
            self.HookCommand(self.OnCmdViewFold, id)
            self.HookCommandUpdate(self.OnUpdateViewFold, id)
        self.HookCommand(self.OnCmdViewFoldTopLevel, win32ui.ID_VIEW_FOLD_TOPLEVEL)

        # Define the markers
        # 		self.SCIMarkerDeleteAll()
        self.SCIMarkerDefineAll(
            MARKER_BOOKMARK,
            scintillacon.SC_MARK_ROUNDRECT,
            win32api.RGB(0x0, 0x0, 0x0),
            win32api.RGB(0, 0xFF, 0xFF),
        )

        self.SCIMarkerDefine(MARKER_CURRENT, scintillacon.SC_MARK_ARROW)
        self.SCIMarkerSetBack(MARKER_CURRENT, win32api.RGB(0xFF, 0xFF, 0x00))

        # Define the folding markers
        if 1:  # traditional markers
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEROPEN,
                scintillacon.SC_MARK_MINUS,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDER,
                scintillacon.SC_MARK_PLUS,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERSUB,
                scintillacon.SC_MARK_EMPTY,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERTAIL,
                scintillacon.SC_MARK_EMPTY,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEREND,
                scintillacon.SC_MARK_EMPTY,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEROPENMID,
                scintillacon.SC_MARK_EMPTY,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERMIDTAIL,
                scintillacon.SC_MARK_EMPTY,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
        else:  # curved markers
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEROPEN,
                scintillacon.SC_MARK_CIRCLEMINUS,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDER,
                scintillacon.SC_MARK_CIRCLEPLUS,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERSUB,
                scintillacon.SC_MARK_VLINE,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERTAIL,
                scintillacon.SC_MARK_LCORNERCURVE,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEREND,
                scintillacon.SC_MARK_CIRCLEPLUSCONNECTED,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDEROPENMID,
                scintillacon.SC_MARK_CIRCLEMINUSCONNECTED,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )
            self.SCIMarkerDefineAll(
                scintillacon.SC_MARKNUM_FOLDERMIDTAIL,
                scintillacon.SC_MARK_TCORNERCURVE,
                win32api.RGB(0xFF, 0xFF, 0xFF),
                win32api.RGB(0, 0, 0),
            )

        self.SCIMarkerDefine(MARKER_BREAKPOINT, scintillacon.SC_MARK_CIRCLE)
        # Marker background depends on debugger state
        self.SCIMarkerSetFore(MARKER_BREAKPOINT, win32api.RGB(0x0, 0, 0))
        # Get the current debugger state.
        try:
            import pywin.debugger

            if pywin.debugger.currentDebugger is None:
                state = dbgcon.DBGSTATE_NOT_DEBUGGING
            else:
                state = pywin.debugger.currentDebugger.debuggerState
        except ImportError:
            state = dbgcon.DBGSTATE_NOT_DEBUGGING
        self.OnDebuggerStateChange(state)

    def _GetSubConfigNames(self):
        return ["editor"]  # Allow [Keys:Editor] sections to be specific to us

    def DoConfigChange(self):
        SyntEditViewParent.DoConfigChange(self)
        tabSize = GetEditorOption("Tab Size", 4, 2)
        indentSize = GetEditorOption("Indent Size", 4, 2)
        bUseTabs = GetEditorOption("Use Tabs", 0)
        bSmartTabs = GetEditorOption("Smart Tabs", 1)
        ext = self.idle.IDLEExtension("AutoIndent")  # Required extension.

        self.SCISetViewWS(GetEditorOption("View Whitespace", 0))
        self.SCISetViewEOL(GetEditorOption("View EOL", 0))
        self.SCISetIndentationGuides(GetEditorOption("View Indentation Guides", 0))

        if GetEditorOption("Right Edge Enabled", 0):
            mode = scintillacon.EDGE_BACKGROUND
        else:
            mode = scintillacon.EDGE_NONE
        self.SCISetEdgeMode(mode)
        self.SCISetEdgeColumn(GetEditorOption("Right Edge Column", 75))
        self.SCISetEdgeColor(
            GetEditorOption("Right Edge Color", win32api.RGB(0xEF, 0xEF, 0xEF))
        )

        width = GetEditorOption("Marker Margin Width", 16)
        self.SCISetMarginWidthN(1, width)
        width = GetEditorOption("Fold Margin Width", 12)
        self.SCISetMarginWidthN(2, width)
        width = GetEditorOption("Line Number Margin Width", 0)
        self.SCISetMarginWidthN(0, width)
        self.bFolding = GetEditorOption("Enable Folding", 1)
        fold_flags = 0
        self.SendScintilla(
            scintillacon.SCI_SETMODEVENTMASK, scintillacon.SC_MOD_CHANGEFOLD
        )
        if self.bFolding:
            if GetEditorOption("Fold Lines", 1):
                fold_flags = 16

        self.SCISetProperty("fold", self.bFolding)
        self.SCISetFoldFlags(fold_flags)

        tt_color = GetEditorOption("Tab Timmy Color", win32api.RGB(0xFF, 0, 0))
        self.SendScintilla(scintillacon.SCI_INDICSETFORE, 1, tt_color)

        tt_use = GetEditorOption("Use Tab Timmy", 1)
        if tt_use:
            self.SCISetProperty("tab.timmy.whinge.level", "1")

        # Auto-indent has very complicated behaviour.  In a nutshell, the only
        # way to get sensible behaviour from it is to ensure tabwidth != indentsize.
        # Further, usetabs will only ever go from 1->0, never 0->1.
        # This is _not_ the behaviour Pythonwin wants:
        # * Tab width is arbitary, so should have no impact on smarts.
        # * bUseTabs setting should reflect how new files are created, and
        #   if Smart Tabs disabled, existing files are edited
        # * If "Smart Tabs" is enabled, bUseTabs should have no bearing
        #   for existing files (unless of course no context can be determined)
        #
        # So for smart tabs we configure the widget with completely dummy
        # values (ensuring tabwidth != indentwidth), ask it to guess, then
        # look at the values it has guessed, and re-configure
        if bSmartTabs:
            ext.config(usetabs=1, tabwidth=5, indentwidth=4)
            ext.set_indentation_params(1)
            if ext.indentwidth == 5:
                # Either 5 literal spaces, or a single tab character. Assume a tab
                usetabs = 1
                indentwidth = tabSize
            else:
                # Either Indented with spaces, and indent size has been guessed or
                # an empty file (or no context found - tough!)
                if self.GetTextLength() == 0:  # emtpy
                    usetabs = bUseTabs
                    indentwidth = indentSize
                else:  # guessed.
                    indentwidth = ext.indentwidth
                    usetabs = 0
            # Tab size can never be guessed - set at user preference.
            ext.config(usetabs=usetabs, indentwidth=indentwidth, tabwidth=tabSize)
        else:
            # Don't want smart-tabs - just set the options!
            ext.config(usetabs=bUseTabs, tabwidth=tabSize, indentwidth=indentSize)
        self.SCISetIndent(indentSize)
        self.SCISetTabWidth(tabSize)

    def OnDebuggerStateChange(self, state):
        if state == dbgcon.DBGSTATE_NOT_DEBUGGING:
            # Indicate breakpoints aren't really usable.
            # Not quite white - useful when no marker margin, so set as background color.
            self.SCIMarkerSetBack(MARKER_BREAKPOINT, win32api.RGB(0xEF, 0xEF, 0xEF))
        else:
            # A light-red, so still readable when no marker margin.
            self.SCIMarkerSetBack(MARKER_BREAKPOINT, win32api.RGB(0xFF, 0x80, 0x80))

    def HookDocumentHandlers(self):
        SyntEditViewParent.HookDocumentHandlers(self)
        self.HookMessage(self.OnCheckExternalDocumentUpdated, MSG_CHECK_EXTERNAL_FILE)

    def HookHandlers(self):
        SyntEditViewParent.HookHandlers(self)
        self.HookMessage(self.OnSetFocus, win32con.WM_SETFOCUS)

    def _PrepareUserStateChange(self):
        return self.GetSel(), self.GetFirstVisibleLine()

    def _EndUserStateChange(self, info):
        scrollOff = info[1] - self.GetFirstVisibleLine()
        if scrollOff:
            self.LineScroll(scrollOff)
        # Make sure we don't reset the cursor beyond the buffer.
        max = self.GetTextLength()
        newPos = min(info[0][0], max), min(info[0][1], max)
        self.SetSel(newPos)

    #######################################
    # The Windows Message or Notify handlers.
    #######################################
    def OnMarginClick(self, std, extra):
        notify = self.SCIUnpackNotifyMessage(extra)
        if notify.margin == 2:  # Our fold margin
            line_click = self.LineFromChar(notify.position)
            # 			max_line = self.GetLineCount()
            if self.SCIGetFoldLevel(line_click) & scintillacon.SC_FOLDLEVELHEADERFLAG:
                # If a fold point.
                self.SCIToggleFold(line_click)
        return 1

    def OnSetFocus(self, msg):
        # Even though we use file change notifications, we should be very sure about it here.
        self.OnCheckExternalDocumentUpdated(msg)
        return 1

    def OnCheckExternalDocumentUpdated(self, msg):
        if self.bCheckingFile:
            return
        self.bCheckingFile = 1
        self.GetDocument().CheckExternalDocumentUpdated()
        self.bCheckingFile = 0

    def OnRClick(self, params):
        menu = win32ui.CreatePopupMenu()
        self.AppendMenu(menu, "&Locate module", "LocateModule")
        self.AppendMenu(menu, flags=win32con.MF_SEPARATOR)
        self.AppendMenu(menu, "&Undo", "EditUndo")
        self.AppendMenu(menu, "&Redo", "EditRedo")
        self.AppendMenu(menu, flags=win32con.MF_SEPARATOR)
        self.AppendMenu(menu, "Cu&t", "EditCut")
        self.AppendMenu(menu, "&Copy", "EditCopy")
        self.AppendMenu(menu, "&Paste", "EditPaste")
        self.AppendMenu(menu, flags=win32con.MF_SEPARATOR)
        self.AppendMenu(menu, "&Select all", "EditSelectAll")
        self.AppendMenu(
            menu, "View &Whitespace", "ViewWhitespace", checked=self.SCIGetViewWS()
        )
        self.AppendMenu(
            menu, "&Fixed Font", "ViewFixedFont", checked=self._GetColorizer().bUseFixed
        )
        self.AppendMenu(menu, flags=win32con.MF_SEPARATOR)
        self.AppendMenu(menu, "&Goto line...", "GotoLine")

        submenu = win32ui.CreatePopupMenu()
        newitems = self.idle.GetMenuItems("edit")
        for text, event in newitems:
            self.AppendMenu(submenu, text, event)

        flags = win32con.MF_STRING | win32con.MF_ENABLED | win32con.MF_POPUP
        menu.AppendMenu(flags, submenu.GetHandle(), "&Source code")

        flags = (
            win32con.TPM_LEFTALIGN | win32con.TPM_LEFTBUTTON | win32con.TPM_RIGHTBUTTON
        )
        menu.TrackPopupMenu(params[5], flags, self)
        return 0

    def OnCmdViewFold(self, cid, code):  # Handle the menu command
        if cid == win32ui.ID_VIEW_FOLD_EXPAND_ALL:
            self.FoldExpandAllEvent(None)
        elif cid == win32ui.ID_VIEW_FOLD_EXPAND:
            self.FoldExpandEvent(None)
        elif cid == win32ui.ID_VIEW_FOLD_COLLAPSE_ALL:
            self.FoldCollapseAllEvent(None)
        elif cid == win32ui.ID_VIEW_FOLD_COLLAPSE:
            self.FoldCollapseEvent(None)
        else:
            print("Unknown collapse/expand ID")

    def OnUpdateViewFold(self, cmdui):  # Update the tick on the UI.
        if not self.bFolding:
            cmdui.Enable(0)
            return
        id = cmdui.m_nID
        if id in (win32ui.ID_VIEW_FOLD_EXPAND_ALL, win32ui.ID_VIEW_FOLD_COLLAPSE_ALL):
            cmdui.Enable()
        else:
            enable = 0
            lineno = self.LineFromChar(self.GetSel()[0])
            foldable = (
                self.SCIGetFoldLevel(lineno) & scintillacon.SC_FOLDLEVELHEADERFLAG
            )
            is_expanded = self.SCIGetFoldExpanded(lineno)
            if id == win32ui.ID_VIEW_FOLD_EXPAND:
                if foldable and not is_expanded:
                    enable = 1
            elif id == win32ui.ID_VIEW_FOLD_COLLAPSE:
                if foldable and is_expanded:
                    enable = 1
            cmdui.Enable(enable)

    def OnCmdViewFoldTopLevel(self, cid, code):  # Handle the menu command
        self.FoldTopLevelEvent(None)

    #######################################
    # The Events
    #######################################
    def ToggleBookmarkEvent(self, event, pos=-1):
        """Toggle a bookmark at the specified or current position"""
        if pos == -1:
            pos, end = self.GetSel()
        startLine = self.LineFromChar(pos)
        self.GetDocument().MarkerToggle(startLine + 1, MARKER_BOOKMARK)
        return 0

    def GotoNextBookmarkEvent(self, event, fromPos=-1):
        """Move to the next bookmark"""
        if fromPos == -1:
            fromPos, end = self.GetSel()
        startLine = self.LineFromChar(fromPos) + 1  # Zero based line to start
        nextLine = self.GetDocument().MarkerGetNext(startLine + 1, MARKER_BOOKMARK) - 1
        if nextLine < 0:
            nextLine = self.GetDocument().MarkerGetNext(0, MARKER_BOOKMARK) - 1
        if nextLine < 0 or nextLine == startLine - 1:
            win32api.MessageBeep()
        else:
            self.SCIEnsureVisible(nextLine)
            self.SCIGotoLine(nextLine)
        return 0

    def TabKeyEvent(self, event):
        """Insert an indent.  If no selection, a single indent, otherwise a block indent"""
        # Handle auto-complete first.
        if self.SCIAutoCActive():
            self.SCIAutoCComplete()
            return 0
        # Call the IDLE event.
        return self.bindings.fire("<<smart-indent>>", event)

    def EnterKeyEvent(self, event):
        """Handle the enter key with special handling for auto-complete"""
        # Handle auto-complete first.
        if self.SCIAutoCActive():
            self.SCIAutoCComplete()
            self.SCIAutoCCancel()
        # Call the IDLE event.
        return self.bindings.fire("<<newline-and-indent>>", event)

    def ShowInteractiveWindowEvent(self, event):
        import pywin.framework.interact

        pywin.framework.interact.ShowInteractiveWindow()

    def FoldTopLevelEvent(self, event=None):
        if not self.bFolding:
            return 1

        win32ui.DoWaitCursor(1)
        try:
            self.Colorize()
            maxLine = self.GetLineCount()
            # Find the first line, and check out its state.
            for lineSeek in range(maxLine):
                if self.SCIGetFoldLevel(lineSeek) & scintillacon.SC_FOLDLEVELHEADERFLAG:
                    expanding = not self.SCIGetFoldExpanded(lineSeek)
                    break
            else:
                # no folds here!
                return
            for lineSeek in range(lineSeek, maxLine):
                level = self.SCIGetFoldLevel(lineSeek)
                level_no = (
                    level
                    & scintillacon.SC_FOLDLEVELNUMBERMASK
                    - scintillacon.SC_FOLDLEVELBASE
                )
                is_header = level & scintillacon.SC_FOLDLEVELHEADERFLAG
                # print(lineSeek, level_no, is_header)
                if level_no == 0 and is_header:
                    if (expanding and not self.SCIGetFoldExpanded(lineSeek)) or (
                        not expanding and self.SCIGetFoldExpanded(lineSeek)
                    ):
                        self.SCIToggleFold(lineSeek)
        finally:
            win32ui.DoWaitCursor(-1)

    def FoldExpandSecondLevelEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        ## I think this is needed since Scintilla may not have
        ## already formatted parts of file outside visible window.
        self.Colorize()
        levels = [scintillacon.SC_FOLDLEVELBASE]
        ## Scintilla's level number is based on amount of whitespace indentation
        for lineno in range(self.GetLineCount()):
            level = self.SCIGetFoldLevel(lineno)
            if not level & scintillacon.SC_FOLDLEVELHEADERFLAG:
                continue
            curr_level = level & scintillacon.SC_FOLDLEVELNUMBERMASK
            if curr_level > levels[-1]:
                levels.append(curr_level)
            try:
                level_ind = levels.index(curr_level)
            except ValueError:
                ## probably syntax error in source file, bail
                break
            levels = levels[: level_ind + 1]
            if level_ind == 1 and not self.SCIGetFoldExpanded(lineno):
                self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)

    def FoldCollapseSecondLevelEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        ## I think this is needed since Scintilla may not have
        ## already formatted parts of file outside visible window.
        self.Colorize()
        levels = [scintillacon.SC_FOLDLEVELBASE]
        ## Scintilla's level number is based on amount of whitespace indentation
        for lineno in range(self.GetLineCount()):
            level = self.SCIGetFoldLevel(lineno)
            if not level & scintillacon.SC_FOLDLEVELHEADERFLAG:
                continue
            curr_level = level & scintillacon.SC_FOLDLEVELNUMBERMASK
            if curr_level > levels[-1]:
                levels.append(curr_level)
            try:
                level_ind = levels.index(curr_level)
            except ValueError:
                ## probably syntax error in source file, bail
                break
            levels = levels[: level_ind + 1]
            if level_ind == 1 and self.SCIGetFoldExpanded(lineno):
                self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)

    def FoldExpandEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        lineno = self.LineFromChar(self.GetSel()[0])
        if self.SCIGetFoldLevel(
            lineno
        ) & scintillacon.SC_FOLDLEVELHEADERFLAG and not self.SCIGetFoldExpanded(lineno):
            self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)

    def FoldExpandAllEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        for lineno in range(0, self.GetLineCount()):
            if self.SCIGetFoldLevel(
                lineno
            ) & scintillacon.SC_FOLDLEVELHEADERFLAG and not self.SCIGetFoldExpanded(
                lineno
            ):
                self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)

    def FoldCollapseEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        lineno = self.LineFromChar(self.GetSel()[0])
        if self.SCIGetFoldLevel(
            lineno
        ) & scintillacon.SC_FOLDLEVELHEADERFLAG and self.SCIGetFoldExpanded(lineno):
            self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)

    def FoldCollapseAllEvent(self, event):
        if not self.bFolding:
            return 1
        win32ui.DoWaitCursor(1)
        self.Colorize()
        for lineno in range(0, self.GetLineCount()):
            if self.SCIGetFoldLevel(
                lineno
            ) & scintillacon.SC_FOLDLEVELHEADERFLAG and self.SCIGetFoldExpanded(lineno):
                self.SCIToggleFold(lineno)
        win32ui.DoWaitCursor(-1)


class SplitterFrame(EditorFrame):
    def OnCreate(self, cs):
        self.HookCommand(self.OnWindowSplit, win32ui.ID_WINDOW_SPLIT)
        return 1

    def OnWindowSplit(self, id, code):
        self.GetDlgItem(win32ui.AFX_IDW_PANE_FIRST).DoKeyboardSplit()
        return 1


class SyntEditTemplate(EditorTemplateBase):
    def __init__(
        self, res=win32ui.IDR_TEXTTYPE, makeDoc=None, makeFrame=None, makeView=None
    ):
        if makeDoc is None:
            makeDoc = SyntEditDocument
        if makeView is None:
            makeView = SyntEditView
        if makeFrame is None:
            makeFrame = SplitterFrame
        self.bSetMenus = 0
        EditorTemplateBase.__init__(self, res, makeDoc, makeFrame, makeView)

    def CheckIDLEMenus(self, idle):
        if self.bSetMenus:
            return
        self.bSetMenus = 1

        submenu = win32ui.CreatePopupMenu()
        newitems = idle.GetMenuItems("edit")
        flags = win32con.MF_STRING | win32con.MF_ENABLED
        for text, event in newitems:
            id = bindings.event_to_commands.get(event)
            if id is not None:
                keyname = pywin.scintilla.view.configManager.get_key_binding(
                    event, ["editor"]
                )
                if keyname is not None:
                    text += "\t" + keyname
                submenu.AppendMenu(flags, id, text)

        mainMenu = self.GetSharedMenu()
        editMenu = mainMenu.GetSubMenu(1)
        editMenu.AppendMenu(win32con.MF_SEPARATOR, 0, "")
        editMenu.AppendMenu(
            win32con.MF_STRING | win32con.MF_POPUP | win32con.MF_ENABLED,
            submenu.GetHandle(),
            "&Source Code",
        )

    def _CreateDocTemplate(self, resourceId):
        return win32ui.CreateDocTemplate(resourceId)

    def CreateWin32uiDocument(self):
        return self.DoCreateDoc()

    def GetPythonPropertyPages(self):
        """Returns a list of property pages"""
        from pywin.scintilla import configui

        return EditorTemplateBase.GetPythonPropertyPages(self) + [
            configui.ScintillaFormatPropertyPage()
        ]


# For debugging purposes, when this module may be reloaded many times.
try:
    win32ui.GetApp().RemoveDocTemplate(editorTemplate)  # type: ignore[has-type, used-before-def]
except NameError:
    pass

editorTemplate = SyntEditTemplate()
win32ui.GetApp().AddDocTemplate(editorTemplate)

# === NexusCore/openenv\Lib\site-packages\click\shell_completion.py ===
from __future__ import annotations

import collections.abc as cabc
import os
import re
import typing as t
from gettext import gettext as _

from .core import Argument
from .core import Command
from .core import Context
from .core import Group
from .core import Option
from .core import Parameter
from .core import ParameterSource
from .utils import echo


def shell_complete(
    cli: Command,
    ctx_args: cabc.MutableMapping[str, t.Any],
    prog_name: str,
    complete_var: str,
    instruction: str,
) -> int:
    """Perform shell completion for the given CLI program.

    :param cli: Command being called.
    :param ctx_args: Extra arguments to pass to
        ``cli.make_context``.
    :param prog_name: Name of the executable in the shell.
    :param complete_var: Name of the environment variable that holds
        the completion instruction.
    :param instruction: Value of ``complete_var`` with the completion
        instruction and shell, in the form ``instruction_shell``.
    :return: Status code to exit with.
    """
    shell, _, instruction = instruction.partition("_")
    comp_cls = get_completion_class(shell)

    if comp_cls is None:
        return 1

    comp = comp_cls(cli, ctx_args, prog_name, complete_var)

    if instruction == "source":
        echo(comp.source())
        return 0

    if instruction == "complete":
        echo(comp.complete())
        return 0

    return 1


class CompletionItem:
    """Represents a completion value and metadata about the value. The
    default metadata is ``type`` to indicate special shell handling,
    and ``help`` if a shell supports showing a help string next to the
    value.

    Arbitrary parameters can be passed when creating the object, and
    accessed using ``item.attr``. If an attribute wasn't passed,
    accessing it returns ``None``.

    :param value: The completion suggestion.
    :param type: Tells the shell script to provide special completion
        support for the type. Click uses ``"dir"`` and ``"file"``.
    :param help: String shown next to the value if supported.
    :param kwargs: Arbitrary metadata. The built-in implementations
        don't use this, but custom type completions paired with custom
        shell support could use it.
    """

    __slots__ = ("value", "type", "help", "_info")

    def __init__(
        self,
        value: t.Any,
        type: str = "plain",
        help: str | None = None,
        **kwargs: t.Any,
    ) -> None:
        self.value: t.Any = value
        self.type: str = type
        self.help: str | None = help
        self._info = kwargs

    def __getattr__(self, name: str) -> t.Any:
        return self._info.get(name)


# Only Bash >= 4.4 has the nosort option.
_SOURCE_BASH = """\
%(complete_func)s() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD \
%(complete_var)s=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

%(complete_func)s_setup() {
    complete -o nosort -F %(complete_func)s %(prog_name)s
}

%(complete_func)s_setup;
"""

_SOURCE_ZSH = """\
#compdef %(prog_name)s

%(complete_func)s() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[%(prog_name)s] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) \
%(complete_var)s=zsh_complete %(prog_name)s)}")

    for type key descr in ${response}; do
        if [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                completions+=("$key")
            else
                completions_with_descriptions+=("$key":"$descr")
            fi
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
    # autoload from fpath, call function directly
    %(complete_func)s "$@"
else
    # eval/source/. command, register function for later
    compdef %(complete_func)s %(prog_name)s
fi
"""

_SOURCE_FISH = """\
function %(complete_func)s;
    set -l response (env %(complete_var)s=fish_complete COMP_WORDS=(commandline -cp) \
COMP_CWORD=(commandline -t) %(prog_name)s);

    for completion in $response;
        set -l metadata (string split "," $completion);

        if test $metadata[1] = "dir";
            __fish_complete_directories $metadata[2];
        else if test $metadata[1] = "file";
            __fish_complete_path $metadata[2];
        else if test $metadata[1] = "plain";
            echo $metadata[2];
        end;
    end;
end;

complete --no-files --command %(prog_name)s --arguments \
"(%(complete_func)s)";
"""


class ShellComplete:
    """Base class for providing shell completion support. A subclass for
    a given shell will override attributes and methods to implement the
    completion instructions (``source`` and ``complete``).

    :param cli: Command being called.
    :param prog_name: Name of the executable in the shell.
    :param complete_var: Name of the environment variable that holds
        the completion instruction.

    .. versionadded:: 8.0
    """

    name: t.ClassVar[str]
    """Name to register the shell as with :func:`add_completion_class`.
    This is used in completion instructions (``{name}_source`` and
    ``{name}_complete``).
    """

    source_template: t.ClassVar[str]
    """Completion script template formatted by :meth:`source`. This must
    be provided by subclasses.
    """

    def __init__(
        self,
        cli: Command,
        ctx_args: cabc.MutableMapping[str, t.Any],
        prog_name: str,
        complete_var: str,
    ) -> None:
        self.cli = cli
        self.ctx_args = ctx_args
        self.prog_name = prog_name
        self.complete_var = complete_var

    @property
    def func_name(self) -> str:
        """The name of the shell function defined by the completion
        script.
        """
        safe_name = re.sub(r"\W*", "", self.prog_name.replace("-", "_"), flags=re.ASCII)
        return f"_{safe_name}_completion"

    def source_vars(self) -> dict[str, t.Any]:
        """Vars for formatting :attr:`source_template`.

        By default this provides ``complete_func``, ``complete_var``,
        and ``prog_name``.
        """
        return {
            "complete_func": self.func_name,
            "complete_var": self.complete_var,
            "prog_name": self.prog_name,
        }

    def source(self) -> str:
        """Produce the shell script that defines the completion
        function. By default this ``%``-style formats
        :attr:`source_template` with the dict returned by
        :meth:`source_vars`.
        """
        return self.source_template % self.source_vars()

    def get_completion_args(self) -> tuple[list[str], str]:
        """Use the env vars defined by the shell script to return a
        tuple of ``args, incomplete``. This must be implemented by
        subclasses.
        """
        raise NotImplementedError

    def get_completions(self, args: list[str], incomplete: str) -> list[CompletionItem]:
        """Determine the context and last complete command or parameter
        from the complete args. Call that object's ``shell_complete``
        method to get the completions for the incomplete value.

        :param args: List of complete args before the incomplete value.
        :param incomplete: Value being completed. May be empty.
        """
        ctx = _resolve_context(self.cli, self.ctx_args, self.prog_name, args)
        obj, incomplete = _resolve_incomplete(ctx, args, incomplete)
        return obj.shell_complete(ctx, incomplete)

    def format_completion(self, item: CompletionItem) -> str:
        """Format a completion item into the form recognized by the
        shell script. This must be implemented by subclasses.

        :param item: Completion item to format.
        """
        raise NotImplementedError

    def complete(self) -> str:
        """Produce the completion data to send back to the shell.

        By default this calls :meth:`get_completion_args`, gets the
        completions, then calls :meth:`format_completion` for each
        completion.
        """
        args, incomplete = self.get_completion_args()
        completions = self.get_completions(args, incomplete)
        out = [self.format_completion(item) for item in completions]
        return "\n".join(out)


class BashComplete(ShellComplete):
    """Shell completion for Bash."""

    name = "bash"
    source_template = _SOURCE_BASH

    @staticmethod
    def _check_version() -> None:
        import shutil
        import subprocess

        bash_exe = shutil.which("bash")

        if bash_exe is None:
            match = None
        else:
            output = subprocess.run(
                [bash_exe, "--norc", "-c", 'echo "${BASH_VERSION}"'],
                stdout=subprocess.PIPE,
            )
            match = re.search(r"^(\d+)\.(\d+)\.\d+", output.stdout.decode())

        if match is not None:
            major, minor = match.groups()

            if major < "4" or major == "4" and minor < "4":
                echo(
                    _(
                        "Shell completion is not supported for Bash"
                        " versions older than 4.4."
                    ),
                    err=True,
                )
        else:
            echo(
                _("Couldn't detect Bash version, shell completion is not supported."),
                err=True,
            )

    def source(self) -> str:
        self._check_version()
        return super().source()

    def get_completion_args(self) -> tuple[list[str], str]:
        cwords = split_arg_string(os.environ["COMP_WORDS"])
        cword = int(os.environ["COMP_CWORD"])
        args = cwords[1:cword]

        try:
            incomplete = cwords[cword]
        except IndexError:
            incomplete = ""

        return args, incomplete

    def format_completion(self, item: CompletionItem) -> str:
        return f"{item.type},{item.value}"


class ZshComplete(ShellComplete):
    """Shell completion for Zsh."""

    name = "zsh"
    source_template = _SOURCE_ZSH

    def get_completion_args(self) -> tuple[list[str], str]:
        cwords = split_arg_string(os.environ["COMP_WORDS"])
        cword = int(os.environ["COMP_CWORD"])
        args = cwords[1:cword]

        try:
            incomplete = cwords[cword]
        except IndexError:
            incomplete = ""

        return args, incomplete

    def format_completion(self, item: CompletionItem) -> str:
        return f"{item.type}\n{item.value}\n{item.help if item.help else '_'}"


class FishComplete(ShellComplete):
    """Shell completion for Fish."""

    name = "fish"
    source_template = _SOURCE_FISH

    def get_completion_args(self) -> tuple[list[str], str]:
        cwords = split_arg_string(os.environ["COMP_WORDS"])
        incomplete = os.environ["COMP_CWORD"]
        args = cwords[1:]

        # Fish stores the partial word in both COMP_WORDS and
        # COMP_CWORD, remove it from complete args.
        if incomplete and args and args[-1] == incomplete:
            args.pop()

        return args, incomplete

    def format_completion(self, item: CompletionItem) -> str:
        if item.help:
            return f"{item.type},{item.value}\t{item.help}"

        return f"{item.type},{item.value}"


ShellCompleteType = t.TypeVar("ShellCompleteType", bound="type[ShellComplete]")


_available_shells: dict[str, type[ShellComplete]] = {
    "bash": BashComplete,
    "fish": FishComplete,
    "zsh": ZshComplete,
}


def add_completion_class(
    cls: ShellCompleteType, name: str | None = None
) -> ShellCompleteType:
    """Register a :class:`ShellComplete` subclass under the given name.
    The name will be provided by the completion instruction environment
    variable during completion.

    :param cls: The completion class that will handle completion for the
        shell.
    :param name: Name to register the class under. Defaults to the
        class's ``name`` attribute.
    """
    if name is None:
        name = cls.name

    _available_shells[name] = cls

    return cls


def get_completion_class(shell: str) -> type[ShellComplete] | None:
    """Look up a registered :class:`ShellComplete` subclass by the name
    provided by the completion instruction environment variable. If the
    name isn't registered, returns ``None``.

    :param shell: Name the class is registered under.
    """
    return _available_shells.get(shell)


def split_arg_string(string: str) -> list[str]:
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.

    .. code-block:: python

        split_arg_string("example 'my file")
        ["example", "my file"]

        split_arg_string("example my\\")
        ["example", "my"]

    :param string: String to split.

    .. versionchanged:: 8.2
        Moved to ``shell_completion`` from ``parser``.
    """
    import shlex

    lex = shlex.shlex(string, posix=True)
    lex.whitespace_split = True
    lex.commenters = ""
    out = []

    try:
        for token in lex:
            out.append(token)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        out.append(lex.token)

    return out


def _is_incomplete_argument(ctx: Context, param: Parameter) -> bool:
    """Determine if the given parameter is an argument that can still
    accept values.

    :param ctx: Invocation context for the command represented by the
        parsed complete args.
    :param param: Argument object being checked.
    """
    if not isinstance(param, Argument):
        return False

    assert param.name is not None
    # Will be None if expose_value is False.
    value = ctx.params.get(param.name)
    return (
        param.nargs == -1
        or ctx.get_parameter_source(param.name) is not ParameterSource.COMMANDLINE
        or (
            param.nargs > 1
            and isinstance(value, (tuple, list))
            and len(value) < param.nargs
        )
    )


def _start_of_option(ctx: Context, value: str) -> bool:
    """Check if the value looks like the start of an option."""
    if not value:
        return False

    c = value[0]
    return c in ctx._opt_prefixes


def _is_incomplete_option(ctx: Context, args: list[str], param: Parameter) -> bool:
    """Determine if the given parameter is an option that needs a value.

    :param args: List of complete args before the incomplete value.
    :param param: Option object being checked.
    """
    if not isinstance(param, Option):
        return False

    if param.is_flag or param.count:
        return False

    last_option = None

    for index, arg in enumerate(reversed(args)):
        if index + 1 > param.nargs:
            break

        if _start_of_option(ctx, arg):
            last_option = arg

    return last_option is not None and last_option in param.opts


def _resolve_context(
    cli: Command,
    ctx_args: cabc.MutableMapping[str, t.Any],
    prog_name: str,
    args: list[str],
) -> Context:
    """Produce the context hierarchy starting with the command and
    traversing the complete arguments. This only follows the commands,
    it doesn't trigger input prompts or callbacks.

    :param cli: Command being called.
    :param prog_name: Name of the executable in the shell.
    :param args: List of complete args before the incomplete value.
    """
    ctx_args["resilient_parsing"] = True
    with cli.make_context(prog_name, args.copy(), **ctx_args) as ctx:
        args = ctx._protected_args + ctx.args

        while args:
            command = ctx.command

            if isinstance(command, Group):
                if not command.chain:
                    name, cmd, args = command.resolve_command(ctx, args)

                    if cmd is None:
                        return ctx

                    with cmd.make_context(
                        name, args, parent=ctx, resilient_parsing=True
                    ) as sub_ctx:
                        ctx = sub_ctx
                        args = ctx._protected_args + ctx.args
                else:
                    sub_ctx = ctx

                    while args:
                        name, cmd, args = command.resolve_command(ctx, args)

                        if cmd is None:
                            return ctx

                        with cmd.make_context(
                            name,
                            args,
                            parent=ctx,
                            allow_extra_args=True,
                            allow_interspersed_args=False,
                            resilient_parsing=True,
                        ) as sub_sub_ctx:
                            sub_ctx = sub_sub_ctx
                            args = sub_ctx.args

                    ctx = sub_ctx
                    args = [*sub_ctx._protected_args, *sub_ctx.args]
            else:
                break

    return ctx


def _resolve_incomplete(
    ctx: Context, args: list[str], incomplete: str
) -> tuple[Command | Parameter, str]:
    """Find the Click object that will handle the completion of the
    incomplete value. Return the object and the incomplete value.

    :param ctx: Invocation context for the command represented by
        the parsed complete args.
    :param args: List of complete args before the incomplete value.
    :param incomplete: Value being completed. May be empty.
    """
    # Different shells treat an "=" between a long option name and
    # value differently. Might keep the value joined, return the "="
    # as a separate item, or return the split name and value. Always
    # split and discard the "=" to make completion easier.
    if incomplete == "=":
        incomplete = ""
    elif "=" in incomplete and _start_of_option(ctx, incomplete):
        name, _, incomplete = incomplete.partition("=")
        args.append(name)

    # The "--" marker tells Click to stop treating values as options
    # even if they start with the option character. If it hasn't been
    # given and the incomplete arg looks like an option, the current
    # command will provide option name completions.
    if "--" not in args and _start_of_option(ctx, incomplete):
        return ctx.command, incomplete

    params = ctx.command.get_params(ctx)

    # If the last complete arg is an option name with an incomplete
    # value, the option will provide value completions.
    for param in params:
        if _is_incomplete_option(ctx, args, param):
            return param, incomplete

    # It's not an option name or value. The first argument without a
    # parsed value will provide value completions.
    for param in params:
        if _is_incomplete_argument(ctx, param):
            return param, incomplete

    # There were no unparsed arguments, the command may be a group that
    # will provide command name completions.
    return ctx.command, incomplete

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\pascal.py ===
"""
    pygments.lexers.pascal
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Pascal family languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer
from pygments.util import get_bool_opt, get_list_opt
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error, Whitespace
from pygments.scanner import Scanner

# compatibility import
from pygments.lexers.modula2 import Modula2Lexer # noqa: F401

__all__ = ['DelphiLexer', 'PortugolLexer']


class PortugolLexer(Lexer):
    """For Portugol, a Pascal dialect with keywords in Portuguese."""
    name = 'Portugol'
    aliases = ['portugol']
    filenames = ['*.alg', '*.portugol']
    mimetypes = []
    url = "https://www.apoioinformatica.inf.br/produtos/visualg/linguagem"
    version_added = ''

    def __init__(self, **options):
        Lexer.__init__(self, **options)
        self.lexer = DelphiLexer(**options, portugol=True)

    def get_tokens_unprocessed(self, text):
        return self.lexer.get_tokens_unprocessed(text)


class DelphiLexer(Lexer):
    """
    For Delphi (Borland Object Pascal),
    Turbo Pascal and Free Pascal source code.

    Additional options accepted:

    `turbopascal`
        Highlight Turbo Pascal specific keywords (default: ``True``).
    `delphi`
        Highlight Borland Delphi specific keywords (default: ``True``).
    `freepascal`
        Highlight Free Pascal specific keywords (default: ``True``).
    `units`
        A list of units that should be considered builtin, supported are
        ``System``, ``SysUtils``, ``Classes`` and ``Math``.
        Default is to consider all of them builtin.
    """
    name = 'Delphi'
    aliases = ['delphi', 'pas', 'pascal', 'objectpascal']
    filenames = ['*.pas', '*.dpr']
    mimetypes = ['text/x-pascal']
    url = 'https://www.embarcadero.com/products/delphi'
    version_added = ''

    TURBO_PASCAL_KEYWORDS = (
        'absolute', 'and', 'array', 'asm', 'begin', 'break', 'case',
        'const', 'constructor', 'continue', 'destructor', 'div', 'do',
        'downto', 'else', 'end', 'file', 'for', 'function', 'goto',
        'if', 'implementation', 'in', 'inherited', 'inline', 'interface',
        'label', 'mod', 'nil', 'not', 'object', 'of', 'on', 'operator',
        'or', 'packed', 'procedure', 'program', 'record', 'reintroduce',
        'repeat', 'self', 'set', 'shl', 'shr', 'string', 'then', 'to',
        'type', 'unit', 'until', 'uses', 'var', 'while', 'with', 'xor'
    )

    DELPHI_KEYWORDS = (
        'as', 'class', 'except', 'exports', 'finalization', 'finally',
        'initialization', 'is', 'library', 'on', 'property', 'raise',
        'threadvar', 'try'
    )

    FREE_PASCAL_KEYWORDS = (
        'dispose', 'exit', 'false', 'new', 'true'
    )

    BLOCK_KEYWORDS = {
        'begin', 'class', 'const', 'constructor', 'destructor', 'end',
        'finalization', 'function', 'implementation', 'initialization',
        'label', 'library', 'operator', 'procedure', 'program', 'property',
        'record', 'threadvar', 'type', 'unit', 'uses', 'var'
    }

    FUNCTION_MODIFIERS = {
        'alias', 'cdecl', 'export', 'inline', 'interrupt', 'nostackframe',
        'pascal', 'register', 'safecall', 'softfloat', 'stdcall',
        'varargs', 'name', 'dynamic', 'near', 'virtual', 'external',
        'override', 'assembler'
    }

    # XXX: those aren't global. but currently we know no way for defining
    #      them just for the type context.
    DIRECTIVES = {
        'absolute', 'abstract', 'assembler', 'cppdecl', 'default', 'far',
        'far16', 'forward', 'index', 'oldfpccall', 'private', 'protected',
        'published', 'public'
    }

    BUILTIN_TYPES = {
        'ansichar', 'ansistring', 'bool', 'boolean', 'byte', 'bytebool',
        'cardinal', 'char', 'comp', 'currency', 'double', 'dword',
        'extended', 'int64', 'integer', 'iunknown', 'longbool', 'longint',
        'longword', 'pansichar', 'pansistring', 'pbool', 'pboolean',
        'pbyte', 'pbytearray', 'pcardinal', 'pchar', 'pcomp', 'pcurrency',
        'pdate', 'pdatetime', 'pdouble', 'pdword', 'pextended', 'phandle',
        'pint64', 'pinteger', 'plongint', 'plongword', 'pointer',
        'ppointer', 'pshortint', 'pshortstring', 'psingle', 'psmallint',
        'pstring', 'pvariant', 'pwidechar', 'pwidestring', 'pword',
        'pwordarray', 'pwordbool', 'real', 'real48', 'shortint',
        'shortstring', 'single', 'smallint', 'string', 'tclass', 'tdate',
        'tdatetime', 'textfile', 'thandle', 'tobject', 'ttime', 'variant',
        'widechar', 'widestring', 'word', 'wordbool'
    }

    BUILTIN_UNITS = {
        'System': (
            'abs', 'acquireexceptionobject', 'addr', 'ansitoutf8',
            'append', 'arctan', 'assert', 'assigned', 'assignfile',
            'beginthread', 'blockread', 'blockwrite', 'break', 'chdir',
            'chr', 'close', 'closefile', 'comptocurrency', 'comptodouble',
            'concat', 'continue', 'copy', 'cos', 'dec', 'delete',
            'dispose', 'doubletocomp', 'endthread', 'enummodules',
            'enumresourcemodules', 'eof', 'eoln', 'erase', 'exceptaddr',
            'exceptobject', 'exclude', 'exit', 'exp', 'filepos', 'filesize',
            'fillchar', 'finalize', 'findclasshinstance', 'findhinstance',
            'findresourcehinstance', 'flush', 'frac', 'freemem',
            'get8087cw', 'getdir', 'getlasterror', 'getmem',
            'getmemorymanager', 'getmodulefilename', 'getvariantmanager',
            'halt', 'hi', 'high', 'inc', 'include', 'initialize', 'insert',
            'int', 'ioresult', 'ismemorymanagerset', 'isvariantmanagerset',
            'length', 'ln', 'lo', 'low', 'mkdir', 'move', 'new', 'odd',
            'olestrtostring', 'olestrtostrvar', 'ord', 'paramcount',
            'paramstr', 'pi', 'pos', 'pred', 'ptr', 'pucs4chars', 'random',
            'randomize', 'read', 'readln', 'reallocmem',
            'releaseexceptionobject', 'rename', 'reset', 'rewrite', 'rmdir',
            'round', 'runerror', 'seek', 'seekeof', 'seekeoln',
            'set8087cw', 'setlength', 'setlinebreakstyle',
            'setmemorymanager', 'setstring', 'settextbuf',
            'setvariantmanager', 'sin', 'sizeof', 'slice', 'sqr', 'sqrt',
            'str', 'stringofchar', 'stringtoolestr', 'stringtowidechar',
            'succ', 'swap', 'trunc', 'truncate', 'typeinfo',
            'ucs4stringtowidestring', 'unicodetoutf8', 'uniquestring',
            'upcase', 'utf8decode', 'utf8encode', 'utf8toansi',
            'utf8tounicode', 'val', 'vararrayredim', 'varclear',
            'widecharlentostring', 'widecharlentostrvar',
            'widechartostring', 'widechartostrvar',
            'widestringtoucs4string', 'write', 'writeln'
        ),
        'SysUtils': (
            'abort', 'addexitproc', 'addterminateproc', 'adjustlinebreaks',
            'allocmem', 'ansicomparefilename', 'ansicomparestr',
            'ansicomparetext', 'ansidequotedstr', 'ansiextractquotedstr',
            'ansilastchar', 'ansilowercase', 'ansilowercasefilename',
            'ansipos', 'ansiquotedstr', 'ansisamestr', 'ansisametext',
            'ansistrcomp', 'ansistricomp', 'ansistrlastchar', 'ansistrlcomp',
            'ansistrlicomp', 'ansistrlower', 'ansistrpos', 'ansistrrscan',
            'ansistrscan', 'ansistrupper', 'ansiuppercase',
            'ansiuppercasefilename', 'appendstr', 'assignstr', 'beep',
            'booltostr', 'bytetocharindex', 'bytetocharlen', 'bytetype',
            'callterminateprocs', 'changefileext', 'charlength',
            'chartobyteindex', 'chartobytelen', 'comparemem', 'comparestr',
            'comparetext', 'createdir', 'createguid', 'currentyear',
            'currtostr', 'currtostrf', 'date', 'datetimetofiledate',
            'datetimetostr', 'datetimetostring', 'datetimetosystemtime',
            'datetimetotimestamp', 'datetostr', 'dayofweek', 'decodedate',
            'decodedatefully', 'decodetime', 'deletefile', 'directoryexists',
            'diskfree', 'disksize', 'disposestr', 'encodedate', 'encodetime',
            'exceptionerrormessage', 'excludetrailingbackslash',
            'excludetrailingpathdelimiter', 'expandfilename',
            'expandfilenamecase', 'expanduncfilename', 'extractfiledir',
            'extractfiledrive', 'extractfileext', 'extractfilename',
            'extractfilepath', 'extractrelativepath', 'extractshortpathname',
            'fileage', 'fileclose', 'filecreate', 'filedatetodatetime',
            'fileexists', 'filegetattr', 'filegetdate', 'fileisreadonly',
            'fileopen', 'fileread', 'filesearch', 'fileseek', 'filesetattr',
            'filesetdate', 'filesetreadonly', 'filewrite', 'finalizepackage',
            'findclose', 'findcmdlineswitch', 'findfirst', 'findnext',
            'floattocurr', 'floattodatetime', 'floattodecimal', 'floattostr',
            'floattostrf', 'floattotext', 'floattotextfmt', 'fmtloadstr',
            'fmtstr', 'forcedirectories', 'format', 'formatbuf', 'formatcurr',
            'formatdatetime', 'formatfloat', 'freeandnil', 'getcurrentdir',
            'getenvironmentvariable', 'getfileversion', 'getformatsettings',
            'getlocaleformatsettings', 'getmodulename', 'getpackagedescription',
            'getpackageinfo', 'gettime', 'guidtostring', 'incamonth',
            'includetrailingbackslash', 'includetrailingpathdelimiter',
            'incmonth', 'initializepackage', 'interlockeddecrement',
            'interlockedexchange', 'interlockedexchangeadd',
            'interlockedincrement', 'inttohex', 'inttostr', 'isdelimiter',
            'isequalguid', 'isleapyear', 'ispathdelimiter', 'isvalidident',
            'languages', 'lastdelimiter', 'loadpackage', 'loadstr',
            'lowercase', 'msecstotimestamp', 'newstr', 'nextcharindex', 'now',
            'outofmemoryerror', 'quotedstr', 'raiselastoserror',
            'raiselastwin32error', 'removedir', 'renamefile', 'replacedate',
            'replacetime', 'safeloadlibrary', 'samefilename', 'sametext',
            'setcurrentdir', 'showexception', 'sleep', 'stralloc', 'strbufsize',
            'strbytetype', 'strcat', 'strcharlength', 'strcomp', 'strcopy',
            'strdispose', 'strecopy', 'strend', 'strfmt', 'stricomp',
            'stringreplace', 'stringtoguid', 'strlcat', 'strlcomp', 'strlcopy',
            'strlen', 'strlfmt', 'strlicomp', 'strlower', 'strmove', 'strnew',
            'strnextchar', 'strpas', 'strpcopy', 'strplcopy', 'strpos',
            'strrscan', 'strscan', 'strtobool', 'strtobooldef', 'strtocurr',
            'strtocurrdef', 'strtodate', 'strtodatedef', 'strtodatetime',
            'strtodatetimedef', 'strtofloat', 'strtofloatdef', 'strtoint',
            'strtoint64', 'strtoint64def', 'strtointdef', 'strtotime',
            'strtotimedef', 'strupper', 'supports', 'syserrormessage',
            'systemtimetodatetime', 'texttofloat', 'time', 'timestamptodatetime',
            'timestamptomsecs', 'timetostr', 'trim', 'trimleft', 'trimright',
            'tryencodedate', 'tryencodetime', 'tryfloattocurr', 'tryfloattodatetime',
            'trystrtobool', 'trystrtocurr', 'trystrtodate', 'trystrtodatetime',
            'trystrtofloat', 'trystrtoint', 'trystrtoint64', 'trystrtotime',
            'unloadpackage', 'uppercase', 'widecomparestr', 'widecomparetext',
            'widefmtstr', 'wideformat', 'wideformatbuf', 'widelowercase',
            'widesamestr', 'widesametext', 'wideuppercase', 'win32check',
            'wraptext'
        ),
        'Classes': (
            'activateclassgroup', 'allocatehwnd', 'bintohex', 'checksynchronize',
            'collectionsequal', 'countgenerations', 'deallocatehwnd', 'equalrect',
            'extractstrings', 'findclass', 'findglobalcomponent', 'getclass',
            'groupdescendantswith', 'hextobin', 'identtoint',
            'initinheritedcomponent', 'inttoident', 'invalidpoint',
            'isuniqueglobalcomponentname', 'linestart', 'objectbinarytotext',
            'objectresourcetotext', 'objecttexttobinary', 'objecttexttoresource',
            'pointsequal', 'readcomponentres', 'readcomponentresex',
            'readcomponentresfile', 'rect', 'registerclass', 'registerclassalias',
            'registerclasses', 'registercomponents', 'registerintegerconsts',
            'registernoicon', 'registernonactivex', 'smallpoint', 'startclassgroup',
            'teststreamformat', 'unregisterclass', 'unregisterclasses',
            'unregisterintegerconsts', 'unregistermoduleclasses',
            'writecomponentresfile'
        ),
        'Math': (
            'arccos', 'arccosh', 'arccot', 'arccoth', 'arccsc', 'arccsch', 'arcsec',
            'arcsech', 'arcsin', 'arcsinh', 'arctan2', 'arctanh', 'ceil',
            'comparevalue', 'cosecant', 'cosh', 'cot', 'cotan', 'coth', 'csc',
            'csch', 'cycletodeg', 'cycletograd', 'cycletorad', 'degtocycle',
            'degtograd', 'degtorad', 'divmod', 'doubledecliningbalance',
            'ensurerange', 'floor', 'frexp', 'futurevalue', 'getexceptionmask',
            'getprecisionmode', 'getroundmode', 'gradtocycle', 'gradtodeg',
            'gradtorad', 'hypot', 'inrange', 'interestpayment', 'interestrate',
            'internalrateofreturn', 'intpower', 'isinfinite', 'isnan', 'iszero',
            'ldexp', 'lnxp1', 'log10', 'log2', 'logn', 'max', 'maxintvalue',
            'maxvalue', 'mean', 'meanandstddev', 'min', 'minintvalue', 'minvalue',
            'momentskewkurtosis', 'netpresentvalue', 'norm', 'numberofperiods',
            'payment', 'periodpayment', 'poly', 'popnstddev', 'popnvariance',
            'power', 'presentvalue', 'radtocycle', 'radtodeg', 'radtograd',
            'randg', 'randomrange', 'roundto', 'samevalue', 'sec', 'secant',
            'sech', 'setexceptionmask', 'setprecisionmode', 'setroundmode',
            'sign', 'simpleroundto', 'sincos', 'sinh', 'slndepreciation', 'stddev',
            'sum', 'sumint', 'sumofsquares', 'sumsandsquares', 'syddepreciation',
            'tan', 'tanh', 'totalvariance', 'variance'
        )
    }

    ASM_REGISTERS = {
        'ah', 'al', 'ax', 'bh', 'bl', 'bp', 'bx', 'ch', 'cl', 'cr0',
        'cr1', 'cr2', 'cr3', 'cr4', 'cs', 'cx', 'dh', 'di', 'dl', 'dr0',
        'dr1', 'dr2', 'dr3', 'dr4', 'dr5', 'dr6', 'dr7', 'ds', 'dx',
        'eax', 'ebp', 'ebx', 'ecx', 'edi', 'edx', 'es', 'esi', 'esp',
        'fs', 'gs', 'mm0', 'mm1', 'mm2', 'mm3', 'mm4', 'mm5', 'mm6',
        'mm7', 'si', 'sp', 'ss', 'st0', 'st1', 'st2', 'st3', 'st4', 'st5',
        'st6', 'st7', 'xmm0', 'xmm1', 'xmm2', 'xmm3', 'xmm4', 'xmm5',
        'xmm6', 'xmm7'
    }

    ASM_INSTRUCTIONS = {
        'aaa', 'aad', 'aam', 'aas', 'adc', 'add', 'and', 'arpl', 'bound',
        'bsf', 'bsr', 'bswap', 'bt', 'btc', 'btr', 'bts', 'call', 'cbw',
        'cdq', 'clc', 'cld', 'cli', 'clts', 'cmc', 'cmova', 'cmovae',
        'cmovb', 'cmovbe', 'cmovc', 'cmovcxz', 'cmove', 'cmovg',
        'cmovge', 'cmovl', 'cmovle', 'cmovna', 'cmovnae', 'cmovnb',
        'cmovnbe', 'cmovnc', 'cmovne', 'cmovng', 'cmovnge', 'cmovnl',
        'cmovnle', 'cmovno', 'cmovnp', 'cmovns', 'cmovnz', 'cmovo',
        'cmovp', 'cmovpe', 'cmovpo', 'cmovs', 'cmovz', 'cmp', 'cmpsb',
        'cmpsd', 'cmpsw', 'cmpxchg', 'cmpxchg486', 'cmpxchg8b', 'cpuid',
        'cwd', 'cwde', 'daa', 'das', 'dec', 'div', 'emms', 'enter', 'hlt',
        'ibts', 'icebp', 'idiv', 'imul', 'in', 'inc', 'insb', 'insd',
        'insw', 'int', 'int01', 'int03', 'int1', 'int3', 'into', 'invd',
        'invlpg', 'iret', 'iretd', 'iretw', 'ja', 'jae', 'jb', 'jbe',
        'jc', 'jcxz', 'jcxz', 'je', 'jecxz', 'jg', 'jge', 'jl', 'jle',
        'jmp', 'jna', 'jnae', 'jnb', 'jnbe', 'jnc', 'jne', 'jng', 'jnge',
        'jnl', 'jnle', 'jno', 'jnp', 'jns', 'jnz', 'jo', 'jp', 'jpe',
        'jpo', 'js', 'jz', 'lahf', 'lar', 'lcall', 'lds', 'lea', 'leave',
        'les', 'lfs', 'lgdt', 'lgs', 'lidt', 'ljmp', 'lldt', 'lmsw',
        'loadall', 'loadall286', 'lock', 'lodsb', 'lodsd', 'lodsw',
        'loop', 'loope', 'loopne', 'loopnz', 'loopz', 'lsl', 'lss', 'ltr',
        'mov', 'movd', 'movq', 'movsb', 'movsd', 'movsw', 'movsx',
        'movzx', 'mul', 'neg', 'nop', 'not', 'or', 'out', 'outsb', 'outsd',
        'outsw', 'pop', 'popa', 'popad', 'popaw', 'popf', 'popfd', 'popfw',
        'push', 'pusha', 'pushad', 'pushaw', 'pushf', 'pushfd', 'pushfw',
        'rcl', 'rcr', 'rdmsr', 'rdpmc', 'rdshr', 'rdtsc', 'rep', 'repe',
        'repne', 'repnz', 'repz', 'ret', 'retf', 'retn', 'rol', 'ror',
        'rsdc', 'rsldt', 'rsm', 'sahf', 'sal', 'salc', 'sar', 'sbb',
        'scasb', 'scasd', 'scasw', 'seta', 'setae', 'setb', 'setbe',
        'setc', 'setcxz', 'sete', 'setg', 'setge', 'setl', 'setle',
        'setna', 'setnae', 'setnb', 'setnbe', 'setnc', 'setne', 'setng',
        'setnge', 'setnl', 'setnle', 'setno', 'setnp', 'setns', 'setnz',
        'seto', 'setp', 'setpe', 'setpo', 'sets', 'setz', 'sgdt', 'shl',
        'shld', 'shr', 'shrd', 'sidt', 'sldt', 'smi', 'smint', 'smintold',
        'smsw', 'stc', 'std', 'sti', 'stosb', 'stosd', 'stosw', 'str',
        'sub', 'svdc', 'svldt', 'svts', 'syscall', 'sysenter', 'sysexit',
        'sysret', 'test', 'ud1', 'ud2', 'umov', 'verr', 'verw', 'wait',
        'wbinvd', 'wrmsr', 'wrshr', 'xadd', 'xbts', 'xchg', 'xlat',
        'xlatb', 'xor'
    }

    PORTUGOL_KEYWORDS = (
        'aleatorio',
        'algoritmo',
        'arquivo',
        'ate',
        'caso',
        'cronometro',
        'debug',
        'e',
        'eco',
        'enquanto',
        'entao',
        'escolha',
        'escreva',
        'escreval',
        'faca',
        'falso',
        'fimalgoritmo',
        'fimenquanto',
        'fimescolha',
        'fimfuncao',
        'fimpara',
        'fimprocedimento',
        'fimrepita',
        'fimse',
        'funcao',
        'inicio',
        'int',
        'interrompa',
        'leia',
        'limpatela',
        'mod',
        'nao',
        'ou',
        'outrocaso',
        'para',
        'passo',
        'pausa',
        'procedimento',
        'repita',
        'retorne',
        'se',
        'senao',
        'timer',
        'var',
        'vetor',
        'verdadeiro',
        'xou',
        'div',
        'mod',
        'abs',
        'arccos',
        'arcsen',
        'arctan',
        'cos',
        'cotan',
        'Exp',
        'grauprad',
        'int',
        'log',
        'logn',
        'pi',
        'quad',
        'radpgrau',
        'raizq',
        'rand',
        'randi',
        'sen',
        'Tan',
        'asc',
        'carac',
        'caracpnum',
        'compr',
        'copia',
        'maiusc',
        'minusc',
        'numpcarac',
        'pos',
    )

    PORTUGOL_BUILTIN_TYPES = {
        'inteiro', 'real', 'caractere', 'logico'
    }

    def __init__(self, **options):
        Lexer.__init__(self, **options)
        self.keywords = set()
        self.builtins = set()
        if get_bool_opt(options, 'portugol', False):
            self.keywords.update(self.PORTUGOL_KEYWORDS)
            self.builtins.update(self.PORTUGOL_BUILTIN_TYPES)
            self.is_portugol = True
        else:
            self.is_portugol = False

            if get_bool_opt(options, 'turbopascal', True):
                self.keywords.update(self.TURBO_PASCAL_KEYWORDS)
            if get_bool_opt(options, 'delphi', True):
                self.keywords.update(self.DELPHI_KEYWORDS)
            if get_bool_opt(options, 'freepascal', True):
                self.keywords.update(self.FREE_PASCAL_KEYWORDS)
            for unit in get_list_opt(options, 'units', list(self.BUILTIN_UNITS)):
                self.builtins.update(self.BUILTIN_UNITS[unit])

    def get_tokens_unprocessed(self, text):
        scanner = Scanner(text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        stack = ['initial']
        in_function_block = False
        in_property_block = False
        was_dot = False
        next_token_is_function = False
        next_token_is_property = False
        collect_labels = False
        block_labels = set()
        brace_balance = [0, 0]

        while not scanner.eos:
            token = Error

            if stack[-1] == 'initial':
                if scanner.scan(r'\s+'):
                    token = Whitespace
                elif not self.is_portugol and scanner.scan(r'\{.*?\}|\(\*.*?\*\)'):
                    if scanner.match.startswith('$'):
                        token = Comment.Preproc
                    else:
                        token = Comment.Multiline
                elif scanner.scan(r'//.*?$'):
                    token = Comment.Single
                elif self.is_portugol and scanner.scan(r'(<\-)|(>=)|(<=)|%|<|>|-|\+|\*|\=|(<>)|\/|\.|:|,'):
                    token = Operator
                elif not self.is_portugol and scanner.scan(r'[-+*\/=<>:;,.@\^]'):
                    token = Operator
                    # stop label highlighting on next ";"
                    if collect_labels and scanner.match == ';':
                        collect_labels = False
                elif scanner.scan(r'[\(\)\[\]]+'):
                    token = Punctuation
                    # abort function naming ``foo = Function(...)``
                    next_token_is_function = False
                    # if we are in a function block we count the open
                    # braces because ootherwise it's impossible to
                    # determine the end of the modifier context
                    if in_function_block or in_property_block:
                        if scanner.match == '(':
                            brace_balance[0] += 1
                        elif scanner.match == ')':
                            brace_balance[0] -= 1
                        elif scanner.match == '[':
                            brace_balance[1] += 1
                        elif scanner.match == ']':
                            brace_balance[1] -= 1
                elif scanner.scan(r'[A-Za-z_][A-Za-z_0-9]*'):
                    lowercase_name = scanner.match.lower()
                    if lowercase_name == 'result':
                        token = Name.Builtin.Pseudo
                    elif lowercase_name in self.keywords:
                        token = Keyword
                        # if we are in a special block and a
                        # block ending keyword occurs (and the parenthesis
                        # is balanced) we end the current block context
                        if self.is_portugol:
                            if lowercase_name in ('funcao', 'procedimento'):
                                in_function_block = True
                                next_token_is_function = True
                        else:
                            if (in_function_block or in_property_block) and \
                                    lowercase_name in self.BLOCK_KEYWORDS and \
                                    brace_balance[0] <= 0 and \
                                    brace_balance[1] <= 0:
                                in_function_block = False
                                in_property_block = False
                                brace_balance = [0, 0]
                                block_labels = set()
                            if lowercase_name in ('label', 'goto'):
                                collect_labels = True
                            elif lowercase_name == 'asm':
                                stack.append('asm')
                            elif lowercase_name == 'property':
                                in_property_block = True
                                next_token_is_property = True
                            elif lowercase_name in ('procedure', 'operator',
                                                    'function', 'constructor',
                                                    'destructor'):
                                in_function_block = True
                                next_token_is_function = True
                    # we are in a function block and the current name
                    # is in the set of registered modifiers. highlight
                    # it as pseudo keyword
                    elif not self.is_portugol and in_function_block and \
                            lowercase_name in self.FUNCTION_MODIFIERS:
                        token = Keyword.Pseudo
                    # if we are in a property highlight some more
                    # modifiers
                    elif not self.is_portugol and in_property_block and \
                            lowercase_name in ('read', 'write'):
                        token = Keyword.Pseudo
                        next_token_is_function = True
                    # if the last iteration set next_token_is_function
                    # to true we now want this name highlighted as
                    # function. so do that and reset the state
                    elif next_token_is_function:
                        # Look if the next token is a dot. If yes it's
                        # not a function, but a class name and the
                        # part after the dot a function name
                        if not self.is_portugol and scanner.test(r'\s*\.\s*'):
                            token = Name.Class
                        # it's not a dot, our job is done
                        else:
                            token = Name.Function
                            next_token_is_function = False

                            if self.is_portugol:
                                block_labels.add(scanner.match.lower())

                    # same for properties
                    elif not self.is_portugol and next_token_is_property:
                        token = Name.Property
                        next_token_is_property = False
                    # Highlight this token as label and add it
                    # to the list of known labels
                    elif not self.is_portugol and collect_labels:
                        token = Name.Label
                        block_labels.add(scanner.match.lower())
                    # name is in list of known labels
                    elif lowercase_name in block_labels:
                        token = Name.Label
                    elif self.is_portugol and lowercase_name in self.PORTUGOL_BUILTIN_TYPES:
                        token = Keyword.Type
                    elif not self.is_portugol and lowercase_name in self.BUILTIN_TYPES:
                        token = Keyword.Type
                    elif not self.is_portugol and lowercase_name in self.DIRECTIVES:
                        token = Keyword.Pseudo
                    # builtins are just builtins if the token
                    # before isn't a dot
                    elif not self.is_portugol and not was_dot and lowercase_name in self.builtins:
                        token = Name.Builtin
                    else:
                        token = Name
                elif self.is_portugol and scanner.scan(r"\""):
                    token = String
                    stack.append('string')
                elif not self.is_portugol and scanner.scan(r"'"):
                    token = String
                    stack.append('string')
                elif not self.is_portugol and scanner.scan(r'\#(\d+|\$[0-9A-Fa-f]+)'):
                    token = String.Char
                elif not self.is_portugol and scanner.scan(r'\$[0-9A-Fa-f]+'):
                    token = Number.Hex
                elif scanner.scan(r'\d+(?![eE]|\.[^.])'):
                    token = Number.Integer
                elif scanner.scan(r'\d+(\.\d+([eE][+-]?\d+)?|[eE][+-]?\d+)'):
                    token = Number.Float
                else:
                    # if the stack depth is deeper than once, pop
                    if len(stack) > 1:
                        stack.pop()
                    scanner.get_char()

            elif stack[-1] == 'string':
                if self.is_portugol:
                    if scanner.scan(r"''"):
                        token = String.Escape
                    elif scanner.scan(r"\""):
                        token = String
                        stack.pop()
                    elif scanner.scan(r"[^\"]*"):
                        token = String
                    else:
                        scanner.get_char()
                        stack.pop()
                else:
                    if scanner.scan(r"''"):
                        token = String.Escape
                    elif scanner.scan(r"'"):
                        token = String
                        stack.pop()
                    elif scanner.scan(r"[^']*"):
                        token = String
                    else:
                        scanner.get_char()
                        stack.pop()
            elif not self.is_portugol and stack[-1] == 'asm':
                if scanner.scan(r'\s+'):
                    token = Whitespace
                elif scanner.scan(r'end'):
                    token = Keyword
                    stack.pop()
                elif scanner.scan(r'\{.*?\}|\(\*.*?\*\)'):
                    if scanner.match.startswith('$'):
                        token = Comment.Preproc
                    else:
                        token = Comment.Multiline
                elif scanner.scan(r'//.*?$'):
                    token = Comment.Single
                elif scanner.scan(r"'"):
                    token = String
                    stack.append('string')
                elif scanner.scan(r'@@[A-Za-z_][A-Za-z_0-9]*'):
                    token = Name.Label
                elif scanner.scan(r'[A-Za-z_][A-Za-z_0-9]*'):
                    lowercase_name = scanner.match.lower()
                    if lowercase_name in self.ASM_INSTRUCTIONS:
                        token = Keyword
                    elif lowercase_name in self.ASM_REGISTERS:
                        token = Name.Builtin
                    else:
                        token = Name
                elif scanner.scan(r'[-+*\/=<>:;,.@\^]+'):
                    token = Operator
                elif scanner.scan(r'[\(\)\[\]]+'):
                    token = Punctuation
                elif scanner.scan(r'\$[0-9A-Fa-f]+'):
                    token = Number.Hex
                elif scanner.scan(r'\d+(?![eE]|\.[^.])'):
                    token = Number.Integer
                elif scanner.scan(r'\d+(\.\d+([eE][+-]?\d+)?|[eE][+-]?\d+)'):
                    token = Number.Float
                else:
                    scanner.get_char()
                    stack.pop()

            # save the dot!!!11
            if not self.is_portugol and scanner.match.strip():
                was_dot = scanner.match == '.'

            yield scanner.start_pos, token, scanner.match or ''

# === NexusCore/openenv\Lib\site-packages\referencing\jsonschema.py ===
"""
Referencing implementations for JSON Schema specs (historic & current).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence, Set
from typing import Any, Union

from referencing import Anchor, Registry, Resource, Specification, exceptions
from referencing._attrs import frozen
from referencing._core import (
    _UNSET,  # type: ignore[reportPrivateUsage]
    Resolved as _Resolved,
    Resolver as _Resolver,
    _Unset,  # type: ignore[reportPrivateUsage]
)
from referencing.typing import URI, Anchor as AnchorType, Mapping

#: A JSON Schema which is a JSON object
ObjectSchema = Mapping[str, Any]

#: A JSON Schema of any kind
Schema = Union[bool, ObjectSchema]

#: A Resource whose contents are JSON Schemas
SchemaResource = Resource[Schema]

#: A JSON Schema Registry
SchemaRegistry = Registry[Schema]

#: The empty JSON Schema Registry
EMPTY_REGISTRY: SchemaRegistry = Registry()


@frozen
class UnknownDialect(Exception):
    """
    A dialect identifier was found for a dialect unknown by this library.

    If it's a custom ("unofficial") dialect, be sure you've registered it.
    """

    uri: URI


def _dollar_id(contents: Schema) -> URI | None:
    if isinstance(contents, bool):
        return
    return contents.get("$id")


def _legacy_dollar_id(contents: Schema) -> URI | None:
    if isinstance(contents, bool) or "$ref" in contents:
        return
    id = contents.get("$id")
    if id is not None and not id.startswith("#"):
        return id


def _legacy_id(contents: ObjectSchema) -> URI | None:
    if "$ref" in contents:
        return
    id = contents.get("id")
    if id is not None and not id.startswith("#"):
        return id


def _anchor(
    specification: Specification[Schema],
    contents: Schema,
) -> Iterable[AnchorType[Schema]]:
    if isinstance(contents, bool):
        return
    anchor = contents.get("$anchor")
    if anchor is not None:
        yield Anchor(
            name=anchor,
            resource=specification.create_resource(contents),
        )

    dynamic_anchor = contents.get("$dynamicAnchor")
    if dynamic_anchor is not None:
        yield DynamicAnchor(
            name=dynamic_anchor,
            resource=specification.create_resource(contents),
        )


def _anchor_2019(
    specification: Specification[Schema],
    contents: Schema,
) -> Iterable[Anchor[Schema]]:
    if isinstance(contents, bool):
        return []
    anchor = contents.get("$anchor")
    if anchor is None:
        return []
    return [
        Anchor(
            name=anchor,
            resource=specification.create_resource(contents),
        ),
    ]


def _legacy_anchor_in_dollar_id(
    specification: Specification[Schema],
    contents: Schema,
) -> Iterable[Anchor[Schema]]:
    if isinstance(contents, bool):
        return []
    id = contents.get("$id", "")
    if not id.startswith("#"):
        return []
    return [
        Anchor(
            name=id[1:],
            resource=specification.create_resource(contents),
        ),
    ]


def _legacy_anchor_in_id(
    specification: Specification[ObjectSchema],
    contents: ObjectSchema,
) -> Iterable[Anchor[ObjectSchema]]:
    id = contents.get("id", "")
    if not id.startswith("#"):
        return []
    return [
        Anchor(
            name=id[1:],
            resource=specification.create_resource(contents),
        ),
    ]


def _subresources_of(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    """
    Create a callable returning JSON Schema specification-style subschemas.

    Relies on specifying the set of keywords containing subschemas in their
    values, in a subobject's values, or in a subarray.
    """

    def subresources_of(contents: Schema) -> Iterable[ObjectSchema]:
        if isinstance(contents, bool):
            return
        for each in in_value:
            if each in contents:
                yield contents[each]
        for each in in_subarray:
            if each in contents:
                yield from contents[each]
        for each in in_subvalues:
            if each in contents:
                yield from contents[each].values()

    return subresources_of


def _subresources_of_with_crazy_items(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    """
    Specifically handle older drafts where there are some funky keywords.
    """

    def subresources_of(contents: Schema) -> Iterable[ObjectSchema]:
        if isinstance(contents, bool):
            return
        for each in in_value:
            if each in contents:
                yield contents[each]
        for each in in_subarray:
            if each in contents:
                yield from contents[each]
        for each in in_subvalues:
            if each in contents:
                yield from contents[each].values()

        items = contents.get("items")
        if items is not None:
            if isinstance(items, Sequence):
                yield from items
            else:
                yield items

    return subresources_of


def _subresources_of_with_crazy_items_dependencies(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    """
    Specifically handle older drafts where there are some funky keywords.
    """

    def subresources_of(contents: Schema) -> Iterable[ObjectSchema]:
        if isinstance(contents, bool):
            return
        for each in in_value:
            if each in contents:
                yield contents[each]
        for each in in_subarray:
            if each in contents:
                yield from contents[each]
        for each in in_subvalues:
            if each in contents:
                yield from contents[each].values()

        items = contents.get("items")
        if items is not None:
            if isinstance(items, Sequence):
                yield from items
            else:
                yield items
        dependencies = contents.get("dependencies")
        if dependencies is not None:
            values = iter(dependencies.values())
            value = next(values, None)
            if isinstance(value, Mapping):
                yield value
                yield from values

    return subresources_of


def _subresources_of_with_crazy_aP_items_dependencies(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    """
    Specifically handle even older drafts where there are some funky keywords.
    """

    def subresources_of(contents: ObjectSchema) -> Iterable[ObjectSchema]:
        for each in in_value:
            if each in contents:
                yield contents[each]
        for each in in_subarray:
            if each in contents:
                yield from contents[each]
        for each in in_subvalues:
            if each in contents:
                yield from contents[each].values()

        items = contents.get("items")
        if items is not None:
            if isinstance(items, Sequence):
                yield from items
            else:
                yield items
        dependencies = contents.get("dependencies")
        if dependencies is not None:
            values = iter(dependencies.values())
            value = next(values, None)
            if isinstance(value, Mapping):
                yield value
                yield from values

        for each in "additionalItems", "additionalProperties":
            value = contents.get(each)
            if isinstance(value, Mapping):
                yield value

    return subresources_of


def _maybe_in_subresource(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    in_child = in_subvalues | in_subarray

    def maybe_in_subresource(
        segments: Sequence[int | str],
        resolver: _Resolver[Any],
        subresource: Resource[Any],
    ) -> _Resolver[Any]:
        _segments = iter(segments)
        for segment in _segments:
            if segment not in in_value and (
                segment not in in_child or next(_segments, None) is None
            ):
                return resolver
        return resolver.in_subresource(subresource)

    return maybe_in_subresource


def _maybe_in_subresource_crazy_items(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    in_child = in_subvalues | in_subarray

    def maybe_in_subresource(
        segments: Sequence[int | str],
        resolver: _Resolver[Any],
        subresource: Resource[Any],
    ) -> _Resolver[Any]:
        _segments = iter(segments)
        for segment in _segments:
            if segment == "items" and isinstance(
                subresource.contents,
                Mapping,
            ):
                return resolver.in_subresource(subresource)
            if segment not in in_value and (
                segment not in in_child or next(_segments, None) is None
            ):
                return resolver
        return resolver.in_subresource(subresource)

    return maybe_in_subresource


def _maybe_in_subresource_crazy_items_dependencies(
    in_value: Set[str] = frozenset(),
    in_subvalues: Set[str] = frozenset(),
    in_subarray: Set[str] = frozenset(),
):
    in_child = in_subvalues | in_subarray

    def maybe_in_subresource(
        segments: Sequence[int | str],
        resolver: _Resolver[Any],
        subresource: Resource[Any],
    ) -> _Resolver[Any]:
        _segments = iter(segments)
        for segment in _segments:
            if segment in {"items", "dependencies"} and isinstance(
                subresource.contents,
                Mapping,
            ):
                return resolver.in_subresource(subresource)
            if segment not in in_value and (
                segment not in in_child or next(_segments, None) is None
            ):
                return resolver
        return resolver.in_subresource(subresource)

    return maybe_in_subresource


#: JSON Schema draft 2020-12
DRAFT202012 = Specification(
    name="draft2020-12",
    id_of=_dollar_id,
    subresources_of=_subresources_of(
        in_value={
            "additionalProperties",
            "contains",
            "contentSchema",
            "else",
            "if",
            "items",
            "not",
            "propertyNames",
            "then",
            "unevaluatedItems",
            "unevaluatedProperties",
        },
        in_subarray={"allOf", "anyOf", "oneOf", "prefixItems"},
        in_subvalues={
            "$defs",
            "definitions",
            "dependentSchemas",
            "patternProperties",
            "properties",
        },
    ),
    anchors_in=_anchor,
    maybe_in_subresource=_maybe_in_subresource(
        in_value={
            "additionalProperties",
            "contains",
            "contentSchema",
            "else",
            "if",
            "items",
            "not",
            "propertyNames",
            "then",
            "unevaluatedItems",
            "unevaluatedProperties",
        },
        in_subarray={"allOf", "anyOf", "oneOf", "prefixItems"},
        in_subvalues={
            "$defs",
            "definitions",
            "dependentSchemas",
            "patternProperties",
            "properties",
        },
    ),
)
#: JSON Schema draft 2019-09
DRAFT201909 = Specification(
    name="draft2019-09",
    id_of=_dollar_id,
    subresources_of=_subresources_of_with_crazy_items(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "contentSchema",
            "else",
            "if",
            "not",
            "propertyNames",
            "then",
            "unevaluatedItems",
            "unevaluatedProperties",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={
            "$defs",
            "definitions",
            "dependentSchemas",
            "patternProperties",
            "properties",
        },
    ),
    anchors_in=_anchor_2019,
    maybe_in_subresource=_maybe_in_subresource_crazy_items(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "contentSchema",
            "else",
            "if",
            "not",
            "propertyNames",
            "then",
            "unevaluatedItems",
            "unevaluatedProperties",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={
            "$defs",
            "definitions",
            "dependentSchemas",
            "patternProperties",
            "properties",
        },
    ),
)
#: JSON Schema draft 7
DRAFT7 = Specification(
    name="draft-07",
    id_of=_legacy_dollar_id,
    subresources_of=_subresources_of_with_crazy_items_dependencies(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "else",
            "if",
            "not",
            "propertyNames",
            "then",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
    anchors_in=_legacy_anchor_in_dollar_id,
    maybe_in_subresource=_maybe_in_subresource_crazy_items_dependencies(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "else",
            "if",
            "not",
            "propertyNames",
            "then",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
)
#: JSON Schema draft 6
DRAFT6 = Specification(
    name="draft-06",
    id_of=_legacy_dollar_id,
    subresources_of=_subresources_of_with_crazy_items_dependencies(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "not",
            "propertyNames",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
    anchors_in=_legacy_anchor_in_dollar_id,
    maybe_in_subresource=_maybe_in_subresource_crazy_items_dependencies(
        in_value={
            "additionalItems",
            "additionalProperties",
            "contains",
            "not",
            "propertyNames",
        },
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
)
#: JSON Schema draft 4
DRAFT4 = Specification(
    name="draft-04",
    id_of=_legacy_id,
    subresources_of=_subresources_of_with_crazy_aP_items_dependencies(
        in_value={"not"},
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
    anchors_in=_legacy_anchor_in_id,
    maybe_in_subresource=_maybe_in_subresource_crazy_items_dependencies(
        in_value={"additionalItems", "additionalProperties", "not"},
        in_subarray={"allOf", "anyOf", "oneOf"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
)
#: JSON Schema draft 3
DRAFT3 = Specification(
    name="draft-03",
    id_of=_legacy_id,
    subresources_of=_subresources_of_with_crazy_aP_items_dependencies(
        in_subarray={"extends"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
    anchors_in=_legacy_anchor_in_id,
    maybe_in_subresource=_maybe_in_subresource_crazy_items_dependencies(
        in_value={"additionalItems", "additionalProperties"},
        in_subarray={"extends"},
        in_subvalues={"definitions", "patternProperties", "properties"},
    ),
)


_SPECIFICATIONS: Registry[Specification[Schema]] = Registry(
    {
        dialect_id: Resource.opaque(specification)
        for dialect_id, specification in [
            ("https://json-schema.org/draft/2020-12/schema", DRAFT202012),
            ("https://json-schema.org/draft/2019-09/schema", DRAFT201909),
            ("http://json-schema.org/draft-07/schema", DRAFT7),
            ("http://json-schema.org/draft-06/schema", DRAFT6),
            ("http://json-schema.org/draft-04/schema", DRAFT4),
            ("http://json-schema.org/draft-03/schema", DRAFT3),
        ]
    },
)


def specification_with(
    dialect_id: URI,
    default: Specification[Any] | _Unset = _UNSET,
) -> Specification[Any]:
    """
    Retrieve the `Specification` with the given dialect identifier.

    Raises:

        `UnknownDialect`

            if the given ``dialect_id`` isn't known

    """
    resource = _SPECIFICATIONS.get(dialect_id.rstrip("#"))
    if resource is not None:
        return resource.contents
    if default is _UNSET:
        raise UnknownDialect(dialect_id)
    return default


@frozen
class DynamicAnchor:
    """
    Dynamic anchors, introduced in draft 2020.
    """

    name: str
    resource: SchemaResource

    def resolve(self, resolver: _Resolver[Schema]) -> _Resolved[Schema]:
        """
        Resolve this anchor dynamically.
        """
        last = self.resource
        for uri, registry in resolver.dynamic_scope():
            try:
                anchor = registry.anchor(uri, self.name).value
            except exceptions.NoSuchAnchor:
                continue
            if isinstance(anchor, DynamicAnchor):
                last = anchor.resource
        return _Resolved(
            contents=last.contents,
            resolver=resolver.in_subresource(last),
        )


def lookup_recursive_ref(resolver: _Resolver[Schema]) -> _Resolved[Schema]:
    """
    Recursive references (via recursive anchors), present only in draft 2019.

    As per the 2019 specification (§ 8.2.4.2.1), only the ``#`` recursive
    reference is supported (and is therefore assumed to be the relevant
    reference).
    """
    resolved = resolver.lookup("#")
    if isinstance(resolved.contents, Mapping) and resolved.contents.get(
        "$recursiveAnchor",
    ):
        for uri, _ in resolver.dynamic_scope():
            next_resolved = resolver.lookup(uri)
            if not isinstance(
                next_resolved.contents,
                Mapping,
            ) or not next_resolved.contents.get("$recursiveAnchor"):
                break
            resolved = next_resolved
    return resolved

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\models.py ===
"""Variation fonts interpolation models."""

__all__ = [
    "normalizeValue",
    "normalizeLocation",
    "supportScalar",
    "piecewiseLinearMap",
    "VariationModel",
]

from fontTools.misc.roundTools import noRound
from .errors import VariationModelError


def nonNone(lst):
    return [l for l in lst if l is not None]


def allNone(lst):
    return all(l is None for l in lst)


def allEqualTo(ref, lst, mapper=None):
    if mapper is None:
        return all(ref == item for item in lst)

    mapped = mapper(ref)
    return all(mapped == mapper(item) for item in lst)


def allEqual(lst, mapper=None):
    if not lst:
        return True
    it = iter(lst)
    try:
        first = next(it)
    except StopIteration:
        return True
    return allEqualTo(first, it, mapper=mapper)


def subList(truth, lst):
    assert len(truth) == len(lst)
    return [l for l, t in zip(lst, truth) if t]


def normalizeValue(v, triple, extrapolate=False):
    """Normalizes value based on a min/default/max triple.

    >>> normalizeValue(400, (100, 400, 900))
    0.0
    >>> normalizeValue(100, (100, 400, 900))
    -1.0
    >>> normalizeValue(650, (100, 400, 900))
    0.5
    """
    lower, default, upper = triple
    if not (lower <= default <= upper):
        raise ValueError(
            f"Invalid axis values, must be minimum, default, maximum: "
            f"{lower:3.3f}, {default:3.3f}, {upper:3.3f}"
        )
    if not extrapolate:
        v = max(min(v, upper), lower)

    if v == default or lower == upper:
        return 0.0

    if (v < default and lower != default) or (v > default and upper == default):
        return (v - default) / (default - lower)
    else:
        assert (v > default and upper != default) or (
            v < default and lower == default
        ), f"Ooops... v={v}, triple=({lower}, {default}, {upper})"
        return (v - default) / (upper - default)


def normalizeLocation(location, axes, extrapolate=False, *, validate=False):
    """Normalizes location based on axis min/default/max values from axes.

    >>> axes = {"wght": (100, 400, 900)}
    >>> normalizeLocation({"wght": 400}, axes)
    {'wght': 0.0}
    >>> normalizeLocation({"wght": 100}, axes)
    {'wght': -1.0}
    >>> normalizeLocation({"wght": 900}, axes)
    {'wght': 1.0}
    >>> normalizeLocation({"wght": 650}, axes)
    {'wght': 0.5}
    >>> normalizeLocation({"wght": 1000}, axes)
    {'wght': 1.0}
    >>> normalizeLocation({"wght": 0}, axes)
    {'wght': -1.0}
    >>> axes = {"wght": (0, 0, 1000)}
    >>> normalizeLocation({"wght": 0}, axes)
    {'wght': 0.0}
    >>> normalizeLocation({"wght": -1}, axes)
    {'wght': 0.0}
    >>> normalizeLocation({"wght": 1000}, axes)
    {'wght': 1.0}
    >>> normalizeLocation({"wght": 500}, axes)
    {'wght': 0.5}
    >>> normalizeLocation({"wght": 1001}, axes)
    {'wght': 1.0}
    >>> axes = {"wght": (0, 1000, 1000)}
    >>> normalizeLocation({"wght": 0}, axes)
    {'wght': -1.0}
    >>> normalizeLocation({"wght": -1}, axes)
    {'wght': -1.0}
    >>> normalizeLocation({"wght": 500}, axes)
    {'wght': -0.5}
    >>> normalizeLocation({"wght": 1000}, axes)
    {'wght': 0.0}
    >>> normalizeLocation({"wght": 1001}, axes)
    {'wght': 0.0}
    """
    if validate:
        assert set(location.keys()) <= set(axes.keys()), set(location.keys()) - set(
            axes.keys()
        )
    out = {}
    for tag, triple in axes.items():
        v = location.get(tag, triple[1])
        out[tag] = normalizeValue(v, triple, extrapolate=extrapolate)
    return out


def supportScalar(location, support, ot=True, extrapolate=False, axisRanges=None):
    """Returns the scalar multiplier at location, for a master
    with support.  If ot is True, then a peak value of zero
    for support of an axis means "axis does not participate".  That
    is how OpenType Variation Font technology works.

    If extrapolate is True, axisRanges must be a dict that maps axis
    names to (axisMin, axisMax) tuples.

      >>> supportScalar({}, {})
      1.0
      >>> supportScalar({'wght':.2}, {})
      1.0
      >>> supportScalar({'wght':.2}, {'wght':(0,2,3)})
      0.1
      >>> supportScalar({'wght':2.5}, {'wght':(0,2,4)})
      0.75
      >>> supportScalar({'wght':2.5, 'wdth':0}, {'wght':(0,2,4), 'wdth':(-1,0,+1)})
      0.75
      >>> supportScalar({'wght':2.5, 'wdth':.5}, {'wght':(0,2,4), 'wdth':(-1,0,+1)}, ot=False)
      0.375
      >>> supportScalar({'wght':2.5, 'wdth':0}, {'wght':(0,2,4), 'wdth':(-1,0,+1)})
      0.75
      >>> supportScalar({'wght':2.5, 'wdth':.5}, {'wght':(0,2,4), 'wdth':(-1,0,+1)})
      0.75
      >>> supportScalar({'wght':3}, {'wght':(0,1,2)}, extrapolate=True, axisRanges={'wght':(0, 2)})
      -1.0
      >>> supportScalar({'wght':-1}, {'wght':(0,1,2)}, extrapolate=True, axisRanges={'wght':(0, 2)})
      -1.0
      >>> supportScalar({'wght':3}, {'wght':(0,2,2)}, extrapolate=True, axisRanges={'wght':(0, 2)})
      1.5
      >>> supportScalar({'wght':-1}, {'wght':(0,2,2)}, extrapolate=True, axisRanges={'wght':(0, 2)})
      -0.5
    """
    if extrapolate and axisRanges is None:
        raise TypeError("axisRanges must be passed when extrapolate is True")
    scalar = 1.0
    for axis, (lower, peak, upper) in support.items():
        if ot:
            # OpenType-specific case handling
            if peak == 0.0:
                continue
            if lower > peak or peak > upper:
                continue
            if lower < 0.0 and upper > 0.0:
                continue
            v = location.get(axis, 0.0)
        else:
            assert axis in location
            v = location[axis]
        if v == peak:
            continue

        if extrapolate:
            axisMin, axisMax = axisRanges[axis]
            if v < axisMin and lower <= axisMin:
                if peak <= axisMin and peak < upper:
                    scalar *= (v - upper) / (peak - upper)
                    continue
                elif axisMin < peak:
                    scalar *= (v - lower) / (peak - lower)
                    continue
            elif axisMax < v and axisMax <= upper:
                if axisMax <= peak and lower < peak:
                    scalar *= (v - lower) / (peak - lower)
                    continue
                elif peak < axisMax:
                    scalar *= (v - upper) / (peak - upper)
                    continue

        if v <= lower or upper <= v:
            scalar = 0.0
            break

        if v < peak:
            scalar *= (v - lower) / (peak - lower)
        else:  # v > peak
            scalar *= (v - upper) / (peak - upper)
    return scalar


class VariationModel(object):
    """Locations must have the base master at the origin (ie. 0).

    If axis-ranges are not provided, values are assumed to be normalized to
    the range [-1, 1].

    If the extrapolate argument is set to True, then values are extrapolated
    outside the axis range.

      >>> from pprint import pprint
      >>> axisRanges = {'wght': (-180, +180), 'wdth': (-1, +1)}
      >>> locations = [ \
      {'wght':100}, \
      {'wght':-100}, \
      {'wght':-180}, \
      {'wdth':+.3}, \
      {'wght':+120,'wdth':.3}, \
      {'wght':+120,'wdth':.2}, \
      {}, \
      {'wght':+180,'wdth':.3}, \
      {'wght':+180}, \
      ]
      >>> model = VariationModel(locations, axisOrder=['wght'], axisRanges=axisRanges)
      >>> pprint(model.locations)
      [{},
       {'wght': -100},
       {'wght': -180},
       {'wght': 100},
       {'wght': 180},
       {'wdth': 0.3},
       {'wdth': 0.3, 'wght': 180},
       {'wdth': 0.3, 'wght': 120},
       {'wdth': 0.2, 'wght': 120}]
      >>> pprint(model.deltaWeights)
      [{},
       {0: 1.0},
       {0: 1.0},
       {0: 1.0},
       {0: 1.0},
       {0: 1.0},
       {0: 1.0, 4: 1.0, 5: 1.0},
       {0: 1.0, 3: 0.75, 4: 0.25, 5: 1.0, 6: 0.6666666666666666},
       {0: 1.0,
        3: 0.75,
        4: 0.25,
        5: 0.6666666666666667,
        6: 0.4444444444444445,
        7: 0.6666666666666667}]
    """

    def __init__(
        self, locations, axisOrder=None, extrapolate=False, *, axisRanges=None
    ):
        if len(set(tuple(sorted(l.items())) for l in locations)) != len(locations):
            raise VariationModelError("Locations must be unique.")

        self.origLocations = locations
        self.axisOrder = axisOrder if axisOrder is not None else []
        self.extrapolate = extrapolate
        if axisRanges is None:
            if extrapolate:
                axisRanges = self.computeAxisRanges(locations)
            else:
                allAxes = {axis for loc in locations for axis in loc.keys()}
                axisRanges = {axis: (-1, 1) for axis in allAxes}
        self.axisRanges = axisRanges

        locations = [{k: v for k, v in loc.items() if v != 0.0} for loc in locations]
        keyFunc = self.getMasterLocationsSortKeyFunc(
            locations, axisOrder=self.axisOrder
        )
        self.locations = sorted(locations, key=keyFunc)

        # Mapping from user's master order to our master order
        self.mapping = [self.locations.index(l) for l in locations]
        self.reverseMapping = [locations.index(l) for l in self.locations]

        self._computeMasterSupports()
        self._subModels = {}

    def getSubModel(self, items):
        """Return a sub-model and the items that are not None.

        The sub-model is necessary for working with the subset
        of items when some are None.

        The sub-model is cached."""
        if None not in items:
            return self, items
        key = tuple(v is not None for v in items)
        subModel = self._subModels.get(key)
        if subModel is None:
            subModel = VariationModel(subList(key, self.origLocations), self.axisOrder)
            self._subModels[key] = subModel
        return subModel, subList(key, items)

    @staticmethod
    def computeAxisRanges(locations):
        axisRanges = {}
        allAxes = {axis for loc in locations for axis in loc.keys()}
        for loc in locations:
            for axis in allAxes:
                value = loc.get(axis, 0)
                axisMin, axisMax = axisRanges.get(axis, (value, value))
                axisRanges[axis] = min(value, axisMin), max(value, axisMax)
        return axisRanges

    @staticmethod
    def getMasterLocationsSortKeyFunc(locations, axisOrder=[]):
        if {} not in locations:
            raise VariationModelError("Base master not found.")
        axisPoints = {}
        for loc in locations:
            if len(loc) != 1:
                continue
            axis = next(iter(loc))
            value = loc[axis]
            if axis not in axisPoints:
                axisPoints[axis] = {0.0}
            assert (
                value not in axisPoints[axis]
            ), 'Value "%s" in axisPoints["%s"] -->  %s' % (value, axis, axisPoints)
            axisPoints[axis].add(value)

        def getKey(axisPoints, axisOrder):
            def sign(v):
                return -1 if v < 0 else +1 if v > 0 else 0

            def key(loc):
                rank = len(loc)
                onPointAxes = [
                    axis
                    for axis, value in loc.items()
                    if axis in axisPoints and value in axisPoints[axis]
                ]
                orderedAxes = [axis for axis in axisOrder if axis in loc]
                orderedAxes.extend(
                    [axis for axis in sorted(loc.keys()) if axis not in axisOrder]
                )
                return (
                    rank,  # First, order by increasing rank
                    -len(onPointAxes),  # Next, by decreasing number of onPoint axes
                    tuple(
                        axisOrder.index(axis) if axis in axisOrder else 0x10000
                        for axis in orderedAxes
                    ),  # Next, by known axes
                    tuple(orderedAxes),  # Next, by all axes
                    tuple(
                        sign(loc[axis]) for axis in orderedAxes
                    ),  # Next, by signs of axis values
                    tuple(
                        abs(loc[axis]) for axis in orderedAxes
                    ),  # Next, by absolute value of axis values
                )

            return key

        ret = getKey(axisPoints, axisOrder)
        return ret

    def reorderMasters(self, master_list, mapping):
        # For changing the master data order without
        # recomputing supports and deltaWeights.
        new_list = [master_list[idx] for idx in mapping]
        self.origLocations = [self.origLocations[idx] for idx in mapping]
        locations = [
            {k: v for k, v in loc.items() if v != 0.0} for loc in self.origLocations
        ]
        self.mapping = [self.locations.index(l) for l in locations]
        self.reverseMapping = [locations.index(l) for l in self.locations]
        self._subModels = {}
        return new_list

    def _computeMasterSupports(self):
        self.supports = []
        regions = self._locationsToRegions()
        for i, region in enumerate(regions):
            locAxes = set(region.keys())
            # Walk over previous masters now
            for prev_region in regions[:i]:
                # Master with different axes do not participte
                if set(prev_region.keys()) != locAxes:
                    continue
                # If it's NOT in the current box, it does not participate
                relevant = True
                for axis, (lower, peak, upper) in region.items():
                    if not (
                        prev_region[axis][1] == peak
                        or lower < prev_region[axis][1] < upper
                    ):
                        relevant = False
                        break
                if not relevant:
                    continue

                # Split the box for new master; split in whatever direction
                # that has largest range ratio.
                #
                # For symmetry, we actually cut across multiple axes
                # if they have the largest, equal, ratio.
                # https://github.com/fonttools/fonttools/commit/7ee81c8821671157968b097f3e55309a1faa511e#commitcomment-31054804

                bestAxes = {}
                bestRatio = -1
                for axis in prev_region.keys():
                    val = prev_region[axis][1]
                    assert axis in region
                    lower, locV, upper = region[axis]
                    newLower, newUpper = lower, upper
                    if val < locV:
                        newLower = val
                        ratio = (val - locV) / (lower - locV)
                    elif locV < val:
                        newUpper = val
                        ratio = (val - locV) / (upper - locV)
                    else:  # val == locV
                        # Can't split box in this direction.
                        continue
                    if ratio > bestRatio:
                        bestAxes = {}
                        bestRatio = ratio
                    if ratio == bestRatio:
                        bestAxes[axis] = (newLower, locV, newUpper)

                for axis, triple in bestAxes.items():
                    region[axis] = triple
            self.supports.append(region)
        self._computeDeltaWeights()

    def _locationsToRegions(self):
        locations = self.locations
        axisRanges = self.axisRanges

        regions = []
        for loc in locations:
            region = {}
            for axis, locV in loc.items():
                if locV > 0:
                    region[axis] = (0, locV, axisRanges[axis][1])
                else:
                    region[axis] = (axisRanges[axis][0], locV, 0)
            regions.append(region)
        return regions

    def _computeDeltaWeights(self):
        self.deltaWeights = []
        for i, loc in enumerate(self.locations):
            deltaWeight = {}
            # Walk over previous masters now, populate deltaWeight
            for j, support in enumerate(self.supports[:i]):
                scalar = supportScalar(loc, support)
                if scalar:
                    deltaWeight[j] = scalar
            self.deltaWeights.append(deltaWeight)

    def getDeltas(self, masterValues, *, round=noRound):
        assert len(masterValues) == len(self.deltaWeights), (
            len(masterValues),
            len(self.deltaWeights),
        )
        mapping = self.reverseMapping
        out = []
        for i, weights in enumerate(self.deltaWeights):
            delta = masterValues[mapping[i]]
            for j, weight in weights.items():
                if weight == 1:
                    delta -= out[j]
                else:
                    delta -= out[j] * weight
            out.append(round(delta))
        return out

    def getDeltasAndSupports(self, items, *, round=noRound):
        model, items = self.getSubModel(items)
        return model.getDeltas(items, round=round), model.supports

    def getScalars(self, loc):
        """Return scalars for each delta, for the given location.
        If interpolating many master-values at the same location,
        this function allows speed up by fetching the scalars once
        and using them with interpolateFromMastersAndScalars()."""
        return [
            supportScalar(
                loc, support, extrapolate=self.extrapolate, axisRanges=self.axisRanges
            )
            for support in self.supports
        ]

    def getMasterScalars(self, targetLocation):
        """Return multipliers for each master, for the given location.
        If interpolating many master-values at the same location,
        this function allows speed up by fetching the scalars once
        and using them with interpolateFromValuesAndScalars().

        Note that the scalars used in interpolateFromMastersAndScalars(),
        are *not* the same as the ones returned here. They are the result
        of getScalars()."""
        out = self.getScalars(targetLocation)
        for i, weights in reversed(list(enumerate(self.deltaWeights))):
            for j, weight in weights.items():
                out[j] -= out[i] * weight

        out = [out[self.mapping[i]] for i in range(len(out))]
        return out

    @staticmethod
    def interpolateFromValuesAndScalars(values, scalars):
        """Interpolate from values and scalars coefficients.

        If the values are master-values, then the scalars should be
        fetched from getMasterScalars().

        If the values are deltas, then the scalars should be fetched
        from getScalars(); in which case this is the same as
        interpolateFromDeltasAndScalars().
        """
        v = None
        assert len(values) == len(scalars)
        for value, scalar in zip(values, scalars):
            if not scalar:
                continue
            contribution = value * scalar
            if v is None:
                v = contribution
            else:
                v += contribution
        return v

    @staticmethod
    def interpolateFromDeltasAndScalars(deltas, scalars):
        """Interpolate from deltas and scalars fetched from getScalars()."""
        return VariationModel.interpolateFromValuesAndScalars(deltas, scalars)

    def interpolateFromDeltas(self, loc, deltas):
        """Interpolate from deltas, at location loc."""
        scalars = self.getScalars(loc)
        return self.interpolateFromDeltasAndScalars(deltas, scalars)

    def interpolateFromMasters(self, loc, masterValues, *, round=noRound):
        """Interpolate from master-values, at location loc."""
        scalars = self.getMasterScalars(loc)
        return self.interpolateFromValuesAndScalars(masterValues, scalars)

    def interpolateFromMastersAndScalars(self, masterValues, scalars, *, round=noRound):
        """Interpolate from master-values, and scalars fetched from
        getScalars(), which is useful when you want to interpolate
        multiple master-values with the same location."""
        deltas = self.getDeltas(masterValues, round=round)
        return self.interpolateFromDeltasAndScalars(deltas, scalars)


def piecewiseLinearMap(v, mapping):
    keys = mapping.keys()
    if not keys:
        return v
    if v in keys:
        return mapping[v]
    k = min(keys)
    if v < k:
        return v + mapping[k] - k
    k = max(keys)
    if v > k:
        return v + mapping[k] - k
    # Interpolate
    a = max(k for k in keys if k < v)
    b = min(k for k in keys if k > v)
    va = mapping[a]
    vb = mapping[b]
    return va + (vb - va) * (v - a) / (b - a)


def main(args=None):
    """Normalize locations on a given designspace"""
    from fontTools import configLogger
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools varLib.models",
        description=main.__doc__,
    )
    parser.add_argument(
        "--loglevel",
        metavar="LEVEL",
        default="INFO",
        help="Logging level (defaults to INFO)",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--designspace", metavar="DESIGNSPACE", type=str)
    group.add_argument(
        "-l",
        "--locations",
        metavar="LOCATION",
        nargs="+",
        help="Master locations as comma-separate coordinates. One must be all zeros.",
    )

    args = parser.parse_args(args)

    configLogger(level=args.loglevel)
    from pprint import pprint

    if args.designspace:
        from fontTools.designspaceLib import DesignSpaceDocument

        doc = DesignSpaceDocument()
        doc.read(args.designspace)
        locs = [s.location for s in doc.sources]
        print("Original locations:")
        pprint(locs)
        doc.normalize()
        print("Normalized locations:")
        locs = [s.location for s in doc.sources]
        pprint(locs)
    else:
        axes = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        locs = [
            dict(zip(axes, (float(v) for v in s.split(",")))) for s in args.locations
        ]

    model = VariationModel(locs)
    print("Sorted locations:")
    pprint(model.locations)
    print("Supports:")
    pprint(model.supports)


if __name__ == "__main__":
    import doctest, sys

    if len(sys.argv) > 1:
        sys.exit(main())

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\nltk\chunk\util.py ===
# Natural Language Toolkit: Chunk format conversions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

from nltk.metrics import accuracy as _accuracy
from nltk.tag.mapping import map_tag
from nltk.tag.util import str2tuple
from nltk.tree import Tree

##//////////////////////////////////////////////////////
## EVALUATION
##//////////////////////////////////////////////////////


def accuracy(chunker, gold):
    """
    Score the accuracy of the chunker against the gold standard.
    Strip the chunk information from the gold standard and rechunk it using
    the chunker, then compute the accuracy score.

    :type chunker: ChunkParserI
    :param chunker: The chunker being evaluated.
    :type gold: tree
    :param gold: The chunk structures to score the chunker on.
    :rtype: float
    """

    gold_tags = []
    test_tags = []
    for gold_tree in gold:
        test_tree = chunker.parse(gold_tree.flatten())
        gold_tags += tree2conlltags(gold_tree)
        test_tags += tree2conlltags(test_tree)

    #    print 'GOLD:', gold_tags[:50]
    #    print 'TEST:', test_tags[:50]
    return _accuracy(gold_tags, test_tags)


# Patched for increased performance by Yoav Goldberg <yoavg@cs.bgu.ac.il>, 2006-01-13
#  -- statistics are evaluated only on demand, instead of at every sentence evaluation
#
# SB: use nltk.metrics for precision/recall scoring?
#
class ChunkScore:
    """
    A utility class for scoring chunk parsers.  ``ChunkScore`` can
    evaluate a chunk parser's output, based on a number of statistics
    (precision, recall, f-measure, misssed chunks, incorrect chunks).
    It can also combine the scores from the parsing of multiple texts;
    this makes it significantly easier to evaluate a chunk parser that
    operates one sentence at a time.

    Texts are evaluated with the ``score`` method.  The results of
    evaluation can be accessed via a number of accessor methods, such
    as ``precision`` and ``f_measure``.  A typical use of the
    ``ChunkScore`` class is::

        >>> chunkscore = ChunkScore()           # doctest: +SKIP
        >>> for correct in correct_sentences:   # doctest: +SKIP
        ...     guess = chunkparser.parse(correct.leaves())   # doctest: +SKIP
        ...     chunkscore.score(correct, guess)              # doctest: +SKIP
        >>> print('F Measure:', chunkscore.f_measure())       # doctest: +SKIP
        F Measure: 0.823

    :ivar kwargs: Keyword arguments:

        - max_tp_examples: The maximum number actual examples of true
          positives to record.  This affects the ``correct`` member
          function: ``correct`` will not return more than this number
          of true positive examples.  This does *not* affect any of
          the numerical metrics (precision, recall, or f-measure)

        - max_fp_examples: The maximum number actual examples of false
          positives to record.  This affects the ``incorrect`` member
          function and the ``guessed`` member function: ``incorrect``
          will not return more than this number of examples, and
          ``guessed`` will not return more than this number of true
          positive examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)

        - max_fn_examples: The maximum number actual examples of false
          negatives to record.  This affects the ``missed`` member
          function and the ``correct`` member function: ``missed``
          will not return more than this number of examples, and
          ``correct`` will not return more than this number of true
          negative examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)

        - chunk_label: A regular expression indicating which chunks
          should be compared.  Defaults to ``'.*'`` (i.e., all chunks).

    :type _tp: list(Token)
    :ivar _tp: List of true positives
    :type _fp: list(Token)
    :ivar _fp: List of false positives
    :type _fn: list(Token)
    :ivar _fn: List of false negatives

    :type _tp_num: int
    :ivar _tp_num: Number of true positives
    :type _fp_num: int
    :ivar _fp_num: Number of false positives
    :type _fn_num: int
    :ivar _fn_num: Number of false negatives.
    """

    def __init__(self, **kwargs):
        self._correct = set()
        self._guessed = set()
        self._tp = set()
        self._fp = set()
        self._fn = set()
        self._max_tp = kwargs.get("max_tp_examples", 100)
        self._max_fp = kwargs.get("max_fp_examples", 100)
        self._max_fn = kwargs.get("max_fn_examples", 100)
        self._chunk_label = kwargs.get("chunk_label", ".*")
        self._tp_num = 0
        self._fp_num = 0
        self._fn_num = 0
        self._count = 0
        self._tags_correct = 0.0
        self._tags_total = 0.0

        self._measuresNeedUpdate = False

    def _updateMeasures(self):
        if self._measuresNeedUpdate:
            self._tp = self._guessed & self._correct
            self._fn = self._correct - self._guessed
            self._fp = self._guessed - self._correct
            self._tp_num = len(self._tp)
            self._fp_num = len(self._fp)
            self._fn_num = len(self._fn)
            self._measuresNeedUpdate = False

    def score(self, correct, guessed):
        """
        Given a correctly chunked sentence, score another chunked
        version of the same sentence.

        :type correct: chunk structure
        :param correct: The known-correct ("gold standard") chunked
            sentence.
        :type guessed: chunk structure
        :param guessed: The chunked sentence to be scored.
        """
        self._correct |= _chunksets(correct, self._count, self._chunk_label)
        self._guessed |= _chunksets(guessed, self._count, self._chunk_label)
        self._count += 1
        self._measuresNeedUpdate = True
        # Keep track of per-tag accuracy (if possible)
        try:
            correct_tags = tree2conlltags(correct)
            guessed_tags = tree2conlltags(guessed)
        except ValueError:
            # This exception case is for nested chunk structures,
            # where tree2conlltags will fail with a ValueError: "Tree
            # is too deeply nested to be printed in CoNLL format."
            correct_tags = guessed_tags = ()
        self._tags_total += len(correct_tags)
        self._tags_correct += sum(
            1 for (t, g) in zip(guessed_tags, correct_tags) if t == g
        )

    def accuracy(self):
        """
        Return the overall tag-based accuracy for all text that have
        been scored by this ``ChunkScore``, using the IOB (conll2000)
        tag encoding.

        :rtype: float
        """
        if self._tags_total == 0:
            return 1
        return self._tags_correct / self._tags_total

    def precision(self):
        """
        Return the overall precision for all texts that have been
        scored by this ``ChunkScore``.

        :rtype: float
        """
        self._updateMeasures()
        div = self._tp_num + self._fp_num
        if div == 0:
            return 0
        else:
            return self._tp_num / div

    def recall(self):
        """
        Return the overall recall for all texts that have been
        scored by this ``ChunkScore``.

        :rtype: float
        """
        self._updateMeasures()
        div = self._tp_num + self._fn_num
        if div == 0:
            return 0
        else:
            return self._tp_num / div

    def f_measure(self, alpha=0.5):
        """
        Return the overall F measure for all texts that have been
        scored by this ``ChunkScore``.

        :param alpha: the relative weighting of precision and recall.
            Larger alpha biases the score towards the precision value,
            while smaller alpha biases the score towards the recall
            value.  ``alpha`` should have a value in the range [0,1].
        :type alpha: float
        :rtype: float
        """
        self._updateMeasures()
        p = self.precision()
        r = self.recall()
        if p == 0 or r == 0:  # what if alpha is 0 or 1?
            return 0
        return 1 / (alpha / p + (1 - alpha) / r)

    def missed(self):
        """
        Return the chunks which were included in the
        correct chunk structures, but not in the guessed chunk
        structures, listed in input order.

        :rtype: list of chunks
        """
        self._updateMeasures()
        chunks = list(self._fn)
        return [c[1] for c in chunks]  # discard position information

    def incorrect(self):
        """
        Return the chunks which were included in the guessed chunk structures,
        but not in the correct chunk structures, listed in input order.

        :rtype: list of chunks
        """
        self._updateMeasures()
        chunks = list(self._fp)
        return [c[1] for c in chunks]  # discard position information

    def correct(self):
        """
        Return the chunks which were included in the correct
        chunk structures, listed in input order.

        :rtype: list of chunks
        """
        chunks = list(self._correct)
        return [c[1] for c in chunks]  # discard position information

    def guessed(self):
        """
        Return the chunks which were included in the guessed
        chunk structures, listed in input order.

        :rtype: list of chunks
        """
        chunks = list(self._guessed)
        return [c[1] for c in chunks]  # discard position information

    def __len__(self):
        self._updateMeasures()
        return self._tp_num + self._fn_num

    def __repr__(self):
        """
        Return a concise representation of this ``ChunkScoring``.

        :rtype: str
        """
        return "<ChunkScoring of " + repr(len(self)) + " chunks>"

    def __str__(self):
        """
        Return a verbose representation of this ``ChunkScoring``.
        This representation includes the precision, recall, and
        f-measure scores.  For other information about the score,
        use the accessor methods (e.g., ``missed()`` and ``incorrect()``).

        :rtype: str
        """
        return (
            "ChunkParse score:\n"
            + (f"    IOB Accuracy: {self.accuracy() * 100:5.1f}%%\n")
            + (f"    Precision:    {self.precision() * 100:5.1f}%%\n")
            + (f"    Recall:       {self.recall() * 100:5.1f}%%\n")
            + (f"    F-Measure:    {self.f_measure() * 100:5.1f}%%")
        )


# extract chunks, and assign unique id, the absolute position of
# the first word of the chunk
def _chunksets(t, count, chunk_label):
    pos = 0
    chunks = []
    for child in t:
        if isinstance(child, Tree):
            if re.match(chunk_label, child.label()):
                chunks.append(((count, pos), child.freeze()))
            pos += len(child.leaves())
        else:
            pos += 1
    return set(chunks)


def tagstr2tree(
    s, chunk_label="NP", root_label="S", sep="/", source_tagset=None, target_tagset=None
):
    """
    Divide a string of bracketted tagged text into
    chunks and unchunked tokens, and produce a Tree.
    Chunks are marked by square brackets (``[...]``).  Words are
    delimited by whitespace, and each word should have the form
    ``text/tag``.  Words that do not contain a slash are
    assigned a ``tag`` of None.

    :param s: The string to be converted
    :type s: str
    :param chunk_label: The label to use for chunk nodes
    :type chunk_label: str
    :param root_label: The label to use for the root of the tree
    :type root_label: str
    :rtype: Tree
    """

    WORD_OR_BRACKET = re.compile(r"\[|\]|[^\[\]\s]+")

    stack = [Tree(root_label, [])]
    for match in WORD_OR_BRACKET.finditer(s):
        text = match.group()
        if text[0] == "[":
            if len(stack) != 1:
                raise ValueError(f"Unexpected [ at char {match.start():d}")
            chunk = Tree(chunk_label, [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif text[0] == "]":
            if len(stack) != 2:
                raise ValueError(f"Unexpected ] at char {match.start():d}")
            stack.pop()
        else:
            if sep is None:
                stack[-1].append(text)
            else:
                word, tag = str2tuple(text, sep)
                if source_tagset and target_tagset:
                    tag = map_tag(source_tagset, target_tagset, tag)
                stack[-1].append((word, tag))

    if len(stack) != 1:
        raise ValueError(f"Expected ] at char {len(s):d}")
    return stack[0]


### CONLL

_LINE_RE = re.compile(r"(\S+)\s+(\S+)\s+([IOB])-?(\S+)?")


def conllstr2tree(s, chunk_types=("NP", "PP", "VP"), root_label="S"):
    """
    Return a chunk structure for a single sentence
    encoded in the given CONLL 2000 style string.
    This function converts a CoNLL IOB string into a tree.
    It uses the specified chunk types
    (defaults to NP, PP and VP), and creates a tree rooted at a node
    labeled S (by default).

    :param s: The CoNLL string to be converted.
    :type s: str
    :param chunk_types: The chunk types to be converted.
    :type chunk_types: tuple
    :param root_label: The node label to use for the root.
    :type root_label: str
    :rtype: Tree
    """

    stack = [Tree(root_label, [])]

    for lineno, line in enumerate(s.split("\n")):
        if not line.strip():
            continue

        # Decode the line.
        match = _LINE_RE.match(line)
        if match is None:
            raise ValueError(f"Error on line {lineno:d}")
        (word, tag, state, chunk_type) = match.groups()

        # If it's a chunk type we don't care about, treat it as O.
        if chunk_types is not None and chunk_type not in chunk_types:
            state = "O"

        # For "Begin"/"Outside", finish any completed chunks -
        # also do so for "Inside" which don't match the previous token.
        mismatch_I = state == "I" and chunk_type != stack[-1].label()
        if state in "BO" or mismatch_I:
            if len(stack) == 2:
                stack.pop()

        # For "Begin", start a new chunk.
        if state == "B" or mismatch_I:
            chunk = Tree(chunk_type, [])
            stack[-1].append(chunk)
            stack.append(chunk)

        # Add the new word token.
        stack[-1].append((word, tag))

    return stack[0]


def tree2conlltags(t):
    """
    Return a list of 3-tuples containing ``(word, tag, IOB-tag)``.
    Convert a tree to the CoNLL IOB tag format.

    :param t: The tree to be converted.
    :type t: Tree
    :rtype: list(tuple)
    """

    tags = []
    for child in t:
        try:
            category = child.label()
            prefix = "B-"
            for contents in child:
                if isinstance(contents, Tree):
                    raise ValueError(
                        "Tree is too deeply nested to be printed in CoNLL format"
                    )
                tags.append((contents[0], contents[1], prefix + category))
                prefix = "I-"
        except AttributeError:
            tags.append((child[0], child[1], "O"))
    return tags


def conlltags2tree(
    sentence, chunk_types=("NP", "PP", "VP"), root_label="S", strict=False
):
    """
    Convert the CoNLL IOB format to a tree.
    """
    tree = Tree(root_label, [])
    for word, postag, chunktag in sentence:
        if chunktag is None:
            if strict:
                raise ValueError("Bad conll tag sequence")
            else:
                # Treat as O
                tree.append((word, postag))
        elif chunktag.startswith("B-"):
            tree.append(Tree(chunktag[2:], [(word, postag)]))
        elif chunktag.startswith("I-"):
            if (
                len(tree) == 0
                or not isinstance(tree[-1], Tree)
                or tree[-1].label() != chunktag[2:]
            ):
                if strict:
                    raise ValueError("Bad conll tag sequence")
                else:
                    # Treat as B-*
                    tree.append(Tree(chunktag[2:], [(word, postag)]))
            else:
                tree[-1].append((word, postag))
        elif chunktag == "O":
            tree.append((word, postag))
        else:
            raise ValueError(f"Bad conll tag {chunktag!r}")
    return tree


def tree2conllstr(t):
    """
    Return a multiline string where each line contains a word, tag and IOB tag.
    Convert a tree to the CoNLL IOB string format

    :param t: The tree to be converted.
    :type t: Tree
    :rtype: str
    """
    lines = [" ".join(token) for token in tree2conlltags(t)]
    return "\n".join(lines)


### IEER

_IEER_DOC_RE = re.compile(
    r"<DOC>\s*"
    r"(<DOCNO>\s*(?P<docno>.+?)\s*</DOCNO>\s*)?"
    r"(<DOCTYPE>\s*(?P<doctype>.+?)\s*</DOCTYPE>\s*)?"
    r"(<DATE_TIME>\s*(?P<date_time>.+?)\s*</DATE_TIME>\s*)?"
    r"<BODY>\s*"
    r"(<HEADLINE>\s*(?P<headline>.+?)\s*</HEADLINE>\s*)?"
    r"<TEXT>(?P<text>.*?)</TEXT>\s*"
    r"</BODY>\s*</DOC>\s*",
    re.DOTALL,
)

_IEER_TYPE_RE = re.compile(r'<b_\w+\s+[^>]*?type="(?P<type>\w+)"')


def _ieer_read_text(s, root_label):
    stack = [Tree(root_label, [])]
    # s will be None if there is no headline in the text
    # return the empty list in place of a Tree
    if s is None:
        return []
    for piece_m in re.finditer(r"<[^>]+>|[^\s<]+", s):
        piece = piece_m.group()
        try:
            if piece.startswith("<b_"):
                m = _IEER_TYPE_RE.match(piece)
                if m is None:
                    print("XXXX", piece)
                chunk = Tree(m.group("type"), [])
                stack[-1].append(chunk)
                stack.append(chunk)
            elif piece.startswith("<e_"):
                stack.pop()
            #           elif piece.startswith('<'):
            #               print "ERROR:", piece
            #               raise ValueError # Unexpected HTML
            else:
                stack[-1].append(piece)
        except (IndexError, ValueError) as e:
            raise ValueError(
                f"Bad IEER string (error at character {piece_m.start():d})"
            ) from e
    if len(stack) != 1:
        raise ValueError("Bad IEER string")
    return stack[0]


def ieerstr2tree(
    s,
    chunk_types=[
        "LOCATION",
        "ORGANIZATION",
        "PERSON",
        "DURATION",
        "DATE",
        "CARDINAL",
        "PERCENT",
        "MONEY",
        "MEASURE",
    ],
    root_label="S",
):
    """
    Return a chunk structure containing the chunked tagged text that is
    encoded in the given IEER style string.
    Convert a string of chunked tagged text in the IEER named
    entity format into a chunk structure.  Chunks are of several
    types, LOCATION, ORGANIZATION, PERSON, DURATION, DATE, CARDINAL,
    PERCENT, MONEY, and MEASURE.

    :rtype: Tree
    """

    # Try looking for a single document.  If that doesn't work, then just
    # treat everything as if it was within the <TEXT>...</TEXT>.
    m = _IEER_DOC_RE.match(s)
    if m:
        return {
            "text": _ieer_read_text(m.group("text"), root_label),
            "docno": m.group("docno"),
            "doctype": m.group("doctype"),
            "date_time": m.group("date_time"),
            #'headline': m.group('headline')
            # we want to capture NEs in the headline too!
            "headline": _ieer_read_text(m.group("headline"), root_label),
        }
    else:
        return _ieer_read_text(s, root_label)


def demo():
    s = "[ Pierre/NNP Vinken/NNP ] ,/, [ 61/CD years/NNS ] old/JJ ,/, will/MD join/VB [ the/DT board/NN ] ./."
    import nltk

    t = nltk.chunk.tagstr2tree(s, chunk_label="NP")
    t.pprint()
    print()

    s = """
These DT B-NP
research NN I-NP
protocols NNS I-NP
offer VBP B-VP
to TO B-PP
the DT B-NP
patient NN I-NP
not RB O
only RB O
the DT B-NP
very RB I-NP
best JJS I-NP
therapy NN I-NP
which WDT B-NP
we PRP B-NP
have VBP B-VP
established VBN I-VP
today NN B-NP
but CC B-NP
also RB I-NP
the DT B-NP
hope NN I-NP
of IN B-PP
something NN B-NP
still RB B-ADJP
better JJR I-ADJP
. . O
"""

    conll_tree = conllstr2tree(s, chunk_types=("NP", "PP"))
    conll_tree.pprint()

    # Demonstrate CoNLL output
    print("CoNLL output:")
    print(nltk.chunk.tree2conllstr(conll_tree))
    print()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\httpx\_urls.py ===
from __future__ import annotations

import typing
from urllib.parse import parse_qs, unquote, urlencode

import idna

from ._types import QueryParamTypes
from ._urlparse import urlparse
from ._utils import primitive_value_to_str

__all__ = ["URL", "QueryParams"]


class URL:
    """
    url = httpx.URL("HTTPS://jo%40email.com:a%20secret@müller.de:1234/pa%20th?search=ab#anchorlink")

    assert url.scheme == "https"
    assert url.username == "jo@email.com"
    assert url.password == "a secret"
    assert url.userinfo == b"jo%40email.com:a%20secret"
    assert url.host == "müller.de"
    assert url.raw_host == b"xn--mller-kva.de"
    assert url.port == 1234
    assert url.netloc == b"xn--mller-kva.de:1234"
    assert url.path == "/pa th"
    assert url.query == b"?search=ab"
    assert url.raw_path == b"/pa%20th?search=ab"
    assert url.fragment == "anchorlink"

    The components of a URL are broken down like this:

       https://jo%40email.com:a%20secret@müller.de:1234/pa%20th?search=ab#anchorlink
    [scheme]   [  username  ] [password] [ host ][port][ path ] [ query ] [fragment]
               [       userinfo        ] [   netloc   ][    raw_path    ]

    Note that:

    * `url.scheme` is normalized to always be lowercased.

    * `url.host` is normalized to always be lowercased. Internationalized domain
      names are represented in unicode, without IDNA encoding applied. For instance:

      url = httpx.URL("http://中国.icom.museum")
      assert url.host == "中国.icom.museum"
      url = httpx.URL("http://xn--fiqs8s.icom.museum")
      assert url.host == "中国.icom.museum"

    * `url.raw_host` is normalized to always be lowercased, and is IDNA encoded.

      url = httpx.URL("http://中国.icom.museum")
      assert url.raw_host == b"xn--fiqs8s.icom.museum"
      url = httpx.URL("http://xn--fiqs8s.icom.museum")
      assert url.raw_host == b"xn--fiqs8s.icom.museum"

    * `url.port` is either None or an integer. URLs that include the default port for
      "http", "https", "ws", "wss", and "ftp" schemes have their port
      normalized to `None`.

      assert httpx.URL("http://example.com") == httpx.URL("http://example.com:80")
      assert httpx.URL("http://example.com").port is None
      assert httpx.URL("http://example.com:80").port is None

    * `url.userinfo` is raw bytes, without URL escaping. Usually you'll want to work
      with `url.username` and `url.password` instead, which handle the URL escaping.

    * `url.raw_path` is raw bytes of both the path and query, without URL escaping.
      This portion is used as the target when constructing HTTP requests. Usually you'll
      want to work with `url.path` instead.

    * `url.query` is raw bytes, without URL escaping. A URL query string portion can
      only be properly URL escaped when decoding the parameter names and values
      themselves.
    """

    def __init__(self, url: URL | str = "", **kwargs: typing.Any) -> None:
        if kwargs:
            allowed = {
                "scheme": str,
                "username": str,
                "password": str,
                "userinfo": bytes,
                "host": str,
                "port": int,
                "netloc": bytes,
                "path": str,
                "query": bytes,
                "raw_path": bytes,
                "fragment": str,
                "params": object,
            }

            # Perform type checking for all supported keyword arguments.
            for key, value in kwargs.items():
                if key not in allowed:
                    message = f"{key!r} is an invalid keyword argument for URL()"
                    raise TypeError(message)
                if value is not None and not isinstance(value, allowed[key]):
                    expected = allowed[key].__name__
                    seen = type(value).__name__
                    message = f"Argument {key!r} must be {expected} but got {seen}"
                    raise TypeError(message)
                if isinstance(value, bytes):
                    kwargs[key] = value.decode("ascii")

            if "params" in kwargs:
                # Replace any "params" keyword with the raw "query" instead.
                #
                # Ensure that empty params use `kwargs["query"] = None` rather
                # than `kwargs["query"] = ""`, so that generated URLs do not
                # include an empty trailing "?".
                params = kwargs.pop("params")
                kwargs["query"] = None if not params else str(QueryParams(params))

        if isinstance(url, str):
            self._uri_reference = urlparse(url, **kwargs)
        elif isinstance(url, URL):
            self._uri_reference = url._uri_reference.copy_with(**kwargs)
        else:
            raise TypeError(
                "Invalid type for url.  Expected str or httpx.URL,"
                f" got {type(url)}: {url!r}"
            )

    @property
    def scheme(self) -> str:
        """
        The URL scheme, such as "http", "https".
        Always normalised to lowercase.
        """
        return self._uri_reference.scheme

    @property
    def raw_scheme(self) -> bytes:
        """
        The raw bytes representation of the URL scheme, such as b"http", b"https".
        Always normalised to lowercase.
        """
        return self._uri_reference.scheme.encode("ascii")

    @property
    def userinfo(self) -> bytes:
        """
        The URL userinfo as a raw bytestring.
        For example: b"jo%40email.com:a%20secret".
        """
        return self._uri_reference.userinfo.encode("ascii")

    @property
    def username(self) -> str:
        """
        The URL username as a string, with URL decoding applied.
        For example: "jo@email.com"
        """
        userinfo = self._uri_reference.userinfo
        return unquote(userinfo.partition(":")[0])

    @property
    def password(self) -> str:
        """
        The URL password as a string, with URL decoding applied.
        For example: "a secret"
        """
        userinfo = self._uri_reference.userinfo
        return unquote(userinfo.partition(":")[2])

    @property
    def host(self) -> str:
        """
        The URL host as a string.
        Always normalized to lowercase, with IDNA hosts decoded into unicode.

        Examples:

        url = httpx.URL("http://www.EXAMPLE.org")
        assert url.host == "www.example.org"

        url = httpx.URL("http://中国.icom.museum")
        assert url.host == "中国.icom.museum"

        url = httpx.URL("http://xn--fiqs8s.icom.museum")
        assert url.host == "中国.icom.museum"

        url = httpx.URL("https://[::ffff:192.168.0.1]")
        assert url.host == "::ffff:192.168.0.1"
        """
        host: str = self._uri_reference.host

        if host.startswith("xn--"):
            host = idna.decode(host)

        return host

    @property
    def raw_host(self) -> bytes:
        """
        The raw bytes representation of the URL host.
        Always normalized to lowercase, and IDNA encoded.

        Examples:

        url = httpx.URL("http://www.EXAMPLE.org")
        assert url.raw_host == b"www.example.org"

        url = httpx.URL("http://中国.icom.museum")
        assert url.raw_host == b"xn--fiqs8s.icom.museum"

        url = httpx.URL("http://xn--fiqs8s.icom.museum")
        assert url.raw_host == b"xn--fiqs8s.icom.museum"

        url = httpx.URL("https://[::ffff:192.168.0.1]")
        assert url.raw_host == b"::ffff:192.168.0.1"
        """
        return self._uri_reference.host.encode("ascii")

    @property
    def port(self) -> int | None:
        """
        The URL port as an integer.

        Note that the URL class performs port normalization as per the WHATWG spec.
        Default ports for "http", "https", "ws", "wss", and "ftp" schemes are always
        treated as `None`.

        For example:

        assert httpx.URL("http://www.example.com") == httpx.URL("http://www.example.com:80")
        assert httpx.URL("http://www.example.com:80").port is None
        """
        return self._uri_reference.port

    @property
    def netloc(self) -> bytes:
        """
        Either `<host>` or `<host>:<port>` as bytes.
        Always normalized to lowercase, and IDNA encoded.

        This property may be used for generating the value of a request
        "Host" header.
        """
        return self._uri_reference.netloc.encode("ascii")

    @property
    def path(self) -> str:
        """
        The URL path as a string. Excluding the query string, and URL decoded.

        For example:

        url = httpx.URL("https://example.com/pa%20th")
        assert url.path == "/pa th"
        """
        path = self._uri_reference.path or "/"
        return unquote(path)

    @property
    def query(self) -> bytes:
        """
        The URL query string, as raw bytes, excluding the leading b"?".

        This is necessarily a bytewise interface, because we cannot
        perform URL decoding of this representation until we've parsed
        the keys and values into a QueryParams instance.

        For example:

        url = httpx.URL("https://example.com/?filter=some%20search%20terms")
        assert url.query == b"filter=some%20search%20terms"
        """
        query = self._uri_reference.query or ""
        return query.encode("ascii")

    @property
    def params(self) -> QueryParams:
        """
        The URL query parameters, neatly parsed and packaged into an immutable
        multidict representation.
        """
        return QueryParams(self._uri_reference.query)

    @property
    def raw_path(self) -> bytes:
        """
        The complete URL path and query string as raw bytes.
        Used as the target when constructing HTTP requests.

        For example:

        GET /users?search=some%20text HTTP/1.1
        Host: www.example.org
        Connection: close
        """
        path = self._uri_reference.path or "/"
        if self._uri_reference.query is not None:
            path += "?" + self._uri_reference.query
        return path.encode("ascii")

    @property
    def fragment(self) -> str:
        """
        The URL fragments, as used in HTML anchors.
        As a string, without the leading '#'.
        """
        return unquote(self._uri_reference.fragment or "")

    @property
    def is_absolute_url(self) -> bool:
        """
        Return `True` for absolute URLs such as 'http://example.com/path',
        and `False` for relative URLs such as '/path'.
        """
        # We don't use `.is_absolute` from `rfc3986` because it treats
        # URLs with a fragment portion as not absolute.
        # What we actually care about is if the URL provides
        # a scheme and hostname to which connections should be made.
        return bool(self._uri_reference.scheme and self._uri_reference.host)

    @property
    def is_relative_url(self) -> bool:
        """
        Return `False` for absolute URLs such as 'http://example.com/path',
        and `True` for relative URLs such as '/path'.
        """
        return not self.is_absolute_url

    def copy_with(self, **kwargs: typing.Any) -> URL:
        """
        Copy this URL, returning a new URL with some components altered.
        Accepts the same set of parameters as the components that are made
        available via properties on the `URL` class.

        For example:

        url = httpx.URL("https://www.example.com").copy_with(
            username="jo@gmail.com", password="a secret"
        )
        assert url == "https://jo%40email.com:a%20secret@www.example.com"
        """
        return URL(self, **kwargs)

    def copy_set_param(self, key: str, value: typing.Any = None) -> URL:
        return self.copy_with(params=self.params.set(key, value))

    def copy_add_param(self, key: str, value: typing.Any = None) -> URL:
        return self.copy_with(params=self.params.add(key, value))

    def copy_remove_param(self, key: str) -> URL:
        return self.copy_with(params=self.params.remove(key))

    def copy_merge_params(self, params: QueryParamTypes) -> URL:
        return self.copy_with(params=self.params.merge(params))

    def join(self, url: URL | str) -> URL:
        """
        Return an absolute URL, using this URL as the base.

        Eg.

        url = httpx.URL("https://www.example.com/test")
        url = url.join("/new/path")
        assert url == "https://www.example.com/new/path"
        """
        from urllib.parse import urljoin

        return URL(urljoin(str(self), str(URL(url))))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, (URL, str)) and str(self) == str(URL(other))

    def __str__(self) -> str:
        return str(self._uri_reference)

    def __repr__(self) -> str:
        scheme, userinfo, host, port, path, query, fragment = self._uri_reference

        if ":" in userinfo:
            # Mask any password component.
            userinfo = f'{userinfo.split(":")[0]}:[secure]'

        authority = "".join(
            [
                f"{userinfo}@" if userinfo else "",
                f"[{host}]" if ":" in host else host,
                f":{port}" if port is not None else "",
            ]
        )
        url = "".join(
            [
                f"{self.scheme}:" if scheme else "",
                f"//{authority}" if authority else "",
                path,
                f"?{query}" if query is not None else "",
                f"#{fragment}" if fragment is not None else "",
            ]
        )

        return f"{self.__class__.__name__}({url!r})"

    @property
    def raw(self) -> tuple[bytes, bytes, int, bytes]:  # pragma: nocover
        import collections
        import warnings

        warnings.warn("URL.raw is deprecated.")
        RawURL = collections.namedtuple(
            "RawURL", ["raw_scheme", "raw_host", "port", "raw_path"]
        )
        return RawURL(
            raw_scheme=self.raw_scheme,
            raw_host=self.raw_host,
            port=self.port,
            raw_path=self.raw_path,
        )


class QueryParams(typing.Mapping[str, str]):
    """
    URL query parameters, as a multi-dict.
    """

    def __init__(self, *args: QueryParamTypes | None, **kwargs: typing.Any) -> None:
        assert len(args) < 2, "Too many arguments."
        assert not (args and kwargs), "Cannot mix named and unnamed arguments."

        value = args[0] if args else kwargs

        if value is None or isinstance(value, (str, bytes)):
            value = value.decode("ascii") if isinstance(value, bytes) else value
            self._dict = parse_qs(value, keep_blank_values=True)
        elif isinstance(value, QueryParams):
            self._dict = {k: list(v) for k, v in value._dict.items()}
        else:
            dict_value: dict[typing.Any, list[typing.Any]] = {}
            if isinstance(value, (list, tuple)):
                # Convert list inputs like:
                #     [("a", "123"), ("a", "456"), ("b", "789")]
                # To a dict representation, like:
                #     {"a": ["123", "456"], "b": ["789"]}
                for item in value:
                    dict_value.setdefault(item[0], []).append(item[1])
            else:
                # Convert dict inputs like:
                #    {"a": "123", "b": ["456", "789"]}
                # To dict inputs where values are always lists, like:
                #    {"a": ["123"], "b": ["456", "789"]}
                dict_value = {
                    k: list(v) if isinstance(v, (list, tuple)) else [v]
                    for k, v in value.items()
                }

            # Ensure that keys and values are neatly coerced to strings.
            # We coerce values `True` and `False` to JSON-like "true" and "false"
            # representations, and coerce `None` values to the empty string.
            self._dict = {
                str(k): [primitive_value_to_str(item) for item in v]
                for k, v in dict_value.items()
            }

    def keys(self) -> typing.KeysView[str]:
        """
        Return all the keys in the query params.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.keys()) == ["a", "b"]
        """
        return self._dict.keys()

    def values(self) -> typing.ValuesView[str]:
        """
        Return all the values in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.values()) == ["123", "789"]
        """
        return {k: v[0] for k, v in self._dict.items()}.values()

    def items(self) -> typing.ItemsView[str, str]:
        """
        Return all items in the query params. If a key occurs more than once
        only the first item for that key is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.items()) == [("a", "123"), ("b", "789")]
        """
        return {k: v[0] for k, v in self._dict.items()}.items()

    def multi_items(self) -> list[tuple[str, str]]:
        """
        Return all items in the query params. Allow duplicate keys to occur.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert list(q.multi_items()) == [("a", "123"), ("a", "456"), ("b", "789")]
        """
        multi_items: list[tuple[str, str]] = []
        for k, v in self._dict.items():
            multi_items.extend([(k, i) for i in v])
        return multi_items

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        """
        Get a value from the query param for a given key. If the key occurs
        more than once, then only the first value is returned.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get("a") == "123"
        """
        if key in self._dict:
            return self._dict[str(key)][0]
        return default

    def get_list(self, key: str) -> list[str]:
        """
        Get all values from the query param for a given key.

        Usage:

        q = httpx.QueryParams("a=123&a=456&b=789")
        assert q.get_list("a") == ["123", "456"]
        """
        return list(self._dict.get(str(key), []))

    def set(self, key: str, value: typing.Any = None) -> QueryParams:
        """
        Return a new QueryParams instance, setting the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.set("a", "456")
        assert q == httpx.QueryParams("a=456")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict[str(key)] = [primitive_value_to_str(value)]
        return q

    def add(self, key: str, value: typing.Any = None) -> QueryParams:
        """
        Return a new QueryParams instance, setting or appending the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.add("a", "456")
        assert q == httpx.QueryParams("a=123&a=456")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict[str(key)] = q.get_list(key) + [primitive_value_to_str(value)]
        return q

    def remove(self, key: str) -> QueryParams:
        """
        Return a new QueryParams instance, removing the value of a key.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.remove("a")
        assert q == httpx.QueryParams("")
        """
        q = QueryParams()
        q._dict = dict(self._dict)
        q._dict.pop(str(key), None)
        return q

    def merge(self, params: QueryParamTypes | None = None) -> QueryParams:
        """
        Return a new QueryParams instance, updated with.

        Usage:

        q = httpx.QueryParams("a=123")
        q = q.merge({"b": "456"})
        assert q == httpx.QueryParams("a=123&b=456")

        q = httpx.QueryParams("a=123")
        q = q.merge({"a": "456", "b": "789"})
        assert q == httpx.QueryParams("a=456&b=789")
        """
        q = QueryParams(params)
        q._dict = {**self._dict, **q._dict}
        return q

    def __getitem__(self, key: typing.Any) -> str:
        return self._dict[key][0]

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._dict

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self.multi_items()) == sorted(other.multi_items())

    def __str__(self) -> str:
        return urlencode(self.multi_items())

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"

    def update(self, params: QueryParamTypes | None = None) -> None:
        raise RuntimeError(
            "QueryParams are immutable since 0.18.0. "
            "Use `q = q.merge(...)` to create an updated copy."
        )

    def __setitem__(self, key: str, value: str) -> None:
        raise RuntimeError(
            "QueryParams are immutable since 0.18.0. "
            "Use `q = q.set(key, value)` to create an updated copy."
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_console_utils.py ===
import os
import sys
import traceback
from _pydev_bundle.pydev_imports import xmlrpclib, _queue, Exec
from _pydev_bundle._pydev_calltip_util import get_description
from _pydevd_bundle import pydevd_vars
from _pydevd_bundle import pydevd_xml
from _pydevd_bundle.pydevd_constants import IS_JYTHON, NEXT_VALUE_SEPARATOR, get_global_debugger, silence_warnings_decorator
from contextlib import contextmanager
from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_utils import interrupt_main_thread

from io import StringIO


# =======================================================================================================================
# BaseStdIn
# =======================================================================================================================
class BaseStdIn:
    def __init__(self, original_stdin=sys.stdin, *args, **kwargs):
        try:
            self.encoding = sys.stdin.encoding
        except:
            # Not sure if it's available in all Python versions...
            pass
        self.original_stdin = original_stdin

        try:
            self.errors = sys.stdin.errors  # Who knew? sys streams have an errors attribute!
        except:
            # Not sure if it's available in all Python versions...
            pass

    def readline(self, *args, **kwargs):
        # sys.stderr.write('Cannot readline out of the console evaluation\n') -- don't show anything
        # This could happen if the user had done input('enter number).<-- upon entering this, that message would appear,
        # which is not something we want.
        return "\n"

    def write(self, *args, **kwargs):
        pass  # not available StdIn (but it can be expected to be in the stream interface)

    def flush(self, *args, **kwargs):
        pass  # not available StdIn (but it can be expected to be in the stream interface)

    def read(self, *args, **kwargs):
        # in the interactive interpreter, a read and a readline are the same.
        return self.readline()

    def close(self, *args, **kwargs):
        pass  # expected in StdIn

    def __iter__(self):
        # BaseStdIn would not be considered as Iterable in Python 3 without explicit `__iter__` implementation
        return self.original_stdin.__iter__()

    def __getattr__(self, item):
        # it's called if the attribute wasn't found
        if hasattr(self.original_stdin, item):
            return getattr(self.original_stdin, item)
        raise AttributeError("%s has no attribute %s" % (self.original_stdin, item))


# =======================================================================================================================
# StdIn
# =======================================================================================================================
class StdIn(BaseStdIn):
    """
    Object to be added to stdin (to emulate it as non-blocking while the next line arrives)
    """

    def __init__(self, interpreter, host, client_port, original_stdin=sys.stdin):
        BaseStdIn.__init__(self, original_stdin)
        self.interpreter = interpreter
        self.client_port = client_port
        self.host = host

    def readline(self, *args, **kwargs):
        # Ok, callback into the client to get the new input
        try:
            server = xmlrpclib.Server("http://%s:%s" % (self.host, self.client_port))
            requested_input = server.RequestInput()
            if not requested_input:
                return "\n"  # Yes, a readline must return something (otherwise we can get an EOFError on the input() call).
            else:
                # readline should end with '\n' (not doing so makes IPython 5 remove the last *valid* character).
                requested_input += "\n"
            return requested_input
        except KeyboardInterrupt:
            raise  # Let KeyboardInterrupt go through -- #PyDev-816: Interrupting infinite loop in the Interactive Console
        except:
            return "\n"

    def close(self, *args, **kwargs):
        pass  # expected in StdIn


# =======================================================================================================================
# DebugConsoleStdIn
# =======================================================================================================================
class DebugConsoleStdIn(BaseStdIn):
    """
    Object to be added to stdin (to emulate it as non-blocking while the next line arrives)
    """

    def __init__(self, py_db, original_stdin):
        """
        :param py_db:
            If None, get_global_debugger() is used.
        """
        BaseStdIn.__init__(self, original_stdin)
        self._py_db = py_db
        self._in_notification = 0

    def __send_input_requested_message(self, is_started):
        try:
            py_db = self._py_db
            if py_db is None:
                py_db = get_global_debugger()

            if py_db is None:
                return

            cmd = py_db.cmd_factory.make_input_requested_message(is_started)
            py_db.writer.add_command(cmd)
        except Exception:
            pydev_log.exception()

    @contextmanager
    def notify_input_requested(self):
        self._in_notification += 1
        if self._in_notification == 1:
            self.__send_input_requested_message(True)
        try:
            yield
        finally:
            self._in_notification -= 1
            if self._in_notification == 0:
                self.__send_input_requested_message(False)

    def readline(self, *args, **kwargs):
        with self.notify_input_requested():
            return self.original_stdin.readline(*args, **kwargs)

    def read(self, *args, **kwargs):
        with self.notify_input_requested():
            return self.original_stdin.read(*args, **kwargs)


class CodeFragment:
    def __init__(self, text, is_single_line=True):
        self.text = text
        self.is_single_line = is_single_line

    def append(self, code_fragment):
        self.text = self.text + "\n" + code_fragment.text
        if not code_fragment.is_single_line:
            self.is_single_line = False


# =======================================================================================================================
# BaseInterpreterInterface
# =======================================================================================================================
class BaseInterpreterInterface:
    def __init__(self, mainThread, connect_status_queue=None):
        self.mainThread = mainThread
        self.interruptable = False
        self.exec_queue = _queue.Queue(0)
        self.buffer = None
        self.banner_shown = False
        self.connect_status_queue = connect_status_queue
        self.mpl_modules_for_patching = {}
        self.init_mpl_modules_for_patching()

    def build_banner(self):
        return "print({0})\n".format(repr(self.get_greeting_msg()))

    def get_greeting_msg(self):
        return "PyDev console: starting.\n"

    def init_mpl_modules_for_patching(self):
        from pydev_ipython.matplotlibtools import activate_matplotlib, activate_pylab, activate_pyplot

        self.mpl_modules_for_patching = {
            "matplotlib": lambda: activate_matplotlib(self.enableGui),
            "matplotlib.pyplot": activate_pyplot,
            "pylab": activate_pylab,
        }

    def need_more_for_code(self, source):
        # PyDev-502: PyDev 3.9 F2 doesn't support backslash continuations

        # Strangely even the IPython console is_complete said it was complete
        # even with a continuation char at the end.
        if source.endswith("\\"):
            return True

        if hasattr(self.interpreter, "is_complete"):
            return not self.interpreter.is_complete(source)
        try:
            # At this point, it should always be single.
            # If we don't do this, things as:
            #
            #     for i in range(10): print(i)
            #
            # (in a single line) don't work.
            # Note that it won't give an error and code will be None (so, it'll
            # use execMultipleLines in the next call in this case).
            symbol = "single"
            code = self.interpreter.compile(source, "<input>", symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            return False
        if code is None:
            # Case 2
            return True

        # Case 3
        return False

    def need_more(self, code_fragment):
        if self.buffer is None:
            self.buffer = code_fragment
        else:
            self.buffer.append(code_fragment)

        return self.need_more_for_code(self.buffer.text)

    def create_std_in(self, debugger=None, original_std_in=None):
        if debugger is None:
            return StdIn(self, self.host, self.client_port, original_stdin=original_std_in)
        else:
            return DebugConsoleStdIn(py_db=debugger, original_stdin=original_std_in)

    def add_exec(self, code_fragment, debugger=None):
        # In case sys.excepthook called, use original excepthook #PyDev-877: Debug console freezes with Python 3.5+
        # (showtraceback does it on python 3.5 onwards)
        sys.excepthook = sys.__excepthook__
        try:
            original_in = sys.stdin
            try:
                help = None
                if "pydoc" in sys.modules:
                    pydoc = sys.modules["pydoc"]  # Don't import it if it still is not there.

                    if hasattr(pydoc, "help"):
                        # You never know how will the API be changed, so, let's code defensively here
                        help = pydoc.help
                        if not hasattr(help, "input"):
                            help = None
            except:
                # Just ignore any error here
                pass

            more = False
            try:
                sys.stdin = self.create_std_in(debugger, original_in)
                try:
                    if help is not None:
                        # This will enable the help() function to work.
                        try:
                            try:
                                help.input = sys.stdin
                            except AttributeError:
                                help._input = sys.stdin
                        except:
                            help = None
                            if not self._input_error_printed:
                                self._input_error_printed = True
                                sys.stderr.write("\nError when trying to update pydoc.help.input\n")
                                sys.stderr.write("(help() may not work -- please report this as a bug in the pydev bugtracker).\n\n")
                                traceback.print_exc()

                    try:
                        self.start_exec()
                        if hasattr(self, "debugger"):
                            self.debugger.enable_tracing()

                        more = self.do_add_exec(code_fragment)

                        if hasattr(self, "debugger"):
                            self.debugger.disable_tracing()

                        self.finish_exec(more)
                    finally:
                        if help is not None:
                            try:
                                try:
                                    help.input = original_in
                                except AttributeError:
                                    help._input = original_in
                            except:
                                pass

                finally:
                    sys.stdin = original_in
            except SystemExit:
                raise
            except:
                traceback.print_exc()
        finally:
            sys.__excepthook__ = sys.excepthook

        return more

    def do_add_exec(self, codeFragment):
        """
        Subclasses should override.

        @return: more (True if more input is needed to complete the statement and False if the statement is complete).
        """
        raise NotImplementedError()

    def get_namespace(self):
        """
        Subclasses should override.

        @return: dict with namespace.
        """
        raise NotImplementedError()

    def __resolve_reference__(self, text):
        """

        :type text: str
        """
        obj = None
        if "." not in text:
            try:
                obj = self.get_namespace()[text]
            except KeyError:
                pass

            if obj is None:
                try:
                    obj = self.get_namespace()["__builtins__"][text]
                except:
                    pass

            if obj is None:
                try:
                    obj = getattr(self.get_namespace()["__builtins__"], text, None)
                except:
                    pass

        else:
            try:
                last_dot = text.rindex(".")
                parent_context = text[0:last_dot]
                res = pydevd_vars.eval_in_context(parent_context, self.get_namespace(), self.get_namespace())
                obj = getattr(res, text[last_dot + 1 :])
            except:
                pass
        return obj

    def getDescription(self, text):
        try:
            obj = self.__resolve_reference__(text)
            if obj is None:
                return ""
            return get_description(obj)
        except:
            return ""

    def do_exec_code(self, code, is_single_line):
        try:
            code_fragment = CodeFragment(code, is_single_line)
            more = self.need_more(code_fragment)
            if not more:
                code_fragment = self.buffer
                self.buffer = None
                self.exec_queue.put(code_fragment)

            return more
        except:
            traceback.print_exc()
            return False

    def execLine(self, line):
        return self.do_exec_code(line, True)

    def execMultipleLines(self, lines):
        if IS_JYTHON:
            more = False
            for line in lines.split("\n"):
                more = self.do_exec_code(line, True)
            return more
        else:
            return self.do_exec_code(lines, False)

    def interrupt(self):
        self.buffer = None  # Also clear the buffer when it's interrupted.
        try:
            if self.interruptable:
                # Fix for #PyDev-500: Console interrupt can't interrupt on sleep
                interrupt_main_thread(self.mainThread)

            self.finish_exec(False)
            return True
        except:
            traceback.print_exc()
            return False

    def close(self):
        sys.exit(0)

    def start_exec(self):
        self.interruptable = True

    def get_server(self):
        if getattr(self, "host", None) is not None:
            return xmlrpclib.Server("http://%s:%s" % (self.host, self.client_port))
        else:
            return None

    server = property(get_server)

    def ShowConsole(self):
        server = self.get_server()
        if server is not None:
            server.ShowConsole()

    def finish_exec(self, more):
        self.interruptable = False

        server = self.get_server()

        if server is not None:
            return server.NotifyFinished(more)
        else:
            return True

    def getFrame(self):
        xml = StringIO()
        hidden_ns = self.get_ipython_hidden_vars_dict()
        xml.write("<xml>")
        xml.write(pydevd_xml.frame_vars_to_xml(self.get_namespace(), hidden_ns))
        xml.write("</xml>")

        return xml.getvalue()

    @silence_warnings_decorator
    def getVariable(self, attributes):
        xml = StringIO()
        xml.write("<xml>")
        val_dict = pydevd_vars.resolve_compound_var_object_fields(self.get_namespace(), attributes)
        if val_dict is None:
            val_dict = {}

        for k, val in val_dict.items():
            val = val_dict[k]
            evaluate_full_value = pydevd_xml.should_evaluate_full_value(val)
            xml.write(pydevd_vars.var_to_xml(val, k, evaluate_full_value=evaluate_full_value))

        xml.write("</xml>")

        return xml.getvalue()

    def getArray(self, attr, roffset, coffset, rows, cols, format):
        name = attr.split("\t")[-1]
        array = pydevd_vars.eval_in_context(name, self.get_namespace(), self.get_namespace())
        return pydevd_vars.table_like_struct_to_xml(array, name, roffset, coffset, rows, cols, format)

    def evaluate(self, expression):
        xml = StringIO()
        xml.write("<xml>")
        result = pydevd_vars.eval_in_context(expression, self.get_namespace(), self.get_namespace())
        xml.write(pydevd_vars.var_to_xml(result, expression))
        xml.write("</xml>")
        return xml.getvalue()

    @silence_warnings_decorator
    def loadFullValue(self, seq, scope_attrs):
        """
        Evaluate full value for async Console variables in a separate thread and send results to IDE side
        :param seq: id of command
        :param scope_attrs: a sequence of variables with their attributes separated by NEXT_VALUE_SEPARATOR
        (i.e.: obj\tattr1\tattr2NEXT_VALUE_SEPARATORobj2\attr1\tattr2)
        :return:
        """
        frame_variables = self.get_namespace()
        var_objects = []
        vars = scope_attrs.split(NEXT_VALUE_SEPARATOR)
        for var_attrs in vars:
            if "\t" in var_attrs:
                name, attrs = var_attrs.split("\t", 1)

            else:
                name = var_attrs
                attrs = None
            if name in frame_variables:
                var_object = pydevd_vars.resolve_var_object(frame_variables[name], attrs)
                var_objects.append((var_object, name))
            else:
                var_object = pydevd_vars.eval_in_context(name, frame_variables, frame_variables)
                var_objects.append((var_object, name))

        from _pydevd_bundle.pydevd_comm import GetValueAsyncThreadConsole

        py_db = getattr(self, "debugger", None)

        if py_db is None:
            py_db = get_global_debugger()

        if py_db is None:
            from pydevd import PyDB

            py_db = PyDB()

        t = GetValueAsyncThreadConsole(py_db, self.get_server(), seq, var_objects)
        t.start()

    def changeVariable(self, attr, value):
        def do_change_variable():
            Exec("%s=%s" % (attr, value), self.get_namespace(), self.get_namespace())

        # Important: it has to be really enabled in the main thread, so, schedule
        # it to run in the main thread.
        self.exec_queue.put(do_change_variable)

    def connectToDebugger(self, debuggerPort, debugger_options=None):
        """
        Used to show console with variables connection.
        Mainly, monkey-patches things in the debugger structure so that the debugger protocol works.
        """

        if debugger_options is None:
            debugger_options = {}
        env_key = "PYDEVD_EXTRA_ENVS"
        if env_key in debugger_options:
            for env_name, value in debugger_options[env_key].items():
                existing_value = os.environ.get(env_name, None)
                if existing_value:
                    os.environ[env_name] = "%s%c%s" % (existing_value, os.path.pathsep, value)
                else:
                    os.environ[env_name] = value
                if env_name == "PYTHONPATH":
                    sys.path.append(value)

            del debugger_options[env_key]

        def do_connect_to_debugger():
            try:
                # Try to import the packages needed to attach the debugger
                import pydevd
                from _pydev_bundle._pydev_saved_modules import threading
            except:
                # This happens on Jython embedded in host eclipse
                traceback.print_exc()
                sys.stderr.write("pydevd is not available, cannot connect\n")

            from _pydevd_bundle.pydevd_constants import set_thread_id
            from _pydev_bundle import pydev_localhost

            set_thread_id(threading.current_thread(), "console_main")

            VIRTUAL_FRAME_ID = "1"  # matches PyStackFrameConsole.java
            VIRTUAL_CONSOLE_ID = "console_main"  # matches PyThreadConsole.java
            f = FakeFrame()
            f.f_back = None
            f.f_globals = {}  # As globals=locals here, let's simply let it empty (and save a bit of network traffic).
            f.f_locals = self.get_namespace()

            self.debugger = pydevd.PyDB()
            self.debugger.add_fake_frame(thread_id=VIRTUAL_CONSOLE_ID, frame_id=VIRTUAL_FRAME_ID, frame=f)
            try:
                pydevd.apply_debugger_options(debugger_options)
                self.debugger.connect(pydev_localhost.get_localhost(), debuggerPort)
                self.debugger.prepare_to_run()
                self.debugger.disable_tracing()
            except:
                traceback.print_exc()
                sys.stderr.write("Failed to connect to target debugger.\n")

            # Register to process commands when idle
            self.debugrunning = False
            try:
                import pydevconsole

                pydevconsole.set_debug_hook(self.debugger.process_internal_commands)
            except:
                traceback.print_exc()
                sys.stderr.write("Version of Python does not support debuggable Interactive Console.\n")

        # Important: it has to be really enabled in the main thread, so, schedule
        # it to run in the main thread.
        self.exec_queue.put(do_connect_to_debugger)

        return ("connect complete",)

    def handshake(self):
        if self.connect_status_queue is not None:
            self.connect_status_queue.put(True)
        return "PyCharm"

    def get_connect_status_queue(self):
        return self.connect_status_queue

    def hello(self, input_str):
        # Don't care what the input string is
        return ("Hello eclipse",)

    def enableGui(self, guiname):
        """Enable the GUI specified in guiname (see inputhook for list).
        As with IPython, enabling multiple GUIs isn't an error, but
        only the last one's main loop runs and it may not work
        """

        def do_enable_gui():
            from _pydev_bundle.pydev_versioncheck import versionok_for_gui

            if versionok_for_gui():
                try:
                    from pydev_ipython.inputhook import enable_gui

                    enable_gui(guiname)
                except:
                    sys.stderr.write("Failed to enable GUI event loop integration for '%s'\n" % guiname)
                    traceback.print_exc()
            elif guiname not in ["none", "", None]:
                # Only print a warning if the guiname was going to do something
                sys.stderr.write("PyDev console: Python version does not support GUI event loop integration for '%s'\n" % guiname)
            # Return value does not matter, so return back what was sent
            return guiname

        # Important: it has to be really enabled in the main thread, so, schedule
        # it to run in the main thread.
        self.exec_queue.put(do_enable_gui)

    def get_ipython_hidden_vars_dict(self):
        return None


# =======================================================================================================================
# FakeFrame
# =======================================================================================================================
class FakeFrame:
    """
    Used to show console with variables connection.
    A class to be used as a mock of a frame.
    """

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_plugins\django_debug.py ===
import inspect

from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_comm import CMD_SET_BREAK, CMD_ADD_EXCEPTION_BREAK
from _pydevd_bundle.pydevd_constants import STATE_SUSPEND, DJANGO_SUSPEND, DebugInfoHolder
from _pydevd_bundle.pydevd_frame_utils import add_exception_to_frame, FCode, just_raised, ignore_exception_trace
from pydevd_file_utils import canonical_normalized_path, absolute_path
from _pydevd_bundle.pydevd_api import PyDevdAPI
from pydevd_plugins.pydevd_line_validation import LineBreakpointWithLazyValidation, ValidationInfo
from _pydev_bundle.pydev_override import overrides

IS_DJANGO18 = False
IS_DJANGO19 = False
IS_DJANGO19_OR_HIGHER = False
try:
    import django

    version = django.VERSION
    IS_DJANGO18 = version[0] == 1 and version[1] == 8
    IS_DJANGO19 = version[0] == 1 and version[1] == 9
    IS_DJANGO19_OR_HIGHER = (version[0] == 1 and version[1] >= 9) or version[0] > 1
except:
    pass


class DjangoLineBreakpoint(LineBreakpointWithLazyValidation):
    def __init__(
        self, canonical_normalized_filename, breakpoint_id, line, condition, func_name, expression, hit_condition=None, is_logpoint=False
    ):
        self.canonical_normalized_filename = canonical_normalized_filename
        LineBreakpointWithLazyValidation.__init__(
            self, breakpoint_id, line, condition, func_name, expression, hit_condition=hit_condition, is_logpoint=is_logpoint
        )

    def __str__(self):
        return "DjangoLineBreakpoint: %s-%d" % (self.canonical_normalized_filename, self.line)


class _DjangoValidationInfo(ValidationInfo):
    @overrides(ValidationInfo._collect_valid_lines_in_template_uncached)
    def _collect_valid_lines_in_template_uncached(self, template):
        lines = set()
        for node in self._iternodes(template.nodelist):
            if node.__class__.__name__ in _IGNORE_RENDER_OF_CLASSES:
                continue
            lineno = self._get_lineno(node)
            if lineno is not None:
                lines.add(lineno)
        return lines

    def _get_lineno(self, node):
        if hasattr(node, "token") and hasattr(node.token, "lineno"):
            return node.token.lineno
        return None

    def _iternodes(self, nodelist):
        for node in nodelist:
            yield node

            try:
                children = node.child_nodelists
            except:
                pass
            else:
                for attr in children:
                    nodelist = getattr(node, attr, None)
                    if nodelist:
                        # i.e.: yield from _iternodes(nodelist)
                        for node in self._iternodes(nodelist):
                            yield node


def add_line_breakpoint(
    pydb,
    type,
    canonical_normalized_filename,
    breakpoint_id,
    line,
    condition,
    expression,
    func_name,
    hit_condition=None,
    is_logpoint=False,
    add_breakpoint_result=None,
    on_changed_breakpoint_state=None,
):
    if type == "django-line":
        django_line_breakpoint = DjangoLineBreakpoint(
            canonical_normalized_filename,
            breakpoint_id,
            line,
            condition,
            func_name,
            expression,
            hit_condition=hit_condition,
            is_logpoint=is_logpoint,
        )
        if not hasattr(pydb, "django_breakpoints"):
            _init_plugin_breaks(pydb)

        if IS_DJANGO19_OR_HIGHER:
            add_breakpoint_result.error_code = PyDevdAPI.ADD_BREAKPOINT_LAZY_VALIDATION
            django_line_breakpoint.add_breakpoint_result = add_breakpoint_result
            django_line_breakpoint.on_changed_breakpoint_state = on_changed_breakpoint_state
        else:
            add_breakpoint_result.error_code = PyDevdAPI.ADD_BREAKPOINT_NO_ERROR

        return django_line_breakpoint, pydb.django_breakpoints
    return None


def after_breakpoints_consolidated(py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints):
    if IS_DJANGO19_OR_HIGHER:
        django_breakpoints_for_file = file_to_line_to_breakpoints.get(canonical_normalized_filename)
        if not django_breakpoints_for_file:
            return

        if not hasattr(py_db, "django_validation_info"):
            _init_plugin_breaks(py_db)

        # In general we validate the breakpoints only when the template is loaded, but if the template
        # was already loaded, we can validate the breakpoints based on the last loaded value.
        py_db.django_validation_info.verify_breakpoints_from_template_cached_lines(
            py_db, canonical_normalized_filename, django_breakpoints_for_file
        )


def add_exception_breakpoint(pydb, type, exception):
    if type == "django":
        if not hasattr(pydb, "django_exception_break"):
            _init_plugin_breaks(pydb)
        pydb.django_exception_break[exception] = True
        return True
    return False


def _init_plugin_breaks(pydb):
    pydb.django_exception_break = {}
    pydb.django_breakpoints = {}

    pydb.django_validation_info = _DjangoValidationInfo()


def remove_exception_breakpoint(pydb, exception_type, exception):
    if exception_type == "django":
        try:
            del pydb.django_exception_break[exception]
            return True
        except KeyError:
            pass
    return False


def remove_all_exception_breakpoints(pydb):
    if hasattr(pydb, "django_exception_break"):
        pydb.django_exception_break = {}
        return True
    return False


def get_breakpoints(pydb, breakpoint_type):
    if breakpoint_type == "django-line":
        return pydb.django_breakpoints
    return None


def _inherits(cls, *names):
    if cls.__name__ in names:
        return True
    inherits_node = False
    for base in inspect.getmro(cls):
        if base.__name__ in names:
            inherits_node = True
            break
    return inherits_node


_IGNORE_RENDER_OF_CLASSES = ("TextNode", "NodeList")


def _is_django_render_call(frame):
    try:
        name = frame.f_code.co_name
        if name != "render":
            return False

        if "self" not in frame.f_locals:
            return False

        cls = frame.f_locals["self"].__class__

        inherits_node = _inherits(cls, "Node")

        if not inherits_node:
            return False

        clsname = cls.__name__
        if IS_DJANGO19:
            # in Django 1.9 we need to save the flag that there is included template
            if clsname == "IncludeNode":
                if "context" in frame.f_locals:
                    context = frame.f_locals["context"]
                    context._has_included_template = True

        return clsname not in _IGNORE_RENDER_OF_CLASSES
    except:
        pydev_log.exception()
        return False


def _is_django_context_get_call(frame):
    try:
        if "self" not in frame.f_locals:
            return False

        cls = frame.f_locals["self"].__class__

        return _inherits(cls, "BaseContext")
    except:
        pydev_log.exception()
        return False


def _is_django_resolve_call(frame):
    try:
        name = frame.f_code.co_name
        if name != "_resolve_lookup":
            return False

        if "self" not in frame.f_locals:
            return False

        cls = frame.f_locals["self"].__class__

        clsname = cls.__name__
        return clsname == "Variable"
    except:
        pydev_log.exception()
        return False


def _is_django_suspended(thread):
    return thread.additional_info.suspend_type == DJANGO_SUSPEND


def suspend_django(py_db, thread, frame, cmd=CMD_SET_BREAK):
    if frame.f_lineno is None:
        return None

    py_db.set_suspend(thread, cmd)
    thread.additional_info.suspend_type = DJANGO_SUSPEND

    return frame


def _find_django_render_frame(frame):
    while frame is not None and not _is_django_render_call(frame):
        frame = frame.f_back

    return frame


# =======================================================================================================================
# Django Frame
# =======================================================================================================================


def _read_file(filename):
    # type: (str) -> str
    f = open(filename, "r", encoding="utf-8", errors="replace")
    s = f.read()
    f.close()
    return s


def _offset_to_line_number(text, offset):
    curLine = 1
    curOffset = 0
    while curOffset < offset:
        if curOffset == len(text):
            return -1
        c = text[curOffset]
        if c == "\n":
            curLine += 1
        elif c == "\r":
            curLine += 1
            if curOffset < len(text) and text[curOffset + 1] == "\n":
                curOffset += 1

        curOffset += 1

    return curLine


def _get_source_django_18_or_lower(frame):
    # This method is usable only for the Django <= 1.8
    try:
        node = frame.f_locals["self"]
        if hasattr(node, "source"):
            return node.source
        else:
            if IS_DJANGO18:
                # The debug setting was changed since Django 1.8
                pydev_log.error_once(
                    "WARNING: Template path is not available. Set the 'debug' option in the OPTIONS of a DjangoTemplates " "backend."
                )
            else:
                # The debug setting for Django < 1.8
                pydev_log.error_once(
                    "WARNING: Template path is not available. Please set TEMPLATE_DEBUG=True in your settings.py to make "
                    "django template breakpoints working"
                )
            return None

    except:
        pydev_log.exception()
        return None


def _convert_to_str(s):
    return s


def _get_template_original_file_name_from_frame(frame):
    try:
        if IS_DJANGO19:
            # The Node source was removed since Django 1.9
            if "context" in frame.f_locals:
                context = frame.f_locals["context"]
                if hasattr(context, "_has_included_template"):
                    # if there was included template we need to inspect the previous frames and find its name
                    back = frame.f_back
                    while back is not None and frame.f_code.co_name in ("render", "_render"):
                        locals = back.f_locals
                        if "self" in locals:
                            self = locals["self"]
                            if self.__class__.__name__ == "Template" and hasattr(self, "origin") and hasattr(self.origin, "name"):
                                return _convert_to_str(self.origin.name)
                        back = back.f_back
                else:
                    if hasattr(context, "template") and hasattr(context.template, "origin") and hasattr(context.template.origin, "name"):
                        return _convert_to_str(context.template.origin.name)
            return None
        elif IS_DJANGO19_OR_HIGHER:
            # For Django 1.10 and later there is much simpler way to get template name
            if "self" in frame.f_locals:
                self = frame.f_locals["self"]
                if hasattr(self, "origin") and hasattr(self.origin, "name"):
                    return _convert_to_str(self.origin.name)
            return None

        source = _get_source_django_18_or_lower(frame)
        if source is None:
            pydev_log.debug("Source is None\n")
            return None
        fname = _convert_to_str(source[0].name)

        if fname == "<unknown source>":
            pydev_log.debug("Source name is %s\n" % fname)
            return None
        else:
            return fname
    except:
        if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 2:
            pydev_log.exception("Error getting django template filename.")
        return None


def _get_template_line(frame):
    if IS_DJANGO19_OR_HIGHER:
        node = frame.f_locals["self"]
        if hasattr(node, "token") and hasattr(node.token, "lineno"):
            return node.token.lineno
        else:
            return None

    source = _get_source_django_18_or_lower(frame)
    original_filename = _get_template_original_file_name_from_frame(frame)
    if original_filename is not None:
        try:
            absolute_filename = absolute_path(original_filename)
            return _offset_to_line_number(_read_file(absolute_filename), source[1][0])
        except:
            return None
    return None


class DjangoTemplateFrame(object):
    IS_PLUGIN_FRAME = True

    def __init__(self, frame):
        original_filename = _get_template_original_file_name_from_frame(frame)
        self._back_context = frame.f_locals["context"]
        self.f_code = FCode("Django Template", original_filename)
        self.f_lineno = _get_template_line(frame)
        self.f_back = frame
        self.f_globals = {}
        self.f_locals = self._collect_context(self._back_context)
        self.f_trace = None

    def _collect_context(self, context):
        res = {}
        try:
            for d in context.dicts:
                for k, v in d.items():
                    res[k] = v
        except AttributeError:
            pass
        return res

    def _change_variable(self, name, value):
        for d in self._back_context.dicts:
            for k, v in d.items():
                if k == name:
                    d[k] = value


class DjangoTemplateSyntaxErrorFrame(object):
    IS_PLUGIN_FRAME = True

    def __init__(self, frame, original_filename, lineno, f_locals):
        self.f_code = FCode("Django TemplateSyntaxError", original_filename)
        self.f_lineno = lineno
        self.f_back = frame
        self.f_globals = {}
        self.f_locals = f_locals
        self.f_trace = None


def change_variable(frame, attr, expression, default, scope=None):
    if isinstance(frame, DjangoTemplateFrame):
        result = eval(expression, frame.f_globals, frame.f_locals)
        frame._change_variable(attr, result, scope=scope)
        return result
    return default


def _is_django_variable_does_not_exist_exception_break_context(frame):
    try:
        name = frame.f_code.co_name
    except:
        name = None
    return name in ("_resolve_lookup", "find_template")


def _is_ignoring_failures(frame):
    while frame is not None:
        if frame.f_code.co_name == "resolve":
            ignore_failures = frame.f_locals.get("ignore_failures")
            if ignore_failures:
                return True
        frame = frame.f_back

    return False


# =======================================================================================================================
# Django Step Commands
# =======================================================================================================================


def can_skip(py_db, frame):
    if py_db.django_breakpoints:
        if _is_django_render_call(frame):
            return False

    if py_db.django_exception_break:
        module_name = frame.f_globals.get("__name__", "")

        if module_name == "django.template.base":
            # Exceptions raised at django.template.base must be checked.
            return False

    return True


is_tracked_frame = _is_django_render_call


def required_events_breakpoint():
    return ("call",)


def required_events_stepping():
    return ("call", "return")


def has_exception_breaks(py_db):
    if len(py_db.django_exception_break) > 0:
        return True
    return False


def has_line_breaks(py_db):
    for _canonical_normalized_filename, breakpoints in py_db.django_breakpoints.items():
        if len(breakpoints) > 0:
            return True
    return False


def cmd_step_into(py_db, frame, event, info, thread, stop_info, stop):
    plugin_stop = False
    if _is_django_suspended(thread):
        plugin_stop = stop_info["django_stop"] = event == "call" and _is_django_render_call(frame)
        stop = stop and _is_django_resolve_call(frame.f_back) and not _is_django_context_get_call(frame)
        if stop:
            info.pydev_django_resolve_frame = True  # we remember that we've go into python code from django rendering frame
    return stop, plugin_stop


def cmd_step_over(py_db, frame, event, info, thread, stop_info, stop):
    plugin_stop = False
    if _is_django_suspended(thread):
        plugin_stop = stop_info["django_stop"] = event == "call" and _is_django_render_call(frame)
        stop = False
        return stop, plugin_stop
    else:
        if event == "return" and info.pydev_django_resolve_frame and _is_django_resolve_call(frame.f_back):
            # we return to Django suspend mode and should not stop before django rendering frame
            info.pydev_step_stop = frame.f_back
            info.pydev_django_resolve_frame = False
            thread.additional_info.suspend_type = DJANGO_SUSPEND
        stop = info.pydev_step_stop is frame and event in ("line", "return")
    return stop, plugin_stop


def stop(py_db, frame, event, thread, stop_info, arg, step_cmd):
    if "django_stop" in stop_info and stop_info["django_stop"]:
        frame = suspend_django(py_db, thread, DjangoTemplateFrame(frame), step_cmd)
        if frame:
            py_db.do_wait_suspend(thread, frame, event, arg)
            return True
    return False


def get_breakpoint(py_db, frame, event, info):
    breakpoint_type = "django"

    if event == "call" and info.pydev_state != STATE_SUSPEND and py_db.django_breakpoints and _is_django_render_call(frame):
        original_filename = _get_template_original_file_name_from_frame(frame)
        pydev_log.debug("Django is rendering a template: %s", original_filename)

        canonical_normalized_filename = canonical_normalized_path(original_filename)
        django_breakpoints_for_file = py_db.django_breakpoints.get(canonical_normalized_filename)

        if django_breakpoints_for_file:
            # At this point, let's validate whether template lines are correct.
            if IS_DJANGO19_OR_HIGHER:
                django_validation_info = py_db.django_validation_info
                context = frame.f_locals["context"]
                django_template = context.template
                django_validation_info.verify_breakpoints(
                    py_db, canonical_normalized_filename, django_breakpoints_for_file, django_template
                )

            pydev_log.debug("Breakpoints for that file: %s", django_breakpoints_for_file)
            template_line = _get_template_line(frame)
            pydev_log.debug("Tracing template line: %s", template_line)

            if template_line in django_breakpoints_for_file:
                django_breakpoint = django_breakpoints_for_file[template_line]
                new_frame = DjangoTemplateFrame(frame)
                return django_breakpoint, new_frame, breakpoint_type

    return None


def suspend(py_db, thread, frame, bp_type):
    if bp_type == "django":
        return suspend_django(py_db, thread, DjangoTemplateFrame(frame))
    return None


def _get_original_filename_from_origin_in_parent_frame_locals(frame, parent_frame_name):
    filename = None
    parent_frame = frame
    while parent_frame.f_code.co_name != parent_frame_name:
        parent_frame = parent_frame.f_back

    origin = None
    if parent_frame is not None:
        origin = parent_frame.f_locals.get("origin")

    if hasattr(origin, "name") and origin.name is not None:
        filename = _convert_to_str(origin.name)
    return filename


def exception_break(py_db, frame, thread, arg, is_unwind):
    exception, value, trace = arg

    if py_db.django_exception_break and exception is not None:
        if (
            exception.__name__ in ["VariableDoesNotExist", "TemplateDoesNotExist", "TemplateSyntaxError"]
            and not is_unwind
            and just_raised(trace)
            and not ignore_exception_trace(trace)
        ):
            if exception.__name__ == "TemplateSyntaxError":
                # In this case we don't actually have a regular render frame with the context
                # (we didn't really get to that point).
                token = getattr(value, "token", None)

                if token is None:
                    # Django 1.7 does not have token in exception. Try to get it from locals.
                    token = frame.f_locals.get("token")

                lineno = getattr(token, "lineno", None)

                original_filename = None
                if lineno is not None:
                    original_filename = _get_original_filename_from_origin_in_parent_frame_locals(frame, "get_template")

                    if original_filename is None:
                        # Django 1.7 does not have origin in get_template. Try to get it from
                        # load_template.
                        original_filename = _get_original_filename_from_origin_in_parent_frame_locals(frame, "load_template")

                if original_filename is not None and lineno is not None:
                    syntax_error_frame = DjangoTemplateSyntaxErrorFrame(
                        frame, original_filename, lineno, {"token": token, "exception": exception}
                    )

                    suspend_frame = suspend_django(py_db, thread, syntax_error_frame, CMD_ADD_EXCEPTION_BREAK)
                    return True, suspend_frame

            elif exception.__name__ == "VariableDoesNotExist":
                if _is_django_variable_does_not_exist_exception_break_context(frame):
                    if not getattr(exception, "silent_variable_failure", False) and not _is_ignoring_failures(frame):
                        render_frame = _find_django_render_frame(frame)
                        if render_frame:
                            suspend_frame = suspend_django(py_db, thread, DjangoTemplateFrame(render_frame), CMD_ADD_EXCEPTION_BREAK)
                            if suspend_frame:
                                add_exception_to_frame(suspend_frame, (exception, value, trace))
                                thread.additional_info.pydev_message = "VariableDoesNotExist"
                                suspend_frame.f_back = frame
                                frame = suspend_frame
                                return True, frame

    return None

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\__init__.py ===
from ._types import (
    TextEvent as TextEvent,
    InputJsonEvent as InputJsonEvent,
    MessageStopEvent as MessageStopEvent,
    MessageStreamEvent as MessageStreamEvent,
    ContentBlockStopEvent as ContentBlockStopEvent,
)
from ._messages import (
    MessageStream as MessageStream,
    AsyncMessageStream as AsyncMessageStream,
    MessageStreamManager as MessageStreamManager,
    AsyncMessageStreamManager as AsyncMessageStreamManager,
)
from ._prompt_caching_beta_messages import (
    PromptCachingBetaMessageStream as PromptCachingBetaMessageStream,
    AsyncPromptCachingBetaMessageStream as AsyncPromptCachingBetaMessageStream,
    PromptCachingBetaMessageStreamManager as PromptCachingBetaMessageStreamManager,
    AsyncPromptCachingBetaMessageStreamManager as AsyncPromptCachingBetaMessageStreamManager,
)

# === NexusCore/openenv\Lib\site-packages\urllib3\poolmanager.py ===
from __future__ import annotations

import functools
import logging
import typing
import warnings
from types import TracebackType
from urllib.parse import urljoin

from ._collections import HTTPHeaderDict, RecentlyUsedContainer
from ._request_methods import RequestMethods
from .connection import ProxyConfig
from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool, port_by_scheme
from .exceptions import (
    LocationValueError,
    MaxRetryError,
    ProxySchemeUnknown,
    URLSchemeUnknown,
)
from .response import BaseHTTPResponse
from .util.connection import _TYPE_SOCKET_OPTIONS
from .util.proxy import connection_requires_http_tunnel
from .util.retry import Retry
from .util.timeout import Timeout
from .util.url import Url, parse_url

if typing.TYPE_CHECKING:
    import ssl

    from typing_extensions import Self

__all__ = ["PoolManager", "ProxyManager", "proxy_from_url"]


log = logging.getLogger(__name__)

SSL_KEYWORDS = (
    "key_file",
    "cert_file",
    "cert_reqs",
    "ca_certs",
    "ca_cert_data",
    "ssl_version",
    "ssl_minimum_version",
    "ssl_maximum_version",
    "ca_cert_dir",
    "ssl_context",
    "key_password",
    "server_hostname",
)
# Default value for `blocksize` - a new parameter introduced to
# http.client.HTTPConnection & http.client.HTTPSConnection in Python 3.7
_DEFAULT_BLOCKSIZE = 16384


class PoolKey(typing.NamedTuple):
    """
    All known keyword arguments that could be provided to the pool manager, its
    pools, or the underlying connections.

    All custom key schemes should include the fields in this key at a minimum.
    """

    key_scheme: str
    key_host: str
    key_port: int | None
    key_timeout: Timeout | float | int | None
    key_retries: Retry | bool | int | None
    key_block: bool | None
    key_source_address: tuple[str, int] | None
    key_key_file: str | None
    key_key_password: str | None
    key_cert_file: str | None
    key_cert_reqs: str | None
    key_ca_certs: str | None
    key_ca_cert_data: str | bytes | None
    key_ssl_version: int | str | None
    key_ssl_minimum_version: ssl.TLSVersion | None
    key_ssl_maximum_version: ssl.TLSVersion | None
    key_ca_cert_dir: str | None
    key_ssl_context: ssl.SSLContext | None
    key_maxsize: int | None
    key_headers: frozenset[tuple[str, str]] | None
    key__proxy: Url | None
    key__proxy_headers: frozenset[tuple[str, str]] | None
    key__proxy_config: ProxyConfig | None
    key_socket_options: _TYPE_SOCKET_OPTIONS | None
    key__socks_options: frozenset[tuple[str, str]] | None
    key_assert_hostname: bool | str | None
    key_assert_fingerprint: str | None
    key_server_hostname: str | None
    key_blocksize: int | None


def _default_key_normalizer(
    key_class: type[PoolKey], request_context: dict[str, typing.Any]
) -> PoolKey:
    """
    Create a pool key out of a request context dictionary.

    According to RFC 3986, both the scheme and host are case-insensitive.
    Therefore, this function normalizes both before constructing the pool
    key for an HTTPS request. If you wish to change this behaviour, provide
    alternate callables to ``key_fn_by_scheme``.

    :param key_class:
        The class to use when constructing the key. This should be a namedtuple
        with the ``scheme`` and ``host`` keys at a minimum.
    :type  key_class: namedtuple
    :param request_context:
        A dictionary-like object that contain the context for a request.
    :type  request_context: dict

    :return: A namedtuple that can be used as a connection pool key.
    :rtype:  PoolKey
    """
    # Since we mutate the dictionary, make a copy first
    context = request_context.copy()
    context["scheme"] = context["scheme"].lower()
    context["host"] = context["host"].lower()

    # These are both dictionaries and need to be transformed into frozensets
    for key in ("headers", "_proxy_headers", "_socks_options"):
        if key in context and context[key] is not None:
            context[key] = frozenset(context[key].items())

    # The socket_options key may be a list and needs to be transformed into a
    # tuple.
    socket_opts = context.get("socket_options")
    if socket_opts is not None:
        context["socket_options"] = tuple(socket_opts)

    # Map the kwargs to the names in the namedtuple - this is necessary since
    # namedtuples can't have fields starting with '_'.
    for key in list(context.keys()):
        context["key_" + key] = context.pop(key)

    # Default to ``None`` for keys missing from the context
    for field in key_class._fields:
        if field not in context:
            context[field] = None

    # Default key_blocksize to _DEFAULT_BLOCKSIZE if missing from the context
    if context.get("key_blocksize") is None:
        context["key_blocksize"] = _DEFAULT_BLOCKSIZE

    return key_class(**context)


#: A dictionary that maps a scheme to a callable that creates a pool key.
#: This can be used to alter the way pool keys are constructed, if desired.
#: Each PoolManager makes a copy of this dictionary so they can be configured
#: globally here, or individually on the instance.
key_fn_by_scheme = {
    "http": functools.partial(_default_key_normalizer, PoolKey),
    "https": functools.partial(_default_key_normalizer, PoolKey),
}

pool_classes_by_scheme = {"http": HTTPConnectionPool, "https": HTTPSConnectionPool}


class PoolManager(RequestMethods):
    """
    Allows for arbitrary requests while transparently keeping track of
    necessary connection pools for you.

    :param num_pools:
        Number of connection pools to cache before discarding the least
        recently used pool.

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.

    :param \\**connection_pool_kw:
        Additional parameters are used to create fresh
        :class:`urllib3.connectionpool.ConnectionPool` instances.

    Example:

    .. code-block:: python

        import urllib3

        http = urllib3.PoolManager(num_pools=2)

        resp1 = http.request("GET", "https://google.com/")
        resp2 = http.request("GET", "https://google.com/mail")
        resp3 = http.request("GET", "https://yahoo.com/")

        print(len(http.pools))
        # 2

    """

    proxy: Url | None = None
    proxy_config: ProxyConfig | None = None

    def __init__(
        self,
        num_pools: int = 10,
        headers: typing.Mapping[str, str] | None = None,
        **connection_pool_kw: typing.Any,
    ) -> None:
        super().__init__(headers)
        self.connection_pool_kw = connection_pool_kw

        self.pools: RecentlyUsedContainer[PoolKey, HTTPConnectionPool]
        self.pools = RecentlyUsedContainer(num_pools)

        # Locally set the pool classes and keys so other PoolManagers can
        # override them.
        self.pool_classes_by_scheme = pool_classes_by_scheme
        self.key_fn_by_scheme = key_fn_by_scheme.copy()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> typing.Literal[False]:
        self.clear()
        # Return False to re-raise any potential exceptions
        return False

    def _new_pool(
        self,
        scheme: str,
        host: str,
        port: int,
        request_context: dict[str, typing.Any] | None = None,
    ) -> HTTPConnectionPool:
        """
        Create a new :class:`urllib3.connectionpool.ConnectionPool` based on host, port, scheme, and
        any additional pool keyword arguments.

        If ``request_context`` is provided, it is provided as keyword arguments
        to the pool class used. This method is used to actually create the
        connection pools handed out by :meth:`connection_from_url` and
        companion methods. It is intended to be overridden for customization.
        """
        pool_cls: type[HTTPConnectionPool] = self.pool_classes_by_scheme[scheme]
        if request_context is None:
            request_context = self.connection_pool_kw.copy()

        # Default blocksize to _DEFAULT_BLOCKSIZE if missing or explicitly
        # set to 'None' in the request_context.
        if request_context.get("blocksize") is None:
            request_context["blocksize"] = _DEFAULT_BLOCKSIZE

        # Although the context has everything necessary to create the pool,
        # this function has historically only used the scheme, host, and port
        # in the positional args. When an API change is acceptable these can
        # be removed.
        for key in ("scheme", "host", "port"):
            request_context.pop(key, None)

        if scheme == "http":
            for kw in SSL_KEYWORDS:
                request_context.pop(kw, None)

        return pool_cls(host, port, **request_context)

    def clear(self) -> None:
        """
        Empty our store of pools and direct them all to close.

        This will not affect in-flight connections, but they will not be
        re-used after completion.
        """
        self.pools.clear()

    def connection_from_host(
        self,
        host: str | None,
        port: int | None = None,
        scheme: str | None = "http",
        pool_kwargs: dict[str, typing.Any] | None = None,
    ) -> HTTPConnectionPool:
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the host, port, and scheme.

        If ``port`` isn't given, it will be derived from the ``scheme`` using
        ``urllib3.connectionpool.port_by_scheme``. If ``pool_kwargs`` is
        provided, it is merged with the instance's ``connection_pool_kw``
        variable and used to create the new connection pool, if one is
        needed.
        """

        if not host:
            raise LocationValueError("No host specified.")

        request_context = self._merge_pool_kwargs(pool_kwargs)
        request_context["scheme"] = scheme or "http"
        if not port:
            port = port_by_scheme.get(request_context["scheme"].lower(), 80)
        request_context["port"] = port
        request_context["host"] = host

        return self.connection_from_context(request_context)

    def connection_from_context(
        self, request_context: dict[str, typing.Any]
    ) -> HTTPConnectionPool:
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the request context.

        ``request_context`` must at least contain the ``scheme`` key and its
        value must be a key in ``key_fn_by_scheme`` instance variable.
        """
        if "strict" in request_context:
            warnings.warn(
                "The 'strict' parameter is no longer needed on Python 3+. "
                "This will raise an error in urllib3 v2.1.0.",
                DeprecationWarning,
            )
            request_context.pop("strict")

        scheme = request_context["scheme"].lower()
        pool_key_constructor = self.key_fn_by_scheme.get(scheme)
        if not pool_key_constructor:
            raise URLSchemeUnknown(scheme)
        pool_key = pool_key_constructor(request_context)

        return self.connection_from_pool_key(pool_key, request_context=request_context)

    def connection_from_pool_key(
        self, pool_key: PoolKey, request_context: dict[str, typing.Any]
    ) -> HTTPConnectionPool:
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the provided pool key.

        ``pool_key`` should be a namedtuple that only contains immutable
        objects. At a minimum it must have the ``scheme``, ``host``, and
        ``port`` fields.
        """
        with self.pools.lock:
            # If the scheme, host, or port doesn't match existing open
            # connections, open a new ConnectionPool.
            pool = self.pools.get(pool_key)
            if pool:
                return pool

            # Make a fresh ConnectionPool of the desired type
            scheme = request_context["scheme"]
            host = request_context["host"]
            port = request_context["port"]
            pool = self._new_pool(scheme, host, port, request_context=request_context)
            self.pools[pool_key] = pool

        return pool

    def connection_from_url(
        self, url: str, pool_kwargs: dict[str, typing.Any] | None = None
    ) -> HTTPConnectionPool:
        """
        Similar to :func:`urllib3.connectionpool.connection_from_url`.

        If ``pool_kwargs`` is not provided and a new pool needs to be
        constructed, ``self.connection_pool_kw`` is used to initialize
        the :class:`urllib3.connectionpool.ConnectionPool`. If ``pool_kwargs``
        is provided, it is used instead. Note that if a new pool does not
        need to be created for the request, the provided ``pool_kwargs`` are
        not used.
        """
        u = parse_url(url)
        return self.connection_from_host(
            u.host, port=u.port, scheme=u.scheme, pool_kwargs=pool_kwargs
        )

    def _merge_pool_kwargs(
        self, override: dict[str, typing.Any] | None
    ) -> dict[str, typing.Any]:
        """
        Merge a dictionary of override values for self.connection_pool_kw.

        This does not modify self.connection_pool_kw and returns a new dict.
        Any keys in the override dictionary with a value of ``None`` are
        removed from the merged dictionary.
        """
        base_pool_kwargs = self.connection_pool_kw.copy()
        if override:
            for key, value in override.items():
                if value is None:
                    try:
                        del base_pool_kwargs[key]
                    except KeyError:
                        pass
                else:
                    base_pool_kwargs[key] = value
        return base_pool_kwargs

    def _proxy_requires_url_absolute_form(self, parsed_url: Url) -> bool:
        """
        Indicates if the proxy requires the complete destination URL in the
        request.  Normally this is only needed when not using an HTTP CONNECT
        tunnel.
        """
        if self.proxy is None:
            return False

        return not connection_requires_http_tunnel(
            self.proxy, self.proxy_config, parsed_url.scheme
        )

    def urlopen(  # type: ignore[override]
        self, method: str, url: str, redirect: bool = True, **kw: typing.Any
    ) -> BaseHTTPResponse:
        """
        Same as :meth:`urllib3.HTTPConnectionPool.urlopen`
        with custom cross-host redirect logic and only sends the request-uri
        portion of the ``url``.

        The given ``url`` parameter must be absolute, such that an appropriate
        :class:`urllib3.connectionpool.ConnectionPool` can be chosen for it.
        """
        u = parse_url(url)

        if u.scheme is None:
            warnings.warn(
                "URLs without a scheme (ie 'https://') are deprecated and will raise an error "
                "in a future version of urllib3. To avoid this DeprecationWarning ensure all URLs "
                "start with 'https://' or 'http://'. Read more in this issue: "
                "https://github.com/urllib3/urllib3/issues/2920",
                category=DeprecationWarning,
                stacklevel=2,
            )

        conn = self.connection_from_host(u.host, port=u.port, scheme=u.scheme)

        kw["assert_same_host"] = False
        kw["redirect"] = False

        if "headers" not in kw:
            kw["headers"] = self.headers

        if self._proxy_requires_url_absolute_form(u):
            response = conn.urlopen(method, url, **kw)
        else:
            response = conn.urlopen(method, u.request_uri, **kw)

        redirect_location = redirect and response.get_redirect_location()
        if not redirect_location:
            return response

        # Support relative URLs for redirecting.
        redirect_location = urljoin(url, redirect_location)

        if response.status == 303:
            # Change the method according to RFC 9110, Section 15.4.4.
            method = "GET"
            # And lose the body not to transfer anything sensitive.
            kw["body"] = None
            kw["headers"] = HTTPHeaderDict(kw["headers"])._prepare_for_method_change()

        retries = kw.get("retries")
        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect)

        # Strip headers marked as unsafe to forward to the redirected location.
        # Check remove_headers_on_redirect to avoid a potential network call within
        # conn.is_same_host() which may use socket.gethostbyname() in the future.
        if retries.remove_headers_on_redirect and not conn.is_same_host(
            redirect_location
        ):
            new_headers = kw["headers"].copy()
            for header in kw["headers"]:
                if header.lower() in retries.remove_headers_on_redirect:
                    new_headers.pop(header, None)
            kw["headers"] = new_headers

        try:
            retries = retries.increment(method, url, response=response, _pool=conn)
        except MaxRetryError:
            if retries.raise_on_redirect:
                response.drain_conn()
                raise
            return response

        kw["retries"] = retries
        kw["redirect"] = redirect

        log.info("Redirecting %s -> %s", url, redirect_location)

        response.drain_conn()
        return self.urlopen(method, redirect_location, **kw)


class ProxyManager(PoolManager):
    """
    Behaves just like :class:`PoolManager`, but sends all requests through
    the defined proxy, using the CONNECT method for HTTPS URLs.

    :param proxy_url:
        The URL of the proxy to be used.

    :param proxy_headers:
        A dictionary containing headers that will be sent to the proxy. In case
        of HTTP they are being sent with each request, while in the
        HTTPS/CONNECT case they are sent only once. Could be used for proxy
        authentication.

    :param proxy_ssl_context:
        The proxy SSL context is used to establish the TLS connection to the
        proxy when using HTTPS proxies.

    :param use_forwarding_for_https:
        (Defaults to False) If set to True will forward requests to the HTTPS
        proxy to be made on behalf of the client instead of creating a TLS
        tunnel via the CONNECT method. **Enabling this flag means that request
        and response headers and content will be visible from the HTTPS proxy**
        whereas tunneling keeps request and response headers and content
        private.  IP address, target hostname, SNI, and port are always visible
        to an HTTPS proxy even when this flag is disabled.

    :param proxy_assert_hostname:
        The hostname of the certificate to verify against.

    :param proxy_assert_fingerprint:
        The fingerprint of the certificate to verify against.

    Example:

    .. code-block:: python

        import urllib3

        proxy = urllib3.ProxyManager("https://localhost:3128/")

        resp1 = proxy.request("GET", "https://google.com/")
        resp2 = proxy.request("GET", "https://httpbin.org/")

        print(len(proxy.pools))
        # 1

        resp3 = proxy.request("GET", "https://httpbin.org/")
        resp4 = proxy.request("GET", "https://twitter.com/")

        print(len(proxy.pools))
        # 3

    """

    def __init__(
        self,
        proxy_url: str,
        num_pools: int = 10,
        headers: typing.Mapping[str, str] | None = None,
        proxy_headers: typing.Mapping[str, str] | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
        use_forwarding_for_https: bool = False,
        proxy_assert_hostname: None | str | typing.Literal[False] = None,
        proxy_assert_fingerprint: str | None = None,
        **connection_pool_kw: typing.Any,
    ) -> None:
        if isinstance(proxy_url, HTTPConnectionPool):
            str_proxy_url = f"{proxy_url.scheme}://{proxy_url.host}:{proxy_url.port}"
        else:
            str_proxy_url = proxy_url
        proxy = parse_url(str_proxy_url)

        if proxy.scheme not in ("http", "https"):
            raise ProxySchemeUnknown(proxy.scheme)

        if not proxy.port:
            port = port_by_scheme.get(proxy.scheme, 80)
            proxy = proxy._replace(port=port)

        self.proxy = proxy
        self.proxy_headers = proxy_headers or {}
        self.proxy_ssl_context = proxy_ssl_context
        self.proxy_config = ProxyConfig(
            proxy_ssl_context,
            use_forwarding_for_https,
            proxy_assert_hostname,
            proxy_assert_fingerprint,
        )

        connection_pool_kw["_proxy"] = self.proxy
        connection_pool_kw["_proxy_headers"] = self.proxy_headers
        connection_pool_kw["_proxy_config"] = self.proxy_config

        super().__init__(num_pools, headers, **connection_pool_kw)

    def connection_from_host(
        self,
        host: str | None,
        port: int | None = None,
        scheme: str | None = "http",
        pool_kwargs: dict[str, typing.Any] | None = None,
    ) -> HTTPConnectionPool:
        if scheme == "https":
            return super().connection_from_host(
                host, port, scheme, pool_kwargs=pool_kwargs
            )

        return super().connection_from_host(
            self.proxy.host, self.proxy.port, self.proxy.scheme, pool_kwargs=pool_kwargs  # type: ignore[union-attr]
        )

    def _set_proxy_headers(
        self, url: str, headers: typing.Mapping[str, str] | None = None
    ) -> typing.Mapping[str, str]:
        """
        Sets headers needed by proxies: specifically, the Accept and Host
        headers. Only sets headers not provided by the user.
        """
        headers_ = {"Accept": "*/*"}

        netloc = parse_url(url).netloc
        if netloc:
            headers_["Host"] = netloc

        if headers:
            headers_.update(headers)
        return headers_

    def urlopen(  # type: ignore[override]
        self, method: str, url: str, redirect: bool = True, **kw: typing.Any
    ) -> BaseHTTPResponse:
        "Same as HTTP(S)ConnectionPool.urlopen, ``url`` must be absolute."
        u = parse_url(url)
        if not connection_requires_http_tunnel(self.proxy, self.proxy_config, u.scheme):
            # For connections using HTTP CONNECT, httplib sets the necessary
            # headers on the CONNECT to the proxy. If we're not using CONNECT,
            # we'll definitely need to set 'Host' at the very least.
            headers = kw.get("headers", self.headers)
            kw["headers"] = self._set_proxy_headers(url, headers)

        return super().urlopen(method, url, redirect=redirect, **kw)


def proxy_from_url(url: str, **kw: typing.Any) -> ProxyManager:
    return ProxyManager(proxy_url=url, **kw)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_http.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contains utilities to handle HTTP requests in Huggingface Hub."""

import io
import os
import re
import threading
import time
import uuid
from functools import lru_cache
from http import HTTPStatus
from shlex import quote
from typing import Any, Callable, List, Optional, Tuple, Type, Union

import requests
from requests import HTTPError, Response
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest

from huggingface_hub.errors import OfflineModeIsEnabled

from .. import constants
from ..errors import (
    BadRequestError,
    DisabledRepoError,
    EntryNotFoundError,
    GatedRepoError,
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from . import logging
from ._fixes import JSONDecodeError
from ._lfs import SliceFileObj
from ._typing import HTTP_METHOD_T


logger = logging.get_logger(__name__)

# Both headers are used by the Hub to debug failed requests.
# `X_AMZN_TRACE_ID` is better as it also works to debug on Cloudfront and ALB.
# If `X_AMZN_TRACE_ID` is set, the Hub will use it as well.
X_AMZN_TRACE_ID = "X-Amzn-Trace-Id"
X_REQUEST_ID = "x-request-id"

REPO_API_REGEX = re.compile(
    r"""
        # staging or production endpoint
        ^https://[^/]+
        (
            # on /api/repo_type/repo_id
            /api/(models|datasets|spaces)/(.+)
            |
            # or /repo_id/resolve/revision/...
            /(.+)/resolve/(.+)
        )
    """,
    flags=re.VERBOSE,
)


class UniqueRequestIdAdapter(HTTPAdapter):
    X_AMZN_TRACE_ID = "X-Amzn-Trace-Id"

    def add_headers(self, request, **kwargs):
        super().add_headers(request, **kwargs)

        # Add random request ID => easier for server-side debug
        if X_AMZN_TRACE_ID not in request.headers:
            request.headers[X_AMZN_TRACE_ID] = request.headers.get(X_REQUEST_ID) or str(uuid.uuid4())

        # Add debug log
        has_token = len(str(request.headers.get("authorization", ""))) > 0
        logger.debug(
            f"Request {request.headers[X_AMZN_TRACE_ID]}: {request.method} {request.url} (authenticated: {has_token})"
        )

    def send(self, request: PreparedRequest, *args, **kwargs) -> Response:
        """Catch any RequestException to append request id to the error message for debugging."""
        if constants.HF_DEBUG:
            logger.debug(f"Send: {_curlify(request)}")
        try:
            return super().send(request, *args, **kwargs)
        except requests.RequestException as e:
            request_id = request.headers.get(X_AMZN_TRACE_ID)
            if request_id is not None:
                # Taken from https://stackoverflow.com/a/58270258
                e.args = (*e.args, f"(Request ID: {request_id})")
            raise


class OfflineAdapter(HTTPAdapter):
    def send(self, request: PreparedRequest, *args, **kwargs) -> Response:
        raise OfflineModeIsEnabled(
            f"Cannot reach {request.url}: offline mode is enabled. To disable it, please unset the `HF_HUB_OFFLINE` environment variable."
        )


def _default_backend_factory() -> requests.Session:
    session = requests.Session()
    if constants.HF_HUB_OFFLINE:
        session.mount("http://", OfflineAdapter())
        session.mount("https://", OfflineAdapter())
    else:
        session.mount("http://", UniqueRequestIdAdapter())
        session.mount("https://", UniqueRequestIdAdapter())
    return session


BACKEND_FACTORY_T = Callable[[], requests.Session]
_GLOBAL_BACKEND_FACTORY: BACKEND_FACTORY_T = _default_backend_factory


def configure_http_backend(backend_factory: BACKEND_FACTORY_T = _default_backend_factory) -> None:
    """
    Configure the HTTP backend by providing a `backend_factory`. Any HTTP calls made by `huggingface_hub` will use a
    Session object instantiated by this factory. This can be useful if you are running your scripts in a specific
    environment requiring custom configuration (e.g. custom proxy or certifications).

    Use [`get_session`] to get a configured Session. Since `requests.Session` is not guaranteed to be thread-safe,
    `huggingface_hub` creates 1 Session instance per thread. They are all instantiated using the same `backend_factory`
    set in [`configure_http_backend`]. A LRU cache is used to cache the created sessions (and connections) between
    calls. Max size is 128 to avoid memory leaks if thousands of threads are spawned.

    See [this issue](https://github.com/psf/requests/issues/2766) to know more about thread-safety in `requests`.

    Example:
    ```py
    import requests
    from huggingface_hub import configure_http_backend, get_session

    # Create a factory function that returns a Session with configured proxies
    def backend_factory() -> requests.Session:
        session = requests.Session()
        session.proxies = {"http": "http://10.10.1.10:3128", "https": "https://10.10.1.11:1080"}
        return session

    # Set it as the default session factory
    configure_http_backend(backend_factory=backend_factory)

    # In practice, this is mostly done internally in `huggingface_hub`
    session = get_session()
    ```
    """
    global _GLOBAL_BACKEND_FACTORY
    _GLOBAL_BACKEND_FACTORY = backend_factory
    reset_sessions()


def get_session() -> requests.Session:
    """
    Get a `requests.Session` object, using the session factory from the user.

    Use [`get_session`] to get a configured Session. Since `requests.Session` is not guaranteed to be thread-safe,
    `huggingface_hub` creates 1 Session instance per thread. They are all instantiated using the same `backend_factory`
    set in [`configure_http_backend`]. A LRU cache is used to cache the created sessions (and connections) between
    calls. Max size is 128 to avoid memory leaks if thousands of threads are spawned.

    See [this issue](https://github.com/psf/requests/issues/2766) to know more about thread-safety in `requests`.

    Example:
    ```py
    import requests
    from huggingface_hub import configure_http_backend, get_session

    # Create a factory function that returns a Session with configured proxies
    def backend_factory() -> requests.Session:
        session = requests.Session()
        session.proxies = {"http": "http://10.10.1.10:3128", "https": "https://10.10.1.11:1080"}
        return session

    # Set it as the default session factory
    configure_http_backend(backend_factory=backend_factory)

    # In practice, this is mostly done internally in `huggingface_hub`
    session = get_session()
    ```
    """
    return _get_session_from_cache(process_id=os.getpid(), thread_id=threading.get_ident())


def reset_sessions() -> None:
    """Reset the cache of sessions.

    Mostly used internally when sessions are reconfigured or an SSLError is raised.
    See [`configure_http_backend`] for more details.
    """
    _get_session_from_cache.cache_clear()


@lru_cache
def _get_session_from_cache(process_id: int, thread_id: int) -> requests.Session:
    """
    Create a new session per thread using global factory. Using LRU cache (maxsize 128) to avoid memory leaks when
    using thousands of threads. Cache is cleared when `configure_http_backend` is called.
    """
    return _GLOBAL_BACKEND_FACTORY()


def http_backoff(
    method: HTTP_METHOD_T,
    url: str,
    *,
    max_retries: int = 5,
    base_wait_time: float = 1,
    max_wait_time: float = 8,
    retry_on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (
        requests.Timeout,
        requests.ConnectionError,
    ),
    retry_on_status_codes: Union[int, Tuple[int, ...]] = HTTPStatus.SERVICE_UNAVAILABLE,
    **kwargs,
) -> Response:
    """Wrapper around requests to retry calls on an endpoint, with exponential backoff.

    Endpoint call is retried on exceptions (ex: connection timeout, proxy error,...)
    and/or on specific status codes (ex: service unavailable). If the call failed more
    than `max_retries`, the exception is thrown or `raise_for_status` is called on the
    response object.

    Re-implement mechanisms from the `backoff` library to avoid adding an external
    dependencies to `hugging_face_hub`. See https://github.com/litl/backoff.

    Args:
        method (`Literal["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"]`):
            HTTP method to perform.
        url (`str`):
            The URL of the resource to fetch.
        max_retries (`int`, *optional*, defaults to `5`):
            Maximum number of retries, defaults to 5 (no retries).
        base_wait_time (`float`, *optional*, defaults to `1`):
            Duration (in seconds) to wait before retrying the first time.
            Wait time between retries then grows exponentially, capped by
            `max_wait_time`.
        max_wait_time (`float`, *optional*, defaults to `8`):
            Maximum duration (in seconds) to wait before retrying.
        retry_on_exceptions (`Type[Exception]` or `Tuple[Type[Exception]]`, *optional*):
            Define which exceptions must be caught to retry the request. Can be a single type or a tuple of types.
            By default, retry on `requests.Timeout` and `requests.ConnectionError`.
        retry_on_status_codes (`int` or `Tuple[int]`, *optional*, defaults to `503`):
            Define on which status codes the request must be retried. By default, only
            HTTP 503 Service Unavailable is retried.
        **kwargs (`dict`, *optional*):
            kwargs to pass to `requests.request`.

    Example:
    ```
    >>> from huggingface_hub.utils import http_backoff

    # Same usage as "requests.request".
    >>> response = http_backoff("GET", "https://www.google.com")
    >>> response.raise_for_status()

    # If you expect a Gateway Timeout from time to time
    >>> http_backoff("PUT", upload_url, data=data, retry_on_status_codes=504)
    >>> response.raise_for_status()
    ```

    <Tip warning={true}>

    When using `requests` it is possible to stream data by passing an iterator to the
    `data` argument. On http backoff this is a problem as the iterator is not reset
    after a failed call. This issue is mitigated for file objects or any IO streams
    by saving the initial position of the cursor (with `data.tell()`) and resetting the
    cursor between each call (with `data.seek()`). For arbitrary iterators, http backoff
    will fail. If this is a hard constraint for you, please let us know by opening an
    issue on [Github](https://github.com/huggingface/huggingface_hub).

    </Tip>
    """
    if isinstance(retry_on_exceptions, type):  # Tuple from single exception type
        retry_on_exceptions = (retry_on_exceptions,)

    if isinstance(retry_on_status_codes, int):  # Tuple from single status code
        retry_on_status_codes = (retry_on_status_codes,)

    nb_tries = 0
    sleep_time = base_wait_time

    # If `data` is used and is a file object (or any IO), it will be consumed on the
    # first HTTP request. We need to save the initial position so that the full content
    # of the file is re-sent on http backoff. See warning tip in docstring.
    io_obj_initial_pos = None
    if "data" in kwargs and isinstance(kwargs["data"], (io.IOBase, SliceFileObj)):
        io_obj_initial_pos = kwargs["data"].tell()

    session = get_session()
    while True:
        nb_tries += 1
        try:
            # If `data` is used and is a file object (or any IO), set back cursor to
            # initial position.
            if io_obj_initial_pos is not None:
                kwargs["data"].seek(io_obj_initial_pos)

            # Perform request and return if status_code is not in the retry list.
            response = session.request(method=method, url=url, **kwargs)
            if response.status_code not in retry_on_status_codes:
                return response

            # Wrong status code returned (HTTP 503 for instance)
            logger.warning(f"HTTP Error {response.status_code} thrown while requesting {method} {url}")
            if nb_tries > max_retries:
                response.raise_for_status()  # Will raise uncaught exception
                # We return response to avoid infinite loop in the corner case where the
                # user ask for retry on a status code that doesn't raise_for_status.
                return response

        except retry_on_exceptions as err:
            logger.warning(f"'{err}' thrown while requesting {method} {url}")

            if isinstance(err, requests.ConnectionError):
                reset_sessions()  # In case of SSLError it's best to reset the shared requests.Session objects

            if nb_tries > max_retries:
                raise err

        # Sleep for X seconds
        logger.warning(f"Retrying in {sleep_time}s [Retry {nb_tries}/{max_retries}].")
        time.sleep(sleep_time)

        # Update sleep time for next retry
        sleep_time = min(max_wait_time, sleep_time * 2)  # Exponential backoff


def fix_hf_endpoint_in_url(url: str, endpoint: Optional[str]) -> str:
    """Replace the default endpoint in a URL by a custom one.

    This is useful when using a proxy and the Hugging Face Hub returns a URL with the default endpoint.
    """
    endpoint = endpoint.rstrip("/") if endpoint else constants.ENDPOINT
    # check if a proxy has been set => if yes, update the returned URL to use the proxy
    if endpoint not in (constants._HF_DEFAULT_ENDPOINT, constants._HF_DEFAULT_STAGING_ENDPOINT):
        url = url.replace(constants._HF_DEFAULT_ENDPOINT, endpoint)
        url = url.replace(constants._HF_DEFAULT_STAGING_ENDPOINT, endpoint)
    return url


def hf_raise_for_status(response: Response, endpoint_name: Optional[str] = None) -> None:
    """
    Internal version of `response.raise_for_status()` that will refine a
    potential HTTPError. Raised exception will be an instance of `HfHubHTTPError`.

    This helper is meant to be the unique method to raise_for_status when making a call
    to the Hugging Face Hub.


    Example:
    ```py
        import requests
        from huggingface_hub.utils import get_session, hf_raise_for_status, HfHubHTTPError

        response = get_session().post(...)
        try:
            hf_raise_for_status(response)
        except HfHubHTTPError as e:
            print(str(e)) # formatted message
            e.request_id, e.server_message # details returned by server

            # Complete the error message with additional information once it's raised
            e.append_to_message("\n`create_commit` expects the repository to exist.")
            raise
    ```

    Args:
        response (`Response`):
            Response from the server.
        endpoint_name (`str`, *optional*):
            Name of the endpoint that has been called. If provided, the error message
            will be more complete.

    <Tip warning={true}>

    Raises when the request has failed:

        - [`~utils.RepositoryNotFoundError`]
            If the repository to download from cannot be found. This may be because it
            doesn't exist, because `repo_type` is not set correctly, or because the repo
            is `private` and you do not have access.
        - [`~utils.GatedRepoError`]
            If the repository exists but is gated and the user is not on the authorized
            list.
        - [`~utils.RevisionNotFoundError`]
            If the repository exists but the revision couldn't be find.
        - [`~utils.EntryNotFoundError`]
            If the repository exists but the entry (e.g. the requested file) couldn't be
            find.
        - [`~utils.BadRequestError`]
            If request failed with a HTTP 400 BadRequest error.
        - [`~utils.HfHubHTTPError`]
            If request failed for a reason not listed above.

    </Tip>
    """
    try:
        response.raise_for_status()
    except HTTPError as e:
        error_code = response.headers.get("X-Error-Code")
        error_message = response.headers.get("X-Error-Message")

        if error_code == "RevisionNotFound":
            message = f"{response.status_code} Client Error." + "\n\n" + f"Revision Not Found for url: {response.url}."
            raise _format(RevisionNotFoundError, message, response) from e

        elif error_code == "EntryNotFound":
            message = f"{response.status_code} Client Error." + "\n\n" + f"Entry Not Found for url: {response.url}."
            raise _format(EntryNotFoundError, message, response) from e

        elif error_code == "GatedRepo":
            message = (
                f"{response.status_code} Client Error." + "\n\n" + f"Cannot access gated repo for url {response.url}."
            )
            raise _format(GatedRepoError, message, response) from e

        elif error_message == "Access to this resource is disabled.":
            message = (
                f"{response.status_code} Client Error."
                + "\n\n"
                + f"Cannot access repository for url {response.url}."
                + "\n"
                + "Access to this resource is disabled."
            )
            raise _format(DisabledRepoError, message, response) from e

        elif error_code == "RepoNotFound" or (
            response.status_code == 401
            and error_message != "Invalid credentials in Authorization header"
            and response.request is not None
            and response.request.url is not None
            and REPO_API_REGEX.search(response.request.url) is not None
        ):
            # 401 is misleading as it is returned for:
            #    - private and gated repos if user is not authenticated
            #    - missing repos
            # => for now, we process them as `RepoNotFound` anyway.
            # See https://gist.github.com/Wauplin/46c27ad266b15998ce56a6603796f0b9
            message = (
                f"{response.status_code} Client Error."
                + "\n\n"
                + f"Repository Not Found for url: {response.url}."
                + "\nPlease make sure you specified the correct `repo_id` and"
                " `repo_type`.\nIf you are trying to access a private or gated repo,"
                " make sure you are authenticated. For more details, see"
                " https://huggingface.co/docs/huggingface_hub/authentication"
            )
            raise _format(RepositoryNotFoundError, message, response) from e

        elif response.status_code == 400:
            message = (
                f"\n\nBad request for {endpoint_name} endpoint:" if endpoint_name is not None else "\n\nBad request:"
            )
            raise _format(BadRequestError, message, response) from e

        elif response.status_code == 403:
            message = (
                f"\n\n{response.status_code} Forbidden: {error_message}."
                + f"\nCannot access content at: {response.url}."
                + "\nMake sure your token has the correct permissions."
            )
            raise _format(HfHubHTTPError, message, response) from e

        elif response.status_code == 416:
            range_header = response.request.headers.get("Range")
            message = f"{e}. Requested range: {range_header}. Content-Range: {response.headers.get('Content-Range')}."
            raise _format(HfHubHTTPError, message, response) from e

        # Convert `HTTPError` into a `HfHubHTTPError` to display request information
        # as well (request id and/or server error message)
        raise _format(HfHubHTTPError, str(e), response) from e


def _format(error_type: Type[HfHubHTTPError], custom_message: str, response: Response) -> HfHubHTTPError:
    server_errors = []

    # Retrieve server error from header
    from_headers = response.headers.get("X-Error-Message")
    if from_headers is not None:
        server_errors.append(from_headers)

    # Retrieve server error from body
    try:
        # Case errors are returned in a JSON format
        data = response.json()

        error = data.get("error")
        if error is not None:
            if isinstance(error, list):
                # Case {'error': ['my error 1', 'my error 2']}
                server_errors.extend(error)
            else:
                # Case {'error': 'my error'}
                server_errors.append(error)

        errors = data.get("errors")
        if errors is not None:
            # Case {'errors': [{'message': 'my error 1'}, {'message': 'my error 2'}]}
            for error in errors:
                if "message" in error:
                    server_errors.append(error["message"])

    except JSONDecodeError:
        # If content is not JSON and not HTML, append the text
        content_type = response.headers.get("Content-Type", "")
        if response.text and "html" not in content_type.lower():
            server_errors.append(response.text)

    # Strip all server messages
    server_errors = [str(line).strip() for line in server_errors if str(line).strip()]

    # Deduplicate server messages (keep order)
    # taken from https://stackoverflow.com/a/17016257
    server_errors = list(dict.fromkeys(server_errors))

    # Format server error
    server_message = "\n".join(server_errors)

    # Add server error to custom message
    final_error_message = custom_message
    if server_message and server_message.lower() not in custom_message.lower():
        if "\n\n" in custom_message:
            final_error_message += "\n" + server_message
        else:
            final_error_message += "\n\n" + server_message
    # Add Request ID
    request_id = str(response.headers.get(X_REQUEST_ID, ""))
    if request_id:
        request_id_message = f" (Request ID: {request_id})"
    else:
        # Fallback to X-Amzn-Trace-Id
        request_id = str(response.headers.get(X_AMZN_TRACE_ID, ""))
        if request_id:
            request_id_message = f" (Amzn Trace ID: {request_id})"
    if request_id and request_id.lower() not in final_error_message.lower():
        if "\n" in final_error_message:
            newline_index = final_error_message.index("\n")
            final_error_message = (
                final_error_message[:newline_index] + request_id_message + final_error_message[newline_index:]
            )
        else:
            final_error_message += request_id_message

    # Return
    return error_type(final_error_message.strip(), response=response, server_message=server_message or None)


def _curlify(request: requests.PreparedRequest) -> str:
    """Convert a `requests.PreparedRequest` into a curl command (str).

    Used for debug purposes only.

    Implementation vendored from https://github.com/ofw/curlify/blob/master/curlify.py.
    MIT License Copyright (c) 2016 Egor.
    """
    parts: List[Tuple[Any, Any]] = [
        ("curl", None),
        ("-X", request.method),
    ]

    for k, v in sorted(request.headers.items()):
        if k.lower() == "authorization":
            v = "<TOKEN>"  # Hide authorization header, no matter its value (can be Bearer, Key, etc.)
        parts += [("-H", "{0}: {1}".format(k, v))]

    if request.body:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="ignore")
        elif hasattr(body, "read"):
            body = "<file-like object>"  # Don't try to read it to avoid consuming the stream
        if len(body) > 1000:
            body = body[:1000] + " ... [truncated]"
        parts += [("-d", body.replace("\n", ""))]

    parts += [(None, request.url)]

    flat_parts = []
    for k, v in parts:
        if k:
            flat_parts.append(quote(k))
        if v:
            flat_parts.append(quote(v))

    return " ".join(flat_parts)


# Regex to parse HTTP Range header
RANGE_REGEX = re.compile(r"^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$", re.IGNORECASE)


def _adjust_range_header(original_range: Optional[str], resume_size: int) -> Optional[str]:
    """
    Adjust HTTP Range header to account for resume position.
    """
    if not original_range:
        return f"bytes={resume_size}-"

    if "," in original_range:
        raise ValueError(f"Multiple ranges detected - {original_range!r}, not supported yet.")

    match = RANGE_REGEX.match(original_range)
    if not match:
        raise RuntimeError(f"Invalid range format - {original_range!r}.")
    start, end = match.groups()

    if not start:
        if not end:
            raise RuntimeError(f"Invalid range format - {original_range!r}.")

        new_suffix = int(end) - resume_size
        new_range = f"bytes=-{new_suffix}"
        if new_suffix <= 0:
            raise RuntimeError(f"Empty new range - {new_range!r}.")
        return new_range

    start = int(start)
    new_start = start + resume_size
    if end:
        end = int(end)
        new_range = f"bytes={new_start}-{end}"
        if new_start > end:
            raise RuntimeError(f"Empty new range - {new_range!r}.")
        return new_range

    return f"bytes={new_start}-"

# === NexusCore/openenv\Lib\site-packages\trio\testing\_memory_streams.py ===
from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from .. import _core, _util
from .._highlevel_generic import StapledStream
from ..abc import ReceiveStream, SendStream

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


AsyncHook: TypeAlias = Callable[[], Awaitable[object]]
# Would be nice to exclude awaitable here, but currently not possible.
SyncHook: TypeAlias = Callable[[], object]
SendStreamT = TypeVar("SendStreamT", bound=SendStream)
ReceiveStreamT = TypeVar("ReceiveStreamT", bound=ReceiveStream)


################################################################
# In-memory streams - Unbounded buffer version
################################################################


class _UnboundedByteQueue:
    def __init__(self) -> None:
        self._data = bytearray()
        self._closed = False
        self._lot = _core.ParkingLot()
        self._fetch_lock = _util.ConflictDetector(
            "another task is already fetching data",
        )

    # This object treats "close" as being like closing the send side of a
    # channel: so after close(), calling put() raises ClosedResourceError, and
    # calling the get() variants drains the buffer and then returns an empty
    # bytearray.
    def close(self) -> None:
        self._closed = True
        self._lot.unpark_all()

    def close_and_wipe(self) -> None:
        self._data = bytearray()
        self.close()

    def put(self, data: bytes | bytearray | memoryview) -> None:
        if self._closed:
            raise _core.ClosedResourceError("virtual connection closed")
        self._data += data
        self._lot.unpark_all()

    def _check_max_bytes(self, max_bytes: int | None) -> None:
        if max_bytes is None:
            return
        max_bytes = operator.index(max_bytes)
        if max_bytes < 1:
            raise ValueError("max_bytes must be >= 1")

    def _get_impl(self, max_bytes: int | None) -> bytearray:
        assert self._closed or self._data
        if max_bytes is None:
            max_bytes = len(self._data)
        if self._data:
            chunk = self._data[:max_bytes]
            del self._data[:max_bytes]
            assert chunk
            return chunk
        else:
            return bytearray()

    def get_nowait(self, max_bytes: int | None = None) -> bytearray:
        with self._fetch_lock:
            self._check_max_bytes(max_bytes)
            if not self._closed and not self._data:
                raise _core.WouldBlock
            return self._get_impl(max_bytes)

    async def get(self, max_bytes: int | None = None) -> bytearray:
        with self._fetch_lock:
            self._check_max_bytes(max_bytes)
            if not self._closed and not self._data:
                await self._lot.park()
            else:
                await _core.checkpoint()
            return self._get_impl(max_bytes)


@_util.final
class MemorySendStream(SendStream):
    """An in-memory :class:`~trio.abc.SendStream`.

    Args:
      send_all_hook: An async function, or None. Called from
          :meth:`send_all`. Can do whatever you like.
      wait_send_all_might_not_block_hook: An async function, or None. Called
          from :meth:`wait_send_all_might_not_block`. Can do whatever you
          like.
      close_hook: A synchronous function, or None. Called from :meth:`close`
          and :meth:`aclose`. Can do whatever you like.

    .. attribute:: send_all_hook
                   wait_send_all_might_not_block_hook
                   close_hook

       All of these hooks are also exposed as attributes on the object, and
       you can change them at any time.

    """

    def __init__(
        self,
        send_all_hook: AsyncHook | None = None,
        wait_send_all_might_not_block_hook: AsyncHook | None = None,
        close_hook: SyncHook | None = None,
    ) -> None:
        self._conflict_detector = _util.ConflictDetector(
            "another task is using this stream",
        )
        self._outgoing = _UnboundedByteQueue()
        self.send_all_hook = send_all_hook
        self.wait_send_all_might_not_block_hook = wait_send_all_might_not_block_hook
        self.close_hook = close_hook

    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        """Places the given data into the object's internal buffer, and then
        calls the :attr:`send_all_hook` (if any).

        """
        # Execute two checkpoints so we have more of a chance to detect
        # buggy user code that calls this twice at the same time.
        with self._conflict_detector:
            await _core.checkpoint()
            await _core.checkpoint()
            self._outgoing.put(data)
            if self.send_all_hook is not None:
                await self.send_all_hook()

    async def wait_send_all_might_not_block(self) -> None:
        """Calls the :attr:`wait_send_all_might_not_block_hook` (if any), and
        then returns immediately.

        """
        # Execute two checkpoints so that we have more of a chance to detect
        # buggy user code that calls this twice at the same time.
        with self._conflict_detector:
            await _core.checkpoint()
            await _core.checkpoint()
            # check for being closed:
            self._outgoing.put(b"")
            if self.wait_send_all_might_not_block_hook is not None:
                await self.wait_send_all_might_not_block_hook()

    def close(self) -> None:
        """Marks this stream as closed, and then calls the :attr:`close_hook`
        (if any).

        """
        # XXX should this cancel any pending calls to the send_all_hook and
        # wait_send_all_might_not_block_hook? Those are the only places where
        # send_all and wait_send_all_might_not_block can be blocked.
        #
        # The way we set things up, send_all_hook is memory_stream_pump, and
        # wait_send_all_might_not_block_hook is unset. memory_stream_pump is
        # synchronous. So normally, send_all and wait_send_all_might_not_block
        # cannot block at all.
        self._outgoing.close()
        if self.close_hook is not None:
            self.close_hook()

    async def aclose(self) -> None:
        """Same as :meth:`close`, but async."""
        self.close()
        await _core.checkpoint()

    async def get_data(self, max_bytes: int | None = None) -> bytearray:
        """Retrieves data from the internal buffer, blocking if necessary.

        Args:
          max_bytes (int or None): The maximum amount of data to
              retrieve. None (the default) means to retrieve all the data
              that's present (but still blocks until at least one byte is
              available).

        Returns:
          If this stream has been closed, an empty bytearray. Otherwise, the
          requested data.

        """
        return await self._outgoing.get(max_bytes)

    def get_data_nowait(self, max_bytes: int | None = None) -> bytearray:
        """Retrieves data from the internal buffer, but doesn't block.

        See :meth:`get_data` for details.

        Raises:
          trio.WouldBlock: if no data is available to retrieve.

        """
        return self._outgoing.get_nowait(max_bytes)


@_util.final
class MemoryReceiveStream(ReceiveStream):
    """An in-memory :class:`~trio.abc.ReceiveStream`.

    Args:
      receive_some_hook: An async function, or None. Called from
          :meth:`receive_some`. Can do whatever you like.
      close_hook: A synchronous function, or None. Called from :meth:`close`
          and :meth:`aclose`. Can do whatever you like.

    .. attribute:: receive_some_hook
                   close_hook

       Both hooks are also exposed as attributes on the object, and you can
       change them at any time.

    """

    def __init__(
        self,
        receive_some_hook: AsyncHook | None = None,
        close_hook: SyncHook | None = None,
    ) -> None:
        self._conflict_detector = _util.ConflictDetector(
            "another task is using this stream",
        )
        self._incoming = _UnboundedByteQueue()
        self._closed = False
        self.receive_some_hook = receive_some_hook
        self.close_hook = close_hook

    async def receive_some(self, max_bytes: int | None = None) -> bytearray:
        """Calls the :attr:`receive_some_hook` (if any), and then retrieves
        data from the internal buffer, blocking if necessary.

        """
        # Execute two checkpoints so we have more of a chance to detect
        # buggy user code that calls this twice at the same time.
        with self._conflict_detector:
            await _core.checkpoint()
            await _core.checkpoint()
            if self._closed:
                raise _core.ClosedResourceError
            if self.receive_some_hook is not None:
                await self.receive_some_hook()
            # self._incoming's closure state tracks whether we got an EOF.
            # self._closed tracks whether we, ourselves, are closed.
            # self.close() sends an EOF to wake us up and sets self._closed,
            # so after we wake up we have to check self._closed again.
            data = await self._incoming.get(max_bytes)
            if self._closed:
                raise _core.ClosedResourceError
            return data

    def close(self) -> None:
        """Discards any pending data from the internal buffer, and marks this
        stream as closed.

        """
        self._closed = True
        self._incoming.close_and_wipe()
        if self.close_hook is not None:
            self.close_hook()

    async def aclose(self) -> None:
        """Same as :meth:`close`, but async."""
        self.close()
        await _core.checkpoint()

    def put_data(self, data: bytes | bytearray | memoryview) -> None:
        """Appends the given data to the internal buffer."""
        self._incoming.put(data)

    def put_eof(self) -> None:
        """Adds an end-of-file marker to the internal buffer."""
        self._incoming.close()


# TODO: investigate why this is necessary for the docs
MemorySendStream.__module__ = MemorySendStream.__module__.replace(
    "._memory_streams", ""
)
MemoryReceiveStream.__module__ = MemoryReceiveStream.__module__.replace(
    "._memory_streams", ""
)


def memory_stream_pump(
    memory_send_stream: MemorySendStream,
    memory_receive_stream: MemoryReceiveStream,
    *,
    max_bytes: int | None = None,
) -> bool:
    """Take data out of the given :class:`MemorySendStream`'s internal buffer,
    and put it into the given :class:`MemoryReceiveStream`'s internal buffer.

    Args:
      memory_send_stream (MemorySendStream): The stream to get data from.
      memory_receive_stream (MemoryReceiveStream): The stream to put data into.
      max_bytes (int or None): The maximum amount of data to transfer in this
          call, or None to transfer all available data.

    Returns:
      True if it successfully transferred some data, or False if there was no
      data to transfer.

    This is used to implement :func:`memory_stream_one_way_pair` and
    :func:`memory_stream_pair`; see the latter's docstring for an example
    of how you might use it yourself.

    """
    try:
        data = memory_send_stream.get_data_nowait(max_bytes)
    except _core.WouldBlock:
        return False
    try:
        if not data:
            memory_receive_stream.put_eof()
        else:
            memory_receive_stream.put_data(data)
    except _core.ClosedResourceError:
        raise _core.BrokenResourceError("MemoryReceiveStream was closed") from None
    return True


def memory_stream_one_way_pair() -> tuple[MemorySendStream, MemoryReceiveStream]:
    """Create a connected, pure-Python, unidirectional stream with infinite
    buffering and flexible configuration options.

    You can think of this as being a no-operating-system-involved
    Trio-streamsified version of :func:`os.pipe` (except that :func:`os.pipe`
    returns the streams in the wrong order – we follow the superior convention
    that data flows from left to right).

    Returns:
      A tuple (:class:`MemorySendStream`, :class:`MemoryReceiveStream`), where
      the :class:`MemorySendStream` has its hooks set up so that it calls
      :func:`memory_stream_pump` from its
      :attr:`~MemorySendStream.send_all_hook` and
      :attr:`~MemorySendStream.close_hook`.

    The end result is that data automatically flows from the
    :class:`MemorySendStream` to the :class:`MemoryReceiveStream`. But you're
    also free to rearrange things however you like. For example, you can
    temporarily set the :attr:`~MemorySendStream.send_all_hook` to None if you
    want to simulate a stall in data transmission. Or see
    :func:`memory_stream_pair` for a more elaborate example.

    """
    send_stream = MemorySendStream()
    recv_stream = MemoryReceiveStream()

    def pump_from_send_stream_to_recv_stream() -> None:
        memory_stream_pump(send_stream, recv_stream)

    # await not used
    async def async_pump_from_send_stream_to_recv_stream() -> None:  # noqa: RUF029
        pump_from_send_stream_to_recv_stream()

    send_stream.send_all_hook = async_pump_from_send_stream_to_recv_stream
    send_stream.close_hook = pump_from_send_stream_to_recv_stream
    return send_stream, recv_stream


def _make_stapled_pair(
    one_way_pair: Callable[[], tuple[SendStreamT, ReceiveStreamT]],
) -> tuple[
    StapledStream[SendStreamT, ReceiveStreamT],
    StapledStream[SendStreamT, ReceiveStreamT],
]:
    pipe1_send, pipe1_recv = one_way_pair()
    pipe2_send, pipe2_recv = one_way_pair()
    stream1 = StapledStream(pipe1_send, pipe2_recv)
    stream2 = StapledStream(pipe2_send, pipe1_recv)
    return stream1, stream2


def memory_stream_pair() -> tuple[
    StapledStream[MemorySendStream, MemoryReceiveStream],
    StapledStream[MemorySendStream, MemoryReceiveStream],
]:
    """Create a connected, pure-Python, bidirectional stream with infinite
    buffering and flexible configuration options.

    This is a convenience function that creates two one-way streams using
    :func:`memory_stream_one_way_pair`, and then uses
    :class:`~trio.StapledStream` to combine them into a single bidirectional
    stream.

    This is like a no-operating-system-involved, Trio-streamsified version of
    :func:`socket.socketpair`.

    Returns:
      A pair of :class:`~trio.StapledStream` objects that are connected so
      that data automatically flows from one to the other in both directions.

    After creating a stream pair, you can send data back and forth, which is
    enough for simple tests::

       left, right = memory_stream_pair()
       await left.send_all(b"123")
       assert await right.receive_some() == b"123"
       await right.send_all(b"456")
       assert await left.receive_some() == b"456"

    But if you read the docs for :class:`~trio.StapledStream` and
    :func:`memory_stream_one_way_pair`, you'll see that all the pieces
    involved in wiring this up are public APIs, so you can adjust to suit the
    requirements of your tests. For example, here's how to tweak a stream so
    that data flowing from left to right trickles in one byte at a time (but
    data flowing from right to left proceeds at full speed)::

        left, right = memory_stream_pair()
        async def trickle():
            # left is a StapledStream, and left.send_stream is a MemorySendStream
            # right is a StapledStream, and right.recv_stream is a MemoryReceiveStream
            while memory_stream_pump(left.send_stream, right.recv_stream, max_bytes=1):
                # Pause between each byte
                await trio.sleep(1)
        # Normally this send_all_hook calls memory_stream_pump directly without
        # passing in a max_bytes. We replace it with our custom version:
        left.send_stream.send_all_hook = trickle

    And here's a simple test using our modified stream objects::

        async def sender():
            await left.send_all(b"12345")
            await left.send_eof()

        async def receiver():
            async for data in right:
                print(data)

        async with trio.open_nursery() as nursery:
            nursery.start_soon(sender)
            nursery.start_soon(receiver)

    By default, this will print ``b"12345"`` and then immediately exit; with
    our trickle stream it instead sleeps 1 second, then prints ``b"1"``, then
    sleeps 1 second, then prints ``b"2"``, etc.

    Pro-tip: you can insert sleep calls (like in our example above) to
    manipulate the flow of data across tasks... and then use
    :class:`MockClock` and its :attr:`~MockClock.autojump_threshold`
    functionality to keep your test suite running quickly.

    If you want to stress test a protocol implementation, one nice trick is to
    use the :mod:`random` module (preferably with a fixed seed) to move random
    numbers of bytes at a time, and insert random sleeps in between them. You
    can also set up a custom :attr:`~MemoryReceiveStream.receive_some_hook` if
    you want to manipulate things on the receiving side, and not just the
    sending side.

    """
    return _make_stapled_pair(memory_stream_one_way_pair)


################################################################
# In-memory streams - Lockstep version
################################################################


class _LockstepByteQueue:
    def __init__(self) -> None:
        self._data = bytearray()
        self._sender_closed = False
        self._receiver_closed = False
        self._receiver_waiting = False
        self._waiters = _core.ParkingLot()
        self._send_conflict_detector = _util.ConflictDetector(
            "another task is already sending",
        )
        self._receive_conflict_detector = _util.ConflictDetector(
            "another task is already receiving",
        )

    def _something_happened(self) -> None:
        self._waiters.unpark_all()

    # Always wakes up when one side is closed, because everyone always reacts
    # to that.
    async def _wait_for(self, fn: Callable[[], bool]) -> None:
        while True:
            if fn():
                break
            if self._sender_closed or self._receiver_closed:
                break
            await self._waiters.park()
        await _core.checkpoint()

    def close_sender(self) -> None:
        self._sender_closed = True
        self._something_happened()

    def close_receiver(self) -> None:
        self._receiver_closed = True
        self._something_happened()

    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        with self._send_conflict_detector:
            if self._sender_closed:
                raise _core.ClosedResourceError
            if self._receiver_closed:
                raise _core.BrokenResourceError
            assert not self._data
            self._data += data
            self._something_happened()
            await self._wait_for(lambda: self._data == b"")
            if self._sender_closed:
                raise _core.ClosedResourceError
            if self._data and self._receiver_closed:
                raise _core.BrokenResourceError

    async def wait_send_all_might_not_block(self) -> None:
        with self._send_conflict_detector:
            if self._sender_closed:
                raise _core.ClosedResourceError
            if self._receiver_closed:
                await _core.checkpoint()
                return
            await self._wait_for(lambda: self._receiver_waiting)
            if self._sender_closed:
                raise _core.ClosedResourceError

    async def receive_some(self, max_bytes: int | None = None) -> bytes | bytearray:
        with self._receive_conflict_detector:
            # Argument validation
            if max_bytes is not None:
                max_bytes = operator.index(max_bytes)
                if max_bytes < 1:
                    raise ValueError("max_bytes must be >= 1")
            # State validation
            if self._receiver_closed:
                raise _core.ClosedResourceError
            # Wake wait_send_all_might_not_block and wait for data
            self._receiver_waiting = True
            self._something_happened()
            try:
                await self._wait_for(lambda: self._data != b"")
            finally:
                self._receiver_waiting = False
            if self._receiver_closed:
                raise _core.ClosedResourceError
            # Get data, possibly waking send_all
            if self._data:
                # Neat trick: if max_bytes is None, then obj[:max_bytes] is
                # the same as obj[:].
                got = self._data[:max_bytes]
                del self._data[:max_bytes]
                self._something_happened()
                return got
            else:
                assert self._sender_closed
                return b""


class _LockstepSendStream(SendStream):
    def __init__(self, lbq: _LockstepByteQueue) -> None:
        self._lbq = lbq

    def close(self) -> None:
        self._lbq.close_sender()

    async def aclose(self) -> None:
        self.close()
        await _core.checkpoint()

    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        await self._lbq.send_all(data)

    async def wait_send_all_might_not_block(self) -> None:
        await self._lbq.wait_send_all_might_not_block()


class _LockstepReceiveStream(ReceiveStream):
    def __init__(self, lbq: _LockstepByteQueue) -> None:
        self._lbq = lbq

    def close(self) -> None:
        self._lbq.close_receiver()

    async def aclose(self) -> None:
        self.close()
        await _core.checkpoint()

    async def receive_some(self, max_bytes: int | None = None) -> bytes | bytearray:
        return await self._lbq.receive_some(max_bytes)


def lockstep_stream_one_way_pair() -> tuple[SendStream, ReceiveStream]:
    """Create a connected, pure Python, unidirectional stream where data flows
    in lockstep.

    Returns:
      A tuple
      (:class:`~trio.abc.SendStream`, :class:`~trio.abc.ReceiveStream`).

    This stream has *absolutely no* buffering. Each call to
    :meth:`~trio.abc.SendStream.send_all` will block until all the given data
    has been returned by a call to
    :meth:`~trio.abc.ReceiveStream.receive_some`.

    This can be useful for testing flow control mechanisms in an extreme case,
    or for setting up "clogged" streams to use with
    :func:`check_one_way_stream` and friends.

    In addition to fulfilling the :class:`~trio.abc.SendStream` and
    :class:`~trio.abc.ReceiveStream` interfaces, the return objects
    also have a synchronous ``close`` method.

    """

    lbq = _LockstepByteQueue()
    return _LockstepSendStream(lbq), _LockstepReceiveStream(lbq)


def lockstep_stream_pair() -> tuple[
    StapledStream[SendStream, ReceiveStream],
    StapledStream[SendStream, ReceiveStream],
]:
    """Create a connected, pure-Python, bidirectional stream where data flows
    in lockstep.

    Returns:
      A tuple (:class:`~trio.StapledStream`, :class:`~trio.StapledStream`).

    This is a convenience function that creates two one-way streams using
    :func:`lockstep_stream_one_way_pair`, and then uses
    :class:`~trio.StapledStream` to combine them into a single bidirectional
    stream.

    """
    return _make_stapled_pair(lockstep_stream_one_way_pair)

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\shortcuts\__init__.py ===
"""
Module to define and register Terminal IPython shortcuts with
:mod:`prompt_toolkit`
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import signal
import sys
import warnings
from dataclasses import dataclass
from typing import Callable, Any, Optional, List

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.key_binding.bindings import named_commands as nc
from prompt_toolkit.key_binding.bindings.completion import (
    display_completions_like_readline,
)
from prompt_toolkit.key_binding.vi_state import InputMode, ViState
from prompt_toolkit.filters import Condition

from IPython.core.getipython import get_ipython
from . import auto_match as match
from . import auto_suggest
from .filters import filter_from_string
from IPython.utils.decorators import undoc

from prompt_toolkit.enums import DEFAULT_BUFFER

__all__ = ["create_ipython_shortcuts"]


@dataclass
class BaseBinding:
    command: Callable[[KeyPressEvent], Any]
    keys: List[str]


@dataclass
class RuntimeBinding(BaseBinding):
    filter: Condition


@dataclass
class Binding(BaseBinding):
    # while filter could be created by referencing variables directly (rather
    # than created from strings), by using strings we ensure that users will
    # be able to create filters in configuration (e.g. JSON) files too, which
    # also benefits the documentation by enforcing human-readable filter names.
    condition: Optional[str] = None

    def __post_init__(self):
        if self.condition:
            self.filter = filter_from_string(self.condition)
        else:
            self.filter = None


def create_identifier(handler: Callable):
    parts = handler.__module__.split(".")
    name = handler.__name__
    package = parts[0]
    if len(parts) > 1:
        final_module = parts[-1]
        return f"{package}:{final_module}.{name}"
    else:
        return f"{package}:{name}"


AUTO_MATCH_BINDINGS = [
    *[
        Binding(
            cmd, [key], "focused_insert & auto_match & followed_by_closing_paren_or_end"
        )
        for key, cmd in match.auto_match_parens.items()
    ],
    *[
        # raw string
        Binding(cmd, [key], "focused_insert & auto_match & preceded_by_raw_str_prefix")
        for key, cmd in match.auto_match_parens_raw_string.items()
    ],
    Binding(
        match.double_quote,
        ['"'],
        "focused_insert"
        " & auto_match"
        " & not_inside_unclosed_string"
        " & preceded_by_paired_double_quotes"
        " & followed_by_closing_paren_or_end",
    ),
    Binding(
        match.single_quote,
        ["'"],
        "focused_insert"
        " & auto_match"
        " & not_inside_unclosed_string"
        " & preceded_by_paired_single_quotes"
        " & followed_by_closing_paren_or_end",
    ),
    Binding(
        match.docstring_double_quotes,
        ['"'],
        "focused_insert"
        " & auto_match"
        " & not_inside_unclosed_string"
        " & preceded_by_two_double_quotes",
    ),
    Binding(
        match.docstring_single_quotes,
        ["'"],
        "focused_insert"
        " & auto_match"
        " & not_inside_unclosed_string"
        " & preceded_by_two_single_quotes",
    ),
    Binding(
        match.skip_over,
        [")"],
        "focused_insert & auto_match & followed_by_closing_round_paren",
    ),
    Binding(
        match.skip_over,
        ["]"],
        "focused_insert & auto_match & followed_by_closing_bracket",
    ),
    Binding(
        match.skip_over,
        ["}"],
        "focused_insert & auto_match & followed_by_closing_brace",
    ),
    Binding(
        match.skip_over, ['"'], "focused_insert & auto_match & followed_by_double_quote"
    ),
    Binding(
        match.skip_over, ["'"], "focused_insert & auto_match & followed_by_single_quote"
    ),
    Binding(
        match.delete_pair,
        ["backspace"],
        "focused_insert"
        " & preceded_by_opening_round_paren"
        " & auto_match"
        " & followed_by_closing_round_paren",
    ),
    Binding(
        match.delete_pair,
        ["backspace"],
        "focused_insert"
        " & preceded_by_opening_bracket"
        " & auto_match"
        " & followed_by_closing_bracket",
    ),
    Binding(
        match.delete_pair,
        ["backspace"],
        "focused_insert"
        " & preceded_by_opening_brace"
        " & auto_match"
        " & followed_by_closing_brace",
    ),
    Binding(
        match.delete_pair,
        ["backspace"],
        "focused_insert"
        " & preceded_by_double_quote"
        " & auto_match"
        " & followed_by_double_quote",
    ),
    Binding(
        match.delete_pair,
        ["backspace"],
        "focused_insert"
        " & preceded_by_single_quote"
        " & auto_match"
        " & followed_by_single_quote",
    ),
]

AUTO_SUGGEST_BINDINGS = [
    # there are two reasons for re-defining bindings defined upstream:
    # 1) prompt-toolkit does not execute autosuggestion bindings in vi mode,
    # 2) prompt-toolkit checks if we are at the end of text, not end of line
    #    hence it does not work in multi-line mode of navigable provider
    Binding(
        auto_suggest.accept_or_jump_to_end,
        ["end"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept_or_jump_to_end,
        ["c-e"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept,
        ["c-f"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept,
        ["right"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode & is_cursor_at_the_end_of_line",
    ),
    Binding(
        auto_suggest.accept_word,
        ["escape", "f"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept_token,
        ["c-right"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.discard,
        ["escape"],
        # note this one is using `emacs_insert_mode`, not `emacs_like_insert_mode`
        # as in `vi_insert_mode` we do not want `escape` to be shadowed (ever).
        "has_suggestion & default_buffer_focused & emacs_insert_mode",
    ),
    Binding(
        auto_suggest.discard,
        ["delete"],
        "has_suggestion & default_buffer_focused & emacs_insert_mode",
    ),
    Binding(
        auto_suggest.swap_autosuggestion_up,
        ["c-up"],
        "navigable_suggestions"
        " & ~has_line_above"
        " & has_suggestion"
        " & default_buffer_focused",
    ),
    Binding(
        auto_suggest.swap_autosuggestion_down,
        ["c-down"],
        "navigable_suggestions"
        " & ~has_line_below"
        " & has_suggestion"
        " & default_buffer_focused",
    ),
    Binding(
        auto_suggest.up_and_update_hint,
        ["c-up"],
        "has_line_above & navigable_suggestions & default_buffer_focused",
    ),
    Binding(
        auto_suggest.down_and_update_hint,
        ["c-down"],
        "has_line_below & navigable_suggestions & default_buffer_focused",
    ),
    Binding(
        auto_suggest.accept_character,
        ["escape", "right"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept_and_move_cursor_left,
        ["c-left"],
        "has_suggestion & default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.accept_and_keep_cursor,
        ["escape", "down"],
        "has_suggestion & default_buffer_focused & emacs_insert_mode",
    ),
    Binding(
        auto_suggest.backspace_and_resume_hint,
        ["backspace"],
        # no `has_suggestion` here to allow resuming if no suggestion
        "default_buffer_focused & emacs_like_insert_mode",
    ),
    Binding(
        auto_suggest.resume_hinting,
        ["right"],
        "is_cursor_at_the_end_of_line"
        " & default_buffer_focused"
        " & emacs_like_insert_mode"
        " & pass_through",
    ),
]


SIMPLE_CONTROL_BINDINGS = [
    Binding(cmd, [key], "vi_insert_mode & default_buffer_focused & ebivim")
    for key, cmd in {
        "c-a": nc.beginning_of_line,
        "c-b": nc.backward_char,
        "c-k": nc.kill_line,
        "c-w": nc.backward_kill_word,
        "c-y": nc.yank,
        "c-_": nc.undo,
    }.items()
]


ALT_AND_COMOBO_CONTROL_BINDINGS = [
    Binding(cmd, list(keys), "vi_insert_mode & default_buffer_focused & ebivim")
    for keys, cmd in {
        # Control Combos
        ("c-x", "c-e"): nc.edit_and_execute,
        ("c-x", "e"): nc.edit_and_execute,
        # Alt
        ("escape", "b"): nc.backward_word,
        ("escape", "c"): nc.capitalize_word,
        ("escape", "d"): nc.kill_word,
        ("escape", "h"): nc.backward_kill_word,
        ("escape", "l"): nc.downcase_word,
        ("escape", "u"): nc.uppercase_word,
        ("escape", "y"): nc.yank_pop,
        ("escape", "."): nc.yank_last_arg,
    }.items()
]


def add_binding(bindings: KeyBindings, binding: Binding):
    bindings.add(
        *binding.keys,
        **({"filter": binding.filter} if binding.filter is not None else {}),
    )(binding.command)


def create_ipython_shortcuts(shell, skip=None) -> KeyBindings:
    """Set up the prompt_toolkit keyboard shortcuts for IPython.

    Parameters
    ----------
    shell: InteractiveShell
        The current IPython shell Instance
    skip: List[Binding]
        Bindings to skip.

    Returns
    -------
    KeyBindings
        the keybinding instance for prompt toolkit.

    """
    kb = KeyBindings()
    skip = skip or []
    for binding in KEY_BINDINGS:
        skip_this_one = False
        for to_skip in skip:
            if (
                to_skip.command == binding.command
                and to_skip.filter == binding.filter
                and to_skip.keys == binding.keys
            ):
                skip_this_one = True
                break
        if skip_this_one:
            continue
        add_binding(kb, binding)

    def get_input_mode(self):
        app = get_app()
        app.ttimeoutlen = shell.ttimeoutlen
        app.timeoutlen = shell.timeoutlen

        return self._input_mode

    def set_input_mode(self, mode):
        shape = {InputMode.NAVIGATION: 2, InputMode.REPLACE: 4}.get(mode, 6)
        cursor = "\x1b[{} q".format(shape)

        sys.stdout.write(cursor)
        sys.stdout.flush()

        self._input_mode = mode

    if shell.editing_mode == "vi" and shell.modal_cursor:
        ViState._input_mode = InputMode.INSERT  # type: ignore
        ViState.input_mode = property(get_input_mode, set_input_mode)  # type: ignore

    return kb


def reformat_and_execute(event):
    """Reformat code and execute it"""
    shell = get_ipython()
    reformat_text_before_cursor(
        event.current_buffer, event.current_buffer.document, shell
    )
    event.current_buffer.validate_and_handle()


def reformat_text_before_cursor(buffer, document, shell):
    text = buffer.delete_before_cursor(len(document.text[: document.cursor_position]))
    try:
        formatted_text = shell.reformat_handler(text)
        buffer.insert_text(formatted_text)
    except Exception as e:
        buffer.insert_text(text)


def handle_return_or_newline_or_execute(event):
    shell = get_ipython()
    if getattr(shell, "handle_return", None):
        return shell.handle_return(shell)(event)
    else:
        return newline_or_execute_outer(shell)(event)


def newline_or_execute_outer(shell):
    def newline_or_execute(event):
        """When the user presses return, insert a newline or execute the code."""
        b = event.current_buffer
        d = b.document

        if b.complete_state:
            cc = b.complete_state.current_completion
            if cc:
                b.apply_completion(cc)
            else:
                b.cancel_completion()
            return

        # If there's only one line, treat it as if the cursor is at the end.
        # See https://github.com/ipython/ipython/issues/10425
        if d.line_count == 1:
            check_text = d.text
        else:
            check_text = d.text[: d.cursor_position]
        status, indent = shell.check_complete(check_text)

        # if all we have after the cursor is whitespace: reformat current text
        # before cursor
        after_cursor = d.text[d.cursor_position :]
        reformatted = False
        if not after_cursor.strip():
            reformat_text_before_cursor(b, d, shell)
            reformatted = True
        if not (
            d.on_last_line
            or d.cursor_position_row >= d.line_count - d.empty_line_count_at_the_end()
        ):
            if shell.autoindent:
                b.insert_text("\n" + indent)
            else:
                b.insert_text("\n")
            return

        if (status != "incomplete") and b.accept_handler:
            if not reformatted:
                reformat_text_before_cursor(b, d, shell)
            b.validate_and_handle()
        else:
            if shell.autoindent:
                b.insert_text("\n" + indent)
            else:
                b.insert_text("\n")

    return newline_or_execute


def previous_history_or_previous_completion(event):
    """
    Control-P in vi edit mode on readline is history next, unlike default prompt toolkit.

    If completer is open this still select previous completion.
    """
    event.current_buffer.auto_up()


def next_history_or_next_completion(event):
    """
    Control-N in vi edit mode on readline is history previous, unlike default prompt toolkit.

    If completer is open this still select next completion.
    """
    event.current_buffer.auto_down()


def dismiss_completion(event):
    """Dismiss completion"""
    b = event.current_buffer
    if b.complete_state:
        b.cancel_completion()


def reset_buffer(event):
    """Reset buffer"""
    b = event.current_buffer
    if b.complete_state:
        b.cancel_completion()
    else:
        b.reset()


def reset_search_buffer(event):
    """Reset search buffer"""
    if event.current_buffer.document.text:
        event.current_buffer.reset()
    else:
        event.app.layout.focus(DEFAULT_BUFFER)


def suspend_to_bg(event):
    """Suspend to background"""
    event.app.suspend_to_background()


def quit(event):
    """
    Quit application with ``SIGQUIT`` if supported or ``sys.exit`` otherwise.

    On platforms that support SIGQUIT, send SIGQUIT to the current process.
    On other platforms, just exit the process with a message.
    """
    sigquit = getattr(signal, "SIGQUIT", None)
    if sigquit is not None:
        os.kill(0, signal.SIGQUIT)
    else:
        sys.exit("Quit")


def indent_buffer(event):
    """Indent buffer"""
    event.current_buffer.insert_text(" " * 4)


def newline_autoindent(event):
    """Insert a newline after the cursor indented appropriately.

    Fancier version of former ``newline_with_copy_margin`` which should
    compute the correct indentation of the inserted line. That is to say, indent
    by 4 extra space after a function definition, class definition, context
    manager... And dedent by 4 space after ``pass``, ``return``, ``raise ...``.
    """
    shell = get_ipython()
    inputsplitter = shell.input_transformer_manager
    b = event.current_buffer
    d = b.document

    if b.complete_state:
        b.cancel_completion()
    text = d.text[: d.cursor_position] + "\n"
    _, indent = inputsplitter.check_complete(text)
    b.insert_text("\n" + (" " * (indent or 0)), move_cursor=False)


def open_input_in_editor(event):
    """Open code from input in external editor"""
    event.app.current_buffer.open_in_editor()


if sys.platform == "win32":
    from IPython.core.error import TryNext
    from IPython.lib.clipboard import (
        ClipboardEmpty,
        tkinter_clipboard_get,
        win32_clipboard_get,
    )

    @undoc
    def win_paste(event):
        try:
            text = win32_clipboard_get()
        except TryNext:
            try:
                text = tkinter_clipboard_get()
            except (TryNext, ClipboardEmpty):
                return
        except ClipboardEmpty:
            return
        event.current_buffer.insert_text(text.replace("\t", " " * 4))

else:

    @undoc
    def win_paste(event):
        """Stub used on other platforms"""
        pass


KEY_BINDINGS = [
    Binding(
        handle_return_or_newline_or_execute,
        ["enter"],
        "default_buffer_focused & ~has_selection & insert_mode",
    ),
    Binding(
        reformat_and_execute,
        ["escape", "enter"],
        "default_buffer_focused & ~has_selection & insert_mode & ebivim",
    ),
    Binding(quit, ["c-\\"]),
    Binding(
        previous_history_or_previous_completion,
        ["c-p"],
        "vi_insert_mode & default_buffer_focused",
    ),
    Binding(
        next_history_or_next_completion,
        ["c-n"],
        "vi_insert_mode & default_buffer_focused",
    ),
    Binding(dismiss_completion, ["c-g"], "default_buffer_focused & has_completions"),
    Binding(reset_buffer, ["c-c"], "default_buffer_focused"),
    Binding(reset_search_buffer, ["c-c"], "search_buffer_focused"),
    Binding(suspend_to_bg, ["c-z"], "supports_suspend"),
    Binding(
        indent_buffer,
        ["tab"],  # Ctrl+I == Tab
        "default_buffer_focused & ~has_selection & insert_mode & cursor_in_leading_ws",
    ),
    Binding(newline_autoindent, ["c-o"], "default_buffer_focused & emacs_insert_mode"),
    Binding(open_input_in_editor, ["f2"], "default_buffer_focused"),
    *AUTO_MATCH_BINDINGS,
    *AUTO_SUGGEST_BINDINGS,
    Binding(
        display_completions_like_readline,
        ["c-i"],
        "readline_like_completions"
        " & default_buffer_focused"
        " & ~has_selection"
        " & insert_mode"
        " & ~cursor_in_leading_ws",
    ),
    Binding(win_paste, ["c-v"], "default_buffer_focused & ~vi_mode & is_windows_os"),
    *SIMPLE_CONTROL_BINDINGS,
    *ALT_AND_COMOBO_CONTROL_BINDINGS,
]

UNASSIGNED_ALLOWED_COMMANDS = [
    auto_suggest.llm_autosuggestion,
    nc.beginning_of_buffer,
    nc.end_of_buffer,
    nc.end_of_line,
    nc.forward_word,
    nc.unix_line_discard,
]

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\chat\invoke_transformations\base_invoke_transformation.py ===
import copy
import json
import time
import urllib.parse
from functools import partial
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast, get_args

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.litellm_core_utils.logging_utils import track_llm_api_timing
from litellm.litellm_core_utils.prompt_templates.factory import (
    cohere_message_pt,
    custom_prompt,
    deepseek_r1_pt,
    prompt_factory,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.llms.bedrock.chat.invoke_handler import make_call, make_sync_call
from litellm.llms.bedrock.common_utils import BedrockError
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse, Usage
from litellm.utils import CustomStreamWrapper

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any

from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM


class AmazonInvokeConfig(BaseConfig, BaseAWSLLM):
    def __init__(self, **kwargs):
        BaseConfig.__init__(self, **kwargs)
        BaseAWSLLM.__init__(self, **kwargs)

    def get_supported_openai_params(self, model: str) -> List[str]:
        """
        This is a base invoke model mapping. For Invoke - define a bedrock provider specific config that extends this class.
        """
        return [
            "max_tokens",
            "max_completion_tokens",
            "stream",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        This is a base invoke model mapping. For Invoke - define a bedrock provider specific config that extends this class.
        """
        for param, value in non_default_params.items():
            if param == "max_tokens" or param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            if param == "stream":
                optional_params["stream"] = value
        return optional_params

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
        Get the complete url for the request
        """
        provider = self.get_bedrock_invoke_provider(model)
        modelId = self.get_bedrock_model_id(
            model=model,
            provider=provider,
            optional_params=optional_params,
        )
        ### SET RUNTIME ENDPOINT ###
        aws_bedrock_runtime_endpoint = optional_params.get(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        endpoint_url, proxy_endpoint_url = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=aws_bedrock_runtime_endpoint,
            aws_region_name=self._get_aws_region_name(
                optional_params=optional_params, model=model
            ),
        )

        if (stream is not None and stream is True) and provider != "ai21":
            endpoint_url = f"{endpoint_url}/model/{modelId}/invoke-with-response-stream"
            proxy_endpoint_url = (
                f"{proxy_endpoint_url}/model/{modelId}/invoke-with-response-stream"
            )
        else:
            endpoint_url = f"{endpoint_url}/model/{modelId}/invoke"
            proxy_endpoint_url = f"{proxy_endpoint_url}/model/{modelId}/invoke"

        return endpoint_url

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
        return self._sign_request(
            service_name="bedrock",
            headers=headers,
            optional_params=optional_params,
            request_data=request_data,
            api_base=api_base,
            model=model,
            stream=stream,
            fake_stream=fake_stream,
        )

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        ## SETUP ##
        stream = optional_params.pop("stream", None)
        custom_prompt_dict: dict = litellm_params.pop("custom_prompt_dict", None) or {}
        hf_model_name = litellm_params.get("hf_model_name", None)

        provider = self.get_bedrock_invoke_provider(model)

        prompt, chat_history = self.convert_messages_to_prompt(
            model=hf_model_name or model,
            messages=messages,
            provider=provider,
            custom_prompt_dict=custom_prompt_dict,
        )
        inference_params = copy.deepcopy(optional_params)
        inference_params = {
            k: v
            for k, v in inference_params.items()
            if k not in self.aws_authentication_params
        }
        request_data: dict = {}
        if provider == "cohere":
            if model.startswith("cohere.command-r"):
                ## LOAD CONFIG
                config = litellm.AmazonCohereChatConfig().get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                _data = {"message": prompt, **inference_params}
                if chat_history is not None:
                    _data["chat_history"] = chat_history
                request_data = _data
            else:
                ## LOAD CONFIG
                config = litellm.AmazonCohereConfig.get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                if stream is True:
                    inference_params[
                        "stream"
                    ] = True  # cohere requires stream = True in inference params
                request_data = {"prompt": prompt, **inference_params}
        elif provider == "anthropic":
            return litellm.AmazonAnthropicClaude3Config().transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                headers=headers,
            )
        elif provider == "nova":
            return litellm.AmazonInvokeNovaConfig().transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                headers=headers,
            )
        elif provider == "ai21":
            ## LOAD CONFIG
            config = litellm.AmazonAI21Config.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            request_data = {"prompt": prompt, **inference_params}
        elif provider == "mistral":
            ## LOAD CONFIG
            config = litellm.AmazonMistralConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > amazon_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            request_data = {"prompt": prompt, **inference_params}
        elif provider == "amazon":  # amazon titan
            ## LOAD CONFIG
            config = litellm.AmazonTitanConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > amazon_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            request_data = {
                "inputText": prompt,
                "textGenerationConfig": inference_params,
            }
        elif provider == "meta" or provider == "llama" or provider == "deepseek_r1":
            ## LOAD CONFIG
            config = litellm.AmazonLlamaConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v
            request_data = {"prompt": prompt, **inference_params}
        else:
            raise BedrockError(
                status_code=404,
                message="Bedrock Invoke HTTPX: Unknown provider={}, model={}. Try calling via converse route - `bedrock/converse/<model>`.".format(
                    provider, model
                ),
            )

        return request_data

    def transform_response(  # noqa: PLR0915
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            completion_response = raw_response.json()
        except Exception:
            raise BedrockError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        verbose_logger.debug(
            "bedrock invoke response % s",
            json.dumps(completion_response, indent=4, default=str),
        )
        provider = self.get_bedrock_invoke_provider(model)
        outputText: Optional[str] = None
        try:
            if provider == "cohere":
                if "text" in completion_response:
                    outputText = completion_response["text"]  # type: ignore
                elif "generations" in completion_response:
                    outputText = completion_response["generations"][0]["text"]
                    model_response.choices[0].finish_reason = map_finish_reason(
                        completion_response["generations"][0]["finish_reason"]
                    )
            elif provider == "anthropic":
                return litellm.AmazonAnthropicClaude3Config().transform_response(
                    model=model,
                    raw_response=raw_response,
                    model_response=model_response,
                    logging_obj=logging_obj,
                    request_data=request_data,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    encoding=encoding,
                    api_key=api_key,
                    json_mode=json_mode,
                )
            elif provider == "nova":
                return litellm.AmazonInvokeNovaConfig().transform_response(
                    model=model,
                    raw_response=raw_response,
                    model_response=model_response,
                    logging_obj=logging_obj,
                    request_data=request_data,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    encoding=encoding,
                )
            elif provider == "ai21":
                outputText = (
                    completion_response.get("completions")[0].get("data").get("text")
                )
            elif provider == "meta" or provider == "llama" or provider == "deepseek_r1":
                outputText = completion_response["generation"]
            elif provider == "mistral":
                outputText = litellm.AmazonMistralConfig.get_outputText(completion_response, model_response)
            else:  # amazon titan
                outputText = completion_response.get("results")[0].get("outputText")
        except Exception as e:
            raise BedrockError(
                message="Error processing={}, Received error={}".format(
                    raw_response.text, str(e)
                ),
                status_code=422,
            )

        try:
            if (
                outputText is not None
                and len(outputText) > 0
                and hasattr(model_response.choices[0], "message")
                and getattr(model_response.choices[0].message, "tool_calls", None)  # type: ignore
                is None
            ):
                model_response.choices[0].message.content = outputText  # type: ignore
            elif (
                hasattr(model_response.choices[0], "message")
                and getattr(model_response.choices[0].message, "tool_calls", None)  # type: ignore
                is not None
            ):
                pass
            else:
                raise Exception()
        except Exception as e:
            raise BedrockError(
                message="Error parsing received text={}.\nError-{}".format(
                    outputText, str(e)
                ),
                status_code=raw_response.status_code,
            )

        ## CALCULATING USAGE - bedrock returns usage in the headers
        bedrock_input_tokens = raw_response.headers.get(
            "x-amzn-bedrock-input-token-count", None
        )
        bedrock_output_tokens = raw_response.headers.get(
            "x-amzn-bedrock-output-token-count", None
        )

        prompt_tokens = int(
            bedrock_input_tokens or litellm.token_counter(messages=messages)
        )

        completion_tokens = int(
            bedrock_output_tokens
            or litellm.token_counter(
                text=model_response.choices[0].message.content,  # type: ignore
                count_response_tokens=True,
            )
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
        return headers

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return BedrockError(status_code=status_code, message=error_message)

    @track_llm_api_timing()
    async def get_async_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[AsyncHTTPHandler] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> CustomStreamWrapper:
        streaming_response = CustomStreamWrapper(
            completion_stream=None,
            make_call=partial(
                make_call,
                client=client,
                api_base=api_base,
                headers=headers,
                data=json.dumps(data),
                model=model,
                messages=messages,
                logging_obj=logging_obj,
                fake_stream=True if "ai21" in api_base else False,
                bedrock_invoke_provider=self.get_bedrock_invoke_provider(model),
                json_mode=json_mode,
            ),
            model=model,
            custom_llm_provider="bedrock",
            logging_obj=logging_obj,
        )
        return streaming_response

    @track_llm_api_timing()
    def get_sync_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> CustomStreamWrapper:
        if client is None or isinstance(client, AsyncHTTPHandler):
            client = _get_httpx_client(params={})
        streaming_response = CustomStreamWrapper(
            completion_stream=None,
            make_call=partial(
                make_sync_call,
                client=client,
                api_base=api_base,
                headers=headers,
                data=json.dumps(data),
                signed_json_body=signed_json_body,
                model=model,
                messages=messages,
                logging_obj=logging_obj,
                fake_stream=True if "ai21" in api_base else False,
                bedrock_invoke_provider=self.get_bedrock_invoke_provider(model),
                json_mode=json_mode,
            ),
            model=model,
            custom_llm_provider="bedrock",
            logging_obj=logging_obj,
        )
        return streaming_response

    @property
    def has_custom_stream_wrapper(self) -> bool:
        return True

    @property
    def supports_stream_param_in_request_body(self) -> bool:
        """
        Bedrock invoke does not allow passing `stream` in the request body.
        """
        return False

    @staticmethod
    def get_bedrock_invoke_provider(
        model: str,
    ) -> Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL]:
        """
        Helper function to get the bedrock provider from the model

        handles 4 scenarios:
        1. model=invoke/anthropic.claude-3-5-sonnet-20240620-v1:0 -> Returns `anthropic`
        2. model=anthropic.claude-3-5-sonnet-20240620-v1:0 -> Returns `anthropic`
        3. model=llama/arn:aws:bedrock:us-east-1:086734376398:imported-model/r4c4kewx2s0n -> Returns `llama`
        4. model=us.amazon.nova-pro-v1:0 -> Returns `nova`
        """
        if model.startswith("invoke/"):
            model = model.replace("invoke/", "", 1)

        _split_model = model.split(".")[0]
        if _split_model in get_args(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL):
            return cast(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL, _split_model)

        # If not a known provider, check for pattern with two slashes
        provider = AmazonInvokeConfig._get_provider_from_model_path(model)
        if provider is not None:
            return provider

        # check if provider == "nova"
        if "nova" in model:
            return "nova"

        for provider in get_args(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL):
            if provider in model:
                return provider
        return None

    @staticmethod
    def _get_provider_from_model_path(
        model_path: str,
    ) -> Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL]:
        """
        Helper function to get the provider from a model path with format: provider/model-name

        Args:
            model_path (str): The model path (e.g., 'llama/arn:aws:bedrock:us-east-1:086734376398:imported-model/r4c4kewx2s0n' or 'anthropic/model-name')

        Returns:
            Optional[str]: The provider name, or None if no valid provider found
        """
        parts = model_path.split("/")
        if len(parts) >= 1:
            provider = parts[0]
            if provider in get_args(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL):
                return cast(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL, provider)
        return None

    def get_bedrock_model_id(
        self,
        optional_params: dict,
        provider: Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL],
        model: str,
    ) -> str:
        modelId = optional_params.pop("model_id", None)
        if modelId is not None:
            modelId = self.encode_model_id(model_id=modelId)
        else:
            modelId = model

        modelId = modelId.replace("invoke/", "", 1)
        if provider == "llama" and "llama/" in modelId:
            modelId = self._get_model_id_from_model_with_spec(modelId, spec="llama")
        elif provider == "deepseek_r1" and "deepseek_r1/" in modelId:
            modelId = self._get_model_id_from_model_with_spec(
                modelId, spec="deepseek_r1"
            )
        return modelId

    def _get_model_id_from_model_with_spec(
        self,
        model: str,
        spec: str,
    ) -> str:
        """
        Remove `llama` from modelID since `llama` is simply a spec to follow for custom bedrock models
        """
        model_id = model.replace(spec + "/", "")
        return self.encode_model_id(model_id=model_id)

    def encode_model_id(self, model_id: str) -> str:
        """
        Double encode the model ID to ensure it matches the expected double-encoded format.
        Args:
            model_id (str): The model ID to encode.
        Returns:
            str: The double-encoded model ID.
        """
        return urllib.parse.quote(model_id, safe="")

    def convert_messages_to_prompt(
        self, model, messages, provider, custom_prompt_dict
    ) -> Tuple[str, Optional[list]]:
        # handle anthropic prompts and amazon titan prompts
        prompt = ""
        chat_history: Optional[list] = None
        ## CUSTOM PROMPT
        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details["roles"],
                initial_prompt_value=model_prompt_details.get(
                    "initial_prompt_value", ""
                ),
                final_prompt_value=model_prompt_details.get("final_prompt_value", ""),
                messages=messages,
            )
            return prompt, None
        ## ELSE
        if provider == "anthropic" or provider == "amazon":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "mistral":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "meta" or provider == "llama":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "cohere":
            prompt, chat_history = cohere_message_pt(messages=messages)
        elif provider == "deepseek_r1":
            prompt = deepseek_r1_pt(messages=messages)
        else:
            prompt = ""
            for message in messages:
                if "role" in message:
                    if message["role"] == "user":
                        prompt += f"{message['content']}"
                    else:
                        prompt += f"{message['content']}"
                else:
                    prompt += f"{message['content']}"
        return prompt, chat_history  # type: ignore

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\md.py ===
from __future__ import annotations

from functools import lru_cache
from logging import getLogger

from .constant import (
    COMMON_SAFE_ASCII_CHARACTERS,
    TRACE,
    UNICODE_SECONDARY_RANGE_KEYWORD,
)
from .utils import (
    is_accentuated,
    is_arabic,
    is_arabic_isolated_form,
    is_case_variable,
    is_cjk,
    is_emoticon,
    is_hangul,
    is_hiragana,
    is_katakana,
    is_latin,
    is_punctuation,
    is_separator,
    is_symbol,
    is_thai,
    is_unprintable,
    remove_accent,
    unicode_range,
    is_cjk_uncommon,
)


class MessDetectorPlugin:
    """
    Base abstract class used for mess detection plugins.
    All detectors MUST extend and implement given methods.
    """

    def eligible(self, character: str) -> bool:
        """
        Determine if given character should be fed in.
        """
        raise NotImplementedError  # pragma: nocover

    def feed(self, character: str) -> None:
        """
        The main routine to be executed upon character.
        Insert the logic in witch the text would be considered chaotic.
        """
        raise NotImplementedError  # pragma: nocover

    def reset(self) -> None:  # pragma: no cover
        """
        Permit to reset the plugin to the initial state.
        """
        raise NotImplementedError

    @property
    def ratio(self) -> float:
        """
        Compute the chaos ratio based on what your feed() has seen.
        Must NOT be lower than 0.; No restriction gt 0.
        """
        raise NotImplementedError  # pragma: nocover


class TooManySymbolOrPunctuationPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._punctuation_count: int = 0
        self._symbol_count: int = 0
        self._character_count: int = 0

        self._last_printable_char: str | None = None
        self._frenzy_symbol_in_word: bool = False

    def eligible(self, character: str) -> bool:
        return character.isprintable()

    def feed(self, character: str) -> None:
        self._character_count += 1

        if (
            character != self._last_printable_char
            and character not in COMMON_SAFE_ASCII_CHARACTERS
        ):
            if is_punctuation(character):
                self._punctuation_count += 1
            elif (
                character.isdigit() is False
                and is_symbol(character)
                and is_emoticon(character) is False
            ):
                self._symbol_count += 2

        self._last_printable_char = character

    def reset(self) -> None:  # Abstract
        self._punctuation_count = 0
        self._character_count = 0
        self._symbol_count = 0

    @property
    def ratio(self) -> float:
        if self._character_count == 0:
            return 0.0

        ratio_of_punctuation: float = (
            self._punctuation_count + self._symbol_count
        ) / self._character_count

        return ratio_of_punctuation if ratio_of_punctuation >= 0.3 else 0.0


class TooManyAccentuatedPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._character_count: int = 0
        self._accentuated_count: int = 0

    def eligible(self, character: str) -> bool:
        return character.isalpha()

    def feed(self, character: str) -> None:
        self._character_count += 1

        if is_accentuated(character):
            self._accentuated_count += 1

    def reset(self) -> None:  # Abstract
        self._character_count = 0
        self._accentuated_count = 0

    @property
    def ratio(self) -> float:
        if self._character_count < 8:
            return 0.0

        ratio_of_accentuation: float = self._accentuated_count / self._character_count
        return ratio_of_accentuation if ratio_of_accentuation >= 0.35 else 0.0


class UnprintablePlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._unprintable_count: int = 0
        self._character_count: int = 0

    def eligible(self, character: str) -> bool:
        return True

    def feed(self, character: str) -> None:
        if is_unprintable(character):
            self._unprintable_count += 1
        self._character_count += 1

    def reset(self) -> None:  # Abstract
        self._unprintable_count = 0

    @property
    def ratio(self) -> float:
        if self._character_count == 0:
            return 0.0

        return (self._unprintable_count * 8) / self._character_count


class SuspiciousDuplicateAccentPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._successive_count: int = 0
        self._character_count: int = 0

        self._last_latin_character: str | None = None

    def eligible(self, character: str) -> bool:
        return character.isalpha() and is_latin(character)

    def feed(self, character: str) -> None:
        self._character_count += 1
        if (
            self._last_latin_character is not None
            and is_accentuated(character)
            and is_accentuated(self._last_latin_character)
        ):
            if character.isupper() and self._last_latin_character.isupper():
                self._successive_count += 1
            # Worse if its the same char duplicated with different accent.
            if remove_accent(character) == remove_accent(self._last_latin_character):
                self._successive_count += 1
        self._last_latin_character = character

    def reset(self) -> None:  # Abstract
        self._successive_count = 0
        self._character_count = 0
        self._last_latin_character = None

    @property
    def ratio(self) -> float:
        if self._character_count == 0:
            return 0.0

        return (self._successive_count * 2) / self._character_count


class SuspiciousRange(MessDetectorPlugin):
    def __init__(self) -> None:
        self._suspicious_successive_range_count: int = 0
        self._character_count: int = 0
        self._last_printable_seen: str | None = None

    def eligible(self, character: str) -> bool:
        return character.isprintable()

    def feed(self, character: str) -> None:
        self._character_count += 1

        if (
            character.isspace()
            or is_punctuation(character)
            or character in COMMON_SAFE_ASCII_CHARACTERS
        ):
            self._last_printable_seen = None
            return

        if self._last_printable_seen is None:
            self._last_printable_seen = character
            return

        unicode_range_a: str | None = unicode_range(self._last_printable_seen)
        unicode_range_b: str | None = unicode_range(character)

        if is_suspiciously_successive_range(unicode_range_a, unicode_range_b):
            self._suspicious_successive_range_count += 1

        self._last_printable_seen = character

    def reset(self) -> None:  # Abstract
        self._character_count = 0
        self._suspicious_successive_range_count = 0
        self._last_printable_seen = None

    @property
    def ratio(self) -> float:
        if self._character_count <= 13:
            return 0.0

        ratio_of_suspicious_range_usage: float = (
            self._suspicious_successive_range_count * 2
        ) / self._character_count

        return ratio_of_suspicious_range_usage


class SuperWeirdWordPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._word_count: int = 0
        self._bad_word_count: int = 0
        self._foreign_long_count: int = 0

        self._is_current_word_bad: bool = False
        self._foreign_long_watch: bool = False

        self._character_count: int = 0
        self._bad_character_count: int = 0

        self._buffer: str = ""
        self._buffer_accent_count: int = 0
        self._buffer_glyph_count: int = 0

    def eligible(self, character: str) -> bool:
        return True

    def feed(self, character: str) -> None:
        if character.isalpha():
            self._buffer += character
            if is_accentuated(character):
                self._buffer_accent_count += 1
            if (
                self._foreign_long_watch is False
                and (is_latin(character) is False or is_accentuated(character))
                and is_cjk(character) is False
                and is_hangul(character) is False
                and is_katakana(character) is False
                and is_hiragana(character) is False
                and is_thai(character) is False
            ):
                self._foreign_long_watch = True
            if (
                is_cjk(character)
                or is_hangul(character)
                or is_katakana(character)
                or is_hiragana(character)
                or is_thai(character)
            ):
                self._buffer_glyph_count += 1
            return
        if not self._buffer:
            return
        if (
            character.isspace() or is_punctuation(character) or is_separator(character)
        ) and self._buffer:
            self._word_count += 1
            buffer_length: int = len(self._buffer)

            self._character_count += buffer_length

            if buffer_length >= 4:
                if self._buffer_accent_count / buffer_length >= 0.5:
                    self._is_current_word_bad = True
                # Word/Buffer ending with an upper case accentuated letter are so rare,
                # that we will consider them all as suspicious. Same weight as foreign_long suspicious.
                elif (
                    is_accentuated(self._buffer[-1])
                    and self._buffer[-1].isupper()
                    and all(_.isupper() for _ in self._buffer) is False
                ):
                    self._foreign_long_count += 1
                    self._is_current_word_bad = True
                elif self._buffer_glyph_count == 1:
                    self._is_current_word_bad = True
                    self._foreign_long_count += 1
            if buffer_length >= 24 and self._foreign_long_watch:
                camel_case_dst = [
                    i
                    for c, i in zip(self._buffer, range(0, buffer_length))
                    if c.isupper()
                ]
                probable_camel_cased: bool = False

                if camel_case_dst and (len(camel_case_dst) / buffer_length <= 0.3):
                    probable_camel_cased = True

                if not probable_camel_cased:
                    self._foreign_long_count += 1
                    self._is_current_word_bad = True

            if self._is_current_word_bad:
                self._bad_word_count += 1
                self._bad_character_count += len(self._buffer)
                self._is_current_word_bad = False

            self._foreign_long_watch = False
            self._buffer = ""
            self._buffer_accent_count = 0
            self._buffer_glyph_count = 0
        elif (
            character not in {"<", ">", "-", "=", "~", "|", "_"}
            and character.isdigit() is False
            and is_symbol(character)
        ):
            self._is_current_word_bad = True
            self._buffer += character

    def reset(self) -> None:  # Abstract
        self._buffer = ""
        self._is_current_word_bad = False
        self._foreign_long_watch = False
        self._bad_word_count = 0
        self._word_count = 0
        self._character_count = 0
        self._bad_character_count = 0
        self._foreign_long_count = 0

    @property
    def ratio(self) -> float:
        if self._word_count <= 10 and self._foreign_long_count == 0:
            return 0.0

        return self._bad_character_count / self._character_count


class CjkUncommonPlugin(MessDetectorPlugin):
    """
    Detect messy CJK text that probably means nothing.
    """

    def __init__(self) -> None:
        self._character_count: int = 0
        self._uncommon_count: int = 0

    def eligible(self, character: str) -> bool:
        return is_cjk(character)

    def feed(self, character: str) -> None:
        self._character_count += 1

        if is_cjk_uncommon(character):
            self._uncommon_count += 1
            return

    def reset(self) -> None:  # Abstract
        self._character_count = 0
        self._uncommon_count = 0

    @property
    def ratio(self) -> float:
        if self._character_count < 8:
            return 0.0

        uncommon_form_usage: float = self._uncommon_count / self._character_count

        # we can be pretty sure it's garbage when uncommon characters are widely
        # used. otherwise it could just be traditional chinese for example.
        return uncommon_form_usage / 10 if uncommon_form_usage > 0.5 else 0.0


class ArchaicUpperLowerPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._buf: bool = False

        self._character_count_since_last_sep: int = 0

        self._successive_upper_lower_count: int = 0
        self._successive_upper_lower_count_final: int = 0

        self._character_count: int = 0

        self._last_alpha_seen: str | None = None
        self._current_ascii_only: bool = True

    def eligible(self, character: str) -> bool:
        return True

    def feed(self, character: str) -> None:
        is_concerned = character.isalpha() and is_case_variable(character)
        chunk_sep = is_concerned is False

        if chunk_sep and self._character_count_since_last_sep > 0:
            if (
                self._character_count_since_last_sep <= 64
                and character.isdigit() is False
                and self._current_ascii_only is False
            ):
                self._successive_upper_lower_count_final += (
                    self._successive_upper_lower_count
                )

            self._successive_upper_lower_count = 0
            self._character_count_since_last_sep = 0
            self._last_alpha_seen = None
            self._buf = False
            self._character_count += 1
            self._current_ascii_only = True

            return

        if self._current_ascii_only is True and character.isascii() is False:
            self._current_ascii_only = False

        if self._last_alpha_seen is not None:
            if (character.isupper() and self._last_alpha_seen.islower()) or (
                character.islower() and self._last_alpha_seen.isupper()
            ):
                if self._buf is True:
                    self._successive_upper_lower_count += 2
                    self._buf = False
                else:
                    self._buf = True
            else:
                self._buf = False

        self._character_count += 1
        self._character_count_since_last_sep += 1
        self._last_alpha_seen = character

    def reset(self) -> None:  # Abstract
        self._character_count = 0
        self._character_count_since_last_sep = 0
        self._successive_upper_lower_count = 0
        self._successive_upper_lower_count_final = 0
        self._last_alpha_seen = None
        self._buf = False
        self._current_ascii_only = True

    @property
    def ratio(self) -> float:
        if self._character_count == 0:
            return 0.0

        return self._successive_upper_lower_count_final / self._character_count


class ArabicIsolatedFormPlugin(MessDetectorPlugin):
    def __init__(self) -> None:
        self._character_count: int = 0
        self._isolated_form_count: int = 0

    def reset(self) -> None:  # Abstract
        self._character_count = 0
        self._isolated_form_count = 0

    def eligible(self, character: str) -> bool:
        return is_arabic(character)

    def feed(self, character: str) -> None:
        self._character_count += 1

        if is_arabic_isolated_form(character):
            self._isolated_form_count += 1

    @property
    def ratio(self) -> float:
        if self._character_count < 8:
            return 0.0

        isolated_form_usage: float = self._isolated_form_count / self._character_count

        return isolated_form_usage


@lru_cache(maxsize=1024)
def is_suspiciously_successive_range(
    unicode_range_a: str | None, unicode_range_b: str | None
) -> bool:
    """
    Determine if two Unicode range seen next to each other can be considered as suspicious.
    """
    if unicode_range_a is None or unicode_range_b is None:
        return True

    if unicode_range_a == unicode_range_b:
        return False

    if "Latin" in unicode_range_a and "Latin" in unicode_range_b:
        return False

    if "Emoticons" in unicode_range_a or "Emoticons" in unicode_range_b:
        return False

    # Latin characters can be accompanied with a combining diacritical mark
    # eg. Vietnamese.
    if ("Latin" in unicode_range_a or "Latin" in unicode_range_b) and (
        "Combining" in unicode_range_a or "Combining" in unicode_range_b
    ):
        return False

    keywords_range_a, keywords_range_b = (
        unicode_range_a.split(" "),
        unicode_range_b.split(" "),
    )

    for el in keywords_range_a:
        if el in UNICODE_SECONDARY_RANGE_KEYWORD:
            continue
        if el in keywords_range_b:
            return False

    # Japanese Exception
    range_a_jp_chars, range_b_jp_chars = (
        unicode_range_a
        in (
            "Hiragana",
            "Katakana",
        ),
        unicode_range_b in ("Hiragana", "Katakana"),
    )
    if (range_a_jp_chars or range_b_jp_chars) and (
        "CJK" in unicode_range_a or "CJK" in unicode_range_b
    ):
        return False
    if range_a_jp_chars and range_b_jp_chars:
        return False

    if "Hangul" in unicode_range_a or "Hangul" in unicode_range_b:
        if "CJK" in unicode_range_a or "CJK" in unicode_range_b:
            return False
        if unicode_range_a == "Basic Latin" or unicode_range_b == "Basic Latin":
            return False

    # Chinese/Japanese use dedicated range for punctuation and/or separators.
    if ("CJK" in unicode_range_a or "CJK" in unicode_range_b) or (
        unicode_range_a in ["Katakana", "Hiragana"]
        and unicode_range_b in ["Katakana", "Hiragana"]
    ):
        if "Punctuation" in unicode_range_a or "Punctuation" in unicode_range_b:
            return False
        if "Forms" in unicode_range_a or "Forms" in unicode_range_b:
            return False
        if unicode_range_a == "Basic Latin" or unicode_range_b == "Basic Latin":
            return False

    return True


@lru_cache(maxsize=2048)
def mess_ratio(
    decoded_sequence: str, maximum_threshold: float = 0.2, debug: bool = False
) -> float:
    """
    Compute a mess ratio given a decoded bytes sequence. The maximum threshold does stop the computation earlier.
    """

    detectors: list[MessDetectorPlugin] = [
        md_class() for md_class in MessDetectorPlugin.__subclasses__()
    ]

    length: int = len(decoded_sequence) + 1

    mean_mess_ratio: float = 0.0

    if length < 512:
        intermediary_mean_mess_ratio_calc: int = 32
    elif length <= 1024:
        intermediary_mean_mess_ratio_calc = 64
    else:
        intermediary_mean_mess_ratio_calc = 128

    for character, index in zip(decoded_sequence + "\n", range(length)):
        for detector in detectors:
            if detector.eligible(character):
                detector.feed(character)

        if (
            index > 0 and index % intermediary_mean_mess_ratio_calc == 0
        ) or index == length - 1:
            mean_mess_ratio = sum(dt.ratio for dt in detectors)

            if mean_mess_ratio >= maximum_threshold:
                break

    if debug:
        logger = getLogger("charset_normalizer")

        logger.log(
            TRACE,
            "Mess-detector extended-analysis start. "
            f"intermediary_mean_mess_ratio_calc={intermediary_mean_mess_ratio_calc} mean_mess_ratio={mean_mess_ratio} "
            f"maximum_threshold={maximum_threshold}",
        )

        if len(decoded_sequence) > 16:
            logger.log(TRACE, f"Starting with: {decoded_sequence[:16]}")
            logger.log(TRACE, f"Ending with: {decoded_sequence[-16::]}")

        for dt in detectors:
            logger.log(TRACE, f"{dt.__class__}: {dt.ratio}")

    return round(mean_mess_ratio, 3)

# === NexusCore/openenv\Lib\site-packages\litellm\completion_extras\litellm_responses_transformation\transformation.py ===
"""
Handler for transforming /chat/completions api requests to litellm.responses requests
"""

import json
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

from litellm import ModelResponse
from litellm._logging import verbose_logger
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.bridges.completion_transformation import (
    CompletionTransformationBridge,
)

if TYPE_CHECKING:
    from openai.types.responses import ResponseInputImageParam
    from pydantic import BaseModel

    from litellm import LiteLLMLoggingObj, ModelResponse
    from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
    from litellm.types.llms.openai import (
        ALL_RESPONSES_API_TOOL_PARAMS,
        AllMessageValues,
        ChatCompletionImageObject,
        ChatCompletionThinkingBlock,
        OpenAIMessageContentListBlock,
    )
    from litellm.types.utils import GenericStreamingChunk, ModelResponseStream


class LiteLLMResponsesTransformationHandler(CompletionTransformationBridge):
    """
    Handler for transforming /chat/completions api requests to litellm.responses requests
    """

    def __init__(self):
        pass

    def convert_chat_completion_messages_to_responses_api(
        self, messages: List["AllMessageValues"]
    ) -> Tuple[List[Any], Optional[str]]:
        input_items: List[Any] = []
        instructions: Optional[str] = None

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")

            if role == "system":
                # Extract system message as instructions
                if isinstance(content, str):
                    instructions = content
                else:
                    input_items.append(
                        {
                            "type": "message",
                            "role": role,
                            "content": self._convert_content_to_responses_format(
                                content, role  # type: ignore
                            ),
                        }
                    )
            elif role == "tool":
                # Convert tool message to function call output format
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": tool_call_id,
                        "output": content,
                    }
                )
            elif role == "assistant" and tool_calls and isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    function = tool_call.get("function")
                    if function:
                        input_tool_call = {
                            "type": "function_call",
                            "call_id": tool_call["id"],
                        }
                        if "name" in function:
                            input_tool_call["name"] = function["name"]
                        if "arguments" in function:
                            input_tool_call["arguments"] = function["arguments"]
                        input_items.append(input_tool_call)
                    else:
                        raise ValueError(f"tool call not supported: {tool_call}")
            elif content is not None:
                # Regular user/assistant message
                input_items.append(
                    {
                        "type": "message",
                        "role": role,
                        "content": self._convert_content_to_responses_format(
                            content, cast(str, role)
                        ),
                    }
                )

        return input_items, instructions

    def transform_request(
        self,
        model: str,
        messages: List["AllMessageValues"],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
        litellm_logging_obj: "LiteLLMLoggingObj",
    ) -> dict:
        from litellm.types.llms.openai import ResponsesAPIOptionalRequestParams

        (
            input_items,
            instructions,
        ) = self.convert_chat_completion_messages_to_responses_api(messages)

        # Build responses API request using the reverse transformation logic
        responses_api_request = ResponsesAPIOptionalRequestParams()

        # Set instructions if we found a system message
        if instructions:
            responses_api_request["instructions"] = instructions

        # Map optional parameters
        for key, value in optional_params.items():
            if value is None:
                continue
            if key in ("max_tokens", "max_completion_tokens"):
                responses_api_request["max_output_tokens"] = value
            elif key == "tools" and value is not None:
                # Convert chat completion tools to responses API tools format
                responses_api_request["tools"] = (
                    self._convert_tools_to_responses_format(
                        cast(List[Dict[str, Any]], value)
                    )
                )
            elif key in ResponsesAPIOptionalRequestParams.__annotations__.keys():
                responses_api_request[key] = value  # type: ignore
            elif key == "metadata":
                responses_api_request["metadata"] = value
            elif key == "previous_response_id":
                # Support for responses API session management
                responses_api_request["previous_response_id"] = value

        # Get stream parameter from litellm_params if not in optional_params
        stream = optional_params.get("stream") or litellm_params.get("stream", False)
        verbose_logger.debug(f"Chat provider: Stream parameter: {stream}")

        # Ensure stream is properly set in the request
        if stream:
            responses_api_request["stream"] = True

        # Handle session management if previous_response_id is provided
        previous_response_id = optional_params.get("previous_response_id")
        if previous_response_id:
            # Use the existing session handler for responses API
            verbose_logger.debug(
                f"Chat provider: Warning ignoring previous response ID: {previous_response_id}"
            )

        # Convert back to responses API format for the actual request

        api_model = model

        from litellm.types.utils import CallTypes

        setattr(litellm_logging_obj, "call_type", CallTypes.responses.value)

        request_data = {
            "model": api_model,
            "input": input_items,
            "litellm_logging_obj": litellm_logging_obj,
            **litellm_params,
        }

        verbose_logger.debug(
            f"Chat provider: Final request model={api_model}, input_items={len(input_items)}"
        )

        # Add non-None values from responses_api_request
        for key, value in responses_api_request.items():
            if value is not None:
                if key == "instructions" and instructions:
                    request_data["instructions"] = instructions
                else:
                    request_data[key] = value

        return request_data

    def transform_response(
        self,
        model: str,
        raw_response: "BaseModel",
        model_response: "ModelResponse",
        logging_obj: "LiteLLMLoggingObj",
        request_data: dict,
        messages: List["AllMessageValues"],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> "ModelResponse":
        """Transform Responses API response to chat completion response"""

        from openai.types.responses import (
            ResponseFunctionToolCall,
            ResponseOutputMessage,
            ResponseReasoningItem,
        )

        from litellm.responses.utils import ResponseAPILoggingUtils
        from litellm.types.llms.openai import ResponsesAPIResponse
        from litellm.types.responses.main import (
            GenericResponseOutputItem,
            OutputFunctionToolCall,
        )
        from litellm.types.utils import Choices, Message

        if not isinstance(raw_response, ResponsesAPIResponse):
            raise ValueError(f"Unexpected response type: {type(raw_response)}")

        if raw_response.error is not None:
            raise ValueError(f"Error in response: {raw_response.error}")

        choices: List[Choices] = []
        index = 0
        for item in raw_response.output:
            if isinstance(item, ResponseReasoningItem):
                pass  # ignore for now.
            elif isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    response_text = getattr(content, "text", "")
                    msg = Message(
                        role=item.role, content=response_text if response_text else ""
                    )

                    choices.append(
                        Choices(message=msg, finish_reason="stop", index=index)
                    )
                    index += 1
            elif isinstance(item, ResponseFunctionToolCall):
                msg = Message(
                    content=None,
                    tool_calls=[
                        {
                            "id": item.call_id,
                            "function": {
                                "name": item.name,
                                "arguments": item.arguments,
                            },
                            "type": "function",
                        }
                    ],
                )

                choices.append(
                    Choices(message=msg, finish_reason="tool_calls", index=index)
                )
                index += 1
            elif isinstance(item, GenericResponseOutputItem):
                raise ValueError("GenericResponseOutputItem not supported")
            elif isinstance(item, OutputFunctionToolCall):
                # function/tool calls pass through as-is
                raise ValueError("Function calling not supported yet.")
            else:
                raise ValueError(f"Unknown item type: {item}")

        if len(choices) == 0:
            if (
                raw_response.incomplete_details is not None
                and raw_response.incomplete_details.reason is not None
            ):
                raise ValueError(
                    f"{model} unable to complete request: {raw_response.incomplete_details.reason}"
                )

        setattr(model_response, "choices", choices)

        model_response.model = model

        setattr(
            model_response,
            "usage",
            ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
                raw_response.usage
            ),
        )
        return model_response

    def get_model_response_iterator(
        self,
        streaming_response: Union[
            Iterator[str], AsyncIterator[str], "ModelResponse", "BaseModel"
        ],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ) -> BaseModelResponseIterator:
        return OpenAiResponsesToChatCompletionStreamIterator(
            streaming_response, sync_stream, json_mode
        )

    def _convert_content_str_to_input_text(
        self, content: str, role: str
    ) -> Dict[str, Any]:
        if role == "user" or role == "system":
            return {"type": "input_text", "text": content}
        else:
            return {"type": "output_text", "text": content}

    def _convert_content_to_responses_format_image(
        self, content: "ChatCompletionImageObject", role: str
    ) -> "ResponseInputImageParam":
        from openai.types.responses import ResponseInputImageParam

        content_image_url = content.get("image_url")
        actual_image_url: Optional[str] = None
        detail: Optional[Literal["low", "high", "auto"]] = None

        if isinstance(content_image_url, str):
            actual_image_url = content_image_url
        elif isinstance(content_image_url, dict):
            actual_image_url = content_image_url.get("url")
            detail = cast(
                Optional[Literal["low", "high", "auto"]],
                content_image_url.get("detail"),
            )

        if actual_image_url is None:
            raise ValueError(f"Invalid image URL: {content_image_url}")

        image_param = ResponseInputImageParam(
            image_url=actual_image_url, detail="auto", type="input_image"
        )

        if detail:
            image_param["detail"] = detail

        return image_param

    def _convert_content_to_responses_format(
        self,
        content: Union[
            str,
            Iterable[
                Union["OpenAIMessageContentListBlock", "ChatCompletionThinkingBlock"]
            ],
        ],
        role: str,
    ) -> List[Dict[str, Any]]:
        """Convert chat completion content to responses API format"""
        from litellm.types.llms.openai import ChatCompletionImageObject

        verbose_logger.debug(
            f"Chat provider: Converting content to responses format - input type: {type(content)}"
        )

        if isinstance(content, str):
            result = [self._convert_content_str_to_input_text(content, role)]
            verbose_logger.debug(f"Chat provider: String content -> {result}")
            return result
        elif isinstance(content, list):
            result = []
            for i, item in enumerate(content):
                verbose_logger.debug(
                    f"Chat provider: Processing content item {i}: {type(item)} = {item}"
                )
                if isinstance(item, str):
                    converted = self._convert_content_str_to_input_text(item, role)
                    result.append(converted)
                    verbose_logger.debug(f"Chat provider:   -> {converted}")
                elif isinstance(item, dict):
                    # Handle multimodal content
                    original_type = item.get("type")
                    if original_type == "text":
                        converted = self._convert_content_str_to_input_text(
                            item.get("text", ""), role
                        )
                        result.append(converted)
                        verbose_logger.debug(f"Chat provider:   text -> {converted}")
                    elif original_type == "image_url":
                        # Map to responses API image format
                        converted = cast(
                            dict,
                            self._convert_content_to_responses_format_image(
                                cast(ChatCompletionImageObject, item), role
                            ),
                        )
                        result.append(converted)
                        verbose_logger.debug(
                            f"Chat provider:   image_url -> {converted}"
                        )
                    else:
                        # Try to map other types to responses API format
                        item_type = original_type or "input_text"
                        if item_type == "image":
                            converted = {"type": "input_image", **item}
                            result.append(converted)
                            verbose_logger.debug(
                                f"Chat provider:   image -> {converted}"
                            )
                        elif item_type in [
                            "input_text",
                            "input_image",
                            "output_text",
                            "refusal",
                            "input_file",
                            "computer_screenshot",
                            "summary_text",
                        ]:
                            # Already in responses API format
                            result.append(item)
                            verbose_logger.debug(
                                f"Chat provider:   passthrough -> {item}"
                            )
                        else:
                            # Default to input_text for unknown types
                            converted = self._convert_content_str_to_input_text(
                                str(item.get("text", item)), role
                            )
                            result.append(converted)
                            verbose_logger.debug(
                                f"Chat provider:   unknown({original_type}) -> {converted}"
                            )
            verbose_logger.debug(f"Chat provider: Final converted content: {result}")
            return result
        else:
            result = [self._convert_content_str_to_input_text(str(content), role)]
            verbose_logger.debug(f"Chat provider: Other content type -> {result}")
            return result

    def _convert_tools_to_responses_format(
        self, tools: List[Dict[str, Any]]
    ) -> List["ALL_RESPONSES_API_TOOL_PARAMS"]:
        """Convert chat completion tools to responses API tools format"""
        responses_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                function = tool.get("function", {})
                responses_tools.append(
                    {
                        "type": "function",
                        "name": function.get("name", ""),
                        "description": function.get("description", ""),
                        "parameters": function.get("parameters", {}),
                        "strict": function.get("strict", False),
                    }
                )
        return cast(List["ALL_RESPONSES_API_TOOL_PARAMS"], responses_tools)

    def _map_responses_status_to_finish_reason(self, status: Optional[str]) -> str:
        """Map responses API status to chat completion finish_reason"""
        if not status:
            return "stop"

        status_mapping = {
            "completed": "stop",
            "incomplete": "length",
            "failed": "stop",
            "cancelled": "stop",
        }

        return status_mapping.get(status, "stop")


class OpenAiResponsesToChatCompletionStreamIterator(BaseModelResponseIterator):
    def __init__(
        self, streaming_response, sync_stream: bool, json_mode: Optional[bool] = False
    ):
        super().__init__(streaming_response, sync_stream, json_mode)

    def _handle_string_chunk(
        self, str_line: Union[str, "BaseModel"]
    ) -> Union["GenericStreamingChunk", "ModelResponseStream"]:
        from pydantic import BaseModel

        if isinstance(str_line, BaseModel):
            return self.chunk_parser(str_line.model_dump())

        if not str_line or str_line.startswith("event:"):
            # ignore.
            return GenericStreamingChunk(
                text="", tool_use=None, is_finished=False, finish_reason="", usage=None
            )
        index = str_line.find("data:")
        if index != -1:
            str_line = str_line[index + 5 :]

        return self.chunk_parser(json.loads(str_line))

    def chunk_parser(
        self, chunk: dict
    ) -> Union["GenericStreamingChunk", "ModelResponseStream"]:
        # Transform responses API streaming chunk to chat completion format
        from litellm.types.llms.openai import ChatCompletionToolCallFunctionChunk
        from litellm.types.utils import (
            ChatCompletionToolCallChunk,
            GenericStreamingChunk,
        )

        verbose_logger.debug(
            f"Chat provider: transform_streaming_response called with chunk: {chunk}"
        )
        parsed_chunk = chunk

        if not parsed_chunk:
            raise ValueError("Chat provider: Empty parsed_chunk")

        if not isinstance(parsed_chunk, dict):
            raise ValueError(f"Chat provider: Invalid chunk type {type(parsed_chunk)}")

        # Handle different event types from responses API
        event_type = parsed_chunk.get("type")
        verbose_logger.debug(f"Chat provider: Processing event type: {event_type}")

        if event_type == "response.created":
            # Initial response creation event
            verbose_logger.debug(f"Chat provider: response.created -> {chunk}")
            return GenericStreamingChunk(
                text="", tool_use=None, is_finished=False, finish_reason="", usage=None
            )
        elif event_type == "response.output_item.added":
            # New output item added
            output_item = parsed_chunk.get("item", {})
            if output_item.get("type") == "function_call":
                return GenericStreamingChunk(
                    text="",
                    tool_use=ChatCompletionToolCallChunk(
                        id=output_item.get("call_id"),
                        index=0,
                        type="function",
                        function=ChatCompletionToolCallFunctionChunk(
                            name=parsed_chunk.get("name", None),
                            arguments=parsed_chunk.get("arguments", ""),
                        ),
                    ),
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                )
            elif output_item.get("type") == "message":
                pass
            elif output_item.get("type") == "reasoning":
                pass
            else:
                raise ValueError(f"Chat provider: Invalid output_item  {output_item}")
        elif event_type == "response.function_call_arguments.delta":
            content_part: Optional[str] = parsed_chunk.get("delta", None)
            if content_part:
                return GenericStreamingChunk(
                    text="",
                    tool_use=ChatCompletionToolCallChunk(
                        id=None,
                        index=0,
                        type="function",
                        function=ChatCompletionToolCallFunctionChunk(
                            name=None, arguments=content_part
                        ),
                    ),
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                )
            else:
                raise ValueError(
                    f"Chat provider: Invalid function argument delta {parsed_chunk}"
                )
        elif event_type == "response.output_item.done":
            # New output item added
            output_item = parsed_chunk.get("item", {})
            if output_item.get("type") == "function_call":
                return GenericStreamingChunk(
                    text="",
                    tool_use=ChatCompletionToolCallChunk(
                        id=output_item.get("call_id"),
                        index=0,
                        type="function",
                        function=ChatCompletionToolCallFunctionChunk(
                            name=parsed_chunk.get("name", None),
                            arguments="",  # responses API sends everything again, we don't
                        ),
                    ),
                    is_finished=True,
                    finish_reason="tool_calls",
                    usage=None,
                )
            elif output_item.get("type") == "message":
                return GenericStreamingChunk(
                    finish_reason="stop", is_finished=True, usage=None, text=""
                )
            elif output_item.get("type") == "reasoning":
                pass
            else:
                raise ValueError(f"Chat provider: Invalid output_item  {output_item}")

        elif event_type == "response.output_text.delta":
            # Content part added to output
            content_part = parsed_chunk.get("delta", None)
            if content_part is not None:
                return GenericStreamingChunk(
                    text=content_part,
                    tool_use=None,
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                )
            else:
                raise ValueError(f"Chat provider: Invalid text delta {parsed_chunk}")
        else:
            pass
        # For any unhandled event types, create a minimal valid chunk or skip
        verbose_logger.debug(
            f"Chat provider: Unhandled event type '{event_type}', creating empty chunk"
        )

        # Return a minimal valid chunk for unknown events
        return GenericStreamingChunk(
            text="", tool_use=None, is_finished=False, finish_reason="", usage=None
        )