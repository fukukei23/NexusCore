
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\chunkparser_app.py ===
# Natural Language Toolkit: Regexp Chunk Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the regular expression based chunk
parser ``nltk.chunk.RegexpChunkParser``.
"""

# Todo: Add a way to select the development set from the menubar.  This
# might just need to be a selection box (conll vs treebank etc) plus
# configuration parameters to select what's being chunked (eg VP vs NP)
# and what part of the data is being used as the development set.

import random
import re
import textwrap
import time
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Text,
    Tk,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font

from nltk.chunk import ChunkScore, RegexpChunkParser
from nltk.chunk.regexp import RegexpChunkRule
from nltk.corpus import conll2000, treebank_chunk
from nltk.draw.util import ShowText
from nltk.tree import Tree
from nltk.util import in_idle


class RegexpChunkApp:
    """
    A graphical tool for exploring the regular expression based chunk
    parser ``nltk.chunk.RegexpChunkParser``.

    See ``HELP`` for instructional text.
    """

    ##/////////////////////////////////////////////////////////////////
    ##  Help Text
    ##/////////////////////////////////////////////////////////////////

    #: A dictionary mapping from part of speech tags to descriptions,
    #: which is used in the help text.  (This should probably live with
    #: the conll and/or treebank corpus instead.)
    TAGSET = {
        "CC": "Coordinating conjunction",
        "PRP$": "Possessive pronoun",
        "CD": "Cardinal number",
        "RB": "Adverb",
        "DT": "Determiner",
        "RBR": "Adverb, comparative",
        "EX": "Existential there",
        "RBS": "Adverb, superlative",
        "FW": "Foreign word",
        "RP": "Particle",
        "JJ": "Adjective",
        "TO": "to",
        "JJR": "Adjective, comparative",
        "UH": "Interjection",
        "JJS": "Adjective, superlative",
        "VB": "Verb, base form",
        "LS": "List item marker",
        "VBD": "Verb, past tense",
        "MD": "Modal",
        "NNS": "Noun, plural",
        "NN": "Noun, singular or mass",
        "VBN": "Verb, past participle",
        "VBZ": "Verb,3rd ps. sing. present",
        "NNP": "Proper noun, singular",
        "NNPS": "Proper noun plural",
        "WDT": "wh-determiner",
        "PDT": "Predeterminer",
        "WP": "wh-pronoun",
        "POS": "Possessive ending",
        "WP$": "Possessive wh-pronoun",
        "PRP": "Personal pronoun",
        "WRB": "wh-adverb",
        "(": "open parenthesis",
        ")": "close parenthesis",
        "``": "open quote",
        ",": "comma",
        "''": "close quote",
        ".": "period",
        "#": "pound sign (currency marker)",
        "$": "dollar sign (currency marker)",
        "IN": "Preposition/subord. conjunction",
        "SYM": "Symbol (mathematical or scientific)",
        "VBG": "Verb, gerund/present participle",
        "VBP": "Verb, non-3rd ps. sing. present",
        ":": "colon",
    }

    #: Contents for the help box.  This is a list of tuples, one for
    #: each help page, where each tuple has four elements:
    #:   - A title (displayed as a tab)
    #:   - A string description of tabstops (see Tkinter.Text for details)
    #:   - The text contents for the help page.  You can use expressions
    #:     like <red>...</red> to colorize the text; see ``HELP_AUTOTAG``
    #:     for a list of tags you can use for colorizing.
    HELP = [
        (
            "Help",
            "20",
            "Welcome to the regular expression chunk-parser grammar editor.  "
            "You can use this editor to develop and test chunk parser grammars "
            "based on NLTK's RegexpChunkParser class.\n\n"
            # Help box.
            "Use this box ('Help') to learn more about the editor; click on the "
            "tabs for help on specific topics:"
            "<indent>\n"
            "Rules: grammar rule types\n"
            "Regexps: regular expression syntax\n"
            "Tags: part of speech tags\n</indent>\n"
            # Grammar.
            "Use the upper-left box ('Grammar') to edit your grammar.  "
            "Each line of your grammar specifies a single 'rule', "
            "which performs an action such as creating a chunk or merging "
            "two chunks.\n\n"
            # Dev set.
            "The lower-left box ('Development Set') runs your grammar on the "
            "development set, and displays the results.  "
            "Your grammar's chunks are <highlight>highlighted</highlight>, and "
            "the correct (gold standard) chunks are "
            "<underline>underlined</underline>.  If they "
            "match, they are displayed in <green>green</green>; otherwise, "
            "they are displayed in <red>red</red>.  The box displays a single "
            "sentence from the development set at a time; use the scrollbar or "
            "the next/previous buttons view additional sentences.\n\n"
            # Performance
            "The lower-right box ('Evaluation') tracks the performance of "
            "your grammar on the development set.  The 'precision' axis "
            "indicates how many of your grammar's chunks are correct; and "
            "the 'recall' axis indicates how many of the gold standard "
            "chunks your system generated.  Typically, you should try to "
            "design a grammar that scores high on both metrics.  The "
            "exact precision and recall of the current grammar, as well "
            "as their harmonic mean (the 'f-score'), are displayed in "
            "the status bar at the bottom of the window.",
        ),
        (
            "Rules",
            "10",
            "<h1>{...regexp...}</h1>"
            "<indent>\nChunk rule: creates new chunks from words matching "
            "regexp.</indent>\n\n"
            "<h1>}...regexp...{</h1>"
            "<indent>\nStrip rule: removes words matching regexp from existing "
            "chunks.</indent>\n\n"
            "<h1>...regexp1...}{...regexp2...</h1>"
            "<indent>\nSplit rule: splits chunks that match regexp1 followed by "
            "regexp2 in two.</indent>\n\n"
            "<h1>...regexp...{}...regexp...</h1>"
            "<indent>\nMerge rule: joins consecutive chunks that match regexp1 "
            "and regexp2</indent>\n",
        ),
        (
            "Regexps",
            "10 60",
            # "Regular Expression Syntax Summary:\n\n"
            "<h1>Pattern\t\tMatches...</h1>\n"
            "<hangindent>"
            "\t<<var>T</var>>\ta word with tag <var>T</var> "
            "(where <var>T</var> may be a regexp).\n"
            "\t<var>x</var>?\tan optional <var>x</var>\n"
            "\t<var>x</var>+\ta sequence of 1 or more <var>x</var>'s\n"
            "\t<var>x</var>*\ta sequence of 0 or more <var>x</var>'s\n"
            "\t<var>x</var>|<var>y</var>\t<var>x</var> or <var>y</var>\n"
            "\t.\tmatches any character\n"
            "\t(<var>x</var>)\tTreats <var>x</var> as a group\n"
            "\t# <var>x...</var>\tTreats <var>x...</var> "
            "(to the end of the line) as a comment\n"
            "\t\\<var>C</var>\tmatches character <var>C</var> "
            "(useful when <var>C</var> is a special character "
            "like + or #)\n"
            "</hangindent>"
            "\n<h1>Examples:</h1>\n"
            "<hangindent>"
            "\t<regexp><NN></regexp>\n"
            '\t\tMatches <match>"cow/NN"</match>\n'
            '\t\tMatches <match>"green/NN"</match>\n'
            "\t<regexp><VB.*></regexp>\n"
            '\t\tMatches <match>"eating/VBG"</match>\n'
            '\t\tMatches <match>"ate/VBD"</match>\n'
            "\t<regexp><IN><DT><NN></regexp>\n"
            '\t\tMatches <match>"on/IN the/DT car/NN"</match>\n'
            "\t<regexp><RB>?<VBD></regexp>\n"
            '\t\tMatches <match>"ran/VBD"</match>\n'
            '\t\tMatches <match>"slowly/RB ate/VBD"</match>\n'
            r"\t<regexp><\#><CD> # This is a comment...</regexp>\n"
            '\t\tMatches <match>"#/# 100/CD"</match>\n'
            "</hangindent>",
        ),
        (
            "Tags",
            "10 60",
            "<h1>Part of Speech Tags:</h1>\n"
            + "<hangindent>"
            + "<<TAGSET>>"
            + "</hangindent>\n",  # this gets auto-substituted w/ self.TAGSET
        ),
    ]

    HELP_AUTOTAG = [
        ("red", dict(foreground="#a00")),
        ("green", dict(foreground="#080")),
        ("highlight", dict(background="#ddd")),
        ("underline", dict(underline=True)),
        ("h1", dict(underline=True)),
        ("indent", dict(lmargin1=20, lmargin2=20)),
        ("hangindent", dict(lmargin1=0, lmargin2=60)),
        ("var", dict(foreground="#88f")),
        ("regexp", dict(foreground="#ba7")),
        ("match", dict(foreground="#6a6")),
    ]

    ##/////////////////////////////////////////////////////////////////
    ##  Config Parameters
    ##/////////////////////////////////////////////////////////////////

    _EVAL_DELAY = 1
    """If the user has not pressed any key for this amount of time (in
       seconds), and the current grammar has not been evaluated, then
       the eval demon will evaluate it."""

    _EVAL_CHUNK = 15
    """The number of sentences that should be evaluated by the eval
       demon each time it runs."""
    _EVAL_FREQ = 0.2
    """The frequency (in seconds) at which the eval demon is run"""
    _EVAL_DEMON_MIN = 0.02
    """The minimum amount of time that the eval demon should take each time
       it runs -- if it takes less than this time, _EVAL_CHUNK will be
       modified upwards."""
    _EVAL_DEMON_MAX = 0.04
    """The maximum amount of time that the eval demon should take each time
       it runs -- if it takes more than this time, _EVAL_CHUNK will be
       modified downwards."""

    _GRAMMARBOX_PARAMS = dict(
        width=40,
        height=12,
        background="#efe",
        highlightbackground="#efe",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _HELPBOX_PARAMS = dict(
        width=15,
        height=15,
        background="#efe",
        highlightbackground="#efe",
        foreground="#555",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _DEVSETBOX_PARAMS = dict(
        width=70,
        height=10,
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
        tabs=(30,),
    )
    _STATUS_PARAMS = dict(background="#9bb", relief="groove", border=2)
    _FONT_PARAMS = dict(family="helvetica", size=-20)
    _FRAME_PARAMS = dict(background="#777", padx=2, pady=2, border=3)
    _EVALBOX_PARAMS = dict(
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        width=300,
        height=280,
    )
    _BUTTON_PARAMS = dict(
        background="#777", activebackground="#777", highlightbackground="#777"
    )
    _HELPTAB_BG_COLOR = "#aba"
    _HELPTAB_FG_COLOR = "#efe"

    _HELPTAB_FG_PARAMS = dict(background="#efe")
    _HELPTAB_BG_PARAMS = dict(background="#aba")
    _HELPTAB_SPACER = 6

    def normalize_grammar(self, grammar):
        # Strip comments
        grammar = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", grammar)
        # Normalize whitespace
        grammar = re.sub(" +", " ", grammar)
        grammar = re.sub(r"\n\s+", r"\n", grammar)
        grammar = grammar.strip()
        # [xx] Hack: automatically backslash $!
        grammar = re.sub(r"([^\\])\$", r"\1\\$", grammar)
        return grammar

    def __init__(
        self,
        devset_name="conll2000",
        devset=None,
        grammar="",
        chunk_label="NP",
        tagset=None,
    ):
        """
        :param devset_name: The name of the development set; used for
            display & for save files.  If either the name 'treebank'
            or the name 'conll2000' is used, and devset is None, then
            devset will be set automatically.
        :param devset: A list of chunked sentences
        :param grammar: The initial grammar to display.
        :param tagset: Dictionary from tags to string descriptions, used
            for the help page.  Defaults to ``self.TAGSET``.
        """
        self._chunk_label = chunk_label

        if tagset is None:
            tagset = self.TAGSET
        self.tagset = tagset

        # Named development sets:
        if devset is None:
            if devset_name == "conll2000":
                devset = conll2000.chunked_sents("train.txt")  # [:100]
            elif devset == "treebank":
                devset = treebank_chunk.chunked_sents()  # [:100]
            else:
                raise ValueError("Unknown development set %s" % devset_name)

        self.chunker = None
        """The chunker built from the grammar string"""

        self.grammar = grammar
        """The unparsed grammar string"""

        self.normalized_grammar = None
        """A normalized version of ``self.grammar``."""

        self.grammar_changed = 0
        """The last time() that the grammar was changed."""

        self.devset = devset
        """The development set -- a list of chunked sentences."""

        self.devset_name = devset_name
        """The name of the development set (for save files)."""

        self.devset_index = -1
        """The index into the development set of the first instance
           that's currently being viewed."""

        self._last_keypress = 0
        """The time() when a key was most recently pressed"""

        self._history = []
        """A list of (grammar, precision, recall, fscore) tuples for
           grammars that the user has already tried."""

        self._history_index = 0
        """When the user is scrolling through previous grammars, this
           is used to keep track of which grammar they're looking at."""

        self._eval_grammar = None
        """The grammar that is being currently evaluated by the eval
           demon."""

        self._eval_normalized_grammar = None
        """A normalized copy of ``_eval_grammar``."""

        self._eval_index = 0
        """The index of the next sentence in the development set that
           should be looked at by the eval demon."""

        self._eval_score = ChunkScore(chunk_label=chunk_label)
        """The ``ChunkScore`` object that's used to keep track of the score
        of the current grammar on the development set."""

        # Set up the main window.
        top = self.top = Tk()
        top.geometry("+50+50")
        top.title("Regexp Chunk Parser App")
        top.bind("<Control-q>", self.destroy)

        # Variable that restricts how much of the devset we look at.
        self._devset_size = IntVar(top)
        self._devset_size.set(100)

        # Set up all the tkinter widgets
        self._init_fonts(top)
        self._init_widgets(top)
        self._init_bindings(top)
        self._init_menubar(top)
        self.grammarbox.focus()

        # If a grammar was given, then display it.
        if grammar:
            self.grammarbox.insert("end", grammar + "\n")
            self.grammarbox.mark_set("insert", "1.0")

        # Display the first item in the development set
        self.show_devset(0)
        self.update()

    def _init_bindings(self, top):
        top.bind("<Control-n>", self._devset_next)
        top.bind("<Control-p>", self._devset_prev)
        top.bind("<Control-t>", self.toggle_show_trace)
        top.bind("<KeyPress>", self.update)
        top.bind("<Control-s>", lambda e: self.save_grammar())
        top.bind("<Control-o>", lambda e: self.load_grammar())
        self.grammarbox.bind("<Control-t>", self.toggle_show_trace)
        self.grammarbox.bind("<Control-n>", self._devset_next)
        self.grammarbox.bind("<Control-p>", self._devset_prev)

        # Redraw the eval graph when the window size changes
        self.evalbox.bind("<Configure>", self._eval_plot)

    def _init_fonts(self, top):
        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(top)
        self._size.set(20)
        self._font = Font(family="helvetica", size=-self._size.get())
        self._smallfont = Font(
            family="helvetica", size=-(int(self._size.get() * 14 // 20))
        )

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Reset Application", underline=0, command=self.reset)
        filemenu.add_command(
            label="Save Current Grammar",
            underline=0,
            accelerator="Ctrl-s",
            command=self.save_grammar,
        )
        filemenu.add_command(
            label="Load Grammar",
            underline=0,
            accelerator="Ctrl-o",
            command=self.load_grammar,
        )

        filemenu.add_command(
            label="Save Grammar History", underline=13, command=self.save_history
        )

        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=16,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=20,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=34,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        devsetmenu = Menu(menubar, tearoff=0)
        devsetmenu.add_radiobutton(
            label="50 sentences",
            variable=self._devset_size,
            value=50,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="100 sentences",
            variable=self._devset_size,
            value=100,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="200 sentences",
            variable=self._devset_size,
            value=200,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="500 sentences",
            variable=self._devset_size,
            value=500,
            command=self.set_devset_size,
        )
        menubar.add_cascade(label="Development-Set", underline=0, menu=devsetmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def toggle_show_trace(self, *e):
        if self._showing_trace:
            self.show_devset()
        else:
            self.show_trace()
        return "break"

    _SCALE_N = 5  # center on the last 5 examples.
    _DRAW_LINES = False

    def _eval_plot(self, *e, **config):
        width = config.get("width", self.evalbox.winfo_width())
        height = config.get("height", self.evalbox.winfo_height())

        # Clear the canvas
        self.evalbox.delete("all")

        # Draw the precision & recall labels.
        tag = self.evalbox.create_text(
            10, height // 2 - 10, justify="left", anchor="w", text="Precision"
        )
        left, right = self.evalbox.bbox(tag)[2] + 5, width - 10
        tag = self.evalbox.create_text(
            left + (width - left) // 2,
            height - 10,
            anchor="s",
            text="Recall",
            justify="center",
        )
        top, bot = 10, self.evalbox.bbox(tag)[1] - 10

        # Draw masks for clipping the plot.
        bg = self._EVALBOX_PARAMS["background"]
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, 0, left - 1, 5000, fill=bg, outline=bg)
        )
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, bot + 1, 5000, 5000, fill=bg, outline=bg)
        )

        # Calculate the plot's scale.
        if self._autoscale.get() and len(self._history) > 1:
            max_precision = max_recall = 0
            min_precision = min_recall = 1
            for i in range(1, min(len(self._history), self._SCALE_N + 1)):
                grammar, precision, recall, fmeasure = self._history[-i]
                min_precision = min(precision, min_precision)
                min_recall = min(recall, min_recall)
                max_precision = max(precision, max_precision)
                max_recall = max(recall, max_recall)
            #             if max_precision-min_precision > max_recall-min_recall:
            #                 min_recall -= (max_precision-min_precision)/2
            #                 max_recall += (max_precision-min_precision)/2
            #             else:
            #                 min_precision -= (max_recall-min_recall)/2
            #                 max_precision += (max_recall-min_recall)/2
            #             if min_recall < 0:
            #                 max_recall -= min_recall
            #                 min_recall = 0
            #             if min_precision < 0:
            #                 max_precision -= min_precision
            #                 min_precision = 0
            min_precision = max(min_precision - 0.01, 0)
            min_recall = max(min_recall - 0.01, 0)
            max_precision = min(max_precision + 0.01, 1)
            max_recall = min(max_recall + 0.01, 1)
        else:
            min_precision = min_recall = 0
            max_precision = max_recall = 1

        # Draw the axis lines & grid lines
        for i in range(11):
            x = left + (right - left) * (
                (i / 10.0 - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (i / 10.0 - min_precision) / (max_precision - min_precision)
            )
            if left < x < right:
                self.evalbox.create_line(x, top, x, bot, fill="#888")
            if top < y < bot:
                self.evalbox.create_line(left, y, right, y, fill="#888")
        self.evalbox.create_line(left, top, left, bot)
        self.evalbox.create_line(left, bot, right, bot)

        # Display the plot's scale
        self.evalbox.create_text(
            left - 3,
            bot,
            justify="right",
            anchor="se",
            text="%d%%" % (100 * min_precision),
        )
        self.evalbox.create_text(
            left - 3,
            top,
            justify="right",
            anchor="ne",
            text="%d%%" % (100 * max_precision),
        )
        self.evalbox.create_text(
            left,
            bot + 3,
            justify="center",
            anchor="nw",
            text="%d%%" % (100 * min_recall),
        )
        self.evalbox.create_text(
            right,
            bot + 3,
            justify="center",
            anchor="ne",
            text="%d%%" % (100 * max_recall),
        )

        # Display the scores.
        prev_x = prev_y = None
        for i, (_, precision, recall, fscore) in enumerate(self._history):
            x = left + (right - left) * (
                (recall - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (precision - min_precision) / (max_precision - min_precision)
            )
            if i == self._history_index:
                self.evalbox.create_oval(
                    x - 2, y - 2, x + 2, y + 2, fill="#0f0", outline="#000"
                )
                self.status["text"] = (
                    "Precision: %.2f%%\t" % (precision * 100)
                    + "Recall: %.2f%%\t" % (recall * 100)
                    + "F-score: %.2f%%" % (fscore * 100)
                )
            else:
                self.evalbox.lower(
                    self.evalbox.create_oval(
                        x - 2, y - 2, x + 2, y + 2, fill="#afa", outline="#8c8"
                    )
                )
            if prev_x is not None and self._eval_lines.get():
                self.evalbox.lower(
                    self.evalbox.create_line(prev_x, prev_y, x, y, fill="#8c8")
                )
            prev_x, prev_y = x, y

    _eval_demon_running = False

    def _eval_demon(self):
        if self.top is None:
            return
        if self.chunker is None:
            self._eval_demon_running = False
            return

        # Note our starting time.
        t0 = time.time()

        # If are still typing, then wait for them to finish.
        if (
            time.time() - self._last_keypress < self._EVAL_DELAY
            and self.normalized_grammar != self._eval_normalized_grammar
        ):
            self._eval_demon_running = True
            return self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

        # If the grammar changed, restart the evaluation.
        if self.normalized_grammar != self._eval_normalized_grammar:
            # Check if we've seen this grammar already.  If so, then
            # just use the old evaluation values.
            for g, p, r, f in self._history:
                if self.normalized_grammar == self.normalize_grammar(g):
                    self._history.append((g, p, r, f))
                    self._history_index = len(self._history) - 1
                    self._eval_plot()
                    self._eval_demon_running = False
                    self._eval_normalized_grammar = None
                    return
            self._eval_index = 0
            self._eval_score = ChunkScore(chunk_label=self._chunk_label)
            self._eval_grammar = self.grammar
            self._eval_normalized_grammar = self.normalized_grammar

        # If the grammar is empty, the don't bother evaluating it, or
        # recording it in history -- the score will just be 0.
        if self.normalized_grammar.strip() == "":
            # self._eval_index = self._devset_size.get()
            self._eval_demon_running = False
            return

        # Score the next set of examples
        for gold in self.devset[
            self._eval_index : min(
                self._eval_index + self._EVAL_CHUNK, self._devset_size.get()
            )
        ]:
            guess = self._chunkparse(gold.leaves())
            self._eval_score.score(gold, guess)

        # update our index in the devset.
        self._eval_index += self._EVAL_CHUNK

        # Check if we're done
        if self._eval_index >= self._devset_size.get():
            self._history.append(
                (
                    self._eval_grammar,
                    self._eval_score.precision(),
                    self._eval_score.recall(),
                    self._eval_score.f_measure(),
                )
            )
            self._history_index = len(self._history) - 1
            self._eval_plot()
            self._eval_demon_running = False
            self._eval_normalized_grammar = None
        else:
            progress = 100 * self._eval_index / self._devset_size.get()
            self.status["text"] = "Evaluating on Development Set (%d%%)" % progress
            self._eval_demon_running = True
            self._adaptively_modify_eval_chunk(time.time() - t0)
            self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

    def _adaptively_modify_eval_chunk(self, t):
        """
        Modify _EVAL_CHUNK to try to keep the amount of time that the
        eval demon takes between _EVAL_DEMON_MIN and _EVAL_DEMON_MAX.

        :param t: The amount of time that the eval demon took.
        """
        if t > self._EVAL_DEMON_MAX and self._EVAL_CHUNK > 5:
            self._EVAL_CHUNK = min(
                self._EVAL_CHUNK - 1,
                max(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MAX / t)),
                    self._EVAL_CHUNK - 10,
                ),
            )
        elif t < self._EVAL_DEMON_MIN:
            self._EVAL_CHUNK = max(
                self._EVAL_CHUNK + 1,
                min(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MIN / t)),
                    self._EVAL_CHUNK + 10,
                ),
            )

    def _init_widgets(self, top):
        frame0 = Frame(top, **self._FRAME_PARAMS)
        frame0.grid_columnconfigure(0, weight=4)
        frame0.grid_columnconfigure(3, weight=2)
        frame0.grid_rowconfigure(1, weight=1)
        frame0.grid_rowconfigure(5, weight=1)

        # The grammar
        self.grammarbox = Text(frame0, font=self._font, **self._GRAMMARBOX_PARAMS)
        self.grammarlabel = Label(
            frame0,
            font=self._font,
            text="Grammar:",
            highlightcolor="black",
            background=self._GRAMMARBOX_PARAMS["background"],
        )
        self.grammarlabel.grid(column=0, row=0, sticky="SW")
        self.grammarbox.grid(column=0, row=1, sticky="NEWS")

        # Scroll bar for grammar
        grammar_scrollbar = Scrollbar(frame0, command=self.grammarbox.yview)
        grammar_scrollbar.grid(column=1, row=1, sticky="NWS")
        self.grammarbox.config(yscrollcommand=grammar_scrollbar.set)

        # grammar buttons
        bg = self._FRAME_PARAMS["background"]
        frame3 = Frame(frame0, background=bg)
        frame3.grid(column=0, row=2, sticky="EW")
        Button(
            frame3,
            text="Prev Grammar",
            command=self._history_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame3,
            text="Next Grammar",
            command=self._history_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")

        # Help box
        self.helpbox = Text(frame0, font=self._smallfont, **self._HELPBOX_PARAMS)
        self.helpbox.grid(column=3, row=1, sticky="NEWS")
        self.helptabs = {}
        bg = self._FRAME_PARAMS["background"]
        helptab_frame = Frame(frame0, background=bg)
        helptab_frame.grid(column=3, row=0, sticky="SW")
        for i, (tab, tabstops, text) in enumerate(self.HELP):
            label = Label(helptab_frame, text=tab, font=self._smallfont)
            label.grid(column=i * 2, row=0, sticky="S")
            # help_frame.grid_columnconfigure(i, weight=1)
            # label.pack(side='left')
            label.bind("<ButtonPress>", lambda e, tab=tab: self.show_help(tab))
            self.helptabs[tab] = label
            Frame(
                helptab_frame, height=1, width=self._HELPTAB_SPACER, background=bg
            ).grid(column=i * 2 + 1, row=0)
        self.helptabs[self.HELP[0][0]].configure(font=self._font)
        self.helpbox.tag_config("elide", elide=True)
        for tag, params in self.HELP_AUTOTAG:
            self.helpbox.tag_config("tag-%s" % tag, **params)
        self.show_help(self.HELP[0][0])

        # Scroll bar for helpbox
        help_scrollbar = Scrollbar(frame0, command=self.helpbox.yview)
        self.helpbox.config(yscrollcommand=help_scrollbar.set)
        help_scrollbar.grid(column=4, row=1, sticky="NWS")

        # The dev set
        frame4 = Frame(frame0, background=self._FRAME_PARAMS["background"])
        self.devsetbox = Text(frame4, font=self._font, **self._DEVSETBOX_PARAMS)
        self.devsetbox.pack(expand=True, fill="both")
        self.devsetlabel = Label(
            frame0,
            font=self._font,
            text="Development Set:",
            justify="right",
            background=self._DEVSETBOX_PARAMS["background"],
        )
        self.devsetlabel.grid(column=0, row=4, sticky="SW")
        frame4.grid(column=0, row=5, sticky="NEWS")

        # dev set scrollbars
        self.devset_scroll = Scrollbar(frame0, command=self._devset_scroll)
        self.devset_scroll.grid(column=1, row=5, sticky="NWS")
        self.devset_xscroll = Scrollbar(
            frame4, command=self.devsetbox.xview, orient="horiz"
        )
        self.devsetbox["xscrollcommand"] = self.devset_xscroll.set
        self.devset_xscroll.pack(side="bottom", fill="x")

        # dev set buttons
        bg = self._FRAME_PARAMS["background"]
        frame1 = Frame(frame0, background=bg)
        frame1.grid(column=0, row=7, sticky="EW")
        Button(
            frame1,
            text="Prev Example (Ctrl-p)",
            command=self._devset_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame1,
            text="Next Example (Ctrl-n)",
            command=self._devset_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self.devset_button = Button(
            frame1,
            text="Show example",
            command=self.show_devset,
            state="disabled",
            **self._BUTTON_PARAMS,
        )
        self.devset_button.pack(side="right")
        self.trace_button = Button(
            frame1, text="Show trace", command=self.show_trace, **self._BUTTON_PARAMS
        )
        self.trace_button.pack(side="right")

        # evaluation box
        self.evalbox = Canvas(frame0, **self._EVALBOX_PARAMS)
        label = Label(
            frame0,
            font=self._font,
            text="Evaluation:",
            justify="right",
            background=self._EVALBOX_PARAMS["background"],
        )
        label.grid(column=3, row=4, sticky="SW")
        self.evalbox.grid(column=3, row=5, sticky="NEWS", columnspan=2)

        # evaluation box buttons
        bg = self._FRAME_PARAMS["background"]
        frame2 = Frame(frame0, background=bg)
        frame2.grid(column=3, row=7, sticky="EW")
        self._autoscale = IntVar(self.top)
        self._autoscale.set(False)
        Checkbutton(
            frame2,
            variable=self._autoscale,
            command=self._eval_plot,
            text="Zoom",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self._eval_lines = IntVar(self.top)
        self._eval_lines.set(False)
        Checkbutton(
            frame2,
            variable=self._eval_lines,
            command=self._eval_plot,
            text="Lines",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(frame2, text="History", **self._BUTTON_PARAMS).pack(side="right")

        # The status label
        self.status = Label(frame0, font=self._font, **self._STATUS_PARAMS)
        self.status.grid(column=0, row=9, sticky="NEW", padx=3, pady=2, columnspan=5)

        # Help box & devset box can't be edited.
        self.helpbox["state"] = "disabled"
        self.devsetbox["state"] = "disabled"

        # Spacers
        bg = self._FRAME_PARAMS["background"]
        Frame(frame0, height=10, width=0, background=bg).grid(column=0, row=3)
        Frame(frame0, height=0, width=10, background=bg).grid(column=2, row=0)
        Frame(frame0, height=6, width=0, background=bg).grid(column=0, row=8)

        # pack the frame.
        frame0.pack(fill="both", expand=True)

        # Set up colors for the devset box
        self.devsetbox.tag_config("true-pos", background="#afa", underline="True")
        self.devsetbox.tag_config("false-neg", underline="True", foreground="#800")
        self.devsetbox.tag_config("false-pos", background="#faa")
        self.devsetbox.tag_config("trace", foreground="#666", wrap="none")
        self.devsetbox.tag_config("wrapindent", lmargin2=30, wrap="none")
        self.devsetbox.tag_config("error", foreground="#800")

        # And for the grammarbox
        self.grammarbox.tag_config("error", background="#fec")
        self.grammarbox.tag_config("comment", foreground="#840")
        self.grammarbox.tag_config("angle", foreground="#00f")
        self.grammarbox.tag_config("brace", foreground="#0a0")
        self.grammarbox.tag_config("hangindent", lmargin1=0, lmargin2=40)

    _showing_trace = False

    def show_trace(self, *e):
        self._showing_trace = True
        self.trace_button["state"] = "disabled"
        self.devset_button["state"] = "normal"

        self.devsetbox["state"] = "normal"
        # self.devsetbox['wrap'] = 'none'
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        if self.chunker is None:
            self.devsetbox.insert("1.0", "Trace: waiting for a valid grammar.")
            self.devsetbox.tag_add("error", "1.0", "end")
            return  # can't do anything more

        gold_tree = self.devset[self.devset_index]
        rules = self.chunker.rules()

        # Calculate the tag sequence
        tagseq = "\t"
        charnum = [1]
        for wordnum, (word, pos) in enumerate(gold_tree.leaves()):
            tagseq += "%s " % pos
            charnum.append(len(tagseq))
        self.charnum = {
            (i, j): charnum[j]
            for i in range(len(rules) + 1)
            for j in range(len(charnum))
        }
        self.linenum = {i: i * 2 + 2 for i in range(len(rules) + 1)}

        for i in range(len(rules) + 1):
            if i == 0:
                self.devsetbox.insert("end", "Start:\n")
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            else:
                self.devsetbox.insert("end", "Apply %s:\n" % rules[i - 1])
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            # Display the tag sequence.
            self.devsetbox.insert("end", tagseq + "\n")
            self.devsetbox.tag_add("wrapindent", "end -2c linestart", "end -2c")
            # Run a partial parser, and extract gold & test chunks
            chunker = RegexpChunkParser(rules[:i])
            test_tree = self._chunkparse(gold_tree.leaves())
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(i, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(i, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(i, chunk, "false-pos")
        self.devsetbox.insert("end", "Finished.\n")
        self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")

        # This is a hack, because the x-scrollbar isn't updating its
        # position right -- I'm not sure what the underlying cause is
        # though.  (This is on OS X w/ python 2.5)
        self.top.after(100, self.devset_xscroll.set, 0, 0.3)

    def show_help(self, tab):
        self.helpbox["state"] = "normal"
        self.helpbox.delete("1.0", "end")
        for name, tabstops, text in self.HELP:
            if name == tab:
                text = text.replace(
                    "<<TAGSET>>",
                    "\n".join(
                        "\t%s\t%s" % item
                        for item in sorted(
                            list(self.tagset.items()),
                            key=lambda t_w: re.match(r"\w+", t_w[0])
                            and (0, t_w[0])
                            or (1, t_w[0]),
                        )
                    ),
                )

                self.helptabs[name].config(**self._HELPTAB_FG_PARAMS)
                self.helpbox.config(tabs=tabstops)
                self.helpbox.insert("1.0", text + "\n" * 20)
                C = "1.0 + %d chars"
                for tag, params in self.HELP_AUTOTAG:
                    pattern = f"(?s)(<{tag}>)(.*?)(</{tag}>)"
                    for m in re.finditer(pattern, text):
                        self.helpbox.tag_add("elide", C % m.start(1), C % m.end(1))
                        self.helpbox.tag_add(
                            "tag-%s" % tag, C % m.start(2), C % m.end(2)
                        )
                        self.helpbox.tag_add("elide", C % m.start(3), C % m.end(3))
            else:
                self.helptabs[name].config(**self._HELPTAB_BG_PARAMS)
        self.helpbox["state"] = "disabled"

    def _history_prev(self, *e):
        self._view_history(self._history_index - 1)
        return "break"

    def _history_next(self, *e):
        self._view_history(self._history_index + 1)
        return "break"

    def _view_history(self, index):
        # Bounds & sanity checking:
        index = max(0, min(len(self._history) - 1, index))
        if not self._history:
            return
        # Already viewing the requested history item?
        if index == self._history_index:
            return
        # Show the requested grammar.  It will get added to _history
        # only if they edit it (causing self.update() to get run.)
        self.grammarbox["state"] = "normal"
        self.grammarbox.delete("1.0", "end")
        self.grammarbox.insert("end", self._history[index][0])
        self.grammarbox.mark_set("insert", "1.0")
        self._history_index = index
        self._syntax_highlight_grammar(self._history[index][0])
        # Record the normalized grammar & regenerate the chunker.
        self.normalized_grammar = self.normalize_grammar(self._history[index][0])
        if self.normalized_grammar:
            rules = [
                RegexpChunkRule.fromstring(line)
                for line in self.normalized_grammar.split("\n")
            ]
        else:
            rules = []
        self.chunker = RegexpChunkParser(rules)
        # Show the score.
        self._eval_plot()
        # Update the devset box
        self._highlight_devset()
        if self._showing_trace:
            self.show_trace()
        # Update the grammar label
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar {}/{}:".format(
                self._history_index + 1,
                len(self._history),
            )
        else:
            self.grammarlabel["text"] = "Grammar:"

    def _devset_next(self, *e):
        self._devset_scroll("scroll", 1, "page")
        return "break"

    def _devset_prev(self, *e):
        self._devset_scroll("scroll", -1, "page")
        return "break"

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.destroy()
        self.top = None

    def _devset_scroll(self, command, *args):
        N = 1  # size of a page -- one sentence.
        showing_trace = self._showing_trace
        if command == "scroll" and args[1].startswith("unit"):
            self.show_devset(self.devset_index + int(args[0]))
        elif command == "scroll" and args[1].startswith("page"):
            self.show_devset(self.devset_index + N * int(args[0]))
        elif command == "moveto":
            self.show_devset(int(float(args[0]) * self._devset_size.get()))
        else:
            assert 0, f"bad scroll command {command} {args}"
        if showing_trace:
            self.show_trace()

    def show_devset(self, index=None):
        if index is None:
            index = self.devset_index

        # Bounds checking
        index = min(max(0, index), self._devset_size.get() - 1)

        if index == self.devset_index and not self._showing_trace:
            return
        self.devset_index = index

        self._showing_trace = False
        self.trace_button["state"] = "normal"
        self.devset_button["state"] = "disabled"

        # Clear the text box.
        self.devsetbox["state"] = "normal"
        self.devsetbox["wrap"] = "word"
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        # Add the sentences
        sample = self.devset[self.devset_index : self.devset_index + 1]
        self.charnum = {}
        self.linenum = {0: 1}
        for sentnum, sent in enumerate(sample):
            linestr = ""
            for wordnum, (word, pos) in enumerate(sent.leaves()):
                self.charnum[sentnum, wordnum] = len(linestr)
                linestr += f"{word}/{pos} "
                self.charnum[sentnum, wordnum + 1] = len(linestr)
            self.devsetbox.insert("end", linestr[:-1] + "\n\n")

        # Highlight chunks in the dev set
        if self.chunker is not None:
            self._highlight_devset()
        self.devsetbox["state"] = "disabled"

        # Update the scrollbar
        first = self.devset_index / self._devset_size.get()
        last = (self.devset_index + 2) / self._devset_size.get()
        self.devset_scroll.set(first, last)

    def _chunks(self, tree):
        chunks = set()
        wordnum = 0
        for child in tree:
            if isinstance(child, Tree):
                if child.label() == self._chunk_label:
                    chunks.add((wordnum, wordnum + len(child)))
                wordnum += len(child)
            else:
                wordnum += 1
        return chunks

    def _syntax_highlight_grammar(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("comment", "1.0", "end")
        self.grammarbox.tag_remove("angle", "1.0", "end")
        self.grammarbox.tag_remove("brace", "1.0", "end")
        self.grammarbox.tag_add("hangindent", "1.0", "end")
        for lineno, line in enumerate(grammar.split("\n")):
            if not line.strip():
                continue
            m = re.match(r"(\\.|[^#])*(#.*)?", line)
            comment_start = None
            if m.group(2):
                comment_start = m.start(2)
                s = "%d.%d" % (lineno + 1, m.start(2))
                e = "%d.%d" % (lineno + 1, m.end(2))
                self.grammarbox.tag_add("comment", s, e)
            for m in re.finditer("[<>{}]", line):
                if comment_start is not None and m.start() >= comment_start:
                    break
                s = "%d.%d" % (lineno + 1, m.start())
                e = "%d.%d" % (lineno + 1, m.end())
                if m.group() in "<>":
                    self.grammarbox.tag_add("angle", s, e)
                else:
                    self.grammarbox.tag_add("brace", s, e)

    def _grammarcheck(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("error", "1.0", "end")
        self._grammarcheck_errs = []
        for lineno, line in enumerate(grammar.split("\n")):
            line = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", line)
            line = line.strip()
            if line:
                try:
                    RegexpChunkRule.fromstring(line)
                except ValueError as e:
                    self.grammarbox.tag_add(
                        "error", "%s.0" % (lineno + 1), "%s.0 lineend" % (lineno + 1)
                    )
        self.status["text"] = ""

    def update(self, *event):
        # Record when update was called (for grammarcheck)
        if event:
            self._last_keypress = time.time()

        # Read the grammar from the Text box.
        self.grammar = grammar = self.grammarbox.get("1.0", "end")

        # If the grammar hasn't changed, do nothing:
        normalized_grammar = self.normalize_grammar(grammar)
        if normalized_grammar == self.normalized_grammar:
            return
        else:
            self.normalized_grammar = normalized_grammar

        # If the grammar has changed, and we're looking at history,
        # then stop looking at history.
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar:"

        self._syntax_highlight_grammar(grammar)

        # The grammar has changed; try parsing it.  If it doesn't
        # parse, do nothing.  (flag error location?)
        try:
            # Note: the normalized grammar has no blank lines.
            if normalized_grammar:
                rules = [
                    RegexpChunkRule.fromstring(line)
                    for line in normalized_grammar.split("\n")
                ]
            else:
                rules = []
        except ValueError as e:
            # Use the un-normalized grammar for error highlighting.
            self._grammarcheck(grammar)
            self.chunker = None
            return

        self.chunker = RegexpChunkParser(rules)
        self.grammarbox.tag_remove("error", "1.0", "end")
        self.grammar_changed = time.time()
        # Display the results
        if self._showing_trace:
            self.show_trace()
        else:
            self._highlight_devset()
        # Start the eval demon
        if not self._eval_demon_running:
            self._eval_demon()

    def _highlight_devset(self, sample=None):
        if sample is None:
            sample = self.devset[self.devset_index : self.devset_index + 1]

        self.devsetbox.tag_remove("true-pos", "1.0", "end")
        self.devsetbox.tag_remove("false-neg", "1.0", "end")
        self.devsetbox.tag_remove("false-pos", "1.0", "end")

        # Run the grammar on the test cases.
        for sentnum, gold_tree in enumerate(sample):
            # Run the chunk parser
            test_tree = self._chunkparse(gold_tree.leaves())
            # Extract gold & test chunks
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(sentnum, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(sentnum, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(sentnum, chunk, "false-pos")

    def _chunkparse(self, words):
        try:
            return self.chunker.parse(words)
        except (ValueError, IndexError) as e:
            # There's an error somewhere in the grammar, but we're not sure
            # exactly where, so just mark the whole grammar as bad.
            # E.g., this is caused by: "({<NN>})"
            self.grammarbox.tag_add("error", "1.0", "end")
            # Treat it as tagging nothing:
            return words

    def _color_chunk(self, sentnum, chunk, tag):
        start, end = chunk
        self.devsetbox.tag_add(
            tag,
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, start]}",
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, end] - 1}",
        )

    def reset(self):
        # Clear various variables
        self.chunker = None
        self.grammar = None
        self.normalized_grammar = None
        self.grammar_changed = 0
        self._history = []
        self._history_index = 0
        # Update the on-screen display.
        self.grammarbox.delete("1.0", "end")
        self.show_devset(0)
        self.update()
        # self._eval_plot()

    SAVE_GRAMMAR_TEMPLATE = (
        "# Regexp Chunk Parsing Grammar\n"
        "# Saved %(date)s\n"
        "#\n"
        "# Development set: %(devset)s\n"
        "#   Precision: %(precision)s\n"
        "#   Recall:    %(recall)s\n"
        "#   F-score:   %(fscore)s\n\n"
        "%(grammar)s\n"
    )

    def save_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        if self._history and self.normalized_grammar == self.normalize_grammar(
            self._history[-1][0]
        ):
            precision, recall, fscore = (
                "%.2f%%" % (100 * v) for v in self._history[-1][1:]
            )
        elif self.chunker is None:
            precision = recall = fscore = "Grammar not well formed"
        else:
            precision = recall = fscore = "Not finished evaluation yet"

        with open(filename, "w") as outfile:
            outfile.write(
                self.SAVE_GRAMMAR_TEMPLATE
                % dict(
                    date=time.ctime(),
                    devset=self.devset_name,
                    precision=precision,
                    recall=recall,
                    fscore=fscore,
                    grammar=self.grammar.strip(),
                )
            )

    def load_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = askopenfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        self.grammarbox.delete("1.0", "end")
        self.update()
        with open(filename) as infile:
            grammar = infile.read()
        grammar = re.sub(
            r"^\# Regexp Chunk Parsing Grammar[\s\S]*" "F-score:.*\n", "", grammar
        ).lstrip()
        self.grammarbox.insert("1.0", grammar)
        self.update()

    def save_history(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr History", ".txt"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".txt")
            if not filename:
                return

        with open(filename, "w") as outfile:
            outfile.write("# Regexp Chunk Parsing Grammar History\n")
            outfile.write("# Saved %s\n" % time.ctime())
            outfile.write("# Development set: %s\n" % self.devset_name)
            for i, (g, p, r, f) in enumerate(self._history):
                hdr = (
                    "Grammar %d/%d (precision=%.2f%%, recall=%.2f%%, "
                    "fscore=%.2f%%)"
                    % (i + 1, len(self._history), p * 100, r * 100, f * 100)
                )
                outfile.write("\n%s\n" % hdr)
                outfile.write("".join("  %s\n" % line for line in g.strip().split()))

            if not (
                self._history
                and self.normalized_grammar
                == self.normalize_grammar(self._history[-1][0])
            ):
                if self.chunker is None:
                    outfile.write("\nCurrent Grammar (not well-formed)\n")
                else:
                    outfile.write("\nCurrent Grammar (not evaluated)\n")
                outfile.write(
                    "".join("  %s\n" % line for line in self.grammar.strip().split())
                )

    def about(self, *e):
        ABOUT = "NLTK RegExp Chunk Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Regular Expression Chunk Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def set_devset_size(self, size=None):
        if size is not None:
            self._devset_size.set(size)
        self._devset_size.set(min(len(self.devset), self._devset_size.get()))
        self.show_devset(1)
        self.show_devset(0)
        # what about history?  Evaluated at diff dev set sizes!

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._smallfont.configure(size=min(-10, -(abs(size)) * 14 // 20))

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


def app():
    RegexpChunkApp().mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/openenv\Lib\site-packages\nltk\app\rdparser_app.py ===
# Natural Language Toolkit: Recursive Descent Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the recursive descent parser.

The recursive descent parser maintains a tree, which records the
structure of the portion of the text that has been parsed.  It uses
CFG productions to expand the fringe of the tree, and matches its
leaves against the text.  Initially, the tree contains the start
symbol ("S").  It is shown in the main canvas, to the right of the
list of available expansions.

The parser builds up a tree structure for the text using three
operations:

  - "expand" uses a CFG production to add children to a node on the
    fringe of the tree.
  - "match" compares a leaf in the tree to a text token.
  - "backtrack" returns the tree to its state before the most recent
    expand or match operation.

The parser maintains a list of tree locations called a "frontier" to
remember which nodes have not yet been expanded and which leaves have
not yet been matched against the text.  The leftmost frontier node is
shown in green, and the other frontier nodes are shown in blue.  The
parser always performs expand and match operations on the leftmost
element of the frontier.

You can control the parser's operation by using the "expand," "match,"
and "backtrack" buttons; or you can use the "step" button to let the
parser automatically decide which operation to apply.  The parser uses
the following rules to decide which operation to apply:

  - If the leftmost frontier element is a token, try matching it.
  - If the leftmost frontier element is a node, try expanding it with
    the first untried expansion.
  - Otherwise, backtrack.

The "expand" button applies the untried expansion whose CFG production
is listed earliest in the grammar.  To manually choose which expansion
to apply, click on a CFG production from the list of available
expansions, on the left side of the main window.

The "autostep" button will let the parser continue applying
applications to the tree until it reaches a complete parse.  You can
cancel an autostep in progress at any time by clicking on the
"autostep" button again.

Keyboard Shortcuts::
      [Space]\t Perform the next expand, match, or backtrack operation
      [a]\t Step through operations until the next complete parse
      [e]\t Perform an expand operation
      [m]\t Perform a match operation
      [b]\t Perform a backtrack operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available expansions list
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit
"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingRecursiveDescentParser
from nltk.tree import Tree
from nltk.util import in_idle


class RecursiveDescentApp:
    """
    A graphical tool for exploring the recursive descent parser.  The tool
    displays the parser's tree and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can expand subtrees on the frontier, match tokens on the frontier
    against the text, and backtrack.  A "step" button simply steps
    through the parsing process, performing the operations that
    ``RecursiveDescentParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingRecursiveDescentParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Recursive Descent Parser Application")

        # Set up key bindings.
        self._init_bindings()

        # Initialize the fonts.
        self._init_fonts(self._top)

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animation_frames = IntVar(self._top)
        self._animation_frames.set(5)
        self._animating_lock = 0
        self._autostep = 0

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # Initialize the parser.
        self._parser.initialize(self._sent)

        # Resize callback
        self._canvas.bind("<Configure>", self._configure)

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())
        if self._size.get() < 0:
            big = self._size.get() - 2
        else:
            big = self._size.get() + 2
        self._bigfont = Font(family="helvetica", weight="bold", size=big)

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Expansions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", ("  %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Escape>", self.destroy)
        self._top.bind("e", self.expand)
        # self._top.bind('<Alt-e>', self.expand)
        # self._top.bind('<Control-e>', self.expand)
        self._top.bind("m", self.match)
        self._top.bind("<Alt-m>", self.match)
        self._top.bind("<Control-m>", self.match)
        self._top.bind("b", self.backtrack)
        self._top.bind("<Alt-b>", self.backtrack)
        self._top.bind("<Control-b>", self.backtrack)
        self._top.bind("<Control-z>", self.backtrack)
        self._top.bind("<BackSpace>", self.backtrack)
        self._top.bind("a", self.autostep)
        # self._top.bind('<Control-a>', self.autostep)
        self._top.bind("<Control-space>", self.autostep)
        self._top.bind("<Control-c>", self.cancel_autostep)
        self._top.bind("<space>", self.step)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<Control-p>", self.postscript)
        # self._top.bind('<h>', self.help)
        # self._top.bind('<Alt-h>', self.help)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        # self._top.bind('<g>', self.toggle_grammar)
        # self._top.bind('<Alt-g>', self.toggle_grammar)
        # self._top.bind('<Control-g>', self.toggle_grammar)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom", padx=3, pady=2)
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Autostep",
            background="#90c0d0",
            foreground="black",
            command=self.autostep,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Expand",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.expand,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Match",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.match,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Backtrack",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.backtrack,
        ).pack(side="left")
        # Replace autostep...

    #         self._autostep_button = Button(buttonframe, text='Autostep',
    #                                        underline=0, command=self.autostep)
    #         self._autostep_button.pack(side='left')

    def _configure(self, event):
        self._autostep = 0
        (x1, y1, x2, y2) = self._cframe.scrollregion()
        y2 = event.height - 6
        self._canvas["scrollregion"] = "%d %d %d %d" % (x1, y1, x2, y2)
        self._redraw()

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            # width=525, height=250,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree or text
        self._tree = None
        self._textwidgets = []
        self._textline = None

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Match", underline=0, command=self.match, accelerator="Ctrl-m"
        )
        rulemenu.add_command(
            label="Expand", underline=0, command=self.expand, accelerator="Ctrl-e"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Backtrack", underline=0, command=self.backtrack, accelerator="Ctrl-b"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animation_frames, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animation_frames,
            value=10,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animation_frames,
            value=5,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animation_frames,
            value=2,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    #########################################
    ##  Helper
    #########################################

    def _get(self, widget, treeloc):
        for i in treeloc:
            widget = widget.subtrees()[i]
        if isinstance(widget, TreeSegmentWidget):
            widget = widget.label()
        return widget

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        canvas = self._canvas

        # Delete the old tree, widgets, etc.
        if self._tree is not None:
            self._cframe.destroy_widget(self._tree)
        for twidget in self._textwidgets:
            self._cframe.destroy_widget(twidget)
        if self._textline is not None:
            self._canvas.delete(self._textline)

        # Draw the tree.
        helv = ("helvetica", -self._size.get())
        bold = ("helvetica", -self._size.get(), "bold")
        attribs = {
            "tree_color": "#000000",
            "tree_width": 2,
            "node_font": bold,
            "leaf_font": helv,
        }
        tree = self._parser.tree()
        self._tree = tree_to_treesegment(canvas, tree, **attribs)
        self._cframe.add_widget(self._tree, 30, 5)

        # Draw the text.
        helv = ("helvetica", -self._size.get())
        bottom = y = self._cframe.scrollregion()[3]
        self._textwidgets = [
            TextWidget(canvas, word, font=self._font) for word in self._sent
        ]
        for twidget in self._textwidgets:
            self._cframe.add_widget(twidget, 0, 0)
            twidget.move(0, bottom - twidget.bbox()[3] - 5)
            y = min(y, twidget.bbox()[1])

        # Draw a line over the text, to separate it from the tree.
        self._textline = canvas.create_line(-5000, y - 5, 5000, y - 5, dash=".")

        # Highlight appropriate nodes.
        self._highlight_nodes()
        self._highlight_prodlist()

        # Make sure the text lines up.
        self._position_text()

    def _redraw_quick(self):
        # This should be more-or-less sufficient after an animation.
        self._highlight_nodes()
        self._highlight_prodlist()
        self._position_text()

    def _highlight_nodes(self):
        # Highlight the list of nodes to be checked.
        bold = ("helvetica", -self._size.get(), "bold")
        for treeloc in self._parser.frontier()[:1]:
            self._get(self._tree, treeloc)["color"] = "#20a050"
            self._get(self._tree, treeloc)["font"] = bold
        for treeloc in self._parser.frontier()[1:]:
            self._get(self._tree, treeloc)["color"] = "#008080"

    def _highlight_prodlist(self):
        # Highlight the productions that can be expanded.
        # Boy, too bad tkinter doesn't implement Listbox.itemconfig;
        # that would be pretty useful here.
        self._prodlist.delete(0, "end")
        expandable = self._parser.expandable_productions()
        untried = self._parser.untried_expandable_productions()
        productions = self._productions
        for index in range(len(productions)):
            if productions[index] in expandable:
                if productions[index] in untried:
                    self._prodlist.insert(index, " %s" % productions[index])
                else:
                    self._prodlist.insert(index, " %s (TRIED)" % productions[index])
                self._prodlist.selection_set(index)
            else:
                self._prodlist.insert(index, " %s" % productions[index])

    def _position_text(self):
        # Line up the text widgets that are matched against the tree
        numwords = len(self._sent)
        num_matched = numwords - len(self._parser.remaining_text())
        leaves = self._tree_leaves()[:num_matched]
        xmax = self._tree.bbox()[0]
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            widget["color"] = "#006040"
            leaf["color"] = "#006040"
            widget.move(leaf.bbox()[0] - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # Line up the text widgets that are not matched against the tree.
        for i in range(len(leaves), numwords):
            widget = self._textwidgets[i]
            widget["color"] = "#a0a0a0"
            widget.move(xmax - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # If we have a complete parse, make everything green :)
        if self._parser.currently_complete():
            for twidget in self._textwidgets:
                twidget["color"] = "#00a000"

        # Move the matched leaves down to the text.
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            dy = widget.bbox()[1] - leaf.bbox()[3] - 10.0
            dy = max(dy, leaf.parent().label().bbox()[3] - leaf.bbox()[3] + 10)
            leaf.move(0, dy)

    def _tree_leaves(self, tree=None):
        if tree is None:
            tree = self._tree
        if isinstance(tree, TreeSegmentWidget):
            leaves = []
            for child in tree.subtrees():
                leaves += self._tree_leaves(child)
            return leaves
        else:
            return [tree]

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._autostep = 0
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset Application"
        self._lastoper2["text"] = ""
        self._redraw()

    def autostep(self, *e):
        if self._animation_frames.get() == 0:
            self._animation_frames.set(2)
        if self._autostep:
            self._autostep = 0
        else:
            self._autostep = 1
            self._step()

    def cancel_autostep(self, *e):
        # self._autostep_button['text'] = 'Autostep'
        self._autostep = 0

    # Make sure to stop auto-stepping if we get any user input.
    def step(self, *e):
        self._autostep = 0
        self._step()

    def match(self, *e):
        self._autostep = 0
        self._match()

    def expand(self, *e):
        self._autostep = 0
        self._expand()

    def backtrack(self, *e):
        self._autostep = 0
        self._backtrack()

    def _step(self):
        if self._animating_lock:
            return

        # Try expanding, matching, and backtracking (in that order)
        if self._expand():
            pass
        elif self._parser.untried_match() and self._match():
            pass
        elif self._backtrack():
            pass
        else:
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            self._autostep = 0

        # Check if we just completed a parse.
        if self._parser.currently_complete():
            self._autostep = 0
            self._lastoper2["text"] += "    [COMPLETE PARSE]"

    def _expand(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.expand()
        if rv is not None:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = rv
            self._prodlist.selection_clear(0, "end")
            index = self._productions.index(rv)
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = "(all expansions tried)"
            return False

    def _match(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.match()
        if rv is not None:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = rv
            self._animate_match(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = "(failed)"
            return False

    def _backtrack(self, *e):
        if self._animating_lock:
            return
        if self._parser.backtrack():
            elt = self._parser.tree()
            for i in self._parser.frontier()[0]:
                elt = elt[i]
            self._lastoper1["text"] = "Backtrack"
            self._lastoper2["text"] = ""
            if isinstance(elt, Tree):
                self._animate_backtrack(self._parser.frontier()[0])
            else:
                self._animate_match_backtrack(self._parser.frontier()[0])
            return True
        else:
            self._autostep = 0
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            return False

    def about(self, *e):
        ABOUT = (
            "NLTK Recursive Descent Parser Application\n" + "Written by Edward Loper"
        )
        TITLE = "About: Recursive Descent Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def help(self, *e):
        self._autostep = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def postscript(self, *e):
        self._autostep = 0
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))
        self._bigfont.configure(size=-(abs(size + 2)))
        self._redraw()

    #########################################
    ##  Expand Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    #     def toggle_grammar(self, *e):
    #         self._show_grammar = not self._show_grammar
    #         if self._show_grammar:
    #             self._prodframe.pack(fill='both', expand='y', side='left',
    #                                  after=self._feedbackframe)
    #             self._lastoper1['text'] = 'Show Grammar'
    #         else:
    #             self._prodframe.pack_forget()
    #             self._lastoper1['text'] = 'Hide Grammar'
    #         self._lastoper2['text'] = ''

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        old_frontier = self._parser.frontier()
        production = self._parser.expand(self._productions[index])

        if production:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = production
            self._prodlist.selection_clear(0, "end")
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.expandable_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    #########################################
    ##  Animation
    #########################################

    def _animate_expand(self, treeloc):
        oldwidget = self._get(self._tree, treeloc)
        oldtree = oldwidget.parent()
        top = not isinstance(oldtree.parent(), TreeSegmentWidget)

        tree = self._parser.tree()
        for i in treeloc:
            tree = tree[i]

        widget = tree_to_treesegment(
            self._canvas,
            tree,
            node_font=self._boldfont,
            leaf_color="white",
            tree_width=2,
            tree_color="white",
            node_color="white",
            leaf_font=self._font,
        )
        widget.label()["color"] = "#20a050"

        (oldx, oldy) = oldtree.label().bbox()[:2]
        (newx, newy) = widget.label().bbox()[:2]
        widget.move(oldx - newx, oldy - newy)

        if top:
            self._cframe.add_widget(widget, 0, 5)
            widget.move(30 - widget.label().bbox()[0], 0)
            self._tree = widget
        else:
            oldtree.parent().replace_child(oldtree, widget)

        # Move the children over so they don't overlap.
        # Line the children up in a strange way.
        if widget.subtrees():
            dx = (
                oldx
                + widget.label().width() / 2
                - widget.subtrees()[0].bbox()[0] / 2
                - widget.subtrees()[0].bbox()[2] / 2
            )
            for subtree in widget.subtrees():
                subtree.move(dx, 0)

        self._makeroom(widget)

        if top:
            self._cframe.destroy_widget(oldtree)
        else:
            oldtree.destroy()

        colors = [
            "gray%d" % (10 * int(10 * x / self._animation_frames.get()))
            for x in range(self._animation_frames.get(), 0, -1)
        ]

        # Move the text string down, if necessary.
        dy = widget.bbox()[3] + 30 - self._canvas.coords(self._textline)[1]
        if dy > 0:
            for twidget in self._textwidgets:
                twidget.move(0, dy)
            self._canvas.move(self._textline, 0, dy)

        self._animate_expand_frame(widget, colors)

    def _makeroom(self, treeseg):
        """
        Make sure that no sibling tree bbox's overlap.
        """
        parent = treeseg.parent()
        if not isinstance(parent, TreeSegmentWidget):
            return

        index = parent.subtrees().index(treeseg)

        # Handle siblings to the right
        rsiblings = parent.subtrees()[index + 1 :]
        if rsiblings:
            dx = treeseg.bbox()[2] - rsiblings[0].bbox()[0] + 10
            for sibling in rsiblings:
                sibling.move(dx, 0)

        # Handle siblings to the left
        if index > 0:
            lsibling = parent.subtrees()[index - 1]
            dx = max(0, lsibling.bbox()[2] - treeseg.bbox()[0] + 10)
            treeseg.move(dx, 0)

        # Keep working up the tree.
        self._makeroom(parent)

    def _animate_expand_frame(self, widget, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            widget["color"] = colors[0]
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = colors[0]
                else:
                    subtree["color"] = colors[0]
            self._top.after(50, self._animate_expand_frame, widget, colors[1:])
        else:
            widget["color"] = "black"
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = "black"
                else:
                    subtree["color"] = "black"
            self._redraw_quick()
            widget.label()["color"] = "black"
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_backtrack(self, treeloc):
        # Flash red first, if we're animating.
        if self._animation_frames.get() == 0:
            colors = []
        else:
            colors = ["#a00000", "#000000", "#a00000"]
        colors += [
            "gray%d" % (10 * int(10 * x / (self._animation_frames.get())))
            for x in range(1, self._animation_frames.get() + 1)
        ]

        widgets = [self._get(self._tree, treeloc).parent()]
        for subtree in widgets[0].subtrees():
            if isinstance(subtree, TreeSegmentWidget):
                widgets.append(subtree.label())
            else:
                widgets.append(subtree)

        self._animate_backtrack_frame(widgets, colors)

    def _animate_backtrack_frame(self, widgets, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget["color"] = colors[0]
            self._top.after(50, self._animate_backtrack_frame, widgets, colors[1:])
        else:
            for widget in widgets[0].subtrees():
                widgets[0].remove_child(widget)
                widget.destroy()
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack(self, treeloc):
        widget = self._get(self._tree, treeloc)
        node = widget.parent().label()
        dy = (node.bbox()[3] - widget.bbox()[1] + 14) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_backtrack_frame(self._animation_frames.get(), widget, dy)

    def _animate_match(self, treeloc):
        widget = self._get(self._tree, treeloc)

        dy = (self._textwidgets[0].bbox()[1] - widget.bbox()[3] - 10.0) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_frame(self._animation_frames.get(), widget, dy)

    def _animate_match_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(10, self._animate_match_frame, frame - 1, widget, dy)
        else:
            widget["color"] = "#006040"
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(
                10, self._animate_match_backtrack_frame, frame - 1, widget, dy
            )
        else:
            widget.parent().remove_child(widget)
            widget.destroy()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._sent = sentence.split()  # [XX] use tagged?
        self.reset()


def app():
    """
    Create a recursive descent parser demo, using a simple grammar and
    text.
    """
    from nltk.grammar import CFG

    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        NP -> Det N PP | Det N
        VP -> V NP PP | V NP | V
        PP -> P NP
    # Lexical productions.
        NP -> 'I'
        Det -> 'the' | 'a'
        N -> 'man' | 'park' | 'dog' | 'telescope'
        V -> 'ate' | 'saw'
        P -> 'in' | 'under' | 'with'
    """
    )

    sent = "the dog saw a man in the park".split()

    RecursiveDescentApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\rdparser_app.py ===
# Natural Language Toolkit: Recursive Descent Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the recursive descent parser.

The recursive descent parser maintains a tree, which records the
structure of the portion of the text that has been parsed.  It uses
CFG productions to expand the fringe of the tree, and matches its
leaves against the text.  Initially, the tree contains the start
symbol ("S").  It is shown in the main canvas, to the right of the
list of available expansions.

The parser builds up a tree structure for the text using three
operations:

  - "expand" uses a CFG production to add children to a node on the
    fringe of the tree.
  - "match" compares a leaf in the tree to a text token.
  - "backtrack" returns the tree to its state before the most recent
    expand or match operation.

The parser maintains a list of tree locations called a "frontier" to
remember which nodes have not yet been expanded and which leaves have
not yet been matched against the text.  The leftmost frontier node is
shown in green, and the other frontier nodes are shown in blue.  The
parser always performs expand and match operations on the leftmost
element of the frontier.

You can control the parser's operation by using the "expand," "match,"
and "backtrack" buttons; or you can use the "step" button to let the
parser automatically decide which operation to apply.  The parser uses
the following rules to decide which operation to apply:

  - If the leftmost frontier element is a token, try matching it.
  - If the leftmost frontier element is a node, try expanding it with
    the first untried expansion.
  - Otherwise, backtrack.

The "expand" button applies the untried expansion whose CFG production
is listed earliest in the grammar.  To manually choose which expansion
to apply, click on a CFG production from the list of available
expansions, on the left side of the main window.

The "autostep" button will let the parser continue applying
applications to the tree until it reaches a complete parse.  You can
cancel an autostep in progress at any time by clicking on the
"autostep" button again.

Keyboard Shortcuts::
      [Space]\t Perform the next expand, match, or backtrack operation
      [a]\t Step through operations until the next complete parse
      [e]\t Perform an expand operation
      [m]\t Perform a match operation
      [b]\t Perform a backtrack operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available expansions list
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit
"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingRecursiveDescentParser
from nltk.tree import Tree
from nltk.util import in_idle


class RecursiveDescentApp:
    """
    A graphical tool for exploring the recursive descent parser.  The tool
    displays the parser's tree and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can expand subtrees on the frontier, match tokens on the frontier
    against the text, and backtrack.  A "step" button simply steps
    through the parsing process, performing the operations that
    ``RecursiveDescentParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingRecursiveDescentParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Recursive Descent Parser Application")

        # Set up key bindings.
        self._init_bindings()

        # Initialize the fonts.
        self._init_fonts(self._top)

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animation_frames = IntVar(self._top)
        self._animation_frames.set(5)
        self._animating_lock = 0
        self._autostep = 0

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # Initialize the parser.
        self._parser.initialize(self._sent)

        # Resize callback
        self._canvas.bind("<Configure>", self._configure)

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())
        if self._size.get() < 0:
            big = self._size.get() - 2
        else:
            big = self._size.get() + 2
        self._bigfont = Font(family="helvetica", weight="bold", size=big)

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Expansions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", ("  %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Escape>", self.destroy)
        self._top.bind("e", self.expand)
        # self._top.bind('<Alt-e>', self.expand)
        # self._top.bind('<Control-e>', self.expand)
        self._top.bind("m", self.match)
        self._top.bind("<Alt-m>", self.match)
        self._top.bind("<Control-m>", self.match)
        self._top.bind("b", self.backtrack)
        self._top.bind("<Alt-b>", self.backtrack)
        self._top.bind("<Control-b>", self.backtrack)
        self._top.bind("<Control-z>", self.backtrack)
        self._top.bind("<BackSpace>", self.backtrack)
        self._top.bind("a", self.autostep)
        # self._top.bind('<Control-a>', self.autostep)
        self._top.bind("<Control-space>", self.autostep)
        self._top.bind("<Control-c>", self.cancel_autostep)
        self._top.bind("<space>", self.step)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<Control-p>", self.postscript)
        # self._top.bind('<h>', self.help)
        # self._top.bind('<Alt-h>', self.help)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        # self._top.bind('<g>', self.toggle_grammar)
        # self._top.bind('<Alt-g>', self.toggle_grammar)
        # self._top.bind('<Control-g>', self.toggle_grammar)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom", padx=3, pady=2)
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Autostep",
            background="#90c0d0",
            foreground="black",
            command=self.autostep,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Expand",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.expand,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Match",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.match,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Backtrack",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.backtrack,
        ).pack(side="left")
        # Replace autostep...

    #         self._autostep_button = Button(buttonframe, text='Autostep',
    #                                        underline=0, command=self.autostep)
    #         self._autostep_button.pack(side='left')

    def _configure(self, event):
        self._autostep = 0
        (x1, y1, x2, y2) = self._cframe.scrollregion()
        y2 = event.height - 6
        self._canvas["scrollregion"] = "%d %d %d %d" % (x1, y1, x2, y2)
        self._redraw()

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            # width=525, height=250,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree or text
        self._tree = None
        self._textwidgets = []
        self._textline = None

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Match", underline=0, command=self.match, accelerator="Ctrl-m"
        )
        rulemenu.add_command(
            label="Expand", underline=0, command=self.expand, accelerator="Ctrl-e"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Backtrack", underline=0, command=self.backtrack, accelerator="Ctrl-b"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animation_frames, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animation_frames,
            value=10,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animation_frames,
            value=5,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animation_frames,
            value=2,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    #########################################
    ##  Helper
    #########################################

    def _get(self, widget, treeloc):
        for i in treeloc:
            widget = widget.subtrees()[i]
        if isinstance(widget, TreeSegmentWidget):
            widget = widget.label()
        return widget

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        canvas = self._canvas

        # Delete the old tree, widgets, etc.
        if self._tree is not None:
            self._cframe.destroy_widget(self._tree)
        for twidget in self._textwidgets:
            self._cframe.destroy_widget(twidget)
        if self._textline is not None:
            self._canvas.delete(self._textline)

        # Draw the tree.
        helv = ("helvetica", -self._size.get())
        bold = ("helvetica", -self._size.get(), "bold")
        attribs = {
            "tree_color": "#000000",
            "tree_width": 2,
            "node_font": bold,
            "leaf_font": helv,
        }
        tree = self._parser.tree()
        self._tree = tree_to_treesegment(canvas, tree, **attribs)
        self._cframe.add_widget(self._tree, 30, 5)

        # Draw the text.
        helv = ("helvetica", -self._size.get())
        bottom = y = self._cframe.scrollregion()[3]
        self._textwidgets = [
            TextWidget(canvas, word, font=self._font) for word in self._sent
        ]
        for twidget in self._textwidgets:
            self._cframe.add_widget(twidget, 0, 0)
            twidget.move(0, bottom - twidget.bbox()[3] - 5)
            y = min(y, twidget.bbox()[1])

        # Draw a line over the text, to separate it from the tree.
        self._textline = canvas.create_line(-5000, y - 5, 5000, y - 5, dash=".")

        # Highlight appropriate nodes.
        self._highlight_nodes()
        self._highlight_prodlist()

        # Make sure the text lines up.
        self._position_text()

    def _redraw_quick(self):
        # This should be more-or-less sufficient after an animation.
        self._highlight_nodes()
        self._highlight_prodlist()
        self._position_text()

    def _highlight_nodes(self):
        # Highlight the list of nodes to be checked.
        bold = ("helvetica", -self._size.get(), "bold")
        for treeloc in self._parser.frontier()[:1]:
            self._get(self._tree, treeloc)["color"] = "#20a050"
            self._get(self._tree, treeloc)["font"] = bold
        for treeloc in self._parser.frontier()[1:]:
            self._get(self._tree, treeloc)["color"] = "#008080"

    def _highlight_prodlist(self):
        # Highlight the productions that can be expanded.
        # Boy, too bad tkinter doesn't implement Listbox.itemconfig;
        # that would be pretty useful here.
        self._prodlist.delete(0, "end")
        expandable = self._parser.expandable_productions()
        untried = self._parser.untried_expandable_productions()
        productions = self._productions
        for index in range(len(productions)):
            if productions[index] in expandable:
                if productions[index] in untried:
                    self._prodlist.insert(index, " %s" % productions[index])
                else:
                    self._prodlist.insert(index, " %s (TRIED)" % productions[index])
                self._prodlist.selection_set(index)
            else:
                self._prodlist.insert(index, " %s" % productions[index])

    def _position_text(self):
        # Line up the text widgets that are matched against the tree
        numwords = len(self._sent)
        num_matched = numwords - len(self._parser.remaining_text())
        leaves = self._tree_leaves()[:num_matched]
        xmax = self._tree.bbox()[0]
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            widget["color"] = "#006040"
            leaf["color"] = "#006040"
            widget.move(leaf.bbox()[0] - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # Line up the text widgets that are not matched against the tree.
        for i in range(len(leaves), numwords):
            widget = self._textwidgets[i]
            widget["color"] = "#a0a0a0"
            widget.move(xmax - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # If we have a complete parse, make everything green :)
        if self._parser.currently_complete():
            for twidget in self._textwidgets:
                twidget["color"] = "#00a000"

        # Move the matched leaves down to the text.
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            dy = widget.bbox()[1] - leaf.bbox()[3] - 10.0
            dy = max(dy, leaf.parent().label().bbox()[3] - leaf.bbox()[3] + 10)
            leaf.move(0, dy)

    def _tree_leaves(self, tree=None):
        if tree is None:
            tree = self._tree
        if isinstance(tree, TreeSegmentWidget):
            leaves = []
            for child in tree.subtrees():
                leaves += self._tree_leaves(child)
            return leaves
        else:
            return [tree]

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._autostep = 0
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset Application"
        self._lastoper2["text"] = ""
        self._redraw()

    def autostep(self, *e):
        if self._animation_frames.get() == 0:
            self._animation_frames.set(2)
        if self._autostep:
            self._autostep = 0
        else:
            self._autostep = 1
            self._step()

    def cancel_autostep(self, *e):
        # self._autostep_button['text'] = 'Autostep'
        self._autostep = 0

    # Make sure to stop auto-stepping if we get any user input.
    def step(self, *e):
        self._autostep = 0
        self._step()

    def match(self, *e):
        self._autostep = 0
        self._match()

    def expand(self, *e):
        self._autostep = 0
        self._expand()

    def backtrack(self, *e):
        self._autostep = 0
        self._backtrack()

    def _step(self):
        if self._animating_lock:
            return

        # Try expanding, matching, and backtracking (in that order)
        if self._expand():
            pass
        elif self._parser.untried_match() and self._match():
            pass
        elif self._backtrack():
            pass
        else:
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            self._autostep = 0

        # Check if we just completed a parse.
        if self._parser.currently_complete():
            self._autostep = 0
            self._lastoper2["text"] += "    [COMPLETE PARSE]"

    def _expand(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.expand()
        if rv is not None:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = rv
            self._prodlist.selection_clear(0, "end")
            index = self._productions.index(rv)
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = "(all expansions tried)"
            return False

    def _match(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.match()
        if rv is not None:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = rv
            self._animate_match(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = "(failed)"
            return False

    def _backtrack(self, *e):
        if self._animating_lock:
            return
        if self._parser.backtrack():
            elt = self._parser.tree()
            for i in self._parser.frontier()[0]:
                elt = elt[i]
            self._lastoper1["text"] = "Backtrack"
            self._lastoper2["text"] = ""
            if isinstance(elt, Tree):
                self._animate_backtrack(self._parser.frontier()[0])
            else:
                self._animate_match_backtrack(self._parser.frontier()[0])
            return True
        else:
            self._autostep = 0
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            return False

    def about(self, *e):
        ABOUT = (
            "NLTK Recursive Descent Parser Application\n" + "Written by Edward Loper"
        )
        TITLE = "About: Recursive Descent Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def help(self, *e):
        self._autostep = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def postscript(self, *e):
        self._autostep = 0
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))
        self._bigfont.configure(size=-(abs(size + 2)))
        self._redraw()

    #########################################
    ##  Expand Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    #     def toggle_grammar(self, *e):
    #         self._show_grammar = not self._show_grammar
    #         if self._show_grammar:
    #             self._prodframe.pack(fill='both', expand='y', side='left',
    #                                  after=self._feedbackframe)
    #             self._lastoper1['text'] = 'Show Grammar'
    #         else:
    #             self._prodframe.pack_forget()
    #             self._lastoper1['text'] = 'Hide Grammar'
    #         self._lastoper2['text'] = ''

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        old_frontier = self._parser.frontier()
        production = self._parser.expand(self._productions[index])

        if production:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = production
            self._prodlist.selection_clear(0, "end")
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.expandable_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    #########################################
    ##  Animation
    #########################################

    def _animate_expand(self, treeloc):
        oldwidget = self._get(self._tree, treeloc)
        oldtree = oldwidget.parent()
        top = not isinstance(oldtree.parent(), TreeSegmentWidget)

        tree = self._parser.tree()
        for i in treeloc:
            tree = tree[i]

        widget = tree_to_treesegment(
            self._canvas,
            tree,
            node_font=self._boldfont,
            leaf_color="white",
            tree_width=2,
            tree_color="white",
            node_color="white",
            leaf_font=self._font,
        )
        widget.label()["color"] = "#20a050"

        (oldx, oldy) = oldtree.label().bbox()[:2]
        (newx, newy) = widget.label().bbox()[:2]
        widget.move(oldx - newx, oldy - newy)

        if top:
            self._cframe.add_widget(widget, 0, 5)
            widget.move(30 - widget.label().bbox()[0], 0)
            self._tree = widget
        else:
            oldtree.parent().replace_child(oldtree, widget)

        # Move the children over so they don't overlap.
        # Line the children up in a strange way.
        if widget.subtrees():
            dx = (
                oldx
                + widget.label().width() / 2
                - widget.subtrees()[0].bbox()[0] / 2
                - widget.subtrees()[0].bbox()[2] / 2
            )
            for subtree in widget.subtrees():
                subtree.move(dx, 0)

        self._makeroom(widget)

        if top:
            self._cframe.destroy_widget(oldtree)
        else:
            oldtree.destroy()

        colors = [
            "gray%d" % (10 * int(10 * x / self._animation_frames.get()))
            for x in range(self._animation_frames.get(), 0, -1)
        ]

        # Move the text string down, if necessary.
        dy = widget.bbox()[3] + 30 - self._canvas.coords(self._textline)[1]
        if dy > 0:
            for twidget in self._textwidgets:
                twidget.move(0, dy)
            self._canvas.move(self._textline, 0, dy)

        self._animate_expand_frame(widget, colors)

    def _makeroom(self, treeseg):
        """
        Make sure that no sibling tree bbox's overlap.
        """
        parent = treeseg.parent()
        if not isinstance(parent, TreeSegmentWidget):
            return

        index = parent.subtrees().index(treeseg)

        # Handle siblings to the right
        rsiblings = parent.subtrees()[index + 1 :]
        if rsiblings:
            dx = treeseg.bbox()[2] - rsiblings[0].bbox()[0] + 10
            for sibling in rsiblings:
                sibling.move(dx, 0)

        # Handle siblings to the left
        if index > 0:
            lsibling = parent.subtrees()[index - 1]
            dx = max(0, lsibling.bbox()[2] - treeseg.bbox()[0] + 10)
            treeseg.move(dx, 0)

        # Keep working up the tree.
        self._makeroom(parent)

    def _animate_expand_frame(self, widget, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            widget["color"] = colors[0]
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = colors[0]
                else:
                    subtree["color"] = colors[0]
            self._top.after(50, self._animate_expand_frame, widget, colors[1:])
        else:
            widget["color"] = "black"
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = "black"
                else:
                    subtree["color"] = "black"
            self._redraw_quick()
            widget.label()["color"] = "black"
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_backtrack(self, treeloc):
        # Flash red first, if we're animating.
        if self._animation_frames.get() == 0:
            colors = []
        else:
            colors = ["#a00000", "#000000", "#a00000"]
        colors += [
            "gray%d" % (10 * int(10 * x / (self._animation_frames.get())))
            for x in range(1, self._animation_frames.get() + 1)
        ]

        widgets = [self._get(self._tree, treeloc).parent()]
        for subtree in widgets[0].subtrees():
            if isinstance(subtree, TreeSegmentWidget):
                widgets.append(subtree.label())
            else:
                widgets.append(subtree)

        self._animate_backtrack_frame(widgets, colors)

    def _animate_backtrack_frame(self, widgets, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget["color"] = colors[0]
            self._top.after(50, self._animate_backtrack_frame, widgets, colors[1:])
        else:
            for widget in widgets[0].subtrees():
                widgets[0].remove_child(widget)
                widget.destroy()
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack(self, treeloc):
        widget = self._get(self._tree, treeloc)
        node = widget.parent().label()
        dy = (node.bbox()[3] - widget.bbox()[1] + 14) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_backtrack_frame(self._animation_frames.get(), widget, dy)

    def _animate_match(self, treeloc):
        widget = self._get(self._tree, treeloc)

        dy = (self._textwidgets[0].bbox()[1] - widget.bbox()[3] - 10.0) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_frame(self._animation_frames.get(), widget, dy)

    def _animate_match_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(10, self._animate_match_frame, frame - 1, widget, dy)
        else:
            widget["color"] = "#006040"
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(
                10, self._animate_match_backtrack_frame, frame - 1, widget, dy
            )
        else:
            widget.parent().remove_child(widget)
            widget.destroy()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._sent = sentence.split()  # [XX] use tagged?
        self.reset()


def app():
    """
    Create a recursive descent parser demo, using a simple grammar and
    text.
    """
    from nltk.grammar import CFG

    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        NP -> Det N PP | Det N
        VP -> V NP PP | V NP | V
        PP -> P NP
    # Lexical productions.
        NP -> 'I'
        Det -> 'the' | 'a'
        N -> 'man' | 'park' | 'dog' | 'telescope'
        V -> 'ate' | 'saw'
        P -> 'in' | 'under' | 'with'
    """
    )

    sent = "the dog saw a man in the park".split()

    RecursiveDescentApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\rdparser_app.py ===
# Natural Language Toolkit: Recursive Descent Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the recursive descent parser.

The recursive descent parser maintains a tree, which records the
structure of the portion of the text that has been parsed.  It uses
CFG productions to expand the fringe of the tree, and matches its
leaves against the text.  Initially, the tree contains the start
symbol ("S").  It is shown in the main canvas, to the right of the
list of available expansions.

The parser builds up a tree structure for the text using three
operations:

  - "expand" uses a CFG production to add children to a node on the
    fringe of the tree.
  - "match" compares a leaf in the tree to a text token.
  - "backtrack" returns the tree to its state before the most recent
    expand or match operation.

The parser maintains a list of tree locations called a "frontier" to
remember which nodes have not yet been expanded and which leaves have
not yet been matched against the text.  The leftmost frontier node is
shown in green, and the other frontier nodes are shown in blue.  The
parser always performs expand and match operations on the leftmost
element of the frontier.

You can control the parser's operation by using the "expand," "match,"
and "backtrack" buttons; or you can use the "step" button to let the
parser automatically decide which operation to apply.  The parser uses
the following rules to decide which operation to apply:

  - If the leftmost frontier element is a token, try matching it.
  - If the leftmost frontier element is a node, try expanding it with
    the first untried expansion.
  - Otherwise, backtrack.

The "expand" button applies the untried expansion whose CFG production
is listed earliest in the grammar.  To manually choose which expansion
to apply, click on a CFG production from the list of available
expansions, on the left side of the main window.

The "autostep" button will let the parser continue applying
applications to the tree until it reaches a complete parse.  You can
cancel an autostep in progress at any time by clicking on the
"autostep" button again.

Keyboard Shortcuts::
      [Space]\t Perform the next expand, match, or backtrack operation
      [a]\t Step through operations until the next complete parse
      [e]\t Perform an expand operation
      [m]\t Perform a match operation
      [b]\t Perform a backtrack operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available expansions list
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit
"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingRecursiveDescentParser
from nltk.tree import Tree
from nltk.util import in_idle


class RecursiveDescentApp:
    """
    A graphical tool for exploring the recursive descent parser.  The tool
    displays the parser's tree and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can expand subtrees on the frontier, match tokens on the frontier
    against the text, and backtrack.  A "step" button simply steps
    through the parsing process, performing the operations that
    ``RecursiveDescentParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingRecursiveDescentParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Recursive Descent Parser Application")

        # Set up key bindings.
        self._init_bindings()

        # Initialize the fonts.
        self._init_fonts(self._top)

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animation_frames = IntVar(self._top)
        self._animation_frames.set(5)
        self._animating_lock = 0
        self._autostep = 0

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # Initialize the parser.
        self._parser.initialize(self._sent)

        # Resize callback
        self._canvas.bind("<Configure>", self._configure)

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())
        if self._size.get() < 0:
            big = self._size.get() - 2
        else:
            big = self._size.get() + 2
        self._bigfont = Font(family="helvetica", weight="bold", size=big)

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Expansions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", ("  %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Escape>", self.destroy)
        self._top.bind("e", self.expand)
        # self._top.bind('<Alt-e>', self.expand)
        # self._top.bind('<Control-e>', self.expand)
        self._top.bind("m", self.match)
        self._top.bind("<Alt-m>", self.match)
        self._top.bind("<Control-m>", self.match)
        self._top.bind("b", self.backtrack)
        self._top.bind("<Alt-b>", self.backtrack)
        self._top.bind("<Control-b>", self.backtrack)
        self._top.bind("<Control-z>", self.backtrack)
        self._top.bind("<BackSpace>", self.backtrack)
        self._top.bind("a", self.autostep)
        # self._top.bind('<Control-a>', self.autostep)
        self._top.bind("<Control-space>", self.autostep)
        self._top.bind("<Control-c>", self.cancel_autostep)
        self._top.bind("<space>", self.step)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<Control-p>", self.postscript)
        # self._top.bind('<h>', self.help)
        # self._top.bind('<Alt-h>', self.help)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        # self._top.bind('<g>', self.toggle_grammar)
        # self._top.bind('<Alt-g>', self.toggle_grammar)
        # self._top.bind('<Control-g>', self.toggle_grammar)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom", padx=3, pady=2)
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Autostep",
            background="#90c0d0",
            foreground="black",
            command=self.autostep,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Expand",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.expand,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Match",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.match,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Backtrack",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.backtrack,
        ).pack(side="left")
        # Replace autostep...

    #         self._autostep_button = Button(buttonframe, text='Autostep',
    #                                        underline=0, command=self.autostep)
    #         self._autostep_button.pack(side='left')

    def _configure(self, event):
        self._autostep = 0
        (x1, y1, x2, y2) = self._cframe.scrollregion()
        y2 = event.height - 6
        self._canvas["scrollregion"] = "%d %d %d %d" % (x1, y1, x2, y2)
        self._redraw()

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            # width=525, height=250,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree or text
        self._tree = None
        self._textwidgets = []
        self._textline = None

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Match", underline=0, command=self.match, accelerator="Ctrl-m"
        )
        rulemenu.add_command(
            label="Expand", underline=0, command=self.expand, accelerator="Ctrl-e"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Backtrack", underline=0, command=self.backtrack, accelerator="Ctrl-b"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animation_frames, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animation_frames,
            value=10,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animation_frames,
            value=5,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animation_frames,
            value=2,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    #########################################
    ##  Helper
    #########################################

    def _get(self, widget, treeloc):
        for i in treeloc:
            widget = widget.subtrees()[i]
        if isinstance(widget, TreeSegmentWidget):
            widget = widget.label()
        return widget

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        canvas = self._canvas

        # Delete the old tree, widgets, etc.
        if self._tree is not None:
            self._cframe.destroy_widget(self._tree)
        for twidget in self._textwidgets:
            self._cframe.destroy_widget(twidget)
        if self._textline is not None:
            self._canvas.delete(self._textline)

        # Draw the tree.
        helv = ("helvetica", -self._size.get())
        bold = ("helvetica", -self._size.get(), "bold")
        attribs = {
            "tree_color": "#000000",
            "tree_width": 2,
            "node_font": bold,
            "leaf_font": helv,
        }
        tree = self._parser.tree()
        self._tree = tree_to_treesegment(canvas, tree, **attribs)
        self._cframe.add_widget(self._tree, 30, 5)

        # Draw the text.
        helv = ("helvetica", -self._size.get())
        bottom = y = self._cframe.scrollregion()[3]
        self._textwidgets = [
            TextWidget(canvas, word, font=self._font) for word in self._sent
        ]
        for twidget in self._textwidgets:
            self._cframe.add_widget(twidget, 0, 0)
            twidget.move(0, bottom - twidget.bbox()[3] - 5)
            y = min(y, twidget.bbox()[1])

        # Draw a line over the text, to separate it from the tree.
        self._textline = canvas.create_line(-5000, y - 5, 5000, y - 5, dash=".")

        # Highlight appropriate nodes.
        self._highlight_nodes()
        self._highlight_prodlist()

        # Make sure the text lines up.
        self._position_text()

    def _redraw_quick(self):
        # This should be more-or-less sufficient after an animation.
        self._highlight_nodes()
        self._highlight_prodlist()
        self._position_text()

    def _highlight_nodes(self):
        # Highlight the list of nodes to be checked.
        bold = ("helvetica", -self._size.get(), "bold")
        for treeloc in self._parser.frontier()[:1]:
            self._get(self._tree, treeloc)["color"] = "#20a050"
            self._get(self._tree, treeloc)["font"] = bold
        for treeloc in self._parser.frontier()[1:]:
            self._get(self._tree, treeloc)["color"] = "#008080"

    def _highlight_prodlist(self):
        # Highlight the productions that can be expanded.
        # Boy, too bad tkinter doesn't implement Listbox.itemconfig;
        # that would be pretty useful here.
        self._prodlist.delete(0, "end")
        expandable = self._parser.expandable_productions()
        untried = self._parser.untried_expandable_productions()
        productions = self._productions
        for index in range(len(productions)):
            if productions[index] in expandable:
                if productions[index] in untried:
                    self._prodlist.insert(index, " %s" % productions[index])
                else:
                    self._prodlist.insert(index, " %s (TRIED)" % productions[index])
                self._prodlist.selection_set(index)
            else:
                self._prodlist.insert(index, " %s" % productions[index])

    def _position_text(self):
        # Line up the text widgets that are matched against the tree
        numwords = len(self._sent)
        num_matched = numwords - len(self._parser.remaining_text())
        leaves = self._tree_leaves()[:num_matched]
        xmax = self._tree.bbox()[0]
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            widget["color"] = "#006040"
            leaf["color"] = "#006040"
            widget.move(leaf.bbox()[0] - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # Line up the text widgets that are not matched against the tree.
        for i in range(len(leaves), numwords):
            widget = self._textwidgets[i]
            widget["color"] = "#a0a0a0"
            widget.move(xmax - widget.bbox()[0], 0)
            xmax = widget.bbox()[2] + 10

        # If we have a complete parse, make everything green :)
        if self._parser.currently_complete():
            for twidget in self._textwidgets:
                twidget["color"] = "#00a000"

        # Move the matched leaves down to the text.
        for i in range(0, len(leaves)):
            widget = self._textwidgets[i]
            leaf = leaves[i]
            dy = widget.bbox()[1] - leaf.bbox()[3] - 10.0
            dy = max(dy, leaf.parent().label().bbox()[3] - leaf.bbox()[3] + 10)
            leaf.move(0, dy)

    def _tree_leaves(self, tree=None):
        if tree is None:
            tree = self._tree
        if isinstance(tree, TreeSegmentWidget):
            leaves = []
            for child in tree.subtrees():
                leaves += self._tree_leaves(child)
            return leaves
        else:
            return [tree]

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._autostep = 0
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset Application"
        self._lastoper2["text"] = ""
        self._redraw()

    def autostep(self, *e):
        if self._animation_frames.get() == 0:
            self._animation_frames.set(2)
        if self._autostep:
            self._autostep = 0
        else:
            self._autostep = 1
            self._step()

    def cancel_autostep(self, *e):
        # self._autostep_button['text'] = 'Autostep'
        self._autostep = 0

    # Make sure to stop auto-stepping if we get any user input.
    def step(self, *e):
        self._autostep = 0
        self._step()

    def match(self, *e):
        self._autostep = 0
        self._match()

    def expand(self, *e):
        self._autostep = 0
        self._expand()

    def backtrack(self, *e):
        self._autostep = 0
        self._backtrack()

    def _step(self):
        if self._animating_lock:
            return

        # Try expanding, matching, and backtracking (in that order)
        if self._expand():
            pass
        elif self._parser.untried_match() and self._match():
            pass
        elif self._backtrack():
            pass
        else:
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            self._autostep = 0

        # Check if we just completed a parse.
        if self._parser.currently_complete():
            self._autostep = 0
            self._lastoper2["text"] += "    [COMPLETE PARSE]"

    def _expand(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.expand()
        if rv is not None:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = rv
            self._prodlist.selection_clear(0, "end")
            index = self._productions.index(rv)
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = "(all expansions tried)"
            return False

    def _match(self, *e):
        if self._animating_lock:
            return
        old_frontier = self._parser.frontier()
        rv = self._parser.match()
        if rv is not None:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = rv
            self._animate_match(old_frontier[0])
            return True
        else:
            self._lastoper1["text"] = "Match:"
            self._lastoper2["text"] = "(failed)"
            return False

    def _backtrack(self, *e):
        if self._animating_lock:
            return
        if self._parser.backtrack():
            elt = self._parser.tree()
            for i in self._parser.frontier()[0]:
                elt = elt[i]
            self._lastoper1["text"] = "Backtrack"
            self._lastoper2["text"] = ""
            if isinstance(elt, Tree):
                self._animate_backtrack(self._parser.frontier()[0])
            else:
                self._animate_match_backtrack(self._parser.frontier()[0])
            return True
        else:
            self._autostep = 0
            self._lastoper1["text"] = "Finished"
            self._lastoper2["text"] = ""
            return False

    def about(self, *e):
        ABOUT = (
            "NLTK Recursive Descent Parser Application\n" + "Written by Edward Loper"
        )
        TITLE = "About: Recursive Descent Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def help(self, *e):
        self._autostep = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Recursive Descent Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def postscript(self, *e):
        self._autostep = 0
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))
        self._bigfont.configure(size=-(abs(size + 2)))
        self._redraw()

    #########################################
    ##  Expand Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    #     def toggle_grammar(self, *e):
    #         self._show_grammar = not self._show_grammar
    #         if self._show_grammar:
    #             self._prodframe.pack(fill='both', expand='y', side='left',
    #                                  after=self._feedbackframe)
    #             self._lastoper1['text'] = 'Show Grammar'
    #         else:
    #             self._prodframe.pack_forget()
    #             self._lastoper1['text'] = 'Hide Grammar'
    #         self._lastoper2['text'] = ''

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        old_frontier = self._parser.frontier()
        production = self._parser.expand(self._productions[index])

        if production:
            self._lastoper1["text"] = "Expand:"
            self._lastoper2["text"] = production
            self._prodlist.selection_clear(0, "end")
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.expandable_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    #########################################
    ##  Animation
    #########################################

    def _animate_expand(self, treeloc):
        oldwidget = self._get(self._tree, treeloc)
        oldtree = oldwidget.parent()
        top = not isinstance(oldtree.parent(), TreeSegmentWidget)

        tree = self._parser.tree()
        for i in treeloc:
            tree = tree[i]

        widget = tree_to_treesegment(
            self._canvas,
            tree,
            node_font=self._boldfont,
            leaf_color="white",
            tree_width=2,
            tree_color="white",
            node_color="white",
            leaf_font=self._font,
        )
        widget.label()["color"] = "#20a050"

        (oldx, oldy) = oldtree.label().bbox()[:2]
        (newx, newy) = widget.label().bbox()[:2]
        widget.move(oldx - newx, oldy - newy)

        if top:
            self._cframe.add_widget(widget, 0, 5)
            widget.move(30 - widget.label().bbox()[0], 0)
            self._tree = widget
        else:
            oldtree.parent().replace_child(oldtree, widget)

        # Move the children over so they don't overlap.
        # Line the children up in a strange way.
        if widget.subtrees():
            dx = (
                oldx
                + widget.label().width() / 2
                - widget.subtrees()[0].bbox()[0] / 2
                - widget.subtrees()[0].bbox()[2] / 2
            )
            for subtree in widget.subtrees():
                subtree.move(dx, 0)

        self._makeroom(widget)

        if top:
            self._cframe.destroy_widget(oldtree)
        else:
            oldtree.destroy()

        colors = [
            "gray%d" % (10 * int(10 * x / self._animation_frames.get()))
            for x in range(self._animation_frames.get(), 0, -1)
        ]

        # Move the text string down, if necessary.
        dy = widget.bbox()[3] + 30 - self._canvas.coords(self._textline)[1]
        if dy > 0:
            for twidget in self._textwidgets:
                twidget.move(0, dy)
            self._canvas.move(self._textline, 0, dy)

        self._animate_expand_frame(widget, colors)

    def _makeroom(self, treeseg):
        """
        Make sure that no sibling tree bbox's overlap.
        """
        parent = treeseg.parent()
        if not isinstance(parent, TreeSegmentWidget):
            return

        index = parent.subtrees().index(treeseg)

        # Handle siblings to the right
        rsiblings = parent.subtrees()[index + 1 :]
        if rsiblings:
            dx = treeseg.bbox()[2] - rsiblings[0].bbox()[0] + 10
            for sibling in rsiblings:
                sibling.move(dx, 0)

        # Handle siblings to the left
        if index > 0:
            lsibling = parent.subtrees()[index - 1]
            dx = max(0, lsibling.bbox()[2] - treeseg.bbox()[0] + 10)
            treeseg.move(dx, 0)

        # Keep working up the tree.
        self._makeroom(parent)

    def _animate_expand_frame(self, widget, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            widget["color"] = colors[0]
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = colors[0]
                else:
                    subtree["color"] = colors[0]
            self._top.after(50, self._animate_expand_frame, widget, colors[1:])
        else:
            widget["color"] = "black"
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.label()["color"] = "black"
                else:
                    subtree["color"] = "black"
            self._redraw_quick()
            widget.label()["color"] = "black"
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_backtrack(self, treeloc):
        # Flash red first, if we're animating.
        if self._animation_frames.get() == 0:
            colors = []
        else:
            colors = ["#a00000", "#000000", "#a00000"]
        colors += [
            "gray%d" % (10 * int(10 * x / (self._animation_frames.get())))
            for x in range(1, self._animation_frames.get() + 1)
        ]

        widgets = [self._get(self._tree, treeloc).parent()]
        for subtree in widgets[0].subtrees():
            if isinstance(subtree, TreeSegmentWidget):
                widgets.append(subtree.label())
            else:
                widgets.append(subtree)

        self._animate_backtrack_frame(widgets, colors)

    def _animate_backtrack_frame(self, widgets, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget["color"] = colors[0]
            self._top.after(50, self._animate_backtrack_frame, widgets, colors[1:])
        else:
            for widget in widgets[0].subtrees():
                widgets[0].remove_child(widget)
                widget.destroy()
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack(self, treeloc):
        widget = self._get(self._tree, treeloc)
        node = widget.parent().label()
        dy = (node.bbox()[3] - widget.bbox()[1] + 14) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_backtrack_frame(self._animation_frames.get(), widget, dy)

    def _animate_match(self, treeloc):
        widget = self._get(self._tree, treeloc)

        dy = (self._textwidgets[0].bbox()[1] - widget.bbox()[3] - 10.0) / max(
            1, self._animation_frames.get()
        )
        self._animate_match_frame(self._animation_frames.get(), widget, dy)

    def _animate_match_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(10, self._animate_match_frame, frame - 1, widget, dy)
        else:
            widget["color"] = "#006040"
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def _animate_match_backtrack_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(
                10, self._animate_match_backtrack_frame, frame - 1, widget, dy
            )
        else:
            widget.parent().remove_child(widget)
            widget.destroy()
            self._animating_lock = 0
            if self._autostep:
                self._step()

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._sent = sentence.split()  # [XX] use tagged?
        self.reset()


def app():
    """
    Create a recursive descent parser demo, using a simple grammar and
    text.
    """
    from nltk.grammar import CFG

    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        NP -> Det N PP | Det N
        VP -> V NP PP | V NP | V
        PP -> P NP
    # Lexical productions.
        NP -> 'I'
        Det -> 'the' | 'a'
        N -> 'man' | 'park' | 'dog' | 'telescope'
        V -> 'ate' | 'saw'
        P -> 'in' | 'under' | 'with'
    """
    )

    sent = "the dog saw a man in the park".split()

    RecursiveDescentApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/openenv\Lib\site-packages\nltk\app\wordnet_app.py ===
# Natural Language Toolkit: WordNet Browser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A WordNet Browser application which launches the default browser
(if it is not already running) and opens a new tab with a connection
to http://localhost:port/ .  It also starts an HTTP server on the
specified port and begins serving browser requests.  The default
port is 8000.  (For command-line help, run "python wordnet -h")
This application requires that the user's web browser supports
Javascript.

BrowServer is a server for browsing the NLTK Wordnet database It first
launches a browser client to be used for browsing and then starts
serving the requests of that and maybe other clients

Usage::

    browserver.py -h
    browserver.py [-s] [-p <port>]

Options::

    -h or --help
        Display this help message.

    -l <file> or --log-file <file>
        Logs messages to the given file, If this option is not specified
        messages are silently dropped.

    -p <port> or --port <port>
        Run the web server on this TCP port, defaults to 8000.

    -s or --server-mode
        Do not start a web browser, and do not allow a user to
        shutdown the server through the web interface.
"""
# TODO: throughout this package variable names and docstrings need
# modifying to be compliant with NLTK's coding standards.  Tests also
# need to be develop to ensure this continues to work in the face of
# changes to other NLTK packages.

import base64
import copy
import getopt
import io
import os
import pickle
import sys
import threading
import time
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

# Allow this program to run inside the NLTK source tree.
from sys import argv
from urllib.parse import unquote_plus

from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Lemma, Synset

firstClient = True

# True if we're not also running a web browser.  The value f server_mode
# gets set by demo().
server_mode = None

# If set this is a file object for writing log messages.
logfile = None


class MyServerHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_head()

    def do_GET(self):
        global firstClient
        sp = self.path[1:]
        if unquote_plus(sp) == "SHUTDOWN THE SERVER":
            if server_mode:
                page = "Server must be killed with SIGTERM."
                type = "text/plain"
            else:
                print("Server shutting down!")
                os._exit(0)

        elif sp == "":  # First request.
            type = "text/html"
            if not server_mode and firstClient:
                firstClient = False
                page = get_static_index_page(True)
            else:
                page = get_static_index_page(False)
            word = "green"

        elif sp.endswith(".html"):  # Trying to fetch a HTML file TODO:
            type = "text/html"
            usp = unquote_plus(sp)
            if usp == "NLTK Wordnet Browser Database Info.html":
                word = "* Database Info *"
                if os.path.isfile(usp):
                    with open(usp) as infile:
                        page = infile.read()
                else:
                    page = (
                        (html_header % word) + "<p>The database info file:"
                        "<p><b>"
                        + usp
                        + "</b>"
                        + "<p>was not found. Run this:"
                        + "<p><b>python dbinfo_html.py</b>"
                        + "<p>to produce it."
                        + html_trailer
                    )
            else:
                # Handle files here.
                word = sp
                try:
                    page = get_static_page_by_path(usp)
                except FileNotFoundError:
                    page = "Internal error: Path for static page '%s' is unknown" % usp
                    # Set type to plain to prevent XSS by printing the path as HTML
                    type = "text/plain"
        elif sp.startswith("search"):
            # This doesn't seem to work with MWEs.
            type = "text/html"
            parts = (sp.split("?")[1]).split("&")
            word = [
                p.split("=")[1].replace("+", " ")
                for p in parts
                if p.startswith("nextWord")
            ][0]
            page, word = page_from_word(word)
        elif sp.startswith("lookup_"):
            # TODO add a variation of this that takes a non ecoded word or MWE.
            type = "text/html"
            sp = sp[len("lookup_") :]
            page, word = page_from_href(sp)
        elif sp == "start_page":
            # if this is the first request we should display help
            # information, and possibly set a default word.
            type = "text/html"
            page, word = page_from_word("wordnet")
        else:
            type = "text/plain"
            page = "Could not parse request: '%s'" % sp

        # Send result.
        self.send_head(type)
        self.wfile.write(page.encode("utf8"))

    def send_head(self, type=None):
        self.send_response(200)
        self.send_header("Content-type", type)
        self.end_headers()

    def log_message(self, format, *args):
        global logfile

        if logfile:
            logfile.write(
                "%s - - [%s] %s\n"
                % (self.address_string(), self.log_date_time_string(), format % args)
            )


def get_unique_counter_from_url(sp):
    """
    Extract the unique counter from the URL if it has one.  Otherwise return
    null.
    """
    pos = sp.rfind("%23")
    if pos != -1:
        return int(sp[(pos + 3) :])
    else:
        return None


def wnb(port=8000, runBrowser=True, logfilename=None):
    """
    Run NLTK Wordnet Browser Server.

    :param port: The port number for the server to listen on, defaults to
                 8000
    :type  port: int

    :param runBrowser: True to start a web browser and point it at the web
                       server.
    :type  runBrowser: bool
    """
    # The webbrowser module is unpredictable, typically it blocks if it uses
    # a console web browser, and doesn't block if it uses a GUI webbrowser,
    # so we need to force it to have a clear correct behaviour.
    #
    # Normally the server should run for as long as the user wants. they
    # should idealy be able to control this from the UI by closing the
    # window or tab.  Second best would be clicking a button to say
    # 'Shutdown' that first shutsdown the server and closes the window or
    # tab, or exits the text-mode browser.  Both of these are unfreasable.
    #
    # The next best alternative is to start the server, have it close when
    # it receives SIGTERM (default), and run the browser as well.  The user
    # may have to shutdown both programs.
    #
    # Since webbrowser may block, and the webserver will block, we must run
    # them in separate threads.
    #
    global server_mode, logfile
    server_mode = not runBrowser

    # Setup logging.
    if logfilename:
        try:
            logfile = open(logfilename, "a", 1)  # 1 means 'line buffering'
        except OSError as e:
            sys.stderr.write("Couldn't open %s for writing: %s", logfilename, e)
            sys.exit(1)
    else:
        logfile = None

    # Compute URL and start web browser
    url = "http://localhost:" + str(port)

    server_ready = None
    browser_thread = None

    if runBrowser:
        server_ready = threading.Event()
        browser_thread = startBrowser(url, server_ready)

    # Start the server.
    server = HTTPServer(("", port), MyServerHandler)
    if logfile:
        logfile.write("NLTK Wordnet browser server running serving: %s\n" % url)
    if runBrowser:
        server_ready.set()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    if runBrowser:
        browser_thread.join()

    if logfile:
        logfile.close()


def startBrowser(url, server_ready):
    def run():
        server_ready.wait()
        time.sleep(1)  # Wait a little bit more, there's still the chance of
        # a race condition.
        webbrowser.open(url, new=2, autoraise=1)

    t = threading.Thread(target=run)
    t.start()
    return t


#####################################################################
# Utilities
#####################################################################


"""
WordNet Browser Utilities.

This provides a backend to both wxbrowse and browserver.py.
"""

################################################################################
#
# Main logic for wordnet browser.
#


# This is wrapped inside a function since wn is only available if the
# WordNet corpus is installed.
def _pos_tuples():
    return [
        (wn.NOUN, "N", "noun"),
        (wn.VERB, "V", "verb"),
        (wn.ADJ, "J", "adj"),
        (wn.ADV, "R", "adv"),
    ]


def _pos_match(pos_tuple):
    """
    This function returns the complete pos tuple for the partial pos
    tuple given to it.  It attempts to match it against the first
    non-null component of the given pos tuple.
    """
    if pos_tuple[0] == "s":
        pos_tuple = ("a", pos_tuple[1], pos_tuple[2])
    for n, x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples():
        if pt[n] == pos_tuple[n]:
            return pt
    return None


HYPONYM = 0
HYPERNYM = 1
CLASS_REGIONAL = 2
PART_HOLONYM = 3
PART_MERONYM = 4
ATTRIBUTE = 5
SUBSTANCE_HOLONYM = 6
SUBSTANCE_MERONYM = 7
MEMBER_HOLONYM = 8
MEMBER_MERONYM = 9
VERB_GROUP = 10
INSTANCE_HYPONYM = 12
INSTANCE_HYPERNYM = 13
CAUSE = 14
ALSO_SEE = 15
SIMILAR = 16
ENTAILMENT = 17
ANTONYM = 18
FRAMES = 19
PERTAINYM = 20

CLASS_CATEGORY = 21
CLASS_USAGE = 22
CLASS_REGIONAL = 23
CLASS_USAGE = 24
CLASS_CATEGORY = 11

DERIVATIONALLY_RELATED_FORM = 25

INDIRECT_HYPERNYMS = 26


def lemma_property(word, synset, func):
    def flattern(l):
        if l == []:
            return []
        else:
            return l[0] + flattern(l[1:])

    return flattern([func(l) for l in synset.lemmas() if l.name == word])


def rebuild_tree(orig_tree):
    node = orig_tree[0]
    children = orig_tree[1:]
    return (node, [rebuild_tree(t) for t in children])


def get_relations_data(word, synset):
    """
    Get synset relations data for a synset.  Note that this doesn't
    yet support things such as full hyponym vs direct hyponym.
    """
    if synset.pos() == wn.NOUN:
        return (
            (HYPONYM, "Hyponyms", synset.hyponyms()),
            (INSTANCE_HYPONYM, "Instance hyponyms", synset.instance_hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            #  hypernyms', 'Sister terms',
            (INSTANCE_HYPERNYM, "Instance hypernyms", synset.instance_hypernyms()),
            #            (CLASS_REGIONAL, ['domain term region'], ),
            (PART_HOLONYM, "Part holonyms", synset.part_holonyms()),
            (PART_MERONYM, "Part meronyms", synset.part_meronyms()),
            (SUBSTANCE_HOLONYM, "Substance holonyms", synset.substance_holonyms()),
            (SUBSTANCE_MERONYM, "Substance meronyms", synset.substance_meronyms()),
            (MEMBER_HOLONYM, "Member holonyms", synset.member_holonyms()),
            (MEMBER_MERONYM, "Member meronyms", synset.member_meronyms()),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ANTONYM, "Antonyms", lemma_property(word, synset, lambda l: l.antonyms())),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.VERB:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (HYPONYM, "Hyponym", synset.hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            (ENTAILMENT, "Entailments", synset.entailments()),
            (CAUSE, "Causes", synset.causes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
            (VERB_GROUP, "Verb Groups", synset.verb_groups()),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.ADJ or synset.pos == wn.ADJ_SAT:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (SIMILAR, "Similar to", synset.similar_tos()),
            # Participle of verb - not supported by corpus
            (
                PERTAINYM,
                "Pertainyms",
                lemma_property(word, synset, lambda l: l.pertainyms()),
            ),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
        )
    elif synset.pos() == wn.ADV:
        # This is weird. adverbs such as 'quick' and 'fast' don't seem
        # to have antonyms returned by the corpus.a
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
        )
        # Derived from adjective - not supported by corpus
    else:
        raise TypeError("Unhandles synset POS type: " + str(synset.pos()))


html_header = """
<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'
'http://www.w3.org/TR/html4/strict.dtd'>
<html>
<head>
<meta name='generator' content=
'HTML Tidy for Windows (vers 14 February 2006), see www.w3.org'>
<meta http-equiv='Content-Type' content=
'text/html; charset=us-ascii'>
<title>NLTK Wordnet Browser display of: %s</title></head>
<body bgcolor='#F5F5F5' text='#000000'>
"""
html_trailer = """
</body>
</html>
"""

explanation = """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.
</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width='100%'>
"""

# HTML oriented functions


def _bold(txt):
    return "<b>%s</b>" % txt


def _center(txt):
    return "<center>%s</center>" % txt


def _hlev(n, txt):
    return "<h%d>%s</h%d>" % (n, txt, n)


def _italic(txt):
    return "<i>%s</i>" % txt


def _li(txt):
    return "<li>%s</li>" % txt


def pg(word, body):
    """
    Return a HTML page of NLTK Browser format constructed from the
    word and body

    :param word: The word that the body corresponds to
    :type word: str
    :param body: The HTML body corresponding to the word
    :type body: str
    :return: a HTML page for the word-body combination
    :rtype: str
    """
    return (html_header % word) + body + html_trailer


def _ul(txt):
    return "<ul>" + txt + "</ul>"


def _abbc(txt):
    """
    abbc = asterisks, breaks, bold, center
    """
    return _center(_bold("<br>" * 10 + "*" * 10 + " " + txt + " " + "*" * 10))


full_hyponym_cont_text = _ul(_li(_italic("(has full hyponym continuation)"))) + "\n"


def _get_synset(synset_key):
    """
    The synset key is the unique name of the synset, this can be
    retrieved via synset.name()
    """
    return wn.synset(synset_key)


def _collect_one_synset(word, synset, synset_relations):
    """
    Returns the HTML string for one synset or word

    :param word: the current word
    :type word: str
    :param synset: a synset
    :type synset: synset
    :param synset_relations: information about which synset relations
    to display.
    :type synset_relations: dict(synset_key, set(relation_id))
    :return: The HTML string built for this synset
    :rtype: str
    """
    if isinstance(synset, tuple):  # It's a word
        raise NotImplementedError("word not supported by _collect_one_synset")

    typ = "S"
    pos_tuple = _pos_match((synset.pos(), None, None))
    assert pos_tuple is not None, "pos_tuple is null: synset.pos(): %s" % synset.pos()
    descr = pos_tuple[2]
    ref = copy.deepcopy(Reference(word, synset_relations))
    ref.toggle_synset(synset)
    synset_label = typ + ";"
    if synset.name() in synset_relations:
        synset_label = _bold(synset_label)
    s = f"<li>{make_lookup_link(ref, synset_label)} ({descr}) "

    def format_lemma(w):
        w = w.replace("_", " ")
        if w.lower() == word:
            return _bold(w)
        else:
            ref = Reference(w)
            return make_lookup_link(ref, w)

    s += ", ".join(format_lemma(l.name()) for l in synset.lemmas())

    gl = " ({}) <i>{}</i> ".format(
        synset.definition(),
        "; ".join('"%s"' % e for e in synset.examples()),
    )
    return s + gl + _synset_relations(word, synset, synset_relations) + "</li>\n"


def _collect_all_synsets(word, pos, synset_relations=dict()):
    """
    Return a HTML unordered list of synsets for the given word and
    part of speech.
    """
    return "<ul>%s\n</ul>\n" % "".join(
        _collect_one_synset(word, synset, synset_relations)
        for synset in wn.synsets(word, pos)
    )


def _synset_relations(word, synset, synset_relations):
    """
    Builds the HTML string for the relations of a synset

    :param word: The current word
    :type word: str
    :param synset: The synset for which we're building the relations.
    :type synset: Synset
    :param synset_relations: synset keys and relation types for which to display relations.
    :type synset_relations: dict(synset_key, set(relation_type))
    :return: The HTML for a synset's relations
    :rtype: str
    """

    if not synset.name() in synset_relations:
        return ""
    ref = Reference(word, synset_relations)

    def relation_html(r):
        if isinstance(r, Synset):
            return make_lookup_link(Reference(r.lemma_names()[0]), r.lemma_names()[0])
        elif isinstance(r, Lemma):
            return relation_html(r.synset())
        elif isinstance(r, tuple):
            # It's probably a tuple containing a Synset and a list of
            # similar tuples.  This forms a tree of synsets.
            return "{}\n<ul>{}</ul>\n".format(
                relation_html(r[0]),
                "".join("<li>%s</li>\n" % relation_html(sr) for sr in r[1]),
            )
        else:
            raise TypeError(
                "r must be a synset, lemma or list, it was: type(r) = %s, r = %s"
                % (type(r), r)
            )

    def make_synset_html(db_name, disp_name, rels):
        synset_html = "<i>%s</i>\n" % make_lookup_link(
            copy.deepcopy(ref).toggle_synset_relation(synset, db_name),
            disp_name,
        )

        if db_name in ref.synset_relations[synset.name()]:
            synset_html += "<ul>%s</ul>\n" % "".join(
                "<li>%s</li>\n" % relation_html(r) for r in rels
            )

        return synset_html

    html = (
        "<ul>"
        + "\n".join(
            "<li>%s</li>" % make_synset_html(*rel_data)
            for rel_data in get_relations_data(word, synset)
            if rel_data[2] != []
        )
        + "</ul>"
    )

    return html


class RestrictedUnpickler(pickle.Unpickler):
    """
    Unpickler that prevents any class or function from being used during loading.
    """

    def find_class(self, module, name):
        # Forbid every function
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


class Reference:
    """
    A reference to a page that may be generated by page_word
    """

    def __init__(self, word, synset_relations=dict()):
        """
        Build a reference to a new page.

        word is the word or words (separated by commas) for which to
        search for synsets of

        synset_relations is a dictionary of synset keys to sets of
        synset relation identifaiers to unfold a list of synset
        relations for.
        """
        self.word = word
        self.synset_relations = synset_relations

    def encode(self):
        """
        Encode this reference into a string to be used in a URL.
        """
        # This uses a tuple rather than an object since the python
        # pickle representation is much smaller and there is no need
        # to represent the complete object.
        string = pickle.dumps((self.word, self.synset_relations), -1)
        return base64.urlsafe_b64encode(string).decode()

    @staticmethod
    def decode(string):
        """
        Decode a reference encoded with Reference.encode
        """
        string = base64.urlsafe_b64decode(string.encode())
        word, synset_relations = RestrictedUnpickler(io.BytesIO(string)).load()
        return Reference(word, synset_relations)

    def toggle_synset_relation(self, synset, relation):
        """
        Toggle the display of the relations for the given synset and
        relation type.

        This function will throw a KeyError if the synset is currently
        not being displayed.
        """
        if relation in self.synset_relations[synset.name()]:
            self.synset_relations[synset.name()].remove(relation)
        else:
            self.synset_relations[synset.name()].add(relation)

        return self

    def toggle_synset(self, synset):
        """
        Toggle displaying of the relation types for the given synset
        """
        if synset.name() in self.synset_relations:
            del self.synset_relations[synset.name()]
        else:
            self.synset_relations[synset.name()] = set()

        return self


def make_lookup_link(ref, label):
    return f'<a href="lookup_{ref.encode()}">{label}</a>'


def page_from_word(word):
    """
    Return a HTML page for the given word.

    :type word: str
    :param word: The currently active word
    :return: A tuple (page,word), where page is the new current HTML page
        to be sent to the browser and
        word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference(word))


def page_from_href(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference.decode(href))


def page_from_reference(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    word = href.word
    pos_forms = defaultdict(list)
    words = word.split(",")
    words = [w for w in [w.strip().lower().replace(" ", "_") for w in words] if w != ""]
    if len(words) == 0:
        # No words were found.
        return "", "Please specify a word to search for."

    # This looks up multiple words at once.  This is probably not
    # necessary and may lead to problems.
    for w in words:
        for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
            form = wn.morphy(w, pos)
            if form and form not in pos_forms[pos]:
                pos_forms[pos].append(form)
    body = ""
    for pos, pos_str, name in _pos_tuples():
        if pos in pos_forms:
            body += _hlev(3, name) + "\n"
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    body += _collect_all_synsets(w, pos, href.synset_relations)
                except KeyError:
                    pass
    if not body:
        body = "The word or words '%s' were not found in the dictionary." % word
    return body, word


#####################################################################
# Static pages
#####################################################################


def get_static_page_by_path(path):
    """
    Return a static HTML page from the path given.
    """
    if path == "index_2.html":
        return get_static_index_page(False)
    elif path == "index.html":
        return get_static_index_page(True)
    elif path == "NLTK Wordnet Browser Database Info.html":
        return "Display of Wordnet Database Statistics is not supported"
    elif path == "upper_2.html":
        return get_static_upper_page(False)
    elif path == "upper.html":
        return get_static_upper_page(True)
    elif path == "web_help.html":
        return get_static_web_help_page()
    elif path == "wx_help.html":
        return get_static_wx_help_page()
    raise FileNotFoundError()


def get_static_web_help_page():
    """
    Return the static web help page.
    """
    return """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database.
<p><b>You are using the Javascript client part of the NLTK Wordnet BrowseServer.</b> We assume your browser is in tab sheets enabled mode.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <a href="https://wordnet.princeton.edu/"><b> https://wordnet.princeton.edu/</b></a>. For more information on the NLTK project, see the project home:
<a href="https://www.nltk.org/"><b>https://www.nltk.org/</b></a>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>New Word</b> field and the search started with Enter or by clicking the <b>Search</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>The Buttons</h3>
<p>The <b>Search</b> and <b>Help</b> buttons need no more explanation. </p>
<p>The <b>Show Database Info</b> button shows a collection of Wordnet database statistics.</p>
<p>The <b>Shutdown the Server</b> button is shown for the first client of the BrowServer program i.e. for the client that is automatically launched when the BrowServer is started but not for the succeeding clients in order to protect the server from accidental shutdowns.
</p></body>
</html>
"""


def get_static_welcome_message():
    """
    Get the static welcome page.
    """
    return """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Next Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
"""


def get_static_index_page(with_shutdown):
    """
    Get the static index page.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"  "http://www.w3.org/TR/html4/frameset.dtd">
<HTML>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <HEAD>
         <TITLE>NLTK Wordnet Browser</TITLE>
     </HEAD>

<frameset rows="7%%,93%%">
    <frame src="%s" name="header">
    <frame src="start_page" name="body">
</frameset>
</HTML>
"""
    if with_shutdown:
        upper_link = "upper.html"
    else:
        upper_link = "upper_2.html"

    return template % upper_link


def get_static_upper_page(with_shutdown):
    """
    Return the upper frame page,

    If with_shutdown is True then a 'shutdown' button is also provided
    to shutdown the server.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
        Copyright (C) 2001-2024 NLTK Project
        Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
        URL: <https://www.nltk.org/>
        For license information, see LICENSE.TXT -->
    <head>
                <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
        <title>Untitled Document</title>
    </head>
    <body>
    <form method="GET" action="search" target="body">
            Current Word:&nbsp;<input type="text" id="currentWord" size="10" disabled>
            Next Word:&nbsp;<input type="text" id="nextWord" name="nextWord" size="10">
            <input name="searchButton" type="submit" value="Search">
    </form>
        <a target="body" href="web_help.html">Help</a>
        %s

</body>
</html>
"""
    if with_shutdown:
        shutdown_link = '<a href="SHUTDOWN THE SERVER">Shutdown</a>'
    else:
        shutdown_link = ""

    return template % shutdown_link


def usage():
    """
    Display the command line help message.
    """
    print(__doc__)


def app():
    # Parse and interpret options.
    (opts, _) = getopt.getopt(
        argv[1:], "l:p:sh", ["logfile=", "port=", "server-mode", "help"]
    )
    port = 8000
    server_mode = False
    help_mode = False
    logfilename = None
    for opt, value in opts:
        if (opt == "-l") or (opt == "--logfile"):
            logfilename = str(value)
        elif (opt == "-p") or (opt == "--port"):
            port = int(value)
        elif (opt == "-s") or (opt == "--server-mode"):
            server_mode = True
        elif (opt == "-h") or (opt == "--help"):
            help_mode = True

    if help_mode:
        usage()
    else:
        wnb(port, not server_mode, logfilename)


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\wordnet_app.py ===
# Natural Language Toolkit: WordNet Browser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A WordNet Browser application which launches the default browser
(if it is not already running) and opens a new tab with a connection
to http://localhost:port/ .  It also starts an HTTP server on the
specified port and begins serving browser requests.  The default
port is 8000.  (For command-line help, run "python wordnet -h")
This application requires that the user's web browser supports
Javascript.

BrowServer is a server for browsing the NLTK Wordnet database It first
launches a browser client to be used for browsing and then starts
serving the requests of that and maybe other clients

Usage::

    browserver.py -h
    browserver.py [-s] [-p <port>]

Options::

    -h or --help
        Display this help message.

    -l <file> or --log-file <file>
        Logs messages to the given file, If this option is not specified
        messages are silently dropped.

    -p <port> or --port <port>
        Run the web server on this TCP port, defaults to 8000.

    -s or --server-mode
        Do not start a web browser, and do not allow a user to
        shutdown the server through the web interface.
"""
# TODO: throughout this package variable names and docstrings need
# modifying to be compliant with NLTK's coding standards.  Tests also
# need to be develop to ensure this continues to work in the face of
# changes to other NLTK packages.

import base64
import copy
import getopt
import io
import os
import pickle
import sys
import threading
import time
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

# Allow this program to run inside the NLTK source tree.
from sys import argv
from urllib.parse import unquote_plus

from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Lemma, Synset

firstClient = True

# True if we're not also running a web browser.  The value f server_mode
# gets set by demo().
server_mode = None

# If set this is a file object for writing log messages.
logfile = None


class MyServerHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_head()

    def do_GET(self):
        global firstClient
        sp = self.path[1:]
        if unquote_plus(sp) == "SHUTDOWN THE SERVER":
            if server_mode:
                page = "Server must be killed with SIGTERM."
                type = "text/plain"
            else:
                print("Server shutting down!")
                os._exit(0)

        elif sp == "":  # First request.
            type = "text/html"
            if not server_mode and firstClient:
                firstClient = False
                page = get_static_index_page(True)
            else:
                page = get_static_index_page(False)
            word = "green"

        elif sp.endswith(".html"):  # Trying to fetch a HTML file TODO:
            type = "text/html"
            usp = unquote_plus(sp)
            if usp == "NLTK Wordnet Browser Database Info.html":
                word = "* Database Info *"
                if os.path.isfile(usp):
                    with open(usp) as infile:
                        page = infile.read()
                else:
                    page = (
                        (html_header % word) + "<p>The database info file:"
                        "<p><b>"
                        + usp
                        + "</b>"
                        + "<p>was not found. Run this:"
                        + "<p><b>python dbinfo_html.py</b>"
                        + "<p>to produce it."
                        + html_trailer
                    )
            else:
                # Handle files here.
                word = sp
                try:
                    page = get_static_page_by_path(usp)
                except FileNotFoundError:
                    page = "Internal error: Path for static page '%s' is unknown" % usp
                    # Set type to plain to prevent XSS by printing the path as HTML
                    type = "text/plain"
        elif sp.startswith("search"):
            # This doesn't seem to work with MWEs.
            type = "text/html"
            parts = (sp.split("?")[1]).split("&")
            word = [
                p.split("=")[1].replace("+", " ")
                for p in parts
                if p.startswith("nextWord")
            ][0]
            page, word = page_from_word(word)
        elif sp.startswith("lookup_"):
            # TODO add a variation of this that takes a non ecoded word or MWE.
            type = "text/html"
            sp = sp[len("lookup_") :]
            page, word = page_from_href(sp)
        elif sp == "start_page":
            # if this is the first request we should display help
            # information, and possibly set a default word.
            type = "text/html"
            page, word = page_from_word("wordnet")
        else:
            type = "text/plain"
            page = "Could not parse request: '%s'" % sp

        # Send result.
        self.send_head(type)
        self.wfile.write(page.encode("utf8"))

    def send_head(self, type=None):
        self.send_response(200)
        self.send_header("Content-type", type)
        self.end_headers()

    def log_message(self, format, *args):
        global logfile

        if logfile:
            logfile.write(
                "%s - - [%s] %s\n"
                % (self.address_string(), self.log_date_time_string(), format % args)
            )


def get_unique_counter_from_url(sp):
    """
    Extract the unique counter from the URL if it has one.  Otherwise return
    null.
    """
    pos = sp.rfind("%23")
    if pos != -1:
        return int(sp[(pos + 3) :])
    else:
        return None


def wnb(port=8000, runBrowser=True, logfilename=None):
    """
    Run NLTK Wordnet Browser Server.

    :param port: The port number for the server to listen on, defaults to
                 8000
    :type  port: int

    :param runBrowser: True to start a web browser and point it at the web
                       server.
    :type  runBrowser: bool
    """
    # The webbrowser module is unpredictable, typically it blocks if it uses
    # a console web browser, and doesn't block if it uses a GUI webbrowser,
    # so we need to force it to have a clear correct behaviour.
    #
    # Normally the server should run for as long as the user wants. they
    # should idealy be able to control this from the UI by closing the
    # window or tab.  Second best would be clicking a button to say
    # 'Shutdown' that first shutsdown the server and closes the window or
    # tab, or exits the text-mode browser.  Both of these are unfreasable.
    #
    # The next best alternative is to start the server, have it close when
    # it receives SIGTERM (default), and run the browser as well.  The user
    # may have to shutdown both programs.
    #
    # Since webbrowser may block, and the webserver will block, we must run
    # them in separate threads.
    #
    global server_mode, logfile
    server_mode = not runBrowser

    # Setup logging.
    if logfilename:
        try:
            logfile = open(logfilename, "a", 1)  # 1 means 'line buffering'
        except OSError as e:
            sys.stderr.write("Couldn't open %s for writing: %s", logfilename, e)
            sys.exit(1)
    else:
        logfile = None

    # Compute URL and start web browser
    url = "http://localhost:" + str(port)

    server_ready = None
    browser_thread = None

    if runBrowser:
        server_ready = threading.Event()
        browser_thread = startBrowser(url, server_ready)

    # Start the server.
    server = HTTPServer(("", port), MyServerHandler)
    if logfile:
        logfile.write("NLTK Wordnet browser server running serving: %s\n" % url)
    if runBrowser:
        server_ready.set()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    if runBrowser:
        browser_thread.join()

    if logfile:
        logfile.close()


def startBrowser(url, server_ready):
    def run():
        server_ready.wait()
        time.sleep(1)  # Wait a little bit more, there's still the chance of
        # a race condition.
        webbrowser.open(url, new=2, autoraise=1)

    t = threading.Thread(target=run)
    t.start()
    return t


#####################################################################
# Utilities
#####################################################################


"""
WordNet Browser Utilities.

This provides a backend to both wxbrowse and browserver.py.
"""

################################################################################
#
# Main logic for wordnet browser.
#


# This is wrapped inside a function since wn is only available if the
# WordNet corpus is installed.
def _pos_tuples():
    return [
        (wn.NOUN, "N", "noun"),
        (wn.VERB, "V", "verb"),
        (wn.ADJ, "J", "adj"),
        (wn.ADV, "R", "adv"),
    ]


def _pos_match(pos_tuple):
    """
    This function returns the complete pos tuple for the partial pos
    tuple given to it.  It attempts to match it against the first
    non-null component of the given pos tuple.
    """
    if pos_tuple[0] == "s":
        pos_tuple = ("a", pos_tuple[1], pos_tuple[2])
    for n, x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples():
        if pt[n] == pos_tuple[n]:
            return pt
    return None


HYPONYM = 0
HYPERNYM = 1
CLASS_REGIONAL = 2
PART_HOLONYM = 3
PART_MERONYM = 4
ATTRIBUTE = 5
SUBSTANCE_HOLONYM = 6
SUBSTANCE_MERONYM = 7
MEMBER_HOLONYM = 8
MEMBER_MERONYM = 9
VERB_GROUP = 10
INSTANCE_HYPONYM = 12
INSTANCE_HYPERNYM = 13
CAUSE = 14
ALSO_SEE = 15
SIMILAR = 16
ENTAILMENT = 17
ANTONYM = 18
FRAMES = 19
PERTAINYM = 20

CLASS_CATEGORY = 21
CLASS_USAGE = 22
CLASS_REGIONAL = 23
CLASS_USAGE = 24
CLASS_CATEGORY = 11

DERIVATIONALLY_RELATED_FORM = 25

INDIRECT_HYPERNYMS = 26


def lemma_property(word, synset, func):
    def flattern(l):
        if l == []:
            return []
        else:
            return l[0] + flattern(l[1:])

    return flattern([func(l) for l in synset.lemmas() if l.name == word])


def rebuild_tree(orig_tree):
    node = orig_tree[0]
    children = orig_tree[1:]
    return (node, [rebuild_tree(t) for t in children])


def get_relations_data(word, synset):
    """
    Get synset relations data for a synset.  Note that this doesn't
    yet support things such as full hyponym vs direct hyponym.
    """
    if synset.pos() == wn.NOUN:
        return (
            (HYPONYM, "Hyponyms", synset.hyponyms()),
            (INSTANCE_HYPONYM, "Instance hyponyms", synset.instance_hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            #  hypernyms', 'Sister terms',
            (INSTANCE_HYPERNYM, "Instance hypernyms", synset.instance_hypernyms()),
            #            (CLASS_REGIONAL, ['domain term region'], ),
            (PART_HOLONYM, "Part holonyms", synset.part_holonyms()),
            (PART_MERONYM, "Part meronyms", synset.part_meronyms()),
            (SUBSTANCE_HOLONYM, "Substance holonyms", synset.substance_holonyms()),
            (SUBSTANCE_MERONYM, "Substance meronyms", synset.substance_meronyms()),
            (MEMBER_HOLONYM, "Member holonyms", synset.member_holonyms()),
            (MEMBER_MERONYM, "Member meronyms", synset.member_meronyms()),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ANTONYM, "Antonyms", lemma_property(word, synset, lambda l: l.antonyms())),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.VERB:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (HYPONYM, "Hyponym", synset.hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            (ENTAILMENT, "Entailments", synset.entailments()),
            (CAUSE, "Causes", synset.causes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
            (VERB_GROUP, "Verb Groups", synset.verb_groups()),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.ADJ or synset.pos == wn.ADJ_SAT:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (SIMILAR, "Similar to", synset.similar_tos()),
            # Participle of verb - not supported by corpus
            (
                PERTAINYM,
                "Pertainyms",
                lemma_property(word, synset, lambda l: l.pertainyms()),
            ),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
        )
    elif synset.pos() == wn.ADV:
        # This is weird. adverbs such as 'quick' and 'fast' don't seem
        # to have antonyms returned by the corpus.a
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
        )
        # Derived from adjective - not supported by corpus
    else:
        raise TypeError("Unhandles synset POS type: " + str(synset.pos()))


html_header = """
<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'
'http://www.w3.org/TR/html4/strict.dtd'>
<html>
<head>
<meta name='generator' content=
'HTML Tidy for Windows (vers 14 February 2006), see www.w3.org'>
<meta http-equiv='Content-Type' content=
'text/html; charset=us-ascii'>
<title>NLTK Wordnet Browser display of: %s</title></head>
<body bgcolor='#F5F5F5' text='#000000'>
"""
html_trailer = """
</body>
</html>
"""

explanation = """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.
</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width='100%'>
"""

# HTML oriented functions


def _bold(txt):
    return "<b>%s</b>" % txt


def _center(txt):
    return "<center>%s</center>" % txt


def _hlev(n, txt):
    return "<h%d>%s</h%d>" % (n, txt, n)


def _italic(txt):
    return "<i>%s</i>" % txt


def _li(txt):
    return "<li>%s</li>" % txt


def pg(word, body):
    """
    Return a HTML page of NLTK Browser format constructed from the
    word and body

    :param word: The word that the body corresponds to
    :type word: str
    :param body: The HTML body corresponding to the word
    :type body: str
    :return: a HTML page for the word-body combination
    :rtype: str
    """
    return (html_header % word) + body + html_trailer


def _ul(txt):
    return "<ul>" + txt + "</ul>"


def _abbc(txt):
    """
    abbc = asterisks, breaks, bold, center
    """
    return _center(_bold("<br>" * 10 + "*" * 10 + " " + txt + " " + "*" * 10))


full_hyponym_cont_text = _ul(_li(_italic("(has full hyponym continuation)"))) + "\n"


def _get_synset(synset_key):
    """
    The synset key is the unique name of the synset, this can be
    retrieved via synset.name()
    """
    return wn.synset(synset_key)


def _collect_one_synset(word, synset, synset_relations):
    """
    Returns the HTML string for one synset or word

    :param word: the current word
    :type word: str
    :param synset: a synset
    :type synset: synset
    :param synset_relations: information about which synset relations
    to display.
    :type synset_relations: dict(synset_key, set(relation_id))
    :return: The HTML string built for this synset
    :rtype: str
    """
    if isinstance(synset, tuple):  # It's a word
        raise NotImplementedError("word not supported by _collect_one_synset")

    typ = "S"
    pos_tuple = _pos_match((synset.pos(), None, None))
    assert pos_tuple is not None, "pos_tuple is null: synset.pos(): %s" % synset.pos()
    descr = pos_tuple[2]
    ref = copy.deepcopy(Reference(word, synset_relations))
    ref.toggle_synset(synset)
    synset_label = typ + ";"
    if synset.name() in synset_relations:
        synset_label = _bold(synset_label)
    s = f"<li>{make_lookup_link(ref, synset_label)} ({descr}) "

    def format_lemma(w):
        w = w.replace("_", " ")
        if w.lower() == word:
            return _bold(w)
        else:
            ref = Reference(w)
            return make_lookup_link(ref, w)

    s += ", ".join(format_lemma(l.name()) for l in synset.lemmas())

    gl = " ({}) <i>{}</i> ".format(
        synset.definition(),
        "; ".join('"%s"' % e for e in synset.examples()),
    )
    return s + gl + _synset_relations(word, synset, synset_relations) + "</li>\n"


def _collect_all_synsets(word, pos, synset_relations=dict()):
    """
    Return a HTML unordered list of synsets for the given word and
    part of speech.
    """
    return "<ul>%s\n</ul>\n" % "".join(
        _collect_one_synset(word, synset, synset_relations)
        for synset in wn.synsets(word, pos)
    )


def _synset_relations(word, synset, synset_relations):
    """
    Builds the HTML string for the relations of a synset

    :param word: The current word
    :type word: str
    :param synset: The synset for which we're building the relations.
    :type synset: Synset
    :param synset_relations: synset keys and relation types for which to display relations.
    :type synset_relations: dict(synset_key, set(relation_type))
    :return: The HTML for a synset's relations
    :rtype: str
    """

    if not synset.name() in synset_relations:
        return ""
    ref = Reference(word, synset_relations)

    def relation_html(r):
        if isinstance(r, Synset):
            return make_lookup_link(Reference(r.lemma_names()[0]), r.lemma_names()[0])
        elif isinstance(r, Lemma):
            return relation_html(r.synset())
        elif isinstance(r, tuple):
            # It's probably a tuple containing a Synset and a list of
            # similar tuples.  This forms a tree of synsets.
            return "{}\n<ul>{}</ul>\n".format(
                relation_html(r[0]),
                "".join("<li>%s</li>\n" % relation_html(sr) for sr in r[1]),
            )
        else:
            raise TypeError(
                "r must be a synset, lemma or list, it was: type(r) = %s, r = %s"
                % (type(r), r)
            )

    def make_synset_html(db_name, disp_name, rels):
        synset_html = "<i>%s</i>\n" % make_lookup_link(
            copy.deepcopy(ref).toggle_synset_relation(synset, db_name),
            disp_name,
        )

        if db_name in ref.synset_relations[synset.name()]:
            synset_html += "<ul>%s</ul>\n" % "".join(
                "<li>%s</li>\n" % relation_html(r) for r in rels
            )

        return synset_html

    html = (
        "<ul>"
        + "\n".join(
            "<li>%s</li>" % make_synset_html(*rel_data)
            for rel_data in get_relations_data(word, synset)
            if rel_data[2] != []
        )
        + "</ul>"
    )

    return html


class RestrictedUnpickler(pickle.Unpickler):
    """
    Unpickler that prevents any class or function from being used during loading.
    """

    def find_class(self, module, name):
        # Forbid every function
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


class Reference:
    """
    A reference to a page that may be generated by page_word
    """

    def __init__(self, word, synset_relations=dict()):
        """
        Build a reference to a new page.

        word is the word or words (separated by commas) for which to
        search for synsets of

        synset_relations is a dictionary of synset keys to sets of
        synset relation identifaiers to unfold a list of synset
        relations for.
        """
        self.word = word
        self.synset_relations = synset_relations

    def encode(self):
        """
        Encode this reference into a string to be used in a URL.
        """
        # This uses a tuple rather than an object since the python
        # pickle representation is much smaller and there is no need
        # to represent the complete object.
        string = pickle.dumps((self.word, self.synset_relations), -1)
        return base64.urlsafe_b64encode(string).decode()

    @staticmethod
    def decode(string):
        """
        Decode a reference encoded with Reference.encode
        """
        string = base64.urlsafe_b64decode(string.encode())
        word, synset_relations = RestrictedUnpickler(io.BytesIO(string)).load()
        return Reference(word, synset_relations)

    def toggle_synset_relation(self, synset, relation):
        """
        Toggle the display of the relations for the given synset and
        relation type.

        This function will throw a KeyError if the synset is currently
        not being displayed.
        """
        if relation in self.synset_relations[synset.name()]:
            self.synset_relations[synset.name()].remove(relation)
        else:
            self.synset_relations[synset.name()].add(relation)

        return self

    def toggle_synset(self, synset):
        """
        Toggle displaying of the relation types for the given synset
        """
        if synset.name() in self.synset_relations:
            del self.synset_relations[synset.name()]
        else:
            self.synset_relations[synset.name()] = set()

        return self


def make_lookup_link(ref, label):
    return f'<a href="lookup_{ref.encode()}">{label}</a>'


def page_from_word(word):
    """
    Return a HTML page for the given word.

    :type word: str
    :param word: The currently active word
    :return: A tuple (page,word), where page is the new current HTML page
        to be sent to the browser and
        word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference(word))


def page_from_href(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference.decode(href))


def page_from_reference(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    word = href.word
    pos_forms = defaultdict(list)
    words = word.split(",")
    words = [w for w in [w.strip().lower().replace(" ", "_") for w in words] if w != ""]
    if len(words) == 0:
        # No words were found.
        return "", "Please specify a word to search for."

    # This looks up multiple words at once.  This is probably not
    # necessary and may lead to problems.
    for w in words:
        for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
            form = wn.morphy(w, pos)
            if form and form not in pos_forms[pos]:
                pos_forms[pos].append(form)
    body = ""
    for pos, pos_str, name in _pos_tuples():
        if pos in pos_forms:
            body += _hlev(3, name) + "\n"
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    body += _collect_all_synsets(w, pos, href.synset_relations)
                except KeyError:
                    pass
    if not body:
        body = "The word or words '%s' were not found in the dictionary." % word
    return body, word


#####################################################################
# Static pages
#####################################################################


def get_static_page_by_path(path):
    """
    Return a static HTML page from the path given.
    """
    if path == "index_2.html":
        return get_static_index_page(False)
    elif path == "index.html":
        return get_static_index_page(True)
    elif path == "NLTK Wordnet Browser Database Info.html":
        return "Display of Wordnet Database Statistics is not supported"
    elif path == "upper_2.html":
        return get_static_upper_page(False)
    elif path == "upper.html":
        return get_static_upper_page(True)
    elif path == "web_help.html":
        return get_static_web_help_page()
    elif path == "wx_help.html":
        return get_static_wx_help_page()
    raise FileNotFoundError()


def get_static_web_help_page():
    """
    Return the static web help page.
    """
    return """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database.
<p><b>You are using the Javascript client part of the NLTK Wordnet BrowseServer.</b> We assume your browser is in tab sheets enabled mode.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <a href="https://wordnet.princeton.edu/"><b> https://wordnet.princeton.edu/</b></a>. For more information on the NLTK project, see the project home:
<a href="https://www.nltk.org/"><b>https://www.nltk.org/</b></a>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>New Word</b> field and the search started with Enter or by clicking the <b>Search</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>The Buttons</h3>
<p>The <b>Search</b> and <b>Help</b> buttons need no more explanation. </p>
<p>The <b>Show Database Info</b> button shows a collection of Wordnet database statistics.</p>
<p>The <b>Shutdown the Server</b> button is shown for the first client of the BrowServer program i.e. for the client that is automatically launched when the BrowServer is started but not for the succeeding clients in order to protect the server from accidental shutdowns.
</p></body>
</html>
"""


def get_static_welcome_message():
    """
    Get the static welcome page.
    """
    return """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Next Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
"""


def get_static_index_page(with_shutdown):
    """
    Get the static index page.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"  "http://www.w3.org/TR/html4/frameset.dtd">
<HTML>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <HEAD>
         <TITLE>NLTK Wordnet Browser</TITLE>
     </HEAD>

<frameset rows="7%%,93%%">
    <frame src="%s" name="header">
    <frame src="start_page" name="body">
</frameset>
</HTML>
"""
    if with_shutdown:
        upper_link = "upper.html"
    else:
        upper_link = "upper_2.html"

    return template % upper_link


def get_static_upper_page(with_shutdown):
    """
    Return the upper frame page,

    If with_shutdown is True then a 'shutdown' button is also provided
    to shutdown the server.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
        Copyright (C) 2001-2024 NLTK Project
        Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
        URL: <https://www.nltk.org/>
        For license information, see LICENSE.TXT -->
    <head>
                <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
        <title>Untitled Document</title>
    </head>
    <body>
    <form method="GET" action="search" target="body">
            Current Word:&nbsp;<input type="text" id="currentWord" size="10" disabled>
            Next Word:&nbsp;<input type="text" id="nextWord" name="nextWord" size="10">
            <input name="searchButton" type="submit" value="Search">
    </form>
        <a target="body" href="web_help.html">Help</a>
        %s

</body>
</html>
"""
    if with_shutdown:
        shutdown_link = '<a href="SHUTDOWN THE SERVER">Shutdown</a>'
    else:
        shutdown_link = ""

    return template % shutdown_link


def usage():
    """
    Display the command line help message.
    """
    print(__doc__)


def app():
    # Parse and interpret options.
    (opts, _) = getopt.getopt(
        argv[1:], "l:p:sh", ["logfile=", "port=", "server-mode", "help"]
    )
    port = 8000
    server_mode = False
    help_mode = False
    logfilename = None
    for opt, value in opts:
        if (opt == "-l") or (opt == "--logfile"):
            logfilename = str(value)
        elif (opt == "-p") or (opt == "--port"):
            port = int(value)
        elif (opt == "-s") or (opt == "--server-mode"):
            server_mode = True
        elif (opt == "-h") or (opt == "--help"):
            help_mode = True

    if help_mode:
        usage()
    else:
        wnb(port, not server_mode, logfilename)


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\wordnet_app.py ===
# Natural Language Toolkit: WordNet Browser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A WordNet Browser application which launches the default browser
(if it is not already running) and opens a new tab with a connection
to http://localhost:port/ .  It also starts an HTTP server on the
specified port and begins serving browser requests.  The default
port is 8000.  (For command-line help, run "python wordnet -h")
This application requires that the user's web browser supports
Javascript.

BrowServer is a server for browsing the NLTK Wordnet database It first
launches a browser client to be used for browsing and then starts
serving the requests of that and maybe other clients

Usage::

    browserver.py -h
    browserver.py [-s] [-p <port>]

Options::

    -h or --help
        Display this help message.

    -l <file> or --log-file <file>
        Logs messages to the given file, If this option is not specified
        messages are silently dropped.

    -p <port> or --port <port>
        Run the web server on this TCP port, defaults to 8000.

    -s or --server-mode
        Do not start a web browser, and do not allow a user to
        shutdown the server through the web interface.
"""
# TODO: throughout this package variable names and docstrings need
# modifying to be compliant with NLTK's coding standards.  Tests also
# need to be develop to ensure this continues to work in the face of
# changes to other NLTK packages.

import base64
import copy
import getopt
import io
import os
import pickle
import sys
import threading
import time
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

# Allow this program to run inside the NLTK source tree.
from sys import argv
from urllib.parse import unquote_plus

from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Lemma, Synset

firstClient = True

# True if we're not also running a web browser.  The value f server_mode
# gets set by demo().
server_mode = None

# If set this is a file object for writing log messages.
logfile = None


class MyServerHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_head()

    def do_GET(self):
        global firstClient
        sp = self.path[1:]
        if unquote_plus(sp) == "SHUTDOWN THE SERVER":
            if server_mode:
                page = "Server must be killed with SIGTERM."
                type = "text/plain"
            else:
                print("Server shutting down!")
                os._exit(0)

        elif sp == "":  # First request.
            type = "text/html"
            if not server_mode and firstClient:
                firstClient = False
                page = get_static_index_page(True)
            else:
                page = get_static_index_page(False)
            word = "green"

        elif sp.endswith(".html"):  # Trying to fetch a HTML file TODO:
            type = "text/html"
            usp = unquote_plus(sp)
            if usp == "NLTK Wordnet Browser Database Info.html":
                word = "* Database Info *"
                if os.path.isfile(usp):
                    with open(usp) as infile:
                        page = infile.read()
                else:
                    page = (
                        (html_header % word) + "<p>The database info file:"
                        "<p><b>"
                        + usp
                        + "</b>"
                        + "<p>was not found. Run this:"
                        + "<p><b>python dbinfo_html.py</b>"
                        + "<p>to produce it."
                        + html_trailer
                    )
            else:
                # Handle files here.
                word = sp
                try:
                    page = get_static_page_by_path(usp)
                except FileNotFoundError:
                    page = "Internal error: Path for static page '%s' is unknown" % usp
                    # Set type to plain to prevent XSS by printing the path as HTML
                    type = "text/plain"
        elif sp.startswith("search"):
            # This doesn't seem to work with MWEs.
            type = "text/html"
            parts = (sp.split("?")[1]).split("&")
            word = [
                p.split("=")[1].replace("+", " ")
                for p in parts
                if p.startswith("nextWord")
            ][0]
            page, word = page_from_word(word)
        elif sp.startswith("lookup_"):
            # TODO add a variation of this that takes a non ecoded word or MWE.
            type = "text/html"
            sp = sp[len("lookup_") :]
            page, word = page_from_href(sp)
        elif sp == "start_page":
            # if this is the first request we should display help
            # information, and possibly set a default word.
            type = "text/html"
            page, word = page_from_word("wordnet")
        else:
            type = "text/plain"
            page = "Could not parse request: '%s'" % sp

        # Send result.
        self.send_head(type)
        self.wfile.write(page.encode("utf8"))

    def send_head(self, type=None):
        self.send_response(200)
        self.send_header("Content-type", type)
        self.end_headers()

    def log_message(self, format, *args):
        global logfile

        if logfile:
            logfile.write(
                "%s - - [%s] %s\n"
                % (self.address_string(), self.log_date_time_string(), format % args)
            )


def get_unique_counter_from_url(sp):
    """
    Extract the unique counter from the URL if it has one.  Otherwise return
    null.
    """
    pos = sp.rfind("%23")
    if pos != -1:
        return int(sp[(pos + 3) :])
    else:
        return None


def wnb(port=8000, runBrowser=True, logfilename=None):
    """
    Run NLTK Wordnet Browser Server.

    :param port: The port number for the server to listen on, defaults to
                 8000
    :type  port: int

    :param runBrowser: True to start a web browser and point it at the web
                       server.
    :type  runBrowser: bool
    """
    # The webbrowser module is unpredictable, typically it blocks if it uses
    # a console web browser, and doesn't block if it uses a GUI webbrowser,
    # so we need to force it to have a clear correct behaviour.
    #
    # Normally the server should run for as long as the user wants. they
    # should idealy be able to control this from the UI by closing the
    # window or tab.  Second best would be clicking a button to say
    # 'Shutdown' that first shutsdown the server and closes the window or
    # tab, or exits the text-mode browser.  Both of these are unfreasable.
    #
    # The next best alternative is to start the server, have it close when
    # it receives SIGTERM (default), and run the browser as well.  The user
    # may have to shutdown both programs.
    #
    # Since webbrowser may block, and the webserver will block, we must run
    # them in separate threads.
    #
    global server_mode, logfile
    server_mode = not runBrowser

    # Setup logging.
    if logfilename:
        try:
            logfile = open(logfilename, "a", 1)  # 1 means 'line buffering'
        except OSError as e:
            sys.stderr.write("Couldn't open %s for writing: %s", logfilename, e)
            sys.exit(1)
    else:
        logfile = None

    # Compute URL and start web browser
    url = "http://localhost:" + str(port)

    server_ready = None
    browser_thread = None

    if runBrowser:
        server_ready = threading.Event()
        browser_thread = startBrowser(url, server_ready)

    # Start the server.
    server = HTTPServer(("", port), MyServerHandler)
    if logfile:
        logfile.write("NLTK Wordnet browser server running serving: %s\n" % url)
    if runBrowser:
        server_ready.set()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    if runBrowser:
        browser_thread.join()

    if logfile:
        logfile.close()


def startBrowser(url, server_ready):
    def run():
        server_ready.wait()
        time.sleep(1)  # Wait a little bit more, there's still the chance of
        # a race condition.
        webbrowser.open(url, new=2, autoraise=1)

    t = threading.Thread(target=run)
    t.start()
    return t


#####################################################################
# Utilities
#####################################################################


"""
WordNet Browser Utilities.

This provides a backend to both wxbrowse and browserver.py.
"""

################################################################################
#
# Main logic for wordnet browser.
#


# This is wrapped inside a function since wn is only available if the
# WordNet corpus is installed.
def _pos_tuples():
    return [
        (wn.NOUN, "N", "noun"),
        (wn.VERB, "V", "verb"),
        (wn.ADJ, "J", "adj"),
        (wn.ADV, "R", "adv"),
    ]


def _pos_match(pos_tuple):
    """
    This function returns the complete pos tuple for the partial pos
    tuple given to it.  It attempts to match it against the first
    non-null component of the given pos tuple.
    """
    if pos_tuple[0] == "s":
        pos_tuple = ("a", pos_tuple[1], pos_tuple[2])
    for n, x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples():
        if pt[n] == pos_tuple[n]:
            return pt
    return None


HYPONYM = 0
HYPERNYM = 1
CLASS_REGIONAL = 2
PART_HOLONYM = 3
PART_MERONYM = 4
ATTRIBUTE = 5
SUBSTANCE_HOLONYM = 6
SUBSTANCE_MERONYM = 7
MEMBER_HOLONYM = 8
MEMBER_MERONYM = 9
VERB_GROUP = 10
INSTANCE_HYPONYM = 12
INSTANCE_HYPERNYM = 13
CAUSE = 14
ALSO_SEE = 15
SIMILAR = 16
ENTAILMENT = 17
ANTONYM = 18
FRAMES = 19
PERTAINYM = 20

CLASS_CATEGORY = 21
CLASS_USAGE = 22
CLASS_REGIONAL = 23
CLASS_USAGE = 24
CLASS_CATEGORY = 11

DERIVATIONALLY_RELATED_FORM = 25

INDIRECT_HYPERNYMS = 26


def lemma_property(word, synset, func):
    def flattern(l):
        if l == []:
            return []
        else:
            return l[0] + flattern(l[1:])

    return flattern([func(l) for l in synset.lemmas() if l.name == word])


def rebuild_tree(orig_tree):
    node = orig_tree[0]
    children = orig_tree[1:]
    return (node, [rebuild_tree(t) for t in children])


def get_relations_data(word, synset):
    """
    Get synset relations data for a synset.  Note that this doesn't
    yet support things such as full hyponym vs direct hyponym.
    """
    if synset.pos() == wn.NOUN:
        return (
            (HYPONYM, "Hyponyms", synset.hyponyms()),
            (INSTANCE_HYPONYM, "Instance hyponyms", synset.instance_hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            #  hypernyms', 'Sister terms',
            (INSTANCE_HYPERNYM, "Instance hypernyms", synset.instance_hypernyms()),
            #            (CLASS_REGIONAL, ['domain term region'], ),
            (PART_HOLONYM, "Part holonyms", synset.part_holonyms()),
            (PART_MERONYM, "Part meronyms", synset.part_meronyms()),
            (SUBSTANCE_HOLONYM, "Substance holonyms", synset.substance_holonyms()),
            (SUBSTANCE_MERONYM, "Substance meronyms", synset.substance_meronyms()),
            (MEMBER_HOLONYM, "Member holonyms", synset.member_holonyms()),
            (MEMBER_MERONYM, "Member meronyms", synset.member_meronyms()),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ANTONYM, "Antonyms", lemma_property(word, synset, lambda l: l.antonyms())),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.VERB:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (HYPONYM, "Hyponym", synset.hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            (ENTAILMENT, "Entailments", synset.entailments()),
            (CAUSE, "Causes", synset.causes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
            (VERB_GROUP, "Verb Groups", synset.verb_groups()),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.ADJ or synset.pos == wn.ADJ_SAT:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (SIMILAR, "Similar to", synset.similar_tos()),
            # Participle of verb - not supported by corpus
            (
                PERTAINYM,
                "Pertainyms",
                lemma_property(word, synset, lambda l: l.pertainyms()),
            ),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
        )
    elif synset.pos() == wn.ADV:
        # This is weird. adverbs such as 'quick' and 'fast' don't seem
        # to have antonyms returned by the corpus.a
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
        )
        # Derived from adjective - not supported by corpus
    else:
        raise TypeError("Unhandles synset POS type: " + str(synset.pos()))


html_header = """
<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'
'http://www.w3.org/TR/html4/strict.dtd'>
<html>
<head>
<meta name='generator' content=
'HTML Tidy for Windows (vers 14 February 2006), see www.w3.org'>
<meta http-equiv='Content-Type' content=
'text/html; charset=us-ascii'>
<title>NLTK Wordnet Browser display of: %s</title></head>
<body bgcolor='#F5F5F5' text='#000000'>
"""
html_trailer = """
</body>
</html>
"""

explanation = """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.
</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width='100%'>
"""

# HTML oriented functions


def _bold(txt):
    return "<b>%s</b>" % txt


def _center(txt):
    return "<center>%s</center>" % txt


def _hlev(n, txt):
    return "<h%d>%s</h%d>" % (n, txt, n)


def _italic(txt):
    return "<i>%s</i>" % txt


def _li(txt):
    return "<li>%s</li>" % txt


def pg(word, body):
    """
    Return a HTML page of NLTK Browser format constructed from the
    word and body

    :param word: The word that the body corresponds to
    :type word: str
    :param body: The HTML body corresponding to the word
    :type body: str
    :return: a HTML page for the word-body combination
    :rtype: str
    """
    return (html_header % word) + body + html_trailer


def _ul(txt):
    return "<ul>" + txt + "</ul>"


def _abbc(txt):
    """
    abbc = asterisks, breaks, bold, center
    """
    return _center(_bold("<br>" * 10 + "*" * 10 + " " + txt + " " + "*" * 10))


full_hyponym_cont_text = _ul(_li(_italic("(has full hyponym continuation)"))) + "\n"


def _get_synset(synset_key):
    """
    The synset key is the unique name of the synset, this can be
    retrieved via synset.name()
    """
    return wn.synset(synset_key)


def _collect_one_synset(word, synset, synset_relations):
    """
    Returns the HTML string for one synset or word

    :param word: the current word
    :type word: str
    :param synset: a synset
    :type synset: synset
    :param synset_relations: information about which synset relations
    to display.
    :type synset_relations: dict(synset_key, set(relation_id))
    :return: The HTML string built for this synset
    :rtype: str
    """
    if isinstance(synset, tuple):  # It's a word
        raise NotImplementedError("word not supported by _collect_one_synset")

    typ = "S"
    pos_tuple = _pos_match((synset.pos(), None, None))
    assert pos_tuple is not None, "pos_tuple is null: synset.pos(): %s" % synset.pos()
    descr = pos_tuple[2]
    ref = copy.deepcopy(Reference(word, synset_relations))
    ref.toggle_synset(synset)
    synset_label = typ + ";"
    if synset.name() in synset_relations:
        synset_label = _bold(synset_label)
    s = f"<li>{make_lookup_link(ref, synset_label)} ({descr}) "

    def format_lemma(w):
        w = w.replace("_", " ")
        if w.lower() == word:
            return _bold(w)
        else:
            ref = Reference(w)
            return make_lookup_link(ref, w)

    s += ", ".join(format_lemma(l.name()) for l in synset.lemmas())

    gl = " ({}) <i>{}</i> ".format(
        synset.definition(),
        "; ".join('"%s"' % e for e in synset.examples()),
    )
    return s + gl + _synset_relations(word, synset, synset_relations) + "</li>\n"


def _collect_all_synsets(word, pos, synset_relations=dict()):
    """
    Return a HTML unordered list of synsets for the given word and
    part of speech.
    """
    return "<ul>%s\n</ul>\n" % "".join(
        _collect_one_synset(word, synset, synset_relations)
        for synset in wn.synsets(word, pos)
    )


def _synset_relations(word, synset, synset_relations):
    """
    Builds the HTML string for the relations of a synset

    :param word: The current word
    :type word: str
    :param synset: The synset for which we're building the relations.
    :type synset: Synset
    :param synset_relations: synset keys and relation types for which to display relations.
    :type synset_relations: dict(synset_key, set(relation_type))
    :return: The HTML for a synset's relations
    :rtype: str
    """

    if not synset.name() in synset_relations:
        return ""
    ref = Reference(word, synset_relations)

    def relation_html(r):
        if isinstance(r, Synset):
            return make_lookup_link(Reference(r.lemma_names()[0]), r.lemma_names()[0])
        elif isinstance(r, Lemma):
            return relation_html(r.synset())
        elif isinstance(r, tuple):
            # It's probably a tuple containing a Synset and a list of
            # similar tuples.  This forms a tree of synsets.
            return "{}\n<ul>{}</ul>\n".format(
                relation_html(r[0]),
                "".join("<li>%s</li>\n" % relation_html(sr) for sr in r[1]),
            )
        else:
            raise TypeError(
                "r must be a synset, lemma or list, it was: type(r) = %s, r = %s"
                % (type(r), r)
            )

    def make_synset_html(db_name, disp_name, rels):
        synset_html = "<i>%s</i>\n" % make_lookup_link(
            copy.deepcopy(ref).toggle_synset_relation(synset, db_name),
            disp_name,
        )

        if db_name in ref.synset_relations[synset.name()]:
            synset_html += "<ul>%s</ul>\n" % "".join(
                "<li>%s</li>\n" % relation_html(r) for r in rels
            )

        return synset_html

    html = (
        "<ul>"
        + "\n".join(
            "<li>%s</li>" % make_synset_html(*rel_data)
            for rel_data in get_relations_data(word, synset)
            if rel_data[2] != []
        )
        + "</ul>"
    )

    return html


class RestrictedUnpickler(pickle.Unpickler):
    """
    Unpickler that prevents any class or function from being used during loading.
    """

    def find_class(self, module, name):
        # Forbid every function
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


class Reference:
    """
    A reference to a page that may be generated by page_word
    """

    def __init__(self, word, synset_relations=dict()):
        """
        Build a reference to a new page.

        word is the word or words (separated by commas) for which to
        search for synsets of

        synset_relations is a dictionary of synset keys to sets of
        synset relation identifaiers to unfold a list of synset
        relations for.
        """
        self.word = word
        self.synset_relations = synset_relations

    def encode(self):
        """
        Encode this reference into a string to be used in a URL.
        """
        # This uses a tuple rather than an object since the python
        # pickle representation is much smaller and there is no need
        # to represent the complete object.
        string = pickle.dumps((self.word, self.synset_relations), -1)
        return base64.urlsafe_b64encode(string).decode()

    @staticmethod
    def decode(string):
        """
        Decode a reference encoded with Reference.encode
        """
        string = base64.urlsafe_b64decode(string.encode())
        word, synset_relations = RestrictedUnpickler(io.BytesIO(string)).load()
        return Reference(word, synset_relations)

    def toggle_synset_relation(self, synset, relation):
        """
        Toggle the display of the relations for the given synset and
        relation type.

        This function will throw a KeyError if the synset is currently
        not being displayed.
        """
        if relation in self.synset_relations[synset.name()]:
            self.synset_relations[synset.name()].remove(relation)
        else:
            self.synset_relations[synset.name()].add(relation)

        return self

    def toggle_synset(self, synset):
        """
        Toggle displaying of the relation types for the given synset
        """
        if synset.name() in self.synset_relations:
            del self.synset_relations[synset.name()]
        else:
            self.synset_relations[synset.name()] = set()

        return self


def make_lookup_link(ref, label):
    return f'<a href="lookup_{ref.encode()}">{label}</a>'


def page_from_word(word):
    """
    Return a HTML page for the given word.

    :type word: str
    :param word: The currently active word
    :return: A tuple (page,word), where page is the new current HTML page
        to be sent to the browser and
        word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference(word))


def page_from_href(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    return page_from_reference(Reference.decode(href))


def page_from_reference(href):
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    word = href.word
    pos_forms = defaultdict(list)
    words = word.split(",")
    words = [w for w in [w.strip().lower().replace(" ", "_") for w in words] if w != ""]
    if len(words) == 0:
        # No words were found.
        return "", "Please specify a word to search for."

    # This looks up multiple words at once.  This is probably not
    # necessary and may lead to problems.
    for w in words:
        for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
            form = wn.morphy(w, pos)
            if form and form not in pos_forms[pos]:
                pos_forms[pos].append(form)
    body = ""
    for pos, pos_str, name in _pos_tuples():
        if pos in pos_forms:
            body += _hlev(3, name) + "\n"
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    body += _collect_all_synsets(w, pos, href.synset_relations)
                except KeyError:
                    pass
    if not body:
        body = "The word or words '%s' were not found in the dictionary." % word
    return body, word


#####################################################################
# Static pages
#####################################################################


def get_static_page_by_path(path):
    """
    Return a static HTML page from the path given.
    """
    if path == "index_2.html":
        return get_static_index_page(False)
    elif path == "index.html":
        return get_static_index_page(True)
    elif path == "NLTK Wordnet Browser Database Info.html":
        return "Display of Wordnet Database Statistics is not supported"
    elif path == "upper_2.html":
        return get_static_upper_page(False)
    elif path == "upper.html":
        return get_static_upper_page(True)
    elif path == "web_help.html":
        return get_static_web_help_page()
    elif path == "wx_help.html":
        return get_static_wx_help_page()
    raise FileNotFoundError()


def get_static_web_help_page():
    """
    Return the static web help page.
    """
    return """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database.
<p><b>You are using the Javascript client part of the NLTK Wordnet BrowseServer.</b> We assume your browser is in tab sheets enabled mode.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <a href="https://wordnet.princeton.edu/"><b> https://wordnet.princeton.edu/</b></a>. For more information on the NLTK project, see the project home:
<a href="https://www.nltk.org/"><b>https://www.nltk.org/</b></a>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>New Word</b> field and the search started with Enter or by clicking the <b>Search</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>The Buttons</h3>
<p>The <b>Search</b> and <b>Help</b> buttons need no more explanation. </p>
<p>The <b>Show Database Info</b> button shows a collection of Wordnet database statistics.</p>
<p>The <b>Shutdown the Server</b> button is shown for the first client of the BrowServer program i.e. for the client that is automatically launched when the BrowServer is started but not for the succeeding clients in order to protect the server from accidental shutdowns.
</p></body>
</html>
"""


def get_static_welcome_message():
    """
    Get the static welcome page.
    """
    return """
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Next Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
"""


def get_static_index_page(with_shutdown):
    """
    Get the static index page.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"  "http://www.w3.org/TR/html4/frameset.dtd">
<HTML>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2001-2024 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <https://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <HEAD>
         <TITLE>NLTK Wordnet Browser</TITLE>
     </HEAD>

<frameset rows="7%%,93%%">
    <frame src="%s" name="header">
    <frame src="start_page" name="body">
</frameset>
</HTML>
"""
    if with_shutdown:
        upper_link = "upper.html"
    else:
        upper_link = "upper_2.html"

    return template % upper_link


def get_static_upper_page(with_shutdown):
    """
    Return the upper frame page,

    If with_shutdown is True then a 'shutdown' button is also provided
    to shutdown the server.
    """
    template = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
        Copyright (C) 2001-2024 NLTK Project
        Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
        URL: <https://www.nltk.org/>
        For license information, see LICENSE.TXT -->
    <head>
                <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
        <title>Untitled Document</title>
    </head>
    <body>
    <form method="GET" action="search" target="body">
            Current Word:&nbsp;<input type="text" id="currentWord" size="10" disabled>
            Next Word:&nbsp;<input type="text" id="nextWord" name="nextWord" size="10">
            <input name="searchButton" type="submit" value="Search">
    </form>
        <a target="body" href="web_help.html">Help</a>
        %s

</body>
</html>
"""
    if with_shutdown:
        shutdown_link = '<a href="SHUTDOWN THE SERVER">Shutdown</a>'
    else:
        shutdown_link = ""

    return template % shutdown_link


def usage():
    """
    Display the command line help message.
    """
    print(__doc__)


def app():
    # Parse and interpret options.
    (opts, _) = getopt.getopt(
        argv[1:], "l:p:sh", ["logfile=", "port=", "server-mode", "help"]
    )
    port = 8000
    server_mode = False
    help_mode = False
    logfilename = None
    for opt, value in opts:
        if (opt == "-l") or (opt == "--logfile"):
            logfilename = str(value)
        elif (opt == "-p") or (opt == "--port"):
            port = int(value)
        elif (opt == "-s") or (opt == "--server-mode"):
            server_mode = True
        elif (opt == "-h") or (opt == "--help"):
            help_mode = True

    if help_mode:
        usage()
    else:
        wnb(port, not server_mode, logfilename)


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/openenv\Lib\site-packages\nltk\app\srparser_app.py ===
# Natural Language Toolkit: Shift-Reduce Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the shift-reduce parser.

The shift-reduce parser maintains a stack, which records the structure
of the portion of the text that has been parsed.  The stack is
initially empty.  Its contents are shown on the left side of the main
canvas.

On the right side of the main canvas is the remaining text.  This is
the portion of the text which has not yet been considered by the
parser.

The parser builds up a tree structure for the text using two
operations:

  - "shift" moves the first token from the remaining text to the top
    of the stack.  In the demo, the top of the stack is its right-hand
    side.
  - "reduce" uses a grammar production to combine the rightmost stack
    elements into a single tree token.

You can control the parser's operation by using the "shift" and
"reduce" buttons; or you can use the "step" button to let the parser
automatically decide which operation to apply.  The parser uses the
following rules to decide which operation to apply:

  - Only shift if no reductions are available.
  - If multiple reductions are available, then apply the reduction
    whose CFG production is listed earliest in the grammar.

The "reduce" button applies the reduction whose CFG production is
listed earliest in the grammar.  There are two ways to manually choose
which reduction to apply:

  - Click on a CFG production from the list of available reductions,
    on the left side of the main window.  The reduction based on that
    production will be applied to the top of the stack.
  - Click on one of the stack elements.  A popup window will appear,
    containing all available reductions.  Select one, and it will be
    applied to the top of the stack.

Note that reductions can only be applied to the top of the stack.

Keyboard Shortcuts::
      [Space]\t Perform the next shift or reduce operation
      [s]\t Perform a shift operation
      [r]\t Perform a reduction operation
      [Ctrl-z]\t Undo most recent operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available production list
      [Ctrl-a]\t Toggle animations
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit

"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingShiftReduceParser
from nltk.tree import Tree
from nltk.util import in_idle

"""
Possible future improvements:
  - button/window to change and/or select text.  Just pop up a window
    with an entry, and let them modify the text; and then retokenize
    it?  Maybe give a warning if it contains tokens whose types are
    not in the grammar.
  - button/window to change and/or select grammar.  Select from
    several alternative grammars?  Or actually change the grammar?  If
    the later, then I'd want to define nltk.draw.cfg, which would be
    responsible for that.
"""


class ShiftReduceApp:
    """
    A graphical tool for exploring the shift-reduce parser.  The tool
    displays the parser's stack and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can shift tokens onto the stack, and can perform reductions on the
    top elements of the stack.  A "step" button simply steps through
    the parsing process, performing the operations that
    ``nltk.parse.ShiftReduceParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingShiftReduceParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Shift Reduce Parser Application")

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animating_lock = 0
        self._animate = IntVar(self._top)
        self._animate.set(10)  # = medium

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Initialize fonts.
        self._init_fonts(self._top)

        # Set up key bindings.
        self._init_bindings()

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # A popup menu for reducing.
        self._reduce_menu = Menu(self._canvas, tearoff=0)

        # Reset the demo, and set the feedback frame to empty.
        self.reset()
        self._lastoper1["text"] = ""

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Reductions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if 1:  # len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

        # When they hover over a production, highlight it.
        self._hover = -1
        self._prodlist.bind("<Motion>", self._highlight_hover)
        self._prodlist.bind("<Leave>", self._clear_hover)

    def _init_bindings(self):
        # Quit
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Alt-q>", self.destroy)
        self._top.bind("<Alt-x>", self.destroy)

        # Ops (step, shift, reduce, undo)
        self._top.bind("<space>", self.step)
        self._top.bind("<s>", self.shift)
        self._top.bind("<Alt-s>", self.shift)
        self._top.bind("<Control-s>", self.shift)
        self._top.bind("<r>", self.reduce)
        self._top.bind("<Alt-r>", self.reduce)
        self._top.bind("<Control-r>", self.reduce)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<u>", self.undo)
        self._top.bind("<Alt-u>", self.undo)
        self._top.bind("<Control-u>", self.undo)
        self._top.bind("<Control-z>", self.undo)
        self._top.bind("<BackSpace>", self.undo)

        # Misc
        self._top.bind("<Control-p>", self.postscript)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._top.bind("-", lambda e, a=self._animate: a.set(20))
        self._top.bind("=", lambda e, a=self._animate: a.set(10))
        self._top.bind("+", lambda e, a=self._animate: a.set(4))

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom")
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Shift",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.shift,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Reduce",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.reduce,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Undo",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.undo,
        ).pack(side="left")

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Shift", underline=0, command=self.shift, accelerator="Ctrl-s"
        )
        rulemenu.add_command(
            label="Reduce", underline=0, command=self.reduce, accelerator="Ctrl-r"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Undo", underline=0, command=self.undo, accelerator="Ctrl-u"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=20,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=10,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=4,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            width=525,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        self._stackwidgets = []
        self._rtextwidgets = []
        self._titlebar = canvas.create_rectangle(
            0, 0, 0, 0, fill="#c0f0f0", outline="black"
        )
        self._exprline = canvas.create_line(0, 0, 0, 0, dash=".")
        self._stacktop = canvas.create_line(0, 0, 0, 0, fill="#408080")
        size = self._size.get() + 4
        self._stacklabel = TextWidget(
            canvas, "Stack", color="#004040", font=self._boldfont
        )
        self._rtextlabel = TextWidget(
            canvas, "Remaining Text", color="#004040", font=self._boldfont
        )
        self._cframe.add_widget(self._stacklabel)
        self._cframe.add_widget(self._rtextlabel)

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        scrollregion = self._canvas["scrollregion"].split()
        (cx1, cy1, cx2, cy2) = (int(c) for c in scrollregion)

        # Delete the old stack & rtext widgets.
        for stackwidget in self._stackwidgets:
            self._cframe.destroy_widget(stackwidget)
        self._stackwidgets = []
        for rtextwidget in self._rtextwidgets:
            self._cframe.destroy_widget(rtextwidget)
        self._rtextwidgets = []

        # Position the titlebar & exprline
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        y = y2 - y1 + 10
        self._canvas.coords(self._titlebar, -5000, 0, 5000, y - 4)
        self._canvas.coords(self._exprline, 0, y * 2 - 10, 5000, y * 2 - 10)

        # Position the titlebar labels..
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        self._stacklabel.move(5 - x1, 3 - y1)
        (x1, y1, x2, y2) = self._rtextlabel.bbox()
        self._rtextlabel.move(cx2 - x2 - 5, 3 - y1)

        # Draw the stack.
        stackx = 5
        for tok in self._parser.stack():
            if isinstance(tok, Tree):
                attribs = {
                    "tree_color": "#4080a0",
                    "tree_width": 2,
                    "node_font": self._boldfont,
                    "node_color": "#006060",
                    "leaf_color": "#006060",
                    "leaf_font": self._font,
                }
                widget = tree_to_treesegment(self._canvas, tok, **attribs)
                widget.label()["color"] = "#000000"
            else:
                widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            widget.bind_click(self._popup_reduce)
            self._stackwidgets.append(widget)
            self._cframe.add_widget(widget, stackx, y)
            stackx = widget.bbox()[2] + 10

        # Draw the remaining text.
        rtextwidth = 0
        for tok in self._parser.remaining_text():
            widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            self._rtextwidgets.append(widget)
            self._cframe.add_widget(widget, rtextwidth, y)
            rtextwidth = widget.bbox()[2] + 4

        # Allow enough room to shift the next token (for animations)
        if len(self._rtextwidgets) > 0:
            stackx += self._rtextwidgets[0].width()

        # Move the remaining text to the correct location (keep it
        # right-justified, when possible); and move the remaining text
        # label, if necessary.
        stackx = max(stackx, self._stacklabel.width() + 25)
        rlabelwidth = self._rtextlabel.width() + 10
        if stackx >= cx2 - max(rtextwidth, rlabelwidth):
            cx2 = stackx + max(rtextwidth, rlabelwidth)
        for rtextwidget in self._rtextwidgets:
            rtextwidget.move(4 + cx2 - rtextwidth, 0)
        self._rtextlabel.move(cx2 - self._rtextlabel.bbox()[2] - 5, 0)

        midx = (stackx + cx2 - max(rtextwidth, rlabelwidth)) / 2
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)
        (x1, y1, x2, y2) = self._stacklabel.bbox()

        # Set up binding to allow them to shift a token by dragging it.
        if len(self._rtextwidgets) > 0:

            def drag_shift(widget, midx=midx, self=self):
                if widget.bbox()[0] < midx:
                    self.shift()
                else:
                    self._redraw()

            self._rtextwidgets[0].bind_drag(drag_shift)
            self._rtextwidgets[0].bind_click(self.shift)

        # Draw the stack top.
        self._highlight_productions()

    def _draw_stack_top(self, widget):
        # hack..
        midx = widget.bbox()[2] + 50
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)

    def _highlight_productions(self):
        # Highlight the productions that can be reduced.
        self._prodlist.selection_clear(0, "end")
        for prod in self._parser.reducible_productions():
            index = self._productions.index(prod)
            self._prodlist.selection_set(index)

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset App"
        self._lastoper2["text"] = ""
        self._redraw()

    def step(self, *e):
        if self.reduce():
            return True
        elif self.shift():
            return True
        else:
            if list(self._parser.parses()):
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Success"
            else:
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Failure"

    def shift(self, *e):
        if self._animating_lock:
            return
        if self._parser.shift():
            tok = self._parser.stack()[-1]
            self._lastoper1["text"] = "Shift:"
            self._lastoper2["text"] = "%r" % tok
            if self._animate.get():
                self._animate_shift()
            else:
                self._redraw()
            return True
        return False

    def reduce(self, *e):
        if self._animating_lock:
            return
        production = self._parser.reduce()
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        return production

    def undo(self, *e):
        if self._animating_lock:
            return
        if self._parser.undo():
            self._redraw()

    def postscript(self, *e):
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    #########################################
    ##  Menubar callbacks
    #########################################

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))

        # self._stacklabel['font'] = ('helvetica', -size-4, 'bold')
        # self._rtextlabel['font'] = ('helvetica', -size-4, 'bold')
        # self._lastoper_label['font'] = ('helvetica', -size)
        # self._lastoper1['font'] = ('helvetica', -size)
        # self._lastoper2['font'] = ('helvetica', -size)
        # self._prodlist['font'] = ('helvetica', -size)
        # self._prodlist_label['font'] = ('helvetica', -size-2, 'bold')
        self._redraw()

    def help(self, *e):
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Shift-Reduce Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Shift-Reduce Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sent):
        self._sent = sent.split()  # [XX] use tagged?
        self.reset()

    #########################################
    ##  Reduce Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        production = self._parser.reduce(self._productions[index])
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.reducible_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    def _popup_reduce(self, widget):
        # Remove old commands.
        productions = self._parser.reducible_productions()
        if len(productions) == 0:
            return

        self._reduce_menu.delete(0, "end")
        for production in productions:
            self._reduce_menu.add_command(label=str(production), command=self.reduce)
        self._reduce_menu.post(
            self._canvas.winfo_pointerx(), self._canvas.winfo_pointery()
        )

    #########################################
    ##  Animations
    #########################################

    def _animate_shift(self):
        # What widget are we shifting?
        widget = self._rtextwidgets[0]

        # Where are we shifting from & to?
        right = widget.bbox()[0]
        if len(self._stackwidgets) == 0:
            left = 5
        else:
            left = self._stackwidgets[-1].bbox()[2] + 10

        # Start animating.
        dt = self._animate.get()
        dx = (left - right) * 1.0 / dt
        self._animate_shift_frame(dt, widget, dx)

    def _animate_shift_frame(self, frame, widget, dx):
        if frame > 0:
            self._animating_lock = 1
            widget.move(dx, 0)
            self._top.after(10, self._animate_shift_frame, frame - 1, widget, dx)
        else:
            # but: stacktop??

            # Shift the widget to the stack.
            del self._rtextwidgets[0]
            self._stackwidgets.append(widget)
            self._animating_lock = 0

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

    def _animate_reduce(self):
        # What widgets are we shifting?
        numwidgets = len(self._parser.stack()[-1])  # number of children
        widgets = self._stackwidgets[-numwidgets:]

        # How far are we moving?
        if isinstance(widgets[0], TreeSegmentWidget):
            ydist = 15 + widgets[0].label().height()
        else:
            ydist = 15 + widgets[0].height()

        # Start animating.
        dt = self._animate.get()
        dy = ydist * 2.0 / dt
        self._animate_reduce_frame(dt / 2, widgets, dy)

    def _animate_reduce_frame(self, frame, widgets, dy):
        if frame > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget.move(0, dy)
            self._top.after(10, self._animate_reduce_frame, frame - 1, widgets, dy)
        else:
            del self._stackwidgets[-len(widgets) :]
            for widget in widgets:
                self._cframe.remove_widget(widget)
            tok = self._parser.stack()[-1]
            if not isinstance(tok, Tree):
                raise ValueError()
            label = TextWidget(
                self._canvas, str(tok.label()), color="#006060", font=self._boldfont
            )
            widget = TreeSegmentWidget(self._canvas, label, widgets, width=2)
            (x1, y1, x2, y2) = self._stacklabel.bbox()
            y = y2 - y1 + 10
            if not self._stackwidgets:
                x = 5
            else:
                x = self._stackwidgets[-1].bbox()[2] + 10
            self._cframe.add_widget(widget, x, y)
            self._stackwidgets.append(widget)

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

            #             # Delete the old widgets..
            #             del self._stackwidgets[-len(widgets):]
            #             for widget in widgets:
            #                 self._cframe.destroy_widget(widget)
            #
            #             # Make a new one.
            #             tok = self._parser.stack()[-1]
            #             if isinstance(tok, Tree):
            #                 attribs = {'tree_color': '#4080a0', 'tree_width': 2,
            #                            'node_font': bold, 'node_color': '#006060',
            #                            'leaf_color': '#006060', 'leaf_font':self._font}
            #                 widget = tree_to_treesegment(self._canvas, tok.type(),
            #                                              **attribs)
            #                 widget.node()['color'] = '#000000'
            #             else:
            #                 widget = TextWidget(self._canvas, tok.type(),
            #                                     color='#000000', font=self._font)
            #             widget.bind_click(self._popup_reduce)
            #             (x1, y1, x2, y2) = self._stacklabel.bbox()
            #             y = y2-y1+10
            #             if not self._stackwidgets: x = 5
            #             else: x = self._stackwidgets[-1].bbox()[2] + 10
            #             self._cframe.add_widget(widget, x, y)
            #             self._stackwidgets.append(widget)

            # self._redraw()
            self._animating_lock = 0

    #########################################
    ##  Hovering.
    #########################################

    def _highlight_hover(self, event):
        # What production are we hovering over?
        index = self._prodlist.nearest(event.y)
        if self._hover == index:
            return

        # Clear any previous hover highlighting.
        self._clear_hover()

        # If the production corresponds to an available reduction,
        # highlight the stack.
        selection = [int(s) for s in self._prodlist.curselection()]
        if index in selection:
            rhslen = len(self._productions[index].rhs())
            for stackwidget in self._stackwidgets[-rhslen:]:
                if isinstance(stackwidget, TreeSegmentWidget):
                    stackwidget.label()["color"] = "#00a000"
                else:
                    stackwidget["color"] = "#00a000"

        # Remember what production we're hovering over.
        self._hover = index

    def _clear_hover(self, *event):
        # Clear any previous hover highlighting.
        if self._hover == -1:
            return
        self._hover = -1
        for stackwidget in self._stackwidgets:
            if isinstance(stackwidget, TreeSegmentWidget):
                stackwidget.label()["color"] = "black"
            else:
                stackwidget["color"] = "black"


