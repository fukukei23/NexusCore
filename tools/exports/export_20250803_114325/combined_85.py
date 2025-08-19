
# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_corenlp.py ===
"""
Mock test for Stanford CoreNLP wrappers.
"""

from unittest import TestCase
from unittest.mock import MagicMock

import pytest

from nltk.parse import corenlp
from nltk.tree import Tree


def setup_module(module):
    global server

    try:
        server = corenlp.CoreNLPServer(port=9000)
    except LookupError:
        pytest.skip("Could not instantiate CoreNLPServer.")

    try:
        server.start()
    except corenlp.CoreNLPServerError as e:
        pytest.skip(
            "Skipping CoreNLP tests because the server could not be started. "
            "Make sure that the 9000 port is free. "
            "{}".format(e.strerror)
        )


def teardown_module(module):
    server.stop()


class TestTokenizerAPI(TestCase):
    def test_tokenize(self):
        corenlp_tokenizer = corenlp.CoreNLPParser()

        api_return_value = {
            "sentences": [
                {
                    "index": 0,
                    "tokens": [
                        {
                            "after": " ",
                            "before": "",
                            "characterOffsetBegin": 0,
                            "characterOffsetEnd": 4,
                            "index": 1,
                            "originalText": "Good",
                            "word": "Good",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 5,
                            "characterOffsetEnd": 12,
                            "index": 2,
                            "originalText": "muffins",
                            "word": "muffins",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 13,
                            "characterOffsetEnd": 17,
                            "index": 3,
                            "originalText": "cost",
                            "word": "cost",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 18,
                            "characterOffsetEnd": 19,
                            "index": 4,
                            "originalText": "$",
                            "word": "$",
                        },
                        {
                            "after": "\n",
                            "before": "",
                            "characterOffsetBegin": 19,
                            "characterOffsetEnd": 23,
                            "index": 5,
                            "originalText": "3.88",
                            "word": "3.88",
                        },
                        {
                            "after": " ",
                            "before": "\n",
                            "characterOffsetBegin": 24,
                            "characterOffsetEnd": 26,
                            "index": 6,
                            "originalText": "in",
                            "word": "in",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 27,
                            "characterOffsetEnd": 30,
                            "index": 7,
                            "originalText": "New",
                            "word": "New",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 31,
                            "characterOffsetEnd": 35,
                            "index": 8,
                            "originalText": "York",
                            "word": "York",
                        },
                        {
                            "after": "  ",
                            "before": "",
                            "characterOffsetBegin": 35,
                            "characterOffsetEnd": 36,
                            "index": 9,
                            "originalText": ".",
                            "word": ".",
                        },
                    ],
                },
                {
                    "index": 1,
                    "tokens": [
                        {
                            "after": " ",
                            "before": "  ",
                            "characterOffsetBegin": 38,
                            "characterOffsetEnd": 44,
                            "index": 1,
                            "originalText": "Please",
                            "word": "Please",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 45,
                            "characterOffsetEnd": 48,
                            "index": 2,
                            "originalText": "buy",
                            "word": "buy",
                        },
                        {
                            "after": "\n",
                            "before": " ",
                            "characterOffsetBegin": 49,
                            "characterOffsetEnd": 51,
                            "index": 3,
                            "originalText": "me",
                            "word": "me",
                        },
                        {
                            "after": " ",
                            "before": "\n",
                            "characterOffsetBegin": 52,
                            "characterOffsetEnd": 55,
                            "index": 4,
                            "originalText": "two",
                            "word": "two",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 56,
                            "characterOffsetEnd": 58,
                            "index": 5,
                            "originalText": "of",
                            "word": "of",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 59,
                            "characterOffsetEnd": 63,
                            "index": 6,
                            "originalText": "them",
                            "word": "them",
                        },
                        {
                            "after": "\n",
                            "before": "",
                            "characterOffsetBegin": 63,
                            "characterOffsetEnd": 64,
                            "index": 7,
                            "originalText": ".",
                            "word": ".",
                        },
                    ],
                },
                {
                    "index": 2,
                    "tokens": [
                        {
                            "after": "",
                            "before": "\n",
                            "characterOffsetBegin": 65,
                            "characterOffsetEnd": 71,
                            "index": 1,
                            "originalText": "Thanks",
                            "word": "Thanks",
                        },
                        {
                            "after": "",
                            "before": "",
                            "characterOffsetBegin": 71,
                            "characterOffsetEnd": 72,
                            "index": 2,
                            "originalText": ".",
                            "word": ".",
                        },
                    ],
                },
            ]
        }
        corenlp_tokenizer.api_call = MagicMock(return_value=api_return_value)

        input_string = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks."

        expected_output = [
            "Good",
            "muffins",
            "cost",
            "$",
            "3.88",
            "in",
            "New",
            "York",
            ".",
            "Please",
            "buy",
            "me",
            "two",
            "of",
            "them",
            ".",
            "Thanks",
            ".",
        ]

        tokenized_output = list(corenlp_tokenizer.tokenize(input_string))

        corenlp_tokenizer.api_call.assert_called_once_with(
            "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks.",
            properties={"annotators": "tokenize,ssplit"},
        )
        self.assertEqual(expected_output, tokenized_output)


class TestTaggerAPI(TestCase):
    def test_pos_tagger(self):
        corenlp_tagger = corenlp.CoreNLPParser(tagtype="pos")

        api_return_value = {
            "sentences": [
                {
                    "basicDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 1,
                            "dependentGloss": "What",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "cop",
                            "dependent": 2,
                            "dependentGloss": "is",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "det",
                            "dependent": 3,
                            "dependentGloss": "the",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "airspeed",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "case",
                            "dependent": 5,
                            "dependentGloss": "of",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "det",
                            "dependent": 6,
                            "dependentGloss": "an",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "compound",
                            "dependent": 7,
                            "dependentGloss": "unladen",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "nmod",
                            "dependent": 8,
                            "dependentGloss": "swallow",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "punct",
                            "dependent": 9,
                            "dependentGloss": "?",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                    ],
                    "enhancedDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 1,
                            "dependentGloss": "What",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "cop",
                            "dependent": 2,
                            "dependentGloss": "is",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "det",
                            "dependent": 3,
                            "dependentGloss": "the",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "airspeed",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "case",
                            "dependent": 5,
                            "dependentGloss": "of",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "det",
                            "dependent": 6,
                            "dependentGloss": "an",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "compound",
                            "dependent": 7,
                            "dependentGloss": "unladen",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "nmod:of",
                            "dependent": 8,
                            "dependentGloss": "swallow",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "punct",
                            "dependent": 9,
                            "dependentGloss": "?",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                    ],
                    "enhancedPlusPlusDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 1,
                            "dependentGloss": "What",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "cop",
                            "dependent": 2,
                            "dependentGloss": "is",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "det",
                            "dependent": 3,
                            "dependentGloss": "the",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "airspeed",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                        {
                            "dep": "case",
                            "dependent": 5,
                            "dependentGloss": "of",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "det",
                            "dependent": 6,
                            "dependentGloss": "an",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "compound",
                            "dependent": 7,
                            "dependentGloss": "unladen",
                            "governor": 8,
                            "governorGloss": "swallow",
                        },
                        {
                            "dep": "nmod:of",
                            "dependent": 8,
                            "dependentGloss": "swallow",
                            "governor": 4,
                            "governorGloss": "airspeed",
                        },
                        {
                            "dep": "punct",
                            "dependent": 9,
                            "dependentGloss": "?",
                            "governor": 1,
                            "governorGloss": "What",
                        },
                    ],
                    "index": 0,
                    "parse": "(ROOT\n  (SBARQ\n    (WHNP (WP What))\n    (SQ (VBZ is)\n      (NP\n        (NP (DT the) (NN airspeed))\n        (PP (IN of)\n          (NP (DT an) (NN unladen) (NN swallow)))))\n    (. ?)))",
                    "tokens": [
                        {
                            "after": " ",
                            "before": "",
                            "characterOffsetBegin": 0,
                            "characterOffsetEnd": 4,
                            "index": 1,
                            "lemma": "what",
                            "originalText": "What",
                            "pos": "WP",
                            "word": "What",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 5,
                            "characterOffsetEnd": 7,
                            "index": 2,
                            "lemma": "be",
                            "originalText": "is",
                            "pos": "VBZ",
                            "word": "is",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 8,
                            "characterOffsetEnd": 11,
                            "index": 3,
                            "lemma": "the",
                            "originalText": "the",
                            "pos": "DT",
                            "word": "the",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 12,
                            "characterOffsetEnd": 20,
                            "index": 4,
                            "lemma": "airspeed",
                            "originalText": "airspeed",
                            "pos": "NN",
                            "word": "airspeed",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 21,
                            "characterOffsetEnd": 23,
                            "index": 5,
                            "lemma": "of",
                            "originalText": "of",
                            "pos": "IN",
                            "word": "of",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 24,
                            "characterOffsetEnd": 26,
                            "index": 6,
                            "lemma": "a",
                            "originalText": "an",
                            "pos": "DT",
                            "word": "an",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 27,
                            "characterOffsetEnd": 34,
                            "index": 7,
                            "lemma": "unladen",
                            "originalText": "unladen",
                            "pos": "JJ",
                            "word": "unladen",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 35,
                            "characterOffsetEnd": 42,
                            "index": 8,
                            "lemma": "swallow",
                            "originalText": "swallow",
                            "pos": "VB",
                            "word": "swallow",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 43,
                            "characterOffsetEnd": 44,
                            "index": 9,
                            "lemma": "?",
                            "originalText": "?",
                            "pos": ".",
                            "word": "?",
                        },
                    ],
                }
            ]
        }
        corenlp_tagger.api_call = MagicMock(return_value=api_return_value)

        input_tokens = "What is the airspeed of an unladen swallow ?".split()
        expected_output = [
            ("What", "WP"),
            ("is", "VBZ"),
            ("the", "DT"),
            ("airspeed", "NN"),
            ("of", "IN"),
            ("an", "DT"),
            ("unladen", "JJ"),
            ("swallow", "VB"),
            ("?", "."),
        ]
        tagged_output = corenlp_tagger.tag(input_tokens)

        corenlp_tagger.api_call.assert_called_once_with(
            "What is the airspeed of an unladen swallow ?",
            properties={
                "ssplit.isOneSentence": "true",
                "annotators": "tokenize,ssplit,pos",
            },
        )
        self.assertEqual(expected_output, tagged_output)

    def test_ner_tagger(self):
        corenlp_tagger = corenlp.CoreNLPParser(tagtype="ner")

        api_return_value = {
            "sentences": [
                {
                    "index": 0,
                    "tokens": [
                        {
                            "after": " ",
                            "before": "",
                            "characterOffsetBegin": 0,
                            "characterOffsetEnd": 4,
                            "index": 1,
                            "lemma": "Rami",
                            "ner": "PERSON",
                            "originalText": "Rami",
                            "pos": "NNP",
                            "word": "Rami",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 5,
                            "characterOffsetEnd": 8,
                            "index": 2,
                            "lemma": "Eid",
                            "ner": "PERSON",
                            "originalText": "Eid",
                            "pos": "NNP",
                            "word": "Eid",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 9,
                            "characterOffsetEnd": 11,
                            "index": 3,
                            "lemma": "be",
                            "ner": "O",
                            "originalText": "is",
                            "pos": "VBZ",
                            "word": "is",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 12,
                            "characterOffsetEnd": 20,
                            "index": 4,
                            "lemma": "study",
                            "ner": "O",
                            "originalText": "studying",
                            "pos": "VBG",
                            "word": "studying",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 21,
                            "characterOffsetEnd": 23,
                            "index": 5,
                            "lemma": "at",
                            "ner": "O",
                            "originalText": "at",
                            "pos": "IN",
                            "word": "at",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 24,
                            "characterOffsetEnd": 29,
                            "index": 6,
                            "lemma": "Stony",
                            "ner": "ORGANIZATION",
                            "originalText": "Stony",
                            "pos": "NNP",
                            "word": "Stony",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 30,
                            "characterOffsetEnd": 35,
                            "index": 7,
                            "lemma": "Brook",
                            "ner": "ORGANIZATION",
                            "originalText": "Brook",
                            "pos": "NNP",
                            "word": "Brook",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 36,
                            "characterOffsetEnd": 46,
                            "index": 8,
                            "lemma": "University",
                            "ner": "ORGANIZATION",
                            "originalText": "University",
                            "pos": "NNP",
                            "word": "University",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 47,
                            "characterOffsetEnd": 49,
                            "index": 9,
                            "lemma": "in",
                            "ner": "O",
                            "originalText": "in",
                            "pos": "IN",
                            "word": "in",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 50,
                            "characterOffsetEnd": 52,
                            "index": 10,
                            "lemma": "NY",
                            "ner": "O",
                            "originalText": "NY",
                            "pos": "NNP",
                            "word": "NY",
                        },
                    ],
                }
            ]
        }

        corenlp_tagger.api_call = MagicMock(return_value=api_return_value)

        input_tokens = "Rami Eid is studying at Stony Brook University in NY".split()
        expected_output = [
            ("Rami", "PERSON"),
            ("Eid", "PERSON"),
            ("is", "O"),
            ("studying", "O"),
            ("at", "O"),
            ("Stony", "ORGANIZATION"),
            ("Brook", "ORGANIZATION"),
            ("University", "ORGANIZATION"),
            ("in", "O"),
            ("NY", "O"),
        ]
        tagged_output = corenlp_tagger.tag(input_tokens)

        corenlp_tagger.api_call.assert_called_once_with(
            "Rami Eid is studying at Stony Brook University in NY",
            properties={
                "ssplit.isOneSentence": "true",
                "annotators": "tokenize,ssplit,ner",
            },
        )
        self.assertEqual(expected_output, tagged_output)

    def test_unexpected_tagtype(self):
        with self.assertRaises(ValueError):
            corenlp_tagger = corenlp.CoreNLPParser(tagtype="test")


