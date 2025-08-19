
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

# === NexusCore/src\agents\debugger_agent.py ===
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