def app():
    """
    Create a shift reduce parser app, using a simple grammar and
    text.
    """

    from nltk.grammar import CFG, Nonterminal, Production

    nonterminals = "S VP NP PP P N Name V Det"
    (S, VP, NP, PP, P, N, Name, V, Det) = (Nonterminal(s) for s in nonterminals.split())

    productions = (
        # Syntactic Productions
        Production(S, [NP, VP]),
        Production(NP, [Det, N]),
        Production(NP, [NP, PP]),
        Production(VP, [VP, PP]),
        Production(VP, [V, NP, PP]),
        Production(VP, [V, NP]),
        Production(PP, [P, NP]),
        # Lexical Productions
        Production(NP, ["I"]),
        Production(Det, ["the"]),
        Production(Det, ["a"]),
        Production(N, ["man"]),
        Production(V, ["saw"]),
        Production(P, ["in"]),
        Production(P, ["with"]),
        Production(N, ["park"]),
        Production(N, ["dog"]),
        Production(N, ["statue"]),
        Production(Det, ["my"]),
    )

    grammar = CFG(S, productions)

    # tokenize the sentence
    sent = "my dog saw a man in the park with a statue".split()

    ShiftReduceApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\srparser_app.py ===
# Natural Language Toolkit: Shift-Reduce Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the shift-reduce parser.