class TestParserAPI(TestCase):
    def test_parse(self):
        corenlp_parser = corenlp.CoreNLPParser()

        api_return_value = {
            "sentences": [
                {
                    "basicDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "dep",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "enhancedDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "dep",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod:over",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "enhancedPlusPlusDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "dep",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod:over",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "index": 0,
                    "parse": "(ROOT\n  (NP\n    (NP (DT The) (JJ quick) (JJ brown) (NN fox))\n    (NP\n      (NP (NNS jumps))\n      (PP (IN over)\n        (NP (DT the) (JJ lazy) (NN dog))))))",
                    "tokens": [
                        {
                            "after": " ",
                            "before": "",
                            "characterOffsetBegin": 0,
                            "characterOffsetEnd": 3,
                            "index": 1,
                            "lemma": "the",
                            "originalText": "The",
                            "pos": "DT",
                            "word": "The",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 4,
                            "characterOffsetEnd": 9,
                            "index": 2,
                            "lemma": "quick",
                            "originalText": "quick",
                            "pos": "JJ",
                            "word": "quick",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 10,
                            "characterOffsetEnd": 15,
                            "index": 3,
                            "lemma": "brown",
                            "originalText": "brown",
                            "pos": "JJ",
                            "word": "brown",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 16,
                            "characterOffsetEnd": 19,
                            "index": 4,
                            "lemma": "fox",
                            "originalText": "fox",
                            "pos": "NN",
                            "word": "fox",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 20,
                            "characterOffsetEnd": 25,
                            "index": 5,
                            "lemma": "jump",
                            "originalText": "jumps",
                            "pos": "VBZ",
                            "word": "jumps",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 26,
                            "characterOffsetEnd": 30,
                            "index": 6,
                            "lemma": "over",
                            "originalText": "over",
                            "pos": "IN",
                            "word": "over",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 31,
                            "characterOffsetEnd": 34,
                            "index": 7,
                            "lemma": "the",
                            "originalText": "the",
                            "pos": "DT",
                            "word": "the",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 35,
                            "characterOffsetEnd": 39,
                            "index": 8,
                            "lemma": "lazy",
                            "originalText": "lazy",
                            "pos": "JJ",
                            "word": "lazy",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 40,
                            "characterOffsetEnd": 43,
                            "index": 9,
                            "lemma": "dog",
                            "originalText": "dog",
                            "pos": "NN",
                            "word": "dog",
                        },
                    ],
                }
            ]
        }

        corenlp_parser.api_call = MagicMock(return_value=api_return_value)

        input_string = "The quick brown fox jumps over the lazy dog".split()
        expected_output = Tree(
            "ROOT",
            [
                Tree(
                    "NP",
                    [
                        Tree(
                            "NP",
                            [
                                Tree("DT", ["The"]),
                                Tree("JJ", ["quick"]),
                                Tree("JJ", ["brown"]),
                                Tree("NN", ["fox"]),
                            ],
                        ),
                        Tree(
                            "NP",
                            [
                                Tree("NP", [Tree("NNS", ["jumps"])]),
                                Tree(
                                    "PP",
                                    [
                                        Tree("IN", ["over"]),
                                        Tree(
                                            "NP",
                                            [
                                                Tree("DT", ["the"]),
                                                Tree("JJ", ["lazy"]),
                                                Tree("NN", ["dog"]),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
            ],
        )

        parsed_data = next(corenlp_parser.parse(input_string))

        corenlp_parser.api_call.assert_called_once_with(
            "The quick brown fox jumps over the lazy dog",
            properties={"ssplit.eolonly": "true"},
        )
        self.assertEqual(expected_output, parsed_data)

    def test_dependency_parser(self):
        corenlp_parser = corenlp.CoreNLPDependencyParser()

        api_return_value = {
            "sentences": [
                {
                    "basicDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "enhancedDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod:over",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "enhancedPlusPlusDependencies": [
                        {
                            "dep": "ROOT",
                            "dependent": 5,
                            "dependentGloss": "jumps",
                            "governor": 0,
                            "governorGloss": "ROOT",
                        },
                        {
                            "dep": "det",
                            "dependent": 1,
                            "dependentGloss": "The",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 2,
                            "dependentGloss": "quick",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "amod",
                            "dependent": 3,
                            "dependentGloss": "brown",
                            "governor": 4,
                            "governorGloss": "fox",
                        },
                        {
                            "dep": "nsubj",
                            "dependent": 4,
                            "dependentGloss": "fox",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                        {
                            "dep": "case",
                            "dependent": 6,
                            "dependentGloss": "over",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "det",
                            "dependent": 7,
                            "dependentGloss": "the",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "amod",
                            "dependent": 8,
                            "dependentGloss": "lazy",
                            "governor": 9,
                            "governorGloss": "dog",
                        },
                        {
                            "dep": "nmod:over",
                            "dependent": 9,
                            "dependentGloss": "dog",
                            "governor": 5,
                            "governorGloss": "jumps",
                        },
                    ],
                    "index": 0,
                    "tokens": [
                        {
                            "after": " ",
                            "before": "",
                            "characterOffsetBegin": 0,
                            "characterOffsetEnd": 3,
                            "index": 1,
                            "lemma": "the",
                            "originalText": "The",
                            "pos": "DT",
                            "word": "The",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 4,
                            "characterOffsetEnd": 9,
                            "index": 2,
                            "lemma": "quick",
                            "originalText": "quick",
                            "pos": "JJ",
                            "word": "quick",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 10,
                            "characterOffsetEnd": 15,
                            "index": 3,
                            "lemma": "brown",
                            "originalText": "brown",
                            "pos": "JJ",
                            "word": "brown",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 16,
                            "characterOffsetEnd": 19,
                            "index": 4,
                            "lemma": "fox",
                            "originalText": "fox",
                            "pos": "NN",
                            "word": "fox",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 20,
                            "characterOffsetEnd": 25,
                            "index": 5,
                            "lemma": "jump",
                            "originalText": "jumps",
                            "pos": "VBZ",
                            "word": "jumps",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 26,
                            "characterOffsetEnd": 30,
                            "index": 6,
                            "lemma": "over",
                            "originalText": "over",
                            "pos": "IN",
                            "word": "over",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 31,
                            "characterOffsetEnd": 34,
                            "index": 7,
                            "lemma": "the",
                            "originalText": "the",
                            "pos": "DT",
                            "word": "the",
                        },
                        {
                            "after": " ",
                            "before": " ",
                            "characterOffsetBegin": 35,
                            "characterOffsetEnd": 39,
                            "index": 8,
                            "lemma": "lazy",
                            "originalText": "lazy",
                            "pos": "JJ",
                            "word": "lazy",
                        },
                        {
                            "after": "",
                            "before": " ",
                            "characterOffsetBegin": 40,
                            "characterOffsetEnd": 43,
                            "index": 9,
                            "lemma": "dog",
                            "originalText": "dog",
                            "pos": "NN",
                            "word": "dog",
                        },
                    ],
                }
            ]
        }

        corenlp_parser.api_call = MagicMock(return_value=api_return_value)

        input_string = "The quick brown fox jumps over the lazy dog".split()
        expected_output = Tree(
            "jumps",
            [
                Tree("fox", ["The", "quick", "brown"]),
                Tree("dog", ["over", "the", "lazy"]),
            ],
        )

        parsed_data = next(corenlp_parser.parse(input_string))

        corenlp_parser.api_call.assert_called_once_with(
            "The quick brown fox jumps over the lazy dog",
            properties={"ssplit.eolonly": "true"},
        )
        self.assertEqual(expected_output, parsed_data.tree())

# === NexusCore/openenv\Lib\site-packages\yaml\scanner.py ===

# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DIRECTIVE(name, value)
# DOCUMENT-START
# DOCUMENT-END
# BLOCK-SEQUENCE-START
# BLOCK-MAPPING-START
# BLOCK-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# BLOCK-ENTRY
# FLOW-ENTRY
# KEY
# VALUE
# ALIAS(value)
# ANCHOR(value)
# TAG(value)
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.
#

__all__ = ['Scanner', 'ScannerError']

from .error import MarkedYAMLError
from .tokens import *

class ScannerError(MarkedYAMLError):
    pass

class SimpleKey:
    # See below simple keys treatment.

    def __init__(self, token_number, required, index, line, column, mark):
        self.token_number = token_number
        self.required = required
        self.index = index
        self.line = line
        self.column = column
        self.mark = mark

class Scanner:

    def __init__(self):
        """Initialize the scanner."""
        # It is assumed that Scanner and Reader will have a common descendant.
        # Reader do the dirty work of checking for BOM and converting the
        # input data to Unicode. It also adds NUL to the end.
        #
        # Reader supports the following methods
        #   self.peek(i=0)       # peek the next i-th character
        #   self.prefix(l=1)     # peek the next l characters
        #   self.forward(l=1)    # read the next l characters and move the pointer.

        # Had we reached the end of the stream?
        self.done = False

        # The number of unclosed '{' and '['. `flow_level == 0` means block
        # context.
        self.flow_level = 0

        # List of processed tokens that are not yet emitted.
        self.tokens = []

        # Add the STREAM-START token.
        self.fetch_stream_start()

        # Number of tokens that were emitted through the `get_token` method.
        self.tokens_taken = 0

        # The current indentation level.
        self.indent = -1

        # Past indentation levels.
        self.indents = []

        # Variables related to simple keys treatment.

        # A simple key is a key that is not denoted by the '?' indicator.
        # Example of simple keys:
        #   ---
        #   block simple key: value
        #   ? not a simple key:
        #   : { flow simple key: value }
        # We emit the KEY token before all keys, so when we find a potential
        # simple key, we try to locate the corresponding ':' indicator.
        # Simple keys should be limited to a single line and 1024 characters.

        # Can a simple key start at the current position? A simple key may
        # start:
        # - at the beginning of the line, not counting indentation spaces
        #       (in block context),
        # - after '{', '[', ',' (in the flow context),
        # - after '?', ':', '-' (in the block context).
        # In the block context, this flag also signifies if a block collection
        # may start at the current position.
        self.allow_simple_key = True

        # Keep track of possible simple keys. This is a dictionary. The key
        # is `flow_level`; there can be no more that one possible simple key
        # for each level. The value is a SimpleKey record:
        #   (token_number, required, index, line, column, mark)
        # A simple key may start with ALIAS, ANCHOR, TAG, SCALAR(flow),
        # '[', or '{' tokens.
        self.possible_simple_keys = {}

    # Public methods.

    def check_token(self, *choices):
        # Check if the next token is one of the given types.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.tokens[0], choice):
                    return True
        return False

    def peek_token(self):
        # Return the next token, but do not delete if from the queue.
        # Return None if no more tokens.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            return self.tokens[0]
        else:
            return None

    def get_token(self):
        # Return the next token.
        while self.need_more_tokens():
            self.fetch_more_tokens()
        if self.tokens:
            self.tokens_taken += 1
            return self.tokens.pop(0)

    # Private methods.

    def need_more_tokens(self):
        if self.done:
            return False
        if not self.tokens:
            return True
        # The current token may be a potential simple key, so we
        # need to look further.
        self.stale_possible_simple_keys()
        if self.next_possible_simple_key() == self.tokens_taken:
            return True

    def fetch_more_tokens(self):

        # Eat whitespaces and comments until we reach the next token.
        self.scan_to_next_token()

        # Remove obsolete possible simple keys.
        self.stale_possible_simple_keys()

        # Compare the current indentation and column. It may add some tokens
        # and decrease the current indentation level.
        self.unwind_indent(self.column)

        # Peek the next character.
        ch = self.peek()

        # Is it the end of stream?
        if ch == '\0':
            return self.fetch_stream_end()

        # Is it a directive?
        if ch == '%' and self.check_directive():
            return self.fetch_directive()

        # Is it the document start?
        if ch == '-' and self.check_document_start():
            return self.fetch_document_start()

        # Is it the document end?
        if ch == '.' and self.check_document_end():
            return self.fetch_document_end()

        # TODO: support for BOM within a stream.
        #if ch == '\uFEFF':
        #    return self.fetch_bom()    <-- issue BOMToken

        # Note: the order of the following checks is NOT significant.

        # Is it the flow sequence start indicator?
        if ch == '[':
            return self.fetch_flow_sequence_start()

        # Is it the flow mapping start indicator?
        if ch == '{':
            return self.fetch_flow_mapping_start()

        # Is it the flow sequence end indicator?
        if ch == ']':
            return self.fetch_flow_sequence_end()

        # Is it the flow mapping end indicator?
        if ch == '}':
            return self.fetch_flow_mapping_end()

        # Is it the flow entry indicator?
        if ch == ',':
            return self.fetch_flow_entry()

        # Is it the block entry indicator?
        if ch == '-' and self.check_block_entry():
            return self.fetch_block_entry()

        # Is it the key indicator?
        if ch == '?' and self.check_key():
            return self.fetch_key()

        # Is it the value indicator?
        if ch == ':' and self.check_value():
            return self.fetch_value()

        # Is it an alias?
        if ch == '*':
            return self.fetch_alias()

        # Is it an anchor?
        if ch == '&':
            return self.fetch_anchor()

        # Is it a tag?
        if ch == '!':
            return self.fetch_tag()

        # Is it a literal scalar?
        if ch == '|' and not self.flow_level:
            return self.fetch_literal()

        # Is it a folded scalar?
        if ch == '>' and not self.flow_level:
            return self.fetch_folded()

        # Is it a single quoted scalar?
        if ch == '\'':
            return self.fetch_single()

        # Is it a double quoted scalar?
        if ch == '\"':
            return self.fetch_double()

        # It must be a plain scalar then.
        if self.check_plain():
            return self.fetch_plain()

        # No? It's an error. Let's produce a nice error message.
        raise ScannerError("while scanning for the next token", None,
                "found character %r that cannot start any token" % ch,
                self.get_mark())

    # Simple keys treatment.

    def next_possible_simple_key(self):
        # Return the number of the nearest possible simple key. Actually we
        # don't need to loop through the whole dictionary. We may replace it
        # with the following code:
        #   if not self.possible_simple_keys:
        #       return None
        #   return self.possible_simple_keys[
        #           min(self.possible_simple_keys.keys())].token_number
        min_token_number = None
        for level in self.possible_simple_keys:
            key = self.possible_simple_keys[level]
            if min_token_number is None or key.token_number < min_token_number:
                min_token_number = key.token_number
        return min_token_number

    def stale_possible_simple_keys(self):
        # Remove entries that are no longer possible simple keys. According to
        # the YAML specification, simple keys
        # - should be limited to a single line,
        # - should be no longer than 1024 characters.
        # Disabling this procedure will allow simple keys of any length and
        # height (may cause problems if indentation is broken though).
        for level in list(self.possible_simple_keys):
            key = self.possible_simple_keys[level]
            if key.line != self.line  \
                    or self.index-key.index > 1024:
                if key.required:
                    raise ScannerError("while scanning a simple key", key.mark,
                            "could not find expected ':'", self.get_mark())
                del self.possible_simple_keys[level]

    def save_possible_simple_key(self):
        # The next token may start a simple key. We check if it's possible
        # and save its position. This function is called for
        #   ALIAS, ANCHOR, TAG, SCALAR(flow), '[', and '{'.

        # Check if a simple key is required at the current position.
        required = not self.flow_level and self.indent == self.column

        # The next token might be a simple key. Let's save it's number and
        # position.
        if self.allow_simple_key:
            self.remove_possible_simple_key()
            token_number = self.tokens_taken+len(self.tokens)
            key = SimpleKey(token_number, required,
                    self.index, self.line, self.column, self.get_mark())
            self.possible_simple_keys[self.flow_level] = key

    def remove_possible_simple_key(self):
        # Remove the saved possible key position at the current flow level.
        if self.flow_level in self.possible_simple_keys:
            key = self.possible_simple_keys[self.flow_level]
            
            if key.required:
                raise ScannerError("while scanning a simple key", key.mark,
                        "could not find expected ':'", self.get_mark())

            del self.possible_simple_keys[self.flow_level]

    # Indentation functions.

    def unwind_indent(self, column):

        ## In flow context, tokens should respect indentation.
        ## Actually the condition should be `self.indent >= column` according to
        ## the spec. But this condition will prohibit intuitively correct
        ## constructions such as
        ## key : {
        ## }
        #if self.flow_level and self.indent > column:
        #    raise ScannerError(None, None,
        #            "invalid indentation or unclosed '[' or '{'",
        #            self.get_mark())

        # In the flow context, indentation is ignored. We make the scanner less
        # restrictive then specification requires.
        if self.flow_level:
            return

        # In block context, we may need to issue the BLOCK-END tokens.
        while self.indent > column:
            mark = self.get_mark()
            self.indent = self.indents.pop()
            self.tokens.append(BlockEndToken(mark, mark))

    def add_indent(self, column):
        # Check if we need to increase indentation.
        if self.indent < column:
            self.indents.append(self.indent)
            self.indent = column
            return True
        return False

    # Fetchers.

    def fetch_stream_start(self):
        # We always add STREAM-START as the first token and STREAM-END as the
        # last token.

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-START.
        self.tokens.append(StreamStartToken(mark, mark,
            encoding=self.encoding))
        

    def fetch_stream_end(self):

        # Set the current indentation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False
        self.possible_simple_keys = {}

        # Read the token.
        mark = self.get_mark()
        
        # Add STREAM-END.
        self.tokens.append(StreamEndToken(mark, mark))

        # The steam is finished.
        self.done = True

    def fetch_directive(self):
        
        # Set the current indentation to -1.
        self.unwind_indent(-1)

        # Reset simple keys.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Scan and add DIRECTIVE.
        self.tokens.append(self.scan_directive())

    def fetch_document_start(self):
        self.fetch_document_indicator(DocumentStartToken)

    def fetch_document_end(self):
        self.fetch_document_indicator(DocumentEndToken)

    def fetch_document_indicator(self, TokenClass):

        # Set the current indentation to -1.
        self.unwind_indent(-1)

        # Reset simple keys. Note that there could not be a block collection
        # after '---'.
        self.remove_possible_simple_key()
        self.allow_simple_key = False

        # Add DOCUMENT-START or DOCUMENT-END.
        start_mark = self.get_mark()
        self.forward(3)
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_start(self):
        self.fetch_flow_collection_start(FlowSequenceStartToken)

    def fetch_flow_mapping_start(self):
        self.fetch_flow_collection_start(FlowMappingStartToken)

    def fetch_flow_collection_start(self, TokenClass):

        # '[' and '{' may start a simple key.
        self.save_possible_simple_key()

        # Increase the flow level.
        self.flow_level += 1

        # Simple keys are allowed after '[' and '{'.
        self.allow_simple_key = True

        # Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_sequence_end(self):
        self.fetch_flow_collection_end(FlowSequenceEndToken)

    def fetch_flow_mapping_end(self):
        self.fetch_flow_collection_end(FlowMappingEndToken)

    def fetch_flow_collection_end(self, TokenClass):

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Decrease the flow level.
        self.flow_level -= 1

        # No simple keys after ']' or '}'.
        self.allow_simple_key = False

        # Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(TokenClass(start_mark, end_mark))

    def fetch_flow_entry(self):

        # Simple keys are allowed after ','.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add FLOW-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(FlowEntryToken(start_mark, end_mark))

    def fetch_block_entry(self):

        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a new entry?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "sequence entries are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-SEQUENCE-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockSequenceStartToken(mark, mark))

        # It's an error for the block entry to occur in the flow context,
        # but we let the parser detect this.
        else:
            pass

        # Simple keys are allowed after '-'.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add BLOCK-ENTRY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(BlockEntryToken(start_mark, end_mark))

    def fetch_key(self):
        
        # Block context needs additional checks.
        if not self.flow_level:

            # Are we allowed to start a key (not necessary a simple)?
            if not self.allow_simple_key:
                raise ScannerError(None, None,
                        "mapping keys are not allowed here",
                        self.get_mark())

            # We may need to add BLOCK-MAPPING-START.
            if self.add_indent(self.column):
                mark = self.get_mark()
                self.tokens.append(BlockMappingStartToken(mark, mark))

        # Simple keys are allowed after '?' in the block context.
        self.allow_simple_key = not self.flow_level

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Add KEY.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(KeyToken(start_mark, end_mark))

    def fetch_value(self):

        # Do we determine a simple key?
        if self.flow_level in self.possible_simple_keys:

            # Add KEY.
            key = self.possible_simple_keys[self.flow_level]
            del self.possible_simple_keys[self.flow_level]
            self.tokens.insert(key.token_number-self.tokens_taken,
                    KeyToken(key.mark, key.mark))

            # If this key starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.
            if not self.flow_level:
                if self.add_indent(key.column):
                    self.tokens.insert(key.token_number-self.tokens_taken,
                            BlockMappingStartToken(key.mark, key.mark))

            # There cannot be two simple keys one after another.
            self.allow_simple_key = False

        # It must be a part of a complex key.
        else:
            
            # Block context needs additional checks.
            # (Do we really need them? They will be caught by the parser
            # anyway.)
            if not self.flow_level:

                # We are allowed to start a complex value if and only if
                # we can start a simple key.
                if not self.allow_simple_key:
                    raise ScannerError(None, None,
                            "mapping values are not allowed here",
                            self.get_mark())

            # If this value starts a new block mapping, we need to add
            # BLOCK-MAPPING-START.  It will be detected as an error later by
            # the parser.
            if not self.flow_level:
                if self.add_indent(self.column):
                    mark = self.get_mark()
                    self.tokens.append(BlockMappingStartToken(mark, mark))

            # Simple keys are allowed after ':' in the block context.
            self.allow_simple_key = not self.flow_level

            # Reset possible simple key on the current level.
            self.remove_possible_simple_key()

        # Add VALUE.
        start_mark = self.get_mark()
        self.forward()
        end_mark = self.get_mark()
        self.tokens.append(ValueToken(start_mark, end_mark))

    def fetch_alias(self):

        # ALIAS could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after ALIAS.
        self.allow_simple_key = False

        # Scan and add ALIAS.
        self.tokens.append(self.scan_anchor(AliasToken))

    def fetch_anchor(self):

        # ANCHOR could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after ANCHOR.
        self.allow_simple_key = False

        # Scan and add ANCHOR.
        self.tokens.append(self.scan_anchor(AnchorToken))

    def fetch_tag(self):

        # TAG could start a simple key.
        self.save_possible_simple_key()

        # No simple keys after TAG.
        self.allow_simple_key = False

        # Scan and add TAG.
        self.tokens.append(self.scan_tag())

    def fetch_literal(self):
        self.fetch_block_scalar(style='|')

    def fetch_folded(self):
        self.fetch_block_scalar(style='>')

    def fetch_block_scalar(self, style):

        # A simple key may follow a block scalar.
        self.allow_simple_key = True

        # Reset possible simple key on the current level.
        self.remove_possible_simple_key()

        # Scan and add SCALAR.
        self.tokens.append(self.scan_block_scalar(style))

    def fetch_single(self):
        self.fetch_flow_scalar(style='\'')

    def fetch_double(self):
        self.fetch_flow_scalar(style='"')

    def fetch_flow_scalar(self, style):

        # A flow scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after flow scalars.
        self.allow_simple_key = False

        # Scan and add SCALAR.
        self.tokens.append(self.scan_flow_scalar(style))

    def fetch_plain(self):

        # A plain scalar could be a simple key.
        self.save_possible_simple_key()

        # No simple keys after plain scalars. But note that `scan_plain` will
        # change this flag if the scan is finished at the beginning of the
        # line.
        self.allow_simple_key = False

        # Scan and add SCALAR. May change `allow_simple_key`.
        self.tokens.append(self.scan_plain())

    # Checkers.

    def check_directive(self):

        # DIRECTIVE:        ^ '%' ...
        # The '%' indicator is already checked.
        if self.column == 0:
            return True

    def check_document_start(self):

        # DOCUMENT-START:   ^ '---' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == '---'  \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_document_end(self):

        # DOCUMENT-END:     ^ '...' (' '|'\n')
        if self.column == 0:
            if self.prefix(3) == '...'  \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return True

    def check_block_entry(self):

        # BLOCK-ENTRY:      '-' (' '|'\n')
        return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_key(self):

        # KEY(flow context):    '?'
        if self.flow_level:
            return True

        # KEY(block context):   '?' (' '|'\n')
        else:
            return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_value(self):

        # VALUE(flow context):  ':'
        if self.flow_level:
            return True

        # VALUE(block context): ':' (' '|'\n')
        else:
            return self.peek(1) in '\0 \t\r\n\x85\u2028\u2029'

    def check_plain(self):

        # A plain scalar may start with any non-space character except:
        #   '-', '?', ':', ',', '[', ']', '{', '}',
        #   '#', '&', '*', '!', '|', '>', '\'', '\"',
        #   '%', '@', '`'.
        #
        # It may also start with
        #   '-', '?', ':'
        # if it is followed by a non-space character.
        #
        # Note that we limit the last rule to the block context (except the
        # '-' character) because we want the flow context to be space
        # independent.
        ch = self.peek()
        return ch not in '\0 \t\r\n\x85\u2028\u2029-?:,[]{}#&*!|>\'\"%@`'  \
                or (self.peek(1) not in '\0 \t\r\n\x85\u2028\u2029'
                        and (ch == '-' or (not self.flow_level and ch in '?:')))

    # Scanners.

    def scan_to_next_token(self):
        # We ignore spaces, line breaks and comments.
        # If we find a line break in the block context, we set the flag
        # `allow_simple_key` on.
        # The byte order mark is stripped if it's the first character in the
        # stream. We do not yet support BOM inside the stream as the
        # specification requires. Any such mark will be considered as a part
        # of the document.
        #
        # TODO: We need to make tab handling rules more sane. A good rule is
        #   Tabs cannot precede tokens
        #   BLOCK-SEQUENCE-START, BLOCK-MAPPING-START, BLOCK-END,
        #   KEY(block), VALUE(block), BLOCK-ENTRY
        # So the checking code is
        #   if <TAB>:
        #       self.allow_simple_keys = False
        # We also need to add the check for `allow_simple_keys == True` to
        # `unwind_indent` before issuing BLOCK-END.
        # Scanners for block, flow, and plain scalars need to be modified.

        if self.index == 0 and self.peek() == '\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == ' ':
                self.forward()
            if self.peek() == '#':
                while self.peek() not in '\0\r\n\x85\u2028\u2029':
                    self.forward()
            if self.scan_line_break():
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

    def scan_directive(self):
        # See the specification for details.
        start_mark = self.get_mark()
        self.forward()
        name = self.scan_directive_name(start_mark)
        value = None
        if name == 'YAML':
            value = self.scan_yaml_directive_value(start_mark)
            end_mark = self.get_mark()
        elif name == 'TAG':
            value = self.scan_tag_directive_value(start_mark)
            end_mark = self.get_mark()
        else:
            end_mark = self.get_mark()
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        self.scan_directive_ignored_line(start_mark)
        return DirectiveToken(name, value, start_mark, end_mark)

    def scan_directive_name(self, start_mark):
        # See the specification for details.
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        return value

    def scan_yaml_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        major = self.scan_yaml_directive_number(start_mark)
        if self.peek() != '.':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or '.', but found %r" % self.peek(),
                    self.get_mark())
        self.forward()
        minor = self.scan_yaml_directive_number(start_mark)
        if self.peek() not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit or ' ', but found %r" % self.peek(),
                    self.get_mark())
        return (major, minor)

    def scan_yaml_directive_number(self, start_mark):
        # See the specification for details.
        ch = self.peek()
        if not ('0' <= ch <= '9'):
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a digit, but found %r" % ch, self.get_mark())
        length = 0
        while '0' <= self.peek(length) <= '9':
            length += 1
        value = int(self.prefix(length))
        self.forward(length)
        return value

    def scan_tag_directive_value(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        handle = self.scan_tag_directive_handle(start_mark)
        while self.peek() == ' ':
            self.forward()
        prefix = self.scan_tag_directive_prefix(start_mark)
        return (handle, prefix)

    def scan_tag_directive_handle(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_handle('directive', start_mark)
        ch = self.peek()
        if ch != ' ':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        return value

    def scan_tag_directive_prefix(self, start_mark):
        # See the specification for details.
        value = self.scan_tag_uri('directive', start_mark)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        return value

    def scan_directive_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        if self.peek() == '#':
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in '\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a directive", start_mark,
                    "expected a comment or a line break, but found %r"
                        % ch, self.get_mark())
        self.scan_line_break()

    def scan_anchor(self, TokenClass):
        # The specification does not restrict characters for anchors and
        # aliases. This may lead to problems, for instance, the document:
        #   [ *alias, value ]
        # can be interpreted in two ways, as
        #   [ "value" ]
        # and
        #   [ *alias , "value" ]
        # Therefore we restrict aliases to numbers and ASCII letters.
        start_mark = self.get_mark()
        indicator = self.peek()
        if indicator == '*':
            name = 'alias'
        else:
            name = 'anchor'
        self.forward()
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-_':
            length += 1
            ch = self.peek(length)
        if not length:
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        value = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch not in '\0 \t\r\n\x85\u2028\u2029?:,]}%@`':
            raise ScannerError("while scanning an %s" % name, start_mark,
                    "expected alphabetic or numeric character, but found %r"
                    % ch, self.get_mark())
        end_mark = self.get_mark()
        return TokenClass(value, start_mark, end_mark)

    def scan_tag(self):
        # See the specification for details.
        start_mark = self.get_mark()
        ch = self.peek(1)
        if ch == '<':
            handle = None
            self.forward(2)
            suffix = self.scan_tag_uri('tag', start_mark)
            if self.peek() != '>':
                raise ScannerError("while parsing a tag", start_mark,
                        "expected '>', but found %r" % self.peek(),
                        self.get_mark())
            self.forward()
        elif ch in '\0 \t\r\n\x85\u2028\u2029':
            handle = None
            suffix = '!'
            self.forward()
        else:
            length = 1
            use_handle = False
            while ch not in '\0 \r\n\x85\u2028\u2029':
                if ch == '!':
                    use_handle = True
                    break
                length += 1
                ch = self.peek(length)
            handle = '!'
            if use_handle:
                handle = self.scan_tag_handle('tag', start_mark)
            else:
                handle = '!'
                self.forward()
            suffix = self.scan_tag_uri('tag', start_mark)
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a tag", start_mark,
                    "expected ' ', but found %r" % ch, self.get_mark())
        value = (handle, suffix)
        end_mark = self.get_mark()
        return TagToken(value, start_mark, end_mark)

    def scan_block_scalar(self, style):
        # See the specification for details.

        if style == '>':
            folded = True
        else:
            folded = False

        chunks = []
        start_mark = self.get_mark()

        # Scan the header.
        self.forward()
        chomping, increment = self.scan_block_scalar_indicators(start_mark)
        self.scan_block_scalar_ignored_line(start_mark)

        # Determine the indentation level and go to the first non-empty line.
        min_indent = self.indent+1
        if min_indent < 1:
            min_indent = 1
        if increment is None:
            breaks, max_indent, end_mark = self.scan_block_scalar_indentation()
            indent = max(min_indent, max_indent)
        else:
            indent = min_indent+increment-1
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
        line_break = ''

        # Scan the inner part of the block scalar.
        while self.column == indent and self.peek() != '\0':
            chunks.extend(breaks)
            leading_non_space = self.peek() not in ' \t'
            length = 0
            while self.peek(length) not in '\0\r\n\x85\u2028\u2029':
                length += 1
            chunks.append(self.prefix(length))
            self.forward(length)
            line_break = self.scan_line_break()
            breaks, end_mark = self.scan_block_scalar_breaks(indent)
            if self.column == indent and self.peek() != '\0':

                # Unfortunately, folding rules are ambiguous.
                #
                # This is the folding according to the specification:
                
                if folded and line_break == '\n'    \
                        and leading_non_space and self.peek() not in ' \t':
                    if not breaks:
                        chunks.append(' ')
                else:
                    chunks.append(line_break)
                
                # This is Clark Evans's interpretation (also in the spec
                # examples):
                #
                #if folded and line_break == '\n':
                #    if not breaks:
                #        if self.peek() not in ' \t':
                #            chunks.append(' ')
                #        else:
                #            chunks.append(line_break)
                #else:
                #    chunks.append(line_break)
            else:
                break

        # Chomp the tail.
        if chomping is not False:
            chunks.append(line_break)
        if chomping is True:
            chunks.extend(breaks)

        # We are done.
        return ScalarToken(''.join(chunks), False, start_mark, end_mark,
                style)

    def scan_block_scalar_indicators(self, start_mark):
        # See the specification for details.
        chomping = None
        increment = None
        ch = self.peek()
        if ch in '+-':
            if ch == '+':
                chomping = True
            else:
                chomping = False
            self.forward()
            ch = self.peek()
            if ch in '0123456789':
                increment = int(ch)
                if increment == 0:
                    raise ScannerError("while scanning a block scalar", start_mark,
                            "expected indentation indicator in the range 1-9, but found 0",
                            self.get_mark())
                self.forward()
        elif ch in '0123456789':
            increment = int(ch)
            if increment == 0:
                raise ScannerError("while scanning a block scalar", start_mark,
                        "expected indentation indicator in the range 1-9, but found 0",
                        self.get_mark())
            self.forward()
            ch = self.peek()
            if ch in '+-':
                if ch == '+':
                    chomping = True
                else:
                    chomping = False
                self.forward()
        ch = self.peek()
        if ch not in '\0 \r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected chomping or indentation indicators, but found %r"
                    % ch, self.get_mark())
        return chomping, increment

    def scan_block_scalar_ignored_line(self, start_mark):
        # See the specification for details.
        while self.peek() == ' ':
            self.forward()
        if self.peek() == '#':
            while self.peek() not in '\0\r\n\x85\u2028\u2029':
                self.forward()
        ch = self.peek()
        if ch not in '\0\r\n\x85\u2028\u2029':
            raise ScannerError("while scanning a block scalar", start_mark,
                    "expected a comment or a line break, but found %r" % ch,
                    self.get_mark())
        self.scan_line_break()

    def scan_block_scalar_indentation(self):
        # See the specification for details.
        chunks = []
        max_indent = 0
        end_mark = self.get_mark()
        while self.peek() in ' \r\n\x85\u2028\u2029':
            if self.peek() != ' ':
                chunks.append(self.scan_line_break())
                end_mark = self.get_mark()
            else:
                self.forward()
                if self.column > max_indent:
                    max_indent = self.column
        return chunks, max_indent, end_mark

    def scan_block_scalar_breaks(self, indent):
        # See the specification for details.
        chunks = []
        end_mark = self.get_mark()
        while self.column < indent and self.peek() == ' ':
            self.forward()
        while self.peek() in '\r\n\x85\u2028\u2029':
            chunks.append(self.scan_line_break())
            end_mark = self.get_mark()
            while self.column < indent and self.peek() == ' ':
                self.forward()
        return chunks, end_mark

    def scan_flow_scalar(self, style):
        # See the specification for details.
        # Note that we loose indentation rules for quoted scalars. Quoted
        # scalars don't need to adhere indentation because " and ' clearly
        # mark the beginning and the end of them. Therefore we are less
        # restrictive then the specification requires. We only need to check
        # that document separators are not included in scalars.
        if style == '"':
            double = True
        else:
            double = False
        chunks = []
        start_mark = self.get_mark()
        quote = self.peek()
        self.forward()
        chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        while self.peek() != quote:
            chunks.extend(self.scan_flow_scalar_spaces(double, start_mark))
            chunks.extend(self.scan_flow_scalar_non_spaces(double, start_mark))
        self.forward()
        end_mark = self.get_mark()
        return ScalarToken(''.join(chunks), False, start_mark, end_mark,
                style)

    ESCAPE_REPLACEMENTS = {
        '0':    '\0',
        'a':    '\x07',
        'b':    '\x08',
        't':    '\x09',
        '\t':   '\x09',
        'n':    '\x0A',
        'v':    '\x0B',
        'f':    '\x0C',
        'r':    '\x0D',
        'e':    '\x1B',
        ' ':    '\x20',
        '\"':   '\"',
        '\\':   '\\',
        '/':    '/',
        'N':    '\x85',
        '_':    '\xA0',
        'L':    '\u2028',
        'P':    '\u2029',
    }

    ESCAPE_CODES = {
        'x':    2,
        'u':    4,
        'U':    8,
    }

    def scan_flow_scalar_non_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            length = 0
            while self.peek(length) not in '\'\"\\\0 \t\r\n\x85\u2028\u2029':
                length += 1
            if length:
                chunks.append(self.prefix(length))
                self.forward(length)
            ch = self.peek()
            if not double and ch == '\'' and self.peek(1) == '\'':
                chunks.append('\'')
                self.forward(2)
            elif (double and ch == '\'') or (not double and ch in '\"\\'):
                chunks.append(ch)
                self.forward()
            elif double and ch == '\\':
                self.forward()
                ch = self.peek()
                if ch in self.ESCAPE_REPLACEMENTS:
                    chunks.append(self.ESCAPE_REPLACEMENTS[ch])
                    self.forward()
                elif ch in self.ESCAPE_CODES:
                    length = self.ESCAPE_CODES[ch]
                    self.forward()
                    for k in range(length):
                        if self.peek(k) not in '0123456789ABCDEFabcdef':
                            raise ScannerError("while scanning a double-quoted scalar", start_mark,
                                    "expected escape sequence of %d hexadecimal numbers, but found %r" %
                                        (length, self.peek(k)), self.get_mark())
                    code = int(self.prefix(length), 16)
                    chunks.append(chr(code))
                    self.forward(length)
                elif ch in '\r\n\x85\u2028\u2029':
                    self.scan_line_break()
                    chunks.extend(self.scan_flow_scalar_breaks(double, start_mark))
                else:
                    raise ScannerError("while scanning a double-quoted scalar", start_mark,
                            "found unknown escape character %r" % ch, self.get_mark())
            else:
                return chunks

    def scan_flow_scalar_spaces(self, double, start_mark):
        # See the specification for details.
        chunks = []
        length = 0
        while self.peek(length) in ' \t':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch == '\0':
            raise ScannerError("while scanning a quoted scalar", start_mark,
                    "found unexpected end of stream", self.get_mark())
        elif ch in '\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            breaks = self.scan_flow_scalar_breaks(double, start_mark)
            if line_break != '\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(' ')
            chunks.extend(breaks)
        else:
            chunks.append(whitespaces)
        return chunks

    def scan_flow_scalar_breaks(self, double, start_mark):
        # See the specification for details.
        chunks = []
        while True:
            # Instead of checking indentation, we check for document
            # separators.
            prefix = self.prefix(3)
            if (prefix == '---' or prefix == '...')   \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                raise ScannerError("while scanning a quoted scalar", start_mark,
                        "found unexpected document separator", self.get_mark())
            while self.peek() in ' \t':
                self.forward()
            if self.peek() in '\r\n\x85\u2028\u2029':
                chunks.append(self.scan_line_break())
            else:
                return chunks

    def scan_plain(self):
        # See the specification for details.
        # We add an additional restriction for the flow context:
        #   plain scalars in the flow context cannot contain ',' or '?'.
        # We also keep track of the `allow_simple_key` flag here.
        # Indentation rules are loosed for the flow context.
        chunks = []
        start_mark = self.get_mark()
        end_mark = start_mark
        indent = self.indent+1
        # We allow zero indentation for scalars, but then we need to check for
        # document separators at the beginning of the line.
        #if indent == 0:
        #    indent = 1
        spaces = []
        while True:
            length = 0
            if self.peek() == '#':
                break
            while True:
                ch = self.peek(length)
                if ch in '\0 \t\r\n\x85\u2028\u2029'    \
                        or (ch == ':' and
                                self.peek(length+1) in '\0 \t\r\n\x85\u2028\u2029'
                                      + (u',[]{}' if self.flow_level else u''))\
                        or (self.flow_level and ch in ',?[]{}'):
                    break
                length += 1
            if length == 0:
                break
            self.allow_simple_key = False
            chunks.extend(spaces)
            chunks.append(self.prefix(length))
            self.forward(length)
            end_mark = self.get_mark()
            spaces = self.scan_plain_spaces(indent, start_mark)
            if not spaces or self.peek() == '#' \
                    or (not self.flow_level and self.column < indent):
                break
        return ScalarToken(''.join(chunks), True, start_mark, end_mark)

    def scan_plain_spaces(self, indent, start_mark):
        # See the specification for details.
        # The specification is really confusing about tabs in plain scalars.
        # We just forbid them completely. Do not use tabs in YAML!
        chunks = []
        length = 0
        while self.peek(length) in ' ':
            length += 1
        whitespaces = self.prefix(length)
        self.forward(length)
        ch = self.peek()
        if ch in '\r\n\x85\u2028\u2029':
            line_break = self.scan_line_break()
            self.allow_simple_key = True
            prefix = self.prefix(3)
            if (prefix == '---' or prefix == '...')   \
                    and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                return
            breaks = []
            while self.peek() in ' \r\n\x85\u2028\u2029':
                if self.peek() == ' ':
                    self.forward()
                else:
                    breaks.append(self.scan_line_break())
                    prefix = self.prefix(3)
                    if (prefix == '---' or prefix == '...')   \
                            and self.peek(3) in '\0 \t\r\n\x85\u2028\u2029':
                        return
            if line_break != '\n':
                chunks.append(line_break)
            elif not breaks:
                chunks.append(' ')
            chunks.extend(breaks)
        elif whitespaces:
            chunks.append(whitespaces)
        return chunks

    def scan_tag_handle(self, name, start_mark):
        # See the specification for details.
        # For some strange reasons, the specification does not allow '_' in
        # tag handles. I have allowed it anyway.
        ch = self.peek()
        if ch != '!':
            raise ScannerError("while scanning a %s" % name, start_mark,
                    "expected '!', but found %r" % ch, self.get_mark())
        length = 1
        ch = self.peek(length)
        if ch != ' ':
            while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                    or ch in '-_':
                length += 1
                ch = self.peek(length)
            if ch != '!':
                self.forward(length)
                raise ScannerError("while scanning a %s" % name, start_mark,
                        "expected '!', but found %r" % ch, self.get_mark())
            length += 1
        value = self.prefix(length)
        self.forward(length)
        return value

    def scan_tag_uri(self, name, start_mark):
        # See the specification for details.
        # Note: we do not check if URI is well-formed.
        chunks = []
        length = 0
        ch = self.peek(length)
        while '0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'  \
                or ch in '-;/?:@&=+$,_.!~*\'()[]%':
            if ch == '%':
                chunks.append(self.prefix(length))
                self.forward(length)
                length = 0
                chunks.append(self.scan_uri_escapes(name, start_mark))
            else:
                length += 1
            ch = self.peek(length)
        if length:
            chunks.append(self.prefix(length))
            self.forward(length)
            length = 0
        if not chunks:
            raise ScannerError("while parsing a %s" % name, start_mark,
                    "expected URI, but found %r" % ch, self.get_mark())
        return ''.join(chunks)

    def scan_uri_escapes(self, name, start_mark):
        # See the specification for details.
        codes = []
        mark = self.get_mark()
        while self.peek() == '%':
            self.forward()
            for k in range(2):
                if self.peek(k) not in '0123456789ABCDEFabcdef':
                    raise ScannerError("while scanning a %s" % name, start_mark,
                            "expected URI escape sequence of 2 hexadecimal numbers, but found %r"
                            % self.peek(k), self.get_mark())
            codes.append(int(self.prefix(2), 16))
            self.forward(2)
        try:
            value = bytes(codes).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ScannerError("while scanning a %s" % name, start_mark, str(exc), mark)
        return value

    def scan_line_break(self):
        # Transforms:
        #   '\r\n'      :   '\n'
        #   '\r'        :   '\n'
        #   '\n'        :   '\n'
        #   '\x85'      :   '\n'
        #   '\u2028'    :   '\u2028'
        #   '\u2029     :   '\u2029'
        #   default     :   ''
        ch = self.peek()
        if ch in '\r\n\x85':
            if self.prefix(2) == '\r\n':
                self.forward(2)
            else:
                self.forward()
            return '\n'
        elif ch in '\u2028\u2029':
            self.forward()
            return ch
        return ''

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\configs.py ===
"""
    pygments.lexers.configs
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for configuration file formats.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, RegexLexer, default, words, \
    bygroups, include, using, line_re
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace, Literal, Error, Generic
from pygments.lexers.shell import BashLexer
from pygments.lexers.data import JsonLexer

__all__ = ['IniLexer', 'SystemdLexer', 'DesktopLexer', 'RegeditLexer', 'PropertiesLexer',
           'KconfigLexer', 'Cfengine3Lexer', 'ApacheConfLexer', 'SquidConfLexer',
           'NginxConfLexer', 'LighttpdConfLexer', 'DockerLexer',
           'TerraformLexer', 'TermcapLexer', 'TerminfoLexer',
           'PkgConfigLexer', 'PacmanConfLexer', 'AugeasLexer', 'TOMLLexer',
           'NestedTextLexer', 'SingularityLexer', 'UnixConfigLexer']


class IniLexer(RegexLexer):
    """
    Lexer for configuration files in INI style.
    """

    name = 'INI'
    aliases = ['ini', 'cfg', 'dosini']
    filenames = [
        '*.ini', '*.cfg', '*.inf', '.editorconfig',
    ]
    mimetypes = ['text/x-ini', 'text/inf']
    url = 'https://en.wikipedia.org/wiki/INI_file'
    version_added = ''

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'[;#].*', Comment.Single),
            (r'(\[.*?\])([ \t]*)$', bygroups(Keyword, Whitespace)),
            (r'''(.*?)([ \t]*)([=:])([ \t]*)(["'])''',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String),
             "quoted_value"),
            (r'(.*?)([ \t]*)([=:])([ \t]*)([^;#\n]*)(\\)(\s+)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String,
                      Text, Whitespace),
             "value"),
            (r'(.*?)([ \t]*)([=:])([ \t]*)([^ ;#\n]*(?: +[^ ;#\n]+)*)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String)),
            # standalone option, supported by some INI parsers
            (r'(.+?)$', Name.Attribute),
        ],
        'quoted_value': [
            (r'''([^"'\n]*)(["'])(\s*)''',
             bygroups(String, String, Whitespace), "#pop"),
            (r'[;#].*', Comment.Single),
            (r'$', String, "#pop"),
        ],
        'value': [     # line continuation
            (r'\s+', Whitespace),
            (r'(\s*)(.*)(\\)([ \t]*)',
             bygroups(Whitespace, String, Text, Whitespace)),
            (r'.*$', String, "#pop"),
        ],
    }

    def analyse_text(text):
        npos = text.find('\n')
        if npos < 3:
            return False
        if text[0] == '[' and text[npos-1] == ']':
            return 0.8
        return False


class DesktopLexer(RegexLexer):
    """
    Lexer for .desktop files.
    """

    name = 'Desktop file'
    url = "https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html"
    aliases = ['desktop']
    filenames = ['*.desktop']
    mimetypes = ['application/x-desktop']
    version_added = '2.16'

    tokens = {
        'root': [
            (r'^[ \t]*\n', Whitespace),
            (r'^(#.*)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'(\[[^\]\n]+\])(\n)', bygroups(Keyword, Whitespace)),
            (r'([-A-Za-z0-9]+)(\[[^\] \t=]+\])?([ \t]*)(=)([ \t]*)([^\n]*)([ \t\n]*\n)',
             bygroups(Name.Attribute, Name.Namespace, Whitespace, Operator, Whitespace, String, Whitespace)),
        ],
    }

    def analyse_text(text):
        if text.startswith("[Desktop Entry]"):
            return 1.0
        if re.search(r"^\[Desktop Entry\][ \t]*$", text[:500], re.MULTILINE) is not None:
            return 0.9
        return 0.0


class SystemdLexer(RegexLexer):
    """
    Lexer for systemd unit files.
    """

    name = 'Systemd'
    url = "https://www.freedesktop.org/software/systemd/man/systemd.syntax.html"
    aliases = ['systemd']
    filenames = [
        '*.service', '*.socket', '*.device', '*.mount', '*.automount',
        '*.swap', '*.target', '*.path', '*.timer', '*.slice', '*.scope',
    ]
    version_added = '2.16'

    tokens = {
        'root': [
            (r'^[ \t]*\n', Whitespace),
            (r'^([;#].*)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'(\[[^\]\n]+\])(\n)', bygroups(Keyword, Whitespace)),
            (r'([^=]+)([ \t]*)(=)([ \t]*)([^\n]*)(\\)(\n)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String,
                      Text, Whitespace),
             "value"),
            (r'([^=]+)([ \t]*)(=)([ \t]*)([^\n]*)(\n)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace, String, Whitespace)),
        ],
        'value': [
            # line continuation
            (r'^([;#].*)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'([ \t]*)([^\n]*)(\\)(\n)',
             bygroups(Whitespace, String, Text, Whitespace)),
            (r'([ \t]*)([^\n]*)(\n)',
             bygroups(Whitespace, String, Whitespace), "#pop"),
        ],
    }

    def analyse_text(text):
        if text.startswith("[Unit]"):
            return 1.0
        if re.search(r"^\[Unit\][ \t]*$", text[:500], re.MULTILINE) is not None:
            return 0.9
        return 0.0


class RegeditLexer(RegexLexer):
    """
    Lexer for Windows Registry files produced by regedit.
    """

    name = 'reg'
    url = 'http://en.wikipedia.org/wiki/Windows_Registry#.REG_files'
    aliases = ['registry']
    filenames = ['*.reg']
    mimetypes = ['text/x-windows-registry']
    version_added = '1.6'

    tokens = {
        'root': [
            (r'Windows Registry Editor.*', Text),
            (r'\s+', Whitespace),
            (r'[;#].*', Comment.Single),
            (r'(\[)(-?)(HKEY_[A-Z_]+)(.*?\])$',
             bygroups(Keyword, Operator, Name.Builtin, Keyword)),
            # String keys, which obey somewhat normal escaping
            (r'("(?:\\"|\\\\|[^"])+")([ \t]*)(=)([ \t]*)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace),
             'value'),
            # Bare keys (includes @)
            (r'(.*?)([ \t]*)(=)([ \t]*)',
             bygroups(Name.Attribute, Whitespace, Operator, Whitespace),
             'value'),
        ],
        'value': [
            (r'-', Operator, '#pop'),  # delete value
            (r'(dword|hex(?:\([0-9a-fA-F]\))?)(:)([0-9a-fA-F,]+)',
             bygroups(Name.Variable, Punctuation, Number), '#pop'),
            # As far as I know, .reg files do not support line continuation.
            (r'.+', String, '#pop'),
            default('#pop'),
        ]
    }

    def analyse_text(text):
        return text.startswith('Windows Registry Editor')


class PropertiesLexer(RegexLexer):
    """
    Lexer for configuration files in Java's properties format.

    Note: trailing whitespace counts as part of the value as per spec
    """

    name = 'Properties'
    aliases = ['properties', 'jproperties']
    filenames = ['*.properties']
    mimetypes = ['text/x-java-properties']
    url = 'https://en.wikipedia.org/wiki/.properties'
    version_added = '1.4'

    tokens = {
        'root': [
            # comments
            (r'[!#].*|/{2}.*', Comment.Single),
            # ending a comment or whitespace-only line
            (r'\n', Whitespace),
            # eat whitespace at the beginning of a line
            (r'^[^\S\n]+', Whitespace),
            # start lexing a key
            default('key'),
        ],
        'key': [
            # non-escaped key characters
            (r'[^\\:=\s]+', Name.Attribute),
            # escapes
            include('escapes'),
            # separator is the first non-escaped whitespace or colon or '=' on the line;
            # if it's whitespace, = and : are gobbled after it
            (r'([^\S\n]*)([:=])([^\S\n]*)',
             bygroups(Whitespace, Operator, Whitespace),
             ('#pop', 'value')),
            (r'[^\S\n]+', Whitespace, ('#pop', 'value')),
            # maybe we got no value after all
            (r'\n', Whitespace, '#pop'),
        ],
        'value': [
            # non-escaped value characters
            (r'[^\\\n]+', String),
            # escapes
            include('escapes'),
            # end the value on an unescaped newline
            (r'\n', Whitespace, '#pop'),
        ],
        'escapes': [
            # line continuations; these gobble whitespace at the beginning of the next line
            (r'(\\\n)([^\S\n]*)', bygroups(String.Escape, Whitespace)),
            # other escapes
            (r'\\(.|\n)', String.Escape),
        ],
    }


def _rx_indent(level):
    # Kconfig *always* interprets a tab as 8 spaces, so this is the default.
    # Edit this if you are in an environment where KconfigLexer gets expanded
    # input (tabs expanded to spaces) and the expansion tab width is != 8,
    # e.g. in connection with Trac (trac.ini, [mimeviewer], tab_width).
    # Value range here is 2 <= {tab_width} <= 8.
    tab_width = 8
    # Regex matching a given indentation {level}, assuming that indentation is
    # a multiple of {tab_width}. In other cases there might be problems.
    if tab_width == 2:
        space_repeat = '+'
    else:
        space_repeat = '{1,%d}' % (tab_width - 1)
    if level == 1:
        level_repeat = ''
    else:
        level_repeat = f'{{{level}}}'
    return rf'(?:\t| {space_repeat}\t| {{{tab_width}}}){level_repeat}.*\n'


class KconfigLexer(RegexLexer):
    """
    For Linux-style Kconfig files.
    """

    name = 'Kconfig'
    aliases = ['kconfig', 'menuconfig', 'linux-config', 'kernel-config']
    version_added = '1.6'
    # Adjust this if new kconfig file names appear in your environment
    filenames = ['Kconfig*', '*Config.in*', 'external.in*',
                 'standard-modules.in']
    mimetypes = ['text/x-kconfig']
    url = 'https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html'

    # No re.MULTILINE, indentation-aware help text needs line-by-line handling
    flags = 0

    def call_indent(level):
        # If indentation >= {level} is detected, enter state 'indent{level}'
        return (_rx_indent(level), String.Doc, f'indent{level}')

    def do_indent(level):
        # Print paragraphs of indentation level >= {level} as String.Doc,
        # ignoring blank lines. Then return to 'root' state.
        return [
            (_rx_indent(level), String.Doc),
            (r'\s*\n', Text),
            default('#pop:2')
        ]

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#.*?\n', Comment.Single),
            (words((
                'mainmenu', 'config', 'menuconfig', 'choice', 'endchoice',
                'comment', 'menu', 'endmenu', 'visible if', 'if', 'endif',
                'source', 'prompt', 'select', 'depends on', 'default',
                'range', 'option'), suffix=r'\b'),
             Keyword),
            (r'(---help---|help)[\t ]*\n', Keyword, 'help'),
            (r'(bool|tristate|string|hex|int|defconfig_list|modules|env)\b',
             Name.Builtin),
            (r'[!=&|]', Operator),
            (r'[()]', Punctuation),
            (r'[0-9]+', Number.Integer),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Double),
            (r'\S+', Text),
        ],
        # Help text is indented, multi-line and ends when a lower indentation
        # level is detected.
        'help': [
            # Skip blank lines after help token, if any
            (r'\s*\n', Text),
            # Determine the first help line's indentation level heuristically(!).
            # Attention: this is not perfect, but works for 99% of "normal"
            # indentation schemes up to a max. indentation level of 7.
            call_indent(7),
            call_indent(6),
            call_indent(5),
            call_indent(4),
            call_indent(3),
            call_indent(2),
            call_indent(1),
            default('#pop'),  # for incomplete help sections without text
        ],
        # Handle text for indentation levels 7 to 1
        'indent7': do_indent(7),
        'indent6': do_indent(6),
        'indent5': do_indent(5),
        'indent4': do_indent(4),
        'indent3': do_indent(3),
        'indent2': do_indent(2),
        'indent1': do_indent(1),
    }


class Cfengine3Lexer(RegexLexer):
    """
    Lexer for CFEngine3 policy files.
    """

    name = 'CFEngine3'
    url = 'http://cfengine.org'
    aliases = ['cfengine3', 'cf3']
    filenames = ['*.cf']
    mimetypes = []
    version_added = '1.5'

    tokens = {
        'root': [
            (r'#.*?\n', Comment),
            (r'(body)(\s+)(\S+)(\s+)(control)',
             bygroups(Keyword, Whitespace, Keyword, Whitespace, Keyword)),
            (r'(body|bundle)(\s+)(\S+)(\s+)(\w+)(\()',
             bygroups(Keyword, Whitespace, Keyword, Whitespace, Name.Function, Punctuation),
             'arglist'),
            (r'(body|bundle)(\s+)(\S+)(\s+)(\w+)',
             bygroups(Keyword, Whitespace, Keyword, Whitespace, Name.Function)),
            (r'(")([^"]+)(")(\s+)(string|slist|int|real)(\s*)(=>)(\s*)',
             bygroups(Punctuation, Name.Variable, Punctuation,
                      Whitespace, Keyword.Type, Whitespace, Operator, Whitespace)),
            (r'(\S+)(\s*)(=>)(\s*)',
             bygroups(Keyword.Reserved, Whitespace, Operator, Text)),
            (r'"', String, 'string'),
            (r'(\w+)(\()', bygroups(Name.Function, Punctuation)),
            (r'([\w.!&|()]+)(::)', bygroups(Name.Class, Punctuation)),
            (r'(\w+)(:)', bygroups(Keyword.Declaration, Punctuation)),
            (r'@[{(][^)}]+[})]', Name.Variable),
            (r'[(){},;]', Punctuation),
            (r'=>', Operator),
            (r'->', Operator),
            (r'\d+\.\d+', Number.Float),
            (r'\d+', Number.Integer),
            (r'\w+', Name.Function),
            (r'\s+', Whitespace),
        ],
        'string': [
            (r'\$[{(]', String.Interpol, 'interpol'),
            (r'\\.', String.Escape),
            (r'"', String, '#pop'),
            (r'\n', String),
            (r'.', String),
        ],
        'interpol': [
            (r'\$[{(]', String.Interpol, '#push'),
            (r'[})]', String.Interpol, '#pop'),
            (r'[^${()}]+', String.Interpol),
        ],
        'arglist': [
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'\w+', Name.Variable),
            (r'\s+', Whitespace),
        ],
    }


class ApacheConfLexer(RegexLexer):
    """
    Lexer for configuration files following the Apache config file
    format.
    """

    name = 'ApacheConf'
    aliases = ['apacheconf', 'aconf', 'apache']
    filenames = ['.htaccess', 'apache.conf', 'apache2.conf']
    mimetypes = ['text/x-apacheconf']
    url = 'https://httpd.apache.org/docs/current/configuring.html'
    version_added = '0.6'
    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#(.*\\\n)+.*$|(#.*?)$', Comment),
            (r'(<[^\s>/][^\s>]*)(?:(\s+)(.*))?(>)',
             bygroups(Name.Tag, Whitespace, String, Name.Tag)),
            (r'(</[^\s>]+)(>)',
             bygroups(Name.Tag, Name.Tag)),
            (r'[a-z]\w*', Name.Builtin, 'value'),
            (r'\.+', Text),
        ],
        'value': [
            (r'\\\n', Text),
            (r'\n+', Whitespace, '#pop'),
            (r'\\', Text),
            (r'[^\S\n]+', Whitespace),
            (r'\d+\.\d+\.\d+\.\d+(?:/\d+)?', Number),
            (r'\d+', Number),
            (r'/([*a-z0-9][*\w./-]+)', String.Other),
            (r'(on|off|none|any|all|double|email|dns|min|minimal|'
             r'os|productonly|full|emerg|alert|crit|error|warn|'
             r'notice|info|debug|registry|script|inetd|standalone|'
             r'user|group)\b', Keyword),
            (r'"([^"\\]*(?:\\(.|\n)[^"\\]*)*)"', String.Double),
            (r'[^\s"\\]+', Text)
        ],
    }


class SquidConfLexer(RegexLexer):
    """
    Lexer for squid configuration files.
    """

    name = 'SquidConf'
    url = 'http://www.squid-cache.org/'
    aliases = ['squidconf', 'squid.conf', 'squid']
    filenames = ['squid.conf']
    mimetypes = ['text/x-squidconf']
    version_added = '0.9'
    flags = re.IGNORECASE

    keywords = (
        "access_log", "acl", "always_direct", "announce_host",
        "announce_period", "announce_port", "announce_to", "anonymize_headers",
        "append_domain", "as_whois_server", "auth_param_basic",
        "authenticate_children", "authenticate_program", "authenticate_ttl",
        "broken_posts", "buffered_logs", "cache_access_log", "cache_announce",
        "cache_dir", "cache_dns_program", "cache_effective_group",
        "cache_effective_user", "cache_host", "cache_host_acl",
        "cache_host_domain", "cache_log", "cache_mem", "cache_mem_high",
        "cache_mem_low", "cache_mgr", "cachemgr_passwd", "cache_peer",
        "cache_peer_access", "cache_replacement_policy", "cache_stoplist",
        "cache_stoplist_pattern", "cache_store_log", "cache_swap",
        "cache_swap_high", "cache_swap_log", "cache_swap_low", "client_db",
        "client_lifetime", "client_netmask", "connect_timeout", "coredump_dir",
        "dead_peer_timeout", "debug_options", "delay_access", "delay_class",
        "delay_initial_bucket_level", "delay_parameters", "delay_pools",
        "deny_info", "dns_children", "dns_defnames", "dns_nameservers",
        "dns_testnames", "emulate_httpd_log", "err_html_text",
        "fake_user_agent", "firewall_ip", "forwarded_for", "forward_snmpd_port",
        "fqdncache_size", "ftpget_options", "ftpget_program", "ftp_list_width",
        "ftp_passive", "ftp_user", "half_closed_clients", "header_access",
        "header_replace", "hierarchy_stoplist", "high_response_time_warning",
        "high_page_fault_warning", "hosts_file", "htcp_port", "http_access",
        "http_anonymizer", "httpd_accel", "httpd_accel_host",
        "httpd_accel_port", "httpd_accel_uses_host_header",
        "httpd_accel_with_proxy", "http_port", "http_reply_access",
        "icp_access", "icp_hit_stale", "icp_port", "icp_query_timeout",
        "ident_lookup", "ident_lookup_access", "ident_timeout",
        "incoming_http_average", "incoming_icp_average", "inside_firewall",
        "ipcache_high", "ipcache_low", "ipcache_size", "local_domain",
        "local_ip", "logfile_rotate", "log_fqdn", "log_icp_queries",
        "log_mime_hdrs", "maximum_object_size", "maximum_single_addr_tries",
        "mcast_groups", "mcast_icp_query_timeout", "mcast_miss_addr",
        "mcast_miss_encode_key", "mcast_miss_port", "memory_pools",
        "memory_pools_limit", "memory_replacement_policy", "mime_table",
        "min_http_poll_cnt", "min_icp_poll_cnt", "minimum_direct_hops",
        "minimum_object_size", "minimum_retry_timeout", "miss_access",
        "negative_dns_ttl", "negative_ttl", "neighbor_timeout",
        "neighbor_type_domain", "netdb_high", "netdb_low", "netdb_ping_period",
        "netdb_ping_rate", "never_direct", "no_cache", "passthrough_proxy",
        "pconn_timeout", "pid_filename", "pinger_program", "positive_dns_ttl",
        "prefer_direct", "proxy_auth", "proxy_auth_realm", "query_icmp",
        "quick_abort", "quick_abort_max", "quick_abort_min",
        "quick_abort_pct", "range_offset_limit", "read_timeout",
        "redirect_children", "redirect_program",
        "redirect_rewrites_host_header", "reference_age",
        "refresh_pattern", "reload_into_ims", "request_body_max_size",
        "request_size", "request_timeout", "shutdown_lifetime",
        "single_parent_bypass", "siteselect_timeout", "snmp_access",
        "snmp_incoming_address", "snmp_port", "source_ping", "ssl_proxy",
        "store_avg_object_size", "store_objects_per_bucket",
        "strip_query_terms", "swap_level1_dirs", "swap_level2_dirs",
        "tcp_incoming_address", "tcp_outgoing_address", "tcp_recv_bufsize",
        "test_reachability", "udp_hit_obj", "udp_hit_obj_size",
        "udp_incoming_address", "udp_outgoing_address", "unique_hostname",
        "unlinkd_program", "uri_whitespace", "useragent_log",
        "visible_hostname", "wais_relay", "wais_relay_host", "wais_relay_port",
    )

    opts = (
        "proxy-only", "weight", "ttl", "no-query", "default", "round-robin",
        "multicast-responder", "on", "off", "all", "deny", "allow", "via",
        "parent", "no-digest", "heap", "lru", "realm", "children", "q1", "q2",
        "credentialsttl", "none", "disable", "offline_toggle", "diskd",
    )

    actions = (
        "shutdown", "info", "parameter", "server_list", "client_list",
        r'squid.conf',
    )

    actions_stats = (
        "objects", "vm_objects", "utilization", "ipcache", "fqdncache", "dns",
        "redirector", "io", "reply_headers", "filedescriptors", "netdb",
    )

    actions_log = ("status", "enable", "disable", "clear")

    acls = (
        "url_regex", "urlpath_regex", "referer_regex", "port", "proto",
        "req_mime_type", "rep_mime_type", "method", "browser", "user", "src",
        "dst", "time", "dstdomain", "ident", "snmp_community",
    )

    ipv4_group = r'(\d+|0x[0-9a-f]+)'
    ipv4 = rf'({ipv4_group}(\.{ipv4_group}){{3}})'
    ipv6_group = r'([0-9a-f]{0,4})'
    ipv6 = rf'({ipv6_group}(:{ipv6_group}){{1,7}})'
    bare_ip = rf'({ipv4}|{ipv6})'
    # XXX: /integer is a subnet mark, but what is /IP ?
    # There is no test where it is used.
    ip = rf'{bare_ip}(/({bare_ip}|\d+))?'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#', Comment, 'comment'),
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(opts, prefix=r'\b', suffix=r'\b'), Name.Constant),
            # Actions
            (words(actions, prefix=r'\b', suffix=r'\b'), String),
            (words(actions_stats, prefix=r'stats/', suffix=r'\b'), String),
            (words(actions_log, prefix=r'log/', suffix=r'='), String),
            (words(acls, prefix=r'\b', suffix=r'\b'), Keyword),
            (ip, Number.Float),
            (r'(?:\b\d+\b(?:-\b\d+|%)?)', Number),
            (r'\S+', Text),
        ],
        'comment': [
            (r'\s*TAG:.*', String.Escape, '#pop'),
            (r'.+', Comment, '#pop'),
            default('#pop'),
        ],
    }


class NginxConfLexer(RegexLexer):
    """
    Lexer for Nginx configuration files.
    """
    name = 'Nginx configuration file'
    url = 'http://nginx.net/'
    aliases = ['nginx']
    filenames = ['nginx.conf']
    mimetypes = ['text/x-nginx-conf']
    version_added = '0.11'

    tokens = {
        'root': [
            (r'(include)(\s+)([^\s;]+)', bygroups(Keyword, Whitespace, Name)),
            (r'[^\s;#]+', Keyword, 'stmt'),
            include('base'),
        ],
        'block': [
            (r'\}', Punctuation, '#pop:2'),
            (r'[^\s;#]+', Keyword.Namespace, 'stmt'),
            include('base'),
        ],
        'stmt': [
            (r'\{', Punctuation, 'block'),
            (r';', Punctuation, '#pop'),
            include('base'),
        ],
        'base': [
            (r'#.*\n', Comment.Single),
            (r'on|off', Name.Constant),
            (r'\$[^\s;#()]+', Name.Variable),
            (r'([a-z0-9.-]+)(:)([0-9]+)',
             bygroups(Name, Punctuation, Number.Integer)),
            (r'[a-z-]+/[a-z-+]+', String),  # mimetype
            # (r'[a-zA-Z._-]+', Keyword),
            (r'[0-9]+[km]?\b', Number.Integer),
            (r'(~)(\s*)([^\s{]+)', bygroups(Punctuation, Whitespace, String.Regex)),
            (r'[:=~]', Punctuation),
            (r'[^\s;#{}$]+', String),  # catch all
            (r'/[^\s;#]*', Name),  # pathname
            (r'\s+', Whitespace),
            (r'[$;]', Text),  # leftover characters
        ],
    }


class LighttpdConfLexer(RegexLexer):
    """
    Lexer for Lighttpd configuration files.
    """
    name = 'Lighttpd configuration file'
    url = 'http://lighttpd.net/'
    aliases = ['lighttpd', 'lighty']
    filenames = ['lighttpd.conf']
    mimetypes = ['text/x-lighttpd-conf']
    version_added = '0.11'

    tokens = {
        'root': [
            (r'#.*\n', Comment.Single),
            (r'/\S*', Name),  # pathname
            (r'[a-zA-Z._-]+', Keyword),
            (r'\d+\.\d+\.\d+\.\d+(?:/\d+)?', Number),
            (r'[0-9]+', Number),
            (r'=>|=~|\+=|==|=|\+', Operator),
            (r'\$[A-Z]+', Name.Builtin),
            (r'[(){}\[\],]', Punctuation),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', String.Double),
            (r'\s+', Whitespace),
        ],

    }


class DockerLexer(RegexLexer):
    """
    Lexer for Docker configuration files.
    """
    name = 'Docker'
    url = 'http://docker.io'
    aliases = ['docker', 'dockerfile']
    filenames = ['Dockerfile', '*.docker']
    mimetypes = ['text/x-dockerfile-config']
    version_added = '2.0'

    _keywords = (r'(?:MAINTAINER|EXPOSE|WORKDIR|USER|STOPSIGNAL)')
    _bash_keywords = (r'(?:RUN|CMD|ENTRYPOINT|ENV|ARG|LABEL|ADD|COPY)')
    _lb = r'(?:\s*\\?\s*)'  # dockerfile line break regex
    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            (r'#.*', Comment),
            (r'(FROM)([ \t]*)(\S*)([ \t]*)(?:(AS)([ \t]*)(\S*))?',
             bygroups(Keyword, Whitespace, String, Whitespace, Keyword, Whitespace, String)),
            (rf'(ONBUILD)(\s+)({_lb})', bygroups(Keyword, Whitespace, using(BashLexer))),
            (rf'(HEALTHCHECK)(\s+)(({_lb}--\w+=\w+{_lb})*)',
                bygroups(Keyword, Whitespace, using(BashLexer))),
            (rf'(VOLUME|ENTRYPOINT|CMD|SHELL)(\s+)({_lb})(\[.*?\])',
                bygroups(Keyword, Whitespace, using(BashLexer), using(JsonLexer))),
            (rf'(LABEL|ENV|ARG)(\s+)(({_lb}\w+=\w+{_lb})*)',
                bygroups(Keyword, Whitespace, using(BashLexer))),
            (rf'({_keywords}|VOLUME)\b(\s+)(.*)', bygroups(Keyword, Whitespace, String)),
            (rf'({_bash_keywords})(\s+)', bygroups(Keyword, Whitespace)),
            (r'(.*\\\n)*.+', using(BashLexer)),
        ]
    }


class TerraformLexer(ExtendedRegexLexer):
    """
    Lexer for terraformi ``.tf`` files.
    """

    name = 'Terraform'
    url = 'https://www.terraform.io/'
    aliases = ['terraform', 'tf', 'hcl']
    filenames = ['*.tf', '*.hcl']
    mimetypes = ['application/x-tf', 'application/x-terraform']
    version_added = '2.1'

    classes = ('backend', 'data', 'module', 'output', 'provider',
               'provisioner', 'resource', 'variable')
    classes_re = "({})".format(('|').join(classes))

    types = ('string', 'number', 'bool', 'list', 'tuple', 'map', 'set', 'object', 'null')

    numeric_functions = ('abs', 'ceil', 'floor', 'log', 'max',
                         'mix', 'parseint', 'pow', 'signum')

    string_functions = ('chomp', 'format', 'formatlist', 'indent',
                        'join', 'lower', 'regex', 'regexall', 'replace',
                        'split', 'strrev', 'substr', 'title', 'trim',
                        'trimprefix', 'trimsuffix', 'trimspace', 'upper'
                        )

    collection_functions = ('alltrue', 'anytrue', 'chunklist', 'coalesce',
                            'coalescelist', 'compact', 'concat', 'contains',
                            'distinct', 'element', 'flatten', 'index', 'keys',
                            'length', 'list', 'lookup', 'map', 'matchkeys',
                            'merge', 'range', 'reverse', 'setintersection',
                            'setproduct', 'setsubtract', 'setunion', 'slice',
                            'sort', 'sum', 'transpose', 'values', 'zipmap'
                            )

    encoding_functions = ('base64decode', 'base64encode', 'base64gzip',
                          'csvdecode', 'jsondecode', 'jsonencode', 'textdecodebase64',
                          'textencodebase64', 'urlencode', 'yamldecode', 'yamlencode')

    filesystem_functions = ('abspath', 'dirname', 'pathexpand', 'basename',
                            'file', 'fileexists', 'fileset', 'filebase64', 'templatefile')

    date_time_functions = ('formatdate', 'timeadd', 'timestamp')

    hash_crypto_functions = ('base64sha256', 'base64sha512', 'bcrypt', 'filebase64sha256',
                             'filebase64sha512', 'filemd5', 'filesha1', 'filesha256', 'filesha512',
                             'md5', 'rsadecrypt', 'sha1', 'sha256', 'sha512', 'uuid', 'uuidv5')

    ip_network_functions = ('cidrhost', 'cidrnetmask', 'cidrsubnet', 'cidrsubnets')

    type_conversion_functions = ('can', 'defaults', 'tobool', 'tolist', 'tomap',
                                 'tonumber', 'toset', 'tostring', 'try')

    builtins = numeric_functions + string_functions + collection_functions + encoding_functions +\
        filesystem_functions + date_time_functions + hash_crypto_functions + ip_network_functions +\
        type_conversion_functions
    builtins_re = "({})".format(('|').join(builtins))

    def heredoc_callback(self, match, ctx):
        # Parse a terraform heredoc
        # match: 1 = <<[-]?, 2 = name 3 = rest of line

        start = match.start(1)
        yield start, Operator, match.group(1)        # <<[-]?
        yield match.start(2), String.Delimiter, match.group(2)  # heredoc name

        ctx.pos = match.start(3)
        ctx.end = match.end(3)
        yield ctx.pos, String.Heredoc, match.group(3)
        ctx.pos = match.end()

        hdname = match.group(2)
        tolerant = True  # leading whitespace is always accepted

        lines = []

        for match in line_re.finditer(ctx.text, ctx.pos):
            if tolerant:
                check = match.group().strip()
            else:
                check = match.group().rstrip()
            if check == hdname:
                for amatch in lines:
                    yield amatch.start(), String.Heredoc, amatch.group()
                yield match.start(), String.Delimiter, match.group()
                ctx.pos = match.end()
                break
            else:
                lines.append(match)
        else:
            # end of heredoc not found -- error!
            for amatch in lines:
                yield amatch.start(), Error, amatch.group()
        ctx.end = len(ctx.text)

    tokens = {
        'root': [
            include('basic'),
            include('whitespace'),

            # Strings
            (r'(".*")', bygroups(String.Double)),

            # Constants
            (words(('true', 'false'), prefix=r'\b', suffix=r'\b'), Name.Constant),

            # Types
            (words(types, prefix=r'\b', suffix=r'\b'), Keyword.Type),

            include('identifier'),
            include('punctuation'),
            (r'[0-9]+', Number),
        ],
        'basic': [
            (r'\s*/\*', Comment.Multiline, 'comment'),
            (r'\s*(#|//).*\n', Comment.Single),
            include('whitespace'),

            # e.g. terraform {
            # e.g. egress {
            (r'(\s*)([0-9a-zA-Z-_]+)(\s*)(=?)(\s*)(\{)',
             bygroups(Whitespace, Name.Builtin, Whitespace, Operator, Whitespace, Punctuation)),

            # Assignment with attributes, e.g. something = ...
            (r'(\s*)([0-9a-zA-Z-_]+)(\s*)(=)(\s*)',
             bygroups(Whitespace, Name.Attribute, Whitespace, Operator, Whitespace)),

            # Assignment with environment variables and similar, e.g. "something" = ...
            # or key value assignment, e.g. "SlotName" : ...
            (r'(\s*)("\S+")(\s*)([=:])(\s*)',
             bygroups(Whitespace, Literal.String.Double, Whitespace, Operator, Whitespace)),

            # Functions, e.g. jsonencode(element("value"))
            (builtins_re + r'(\()', bygroups(Name.Function, Punctuation)),

            # List of attributes, e.g. ignore_changes = [last_modified, filename]
            (r'(\[)([a-z_,\s]+)(\])', bygroups(Punctuation, Name.Builtin, Punctuation)),

            # e.g. resource "aws_security_group" "allow_tls" {
            # e.g. backend "consul" {
            (classes_re + r'(\s+)("[0-9a-zA-Z-_]+")?(\s*)("[0-9a-zA-Z-_]+")(\s+)(\{)',
             bygroups(Keyword.Reserved, Whitespace, Name.Class, Whitespace, Name.Variable, Whitespace, Punctuation)),

            # here-doc style delimited strings
            (r'(<<-?)\s*([a-zA-Z_]\w*)(.*?\n)', heredoc_callback),
        ],
        'identifier': [
            (r'\b(var\.[0-9a-zA-Z-_\.\[\]]+)\b', bygroups(Name.Variable)),
            (r'\b([0-9a-zA-Z-_\[\]]+\.[0-9a-zA-Z-_\.\[\]]+)\b',
             bygroups(Name.Variable)),
        ],
        'punctuation': [
            (r'[\[\]()\{\},.?:!=]', Punctuation),
        ],
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'(\\)(\n)', bygroups(Text, Whitespace)),
        ],
    }


class TermcapLexer(RegexLexer):
    """
    Lexer for termcap database source.

    This is very simple and minimal.
    """
    name = 'Termcap'
    aliases = ['termcap']
    filenames = ['termcap', 'termcap.src']
    mimetypes = []
    url = 'https://en.wikipedia.org/wiki/Termcap'
    version_added = '2.1'

    # NOTE:
    #   * multiline with trailing backslash
    #   * separator is ':'
    #   * to embed colon as data, we must use \072
    #   * space after separator is not allowed (mayve)
    tokens = {
        'root': [
            (r'^#.*', Comment),
            (r'^[^\s#:|]+', Name.Tag, 'names'),
            (r'\s+', Whitespace),
        ],
        'names': [
            (r'\n', Whitespace, '#pop'),
            (r':', Punctuation, 'defs'),
            (r'\|', Punctuation),
            (r'[^:|]+', Name.Attribute),
        ],
        'defs': [
            (r'(\\)(\n[ \t]*)', bygroups(Text, Whitespace)),
            (r'\n[ \t]*', Whitespace, '#pop:2'),
            (r'(#)([0-9]+)', bygroups(Operator, Number)),
            (r'=', Operator, 'data'),
            (r':', Punctuation),
            (r'[^\s:=#]+', Name.Class),
        ],
        'data': [
            (r'\\072', Literal),
            (r':', Punctuation, '#pop'),
            (r'[^:\\]+', Literal),  # for performance
            (r'.', Literal),
        ],
    }


class TerminfoLexer(RegexLexer):
    """
    Lexer for terminfo database source.

    This is very simple and minimal.
    """
    name = 'Terminfo'
    aliases = ['terminfo']
    filenames = ['terminfo', 'terminfo.src']
    mimetypes = []
    url = 'https://en.wikipedia.org/wiki/Terminfo'
    version_added = '2.1'

    # NOTE:
    #   * multiline with leading whitespace
    #   * separator is ','
    #   * to embed comma as data, we can use \,
    #   * space after separator is allowed
    tokens = {
        'root': [
            (r'^#.*$', Comment),
            (r'^[^\s#,|]+', Name.Tag, 'names'),
            (r'\s+', Whitespace),
        ],
        'names': [
            (r'\n', Whitespace, '#pop'),
            (r'(,)([ \t]*)', bygroups(Punctuation, Whitespace), 'defs'),
            (r'\|', Punctuation),
            (r'[^,|]+', Name.Attribute),
        ],
        'defs': [
            (r'\n[ \t]+', Whitespace),
            (r'\n', Whitespace, '#pop:2'),
            (r'(#)([0-9]+)', bygroups(Operator, Number)),
            (r'=', Operator, 'data'),
            (r'(,)([ \t]*)', bygroups(Punctuation, Whitespace)),
            (r'[^\s,=#]+', Name.Class),
        ],
        'data': [
            (r'\\[,\\]', Literal),
            (r'(,)([ \t]*)', bygroups(Punctuation, Whitespace), '#pop'),
            (r'[^\\,]+', Literal),  # for performance
            (r'.', Literal),
        ],
    }


class PkgConfigLexer(RegexLexer):
    """
    Lexer for pkg-config
    (see also `manual page <http://linux.die.net/man/1/pkg-config>`_).
    """

    name = 'PkgConfig'
    url = 'http://www.freedesktop.org/wiki/Software/pkg-config/'
    aliases = ['pkgconfig']
    filenames = ['*.pc']
    mimetypes = []
    version_added = '2.1'

    tokens = {
        'root': [
            (r'#.*$', Comment.Single),

            # variable definitions
            (r'^(\w+)(=)', bygroups(Name.Attribute, Operator)),

            # keyword lines
            (r'^([\w.]+)(:)',
             bygroups(Name.Tag, Punctuation), 'spvalue'),

            # variable references
            include('interp'),

            # fallback
            (r'\s+', Whitespace),
            (r'[^${}#=:\n.]+', Text),
            (r'.', Text),
        ],
        'interp': [
            # you can escape literal "$" as "$$"
            (r'\$\$', Text),

            # variable references
            (r'\$\{', String.Interpol, 'curly'),
        ],
        'curly': [
            (r'\}', String.Interpol, '#pop'),
            (r'\w+', Name.Attribute),
        ],
        'spvalue': [
            include('interp'),

            (r'#.*$', Comment.Single, '#pop'),
            (r'\n', Whitespace, '#pop'),

            # fallback
            (r'\s+', Whitespace),
            (r'[^${}#\n\s]+', Text),
            (r'.', Text),
        ],
    }


class PacmanConfLexer(RegexLexer):
    """
    Lexer for pacman.conf.

    Actually, IniLexer works almost fine for this format,
    but it yield error token. It is because pacman.conf has
    a form without assignment like:

        UseSyslog
        Color
        TotalDownload
        CheckSpace
        VerbosePkgLists

    These are flags to switch on.
    """

    name = 'PacmanConf'
    url = 'https://www.archlinux.org/pacman/pacman.conf.5.html'
    aliases = ['pacmanconf']
    filenames = ['pacman.conf']
    mimetypes = []
    version_added = '2.1'

    tokens = {
        'root': [
            # comment
            (r'#.*$', Comment.Single),

            # section header
            (r'^(\s*)(\[.*?\])(\s*)$', bygroups(Whitespace, Keyword, Whitespace)),

            # variable definitions
            # (Leading space is allowed...)
            (r'(\w+)(\s*)(=)',
             bygroups(Name.Attribute, Whitespace, Operator)),

            # flags to on
            (r'^(\s*)(\w+)(\s*)$',
             bygroups(Whitespace, Name.Attribute, Whitespace)),

            # built-in special values
            (words((
                '$repo',  # repository
                '$arch',  # architecture
                '%o',     # outfile
                '%u',     # url
                ), suffix=r'\b'),
             Name.Variable),

            # fallback
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
    }


class AugeasLexer(RegexLexer):
    """
    Lexer for Augeas.
    """
    name = 'Augeas'
    url = 'http://augeas.net'
    aliases = ['augeas']
    filenames = ['*.aug']
    version_added = '2.4'

    tokens = {
        'root': [
            (r'(module)(\s*)([^\s=]+)', bygroups(Keyword.Namespace, Whitespace, Name.Namespace)),
            (r'(let)(\s*)([^\s=]+)', bygroups(Keyword.Declaration, Whitespace, Name.Variable)),
            (r'(del|store|value|counter|seq|key|label|autoload|incl|excl|transform|test|get|put)(\s+)', bygroups(Name.Builtin, Whitespace)),
            (r'(\()([^:]+)(\:)(unit|string|regexp|lens|tree|filter)(\))', bygroups(Punctuation, Name.Variable, Punctuation, Keyword.Type, Punctuation)),
            (r'\(\*', Comment.Multiline, 'comment'),
            (r'[*+\-.;=?|]', Operator),
            (r'[()\[\]{}]', Operator),
            (r'"', String.Double, 'string'),
            (r'\/', String.Regex, 'regex'),
            (r'([A-Z]\w*)(\.)(\w+)', bygroups(Name.Namespace, Punctuation, Name.Variable)),
            (r'.', Name.Variable),
            (r'\s+', Whitespace),
        ],
        'string': [
            (r'\\.', String.Escape),
            (r'[^"]', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'regex': [
            (r'\\.', String.Escape),
            (r'[^/]', String.Regex),
            (r'\/', String.Regex, '#pop'),
        ],
        'comment': [
            (r'[^*)]', Comment.Multiline),
            (r'\(\*', Comment.Multiline, '#push'),
            (r'\*\)', Comment.Multiline, '#pop'),
            (r'[)*]', Comment.Multiline)
        ],
    }


class TOMLLexer(RegexLexer):
    """
    Lexer for TOML, a simple language for config files.
    """

    name = 'TOML'
    aliases = ['toml']
    filenames = ['*.toml', 'Pipfile', 'poetry.lock']
    mimetypes = ['application/toml']
    url = 'https://toml.io'
    version_added = '2.4'

    # Based on the TOML spec: https://toml.io/en/v1.0.0

    # The following is adapted from CPython's tomllib:
    _time = r"\d\d:\d\d:\d\d(\.\d+)?"
    _datetime = rf"""(?x)
                  \d\d\d\d-\d\d-\d\d # date, e.g., 1988-10-27
                (
                  [Tt ] {_time} # optional time
                  (
                    [Zz]|[+-]\d\d:\d\d # optional time offset
                  )?
                )?
              """

    tokens = {
        'root': [
            # Note that we make an effort in order to distinguish
            # moments at which we're parsing a key and moments at
            # which we're parsing a value. In the TOML code
            #
            #   1234 = 1234
            #
            # the first "1234" should be Name, the second Integer.

            # Whitespace
            (r'\s+', Whitespace),

            # Comment
            (r'#.*', Comment.Single),

            # Assignment keys
            include('key'),

            # After "=", find a value
            (r'(=)(\s*)', bygroups(Operator, Whitespace), 'value'),

            # Table header
            (r'\[\[?', Keyword, 'table-key'),
        ],
        'key': [
            # Start of bare key (only ASCII is allowed here).
            (r'[A-Za-z0-9_-]+', Name),
            # Quoted key
            (r'"', String.Double, 'basic-string'),
            (r"'", String.Single, 'literal-string'),
            # Dots act as separators in keys
            (r'\.', Punctuation),
        ],
        'table-key': [
            # This is like 'key', but highlights the name components
            # and separating dots as Keyword because it looks better
            # when the whole table header is Keyword. We do highlight
            # strings as strings though.
            # Start of bare key (only ASCII is allowed here).
            (r'[A-Za-z0-9_-]+', Keyword),
            (r'"', String.Double, 'basic-string'),
            (r"'", String.Single, 'literal-string'),
            (r'\.', Keyword),
            (r'\]\]?', Keyword, '#pop'),

            # Inline whitespace allowed
            (r'[ \t]+', Whitespace),
        ],
        'value': [
            # Datetime, baretime
            (_datetime, Literal.Date, '#pop'),
            (_time, Literal.Date, '#pop'),

            # Recognize as float if there is a fractional part
            # and/or an exponent.
            (r'[+-]?\d[0-9_]*[eE][+-]?\d[0-9_]*', Number.Float, '#pop'),
            (r'[+-]?\d[0-9_]*\.\d[0-9_]*([eE][+-]?\d[0-9_]*)?',
             Number.Float, '#pop'),

            # Infinities and NaN
            (r'[+-]?(inf|nan)', Number.Float, '#pop'),

            # Integers
            (r'-?0b[01_]+', Number.Bin, '#pop'),
            (r'-?0o[0-7_]+', Number.Oct, '#pop'),
            (r'-?0x[0-9a-fA-F_]+', Number.Hex, '#pop'),
            (r'[+-]?[0-9_]+', Number.Integer, '#pop'),

            # Strings
            (r'"""', String.Double, ('#pop', 'multiline-basic-string')),
            (r'"', String.Double, ('#pop', 'basic-string')),
            (r"'''", String.Single, ('#pop', 'multiline-literal-string')),
            (r"'", String.Single, ('#pop', 'literal-string')),

            # Booleans
            (r'true|false', Keyword.Constant, '#pop'),

            # Start of array
            (r'\[', Punctuation, ('#pop', 'array')),

            # Start of inline table
            (r'\{', Punctuation, ('#pop', 'inline-table')),
        ],
        'array': [
            # Whitespace, including newlines, is ignored inside arrays,
            # and comments are allowed.
            (r'\s+', Whitespace),
            (r'#.*', Comment.Single),

            # Delimiters
            (r',', Punctuation),

            # End of array
            (r'\]', Punctuation, '#pop'),

            # Parse a value and come back
            default('value'),
        ],
        'inline-table': [
            # Note that unlike inline arrays, inline tables do not
            # allow newlines or comments.
            (r'[ \t]+', Whitespace),

            # Keys
            include('key'),

            # Values
            (r'(=)(\s*)', bygroups(Punctuation, Whitespace), 'value'),

            # Delimiters
            (r',', Punctuation),

            # End of inline table
            (r'\}', Punctuation, '#pop'),
        ],
        'basic-string': [
            (r'"', String.Double, '#pop'),
            include('escapes'),
            (r'[^"\\]+', String.Double),
        ],
        'literal-string': [
            (r".*?'", String.Single, '#pop'),
        ],
        'multiline-basic-string': [
            (r'"""', String.Double, '#pop'),
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),
            include('escapes'),
            (r'[^"\\]+', String.Double),
            (r'"', String.Double),
        ],
        'multiline-literal-string': [
            (r"'''", String.Single, '#pop'),
            (r"[^']+", String.Single),
            (r"'", String.Single),
        ],
        'escapes': [
            (r'\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}', String.Escape),
            (r'\\.', String.Escape),
        ],
    }

class NestedTextLexer(RegexLexer):
    """
    Lexer for *NextedText*, a human-friendly data format.

    .. versionchanged:: 2.16
        Added support for *NextedText* v3.0.
    """

    name = 'NestedText'
    url = 'https://nestedtext.org'
    aliases = ['nestedtext', 'nt']
    filenames = ['*.nt']
    version_added = '2.9'

    tokens = {
        'root': [
            # Comment: # ...
            (r'^([ ]*)(#.*)$', bygroups(Whitespace, Comment)),

            # Inline dictionary: {...}
            (r'^([ ]*)(\{)', bygroups(Whitespace, Punctuation), 'inline_dict'),

            # Inline list: [...]
            (r'^([ ]*)(\[)', bygroups(Whitespace, Punctuation), 'inline_list'),

            # empty multiline string item: >
            (r'^([ ]*)(>)$', bygroups(Whitespace, Punctuation)),

            # multiline string item: > ...
            (r'^([ ]*)(>)( )(.*?)([ \t]*)$', bygroups(Whitespace, Punctuation, Whitespace, Text, Whitespace)),

            # empty list item: -
            (r'^([ ]*)(-)$', bygroups(Whitespace, Punctuation)),

            # list item: - ...
            (r'^([ ]*)(-)( )(.*?)([ \t]*)$', bygroups(Whitespace, Punctuation, Whitespace, Text, Whitespace)),

            # empty multiline key item: :
            (r'^([ ]*)(:)$', bygroups(Whitespace, Punctuation)),

            # multiline key item: : ...
            (r'^([ ]*)(:)( )([^\n]*?)([ \t]*)$', bygroups(Whitespace, Punctuation, Whitespace, Name.Tag, Whitespace)),

            # empty dict key item: ...:
            (r'^([ ]*)([^\{\[\s].*?)(:)$', bygroups(Whitespace, Name.Tag, Punctuation)),

            # dict key item: ...: ...
            (r'^([ ]*)([^\{\[\s].*?)(:)( )(.*?)([ \t]*)$', bygroups(Whitespace, Name.Tag, Punctuation, Whitespace, Text, Whitespace)),
        ],
        'inline_list': [
            include('whitespace'),
            (r'[^\{\}\[\],\s]+', Text),
            include('inline_value'),
            (r',', Punctuation),
            (r'\]', Punctuation, '#pop'),
            (r'\n', Error, '#pop'),
        ],
        'inline_dict': [
            include('whitespace'),
            (r'[^\{\}\[\],:\s]+', Name.Tag),
            (r':', Punctuation, 'inline_dict_value'),
            (r'\}', Punctuation, '#pop'),
            (r'\n', Error, '#pop'),
        ],
        'inline_dict_value': [
            include('whitespace'),
            (r'[^\{\}\[\],:\s]+', Text),
            include('inline_value'),
            (r',', Punctuation, '#pop'),
            (r'\}', Punctuation, '#pop:2'),
        ],
        'inline_value': [
            include('whitespace'),
            (r'\{', Punctuation, 'inline_dict'),
            (r'\[', Punctuation, 'inline_list'),
        ],
        'whitespace': [
            (r'[ \t]+', Whitespace),
        ],
    }


class SingularityLexer(RegexLexer):
    """
    Lexer for Singularity definition files.
    """

    name = 'Singularity'
    url = 'https://www.sylabs.io/guides/3.0/user-guide/definition_files.html'
    aliases = ['singularity']
    filenames = ['*.def', 'Singularity']
    version_added = '2.6'
    flags = re.IGNORECASE | re.MULTILINE | re.DOTALL

    _headers = r'^(\s*)(bootstrap|from|osversion|mirrorurl|include|registry|namespace|includecmd)(:)'
    _section = r'^(%(?:pre|post|setup|environment|help|labels|test|runscript|files|startscript))(\s*)'
    _appsect = r'^(%app(?:install|help|run|labels|env|test|files))(\s*)'

    tokens = {
        'root': [
            (_section, bygroups(Generic.Heading, Whitespace), 'script'),
            (_appsect, bygroups(Generic.Heading, Whitespace), 'script'),
            (_headers, bygroups(Whitespace, Keyword, Text)),
            (r'\s*#.*?\n', Comment),
            (r'\b(([0-9]+\.?[0-9]*)|(\.[0-9]+))\b', Number),
            (r'[ \t]+', Whitespace),
            (r'(?!^\s*%).', Text),
        ],
        'script': [
            (r'(.+?(?=^\s*%))|(.*)', using(BashLexer), '#pop'),
        ],
    }

    def analyse_text(text):
        """This is a quite simple script file, but there are a few keywords
        which seem unique to this language."""
        result = 0
        if re.search(r'\b(?:osversion|includecmd|mirrorurl)\b', text, re.IGNORECASE):
            result += 0.5

        if re.search(SingularityLexer._section[1:], text):
            result += 0.49

        return result


class UnixConfigLexer(RegexLexer):
    """
    Lexer for Unix/Linux config files using colon-separated values, e.g.

    * ``/etc/group``
    * ``/etc/passwd``
    * ``/etc/shadow``
    """

    name = 'Unix/Linux config files'
    aliases = ['unixconfig', 'linuxconfig']
    filenames = []
    url = 'https://en.wikipedia.org/wiki/Configuration_file#Unix_and_Unix-like_operating_systems'
    version_added = '2.12'

    tokens = {
        'root': [
            (r'^#.*', Comment),
            (r'\n', Whitespace),
            (r':', Punctuation),
            (r'[0-9]+', Number),
            (r'((?!\n)[a-zA-Z0-9\_\-\s\(\),]){2,}', Text),
            (r'[^:\n]+', String),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\mplot3d\art3d.py ===
# art3d.py, original mplot3d version by John Porter
# Parts rewritten by Reinier Heeres <reinier@heeres.eu>
# Minor additions by Ben Axelrod <baxelrod@coroware.com>

"""
Module containing 3D artist code and functions to convert 2D
artists into 3D versions which can be added to an Axes3D.
"""

import math

import numpy as np

from contextlib import contextmanager

from matplotlib import (
    _api, artist, cbook, colors as mcolors, lines, text as mtext,
    path as mpath)
from matplotlib.collections import (
    Collection, LineCollection, PolyCollection, PatchCollection, PathCollection)
from matplotlib.colors import Normalize
from matplotlib.patches import Patch
from . import proj3d


def _norm_angle(a):
    """Return the given angle normalized to -180 < *a* <= 180 degrees."""
    a = (a + 360) % 360
    if a > 180:
        a = a - 360
    return a


def _norm_text_angle(a):
    """Return the given angle normalized to -90 < *a* <= 90 degrees."""
    a = (a + 180) % 180
    if a > 90:
        a = a - 180
    return a


def get_dir_vector(zdir):
    """
    Return a direction vector.

    Parameters
    ----------
    zdir : {'x', 'y', 'z', None, 3-tuple}
        The direction. Possible values are:

        - 'x': equivalent to (1, 0, 0)
        - 'y': equivalent to (0, 1, 0)
        - 'z': equivalent to (0, 0, 1)
        - *None*: equivalent to (0, 0, 0)
        - an iterable (x, y, z) is converted to an array

    Returns
    -------
    x, y, z : array
        The direction vector.
    """
    if zdir == 'x':
        return np.array((1, 0, 0))
    elif zdir == 'y':
        return np.array((0, 1, 0))
    elif zdir == 'z':
        return np.array((0, 0, 1))
    elif zdir is None:
        return np.array((0, 0, 0))
    elif np.iterable(zdir) and len(zdir) == 3:
        return np.array(zdir)
    else:
        raise ValueError("'x', 'y', 'z', None or vector of length 3 expected")


def _viewlim_mask(xs, ys, zs, axes):
    """
    Return original points with points outside the axes view limits masked.

    Parameters
    ----------
    xs, ys, zs : array-like
        The points to mask.
    axes : Axes3D
        The axes to use for the view limits.

    Returns
    -------
    xs_masked, ys_masked, zs_masked : np.ma.array
        The masked points.
    """
    mask = np.logical_or.reduce((xs < axes.xy_viewLim.xmin,
                                 xs > axes.xy_viewLim.xmax,
                                 ys < axes.xy_viewLim.ymin,
                                 ys > axes.xy_viewLim.ymax,
                                 zs < axes.zz_viewLim.xmin,
                                 zs > axes.zz_viewLim.xmax))
    xs_masked = np.ma.array(xs, mask=mask)
    ys_masked = np.ma.array(ys, mask=mask)
    zs_masked = np.ma.array(zs, mask=mask)
    return xs_masked, ys_masked, zs_masked


class Text3D(mtext.Text):
    """
    Text object with 3D position and direction.

    Parameters
    ----------
    x, y, z : float
        The position of the text.
    text : str
        The text string to display.
    zdir : {'x', 'y', 'z', None, 3-tuple}
        The direction of the text. See `.get_dir_vector` for a description of
        the values.
    axlim_clip : bool, default: False
        Whether to hide text outside the axes view limits.

    Other Parameters
    ----------------
    **kwargs
         All other parameters are passed on to `~matplotlib.text.Text`.
    """

    def __init__(self, x=0, y=0, z=0, text='', zdir='z', axlim_clip=False,
                 **kwargs):
        mtext.Text.__init__(self, x, y, text, **kwargs)
        self.set_3d_properties(z, zdir, axlim_clip)

    def get_position_3d(self):
        """Return the (x, y, z) position of the text."""
        return self._x, self._y, self._z

    def set_position_3d(self, xyz, zdir=None):
        """
        Set the (*x*, *y*, *z*) position of the text.

        Parameters
        ----------
        xyz : (float, float, float)
            The position in 3D space.
        zdir : {'x', 'y', 'z', None, 3-tuple}
            The direction of the text. If unspecified, the *zdir* will not be
            changed. See `.get_dir_vector` for a description of the values.
        """
        super().set_position(xyz[:2])
        self.set_z(xyz[2])
        if zdir is not None:
            self._dir_vec = get_dir_vector(zdir)

    def set_z(self, z):
        """
        Set the *z* position of the text.

        Parameters
        ----------
        z : float
        """
        self._z = z
        self.stale = True

    def set_3d_properties(self, z=0, zdir='z', axlim_clip=False):
        """
        Set the *z* position and direction of the text.

        Parameters
        ----------
        z : float
            The z-position in 3D space.
        zdir : {'x', 'y', 'z', 3-tuple}
            The direction of the text. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide text outside the axes view limits.
        """
        self._z = z
        self._dir_vec = get_dir_vector(zdir)
        self._axlim_clip = axlim_clip
        self.stale = True

    @artist.allow_rasterization
    def draw(self, renderer):
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(self._x, self._y, self._z, self.axes)
            position3d = np.ma.row_stack((xs, ys, zs)).ravel().filled(np.nan)
        else:
            xs, ys, zs = self._x, self._y, self._z
            position3d = np.asanyarray([xs, ys, zs])

        proj = proj3d._proj_trans_points(
            [position3d, position3d + self._dir_vec], self.axes.M)
        dx = proj[0][1] - proj[0][0]
        dy = proj[1][1] - proj[1][0]
        angle = math.degrees(math.atan2(dy, dx))
        with cbook._setattr_cm(self, _x=proj[0][0], _y=proj[1][0],
                               _rotation=_norm_text_angle(angle)):
            mtext.Text.draw(self, renderer)
        self.stale = False

    def get_tightbbox(self, renderer=None):
        # Overwriting the 2d Text behavior which is not valid for 3d.
        # For now, just return None to exclude from layout calculation.
        return None


def text_2d_to_3d(obj, z=0, zdir='z', axlim_clip=False):
    """
    Convert a `.Text` to a `.Text3D` object.

    Parameters
    ----------
    z : float
        The z-position in 3D space.
    zdir : {'x', 'y', 'z', 3-tuple}
        The direction of the text. Default: 'z'.
        See `.get_dir_vector` for a description of the values.
    axlim_clip : bool, default: False
        Whether to hide text outside the axes view limits.
    """
    obj.__class__ = Text3D
    obj.set_3d_properties(z, zdir, axlim_clip)


class Line3D(lines.Line2D):
    """
    3D line object.

    .. note:: Use `get_data_3d` to obtain the data associated with the line.
            `~.Line2D.get_data`, `~.Line2D.get_xdata`, and `~.Line2D.get_ydata` return
            the x- and y-coordinates of the projected 2D-line, not the x- and y-data of
            the 3D-line. Similarly, use `set_data_3d` to set the data, not
            `~.Line2D.set_data`, `~.Line2D.set_xdata`, and `~.Line2D.set_ydata`.
    """

    def __init__(self, xs, ys, zs, *args, axlim_clip=False, **kwargs):
        """

        Parameters
        ----------
        xs : array-like
            The x-data to be plotted.
        ys : array-like
            The y-data to be plotted.
        zs : array-like
            The z-data to be plotted.
        *args, **kwargs
            Additional arguments are passed to `~matplotlib.lines.Line2D`.
        """
        super().__init__([], [], *args, **kwargs)
        self.set_data_3d(xs, ys, zs)
        self._axlim_clip = axlim_clip

    def set_3d_properties(self, zs=0, zdir='z', axlim_clip=False):
        """
        Set the *z* position and direction of the line.

        Parameters
        ----------
        zs : float or array of floats
            The location along the *zdir* axis in 3D space to position the
            line.
        zdir : {'x', 'y', 'z'}
            Plane to plot line orthogonal to. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide lines with an endpoint outside the axes view limits.
        """
        xs = self.get_xdata()
        ys = self.get_ydata()
        zs = cbook._to_unmasked_float_array(zs).ravel()
        zs = np.broadcast_to(zs, len(xs))
        self._verts3d = juggle_axes(xs, ys, zs, zdir)
        self._axlim_clip = axlim_clip
        self.stale = True

    def set_data_3d(self, *args):
        """
        Set the x, y and z data

        Parameters
        ----------
        x : array-like
            The x-data to be plotted.
        y : array-like
            The y-data to be plotted.
        z : array-like
            The z-data to be plotted.

        Notes
        -----
        Accepts x, y, z arguments or a single array-like (x, y, z)
        """
        if len(args) == 1:
            args = args[0]
        for name, xyz in zip('xyz', args):
            if not np.iterable(xyz):
                raise RuntimeError(f'{name} must be a sequence')
        self._verts3d = args
        self.stale = True

    def get_data_3d(self):
        """
        Get the current data

        Returns
        -------
        verts3d : length-3 tuple or array-like
            The current data as a tuple or array-like.
        """
        return self._verts3d

    @artist.allow_rasterization
    def draw(self, renderer):
        if self._axlim_clip:
            xs3d, ys3d, zs3d = _viewlim_mask(*self._verts3d, self.axes)
        else:
            xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs, tis = proj3d._proj_transform_clip(xs3d, ys3d, zs3d,
                                                      self.axes.M,
                                                      self.axes._focal_length)
        self.set_data(xs, ys)
        super().draw(renderer)
        self.stale = False


def line_2d_to_3d(line, zs=0, zdir='z', axlim_clip=False):
    """
    Convert a `.Line2D` to a `.Line3D` object.

    Parameters
    ----------
    zs : float
        The location along the *zdir* axis in 3D space to position the line.
    zdir : {'x', 'y', 'z'}
        Plane to plot line orthogonal to. Default: 'z'.
        See `.get_dir_vector` for a description of the values.
    axlim_clip : bool, default: False
        Whether to hide lines with an endpoint outside the axes view limits.
    """

    line.__class__ = Line3D
    line.set_3d_properties(zs, zdir, axlim_clip)


def _path_to_3d_segment(path, zs=0, zdir='z'):
    """Convert a path to a 3D segment."""

    zs = np.broadcast_to(zs, len(path))
    pathsegs = path.iter_segments(simplify=False, curves=False)
    seg = [(x, y, z) for (((x, y), code), z) in zip(pathsegs, zs)]
    seg3d = [juggle_axes(x, y, z, zdir) for (x, y, z) in seg]
    return seg3d


def _paths_to_3d_segments(paths, zs=0, zdir='z'):
    """Convert paths from a collection object to 3D segments."""

    if not np.iterable(zs):
        zs = np.broadcast_to(zs, len(paths))
    else:
        if len(zs) != len(paths):
            raise ValueError('Number of z-coordinates does not match paths.')

    segs = [_path_to_3d_segment(path, pathz, zdir)
            for path, pathz in zip(paths, zs)]
    return segs


def _path_to_3d_segment_with_codes(path, zs=0, zdir='z'):
    """Convert a path to a 3D segment with path codes."""

    zs = np.broadcast_to(zs, len(path))
    pathsegs = path.iter_segments(simplify=False, curves=False)
    seg_codes = [((x, y, z), code) for ((x, y), code), z in zip(pathsegs, zs)]
    if seg_codes:
        seg, codes = zip(*seg_codes)
        seg3d = [juggle_axes(x, y, z, zdir) for (x, y, z) in seg]
    else:
        seg3d = []
        codes = []
    return seg3d, list(codes)


def _paths_to_3d_segments_with_codes(paths, zs=0, zdir='z'):
    """
    Convert paths from a collection object to 3D segments with path codes.
    """

    zs = np.broadcast_to(zs, len(paths))
    segments_codes = [_path_to_3d_segment_with_codes(path, pathz, zdir)
                      for path, pathz in zip(paths, zs)]
    if segments_codes:
        segments, codes = zip(*segments_codes)
    else:
        segments, codes = [], []
    return list(segments), list(codes)


class Collection3D(Collection):
    """A collection of 3D paths."""

    def do_3d_projection(self):
        """Project the points according to renderer matrix."""
        vs_list = [vs for vs, _ in self._3dverts_codes]
        if self._axlim_clip:
            vs_list = [np.ma.row_stack(_viewlim_mask(*vs.T, self.axes)).T
                       for vs in vs_list]
        xyzs_list = [proj3d.proj_transform(*vs.T, self.axes.M) for vs in vs_list]
        self._paths = [mpath.Path(np.ma.column_stack([xs, ys]), cs)
                       for (xs, ys, _), (_, cs) in zip(xyzs_list, self._3dverts_codes)]
        zs = np.concatenate([zs for _, _, zs in xyzs_list])
        return zs.min() if len(zs) else 1e9


def collection_2d_to_3d(col, zs=0, zdir='z', axlim_clip=False):
    """Convert a `.Collection` to a `.Collection3D` object."""
    zs = np.broadcast_to(zs, len(col.get_paths()))
    col._3dverts_codes = [
        (np.column_stack(juggle_axes(
            *np.column_stack([p.vertices, np.broadcast_to(z, len(p.vertices))]).T,
            zdir)),
         p.codes)
        for p, z in zip(col.get_paths(), zs)]
    col.__class__ = cbook._make_class_factory(Collection3D, "{}3D")(type(col))
    col._axlim_clip = axlim_clip


class Line3DCollection(LineCollection):
    """
    A collection of 3D lines.
    """
    def __init__(self, lines, axlim_clip=False, **kwargs):
        super().__init__(lines, **kwargs)
        self._axlim_clip = axlim_clip

    def set_sort_zpos(self, val):
        """Set the position to use for z-sorting."""
        self._sort_zpos = val
        self.stale = True

    def set_segments(self, segments):
        """
        Set 3D segments.
        """
        self._segments3d = segments
        super().set_segments([])

    def do_3d_projection(self):
        """
        Project the points according to renderer matrix.
        """
        segments = self._segments3d
        if self._axlim_clip:
            all_points = np.ma.vstack(segments)
            masked_points = np.ma.column_stack([*_viewlim_mask(*all_points.T,
                                                               self.axes)])
            segment_lengths = [np.shape(segment)[0] for segment in segments]
            segments = np.split(masked_points, np.cumsum(segment_lengths[:-1]))
        xyslist = [proj3d._proj_trans_points(points, self.axes.M)
                   for points in segments]
        segments_2d = [np.ma.column_stack([xs, ys]) for xs, ys, zs in xyslist]
        LineCollection.set_segments(self, segments_2d)

        # FIXME
        minz = 1e9
        for xs, ys, zs in xyslist:
            minz = min(minz, min(zs))
        return minz


def line_collection_2d_to_3d(col, zs=0, zdir='z', axlim_clip=False):
    """Convert a `.LineCollection` to a `.Line3DCollection` object."""
    segments3d = _paths_to_3d_segments(col.get_paths(), zs, zdir)
    col.__class__ = Line3DCollection
    col.set_segments(segments3d)
    col._axlim_clip = axlim_clip


class Patch3D(Patch):
    """
    3D patch object.
    """

    def __init__(self, *args, zs=(), zdir='z', axlim_clip=False, **kwargs):
        """
        Parameters
        ----------
        verts :
        zs : float
            The location along the *zdir* axis in 3D space to position the
            patch.
        zdir : {'x', 'y', 'z'}
            Plane to plot patch orthogonal to. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide patches with a vertex outside the axes view limits.
        """
        super().__init__(*args, **kwargs)
        self.set_3d_properties(zs, zdir, axlim_clip)

    def set_3d_properties(self, verts, zs=0, zdir='z', axlim_clip=False):
        """
        Set the *z* position and direction of the patch.

        Parameters
        ----------
        verts :
        zs : float
            The location along the *zdir* axis in 3D space to position the
            patch.
        zdir : {'x', 'y', 'z'}
            Plane to plot patch orthogonal to. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide patches with a vertex outside the axes view limits.
        """
        zs = np.broadcast_to(zs, len(verts))
        self._segment3d = [juggle_axes(x, y, z, zdir)
                           for ((x, y), z) in zip(verts, zs)]
        self._axlim_clip = axlim_clip

    def get_path(self):
        # docstring inherited
        # self._path2d is not initialized until do_3d_projection
        if not hasattr(self, '_path2d'):
            self.axes.M = self.axes.get_proj()
            self.do_3d_projection()
        return self._path2d

    def do_3d_projection(self):
        s = self._segment3d
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(*zip(*s), self.axes)
        else:
            xs, ys, zs = zip(*s)
        vxs, vys, vzs, vis = proj3d._proj_transform_clip(xs, ys, zs,
                                                         self.axes.M,
                                                         self.axes._focal_length)
        self._path2d = mpath.Path(np.ma.column_stack([vxs, vys]))
        return min(vzs)


class PathPatch3D(Patch3D):
    """
    3D PathPatch object.
    """

    def __init__(self, path, *, zs=(), zdir='z', axlim_clip=False, **kwargs):
        """
        Parameters
        ----------
        path :
        zs : float
            The location along the *zdir* axis in 3D space to position the
            path patch.
        zdir : {'x', 'y', 'z', 3-tuple}
            Plane to plot path patch orthogonal to. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide path patches with a point outside the axes view limits.
        """
        # Not super().__init__!
        Patch.__init__(self, **kwargs)
        self.set_3d_properties(path, zs, zdir, axlim_clip)

    def set_3d_properties(self, path, zs=0, zdir='z', axlim_clip=False):
        """
        Set the *z* position and direction of the path patch.

        Parameters
        ----------
        path :
        zs : float
            The location along the *zdir* axis in 3D space to position the
            path patch.
        zdir : {'x', 'y', 'z', 3-tuple}
            Plane to plot path patch orthogonal to. Default: 'z'.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide path patches with a point outside the axes view limits.
        """
        Patch3D.set_3d_properties(self, path.vertices, zs=zs, zdir=zdir,
                                  axlim_clip=axlim_clip)
        self._code3d = path.codes

    def do_3d_projection(self):
        s = self._segment3d
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(*zip(*s), self.axes)
        else:
            xs, ys, zs = zip(*s)
        vxs, vys, vzs, vis = proj3d._proj_transform_clip(xs, ys, zs,
                                                         self.axes.M,
                                                         self.axes._focal_length)
        self._path2d = mpath.Path(np.ma.column_stack([vxs, vys]), self._code3d)
        return min(vzs)


def _get_patch_verts(patch):
    """Return a list of vertices for the path of a patch."""
    trans = patch.get_patch_transform()
    path = patch.get_path()
    polygons = path.to_polygons(trans)
    return polygons[0] if len(polygons) else np.array([])


def patch_2d_to_3d(patch, z=0, zdir='z', axlim_clip=False):
    """Convert a `.Patch` to a `.Patch3D` object."""
    verts = _get_patch_verts(patch)
    patch.__class__ = Patch3D
    patch.set_3d_properties(verts, z, zdir, axlim_clip)


def pathpatch_2d_to_3d(pathpatch, z=0, zdir='z'):
    """Convert a `.PathPatch` to a `.PathPatch3D` object."""
    path = pathpatch.get_path()
    trans = pathpatch.get_patch_transform()

    mpath = trans.transform_path(path)
    pathpatch.__class__ = PathPatch3D
    pathpatch.set_3d_properties(mpath, z, zdir)


class Patch3DCollection(PatchCollection):
    """
    A collection of 3D patches.
    """

    def __init__(self, *args,
                 zs=0, zdir='z', depthshade=True, axlim_clip=False, **kwargs):
        """
        Create a collection of flat 3D patches with its normal vector
        pointed in *zdir* direction, and located at *zs* on the *zdir*
        axis. 'zs' can be a scalar or an array-like of the same length as
        the number of patches in the collection.

        Constructor arguments are the same as for
        :class:`~matplotlib.collections.PatchCollection`. In addition,
        keywords *zs=0* and *zdir='z'* are available.

        Also, the keyword argument *depthshade* is available to indicate
        whether to shade the patches in order to give the appearance of depth
        (default is *True*). This is typically desired in scatter plots.
        """
        self._depthshade = depthshade
        super().__init__(*args, **kwargs)
        self.set_3d_properties(zs, zdir, axlim_clip)

    def get_depthshade(self):
        return self._depthshade

    def set_depthshade(self, depthshade):
        """
        Set whether depth shading is performed on collection members.

        Parameters
        ----------
        depthshade : bool
            Whether to shade the patches in order to give the appearance of
            depth.
        """
        self._depthshade = depthshade
        self.stale = True

    def set_sort_zpos(self, val):
        """Set the position to use for z-sorting."""
        self._sort_zpos = val
        self.stale = True

    def set_3d_properties(self, zs, zdir, axlim_clip=False):
        """
        Set the *z* positions and direction of the patches.

        Parameters
        ----------
        zs : float or array of floats
            The location or locations to place the patches in the collection
            along the *zdir* axis.
        zdir : {'x', 'y', 'z'}
            Plane to plot patches orthogonal to.
            All patches must have the same direction.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide patches with a vertex outside the axes view limits.
        """
        # Force the collection to initialize the face and edgecolors
        # just in case it is a scalarmappable with a colormap.
        self.update_scalarmappable()
        offsets = self.get_offsets()
        if len(offsets) > 0:
            xs, ys = offsets.T
        else:
            xs = []
            ys = []
        self._offsets3d = juggle_axes(xs, ys, np.atleast_1d(zs), zdir)
        self._z_markers_idx = slice(-1)
        self._vzs = None
        self._axlim_clip = axlim_clip
        self.stale = True

    def do_3d_projection(self):
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(*self._offsets3d, self.axes)
        else:
            xs, ys, zs = self._offsets3d
        vxs, vys, vzs, vis = proj3d._proj_transform_clip(xs, ys, zs,
                                                         self.axes.M,
                                                         self.axes._focal_length)
        self._vzs = vzs
        super().set_offsets(np.ma.column_stack([vxs, vys]))

        if vzs.size > 0:
            return min(vzs)
        else:
            return np.nan

    def _maybe_depth_shade_and_sort_colors(self, color_array):
        color_array = (
            _zalpha(color_array, self._vzs)
            if self._vzs is not None and self._depthshade
            else color_array
        )
        if len(color_array) > 1:
            color_array = color_array[self._z_markers_idx]
        return mcolors.to_rgba_array(color_array, self._alpha)

    def get_facecolor(self):
        return self._maybe_depth_shade_and_sort_colors(super().get_facecolor())

    def get_edgecolor(self):
        # We need this check here to make sure we do not double-apply the depth
        # based alpha shading when the edge color is "face" which means the
        # edge colour should be identical to the face colour.
        if cbook._str_equal(self._edgecolors, 'face'):
            return self.get_facecolor()
        return self._maybe_depth_shade_and_sort_colors(super().get_edgecolor())


class Path3DCollection(PathCollection):
    """
    A collection of 3D paths.
    """

    def __init__(self, *args,
                 zs=0, zdir='z', depthshade=True, axlim_clip=False, **kwargs):
        """
        Create a collection of flat 3D paths with its normal vector
        pointed in *zdir* direction, and located at *zs* on the *zdir*
        axis. 'zs' can be a scalar or an array-like of the same length as
        the number of paths in the collection.

        Constructor arguments are the same as for
        :class:`~matplotlib.collections.PathCollection`. In addition,
        keywords *zs=0* and *zdir='z'* are available.

        Also, the keyword argument *depthshade* is available to indicate
        whether to shade the patches in order to give the appearance of depth
        (default is *True*). This is typically desired in scatter plots.
        """
        self._depthshade = depthshade
        self._in_draw = False
        super().__init__(*args, **kwargs)
        self.set_3d_properties(zs, zdir, axlim_clip)
        self._offset_zordered = None

    def draw(self, renderer):
        with self._use_zordered_offset():
            with cbook._setattr_cm(self, _in_draw=True):
                super().draw(renderer)

    def set_sort_zpos(self, val):
        """Set the position to use for z-sorting."""
        self._sort_zpos = val
        self.stale = True

    def set_3d_properties(self, zs, zdir, axlim_clip=False):
        """
        Set the *z* positions and direction of the paths.

        Parameters
        ----------
        zs : float or array of floats
            The location or locations to place the paths in the collection
            along the *zdir* axis.
        zdir : {'x', 'y', 'z'}
            Plane to plot paths orthogonal to.
            All paths must have the same direction.
            See `.get_dir_vector` for a description of the values.
        axlim_clip : bool, default: False
            Whether to hide paths with a vertex outside the axes view limits.
        """
        # Force the collection to initialize the face and edgecolors
        # just in case it is a scalarmappable with a colormap.
        self.update_scalarmappable()
        offsets = self.get_offsets()
        if len(offsets) > 0:
            xs, ys = offsets.T
        else:
            xs = []
            ys = []
        self._zdir = zdir
        self._offsets3d = juggle_axes(xs, ys, np.atleast_1d(zs), zdir)
        # In the base draw methods we access the attributes directly which
        # means we cannot resolve the shuffling in the getter methods like
        # we do for the edge and face colors.
        #
        # This means we need to carry around a cache of the unsorted sizes and
        # widths (postfixed with 3d) and in `do_3d_projection` set the
        # depth-sorted version of that data into the private state used by the
        # base collection class in its draw method.
        #
        # Grab the current sizes and linewidths to preserve them.
        self._sizes3d = self._sizes
        self._linewidths3d = np.array(self._linewidths)
        xs, ys, zs = self._offsets3d

        # Sort the points based on z coordinates
        # Performance optimization: Create a sorted index array and reorder
        # points and point properties according to the index array
        self._z_markers_idx = slice(-1)
        self._vzs = None

        self._axlim_clip = axlim_clip
        self.stale = True

    def set_sizes(self, sizes, dpi=72.0):
        super().set_sizes(sizes, dpi)
        if not self._in_draw:
            self._sizes3d = sizes

    def set_linewidth(self, lw):
        super().set_linewidth(lw)
        if not self._in_draw:
            self._linewidths3d = np.array(self._linewidths)

    def get_depthshade(self):
        return self._depthshade

    def set_depthshade(self, depthshade):
        """
        Set whether depth shading is performed on collection members.

        Parameters
        ----------
        depthshade : bool
            Whether to shade the patches in order to give the appearance of
            depth.
        """
        self._depthshade = depthshade
        self.stale = True

    def do_3d_projection(self):
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(*self._offsets3d, self.axes)
        else:
            xs, ys, zs = self._offsets3d
        vxs, vys, vzs, vis = proj3d._proj_transform_clip(xs, ys, zs,
                                                         self.axes.M,
                                                         self.axes._focal_length)
        # Sort the points based on z coordinates
        # Performance optimization: Create a sorted index array and reorder
        # points and point properties according to the index array
        z_markers_idx = self._z_markers_idx = np.ma.argsort(vzs)[::-1]
        self._vzs = vzs

        # we have to special case the sizes because of code in collections.py
        # as the draw method does
        #      self.set_sizes(self._sizes, self.figure.dpi)
        # so we cannot rely on doing the sorting on the way out via get_*

        if len(self._sizes3d) > 1:
            self._sizes = self._sizes3d[z_markers_idx]

        if len(self._linewidths3d) > 1:
            self._linewidths = self._linewidths3d[z_markers_idx]

        PathCollection.set_offsets(self, np.ma.column_stack((vxs, vys)))

        # Re-order items
        vzs = vzs[z_markers_idx]
        vxs = vxs[z_markers_idx]
        vys = vys[z_markers_idx]

        # Store ordered offset for drawing purpose
        self._offset_zordered = np.ma.column_stack((vxs, vys))

        return np.min(vzs) if vzs.size else np.nan

    @contextmanager
    def _use_zordered_offset(self):
        if self._offset_zordered is None:
            # Do nothing
            yield
        else:
            # Swap offset with z-ordered offset
            old_offset = self._offsets
            super().set_offsets(self._offset_zordered)
            try:
                yield
            finally:
                self._offsets = old_offset

    def _maybe_depth_shade_and_sort_colors(self, color_array):
        color_array = (
            _zalpha(color_array, self._vzs)
            if self._vzs is not None and self._depthshade
            else color_array
        )
        if len(color_array) > 1:
            color_array = color_array[self._z_markers_idx]
        return mcolors.to_rgba_array(color_array, self._alpha)

    def get_facecolor(self):
        return self._maybe_depth_shade_and_sort_colors(super().get_facecolor())

    def get_edgecolor(self):
        # We need this check here to make sure we do not double-apply the depth
        # based alpha shading when the edge color is "face" which means the
        # edge colour should be identical to the face colour.
        if cbook._str_equal(self._edgecolors, 'face'):
            return self.get_facecolor()
        return self._maybe_depth_shade_and_sort_colors(super().get_edgecolor())


def patch_collection_2d_to_3d(col, zs=0, zdir='z', depthshade=True, axlim_clip=False):
    """
    Convert a `.PatchCollection` into a `.Patch3DCollection` object
    (or a `.PathCollection` into a `.Path3DCollection` object).

    Parameters
    ----------
    col : `~matplotlib.collections.PatchCollection` or \
`~matplotlib.collections.PathCollection`
        The collection to convert.
    zs : float or array of floats
        The location or locations to place the patches in the collection along
        the *zdir* axis. Default: 0.
    zdir : {'x', 'y', 'z'}
        The axis in which to place the patches. Default: "z".
        See `.get_dir_vector` for a description of the values.
    depthshade : bool, default: True
        Whether to shade the patches to give a sense of depth.
    axlim_clip : bool, default: False
        Whether to hide patches with a vertex outside the axes view limits.
    """
    if isinstance(col, PathCollection):
        col.__class__ = Path3DCollection
        col._offset_zordered = None
    elif isinstance(col, PatchCollection):
        col.__class__ = Patch3DCollection
    col._depthshade = depthshade
    col._in_draw = False
    col.set_3d_properties(zs, zdir, axlim_clip)


class Poly3DCollection(PolyCollection):
    """
    A collection of 3D polygons.

    .. note::
        **Filling of 3D polygons**

        There is no simple definition of the enclosed surface of a 3D polygon
        unless the polygon is planar.

        In practice, Matplotlib fills the 2D projection of the polygon. This
        gives a correct filling appearance only for planar polygons. For all
        other polygons, you'll find orientations in which the edges of the
        polygon intersect in the projection. This will lead to an incorrect
        visualization of the 3D area.

        If you need filled areas, it is recommended to create them via
        `~mpl_toolkits.mplot3d.axes3d.Axes3D.plot_trisurf`, which creates a
        triangulation and thus generates consistent surfaces.
    """

    def __init__(self, verts, *args, zsort='average', shade=False,
                 lightsource=None, axlim_clip=False, **kwargs):
        """
        Parameters
        ----------
        verts : list of (N, 3) array-like
            The sequence of polygons [*verts0*, *verts1*, ...] where each
            element *verts_i* defines the vertices of polygon *i* as a 2D
            array-like of shape (N, 3).
        zsort : {'average', 'min', 'max'}, default: 'average'
            The calculation method for the z-order.
            See `~.Poly3DCollection.set_zsort` for details.
        shade : bool, default: False
            Whether to shade *facecolors* and *edgecolors*. When activating
            *shade*, *facecolors* and/or *edgecolors* must be provided.

            .. versionadded:: 3.7

        lightsource : `~matplotlib.colors.LightSource`, optional
            The lightsource to use when *shade* is True.

            .. versionadded:: 3.7

        axlim_clip : bool, default: False
            Whether to hide polygons with a vertex outside the view limits.

        *args, **kwargs
            All other parameters are forwarded to `.PolyCollection`.

        Notes
        -----
        Note that this class does a bit of magic with the _facecolors
        and _edgecolors properties.
        """
        if shade:
            normals = _generate_normals(verts)
            facecolors = kwargs.get('facecolors', None)
            if facecolors is not None:
                kwargs['facecolors'] = _shade_colors(
                    facecolors, normals, lightsource
                )

            edgecolors = kwargs.get('edgecolors', None)
            if edgecolors is not None:
                kwargs['edgecolors'] = _shade_colors(
                    edgecolors, normals, lightsource
                )
            if facecolors is None and edgecolors is None:
                raise ValueError(
                    "You must provide facecolors, edgecolors, or both for "
                    "shade to work.")
        super().__init__(verts, *args, **kwargs)
        if isinstance(verts, np.ndarray):
            if verts.ndim != 3:
                raise ValueError('verts must be a list of (N, 3) array-like')
        else:
            if any(len(np.shape(vert)) != 2 for vert in verts):
                raise ValueError('verts must be a list of (N, 3) array-like')
        self.set_zsort(zsort)
        self._codes3d = None
        self._axlim_clip = axlim_clip

    _zsort_functions = {
        'average': np.average,
        'min': np.min,
        'max': np.max,
    }

    def set_zsort(self, zsort):
        """
        Set the calculation method for the z-order.

        Parameters
        ----------
        zsort : {'average', 'min', 'max'}
            The function applied on the z-coordinates of the vertices in the
            viewer's coordinate system, to determine the z-order.
        """
        self._zsortfunc = self._zsort_functions[zsort]
        self._sort_zpos = None
        self.stale = True

    @_api.deprecated("3.10")
    def get_vector(self, segments3d):
        return self._get_vector(segments3d)

    def _get_vector(self, segments3d):
        """Optimize points for projection."""
        if len(segments3d):
            xs, ys, zs = np.vstack(segments3d).T
        else:  # vstack can't stack zero arrays.
            xs, ys, zs = [], [], []
        ones = np.ones(len(xs))
        self._vec = np.array([xs, ys, zs, ones])

        indices = [0, *np.cumsum([len(segment) for segment in segments3d])]
        self._segslices = [*map(slice, indices[:-1], indices[1:])]

    def set_verts(self, verts, closed=True):
        """
        Set 3D vertices.

        Parameters
        ----------
        verts : list of (N, 3) array-like
            The sequence of polygons [*verts0*, *verts1*, ...] where each
            element *verts_i* defines the vertices of polygon *i* as a 2D
            array-like of shape (N, 3).
        closed : bool, default: True
            Whether the polygon should be closed by adding a CLOSEPOLY
            connection at the end.
        """
        self._get_vector(verts)
        # 2D verts will be updated at draw time
        super().set_verts([], False)
        self._closed = closed

    def set_verts_and_codes(self, verts, codes):
        """Set 3D vertices with path codes."""
        # set vertices with closed=False to prevent PolyCollection from
        # setting path codes
        self.set_verts(verts, closed=False)
        # and set our own codes instead.
        self._codes3d = codes

    def set_3d_properties(self, axlim_clip=False):
        # Force the collection to initialize the face and edgecolors
        # just in case it is a scalarmappable with a colormap.
        self.update_scalarmappable()
        self._sort_zpos = None
        self.set_zsort('average')
        self._facecolor3d = PolyCollection.get_facecolor(self)
        self._edgecolor3d = PolyCollection.get_edgecolor(self)
        self._alpha3d = PolyCollection.get_alpha(self)
        self.stale = True

    def set_sort_zpos(self, val):
        """Set the position to use for z-sorting."""
        self._sort_zpos = val
        self.stale = True

    def do_3d_projection(self):
        """
        Perform the 3D projection for this object.
        """
        if self._A is not None:
            # force update of color mapping because we re-order them
            # below.  If we do not do this here, the 2D draw will call
            # this, but we will never port the color mapped values back
            # to the 3D versions.
            #
            # We hold the 3D versions in a fixed order (the order the user
            # passed in) and sort the 2D version by view depth.
            self.update_scalarmappable()
            if self._face_is_mapped:
                self._facecolor3d = self._facecolors
            if self._edge_is_mapped:
                self._edgecolor3d = self._edgecolors
        if self._axlim_clip:
            xs, ys, zs = _viewlim_mask(*self._vec[0:3], self.axes)
            if self._vec.shape[0] == 4:  # Will be 3 (xyz) or 4 (xyzw)
                w_masked = np.ma.masked_where(zs.mask, self._vec[3])
                vec = np.ma.array([xs, ys, zs, w_masked])
            else:
                vec = np.ma.array([xs, ys, zs])
        else:
            vec = self._vec
        txs, tys, tzs = proj3d._proj_transform_vec(vec, self.axes.M)
        xyzlist = [(txs[sl], tys[sl], tzs[sl]) for sl in self._segslices]

        # This extra fuss is to re-order face / edge colors
        cface = self._facecolor3d
        cedge = self._edgecolor3d
        if len(cface) != len(xyzlist):
            cface = cface.repeat(len(xyzlist), axis=0)
        if len(cedge) != len(xyzlist):
            if len(cedge) == 0:
                cedge = cface
            else:
                cedge = cedge.repeat(len(xyzlist), axis=0)

        if xyzlist:
            # sort by depth (furthest drawn first)
            z_segments_2d = sorted(
                ((self._zsortfunc(zs.data), np.ma.column_stack([xs, ys]), fc, ec, idx)
                 for idx, ((xs, ys, zs), fc, ec)
                 in enumerate(zip(xyzlist, cface, cedge))),
                key=lambda x: x[0], reverse=True)

            _, segments_2d, self._facecolors2d, self._edgecolors2d, idxs = \
                zip(*z_segments_2d)
        else:
            segments_2d = []
            self._facecolors2d = np.empty((0, 4))
            self._edgecolors2d = np.empty((0, 4))
            idxs = []

        if self._codes3d is not None:
            codes = [self._codes3d[idx] for idx in idxs]
            PolyCollection.set_verts_and_codes(self, segments_2d, codes)
        else:
            PolyCollection.set_verts(self, segments_2d, self._closed)

        if len(self._edgecolor3d) != len(cface):
            self._edgecolors2d = self._edgecolor3d

        # Return zorder value
        if self._sort_zpos is not None:
            zvec = np.array([[0], [0], [self._sort_zpos], [1]])
            ztrans = proj3d._proj_transform_vec(zvec, self.axes.M)
            return ztrans[2][0]
        elif tzs.size > 0:
            # FIXME: Some results still don't look quite right.
            #        In particular, examine contourf3d_demo2.py
            #        with az = -54 and elev = -45.
            return np.min(tzs)
        else:
            return np.nan

    def set_facecolor(self, colors):
        # docstring inherited
        super().set_facecolor(colors)
        self._facecolor3d = PolyCollection.get_facecolor(self)

    def set_edgecolor(self, colors):
        # docstring inherited
        super().set_edgecolor(colors)
        self._edgecolor3d = PolyCollection.get_edgecolor(self)

    def set_alpha(self, alpha):
        # docstring inherited
        artist.Artist.set_alpha(self, alpha)
        try:
            self._facecolor3d = mcolors.to_rgba_array(
                self._facecolor3d, self._alpha)
        except (AttributeError, TypeError, IndexError):
            pass
        try:
            self._edgecolors = mcolors.to_rgba_array(
                    self._edgecolor3d, self._alpha)
        except (AttributeError, TypeError, IndexError):
            pass
        self.stale = True

    def get_facecolor(self):
        # docstring inherited
        # self._facecolors2d is not initialized until do_3d_projection
        if not hasattr(self, '_facecolors2d'):
            self.axes.M = self.axes.get_proj()
            self.do_3d_projection()
        return np.asarray(self._facecolors2d)

    def get_edgecolor(self):
        # docstring inherited
        # self._edgecolors2d is not initialized until do_3d_projection
        if not hasattr(self, '_edgecolors2d'):
            self.axes.M = self.axes.get_proj()
            self.do_3d_projection()
        return np.asarray(self._edgecolors2d)


def poly_collection_2d_to_3d(col, zs=0, zdir='z', axlim_clip=False):
    """
    Convert a `.PolyCollection` into a `.Poly3DCollection` object.

    Parameters
    ----------
    col : `~matplotlib.collections.PolyCollection`
        The collection to convert.
    zs : float or array of floats
        The location or locations to place the polygons in the collection along
        the *zdir* axis. Default: 0.
    zdir : {'x', 'y', 'z'}
        The axis in which to place the patches. Default: 'z'.
        See `.get_dir_vector` for a description of the values.
    """
    segments_3d, codes = _paths_to_3d_segments_with_codes(
            col.get_paths(), zs, zdir)
    col.__class__ = Poly3DCollection
    col.set_verts_and_codes(segments_3d, codes)
    col.set_3d_properties()
    col._axlim_clip = axlim_clip


def juggle_axes(xs, ys, zs, zdir):
    """
    Reorder coordinates so that 2D *xs*, *ys* can be plotted in the plane
    orthogonal to *zdir*. *zdir* is normally 'x', 'y' or 'z'. However, if
    *zdir* starts with a '-' it is interpreted as a compensation for
    `rotate_axes`.
    """
    if zdir == 'x':
        return zs, xs, ys
    elif zdir == 'y':
        return xs, zs, ys
    elif zdir[0] == '-':
        return rotate_axes(xs, ys, zs, zdir)
    else:
        return xs, ys, zs


def rotate_axes(xs, ys, zs, zdir):
    """
    Reorder coordinates so that the axes are rotated with *zdir* along
    the original z axis. Prepending the axis with a '-' does the
    inverse transform, so *zdir* can be 'x', '-x', 'y', '-y', 'z' or '-z'.
    """
    if zdir in ('x', '-y'):
        return ys, zs, xs
    elif zdir in ('-x', 'y'):
        return zs, xs, ys
    else:
        return xs, ys, zs


def _zalpha(colors, zs):
    """Modify the alphas of the color list according to depth."""
    # FIXME: This only works well if the points for *zs* are well-spaced
    #        in all three dimensions. Otherwise, at certain orientations,
    #        the min and max zs are very close together.
    #        Should really normalize against the viewing depth.
    if len(colors) == 0 or len(zs) == 0:
        return np.zeros((0, 4))
    norm = Normalize(min(zs), max(zs))
    sats = 1 - norm(zs) * 0.7
    rgba = np.broadcast_to(mcolors.to_rgba_array(colors), (len(zs), 4))
    return np.column_stack([rgba[:, :3], rgba[:, 3] * sats])


def _all_points_on_plane(xs, ys, zs, atol=1e-8):
    """
    Check if all points are on the same plane. Note that NaN values are
    ignored.

    Parameters
    ----------
    xs, ys, zs : array-like
        The x, y, and z coordinates of the points.
    atol : float, default: 1e-8
        The tolerance for the equality check.
    """
    xs, ys, zs = np.asarray(xs), np.asarray(ys), np.asarray(zs)
    points = np.column_stack([xs, ys, zs])
    points = points[~np.isnan(points).any(axis=1)]
    # Check for the case where we have less than 3 unique points
    points = np.unique(points, axis=0)
    if len(points) <= 3:
        return True
    # Calculate the vectors from the first point to all other points
    vs = (points - points[0])[1:]
    vs = vs / np.linalg.norm(vs, axis=1)[:, np.newaxis]
    # Filter out parallel vectors
    vs = np.unique(vs, axis=0)
    if len(vs) <= 2:
        return True
    # Filter out parallel and antiparallel vectors to the first vector
    cross_norms = np.linalg.norm(np.cross(vs[0], vs[1:]), axis=1)
    zero_cross_norms = np.where(np.isclose(cross_norms, 0, atol=atol))[0] + 1
    vs = np.delete(vs, zero_cross_norms, axis=0)
    if len(vs) <= 2:
        return True
    # Calculate the normal vector from the first three points
    n = np.cross(vs[0], vs[1])
    n = n / np.linalg.norm(n)
    # If the dot product of the normal vector and all other vectors is zero,
    # all points are on the same plane
    dots = np.dot(n, vs.transpose())
    return np.allclose(dots, 0, atol=atol)


def _generate_normals(polygons):
    """
    Compute the normals of a list of polygons, one normal per polygon.

    Normals point towards the viewer for a face with its vertices in
    counterclockwise order, following the right hand rule.

    Uses three points equally spaced around the polygon. This method assumes
    that the points are in a plane. Otherwise, more than one shade is required,
    which is not supported.

    Parameters
    ----------
    polygons : list of (M_i, 3) array-like, or (..., M, 3) array-like
        A sequence of polygons to compute normals for, which can have
        varying numbers of vertices. If the polygons all have the same
        number of vertices and array is passed, then the operation will
        be vectorized.

    Returns
    -------
    normals : (..., 3) array
        A normal vector estimated for the polygon.
    """
    if isinstance(polygons, np.ndarray):
        # optimization: polygons all have the same number of points, so can
        # vectorize
        n = polygons.shape[-2]
        i1, i2, i3 = 0, n//3, 2*n//3
        v1 = polygons[..., i1, :] - polygons[..., i2, :]
        v2 = polygons[..., i2, :] - polygons[..., i3, :]
    else:
        # The subtraction doesn't vectorize because polygons is jagged.
        v1 = np.empty((len(polygons), 3))
        v2 = np.empty((len(polygons), 3))
        for poly_i, ps in enumerate(polygons):
            n = len(ps)
            ps = np.asarray(ps)
            i1, i2, i3 = 0, n//3, 2*n//3
            v1[poly_i, :] = ps[i1, :] - ps[i2, :]
            v2[poly_i, :] = ps[i2, :] - ps[i3, :]
    return np.cross(v1, v2)


def _shade_colors(color, normals, lightsource=None):
    """
    Shade *color* using normal vectors given by *normals*,
    assuming a *lightsource* (using default position if not given).
    *color* can also be an array of the same length as *normals*.
    """
    if lightsource is None:
        # chosen for backwards-compatibility
        lightsource = mcolors.LightSource(azdeg=225, altdeg=19.4712)

    with np.errstate(invalid="ignore"):
        shade = ((normals / np.linalg.norm(normals, axis=1, keepdims=True))
                 @ lightsource.direction)
    mask = ~np.isnan(shade)

    if mask.any():
        # convert dot product to allowed shading fractions
        in_norm = mcolors.Normalize(-1, 1)
        out_norm = mcolors.Normalize(0.3, 1).inverse

        def norm(x):
            return out_norm(in_norm(x))

        shade[~mask] = 0

        color = mcolors.to_rgba_array(color)
        # shape of color should be (M, 4) (where M is number of faces)
        # shape of shade should be (M,)
        # colors should have final shape of (M, 4)
        alpha = color[:, 3]
        colors = norm(shade)[:, np.newaxis] * color
        colors[:, 3] = alpha
    else:
        colors = np.asanyarray(color).copy()

    return colors

# === NexusCore/openenv\Lib\site-packages\numpy\_core\defchararray.py ===
"""
This module contains a set of functions for vectorized string
operations and methods.

.. note::
   The `chararray` class exists for backwards compatibility with
   Numarray, it is not recommended for new development. Starting from numpy
   1.4, if one needs arrays of strings, it is recommended to use arrays of
   `dtype` `object_`, `bytes_` or `str_`, and use the free functions
   in the `numpy.char` module for fast vectorized string operations.

Some methods will only be available if the corresponding string method is
available in your version of Python.

The preferred alias for `defchararray` is `numpy.char`.

"""
import functools

import numpy as np
from numpy._core import overrides
from numpy._core.multiarray import compare_chararrays
from numpy._core.strings import (
    _join as join,
)
from numpy._core.strings import (
    _rsplit as rsplit,
)
from numpy._core.strings import (
    _split as split,
)
from numpy._core.strings import (
    _splitlines as splitlines,
)
from numpy._utils import set_module
from numpy.strings import *
from numpy.strings import (
    multiply as strings_multiply,
)
from numpy.strings import (
    partition as strings_partition,
)
from numpy.strings import (
    rpartition as strings_rpartition,
)

from .numeric import array as narray
from .numeric import asarray as asnarray
from .numeric import ndarray
from .numerictypes import bytes_, character, str_

__all__ = [
    'equal', 'not_equal', 'greater_equal', 'less_equal',
    'greater', 'less', 'str_len', 'add', 'multiply', 'mod', 'capitalize',
    'center', 'count', 'decode', 'encode', 'endswith', 'expandtabs',
    'find', 'index', 'isalnum', 'isalpha', 'isdigit', 'islower', 'isspace',
    'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip', 'partition',
    'replace', 'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit',
    'rstrip', 'split', 'splitlines', 'startswith', 'strip', 'swapcase',
    'title', 'translate', 'upper', 'zfill', 'isnumeric', 'isdecimal',
    'array', 'asarray', 'compare_chararrays', 'chararray'
    ]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy.char')


def _binary_op_dispatcher(x1, x2):
    return (x1, x2)


@array_function_dispatch(_binary_op_dispatcher)
def equal(x1, x2):
    """
    Return (x1 == x2) element-wise.

    Unlike `numpy.equal`, this comparison is performed by first
    stripping whitespace characters from the end of the string.  This
    behavior is provided for backward-compatibility with numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    Examples
    --------
    >>> import numpy as np
    >>> y = "aa "
    >>> x = "aa"
    >>> np.char.equal(x, y)
    array(True)

    See Also
    --------
    not_equal, greater_equal, less_equal, greater, less
    """
    return compare_chararrays(x1, x2, '==', True)


@array_function_dispatch(_binary_op_dispatcher)
def not_equal(x1, x2):
    """
    Return (x1 != x2) element-wise.

    Unlike `numpy.not_equal`, this comparison is performed by first
    stripping whitespace characters from the end of the string.  This
    behavior is provided for backward-compatibility with numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    See Also
    --------
    equal, greater_equal, less_equal, greater, less

    Examples
    --------
    >>> import numpy as np
    >>> x1 = np.array(['a', 'b', 'c'])
    >>> np.char.not_equal(x1, 'b')
    array([ True, False,  True])

    """
    return compare_chararrays(x1, x2, '!=', True)


@array_function_dispatch(_binary_op_dispatcher)
def greater_equal(x1, x2):
    """
    Return (x1 >= x2) element-wise.

    Unlike `numpy.greater_equal`, this comparison is performed by
    first stripping whitespace characters from the end of the string.
    This behavior is provided for backward-compatibility with
    numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    See Also
    --------
    equal, not_equal, less_equal, greater, less

    Examples
    --------
    >>> import numpy as np
    >>> x1 = np.array(['a', 'b', 'c'])
    >>> np.char.greater_equal(x1, 'b')
    array([False,  True,  True])

    """
    return compare_chararrays(x1, x2, '>=', True)


@array_function_dispatch(_binary_op_dispatcher)
def less_equal(x1, x2):
    """
    Return (x1 <= x2) element-wise.

    Unlike `numpy.less_equal`, this comparison is performed by first
    stripping whitespace characters from the end of the string.  This
    behavior is provided for backward-compatibility with numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    See Also
    --------
    equal, not_equal, greater_equal, greater, less

    Examples
    --------
    >>> import numpy as np
    >>> x1 = np.array(['a', 'b', 'c'])
    >>> np.char.less_equal(x1, 'b')
    array([ True,  True, False])

    """
    return compare_chararrays(x1, x2, '<=', True)


@array_function_dispatch(_binary_op_dispatcher)
def greater(x1, x2):
    """
    Return (x1 > x2) element-wise.

    Unlike `numpy.greater`, this comparison is performed by first
    stripping whitespace characters from the end of the string.  This
    behavior is provided for backward-compatibility with numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    See Also
    --------
    equal, not_equal, greater_equal, less_equal, less

    Examples
    --------
    >>> import numpy as np
    >>> x1 = np.array(['a', 'b', 'c'])
    >>> np.char.greater(x1, 'b')
    array([False, False,  True])

    """
    return compare_chararrays(x1, x2, '>', True)


@array_function_dispatch(_binary_op_dispatcher)
def less(x1, x2):
    """
    Return (x1 < x2) element-wise.

    Unlike `numpy.greater`, this comparison is performed by first
    stripping whitespace characters from the end of the string.  This
    behavior is provided for backward-compatibility with numarray.

    Parameters
    ----------
    x1, x2 : array_like of str or unicode
        Input arrays of the same shape.

    Returns
    -------
    out : ndarray
        Output array of bools.

    See Also
    --------
    equal, not_equal, greater_equal, less_equal, greater

    Examples
    --------
    >>> import numpy as np
    >>> x1 = np.array(['a', 'b', 'c'])
    >>> np.char.less(x1, 'b')
    array([True, False, False])

    """
    return compare_chararrays(x1, x2, '<', True)


@set_module("numpy.char")
def multiply(a, i):
    """
    Return (a * i), that is string multiple concatenation,
    element-wise.

    Values in ``i`` of less than 0 are treated as 0 (which yields an
    empty string).

    Parameters
    ----------
    a : array_like, with `np.bytes_` or `np.str_` dtype

    i : array_like, with any integer dtype

    Returns
    -------
    out : ndarray
        Output array of str or unicode, depending on input types

    Notes
    -----
    This is a thin wrapper around np.strings.multiply that raises
    `ValueError` when ``i`` is not an integer. It only
    exists for backwards-compatibility.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["a", "b", "c"])
    >>> np.strings.multiply(a, 3)
    array(['aaa', 'bbb', 'ccc'], dtype='<U3')
    >>> i = np.array([1, 2, 3])
    >>> np.strings.multiply(a, i)
    array(['a', 'bb', 'ccc'], dtype='<U3')
    >>> np.strings.multiply(np.array(['a']), i)
    array(['a', 'aa', 'aaa'], dtype='<U3')
    >>> a = np.array(['a', 'b', 'c', 'd', 'e', 'f']).reshape((2, 3))
    >>> np.strings.multiply(a, 3)
    array([['aaa', 'bbb', 'ccc'],
           ['ddd', 'eee', 'fff']], dtype='<U3')
    >>> np.strings.multiply(a, i)
    array([['a', 'bb', 'ccc'],
           ['d', 'ee', 'fff']], dtype='<U3')

    """
    try:
        return strings_multiply(a, i)
    except TypeError:
        raise ValueError("Can only multiply by integers")


@set_module("numpy.char")
def partition(a, sep):
    """
    Partition each element in `a` around `sep`.

    Calls :meth:`str.partition` element-wise.

    For each element in `a`, split the element as the first
    occurrence of `sep`, and return 3 strings containing the part
    before the separator, the separator itself, and the part after
    the separator. If the separator is not found, return 3 strings
    containing the string itself, followed by two empty strings.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array
    sep : {str, unicode}
        Separator to split each string element in `a`.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types. The output array will have an extra
        dimension with 3 elements per input element.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array(["Numpy is nice!"])
    >>> np.char.partition(x, " ")
    array([['Numpy', ' ', 'is nice!']], dtype='<U8')

    See Also
    --------
    str.partition

    """
    return np.stack(strings_partition(a, sep), axis=-1)


@set_module("numpy.char")
def rpartition(a, sep):
    """
    Partition (split) each element around the right-most separator.

    Calls :meth:`str.rpartition` element-wise.

    For each element in `a`, split the element as the last
    occurrence of `sep`, and return 3 strings containing the part
    before the separator, the separator itself, and the part after
    the separator. If the separator is not found, return 3 strings
    containing the string itself, followed by two empty strings.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array
    sep : str or unicode
        Right-most separator to split each element in array.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types. The output array will have an extra
        dimension with 3 elements per input element.

    See Also
    --------
    str.rpartition

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> np.char.rpartition(a, 'A')
    array([['aAaAa', 'A', ''],
       ['  a', 'A', '  '],
       ['abB', 'A', 'Bba']], dtype='<U5')

    """
    return np.stack(strings_rpartition(a, sep), axis=-1)


@set_module("numpy.char")
class chararray(ndarray):
    """
    chararray(shape, itemsize=1, unicode=False, buffer=None, offset=0,
              strides=None, order=None)

    Provides a convenient view on arrays of string and unicode values.

    .. note::
       The `chararray` class exists for backwards compatibility with
       Numarray, it is not recommended for new development. Starting from numpy
       1.4, if one needs arrays of strings, it is recommended to use arrays of
       `dtype` `~numpy.object_`, `~numpy.bytes_` or `~numpy.str_`, and use
       the free functions in the `numpy.char` module for fast vectorized
       string operations.

    Versus a NumPy array of dtype `~numpy.bytes_` or `~numpy.str_`, this
    class adds the following functionality:

    1) values automatically have whitespace removed from the end
       when indexed

    2) comparison operators automatically remove whitespace from the
       end when comparing values

    3) vectorized string operations are provided as methods
       (e.g. `.endswith`) and infix operators (e.g. ``"+", "*", "%"``)

    chararrays should be created using `numpy.char.array` or
    `numpy.char.asarray`, rather than this constructor directly.

    This constructor creates the array, using `buffer` (with `offset`
    and `strides`) if it is not ``None``. If `buffer` is ``None``, then
    constructs a new array with `strides` in "C order", unless both
    ``len(shape) >= 2`` and ``order='F'``, in which case `strides`
    is in "Fortran order".

    Methods
    -------
    astype
    argsort
    copy
    count
    decode
    dump
    dumps
    encode
    endswith
    expandtabs
    fill
    find
    flatten
    getfield
    index
    isalnum
    isalpha
    isdecimal
    isdigit
    islower
    isnumeric
    isspace
    istitle
    isupper
    item
    join
    ljust
    lower
    lstrip
    nonzero
    put
    ravel
    repeat
    replace
    reshape
    resize
    rfind
    rindex
    rjust
    rsplit
    rstrip
    searchsorted
    setfield
    setflags
    sort
    split
    splitlines
    squeeze
    startswith
    strip
    swapaxes
    swapcase
    take
    title
    tofile
    tolist
    tostring
    translate
    transpose
    upper
    view
    zfill

    Parameters
    ----------
    shape : tuple
        Shape of the array.
    itemsize : int, optional
        Length of each array element, in number of characters. Default is 1.
    unicode : bool, optional
        Are the array elements of type unicode (True) or string (False).
        Default is False.
    buffer : object exposing the buffer interface or str, optional
        Memory address of the start of the array data.  Default is None,
        in which case a new array is created.
    offset : int, optional
        Fixed stride displacement from the beginning of an axis?
        Default is 0. Needs to be >=0.
    strides : array_like of ints, optional
        Strides for the array (see `~numpy.ndarray.strides` for
        full description). Default is None.
    order : {'C', 'F'}, optional
        The order in which the array data is stored in memory: 'C' ->
        "row major" order (the default), 'F' -> "column major"
        (Fortran) order.

    Examples
    --------
    >>> import numpy as np
    >>> charar = np.char.chararray((3, 3))
    >>> charar[:] = 'a'
    >>> charar
    chararray([[b'a', b'a', b'a'],
               [b'a', b'a', b'a'],
               [b'a', b'a', b'a']], dtype='|S1')

    >>> charar = np.char.chararray(charar.shape, itemsize=5)
    >>> charar[:] = 'abc'
    >>> charar
    chararray([[b'abc', b'abc', b'abc'],
               [b'abc', b'abc', b'abc'],
               [b'abc', b'abc', b'abc']], dtype='|S5')

    """
    def __new__(subtype, shape, itemsize=1, unicode=False, buffer=None,
                offset=0, strides=None, order='C'):
        if unicode:
            dtype = str_
        else:
            dtype = bytes_

        # force itemsize to be a Python int, since using NumPy integer
        # types results in itemsize.itemsize being used as the size of
        # strings in the new array.
        itemsize = int(itemsize)

        if isinstance(buffer, str):
            # unicode objects do not have the buffer interface
            filler = buffer
            buffer = None
        else:
            filler = None

        if buffer is None:
            self = ndarray.__new__(subtype, shape, (dtype, itemsize),
                                   order=order)
        else:
            self = ndarray.__new__(subtype, shape, (dtype, itemsize),
                                   buffer=buffer,
                                   offset=offset, strides=strides,
                                   order=order)
        if filler is not None:
            self[...] = filler

        return self

    def __array_wrap__(self, arr, context=None, return_scalar=False):
        # When calling a ufunc (and some other functions), we return a
        # chararray if the ufunc output is a string-like array,
        # or an ndarray otherwise
        if arr.dtype.char in "SUbc":
            return arr.view(type(self))
        return arr

    def __array_finalize__(self, obj):
        # The b is a special case because it is used for reconstructing.
        if self.dtype.char not in 'VSUbc':
            raise ValueError("Can only create a chararray from string data.")

    def __getitem__(self, obj):
        val = ndarray.__getitem__(self, obj)
        if isinstance(val, character):
            return val.rstrip()
        return val

    # IMPLEMENTATION NOTE: Most of the methods of this class are
    # direct delegations to the free functions in this module.
    # However, those that return an array of strings should instead
    # return a chararray, so some extra wrapping is required.

    def __eq__(self, other):
        """
        Return (self == other) element-wise.

        See Also
        --------
        equal
        """
        return equal(self, other)

    def __ne__(self, other):
        """
        Return (self != other) element-wise.

        See Also
        --------
        not_equal
        """
        return not_equal(self, other)

    def __ge__(self, other):
        """
        Return (self >= other) element-wise.

        See Also
        --------
        greater_equal
        """
        return greater_equal(self, other)

    def __le__(self, other):
        """
        Return (self <= other) element-wise.

        See Also
        --------
        less_equal
        """
        return less_equal(self, other)

    def __gt__(self, other):
        """
        Return (self > other) element-wise.

        See Also
        --------
        greater
        """
        return greater(self, other)

    def __lt__(self, other):
        """
        Return (self < other) element-wise.

        See Also
        --------
        less
        """
        return less(self, other)

    def __add__(self, other):
        """
        Return (self + other), that is string concatenation,
        element-wise for a pair of array_likes of str or unicode.

        See Also
        --------
        add
        """
        return add(self, other)

    def __radd__(self, other):
        """
        Return (other + self), that is string concatenation,
        element-wise for a pair of array_likes of `bytes_` or `str_`.

        See Also
        --------
        add
        """
        return add(other, self)

    def __mul__(self, i):
        """
        Return (self * i), that is string multiple concatenation,
        element-wise.

        See Also
        --------
        multiply
        """
        return asarray(multiply(self, i))

    def __rmul__(self, i):
        """
        Return (self * i), that is string multiple concatenation,
        element-wise.

        See Also
        --------
        multiply
        """
        return asarray(multiply(self, i))

    def __mod__(self, i):
        """
        Return (self % i), that is pre-Python 2.6 string formatting
        (interpolation), element-wise for a pair of array_likes of `bytes_`
        or `str_`.

        See Also
        --------
        mod
        """
        return asarray(mod(self, i))

    def __rmod__(self, other):
        return NotImplemented

    def argsort(self, axis=-1, kind=None, order=None):
        """
        Return the indices that sort the array lexicographically.

        For full documentation see `numpy.argsort`, for which this method is
        in fact merely a "thin wrapper."

        Examples
        --------
        >>> c = np.array(['a1b c', '1b ca', 'b ca1', 'Ca1b'], 'S5')
        >>> c = c.view(np.char.chararray); c
        chararray(['a1b c', '1b ca', 'b ca1', 'Ca1b'],
              dtype='|S5')
        >>> c[c.argsort()]
        chararray(['1b ca', 'Ca1b', 'a1b c', 'b ca1'],
              dtype='|S5')

        """
        return self.__array__().argsort(axis, kind, order)
    argsort.__doc__ = ndarray.argsort.__doc__

    def capitalize(self):
        """
        Return a copy of `self` with only the first character of each element
        capitalized.

        See Also
        --------
        char.capitalize

        """
        return asarray(capitalize(self))

    def center(self, width, fillchar=' '):
        """
        Return a copy of `self` with its elements centered in a
        string of length `width`.

        See Also
        --------
        center
        """
        return asarray(center(self, width, fillchar))

    def count(self, sub, start=0, end=None):
        """
        Returns an array with the number of non-overlapping occurrences of
        substring `sub` in the range [`start`, `end`].

        See Also
        --------
        char.count

        """
        return count(self, sub, start, end)

    def decode(self, encoding=None, errors=None):
        """
        Calls ``bytes.decode`` element-wise.

        See Also
        --------
        char.decode

        """
        return decode(self, encoding, errors)

    def encode(self, encoding=None, errors=None):
        """
        Calls :meth:`str.encode` element-wise.

        See Also
        --------
        char.encode

        """
        return encode(self, encoding, errors)

    def endswith(self, suffix, start=0, end=None):
        """
        Returns a boolean array which is `True` where the string element
        in `self` ends with `suffix`, otherwise `False`.

        See Also
        --------
        char.endswith

        """
        return endswith(self, suffix, start, end)

    def expandtabs(self, tabsize=8):
        """
        Return a copy of each string element where all tab characters are
        replaced by one or more spaces.

        See Also
        --------
        char.expandtabs

        """
        return asarray(expandtabs(self, tabsize))

    def find(self, sub, start=0, end=None):
        """
        For each element, return the lowest index in the string where
        substring `sub` is found.

        See Also
        --------
        char.find

        """
        return find(self, sub, start, end)

    def index(self, sub, start=0, end=None):
        """
        Like `find`, but raises :exc:`ValueError` when the substring is not
        found.

        See Also
        --------
        char.index

        """
        return index(self, sub, start, end)

    def isalnum(self):
        """
        Returns true for each element if all characters in the string
        are alphanumeric and there is at least one character, false
        otherwise.

        See Also
        --------
        char.isalnum

        """
        return isalnum(self)

    def isalpha(self):
        """
        Returns true for each element if all characters in the string
        are alphabetic and there is at least one character, false
        otherwise.

        See Also
        --------
        char.isalpha

        """
        return isalpha(self)

    def isdigit(self):
        """
        Returns true for each element if all characters in the string are
        digits and there is at least one character, false otherwise.

        See Also
        --------
        char.isdigit

        """
        return isdigit(self)

    def islower(self):
        """
        Returns true for each element if all cased characters in the
        string are lowercase and there is at least one cased character,
        false otherwise.

        See Also
        --------
        char.islower

        """
        return islower(self)

    def isspace(self):
        """
        Returns true for each element if there are only whitespace
        characters in the string and there is at least one character,
        false otherwise.

        See Also
        --------
        char.isspace

        """
        return isspace(self)

    def istitle(self):
        """
        Returns true for each element if the element is a titlecased
        string and there is at least one character, false otherwise.

        See Also
        --------
        char.istitle

        """
        return istitle(self)

    def isupper(self):
        """
        Returns true for each element if all cased characters in the
        string are uppercase and there is at least one character, false
        otherwise.

        See Also
        --------
        char.isupper

        """
        return isupper(self)

    def join(self, seq):
        """
        Return a string which is the concatenation of the strings in the
        sequence `seq`.

        See Also
        --------
        char.join

        """
        return join(self, seq)

    def ljust(self, width, fillchar=' '):
        """
        Return an array with the elements of `self` left-justified in a
        string of length `width`.

        See Also
        --------
        char.ljust

        """
        return asarray(ljust(self, width, fillchar))

    def lower(self):
        """
        Return an array with the elements of `self` converted to
        lowercase.

        See Also
        --------
        char.lower

        """
        return asarray(lower(self))

    def lstrip(self, chars=None):
        """
        For each element in `self`, return a copy with the leading characters
        removed.

        See Also
        --------
        char.lstrip

        """
        return lstrip(self, chars)

    def partition(self, sep):
        """
        Partition each element in `self` around `sep`.

        See Also
        --------
        partition
        """
        return asarray(partition(self, sep))

    def replace(self, old, new, count=None):
        """
        For each element in `self`, return a copy of the string with all
        occurrences of substring `old` replaced by `new`.

        See Also
        --------
        char.replace

        """
        return replace(self, old, new, count if count is not None else -1)

    def rfind(self, sub, start=0, end=None):
        """
        For each element in `self`, return the highest index in the string
        where substring `sub` is found, such that `sub` is contained
        within [`start`, `end`].

        See Also
        --------
        char.rfind

        """
        return rfind(self, sub, start, end)

    def rindex(self, sub, start=0, end=None):
        """
        Like `rfind`, but raises :exc:`ValueError` when the substring `sub` is
        not found.

        See Also
        --------
        char.rindex

        """
        return rindex(self, sub, start, end)

    def rjust(self, width, fillchar=' '):
        """
        Return an array with the elements of `self`
        right-justified in a string of length `width`.

        See Also
        --------
        char.rjust

        """
        return asarray(rjust(self, width, fillchar))

    def rpartition(self, sep):
        """
        Partition each element in `self` around `sep`.

        See Also
        --------
        rpartition
        """
        return asarray(rpartition(self, sep))

    def rsplit(self, sep=None, maxsplit=None):
        """
        For each element in `self`, return a list of the words in
        the string, using `sep` as the delimiter string.

        See Also
        --------
        char.rsplit

        """
        return rsplit(self, sep, maxsplit)

    def rstrip(self, chars=None):
        """
        For each element in `self`, return a copy with the trailing
        characters removed.

        See Also
        --------
        char.rstrip

        """
        return rstrip(self, chars)

    def split(self, sep=None, maxsplit=None):
        """
        For each element in `self`, return a list of the words in the
        string, using `sep` as the delimiter string.

        See Also
        --------
        char.split

        """
        return split(self, sep, maxsplit)

    def splitlines(self, keepends=None):
        """
        For each element in `self`, return a list of the lines in the
        element, breaking at line boundaries.

        See Also
        --------
        char.splitlines

        """
        return splitlines(self, keepends)

    def startswith(self, prefix, start=0, end=None):
        """
        Returns a boolean array which is `True` where the string element
        in `self` starts with `prefix`, otherwise `False`.

        See Also
        --------
        char.startswith

        """
        return startswith(self, prefix, start, end)

    def strip(self, chars=None):
        """
        For each element in `self`, return a copy with the leading and
        trailing characters removed.

        See Also
        --------
        char.strip

        """
        return strip(self, chars)

    def swapcase(self):
        """
        For each element in `self`, return a copy of the string with
        uppercase characters converted to lowercase and vice versa.

        See Also
        --------
        char.swapcase

        """
        return asarray(swapcase(self))

    def title(self):
        """
        For each element in `self`, return a titlecased version of the
        string: words start with uppercase characters, all remaining cased
        characters are lowercase.

        See Also
        --------
        char.title

        """
        return asarray(title(self))

    def translate(self, table, deletechars=None):
        """
        For each element in `self`, return a copy of the string where
        all characters occurring in the optional argument
        `deletechars` are removed, and the remaining characters have
        been mapped through the given translation table.

        See Also
        --------
        char.translate

        """
        return asarray(translate(self, table, deletechars))

    def upper(self):
        """
        Return an array with the elements of `self` converted to
        uppercase.

        See Also
        --------
        char.upper

        """
        return asarray(upper(self))

    def zfill(self, width):
        """
        Return the numeric string left-filled with zeros in a string of
        length `width`.

        See Also
        --------
        char.zfill

        """
        return asarray(zfill(self, width))

    def isnumeric(self):
        """
        For each element in `self`, return True if there are only
        numeric characters in the element.

        See Also
        --------
        char.isnumeric

        """
        return isnumeric(self)

    def isdecimal(self):
        """
        For each element in `self`, return True if there are only
        decimal characters in the element.

        See Also
        --------
        char.isdecimal

        """
        return isdecimal(self)


@set_module("numpy.char")
def array(obj, itemsize=None, copy=True, unicode=None, order=None):
    """
    Create a `~numpy.char.chararray`.

    .. note::
       This class is provided for numarray backward-compatibility.
       New code (not concerned with numarray compatibility) should use
       arrays of type `bytes_` or `str_` and use the free functions
       in :mod:`numpy.char` for fast vectorized string operations instead.

    Versus a NumPy array of dtype `bytes_` or `str_`, this
    class adds the following functionality:

    1) values automatically have whitespace removed from the end
       when indexed

    2) comparison operators automatically remove whitespace from the
       end when comparing values

    3) vectorized string operations are provided as methods
       (e.g. `chararray.endswith <numpy.char.chararray.endswith>`)
       and infix operators (e.g. ``+, *, %``)

    Parameters
    ----------
    obj : array of str or unicode-like

    itemsize : int, optional
        `itemsize` is the number of characters per scalar in the
        resulting array.  If `itemsize` is None, and `obj` is an
        object array or a Python list, the `itemsize` will be
        automatically determined.  If `itemsize` is provided and `obj`
        is of type str or unicode, then the `obj` string will be
        chunked into `itemsize` pieces.

    copy : bool, optional
        If true (default), then the object is copied.  Otherwise, a copy
        will only be made if ``__array__`` returns a copy, if obj is a
        nested sequence, or if a copy is needed to satisfy any of the other
        requirements (`itemsize`, unicode, `order`, etc.).

    unicode : bool, optional
        When true, the resulting `~numpy.char.chararray` can contain Unicode
        characters, when false only 8-bit characters.  If unicode is
        None and `obj` is one of the following:

        - a `~numpy.char.chararray`,
        - an ndarray of type :class:`str_` or :class:`bytes_`
        - a Python :class:`str` or :class:`bytes` object,

        then the unicode setting of the output array will be
        automatically determined.

    order : {'C', 'F', 'A'}, optional
        Specify the order of the array.  If order is 'C' (default), then the
        array will be in C-contiguous order (last-index varies the
        fastest).  If order is 'F', then the returned array
        will be in Fortran-contiguous order (first-index varies the
        fastest).  If order is 'A', then the returned array may
        be in any order (either C-, Fortran-contiguous, or even
        discontiguous).

    Examples
    --------

    >>> import numpy as np
    >>> char_array = np.char.array(['hello', 'world', 'numpy','array'])
    >>> char_array
    chararray(['hello', 'world', 'numpy', 'array'], dtype='<U5')

    """
    if isinstance(obj, (bytes, str)):
        if unicode is None:
            if isinstance(obj, str):
                unicode = True
            else:
                unicode = False

        if itemsize is None:
            itemsize = len(obj)
        shape = len(obj) // itemsize

        return chararray(shape, itemsize=itemsize, unicode=unicode,
                         buffer=obj, order=order)

    if isinstance(obj, (list, tuple)):
        obj = asnarray(obj)

    if isinstance(obj, ndarray) and issubclass(obj.dtype.type, character):
        # If we just have a vanilla chararray, create a chararray
        # view around it.
        if not isinstance(obj, chararray):
            obj = obj.view(chararray)

        if itemsize is None:
            itemsize = obj.itemsize
            # itemsize is in 8-bit chars, so for Unicode, we need
            # to divide by the size of a single Unicode character,
            # which for NumPy is always 4
            if issubclass(obj.dtype.type, str_):
                itemsize //= 4

        if unicode is None:
            if issubclass(obj.dtype.type, str_):
                unicode = True
            else:
                unicode = False

        if unicode:
            dtype = str_
        else:
            dtype = bytes_

        if order is not None:
            obj = asnarray(obj, order=order)
        if (copy or
                (itemsize != obj.itemsize) or
                (not unicode and isinstance(obj, str_)) or
                (unicode and isinstance(obj, bytes_))):
            obj = obj.astype((dtype, int(itemsize)))
        return obj

    if isinstance(obj, ndarray) and issubclass(obj.dtype.type, object):
        if itemsize is None:
            # Since no itemsize was specified, convert the input array to
            # a list so the ndarray constructor will automatically
            # determine the itemsize for us.
            obj = obj.tolist()
            # Fall through to the default case

    if unicode:
        dtype = str_
    else:
        dtype = bytes_

    if itemsize is None:
        val = narray(obj, dtype=dtype, order=order, subok=True)
    else:
        val = narray(obj, dtype=(dtype, itemsize), order=order, subok=True)
    return val.view(chararray)


@set_module("numpy.char")
def asarray(obj, itemsize=None, unicode=None, order=None):
    """
    Convert the input to a `~numpy.char.chararray`, copying the data only if
    necessary.

    Versus a NumPy array of dtype `bytes_` or `str_`, this
    class adds the following functionality:

    1) values automatically have whitespace removed from the end
       when indexed

    2) comparison operators automatically remove whitespace from the
       end when comparing values

    3) vectorized string operations are provided as methods
       (e.g. `chararray.endswith <numpy.char.chararray.endswith>`)
       and infix operators (e.g. ``+``, ``*``, ``%``)

    Parameters
    ----------
    obj : array of str or unicode-like

    itemsize : int, optional
        `itemsize` is the number of characters per scalar in the
        resulting array.  If `itemsize` is None, and `obj` is an
        object array or a Python list, the `itemsize` will be
        automatically determined.  If `itemsize` is provided and `obj`
        is of type str or unicode, then the `obj` string will be
        chunked into `itemsize` pieces.

    unicode : bool, optional
        When true, the resulting `~numpy.char.chararray` can contain Unicode
        characters, when false only 8-bit characters.  If unicode is
        None and `obj` is one of the following:

        - a `~numpy.char.chararray`,
        - an ndarray of type `str_` or `unicode_`
        - a Python str or unicode object,

        then the unicode setting of the output array will be
        automatically determined.

    order : {'C', 'F'}, optional
        Specify the order of the array.  If order is 'C' (default), then the
        array will be in C-contiguous order (last-index varies the
        fastest).  If order is 'F', then the returned array
        will be in Fortran-contiguous order (first-index varies the
        fastest).

    Examples
    --------
    >>> import numpy as np
    >>> np.char.asarray(['hello', 'world'])
    chararray(['hello', 'world'], dtype='<U5')

    """
    return array(obj, itemsize, copy=False,
                 unicode=unicode, order=order)

# === NexusCore/openenv\Lib\site-packages\tornado\test\iostream_test.py ===
from tornado.concurrent import Future
from tornado import gen
from tornado import netutil
from tornado.ioloop import IOLoop
from tornado.iostream import (
    IOStream,
    SSLIOStream,
    PipeIOStream,
    StreamClosedError,
    _StreamBuffer,
)
from tornado.httpclient import AsyncHTTPClient, HTTPResponse
from tornado.httputil import HTTPHeaders
from tornado.locks import Condition, Event
from tornado.log import gen_log
from tornado.netutil import ssl_options_to_context, ssl_wrap_socket
from tornado.platform.asyncio import AddThreadSelectorEventLoop
from tornado.tcpserver import TCPServer
from tornado.testing import (
    AsyncHTTPTestCase,
    AsyncHTTPSTestCase,
    AsyncTestCase,
    bind_unused_port,
    ExpectLog,
    gen_test,
)
from tornado.test.util import (
    skipIfNonUnix,
    refusing_port,
    ignore_deprecation,
    abstract_base_test,
)
from tornado.web import RequestHandler, Application
import asyncio
import errno
import hashlib
import logging
import os
import platform
import random
import socket
import ssl
import typing
from unittest import mock
import unittest


def _server_ssl_options():
    return dict(
        certfile=os.path.join(os.path.dirname(__file__), "test.crt"),
        keyfile=os.path.join(os.path.dirname(__file__), "test.key"),
    )


class HelloHandler(RequestHandler):
    def get(self):
        self.write("Hello")


@abstract_base_test
class TestIOStreamWebMixin(AsyncTestCase):
    # We want to run these tests with both AsyncHTTPTestCase and AsyncHTTPSTestCase,
    # but this leads to some tricky inheritance situations. We want this class's
    # get_app, but the test classes's get_http_port and fetch. There's no way to make
    # the method resolution order to do what we want in all cases, so the current
    # state is that that AsyncHTTP(S)TestCase must be the first base class of the
    # final class, and that class must define a get_app method that calls mixin_get_app.
    #
    # Alternatives include defining this class in a factory that can change the base class
    # or refactoring to use composition instead of inheritance for the http components.
    def _make_client_iostream(self):
        raise NotImplementedError()

    def mixin_get_app(self):
        return Application([("/", HelloHandler)])

    def get_http_port(self) -> int:
        raise NotImplementedError()

    def fetch(
        self, path: str, raise_error: bool = False, **kwargs: typing.Any
    ) -> HTTPResponse:
        # To be filled in by mixing in AsyncHTTPTestCase or AsyncHTTPSTestCase
        raise NotImplementedError()

    def test_connection_closed(self):
        # When a server sends a response and then closes the connection,
        # the client must be allowed to read the data before the IOStream
        # closes itself.  Epoll reports closed connections with a separate
        # EPOLLRDHUP event delivered at the same time as the read event,
        # while kqueue reports them as a second read/write event with an EOF
        # flag.
        if (
            AsyncHTTPClient.configured_class().__name__.endswith("CurlAsyncHTTPClient")
            and platform.system() == "Darwin"
        ):
            # It's possible that this is Tornado's fault, either in AsyncIOLoop or in
            # CurlAsyncHTTPClient, but we've also seen this kind of issue in libcurl itself
            # (especially a long time ago). The error is tied to the use of Apple's
            # SecureTransport instead of OpenSSL.
            self.skipTest("libcurl doesn't handle closed connections cleanly on macOS")
        response = self.fetch("/", headers={"Connection": "close"})
        response.rethrow()

    @gen_test
    def test_read_until_close(self):
        stream = self._make_client_iostream()
        yield stream.connect(("127.0.0.1", self.get_http_port()))
        stream.write(b"GET / HTTP/1.0\r\n\r\n")

        data = yield stream.read_until_close()
        self.assertTrue(data.startswith(b"HTTP/1.1 200"))
        self.assertTrue(data.endswith(b"Hello"))

    @gen_test
    def test_read_zero_bytes(self):
        self.stream = self._make_client_iostream()
        yield self.stream.connect(("127.0.0.1", self.get_http_port()))
        self.stream.write(b"GET / HTTP/1.0\r\n\r\n")

        # normal read
        data = yield self.stream.read_bytes(9)
        self.assertEqual(data, b"HTTP/1.1 ")

        # zero bytes
        data = yield self.stream.read_bytes(0)
        self.assertEqual(data, b"")

        # another normal read
        data = yield self.stream.read_bytes(3)
        self.assertEqual(data, b"200")

        self.stream.close()

    @gen_test
    def test_write_while_connecting(self):
        stream = self._make_client_iostream()
        connect_fut = stream.connect(("127.0.0.1", self.get_http_port()))
        # unlike the previous tests, try to write before the connection
        # is complete.
        write_fut = stream.write(b"GET / HTTP/1.0\r\nConnection: close\r\n\r\n")
        self.assertFalse(connect_fut.done())

        # connect will always complete before write.
        it = gen.WaitIterator(connect_fut, write_fut)
        resolved_order = []
        while not it.done():
            yield it.next()
            resolved_order.append(it.current_future)
        self.assertEqual(resolved_order, [connect_fut, write_fut])

        data = yield stream.read_until_close()
        self.assertTrue(data.endswith(b"Hello"))

        stream.close()

    @gen_test
    def test_future_interface(self):
        """Basic test of IOStream's ability to return Futures."""
        stream = self._make_client_iostream()
        connect_result = yield stream.connect(("127.0.0.1", self.get_http_port()))
        self.assertIs(connect_result, stream)
        yield stream.write(b"GET / HTTP/1.0\r\n\r\n")
        first_line = yield stream.read_until(b"\r\n")
        self.assertEqual(first_line, b"HTTP/1.1 200 OK\r\n")
        # callback=None is equivalent to no callback.
        header_data = yield stream.read_until(b"\r\n\r\n")
        headers = HTTPHeaders.parse(header_data.decode("latin1"))
        content_length = int(headers["Content-Length"])
        body = yield stream.read_bytes(content_length)
        self.assertEqual(body, b"Hello")
        stream.close()

    @gen_test
    def test_future_close_while_reading(self):
        stream = self._make_client_iostream()
        yield stream.connect(("127.0.0.1", self.get_http_port()))
        yield stream.write(b"GET / HTTP/1.0\r\n\r\n")
        with self.assertRaises(StreamClosedError):
            yield stream.read_bytes(1024 * 1024)
        stream.close()

    @gen_test
    def test_future_read_until_close(self):
        # Ensure that the data comes through before the StreamClosedError.
        stream = self._make_client_iostream()
        yield stream.connect(("127.0.0.1", self.get_http_port()))
        yield stream.write(b"GET / HTTP/1.0\r\nConnection: close\r\n\r\n")
        yield stream.read_until(b"\r\n\r\n")
        body = yield stream.read_until_close()
        self.assertEqual(body, b"Hello")

        # Nothing else to read; the error comes immediately without waiting
        # for yield.
        with self.assertRaises(StreamClosedError):
            stream.read_bytes(1)


@abstract_base_test
class TestReadWriteMixin(AsyncTestCase):
    # Tests where one stream reads and the other writes.
    # These should work for BaseIOStream implementations.

    def make_iostream_pair(self, **kwargs):
        raise NotImplementedError

    def iostream_pair(self, **kwargs):
        """Like make_iostream_pair, but called by ``async with``.

        In py37 this becomes simpler with contextlib.asynccontextmanager.
        """

        class IOStreamPairContext:
            def __init__(self, test, kwargs):
                self.test = test
                self.kwargs = kwargs

            async def __aenter__(self):
                self.pair = await self.test.make_iostream_pair(**self.kwargs)
                return self.pair

            async def __aexit__(self, typ, value, tb):
                for s in self.pair:
                    s.close()

        return IOStreamPairContext(self, kwargs)

    @gen_test
    def test_write_zero_bytes(self):
        # Attempting to write zero bytes should run the callback without
        # going into an infinite loop.
        rs, ws = yield self.make_iostream_pair()
        yield ws.write(b"")
        ws.close()
        rs.close()

    @gen_test
    def test_future_delayed_close_callback(self):
        # Same as test_delayed_close_callback, but with the future interface.
        rs, ws = yield self.make_iostream_pair()

        try:
            ws.write(b"12")
            chunks = []
            chunks.append((yield rs.read_bytes(1)))
            ws.close()
            chunks.append((yield rs.read_bytes(1)))
            self.assertEqual(chunks, [b"1", b"2"])
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_close_buffered_data(self):
        # Similar to the previous test, but with data stored in the OS's
        # socket buffers instead of the IOStream's read buffer.  Out-of-band
        # close notifications must be delayed until all data has been
        # drained into the IOStream buffer. (epoll used to use out-of-band
        # close events with EPOLLRDHUP, but no longer)
        #
        # This depends on the read_chunk_size being smaller than the
        # OS socket buffer, so make it small.
        rs, ws = yield self.make_iostream_pair(read_chunk_size=256)
        try:
            ws.write(b"A" * 512)
            data = yield rs.read_bytes(256)
            self.assertEqual(b"A" * 256, data)
            ws.close()
            # Allow the close to propagate to the `rs` side of the
            # connection.  Using add_callback instead of add_timeout
            # doesn't seem to work, even with multiple iterations
            yield gen.sleep(0.01)
            data = yield rs.read_bytes(256)
            self.assertEqual(b"A" * 256, data)
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_close_after_close(self):
        # Similar to test_delayed_close_callback, but read_until_close takes
        # a separate code path so test it separately.
        rs, ws = yield self.make_iostream_pair()
        try:
            ws.write(b"1234")
            # Read one byte to make sure the client has received the data.
            # It won't run the close callback as long as there is more buffered
            # data that could satisfy a later read.
            data = yield rs.read_bytes(1)
            ws.close()
            self.assertEqual(data, b"1")
            data = yield rs.read_until_close()
            self.assertEqual(data, b"234")
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_large_read_until(self):
        # Performance test: read_until used to have a quadratic component
        # so a read_until of 4MB would take 8 seconds; now it takes 0.25
        # seconds.
        rs, ws = yield self.make_iostream_pair()
        try:
            # This test fails on pypy with ssl.  I think it's because
            # pypy's gc defeats moves objects, breaking the
            # "frozen write buffer" assumption.
            if (
                isinstance(rs, SSLIOStream)
                and platform.python_implementation() == "PyPy"
            ):
                raise unittest.SkipTest("pypy gc causes problems with openssl")
            NUM_KB = 4096
            for i in range(NUM_KB):
                ws.write(b"A" * 1024)
            ws.write(b"\r\n")
            data = yield rs.read_until(b"\r\n")
            self.assertEqual(len(data), NUM_KB * 1024 + 2)
        finally:
            ws.close()
            rs.close()

    @gen_test
    async def test_read_until_with_close_after_second_packet(self):
        # This is a regression test for a regression in Tornado 6.0
        # (maybe 6.0.3?) reported in
        # https://github.com/tornadoweb/tornado/issues/2717
        #
        # The data arrives in two chunks; the stream is closed at the
        # same time that the second chunk is received. If the second
        # chunk is larger than the first, it works, but when this bug
        # existed it would fail if the second chunk were smaller than
        # the first. This is due to the optimization that the
        # read_until condition is only checked when the buffer doubles
        # in size
        async with self.iostream_pair() as (rs, ws):
            rf = asyncio.ensure_future(rs.read_until(b"done"))
            # We need to wait for the read_until to actually start. On
            # windows that's tricky because the selector runs in
            # another thread; sleeping is the simplest way.
            await asyncio.sleep(0.1)
            await ws.write(b"x" * 2048)
            ws.write(b"done")
            ws.close()
            await rf

    @gen_test
    async def test_read_until_unsatisfied_after_close(self):
        # If a stream is closed while reading, it raises
        # StreamClosedError instead of UnsatisfiableReadError (the
        # latter should only be raised when byte limits are reached).
        # The particular scenario tested here comes from #2717.
        async with self.iostream_pair() as (rs, ws):
            rf = asyncio.ensure_future(rs.read_until(b"done"))
            await ws.write(b"x" * 2048)
            ws.write(b"foo")
            ws.close()
            with self.assertRaises(StreamClosedError):
                await rf

    @gen_test
    def test_close_callback_with_pending_read(self):
        # Regression test for a bug that was introduced in 2.3
        # where the IOStream._close_callback would never be called
        # if there were pending reads.
        OK = b"OK\r\n"
        rs, ws = yield self.make_iostream_pair()
        event = Event()
        rs.set_close_callback(event.set)
        try:
            ws.write(OK)
            res = yield rs.read_until(b"\r\n")
            self.assertEqual(res, OK)

            ws.close()
            rs.read_until(b"\r\n")
            # If _close_callback (self.stop) is not called,
            # an AssertionError: Async operation timed out after 5 seconds
            # will be raised.
            yield event.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_future_close_callback(self):
        # Regression test for interaction between the Future read interfaces
        # and IOStream._maybe_add_error_listener.
        rs, ws = yield self.make_iostream_pair()
        closed = [False]
        cond = Condition()

        def close_callback():
            closed[0] = True
            cond.notify()

        rs.set_close_callback(close_callback)
        try:
            ws.write(b"a")
            res = yield rs.read_bytes(1)
            self.assertEqual(res, b"a")
            self.assertFalse(closed[0])
            ws.close()
            yield cond.wait()
            self.assertTrue(closed[0])
        finally:
            rs.close()
            ws.close()

    @gen_test
    def test_write_memoryview(self):
        rs, ws = yield self.make_iostream_pair()
        try:
            fut = rs.read_bytes(4)
            ws.write(memoryview(b"hello"))
            data = yield fut
            self.assertEqual(data, b"hell")
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_bytes_partial(self):
        rs, ws = yield self.make_iostream_pair()
        try:
            # Ask for more than is available with partial=True
            fut = rs.read_bytes(50, partial=True)
            ws.write(b"hello")
            data = yield fut
            self.assertEqual(data, b"hello")

            # Ask for less than what is available; num_bytes is still
            # respected.
            fut = rs.read_bytes(3, partial=True)
            ws.write(b"world")
            data = yield fut
            self.assertEqual(data, b"wor")

            # Partial reads won't return an empty string, but read_bytes(0)
            # will.
            data = yield rs.read_bytes(0, partial=True)
            self.assertEqual(data, b"")
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_max_bytes(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Extra room under the limit
            fut = rs.read_until(b"def", max_bytes=50)
            ws.write(b"abcdef")
            data = yield fut
            self.assertEqual(data, b"abcdef")

            # Just enough space
            fut = rs.read_until(b"def", max_bytes=6)
            ws.write(b"abcdef")
            data = yield fut
            self.assertEqual(data, b"abcdef")

            # Not enough space, but we don't know it until all we can do is
            # log a warning and close the connection.
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                fut = rs.read_until(b"def", max_bytes=5)
                ws.write(b"123456")
                yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_max_bytes_inline(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Similar to the error case in the previous test, but the
            # ws writes first so rs reads are satisfied
            # inline.  For consistency with the out-of-line case, we
            # do not raise the error synchronously.
            ws.write(b"123456")
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                with self.assertRaises(StreamClosedError):
                    yield rs.read_until(b"def", max_bytes=5)
            yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_max_bytes_ignores_extra(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Even though data that matches arrives the same packet that
            # puts us over the limit, we fail the request because it was not
            # found within the limit.
            ws.write(b"abcdef")
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                rs.read_until(b"def", max_bytes=5)
                yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_regex_max_bytes(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Extra room under the limit
            fut = rs.read_until_regex(b"def", max_bytes=50)
            ws.write(b"abcdef")
            data = yield fut
            self.assertEqual(data, b"abcdef")

            # Just enough space
            fut = rs.read_until_regex(b"def", max_bytes=6)
            ws.write(b"abcdef")
            data = yield fut
            self.assertEqual(data, b"abcdef")

            # Not enough space, but we don't know it until all we can do is
            # log a warning and close the connection.
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                rs.read_until_regex(b"def", max_bytes=5)
                ws.write(b"123456")
                yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_regex_max_bytes_inline(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Similar to the error case in the previous test, but the
            # ws writes first so rs reads are satisfied
            # inline.  For consistency with the out-of-line case, we
            # do not raise the error synchronously.
            ws.write(b"123456")
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                rs.read_until_regex(b"def", max_bytes=5)
                yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_until_regex_max_bytes_ignores_extra(self):
        rs, ws = yield self.make_iostream_pair()
        closed = Event()
        rs.set_close_callback(closed.set)
        try:
            # Even though data that matches arrives the same packet that
            # puts us over the limit, we fail the request because it was not
            # found within the limit.
            ws.write(b"abcdef")
            with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
                rs.read_until_regex(b"def", max_bytes=5)
                yield closed.wait()
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_small_reads_from_large_buffer(self):
        # 10KB buffer size, 100KB available to read.
        # Read 1KB at a time and make sure that the buffer is not eagerly
        # filled.
        rs, ws = yield self.make_iostream_pair(max_buffer_size=10 * 1024)
        try:
            ws.write(b"a" * 1024 * 100)
            for i in range(100):
                data = yield rs.read_bytes(1024)
                self.assertEqual(data, b"a" * 1024)
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_small_read_untils_from_large_buffer(self):
        # 10KB buffer size, 100KB available to read.
        # Read 1KB at a time and make sure that the buffer is not eagerly
        # filled.
        rs, ws = yield self.make_iostream_pair(max_buffer_size=10 * 1024)
        try:
            ws.write((b"a" * 1023 + b"\n") * 100)
            for i in range(100):
                data = yield rs.read_until(b"\n", max_bytes=4096)
                self.assertEqual(data, b"a" * 1023 + b"\n")
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_flow_control(self):
        MB = 1024 * 1024
        rs, ws = yield self.make_iostream_pair(max_buffer_size=5 * MB)
        try:
            # Client writes more than the rs will accept.
            ws.write(b"a" * 10 * MB)
            # The rs pauses while reading.
            yield rs.read_bytes(MB)
            yield gen.sleep(0.1)
            # The ws's writes have been blocked; the rs can
            # continue to read gradually.
            for i in range(9):
                yield rs.read_bytes(MB)
        finally:
            rs.close()
            ws.close()

    @gen_test
    def test_read_into(self):
        rs, ws = yield self.make_iostream_pair()

        def sleep_some():
            self.io_loop.run_sync(lambda: gen.sleep(0.05))

        try:
            buf = bytearray(10)
            fut = rs.read_into(buf)
            ws.write(b"hello")
            yield gen.sleep(0.05)
            self.assertTrue(rs.reading())
            ws.write(b"world!!")
            data = yield fut
            self.assertFalse(rs.reading())
            self.assertEqual(data, 10)
            self.assertEqual(bytes(buf), b"helloworld")

            # Existing buffer is fed into user buffer
            fut = rs.read_into(buf)
            yield gen.sleep(0.05)
            self.assertTrue(rs.reading())
            ws.write(b"1234567890")
            data = yield fut
            self.assertFalse(rs.reading())
            self.assertEqual(data, 10)
            self.assertEqual(bytes(buf), b"!!12345678")

            # Existing buffer can satisfy read immediately
            buf = bytearray(4)
            ws.write(b"abcdefghi")
            data = yield rs.read_into(buf)
            self.assertEqual(data, 4)
            self.assertEqual(bytes(buf), b"90ab")

            data = yield rs.read_bytes(7)
            self.assertEqual(data, b"cdefghi")
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_into_partial(self):
        rs, ws = yield self.make_iostream_pair()

        try:
            # Partial read
            buf = bytearray(10)
            fut = rs.read_into(buf, partial=True)
            ws.write(b"hello")
            data = yield fut
            self.assertFalse(rs.reading())
            self.assertEqual(data, 5)
            self.assertEqual(bytes(buf), b"hello\0\0\0\0\0")

            # Full read despite partial=True
            ws.write(b"world!1234567890")
            data = yield rs.read_into(buf, partial=True)
            self.assertEqual(data, 10)
            self.assertEqual(bytes(buf), b"world!1234")

            # Existing buffer can satisfy read immediately
            data = yield rs.read_into(buf, partial=True)
            self.assertEqual(data, 6)
            self.assertEqual(bytes(buf), b"5678901234")

        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_read_into_zero_bytes(self):
        rs, ws = yield self.make_iostream_pair()
        try:
            buf = bytearray()
            fut = rs.read_into(buf)
            self.assertEqual(fut.result(), 0)
        finally:
            ws.close()
            rs.close()

    @gen_test
    def test_many_mixed_reads(self):
        # Stress buffer handling when going back and forth between
        # read_bytes() (using an internal buffer) and read_into()
        # (using a user-allocated buffer).
        r = random.Random(42)
        nbytes = 1000000
        rs, ws = yield self.make_iostream_pair()

        produce_hash = hashlib.sha1()
        consume_hash = hashlib.sha1()

        @gen.coroutine
        def produce():
            remaining = nbytes
            while remaining > 0:
                size = r.randint(1, min(1000, remaining))
                data = os.urandom(size)
                produce_hash.update(data)
                yield ws.write(data)
                remaining -= size
            assert remaining == 0

        @gen.coroutine
        def consume():
            remaining = nbytes
            while remaining > 0:
                if r.random() > 0.5:
                    # read_bytes()
                    size = r.randint(1, min(1000, remaining))
                    data = yield rs.read_bytes(size)
                    consume_hash.update(data)
                    remaining -= size
                else:
                    # read_into()
                    size = r.randint(1, min(1000, remaining))
                    buf = bytearray(size)
                    n = yield rs.read_into(buf)
                    assert n == size
                    consume_hash.update(buf)
                    remaining -= size
            assert remaining == 0

        try:
            yield [produce(), consume()]
            assert produce_hash.hexdigest() == consume_hash.hexdigest()
        finally:
            ws.close()
            rs.close()


@abstract_base_test
class TestIOStreamMixin(TestReadWriteMixin):
    def _make_server_iostream(self, connection, **kwargs):
        raise NotImplementedError()

    def _make_client_iostream(self, connection, **kwargs):
        raise NotImplementedError()

    @gen.coroutine
    def make_iostream_pair(self, **kwargs):
        listener, port = bind_unused_port()
        server_stream_fut = Future()  # type: Future[IOStream]

        def accept_callback(connection, address):
            server_stream_fut.set_result(
                self._make_server_iostream(connection, **kwargs)
            )

        netutil.add_accept_handler(listener, accept_callback)
        client_stream = self._make_client_iostream(socket.socket(), **kwargs)
        connect_fut = client_stream.connect(("127.0.0.1", port))
        server_stream, client_stream = yield [server_stream_fut, connect_fut]
        self.io_loop.remove_handler(listener.fileno())
        listener.close()
        raise gen.Return((server_stream, client_stream))

    @gen_test
    def test_connection_refused(self):
        # When a connection is refused, the connect callback should not
        # be run.  (The kqueue IOLoop used to behave differently from the
        # epoll IOLoop in this respect)
        cleanup_func, port = refusing_port()
        self.addCleanup(cleanup_func)
        stream = IOStream(socket.socket())

        stream.set_close_callback(self.stop)
        # log messages vary by platform and ioloop implementation
        with ExpectLog(gen_log, ".*", required=False):
            with self.assertRaises(StreamClosedError):
                yield stream.connect(("127.0.0.1", port))

        self.assertTrue(isinstance(stream.error, ConnectionRefusedError), stream.error)

    @gen_test
    def test_gaierror(self):
        # Test that IOStream sets its exc_info on getaddrinfo error.
        # It's difficult to reliably trigger a getaddrinfo error;
        # some resolvers own't even return errors for malformed names,
        # so we mock it instead. If IOStream changes to call a Resolver
        # before sock.connect, the mock target will need to change too.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = IOStream(s)
        stream.set_close_callback(self.stop)
        with mock.patch(
            "socket.socket.connect", side_effect=socket.gaierror(errno.EIO, "boom")
        ):
            with self.assertRaises(StreamClosedError):
                yield stream.connect(("localhost", 80))
            self.assertTrue(isinstance(stream.error, socket.gaierror))

    @gen_test
    def test_read_until_close_with_error(self):
        server, client = yield self.make_iostream_pair()
        try:
            with mock.patch(
                "tornado.iostream.BaseIOStream._try_inline_read",
                side_effect=IOError("boom"),
            ):
                with self.assertRaisesRegex(IOError, "boom"):
                    client.read_until_close()
        finally:
            server.close()
            client.close()

    @skipIfNonUnix
    @gen_test
    def test_inline_read_error(self):
        # An error on an inline read is raised without logging (on the
        # assumption that it will eventually be noticed or logged further
        # up the stack).
        #
        # This test is posix-only because windows os.close() doesn't work
        # on socket FDs, but we can't close the socket object normally
        # because we won't get the error we want if the socket knows
        # it's closed.
        #
        # This test is also disabled when the
        # AddThreadSelectorEventLoop is used, because a race between
        # this thread closing the socket and the selector thread
        # calling the select system call can make this test flaky.
        # This event loop implementation is normally only used on
        # windows, making this check redundant with skipIfNonUnix, but
        # we sometimes enable it on other platforms for testing.
        io_loop = IOLoop.current()
        if isinstance(
            io_loop.selector_loop,  # type: ignore[attr-defined]
            AddThreadSelectorEventLoop,
        ):
            self.skipTest("AddThreadSelectorEventLoop not supported")
        server, client = yield self.make_iostream_pair()
        try:
            os.close(server.socket.fileno())
            with self.assertRaises(socket.error):
                server.read_bytes(1)
        finally:
            server.close()
            client.close()

    @gen_test
    def test_async_read_error_logging(self):
        # Socket errors on asynchronous reads should be logged (but only
        # once).
        server, client = yield self.make_iostream_pair()
        closed = Event()
        server.set_close_callback(closed.set)
        try:
            # Start a read that will be fulfilled asynchronously.
            server.read_bytes(1)
            client.write(b"a")
            # Stub out read_from_fd to make it fail.

            def fake_read_from_fd():
                os.close(server.socket.fileno())
                server.__class__.read_from_fd(server)

            server.read_from_fd = fake_read_from_fd
            # This log message is from _handle_read (not read_from_fd).
            with ExpectLog(gen_log, "error on read"):
                yield closed.wait()
        finally:
            server.close()
            client.close()

    @gen_test
    def test_future_write(self):
        """
        Test that write() Futures are never orphaned.
        """
        # Run concurrent writers that will write enough bytes so as to
        # clog the socket buffer and accumulate bytes in our write buffer.
        m, n = 5000, 1000
        nproducers = 10
        total_bytes = m * n * nproducers
        server, client = yield self.make_iostream_pair(max_buffer_size=total_bytes)

        @gen.coroutine
        def produce():
            data = b"x" * m
            for i in range(n):
                yield server.write(data)

        @gen.coroutine
        def consume():
            nread = 0
            while nread < total_bytes:
                res = yield client.read_bytes(m)
                nread += len(res)

        try:
            yield [produce() for i in range(nproducers)] + [consume()]
        finally:
            server.close()
            client.close()


class TestIOStreamWebHTTP(AsyncHTTPTestCase, TestIOStreamWebMixin):
    def _make_client_iostream(self):
        return IOStream(socket.socket())

    def get_app(self):
        return self.mixin_get_app()


class TestIOStreamWebHTTPS(AsyncHTTPSTestCase, TestIOStreamWebMixin):
    def _make_client_iostream(self):
        return SSLIOStream(socket.socket(), ssl_options=dict(cert_reqs=ssl.CERT_NONE))

    def get_app(self):
        return self.mixin_get_app()


class TestIOStream(TestIOStreamMixin):
    def _make_server_iostream(self, connection, **kwargs):
        return IOStream(connection, **kwargs)

    def _make_client_iostream(self, connection, **kwargs):
        return IOStream(connection, **kwargs)


class TestIOStreamSSL(TestIOStreamMixin):
    def _make_server_iostream(self, connection, **kwargs):
        ssl_ctx = ssl_options_to_context(_server_ssl_options(), server_side=True)
        connection = ssl_ctx.wrap_socket(
            connection,
            server_side=True,
            do_handshake_on_connect=False,
        )
        return SSLIOStream(connection, **kwargs)

    def _make_client_iostream(self, connection, **kwargs):
        return SSLIOStream(
            connection, ssl_options=dict(cert_reqs=ssl.CERT_NONE), **kwargs
        )


# This will run some tests that are basically redundant but it's the
# simplest way to make sure that it works to pass an SSLContext
# instead of an ssl_options dict to the SSLIOStream constructor.
class TestIOStreamSSLContext(TestIOStreamMixin):
    def _make_server_iostream(self, connection, **kwargs):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            os.path.join(os.path.dirname(__file__), "test.crt"),
            os.path.join(os.path.dirname(__file__), "test.key"),
        )
        connection = ssl_wrap_socket(
            connection, context, server_side=True, do_handshake_on_connect=False
        )
        return SSLIOStream(connection, **kwargs)

    def _make_client_iostream(self, connection, **kwargs):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return SSLIOStream(connection, ssl_options=context, **kwargs)


class TestIOStreamStartTLS(AsyncTestCase):
    def setUp(self):
        try:
            super().setUp()
            self.listener, self.port = bind_unused_port()
            self.server_stream = None
            self.server_accepted = Future()  # type: Future[None]
            netutil.add_accept_handler(self.listener, self.accept)
            self.client_stream = IOStream(
                socket.socket()
            )  # type: typing.Optional[IOStream]
            self.io_loop.add_future(
                self.client_stream.connect(("127.0.0.1", self.port)), self.stop
            )
            self.wait()
            self.io_loop.add_future(self.server_accepted, self.stop)
            self.wait()
        except Exception as e:
            print(e)
            raise

    def tearDown(self):
        if self.server_stream is not None:
            self.server_stream.close()
        if self.client_stream is not None:
            self.client_stream.close()
        self.io_loop.remove_handler(self.listener.fileno())
        self.listener.close()
        super().tearDown()

    def accept(self, connection, address):
        if self.server_stream is not None:
            self.fail("should only get one connection")
        self.server_stream = IOStream(connection)
        self.server_accepted.set_result(None)

    @gen.coroutine
    def client_send_line(self, line):
        assert self.client_stream is not None
        self.client_stream.write(line)
        assert self.server_stream is not None
        recv_line = yield self.server_stream.read_until(b"\r\n")
        self.assertEqual(line, recv_line)

    @gen.coroutine
    def server_send_line(self, line):
        assert self.server_stream is not None
        self.server_stream.write(line)
        assert self.client_stream is not None
        recv_line = yield self.client_stream.read_until(b"\r\n")
        self.assertEqual(line, recv_line)

    def client_start_tls(self, ssl_options=None, server_hostname=None):
        assert self.client_stream is not None
        client_stream = self.client_stream
        self.client_stream = None
        return client_stream.start_tls(False, ssl_options, server_hostname)

    def server_start_tls(self, ssl_options=None):
        assert self.server_stream is not None
        server_stream = self.server_stream
        self.server_stream = None
        return server_stream.start_tls(True, ssl_options)

    @gen_test
    def test_start_tls_smtp(self):
        # This flow is simplified from RFC 3207 section 5.
        # We don't really need all of this, but it helps to make sure
        # that after realistic back-and-forth traffic the buffers end up
        # in a sane state.
        yield self.server_send_line(b"220 mail.example.com ready\r\n")
        yield self.client_send_line(b"EHLO mail.example.com\r\n")
        yield self.server_send_line(b"250-mail.example.com welcome\r\n")
        yield self.server_send_line(b"250 STARTTLS\r\n")
        yield self.client_send_line(b"STARTTLS\r\n")
        yield self.server_send_line(b"220 Go ahead\r\n")
        client_future = self.client_start_tls(dict(cert_reqs=ssl.CERT_NONE))
        server_future = self.server_start_tls(_server_ssl_options())
        self.client_stream = yield client_future
        self.server_stream = yield server_future
        self.assertTrue(isinstance(self.client_stream, SSLIOStream))
        self.assertTrue(isinstance(self.server_stream, SSLIOStream))
        yield self.client_send_line(b"EHLO mail.example.com\r\n")
        yield self.server_send_line(b"250 mail.example.com welcome\r\n")

    @gen_test
    def test_handshake_fail(self):
        server_future = self.server_start_tls(_server_ssl_options())
        # Certificates are verified with the default configuration.
        with ExpectLog(gen_log, "SSL Error"):
            client_future = self.client_start_tls(server_hostname="localhost")
            with self.assertRaises(ssl.SSLError):
                yield client_future
            with self.assertRaises((ssl.SSLError, socket.error)):
                yield server_future

    @gen_test
    def test_check_hostname(self):
        # Test that server_hostname parameter to start_tls is being used.
        server_future = self.server_start_tls(_server_ssl_options())
        with ExpectLog(gen_log, "SSL Error"):
            client_future = self.client_start_tls(
                ssl.create_default_context(), server_hostname="127.0.0.1"
            )
            with self.assertRaises(ssl.SSLError):
                # The client fails to connect with an SSL error.
                yield client_future
            with self.assertRaises(Exception):
                # The server fails to connect, but the exact error is unspecified.
                yield server_future

    @gen_test
    def test_typed_memoryview(self):
        # Test support of memoryviews with an item size greater than 1 byte.
        buf = memoryview(bytes(80)).cast("L")
        assert self.server_stream is not None
        yield self.server_stream.write(buf)
        assert self.client_stream is not None
        # This will timeout if the calculation of the buffer size is incorrect
        recv = yield self.client_stream.read_bytes(buf.nbytes)
        self.assertEqual(bytes(recv), bytes(buf))


class WaitForHandshakeTest(AsyncTestCase):
    @gen.coroutine
    def connect_to_server(self, server_cls):
        server = client = None
        try:
            sock, port = bind_unused_port()
            server = server_cls(ssl_options=_server_ssl_options())
            server.add_socket(sock)

            ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            # These tests fail with ConnectionAbortedErrors with TLS
            # 1.3 on windows python 3.7.4 (which includes an upgrade
            # to openssl 1.1.c. Other platforms might be affected with
            # newer openssl too). Disable it until we figure out
            # what's up.
            # Update 2021-12-28: Still happening with Python 3.10 on
            # Windows. OP_NO_TLSv1_3 now raises a DeprecationWarning.
            with ignore_deprecation():
                ssl_ctx.options |= getattr(ssl, "OP_NO_TLSv1_3", 0)
                client = SSLIOStream(socket.socket(), ssl_options=ssl_ctx)
            yield client.connect(("127.0.0.1", port))
            self.assertIsNotNone(client.socket.cipher())
        finally:
            if server is not None:
                server.stop()
            if client is not None:
                client.close()

    @gen_test
    def test_wait_for_handshake_future(self):
        test = self
        handshake_future = Future()  # type: Future[None]

        class TestServer(TCPServer):
            def handle_stream(self, stream, address):
                test.assertIsNone(stream.socket.cipher())
                test.io_loop.spawn_callback(self.handle_connection, stream)

            @gen.coroutine
            def handle_connection(self, stream):
                yield stream.wait_for_handshake()
                handshake_future.set_result(None)

        yield self.connect_to_server(TestServer)
        yield handshake_future

    @gen_test
    def test_wait_for_handshake_already_waiting_error(self):
        test = self
        handshake_future = Future()  # type: Future[None]

        class TestServer(TCPServer):
            @gen.coroutine
            def handle_stream(self, stream, address):
                fut = stream.wait_for_handshake()
                test.assertRaises(RuntimeError, stream.wait_for_handshake)
                yield fut

                handshake_future.set_result(None)

        yield self.connect_to_server(TestServer)
        yield handshake_future

    @gen_test
    def test_wait_for_handshake_already_connected(self):
        handshake_future = Future()  # type: Future[None]

        class TestServer(TCPServer):
            @gen.coroutine
            def handle_stream(self, stream, address):
                yield stream.wait_for_handshake()
                yield stream.wait_for_handshake()
                handshake_future.set_result(None)

        yield self.connect_to_server(TestServer)
        yield handshake_future


class TestIOStreamCheckHostname(AsyncTestCase):
    # This test ensures that hostname checks are working correctly after
    # #3337 revealed that we have no test coverage in this area, and we
    # removed a manual hostname check that was needed only for very old
    # versions of python.
    def setUp(self):
        super().setUp()
        self.listener, self.port = bind_unused_port()

        def accept_callback(connection, address):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(
                os.path.join(os.path.dirname(__file__), "test.crt"),
                os.path.join(os.path.dirname(__file__), "test.key"),
            )
            connection = ssl_ctx.wrap_socket(
                connection,
                server_side=True,
                do_handshake_on_connect=False,
            )
            SSLIOStream(connection)

        netutil.add_accept_handler(self.listener, accept_callback)

        # Our self-signed cert is its own CA.  We have to pass the CA check before
        # the hostname check will be performed.
        self.client_ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.client_ssl_ctx.load_verify_locations(
            os.path.join(os.path.dirname(__file__), "test.crt")
        )

    def tearDown(self):
        self.io_loop.remove_handler(self.listener.fileno())
        self.listener.close()
        super().tearDown()

    @gen_test
    async def test_match(self):
        stream = SSLIOStream(socket.socket(), ssl_options=self.client_ssl_ctx)
        await stream.connect(
            ("127.0.0.1", self.port),
            server_hostname="foo.example.com",
        )
        stream.close()

    @gen_test
    async def test_no_match(self):
        stream = SSLIOStream(socket.socket(), ssl_options=self.client_ssl_ctx)
        with ExpectLog(
            gen_log,
            ".*alert bad certificate",
            level=logging.WARNING,
            required=platform.system() != "Windows",
        ):
            with self.assertRaises(ssl.SSLCertVerificationError):
                with ExpectLog(
                    gen_log,
                    ".*(certificate verify failed: Hostname mismatch)",
                    level=logging.WARNING,
                ):
                    await stream.connect(
                        ("127.0.0.1", self.port),
                        server_hostname="bar.example.com",
                    )
            # The server logs a warning while cleaning up the failed connection.
            # Unfortunately there's no good hook to wait for this logging.
            # It doesn't seem to happen on windows; I'm not sure why.
            if platform.system() != "Windows":
                await asyncio.sleep(0.1)

    @gen_test
    async def test_check_disabled(self):
        # check_hostname can be set to false and the connection will succeed even though it doesn't
        # have the right hostname.
        self.client_ssl_ctx.check_hostname = False
        stream = SSLIOStream(socket.socket(), ssl_options=self.client_ssl_ctx)
        await stream.connect(
            ("127.0.0.1", self.port),
            server_hostname="bar.example.com",
        )


@skipIfNonUnix
class TestPipeIOStream(TestReadWriteMixin, AsyncTestCase):
    @gen.coroutine
    def make_iostream_pair(self, **kwargs):
        r, w = os.pipe()

        return PipeIOStream(r, **kwargs), PipeIOStream(w, **kwargs)

    @gen_test
    def test_pipe_iostream(self):
        rs, ws = yield self.make_iostream_pair()

        ws.write(b"hel")
        ws.write(b"lo world")

        data = yield rs.read_until(b" ")
        self.assertEqual(data, b"hello ")

        data = yield rs.read_bytes(3)
        self.assertEqual(data, b"wor")

        ws.close()

        data = yield rs.read_until_close()
        self.assertEqual(data, b"ld")

        rs.close()

    @gen_test
    def test_pipe_iostream_big_write(self):
        rs, ws = yield self.make_iostream_pair()

        NUM_BYTES = 1048576

        # Write 1MB of data, which should fill the buffer
        ws.write(b"1" * NUM_BYTES)

        data = yield rs.read_bytes(NUM_BYTES)
        self.assertEqual(data, b"1" * NUM_BYTES)

        ws.close()
        rs.close()


class TestStreamBuffer(unittest.TestCase):
    """
    Unit tests for the private _StreamBuffer class.
    """

    def setUp(self):
        self.random = random.Random(42)

    def to_bytes(self, b):
        if isinstance(b, (bytes, bytearray)):
            return bytes(b)
        elif isinstance(b, memoryview):
            return b.tobytes()  # For py2
        else:
            raise TypeError(b)

    def make_streambuffer(self, large_buf_threshold=10):
        buf = _StreamBuffer()
        assert buf._large_buf_threshold
        buf._large_buf_threshold = large_buf_threshold
        return buf

    def check_peek(self, buf, expected):
        size = 1
        while size < 2 * len(expected):
            got = self.to_bytes(buf.peek(size))
            self.assertTrue(got)  # Not empty
            self.assertLessEqual(len(got), size)
            self.assertTrue(expected.startswith(got), (expected, got))
            size = (size * 3 + 1) // 2

    def check_append_all_then_skip_all(self, buf, objs, input_type):
        self.assertEqual(len(buf), 0)

        expected = b""

        for o in objs:
            expected += o
            buf.append(input_type(o))
            self.assertEqual(len(buf), len(expected))
            self.check_peek(buf, expected)

        while expected:
            n = self.random.randrange(1, len(expected) + 1)
            expected = expected[n:]
            buf.advance(n)
            self.assertEqual(len(buf), len(expected))
            self.check_peek(buf, expected)

        self.assertEqual(len(buf), 0)

    def test_small(self):
        objs = [b"12", b"345", b"67", b"89a", b"bcde", b"fgh", b"ijklmn"]

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, bytes)

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, bytearray)

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, memoryview)

        # Test internal algorithm
        buf = self.make_streambuffer(10)
        for i in range(9):
            buf.append(b"x")
        self.assertEqual(len(buf._buffers), 1)
        for i in range(9):
            buf.append(b"x")
        self.assertEqual(len(buf._buffers), 2)
        buf.advance(10)
        self.assertEqual(len(buf._buffers), 1)
        buf.advance(8)
        self.assertEqual(len(buf._buffers), 0)
        self.assertEqual(len(buf), 0)

    def test_large(self):
        objs = [
            b"12" * 5,
            b"345" * 2,
            b"67" * 20,
            b"89a" * 12,
            b"bcde" * 1,
            b"fgh" * 7,
            b"ijklmn" * 2,
        ]

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, bytes)

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, bytearray)

        buf = self.make_streambuffer()
        self.check_append_all_then_skip_all(buf, objs, memoryview)

        # Test internal algorithm
        buf = self.make_streambuffer(10)
        for i in range(3):
            buf.append(b"x" * 11)
        self.assertEqual(len(buf._buffers), 3)
        buf.append(b"y")
        self.assertEqual(len(buf._buffers), 4)
        buf.append(b"z")
        self.assertEqual(len(buf._buffers), 4)
        buf.advance(33)
        self.assertEqual(len(buf._buffers), 1)
        buf.advance(2)
        self.assertEqual(len(buf._buffers), 0)
        self.assertEqual(len(buf), 0)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\pass_through_endpoints.py ===
import ast
import asyncio
import copy
import json
import traceback
import uuid
from base64 import b64encode
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import MAXIMUM_TRACEBACK_LINES_TO_LOG
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.llms.custom_httpx.http_handler import get_async_httpx_client
from litellm.passthrough import BasePassthroughUtils
from litellm.proxy._types import (
    ConfigFieldInfo,
    ConfigFieldUpdate,
    PassThroughEndpointResponse,
    PassThroughGenericEndpoint,
    ProxyException,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from litellm.proxy.common_utils.http_parsing_utils import _read_request_body
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.custom_http import httpxSpecialProvider
from litellm.types.passthrough_endpoints.pass_through_endpoints import (
    EndpointType,
    PassthroughStandardLoggingPayload,
)
from litellm.types.utils import StandardLoggingUserAPIKeyMetadata

from .streaming_handler import PassThroughStreamingHandler
from .success_handler import PassThroughEndpointLogging

router = APIRouter()

pass_through_endpoint_logging = PassThroughEndpointLogging()


def get_response_body(response: httpx.Response) -> Optional[dict]:
    try:
        return response.json()
    except Exception:
        return None


async def set_env_variables_in_header(custom_headers: Optional[dict]) -> Optional[dict]:
    """
    checks if any headers on config.yaml are defined as os.environ/COHERE_API_KEY etc

    only runs for headers defined on config.yaml

    example header can be

    {"Authorization": "bearer os.environ/COHERE_API_KEY"}
    """
    if custom_headers is None:
        return None
    headers = {}
    for key, value in custom_headers.items():
        # langfuse Api requires base64 encoded headers - it's simpleer to just ask litellm users to set their langfuse public and secret keys
        # we can then get the b64 encoded keys here
        if key == "LANGFUSE_PUBLIC_KEY" or key == "LANGFUSE_SECRET_KEY":
            # langfuse requires b64 encoded headers - we construct that here
            _langfuse_public_key = custom_headers["LANGFUSE_PUBLIC_KEY"]
            _langfuse_secret_key = custom_headers["LANGFUSE_SECRET_KEY"]
            if isinstance(
                _langfuse_public_key, str
            ) and _langfuse_public_key.startswith("os.environ/"):
                _langfuse_public_key = get_secret_str(_langfuse_public_key)
            if isinstance(
                _langfuse_secret_key, str
            ) and _langfuse_secret_key.startswith("os.environ/"):
                _langfuse_secret_key = get_secret_str(_langfuse_secret_key)
            headers["Authorization"] = "Basic " + b64encode(
                f"{_langfuse_public_key}:{_langfuse_secret_key}".encode("utf-8")
            ).decode("ascii")
        else:
            # for all other headers
            headers[key] = value
            if isinstance(value, str) and "os.environ/" in value:
                verbose_proxy_logger.debug(
                    "pass through endpoint - looking up 'os.environ/' variable"
                )
                # get string section that is os.environ/
                start_index = value.find("os.environ/")
                _variable_name = value[start_index:]

                verbose_proxy_logger.debug(
                    "pass through endpoint - getting secret for variable name: %s",
                    _variable_name,
                )
                _secret_value = get_secret_str(_variable_name)
                if _secret_value is not None:
                    new_value = value.replace(_variable_name, _secret_value)
                    headers[key] = new_value
    return headers


async def chat_completion_pass_through_endpoint(  # noqa: PLR0915
    fastapi_response: Response,
    request: Request,
    adapter_id: str,
    user_api_key_dict: UserAPIKeyAuth,
):
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    data = {}
    try:
        body = await request.body()
        body_str = body.decode()
        try:
            data = ast.literal_eval(body_str)
        except Exception:
            data = json.loads(body_str)

        data["adapter_id"] = adapter_id

        verbose_proxy_logger.debug(
            "Request received by LiteLLM:\n{}".format(json.dumps(data, indent=4)),
        )
        data["model"] = (
            general_settings.get("completion_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        data = await add_litellm_data_to_request(
            data=data,  # type: ignore
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # override with user settings, these are params passed via cli
        if user_temperature:
            data["temperature"] = user_temperature
        if user_request_timeout:
            data["request_timeout"] = user_request_timeout
        if user_max_tokens:
            data["max_tokens"] = user_max_tokens
        if user_api_base:
            data["api_base"] = user_api_base

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in litellm.model_alias_map:
            data["model"] = litellm.model_alias_map[data["model"]]

        ### CALL HOOKS ### - modify incoming data before calling the model
        data = await proxy_logging_obj.pre_call_hook(  # type: ignore
            user_api_key_dict=user_api_key_dict, data=data, call_type="text_completion"
        )

        ### ROUTE THE REQUESTs ###
        router_model_names = llm_router.model_names if llm_router is not None else []
        # skip router if user passed their key
        if "api_key" in data:
            llm_response = asyncio.create_task(litellm.aadapter_completion(**data))
        elif (
            llm_router is not None and data["model"] in router_model_names
        ):  # model in router model list
            llm_response = asyncio.create_task(llm_router.aadapter_completion(**data))
        elif (
            llm_router is not None
            and llm_router.model_group_alias is not None
            and data["model"] in llm_router.model_group_alias
        ):  # model set in model_group_alias
            llm_response = asyncio.create_task(llm_router.aadapter_completion(**data))
        elif (
            llm_router is not None and data["model"] in llm_router.deployment_names
        ):  # model in router deployments, calling a specific deployment on the router
            llm_response = asyncio.create_task(
                llm_router.aadapter_completion(**data, specific_deployment=True)
            )
        elif (
            llm_router is not None and data["model"] in llm_router.get_model_ids()
        ):  # model in router model list
            llm_response = asyncio.create_task(llm_router.aadapter_completion(**data))
        elif (
            llm_router is not None
            and data["model"] not in router_model_names
            and llm_router.default_deployment is not None
        ):  # model in router deployments, calling a specific deployment on the router
            llm_response = asyncio.create_task(llm_router.aadapter_completion(**data))
        elif user_model is not None:  # `litellm --model <your-model-name>`
            llm_response = asyncio.create_task(litellm.aadapter_completion(**data))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "completion: Invalid model name passed in model="
                    + data.get("model", "")
                },
            )

        # Await the llm_response task
        response = await llm_response

        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        verbose_proxy_logger.debug("final response: %s", response)

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
            )
        )

        verbose_proxy_logger.info("\nResponse from Litellm:\n{}".format(response))
        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.completion(): Exception occured - {}".format(
                str(e)
            )
        )
        error_msg = f"{str(e)}"
        raise ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )


