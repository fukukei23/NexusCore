
# === NexusCore/tools\exports\export_20250803_114325\combined_184.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\test_bleu.py ===
"""
Tests for BLEU translation evaluation metric
"""

import unittest

import numpy as np

from nltk.data import find
from nltk.translate.bleu_score import (
    SmoothingFunction,
    brevity_penalty,
    closest_ref_length,
    corpus_bleu,
    modified_precision,
    sentence_bleu,
)


class TestBLEU(unittest.TestCase):
    def test_modified_precision(self):
        """
        Examples from the original BLEU paper
        https://www.aclweb.org/anthology/P02-1040.pdf
        """
        # Example 1: the "the*" example.
        # Reference sentences.
        ref1 = "the cat is on the mat".split()
        ref2 = "there is a cat on the mat".split()
        # Hypothesis sentence(s).
        hyp1 = "the the the the the the the".split()

        references = [ref1, ref2]

        # Testing modified unigram precision.
        hyp1_unigram_precision = float(modified_precision(references, hyp1, n=1))
        assert round(hyp1_unigram_precision, 4) == 0.2857
        # With assertAlmostEqual at 4 place precision.
        self.assertAlmostEqual(hyp1_unigram_precision, 0.28571428, places=4)

        # Testing modified bigram precision.
        assert float(modified_precision(references, hyp1, n=2)) == 0.0

        # Example 2: the "of the" example.
        # Reference sentences
        ref1 = str(
            "It is a guide to action that ensures that the military "
            "will forever heed Party commands"
        ).split()
        ref2 = str(
            "It is the guiding principle which guarantees the military "
            "forces always being under the command of the Party"
        ).split()
        ref3 = str(
            "It is the practical guide for the army always to heed "
            "the directions of the party"
        ).split()
        # Hypothesis sentence(s).
        hyp1 = "of the".split()

        references = [ref1, ref2, ref3]
        # Testing modified unigram precision.
        assert float(modified_precision(references, hyp1, n=1)) == 1.0

        # Testing modified bigram precision.
        assert float(modified_precision(references, hyp1, n=2)) == 1.0

        # Example 3: Proper MT outputs.
        hyp1 = str(
            "It is a guide to action which ensures that the military "
            "always obeys the commands of the party"
        ).split()
        hyp2 = str(
            "It is to insure the troops forever hearing the activity "
            "guidebook that party direct"
        ).split()

        references = [ref1, ref2, ref3]

        # Unigram precision.
        hyp1_unigram_precision = float(modified_precision(references, hyp1, n=1))
        hyp2_unigram_precision = float(modified_precision(references, hyp2, n=1))
        # Test unigram precision with assertAlmostEqual at 4 place precision.
        self.assertAlmostEqual(hyp1_unigram_precision, 0.94444444, places=4)
        self.assertAlmostEqual(hyp2_unigram_precision, 0.57142857, places=4)
        # Test unigram precision with rounding.
        assert round(hyp1_unigram_precision, 4) == 0.9444
        assert round(hyp2_unigram_precision, 4) == 0.5714

        # Bigram precision
        hyp1_bigram_precision = float(modified_precision(references, hyp1, n=2))
        hyp2_bigram_precision = float(modified_precision(references, hyp2, n=2))
        # Test bigram precision with assertAlmostEqual at 4 place precision.
        self.assertAlmostEqual(hyp1_bigram_precision, 0.58823529, places=4)
        self.assertAlmostEqual(hyp2_bigram_precision, 0.07692307, places=4)
        # Test bigram precision with rounding.
        assert round(hyp1_bigram_precision, 4) == 0.5882
        assert round(hyp2_bigram_precision, 4) == 0.0769

    def test_brevity_penalty(self):
        # Test case from brevity_penalty_closest function in mteval-v13a.pl.
        # Same test cases as in the doctest in nltk.translate.bleu_score.py
        references = [["a"] * 11, ["a"] * 8]
        hypothesis = ["a"] * 7
        hyp_len = len(hypothesis)
        closest_ref_len = closest_ref_length(references, hyp_len)
        self.assertAlmostEqual(
            brevity_penalty(closest_ref_len, hyp_len), 0.8669, places=4
        )

        references = [["a"] * 11, ["a"] * 8, ["a"] * 6, ["a"] * 7]
        hypothesis = ["a"] * 7
        hyp_len = len(hypothesis)
        closest_ref_len = closest_ref_length(references, hyp_len)
        assert brevity_penalty(closest_ref_len, hyp_len) == 1.0

    def test_zero_matches(self):
        # Test case where there's 0 matches
        references = ["The candidate has no alignment to any of the references".split()]
        hypothesis = "John loves Mary".split()

        # Test BLEU to nth order of n-grams, where n is len(hypothesis).
        for n in range(1, len(hypothesis)):
            weights = (1.0 / n,) * n  # Uniform weights.
            assert sentence_bleu(references, hypothesis, weights) == 0

    def test_full_matches(self):
        # Test case where there's 100% matches
        references = ["John loves Mary".split()]
        hypothesis = "John loves Mary".split()

        # Test BLEU to nth order of n-grams, where n is len(hypothesis).
        for n in range(1, len(hypothesis)):
            weights = (1.0 / n,) * n  # Uniform weights.
            assert sentence_bleu(references, hypothesis, weights) == 1.0

    def test_partial_matches_hypothesis_longer_than_reference(self):
        references = ["John loves Mary".split()]
        hypothesis = "John loves Mary who loves Mike".split()
        # Since no 4-grams matches were found the result should be zero
        # exp(w_1 * 1 * w_2 * 1 * w_3 * 1 * w_4 * -inf) = 0
        self.assertAlmostEqual(sentence_bleu(references, hypothesis), 0.0, places=4)
        # Checks that the warning has been raised because len(reference) < 4.
        try:
            self.assertWarns(UserWarning, sentence_bleu, references, hypothesis)
        except AttributeError:
            pass  # unittest.TestCase.assertWarns is only supported in Python >= 3.2.


# @unittest.skip("Skipping fringe cases for BLEU.")
class TestBLEUFringeCases(unittest.TestCase):
    def test_case_where_n_is_bigger_than_hypothesis_length(self):
        # Test BLEU to nth order of n-grams, where n > len(hypothesis).
        references = ["John loves Mary ?".split()]
        hypothesis = "John loves Mary".split()
        n = len(hypothesis) + 1  #
        weights = (1.0 / n,) * n  # Uniform weights.
        # Since no n-grams matches were found the result should be zero
        # exp(w_1 * 1 * w_2 * 1 * w_3 * 1 * w_4 * -inf) = 0
        self.assertAlmostEqual(
            sentence_bleu(references, hypothesis, weights), 0.0, places=4
        )
        # Checks that the warning has been raised because len(hypothesis) < 4.
        try:
            self.assertWarns(UserWarning, sentence_bleu, references, hypothesis)
        except AttributeError:
            pass  # unittest.TestCase.assertWarns is only supported in Python >= 3.2.

        # Test case where n > len(hypothesis) but so is n > len(reference), and
        # it's a special case where reference == hypothesis.
        references = ["John loves Mary".split()]
        hypothesis = "John loves Mary".split()
        # Since no 4-grams matches were found the result should be zero
        # exp(w_1 * 1 * w_2 * 1 * w_3 * 1 * w_4 * -inf) = 0
        self.assertAlmostEqual(
            sentence_bleu(references, hypothesis, weights), 0.0, places=4
        )

    def test_empty_hypothesis(self):
        # Test case where there's hypothesis is empty.
        references = ["The candidate has no alignment to any of the references".split()]
        hypothesis = []
        assert sentence_bleu(references, hypothesis) == 0

    def test_length_one_hypothesis(self):
        # Test case where there's hypothesis is of length 1 in Smoothing method 4.
        references = ["The candidate has no alignment to any of the references".split()]
        hypothesis = ["Foo"]
        method4 = SmoothingFunction().method4
        try:
            sentence_bleu(references, hypothesis, smoothing_function=method4)
        except ValueError:
            pass  # unittest.TestCase.assertWarns is only supported in Python >= 3.2.

    def test_empty_references(self):
        # Test case where there's reference is empty.
        references = [[]]
        hypothesis = "John loves Mary".split()
        assert sentence_bleu(references, hypothesis) == 0

    def test_empty_references_and_hypothesis(self):
        # Test case where both references and hypothesis is empty.
        references = [[]]
        hypothesis = []
        assert sentence_bleu(references, hypothesis) == 0

    def test_reference_or_hypothesis_shorter_than_fourgrams(self):
        # Test case where the length of reference or hypothesis
        # is shorter than 4.
        references = ["let it go".split()]
        hypothesis = "let go it".split()
        # Checks that the value the hypothesis and reference returns is 0.0
        # exp(w_1 * 1 * w_2 * 1 * w_3 * 1 * w_4 * -inf) = 0
        self.assertAlmostEqual(sentence_bleu(references, hypothesis), 0.0, places=4)
        # Checks that the warning has been raised.
        try:
            self.assertWarns(UserWarning, sentence_bleu, references, hypothesis)
        except AttributeError:
            pass  # unittest.TestCase.assertWarns is only supported in Python >= 3.2.

    def test_numpy_weights(self):
        # Test case where there's 0 matches
        references = ["The candidate has no alignment to any of the references".split()]
        hypothesis = "John loves Mary".split()

        weights = np.array([0.25] * 4)
        assert sentence_bleu(references, hypothesis, weights) == 0


class TestBLEUvsMteval13a(unittest.TestCase):
    def test_corpus_bleu(self):
        ref_file = find("models/wmt15_eval/ref.ru")
        hyp_file = find("models/wmt15_eval/google.ru")
        mteval_output_file = find("models/wmt15_eval/mteval-13a.output")

        # Reads the BLEU scores from the `mteval-13a.output` file.
        # The order of the list corresponds to the order of the ngrams.
        with open(mteval_output_file) as mteval_fin:
            # The numbers are located in the last 2nd line of the file.
            # The first and 2nd item in the list are the score and system names.
            mteval_bleu_scores = map(float, mteval_fin.readlines()[-2].split()[1:-1])

        with open(ref_file, encoding="utf8") as ref_fin:
            with open(hyp_file, encoding="utf8") as hyp_fin:
                # Whitespace tokenize the file.
                # Note: split() automatically strip().
                hypothesis = list(map(lambda x: x.split(), hyp_fin))
                # Note that the corpus_bleu input is list of list of references.
                references = list(map(lambda x: [x.split()], ref_fin))
                # Without smoothing.
                for i, mteval_bleu in zip(range(1, 10), mteval_bleu_scores):
                    nltk_bleu = corpus_bleu(
                        references, hypothesis, weights=(1.0 / i,) * i
                    )
                    # Check that the BLEU scores difference is less than 0.005 .
                    # Note: This is an approximate comparison; as much as
                    #       +/- 0.01 BLEU might be "statistically significant",
                    #       the actual translation quality might not be.
                    assert abs(mteval_bleu - nltk_bleu) < 0.005

                # With the same smoothing method used in mteval-v13a.pl
                chencherry = SmoothingFunction()
                for i, mteval_bleu in zip(range(1, 10), mteval_bleu_scores):
                    nltk_bleu = corpus_bleu(
                        references,
                        hypothesis,
                        weights=(1.0 / i,) * i,
                        smoothing_function=chencherry.method3,
                    )
                    assert abs(mteval_bleu - nltk_bleu) < 0.005


class TestBLEUWithBadSentence(unittest.TestCase):
    def test_corpus_bleu_with_bad_sentence(self):
        hyp = "Teo S yb , oe uNb , R , T t , , t Tue Ar saln S , , 5istsi l , 5oe R ulO sae oR R"
        ref = str(
            "Their tasks include changing a pump on the faulty stokehold ."
            "Likewise , two species that are very similar in morphology "
            "were distinguished using genetics ."
        )
        references = [[ref.split()]]
        hypotheses = [hyp.split()]
        try:  # Check that the warning is raised since no. of 2-grams < 0.
            with self.assertWarns(UserWarning):
                # Verify that the BLEU output is undesired since no. of 2-grams < 0.
                self.assertAlmostEqual(
                    corpus_bleu(references, hypotheses), 0.0, places=4
                )
        except (
            AttributeError
        ):  # unittest.TestCase.assertWarns is only supported in Python >= 3.2.
            self.assertAlmostEqual(corpus_bleu(references, hypotheses), 0.0, places=4)


class TestBLEUWithMultipleWeights(unittest.TestCase):
    def test_corpus_bleu_with_multiple_weights(self):
        hyp1 = [
            "It",
            "is",
            "a",
            "guide",
            "to",
            "action",
            "which",
            "ensures",
            "that",
            "the",
            "military",
            "always",
            "obeys",
            "the",
            "commands",
            "of",
            "the",
            "party",
        ]
        ref1a = [
            "It",
            "is",
            "a",
            "guide",
            "to",
            "action",
            "that",
            "ensures",
            "that",
            "the",
            "military",
            "will",
            "forever",
            "heed",
            "Party",
            "commands",
        ]
        ref1b = [
            "It",
            "is",
            "the",
            "guiding",
            "principle",
            "which",
            "guarantees",
            "the",
            "military",
            "forces",
            "always",
            "being",
            "under",
            "the",
            "command",
            "of",
            "the",
            "Party",
        ]
        ref1c = [
            "It",
            "is",
            "the",
            "practical",
            "guide",
            "for",
            "the",
            "army",
            "always",
            "to",
            "heed",
            "the",
            "directions",
            "of",
            "the",
            "party",
        ]
        hyp2 = [
            "he",
            "read",
            "the",
            "book",
            "because",
            "he",
            "was",
            "interested",
            "in",
            "world",
            "history",
        ]
        ref2a = [
            "he",
            "was",
            "interested",
            "in",
            "world",
            "history",
            "because",
            "he",
            "read",
            "the",
            "book",
        ]
        weight_1 = (1, 0, 0, 0)
        weight_2 = (0.25, 0.25, 0.25, 0.25)
        weight_3 = (0, 0, 0, 0, 1)

        bleu_scores = corpus_bleu(
            list_of_references=[[ref1a, ref1b, ref1c], [ref2a]],
            hypotheses=[hyp1, hyp2],
            weights=[weight_1, weight_2, weight_3],
        )
        assert bleu_scores[0] == corpus_bleu(
            [[ref1a, ref1b, ref1c], [ref2a]], [hyp1, hyp2], weight_1
        )
        assert bleu_scores[1] == corpus_bleu(
            [[ref1a, ref1b, ref1c], [ref2a]], [hyp1, hyp2], weight_2
        )
        assert bleu_scores[2] == corpus_bleu(
            [[ref1a, ref1b, ref1c], [ref2a]], [hyp1, hyp2], weight_3
        )

# === NexusCore/openenv\Lib\site-packages\openai\lib\_parsing\__init__.py ===
from ._completions import (
    ResponseFormatT as ResponseFormatT,
    has_parseable_input,
    has_parseable_input as has_parseable_input,
    maybe_parse_content as maybe_parse_content,
    validate_input_tools as validate_input_tools,
    parse_chat_completion as parse_chat_completion,
    get_input_tool_by_name as get_input_tool_by_name,
    solve_response_format_t as solve_response_format_t,
    parse_function_tool_arguments as parse_function_tool_arguments,
    type_to_response_format_param as type_to_response_format_param,
)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\openGLDemo.py ===
# Ported from the win32 and MFC OpenGL Samples.

import sys

try:
    from OpenGL.GL import (
        GL_COLOR_BUFFER_BIT,
        GL_DEPTH_BUFFER_BIT,
        GL_DEPTH_TEST,
        GL_MODELVIEW,
        GL_PROJECTION,
        GL_QUAD_STRIP,
        GL_QUADS,
        GL_TRIANGLE_FAN,
        glBegin,
        glClear,
        glClearColor,
        glClearDepth,
        glColor3f,
        glEnable,
        glEnd,
        glFinish,
        glLoadIdentity,
        glMatrixMode,
        glPopMatrix,
        glPushMatrix,
        glRotatef,
        glTranslatef,
        glVertex3f,
        glViewport,
    )
    from OpenGL.GLU import (
        GLU_FILL,
        GLU_SMOOTH,
        gluCylinder,
        gluNewQuadric,
        gluPerspective,
        gluQuadricDrawStyle,
        gluQuadricNormals,
    )
    from OpenGL.WGL import (
        PIXELFORMATDESCRIPTOR,
        ChoosePixelFormat,
        DescribePixelFormat,
        GetPixelFormat,
        SetPixelFormat,
        SwapBuffers,
        wglCreateContext,
        wglDeleteContext,
        wglGetCurrentContext,
        wglGetCurrentDC,
        wglMakeCurrent,
    )
except ImportError:
    print("The OpenGL extensions do not appear to be installed.")
    print("This Pythonwin demo can not run")
    sys.exit(1)

import timer
import win32api
import win32con
import win32ui
from pywin.mfc import docview

PFD_TYPE_RGBA = 0
PFD_TYPE_COLORINDEX = 1
PFD_MAIN_PLANE = 0
PFD_OVERLAY_PLANE = 1
PFD_UNDERLAY_PLANE = -1
PFD_DOUBLEBUFFER = 0x00000001
PFD_STEREO = 0x00000002
PFD_DRAW_TO_WINDOW = 0x00000004
PFD_DRAW_TO_BITMAP = 0x00000008
PFD_SUPPORT_GDI = 0x00000010
PFD_SUPPORT_OPENGL = 0x00000020
PFD_GENERIC_FORMAT = 0x00000040
PFD_NEED_PALETTE = 0x00000080
PFD_NEED_SYSTEM_PALETTE = 0x00000100
PFD_SWAP_EXCHANGE = 0x00000200
PFD_SWAP_COPY = 0x00000400
PFD_SWAP_LAYER_BUFFERS = 0x00000800
PFD_GENERIC_ACCELERATED = 0x00001000
PFD_DEPTH_DONTCARE = 0x20000000
PFD_DOUBLEBUFFER_DONTCARE = 0x40000000
PFD_STEREO_DONTCARE = 0x80000000


# threeto8 = [0, 0o111>>1, 0o222>>1, 0o333>>1, 0o444>>1, 0o555>>1, 0o666>>1, 0o377]
threeto8 = [0, 73 >> 1, 146 >> 1, 219 >> 1, 292 >> 1, 365 >> 1, 438 >> 1, 255]
twoto8 = [0, 0x55, 0xAA, 0xFF]
oneto8 = [0, 255]


def ComponentFromIndex(i, nbits, shift):
    # val = (unsigned char) (i >> shift);
    val = (i >> shift) & 0xF
    if nbits == 1:
        val &= 0x1
        return oneto8[val]
    elif nbits == 2:
        val &= 0x3
        return twoto8[val]
    elif nbits == 3:
        val &= 0x7
        return threeto8[val]
    else:
        return 0


OpenGLViewParent = docview.ScrollView


class OpenGLView(OpenGLViewParent):
    def PreCreateWindow(self, cc):
        self.HookMessage(self.OnSize, win32con.WM_SIZE)
        # An OpenGL window must be created with the following flags and must not
        # include CS_PARENTDC for the class style. Refer to SetPixelFormat
        # documentation in the "Comments" section for further information.
        style = cc[5]
        style |= win32con.WS_CLIPSIBLINGS | win32con.WS_CLIPCHILDREN
        cc = cc[0], cc[1], cc[2], cc[3], cc[4], style, cc[6], cc[7], cc[8]
        cc = self._obj_.PreCreateWindow(cc)
        return cc

    def OnSize(self, params):
        lParam = params[3]
        cx = win32api.LOWORD(lParam)
        cy = win32api.HIWORD(lParam)
        glViewport(0, 0, cx, cy)

        if self.oldrect[2] > cx or self.oldrect[3] > cy:
            self.RedrawWindow()

        self.OnSizeChange(cx, cy)

        self.oldrect = self.oldrect[0], self.oldrect[1], cx, cy

    def OnInitialUpdate(self):
        self.SetScaleToFitSize(
            (100, 100)
        )  # or SetScrollSizes() - A Pythonwin requirement
        return self._obj_.OnInitialUpdate()

    # 		return rc

    def OnCreate(self, cs):
        self.oldrect = self.GetClientRect()
        self._InitContexts()
        self.Init()

    def OnDestroy(self, msg):
        self.Term()
        self._DestroyContexts()
        return OpenGLViewParent.OnDestroy(self, msg)

    def OnDraw(self, dc):
        self.DrawScene()

    def OnEraseBkgnd(self, dc):
        return 1

    # The OpenGL helpers
    def _SetupPixelFormat(self):
        dc = self.dc.GetSafeHdc()
        pfd = PIXELFORMATDESCRIPTOR()
        pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER
        pfd.iPixelType = PFD_TYPE_RGBA
        pfd.cColorBits = 24
        pfd.cDepthBits = 32
        pfd.iLayerType = PFD_MAIN_PLANE
        pixelformat = ChoosePixelFormat(dc, pfd)
        SetPixelFormat(dc, pixelformat, pfd)
        self._CreateRGBPalette(pfd)

    def _CreateRGBPalette(self, pfd):
        hdc = self.dc.GetSafeHdc()
        iPixelFormat = GetPixelFormat(hdc)
        DescribePixelFormat(hdc, iPixelFormat, pfd.nSize, pfd)
        if pfd.dwFlags & PFD_NEED_PALETTE:
            iPixelFormat = 1 << pfd.cColorBits
            pal = []
            for i in range(iPixelFormat):
                this = (
                    ComponentFromIndex(i, pfd.cRedBits, pfd.cRedShift),
                    ComponentFromIndex(i, pfd.cGreenBits, pfd.cGreenShift),
                    ComponentFromIndex(i, pfd.cBlueBits, pfd.cBlueShift),
                    0,
                )
                pal.append(this)
            hpal = win32ui.CreatePalette(pal)
            self.dc.SelectPalette(hpal, 0)
            self.dc.RealizePalette()

    def _InitContexts(self):
        self.dc = self.GetDC()
        self._SetupPixelFormat()
        hrc = wglCreateContext(self.dc.GetSafeHdc())
        wglMakeCurrent(self.dc.GetSafeHdc(), hrc)

    def _DestroyContexts(self):
        hrc = wglGetCurrentContext()
        wglMakeCurrent(0, 0)
        if hrc:
            wglDeleteContext(hrc)

    # The methods to support OpenGL
    def DrawScene(self):
        raise NotImplementedError("You must override this method")

    def Init(self):
        raise NotImplementedError("You must override this method")

    def OnSizeChange(self, cx, cy):
        pass

    def Term(self):
        pass


class TestView(OpenGLView):
    def OnSizeChange(self, right, bottom):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        if bottom:
            aspect = right / bottom
        else:
            aspect = 0  # When window created!
        glLoadIdentity()
        gluPerspective(45.0, aspect, 3.0, 7.0)
        glMatrixMode(GL_MODELVIEW)

        near_plane = 3.0
        far_plane = 7.0
        maxObjectSize = 3.0
        self.radius = near_plane + maxObjectSize / 2.0

    def Init(self):
        pass

    def DrawScene(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        glTranslatef(0.0, 0.0, -self.radius)

        self._DrawCone()

        self._DrawPyramid()

        glPopMatrix()
        glFinish()

        SwapBuffers(wglGetCurrentDC())

    def _DrawCone(self):
        glColor3f(0.0, 1.0, 0.0)

        glPushMatrix()
        glTranslatef(-1.0, 0.0, 0.0)
        quadObj = gluNewQuadric()
        gluQuadricDrawStyle(quadObj, GLU_FILL)
        gluQuadricNormals(quadObj, GLU_SMOOTH)
        gluCylinder(quadObj, 1.0, 0.0, 1.0, 20, 10)
        # 		gluDeleteQuadric(quadObj);
        glPopMatrix()

    def _DrawPyramid(self):
        glPushMatrix()
        glTranslatef(1.0, 0.0, 0.0)
        glBegin(GL_TRIANGLE_FAN)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0.0, 1.0, 0.0)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(-1.0, 0.0, 0.0)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, 1.0)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(1.0, 0.0, 0.0)
        glEnd()
        glPopMatrix()