The shift-reduce parser maintains a stack, which records the structure
of the portion of the text that has been parsed.  The stack is
initially empty.  Its contents are shown on the left side of the main
canvas.

On the right side of the main canvas is the remaining text.  This is
the portion of the text which has not yet been considered by the
parser.

The parser builds up a tree structure for the text using two
operations:

  - "shift" moves the first token from the remaining text to the top
    of the stack.  In the demo, the top of the stack is its right-hand
    side.
  - "reduce" uses a grammar production to combine the rightmost stack
    elements into a single tree token.

You can control the parser's operation by using the "shift" and
"reduce" buttons; or you can use the "step" button to let the parser
automatically decide which operation to apply.  The parser uses the
following rules to decide which operation to apply:

  - Only shift if no reductions are available.
  - If multiple reductions are available, then apply the reduction
    whose CFG production is listed earliest in the grammar.

The "reduce" button applies the reduction whose CFG production is
listed earliest in the grammar.  There are two ways to manually choose
which reduction to apply:

  - Click on a CFG production from the list of available reductions,
    on the left side of the main window.  The reduction based on that
    production will be applied to the top of the stack.
  - Click on one of the stack elements.  A popup window will appear,
    containing all available reductions.  Select one, and it will be
    applied to the top of the stack.

Note that reductions can only be applied to the top of the stack.