class HttpPassThroughEndpointHelpers(BasePassthroughUtils):
    @staticmethod
    def get_response_headers(
        headers: httpx.Headers,
        litellm_call_id: Optional[str] = None,
        custom_headers: Optional[dict] = None,
    ) -> dict:
        excluded_headers = {"transfer-encoding", "content-encoding"}

        return_headers = {
            key: value
            for key, value in headers.items()
            if key.lower() not in excluded_headers
        }
        if litellm_call_id:
            return_headers["x-litellm-call-id"] = litellm_call_id
        if custom_headers:
            return_headers.update(custom_headers)

        return return_headers

    @staticmethod
    def get_endpoint_type(url: str) -> EndpointType:
        parsed_url = urlparse(url)
        if (
            ("generateContent") in url
            or ("streamGenerateContent") in url
            or ("rawPredict") in url
            or ("streamRawPredict") in url
        ):
            return EndpointType.VERTEX_AI
        elif parsed_url.hostname == "api.anthropic.com":
            return EndpointType.ANTHROPIC
        return EndpointType.GENERIC

    @staticmethod
    async def _make_non_streaming_http_request(
        request: Request,
        async_client: httpx.AsyncClient,
        url: str,
        headers: dict,
        requested_query_params: Optional[dict] = None,
        custom_body: Optional[dict] = None,
    ) -> httpx.Response:
        """
        Make a non-streaming HTTP request

        If request is GET, don't include a JSON body
        """
        if request.method == "GET":
            response = await async_client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=requested_query_params,
            )
        else:
            response = await async_client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=requested_query_params,
                json=custom_body,
            )
        return response

    @staticmethod
    async def non_streaming_http_request_handler(
        request: Request,
        async_client: httpx.AsyncClient,
        url: httpx.URL,
        headers: dict,
        requested_query_params: Optional[dict] = None,
        _parsed_body: Optional[dict] = None,
    ) -> httpx.Response:
        """
        Handle non-streaming HTTP requests

        Handles special cases when GET requests, multipart/form-data requests, and generic httpx requests
        """
        if request.method == "GET":
            response = await async_client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=requested_query_params,
            )
        elif HttpPassThroughEndpointHelpers.is_multipart(request) is True:
            return await HttpPassThroughEndpointHelpers.make_multipart_http_request(
                request=request,
                async_client=async_client,
                url=url,
                headers=headers,
                requested_query_params=requested_query_params,
            )
        else:
            # Generic httpx method
            response = await async_client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=requested_query_params,
                json=_parsed_body,
            )
        return response

    @staticmethod
    def is_multipart(request: Request) -> bool:
        """Check if the request is a multipart/form-data request"""
        return "multipart/form-data" in request.headers.get("content-type", "")

    @staticmethod
    async def _build_request_files_from_upload_file(
        upload_file: Union[UploadFile, StarletteUploadFile],
    ) -> Tuple[Optional[str], bytes, Optional[str]]:
        """Build a request files dict from an UploadFile object"""
        file_content = await upload_file.read()
        return (upload_file.filename, file_content, upload_file.content_type)

    @staticmethod
    async def make_multipart_http_request(
        request: Request,
        async_client: httpx.AsyncClient,
        url: httpx.URL,
        headers: dict,
        requested_query_params: Optional[dict] = None,
    ) -> httpx.Response:
        """Process multipart/form-data requests, handling both files and form fields"""
        form_data = await request.form()
        files = {}
        form_data_dict = {}

        for field_name, field_value in form_data.items():
            if isinstance(field_value, (StarletteUploadFile, UploadFile)):
                files[field_name] = (
                    await HttpPassThroughEndpointHelpers._build_request_files_from_upload_file(
                        upload_file=field_value
                    )
                )
            else:
                form_data_dict[field_name] = field_value

        response = await async_client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=requested_query_params,
            files=files,
            data=form_data_dict,
        )
        return response

    @staticmethod
    def _init_kwargs_for_pass_through_endpoint(
        request: Request,
        user_api_key_dict: UserAPIKeyAuth,
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
        logging_obj: LiteLLMLoggingObj,
        _parsed_body: Optional[dict] = None,
        litellm_call_id: Optional[str] = None,
    ) -> dict:
        _parsed_body = _parsed_body or {}
        _litellm_metadata: Optional[dict] = _parsed_body.pop("litellm_metadata", None)
        _metadata = dict(
            StandardLoggingUserAPIKeyMetadata(
                user_api_key_hash=user_api_key_dict.api_key,
                user_api_key_alias=user_api_key_dict.key_alias,
                user_api_key_user_email=user_api_key_dict.user_email,
                user_api_key_user_id=user_api_key_dict.user_id,
                user_api_key_team_id=user_api_key_dict.team_id,
                user_api_key_org_id=user_api_key_dict.org_id,
                user_api_key_team_alias=user_api_key_dict.team_alias,
                user_api_key_end_user_id=user_api_key_dict.end_user_id,
                user_api_key_request_route=user_api_key_dict.request_route,
            )
        )
        _metadata["user_api_key"] = user_api_key_dict.api_key
        if _litellm_metadata:
            _metadata.update(_litellm_metadata)

        _metadata = _update_metadata_with_tags_in_header(
            request=request,
            metadata=_metadata,
        )

        kwargs = {
            "litellm_params": {
                "metadata": _metadata,
                "proxy_server_request": {
                        "url": str(request.url),
                        "method": request.method,
                        "body": copy.copy(_parsed_body),  # use copy instead of deepcopy
                    }
            },
            "call_type": "pass_through_endpoint",
            "litellm_call_id": litellm_call_id,
            "passthrough_logging_payload": passthrough_logging_payload,
        }

        logging_obj.model_call_details["passthrough_logging_payload"] = (
            passthrough_logging_payload
        )

        return kwargs

    @staticmethod
    def construct_target_url_with_subpath(
        base_target: str, subpath: str, include_subpath: Optional[bool]
    ) -> str:
        """
        Helper function to construct the full target URL with subpath handling.

        Args:
            base_target: The base target URL
            subpath: The captured subpath from the request
            include_subpath: Whether to include the subpath in the target URL

        Returns:
            The constructed full target URL
        """
        if not include_subpath:
            return base_target

        if not subpath:
            return base_target

        # Ensure base_target ends with / and subpath doesn't start with /
        if not base_target.endswith("/"):
            base_target = base_target + "/"
        if subpath.startswith("/"):
            subpath = subpath[1:]

        return base_target + subpath


