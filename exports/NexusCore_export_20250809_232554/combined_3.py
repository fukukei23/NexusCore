
# === NexusCore/openenv\Lib\site-packages\nltk\app\concordance_app.py ===
# Natural Language Toolkit: Concordance Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import queue as q
import re
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Entry,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.draw.util import ShowText
from nltk.util import in_idle

WORD_OR_TAG = "[^/ ]+"
BOUNDARY = r"\b"

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
SEARCH_TERMINATED_EVENT = "<<ST_EVENT>>"
SEARCH_ERROR_EVENT = "<<SE_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"

POLL_INTERVAL = 50

# NB All corpora must be specified in a lambda expression so as not to be
# loaded when the module is imported.

_DEFAULT = "English: Brown Corpus (Humor, simplified)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus (simplified)": lambda: cess_cat.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus": lambda: brown.tagged_sents(),
    "English: Brown Corpus (simplified)": lambda: brown.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus (Press, simplified)": lambda: brown.tagged_sents(
        categories=["news", "editorial", "reviews"], tagset="universal"
    ),
    "English: Brown Corpus (Religion, simplified)": lambda: brown.tagged_sents(
        categories="religion", tagset="universal"
    ),
    "English: Brown Corpus (Learned, simplified)": lambda: brown.tagged_sents(
        categories="learned", tagset="universal"
    ),
    "English: Brown Corpus (Science Fiction, simplified)": lambda: brown.tagged_sents(
        categories="science_fiction", tagset="universal"
    ),
    "English: Brown Corpus (Romance, simplified)": lambda: brown.tagged_sents(
        categories="romance", tagset="universal"
    ),
    "English: Brown Corpus (Humor, simplified)": lambda: brown.tagged_sents(
        categories="humor", tagset="universal"
    ),
    "English: NPS Chat Corpus": lambda: nps_chat.tagged_posts(),
    "English: NPS Chat Corpus (simplified)": lambda: nps_chat.tagged_posts(
        tagset="universal"
    ),
    "English: Wall Street Journal Corpus": lambda: treebank.tagged_sents(),
    "English: Wall Street Journal Corpus (simplified)": lambda: treebank.tagged_sents(
        tagset="universal"
    ),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.tagged_sents(),
    "Chinese: Sinica Corpus (simplified)": lambda: sinica_treebank.tagged_sents(
        tagset="universal"
    ),
    "Dutch: Alpino Corpus": lambda: alpino.tagged_sents(),
    "Dutch: Alpino Corpus (simplified)": lambda: alpino.tagged_sents(
        tagset="universal"
    ),
    "Hindi: Indian Languages Corpus": lambda: indian.tagged_sents(files="hindi.pos"),
    "Hindi: Indian Languages Corpus (simplified)": lambda: indian.tagged_sents(
        files="hindi.pos", tagset="universal"
    ),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.tagged_sents(),
    "Portuguese: Floresta Corpus (Portugal, simplified)": lambda: floresta.tagged_sents(
        tagset="universal"
    ),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.tagged_sents(),
    "Portuguese: MAC-MORPHO Corpus (Brazil, simplified)": lambda: mac_morpho.tagged_sents(
        tagset="universal"
    ),
    "Spanish: CESS-ESP Corpus (simplified)": lambda: cess_esp.tagged_sents(
        tagset="universal"
    ),
}