Keyboard Shortcuts::
      [Space]\t Perform the next shift or reduce operation
      [s]\t Perform a shift operation
      [r]\t Perform a reduction operation
      [Ctrl-z]\t Undo most recent operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available production list
      [Ctrl-a]\t Toggle animations
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit

"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingShiftReduceParser
from nltk.tree import Tree
from nltk.util import in_idle

"""
Possible future improvements:
  - button/window to change and/or select text.  Just pop up a window
    with an entry, and let them modify the text; and then retokenize
    it?  Maybe give a warning if it contains tokens whose types are
    not in the grammar.
  - button/window to change and/or select grammar.  Select from
    several alternative grammars?  Or actually change the grammar?  If
    the later, then I'd want to define nltk.draw.cfg, which would be
    responsible for that.
"""


class ShiftReduceApp:
    """
    A graphical tool for exploring the shift-reduce parser.  The tool
    displays the parser's stack and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can shift tokens onto the stack, and can perform reductions on the
    top elements of the stack.  A "step" button simply steps through
    the parsing process, performing the operations that
    ``nltk.parse.ShiftReduceParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingShiftReduceParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Shift Reduce Parser Application")

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animating_lock = 0
        self._animate = IntVar(self._top)
        self._animate.set(10)  # = medium

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Initialize fonts.
        self._init_fonts(self._top)

        # Set up key bindings.
        self._init_bindings()

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # A popup menu for reducing.
        self._reduce_menu = Menu(self._canvas, tearoff=0)

        # Reset the demo, and set the feedback frame to empty.
        self.reset()
        self._lastoper1["text"] = ""

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Reductions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if 1:  # len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

        # When they hover over a production, highlight it.
        self._hover = -1
        self._prodlist.bind("<Motion>", self._highlight_hover)
        self._prodlist.bind("<Leave>", self._clear_hover)

    def _init_bindings(self):
        # Quit
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Alt-q>", self.destroy)
        self._top.bind("<Alt-x>", self.destroy)

        # Ops (step, shift, reduce, undo)
        self._top.bind("<space>", self.step)
        self._top.bind("<s>", self.shift)
        self._top.bind("<Alt-s>", self.shift)
        self._top.bind("<Control-s>", self.shift)
        self._top.bind("<r>", self.reduce)
        self._top.bind("<Alt-r>", self.reduce)
        self._top.bind("<Control-r>", self.reduce)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<u>", self.undo)
        self._top.bind("<Alt-u>", self.undo)
        self._top.bind("<Control-u>", self.undo)
        self._top.bind("<Control-z>", self.undo)
        self._top.bind("<BackSpace>", self.undo)

        # Misc
        self._top.bind("<Control-p>", self.postscript)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._top.bind("-", lambda e, a=self._animate: a.set(20))
        self._top.bind("=", lambda e, a=self._animate: a.set(10))
        self._top.bind("+", lambda e, a=self._animate: a.set(4))

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom")
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Shift",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.shift,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Reduce",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.reduce,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Undo",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.undo,
        ).pack(side="left")

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Shift", underline=0, command=self.shift, accelerator="Ctrl-s"
        )
        rulemenu.add_command(
            label="Reduce", underline=0, command=self.reduce, accelerator="Ctrl-r"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Undo", underline=0, command=self.undo, accelerator="Ctrl-u"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=20,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=10,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=4,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            width=525,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        self._stackwidgets = []
        self._rtextwidgets = []
        self._titlebar = canvas.create_rectangle(
            0, 0, 0, 0, fill="#c0f0f0", outline="black"
        )
        self._exprline = canvas.create_line(0, 0, 0, 0, dash=".")
        self._stacktop = canvas.create_line(0, 0, 0, 0, fill="#408080")
        size = self._size.get() + 4
        self._stacklabel = TextWidget(
            canvas, "Stack", color="#004040", font=self._boldfont
        )
        self._rtextlabel = TextWidget(
            canvas, "Remaining Text", color="#004040", font=self._boldfont
        )
        self._cframe.add_widget(self._stacklabel)
        self._cframe.add_widget(self._rtextlabel)

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        scrollregion = self._canvas["scrollregion"].split()
        (cx1, cy1, cx2, cy2) = (int(c) for c in scrollregion)

        # Delete the old stack & rtext widgets.
        for stackwidget in self._stackwidgets:
            self._cframe.destroy_widget(stackwidget)
        self._stackwidgets = []
        for rtextwidget in self._rtextwidgets:
            self._cframe.destroy_widget(rtextwidget)
        self._rtextwidgets = []

        # Position the titlebar & exprline
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        y = y2 - y1 + 10
        self._canvas.coords(self._titlebar, -5000, 0, 5000, y - 4)
        self._canvas.coords(self._exprline, 0, y * 2 - 10, 5000, y * 2 - 10)

        # Position the titlebar labels..
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        self._stacklabel.move(5 - x1, 3 - y1)
        (x1, y1, x2, y2) = self._rtextlabel.bbox()
        self._rtextlabel.move(cx2 - x2 - 5, 3 - y1)

        # Draw the stack.
        stackx = 5
        for tok in self._parser.stack():
            if isinstance(tok, Tree):
                attribs = {
                    "tree_color": "#4080a0",
                    "tree_width": 2,
                    "node_font": self._boldfont,
                    "node_color": "#006060",
                    "leaf_color": "#006060",
                    "leaf_font": self._font,
                }
                widget = tree_to_treesegment(self._canvas, tok, **attribs)
                widget.label()["color"] = "#000000"
            else:
                widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            widget.bind_click(self._popup_reduce)
            self._stackwidgets.append(widget)
            self._cframe.add_widget(widget, stackx, y)
            stackx = widget.bbox()[2] + 10

        # Draw the remaining text.
        rtextwidth = 0
        for tok in self._parser.remaining_text():
            widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            self._rtextwidgets.append(widget)
            self._cframe.add_widget(widget, rtextwidth, y)
            rtextwidth = widget.bbox()[2] + 4

        # Allow enough room to shift the next token (for animations)
        if len(self._rtextwidgets) > 0:
            stackx += self._rtextwidgets[0].width()

        # Move the remaining text to the correct location (keep it
        # right-justified, when possible); and move the remaining text
        # label, if necessary.
        stackx = max(stackx, self._stacklabel.width() + 25)
        rlabelwidth = self._rtextlabel.width() + 10
        if stackx >= cx2 - max(rtextwidth, rlabelwidth):
            cx2 = stackx + max(rtextwidth, rlabelwidth)
        for rtextwidget in self._rtextwidgets:
            rtextwidget.move(4 + cx2 - rtextwidth, 0)
        self._rtextlabel.move(cx2 - self._rtextlabel.bbox()[2] - 5, 0)

        midx = (stackx + cx2 - max(rtextwidth, rlabelwidth)) / 2
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)
        (x1, y1, x2, y2) = self._stacklabel.bbox()

        # Set up binding to allow them to shift a token by dragging it.
        if len(self._rtextwidgets) > 0:

            def drag_shift(widget, midx=midx, self=self):
                if widget.bbox()[0] < midx:
                    self.shift()
                else:
                    self._redraw()

            self._rtextwidgets[0].bind_drag(drag_shift)
            self._rtextwidgets[0].bind_click(self.shift)

        # Draw the stack top.
        self._highlight_productions()

    def _draw_stack_top(self, widget):
        # hack..
        midx = widget.bbox()[2] + 50
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)

    def _highlight_productions(self):
        # Highlight the productions that can be reduced.
        self._prodlist.selection_clear(0, "end")
        for prod in self._parser.reducible_productions():
            index = self._productions.index(prod)
            self._prodlist.selection_set(index)

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset App"
        self._lastoper2["text"] = ""
        self._redraw()

    def step(self, *e):
        if self.reduce():
            return True
        elif self.shift():
            return True
        else:
            if list(self._parser.parses()):
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Success"
            else:
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Failure"

    def shift(self, *e):
        if self._animating_lock:
            return
        if self._parser.shift():
            tok = self._parser.stack()[-1]
            self._lastoper1["text"] = "Shift:"
            self._lastoper2["text"] = "%r" % tok
            if self._animate.get():
                self._animate_shift()
            else:
                self._redraw()
            return True
        return False

    def reduce(self, *e):
        if self._animating_lock:
            return
        production = self._parser.reduce()
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        return production

    def undo(self, *e):
        if self._animating_lock:
            return
        if self._parser.undo():
            self._redraw()

    def postscript(self, *e):
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    #########################################
    ##  Menubar callbacks
    #########################################

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))

        # self._stacklabel['font'] = ('helvetica', -size-4, 'bold')
        # self._rtextlabel['font'] = ('helvetica', -size-4, 'bold')
        # self._lastoper_label['font'] = ('helvetica', -size)
        # self._lastoper1['font'] = ('helvetica', -size)
        # self._lastoper2['font'] = ('helvetica', -size)
        # self._prodlist['font'] = ('helvetica', -size)
        # self._prodlist_label['font'] = ('helvetica', -size-2, 'bold')
        self._redraw()

    def help(self, *e):
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Shift-Reduce Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Shift-Reduce Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sent):
        self._sent = sent.split()  # [XX] use tagged?
        self.reset()

    #########################################
    ##  Reduce Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        production = self._parser.reduce(self._productions[index])
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.reducible_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    def _popup_reduce(self, widget):
        # Remove old commands.
        productions = self._parser.reducible_productions()
        if len(productions) == 0:
            return

        self._reduce_menu.delete(0, "end")
        for production in productions:
            self._reduce_menu.add_command(label=str(production), command=self.reduce)
        self._reduce_menu.post(
            self._canvas.winfo_pointerx(), self._canvas.winfo_pointery()
        )

    #########################################
    ##  Animations
    #########################################

    def _animate_shift(self):
        # What widget are we shifting?
        widget = self._rtextwidgets[0]

        # Where are we shifting from & to?
        right = widget.bbox()[0]
        if len(self._stackwidgets) == 0:
            left = 5
        else:
            left = self._stackwidgets[-1].bbox()[2] + 10

        # Start animating.
        dt = self._animate.get()
        dx = (left - right) * 1.0 / dt
        self._animate_shift_frame(dt, widget, dx)

    def _animate_shift_frame(self, frame, widget, dx):
        if frame > 0:
            self._animating_lock = 1
            widget.move(dx, 0)
            self._top.after(10, self._animate_shift_frame, frame - 1, widget, dx)
        else:
            # but: stacktop??

            # Shift the widget to the stack.
            del self._rtextwidgets[0]
            self._stackwidgets.append(widget)
            self._animating_lock = 0

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

    def _animate_reduce(self):
        # What widgets are we shifting?
        numwidgets = len(self._parser.stack()[-1])  # number of children
        widgets = self._stackwidgets[-numwidgets:]

        # How far are we moving?
        if isinstance(widgets[0], TreeSegmentWidget):
            ydist = 15 + widgets[0].label().height()
        else:
            ydist = 15 + widgets[0].height()

        # Start animating.
        dt = self._animate.get()
        dy = ydist * 2.0 / dt
        self._animate_reduce_frame(dt / 2, widgets, dy)

    def _animate_reduce_frame(self, frame, widgets, dy):
        if frame > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget.move(0, dy)
            self._top.after(10, self._animate_reduce_frame, frame - 1, widgets, dy)
        else:
            del self._stackwidgets[-len(widgets) :]
            for widget in widgets:
                self._cframe.remove_widget(widget)
            tok = self._parser.stack()[-1]
            if not isinstance(tok, Tree):
                raise ValueError()
            label = TextWidget(
                self._canvas, str(tok.label()), color="#006060", font=self._boldfont
            )
            widget = TreeSegmentWidget(self._canvas, label, widgets, width=2)
            (x1, y1, x2, y2) = self._stacklabel.bbox()
            y = y2 - y1 + 10
            if not self._stackwidgets:
                x = 5
            else:
                x = self._stackwidgets[-1].bbox()[2] + 10
            self._cframe.add_widget(widget, x, y)
            self._stackwidgets.append(widget)

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

            #             # Delete the old widgets..
            #             del self._stackwidgets[-len(widgets):]
            #             for widget in widgets:
            #                 self._cframe.destroy_widget(widget)
            #
            #             # Make a new one.
            #             tok = self._parser.stack()[-1]
            #             if isinstance(tok, Tree):
            #                 attribs = {'tree_color': '#4080a0', 'tree_width': 2,
            #                            'node_font': bold, 'node_color': '#006060',
            #                            'leaf_color': '#006060', 'leaf_font':self._font}
            #                 widget = tree_to_treesegment(self._canvas, tok.type(),
            #                                              **attribs)
            #                 widget.node()['color'] = '#000000'
            #             else:
            #                 widget = TextWidget(self._canvas, tok.type(),
            #                                     color='#000000', font=self._font)
            #             widget.bind_click(self._popup_reduce)
            #             (x1, y1, x2, y2) = self._stacklabel.bbox()
            #             y = y2-y1+10
            #             if not self._stackwidgets: x = 5
            #             else: x = self._stackwidgets[-1].bbox()[2] + 10
            #             self._cframe.add_widget(widget, x, y)
            #             self._stackwidgets.append(widget)

            # self._redraw()
            self._animating_lock = 0

    #########################################
    ##  Hovering.
    #########################################

    def _highlight_hover(self, event):
        # What production are we hovering over?
        index = self._prodlist.nearest(event.y)
        if self._hover == index:
            return

        # Clear any previous hover highlighting.
        self._clear_hover()

        # If the production corresponds to an available reduction,
        # highlight the stack.
        selection = [int(s) for s in self._prodlist.curselection()]
        if index in selection:
            rhslen = len(self._productions[index].rhs())
            for stackwidget in self._stackwidgets[-rhslen:]:
                if isinstance(stackwidget, TreeSegmentWidget):
                    stackwidget.label()["color"] = "#00a000"
                else:
                    stackwidget["color"] = "#00a000"

        # Remember what production we're hovering over.
        self._hover = index

    def _clear_hover(self, *event):
        # Clear any previous hover highlighting.
        if self._hover == -1:
            return
        self._hover = -1
        for stackwidget in self._stackwidgets:
            if isinstance(stackwidget, TreeSegmentWidget):
                stackwidget.label()["color"] = "black"
            else:
                stackwidget["color"] = "black"


def app():
    """
    Create a shift reduce parser app, using a simple grammar and
    text.
    """

    from nltk.grammar import CFG, Nonterminal, Production

    nonterminals = "S VP NP PP P N Name V Det"
    (S, VP, NP, PP, P, N, Name, V, Det) = (Nonterminal(s) for s in nonterminals.split())

    productions = (
        # Syntactic Productions
        Production(S, [NP, VP]),
        Production(NP, [Det, N]),
        Production(NP, [NP, PP]),
        Production(VP, [VP, PP]),
        Production(VP, [V, NP, PP]),
        Production(VP, [V, NP]),
        Production(PP, [P, NP]),
        # Lexical Productions
        Production(NP, ["I"]),
        Production(Det, ["the"]),
        Production(Det, ["a"]),
        Production(N, ["man"]),
        Production(V, ["saw"]),
        Production(P, ["in"]),
        Production(P, ["with"]),
        Production(N, ["park"]),
        Production(N, ["dog"]),
        Production(N, ["statue"]),
        Production(Det, ["my"]),
    )

    grammar = CFG(S, productions)

    # tokenize the sentence
    sent = "my dog saw a man in the park with a statue".split()

    ShiftReduceApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\srparser_app.py ===
# Natural Language Toolkit: Shift-Reduce Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the shift-reduce parser.

The shift-reduce parser maintains a stack, which records the structure
of the portion of the text that has been parsed.  The stack is
initially empty.  Its contents are shown on the left side of the main
canvas.

On the right side of the main canvas is the remaining text.  This is
the portion of the text which has not yet been considered by the
parser.

The parser builds up a tree structure for the text using two
operations:

  - "shift" moves the first token from the remaining text to the top
    of the stack.  In the demo, the top of the stack is its right-hand
    side.
  - "reduce" uses a grammar production to combine the rightmost stack
    elements into a single tree token.

You can control the parser's operation by using the "shift" and
"reduce" buttons; or you can use the "step" button to let the parser
automatically decide which operation to apply.  The parser uses the
following rules to decide which operation to apply:

  - Only shift if no reductions are available.
  - If multiple reductions are available, then apply the reduction
    whose CFG production is listed earliest in the grammar.

The "reduce" button applies the reduction whose CFG production is
listed earliest in the grammar.  There are two ways to manually choose
which reduction to apply:

  - Click on a CFG production from the list of available reductions,
    on the left side of the main window.  The reduction based on that
    production will be applied to the top of the stack.
  - Click on one of the stack elements.  A popup window will appear,
    containing all available reductions.  Select one, and it will be
    applied to the top of the stack.

Note that reductions can only be applied to the top of the stack.

Keyboard Shortcuts::
      [Space]\t Perform the next shift or reduce operation
      [s]\t Perform a shift operation
      [r]\t Perform a reduction operation
      [Ctrl-z]\t Undo most recent operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available production list
      [Ctrl-a]\t Toggle animations
      [h]\t Help
      [Ctrl-p]\t Print
      [q]\t Quit

"""