async def pass_through_request(  # noqa: PLR0915
    request: Request,
    target: str,
    custom_headers: dict,
    user_api_key_dict: UserAPIKeyAuth,
    custom_body: Optional[dict] = None,
    forward_headers: Optional[bool] = False,
    merge_query_params: Optional[bool] = False,
    query_params: Optional[dict] = None,
    stream: Optional[bool] = None,
    cost_per_request: Optional[float] = None,
):
    """
    Pass through endpoint handler, makes the httpx request for pass-through endpoints and ensures logging hooks are called

    Args:
        request: The incoming request
        target: The target URL
        custom_headers: The custom headers
        user_api_key_dict: The user API key dictionary
        custom_body: The custom body
        forward_headers: Whether to forward headers
        merge_query_params: Whether to merge query params
        query_params: The query params
        stream: Whether to stream the response
        cost_per_request: Optional field - cost per request to the target endpoint
    """
    from litellm.litellm_core_utils.litellm_logging import Logging
    from litellm.proxy.proxy_server import proxy_logging_obj

    #########################################################
    # Initialize variables
    #########################################################
    litellm_call_id = str(uuid.uuid4())
    url: Optional[httpx.URL] = None

    # parsed request body
    _parsed_body: Optional[dict] = None
    # kwargs for pass through endpoint, contains metadata, litellm_params, call_type, litellm_call_id, passthrough_logging_payload
    kwargs: Optional[dict] = None

    #########################################################
    try:
        url = httpx.URL(target)
        headers = custom_headers
        headers = HttpPassThroughEndpointHelpers.forward_headers_from_request(
            request_headers=dict(request.headers),
            headers=headers,
            forward_headers=forward_headers,
        )

        if merge_query_params:
            # Create a new URL with the merged query params
            url = url.copy_with(
                query=urlencode(
                    HttpPassThroughEndpointHelpers.get_merged_query_parameters(
                        existing_url=url,
                        request_query_params=dict(request.query_params),
                    )
                ).encode("ascii")
            )

        endpoint_type: EndpointType = HttpPassThroughEndpointHelpers.get_endpoint_type(
            str(url)
        )

        if custom_body:
            _parsed_body = custom_body
        else:
            _parsed_body = await _read_request_body(request)
        verbose_proxy_logger.debug(
            "Pass through endpoint sending request to \nURL {}\nheaders: {}\nbody: {}\n".format(
                url, headers, _parsed_body
            )
        )

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        _parsed_body = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict,
            data=_parsed_body,
            call_type="pass_through_endpoint",
        )
        async_client_obj = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.PassThroughEndpoint,
            params={"timeout": 600},
        )
        async_client = async_client_obj.client

        # create logging object
        start_time = datetime.now()
        logging_obj = Logging(
            model="unknown",
            messages=[{"role": "user", "content": safe_dumps(_parsed_body)}],
            stream=False,
            call_type="pass_through_endpoint",
            start_time=start_time,
            litellm_call_id=litellm_call_id,
            function_id="1245",
        )
        passthrough_logging_payload = PassthroughStandardLoggingPayload(
            url=str(url),
            request_body=_parsed_body,
            request_method=getattr(request, "method", None),
            cost_per_request=cost_per_request,
        )
        kwargs = HttpPassThroughEndpointHelpers._init_kwargs_for_pass_through_endpoint(
            user_api_key_dict=user_api_key_dict,
            _parsed_body=_parsed_body,
            passthrough_logging_payload=passthrough_logging_payload,
            litellm_call_id=litellm_call_id,
            request=request,
            logging_obj=logging_obj,
        )
        # done for supporting 'parallel_request_limiter.py' with pass-through endpoints
        logging_obj.update_environment_variables(
            model="unknown",
            user="unknown",
            optional_params={},
            litellm_params=kwargs["litellm_params"],
            call_type="pass_through_endpoint",
        )
        logging_obj.model_call_details["litellm_call_id"] = litellm_call_id

        # combine url with query params for logging
        requested_query_params: Optional[dict] = (
            query_params or request.query_params.__dict__
        )
        if requested_query_params == request.query_params.__dict__:
            requested_query_params = None

        requested_query_params_str = None
        if requested_query_params:
            requested_query_params_str = "&".join(
                f"{k}={v}" for k, v in requested_query_params.items()
            )

        logging_url = str(url)
        if requested_query_params_str:
            if "?" in str(url):
                logging_url = str(url) + "&" + requested_query_params_str
            else:
                logging_url = str(url) + "?" + requested_query_params_str

        logging_obj.pre_call(
            input=[{"role": "user", "content": safe_dumps(_parsed_body)}],
            api_key="",
            additional_args={
                "complete_input_dict": _parsed_body,
                "api_base": str(logging_url),
                "headers": headers,
            },
        )
        if stream:
            req = async_client.build_request(
                "POST",
                url,
                json=_parsed_body,
                params=requested_query_params,
                headers=headers,
            )

            response = await async_client.send(req, stream=stream)

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code, detail=await e.response.aread()
                )

            return StreamingResponse(
                PassThroughStreamingHandler.chunk_processor(
                    response=response,
                    request_body=_parsed_body,
                    litellm_logging_obj=logging_obj,
                    endpoint_type=endpoint_type,
                    start_time=start_time,
                    passthrough_success_handler_obj=pass_through_endpoint_logging,
                    url_route=str(url),
                ),
                headers=HttpPassThroughEndpointHelpers.get_response_headers(
                    headers=response.headers,
                    litellm_call_id=litellm_call_id,
                ),
                status_code=response.status_code,
            )

        verbose_proxy_logger.debug("request method: {}".format(request.method))
        verbose_proxy_logger.debug("request url: {}".format(url))
        verbose_proxy_logger.debug("request headers: {}".format(headers))
        verbose_proxy_logger.debug(
            "requested_query_params={}".format(requested_query_params)
        )
        verbose_proxy_logger.debug("request body: {}".format(_parsed_body))

        response = (
            await HttpPassThroughEndpointHelpers.non_streaming_http_request_handler(
                request=request,
                async_client=async_client,
                url=url,
                headers=headers,
                requested_query_params=requested_query_params,
                _parsed_body=_parsed_body,
            )
        )
        verbose_proxy_logger.debug("response.headers= %s", response.headers)

        if _is_streaming_response(response) is True:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code, detail=await e.response.aread()
                )

            return StreamingResponse(
                PassThroughStreamingHandler.chunk_processor(
                    response=response,
                    request_body=_parsed_body,
                    litellm_logging_obj=logging_obj,
                    endpoint_type=endpoint_type,
                    start_time=start_time,
                    passthrough_success_handler_obj=pass_through_endpoint_logging,
                    url_route=str(url),
                ),
                headers=HttpPassThroughEndpointHelpers.get_response_headers(
                    headers=response.headers,
                    litellm_call_id=litellm_call_id,
                ),
                status_code=response.status_code,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.text
            )

        if response.status_code >= 300:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        content = await response.aread()

        ## LOG SUCCESS
        response_body: Optional[dict] = get_response_body(response)
        passthrough_logging_payload["response_body"] = response_body
        end_time = datetime.now()
        asyncio.create_task(
            pass_through_endpoint_logging.pass_through_async_success_handler(
                httpx_response=response,
                response_body=response_body,
                url_route=str(url),
                result="",
                start_time=start_time,
                end_time=end_time,
                logging_obj=logging_obj,
                cache_hit=False,
                request_body=_parsed_body,
                **kwargs,
            )
        )

        ## CUSTOM HEADERS - `x-litellm-*`
        custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
            user_api_key_dict=user_api_key_dict,
            call_id=litellm_call_id,
            model_id=None,
            cache_key=None,
            api_base=str(url._uri_reference),
        )

        return Response(
            content=content,
            status_code=response.status_code,
            headers=HttpPassThroughEndpointHelpers.get_response_headers(
                headers=response.headers,
                custom_headers=custom_headers,
            ),
        )
    except Exception as e:
        custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
            user_api_key_dict=user_api_key_dict,
            call_id=litellm_call_id,
            model_id=None,
            cache_key=None,
            api_base=str(url._uri_reference) if url else None,
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.pass_through_endpoint(): Exception occured - {}".format(
                str(e)
            )
        )

        #########################################################
        # Monitoring: Trigger post_call_failure_hook
        # for pass through endpoint failure
        #########################################################
        request_payload: dict = _parsed_body or {}
        # add user_api_key_dict, litellm_call_id, passthrough_logging_payloa for logging
        if kwargs:
            for key, value in kwargs.items():
                request_payload[key] = value
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=request_payload,
            traceback_str=traceback.format_exc(
                limit=MAXIMUM_TRACEBACK_LINES_TO_LOG,
            ),
        )

        #########################################################

        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
                headers=custom_headers,
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
                headers=custom_headers,
            )