class ConcordanceSearchView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    # Colour of highlighted results
    _HIGHLIGHT_WORD_COLOUR = "#F00"  # red
    _HIGHLIGHT_WORD_TAG = "HL_WRD_TAG"

    _HIGHLIGHT_LABEL_COLOUR = "#C0C0C0"  # dark grey
    _HIGHLIGHT_LABEL_TAG = "HL_LBL_TAG"

    # Percentage of text left of the scrollbar position
    _FRACTION_LEFT_TEXT = 0.30

    def __init__(self):
        self.queue = q.Queue()
        self.model = ConcordanceSearchModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("950x680+50+50")
        top.title("NLTK Concordance Search")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(950, 680)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        self._cntx_bf_len = IntVar(self.top)
        self._cntx_af_len = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        cntxmenu = Menu(editmenu, tearoff=0)
        cntxbfmenu = Menu(cntxmenu, tearoff=0)
        cntxbfmenu.add_radiobutton(
            label="60 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=60,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="80 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=80,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="100 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=100,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.invoke(1)
        cntxmenu.add_cascade(label="Before", underline=0, menu=cntxbfmenu)

        cntxafmenu = Menu(cntxmenu, tearoff=0)
        cntxafmenu.add_radiobutton(
            label="70 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=70,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="90 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=90,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="110 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=110,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.invoke(1)
        cntxmenu.add_cascade(label="After", underline=0, menu=cntxafmenu)

        editmenu.add_cascade(label="Context", underline=0, menu=cntxmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def set_cntx_af_len(self, **kwargs):
        self._char_after = self._cntx_af_len.get()

    def set_cntx_bf_len(self, **kwargs):
        self._char_before = self._cntx_bf_len.get()

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_query_box(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        another = Frame(innerframe, background=self._BACKGROUND_COLOUR)
        self.query_box = Entry(another, width=60)
        self.query_box.pack(side="left", fill="x", pady=25, anchor="center")
        self.search_button = Button(
            another,
            text="Search",
            command=self.search,
            borderwidth=1,
            highlightthickness=1,
        )
        self.search_button.pack(side="left", fill="x", pady=25, anchor="center")
        self.query_box.bind("<KeyPress-Return>", self.search_enter_keypress_handler)
        another.pack()
        innerframe.pack(side="top", fill="x", anchor="n")

    def search_enter_keypress_handler(self, *event):
        self.search()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        self.results_box.tag_config(
            self._HIGHLIGHT_WORD_TAG, foreground=self._HIGHLIGHT_WORD_COLOUR
        )
        self.results_box.tag_config(
            self._HIGHLIGHT_LABEL_TAG, foreground=self._HIGHLIGHT_LABEL_COLOUR
        )
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.current_page = 0

    def previous(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.prev(self.current_page - 1)

    def __next__(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.next(self.current_page + 1)

    def about(self, *e):
        ABOUT = "NLTK Concordance Search Demo\n"
        TITLE = "About: NLTK Concordance Search Demo"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE, parent=self.main_frame).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def _bind_event_handlers(self):
        self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
        self.top.bind(SEARCH_TERMINATED_EVENT, self.handle_search_terminated)
        self.top.bind(SEARCH_ERROR_EVENT, self.handle_search_error)
        self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == SEARCH_TERMINATED_EVENT:
                self.handle_search_terminated(event)
            elif event == SEARCH_ERROR_EVENT:
                self.handle_search_error(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_all()
        self.freeze_editable()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_all()
        self.query_box.focus_set()

    def handle_search_terminated(self, event):
        # todo: refactor the model such that it is less state sensitive
        results = self.model.get_results()
        self.write_results(results)
        self.status["text"] = ""
        if len(results) == 0:
            self.status["text"] = "No results found for " + self.model.query
        else:
            self.current_page = self.model.last_requested_page
        self.unfreeze_editable()
        self.results_box.xview_moveto(self._FRACTION_LEFT_TEXT)

    def handle_search_error(self, event):
        self.status["text"] = "Error in query " + self.model.query
        self.unfreeze_editable()

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def search(self):
        self.current_page = 0
        self.clear_results_box()
        self.model.reset_results()
        query = self.query_box.get()
        if len(query.strip()) == 0:
            return
        self.status["text"] = "Searching for " + query
        self.freeze_editable()
        self.model.search(query, self.current_page + 1)

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            sent, pos1, pos2 = each[0].strip(), each[1], each[2]
            if len(sent) != 0:
                if pos1 < self._char_before:
                    sent, pos1, pos2 = self.pad(sent, pos1, pos2)
                sentence = sent[pos1 - self._char_before : pos1 + self._char_after]
                if not row == len(results):
                    sentence += "\n"
                self.results_box.insert(str(row) + ".0", sentence)
                word_markers, label_markers = self.words_and_labels(sent, pos1, pos2)
                for marker in word_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_WORD_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                for marker in label_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_LABEL_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                row += 1
        self.results_box["state"] = "disabled"

    def words_and_labels(self, sentence, pos1, pos2):
        search_exp = sentence[pos1:pos2]
        words, labels = [], []
        labeled_words = search_exp.split(" ")
        index = 0
        for each in labeled_words:
            if each == "":
                index += 1
            else:
                word, label = each.split("/")
                words.append(
                    (self._char_before + index, self._char_before + index + len(word))
                )
                index += len(word) + 1
                labels.append(
                    (self._char_before + index, self._char_before + index + len(label))
                )
                index += len(label)
            index += 1
        return words, labels

    def pad(self, sent, hstart, hend):
        if hstart >= self._char_before:
            return sent, hstart, hend
        d = self._char_before - hstart
        sent = "".join([" "] * d) + sent
        return sent, hstart + d, hend + d

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def clear_all(self):
        self.query_box.delete(0, END)
        self.model.reset_query()
        self.clear_results_box()

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def freeze_editable(self):
        self.query_box["state"] = "disabled"
        self.search_button["state"] = "disabled"
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def unfreeze_editable(self):
        self.query_box["state"] = "normal"
        self.search_button["state"] = "normal"
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == 0 or self.current_page == 1:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.has_more_pages(self.current_page):
            self.next["state"] = "normal"
        else:
            self.next["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


class ConcordanceSearchModel:
    def __init__(self, queue):
        self.queue = queue
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.selected_corpus = None
        self.reset_query()
        self.reset_results()
        self.result_count = None
        self.last_sent_searched = 0

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def load_corpus(self, name):
        self.selected_corpus = name
        self.tagged_sents = []
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()

    def search(self, query, page):
        self.query = query
        self.last_requested_page = page
        self.SearchCorpus(self, page, self.result_count).start()

    def next(self, page):
        self.last_requested_page = page
        if len(self.results) < page:
            self.search(self.query, page)
        else:
            self.queue.put(SEARCH_TERMINATED_EVENT)

    def prev(self, page):
        self.last_requested_page = page
        self.queue.put(SEARCH_TERMINATED_EVENT)

    def reset_results(self):
        self.last_sent_searched = 0
        self.results = []
        self.last_page = None

    def reset_query(self):
        self.query = None

    def set_results(self, page, resultset):
        self.results.insert(page - 1, resultset)

    def get_results(self):
        return self.results[self.last_requested_page - 1]

    def has_more_pages(self, page):
        if self.results == [] or self.results[0] == []:
            return False
        if self.last_page is None:
            return True
        return page < self.last_page

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                ts = self.model.CORPORA[self.name]()
                self.model.tagged_sents = [
                    " ".join(w + "/" + t for (w, t) in sent) for sent in ts
                ]
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)

    class SearchCorpus(threading.Thread):
        def __init__(self, model, page, count):
            self.model, self.count, self.page = model, count, page
            threading.Thread.__init__(self)

        def run(self):
            q = self.processed_query()
            sent_pos, i, sent_count = [], 0, 0
            for sent in self.model.tagged_sents[self.model.last_sent_searched :]:
                try:
                    m = re.search(q, sent)
                except re.error:
                    self.model.reset_results()
                    self.model.queue.put(SEARCH_ERROR_EVENT)
                    return
                if m:
                    sent_pos.append((sent, m.start(), m.end()))
                    i += 1
                    if i > self.count:
                        self.model.last_sent_searched += sent_count - 1
                        break
                sent_count += 1
            if self.count >= len(sent_pos):
                self.model.last_sent_searched += sent_count - 1
                self.model.last_page = self.page
                self.model.set_results(self.page, sent_pos)
            else:
                self.model.set_results(self.page, sent_pos[:-1])
            self.model.queue.put(SEARCH_TERMINATED_EVENT)

        def processed_query(self):
            new = []
            for term in self.model.query.split():
                term = re.sub(r"\.", r"[^/ ]", term)
                if re.match("[A-Z]+$", term):
                    new.append(BOUNDARY + WORD_OR_TAG + "/" + term + BOUNDARY)
                elif "/" in term:
                    new.append(BOUNDARY + term + BOUNDARY)
                else:
                    new.append(BOUNDARY + term + "/" + WORD_OR_TAG + BOUNDARY)
            return " ".join(new)


def app():
    d = ConcordanceSearchView()
    d.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\concordance_app.py ===
# Natural Language Toolkit: Concordance Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import queue as q
import re
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Entry,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.draw.util import ShowText
from nltk.util import in_idle

WORD_OR_TAG = "[^/ ]+"
BOUNDARY = r"\b"

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
SEARCH_TERMINATED_EVENT = "<<ST_EVENT>>"
SEARCH_ERROR_EVENT = "<<SE_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"

POLL_INTERVAL = 50

# NB All corpora must be specified in a lambda expression so as not to be
# loaded when the module is imported.

_DEFAULT = "English: Brown Corpus (Humor, simplified)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus (simplified)": lambda: cess_cat.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus": lambda: brown.tagged_sents(),
    "English: Brown Corpus (simplified)": lambda: brown.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus (Press, simplified)": lambda: brown.tagged_sents(
        categories=["news", "editorial", "reviews"], tagset="universal"
    ),
    "English: Brown Corpus (Religion, simplified)": lambda: brown.tagged_sents(
        categories="religion", tagset="universal"
    ),
    "English: Brown Corpus (Learned, simplified)": lambda: brown.tagged_sents(
        categories="learned", tagset="universal"
    ),
    "English: Brown Corpus (Science Fiction, simplified)": lambda: brown.tagged_sents(
        categories="science_fiction", tagset="universal"
    ),
    "English: Brown Corpus (Romance, simplified)": lambda: brown.tagged_sents(
        categories="romance", tagset="universal"
    ),
    "English: Brown Corpus (Humor, simplified)": lambda: brown.tagged_sents(
        categories="humor", tagset="universal"
    ),
    "English: NPS Chat Corpus": lambda: nps_chat.tagged_posts(),
    "English: NPS Chat Corpus (simplified)": lambda: nps_chat.tagged_posts(
        tagset="universal"
    ),
    "English: Wall Street Journal Corpus": lambda: treebank.tagged_sents(),
    "English: Wall Street Journal Corpus (simplified)": lambda: treebank.tagged_sents(
        tagset="universal"
    ),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.tagged_sents(),
    "Chinese: Sinica Corpus (simplified)": lambda: sinica_treebank.tagged_sents(
        tagset="universal"
    ),
    "Dutch: Alpino Corpus": lambda: alpino.tagged_sents(),
    "Dutch: Alpino Corpus (simplified)": lambda: alpino.tagged_sents(
        tagset="universal"
    ),
    "Hindi: Indian Languages Corpus": lambda: indian.tagged_sents(files="hindi.pos"),
    "Hindi: Indian Languages Corpus (simplified)": lambda: indian.tagged_sents(
        files="hindi.pos", tagset="universal"
    ),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.tagged_sents(),
    "Portuguese: Floresta Corpus (Portugal, simplified)": lambda: floresta.tagged_sents(
        tagset="universal"
    ),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.tagged_sents(),
    "Portuguese: MAC-MORPHO Corpus (Brazil, simplified)": lambda: mac_morpho.tagged_sents(
        tagset="universal"
    ),
    "Spanish: CESS-ESP Corpus (simplified)": lambda: cess_esp.tagged_sents(
        tagset="universal"
    ),
}


class ConcordanceSearchView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    # Colour of highlighted results
    _HIGHLIGHT_WORD_COLOUR = "#F00"  # red
    _HIGHLIGHT_WORD_TAG = "HL_WRD_TAG"

    _HIGHLIGHT_LABEL_COLOUR = "#C0C0C0"  # dark grey
    _HIGHLIGHT_LABEL_TAG = "HL_LBL_TAG"

    # Percentage of text left of the scrollbar position
    _FRACTION_LEFT_TEXT = 0.30

    def __init__(self):
        self.queue = q.Queue()
        self.model = ConcordanceSearchModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("950x680+50+50")
        top.title("NLTK Concordance Search")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(950, 680)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        self._cntx_bf_len = IntVar(self.top)
        self._cntx_af_len = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        cntxmenu = Menu(editmenu, tearoff=0)
        cntxbfmenu = Menu(cntxmenu, tearoff=0)
        cntxbfmenu.add_radiobutton(
            label="60 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=60,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="80 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=80,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="100 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=100,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.invoke(1)
        cntxmenu.add_cascade(label="Before", underline=0, menu=cntxbfmenu)

        cntxafmenu = Menu(cntxmenu, tearoff=0)
        cntxafmenu.add_radiobutton(
            label="70 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=70,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="90 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=90,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="110 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=110,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.invoke(1)
        cntxmenu.add_cascade(label="After", underline=0, menu=cntxafmenu)

        editmenu.add_cascade(label="Context", underline=0, menu=cntxmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def set_cntx_af_len(self, **kwargs):
        self._char_after = self._cntx_af_len.get()

    def set_cntx_bf_len(self, **kwargs):
        self._char_before = self._cntx_bf_len.get()

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_query_box(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        another = Frame(innerframe, background=self._BACKGROUND_COLOUR)
        self.query_box = Entry(another, width=60)
        self.query_box.pack(side="left", fill="x", pady=25, anchor="center")
        self.search_button = Button(
            another,
            text="Search",
            command=self.search,
            borderwidth=1,
            highlightthickness=1,
        )
        self.search_button.pack(side="left", fill="x", pady=25, anchor="center")
        self.query_box.bind("<KeyPress-Return>", self.search_enter_keypress_handler)
        another.pack()
        innerframe.pack(side="top", fill="x", anchor="n")

    def search_enter_keypress_handler(self, *event):
        self.search()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        self.results_box.tag_config(
            self._HIGHLIGHT_WORD_TAG, foreground=self._HIGHLIGHT_WORD_COLOUR
        )
        self.results_box.tag_config(
            self._HIGHLIGHT_LABEL_TAG, foreground=self._HIGHLIGHT_LABEL_COLOUR
        )
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.current_page = 0

    def previous(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.prev(self.current_page - 1)

    def __next__(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.next(self.current_page + 1)

    def about(self, *e):
        ABOUT = "NLTK Concordance Search Demo\n"
        TITLE = "About: NLTK Concordance Search Demo"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE, parent=self.main_frame).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def _bind_event_handlers(self):
        self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
        self.top.bind(SEARCH_TERMINATED_EVENT, self.handle_search_terminated)
        self.top.bind(SEARCH_ERROR_EVENT, self.handle_search_error)
        self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == SEARCH_TERMINATED_EVENT:
                self.handle_search_terminated(event)
            elif event == SEARCH_ERROR_EVENT:
                self.handle_search_error(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_all()
        self.freeze_editable()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_all()
        self.query_box.focus_set()

    def handle_search_terminated(self, event):
        # todo: refactor the model such that it is less state sensitive
        results = self.model.get_results()
        self.write_results(results)
        self.status["text"] = ""
        if len(results) == 0:
            self.status["text"] = "No results found for " + self.model.query
        else:
            self.current_page = self.model.last_requested_page
        self.unfreeze_editable()
        self.results_box.xview_moveto(self._FRACTION_LEFT_TEXT)

    def handle_search_error(self, event):
        self.status["text"] = "Error in query " + self.model.query
        self.unfreeze_editable()

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def search(self):
        self.current_page = 0
        self.clear_results_box()
        self.model.reset_results()
        query = self.query_box.get()
        if len(query.strip()) == 0:
            return
        self.status["text"] = "Searching for " + query
        self.freeze_editable()
        self.model.search(query, self.current_page + 1)

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            sent, pos1, pos2 = each[0].strip(), each[1], each[2]
            if len(sent) != 0:
                if pos1 < self._char_before:
                    sent, pos1, pos2 = self.pad(sent, pos1, pos2)
                sentence = sent[pos1 - self._char_before : pos1 + self._char_after]
                if not row == len(results):
                    sentence += "\n"
                self.results_box.insert(str(row) + ".0", sentence)
                word_markers, label_markers = self.words_and_labels(sent, pos1, pos2)
                for marker in word_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_WORD_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                for marker in label_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_LABEL_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                row += 1
        self.results_box["state"] = "disabled"

    def words_and_labels(self, sentence, pos1, pos2):
        search_exp = sentence[pos1:pos2]
        words, labels = [], []
        labeled_words = search_exp.split(" ")
        index = 0
        for each in labeled_words:
            if each == "":
                index += 1
            else:
                word, label = each.split("/")
                words.append(
                    (self._char_before + index, self._char_before + index + len(word))
                )
                index += len(word) + 1
                labels.append(
                    (self._char_before + index, self._char_before + index + len(label))
                )
                index += len(label)
            index += 1
        return words, labels

    def pad(self, sent, hstart, hend):
        if hstart >= self._char_before:
            return sent, hstart, hend
        d = self._char_before - hstart
        sent = "".join([" "] * d) + sent
        return sent, hstart + d, hend + d

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def clear_all(self):
        self.query_box.delete(0, END)
        self.model.reset_query()
        self.clear_results_box()

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def freeze_editable(self):
        self.query_box["state"] = "disabled"
        self.search_button["state"] = "disabled"
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def unfreeze_editable(self):
        self.query_box["state"] = "normal"
        self.search_button["state"] = "normal"
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == 0 or self.current_page == 1:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.has_more_pages(self.current_page):
            self.next["state"] = "normal"
        else:
            self.next["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


class ConcordanceSearchModel:
    def __init__(self, queue):
        self.queue = queue
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.selected_corpus = None
        self.reset_query()
        self.reset_results()
        self.result_count = None
        self.last_sent_searched = 0

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def load_corpus(self, name):
        self.selected_corpus = name
        self.tagged_sents = []
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()

    def search(self, query, page):
        self.query = query
        self.last_requested_page = page
        self.SearchCorpus(self, page, self.result_count).start()

    def next(self, page):
        self.last_requested_page = page
        if len(self.results) < page:
            self.search(self.query, page)
        else:
            self.queue.put(SEARCH_TERMINATED_EVENT)

    def prev(self, page):
        self.last_requested_page = page
        self.queue.put(SEARCH_TERMINATED_EVENT)

    def reset_results(self):
        self.last_sent_searched = 0
        self.results = []
        self.last_page = None

    def reset_query(self):
        self.query = None

    def set_results(self, page, resultset):
        self.results.insert(page - 1, resultset)

    def get_results(self):
        return self.results[self.last_requested_page - 1]

    def has_more_pages(self, page):
        if self.results == [] or self.results[0] == []:
            return False
        if self.last_page is None:
            return True
        return page < self.last_page

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                ts = self.model.CORPORA[self.name]()
                self.model.tagged_sents = [
                    " ".join(w + "/" + t for (w, t) in sent) for sent in ts
                ]
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)

    class SearchCorpus(threading.Thread):
        def __init__(self, model, page, count):
            self.model, self.count, self.page = model, count, page
            threading.Thread.__init__(self)

        def run(self):
            q = self.processed_query()
            sent_pos, i, sent_count = [], 0, 0
            for sent in self.model.tagged_sents[self.model.last_sent_searched :]:
                try:
                    m = re.search(q, sent)
                except re.error:
                    self.model.reset_results()
                    self.model.queue.put(SEARCH_ERROR_EVENT)
                    return
                if m:
                    sent_pos.append((sent, m.start(), m.end()))
                    i += 1
                    if i > self.count:
                        self.model.last_sent_searched += sent_count - 1
                        break
                sent_count += 1
            if self.count >= len(sent_pos):
                self.model.last_sent_searched += sent_count - 1
                self.model.last_page = self.page
                self.model.set_results(self.page, sent_pos)
            else:
                self.model.set_results(self.page, sent_pos[:-1])
            self.model.queue.put(SEARCH_TERMINATED_EVENT)

        def processed_query(self):
            new = []
            for term in self.model.query.split():
                term = re.sub(r"\.", r"[^/ ]", term)
                if re.match("[A-Z]+$", term):
                    new.append(BOUNDARY + WORD_OR_TAG + "/" + term + BOUNDARY)
                elif "/" in term:
                    new.append(BOUNDARY + term + BOUNDARY)
                else:
                    new.append(BOUNDARY + term + "/" + WORD_OR_TAG + BOUNDARY)
            return " ".join(new)


def app():
    d = ConcordanceSearchView()
    d.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\concordance_app.py ===
# Natural Language Toolkit: Concordance Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import queue as q
import re
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Entry,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.draw.util import ShowText
from nltk.util import in_idle

WORD_OR_TAG = "[^/ ]+"
BOUNDARY = r"\b"

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
SEARCH_TERMINATED_EVENT = "<<ST_EVENT>>"
SEARCH_ERROR_EVENT = "<<SE_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"

POLL_INTERVAL = 50

# NB All corpora must be specified in a lambda expression so as not to be
# loaded when the module is imported.

_DEFAULT = "English: Brown Corpus (Humor, simplified)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus (simplified)": lambda: cess_cat.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus": lambda: brown.tagged_sents(),
    "English: Brown Corpus (simplified)": lambda: brown.tagged_sents(
        tagset="universal"
    ),
    "English: Brown Corpus (Press, simplified)": lambda: brown.tagged_sents(
        categories=["news", "editorial", "reviews"], tagset="universal"
    ),
    "English: Brown Corpus (Religion, simplified)": lambda: brown.tagged_sents(
        categories="religion", tagset="universal"
    ),
    "English: Brown Corpus (Learned, simplified)": lambda: brown.tagged_sents(
        categories="learned", tagset="universal"
    ),
    "English: Brown Corpus (Science Fiction, simplified)": lambda: brown.tagged_sents(
        categories="science_fiction", tagset="universal"
    ),
    "English: Brown Corpus (Romance, simplified)": lambda: brown.tagged_sents(
        categories="romance", tagset="universal"
    ),
    "English: Brown Corpus (Humor, simplified)": lambda: brown.tagged_sents(
        categories="humor", tagset="universal"
    ),
    "English: NPS Chat Corpus": lambda: nps_chat.tagged_posts(),
    "English: NPS Chat Corpus (simplified)": lambda: nps_chat.tagged_posts(
        tagset="universal"
    ),
    "English: Wall Street Journal Corpus": lambda: treebank.tagged_sents(),
    "English: Wall Street Journal Corpus (simplified)": lambda: treebank.tagged_sents(
        tagset="universal"
    ),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.tagged_sents(),
    "Chinese: Sinica Corpus (simplified)": lambda: sinica_treebank.tagged_sents(
        tagset="universal"
    ),
    "Dutch: Alpino Corpus": lambda: alpino.tagged_sents(),
    "Dutch: Alpino Corpus (simplified)": lambda: alpino.tagged_sents(
        tagset="universal"
    ),
    "Hindi: Indian Languages Corpus": lambda: indian.tagged_sents(files="hindi.pos"),
    "Hindi: Indian Languages Corpus (simplified)": lambda: indian.tagged_sents(
        files="hindi.pos", tagset="universal"
    ),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.tagged_sents(),
    "Portuguese: Floresta Corpus (Portugal, simplified)": lambda: floresta.tagged_sents(
        tagset="universal"
    ),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.tagged_sents(),
    "Portuguese: MAC-MORPHO Corpus (Brazil, simplified)": lambda: mac_morpho.tagged_sents(
        tagset="universal"
    ),
    "Spanish: CESS-ESP Corpus (simplified)": lambda: cess_esp.tagged_sents(
        tagset="universal"
    ),
}


class ConcordanceSearchView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    # Colour of highlighted results
    _HIGHLIGHT_WORD_COLOUR = "#F00"  # red
    _HIGHLIGHT_WORD_TAG = "HL_WRD_TAG"

    _HIGHLIGHT_LABEL_COLOUR = "#C0C0C0"  # dark grey
    _HIGHLIGHT_LABEL_TAG = "HL_LBL_TAG"

    # Percentage of text left of the scrollbar position
    _FRACTION_LEFT_TEXT = 0.30

    def __init__(self):
        self.queue = q.Queue()
        self.model = ConcordanceSearchModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("950x680+50+50")
        top.title("NLTK Concordance Search")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(950, 680)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        self._cntx_bf_len = IntVar(self.top)
        self._cntx_af_len = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        cntxmenu = Menu(editmenu, tearoff=0)
        cntxbfmenu = Menu(cntxmenu, tearoff=0)
        cntxbfmenu.add_radiobutton(
            label="60 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=60,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="80 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=80,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.add_radiobutton(
            label="100 characters",
            variable=self._cntx_bf_len,
            underline=0,
            value=100,
            command=self.set_cntx_bf_len,
        )
        cntxbfmenu.invoke(1)
        cntxmenu.add_cascade(label="Before", underline=0, menu=cntxbfmenu)

        cntxafmenu = Menu(cntxmenu, tearoff=0)
        cntxafmenu.add_radiobutton(
            label="70 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=70,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="90 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=90,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.add_radiobutton(
            label="110 characters",
            variable=self._cntx_af_len,
            underline=0,
            value=110,
            command=self.set_cntx_af_len,
        )
        cntxafmenu.invoke(1)
        cntxmenu.add_cascade(label="After", underline=0, menu=cntxafmenu)

        editmenu.add_cascade(label="Context", underline=0, menu=cntxmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def set_cntx_af_len(self, **kwargs):
        self._char_after = self._cntx_af_len.get()

    def set_cntx_bf_len(self, **kwargs):
        self._char_before = self._cntx_bf_len.get()

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_query_box(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        another = Frame(innerframe, background=self._BACKGROUND_COLOUR)
        self.query_box = Entry(another, width=60)
        self.query_box.pack(side="left", fill="x", pady=25, anchor="center")
        self.search_button = Button(
            another,
            text="Search",
            command=self.search,
            borderwidth=1,
            highlightthickness=1,
        )
        self.search_button.pack(side="left", fill="x", pady=25, anchor="center")
        self.query_box.bind("<KeyPress-Return>", self.search_enter_keypress_handler)
        another.pack()
        innerframe.pack(side="top", fill="x", anchor="n")

    def search_enter_keypress_handler(self, *event):
        self.search()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        self.results_box.tag_config(
            self._HIGHLIGHT_WORD_TAG, foreground=self._HIGHLIGHT_WORD_COLOUR
        )
        self.results_box.tag_config(
            self._HIGHLIGHT_LABEL_TAG, foreground=self._HIGHLIGHT_LABEL_COLOUR
        )
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.current_page = 0

    def previous(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.prev(self.current_page - 1)

    def __next__(self):
        self.clear_results_box()
        self.freeze_editable()
        self.model.next(self.current_page + 1)

    def about(self, *e):
        ABOUT = "NLTK Concordance Search Demo\n"
        TITLE = "About: NLTK Concordance Search Demo"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE, parent=self.main_frame).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def _bind_event_handlers(self):
        self.top.bind(CORPUS_LOADED_EVENT, self.handle_corpus_loaded)
        self.top.bind(SEARCH_TERMINATED_EVENT, self.handle_search_terminated)
        self.top.bind(SEARCH_ERROR_EVENT, self.handle_search_error)
        self.top.bind(ERROR_LOADING_CORPUS_EVENT, self.handle_error_loading_corpus)

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == SEARCH_TERMINATED_EVENT:
                self.handle_search_terminated(event)
            elif event == SEARCH_ERROR_EVENT:
                self.handle_search_error(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_all()
        self.freeze_editable()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_all()
        self.query_box.focus_set()

    def handle_search_terminated(self, event):
        # todo: refactor the model such that it is less state sensitive
        results = self.model.get_results()
        self.write_results(results)
        self.status["text"] = ""
        if len(results) == 0:
            self.status["text"] = "No results found for " + self.model.query
        else:
            self.current_page = self.model.last_requested_page
        self.unfreeze_editable()
        self.results_box.xview_moveto(self._FRACTION_LEFT_TEXT)

    def handle_search_error(self, event):
        self.status["text"] = "Error in query " + self.model.query
        self.unfreeze_editable()

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def search(self):
        self.current_page = 0
        self.clear_results_box()
        self.model.reset_results()
        query = self.query_box.get()
        if len(query.strip()) == 0:
            return
        self.status["text"] = "Searching for " + query
        self.freeze_editable()
        self.model.search(query, self.current_page + 1)

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            sent, pos1, pos2 = each[0].strip(), each[1], each[2]
            if len(sent) != 0:
                if pos1 < self._char_before:
                    sent, pos1, pos2 = self.pad(sent, pos1, pos2)
                sentence = sent[pos1 - self._char_before : pos1 + self._char_after]
                if not row == len(results):
                    sentence += "\n"
                self.results_box.insert(str(row) + ".0", sentence)
                word_markers, label_markers = self.words_and_labels(sent, pos1, pos2)
                for marker in word_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_WORD_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                for marker in label_markers:
                    self.results_box.tag_add(
                        self._HIGHLIGHT_LABEL_TAG,
                        str(row) + "." + str(marker[0]),
                        str(row) + "." + str(marker[1]),
                    )
                row += 1
        self.results_box["state"] = "disabled"

    def words_and_labels(self, sentence, pos1, pos2):
        search_exp = sentence[pos1:pos2]
        words, labels = [], []
        labeled_words = search_exp.split(" ")
        index = 0
        for each in labeled_words:
            if each == "":
                index += 1
            else:
                word, label = each.split("/")
                words.append(
                    (self._char_before + index, self._char_before + index + len(word))
                )
                index += len(word) + 1
                labels.append(
                    (self._char_before + index, self._char_before + index + len(label))
                )
                index += len(label)
            index += 1
        return words, labels

    def pad(self, sent, hstart, hend):
        if hstart >= self._char_before:
            return sent, hstart, hend
        d = self._char_before - hstart
        sent = "".join([" "] * d) + sent
        return sent, hstart + d, hend + d

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def clear_all(self):
        self.query_box.delete(0, END)
        self.model.reset_query()
        self.clear_results_box()

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def freeze_editable(self):
        self.query_box["state"] = "disabled"
        self.search_button["state"] = "disabled"
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def unfreeze_editable(self):
        self.query_box["state"] = "normal"
        self.search_button["state"] = "normal"
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == 0 or self.current_page == 1:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.has_more_pages(self.current_page):
            self.next["state"] = "normal"
        else:
            self.next["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


class ConcordanceSearchModel:
    def __init__(self, queue):
        self.queue = queue
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.selected_corpus = None
        self.reset_query()
        self.reset_results()
        self.result_count = None
        self.last_sent_searched = 0

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def load_corpus(self, name):
        self.selected_corpus = name
        self.tagged_sents = []
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()

    def search(self, query, page):
        self.query = query
        self.last_requested_page = page
        self.SearchCorpus(self, page, self.result_count).start()

    def next(self, page):
        self.last_requested_page = page
        if len(self.results) < page:
            self.search(self.query, page)
        else:
            self.queue.put(SEARCH_TERMINATED_EVENT)

    def prev(self, page):
        self.last_requested_page = page
        self.queue.put(SEARCH_TERMINATED_EVENT)

    def reset_results(self):
        self.last_sent_searched = 0
        self.results = []
        self.last_page = None

    def reset_query(self):
        self.query = None

    def set_results(self, page, resultset):
        self.results.insert(page - 1, resultset)

    def get_results(self):
        return self.results[self.last_requested_page - 1]

    def has_more_pages(self, page):
        if self.results == [] or self.results[0] == []:
            return False
        if self.last_page is None:
            return True
        return page < self.last_page

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                ts = self.model.CORPORA[self.name]()
                self.model.tagged_sents = [
                    " ".join(w + "/" + t for (w, t) in sent) for sent in ts
                ]
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)

    class SearchCorpus(threading.Thread):
        def __init__(self, model, page, count):
            self.model, self.count, self.page = model, count, page
            threading.Thread.__init__(self)

        def run(self):
            q = self.processed_query()
            sent_pos, i, sent_count = [], 0, 0
            for sent in self.model.tagged_sents[self.model.last_sent_searched :]:
                try:
                    m = re.search(q, sent)
                except re.error:
                    self.model.reset_results()
                    self.model.queue.put(SEARCH_ERROR_EVENT)
                    return
                if m:
                    sent_pos.append((sent, m.start(), m.end()))
                    i += 1
                    if i > self.count:
                        self.model.last_sent_searched += sent_count - 1
                        break
                sent_count += 1
            if self.count >= len(sent_pos):
                self.model.last_sent_searched += sent_count - 1
                self.model.last_page = self.page
                self.model.set_results(self.page, sent_pos)
            else:
                self.model.set_results(self.page, sent_pos[:-1])
            self.model.queue.put(SEARCH_TERMINATED_EVENT)

        def processed_query(self):
            new = []
            for term in self.model.query.split():
                term = re.sub(r"\.", r"[^/ ]", term)
                if re.match("[A-Z]+$", term):
                    new.append(BOUNDARY + WORD_OR_TAG + "/" + term + BOUNDARY)
                elif "/" in term:
                    new.append(BOUNDARY + term + BOUNDARY)
                else:
                    new.append(BOUNDARY + term + "/" + WORD_OR_TAG + BOUNDARY)
            return " ".join(new)


def app():
    d = ConcordanceSearchView()
    d.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/src\nexuscore\agents\requirement_agent.py ===
# ==============================================================================
# ファイル: src/nexuscore/agents/requirement_agent.py
# メモ: 完全版（中間仕様ボタン・状態/進捗・編集/再生成・多言語）
# ==============================================================================
import os
import json
import uuid
import gradio as gr
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# --- 安全なインポート ---
try:
    from .base_agent import BaseAgent
except ImportError:
    # スクリプトとして直接実行する場合のフォールバック
    class BaseAgent:
        def __init__(self):
            print("警告: BaseAgentが見つかりません。ダミークラスを使用します。")
        def execute_llm_task(self, prompt, as_json=False):
            print(f"ダミーLLM実行: {prompt[:80]}...")
            if "JSON" in prompt:
                if "松・竹・梅" in prompt:
                    return json.dumps({
                        "proposals": [
                            {"plan_name": "梅プラン（最小構成）", "description": "必要最低限の機能に絞ったプランです。"},
                            {"plan_name": "竹プラン（標準構成）", "description": "基本的な機能を網羅したバランスの取れたプランです。"},
                            {"plan_name": "松プラン（高機能版）", "description": "全ての機能を利用できる最高位のプランです。"}
                        ]
                    })
                # ダミーの仕様書JSONを返す
                return json.dumps({
                    "requirements_specification": {
                        "project_overview": "ダミーのプロジェクト概要",
                        "user_stories": ["ダミーのユーザーストーリー1"],
                    }
                })
            if "HEARING" in prompt or "PROPOSAL" in prompt:
                return "HEARING"
            return "CONTINUE_HEARING"

# --- 定数 ---
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'requirement_sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

SUPPORTED_LANGS = {"ja": "日本語", "en": "English"}

UI_TEXT = {
    "ja": {
        "title": "Requirement Agent - 要求定義セッション",
        "session_id": "セッションID",
        "lang_select": "言語を選択",
        "chat_label": "対話履歴",
        "input_label": "あなたの要求を入力してください",
        "input_ph": "具体的な機能や改善点を自由に入力してください...",
        "send": "送信",
        "finish": "この内容で仕様書を作成",
        "final_spec": "最終要求仕様書",
        "boot_msg": "Gradio UIを起動します。ブラウザで対話を行ってください。",
        "pii_warn": "注意: 入力内容はログに保存されます（PII/機微情報を含めないようご注意ください）。",
        "resume_msg": "以前の続きから始めましょう。ご要望の追加や変更点はありますか？",
        "thanks_and_wait": "ありがとうございます。仕様書を作成しますので、少々お待ちください。",
        "ask_to_type": "何か入力してください。",
        "proposals_intro": "承知いたしました。一般的な構成プランを3つ提案します。どのプランがイメージに近いですか？",
        "hearing_intro": "承知いたしました。では、要求を具体化するためにいくつか質問させてください。",
        "first_ai_done": "ありがとうございます。頂いた情報で要求仕様書を作成しますので、少々お待ちください。",
        "gen_ok": "要求仕様書の生成が完了しました。",
        "gen_fail": "要求仕様書の生成に失敗しました。",
        "log_saved": "対話ログは次のパスに保存されています",
        "draft_intro": "ここまでの内容で中間たたき台を作りました。合っていますか？",
        "choose_one": "以下から選んでください。",
        "yes": "はい",
        "no": "いいえ（修正したい）",
        "ask_for_correction": "承知いたしました。どの部分を修正しますか？具体的に教えてください。",
        "acknowledge_correction": "修正内容を承知いたしました。反映して、再度ヒアリングを続けます。",
        "explain_nfr": "「非機能要件」とは、システムの性能（例：ページの表示速度）、セキュリティ、信頼性など、機能そのものではない品質に関する要求のことです。デフォルト案では、一般的なWebシステムの目標値を設定します。後で個別に調整も可能です。",
        "explain_risk": "「リスク対策テンプレート」とは、不正アクセスやデータ漏洩といった一般的なリスクを想定し、それらに対する基本的な防御策（例：ログイン試行回数制限、IPアドレスによるアクセス制限など）を予め仕様に組み込むことです。",
        "status_label": "状態",
        "progress_label": "進捗",
        "mid_draft_btn": "中間仕様書を作成",
        "edit_switch": "編集モード（JSONを手直し）",
        "apply_edit": "この編集内容を採用（保存）",
        "regen": "AIに再生成させる（編集を反映）",
        "processing": "⏳ 処理中…",
        "draft_label": "中間仕様書（Draft）",
    },
    "en": {
        "title": "Requirement Agent - Requirement Definition Session",
        "session_id": "Session ID",
        "lang_select": "Select Language",
        "chat_label": "Conversation",
        "input_label": "Enter your requirements",
        "input_ph": "Describe desired features or improvements...",
        "send": "Send",
        "finish": "Generate specification",
        "final_spec": "Final Requirements Specification",
        "boot_msg": "Launching Gradio UI. Please continue in your browser.",
        "pii_warn": "Note: Inputs are logged. Avoid entering PII or sensitive data.",
        "resume_msg": "Let's resume where we left off. Any additions or changes?",
        "thanks_and_wait": "Thanks. I will generate the specification now. Please wait a moment.",
        "ask_to_type": "Please type something.",
        "proposals_intro": "Understood. Here are three typical plan options. Which is closest to your image?",
        "hearing_intro": "Understood. Let me ask a few questions to clarify your requirements.",
        "first_ai_done": "Thanks. I have enough information to draft the specification. Please wait a moment.",
        "gen_ok": "Specification generation completed.",
        "gen_fail": "Failed to generate the specification.",
        "log_saved": "Conversation log saved at",
        "draft_intro": "Here is a draft based on your inputs so far. Does this look right?",
        "choose_one": "Please choose one.",
        "yes": "Yes",
        "no": "No (I want to edit)",
        "ask_for_correction": "Understood. Which part would you like to correct? Please be specific.",
        "acknowledge_correction": "Acknowledged your corrections. I will reflect them and continue the hearing.",
        "explain_nfr": "'Non-functional requirements' (NFRs) refer to quality aspects like system performance (e.g., page load speed), security, and reliability, rather than specific features. The default plan sets typical targets for a standard web system, which can be adjusted later.",
        "explain_risk": "The 'risk mitigation template' involves pre-emptively incorporating basic defenses against common risks like unauthorized access or data breaches into the specification, such as limiting login attempts or restricting access by IP address.",
        "status_label": "Status",
        "progress_label": "Progress",
        "mid_draft_btn": "Generate Draft Spec",
        "edit_switch": "Edit mode (tweak JSON)",
        "apply_edit": "Apply this edit (save)",
        "regen": "Regenerate with AI (reflect edits)",
        "processing": "⏳ Processing...",
        "draft_label": "Draft Specification",
    }
}

SYSTEM_PROMPTS = {
    "ja": """あなたは、経験豊富なビジネスアナリスト兼プロダクトマネージャーです。
あなたの役割は、ユーザーの曖昧な要求を聞き出し、対話を通じて
開発チームがすぐに作業に取り掛かれる具体的な「要求仕様書」を完成させることです。
ただ質問するだけでなく、ベストプラクティスに基づいた提案も行い、ユーザーの思考を導いてください。
対話の最終目的は、抜け漏れのない完璧なJSON仕様書を完成させることです。""",
    "en": """You are an experienced business analyst and product manager.
Your role is to elicit ambiguous user needs and, through dialogue,
produce a concrete JSON "requirements specification" that the development team can act on immediately.
Not only ask questions, but also provide best-practice proposals to guide the user.
The ultimate goal is to produce a complete, gap-free JSON specification."""
}

def _ensure_json_obj(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        start_brace = s.find("{")
        start_bracket = s.find("[")
        if start_brace == -1 and start_bracket == -1:
            return value
        starts = [x for x in [start_brace, start_bracket] if x != -1]
        if not starts:
            return value
        start = min(starts)
        end = max(s.rfind("}"), s.rfind("]"))
        if end > start:
            try:
                return json.loads(s[start:end+1])
            except Exception:
                return value
    return value

def _limit_questions(items: List[str], max_q: int = 3) -> List[str]:
    return items[:max_q] if isinstance(items, list) else []

class RequirementAgent(BaseAgent):
    def __init__(self, session_id: Optional[str] = None, language: str = "ja"):
        super().__init__()
        self.set_language(language)

        self.state: str = "INITIALIZING"
        self.conversation_history: List[Dict[str, str]] = []
        self.final_requirements: Optional[Dict] = None
        self.session_id = session_id or (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
        self.session_path: str = os.path.join(SESSIONS_DIR, f"session_{self.session_id}.jsonl")
        self._load_session()
        
        self.slots: Dict[str, Any] = {
            "persona": None,
            "core_features": None,
            "data_acquisition_policy": None,
            "non_functional_defaults": None,
            "risk_policy": None,
        }
        self.turn_counter: int = 0

    def set_language(self, language: str = "ja"):
        if language not in SUPPORTED_LANGS:
            language = "ja"
        self.lang = language
        self.text = UI_TEXT[self.lang]
        self.system_prompt = SYSTEM_PROMPTS[self.lang]

    def _save_log(self, role: str, content: str):
        entry = {"timestamp": datetime.now().isoformat(), "role": role, "content": content}
        with open(self.session_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_session(self):
        if os.path.exists(self.session_path):
            with open(self.session_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        self.conversation_history.append({"role": log_entry["role"], "content": log_entry["content"]})
                    except Exception:
                        continue
            if self.conversation_history:
                self.state = "GATHERING"

    def _determine_next_action(self) -> str:
        # この関数は、次に何をすべきか大まかな方針を決める
        # 全スロットが埋まったら仕様書生成を提案
        if all(v is not None for v in self.slots.values()):
            return "SYNTHESIZE_REQUIREMENTS"
        return "CONTINUE_HEARING"

    def _generate_user_friendly_questions(self) -> str:
        # 未入力のスロットに対する質問を生成する
        missing = [k for k, v in self.slots.items() if v is None]
        order = ["persona", "core_features", "data_acquisition_policy", "non_functional_defaults", "risk_policy"]
        missing_sorted = sorted(missing, key=lambda x: order.index(x) if x in order else len(order))
        
        if not missing_sorted:
            return self.text["first_ai_done"]

        next_slot = missing_sorted[0]
        
        if self.lang == "ja":
            bank = {
                "persona": "まず、このシステムの主な想定ユーザーを教えてください: 1) 個人バイヤー 2) 小規模事業者 3) 企業内担当者 4) その他",
                "core_features": "次に、中心となる機能を3つまで選んでください: [商品収集, 競合分析, レコメンド, メール生成, 価格/在庫トラッキング]",
                "data_acquisition_policy": "ECサイトからのデータ取得頻度や方法に関するポリシーをどうしますか？: 1) 保守的（規約を厳守し、低頻度） 2) 標準（規約に配慮しつつ、適度な頻度） 3) 積極的（高頻度で取得、ただし注意が必要）",
                "non_functional_defaults": "システムの性能やセキュリティなどの非機能要件は、一般的な推奨値（デフォルト案）で開始しますか？ 1) はい 2) いいえ（後で個別に設定）",
                "risk_policy": "一般的なリスク対策（不正ログイン防止など）のテンプレートを適用しますか？ 1) はい 2) いいえ（個別指定）",
            }
        else:
            bank = {
                "persona": "First, who are the primary users of this system?: 1) Individual Buyers 2) Small Businesses 3) Enterprise Users 4) Other",
                "core_features": "Next, pick up to 3 core features: [Product Harvesting, Competitor Analysis, Recommendations, Email Generation, Price/Stock Tracking]",
                "data_acquisition_policy": "What is your policy for data acquisition from e-commerce sites?: 1) Conservative (strict adherence to terms, low frequency) 2) Standard (respectful of terms, moderate frequency) 3) Aggressive (high frequency, requires caution)",
                "non_functional_defaults": "Shall we start with default targets for non-functional requirements like performance and security? 1) Yes 2) No (configure later)",
                "risk_policy": "Should we apply a template for common risk mitigation (e.g., preventing brute-force logins)? 1) Yes 2) No (specify individually)",
            }
        return bank.get(next_slot, self.text["hearing_intro"])

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★ ここからが修正箇所です ★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    def _generate_response(self, user_message: str) -> str:
        """ユーザーの入力に基づいて、文脈に応じた応答を生成する（新ロジック）"""
        
        last_ai_q = self.conversation_history[-2]['content'] if len(self.conversation_history) > 1 else ""
        user_msg_lower = user_message.lower()

        # 状態1: 修正内容の入力を待っている
        if self.state == "AWAITING_CORRECTION":
            self.state = "GATHERING"
            # ユーザーの修正内容を履歴に反映する（ここでは簡略化）
            self.conversation_history.append({"role": "user_correction", "content": user_message})
            return self.text["acknowledge_correction"] + "\n\n" + self._generate_user_friendly_questions()

        # 状態2: 中間仕様書の承認を待っている
        if self.text["draft_intro"] in last_ai_q:
            if "はい" in user_msg_lower or "yes" in user_msg_lower:
                self.state = "GATHERING"
                return self._generate_user_friendly_questions()
            if "いいえ" in user_msg_lower or "no" in user_msg_lower:
                self.state = "AWAITING_CORRECTION"
                return self.text["ask_for_correction"]
        
        # 状態3: 通常のヒアリング中
        # ユーザーが説明を求めてきた場合
        if "どういう意味" in user_message or "what does that mean" in user_msg_lower:
            if "非機能要件" in last_ai_q:
                return self.text["explain_nfr"]
            if "リスク対策" in last_ai_q:
                return self.text["explain_risk"]

        # スロットを埋めるための応答解釈
        self._ingest_user_signal_to_slots(user_message, last_ai_q)
        
        # 次の質問を生成
        return self._generate_user_friendly_questions()

    def process_user_message(self, message: str) -> str:
        if not message or not message.strip():
            return self.text["ask_to_type"]
        
        self.conversation_history.append({"role": "user", "content": message})
        self._save_log("user", message)
        
        if self.state != "AWAITING_CORRECTION":
            self.turn_counter += 1
        
        ai_response = self._generate_response(message)
        
        self.conversation_history.append({"role": "assistant", "content": ai_response})
        self._save_log("assistant", ai_response)
        
        # 特定の応答の場合、状態を変更
        if ai_response == self.text["draft_intro"]:
            self.state = "AWAITING_DRAFT_APPROVAL"
        elif ai_response == self.text["ask_for_correction"]:
             self.state = "AWAITING_CORRECTION"
        else:
             self.state = "GATHERING"
             
        return ai_response

    def _ingest_user_signal_to_slots(self, message: str, last_question: str):
        """最後の質問の文脈を考慮してスロットを埋める"""
        t = message.lower()
        
        # 回答の柔軟な解釈
        is_yes = "はい" in t or "yes" in t or t.strip().startswith("1")
        is_no = "いいえ" in t or "no" in t or t.strip().startswith("2")

        if "想定ユーザー" in last_question or "primary users" in last_question:
            if "個人" in t or "individual" in t: self.slots["persona"] = "individual"
            elif "小規模" in t or "small" in t: self.slots["persona"] = "small_business"
            elif "企業" in t or "enterprise" in t: self.slots["persona"] = "enterprise"
        
        elif "非機能要件" in last_question or "non-functional" in last_question:
            if is_yes: self.slots["non_functional_defaults"] = "default_ok"
            if is_no: self.slots["non_functional_defaults"] = "custom"
        
        elif "リスク対策" in last_question or "risk mitigation" in last_question:
            if is_yes: self.slots["risk_policy"] = "template_on"
            if is_no: self.slots["risk_policy"] = "custom"
        
        # キーワードベースのスロットフィリングも残す
        if "攻め" in t or "aggressive" in t: self.slots["data_acquisition_policy"] = "aggressive"
        
    def generate_intermediate_spec(self) -> Dict:
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        
        prompt = f"""以下の対話履歴から現時点の暫定仕様JSONを{lang_instruction}出力。未確定はTBDで埋め、必須キーは保持。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}"""
        
        try:
            draft = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
            if isinstance(draft, dict) and "requirements_specification" in draft:
                return draft
        except Exception:
            pass
        return {"error": "Draft generation failed."}

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★ 修正箇所はここまでです ★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

    def start_session(self, user_initial_request: str) -> List[Tuple[Optional[str], Optional[str]]]:
        if not self.conversation_history:
            self.state = "GATHERING"
            self.conversation_history.append({"role": "user", "content": user_initial_request})
            self._save_log("user", user_initial_request)
            ai_message = self._generate_user_friendly_questions()
            self.conversation_history.append({"role": "assistant", "content": ai_message})
            self._save_log("assistant", ai_message)
        
        history: List[Tuple[Optional[str], Optional[str]]] = []
        u: Optional[str] = None
        for m in self.conversation_history:
            if m["role"] == "user":
                u = m["content"]
            elif m["role"] == "assistant":
                history.append((u, m["content"]))
                u = None
        return history

    def finalize_session(self) -> Dict:
        self.state = "FINALIZING"
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        prompt = f"""以下の対話履歴に基づき、要求仕様書を{lang_instruction}厳格に出力してください。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}"""
        try:
            final_obj = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
            if not isinstance(final_obj, dict) or "requirements_specification" not in final_obj:
                raise ValueError("Missing 'requirements_specification'")
            self.final_requirements = final_obj
            self._save_log("system", f"spec_generated: {json.dumps(self.final_requirements, ensure_ascii=False)}")
            self.state = "DONE"
            return self.final_requirements
        except Exception as e:
            self.state = "ERROR"
            return {"error": self.text["gen_fail"], "details": str(e)}

    def regenerate_with_hint(self, edit_hint_json_text: str) -> Dict:
        hint = ""
        try:
            obj = json.loads(edit_hint_json_text)
            hint = json.dumps(obj, ensure_ascii=False)
        except Exception:
            pass
        self.state = "FINALIZING"
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        prompt = f"""以下の対話履歴と編集ヒントを踏まえ、仕様JSONを{lang_instruction}再生成。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}
編集ヒント（優先）
{hint}"""
        obj = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
        if isinstance(obj, dict) and "requirements_specification" in obj:
            self.final_requirements = obj
            self.state = "DONE"
            return obj
        self.state = "ERROR"
        return {"error": "Regeneration failed"}

    def launch_ui(self, user_initial_request: str, share: bool = False):
        with gr.Blocks(theme=gr.themes.Soft(), title=self.text["title"]) as demo:
            gr.Markdown(f"# 🤖 {self.text['title']}")
            with gr.Row():
                gr.Markdown(f"**{self.text['session_id']}:** `{self.session_id}`")
                lang_selector = gr.Radio(
                    list(SUPPORTED_LANGS.values()), 
                    value=SUPPORTED_LANGS[self.lang], 
                    label=self.text["lang_select"],
                    interactive=True
                )
            gr.Markdown(f"_{self.text['pii_warn']}_")
            status_bar = gr.Markdown(f"{self.text['status_label']}: INITIALIZING")
            progress = gr.Slider(minimum=0, maximum=100, value=5, step=1, label=self.text["progress_label"], interactive=False)
            spinner = gr.Markdown("")
            
            chatbot = gr.Chatbot(label=self.text["chat_label"], height=460, type="messages")

            with gr.Row():
                msg_input = gr.Textbox(label=self.text["input_label"], placeholder=self.text["input_ph"], scale=4)
                send_button = gr.Button(self.text["send"], variant="primary", scale=1)
            with gr.Row():
                mid_draft_btn = gr.Button(self.text["mid_draft_btn"], variant="secondary")
                finish_button = gr.Button(self.text["finish"], variant="stop")
            draft_output = gr.JSON(label=self.text["draft_label"], visible=False)
            final_output = gr.JSON(label=self.text["final_spec"], visible=False)
            edit_switch = gr.Checkbox(label=self.text["edit_switch"], value=False)
            draft_editor = gr.Code(label="編集用JSON（Draft/Final）", language="json", visible=False, lines=18)
            apply_edited_btn = gr.Button(self.text["apply_edit"], visible=False)
            regen_btn = gr.Button(self.text["regen"], visible=False)

            def on_lang_change(lang_value):
                lang_key = [k for k, v in SUPPORTED_LANGS.items() if v == lang_value][0]
                self.set_language(lang_key)
                # UIのテキストを更新するために、各コンポーネントのupdateを返す
                return {
                    demo: gr.update(title=self.text["title"]),
                    lang_selector: gr.update(label=self.text["lang_select"]),
                    # 他のUI要素も同様に更新
                }

            def reflect_state(custom: Optional[str] = None):
                label = custom or self.state
                user_messages = [m for m in self.conversation_history if m.get("role") == "user"]
                pairs = len(user_messages)
                base = 10 if label == "INITIALIZING" else 20
                prog = max(5, min(100, base + pairs * 12))
                return gr.update(value=f"{self.text['status_label']}: {label}"), gr.update(value=prog)

            def on_ui_load(progress=gr.Progress()):
                progress(0, desc="Initializing")
                history_tuples = self.start_session(user_initial_request)
                message_history = []
                for user, assistant in history_tuples:
                    if user:
                        message_history.append({"role": "user", "content": user})
                    if assistant:
                        message_history.append({"role": "assistant", "content": assistant})

                self.state = "GATHERING"
                st, pg = reflect_state("GATHERING")
                progress(1.0, desc="Ready")
                return message_history, st, pg
            
            def on_user_submit(message, history, progress=gr.Progress()):
                spinner_on = gr.update(value=self.text["processing"])
                st1, pg1 = reflect_state()
                progress(0.2, desc="Parsing input")
                ai_response = self.process_user_message(message)
                progress(0.7, desc="Generating reply")
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": ai_response})
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                progress(1.0, desc="Done")

                if self.text["draft_intro"] in ai_response:
                    progress(0.1, desc="Drafting spec...")
                    draft_spec = self.generate_intermediate_spec()
                    self.state = "AWAITING_DRAFT_APPROVAL"
                    st3, pg3 = reflect_state()
                    progress(1.0, desc="Draft ready")
                    return "", history, st3, pg3, spinner_off, gr.update(value=draft_spec, visible=True)
                
                return "", history, st2, pg2, spinner_off, gr.update(visible=False)

            def on_mid_draft_click(history, progress=gr.Progress()):
                self.state = "SYNTHESIZING"
                st1, pg1 = reflect_state()
                progress(0.3, desc="Drafting")
                draft = self.generate_intermediate_spec()
                progress(0.8, desc="Validating")
                self.state = "AWAITING_DRAFT_APPROVAL"
                st2, pg2 = reflect_state()
                progress(1.0, desc="Draft ready")
                return gr.update(value=draft, visible=True), st2, pg2

            def on_finish_click(history, progress=gr.Progress()):
                self.state = "FINALIZING"
                st1, pg1 = reflect_state()
                spinner_on = gr.update(value=self.text["processing"])
                final_message = self.text["thanks_and_wait"]
                self.conversation_history.append({"role": "assistant", "content": final_message})
                self._save_log("assistant", final_message)
                history.append({"role": "assistant", "content": final_message})
                progress(0.4, desc="Composing spec")
                final_specs = self.finalize_session()
                progress(1.0, desc="Spec ready")
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                return {
                    chatbot: gr.update(value=history),
                    final_output: gr.update(value=final_specs, visible=True),
                    finish_button: gr.update(interactive=False),
                    msg_input: gr.update(interactive=False),
                    send_button: gr.update(interactive=False),
                    status_bar: st2,
                    progress: pg2,
                    spinner: spinner_off
                }

            def on_edit_toggle(flag, draft, final_):
                target = final_ if (isinstance(final_, dict) and final_) else (draft if isinstance(draft, dict) else {})
                editor_value = json.dumps(target, ensure_ascii=False, indent=2) if flag else ""
                return gr.update(visible=flag, value=editor_value), gr.update(visible=flag), gr.update(visible=flag)

            def on_apply_edit(code_text):
                try:
                    obj = json.loads(code_text)
                    if isinstance(obj, dict) and "requirements_specification" in obj:
                        self.final_requirements = obj
                        return gr.update(value=obj, visible=True)
                    return gr.update(value={"error": "Missing 'requirements_specification'"}, visible=True)
                except Exception as e:
                    return gr.update(value={"error": "JSON Parse Error", "details": str(e)}, visible=True)
            
            def on_regen(code_text, progress=gr.Progress()):
                self.state = "FINALIZING"
                st1, pg1 = reflect_state()
                spinner_on = gr.update(value=self.text["processing"])
                progress(0.3, desc="Regenerating")
                obj = self.regenerate_with_hint(code_text)
                progress(1.0, desc="Done")
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                return gr.update(value=obj, visible=True), st2, pg2, spinner_off

            lang_selector.change(on_lang_change, [lang_selector], [demo, lang_selector])
            send_button.click(on_user_submit, [msg_input, chatbot], [msg_input, chatbot, status_bar, progress, spinner, draft_output])
            msg_input.submit(on_user_submit, [msg_input, chatbot], [msg_input, chatbot, status_bar, progress, spinner, draft_output])
            
            mid_draft_btn.click(
                on_mid_draft_click,
                inputs=[chatbot],
                outputs=[draft_output, status_bar, progress]
            )
            
            demo.load(on_ui_load, outputs=[chatbot, status_bar, progress])
            finish_button.click(on_finish_click, inputs=[chatbot], outputs=[chatbot, final_output, finish_button, msg_input, send_button, status_bar, progress, spinner])
            edit_switch.change(on_edit_toggle, [edit_switch, draft_output, final_output], [draft_editor, apply_edited_btn, regen_btn])
            apply_edited_btn.click(on_apply_edit, [draft_editor], [final_output])
            regen_btn.click(on_regen, [draft_editor], [final_output, status_bar, progress, spinner])

        print(self.text["boot_msg"])
        demo.queue().launch(share=share)
        return self.final_requirements or {}

# ----------------- 直接実行 -----------------
if __name__ == "__main__":
    agent = RequirementAgent(language="ja")
    initial_request = "AIで営業メールを自動生成する機能を作りたい。顧客リストをアップロードして、ターゲットごとに内容を少し変えたい。"
    final_specs = agent.launch_ui(initial_request, share=False)

    print("\n" + "="*50)
    print(f"{UI_TEXT[agent.lang]['session_id']}: {agent.session_id}")
    print(UI_TEXT[agent.lang]['log_saved'], agent.session_path)
    print("Final Spec:")
    if final_specs:
        print(json.dumps(final_specs, indent=2, ensure_ascii=False))
    else:
        print("N/A")
    print("="*50)

# === NexusCore/src\nexuscore\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【記憶能力強化版】外部から新しい知識を動的に追加するための
#      `add_knowledge`メソッドを実装。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【信頼性向上・最終版】LLMに不確実なパッチを生成させるのをやめ、
#      「修正後の完全なコード」を生成させるようにプロンプトを変更。
#      受け取ったコードから、Python標準のdifflibを用いて、自ら100%正確な
#      パッチを生成するロジックにアップグレード。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    def add_knowledge(self, new_entry: dict):
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue
                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break
                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        
                        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                        modified_code = self._llm_generate_fixed_code(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if modified_code and original_code != modified_code:
                            patch_str = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"LLM-based fix generated a patch for '{found_target_hint}':\n{patch_str}")
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                        else:
                             self.logger.warning("LLM-based fix did not result in code changes.")
                        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    # ▼▼▼▼▼ メソッド名を変更し、役割を明確化 ▼▼▼▼▼
    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        # ▼▼▼▼▼ プロンプトを「完全なコード」を要求するように変更 ▼▼▼▼▼
        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to provide the complete, fixed version of the source code file.

# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}

# ABSOLUTE OUTPUT RULES
- **Output ONLY the complete and fixed Python code for the file `{source_path_normalized}`.**
- Do NOT include any explanations, apologies, or any text before or after the code block.
- Your output must start with `def` or `import` and be a single, clean block of Python code.
"""
        # ▲▲▲▲▲ プロンプトを「完全なコード」を要求するように変更 ▲▲▲▲▲
        
        fixed_code_raw = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # LLMの出力からコードブロックを抽出する堅牢なロジック
        match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # コードブロックが見つからない場合、出力がそのままコードであると仮定
        return fixed_code_raw.strip()


    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログ、関連するソースコード、そしてテストコードを分析し、
エラーの根本原因を特定して、それを修正するためのunified diff形式のパッチを生成することです。
パッチは正確で、必要最小限の変更に留めてください。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
    def add_knowledge(self, new_entry: dict):
        """新しい知識エントリをメモリ内のFKBに動的に追加する。"""
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")
    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue

                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break

                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        # (このメソッドは変更なし)
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to generate a patch file to fix the bug.
# INSTRUCTION
{instruction}
# FAILED TEST LOG
```
{error_log}
```
# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}
# ANALYSIS & DEBUGGING STRATEGY
1.  Analyze the error log and the source code. The test is failing. This often means the function's output does not match the test's expectation.
2.  Identify the root cause. A very common bug pattern is a function using `print()` to display a result, when the test expects a `return` statement to capture the output.
3.  Formulate the simplest, most correct fix. If the issue is `print` vs `return`, the best fix is to **replace** the `print()` statement with a `return` statement. Do not add a `return` statement while keeping the `print()`. This is a crucial best practice.
4.  Generate the patch. Create a concise, correct patch in the **unified diff format**.
# ABSOLUTE OUTPUT RULES
- **Output ONLY the patch content.**
- Start the patch with `--- {source_path_normalized}` and `+++ {source_path_normalized}`.
- Do NOT include any explanations, apologies, or any text before or after the patch content.
- The output must be a valid unified diff that can be applied by the `patch` command.
- Ensure the patched code is syntactically correct Python.
"""
        patch = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【記憶能力強化版】外部から新しい知識を動的に追加するための
#      `add_knowledge`メソッドを実装。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【信頼性向上・最終版】LLMに不確実なパッチを生成させるのをやめ、
#      「修正後の完全なコード」を生成させるようにプロンプトを変更。
#      受け取ったコードから、Python標準のdifflibを用いて、自ら100%正確な
#      パッチを生成するロジックにアップグレード。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    def add_knowledge(self, new_entry: dict):
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue
                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break
                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        
                        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                        modified_code = self._llm_generate_fixed_code(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if modified_code and original_code != modified_code:
                            patch_str = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"LLM-based fix generated a patch for '{found_target_hint}':\n{patch_str}")
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                        else:
                             self.logger.warning("LLM-based fix did not result in code changes.")
                        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    # ▼▼▼▼▼ メソッド名を変更し、役割を明確化 ▼▼▼▼▼
    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        # ▼▼▼▼▼ プロンプトを「完全なコード」を要求するように変更 ▼▼▼▼▼
        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to provide the complete, fixed version of the source code file.

# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}

# ABSOLUTE OUTPUT RULES
- **Output ONLY the complete and fixed Python code for the file `{source_path_normalized}`.**
- Do NOT include any explanations, apologies, or any text before or after the code block.
- Your output must start with `def` or `import` and be a single, clean block of Python code.
"""
        # ▲▲▲▲▲ プロンプトを「完全なコード」を要求するように変更 ▲▲▲▲▲
        
        fixed_code_raw = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # LLMの出力からコードブロックを抽出する堅牢なロジック
        match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # コードブロックが見つからない場合、出力がそのままコードであると仮定
        return fixed_code_raw.strip()


    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログ、関連するソースコード、そしてテストコードを分析し、
エラーの根本原因を特定して、それを修正するためのunified diff形式のパッチを生成することです。
パッチは正確で、必要最小限の変更に留めてください。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
    def add_knowledge(self, new_entry: dict):
        """新しい知識エントリをメモリ内のFKBに動的に追加する。"""
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")
    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue

                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break

                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        # (このメソッドは変更なし)
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to generate a patch file to fix the bug.
# INSTRUCTION
{instruction}
# FAILED TEST LOG
```
{error_log}
```
# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}
# ANALYSIS & DEBUGGING STRATEGY
1.  Analyze the error log and the source code. The test is failing. This often means the function's output does not match the test's expectation.
2.  Identify the root cause. A very common bug pattern is a function using `print()` to display a result, when the test expects a `return` statement to capture the output.
3.  Formulate the simplest, most correct fix. If the issue is `print` vs `return`, the best fix is to **replace** the `print()` statement with a `return` statement. Do not add a `return` statement while keeping the `print()`. This is a crucial best practice.
4.  Generate the patch. Create a concise, correct patch in the **unified diff format**.
# ABSOLUTE OUTPUT RULES
- **Output ONLY the patch content.**
- Start the patch with `--- {source_path_normalized}` and `+++ {source_path_normalized}`.
- Do NOT include any explanations, apologies, or any text before or after the patch content.
- The output must be a valid unified diff that can be applied by the `patch` command.
- Ensure the patched code is syntactically correct Python.
"""
        patch = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【記憶能力強化版】外部から新しい知識を動的に追加するための
#      `add_knowledge`メソッドを実装。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【信頼性向上・最終版】LLMに不確実なパッチを生成させるのをやめ、
#      「修正後の完全なコード」を生成させるようにプロンプトを変更。
#      受け取ったコードから、Python標準のdifflibを用いて、自ら100%正確な
#      パッチを生成するロジックにアップグレード。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    def add_knowledge(self, new_entry: dict):
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue
                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break
                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        
                        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                        modified_code = self._llm_generate_fixed_code(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if modified_code and original_code != modified_code:
                            patch_str = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"LLM-based fix generated a patch for '{found_target_hint}':\n{patch_str}")
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                        else:
                             self.logger.warning("LLM-based fix did not result in code changes.")
                        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    # ▼▼▼▼▼ メソッド名を変更し、役割を明確化 ▼▼▼▼▼
    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        # ▼▼▼▼▼ プロンプトを「完全なコード」を要求するように変更 ▼▼▼▼▼
        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to provide the complete, fixed version of the source code file.

# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}

# ABSOLUTE OUTPUT RULES
- **Output ONLY the complete and fixed Python code for the file `{source_path_normalized}`.**
- Do NOT include any explanations, apologies, or any text before or after the code block.
- Your output must start with `def` or `import` and be a single, clean block of Python code.
"""
        # ▲▲▲▲▲ プロンプトを「完全なコード」を要求するように変更 ▲▲▲▲▲
        
        fixed_code_raw = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # LLMの出力からコードブロックを抽出する堅牢なロジック
        match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # コードブロックが見つからない場合、出力がそのままコードであると仮定
        return fixed_code_raw.strip()


    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログ、関連するソースコード、そしてテストコードを分析し、
エラーの根本原因を特定して、それを修正するためのunified diff形式のパッチを生成することです。
パッチは正確で、必要最小限の変更に留めてください。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
    def add_knowledge(self, new_entry: dict):
        """新しい知識エントリをメモリ内のFKBに動的に追加する。"""
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")
    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue

                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break

                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        # (このメソッドは変更なし)
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to generate a patch file to fix the bug.
# INSTRUCTION
{instruction}
# FAILED TEST LOG
```
{error_log}
```
# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}
# ANALYSIS & DEBUGGING STRATEGY
1.  Analyze the error log and the source code. The test is failing. This often means the function's output does not match the test's expectation.
2.  Identify the root cause. A very common bug pattern is a function using `print()` to display a result, when the test expects a `return` statement to capture the output.
3.  Formulate the simplest, most correct fix. If the issue is `print` vs `return`, the best fix is to **replace** the `print()` statement with a `return` statement. Do not add a `return` statement while keeping the `print()`. This is a crucial best practice.
4.  Generate the patch. Create a concise, correct patch in the **unified diff format**.
# ABSOLUTE OUTPUT RULES
- **Output ONLY the patch content.**
- Start the patch with `--- {source_path_normalized}` and `+++ {source_path_normalized}`.
- Do NOT include any explanations, apologies, or any text before or after the patch content.
- The output must be a valid unified diff that can be applied by the `patch` command.
- Ensure the patched code is syntactically correct Python.
"""
        patch = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【記憶能力強化版】外部から新しい知識を動的に追加するための
#      `add_knowledge`メソッドを実装。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: 【信頼性向上・最終版】LLMに不確実なパッチを生成させるのをやめ、
#      「修正後の完全なコード」を生成させるようにプロンプトを変更。
#      受け取ったコードから、Python標準のdifflibを用いて、自ら100%正確な
#      パッチを生成するロジックにアップグレード。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from pathlib import Path
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログと関連するソースコードを分析し、
エラーの根本原因を特定して、それを修正した後の完全なソースコードを生成することです。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    def add_knowledge(self, new_entry: dict):
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue
                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break
                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        
                        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                        modified_code = self._llm_generate_fixed_code(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if modified_code and original_code != modified_code:
                            patch_str = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"LLM-based fix generated a patch for '{found_target_hint}':\n{patch_str}")
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                        else:
                             self.logger.warning("LLM-based fix did not result in code changes.")
                        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    # ▼▼▼▼▼ メソッド名を変更し、役割を明確化 ▼▼▼▼▼
    def _llm_generate_fixed_code(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        # ▼▼▼▼▼ プロンプトを「完全なコード」を要求するように変更 ▼▼▼▼▼
        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to provide the complete, fixed version of the source code file.

# INSTRUCTION
{instruction}

# FAILED TEST LOG
```
{error_log}
```

# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}

# ABSOLUTE OUTPUT RULES
- **Output ONLY the complete and fixed Python code for the file `{source_path_normalized}`.**
- Do NOT include any explanations, apologies, or any text before or after the code block.
- Your output must start with `def` or `import` and be a single, clean block of Python code.
"""
        # ▲▲▲▲▲ プロンプトを「完全なコード」を要求するように変更 ▲▲▲▲▲
        
        fixed_code_raw = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        # LLMの出力からコードブロックを抽出する堅牢なロジック
        match = re.search(r"```(?:python\n)?(.*)```", fixed_code_raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # コードブロックが見つからない場合、出力がそのままコードであると仮定
        return fixed_code_raw.strip()


    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

class DebuggerAgent(BaseAgent):
    DEBUG_SYSTEM_PROMPT = """
あなたは、熟練のソフトウェア開発者であり、デバッグの達人です。
あなたの仕事は、失敗したテストのエラーログ、関連するソースコード、そしてテストコードを分析し、
エラーの根本原因を特定して、それを修正するためのunified diff形式のパッチを生成することです。
パッチは正確で、必要最小限の変更に留めてください。
"""

    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json", project_path: str = "."):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.project_path = os.path.abspath(project_path)
        self.fkb = self._load_fkb()
        
        if self.fkb:
            self.logger.info(f"{len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            self.logger.warning(f"EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        try:
            if os.path.isabs(self.knowledge_base_path) and os.path.exists(self.knowledge_base_path):
                config_path = self.knowledge_base_path
            elif os.path.exists(os.path.join(self.project_path, self.knowledge_base_path)):
                 config_path = os.path.join(self.project_path, self.knowledge_base_path)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(base_dir, '..', '..', self.knowledge_base_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load FKB from attempted paths: {e}")
            return []

    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
    def add_knowledge(self, new_entry: dict):
        """新しい知識エントリをメモリ内のFKBに動的に追加する。"""
        if isinstance(new_entry, dict) and "error_signature" in new_entry:
            self.fkb.append(new_entry)
            self.logger.info(f"New knowledge for '{new_entry.get('cause', 'N/A')}' added to in-memory FKB.")
        else:
            self.logger.warning(f"Attempted to add malformed knowledge entry: {new_entry}")
    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        self.logger.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                self.logger.info(f"Found known issue: {entry['cause']}")
                
                raw_target_hints = entry.get("target", "source_file")
                if isinstance(raw_target_hints, str):
                    raw_target_hints = [raw_target_hints] 

                target_hints = []
                for hint in raw_target_hints:
                    target_hints.extend([h.strip() for h in hint.split(',')])

                file_to_read_path = None
                found_target_hint = None
                for hint in target_hints:
                    if not hint: continue

                    path = files_context.get(hint)
                    if path and os.path.exists(path):
                        file_to_read_path = path
                        found_target_hint = hint
                        self.logger.info(f"Found target file '{path}' using symbolic hint '{hint}'.")
                        break

                    if not file_to_read_path:
                        for key, file_path_value in files_context.items():
                            normalized_hint = str(Path(hint)).replace("\\", "/")
                            normalized_path_value = str(Path(file_path_value)).replace("\\", "/")
                            
                            if normalized_hint in normalized_path_value:
                                file_to_read_path = file_path_value
                                found_target_hint = key
                                self.logger.info(f"Found target file '{file_to_read_path}' by matching path hint '{hint}' with key '{key}'.")
                                break
                    
                    if file_to_read_path:
                        break

                if not file_to_read_path:
                    self.logger.error(f"None of the target files for reading were found in context using hints: {target_hints}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    solution = entry["solution_pattern"]
                    
                    if not isinstance(solution, dict):
                        self.logger.warning(f"Malformed solution_pattern in FKB entry for '{entry['cause']}'. Expected a dictionary, but got {type(solution)}. Skipping this solution.")
                        continue

                    if solution.get("type") == "llm_diagnose_and_fix":
                        self.logger.info("Attempting LLM-based diagnosis and fix...")
                        other_files_context = {k: v for k, v in files_context.items() if k != found_target_hint}
                        patch_str = self._llm_generate_patch(error_log, original_code, file_to_read_path, solution["instruction"], other_files_context)
                        if patch_str:
                            return {"patch": patch_str, "target": found_target_hint, "entry": entry}
                    else:
                        modified_code = self._apply_solution_pattern(original_code, solution)
                        if modified_code and original_code != modified_code:
                            diff = self._create_diff(original_code, modified_code, file_to_read_path)
                            self.logger.info(f"Generated patch for '{found_target_hint}':\n{diff}")
                            return {"patch": diff, "target": found_target_hint, "entry": entry}
                        else:
                            self.logger.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    self.logger.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                return None

        self.logger.warning("No known solution found in FKB for this error.")
        return None

    def _llm_generate_patch(self, error_log: str, source_code: str, source_path: str, instruction: str, other_files: dict) -> str | None:
        # (このメソッドは変更なし)
        context_str = ""
        source_path_rel = os.path.relpath(source_path, self.project_path)
        source_path_normalized = Path(source_path_rel).as_posix()
        
        for name, path in other_files.items():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(path, self.project_path)
                context_str += f"\n\n--- Context File: {name} ({Path(rel_path).as_posix()}) ---\n```python\n{content}\n```"
            except Exception:
                pass

        prompt = f"""
# CONTEXT
You are an expert developer debugging a failed test. Your task is to generate a patch file to fix the bug.
# INSTRUCTION
{instruction}
# FAILED TEST LOG
```
{error_log}
```
# SOURCE CODE TO FIX: {source_path_normalized}
```python
{source_code}
```
{context_str}
# ANALYSIS & DEBUGGING STRATEGY
1.  Analyze the error log and the source code. The test is failing. This often means the function's output does not match the test's expectation.
2.  Identify the root cause. A very common bug pattern is a function using `print()` to display a result, when the test expects a `return` statement to capture the output.
3.  Formulate the simplest, most correct fix. If the issue is `print` vs `return`, the best fix is to **replace** the `print()` statement with a `return` statement. Do not add a `return` statement while keeping the `print()`. This is a crucial best practice.
4.  Generate the patch. Create a concise, correct patch in the **unified diff format**.
# ABSOLUTE OUTPUT RULES
- **Output ONLY the patch content.**
- Start the patch with `--- {source_path_normalized}` and `+++ {source_path_normalized}`.
- Do NOT include any explanations, apologies, or any text before or after the patch content.
- The output must be a valid unified diff that can be applied by the `patch` command.
- Ensure the patched code is syntactically correct Python.
"""
        patch = self._call_llm(prompt, self.DEBUG_SYSTEM_PROMPT)
        
        if "```" in patch:
            match = re.search(r"```(?:diff\n)?((?:.|\n)*?)```", patch, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
                patch = patch_content + "\n"
        
        if patch and patch.startswith("---") and "+++" in patch and "@@" in patch:
            self.logger.info(f"LLM generated a valid-looking patch:\n{patch}")
            return patch
            
        self.logger.warning(f"LLM did not generate a valid patch. Output:\n{patch}")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        # (このメソッドは変更なし)
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        elif solution_type == "regex_replace_with_import":
            import_statement = solution["import_statement"]
            modified_code = code
            if not re.search(fr"^\s*import\s+{re.escape(import_statement.split(' ')[1])}", code, re.MULTILINE):
                 if import_statement not in modified_code:
                    modified_code = f"{import_statement}\n{modified_code}"
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, modified_code, flags=re.DOTALL)
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        # (このメソッドは変更なし)
        rel_path = os.path.relpath(filename, self.project_path)
        filename_for_diff = Path(rel_path).as_posix()
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename_for_diff,
            tofile=filename_for_diff,
        )
        return "".join(diff)

# === NexusCore/openenv\Lib\site-packages\nltk\app\collocations_app.py ===
# Natural Language Toolkit: Collocations Application
# Much of the GUI code is imported from concordance.py; We intend to merge these tools together
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#


import queue as q
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    machado,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.probability import FreqDist
from nltk.util import in_idle

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"
POLL_INTERVAL = 100

_DEFAULT = "English: Brown Corpus (Humor)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus": lambda: cess_cat.words(),
    "English: Brown Corpus": lambda: brown.words(),
    "English: Brown Corpus (Press)": lambda: brown.words(
        categories=["news", "editorial", "reviews"]
    ),
    "English: Brown Corpus (Religion)": lambda: brown.words(categories="religion"),
    "English: Brown Corpus (Learned)": lambda: brown.words(categories="learned"),
    "English: Brown Corpus (Science Fiction)": lambda: brown.words(
        categories="science_fiction"
    ),
    "English: Brown Corpus (Romance)": lambda: brown.words(categories="romance"),
    "English: Brown Corpus (Humor)": lambda: brown.words(categories="humor"),
    "English: NPS Chat Corpus": lambda: nps_chat.words(),
    "English: Wall Street Journal Corpus": lambda: treebank.words(),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.words(),
    "Dutch: Alpino Corpus": lambda: alpino.words(),
    "Hindi: Indian Languages Corpus": lambda: indian.words(files="hindi.pos"),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.words(),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.words(),
    "Portuguese: Machado Corpus (Brazil)": lambda: machado.words(),
    "Spanish: CESS-ESP Corpus": lambda: cess_esp.words(),
}


class CollocationsView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    def __init__(self):
        self.queue = q.Queue()
        self.model = CollocationsModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("550x650+50+50")
        top.title("NLTK Collocations List")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(550, 650)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)
        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.reset_current_page()

    def reset_current_page(self):
        self.current_page = -1

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_results_box()
        self.freeze_editable()
        self.reset_current_page()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_results_box()
        self.reset_current_page()
        # self.next()
        collocations = self.model.next(self.current_page + 1)
        self.write_results(collocations)
        self.current_page += 1

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def previous(self):
        self.freeze_editable()
        collocations = self.model.prev(self.current_page - 1)
        self.current_page = self.current_page - 1
        self.clear_results_box()
        self.write_results(collocations)
        self.unfreeze_editable()

    def __next__(self):
        self.freeze_editable()
        collocations = self.model.next(self.current_page + 1)
        self.clear_results_box()
        self.write_results(collocations)
        self.current_page += 1
        self.unfreeze_editable()

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def freeze_editable(self):
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)

    def unfreeze_editable(self):
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == -1 or self.current_page == 0:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.is_last_page(self.current_page):
            self.next["state"] = "disabled"
        else:
            self.next["state"] = "normal"

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            self.results_box.insert(str(row) + ".0", each[0] + " " + each[1] + "\n")
            row += 1
        self.results_box["state"] = "disabled"


class CollocationsModel:
    def __init__(self, queue):
        self.result_count = None
        self.selected_corpus = None
        self.collocations = None
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.queue = queue
        self.reset_results()

    def reset_results(self):
        self.result_pages = []
        self.results_returned = 0

    def load_corpus(self, name):
        self.selected_corpus = name
        self.collocations = None
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()
        self.reset_results()

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def is_last_page(self, number):
        if number < len(self.result_pages):
            return False
        return self.results_returned + (
            number - len(self.result_pages)
        ) * self.result_count >= len(self.collocations)

    def next(self, page):
        if (len(self.result_pages) - 1) < page:
            for i in range(page - (len(self.result_pages) - 1)):
                self.result_pages.append(
                    self.collocations[
                        self.results_returned : self.results_returned
                        + self.result_count
                    ]
                )
                self.results_returned += self.result_count
        return self.result_pages[page]

    def prev(self, page):
        if page == -1:
            return []
        return self.result_pages[page]

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                words = self.model.CORPORA[self.name]()
                from operator import itemgetter

                text = [w for w in words if len(w) > 2]
                fd = FreqDist(tuple(text[i : i + 2]) for i in range(len(text) - 1))
                vocab = FreqDist(text)
                scored = [
                    ((w1, w2), fd[(w1, w2)] ** 3 / (vocab[w1] * vocab[w2]))
                    for w1, w2 in fd
                ]
                scored.sort(key=itemgetter(1), reverse=True)
                self.model.collocations = list(map(itemgetter(0), scored))
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)


# def collocations():
#    colloc_strings = [w1 + ' ' + w2 for w1, w2 in self._collocations[:num]]


def app():
    c = CollocationsView()
    c.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\collocations_app.py ===
# Natural Language Toolkit: Collocations Application
# Much of the GUI code is imported from concordance.py; We intend to merge these tools together
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#


import queue as q
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    machado,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.probability import FreqDist
from nltk.util import in_idle

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"
POLL_INTERVAL = 100

_DEFAULT = "English: Brown Corpus (Humor)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus": lambda: cess_cat.words(),
    "English: Brown Corpus": lambda: brown.words(),
    "English: Brown Corpus (Press)": lambda: brown.words(
        categories=["news", "editorial", "reviews"]
    ),
    "English: Brown Corpus (Religion)": lambda: brown.words(categories="religion"),
    "English: Brown Corpus (Learned)": lambda: brown.words(categories="learned"),
    "English: Brown Corpus (Science Fiction)": lambda: brown.words(
        categories="science_fiction"
    ),
    "English: Brown Corpus (Romance)": lambda: brown.words(categories="romance"),
    "English: Brown Corpus (Humor)": lambda: brown.words(categories="humor"),
    "English: NPS Chat Corpus": lambda: nps_chat.words(),
    "English: Wall Street Journal Corpus": lambda: treebank.words(),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.words(),
    "Dutch: Alpino Corpus": lambda: alpino.words(),
    "Hindi: Indian Languages Corpus": lambda: indian.words(files="hindi.pos"),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.words(),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.words(),
    "Portuguese: Machado Corpus (Brazil)": lambda: machado.words(),
    "Spanish: CESS-ESP Corpus": lambda: cess_esp.words(),
}


class CollocationsView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    def __init__(self):
        self.queue = q.Queue()
        self.model = CollocationsModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("550x650+50+50")
        top.title("NLTK Collocations List")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(550, 650)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)
        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.reset_current_page()

    def reset_current_page(self):
        self.current_page = -1

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_results_box()
        self.freeze_editable()
        self.reset_current_page()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_results_box()
        self.reset_current_page()
        # self.next()
        collocations = self.model.next(self.current_page + 1)
        self.write_results(collocations)
        self.current_page += 1

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def previous(self):
        self.freeze_editable()
        collocations = self.model.prev(self.current_page - 1)
        self.current_page = self.current_page - 1
        self.clear_results_box()
        self.write_results(collocations)
        self.unfreeze_editable()

    def __next__(self):
        self.freeze_editable()
        collocations = self.model.next(self.current_page + 1)
        self.clear_results_box()
        self.write_results(collocations)
        self.current_page += 1
        self.unfreeze_editable()

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def freeze_editable(self):
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)

    def unfreeze_editable(self):
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == -1 or self.current_page == 0:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.is_last_page(self.current_page):
            self.next["state"] = "disabled"
        else:
            self.next["state"] = "normal"

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            self.results_box.insert(str(row) + ".0", each[0] + " " + each[1] + "\n")
            row += 1
        self.results_box["state"] = "disabled"


class CollocationsModel:
    def __init__(self, queue):
        self.result_count = None
        self.selected_corpus = None
        self.collocations = None
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.queue = queue
        self.reset_results()

    def reset_results(self):
        self.result_pages = []
        self.results_returned = 0

    def load_corpus(self, name):
        self.selected_corpus = name
        self.collocations = None
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()
        self.reset_results()

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def is_last_page(self, number):
        if number < len(self.result_pages):
            return False
        return self.results_returned + (
            number - len(self.result_pages)
        ) * self.result_count >= len(self.collocations)

    def next(self, page):
        if (len(self.result_pages) - 1) < page:
            for i in range(page - (len(self.result_pages) - 1)):
                self.result_pages.append(
                    self.collocations[
                        self.results_returned : self.results_returned
                        + self.result_count
                    ]
                )
                self.results_returned += self.result_count
        return self.result_pages[page]

    def prev(self, page):
        if page == -1:
            return []
        return self.result_pages[page]

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                words = self.model.CORPORA[self.name]()
                from operator import itemgetter

                text = [w for w in words if len(w) > 2]
                fd = FreqDist(tuple(text[i : i + 2]) for i in range(len(text) - 1))
                vocab = FreqDist(text)
                scored = [
                    ((w1, w2), fd[(w1, w2)] ** 3 / (vocab[w1] * vocab[w2]))
                    for w1, w2 in fd
                ]
                scored.sort(key=itemgetter(1), reverse=True)
                self.model.collocations = list(map(itemgetter(0), scored))
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)


# def collocations():
#    colloc_strings = [w1 + ' ' + w2 for w1, w2 in self._collocations[:num]]


def app():
    c = CollocationsView()
    c.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\collocations_app.py ===
# Natural Language Toolkit: Collocations Application
# Much of the GUI code is imported from concordance.py; We intend to merge these tools together
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#


import queue as q
import threading
from tkinter import (
    END,
    LEFT,
    SUNKEN,
    Button,
    Frame,
    IntVar,
    Label,
    Menu,
    OptionMenu,
    Scrollbar,
    StringVar,
    Text,
    Tk,
)
from tkinter.font import Font

from nltk.corpus import (
    alpino,
    brown,
    cess_cat,
    cess_esp,
    floresta,
    indian,
    mac_morpho,
    machado,
    nps_chat,
    sinica_treebank,
    treebank,
)
from nltk.probability import FreqDist
from nltk.util import in_idle

CORPUS_LOADED_EVENT = "<<CL_EVENT>>"
ERROR_LOADING_CORPUS_EVENT = "<<ELC_EVENT>>"
POLL_INTERVAL = 100

_DEFAULT = "English: Brown Corpus (Humor)"
_CORPORA = {
    "Catalan: CESS-CAT Corpus": lambda: cess_cat.words(),
    "English: Brown Corpus": lambda: brown.words(),
    "English: Brown Corpus (Press)": lambda: brown.words(
        categories=["news", "editorial", "reviews"]
    ),
    "English: Brown Corpus (Religion)": lambda: brown.words(categories="religion"),
    "English: Brown Corpus (Learned)": lambda: brown.words(categories="learned"),
    "English: Brown Corpus (Science Fiction)": lambda: brown.words(
        categories="science_fiction"
    ),
    "English: Brown Corpus (Romance)": lambda: brown.words(categories="romance"),
    "English: Brown Corpus (Humor)": lambda: brown.words(categories="humor"),
    "English: NPS Chat Corpus": lambda: nps_chat.words(),
    "English: Wall Street Journal Corpus": lambda: treebank.words(),
    "Chinese: Sinica Corpus": lambda: sinica_treebank.words(),
    "Dutch: Alpino Corpus": lambda: alpino.words(),
    "Hindi: Indian Languages Corpus": lambda: indian.words(files="hindi.pos"),
    "Portuguese: Floresta Corpus (Portugal)": lambda: floresta.words(),
    "Portuguese: MAC-MORPHO Corpus (Brazil)": lambda: mac_morpho.words(),
    "Portuguese: Machado Corpus (Brazil)": lambda: machado.words(),
    "Spanish: CESS-ESP Corpus": lambda: cess_esp.words(),
}


class CollocationsView:
    _BACKGROUND_COLOUR = "#FFF"  # white

    def __init__(self):
        self.queue = q.Queue()
        self.model = CollocationsModel(self.queue)
        self.top = Tk()
        self._init_top(self.top)
        self._init_menubar()
        self._init_widgets(self.top)
        self.load_corpus(self.model.DEFAULT_CORPUS)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def _init_top(self, top):
        top.geometry("550x650+50+50")
        top.title("NLTK Collocations List")
        top.bind("<Control-q>", self.destroy)
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        top.minsize(550, 650)

    def _init_widgets(self, parent):
        self.main_frame = Frame(
            parent, dict(background=self._BACKGROUND_COLOUR, padx=1, pady=1, border=1)
        )
        self._init_corpus_select(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_paging(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill="both", expand=True)

    def _init_corpus_select(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.var = StringVar(innerframe)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(
            innerframe,
            justify=LEFT,
            text=" Corpus: ",
            background=self._BACKGROUND_COLOUR,
            padx=2,
            pady=1,
            border=0,
        ).pack(side="left")

        other_corpora = list(self.model.CORPORA.keys()).remove(
            self.model.DEFAULT_CORPUS
        )
        om = OptionMenu(
            innerframe,
            self.var,
            self.model.DEFAULT_CORPUS,
            command=self.corpus_selected,
            *self.model.non_default_corpora()
        )
        om["borderwidth"] = 0
        om["highlightthickness"] = 1
        om.pack(side="left")
        innerframe.pack(side="top", fill="x", anchor="n")

    def _init_status(self, parent):
        self.status = Label(
            parent,
            justify=LEFT,
            relief=SUNKEN,
            background=self._BACKGROUND_COLOUR,
            border=0,
            padx=1,
            pady=0,
        )
        self.status.pack(side="top", anchor="sw")

    def _init_menubar(self):
        self._result_size = IntVar(self.top)
        menubar = Menu(self.top)

        filemenu = Menu(menubar, tearoff=0, borderwidth=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        rescntmenu = Menu(editmenu, tearoff=0)
        rescntmenu.add_radiobutton(
            label="20",
            variable=self._result_size,
            underline=0,
            value=20,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="50",
            variable=self._result_size,
            underline=0,
            value=50,
            command=self.set_result_size,
        )
        rescntmenu.add_radiobutton(
            label="100",
            variable=self._result_size,
            underline=0,
            value=100,
            command=self.set_result_size,
        )
        rescntmenu.invoke(1)
        editmenu.add_cascade(label="Result Count", underline=0, menu=rescntmenu)

        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)
        self.top.config(menu=menubar)

    def set_result_size(self, **kwargs):
        self.model.result_count = self._result_size.get()

    def _init_results_box(self, parent):
        innerframe = Frame(parent)
        i1 = Frame(innerframe)
        i2 = Frame(innerframe)
        vscrollbar = Scrollbar(i1, borderwidth=1)
        hscrollbar = Scrollbar(i2, borderwidth=1, orient="horiz")
        self.results_box = Text(
            i1,
            font=Font(family="courier", size="16"),
            state="disabled",
            borderwidth=1,
            yscrollcommand=vscrollbar.set,
            xscrollcommand=hscrollbar.set,
            wrap="none",
            width="40",
            height="20",
            exportselection=1,
        )
        self.results_box.pack(side="left", fill="both", expand=True)
        vscrollbar.pack(side="left", fill="y", anchor="e")
        vscrollbar.config(command=self.results_box.yview)
        hscrollbar.pack(side="left", fill="x", expand=True, anchor="w")
        hscrollbar.config(command=self.results_box.xview)
        # there is no other way of avoiding the overlap of scrollbars while using pack layout manager!!!
        Label(i2, text="   ", background=self._BACKGROUND_COLOUR).pack(
            side="left", anchor="e"
        )
        i1.pack(side="top", fill="both", expand=True, anchor="n")
        i2.pack(side="bottom", fill="x", anchor="s")
        innerframe.pack(side="top", fill="both", expand=True)

    def _init_paging(self, parent):
        innerframe = Frame(parent, background=self._BACKGROUND_COLOUR)
        self.prev = prev = Button(
            innerframe,
            text="Previous",
            command=self.previous,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        prev.pack(side="left", anchor="center")
        self.next = next = Button(
            innerframe,
            text="Next",
            command=self.__next__,
            width="10",
            borderwidth=1,
            highlightthickness=1,
            state="disabled",
        )
        next.pack(side="right", anchor="center")
        innerframe.pack(side="top", fill="y")
        self.reset_current_page()

    def reset_current_page(self):
        self.current_page = -1

    def _poll(self):
        try:
            event = self.queue.get(block=False)
        except q.Empty:
            pass
        else:
            if event == CORPUS_LOADED_EVENT:
                self.handle_corpus_loaded(event)
            elif event == ERROR_LOADING_CORPUS_EVENT:
                self.handle_error_loading_corpus(event)
        self.after = self.top.after(POLL_INTERVAL, self._poll)

    def handle_error_loading_corpus(self, event):
        self.status["text"] = "Error in loading " + self.var.get()
        self.unfreeze_editable()
        self.clear_results_box()
        self.freeze_editable()
        self.reset_current_page()

    def handle_corpus_loaded(self, event):
        self.status["text"] = self.var.get() + " is loaded"
        self.unfreeze_editable()
        self.clear_results_box()
        self.reset_current_page()
        # self.next()
        collocations = self.model.next(self.current_page + 1)
        self.write_results(collocations)
        self.current_page += 1

    def corpus_selected(self, *args):
        new_selection = self.var.get()
        self.load_corpus(new_selection)

    def previous(self):
        self.freeze_editable()
        collocations = self.model.prev(self.current_page - 1)
        self.current_page = self.current_page - 1
        self.clear_results_box()
        self.write_results(collocations)
        self.unfreeze_editable()

    def __next__(self):
        self.freeze_editable()
        collocations = self.model.next(self.current_page + 1)
        self.clear_results_box()
        self.write_results(collocations)
        self.current_page += 1
        self.unfreeze_editable()

    def load_corpus(self, selection):
        if self.model.selected_corpus != selection:
            self.status["text"] = "Loading " + selection + "..."
            self.freeze_editable()
            self.model.load_corpus(selection)

    def freeze_editable(self):
        self.prev["state"] = "disabled"
        self.next["state"] = "disabled"

    def clear_results_box(self):
        self.results_box["state"] = "normal"
        self.results_box.delete("1.0", END)
        self.results_box["state"] = "disabled"

    def fire_event(self, event):
        # Firing an event so that rendering of widgets happen in the mainloop thread
        self.top.event_generate(event, when="tail")

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.after_cancel(self.after)
        self.top.destroy()
        self.top = None

    def mainloop(self, *args, **kwargs):
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)

    def unfreeze_editable(self):
        self.set_paging_button_states()

    def set_paging_button_states(self):
        if self.current_page == -1 or self.current_page == 0:
            self.prev["state"] = "disabled"
        else:
            self.prev["state"] = "normal"
        if self.model.is_last_page(self.current_page):
            self.next["state"] = "disabled"
        else:
            self.next["state"] = "normal"

    def write_results(self, results):
        self.results_box["state"] = "normal"
        row = 1
        for each in results:
            self.results_box.insert(str(row) + ".0", each[0] + " " + each[1] + "\n")
            row += 1
        self.results_box["state"] = "disabled"


class CollocationsModel:
    def __init__(self, queue):
        self.result_count = None
        self.selected_corpus = None
        self.collocations = None
        self.CORPORA = _CORPORA
        self.DEFAULT_CORPUS = _DEFAULT
        self.queue = queue
        self.reset_results()

    def reset_results(self):
        self.result_pages = []
        self.results_returned = 0

    def load_corpus(self, name):
        self.selected_corpus = name
        self.collocations = None
        runner_thread = self.LoadCorpus(name, self)
        runner_thread.start()
        self.reset_results()

    def non_default_corpora(self):
        copy = []
        copy.extend(list(self.CORPORA.keys()))
        copy.remove(self.DEFAULT_CORPUS)
        copy.sort()
        return copy

    def is_last_page(self, number):
        if number < len(self.result_pages):
            return False
        return self.results_returned + (
            number - len(self.result_pages)
        ) * self.result_count >= len(self.collocations)

    def next(self, page):
        if (len(self.result_pages) - 1) < page:
            for i in range(page - (len(self.result_pages) - 1)):
                self.result_pages.append(
                    self.collocations[
                        self.results_returned : self.results_returned
                        + self.result_count
                    ]
                )
                self.results_returned += self.result_count
        return self.result_pages[page]

    def prev(self, page):
        if page == -1:
            return []
        return self.result_pages[page]

    class LoadCorpus(threading.Thread):
        def __init__(self, name, model):
            threading.Thread.__init__(self)
            self.model, self.name = model, name

        def run(self):
            try:
                words = self.model.CORPORA[self.name]()
                from operator import itemgetter

                text = [w for w in words if len(w) > 2]
                fd = FreqDist(tuple(text[i : i + 2]) for i in range(len(text) - 1))
                vocab = FreqDist(text)
                scored = [
                    ((w1, w2), fd[(w1, w2)] ** 3 / (vocab[w1] * vocab[w2]))
                    for w1, w2 in fd
                ]
                scored.sort(key=itemgetter(1), reverse=True)
                self.model.collocations = list(map(itemgetter(0), scored))
                self.model.queue.put(CORPUS_LOADED_EVENT)
            except Exception as e:
                print(e)
                self.model.queue.put(ERROR_LOADING_CORPUS_EVENT)


# def collocations():
#    colloc_strings = [w1 + ' ' + w2 for w1, w2 in self._collocations[:num]]


def app():
    c = CollocationsView()
    c.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/exported_projects\app_20250703_223016\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()