from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
from tkinter.font import Font

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import CanvasFrame, EntryDialog, ShowText, TextWidget
from nltk.parse import SteppingShiftReduceParser
from nltk.tree import Tree
from nltk.util import in_idle

"""
Possible future improvements:
  - button/window to change and/or select text.  Just pop up a window
    with an entry, and let them modify the text; and then retokenize
    it?  Maybe give a warning if it contains tokens whose types are
    not in the grammar.
  - button/window to change and/or select grammar.  Select from
    several alternative grammars?  Or actually change the grammar?  If
    the later, then I'd want to define nltk.draw.cfg, which would be
    responsible for that.
"""


class ShiftReduceApp:
    """
    A graphical tool for exploring the shift-reduce parser.  The tool
    displays the parser's stack and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can shift tokens onto the stack, and can perform reductions on the
    top elements of the stack.  A "step" button simply steps through
    the parsing process, performing the operations that
    ``nltk.parse.ShiftReduceParser`` would use.
    """

    def __init__(self, grammar, sent, trace=0):
        self._sent = sent
        self._parser = SteppingShiftReduceParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title("Shift Reduce Parser Application")

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animating_lock = 0
        self._animate = IntVar(self._top)
        self._animate.set(10)  # = medium

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Initialize fonts.
        self._init_fonts(self._top)

        # Set up key bindings.
        self._init_bindings()

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # A popup menu for reducing.
        self._reduce_menu = Menu(self._canvas, tearoff=0)

        # Reset the demo, and set the feedback frame to empty.
        self.reset()
        self._lastoper1["text"] = ""

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_grammar(self, parent):
        # Grammar view.
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill="both", side="left", padx=2)
        self._prodlist_label = Label(
            self._prodframe, font=self._boldfont, text="Available Reductions"
        )
        self._prodlist_label.pack()
        self._prodlist = Listbox(
            self._prodframe,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._prodlist.pack(side="right", fill="both", expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if 1:  # len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe, orient="vertical")
            self._prodlist.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a production, apply it.
        self._prodlist.bind("<<ListboxSelect>>", self._prodlist_select)

        # When they hover over a production, highlight it.
        self._hover = -1
        self._prodlist.bind("<Motion>", self._highlight_hover)
        self._prodlist.bind("<Leave>", self._clear_hover)

    def _init_bindings(self):
        # Quit
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Alt-q>", self.destroy)
        self._top.bind("<Alt-x>", self.destroy)

        # Ops (step, shift, reduce, undo)
        self._top.bind("<space>", self.step)
        self._top.bind("<s>", self.shift)
        self._top.bind("<Alt-s>", self.shift)
        self._top.bind("<Control-s>", self.shift)
        self._top.bind("<r>", self.reduce)
        self._top.bind("<Alt-r>", self.reduce)
        self._top.bind("<Control-r>", self.reduce)
        self._top.bind("<Delete>", self.reset)
        self._top.bind("<u>", self.undo)
        self._top.bind("<Alt-u>", self.undo)
        self._top.bind("<Control-u>", self.undo)
        self._top.bind("<Control-z>", self.undo)
        self._top.bind("<BackSpace>", self.undo)

        # Misc
        self._top.bind("<Control-p>", self.postscript)
        self._top.bind("<Control-h>", self.help)
        self._top.bind("<F1>", self.help)
        self._top.bind("<Control-g>", self.edit_grammar)
        self._top.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._top.bind("-", lambda e, a=self._animate: a.set(20))
        self._top.bind("=", lambda e, a=self._animate: a.set(10))
        self._top.bind("+", lambda e, a=self._animate: a.set(4))

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom")
        Button(
            buttonframe,
            text="Step",
            background="#90c0d0",
            foreground="black",
            command=self.step,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Shift",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.shift,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Reduce",
            underline=0,
            background="#90f090",
            foreground="black",
            command=self.reduce,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Undo",
            underline=0,
            background="#f0a0a0",
            foreground="black",
            command=self.undo,
        ).pack(side="left")

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Reset Parser", underline=0, command=self.reset, accelerator="Del"
        )
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.postscript,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Step", underline=1, command=self.step, accelerator="Space"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Shift", underline=0, command=self.shift, accelerator="Ctrl-s"
        )
        rulemenu.add_command(
            label="Reduce", underline=0, command=self.reduce, accelerator="Ctrl-r"
        )
        rulemenu.add_separator()
        rulemenu.add_command(
            label="Undo", underline=0, command=self.undo, accelerator="Ctrl-u"
        )
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_checkbutton(
            label="Show Grammar",
            underline=0,
            variable=self._show_grammar,
            command=self._toggle_grammar,
        )
        viewmenu.add_separator()
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=20,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=10,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=4,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill="x", side="bottom", padx=3, pady=3)
        self._lastoper_label = Label(
            feedbackframe, text="Last Operation:", font=self._font
        )
        self._lastoper_label.pack(side="left")
        lastoperframe = Frame(feedbackframe, relief="sunken", border=1)
        lastoperframe.pack(fill="x", side="right", expand=1, padx=5)
        self._lastoper1 = Label(
            lastoperframe, foreground="#007070", background="#f0f0f0", font=self._font
        )
        self._lastoper2 = Label(
            lastoperframe,
            anchor="w",
            width=30,
            foreground="#004040",
            background="#f0f0f0",
            font=self._font,
        )
        self._lastoper1.pack(side="left")
        self._lastoper2.pack(side="left", fill="x", expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            width=525,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        self._stackwidgets = []
        self._rtextwidgets = []
        self._titlebar = canvas.create_rectangle(
            0, 0, 0, 0, fill="#c0f0f0", outline="black"
        )
        self._exprline = canvas.create_line(0, 0, 0, 0, dash=".")
        self._stacktop = canvas.create_line(0, 0, 0, 0, fill="#408080")
        size = self._size.get() + 4
        self._stacklabel = TextWidget(
            canvas, "Stack", color="#004040", font=self._boldfont
        )
        self._rtextlabel = TextWidget(
            canvas, "Remaining Text", color="#004040", font=self._boldfont
        )
        self._cframe.add_widget(self._stacklabel)
        self._cframe.add_widget(self._rtextlabel)

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        scrollregion = self._canvas["scrollregion"].split()
        (cx1, cy1, cx2, cy2) = (int(c) for c in scrollregion)

        # Delete the old stack & rtext widgets.
        for stackwidget in self._stackwidgets:
            self._cframe.destroy_widget(stackwidget)
        self._stackwidgets = []
        for rtextwidget in self._rtextwidgets:
            self._cframe.destroy_widget(rtextwidget)
        self._rtextwidgets = []

        # Position the titlebar & exprline
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        y = y2 - y1 + 10
        self._canvas.coords(self._titlebar, -5000, 0, 5000, y - 4)
        self._canvas.coords(self._exprline, 0, y * 2 - 10, 5000, y * 2 - 10)

        # Position the titlebar labels..
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        self._stacklabel.move(5 - x1, 3 - y1)
        (x1, y1, x2, y2) = self._rtextlabel.bbox()
        self._rtextlabel.move(cx2 - x2 - 5, 3 - y1)

        # Draw the stack.
        stackx = 5
        for tok in self._parser.stack():
            if isinstance(tok, Tree):
                attribs = {
                    "tree_color": "#4080a0",
                    "tree_width": 2,
                    "node_font": self._boldfont,
                    "node_color": "#006060",
                    "leaf_color": "#006060",
                    "leaf_font": self._font,
                }
                widget = tree_to_treesegment(self._canvas, tok, **attribs)
                widget.label()["color"] = "#000000"
            else:
                widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            widget.bind_click(self._popup_reduce)
            self._stackwidgets.append(widget)
            self._cframe.add_widget(widget, stackx, y)
            stackx = widget.bbox()[2] + 10

        # Draw the remaining text.
        rtextwidth = 0
        for tok in self._parser.remaining_text():
            widget = TextWidget(self._canvas, tok, color="#000000", font=self._font)
            self._rtextwidgets.append(widget)
            self._cframe.add_widget(widget, rtextwidth, y)
            rtextwidth = widget.bbox()[2] + 4

        # Allow enough room to shift the next token (for animations)
        if len(self._rtextwidgets) > 0:
            stackx += self._rtextwidgets[0].width()

        # Move the remaining text to the correct location (keep it
        # right-justified, when possible); and move the remaining text
        # label, if necessary.
        stackx = max(stackx, self._stacklabel.width() + 25)
        rlabelwidth = self._rtextlabel.width() + 10
        if stackx >= cx2 - max(rtextwidth, rlabelwidth):
            cx2 = stackx + max(rtextwidth, rlabelwidth)
        for rtextwidget in self._rtextwidgets:
            rtextwidget.move(4 + cx2 - rtextwidth, 0)
        self._rtextlabel.move(cx2 - self._rtextlabel.bbox()[2] - 5, 0)

        midx = (stackx + cx2 - max(rtextwidth, rlabelwidth)) / 2
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)
        (x1, y1, x2, y2) = self._stacklabel.bbox()

        # Set up binding to allow them to shift a token by dragging it.
        if len(self._rtextwidgets) > 0:

            def drag_shift(widget, midx=midx, self=self):
                if widget.bbox()[0] < midx:
                    self.shift()
                else:
                    self._redraw()

            self._rtextwidgets[0].bind_drag(drag_shift)
            self._rtextwidgets[0].bind_click(self.shift)

        # Draw the stack top.
        self._highlight_productions()

    def _draw_stack_top(self, widget):
        # hack..
        midx = widget.bbox()[2] + 50
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)

    def _highlight_productions(self):
        # Highlight the productions that can be reduced.
        self._prodlist.selection_clear(0, "end")
        for prod in self._parser.reducible_productions():
            index = self._productions.index(prod)
            self._prodlist.selection_set(index)

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._parser.initialize(self._sent)
        self._lastoper1["text"] = "Reset App"
        self._lastoper2["text"] = ""
        self._redraw()

    def step(self, *e):
        if self.reduce():
            return True
        elif self.shift():
            return True
        else:
            if list(self._parser.parses()):
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Success"
            else:
                self._lastoper1["text"] = "Finished:"
                self._lastoper2["text"] = "Failure"

    def shift(self, *e):
        if self._animating_lock:
            return
        if self._parser.shift():
            tok = self._parser.stack()[-1]
            self._lastoper1["text"] = "Shift:"
            self._lastoper2["text"] = "%r" % tok
            if self._animate.get():
                self._animate_shift()
            else:
                self._redraw()
            return True
        return False

    def reduce(self, *e):
        if self._animating_lock:
            return
        production = self._parser.reduce()
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        return production

    def undo(self, *e):
        if self._animating_lock:
            return
        if self._parser.undo():
            self._redraw()

    def postscript(self, *e):
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    #########################################
    ##  Menubar callbacks
    #########################################

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))

        # self._stacklabel['font'] = ('helvetica', -size-4, 'bold')
        # self._rtextlabel['font'] = ('helvetica', -size-4, 'bold')
        # self._lastoper_label['font'] = ('helvetica', -size)
        # self._lastoper1['font'] = ('helvetica', -size)
        # self._lastoper2['font'] = ('helvetica', -size)
        # self._prodlist['font'] = ('helvetica', -size)
        # self._prodlist_label['font'] = ('helvetica', -size-2, 'bold')
        self._redraw()

    def help(self, *e):
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._top,
                "Help: Shift-Reduce Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Shift-Reduce Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Shift-Reduce Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def edit_grammar(self, *e):
        CFGEditor(self._top, self._parser.grammar(), self.set_grammar)

    def set_grammar(self, grammar):
        self._parser.set_grammar(grammar)
        self._productions = list(grammar.productions())
        self._prodlist.delete(0, "end")
        for production in self._productions:
            self._prodlist.insert("end", (" %s" % production))

    def edit_sentence(self, *e):
        sentence = " ".join(self._sent)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._top, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sent):
        self._sent = sent.split()  # [XX] use tagged?
        self.reset()

    #########################################
    ##  Reduce Production Selection
    #########################################

    def _toggle_grammar(self, *e):
        if self._show_grammar.get():
            self._prodframe.pack(
                fill="both", side="left", padx=2, after=self._feedbackframe
            )
            self._lastoper1["text"] = "Show Grammar"
        else:
            self._prodframe.pack_forget()
            self._lastoper1["text"] = "Hide Grammar"
        self._lastoper2["text"] = ""

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1:
            return
        index = int(selection[0])
        production = self._parser.reduce(self._productions[index])
        if production:
            self._lastoper1["text"] = "Reduce:"
            self._lastoper2["text"] = "%s" % production
            if self._animate.get():
                self._animate_reduce()
            else:
                self._redraw()
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, "end")
            for prod in self._parser.reducible_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    def _popup_reduce(self, widget):
        # Remove old commands.
        productions = self._parser.reducible_productions()
        if len(productions) == 0:
            return

        self._reduce_menu.delete(0, "end")
        for production in productions:
            self._reduce_menu.add_command(label=str(production), command=self.reduce)
        self._reduce_menu.post(
            self._canvas.winfo_pointerx(), self._canvas.winfo_pointery()
        )

    #########################################
    ##  Animations
    #########################################

    def _animate_shift(self):
        # What widget are we shifting?
        widget = self._rtextwidgets[0]

        # Where are we shifting from & to?
        right = widget.bbox()[0]
        if len(self._stackwidgets) == 0:
            left = 5
        else:
            left = self._stackwidgets[-1].bbox()[2] + 10

        # Start animating.
        dt = self._animate.get()
        dx = (left - right) * 1.0 / dt
        self._animate_shift_frame(dt, widget, dx)

    def _animate_shift_frame(self, frame, widget, dx):
        if frame > 0:
            self._animating_lock = 1
            widget.move(dx, 0)
            self._top.after(10, self._animate_shift_frame, frame - 1, widget, dx)
        else:
            # but: stacktop??

            # Shift the widget to the stack.
            del self._rtextwidgets[0]
            self._stackwidgets.append(widget)
            self._animating_lock = 0

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

    def _animate_reduce(self):
        # What widgets are we shifting?
        numwidgets = len(self._parser.stack()[-1])  # number of children
        widgets = self._stackwidgets[-numwidgets:]

        # How far are we moving?
        if isinstance(widgets[0], TreeSegmentWidget):
            ydist = 15 + widgets[0].label().height()
        else:
            ydist = 15 + widgets[0].height()

        # Start animating.
        dt = self._animate.get()
        dy = ydist * 2.0 / dt
        self._animate_reduce_frame(dt / 2, widgets, dy)

    def _animate_reduce_frame(self, frame, widgets, dy):
        if frame > 0:
            self._animating_lock = 1
            for widget in widgets:
                widget.move(0, dy)
            self._top.after(10, self._animate_reduce_frame, frame - 1, widgets, dy)
        else:
            del self._stackwidgets[-len(widgets) :]
            for widget in widgets:
                self._cframe.remove_widget(widget)
            tok = self._parser.stack()[-1]
            if not isinstance(tok, Tree):
                raise ValueError()
            label = TextWidget(
                self._canvas, str(tok.label()), color="#006060", font=self._boldfont
            )
            widget = TreeSegmentWidget(self._canvas, label, widgets, width=2)
            (x1, y1, x2, y2) = self._stacklabel.bbox()
            y = y2 - y1 + 10
            if not self._stackwidgets:
                x = 5
            else:
                x = self._stackwidgets[-1].bbox()[2] + 10
            self._cframe.add_widget(widget, x, y)
            self._stackwidgets.append(widget)

            # Display the available productions.
            self._draw_stack_top(widget)
            self._highlight_productions()

            #             # Delete the old widgets..
            #             del self._stackwidgets[-len(widgets):]
            #             for widget in widgets:
            #                 self._cframe.destroy_widget(widget)
            #
            #             # Make a new one.
            #             tok = self._parser.stack()[-1]
            #             if isinstance(tok, Tree):
            #                 attribs = {'tree_color': '#4080a0', 'tree_width': 2,
            #                            'node_font': bold, 'node_color': '#006060',
            #                            'leaf_color': '#006060', 'leaf_font':self._font}
            #                 widget = tree_to_treesegment(self._canvas, tok.type(),
            #                                              **attribs)
            #                 widget.node()['color'] = '#000000'
            #             else:
            #                 widget = TextWidget(self._canvas, tok.type(),
            #                                     color='#000000', font=self._font)
            #             widget.bind_click(self._popup_reduce)
            #             (x1, y1, x2, y2) = self._stacklabel.bbox()
            #             y = y2-y1+10
            #             if not self._stackwidgets: x = 5
            #             else: x = self._stackwidgets[-1].bbox()[2] + 10
            #             self._cframe.add_widget(widget, x, y)
            #             self._stackwidgets.append(widget)

            # self._redraw()
            self._animating_lock = 0

    #########################################
    ##  Hovering.
    #########################################

    def _highlight_hover(self, event):
        # What production are we hovering over?
        index = self._prodlist.nearest(event.y)
        if self._hover == index:
            return

        # Clear any previous hover highlighting.
        self._clear_hover()

        # If the production corresponds to an available reduction,
        # highlight the stack.
        selection = [int(s) for s in self._prodlist.curselection()]
        if index in selection:
            rhslen = len(self._productions[index].rhs())
            for stackwidget in self._stackwidgets[-rhslen:]:
                if isinstance(stackwidget, TreeSegmentWidget):
                    stackwidget.label()["color"] = "#00a000"
                else:
                    stackwidget["color"] = "#00a000"

        # Remember what production we're hovering over.
        self._hover = index

    def _clear_hover(self, *event):
        # Clear any previous hover highlighting.
        if self._hover == -1:
            return
        self._hover = -1
        for stackwidget in self._stackwidgets:
            if isinstance(stackwidget, TreeSegmentWidget):
                stackwidget.label()["color"] = "black"
            else:
                stackwidget["color"] = "black"


def app():
    """
    Create a shift reduce parser app, using a simple grammar and
    text.
    """

    from nltk.grammar import CFG, Nonterminal, Production

    nonterminals = "S VP NP PP P N Name V Det"
    (S, VP, NP, PP, P, N, Name, V, Det) = (Nonterminal(s) for s in nonterminals.split())

    productions = (
        # Syntactic Productions
        Production(S, [NP, VP]),
        Production(NP, [Det, N]),
        Production(NP, [NP, PP]),
        Production(VP, [VP, PP]),
        Production(VP, [V, NP, PP]),
        Production(VP, [V, NP]),
        Production(PP, [P, NP]),
        # Lexical Productions
        Production(NP, ["I"]),
        Production(Det, ["the"]),
        Production(Det, ["a"]),
        Production(N, ["man"]),
        Production(V, ["saw"]),
        Production(P, ["in"]),
        Production(P, ["with"]),
        Production(N, ["park"]),
        Production(N, ["dog"]),
        Production(N, ["statue"]),
        Production(Det, ["my"]),
    )

    grammar = CFG(S, productions)

    # tokenize the sentence
    sent = "my dog saw a man in the park with a statue".split()

    ShiftReduceApp(grammar, sent).mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]