def _update_metadata_with_tags_in_header(request: Request, metadata: dict) -> dict:
    """
    If tags are in the request headers, add them to the metadata

    Used for google and vertex JS SDKs
    """
    _tags = request.headers.get("tags")
    if _tags:
        metadata["tags"] = _tags.split(",")
    return metadata


def create_pass_through_route(
    endpoint,
    target: str,
    custom_headers: Optional[dict] = None,
    _forward_headers: Optional[bool] = False,
    _merge_query_params: Optional[bool] = False,
    dependencies: Optional[List] = None,
    include_subpath: Optional[bool] = False,
    cost_per_request: Optional[float] = None,
):
    # check if target is an adapter.py or a url
    import uuid

    from litellm.proxy.types_utils.utils import get_instance_fn

    try:
        if isinstance(target, CustomLogger):
            adapter = target
        else:
            adapter = get_instance_fn(value=target)
        adapter_id = str(uuid.uuid4())
        litellm.adapters = [{"id": adapter_id, "adapter": adapter}]

        async def endpoint_func(  # type: ignore
            request: Request,
            fastapi_response: Response,
            user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
            subpath: str = "",  # captures sub-paths when include_subpath=True
        ):
            return await chat_completion_pass_through_endpoint(
                fastapi_response=fastapi_response,
                request=request,
                adapter_id=adapter_id,
                user_api_key_dict=user_api_key_dict,
            )

    except Exception:
        verbose_proxy_logger.debug("Defaulting to target being a url.")

        async def endpoint_func(  # type: ignore
            request: Request,
            fastapi_response: Response,
            user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
            query_params: Optional[dict] = None,
            custom_body: Optional[dict] = None,
            stream: Optional[
                bool
            ] = None,  # if pass-through endpoint is a streaming request
            subpath: str = "",  # captures sub-paths when include_subpath=True
        ):
            # Construct the full target URL with subpath if needed
            full_target = (
                HttpPassThroughEndpointHelpers.construct_target_url_with_subpath(
                    base_target=target, subpath=subpath, include_subpath=include_subpath
                )
            )

            return await pass_through_request(  # type: ignore
                request=request,
                target=full_target,
                custom_headers=custom_headers or {},
                user_api_key_dict=user_api_key_dict,
                forward_headers=_forward_headers,
                merge_query_params=_merge_query_params,
                query_params=query_params,
                stream=stream,
                custom_body=custom_body,
                cost_per_request=cost_per_request,
            )

    return endpoint_func