class CubeView(OpenGLView):
    def OnSizeChange(self, right, bottom):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        if bottom:
            aspect = right / bottom
        else:
            aspect = 0  # When window created!
        glLoadIdentity()
        gluPerspective(45.0, aspect, 3.0, 7.0)
        glMatrixMode(GL_MODELVIEW)

        near_plane = 3.0
        far_plane = 7.0
        maxObjectSize = 3.0
        self.radius = near_plane + maxObjectSize / 2.0

    def Init(self):
        self.busy = 0
        self.wAngleY = 10.0
        self.wAngleX = 1.0
        self.wAngleZ = 5.0
        self.timerid = timer.set_timer(150, self.OnTimer)

    def OnTimer(self, id, timeVal):
        self.DrawScene()

    def Term(self):
        timer.kill_timer(self.timerid)

    def DrawScene(self):
        if self.busy:
            return
        self.busy = 1

        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()

        glTranslatef(0.0, 0.0, -self.radius)
        glRotatef(self.wAngleX, 1.0, 0.0, 0.0)
        glRotatef(self.wAngleY, 0.0, 1.0, 0.0)
        glRotatef(self.wAngleZ, 0.0, 0.0, 1.0)

        self.wAngleX += 1.0
        self.wAngleY += 10.0
        self.wAngleZ += 5.0

        glBegin(GL_QUAD_STRIP)
        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(-0.5, 0.5, 0.5)

        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, 0.5)

        glColor3f(1.0, 1.0, 1.0)
        glVertex3f(0.5, 0.5, 0.5)

        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(0.5, -0.5, 0.5)

        glColor3f(0.0, 1.0, 1.0)
        glVertex3f(0.5, 0.5, -0.5)

        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.5, -0.5, -0.5)

        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-0.5, 0.5, -0.5)

        glColor3f(0.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, -0.5)

        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(-0.5, 0.5, 0.5)

        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, 0.5)

        glEnd()

        glBegin(GL_QUADS)
        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(-0.5, 0.5, 0.5)

        glColor3f(1.0, 1.0, 1.0)
        glVertex3f(0.5, 0.5, 0.5)

        glColor3f(0.0, 1.0, 1.0)
        glVertex3f(0.5, 0.5, -0.5)

        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-0.5, 0.5, -0.5)
        glEnd()

        glBegin(GL_QUADS)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, 0.5)

        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(0.5, -0.5, 0.5)

        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.5, -0.5, -0.5)

        glColor3f(0.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glEnd()

        glPopMatrix()

        glFinish()
        SwapBuffers(wglGetCurrentDC())

        self.busy = 0


def test():
    template = docview.DocTemplate(None, None, None, CubeView)
    # 	template = docview.DocTemplate(None, None, None, TestView )
    template.OpenDocumentFile(None)


if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\bidi\storage.py ===
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

from typing import Dict, List, Optional, Union

from selenium.webdriver.common.bidi.common import command_builder


class SameSite:
    """Represents the possible same site values for cookies."""

    STRICT = "strict"
    LAX = "lax"
    NONE = "none"


class BytesValue:
    """Represents a bytes value."""

    TYPE_BASE64 = "base64"
    TYPE_STRING = "string"

    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

    def to_dict(self) -> Dict:
        """Converts the BytesValue to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the BytesValue.
        """
        return {"type": self.type, "value": self.value}


class Cookie:
    """Represents a cookie."""

    def __init__(
        self,
        name: str,
        value: BytesValue,
        domain: str,
        path: Optional[str] = None,
        size: Optional[int] = None,
        http_only: Optional[bool] = None,
        secure: Optional[bool] = None,
        same_site: Optional[str] = None,
        expiry: Optional[int] = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.size = size
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    @classmethod
    def from_dict(cls, data: Dict) -> "Cookie":
        """Creates a Cookie instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the cookie information.

        Returns:
        -------
            Cookie: A new instance of Cookie.
        """
        value = BytesValue(data.get("value", {}).get("type"), data.get("value", {}).get("value"))

        return cls(
            name=data.get("name"),
            value=value,
            domain=data.get("domain"),
            path=data.get("path"),
            size=data.get("size"),
            http_only=data.get("httpOnly"),
            secure=data.get("secure"),
            same_site=data.get("sameSite"),
            expiry=data.get("expiry"),
        )


class CookieFilter:
    """Represents a filter for cookies."""

    def __init__(
        self,
        name: Optional[str] = None,
        value: Optional[BytesValue] = None,
        domain: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
        http_only: Optional[bool] = None,
        secure: Optional[bool] = None,
        same_site: Optional[str] = None,
        expiry: Optional[int] = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.size = size
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    def to_dict(self) -> Dict:
        """Converts the CookieFilter to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the CookieFilter.
        """
        result = {}
        if self.name is not None:
            result["name"] = self.name
        if self.value is not None:
            result["value"] = self.value.to_dict()
        if self.domain is not None:
            result["domain"] = self.domain
        if self.path is not None:
            result["path"] = self.path
        if self.size is not None:
            result["size"] = self.size
        if self.http_only is not None:
            result["httpOnly"] = self.http_only
        if self.secure is not None:
            result["secure"] = self.secure
        if self.same_site is not None:
            result["sameSite"] = self.same_site
        if self.expiry is not None:
            result["expiry"] = self.expiry
        return result


class PartitionKey:
    """Represents a storage partition key."""

    def __init__(self, user_context: Optional[str] = None, source_origin: Optional[str] = None):
        self.user_context = user_context
        self.source_origin = source_origin

    @classmethod
    def from_dict(cls, data: Dict) -> "PartitionKey":
        """Creates a PartitionKey instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the partition key information.

        Returns:
        -------
            PartitionKey: A new instance of PartitionKey.
        """
        return cls(
            user_context=data.get("userContext"),
            source_origin=data.get("sourceOrigin"),
        )


class BrowsingContextPartitionDescriptor:
    """Represents a browsing context partition descriptor."""

    def __init__(self, context: str):
        self.type = "context"
        self.context = context

    def to_dict(self) -> Dict:
        """Converts the BrowsingContextPartitionDescriptor to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the BrowsingContextPartitionDescriptor.
        """
        return {"type": self.type, "context": self.context}


class StorageKeyPartitionDescriptor:
    """Represents a storage key partition descriptor."""

    def __init__(self, user_context: Optional[str] = None, source_origin: Optional[str] = None):
        self.type = "storageKey"
        self.user_context = user_context
        self.source_origin = source_origin

    def to_dict(self) -> Dict:
        """Converts the StorageKeyPartitionDescriptor to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the StorageKeyPartitionDescriptor.
        """
        result = {"type": self.type}
        if self.user_context is not None:
            result["userContext"] = self.user_context
        if self.source_origin is not None:
            result["sourceOrigin"] = self.source_origin
        return result


class PartialCookie:
    """Represents a partial cookie for setting."""

    def __init__(
        self,
        name: str,
        value: BytesValue,
        domain: str,
        path: Optional[str] = None,
        http_only: Optional[bool] = None,
        secure: Optional[bool] = None,
        same_site: Optional[str] = None,
        expiry: Optional[int] = None,
    ):
        self.name = name
        self.value = value
        self.domain = domain
        self.path = path
        self.http_only = http_only
        self.secure = secure
        self.same_site = same_site
        self.expiry = expiry

    def to_dict(self) -> Dict:
        """Converts the PartialCookie to a dictionary.

        Returns:
        -------
            Dict: A dictionary representation of the PartialCookie.
        """
        result = {
            "name": self.name,
            "value": self.value.to_dict(),
            "domain": self.domain,
        }
        if self.path is not None:
            result["path"] = self.path
        if self.http_only is not None:
            result["httpOnly"] = self.http_only
        if self.secure is not None:
            result["secure"] = self.secure
        if self.same_site is not None:
            result["sameSite"] = self.same_site
        if self.expiry is not None:
            result["expiry"] = self.expiry
        return result


class GetCookiesResult:
    """Represents the result of a getCookies command."""

    def __init__(self, cookies: List[Cookie], partition_key: PartitionKey):
        self.cookies = cookies
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: Dict) -> "GetCookiesResult":
        """Creates a GetCookiesResult instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the get cookies result information.

        Returns:
        -------
            GetCookiesResult: A new instance of GetCookiesResult.
        """
        cookies = [Cookie.from_dict(cookie) for cookie in data.get("cookies", [])]
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(cookies=cookies, partition_key=partition_key)


class SetCookieResult:
    """Represents the result of a setCookie command."""

    def __init__(self, partition_key: PartitionKey):
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: Dict) -> "SetCookieResult":
        """Creates a SetCookieResult instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the set cookie result information.

        Returns:
        -------
            SetCookieResult: A new instance of SetCookieResult.
        """
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(partition_key=partition_key)


class DeleteCookiesResult:
    """Represents the result of a deleteCookies command."""

    def __init__(self, partition_key: PartitionKey):
        self.partition_key = partition_key

    @classmethod
    def from_dict(cls, data: Dict) -> "DeleteCookiesResult":
        """Creates a DeleteCookiesResult instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the delete cookies result information.

        Returns:
        -------
            DeleteCookiesResult: A new instance of DeleteCookiesResult.
        """
        partition_key = PartitionKey.from_dict(data.get("partitionKey", {}))
        return cls(partition_key=partition_key)


class Storage:
    """BiDi implementation of the storage module."""

    def __init__(self, conn):
        self.conn = conn

    def get_cookies(
        self,
        filter: Optional[CookieFilter] = None,
        partition: Optional[Union[BrowsingContextPartitionDescriptor, StorageKeyPartitionDescriptor]] = None,
    ) -> GetCookiesResult:
        """Retrieves cookies that match the given parameters.

        Parameters:
        -----------
            filter: Optional filter to match cookies.
            partition: Optional partition descriptor.

        Returns:
        -------
            GetCookiesResult: The result of the get cookies command.
        """
        params = {}
        if filter is not None:
            params["filter"] = filter.to_dict()
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.getCookies", params))
        return GetCookiesResult.from_dict(result)

    def set_cookie(
        self,
        cookie: PartialCookie,
        partition: Optional[Union[BrowsingContextPartitionDescriptor, StorageKeyPartitionDescriptor]] = None,
    ) -> SetCookieResult:
        """Sets a cookie in the browser.

        Parameters:
        -----------
            cookie: The cookie to set.
            partition: Optional partition descriptor.

        Returns:
        -------
            SetCookieResult: The result of the set cookie command.
        """
        params = {"cookie": cookie.to_dict()}
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.setCookie", params))
        return SetCookieResult.from_dict(result)

    def delete_cookies(
        self,
        filter: Optional[CookieFilter] = None,
        partition: Optional[Union[BrowsingContextPartitionDescriptor, StorageKeyPartitionDescriptor]] = None,
    ) -> DeleteCookiesResult:
        """Deletes cookies that match the given parameters.

        Parameters:
        -----------
            filter: Optional filter to match cookies to delete.
            partition: Optional partition descriptor.

        Returns:
        -------
            DeleteCookiesResult: The result of the delete cookies command.
        """
        params = {}
        if filter is not None:
            params["filter"] = filter.to_dict()
        if partition is not None:
            params["partition"] = partition.to_dict()

        result = self.conn.execute(command_builder("storage.deleteCookies", params))
        return DeleteCookiesResult.from_dict(result)

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\utils.py ===
from __future__ import annotations

import importlib
import logging
import unicodedata
from codecs import IncrementalDecoder
from encodings.aliases import aliases
from functools import lru_cache
from re import findall
from typing import Generator

from _multibytecodec import (  # type: ignore[import-not-found,import]
    MultibyteIncrementalDecoder,
)

from .constant import (
    ENCODING_MARKS,
    IANA_SUPPORTED_SIMILAR,
    RE_POSSIBLE_ENCODING_INDICATION,
    UNICODE_RANGES_COMBINED,
    UNICODE_SECONDARY_RANGE_KEYWORD,
    UTF8_MAXIMAL_ALLOCATION,
    COMMON_CJK_CHARACTERS,
)


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_accentuated(character: str) -> bool:
    try:
        description: str = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False
    return (
        "WITH GRAVE" in description
        or "WITH ACUTE" in description
        or "WITH CEDILLA" in description
        or "WITH DIAERESIS" in description
        or "WITH CIRCUMFLEX" in description
        or "WITH TILDE" in description
        or "WITH MACRON" in description
        or "WITH RING ABOVE" in description
    )


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def remove_accent(character: str) -> str:
    decomposed: str = unicodedata.decomposition(character)
    if not decomposed:
        return character

    codes: list[str] = decomposed.split(" ")

    return chr(int(codes[0], 16))


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def unicode_range(character: str) -> str | None:
    """
    Retrieve the Unicode range official name from a single character.
    """
    character_ord: int = ord(character)

    for range_name, ord_range in UNICODE_RANGES_COMBINED.items():
        if character_ord in ord_range:
            return range_name

    return None


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_latin(character: str) -> bool:
    try:
        description: str = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False
    return "LATIN" in description


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_punctuation(character: str) -> bool:
    character_category: str = unicodedata.category(character)

    if "P" in character_category:
        return True

    character_range: str | None = unicode_range(character)

    if character_range is None:
        return False

    return "Punctuation" in character_range


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_symbol(character: str) -> bool:
    character_category: str = unicodedata.category(character)

    if "S" in character_category or "N" in character_category:
        return True

    character_range: str | None = unicode_range(character)

    if character_range is None:
        return False

    return "Forms" in character_range and character_category != "Lo"


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_emoticon(character: str) -> bool:
    character_range: str | None = unicode_range(character)

    if character_range is None:
        return False

    return "Emoticons" in character_range or "Pictographs" in character_range


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_separator(character: str) -> bool:
    if character.isspace() or character in {"｜", "+", "<", ">"}:
        return True

    character_category: str = unicodedata.category(character)

    return "Z" in character_category or character_category in {"Po", "Pd", "Pc"}


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_case_variable(character: str) -> bool:
    return character.islower() != character.isupper()


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_cjk(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "CJK" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_hiragana(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "HIRAGANA" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_katakana(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "KATAKANA" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_hangul(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "HANGUL" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_thai(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "THAI" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_arabic(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "ARABIC" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_arabic_isolated_form(character: str) -> bool:
    try:
        character_name = unicodedata.name(character)
    except ValueError:  # Defensive: unicode database outdated?
        return False

    return "ARABIC" in character_name and "ISOLATED FORM" in character_name


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_cjk_uncommon(character: str) -> bool:
    return character not in COMMON_CJK_CHARACTERS


@lru_cache(maxsize=len(UNICODE_RANGES_COMBINED))
def is_unicode_range_secondary(range_name: str) -> bool:
    return any(keyword in range_name for keyword in UNICODE_SECONDARY_RANGE_KEYWORD)


@lru_cache(maxsize=UTF8_MAXIMAL_ALLOCATION)
def is_unprintable(character: str) -> bool:
    return (
        character.isspace() is False  # includes \n \t \r \v
        and character.isprintable() is False
        and character != "\x1a"  # Why? Its the ASCII substitute character.
        and character != "\ufeff"  # bug discovered in Python,
        # Zero Width No-Break Space located in 	Arabic Presentation Forms-B, Unicode 1.1 not acknowledged as space.
    )


def any_specified_encoding(sequence: bytes, search_zone: int = 8192) -> str | None:
    """
    Extract using ASCII-only decoder any specified encoding in the first n-bytes.
    """
    if not isinstance(sequence, bytes):
        raise TypeError

    seq_len: int = len(sequence)

    results: list[str] = findall(
        RE_POSSIBLE_ENCODING_INDICATION,
        sequence[: min(seq_len, search_zone)].decode("ascii", errors="ignore"),
    )

    if len(results) == 0:
        return None

    for specified_encoding in results:
        specified_encoding = specified_encoding.lower().replace("-", "_")

        encoding_alias: str
        encoding_iana: str

        for encoding_alias, encoding_iana in aliases.items():
            if encoding_alias == specified_encoding:
                return encoding_iana
            if encoding_iana == specified_encoding:
                return encoding_iana

    return None


@lru_cache(maxsize=128)
def is_multi_byte_encoding(name: str) -> bool:
    """
    Verify is a specific encoding is a multi byte one based on it IANA name
    """
    return name in {
        "utf_8",
        "utf_8_sig",
        "utf_16",
        "utf_16_be",
        "utf_16_le",
        "utf_32",
        "utf_32_le",
        "utf_32_be",
        "utf_7",
    } or issubclass(
        importlib.import_module(f"encodings.{name}").IncrementalDecoder,
        MultibyteIncrementalDecoder,
    )


def identify_sig_or_bom(sequence: bytes) -> tuple[str | None, bytes]:
    """
    Identify and extract SIG/BOM in given sequence.
    """

    for iana_encoding in ENCODING_MARKS:
        marks: bytes | list[bytes] = ENCODING_MARKS[iana_encoding]

        if isinstance(marks, bytes):
            marks = [marks]

        for mark in marks:
            if sequence.startswith(mark):
                return iana_encoding, mark

    return None, b""


def should_strip_sig_or_bom(iana_encoding: str) -> bool:
    return iana_encoding not in {"utf_16", "utf_32"}


def iana_name(cp_name: str, strict: bool = True) -> str:
    """Returns the Python normalized encoding name (Not the IANA official name)."""
    cp_name = cp_name.lower().replace("-", "_")

    encoding_alias: str
    encoding_iana: str

    for encoding_alias, encoding_iana in aliases.items():
        if cp_name in [encoding_alias, encoding_iana]:
            return encoding_iana

    if strict:
        raise ValueError(f"Unable to retrieve IANA for '{cp_name}'")

    return cp_name


def cp_similarity(iana_name_a: str, iana_name_b: str) -> float:
    if is_multi_byte_encoding(iana_name_a) or is_multi_byte_encoding(iana_name_b):
        return 0.0

    decoder_a = importlib.import_module(f"encodings.{iana_name_a}").IncrementalDecoder
    decoder_b = importlib.import_module(f"encodings.{iana_name_b}").IncrementalDecoder

    id_a: IncrementalDecoder = decoder_a(errors="ignore")
    id_b: IncrementalDecoder = decoder_b(errors="ignore")

    character_match_count: int = 0

    for i in range(255):
        to_be_decoded: bytes = bytes([i])
        if id_a.decode(to_be_decoded) == id_b.decode(to_be_decoded):
            character_match_count += 1

    return character_match_count / 254


def is_cp_similar(iana_name_a: str, iana_name_b: str) -> bool:
    """
    Determine if two code page are at least 80% similar. IANA_SUPPORTED_SIMILAR dict was generated using
    the function cp_similarity.
    """
    return (
        iana_name_a in IANA_SUPPORTED_SIMILAR
        and iana_name_b in IANA_SUPPORTED_SIMILAR[iana_name_a]
    )


def set_logging_handler(
    name: str = "charset_normalizer",
    level: int = logging.INFO,
    format_string: str = "%(asctime)s | %(levelname)s | %(message)s",
) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(handler)


def cut_sequence_chunks(
    sequences: bytes,
    encoding_iana: str,
    offsets: range,
    chunk_size: int,
    bom_or_sig_available: bool,
    strip_sig_or_bom: bool,
    sig_payload: bytes,
    is_multi_byte_decoder: bool,
    decoded_payload: str | None = None,
) -> Generator[str, None, None]:
    if decoded_payload and is_multi_byte_decoder is False:
        for i in offsets:
            chunk = decoded_payload[i : i + chunk_size]
            if not chunk:
                break
            yield chunk
    else:
        for i in offsets:
            chunk_end = i + chunk_size
            if chunk_end > len(sequences) + 8:
                continue

            cut_sequence = sequences[i : i + chunk_size]

            if bom_or_sig_available and strip_sig_or_bom is False:
                cut_sequence = sig_payload + cut_sequence

            chunk = cut_sequence.decode(
                encoding_iana,
                errors="ignore" if is_multi_byte_decoder else "strict",
            )

            # multi-byte bad cutting detector and adjustment
            # not the cleanest way to perform that fix but clever enough for now.
            if is_multi_byte_decoder and i > 0:
                chunk_partial_size_chk: int = min(chunk_size, 16)

                if (
                    decoded_payload
                    and chunk[:chunk_partial_size_chk] not in decoded_payload
                ):
                    for j in range(i, i - 4, -1):
                        cut_sequence = sequences[j:chunk_end]

                        if bom_or_sig_available and strip_sig_or_bom is False:
                            cut_sequence = sig_payload + cut_sequence

                        chunk = cut_sequence.decode(encoding_iana, errors="ignore")

                        if chunk[:chunk_partial_size_chk] in decoded_payload:
                            break

            yield chunk

# === NexusCore/openenv\Lib\site-packages\trio\_highlevel_socket.py ===
# "High-level" networking interface
from __future__ import annotations

import errno
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, overload

import trio

from . import socket as tsocket
from ._util import ConflictDetector, final
from .abc import HalfCloseableStream, Listener

if TYPE_CHECKING:
    from collections.abc import Generator

    from typing_extensions import Buffer

    from ._socket import SocketType

# XX TODO: this number was picked arbitrarily. We should do experiments to
# tune it. (Or make it dynamic -- one idea is to start small and increase it
# if we observe single reads filling up the whole buffer, at least within some
# limits.)
DEFAULT_RECEIVE_SIZE = 65536

_closed_stream_errnos = {
    # Unix
    errno.EBADF,
    # Windows
    errno.ENOTSOCK,
}


@contextmanager
def _translate_socket_errors_to_stream_errors() -> Generator[None, None, None]:
    try:
        yield
    except OSError as exc:
        if exc.errno in _closed_stream_errnos:
            raise trio.ClosedResourceError("this socket was already closed") from None
        else:
            raise trio.BrokenResourceError(f"socket connection broken: {exc}") from exc


@final
class SocketStream(HalfCloseableStream):
    """An implementation of the :class:`trio.abc.HalfCloseableStream`
    interface based on a raw network socket.

    Args:
      socket: The Trio socket object to wrap. Must have type ``SOCK_STREAM``,
          and be connected.

    By default for TCP sockets, :class:`SocketStream` enables ``TCP_NODELAY``,
    and (on platforms where it's supported) enables ``TCP_NOTSENT_LOWAT`` with
    a reasonable buffer size (currently 16 KiB) – see `issue #72
    <https://github.com/python-trio/trio/issues/72>`__ for discussion. You can
    of course override these defaults by calling :meth:`setsockopt`.

    Once a :class:`SocketStream` object is constructed, it implements the full
    :class:`trio.abc.HalfCloseableStream` interface. In addition, it provides
    a few extra features:

    .. attribute:: socket

       The Trio socket object that this stream wraps.

    """

    def __init__(self, socket: SocketType) -> None:
        if not isinstance(socket, tsocket.SocketType):
            raise TypeError("SocketStream requires a Trio socket object")
        if socket.type != tsocket.SOCK_STREAM:
            raise ValueError("SocketStream requires a SOCK_STREAM socket")

        self.socket = socket
        self._send_conflict_detector = ConflictDetector(
            "another task is currently sending data on this SocketStream",
        )

        # Socket defaults:

        # Not supported on e.g. unix domain sockets
        with suppress(OSError):
            self.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, True)

        if hasattr(tsocket, "TCP_NOTSENT_LOWAT"):
            # 16 KiB is pretty arbitrary and could probably do with some
            # tuning. (Apple is also setting this by default in CFNetwork
            # apparently -- I'm curious what value they're using, though I
            # couldn't find it online trivially. CFNetwork-129.20 source
            # has no mentions of TCP_NOTSENT_LOWAT. This presentation says
            # "typically 8 kilobytes":
            # http://devstreaming.apple.com/videos/wwdc/2015/719ui2k57m/719/719_your_app_and_next_generation_networks.pdf?dl=1
            # ). The theory is that you want it to be bandwidth *
            # rescheduling interval.
            with suppress(OSError):
                self.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NOTSENT_LOWAT, 2**14)

    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        if self.socket.did_shutdown_SHUT_WR:
            raise trio.ClosedResourceError("can't send data after sending EOF")
        with self._send_conflict_detector:
            with _translate_socket_errors_to_stream_errors():
                with memoryview(data) as data:
                    if not data:
                        if self.socket.fileno() == -1:
                            raise trio.ClosedResourceError("socket was already closed")
                        await trio.lowlevel.checkpoint()
                        return
                    total_sent = 0
                    while total_sent < len(data):
                        with data[total_sent:] as remaining:
                            sent = await self.socket.send(remaining)
                        total_sent += sent

    async def wait_send_all_might_not_block(self) -> None:
        with self._send_conflict_detector:
            if self.socket.fileno() == -1:
                raise trio.ClosedResourceError
            with _translate_socket_errors_to_stream_errors():
                await self.socket.wait_writable()

    async def send_eof(self) -> None:
        with self._send_conflict_detector:
            await trio.lowlevel.checkpoint()
            # On macOS, calling shutdown a second time raises ENOTCONN, but
            # send_eof needs to be idempotent.
            if self.socket.did_shutdown_SHUT_WR:
                return
            with _translate_socket_errors_to_stream_errors():
                self.socket.shutdown(tsocket.SHUT_WR)

    async def receive_some(self, max_bytes: int | None = None) -> bytes:
        if max_bytes is None:
            max_bytes = DEFAULT_RECEIVE_SIZE
        if max_bytes < 1:
            raise ValueError("max_bytes must be >= 1")
        with _translate_socket_errors_to_stream_errors():
            return await self.socket.recv(max_bytes)

    async def aclose(self) -> None:
        self.socket.close()
        await trio.lowlevel.checkpoint()

    # __aenter__, __aexit__ inherited from HalfCloseableStream are OK

    @overload
    def setsockopt(self, level: int, option: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(self, level: int, option: int, value: None, length: int) -> None: ...

    def setsockopt(
        self,
        level: int,
        option: int,
        value: int | Buffer | None,
        length: int | None = None,
    ) -> None:
        """Set an option on the underlying socket.

        See :meth:`socket.socket.setsockopt` for details.

        """
        if length is None:
            if value is None:
                raise TypeError(
                    "invalid value for argument 'value', must not be None when specifying length",
                )
            return self.socket.setsockopt(level, option, value)
        if value is not None:
            raise TypeError(
                f"invalid value for argument 'value': {value!r}, must be None when specifying optlen",
            )
        return self.socket.setsockopt(level, option, value, length)

    @overload
    def getsockopt(self, level: int, option: int) -> int: ...

    @overload
    def getsockopt(self, level: int, option: int, buffersize: int) -> bytes: ...

    def getsockopt(self, level: int, option: int, buffersize: int = 0) -> int | bytes:
        """Check the current value of an option on the underlying socket.

        See :meth:`socket.socket.getsockopt` for details.

        """
        # This is to work around
        #   https://bitbucket.org/pypy/pypy/issues/2561
        # We should be able to drop it when the next PyPy3 beta is released.
        if buffersize == 0:
            return self.socket.getsockopt(level, option)
        else:
            return self.socket.getsockopt(level, option, buffersize)


################################################################
# SocketListener
################################################################

# Accept error handling
# =====================
#
# Literature review
# -----------------
#
# Here's a list of all the possible errors that accept() can return, according
# to the POSIX spec or the Linux, FreeBSD, macOS, and Windows docs:
#
# Can't happen with a Trio socket:
# - EAGAIN/(WSA)EWOULDBLOCK
# - EINTR
# - WSANOTINITIALISED
# - WSAEINPROGRESS: a blocking call is already in progress
# - WSAEINTR: someone called WSACancelBlockingCall, but we don't make blocking
#   calls in the first place
#
# Something is wrong with our call:
# - EBADF: not a file descriptor
# - (WSA)EINVAL: socket isn't listening, or (Linux, BSD) bad flags
# - (WSA)ENOTSOCK: not a socket
# - (WSA)EOPNOTSUPP: this kind of socket doesn't support accept
# - (Linux, FreeBSD, Windows) EFAULT: the sockaddr pointer points to readonly
#   memory
#
# Something is wrong with the environment:
# - (WSA)EMFILE: this process hit its fd limit
# - ENFILE: the system hit its fd limit
# - (WSA)ENOBUFS, ENOMEM: unspecified memory problems
#
# Something is wrong with the connection we were going to accept. There's a
# ton of variability between systems here:
# - ECONNABORTED: documented everywhere, but apparently only the BSDs do this
#   (signals a connection was closed/reset before being accepted)
# - EPROTO: unspecified protocol error
# - (Linux) EPERM: firewall rule prevented connection
# - (Linux) ENETDOWN, EPROTO, ENOPROTOOPT, EHOSTDOWN, ENONET, EHOSTUNREACH,
#   EOPNOTSUPP, ENETUNREACH, ENOSR, ESOCKTNOSUPPORT, EPROTONOSUPPORT,
#   ETIMEDOUT, ... or any other error that the socket could give, because
#   apparently if an error happens on a connection before it's accept()ed,
#   Linux will report that error from accept().
# - (Windows) WSAECONNRESET, WSAENETDOWN
#
#
# Code review
# -----------
#
# What do other libraries do?
#
# Twisted on Unix or when using nonblocking I/O on Windows:
# - ignores EPERM, with comment about Linux firewalls
# - logs and ignores EMFILE, ENOBUFS, ENFILE, ENOMEM, ECONNABORTED
#   Comment notes that ECONNABORTED is a BSDism and that Linux returns the
#   socket before having it fail, and macOS just silently discards it.
# - other errors are raised, which is logged + kills the socket
# ref: src/twisted/internet/tcp.py, Port.doRead
#
# Twisted using IOCP on Windows:
# - logs and ignores all errors
# ref: src/twisted/internet/iocpreactor/tcp.py, Port.handleAccept
#
# Tornado:
# - ignore ECONNABORTED (comments notes that it was observed on FreeBSD)
# - everything else raised, but all this does (by default) is cause it to be
#   logged and then ignored
# (ref: tornado/netutil.py, tornado/ioloop.py)
#
# libuv on Unix:
# - ignores ECONNABORTED
# - does a "trick" for EMFILE or ENFILE
# - all other errors passed to the connection_cb to be handled
# (ref: src/unix/stream.c:uv__server_io, uv__emfile_trick)
#
# libuv on Windows:
# src/win/tcp.c:uv_tcp_queue_accept
#   this calls AcceptEx, and then arranges to call:
# src/win/tcp.c:uv_process_tcp_accept_req
#   this gets the result from AcceptEx. If the original AcceptEx call failed,
#   then "we stop accepting connections and report this error to the
#   connection callback". I think this is for things like ENOTSOCK. If
#   AcceptEx successfully queues an overlapped operation, and then that
#   reports an error, it's just discarded.
#
# asyncio, selector mode:
# - ignores EWOULDBLOCK, EINTR, ECONNABORTED
# - on EMFILE, ENFILE, ENOBUFS, ENOMEM, logs an error and then disables the
#   listening loop for 1 second
# - everything else raises, but then the event loop just logs and ignores it
# (selector_events.py: BaseSelectorEventLoop._accept_connection)
#
#
# What should we do?
# ------------------
#
# When accept() returns an error, we can either ignore it or raise it.
#
# We have a long list of errors that should be ignored, and a long list of
# errors that should be raised. The big question is what to do with an error
# that isn't on either list. On Linux apparently you can get nearly arbitrary
# errors from accept() and they should be ignored, because it just indicates a
# socket that crashed before it began, and there isn't really anything to be
# done about this, plus on other platforms you may not get any indication at
# all, so programs have to tolerate not getting any indication too. OTOH if we
# get an unexpected error then it could indicate something arbitrarily bad --
# after all, it's unexpected.
#
# Given that we know that other libraries seem to be getting along fine with a
# fairly minimal list of errors to ignore, I think we'll be OK if we write
# down that list and then raise on everything else.
#
# The other question is what to do about the capacity problem errors: EMFILE,
# ENFILE, ENOBUFS, ENOMEM. Just flat out ignoring these is clearly not optimal
# -- at the very least you want to log them, and probably you want to take
# some remedial action. And if we ignore them then it prevents higher levels
# from doing anything clever with them. So we raise them.

_ignorable_accept_errno_names = [
    # Linux can do this when the a connection is denied by the firewall
    "EPERM",
    # BSDs with an early close/reset
    "ECONNABORTED",
    # All the other miscellany noted above -- may not happen in practice, but
    # whatever.
    "EPROTO",
    "ENETDOWN",
    "ENOPROTOOPT",
    "EHOSTDOWN",
    "ENONET",
    "EHOSTUNREACH",
    "EOPNOTSUPP",
    "ENETUNREACH",
    "ENOSR",
    "ESOCKTNOSUPPORT",
    "EPROTONOSUPPORT",
    "ETIMEDOUT",
    "ECONNRESET",
]

# Not all errnos are defined on all platforms
_ignorable_accept_errnos: set[int] = set()
for name in _ignorable_accept_errno_names:
    with suppress(AttributeError):
        _ignorable_accept_errnos.add(getattr(errno, name))


@final
class SocketListener(Listener[SocketStream]):
    """A :class:`~trio.abc.Listener` that uses a listening socket to accept
    incoming connections as :class:`SocketStream` objects.

    Args:
      socket: The Trio socket object to wrap. Must have type ``SOCK_STREAM``,
          and be listening.

    Note that the :class:`SocketListener` "takes ownership" of the given
    socket; closing the :class:`SocketListener` will also close the socket.

    .. attribute:: socket

       The Trio socket object that this stream wraps.

    """

    def __init__(self, socket: SocketType) -> None:
        if not isinstance(socket, tsocket.SocketType):
            raise TypeError("SocketListener requires a Trio socket object")
        if socket.type != tsocket.SOCK_STREAM:
            raise ValueError("SocketListener requires a SOCK_STREAM socket")
        try:
            listening = socket.getsockopt(tsocket.SOL_SOCKET, tsocket.SO_ACCEPTCONN)
        except OSError:
            # SO_ACCEPTCONN fails on macOS; we just have to trust the user.
            pass
        else:
            if not listening:
                raise ValueError("SocketListener requires a listening socket")

        self.socket = socket

    async def accept(self) -> SocketStream:
        """Accept an incoming connection.

        Returns:
          :class:`SocketStream`

        Raises:
          OSError: if the underlying call to ``accept`` raises an unexpected
              error.
          ClosedResourceError: if you already closed the socket.

        This method handles routine errors like ``ECONNABORTED``, but passes
        other errors on to its caller. In particular, it does *not* make any
        special effort to handle resource exhaustion errors like ``EMFILE``,
        ``ENFILE``, ``ENOBUFS``, ``ENOMEM``.

        """
        while True:
            try:
                sock, _ = await self.socket.accept()
            except OSError as exc:
                if exc.errno in _closed_stream_errnos:
                    raise trio.ClosedResourceError from None
                if exc.errno not in _ignorable_accept_errnos:
                    raise
            else:
                return SocketStream(sock)

    async def aclose(self) -> None:
        """Close this listener and its underlying socket."""
        self.socket.close()
        await trio.lowlevel.checkpoint()

# === NexusCore/openenv\Lib\site-packages\git\objects\tree.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["TreeModifier", "Tree"]

import sys

import git.diff as git_diff
from git.util import IterableList, join_path, to_bin_sha

from . import util
from .base import IndexObjUnion, IndexObject
from .blob import Blob
from .fun import tree_entries_from_data, tree_to_stream
from .submodule.base import Submodule

# typing -------------------------------------------------

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Tuple,
    TYPE_CHECKING,
    Type,
    Union,
    cast,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from git.types import PathLike

if TYPE_CHECKING:
    from io import BytesIO

    from git.repo import Repo

TreeCacheTup = Tuple[bytes, int, str]

TraversedTreeTup = Union[Tuple[Union["Tree", None], IndexObjUnion, Tuple["Submodule", "Submodule"]]]

# --------------------------------------------------------

cmp: Callable[[str, str], int] = lambda a, b: (a > b) - (a < b)


class TreeModifier:
    """A utility class providing methods to alter the underlying cache in a list-like
    fashion.

    Once all adjustments are complete, the :attr:`_cache`, which really is a reference
    to the cache of a tree, will be sorted. This ensures it will be in a serializable
    state.
    """

    __slots__ = ("_cache",)

    def __init__(self, cache: List[TreeCacheTup]) -> None:
        self._cache = cache

    def _index_by_name(self, name: str) -> int:
        """:return: index of an item with name, or -1 if not found"""
        for i, t in enumerate(self._cache):
            if t[2] == name:
                return i
            # END found item
        # END for each item in cache
        return -1

    # { Interface
    def set_done(self) -> "TreeModifier":
        """Call this method once you are done modifying the tree information.

        This may be called several times, but be aware that each call will cause a sort
        operation.

        :return:
            self
        """
        self._cache.sort(key=lambda x: (x[2] + "/") if x[1] == Tree.tree_id << 12 else x[2])
        return self

    # } END interface

    # { Mutators
    def add(self, sha: bytes, mode: int, name: str, force: bool = False) -> "TreeModifier":
        """Add the given item to the tree.

        If an item with the given name already exists, nothing will be done, but a
        :exc:`ValueError` will be raised if the sha and mode of the existing item do not
        match the one you add, unless `force` is ``True``.

        :param sha:
            The 20 or 40 byte sha of the item to add.

        :param mode:
            :class:`int` representing the stat-compatible mode of the item.

        :param force:
            If ``True``, an item with your name and information will overwrite any
            existing item with the same name, no matter which information it has.

        :return:
            self
        """
        if "/" in name:
            raise ValueError("Name must not contain '/' characters")
        if (mode >> 12) not in Tree._map_id_to_type:
            raise ValueError("Invalid object type according to mode %o" % mode)

        sha = to_bin_sha(sha)
        index = self._index_by_name(name)

        item = (sha, mode, name)

        if index == -1:
            self._cache.append(item)
        else:
            if force:
                self._cache[index] = item
            else:
                ex_item = self._cache[index]
                if ex_item[0] != sha or ex_item[1] != mode:
                    raise ValueError("Item %r existed with different properties" % name)
                # END handle mismatch
            # END handle force
        # END handle name exists
        return self

    def add_unchecked(self, binsha: bytes, mode: int, name: str) -> None:
        """Add the given item to the tree. Its correctness is assumed, so it is the
        caller's responsibility to ensure that the input is correct.

        For more information on the parameters, see :meth:`add`.

        :param binsha:
            20 byte binary sha.
        """
        assert isinstance(binsha, bytes) and isinstance(mode, int) and isinstance(name, str)
        tree_cache = (binsha, mode, name)

        self._cache.append(tree_cache)

    def __delitem__(self, name: str) -> None:
        """Delete an item with the given name if it exists."""
        index = self._index_by_name(name)
        if index > -1:
            del self._cache[index]

    # } END mutators


class Tree(IndexObject, git_diff.Diffable, util.Traversable, util.Serializable):
    R"""Tree objects represent an ordered list of :class:`~git.objects.blob.Blob`\s and
    other :class:`Tree`\s.

    See :manpage:`gitglossary(7)` on "tree object":
    https://git-scm.com/docs/gitglossary#def_tree_object

    Subscripting is supported, as with a list or dict:

    * Access a specific blob using the ``tree["filename"]`` notation.
    * You may likewise access by index, like ``blob = tree[0]``.
    """

    type: Literal["tree"] = "tree"

    __slots__ = ("_cache",)

    # Actual integer IDs for comparison.
    commit_id = 0o16  # Equals stat.S_IFDIR | stat.S_IFLNK - a directory link.
    blob_id = 0o10
    symlink_id = 0o12
    tree_id = 0o04

    _map_id_to_type: Dict[int, Type[IndexObjUnion]] = {
        commit_id: Submodule,
        blob_id: Blob,
        symlink_id: Blob,
        # Tree ID added once Tree is defined.
    }

    def __init__(
        self,
        repo: "Repo",
        binsha: bytes,
        mode: int = tree_id << 12,
        path: Union[PathLike, None] = None,
    ):
        super().__init__(repo, binsha, mode, path)

    @classmethod
    def _get_intermediate_items(
        cls,
        index_object: IndexObjUnion,
    ) -> Union[Tuple["Tree", ...], Tuple[()]]:
        if index_object.type == "tree":
            return tuple(index_object._iter_convert_to_object(index_object._cache))
        return ()

    def _set_cache_(self, attr: str) -> None:
        if attr == "_cache":
            # Set the data when we need it.
            ostream = self.repo.odb.stream(self.binsha)
            self._cache: List[TreeCacheTup] = tree_entries_from_data(ostream.read())
        else:
            super()._set_cache_(attr)
        # END handle attribute

    def _iter_convert_to_object(self, iterable: Iterable[TreeCacheTup]) -> Iterator[IndexObjUnion]:
        """Iterable yields tuples of (binsha, mode, name), which will be converted to
        the respective object representation.
        """
        for binsha, mode, name in iterable:
            path = join_path(self.path, name)
            try:
                yield self._map_id_to_type[mode >> 12](self.repo, binsha, mode, path)
            except KeyError as e:
                raise TypeError("Unknown mode %o found in tree data for path '%s'" % (mode, path)) from e
        # END for each item

    def join(self, file: str) -> IndexObjUnion:
        """Find the named object in this tree's contents.

        :return:
            :class:`~git.objects.blob.Blob`, :class:`Tree`, or
            :class:`~git.objects.submodule.base.Submodule`

        :raise KeyError:
            If the given file or tree does not exist in this tree.
        """
        msg = "Blob or Tree named %r not found"
        if "/" in file:
            tree = self
            item = self
            tokens = file.split("/")
            for i, token in enumerate(tokens):
                item = tree[token]
                if item.type == "tree":
                    tree = item
                else:
                    # Safety assertion - blobs are at the end of the path.
                    if i != len(tokens) - 1:
                        raise KeyError(msg % file)
                    return item
                # END handle item type
            # END for each token of split path
            if item == self:
                raise KeyError(msg % file)
            return item
        else:
            for info in self._cache:
                if info[2] == file:  # [2] == name
                    return self._map_id_to_type[info[1] >> 12](
                        self.repo, info[0], info[1], join_path(self.path, info[2])
                    )
            # END for each obj
            raise KeyError(msg % file)
        # END handle long paths

    def __truediv__(self, file: str) -> IndexObjUnion:
        """The ``/`` operator is another syntax for joining.

        See :meth:`join` for details.
        """
        return self.join(file)

    @property
    def trees(self) -> List["Tree"]:
        """:return: list(Tree, ...) List of trees directly below this tree"""
        return [i for i in self if i.type == "tree"]

    @property
    def blobs(self) -> List[Blob]:
        """:return: list(Blob, ...) List of blobs directly below this tree"""
        return [i for i in self if i.type == "blob"]

    @property
    def cache(self) -> TreeModifier:
        """
        :return:
            An object allowing modification of the internal cache. This can be used to
            change the tree's contents. When done, make sure you call
            :meth:`~TreeModifier.set_done` on the tree modifier, or serialization
            behaviour will be incorrect.

        :note:
            See :class:`TreeModifier` for more information on how to alter the cache.
        """
        return TreeModifier(self._cache)

    def traverse(
        self,
        predicate: Callable[[Union[IndexObjUnion, TraversedTreeTup], int], bool] = lambda i, d: True,
        prune: Callable[[Union[IndexObjUnion, TraversedTreeTup], int], bool] = lambda i, d: False,
        depth: int = -1,
        branch_first: bool = True,
        visit_once: bool = False,
        ignore_self: int = 1,
        as_edge: bool = False,
    ) -> Union[Iterator[IndexObjUnion], Iterator[TraversedTreeTup]]:
        """For documentation, see
        `Traversable._traverse() <git.objects.util.Traversable._traverse>`.

        Trees are set to ``visit_once = False`` to gain more performance in the
        traversal.
        """

        # # To typecheck instead of using cast.
        # import itertools
        # def is_tree_traversed(inp: Tuple) -> TypeGuard[Tuple[Iterator[Union['Tree', 'Blob', 'Submodule']]]]:
        #     return all(isinstance(x, (Blob, Tree, Submodule)) for x in inp[1])

        # ret = super().traverse(predicate, prune, depth, branch_first, visit_once, ignore_self)
        # ret_tup = itertools.tee(ret, 2)
        # assert is_tree_traversed(ret_tup), f"Type is {[type(x) for x in list(ret_tup[0])]}"
        # return ret_tup[0]

        return cast(
            Union[Iterator[IndexObjUnion], Iterator[TraversedTreeTup]],
            super()._traverse(
                predicate,  # type: ignore[arg-type]
                prune,  # type: ignore[arg-type]
                depth,
                branch_first,
                visit_once,
                ignore_self,
            ),
        )

    def list_traverse(self, *args: Any, **kwargs: Any) -> IterableList[IndexObjUnion]:
        """
        :return:
            :class:`~git.util.IterableList` with the results of the traversal as
            produced by :meth:`traverse`

            Tree -> IterableList[Union[Submodule, Tree, Blob]]
        """
        return super()._list_traverse(*args, **kwargs)

    # List protocol

    def __getslice__(self, i: int, j: int) -> List[IndexObjUnion]:
        return list(self._iter_convert_to_object(self._cache[i:j]))

    def __iter__(self) -> Iterator[IndexObjUnion]:
        return self._iter_convert_to_object(self._cache)

    def __len__(self) -> int:
        return len(self._cache)

    def __getitem__(self, item: Union[str, int, slice]) -> IndexObjUnion:
        if isinstance(item, int):
            info = self._cache[item]
            return self._map_id_to_type[info[1] >> 12](self.repo, info[0], info[1], join_path(self.path, info[2]))

        if isinstance(item, str):
            # compatibility
            return self.join(item)
        # END index is basestring

        raise TypeError("Invalid index type: %r" % item)

    def __contains__(self, item: Union[IndexObjUnion, PathLike]) -> bool:
        if isinstance(item, IndexObject):
            for info in self._cache:
                if item.binsha == info[0]:
                    return True
                # END compare sha
            # END for each entry
        # END handle item is index object
        # compatibility

        # Treat item as repo-relative path.
        else:
            path = self.path
            for info in self._cache:
                if item == join_path(path, info[2]):
                    return True
        # END for each item
        return False

    def __reversed__(self) -> Iterator[IndexObjUnion]:
        return reversed(self._iter_convert_to_object(self._cache))  # type: ignore[call-overload]

    def _serialize(self, stream: "BytesIO") -> "Tree":
        """Serialize this tree into the stream. Assumes sorted tree data.

        :note:
            We will assume our tree data to be in a sorted state. If this is not the
            case, serialization will not generate a correct tree representation as these
            are assumed to be sorted by algorithms.
        """
        tree_to_stream(self._cache, stream.write)
        return self

    def _deserialize(self, stream: "BytesIO") -> "Tree":
        self._cache = tree_entries_from_data(stream.read())
        return self


# END tree

# Finalize map definition.
Tree._map_id_to_type[Tree.tree_id] = Tree

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\registry.py ===
from enum import Enum
import importlib


class BackendFilter(Enum):
    """
    Filter used with :meth:`~matplotlib.backends.registry.BackendRegistry.list_builtin`

    .. versionadded:: 3.9
    """
    INTERACTIVE = 0
    NON_INTERACTIVE = 1


class BackendRegistry:
    """
    Registry of backends available within Matplotlib.

    This is the single source of truth for available backends.

    All use of ``BackendRegistry`` should be via the singleton instance
    ``backend_registry`` which can be imported from ``matplotlib.backends``.

    Each backend has a name, a module name containing the backend code, and an
    optional GUI framework that must be running if the backend is interactive.
    There are three sources of backends: built-in (source code is within the
    Matplotlib repository), explicit ``module://some.backend`` syntax (backend is
    obtained by loading the module), or via an entry point (self-registering
    backend in an external package).

    .. versionadded:: 3.9
    """
    # Mapping of built-in backend name to GUI framework, or "headless" for no
    # GUI framework. Built-in backends are those which are included in the
    # Matplotlib repo. A backend with name 'name' is located in the module
    # f"matplotlib.backends.backend_{name.lower()}"
    _BUILTIN_BACKEND_TO_GUI_FRAMEWORK = {
        "gtk3agg": "gtk3",
        "gtk3cairo": "gtk3",
        "gtk4agg": "gtk4",
        "gtk4cairo": "gtk4",
        "macosx": "macosx",
        "nbagg": "nbagg",
        "notebook": "nbagg",
        "qtagg": "qt",
        "qtcairo": "qt",
        "qt5agg": "qt5",
        "qt5cairo": "qt5",
        "tkagg": "tk",
        "tkcairo": "tk",
        "webagg": "webagg",
        "wx": "wx",
        "wxagg": "wx",
        "wxcairo": "wx",
        "agg": "headless",
        "cairo": "headless",
        "pdf": "headless",
        "pgf": "headless",
        "ps": "headless",
        "svg": "headless",
        "template": "headless",
    }

    # Reverse mapping of gui framework to preferred built-in backend.
    _GUI_FRAMEWORK_TO_BACKEND = {
        "gtk3": "gtk3agg",
        "gtk4": "gtk4agg",
        "headless": "agg",
        "macosx": "macosx",
        "qt": "qtagg",
        "qt5": "qt5agg",
        "qt6": "qtagg",
        "tk": "tkagg",
        "wx": "wxagg",
    }

    def __init__(self):
        # Only load entry points when first needed.
        self._loaded_entry_points = False

        # Mapping of non-built-in backend to GUI framework, added dynamically from
        # entry points and from matplotlib.use("module://some.backend") format.
        # New entries have an "unknown" GUI framework that is determined when first
        # needed by calling _get_gui_framework_by_loading.
        self._backend_to_gui_framework = {}

        # Mapping of backend name to module name, where different from
        # f"matplotlib.backends.backend_{backend_name.lower()}". These are either
        # hardcoded for backward compatibility, or loaded from entry points or
        # "module://some.backend" syntax.
        self._name_to_module = {
            "notebook": "nbagg",
        }

    def _backend_module_name(self, backend):
        if backend.startswith("module://"):
            return backend[9:]

        # Return name of module containing the specified backend.
        # Does not check if the backend is valid, use is_valid_backend for that.
        backend = backend.lower()

        # Check if have specific name to module mapping.
        backend = self._name_to_module.get(backend, backend)

        return (backend[9:] if backend.startswith("module://")
                else f"matplotlib.backends.backend_{backend}")

    def _clear(self):
        # Clear all dynamically-added data, used for testing only.
        self.__init__()

    def _ensure_entry_points_loaded(self):
        # Load entry points, if they have not already been loaded.
        if not self._loaded_entry_points:
            entries = self._read_entry_points()
            self._validate_and_store_entry_points(entries)
            self._loaded_entry_points = True

    def _get_gui_framework_by_loading(self, backend):
        # Determine GUI framework for a backend by loading its module and reading the
        # FigureCanvas.required_interactive_framework attribute.
        # Returns "headless" if there is no GUI framework.
        module = self.load_backend_module(backend)
        canvas_class = module.FigureCanvas
        return canvas_class.required_interactive_framework or "headless"

    def _read_entry_points(self):
        # Read entry points of modules that self-advertise as Matplotlib backends.
        # Expects entry points like this one from matplotlib-inline (in pyproject.toml
        # format):
        #   [project.entry-points."matplotlib.backend"]
        #   inline = "matplotlib_inline.backend_inline"
        import importlib.metadata as im

        entry_points = im.entry_points(group="matplotlib.backend")
        entries = [(entry.name, entry.value) for entry in entry_points]

        # For backward compatibility, if matplotlib-inline and/or ipympl are installed
        # but too old to include entry points, create them. Do not import ipympl
        # directly as this calls matplotlib.use() whilst in this function.
        def backward_compatible_entry_points(
                entries, module_name, threshold_version, names, target):
            from matplotlib import _parse_to_version_info
            try:
                module_version = im.version(module_name)
                if _parse_to_version_info(module_version) < threshold_version:
                    for name in names:
                        entries.append((name, target))
            except im.PackageNotFoundError:
                pass

        names = [entry[0] for entry in entries]
        if "inline" not in names:
            backward_compatible_entry_points(
                entries, "matplotlib_inline", (0, 1, 7), ["inline"],
                "matplotlib_inline.backend_inline")
        if "ipympl" not in names:
            backward_compatible_entry_points(
                entries, "ipympl", (0, 9, 4), ["ipympl", "widget"],
                "ipympl.backend_nbagg")

        return entries

    def _validate_and_store_entry_points(self, entries):
        # Validate and store entry points so that they can be used via matplotlib.use()
        # in the normal manner. Entry point names cannot be of module:// format, cannot
        # shadow a built-in backend name, and there cannot be multiple entry points
        # with the same name but different modules. Multiple entry points with the same
        # name and value are permitted (it can sometimes happen outside of our control,
        # see https://github.com/matplotlib/matplotlib/issues/28367).
        for name, module in set(entries):
            name = name.lower()
            if name.startswith("module://"):
                raise RuntimeError(
                    f"Entry point name '{name}' cannot start with 'module://'")
            if name in self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK:
                raise RuntimeError(f"Entry point name '{name}' is a built-in backend")
            if name in self._backend_to_gui_framework:
                raise RuntimeError(f"Entry point name '{name}' duplicated")

            self._name_to_module[name] = "module://" + module
            # Do not yet know backend GUI framework, determine it only when necessary.
            self._backend_to_gui_framework[name] = "unknown"

    def backend_for_gui_framework(self, framework):
        """
        Return the name of the backend corresponding to the specified GUI framework.

        Parameters
        ----------
        framework : str
            GUI framework such as "qt".

        Returns
        -------
        str or None
            Backend name or None if GUI framework not recognised.
        """
        return self._GUI_FRAMEWORK_TO_BACKEND.get(framework.lower())

    def is_valid_backend(self, backend):
        """
        Return True if the backend name is valid, False otherwise.

        A backend name is valid if it is one of the built-in backends or has been
        dynamically added via an entry point. Those beginning with ``module://`` are
        always considered valid and are added to the current list of all backends
        within this function.

        Even if a name is valid, it may not be importable or usable. This can only be
        determined by loading and using the backend module.

        Parameters
        ----------
        backend : str
            Name of backend.

        Returns
        -------
        bool
            True if backend is valid, False otherwise.
        """
        if not backend.startswith("module://"):
            backend = backend.lower()

        # For backward compatibility, convert ipympl and matplotlib-inline long
        # module:// names to their shortened forms.
        backwards_compat = {
            "module://ipympl.backend_nbagg": "widget",
            "module://matplotlib_inline.backend_inline": "inline",
        }
        backend = backwards_compat.get(backend, backend)

        if (backend in self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK or
                backend in self._backend_to_gui_framework):
            return True

        if backend.startswith("module://"):
            self._backend_to_gui_framework[backend] = "unknown"
            return True

        # Only load entry points if really need to and not already done so.
        self._ensure_entry_points_loaded()
        if backend in self._backend_to_gui_framework:
            return True

        return False

    def list_all(self):
        """
        Return list of all known backends.

        These include built-in backends and those obtained at runtime either from entry
        points or explicit ``module://some.backend`` syntax.

        Entry points will be loaded if they haven't been already.

        Returns
        -------
        list of str
            Backend names.
        """
        self._ensure_entry_points_loaded()
        return [*self.list_builtin(), *self._backend_to_gui_framework]

    def list_builtin(self, filter_=None):
        """
        Return list of backends that are built into Matplotlib.

        Parameters
        ----------
        filter_ : `~.BackendFilter`, optional
            Filter to apply to returned backends. For example, to return only
            non-interactive backends use `.BackendFilter.NON_INTERACTIVE`.

        Returns
        -------
        list of str
            Backend names.
        """
        if filter_ == BackendFilter.INTERACTIVE:
            return [k for k, v in self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK.items()
                    if v != "headless"]
        elif filter_ == BackendFilter.NON_INTERACTIVE:
            return [k for k, v in self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK.items()
                    if v == "headless"]

        return [*self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK]

    def list_gui_frameworks(self):
        """
        Return list of GUI frameworks used by Matplotlib backends.

        Returns
        -------
        list of str
            GUI framework names.
        """
        return [k for k in self._GUI_FRAMEWORK_TO_BACKEND if k != "headless"]

    def load_backend_module(self, backend):
        """
        Load and return the module containing the specified backend.

        Parameters
        ----------
        backend : str
            Name of backend to load.

        Returns
        -------
        Module
            Module containing backend.
        """
        module_name = self._backend_module_name(backend)
        return importlib.import_module(module_name)

    def resolve_backend(self, backend):
        """
        Return the backend and GUI framework for the specified backend name.

        If the GUI framework is not yet known then it will be determined by loading the
        backend module and checking the ``FigureCanvas.required_interactive_framework``
        attribute.

        This function only loads entry points if they have not already been loaded and
        the backend is not built-in and not of ``module://some.backend`` format.

        Parameters
        ----------
        backend : str or None
            Name of backend, or None to use the default backend.

        Returns
        -------
        backend : str
            The backend name.
        framework : str or None
            The GUI framework, which will be None for a backend that is non-interactive.
        """
        if isinstance(backend, str):
            if not backend.startswith("module://"):
                backend = backend.lower()
        else:  # Might be _auto_backend_sentinel or None
            # Use whatever is already running...
            from matplotlib import get_backend
            backend = get_backend()

        # Is backend already known (built-in or dynamically loaded)?
        gui = (self._BUILTIN_BACKEND_TO_GUI_FRAMEWORK.get(backend) or
               self._backend_to_gui_framework.get(backend))

        # Is backend "module://something"?
        if gui is None and isinstance(backend, str) and backend.startswith("module://"):
            gui = "unknown"

        # Is backend a possible entry point?
        if gui is None and not self._loaded_entry_points:
            self._ensure_entry_points_loaded()
            gui = self._backend_to_gui_framework.get(backend)

        # Backend known but not its gui framework.
        if gui == "unknown":
            gui = self._get_gui_framework_by_loading(backend)
            self._backend_to_gui_framework[backend] = gui

        if gui is None:
            raise RuntimeError(f"'{backend}' is not a recognised backend name")

        return backend, gui if gui != "headless" else None

    def resolve_gui_or_backend(self, gui_or_backend):
        """
        Return the backend and GUI framework for the specified string that may be
        either a GUI framework or a backend name, tested in that order.

        This is for use with the IPython %matplotlib magic command which may be a GUI
        framework such as ``%matplotlib qt`` or a backend name such as
        ``%matplotlib qtagg``.

        This function only loads entry points if they have not already been loaded and
        the backend is not built-in and not of ``module://some.backend`` format.

        Parameters
        ----------
        gui_or_backend : str or None
            Name of GUI framework or backend, or None to use the default backend.

        Returns
        -------
        backend : str
            The backend name.
        framework : str or None
            The GUI framework, which will be None for a backend that is non-interactive.
        """
        if not gui_or_backend.startswith("module://"):
            gui_or_backend = gui_or_backend.lower()

        # First check if it is a gui loop name.
        backend = self.backend_for_gui_framework(gui_or_backend)
        if backend is not None:
            return backend, gui_or_backend if gui_or_backend != "headless" else None

        # Then check if it is a backend name.
        try:
            return self.resolve_backend(gui_or_backend)
        except Exception:  # KeyError ?
            raise RuntimeError(
                f"'{gui_or_backend}' is not a recognised GUI loop or backend name")


# Singleton
backend_registry = BackendRegistry()

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\anchored_artists.py ===
from matplotlib import transforms
from matplotlib.offsetbox import (AnchoredOffsetbox, AuxTransformBox,
                                  DrawingArea, TextArea, VPacker)
from matplotlib.patches import (Rectangle, ArrowStyle,
                                FancyArrowPatch, PathPatch)
from matplotlib.text import TextPath

__all__ = ['AnchoredDrawingArea', 'AnchoredAuxTransformBox',
           'AnchoredSizeBar', 'AnchoredDirectionArrows']


class AnchoredDrawingArea(AnchoredOffsetbox):
    def __init__(self, width, height, xdescent, ydescent,
                 loc, pad=0.4, borderpad=0.5, prop=None, frameon=True,
                 **kwargs):
        """
        An anchored container with a fixed size and fillable `.DrawingArea`.

        Artists added to the *drawing_area* will have their coordinates
        interpreted as pixels. Any transformations set on the artists will be
        overridden.

        Parameters
        ----------
        width, height : float
            Width and height of the container, in pixels.
        xdescent, ydescent : float
            Descent of the container in the x- and y- direction, in pixels.
        loc : str
            Location of this artist.  Valid locations are
            'upper left', 'upper center', 'upper right',
            'center left', 'center', 'center right',
            'lower left', 'lower center', 'lower right'.
            For backward compatibility, numeric values are accepted as well.
            See the parameter *loc* of `.Legend` for details.
        pad : float, default: 0.4
            Padding around the child objects, in fraction of the font size.
        borderpad : float, default: 0.5
            Border padding, in fraction of the font size.
        prop : `~matplotlib.font_manager.FontProperties`, optional
            Font property used as a reference for paddings.
        frameon : bool, default: True
            If True, draw a box around this artist.
        **kwargs
            Keyword arguments forwarded to `.AnchoredOffsetbox`.

        Attributes
        ----------
        drawing_area : `~matplotlib.offsetbox.DrawingArea`
            A container for artists to display.

        Examples
        --------
        To display blue and red circles of different sizes in the upper right
        of an Axes *ax*:

        >>> ada = AnchoredDrawingArea(20, 20, 0, 0,
        ...                           loc='upper right', frameon=False)
        >>> ada.drawing_area.add_artist(Circle((10, 10), 10, fc="b"))
        >>> ada.drawing_area.add_artist(Circle((30, 10), 5, fc="r"))
        >>> ax.add_artist(ada)
        """
        self.da = DrawingArea(width, height, xdescent, ydescent)
        self.drawing_area = self.da

        super().__init__(
            loc, pad=pad, borderpad=borderpad, child=self.da, prop=None,
            frameon=frameon, **kwargs
        )


class AnchoredAuxTransformBox(AnchoredOffsetbox):
    def __init__(self, transform, loc,
                 pad=0.4, borderpad=0.5, prop=None, frameon=True, **kwargs):
        """
        An anchored container with transformed coordinates.

        Artists added to the *drawing_area* are scaled according to the
        coordinates of the transformation used. The dimensions of this artist
        will scale to contain the artists added.

        Parameters
        ----------
        transform : `~matplotlib.transforms.Transform`
            The transformation object for the coordinate system in use, i.e.,
            :attr:`matplotlib.axes.Axes.transData`.
        loc : str
            Location of this artist.  Valid locations are
            'upper left', 'upper center', 'upper right',
            'center left', 'center', 'center right',
            'lower left', 'lower center', 'lower right'.
            For backward compatibility, numeric values are accepted as well.
            See the parameter *loc* of `.Legend` for details.
        pad : float, default: 0.4
            Padding around the child objects, in fraction of the font size.
        borderpad : float, default: 0.5
            Border padding, in fraction of the font size.
        prop : `~matplotlib.font_manager.FontProperties`, optional
            Font property used as a reference for paddings.
        frameon : bool, default: True
            If True, draw a box around this artist.
        **kwargs
            Keyword arguments forwarded to `.AnchoredOffsetbox`.

        Attributes
        ----------
        drawing_area : `~matplotlib.offsetbox.AuxTransformBox`
            A container for artists to display.

        Examples
        --------
        To display an ellipse in the upper left, with a width of 0.1 and
        height of 0.4 in data coordinates:

        >>> box = AnchoredAuxTransformBox(ax.transData, loc='upper left')
        >>> el = Ellipse((0, 0), width=0.1, height=0.4, angle=30)
        >>> box.drawing_area.add_artist(el)
        >>> ax.add_artist(box)
        """
        self.drawing_area = AuxTransformBox(transform)

        super().__init__(loc, pad=pad, borderpad=borderpad,
                         child=self.drawing_area, prop=prop, frameon=frameon,
                         **kwargs)


class AnchoredSizeBar(AnchoredOffsetbox):
    def __init__(self, transform, size, label, loc,
                 pad=0.1, borderpad=0.1, sep=2,
                 frameon=True, size_vertical=0, color='black',
                 label_top=False, fontproperties=None, fill_bar=None,
                 **kwargs):
        """
        Draw a horizontal scale bar with a center-aligned label underneath.

        Parameters
        ----------
        transform : `~matplotlib.transforms.Transform`
            The transformation object for the coordinate system in use, i.e.,
            :attr:`matplotlib.axes.Axes.transData`.
        size : float
            Horizontal length of the size bar, given in coordinates of
            *transform*.
        label : str
            Label to display.
        loc : str
            Location of the size bar.  Valid locations are
            'upper left', 'upper center', 'upper right',
            'center left', 'center', 'center right',
            'lower left', 'lower center', 'lower right'.
            For backward compatibility, numeric values are accepted as well.
            See the parameter *loc* of `.Legend` for details.
        pad : float, default: 0.1
            Padding around the label and size bar, in fraction of the font
            size.
        borderpad : float, default: 0.1
            Border padding, in fraction of the font size.
        sep : float, default: 2
            Separation between the label and the size bar, in points.
        frameon : bool, default: True
            If True, draw a box around the horizontal bar and label.
        size_vertical : float, default: 0
            Vertical length of the size bar, given in coordinates of
            *transform*.
        color : str, default: 'black'
            Color for the size bar and label.
        label_top : bool, default: False
            If True, the label will be over the size bar.
        fontproperties : `~matplotlib.font_manager.FontProperties`, optional
            Font properties for the label text.
        fill_bar : bool, optional
            If True and if *size_vertical* is nonzero, the size bar will
            be filled in with the color specified by the size bar.
            Defaults to True if *size_vertical* is greater than
            zero and False otherwise.
        **kwargs
            Keyword arguments forwarded to `.AnchoredOffsetbox`.

        Attributes
        ----------
        size_bar : `~matplotlib.offsetbox.AuxTransformBox`
            Container for the size bar.
        txt_label : `~matplotlib.offsetbox.TextArea`
            Container for the label of the size bar.

        Notes
        -----
        If *prop* is passed as a keyword argument, but *fontproperties* is
        not, then *prop* is assumed to be the intended *fontproperties*.
        Using both *prop* and *fontproperties* is not supported.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> from mpl_toolkits.axes_grid1.anchored_artists import (
        ...     AnchoredSizeBar)
        >>> fig, ax = plt.subplots()
        >>> ax.imshow(np.random.random((10, 10)))
        >>> bar = AnchoredSizeBar(ax.transData, 3, '3 data units', 4)
        >>> ax.add_artist(bar)
        >>> fig.show()

        Using all the optional parameters

        >>> import matplotlib.font_manager as fm
        >>> fontprops = fm.FontProperties(size=14, family='monospace')
        >>> bar = AnchoredSizeBar(ax.transData, 3, '3 units', 4, pad=0.5,
        ...                       sep=5, borderpad=0.5, frameon=False,
        ...                       size_vertical=0.5, color='white',
        ...                       fontproperties=fontprops)
        """
        if fill_bar is None:
            fill_bar = size_vertical > 0

        self.size_bar = AuxTransformBox(transform)
        self.size_bar.add_artist(Rectangle((0, 0), size, size_vertical,
                                           fill=fill_bar, facecolor=color,
                                           edgecolor=color))

        if fontproperties is None and 'prop' in kwargs:
            fontproperties = kwargs.pop('prop')

        if fontproperties is None:
            textprops = {'color': color}
        else:
            textprops = {'color': color, 'fontproperties': fontproperties}

        self.txt_label = TextArea(label, textprops=textprops)

        if label_top:
            _box_children = [self.txt_label, self.size_bar]
        else:
            _box_children = [self.size_bar, self.txt_label]

        self._box = VPacker(children=_box_children,
                            align="center",
                            pad=0, sep=sep)

        super().__init__(loc, pad=pad, borderpad=borderpad, child=self._box,
                         prop=fontproperties, frameon=frameon, **kwargs)


class AnchoredDirectionArrows(AnchoredOffsetbox):
    def __init__(self, transform, label_x, label_y, length=0.15,
                 fontsize=0.08, loc='upper left', angle=0, aspect_ratio=1,
                 pad=0.4, borderpad=0.4, frameon=False, color='w', alpha=1,
                 sep_x=0.01, sep_y=0, fontproperties=None, back_length=0.15,
                 head_width=10, head_length=15, tail_width=2,
                 text_props=None, arrow_props=None,
                 **kwargs):
        """
        Draw two perpendicular arrows to indicate directions.

        Parameters
        ----------
        transform : `~matplotlib.transforms.Transform`
            The transformation object for the coordinate system in use, i.e.,
            :attr:`matplotlib.axes.Axes.transAxes`.
        label_x, label_y : str
            Label text for the x and y arrows
        length : float, default: 0.15
            Length of the arrow, given in coordinates of *transform*.
        fontsize : float, default: 0.08
            Size of label strings, given in coordinates of *transform*.
        loc : str, default: 'upper left'
            Location of the arrow.  Valid locations are
            'upper left', 'upper center', 'upper right',
            'center left', 'center', 'center right',
            'lower left', 'lower center', 'lower right'.
            For backward compatibility, numeric values are accepted as well.
            See the parameter *loc* of `.Legend` for details.
        angle : float, default: 0
            The angle of the arrows in degrees.
        aspect_ratio : float, default: 1
            The ratio of the length of arrow_x and arrow_y.
            Negative numbers can be used to change the direction.
        pad : float, default: 0.4
            Padding around the labels and arrows, in fraction of the font size.
        borderpad : float, default: 0.4
            Border padding, in fraction of the font size.
        frameon : bool, default: False
            If True, draw a box around the arrows and labels.
        color : str, default: 'white'
            Color for the arrows and labels.
        alpha : float, default: 1
            Alpha values of the arrows and labels
        sep_x, sep_y : float, default: 0.01 and 0 respectively
            Separation between the arrows and labels in coordinates of
            *transform*.
        fontproperties : `~matplotlib.font_manager.FontProperties`, optional
            Font properties for the label text.
        back_length : float, default: 0.15
            Fraction of the arrow behind the arrow crossing.
        head_width : float, default: 10
            Width of arrow head, sent to `.ArrowStyle`.
        head_length : float, default: 15
            Length of arrow head, sent to `.ArrowStyle`.
        tail_width : float, default: 2
            Width of arrow tail, sent to `.ArrowStyle`.
        text_props, arrow_props : dict
            Properties of the text and arrows, passed to `.TextPath` and
            `.FancyArrowPatch`.
        **kwargs
            Keyword arguments forwarded to `.AnchoredOffsetbox`.

        Attributes
        ----------
        arrow_x, arrow_y : `~matplotlib.patches.FancyArrowPatch`
            Arrow x and y
        text_path_x, text_path_y : `~matplotlib.text.TextPath`
            Path for arrow labels
        p_x, p_y : `~matplotlib.patches.PathPatch`
            Patch for arrow labels
        box : `~matplotlib.offsetbox.AuxTransformBox`
            Container for the arrows and labels.

        Notes
        -----
        If *prop* is passed as a keyword argument, but *fontproperties* is
        not, then *prop* is assumed to be the intended *fontproperties*.
        Using both *prop* and *fontproperties* is not supported.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> from mpl_toolkits.axes_grid1.anchored_artists import (
        ...     AnchoredDirectionArrows)
        >>> fig, ax = plt.subplots()
        >>> ax.imshow(np.random.random((10, 10)))
        >>> arrows = AnchoredDirectionArrows(ax.transAxes, '111', '110')
        >>> ax.add_artist(arrows)
        >>> fig.show()

        Using several of the optional parameters, creating downward pointing
        arrow and high contrast text labels.

        >>> import matplotlib.font_manager as fm
        >>> fontprops = fm.FontProperties(family='monospace')
        >>> arrows = AnchoredDirectionArrows(ax.transAxes, 'East', 'South',
        ...                                  loc='lower left', color='k',
        ...                                  aspect_ratio=-1, sep_x=0.02,
        ...                                  sep_y=-0.01,
        ...                                  text_props={'ec':'w', 'fc':'k'},
        ...                                  fontproperties=fontprops)
        """
        if arrow_props is None:
            arrow_props = {}

        if text_props is None:
            text_props = {}

        arrowstyle = ArrowStyle("Simple",
                                head_width=head_width,
                                head_length=head_length,
                                tail_width=tail_width)

        if fontproperties is None and 'prop' in kwargs:
            fontproperties = kwargs.pop('prop')

        if 'color' not in arrow_props:
            arrow_props['color'] = color

        if 'alpha' not in arrow_props:
            arrow_props['alpha'] = alpha

        if 'color' not in text_props:
            text_props['color'] = color

        if 'alpha' not in text_props:
            text_props['alpha'] = alpha

        t_start = transform
        t_end = t_start + transforms.Affine2D().rotate_deg(angle)

        self.box = AuxTransformBox(t_end)

        length_x = length
        length_y = length*aspect_ratio

        self.arrow_x = FancyArrowPatch(
                (0, back_length*length_y),
                (length_x, back_length*length_y),
                arrowstyle=arrowstyle,
                shrinkA=0.0,
                shrinkB=0.0,
                **arrow_props)

        self.arrow_y = FancyArrowPatch(
                (back_length*length_x, 0),
                (back_length*length_x, length_y),
                arrowstyle=arrowstyle,
                shrinkA=0.0,
                shrinkB=0.0,
                **arrow_props)

        self.box.add_artist(self.arrow_x)
        self.box.add_artist(self.arrow_y)

        text_path_x = TextPath((
            length_x+sep_x, back_length*length_y+sep_y), label_x,
            size=fontsize, prop=fontproperties)
        self.p_x = PathPatch(text_path_x, transform=t_start, **text_props)
        self.box.add_artist(self.p_x)

        text_path_y = TextPath((
            length_x*back_length+sep_x, length_y*(1-back_length)+sep_y),
            label_y, size=fontsize, prop=fontproperties)
        self.p_y = PathPatch(text_path_y, **text_props)
        self.box.add_artist(self.p_y)

        super().__init__(loc, pad=pad, borderpad=borderpad, child=self.box,
                         frameon=frameon, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\c_cpp.py ===
"""
    pygments.lexers.c_cpp
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for C/C++ languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, \
    this, inherit, default, words
from pygments.util import get_bool_opt
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['CLexer', 'CppLexer']


class CFamilyLexer(RegexLexer):
    """
    For C family source code.  This is used as a base class to avoid repetitious
    definitions.
    """

    # The trailing ?, rather than *, avoids a geometric performance drop here.
    #: only one /* */ style comment
    _ws1 = r'\s*(?:/[*].*?[*]/\s*)?'

    # Hexadecimal part in an hexadecimal integer/floating-point literal.
    # This includes decimal separators matching.
    _hexpart = r'[0-9a-fA-F](\'?[0-9a-fA-F])*'
    # Decimal part in an decimal integer/floating-point literal.
    # This includes decimal separators matching.
    _decpart = r'\d(\'?\d)*'
    # Integer literal suffix (e.g. 'ull' or 'll').
    _intsuffix = r'(([uU][lL]{0,2})|[lL]{1,2}[uU]?)?'

    # Identifier regex with C and C++ Universal Character Name (UCN) support.
    _ident = r'(?!\d)(?:[\w$]|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8})+'
    _namespaced_ident = r'(?!\d)(?:[\w$]|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|::)+'

    # Single and multiline comment regexes
    # Beware not to use *? for the inner content! When these regexes
    # are embedded in larger regexes, that can cause the stuff*? to
    # match more than it would have if the regex had been used in
    # a standalone way ...
    _comment_single = r'//(?:.|(?<=\\)\n)*\n'
    _comment_multiline = r'/(?:\\\n)?[*](?:[^*]|[*](?!(?:\\\n)?/))*[*](?:\\\n)?/'

    # Regex to match optional comments
    _possible_comments = rf'\s*(?:(?:(?:{_comment_single})|(?:{_comment_multiline}))\s*)*'

    tokens = {
        'whitespace': [
            # preprocessor directives: without whitespace
            (r'^#if\s+0', Comment.Preproc, 'if0'),
            ('^#', Comment.Preproc, 'macro'),
            # or with whitespace
            ('^(' + _ws1 + r')(#if\s+0)',
             bygroups(using(this), Comment.Preproc), 'if0'),
            ('^(' + _ws1 + ')(#)',
             bygroups(using(this), Comment.Preproc), 'macro'),
            # Labels:
            # Line start and possible indentation.
            (r'(^[ \t]*)'
             # Not followed by keywords which can be mistaken as labels.
             r'(?!(?:public|private|protected|default)\b)'
             # Actual label, followed by a single colon.
             r'(' + _ident + r')(\s*)(:)(?!:)',
             bygroups(Whitespace, Name.Label, Whitespace, Punctuation)),
            (r'\n', Whitespace),
            (r'[^\S\n]+', Whitespace),
            (r'\\\n', Text),  # line continuation
            (_comment_single, Comment.Single),
            (_comment_multiline, Comment.Multiline),
            # Open until EOF, so no ending delimiter
            (r'/(\\\n)?[*][\w\W]*', Comment.Multiline),
        ],
        'statements': [
            include('keywords'),
            include('types'),
            (r'([LuU]|u8)?(")', bygroups(String.Affix, String), 'string'),
            (r"([LuU]|u8)?(')(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])(')",
             bygroups(String.Affix, String.Char, String.Char, String.Char)),

             # Hexadecimal floating-point literals (C11, C++17)
            (r'0[xX](' + _hexpart + r'\.' + _hexpart + r'|\.' + _hexpart +
             r'|' + _hexpart + r')[pP][+-]?' + _hexpart + r'[lL]?', Number.Float),

            (r'(-)?(' + _decpart + r'\.' + _decpart + r'|\.' + _decpart + r'|' +
             _decpart + r')[eE][+-]?' + _decpart + r'[fFlL]?', Number.Float),
            (r'(-)?((' + _decpart + r'\.(' + _decpart + r')?|\.' +
             _decpart + r')[fFlL]?)|(' + _decpart + r'[fFlL])', Number.Float),
            (r'(-)?0[xX]' + _hexpart + _intsuffix, Number.Hex),
            (r'(-)?0[bB][01](\'?[01])*' + _intsuffix, Number.Bin),
            (r'(-)?0(\'?[0-7])+' + _intsuffix, Number.Oct),
            (r'(-)?' + _decpart + _intsuffix, Number.Integer),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.]', Punctuation),
            (r'(true|false|NULL)\b', Name.Builtin),
            (_ident, Name)
        ],
        'types': [
            (words(('int8', 'int16', 'int32', 'int64', 'wchar_t'), prefix=r'__',
                    suffix=r'\b'), Keyword.Reserved),
            (words(('bool', 'int', 'long', 'float', 'short', 'double', 'char',
                    'unsigned', 'signed', 'void', '_BitInt',
                    '__int128'), suffix=r'\b'), Keyword.Type)
        ],
        'keywords': [
            (r'(struct|union)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'case\b', Keyword, 'case-value'),
            (words(('asm', 'auto', 'break', 'const', 'continue', 'default',
                    'do', 'else', 'enum', 'extern', 'for', 'goto', 'if',
                    'register', 'restricted', 'return', 'sizeof', 'struct',
                    'static', 'switch', 'typedef', 'volatile', 'while', 'union',
                    'thread_local', 'alignas', 'alignof', 'static_assert', '_Pragma'),
                   suffix=r'\b'), Keyword),
            (words(('inline', '_inline', '__inline', 'naked', 'restrict',
                    'thread'), suffix=r'\b'), Keyword.Reserved),
            # Vector intrinsics
            (r'(__m(128i|128d|128|64))\b', Keyword.Reserved),
            # Microsoft-isms
            (words((
                'asm', 'based', 'except', 'stdcall', 'cdecl',
                'fastcall', 'declspec', 'finally', 'try',
                'leave', 'w64', 'unaligned', 'raise', 'noop',
                'identifier', 'forceinline', 'assume'),
                prefix=r'__', suffix=r'\b'), Keyword.Reserved)
        ],
        'root': [
            include('whitespace'),
            include('keywords'),
            # functions
            (r'(' + _namespaced_ident + r'(?:[&*\s])+)'  # return arguments
             r'(' + _possible_comments + r')'
             r'(' + _namespaced_ident + r')'             # method name
             r'(' + _possible_comments + r')'
             r'(\([^;"\')]*?\))'                         # signature
             r'(' + _possible_comments + r')'
             r'([^;{/"\']*)(\{)',
             bygroups(using(this), using(this, state='whitespace'),
                      Name.Function, using(this, state='whitespace'),
                      using(this), using(this, state='whitespace'),
                      using(this), Punctuation),
             'function'),
            # function declarations
            (r'(' + _namespaced_ident + r'(?:[&*\s])+)'  # return arguments
             r'(' + _possible_comments + r')'
             r'(' + _namespaced_ident + r')'             # method name
             r'(' + _possible_comments + r')'
             r'(\([^;"\')]*?\))'                         # signature
             r'(' + _possible_comments + r')'
             r'([^;/"\']*)(;)',
             bygroups(using(this), using(this, state='whitespace'),
                      Name.Function, using(this, state='whitespace'),
                      using(this), using(this, state='whitespace'),
                      using(this), Punctuation)),
            include('types'),
            default('statement'),
        ],
        'statement': [
            include('whitespace'),
            include('statements'),
            (r'\}', Punctuation),
            (r'[{;]', Punctuation, '#pop'),
        ],
        'function': [
            include('whitespace'),
            include('statements'),
            (';', Punctuation),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|'
             r'u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'('+_ws1+r')(include)('+_ws1+r')("[^"]+")([^\n]*)',
                bygroups(using(this), Comment.Preproc, using(this),
                         Comment.PreprocFile, Comment.Single)),
            (r'('+_ws1+r')(include)('+_ws1+r')(<[^>]+>)([^\n]*)',
                bygroups(using(this), Comment.Preproc, using(this),
                         Comment.PreprocFile, Comment.Single)),
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#el(?:se|if).*\n', Comment.Preproc, '#pop'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ],
        'classname': [
            (_ident, Name.Class, '#pop'),
            # template specification
            (r'\s*(?=>)', Text, '#pop'),
            default('#pop')
        ],
        # Mark identifiers preceded by `case` keyword as constants.
        'case-value': [
            (r'(?<!:)(:)(?!:)', Punctuation, '#pop'),
            (_ident, Name.Constant),
            include('whitespace'),
            include('statements'),
        ]
    }

    stdlib_types = {
        'size_t', 'ssize_t', 'off_t', 'wchar_t', 'ptrdiff_t', 'sig_atomic_t', 'fpos_t',
        'clock_t', 'time_t', 'va_list', 'jmp_buf', 'FILE', 'DIR', 'div_t', 'ldiv_t',
        'mbstate_t', 'wctrans_t', 'wint_t', 'wctype_t'}
    c99_types = {
        'int8_t', 'int16_t', 'int32_t', 'int64_t', 'uint8_t',
        'uint16_t', 'uint32_t', 'uint64_t', 'int_least8_t', 'int_least16_t',
        'int_least32_t', 'int_least64_t', 'uint_least8_t', 'uint_least16_t',
        'uint_least32_t', 'uint_least64_t', 'int_fast8_t', 'int_fast16_t', 'int_fast32_t',
        'int_fast64_t', 'uint_fast8_t', 'uint_fast16_t', 'uint_fast32_t', 'uint_fast64_t',
        'intptr_t', 'uintptr_t', 'intmax_t', 'uintmax_t'}
    linux_types = {
        'clockid_t', 'cpu_set_t', 'cpumask_t', 'dev_t', 'gid_t', 'id_t', 'ino_t', 'key_t',
        'mode_t', 'nfds_t', 'pid_t', 'rlim_t', 'sig_t', 'sighandler_t', 'siginfo_t',
        'sigset_t', 'sigval_t', 'socklen_t', 'timer_t', 'uid_t'}
    c11_atomic_types = {
        'atomic_bool', 'atomic_char', 'atomic_schar', 'atomic_uchar', 'atomic_short',
        'atomic_ushort', 'atomic_int', 'atomic_uint', 'atomic_long', 'atomic_ulong',
        'atomic_llong', 'atomic_ullong', 'atomic_char16_t', 'atomic_char32_t', 'atomic_wchar_t',
        'atomic_int_least8_t', 'atomic_uint_least8_t', 'atomic_int_least16_t',
        'atomic_uint_least16_t', 'atomic_int_least32_t', 'atomic_uint_least32_t',
        'atomic_int_least64_t', 'atomic_uint_least64_t', 'atomic_int_fast8_t',
        'atomic_uint_fast8_t', 'atomic_int_fast16_t', 'atomic_uint_fast16_t',
        'atomic_int_fast32_t', 'atomic_uint_fast32_t', 'atomic_int_fast64_t',
        'atomic_uint_fast64_t', 'atomic_intptr_t', 'atomic_uintptr_t', 'atomic_size_t',
        'atomic_ptrdiff_t', 'atomic_intmax_t', 'atomic_uintmax_t'}

    def __init__(self, **options):
        self.stdlibhighlighting = get_bool_opt(options, 'stdlibhighlighting', True)
        self.c99highlighting = get_bool_opt(options, 'c99highlighting', True)
        self.c11highlighting = get_bool_opt(options, 'c11highlighting', True)
        self.platformhighlighting = get_bool_opt(options, 'platformhighlighting', True)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text, stack=('root',)):
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name:
                if self.stdlibhighlighting and value in self.stdlib_types:
                    token = Keyword.Type
                elif self.c99highlighting and value in self.c99_types:
                    token = Keyword.Type
                elif self.c11highlighting and value in self.c11_atomic_types:
                    token = Keyword.Type
                elif self.platformhighlighting and value in self.linux_types:
                    token = Keyword.Type
            yield index, token, value


class CLexer(CFamilyLexer):
    """
    For C source code with preprocessor directives.

    Additional options accepted:

    `stdlibhighlighting`
        Highlight common types found in the C/C++ standard library (e.g. `size_t`).
        (default: ``True``).

    `c99highlighting`
        Highlight common types found in the C99 standard library (e.g. `int8_t`).
        Actually, this includes all fixed-width integer types.
        (default: ``True``).

    `c11highlighting`
        Highlight atomic types found in the C11 standard library (e.g. `atomic_bool`).
        (default: ``True``).

    `platformhighlighting`
        Highlight common types found in the platform SDK headers (e.g. `clockid_t` on Linux).
        (default: ``True``).
    """
    name = 'C'
    aliases = ['c']
    filenames = ['*.c', '*.h', '*.idc', '*.x[bp]m']
    mimetypes = ['text/x-chdr', 'text/x-csrc', 'image/x-xbitmap', 'image/x-xpixmap']
    url = 'https://en.wikipedia.org/wiki/C_(programming_language)'
    version_added = ''
    priority = 0.1

    tokens = {
        'keywords': [
            (words((
                '_Alignas', '_Alignof', '_Noreturn', '_Generic', '_Thread_local',
                '_Static_assert', '_Imaginary', 'noreturn', 'imaginary', 'complex'),
                suffix=r'\b'), Keyword),
            inherit
        ],
        'types': [
            (words(('_Bool', '_Complex', '_Atomic'), suffix=r'\b'), Keyword.Type),
            inherit
        ]
    }

    def analyse_text(text):
        if re.search(r'^\s*#include [<"]', text, re.MULTILINE):
            return 0.1
        if re.search(r'^\s*#ifn?def ', text, re.MULTILINE):
            return 0.1


class CppLexer(CFamilyLexer):
    """
    For C++ source code with preprocessor directives.

    Additional options accepted:

    `stdlibhighlighting`
        Highlight common types found in the C/C++ standard library (e.g. `size_t`).
        (default: ``True``).

    `c99highlighting`
        Highlight common types found in the C99 standard library (e.g. `int8_t`).
        Actually, this includes all fixed-width integer types.
        (default: ``True``).

    `c11highlighting`
        Highlight atomic types found in the C11 standard library (e.g. `atomic_bool`).
        (default: ``True``).

    `platformhighlighting`
        Highlight common types found in the platform SDK headers (e.g. `clockid_t` on Linux).
        (default: ``True``).
    """
    name = 'C++'
    url = 'https://isocpp.org/'
    aliases = ['cpp', 'c++']
    filenames = ['*.cpp', '*.hpp', '*.c++', '*.h++',
                 '*.cc', '*.hh', '*.cxx', '*.hxx',
                 '*.C', '*.H', '*.cp', '*.CPP', '*.tpp']
    mimetypes = ['text/x-c++hdr', 'text/x-c++src']
    version_added = ''
    priority = 0.1

    tokens = {
        'statements': [
            # C++11 raw strings
            (r'((?:[LuU]|u8)?R)(")([^\\()\s]{,16})(\()((?:.|\n)*?)(\)\3)(")',
             bygroups(String.Affix, String, String.Delimiter, String.Delimiter,
                      String, String.Delimiter, String)),
            inherit,
        ],
        'root': [
            inherit,
            # C++ Microsoft-isms
            (words(('virtual_inheritance', 'uuidof', 'super', 'single_inheritance',
                    'multiple_inheritance', 'interface', 'event'),
                   prefix=r'__', suffix=r'\b'), Keyword.Reserved),
            # Offload C++ extensions, http://offload.codeplay.com/
            (r'__(offload|blockingoffload|outer)\b', Keyword.Pseudo),
        ],
        'enumname': [
            include('whitespace'),
            # 'enum class' and 'enum struct' C++11 support
            (words(('class', 'struct'), suffix=r'\b'), Keyword),
            (CFamilyLexer._ident, Name.Class, '#pop'),
            # template specification
            (r'\s*(?=>)', Text, '#pop'),
            default('#pop')
        ],
        'keywords': [
            (r'(class|concept|typename)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            (words((
                'catch', 'const_cast', 'delete', 'dynamic_cast', 'explicit',
                'export', 'friend', 'mutable', 'new', 'operator',
                'private', 'protected', 'public', 'reinterpret_cast', 'class',
                '__restrict', 'static_cast', 'template', 'this', 'throw', 'throws',
                'try', 'typeid', 'using', 'virtual', 'constexpr', 'nullptr', 'concept',
                'decltype', 'noexcept', 'override', 'final', 'constinit', 'consteval',
                'co_await', 'co_return', 'co_yield', 'requires', 'import', 'module',
                'typename', 'and', 'and_eq', 'bitand', 'bitor', 'compl', 'not',
                'not_eq', 'or', 'or_eq', 'xor', 'xor_eq'),
               suffix=r'\b'), Keyword),
            (r'namespace\b', Keyword, 'namespace'),
            (r'(enum)(\s+)', bygroups(Keyword, Whitespace), 'enumname'),
            inherit
        ],
        'types': [
            (r'char(16_t|32_t|8_t)\b', Keyword.Type),
            inherit
        ],
        'namespace': [
            (r'[;{]', Punctuation, ('#pop', 'root')),
            (r'inline\b', Keyword.Reserved),
            (CFamilyLexer._ident, Name.Namespace),
            include('statement')
        ]
    }

    def analyse_text(text):
        if re.search('#include <[a-z_]+>', text):
            return 0.2
        if re.search('using namespace ', text):
            return 0.4

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\service_worker.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: ServiceWorker (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


class RegistrationID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RegistrationID:
        return cls(json)

    def __repr__(self):
        return 'RegistrationID({})'.format(super().__repr__())


@dataclass
class ServiceWorkerRegistration:
    '''
    ServiceWorker registration.
    '''
    registration_id: RegistrationID

    scope_url: str

    is_deleted: bool

    def to_json(self):
        json = dict()
        json['registrationId'] = self.registration_id.to_json()
        json['scopeURL'] = self.scope_url
        json['isDeleted'] = self.is_deleted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            registration_id=RegistrationID.from_json(json['registrationId']),
            scope_url=str(json['scopeURL']),
            is_deleted=bool(json['isDeleted']),
        )


class ServiceWorkerVersionRunningStatus(enum.Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ServiceWorkerVersionStatus(enum.Enum):
    NEW = "new"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    REDUNDANT = "redundant"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ServiceWorkerVersion:
    '''
    ServiceWorker version.
    '''
    version_id: str

    registration_id: RegistrationID

    script_url: str

    running_status: ServiceWorkerVersionRunningStatus

    status: ServiceWorkerVersionStatus

    #: The Last-Modified header value of the main script.
    script_last_modified: typing.Optional[float] = None

    #: The time at which the response headers of the main script were received from the server.
    #: For cached script it is the last time the cache entry was validated.
    script_response_time: typing.Optional[float] = None

    controlled_clients: typing.Optional[typing.List[target.TargetID]] = None

    target_id: typing.Optional[target.TargetID] = None

    router_rules: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['versionId'] = self.version_id
        json['registrationId'] = self.registration_id.to_json()
        json['scriptURL'] = self.script_url
        json['runningStatus'] = self.running_status.to_json()
        json['status'] = self.status.to_json()
        if self.script_last_modified is not None:
            json['scriptLastModified'] = self.script_last_modified
        if self.script_response_time is not None:
            json['scriptResponseTime'] = self.script_response_time
        if self.controlled_clients is not None:
            json['controlledClients'] = [i.to_json() for i in self.controlled_clients]
        if self.target_id is not None:
            json['targetId'] = self.target_id.to_json()
        if self.router_rules is not None:
            json['routerRules'] = self.router_rules
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            version_id=str(json['versionId']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            script_url=str(json['scriptURL']),
            running_status=ServiceWorkerVersionRunningStatus.from_json(json['runningStatus']),
            status=ServiceWorkerVersionStatus.from_json(json['status']),
            script_last_modified=float(json['scriptLastModified']) if 'scriptLastModified' in json else None,
            script_response_time=float(json['scriptResponseTime']) if 'scriptResponseTime' in json else None,
            controlled_clients=[target.TargetID.from_json(i) for i in json['controlledClients']] if 'controlledClients' in json else None,
            target_id=target.TargetID.from_json(json['targetId']) if 'targetId' in json else None,
            router_rules=str(json['routerRules']) if 'routerRules' in json else None,
        )


@dataclass
class ServiceWorkerErrorMessage:
    '''
    ServiceWorker error message.
    '''
    error_message: str

    registration_id: RegistrationID

    version_id: str

    source_url: str

    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['errorMessage'] = self.error_message
        json['registrationId'] = self.registration_id.to_json()
        json['versionId'] = self.version_id
        json['sourceURL'] = self.source_url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_message=str(json['errorMessage']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            version_id=str(json['versionId']),
            source_url=str(json['sourceURL']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


def deliver_push_message(
        origin: str,
        registration_id: RegistrationID,
        data: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param data:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['data'] = data
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.deliverPushMessage',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.disable',
    }
    json = yield cmd_dict


def dispatch_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str,
        last_chance: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    :param last_chance:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    params['lastChance'] = last_chance
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def dispatch_periodic_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchPeriodicSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.enable',
    }
    json = yield cmd_dict


def inspect_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.inspectWorker',
        'params': params,
    }
    json = yield cmd_dict


def set_force_update_on_page_load(
        force_update_on_page_load: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param force_update_on_page_load:
    '''
    params: T_JSON_DICT = dict()
    params['forceUpdateOnPageLoad'] = force_update_on_page_load
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.setForceUpdateOnPageLoad',
        'params': params,
    }
    json = yield cmd_dict


def skip_waiting(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.skipWaiting',
        'params': params,
    }
    json = yield cmd_dict


def start_worker(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.startWorker',
        'params': params,
    }
    json = yield cmd_dict


def stop_all_workers() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopAllWorkers',
    }
    json = yield cmd_dict


def stop_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopWorker',
        'params': params,
    }
    json = yield cmd_dict


def unregister(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.unregister',
        'params': params,
    }
    json = yield cmd_dict


def update_registration(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.updateRegistration',
        'params': params,
    }
    json = yield cmd_dict


@event_class('ServiceWorker.workerErrorReported')
@dataclass
class WorkerErrorReported:
    error_message: ServiceWorkerErrorMessage

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerErrorReported:
        return cls(
            error_message=ServiceWorkerErrorMessage.from_json(json['errorMessage'])
        )


@event_class('ServiceWorker.workerRegistrationUpdated')
@dataclass
class WorkerRegistrationUpdated:
    registrations: typing.List[ServiceWorkerRegistration]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerRegistrationUpdated:
        return cls(
            registrations=[ServiceWorkerRegistration.from_json(i) for i in json['registrations']]
        )


@event_class('ServiceWorker.workerVersionUpdated')
@dataclass
class WorkerVersionUpdated:
    versions: typing.List[ServiceWorkerVersion]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerVersionUpdated:
        return cls(
            versions=[ServiceWorkerVersion.from_json(i) for i in json['versions']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\service_worker.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: ServiceWorker (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


class RegistrationID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RegistrationID:
        return cls(json)

    def __repr__(self):
        return 'RegistrationID({})'.format(super().__repr__())


@dataclass
class ServiceWorkerRegistration:
    '''
    ServiceWorker registration.
    '''
    registration_id: RegistrationID

    scope_url: str

    is_deleted: bool

    def to_json(self):
        json = dict()
        json['registrationId'] = self.registration_id.to_json()
        json['scopeURL'] = self.scope_url
        json['isDeleted'] = self.is_deleted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            registration_id=RegistrationID.from_json(json['registrationId']),
            scope_url=str(json['scopeURL']),
            is_deleted=bool(json['isDeleted']),
        )


class ServiceWorkerVersionRunningStatus(enum.Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ServiceWorkerVersionStatus(enum.Enum):
    NEW = "new"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    REDUNDANT = "redundant"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ServiceWorkerVersion:
    '''
    ServiceWorker version.
    '''
    version_id: str

    registration_id: RegistrationID

    script_url: str

    running_status: ServiceWorkerVersionRunningStatus

    status: ServiceWorkerVersionStatus

    #: The Last-Modified header value of the main script.
    script_last_modified: typing.Optional[float] = None

    #: The time at which the response headers of the main script were received from the server.
    #: For cached script it is the last time the cache entry was validated.
    script_response_time: typing.Optional[float] = None

    controlled_clients: typing.Optional[typing.List[target.TargetID]] = None

    target_id: typing.Optional[target.TargetID] = None

    router_rules: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['versionId'] = self.version_id
        json['registrationId'] = self.registration_id.to_json()
        json['scriptURL'] = self.script_url
        json['runningStatus'] = self.running_status.to_json()
        json['status'] = self.status.to_json()
        if self.script_last_modified is not None:
            json['scriptLastModified'] = self.script_last_modified
        if self.script_response_time is not None:
            json['scriptResponseTime'] = self.script_response_time
        if self.controlled_clients is not None:
            json['controlledClients'] = [i.to_json() for i in self.controlled_clients]
        if self.target_id is not None:
            json['targetId'] = self.target_id.to_json()
        if self.router_rules is not None:
            json['routerRules'] = self.router_rules
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            version_id=str(json['versionId']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            script_url=str(json['scriptURL']),
            running_status=ServiceWorkerVersionRunningStatus.from_json(json['runningStatus']),
            status=ServiceWorkerVersionStatus.from_json(json['status']),
            script_last_modified=float(json['scriptLastModified']) if 'scriptLastModified' in json else None,
            script_response_time=float(json['scriptResponseTime']) if 'scriptResponseTime' in json else None,
            controlled_clients=[target.TargetID.from_json(i) for i in json['controlledClients']] if 'controlledClients' in json else None,
            target_id=target.TargetID.from_json(json['targetId']) if 'targetId' in json else None,
            router_rules=str(json['routerRules']) if 'routerRules' in json else None,
        )


@dataclass
class ServiceWorkerErrorMessage:
    '''
    ServiceWorker error message.
    '''
    error_message: str

    registration_id: RegistrationID

    version_id: str

    source_url: str

    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['errorMessage'] = self.error_message
        json['registrationId'] = self.registration_id.to_json()
        json['versionId'] = self.version_id
        json['sourceURL'] = self.source_url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_message=str(json['errorMessage']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            version_id=str(json['versionId']),
            source_url=str(json['sourceURL']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


def deliver_push_message(
        origin: str,
        registration_id: RegistrationID,
        data: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param data:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['data'] = data
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.deliverPushMessage',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.disable',
    }
    json = yield cmd_dict


def dispatch_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str,
        last_chance: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    :param last_chance:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    params['lastChance'] = last_chance
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def dispatch_periodic_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchPeriodicSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.enable',
    }
    json = yield cmd_dict


def inspect_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.inspectWorker',
        'params': params,
    }
    json = yield cmd_dict


def set_force_update_on_page_load(
        force_update_on_page_load: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param force_update_on_page_load:
    '''
    params: T_JSON_DICT = dict()
    params['forceUpdateOnPageLoad'] = force_update_on_page_load
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.setForceUpdateOnPageLoad',
        'params': params,
    }
    json = yield cmd_dict


def skip_waiting(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.skipWaiting',
        'params': params,
    }
    json = yield cmd_dict


def start_worker(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.startWorker',
        'params': params,
    }
    json = yield cmd_dict


def stop_all_workers() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopAllWorkers',
    }
    json = yield cmd_dict


def stop_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopWorker',
        'params': params,
    }
    json = yield cmd_dict


def unregister(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.unregister',
        'params': params,
    }
    json = yield cmd_dict


def update_registration(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.updateRegistration',
        'params': params,
    }
    json = yield cmd_dict


@event_class('ServiceWorker.workerErrorReported')
@dataclass
class WorkerErrorReported:
    error_message: ServiceWorkerErrorMessage

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerErrorReported:
        return cls(
            error_message=ServiceWorkerErrorMessage.from_json(json['errorMessage'])
        )


@event_class('ServiceWorker.workerRegistrationUpdated')
@dataclass
class WorkerRegistrationUpdated:
    registrations: typing.List[ServiceWorkerRegistration]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerRegistrationUpdated:
        return cls(
            registrations=[ServiceWorkerRegistration.from_json(i) for i in json['registrations']]
        )


@event_class('ServiceWorker.workerVersionUpdated')
@dataclass
class WorkerVersionUpdated:
    versions: typing.List[ServiceWorkerVersion]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerVersionUpdated:
        return cls(
            versions=[ServiceWorkerVersion.from_json(i) for i in json['versions']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\service_worker.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: ServiceWorker (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


class RegistrationID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RegistrationID:
        return cls(json)

    def __repr__(self):
        return 'RegistrationID({})'.format(super().__repr__())


@dataclass
class ServiceWorkerRegistration:
    '''
    ServiceWorker registration.
    '''
    registration_id: RegistrationID

    scope_url: str

    is_deleted: bool

    def to_json(self):
        json = dict()
        json['registrationId'] = self.registration_id.to_json()
        json['scopeURL'] = self.scope_url
        json['isDeleted'] = self.is_deleted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            registration_id=RegistrationID.from_json(json['registrationId']),
            scope_url=str(json['scopeURL']),
            is_deleted=bool(json['isDeleted']),
        )


class ServiceWorkerVersionRunningStatus(enum.Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ServiceWorkerVersionStatus(enum.Enum):
    NEW = "new"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    REDUNDANT = "redundant"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ServiceWorkerVersion:
    '''
    ServiceWorker version.
    '''
    version_id: str

    registration_id: RegistrationID

    script_url: str

    running_status: ServiceWorkerVersionRunningStatus

    status: ServiceWorkerVersionStatus

    #: The Last-Modified header value of the main script.
    script_last_modified: typing.Optional[float] = None

    #: The time at which the response headers of the main script were received from the server.
    #: For cached script it is the last time the cache entry was validated.
    script_response_time: typing.Optional[float] = None

    controlled_clients: typing.Optional[typing.List[target.TargetID]] = None

    target_id: typing.Optional[target.TargetID] = None

    router_rules: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['versionId'] = self.version_id
        json['registrationId'] = self.registration_id.to_json()
        json['scriptURL'] = self.script_url
        json['runningStatus'] = self.running_status.to_json()
        json['status'] = self.status.to_json()
        if self.script_last_modified is not None:
            json['scriptLastModified'] = self.script_last_modified
        if self.script_response_time is not None:
            json['scriptResponseTime'] = self.script_response_time
        if self.controlled_clients is not None:
            json['controlledClients'] = [i.to_json() for i in self.controlled_clients]
        if self.target_id is not None:
            json['targetId'] = self.target_id.to_json()
        if self.router_rules is not None:
            json['routerRules'] = self.router_rules
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            version_id=str(json['versionId']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            script_url=str(json['scriptURL']),
            running_status=ServiceWorkerVersionRunningStatus.from_json(json['runningStatus']),
            status=ServiceWorkerVersionStatus.from_json(json['status']),
            script_last_modified=float(json['scriptLastModified']) if 'scriptLastModified' in json else None,
            script_response_time=float(json['scriptResponseTime']) if 'scriptResponseTime' in json else None,
            controlled_clients=[target.TargetID.from_json(i) for i in json['controlledClients']] if 'controlledClients' in json else None,
            target_id=target.TargetID.from_json(json['targetId']) if 'targetId' in json else None,
            router_rules=str(json['routerRules']) if 'routerRules' in json else None,
        )


@dataclass
class ServiceWorkerErrorMessage:
    '''
    ServiceWorker error message.
    '''
    error_message: str

    registration_id: RegistrationID

    version_id: str

    source_url: str

    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['errorMessage'] = self.error_message
        json['registrationId'] = self.registration_id.to_json()
        json['versionId'] = self.version_id
        json['sourceURL'] = self.source_url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_message=str(json['errorMessage']),
            registration_id=RegistrationID.from_json(json['registrationId']),
            version_id=str(json['versionId']),
            source_url=str(json['sourceURL']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


def deliver_push_message(
        origin: str,
        registration_id: RegistrationID,
        data: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param data:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['data'] = data
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.deliverPushMessage',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.disable',
    }
    json = yield cmd_dict


def dispatch_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str,
        last_chance: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    :param last_chance:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    params['lastChance'] = last_chance
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def dispatch_periodic_sync_event(
        origin: str,
        registration_id: RegistrationID,
        tag: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param origin:
    :param registration_id:
    :param tag:
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['registrationId'] = registration_id.to_json()
    params['tag'] = tag
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.dispatchPeriodicSyncEvent',
        'params': params,
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.enable',
    }
    json = yield cmd_dict


def inspect_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.inspectWorker',
        'params': params,
    }
    json = yield cmd_dict


def set_force_update_on_page_load(
        force_update_on_page_load: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param force_update_on_page_load:
    '''
    params: T_JSON_DICT = dict()
    params['forceUpdateOnPageLoad'] = force_update_on_page_load
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.setForceUpdateOnPageLoad',
        'params': params,
    }
    json = yield cmd_dict


def skip_waiting(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.skipWaiting',
        'params': params,
    }
    json = yield cmd_dict


def start_worker(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.startWorker',
        'params': params,
    }
    json = yield cmd_dict


def stop_all_workers() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopAllWorkers',
    }
    json = yield cmd_dict


def stop_worker(
        version_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param version_id:
    '''
    params: T_JSON_DICT = dict()
    params['versionId'] = version_id
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.stopWorker',
        'params': params,
    }
    json = yield cmd_dict


def unregister(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.unregister',
        'params': params,
    }
    json = yield cmd_dict


def update_registration(
        scope_url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param scope_url:
    '''
    params: T_JSON_DICT = dict()
    params['scopeURL'] = scope_url
    cmd_dict: T_JSON_DICT = {
        'method': 'ServiceWorker.updateRegistration',
        'params': params,
    }
    json = yield cmd_dict


@event_class('ServiceWorker.workerErrorReported')
@dataclass
class WorkerErrorReported:
    error_message: ServiceWorkerErrorMessage

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerErrorReported:
        return cls(
            error_message=ServiceWorkerErrorMessage.from_json(json['errorMessage'])
        )


@event_class('ServiceWorker.workerRegistrationUpdated')
@dataclass
class WorkerRegistrationUpdated:
    registrations: typing.List[ServiceWorkerRegistration]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerRegistrationUpdated:
        return cls(
            registrations=[ServiceWorkerRegistration.from_json(i) for i in json['registrations']]
        )


@event_class('ServiceWorker.workerVersionUpdated')
@dataclass
class WorkerVersionUpdated:
    versions: typing.List[ServiceWorkerVersion]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WorkerVersionUpdated:
        return cls(
            versions=[ServiceWorkerVersion.from_json(i) for i in json['versions']]
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\tuned_model.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import timestamp_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "TunedModel",
        "TunedModelSource",
        "TuningTask",
        "Hyperparameters",
        "Dataset",
        "TuningExamples",
        "TuningExample",
        "TuningSnapshot",
    },
)


class TunedModel(proto.Message):
    r"""A fine-tuned model created using
    ModelService.CreateTunedModel.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        tuned_model_source (google.ai.generativelanguage_v1beta3.types.TunedModelSource):
            Optional. TunedModel to use as the starting
            point for training the new model.

            This field is a member of `oneof`_ ``source_model``.
        base_model (str):
            Immutable. The name of the ``Model`` to tune. Example:
            ``models/text-bison-001``

            This field is a member of `oneof`_ ``source_model``.
        name (str):
            Output only. The tuned model name. A unique name will be
            generated on create. Example: ``tunedModels/az2mb0bpw6i`` If
            display_name is set on create, the id portion of the name
            will be set by concatenating the words of the display_name
            with hyphens and adding a random portion for uniqueness.
            Example: display_name = "Sentence Translator" name =
            "tunedModels/sentence-translator-u3b7m".
        display_name (str):
            Optional. The name to display for this model
            in user interfaces. The display name must be up
            to 40 characters including spaces.
        description (str):
            Optional. A short description of this model.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. For Nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. For Top-k sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. This value specifies default to be used by the
            backend while making the call to the model.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_top_k``.
        state (google.ai.generativelanguage_v1beta3.types.TunedModel.State):
            Output only. The state of the tuned model.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this model
            was created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this model
            was updated.
        tuning_task (google.ai.generativelanguage_v1beta3.types.TuningTask):
            Required. The tuning task that creates the
            tuned model.
    """

    class State(proto.Enum):
        r"""The state of the tuned model.

        Values:
            STATE_UNSPECIFIED (0):
                The default value. This value is unused.
            CREATING (1):
                The model is being created.
            ACTIVE (2):
                The model is ready to be used.
            FAILED (3):
                The model failed to be created.
        """
        STATE_UNSPECIFIED = 0
        CREATING = 1
        ACTIVE = 2
        FAILED = 3

    tuned_model_source: "TunedModelSource" = proto.Field(
        proto.MESSAGE,
        number=3,
        oneof="source_model",
        message="TunedModelSource",
    )
    base_model: str = proto.Field(
        proto.STRING,
        number=4,
        oneof="source_model",
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=5,
    )
    description: str = proto.Field(
        proto.STRING,
        number=6,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=11,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=12,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=13,
        optional=True,
    )
    state: State = proto.Field(
        proto.ENUM,
        number=7,
        enum=State,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=8,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=9,
        message=timestamp_pb2.Timestamp,
    )
    tuning_task: "TuningTask" = proto.Field(
        proto.MESSAGE,
        number=10,
        message="TuningTask",
    )


class TunedModelSource(proto.Message):
    r"""Tuned model as a source for training a new model.

    Attributes:
        tuned_model (str):
            Immutable. The name of the ``TunedModel`` to use as the
            starting point for training the new model. Example:
            ``tunedModels/my-tuned-model``
        base_model (str):
            Output only. The name of the base ``Model`` this
            ``TunedModel`` was tuned from. Example:
            ``models/text-bison-001``
    """

    tuned_model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    base_model: str = proto.Field(
        proto.STRING,
        number=2,
    )


class TuningTask(proto.Message):
    r"""Tuning tasks that create tuned models.

    Attributes:
        start_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when tuning this
            model started.
        complete_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when tuning this
            model completed.
        snapshots (MutableSequence[google.ai.generativelanguage_v1beta3.types.TuningSnapshot]):
            Output only. Metrics collected during tuning.
        training_data (google.ai.generativelanguage_v1beta3.types.Dataset):
            Required. Input only. Immutable. The model
            training data.
        hyperparameters (google.ai.generativelanguage_v1beta3.types.Hyperparameters):
            Immutable. Hyperparameters controlling the
            tuning process. If not provided, default values
            will be used.
    """

    start_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=1,
        message=timestamp_pb2.Timestamp,
    )
    complete_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=2,
        message=timestamp_pb2.Timestamp,
    )
    snapshots: MutableSequence["TuningSnapshot"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="TuningSnapshot",
    )
    training_data: "Dataset" = proto.Field(
        proto.MESSAGE,
        number=4,
        message="Dataset",
    )
    hyperparameters: "Hyperparameters" = proto.Field(
        proto.MESSAGE,
        number=5,
        message="Hyperparameters",
    )


class Hyperparameters(proto.Message):
    r"""Hyperparameters controlling the tuning process.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        epoch_count (int):
            Immutable. The number of training epochs. An
            epoch is one pass through the training data. If
            not set, a default of 10 will be used.

            This field is a member of `oneof`_ ``_epoch_count``.
        batch_size (int):
            Immutable. The batch size hyperparameter for
            tuning. If not set, a default of 16 or 64 will
            be used based on the number of training
            examples.

            This field is a member of `oneof`_ ``_batch_size``.
        learning_rate (float):
            Immutable. The learning rate hyperparameter
            for tuning. If not set, a default of 0.0002 or
            0.002 will be calculated based on the number of
            training examples.

            This field is a member of `oneof`_ ``_learning_rate``.
    """

    epoch_count: int = proto.Field(
        proto.INT32,
        number=14,
        optional=True,
    )
    batch_size: int = proto.Field(
        proto.INT32,
        number=15,
        optional=True,
    )
    learning_rate: float = proto.Field(
        proto.FLOAT,
        number=16,
        optional=True,
    )


class Dataset(proto.Message):
    r"""Dataset for training or validation.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        examples (google.ai.generativelanguage_v1beta3.types.TuningExamples):
            Optional. Inline examples.

            This field is a member of `oneof`_ ``dataset``.
    """

    examples: "TuningExamples" = proto.Field(
        proto.MESSAGE,
        number=1,
        oneof="dataset",
        message="TuningExamples",
    )


class TuningExamples(proto.Message):
    r"""A set of tuning examples. Can be training or validatation
    data.

    Attributes:
        examples (MutableSequence[google.ai.generativelanguage_v1beta3.types.TuningExample]):
            Required. The examples. Example input can be
            for text or discuss, but all examples in a set
            must be of the same type.
    """

    examples: MutableSequence["TuningExample"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="TuningExample",
    )


class TuningExample(proto.Message):
    r"""A single example for tuning.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        text_input (str):
            Optional. Text model input.

            This field is a member of `oneof`_ ``model_input``.
        output (str):
            Required. The expected model output.
    """

    text_input: str = proto.Field(
        proto.STRING,
        number=1,
        oneof="model_input",
    )
    output: str = proto.Field(
        proto.STRING,
        number=3,
    )


class TuningSnapshot(proto.Message):
    r"""Record for a single tuning step.

    Attributes:
        step (int):
            Output only. The tuning step.
        epoch (int):
            Output only. The epoch this step was part of.
        mean_loss (float):
            Output only. The mean loss of the training
            examples for this step.
        compute_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this metric
            was computed.
    """

    step: int = proto.Field(
        proto.INT32,
        number=1,
    )
    epoch: int = proto.Field(
        proto.INT32,
        number=2,
    )
    mean_loss: float = proto.Field(
        proto.FLOAT,
        number=3,
    )
    compute_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=4,
        message=timestamp_pb2.Timestamp,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\unicon.py ===
"""
    pygments.lexers.unicon
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for the Icon and Unicon languages, including ucode VM.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words, using, this
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['IconLexer', 'UcodeLexer', 'UniconLexer']


class UniconLexer(RegexLexer):
    """
    For Unicon source code.
    """

    name = 'Unicon'
    aliases = ['unicon']
    filenames = ['*.icn']
    mimetypes = ['text/unicon']
    url = 'https://www.unicon.org'
    version_added = '2.4'

    flags = re.MULTILINE

    tokens = {
        'root': [
            (r'[^\S\n]+', Text),
            (r'#.*?\n', Comment.Single),
            (r'[^\S\n]+', Text),
            (r'class|method|procedure', Keyword.Declaration, 'subprogram'),
            (r'(record)(\s+)(\w+)',
             bygroups(Keyword.Declaration, Text, Keyword.Type), 'type_def'),
            (r'(#line|\$C|\$Cend|\$define|\$else|\$endif|\$error|\$ifdef|'
             r'\$ifndef|\$include|\$line|\$undef)\b', Keyword.PreProc),
            (r'(&null|&fail)\b', Keyword.Constant),
            (r'&allocated|&ascii|&clock|&collections|&column|&col|&control|'
             r'&cset|&current|&dateline|&date|&digits|&dump|'
             r'&errno|&errornumber|&errortext|&errorvalue|&error|&errout|'
             r'&eventcode|&eventvalue|&eventsource|&e|'
             r'&features|&file|&host|&input|&interval|&lcase|&letters|'
             r'&level|&line|&ldrag|&lpress|&lrelease|'
             r'&main|&mdrag|&meta|&mpress|&mrelease|&now|&output|'
             r'&phi|&pick|&pi|&pos|&progname|'
             r'&random|&rdrag|&regions|&resize|&row|&rpress|&rrelease|'
             r'&shift|&source|&storage|&subject|'
             r'&time|&trace|&ucase|&version|'
             r'&window|&x|&y', Keyword.Reserved),
            (r'(by|of|not|to)\b', Keyword.Reserved),
            (r'(global|local|static|abstract)\b', Keyword.Reserved),
            (r'package|link|import', Keyword.Declaration),
            (words((
                'break', 'case', 'create', 'critical', 'default', 'end', 'all',
                'do', 'else', 'every', 'fail', 'if', 'import', 'initial',
                'initially', 'invocable', 'next',
                'repeat', 'return', 'suspend',
                'then', 'thread', 'until', 'while'), prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
            (words((
                'Abort', 'abs', 'acos', 'Active', 'Alert', 'any', 'Any', 'Arb',
                'Arbno', 'args', 'array', 'asin', 'atan', 'atanh', 'Attrib',
                'Bal', 'bal', 'Bg', 'Break', 'Breakx',
                'callout', 'center', 'char', 'chdir', 'chmod', 'chown', 'chroot',
                'classname', 'Clip', 'Clone', 'close', 'cofail', 'collect',
                'Color', 'ColorValue', 'condvar', 'constructor', 'copy',
                'CopyArea', 'cos', 'Couple', 'crypt', 'cset', 'ctime',
                'dbcolumns', 'dbdriver', 'dbkeys', 'dblimits', 'dbproduct',
                'dbtables', 'delay', 'delete', 'detab', 'display', 'DrawArc',
                'DrawCircle', 'DrawCube', 'DrawCurve', 'DrawCylinder',
                'DrawDisk', 'DrawImage', 'DrawLine', 'DrawPoint', 'DrawPolygon',
                'DrawRectangle', 'DrawSegment', 'DrawSphere', 'DrawString',
                'DrawTorus', 'dtor',
                'entab', 'EraseArea', 'errorclear', 'Event', 'eventmask',
                'EvGet', 'EvSend', 'exec', 'exit', 'exp', 'Eye',
                'Fail', 'fcntl', 'fdup', 'Fence', 'fetch', 'Fg', 'fieldnames',
                'filepair', 'FillArc', 'FillCircle', 'FillPolygon',
                'FillRectangle', 'find', 'flock', 'flush', 'Font', 'fork',
                'FreeColor', 'FreeSpace', 'function',
                'get', 'getch', 'getche', 'getegid', 'getenv', 'geteuid',
                'getgid', 'getgr', 'gethost', 'getpgrp', 'getpid', 'getppid',
                'getpw', 'getrusage', 'getserv', 'GetSpace', 'gettimeofday',
                'getuid', 'globalnames', 'GotoRC', 'GotoXY', 'gtime', 'hardlink',
                'iand', 'icom', 'IdentityMatrix', 'image', 'InPort', 'insert',
                'Int86', 'integer', 'ioctl', 'ior', 'ishift', 'istate', 'ixor',
                'kbhit', 'key', 'keyword', 'kill',
                'left', 'Len', 'list', 'load', 'loadfunc', 'localnames',
                'lock', 'log', 'Lower', 'lstat',
                'many', 'map', 'match', 'MatrixMode', 'max', 'member',
                'membernames', 'methodnames', 'methods', 'min', 'mkdir', 'move',
                'MultMatrix', 'mutex',
                'name', 'NewColor', 'Normals', 'NotAny', 'numeric',
                'open', 'opencl', 'oprec', 'ord', 'OutPort',
                'PaletteChars', 'PaletteColor', 'PaletteKey', 'paramnames',
                'parent', 'Pattern', 'Peek', 'Pending', 'pipe', 'Pixel',
                'PlayAudio', 'Poke', 'pop', 'PopMatrix', 'Pos', 'pos',
                'proc', 'pull', 'push', 'PushMatrix', 'PushRotate', 'PushScale',
                'PushTranslate', 'put',
                'QueryPointer',
                'Raise', 'read', 'ReadImage', 'readlink', 'reads', 'ready',
                'real', 'receive', 'Refresh', 'Rem', 'remove', 'rename',
                'repl', 'reverse', 'right', 'rmdir', 'Rotate', 'Rpos',
                'Rtab', 'rtod', 'runerr',
                'save', 'Scale', 'seek', 'select', 'send', 'seq',
                'serial', 'set', 'setenv', 'setgid', 'setgrent',
                'sethostent', 'setpgrp', 'setpwent', 'setservent',
                'setuid', 'signal', 'sin', 'sort', 'sortf', 'Span',
                'spawn', 'sql', 'sqrt', 'stat', 'staticnames', 'stop',
                'StopAudio', 'string', 'structure', 'Succeed', 'Swi',
                'symlink', 'sys_errstr', 'system', 'syswrite',
                'Tab', 'tab', 'table', 'tan',
                'Texcoord', 'Texture', 'TextWidth', 'Translate',
                'trap', 'trim', 'truncate', 'trylock', 'type',
                'umask', 'Uncouple', 'unlock', 'upto', 'utime',
                'variable', 'VAttrib',
                'wait', 'WAttrib', 'WDefault', 'WFlush', 'where',
                'WinAssociate', 'WinButton', 'WinColorDialog', 'WindowContents',
                'WinEditRegion', 'WinFontDialog', 'WinMenuBar', 'WinOpenDialog',
                'WinPlayMedia', 'WinSaveDialog', 'WinScrollBar', 'WinSelectDialog',
                'write', 'WriteImage', 'writes', 'WSection',
                'WSync'), prefix=r'\b', suffix=r'\b'),
             Name.Function),
            include('numbers'),
            (r'<@|<<@|>@|>>@|\.>|->|===|~===|\*\*|\+\+|--|\.|~==|~=|<=|>=|==|'
             r'=|<<=|<<|>>=|>>|:=:|:=|->|<->|\+:=|\|', Operator),
            (r'"(?:[^\\"]|\\.)*"', String),
            (r"'(?:[^\\']|\\.)*'", String.Character),
            (r'[*<>+=/&!?@~\\-]', Operator),
            (r'\^', Operator),
            (r'(\w+)(\s*|[(,])', bygroups(Name, using(this))),
            (r"[\[\]]", Punctuation),
            (r"<>|=>|[()|:;,.'`{}%&?]", Punctuation),
            (r'\n+', Text),
        ],
        'numbers': [
            (r'\b([+-]?([2-9]|[12][0-9]|3[0-6])[rR][0-9a-zA-Z]+)\b', Number.Hex),
            (r'[+-]?[0-9]*\.([0-9]*)([Ee][+-]?[0-9]*)?', Number.Float),
            (r'\b([+-]?[0-9]+[KMGTPkmgtp]?)\b', Number.Integer),
        ],
        'subprogram': [
            (r'\(', Punctuation, ('#pop', 'formal_part')),
            (r';', Punctuation, '#pop'),
            (r'"[^"]+"|\w+', Name.Function),
            include('root'),
        ],
        'type_def': [
            (r'\(', Punctuation, 'formal_part'),
        ],
        'formal_part': [
            (r'\)', Punctuation, '#pop'),
            (r'\w+', Name.Variable),
            (r',', Punctuation),
            (r'(:string|:integer|:real)\b', Keyword.Reserved),
            include('root'),
        ],
    }


class IconLexer(RegexLexer):
    """
    Lexer for Icon.
    """
    name = 'Icon'
    aliases = ['icon']
    filenames = ['*.icon', '*.ICON']
    mimetypes = []
    url = 'https://www2.cs.arizona.edu/icon'
    version_added = '1.6'

    flags = re.MULTILINE

    tokens = {
        'root': [
            (r'[^\S\n]+', Text),
            (r'#.*?\n', Comment.Single),
            (r'[^\S\n]+', Text),
            (r'class|method|procedure', Keyword.Declaration, 'subprogram'),
            (r'(record)(\s+)(\w+)',
             bygroups(Keyword.Declaration, Text, Keyword.Type), 'type_def'),
            (r'(#line|\$C|\$Cend|\$define|\$else|\$endif|\$error|\$ifdef|'
             r'\$ifndef|\$include|\$line|\$undef)\b', Keyword.PreProc),
            (r'(&null|&fail)\b', Keyword.Constant),
            (r'&allocated|&ascii|&clock|&collections|&column|&col|&control|'
             r'&cset|&current|&dateline|&date|&digits|&dump|'
             r'&errno|&errornumber|&errortext|&errorvalue|&error|&errout|'
             r'&eventcode|&eventvalue|&eventsource|&e|'
             r'&features|&file|&host|&input|&interval|&lcase|&letters|'
             r'&level|&line|&ldrag|&lpress|&lrelease|'
             r'&main|&mdrag|&meta|&mpress|&mrelease|&now|&output|'
             r'&phi|&pick|&pi|&pos|&progname|'
             r'&random|&rdrag|&regions|&resize|&row|&rpress|&rrelease|'
             r'&shift|&source|&storage|&subject|'
             r'&time|&trace|&ucase|&version|'
             r'&window|&x|&y', Keyword.Reserved),
            (r'(by|of|not|to)\b', Keyword.Reserved),
            (r'(global|local|static)\b', Keyword.Reserved),
            (r'link', Keyword.Declaration),
            (words((
                'break', 'case', 'create', 'default', 'end', 'all',
                'do', 'else', 'every', 'fail', 'if', 'initial',
                'invocable', 'next',
                'repeat', 'return', 'suspend',
                'then', 'until', 'while'), prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
            (words((
                'abs', 'acos', 'Active', 'Alert', 'any',
                'args', 'array', 'asin', 'atan', 'atanh', 'Attrib',
                'bal', 'Bg',
                'callout', 'center', 'char', 'chdir', 'chmod', 'chown', 'chroot',
                'Clip', 'Clone', 'close', 'cofail', 'collect',
                'Color', 'ColorValue', 'condvar', 'copy',
                'CopyArea', 'cos', 'Couple', 'crypt', 'cset', 'ctime',
                'delay', 'delete', 'detab', 'display', 'DrawArc',
                'DrawCircle', 'DrawCube', 'DrawCurve', 'DrawCylinder',
                'DrawDisk', 'DrawImage', 'DrawLine', 'DrawPoint', 'DrawPolygon',
                'DrawRectangle', 'DrawSegment', 'DrawSphere', 'DrawString',
                'DrawTorus', 'dtor',
                'entab', 'EraseArea', 'errorclear', 'Event', 'eventmask',
                'EvGet', 'EvSend', 'exec', 'exit', 'exp', 'Eye',
                'fcntl', 'fdup', 'fetch', 'Fg', 'fieldnames',
                'FillArc', 'FillCircle', 'FillPolygon',
                'FillRectangle', 'find', 'flock', 'flush', 'Font',
                'FreeColor', 'FreeSpace', 'function',
                'get', 'getch', 'getche', 'getenv',
                'GetSpace', 'gettimeofday',
                'getuid', 'globalnames', 'GotoRC', 'GotoXY', 'gtime', 'hardlink',
                'iand', 'icom', 'IdentityMatrix', 'image', 'InPort', 'insert',
                'Int86', 'integer', 'ioctl', 'ior', 'ishift', 'istate', 'ixor',
                'kbhit', 'key', 'keyword', 'kill',
                'left', 'Len', 'list', 'load', 'loadfunc', 'localnames',
                'lock', 'log', 'Lower', 'lstat',
                'many', 'map', 'match', 'MatrixMode', 'max', 'member',
                'membernames', 'methodnames', 'methods', 'min', 'mkdir', 'move',
                'MultMatrix', 'mutex',
                'name', 'NewColor', 'Normals', 'numeric',
                'open', 'opencl', 'oprec', 'ord', 'OutPort',
                'PaletteChars', 'PaletteColor', 'PaletteKey', 'paramnames',
                'parent', 'Pattern', 'Peek', 'Pending', 'pipe', 'Pixel',
                'Poke', 'pop', 'PopMatrix', 'Pos', 'pos',
                'proc', 'pull', 'push', 'PushMatrix', 'PushRotate', 'PushScale',
                'PushTranslate', 'put',
                'QueryPointer',
                'Raise', 'read', 'ReadImage', 'readlink', 'reads', 'ready',
                'real', 'receive', 'Refresh', 'Rem', 'remove', 'rename',
                'repl', 'reverse', 'right', 'rmdir', 'Rotate', 'Rpos',
                'rtod', 'runerr',
                'save', 'Scale', 'seek', 'select', 'send', 'seq',
                'serial', 'set', 'setenv',
                'setuid', 'signal', 'sin', 'sort', 'sortf',
                'spawn', 'sql', 'sqrt', 'stat', 'staticnames', 'stop',
                'string', 'structure', 'Swi',
                'symlink', 'sys_errstr', 'system', 'syswrite',
                'tab', 'table', 'tan',
                'Texcoord', 'Texture', 'TextWidth', 'Translate',
                'trap', 'trim', 'truncate', 'trylock', 'type',
                'umask', 'Uncouple', 'unlock', 'upto', 'utime',
                'variable',
                'wait', 'WAttrib', 'WDefault', 'WFlush', 'where',
                'WinAssociate', 'WinButton', 'WinColorDialog', 'WindowContents',
                'WinEditRegion', 'WinFontDialog', 'WinMenuBar', 'WinOpenDialog',
                'WinPlayMedia', 'WinSaveDialog', 'WinScrollBar', 'WinSelectDialog',
                'write', 'WriteImage', 'writes', 'WSection',
                'WSync'), prefix=r'\b', suffix=r'\b'),
             Name.Function),
            include('numbers'),
            (r'===|~===|\*\*|\+\+|--|\.|==|~==|<=|>=|=|~=|<<=|<<|>>=|>>|'
             r':=:|:=|<->|<-|\+:=|\|\||\|', Operator),
            (r'"(?:[^\\"]|\\.)*"', String),
            (r"'(?:[^\\']|\\.)*'", String.Character),
            (r'[*<>+=/&!?@~\\-]', Operator),
            (r'(\w+)(\s*|[(,])', bygroups(Name, using(this))),
            (r"[\[\]]", Punctuation),
            (r"<>|=>|[()|:;,.'`{}%\^&?]", Punctuation),
            (r'\n+', Text),
        ],
        'numbers': [
            (r'\b([+-]?([2-9]|[12][0-9]|3[0-6])[rR][0-9a-zA-Z]+)\b', Number.Hex),
            (r'[+-]?[0-9]*\.([0-9]*)([Ee][+-]?[0-9]*)?', Number.Float),
            (r'\b([+-]?[0-9]+[KMGTPkmgtp]?)\b', Number.Integer),
        ],
        'subprogram': [
            (r'\(', Punctuation, ('#pop', 'formal_part')),
            (r';', Punctuation, '#pop'),
            (r'"[^"]+"|\w+', Name.Function),
            include('root'),
        ],
        'type_def': [
            (r'\(', Punctuation, 'formal_part'),
        ],
        'formal_part': [
            (r'\)', Punctuation, '#pop'),
            (r'\w+', Name.Variable),
            (r',', Punctuation),
            (r'(:string|:integer|:real)\b', Keyword.Reserved),
            include('root'),
        ],
    }


class UcodeLexer(RegexLexer):
    """
    Lexer for Icon ucode files.
    """
    name = 'ucode'
    aliases = ['ucode']
    filenames = ['*.u', '*.u1', '*.u2']
    mimetypes = []
    url = 'http://www.unicon.org'
    version_added = '2.4'

    flags = re.MULTILINE

    tokens = {
        'root': [
            (r'(#.*\n)', Comment),
            (words((
                'con', 'declend', 'end',
                'global',
                'impl', 'invocable',
                'lab', 'link', 'local',
                'record',
                'uid', 'unions',
                'version'),
                prefix=r'\b', suffix=r'\b'),
             Name.Function),
            (words((
                'colm', 'filen', 'line', 'synt'),
                prefix=r'\b', suffix=r'\b'),
             Comment),
            (words((
                'asgn',
                'bang', 'bscan',
                'cat', 'ccase', 'chfail',
                'coact', 'cofail', 'compl',
                'coret', 'create', 'cset',
                'diff', 'div', 'dup',
                'efail', 'einit', 'end', 'eqv', 'eret',
                'error', 'escan', 'esusp',
                'field',
                'goto',
                'init', 'int', 'inter',
                'invoke',
                'keywd',
                'lconcat', 'lexeq', 'lexge',
                'lexgt', 'lexle', 'lexlt', 'lexne',
                'limit', 'llist', 'lsusp',
                'mark', 'mark0', 'minus', 'mod', 'mult',
                'neg', 'neqv', 'nonnull', 'noop', 'null',
                'number', 'numeq', 'numge', 'numgt',
                'numle', 'numlt', 'numne',
                'pfail', 'plus', 'pnull', 'pop', 'power',
                'pret', 'proc', 'psusp', 'push1', 'pushn1',
                'random', 'rasgn', 'rcv', 'rcvbk', 'real',
                'refresh', 'rswap',
                'sdup', 'sect', 'size', 'snd', 'sndbk',
                'str', 'subsc', 'swap',
                'tabmat', 'tally', 'toby', 'trace',
                'unmark',
                'value', 'var'), prefix=r'\b', suffix=r'\b'),
             Keyword.Declaration),
            (words((
                'any',
                'case',
                'endcase', 'endevery', 'endif',
                'endifelse', 'endrepeat', 'endsuspend',
                'enduntil', 'endwhile', 'every',
                'if', 'ifelse',
                'repeat',
                'suspend',
                'until',
                'while'),
             prefix=r'\b', suffix=r'\b'),
             Name.Constant),
            (r'\d+(\s*|\.$|$)', Number.Integer),
            (r'[+-]?\d*\.\d+(E[-+]?\d+)?', Number.Float),
            (r'[+-]?\d+\.\d*(E[-+]?\d+)?', Number.Float),
            (r"(<>|=>|[()|:;,.'`]|[{}]|[%^]|[&?])", Punctuation),
            (r'\s+\b', Text),
            (r'[\w-]+', Text),
        ],
    }

    def analyse_text(text):
        """endsuspend and endrepeat are unique to this language, and
        \\self, /self doesn't seem to get used anywhere else either."""
        result = 0

        if 'endsuspend' in text:
            result += 0.1

        if 'endrepeat' in text:
            result += 0.1

        if ':=' in text:
            result += 0.01

        if 'procedure' in text and 'end' in text:
            result += 0.01

        # This seems quite unique to unicon -- doesn't appear in any other
        # example source we have (A quick search reveals that \SELF appears in
        # Perl/Raku code)
        if r'\self' in text and r'/self' in text:
            result += 0.5

        return result

# === NexusCore/openenv\Lib\site-packages\nltk\collocations.py ===
# Natural Language Toolkit: Collocations and Association Measures
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""
Tools to identify collocations --- words that often appear consecutively
--- within corpora. They may also be used to find other associations between
word occurrences.
See Manning and Schutze ch. 5 at https://nlp.stanford.edu/fsnlp/promo/colloc.pdf
and the Text::NSP Perl package at http://ngram.sourceforge.net

Finding collocations requires first calculating the frequencies of words and
their appearance in the context of other words. Often the collection of words
will then requiring filtering to only retain useful content terms. Each ngram
of words may then be scored according to some association measure, in order
to determine the relative likelihood of each ngram being a collocation.

The ``BigramCollocationFinder`` and ``TrigramCollocationFinder`` classes provide
these functionalities, dependent on being provided a function which scores a
ngram given appropriate frequency counts. A number of standard association
measures are provided in bigram_measures and trigram_measures.
"""

# Possible TODOs:
# - consider the distinction between f(x,_) and f(x) and whether our
#   approximation is good enough for fragmented data, and mention it
# - add a n-gram collocation finder with measures which only utilise n-gram
#   and unigram counts (raw_freq, pmi, student_t)

import itertools as _itertools

# these two unused imports are referenced in collocations.doctest
from nltk.metrics import (
    BigramAssocMeasures,
    ContingencyMeasures,
    QuadgramAssocMeasures,
    TrigramAssocMeasures,
)
from nltk.metrics.spearman import ranks_from_scores, spearman_correlation
from nltk.probability import FreqDist
from nltk.util import ngrams


class AbstractCollocationFinder:
    """
    An abstract base class for collocation finders whose purpose is to
    collect collocation candidate frequencies, filter and rank them.

    As a minimum, collocation finders require the frequencies of each
    word in a corpus, and the joint frequency of word tuples. This data
    should be provided through nltk.probability.FreqDist objects or an
    identical interface.
    """

    def __init__(self, word_fd, ngram_fd):
        self.word_fd = word_fd
        self.N = word_fd.N()
        self.ngram_fd = ngram_fd

    @classmethod
    def _build_new_documents(
        cls, documents, window_size, pad_left=False, pad_right=False, pad_symbol=None
    ):
        """
        Pad the document with the place holder according to the window_size
        """
        padding = (pad_symbol,) * (window_size - 1)
        if pad_right:
            return _itertools.chain.from_iterable(
                _itertools.chain(doc, padding) for doc in documents
            )
        if pad_left:
            return _itertools.chain.from_iterable(
                _itertools.chain(padding, doc) for doc in documents
            )

    @classmethod
    def from_documents(cls, documents):
        """Constructs a collocation finder given a collection of documents,
        each of which is a list (or iterable) of tokens.
        """
        # return cls.from_words(_itertools.chain(*documents))
        return cls.from_words(
            cls._build_new_documents(documents, cls.default_ws, pad_right=True)
        )

    @staticmethod
    def _ngram_freqdist(words, n):
        return FreqDist(tuple(words[i : i + n]) for i in range(len(words) - 1))

    def _apply_filter(self, fn=lambda ngram, freq: False):
        """Generic filter removes ngrams from the frequency distribution
        if the function returns True when passed an ngram tuple.
        """
        tmp_ngram = FreqDist()
        for ngram, freq in self.ngram_fd.items():
            if not fn(ngram, freq):
                tmp_ngram[ngram] = freq
        self.ngram_fd = tmp_ngram

    def apply_freq_filter(self, min_freq):
        """Removes candidate ngrams which have frequency less than min_freq."""
        self._apply_filter(lambda ng, freq: freq < min_freq)

    def apply_ngram_filter(self, fn):
        """Removes candidate ngrams (w1, w2, ...) where fn(w1, w2, ...)
        evaluates to True.
        """
        self._apply_filter(lambda ng, f: fn(*ng))

    def apply_word_filter(self, fn):
        """Removes candidate ngrams (w1, w2, ...) where any of (fn(w1), fn(w2),
        ...) evaluates to True.
        """
        self._apply_filter(lambda ng, f: any(fn(w) for w in ng))

    def _score_ngrams(self, score_fn):
        """Generates of (ngram, score) pairs as determined by the scoring
        function provided.
        """
        for tup in self.ngram_fd:
            score = self.score_ngram(score_fn, *tup)
            if score is not None:
                yield tup, score

    def score_ngrams(self, score_fn):
        """Returns a sequence of (ngram, score) pairs ordered from highest to
        lowest score, as determined by the scoring function provided.
        """
        return sorted(self._score_ngrams(score_fn), key=lambda t: (-t[1], t[0]))

    def nbest(self, score_fn, n):
        """Returns the top n ngrams when scored by the given function."""
        return [p for p, s in self.score_ngrams(score_fn)[:n]]

    def above_score(self, score_fn, min_score):
        """Returns a sequence of ngrams, ordered by decreasing score, whose
        scores each exceed the given minimum score.
        """
        for ngram, score in self.score_ngrams(score_fn):
            if score > min_score:
                yield ngram
            else:
                break


class BigramCollocationFinder(AbstractCollocationFinder):
    """A tool for the finding and ranking of bigram collocations or other
    association measures. It is often useful to use from_words() rather than
    constructing an instance directly.
    """

    default_ws = 2

    def __init__(self, word_fd, bigram_fd, window_size=2):
        """Construct a BigramCollocationFinder, given FreqDists for
        appearances of words and (possibly non-contiguous) bigrams.
        """
        AbstractCollocationFinder.__init__(self, word_fd, bigram_fd)
        self.window_size = window_size

    @classmethod
    def from_words(cls, words, window_size=2):
        """Construct a BigramCollocationFinder for all bigrams in the given
        sequence.  When window_size > 2, count non-contiguous bigrams, in the
        style of Church and Hanks's (1990) association ratio.
        """
        wfd = FreqDist()
        bfd = FreqDist()

        if window_size < 2:
            raise ValueError("Specify window_size at least 2")

        for window in ngrams(words, window_size, pad_right=True):
            w1 = window[0]
            if w1 is None:
                continue
            wfd[w1] += 1
            for w2 in window[1:]:
                if w2 is not None:
                    bfd[(w1, w2)] += 1
        return cls(wfd, bfd, window_size=window_size)

    def score_ngram(self, score_fn, w1, w2):
        """Returns the score for a given bigram using the given scoring
        function.  Following Church and Hanks (1990), counts are scaled by
        a factor of 1/(window_size - 1).
        """
        n_all = self.N
        n_ii = self.ngram_fd[(w1, w2)] / (self.window_size - 1.0)
        if not n_ii:
            return
        n_ix = self.word_fd[w1]
        n_xi = self.word_fd[w2]
        return score_fn(n_ii, (n_ix, n_xi), n_all)


class TrigramCollocationFinder(AbstractCollocationFinder):
    """A tool for the finding and ranking of trigram collocations or other
    association measures. It is often useful to use from_words() rather than
    constructing an instance directly.
    """

    default_ws = 3

    def __init__(self, word_fd, bigram_fd, wildcard_fd, trigram_fd):
        """Construct a TrigramCollocationFinder, given FreqDists for
        appearances of words, bigrams, two words with any word between them,
        and trigrams.
        """
        AbstractCollocationFinder.__init__(self, word_fd, trigram_fd)
        self.wildcard_fd = wildcard_fd
        self.bigram_fd = bigram_fd

    @classmethod
    def from_words(cls, words, window_size=3):
        """Construct a TrigramCollocationFinder for all trigrams in the given
        sequence.
        """
        if window_size < 3:
            raise ValueError("Specify window_size at least 3")

        wfd = FreqDist()
        wildfd = FreqDist()
        bfd = FreqDist()
        tfd = FreqDist()
        for window in ngrams(words, window_size, pad_right=True):
            w1 = window[0]
            if w1 is None:
                continue
            for w2, w3 in _itertools.combinations(window[1:], 2):
                wfd[w1] += 1
                if w2 is None:
                    continue
                bfd[(w1, w2)] += 1
                if w3 is None:
                    continue
                wildfd[(w1, w3)] += 1
                tfd[(w1, w2, w3)] += 1
        return cls(wfd, bfd, wildfd, tfd)

    def bigram_finder(self):
        """Constructs a bigram collocation finder with the bigram and unigram
        data from this finder. Note that this does not include any filtering
        applied to this finder.
        """
        return BigramCollocationFinder(self.word_fd, self.bigram_fd)

    def score_ngram(self, score_fn, w1, w2, w3):
        """Returns the score for a given trigram using the given scoring
        function.
        """
        n_all = self.N
        n_iii = self.ngram_fd[(w1, w2, w3)]
        if not n_iii:
            return
        n_iix = self.bigram_fd[(w1, w2)]
        n_ixi = self.wildcard_fd[(w1, w3)]
        n_xii = self.bigram_fd[(w2, w3)]
        n_ixx = self.word_fd[w1]
        n_xix = self.word_fd[w2]
        n_xxi = self.word_fd[w3]
        return score_fn(n_iii, (n_iix, n_ixi, n_xii), (n_ixx, n_xix, n_xxi), n_all)


class QuadgramCollocationFinder(AbstractCollocationFinder):
    """A tool for the finding and ranking of quadgram collocations or other association measures.
    It is often useful to use from_words() rather than constructing an instance directly.
    """

    default_ws = 4

    def __init__(self, word_fd, quadgram_fd, ii, iii, ixi, ixxi, iixi, ixii):
        """Construct a QuadgramCollocationFinder, given FreqDists for appearances of words,
        bigrams, trigrams, two words with one word and two words between them, three words
        with a word between them in both variations.
        """
        AbstractCollocationFinder.__init__(self, word_fd, quadgram_fd)
        self.iii = iii
        self.ii = ii
        self.ixi = ixi
        self.ixxi = ixxi
        self.iixi = iixi
        self.ixii = ixii

    @classmethod
    def from_words(cls, words, window_size=4):
        if window_size < 4:
            raise ValueError("Specify window_size at least 4")
        ixxx = FreqDist()
        iiii = FreqDist()
        ii = FreqDist()
        iii = FreqDist()
        ixi = FreqDist()
        ixxi = FreqDist()
        iixi = FreqDist()
        ixii = FreqDist()

        for window in ngrams(words, window_size, pad_right=True):
            w1 = window[0]
            if w1 is None:
                continue
            for w2, w3, w4 in _itertools.combinations(window[1:], 3):
                ixxx[w1] += 1
                if w2 is None:
                    continue
                ii[(w1, w2)] += 1
                if w3 is None:
                    continue
                iii[(w1, w2, w3)] += 1
                ixi[(w1, w3)] += 1
                if w4 is None:
                    continue
                iiii[(w1, w2, w3, w4)] += 1
                ixxi[(w1, w4)] += 1
                ixii[(w1, w3, w4)] += 1
                iixi[(w1, w2, w4)] += 1

        return cls(ixxx, iiii, ii, iii, ixi, ixxi, iixi, ixii)

    def score_ngram(self, score_fn, w1, w2, w3, w4):
        n_all = self.N
        n_iiii = self.ngram_fd[(w1, w2, w3, w4)]
        if not n_iiii:
            return
        n_iiix = self.iii[(w1, w2, w3)]
        n_xiii = self.iii[(w2, w3, w4)]
        n_iixi = self.iixi[(w1, w2, w4)]
        n_ixii = self.ixii[(w1, w3, w4)]

        n_iixx = self.ii[(w1, w2)]
        n_xxii = self.ii[(w3, w4)]
        n_xiix = self.ii[(w2, w3)]
        n_ixix = self.ixi[(w1, w3)]
        n_ixxi = self.ixxi[(w1, w4)]
        n_xixi = self.ixi[(w2, w4)]

        n_ixxx = self.word_fd[w1]
        n_xixx = self.word_fd[w2]
        n_xxix = self.word_fd[w3]
        n_xxxi = self.word_fd[w4]
        return score_fn(
            n_iiii,
            (n_iiix, n_iixi, n_ixii, n_xiii),
            (n_iixx, n_ixix, n_ixxi, n_xixi, n_xxii, n_xiix),
            (n_ixxx, n_xixx, n_xxix, n_xxxi),
            n_all,
        )


def demo(scorer=None, compare_scorer=None):
    """Finds bigram collocations in the files of the WebText corpus."""
    from nltk.metrics import (
        BigramAssocMeasures,
        ranks_from_scores,
        spearman_correlation,
    )

    if scorer is None:
        scorer = BigramAssocMeasures.likelihood_ratio
    if compare_scorer is None:
        compare_scorer = BigramAssocMeasures.raw_freq

    from nltk.corpus import stopwords, webtext

    ignored_words = stopwords.words("english")
    word_filter = lambda w: len(w) < 3 or w.lower() in ignored_words

    for file in webtext.fileids():
        words = [word.lower() for word in webtext.words(file)]

        cf = BigramCollocationFinder.from_words(words)
        cf.apply_freq_filter(3)
        cf.apply_word_filter(word_filter)

        corr = spearman_correlation(
            ranks_from_scores(cf.score_ngrams(scorer)),
            ranks_from_scores(cf.score_ngrams(compare_scorer)),
        )
        print(file)
        print("\t", [" ".join(tup) for tup in cf.nbest(scorer, 15)])
        print(f"\t Correlation to {compare_scorer.__name__}: {corr:0.4f}")


# Slows down loading too much
# bigram_measures = BigramAssocMeasures()
# trigram_measures = TrigramAssocMeasures()

if __name__ == "__main__":
    import sys

    from nltk.metrics import BigramAssocMeasures

    try:
        scorer = eval("BigramAssocMeasures." + sys.argv[1])
    except IndexError:
        scorer = None
    try:
        compare_scorer = eval("BigramAssocMeasures." + sys.argv[2])
    except IndexError:
        compare_scorer = None

    demo(scorer, compare_scorer)

__all__ = [
    "BigramCollocationFinder",
    "TrigramCollocationFinder",
    "QuadgramCollocationFinder",
]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_stackless.py ===
from __future__ import nested_scopes

import weakref
import sys

from _pydevd_bundle.pydevd_comm import get_global_debugger
from _pydevd_bundle.pydevd_constants import call_only_once
from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle.pydevd_custom_frames import update_custom_frame, remove_custom_frame, add_custom_frame
import stackless  # @UnresolvedImport
from _pydev_bundle import pydev_log


# Used so that we don't loose the id (because we'll remove when it's not alive and would generate a new id for the
# same tasklet).
class TaskletToLastId:
    """
    So, why not a WeakKeyDictionary?
    The problem is that removals from the WeakKeyDictionary will create a new tasklet (as it adds a callback to
    remove the key when it's garbage-collected), so, we can get into a recursion.
    """

    def __init__(self):
        self.tasklet_ref_to_last_id = {}
        self._i = 0

    def get(self, tasklet):
        return self.tasklet_ref_to_last_id.get(weakref.ref(tasklet))

    def __setitem__(self, tasklet, last_id):
        self.tasklet_ref_to_last_id[weakref.ref(tasklet)] = last_id
        self._i += 1
        if self._i % 100 == 0:  # Collect at each 100 additions to the dict (no need to rush).
            for tasklet_ref in list(self.tasklet_ref_to_last_id.keys()):
                if tasklet_ref() is None:
                    del self.tasklet_ref_to_last_id[tasklet_ref]


_tasklet_to_last_id = TaskletToLastId()


# =======================================================================================================================
# _TaskletInfo
# =======================================================================================================================
class _TaskletInfo:
    _last_id = 0

    def __init__(self, tasklet_weakref, tasklet):
        self.frame_id = None
        self.tasklet_weakref = tasklet_weakref

        last_id = _tasklet_to_last_id.get(tasklet)
        if last_id is None:
            _TaskletInfo._last_id += 1
            last_id = _TaskletInfo._last_id
            _tasklet_to_last_id[tasklet] = last_id

        self._tasklet_id = last_id

        self.update_name()

    def update_name(self):
        tasklet = self.tasklet_weakref()
        if tasklet:
            if tasklet.blocked:
                state = "blocked"
            elif tasklet.paused:
                state = "paused"
            elif tasklet.scheduled:
                state = "scheduled"
            else:
                state = "<UNEXPECTED>"

            try:
                name = tasklet.name
            except AttributeError:
                if tasklet.is_main:
                    name = "MainTasklet"
                else:
                    name = "Tasklet-%s" % (self._tasklet_id,)

            thread_id = tasklet.thread_id
            if thread_id != -1:
                for thread in threading.enumerate():
                    if thread.ident == thread_id:
                        if thread.name:
                            thread_name = "of %s" % (thread.name,)
                        else:
                            thread_name = "of Thread-%s" % (thread.name or str(thread_id),)
                        break
                else:
                    # should not happen.
                    thread_name = "of Thread-%s" % (str(thread_id),)
                thread = None
            else:
                # tasklet is no longer bound to a thread, because its thread ended
                thread_name = "without thread"

            tid = id(tasklet)
            tasklet = None
        else:
            state = "dead"
            name = "Tasklet-%s" % (self._tasklet_id,)
            thread_name = ""
            tid = "-"
        self.tasklet_name = "%s %s %s (%s)" % (state, name, thread_name, tid)

    if not hasattr(stackless.tasklet, "trace_function"):
        # bug https://bitbucket.org/stackless-dev/stackless/issue/42
        # is not fixed. Stackless releases before 2014
        def update_name(self):
            tasklet = self.tasklet_weakref()
            if tasklet:
                try:
                    name = tasklet.name
                except AttributeError:
                    if tasklet.is_main:
                        name = "MainTasklet"
                    else:
                        name = "Tasklet-%s" % (self._tasklet_id,)

                thread_id = tasklet.thread_id
                for thread in threading.enumerate():
                    if thread.ident == thread_id:
                        if thread.name:
                            thread_name = "of %s" % (thread.name,)
                        else:
                            thread_name = "of Thread-%s" % (thread.name or str(thread_id),)
                        break
                else:
                    # should not happen.
                    thread_name = "of Thread-%s" % (str(thread_id),)
                thread = None

                tid = id(tasklet)
                tasklet = None
            else:
                name = "Tasklet-%s" % (self._tasklet_id,)
                thread_name = ""
                tid = "-"
            self.tasklet_name = "%s %s (%s)" % (name, thread_name, tid)


_weak_tasklet_registered_to_info = {}


# =======================================================================================================================
# get_tasklet_info
# =======================================================================================================================
def get_tasklet_info(tasklet):
    return register_tasklet_info(tasklet)


# =======================================================================================================================
# register_tasklet_info
# =======================================================================================================================
def register_tasklet_info(tasklet):
    r = weakref.ref(tasklet)
    info = _weak_tasklet_registered_to_info.get(r)
    if info is None:
        info = _weak_tasklet_registered_to_info[r] = _TaskletInfo(r, tasklet)

    return info


_application_set_schedule_callback = None


# =======================================================================================================================
# _schedule_callback
# =======================================================================================================================
def _schedule_callback(prev, next):
    """
    Called when a context is stopped or a new context is made runnable.
    """
    try:
        if not prev and not next:
            return

        current_frame = sys._getframe()

        if next:
            register_tasklet_info(next)

            # Ok, making next runnable: set the tracing facility in it.
            debugger = get_global_debugger()
            if debugger is not None:
                next.trace_function = debugger.get_thread_local_trace_func()
                frame = next.frame
                if frame is current_frame:
                    frame = frame.f_back
                if hasattr(frame, "f_trace"):  # Note: can be None (but hasattr should cover for that too).
                    frame.f_trace = debugger.get_thread_local_trace_func()

            debugger = None

        if prev:
            register_tasklet_info(prev)

        try:
            for tasklet_ref, tasklet_info in list(_weak_tasklet_registered_to_info.items()):  # Make sure it's a copy!
                tasklet = tasklet_ref()
                if tasklet is None or not tasklet.alive:
                    # Garbage-collected already!
                    try:
                        del _weak_tasklet_registered_to_info[tasklet_ref]
                    except KeyError:
                        pass
                    if tasklet_info.frame_id is not None:
                        remove_custom_frame(tasklet_info.frame_id)
                else:
                    is_running = stackless.get_thread_info(tasklet.thread_id)[1] is tasklet
                    if tasklet is prev or (tasklet is not next and not is_running):
                        # the tasklet won't run after this scheduler action:
                        # - the tasklet is the previous tasklet
                        # - it is not the next tasklet and it is not an already running tasklet
                        frame = tasklet.frame
                        if frame is current_frame:
                            frame = frame.f_back
                        if frame is not None:
                            # print >>sys.stderr, "SchedCB: %r, %d, '%s', '%s'" % (tasklet, frame.f_lineno, _filename, base)
                            debugger = get_global_debugger()
                            if debugger is not None and debugger.get_file_type(frame) is None:
                                tasklet_info.update_name()
                                if tasklet_info.frame_id is None:
                                    tasklet_info.frame_id = add_custom_frame(frame, tasklet_info.tasklet_name, tasklet.thread_id)
                                else:
                                    update_custom_frame(tasklet_info.frame_id, frame, tasklet.thread_id, name=tasklet_info.tasklet_name)
                            debugger = None

                    elif tasklet is next or is_running:
                        if tasklet_info.frame_id is not None:
                            # Remove info about stackless suspended when it starts to run.
                            remove_custom_frame(tasklet_info.frame_id)
                            tasklet_info.frame_id = None

        finally:
            tasklet = None
            tasklet_info = None
            frame = None

    except:
        pydev_log.exception()

    if _application_set_schedule_callback is not None:
        return _application_set_schedule_callback(prev, next)


if not hasattr(stackless.tasklet, "trace_function"):
    # Older versions of Stackless, released before 2014
    # This code does not work reliable! It is affected by several
    # stackless bugs: Stackless issues #44, #42, #40
    def _schedule_callback(prev, next):
        """
        Called when a context is stopped or a new context is made runnable.
        """
        try:
            if not prev and not next:
                return

            if next:
                register_tasklet_info(next)

                # Ok, making next runnable: set the tracing facility in it.
                debugger = get_global_debugger()
                if debugger is not None and next.frame:
                    if hasattr(next.frame, "f_trace"):
                        next.frame.f_trace = debugger.get_thread_local_trace_func()
                debugger = None

            if prev:
                register_tasklet_info(prev)

            try:
                for tasklet_ref, tasklet_info in list(_weak_tasklet_registered_to_info.items()):  # Make sure it's a copy!
                    tasklet = tasklet_ref()
                    if tasklet is None or not tasklet.alive:
                        # Garbage-collected already!
                        try:
                            del _weak_tasklet_registered_to_info[tasklet_ref]
                        except KeyError:
                            pass
                        if tasklet_info.frame_id is not None:
                            remove_custom_frame(tasklet_info.frame_id)
                    else:
                        if tasklet.paused or tasklet.blocked or tasklet.scheduled:
                            if tasklet.frame and tasklet.frame.f_back:
                                f_back = tasklet.frame.f_back
                                debugger = get_global_debugger()
                                if debugger is not None and debugger.get_file_type(f_back) is None:
                                    if tasklet_info.frame_id is None:
                                        tasklet_info.frame_id = add_custom_frame(f_back, tasklet_info.tasklet_name, tasklet.thread_id)
                                    else:
                                        update_custom_frame(tasklet_info.frame_id, f_back, tasklet.thread_id)
                                debugger = None

                        elif tasklet.is_current:
                            if tasklet_info.frame_id is not None:
                                # Remove info about stackless suspended when it starts to run.
                                remove_custom_frame(tasklet_info.frame_id)
                                tasklet_info.frame_id = None

            finally:
                tasklet = None
                tasklet_info = None
                f_back = None

        except:
            pydev_log.exception()

        if _application_set_schedule_callback is not None:
            return _application_set_schedule_callback(prev, next)

    _original_setup = stackless.tasklet.setup

    # =======================================================================================================================
    # setup
    # =======================================================================================================================
    def setup(self, *args, **kwargs):
        """
        Called to run a new tasklet: rebind the creation so that we can trace it.
        """

        f = self.tempval

        def new_f(old_f, args, kwargs):
            debugger = get_global_debugger()
            if debugger is not None:
                debugger.enable_tracing()

            debugger = None

            # Remove our own traces :)
            self.tempval = old_f
            register_tasklet_info(self)

            # Hover old_f to see the stackless being created and *args and **kwargs to see its parameters.
            return old_f(*args, **kwargs)

        # This is the way to tell stackless that the function it should execute is our function, not the original one. Note:
        # setting tempval is the same as calling bind(new_f), but it seems that there's no other way to get the currently
        # bound function, so, keeping on using tempval instead of calling bind (which is actually the same thing in a better
        # API).

        self.tempval = new_f

        return _original_setup(self, f, args, kwargs)

    # =======================================================================================================================
    # __call__
    # =======================================================================================================================
    def __call__(self, *args, **kwargs):
        """
        Called to run a new tasklet: rebind the creation so that we can trace it.
        """

        return setup(self, *args, **kwargs)

    _original_run = stackless.run

    # =======================================================================================================================
    # run
    # =======================================================================================================================
    def run(*args, **kwargs):
        debugger = get_global_debugger()
        if debugger is not None:
            debugger.enable_tracing()
        debugger = None

        return _original_run(*args, **kwargs)


# =======================================================================================================================
# patch_stackless
# =======================================================================================================================
def patch_stackless():
    """
    This function should be called to patch the stackless module so that new tasklets are properly tracked in the
    debugger.
    """
    global _application_set_schedule_callback
    _application_set_schedule_callback = stackless.set_schedule_callback(_schedule_callback)

    def set_schedule_callback(callable):
        global _application_set_schedule_callback
        old = _application_set_schedule_callback
        _application_set_schedule_callback = callable
        return old

    def get_schedule_callback():
        global _application_set_schedule_callback
        return _application_set_schedule_callback

    set_schedule_callback.__doc__ = stackless.set_schedule_callback.__doc__
    if hasattr(stackless, "get_schedule_callback"):
        get_schedule_callback.__doc__ = stackless.get_schedule_callback.__doc__
    stackless.set_schedule_callback = set_schedule_callback
    stackless.get_schedule_callback = get_schedule_callback

    if not hasattr(stackless.tasklet, "trace_function"):
        # Older versions of Stackless, released before 2014
        __call__.__doc__ = stackless.tasklet.__call__.__doc__
        stackless.tasklet.__call__ = __call__

        setup.__doc__ = stackless.tasklet.setup.__doc__
        stackless.tasklet.setup = setup

        run.__doc__ = stackless.run.__doc__
        stackless.run = run


patch_stackless = call_only_once(patch_stackless)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_element_handle.py ===
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

import base64
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    cast,
)

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    async_writefile,
    locals_to_params,
    make_dirs_for_file,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._set_input_files_helpers import convert_input_files

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._locator import Locator


class ElementHandle(JSHandle):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def _createSelectorForTest(self, name: str) -> Optional[str]:
        return await self._channel.send("createSelectorForTest", dict(name=name))

    def as_element(self) -> Optional["ElementHandle"]:
        return self

    async def owner_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("ownerFrame"))

    async def content_frame(self) -> Optional["Frame"]:
        return from_nullable_channel(await self._channel.send("contentFrame"))

    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._channel.send("getAttribute", dict(name=name))

    async def text_content(self) -> Optional[str]:
        return await self._channel.send("textContent")

    async def inner_text(self) -> str:
        return await self._channel.send("innerText")

    async def inner_html(self) -> str:
        return await self._channel.send("innerHTML")

    async def is_checked(self) -> bool:
        return await self._channel.send("isChecked")

    async def is_disabled(self) -> bool:
        return await self._channel.send("isDisabled")

    async def is_editable(self) -> bool:
        return await self._channel.send("isEditable")

    async def is_enabled(self) -> bool:
        return await self._channel.send("isEnabled")

    async def is_hidden(self) -> bool:
        return await self._channel.send("isHidden")

    async def is_visible(self) -> bool:
        return await self._channel.send("isVisible")

    async def dispatch_event(self, type: str, eventInit: Dict = None) -> None:
        await self._channel.send(
            "dispatchEvent", dict(type=type, eventInit=serialize_argument(eventInit))
        )

    async def scroll_into_view_if_needed(self, timeout: float = None) -> None:
        await self._channel.send("scrollIntoViewIfNeeded", locals_to_params(locals()))

    async def hover(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def click(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def select_option(
        self,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                timeout=timeout,
                force=force,
                **convert_select_option_values(value, index, label, element),
            )
        )
        return await self._channel.send("selectOption", params)

    async def tap(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        await self._channel.send("selectText", locals_to_params(locals()))

    async def input_value(self, timeout: float = None) -> str:
        return await self._channel.send("inputValue", locals_to_params(locals()))

    async def set_input_files(
        self,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        frame = await self.owner_frame()
        if not frame:
            raise Error("Cannot set input files to detached element")
        converted = await convert_input_files(files, frame.page.context)
        await self._channel.send(
            "setInputFiles",
            {
                "timeout": timeout,
                **converted,
            },
        )

    async def focus(self) -> None:
        await self._channel.send("focus")

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("type", locals_to_params(locals()))

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("press", locals_to_params(locals()))

    async def set_checked(
        self,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("check", locals_to_params(locals()))

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def bounding_box(self) -> Optional[FloatRect]:
        return await self._channel.send("boundingBox")

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: Sequence["Locator"] = None,
        maskColor: str = None,
        style: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        if "mask" in params:
            params["mask"] = list(
                map(
                    lambda locator: (
                        {
                            "frame": locator._frame._channel,
                            "selector": locator._selector,
                        }
                    ),
                    params["mask"],
                )
            )
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def query_selector(self, selector: str) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("querySelector", dict(selector=selector))
        )

    async def query_selector_all(self, selector: str) -> List["ElementHandle"]:
        return list(
            map(
                cast(Callable[[Any], Any], from_nullable_channel),
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def wait_for_element_state(
        self,
        state: Literal[
            "disabled", "editable", "enabled", "hidden", "stable", "visible"
        ],
        timeout: float = None,
    ) -> None:
        await self._channel.send("waitForElementState", locals_to_params(locals()))

    async def wait_for_selector(
        self,
        selector: str,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        timeout: float = None,
        strict: bool = None,
    ) -> Optional["ElementHandle"]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )


def convert_select_option_values(
    value: Union[str, Sequence[str]] = None,
    index: Union[int, Sequence[int]] = None,
    label: Union[str, Sequence[str]] = None,
    element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
) -> Any:
    if value is None and index is None and label is None and element is None:
        return {}

    options: Any = None
    elements: Any = None
    if value is not None:
        if isinstance(value, str):
            value = [value]
        options = (options or []) + list(map(lambda e: dict(valueOrLabel=e), value))
    if index is not None:
        if isinstance(index, int):
            index = [index]
        options = (options or []) + list(map(lambda e: dict(index=e), index))
    if label is not None:
        if isinstance(label, str):
            label = [label]
        options = (options or []) + list(map(lambda e: dict(label=e), label))
    if element:
        if isinstance(element, ElementHandle):
            element = [element]
        elements = list(map(lambda e: e._channel, element))

    return dict(options=options, elements=elements)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\layout.py ===
"""
Wrapper for the layout.
"""

from __future__ import annotations

from typing import Generator, Iterable, Union

from prompt_toolkit.buffer import Buffer

from .containers import (
    AnyContainer,
    ConditionalContainer,
    Container,
    Window,
    to_container,
)
from .controls import BufferControl, SearchBufferControl, UIControl

__all__ = [
    "Layout",
    "InvalidLayoutError",
    "walk",
]

FocusableElement = Union[str, Buffer, UIControl, AnyContainer]


class Layout:
    """
    The layout for a prompt_toolkit
    :class:`~prompt_toolkit.application.Application`.
    This also keeps track of which user control is focused.

    :param container: The "root" container for the layout.
    :param focused_element: element to be focused initially. (Can be anything
        the `focus` function accepts.)
    """

    def __init__(
        self,
        container: AnyContainer,
        focused_element: FocusableElement | None = None,
    ) -> None:
        self.container = to_container(container)
        self._stack: list[Window] = []

        # Map search BufferControl back to the original BufferControl.
        # This is used to keep track of when exactly we are searching, and for
        # applying the search.
        # When a link exists in this dictionary, that means the search is
        # currently active.
        # Map: search_buffer_control -> original buffer control.
        self.search_links: dict[SearchBufferControl, BufferControl] = {}

        # Mapping that maps the children in the layout to their parent.
        # This relationship is calculated dynamically, each time when the UI
        # is rendered.  (UI elements have only references to their children.)
        self._child_to_parent: dict[Container, Container] = {}

        if focused_element is None:
            try:
                self._stack.append(next(self.find_all_windows()))
            except StopIteration as e:
                raise InvalidLayoutError(
                    "Invalid layout. The layout does not contain any Window object."
                ) from e
        else:
            self.focus(focused_element)

        # List of visible windows.
        self.visible_windows: list[Window] = []  # List of `Window` objects.

    def __repr__(self) -> str:
        return f"Layout({self.container!r}, current_window={self.current_window!r})"

    def find_all_windows(self) -> Generator[Window, None, None]:
        """
        Find all the :class:`.UIControl` objects in this layout.
        """
        for item in self.walk():
            if isinstance(item, Window):
                yield item

    def find_all_controls(self) -> Iterable[UIControl]:
        for container in self.find_all_windows():
            yield container.content

    def focus(self, value: FocusableElement) -> None:
        """
        Focus the given UI element.

        `value` can be either:

        - a :class:`.UIControl`
        - a :class:`.Buffer` instance or the name of a :class:`.Buffer`
        - a :class:`.Window`
        - Any container object. In this case we will focus the :class:`.Window`
          from this container that was focused most recent, or the very first
          focusable :class:`.Window` of the container.
        """
        # BufferControl by buffer name.
        if isinstance(value, str):
            for control in self.find_all_controls():
                if isinstance(control, BufferControl) and control.buffer.name == value:
                    self.focus(control)
                    return
            raise ValueError(f"Couldn't find Buffer in the current layout: {value!r}.")

        # BufferControl by buffer object.
        elif isinstance(value, Buffer):
            for control in self.find_all_controls():
                if isinstance(control, BufferControl) and control.buffer == value:
                    self.focus(control)
                    return
            raise ValueError(f"Couldn't find Buffer in the current layout: {value!r}.")

        # Focus UIControl.
        elif isinstance(value, UIControl):
            if value not in self.find_all_controls():
                raise ValueError(
                    "Invalid value. Container does not appear in the layout."
                )
            if not value.is_focusable():
                raise ValueError("Invalid value. UIControl is not focusable.")

            self.current_control = value

        # Otherwise, expecting any Container object.
        else:
            value = to_container(value)

            if isinstance(value, Window):
                # This is a `Window`: focus that.
                if value not in self.find_all_windows():
                    raise ValueError(
                        f"Invalid value. Window does not appear in the layout: {value!r}"
                    )

                self.current_window = value
            else:
                # Focus a window in this container.
                # If we have many windows as part of this container, and some
                # of them have been focused before, take the last focused
                # item. (This is very useful when the UI is composed of more
                # complex sub components.)
                windows = []
                for c in walk(value, skip_hidden=True):
                    if isinstance(c, Window) and c.content.is_focusable():
                        windows.append(c)

                # Take the first one that was focused before.
                for w in reversed(self._stack):
                    if w in windows:
                        self.current_window = w
                        return

                # None was focused before: take the very first focusable window.
                if windows:
                    self.current_window = windows[0]
                    return

                raise ValueError(
                    f"Invalid value. Container cannot be focused: {value!r}"
                )

    def has_focus(self, value: FocusableElement) -> bool:
        """
        Check whether the given control has the focus.
        :param value: :class:`.UIControl` or :class:`.Window` instance.
        """
        if isinstance(value, str):
            if self.current_buffer is None:
                return False
            return self.current_buffer.name == value
        if isinstance(value, Buffer):
            return self.current_buffer == value
        if isinstance(value, UIControl):
            return self.current_control == value
        else:
            value = to_container(value)
            if isinstance(value, Window):
                return self.current_window == value
            else:
                # Check whether this "container" is focused. This is true if
                # one of the elements inside is focused.
                for element in walk(value):
                    if element == self.current_window:
                        return True
                return False

    @property
    def current_control(self) -> UIControl:
        """
        Get the :class:`.UIControl` to currently has the focus.
        """
        return self._stack[-1].content

    @current_control.setter
    def current_control(self, control: UIControl) -> None:
        """
        Set the :class:`.UIControl` to receive the focus.
        """
        for window in self.find_all_windows():
            if window.content == control:
                self.current_window = window
                return

        raise ValueError("Control not found in the user interface.")

    @property
    def current_window(self) -> Window:
        "Return the :class:`.Window` object that is currently focused."
        return self._stack[-1]

    @current_window.setter
    def current_window(self, value: Window) -> None:
        "Set the :class:`.Window` object to be currently focused."
        self._stack.append(value)

    @property
    def is_searching(self) -> bool:
        "True if we are searching right now."
        return self.current_control in self.search_links

    @property
    def search_target_buffer_control(self) -> BufferControl | None:
        """
        Return the :class:`.BufferControl` in which we are searching or `None`.
        """
        # Not every `UIControl` is a `BufferControl`. This only applies to
        # `BufferControl`.
        control = self.current_control

        if isinstance(control, SearchBufferControl):
            return self.search_links.get(control)
        else:
            return None

    def get_focusable_windows(self) -> Iterable[Window]:
        """
        Return all the :class:`.Window` objects which are focusable (in the
        'modal' area).
        """
        for w in self.walk_through_modal_area():
            if isinstance(w, Window) and w.content.is_focusable():
                yield w

    def get_visible_focusable_windows(self) -> list[Window]:
        """
        Return a list of :class:`.Window` objects that are focusable.
        """
        # focusable windows are windows that are visible, but also part of the
        # modal container. Make sure to keep the ordering.
        visible_windows = self.visible_windows
        return [w for w in self.get_focusable_windows() if w in visible_windows]

    @property
    def current_buffer(self) -> Buffer | None:
        """
        The currently focused :class:`~.Buffer` or `None`.
        """
        ui_control = self.current_control
        if isinstance(ui_control, BufferControl):
            return ui_control.buffer
        return None

    def get_buffer_by_name(self, buffer_name: str) -> Buffer | None:
        """
        Look in the layout for a buffer with the given name.
        Return `None` when nothing was found.
        """
        for w in self.walk():
            if isinstance(w, Window) and isinstance(w.content, BufferControl):
                if w.content.buffer.name == buffer_name:
                    return w.content.buffer
        return None

    @property
    def buffer_has_focus(self) -> bool:
        """
        Return `True` if the currently focused control is a
        :class:`.BufferControl`. (For instance, used to determine whether the
        default key bindings should be active or not.)
        """
        ui_control = self.current_control
        return isinstance(ui_control, BufferControl)

    @property
    def previous_control(self) -> UIControl:
        """
        Get the :class:`.UIControl` to previously had the focus.
        """
        try:
            return self._stack[-2].content
        except IndexError:
            return self._stack[-1].content

    def focus_last(self) -> None:
        """
        Give the focus to the last focused control.
        """
        if len(self._stack) > 1:
            self._stack = self._stack[:-1]

    def focus_next(self) -> None:
        """
        Focus the next visible/focusable Window.
        """
        windows = self.get_visible_focusable_windows()

        if len(windows) > 0:
            try:
                index = windows.index(self.current_window)
            except ValueError:
                index = 0
            else:
                index = (index + 1) % len(windows)

            self.focus(windows[index])

    def focus_previous(self) -> None:
        """
        Focus the previous visible/focusable Window.
        """
        windows = self.get_visible_focusable_windows()

        if len(windows) > 0:
            try:
                index = windows.index(self.current_window)
            except ValueError:
                index = 0
            else:
                index = (index - 1) % len(windows)

            self.focus(windows[index])

    def walk(self) -> Iterable[Container]:
        """
        Walk through all the layout nodes (and their children) and yield them.
        """
        yield from walk(self.container)

    def walk_through_modal_area(self) -> Iterable[Container]:
        """
        Walk through all the containers which are in the current 'modal' part
        of the layout.
        """
        # Go up in the tree, and find the root. (it will be a part of the
        # layout, if the focus is in a modal part.)
        root: Container = self.current_window
        while not root.is_modal() and root in self._child_to_parent:
            root = self._child_to_parent[root]

        yield from walk(root)

    def update_parents_relations(self) -> None:
        """
        Update child->parent relationships mapping.
        """
        parents = {}

        def walk(e: Container) -> None:
            for c in e.get_children():
                parents[c] = e
                walk(c)

        walk(self.container)

        self._child_to_parent = parents

    def reset(self) -> None:
        # Remove all search links when the UI starts.
        # (Important, for instance when control-c is been pressed while
        #  searching. The prompt cancels, but next `run()` call the search
        #  links are still there.)
        self.search_links.clear()

        self.container.reset()

    def get_parent(self, container: Container) -> Container | None:
        """
        Return the parent container for the given container, or ``None``, if it
        wasn't found.
        """
        try:
            return self._child_to_parent[container]
        except KeyError:
            return None


class InvalidLayoutError(Exception):
    pass


def walk(container: Container, skip_hidden: bool = False) -> Iterable[Container]:
    """
    Walk through layout, starting at this container.
    """
    # When `skip_hidden` is set, don't go into disabled ConditionalContainer containers.
    if (
        skip_hidden
        and isinstance(container, ConditionalContainer)
        and not container.filter()
    ):
        return

    yield container

    for c in container.get_children():
        # yield from walk(c)
        yield from walk(c, skip_hidden=skip_hidden)

# === NexusCore/openenv\Lib\site-packages\PIL\IcnsImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# macOS icns file decoder, based on icns.py by Bob Ippolito.
#
# history:
# 2004-10-09 fl   Turned into a PIL plugin; removed 2.3 dependencies.
# 2020-04-04      Allow saving on all operating systems.
#
# Copyright (c) 2004 by Bob Ippolito.
# Copyright (c) 2004 by Secret Labs.
# Copyright (c) 2004 by Fredrik Lundh.
# Copyright (c) 2014 by Alastair Houghton.
# Copyright (c) 2020 by Pan Jing.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
import os
import struct
import sys
from typing import IO

from . import Image, ImageFile, PngImagePlugin, features
from ._deprecate import deprecate

enable_jpeg2k = features.check_codec("jpg_2000")
if enable_jpeg2k:
    from . import Jpeg2KImagePlugin

MAGIC = b"icns"
HEADERSIZE = 8


def nextheader(fobj: IO[bytes]) -> tuple[bytes, int]:
    return struct.unpack(">4sI", fobj.read(HEADERSIZE))


def read_32t(
    fobj: IO[bytes], start_length: tuple[int, int], size: tuple[int, int, int]
) -> dict[str, Image.Image]:
    # The 128x128 icon seems to have an extra header for some reason.
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(4)
    if sig != b"\x00\x00\x00\x00":
        msg = "Unknown signature, expecting 0x00000000"
        raise SyntaxError(msg)
    return read_32(fobj, (start + 4, length - 4), size)


def read_32(
    fobj: IO[bytes], start_length: tuple[int, int], size: tuple[int, int, int]
) -> dict[str, Image.Image]:
    """
    Read a 32bit RGB icon resource.  Seems to be either uncompressed or
    an RLE packbits-like scheme.
    """
    (start, length) = start_length
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    if length == sizesq * 3:
        # uncompressed ("RGBRGBGB")
        indata = fobj.read(length)
        im = Image.frombuffer("RGB", pixel_size, indata, "raw", "RGB", 0, 1)
    else:
        # decode image
        im = Image.new("RGB", pixel_size, None)
        for band_ix in range(3):
            data = []
            bytesleft = sizesq
            while bytesleft > 0:
                byte = fobj.read(1)
                if not byte:
                    break
                byte_int = byte[0]
                if byte_int & 0x80:
                    blocksize = byte_int - 125
                    byte = fobj.read(1)
                    for i in range(blocksize):
                        data.append(byte)
                else:
                    blocksize = byte_int + 1
                    data.append(fobj.read(blocksize))
                bytesleft -= blocksize
                if bytesleft <= 0:
                    break
            if bytesleft != 0:
                msg = f"Error reading channel [{repr(bytesleft)} left]"
                raise SyntaxError(msg)
            band = Image.frombuffer("L", pixel_size, b"".join(data), "raw", "L", 0, 1)
            im.im.putband(band.im, band_ix)
    return {"RGB": im}


def read_mk(
    fobj: IO[bytes], start_length: tuple[int, int], size: tuple[int, int, int]
) -> dict[str, Image.Image]:
    # Alpha masks seem to be uncompressed
    start = start_length[0]
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    band = Image.frombuffer("L", pixel_size, fobj.read(sizesq), "raw", "L", 0, 1)
    return {"A": band}


def read_png_or_jpeg2000(
    fobj: IO[bytes], start_length: tuple[int, int], size: tuple[int, int, int]
) -> dict[str, Image.Image]:
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(12)

    im: Image.Image
    if sig.startswith(b"\x89PNG\x0d\x0a\x1a\x0a"):
        fobj.seek(start)
        im = PngImagePlugin.PngImageFile(fobj)
        Image._decompression_bomb_check(im.size)
        return {"RGBA": im}
    elif (
        sig.startswith((b"\xff\x4f\xff\x51", b"\x0d\x0a\x87\x0a"))
        or sig == b"\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a"
    ):
        if not enable_jpeg2k:
            msg = (
                "Unsupported icon subimage format (rebuild PIL "
                "with JPEG 2000 support to fix this)"
            )
            raise ValueError(msg)
        # j2k, jpc or j2c
        fobj.seek(start)
        jp2kstream = fobj.read(length)
        f = io.BytesIO(jp2kstream)
        im = Jpeg2KImagePlugin.Jpeg2KImageFile(f)
        Image._decompression_bomb_check(im.size)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        return {"RGBA": im}
    else:
        msg = "Unsupported icon subimage format"
        raise ValueError(msg)


class IcnsFile:
    SIZES = {
        (512, 512, 2): [(b"ic10", read_png_or_jpeg2000)],
        (512, 512, 1): [(b"ic09", read_png_or_jpeg2000)],
        (256, 256, 2): [(b"ic14", read_png_or_jpeg2000)],
        (256, 256, 1): [(b"ic08", read_png_or_jpeg2000)],
        (128, 128, 2): [(b"ic13", read_png_or_jpeg2000)],
        (128, 128, 1): [
            (b"ic07", read_png_or_jpeg2000),
            (b"it32", read_32t),
            (b"t8mk", read_mk),
        ],
        (64, 64, 1): [(b"icp6", read_png_or_jpeg2000)],
        (32, 32, 2): [(b"ic12", read_png_or_jpeg2000)],
        (48, 48, 1): [(b"ih32", read_32), (b"h8mk", read_mk)],
        (32, 32, 1): [
            (b"icp5", read_png_or_jpeg2000),
            (b"il32", read_32),
            (b"l8mk", read_mk),
        ],
        (16, 16, 2): [(b"ic11", read_png_or_jpeg2000)],
        (16, 16, 1): [
            (b"icp4", read_png_or_jpeg2000),
            (b"is32", read_32),
            (b"s8mk", read_mk),
        ],
    }

    def __init__(self, fobj: IO[bytes]) -> None:
        """
        fobj is a file-like object as an icns resource
        """
        # signature : (start, length)
        self.dct = {}
        self.fobj = fobj
        sig, filesize = nextheader(fobj)
        if not _accept(sig):
            msg = "not an icns file"
            raise SyntaxError(msg)
        i = HEADERSIZE
        while i < filesize:
            sig, blocksize = nextheader(fobj)
            if blocksize <= 0:
                msg = "invalid block header"
                raise SyntaxError(msg)
            i += HEADERSIZE
            blocksize -= HEADERSIZE
            self.dct[sig] = (i, blocksize)
            fobj.seek(blocksize, io.SEEK_CUR)
            i += blocksize

    def itersizes(self) -> list[tuple[int, int, int]]:
        sizes = []
        for size, fmts in self.SIZES.items():
            for fmt, reader in fmts:
                if fmt in self.dct:
                    sizes.append(size)
                    break
        return sizes

    def bestsize(self) -> tuple[int, int, int]:
        sizes = self.itersizes()
        if not sizes:
            msg = "No 32bit icon resources found"
            raise SyntaxError(msg)
        return max(sizes)

    def dataforsize(self, size: tuple[int, int, int]) -> dict[str, Image.Image]:
        """
        Get an icon resource as {channel: array}.  Note that
        the arrays are bottom-up like windows bitmaps and will likely
        need to be flipped or transposed in some way.
        """
        dct = {}
        for code, reader in self.SIZES[size]:
            desc = self.dct.get(code)
            if desc is not None:
                dct.update(reader(self.fobj, desc, size))
        return dct

    def getimage(
        self, size: tuple[int, int] | tuple[int, int, int] | None = None
    ) -> Image.Image:
        if size is None:
            size = self.bestsize()
        elif len(size) == 2:
            size = (size[0], size[1], 1)
        channels = self.dataforsize(size)

        im = channels.get("RGBA")
        if im:
            return im

        im = channels["RGB"].copy()
        try:
            im.putalpha(channels["A"])
        except KeyError:
            pass
        return im


##
# Image plugin for Mac OS icons.


class IcnsImageFile(ImageFile.ImageFile):
    """
    PIL image support for Mac OS .icns files.
    Chooses the best resolution, but will possibly load
    a different size image if you mutate the size attribute
    before calling 'load'.

    The info dictionary has a key 'sizes' that is a list
    of sizes that the icns file has.
    """

    format = "ICNS"
    format_description = "Mac OS icns resource"

    def _open(self) -> None:
        self.icns = IcnsFile(self.fp)
        self._mode = "RGBA"
        self.info["sizes"] = self.icns.itersizes()
        self.best_size = self.icns.bestsize()
        self.size = (
            self.best_size[0] * self.best_size[2],
            self.best_size[1] * self.best_size[2],
        )

    @property  # type: ignore[override]
    def size(self) -> tuple[int, int] | tuple[int, int, int]:
        return self._size

    @size.setter
    def size(self, value: tuple[int, int] | tuple[int, int, int]) -> None:
        if len(value) == 3:
            deprecate("Setting size to (width, height, scale)", 12, "load(scale)")
            if value in self.info["sizes"]:
                self._size = value  # type: ignore[assignment]
                return
        else:
            # Check that a matching size exists,
            # or that there is a scale that would create a size that matches
            for size in self.info["sizes"]:
                simple_size = size[0] * size[2], size[1] * size[2]
                scale = simple_size[0] // value[0]
                if simple_size[1] / value[1] == scale:
                    self._size = value
                    return
        msg = "This is not one of the allowed sizes of this image"
        raise ValueError(msg)

    def load(self, scale: int | None = None) -> Image.core.PixelAccess | None:
        if scale is not None or len(self.size) == 3:
            if scale is None and len(self.size) == 3:
                scale = self.size[2]
            assert scale is not None
            width, height = self.size[:2]
            self.size = width * scale, height * scale
            self.best_size = width, height, scale

        px = Image.Image.load(self)
        if self._im is not None and self.im.size == self.size:
            # Already loaded
            return px
        self.load_prepare()
        # This is likely NOT the best way to do it, but whatever.
        im = self.icns.getimage(self.best_size)

        # If this is a PNG or JPEG 2000, it won't be loaded yet
        px = im.load()

        self.im = im.im
        self._mode = im.mode
        self.size = im.size

        return px


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    """
    Saves the image as a series of PNG files,
    that are then combined into a .icns file.
    """
    if hasattr(fp, "flush"):
        fp.flush()

    sizes = {
        b"ic07": 128,
        b"ic08": 256,
        b"ic09": 512,
        b"ic10": 1024,
        b"ic11": 32,
        b"ic12": 64,
        b"ic13": 256,
        b"ic14": 512,
    }
    provided_images = {im.width: im for im in im.encoderinfo.get("append_images", [])}
    size_streams = {}
    for size in set(sizes.values()):
        image = (
            provided_images[size]
            if size in provided_images
            else im.resize((size, size))
        )

        temp = io.BytesIO()
        image.save(temp, "png")
        size_streams[size] = temp.getvalue()

    entries = []
    for type, size in sizes.items():
        stream = size_streams[size]
        entries.append((type, HEADERSIZE + len(stream), stream))

    # Header
    fp.write(MAGIC)
    file_length = HEADERSIZE  # Header
    file_length += HEADERSIZE + 8 * len(entries)  # TOC
    file_length += sum(entry[1] for entry in entries)
    fp.write(struct.pack(">i", file_length))

    # TOC
    fp.write(b"TOC ")
    fp.write(struct.pack(">i", HEADERSIZE + len(entries) * HEADERSIZE))
    for entry in entries:
        fp.write(entry[0])
        fp.write(struct.pack(">i", entry[1]))

    # Data
    for entry in entries:
        fp.write(entry[0])
        fp.write(struct.pack(">i", entry[1]))
        fp.write(entry[2])

    if hasattr(fp, "flush"):
        fp.flush()


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(MAGIC)


Image.register_open(IcnsImageFile.format, IcnsImageFile, _accept)
Image.register_extension(IcnsImageFile.format, ".icns")

Image.register_save(IcnsImageFile.format, _save)
Image.register_mime(IcnsImageFile.format, "image/icns")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Syntax: python3 IcnsImagePlugin.py [file]")
        sys.exit()

    with open(sys.argv[1], "rb") as fp:
        imf = IcnsImageFile(fp)
        for size in imf.info["sizes"]:
            width, height, scale = imf.size = size
            imf.save(f"out-{width}-{height}-{scale}.png")
        with Image.open(sys.argv[1]) as im:
            im.save("out.png")
        if sys.platform == "windows":
            os.startfile("out.png")

# === NexusCore/openenv\Lib\site-packages\debugpy\common\log.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import atexit
import contextlib
import functools
import inspect
import io
import os
import platform
import sys
import threading
import traceback

import debugpy
from debugpy.common import json, timestamp, util


LEVELS = ("debug", "info", "warning", "error")
"""Logging levels, lowest to highest importance.
"""

log_dir = os.getenv("DEBUGPY_LOG_DIR")
"""If not None, debugger logs its activity to a file named debugpy.*-<pid>.log
in the specified directory, where <pid> is the return value of os.getpid().
"""

timestamp_format = "09.3f"
"""Format spec used for timestamps. Can be changed to dial precision up or down.
"""

_lock = threading.RLock()
_tls = threading.local()
_files = {}  # filename -> LogFile
_levels = set()  # combined for all log files


def _update_levels():
    global _levels
    _levels = frozenset(level for file in _files.values() for level in file.levels)


class LogFile(object):
    def __init__(self, filename, file, levels=LEVELS, close_file=True):
        info("Also logging to {0}.", json.repr(filename))
        self.filename = filename
        self.file = file
        self.close_file = close_file
        self._levels = frozenset(levels)

        with _lock:
            _files[self.filename] = self
            _update_levels()
            info(
                "{0} {1}\n{2} {3} ({4}-bit)\ndebugpy {5}",
                platform.platform(),
                platform.machine(),
                platform.python_implementation(),
                platform.python_version(),
                64 if sys.maxsize > 2**32 else 32,
                debugpy.__version__,
                _to_files=[self],
            )

    @property
    def levels(self):
        return self._levels

    @levels.setter
    def levels(self, value):
        with _lock:
            self._levels = frozenset(LEVELS if value is all else value)
            _update_levels()

    def write(self, level, output):
        if level in self.levels:
            try:
                self.file.write(output)
                self.file.flush()
            except Exception:  # pragma: no cover
                pass

    def close(self):
        with _lock:
            del _files[self.filename]
            _update_levels()
        info("Not logging to {0} anymore.", json.repr(self.filename))

        if self.close_file:
            try:
                self.file.close()
            except Exception:  # pragma: no cover
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class NoLog(object):
    file = filename = None

    __bool__ = __nonzero__ = lambda self: False

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Used to inject a newline into stderr if logging there, to clean up the output
# when it's intermixed with regular prints from other sources.
def newline(level="info"):
    with _lock:
        stderr.write(level, "\n")


def write(level, text, _to_files=all):
    assert level in LEVELS

    t = timestamp.current()
    format_string = "{0}+{1:" + timestamp_format + "}: "
    prefix = format_string.format(level[0].upper(), t)

    text = getattr(_tls, "prefix", "") + text
    indent = "\n" + (" " * len(prefix))
    output = indent.join(text.split("\n"))
    output = prefix + output + "\n\n"

    with _lock:
        if _to_files is all:
            _to_files = _files.values()
        for file in _to_files:
            file.write(level, output)

    return text


def write_format(level, format_string, *args, **kwargs):
    # Don't spend cycles doing expensive formatting if we don't have to. Errors are
    # always formatted, so that error() can return the text even if it's not logged.
    if level != "error" and level not in _levels:
        return

    try:
        text = format_string.format(*args, **kwargs)
    except Exception:  # pragma: no cover
        reraise_exception()

    return write(level, text, kwargs.pop("_to_files", all))


debug = functools.partial(write_format, "debug")
info = functools.partial(write_format, "info")
warning = functools.partial(write_format, "warning")


def error(*args, **kwargs):
    """Logs an error.

    Returns the output wrapped in AssertionError. Thus, the following::

        raise log.error(s, ...)

    has the same effect as::

        log.error(...)
        assert False, (s.format(...))
    """
    return AssertionError(write_format("error", *args, **kwargs))


def _exception(format_string="", *args, **kwargs):
    level = kwargs.pop("level", "error")
    exc_info = kwargs.pop("exc_info", sys.exc_info())

    if format_string:
        format_string += "\n\n"
    format_string += "{exception}\nStack where logged:\n{stack}"

    exception = "".join(traceback.format_exception(*exc_info))

    f = inspect.currentframe()
    f = f.f_back if f else f  # don't log this frame
    try:
        stack = "".join(traceback.format_stack(f))
    finally:
        del f  # avoid cycles

    write_format(
        level, format_string, *args, exception=exception, stack=stack, **kwargs
    )


def swallow_exception(format_string="", *args, **kwargs):
    """Logs an exception with full traceback.

    If format_string is specified, it is formatted with format(*args, **kwargs), and
    prepended to the exception traceback on a separate line.

    If exc_info is specified, the exception it describes will be logged. Otherwise,
    sys.exc_info() - i.e. the exception being handled currently - will be logged.

    If level is specified, the exception will be logged as a message of that level.
    The default is "error".
    """

    _exception(format_string, *args, **kwargs)


def reraise_exception(format_string="", *args, **kwargs):
    """Like swallow_exception(), but re-raises the current exception after logging it."""

    assert "exc_info" not in kwargs
    _exception(format_string, *args, **kwargs)
    raise


def to_file(filename=None, prefix=None, levels=LEVELS):
    """Starts logging all messages at the specified levels to the designated file.

    Either filename or prefix must be specified, but not both.

    If filename is specified, it designates the log file directly.

    If prefix is specified, the log file is automatically created in options.log_dir,
    with filename computed as prefix + os.getpid(). If log_dir is None, no log file
    is created, and the function returns immediately.

    If the file with the specified or computed name is already being used as a log
    file, it is not overwritten, but its levels are updated as specified.

    The function returns an object with a close() method. When the object is closed,
    logs are not written into that file anymore. Alternatively, the returned object
    can be used in a with-statement:

        with log.to_file("some.log"):
            # now also logging to some.log
        # not logging to some.log anymore
    """

    assert (filename is not None) ^ (prefix is not None)

    if filename is None:
        if log_dir is None:
            return NoLog()
        try:
            os.makedirs(log_dir)
        except OSError:  # pragma: no cover
            pass
        filename = f"{log_dir}/{prefix}-{os.getpid()}.log"

    file = _files.get(filename)
    if file is None:
        file = LogFile(filename, io.open(filename, "w", encoding="utf-8"), levels)
    else:
        file.levels = levels
    return file


@contextlib.contextmanager
def prefixed(format_string, *args, **kwargs):
    """Adds a prefix to all messages logged from the current thread for the duration
    of the context manager.
    """
    prefix = format_string.format(*args, **kwargs)
    old_prefix = getattr(_tls, "prefix", "")
    _tls.prefix = prefix + old_prefix
    try:
        yield
    finally:
        _tls.prefix = old_prefix


def get_environment_description(header):
    import sysconfig
    import site  # noqa

    result = [header, "\n\n"]

    def report(s, *args, **kwargs):
        result.append(s.format(*args, **kwargs))

    def report_paths(get_paths, label=None):
        prefix = f"    {label or get_paths}: "

        expr = None
        if not callable(get_paths):
            expr = get_paths
            get_paths = lambda: util.evaluate(expr)
        try:
            paths = get_paths()
        except AttributeError:
            report("{0}<missing>\n", prefix)
            return
        except Exception:  # pragma: no cover
            swallow_exception(
                "Error evaluating {0}",
                repr(expr) if expr else util.srcnameof(get_paths),
                level="info",
            )
            return

        if not isinstance(paths, (list, tuple)):
            paths = [paths]

        for p in sorted(paths):
            report("{0}{1}", prefix, p)
            if p is not None:
                rp = os.path.realpath(p)
                if p != rp:
                    report("({0})", rp)
            report("\n")

            prefix = " " * len(prefix)

    report("System paths:\n")
    report_paths("sys.executable")
    report_paths("sys.prefix")
    report_paths("sys.base_prefix")
    report_paths("sys.real_prefix")
    report_paths("site.getsitepackages()")
    report_paths("site.getusersitepackages()")

    site_packages = [
        p
        for p in sys.path
        if os.path.exists(p) and os.path.basename(p) == "site-packages"
    ]
    report_paths(lambda: site_packages, "sys.path (site-packages)")

    for name in sysconfig.get_path_names():
        expr = "sysconfig.get_path({0!r})".format(name)
        report_paths(expr)

    report_paths("os.__file__")
    report_paths("threading.__file__")
    report_paths("debugpy.__file__")
    report("\n")

    importlib_metadata = None
    try:
        import importlib_metadata
    except ImportError:  # pragma: no cover
        try:
            from importlib import metadata as importlib_metadata
        except ImportError:
            pass
    if importlib_metadata is None:  # pragma: no cover
        report("Cannot enumerate installed packages - missing importlib_metadata.")
    else:
        report("Installed packages:\n")
        try:
            for pkg in importlib_metadata.distributions():
                report("    {0}=={1}\n", pkg.name, pkg.version)
        except Exception:  # pragma: no cover
            swallow_exception(
                "Error while enumerating installed packages.", level="info"
            )

    return "".join(result).rstrip("\n")


def describe_environment(header):
    info("{0}", get_environment_description(header))


stderr = LogFile(
    "<stderr>",
    sys.stderr,
    levels=os.getenv("DEBUGPY_LOG_STDERR", "warning error").split(),
    close_file=False,
)


@atexit.register
def _close_files():
    for file in tuple(_files.values()):
        file.close()


# The following are helper shortcuts for printf debugging. They must never be used
# in production code.


def _repr(value):  # pragma: no cover
    warning("$REPR {0!r}", value)


def _vars(*names):  # pragma: no cover
    locals = inspect.currentframe().f_back.f_locals
    if names:
        locals = {name: locals[name] for name in names if name in locals}
    warning("$VARS {0!r}", locals)


def _stack():  # pragma: no cover
    stack = "\n".join(traceback.format_stack())
    warning("$STACK:\n\n{0}", stack)


def _threads():  # pragma: no cover
    output = "\n".join([str(t) for t in threading.enumerate()])
    warning("$THREADS:\n\n{0}", output)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\retriever.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import timestamp_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "Corpus",
        "Document",
        "StringList",
        "CustomMetadata",
        "MetadataFilter",
        "Condition",
        "Chunk",
        "ChunkData",
    },
)


class Corpus(proto.Message):
    r"""A ``Corpus`` is a collection of ``Document``\ s. A project can
    create up to 5 corpora.

    Attributes:
        name (str):
            Immutable. Identifier. The ``Corpus`` resource name. The ID
            (name excluding the "corpora/" prefix) can contain up to 40
            characters that are lowercase alphanumeric or dashes (-).
            The ID cannot start or end with a dash. If the name is empty
            on create, a unique name will be derived from
            ``display_name`` along with a 12 character random suffix.
            Example: ``corpora/my-awesome-corpora-123a456b789c``
        display_name (str):
            Optional. The human-readable display name for the
            ``Corpus``. The display name must be no more than 512
            characters in length, including spaces. Example: "Docs on
            Semantic Retriever".
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Corpus`` was
            created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Corpus`` was last
            updated.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=2,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=3,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=4,
        message=timestamp_pb2.Timestamp,
    )


class Document(proto.Message):
    r"""A ``Document`` is a collection of ``Chunk``\ s. A ``Corpus`` can
    have a maximum of 10,000 ``Document``\ s.

    Attributes:
        name (str):
            Immutable. Identifier. The ``Document`` resource name. The
            ID (name excluding the `corpora/*/documents/` prefix) can
            contain up to 40 characters that are lowercase alphanumeric
            or dashes (-). The ID cannot start or end with a dash. If
            the name is empty on create, a unique name will be derived
            from ``display_name`` along with a 12 character random
            suffix. Example:
            ``corpora/{corpus_id}/documents/my-awesome-doc-123a456b789c``
        display_name (str):
            Optional. The human-readable display name for the
            ``Document``. The display name must be no more than 512
            characters in length, including spaces. Example: "Semantic
            Retriever Documentation".
        custom_metadata (MutableSequence[google.ai.generativelanguage_v1beta.types.CustomMetadata]):
            Optional. User provided custom metadata stored as key-value
            pairs used for querying. A ``Document`` can have a maximum
            of 20 ``CustomMetadata``.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Document`` was last
            updated.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Document`` was
            created.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=2,
    )
    custom_metadata: MutableSequence["CustomMetadata"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="CustomMetadata",
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=4,
        message=timestamp_pb2.Timestamp,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=5,
        message=timestamp_pb2.Timestamp,
    )


class StringList(proto.Message):
    r"""User provided string values assigned to a single metadata
    key.

    Attributes:
        values (MutableSequence[str]):
            The string values of the metadata to store.
    """

    values: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=1,
    )


class CustomMetadata(proto.Message):
    r"""User provided metadata stored as key-value pairs.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        string_value (str):
            The string value of the metadata to store.

            This field is a member of `oneof`_ ``value``.
        string_list_value (google.ai.generativelanguage_v1beta.types.StringList):
            The StringList value of the metadata to
            store.

            This field is a member of `oneof`_ ``value``.
        numeric_value (float):
            The numeric value of the metadata to store.

            This field is a member of `oneof`_ ``value``.
        key (str):
            Required. The key of the metadata to store.
    """

    string_value: str = proto.Field(
        proto.STRING,
        number=2,
        oneof="value",
    )
    string_list_value: "StringList" = proto.Field(
        proto.MESSAGE,
        number=6,
        oneof="value",
        message="StringList",
    )
    numeric_value: float = proto.Field(
        proto.FLOAT,
        number=7,
        oneof="value",
    )
    key: str = proto.Field(
        proto.STRING,
        number=1,
    )


class MetadataFilter(proto.Message):
    r"""User provided filter to limit retrieval based on ``Chunk`` or
    ``Document`` level metadata values. Example (genre = drama OR genre
    = action): key = "document.custom_metadata.genre" conditions =
    [{string_value = "drama", operation = EQUAL}, {string_value =
    "action", operation = EQUAL}]

    Attributes:
        key (str):
            Required. The key of the metadata to filter
            on.
        conditions (MutableSequence[google.ai.generativelanguage_v1beta.types.Condition]):
            Required. The ``Condition``\ s for the given key that will
            trigger this filter. Multiple ``Condition``\ s are joined by
            logical ORs.
    """

    key: str = proto.Field(
        proto.STRING,
        number=1,
    )
    conditions: MutableSequence["Condition"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="Condition",
    )


class Condition(proto.Message):
    r"""Filter condition applicable to a single key.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        string_value (str):
            The string value to filter the metadata on.

            This field is a member of `oneof`_ ``value``.
        numeric_value (float):
            The numeric value to filter the metadata on.

            This field is a member of `oneof`_ ``value``.
        operation (google.ai.generativelanguage_v1beta.types.Condition.Operator):
            Required. Operator applied to the given
            key-value pair to trigger the condition.
    """

    class Operator(proto.Enum):
        r"""Defines the valid operators that can be applied to a
        key-value pair.

        Values:
            OPERATOR_UNSPECIFIED (0):
                The default value. This value is unused.
            LESS (1):
                Supported by numeric.
            LESS_EQUAL (2):
                Supported by numeric.
            EQUAL (3):
                Supported by numeric & string.
            GREATER_EQUAL (4):
                Supported by numeric.
            GREATER (5):
                Supported by numeric.
            NOT_EQUAL (6):
                Supported by numeric & string.
            INCLUDES (7):
                Supported by string only when ``CustomMetadata`` value type
                for the given key has a ``string_list_value``.
            EXCLUDES (8):
                Supported by string only when ``CustomMetadata`` value type
                for the given key has a ``string_list_value``.
        """
        OPERATOR_UNSPECIFIED = 0
        LESS = 1
        LESS_EQUAL = 2
        EQUAL = 3
        GREATER_EQUAL = 4
        GREATER = 5
        NOT_EQUAL = 6
        INCLUDES = 7
        EXCLUDES = 8

    string_value: str = proto.Field(
        proto.STRING,
        number=1,
        oneof="value",
    )
    numeric_value: float = proto.Field(
        proto.FLOAT,
        number=6,
        oneof="value",
    )
    operation: Operator = proto.Field(
        proto.ENUM,
        number=5,
        enum=Operator,
    )


class Chunk(proto.Message):
    r"""A ``Chunk`` is a subpart of a ``Document`` that is treated as an
    independent unit for the purposes of vector representation and
    storage. A ``Corpus`` can have a maximum of 1 million ``Chunk``\ s.

    Attributes:
        name (str):
            Immutable. Identifier. The ``Chunk`` resource name. The ID
            (name excluding the `corpora/*/documents/*/chunks/` prefix)
            can contain up to 40 characters that are lowercase
            alphanumeric or dashes (-). The ID cannot start or end with
            a dash. If the name is empty on create, a random
            12-character unique ID will be generated. Example:
            ``corpora/{corpus_id}/documents/{document_id}/chunks/123a456b789c``
        data (google.ai.generativelanguage_v1beta.types.ChunkData):
            Required. The content for the ``Chunk``, such as the text
            string. The maximum number of tokens per chunk is 2043.
        custom_metadata (MutableSequence[google.ai.generativelanguage_v1beta.types.CustomMetadata]):
            Optional. User provided custom metadata stored as key-value
            pairs. The maximum number of ``CustomMetadata`` per chunk is
            20.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Chunk`` was
            created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The Timestamp of when the ``Chunk`` was last
            updated.
        state (google.ai.generativelanguage_v1beta.types.Chunk.State):
            Output only. Current state of the ``Chunk``.
    """

    class State(proto.Enum):
        r"""States for the lifecycle of a ``Chunk``.

        Values:
            STATE_UNSPECIFIED (0):
                The default value. This value is used if the
                state is omitted.
            STATE_PENDING_PROCESSING (1):
                ``Chunk`` is being processed (embedding and vector storage).
            STATE_ACTIVE (2):
                ``Chunk`` is processed and available for querying.
            STATE_FAILED (10):
                ``Chunk`` failed processing.
        """
        STATE_UNSPECIFIED = 0
        STATE_PENDING_PROCESSING = 1
        STATE_ACTIVE = 2
        STATE_FAILED = 10

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    data: "ChunkData" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="ChunkData",
    )
    custom_metadata: MutableSequence["CustomMetadata"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="CustomMetadata",
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=4,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=5,
        message=timestamp_pb2.Timestamp,
    )
    state: State = proto.Field(
        proto.ENUM,
        number=6,
        enum=State,
    )


class ChunkData(proto.Message):
    r"""Extracted data that represents the ``Chunk`` content.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        string_value (str):
            The ``Chunk`` content as a string. The maximum number of
            tokens per chunk is 2043.

            This field is a member of `oneof`_ ``data``.
    """

    string_value: str = proto.Field(
        proto.STRING,
        number=1,
        oneof="data",
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\pagers.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta.types import retriever, retriever_service


class ListCorporaPager:
    """A pager for iterating through ``list_corpora`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListCorporaResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``corpora`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListCorpora`` requests and continue to iterate
    through the ``corpora`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListCorporaResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., retriever_service.ListCorporaResponse],
        request: retriever_service.ListCorporaRequest,
        response: retriever_service.ListCorporaResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListCorporaRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListCorporaResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListCorporaRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[retriever_service.ListCorporaResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[retriever.Corpus]:
        for page in self.pages:
            yield from page.corpora

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListCorporaAsyncPager:
    """A pager for iterating through ``list_corpora`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListCorporaResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``corpora`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListCorpora`` requests and continue to iterate
    through the ``corpora`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListCorporaResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[retriever_service.ListCorporaResponse]],
        request: retriever_service.ListCorporaRequest,
        response: retriever_service.ListCorporaResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListCorporaRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListCorporaResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListCorporaRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[retriever_service.ListCorporaResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[retriever.Corpus]:
        async def async_generator():
            async for page in self.pages:
                for response in page.corpora:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListDocumentsPager:
    """A pager for iterating through ``list_documents`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListDocumentsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``documents`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListDocuments`` requests and continue to iterate
    through the ``documents`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListDocumentsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., retriever_service.ListDocumentsResponse],
        request: retriever_service.ListDocumentsRequest,
        response: retriever_service.ListDocumentsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListDocumentsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListDocumentsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListDocumentsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[retriever_service.ListDocumentsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[retriever.Document]:
        for page in self.pages:
            yield from page.documents

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListDocumentsAsyncPager:
    """A pager for iterating through ``list_documents`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListDocumentsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``documents`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListDocuments`` requests and continue to iterate
    through the ``documents`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListDocumentsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[retriever_service.ListDocumentsResponse]],
        request: retriever_service.ListDocumentsRequest,
        response: retriever_service.ListDocumentsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListDocumentsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListDocumentsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListDocumentsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[retriever_service.ListDocumentsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[retriever.Document]:
        async def async_generator():
            async for page in self.pages:
                for response in page.documents:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListChunksPager:
    """A pager for iterating through ``list_chunks`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListChunksResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``chunks`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListChunks`` requests and continue to iterate
    through the ``chunks`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListChunksResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., retriever_service.ListChunksResponse],
        request: retriever_service.ListChunksRequest,
        response: retriever_service.ListChunksResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListChunksRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListChunksResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListChunksRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[retriever_service.ListChunksResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[retriever.Chunk]:
        for page in self.pages:
            yield from page.chunks

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListChunksAsyncPager:
    """A pager for iterating through ``list_chunks`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListChunksResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``chunks`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListChunks`` requests and continue to iterate
    through the ``chunks`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListChunksResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[retriever_service.ListChunksResponse]],
        request: retriever_service.ListChunksRequest,
        response: retriever_service.ListChunksResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListChunksRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListChunksResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = retriever_service.ListChunksRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[retriever_service.ListChunksResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[retriever.Chunk]:
        async def async_generator():
            async for page in self.pages:
                for response in page.chunks:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_julia_builtins.py ===
"""
    pygments.lexers._julia_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Julia builtins.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# operators
#   see https://github.com/JuliaLang/julia/blob/master/src/julia-parser.scm
# Julia v1.6.0-rc1
OPERATORS_LIST = [
    # other
    '->',
    # prec-assignment
    ':=', '$=',
    # prec-conditional, prec-lazy-or, prec-lazy-and
    '?', '||', '&&',
    # prec-colon
    ':',
    # prec-plus
    '$',
    # prec-decl
    '::',
]
DOTTED_OPERATORS_LIST = [
    # prec-assignment
    r'=', r'+=', r'-=', r'*=', r'/=', r'//=', r'\=', r'^=', r'÷=', r'%=', r'<<=',
    r'>>=', r'>>>=', r'|=', r'&=', r'⊻=', r'≔', r'⩴', r"≕'", r'~',
    # prec-pair
    '=>',
    # prec-arrow
    r'→', r'↔', r'↚', r'↛', r'↞', r'↠', r'↢', r'↣', r'↦', r'↤', r'↮', r'⇎', r'⇍', r'⇏',
    r'⇐', r'⇒', r'⇔', r'⇴', r'⇶', r'⇷', r'⇸', r'⇹', r'⇺', r'⇻', r'⇼', r'⇽', r'⇾', r'⇿',
    r'⟵', r'⟶', r'⟷', r'⟹', r'⟺', r'⟻', r'⟼', r'⟽', r'⟾', r'⟿', r'⤀', r'⤁', r'⤂', r'⤃',
    r'⤄', r'⤅', r'⤆', r'⤇', r'⤌', r'⤍', r'⤎', r'⤏', r'⤐', r'⤑', r'⤔', r'⤕', r'⤖', r'⤗',
    r'⤘', r'⤝', r'⤞', r'⤟', r'⤠', r'⥄', r'⥅', r'⥆', r'⥇', r'⥈', r'⥊', r'⥋', r'⥎', r'⥐',
    r'⥒', r'⥓', r'⥖', r'⥗', r'⥚', r'⥛', r'⥞', r'⥟', r'⥢', r'⥤', r'⥦', r'⥧', r'⥨', r'⥩',
    r'⥪', r'⥫', r'⥬', r'⥭', r'⥰', r'⧴', r'⬱', r'⬰', r'⬲', r'⬳', r'⬴', r'⬵', r'⬶', r'⬷',
    r'⬸', r'⬹', r'⬺', r'⬻', r'⬼', r'⬽', r'⬾', r'⬿', r'⭀', r'⭁', r'⭂', r'⭃', r'⭄', r'⭇',
    r'⭈', r'⭉', r'⭊', r'⭋', r'⭌', r'￩', r'￫', r'⇜', r'⇝', r'↜', r'↝', r'↩', r'↪', r'↫',
    r'↬', r'↼', r'↽', r'⇀', r'⇁', r'⇄', r'⇆', r'⇇', r'⇉', r'⇋', r'⇌', r'⇚', r'⇛', r'⇠',
    r'⇢', r'↷', r'↶', r'↺', r'↻', r'-->', r'<--', r'<-->',
    # prec-comparison
    r'>', r'<', r'>=', r'≥', r'<=', r'≤', r'==', r'===', r'≡', r'!=', r'≠', r'!==',
    r'≢', r'∈', r'∉', r'∋', r'∌', r'⊆', r'⊈', r'⊂', r'⊄', r'⊊', r'∝', r'∊', r'∍', r'∥',
    r'∦', r'∷', r'∺', r'∻', r'∽', r'∾', r'≁', r'≃', r'≂', r'≄', r'≅', r'≆', r'≇', r'≈',
    r'≉', r'≊', r'≋', r'≌', r'≍', r'≎', r'≐', r'≑', r'≒', r'≓', r'≖', r'≗', r'≘', r'≙',
    r'≚', r'≛', r'≜', r'≝', r'≞', r'≟', r'≣', r'≦', r'≧', r'≨', r'≩', r'≪', r'≫', r'≬',
    r'≭', r'≮', r'≯', r'≰', r'≱', r'≲', r'≳', r'≴', r'≵', r'≶', r'≷', r'≸', r'≹', r'≺',
    r'≻', r'≼', r'≽', r'≾', r'≿', r'⊀', r'⊁', r'⊃', r'⊅', r'⊇', r'⊉', r'⊋', r'⊏', r'⊐',
    r'⊑', r'⊒', r'⊜', r'⊩', r'⊬', r'⊮', r'⊰', r'⊱', r'⊲', r'⊳', r'⊴', r'⊵', r'⊶', r'⊷',
    r'⋍', r'⋐', r'⋑', r'⋕', r'⋖', r'⋗', r'⋘', r'⋙', r'⋚', r'⋛', r'⋜', r'⋝', r'⋞', r'⋟',
    r'⋠', r'⋡', r'⋢', r'⋣', r'⋤', r'⋥', r'⋦', r'⋧', r'⋨', r'⋩', r'⋪', r'⋫', r'⋬', r'⋭',
    r'⋲', r'⋳', r'⋴', r'⋵', r'⋶', r'⋷', r'⋸', r'⋹', r'⋺', r'⋻', r'⋼', r'⋽', r'⋾', r'⋿',
    r'⟈', r'⟉', r'⟒', r'⦷', r'⧀', r'⧁', r'⧡', r'⧣', r'⧤', r'⧥', r'⩦', r'⩧', r'⩪', r'⩫',
    r'⩬', r'⩭', r'⩮', r'⩯', r'⩰', r'⩱', r'⩲', r'⩳', r'⩵', r'⩶', r'⩷', r'⩸', r'⩹', r'⩺',
    r'⩻', r'⩼', r'⩽', r'⩾', r'⩿', r'⪀', r'⪁', r'⪂', r'⪃', r'⪄', r'⪅', r'⪆', r'⪇', r'⪈',
    r'⪉', r'⪊', r'⪋', r'⪌', r'⪍', r'⪎', r'⪏', r'⪐', r'⪑', r'⪒', r'⪓', r'⪔', r'⪕', r'⪖',
    r'⪗', r'⪘', r'⪙', r'⪚', r'⪛', r'⪜', r'⪝', r'⪞', r'⪟', r'⪠', r'⪡', r'⪢', r'⪣', r'⪤',
    r'⪥', r'⪦', r'⪧', r'⪨', r'⪩', r'⪪', r'⪫', r'⪬', r'⪭', r'⪮', r'⪯', r'⪰', r'⪱', r'⪲',
    r'⪳', r'⪴', r'⪵', r'⪶', r'⪷', r'⪸', r'⪹', r'⪺', r'⪻', r'⪼', r'⪽', r'⪾', r'⪿', r'⫀',
    r'⫁', r'⫂', r'⫃', r'⫄', r'⫅', r'⫆', r'⫇', r'⫈', r'⫉', r'⫊', r'⫋', r'⫌', r'⫍', r'⫎',
    r'⫏', r'⫐', r'⫑', r'⫒', r'⫓', r'⫔', r'⫕', r'⫖', r'⫗', r'⫘', r'⫙', r'⫷', r'⫸', r'⫹',
    r'⫺', r'⊢', r'⊣', r'⟂', r'<:', r'>:',
    # prec-pipe
    '<|', '|>',
    # prec-colon
    r'…', r'⁝', r'⋮', r'⋱', r'⋰', r'⋯',
    # prec-plus
    r'+', r'-', r'¦', r'|', r'⊕', r'⊖', r'⊞', r'⊟', r'++', r'∪', r'∨', r'⊔', r'±', r'∓',
    r'∔', r'∸', r'≏', r'⊎', r'⊻', r'⊽', r'⋎', r'⋓', r'⧺', r'⧻', r'⨈', r'⨢', r'⨣', r'⨤',
    r'⨥', r'⨦', r'⨧', r'⨨', r'⨩', r'⨪', r'⨫', r'⨬', r'⨭', r'⨮', r'⨹', r'⨺', r'⩁', r'⩂',
    r'⩅', r'⩊', r'⩌', r'⩏', r'⩐', r'⩒', r'⩔', r'⩖', r'⩗', r'⩛', r'⩝', r'⩡', r'⩢', r'⩣',
    # prec-times
    r'*', r'/', r'⌿', r'÷', r'%', r'&', r'⋅', r'∘', r'×', '\\', r'∩', r'∧', r'⊗', r'⊘',
    r'⊙', r'⊚', r'⊛', r'⊠', r'⊡', r'⊓', r'∗', r'∙', r'∤', r'⅋', r'≀', r'⊼', r'⋄', r'⋆',
    r'⋇', r'⋉', r'⋊', r'⋋', r'⋌', r'⋏', r'⋒', r'⟑', r'⦸', r'⦼', r'⦾', r'⦿', r'⧶', r'⧷',
    r'⨇', r'⨰', r'⨱', r'⨲', r'⨳', r'⨴', r'⨵', r'⨶', r'⨷', r'⨸', r'⨻', r'⨼', r'⨽', r'⩀',
    r'⩃', r'⩄', r'⩋', r'⩍', r'⩎', r'⩑', r'⩓', r'⩕', r'⩘', r'⩚', r'⩜', r'⩞', r'⩟', r'⩠',
    r'⫛', r'⊍', r'▷', r'⨝', r'⟕', r'⟖', r'⟗', r'⨟',
    # prec-rational, prec-bitshift
    '//', '>>', '<<', '>>>',
    # prec-power
    r'^', r'↑', r'↓', r'⇵', r'⟰', r'⟱', r'⤈', r'⤉', r'⤊', r'⤋', r'⤒', r'⤓', r'⥉', r'⥌',
    r'⥍', r'⥏', r'⥑', r'⥔', r'⥕', r'⥘', r'⥙', r'⥜', r'⥝', r'⥠', r'⥡', r'⥣', r'⥥', r'⥮',
    r'⥯', r'￪', r'￬',
    # unary-ops, excluding unary-and-binary-ops
    '!', r'¬', r'√', r'∛', r'∜'
]

# Generated with the following in Julia v1.6.0-rc1
'''
#!/usr/bin/env julia

import REPL.REPLCompletions
res = String["in", "isa", "where"]
for kw in collect(x.keyword for x in REPLCompletions.complete_keyword(""))
    if !(contains(kw, " ") || kw == "struct")
        push!(res, kw)
    end
end
sort!(unique!(setdiff!(res, ["true", "false"])))
foreach(x -> println("\'", x, "\',"), res)
'''
KEYWORD_LIST = (
    'baremodule',
    'begin',
    'break',
    'catch',
    'ccall',
    'const',
    'continue',
    'do',
    'else',
    'elseif',
    'end',
    'export',
    'finally',
    'for',
    'function',
    'global',
    'if',
    'import',
    'in',
    'isa',
    'let',
    'local',
    'macro',
    'module',
    'quote',
    'return',
    'try',
    'using',
    'where',
    'while',
)

# Generated with the following in Julia v1.6.0-rc1
'''
#!/usr/bin/env julia

import REPL.REPLCompletions
res = String[]
for compl in filter!(x -> isa(x, REPLCompletions.ModuleCompletion) && (x.parent === Base || x.parent === Core),
                    REPLCompletions.completions("", 0)[1])
    try
        v = eval(Symbol(compl.mod))
        if (v isa Type || v isa TypeVar) && (compl.mod != "=>")
            push!(res, compl.mod)
        end
    catch e
    end
end
sort!(unique!(res))
foreach(x -> println("\'", x, "\',"), res)
'''
BUILTIN_LIST = (
    'AbstractArray',
    'AbstractChannel',
    'AbstractChar',
    'AbstractDict',
    'AbstractDisplay',
    'AbstractFloat',
    'AbstractIrrational',
    'AbstractMatch',
    'AbstractMatrix',
    'AbstractPattern',
    'AbstractRange',
    'AbstractSet',
    'AbstractString',
    'AbstractUnitRange',
    'AbstractVecOrMat',
    'AbstractVector',
    'Any',
    'ArgumentError',
    'Array',
    'AssertionError',
    'BigFloat',
    'BigInt',
    'BitArray',
    'BitMatrix',
    'BitSet',
    'BitVector',
    'Bool',
    'BoundsError',
    'CapturedException',
    'CartesianIndex',
    'CartesianIndices',
    'Cchar',
    'Cdouble',
    'Cfloat',
    'Channel',
    'Char',
    'Cint',
    'Cintmax_t',
    'Clong',
    'Clonglong',
    'Cmd',
    'Colon',
    'Complex',
    'ComplexF16',
    'ComplexF32',
    'ComplexF64',
    'ComposedFunction',
    'CompositeException',
    'Condition',
    'Cptrdiff_t',
    'Cshort',
    'Csize_t',
    'Cssize_t',
    'Cstring',
    'Cuchar',
    'Cuint',
    'Cuintmax_t',
    'Culong',
    'Culonglong',
    'Cushort',
    'Cvoid',
    'Cwchar_t',
    'Cwstring',
    'DataType',
    'DenseArray',
    'DenseMatrix',
    'DenseVecOrMat',
    'DenseVector',
    'Dict',
    'DimensionMismatch',
    'Dims',
    'DivideError',
    'DomainError',
    'EOFError',
    'Enum',
    'ErrorException',
    'Exception',
    'ExponentialBackOff',
    'Expr',
    'Float16',
    'Float32',
    'Float64',
    'Function',
    'GlobalRef',
    'HTML',
    'IO',
    'IOBuffer',
    'IOContext',
    'IOStream',
    'IdDict',
    'IndexCartesian',
    'IndexLinear',
    'IndexStyle',
    'InexactError',
    'InitError',
    'Int',
    'Int128',
    'Int16',
    'Int32',
    'Int64',
    'Int8',
    'Integer',
    'InterruptException',
    'InvalidStateException',
    'Irrational',
    'KeyError',
    'LinRange',
    'LineNumberNode',
    'LinearIndices',
    'LoadError',
    'MIME',
    'Matrix',
    'Method',
    'MethodError',
    'Missing',
    'MissingException',
    'Module',
    'NTuple',
    'NamedTuple',
    'Nothing',
    'Number',
    'OrdinalRange',
    'OutOfMemoryError',
    'OverflowError',
    'Pair',
    'PartialQuickSort',
    'PermutedDimsArray',
    'Pipe',
    'ProcessFailedException',
    'Ptr',
    'QuoteNode',
    'Rational',
    'RawFD',
    'ReadOnlyMemoryError',
    'Real',
    'ReentrantLock',
    'Ref',
    'Regex',
    'RegexMatch',
    'RoundingMode',
    'SegmentationFault',
    'Set',
    'Signed',
    'Some',
    'StackOverflowError',
    'StepRange',
    'StepRangeLen',
    'StridedArray',
    'StridedMatrix',
    'StridedVecOrMat',
    'StridedVector',
    'String',
    'StringIndexError',
    'SubArray',
    'SubString',
    'SubstitutionString',
    'Symbol',
    'SystemError',
    'Task',
    'TaskFailedException',
    'Text',
    'TextDisplay',
    'Timer',
    'Tuple',
    'Type',
    'TypeError',
    'TypeVar',
    'UInt',
    'UInt128',
    'UInt16',
    'UInt32',
    'UInt64',
    'UInt8',
    'UndefInitializer',
    'UndefKeywordError',
    'UndefRefError',
    'UndefVarError',
    'Union',
    'UnionAll',
    'UnitRange',
    'Unsigned',
    'Val',
    'Vararg',
    'VecElement',
    'VecOrMat',
    'Vector',
    'VersionNumber',
    'WeakKeyDict',
    'WeakRef',
)

# Generated with the following in Julia v1.6.0-rc1
'''
#!/usr/bin/env julia

import REPL.REPLCompletions
res = String["true", "false"]
for compl in filter!(x -> isa(x, REPLCompletions.ModuleCompletion) && (x.parent === Base || x.parent === Core),
                    REPLCompletions.completions("", 0)[1])
    try
        v = eval(Symbol(compl.mod))
        if !(v isa Function || v isa Type || v isa TypeVar || v isa Module || v isa Colon)
            push!(res, compl.mod)
        end
    catch e
    end
end
sort!(unique!(res))
foreach(x -> println("\'", x, "\',"), res)
'''
LITERAL_LIST = (
    'ARGS',
    'C_NULL',
    'DEPOT_PATH',
    'ENDIAN_BOM',
    'ENV',
    'Inf',
    'Inf16',
    'Inf32',
    'Inf64',
    'InsertionSort',
    'LOAD_PATH',
    'MergeSort',
    'NaN',
    'NaN16',
    'NaN32',
    'NaN64',
    'PROGRAM_FILE',
    'QuickSort',
    'RoundDown',
    'RoundFromZero',
    'RoundNearest',
    'RoundNearestTiesAway',
    'RoundNearestTiesUp',
    'RoundToZero',
    'RoundUp',
    'VERSION',
    'devnull',
    'false',
    'im',
    'missing',
    'nothing',
    'pi',
    'stderr',
    'stdin',
    'stdout',
    'true',
    'undef',
    'π',
    'ℯ',
)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\app.py ===
# Application stuff.
# The application is responsible for managing the main frame window.
#
# We also grab the FileOpen command, to invoke our Python editor
"The PythonWin application code. Manages most aspects of MDI, etc"

from __future__ import annotations

import builtins
import os
import sys
import traceback
import warnings
from typing import TYPE_CHECKING

import regutil
import win32api
import win32con
import win32ui
from pywin.mfc import afxres, dialog, window
from pywin.mfc.thread import WinApp

from . import scriptutils

if TYPE_CHECKING:
    from typing_extensions import Literal


# Helper for writing a Window position by name, and later loading it.
def SaveWindowSize(section, rect, state=""):
    """Writes a rectangle to an INI file
    Args: section = section name in the applications INI file
          rect = a rectangle in a (cy, cx, y, x) tuple
                 (same format as CREATESTRUCT position tuples)."""
    left, top, right, bottom = rect
    if state:
        state += " "
    win32ui.WriteProfileVal(section, state + "left", left)
    win32ui.WriteProfileVal(section, state + "top", top)
    win32ui.WriteProfileVal(section, state + "right", right)
    win32ui.WriteProfileVal(section, state + "bottom", bottom)


def LoadWindowSize(section, state=""):
    """Loads a section from an INI file, and returns a rect in a tuple (see SaveWindowSize)"""
    if state:
        state += " "
    left = win32ui.GetProfileVal(section, state + "left", 0)
    top = win32ui.GetProfileVal(section, state + "top", 0)
    right = win32ui.GetProfileVal(section, state + "right", 0)
    bottom = win32ui.GetProfileVal(section, state + "bottom", 0)
    return (left, top, right, bottom)


def RectToCreateStructRect(rect):
    return (rect[3] - rect[1], rect[2] - rect[0], rect[1], rect[0])


# Define FrameWindow and Application objects
#
# The Main Frame of the application.
class MainFrame(window.MDIFrameWnd):
    sectionPos = "Main Window"
    statusBarIndicators = (
        afxres.ID_SEPARATOR,  # // status line indicator
        afxres.ID_INDICATOR_CAPS,
        afxres.ID_INDICATOR_NUM,
        afxres.ID_INDICATOR_SCRL,
        win32ui.ID_INDICATOR_LINENUM,
        win32ui.ID_INDICATOR_COLNUM,
    )

    def OnCreate(self, cs) -> Literal[-1, 0, 1]:
        self._CreateStatusBar()
        return 0

    def _CreateStatusBar(self):
        self.statusBar = win32ui.CreateStatusBar(self)
        self.statusBar.SetIndicators(self.statusBarIndicators)
        self.HookCommandUpdate(self.OnUpdatePosIndicator, win32ui.ID_INDICATOR_LINENUM)
        self.HookCommandUpdate(self.OnUpdatePosIndicator, win32ui.ID_INDICATOR_COLNUM)

    def OnUpdatePosIndicator(self, cmdui):
        editControl = scriptutils.GetActiveEditControl()
        value = " " * 5
        if editControl is not None:
            try:
                startChar, endChar = editControl.GetSel()
                lineNo = editControl.LineFromChar(startChar)
                colNo = endChar - editControl.LineIndex(lineNo)

                if cmdui.m_nID == win32ui.ID_INDICATOR_LINENUM:
                    value = "%0*d" % (5, lineNo + 1)
                else:
                    value = "%0*d" % (3, colNo + 1)
            except win32ui.error:
                pass
        cmdui.SetText(value)
        cmdui.Enable()

    def PreCreateWindow(self, cc):
        cc = self._obj_.PreCreateWindow(cc)
        pos = LoadWindowSize(self.sectionPos)
        self.startRect = pos
        if pos[2] - pos[0]:
            rect = RectToCreateStructRect(pos)
            cc = cc[0], cc[1], cc[2], cc[3], rect, cc[5], cc[6], cc[7], cc[8]
        return cc

    def OnDestroy(self, msg):
        # use GetWindowPlacement(), as it works even when min'd or max'd
        rectNow = self.GetWindowPlacement()[4]
        if rectNow != self.startRect:
            SaveWindowSize(self.sectionPos, rectNow)
        return 0


class CApp(WinApp):
    "A class for the application"

    def __init__(self):
        self.oldCallbackCaller = None
        WinApp.__init__(self, win32ui.GetApp())
        self.idleHandlers = []

    def InitInstance(self):
        "Called to crank up the app"
        HookInput()
        numMRU = win32ui.GetProfileVal("Settings", "Recent File List Size", 10)
        win32ui.LoadStdProfileSettings(numMRU)
        # 		self._obj_.InitMDIInstance()
        if win32api.GetVersionEx()[0] < 4:
            win32ui.SetDialogBkColor()
            win32ui.Enable3dControls()

        # install a "callback caller" - a manager for the callbacks
        # 		self.oldCallbackCaller = win32ui.InstallCallbackCaller(self.CallbackManager)
        self.LoadMainFrame()
        self.SetApplicationPaths()

    def ExitInstance(self):
        "Called as the app dies - too late to prevent it here!"
        win32ui.OutputDebug("Application shutdown\n")
        # Restore the callback manager, if any.
        try:
            win32ui.InstallCallbackCaller(self.oldCallbackCaller)
        except AttributeError:
            pass
        if self.oldCallbackCaller:
            del self.oldCallbackCaller
        self.frame = None  # clean Python references to the now destroyed window object.
        self.idleHandlers = []
        # Attempt cleanup if not already done!
        if self._obj_:
            self._obj_.AttachObject(None)
        self._obj_ = None
        return 0

    def HaveIdleHandler(self, handler):
        return handler in self.idleHandlers

    def AddIdleHandler(self, handler):
        self.idleHandlers.append(handler)

    def DeleteIdleHandler(self, handler):
        self.idleHandlers.remove(handler)

    def OnIdle(self, count):
        try:
            ret = 0
            handlers = self.idleHandlers[:]  # copy list, as may be modified during loop
            for handler in handlers:
                try:
                    thisRet = handler(handler, count)
                except:
                    print(f"Idle handler {handler!r} failed")
                    traceback.print_exc()
                    print("Idle handler removed from list")
                    try:
                        self.DeleteIdleHandler(handler)
                    except ValueError:  # Item not in list.
                        pass
                    thisRet = 0
                ret = ret or thisRet
            return ret
        except KeyboardInterrupt:
            pass

    def CreateMainFrame(self):
        return MainFrame()

    def LoadMainFrame(self):
        "Create the main applications frame"
        self.frame = self.CreateMainFrame()
        self.SetMainFrame(self.frame)
        self.frame.LoadFrame(win32ui.IDR_MAINFRAME, win32con.WS_OVERLAPPEDWINDOW)
        self.frame.DragAcceptFiles()  # we can accept these.
        self.frame.ShowWindow(win32ui.GetInitialStateRequest())
        self.frame.UpdateWindow()
        self.HookCommands()

    def OnHelp(self, id, code):
        try:
            if id == win32ui.ID_HELP_GUI_REF:
                helpFile = regutil.GetRegisteredHelpFile("Pythonwin Reference")
                helpCmd = win32con.HELP_CONTENTS
            else:
                helpFile = regutil.GetRegisteredHelpFile("Main Python Documentation")
                helpCmd = win32con.HELP_FINDER
            if helpFile is None:
                win32ui.MessageBox("The help file is not registered!")
            else:
                from . import help

                help.OpenHelpFile(helpFile, helpCmd)
        except:
            t, v, tb = sys.exc_info()
            win32ui.MessageBox(f"Internal error in help file processing\r\n{t}: {v}")
            tb = None  # Prevent a cycle

    def DoLoadModules(self, modules):
        # XXX - this should go, but the debugger uses it :-(
        # don't do much checking!
        for module in modules:
            __import__(module)

    def HookCommands(self):
        self.frame.HookMessage(self.OnDropFiles, win32con.WM_DROPFILES)
        self.HookCommand(self.HandleOnFileOpen, win32ui.ID_FILE_OPEN)
        self.HookCommand(self.HandleOnFileNew, win32ui.ID_FILE_NEW)
        self.HookCommand(self.OnFileMRU, win32ui.ID_FILE_MRU_FILE1)
        self.HookCommand(self.OnHelpAbout, win32ui.ID_APP_ABOUT)
        self.HookCommand(self.OnHelp, win32ui.ID_HELP_PYTHON)
        self.HookCommand(self.OnHelp, win32ui.ID_HELP_GUI_REF)
        # Hook for the right-click menu.
        self.frame.GetWindow(win32con.GW_CHILD).HookMessage(
            self.OnRClick, win32con.WM_RBUTTONDOWN
        )

    def SetApplicationPaths(self):
        # Load the users/application paths
        new_path = []
        apppath = win32ui.GetProfileVal("Python", "Application Path", "").split(";")
        for path in apppath:
            if len(path) > 0:
                new_path.append(win32ui.FullPath(path))
        for extra_num in range(1, 11):
            apppath = win32ui.GetProfileVal(
                "Python", "Application Path %d" % extra_num, ""
            ).split(";")
            if len(apppath) == 0:
                break
            for path in apppath:
                if len(path) > 0:
                    new_path.append(win32ui.FullPath(path))
        sys.path = new_path + sys.path

    def OnRClick(self, params):
        "Handle right click message"
        # put up the entire FILE menu!
        menu = win32ui.LoadMenu(win32ui.IDR_TEXTTYPE).GetSubMenu(0)
        menu.TrackPopupMenu(params[5])  # track at mouse position.
        return 0

    def OnDropFiles(self, msg):
        "Handle a file being dropped from file manager"
        hDropInfo = msg[2]
        self.frame.SetActiveWindow()  # active us
        nFiles = win32api.DragQueryFile(hDropInfo)
        try:
            for iFile in range(0, nFiles):
                fileName = win32api.DragQueryFile(hDropInfo, iFile)
                win32ui.GetApp().OpenDocumentFile(fileName)
        finally:
            win32api.DragFinish(hDropInfo)

        return 0

    # No longer used by Pythonwin, as the C++ code has this same basic functionality
    # but handles errors slightly better.
    # It all still works, tho, so if you need similar functionality, you can use it.
    # Therefore I haven't deleted this code completely!
    # 	def CallbackManager( self, ob, args = () ):
    # 		"""Manage win32 callbacks.  Trap exceptions, report on them, then return 'All OK'
    # 		to the frame-work. """
    # 		import traceback
    # 		try:
    # 			ret = apply(ob, args)
    # 			return ret
    # 		except:
    # 			# take copies of the exception values, else other (handled) exceptions may get
    # 			# copied over by the other fns called.
    # 			win32ui.SetStatusText('An exception occured in a windows command handler.')
    # 			t, v, tb = sys.exc_info()
    # 			traceback.print_exception(t, v, tb.tb_next)
    # 			try:
    # 				sys.stdout.flush()
    # 			except (NameError, AttributeError):
    # 				pass

    # Command handlers.
    def OnFileMRU(self, id, code):
        "Called when a File 1-n message is recieved"
        fileName = win32ui.GetRecentFileList()[id - win32ui.ID_FILE_MRU_FILE1]
        win32ui.GetApp().OpenDocumentFile(fileName)

    def HandleOnFileOpen(self, id, code):
        "Called when FileOpen message is received"
        win32ui.GetApp().OnFileOpen()

    def HandleOnFileNew(self, id, code):
        "Called when FileNew message is received"
        win32ui.GetApp().OnFileNew()

    def OnHelpAbout(self, id, code):
        "Called when HelpAbout message is received.  Displays the About dialog."
        win32ui.InitRichEdit()
        dlg = AboutBox()
        dlg.DoModal()


def _GetRegistryValue(key, val, default=None):
    # val is registry value - None for default val.
    try:
        hkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, key)
        return win32api.RegQueryValueEx(hkey, val)[0]
    except win32api.error:
        try:
            hkey = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, key)
            return win32api.RegQueryValueEx(hkey, val)[0]
        except win32api.error:
            return default


scintilla = "Scintilla is Copyright 1998-2020 Neil Hodgson (https://www.scintilla.org)"
idle = "This program uses IDLE extensions by Guido van Rossum, Tim Peters and others."
contributors = "Thanks to the following people for making significant contributions: Roger Upole, Sidnei da Silva, Sam Rushing, Curt Hagenlocher, Dave Brennan, Roger Burnham, Gordon McMillan, Neil Hodgson, Laramie Leavitt. (let me know if I have forgotten you!)"


# The About Box
class AboutBox(dialog.Dialog):
    def __init__(self, idd=win32ui.IDD_ABOUTBOX):
        dialog.Dialog.__init__(self, idd)

    def OnInitDialog(self):
        text = "Pythonwin - Python IDE and GUI Framework for Windows.\n\n{}\n\nPython is {}\n\n{}\n\n{}\n\n{}".format(
            win32ui.copyright, sys.copyright, scintilla, idle, contributors
        )
        self.SetDlgItemText(win32ui.IDC_EDIT1, text)
        import sysconfig

        site_packages = sysconfig.get_paths()["platlib"]
        version_path = os.path.join(site_packages, "pywin32.version.txt")
        try:
            with open(version_path) as f:
                ver = "pywin32 build %s" % f.read().strip()
        except OSError:
            ver = None
        if not ver:
            warnings.warn(f"Could not read pywin32's version from '{version_path}'")
        self.SetDlgItemText(win32ui.IDC_ABOUT_VERSION, ver)
        self.HookCommand(self.OnButHomePage, win32ui.IDC_BUTTON1)

    def OnButHomePage(self, id, code):
        if code == win32con.BN_CLICKED:
            win32api.ShellExecute(
                0, "open", "https://github.com/mhammond/pywin32", None, "", 1
            )


def Win32Input(prompt=None):
    "Provide input() for gui apps"
    # flush stderr/out first.
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except:
        pass
    if prompt is None:
        prompt = ""
    ret = dialog.GetSimpleInput(prompt)
    if ret is None:
        raise KeyboardInterrupt("operation cancelled")
    return ret


def HookInput():
    builtins.input = Win32Input


def HaveGoodGUI():
    """Returns true if we currently have a good gui available."""
    return "pywin.framework.startup" in sys.modules


def CreateDefaultGUI(appClass=None):
    """Creates a default GUI environment"""
    if appClass is None:
        from . import intpyapp  # Bring in the default app - could be param'd later.

        appClass = intpyapp.InteractivePythonApp
    # Create and init the app.
    appClass().InitInstance()


def CheckCreateDefaultGUI():
    """Checks and creates if necessary a default GUI environment."""
    rc = HaveGoodGUI()
    if not rc:
        CreateDefaultGUI()
    return rc

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pyproject_hooks\_impl.py ===
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from os.path import abspath
from os.path import join as pjoin
from subprocess import STDOUT, check_call, check_output
from typing import TYPE_CHECKING, Any, Iterator, Mapping, Optional, Sequence

from ._in_process import _in_proc_script_path

if TYPE_CHECKING:
    from typing import Protocol

    class SubprocessRunner(Protocol):
        """A protocol for the subprocess runner."""

        def __call__(
            self,
            cmd: Sequence[str],
            cwd: Optional[str] = None,
            extra_environ: Optional[Mapping[str, str]] = None,
        ) -> None:
            ...


def write_json(obj: Mapping[str, Any], path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kwargs)


def read_json(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class BackendUnavailable(Exception):
    """Will be raised if the backend cannot be imported in the hook process."""

    def __init__(
        self,
        traceback: str,
        message: Optional[str] = None,
        backend_name: Optional[str] = None,
        backend_path: Optional[Sequence[str]] = None,
    ) -> None:
        # Preserving arg order for the sake of API backward compatibility.
        self.backend_name = backend_name
        self.backend_path = backend_path
        self.traceback = traceback
        super().__init__(message or "Error while importing backend")


class HookMissing(Exception):
    """Will be raised on missing hooks (if a fallback can't be used)."""

    def __init__(self, hook_name: str) -> None:
        super().__init__(hook_name)
        self.hook_name = hook_name


class UnsupportedOperation(Exception):
    """May be raised by build_sdist if the backend indicates that it can't."""

    def __init__(self, traceback: str) -> None:
        self.traceback = traceback


def default_subprocess_runner(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    extra_environ: Optional[Mapping[str, str]] = None,
) -> None:
    """The default method of calling the wrapper subprocess.

    This uses :func:`subprocess.check_call` under the hood.
    """
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)

    check_call(cmd, cwd=cwd, env=env)


def quiet_subprocess_runner(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    extra_environ: Optional[Mapping[str, str]] = None,
) -> None:
    """Call the subprocess while suppressing output.

    This uses :func:`subprocess.check_output` under the hood.
    """
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)

    check_output(cmd, cwd=cwd, env=env, stderr=STDOUT)


def norm_and_check(source_tree: str, requested: str) -> str:
    """Normalise and check a backend path.

    Ensure that the requested backend path is specified as a relative path,
    and resolves to a location under the given source tree.

    Return an absolute version of the requested path.
    """
    if os.path.isabs(requested):
        raise ValueError("paths must be relative")

    abs_source = os.path.abspath(source_tree)
    abs_requested = os.path.normpath(os.path.join(abs_source, requested))
    # We have to use commonprefix for Python 2.7 compatibility. So we
    # normalise case to avoid problems because commonprefix is a character
    # based comparison :-(
    norm_source = os.path.normcase(abs_source)
    norm_requested = os.path.normcase(abs_requested)
    if os.path.commonprefix([norm_source, norm_requested]) != norm_source:
        raise ValueError("paths must be inside source tree")

    return abs_requested


class BuildBackendHookCaller:
    """A wrapper to call the build backend hooks for a source directory."""

    def __init__(
        self,
        source_dir: str,
        build_backend: str,
        backend_path: Optional[Sequence[str]] = None,
        runner: Optional["SubprocessRunner"] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        """
        :param source_dir: The source directory to invoke the build backend for
        :param build_backend: The build backend spec
        :param backend_path: Additional path entries for the build backend spec
        :param runner: The :ref:`subprocess runner <Subprocess Runners>` to use
        :param python_executable:
            The Python executable used to invoke the build backend
        """
        if runner is None:
            runner = default_subprocess_runner

        self.source_dir = abspath(source_dir)
        self.build_backend = build_backend
        if backend_path:
            backend_path = [norm_and_check(self.source_dir, p) for p in backend_path]
        self.backend_path = backend_path
        self._subprocess_runner = runner
        if not python_executable:
            python_executable = sys.executable
        self.python_executable = python_executable

    @contextmanager
    def subprocess_runner(self, runner: "SubprocessRunner") -> Iterator[None]:
        """A context manager for temporarily overriding the default
        :ref:`subprocess runner <Subprocess Runners>`.

        :param runner: The new subprocess runner to use within the context.

        .. code-block:: python

            hook_caller = BuildBackendHookCaller(...)
            with hook_caller.subprocess_runner(quiet_subprocess_runner):
                ...
        """
        prev = self._subprocess_runner
        self._subprocess_runner = runner
        try:
            yield
        finally:
            self._subprocess_runner = prev

    def _supported_features(self) -> Sequence[str]:
        """Return the list of optional features supported by the backend."""
        return self._call_hook("_supported_features", {})

    def get_requires_for_build_wheel(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building a wheel.

        :param config_settings: The configuration settings for the build backend
        :returns: A list of :pep:`dependency specifiers <508>`.

        .. admonition:: Fallback

            If the build backend does not defined a hook with this name, an
            empty list will be returned.
        """
        return self._call_hook(
            "get_requires_for_build_wheel", {"config_settings": config_settings}
        )

    def prepare_metadata_for_build_wheel(
        self,
        metadata_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        _allow_fallback: bool = True,
    ) -> str:
        """Prepare a ``*.dist-info`` folder with metadata for this project.

        :param metadata_directory: The directory to write the metadata to
        :param config_settings: The configuration settings for the build backend
        :param _allow_fallback:
            Whether to allow the fallback to building a wheel and extracting
            the metadata from it. Should be passed as a keyword argument only.

        :returns: Name of the newly created subfolder within
                  ``metadata_directory``, containing the metadata.

        .. admonition:: Fallback

            If the build backend does not define a hook with this name and
            ``_allow_fallback`` is truthy, the backend will be asked to build a
            wheel via the ``build_wheel`` hook and the dist-info extracted from
            that will be returned.
        """
        return self._call_hook(
            "prepare_metadata_for_build_wheel",
            {
                "metadata_directory": abspath(metadata_directory),
                "config_settings": config_settings,
                "_allow_fallback": _allow_fallback,
            },
        )

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        metadata_directory: Optional[str] = None,
    ) -> str:
        """Build a wheel from this project.

        :param wheel_directory: The directory to write the wheel to
        :param config_settings: The configuration settings for the build backend
        :param metadata_directory: The directory to reuse existing metadata from
        :returns:
            The name of the newly created wheel within ``wheel_directory``.

        .. admonition:: Interaction with fallback

            If the ``build_wheel`` hook was called in the fallback for
            :meth:`prepare_metadata_for_build_wheel`, the build backend would
            not be invoked. Instead, the previously built wheel will be copied
            to ``wheel_directory`` and the name of that file will be returned.
        """
        if metadata_directory is not None:
            metadata_directory = abspath(metadata_directory)
        return self._call_hook(
            "build_wheel",
            {
                "wheel_directory": abspath(wheel_directory),
                "config_settings": config_settings,
                "metadata_directory": metadata_directory,
            },
        )

    def get_requires_for_build_editable(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building an editable wheel.

        :param config_settings: The configuration settings for the build backend
        :returns: A list of :pep:`dependency specifiers <508>`.

        .. admonition:: Fallback

            If the build backend does not defined a hook with this name, an
            empty list will be returned.
        """
        return self._call_hook(
            "get_requires_for_build_editable", {"config_settings": config_settings}
        )

    def prepare_metadata_for_build_editable(
        self,
        metadata_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        _allow_fallback: bool = True,
    ) -> Optional[str]:
        """Prepare a ``*.dist-info`` folder with metadata for this project.

        :param metadata_directory: The directory to write the metadata to
        :param config_settings: The configuration settings for the build backend
        :param _allow_fallback:
            Whether to allow the fallback to building a wheel and extracting
            the metadata from it. Should be passed as a keyword argument only.
        :returns: Name of the newly created subfolder within
                  ``metadata_directory``, containing the metadata.

        .. admonition:: Fallback

            If the build backend does not define a hook with this name and
            ``_allow_fallback`` is truthy, the backend will be asked to build a
            wheel via the ``build_editable`` hook and the dist-info
            extracted from that will be returned.
        """
        return self._call_hook(
            "prepare_metadata_for_build_editable",
            {
                "metadata_directory": abspath(metadata_directory),
                "config_settings": config_settings,
                "_allow_fallback": _allow_fallback,
            },
        )

    def build_editable(
        self,
        wheel_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        metadata_directory: Optional[str] = None,
    ) -> str:
        """Build an editable wheel from this project.

        :param wheel_directory: The directory to write the wheel to
        :param config_settings: The configuration settings for the build backend
        :param metadata_directory: The directory to reuse existing metadata from
        :returns:
            The name of the newly created wheel within ``wheel_directory``.

        .. admonition:: Interaction with fallback

            If the ``build_editable`` hook was called in the fallback for
            :meth:`prepare_metadata_for_build_editable`, the build backend
            would not be invoked. Instead, the previously built wheel will be
            copied to ``wheel_directory`` and the name of that file will be
            returned.
        """
        if metadata_directory is not None:
            metadata_directory = abspath(metadata_directory)
        return self._call_hook(
            "build_editable",
            {
                "wheel_directory": abspath(wheel_directory),
                "config_settings": config_settings,
                "metadata_directory": metadata_directory,
            },
        )

    def get_requires_for_build_sdist(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building an sdist.

        :returns: A list of :pep:`dependency specifiers <508>`.
        """
        return self._call_hook(
            "get_requires_for_build_sdist", {"config_settings": config_settings}
        )

    def build_sdist(
        self,
        sdist_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Build an sdist from this project.

        :returns:
            The name of the newly created sdist within ``wheel_directory``.
        """
        return self._call_hook(
            "build_sdist",
            {
                "sdist_directory": abspath(sdist_directory),
                "config_settings": config_settings,
            },
        )

    def _call_hook(self, hook_name: str, kwargs: Mapping[str, Any]) -> Any:
        extra_environ = {"_PYPROJECT_HOOKS_BUILD_BACKEND": self.build_backend}

        if self.backend_path:
            backend_path = os.pathsep.join(self.backend_path)
            extra_environ["_PYPROJECT_HOOKS_BACKEND_PATH"] = backend_path

        with tempfile.TemporaryDirectory() as td:
            hook_input = {"kwargs": kwargs}
            write_json(hook_input, pjoin(td, "input.json"), indent=2)

            # Run the hook in a subprocess
            with _in_proc_script_path() as script:
                python = self.python_executable
                self._subprocess_runner(
                    [python, abspath(str(script)), hook_name, td],
                    cwd=self.source_dir,
                    extra_environ=extra_environ,
                )

            data = read_json(pjoin(td, "output.json"))
            if data.get("unsupported"):
                raise UnsupportedOperation(data.get("traceback", ""))
            if data.get("no_backend"):
                raise BackendUnavailable(
                    data.get("traceback", ""),
                    message=data.get("backend_error", ""),
                    backend_name=self.build_backend,
                    backend_path=self.backend_path,
                )
            if data.get("hook_missing"):
                raise HookMissing(data.get("missing_hook_name") or hook_name)
            return data["return_val"]