def _is_streaming_response(response: httpx.Response) -> bool:
    _content_type = response.headers.get("content-type")
    if _content_type is not None and "text/event-stream" in _content_type:
        return True
    return False


class InitPassThroughEndpointHelpers:
    @staticmethod
    def add_exact_path_route(
        app: FastAPI,
        path: str,
        target: str,
        custom_headers: Optional[dict],
        forward_headers: Optional[bool],
        merge_query_params: Optional[bool],
        dependencies: Optional[List],
        cost_per_request: Optional[float],
    ):
        """Add exact path route for pass-through endpoint"""
        verbose_proxy_logger.debug(
            "adding exact pass through endpoint: %s, dependencies: %s",
            path,
            dependencies,
        )

        app.add_api_route(
            path=path,
            endpoint=create_pass_through_route(
                path,
                target,
                custom_headers,
                forward_headers,
                merge_query_params,
                dependencies,
                cost_per_request=cost_per_request,
            ),
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            dependencies=dependencies,
        )

    @staticmethod
    def add_subpath_route(
        app: FastAPI,
        path: str,
        target: str,
        custom_headers: Optional[dict],
        forward_headers: Optional[bool],
        merge_query_params: Optional[bool],
        dependencies: Optional[List],
        cost_per_request: Optional[float],
    ):
        """Add wildcard route for sub-paths"""
        wildcard_path = f"{path}/{{subpath:path}}"
        verbose_proxy_logger.debug(
            "adding wildcard pass through endpoint: %s, dependencies: %s",
            wildcard_path,
            dependencies,
        )

        app.add_api_route(
            path=wildcard_path,
            endpoint=create_pass_through_route(
                path,
                target,
                custom_headers,
                forward_headers,
                merge_query_params,
                dependencies,
                include_subpath=True,
                cost_per_request=cost_per_request,
            ),
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            dependencies=dependencies,
        )


async def initialize_pass_through_endpoints(
    pass_through_endpoints: Union[List[Dict], List[PassThroughGenericEndpoint]],
):
    """
    Initialize a list of pass-through endpoints by adding them to the FastAPI app routes

    Args:
        pass_through_endpoints: List of pass-through endpoints to initialize

    Returns:
        None
    """
    import uuid
    verbose_proxy_logger.debug("initializing pass through endpoints")
    from litellm.proxy._types import CommonProxyErrors, LiteLLMRoutes
    from litellm.proxy.proxy_server import app, premium_user

    for endpoint in pass_through_endpoints:
        if isinstance(endpoint, PassThroughGenericEndpoint):
            endpoint = endpoint.model_dump()
        
        # Auto-generate ID for backwards compatibility if not present
        if endpoint.get("id") is None:
            endpoint["id"] = str(uuid.uuid4())
            
        _target = endpoint.get("target", None)
        _path: Optional[str] = endpoint.get("path", None)
        if _path is None:
            raise ValueError("Path is required for pass-through endpoint")
        _custom_headers = endpoint.get("headers", None)
        _custom_headers = await set_env_variables_in_header(
            custom_headers=_custom_headers
        )
        _forward_headers = endpoint.get("forward_headers", None)
        _merge_query_params = endpoint.get("merge_query_params", None)
        _auth = endpoint.get("auth", None)
        _dependencies = None
        if _auth is not None and str(_auth).lower() == "true":
            if premium_user is not True:
                raise ValueError(
                    "Error Setting Authentication on Pass Through Endpoint: {}".format(
                        CommonProxyErrors.not_premium_user.value
                    )
                )
            _dependencies = [Depends(user_api_key_auth)]
            LiteLLMRoutes.openai_routes.value.append(_path)

        if _target is None:
            continue

        # Add exact path route
        verbose_proxy_logger.debug("Initializing pass through endpoint: %s (ID: %s)", _path, endpoint.get("id"))
        InitPassThroughEndpointHelpers.add_exact_path_route(
            app=app,
            path=_path,
            target=_target,
            custom_headers=_custom_headers,
            forward_headers=_forward_headers,
            merge_query_params=_merge_query_params,
            dependencies=_dependencies,
            cost_per_request=endpoint.get("cost_per_request", None),
        )

        # Add wildcard route for sub-paths
        if endpoint.get("include_subpath", False) is True:
            InitPassThroughEndpointHelpers.add_subpath_route(
                app=app,
                path=_path,
                target=_target,
                custom_headers=_custom_headers,
                forward_headers=_forward_headers,
                merge_query_params=_merge_query_params,
                dependencies=_dependencies,
                cost_per_request=endpoint.get("cost_per_request", None),
            )

        verbose_proxy_logger.debug("Added new pass through endpoint: %s (ID: %s)", _path, endpoint.get("id"))


async def _get_pass_through_endpoints_from_db(
    endpoint_id: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> List[PassThroughGenericEndpoint]:
    from litellm.proxy.proxy_server import get_config_general_settings

    try:
        response: ConfigFieldInfo = await get_config_general_settings(
            field_name="pass_through_endpoints", user_api_key_dict=user_api_key_dict
        )
    except Exception:
        return []

    pass_through_endpoint_data: Optional[List] = response.field_value
    if pass_through_endpoint_data is None:
        return []

    returned_endpoints: List[PassThroughGenericEndpoint] = []
    if endpoint_id is None:
        # Return all endpoints
        for endpoint in pass_through_endpoint_data:
            if isinstance(endpoint, dict):
                returned_endpoints.append(PassThroughGenericEndpoint(**endpoint))
            elif isinstance(endpoint, PassThroughGenericEndpoint):
                returned_endpoints.append(endpoint)
    else:
        # Find specific endpoint by ID
        found_endpoint = _find_endpoint_by_id(
            pass_through_endpoint_data, endpoint_id
        )
        if found_endpoint is not None:
            returned_endpoints.append(found_endpoint)
    
    return returned_endpoints


@router.get(
    "/config/pass_through_endpoint",
    dependencies=[Depends(user_api_key_auth)],
    response_model=PassThroughEndpointResponse,
)
async def get_pass_through_endpoints(
    endpoint_id: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    GET configured pass through endpoint.

    If no endpoint_id given, return all configured endpoints.
    """  ## Get existing pass-through endpoint field value
    pass_through_endpoints = await _get_pass_through_endpoints_from_db(
        endpoint_id=endpoint_id, user_api_key_dict=user_api_key_dict
    )
    return PassThroughEndpointResponse(endpoints=pass_through_endpoints)


@router.post(
    "/config/pass_through_endpoint/{endpoint_id}",
    dependencies=[Depends(user_api_key_auth)],
)
async def update_pass_through_endpoints(
    endpoint_id: str,
    data: PassThroughGenericEndpoint,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update a pass-through endpoint by ID.
    """
    from litellm.proxy.proxy_server import (
        get_config_general_settings,
        update_config_general_settings,
    )

    ## Get existing pass-through endpoint field value
    try:
        response: ConfigFieldInfo = await get_config_general_settings(
            field_name="pass_through_endpoints", user_api_key_dict=user_api_key_dict
        )
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"error": "No pass-through endpoints found"},
        )

    pass_through_endpoint_data: Optional[List] = response.field_value
    if pass_through_endpoint_data is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "No pass-through endpoints found"},
        )

    # Find the endpoint to update
    found_endpoint = _find_endpoint_by_id(
        pass_through_endpoint_data, endpoint_id
    )
    
    if found_endpoint is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Endpoint with ID '{endpoint_id}' not found"
            },
        )

    # Find the index for updating the list
    endpoint_index = None
    for idx, endpoint in enumerate(pass_through_endpoint_data):
        _endpoint = PassThroughGenericEndpoint(**endpoint) if isinstance(endpoint, dict) else endpoint
        if _endpoint.id == endpoint_id:
            endpoint_index = idx
            break

    if endpoint_index is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Could not find index for endpoint with ID '{endpoint_id}'"
            },
        )

    # Get the update data as dict, excluding None values for partial updates
    update_data = data.model_dump(exclude_none=True)
    
    # Start with existing endpoint data
    endpoint_dict = found_endpoint.model_dump()
    
    # Update with new data (only non-None values)
    endpoint_dict.update(update_data)
    
    # Preserve existing ID if not provided in update and endpoint has ID
    if "id" not in update_data and found_endpoint.id is not None:
        endpoint_dict["id"] = found_endpoint.id
    
    # Create updated endpoint object
    updated_endpoint = PassThroughGenericEndpoint(**endpoint_dict)
    
    # Update the list
    pass_through_endpoint_data[endpoint_index] = endpoint_dict

    ## Update db
    updated_data = ConfigFieldUpdate(
        field_name="pass_through_endpoints",
        field_value=pass_through_endpoint_data,
        config_type="general_settings",
    )
    await update_config_general_settings(
        data=updated_data, user_api_key_dict=user_api_key_dict
    )

    return PassThroughEndpointResponse(endpoints=[updated_endpoint] if updated_endpoint else [])


@router.post(
    "/config/pass_through_endpoint",
    dependencies=[Depends(user_api_key_auth)],
)
async def create_pass_through_endpoints(
    data: PassThroughGenericEndpoint,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create new pass-through endpoint
    """
    import uuid

    from litellm.proxy.proxy_server import (
        get_config_general_settings,
        update_config_general_settings,
    )

    ## Get existing pass-through endpoint field value

    try:
        response: ConfigFieldInfo = await get_config_general_settings(
            field_name="pass_through_endpoints", user_api_key_dict=user_api_key_dict
        )
    except Exception:
        response = ConfigFieldInfo(
            field_name="pass_through_endpoints", field_value=None
        )

    ## Auto-generate ID if not provided
    data_dict = data.model_dump()
    if data_dict.get("id") is None:
        data_dict["id"] = str(uuid.uuid4())

    if response.field_value is None:
        response.field_value = [data_dict]
    elif isinstance(response.field_value, List):
        response.field_value.append(data_dict)

    ## Update db
    updated_data = ConfigFieldUpdate(
        field_name="pass_through_endpoints",
        field_value=response.field_value,
        config_type="general_settings",
    )
    await update_config_general_settings(
        data=updated_data, user_api_key_dict=user_api_key_dict
    )

    # Return the created endpoint with the generated ID
    created_endpoint = PassThroughGenericEndpoint(**data_dict)
    return PassThroughEndpointResponse(endpoints=[created_endpoint])


@router.delete(
    "/config/pass_through_endpoint",
    dependencies=[Depends(user_api_key_auth)],
    response_model=PassThroughEndpointResponse,
)
async def delete_pass_through_endpoints(
    endpoint_id: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete a pass-through endpoint by ID.

    Returns - the deleted endpoint
    """
    from litellm.proxy.proxy_server import (
        get_config_general_settings,
        update_config_general_settings,
    )

    ## Get existing pass-through endpoint field value

    try:
        response: ConfigFieldInfo = await get_config_general_settings(
            field_name="pass_through_endpoints", user_api_key_dict=user_api_key_dict
        )
    except Exception:
        response = ConfigFieldInfo(
            field_name="pass_through_endpoints", field_value=None
        )

    ## Update field by removing endpoint
    pass_through_endpoint_data: Optional[List] = response.field_value
    if response.field_value is None or pass_through_endpoint_data is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "There are no pass-through endpoints setup."},
        )

    # Find the endpoint to delete
    found_endpoint = _find_endpoint_by_id(
        pass_through_endpoint_data, endpoint_id
    )
    
    if found_endpoint is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Endpoint with ID '{}' was not found in pass-through endpoint list.".format(
                    endpoint_id
                )
            },
        )
    
    # Find the index for deleting from the list
    endpoint_index = None
    for idx, endpoint in enumerate(pass_through_endpoint_data):
        _endpoint = PassThroughGenericEndpoint(**endpoint) if isinstance(endpoint, dict) else endpoint
        if _endpoint.id == endpoint_id:
            endpoint_index = idx
            break

    if endpoint_index is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Could not find index for endpoint with ID '{endpoint_id}'"
            },
        )
    
    # Remove the endpoint
    pass_through_endpoint_data.pop(endpoint_index)
    response_obj = found_endpoint

    ## Update db
    updated_data = ConfigFieldUpdate(
        field_name="pass_through_endpoints",
        field_value=pass_through_endpoint_data,
        config_type="general_settings",
    )
    await update_config_general_settings(
        data=updated_data, user_api_key_dict=user_api_key_dict
    )

    return PassThroughEndpointResponse(endpoints=[response_obj])


def _find_endpoint_by_id(
    endpoints_data: List,
    endpoint_id: str,
) -> Optional[PassThroughGenericEndpoint]:
    """
    Find an endpoint by ID.
    
    Args:
        endpoints_data: List of endpoint data (dicts or PassThroughGenericEndpoint objects)
        endpoint_id: ID to search for
        
    Returns:
        Found endpoint or None if not found
    """
    for endpoint in endpoints_data:
        _endpoint: Optional[PassThroughGenericEndpoint] = None
        if isinstance(endpoint, dict):
            _endpoint = PassThroughGenericEndpoint(**endpoint)
        elif isinstance(endpoint, PassThroughGenericEndpoint):
            _endpoint = endpoint

        # Only compare IDs to IDs
        if _endpoint is not None and _endpoint.id == endpoint_id:
            return _endpoint
    
    return None


async def initialize_pass_through_endpoints_in_db():
    """
    Gets all pass-through endpoints from db and initializes them in the proxy server.
    """
    pass_through_endpoints = await _get_pass_through_endpoints_from_db()
    await initialize_pass_through_endpoints(
        pass_through_endpoints=pass_through_endpoints
    )